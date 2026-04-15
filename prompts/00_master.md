# MULTI-AGENT TRADING ANALYSIS

**Asset:** {{SYMBOL}} | **Language:** {{LANGUAGE}} (Default: English)

> Entry point: natural-language request ("Analysiere PLTR", "Analyze ENR.DE").
> There is no slash-command skill. Enforcement lives in `preflight_check.py` (hard script output)
> and the CLAUDE.md hard rules. Mini-analyses are forbidden.

## Pipeline

Execute sequentially. Each step builds on the previous. No step may be skipped.

| Step | File | Purpose |
|------|------|---------|
| 0 | `preflight_check.py` | Date/weekday/market-status + yfinance news + mandatory Trump/Reddit/day-news searches |
| 1 | `prompts/01_data_collection.md` | Price, indicators, chart, news, macro, patterns, events |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate, SHORT scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO, reversion guard, risk audit, trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, prediction DB record |

**Step 0 command:** `python3 preflight_check.py {{SYMBOL}}` — runs FIRST. Its date/market output is ground truth. Echo the checklist back with your answers before Step 1.

## Rules

- **Primary ruleset:** `CLAUDE.md` — current Hard Rules (Gate, Exits, KO, Position Sizing, Rules 1-18). Re-read before each analysis in case rules changed.
- **Strategy:** `memory/strategy_v7_draft.md` (v7 core, hedge, pivot, v8 exits, overnight rule)
- **Portfolio state:** `python prediction_db.py portfolio` — run BEFORE Step 1.
- **yfinance = truth** for all price data. Never use web search for prices.
- **Every trade** needs: entry, stop, KO, exits, time-stop.
- **Horizon 1-5 days only.** No multi-week setups. "No edge today" is valid; "come back in 3 weeks" is forbidden.

## Quality Gate

Before completing Step 4, record the prediction:
```bash
python3 prediction_db.py record {{SYMBOL}} --direction [LONG|SHORT] --confidence [XX] --entry [XX.XX] --stop [XX.XX] --target [XX.XX] --ko [XX.XX]
```

`--entry` MUST be the limit/trigger level (Rule 18), NOT the current close.
