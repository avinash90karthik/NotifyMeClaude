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

**1-5 days only.** Medium-/long-term setups are NOT scored. If 1-5d shows no edge -> signal = NO-TRADE.

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

**Exits (v9, replaces v5/v8):**
- 80% SELL at +20% cert gain - immediately
- Rest max +30%, then trail
- Trump event / overnight event -> all out

**Time stops:** 3 days < 5% profit -> halve | 5 days sideways -> exit | Earnings < 2 days -> 50% off

**Expected duration:** 1-3d momentum / 2-4d pullback / 1-2d event. If > 5d -> warn explicitly that the cert is not suitable.

---

## Risk Audit

### V Vetos (hard - one active V means signal = NO-TRADE)

| # | Rule | Value | Status |
|---|------|-------|--------|
| V1 | ATR > 7%? (warrants/options instead of KO) | ATR=X.X% | PASS/VETO |
| V2 | CHOPPY + Score < 50? | Regime=X, Score=X | PASS/VETO |
| V3 | ≥ 3 open positions? | X/3 | PASS/VETO |
| V4 | Sector > 60%? | Sector: X% | PASS/VETO |
| V5 | Monthly drawdown > 20%? | P&L: X% | PASS/VETO |

### W Warnings (modify trade-plan ONLY, no confidence penalty)

| # | Rule | Effect when active | Status |
|---|------|--------------------|--------|
| W1 | Earnings < 5 days | KO multiplier +0.5 | PASS/WARN |
| W2 | Correlation to open position | Halve size | PASS/WARN |
| W3 | KO < 2× ATR (too tight) | Push KO out, raise multiplier | PASS/WARN |
| W5 | Overnight event < 24h (FOMC/CPI/NFP/Trump/Earnings) | Overnight rule (below) | PASS/WARN |

**W5 Overnight Protection** (from `memory/strategy_v9.md` § Overnight Event Rule):
- Position ≥ +10% -> stop to BE (mandatory)
- Position ≥ +15% -> 50% partial exit or stop to +5%
- Position < +10% -> default = close, or document risk acceptance
- Friday: always BE-stop before the weekend

**Result:** APPROVED / BLOCKED - [reason]

---

## Position Sizing (v9: Scout-inverted sizing for borderline confidence)

> **Hard Rule (8): All position recommendations are in % of portfolio**, never in absolute EUR. Reason: portfolio value changes, ratios are stable. The cert count in EUR comes only at the end of Step 4 (`Scout EUR / cert ask price`).

**Rule 20:** At Confidence 60-65% the Scout is **smaller** than the Confirmation (40/60 instead of 60/40). From ≥65% the classic split (60/40).

| Confidence | Total (% portfolio) | Scout % of Total | Confirmation % of Total | Scout (% portfolio) | Confirmation (% portfolio) |
|------------|---------------------|------------------|-------------------------|---------------------|----------------------------|
| 60-65% | 15% | **40% (inverted)** | **60%** | 6% | 9% |
| 65-70% | 20% | 60% | 40% | 12% | 8% |
| 70%+ | 25% | 60% | 40% | 15% | 10% |

**Rationale (from backtest 2026-04-16):** the 60-65% confidence bracket has only 56% accuracy and +0.33% avg move (coin-flip). Inverted Scout reduces damage on a wrong signal; Confirmation buy after confirmation (Scout at least +5% in profit) deploys the main size only on real trend confirmation.

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
