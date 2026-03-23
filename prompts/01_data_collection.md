# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

---

## STOP! ENFORCEMENT CHECKLIST

```
╔═══════════════════════════════════════════════════════════════╗
║  BEFORE YOU START:                                            ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ✅ YFINANCE FIRST: Python script for live data (MANDATORY!) ║
║  ✅ GENERATE CHART: Visually analyze the chart!              ║
║  ✅ REAL News: With date, source, and link                    ║
║  ✅ Web search: ONLY for news and current events              ║
║  ✅ CORRELATION: Check existing positions!                    ║
║                                                               ║
║  ❌ Do NOT use web search for price data (outdated!)          ║
║  ❌ NO fabricated data or estimates without source            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 0.0 UPDATE PORTFOLIO.MD (BEFORE STARTING ANALYSIS!)

**Read `memory/portfolio.md` and check if it is up to date.**

If the user has made a trade since the last update (new position, partial sale, stop triggered), enter it NOW BEFORE the analysis begins.

- New position? → Add to "Open Positions" (Symbol, Sector, Value, Buy-In, KO, Stop)
- Position closed? → Move to "Closed Trades" + P&L
- Stop triggered? → Mark as closed + enter loss
- Set "Last Updated" date

**After every trade, portfolio.md is also checked again in Step 4.**

---

## 1.0 LIVE DATA VIA YFINANCE (MANDATORY!)

**ALWAYS execute this Python script first:**

```python
import yfinance as yf
import pandas as pd

def calculate_rsi(close, periods=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/periods, min_periods=periods).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/periods, min_periods=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(close):
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

# Wavelet denoising (graceful fallback)
try:
    from wavelet_utils import wavelet_denoise
    HAS_WAVELET = True
except ImportError:
    HAS_WAVELET = False

from datetime import datetime

# Futures proxy map: Use ETF instead of futures for RSI/MACD (no rollover issue)
FUTURES_ETF_PROXY = {
    'SI=F': 'SLV',   # Silver → iShares Silver ETF
    'GC=F': 'GLD',   # Gold → SPDR Gold ETF
    'CL=F': 'USO',   # Oil → United States Oil ETF
    'NG=F': 'UNG',   # Natural Gas → United States Natural Gas ETF
}

# Fetch price data for {{SYMBOL}}
ticker = yf.Ticker("{{SYMBOL}}")
hist = ticker.history(period='3mo')
info = ticker.info

# For technicals: ETF proxy if futures, otherwise direct
proxy_symbol = FUTURES_ETF_PROXY.get("{{SYMBOL}}")
if proxy_symbol:
    proxy_hist = yf.Ticker(proxy_symbol).history(period='3mo')
    close_for_ta = wavelet_denoise(proxy_hist['Close']) if HAS_WAVELET else proxy_hist['Close']
    rsi = calculate_rsi(close_for_ta)
    macd, signal, histogram = calculate_macd(close_for_ta)
    technicals_source = f'{proxy_symbol} (ETF proxy, rollover-free, wavelet-denoised)'
else:
    close_for_ta = wavelet_denoise(hist['Close']) if HAS_WAVELET else hist['Close']
    rsi = calculate_rsi(close_for_ta)
    macd, signal, histogram = calculate_macd(close_for_ta)
    technicals_source = '{{SYMBOL}} (wavelet-denoised)' if HAS_WAVELET else '{{SYMBOL}}'

# EXACT TIMESTAMP
now = datetime.utcnow()
last_trade = datetime.fromtimestamp(info.get('regularMarketTime', 0))
market_state = info.get('marketState', 'UNKNOWN')

print('=' * 60)
print('{{SYMBOL}} - LIVE DATA')
print('=' * 60)
print(f'Analysis Time:     {now.strftime("%Y-%m-%d %H:%M:%S")} UTC')
print(f'Last Trade:        {last_trade.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Market State:      {market_state}')
print(f'Technicals Source: {technicals_source}')
print('=' * 60)
print()
print('PRICE & PERFORMANCE')
print(f'  Current Price:      ${info.get("currentPrice", 0):.2f}')
print(f'  Day High:           ${info.get("dayHigh", 0):.2f}')
print(f'  Day Low:            ${info.get("dayLow", 0):.2f}')
print(f'  Previous Close:     ${info.get("previousClose", 0):.2f}')
print(f'  52W High:           ${info.get("fiftyTwoWeekHigh", 0):.2f}')
print(f'  52W Low:            ${info.get("fiftyTwoWeekLow", 0):.2f}')
print()
print('MOVING AVERAGES')
print(f'  50-Day SMA:         ${info.get("fiftyDayAverage", 0):.2f}')
print(f'  200-Day SMA:        ${info.get("twoHundredDayAverage", 0):.2f}')
price = info.get('currentPrice', 0)
sma50 = info.get('fiftyDayAverage', 1)
sma200 = info.get('twoHundredDayAverage', 1)
print(f'  Price vs 50 SMA:    {((price/sma50)-1)*100:.1f}%')
print(f'  Price vs 200 SMA:   {((price/sma200)-1)*100:.1f}%')
print(f'  Golden Cross:       {"YES" if sma50 > sma200 else "NO"}')
print()
print('TECHNICAL INDICATORS')
current_rsi = rsi.iloc[-1]
current_macd = macd.iloc[-1]
current_signal = signal.iloc[-1]
current_hist = histogram.iloc[-1]
rsi_status = "OVERBOUGHT" if current_rsi > 70 else "OVERSOLD" if current_rsi < 30 else "Neutral"
print(f'  RSI (14):           {current_rsi:.1f} ({rsi_status})')
print(f'  MACD:               {current_macd:.2f}')
print(f'  MACD Signal:        {current_signal:.2f}')
print(f'  MACD Histogram:     {current_hist:.2f} ({"BULLISH" if current_hist > 0 else "BEARISH"})')
print()

