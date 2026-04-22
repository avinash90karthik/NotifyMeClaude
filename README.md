# Silver Hawk Trading

AI-powered trading analysis built with Claude Code and yfinance.

## What It Does

- **Multi-Agent Analysis:** 4-step pipeline (data collection, bull/bear debate, judge verdict, trading card) for any stock or commodity
- **LONG & SHORT Signals:** Scorecard-based evaluation ensures SHORT trades are treated equally
- **3-Step KO Calculation:** ATR-based + chart-support combined, asset-class adjusted (Large Cap 2x, Mid/Small 2.5x, Commodities 3x)
- **Risk Management:** 10% max per trade, 40% max simultaneous risk, 60% max sector concentration
- **Portfolio Tracking:** `memory/predictions.db` (SQLite) as single source of truth — updated after every analysis and trade
- **Correlation Check:** Reads open positions from `memory/predictions.db` before every new trade
- **Time-Stops:** Halve after 3 days without +5%, close after 5 days sideways, secure 50% before earnings

## Quick Start

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Clone and configure
git clone https://github.com/YOUR_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude
cp .env.template .env    # Optional paths only

# Install dependencies
pip3 install yfinance numpy

# Run your first analysis
claude
> Analysiere SYMBOL
```

Full setup guide: **[ONBOARDING.md](ONBOARDING.md)** (EN) | **[ONBOARDING_DE.md](ONBOARDING_DE.md)** (DE)

## Requirements

- **Claude Pro** ($20/month) - for Claude Code
- **yfinance** (free) - all market data

Portfolio state lives in `memory/predictions.db` (SQLite — auto-created on first use).

## Architecture

```
You (Claude Code)
├── "Analysiere SYMBOL"                       → pre-flight + 4-step analysis → terminal trading card
├── python3 scripts/prediction_db.py portfolio  → View positions, cash, slots
└── python3 scripts/collect_data.py SYMBOL      → Quick technical snapshot

Local State
└── memory/predictions.db                       → Open positions, stops, P&L, analysis log (SQLite)
```

## Analysis Pipeline

Tell Claude Code: **"Analysiere SYMBOL"** (or "Analyze SYMBOL"). The pipeline starts with a pre-flight check (`scripts/preflight_check.py`) and runs all four steps below — no shortcuts, no mini-versions.

| Step | What Happens |
|------|-------------|
| 0. Pre-Flight | `scripts/preflight_check.py` — real date/weekday/market-status, yfinance news (7d), mandatory Trump/Reddit/day-news/event searches, echo-back checklist. |
| 1. Data Collection | yfinance prices, RSI, MACD, SMAs, ATR, short interest, news, correlation check, event calendar. Futures (SI=F, GC=F) use ETF proxy for RSI to avoid rollover distortion. |
| 2. Investment Debate | Bull vs Bear - 2 full rounds + LONG vs SHORT scorecard (6 criteria, /60) |
| 3. Judge & Risk | Verdict + confidence %, 3-step KO (ATR + chart + take further), position sizing in % of portfolio, time-stops |
| 4. Trading Card | Summary card in terminal. `memory/predictions.db` updated with the analysis (always, even on HOLD). |

## Scripts

All CLI tools live under `scripts/`. Shared library code (indicators, scoring, risk audit, wavelet utilities) lives under `lib/` and is imported by the scripts — not invoked directly.

| Script | Purpose |
|--------|---------|
| `scripts/collect_data.py` | Full technical snapshot (price, RSI, MACD, ATR, SMAs, S/R, events) |
| `scripts/prediction_db.py` | Portfolio state + trade log + analysis record (SQLite) |
| `scripts/preopen_check.py` | Pre-open verdict: buy NOW or WAIT? Pattern-based |
| `scripts/preopen_backtest.py` | Backtest pre-open patterns on historical data |
| `scripts/backtest.py` | Validate v5 scoring against historical data |
| `scripts/preflight_check.py` | Date/market status + mandatory search-query banner |
| `scripts/indicator_context.py` | Per-stock RSI/BB/DistHigh band statistics + sigmoid adjust |
| `scripts/earnings_pattern.py` | Per-stock earnings-window historical behavior |
| `scripts/reversion_guard.py` | Per-stock LONG/SHORT reversion-edge check |

## Environment

Optional paths in `.env` (never committed to git):

```
YFINANCE_VENV=...        # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...          # Optional: path to chart generation script
CHART_OUTPUT_DIR=...      # Optional: path to chart output directory
```

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Prediction Fill | `prediction_fill.yml` | 22:15 CET (weekdays) | Fill real outcomes, analyze prediction quality |
| Tests | `tests.yml` | on push | pytest suite for critical fixes |

## Privacy

Everything is completely local:
- No cloud database — state lives in your local `memory/predictions.db` (SQLite)
- No shared data, no tracking, no accounts
- yfinance pulls public market data only

## License

Personal use. Fork and customize for your own trading setup.
