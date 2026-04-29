# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}
**Input:** Step 1 bullets + ratings | Step 2 scorecard + Bull/Bear synthesis.

This step produces the **stock trade plan only** (signal, confidence, entry/stop/KO/target on the underlying, position sizing in EUR). Cert selection, leverage formula, and KO-range for the certificate live entirely in Step 4. Do not propose a cert here.

---

## Judge Verdict

### Signal + Confidence (formula, not free-form list)

```
Direction      = LONG if Scorecard-LONG-Total > Scorecard-SHORT-Total, else SHORT
Raw Confidence = max(LONG-Total, SHORT-Total) / 60 × 100   (%)

Smooth differential penalty (replaces the old < 10 / >= 10 cliff):
  Diff = |LONG-Total - SHORT-Total|
  penalty_factor = 1 - 0.15 * exp(-Diff / 4)

  Diff = 0  -> 0.85
  Diff = 4  -> 0.94
  Diff = 10 -> 0.987
  Diff = 20 -> 0.999

  Confidence = Raw Confidence × penalty_factor

v9 Oversold Bonus (Rule 19) - LONG only:
  Indicator-Context RSI band <20 + Fwd5 green ≥ 65% + n ≥ 20  ->  +5% confidence
  Indicator-Context RSI band <15 + Fwd5 green ≥ 70% + n ≥ 20  ->  +8% confidence (capitulation)
  Bonus is added AFTER the differential penalty.
```

The Gate is automatically consistent: 36/60 = 60% = trade gate (before oversold bonus).

### Judge Override (allowed, with mandatory documentation)

The Judge may override the scorecard when at least one Step-1 rating is **demonstrably miscalibrated**. Miscalibration means:
- Sample too small (THIN) was counted as full
- Rating source not cited from Step 1 (forbidden gut-feel point)
- Hard new information has appeared since Step 1 (Trump post, earnings gap)

An override MUST be documented with:
1. **Which rating** is miscalibrated
2. **Why** (one sentence with concrete source reference)
3. **Impact**: scorecard said X, Judge decided Y

This documentation is copied verbatim into the Step-3 card AND the Step-4 trading card - the user must see every override.

### Neutrality Check (hard, before final signal)

- Mirror test: would I let through the **same** arguments at mirrored data (RSI 90 instead of 10, +17% instead of -17%)? Asymmetric = bias.
- Gate is Confidence < 60% OR an active V-veto. Everything else ("entered too late", "R/R not perfect", "counter-trend uncomfortable") is a trade-plan adjustment (smaller size, tighter targets), not a signal veto.
- NO-TRADE is a valid result, but only on a real gate violation - not from caution.

### Horizon

**1-3 days primary, up to 5d if structurally justified.** Empirical v10 observation 2026-04-28: trades almost never reached full 5d — limit or stop triggered earlier (median hold time 1-3d). Day+1 to Day+3 is the primary signal, Day+4 to Day+5 is secondary. Medium-/long-term setups are NOT scored. If the 1-3d window shows no edge -> signal = NO-TRADE.

Forbidden: "setup active from date X", "come back in Y weeks", "wait for T-7 pre-earnings". These patterns are RISK warnings or watchlist triggers, never trade triggers.

---

## KO Level (on the underlying)

> **Hard Rule (5): KO is computed, never estimated.** Both methods (ATR-based + chart-based) MUST be calculated; the "further of the two" is the final KO. No gut-feel KO levels - if calculation fails (e.g. ATR unavailable), the trade is invalid, not "estimated". See `memory/strategy_v9.md § Why Rule 5` for the post-mortem.

KO = the level that is FARTHER from the price (ATR-based or chart-based).

### A - ATR-based KO

| Asset Class | Multiplier | Criterion |
|-------------|------------|-----------|
| Large Cap | 2.0× ATR | Market Cap > $50B |
| Mid/Small Cap | 2.5× ATR | Market Cap < $50B |
| Commodities | 3.0× ATR | Futures (=F suffix) |
| Crypto-related | 3.0× ATR | BTC/Crypto exposure |

