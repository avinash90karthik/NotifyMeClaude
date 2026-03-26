# Silver Hawk Trading

AI-powered trading analysis and price alerts via Telegram. Built with Claude Code and yfinance.

## What It Does

- **Multi-Agent Analysis:** 4-step pipeline (data collection, bull/bear debate, judge verdict, trading card) for any stock or commodity
- **LONG & SHORT Signals:** Scorecard-based evaluation ensures SHORT trades are treated equally
- **3-Step KO Calculation:** ATR-based + chart-support combined, asset-class adjusted (Large Cap 2x, Mid/Small 2.5x, Commodities 3x)
- **Risk Management:** 10% max per trade, 40% max simultaneous risk, 60% max sector concentration
- **Portfolio Tracking:** `memory/portfolio.md` as single source of truth — updated after every analysis and trade
- **Correlation Check:** Reads open positions from `memory/portfolio.md` before every new trade
- **Time-Stops:** Halve after 3 days without +5%, close after 5 days sideways, secure 50% before earnings
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
> /analyse-stock SYMBOL
```

Full setup guide: **[ONBOARDING.md](ONBOARDING.md)** (EN) | **[ONBOARDING_DE.md](ONBOARDING_DE.md)** (DE)

## Requirements

- **Claude Pro** ($20/month) - for Claude Code
- **Telegram** (free) - create a bot via @BotFather
- **GitHub Actions** (free) - automated price alerts
- **yfinance** (free) - all market data

No database required. Portfolio state lives in `memory/portfolio.md`.

## Architecture

```
You (Claude Code)
├── /analyse-stock SYMBOL         → 4-step analysis → Telegram (text + chart photo)
├── python3 browse_stocks.py     → View watchlist
└── python3 admin_stocks.py add SYMBOL ...  → Manage watchlist

GitHub Actions (automatic)
├── watchlist_check.yml (2x daily)        → Top LONG/SHORT from watchlist → Telegram
├── morning_screener.yml (08:00 CET)      → LONG/SHORT scoring, top picks → Telegram
├── portfolio_check.yml (3x daily)        → RSI alerts for positions + watchlist
└── reddit_gems.yml (07:00 CET)           → Reddit trending stocks → Telegram

Local State
└── memory/portfolio.md                   → Open positions, stops, P&L, analysis log
```

## Analysis Pipeline

```
/analyse-stock SYMBOL
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
| `morning_screener.py` | Pre-market LONG/SHORT screener, scores 500+ stocks |
| `watchlist_check.py` | 2x daily scan of personal watchlist with v4 scoring |
| `portfolio_check.py` | RSI alerts for positions + watchlist (3x daily via GitHub Actions) |
| `preopen_check.py` | Pre-open verdict: buy NOW or WAIT? Pattern-based |
| `reddit_gems.py` | Daily Reddit trending stocks via ApeWisdom API |
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
| `watchlist_check.yml` | 07:30 + 21:15 CET (weekdays) | Top 5 LONG/SHORT from personal watchlist |
| `morning_screener.yml` | 08:00 CET (weekdays) | LONG/SHORT scoring, top picks |
| `portfolio_check.yml` | 3x daily (08:00, 15:00, 21:00 CET) | RSI alerts, stop/KO proximity |
| `reddit_gems.yml` | 07:00 CET (weekdays) | Reddit trending stocks via ApeWisdom |
| `reflect.yml` | Friday 20:00 CET | Weekly trade statistics and patterns |

Secrets needed: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Privacy

Everything is completely private:
- Your own Telegram bot
- No cloud database — state lives in your local `memory/portfolio.md`
- Your own GitHub Actions
- No shared data, no tracking, no accounts

## License

Personal use. Fork and customize for your own trading setup.
