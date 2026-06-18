#!/usr/bin/env python3
"""
Polymarket Trading Bot Driver

Provides programmatic access to the trading bot for Claude Code agents.
Usage: python driver.py <command> [options]

Commands:
  status      - Show bot status and current market
  run         - Run strategy (use --dry-run for simulation)
  once        - Single check then exit
  orders      - List open orders
  order       - Get order details
  buy         - Place buy order
  sell        - Place sell order
  cancel      - Cancel order
  cancel-all  - Cancel all orders for token
  price       - Get current BTC price
  market      - Get current market info
"""

import asyncio
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def now_beijing() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=8)


def log(msg: str):
    ts = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


async def cmd_status():
    """Show bot status"""
    import requests

    # Get BTC price
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price",
                          params={"symbol": "BTCUSDT"}, timeout=5)
        btc_price = float(resp.json()["price"])
    except Exception as e:
        btc_price = f"Error: {e}"

    # Get current market slug
    import time
    ts = int(time.time())
    interval_ts = (ts // 300) * 300
    slug = f"btc-updown-5m-{interval_ts}"

    print(json.dumps({
        "timestamp": now_beijing().isoformat(),
        "btc_price": btc_price,
        "current_market_slug": slug,
        "env_configured": os.path.exists(PROJECT_ROOT / ".env"),
    }, indent=2, ensure_ascii=False))


async def cmd_run(dry_run: bool = False):
    """Run the strategy"""
    args = [sys.executable, str(PROJECT_ROOT / "btc5m_strategy.py")]
    if dry_run:
        args.append("--dry-run")
    log(f"Starting strategy: {' '.join(args)}")
    proc = subprocess.Popen(args, cwd=str(PROJECT_ROOT))
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        log("Strategy stopped")


async def cmd_once(dry_run: bool = False):
    """Single check"""
    args = [sys.executable, str(PROJECT_ROOT / "btc5m_strategy.py"), "--once"]
    if dry_run:
        args.append("--dry-run")
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_orders(condition_id: str = None):
    """List open orders"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "list"]
    if condition_id:
        args.extend(["--condition-id", condition_id])
    else:
        # Without condition_id, we can't list - show help
        print("Usage: driver.py orders --condition-id <CONDITION_ID>")
        print("Get condition_id from market data")
        return 1
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_order(order_id: str):
    """Get order details"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "get", "--order-id", order_id]
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_buy(token_id: str, price: float, size: float):
    """Place buy order"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "buy",
            "--token-id", token_id, "--price", str(price), "--size", str(size)]
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_sell(token_id: str, price: float, size: float):
    """Place sell order"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "sell",
            "--token-id", token_id, "--price", str(price), "--size", str(size)]
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_cancel(order_id: str):
    """Cancel order"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "cancel", "--order-id", order_id]
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_cancel_all(token_id: str):
    """Cancel all orders for token"""
    args = [sys.executable, str(PROJECT_ROOT / "place_order.py"), "cancel-all", "--token-id", token_id]
    result = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


async def cmd_price():
    """Get current BTC price"""
    import requests
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price",
                          params={"symbol": "BTCUSDT"}, timeout=5)
        data = resp.json()
        print(json.dumps({
            "symbol": "BTCUSDT",
            "price": float(data["price"]),
            "timestamp": now_beijing().isoformat(),
        }, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def cmd_market():
    """Get current market info"""
    import requests
    import time

    ts = int(time.time())
    interval_ts = (ts // 300) * 300
    slug = f"btc-updown-5m-{interval_ts}"

    try:
        resp = requests.get(f"https://gamma-api.polymarket.com/markets/slug/{slug}", timeout=20)
        if resp.ok:
            market = resp.json()
            print(json.dumps({
                "slug": slug,
                "question": market.get("question"),
                "condition_id": market.get("conditionId"),
                "clob_token_ids": json.loads(market.get("clobTokenIds", "[]")),
                "active": market.get("active"),
                "closed": market.get("closed"),
            }, indent=2, ensure_ascii=False))
        else:
            print(f"Market not found: {slug}")
            print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Polymarket Trading Bot Driver")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser("status", help="Show bot status")

    # run
    p = sub.add_parser("run", help="Run strategy")
    p.add_argument("--dry-run", action="store_true")

    # once
    p = sub.add_parser("once", help="Single check")
    p.add_argument("--dry-run", action="store_true")

    # orders
    p = sub.add_parser("orders", help="List open orders")
    p.add_argument("--condition-id", required=True)

    # order
    p = sub.add_parser("order", help="Get order details")
    p.add_argument("--order-id", required=True)

    # buy
    p = sub.add_parser("buy", help="Place buy order")
    p.add_argument("--token-id", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--size", type=float, required=True)

    # sell
    p = sub.add_parser("sell", help="Place sell order")
    p.add_argument("--token-id", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--size", type=float, required=True)

    # cancel
    p = sub.add_parser("cancel", help="Cancel order")
    p.add_argument("--order-id", required=True)

    # cancel-all
    p = sub.add_parser("cancel-all", help="Cancel all orders")
    p.add_argument("--token-id", required=True)

    # price
    sub.add_parser("price", help="Get BTC price")

    # market
    sub.add_parser("market", help="Get current market")

    args = parser.parse_args()

    cmd_map = {
        "status": cmd_status,
        "run": lambda: cmd_run(args.dry_run),
        "once": lambda: cmd_once(args.dry_run),
        "orders": lambda: cmd_orders(args.condition_id),
        "order": lambda: cmd_order(args.order_id),
        "buy": lambda: cmd_buy(args.token_id, args.price, args.size),
        "sell": lambda: cmd_sell(args.token_id, args.price, args.size),
        "cancel": lambda: cmd_cancel(args.order_id),
        "cancel-all": lambda: cmd_cancel_all(args.token_id),
        "price": cmd_price,
        "market": cmd_market,
    }

    result = asyncio.run(cmd_map[args.command]())
    sys.exit(result or 0)


if __name__ == "__main__":
    main()
