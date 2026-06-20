"""
WebSocket 端点 — 处理客户端连接和策略控制命令
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# 由 app.py 在 lifespan 中设置
bridge = None       # DashboardBridge
strategy = None     # Strategy 实例
strategy_task = None  # asyncio.Task


def init(b, s):
    """由 app.py lifespan 调用，注入 bridge 和 strategy"""
    global bridge, strategy
    bridge = b
    strategy = s


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    bridge.add_client(ws)

    # 发送历史数据 + 当前状态
    await bridge.send_history(ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")

            if action == "start":
                await handle_start(msg, ws)

            elif action == "stop":
                await handle_stop(ws)

            elif action == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bridge.remove_client(ws)


async def handle_start(msg: dict, ws: WebSocket):
    global strategy_task

    if strategy_task and not strategy_task.done():
        await ws.send_text(json.dumps({
            "type": "error",
            "data": {"msg": "策略已在运行中"},
        }))
        return

    dry_run = msg.get("dry_run", True)
    strategy.dry_run = dry_run
    strategy.trader.dry_run = dry_run   # 同步到 Trader，否则下单永远走模拟
    strategy.once = False

    # 重置策略状态以允许重新启动
    strategy.trader.last_trade_time = 0
    strategy.trader.position_count = 0

    bridge.set_status(running=True, dry_run=dry_run)
    await bridge.broadcast({
        "type": "status",
        "data": {"running": True, "dry_run": dry_run},
    })

    # 重置信号标志以允许新周期交易
    strategy.signal_given_this_period = False

    # 作为后台任务运行策略
    async def _run():
        try:
            await strategy.init()
            await strategy.run_loop()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await bridge.broadcast({
                "type": "log",
                "data": {"level": "ERROR", "msg": f"策略异常退出: {e}", "ts": ""},
            })
        finally:
            bridge.set_status(running=False)
            await bridge.broadcast({
                "type": "status",
                "data": {"running": False, "dry_run": strategy.dry_run},
            })

    strategy_task = asyncio.create_task(_run())


async def handle_stop(ws: WebSocket):
    global strategy_task

    if not strategy_task or strategy_task.done():
        await ws.send_text(json.dumps({
            "type": "error",
            "data": {"msg": "策略未在运行"},
        }))
        return

    strategy_task.cancel()
    try:
        await strategy_task
    except asyncio.CancelledError:
        pass

    bridge.set_status(running=False)
    await bridge.broadcast({
        "type": "status",
        "data": {"running": False, "dry_run": strategy.dry_run},
    })
