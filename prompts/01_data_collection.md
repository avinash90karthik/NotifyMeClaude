# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

---

## ⚠️ PRE-FLIGHT CHECKLIST — WIEDERKEHRENDE BLINDSTELLEN

> **STEP 0 — HARD-SCRIPT ERSETZT DIESE LISTE.**
> Führe **`python3 preflight_check.py {{SYMBOL}}`** als ALLERERSTEN Befehl aus.
> Das Script druckt: Datum, Wochentag, CET/NY-Zeit, Wochenend-Flag, US/EU-Markt-Status,
> Price Snapshot, yfinance News (letzte 7 Tage), MANDATORY Search Queries (Trump/Reddit/Day-News/Events).
>
> Die Checkliste unten MUSS danach verbatim in deinem Output erscheinen — mit Antworten.
> Jeder Punkt muss explizit beantwortet werden — NICHT überspringen, NICHT "mache ich gleich".
> Grund: Dieselben Fehler wiederholen sich. User hat mehrfach korrigieren müssen.

```bash
python3 preflight_check.py {{SYMBOL}}
```

### Checkliste (ALLE Punkte pflicht)

**[ ] 0. CLAUDE.md RECALL**
- CLAUDE.md kurz durchgehen — aktuellste Quick-Reference-Regeln (Gate, Exits, KO, Position Sizing, Hard Rules)
- Falls Regel geändert wurde seit letzter Analyse: neue Version verwenden, nicht alte

**[ ] 1. DATUM & WOCHENTAG**
- Python-Script aus § 1.0 ausführen — echtes Datum, Wochentag, CET+NY Zeit
- Falls Web-Suche später "Friday" oder "yesterday" findet: **gegen echtes Datum abgleichen**
- Falls Wochenende: US-Markt geschlossen, alle "heute" Events sind vom Freitag

**[ ] 2. TRUMP-POSTS**
- Web-Suche: `Trump Truth Social {{SYMBOL}}` (letzte 7 Tage)
- Web-Suche: `Trump {{SYMBOL}} tweet` (letzte 7 Tage)
- Besonders wenn Symbol in: Defense / AI / Energy / China-related / Pharma / Tariff-sensitive
- **Trump-Post gefunden? → Strategy-Regel "Trump-Events = keine Overnight-Positionen" aktivieren**
- Trump-Posts sind EVENT-KLASSE **UNBERECHENBAR** (1-5% Gap, Richtung unvorhersagbar)

**[ ] 3. REDDIT / RETAIL-FLOW**
- Pflicht-Subs durchsucht? (siehe § 1.5) — WSB, WSB-Ger, stocks, investing
- Retail-Sentiment-Flag gesetzt? (EUPHORIC/BULLISH/NEUTRAL/BEARISH/PANIC/QUIET)
- Kontra-Signal geprüft? (Retail euphoric bei ATH = bearish, Retail panic bei Oversold = bullish)

**[ ] 4. NEUTRALITÄT (keine Default-Richtung)**
- Keine Annahme in irgendeine Richtung — weder LONG, SHORT, noch NO-TRADE ist Default
- Daten sprechen, nicht Erwartungen (weder User noch eigene)
- "Zu spät einsteigen" / "R/R nicht perfekt" sind KEINE Gate-Gründe — nur Confidence <60% + Veto-Liste V1-V5
- Spiegel-Test: Würde ich bei **spiegelbildlichen Daten** dieselben Argumente gelten lassen? Wenn nein → Bias, nochmal prüfen

### Output der Checkliste

Produziere eine kurze Bestätigungszeile vor § 1.1:

```
PRE-FLIGHT: [Datum XX.XX.XXXX Wochentag] | Trump-Search: [JA/NEIN + Ergebnis] | Reddit-Subs: [durchsucht] | Bias-Check: [LONG/SHORT/NEUTRAL confirmed]
```

Erst DANN weiter mit § 1.0.

---

## 1.0 Datum & Wochentag (MANDATORY FIRST STEP)

