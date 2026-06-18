---
name: run-polymarket
description: Run Polymarket BTC trading bot, check orders, place trades, monitor strategy
---

# Polymarket Trading Bot

Drive the Polymarket BTC 5-minute prediction market trading bot.

**Driver**: `.claude/skills/run-polymarket/driver.py`

## Prerequisites

```bash
pip install -r requirements.txt
```

Configure `.env`:
```
PRIVATE_KEY=0x...
POLYMARKET_FUNDER=0x...
```

## Quick Reference

```bash
# Status check
python .claude/skills/run-polymarket/driver.py status

# Get BTC price
python .claude/skills/run-polymarket/driver.py price

# Get current market
python .claude/skills/run-polymarket/driver.py market

# Run strategy (simulation)
python .claude/skills/run-polymarket/driver.py once --dry-run

# Run strategy (live)
python .claude/skills/run-polymarket/driver.py once

# Continuous trading (live)
python .claude/skills/run-polymarket/driver.py run

# Continuous trading (simulation)
python .claude/skills/run-polymarket/driver.py run --dry-run
```

## Order Management

```bash
# List orders (requires condition_id from market)
python .claude/skills/run-polymarket/driver.py orders --condition-id <CONDITION_ID>

# Get order details
python .claude/skills/run-polymarket/driver.py order --order-id <ORDER_ID>

# Buy
python .claude/skills/run-polymarket/driver.py buy --token-id <TOKEN_ID> --price 0.50 --size 10

# Sell
python .claude/skills/run-polymarket/driver.py sell --token-id <TOKEN_ID> --price 0.95 --size 10

# Cancel order
python .claude/skills/run-polymarket/driver.py cancel --order-id <ORDER_ID>

# Cancel all for token
python .claude/skills/run-polymarket/driver.py cancel-all --token-id <TOKEN_ID>
```

## Workflow: Check Market and Trade

```bash
# 1. Get current market info
python .claude/skills/run-polymarket/driver.py market
# Returns: slug, condition_id, clob_token_ids

# 2. Check BTC price
python .claude/skills/run-polymarket/driver.py price

# 3. Run strategy once to see signals
python .claude/skills/run-polymarket/driver.py once --dry-run

# 4. If signal looks good, place order
python .claude/skills/run-polymarket/driver.py buy \
  --token-id <YES_TOKEN_ID> \
  --price 0.50 \
  --size 10
```

## Strategy Parameters

Edit `btc5m_strategy.py` Config class:

| Parameter | Default | Description |
|-----------|---------|-------------|
| PRICE_CHANGE_BPS | 2 | Price change threshold (basis points) |
| UP_ODDS_THRESHOLD | 0.50 | UP odds trigger |
| DOWN_ODDS_THRESHOLD | 0.50 | DOWN odds trigger |
| ORDER_SIZE | 10 | Shares per order |
| MAX_POSITION | 100 | Max position size |
| COOLDOWN_SEC | 60 | Seconds between trades |

## Gotchas

- Market slug changes every 5 minutes: `btc-updown-5m-{timestamp}`
- `condition_id` and `token_ids` change with each new market
- Always test with `--dry-run` before live trading
- The bot uses Beijing time (UTC+8) for logging
