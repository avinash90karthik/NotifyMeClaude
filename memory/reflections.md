# Silver Hawk Trading - Reflections

**Generiert:** 19.03.2026 07:37 UTC
**Quelle:** memory/portfolio.md

---

## Performance-Übersicht

| Metrik | Wert |
|--------|------|
| Trades gesamt | 78 |
| Gewinner | 22 |
| Verlierer | 17 |
| Break-Even | 39 |
| **Win-Rate** | **28.2%** |
| Gesamt P&L | +222.73 EUR |
| Avg Win | +50.10 EUR |
| Avg Loss | -51.74 EUR |
| **Risk/Reward** | **0.97** |

---

## Win-Rate nach Richtung

| Richtung | Trades | Wins | Win-Rate | Gesamt P&L | Avg P&L |
|----------|--------|------|----------|------------|---------|
| LONG | 28 | 14 | 50.0% | -144.66 EUR | -5.17 EUR |
| SHORT | 11 | 5 | 45.5% | -100.61 EUR | -9.15 EUR |

---

## Win-Rate nach Konfidenz-Bracket

| Konfidenz | Trades | Wins | Win-Rate | Avg P&L |
|-----------|--------|------|----------|---------|
| 50-59% | 10 | 2 | 20.0% | -18.46 EUR |
| 60-69% | 16 | 8 | 50.0% | +1.04 EUR |
| 70-79% | 3 | 1 | 33.3% | -13.67 EUR |

> **Interpretation:** Trades mit höherer Konfidenz sollten besser performen.
> Wenn 60-69% besser als 70-79% → Overconfidence-Problem.

---

## Pattern-Analyse

| Pattern | Anzahl | Gesamt P&L | Bedeutung |
|---------|--------|------------|-----------|
| 🔴 DISCIPLINE_VIOLATION | 3 | -116.00 EUR | Disziplin-Verstoß (ohne Analyse/Gier) |
| 🔴 STOP_TRIGGERED | 13 | -66.20 EUR | Stop-Loss ausgelöst |
| 🔴 BELOW_GATE | 1 | -32.03 EUR | Trade unter 60% Konfidenz-Gate |
| 🟢 EXECUTION_ERROR | 1 | +6.40 EUR | Ausführungsfehler |
| 🟢 BREAK_EVEN | 10 | +21.36 EUR | Break-Even Exit |
| 🟢 RUNNER | 8 | +95.20 EUR | Runner-Position (Rest nach Teilverkauf) |
| 🟢 V3_PARTIAL_EXIT | 10 | +224.90 EUR | 50% bei +20% verkauft (v3 Regel) |

---

## Trade-Duration

| Metrik | Wert |
|--------|------|
| Trades mit Datums-Info | 15 |
| Durchschnitt | 1.1 Tage |
| Median | 1 Tage |
| Avg Gewinner | 1.0 Tage |
| Avg Verlierer | 1.2 Tage |

> **Empfehlung:** Gewinner laufen ~1.0 Tage → Time-Stop bei 3/5 Tagen sinnvoll.

---

## v3 Compliance

| Metrik | Wert | Status |
|--------|------|--------|
| Teilverkäufe bei +20% | 10 | ✅ |
| Disziplin-Verstöße | 2 | 🔴 |
| Trades unter Gate | 1 | 🔴 |

---

## Schlüssel-Erkenntnisse

- 🔴 **Risk/Reward < 1.0** — Verluste sind größer als Gewinne. Exits zu spät, Stops zu weit.
- 🔴 **2 Disziplin-Verstöße** kosteten -116.00 EUR — KEINE Trades ohne Analyse!
- 🔴 **1 Trades unter 60% Gate** kosteten -32.03 EUR — Gate ist ABSOLUT!
- 🟢 **10 v3 Teilverkäufe** brachten +224.90 EUR — Kern-Strategie funktioniert!