# =============================================
# RSI DELTA, DIVERGENCE & MOMENTUM (NEW!)
# =============================================
print('RSI MOMENTUM & DIVERGENCE')
prev_rsi = rsi.iloc[-2]
rsi_delta_1d = current_rsi - prev_rsi
rsi_delta_3d = current_rsi - rsi.iloc[-4] if len(rsi) > 4 else 0
rsi_delta_5d = current_rsi - rsi.iloc[-6] if len(rsi) > 6 else 0
print(f'  RSI current:        {current_rsi:.1f}')
print(f'  RSI yesterday:      {prev_rsi:.1f}')
print(f'  RSI Delta (1d):     {rsi_delta_1d:+.1f}')
print(f'  RSI Delta (3d):     {rsi_delta_3d:+.1f}')
print(f'  RSI Delta (5d):     {rsi_delta_5d:+.1f}')

# RSI Slope (3-day moving average of RSI delta)
rsi_slope = rsi.diff().rolling(3).mean()
print(f'  RSI Slope (3d avg): {rsi_slope.iloc[-1]:+.2f}')
prev_slope = rsi_slope.iloc[-2]
print(f'  RSI Slope prev:     {prev_slope:+.2f}')
if rsi_slope.iloc[-1] > 0 and prev_slope < 0:
    print('  -> RSI MOMENTUM TURNING POSITIVE!')
elif rsi_slope.iloc[-1] > prev_slope:
    print('  -> RSI momentum IMPROVING')
elif rsi_slope.iloc[-1] < 0:
    print('  -> RSI momentum NEGATIVE')

# RSI status at extremes
if current_rsi < 30:
    if rsi_delta_1d > 0:
        print(f'  SIGNAL: RSI OVERSOLD + TURNING UP ({rsi_delta_1d:+.1f}/day)')
    else:
        print(f'  SIGNAL: RSI OVERSOLD + FALLING FURTHER ({rsi_delta_1d:+.1f}/day)')
elif current_rsi > 70:
    if rsi_delta_1d < 0:
        print(f'  SIGNAL: RSI OVERBOUGHT + TURNING DOWN ({rsi_delta_1d:+.1f}/day)')
    else:
        print(f'  SIGNAL: RSI OVERBOUGHT + STILL RISING ({rsi_delta_1d:+.1f}/day)')

# Divergence check: Compare last 2 price lows with RSI lows
print()
print('  DIVERGENCE CHECK (last 30 days):')
recent = hist.tail(30)
rsi_recent = rsi.tail(30)
lows = []
for i in range(1, len(recent)-1):
    if recent['Low'].iloc[i] < recent['Low'].iloc[i-1] and recent['Low'].iloc[i] < recent['Low'].iloc[i+1]:
        lows.append((recent.index[i].strftime('%Y-%m-%d'), recent['Low'].iloc[i], rsi_recent.iloc[i]))

highs = []
for i in range(1, len(recent)-1):
    if recent['High'].iloc[i] > recent['High'].iloc[i-1] and recent['High'].iloc[i] > recent['High'].iloc[i+1]:
        highs.append((recent.index[i].strftime('%Y-%m-%d'), recent['High'].iloc[i], rsi_recent.iloc[i]))

if len(lows) >= 2:
    last_two = lows[-2:]
    price_lower = last_two[1][1] < last_two[0][1]
    rsi_higher = last_two[1][2] > last_two[0][2]
    print(f'  Low 1: {last_two[0][0]} Price=${last_two[0][1]:.2f} RSI={last_two[0][2]:.1f}')
    print(f'  Low 2: {last_two[1][0]} Price=${last_two[1][1]:.2f} RSI={last_two[1][2]:.1f}')
    if price_lower and rsi_higher:
        print('  -> BULLISH DIVERGENCE (Price Lower Low, RSI Higher Low)')
    elif not price_lower and not rsi_higher:
        print('  -> BEARISH DIVERGENCE (Price Higher Low, RSI Lower Low)')
    else:
        print('  -> No divergence at lows')
else:
    print('  Not enough lows for divergence check')

if len(highs) >= 2:
    last_two_h = highs[-2:]
    price_higher = last_two_h[1][1] > last_two_h[0][1]
    rsi_lower = last_two_h[1][2] < last_two_h[0][2]
    print(f'  High 1: {last_two_h[0][0]} Price=${last_two_h[0][1]:.2f} RSI={last_two_h[0][2]:.1f}')
    print(f'  High 2: {last_two_h[1][0]} Price=${last_two_h[1][1]:.2f} RSI={last_two_h[1][2]:.1f}')
    if price_higher and rsi_lower:
        print('  -> BEARISH DIVERGENCE (Price Higher High, RSI Lower High)')
    elif not price_higher and not rsi_lower:
        print('  -> BULLISH DIVERGENCE (Price Lower High, RSI Higher High)')
    else:
        print('  -> No divergence at highs')

