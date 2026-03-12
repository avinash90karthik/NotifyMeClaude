# SCHRITT 3: JUDGE & RISK

**Asset:** {{SYMBOL}}

---

**Input:** Daten aus Schritt 1 + Debate aus Schritt 2 (inkl. Finale Konfidenz aus Runde 3) + Chart
Referenziere die JSON-Blöcke aus Schritt 1 und 2 fuer strukturierte Datenpunkte.

Konsultiere `memory/reflections.md` fuer historische Performance-Daten (Win-Rate, Muster, Risk/Reward).

---

## INVESTMENT JUDGE

**Der Judge MUSS den Chart als unabhaengige Quelle heranziehen!**

### JUDGE CHART-ANALYSE

**Analysiere den Chart UNABHAENGIG von Bull/Bear:**

| Aspekt | Deine Beobachtung | Gewichtung |
|--------|-------------------|------------|
| Trend-Richtung | [Was siehst du?] | Hoch/Mittel/Niedrig |
| SMA-Konstellation | [Golden/Death Cross?] | Hoch/Mittel/Niedrig |
| RSI-Signal | [Ueberkauft/Ueberverkauft/Neutral?] | Hoch/Mittel/Niedrig |
| **RSI-Delta/Divergenz** | [Dreht RSI? Divergenz erkannt?] | **Hoch** |
| Volume-Bestaetigung | [Bestaetigt Volume den Trend?] | Hoch/Mittel/Niedrig |
| Money Flow (CMF) | [Akkumulation/Distribution?] | Hoch/Mittel/Niedrig |
| Chart-Pattern | [Erkennbare Muster?] | Hoch/Mittel/Niedrig |

**RSI-Divergenz-Urteil:**
> Wenn bullische Divergenz bei RSI <35: Starkes Argument fuer bevorstehende Trendwende.
> Wenn RSI oversold ABER Delta negativ und keine Divergenz: Wasserfall-Risiko, KEIN Kaufsignal!
> Divergenz-Daten aus Schritt 1 hier EXPLIZIT referenzieren!

**Chart-Urteil:** Der Chart spricht fuer [BULL/BEAR/NEUTRAL] weil [1-2 Saetze]

### URTEIL

Analysiere die Bull vs Bear Argumente aus Schritt 2:

**Bewertung der Argumente:**

| Seite | Staerke | Beste Argumente |
|-------|---------|-----------------|
| 🐂 Bull | X/10 | [Top 2 Argumente] |
| 🐂 Bull Finale Konfidenz | XX% | [Aus Runde 3] |
| 🐻 Bear | X/10 | [Top 2 Argumente] |
| 🐻 Bear Finale Konfidenz | XX% | [Aus Runde 3] |
| 📊 Chart | X/10 | [Was sagt der Chart?] |
| 📈 RSI-Divergenz | [Bullisch/Bearisch/Keine] | [Staerke des Signals] |
| 📰 News Sentiment (NSI) | [X.XX] | [Stark bullisch / Leicht bullisch / Neutral / Bearisch] |
| 🔄 Regime | [TRENDING/RANGE/CHOPPY/TRANSITIONAL] | [Signal aligned mit Regime?] |
| 🩳 Short Interest | X% Float / X Tage | [Squeeze-Potential oder bearishes Signal?] |

**Entscheidende Faktoren:**
1. [Wichtigster Faktor]
2. [Zweitwichtigster Faktor]
3. [Drittwichtigster Faktor]

### REGIME-ADJUSTMENT

```
╔═══════════════════════════════════════════════════════════════╗
║  KONFIDENZ-ADJUSTMENT basierend auf Regime                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  TRENDING + Signal MIT Trend:     Konfidenz +5%              ║
║  TRENDING + Signal GEGEN Trend:   Konfidenz -10%             ║
║  RANGE + Signal an S/R-Level:     Konfidenz +3%              ║
║  RANGE + Signal in Range-Mitte:   Konfidenz -5%              ║
║  CHOPPY:                          Konfidenz -5% bis -10%     ║
║  TRANSITIONAL:                    Kein Adjustment             ║
║                                                               ║
║  Regime: [TRENDING/RANGE/CHOPPY/TRANSITIONAL]                ║
║  Signal-Richtung vs Trend: [MIT/GEGEN/NEUTRAL]               ║
║  → Adjustment: [+X% / -X% / 0%]                             ║
║  → Konfidenz vor Adjustment: XX%                             ║
║  → Konfidenz nach Adjustment: XX%                            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### ENTSCHEIDUNG

```
╔═══════════════════════════════════════╗
║  SIGNAL: [LONG / SHORT / HOLD]        ║
║  KONFIDENZ: [XX]%                     ║
╚═══════════════════════════════════════╝
```

**Begruendung:** [2-3 Saetze warum diese Entscheidung - inkl. Chart-Bestaetigung und RSI-Divergenz!]

### Confidence Score Referenz:
| Wert | Bedeutung |
|------|-----------|
| 0.85-1.00 | Extrem stark - alle Signale aligned |
| 0.70-0.84 | Stark - klare Richtung |
| 0.55-0.69 | Moderat - einige Gegenfaktoren |
| 0.40-0.54 | Schwach - eher HOLD |
| < 0.40 | Unklar - HOLD oder IGNORE |

---

## KO-LEVEL ANALYSE

Basierend auf dem Signal: **[LONG/SHORT]**

```
╔═══════════════════════════════════════════════════════════════╗
║  KO-BERECHNUNG: ATR + CHART-SUPPORT KOMBINIERT               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  SCHRITT A: ATR-Multiplikator nach Asset-Klasse bestimmen    ║
║  SCHRITT B: Chart-Support/Resistance identifizieren          ║
║  SCHRITT C: KO = das WEITER ENTFERNTE von beiden             ║
║                                                               ║
║  ❌ NIEMALS KO zwischen Preis und Support setzen!            ║
║  ❌ NIEMALS nur ATR ODER nur Chart nutzen - IMMER beides!    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### SCHRITT A: ATR-Multiplikator nach Asset-Klasse