Multiplier surcharges (push KO further):
- ATR5/ATR14 > 1.5 (vol spike) -> +0.5
- Earnings < 5 days -> +0.5

```
ATR-KO (LONG)  = price - (ATR × multiplier)
ATR-KO (SHORT) = price + (ATR × multiplier)
```

### B - Chart-based KO

Strongest support (LONG) or resistance (SHORT) from Step 1 § 1.4, + 0.5-1% buffer.

### C - Final KO

| Method | Level | Distance |
|--------|-------|----------|
| ATR-based | XX.XX | X.X% |
| Chart-based | XX.XX | X.X% |
| **FINAL** | **XX.XX** | **X.X%** (further of the two) |

---

## Optimal Entry (Rule 18 + Rule 22, script-driven)

```bash
python3 scripts/reversion_guard.py {{SYMBOL}} --direction <LONG|SHORT>   # already pulled in Step 2
python3 scripts/entry_calibration.py {{SYMBOL}}                          # intraday-dip statistics + buy range
```

### Verdict logic

| Reversion-Guard says | Entry-Center rule | entry_price in DB |
|----------------------|-------------------|-------------------|
| LONG: Pullback-Pflicht | Center = Close - 1×ATR | Center level |
| LONG: Kein Reversion-Edge | Center = Buy-range upper (P25 dip) | Center level |
| LONG: real breakout (no reversion setup, R1 break) | Center = trigger level | Trigger level |
| SHORT: valid | Center = Close + 1×ATR OR extension-break level | Trigger level |
| SHORT: NO-TRADE | abort setup | - |

**Hard:** `prediction_db.py record --entry` = **Center level** of the range (not Primär, not Fallback), never the close. HDD.DE #82 is the post-mortem reason for this rule.

### Limit Range instead of point value (vol-derived, MANDATORY)

A point limit ("exactly $89.00") systematically misses fills when the market only just touches the value. Instead: **range around center level**, width from volatility.

**Formula:**
```
Range half-width = max(0.25 × ATR, 0.5% × Close, 0.10 EUR)
Primary level    = Center - half-width  (optimistic, better fill price)
Fallback level   = Center + half-width  (defensive, higher fill probability)
```

- `0.25 × ATR` is the basic vol component - reflects the stock-specific intraday noise level
- `0.5% × Close` is the floor for low-ATR names (e.g. SAP: ATR 2% -> range would otherwise be too tight)
- `0.10 EUR` is the absolute minimum tick floor (warrants/turbos whose spread step > computed range)
- Max of all three = final half-width

**Fallback trigger time:** 60-90 minutes after primary order placement (at US-open entry typically 11:00-11:30 NY / 17:00-17:30 CET). Do not raise the order before the trigger.

### Entry Plan Card (mandatory in Step 3 output)

