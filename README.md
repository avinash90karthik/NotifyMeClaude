# Silver Hawk Trading

AI-powered trading analysis and price alerts via Telegram. Built with Claude Code and yfinance.

## What It Does

- **Multi-Agent Analysis:** 4-step pipeline (data collection, bull/bear debate, judge verdict, trading card) for any stock or commodity
- **LONG & SHORT Signals:** Scorecard-based evaluation ensures SHORT trades are treated equally
- **3-Step KO Calculation:** ATR-based + chart-support combined, asset-class adjusted (Large Cap 2x, Mid/Small 2.5x, Commodities 3x)
- **Risk Management:** 10% max per trade, 40% max simultaneous risk, 60% max sector concentration
- **Portfolio Tracking:** `memory/portfolio.md` as single source of truth — updated after every analysis and trade
- **Correlation Check:** Reads open positions from `memory/portfolio.md` before every new trade
- **Time-Stops:** Auto-halve after 5 days sideways, close after 8 days, secure 50% before earnings
- **Price Alerts:** Telegram notifications on big moves, level crossings, and flash spikes
- **Portfolio Health Check:** 3x daily RSI alerts for all open positions and watchlist

## Quick Start

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Clone and configure
git clone https://github.com/YOUR_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude
cp .env.template .env    # Fill in your Telegram credentials

# Install dependencies
pip3 install yfinance numpy

# Run your first analysis
claude
> /analyse-stock AAPL
```

Full setup guide: **[ONBOARDING.md](ONBOARDING.md)** (DE) | **[ONBOARDING_EN.md](ONBOARDING_EN.md)** (EN)

## Requirements

- **Claude Pro** ($20/month) - for Claude Code
- **Telegram** (free) - create a bot via @BotFather
- **GitHub Actions** (free) - automated price alerts
- **yfinance** (free) - all market data

No database required. Portfolio state lives in `memory/portfolio.md`.

## Architecture

```
You (Claude Code)
├── /analyse-stock NVDA          → 4-step analysis → Telegram (text + chart photo)
├── python3 browse_stocks.py     → View watchlist
└── python3 admin_stocks.py add TSLA ...   → Manage watchlist

GitHub Actions (automatic)
├── tracker.yml (every 10 min)            → Price alerts → Telegram
└── portfolio_check.yml (3x daily)        → RSI alerts for positions + watchlist

Local State
└── memory/portfolio.md                   → Open positions, stops, P&L, analysis log
```

## Analysis Pipeline

```
/analyse-stock NVDA
```

| Step | What Happens |
|------|-------------|
| 1. Data Collection | yfinance prices, RSI, MACD, SMAs, ATR, short interest, news, correlation check, event calendar. Futures (SI=F, GC=F) use ETF proxy for RSI to avoid rollover distortion. |
| 2. Investment Debate | Bull vs Bear - 2 full rounds + LONG vs SHORT scorecard (6 criteria, /60) |
| 3. Judge & Risk | Verdict + confidence %, 3-step KO (ATR + chart + take further), position sizing in % of portfolio, time-stops |
| 4. Trading Card | Summary card + chart → Telegram message + chart photo. `memory/portfolio.md` updated. |

## Scripts

| Script | Purpose |
|--------|---------|
| `tracker_check.py` | Personal price alert config — customize SYMBOLS, ALERT_RULES, TRADING_ZONES |
| `tracker_check_template.py` | Template for new users to copy and customize |
| `portfolio_check.py` | RSI alerts for positions + watchlist (3x daily via GitHub Actions) |
| `morning_screener.py` | Pre-market LONG/SHORT screener, scores 500+ stocks |
| `send_telegram.py` | Send messages and photos to your Telegram bot |
| `browse_stocks.py` | View watchlist with prices, RSI, ratings |
| `admin_stocks.py` | Add/remove stocks, seed watchlist |
| `update_stocks.py` | Fetch latest prices (runs via GitHub Actions) |

## Environment

All secrets in `.env` (never committed to git):

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_BOT_USERNAME=...
YFINANCE_VENV=...        # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...          # Optional: path to chart generation script
CHART_OUTPUT_DIR=...      # Optional: path to chart output directory
```

## GitHub Actions

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `tracker.yml` | Every 10 min (market hours) | Price alerts via Telegram |
| `portfolio_check.yml` | 3x daily (08:00, 15:00, 21:00 CET) | RSI alerts, stop/KO proximity |
| `morning_screener.yml` | 08:00 CET (weekdays) | LONG/SHORT scoring, top picks |

Secrets needed: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Privacy

Everything is completely private:
- Your own Telegram bot
- No cloud database — state lives in your local `memory/portfolio.md`
- Your own GitHub Actions
- No shared data, no tracking, no accounts

## License

Personal use. Fork and customize for your own trading setup.
