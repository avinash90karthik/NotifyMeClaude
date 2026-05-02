# MULTI-AGENT TRADING ANALYSIS — Pipeline Index

**Output Language:** English (cards, reasoning, all step output)

User entry: natural-language request ("Analysiere PLTR", "Analyze ENR.DE").

## Pipeline

| Step | File | Purpose |
|------|------|---------|
| 0 | `prompts/00_preflight.md` | Date/market-status, symbol validity, V5/SW2 hard stops |
| 1 | `prompts/01_data_collection.md` | Raw data: prices, indicators, intraday, news, macro |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate on raw data |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO, exits, per-stock conditioning |
| 4 | `prompts/04_summary_send.md` | Trading card, cert request, prediction DB record |

Each step builds on the previous. No skipping. Each step persists output to `runs/{SYMBOL}_{YYYYMMDD}_{HHMMSS}/`.

## Rules

- **Hard Vetos:** V5 (Max 3 Slots) and SW2 (24h Re-Entry Cooldown) enforced via code in `preflight_check.py`. V1 (KO Validity) is LLM-checked in Step 3 — the LLM reasons over raw bars and aborts with NO-TRADE if no defensible KO can be derived. See `CLAUDE.md`.
- **yfinance = truth** for price data. Never use web search for prices.
- **Every trade** needs: entry, stop, KO, exits, time-stop.
- **Horizon:** 1-3 days primary, up to 5d if structurally justified.
- **English everywhere in step output.** User conversation stays German.

## Quality Gate

Before completing Step 4, record the prediction:

```bash
python3 scripts/ops/prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] --confidence [XX] \
  --entry [XX.XX] --stop [XX.XX] --target [XX.XX] --ko [XX.XX] \
  --atr-pct [X.X] --reason "..."
```

`--entry` is the limit/trigger center level, NOT the current close.

## v1.0 Status (2026-05-02)

Pipeline rewritten on `refactor/v1.0`. Step 1 emits raw data without aggregation. Step 2/3 do reasoning directly on raw bars. Hard vetos V1/V5/SW2 enforced via code; all other rules are LLM context.