Das wird jetzt von `preflight_check.py {{SYMBOL}}` erledigt (siehe Pre-Flight oben).
Falls der Pre-Flight nicht lief (z.B. manueller Lauf ohne Skill), hier der Fallback:

```bash
python3 preflight_check.py {{SYMBOL}}
```

**HARTE REGEL:** Bevor ein Event als "heute" oder "morgen" klassifiziert wird, IMMER gegen den Pre-Flight-Output prüfen. Wenn heute Samstag ist und ein CPI "am Freitag" stattfand → Event ist **gestern gewesen**, nicht "kommend". Wenn heute Montag 06:00 CET ist → letzter US-Handelstag war Freitag, nicht "heute".

**Fehlerquelle:** Web-Such-Ergebnisse zeigen oft "CPI Friday" ohne Jahr/Woche-Kontext — immer mit dem Pre-Flight-Datum abgleichen, NIE blind übernehmen.

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

### ⚠️ Price-Action Reality Check (MANDATORY)

**Bevor MACD/RSI-Turn-Signale als "bullisch" klassifiziert werden, prüfe gegen die ECHTE Kursbewegung:**

```python
python3 -c "
import yfinance as yf
t = yf.Ticker('{{SYMBOL}}')
h = t.history(period='2mo')
h['ret'] = h['Close'].pct_change() * 100
first = h['Close'].iloc[-20]; last = h['Close'].iloc[-1]
first10 = h['Close'].iloc[-10]; first5 = h['Close'].iloc[-5]
print(f'20-Tage Trend: {(last/first-1)*100:+.2f}%')
print(f'10-Tage Trend: {(last/first10-1)*100:+.2f}%')
print(f'5-Tage Trend:  {(last/first5-1)*100:+.2f}%')
greens20 = sum(1 for i in range(-20,0) if h['ret'].iloc[i] > 0)
greens10 = sum(1 for i in range(-10,0) if h['ret'].iloc[i] > 0)
greens5 = sum(1 for i in range(-5,0) if h['ret'].iloc[i] > 0)
print(f'Letzte 20d: {greens20} grün, {20-greens20} rot')
print(f'Letzte 10d: {greens10} grün, {10-greens10} rot')
print(f'Letzte 5d:  {greens5} grün, {5-greens5} rot')
"
```

**Reality-Check-Regel:**
- **MACD kann positiv drehen, ohne dass der Preis steigt** (durch abnehmende Abwärtsdynamik bei Range-Bound-Move). Das ist KEIN "klares Turn-Signal" — das ist **Stabilisierung auf niedrigem Level**.
- **Wenn 5-Tage-Trend flat oder negativ ist UND MACD positiv dreht** → "PREP phase", nicht "LONG triggered". Warte auf Bestätigung durch mindestens 2 grüne Tage in Folge.
- **Wenn Symbol relative Schwäche gegen S&P zeigt** (Index up, Symbol down) an einem Tag → **explizit als Warning vermerken**, nicht überlesen.
- **Grüne-Tage-Zähler** der letzten 10 Tage muss mindestens 5/10 sein, damit ein LONG-Signal "bestätigt" ist. Unter 4/10 grün = kein echter Turn.

**Output als Tabelle:**

| Window | Trend % | Grüne Tage | Reality-Check |
|--------|---------|------------|---------------|
| 20d | +X.X% | X/20 | Trend intakt? |
| 10d | +X.X% | X/10 | Bounce-Phase? |
| 5d | +X.X% | X/5 | Letzte Action |

**Wenn MACD/RSI-Turn-Signal im Widerspruch zu Price-Action-Reality steht: Signal als SCHWÄCHER werten und in Confidence-Berechnung -5% bis -10% einrechnen.**

### ⚠️ Indicator Context Check (MANDATORY — Historie schlägt Bauchgefühl)

