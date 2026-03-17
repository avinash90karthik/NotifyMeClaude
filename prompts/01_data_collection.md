# SCHRITT 1: DATENSAMMLUNG

**Asset:** {{SYMBOL}}

---

## STOP! ENFORCEMENT CHECKLIST

```
╔═══════════════════════════════════════════════════════════════╗
║  BEVOR DU ANFAENGST:                                         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ✅ YFINANCE ZUERST: Python-Script fuer Live-Daten (PFLICHT!)║
║  ✅ CHART GENERIEREN: Visuell den Chart analysieren!         ║
║  ✅ ECHTE News: Mit Datum, Quelle und Link                   ║
║  ✅ Web-Suche: NUR fuer News und aktuelle Events             ║
║  ✅ KORRELATION: Bestehende Positionen pruefen!              ║
║                                                               ║
║  ❌ NICHT Web-Suche fuer Preisdaten nutzen (veraltet!)       ║
║  ❌ KEINE erfundenen Daten oder Schaetzungen ohne Quelle     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 0.0 PORTFOLIO.MD AKTUALISIEREN (VOR ANALYSE-START!)

**Lese `memory/portfolio.md` und pruefe ob es aktuell ist.**

Falls der User seit der letzten Aktualisierung einen Trade gemacht hat (neue Position, Teilverkauf, Stop ausgeloest), trage ihn JETZT ein BEVOR die Analyse beginnt.

- Neue Position? → In "Offene Positionen" eintragen (Symbol, Sektor, Wert, Buy-In, KO, Stop)
- Position geschlossen? → In "Geschlossene Trades" verschieben + P&L
- Stop ausgeloest? → Als geschlossen markieren + Verlust eintragen
- Datum der "Letzte Aktualisierung" setzen

**Nach jedem Trade wird portfolio.md auch in Schritt 4 nochmals geprueft.**

---

## 1.0 LIVE-DATEN VIA YFINANCE (PFLICHT!)

**Fuehre IMMER zuerst dieses Python-Script aus:**

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

# Futures-Proxy-Map: Fuer RSI/MACD ETF statt Futures nutzen (kein Rollover-Problem)
FUTURES_ETF_PROXY = {
    'SI=F': 'SLV',   # Silber → iShares Silver ETF
    'GC=F': 'GLD',   # Gold → SPDR Gold ETF
    'CL=F': 'USO',   # Oel → United States Oil ETF
    'NG=F': 'UNG',   # Natural Gas → United States Natural Gas ETF
}

# Hole Preisdaten fuer {{SYMBOL}}
ticker = yf.Ticker("{{SYMBOL}}")
hist = ticker.history(period='3mo')
info = ticker.info

# Fuer Technicals: ETF-Proxy wenn Futures, sonst direkt
proxy_symbol = FUTURES_ETF_PROXY.get("{{SYMBOL}}")
if proxy_symbol:
    proxy_hist = yf.Ticker(proxy_symbol).history(period='3mo')
    close_for_ta = wavelet_denoise(proxy_hist['Close']) if HAS_WAVELET else proxy_hist['Close']
    rsi = calculate_rsi(close_for_ta)
    macd, signal, histogram = calculate_macd(close_for_ta)
    technicals_source = f'{proxy_symbol} (ETF-Proxy, rollover-frei, wavelet-denoised)'
else:
    close_for_ta = wavelet_denoise(hist['Close']) if HAS_WAVELET else hist['Close']
    rsi = calculate_rsi(close_for_ta)
    macd, signal, histogram = calculate_macd(close_for_ta)
    technicals_source = '{{SYMBOL}} (wavelet-denoised)' if HAS_WAVELET else '{{SYMBOL}}'

# EXAKTER TIMESTAMP
now = datetime.utcnow()
last_trade = datetime.fromtimestamp(info.get('regularMarketTime', 0))
market_state = info.get('marketState', 'UNKNOWN')

print('=' * 60)
print('{{SYMBOL}} - LIVE DATEN')
print('=' * 60)
print(f'Analyse-Zeit:      {now.strftime("%Y-%m-%d %H:%M:%S")} UTC')
print(f'Letzter Trade:     {last_trade.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'Market State:      {market_state}')
print(f'Technicals-Quelle: {technicals_source}')
print('=' * 60)
print()
print('PREIS & PERFORMANCE')
print(f'  Aktueller Preis:    ${info.get("currentPrice", 0):.2f}')
print(f'  Tages-Hoch:         ${info.get("dayHigh", 0):.2f}')
print(f'  Tages-Tief:         ${info.get("dayLow", 0):.2f}')
print(f'  Previous Close:     ${info.get("previousClose", 0):.2f}')
print(f'  52W Hoch:           ${info.get("fiftyTwoWeekHigh", 0):.2f}')
print(f'  52W Tief:           ${info.get("fiftyTwoWeekLow", 0):.2f}')
print()
print('MOVING AVERAGES')
print(f'  50-Day SMA:         ${info.get("fiftyDayAverage", 0):.2f}')
print(f'  200-Day SMA:        ${info.get("twoHundredDayAverage", 0):.2f}')
price = info.get('currentPrice', 0)
sma50 = info.get('fiftyDayAverage', 1)
sma200 = info.get('twoHundredDayAverage', 1)
print(f'  Preis vs 50 SMA:    {((price/sma50)-1)*100:.1f}%')
print(f'  Preis vs 200 SMA:   {((price/sma200)-1)*100:.1f}%')
print(f'  Golden Cross:       {"JA" if sma50 > sma200 else "NEIN"}')
print()
print('TECHNISCHE INDIKATOREN')
current_rsi = rsi.iloc[-1]
current_macd = macd.iloc[-1]
current_signal = signal.iloc[-1]
current_hist = histogram.iloc[-1]
rsi_status = "UEBERKAUFT" if current_rsi > 70 else "UEBERVERKAUFT" if current_rsi < 30 else "Neutral"
print(f'  RSI (14):           {current_rsi:.1f} ({rsi_status})')
print(f'  MACD:               {current_macd:.2f}')
print(f'  MACD Signal:        {current_signal:.2f}')
print(f'  MACD Histogram:     {current_hist:.2f} ({"BULLISH" if current_hist > 0 else "BEARISH"})')
print()

# =============================================
# RSI-DELTA, DIVERGENZ & MOMENTUM (NEU!)
# =============================================
print('RSI-MOMENTUM & DIVERGENZ')
prev_rsi = rsi.iloc[-2]
rsi_delta_1d = current_rsi - prev_rsi
rsi_delta_3d = current_rsi - rsi.iloc[-4] if len(rsi) > 4 else 0
rsi_delta_5d = current_rsi - rsi.iloc[-6] if len(rsi) > 6 else 0
print(f'  RSI aktuell:        {current_rsi:.1f}')
print(f'  RSI gestern:        {prev_rsi:.1f}')
print(f'  RSI-Delta (1d):     {rsi_delta_1d:+.1f}')
print(f'  RSI-Delta (3d):     {rsi_delta_3d:+.1f}')
print(f'  RSI-Delta (5d):     {rsi_delta_5d:+.1f}')

# RSI Slope (3-day moving average of RSI delta)
rsi_slope = rsi.diff().rolling(3).mean()
print(f'  RSI-Slope (3d avg): {rsi_slope.iloc[-1]:+.2f}')
prev_slope = rsi_slope.iloc[-2]
print(f'  RSI-Slope vorher:   {prev_slope:+.2f}')
if rsi_slope.iloc[-1] > 0 and prev_slope < 0:
    print('  -> RSI-MOMENTUM DREHT POSITIV!')
elif rsi_slope.iloc[-1] > prev_slope:
    print('  -> RSI-Momentum VERBESSERT sich')
elif rsi_slope.iloc[-1] < 0:
    print('  -> RSI-Momentum NEGATIV')

# RSI Status bei Extremen
if current_rsi < 30:
    if rsi_delta_1d > 0:
        print(f'  SIGNAL: RSI OVERSOLD + DREHT HOCH ({rsi_delta_1d:+.1f}/Tag)')
    else:
        print(f'  SIGNAL: RSI OVERSOLD + FAELLT WEITER ({rsi_delta_1d:+.1f}/Tag)')
elif current_rsi > 70:
    if rsi_delta_1d < 0:
        print(f'  SIGNAL: RSI OVERBOUGHT + DREHT RUNTER ({rsi_delta_1d:+.1f}/Tag)')
    else:
        print(f'  SIGNAL: RSI OVERBOUGHT + STEIGT WEITER ({rsi_delta_1d:+.1f}/Tag)')

# Divergenz-Check: Vergleiche letzte 2 Preis-Tiefs mit RSI-Tiefs
print()
print('  DIVERGENZ-CHECK (letzte 30 Tage):')
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
    print(f'  Tief 1: {last_two[0][0]} Preis=${last_two[0][1]:.2f} RSI={last_two[0][2]:.1f}')
    print(f'  Tief 2: {last_two[1][0]} Preis=${last_two[1][1]:.2f} RSI={last_two[1][2]:.1f}')
    if price_lower and rsi_higher:
        print('  -> BULLISCHE DIVERGENZ (Preis Lower Low, RSI Higher Low)')
    elif not price_lower and not rsi_higher:
        print('  -> BEARISCHE DIVERGENZ (Preis Higher Low, RSI Lower Low)')
    else:
        print('  -> Keine Divergenz bei Tiefs')
else:
    print('  Nicht genug Tiefs fuer Divergenz-Check')

if len(highs) >= 2:
    last_two_h = highs[-2:]
    price_higher = last_two_h[1][1] > last_two_h[0][1]
    rsi_lower = last_two_h[1][2] < last_two_h[0][2]
    print(f'  Hoch 1: {last_two_h[0][0]} Preis=${last_two_h[0][1]:.2f} RSI={last_two_h[0][2]:.1f}')
    print(f'  Hoch 2: {last_two_h[1][0]} Preis=${last_two_h[1][1]:.2f} RSI={last_two_h[1][2]:.1f}')
    if price_higher and rsi_lower:
        print('  -> BEARISCHE DIVERGENZ (Preis Higher High, RSI Lower High)')
    elif not price_higher and not rsi_lower:
        print('  -> BULLISCHE DIVERGENZ (Preis Lower High, RSI Higher High)')
    else:
        print('  -> Keine Divergenz bei Hochs')

print()
print('SHORT INTEREST')
print(f'  Shares Short:       {info.get("sharesShort", 0):,}')
print(f'  Short % of Float:   {info.get("shortPercentOfFloat", 0)*100:.1f}%')
print(f'  Short Ratio (Days): {info.get("shortRatio", 0):.1f}')
print()
print('BEWERTUNG')
print(f'  Market Cap:         ${info.get("marketCap", 0)/1e9:.1f}B')
print(f'  P/S Ratio:          {info.get("priceToSalesTrailing12Months", 0):.0f}x')
print(f'  P/B Ratio:          {info.get("priceToBook", 0):.1f}x')
print()
print('CASH & SCHULDEN')
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
print('VOLATILITAET')
atr_data = hist['High'] - hist['Low']
atr14 = atr_data.rolling(14).mean().iloc[-1]
atr_pct = (atr14 / price) * 100
ann_vol = hist['Close'].pct_change().std() * (252**0.5) * 100
beta = info.get('beta', 'N/A')
print(f'  ATR (14):           ${atr14:.2f} ({atr_pct:.1f}%)')
print(f'  Ann. Volatilitaet:  {ann_vol:.0f}%')
print(f'  Beta:               {beta}')
print()
print('RISK SCORES')
print(f'  Overall Risk:       {info.get("overallRisk", "N/A")}/10')
print()

# EARNINGS-KALENDER
print('EARNINGS & EVENTS')
try:
    cal = ticker.calendar
    if cal is not None and len(cal) > 0:
        print(f'  Naechste Earnings:  {cal}')
    else:
        print('  Naechste Earnings:  Keine Daten verfuegbar')
except:
    print('  Naechste Earnings:  Keine Daten verfuegbar')
```

