# Silver Hawk Trading - Project Guide

## What this is

Personal trading-notification system built around a multi-agent analysis
framework. The user trades turbo-certs and warrants on Trade Republic in a
1-5 day horizon. Portfolio state lives in `memory/predictions.db` and is
the single source of truth for positions, cash, and analysis history.

## Where to find what

- **Pipeline steps:** `prompts/00_master.md` -> `prompts/01_data_collection.md`
  -> `prompts/02_investment_debate.md` -> `prompts/03_judge_risk.md` ->
  `prompts/04_summary_send.md`. Each step contains the hard rules it
  enforces, inline.
- **Strategy rationale (the "why" behind rules):** `memory/strategy_v9.md`.
  This document is reference-only, not auto-loaded; prompts link to it for
  post-mortems and backtest justifications.
- **Portfolio + analysis history:** `prediction_db.py` CLI + `memory/predictions.db`.
- **Setup / onboarding:** `ONBOARDING.md` + `.env.template`.

## How to invoke an analysis

When the user asks to analyze a stock (e.g. "Analysiere PLTR",
"PLTR anschauen", "Analyze ENR.DE"):

1. Run `python3 scripts/preflight_check.py SYMBOL` FIRST. Its date/market output
   is ground truth.
2. Echo back the pre-flight checklist verbatim with your answers filled in
   before Step 1.
3. Execute all 4 steps from `prompts/00_master.md` -> `prompts/04_summary_send.md`.
   Each step ends with `[STEP N COMPLETE]`.
4. No mini-analyses. No shortened flows. If you cannot run a step (e.g.
   yfinance unreachable), STOP and tell the user.

There is no slash-command - the full flow is triggered by natural-language
intent. The pre-flight script enforces the blindspot checks.

## Conventions for Claude

- **Output language for analysis artifacts:** English. Step output, cards,
  ratings, reasoning sentences, and script output are all English.
- **User-facing conversation around the analysis:** German.
- **Hard rules live where they are enforced** — re-read the relevant
  prompt for the current ruleset; do not rely on memory of older rule
  versions. The full rule rationale is in `memory/strategy_v9.md`.
- **Trade horizon is 1-5 days only.** "No edge today" is a valid answer;
  "come back in 3 weeks" is forbidden as a trade recommendation.
- **No price / ATR / RSI without yfinance source.** Web search is for
  news and macro context, never for prices.

## Environment

All secrets and paths in `.env` (gitignored).

```
YFINANCE_VENV=...      # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...        # Optional: external chart generation script
CHART_OUTPUT_DIR=...    # Optional: chart output directory
```

## GitHub Actions

- `prediction_fill.yml` — 22:15 CET on weekdays — fills real outcomes
  into the predictions DB and analyzes prediction quality.