> **Auslöser:** ENR.DE @ €167.22 am 11.04.2026 — Judge setzte Confidence auf 50% weil "BB>100% = überkauft" und "RSI steigend = bald überkauft". Historische Prüfung zeigte: ENR hat in 67% der Fälle bei BB>100% eine grüne Folge-Woche, und in 67% der Fälle bei RSI>70 ebenfalls. Der gesamte "überkauft"-Abzug war **empirisch falsch** für diesen Stock. Die Regel: **Bevor ein Indikator-Wert als "bullisch/bärisch" interpretiert wird, prüfe wie sich DIESER Stock historisch in DIESEM Band verhalten hat.**

**Kern-Prinzip:** RSI 70 ist bei einem Utility etwas anderes als bei einem Growth-Stock mit +200% YoY. "Überkauft" ist eine **Range-Stock-Heuristik** und kann bei Trend-Stocks systematisch falsch-negativ sein. Die einzige valide Antwort ist: **prüf die Verteilung**.

**Pflicht-Prüfung** — ein einziger Python-Block, der für vier Indikatoren historische Fwd-5d-Verteilungen zieht:

**Wichtig:** Setze `EXPECTED_PRICE` auf den aktuellen Close aus `collect_data.py` und `EXPECTED_DATE` auf den letzten Handelstag. Das Script STOPPT wenn History-Daten >2 Handelstage alt sind oder der Preis >0.5% abweicht — das verhindert einen stillen yfinance-Cache-Hickup, der die Analyse mit veralteten Werten füttern würde.

