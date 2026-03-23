# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}

---

**Input:** Data from Step 1 + Debate from Step 2 (incl. Final Confidence from Round 3) + Chart
Reference the JSON blocks from Steps 1 and 2 for structured data points.

Consult `memory/reflections.md` for historical performance data (win rate, patterns, risk/reward).

**ATTENTION:** Check the date in reflections.md. If older than 7 days → run `python reflect.py`!

---

## INVESTMENT JUDGE

**The Judge MUST use the chart as an independent source!**

### JUDGE CHART ANALYSIS

**Analyze the chart INDEPENDENTLY from Bull/Bear:**

| Aspect | Your Observation | Weighting |
|--------|-----------------|-----------|
| Trend Direction | [What do you see?] | High/Medium/Low |
| SMA Configuration | [Golden/Death Cross?] | High/Medium/Low |
| RSI Signal | [Overbought/Oversold/Neutral?] | High/Medium/Low |
| **RSI Delta/Divergence** | [Is RSI turning? Divergence detected?] | **High** |
| Volume Confirmation | [Does volume confirm the trend?] | High/Medium/Low |
| Money Flow (CMF) | [Accumulation/Distribution?] | High/Medium/Low |
| Chart Pattern | [Recognizable patterns?] | High/Medium/Low |

**RSI Divergence Verdict:**
> If bullish divergence at RSI <35: Strong argument for an impending trend reversal.
> If RSI oversold BUT delta negative and no divergence: Waterfall risk, NOT a buy signal!
> Divergence data from Step 1 must be EXPLICITLY referenced here!

**Chart Verdict:** The chart favors [BULL/BEAR/NEUTRAL] because [1-2 sentences]

### VERDICT

Analyze the Bull vs Bear arguments from Step 2:

**Argument Assessment:**

| Side | Strength | Best Arguments |
|------|----------|----------------|
| 🐂 Bull | X/10 | [Top 2 arguments] |
| 🐂 Bull Final Confidence | XX% | [From Round 3] |
| 🐻 Bear | X/10 | [Top 2 arguments] |
| 🐻 Bear Final Confidence | XX% | [From Round 3] |
| 📊 Chart | X/10 | [What does the chart say?] |
| 📈 RSI Divergence | [Bullish/Bearish/None] | [Signal strength] |
| 📰 News Sentiment (NSI) | [X.XX] | [Strongly bullish / Slightly bullish / Neutral / Bearish] |
| 🔄 Regime | [TRENDING/RANGE/CHOPPY/TRANSITIONAL] | [Signal aligned with regime?] |
| 🩳 Short Interest | X% Float / X Days | [Squeeze potential or bearish signal?] |
| 🎯 Pre-Open Pattern | [Verdict + Hit%] | [Confirms/contradicts signal? Gap fill timing?] |

**Decisive Factors:**
1. [Most important factor]
2. [Second most important factor]
3. [Third most important factor]

### PRE-OPEN PATTERN ADJUSTMENT

```
╔═══════════════════════════════════════════════════════════════╗
║  PRE-OPEN PATTERN → ENTRY TIMING & CONFIDENCE                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Pattern Hit Rate ≥60% AND same direction as signal:          ║
║  → Confidence +3% (pattern confirms signal)                  ║
║                                                               ║
║  Pattern Hit Rate <50% BUT signal says LONG/SHORT:            ║
║  → Confidence -5% (pattern warns: historically poor!)         ║
║                                                               ║
║  Gap Fill Rate ≥80%:                                          ║
║  → Entry recommendation: AFTER US open (gap will be filled)  ║
║  → Document entry timing in Trading Card!                     ║
║                                                               ║
║  BB Squeeze <10%:                                             ║
║  → Breakout imminent, direction uncertain                    ║
║  → Reduce position one tier OR wait for trigger               ║
║                                                               ║
║  Pre-Open Verdict: [LONG/SHORT/WAIT/NO TRADE]                ║
║  Pattern Hit Rate: XX% [Direction]                            ║
║  Gap Fill: XX%                                                ║
║  → Adjustment: [+X% / -X% / 0%]                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### REGIME ADJUSTMENT

```
╔═══════════════════════════════════════════════════════════════╗
║  CONFIDENCE ADJUSTMENT based on Regime                       ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  TRENDING + Signal WITH Trend:     Confidence +5%            ║
║  TRENDING + Signal AGAINST Trend:  Confidence -10%           ║
║  RANGE + Signal at S/R Level:      Confidence +3%            ║
║  RANGE + Signal in mid-range:      Confidence -5%            ║
║  CHOPPY:                           Confidence -5% to -10%    ║
║  TRANSITIONAL:                     No adjustment             ║
║                                                               ║
║  Regime: [TRENDING/RANGE/CHOPPY/TRANSITIONAL]                ║
║  Signal Direction vs Trend: [WITH/AGAINST/NEUTRAL]            ║
║  → Adjustment: [+X% / -X% / 0%]                             ║
║  → Confidence before adjustment: XX%                         ║
║  → Confidence after adjustment: XX%                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### REFLECTION-BASED ADJUSTMENT

