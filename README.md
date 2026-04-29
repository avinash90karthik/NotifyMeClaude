# Silver Hawk Trading

AI-powered trading analysis built with Claude Code and yfinance. Personal
trading-notification system for turbo-certs and warrants on Trade Republic
in a 1-5 day horizon. Everything runs locally — no cloud, no tracking, no
shared data.

## What It Does

- **5-step analysis pipeline** — pre-flight + 4 prompt-driven steps
  (data collection, bull/bear debate, judge verdict, trading card)
  for any stock or commodity.
- **LONG & SHORT signals** — scorecard-based evaluation enforces
  symmetry (Hard Rule 6: SHORT scorecard mandatory regardless of
  preconceived direction).
- **Per-stock indicator analysis** — sigmoid-based confidence adjusts
  derived from each stock's own historical fwd-5d distribution; no
  textbook "RSI > 70 = overbought" reflexes (Rule 16). Strongest single
  axis from RSI / BB / DistHigh is used to avoid double-counting
  correlated signals.
- **Reversion guard** — per-stock percentile + own fwd-distribution
  decides whether today's setup is a continuation or a pullback-required
  entry (Rule 18).
- **Smart KO calculation** — `max(ATR-based, chart-based)`, asset-class
  multiplier (Large Cap 2×, Mid/Small 2.5×, Commodities 3×), with
  vol-spike and pre-earnings surcharges (Rule 5: KO is computed,
  never estimated).
- **Risk management** — Gate at ≥60% confidence, 10% max loss per
  trade, max 3 open slots, 60% max sector concentration, smooth
  differential penalty `1 − 0.15·exp(−Diff/4)` instead of bucket
  cliffs.
- **v9 sizing** — at confidence 60-65% the Scout is inverted to
  40/60 (smaller initial, larger confirmation) because the bracket is
  effectively coin-flip; from ≥65% the classic 60/40 split.
- **v9 oversold bonus** — RSI band <20 with ≥65% green-rate gets +5%
  confidence bonus (Rule 19), <15 with ≥70% gets +8% (capitulation
  setup). Stock-specific evidence overrides regime penalties.
- **Portfolio tracking** — `memory/predictions.db` (SQLite) is the
  single source of truth. Updated after every analysis (recorded
  even on NO-TRADE) and trade.
- **Time-stops** — halve after 3 days without +5%, exit after 5 days
  sideways. v9 exits: 80% out at +20% immediately, rest max +30%.
  Overnight events / Trump posts → all out.

## Requirements

- **Claude Pro** ($20/month) — for Claude Code
- **yfinance** (free) — all market data
- **Python 3.10+**
- **Node.js + npm** — only for Claude Code itself

## Quick Start

```bash
# 1. Install Claude Code
npm install -g @anthropic-ai/claude-code

# 2. Clone the repo
git clone https://github.com/AbdullahKaratas/NotifyMeClaude.git
cd NotifyMeClaude

# 3. Install Python dependencies
pip3 install yfinance numpy pandas pywavelets python-dotenv

# 4. Optional .env (only if you use a dedicated venv or external chart script)
cp .env.template .env

# 5. Smoke-test the install
python3 scripts/analysis/preflight_check.py AAPL
python3 scripts/analysis/collect_data.py AAPL
python3 scripts/ops/prediction_db.py portfolio

# 6. Run your first analysis
claude
> Analysiere SYMBOL
```

The `memory/predictions.db` SQLite file is created on first use.

## Architecture

```
You (Claude Code)
├── "Analysiere SYMBOL"                        → pre-flight + 4-step analysis → terminal trading card
├── python3 scripts/ops/prediction_db.py portfolio  → view positions, cash, slots
└── python3 scripts/analysis/collect_data.py SYMBOL      → quick technical snapshot

Local State
├── memory/predictions.db                       → positions, stops, P&L, analysis log
├── memory/preopen_patterns.json                → pre-open pattern statistics
└── RULES.md                                    → single rule registry (rationale, evidence, falsification)
```

