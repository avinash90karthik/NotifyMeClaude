# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

Pre-Flight läuft vor Step 1 — `python3 preflight_check.py {{SYMBOL}}` aus Step 0. Die dort verlangte Checkliste MUSS vor § 1.1 verbatim mit Antworten erscheinen. Wenn der Pre-Flight nicht lief, STOPP und User informieren.

---

## 1.1 Portfolio Check

```bash
python3 prediction_db.py portfolio
```

Prüfe offene Positionen, Cash, Slots bevor du weitergehst.

## 1.2 Technical Data

```bash
python3 collect_data.py {{SYMBOL}}
```

Sammelt: Preis, RSI (delta/divergence/slope), MACD, ATR, ADX, Regime, SMA50/200, Short Interest, S/R, Earnings, Market Status.

Review Output. Flagge Auffälligkeiten (ATR erhöht, Divergenz, Regime-Wechsel).

## 1.3 Pre-Open Pattern Check

```bash
python3 -c "import json; d=json.load(open('memory/preopen_patterns.json')); print('IN DB' if '{{SYMBOL}}' in d.get('symbols',[]) else 'NOT IN DB')"
# Falls NOT IN DB:
python3 preopen_backtest.py --symbols {{SYMBOL}}
# Dann:
python3 preopen_check.py {{SYMBOL}} --entry-timing
```

Dokumentiere: Verdict, Hit-Rates, Gap-Fill %, bestes Entry-Timing.

## 1.4 Chart Analysis

```bash
source .env 2>/dev/null
SCRIPT="${CHART_SCRIPT:-}"
if [ -n "$SCRIPT" ]; then ${YFINANCE_VENV:-python3} $SCRIPT {{SYMBOL}}; fi
```

Fülle Chart-Tabelle: Trend, SMA 50/200 (Golden/Death Cross), RSI + Divergenz, Volumen, Pattern, Support, Resistance.

### Price-Action Reality Check (Rule 14, MANDATORY)

```bash
python3 price_action_check.py {{SYMBOL}}
```

Das Script gibt 5/10/20-Tage-Trend + Greens und einen Verdict aus. Regeln:

- Greens-in-10d < 5 → kein bestätigter Turn. MACD/RSI-Turn-Signale werden in der Confidence um -5% bis -10% abgewertet.
- 5-Tage-Trend ≤ 0 trotz positivem MACD = Stabilisierung, nicht Bounce. PREP-Phase, kein LONG-Trigger.
- Relative Schwäche ggü S&P am letzten Tag (Index up, Symbol down) als Warning notieren.

### Indicator Context Check (Rule 16, MANDATORY)

```bash
python3 indicator_context.py {{SYMBOL}} --expected-price <Close aus 1.2> --expected-date <letzter Handelstag>
```

Das Script:
- Rechnet RSI/BB-Position/Dist-3M-High auf 3 Jahre Historie für DIESE Aktie
- Reportet pro Band Sample-Size [SOLID n≥30 / WEAK 15-29 / THIN <15] und Fwd-5d Green-Rate
- Klassifiziert als TREND-STOCK oder Range-Stock
- Bricht mit Exit-Code 2 ab, wenn Historie >2 Handelstage alt ist oder der Close >0.5% divergiert (stale-data Schutz)

**Interpretation (PFLICHT):**

| Green-Rate fwd 5d | Signal | Confidence-Adjust (SOLID) |
|-------------------|--------|---------------------------|
| > 65% | Stark bullisch | LONG +3% / SHORT -3% |
| 55-65% | Mild bullisch | LONG +1% / SHORT -1% |
| 45-55% | Neutral | 0% (Indikator liefert kein Signal) |
| 35-45% | Mild bärisch | LONG -1% / SHORT +1% |
| < 35% | Stark bärisch | LONG -3% / SHORT +3% |

WEAK = halber Adjust. THIN = nur als Hinweis, kein Adjust.

### v9 Extrem-Oversold-Bonus (Rule 19, MANDATORY)

Wenn das aktuelle RSI-Band aus dem Script-Output die folgenden Bedingungen erfüllt, **addiere explizit** den Oversold-Bonus zur LONG-Confidence. Er überstimmt Regime-Abzüge.

