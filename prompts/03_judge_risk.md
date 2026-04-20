# STEP 3: JUDGE & RISK

**Asset:** {{SYMBOL}}
**Input:** Step 1 Stichpunkte + Ratings | Step 2 Scorecard + Bull/Bear-Synthese.

---

## Judge-Verdict

### Signal + Confidence (Formel, keine freie Liste)

```
Richtung       = LONG wenn Scorecard-LONG-Total > Scorecard-SHORT-Total, sonst SHORT
Raw Confidence = max(LONG-Total, SHORT-Total) / 60 × 100   (%)

Differenz-Strafe:
  |LONG-Total − SHORT-Total| < 10   →   Confidence × 0.9
  |LONG-Total − SHORT-Total| ≥ 10   →   Confidence × 1.0

v9 Oversold-Bonus (Rule 19) — nur für LONG:
  Indicator-Context RSI-Band <20 + Fwd5 green ≥65% + n≥20  →  +5% Confidence
  Indicator-Context RSI-Band <15 + Fwd5 green ≥70% + n≥20  →  +8% Confidence (Kapitulation)
  Bonus wird NACH Differenz-Strafe addiert.
```

Das Gate aus CLAUDE.md ist automatisch konsistent: 36/60 = 60% = Trade-Gate (vor Oversold-Bonus).

### Judge-Override (erlaubt, aber mit Pflicht-Doku)

Der Judge darf die Scorecard überstimmen, wenn mindestens ein Step-1-Rating **erkennbar fehlkalibriert** ist. Fehlkalibrierung heißt:
- Sample zu klein (THIN) wurde als vollwertig gezählt
- Rating-Quelle nicht aus Step 1 zitiert (verbotener Bauchgefühl-Punkt)
- Harte neue Information seit Step 1 erschienen (Trump-Post, Earnings-Gap)

Ein Override MUSS dokumentiert werden mit:
1. **Welches Rating** fehlkalibriert ist
2. **Warum** (ein Satz mit konkretem Quellenverweis)
3. **Impact**: Scorecard sagte X, Judge entschied Y

Diese Dokumentation wandert verbatim in die Step-3-Card UND in die Step-4-Trading-Card — der User muss jeden Override sehen.

### Neutralitäts-Check (hart vor Final-Signal)