print()
print('SHORT INTEREST')
print(f'  Shares Short:       {info.get("sharesShort", 0):,}')
print(f'  Short % of Float:   {info.get("shortPercentOfFloat", 0)*100:.1f}%')
print(f'  Short Ratio (Days): {info.get("shortRatio", 0):.1f}')
print()
print('VALUATION')
print(f'  Market Cap:         ${info.get("marketCap", 0)/1e9:.1f}B')
print(f'  P/S Ratio:          {info.get("priceToSalesTrailing12Months", 0):.0f}x')
print(f'  P/B Ratio:          {info.get("priceToBook", 0):.1f}x')
print()
print('CASH & DEBT')
print(f'  Total Cash:         ${info.get("totalCash", 0)/1e6:.0f}M')
print(f'  Total Debt:         ${info.get("totalDebt", 0)/1e6:.0f}M')
print(f'  Free Cash Flow:     ${info.get("freeCashflow", 0)/1e6:.0f}M')
print()
print('ANALYST TARGETS')
print(f'  Target High:        ${info.get("targetHighPrice", 0):.0f}')
print(f'  Target Mean:        ${info.get("targetMeanPrice", 0):.0f}')
print(f'  Target Low:         ${info.get("targetLowPrice", 0):.0f}')
print(f'  Recommendation:     {info.get("recommendationKey", "N/A").upper()}')
print()
print('VOLATILITY')
atr_data = hist['High'] - hist['Low']
atr14 = atr_data.rolling(14).mean().iloc[-1]
atr_pct = (atr14 / price) * 100
ann_vol = hist['Close'].pct_change().std() * (252**0.5) * 100
beta = info.get('beta', 'N/A')
print(f'  ATR (14):           ${atr14:.2f} ({atr_pct:.1f}%)')
print(f'  Ann. Volatility:    {ann_vol:.0f}%')
print(f'  Beta:               {beta}')
print()
print('RISK SCORES')
print(f'  Overall Risk:       {info.get("overallRisk", "N/A")}/10')
print()

# EARNINGS CALENDAR
print('EARNINGS & EVENTS')
try:
    cal = ticker.calendar
    if cal is not None and len(cal) > 0:
        print(f'  Next Earnings:      {cal}')
    else:
        print('  Next Earnings:      No data available')
except:
    print('  Next Earnings:      No data available')
```

**IMPORTANT:**
- ❌ NEVER use web search for price data - always yfinance!
- ✅ Web search ONLY for news and current events
- ✅ The yfinance data is the TRUTH - use it!

---

## 1.1 GENERATE & ANALYZE CHART (MANDATORY!)

**Execute this command (use paths from `.env`):**

```bash
source .env 2>/dev/null
VENV="${YFINANCE_VENV:-python3}"
SCRIPT="${CHART_SCRIPT:-}"
OUTPUT="${CHART_OUTPUT_DIR:-charts}"
if [ -z "$SCRIPT" ]; then echo "Chart skipped (CHART_SCRIPT not set)"; else $VENV $SCRIPT {{SYMBOL}}; fi
```

**Then read the chart:**

```
Read the file: ${CHART_OUTPUT_DIR}/{{SYMBOL}}_chart.png
```

### CHART CONTENTS (4 Panels)

| Panel | Content | Colors |
|-------|---------|--------|
| 1 | Candlesticks + Moving Averages | SMA 50 = Orange, SMA 200 = Purple |
| 2 | RSI (14) | Yellow, Overbought 70 = Red, Oversold 30 = Green |
| 3 | Volume | Green = Bullish, Red = Bearish |
| 4 | Money Flow | CMF = Cyan, OBV = Magenta |

### INITIAL CHART ANALYSIS (MANDATORY TABLE)

Document what you see in the chart:

| Aspect | Observation |
|--------|-------------|
| **Trend** | Uptrend/Downtrend/Sideways |
| **SMA 50/200** | Golden Cross / Death Cross / Neutral |
| **RSI** | Overbought (>70) / Oversold (<30) / Neutral |
| **Volume** | Rising/Falling with price movement |
| **CMF** | Positive (Accumulation) / Negative (Distribution) |
| **Pattern** | Double Top/Bottom, H&S, Triangle, etc. |
| **Support** | Visible support levels in the chart |
| **Resistance** | Visible resistance levels in the chart |

---

## 1.1b INTRADAY CONTEXT (MANDATORY for stocks)

**ONLY as context, NOT for indicator calculation!**

```python
# Intraday data (1h, last 5 days)
try:
    intraday = yf.download("{{SYMBOL}}", period='5d', interval='1h', progress=False)
    if intraday is not None and len(intraday) > 0:
        # Flatten MultiIndex if needed
        if intraday.columns.nlevels > 1:
            intraday.columns = intraday.columns.get_level_values(0)

        # Volume profile: Top 3 price zones by volume
        price_bins = pd.cut(intraday['Close'], bins=20)
        vol_profile = intraday.groupby(price_bins, observed=True)['Volume'].sum().sort_values(ascending=False)
        print('INTRADAY CONTEXT (5d, 1h)')
        print('  Volume Profile (Top 3 Zones):')
        for i, (zone, vol) in enumerate(vol_profile.head(3).items()):
            print(f'    {i+1}. ${zone.left:.2f}-${zone.right:.2f}: {vol:,.0f}')

        # VWAP Approximation (5d)
        vwap = (intraday['Close'] * intraday['Volume']).sum() / intraday['Volume'].sum()
        print(f'  VWAP (5d):          ${vwap:.2f}')
        print(f'  Price vs VWAP:      {((price/vwap)-1)*100:+.1f}%')

        # Intraday Range (5d)
        intra_high = float(intraday['High'].max())
        intra_low = float(intraday['Low'].min())
        print(f'  5d Intraday Range:  ${intra_low:.2f} - ${intra_high:.2f}')

        # Momentum: last 6h vs previous 6h
        if len(intraday) >= 12:
            recent_6h = intraday['Close'].iloc[-6:]
            prior_6h = intraday['Close'].iloc[-12:-6]
            recent_chg = (float(recent_6h.iloc[-1]) - float(recent_6h.iloc[0])) / float(recent_6h.iloc[0]) * 100
            prior_chg = (float(prior_6h.iloc[-1]) - float(prior_6h.iloc[0])) / float(prior_6h.iloc[0]) * 100
            momentum = 'ACCELERATING' if abs(recent_chg) > abs(prior_chg) and recent_chg * prior_chg > 0 else 'DECELERATING' if abs(recent_chg) < abs(prior_chg) else 'REVERSING'
            print(f'  Momentum (6h):      {momentum} (last {recent_chg:+.2f}% vs prior {prior_chg:+.2f}%)')
    else:
        print('INTRADAY CONTEXT: No data available (Futures/Weekend)')