**WICHTIG:**
- ❌ NIEMALS Web-Suche fuer Preisdaten nutzen - immer yfinance!
- ✅ Web-Suche NUR fuer News und aktuelle Events
- ✅ Die yfinance-Daten sind die WAHRHEIT - nutze sie!

---

## 1.1 CHART GENERIEREN & ANALYSIEREN (PFLICHT!)

**Fuehre diesen Befehl aus (nutze Pfade aus `.env`):**

```bash
source .env 2>/dev/null
VENV="${YFINANCE_VENV:-python3}"
SCRIPT="${CHART_SCRIPT:-}"
OUTPUT="${CHART_OUTPUT_DIR:-charts}"
if [ -z "$SCRIPT" ]; then echo "Chart uebersprungen (CHART_SCRIPT nicht gesetzt)"; else $VENV $SCRIPT {{SYMBOL}}; fi
```

**Dann lies den Chart:**

```
Lies die Datei: ${CHART_OUTPUT_DIR}/{{SYMBOL}}_chart.png
```

### CHART-INHALTE (4 Panels)

| Panel | Inhalt | Farben |
|-------|--------|--------|
| 1 | Candlesticks + Moving Averages | SMA 50 = Orange, SMA 200 = Purple |
| 2 | RSI (14) | Gelb, Overbought 70 = Rot, Oversold 30 = Gruen |
| 3 | Volume | Gruen = Bullish, Rot = Bearish |
| 4 | Money Flow | CMF = Cyan, OBV = Magenta |

