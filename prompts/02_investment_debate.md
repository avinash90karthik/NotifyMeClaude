# STEP 2: INVESTMENT DEBATE

**Asset:** {{SYMBOL}}

**Input:** Data + JSON from Step 1. Regime: {{REGIME from Step 1}}.

---

## Regime Weighting

| Regime | Trend signals (SMA, MACD) | Oscillators (RSI, BB) | Overall |
|--------|--------------------------|----------------------|---------|
| TRENDING | x1.3 (dominant) | x0.7 | x1.0 |
| RANGE | x0.7 | x1.3 (dominant) | x1.0 |
| CHOPPY | x1.0 | x1.0 | x0.7 (all weaker) |
| TRANSITIONAL | x1.0 | x1.0 | x1.0 |

Apply this weighting to argument strength throughout the debate.

---

## Round 1: BULL (4-6 sentences per argument, concrete numbers, reference chart)

1. **Technical:** Trend signals, RSI momentum (use delta/divergence from Step 1), MACD, SMA setup
2. **News & Catalysts:** Reference NSI score, cite specific headlines with dates
3. **Fundamental:** Supply/demand, valuation, flows
4. **Macro:** Fed, USD, inflation, geopolitics

**Bull target:** $XX.XX (+XX%) | Confidence: XX% | Time: X weeks

## Round 1: BEAR (4-6 sentences per argument, must REFUTE Bull)

1. **Technical:** Warning signals, overbought/oversold risks, what Bull missed
2. **News & Risks:** Why catalysts are priced in, downside risks
3. **Fundamental Weakness:** What Bull overlooked
4. **Macro Headwinds:** What works against the trade

**Bear target:** $XX.XX (-XX%) | Confidence: XX% | Time: X weeks

## Round 2: Rebuttals (3-4 sentences each)

**Bull rebuts** Bear arguments 1-3 + one new argument.
**Bear rebuts** Bull arguments 1-3 + one new argument.

## Round 3: Final Synthesis (4-6 sentences each)

**Bull Final:** Strongest remaining argument, what couldn't be refuted, adjusted target.
Bull Final Confidence: XX%

**Bear Final:** Strongest remaining argument, what couldn't be refuted, adjusted target.
Bear Final Confidence: XX%

---

## SHORT Trade Scorecard (MANDATORY)

| Criterion (0-10 each) | LONG | SHORT |
|------------------------|------|-------|
| Technical Signals | /10 | /10 |
| News Momentum | /10 | /10 |
| Fundamentals | /10 | /10 |
| Macro Environment | /10 | /10 |
| Chart Pattern | /10 | /10 |
| Risk/Reward | /10 | /10 |
| **TOTAL** | **/60** | **/60** |

**If SHORT >= LONG or difference < 5:** Develop concrete SHORT setup (entry, KO, target).
**If LONG clearly better (>10 pts):** Proceed as LONG.
**If unclear (5-10 pts):** Develop both for Step 3.

---

## Output

```json
{
  "step": 2,
  "symbol": "{{SYMBOL}}",
  "bull_target_usd": 0.00,
  "bear_target_usd": 0.00,
  "bull_confidence_pct": 0,
  "bear_confidence_pct": 0,
  "scorecard": { "long_total": 0, "short_total": 0 },
  "strongest_bull_arg": "...",
  "strongest_bear_arg": "...",
  "recommended_direction": "LONG|SHORT|BOTH"
}
```

```
[STEP 2 COMPLETE]
```
