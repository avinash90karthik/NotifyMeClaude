# STEP 2: INVESTMENT DEBATE

**Asset:** {{SYMBOL}}
**Input:** Stichpunkte + 4 Ratings aus Step 1.

---

## Regeln für die Debatte

- Nutze ausschließlich Daten aus Step 1. Keine neuen Zahlen, keine Web-Suchen.
- Die vier Step-1-Ratings (Technical Green-Rate, Price-Action, News+Reddit, Event/Catalyst) sind FIXIERT. Die Debatte darf sie zitieren, interpretieren, kontextualisieren — aber NICHT verändern. Anchoring auf Debatten-Confidence ist der Hauptfehler, den diese Struktur verhindert.
- Debatte liefert nur zwei NEUE Werte: **Chart Structure** (qualitativ, aus Chart-Analyse § 1.4) und **Reversion-Edge** (aus reversion_guard.py, siehe unten).

## Round 1: BULL (4-6 Sätze pro Argument, konkrete Zahlen, Chart-Referenz)

1. **Technical:** Indicator-Context-Werte aus Step 1 zitieren (RSI-Band green-rate, BB, DistHigh), Archetyp einordnen
2. **Price-Action:** Greens-10d, Trend-5d, price_action Verdict
3. **News/Catalysts:** NSI, konkrete Headlines mit Datum, Retail-Flag
4. **Macro:** VIX, F&G, Fed, nur wenn <7d für den Trade relevant

Bull-Ziel: $XX.XX (+XX%) | Confidence: XX% | Horizont: 1-5d

## Round 1: BEAR (4-6 Sätze, muss Bull widerlegen)

Gleicher Aufbau, gegen Bull. Schwachstellen in den Step-1-Daten, nicht Bauchgefühl.

Bear-Ziel: $XX.XX (-XX%) | Confidence: XX% | Horizont: 1-5d

## Round 2: Rebuttals (3-4 Sätze)

Bull widerlegt Bear-Argumente 1-3 + ein neues. Bear widerlegt Bull 1-3 + ein neues.

## Round 3: Final Synthesis (4-6 Sätze)

**Bull Final:** Stärkstes nicht widerlegtes Argument, angepasstes Ziel, Bull-Final-Confidence XX%
**Bear Final:** Stärkstes nicht widerlegtes Argument, angepasstes Ziel, Bear-Final-Confidence XX%

---

## Reversion-Edge vorziehen

Vor dem Scorecard-Fill einmal laufen lassen (Step 3 holt es sich nochmal, aber die Scorecard braucht es hier):

```bash
python3 reversion_guard.py {{SYMBOL}} --direction LONG
python3 reversion_guard.py {{SYMBOL}} --direction SHORT
```

Mapping Verdict → Reversion-Edge-Rating:

| Script-Verdict | LONG-Rating | SHORT-Rating |
|----------------|-------------|--------------|
| LONG "Kein Reversion-Edge" UND SHORT "NO-TRADE" | 6 | 2 |
| LONG "Kein Reversion-Edge" UND SHORT "valid" | 4 | 7 |
| LONG "Pullback-Pflicht" UND SHORT "NO-TRADE" | 3 | 2 |
| LONG "Pullback-Pflicht" UND SHORT "valid" | 2 | 7 |

Interpretation: "Kein Reversion-Edge" LONG bedeutet Continuation-Bias → LONG bekommt Edge. "Pullback-Pflicht" heißt Entry verschoben, aber Richtung intakt — nicht automatisch Edge. SHORT-valid heißt Blowoff-Fade historisch bewiesen → SHORT bekommt Edge.

---

## 6-Achsen Scorecard (MANDATORY)

Vier Achsen (1-4) kommen WÖRTLICH aus Step 1 Rating-Block. Zwei Achsen (5-6) aus Debatte + reversion_guard.

| Criterion (0-10) | LONG | SHORT | Quelle |
|------------------|------|-------|--------|
| 1. Technical Green-Rate | /10 | /10 | Step 1 Rating 1 (unverändert) |
| 2. Price-Action Reality | /10 | /10 | Step 1 Rating 2 (unverändert) |
| 3. News + Reddit Flow | /10 | /10 | Step 1 Rating 3 (unverändert) |
| 4. Event/Catalyst | /10 | /10 | Step 1 Rating 4 (unverändert) |
| 5. Chart Structure | /10 | /10 | Debatte — Pattern, S/R, Volumen-Setup |
| 6. Reversion-Edge | /10 | /10 | reversion_guard.py Verdict |
| **TOTAL** | **/60** | **/60** | |

**Entscheidungsregel:**
- LONG-Total ≥ SHORT+10 → LONG-Setup in Step 3
- SHORT-Total ≥ LONG+10 → SHORT-Setup in Step 3
- Differenz < 10 → beide Setups entwickeln, Step 3 Judge entscheidet
- Beide Totals < 30 → NO-TRADE prüfen

---

## Output-Card (kein JSON)

```
Step 2:
╔════════════════════════════════════════════════════╗
║ SCORECARD — {{SYMBOL}}                             ║
╠════════════════════════════════════════════════════╣
║                              LONG   │   SHORT      ║
║ 1. Technical Green-Rate      X/10   │   X/10       ║
║ 2. Price-Action Reality      X/10   │   X/10       ║
║ 3. News + Reddit Flow        X/10   │   X/10       ║
║ 4. Event/Catalyst            X/10   │   X/10       ║
║ 5. Chart Structure           X/10   │   X/10       ║
║ 6. Reversion-Edge            X/10   │   X/10       ║
║ ─────────────────────────────────── │ ──────       ║
║ TOTAL                       XX/60   │  XX/60       ║
╠════════════════════════════════════════════════════╣
║ Bull-Ziel:   $XX.XX (+XX%) Confidence XX%          ║
║ Bear-Ziel:   $XX.XX (-XX%) Confidence XX%          ║
║ Strongest Bull:  <1 Satz>                          ║
║ Strongest Bear:  <1 Satz>                          ║
║ Recommended:     LONG | SHORT | BOTH | NO-TRADE    ║
╚════════════════════════════════════════════════════╝

[STEP 2 COMPLETE]
```