| RSI-Band aktuell | Fwd-5d Green-Rate | Sample | LONG-Bonus |
|------------------|-------------------|--------|------------|
| < 20 | ≥ 65% | n ≥ 20 [SOLID] | **+5%** |
| < 15 | ≥ 70% | n ≥ 20 [SOLID] | **+8%** (Kapitulations-Tief) |

Beispiel-Lesung: `indicator_context.py` zeigt "RSI 16 | Fwd5 +4.2% green=75% [SOLID n=34]" → **+5% LONG-Bonus** pflichtmäßig in die Summe-Adjust-Tabelle unten einrechnen und im Judge zitieren.

**Begründung-Quelle:** Backtest 16.04.2026, 5/5 Predictions mit Conf <50% bei Extrem-Oversold gingen +8.82% in Signalrichtung. Das System hatte sie wegen TRENDING-Abzügen blockiert, aber die stock-eigene Fwd-Green-Rate dominiert historisch.

**Verbot:** Keine "Überkauft-Reflexe" ohne Script-Output. Sätze wie "RSI 72 ist überkauft → -5%" oder "BB >100% → Fade wahrscheinlich → -5%" sind ohne vorher zitierte Green-Rate Bias, nicht Analyse.

**Output-Tabelle in deiner Analyse:**

| Indikator | Aktuell | Band-n | Sample | Fwd-5d Avg | Green-Rate | Signal | Adjust |
|-----------|---------|--------|--------|-----------|------------|--------|--------|
| RSI | X | n=X | SOLID/WEAK/THIN | +X.X% | X% | ... | ±X% |
| BB-Position | X% | n=X | ... | ... | ... | ... | ±X% |
| Dist 3M-High | ±X% | n=X | ... | Break-Rate X% | — | ... | ±X% |
| Kombi (falls aktiv) | ... | n=X | ... | ... | ... | ... | ±X% |

Notiere Archetyp (TREND/Range) explizit — das ist die Begründung, warum Range-Abzüge (nicht) greifen.

## 1.5 News & Catalysts

Drei Quellen sind Pflicht:

1. **yfinance News** — steht schon im Pre-Flight-Output. Items der letzten 7 Tage in die News-Tabelle übernehmen.
2. **Web Search** — mind. 5 echte News-Items aus Reuters, Bloomberg, Seeking Alpha, sektorspezifisch. Ergänzt yfinance, ersetzt es nicht.
3. **Trump Truth Social / Tweet Search** — für JEDEN Ticker, nicht nur "sensitive" Sektoren. Query-Strings stehen im Pre-Flight-Banner. Trump-Post gefunden → Strategy-Regel "keine Overnight-Positionen" aktiv.

### Reddit Retail-Sentiment (MANDATORY)

```
site:reddit.com/r/wallstreetbets {{SYMBOL}}
site:reddit.com/r/wallstreetbetsGer {{SYMBOL}}
site:reddit.com/r/stocks {{SYMBOL}}
site:reddit.com/r/investing {{SYMBOL}}
```

Bei .DE/.F zusätzlich `r/mauerstrassenwetten`. Penny/Small-Cap zusätzlich `r/pennystocks`. Crypto-related zusätzlich `r/CryptoCurrency`.

Erfassen: Sentiment-Ton (Euphorie/Panik/Kapitulation/Fade/stille Akkumulation), YOLO-Flow, frische DD-Threads (letzte 7d), Trending-Indikatoren.

Rote Flaggen:
- Euphorie bei ATH → Kontra-Indikator (bearish)
- Put-YOLOs bei Oversold → Kontra-Indikator (bullish)
- Plötzlich viral bei unbekanntem Ticker → Pump-Risiko
- Stille bei fundamentalen News → Institutionelle dominieren

### Qualitäts-Check (Rule 15, Argumente lesen)

Demokratie ≠ Analyse. 70% bullish bei einem -30% Stock ist immer da (Dip-Buying-Psychologie). Wichtig ist die Qualität der Minderheitsargumente. Dokumentiere für jede Analyse:

1. Top 3 Bear-Argumente (bei LONG-Setup) — auch wenn Reddit 80% bullish ist
2. Top 3 Bull-Argumente (bei SHORT-Setup) — auch wenn Reddit bearish ist
3. Bewertung: HART (Fakten, Filings, Insider-Daten) oder WEICH (Meinung, Narrative, Targets)?
4. Wenn die Minderheit härtere Argumente hat → Kontra-Signal, unabhängig vom Count