```python
python3 << 'PYEOF'
import yfinance as yf
import numpy as np
import sys
from datetime import date

# GROUND TRUTH aus Step 1.2 (collect_data.py) — bevor du das Script ausführst, hier einfüllen
EXPECTED_PRICE = 0.00  # <-- aus collect_data.py JSON "price_native"
EXPECTED_DATE  = "YYYY-MM-DD"  # <-- letzter Handelstag aus preflight_check.py

t = yf.Ticker('{{SYMBOL}}')
h = t.history(period='3y')

# Sanity check: History muss zum aktuellen Close passen
last_date = h.index[-1].date()
last_close = float(h['Close'].iloc[-1])
expected_d = date.fromisoformat(EXPECTED_DATE) if EXPECTED_DATE != "YYYY-MM-DD" else None

if expected_d:
    day_gap = abs((last_date - expected_d).days)
    if day_gap > 4:  # >2 Handelstage inkl. Wochenende
        print(f"❌ ABORT: History endet {last_date}, erwartet {EXPECTED_DATE} (Diff {day_gap}d)")
        print(f"   yfinance-Cache oder -Delay. STOPP — Analyse nicht auf stale data fortsetzen.")
        sys.exit(2)

if EXPECTED_PRICE > 0:
    pct_diff = abs(last_close / EXPECTED_PRICE - 1) * 100
    if pct_diff > 0.5:
        print(f"❌ ABORT: History-Close {last_close:.2f} vs erwartet {EXPECTED_PRICE:.2f} ({pct_diff:.2f}% Diff)")
        print(f"   Datenquelle inkonsistent. STOPP.")
        sys.exit(2)

print(f"✓ Sanity OK: letztes History-Datum {last_date}, Close €{last_close:.2f}")
print()

# Wilder RSI (konsistent mit indicators.py — nicht .rolling() verwenden!)
delta = h['Close'].diff()
gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
h['RSI'] = 100 - (100 / (1 + gain/loss))

# Bollinger Position (0 = lower band, 100 = upper band, >100 = breach)
h['SMA20'] = h['Close'].rolling(20).mean()
h['STD20'] = h['Close'].rolling(20).std()
h['BB_POS'] = (h['Close'] - (h['SMA20'] - 2*h['STD20'])) / (4*h['STD20']) * 100

# Distance to 3M rolling high
h['high_3m'] = h['Close'].rolling(60).max()
h['dist_high'] = (h['Close'] / h['high_3m'] - 1) * 100

# Forward returns (für historische Statistik)
for d in [1, 3, 5, 10]:
    h[f'fwd_{d}d'] = h['Close'].pct_change(d).shift(-d) * 100

# WICHTIG: "now" ist der AKTUELLE Zustand (letzte Zeile VOR dropna),
# nicht der letzte Zeile nach dropna. Sonst zeigt "now" auf 10 Tage vor heute,
# weil fwd_10d für die letzten 10 Handelstage NaN ist.
now = h.iloc[-1].copy()
h_hist = h.dropna(subset=['RSI','BB_POS','dist_high','fwd_5d','fwd_10d'])
print(f"AKTUELL (letzter Handelstag {h.index[-1].date()}): RSI {now['RSI']:.1f} | BB-Pos {now['BB_POS']:.1f}% | DistHigh {now['dist_high']:+.2f}%")
print(f"Historie für Band-Statistik: {len(h_hist)} Tage ({h_hist.index[0].date()} bis {h_hist.index[-1].date()})")
print()

def report(name, subset, total):
    n = len(subset)
    if n == 0:
        print(f"  {name}: n=0 — keine Historie")
        return
    tag = "SOLID" if n >= 30 else ("WEAK" if n >= 15 else "THIN")
    fwd5 = subset['fwd_5d'].dropna()
    if len(fwd5) == 0:
        print(f"  {name}: n={n} [{tag}] — keine fwd-Daten")
        return
    green_rate = (fwd5 > 0).mean() * 100
    avg = fwd5.mean()
    med = fwd5.median()
    print(f"  {name}: n={n} [{tag}] ({n/total*100:.0f}% der Zeit) | fwd 5d avg {avg:+.2f}% | median {med:+.2f}% | green {green_rate:.0f}%")

# Band-Statistiken IMMER aus h_hist (die hat valide fwd-Returns).
# "now" kommt aus h (letzte verfügbare Zeile, auch wenn fwd_10d dort NaN ist).
total = len(h_hist)

# 1. RSI-Band um aktuellen Wert (±5)
print("== 1. RSI-BAND (aktueller Wert ±5) ==")
rsi_now = now['RSI']
band = h_hist[(h_hist['RSI'] >= rsi_now - 5) & (h_hist['RSI'] <= rsi_now + 5)]
report(f"RSI {rsi_now-5:.0f}-{rsi_now+5:.0f}", band, total)
if rsi_now >= 60:
    report("RSI >70 (klassisch überkauft)", h_hist[h_hist['RSI'] > 70], total)
if rsi_now <= 40:
    report("RSI <30 (klassisch überverkauft)", h_hist[h_hist['RSI'] < 30], total)
print()

# 2. Bollinger-Position-Bucket
print("== 2. BOLLINGER POSITION ==")
bb_now = now['BB_POS']
if bb_now > 100:
    report("BB >100% (oberer Band durchbrochen)", h_hist[h_hist['BB_POS'] > 100], total)
elif bb_now > 70:
    report("BB 70-100% (oberes Drittel)", h_hist[(h_hist['BB_POS'] > 70) & (h_hist['BB_POS'] <= 100)], total)
elif bb_now < 0:
    report("BB <0% (unterer Band durchbrochen)", h_hist[h_hist['BB_POS'] < 0], total)
elif bb_now < 30:
    report("BB 0-30% (unteres Drittel)", h_hist[(h_hist['BB_POS'] >= 0) & (h_hist['BB_POS'] < 30)], total)
else:
    report("BB 30-70% (Mitte)", h_hist[(h_hist['BB_POS'] >= 30) & (h_hist['BB_POS'] <= 70)], total)
print()

# 3. Distanz zu 3M-High (Resistance-Nähe)
print("== 3. DISTANZ ZU 3M-HIGH ==")
d_now = now['dist_high']
if d_now > -3:
    near = h_hist[h_hist['dist_high'] > -3]
    report("Innerhalb 3% vom 3M-High", near, total)
    broken = 0
    n_checked = 0
    for i in range(len(h_hist) - 10):
        if h_hist['dist_high'].iloc[i] > -3:
            n_checked += 1
            if (h_hist['Close'].iloc[i+1:i+11] > h_hist['high_3m'].iloc[i]).any():
                broken += 1
    if n_checked > 0:
        br = broken / n_checked * 100
        tag = "SOLID" if n_checked >= 30 else ("WEAK" if n_checked >= 15 else "THIN")
        print(f"  Break-Rate 3M-High in 10d: {br:.0f}% (n={n_checked}) [{tag}]")
elif d_now < -15:
    far = h_hist[h_hist['dist_high'] < -15]
    report("Mehr als -15% vom 3M-High (tiefer Drawdown)", far, total)
else:
    mid = h_hist[(h_hist['dist_high'] >= -15) & (h_hist['dist_high'] <= -3)]
    report(f"Zwischen -15% und -3% vom 3M-High", mid, total)
print()

# 4. Kombi-Check
print("== 4. KOMBI ==")
if rsi_now >= 60 and bb_now > 100:
    report("RSI >=60 UND BB >100%", h_hist[(h_hist['RSI'] >= 60) & (h_hist['BB_POS'] > 100)], total)
elif rsi_now <= 40 and bb_now < 30:
    report("RSI <=40 UND BB <30%", h_hist[(h_hist['RSI'] <= 40) & (h_hist['BB_POS'] < 30)], total)
else:
    print("  (keine Extrem-Kombi aktiv — Kombi-Check übersprungen)")
print()

# 5. Archetyp-Klassifikation (aus h, nicht h_hist — wir wollen den heutigen Zustand)
print("== 5. ARCHETYP ==")
sma200 = h['Close'].rolling(200).mean().iloc[-1]
dist_sma200 = (now['Close'] / sma200 - 1) * 100
max_dd_1y = 0
h1y = h.tail(252)
for i in range(len(h1y)):
    peak = h1y['Close'].iloc[:i+1].max()
    dd = (h1y['Close'].iloc[i] / peak - 1) * 100
    if dd < max_dd_1y:
        max_dd_1y = dd
gain_1y = (h.iloc[-1]['Close'] / h.iloc[-252]['Close'] - 1) * 100 if len(h) >= 252 else None
print(f"  Dist SMA200: {dist_sma200:+.1f}% | 1Y-Gain: {gain_1y:+.1f}% | Max-DD 1Y: {max_dd_1y:.1f}%")
is_trend = (dist_sma200 > 20 and gain_1y and gain_1y > 100 and max_dd_1y > -25)
print(f"  Klassifikation: {'TREND-STOCK (Range-Heuristiken sind hier historisch falsch-negativ)' if is_trend else 'Range-/Normal-Stock (Range-Heuristiken anwendbar)'}")
PYEOF
```