### INITIALE CHART-ANALYSE (PFLICHT-TABELLE)

Dokumentiere was du im Chart siehst:

| Aspekt | Beobachtung |
|--------|-------------|
| **Trend** | Aufwaerts/Abwaerts/Seitwaerts |
| **SMA 50/200** | Golden Cross / Death Cross / Neutral |
| **RSI** | Ueberkauft (>70) / Ueberverkauft (<30) / Neutral |
| **Volume** | Steigend/Fallend bei Preisbewegung |
| **CMF** | Positiv (Akkumulation) / Negativ (Distribution) |
| **Pattern** | Double Top/Bottom, H&S, Triangle, etc. |
| **Support** | Sichtbare Support-Levels im Chart |
| **Resistance** | Sichtbare Resistance-Levels im Chart |

---

## 1.1b INTRADAY-KONTEXT (PFLICHT fuer Aktien)

**NUR als Kontext, NICHT fuer Indikator-Berechnung!**

```python
# Intraday-Daten (1h, letzte 5 Tage)
try:
    intraday = yf.download("{{SYMBOL}}", period='5d', interval='1h', progress=False)
    if intraday is not None and len(intraday) > 0:
        # Flatten MultiIndex if needed
        if intraday.columns.nlevels > 1:
            intraday.columns = intraday.columns.get_level_values(0)

        # Volume-Profil: Top 3 Preis-Zonen nach Volumen
        price_bins = pd.cut(intraday['Close'], bins=20)
        vol_profile = intraday.groupby(price_bins, observed=True)['Volume'].sum().sort_values(ascending=False)
        print('INTRADAY-KONTEXT (5d, 1h)')
        print('  Volume-Profil (Top 3 Zonen):')
        for i, (zone, vol) in enumerate(vol_profile.head(3).items()):
            print(f'    {i+1}. ${zone.left:.2f}-${zone.right:.2f}: {vol:,.0f}')

        # VWAP Approximation (5d)
        vwap = (intraday['Close'] * intraday['Volume']).sum() / intraday['Volume'].sum()
        print(f'  VWAP (5d):          ${vwap:.2f}')
        print(f'  Preis vs VWAP:      {((price/vwap)-1)*100:+.1f}%')

        # Intraday Range (5d)
        intra_high = float(intraday['High'].max())
        intra_low = float(intraday['Low'].min())
        print(f'  5d Intraday-Range:  ${intra_low:.2f} - ${intra_high:.2f}')

        # Momentum: letzte 6h vs vorherige 6h
        if len(intraday) >= 12:
            recent_6h = intraday['Close'].iloc[-6:]
            prior_6h = intraday['Close'].iloc[-12:-6]
            recent_chg = (float(recent_6h.iloc[-1]) - float(recent_6h.iloc[0])) / float(recent_6h.iloc[0]) * 100
            prior_chg = (float(prior_6h.iloc[-1]) - float(prior_6h.iloc[0])) / float(prior_6h.iloc[0]) * 100
            momentum = 'BESCHLEUNIGEND' if abs(recent_chg) > abs(prior_chg) and recent_chg * prior_chg > 0 else 'VERLANGSAMEND' if abs(recent_chg) < abs(prior_chg) else 'WECHSELND'
            print(f'  Momentum (6h):      {momentum} (letzte {recent_chg:+.2f}% vs vorher {prior_chg:+.2f}%)')
    else:
        print('INTRADAY-KONTEXT: Keine Daten verfuegbar (Futures/Wochenende)')
except Exception as e:
    print(f'INTRADAY-KONTEXT: Nicht verfuegbar ({e})')
```

