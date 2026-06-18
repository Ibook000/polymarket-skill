#!/usr/bin/env python3
"""
Polymarket 下单模块 - 基于统一 Python SDK (polymarket-client)

作为模块调用:
    import asyncio
    from place_order import create_client, place_order, cancel_order, cancel_all_orders, list_orders, get_order

    async def main():
        async with await create_client() as client:
            # 下单
            resp = await place_order(client, token_id="xxx", side="BUY", price=0.05, size=10)
            print(resp.ok, resp.order_id)

            # 撤单
            resp = await cancel_order(client, order_id="xxx")

            # 批量撤单
            resp = await cancel_all_orders(client, token_id="xxx")

            # 查看挂单
            orders = await list_orders(client, condition_id="xxx")

            # 订单详情
            order = await get_order(client, order_id="xxx")

    asyncio.run(main())

作为 CLI:
    python place_order.py buy --token-id <TOKEN_ID> --price 0.05 --size 10
    python place_order.py sell --token-id <TOKEN_ID> --price 0.95 --size 10
    python place_order.py cancel --order-id <ORDER_ID>
    python place_order.py cancel-all --token-id <TOKEN_ID>
    python place_order.py list --condition-id <CONDITION_ID>
    python place_order.py get --order-id <ORDER_ID>
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
_PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_DIR / ".env", override=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 公开 API — 可被其他模块 import 调用
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def create_client(private_key: str | None = None, wallet: str | None = None):
    """
    创建已认证的 AsyncSecureClient（async context manager）。

    用法:
        async with await create_client() as client:
            ...

    Args:
        private_key: 私钥，默认从 .env 读取
        wallet: 钱包地址，默认从 .env 读取（可选，SDK 自动派生）
    """
    from polymarket import AsyncSecureClient

    key = private_key or os.environ.get("POLYMARKET_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
    if not key:
        raise ValueError("请设置 PRIVATE_KEY 或 POLYMARKET_PRIVATE_KEY")

    w = wallet or os.environ.get("POLYMARKET_WALLET_ADDRESS")
    client = await AsyncSecureClient.create(private_key=key, wallet=w)
    return client


async def place_order(client, token_id: str, side: str, price: float | str, size: float | str):
    """
    下限价单 (limit order)。

    Args:
        client: AsyncSecureClient 实例
        token_id: Token ID
        side: "BUY" 或 "SELL"
        price: 价格 (0-1)
        size: 数量

    Returns:
        OrderResponse — 检查 response.ok 判断是否成功，response.order_id 获取订单ID
    """
    response = await client.place_limit_order(
        token_id=token_id,
        side=side,
        price=str(price),
        size=str(size),
    )
    return response


async def cancel_order(client, order_id: str):
    """
    撤销指定订单。

    Args:
        client: AsyncSecureClient 实例
        order_id: 订单 ID

    Returns:
        CancelOrdersResponse — response.canceled 为已撤销的订单ID列表
    """
    return await client.cancel_order(order_id=order_id)


async def cancel_all_orders(client, token_id: str):
    """
    撤销某 token 的所有订单。

    Args:
        client: AsyncSecureClient 实例
        token_id: Token ID

    Returns:
        CancelOrdersResponse — response.canceled 为已撤销的订单ID列表
    """
    return await client.cancel_market_orders(token_id=token_id)


async def list_orders(client, condition_id: str | None = None):
    """
    查看当前挂单。

    Args:
        client: AsyncSecureClient 实例
        condition_id: 市场 condition_id（可选，不传则查所有）

    Returns:
        list[OpenOrder]
    """
    from polymarket import CtfConditionId

    market = CtfConditionId(condition_id) if condition_id else None
    paginator = client.list_open_orders(market=market)

    all_orders = []
    async for page in paginator:
        all_orders.extend(page.items)
    return all_orders


async def get_order(client, order_id: str):
    """
    查看订单详情。

    Args:
        client: AsyncSecureClient 实例
        order_id: 订单 ID

    Returns:
        OpenOrder
    """
    return await client.get_order(order_id=order_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI 入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _cmd_buy(args) -> int:
    async with await create_client() as client:
        resp = await place_order(client, args.token_id, "BUY", args.price, args.size)
        if resp.ok:
            print(f"下单成功 (BUY): order_id={resp.order_id}")
            return 0
        else:
            print(f"下单失败: {getattr(resp, 'code', 'UNKNOWN')} - {getattr(resp, 'message', '')}", file=sys.stderr)
            return 1


async def _cmd_sell(args) -> int:
    async with await create_client() as client:
        resp = await place_order(client, args.token_id, "SELL", args.price, args.size)
        if resp.ok:
            print(f"下单成功 (SELL): order_id={resp.order_id}")
            return 0
        else:
            print(f"下单失败: {getattr(resp, 'code', 'UNKNOWN')} - {getattr(resp, 'message', '')}", file=sys.stderr)
            return 1


async def _cmd_cancel(args) -> int:
    async with await create_client() as client:
        resp = await cancel_order(client, args.order_id)
        print(f"撤单成功: canceled={resp.canceled}")
        return 0


async def _cmd_cancel_all(args) -> int:
    async with await create_client() as client:
        resp = await cancel_all_orders(client, args.token_id)
        print(f"批量撤单成功: canceled={resp.canceled}")
        return 0


async def _cmd_list(args) -> int:
    async with await create_client() as client:
        orders = await list_orders(client, args.condition_id)
        if not orders:
            print("当前没有挂单")
            return 0
        print(f"共 {len(orders)} 个挂单:")
        for o in orders:
            print(f"  [{o.id[:16]}...] {o.side} {o.original_size}@{o.price}  token={o.token_id}")
        return 0


async def _cmd_get(args) -> int:
    async with await create_client() as client:
        order = await get_order(client, args.order_id)
        print("订单详情:")
        for field in ("id", "side", "price", "original_size", "size_matched",
                       "token_id", "status", "created_at"):
            val = getattr(order, field, None)
            if val is not None:
                print(f"  {field}: {val}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket 下单工具 (基于 polymarket-client SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("buy", help="买入 (BUY limit)")
    p.add_argument("--token-id", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--size", type=float, required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_buy(a)))

    p = sub.add_parser("sell", help="卖出 (SELL limit)")
    p.add_argument("--token-id", required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--size", type=float, required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_sell(a)))

    p = sub.add_parser("cancel", help="撤单")
    p.add_argument("--order-id", required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_cancel(a)))

    p = sub.add_parser("cancel-all", help="批量撤单 (按 token)")
    p.add_argument("--token-id", required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_cancel_all(a)))

    p = sub.add_parser("list", help="查看所有挂单")
    p.add_argument("--condition-id", required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_list(a)))

    p = sub.add_parser("get", help="查看订单详情")
    p.add_argument("--order-id", required=True)
    p.set_defaults(func=lambda a: asyncio.run(_cmd_get(a)))

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
