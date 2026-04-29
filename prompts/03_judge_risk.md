# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}
**Input:** Step 1 bullets + ratings | Step 2 scorecard + Bull/Bear synthesis.

This step produces the **stock trade plan only** (signal, confidence, entry/stop/KO/target on the underlying, position sizing in EUR). Cert selection, leverage formula, and KO-range for the certificate live entirely in Step 4. Do not propose a cert here.

> **All rule mechanics — V1–V5, SV1–SV3, W1–W12, SW1–SW2 — live in `RULES.md`.** This step references them; it does not duplicate them. When this prompt says "compute KO per V1", the table, surcharges, and final-selection rule live in `RULES.md § V1`. Same for every other rule.

---

## Judge Verdict

### Signal + Confidence

Compute per `RULES.md § W6` (Mechanics → Confidence computation). Output:

```
Direction:        LONG | SHORT
Raw Confidence:   XX%   (max(LONG-Total, SHORT-Total) / 60 × 100)
Diff:             XX    (|LONG-Total − SHORT-Total|)
Penalty factor:   X.XXX (1 − 0.15 × exp(−Diff / 4))
Oversold bonus:   +0% | +5% | +8%   (per W5 conditions)
Final Confidence: XX%
```

The 60% gate is automatically consistent: 36/60 Scorecard-Total = 60% Confidence (before W5 bonus).

### Judge Override (allowed, with mandatory documentation)

The Judge may override the scorecard when at least one Step-1 rating is **demonstrably miscalibrated**. Miscalibration means:
- Sample too small (THIN) was counted as full
- Rating source not cited from Step 1 (forbidden gut-feel point)
- Hard new information has appeared since Step 1 (Trump post, earnings gap)

An override MUST be documented with:
1. **Which rating** is miscalibrated
2. **Why** (one sentence with concrete source reference)
3. **Impact**: scorecard said X, Judge decided Y

This documentation is copied verbatim into the Step-3 card AND the Step-4 trading card — the user must see every override.

### Neutrality Check (hard, before final signal)

- Mirror test: would I let through the **same** arguments at mirrored data (RSI 90 instead of 10, +17% instead of −17%)? Asymmetric = bias.
- Gate is Confidence < 60% OR an active Veto / un-overridden Soft Veto. Everything else ("entered too late", "R/R not perfect", "counter-trend uncomfortable") is a trade-plan adjustment (smaller size, tighter targets), not a signal veto.
- NO-TRADE is a valid result, but only on a real gate violation — not from caution.

### Horizon

**1-3 days primary, up to 5d if structurally justified.** Day+1 to Day+3 is the primary signal, Day+4 to Day+5 is secondary. Medium-/long-term setups are NOT scored. If the 1-3d window shows no edge → signal = NO-TRADE.

Forbidden: "setup active from date X", "come back in Y weeks", "wait for T-7 pre-earnings". These patterns are RISK warnings or watchlist triggers, never trade triggers.

---

## KO Level

Compute per `RULES.md § V1` (Mechanics → ATR-based KO + Chart-based KO + Final selection). Output table:

| Method | Level | Distance |
|--------|-------|----------|
| ATR-based | XX.XX | X.X% |
| Chart-based | XX.XX | X.X% |
| **FINAL** | **XX.XX** | **X.X%** (further of the two) |

If either calculation cannot complete → trade is invalid, abort (V1 is a hard Veto).

---

## Optimal Entry

Run scripts (already pulled in Step 2):

```bash
python3 scripts/reversion_guard.py {{SYMBOL}} --direction <LONG|SHORT>
python3 scripts/entry_calibration.py {{SYMBOL}}
```

Compute the entry per `RULES.md § W4` (Mechanics → Center derivation + half-width formula + four levels + reconciliation).

### Entry Plan Card (mandatory in Step 3 output)

```
╔══════════════════════════════════════════════════════════════╗
║  ENTRY PLAN (limit range, vol-derived) - UNDERLYING          ║
╠══════════════════════════════════════════════════════════════╣
║  Center level:     Stock $XX.XX                              ║
║  Range half-width: $X.XX                                     ║
║                                                              ║
║  1. PRIMARY LIMIT:    Stock @ $XX.XX  (range low)            ║
║     valid until XX:XX CET                                    ║
║                                                              ║
║  2. FALLBACK LIMIT (from XX:XX CET, +60-90 min):             ║
║     Stock @ $XX.XX  (range high)                             ║
║                                                              ║
║  3. ABSOLUTE NO-CHASE LEVEL:                                 ║
║     Stock > $XX.XX  (= Center + 2×half-width)                ║
║     -> trade expires, do NOT buy                             ║
║                                                              ║
║  No market buys, no orders outside the range.                ║
╚══════════════════════════════════════════════════════════════╝
```

**DB record:** `--entry <Center-Level>` — the backtest needs the mid expected fill price. The pre-commit reconciliation in W4 enforces this.

The cert-side translation of this range (cert primary/fallback levels in EUR), the cert leverage selection, and the KO range that Trade Republic should hit are all done in Step 4 — not here.

---

## Trade Plan (underlying)

**Entry (limit center):** XX.XX  |  **KO:** XX.XX  |  **Stop (mental, above KO):** XX.XX

**Profit Exits:**
- 80% SELL at +20% cert gain — immediately
- Rest max +30%, then trail
- Trump event / overnight event → all out per W12

**Loss Exits:** apply per `RULES.md § W9`. The trading card emits all three triggers (Tier 2, Tier 3, Support-Override) with their concrete cert-% / underlying-level values for the current trade — see `prompts/04_summary_send.md § 1` for the card layout. After fill: run `python3 scripts/tr/place_exits.py --isin <CERT_ISIN> --buy <FILL> --shares <N>` to place the real stop-market sell orders + +20% TP alarm per W9.

