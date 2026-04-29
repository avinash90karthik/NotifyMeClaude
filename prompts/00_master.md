# MULTI-AGENT TRADING ANALYSIS

**Asset:** {{SYMBOL}} | **Output Language:** English (cards, reasoning, all step output)

> Entry point: natural-language request from the user (e.g. "Analysiere PLTR", "Analyze ENR.DE").
> There is no slash-command skill. Enforcement lives in `preflight_check.py` (hard script output)
> and the CLAUDE.md hard rules. Mini-analyses are forbidden.

## Pipeline

Execute sequentially. Each step builds on the previous. No step may be skipped.

| Step | File | Purpose |
|------|------|---------|
| 0 | `preflight_check.py` | Date/weekday/market-status + yfinance news + mandatory Trump/Reddit/day-news searches |
| 1 | `prompts/01_data_collection.md` | Price, indicators, chart, news, macro, patterns, events |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate, 6-axis scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO, reversion guard, risk audit, stock trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, cert request, prediction DB record |

**Step 0 command:** `python3 scripts/preflight_check.py {{SYMBOL}}` - runs FIRST. Its date/market output is ground truth. Echo the checklist back with your answers before Step 1.

## Rules

- **Primary ruleset:** `CLAUDE.md` Hard Rules (Gate, Exits, KO, Position Sizing, Rules 1-24). Re-read before each analysis in case rules changed.
- **Rules:** `RULES.md` (single registry).
- **Portfolio state:** `python3 scripts/prediction_db.py portfolio` - run BEFORE Step 1.
- **yfinance = truth** for all price data. Never use web search for prices.
- **Pre-/Post-Market with yfinance:** When the US market is closed, `preflight_check.py` only returns the last regular close. For extended-hours live prices use `yf.Ticker(SYMBOL).info` (fields `preMarketPrice`, `preMarketChangePercent`, `postMarketPrice`) or `yf.Ticker(SYMBOL).history(period='1d', interval='5m', prepost=True)`. Twelvedata Basic plan does NOT support pre-/post-market - don't waste time on it.
- **Every trade** needs: entry, stop, KO, exits, time-stop.
- **Horizon 1-3 days primary, up to 5d if structurally justified.** Empirical v10 observation 2026-04-28: trades almost never reached full 5d — limit or stop triggered earlier (median hold time 1-3d). No multi-week setups. "No edge today" is valid; "come back in 3 weeks" is forbidden.
- **English everywhere in step output.** Cards, reasoning, ratings, bullet summaries - English. The user-facing conversation around the analysis stays German; the analysis artifacts themselves are English.

**v11 status (2026-04-29):** v11 Posterior-B research branch (`refactor/v11-stochastic`) reached pre-registered falsification on 2026-04-28. No live integration. v9 pipeline remains live. Wavelet denoising disabled in collect_data.py since 2026-04-27 (look-ahead leakage, see plan.md deviations 2026-04-27). Trade horizon updated 2026-04-28 to "1-3 days primary, up to 5d if structurally justified" reflecting v10 empirical observation.

## Quality Gate

Before completing Step 4, record the prediction:
```bash
python3 scripts/prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] --confidence [XX] \
  --entry [XX.XX] --stop [XX.XX] --target [XX.XX] --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] --atr-pct [X.X] \
  --reason "..."
```

`--entry` MUST be the limit/trigger center level (W4), NOT the current close.
