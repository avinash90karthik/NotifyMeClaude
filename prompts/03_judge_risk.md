# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}
**Input:** Step 1 raw data + Step 2 debate output (both in current context).

Goal: Translate the Step-2 reasoning into a concrete trade plan — direction, trade window, KO range, targets, position size, and the cert-stop staircase rule — by directly reading the Step-1 raw bars. No script-derived verdicts. No fixed scoring formulas. The LLM does the reasoning, citing specific bars/levels from Step 1.

Cert selection, leverage, and KO-range matching for the certificate are Step 4. This step works on the underlying only.

---

## 1. Direction Decision

Read Step 2's Asymmetry tag and conviction values:

| Step 2 Asymmetry | Action |
|------------------|--------|
| `clear-LONG` | Direction = LONG |
| `clear-SHORT` | Direction = SHORT |
| `balanced` | NO-TRADE — both sides have standing arguments, edge unclear |
| `both-weak` | NO-TRADE — neither side made a real case |

For NO-TRADE: skip directly to the Output Card, fill `Signal: NO-TRADE` and `Reasoning` with the abort cause, leave trade-plan fields empty or as `—`. No further sections needed.

For LONG/SHORT: continue.

(Hard stops were checked in Step 0 — not re-checked here.)

## 2. Final Confidence

Derive a single Final Confidence (0-100%) from Step 2's two conviction values, the standing un-rebutted points, and the Notes for Step 3.

The Final Confidence reflects how strongly the LLM believes the trade thesis after weighing both sides:
- Strong asymmetry with the losing side rebutted → Final Confidence close to the winning conviction
- Strong asymmetry but with un-rebutted counter-points → Final Confidence noticeably lower than the winning conviction
- Confidence drives position sizing in §6

State the Final Confidence with a one-sentence reason. Be honest, not optimistic.

## 3. Trade Window

Identify a price range and time validity within which entering the trade is acceptable. The current price may already be inside the window (fill possible today) or outside (wait for retracement, fill possible within the next sessions).

Read Step-1 raw bars (OHLCV_DAILY last 60 bars + OHLCV_INTRADAY last 5 sessions) and identify:

1. **Recent support/resistance levels for THIS stock** — multi-touch zones, volume-confirmed reversals, prior resistance flips. Cite specific dates from the bars.
2. **Current price location** relative to those levels.
3. **Reasonable entry range** for the chosen direction:
   - LONG: between strongest nearby support (range low) and current price or slightly above (range high)
   - SHORT: between current price or slightly below (range low) and strongest nearby resistance (range high)
4. **No-chase level**: where entering would mean buying into a stop-cascade or chasing a breakout.

If the current price is **outside** the trade window, recommend that the user sets a **Trade Republic price alarm** at the closer edge of the entry range (range high for LONG-waiting-for-pullback, range low for SHORT-waiting-for-bounce). This prevents missing the fill while waiting passively.

Validity: 3 trading days from now. After expiry, re-evaluate from scratch (new run, new step1, new debate).

### Entry-Range Reachability Cap (mandatory)

Read the average daily range (H − L) / C over the last 14 daily bars from
OHLCV_DAILY. The entry range MUST be reachable in the trade horizon:

- Range_low for LONG (or range_high for SHORT) distance from current price
  must not exceed:    horizon_days × avg_daily_range × 1.5

  Example: 3-day horizon, avg daily range 5% → max distance 22.5% — but see
  also the absolute caps below, which usually bind first.

- Absolute caps (whichever is tighter):
    1-3d horizon:  max 7% from current price to far edge of entry range
    5d horizon:    max 12% from current price to far edge of entry range

If the structurally-strongest support/resistance lies beyond this cap, the
LLM has two options — pick one and state it:

  (a) Use a closer, weaker support/resistance level inside the cap.
      Acknowledge the level is weaker; tighten KO accordingly.
  (b) NO-TRADE with reasoning: "structural entry is beyond reachability cap
      — wait for natural pullback over multiple sessions before re-evaluating."

Forbidden: emitting an entry range whose far edge is beyond the cap and
labeling it "wait for pullback". A wait that statistically won't happen in
the horizon is not a plan, it's a wish.


### Entry-Trigger Specificity Rule