> **Hinweis:** Intraday-Daten dienen NUR als zusaetzlicher Kontext fuer Entry-Timing. Alle technischen Indikatoren (RSI, MACD, ATR etc.) werden ausschliesslich auf Daily-Basis berechnet. Wenn Intraday-Daten nicht verfuegbar (manche Futures/Rohstoffe, Wochenende) → ueberspringen.

### MARKET-MAKER-PRICING CHECK (automatisch!)

```python
# Market-Status-Check: Automatische Warnung bei geschlossenem Markt
from datetime import datetime, timezone

_now_utc = datetime.now(timezone.utc)
_hour = _now_utc.hour + _now_utc.minute / 60
_weekday = _now_utc.weekday()  # 0=Mon, 6=Sun

# Handelszeiten (UTC)
_market_hours = {
    'US': (14.5, 21.0),   # NYSE/NASDAQ 14:30-21:00 UTC
    'EU': (7.0, 15.5),    # XETRA 07:00-15:30 UTC
    'FUT': (23.0, 22.0),  # Futures ~23:00-22:00 UTC (fast 24h)
}

# Bestimme Boerse nach Symbol
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

print(f'\nMARKET-STATUS ({_exchange})')
print(f'  Zeit:     {_now_utc.strftime("%H:%M UTC")} ({["Mo","Di","Mi","Do","Fr","Sa","So"][_weekday]})')
if _is_open:
    print(f'  Status:   ✅ MARKT OFFEN — normale Spreads')
else:
    print(f'  Status:   ⚠️ MARKT GESCHLOSSEN')
    print(f'  → Turbo-Spread beim Market Maker 2-5x hoeher!')
    print(f'  → LIMIT-ORDER statt Market-Order nutzen!')
    print(f'  → Preise koennen vom Fair Value abweichen')
```

---

## 1.2 Preis & Markt

| Datenpunkt | Wert | Quelle |
|------------|------|--------|
| Aktueller Preis (USD) | $XX.XX | yfinance |
| EUR/USD Kurs | X.XXXX | [Quelle] |
| Preis in EUR | €XX.XX | Berechnet |
| Tagesveraenderung | +/-X.XX% | yfinance |
| 52-Wochen Hoch | $XX.XX | yfinance |
| 52-Wochen Tief | $XX.XX | yfinance |
| Volumen | XXM | yfinance |

## 1.3 Technische Indikatoren

| Indikator | Wert | Signal | Quelle |
|-----------|------|--------|--------|
| RSI (14) | XX.X | Ueberkauft/Neutral/Ueberverkauft | yfinance |
| **RSI-Delta (1d)** | +/-X.X | Dreht hoch/runter/stagniert | yfinance |
| **RSI-Divergenz** | Bullisch/Bearisch/Keine | Preis-Tiefs vs RSI-Tiefs | yfinance |
| MACD | X.XX | Bullish/Bearish Crossover | yfinance |
| SMA 50 | $XX.XX | Preis darueber/darunter | yfinance |
| SMA 200 | $XX.XX | Preis darueber/darunter | yfinance |
| Golden/Death Cross | Ja/Nein | Datum des letzten | yfinance |

### RSI-MOMENTUM & DIVERGENZ (PFLICHT!)

```
╔═══════════════════════════════════════════════════════════════╗
║  RSI allein reicht NICHT! Immer auch pruefen:                ║
║                                                               ║
║  1. RSI-DELTA: Dreht der RSI? (+/- pro Tag)                 ║
║  2. RSI-DIVERGENZ: Preis Lower Low + RSI Higher Low?         ║
║  3. RSI-SLOPE: Beschleunigt/verlangsamt sich die Bewegung?  ║
║                                                               ║
║  RSI 27 + STEIGEND = potentieller Bounce                    ║
║  RSI 27 + FALLEND  = Wasserfall, kein Kaufsignal!           ║
╚═══════════════════════════════════════════════════════════════╝
```

