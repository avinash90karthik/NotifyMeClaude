# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}

**Input:** Data (Step 1) + Debate (Step 2) + Chart.

---

## Judge Verdict

Analyze INDEPENDENTLY from Bull/Bear. Use the chart as your own source.

| Factor | Assessment | Weight |
|--------|------------|--------|
| Bull strength (/10) | [top 2 arguments] | |
| Bear strength (/10) | [top 2 arguments] | |
| Chart signal | [what YOU see] | |
| RSI divergence | [bullish/bearish/none + strength] | |
| **Indicator Context (Step 1 § 1.4)** | **[Archetyp + Summe der Adjustments + kurze Begründung]** | |
| NSI (from Step 1) | [value + classification] | |
| Regime | [from Step 1] | |
| Short interest | [squeeze potential?] | |
| Pre-open pattern | [confirms/contradicts?] | |
| Retail sentiment (Reddit) | [EUPHORIC/PANIC/etc. + Kontra-Signal?] | |

**Pflicht:** Der Judge muss die Indicator-Context-Tabelle aus Step 1 wörtlich zitieren (RSI-Band n, Green-Rate, BB-Band n, Green-Rate, Distance-High Break-Rate) bevor Confidence-Adjustments berechnet werden. Wenn Step 1 das Script nicht gelaufen ist oder die Tabelle fehlt, **STOPP und zurück zu Step 1** — nicht improvisieren.

### Confidence Adjustments

**⚠️ Indicator-Adjustments kommen aus Step 1 § 1.4 "Indicator Context Check"** — nicht aus Bauchgefühl. Der Judge übernimmt die Tabelle 1:1 aus Step 1 und addiert sie zu den Regime-/Pattern-Adjustments unten. **Niemals** einen Indikator-Abzug schreiben wie "RSI 72 → überkauft → -5%", ohne dass die historische Green-Rate in Step 1 das bestätigt. Wenn die Green-Rate im aktuellen Band >55% ist, hat "überkauft" **kein Recht auf einen Abzug**, egal wie sehr das Bauchgefühl dagegen schreit.

| Condition | Adjustment |
|-----------|------------|
| **Indicator-Context-Summe aus Step 1** | **±X% (übernehmen)** |
| TRENDING + signal WITH trend | +5% |
| TRENDING + signal AGAINST trend (no confirming signals) | -10% |
| TRENDING + AGAINST trend + 1 confirming (RSI div OR MACD cross) | -5% |
| TRENDING + AGAINST trend + 2+ confirming (div + MACD + SMA50) | -3% |
| RANGE + signal at S/R level | +3% |
| CHOPPY | -5% to -10% |
| Pre-open pattern hit >=60% same direction | +3% |
| Pre-open pattern hit <50% | -5% |
| Reflection: win rate for bracket <30% | -5% |
| Retail EUPHORIC bei ATH + LONG-Signal | -5% (Kontra, Positioning) |
| Retail PANIC bei Oversold + LONG-Signal | +3% (Kontra) |
| Retail EUPHORIC bei ATH + SHORT-Signal | +3% (Kontra) |

**Doppelzählung vermeiden:**
- "Retail EUPHORIC" ist Positioning-basiert, "überkauft" ist Technik — getrennt halten, **aber nicht beide gleichzeitig** anwenden wenn sie dieselbe Logik abbilden. Bei einem Trend-Stock mit hoher Green-Rate bei RSI>70 gilt nur der Positioning-Abzug, der Technik-Abzug fällt weg (Step 1 sagt "neutral" oder "+").
- Wenn Step 1 sagt "BB>100% = +3% LONG" und du zusätzlich "Trend-Stock → LONG with trend = +5%" rechnest, achte darauf dass die beiden nicht doppelt den gleichen Effekt einpreisen. Die Trend-Adjustments oben gelten für **Regime-Analyse** (ADX, Score), nicht für "Trend-Stock"-Archetyp.

### Decision

| Horizon | Signal | Confidence |
|---------|--------|------------|
| Short-term (1-5d) | LONG/SHORT/HOLD | XX% |
| Medium-term (2-8w) | LONG/SHORT/HOLD | XX% |
| Long-term (3m+) | LONG/SHORT/HOLD | XX% |

