# STEP 2: INVESTMENT DEBATE

**Asset:** {{SYMBOL}}
**Input:** Raw data from Step 1 (`runs/.../step1_data.md`).

Goal: Two-sided reasoning that surfaces real arguments and counter-arguments. No new data fetching — work strictly with Step 1 output. The debate produces a structured judgment block for Step 3.

---

## Per-Stock-Conditioning Rule (mandatory)

For every claim about RSI, volume, volatility, momentum, or any indicator: do NOT use textbook thresholds ("RSI 70 = overbought", "Volume 2x avg = breakout"). Instead, use the 250 daily bars and intraday history from Step 1 to assess how unusual the current value is **for THIS stock**.

**Required form:** "RSI is 76. Looking at the last 12 months of daily bars, this stock spent 14 days above RSI 70, and on 9 of those 14 days the next day closed green. No clear mean-reversion signal at this level for this stock."

**Forbidden form:** "RSI 76 is overbought."

If the historical sample is small (<10 occurrences), say so explicitly: "Only 4 occurrences above this RSI level in 12 months — sample too thin to draw a conclusion."

The same logic applies to gap behavior, volume spikes, ATR ranges, distance-from-SMA, and any other indicator the LLM cites.

---

## Round 1: Bull Case (4-6 sentences)

Build the strongest case for LONG. Cover:

1. **Technical setup**: chart structure, momentum, key levels — referenced to specific bars/dates from Step 1
2. **Per-stock conditioning**: at least one explicit conditional ("at this RSI level, this stock has historically...")
3. **News/sentiment**: which headlines or Reddit signals support the bull thesis (with date)
4. **Macro context**: only if directly relevant (Fed/CPI within 7d, sector rotation visible in market-wide data)

End with: **Bull target: $XX.XX (+XX%)** | **Bull conviction: XX%** | **Horizon: 1-3d primary**

## Round 1: Bear Case (4-6 sentences)

Build the strongest case for SHORT. Must directly counter Bull where possible. Same structure:

1. Technical weakness or short setup
2. Per-stock conditioning (e.g., "at this distance from 52w-high, this stock has historically faded")
3. News/sentiment counter-narrative
4. Macro risks

End with: **Bear target: $XX.XX (-XX%)** | **Bear conviction: XX%** | **Horizon: 1-3d primary**

## Round 2: Rebuttals (2-3 sentences each)

**Bull rebuts Bear**: address the strongest 1-2 Bear points directly. Where Bull cannot rebut, acknowledge it.

**Bear rebuts Bull**: same — address strongest Bull points, acknowledge what cannot be rebutted.

The honest acknowledgment of un-rebutted points is more valuable than forced counter-arguments. If a Bear point stands, mark it as standing.

## Round 3: Synthesis (3-5 sentences)

After both sides have presented and rebutted: what is the honest read?

- Which arguments survived rebuttal?
- Where is asymmetry — does one side have substantially stronger, more concrete arguments?
- Are both sides weak (suggesting NO-TRADE)?
- Are both sides strong (suggesting high uncertainty, smaller position or wait)?

This is the LLM's actual reasoning. Don't hedge — commit to a read.

### Evidence Hierarchy when Both Sides have Standing Points

When both Bull and Bear retain un-rebutted points after Round 2, classify each standing point by evidence type:

- **Tier 1** — Live-observable behavior (today's price action, today's volume, today's news flow vs. today's price reaction): strongest weight
- **Tier 2** — Setup-matched historical analogs with n ≥ 5: medium weight
- **Tier 3** — Setup-matched historical analogs with n < 5: weak, MUST be flagged as anecdotal in the Output Block
- **Tier 4** — Textbook patterns without per-stock conditioning: forbidden (already covered by Per-Stock-Conditioning Rule)

Asymmetry derivation:

- Tier-1 point on one side + only Tier-3 points on the other side → Asymmetry follows the Tier-1 side, regardless of which conviction % is higher
- Both sides hold only Tier-3 points and no Tier-1 points → Asymmetry = `both-weak`, regardless of conviction %
- Both sides hold Tier-1 points (genuine live-evidence conflict) → Asymmetry = `balanced`

Rationale: an n=3 historical sample is anecdotal regardless of direction. "Positive news + falling price" is verifiable today and binds reality to one direction. Conviction % alone is not a tie-breaker.

---

## Output Block

```
Step 2: Investment Debate — {{SYMBOL}}

Bull conviction: XX%
Bull reason: <one sentence — strongest standing argument>

Bear conviction: XX%
Bear reason: <one sentence — strongest standing argument>

Strongest non-rebutted Bull point: <one sentence>
Strongest non-rebutted Bear point: <one sentence>

Asymmetry: clear-LONG | clear-SHORT | balanced | both-weak

Notes for Step 3:
  <2-3 sentences on what Step 3 should pay particular attention to —
   per-stock conditioning concerns, macro timing risks, key levels to watch>

[STEP 2 COMPLETE]
```

Step 3 derives the trade direction from the Asymmetry tag and the conviction values — Step 2 does not commit to LONG/SHORT/NO-TRADE itself.

---

## Persistence

Write the full debate (Rounds 1-3 + Output Block) to:
```
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step2_debate.md
```

Overwrite if file exists. Re-runs of the same analysis use a new run_id (new folder).

The user reviews this file as part of the trade decision — the reasoning is for the user too, not just for Step 3.

## What Step 2 does NOT do

- Does not compute KO, stop, target levels — that is Step 3
- Does not commit to LONG/SHORT/NO-TRADE — Step 3 decides
- Does not fetch new data — Step 1 output is the input
- Does not generate a numeric scorecard — conviction percentages are direct LLM estimates with one-sentence reasons
- Does not cite scripts that don't exist (no indicator_context, no reversion_guard, no convergence_check — these were aggregations and have been removed in v1.0)

## Conviction calibration (guidance, not rule)

When assigning conviction percentages:

- **0-30%**: weak case, mostly speculation, multiple major counter-arguments standing
- **30-50%**: plausible case, but significant counter-arguments unrebutted
- **50-70%**: solid case, most counter-arguments answered, some risks remain
- **70-90%**: strong case, counter-arguments rebutted with concrete evidence
- **>90%**: rare — should require multiple independent confirmations and clear per-stock conditioning

If both Bull and Bear conviction are above 60%, that is itself a signal: high uncertainty, the stock is genuinely contested. Mark Asymmetry as `balanced` and let Step 3 size accordingly.

If both are below 40%, mark Asymmetry as `both-weak` — Step 3 will likely decide NO-TRADE.
