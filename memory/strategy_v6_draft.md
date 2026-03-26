# Strategy v6 Draft — Risk/Reward Fix + Blind Re-Analysis

> **Status:** DRAFT — needs backtesting against prediction_db
> **Basis:** v5 core + zwei fundamentale Fixes
> **Ziel:** Mathematisch tragbare Win-Rate-Anforderung + Bias-freie Entscheidungen

---

## Problem mit v5

- Gewinne: +20% auf 50% = +10% effektiver Ertrag
- Runner-Realität: Meistens +20% → BE-Stop → 0% auf den Rest
- Tatsächlicher Durchschnittsgewinn: ~5% effektiv
- Verluste: -60% (oder schlimmer bei Turbo-KO)
- Benötigt 6 Gewinner pro Verlust → 86% Win Rate → unrealistisch
- Ergebnis: negative P&L trotz 50% Win Rate

---

## v6 Kern-Änderungen (auf v5 aufbauend)

### 1. Take 66% at +20% (war 50%)

**Begründung aus der Praxis:**
Runner klingen gut, performen aber schlecht. Die Realität:
- Runner erreichen +20%, dann zieht der BE-Stop
- Meistens: Runner läuft zurück zum BE → +0% auf den Rest
- Selten: Runner läuft auf +40%+ weiter

**Effektive Erträge im Vergleich:**

| Szenario | v5 (50% exit) | v6 (66% exit) |
|----------|---------------|---------------|
| +20% erreicht, Runner → BE | 50% × 20% + 50% × 0% = **5%** | 66% × 20% + 34% × 0% = **8.8%** |
| +20% erreicht, Runner → +40% | 50% × 20% + 50% × 40% = **30%** | 66% × 20% + 34% × 40% = **26.8%** |
| +20% erreicht, Runner → +60% | 50% × 20% + 50% × 60% = **40%** | 66% × 20% + 34% × 60% = **33.6%** |

Im realistischen Fall (Runner → BE) fast **Verdoppelung** des effektiven Ertrags.
Im seltenen Best-Case verlierst du nur ~3% Upside — akzeptabel.

### 2. Blind Re-Analysis bei -20% (KERNSTÜCK v6)

**Das Problem:** Analyse hat einen Richtungs-Bias.
- Du hältst LONG → Re-Analysis liest Portfolio → kommt wieder LONG
- Kollege hat kein Portfolio → bekommt SHORT für dasselbe Symbol am nächsten Tag
- Beweis: Symbol X am Freitag LONG für dich, am Montag SHORT für Kollegen
- Die Analyse bestätigt die bestehende Position statt sie objektiv zu prüfen

**Die Lösung: Blind Re-Analysis**

```
╔═══════════════════════════════════════════════════════════════╗
║  BLIND RE-ANALYSIS — BIAS-KILLER                             ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  TRIGGER: Zertifikat -20% vom Einstieg                       ║
║                                                               ║
║  PROZESS:                                                    ║
║  1. STOPP — Keine weitere Aktion ohne Re-Analysis            ║
║  2. Neue Analyse OHNE portfolio.md lesen                     ║
║  3. Prompt: "Analysiere SYMBOL jetzt. Kein Portfolio-Kontext" ║
║  4. Ergebnis = nackte Richtungsentscheidung                  ║
║                                                               ║
║  ENTSCHEIDUNG:                                               ║
║  • Blind-Analyse = GLEICHE Richtung → Halten bis Orig-Stop  ║
║  • Blind-Analyse = GEGENTEIL → SOFORT schließen bei -20%    ║
║  • Blind-Analyse = HOLD/NEUTRAL → Position halbieren         ║
║                                                               ║
║  REGELN:                                                     ║
║  • NIEMALS portfolio.md im Re-Analysis-Prompt referenzieren  ║
║  • NIEMALS "ich halte LONG, soll ich halten?" fragen         ║
║  • IMMER: "Analysiere X, von Null, blind"                    ║
║  • Confidence der Blind-Analyse muss ≥55% sein für Halten   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Technische Umsetzung:**

```bash
# FALSCH (Bias!):
# "Ich halte SYMBOL LONG seit Freitag, -20%. Re-analysiere."
# → liest Portfolio → bestätigt LONG → Bias

# RICHTIG (Blind):
python collect_data.py SYMBOL
# Dann neue Analyse OHNE Portfolio, OHNE Positionskontext:
# "Analysiere SYMBOL. Nur technische Daten. LONG oder SHORT? Keine Portfolio-Info."
```

**Warum das funktioniert:**
- Kein Confirmation Bias — die Analyse weiß nicht, was du hältst
- Objektive Richtungsentscheidung basiert nur auf aktuellen Daten
- Wenn die Richtung kippt, kippt sie für einen Grund
- Hätte in der Praxis funktioniert: Blind-Analyse hätte Richtungswechsel erkannt → Exit bei -20% statt Totalverlust

---

## v6 Exit Rules (komplett)

```
╔═══════════════════════════════════════════════════════════════╗
║  EXITS (v6)                                                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  GEWINN:                                                     ║
║  +20% Cert → 66% RAUS sofort (war 50%)                      ║
║  Rest (34%): Trail-Stop auf BE, dann:                        ║
║    +30% → Stop +15%                                          ║
║    +40% → Stop +25%                                          ║
║    +50% → Stop +35%                                          ║
║                                                               ║
║  VERLUST:                                                    ║
║  -20% Cert → BLIND RE-ANALYSIS (siehe oben)                  ║
║    Blind = gleiche Richtung (≥55%) → halten bis Original-Stop║
║    Blind = Gegenteil → SOFORT schließen                      ║
║    Blind = neutral → halbieren                               ║
║                                                               ║
║  Original-Stop existiert weiter als absoluter Backstop.      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## v6 Blind Re-Analysis Prompt Template

