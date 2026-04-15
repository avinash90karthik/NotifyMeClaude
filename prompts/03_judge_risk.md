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
```

Das Gate aus CLAUDE.md ist automatisch konsistent: 36/60 = 60% = Trade-Gate.

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

| Reversion-Guard sagt | Entry-Regel | entry_price in DB |
|----------------------|-------------|-------------------|
| LONG: Pullback-Pflicht | Limit ≤ Close − 1×ATR | Limit-Level |
| LONG: Kein Reversion-Edge | Limit im Buy-Range (upper bound für schnelleren Fill) | Limit-Level |
| LONG: Echter Breakout (kein Reversion-Setup, Bruch R1) | Entry = Trigger-Level | Trigger-Level |
| SHORT: Valid | Limit ≥ Close + 1×ATR ODER Extension-Bruch-Level | Trigger-Level |
| SHORT: NO-TRADE | Setup abbrechen | — |

**Hart:** `prediction_db.py record --entry` = Limit-/Trigger-Level, niemals der Close. HDD.DE #82 ist der Post-Mortem-Grund für diese Regel.

### Entry-Plan-Card (Pflicht in Step-3-Output)

```
╔══════════════════════════════════════════════════════════════╗
║  ENTRY-PLAN                                                  ║
╠══════════════════════════════════════════════════════════════╣
║  1. Limit-Order:   Cert @ €X.XX  (= Stock @ XX.XX)           ║
║     Gültig bis XX:XX Uhr                                     ║
║  2. Falls nicht gefüllt bis XX:XX:                           ║
║     Limit anheben auf €X.XX  (= P25-Level aus Buy-Range)     ║
║  3. Absoluter Fallback (XX:XX):                              ║
║     Market Buy NUR wenn Daten noch stimmen                   ║
║  KEIN Market Buy vor Schritt 1–2.                            ║
╚══════════════════════════════════════════════════════════════╝
```

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

## Position Sizing

| Confidence | Total (% Portfolio) | Scout (60%) | Confirmation (40%) |
|------------|---------------------|-------------|--------------------|
| 60-65% | 15% | 9% | 6% |
| 65-70% | 20% | 12% | 8% |
| 70%+ | 25% | 15% | 10% |

**Rechnen:**
- Portfolio-Value aus `prediction_db.py portfolio`
- Scout = Portfolio × Scout-% → durch Cert-Ask-Preis → Cert-Anzahl
- Confirmation = Portfolio × Confirm-% → erst nach Signal-Bestätigung

### Risk-per-Trade Tabelle

| Metric | Wert |
|--------|------|
| Portfolio-Value | XXX EUR |
| Position Size (XX%) | XXX EUR |
| Scout (60%) | XXX EUR / XX Certs |
| Confirmation (40%) | XXX EUR / XX Certs |
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
║ Certs Scout:       XX Stück @ €X.XX                          ║
║                                                              ║
║ V-Vetos aktiv:     <keine | V1/V3/...>                       ║
║ W-Warnings aktiv:  <keine | W1/W5/...>  → Trade-Plan-Mods    ║
║ Approved:          JA / NEIN                                 ║
╚══════════════════════════════════════════════════════════════╝

Reasoning: <2-3 Sätze, Chart + Indicator-Context + Signal>

[STEP 3 COMPLETE]
```