News-Tabelle:

| # | Date | Headline / Thread | Impact | Source |
|---|------|-------------------|--------|--------|

**News Sentiment Index (NSI):** Pro Item 7 Achsen (-2 bis +2): Relevance, Sentiment, Price Impact, Trend, Earnings, Investor Confidence, Risk Profile. Durchschnitt bilden.

NSI > +1.0 = strongly bullish | -0.3 bis +0.3 = neutral | < -1.0 = strongly bearish.

**Retail-Sentiment-Flag** (separat): EUPHORIC / BULLISH / NEUTRAL / BEARISH / PANIC / QUIET. Bei EUPHORIC+ATH oder PANIC+Oversold → Kontra-Signal vermerken.

## 1.6 Macro Context

Via Web-Suche: VIX (< 15 calm, 15-25 normal, 25-35 elevated, > 35 fear), CNN Fear & Greed, Fed/Rates + nächstes Meeting, DXY, letzte CPI, 10Y-Yield, relevante Geopolitik, Polymarket-Odds für anstehende Events (falls applicable).

## 1.7 Correlation Check

Aus `prediction_db.py portfolio`: offene Positionen mit Sektoren listen. Prüfe:
- Gleicher Sektor wie {{SYMBOL}}? >60% Konzentration nach Trade = WARNING
- Gleiche Richtung (alle LONG)? Diversification Risk
- Korrelation mit Nasdaq/S&P?

## 1.8 Recent Day Pattern

```bash
python3 day_pattern.py {{SYMBOL}}
```

Tabelle:

| Pattern | Next Day | After 3d | After 5d |
|---------|----------|----------|----------|
| After similar day (n=X) | +X.X% (X% green) | +X.X% (X% green) | +X.X% (X% green) |
| After X red days streak (n=X) | +X.X% (X% green) | | |

Key Insight: [Was sagt das Pattern über die wahrscheinliche Richtung?]

## 1.8a Pattern Timeline (MANDATORY)

```bash
python3 pattern_timeline.py {{SYMBOL}}
```

Zwei Modi in einem Output:
- **Mode 1 (Similar-Day):** Fwd-Return-Verteilung für Day +1 bis +5 basierend auf Tagen mit ähnlichem heutigen Return (Klassifikation in 5 Return-Bänder, n meist >100).
- **Mode 2 (Analog-Match):** sucht historische 7-Tage-Fenster die matchen auf (Korrelation ≥0.7, RSI ±7, ATR-Regime 0.7-1.4). Skip wenn <10 Analoge.

Je Tag: Mean, ±1σ-Range, Green-Rate. Beide Modi parallel + AGREEMENT/DIVERGE-Check pro Tag.

**Interpretation:**
- **Beide Modi AGREE alle 5 Tage** → Forecast robust, kann als Confidence-Input gewertet werden.
- **DIVERGE ≥3 Tage** → Forecast-Unsicherheit. Signal-Confidence in Step 3 nicht über 60-63% treiben, auch wenn Scorecard höher ist.
- **Mode 2 SKIP** (Analoge <10) → kein Edge belegbar durch Pattern-Matching. Nur Mode 1 nutzen, als Hinweis nicht als Treiber.
- **±1σ-Range** ist der realistische Entry-Limit-Korridor. Wenn Day+1 Mean +0.5% aber Untergrenze −2%, darf Limit bei Close−1.5% gesetzt werden (P25-Zone).

**Output für Step 1 Stichpunkte:**
```
Pattern Timeline: <Mode1-Fwd5 +X.X% green X% / Mode2-Fwd5 +Y.Y% green Y% [n=Z]>
                  AGREEMENT|DIVERGE (Tage X/5)
                  Entry-Korridor morgen: ±1σ [ -X.X% .. +X.X% ] von Close
```

## 1.8b Earnings Window Pattern (MANDATORY)

```bash
python3 earnings_pattern.py {{SYMBOL}}
# Wenn Earnings ≤ 15 Tage UND LONG/SHORT Setup erwogen wird, ZUSÄTZLICH:
python3 earnings_pattern.py {{SYMBOL}} --trade-entry <T-N> --trade-exit <T-M> --same-month
#   T-N = heutiger Abstand in Handelstagen zu Earnings (Entry-Tag)
#   T-M = Exit-Abstand = typisch 1-3 (einen bis drei Tage vor Earnings raus)
#   --same-month hebt historische Quartale im selben Kalendermonat hervor
```

