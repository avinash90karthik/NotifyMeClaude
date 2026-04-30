# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

Pre-flight (Step 0) must be complete, with the verbatim checklist above § 1.1. If not → STOP.

---

## 1.1 Portfolio

```bash
python3 scripts/ops/prediction_db.py portfolio
pytr portfolio
```

`pytr` = truth for fills/cash/shares. `prediction_db` = truth for analysis coverage.
On conflict: pytr for size, DB for history. Note: slots used, cash, sector exposure.

## 1.2 Technical Data

```bash
python3 scripts/analysis/collect_data.py {{SYMBOL}}
```

Review: price, RSI, MACD, ATR, ADX, regime, SMA50/200, S/R, earnings distance. Flag anomalies.
**V3:** prices and FX from APIs only — no hardcoded fallbacks (mechanics: `RULES.md § V3`).

## 1.3 Pre-Open Pattern

```bash
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NOT IN DB')"
# If NOT IN DB:
python3 scripts/analysis/preopen_backtest.py --symbols {{SYMBOL}}
# Then in either case:
python3 scripts/analysis/preopen_check.py {{SYMBOL}} --entry-timing
```

Note: verdict, hit-rate, gap-fill %, best entry time.

## 1.4 Chart + Indicator Context

### Chart

```bash
source .env 2>/dev/null
SCRIPT="${CHART_SCRIPT:-}"
if [ -n "$SCRIPT" ]; then ${YFINANCE_VENV:-python3} $SCRIPT {{SYMBOL}}; fi
```

Note: trend, SMA constellation (golden/death cross), RSI + divergence, volume, pattern, support, resistance.

### Price-Action Reality (W2)

```bash
python3 scripts/analysis/price_action_check.py {{SYMBOL}}
```

Output: 5/10/20-day trend + greens-in-10d + verdict. Mechanics: `RULES.md § W2`.

### Indicator Context (W3 + W5)

```bash
python3 scripts/analysis/indicator_context.py {{SYMBOL}} --expected-price <Close from 1.2> --expected-date <last trading day>
```

Per-stock conditional green-rates over 3y for RSI / BB-position / Dist-3M-high.
Aborts (exit 2) if history is >2 days stale or close diverges >0.5%. Mechanics: `RULES.md § W3`.
If the script flags an extreme-oversold band → apply W5 LONG bonus (`RULES.md § W5`).
**The W5 bonus must be noted explicitly — even when 0%.** Otherwise it gets systematically dropped in Step 3.

| Axis | Now | Sample (n, tag) | Fwd-5d | Green | Adjust | Strongest? |
|------|-----|-----------------|--------|-------|--------|------------|
| RSI | | | | | | |
| BB position | | | | | | |
| Dist 3M-high | | | | | | |
| Combo (if active) | | | | | | |

State explicitly: **archetype = TREND or Range** (justifies whether range penalties apply).
The strongest single axis is the input for Rating 1.

## 1.5 News & Sentiment

**Three sources, all mandatory:**

1. **yfinance** — items from pre-flight, last 7d.
2. **Web search** — ≥5 items from Reuters / Bloomberg / Seeking Alpha / sector sources.
3. **Trump Truth Social / tweets** — for every ticker, queries are in the pre-flight banner. On hit → "no overnight" applies in Step 3.

**Reddit** (one query, one read):

```
site:reddit.com {{SYMBOL}}
```

Sentiment tag: EUPHORIC | BULLISH | NEUTRAL | BEARISH | PANIC | QUIET.
Contra-flags: EUPHORIC@ATH (bearish) or PANIC@oversold (bullish).

### Quality Check (SW1, MANDATORY)

Majority sentiment is not a signal — the quality of the minority arguments is. Discipline against confirmation bias:

1. **Top 3 counter-arguments** to the setup bias (on LONG → bear cases; on SHORT → bull cases) — even if Reddit is clearly one-sided.
2. **Rating: HARD** (filings, insider trades, hard data) **or SOFT** (opinion, narrative, price targets).
3. **HARD minority → contra signal**, regardless of the majority. SOFT minority → note, no override.

