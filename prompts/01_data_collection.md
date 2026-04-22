# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

Pre-flight runs before Step 1 (`python3 preflight_check.py {{SYMBOL}}`, see Step 0). The verbatim checklist with your answers MUST appear before § 1.1. If the pre-flight did not run, STOP and tell the user.

---

## 1.1 Portfolio Check

```bash
python3 prediction_db.py portfolio
```

Inspect open positions, cash, slot count before continuing.

## 1.2 Technical Data

```bash
python3 collect_data.py {{SYMBOL}}
```

Collects: price, RSI (delta/divergence/slope), MACD, ATR, ADX, regime, SMA50/200, short interest, S/R, earnings, market status.

Review output. Flag anomalies (elevated ATR, divergence, regime shift).

> **Hard Rule (7): EUR/USD is always live from yfinance.** Never hardcode an exchange rate (e.g. "1.10" as fallback). `collect_data.py` already pulls live FX. If yfinance fails for FX, the analysis aborts - no hardcoded substitute.

## 1.3 Pre-Open Pattern Check

```bash
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NOT IN DB')"
# If NOT IN DB:
python3 preopen_backtest.py --symbols {{SYMBOL}}
# Then:
python3 preopen_check.py {{SYMBOL}} --entry-timing
```

Document: verdict, hit rates, gap-fill %, best entry timing.

## 1.4 Chart Analysis

```bash
source .env 2>/dev/null
SCRIPT="${CHART_SCRIPT:-}"
if [ -n "$SCRIPT" ]; then ${YFINANCE_VENV:-python3} $SCRIPT {{SYMBOL}}; fi
```

Fill the chart table: trend, SMA 50/200 (golden/death cross), RSI + divergence, volume, pattern, support, resistance.

### Price-Action Reality Check (Rule 14, MANDATORY)

```bash
python3 price_action_check.py {{SYMBOL}}
```

The script returns 5/10/20-day trend + green-day count + verdict. Rules:

- Greens-in-10d < 5 -> not a confirmed turn. MACD/RSI turn signals are weighted DOWN by -5% to -10% confidence.
- 5-day trend ≤ 0 despite positive MACD = stabilization, not bounce. PREP phase, no LONG trigger.
- Note relative weakness vs S&P on the latest day (index up, symbol down) as a warning.

### Indicator Context Check (Rule 16, MANDATORY)

```bash
python3 indicator_context.py {{SYMBOL}} --expected-price <Close from 1.2> --expected-date <last trading day>
```

The script:
- Computes RSI / BB-position / Dist-3M-high over 3 years of THIS stock's history
- Reports per band sample size [SOLID n>=30 / WEAK 15-29 / THIN <15] and Fwd-5d Green-Rate
- Computes a sigmoid Confidence-Adjust per axis (continuous, no bucket cliffs)
- Aggregates with the **strongest single axis** (max absolute adjust) - does NOT sum across axes
- Classifies as TREND-STOCK or Range/Normal-stock
- Aborts with exit code 2 if history is >2 trading days stale or close diverges >0.5% (stale-data guard)

**Sigmoid Adjust formula** (already computed by the script):
```
adjust = 5.0 * tanh((green_rate - 0.5) * 4) * sample_weight
sample_weight: SOLID (n>=30) = 1.0  /  WEAK (15-29) = 0.5  /  THIN (<15) = 0.0
```

Reference values (SOLID, max +/-5%):

| Green-Rate | Adjust |
|------------|--------|
| 50% | 0.00% |
| 55% | +0.99% |
| 60% | +1.90% |
| 65% | +2.69% |
| 70% | +3.32% |
| 75% | +3.81% |
| 80% | +4.17% |
| 85%+ | +4.43% to +4.61% |

Negative green-rates mirror symmetrically (35% -> -2.69%, 25% -> -3.81%, etc.). WEAK halves; THIN is 0.

**Aggregation rule:** Take the **strongest single axis** as Rating 1 input. Reasoning: RSI / BB / DistHigh are positively correlated for trend stocks (a stock near 3M-high tends to have BB high and RSI elevated). Naive summing would double-count. The script already prints `STRONGEST AXIS: <name>  adjust=±X.X%` - use that single number.

### v9 Extreme-Oversold Bonus (Rule 19, MANDATORY)

When the current RSI band from the script output meets the conditions below, **explicitly add** the oversold bonus to LONG confidence. It overrides regime penalties.