**Interpretation der Ausgabe (PFLICHT — diese Schritte durchgehen, nicht überfliegen):**

**Schritt 1: Sample-Size-Qualität**
- `[SOLID]` (n ≥ 30): Belastbar, direkt als Confidence-Input verwenden
- `[WEAK]` (n = 15-29): Richtung nennen, aber schwächer gewichten (halber Adjust)
- `[THIN]` (n < 15): Nur als "Hinweis" erwähnen, **kein Confidence-Adjust ableiten**
- LLM-Urteil darf Sample-Grenzen leicht verschieben (z.B. n=13 bei sehr klarer Richtung 85/15% ist interpretierbar — benutze Kontext)

**Schritt 2: Richtung aus Green-Rate ableiten (symmetrisch für beide Seiten)**

| Green-Rate fwd 5d | Signal-Richtung | Confidence-Adjustment (bei SOLID) |
|-------------------|-----------------|-----------------------------------|
| **> 65%** | Stark bullisch | LONG +3%, SHORT -3% |
| **55-65%** | Mild bullisch | LONG +1%, SHORT -1% |
| **45-55%** | **Neutral (Coin-Flip)** | **0% — dieser Indikator liefert hier kein Signal** |
| **35-45%** | Mild bärisch | LONG -1%, SHORT +1% |
| **< 35%** | Stark bärisch | LONG -3%, SHORT +3% |

Bei `[WEAK]` Samples: **halben Adjust verwenden** (3% → 1.5%, 1% → 0.5%).

**Schritt 3: Das "Überkauft-Reflex"-Verbot**