## Analysis Pipeline

Tell Claude Code: **"Analysiere SYMBOL"** (or "Analyze SYMBOL"). The
pipeline starts with a pre-flight check (`scripts/analysis/preflight_check.py`)
and runs all four steps below — no shortcuts, no mini-versions.

| Step | What Happens |
|------|--------------|
| 0. Pre-Flight | `scripts/analysis/preflight_check.py` — real date/weekday/market-status, yfinance news (7d), mandatory Trump/Reddit/day-news/event searches, echo-back checklist. |
| 1. Data Collection | yfinance prices, RSI, MACD, SMAs, ATR, short interest, news, correlation check, event calendar, geopolitical triggers. Per-stock indicator-context with sigmoid adjusts (strongest single axis). Earnings-window pattern. Reversion-edge probe. Step 1 ends with a one-line summary block. |
| 2. Investment Debate | Bull vs Bear — 2 full rounds + LONG vs SHORT 6-axis scorecard (/60). Reversion-edge mapped to a symmetric rating (LONG max 8/10 in the strongest case). |
| 3. Judge & Risk | Verdict + confidence (smooth differential penalty), KO via max(ATR, chart), V-vetos + W-warnings, position sizing in % of portfolio with v9 Scout-inversion below 65%. |
| 4. Trading Card | Final card in terminal. `memory/predictions.db` updated with the analysis (always, even on NO-TRADE). Cert request with target-based leverage formula and KO-range. |

Hard rules live inline in the prompts where they are enforced. The "why"
behind each rule (rationale, evidence base, falsification trigger) lives
in `RULES.md` at the repo root.

## Watchlist

The watchlist lives in the `watchlist` table inside `memory/predictions.db`.
You don't have to use it — every analysis works on any symbol you pass.

```bash
# List
sqlite3 memory/predictions.db "SELECT symbol, name, sector FROM watchlist ORDER BY symbol;"

# Add
sqlite3 memory/predictions.db "INSERT INTO watchlist(symbol, name, sector) VALUES('AAPL', 'Apple Inc.', 'Technology');"

# Remove
sqlite3 memory/predictions.db "DELETE FROM watchlist WHERE symbol='AAPL';"
```

## Portfolio Tracking

```bash
# Show current state (positions, cash, slots, recent closes)
python3 scripts/ops/prediction_db.py portfolio

# Set cash balance
python3 scripts/ops/prediction_db.py cash 10000

# After a trade is opened
python3 scripts/ops/prediction_db.py open ID --shares 50 --cert-price 2.50 --cert-type turbo

# v9 confirmation buy (after Scout +5% in profit)
python3 scripts/ops/prediction_db.py confirm ID --shares 30 --cert-price 2.65

# Close (full or partial)
python3 scripts/ops/prediction_db.py close ID --exit-price 3.10 --reason target
```

## Repository Layout

```
NotifyMeClaude/
├── CLAUDE.md                  # onboarding index for Claude
├── README.md                  # this file
├── .env.template              # optional config (gitignored .env)
├── prompts/                   # 5 prompt files (00_master + 01-04)
├── scripts/
│   ├── analysis/              # pipeline scripts called by prompts
│   ├── ops/                   # portfolio state CLI (prediction_db)
│   ├── backtest/              # validation / falsification tools
│   └── tr/                    # Trade Republic broker access
├── lib/                       # shared library modules
├── tests/                     # pytest suite
└── memory/                    # local state (predictions.db, patterns)
```

## Scripts

All CLI tools live under `scripts/`. Shared library code lives under `lib/`
and is imported by the scripts — never invoked directly.

### Pipeline scripts (called by prompts)

