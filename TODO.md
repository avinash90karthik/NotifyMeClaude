# Open Follow-Ups

Non-blocking improvements observed during live testing of the new pipeline. Each item is speculative until a real trade exposes it as a gap — don't implement preemptively.

## Prompt / Rule Refinements

### 1. KO-Ausnahme bei Turbo-Hebel
**Context:** HOOD #87 — Chart-KO lag bei 70.43 USD (~19.6% Distanz), ATR-KO bei 77.89 (~10.7%). Bei Turbo mit Hebel 6-8× würde der Chart-KO das Zertifikat 3-4 Monate Theta + Spread fressen lassen, bevor er greift. Judge hat bewusst den engeren ATR-KO gewählt.

**Prompt-Regel aktuell (03_judge_risk.md):** "KO = dasjenige Level, das WEITER vom Preis entfernt ist (ATR-basiert oder Chart-basiert)." Keine Ausnahme.

**Vorschlag:** Ausnahme-Klausel in Step 3 KO-Sektion ergänzen:
> Ausnahme: Wenn Chart-KO >15% vom Preis UND geplanter Hebel ≥6×, wähle ATR-KO (auch wenn näher am Preis). Begründung in der Card-Reasoning zitieren.

**Blocker vor Implementierung:** Einen realen Trade abwarten, bei dem die Regel relevant wird. Sonst Over-Engineering.

---

### 2. Chase-Limit bei Daily-Move > P90 (stock-eigen)
**Context:** HOOD #87 — Daily-Move heute +10.22% = über HOOD's eigenem P90 (+5.48%). Reversion-Guard sagte trotzdem "Kein Reversion-Edge" (weil Fwd-5d-Green-Rate >45%). Aber Entry am Close wäre trotzdem ein Chase. Judge hat manuell auf 85 USD statt 87.17 USD geschnitten.

**Prompt-Regel aktuell (CLAUDE.md Rule 18):** Limit-Verschiebung nur wenn Reversion-Guard "Pullback-Pflicht" sagt. Bei "Kein Reversion-Edge" → Close OK.

**Vorschlag:** Zusatz-Klausel in Rule 18 oder `prompts/03_judge_risk.md` Schritt 0:
> Wenn Daily-Move heute > stock-eigenes P90 (aus reversion_guard.py Output) UND Reversion-Guard dennoch "Kein Reversion-Edge" sagt, trotzdem Limit mindestens 0.5×ATR unter Close setzen. Continuation-Bias heißt: nächster Tag geht wahrscheinlich weiter hoch — aber NICHT zwingend gleich am Open. Ein leichter Intraday-Dip ist statistisch normal (70% der Tage Dip >1%, siehe entry_calibration).

**Blocker:** Schwelle (0.5×ATR? Median-Dip? P25-Dip?) empirisch validieren. Erst 2-3 Trades beobachten, dann kalibrieren.

---

### 3. Edge-Window-Breite als 7. Scorecard-Achse (größerer Umbau)
**Context:** HOOD #87 — Confidence 65% (über Gate), aber Event-Cliff erzwingt Exit nach nur 4 Handelstagen (Earnings + FOMC am 28.04). Das ist ein "Discounted LONG" — rechtes Signal, aber wenig Zeit zum Atmen. Scorecard zeigt keine Reduktion, weil Rating 4 (Event/Catalyst) nur den Event-Tag bewertet, nicht die verfügbaren Tage davor.

**Vorschlag:** Neue Achse in Step 2 Scorecard:
> **7. Edge-Window-Breite** (LONG/SHORT /10): verfügbare Handelstage bis harter Event-Cliff oder Time-Stop
> - ≥10 Tage → 8/8 (symmetrisch, Edge-neutral)
> - 5-9 Tage → 6/6
> - 3-4 Tage → 4/4
> - ≤2 Tage → 2/2 (Signal knapp über Gate reicht dann nicht mehr)

**Gegenargument:** Gut möglich, dass das Problem in der Praxis nur bei Earnings-Nähe auftritt und bereits durch W1 (Earnings <5 Tage → KO +0.5×) adressiert ist. 7 Achsen machen die Scorecard zusätzlich komplex.

**Blocker:** 3-5 reale Trades beobachten. Wenn Short-Window-Trades signifikant schlechter performen als Long-Window-Trades mit gleicher Confidence, dann einbauen. Sonst nicht.

---

### 4. Echter Reddit-Scrape statt Google Site-Search
**Context:** HOOD #87 + ENR.DE #86 — Google `site:reddit.com/...` hat beide Male keine direkten Thread-Treffer geliefert. Reddit-Sentiment-Flag wurde aus Barrons-Kontext („Retail Piling In Again") interpoliert. Das ist weich.

**Vorschlag:** Script `reddit_sentiment.py SYMBOL` mit direktem Reddit-API-Call (PRAW) oder Pushshift (falls noch erreichbar). Output:
- Thread-Count letzte 7 Tage in WSB / WSB-Ger / stocks / investing / mauerstrassenwetten
- Top-3 Thread-Titel mit Upvotes
- Sentiment-Flag aus Titel-Keywords (EUPHORIC/BULLISH/NEUTRAL/BEARISH/PANIC/QUIET)

**Blocker:** Reddit-API braucht Auth (PRAW-Setup, Secrets). Pushshift ist unsicher (wurde 2023 gedrosselt). Aufwand für einen sekundären Signal-Input — nicht prioritär.

---

---

## In Beobachtung (live einsetzen, nach N Trades kalibrieren)

### 5. pattern_timeline.py — Kalibrierung nach 5 Live-Trades
**Context:** Neuer Script (ab PR #X) integriert in Step 1 § 1.8a. Liefert Mode-1 Similar-Day + Mode-2 Analog-Match mit AGREEMENT/DIVERGE-Check. Schwellen aktuell: Korrelation ≥0.7, RSI ±7, ATR-Ratio 0.7-1.4, min 10 Analoge.

**Validation-Fragen nach 5 Live-Trades:**
- War Mode-2-Forecast präziser als Mode-1 (kleinerer Fehler vs. tatsächlicher 5d-Return)?
- Haben AGREEMENT-Signale zu besseren Trade-Ergebnissen geführt als DIVERGE-Signale?
- Wie oft wurden Mode-2-Forecasts übersprungen (<10 Analoge)? Falls häufig → Schwellen lockern.
- ±1σ-Range als Entry-Korridor: hilft es beim Fill oder ist es zu konservativ/aggressiv?

**Mögliche Justierungen (nur wenn Evidence dafür):**
- Korrelation 0.7 → 0.65 (mehr Matches, weichere Qualität)
- Min-Sample 10 → 15 (strenger, mehr Skips)
- Feature-Set erweitern: BB-Position, SMA50-Distance im Matching
- Mode-2 explizit in Step 3 Confidence-Adjustment (−5% bei DIVERGE ≥3 Tage)

**Blocker:** 5 Live-Trades mit pattern_timeline-Output abwarten. Davor: kein Tuning.

---

## How to handle this file

- Kein Commit-Zwang — nur wenn tatsächlich ein relevantes Signal aus einem realen Trade kommt
- Vor Implementierung: mindestens 2-3 reale Trades abwarten, um zu sehen ob der Punkt echt greift oder nur theoretisch ist
- Wenn implementiert: Punkt aus dieser Datei streichen und in CLAUDE.md / Prompts verankern
