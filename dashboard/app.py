"""
BTC 5m Strategy Dashboard — FastAPI 应用入口

启动方式:
  uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 确保项目根目录在 sys.path 中（以便导入 btc5m_strategy）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from btc5m_strategy import Strategy, _log_sink  # noqa: E402
import btc5m_strategy  # noqa: E402
from dashboard.bridge import DashboardBridge  # noqa: E402
from dashboard import ws_handler  # noqa: E402

bridge = DashboardBridge()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化 Strategy，挂钩日志"""
    # 注入 log sink（不自动启动策略，等用户点击）
    strategy = Strategy(dry_run=True, on_event=bridge.on_event)
    btc5m_strategy._log_sink = bridge.on_log

    ws_handler.init(bridge, strategy)

    yield

    # 清理
    if ws_handler.strategy_task and not ws_handler.strategy_task.done():
        ws_handler.strategy_task.cancel()
        try:
            await ws_handler.strategy_task
        except asyncio.CancelledError:
            pass
    await strategy.trader.close()
    btc5m_strategy._log_sink = None


app = FastAPI(title="BTC 5m Strategy Dashboard", lifespan=lifespan)

# WebSocket 路由
app.include_router(ws_handler.router)

# 静态文件
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/status")
async def api_status():
    return {
        "running": bridge.running,
        "dry_run": bridge.dry_run,
        "price_count": len(bridge.price_history),
        "log_count": len(bridge.log_buffer),
        "signal_count": len(bridge.signals),
    }
