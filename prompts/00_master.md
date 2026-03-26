# MULTI-AGENT TRADING ANALYSIS

**Asset:** {{SYMBOL}} | **Language:** {{LANGUAGE}} (Default: English)

## Pipeline

Execute these 4 steps sequentially. Each builds on the previous.

| Step | File | Purpose |
|------|------|---------|
| 1 | `prompts/01_data_collection.md` | Run `python collect_data.py {{SYMBOL}}`, chart, news, macro |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate (2 rounds + synthesis), SHORT scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO calculation, risk audit, trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, Telegram delivery, prediction DB record |

## Rules (always active)

- Strategy rules: `memory/strategy_v5.md` and `CLAUDE.md`
- Portfolio state: `python prediction_db.py portfolio` (run BEFORE Step 1)
- yfinance = truth for all price data (never web search for prices)
- Every trade needs: entry, stop, KO, exits, time-stop
- No step may be skipped

## Quality Gate

Before completing Step 4, record the prediction in the database:
```bash
python prediction_db.py record {{SYMBOL}} --direction [LONG|SHORT] --confidence [XX] --entry [XX.XX] --stop [XX.XX] --target [XX.XX] --ko [XX.XX]
```