Read `memory/reflections.md` and adjust:

| Reflection Finding | Adjustment |
|---|---|
| Win rate confidence bracket < 30% | Confidence -5% for this bracket |
| Win rate LONG < 40% AND signal=LONG | Warning: "LONG historically weak" |
| Win rate SHORT < 40% AND signal=SHORT | Warning: "SHORT historically weak" |
| Pattern DISCIPLINE_VIOLATION > 2x | Additional enforcement check |
| Avg duration winners < 3 days | Tighten time-stop to 3/5 days |

**Applied Adjustments:** [List all applied adjustments here or "None"]

### DECISION

```
╔═══════════════════════════════════════════════════════╗
║  SIGNAL & CONFIDENCE BY TIME HORIZON                  ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Short-term (1-5 days):   [LONG/SHORT/HOLD]  [XX]%  ║
║  Medium-term (2-8 weeks): [LONG/SHORT/HOLD]  [XX]%  ║
║  Long-term (3+ months):   [LONG/SHORT/HOLD]  [XX]%  ║
║                                                       ║
║  → TRADE SIGNAL (short-term): [LONG/SHORT/HOLD]      ║
║  → TRADE CONFIDENCE: [XX]%                           ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

The **TRADE SIGNAL** is always the short-term verdict — this is what determines entry/exit for turbo trades. Medium and long-term provide context only.

**Reasoning:** [2-3 sentences why this decision - incl. chart confirmation and RSI divergence!]

### Confidence Score Reference:
| Value | Meaning |
|-------|---------|
| 0.85-1.00 | Extremely strong - all signals aligned |
| 0.70-0.84 | Strong - clear direction |
| 0.55-0.69 | Moderate - some opposing factors |
| 0.40-0.54 | Weak - rather HOLD |
| < 0.40 | Unclear - HOLD or IGNORE |

---

## KO LEVEL ANALYSIS

Based on the signal: **[LONG/SHORT]**

```
╔═══════════════════════════════════════════════════════════════╗
║  KO CALCULATION: ATR + CHART SUPPORT COMBINED                 ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  STEP A: Determine ATR multiplier by asset class             ║
║  STEP B: Identify chart support/resistance                   ║
║  STEP C: KO = whichever is FURTHER from price                ║
║                                                               ║
║  ❌ NEVER place KO between price and support!                ║
║  ❌ NEVER use only ATR OR only chart - ALWAYS both!          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### STEP A: ATR Multiplier by Asset Class

ATR (14) from Step 1: **$XX.XX (X.X%)**

| Asset Class | Examples | ATR Multiplier | Why |
|-------------|----------|----------------|-----|
| Large Cap Stocks | NVDA, AAPL, MSFT | 2.0x ATR | Stable order books, low gap risk |
| Mid/Small Cap Stocks | ARM, IREN, VST | 2.5x ATR | Thinner liquidity, stronger earnings moves |
| Commodities (Gold, Silver) | GC=F, SI=F | 3.0x ATR | Macro shocks (Fed, tariffs, geopolitics), overnight gap risk |
| Crypto-related | MSTR, COIN | 3.0x ATR | Extreme volatility, 24/7 underlying |
| Leveraged Indices | QQQ, SPY Turbos | 2.0x ATR | Broadly diversified, less single-stock risk |

**Determine the asset class of {{SYMBOL}}:** [Class]
**ATR Multiplier:** [X.Xx]
**ATR-based KO Level (LONG):** Price - (ATR x Multiplier) = $XX.XX - ($XX.XX x X.X) = **$XX.XX**
**ATR-based KO Level (SHORT):** Price + (ATR x Multiplier) = $XX.XX + ($XX.XX x X.X) = **$XX.XX**

### STEP B: Chart Support as Minimum Distance

Identify the relevant chart levels from Step 1:

| Level | Price | Strength (1-5) | Reasoning |
|-------|-------|-----------------|-----------|
| Nearest Support (S1) | $XX.XX | X/5 | [Why is this a support?] |
| Strong Support (S2) | $XX.XX | X/5 | [Why?] |
| Critical Support (S3) | $XX.XX | X/5 | [Why?] |

**Chart-based KO Level:** Below the strongest relevant support + buffer (0.5-1%)
→ Support at $XX.XX → KO at **$XX.XX** (Support - X%)

### STEP C: FINAL KO LEVEL

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  RULE: KO = whichever level is FURTHER from price            ║
║                                                               ║
║  ATR-based:    $XX.XX (XX.X% from price)                     ║
║  Chart-based:  $XX.XX (XX.X% from price)                     ║
║                                                               ║
║  → FINAL KO:  $XX.XX (XX.X% from price)                     ║
║  → Leverage:  ~Xx                                            ║
║  → Method:    [ATR / Chart / Both equal]                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Reasoning:** [2-3 sentences why this KO level. Which chart level provides protection? Why is the ATR distance (in)sufficient?]

### EARNINGS / EVENT WARNING

```
⚠️ EARNINGS/EVENT CHECK:
- Next earnings date: [Date or "none within 2 weeks"]
- Other events (Fed, CPI, etc.): [Date]
- IF event < 5 trading days away:
  → Increase ATR multiplier by +0.5 (earnings gaps!)
  → OR partially close position before event
```

---

## RISK-PER-TRADE CHECK

```
╔═══════════════════════════════════════════════════════════════╗
║  PORTFOLIO PROTECTION                                        ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Portfolio value (from portfolio.md): XXX EUR                ║
║  Max. loss per trade (10%):           XXX EUR                ║
║  Max. simultaneously at risk (40%):   XXX EUR                ║
║  Currently at risk (open positions):  XXX EUR                ║
║  Remaining risk budget:               XXX EUR                ║
║                                                               ║
║  ⚠️ If risk budget exhausted → NO new trade!                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## TRADE PLAN

**Based on the analysis - concrete action recommendation:**

### Entry
| Action | Price | Reasoning |
|--------|-------|-----------|
| **Buy** | $XX.XX | [Why enter here?] |
| **KO Level** | $XX.XX | [ATR + Chart combined] |

### Exits (staggered)
| Action | Price | Portion | Reasoning |
|--------|-------|---------|-----------|
| **Sell** | $XX.XX | XX% | [Which resistance level?] |
| **Sell** | $XX.XX | XX% | [Next target?] |
| **Sell** | $XX.XX | Rest | [Stretch target?] |

### Stops
| Action | Price | Portion | Reasoning |
|--------|-------|---------|-----------|
| **Stop** | $XX.XX | XX% | [Mental stop ABOVE KO!] |
| **Stop** | $XX.XX | Rest | [Absolute limit?] |

### Time Stops
| Condition | Action |
|-----------|--------|
| After 3 trading days <5% in profit | Halve position |
| After 5 trading days sideways | Close position |
| Earnings < 2 days away | Secure at least 50% |

### Trade Duration Expectation (MANDATORY!)

```
╔═══════════════════════════════════════════════════════════════╗
║  EXPECTED TRADE DURATION                                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Historically: Winners run 2-3 days (median)                 ║
║  → If a trade is not +5% in profit after 3 days,            ║
║    the thesis is probably WRONG.                              ║
║                                                               ║
║  TRADE DURATION ESTIMATE:                                     ║
║  Fill in here:                                                ║
║  • Setup type: [from table below]                            ║
║  • Expected duration: [X days]                               ║
║  • Reasoning: [Catalyst timing, event distance, etc.]        ║
║  • If > 5 days expected: WARNING — not suited for turbos     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Setup Type → Expected Duration:**

| Setup Type | Expected Duration | Example |
|------------|-------------------|---------|
| **Momentum Breakout** | 1-3 days | Breakout above resistance with volume |
| **Pullback Entry** | 2-4 days | Pullback to SMA50 in uptrend |
| **Mean Reversion** | 1-2 days | RSI <30 bounce, short-term snap-back |
| **Event/Earnings** | 1-2 days | Catalyst-driven (CPI, FOMC, earnings) |
| **Hedge (Index SHORT)** | 3-7 days | Protection during macro risk |
| **Trend Following** | 5-10 days | Longer trend, preferably WITHOUT leverage |