| Script | Purpose |
|--------|---------|
| `scripts/analysis/preflight_check.py` | Mandatory first step — date/market status, yfinance news, mandatory search-query banner, echo-back checklist |
| `scripts/analysis/collect_data.py` | Full technical snapshot (price, RSI, MACD, ATR, SMAs, S/R, events, FX) |
| `scripts/analysis/price_action_check.py` | 5/10/20-day trend + green-day count + verdict (Rule 14) |
| `scripts/analysis/indicator_context.py` | Per-stock RSI/BB/DistHigh band statistics + sigmoid adjust + STRONGEST AXIS aggregation (Rule 16) |
| `scripts/analysis/day_pattern.py` | Similar-day forward-return distribution |
| `scripts/analysis/pattern_timeline.py` | Mode 1 similar-day + Mode 2 analog-match forecast for Day +1 to +5 |
| `scripts/analysis/earnings_pattern.py` | Per-stock earnings-window historical behavior (backward + trade-window mode) |
| `scripts/analysis/event_impact.py` | Big-moves (>3%) reaction history with bounce rate |
| `scripts/analysis/reversion_guard.py` | Per-stock LONG/SHORT reversion-edge check (Rule 18) |
| `scripts/analysis/entry_calibration.py` | Intraday-dip statistics + realistic buy-range computation |

### Operational scripts

| Script | Purpose |
|--------|---------|
| `scripts/ops/prediction_db.py` | Portfolio state + trade log + analysis record (SQLite CLI) |
| `scripts/analysis/preopen_check.py` | Pre-open verdict: buy NOW or WAIT? Pattern-based |
| `scripts/analysis/preopen_backtest.py` | Backtest pre-open patterns on historical data |
| `scripts/backtest/backtest.py` | Rolling-window validation of `lib/scoring.py` weights + per-component feature-importance decomposition (falsification loop for `score_long`/`score_short`) |

### Library modules (imported, not invoked)

| Module | Purpose |
|--------|---------|
| `lib/indicators.py` | `calc_technicals`, `sigmoid_adjust`, `calc_adx`, `calc_bollinger`, `detect_regime`, `detect_rsi_divergence` |
| `lib/scoring.py` | `score_long`, `score_short` — used by `preopen_check`, `preopen_backtest` and `backtest` (validation) |
| `lib/risk_audit.py` | V-veto layer (V1 ATR, V2 CHOPPY+score, V3 slots, V4 sector, V5 drawdown) |
| `lib/wavelet_utils.py` | Wavelet denoising for OHLCV inputs |

## Environment

Optional paths in `.env` (gitignored):

```
YFINANCE_VENV=...      # path to python3 in a dedicated venv
CHART_SCRIPT=...        # external chart-generation script
CHART_OUTPUT_DIR=...    # chart output directory
```

## Documentation

- **`CLAUDE.md`** — onboarding index for Claude Code (project meta-conventions)
- **`prompts/00_master.md`** — pipeline overview + invocation rules
- **`prompts/01_data_collection.md` … `04_summary_send.md`** — step instructions, hard rules inline
- **`RULES.md`** — single rule registry (severity, owner, rationale, evidence, falsification per rule)
- **`memory/TRACKING.md`** — pending rules and accumulating evidence
- **`archive/`** — historical context retained for evidentiary value (e.g. v9 backtest rationale)
- **`tests/`** — what we never want to break (currency handling, ATR true-range, slot counting, SQL injection guard)

## FAQ

**Does this cost anything?**
Claude Pro ($20/month). Everything else is free (yfinance, local SQLite).

**Can anyone see my data?**
No. Everything is local — your own SQLite file, no cloud, no tracking, no
accounts. yfinance pulls public market data only.

**Do I need to know how to code?**
You need to be comfortable opening a terminal and running the commands
above. The actual analysis is driven by Claude Code in natural language.

**How do I update the code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```

## Privacy

- No cloud database — state lives in your local `memory/predictions.db`
- No shared data, no tracking, no accounts
- yfinance pulls public market data only

## License

Personal use. Fork and customize for your own trading setup.
