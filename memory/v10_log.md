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

## Same-Symbol Re-Entry — historical attempts (Rule 27 tracking retired)

**Status:** Tracking retired 2026-04-29 along with Rule 27 simplification
(see `strategy_v9.md` § 10). Rule 27 is now a flat 24h cooldown anchored
to `exit_ts` with no re-eval criteria — the pipeline is the criterion.
The C2/C3/C4 + Case-A/B/C decision tree is removed. Past attempts are
kept here as historical context, not as a tracking series.

### Past attempts (historical, do not extend)

#### Re-Entry Attempt 2026-04-29 ENR.DE  (under prior Rule 27 wording)

- Symbol: ENR.DE
- Original exit (exit_ts): 2026-04-28 13:43 CET, Tier-3 + Support-Override,
  closed-trade conf 63%
- Re-eval at 2026-04-29 12:35 CET (22h52 after exit)
- Outcome under prior wording: Case B pre-24h, C4 FAIL → cooldown extended
  to 72h (`eligible_at = 2026-05-01 13:43 CET`)
- Outcome under current rule: would be a normal pipeline run during
  cooldown, NO-TRADE-clamped, eligible_at = 2026-04-29 13:43 CET (flat
  +24h). DB Analysis #12 stays as cooldown-clamp record.
- Quant context (informational):
  - Scorecard LONG 44/60 vs SHORT 16/60 (Diff 28), confidence 73%
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
