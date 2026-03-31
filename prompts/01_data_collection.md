# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

---

## 1.1 Portfolio Check

```bash
python prediction_db.py portfolio
```

Review open positions, cash, and slots before continuing.

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
- **VIX** (CBOE Volatility Index) — current level + trend (< 15 calm, 15-25 normal, 25-35 elevated, > 35 fear)
- **CNN Fear & Greed Index** — current reading + zone (Extreme Fear / Fear / Neutral / Greed / Extreme Greed)
- Fed/rates status + next meeting
- DXY trend
- Recent CPI
- Treasury 10Y yield
- Geopolitical factors relevant to {{SYMBOL}}
- Polymarket odds for upcoming events (if applicable)

## 1.7 Correlation Check

From `prediction_db.py portfolio`: list open positions with sectors. Check:
- Same sector as {{SYMBOL}}? If >60% concentration after this trade: WARNING
- Same direction (all LONG)? Diversification risk
- Correlated with Nasdaq/S&P?

## 1.8 Recent Day Pattern Analysis (LLM Pattern Recognition)

```python
python3 -c "
import yfinance as yf
sym = '{{SYMBOL}}'
t = yf.Ticker(sym)
h = t.history(period='2y')
h['ret'] = h['Close'].pct_change() * 100
h['next_1d'] = h['ret'].shift(-1)
h['next_3d'] = h['Close'].pct_change(3).shift(-3) * 100
h['next_5d'] = h['Close'].pct_change(5).shift(-5) * 100

# Last 5 trading days
print('=== LAST 5 TRADING DAYS ===')
for i in range(-5, 0):
    d = h.iloc[i]
    print(f'  {d.name.strftime(\"%d.%m\")} Close: {d[\"Close\"]:.2f} Change: {d[\"ret\"]:+.2f}%')

# Count recent streak
streak = 0
for i in range(len(h)-1, -1, -1):
    if h['ret'].iloc[i] < 0: streak += 1
    else: break
print(f'\nCurrent red streak: {streak} days')

# What happens after similar patterns?
last_ret = h['ret'].iloc[-1]
threshold = -3 if last_ret < -3 else (-1 if last_ret < -1 else 1 if last_ret > 1 else 0)

if threshold < 0:
    similar = h[h['ret'] <= threshold].dropna(subset=['next_1d','next_3d','next_5d'])
    label = f'<= {threshold}%'
elif threshold > 0:
    similar = h[h['ret'] >= threshold].dropna(subset=['next_1d','next_3d','next_5d'])
    label = f'>= +{threshold}%'
else:
    similar = h[(h['ret'] > -1) & (h['ret'] < 1)].dropna(subset=['next_1d','next_3d','next_5d'])
    label = 'flat (-1% to +1%)'

print(f'\n=== AFTER DAYS WITH {label} (n={len(similar)}) ===')
print(f'Next day:  avg {similar[\"next_1d\"].mean():+.2f}% | green {(similar[\"next_1d\"]>0).mean()*100:.0f}%')
print(f'After 3d:  avg {similar[\"next_3d\"].mean():+.2f}% | green {(similar[\"next_3d\"]>0).mean()*100:.0f}%')
print(f'After 5d:  avg {similar[\"next_5d\"].mean():+.2f}% | green {(similar[\"next_5d\"]>0).mean()*100:.0f}%')

# Consecutive red days pattern
if streak >= 2:
    h['red'] = h['ret'] < 0
    h['red_streak'] = h['red'].groupby((~h['red']).cumsum()).cumsum()
    multi = h[h['red_streak'] >= streak].dropna(subset=['next_1d'])
    print(f'\n=== AFTER {streak}+ RED DAYS IN A ROW (n={len(multi)}) ===')
    print(f'Next day:  avg {multi[\"next_1d\"].mean():+.2f}% | green {(multi[\"next_1d\"]>0).mean()*100:.0f}%')
"
```

Fill this table from the output:

| Pattern | Next Day | After 3d | After 5d |
|---------|----------|----------|----------|
| After similar day (n=X) | +X.X% (X% green) | +X.X% (X% green) | +X.X% (X% green) |
| After X red days streak (n=X) | +X.X% (X% green) | | |

**Key insight:** [What does the pattern data tell us about likely direction?]

## 1.9 Event Calendar

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
  "day_pattern": {
    "red_streak": 0,
    "after_similar_day_n": 0,
    "next_1d_avg_pct": 0,
    "next_1d_green_pct": 0,
    "next_3d_avg_pct": 0,
    "next_3d_green_pct": 0,
    "next_5d_avg_pct": 0,
    "next_5d_green_pct": 0,
    "pattern_insight": ""
  },
  "events": []
}
```

```
[STEP 1 COMPLETE]
```
