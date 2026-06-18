# Polymarket BTC 交易机器人

[![AI Agent Skill](https://img.shields.io/badge/AI%20Agent-Skill-blue)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-brightgreen)](https://claude.ai/code)
[![Hermes](https://img.shields.io/badge/Hermes-Compatible-brightgreen)]()
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-brightgreen)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![Polymarket SDK](https://img.shields.io/badge/Polymarket-PY%20SDK-orange)](https://github.com/Polymarket/py-sdk)

基于 [Polymarket Python SDK](https://github.com/Polymarket/py-sdk) 最新版的 BTC 5分钟预测市场自动交易系统。内置 AI Agent 技能，支持 Claude Code / Hermes / OpenClaw 等 agent 直接调用。

## 特点

- 🆕 **最新 SDK** — 使用 Polymarket 官方 [py-sdk](https://github.com/Polymarket/py-sdk)（beta），非旧版 CLOB 客户端
- 🤖 **Agent 技能** — 内置 `.claude/skills/` 技能，支持 Claude Code / Hermes / OpenClaw
- 📊 **自带策略** — 内置 BTC 5分钟均值回归策略，开箱即用
- 🛡️ **风控管理** — 仓位限制、冷却时间、模拟模式

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件：

```env
PRIVATE_KEY=0x你的私钥
POLYMARKET_FUNDER=0x你的钱包地址
```

### 3. 模拟测试

```bash
python btc5m_strategy.py --dry-run
```

### 4. 实盘交易

```bash
python btc5m_strategy.py
```

## Agent 技能使用

本项目自带技能，可直接被 AI agent 调用。

### 安装技能

**方式一：克隆整个仓库（推荐）**

```bash
git clone https://github.com/Ibook000/polymarket-skill.git
cd polymarketv2
pip install -r requirements.txt
```

然后在 AI agent 中打开此目录，技能会自动被识别。

**方式二：复制技能文件到已有项目**

```bash
# 创建技能目录
mkdir -p .claude/skills/run-polymarket

# 复制技能文件
cp /path/to/polymarketv2/.claude/skills/polymarket.md .claude/skills/
cp /path/to/polymarketv2/.claude/skills/run-polymarket/SKILL.md .claude/skills/run-polymarket/
cp /path/to/polymarketv2/.claude/skills/run-polymarket/driver.py .claude/skills/run-polymarket/
```

**方式三：使用 AI agent 安装**

在 Claude Code / Hermes / OpenClaw 中运行：

```
请帮我安装 polymarket 交易技能，技能文件在：
- .claude/skills/polymarket.md
- .claude/skills/run-polymarket/SKILL.md
- .claude/skills/run-polymarket/driver.py
```

### 技能结构

```
.claude/skills/
├── polymarket.md              # 快速参考
└── run-polymarket/
    ├── SKILL.md               # 技能文档
    └── driver.py              # 驱动脚本
```

### 激活技能

| Agent | 命令 | 说明 |
|-------|------|------|
| Claude Code | `/run-polymarket` | 加载完整驱动 |
| Claude Code | `/polymarket` | 加载快速参考 |
| Hermes | `/run-polymarket` | 加载完整驱动 |
| OpenClaw | `/run-polymarket` | 加载完整驱动 |

### 驱动命令

```bash
# 状态查询
python .claude/skills/run-polymarket/driver.py status      # 机器人状态
python .claude/skills/run-polymarket/driver.py price       # BTC价格
python .claude/skills/run-polymarket/driver.py market      # 当前市场

# 策略运行
python .claude/skills/run-polymarket/driver.py once --dry-run   # 模拟运行一次
python .claude/skills/run-polymarket/driver.py once             # 实盘运行一次
python .claude/skills/run-polymarket/driver.py run --dry-run    # 持续模拟
python .claude/skills/run-polymarket/driver.py run              # 持续实盘

# 订单管理
python .claude/skills/run-polymarket/driver.py buy --token-id <ID> --price 0.50 --size 10
python .claude/skills/run-polymarket/driver.py sell --token-id <ID> --price 0.95 --size 10
python .claude/skills/run-polymarket/driver.py cancel --order-id <ID>
python .claude/skills/run-polymarket/driver.py cancel-all --token-id <ID>
python .claude/skills/run-polymarket/driver.py orders --condition-id <ID>
python .claude/skills/run-polymarket/driver.py order --order-id <ID>
```

### 自然语言交互示例

激活技能后，可用自然语言指令：

```
"查看我的订单"
"买入10份 价格0.50"
"取消所有订单"
"BTC现在什么价格"
"启动模拟交易"
"查看当前市场信息"
"运行一次策略看看信号"
```

## CLI 直接使用

不通过 AI agent 也可直接使用：

```bash
# 策略控制
python btc5m_strategy.py              # 实盘交易
python btc5m_strategy.py --dry-run    # 模拟模式
python btc5m_strategy.py --once       # 只检查一次

# 订单管理
python place_order.py buy --token-id <TOKEN_ID> --price 0.50 --size 10
python place_order.py sell --token-id <TOKEN_ID> --price 0.95 --size 10
python place_order.py cancel --order-id <ORDER_ID>
python place_order.py cancel-all --token-id <TOKEN_ID>
python place_order.py list --condition-id <CONDITION_ID>
python place_order.py get --order-id <ORDER_ID>
```

## 策略逻辑

**市场格式**：`btc-updown-5m-{timestamp}`（5分钟周期）

**交易信号**：
- BTC 下跌 ≥2基点 + UP 赔率 >50% → 买 YES（均值回归）
- BTC 上涨 ≥2基点 + DOWN 赔率 >50% → 买 NO（均值回归）

**风控参数**：
- 最大持仓：100 份额
- 下单冷却：60 秒
- 每单份额：10

## 项目结构

```
├── btc5m_strategy.py              # 策略主引擎
├── place_order.py                 # 下单模块
├── requirements.txt               # 依赖
├── .env                           # 环境配置（已忽略）
├── .claude/
│   └── skills/
│       ├── polymarket.md          # 快速参考技能
│       └── run-polymarket/        # 完整驱动技能
│           ├── SKILL.md           # 技能文档
│           └── driver.py          # 驱动脚本
└── doc/
    └── python.md                  # Polymarket SDK 文档
```

## 依赖

- [polymarket-client](https://github.com/Polymarket/py-sdk) — Polymarket 官方 Python SDK（beta）
- py-clob-client — 旧版 CLOB 客户端（兼容）
- requests — HTTP 客户端
- python-dotenv — 环境变量管理
- websockets — 实时数据流
- fastapi + uvicorn — Web UI（可选）

## 安全提示

⚠️ **非模拟模式会使用真实资金交易**

- 务必先用 `--dry-run` 测试
- 不要提交 `.env` 文件
- 定期检查持仓
- 从小额开始

## 许可证

MIT

## 链接

- [Polymarket](https://polymarket.com)
- [Polymarket Python SDK](https://github.com/Polymarket/py-sdk)
- [Polymarket 文档](https://docs.polymarket.com)
- [Claude Code](https://claude.ai/code)