Du darfst **NICHT** schreiben:
- ❌ "RSI 72 ist überkauft → -5% Confidence"
- ❌ "BB-Position >100% → Fade wahrscheinlich → -5%"
- ❌ "Preis 2% unter ATH → kaum Luft → -5%"

Ohne vorher das Script oben gelaufen zu sein und die Green-Rate **konkret zitiert** zu haben. Range-Reflexe ohne historische Belegung sind ab jetzt **Bias**, nicht Analyse.

**Was du stattdessen schreibst:**
> "RSI 62.3 [aktueller Wert] — in den letzten 3 Jahren war ENR in diesem Band (57-67) an 90/733 Tagen [12%], fwd 5d avg +0.64%, Green-Rate 59% → mild bullisch (+1%)."
>
> "BB-Position 103% — n=60 [SOLID], fwd 5d avg +3.50%, Green-Rate 73% → stark bullisch (+3%). Range-Reflex 'überkauft = fällt' ist für diesen Stock empirisch falsch."

**Schritt 4: Archetyp-Klassifikation dokumentieren**

Das Script druckt am Ende "TREND-STOCK" oder "Range-/Normal-Stock". Notiere das explizit in der Analyse — es ist die Begründung, warum bestimmte Abzüge (nicht) greifen. Kriterien: SMA200-Abstand > +20%, 1Y-Gain > +100%, Max-DD 1Y > -25%.

**Output als Tabelle (in Step 1 Analyse):**

| Indikator | Aktuell | Band-n | Sample | Fwd-5d Avg | Green-Rate | Signal | Adjust |
|-----------|---------|--------|--------|-----------|------------|--------|--------|
| RSI | XX.X | n=XX | SOLID/WEAK/THIN | +X.XX% | XX% | bullisch/neutral/bearish | ±X% |
| BB-Position | XX.X% | n=XX | ... | +X.XX% | XX% | ... | ±X% |
| Dist 3M-High | ±X.X% | n=XX | ... | Break-Rate XX% | — | ... | ±X% |
| Kombi (falls sinnvoll) | ... | n=XX | ... | ... | ... | ... | ±X% |

**Archetyp:** TREND-STOCK / Range-Stock / Normal
**Summe Indikator-Adjustments für Step 3:** ±X%

---

## 1.5 News & Catalysts

**Inputs (alle drei Quellen pflicht):**

1. **yfinance news** — bereits aus `preflight_check.py` gezogen, siehe Pre-Flight-Output. Alle Items der letzten 7 Tage in die Tabelle unten übernehmen.
2. **Web search for 5+ real news items** — Reuters, Bloomberg, Seeking Alpha, sector-specific. Must complement (not replace) yfinance feed.
3. **Trump Truth Social / Tweet search** — MANDATORY für JEDEN Ticker, nicht nur "sensitive" Sektoren. Query-Strings stehen im Pre-Flight-Banner. Ein Trump-Post = Strategy-Regel "Trump-Events = keine Overnight-Positionen" aktiv.

**MANDATORY — Retail-Sentiment via Reddit** (zusätzlich zu klassischen News):

Immer mindestens eine Web-Suche gegen Reddit ausführen, um Retail-Positionierung + Memeflow zu erfassen:

```
site:reddit.com/r/wallstreetbets {{SYMBOL}}
site:reddit.com/r/wallstreetbetsGer {{SYMBOL}}
site:reddit.com/r/stocks {{SYMBOL}}
site:reddit.com/r/investing {{SYMBOL}}
```

Bei deutschen Werten (.DE, .F) zusätzlich `r/mauerstrassenwetten`. Bei Penny/Small-Caps zusätzlich `r/pennystocks`. Bei Crypto-related `r/CryptoCurrency`.

**Was suchen:**
- Sentiment-Ton (Euphorie / Panik / Kapitulation / Fade / stille Akkumulation)
- Call/Put-Flow-Posts (YOLO-Positionen, Gamma-Squeeze-Threads)
- Frische DD-Threads (letzte 7 Tage)
- Trending-Indikatoren (in Top-Posts? Daily Discussion erwähnt?)