Script-Logik (zwei Modi):
- **Backward-Mode** (ohne --trade-entry): T-X→T0 Returns, beantwortet "wie weit weg war der Preis X Tage vor Earnings?". Nützlich für grobe Phase-Einordnung, **aber misst NICHT das Trade-Window.**
- **Trade-Window-Mode** (mit --trade-entry/--trade-exit): Interval-Return T-N→T-M, beantwortet "wenn ich heute rein und Tag vor Earnings raus — was ist historisch passiert?". Das ist die **primäre Metrik für unsere 1-5d Trade-Horizon.**

Sonstiges:
- Earnings > 30 Tage: Skip mit Hinweis (Standard-Day-Pattern aus § 1.8 reicht)
- Keine Earnings (Commodity/Index): sauber übersprungen

Wenn volle Analyse lief, Tabelle füllen (Backward-Mode T-5d/T-3d/T-1d/T+1d/T+3d/T+5d Avg/Green/n) UND separat Trade-Window-Return pro Quartal + Summary.

Nach dem Lauf zwingend dokumentieren:
1. Aktuelle Phase im Earnings-Fenster
2. Edge-Richtung aus Script-Output (Pre-Earnings-Drift / Post-Earnings / KEIN klares Muster)
3. **Trade-Window-Adjust (Primärquelle):** der vom Script ausgegebene Confidence-Adjust gilt — NICHT der Backward-Mode-WARNING-Abzug.
4. Same-Month-Hinweis: falls Script ≥3 Quartale im Zielmonat findet, als Validierungs-Signal werten; bei THIN (<3) nur als Richtungs-Hinweis.

Harte Regeln (v2 — Trade-Window-dominant):
- **Trade-Window Green-Rate ≥65% + Ø >+0.5%** → LONG +3% / SHORT -3%
- **Trade-Window Green-Rate 55-65% + Ø >0%** → LONG +1% / SHORT -1%
- **Trade-Window Green-Rate ≤45% + Ø <0%** → LONG -1% / SHORT +1%
- **Trade-Window Green-Rate ≤35% + Ø <-0.5%** → LONG -3% / SHORT +3% (WARNING bleibt)
- **Trade-Window n<8 (THIN)** → halbieren oder nur als Richtungs-Hinweis
- Backward-Mode-WARNING nur als **Sekundär-Signal** (Kontext, kein Auto-Abzug) wenn Trade-Window-Stats vorliegen

**Begründung für den v2-Wechsel (20.04.2026, HOOD):** Die ursprüngliche Regel nutzte T-5d→T0 Backward-Returns und zog pauschal -5% bei schwacher "Phase". Das misst aber **Drift zum Earnings-Day**, nicht den **Return über das gehaltene Trade-Interval**. Für HOOD (T-8): Backward-Stats zeigten 30% green T-5d→T0, real gehaltenes Interval T-8→T-3 zeigte 80% green + Ø +1.57%. Die beiden Metriken können gegensätzliche Signale geben — die Trade-Window-Metrik ist die korrekte für unseren 1-5d Horizon.

Earnings-Pattern overridet den Standard-Day-Pattern bei naher Earnings.

## 1.9 Event Calendar & Impact

Via Web-Suche: alle Events in den nächsten 1-7 Tagen.

| Date | Event | Impact | Relevance |
|------|-------|--------|-----------|

Wenn Earnings < 5 Handelstage → Flag für KO-Adjustment in Step 3.

### Event Impact Assessment (pro HOCH/SEHR HOCH Event)

**1. Klarheit oder Unsicherheit?**
Löst das Event Unsicherheit AUF (Katalysator) oder erzeugt es NEUE Unsicherheit (Risk-Off)?

| Event | Outcome A | Outcome B | Klarheit? |
|-------|-----------|-----------|-----------|

**2. Was sagen die Daten?**

```bash
python3 event_impact.py {{SYMBOL}}
```

Listet große Moves (>3%) der letzten 6 Monate mit Next-Day-Reaktion und Bounce-Rate nach Drops.

