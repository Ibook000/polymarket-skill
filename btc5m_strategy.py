"""
BTC 5分钟预测市场 — 自动交易策略

策略逻辑：
  - BTC价格下跌（≥2基点）+ UP赔率 > 50 → 买YES（押BTC会涨回来）
  - BTC价格上涨（≥2基点）+ DOWN赔率 < 50 → 买NO（押BTC会跌回来）

功能：
  1. 实时监控BTC价格（币安API）
  2. 检测5分钟周期内价格变动
  3. 获取Polymarket市场赔率
  4. 自动下单 / 撤单
  5. 风险管理（仓位限制、止损）

用法：
  python btc5m_strategy.py              # 启动策略
  python btc5m_strategy.py --dry-run    # 模拟运行（不下单）
  python btc5m_strategy.py --once       # 只检查一次
"""

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

# 延迟导入：仅 CLI 直接运行时加载 .env；模块导入时不加载
_place_limit_order = None
_create_client = None


def _ensure_place_order_loaded():
    """延迟加载 place_order 模块（避免 import 时触发 .env / SDK 初始化）"""
    global _place_limit_order, _create_client
    if _place_limit_order is None:
        from dotenv import load_dotenv
        load_dotenv()
        from place_order import create_client, place_order
        _create_client = create_client
        _place_limit_order = place_order

# ======================== 配置 ========================

class Config:
    """策略配置"""
    # 市场参数
    SLUG_PREFIX     = "btc-updown-5m"
    INTERVAL_SEC    = 300  # 5分钟
    TICK_SIZE        = "0.01"

    # 策略参数 — BTC下跌 + UP赔率>50 → 买YES；BTC上涨 + DOWN赔率<50 → 买NO
    PRICE_CHANGE_BPS       = 2      # 价格变动阈值（基点，1基点=0.01%，2基点=0.02%）
    UP_ODDS_THRESHOLD      = 0.50    # UP赔率 > 50% 时满足条件
    DOWN_ODDS_THRESHOLD    = 0.50    # DOWN赔率 < 50% 时满足条件
    ORDER_SIZE             = 10      # 每单份额
    ORDER_PRICE            = 0.50    # 限价单价格
    MAX_POSITION           = 100     # 最大持仓份额
    COOLDOWN_SEC           = 60      # 下单冷却时间（秒）
    CHECK_INTERVAL_SEC     = 0      # 价格检查间隔（秒）

    # 币安API
    BINANCE_KLINE_URL = "https://api.binance.com/api/v3/klines"
    BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"


# ======================== 工具函数 ========================

def now_beijing() -> datetime:
    """当前北京时间"""
    return datetime.now(timezone.utc) + timedelta(hours=8)


