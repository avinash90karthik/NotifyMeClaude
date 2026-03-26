# Strategy v6 Draft — Risk/Reward Fix

## Problem with v5
- Wins: +20% on 50% = +10% effective gain
- Losses: -60% (MU was -68%)
- Need 6 wins per loss → requires 86% win rate → unrealistic
- Result: negative P&L despite 50% win rate

## v6 Core Changes (on top of v5)

### 1. Take 66% at +20% (was 50%)
- Effective gain: +13.2% (was +10%)
- More profit secured, smaller runner (34% instead of 50%)
- Trail stop on remaining 34% unchanged

### 2. Forced Re-Analysis at -20%
- At -20% cert loss: STOP. Re-run thesis check.
- Is the thesis still intact? → Hold to original stop
- Is the thesis broken? → Close immediately at -20%
- This cuts average loss from -60% to -20% in most cases

### 3. v5 Staged Entry remains
- Scout (60%) immediately on signal
- Confirmation (40%) on green follow-up day or +5%
- If Scout fails before Confirmation → loss is only 60% × 20% = -12%

## Math Comparison

| Strategy | Eff. Gain | Eff. Loss | Wins per Loss | Min Win Rate |
|----------|-----------|-----------|---------------|--------------|
| v5 current | +10% | -60% | 6.0x | 86% |
| v6 (66% + review) | +13.2% | -20% | 1.5x | 60% |
| v6 Scout-only fail | +13.2% | -12% | 0.9x | 48% |

## v6 Exit Rules

```
EXITS (v6):
+20% → 66% OUT immediately (was 50%)
Rest (34%): trail stop to BE, then:
  +30% → stop +15%
  +40% → stop +25%
  +50% → stop +35%

STOP (v6):
-20% cert loss → FORCED RE-ANALYSIS
  Thesis intact → hold to original stop
  Thesis broken → close immediately
  Unsure → halve position

Original stop still exists as absolute backstop.
```

## Rules unchanged from v5
- 60% confidence gate
- Max 3 positions
- Scout 60% / Confirmation 40%
- KO ≥ 2x ATR (commodities 3x)
- Max 10% portfolio loss per trade
- Max 40% simultaneously at risk
- Time stops: 3d <5% halve, 5d exit
- Hedge system for 2 LONGs + macro risk

## Status: DRAFT — needs backtesting against prediction_db
