# Silver Hawk Trading - Project Guide

## Overview

Trading notification system built around a Telegram bot and a multi-agent analysis framework. All notifications, price alerts, and analysis results are delivered via Telegram.

Each user runs their own independent instance: own Telegram bot, own GitHub Actions. No database required — portfolio state lives in `memory/portfolio.md`. See `ONBOARDING.md` for setup instructions.

---

## TRADING STRATEGY v5

> Goal: +15% baseline / +30% stretch per month.
> When baseline is reached → become more conservative, not more aggressive.
> Full v5 rules: `memory/strategy_v5.md`

```
╔═══════════════════════════════════════════════════════════════╗
║  CORE STRATEGY v5 — ALWAYS FOLLOW!                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ENTRY (v5):                                                 ║
║  1. 60% SCOUT immediately on signal                          ║
║  2. 40% CONFIRMATION only when: next day green OR +5%        ║
║  3. No follow-up if Scout >10% up OR >10% down               ║
║  4. Event trades (Earnings/FOMC): 100% immediately           ║
║                                                               ║
║  EXITS:                                                       ║
║  5. 50% at +20% IMMEDIATELY OUT — no exceptions!             ║
║  6. Rest: trail stop to BE, then raise incrementally:        ║
║     +30% → stop +15% / +40% → stop +25% / +50% → stop +35% ║
║                                                               ║
║  STOPS (NOT tiered!):                                        ║
║  7. ONE stop for everything — NO negotiating!                ║
║  8. Stop ALWAYS set at purchase — no exceptions              ║
║                                                               ║
║  RULES:                                                      ║
║  9. MAX 3 open positions simultaneously                      ║
║  10. ≥60% confidence gate — NO exceptions, no "lottery"      ║
║  11. Pullbacks always come — patience pays off               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Hedge System

```
╔═══════════════════════════════════════════════════════════════╗
║  SITUATIONAL HEDGE — 3rd slot as protection                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  WHEN TO HEDGE:                                              ║
║  • 2 LONG positions open AND                                 ║
║  • Macro risk HIGH (war, FOMC, CPI, tariffs, crash)          ║
║  → 3rd slot = index SHORT (DAX or Nasdaq) as hedge           ║
║                                                               ║
║  HEDGE RULES:                                                ║
║  • Size: Lottery 10% — NEVER larger than smallest LONG pos   ║
║  • Same exit rules: 50% at +20%, rest trail                  ║
║  • CLOSE hedge when macro risk decreases                     ║
║  • DAX SHORT preferred (lower ATR than Nasdaq, EU hours)     ║
║                                                               ║
║  WHEN NOT TO HEDGE:                                          ║
║  • Only 1 LONG open → use 3rd slot for next trade            ║
║  • Macro calm → hedge only costs performance                 ║
║  • Already 50%+ cash → cash IS the hedge                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Risk Management

```
╔═══════════════════════════════════════════════════════════════╗
║  THESE RULES ALWAYS APPLY — NO EXCEPTIONS!                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. Max loss per trade:         10% of portfolio             ║
║  2. Max simultaneously at risk: 40% of portfolio             ║
║  3. Max sector concentration:   60% in one sector            ║
║  4. After 2 consecutive losses: halve position size          ║
║  5. After -20% drawdown:        24h trading pause            ║
║  6. ATR >7%: ONLY lottery/mini WITHOUT leverage              ║
║  7. KO distance: ALWAYS ≥2x ATR (commodities ≥3x ATR)       ║
║                                                               ║
║  Credentials NEVER in committed files!                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### ATR Measurement (Event-adjusted)

```
╔═══════════════════════════════════════════════════════════════╗
║  ATR CHECK BEFORE EVERY TRADE                                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Base:     ATR (14) — 14-day average                         ║
║  Event:    ATR (5) — last 5 days                             ║
║                                                               ║
║  IF ATR(5) > ATR(14) × 1.5:                                 ║
║  → Volatility ELEVATED, go one tier smaller:                 ║
║    • Standard → Small                                        ║
║    • Small → Lottery                                         ║
║    • Lottery → No trade or no leverage                       ║
║                                                               ║
║  BEFORE EARNINGS/EVENTS: ALWAYS check ATR(5)!               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Analysis Principles

Concrete trading decisions (entry, exit, stop, KO distance) come from the 4-step analysis — not from fixed rules. The analysis delivers support/resistance, confidence, and position size per trade.

