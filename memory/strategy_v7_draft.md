# Strategy v7 — Direct Position Hedge

> **Status:** AKTIV — Live-Test bestanden (ENR.DE 26-27.03.2026)
> **Basis:** v5 core + v6 Blind Re-Analysis + Direct Hedge + Pivot
> **Ziel:** Bei intakter These Verluste reduzieren OHNE Position zu schließen

---

## Das Problem mit v5/v6 Hedge

```
v5 Hedge: Index-SHORT (DAX/Nasdaq) als 3. Slot
→ GESCHEITERT: DAX-Short am 24.03 = -27€ (-19%) in 1 Tag
→ GRUND: Basis-Risiko — Index und Einzelaktie korrelieren nicht 1:1
→ DAX stieg, ENR fiel (oder umgekehrt) → Hedge wirkte nicht
```

---

## v7 Kern-Änderung: Direct Position Hedge

```
╔═══════════════════════════════════════════════════════════════╗
║  DIRECT POSITION HEDGE — v7                                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  TRIGGER — HARTE REGEL:                                      ║
║  → Zertifikat -20% vom Einstieg — SOFORT handeln!            ║
║  → NICHT warten auf -25%, -30% oder schlimmer!               ║
║  → Bei €6.000 Kapital: -20% vs -29% = €50-80 extra Verlust! ║
║  → Gleicher Trigger wie v6 Blind Re-Analysis!                ║
║                                                               ║
║  BEDINGUNGEN (alle müssen erfüllt sein):                     ║
║  1. Cert -20% → v6 Blind Re-Analysis durchgeführt            ║
║  2. Blind-Ergebnis = GLEICHE Richtung (These intakt!)        ║
║  3. Momentum KLAR dagegen (mind. 2 von 3):                   ║
║     • MACD bearish und expandierend                          ║
║     • SMA50 gebrochen                                        ║
║     • Makro-Headwind (Geopolitik, Risk-Off)                  ║
║  4. Katalysator ist EXTERN (Makro), NICHT stock-spezifisch   ║
║                                                               ║
║  WAS:                                                        ║
║  → SHORT-Turbo auf DASSELBE Underlying öffnen                ║
║  → NICHT Index, NICHT Sektor-ETF — DIREKT das gleiche!       ║
║  → Null Basis-Risiko, mathematisch berechenbar               ║
║                                                               ║
║  GRÖßE:                                                     ║
║  → Lottery (max = kleinste offene LONG-Position)              ║
║  → Ziel: 50-65% der Long-Exposure hedgen                     ║
║  → NIEMALS 100% hedgen (= teures Schließen)                  ║
║                                                               ║
║  SHORT-TURBO KO:                                             ║
║  → ÜBER dem nächsten Widerstand                              ║
║  → Mindestens 10% über aktuellem Kurs                        ║
║  → Je weiter KO, desto weniger Hebel (= sicherer)           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Exit-Regeln für den Hedge

```
╔═══════════════════════════════════════════════════════════════╗
║  HEDGE EXIT — 3 Trigger + Time-Stop                          ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. MOMENTUM DREHT:                                          ║
║     → Grüner Tag + RSI steigt über 35-40                     ║
║     → MACD-Histogramm dreht positiv                          ║
║     → SHORT schließen, LONG laufen lassen                    ║
║                                                               ║
║  2. KATALYSATOR LÖST SICH AUF:                               ║
║     → Geopolitik-Deeskalation, Makro-Wende                   ║
║     → SHORT SOFORT schließen (Snap-Back = gefährlich)        ║
║     → LONG profitiert vom Rebound                            ║
║                                                               ║
║  3. LONG-STOP WIRD ERREICHT:                                 ║
║     → BEIDE Positionen schließen                             ║
║     → Netto-Verlust deutlich kleiner als ohne Hedge          ║
║                                                               ║
║  TIME-STOP — HARTE REGEL (wie v5 Time-Stops):               ║
║  → Max 5 Tage Hedge offen halten — KEINE Ausnahmen!         ║
║  → Tag 5: Lage bewerten → schließen ODER Pivot              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Pivot-Regel (NEU — aus Live-Test gelernt)