| RSI-Datenpunkt | Wert | Interpretation |
|----------------|------|----------------|
| RSI aktuell | XX.X | Ueberkauft/Neutral/Ueberverkauft |
| RSI gestern | XX.X | Vergleichswert |
| RSI-Delta (1d) | +/-X.X | Positiv = dreht hoch, Negativ = faellt weiter |
| RSI-Delta (3d) | +/-X.X | Kurzfristiger Trend |
| RSI-Delta (5d) | +/-X.X | Mittelfristiger Trend |
| RSI-Slope (3d avg) | +/-X.XX | Momentum der RSI-Bewegung |
| **Divergenz** | Bullisch/Bearisch/Keine | **Wichtigstes Signal!** |

**RSI-Divergenz-Einordnung:**

| Typ | Bedeutung | Staerke |
|-----|-----------|---------|
| **Bullische Divergenz** | Preis macht Lower Low, RSI macht Higher Low → Verkaufsdruck laesst nach | Stark bullisch wenn RSI <35 |
| **Bearische Divergenz** | Preis macht Higher High, RSI macht Lower High → Kaufdruck laesst nach | Stark bearisch wenn RSI >65 |
| Keine Divergenz | Preis und RSI bewegen sich synchron | Trend intakt |

> **DIVERGENZ ist oft das FRUEHESTE Umkehrsignal!** Wenn eine bullische Divergenz bei RSI <30 erkannt wird, ist das ein starkes Argument fuer einen bevorstehenden Bounce - auch wenn der Trend noch abwaerts zeigt.

## 1.4 Support & Resistance

| Level | Preis | Typ | Begruendung |
|-------|-------|-----|-------------|
| R3 | $XX.XX | Resistance | [Warum dieses Level?] |
| R2 | $XX.XX | Resistance | [Warum?] |
| R1 | $XX.XX | Resistance | [Warum?] |
| **Aktuell** | **$XX.XX** | — | — |
| S1 | $XX.XX | Support | [Warum?] |
| S2 | $XX.XX | Support | [Warum?] |
| S3 | $XX.XX | Support | [Warum?] |

## 1.5 Short Interest

| Datenpunkt | Wert | Bedeutung |
|------------|------|-----------|
| Short % of Float | XX.X% | Anteil der geshorteten Aktien |
| Short Ratio (Days to Cover) | X.X | Tage um alle Shorts zu covern |

**Short-Interest-Einordnung:**
- < 5%: Normal, kein besonderes Signal
- 5-10%: Erhoehte Skepsis, beobachten
- 10-20%: Hohes Short Interest, Short-Squeeze-Potential bei positiven Katalysatoren
- \> 20%: Extrem hoch, starkes Squeeze-Potential ABER auch starke bearishe Ueberzeugung
- Short Ratio > 5 Tage: Shorts koennen nicht schnell covern -> Squeeze-Risiko steigt

> **Hoher Short Interest ist KEIN automatisches Kaufsignal!** Er zeigt Skepsis, kann aber bei Katalysatoren (Earnings Beat, News) explosive Moves ausloesen.

---

## 1.6 Volatilitaet & Risiko-Profil

| Datenpunkt | Wert | Bedeutung |
|------------|------|-----------|
| ATR (14) | $XX.XX (X.X%) | Durchschnittliche Tagesschwankung |
| Ann. Volatilitaet | XX% | Jahres-Volatilitaet |
| Beta | X.XX | Markt-Sensitivitaet |

ATR wird in Schritt 3 fuer die KO-Berechnung genutzt. Hier nur den Wert dokumentieren.

**ATR Event-Check (v3 PFLICHT!):**

```python
# ATR Event-Check: ATR(5) vs ATR(14)
atr5_data = (hist['High'] - hist['Low']).rolling(5).mean().iloc[-1]
atr14_data = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]
atr5_pct = (atr5_data / price) * 100
atr14_pct = (atr14_data / price) * 100
atr_ratio = atr5_data / atr14_data if atr14_data > 0 else 1.0

print(f'  ATR (5):            ${atr5_data:.2f} ({atr5_pct:.1f}%)')
print(f'  ATR (14):           ${atr14_data:.2f} ({atr14_pct:.1f}%)')
print(f'  ATR(5)/ATR(14):     {atr_ratio:.2f}x')
if atr_ratio > 1.5:
    print('  ⚠️ VOLATILITAET ERHOEHT! Position eine Stufe kleiner!')
```

**Volatilitaets-Einordnung:**

| ATR % | Einordnung | Bedeutung fuer Turbos |
|-------|------------|----------------------|
| < 2% | Niedrig | Enger KO moeglich, aber wenig Bewegung |
| 2-4% | Mittel | Standard-Turbos gut geeignet |
| 4-7% | Hoch | Weiter KO noetig, hoeheres Risiko |
| > 7% | Sehr hoch | Nur mit kleiner Position, weiter KO PFLICHT |

---

## 1.6b REGIME-ERKENNUNG (PFLICHT!)

```python
# Regime-Erkennung: ADX, BB-Width-Percentile, DI-Spread
# (ADX, +DI, -DI bereits in 1.0 berechnet)
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

# ADX + DI (aus yfinance-Daten)
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

# Regime bestimmen
if adx_val >= 25 and di_spread > 10:
    regime = 'TRENDING'
elif adx_val < 20 and bb_pctl < 30:
    regime = 'RANGE'
elif adx_val < 20 and bb_pctl > 60:
    regime = 'CHOPPY'
else:
    regime = 'TRANSITIONAL'

print(f'\nREGIME-ERKENNUNG')
print(f'  ADX:                {adx_val:.1f}')
print(f'  +DI:                {plus_di:.1f}')
print(f'  -DI:                {minus_di:.1f}')
print(f'  DI-Spread:          {di_spread:.1f}')
print(f'  BB-Width-Pctl:      {bb_pctl:.0f}%')
print(f'  → REGIME:           {regime}')
```