**SW2 Re-Entry Cooldown:** if `now < exit_ts + 24h` for the candidate symbol, emit the **clamped Trading Card variant** (`prompts/04_summary_send.md § 1a`) and the **clamped DB record** path per `RULES.md § SW2` (Mechanics → NO-TRADE Output Clamp table). Do NOT print Entry Plan / KO / Stop / Sizing / Cert-Request blocks under cooldown.

**Time stops:** 3 days < 5% profit → halve | 5 days sideways → exit | Earnings < 2 days → 50% off

**Expected duration:** 1-3d momentum / 2-4d pullback / 1-2d event. If > 5d → warn explicitly that the cert is not suitable.

---

## Risk Audit

For every active rule in `RULES.md`, evaluate the rule against the current setup. Output **one line per rule**, in this order:

1. Vetos (V1–V5)
2. Soft Vetos (SV1–SV3)
3. Warnings (W1–W12)
4. Soft Warnings (SW1–SW2)

Format per line:

```
- <ID> (<one-line summary from RULES.md>): <STATUS> — <observed value or condition>
```

`<STATUS>` = `PASS` | `VETO` | `OVERRIDE` | `WARN`.

**Decision rules (per severity):**
- Any active **Veto** → signal = NO-TRADE, abort the trade plan.
- Any active **Soft Veto** → signal = NO-TRADE by default. Judge may override; the override line `<ID>-override: <reason>` MUST appear verbatim in the Step-3 card.
- Any active **Warning** → apply the mandated adjustment per `RULES.md § <ID>` (Mechanics block). Signal continues.
- Any active **Soft Warning** → apply the default behaviour per `RULES.md § <ID>`. User may override with explicit acknowledgement.

The full mechanics for each rule live in `RULES.md`. Do NOT duplicate them here. If a rule's status depends on values the Step-1 / Step-2 output does not yet show, fetch the missing input before evaluating (e.g. live Cash via `pytr portfolio` for W1, 60d correlation via `lib/risk_audit.py` for SV2).

**Result:** APPROVED / BLOCKED — [reason citing the rule ID(s) that fired]

---

## Position Sizing

Apply `RULES.md § W6` (Mechanics → Confidence-computation, sizing brackets, compute steps). Before any EUR figure: run the **Sizing Pre-Flight Gate per `RULES.md § W8`** (three checks). Emit each check with the cited source value:

```
SIZING PRE-FLIGHT (per W8):
[ ] 1. Confidence-Bias-Check:  PASS / FLAG
[ ] 2. Correlation/Cluster-Check (SV2):  PASS / SV2-ACTIVE / USER-CONFIRMATION-NEEDED
[ ] 3. Cash-Basis (W1):  PASS / AMBIGUOUS
```

If any check is not PASS → STOP. Do not print the Risk-per-Trade table. Return to user for clarification.

### Risk-per-Trade Table

| Metric | Value |
|--------|-------|
| Cash (live, from `pytr portfolio`) | XXX EUR |
| Position size (XX% of Cash, per W6 bracket) | XXX EUR |
| Scout (XX% of Total) | XXX EUR |
| Confirmation (XX% of Total) | XXX EUR |
| Max loss per trade | XXX EUR |
| Currently at risk | XXX EUR |
| Remaining risk budget | XXX EUR |

(Cert count = Scout EUR / cert ask price — computed in Step 4 once the cert is known.)

---

## Output Card (no JSON)

```
Step 3:
╔══════════════════════════════════════════════════════════════╗
║ JUDGE VERDICT - {{SYMBOL}}                                   ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:            LONG | SHORT | NO-TRADE                   ║
║ Confidence:        XX%   (Raw XX% × penalty XX  + bonus XX)  ║
║ Scorecard diff:    LONG XX / SHORT XX  (Diff=XX)             ║
║                                                              ║
║ Judge override:    YES / NO                                  ║
║   Rating:          <Technical|Price-Action|News|Event>       ║
║   Reason:          <1-2 sentences, source reference>         ║
║   Impact:          scorecard said <X>, Judge decided <Y>     ║
║                                                              ║
║ Reversion-Guard:   <Pullback-Pflicht @ X.XX | No-Edge |      ║
║                     SHORT-NO-TRADE>                          ║
║ Entry (limit ctr): XX.XX (underlying)                        ║
║ Stop (mental):     XX.XX (underlying)                        ║
║ KO (final):        XX.XX  (X.X%, method: ATR|Chart)          ║
║ Target (+20%):     XX.XX (underlying equivalent of +20% cert)║
║                                                              ║
║ Position size:     XX% Cash (XXX EUR)                        ║
║ W6 split:          scout-inverted (40/60) | scout-classic    ║
║                    (50/50)                                   ║
║ Oversold bonus:    NO | +5% | +8%                            ║
║                                                              ║
║ Risk Audit:                                                  ║
║   Vetos:           <list of fired Vetos or "all PASS">       ║
║   Soft Vetos:      <list with override notes if any>         ║
║   Warnings:        <list of fired Warnings + adjustment>     ║
║   Soft Warnings:   <list of fired SW + override notes>       ║
║ Approved:          YES / NO                                  ║
╚══════════════════════════════════════════════════════════════╝

Reasoning: <2-3 sentences, chart + indicator-context + signal>

Next step (Step 4): pick cert + KO range + leverage from formula, attach cert-request card.

[STEP 3 COMPLETE]
```