**Core principles:**
- **Tiered exits:** 50% out at +20%, rest trailing stop to break-even → runner target +40-60%
- **Confidence gate:** Only trades with ≥60% confidence from the analysis — NO exceptions
- **Take profits** when the analysis shows it — don't let winners turn into losers
- **LONG and SHORT are equal** — the analysis decides direction, not a bias
- **Situational hedge** — with 2 LONGs + high macro risk → 3rd slot as index SHORT (DAX preferred)
- **KO calculation: ATR + chart combined** — KO always below strongest support (LONG) or above resistance (SHORT). ATR multiplier by asset class (large cap 2x, small cap 2.5x, commodities 3x)
- **ATR event check** — ATR(5) vs ATR(14) before every trade. If ATR(5) > ATR(14) × 1.5 → one tier smaller
- **Time stops** — after 3 days without +5%, halve; after 5 days, exit
- **Check correlation** — verify sector concentration before every new trade
- **Protect before earnings** — secure at least 50% before the event or increase ATR multiplier
- **No fixed currency amounts** — position size in % of portfolio (scales automatically)
- **Monthly target must not force trades** — +15% baseline is enough, no FOMO on stretch

### Hard Rules for Analyses

These rules are checked BEFORE every analysis is sent:

1. **portfolio.md first** — read portfolio from `memory/portfolio.md` BEFORE step 1 begins
2. **yfinance = truth** — no price, ATR, RSI without yfinance source
3. **Stop-loss mandatory** — every trade needs a stop (mental or broker)
4. **Never invent KO** — KO comes from ATR + chart, never estimated
5. **SHORT = LONG** — scorecard must be filled out, SHORT setup when score >= LONG
6. **No hardcoded exchange rates** — EUR/USD always live from yfinance
7. **Position % instead of currency** — recommendations always in % of portfolio
8. **Correlation check** — sector concentration against 60% limit

### Current State

Portfolio (open/closed positions, cash) lives in `memory/portfolio.md` — that is the single source of truth.
Analyses are sent via Telegram. No database access needed.

---

## Telegram Bot

- Credentials stored in `.env` (never committed to git)
- Each user creates their own bot via @BotFather

### Scripts

**`send_telegram.py`** - Helper module for sending Telegram messages and photos.
- `send_message(text, parse_mode='HTML')` - Send text message
- `send_photo(photo_path, caption='')` - Send photo with optional caption (multipart upload)
- CLI usage: `python send_telegram.py "Your message here"`

## Price Tracker

**`tracker_check.py`** - Personal price alert config, runs via GitHub Actions.
- Contains SYMBOLS, ALERT_RULES, and TRADING_ZONES
- State (prev_prices, alerted_levels) persisted in `memory/tracker_state.json`

**`tracker_check_template.py`** - Template for new users to copy and customize.

**`price_tracker.py`** - Local infinite-loop version (gitignored).

### Alert Features
- Flash move: >1.5% change in 5 minutes
- Big daily move: >5% intraday change
- Price level crossings (per-symbol thresholds in `ALERT_RULES`)
- AI Trading Zones with context notes (in `TRADING_ZONES`)
- Silent hourly summaries, loud alerts for dramatic moves

### GitHub Actions
- Workflow: `.github/workflows/tracker.yml`
- Schedule: every 10 min during market hours (08:00-22:00 CET), every 30 min overnight
- Weekdays only

## Multi-Agent Analysis

**Skill:** `/analyse-stock SYMBOL` - runs the full 4-step pipeline automatically.

**Manual:** `Analyze <SYMBOL> @prompts/00_master.md`

Language defaults to English. Change `{{LANGUAGE}}` in `prompts/00_master.md` if needed.

4-step pipeline in `prompts/`:

| Step | File | Agent Role |
|------|------|-----------|
| 1 | `01_data_collection.md` | yfinance data, chart, news, macro, ATR/volatility, short interest, **correlation check**, **event calendar** |
| 2 | `02_investment_debate.md` | Bull vs Bear debate (3 rounds), **SHORT trade scorecard** |
| 3 | `03_judge_risk.md` | Judge decision + confidence %, **ATR + chart combined KO calculation**, risk-per-trade check, time stops |
| 4 | `04_summary_send.md` | Trading card, chart → **Telegram delivery**, `memory/portfolio.md` update |

### Key Analysis Features
- Each analysis produces concrete entry/exit/stop/KO recommendations based on technicals
- **KO = maximum of ATR-based and chart-based** (always the further level)
- **ATR multiplier by asset class:** Large Cap 2.0x, Small/Mid Cap 2.5x, Commodities 3.0x, Crypto 3.0x
- **SHORT trades evaluated equally** via LONG vs SHORT scorecard in step 2
- Position sizing in % of portfolio (10% lottery / 25% small / 35% standard / 20% no leverage)
- Risk-per-trade capped at 10% portfolio
- Time stops: 5 days without movement → halve, 8 days → exit
- Correlation check against open positions before each new trade

