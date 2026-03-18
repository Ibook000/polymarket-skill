# Polymarket Skill for Nanobot

![Prediction Markets](https://img.shields.io/badge/Prediction%20Markets-Polymarket-blue)

A nanobot skill that provides real-time prediction market data from Polymarket, the world's largest prediction market platform.

## Features

- 🔍 **Market Discovery**: Browse and search active prediction markets
- 💰 **Real-time Prices**: Get current probability prices for market outcomes
- 📊 **Market Analytics**: View trading volume, liquidity, and market details
- 🏷️ **Category Filtering**: Filter markets by categories (Politics, Crypto, Sports, etc.)
- 📈 **Orderbook Data**: Access bid/ask spreads and market depth information

## Installation

### For Nanobot Users

1. Clone this repository to your nanobot skills directory:
   ```bash
   git clone https://github.com/Ibook000/polymarket-skill.git ~/.nanobot/workspace/skills/polymarket
   ```

2. Install required dependencies:
   ```bash
   pip install httpx
   ```

3. Restart your nanobot gateway service.

### Configuration

Create a `config.json` file in the skill directory (optional):

```json
{
  "max_retries": 3,
  "retry_delay": 1,
  "timeout": 10,
  "default_limit": 5
}
```

## Usage Examples

In your nanobot conversation, simply ask:

- "显示最新的 Polymarket 预测市场"
- "查看特定市场的详情" (需要市场ID)
- "有哪些 Polymarket 分类？"

The skill will automatically handle the requests and provide formatted responses.

## API Sources

- **Markets & Events**: Gamma API (`https://gamma-api.polymarket.com`)
- **Prices & Orderbook**: CLOB API (`https://clob.polymarket.com`)  
- **Analytics**: Data API (`https://data-api.polymarket.com`)

## Requirements

- Python 3.8+
- httpx library
- Nanobot AI assistant

## License

MIT License - See [LICENSE](LICENSE) for details.

## Author

Created by [Ibook000](https://github.com/Ibook000)

---

*This skill is designed specifically for the [nanobot AI assistant](https://github.com/nanobot-ai/nanobot).*