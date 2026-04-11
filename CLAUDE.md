# Silver Hawk Trading - Project Guide

## Overview

Trading notification system built around a multi-agent analysis framework. Portfolio state lives in `memory/predictions.db` (single source of truth). See `ONBOARDING.md` for setup instructions.

---

## TRADING STRATEGY v7/v8 (ACTIVE)

> **Full rules:** `memory/strategy_v7_draft.md` (v7 core + hedge + pivot)
> **Learnings & feedback:** `memory/feedback.md`

### Quick Reference

- **Entry:** 60% Scout / 40% Confirmation. No follow-up if Scout >10% up/down
- **Position Sizing:** 60-65% conf → 15% portfolio | 65-70% → 20% | 70%+ → 25%
- **Exit (v8):** 80% at +20% IMMEDIATELY. Rest max +30%. Trump-Events = alles raus
- **Stops:** ONE stop, set at purchase — no negotiating
- **Slots:** MAX 3 open positions (hedge does NOT count as slot)
- **Gate:** ≥60% confidence — NO exceptions
- **Time stops:** 3 days without +5% → halve; 5 days → exit
- **KO:** max(ATR-based, chart-based) — Large Cap 2x, Small/Mid 2.5x, Commodities 3x
- **ATR >7%:** Warrants/options only (no KO certs)
- **Overnight events:** Protect profits before known events (see strategy doc § Overnight-Event-Regel)

For v7 hedge rules, pivot rules, position sizing → `memory/strategy_v7_draft.md`

### Hard Rules for Analyses

1. **pre-flight first** — run `python3 preflight_check.py SYMBOL` BEFORE anything else. Its date/market output is ground truth. Its mandatory searches (Trump/Reddit/day-news) are not optional.
2. **portfolio first** — run `python prediction_db.py portfolio` before step 1 begins
3. **yfinance = truth** — no price, ATR, RSI without yfinance source
4. **Stop-loss mandatory** — every trade needs a stop (mental or broker)
5. **Never invent KO** — KO comes from ATR + chart, never estimated
6. **SHORT = LONG** — scorecard must be filled out, SHORT setup when score >= LONG
7. **No hardcoded exchange rates** — EUR/USD always live from yfinance
8. **Position % instead of currency** — recommendations always in % of portfolio
9. **Correlation check** — sector concentration against 60% limit
10. **Event check** — check for overnight/upcoming macro events BEFORE recommending holds
11. **No mini-analyses** — every analysis runs all 4 steps. Shortened flows are forbidden.
12. **No default direction** — no LONG/SHORT/NO-TRADE bias. Data speaks. Spiegel-Test before finalizing.
13. **Earnings pattern check** — run `python3 earnings_pattern.py SYMBOL` in Step 1. Script auto-skips if earnings >30 days out; runs full historical window analysis if near. Warning + confidence penalty mandatory if current phase historically weak.
14. **Price-action reality check** — MACD/RSI turn signals are NOT bullish triggers on their own. Verify with actual green-day count over last 10 trading days (must be ≥5/10) and relative strength vs S&P on most recent day. Flat price with positive MACD = stabilization, not bounce.
15. **Reddit argument quality** — read the minority's top 3 arguments, not just the majority count. If bears (at a LONG setup) have harder facts than bulls (opinions/targets), that's a contra-signal regardless of 70/30 split.

### Current State

Portfolio state (positions, cash, P&L) lives in `memory/predictions.db` — single source of truth.
Check with: `python prediction_db.py portfolio`
ALL analyses are recorded (traded or not) for backtesting.

---

## Multi-Agent Analysis

**Invocation:** When user asks to analyze a stock (e.g. "Analysiere PLTR", "Analyze ENR.DE", "PLTR anschauen"):

1. **Run `python3 preflight_check.py SYMBOL` FIRST** — no exceptions. Its output is ground truth.
2. **Echo back the Pre-Flight checklist** (verbatim, with your answers filled in) before Step 1.
3. **Execute all 4 steps** from `prompts/00_master.md` → `prompts/01_…md` → `prompts/04_…md`. Each step must end with its `[STEP N COMPLETE]` marker.
4. **No mini-analyses.** Shortened flows are forbidden. If you cannot run a step (e.g. yfinance unreachable), STOP and tell the user — do not substitute a shorter flow.

There is **no `/analyse-stock` slash command** — the full flow is triggered by natural-language intent plus the hard rules below. The pre-flight script (not a skill file) is what physically enforces the blindspot checks.

### Pre-Flight Script (mandatory first step)

