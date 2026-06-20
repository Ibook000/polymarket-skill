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
_place_market_buy = None
_create_client = None


def _ensure_place_order_loaded():
    """延迟加载 place_order 模块（避免 import 时触发 .env / SDK 初始化）"""
    global _place_limit_order, _place_market_buy, _create_client
    if _place_limit_order is None:
        from dotenv import load_dotenv
        load_dotenv()
        from place_order import create_client, place_order, place_market_buy
        _create_client = create_client
        _place_limit_order = place_order
        _place_market_buy = place_market_buy

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
    ORDER_SIZE             = 10      # 每单份额（限价单）
    ORDER_PRICE            = 0.50    # 限价单价格
    ORDER_AMOUNT           = 5       # 市价单花费金额 (USDC)
    USE_MARKET_ORDER       = False   # True=市价单, False=限价单
    MAX_POSITION           = 100     # 最大持仓份额
    COOLDOWN_SEC           = 60      # 下单冷却时间（秒）
    CHECK_INTERVAL_SEC     = 5      # 价格检查间隔（秒）

    # 币安API
    BINANCE_KLINE_URL = "https://api.binance.com/api/v3/klines"
    BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"


# ======================== 工具函数 ========================

def now_beijing() -> datetime:
    """当前北京时间"""
    return datetime.now(timezone.utc) + timedelta(hours=8)


_log_sink = None  # 可选：Dashboard 挂钩，接收日志回调


def log(msg: str, level: str = "INFO"):
    """带时间戳的日志"""
    ts = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")
    if _log_sink:
        try:
            _log_sink({"type": "log", "level": level, "msg": msg, "ts": ts})
        except Exception:
            pass