def log(msg: str, level: str = "INFO"):
    """带时间戳的日志"""
    ts = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def current_slug() -> str:
    """生成当前5分钟周期的市场slug"""
    ts = int(time.time())
    interval_ts = (ts // Config.INTERVAL_SEC) * Config.INTERVAL_SEC
    return f"{Config.SLUG_PREFIX}-{interval_ts}"


# ======================== BTC价格 ========================

class BTCTracker:
    """BTC价格追踪器"""

    def __init__(self):
        self.period_start_price: Optional[float] = None
        self.current_price: Optional[float] = None
        self.last_update: float = 0

    def get_current_price(self) -> Optional[float]:
        """获取BTC当前价格（币安）"""
        try:
            resp = requests.get(
                Config.BINANCE_TICKER_URL,
                params={"symbol": "BTCUSDT"},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            price = float(data["price"])
            self.current_price = price
            self.last_update = time.time()
            return price
        except Exception as e:
            log(f"获取BTC价格失败: {e}", "ERROR")
            return None

    def get_period_start_price(self) -> Optional[float]:
        """获取当前5分钟周期开始时的价格"""
        try:
            # 计算当前周期开始时间
            now = int(time.time())
            interval_start = (now // Config.INTERVAL_SEC) * Config.INTERVAL_SEC

            # 获取该时间点的K线
            resp = requests.get(
                Config.BINANCE_KLINE_URL,
                params={
                    "symbol": "BTCUSDT",
                    "interval": "5m",
                    "startTime": interval_start * 1000,
                    "limit": 1,
                },
                timeout=10
            )
            resp.raise_for_status()
            klines = resp.json()

            if klines:
                # K线格式: [open_time, open, high, low, close, ...]
                open_price = float(klines[0][1])
                self.period_start_price = open_price
                return open_price

        except Exception as e:
            log(f"获取周期起始价格失败: {e}", "ERROR")

        return None

    def get_price_change(self) -> Optional[float]:
        """
        获取当前周期的价格变动
        正数=上涨，负数=下跌
        """
        if not self.current_price:
            self.get_current_price()

        if not self.period_start_price:
            self.get_period_start_price()

        if self.current_price and self.period_start_price:
            return self.current_price - self.period_start_price

        return None


# ======================== 市场数据 ========================

class MarketData:
    """Polymarket市场数据"""

    CLOB_HOST = "https://clob.polymarket.com"

    @staticmethod
    def load_market(slug: str) -> tuple:
        """加载市场，返回 (market, token_yes, token_no)"""
        url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"
        try:
            resp = requests.get(url, timeout=20)
            if not resp.ok:
                log(f"加载市场失败: {resp.status_code}", "ERROR")
                return None, None, None

            market = resp.json()
            clob_ids = json.loads(market.get("clobTokenIds", "[]"))
            token_yes = clob_ids[0] if len(clob_ids) > 0 else None
            token_no = clob_ids[1] if len(clob_ids) > 1 else None

            return market, token_yes, token_no

        except Exception as e:
            log(f"加载市场异常: {e}", "ERROR")
            return None, None, None

    @staticmethod
    def get_last_trade_price(token_id: str) -> Optional[float]:
        """获取最新成交价（实时赔率）— REST API"""
        if not token_id:
            return None
        try:
            resp = requests.get(
                f"{MarketData.CLOB_HOST}/last-trade-price",
                params={"token_id": token_id},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                return float(data.get("price", 0))
        except Exception as e:
            log(f"获取最新成交价失败: {e}", "WARN")
        return None


# ======================== 交易执行 ========================

class Trader:
    """交易执行器 — 使用 polymarket-client SDK"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = None  # AsyncSecureClient
        self.last_trade_time: float = 0
        self.position_count: int = 0

    async def init_client(self):
        """初始化交易客户端"""
        if self.dry_run:
            log("模拟模式，跳过客户端初始化")
            return
        _ensure_place_order_loaded()
        self.client = await _create_client()
        log("交易客户端已初始化")

    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.close()

    def can_trade(self) -> bool:
        """检查是否可以交易"""
        elapsed = time.time() - self.last_trade_time
        if elapsed < Config.COOLDOWN_SEC:
            remaining = Config.COOLDOWN_SEC - elapsed
            log(f"冷却中，还需等待 {remaining:.0f} 秒")
            return False

        if self.position_count >= Config.MAX_POSITION / Config.ORDER_SIZE:
            log(f"已达最大仓位限制 {Config.MAX_POSITION} 份额")
            return False

        return True

    async def place_buy(self, token_id: str, side_label: str) -> Optional[str]:
        """下买单"""
        if not self.can_trade():
            return None

        if self.dry_run:
            log(f"[模拟] 买 {side_label}: price={Config.ORDER_PRICE}, size={Config.ORDER_SIZE}")
            return "dry-run-order-id"

        if not self.client:
            log("交易客户端未初始化", "ERROR")
            return None

        try:
            _ensure_place_order_loaded()
            resp = await _place_limit_order(
                self.client,
                token_id=token_id,
                side="BUY",
                price=Config.ORDER_PRICE,
                size=Config.ORDER_SIZE,
            )

            if resp.ok:
                order_id = resp.order_id
                log(f"[OK] 买单已提交: {side_label} | order_id={order_id[:16]}...")
                self.last_trade_time = time.time()
                self.position_count += 1
                return order_id
            else:
                log(f"[FAIL] 下单失败: {getattr(resp, 'code', '')} - {getattr(resp, 'message', '')}", "ERROR")
                return None

        except Exception as e:
            log(f"下单异常: {e}", "ERROR")
            return None


# ======================== 策略引擎 ========================

class Strategy:
    """策略主引擎"""

    def __init__(self, dry_run: bool = False, once: bool = False):
        self.dry_run = dry_run
        self.once = once
        self.btc = BTCTracker()
        self.trader = Trader(dry_run=dry_run)
        self.current_slug: Optional[str] = None
        self.current_market = None
        self.token_yes: Optional[str] = None
        self.token_no: Optional[str] = None
        self.signal_given_this_period = False

    async def init(self):
        """初始化"""
        log("=" * 60)
        log("BTC 5分钟预测市场策略启动")
        log("=" * 60)
        log(f"模式: {'模拟' if self.dry_run else '实盘'}")
        log(f"价格变动阈值: ±{Config.PRICE_CHANGE_BPS}基点 (±{Config.PRICE_CHANGE_BPS/100:.2f}%)")
        log(f"信号: BTC下跌+UP赔率>{Config.UP_ODDS_THRESHOLD:.0%} → 买YES | BTC上涨+DOWN赔率<{Config.DOWN_ODDS_THRESHOLD:.0%} → 买NO")
        log(f"单笔份额: {Config.ORDER_SIZE}")
        log(f"最大持仓: {Config.MAX_POSITION}")
        log("=" * 60)

        # 初始化交易客户端
        await self.trader.init_client()

        # 获取初始价格
        price = self.btc.get_current_price()
        if price:
            log(f"BTC当前价格: ${price:,.2f}")
        else:
            log("无法获取BTC价格，退出", "ERROR")
            sys.exit(1)

    def update_market(self):
        """更新当前周期的市场"""
        slug = current_slug()

        # 新周期开始
        if slug != self.current_slug:
            self.current_slug = slug
            self.signal_given_this_period = False
            self.btc.period_start_price = None  # 重置周期起始价

            log(f"--- 新周期开始: {slug} ---")

            market, token_yes, token_no = MarketData.load_market(slug)
            if market:
                self.current_market = market
                self.token_yes = token_yes
                self.token_no = token_no
                log(f"市场: {market.get('question', '?')}")
            else:
                self.current_market = None
                self.token_yes = None
                self.token_no = None
                log("市场未就绪", "WARN")

    async def check_signals(self):
        """检查交易信号"""
        if not self.current_market:
            return
        if not self.token_yes or not self.token_no:
            return
        if self.signal_given_this_period:
            return

        # 获取价格变动
        change = self.btc.get_price_change()
        if change is None:
            return

        current = self.btc.current_price
        start = self.btc.period_start_price
        change_bps = (change / start) * 10000  # 转换为基点

        # 从最新成交价获取实时赔率（REST API）
        up_odds = MarketData.get_last_trade_price(self.token_yes)
        down_odds = MarketData.get_last_trade_price(self.token_no)

        # 输出状态
        if up_odds is not None and down_odds is not None:
            log(f"BTC: ${current:,.2f} | 变动: {change:+.2f} ({change_bps:+.1f}基点) | UP: {up_odds:.1%} | DOWN: {down_odds:.1%}")
        else:
            log(f"BTC: ${current:,.2f} | 变动: {change:+.2f} ({change_bps:+.1f}基点) | 赔率获取失败")
            return

        # 判断信号
        signal = None
        threshold_bps = Config.PRICE_CHANGE_BPS

        # 信号1: BTC下跌（≥2bp）+ UP赔率 > 50 → 买YES（押BTC会涨回来）
        if change_bps <= -threshold_bps:
            if up_odds > Config.UP_ODDS_THRESHOLD:
                signal = ("YES", self.token_yes,
                          f"BTC下跌{abs(change_bps):.1f}bp + UP赔率{up_odds:.0%}>50% → 买YES")

        # 信号2: BTC上涨（≥2bp）+ DOWN赔率 > 50 → 买NO（押BTC会跌回来）
        elif change_bps >= threshold_bps:
            if down_odds > Config.DOWN_ODDS_THRESHOLD:
                signal = ("NO", self.token_no,
                          f"BTC上涨{change_bps:.1f}bp + DOWN赔率{down_odds:.0%}<50% → 买NO")

        # 执行交易
        if signal:
            side_label, token_id, reason = signal
            log(f"*** 信号触发: {reason} ***")
            order_id = await self.trader.place_buy(token_id, side_label)
            if order_id:
                self.signal_given_this_period = True

    async def run_loop(self):
        """主循环"""
        log("开始监控...")

        while True:
            try:
                # 更新市场（检测新周期）
                self.update_market()

                # 更新BTC价格
                self.btc.get_current_price()

                # 检查信号
                await self.check_signals()

                # 单次模式
                if self.once:
                    log("单次检查完成")
                    break

                # 等待下次检查
                await asyncio.sleep(Config.CHECK_INTERVAL_SEC)

            except KeyboardInterrupt:
                log("用户中断，退出")
                break
            except Exception as e:
                log(f"异常: {e}", "ERROR")
                await asyncio.sleep(5)

    async def run(self):
        """运行策略"""
        await self.init()
        try:
            await self.run_loop()
        finally:
            await self.trader.close()


# ======================== 主入口 ========================

async def _async_main(dry_run: bool, once: bool):
    strategy = Strategy(dry_run=dry_run, once=once)
    await strategy.run()


def main():
    parser = argparse.ArgumentParser(description="BTC 5分钟预测市场策略")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不下单")
    parser.add_argument("--once", action="store_true", help="只检查一次")
    args = parser.parse_args()

    # CLI 模式：加载 .env
    _ensure_place_order_loaded()

    asyncio.run(_async_main(args.dry_run, args.once))


if __name__ == "__main__":
    main()
