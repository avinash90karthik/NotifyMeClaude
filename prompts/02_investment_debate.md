# STEP 2: INVESTMENT DEBATE

**Asset:** {{SYMBOL}}
**Input:** Bullets + 4 ratings from Step 1.

---

## Rules for the debate

> **Hard Rule (6): The 6-axis scorecard is filled for BOTH directions** in every analysis. SHORT is not optional even when the bull thesis looks obvious - if SHORT-Total >= LONG-Total, that's the setup, regardless of preconceived direction. The mirror test in Step 3 catches asymmetric scoring. See `memory/strategy_v9.md § Why Rule 6` for the rationale.

- Use only data from Step 1. No new numbers, no web searches.
- The four Step-1 ratings (Technical Green-Rate, Price-Action, News+Reddit, Event/Catalyst) are FIXED. The debate may cite, interpret, contextualize - but NOT change them. Anchoring on debate-confidence is the main mistake this structure prevents.
- The debate produces only two NEW values: **Chart Structure** (qualitative, from chart analysis § 1.4) and **Reversion-Edge** (from reversion_guard.py, see below).

## Round 1: BULL (4-6 sentences per argument, concrete numbers, chart reference)

1. **Technical:** cite the indicator-context values from Step 1 (RSI band green-rate, BB, DistHigh), classify the archetype
2. **Price-Action:** Greens-10d, Trend-5d, price_action verdict
3. **News/Catalysts:** NSI, concrete headlines with date, retail flag
4. **Macro:** VIX, F&G, Fed - only if relevant within <7d for the trade

Bull target: $XX.XX (+XX%) | Confidence: XX% | Horizon: 1-5d

## Round 1: BEAR (4-6 sentences, must rebut Bull)

Same structure, against Bull. Weaknesses in the Step-1 data, not gut feel.

Bear target: $XX.XX (-XX%) | Confidence: XX% | Horizon: 1-5d

## Round 2: Rebuttals (3-4 sentences)

Bull rebuts Bear arguments 1-3 + one new. Bear rebuts Bull 1-3 + one new.

## Round 3: Final synthesis (4-6 sentences)

**Bull final:** strongest non-rebutted argument, adjusted target, Bull final confidence XX%
**Bear final:** strongest non-rebutted argument, adjusted target, Bear final confidence XX%

---

## Reversion-Edge - what it means

The `reversion_guard.py` script checks four per-stock triggers (RSI vs. own P80, green-streak length vs. own P80, daily-move vs. own P90, gap vs. own P90) against this stock's **own** forward-5d return distribution. A reversion-edge fires only when:

- Today's metric exceeds the stock's own percentile threshold (extreme for THIS stock, not textbook)
- AND the historical fwd-5d distribution at that level shows mean-reversion
  (LONG: green-rate <45% means "pullback expected"; SHORT: green-rate <45% means "blowoff fades")
- AND sample size is SOLID (n >= 8)

Verdicts:

- **LONG "Pullback-Pflicht"**: wait for limit entry below close (continuation OK but not at this price)
- **LONG "Kein Reversion-Edge"**: continuation dominates, entry at close acceptable
- **SHORT "valid"**: blowoff-fade historically works for this stock
- **SHORT "NO-TRADE"**: no blowoff in this stock's history - continuation dominates, no SHORT

## Pull Reversion-Edge forward

Run once before filling the scorecard (Step 3 will fetch it again, but the scorecard needs it here):

```bash
python3 reversion_guard.py {{SYMBOL}} --direction LONG
python3 reversion_guard.py {{SYMBOL}} --direction SHORT
```

Mapping verdict -> Reversion-Edge rating (symmetric, max LONG = 8 in strongest case):

| Script verdict | LONG Rating | SHORT Rating |
|----------------|-------------|--------------|
| LONG "Kein Reversion-Edge" AND SHORT "NO-TRADE" | **8** | 2 |
| LONG "Kein Reversion-Edge" AND SHORT "valid" | 4 | 7 |
| LONG "Pullback-Pflicht" AND SHORT "NO-TRADE" | **5** | 2 |
| LONG "Pullback-Pflicht" AND SHORT "valid" | 2 | 7 |

Interpretation: "Kein Reversion-Edge" LONG means continuation bias intact -> when SHORT is also a NO-TRADE, that's the strongest pro-LONG signal the script can give (LONG = 8). "Pullback-Pflicht" means entry deferred, but direction intact - not automatically penalized to 3, deserves 5. "Valid" SHORT means blowoff-fade is historically proven -> SHORT = 7.

---

## 6-Axis Scorecard (MANDATORY)

Four axes (1-4) come VERBATIM from the Step 1 rating block. Two axes (5-6) come from the debate + reversion_guard.

| Criterion (0-10) | LONG | SHORT | Source |
|------------------|------|-------|--------|
| 1. Technical Green-Rate | /10 | /10 | Step 1 Rating 1 (unchanged) |
| 2. Price-Action Reality | /10 | /10 | Step 1 Rating 2 (unchanged, loosened cap) |
| 3. News + Reddit Flow | /10 | /10 | Step 1 Rating 3 (unchanged) |
| 4. Event/Catalyst | /10 | /10 | Step 1 Rating 4 (unchanged) |
| 5. Chart Structure | /10 | /10 | Debate - pattern, S/R, volume setup |
| 6. Reversion-Edge | /10 | /10 | reversion_guard.py verdict (mapping above) |
| **TOTAL** | **/60** | **/60** | |

**Decision rule:**
- LONG-Total ≥ SHORT+10 -> LONG setup in Step 3
- SHORT-Total ≥ LONG+10 -> SHORT setup in Step 3
- Difference < 10 -> develop both setups, Step 3 Judge decides
- Both totals < 30 -> consider NO-TRADE

---

## Output Card (no JSON)

```
Step 2:
╔════════════════════════════════════════════════════╗
║ SCORECARD - {{SYMBOL}}                             ║
╠════════════════════════════════════════════════════╣
║                              LONG   │   SHORT      ║
║ 1. Technical Green-Rate      X/10   │   X/10       ║
║ 2. Price-Action Reality      X/10   │   X/10       ║
║ 3. News + Reddit Flow        X/10   │   X/10       ║
║ 4. Event/Catalyst            X/10   │   X/10       ║
║ 5. Chart Structure           X/10   │   X/10       ║
║ 6. Reversion-Edge            X/10   │   X/10       ║
║ ─────────────────────────────────── │ ──────       ║
║ TOTAL                       XX/60   │  XX/60       ║
╠════════════════════════════════════════════════════╣
║ Bull target: $XX.XX (+XX%) Confidence XX%          ║
║ Bear target: $XX.XX (-XX%) Confidence XX%          ║
║ Strongest Bull:  <1 sentence>                      ║
║ Strongest Bear:  <1 sentence>                      ║
║ Recommended:     LONG | SHORT | BOTH | NO-TRADE    ║
╚════════════════════════════════════════════════════╝

[STEP 2 COMPLETE]
```