If the trade window includes a "wait for confirmation" condition (cash-open behavior, intraday reversal, breakout retest, support hold), the condition MUST be specified as a concrete bar-pattern, never a single price threshold.

  WRONG:  "AAPL holds $275+ at cash-open"
  RIGHT:  "On 5-min bars after 15:40 CET — Bar N high ≥ $277.00,
           Bar N+1 high > Bar N high, Bar N+1 low > Bar N low
           (Higher High + Higher Low structure)"

Reasoning: a single price print can be a spike that's immediately distributed. Two-bar structure rules out the spike-fade case. Required components:

1. Time window (after when, until when)
2. Bar interval (1m / 5m / 15m)
3. Structural condition (HH+HL, breakout-with-retest, range-expansion, etc.)

If the user observes cert-side only, additionally provide cert-equivalent levels using actual Hebel × Verhältnis × EURUSD sensitivity. Output Card includes both underlying and cert-side trigger levels in this case.

## 4. KO Level

The LLM determines the KO level from raw Step-1 data. No script, no fixed formula. The KO is a **trade-defining value** — the LLM must justify it with concrete references to bars and structure.

Required reasoning includes:

1. **Where does the trend break?** Cite the specific swing low/high (LONG/SHORT) where a break would invalidate the setup. Reference the date and price from OHLCV_DAILY.
2. **Buffer below/above the trend-break level** — typically 0.5-1.5% to absorb normal intraday volatility without false KO trigger. The LLM justifies the chosen buffer based on this stock's recent daily-range behaviour, read directly from the last 14 daily bars in `OHLCV_DAILY` (high − low per day, plus overnight gaps).
3. **Distance range from entry-range to KO** — because Entry is a range (§3), the KO distance is also a range. Compute distance from both ends of the entry range to the KO level. Audit information for the user.

The KO must not be too close (frequent false-outs from normal volatility) nor too far (R/R ratio destroyed). Both errors are equally bad. The LLM commits to a specific KO level with explicit reasoning.

**Volatility sanity**: if the average true range over the last 14 daily bars is greater than ~6% of price, the 1-3d horizon becomes stressful for KO math — a single average daily move could trigger the KO. Examine the trade plan particularly carefully in such cases.

**The KO distance defines the cert leverage.** Mathematical relationship: Leverage ≈ 100 / KO-distance%. Step 4 inherits this leverage from the actual fill price (which falls somewhere in the entry range) and the KO level chosen here.

If no defensible KO level can be identified from the raw bars (no clear trend-break structure, recent daily-range volatility too large for the trade horizon): discuss this with the user before aborting. Sometimes a wider KO with a smaller position size is acceptable; sometimes the trade should genuinely be skipped. Don't unilaterally NO-TRADE — surface the constraint and let the user decide.

## 5. Targets and Cert-Stop Staircase

Targets are **underlying price levels**. Stops are placed on the cert side (cert-percentage drawdown), not the underlying — Step 4 calculates the concrete cert prices from the chosen cert's ask. Per-stock leverage characteristics differ (NVDA cert at 5x behaves differently from ENR.DE cert at 5x due to volatility, liquidity, KO mechanics) — Step 4 handles this.

**Target 1 (Underlying):** First take-profit level — identified from the next significant resistance (LONG) or support (SHORT) above/below entry, OR a realistic 1-3d move given the recent daily-range pattern in `OHLCV_DAILY`.

**Target 2 (Underlying):** Stretch target — further resistance/support level.

### Cert-Stop staircase (uniform across all trades, calculated in Step 4)

After fill, three stop-market orders are placed via pytr on the cert:

- Cert at -10% from fill price: sell 33% of position
- Cert at -17% from fill price: sell 33% of position
- Cert at -25% from fill price: sell remaining 34%

Rationale: full-entry-then-managed-exit. Three escalating stops force discipline before the KO is reached. The KO level (defined in §4) is the ultimate Trade Republic auto-knockout — it should not be reached if the staircase stops trigger as designed. KO is backstop, not normal exit.

Step 4 calculates the concrete cert price levels for these stops based on the chosen cert and its ask price.

### R/R Reasoning (mandatory before commit)