except Exception as e:
    print(f'INTRADAY CONTEXT: Not available ({e})')
```

> **Note:** Intraday data serves ONLY as additional context for entry timing. All technical indicators (RSI, MACD, ATR etc.) are calculated exclusively on a daily basis. If intraday data is not available (some futures/commodities, weekends) → skip.

### MARKET-MAKER PRICING CHECK (automatic!)

```python
# Market status check: Automatic warning when market is closed
from datetime import datetime, timezone

_now_utc = datetime.now(timezone.utc)
_hour = _now_utc.hour + _now_utc.minute / 60
_weekday = _now_utc.weekday()  # 0=Mon, 6=Sun

# Trading hours (UTC)
_market_hours = {
    'US': (14.5, 21.0),   # NYSE/NASDAQ 14:30-21:00 UTC
    'EU': (7.0, 15.5),    # XETRA 07:00-15:30 UTC
    'FUT': (23.0, 22.0),  # Futures ~23:00-22:00 UTC (nearly 24h)
}

# Determine exchange by symbol
_sym = "{{SYMBOL}}"
if _sym.endswith('.DE') or _sym.endswith('.PA') or _sym.endswith('.AS'):
    _exchange = 'EU'
elif '=F' in _sym:
    _exchange = 'FUT'
else:
    _exchange = 'US'

_open_h, _close_h = _market_hours[_exchange]
if _exchange == 'FUT':
    _is_open = _weekday < 5 and not (_hour >= 22.0 and _hour < 23.0)
else:
    _is_open = _weekday < 5 and _open_h <= _hour < _close_h

print(f'\nMARKET STATUS ({_exchange})')
print(f'  Time:     {_now_utc.strftime("%H:%M UTC")} ({["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][_weekday]})')
if _is_open:
    print(f'  Status:   ✅ MARKET OPEN — normal spreads')
else:
    print(f'  Status:   ⚠️ MARKET CLOSED')
    print(f'  → Turbo spread at market maker 2-5x higher!')
    print(f'  → Use LIMIT ORDER instead of market order!')
    print(f'  → Prices may deviate from fair value')
