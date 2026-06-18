# CLAUDE.md

This file provides guidance to AI agents (Claude Code / Hermes / OpenClaw) when working with code in this repository.

## Project

Polymarket BTC 5-minute prediction market automated trading system.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure (.env)
PRIVATE_KEY=0x...
POLYMARKET_FUNDER=0x...

# Test
python btc5m_strategy.py --dry-run

# Run
python btc5m_strategy.py
```

## Architecture

```
btc5m_strategy.py      # Strategy engine (entry point)
  └── place_order.py   # Order module (SDK wrapper)
        └── polymarket-client SDK
```

## AI Agent Skills

Type `/run-polymarket` to load the full driver skill.

### Driver Commands

```bash
# Status & Info
python .claude/skills/run-polymarket/driver.py status
python .claude/skills/run-polymarket/driver.py price
python .claude/skills/run-polymarket/driver.py market

# Strategy
python .claude/skills/run-polymarket/driver.py once --dry-run
python .claude/skills/run-polymarket/driver.py once
python .claude/skills/run-polymarket/driver.py run --dry-run
python .claude/skills/run-polymarket/driver.py run

# Orders
python .claude/skills/run-polymarket/driver.py buy --token-id <ID> --price 0.50 --size 10
python .claude/skills/run-polymarket/driver.py sell --token-id <ID> --price 0.95 --size 10
python .claude/skills/run-polymarket/driver.py cancel --order-id <ID>
python .claude/skills/run-polymarket/driver.py cancel-all --token-id <ID>
python .claude/skills/run-polymarket/driver.py orders --condition-id <ID>
python .claude/skills/run-polymarket/driver.py order --order-id <ID>
```

## Key APIs

- Binance: BTC price data
- Polymarket Gamma: Market discovery
- Polymarket CLOB: Order execution