**3. Trade-Entscheidung:**
- Klarheit + Daten stützen Richtung → Trade VOR Event (Katalysator nutzen)
- Klarheit, Richtung unklar → Trade mit Stop-Management (Overnight-Regel)
- Neue Unsicherheit → WARTEN bis nach Event
- Beide Outcomes bullish → Event ist Chance, nicht Risiko

---

## Output für Step 1

Schließe Step 1 mit Stichpunkt-Zusammenfassung UND Rating-Block (kein JSON).

### Stichpunkte

```
Step 1:
- Preis/Regime: <Close, ATR%, RSI, MACD-State, ADX, Regime aus 1.2>
- Chart: <Trend, SMA-Konstellation, Pattern, Support, Resistance>
- Price-Action Reality: <Greens 10d + Verdict aus price_action_check>
- Indicator Context: <Archetyp + größtes Signal mit n/green-rate + Summe-Adjust>
- Pre-Open: <Verdict + beste Entry-Zeit>
- News: <NSI + 2-3 wichtigste Items + Trump-Flag>
- Reddit: <Sentiment-Flag + Minderheits-Argumentqualität>
- Macro: <VIX, F&G, Fed, relevante Makro-Events>
- Correlation: <Sektor-Konzentration, Portfolio-Clash-Flag>
- Day Pattern: <Similar-Day Fwd5 green-rate + Key Insight>
- Pattern Timeline: <Mode1/Mode2 Fwd5 + AGREEMENT/DIVERGE + Entry-Korridor>
- Earnings Window: <Skip / Phase / Warning / Edge>
- Events: <Haupt-Event, Klarheit/Unsicherheit, Trade-Decision>
```

### Ratings für Step 2 (PFLICHT — datengetrieben, kein Bauchgefühl)

Vier 0-10-Ratings, jedes mit Quellenzitat aus Step 1. Step 2 MUSS sie unverändert übernehmen (keine Rebewertung in der Debatte).

Mapping-Regel Green-Rate → Rating-Punkt (symmetrisch):

| Fwd-5d Green-Rate / Flag | LONG-Rating | SHORT-Rating |
|--------------------------|-------------|--------------|
| > 70% | 9 | 1 |
| 60-70% | 7 | 3 |
| 50-60% | 5 | 5 |
| 40-50% | 3 | 7 |
| < 40% | 1 | 9 |

Sample THIN (n<15) → Rating auf 5/5 kappen (kein Edge belegbar). Sample WEAK → max ±2 vom Neutralpunkt (also 3-7 Range).

**Rating 1 — Technical Green-Rate** (aus § 1.4 Indicator Context Tabelle Summe-Adjust + Archetyp):
```
Technical Green-Rate:  LONG X/10  |  SHORT X/10
  Quelle: <RSI-Band n=X green=X%, BB n=X green=X%, DistHigh Break-Rate X%, Archetyp=TREND|Range>
```

**Rating 2 — Price-Action Reality** (aus price_action_check.py Verdict + greens-10d):
```
Price-Action Reality:  LONG X/10  |  SHORT X/10
  Quelle: <Greens-10d=X/10, Trend-5d=±X%, Verdict="...">
  Regel: Greens<5/10 → LONG max 4; Greens>7/10 → SHORT max 3
```

**Rating 3 — News + Reddit Flow** (aus § 1.5 NSI + Retail-Flag + Trump + Argumentqualität):
```
News + Reddit Flow:  LONG X/10  |  SHORT X/10
  Quelle: <NSI=±X.X, Retail=FLAG, Trump-Hit=JA/NEIN, Minderheit-Argumentqualität: hart/weich>
  Regel: Trump-Hit → beide Ratings -2 (Unberechenbarkeit). Euphoric@ATH → LONG -2. Panic@Oversold → SHORT -2.
```

**Rating 4 — Event/Catalyst** (aus § 1.8b Earnings + § 1.9 Events, <7 Tage Horizont):
```
Event/Catalyst:  LONG X/10  |  SHORT X/10
  Quelle: <Haupt-Event/Earnings-Phase, Klarheit/Unsicherheit, Trade-Decision aus 1.9>
  Regel: WARTEN → beide 3/3. Trade-VOR-Event bullish → LONG 7-9, SHORT 1-3. Earnings-Warning → betroffene Richtung -2.
```

```
[STEP 1 COMPLETE]
```

Keine Beispiele zitieren, keine Regeln wiederholen — nur Resultate dieser Analyse.