**Rote Flaggen:**
- Euphorie bei ATH → Kontra-Indikator (bearish)
- Massive Put-YOLOs bei Oversold → Kontra-Indikator (bullish)
- Plötzlich viral bei unbekanntem Ticker → Pump-Risiko
- Stille bei fundamentalen News → Institutionelle dominieren, Retail noch nicht drin

**🔍 QUALITÄTS-CHECK — Argumente lesen, nicht nur zählen:**

Demokratie ≠ Analyse. 70% bullish bei einem -30% Stock ist **immer** der Fall (dip-buying Psychologie). Wichtiger als das Count ist die **Qualität der Bear-Argumente** (bei LONG-Setup) bzw. **Bull-Argumente** (bei SHORT-Setup) der Minderheit.

Explizit für JEDE Analyse dokumentieren:
1. **Top 3 Bear-Argumente aus Reddit** (hart, faktisch, nicht Meinung) — auch wenn Reddit 80% bullish ist
2. **Top 3 Bull-Argumente aus Reddit** — auch wenn Reddit bearish ist
3. **Bewertung:** Sind die Minderheits-Argumente HARTER (Fakten, Filings, Insider-Daten) oder WEICHER (Meinung, Narrative, Hoffnung) als die Mehrheit?
4. **Wenn die Minderheit härtere Argumente hat → das ist ein Kontra-Signal, unabhängig vom Count**

Beispiel (MSFT April 2026): Reddit 77/100 bullish, aber Bear-Argumente = CapEx $110B run-rate, FCF collapsed auf $5.9B, Insider-Selling 31 netto-negativ, Copilot nur 3% Penetration. **Das sind harte Fakten.** Bull-Argumente = "Analyst Target $587" (Meinung), "$625B RPO" (Zahl, aber 45% davon ist OpenAI-Klumpenrisiko). **Die Bears haben hier die härteren Argumente**, obwohl sie in der Minderheit sind.

Für jede News-Zeile inkl. Reddit:

| # | Date | Headline / Thread | Impact | Source |
|---|------|-------------------|--------|--------|
| 1 | DD.MM | [headline oder r/sub: titel] | Positive/Negative/Neutral | [source/sub] |

**News Sentiment Index (NSI):** Rate each on 7 axes (-2 to +2): Relevance, Sentiment, Price Impact, Trend, Earnings, Investor Confidence, Risk Profile. Calculate average.

**Retail-Sentiment-Flag** (separat zu NSI, als Kontext):
- `EUPHORIC` / `BULLISH` / `NEUTRAL` / `BEARISH` / `PANIC` / `QUIET`
- Bei EUPHORIC+ATH oder PANIC+Oversold → Kontra-Signal vermerken

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

## 1.8b Earnings Window Pattern (MANDATORY — Auto-Conditional)

**Pflicht-Lauf bei JEDER Analyse.** Das Script entscheidet selbst, ob eine volle Pattern-Analyse nötig ist:

```bash
python3 earnings_pattern.py {{SYMBOL}}
```

**Script-Logik:**
- **Earnings <= 30 Tage:** Volle Pattern-Analyse (letzte 10 Earnings, T-5d bis T+5d Stats, Interpretation, Warning)
- **Earnings > 30 Tage:** Skip mit Hinweis (Standard Day-Pattern aus § 1.8 reicht)
- **Keine Earnings (Commodity/Index):** Sauber übersprungen

**Wenn volle Analyse lief, dokumentiere in der Analyse:**

| Phase | Avg % | Green Rate | n |
|-------|-------|------------|---|
| T-5d | +X.X% | XX% | X |
| T-3d | +X.X% | XX% | X |
| T-1d | +X.X% | XX% | X |
| T+1d | +X.X% | XX% | X |
| T+3d | +X.X% | XX% | X |
| T+5d | +X.X% | XX% | X |

**Kritische Fragen nach dem Lauf:**

