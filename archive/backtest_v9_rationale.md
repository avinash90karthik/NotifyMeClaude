# v9 Backtest Rationale (archived)

> v10 (April 2026) supersedes the live rules, but this rationale informed
> the design of W5 (Extreme-Oversold Bonus), W6 (Position Sizing), W9
> (Tiered Stops) and the sigmoid-adjust formulas used in
> `indicator_context.py` and `earnings_pattern.py`. Kept here for
> evidentiary value; not consulted in day-to-day analysis.

## Backtest Rationale (v9)

Date: 2026-04-16. Backtest on 40 filled predictions revealed two patterns
that drove v9.

### 6.1 The forgotten edge under 50% confidence

5 of 40 predictions landed below 50% confidence and were rejected. All 5
moved in the signal direction, average +8.82% fwd-5d, 100% accuracy.

Common pattern:
- RSI extremely oversold (15–30)
- Commodities or stocks after a sharp crash
- System penalties ("TRENDING down", "Pre-Open weak", "CHOPPY") pulled
  confidence below the 60% gate

The stock's own fwd-5d green-rate at RSI <20 was consistently >65% [SOLID].
Regime penalties had overridden this direct mean-reversion evidence. The
Extreme-Oversold-Bonus (now W5) was added to let stock-specific historical
green-rate override regime penalties via a controlled +5% / +8% bonus.

### 6.2 The 60–65% coin-flip bracket

Accuracy by confidence bracket (fwd-5d):

| Bracket | Accuracy | Avg Move |
|---------|----------|----------|
| 60–65% | 56% | +0.33% |
| 65–70% | 60% | +8.22% |
| 70%+ | 75% | +6.83% |

60–65% is effectively a coin-flip. The classic Scout/Confirmation split
(60/40) puts the **larger** initial size into the **least certain** bucket.
Position-Sizing Scout-Inversion (now W6) flips this to 40/60 in the 60–65%
bracket: smaller initial scout to limit damage on a wrong signal, larger
confirmation only after the trend confirms (Scout +5% in profit).

### 6.3 Sigmoid adjusts replace bucket cliffs

Old bucketed mapping (`>65% → +3%`) created arbitrary 2% jumps at bucket
edges (a stock at green-rate 64.9% got +1%, a stock at 65.1% got +3%).
Sigmoid `5 × tanh((g − 0.5) × 4) × sample_weight` gives a smooth curve with
the same asymptotic ±5% bounds and no edge cliffs. Same function used by
`indicator_context.py` (per-axis) and `earnings_pattern.py` (trade-window
mode), with earnings-specific sample thresholds (SOLID n≥8 instead of n≥30)
because earnings sample size is structurally small (max ~10 quarters).

### 6.4 Strongest-Axis aggregation

Naive sum of RSI-adjust + BB-adjust + DistHigh-adjust was wrong because
those three axes are positively correlated for trend stocks (a stock near
3M-high tends to also have high BB and elevated RSI). Summing double-counts
the same underlying signal. Strongest-axis (max |adjust|) is a conservative
single estimate. The strongest-axis aggregation is now formalised as W3.

### 6.5 Smooth differential penalty

Old penalty had a cliff: `Diff < 10 → ×0.9, Diff ≥ 10 → ×1.0`. This means
a scorecard with Diff = 9 got 10% penalty, Diff = 10 got 0% — arbitrary.
New form `1 − 0.15 × exp(−Diff/4)` gives:
- Diff = 0 → 0.85 (max penalty for a tied scorecard)
- Diff = 4 → 0.94
- Diff = 10 → 0.987
- Diff = 20 → 0.999 (effectively no penalty for a clear setup)

No cliff. Reflects the actual confidence we should have in a setup based
on how clearly the scorecard separates the two sides.
