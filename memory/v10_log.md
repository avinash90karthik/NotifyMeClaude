# v10 Decision Log

Tracks pending v10 components and their evaluation data. Robust v10 components
(Sizing flatten, Concentration tightening V3/V4/V6) are LIVE and not tracked
here — they are documented in `strategy_v9.md` § 9.A and § 12.

## Pending Components

### Rule 28 — Trader-Day Circuit-Breaker

**Status:** PENDING — re-evaluate **2026-05-29**

**Why pending:** April 2026 evidence base is n=12 follow-up trades after a
Tier-2/3 stop. The Win-Rate gap (33% after loss vs 78% after win) cannot be
attributed to Tilt alone — three competing hypotheses are observationally
equivalent at this sample size:

1. **Tilt hypothesis** — trader makes worse decisions in the hours after a stop
2. **Market hypothesis** — Tier-2/3 stops cluster on bad market days, follow-up
   trade suffers from the same market environment, not from trader state
3. **Selection hypothesis** — fewer good setups exist on stop-days because the
   broader market is bearish; the follow-up sample is biased toward weaker setups

Without S&P-500 and sector-ETF returns alongside follow-up outcomes, all three
hypotheses produce the same observed Win-Rate gap. April-2026 backtest
attributed +€1029 to v10 overall; isolated Rule 28 contribution ≈ +€190
(realistic estimate: 1-of-3 prevented trade would have been a win at +€82,
2-of-3 losses at -€136 each; net 1×82 − 2×136 = +€190). Sizing + Concentration
carry the bulk of the v10 edge.

### Decision schema for 2026-05-29 (numerical, fixed before evaluation)

Read after n ≥ 30 follow-up-after-stop logged events:

| S&P-500 mean on stop-days | Follow-up Win-Rate | Decision |
|---|---|---|
| < −0.3% | any | Market-confound dominates → Rule 28 dropped, design separate market filter |
| −0.3% to +0.3% | < 45% | Tilt isolated → Rule 28 promoted to hard veto |
| −0.3% to +0.3% | ≥ 45% | Effect ambiguous → extend tracking 30 more days |
| > +0.3% | any | Tilt unlikely (you traded into strength after stop) → Rule 28 dropped |
| any | ≥ 50% | Effect was April noise → Rule 28 dropped |

Thresholds locked 2026-04-29 to prevent post-hoc redefinition. If 2026-05-29
data falls into the "extend tracking" cell, lock another 30-day extension with
the same schema, do not redefine cells.

### Tracking template (one block per Tier-2/3 stop)

```
## Stop YYYY-MM-DD <SYM> Tier-N

- Date: YYYY-MM-DD HH:MM CET
- Symbol: <SYM>
- Tier: 2 | 3 | Support-Override
- Realized P&L on stop: <EUR> (<%>)

- Same-day follow-up trade?: Y | N
  - If Y:
    - Symbol: <NEW_SYM>
    - Direction: LONG | SHORT
    - Pipeline confidence: <XX%>
    - Outcome: <EUR> (<%> on cert) — measured at trade close, not EoD
  - If N:
    - Pipeline run on watchlist (1-2 symbols, evening of stop-day):
      - <SYM_A>: signal=<LONG|SHORT|NO-TRADE>, confidence=<XX%>
      - <SYM_B>: signal=<LONG|SHORT|NO-TRADE>, confidence=<XX%>
    - Setup-existed?: Y (any signal ≥ 60% confidence) | N (all NO-TRADE or < 60%)

- S&P-500 daily return on stop-day: <±X.XX%>
- Sector-ETF daily return on stop-day: <ETF=XXX, ±X.XX%>
  - Map: AI-Semi → SOXX | Energy/Renewables → ICLN | Aerospace/Space → ARKX
  - Generic Tech → XLK | Healthcare → XLV | Financials → XLF
  - Other → S&P only, note "no clean sector ETF" in entry
```

### Logged events

## Stop 2026-04-28 ENR.DE Tier-3+Support-Override