| Current RSI band | Fwd-5d green-rate | Sample | LONG bonus |
|------------------|-------------------|--------|------------|
| < 20 | ≥ 65% | n ≥ 20 [SOLID] | **+5%** |
| < 15 | ≥ 70% | n ≥ 20 [SOLID] | **+8%** (capitulation low) |

Example reading: `indicator_context.py` shows "RSI 16 | Fwd5 +4.2% green=75% [SOLID n=34]" -> **+5% LONG bonus** mandatory in the summary table below and cited in the Judge step.

**Rationale:** Backtest 2026-04-16, 5/5 predictions with confidence <50% during extreme-oversold went +8.82% in signal direction. The system blocked them due to TRENDING penalties, but the stock-specific Fwd green-rate dominates historically.

**Forbidden:** No "overbought reflexes" without script output. Sentences like "RSI 72 is overbought -> -5%" or "BB >100% -> fade likely -> -5%" without first citing the green-rate are bias, not analysis.

**Output table for your analysis:**

| Indicator | Now | Sample | Fwd-5d Avg | Green-Rate | Adjust | Used as Rating 1? |
|-----------|-----|--------|-----------|------------|--------|-------------------|
| RSI | X | n=X [tag] | +X.X% | X% | ±X.XX% | yes/no |
| BB position | X% | n=X [tag] | +X.X% | X% | ±X.XX% | yes/no |
| Dist 3M-high | ±X% | n=X [tag] | +X.X% / break X% | X% | ±X.XX% | yes/no |
| Combo (if active) | ... | n=X [tag] | ... | ... | ±X.XX% | yes/no |
| **Strongest** | | | | | **±X.XX%** | **yes** |

Note the archetype (TREND/Range) explicitly - this is the justification for whether range penalties apply.

## 1.5 News & Catalysts

Three sources are mandatory:

1. **yfinance news** - already in pre-flight output. Move items from the last 7 days into the news table.
2. **Web search** - at least 5 real news items from Reuters, Bloomberg, Seeking Alpha, sector-specific. Complements yfinance, does not replace it.
3. **Trump Truth Social / tweet search** - for EVERY ticker, not just "sensitive" sectors. Query strings are in the pre-flight banner. If a Trump post is found -> strategy rule "no overnight positions" activates.

### Reddit Retail Sentiment (MANDATORY)

```
site:reddit.com/r/wallstreetbets {{SYMBOL}}
site:reddit.com/r/wallstreetbetsGer {{SYMBOL}}
site:reddit.com/r/stocks {{SYMBOL}}
site:reddit.com/r/investing {{SYMBOL}}
```

For .DE/.F also `r/mauerstrassenwetten`. Penny/small-cap also `r/pennystocks`. Crypto-related also `r/CryptoCurrency`.

Capture: sentiment tone (euphoria/panic/capitulation/fade/silent accumulation), YOLO flow, fresh DD threads (last 7d), trending indicators.

Red flags:
- Euphoria at ATH -> contra-indicator (bearish)
- Put-YOLOs at oversold -> contra-indicator (bullish)
- Suddenly viral on an unknown ticker -> pump risk
- Silence on fundamental news -> institutional dominance

### Quality Check (Rule 15, read the arguments)

Democracy != analysis. 70% bullish on a -30% stock is always there (dip-buying psychology). What matters is the quality of the minority arguments. Document for every analysis:

1. Top 3 bear arguments (on a LONG setup) - even if Reddit is 80% bullish
2. Top 3 bull arguments (on a SHORT setup) - even if Reddit is bearish
3. Rating: HARD (facts, filings, insider data) or SOFT (opinion, narrative, targets)?
4. If the minority has harder arguments -> contra signal, regardless of count

News table:

| # | Date | Headline / Thread | Impact | Source |
|---|------|-------------------|--------|--------|

**News Sentiment Index (NSI):** Per item 7 axes (-2 to +2): Relevance, Sentiment, Price Impact, Trend, Earnings, Investor Confidence, Risk Profile. Take the average.

NSI > +1.0 = strongly bullish | -0.3 to +0.3 = neutral | < -1.0 = strongly bearish.

**Retail sentiment flag** (separate): EUPHORIC / BULLISH / NEUTRAL / BEARISH / PANIC / QUIET. With EUPHORIC+ATH or PANIC+oversold -> note as contra signal.

## 1.6 Macro Context