**TRADE SIGNAL = short-term (1-5d) verdict ONLY. This drives turbo entry/exit.**

**⛔ HORIZON-REGEL (hart):**
- Der einzige relevante Zeitraum ist **1-5 Tage**. Alles darüber ist Kontext, nie Trade-Empfehlung.
- Wenn 1-5d kein Edge zeigt → **Signal = NO-TRADE**.
- VERBOTEN als Empfehlung: "Setup aktiv ab Datum X", "wiederkommen in Y Wochen", "warten bis T-7 pre-earnings". Solche Patterns sind RISIKO-Warnungen oder Watchlist-Trigger, niemals Trade-Trigger.
- Medium/Long-term Zeilen oben sind reiner Kontext — sie überschreiben niemals das 1-5d-Signal.

**Reasoning:** [2-3 sentences including chart + divergence]

### ⚠️ NEUTRALITÄTS-CHECK (mandatory vor finalem Signal)

Das Signal folgt den DATEN — nicht einer Default-Richtung, nicht meiner Erwartung, nicht der User-Erwartung.

**Spiegel-Test gegen eigene Verzerrungen:**
- Würde ich bei **spiegelbildlichen Daten** (RSI 90 statt 10, +17% statt -17%, bullische statt bearische News) **dieselben** Argumente gelten lassen? Wenn ich z.B. "zu spät einsteigen" als LONG-Veto nutzen würde, muss ich es auch als SHORT-Veto anwenden. Asymmetrische Argumente = Bias.
- Würde ich genauso argumentieren, wenn der User explizit das **Gegenteil** erwartet hätte? Wenn mein Verdict sich nur wegen User-Erwartung ändern würde → Bias.

**Gate vs. Rationalisierung — klar trennen:**
- Gate = **Confidence <60%** (einzige harte NO-TRADE-Regel)
- Gate = **Veto-Liste V1-V5** (ATR, Regime+Score, Slots, Sektor, Drawdown)
- KEIN Gate: "R/R nicht perfekt", "spätes Einsteigen", "Counter-Trend ungemütlich", "Event in X Tagen"
  → Das sind Trade-Plan-Justierungen (kleinere Size, engere Targets, kürzere Haltedauer), keine Signal-Vetos.

**Verdict-Regel:**
- Daten sprechen → Signal folgt den Daten, egal ob LONG/SHORT/NO-TRADE
- Scorecard ist ein **Input**, nicht ein Default. Wenn Scorecard SHORT 36 sagt aber Judge-Faktoren LONG 60% zeigen → LONG, mit Begründung warum Scorecard überstimmt wurde
- NO-TRADE ist nur bei echter Gate-Verletzung (Confidence <60%, V-Veto aktiv). Nicht "aus Vorsicht", nicht "zu unsicher"

Wenn nach diesem Check Zweifel bestehen: **Dokumentiere den Zweifel, aber entscheide trotzdem**. Unentschiedenheit ist auch eine Form von Bias (Vorsichts-Bias).

---

## KO Level Calculation

**Always: KO = whichever is FURTHER from price (ATR-based or chart-based)**

### A: ATR-based KO

| Asset Class | Multiplier | Criteria |
|-------------|-----------|----------|
| Large Cap | 2.0x ATR | Market cap > $50B |
| Mid/Small Cap | 2.5x ATR | Market cap < $50B |
| Commodities | 3.0x ATR | Futures (=F suffix) |
| Crypto-related | 3.0x ATR | BTC/crypto exposure |

ATR(14) from Step 1: $XX.XX (X.X%)
ATR-KO (LONG): Price - (ATR x multiplier) = **$XX.XX**
ATR-KO (SHORT): Price + (ATR x multiplier) = **$XX.XX**

If ATR5/ATR14 > 1.5: increase multiplier by +0.5
If earnings < 5 days: increase multiplier by +0.5

### B: Chart-based KO

Identify strongest support (LONG) or resistance (SHORT) from Step 1.
Chart-KO: Below strongest support + 0.5-1% buffer = **$XX.XX**

### C: Final KO

| Method | Level | Distance from price |
|--------|-------|-------------------|
| ATR-based | $XX.XX | XX.X% |
| Chart-based | $XX.XX | XX.X% |
| **FINAL KO** | **$XX.XX** | **XX.X%** |