```

---

## 1.2 Price & Market

| Data Point | Value | Source |
|------------|-------|--------|
| Current Price (USD) | $XX.XX | yfinance |
| EUR/USD Rate | X.XXXX | [Source] |
| Price in EUR | €XX.XX | Calculated |
| Daily Change | +/-X.XX% | yfinance |
| 52-Week High | $XX.XX | yfinance |
| 52-Week Low | $XX.XX | yfinance |
| Volume | XXM | yfinance |

## 1.3 Technical Indicators

| Indicator | Value | Signal | Source |
|-----------|-------|--------|--------|
| RSI (14) | XX.X | Overbought/Neutral/Oversold | yfinance |
| **RSI Delta (1d)** | +/-X.X | Turning up/down/stagnating | yfinance |
| **RSI Divergence** | Bullish/Bearish/None | Price lows vs RSI lows | yfinance |
| MACD | X.XX | Bullish/Bearish Crossover | yfinance |
| SMA 50 | $XX.XX | Price above/below | yfinance |
| SMA 200 | $XX.XX | Price above/below | yfinance |
| Golden/Death Cross | Yes/No | Date of last occurrence | yfinance |

### RSI MOMENTUM & DIVERGENCE (MANDATORY!)

```
╔═══════════════════════════════════════════════════════════════╗
║  RSI alone is NOT enough! Always also check:                  ║
║                                                               ║
║  1. RSI DELTA: Is RSI turning? (+/- per day)                 ║
║  2. RSI DIVERGENCE: Price Lower Low + RSI Higher Low?         ║
║  3. RSI SLOPE: Is the movement accelerating/decelerating?    ║
║                                                               ║
║  RSI 27 + RISING = potential bounce                          ║
║  RSI 27 + FALLING = waterfall, NOT a buy signal!             ║
╚═══════════════════════════════════════════════════════════════╝
```

| RSI Data Point | Value | Interpretation |
|----------------|-------|----------------|
| RSI current | XX.X | Overbought/Neutral/Oversold |
| RSI yesterday | XX.X | Comparison value |
| RSI Delta (1d) | +/-X.X | Positive = turning up, Negative = falling further |
| RSI Delta (3d) | +/-X.X | Short-term trend |
| RSI Delta (5d) | +/-X.X | Medium-term trend |
| RSI Slope (3d avg) | +/-X.XX | Momentum of RSI movement |
| **Divergence** | Bullish/Bearish/None | **Most important signal!** |

**RSI Divergence Classification:**

| Type | Meaning | Strength |
|------|---------|----------|
| **Bullish Divergence** | Price makes Lower Low, RSI makes Higher Low → selling pressure easing | Strongly bullish when RSI <35 |
| **Bearish Divergence** | Price makes Higher High, RSI makes Lower High → buying pressure easing | Strongly bearish when RSI >65 |
| No Divergence | Price and RSI move in sync | Trend intact |

> **DIVERGENCE is often the EARLIEST reversal signal!** If a bullish divergence is detected at RSI <30, it is a strong argument for an upcoming bounce - even if the trend still points downward.

## 1.4 Support & Resistance

| Level | Price | Type | Reasoning |
|-------|-------|------|-----------|
| R3 | $XX.XX | Resistance | [Why this level?] |
| R2 | $XX.XX | Resistance | [Why?] |
| R1 | $XX.XX | Resistance | [Why?] |
| **Current** | **$XX.XX** | — | — |
| S1 | $XX.XX | Support | [Why?] |
| S2 | $XX.XX | Support | [Why?] |
| S3 | $XX.XX | Support | [Why?] |

## 1.5 Short Interest

| Data Point | Value | Meaning |
|------------|-------|---------|
| Short % of Float | XX.X% | Percentage of shorted shares |
| Short Ratio (Days to Cover) | X.X | Days to cover all shorts |

**Short Interest Classification:**
- < 5%: Normal, no special signal
- 5-10%: Elevated skepticism, monitor
- 10-20%: High short interest, short squeeze potential with positive catalysts
- \> 20%: Extremely high, strong squeeze potential BUT also strong bearish conviction
- Short Ratio > 5 days: Shorts cannot cover quickly -> squeeze risk increases

> **High short interest is NOT an automatic buy signal!** It shows skepticism, but can trigger explosive moves with catalysts (earnings beat, news).

---

## 1.6 Volatility & Risk Profile

| Data Point | Value | Meaning |
|------------|-------|---------|
| ATR (14) | $XX.XX (X.X%) | Average daily range |
| Ann. Volatility | XX% | Annualized volatility |
| Beta | X.XX | Market sensitivity |

ATR is used in Step 3 for KO calculation. Here only document the value.

**ATR Event Check (v3 MANDATORY!):**

```python
# ATR Event Check: ATR(5) vs ATR(14)
atr5_data = (hist['High'] - hist['Low']).rolling(5).mean().iloc[-1]
atr14_data = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]
atr5_pct = (atr5_data / price) * 100
atr14_pct = (atr14_data / price) * 100
atr_ratio = atr5_data / atr14_data if atr14_data > 0 else 1.0

print(f'  ATR (5):            ${atr5_data:.2f} ({atr5_pct:.1f}%)')
print(f'  ATR (14):           ${atr14_data:.2f} ({atr14_pct:.1f}%)')
print(f'  ATR(5)/ATR(14):     {atr_ratio:.2f}x')
if atr_ratio > 1.5:
    print('  ⚠️ VOLATILITY ELEVATED! Reduce position by one size level!')
```

**Volatility Classification:**

| ATR % | Classification | Meaning for Turbos |
|-------|----------------|-------------------|
| < 2% | Low | Tight KO possible, but little movement |
| 2-4% | Medium | Standard turbos well suited |
| 4-7% | High | Wider KO needed, higher risk |
| > 7% | Very high | Only with small position, wide KO MANDATORY |

---

## 1.6b REGIME DETECTION (MANDATORY!)

```python
# Regime detection: ADX, BB Width Percentile, DI Spread
# (ADX, +DI, -DI already calculated in 1.0)
import pandas as pd

# Bollinger Band Width Percentile
sma20 = hist['Close'].rolling(20).mean()
std20 = hist['Close'].rolling(20).std()
bb_upper = sma20 + 2 * std20
bb_lower = sma20 - 2 * std20
bb_width = (bb_upper - bb_lower) / sma20
bb_width_clean = bb_width.dropna()
current_bb_width = float(bb_width.iloc[-1])
bb_pctl = round(float((bb_width_clean.tail(120) < current_bb_width).sum() / min(len(bb_width_clean), 120) * 100), 1)