**Regime-Tabelle:**

| Regime | Bedingung | Bedeutung | Gewichtung |
|--------|-----------|-----------|------------|
| **TRENDING** | ADX ≥ 25 + DI-Spread > 10 | Klarer Trend, Trend-Indikatoren (SMA, MACD) dominieren | Trend ×1.3, Oszillatoren ×0.7 |
| **RANGE** | ADX < 20 + BB-Pctl < 30 | Seitwaerts, Oszillatoren (RSI, BB) dominieren | Trend ×0.7, Oszillatoren ×1.3 |
| **CHOPPY** | ADX < 20 + BB-Pctl > 60 | Unruhig ohne Richtung, ALLE Signale schwaecher | Gesamt ×0.7 |
| **TRANSITIONAL** | Alles andere | Uebergang, Standardgewichtung | Alles ×1.0 |

> **Regime fließt in Schritt 2 (Debate Gewichtung) und Schritt 3 (Konfidenz-Adjustment) ein!**

---

## 1.7 News & Katalysatoren

**Suche ECHTE NEWS! Nutze Web-Suche fuer aktuelle Headlines!**

Suchquellen:
- **Google News** - `{{SYMBOL}} news today`
- **Reuters** - `site:reuters.com {{SYMBOL}}`
- **Bloomberg** - `site:bloomberg.com {{SYMBOL}}`
- **Seeking Alpha** - `site:seekingalpha.com {{SYMBOL}}`
- **Kitco** (Commodities) - `site:kitco.com`
- **Oil Price** (Oel) - `site:oilprice.com`

**Mindestens 5 News-Items mit EXAKTEM TIMESTAMP:**

| # | Datum & Uhrzeit (UTC) | Headline | Impact | Quelle | Link |
|---|----------------------|----------|--------|--------|------|
| 1 | DD.MM HH:MM | [Vollstaendige Headline] | 🟢 Bullish / 🔴 Bearish / 🟡 Neutral | [Quelle] | [URL] |
| 2 | DD.MM HH:MM | [Vollstaendige Headline] | 🟢/🔴/🟡 | [Quelle] | [URL] |
| 3 | DD.MM HH:MM | [Vollstaendige Headline] | 🟢/🔴/🟡 | [Quelle] | [URL] |
| 4 | DD.MM HH:MM | [Vollstaendige Headline] | 🟢/🔴/🟡 | [Quelle] | [URL] |
| 5 | DD.MM HH:MM | [Vollstaendige Headline] | 🟢/🔴/🟡 | [Quelle] | [URL] |

**Fuer jede News: 1-2 Saetze Erklaerung warum Bullish/Bearish:**
- News 1: [Erklaerung]
- News 2: [Erklaerung]
- News 3: [Erklaerung]
- News 4: [Erklaerung]
- News 5: [Erklaerung]

## 1.7b NEWS INTELLIGENCE SCORING (PFLICHT!)

Bewerte JEDE der 5+ gesammelten News auf diesen 7 Achsen (-2 bis +2):

| # | Headline (kurz) | Relevanz | Sentiment | Preis-Impact | Trend | Earnings | Investoren-Vertrauen | Risiko-Profil | SCORE |
|---|-----------------|----------|-----------|--------------|-------|----------|---------------------|---------------|-------|
| 1 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 2 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 3 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 4 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |
| 5 | [Headline] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | [-2..+2] | Σ/7 |

**Achsen-Definitionen:**
- `Relevanz`: Wie relevant ist die News fuer {{SYMBOL}}? (-2 = irrelevant, +2 = direkt)
- `Sentiment`: Grundstimmung der Nachricht (-2 = sehr negativ, +2 = sehr positiv)
- `Preis-Impact`: Wird die News den Preis bewegen? (-2 = starker Druck runter, +2 = starker Druck hoch)
- `Trend`: Unterstuetzt die News den aktuellen Trend? (-2 = stark dagegen, +2 = stark dafuer)
- `Earnings`: Wirkt sich auf Earnings/Umsatz aus? (-2 = stark negativ, +2 = stark positiv)
- `Investoren-Vertrauen`: Effekt auf Investoren-Vertrauen? (-2 = Panik, +2 = Euphorie)
- `Risiko-Profil`: Aendert sich das Risiko-Profil? (-2 = viel riskanter, +2 = sicherer)

**News Sentiment Index (NSI) = Durchschnitt aller SCORE-Werte:**

```
NSI > +1.0:         Stark bullisch
NSI +0.3 bis +1.0:  Leicht bullisch
NSI -0.3 bis +0.3:  Neutral
NSI -1.0 bis -0.3:  Leicht bearisch
NSI < -1.0:         Stark bearisch
```

**NSI = X.XX → [Einordnung]**

→ NSI wird in Schritt 2 (Debate) und Schritt 3 (Judge) referenziert!

---

## 1.8 Makro-Faktoren