```
╔══════════════════════════════════════════════════════════════╗
║  ENTRY PLAN (limit range, vol-derived) - UNDERLYING          ║
╠══════════════════════════════════════════════════════════════╣
║  Center level:     Stock $XX.XX                              ║
║  Range half-width: $X.XX  (max(0.25×ATR, 0.5%, 0.10€))       ║
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

**DB record:** `--entry <Center-Level>` - the backtest needs the mid expected fill price, not the optimistic or defensive one.

The cert-side translation of this range (cert primary/fallback levels in EUR), the cert leverage selection, and the KO range that Trade Republic should hit are all done in Step 4 - not here.

---

## Trade Plan (underlying)

**Entry (limit center):** XX.XX  |  **KO:** XX.XX  |  **Stop (mental, above KO):** XX.XX

**Profit Exits (v9, replaces v5/v8):**
- 80% SELL at +20% cert gain - immediately
- Rest max +30%, then trail
- Trump event / overnight event -> all out

**Loss Exits (Rule 26 — Tiered Stop-Strategy, MANDATORY, replaces single-stop):**

Reference unit is **CERT-%**, not underlying-%, because user trades leveraged certs.

> **Hard Rule (26): Stops are tiered, not single-shot.** A single stop-loss waiting for
> KO is the dominant capital-leak in the post-mortem 2026-04-21..27 (n=271 closed
> trades): trades that fell to ≤−15% cert ended on average at **−33%**, and **84%
> of total loss-damage came from the ≤−15% tail**. Disciplined tier-exits would have
> capped the tail at −15% to −25% instead of −35% to −50%.
>
> Rationale and full statistics: `memory/strategy_v9.md § Rule 26 — Tiered Stop`.

```
TIER 2: Cert −15%  →  HARD-EXIT 50% (no discussion, no waiting)
  - Sell 50% IMMEDIATELY
  - Remaining 50% gets new mental stop at cert −25%
  - Empirical: ≤−15% cert trades end on Ø −33%; only 16% recover to BE
  - Forbidden: "I think it'll bounce" — bias, not data

TIER 3: Cert −25%  →  HARD-EXIT 100% (no exception)
  - Sell ALL, regardless of how nice the chart looks
  - Thesis is empirically falsified
  - Activate Rule 27 Re-Entry-Cooldown
  - Empirical: 84% of historical loss-damage (n=271) came from positions
    that breached this threshold without exit-discipline

SUPPORT-OVERRIDE (technical breakdown trumps tier waits):
  If the UNDERLYING closes below the strongest support level identified
  in Step 1 § 1.4 (typical: SMA50, prior swing low, or 3M-low):
  - Force HARD-EXIT 50% even if cert hasn't hit −15% yet
  - Reason: the technical thesis (uptrend / level holds) is broken;
    waiting for −15% cert is letting more capital follow a dead thesis
  - Document the support level in Step 3 trade plan as "Support-Stop"
    alongside KO and tier levels
  - Cite the level explicitly in the trading card so the user knows
    which underlying close triggers a 50% exit
```

**Why no Tier-1 (−10% watch):** The 4h-watch was operationally unrealistic
for a non-fulltime trader. A rule that can't be executed reliably is worse
than no rule — it generates inconsistent behavior. Tier 2 / Tier 3 / Support
override are the three hard triggers. Removed 2026-04-28 after one full
trading day under the rule showed the watch was never actually used.

**Forbidden patterns (auto-veto in Step-3 reasoning):**
- "Hold to KO and re-enter" — KO is a backstop for runaway gaps, not a managed exit
- "Hedge with opposite cert at −20%" — negative-EV due to spread + dual leverage decay
- "Tighten stop to −2% more" once −25% breached — disciplined exit, not tweak
- Any stop calculation in **underlying-%** for cert-trades — must be cert-%

**Rule 27 — Re-Entry Cooldown (HARD)**

After ANY exit on symbol X (Tier-2/3 stop OR TP+20%):

- 24h cooldown from `exit_ts`.
- During cooldown: pipeline run allowed, output is NO-TRADE-clamped.
- After 24h: normal pipeline run, normal trade possible if the pipeline
  produces a signal.

No re-eval criteria. No +10pp. No +1 NEW catalyst. No extension. No
pre-/post-24h cases.

**Rationale:** The pipeline IS the re-eval criterion. A 70%+ signal with
all V-vetos PASS produced 24h after a stop is qualitatively no worse than
the same signal produced on a never-traded symbol.

**NO-TRADE Output Clamp (mandatory when `now < exit_ts + 24h`):**

| Field | Allowed under cooldown? |
|---|---|
| Signal (clamped to NO-TRADE) | yes, MANDATORY |
| Confidence + 6-axis Scorecard | yes (educational) |
| Reversion-Guard verdict | yes (educational) |
| Statistical Setup Strength block (Trade-Window pattern, Convergence, etc.) | yes (educational) |
| Cooldown Status line + `eligible_at` timestamp | yes, MANDATORY |
| **Entry Plan (Center / Primary / Fallback / NO-CHASE)** | **no** |
| **KO Computation table (ATR-based / Chart-based / FINAL)** | **no** |
| **Stop levels (Tier-2/3 cert pricing)** | **no** |
| **Position Sizing table (EUR amounts)** | **no** |
| **Cert-Request block** | **no** |
| DB Record `--entry / --stop / --target / --ko` | omit (NULL) |
| DB Record `--direction` and `--confidence` | yes, recorded for tracking |

`eligible_at` is always `exit_ts + 24h`.

**Rule 28 — Trader-Day Circuit-Breaker (PENDING, re-evaluate 2026-05-29):**

```
STATUS: Pending. n=12 April evidence is too small to distinguish Tilt vs.
Market-confound vs. Selection-bias. Hard-veto suspended; pipeline runs but
emits [RULE 28 PENDING — TRACKING] notice on Tier-2/3 stop in trailing 32h.

