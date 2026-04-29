# Silver Hawk Trading - Project Guide

## What this is

Personal trading-notification system built around a multi-agent analysis
framework. The user trades turbo-certs and warrants on Trade Republic in a
1-5 day horizon. Portfolio state lives in `memory/predictions.db` and is
the single source of truth for positions, cash, and analysis history.

## Where to find what

- **Rules (single registry):** `RULES.md` — rationale, evidence, falsification triggers per rule. Mechanics for each rule live in the prompt that enforces it (linked from each rule entry).
- **Pipeline architecture:** `prompts/00_master.md`. Each step file (`01` … `04`) enforces its own rules inline.
- **Portfolio + analysis history:** `prediction_db.py` CLI + `memory/predictions.db`.
- **Tracking data for pending rules:** `memory/TRACKING.md`.
- **Setup / onboarding:** `README.md` + `.env.template`.
- **Live broker access (pytr — already authenticated):**
  - `scripts/tr/list_orders.py` — read open orders + price alarms
  - `scripts/tr/place_exits.py --isin <X> --buy <P> --shares <N>` —
    auto Tier-2/3 stops + TP alarm after a fill (use `--exchange SGL`
    for SocGen FE-certs, defaults to TUB for HSBC HM-certs)
  - `scripts/tr/cancel_all.py` — cancel orders/alarms on an ISIN
  - Direct API: `from pytr.api import TradeRepublicApi; tr.resume_websession()`
    for ad-hoc reads (portfolio, ticker, instrument_details)
  - `pytr portfolio` (CLI) — official portfolio + cash, requires fresh 2FA
    occasionally; if it asks for a code, the user must enter it
  - **Notifications:** `osascript` → iMessage to `abdullah.karatas@icloud.com`
    when a trigger needs the user's attention away from terminal

## How to invoke an analysis

When the user asks to analyze a stock (e.g. "Analysiere PLTR",
"PLTR anschauen", "Analyze ENR.DE"):

1. Run `python3 scripts/analysis/preflight_check.py SYMBOL` FIRST. Its date/market output
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
  versions. Rule rationale + evidence + falsification triggers live in `RULES.md`.
- **Trade horizon is 1-3 days primary, up to 5d if structurally justified.** "No edge today" is a valid answer;
  "come back in 3 weeks" is forbidden as a trade recommendation.
- **No price / ATR / RSI without yfinance source.** Web search is for
  news and macro context, never for prices.
- **All trading rules live in `RULES.md`**, grouped by severity: **Vetos (V1–V5)** block hard, **Soft Vetos (SV1–SV3)** block by default with override allowed, **Warnings (W1–W12)** mandate trade-plan or confidence adjustments without blocking, **Soft Warnings (SW1–SW2)** are recommendations with override. Re-read the relevant entry before each analysis; do not summarise from memory.
- **After a fill, place W9 (Tiered Stop) exit orders via pytr (mandatory).**
  `python3 scripts/tr/place_exits.py --isin <ISIN> --buy <FILL>
  --shares <N>` — places real stop-market sell orders per W9
  tiers + a +20% price alarm. Re-run after a confirmation
  buy (the script auto-cancels existing exits and re-places at the
  blended buy price). Use `--dry-run` to preview.
- **pytr CAN place orders.** It supports limit/market/stop-market
  orders + cancel + alarms. The W9 exits are placed automatically
  via `place_exits.py`. For ad-hoc orders (manual entries, take-profits)
  Claude WILL still ask for explicit confirmation — the rule is
  "automatic for documented strategy actions, manual for one-offs".

## Environment

All secrets and paths in `.env` (gitignored).

```
YFINANCE_VENV=...      # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...        # Optional: external chart generation script
CHART_OUTPUT_DIR=...    # Optional: chart output directory
```
