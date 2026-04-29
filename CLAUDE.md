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
- **Loss exits are TIERED (Rule 26), never single-shot.** Cert −15%
  = hard sell 50% immediately. Cert −25% = hard sell 100% + activate
  Rule 27 re-entry cooldown. PLUS Support-Override: if underlying
  closes below the strongest support level (Step 1 § 1.4), force
  hard-exit 50% even if cert hasn't hit −15% yet. Reference unit is
  **cert-%**, not underlying-%. Empirical basis: n=271 closed trades,
  ≤−15% trades end on Ø −33%, 84% of total loss-damage came from
  this tail. Full ruleset in `prompts/03_judge_risk.md` § Loss Exits.
- **Rule 27 — Re-Entry Cooldown after ANY exit (Tier-2/3 stop or +20% TP).**
  24h cooldown from `exit_ts`. During cooldown: pipeline run allowed,
  output NO-TRADE-clamped (no entry/stop/KO/sizing/cert; DB record stores
  direction + confidence with NULL trade-plan fields). After 24h: normal
  pipeline run, normal trade if the pipeline produces a signal. The
  pipeline IS the re-eval criterion — no separate +10pp / NEW-catalyst
  gates. Full text: `prompts/03_judge_risk.md` § Rule 27.
- **Rule 28 — Trader-Day Circuit-Breaker (PENDING, re-eval 2026-05-29).**
  Demoted from hard veto to soft warning + tracking on 2026-04-29: n=12
  April evidence cannot separate Tilt vs Market-confound vs Selection-bias.
  `scripts/preflight_check.py` now emits `[RULE 28 PENDING — TRACKING]` on
  Tier-2/3 stop in trailing 32h **without exiting** — pipeline runs through.
  User MUST log each stop in `memory/v10_log.md` (template + locked decision
  schema there). Without log entries, the 2026-05-29 evaluation is blind.
  Rule 27 (same-symbol cooldown) remains hard, with clarified decision tree
  and NO-TRADE output clamp (2026-04-29).
- **v10 concentration limits (tightened 2026-04-28):** Slot cap **2** (was 3,
  hedges excluded). Sector cap **40%** (was 60%) with AI-semi grouping
  {NVDA, AMD, AVGO, MRVL, TSM, ASML} treated as ONE effective sector.
  W2-correlation-halve upgraded to **V6** hard veto at 60d daily-return
  correlation ≥ 0,7. Override: `"V6-override: <reason>"`. Enforced in
  `lib/risk_audit.py`.
- **After a fill, place Rule 26 exit orders via pytr (mandatory).**
  `python3 scripts/tr/place_exits.py --isin <ISIN> --buy <FILL>
  --shares <N>` — places real stop-market sell orders for Tier 2
  and Tier 3 + a +20% price alarm. Re-run after v9 confirmation
  buy (the script auto-cancels existing exits and re-places at the
  blended buy price). Use `--dry-run` to preview.
- **pytr CAN place orders.** It supports limit/market/stop-market
  orders + cancel + alarms. The Rule 26 exits are placed automatically
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

## GitHub Actions

- `prediction_fill.yml` — 22:15 CET on weekdays — fills real outcomes
  into the predictions DB and analyzes prediction quality.
