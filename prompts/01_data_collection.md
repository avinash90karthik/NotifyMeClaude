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