# ADX + DI (from yfinance data)
def calc_adx_manual(high, low, close, period=14):
    plus_dm = high.diff().copy()
    minus_dm = (-low.diff()).copy()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    both = (plus_dm > 0) & (minus_dm > 0)
    plus_dm[both & (plus_dm < minus_dm)] = 0
    minus_dm[both & (minus_dm < plus_dm)] = 0
    tr = pd.Series(np.maximum(
        (high - low).values,
        np.maximum(abs((high - close.shift()).values), abs((low - close.shift()).values))
    ), index=high.index)
    alpha = 1.0 / period
    atr_s = tr.ewm(alpha=alpha, min_periods=period).mean()
    s_plus = plus_dm.ewm(alpha=alpha, min_periods=period).mean()
    s_minus = minus_dm.ewm(alpha=alpha, min_periods=period).mean()
    pdi = 100 * s_plus / atr_s
    mdi = 100 * s_minus / atr_s
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, 1)
    adx_s = dx.ewm(alpha=alpha, min_periods=period).mean()
    return float(adx_s.iloc[-1]), float(pdi.iloc[-1]), float(mdi.iloc[-1])

import numpy as np
adx_val, plus_di, minus_di = calc_adx_manual(hist['High'], hist['Low'], hist['Close'])
di_spread = abs(plus_di - minus_di)

# Determine regime
if adx_val >= 25 and di_spread > 10:
    regime = 'TRENDING'
elif adx_val < 20 and bb_pctl < 30:
    regime = 'RANGE'
elif adx_val < 20 and bb_pctl > 60:
    regime = 'CHOPPY'
else:
    regime = 'TRANSITIONAL'

print(f'\nREGIME DETECTION')
print(f'  ADX:                {adx_val:.1f}')
print(f'  +DI:                {plus_di:.1f}')
print(f'  -DI:                {minus_di:.1f}')
print(f'  DI Spread:          {di_spread:.1f}')
print(f'  BB Width Pctl:      {bb_pctl:.0f}%')
print(f'  → REGIME:           {regime}')
```

**Regime Table:**

| Regime | Condition | Meaning | Weighting |
|--------|-----------|---------|-----------|
| **TRENDING** | ADX ≥ 25 + DI Spread > 10 | Clear trend, trend indicators (SMA, MACD) dominate | Trend ×1.3, Oscillators ×0.7 |
| **RANGE** | ADX < 20 + BB Pctl < 30 | Sideways, oscillators (RSI, BB) dominate | Trend ×0.7, Oscillators ×1.3 |
| **CHOPPY** | ADX < 20 + BB Pctl > 60 | Choppy without direction, ALL signals weaker | Overall ×0.7 |
| **TRANSITIONAL** | Everything else | Transitioning, standard weighting | All ×1.0 |

> **Regime feeds into Step 2 (Debate weighting) and Step 3 (Confidence adjustment)!**

---

## 1.7 News & Catalysts

**Search for REAL NEWS! Use web search for current headlines!**

Search sources:
- **Google News** - `{{SYMBOL}} news today`
- **Reuters** - `site:reuters.com {{SYMBOL}}`
- **Bloomberg** - `site:bloomberg.com {{SYMBOL}}`
- **Seeking Alpha** - `site:seekingalpha.com {{SYMBOL}}`
- **Kitco** (Commodities) - `site:kitco.com`
- **Oil Price** (Oil) - `site:oilprice.com`

**At least 5 news items with EXACT TIMESTAMP:**

| # | Date & Time (UTC) | Headline | Impact | Source | Link |
|---|-------------------|----------|--------|--------|------|
| 1 | DD.MM HH:MM | [Full headline] | 🟢 Bullish / 🔴 Bearish / 🟡 Neutral | [Source] | [URL] |
| 2 | DD.MM HH:MM | [Full headline] | 🟢/🔴/🟡 | [Source] | [URL] |
| 3 | DD.MM HH:MM | [Full headline] | 🟢/🔴/🟡 | [Source] | [URL] |
| 4 | DD.MM HH:MM | [Full headline] | 🟢/🔴/🟡 | [Source] | [URL] |
| 5 | DD.MM HH:MM | [Full headline] | 🟢/🔴/🟡 | [Source] | [URL] |

**For each news item: 1-2 sentences explaining why Bullish/Bearish:**
- News 1: [Explanation]
- News 2: [Explanation]
- News 3: [Explanation]
- News 4: [Explanation]
- News 5: [Explanation]

## 1.7b NEWS INTELLIGENCE SCORING (MANDATORY!)

Rate EACH of the 5+ collected news items on these 7 axes (-2 to +2):

| # | Headline (short) | Relevance | Sentiment | Price Impact | Trend | Earnings | Investor Confidence | Risk Profile | SCORE |
|---|------------------|-----------|-----------|--------------|-------|----------|---------------------|--------------|-------|
| 1 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 2 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 3 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 4 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 5 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |

**Axis Definitions:**
- `Relevance`: How relevant is the news for {{SYMBOL}}? (-2 = irrelevant, +2 = directly relevant)
- `Sentiment`: Overall tone of the news (-2 = very negative, +2 = very positive)
- `Price Impact`: Will the news move the price? (-2 = strong downward pressure, +2 = strong upward pressure)
- `Trend`: Does the news support the current trend? (-2 = strongly against, +2 = strongly in favor)
- `Earnings`: Does it affect earnings/revenue? (-2 = strongly negative, +2 = strongly positive)
- `Investor Confidence`: Effect on investor confidence? (-2 = panic, +2 = euphoria)
- `Risk Profile`: Does the risk profile change? (-2 = much riskier, +2 = safer)

**News Sentiment Index (NSI) = Average of all SCORE values:**

```
NSI > +1.0:         Strongly bullish
NSI +0.3 to +1.0:   Slightly bullish
NSI -0.3 to +0.3:   Neutral
NSI -1.0 to -0.3:   Slightly bearish
NSI < -1.0:         Strongly bearish
```

**NSI = X.XX → [Classification]**

→ NSI is referenced in Step 2 (Debate) and Step 3 (Judge)!

---

## 1.8 Macro Factors

**Current values via web search:**
- Fed/Rates: [Current status + next meeting date]
- USD (DXY): [Current value] + [Trend: rising/falling]
- Inflation: [Last CPI value + date]
- Treasury 10Y: [Current yield]
- Geopolitics: [Current conflicts/events that are relevant]

**Polymarket Check (MANDATORY for macro events!):**
When a relevant macro event is upcoming (FOMC, ECB, CPI, etc.), check market expectations on Polymarket:
- Search: `https://polymarket.com/search?query=[EVENT]`
- Document the odds (e.g. "ECB Hold: 99%, Cut: <1%")
- Do NOT guess what will happen — Polymarket shows what the market EXPECTS
- If market expectation ≠ your assumption → correct your assumption!

