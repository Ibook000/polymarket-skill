"""
DashboardBridge — 策略事件 → WebSocket 客户端广播

维护:
  - 已连接的 WebSocket 客户端集合
  - 价格/赔率/日志的环形缓冲区（新客户端连接时回放历史）
"""

import json
import time
import asyncio
from collections import deque
from typing import Any

from fastapi import WebSocket


class DashboardBridge:
    """策略事件桥接器：接收策略数据，广播给所有 WebSocket 客户端"""

    def __init__(self, max_prices: int = 200, max_logs: int = 500):
        self.clients: set[WebSocket] = set()
        self.price_history: deque[dict] = deque(maxlen=max_prices)
        self.odds_history: deque[dict] = deque(maxlen=max_prices)
        self.log_buffer: deque[dict] = deque(maxlen=max_logs)
        self.signals: list[dict] = []
        self.signal_audit: list[dict] = []  # 信号审核结果
        self._running = False
        self._dry_run = True

    # ── 状态属性 ──────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def set_status(self, running: bool, dry_run: bool | None = None):
        self._running = running
        if dry_run is not None:
            self._dry_run = dry_run

    # ── 客户端管理 ────────────────────────────────────────

    def add_client(self, ws: WebSocket):
        self.clients.add(ws)

    def remove_client(self, ws: WebSocket):
        self.clients.discard(ws)

    async def send_history(self, ws: WebSocket):
        """向新连接的客户端发送历史数据"""
        msg = json.dumps({
            "type": "history",
            "data": {
                "prices": list(self.price_history),
                "odds": list(self.odds_history),
                "logs": list(self.log_buffer),
                "signals": self.signals,
                "signal_audit": self.signal_audit,
                "running": self._running,
                "dry_run": self._dry_run,
            },
        })
        try:
            await ws.send_text(msg)
        except Exception:
            self.clients.discard(ws)

    # ── 广播 ──────────────────────────────────────────────

    async def broadcast(self, message: dict):
        """向所有已连接的客户端广播 JSON 消息"""
        if not self.clients:
            return
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in self.clients:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    # ── 策略事件回调（供 Strategy.on_event 使用）──────────

    def on_event(self, event_type: str, data: dict):
        """同步回调 — 由 Strategy 在 check_signals 中调用"""
        if event_type == "tick":
            entry = {
                "price": data["price"],
                "change_bps": round(data["change_bps"], 2),
                "up_odds": round(data["up_odds"], 4),
                "down_odds": round(data["down_odds"], 4),
                "ts": data["ts"],
            }
            self.price_history.append(entry)
            self.odds_history.append(entry)
            # 异步广播（事件循环已在运行）
            asyncio.get_event_loop().create_task(
                self.broadcast({"type": "tick", "data": entry})
            )

        elif event_type == "signal":
            entry = {
                "side": data["side"],
                "reason": data["reason"],
                "ts": data["ts"],
            }
            self.signals.append(entry)
            asyncio.get_event_loop().create_task(
                self.broadcast({"type": "signal", "data": entry})
            )

        elif event_type == "new_period":
            # 新周期：清空历史数据，通知前端重置图表
            self.price_history.clear()
            self.odds_history.clear()
            asyncio.get_event_loop().create_task(
                self.broadcast({"type": "new_period", "data": {"slug": data["slug"], "ts": data["ts"]}})
            )

        elif event_type == "signal_result":
            entry = {
                "slug": data["slug"],
                "side": data["side"],
                "result": data["result"],
                "start_price": data["start_price"],
                "end_price": data["end_price"],
                "change_bps": data["change_bps"],
                "reason": data["reason"],
                "ts": data["ts"],
            }
            self.signal_audit.append(entry)
            asyncio.get_event_loop().create_task(
                self.broadcast({"type": "signal_result", "data": entry})
            )

    def on_log(self, log_entry: dict):
        """同步回调 — 由 log() 函数调用"""
        self.log_buffer.append(log_entry)
        asyncio.get_event_loop().create_task(
            self.broadcast({"type": "log", "data": log_entry})
        )