Before emitting the Output Card, the LLM evaluates the trade geometry:

- Distance from entry-range to Target 1 vs. distance to KO
- Distance from entry-range to Target 2 vs. distance to KO
- Realistic probability of reaching Target 1 / Target 2 in 1-3 days given the recent daily-range pattern

The LLM judges whether the geometry justifies the trade. A typical Range-Bound-Setup with high probability can work at lower R/R; a Breakout with lower probability needs higher R/R. No fixed threshold — explicit reasoning required.

**Important**: Targets must be derived from real resistance/support structure or realistic 1-3d moves implied by recent daily ranges — never adjusted post-hoc to make the R/R math look better. R/R is a test of the trade plan, not an input.

If the geometry doesn't work cleanly (KO too wide for available upside, Target too close, daily-range volatility insufficient for the move in 1-3d): discuss with the user. There may be acceptable adjustments (lower Target with smaller cert gain expectation, smaller position size to compensate for poor R/R). Don't unilaterally NO-TRADE.

State the R/R ratios explicitly in the Output Card with one sentence on why the LLM judges the geometry as acceptable (or not).

### Mandatory Expected Value Calculation when T1/KO < 1.0

If Target1/KO ratio falls below 1.0× (cert reaches T1 with smaller % gain than Stop 3 reaches with % loss), explicit EV math is mandatory:

  Win_pct  = 0.75 × T1_cert_gain_pct + 0.25 × T2_cert_gain_pct
  Loss_pct = effective stop loss at Stop 3 (account for modified staircase)
  Break-even hit-rate = Loss_pct / (Win_pct + Loss_pct)
  EV = Final_Confidence × Win_pct − (1 − Final_Confidence) × Loss_pct

State all four numbers in the Output Card. Reject the trade if either:

- EV < +5% per trade, OR
- Break-even hit-rate > Final Confidence × 0.90

Rationale: R/R ratios hide the hit-rate × payoff interaction. Sub-1.0× R/R trades are acceptable only when hit-rate margin is meaningful — never assumed.

### Exit Logic After Fill (via pytr)

Standard staffelung, identisch über alle Trades:

- **At Target 1**: sell 75% of position. Move stop to break-even (Stop 1 cancelled, Stop 2 and Stop 3 cancelled, new stop placed at fill price). After Target 1: no more loss possible on the remaining 25%.
- **At Target 2**: sell remaining 25% (full exit)
- **Cert-stop staircase before Target 1**: triggered automatically by the three stop-market orders placed in Step 4 (-10% / -17% / -25% cert drawdown, 33/33/34% size)

No discretionary trail-vs-exit decisions per trade — consistency over optimization.

**Time stops:**
- End of Day 1 with no movement (cert flat or negative): consider 50% exit — the setup thesis is not playing out
- 3 days < 5% profit on cert: halve position
- 5 days sideways: exit fully
- Earnings < 2 trading days away: 50% off regardless of position state

## 6. Position Sizing

Sizing brackets driven by Final Confidence — these are **target sizes**, not
upper bounds. The LLM uses the bracket value unless §6.1 reduction rules
explicitly apply.

| Final Confidence | Target Position Size (% of cash) |
|------------------|----------------------------------|
| < 55%            | NO-TRADE                         |
| 55-59%           | 9%                               |
| 60-69%           | 14%                              |
| 70-79%           | 17%                              |
| 80-89%           | 20%                              |
| ≥ 90%            | 22% (rare)                       |

Hard cap: never above 22% of cash on a single turbo.

### 6.1 Reduction Rules (LLM may reduce, but only for these reasons)

The LLM may size below the bracket only if one or more of the following
specific conditions apply. Each invoked reduction must be named explicitly
in the Output Card with a one-sentence justification — vague references to
"caution" or "general risk" are not valid reasons.

- **R1. Macro event inside trade horizon** — Fed/CPI/FOMC release falls
  within the time-stop window. Reduce by one bracket step (e.g. 14% → 9%).

- **R2. Sector concentration** — this trade would push a single sector
  above 25% of equity, OR all open positions would share the same direction
  (all-LONG or all-SHORT) with this trade making the third such position.
  Reduce by one bracket step.