| Event | Polymarket Odds | Meaning for Trade |
|-------|-----------------|-------------------|
| [Event 1] | [XX% Scenario A / XX% Scenario B] | [Impact on thesis] |
| [Event 2] | [XX% Scenario A / XX% Scenario B] | [Impact on thesis] |

## 1.9 Fundamental Data

| Factor | Status | Details |
|--------|--------|---------|
| Supply/Demand | [Deficit/Surplus] | [Details] |
| ETF Flows | [Inflow/Outflow] | [Numbers if available] |
| COT Data | [Commercials Long/Short] | [Source] |
| Seasonality | [Bullish/Bearish month?] | [Historical] |

---

## 1.10 CORRELATION CHECK (MANDATORY!)

```
╔═══════════════════════════════════════════════════════════════╗
║  BEFORE opening a new trade:                                  ║
║  Check correlation with existing positions!                   ║
║                                                               ║
║  → Read open positions from memory/portfolio.md              ║
║  → Determine sector concentration                             ║
║  → If >60% in one sector: issue WARNING!                      ║
╚═══════════════════════════════════════════════════════════════╝
```

**Existing open positions (from memory/portfolio.md):**

| Symbol | Sector | Direction | Size (EUR) |
|--------|--------|-----------|------------|
| [from portfolio.md] | [Sector] | LONG/SHORT | XXX EUR |
| [from portfolio.md] | [Sector] | LONG/SHORT | XXX EUR |

**Correlation Assessment:**

| Check | Result | Status |
|-------|--------|--------|
| Same sector as {{SYMBOL}}? | [Yes/No - which ones?] | ✅/⚠️ |
| Same direction (all LONG)? | [Yes/No] | ✅/⚠️ |
| Sector concentration | XX% in [Sector] | ✅ <60% / ⚠️ >60% |
| Correlated with Nasdaq/S&P? | [High/Medium/Low] | ✅/⚠️ |

**If ⚠️ WARNING:**
> High correlation detected! In a 3% Nasdaq crash, ALL positions would bleed simultaneously. Consider: smaller position size, SHORT hedge, or uncorrelated trade (Gold, short turbo on index).

---

## 1.10b PRE-OPEN PATTERN CHECK (MANDATORY!)

```
╔═══════════════════════════════════════════════════════════════╗
║  PRE-OPEN PATTERNS — Backtested Pattern Matching              ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Use preopen_check.py for stochastic patterns:                ║
║  → Gap Fill Rate (how often is the opening gap closed?)       ║
║  → Pattern Hit Rates (LONG/SHORT based on score+regime)       ║
║  → Trap Detection (score high, but hit rate low)              ║
║                                                               ║
║  IMPORTANT: Result influences entry timing!                   ║
║  → Gap Fill >80%: BUY AFTER US Open (gap will be filled)     ║
║  → Pattern Hit >60%: Directional confirmation                 ║
║  → Pattern Hit <50%: WARNING — historically poor!             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Step 1: Check Pattern DB — Symbol in DB?**
```bash
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('Symbols:', d.get('symbols',[])); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NOT IN DB — backtest needed!')"
```

**If {{SYMBOL}} NOT in DB → backtest first!**
```bash
python3 preopen_backtest.py --symbols {{SYMBOL}}
```
> IMPORTANT: Then rebuild pattern DB with ALL symbols (background):
> `python3 preopen_backtest.py --symbols AAPL ARM NVDA GOOGL QBTS IREN APLD ASML VST CEG MU {{SYMBOL}}`

**Step 2: Pre-Open Check with symbol-specific patterns:**
```bash
python3 preopen_check.py {{SYMBOL}}
```

**Step 3: ENTRY TIMING ANALYSIS (MANDATORY!)**

Run the entry timing analysis via CLI:

```bash
python3 preopen_check.py {{SYMBOL}} --entry-timing
```

> **Note:** Results are cached in `memory/entry_timing_cache.json`.
> Cache is automatically invalidated when `preopen_patterns.json` is newer.
> For cache bypass: `python3 preopen_check.py {{SYMBOL}} --entry-timing --force-timing`

**Document the result:**

| Data Point | Value |
|------------|-------|
| LONG Score | XX/100 |
| SHORT Score | XX/100 |
| Pattern LONG Hit | XX% |
| Pattern SHORT Hit | XX% |
| Gap Fill Rate | XX% |
| BB Squeeze | Yes (X%) / No |
| Verdict | LONG / SHORT / WAIT / NO TRADE |
| **Best Entry** | **PRE-MARKET / FIRST-HOUR DIP / AT OPEN** |
| Pre-Market Win% | XX% |
| Open Win% | XX% |
| First-Hour Dip Win% | XX% |

**Entry Timing Recommendation (data-driven!):**

```
╔═══════════════════════════════════════════════════════════════╗
║  ENTRY TIMING — Do NOT guess, let DATA decide!               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Pre-Market Win% > Open Win%:                                ║
║  → Set LIMIT order on turbo at market open                   ║
║  → Pre-Market Win% = directional signal, NOT entry price!    ║
║                                                               ║
║  First-Hour Dip Win% > Pre-Market Win%:                      ║
║  → WAIT after US Open for dip in first hour                  ║
║  → Entry ~16:00-16:30 CET                                    ║
║                                                               ║
║  Open Win% is ALMOST ALWAYS the worst!                       ║
║  → NEVER buy exactly at open (market maker spread!)          ║
║                                                               ║
║  CURRENT GAP:                                                ║
║  Gap today: +X.X% → Compare with historical gap bucket       ║
║  → Use the matching bucket (>1% / >3%) for recommendation    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