---

## Trade Plan

**Entry:** $XX.XX | **KO:** $XX.XX | **Stop (mental, above KO):** $XX.XX

**Exits (v5):**
| Cert level | Action | Portion |
|------------|--------|---------|
| +20% | SELL immediately | 50% |
| +30% | Trail stop to +15% | hold |
| +40% | Trail stop to +25% | hold |
| +50% | Trail stop to +35% | rest |

**Time stops:** 3 days <5% profit halve | 5 days sideways exit | Earnings <2 days secure 50%

**Expected duration:** [1-3d momentum / 2-4d pullback / 1-2d event] If >5d: warn about turbo suitability.

---

## Optimal Entry (DATENGETRIEBEN — kein Market Buy ohne Begründung!)

**Regel:** Bei Turbos wirkt jeder Prozent am Entry mit dem vollen Hebel. Ein 2% besserer Einstieg = 20% mehr Gewinn bei 10x Hebel. IMMER Limit-Order bevorzugen.

### Schritt 1: Intraday-Dip-Statistik

Use `intraday_range` from collect_data.py AND run this analysis:

```python
python3 -c "
import yfinance as yf
t = yf.Ticker('{{SYMBOL}}')

# Intraday dip stats
h = t.history(period='3mo')
h['dip_pct'] = (h['Open'] - h['Low']) / h['Open'] * 100

dips = h['dip_pct'].dropna().tail(60)
print(f'Median Dip vom Open: {dips.median():.2f}%')
print(f'P25 (75% Chance):    {dips.quantile(0.25):.2f}%')
print(f'Tage mit Dip > 1%:   {(dips > 1).sum()}/60 ({(dips > 1).mean()*100:.0f}%)')
print(f'Tage mit Dip > 2%:   {(dips > 2).sum()}/60 ({(dips > 2).mean()*100:.0f}%)')

# Wann fällt das Tagestief?
h1 = t.history(period='1mo', interval='1h')
if len(h1) > 0:
    h1['hour'] = h1.index.hour
    from collections import Counter
    daily_groups = h1.groupby(h1.index.date)
    low_hours = []
    for date, group in daily_groups:
        if len(group) > 3:
            low_hours.append(group['Low'].idxmin().hour)
    total = len(low_hours)
    morning = sum(1 for h in low_hours if h < 12)
    afternoon = sum(1 for h in low_hours if h >= 12)
    print(f'Tagestief vor 12:00: {morning}/{total} ({morning/total*100:.0f}%)')
    print(f'Tagestief nach 12:00: {afternoon}/{total} ({afternoon/total*100:.0f}%)')
    counts = Counter(low_hours)
    peak_hour = max(counts, key=counts.get)
    print(f'Häufigste Tief-Stunde: {peak_hour}:00 ({counts[peak_hour]}x)')
"
```

### Schritt 2: Realistischen Buy-Bereich berechnen

| Metric | Value |
|--------|-------|
| Open heute | XX.XX |
| Bisheriges Tief heute | XX.XX (X.X% Dip, X% der ATR ausgeschöpft) |
| Median-Dip (50% Chance) | XX.XX |
| P25-Dip (75% Chance) | XX.XX |
| 0,5x ATR vom Open | XX.XX |
| Nächster Support | XX.XX |
| Tagestief-Timing | X% vor 12:00 / X% nach 12:00 |

**Realistischer Buy-Bereich:** MIN(Median-Dip, 0.5x ATR) bis P25-Dip

### Schritt 3: Cert auswählen & Preise berechnen

> **Hinweis:** Claude kann kein Cert automatisch suchen. Schlage ein passendes Produkt vor
> (Turbo Long/Short oder Warrant, Strike ~KO-Level, Hebel 4-8x, Trade Republic verfügbar)
> und nenne ISIN + berechneten theoretischen Preis. Der Nutzer bestätigt dann den realen
> Marktpreis — erst danach wird der finale Trade-Plan mit echtem Cert-Preis ausgegeben.

```
Cert @ Market (Stock XX.XX):  €X.XX  ← theoretisch berechnet
Cert @ Buy-Bereich oben:      €X.XX  (Ersparnis X.X%)
Cert @ Buy-Bereich unten:     €X.XX  (Ersparnis X.X%)
```

