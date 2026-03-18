---
name: polymarket
description: "Polymarket prediction market data tool - query markets, prices, and trading information from the world's largest prediction market platform."
user-invocable: true
metadata:
  version: 1.0.0
  emoji: "📊"
---

# Polymarket Skill

Query real-time prediction market data from Polymarket, the world's largest prediction market platform.

## Core Features

### 1. Market Discovery 🔍
- **List active markets**: Get current prediction markets with questions, categories, and prices
- **Search markets**: Find markets by keywords or topics
- **Market details**: Get detailed information about specific markets

### 2. Price & Orderbook Data 💰
- **Current prices**: Get real-time probability prices for markets
- **Orderbook depth**: View bid/ask spreads and liquidity
- **Price history**: Historical price movements and trends

### 3. Market Analytics 📈
- **Volume data**: Trading volume and open interest
- **Category overview**: Markets grouped by categories (Politics, Crypto, Sports, etc.)
- **Top markets**: Most active or highest volume markets

### 4. Event Information 📅
- **Event details**: Get information about prediction market events
- **Resolution status**: Check if markets have been resolved
- **End dates**: When markets will close and resolve

## Usage Examples

### List Active Markets
```python
# Get top 10 active markets
query_polymarket_markets(limit=10)

# Get markets by category
query_polymarket_markets(category="Politics", limit=5)
```

### Search Markets
```python
# Search for markets containing "Bitcoin"
search_polymarket_markets("Bitcoin")

# Search for election-related markets
search_polymarket_markets("election")
```

### Get Market Details
```python
# Get details for specific market by ID
get_polymarket_market_by_id("market-id-here")

# Get market by slug/name
get_polymarket_market_by_slug("will-trump-win-2024-election")
```

### Get Price Data
```python
# Get current prices for multiple markets
get_polymarket_prices(["market-id-1", "market-id-2"])

# Get orderbook for a market
get_polymarket_orderbook("market-id-here")
```

## API Endpoints Used

- **Gamma API** (`https://gamma-api.polymarket.com`): Markets, events, search, public data
- **CLOB API** (`https://clob.polymarket.com`): Orderbook, pricing, trading data
- **Data API** (`https://data-api.polymarket.com`): Volume, positions, analytics

## Data Sources

- **Markets & Events**: Gamma API (public, no authentication required)
- **Prices & Orderbook**: CLOB API (public endpoints available)
- **Analytics**: Data API (public, no authentication required)

## Notes

- **No authentication required** for most read operations
- **Real-time data**: All queries return live market data
- **Market IDs**: Use market ID or slug to identify specific markets
- **Categories**: Politics, Crypto, Sports, Entertainment, Business, etc.
- **Price format**: Prices are returned as probabilities (0.0 to 1.0) representing likelihood

## Example User Requests

**User**: "What are the top Polymarket prediction markets right now?"
**Call**: `query_polymarket_markets(limit=5)`

**User**: "Show me Bitcoin-related prediction markets"
**Call**: `search_polymarket_markets("Bitcoin")`

**User**: "What's the current price for Trump 2024 election market?"
**Call**: `get_polymarket_market_by_slug("will-trump-win-2024-election")`

**User**: "Get me the orderbook for the ETH price market"
**Call**: `get_polymarket_orderbook("eth-price-market-id")`