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

def calculate_rsi(data, periods=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data):
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

from datetime import datetime

# Hole Daten fuer {{SYMBOL}}
ticker = yf.Ticker("{{SYMBOL}}")
hist = ticker.history(period='3mo')
info = ticker.info

# Berechne Technicals
rsi = calculate_rsi(hist)
macd, signal, histogram = calculate_macd(hist)

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
SCRIPT="${CHART_SCRIPT:-scripts/generate_chart.py}"
OUTPUT="${CHART_OUTPUT_DIR:-charts}"
$VENV $SCRIPT {{SYMBOL}}
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

**Volatilitaets-Einordnung:**

| ATR % | Einordnung | Bedeutung fuer Turbos |
|-------|------------|----------------------|
| < 2% | Niedrig | Enger KO moeglich, aber wenig Bewegung |
| 2-4% | Mittel | Standard-Turbos gut geeignet |
| 4-7% | Hoch | Weiter KO noetig, hoeheres Risiko |
| > 7% | Sehr hoch | Nur mit kleiner Position, weiter KO PFLICHT |

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

## 1.8 Makro-Faktoren

**Aktuelle Werte via Web-Suche:**
- Fed/Zinsen: [Aktueller Stand + naechstes Meeting Datum]
- USD (DXY): [Aktueller Wert] + [Trend: steigend/fallend]
- Inflation: [Letzter CPI Wert + Datum]
- Treasury 10Y: [Aktueller Yield]
- Geopolitik: [Aktuelle Konflikte/Events die relevant sind]

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
║  → Lies offene Positionen aus Supabase `portfolio` Tabelle   ║
║  → Bestimme Sektor-Konzentration                             ║
║  → Wenn >60% in einem Sektor: WARNUNG ausgeben!              ║
╚═══════════════════════════════════════════════════════════════╝
```

**Bestehende offene Positionen (aus Supabase):**

| Symbol | Sektor | Richtung | Groesse (EUR) |
|--------|--------|----------|---------------|
| [aus DB] | [Sektor] | LONG/SHORT | XXX EUR |
| [aus DB] | [Sektor] | LONG/SHORT | XXX EUR |

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
- ✅ Korrelations-Check gegen bestehende Positionen (PFLICHT!)
- ✅ Event-Kalender mit Earnings und Makro-Terminen

```
✅ [SCHRITT 1: DATENSAMMLUNG ABGESCHLOSSEN]
```