> **If setup type is "Trend Following" → WARNING: Turbo leverage unsuitable for >5 days. Consider buying the stock directly or without leverage!**

### Watch Zones
| Zone | Price Range | What to do? |
|------|-------------|-------------|
| [Zone 1] | $XX - $XX | [Watch / Add / Sell?] |
| [Zone 2] | $XX - $XX | [Watch / Add / Sell?] |

---

## RISK AUDIT (VETO CHECK)

```
╔═══════════════════════════════════════════════════════════════╗
║  INDEPENDENT RISK AUDIT — CAN BLOCK THE TRADE!               ║
╠═══════════════════════════════════════════════════════════════╣
║  Any single VETO rule can prevent the trade.                  ║
║  Check EVERY rule explicitly with ✅ or ❌!                   ║
╚═══════════════════════════════════════════════════════════════╝
```

| # | Rule | Check | Status |
|---|------|-------|--------|
| V1 | ATR > 7%? | ATR = X.X% | ✅/❌ VETO |
| V2 | Regime CHOPPY + Score < 50? | Regime = [X], Score = [X] | ✅/❌ VETO |
| V3 | >= 3 open positions? | Currently: X/3 | ✅/❌ VETO |
| V4 | Sector > 60% after new trade? | [Sector]: X% | ✅/❌ VETO |
| V5 | Monthly drawdown > 20%? | March P&L: X% | ✅/❌ VETO |
| W1 | Earnings < 5 trading days? | [Date or "No"] | ✅/⚠️ |
| W2 | Correlation with open position? | [Yes/No — which one?] | ✅/⚠️ |
| W3 | KO distance < 2x ATR? (Commodities < 3x) | KO distance = X.Xx ATR | ✅/⚠️ |
| W4 | Signal against SMA200 direction? | SMA200 trend = [UP/DOWN] | ✅/⚠️ |

**Risk Audit Result:**

```
╔═══════════════════════════════════════╗
║  ✅ TRADE APPROVED                    ║  (if all VETOs passed)
║  ⛔ TRADE BLOCKED — [Reason]         ║  (if at least 1 VETO)
╚═══════════════════════════════════════╝
```

---

## ENFORCEMENT

- ✅ Judge analyzes chart INDEPENDENTLY from Bull/Bear
- ✅ **RSI divergence explicitly considered in Judge verdict**
- ✅ Signal box with LONG/SHORT/HOLD + Confidence%
- ✅ KO level calculated with BOTH methods (ATR + Chart)
- ✅ ATR multiplier differentiated by asset class
- ✅ KO is ALWAYS below the strongest support (LONG) / above resistance (SHORT)
- ✅ Earnings/event warning checked
- ✅ Risk-per-trade check against portfolio limit
- ✅ Staggered sell plan with concrete prices and percentages
- ✅ Time stops defined
- ✅ Stop levels based on support zones
- ✅ **Risk Audit: All 5 VETO rules + 4 WARNINGs explicitly checked (MANDATORY!)**
- ✅ **Regime adjustment applied (confidence before/after documented)**
- ✅ **Pre-Open Pattern adjustment applied (hit rate + gap fill + BB squeeze)**
- ✅ **Reflection-based adjustment checked**

---

## OUTPUT JSON

**IMPORTANT: The JSON block is IN ADDITION to the prose. It replaces NOTHING.**

Generate this structured output at the end of Step 3:

```json
{
  "step": 3,
  "symbol": "{{SYMBOL}}",
  "signal": "LONG|SHORT|HOLD",
  "confidence_pct": 0,
  "confidence_by_horizon": {
    "short_term_1_5d": 0,
    "medium_term_2_8w": 0,
    "long_term_3m_plus": 0
  },
  "regime": "TRENDING|RANGE|CHOPPY|TRANSITIONAL",
  "regime_adjustment_pct": 0,
  "ko_level_usd": 0.00,
  "ko_method": "ATR|CHART",
  "entry_usd": 0.00,
  "exits": [
    {"price_usd": 0.00, "pct": 50},
    {"price_usd": 0.00, "pct": 30},
    {"price_usd": 0.00, "pct": 20}
  ],
  "stops": [
    {"price_usd": 0.00, "pct": 100}
  ],
  "risk_per_trade_pct": 0.0,
  "vetoes": [],
  "warnings": []
}
```

Fill ALL fields with the actual values from the analysis!

```
✅ [STEP 3: JUDGE & RISK COMPLETED]
```
