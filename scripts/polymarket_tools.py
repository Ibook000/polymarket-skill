#!/usr/bin/env python3
"""
Polymarket Skill - Nanobot Implementation
Provides prediction market data tools for nanobot.
"""

import json
import httpx
import asyncio
from typing import Any, List, Dict, Union, Optional

# API Configuration
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"

async def query_polymarket_markets(
    limit: int = 10,
    category: Optional[str] = None,
    active: bool = True
) -> str:
    """
    Query Polymarket markets with optional filtering.
    
    Args:
        limit: Number of markets to return (default: 10)
        category: Filter by category (Politics, Crypto, Sports, etc.)
        active: Only return active markets (default: True)
    
    Returns:
        Formatted string with market information
    """
    try:
        params = {
            "limit": limit,
            "active": str(active).lower()
        }
        if category:
            params["category"] = category
            
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GAMMA_API_BASE}/markets", params=params, timeout=10.0)
            response.raise_for_status()
            markets = response.json()
            
        if not markets:
            return "❌ No markets found."
            
        result = f"📊 **Top {min(limit, len(markets))} Polymarket Markets**"
        if category:
            result += f" (Category: {category})"
        result += "\n\n"
        
        for i, market in enumerate(markets[:limit], 1):
            question = market.get('question', 'N/A')
            outcomes = json.loads(market.get('outcomes', '[]'))
            prices = json.loads(market.get('outcomePrices', '[]'))
            volume = market.get('volumeNum', 0)
            category_name = market.get('category', 'Unknown')
            
            # Format prices as percentages
            price_str = ""
            if outcomes and prices:
                for outcome, price in zip(outcomes, prices):
                    if price and float(price) > 0:
                        price_pct = float(price) * 100
                        price_str += f"{outcome}: {price_pct:.1f}% | "
                price_str = price_str.rstrip(" | ")
            
            result += f"{i}. **{question}**\n"
            if price_str:
                result += f"   📈 {price_str}\n"
            result += f"   💰 Volume: ${volume:,.0f} | 🏷️ {category_name}\n\n"
            
        return result.strip()
        
    except Exception as e:
        return f"❌ Failed to fetch Polymarket markets: {str(e)}"

async def get_polymarket_market_by_id(market_id: str) -> str:
    """
    Get detailed information for a specific market by ID.
    
    Args:
        market_id: Market ID (numeric string)
    
    Returns:
        Formatted string with market details
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GAMMA_API_BASE}/markets/{market_id}", timeout=10.0)
            response.raise_for_status()
            market = response.json()
            
        question = market.get('question', 'N/A')
        description = market.get('description', 'No description available.')
        outcomes = json.loads(market.get('outcomes', '[]'))
        prices = json.loads(market.get('outcomePrices', '[]'))
        volume = market.get('volumeNum', 0)
        liquidity = market.get('liquidityNum', 0)
        category = market.get('category', 'Unknown')
        end_date = market.get('endDateIso', 'N/A')
        active = market.get('active', False)
        best_bid = market.get('bestBid', 0)
        best_ask = market.get('bestAsk', 1)
        
        result = f"🎯 **{question}**\n\n"
        result += f"📝 {description}\n\n"
        
        if outcomes and prices:
            result += "📊 **Current Prices:**\n"
            for outcome, price in zip(outcomes, prices):
                if price:
                    price_pct = float(price) * 100
                    result += f"   • {outcome}: **{price_pct:.2f}%**\n"
        
        result += f"\n💰 **Volume:** ${volume:,.0f}\n"
        result += f"💧 **Liquidity:** ${liquidity:,.0f}\n"
        result += f"🏷️ **Category:** {category}\n"
        result += f"📅 **End Date:** {end_date}\n"
        result += f"✅ **Status:** {'Active' if active else 'Closed'}\n"
        
        # Add orderbook info if available
        if best_bid and best_ask:
            spread = best_ask - best_bid
            result += f"📈 **Best Bid/Ask:** {best_bid:.4f} / {best_ask:.4f} (Spread: {spread:.6f})\n"
        
        return result
        
    except Exception as e:
        return f"❌ Failed to fetch market details: {str(e)}"

async def get_polymarket_categories() -> str:
    """
    Get available market categories.
    
    Returns:
        Formatted string with categories
    """
    try:
        # Get some markets to extract categories
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GAMMA_API_BASE}/markets?limit=50", timeout=10.0)
            response.raise_for_status()
            markets = response.json()
            
        categories = set()
        for market in markets:
            cat = market.get('category')
            if cat:
                categories.add(cat)
                
        if not categories:
            return "❌ No categories found."
            
        result = "🏷️ **Available Polymarket Categories:**\n\n"
        for cat in sorted(categories):
            result += f"• {cat}\n"
            
        return result
        
    except Exception as e:
        return f"❌ Failed to fetch categories: {str(e)}"

# Main function aliases for easy calling
def query_polymarket_markets_sync(*args, **kwargs):
    return asyncio.run(query_polymarket_markets(*args, **kwargs))

def get_polymarket_market_by_id_sync(*args, **kwargs):
    return asyncio.run(get_polymarket_market_by_id(*args, **kwargs))

def get_polymarket_categories_sync(*args, **kwargs):
    return asyncio.run(get_polymarket_categories(*args, **kwargs))