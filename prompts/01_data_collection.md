# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

---

## 1.1 Portfolio Check

Read `memory/portfolio.md`. If any trades happened since last update, update it NOW before continuing.

## 1.2 Technical Data (automated)

```bash
python collect_data.py {{SYMBOL}}
```

This collects: price, RSI (with delta/divergence/slope), MACD, ATR (with event check), ADX, regime, SMA50/200, short interest, support/resistance, earnings date, market status.

**Review the output.** Flag anything unusual (ATR elevated, divergence detected, regime change).

## 1.3 Pre-Open Pattern Check

```bash
# Check if symbol is in pattern DB
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NOT IN DB')"

# If NOT in DB: python3 preopen_backtest.py --symbols {{SYMBOL}}

# Run pre-open check with entry timing
python3 preopen_check.py {{SYMBOL}} --entry-timing
```

Document: verdict, hit rates, gap fill %, best entry timing.

## 1.4 Chart Analysis

```bash
source .env 2>/dev/null
SCRIPT="${CHART_SCRIPT:-}"
if [ -n "$SCRIPT" ]; then ${YFINANCE_VENV:-python3} $SCRIPT {{SYMBOL}}; fi
```

Analyze the chart and fill this table:

| Aspect | Observation |
|--------|-------------|
| Trend | Uptrend / Downtrend / Sideways |
| SMA 50/200 | Golden Cross / Death Cross / Neutral |
| RSI + Divergence | [From collect_data.py output] |
| Volume | Confirming or diverging from price |
| Pattern | Double Top/Bottom, H&S, Triangle, etc. |
| Key Support | From chart + collect_data.py |
| Key Resistance | From chart + collect_data.py |

## 1.5 News & Catalysts

**Web search for 5+ real news items.** Sources: Reuters, Bloomberg, Seeking Alpha, sector-specific.

For each news item:

| # | Date | Headline | Impact | Source |
|---|------|----------|--------|--------|
| 1 | DD.MM | [headline] | Positive/Negative/Neutral | [source] |

**News Sentiment Index (NSI):** Rate each on 7 axes (-2 to +2): Relevance, Sentiment, Price Impact, Trend, Earnings, Investor Confidence, Risk Profile. Calculate average.

NSI > +1.0 = strongly bullish | -0.3 to +0.3 = neutral | < -1.0 = strongly bearish

## 1.6 Macro Context

Via web search:
- Fed/rates status + next meeting
- DXY trend
- Recent CPI
- Treasury 10Y yield
- Geopolitical factors relevant to {{SYMBOL}}
- Polymarket odds for upcoming events (if applicable)

## 1.7 Correlation Check

From `memory/portfolio.md`: list open positions with sectors. Check:
- Same sector as {{SYMBOL}}? If >60% concentration after this trade: WARNING
- Same direction (all LONG)? Diversification risk
- Correlated with Nasdaq/S&P?

## 1.8 Event Calendar

| Date | Event | Impact | Relevance |
|------|-------|--------|-----------|
| [dates] | [events] | [impact level] | [direct/macro/sector] |

If earnings < 5 trading days: flag for KO adjustment in Step 3.

---

## Output

Produce the structured JSON block (collect_data.py output + your additions):

```json
{
  "step": 1,
  "symbol": "{{SYMBOL}}",
  "collect_data": { /* paste collect_data.py JSON output */ },
  "chart_analysis": { "trend": "", "pattern": "", "key_observation": "" },
  "nsi": 0.00,
  "nsi_classification": "",
  "preopen_verdict": "",
  "preopen_long_hit_pct": 0,
  "preopen_short_hit_pct": 0,
  "entry_timing": { "best": "", "pre_market_win": 0, "open_win": 0, "fh_dip_win": 0 },
  "correlation_ok": true,
  "sector_concentration_pct": 0,
  "events": []
}
```

```
[STEP 1 COMPLETE]
```