ATR (14) aus Schritt 1: **$XX.XX (X.X%)**

| Asset-Klasse | Beispiele | ATR-Multiplikator | Warum |
|-------------|-----------|-------------------|-------|
| Large Cap Aktien | NVDA, AAPL, MSFT | 2.0x ATR | Stabile Orderbuecher, geringe Gap-Gefahr |
| Mid/Small Cap Aktien | ARM, IREN, VST | 2.5x ATR | Duennere Liquiditaet, staerkere Earnings-Moves |
| Rohstoffe (Gold, Silber) | GC=F, SI=F | 3.0x ATR | Makro-Schocks (Fed, Zoelle, Geopolitik), Gap-Risiko ueber Nacht |
| Krypto-bezogen | MSTR, COIN | 3.0x ATR | Extreme Volatilitaet, 24/7 Underlying |
| Gehebelte Indizes | QQQ, SPY Turbos | 2.0x ATR | Breit diversifiziert, weniger Einzelrisiko |

**Bestimme die Asset-Klasse von {{SYMBOL}}:** [Klasse]
**ATR-Multiplikator:** [X.Xx]
**ATR-basiertes KO-Level (LONG):** Preis - (ATR x Multiplikator) = $XX.XX - ($XX.XX x X.X) = **$XX.XX**
**ATR-basiertes KO-Level (SHORT):** Preis + (ATR x Multiplikator) = $XX.XX + ($XX.XX x X.X) = **$XX.XX**

### SCHRITT B: Chart-Support als Mindestabstand

Identifiziere die relevanten Chart-Levels aus Schritt 1:

| Level | Preis | Staerke (1-5) | Begruendung |
|-------|-------|---------------|-------------|
| Naechster Support (S1) | $XX.XX | X/5 | [Warum ist das ein Support?] |
| Starker Support (S2) | $XX.XX | X/5 | [Warum?] |
| Kritischer Support (S3) | $XX.XX | X/5 | [Warum?] |

**Chart-basiertes KO-Level:** Unter dem staerksten relevanten Support + Puffer (0.5-1%)
→ Support bei $XX.XX → KO bei **$XX.XX** (Support - X%)

### SCHRITT C: FINALES KO-LEVEL

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  REGEL: KO = das WEITER vom Preis ENTFERNTE Level            ║
║                                                               ║
║  ATR-basiert:    $XX.XX (XX.X% vom Preis)                    ║
║  Chart-basiert:  $XX.XX (XX.X% vom Preis)                    ║
║                                                               ║
║  → FINALES KO:  $XX.XX (XX.X% vom Preis)                    ║
║  → Hebel:       ~Xx                                          ║
║  → Methode:     [ATR / Chart / Beide gleich]                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Begruendung:** [2-3 Saetze warum dieses KO-Level. Welches Chart-Level schuetzt? Warum reicht der ATR-Abstand (nicht)?]

### EARNINGS / EVENT-WARNUNG

```
⚠️ EARNINGS/EVENT CHECK:
- Naechster Earnings-Termin: [Datum oder "keiner in 2 Wochen"]
- Andere Events (Fed, CPI, etc.): [Datum]
- WENN Event < 5 Handelstage entfernt:
  → ATR-Multiplikator um +0.5 erhoehen (Earnings-Gaps!)
  → ODER Position vor Event teilweise schliessen
```

---

## RISK-PER-TRADE CHECK