This rating is cited as `minority arg=HARD/SOFT` in Rating 3.

**News table:**

| # | Date | Headline | Source | Score (-2..+2) |
|---|------|----------|--------|----------------|

**NSI = mean of the scores.** > +1.0 strongly bullish · -0.3..+0.3 neutral · < -1.0 strongly bearish.

## 1.6 Macro + Geopolitical Triggers

**Macro (web):** VIX, CNN F&G, Fed/rates + days until next decision, DXY, latest CPI, 10Y, Polymarket odds for upcoming events.

**Geopolitical scan:** only ACTIVE triggers with deadline / expiry / material headline in the next 7d.
Categories: armed conflicts + ceasefire expiries, tariff/sanctions deadlines, central-bank decisions, energy chokepoints, election dates.
If nothing material: `Geopolitical scan: no active triggers in next 7d`.
Any trigger with deadline <5 trading days → also add a row in §1.9.

Format per active trigger: `<name>: <status> | next deadline <date> | 24h reaction if relevant`

## 1.7 Correlation

From `pytr portfolio`: open positions with sectors. Flag if:
- Sector concentration >60% after this trade
- All-LONG bias (correlation risk)

## 1.8 Pattern Analytics

Three scripts with different conditionings — none subsumes the others.

### Recent Day Pattern (streak conditional)

```bash
python3 scripts/analysis/day_pattern.py {{SYMBOL}}
```

| Pattern | Next Day | After 3d | After 5d |
|---------|----------|----------|----------|
| After similar day (n=X) | +X.X% (X% green) | +X.X% (X% green) | +X.X% (X% green) |
| After X red days streak (n=X) | +X.X% (X% green) | | |