- **R3. Stock-specific volatility flag** — average daily range over last
  14 bars exceeds 6% of price (the §4 volatility-sanity threshold). Reduce
  by one bracket step.

- **R4. Geopolitical / Trump-Hit** — Trump-Hit or active geopolitical
  trigger directly affecting this ticker or sector within the trade
  horizon. Reduce by one bracket step.

- **R5. Mode B Drift Audit** shows 1-2 corrective changes (3+ is already
  Hard NO-TRADE per §8). Reduce by one bracket step per corrective change,
  max two steps.

Stacking: maximum cumulative reduction is two bracket steps. Below that,
the trade should be re-evaluated for NO-TRADE rather than sized down to
near-zero.

Forbidden reductions:

- "Felt cautious" / "want to be safe" without naming a specific R-rule
- "Bear case has some merit" — the Bear case is already weighted into
  Final Confidence; double-counting it via size reduction is not allowed
- Reduction below 5% of cash — at that point the trade is too small to
  matter; emit NO-TRADE instead

### 6.2 Output

The position-sizing block of the Output Card uses this format:

    Cash:                XXX EUR  (live, from pytr portfolio)
    Bracket target:      XX% per Final Confidence X%  (= XXX EUR)
    Reductions applied:  none | R1 | R2 | R3 | R4 | R5  (one line per applied)
    Position size:       XXX EUR  (final, after reductions)
    Max loss per trade:  XXX EUR  (assuming KO hit on full position)

Cert count = Position EUR / cert ask price → computed in Step 4 once cert
is selected.

**Full position at entry** — no Scout/Confirmation split.

## 7. Risk Audit

Four mandatory checks, each addressed explicitly in 1-2 sentences:

1. **Macro Timing**: any Fed/CPI/FOMC within trade window? Other macro events in next 3-5 days that could whipsaw the trade?
2. **Sector Concentration**: would this trade push sector exposure above comfort? (cite Step 1.6 sector_after_this_trade)
3. **Trump/Geopolitical**: Trump-Hit on this ticker in last 7d? Active geopolitical triggers that could affect this stock?
4. **Per-Stock Conditioning**: at least one explicit per-stock observation that affects the trade — e.g., "this stock has historically faded after 5+ consecutive green days, currently at 6", or "daily ranges have widened 40% in the last 5 sessions, KO buffer adjusted accordingly".

After the four checks, 2-3 sentences of free reasoning covering anything not captured above (standing un-rebutted Bear/Bull points from Step 2, unusual volume patterns, etc.).

If any check reveals a severe risk that the trade plan does not adequately address: state it clearly and discuss with the user before aborting.

## 8. Re-Run Logic (when re-running same symbol within 24h)

Two distinct re-run modes — the LLM identifies which one applies:

### Mode A: Trigger-Fired Re-Run

Triggered when: the original plan set a TR price alarm or entry-trigger
condition, the alarm/trigger fired, and the re-run is the consequence.

Original plan must have been emitted with Final Confidence ≥ 55% and an
explicit trigger. If yes → run the Catastrophic Event Check, NOT a full
Bull/Bear/Judge cycle.

#### Catastrophic Event Check (only blocks execution if YES on any item)

1. Earnings surprise on this stock since original plan? (yfinance .earnings,
   compare to last_4_reports in step1_data.md)
2. Material company-specific news since original plan? (M&A announcement,
   fraud, SEC action, guidance withdrawal, CEO change, major recall) —
   read WEB_NEWS_LAST_7D and YFINANCE_NEWS, compare timestamps to
   original_run.completed_at.
3. Market regime break since original plan? Any of:
     - VIX up > 50% from original_run VIX
     - SPX (or relevant index for DE stocks: DAX) down > 3% intraday
     - Sector ETF (SMH for semis, XLF for financials, etc.) down > 4% intraday
4. Per-stock structure break? Has the stock printed a daily close BELOW the
   KO level from the original plan since the plan was emitted? (KO break =
   thesis was wrong, abort.)

If all four = NO: execute the original plan as written. Position size, KO,
targets, staircase = identical to original. Skip Bull/Bear re-debate, skip
Drift Audit. Emit a short confirmation card with the original parameters.

