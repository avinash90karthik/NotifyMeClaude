# Strategy v7 Draft — Direct Position Hedge

> **Status:** DRAFT — erster Live-Test 26.03.2026 (ENR.DE)
> **Basis:** v5 core + v6 Blind Re-Analysis + Direct Hedge
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
║  TRIGGER:                                                    ║
║  → Zertifikat -20% vom Einstieg (= gleicher Trigger wie v6!) ║
║                                                               ║
║  WANN (alle müssen erfüllt sein):                            ║
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
║  HEDGE EXIT — 3 klare Trigger                                ║
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
║  ZEIT-STOP FÜR HEDGE:                                        ║
║  → Max 5 Tage offen halten                                   ║
║  → Danach: Lage neu bewerten oder schließen                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Warum Direct Hedge > Index Hedge

| Kriterium | Index-Hedge (v5) | Direct Hedge (v7) |
|-----------|-------------------|-------------------|
| Basis-Risiko | HOCH — Index ≠ Aktie | **NULL — gleicher Basiswert** |
| Berechenbar | Nein — Korrelation schwankt | **Ja — exakt gegenläufig** |
| Praxis-Test | DAX-Short: -27€ in 1 Tag | ENR-Short: läuft (26.03) |
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

## v7 Entscheidungsbaum (erweitert v6)

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
    │       │
    │       └─ <2 erfüllt → Halten mit Stop (v5 Standard)
    │
    └─ Cert NICHT bei -20% → kein Hedge, v5/v6 Exits normal
```

---

## Erster Live-Test: ENR.DE 26.03.2026

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
**Tag 2 (27.03):** ENR.DE fällt weiter auf €145 (-3,78%)
- LONG bei -49,58% geschlossen → **-€52,68 Verlust**
- Erlös (€55,56) komplett in SHORT umgeschichtet
- SHORT nachgekauft bei +10% → 57 Stk @ avg €2,32
- Limit-Sell: 28 Stk @ €2,67 (+15%)

**Pivot-Moment:** Hedge → Full SHORT. Kein Halten beider Seiten mehr.

### Learnings aus Live-Test

1. **-20% Trigger einhalten!** Wir haben bei -29% gehedgt statt -20% → €10-15 mehr Verlust als nötig
2. **Pivot-Regel fehlt in v7:** Wenn LONG -40%+ UND SHORT profitabel → LONG schließen, Erlös in SHORT. Das ist kein Hedge mehr sondern ein Richtungswechsel
3. **Recovery-Exits konservativer:** +15% statt +20% bei Recovery-Plays. Ziel ist Verlust-Minimierung, nicht Gewinn-Maximierung
4. **Nachkauf im Gewinner:** Bei +10% auf SHORT nachgekauft (aus LONG-Erlös) = Avg gesenkt, Position gestärkt
5. **Bei €6.000 Kapital (April):** Gleicher Fehler (-49%) wäre -€500+. Disziplin beim -20% Trigger ist KRITISCH

---

## Regeln unverändert von v5/v6

- ≥60% Confidence Gate
- Max 3 offene Positionen (Hedge zählt NICHT als voller Slot)
- Max 10% Verlust pro Trade
- Scout/Confirmation Entry (v5)
- 66% Exit bei +20% (v6)
- Blind Re-Analysis bei -20% (v6)
- KO-Distanz ≥2x ATR
- Time-Stops: 3 Tage ohne +5% → halbieren, 5 Tage → Exit

---

## Offene Fragen

1. Zählt der Hedge als eigener Slot? → NEIN, er schützt eine bestehende Position
2. Max Hedge-Dauer? → Vorschlag 5 Tage, dann Lage neu bewerten
3. Soll Hedge-Größe fix (Lottery) oder dynamisch (% des Long-Verlusts)?
4. Hedge bei BEIDEN offenen Positionen gleichzeitig erlaubt?
5. Backtesting: Hätte Direct Hedge die DAX-Short-Verluste (-27€) verhindert?

---

## Status: DRAFT

Nächste Schritte:
- [ ] ENR.DE Live-Test dokumentieren (Ergebnis)
- [ ] Vergleich: Direct Hedge P&L vs. "einfach halten" P&L
- [ ] Backtesting: Vergangene Trades → wo hätte v7 gegriffen?
- [ ] Regel finalisieren nach 3 Live-Tests