The streak conditional is a sequence signal (last N days' direction), structurally different from Mode-1 return-bands in Pattern Timeline. Subsumption status tracked in `memory/TRACKING.md`.

Key insight: what does the pattern say about the likely direction?

### Pattern Timeline

```bash
python3 scripts/analysis/pattern_timeline.py {{SYMBOL}}
```

Mode 1: similar-day fwd-return (5 return-bands, n typically >100).
Mode 2: analogous 7-day windows (corr ≥0.7, RSI ±7, ATR-regime 0.7–1.4). Skip if <10 analogs.
Per day +1..+3: mean / ±1σ / green-rate + AGREEMENT/DIVERGE.

Reading: AGREEMENT all 3 days → robust. DIVERGE ≥3 days → cap Step-3 confidence at 60–63%.
Mode 2 SKIP → use Mode 1 only as a hint. ±1σ band = realistic entry-limit corridor.

### Convergence (cross-source)

```bash
python3 scripts/analysis/convergence_check.py {{SYMBOL}}
```

Compares three independent fwd-5d green-rate estimators: indicator_context strongest-axis (=Rating-1 input), Mode 1, Mode 2.

Verdict: TIGHT (<10 pp) | MODERATE (10–20 pp) | HIGH SPREAD (≥20 pp).
**HIGH SPREAD is information about regime conditionality, not a NO-TRADE trigger.**
Mode 2 SKIP/THIN → script falls back to a 2-source diagnosis.
Output is descriptive — no auto-cap. Quote the Reading line verbatim in Step 2/3.

### Earnings Window (W7)

```bash
python3 scripts/analysis/earnings_pattern.py {{SYMBOL}}
# If earnings ≤15 days AND a directional setup is being considered:
python3 scripts/analysis/earnings_pattern.py {{SYMBOL}} --trade-entry <T-N> --trade-exit <T-M> --same-month
```

**Earnings proximity is never a skip reason** — adjust hold time (typically exit 1–3 days before earnings), not the trade itself. Mechanics: `RULES.md § W7`. The sigmoid adjust from the script print applies directly.
Same-month sample with ≥3 quarters = validation; <3 = directional hint only.

## 1.9 Events

| Date | Event | Impact | Relevance |
|------|-------|--------|-----------|

For each HIGH/VERY-HIGH event decide:

- Resolves uncertainty (catalyst) or creates new uncertainty (risk-off)?
- Do the data support a direction?
   ```bash
   python3 scripts/analysis/event_impact.py {{SYMBOL}}
   ```
   Lists >3% moves of the last 6 months + next-day reaction + post-drop bounce rate.

Decision matrix:
- Clarity + data → trade BEFORE event
- Clarity + ambivalent direction → trade with stop management
- New uncertainty → WAIT
- Both outcomes bullish → opportunity, not risk

If earnings <5 trading days → flag for KO adjustment in Step 3.

---

## Output: Ratings for Step 2

Step 2 takes these unchanged. No re-rating in the debate.

**Green-rate → rating mapping (symmetric):**

| Fwd-5d green | LONG | SHORT |
|--------------|------|-------|
| >70% | 9 | 1 |
| 60–70% | 7 | 3 |
| 50–60% | 5 | 5 |
| 40–50% | 3 | 7 |
| <40% | 1 | 9 |

THIN sample (n<15) → cap 5/5. WEAK → max ±2 from neutral (3–7).

### Rating 1 — Technical Green-Rate (§ 1.4 strongest axis + archetype)

```
LONG X/10 | SHORT X/10
Source: <axis name, n=X, green=X%, adjust=±X.X%, w5_bonus=±X.X%, archetype=TREND|Range>
```

`w5_bonus` is a required field — when W5 is not active, write `w5_bonus=0%` explicitly, do not omit.

### Rating 2 — Price-Action Reality (§ 1.4 price_action_check)

```
LONG X/10 | SHORT X/10
Source: <Greens-10d, Trend-5d, Trend-20d, Verdict>
LONG cap (max 4) applies only if: Greens<5/10 AND Trend-5d ≤0% AND Trend-20d ≤+5%
SHORT cap (max 3) applies only if: Greens>7/10 AND Trend-5d ≥0% AND Trend-20d ≥-5%
Otherwise: rate by verdict, no cap.
```

### Rating 3 — News + Reddit Flow (§ 1.5)

```
LONG X/10 | SHORT X/10
Source: <NSI=±X.X, Retail=FLAG, Trump-Hit=Y/N, minority arg=HARD/SOFT>
Adjust: Trump-Hit → both -2. EUPHORIC@ATH → LONG -2. PANIC@oversold → SHORT -2.
HARD minority → contra side +1, setup side -1.
```

### Rating 4 — Event/Catalyst (§ 1.8 Earnings + § 1.9 Events)

```
LONG X/10 | SHORT X/10
Source: <main event/earnings phase, clarity, decision>
WAIT → 3/3. Trade-BEFORE bullish → LONG 7–9 / SHORT 1–3. Earnings WARNING → affected side -2.
```

---

## Step 1 One-Line Summary

```
1.1 Portfolio:           <slots / cash EUR / sector clash Y/N>
1.2 Technical:           <regime + 1 key indicator>
1.3 Pre-Open:            <verdict>
1.4 Chart + IndCtx:      <archetype + strongest axis + adjust + w5_bonus>
1.5 News + Reddit:       <NSI + retail flag + Trump Y/N + minority arg HARD/SOFT>
1.6 Macro + Geo:         <VIX + F&G + Fed days + most relevant active trigger or "all QUIET">
1.7 Correlation:         <clash Y/N>
1.8 Day Pattern:         <similar-day Fwd5 + streak insight>
1.8 Pattern Timeline:    <Mode1/Mode2 fwd5 + AGREEMENT Y/N>
1.8 Convergence:         <spread pp + verdict TIGHT|MODERATE|HIGH>
1.8 Convergence Reading: <verbatim Reading line from script>
1.8 Earnings:            <skip / phase / trade-window adjust>
1.9 Events:              <main event + decision>
```

```
[STEP 1 COMPLETE]
```
