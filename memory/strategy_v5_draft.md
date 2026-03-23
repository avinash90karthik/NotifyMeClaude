# Silver Hawk Trading — Strategie v5

> **Status:** Aktiv ab 18.03.2026 — Live-Testing läuft
> **Basis:** Abdullahs Kern-Idee + Claude-Feedback + Kompromiss
> **Ziel:** Verluste drastisch reduzieren, Gewinne voll mitnehmen
> **Kontext:** März-Rest als Live-Test, April-Start mit ~6.000€

---

## KERN-PRINZIP

```
v3: Volle Position rein → Stop → voller Verlust
v5: 60% sofort, 40% bei Bestätigung → Fehl-Trade = 40% weniger Verlust
```

---

## ENTRY IN 2 TRANCHEN

### Phase 1: SCOUT (60% der geplanten Position)

- **Wann:** Beim 4-Schritt-Analyse-Signal (≥60% Konfidenz)
- **Sofort bei Entry:** Limit-Sell für 50% der Scout-Position bei +20% Cert
- **Stop:** Analyse-Stop (ATR + Chart, wie v3)

### Phase 2: BESTÄTIGUNG (restliche 40%)

- **Trigger (einer reicht):**
  - Nächster Handelstag schließt GRÜN (Basiswert, nicht Cert)
  - Position ist +5% im Plus auf Cert-Ebene
  - Neues technisches Signal (Breakout, Volume-Spike, SMA-Reclaim)
- **Wenn keine Bestätigung nach 2 Tagen:**
  - Scout läuft allein weiter mit originalem Stop
  - Kein Nachkauf → nächste Analyse abwarten
- **Bei Bestätigung:**
  - 40% nachkaufen (ggf. anderer Cert-Preis!)
  - Limit-Sell für 50% der Gesamt-Position bei +20% Cert
  - Scout-Stop hochziehen auf Break-Even

### Kein Nachkauf wenn:

- Scout ist >10% im Plus (Entry verpasst, zu teuer)
- Scout ist >10% im Minus (Trade funktioniert nicht wie geplant)
- ATR(5) > ATR(14) × 1,5 (Vola-Spike seit Entry)
- Neues VETO aus Risk-Audit (Slots voll, Sektor >60%)
- Earnings <3 Tage entfernt

### Ausnahme: Event-Trades

- Post-Earnings Dip-Buys, FOMC-Reaktionen = zeitkritisch
- → 100% sofort wie v3 (kein Bestätigungs-Entry)
- → Begründung: Move passiert in 30 Minuten, 60/40 funktioniert nicht

---

## EXIT-REGELN (v5)

### Gewinn-Exits (gestaffelt ab +30%)

| Cert im Plus | Aktion |
|---|---|
| **+10%** | Stop → Break-Even (Scout bei 2 Tranchen) |
| **+20%** | **50% SOFORT verkaufen** (v3 Kern-Regel!) |
| **+30%** | Trail-Stop auf +15% |
| **+40%** | Trail-Stop auf +25% |
| **+50%** | Trail-Stop auf +35% |
| **+60%+** | Trail immer 15% unter aktuellem Hoch |

### Trail-Abstand nach Asset-Typ

| Asset-Typ | Min. Trail-Abstand |
|---|---|
| Large Cap Aktien | 1,5x ATR |
| Mid/Small Cap | 2x ATR |
| Rohstoffe | 2,5x ATR |
| Index | 1,5x ATR |

> Trail NIEMALS enger als 1,5x ATR — sonst triggert Intraday-Noise.

### Verlust-Stop (NICHT gestaffelt!)

