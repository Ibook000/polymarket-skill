# Polymarket Trading Assistant

Quick reference for Polymarket BTC trading. For full driver, see `/run-polymarket`.

## Quick Commands

```bash
# Check status
python .claude/skills/run-polymarket/driver.py status

# Get BTC price
python .claude/skills/run-polymarket/driver.py price

# Get market info
python .claude/skills/run-polymarket/driver.py market

# Run strategy (simulation)
python .claude/skills/run-polymarket/driver.py once --dry-run

# Run strategy (live)
python .claude/skills/run-polymarket/driver.py once
```

## Order Management

```bash
# Buy
python .claude/skills/run-polymarket/driver.py buy --token-id <ID> --price 0.50 --size 10

# Sell
python .claude/skills/run-polymarket/driver.py sell --token-id <ID> --price 0.95 --size 10

# Cancel
python .claude/skills/run-polymarket/driver.py cancel --order-id <ID>

# Cancel all
python .claude/skills/run-polymarket/driver.py cancel-all --token-id <ID>
```

## Environment

Requires `.env` with `PRIVATE_KEY` and `POLYMARKET_FUNDER`.