```
Analysiere {{SYMBOL}} — BLIND CHECK

REGELN:
- Lies NICHT portfolio.md
- Du weißt NICHT, ob eine Position offen ist
- Du weißt NICHT, in welche Richtung eine Position läuft
- Entscheide NUR basierend auf aktuellen technischen Daten

FRAGE: Wenn du JETZT von Null eine Position eröffnen müsstest —
LONG oder SHORT? Mit welcher Konfidenz?

Führe collect_data.py aus und bewerte:
1. RSI + Divergenz
2. MACD + Richtung
3. SMA50/200 Trend
4. Regime
5. Support/Resistance

Ergebnis: LONG / SHORT / NEUTRAL + Konfidenz %
```

---

## Math Comparison (aktualisiert)

| Strategie | Eff. Gewinn | Eff. Verlust | Wins per Loss | Min Win Rate |
|-----------|-------------|--------------|---------------|--------------|
| v5 aktuell (Runner → BE) | +5% | -60% | 12x | 92% |
| v5 aktuell (Runner → +40%) | +30% | -60% | 2x | 67% |
| **v6 (66% + Blind, Verlust -20%)** | **+8.8%** | **-20%** | **2.3x** | **70%** |
| v6 Scout-only Fail | +8.8% | -12% | 1.4x | 58% |
| v6 Best Case (Runner +40%) | +26.8% | -20% | 0.7x | 43% |

**Kernaussage:** v6 senkt die benötigte Win Rate von ~92% (v5 Realität) auf ~70% (v6 typisch). Das ist erreichbar.

---

## Position Sizes (v6 — identisch zu v5)

| Konfidenz | Gesamt | Scout (60%) | Confirmation (40%) |
|-----------|--------|-------------|-------------------|
| 60-65% | Small 15% | 9% | 6% |
| 65-70% | Standard 20% | 12% | 8% |
| 70%+ | Standard 25% | 15% | 10% |

---

## v6 Entscheidungsbaum

```
Signal kommt (≥60% Konfidenz)
    │
    ├─ Scout (60%) kaufen
    │   │
    │   ├─ Cert +20% → 66% RAUS, Rest Trail
    │   │   │
    │   │   ├─ Runner → +30%/+40%/+50% → Trail-Stops
    │   │   └─ Runner → BE → +0% auf Rest (aber +8.8% gesichert)
    │   │
    │   ├─ Cert -20% → BLIND RE-ANALYSIS
    │   │   │
    │   │   ├─ Blind = gleiche Richtung (≥55%) → Halten
    │   │   ├─ Blind = Gegenteil → SOFORT RAUS (-20%)
    │   │   └─ Blind = Neutral/Unsicher → HALBIEREN
    │   │
    │   └─ Confirmation-Tag → +40% kaufen (wenn Scout <10% bewegt)
    │
    └─ Kein Signal / <60% → Kein Trade
```

---

## Regeln unverändert von v5

- ≥60% Confidence Gate — KEINE Ausnahmen
- Max 3 offene Positionen gleichzeitig
- Max 10% Verlust pro Trade
- Max 40% gleichzeitig at risk
- Max 60% Sektor-Konzentration
- KO-Distanz: ≥2x ATR (Commodities ≥3x)
- ATR >7%: NUR ohne Hebel
- Hedge-System: 3. Slot als Index-SHORT bei 2 LONGs + Makro-Risiko
- After-Hours/Weekend-Gap-Risiko
- FOMC/Earnings: mindestens 50% vorher sichern
- Time-Stops: 3 Tage ohne +5% → halbieren, 5 Tage → Exit

---

## Offene Fragen für Backtesting

1. Wie oft erreichen Runner tatsächlich +40%+ vs. BE-Rückfall? → prediction_db auswerten
2. Wie oft hätte Blind Re-Analysis bei -20% die Richtung gewechselt? → Simulieren
3. Leverage-Obergrenze: Sollte max 8x Leverage als Regel rein?
4. KO-Distanz an Cert-Verlust-Toleranz koppeln: Wenn -20% Cert = Max-Loss, wie weit muss KO sein?

---

## Status: DRAFT

Nächste Schritte:
- [ ] Backtesting gegen prediction_db (Blind Re-Analysis simulieren)
- [ ] Runner-Statistik aus close_events auswerten
- [ ] 10 Live-Trades tracken (v6 vs. v5 Vergleich)
- [ ] Leverage-Obergrenze evaluieren
