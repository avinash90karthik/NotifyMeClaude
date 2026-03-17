# SCHRITT 4: ZUSAMMENFASSUNG & VERSAND

**Asset:** {{SYMBOL}}

---

**Input:** ALLE Outputs der vorherigen Schritte (Daten, Debate, Judge, Risk)
Referenziere die JSON-Blöcke aus Schritt 1, 2 und 3 fuer strukturierte Datenpunkte.

---

## TRADING CARD

```
╔══════════════════════════════════════════════════════╗
║  {{SYMBOL}} ANALYSE                                  ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Preis:     $XX.XX (EUR XX.XX)                       ║
║  Signal:    [LONG / SHORT / HOLD]                    ║
║  Konfidenz: XX%                                      ║
║  ATR:       X.X% ($XX.XX/Tag)                        ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  KO-LEVEL (ATR + Chart kombiniert)                   ║
╠══════════════════════════════════════════════════════╣
║  ATR-basiert:   $XX.XX (Xx ATR, Asset-Klasse: XXX)   ║
║  Chart-basiert: $XX.XX (unter Support $XX.XX)        ║
║  → FINALES KO:  $XX.XX (XX.X% Abstand)              ║
║  → Hebel:       ~Xx                                  ║
║  Stop-Loss:     $XX.XX (mental, ueber KO)            ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  POSITIONS-EMPFEHLUNG (% vom Portfolio)              ║
╠══════════════════════════════════════════════════════╣
║  Lotto (5%):       XXX EUR - [Produkt + KO]         ║
║  Klein (15%):      XXX EUR - [Produkt + KO]         ║
║  Standard (30%):   XXX EUR - [Produkt + KO]         ║
║  Ohne Hebel (20%): XXX EUR - [ETF/ETC/Aktie]        ║
║                                                      ║
║  Max. Verlust bei Stop: XXX EUR (XX% Portfolio)      ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  EXITS (gestaffelt)                                  ║
╠══════════════════════════════════════════════════════╣
║  Sell 1: $XX.XX (XX%) - [Begruendung]               ║
║  Sell 2: $XX.XX (XX%) - [Begruendung]               ║
║  Sell 3: $XX.XX (Rest) - [Stretch-Ziel]             ║
║  Time-Stop: X Tage ohne Bewegung → halbieren        ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  ENTRY-TIMING (datenbasiert!)                        ║
╠══════════════════════════════════════════════════════╣
║  Bester Entry: [PRE-MARKET/FIRST-HOUR DIP/BEI OPEN] ║
║  Pre-Market Win:    XX% | First-Hour: XX% | Open: XX%║
║  Aktuelles Gap:     +X.X%                            ║
║  → [Konkrete Empfehlung mit Uhrzeit]                ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  SUPPORT              │  RESISTANCE                  ║
╠══════════════════════════════════════════════════════╣
║  S1: $XX.XX           │  R1: $XX.XX                  ║
║  S2: $XX.XX           │  R2: $XX.XX                  ║
║  S3: $XX.XX           │  R3: $XX.XX                  ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  RISIKO-CHECK                                        ║
╠══════════════════════════════════════════════════════╣
║  Sektor-Konzentration: XX% [Sektor]  [✅/⚠️]       ║
║  Offene Positionen gleiche Richtung: X  [✅/⚠️]    ║
║  Naechstes Event: [Event] am [Datum]  [✅/⚠️]      ║
║  Risk-Budget verbraucht: XX%  [✅/⚠️]               ║
║                                                      ║
╠══════════════════════════════════════════════════════╣
║  ZEITHORIZONTE                                       ║
╠══════════════════════════════════════════════════════╣
║  Kurzfristig:  [LONG/SHORT/HOLD]                     ║
║  Mittelfristig:[LONG/SHORT/HOLD]                     ║
║  Langfristig:  [LONG/SHORT/HOLD]                     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## AUSFUEHRLICHE ANALYSE ({{LANGUAGE}}, 500-800 Woerter)

**PFLICHT! Minimum 500 Woerter!**

Schreibe eine vollstaendige Analyse mit folgender Struktur:

**1. EINLEITUNG (50-100 Woerter)**
- Aktueller Kontext: Was passiert gerade mit dem Asset?
- Warum ist jetzt ein wichtiger Zeitpunkt fuer eine Analyse?

**2. TECHNISCHE SITUATION (100-150 Woerter)**
- Beschreibe den aktuellen Chart-Zustand
- Wichtige Levels und was sie bedeuten
- Trend-Staerke und -Richtung
- **RSI-Delta und Divergenz-Befund erwaehnen!**
- **Referenziere deine Chart-Beobachtungen!**

**3. FUNDAMENTALE FAKTOREN (100-150 Woerter)**
- Was treibt das Asset fundamental?
- Supply/Demand Situation
- Relevante Makro-Faktoren

**4. NEWS & KATALYSATOREN (100-150 Woerter)**
- Die wichtigsten aktuellen News
- Kommende Events die den Preis bewegen koennten
- Sentiment-Einschaetzung

**5. RISIKEN (50-100 Woerter)**
- Was koennte schiefgehen?
- Was wuerde die These invalidieren?
- **Korrelations-Risiko zu bestehenden Positionen!**

**6. FAZIT & HANDLUNGSEMPFEHLUNG (100-150 Woerter)**
- Klare Empfehlung: Was soll der Trader tun?
- Entry-Strategie
- Risk Management (max. Verlust in EUR und % vom Portfolio)
- Zeithorizont
- **Gewinne mitnehmen!** Gestaffelte Exits einhalten!

---

## CHART HOCHLADEN (PFLICHT!)

**Lies SUPABASE_URL und SUPABASE_ANON_KEY aus der `.env` Datei!**

**1. Chart zu Supabase Storage hochladen:**
```bash
source .env
curl -X POST "${SUPABASE_URL}/storage/v1/object/charts/{{SYMBOL}}_chart.png" \
  -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: image/png" \
  -H "x-upsert: true" \
  --data-binary @${CHART_OUTPUT_DIR}/{{SYMBOL}}_chart.png