**→ Nutzer bestätigt realen Cert-Preis → dann Step 4 finalisieren**

### Schritt 4: Handlungsanweisung (MUSS in Summary stehen!)

```
╔═══════════════════════════════════════════════════════════════╗
║  ENTRY-PLAN                                                   ║
╠═══════════════════════════════════════════════════════════════╣
║  1. Limit-Order: Cert @ €X.XX (= Stock @ XX.XX)             ║
║     → Gültig bis XX:XX Uhr                                   ║
║  2. Wenn nicht gefüllt bis XX:XX:                            ║
║     → Limit anheben auf €X.XX (= P25-Level)                 ║
║  3. Absoluter Fallback (XX:XX):                              ║
║     → Market Buy NUR wenn Daten noch stimmen                 ║
║  4. KEIN Market Buy vor Schritt 1-2!                         ║
╚═══════════════════════════════════════════════════════════════╝
```

**NIEMALS "Market Buy OK" ohne datengetriebene Begründung.**
**Bei Turbos ist jeder Cent am Entry bares Geld.**

---

## Risk Audit (VETO CHECK)

| # | Rule | Value | Status |
|---|------|-------|--------|
| V1 | ATR >7%? | ATR=X.X% | PASS/VETO |
| V2 | CHOPPY + Score <50? | Regime=X, Score=X | PASS/VETO |
| V3 | >=3 positions open? | X/3 | PASS/VETO |
| V4 | Sector >60%? | Sector: X% | PASS/VETO |
| V5 | Monthly drawdown >20%? | P&L: X% | PASS/VETO |
| W1 | Earnings <5 days? | Date | PASS/WARN |
| W2 | Correlation with open? | [which] | PASS/WARN |
| W3 | KO <2x ATR? | Distance=X.Xx | PASS/WARN |
| W4 | Against SMA200 trend? | SMA200=[up/down] | PASS/WARN |
| **W5** | **Overnight event <24h?** | **[Event + time]** | **PASS/WARN** |

### W5 Overnight Event Check (MANDATORY)

Search for events in the next 24 hours that could cause gaps:
- FOMC rate decisions, Fed/ECB speeches
- CPI, NFP, Jobless Claims releases
- Presidential addresses, trade policy announcements
- Geopolitical summits, escalation risks
- Earnings of the symbol being analyzed

**If event found AND position would be held overnight:**
- Apply overnight protection rules from `memory/strategy_v7_draft.md` § Overnight-Event-Regel:
  - Position ≥+10%: Stop on BE (PFLICHT)
  - Position ≥+15%: 50% partial exit or Stop on +5%
  - Position <+10%: Default = close, or document risk acceptance
  - Friday: always BE stop before weekend

**Result:** APPROVED / BLOCKED -- [reason]

---

## Position Sizing (Confidence-basiert)

| Confidence | Total (% Portfolio) | Scout (60%) | Confirmation (40%) |
|------------|---------------------|-------------|-------------------|
| 60-65% | Small **15%** | 9% | 6% |
| 65-70% | Standard **20%** | 12% | 8% |
| 70%+ | Standard **25%** | 15% | 10% |

**Calculate:**
- Portfolio value from `prediction_db.py portfolio`
- Scout = Portfolio × Scout% → divide by cert ask price → number of certs
- Confirmation = Portfolio × Confirm% → only after signal confirmation

## Risk-Per-Trade

| Metric | Value |
|--------|-------|
| Portfolio value | XXX EUR |
| Position size (XX%) | XXX EUR |
| Scout (60%) | XXX EUR / XX certs |
| Confirmation (40%) | XXX EUR / XX certs |
| Max loss per trade (10%) | XXX EUR |
| Currently at risk | XXX EUR |
| Remaining risk budget | XXX EUR |

---

## Output

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
  "regime": "",
  "ko_level_usd": 0.00,
  "ko_method": "ATR|CHART",
  "entry_usd": 0.00,
  "stop_usd": 0.00,
  "target_usd": 0.00,
  "exits": [{"price": 0, "pct": 50}],
  "risk_per_trade_eur": 0,
  "overnight_event": null,
  "overnight_protection": null,
  "vetoes": [],
  "warnings": [],
  "approved": true
}
```

```
[STEP 3 COMPLETE]
```
