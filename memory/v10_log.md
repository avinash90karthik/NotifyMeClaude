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

(none yet — first entry will be added on the next Tier-2/3 stop after 2026-04-29)

---

## Closed v10 components (no longer tracked here)

- **Rule 20 v10** (Sizing flatten): live in `prompts/03_judge_risk.md` §
  Position Sizing. April-backtest attribution: dominant edge contributor.
- **V3 / V4 / V6** (Concentration tightening): live in `lib/risk_audit.py` and
  `prompts/03_judge_risk.md` § Risk Audit. April-backtest attribution: prevented
  cluster blowups, secondary edge contributor.