**`preflight_check.py`** — hard-coded ground truth, runs before any analysis.
- `python3 preflight_check.py SYMBOL` — prints real date/weekday/CET-NY time + weekend flag + US/EU market status + price snapshot + yfinance news (last 7 days) + mandatory search queries (Trump Truth Social, Reddit WSB/WSB-Ger/stocks/investing, day news, event calendar) + echo-back checklist
- `python3 preflight_check.py SYMBOL --json` — machine-readable
- **The script's date/market output is THE ground truth.** Never override with web-search guesses.
- **Every search query it prints is MANDATORY.** Trump + Reddit are not optional color, they are pipeline inputs.
- Exits with code 2 if price fetch fails — analysis MUST abort, not fall back to a "mini" version.

### Data Collection Script

**`collect_data.py`** — Automated data collection.
- `python collect_data.py SYMBOL` — Full collection with human-readable + JSON output
- `python collect_data.py SYMBOL --json-only` — JSON only (for piping)
- Collects: price, RSI (delta/divergence/slope), MACD, ATR (event check), ADX, regime, SMA50/200, short interest, S/R, earnings, market status
- Imports shared indicators from `indicators.py`

### Trading Database (Single Source of Truth)

**`prediction_db.py`** — Tracks ALL analyses + portfolio + trades.
- `record SYMBOL --direction LONG --confidence 68 --entry 135.50 --stop 128.00 --target 155.00 --ko 120.00 --reason "..."` — Record analysis
- `open ID --shares 75 --cert-price 2.67 [--cert-type turbo]` — Mark as traded
- `confirm ID --shares 49 --cert-price 2.81` — v5 confirmation buy
- `close ID [--shares N] --exit-price 3.31 [--reason target]` — Partial/full exit
- `portfolio` — Show open positions, cash, closed trades
- `cash AMOUNT` — Set cash balance
- `fill` — Fill real market outcomes (run daily)
- `analyze` — Backtest: traded vs skipped, confidence brackets
- `list [--open|--closed|--analysis]` — Filter by status
- `export` — Export as CSV
- DB file: `memory/predictions.db` (gitignored)

### Pipeline (5 steps including pre-flight)

| Step | File | Purpose |
|------|------|---------|
| 0 | `preflight_check.py` | Date/weekday/market status + yfinance news + mandatory search queries (Trump/Reddit/day-news/events) |
| 1 | `prompts/01_data_collection.md` | Run `collect_data.py`, chart, news, macro, correlation check |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate (2 rounds + synthesis), SHORT scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO calculation, risk audit, trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, prediction DB record, portfolio update |

### Chart Generation

Charts are generated by an external script:
- Script path in `.env` as `CHART_SCRIPT`
- Output dir in `.env` as `CHART_OUTPUT_DIR`

## Environment

All secrets and paths are in `.env` (never committed to git):

```
YFINANCE_VENV=...          # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...            # Optional: path to chart generation script
CHART_OUTPUT_DIR=...        # Optional: path to chart output directory
```

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Prediction Fill | `prediction_fill.yml` | 22:15 CET (weekdays) | Fill real outcomes, analyze prediction quality |

## Dashboard

**`dashboard/`** — Local web dashboard (Flask API + Vite React).

### Setup
```bash
pip install flask flask-cors          # Backend (one-time)
cd dashboard/frontend && npm install  # Frontend (one-time)
bash dashboard/start.sh               # Start dashboard
# → http://localhost:5173
```

### Architecture
```
predictions.db ──┐
  (watchlist +   │   Flask API (:5050)  →  Vite React (:5173)
   portfolio)    │
yfinance (live) ─┤
chart PNGs ──────┘
```

### Tabs

| Tab | Purpose |
|-----|---------|
| Dashboard | Portfolio overview, open positions, P&L, slots |
| Scanner | Combo signal scanner — RSI + MACD + BB combinations with strength scores |
| Chart | 6-month candlestick with SMA50/200, Bollinger, KO zone, stop/entry/target |
| Track Record | P&L timeline, win rate, discipline tracker |
| Hedge | Hedge setup analyzer — RSI zone + short signals for open runners |

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/portfolio` | Portfolio state (positions, cash, slots) |
| `GET /api/predictions?status=` | All analyses, filterable |
| `GET /api/ohlcv/<symbol>` | OHLCV + indicators for charting (15min cache) |
| `GET /api/scan` | Combo signal scan across watchlist |
| `GET /api/hedge-setup/<symbol>` | Hedge analysis for a symbol |
| `GET /api/track-record` | Trade history from close_events |
| `GET /api/collect/<symbol>` | Live technical data (15min cache) |

## Onboarding

Fork the repo and set up your own independent instance. See:
- `ONBOARDING.md` - Setup guide
- `.env.template` - Environment config template