- Spiegel-Test: Würde ich bei spiegelbildlichen Daten (RSI 90 statt 10, +17% statt −17%) **dieselben** Argumente gelten lassen? Asymmetrisch = Bias.
- Gate ist Confidence < 60% ODER aktives V-Veto. Alles andere („zu spät einsteigen", „R/R nicht perfekt", „Counter-Trend ungemütlich") sind Trade-Plan-Justierungen (kleinere Size, engere Targets), keine Signal-Vetos.
- NO-TRADE ist ein valides Ergebnis, aber nur bei echter Gate-Verletzung — nicht aus Vorsicht.

### Horizon

**Nur 1-5 Tage** (CLAUDE.md Rule 17). Medium-/Long-Term werden NICHT bewertet. Wenn 1-5d kein Edge zeigt → Signal = NO-TRADE.

Verboten: „Setup aktiv ab Datum X", „wiederkommen in Y Wochen", „warten bis T-7 pre-earnings". Solche Muster sind RISIKO-Warnungen oder Watchlist-Trigger, niemals Trade-Trigger.

---

## KO-Level

KO = dasjenige Level, das WEITER vom Preis entfernt ist (ATR-basiert oder Chart-basiert).

### A — ATR-basierter KO

| Asset Class | Multiplikator | Kriterium |
|-------------|---------------|-----------|
| Large Cap | 2.0× ATR | Market Cap > $50B |
| Mid/Small Cap | 2.5× ATR | Market Cap < $50B |
| Commodities | 3.0× ATR | Futures (=F Suffix) |
| Crypto-related | 3.0× ATR | BTC/Crypto-Exposure |

Multiplikator-Aufschläge (KO weiter weg legen):
- ATR5/ATR14 > 1.5 (Vola-Spike) → +0.5
- Earnings < 5 Tage → +0.5

```
ATR-KO (LONG)  = Preis − (ATR × Multiplikator)
ATR-KO (SHORT) = Preis + (ATR × Multiplikator)
```

### B — Chart-basierter KO

Stärkster Support (LONG) oder Widerstand (SHORT) aus Step 1 § 1.4, + 0.5-1% Puffer.

### C — Final KO

| Methode | Level | Distanz |
|---------|-------|---------|
| ATR-basiert | XX.XX | X.X% |
| Chart-basiert | XX.XX | X.X% |
| **FINAL** | **XX.XX** | **X.X%** (further of the two) |

---

## Optimal Entry (Rule 18 + Script-gesteuert)

```bash
python3 reversion_guard.py {{SYMBOL}} --direction <LONG|SHORT>   # aus Step 2 vorgezogen
python3 entry_calibration.py {{SYMBOL}}                          # Intraday-Dip-Statistik + Buy-Range
```

### Verdict-Logik

| Reversion-Guard sagt | Entry-Center-Regel | entry_price in DB |
|----------------------|--------------------|-------------------|
| LONG: Pullback-Pflicht | Center = Close − 1×ATR | Center-Level |
| LONG: Kein Reversion-Edge | Center = Buy-Range-Upper (P25-Dip) | Center-Level |
| LONG: Echter Breakout (kein Reversion-Setup, Bruch R1) | Center = Trigger-Level | Trigger-Level |
| SHORT: Valid | Center = Close + 1×ATR ODER Extension-Bruch-Level | Trigger-Level |
| SHORT: NO-TRADE | Setup abbrechen | — |

**Hart:** `prediction_db.py record --entry` = **Center-Level** der Range (nicht Primär, nicht Fallback), niemals der Close. HDD.DE #82 ist der Post-Mortem-Grund für diese Regel.

### Limit-Range statt Punktwert (Vola-abgeleitet, PFLICHT)

Ein Punkt-Limit ("exakt $89.00") verfehlt systematisch Fills, wenn der Markt den Wert nur knapp touchiert. Stattdessen: **Range um Center-Level**, Breite aus Volatilität.

**Formel:**
```
Range-Halbbreite = max(0.25 × ATR, 0.5% × Close, 0.10 EUR)
Primär-Level     = Center − Halbbreite  (optimistisch, besserer Fill-Preis)
Fallback-Level   = Center + Halbbreite  (defensiv, höhere Fill-Wahrscheinlichkeit)
```

- `0.25 × ATR` ist die Grund-Vola-Komponente — spiegelt das stock-spezifische Intraday-Noise-Level
- `0.5% × Close` ist der Floor für Low-ATR-Titel (z.B. SAP: ATR 2% → Range wäre sonst zu eng)
- `0.10 EUR` ist der absolute Minimum-Tick-Floor (Warrants/Turbos, deren Spread-Treppe > Computed-Range ist)
- Max aus allen drei = finale Halbbreite

**Cert-Seite:** Range auf Cert umrechnen über `Cert-Range = Halbbreite × Hebel × EUR-Faktor / Stock-Preis × Cert-Preis` — einfacher: Primär-Cert-Level = Cert-Limit bei Stock=Primär-Level interpolieren. Dokumentiere Stock-Level UND Cert-Level in der Card.

**Fallback-Trigger-Zeit:** 60-90 Minuten nach Primär-Order-Platzierung (bei US-Open-Entry typisch 11:00-11:30 NY / 17:00-17:30 CET). Vor dem Trigger NICHT anheben.

### Entry-Plan-Card (Pflicht in Step-3-Output)

```
╔══════════════════════════════════════════════════════════════╗
║  ENTRY-PLAN (Limit-Range, Vola-abgeleitet)                   ║
╠══════════════════════════════════════════════════════════════╣
║  Center-Level:     Stock $XX.XX  (= Cert €X.XX)              ║
║  Range-Halbbreite: $X.XX  (max(0.25×ATR, 0.5%, 0.10€))       ║
║                                                              ║
║  1. PRIMÄR-LIMIT:  Cert @ €X.XX  (= Stock @ $XX.XX)          ║
║     Range-Low, optimistischer Fill                           ║
║     Gültig bis XX:XX CET                                     ║
║                                                              ║
║  2. FALLBACK-LIMIT (ab XX:XX CET, +60-90min):                ║
║     Cert @ €X.XX  (= Stock @ $XX.XX)                         ║
║     Range-High, defensiver Fill                              ║
║                                                              ║
║  3. ABSOLUTER NO-CHASE-LEVEL:                                ║
║     Stock > $XX.XX  (= Center + 2×Halbbreite)                ║
║     → Trade verfällt, NICHT kaufen                           ║
║                                                              ║
║  KEIN Market-Buy, keine Orders außerhalb Range.              ║
╚══════════════════════════════════════════════════════════════╝
```

**DB-Record:** `--entry <Center-Level>` — Backtest braucht den mittleren erwarteten Fill-Preis, nicht den optimistischen oder defensiven.

Cert-Vorschlag: passendes Produkt (Turbo Long/Short oder Warrant, Strike ~ KO-Level, Hebel 4-8×, auf Trade Republic verfügbar) mit ISIN und theoretischem Preis. User bestätigt realen Marktpreis — dann Step 4.

---

## Trade Plan

**Entry (Limit):** XX.XX  |  **KO:** XX.XX  |  **Stop (mental, above KO):** XX.XX

**Exits (v8, ersetzt v5):**
- 80% SELL bei +20% Cert-Gewinn — sofort
- Rest max +30%, danach Stop trailing
- Trump-Event / Overnight-Event → alles raus

**Time-Stops:** 3 Tage < 5% Profit → halbieren | 5 Tage seitwärts → exit | Earnings < 2 Tage → 50% sichern

**Erwartete Dauer:** 1-3d Momentum / 2-4d Pullback / 1-2d Event. Falls > 5d → Turbo-Eignung explizit warnen.

---

## Risk Audit

### V-Vetos (hart — bei EINEM aktivem V: Signal = NO-TRADE)

| # | Rule | Value | Status |
|---|------|-------|--------|
| V1 | ATR > 7%? (Warrants/Options statt KO) | ATR=X.X% | PASS/VETO |
| V2 | CHOPPY + Score < 50? | Regime=X, Score=X | PASS/VETO |
| V3 | ≥ 3 offene Positionen? | X/3 | PASS/VETO |
| V4 | Sektor > 60%? | Sektor: X% | PASS/VETO |
| V5 | Monats-Drawdown > 20%? | P&L: X% | PASS/VETO |

### W-Warnings (ändern NUR Trade-Plan, keine Confidence-Minus)

| # | Rule | Wirkung bei aktiv | Status |
|---|------|-------------------|--------|
| W1 | Earnings < 5 Tage | KO-Multiplikator +0.5 | PASS/WARN |
| W2 | Correlation zu offener Position | Size halbieren | PASS/WARN |
| W3 | KO < 2× ATR (zu eng) | KO weiter, Multiplikator anheben | PASS/WARN |
| W5 | Overnight-Event < 24h (FOMC/CPI/NFP/Trump/Earnings) | Overnight-Regel (s.u.) | PASS/WARN |

**W5 Overnight-Protection** (aus `memory/strategy_v7_draft.md` § Overnight-Event-Regel):
- Position ≥ +10% → Stop auf BE (Pflicht)
- Position ≥ +15% → 50% Partial-Exit oder Stop auf +5%
- Position < +10% → Default = schließen, oder Risk-Acceptance dokumentieren
- Freitag: immer BE-Stop vor Wochenende

**Result:** APPROVED / BLOCKED — [Grund]

---

## Position Sizing (v9: Scout-Invertierung bei knapper Confidence)

**Rule 20 (v9):** Bei Confidence 60-65% ist der Scout **kleiner** als die Confirmation (40/60 statt 60/40). Ab ≥65% klassische Aufteilung (60/40).

| Confidence | Total (% Portfolio) | Scout % von Total | Confirmation % von Total | Scout (% Portfolio) | Confirmation (% Portfolio) |
|------------|---------------------|-------------------|--------------------------|---------------------|----------------------------|
| 60-65% | 15% | **40% (invertiert)** | **60%** | 6% | 9% |
| 65-70% | 20% | 60% | 40% | 12% | 8% |
| 70%+ | 25% | 60% | 40% | 15% | 10% |

**Begründung (aus Backtest 16.04.2026):** 60-65% Confidence-Bracket hat nur 56% Accuracy und +0.33% Ø-Move (Coin-Flip). Invertierter Scout reduziert den Schaden bei Fehlsignal, Confirmation-Buy nach Bestätigung (mind. +5% im Plus) setzt die Hauptgröße erst bei echter Trendbestätigung.

**Rechnen:**
- Portfolio-Value aus `prediction_db.py portfolio`
- Scout = Portfolio × Scout-% → durch Cert-Ask-Preis → Cert-Anzahl
- Confirmation = Portfolio × Confirm-% → erst nach Signal-Bestätigung (Scout +5% im Plus ODER klarer Regime-Beweis)

**Card-Pflicht:** Step 3 Card und Step 4 Order-Plan müssen explizit dokumentieren, ob Scout-Invertierung aktiv ist ("v9 Scout-invertiert" oder "v9 Scout-klassisch").

### Risk-per-Trade Tabelle

| Metric | Wert |
|--------|------|
| Portfolio-Value | XXX EUR |
| Position Size (XX%) | XXX EUR |
| Scout (XX% von Total — v9 split) | XXX EUR / XX Certs |
| Confirmation (XX% von Total — v9 split) | XXX EUR / XX Certs |
| Max Loss pro Trade (10%) | XXX EUR |
| Aktuell im Risk | XXX EUR |
| Remaining Risk-Budget | XXX EUR |

---

## Output-Card (kein JSON)

```
Step 3:
╔══════════════════════════════════════════════════════════════╗
║ JUDGE VERDICT — {{SYMBOL}}                                   ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:            LONG | SHORT | NO-TRADE                   ║
║ Confidence:        XX%   (Raw XX% × Differenz-Faktor)        ║
║ Scorecard-Diff:    LONG XX / SHORT XX  (Diff=XX)             ║
║                                                              ║
║ Judge-Override:    JA / NEIN                                 ║
║   Rating:          <Technical|Price-Action|News|Event>       ║
║   Grund:           <1-2 Sätze, Quellenverweis>               ║
║   Impact:          Scorecard sagte <X>, Judge entschied <Y>  ║
║                                                              ║
║ Reversion-Guard:   <Pullback-Pflicht @ X.XX | No-Edge |      ║
║                     SHORT-NO-TRADE>                          ║
║ Entry (Limit):     XX.XX                                     ║
║ Stop (mental):     XX.XX                                     ║
║ KO (final):        XX.XX  (X.X%, Methode: ATR|Chart)         ║
║ Target (+20%):     XX.XX                                     ║
║                                                              ║
║ Position Size:     XX% Portfolio (XXX EUR)                   ║
║ v9 Split:          Scout-invertiert (40/60) |                ║
║                    Scout-klassisch (60/40)                   ║
║ Oversold-Bonus:    NEIN | +5% (RSI<20 green XX%) |           ║
║                    +8% (RSI<15 green XX% Kapitulation)       ║
║ Certs Scout:       XX Stück @ €X.XX (XX% von Total)          ║
║ Certs Confirm:     XX Stück @ €X.XX (XX% von Total)          ║
║                                                              ║
║ V-Vetos aktiv:     <keine | V1/V3/...>                       ║
║ W-Warnings aktiv:  <keine | W1/W5/...>  → Trade-Plan-Mods    ║
║ Approved:          JA / NEIN                                 ║
╚══════════════════════════════════════════════════════════════╝

Reasoning: <2-3 Sätze, Chart + Indicator-Context + Signal>

[STEP 3 COMPLETE]
```