**Aktuelle Werte via Web-Suche:**
- Fed/Zinsen: [Aktueller Stand + naechstes Meeting Datum]
- USD (DXY): [Aktueller Wert] + [Trend: steigend/fallend]
- Inflation: [Letzter CPI Wert + Datum]
- Treasury 10Y: [Aktueller Yield]
- Geopolitik: [Aktuelle Konflikte/Events die relevant sind]

**Polymarket-Check (PFLICHT bei Makro-Events!):**
Wenn ein relevantes Makro-Event ansteht (FOMC, ECB, CPI, etc.), pruefe die Markt-Erwartungen auf Polymarket:
- Suche: `https://polymarket.com/search?query=[EVENT]`
- Dokumentiere die Odds (z.B. "ECB Hold: 99%, Cut: <1%")
- NICHT raten was passiert — Polymarket zeigt was der Markt ERWARTET
- Wenn Markt-Erwartung ≠ deine Annahme → Annahme korrigieren!

| Event | Polymarket Odds | Bedeutung fuer Trade |
|-------|-----------------|----------------------|
| [Event 1] | [XX% Szenario A / XX% Szenario B] | [Impact auf These] |
| [Event 2] | [XX% Szenario A / XX% Szenario B] | [Impact auf These] |

## 1.9 Fundamentaldaten

| Faktor | Status | Details |
|--------|--------|---------|
| Angebot/Nachfrage | [Defizit/Ueberschuss] | [Details] |
| ETF Flows | [Inflow/Outflow] | [Zahlen wenn verfuegbar] |
| COT Daten | [Commercials Long/Short] | [Quelle] |
| Saisonalitaet | [Bullish/Bearish Monat?] | [Historisch] |

---

## 1.10 KORRELATIONS-CHECK (PFLICHT!)

```
╔═══════════════════════════════════════════════════════════════╗
║  BEVOR ein neuer Trade eroeffnet wird:                       ║
║  Pruefe Korrelation zu bestehenden Positionen!               ║
║                                                               ║
║  → Lies offene Positionen aus memory/portfolio.md            ║
║  → Bestimme Sektor-Konzentration                             ║
║  → Wenn >60% in einem Sektor: WARNUNG ausgeben!              ║
╚═══════════════════════════════════════════════════════════════╝
```

**Bestehende offene Positionen (aus memory/portfolio.md):**

| Symbol | Sektor | Richtung | Groesse (EUR) |
|--------|--------|----------|---------------|
| [aus portfolio.md] | [Sektor] | LONG/SHORT | XXX EUR |
| [aus portfolio.md] | [Sektor] | LONG/SHORT | XXX EUR |

**Korrelations-Bewertung:**

| Pruefung | Ergebnis | Status |
|----------|----------|--------|
| Gleicher Sektor wie {{SYMBOL}}? | [Ja/Nein - welche?] | ✅/⚠️ |
| Gleiche Richtung (alle LONG)? | [Ja/Nein] | ✅/⚠️ |
| Sektor-Konzentration | XX% in [Sektor] | ✅ <60% / ⚠️ >60% |
| Korreliert mit Nasdaq/S&P? | [Hoch/Mittel/Niedrig] | ✅/⚠️ |

**Wenn ⚠️ WARNUNG:**
> Hohe Korrelation erkannt! Bei einem Nasdaq-Einbruch von 3% wuerden ALLE Positionen gleichzeitig bluten. Erwaege: kleinere Positionsgroesse, SHORT-Hedge, oder unkorrelierten Trade (Gold, Short-Turbo auf Index).

---

## 1.10b PRE-OPEN PATTERN CHECK (PFLICHT!)

