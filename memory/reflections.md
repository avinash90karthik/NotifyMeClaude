# Silver Hawk Trading - Reflections

**Generiert:** 12.03.2026 16:32 UTC
**Quelle:** memory/portfolio.md

---

## Performance-Übersicht

| Metrik | Wert |
|--------|------|
| Trades gesamt | 70 |
| Gewinner | 17 |
| Verlierer | 16 |
| Break-Even | 37 |
| **Win-Rate** | **24.3%** |
| Gesamt P&L | +131.47 EUR |
| Avg Win | +56.00 EUR |
| Avg Loss | -51.28 EUR |
| **Risk/Reward** | **1.09** |

---

## Win-Rate nach Richtung

| Richtung | Trades | Wins | Win-Rate | Gesamt P&L | Avg P&L |
|----------|--------|------|----------|------------|---------|
| LONG | 21 | 9 | 42.9% | -294.92 EUR | -14.04 EUR |
| SHORT | 10 | 5 | 50.0% | -41.61 EUR | -4.16 EUR |

---

## Win-Rate nach Konfidenz-Bracket

| Konfidenz | Trades | Wins | Win-Rate | Avg P&L |
|-----------|--------|------|----------|---------|
| 50-59% | 10 | 2 | 20.0% | -18.46 EUR |
| 60-69% | 16 | 6 | 37.5% | -17.11 EUR |
| 70-79% | 3 | 1 | 33.3% | -13.67 EUR |

> **Interpretation:** Trades mit höherer Konfidenz sollten besser performen.
> Wenn 60-69% besser als 70-79% → Overconfidence-Problem.

---

## Pattern-Analyse

| Pattern | Anzahl | Gesamt P&L | Bedeutung |
|---------|--------|------------|-----------|
| 🔴 DISCIPLINE_VIOLATION | 3 | -116.00 EUR | Disziplin-Verstoß (ohne Analyse/Gier) |
| 🔴 STOP_TRIGGERED | 11 | -66.20 EUR | Stop-Loss ausgelöst |
| 🔴 BELOW_GATE | 1 | -32.03 EUR | Trade unter 60% Konfidenz-Gate |
| 🟢 BREAK_EVEN | 6 | +1.00 EUR | Break-Even Exit |
| 🟢 EXECUTION_ERROR | 1 | +6.40 EUR | Ausführungsfehler |
| 🟢 RUNNER | 4 | +15.80 EUR | Runner-Position (Rest nach Teilverkauf) |
| 🟢 V3_PARTIAL_EXIT | 7 | +134.40 EUR | 50% bei +20% verkauft (v3 Regel) |

---

## v3 Compliance

| Metrik | Wert | Status |
|--------|------|--------|
| Teilverkäufe bei +20% | 7 | ✅ |
| Disziplin-Verstöße | 2 | 🔴 |
| Trades unter Gate | 1 | 🔴 |

---

## Schlüssel-Erkenntnisse

- 🔴 **2 Disziplin-Verstöße** kosteten -116.00 EUR — KEINE Trades ohne Analyse!
- 🔴 **1 Trades unter 60% Gate** kosteten -32.03 EUR — Gate ist ABSOLUT!
- 🟢 **7 v3 Teilverkäufe** brachten +134.40 EUR — Kern-Strategie funktioniert!