Via web search: VIX (< 15 calm, 15-25 normal, 25-35 elevated, > 35 fear), CNN Fear & Greed, Fed/rates + next meeting, DXY, latest CPI, 10Y yield, relevant geopolitics, Polymarket odds for upcoming events (if applicable).

### Active Geopolitical Triggers (MANDATORY)

For each of the following, search and document the **current status + next deadline**. Do not skip on the assumption that "nothing's happening" - the user got burned on a missed Iran-ceasefire-expiry on 2026-04-21.

1. **Iran conflict / Strait of Hormuz status**
   - Search: `Iran ceasefire status [today's date]`
   - Search: `Strait Hormuz oil shipping [today's date]`
   - Document: Is a ceasefire active YES/NO? Next expiry date. Oil price reaction in last 24h.

2. **Trump tariff / executive-order deadlines**
   - Search: `Trump tariff deadline [next 14 days]`
   - Search: `Trump executive order [today's date]`
   - Document: Any deadlines in the next 7 days? Sectors affected? Posts from the last 24h on truth social?

3. **Fed / ECB next decision window**
   - Already partially covered above, but explicitly state: days-until-next-decision. If < 5 days -> add as event row in 1.9.

4. **Russia / Ukraine major events** (only if last 7 days had a material headline)
   - Search: `Russia Ukraine war stock market [today's date]`

Output format - **one line per trigger** (write "QUIET" if no relevant news in 7 days):

```
Iran/Hormuz:    <status + next deadline + 24h oil reaction>
Trump tariffs:  <deadlines in next 7d + sectors + truth-social posts 24h>
Fed/ECB:        <days until next decision + most recent guidance>
Russia/Ukraine: <QUIET | <headline + impact>>
```

## 1.7 Correlation Check

From `prediction_db.py portfolio`: list open positions with sectors. Check:
- Same sector as {{SYMBOL}}? > 60% concentration after this trade = WARNING
- Same direction (all LONG)? Diversification risk
- Correlation with Nasdaq/S&P?

## 1.8 Recent Day Pattern

```bash
python3 day_pattern.py {{SYMBOL}}
```

Table:

| Pattern | Next Day | After 3d | After 5d |
|---------|----------|----------|----------|
| After similar day (n=X) | +X.X% (X% green) | +X.X% (X% green) | +X.X% (X% green) |
| After X red days streak (n=X) | +X.X% (X% green) | | |

Key Insight: [What does the pattern say about the likely direction?]

## 1.8a Pattern Timeline (MANDATORY)

```bash
python3 pattern_timeline.py {{SYMBOL}}
```

Two modes in one output:
- **Mode 1 (similar-day):** fwd-return distribution for Day +1 to +5 based on days with a similar today-return (classified into 5 return bands, n usually >100).
- **Mode 2 (analog match):** searches historical 7-day windows that match (correlation ≥0.7, RSI ±7, ATR regime 0.7-1.4). Skips if <10 analogs.

Per day: mean, ±1σ range, green-rate. Both modes in parallel + AGREEMENT/DIVERGE check per day.

**Interpretation:**
- **Both modes AGREE on all 5 days** -> forecast robust, can be used as confidence input.
- **DIVERGE on ≥3 days** -> forecast uncertain. Cap signal confidence in Step 3 at 60-63% even if scorecard is higher.
- **Mode 2 SKIP** (analogs <10) -> no edge provable through pattern matching. Use only Mode 1 as a hint, not a driver.
- **±1σ range** is the realistic entry-limit corridor. If Day+1 mean +0.5% but lower bound -2%, a limit at Close-1.5% (P25 zone) is reasonable.

**Output for Step 1 bullet summary:**
```
Pattern Timeline: <Mode1-Fwd5 +X.X% green X% / Mode2-Fwd5 +Y.Y% green Y% [n=Z]>
                  AGREEMENT|DIVERGE (days X/5)
                  Entry corridor tomorrow: ±1σ [ -X.X% .. +X.X% ] from close
```

## 1.8b Earnings Window Pattern (MANDATORY)

> **Hard Rule (21): Earnings proximity is NEVER a skip reason.** Forbidden phrases: "earnings in X days, too close", "window closed", "hold time too limited". Mandatory: run earnings_pattern.py and use the **per-stock pre-earnings green-rate as a confidence adjustment** (sigmoid output, ~±5%), not as a gate. If pre-earnings is historically bullish (green-rate >=55%, avg>0) -> LONG edge, do NOT skip. If bearish (<=45%) -> consider SHORT or LONG with reduced size. Adjust hold time (exit 1 day before earnings), but never reject the trade. See `memory/strategy_v9.md § Why Rule 21` for the HIMS/HOOD/RKLB post-mortem.