```
╔═══════════════════════════════════════════════════════════════╗
║  PRE-OPEN PATTERNS — Backtested Pattern-Matching              ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Nutze preopen_check.py fuer stochastische Muster:            ║
║  → Gap Fill Rate (wie oft wird der Opening-Gap geschlossen?)  ║
║  → Pattern Hit Rates (LONG/SHORT basierend auf Score+Regime)  ║
║  → Trap-Erkennung (Score hoch, aber Hit Rate niedrig)         ║
║                                                               ║
║  WICHTIG: Ergebnis beeinflusst Entry-Timing!                  ║
║  → Gap Fill >80%: NACH US-Open kaufen (Gap wird gefuellt)     ║
║  → Pattern Hit >60%: Richtungs-Bestaetigung                   ║
║  → Pattern Hit <50%: WARNUNG — historisch schlecht!            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Schritt 1: Pattern-DB pruefen — Symbol in DB?**
```bash
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('Symbols:', d.get('symbols',[])); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NICHT IN DB — backtest noetig!')"
```

**Wenn {{SYMBOL}} NICHT in DB → erst backtesten!**
```bash
python3 preopen_backtest.py --symbols {{SYMBOL}}
```
> WICHTIG: Danach Pattern-DB mit ALLEN Symbolen neu bauen (Hintergrund):
> `python3 preopen_backtest.py --symbols AAPL ARM NVDA GOOGL QBTS IREN APLD ASML VST CEG MU {{SYMBOL}}`

**Schritt 2: Pre-Open Check mit symbol-spezifischen Patterns:**
```bash
python3 preopen_check.py {{SYMBOL}}
```

**Schritt 3: ENTRY-TIMING ANALYSE (PFLICHT!)**

Fuehre die Entry-Timing Analyse via CLI aus:

```bash
python3 preopen_check.py {{SYMBOL}} --entry-timing
```

> **Hinweis:** Ergebnisse werden in `memory/entry_timing_cache.json` gecacht.
> Cache wird automatisch invalidiert wenn `preopen_patterns.json` neuer ist.
> Fuer Cache-Bypass: `python3 preopen_check.py {{SYMBOL}} --entry-timing --force-timing`

**Dokumentiere das Ergebnis:**

| Datenpunkt | Wert |
|------------|------|
| LONG Score | XX/100 |
| SHORT Score | XX/100 |
| Pattern LONG Hit | XX% |
| Pattern SHORT Hit | XX% |
| Gap Fill Rate | XX% |
| BB Squeeze | Ja (X%) / Nein |
| Verdict | LONG / SHORT / WAIT / KEIN TRADE |
| **Bester Entry** | **PRE-MARKET / FIRST-HOUR DIP / BEI OPEN** |
| Pre-Market Win% | XX% |
| Open Win% | XX% |
| First-Hour Dip Win% | XX% |

**Entry-Timing Empfehlung (datenbasiert!):**

```
╔═══════════════════════════════════════════════════════════════╗
║  ENTRY-TIMING — NICHT raten, DATEN entscheiden!              ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Pre-Market Win% > Open Win%:                                ║
║  → LIMIT-Order auf Turbo bei Market-Open setzen              ║
║  → Pre-Market Win% = Richtungs-Signal, nicht Entry-Preis!    ║
║                                                               ║
║  First-Hour Dip Win% > Pre-Market Win%:                      ║
║  → NACH US-Open warten auf Dip in erster Stunde             ║
║  → Entry ~16:00-16:30 CET                                    ║
║                                                               ║
║  Open Win% ist FAST IMMER am schlechtesten!                  ║
║  → NIEMALS exakt bei Open kaufen (Market-Maker-Spread!)     ║
║                                                               ║
║  AKTUELLES GAP:                                              ║
║  Gap heute: +X.X% → Vergleiche mit historischem Gap-Bucket   ║
║  → Nutze das passende Bucket (>1% / >3%) fuer die Empfehlung║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

> Entry-Timing wird in Schritt 3 (Judge) und Schritt 4 (Trading Card) uebernommen!

---

## 1.11 EVENT-KALENDER

**Kommende Events die {{SYMBOL}} bewegen koennten:**

| Datum | Event | Erwarteter Impact | Relevanz |
|-------|-------|-------------------|----------|
| [Datum] | Earnings {{SYMBOL}} | 🔴🔴🔴 Hoch | Direkt |
| [Datum] | Fed Meeting / FOMC | 🔴🔴 Mittel-Hoch | Makro |
| [Datum] | CPI-Daten | 🔴 Mittel | Makro |
| [Datum] | Earnings [Peer] | 🟡 Niedrig-Mittel | Sektor |
| [Datum] | [Anderes Event] | [Impact] | [Relevanz] |

**⚠️ EARNINGS-WARNUNG:** Wenn {{SYMBOL}} Earnings < 5 Handelstage entfernt sind, wird dies in Schritt 3 bei der KO-Berechnung beruecksichtigt (erhoehter ATR-Multiplikator).

---

## ENFORCEMENT

- ✅ yfinance IMMER zuerst ausfuehren
- ✅ Chart generieren und visuell analysieren
- ✅ Chart-Analyse-Tabelle ist PFLICHT
- ✅ Keine Web-Suche fuer Preisdaten
- ✅ Jeder Datenpunkt mit Quelle
- ✅ Mindestens 5 News-Headlines mit Datum
- ✅ **RSI-Delta, Divergenz und Momentum berechnet (PFLICHT!)**
- ✅ **News Intelligence Scoring: Alle News auf 7 Achsen bewertet, NSI berechnet (PFLICHT!)**
- ✅ Korrelations-Check gegen bestehende Positionen (PFLICHT!)
- ✅ Event-Kalender mit Earnings und Makro-Terminen
- ✅ **Regime-Erkennung durchgefuehrt (TRENDING/RANGE/CHOPPY/TRANSITIONAL)**
- ✅ **Intraday-Kontext fuer Aktien ausgefuehrt (PFLICHT!)**
- ✅ **Market-Maker-Pricing Check: Handelszeiten geprueft, Spread-Warnung bei geschlossenem Markt**
- ✅ **Pre-Open Pattern Check: preopen_check.py ausgefuehrt, Gap Fill + Hit Rates dokumentiert**
- ✅ **Symbol in Pattern-DB? Wenn nicht → preopen_backtest.py --symbols {{SYMBOL}} ausfuehren!**
- ✅ **Entry-Timing Analyse: Pre-Market vs Open vs First-Hour Dip verglichen (PFLICHT!)**
- ✅ **Entry-Empfehlung: PRE-MARKET / FIRST-HOUR DIP / BEI OPEN mit Win% dokumentiert**

---

## OUTPUT JSON

**WICHTIG: Der JSON-Block ist ZUSAETZLICH zur Prosa. Er ersetzt NICHTS.**

Generiere am Ende von Schritt 1 diesen strukturierten Output:

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
  "preopen_verdict": "LONG|SHORT|WAIT|KEIN TRADE",
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

Fuelle ALLE Felder mit den tatsaechlichen Werten aus der Analyse!

```
✅ [SCHRITT 1: DATENSAMMLUNG ABGESCHLOSSEN]
```