def current_slug() -> str:
    """生成当前5分钟周期的市场slug"""
    ts = int(time.time())
    interval_ts = (ts // Config.INTERVAL_SEC) * Config.INTERVAL_SEC
    return f"{Config.SLUG_PREFIX}-{interval_ts}"


def get_period_end_price(interval_start_ts: int) -> Optional[float]:
    """获取某个5分钟周期的收盘价（K线close）"""
    try:
        resp = requests.get(
            Config.BINANCE_KLINE_URL,
            params={
                "symbol": "BTCUSDT",
                "interval": "5m",
                "startTime": interval_start_ts * 1000,
                "limit": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        klines = resp.json()
        if klines:
            return float(klines[0][4])  # close price
    except Exception as e:
        log(f"获取周期收盘价失败: {e}", "ERROR")
    return None


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
    def get_midpoint(token_id: str) -> Optional[float]:
        """获取订单簿中间价（实时赔率）— 比 last-trade-price 更实时"""
        if not token_id:
            return None
        try:
            resp = requests.get(
                f"{MarketData.CLOB_HOST}/midpoint",
                params={"token_id": token_id},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                return float(data.get("mid", 0))
        except Exception as e:
            log(f"获取中间价失败: {e}", "WARN")
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
            if Config.USE_MARKET_ORDER:
                log(f"[模拟] 市价买 {side_label}: amount={Config.ORDER_AMOUNT} USDC")
            else:
                log(f"[模拟] 限价买 {side_label}: price={Config.ORDER_PRICE}, size={Config.ORDER_SIZE}")
            return "dry-run-order-id"

        if not self.client:
            log("交易客户端未初始化", "ERROR")
            return None

        try:
            _ensure_place_order_loaded()

            if Config.USE_MARKET_ORDER:
                resp = await _place_market_buy(
                    self.client,
                    token_id=token_id,
                    amount=Config.ORDER_AMOUNT,
                )
            else:
                resp = await _place_limit_order(
                    self.client,
                    token_id=token_id,
                    side="BUY",
                    price=Config.ORDER_PRICE,
                    size=Config.ORDER_SIZE,
                )

            if resp.ok:
                order_id = resp.order_id
                mode = "市价" if Config.USE_MARKET_ORDER else "限价"
                log(f"[OK] {mode}买单已提交: {side_label} | order_id={order_id[:16]}...")
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

    def __init__(self, dry_run: bool = False, once: bool = False, on_event=None):
        self.dry_run = dry_run
        self.once = once
        self.btc = BTCTracker()
        self.trader = Trader(dry_run=dry_run)
        self.current_slug: Optional[str] = None
        self.current_market = None
        self.token_yes: Optional[str] = None
        self.token_no: Optional[str] = None
        self.signal_given_this_period = False
        self.on_event = on_event  # 可选回调: on_event(type: str, data: dict)
        self.signal_history: list[dict] = []  # 信号审核记录
        self._prev_signal: Optional[dict] = None  # 上一周期待审核信号

    async def init(self):
        """初始化"""
        log("=" * 60)
        log("BTC 5分钟预测市场策略启动")
        log("=" * 60)
        log(f"模式: {'模拟' if self.dry_run else '实盘'}")
        log(f"价格变动阈值: ±{Config.PRICE_CHANGE_BPS}基点 (±{Config.PRICE_CHANGE_BPS/100:.2f}%)")
        log(f"信号: BTC下跌+UP赔率>{Config.UP_ODDS_THRESHOLD:.0%} → 买YES | BTC上涨+DOWN赔率<{Config.DOWN_ODDS_THRESHOLD:.0%} → 买NO")
        if Config.USE_MARKET_ORDER:
            log(f"下单模式: 市价 | 单笔花费: {Config.ORDER_AMOUNT} USDC")
        else:
            log(f"下单模式: 限价 | 单笔份额: {Config.ORDER_SIZE} @ ${Config.ORDER_PRICE}")

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

    async def update_market(self):
        """更新当前周期的市场"""
        slug = current_slug()

        # 新周期开始
        if slug != self.current_slug:
            # ── 审核上一周期的信号 ──────────────────────
            if self._prev_signal:
                await self._audit_prev_signal()

            old_slug = self.current_slug
            self.current_slug = slug
            self.signal_given_this_period = False
            self.btc.period_start_price = None  # 重置周期起始价

            log(f"--- 新周期开始: {slug} ---")

            # 通知 Dashboard 新周期开始（前端重置图表）
            if self.on_event:
                try:
                    self.on_event("new_period", {"slug": slug, "ts": time.time()})
                except Exception:
                    pass

            market, token_yes, token_no = await asyncio.to_thread(MarketData.load_market, slug)
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

    async def _audit_prev_signal(self):
        """审核上一周期的信号：获取收盘价，判断 WIN/LOSS"""
        sig = self._prev_signal
        if not sig:
            return

        prev_slug = sig["slug"]
        # 从 slug 提取周期起始时间戳: btc-updown-5m-{ts}
        try:
            interval_ts = int(prev_slug.split("-")[-1])
        except (ValueError, IndexError):
            self._prev_signal = None
            return

        end_price = await asyncio.to_thread(get_period_end_price, interval_ts)
        if end_price is None:
            log(f"[审核] {prev_slug}: 无法获取收盘价，跳过", "WARN")
            self._prev_signal = None
            return

        start_price = sig["start_price"]
        change = end_price - start_price
        change_bps = (change / start_price) * 10000

        # 判定结果
        # BUY YES = 预测BTC会涨回来 → 正确当 end_price > start_price
        # BUY NO  = 预测BTC会跌回来 → 正确当 end_price < start_price
        if sig["side"] == "YES":
            won = end_price > start_price
        else:  # NO
            won = end_price < start_price

        result = "WIN" if won else "LOSS"
        sig["end_price"] = end_price
        sig["change_bps"] = round(change_bps, 2)
        sig["result"] = result
        self.signal_history.append(sig)

        emoji = "✅" if won else "❌"
        log(f"[审核] {prev_slug}: {sig['side']} → {result} {emoji} "
            f"| 收盘 ${end_price:,.2f} | 变动 {change:+.2f} ({change_bps:+.1f}bp)")

        # 通知 Dashboard
        if self.on_event:
            try:
                self.on_event("signal_result", {
                    "slug": prev_slug,
                    "side": sig["side"],
                    "result": result,
                    "start_price": start_price,
                    "end_price": end_price,
                    "change_bps": round(change_bps, 2),
                    "reason": sig["reason"],
                    "ts": sig["ts"],
                })
            except Exception:
                pass

        self._prev_signal = None

    async def check_signals(self):
        """检查交易信号"""
        if not self.current_market:
            return
        if not self.token_yes or not self.token_no:
            return

        # 获取价格变动（to_thread 避免阻塞事件循环）
        change = await asyncio.to_thread(self.btc.get_price_change)
        if change is None:
            return

        current = self.btc.current_price
        start = self.btc.period_start_price
        change_bps = (change / start) * 10000  # 转换为基点

        # 获取实时赔率（订单簿中间价，比 last-trade-price 更实时）
        up_odds = await asyncio.to_thread(MarketData.get_midpoint, self.token_yes)
        down_odds = await asyncio.to_thread(MarketData.get_midpoint, self.token_no)

        # 输出状态（始终输出，包括信号触发后）
        if up_odds is not None and down_odds is not None:
            tag = " [已下单]" if self.signal_given_this_period else ""
            log(f"BTC: ${current:,.2f} | 变动: {change:+.2f} ({change_bps:+.1f}基点) | UP: {up_odds:.1%} | DOWN: {down_odds:.1%}{tag}")
        else:
            log(f"BTC: ${current:,.2f} | 变动: {change:+.2f} ({change_bps:+.1f}基点) | 赔率获取失败")
            return

        # 发送 tick 事件给 Dashboard
        if self.on_event:
            try:
                self.on_event("tick", {
                    "price": current,
                    "start_price": start,
                    "change": change,
                    "change_bps": change_bps,
                    "up_odds": up_odds,
                    "down_odds": down_odds,
                    "ts": time.time(),
                })
            except Exception:
                pass

        # 已下单则跳过信号判断
        if self.signal_given_this_period:
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
            # 立即标记，防止同一周期重复下单
            self.signal_given_this_period = True
            ts_str = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
            if self.on_event:
                try:
                    self.on_event("signal", {"side": side_label, "reason": reason, "ts": ts_str})
                except Exception:
                    pass
            order_id = await self.trader.place_buy(token_id, side_label)
                # 记录信号供下一周期审核
                self._prev_signal = {
                    "slug": self.current_slug,
                    "side": side_label,
                    "reason": reason,
                    "start_price": start,
                    "signal_price": current,
                    "signal_bps": round(change_bps, 2),
                    "ts": ts_str,
                    "end_price": None,
                    "change_bps": None,
                    "result": None,
                }

    async def run_loop(self):
        """主循环"""
        log("开始监控...")

        while True:
            try:
                # 更新市场（检测新周期）
                await self.update_market()

                # 更新BTC价格（to_thread 避免阻塞事件循环）
                await asyncio.to_thread(self.btc.get_current_price)

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