If any = YES: escalate to full Mode B (User-Initiated Re-Run) and run the
Drift Audit on top.

Rationale: the original plan defined the trigger condition deliberately
(e.g. "LONG on pullback to $545"). The trigger firing IS the entry signal —
re-debating the case at trigger price systematically introduces fresh Bear
arguments (negative momentum, weak intraday tape) that did not exist when
the plan was made and could not have been anticipated, because the trigger
itself produces them. This is the bug that turned MU and AAPL into missed
+40% / +300% moves in early May 2026.

### Mode B: User-Initiated Re-Run

Triggered when: the user explicitly requests a fresh look at the symbol
without an original-plan trigger having fired (or triggered in Mode A
escalated up).

Run full Step 1 → 2 → 3 pipeline. Then enumerate every parameter that
changed vs. the prior plan and classify each as:
- corrective (narrows, reduces, constrains, adds gate)
- structural (different direction, fundamentally different thesis)
- neutral (refinement without tightening)

| Corrective changes | Action |
|---|---|
| 0–2 | Continue normally |
| 3+  | Hard NO-TRADE — log all corrections in DB reason field |

Common corrective changes to count: Final Confidence reduced, Position size
reduced, Entry range tightened, Time stop shortened, Stop staircase
modified, new conditional entry gate added, R/R ratio worsened.

Rationale: a setup needing three or more corrective patches on a fresh
user-initiated look has structurally deteriorated. Removing one patch to
"get back under 3" is sunk-cost rationalization — the count is the signal.

---

## Output Card

```
Step 3: Judge Verdict — {{SYMBOL}}

Signal:           LONG | SHORT | NO-TRADE
Final Confidence: XX%

TRADE WINDOW (3 trading days validity):
  Entry range:    $XX.XX  -  $XX.XX
  Range basis:    <one sentence citing specific bars/levels from Step 1>
  Current price:  $XX.XX  (inside range | above, wait for retrace | below, wait for bounce)
  No-chase level: $XX.XX
  TR alarm:       <if outside range: suggest TR price alarm at closer edge>

KO LEVEL:
  KO:             $XX.XX
  Distance range: X.X%-X.X% (from entry-range low / high to KO)
  Reasoning:      <1-2 sentences citing the trend-break level and chosen buffer>

TARGETS (Underlying):
  Target 1:       $XX.XX  (75% exit + move stop to BE)
  Target 2:       $XX.XX  (remaining 25% exit)
  R/R geometry:   Target1/KO ≈ X.X× | Target2/KO ≈ X.X× | reasoning: <one sentence>
  Cert hint for Step 4: leverage that maps Target 1 to ~+10-15% cert gain, Target 2 to ~+20% cert gain

CERT-STOP STAIRCASE (calculated in Step 4 from chosen cert):
  -10% cert: sell 33%  |  -17% cert: sell 33%  |  -25% cert: sell 34%
  After Target 1: stops cancelled, new stop at break-even (fill price)

POSITION SIZING:
  Cash:           XXX EUR
  Bracket max:    XX% (XXX EUR)
  Actual size:    XXX EUR  (reason if reduced: <...>)
  Max loss:       XXX EUR

RISK AUDIT:
  Macro timing:        <1-2 sentences>
  Sector:              <1-2 sentences>
  Trump/Geopolitical:  <1-2 sentences>
  Per-stock conditioning: <1-2 sentences>
  Other risks:         <2-3 sentences>

Reasoning:        <3 sentences: what makes this trade work, what could break it, why these specific levels>

Next step (Step 4): cert selection, leverage, KO-range matching, trading card emission, place_exits.py integration.

[STEP 3 COMPLETE]
```

## Persistence

Write the full Step 3 output (sections 1-7 + Output Card) to:
```
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step3_judgment.md
```

Overwrite if file exists.

## What Step 3 does NOT do

- Does not pick the certificate (ISIN, leverage) — that is Step 4
- Does not place orders — that is Step 4 with `place_exits.py` after fill
- Does not re-fetch raw data — Step 1 output is in current context
- Does not specify cert-side stop levels — those are calculated in Step 4 from the chosen cert ask price
- Does not unilaterally NO-TRADE on geometry or KO problems — surfaces the constraint and discusses with the user first