```
╔═══════════════════════════════════════════════════════════════╗
║  PIVOT — Vom Hedge zum Richtungswechsel                       ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  TRIGGER:                                                    ║
║  → LONG Cert -40% UND SHORT im Plus                          ║
║                                                               ║
║  AKTION:                                                     ║
║  1. LONG sofort schließen (Verlust akzeptieren)              ║
║  2. Erlös in SHORT umschichten (Nachkauf)                    ║
║  3. Ab hier: SHORT = normale Position mit v5-Exit-Regeln     ║
║     → Recovery-Exit bei +15% (konservativer als +20%)        ║
║     → 50% raus bei +15%, Rest Trail auf BE                   ║
║                                                               ║
║  WICHTIG:                                                    ║
║  → Das ist KEIN Hedge mehr — es ist ein Richtungswechsel!    ║
║  → cert_type in DB wechselt von 'hedge' zu 'turbo'          ║
║  → Zählt ab jetzt als normaler Slot (1/3)                    ║
║  → Recovery-Exits (+15%) gelten, NICHT Standard (+20%)       ║
║                                                               ║
║  WARUM -40% UND NICHT FRÜHER:                                ║
║  → Bei -20%: Hedge gerade erst eröffnet, zu früh für Pivot  ║
║  → Bei -30%: Momentum muss sich erst bestätigen              ║
║  → Bei -40%: LONG ist zu weit weg, Recovery unrealistisch    ║
║  → SHORT hat Momentum bewiesen → Richtung klar              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Warum Direct Hedge > Index Hedge

| Kriterium | Index-Hedge (v5) | Direct Hedge (v7) |
|-----------|-------------------|-------------------|
| Basis-Risiko | HOCH — Index ≠ Aktie | **NULL — gleicher Basiswert** |
| Berechenbar | Nein — Korrelation schwankt | **Ja — exakt gegenläufig** |
| Praxis-Test | DAX-Short: -27€ in 1 Tag | ENR-Short: +€13 recovered |
| Timing | Index hat eigene Dynamik | **Direkte Absicherung** |
| Kosten | Spread auf fremdem Instrument | Spread auf bekanntem Instrument |

---

## Warum Direct Hedge > Verkaufen

| Kriterium | Verkaufen | Direct Hedge (v7) |
|-----------|-----------|-------------------|
| These intakt? | Verlust realisiert, Chance weg | **Beide Richtungen offen** |
| Wenn Bounce | Muss neu kaufen (teurer, Spread) | **Long profitiert sofort** |
| Wenn weiter fällt | Verlust begrenzt ✓ | **Short verdient, federt ab** |
| Psychologie | "Verloren" | **"Abgesichert, warte auf Klarheit"** |

---

## v7 Entscheidungsbaum (komplett)

```
Cert -20% vom Einstieg ← EIN Trigger für ALLES
    │
    ├─ v6 Blind Re-Analysis (OHNE Portfolio-Kontext!)
    │   │
    │   ├─ Blind = GEGENTEIL → SOFORT schließen (v6 Regel)
    │   │
    │   ├─ Blind = NEUTRAL → Position halbieren (v6 Regel)
    │   │
    │   └─ Blind = GLEICHE Richtung (These intakt!)
    │       │
    │       ├─ Momentum-Check (mind. 2/3):
    │       │   □ MACD bearish expandierend?
    │       │   □ SMA50 gebrochen?
    │       │   □ Makro-Headwind?
    │       │
    │       ├─ ≥2 erfüllt → DIRECT HEDGE öffnen (v7)
    │       │   → Short-Turbo, gleiches Underlying
    │       │   → Lottery-Size, max = kleinste LONG
    │       │   → KO über Widerstand (>10% über Kurs)
    │       │   → cert_type = 'hedge' in DB
    │       │
    │       └─ <2 erfüllt → Halten mit Stop (v5 Standard)
    │
    ├─ Hedge läuft → Exit-Trigger prüfen (Momentum/Katalysator/Stop/Time)
    │
    ├─ LONG -40% UND SHORT im Plus → PIVOT (siehe Pivot-Regel)
    │   → LONG schließen, Erlös in SHORT
    │   → cert_type wechselt 'hedge' → 'turbo'
    │   → Recovery-Exits: +15% für 50%, Rest Trail
    │
    └─ Cert NICHT bei -20% → kein Hedge, v5/v6 Exits normal
```

---

## DB-Integration

### Neues Feld: `is_hedge`

Hedges werden in `predictions` mit `cert_type = 'hedge'` erfasst.

- **Hedge:** `cert_type = 'hedge'` → zählt NICHT als voller Slot, wird in Win-Rate separat gerechnet
- **Nach Pivot:** `cert_type` wechselt zu `'turbo'` → zählt als normaler Slot
- **Portfolio-Anzeige:** Hedges werden mit `[H]` markiert
- **Track Record:** Hedges separat auswerten (Hedge-P&L vs. Trade-P&L)

### CLI-Befehle

```bash
# Hedge eröffnen (cert_type='hedge')
python prediction_db.py record ENR.DE --direction SHORT --confidence 60 ...
python prediction_db.py open ID --shares 35 --cert-price 2.17 --cert-type hedge