After ANY Rule 26 Tier-2 / Tier-3 / Support-Override exit on any symbol:
  → preflight prints PENDING notice to stderr (does NOT exit)
  → user MUST log the event in memory/v10_log.md (template + decision
    schema there). Without the log entry, the 2026-05-29 evaluation is
    blind and Pending will extend by default.
  → user retains full trade autonomy on new symbols. No magic-string
    override needed.

Tracking required per stop:
  - Date, Symbol, Tier, Realized P&L
  - Same-day follow-up trade outcome (or watchlist pipeline-run if no trade)
  - S&P-500 daily return on stop-day
  - Sector-ETF daily return on stop-day
    (SOXX / ICLN / ARKX / XLK / XLV / XLF — see v10_log.md mapping)

Decision 2026-05-29: schema in memory/v10_log.md, locked in advance.
Possible outcomes: hard-veto restoration | drop entirely | extend tracking.

Restoration mechanic: single-commit revert in scripts/preflight_check.py
(replace pending notice with sys.exit(2)) + update CLAUDE.md hard-rule
list + flip § 11 status in memory/strategy_v9.md.

Background (April 2026): n=12 trades after stop showed 33% win-rate vs 78%
after win. ENR 2026-04-28 (Tier-2 + Tier-3 in 17 min, NVDA scout same day)
is the founding case. Under Pending it is now data, not blocked behavior.
Rule 27 (same-symbol cooldown) remains hard and unchanged — it covers the
worst tilt sub-case (re-entry into the just-stopped symbol).
```

**Time stops:** 3 days < 5% profit -> halve | 5 days sideways -> exit | Earnings < 2 days -> 50% off

**Expected duration:** 1-3d momentum / 2-4d pullback / 1-2d event. If > 5d -> warn explicitly that the cert is not suitable.

---

## Risk Audit

### V Vetos (hard - one active V means signal = NO-TRADE)

| # | Rule | Value | Status |
|---|------|-------|--------|
| V1 | ATR > 7%? (warrants/options instead of KO) | ATR=X.X% | PASS/VETO |
| V2 | CHOPPY + Score < 50? | Regime=X, Score=X | PASS/VETO |
| V3 | ≥ 2 open turbo positions? (hedges excluded) | X/2 | PASS/VETO |
| V4 | Sector > 40%? (AI-semis grouped: NVDA/AMD/AVGO/MRVL/TSM/ASML treated as ONE sector) | Sector: X% | PASS/VETO |
| V5 | Monthly drawdown > 20%? | P&L: X% | PASS/VETO |
| V6 | 60d daily-return correlation to ANY open position ≥ 0,7? | corr=X.XX vs <SYM> | PASS/VETO |

### W Warnings (modify trade-plan ONLY, no confidence penalty)

| # | Rule | Effect when active | Status |
|---|------|--------------------|--------|
| W1 | Earnings < 5 days | KO multiplier +0.5 | PASS/WARN |
| W3 | KO < 2× ATR (too tight) | Push KO out, raise multiplier | PASS/WARN |
| W5 | Overnight event < 24h (FOMC/CPI/NFP/Trump/Earnings) | Overnight rule (below) | PASS/WARN |

> **v10 note (2026-04-28):** V3 tightened from 3→2 open turbo positions (hedges
> excluded). V4 sector cap tightened from 60%→40% with AI-semi grouping.
> W2 (correlation halve-size) was upgraded to **V6** hard veto at 60d daily-
> return correlation ≥ 0,7. April 2026 had two days where AMD-turbo + NVDA-scout
> were simultaneously open with effective 60d-corr ~0,85 — under v9 W2 this
> only halved size; under v10 V6 it would have been a hard veto.
>
> **V6 override:** explicit `"V6-override: <reason>"` citing why correlation
> breakdown is expected (e.g. divergent earnings, sector-rotation thesis).
>
> **V6 indeterminate:** if either symbol has < 60 days of yfinance history,
> V6 returns soft warning ("V6 inconclusive, n<60") and does NOT auto-veto.

**W5 Overnight Protection** (from `memory/strategy_v9.md` § Overnight Event Rule):
- Position ≥ +10% -> stop to BE (mandatory)
- Position ≥ +15% -> 50% partial exit or stop to +5%
- Position < +10% -> default = close, or document risk acceptance
- Friday: always BE-stop before the weekend

**Result:** APPROVED / BLOCKED - [reason]

---

## Position Sizing (v9: Scout-inverted sizing for borderline confidence)

> **Hard Rule (8): All position recommendations are in % of portfolio**, never in absolute EUR. Reason: portfolio value changes, ratios are stable. The cert count in EUR comes only at the end of Step 4 (`Scout EUR / cert ask price`).

### Sizing Pre-Flight Gate (Rule 25, MANDATORY before EUR-Empfehlung)

Before ANY EUR sizing number is written, this block MUST appear in Step 3
output, each check with explicit source citation:

```
SIZING PRE-FLIGHT:
[ ] 1. Confidence-Bias-Check:
       - indicator_context.py Strongest-Axis-Adjust = ±X.XX%
       - My Rating 1 assigned = X/10
       - Consistency check: If adjust > 0 AND Rating 1 < 6/10 → BIAS FLAG,
         reconsider Rating. If adjust < 0 AND Rating 1 > 5/10 → BIAS FLAG.
       - Forbidden words in Rating-1 reasoning: "überkauft", "overbought",
         "exhaustion", "blowoff-reflex" WITHOUT a cited green-rate.
       Status: PASS / FLAG