> Entry timing is carried over to Step 3 (Judge) and Step 4 (Trading Card)!

---

## 1.11 EVENT CALENDAR

**Upcoming events that could move {{SYMBOL}}:**

| Date | Event | Expected Impact | Relevance |
|------|-------|-----------------|-----------|
| [Date] | Earnings {{SYMBOL}} | 🔴🔴🔴 High | Direct |
| [Date] | Fed Meeting / FOMC | 🔴🔴 Medium-High | Macro |
| [Date] | CPI Data | 🔴 Medium | Macro |
| [Date] | Earnings [Peer] | 🟡 Low-Medium | Sector |
| [Date] | [Other event] | [Impact] | [Relevance] |

**⚠️ EARNINGS WARNING:** If {{SYMBOL}} has earnings < 5 trading days away, this will be factored into Step 3 in the KO calculation (increased ATR multiplier).

---

## ENFORCEMENT

- ✅ yfinance ALWAYS execute first
- ✅ Generate chart and visually analyze
- ✅ Chart analysis table is MANDATORY
- ✅ No web search for price data
- ✅ Every data point with source
- ✅ At least 5 news headlines with date
- ✅ **RSI delta, divergence, and momentum calculated (MANDATORY!)**
- ✅ **News Intelligence Scoring: All news rated on 7 axes, NSI calculated (MANDATORY!)**
- ✅ Correlation check against existing positions (MANDATORY!)
- ✅ Event calendar with earnings and macro dates
- ✅ **Regime detection completed (TRENDING/RANGE/CHOPPY/TRANSITIONAL)**
- ✅ **Intraday context for stocks executed (MANDATORY!)**
- ✅ **Market-Maker Pricing Check: Trading hours verified, spread warning when market closed**
- ✅ **Pre-Open Pattern Check: preopen_check.py executed, Gap Fill + Hit Rates documented**
- ✅ **Symbol in Pattern DB? If not → run preopen_backtest.py --symbols {{SYMBOL}}!**
- ✅ **Entry Timing Analysis: Pre-Market vs Open vs First-Hour Dip compared (MANDATORY!)**
- ✅ **Entry Recommendation: PRE-MARKET / FIRST-HOUR DIP / AT OPEN with Win% documented**

---

## OUTPUT JSON

**IMPORTANT: The JSON block is IN ADDITION to the prose. It replaces NOTHING.**

Generate this structured output at the end of Step 1:

```json
{
  "step": 1,
  "symbol": "{{SYMBOL}}",
  "price_usd": 0.00,
  "price_eur": 0.00,
  "rsi": 0.0,
  "rsi_delta_5d": 0.0,
  "rsi_divergence": "none|bullish|bearish",
  "macd_hist": 0.00,
  "atr_pct": 0.0,
  "regime": "TRENDING|RANGE|CHOPPY|TRANSITIONAL",
  "nsi": 0.00,
  "sma200_dist_pct": 0.0,
  "adx": 0.0,
  "earnings_date": null,
  "support_levels": [0.00, 0.00, 0.00],
  "resistance_levels": [0.00, 0.00, 0.00],
  "preopen_verdict": "LONG|SHORT|WAIT|NO TRADE",
  "preopen_gap_fill_pct": 0,
  "preopen_long_hit_pct": 0,
  "preopen_short_hit_pct": 0,
  "entry_timing": {
    "best_entry": "PRE_MARKET|FIRST_HOUR_DIP|AT_OPEN",
    "pre_market_win_pct": 0,
    "at_open_win_pct": 0,
    "first_hour_dip_win_pct": 0,
    "current_gap_pct": 0.0,
    "gap_bucket": "none|gt1|gt3"
  }
}
```

Fill ALL fields with the actual values from the analysis!

```
✅ [STEP 1: DATA COLLECTION COMPLETE]
```