```bash
python3 earnings_pattern.py {{SYMBOL}}
# If earnings ≤ 15 days AND a LONG/SHORT setup is being considered, ALSO:
python3 earnings_pattern.py {{SYMBOL}} --trade-entry <T-N> --trade-exit <T-M> --same-month
#   T-N = today's distance in trading days to earnings (entry day)
#   T-M = exit distance = typically 1-3 (one to three days before earnings)
#   --same-month highlights historical quarters in the same calendar month
```

Script logic (two modes):
- **Backward mode** (without --trade-entry): T-X→T0 returns, answers "how far away was the price X days before earnings?". Useful for rough phase categorization, **but does NOT measure the trade window.**
- **Trade-window mode** (with --trade-entry/--trade-exit): interval return T-N→T-M, answers "if I enter today and exit the day before earnings - what happened historically?". This is the **primary metric for our 1-5d trade horizon.**

Other:
- Earnings > 30 days: skip with note (standard day pattern from § 1.8 is sufficient)
- No earnings (commodity/index): cleanly skipped

If full analysis ran, fill the table (Backward-mode T-5d/T-3d/T-1d/T+1d/T+3d/T+5d Avg/Green/n) AND separately Trade-Window return per quarter + summary.

After the run, mandatorily document:
1. Current phase in the earnings window
2. Edge direction from script output (pre-earnings drift / post-earnings / NO clear pattern)
3. **Trade-Window adjust (primary source):** the script's printed sigmoid adjust applies - NOT the backward-mode WARNING penalty.
4. Same-month hint: if the script finds ≥3 quarters in the target month, treat as validation; if THIN (<3), only as a directional hint.

The script's sigmoid uses earnings-specific thresholds (SOLID n≥8, WEAK 4-7, THIN <4) because earnings sample size is structurally small (max ~10 quarters). Adjust value is read directly from the script output - do not re-derive from buckets.

Backward-mode WARNING is **secondary signal only** (context, no auto-penalty) when Trade-Window stats are available.

**Why this v9 design:** The original rule used T-5d→T0 backward returns and pulled -5% across the board on weak "phase". But that measures **drift toward earnings day**, not the **return over the held trade interval**. For HOOD (T-8): backward stats showed 30% green T-5d→T0, actual held interval T-8→T-3 showed 80% green + Ø +1.57%. The two metrics can give opposite signals - the trade-window metric is the correct one for our 1-5d horizon.

Earnings pattern overrides the standard day pattern when earnings are near.

## 1.9 Event Calendar & Impact

Via web search: all events in the next 1-7 days.

| Date | Event | Impact | Relevance |
|------|-------|--------|-----------|

If earnings < 5 trading days -> flag for KO adjustment in Step 3.

### Event Impact Assessment (per HIGH/VERY HIGH event)

**1. Clarity or uncertainty?**
Does the event RESOLVE uncertainty (catalyst) or CREATE new uncertainty (risk-off)?

| Event | Outcome A | Outcome B | Clarity? |
|-------|-----------|-----------|----------|

**2. What does the data say?**

```bash
python3 event_impact.py {{SYMBOL}}
```

Lists big moves (>3%) of the last 6 months with next-day reaction and bounce rate after drops.

**3. Trade decision:**
- Clarity + data supports direction -> trade BEFORE event (use the catalyst)
- Clarity, direction unclear -> trade with stop management (overnight rule)
- New uncertainty -> WAIT until after event
- Both outcomes bullish -> event is opportunity, not risk

---

## Output for Step 1

Close Step 1 with the bullet summary AND the rating block (no JSON).

### Bullets

```
Step 1:
- Price/Regime: <Close, ATR%, RSI, MACD state, ADX, regime from 1.2>
- Chart: <trend, SMA constellation, pattern, support, resistance>
- Price-Action Reality: <Greens-10d + verdict from price_action_check>
- Indicator Context: <archetype + STRONGEST axis adjust value (single number)>
- Pre-Open: <verdict + best entry time>
- News: <NSI + 2-3 most important items + Trump flag>
- Reddit: <sentiment flag + minority argument quality>
- Macro: <VIX, F&G, Fed, relevant macro events>
- Geopolitical Triggers: <Iran/Hormuz status, Trump tariffs, Fed/ECB days, Russia/Ukraine>
- Correlation: <sector concentration, portfolio clash flag>
- Day Pattern: <similar-day Fwd5 green-rate + key insight>
- Pattern Timeline: <Mode1/Mode2 Fwd5 + AGREEMENT/DIVERGE + entry corridor>
- Earnings Window: <skip / phase / WARNING / edge + trade-window adjust if applicable>
- Events: <main event, clarity/uncertainty, trade decision>
```