[ ] 2. W2-Cluster-Check:
       - prediction_db.py portfolio output quoted verbatim
       - Cross-reference against user's LATEST portfolio screenshot in chat
       - Rule: If DB shows position X as open, but screenshot does not →
         DB is stale → W2 NOT applied. Ask user to confirm before halving.
       Status: PASS / W2-ACTIVE / USER-CONFIRMATION-NEEDED

[ ] 3. Portfolio-Total-Basis:
       - Cash (from latest user screenshot): XXX EUR
       - Open positions (confirmed): XXX EUR
       - Incoming cash within 2 trading days (user stated): XXX EUR
       - Portfolio-Base for sizing = XXX EUR
       Status: PASS / AMBIGUOUS
```

**Hard:** If any check is FLAG / USER-CONFIRMATION-NEEDED / AMBIGUOUS →
STOP. Do not print the Risk-per-Trade table. Return to user for
clarification. Never guess.

**Why Rule 25 exists:** Post-mortem 2026-04-24 AMD #125 — three sizing
hammers compounded incorrectly (RSI-bias Rating 1 too low + W2 applied
despite MRVL already closed + stale DB). Correct chain would have been
Total 808 EUR / Scout 485 EUR. Actual applied: 162 EUR Scout. User missed
~104 EUR gain on +22.27% exit purely from sizing chain errors. The
pre-flight gate forces the error surface to become visible before EUR
numbers are committed.

**Rule 20 (v10):** 60-65% Confidence keeps inverted Scout 40/60. From 65%+ flat 20% Total / 50/50 split. The 70%+ tier is **dropped** after April 2026 review.

| Confidence | Total (% portfolio) | Scout % of Total | Confirmation % of Total | Scout (% portfolio) | Confirmation (% portfolio) |
|------------|---------------------|------------------|-------------------------|---------------------|----------------------------|
| 60-65% | 10% | **40% (inverted)** | **60%** | 4% | 6% |
| 65%+ | 20% | **50%** | **50%** | 10% | 10% |

**Rationale (v10, post-April-2026 review):**

The v9 backtest 2026-04-16 showed 65-70% confidence with avg move +8.22% vs 70%+ at +6.83% — risk-adjusted, the 65-70% bracket is the sweet spot. April 2026 live data (n=31) confirmed: trades in the 70%+ size bracket (>€1.500 absolute) had a 25% win-rate and −€1.771 cumulative P&L; trades €1000-1500 had 100% win-rate. Correlation between position size and P&L% on losing trades: −0,66.

The v10 curve drops the 70%+ bracket entirely (single threshold at 65%) and flattens to 20% from there. Scout/Confirm 50/50 above 65% replaces the v9 60/40 split: at 60% accuracy a smaller scout limits damage when Confirm never triggers (~17% less Wrong-Trade exposure vs 60/40). The 60-65% inverted-Scout pattern (Rule 20 original) is unchanged.

The 60-65% bracket Total drops from 15% to 10%, in line with the same April-2026 finding that the smallest confidence bucket also tilted negative on a per-trade basis when coin-flip met an unlucky day.

Re-evaluate after 30 additional trades. If the (now retired) 70%+ bracket shows consistently better risk-adjusted return, re-introduce a higher tier. Not before.

**Compute:**
- Portfolio value from `prediction_db.py portfolio`
- Scout = Portfolio × Scout-% -> divide by cert ask price -> cert count
- Confirmation = Portfolio × Confirm-% -> only after signal confirmation (Scout +5% in profit OR clear regime evidence)

**Card requirement:** Step 3 card and Step 4 order plan must explicitly document whether scout-inversion is active ("v9 scout-inverted" or "v9 scout-classic").

### Risk-per-Trade Table

| Metric | Value |
|--------|-------|
| Portfolio value | XXX EUR |
| Position size (XX%) | XXX EUR |
| Scout (XX% of total - v9 split) | XXX EUR |
| Confirmation (XX% of total - v9 split) | XXX EUR |
| Max loss per trade (10%) | XXX EUR |
| Currently at risk | XXX EUR |
| Remaining risk budget | XXX EUR |

(Cert count = Scout EUR / cert ask price - computed in Step 4 once the cert is known.)

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
║ Position size:     XX% portfolio (XXX EUR)                   ║
║ v9 split:          Scout-inverted (40/60) |                  ║
║                    Scout-classic (60/40)                     ║
║ Oversold bonus:    NO | +5% (RSI<20 green XX%) |             ║
║                    +8% (RSI<15 green XX% capitulation)       ║
║                                                              ║
║ V-Vetos active:    <none | V1/V3/...>                        ║
║ W-Warnings active: <none | W1/W5/...>  -> trade-plan mods    ║
║ Approved:          YES / NO                                  ║
╚══════════════════════════════════════════════════════════════╝

Reasoning: <2-3 sentences, chart + indicator-context + signal>

Next step (Step 4): pick cert + KO range + leverage from formula, attach cert-request card.

[STEP 3 COMPLETE]
```
