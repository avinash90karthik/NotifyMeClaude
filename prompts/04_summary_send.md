# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}
**Input:** Cards aus Step 1, Step 2, Step 3.

---

## 1. DB-Record (PFLICHT — auch bei NO-TRADE)

```bash
python3 prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] \
  --confidence [XX] \
  --entry [XX.XX] \
  --stop [XX.XX] \
  --target [XX.XX] \
  --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] \
  --atr-pct [X.X] \
  --reason "Brief thesis summary (1-2 Sätze, aus Step 3 Reasoning)"
```

**Hart (Rule 18):** `--entry` = Limit-/Trigger-Level aus Step 3 Entry-Plan, NIEMALS der Close. Bei Judge-Override muss der Override-Grund im `--reason` auftauchen.

**Nach User-Bestätigung des Trades:**
```bash
python3 prediction_db.py open ID --shares XX --cert-price XX.XX [--cert-type turbo|warrant|stock]
```

---

## 2. Trading Card (der finale Output für den User)

```
╔══════════════════════════════════════════════════════════════╗
║ {{SYMBOL}} — FINAL                                           ║
╠══════════════════════════════════════════════════════════════╣
║ Signal:          LONG | SHORT | NO-TRADE                     ║
║ Confidence:      XX%   (Scorecard: LONG XX / SHORT XX)       ║
║ Price:           $XX.XX  (EUR XX.XX)                         ║
║ Regime:          TRENDING | RANGE | CHOPPY | TRANSITIONAL    ║
║                                                              ║
║ Judge-Override:  JA | NEIN                                   ║
║   Rating:        <Technical|Price-Action|News|Event>         ║
║   Grund:         <1 Satz — nur bei JA>                       ║
║   Impact:        Scorecard <X> → Judge <Y>                   ║
║                                                              ║
║ Cert:            [ISIN]  |  KO: XX.XX  |  Hebel: ~Xx         ║
║ Stop (mental):   XX.XX (Underlying)                          ║
║                                                              ║
║ Position:        XX% Portfolio = XXX EUR                     ║
║                  Scout XX% / Confirm XX%                     ║
║ Stück @ Limit:   XXX Stück @ €X.XX                           ║
║                                                              ║
║ ─ ENTRY-PLAN ────────────────────────────────────────────    ║
║ 1. LIMIT:        Cert €X.XX  (Stock @ XX.XX)  bis XX:XX      ║
║ 2. ANHEBEN:      Cert €X.XX  (Stock @ XX.XX)  ab XX:XX       ║
║ 3. FALLBACK:     Market nur nach Neubewertung                ║
║                                                              ║
║ Don't-Chase:     Preis aktuell X.X% über Limit → OK|WAIT     ║
║                  (>2% über Limit = WAIT, auf Dip warten)     ║
║ Zeitfenster:     XX:XX Berlin — [OK | nach 22:00: Limit      ║
║                  für morgen, kein Trade heute]               ║
║                                                              ║
║ ─ EXITS (v8) ────────────────────────────────────────────    ║
║ +20% Cert:       80% raus sofort                             ║
║ +30%+ Cert:      Rest mit Trail                              ║
║ Time-Stop:       3d <5% → halbieren  |  5d seitwärts → Exit  ║
║ Overnight/Trump: alles raus                                  ║
║                                                              ║
║ ─ KONTEXT ───────────────────────────────────────────────    ║
║ Reversion-Guard: <Pullback-Pflicht @ X.XX | No-Edge |        ║
║                   SHORT-NO-TRADE>                            ║
║ S:               XX / XX / XX                                ║
║ R:               XX / XX / XX                                ║
║ Nächstes Event:  <Event + Uhrzeit + Klarheit/Unsicherheit>   ║
║                                                              ║
║ V-Vetos aktiv:   keine | V1/V3/...                           ║
║ W-Warnings:      keine | W1/W5/...  → Trade-Plan-Mods        ║
║ Approved:        JA | NEIN                                   ║
║                                                              ║
║ Reasoning:       <2-3 Sätze aus Step 3 — Kern-Thesis>        ║
╚══════════════════════════════════════════════════════════════╝
```

Rationale für die Card-Felder:
- **Don't-Chase** und **Zeitfenster** sind die zwei Einzeiler aus der alten Entry-Timing-Kette, die tatsächlich neuen Wert haben. Rest war Dopplung zu Step 3.
- **Judge-Override** ist verpflichtend sichtbar (CLAUDE.md: User sieht jeden Override).
- **Reversion-Guard-Zeile** zeigt, welcher Entry-Modus gewählt wurde.

---

## 3. Wait for User Confirmation

- Analyse ist mit Status `analysis` in der DB. Noch kein Trade.
- User bestätigt Trade → `prediction_db.py open ID ...`
- User bestätigt v5/v7 Confirmation-Buy → `prediction_db.py confirm ID ...`
- Portfolio-State aktualisiert sich automatisch in der DB.

```
[STEP 4 COMPLETE — ANALYSIS FINISHED]
```
