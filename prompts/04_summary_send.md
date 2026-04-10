# STEP 4: SUMMARY & DELIVERY

**Asset:** {{SYMBOL}}

**Input:** ALL previous steps + JSON blocks.

---

## 1. Record Analysis (ALWAYS — even HOLD signals!)

```bash
python prediction_db.py record {{SYMBOL}} \
  --direction [LONG|SHORT] \
  --confidence [XX] \
  --entry [XX.XX] \
  --stop [XX.XX] \
  --target [XX.XX] \
  --ko [XX.XX] \
  --regime [TRENDING|RANGE|CHOPPY|TRANSITIONAL] \
  --atr-pct [X.X] \
  --reason "Brief thesis summary"
```

**After user confirms trade:**
```bash
python prediction_db.py open ID --shares XX --cert-price XX.XX [--cert-type turbo|warrant|stock]
```

## 2. Trading Card (terminal format)

```
{{SYMBOL}} ANALYSIS

Signal: [LONG/SHORT/HOLD] | Confidence: XX%
Price: $XX.XX (EUR XX.XX) | Regime: [REGIME]

Cert: [ISIN] | KO: XX.XX | Hebel: ~Xx
Stop: XX.XX (Underlying)

Position: XX% Portfolio = XXX EUR (Scout XX% / Confirm XX%)
Stück @ Limit: XXX Stk @ €X.XX

═══ ENTRY-PLAN (DATENGETRIEBEN) ═══
1. LIMIT: Cert €X.XX (Stock @ XX.XX) — bis XX:XX
   → Median-Dip X.X%, Tagestief X% nachmittags
2. ANHEBEN: Cert €X.XX (Stock @ XX.XX) — ab XX:XX
3. FALLBACK: Market NUR nach Neubewertung
═══════════════════════════════════

Exits v8: +20% → 80% raus | +30% → Rest Trail
Time-Stop: 3d <5% → ½ | 5d → Exit

S: XX / XX / XX | R: XX / XX / XX

Events: [nächstes Event + Klarheit/Unsicherheit]
Risk: Max XXX EUR | Sector: XX% [OK/WARN]
```

## 3. Detailed Analysis (500-800 words, {{LANGUAGE}})

Structure: Introduction, Technical Situation (include RSI divergence), Fundamentals, News/Catalysts, Risks, Conclusion with action recommendation.

## 4. Entry Timing Recommendation (DATENGETRIEBEN — aus Step 1 + Step 3 ableiten!)

Check the current time:

```python
python3 -c "
from datetime import datetime
import pytz
berlin = pytz.timezone('Europe/Berlin')
now = datetime.now(berlin)
hour = now.hour
print(f'Berlin Time: {now.strftime(\"%H:%M\")}')
print(f'US Market: {\"OPEN\" if 15 <= hour < 22 else \"CLOSED (opens 15:30)\"}')
print(f'EU Market: {\"OPEN\" if 8 <= hour < 17 else \"CLOSED\"}')
"
```

### Entry-Entscheidungskette (ALLE Schritte durchlaufen!)

**Schritt A: Daten aus Step 1 + Step 3 zusammenführen**

| Input | Quelle | Wert |
|-------|--------|------|
| Best Entry Modus | Step 1 `entry_timing.best` | PRE_MARKET / AT_OPEN / FIRST_HOUR_DIP |
| Limit-Preis (Cert) | Step 3 Optimal Entry | €X.XX |
| Limit-Preis (Underlying) | Step 3 Optimal Entry | XX.XX |
| Aktueller Preis | Live | XX.XX |
| Tagestief-Timing | Step 3 (X% nachmittags) | vor/nach 12:00 |
| Overnight Event <24h? | Step 3 W5 | JA/NEIN + wann |
| Confidence | Step 3 | XX% |

**Schritt B: Don't-Chase-Filter**

| Aktueller Preis vs. Limit | Entscheidung |
|---------------------------|-------------|
| Preis ≤ Limit | Execute jetzt mit Limit-Order |
| Preis 0-2% über Limit | Limit-Order setzen, gültig bis Fallback-Zeit |
| Preis >2% über Limit | **WAIT — Don't chase!** Warte auf Dip |

**Schritt C: Event-Filter**

| Bedingung | Entscheidung |
|-----------|-------------|
| Overnight Event in <6h | **KEIN neuer Entry** — warte bis nach Event |
| Event bringt Klarheit (Step 1) + beide Outcomes bullish | Entry OK, aber mit Stop-Management |
| Event bringt Unsicherheit | WARTEN bis nach Event |

**Schritt D: Confidence-Filter**

| Confidence | Entry-Regel |
|------------|------------|
| 60-65% | Limit-Order **PFLICHT** — kein Market Buy |
| 65-70% | Limit bevorzugt, Market nur wenn Dip schon stattgefunden hat |
| 70%+ | Market akzeptabel NUR wenn Preis ≤ P25-Dip-Level |

**Schritt E: Liquiditäts-Filter (nur als letzter Check)**

| Zeit (Berlin) | US Stock | EU Stock |
|--------------|----------|----------|
| Vor 15:30 | Limit für 15:35+ | Markt offen, Limit OK |
| 15:30-16:30 | First-Hour-Dip abwarten wenn Step 1 das sagt | US-Spillover beachten |
| 16:30-22:00 | Beste Liquidität | TR handelt noch |
| Nach 22:00 | **KEIN Trade** — Limit für morgen | **KEIN Trade** |

**Schritt F: Finale Empfehlung**

```
╔═══════════════════════════════════════════════════════════════╗
║  ENTRY-EMPFEHLUNG: [LIMIT / WAIT / MARKET]                  ║
║  Cert: [ISIN] @ €X.XX (Limit) oder WAIT bis XX:XX          ║
║  Stück: XXX (Scout XX% = XXX EUR)                           ║
║  Fallback: Limit anheben auf €X.XX ab XX:XX                 ║
║  Don't-Chase: Preis aktuell X.X% über Limit → [OK/WAIT]    ║
║  Event-Check: [Event] in Xh → [OK/WAIT]                    ║
╚═══════════════════════════════════════════════════════════════╝
```

**Output:** "Execute [LIMIT @ €X.XX / WAIT bis XX:XX / MARKET nur wenn...]" mit Begründung aus den Daten.

**Output:** "Execute [NOW / AT US OPEN / FIRST-HOUR DIP / TOMORROW]" with reasoning.

## 5. Validation Checklist

| # | Check | Value | Status |
|---|-------|-------|--------|
| 1 | portfolio (DB) checked? | | |
| 2 | yfinance data (not web search)? | | |
| 3 | RSI divergence checked? | | |
| 4 | Stop-loss present? | | |
| 5 | KO = MAX(ATR, Chart)? | | |
| 6 | SHORT evaluated (scorecard)? | | |
| 7 | EUR/USD live? | | |
| 8 | Positions in %? | | |
| 9 | Sector <60%? | | |
| 10 | Analysis recorded in DB? (always!) | | |

## 6. Wait for User Confirmation

- Analysis is recorded as `analysis` status
- When user confirms trade → run `open` command
- When user confirms v5 confirmation → run `confirm` command
- Portfolio state auto-updates in DB — no manual file editing

```
[STEP 4 COMPLETE -- ANALYSIS FINISHED]
```