```

**2. Chart-URL:**
```
${SUPABASE_URL}/storage/v1/object/public/charts/{{SYMBOL}}_chart.png
```

---

---

## VALIDIERUNG VOR VERSAND (PFLICHT!)

Pruefe JEDEN Punkt bevor du sendest. Bei einem ❌ → STOPP und korrigieren!

| # | Check | Kriterium |
|---|-------|-----------|
| 1 | Portfolio gelesen? | portfolio.md gelesen (Supabase als Fallback) |
| 2 | yfinance-Daten? | Preis, ATR, RSI aus yfinance (nicht Web-Suche) |
| 3 | RSI-Divergenz geprueft? | Delta, Slope und Divergenz-Check ausgefuehrt |
| 4 | Stop-Loss vorhanden? | Jeder Trade hat einen Stop (mental oder TR) |
| 5 | KO berechnet? | KO = MAX(ATR-basiert, Chart-basiert), nicht geschaetzt |
| 6 | SHORT geprueft? | Scorecard ausgefuellt, SHORT-Setup wenn Score >= LONG |
| 7 | Wechselkurs live? | EUR/USD aus yfinance, nicht hardcodiert |
| 8 | Positionen in %? | Empfehlungen in % vom Portfolio, nicht feste EUR |
| 9 | Korrelation OK? | Sektor-Konzentration < 60% nach diesem Trade |
| 10 | Risk-Budget OK? | Max. 10% Verlust pro Trade, 40% gesamt |

Zeige die Checkliste im Output:
✅ oder ❌ pro Punkt, mit konkretem Wert.

---

## TELEGRAM VERSAND (PFLICHT!)

**Sende die Trading Card als Telegram-Nachricht:**

```bash
source .env
python send_telegram.py "$(cat <<'EOF'
🎯 {{SYMBOL}} ANALYSE

Signal: [LONG/SHORT/HOLD] | Konfidenz: XX%
Preis: $XX.XX | KO: $XX.XX (XX.X%)
Stop: $XX.XX | Hebel: ~Xx

Exits: $XX.XX (XX%) → $XX.XX (XX%) → $XX.XX (Rest)
Time-Stop: X Tage

⚠️ Risiko: Max. XXX EUR (XX% Portfolio)
📊 Sektor-Konz.: XX% [Sektor]
📈 RSI-Divergenz: [Bullisch/Bearisch/Keine]
EOF
)"
```

**Wenn Chart vorhanden, auch als Foto senden:**
```bash
python -c "
from send_telegram import send_photo
send_photo('${CHART_OUTPUT_DIR}/{{SYMBOL}}_chart.png', '📊 {{SYMBOL}} Chart')
"
```

---

## PORTFOLIO.MD AKTUALISIEREN (PFLICHT!)

Nach JEDER Analyse: `memory/portfolio.md` aktualisieren.
Das ist die Single Source of Truth fuer den Portfolio-Stand.

- Neue Position? → In "Offene Positionen" eintragen
- Position geschlossen? → In "Geschlossene Trades" verschieben + P&L
- Sektor-Verteilung neu berechnen
- Anstehende Events aktualisieren
- Datum der letzten Aktualisierung updaten

---

## ENFORCEMENT

- ✅ Trading Card mit allen Key-Facts inkl. KO-Methode und Risiko-Check
- ✅ Positions-Empfehlung in % vom Portfolio (nicht feste EUR-Betraege)
- ✅ Minimum 500 Woerter in der Analyse
- ✅ **RSI-Divergenz in Analyse und Telegram erwaehnt**
- ✅ Chart zu Supabase Storage hochladen
- ✅ Telegram-Nachricht mit Trading Card senden (PFLICHT!)
- ✅ Chart als Telegram-Foto senden
- ✅ portfolio.md aktualisieren (PFLICHT!)

```
✅ [SCHRITT 4: ZUSAMMENFASSUNG & VERSAND ABGESCHLOSSEN]
🏁 [ANALYSE KOMPLETT]
```