1. **Aktuelle Phase:** Wo liegt unser Trade im Earnings-Fenster? (Das Script gibt die Phase aus)
2. **Edge-Richtung:** Script sagt "EDGE: Pre-Earnings-Drift" / "EDGE: Post-Earnings" / "EDGE: KEIN klares Muster"
3. **Aktuelle Phase-Warning:** Wenn Script "WARNING: Aktuelle Phase historisch SCHWACH" ausgibt → **-5% Confidence-Abzug im Judge**

**HARTE REGEL:**
- **Wenn Script WARNING gibt und Trade-Richtung gegen die historische Tendenz läuft → Confidence-Abzug -5% MINIMUM, pflichtmässig**
- **Wenn Script "KEIN klares Muster" sagt → kein Abzug, aber auch kein Earnings-Bonus**
- **Wenn Script "EDGE: Pre-Earnings-Drift" gibt und LONG geplant + aktuelle Phase passt → +3% Confidence**

**WICHTIG:** Earnings-Pattern OVERRIDE't den Standard-Day-Pattern-Edge. Bei naher Earnings zählt das Earnings-Fenster-Muster stärker als das generische RSI<35-Pattern.

## 1.9 Event Calendar & Impact Analysis

**Via web search: Find ALL events in the next 1-7 days.**

| Date | Event | Impact | Relevance |
|------|-------|--------|-----------|
| [dates] | [events] | [impact level] | [direct/macro/sector] |

If earnings < 5 trading days: flag for KO adjustment in Step 3.

### Event Impact Assessment (MANDATORY for each major event)

For each event with impact HOCH or SEHR HOCH, answer:

**1. Klarheit oder Unsicherheit?**
Does this event RESOLVE uncertainty (= Klarheit → Katalysator) or CREATE MORE uncertainty (= neue Unsicherheit → Risk-Off)?

| Event | Outcome A | Outcome B | Klarheit? |
|-------|-----------|-----------|-----------|
| [event] | [scenario A + market impact] | [scenario B + market impact] | JA/NEIN |

**2. Was sagen die Daten?**
How has {{SYMBOL}} reacted to similar events historically? Run:

```python
python3 -c "
import yfinance as yf
t = yf.Ticker('{{SYMBOL}}')
h = t.history(period='6mo')
h['ret'] = h['Close'].pct_change() * 100
# Show behavior around event dates and big move days
big = h[h['ret'].abs() > 3]
print('=== BIG MOVES (>3%) ===')
for i in range(len(big)):
    idx = big.index[i]
    pos = h.index.get_loc(idx)
    r = big['ret'].iloc[i]
    d = idx.strftime('%d.%m')
    nxt = h['ret'].iloc[pos+1] if pos+1 < len(h) else float('nan')
    print(f'  {d}: {r:+.2f}% → next day: {nxt:+.2f}%')
bounce = sum(1 for i in range(len(big)) if h.index.get_loc(big.index[i])+1 < len(h) and h['ret'].iloc[h.index.get_loc(big.index[i])+1] > 0)
print(f'Bounce rate after big drops: {bounce}/{len(big)}')
"
```

**3. Entscheidung für den Trade:**
- Event bringt Klarheit + Daten stützen Richtung → **Trade VOR Event** (profitiere vom Katalysator)
- Event bringt Klarheit aber Richtung unklar → **Trade mit Stop-Management** (Overnight-Regel)
- Event bringt MEHR Unsicherheit → **WARTEN bis nach Event**
- Beide Outcomes bullish für Symbol → **Event ist kein Risiko, sondern Chance**

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
  "retail_sentiment": "EUPHORIC|BULLISH|NEUTRAL|BEARISH|PANIC|QUIET",
  "retail_contra_signal": "",
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
  "events": [],
  "event_impact": {
    "main_event": "",
    "klarheit_or_unsicherheit": "KLARHEIT|UNSICHERHEIT",
    "outcome_a": "",
    "outcome_b": "",
    "both_outcomes_bullish": false,
    "data_supports": "",
    "trade_decision": "TRADE_VOR_EVENT|TRADE_MIT_STOP|WARTEN"
  }
}
```

```
[STEP 1 COMPLETE]
```