```
╔═══════════════════════════════════════════════════════════════╗
║  EIN STOP FÜR ALLES — KEINE VERHANDLUNG!                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Stop kommt aus der 4-Schritt-Analyse:                       ║
║  → ATR-basiert + Chart-Support kombiniert                    ║
║  → Mentaler Stop ÜBER dem KO-Level                           ║
║  → Bei Stop-Trigger: ALLES verkaufen, keine Teile            ║
║                                                               ║
║  Warum KEIN gestaffelter Stop:                               ║
║  1. Turbo-Noise triggert frühe Stufen zu oft                 ║
║  2. Jede Stufe ist ein Punkt zum "Verhandeln"                ║
║  3. MU war -24% vor +20% — gestaffelt hätte verloren         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## POSITIONSGRÖSSEN (v5)

### Konfidenz → Gesamtgröße → Tranchen

| Konfidenz | Gesamt | Scout (60%) | Bestätigung (40%) |
|---|---|---|---|
| 60-65% | Klein 15% | 9% | 6% |
| 65-70% | Standard 20% | 12% | 8% |
| 70%+ | Standard 25% | 15% | 10% |

### Beispiel bei 6.000€ Portfolio (April)

| Konfidenz | Gesamt | Scout | Bestätigung | Max. Verlust* |
|---|---|---|---|---|
| 60-65% | 900€ | 540€ | 360€ | ~108€ (Scout only) / ~180€ (voll) |
| 65-70% | 1.200€ | 720€ | 480€ | ~144€ / ~240€ |
| 70%+ | 1.500€ | 900€ | 600€ | ~180€ / ~300€ |

*Max. Verlust bei -20% Stop auf Cert.

---

## WORST-CASE-SZENARIEN

### A: Scout scheitert sofort (kein Nachkauf)

```
Geplant: 1.200€ | Investiert: 720€ (60% Scout)
Stop: -20% auf Cert | Verlust: -144€ (statt -240€ bei v3)
Ersparnis: 96€ = 40% weniger Verlust
```

### B: Scout + Bestätigung, dann Stop

```
Geplant: 1.200€ | Investiert: 1.200€
Scout auf BE nach Bestätigung
Stop: Scout 0€ + Bestätigung -20% × 480€ = -96€
Gesamt: -96€ (statt -240€ bei v3)
```

### C: Voller Trade läuft (Best Case)

```
Geplant: 1.200€ | Investiert: 1.200€
+20%: 50% verkauft = +120€ gesichert
+40%: Trail auf +25% = mind. +150€
Gesamt: +270€+ (identisch zu v3)
```

---

## V5 vs V3 — VERGLEICH

| Metrik | v3 | v5 |
|---|---|---|
| Entry | 100% auf einmal | 60% sofort, 40% bei Bestätigung |
| Max. Verlust bei Fehl-Trade | 100% der Position | 60% der Position |
| Verlust wenn bestätigt + scheitert | 100% × Stop | Scout BE + 40% × Stop |
| Gewinne mitnehmen | 50% bei +20% | 50% bei +20% (identisch) |
| Trailing Stops | Nur BE | Gestaffelt (+15/+25/+35%) |
| Stop-Verhandlung | 1 Entscheidung | 1 Entscheidung (identisch) |
| Psycho-Effekt bei Verlust | Großer Verlust = Tilt | 40% kleinerer Verlust |
| Gewinn bei vollem Trade | Identisch | ~5% weniger (höherer Avg) |

---

## REGELN DIE VON V3 BLEIBEN

- ≥60% Konfidenz-Gate — KEINE Ausnahme
- Max. 3 offene Positionen gleichzeitig
- Max. 10% Verlust pro Trade
- Max. 40% gleichzeitig riskiert
- Max. 60% Sektor-Konzentration
- KO-Abstand: ≥2x ATR (Rohstoffe ≥3x)
- ATR >7%: NUR ohne Hebel (Aktie direkt OK)
- 50% bei +20% SOFORT raus
- Hedge-System: 3. Slot als Index-SHORT bei 2 LONGs + Makro-Risiko
- After-Hours/Wochenend-Gap-Risiko beachten
- FOMC/Earnings: min. 50% vorher sichern
- Time-Stops: 3 Tage ohne +5% → halbieren, 5 Tage → raus

---

## RISK SCORE KLARSTELLUNG (v5.1, 19.03.2026)

```
╔═══════════════════════════════════════════════════════════════╗
║  yfinance Risk Score (1-10) ist KEIN VETO-Grund!            ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  WARUM: Risk Score misst nur historische Volatilität +       ║
║  Bilanz-Kennzahlen. Er erfasst NICHT:                        ║
║  - Qualitative De-Risking (Meta $15B Backstop)               ║
║  - Strategic Investments (NVIDIA $2B)                         ║
║  - Revenue-Wachstum (479% YoY)                               ║
║  - Analyst Upgrades                                          ║
║                                                               ║
║  PLTR und NBIS haben beide Risk 10/10 — aber PLTR ist       ║
║  eine $370B Firma mit $7B Cash. Der Score ist zu stumpf.     ║
║                                                               ║
║  WAS STATTDESSEN ZÄHLT (echte VETO-Regeln):                 ║
║  V1: ATR >7% → kein Turbo (Aktie direkt OK)                ║
║  V2: CHOPPY + Score <50 → VETO (DAS ist der echte Filter)  ║
║  V3: ≥3 offene Positionen → kein neuer Trade                ║
║  V4: Sektor >60% → Korrelationsrisiko                       ║
║  V5: Drawdown >20% → 24h Pause                              ║
║                                                               ║
║  Risk Score wird DOKUMENTIERT aber nicht als VETO genutzt.   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## POST-FOMC LEARNING (v5.1, 19.03.2026)

```
╔═══════════════════════════════════════════════════════════════╗
║  NACH HAWKISCHEM FOMC: 3-5 TAGE WARTEN!                     ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Gelernt am 19.03.2026 (ENR.DE: -44€ in 1,5h)              ║
║                                                               ║
║  LONG nach hawkisch FOMC:                                    ║
║  → Makro arbeitet GEGEN dich                                 ║
║  → 3-5 Tage warten, technische Signale abwerten (-5%)       ║
║  → "Relative Stärke an 1 Tag" = KEIN nachhaltiges Signal    ║
║                                                               ║
║  SHORT nach hawkisch FOMC:                                   ║
║  → Makro arbeitet MIT dir                                    ║
║  → ABER: RSI-Oversold-Bounce-Risiko beachten                ║
║  → Auf Bounce WARTEN, dann shorten                           ║
║                                                               ║
║  Konfidenz-Adjustment:                                       ║
║  Tag 1-2 nach FOMC: -5% (LONG) / -3% (SHORT)              ║
║  Tag 3-4: -3% / -1%                                         ║
║  Ab Tag 5: 0% / 0%                                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## LIVE-TEST TRACKING (ab 18.03.2026)

| # | Datum | Symbol | Scout | Bestätigt? | Nachkauf | Ergebnis | v3-Vergleich | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | 19.03 | ENR.DE | 183€ (76 Stk, 2,41€) | NEIN (Stop vorher) | NEIN | **-44,56€** | v3 wäre -89€ | Stop 1,83€ nach 1,5h. Post-FOMC Makro überrollte SMA50-Reclaim. **v5 hat Verlust HALBIERT!** |
| 2 | | | | | | | | |
| 3 | | | | | | | | |

**v5.1 Änderungen (19.03.2026):**
- Risk Score (yfinance) KEIN VETO mehr — zu stumpf, erfasst keine qualitativen Faktoren
- Post-FOMC Learning eingebaut: 3-5 Tage warten, Konfidenz-Adjustment nach Tagen
- Nachkauf-Regel klargestellt: AKTUELLER Stand zählt, nicht historischer Tiefpunkt

> Ziel: 10 Trades bis Ende März/Anfang April. Dann v5 evaluieren.