```
╔═══════════════════════════════════════════════════════════════╗
║  PORTFOLIO-SCHUTZ                                            ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Portfolio-Wert (aus Supabase):     XXX EUR                  ║
║  Max. Verlust pro Trade (10%):      XXX EUR                  ║
║  Max. gleichzeitig riskiert (40%):  XXX EUR                  ║
║  Aktuell riskiert (offene Pos.):    XXX EUR                  ║
║  Noch verfuegbares Risiko-Budget:   XXX EUR                  ║
║                                                               ║
║  ⚠️ Wenn Risiko-Budget aufgebraucht → KEIN neuer Trade!     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## TRADE-PLAN

**Basierend auf der Analyse - konkrete Handlungsempfehlung:**

### Entry
| Aktion | Preis | Begruendung |
|--------|-------|-------------|
| **Buy** | $XX.XX | [Warum hier einsteigen?] |
| **KO-Level** | $XX.XX | [ATR + Chart kombiniert] |

### Exits (gestaffelt)
| Aktion | Preis | Anteil | Begruendung |
|--------|-------|--------|-------------|
| **Sell** | $XX.XX | XX% | [Welches Resistance-Level?] |
| **Sell** | $XX.XX | XX% | [Naechstes Ziel?] |
| **Sell** | $XX.XX | Rest | [Stretch-Ziel?] |

### Stops
| Aktion | Preis | Anteil | Begruendung |
|--------|-------|--------|-------------|
| **Stop** | $XX.XX | XX% | [Mentaler Stop UEBER KO!] |
| **Stop** | $XX.XX | Rest | [Absolutes Limit?] |

### Time-Stops
| Bedingung | Aktion |
|-----------|--------|
| Nach 5 Handelstagen <5% im Plus | Position halbieren |
| Nach 8 Handelstagen seitwaerts | Position schliessen |
| Earnings < 2 Tage entfernt | Min. 50% sichern |

### Watch Zones
| Zone | Preis-Range | Was tun? |
|------|-------------|----------|
| [Zone 1] | $XX - $XX | [Beobachten / Nachkaufen / Verkaufen?] |
| [Zone 2] | $XX - $XX | [Beobachten / Nachkaufen / Verkaufen?] |

---

## RISK AUDIT (VETO-CHECK)

```
╔═══════════════════════════════════════════════════════════════╗
║  UNABHAENGIGER RISK AUDIT — KANN TRADE BLOCKIEREN!           ║
╠═══════════════════════════════════════════════════════════════╣
║  Jede einzelne VETO-Regel kann den Trade verhindern.         ║
║  Pruefe JEDE Regel explizit mit ✅ oder ❌!                  ║
╚═══════════════════════════════════════════════════════════════╝
```

| # | Regel | Pruefung | Status |
|---|-------|----------|--------|
| V1 | ATR > 7%? | ATR = X.X% | ✅/❌ VETO |
| V2 | Regime CHOPPY + Score < 50? | Regime = [X], Score = [X] | ✅/❌ VETO |
| V3 | >= 3 offene Positionen? | Aktuell: X/3 | ✅/❌ VETO |
| V4 | Sektor > 60% nach neuem Trade? | [Sektor]: X% | ✅/❌ VETO |
| V5 | Monats-Drawdown > 20%? | März P&L: X% | ✅/❌ VETO |
| W1 | Earnings < 5 Handelstage? | [Datum oder "Nein"] | ✅/⚠️ |
| W2 | Korrelation mit offener Position? | [Ja/Nein — welche?] | ✅/⚠️ |
| W3 | KO-Abstand < 2x ATR? (Rohstoffe < 3x) | KO-Abstand = X.Xx ATR | ✅/⚠️ |
| W4 | Signal gegen SMA200-Richtung? | SMA200-Trend = [UP/DOWN] | ✅/⚠️ |

**Risk Audit Ergebnis:**

```
╔═══════════════════════════════════════╗
║  ✅ TRADE FREIGEGEBEN                 ║  (wenn alle VETOs bestanden)
║  ⛔ TRADE BLOCKIERT — [Grund]        ║  (wenn mindestens 1 VETO)
╚═══════════════════════════════════════╝
```

---

## ENFORCEMENT

- ✅ Judge analysiert Chart UNABHAENGIG von Bull/Bear
- ✅ **RSI-Divergenz explizit im Judge-Urteil beruecksichtigt**
- ✅ Signal-Box mit LONG/SHORT/HOLD + Konfidenz%
- ✅ KO-Level mit BEIDEN Methoden berechnet (ATR + Chart)
- ✅ ATR-Multiplikator nach Asset-Klasse differenziert
- ✅ KO liegt IMMER unter dem staerksten Support (LONG) / ueber Resistance (SHORT)
- ✅ Earnings/Event-Warnung geprueft
- ✅ Risk-per-Trade Check gegen Portfolio-Limit
- ✅ Gestaffelter Sell-Plan mit konkreten Preisen und Prozenten
- ✅ Time-Stops definiert
- ✅ Stop-Levels basierend auf Support-Zonen
- ✅ **Risk Audit: Alle 5 VETO-Regeln + 4 WARNUNGs explizit geprueft (PFLICHT!)**
- ✅ **Regime-Adjustment angewandt (Konfidenz vor/nach dokumentiert)**

---

## OUTPUT JSON

**WICHTIG: Der JSON-Block ist ZUSAETZLICH zur Prosa. Er ersetzt NICHTS.**

Generiere am Ende von Schritt 3 diesen strukturierten Output:

```json
{
  "step": 3,
  "symbol": "{{SYMBOL}}",
  "signal": "LONG|SHORT|HOLD",
  "confidence_pct": 0,
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

Fuelle ALLE Felder mit den tatsaechlichen Werten aus der Analyse!

```
✅ [SCHRITT 3: JUDGE & RISK ABGESCHLOSSEN]
```
