# TRADING-STRATEGIE v3 — DRAFT (finale Version Ende März)

> **Status:** Entwurf 08.03.2026 — wird mit März-Learnings finalisiert für April
> **TODO Ende März:** Pre-Trade-Checklist (Top 5) extrahieren

---

## Ziel: +15% Baseline / +30% Stretch pro Monat

> Wenn Baseline (+15%) erreicht → konservativer werden, nicht aggressiver.
> Das Ziel darf NIEMALS in Trades unter dem 60%-Gate drängen.

```
╔═══════════════════════════════════════════════════════════════╗
║  KERN-STRATEGIE v3 — IMMER EINHALTEN!                        ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. 50% bei +20% SOFORT RAUS, Rest Trailing Stop auf BE     ║
║     → Runner-Ziel +40-60% auf die zweite Hälfte             ║
║  2. Rücksetzer abwarten → gleiche oder bessere Position rein ║
║  3. MAX 3 offene Positionen gleichzeitig                     ║
║  4. Stop IMMER beim Kauf setzen — keine Ausnahme             ║
║  5. Rücksetzer kommt immer — Geduld zahlt sich aus           ║
║  6. ≥60% Konfidenz-Gate — KEINE Ausnahme, auch kein "Lotto" ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## NEU v3: HEDGE-SYSTEM

```
╔═══════════════════════════════════════════════════════════════╗
║  SITUATIVER HEDGE — 3. Slot als Absicherung                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  WANN HEDGEN:                                                ║
║  • 2 LONG-Positionen offen UND                               ║
║  • Makro-Risiko HOCH (Krieg, FOMC, CPI, Tariffs, Crash)     ║
║  → 3. Slot = Index-SHORT (DAX oder Nasdaq) als Hedge         ║
║                                                               ║
║  HEDGE-REGELN:                                               ║
║  • Größe: Lotto 10% — NIE größer als die kleinste LONG-Pos  ║
║  • Gleiche Exit-Regeln: 50% bei +20%, Rest Trail             ║
║  • Hedge SCHLIESSEN wenn Makro-Risiko sinkt                  ║
║  • DAX SHORT bevorzugt (weniger ATR als Nasdaq, EU-Handel)   ║
║                                                               ║
║  WANN NICHT HEDGEN:                                          ║
║  • Nur 1 LONG offen → 3. Slot für nächsten Trade nutzen     ║
║  • Makro ruhig → Hedge kostet nur Performance                ║
║  • Bereits 50%+ Cash → Cash IST der Hedge                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Beweis März:** ENR.DE LONG +20% ✅ + HOOD LONG +20% ✅ + DAX SHORT Runner +40% 🔥

---

## Risk Management v3

```
╔═══════════════════════════════════════════════════════════════╗
║  DIESE REGELN GELTEN IMMER — KEINE AUSNAHMEN!                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. Max. Verlust pro Trade:      10% des Portfolios          ║
║     (zurück von 15% — bei 2 Verlusten = -20%, noch erholbar)║
║  2. Max. gleichzeitig riskiert:  40% des Portfolios          ║
║  3. Max. Sektor-Konzentration:   60% in einem Sektor         ║
║  4. Nach 2 Verlusten in Folge:   Positionsgröße halbieren    ║
║  5. Nach -20% Drawdown:          24h Trading-Pause           ║
║  6. ATR >7%: NUR Lotto/Mini OHNE Hebel                       ║
║  7. KO-Abstand: IMMER ≥2x ATR (Rohstoffe ≥3x ATR)          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## NEU v3: ATR-Messung (Event-adjustiert)

```
╔═══════════════════════════════════════════════════════════════╗
║  ATR-CHECK VOR JEDEM TRADE                                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Basis:    ATR (14) — 14-Tage-Durchschnitt                   ║
║  Event:    ATR (5) — letzte 5 Tage                           ║
║                                                               ║
║  WENN ATR(5) > ATR(14) × 1,5:                               ║
║  → Volatilität ERHÖHT, eine Stufe höher absichern:           ║
║    • Standard → Klein                                        ║
║    • Klein → Lotto                                           ║
║    • Lotto → Kein Trade oder ohne Hebel                      ║
║                                                               ║
║  BEISPIEL: MDB am 03.03 — ATR(14) $20, echte Range $94!     ║
║  ATR(14) allein hätte das Risiko MASSIV unterschätzt.        ║
║                                                               ║
║  VOR EARNINGS/EVENTS: IMMER ATR(5) checken!                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Positions-Matrix v3

| Typ | % Portfolio | Wann |
|-----|------------|------|
| **Lotto** | 10% | ATR >5%, Spekulativ, Hedge |
| **Klein** | 25% | Standard-Turbo, Konfidenz 60-68% |
| **Standard** | 35% | Starkes Setup, Konfidenz >68% |
| **Ohne Hebel** | 20% | ATR >7%, Squeeze-Plays, Aktie direkt |

---

## Exit-System v3 (gestaffelt)

```
EXITS — IMMER EINHALTEN:
━━━━━━━━━━━━━━━━━━━━━━━
+20%  → 50% SOFORT verkaufen, Rest Trail auf Break-Even
+40%  → Weitere 30% verkaufen (Runner!)
+60%  → Rest verkaufen oder enger Trail

TIME-STOPS:
━━━━━━━━━━
3 Tage ohne +5% Bewegung  → Position halbieren
5 Tage seitwärts           → Position schließen
Earnings < 2 Tage          → Min. 50% sichern
```

---

## Harte Learnings (eingebrannt)

| # | Learning | Quelle |
|---|---------|--------|
| 1 | **Gewinne mitnehmen!** +20% = RAUS mit 50% | D-Wave Feb, Gold März |
| 2 | **Unter 60% Gate = KEIN Trade** | SI=F SHORT 55% → -32€ |
| 3 | **KO ≥ 2x ATR, Rohstoffe ≥ 3x ATR** | Gold KO 1,38x → -184€ |
| 4 | **ATR >7% = NUR ohne Hebel** | HIMS 7,8%, BE 8,9% |
| 5 | **Stop SOFORT beim Kauf setzen** | NVDA Feb ohne Stop |
| 6 | **Hedge funktioniert situativ** | DAX SHORT +40% neben 2 LONGs |
| 7 | **Post-Earnings ≠ Kaufsignal** | Bodenbildung abwarten |
| 8 | **MIT dem Trend, nicht dagegen** | Analyse entscheidet Richtung |
| 9 | **0€ Cash = 0 Handlungsfreiheit** | Feb-Lesson |
| 10 | **Kern-Strategie funktioniert** | 4x perfekte +20% Exits März |
| 11 | **Monatsziel darf nicht in Trades drängen** | SI=F unter Gate, "Monat retten" |
| 12 | **ATR(5) vor Events checken** | MDB Earnings: ATR 20, Range 94! |

---

## v2 → v3 Änderungen

| Was | v2 | v3 | Warum |
|-----|----|----|-------|
| Monatsziel | +30% fix | +15% Baseline / +30% Stretch | Psycho-Falle vermeiden |
| Max-Loss/Trade | 15% | **10%** | 2 Verluste = -20% statt -30% |
| Hedge | Keiner | Situativer Index-SHORT (3. Slot) | März-Beweis: DAX SHORT +40% |
| ATR-Messung | ATR(14) fix | ATR(14) + ATR(5) Event-Check | MDB Earnings-Crash |
| Learnings | 10 Regeln | 12 Regeln (+Monatsziel, +ATR-Event) | März-Erfahrung |