- Date: 2026-04-28 13:43 CET
- Symbol: ENR.DE
- Tier: Tier-3 + Support-Override (combined exit)
- Realized P&L on stop: -153.15 EUR (-21% on cert, position #2 closed)

- Same-day follow-up trade?: N
  - Pipeline run on watchlist (1-2 symbols, evening of stop-day): not logged
    in conversation transcripts; closed-trades-list shows no new open between
    2026-04-28 13:43 CET and 2026-04-29 morning. Setup-existed evidence:
    unknown for stop-day; first re-eval is 2026-04-29 ENR.DE itself which
    returned NO-TRADE under cooldown clamp.
  - Setup-existed?: UNKNOWN (no contemporaneous watchlist run logged)

- S&P-500 daily return on stop-day: -0.49%
- Sector-ETF daily return on stop-day: ICLN=-1.68% (Clean Energy proxy for ENR)
  - Note: S&P -0.49% borderline cell; ICLN -1.68% is meaningfully negative.
    Per 2026-05-29 decision schema this is closer to "Market-confound" cell
    if S&P were ≤-0.3% — current S&P read is exactly at -0.49%, slightly
    below threshold. Single-data-point: cannot decide schema, contributes 1
    of n≥30 needed for evaluation.

---

## Same-Symbol Re-Entry Attempts (Rule 27 tracking)

**Status:** HARD active, evidence-base disclosed in `strategy_v9.md` § 10,
tracking armed.

**Why tracked:** Rule 27 has n=1 founding case (AMD #130). Rule retained on
asymmetric-downside grounds, not statistical inference. Tracking trigger
fires at n ≥ 10 same-symbol re-entry attempts (executed or not). At trigger
threshold the rule is re-evaluated against baseline Win-Rate (see
`strategy_v9.md` § 10 "Tracking trigger").

### Tracking template (one block per re-entry attempt on a previously stopped/TP'd symbol)

```
## Re-Entry Attempt YYYY-MM-DD <SYM>

- Symbol: <SYM>
- Original exit timestamp (exit_ts): YYYY-MM-DD HH:MM CET
- Original exit reason: Tier-2 | Tier-3 | Support-Override | TP+20%
- Original exit confidence: <XX%>

- Re-eval timestamp (reeval_ts): YYYY-MM-DD HH:MM CET
- Hours since exit: <X.Xh>
- Decision-tree case: A (no re-eval) | B (pre-24h) | C (post-24h)

- Criteria check:
  - C2 full re-analysis with FRESH data: PASS | FAIL
  - C3 confidence ≥10pp higher than exit confidence:
    - Exit confidence: <XX%>
    - Re-eval confidence: <XX%>
    - Delta: <±Xpp>
    - PASS | FAIL
  - C4 ≥1 NEW catalyst not in original plan:
    - Original catalysts: [list from original DB reason]
    - New catalysts cited: [list or "none"]
    - PASS | FAIL

- Cooldown decision:
  - cooldown_active after this re-eval: Y | N
  - eligible_at: YYYY-MM-DD HH:MM CET

- Trade executed: Y | N
  - If Y:
    - DB analysis ID: #<NN>
    - Direction, confidence, sizing
    - Outcome at close: <EUR> (<%> cert) — fill in when closed
  - If N (clamp held or user chose to wait):
    - Reason: cooldown_active | criteria_failed | discretionary_skip
```

### Logged attempts

## Re-Entry Attempt 2026-04-29 ENR.DE

- Symbol: ENR.DE
- Original exit timestamp (exit_ts): 2026-04-28 13:43 CET
- Original exit reason: Tier-3 + Support-Override (combined)
- Original exit confidence: 63% (closed trade #2)

- Re-eval timestamp (reeval_ts): 2026-04-29 12:35 CET
- Hours since exit: 22h52
- Decision-tree case: B (pre-24h)

- Criteria check:
  - C2 full re-analysis with FRESH data: PASS
  - C3 confidence ≥10pp higher than exit confidence:
    - Exit confidence: 63%
    - Re-eval confidence: 73%
    - Delta: +10pp
    - PASS-borderline (exact threshold)
  - C4 ≥1 NEW catalyst not in original plan:
    - Original catalysts (from ENR.DE position #2 entry context): outlook-raise
      April 23, AI-DC narrative, Grid +41%, Gas +32%, DB PT €170, ATH €191.66
    - New catalysts cited: none material since exit_ts 2026-04-28 13:43 CET
      (Q2 earnings full release scheduled 2026-05-12, no analyst PT change,
      no Trump-Hit, no breaking news 24h)
    - FAIL

- Cooldown decision:
  - cooldown_active after this re-eval: Y (extended)
  - eligible_at: 2026-05-01 13:43 CET (pre-24h-fail → +72h from exit_ts)

- Trade executed: N
  - Reason: criteria_failed (C4 FAIL → 72h extension)
  - DB analysis ID: #12 (recorded under cooldown clamp with placeholder
    entry/stop/target/ko; reason field documents NOT-ACTIONABLE status)

- Quant context for n≥10 tracking-trigger evaluation:
  - Scorecard LONG 44/60 vs SHORT 16/60 (Diff 28)
  - Trade-Window T-9→T-2 Ø+3.25% green 80% n=10 SOLID, sigmoid +4.17%
  - Indicator-Context BB 70-100% green 64% n=277 SOLID, CONVERGE bullish 3/3
  - Reversion-Guard LONG=Kein-Edge + SHORT=NO-TRADE
  - V6 corr NVDA 0.370 PASS

---

## Closed v10 components (no longer tracked here)

- **Rule 20 v10** (Sizing flatten): live in `prompts/03_judge_risk.md` §
  Position Sizing. April-backtest attribution: dominant edge contributor.
- **V3 / V4 / V6** (Concentration tightening): live in `lib/risk_audit.py` and
  `prompts/03_judge_risk.md` § Risk Audit. April-backtest attribution: prevented
  cluster blowups, secondary edge contributor.
