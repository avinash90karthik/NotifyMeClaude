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
║ Stück @ Center:  XXX Stück @ €X.XX (Center-Level)            ║
║                                                              ║
║ ─ ENTRY-PLAN (Limit-Range) ──────────────────────────────    ║
║ Center:          Stock $XX.XX  (Cert €X.XX)                  ║
║ Halbbreite:      $X.XX  (max(0.25×ATR, 0.5%, 0.10€))         ║
║ 1. PRIMÄR:       Cert €X.XX  (Stock $XX.XX)  bis XX:XX CET   ║
║ 2. FALLBACK:     Cert €X.XX  (Stock $XX.XX)  ab XX:XX CET    ║
║                  (+60-90 Min nach Primär)                    ║
║ 3. NO-CHASE:     Stock > $XX.XX (Center + 2×Halbbreite)      ║
║                  → Trade verfällt, NICHT kaufen              ║
║                                                              ║
║ Don't-Chase:     Preis aktuell X.X% über Fallback → OK|WAIT  ║
║ Zeitfenster:     XX:XX Berlin — [OK | nach 22:00: Limits     ║
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
- **Entry-Plan Range:** drei Ebenen (Primär, Fallback, No-Chase) mit expliziten Stock- UND Cert-Levels. Kein Punkt-Limit mehr.

### Aktive Cert-Aufforderung (PFLICHT — unabhängig vom Signal)

Nach der Trading-Card IMMER eine Cert-Aufforderung an den User anhängen, unabhängig davon ob Signal = LONG / SHORT / NO-TRADE. Unterschied liegt nur in der Tonlage:

### Hebel-Berechnung (target-basiert, PFLICHT)

Ziel: **+20% Cert-Gewinn in 1-5 Tagen**. Der Hebel wird so gewählt, dass ein realistischer Stock-Move das +20%-Ziel trifft — und gleichzeitig ein normaler Gegen-Tag (1× ATR) die Position NICHT ausknockt.

**Formel:**
```
Stock-Move-für-+20% = 0.8 × ATR%     (realistischer 2-3-Tage-Move)
Hebel                = 20 / Stock-Move-für-+20%
                     = 25 / ATR%     (gerundet auf 0.5er-Schritt)

KO-Distanz           = 100 / Hebel   (implizit durch Hebel)
KO-Puffer zu ATR     = KO-Distanz / ATR%   (muss ≥ 3.0 sein)
```

**Tabelle (aus Formel abgeleitet):**

| ATR% | Hebel (Ziel +20% in ~3d) | KO-Distanz ≈ | KO / ATR | Check |
|------|--------------------------|---------------|----------|-------|
| <2% | 12-15× | 7-8% | 3.5-4× | OK |
| 2-3% | 9-12× | 8-11% | 3.5-4× | OK |
| 3-4% | 7-9× | 11-14% | 3.5-4× | OK |
| 4-5% | 5-7× | 14-20% | 3.5-4× | OK |
| 5-7% | 4-5× | 20-25% | 3.5-4× | OK (High-Vola) |
| >7% | — | — | — | V1-Veto: Warrants/Options |

**Warum diese Formel:**
- **0.8× ATR als 2-3d-Move:** ATR ist Daily-True-Range. In 2-3 Tagen kumuliert sich typisch 0.7-1.0× ATR als Netto-Move (nicht 2-3× ATR — das wäre nur bei Extrem-Continuation). 0.8× ist der Median.
- **KO bei 3.5-4× ATR Distanz:** überlebt einen normalen -1σ-Tag (~0.8-1× ATR Gegen-Move) mit Puffer. CLAUDE.md W3-Warning ("KO <2× ATR") ist damit sicher vermieden.
- **Hebel skaliert invers mit ATR:** Low-Vola-Stocks brauchen mehr Hebel um +20% zu erreichen (sonst zu langsam), High-Vola-Stocks brauchen weniger (sonst Stop-Out-Risk).

**Sanity-Check (immer durchführen):**
```
Hebel × KO-Distanz% ≈ 100     (mathematische Kohärenz)
KO-Distanz / ATR%   ≥ 3.0     (Vola-Puffer)
```

Wenn Cert-Auswahl diese zwei Checks verletzt → anderes Cert suchen oder Hebel anpassen.

**Bei Signal = LONG/SHORT (Gate PASS):**
```
► Cert-Aufforderung:
  Bitte such mir ein Cert raus mit:
  - Typ: Turbo-{Long|Short} auf {{SYMBOL}}
  - KO-Range: ${KO-Untergrenze} bis ${KO-Obergrenze}
      (abgeleitet aus Hebel-Formel: KO-Distanz = 100/Hebel)
  - Hebel-Range: {Hebel-low}× bis {Hebel-high}×
      (aus Formel: 25/ATR% = {Zielhebel}×, Range ±20%)
  - Aktueller Ask-Preis (für exakte Stück-Zahl)
  - Verfügbar auf Trade Republic

  Sanity-Check vor Kauf:
  - Hebel × KO-Distanz% ≈ 100?  [JA/NEIN]
  - KO-Distanz ≥ 3× ATR%?        [JA/NEIN]
```

**Bei Signal = NO-TRADE aber knapp (Confidence 55-59%):**
```
► Cert-Aufforderung (Stand-by, falls Bedingungen flippen):
  Gate verfehlt um X%. Wenn morgen {konkreter Trigger} eintritt, wäre Trade aktiv.
  Such vorsorglich ein Cert raus mit:
  - Typ: Turbo-{Long|Short} auf {{SYMBOL}}
  - KO-Range: ${KO-Untergrenze} bis ${KO-Obergrenze}
  - Hebel-Range: {Hebel-low}× bis {Hebel-high}×  (25/ATR% Formel)
  - Aktueller Ask-Preis
  - Verfügbar auf Trade Republic

  Wir warten nicht auf den Cert — nur falls Re-Run morgen PASS gibt.
```

**Bei Signal = NO-TRADE und klar unter Gate (<55%):**
Keine Cert-Aufforderung. Begründung: "Kein Setup in Reichweite." stattdessen.

**Bei Signal = NO-TRADE aber Chart qualitativ gut (z.B. Reversion-Guard SHORT-NO-TRADE bei LONG-Setup, aber Confidence <55%):**
Keine Cert-Aufforderung. Trade ist nicht in Reichweite.

Die Hebel-Formel + Sanity-Checks sind **verpflichtend** — kein freies Ratespiel beim Hebel-Vorschlag.

---

## 3. Wait for User Confirmation

- Analyse ist mit Status `analysis` in der DB. Noch kein Trade.
- User bestätigt Trade → `prediction_db.py open ID ...`
- User bestätigt v5/v7 Confirmation-Buy → `prediction_db.py confirm ID ...`
- Portfolio-State aktualisiert sich automatisch in der DB.

```
[STEP 4 COMPLETE — ANALYSIS FINISHED]
```