# Pivot (cert_type wechselt)
python prediction_db.py pivot ID   # setzt cert_type von 'hedge' auf 'turbo'

# Portfolio zeigt Hedges separat
python prediction_db.py portfolio   # Hedges mit [H] markiert, nicht als Slot gezählt
```

---

## Erster Live-Test: ENR.DE 26-27.03.2026

| Parameter | Wert |
|-----------|------|
| Long | 56x Turbo KO 136.72 @ €1.968 |
| Short (Hedge) | 35x Turbo KO 170.69 @ ~€2.09 |
| Hedge-Ratio | 62.5% (3.5 von 5.6 Aktien-Äquiv.) |
| Auslöser | Iran-Eskalation, DAX -1.4%, ENR -5.18% |
| These | Intakt (Backlog, Buyback, Triple-Index) |
| Blind-Check | LONG bestätigt (RSI-Div bullish, GC intakt) |

### Ergebnis Live-Test (27.03.2026)

**Tag 1 (26.03):** Hedge eröffnet bei Cert -29% (zu spät! Regel sagt -20%)
**Tag 2 (27.03):** ENR.DE fällt weiter auf €143,75 (-4,61%)
- LONG bei -49,58% geschlossen → **-€52,68 Verlust**
- Erlös (€55,56) komplett in SHORT umgeschichtet (PIVOT)
- SHORT nachgekauft bei +10% → 57 Stk @ avg €2,32
- 50% Take-Profit: 28 Stk @ €2,67 (+15%) → **+€13,04**
- 29 Stk Runner mit BE-Stop → Trail auf €2,50

**Netto bisher:** -€52,68 + €13,04 = **-€39,64** (Runner könnten noch €5-15 bringen)

### Learnings

1. **-20% Trigger einhalten!** Wir haben bei -29% gehedgt statt -20% → €10-15 mehr Verlust als nötig
2. **Pivot bei -40%+ funktioniert:** LONG war nicht mehr zu retten, SHORT hatte Momentum → Umschichtung war richtig
3. **Recovery-Exits konservativer:** +15% statt +20% bei Recovery-Plays. Ziel ist Verlust-Minimierung, nicht Gewinn-Maximierung
4. **Nachkauf im Gewinner:** Bei +10% auf SHORT nachgekauft (aus LONG-Erlös) = Avg gesenkt, Position gestärkt
5. **Bei €6.000 Kapital (April):** Gleicher Fehler (-49%) wäre -€500+. Disziplin beim -20% Trigger ist KRITISCH

---

## Regeln unverändert von v5/v6

- ≥60% Confidence Gate — KEINE Ausnahmen
- Max 3 offene Positionen (Hedge zählt NICHT als voller Slot)
- Max 10% Verlust pro Trade
- Scout/Confirmation Entry (v5)
- 66% Exit bei +20% (v6)
- Blind Re-Analysis bei -20% (v6)
- KO-Distanz ≥2x ATR
- Time-Stops: 3 Tage ohne +5% → halbieren, 5 Tage → Exit

---

## Offene Fragen (beantwortet)

1. ~~Zählt der Hedge als eigener Slot?~~ → **NEIN**, cert_type='hedge' in DB, wird separat gezählt
2. ~~Max Hedge-Dauer?~~ → **5 Tage — HARTE REGEL** (wie v5 Time-Stops)
3. ~~Hedge-Größe fix oder dynamisch?~~ → **Lottery, max = kleinste LONG** (bewährt im Live-Test)
4. Hedge bei BEIDEN offenen Positionen gleichzeitig erlaubt? → Noch offen (braucht Live-Test)
5. ~~Backtesting~~ → Live-Test hat Index-Hedge-Probleme bestätigt

---

## Status: AKTIV

- [x] ENR.DE Live-Test dokumentiert
- [x] Pivot-Regel definiert
- [x] -20% als harter Trigger
- [x] 5-Tage Time-Stop als harte Regel
- [ ] DB-Integration: cert_type='hedge' + pivot-Befehl implementieren
- [ ] Portfolio-Anzeige: Hedges mit [H] markieren
- [ ] Track Record: Hedges separat auswerten
- [ ] 2 weitere Live-Tests für Validierung