### Ratings for Step 2 (MANDATORY - data-driven, no gut feel)

Four 0-10 ratings, each with a source citation from Step 1. Step 2 MUST take them unchanged (no re-rating in the debate).

Mapping rule green-rate -> rating (symmetric):

| Fwd-5d Green-Rate / Flag | LONG Rating | SHORT Rating |
|--------------------------|-------------|--------------|
| > 70% | 9 | 1 |
| 60-70% | 7 | 3 |
| 50-60% | 5 | 5 |
| 40-50% | 3 | 7 |
| < 40% | 1 | 9 |

Sample THIN (n<15) -> rating capped at 5/5 (no provable edge). Sample WEAK -> max ±2 from neutral (3-7 range).

**Rating 1 - Technical Green-Rate** (from § 1.4 Indicator Context **strongest single axis** + archetype):
```
Technical Green-Rate:  LONG X/10  |  SHORT X/10
  Source: <strongest axis name, n=X, green=X%, adjust=±X.X%, archetype=TREND|Range>
```

**Rating 2 - Price-Action Reality** (from price_action_check.py verdict + greens-10d, with loosened cap):
```
Price-Action Reality:  LONG X/10  |  SHORT X/10
  Source: <Greens-10d=X/10, Trend-5d=±X%, Trend-20d=±X%, Verdict="...">
  Cap rule (loosened):
    LONG-cap (max 4) ACTIVE only iff: Greens<5/10 AND Trend-5d ≤ 0% AND Trend-20d ≤ +5%
      -> stabilization, not pullback-recovery
    SHORT-cap (max 3) ACTIVE only iff: Greens>7/10 AND Trend-5d ≥ 0% AND Trend-20d ≥ -5%
    Otherwise no cap - rate by intrinsic verdict and greens score.
```

**Rating 3 - News + Reddit Flow** (from § 1.5 NSI + retail flag + Trump + minority argument quality):
```
News + Reddit Flow:  LONG X/10  |  SHORT X/10
  Source: <NSI=±X.X, Retail=FLAG, Trump-Hit=YES/NO, minority argument quality: hard/soft>
  Rule: Trump-Hit -> both ratings -2 (unpredictability). EUPHORIC@ATH -> LONG -2. PANIC@oversold -> SHORT -2.
```

**Rating 4 - Event/Catalyst** (from § 1.8b Earnings + § 1.9 Events, <7 day horizon):
```
Event/Catalyst:  LONG X/10  |  SHORT X/10
  Source: <main event/earnings phase, clarity/uncertainty, trade decision from 1.9>
  Rule: WAIT -> both 3/3. Trade-BEFORE-event bullish -> LONG 7-9, SHORT 1-3. Earnings WARNING -> affected direction -2.
```

### Step 1 One-Line Summary (MANDATORY before [STEP 1 COMPLETE])

Exactly one line (max 2 sentences) per subsection. This is the compact recap the user reads before Step 2:

```
1.1 Portfolio:           <slots used / cash EUR / sector clash YES/NO>
1.2 Technical:           <regime + 1 key indicator>
1.3 Pre-Open:            <verdict>
1.4 Chart + IndCtx:      <archetype + strongest axis name + adjust value>
1.5 News + Reddit:       <NSI + retail flag + Trump-hit YES/NO>
1.6 Macro:               <VIX + F&G + Fed days>
1.6 Geopol Triggers:     <most relevant active trigger or "all QUIET">
1.7 Correlation:         <clash YES/NO>
1.8 Day Pattern:         <Fwd5 green-rate>
1.8a Pattern Timeline:   <Mode1 fwd5 + AGREEMENT YES/NO>
1.8b Earnings Window:    <skip / phase / trade-window adjust if applied>
1.9 Events:              <main event + decision>
```

```
[STEP 1 COMPLETE]
```

Do not cite examples, do not repeat rules - only results from this analysis.