### Chart Generation

Charts are generated by an external script and sent directly via Telegram:
- Script path in `.env` as `CHART_SCRIPT`
- Output dir in `.env` as `CHART_OUTPUT_DIR`
- Sent as Telegram photo via `send_telegram.py`

## Environment

All secrets and paths are in `.env` (never committed to git):

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_BOT_USERNAME=...
YFINANCE_VENV=...          # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...            # Optional: path to chart generation script
CHART_OUTPUT_DIR=...        # Optional: path to chart output directory
```

## Morning Screener

**`morning_screener.py`** - Pre-market screener that scans S&P 500 + custom watchlist + futures before market open.
- **Two-phase:** Fast batch `yf.download()` for ~500 symbols, then individual enrichment for top candidates only
- Hard gates: price exists, RSI calculable, volume >= 100k (futures bypass volume/market-cap gates)
- Scoring (0-100) for LONG and SHORT independently: RSI (20), SMA200 trend (15), SMA50 pullback/rejection (15), MACD crossover (15), ATR% volatility (20), analyst rating (10), bonus (5)
- ATR% weighted highest (turbo leverage needs volatility)
- S&P 500 list fetched from Wikipedia, merged with local watchlist
- SI=F and GC=F always included (futures bypass hard gates)
- Portfolio sector concentration check (60% limit)
- Marks already-owned stocks, flags upcoming earnings
- Workflow: `.github/workflows/morning_screener.yml` (08:00 CET, weekdays, 10 min timeout)

## Watchlist Check

**`watchlist_check.py`** - 2x daily scan of personal watchlist (`memory/watchlist.md`) with v4 scoring.
- Parses `memory/watchlist.md` (Markdown tables) for symbols + sectors + names
- Parses `memory/portfolio.md` for open positions
- Batch `yf.download()` for all symbols, then individual enrichment for top candidates
- v4 Trend/Momentum scoring identical to morning_screener.py (RSI, MACD, ADX, ATR%, Bollinger, SMA50/200)
- Hard gates relaxed vs morning screener: MIN_SCORE 20, volume 50k (watchlist is pre-curated)
- Shows Top 5 LONG + Top 5 SHORT, portfolio summary, upcoming events
- Stateless — no state file, no git commit needed
- Workflow: `.github/workflows/watchlist_check.yml` (07:30 + 21:15 CET, weekdays, 5 min timeout)

## Reddit Gems Scanner

**`reddit_gems.py`** - Daily scan of Reddit trending stocks via ApeWisdom API.
- Fetches trending tickers from all stock subreddits, enriches top candidates with yfinance
- Filters: min $500M market cap, min 50% mention change, skips ETFs/crypto
- Sends top 8 gems as Telegram summary before European market open
- Workflow: `.github/workflows/reddit_gems.yml` (07:00 CET, weekdays)

## Stock Watchlist

Curated watchlist managed via `admin_stocks.py`, updated automatically via GitHub Actions.

### Scripts

**`admin_stocks.py`** - Admin CLI for managing the watchlist.
- `python admin_stocks.py list` - Show all stocks
- `python admin_stocks.py add NVDA "NVIDIA" Technology` - Add a stock
- `python admin_stocks.py remove NVDA` - Deactivate (soft delete)
- `python admin_stocks.py seed` - Seed initial watchlist

**`update_stocks.py`** - Fetches yfinance data and updates watchlist.
- Updates: price, change_pct, RSI, SMA50, SMA200, market_cap, volume, analyst_rating
- Workflow: `.github/workflows/update_stocks.yml` (every 30 min during market hours)

**`browse_stocks.py`** - Read-only watchlist browser.
- `python browse_stocks.py` - Formatted table grouped by sector
- `python browse_stocks.py --json` - JSON output

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Stock Updater | `update_stocks.yml` | Every 30 min (market hours) | Update prices, RSI, SMAs |
| Watchlist Check | `watchlist_check.yml` | 07:30 + 21:15 CET (weekdays) | Top 5 LONG/SHORT from personal watchlist |
| Morning Screener | `morning_screener.yml` | 08:00 CET (weekdays) | LONG/SHORT scoring, top picks |
| Reddit Gems | `reddit_gems.yml` | 07:00 CET (weekdays) | Reddit trending stocks via ApeWisdom |
| Weekly Reflection | `reflect.yml` | Friday 20:00 CET | Trade statistics, duration, patterns |

Secrets needed: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Onboarding

Fork the repo and set up your own independent instance. See:
- `ONBOARDING.md` - Setup guide
- `.env.template` - Environment config template
