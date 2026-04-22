# Silver Hawk Trading - Project Guide

## Overview

Trading notification system built around a multi-agent analysis framework. Portfolio state lives in `memory/predictions.db` (single source of truth). See `ONBOARDING.md` for setup instructions.

---

## TRADING STRATEGY v7/v8/v9 (ACTIVE)

> **Full rules:** `memory/strategy_v7_draft.md` (v7 core + hedge + pivot + v8 exits + v9 scout-inversion + oversold-bonus)

### Quick Reference

- **Entry (v9):** Bei Confidence 60-65% → Scout 40% / Confirmation 60% (invertiert). Bei Confidence ≥65% → Scout 60% / Confirmation 40% (klassisch). No follow-up if Scout >10% up/down.
- **Position Sizing:** 60-65% conf → 15% portfolio | 65-70% → 20% | 70%+ → 25%
- **Exit (v8):** 80% at +20% IMMEDIATELY. Rest max +30%. Trump-Events = alles raus
- **Stops:** ONE stop, set at purchase — no negotiating
- **Slots:** MAX 3 open positions (hedge does NOT count as slot)
- **Gate:** ≥60% confidence — NO exceptions
- **Time stops:** 3 days without +5% → halve; 5 days → exit
- **KO:** max(ATR-based, chart-based) — Large Cap 2x, Small/Mid 2.5x, Commodities 3x
- **ATR >7%:** Warrants/options only (no KO certs)
- **Overnight events:** Protect profits before known events (see strategy doc § Overnight-Event-Regel)

For v7 hedge rules, pivot rules, position sizing → `memory/strategy_v7_draft.md`

### Hard Rules for Analyses

1. **pre-flight first** — run `python3 preflight_check.py SYMBOL` BEFORE anything else. Its date/market output is ground truth. Its mandatory searches (Trump/Reddit/day-news) are not optional.
2. **portfolio first** — run `python prediction_db.py portfolio` before step 1 begins
3. **yfinance = truth** — no price, ATR, RSI without yfinance source
4. **Stop-loss mandatory** — every trade needs a stop (mental or broker)
5. **Never invent KO** — KO comes from ATR + chart, never estimated
6. **SHORT = LONG** — scorecard must be filled out, SHORT setup when score >= LONG
7. **No hardcoded exchange rates** — EUR/USD always live from yfinance
8. **Position % instead of currency** — recommendations always in % of portfolio
9. **Correlation check** — sector concentration against 60% limit
10. **Event check** — check for overnight/upcoming macro events BEFORE recommending holds
11. **No mini-analyses** — every analysis runs all 4 steps. Shortened flows are forbidden.
12. **No default direction** — no LONG/SHORT/NO-TRADE bias. Data speaks. Spiegel-Test before finalizing.
13. **Earnings pattern check** — run `python3 earnings_pattern.py SYMBOL` in Step 1. Script auto-skips if earnings >30 days out; runs full historical window analysis if near. **Bei LONG/SHORT-Setup mit Earnings ≤15 Tagen PFLICHT: zusätzlich Trade-Window-Mode** (`--trade-entry N --trade-exit M --same-month`), der den **Interval-Return über das geplante Halte-Window** misst (T-N→T-M, z.B. T-8→T-3), nicht den Backward-Drift zum Earnings-Day. Trade-Window-Adjust ist **Primärquelle**; Backward-Mode-WARNING nur Sekundär-Kontext. Confidence-Abzug/Bonus kommt aus der Script-Ausgabe "CONFIDENCE-ADJUST (Trade-Window)". **Why:** HOOD 20.04.2026 — Backward T-5d→T0 zeigte 30% green (pauschal -5%), real gehaltenes Window T-8→T-3 zeigte 80% green + Ø +1.57% (+3%). Backward misst Drift-zum-Earnings-Day, Trade-Window misst real gehaltenes Interval — das ist die korrekte Metrik für 1-5d Horizon.
14. **Price-action reality check** — MACD/RSI turn signals are NOT bullish triggers on their own. Verify with actual green-day count over last 10 trading days (must be ≥5/10) and relative strength vs S&P on most recent day. Flat price with positive MACD = stabilization, not bounce.
15. **Reddit argument quality** — read the minority's top 3 arguments, not just the majority count. If bears (at a LONG setup) have harder facts than bulls (opinions/targets), that's a contra-signal regardless of 70/30 split.
16. **Indicator context check** — before calling any indicator value "bullish" or "bearish" (RSI level, BB position, distance-to-high, MACD state), run the historical distribution script in `prompts/01_data_collection.md` § 1.4 "Indicator Context Check". The script reports `[SOLID/WEAK/THIN]` sample sizes and Fwd-5d Green-Rate per band. Confidence adjustments come from Green-Rate, not from textbook "overbought = fall" reflexes. Range-stock heuristics are systematically wrong for trend stocks — always prove the direction from this stock's own history, not generic rules.
17. **Horizon 1-5 days only** — user trades turbo-certs in a 1-5 day window. No multi-week setups. "No edge today" is a VALID answer; "come back in 3 weeks" / "wait for T-7 pre-earnings" is FORBIDDEN as a trade recommendation. Earnings-pattern and similar multi-week patterns are RISK warnings, never trade triggers. If today has no 1-5d edge → signal = NO-TRADE, not "defer to later date". **WICHTIG: Earnings-Nähe ist KEIN Skip-Grund — siehe Regel 21.**
18. **Entry-Calibration via Per-Stock Reversion Guard** — bei Confidence ≥60% (Trade-Gate) MUSS `python3 reversion_guard.py SYMBOL --direction LONG|SHORT` laufen, BEVOR Entry/Stop gesetzt werden. Fix-Schwellen wie "RSI>70" oder "Gap>10%" sind VERBOTEN; das Script nutzt die P80/P90-Percentile dieser Aktie + ihre eigene Fwd-5d Green-Rate. Ein Reversion-Trigger feuert nur, wenn beides zutrifft: heute über Stock-Percentile UND historische Fwd-Green-Rate zeigt Mean-Reversion (LONG: <45% = Pullback-Pflicht; SHORT: <45% = Blowoff-Fade valid). Sample <8 = THIN = kein Feuer. **LONG-Verhalten:** Trigger feuert → Limit-Entry ≤ Close − 1×ATR(14). Kein Trigger → Entry am Close OK (Step 1-2 Intraday-Dip-Logik normal). **SHORT-Verhalten:** Trigger feuert → Entry ≥ Close + 1×ATR oder Extension-Bruch-Level. Kein Trigger feuert NIRGENDS → SHORT = NO-TRADE (Continuation-Bias dieser Aktie dominiert). Echte Breakout-Trades mit sauberem Trigger-Level (kein Reversion-Setup) sind Ausnahme. **DB-Record-Regel:** `prediction_db.py record --entry` = Limit-/Trigger-Level, NICHT Close (sonst verliert die Backtest-Auswertung den Trigger, siehe HDD.DE #82). **Why:** NBIS #80 Pullback-Warnung war richtig, Limit war trotzdem zu dicht am Close → Stop bei 1.7 EUR getriggert. Per-Stock statt Lehrbuch: NBIS bei RSI 75 setzt historisch fort (Fwd5 green=64%), HOOD Gaps sind bullish Continuation (green=67-80%), HDD.DE Gaps mean-reverten (green=38%). Textbook-RSI>70 hätte NBIS-LONG fälschlich gebremst und HOOD-SHORT fälschlich erzwungen. **How to apply:** Step 3 "Optimal Entry" → Schritt 0 läuft Script, liest VERDICT, setzt Limit-Level entsprechend, loggt diesen Level als `entry_price`.
19. **Extrem-Oversold-Bonus (v9)** — Wenn `indicator_context.py` am aktuellen RSI-Band <20 zeigt: Fwd-5d Green-Rate ≥65% UND Sample n≥20 [SOLID], dann **+5% Confidence-Bonus**. Dieser Bonus kann Regime-Abzüge (CHOPPY, TRENDING-against-trend) ÜBERSTIMMEN. Bei RSI-Band <15 [SOLID + green ≥70%] → **+8% Bonus** (Kapitulations-Tief-Setup). **Why:** Backtest auf 40 gefüllten Predictions zeigte: 5 Predictions mit Confidence <50% wurden abgelehnt, gingen aber alle 5 in Signalrichtung (Ø +8.82% fwd5d, 100% Accuracy). Gemeinsames Muster: RSI 15-30 oversold nach Crash, aber System-Abzüge ("TRENDING abwärts", "Pattern-Score niedrig") zogen Confidence unter 60% Gate. Bei dieser Aktie-spezifischen Green-Rate von >65% bei Extrem-Oversold ist Mean-Reversion **historisch dominierend** — das muss in die Rechnung. **How to apply:** Step 3 Judge liest `indicator_context.py` RSI-Band-Output. Wenn Bedingung erfüllt, addiert +5% (oder +8% bei <15) auf Raw-Confidence vor dem Gate-Check. Muss in Step-3-Card unter "Judge-Override / Oversold-Bonus" dokumentiert werden. Beispiele aus Backtest: GC=F #14 (Conf 30% → mit +5% = 35%, noch unter Gate, aber näher), CL=F #17 (Conf 40% → +5% = 45%, zukünftige ähnliche Setups schaffen es eher ins Gate).
20. **Scout-Confirmation-Invertierung bei knapper Confidence (v9)** — Die Scout/Confirmation-Aufteilung hängt ab von der Confidence: **60-65% → Scout 40% / Confirmation 60% (invertiert).** **≥65% → Scout 60% / Confirmation 40% (klassisch).** Bei NO-TRADE oder <60% ist die Regel irrelevant. **Why:** Bei knapper Confidence (60-65%) zeigt der Backtest Accuracy nur 56% und Ø-Move +0.33% — quasi Coin-Flip. Kleinerer Initial-Scout (40%) reduziert Schaden bei Fehlsignal. Confirmation-Buy (60%) nach Bestätigung (Scout mind. +5% im Plus) setzt die Hauptgröße zum höheren Preis, aber mit echter Bestätigung. Bei sicheren Setups (≥65% Conf, 60%+ Accuracy) bleibt der klassische größere Scout-Vorlauf. **How to apply:** Step 3 Position-Sizing-Tabelle zeigt Scout/Confirmation-Split abhängig von Confidence. Step 4 Card und Order-Plan dokumentieren welche Variante aktiv ist. Bei Confidence 60-65%: Scout-Order für 40% der Total-Position, Confirmation für 60%. Confirmation-Trigger bleibt wie v7: +5% im Plus ODER klarer Regime-Beweis.
21. **Earnings-Nähe ist KEIN Skip-Grund — Pre-Earnings ist Pattern-Matching-Chance** — Bei Stock-Ideen-Screening und Analyse darf Claude **NIEMALS** einen Kandidaten abwinken mit Begründung "Earnings in X Tagen", "Window geschlossen", "zu nah an Earnings" oder "Haltezeit zu limitiert". **VERBOTEN: Binär-Skip wegen Earnings-Datum.** **PFLICHT:** `python3 earnings_pattern.py SYMBOL` laufen, das per-Stock Pre-Earnings-Verhalten lesen, und als **Confidence-Adjustment** (±5-10%) verwenden — nicht als Gate. Wenn Pre-Earnings historisch BULLISH (green-rate ≥55%, avg>0) → LONG-Edge, **nicht skippen**. Wenn BEARISH (green-rate ≤45%) → SHORT-Setup prüfen ODER LONG mit reduzierter Size. Bei Coin-Flip (45-55%) → normale Analyse ohne Earnings-spezifisches Bias. Haltezeit anpassen (Exit vor Earnings-Day), aber Trade nicht ablehnen. **Why:** Jeder Stock hat eigenes Pre-Earnings-Verhalten — HIMS coin-flip, HOOD historisch spezifisches Muster, RKLB eigenes. Generischer "Earnings nah → skip"-Reflex ist Lehrbuch-Denken und verletzt Regel 16 (per-stock statt generisch). User hat diesen Fehler wiederholt korrigiert (HIMS-Analyse 20.04.2026: HOOD wegen Earnings 28.04. geskippt, RKLB wegen Earnings 07.05. als "Window eng" abgelehnt — beides falsch). **How to apply:** Bei jedem Stock-Screening Earnings-Datum notieren, aber NIE als Skip-Kriterium. Bei Kandidaten mit Earnings <14 Tagen: `earnings_pattern.py` Output in die Ranking-Tabelle aufnehmen (Pre-Earnings green-rate als Spalte), und in Step 3 Confidence-Rechnung als ±5-10% Adjustment dokumentieren. Exit-Plan: Max-Haltezeit 1 Tag vor Earnings, egal welche Position. Earnings-Day selbst = raus (außer explizit Post-Earnings-Play mit separatem Setup).
22. **Entry-Limit-Range statt Punktwert** — Entry-Levels werden NIE als Punkt angegeben ("Limit $89.00"), sondern als **Vola-abgeleitete Range** um ein Center-Level. Formel: `Halbbreite = max(0.25 × ATR, 0.5% × Close, 0.10 EUR)`. Primär-Limit = Center − Halbbreite (optimistisch), Fallback-Limit = Center + Halbbreite (defensiv, +60-90 Min nach Primär). Über Center + 2×Halbbreite = No-Chase, Trade verfällt. DB-Record `--entry` = **Center-Level**, NICHT Primär/Fallback. **Why:** NVDA/SAP-Trades beim Kollegen wurden nicht getriggert weil Punkt-Limits den Markt nur knapp verfehlt haben. Ein Punkt-Limit ist lottery-ticket-artig — die Range fängt die reale Intraday-Noise-Breite ab. Die drei Floor-Werte adressieren: (a) Standard-Vola-Komponente über ATR, (b) Low-ATR-Titel wie SAP wo 0.25×ATR zu eng wäre, (c) Cert/Warrant-Spread-Treppen wo Sub-Cent-Ranges sinnlos sind. **How to apply:** Step 3 Entry-Plan-Card zeigt Center/Primär/Fallback/No-Chase explizit. Step 4 Trading-Card übernimmt die drei Level. Beim Cert-Umrechnen: Stock-Level → Cert-Level interpolieren, beide dokumentieren.
23. **Aktive Cert-Aufforderung auch bei knapp-NO-TRADE** — Bei Signal = LONG/SHORT immer Cert-Aufforderung an User anhängen (Typ, KO-Range, Hebel-Range aus Formel, Ask-Preis, Trade Republic). Bei NO-TRADE mit Confidence 55-59% ("knapp verfehlt") ebenfalls eine **Stand-by-Cert-Aufforderung** mit konkretem Flip-Trigger ("falls morgen X eintritt"). Bei NO-TRADE <55% oder ohne qualitatives Setup: keine Cert-Aufforderung, stattdessen "Kein Setup in Reichweite". **Why:** User soll nicht raten, ob er ein Cert suchen soll. Bei 58% Confidence wie HOOD ist das Setup real — nur eine Metrik kippt es. Stand-by-Cert spart den zweiten Suchlauf, wenn Re-Run morgen Gate öffnet. **How to apply:** Step 4 hat explizite Template-Blöcke für die drei Fälle (LONG/SHORT, knapp-NO-TRADE, klar-NO-TRADE). Hebel-Berechnung siehe Regel 24.

24. **Hebel aus Formel, nicht aus Proxy-Tabelle — target-basiert auf +20% in 1-5d** — Der Hebel-Vorschlag wird IMMER aus der Formel `Hebel ≈ 25 / ATR%` abgeleitet, gerundet auf 0.5er-Schritt, mit Range ±20% (z.B. ATR 3% → Zielhebel 8×, Range 7-10×). Die implizite KO-Distanz = `100 / Hebel` muss zwei Sanity-Checks bestehen: (a) `Hebel × KO-Distanz% ≈ 100` (mathematische Kohärenz), (b) `KO-Distanz ≥ 3× ATR%` (Vola-Puffer gegen normalen -1σ-Tag). Beide Checks MÜSSEN explizit in der Cert-Aufforderung dokumentiert werden. Bei ATR >7% → V1-Veto, keine Turbos, nur Warrants/Options. **Why:** Die alte ATR→Hebel-Mapping-Tabelle (3-5% ATR → 4-6× Hebel) war mathematisch inkonsistent zum KO-Level: bei 2×ATR-KO-Distanz (Large-Cap-Regel `prompts/03_judge_risk.md:65`) ergibt sich natürlicher Hebel 12-15×, nicht 4-6×. User hat das Mismatch bei UNH-Analyse 22.04.2026 aufgedeckt: KO $325 (6% Distanz) passt zu 15×-Cert, Prompt empfahl aber 4-6× — das ist nicht konsistent. Die target-basierte Formel `0.8 × ATR% = realistischer 2-3d-Move` für +20% Cert-Gewinn bindet Hebel an Trade-Horizon 1-5d direkt und produziert automatisch KO-Distanzen mit 3.5-4× ATR Puffer (überlebt -1σ-Tag sicher, vermeidet W3-Warning). **How to apply:** Step 4 Cert-Aufforderung gibt Hebel-Range UND KO-Range aus der Formel aus, plus Sanity-Check-Zeilen. Step 3 Trade-Plan-KO (aus ATR-/Chart-Methode) dient als Referenz-Untergrenze — der gekaufte Cert-KO darf enger sein (höherer Hebel), muss aber den 3×-ATR-Puffer einhalten. Beispiel ATR 3.0% (UNH): Zielhebel 25/3.0 = 8.3× → Range 7-10×, KO-Distanz 10-14% → KO-Range $298-$311 bei Close $346.

### Current State

Portfolio state (positions, cash, P&L) lives in `memory/predictions.db` — single source of truth.
Check with: `python prediction_db.py portfolio`
ALL analyses are recorded (traded or not) for backtesting.

---

## Multi-Agent Analysis

**Invocation:** When user asks to analyze a stock (e.g. "Analysiere PLTR", "Analyze ENR.DE", "PLTR anschauen"):

1. **Run `python3 preflight_check.py SYMBOL` FIRST** — no exceptions. Its output is ground truth.
2. **Echo back the Pre-Flight checklist** (verbatim, with your answers filled in) before Step 1.
3. **Execute all 4 steps** from `prompts/00_master.md` → `prompts/01_…md` → `prompts/04_…md`. Each step must end with its `[STEP N COMPLETE]` marker.
4. **No mini-analyses.** Shortened flows are forbidden. If you cannot run a step (e.g. yfinance unreachable), STOP and tell the user — do not substitute a shorter flow.

There is **no `/analyse-stock` slash command** — the full flow is triggered by natural-language intent plus the hard rules below. The pre-flight script (not a skill file) is what physically enforces the blindspot checks.

### Pre-Flight Script (mandatory first step)

**`preflight_check.py`** — hard-coded ground truth, runs before any analysis.
- `python3 preflight_check.py SYMBOL` — prints real date/weekday/CET-NY time + weekend flag + US/EU market status + price snapshot + yfinance news (last 7 days) + mandatory search queries (Trump Truth Social, Reddit WSB/WSB-Ger/stocks/investing, day news, event calendar) + echo-back checklist
- `python3 preflight_check.py SYMBOL --json` — machine-readable
- **The script's date/market output is THE ground truth.** Never override with web-search guesses.
- **Every search query it prints is MANDATORY.** Trump + Reddit are not optional color, they are pipeline inputs.
- Exits with code 2 if price fetch fails — analysis MUST abort, not fall back to a "mini" version.

### Data Collection Script

**`collect_data.py`** — Automated data collection.
- `python collect_data.py SYMBOL` — Full collection with human-readable + JSON output
- `python collect_data.py SYMBOL --json-only` — JSON only (for piping)
- Collects: price, RSI (delta/divergence/slope), MACD, ATR (event check), ADX, regime, SMA50/200, short interest, S/R, earnings, market status
- Imports shared indicators from `indicators.py`

### Trading Database (Single Source of Truth)

**`prediction_db.py`** — Tracks ALL analyses + portfolio + trades.
- `record SYMBOL --direction LONG --confidence 68 --entry 135.50 --stop 128.00 --target 155.00 --ko 120.00 --reason "..."` — Record analysis
- `open ID --shares 75 --cert-price 2.67 [--cert-type turbo]` — Mark as traded
- `confirm ID --shares 49 --cert-price 2.81` — v5 confirmation buy
- `close ID [--shares N] --exit-price 3.31 [--reason target]` — Partial/full exit
- `portfolio` — Show open positions, cash, closed trades
- `cash AMOUNT` — Set cash balance
- `fill` — Fill real market outcomes (run daily)
- `analyze` — Backtest: traded vs skipped, confidence brackets
- `list [--open|--closed|--analysis]` — Filter by status
- `export` — Export as CSV
- DB file: `memory/predictions.db` (gitignored)

### Pipeline (5 steps including pre-flight)

| Step | File | Purpose |
|------|------|---------|
| 0 | `preflight_check.py` | Date/weekday/market status + yfinance news + mandatory search queries (Trump/Reddit/day-news/events) |
| 1 | `prompts/01_data_collection.md` | Run `collect_data.py`, chart, news, macro, correlation check |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate (2 rounds + synthesis), SHORT scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO calculation, risk audit, trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, prediction DB record, portfolio update |

### Chart Generation

Charts are generated by an external script:
- Script path in `.env` as `CHART_SCRIPT`
- Output dir in `.env` as `CHART_OUTPUT_DIR`

## Environment

All secrets and paths are in `.env` (never committed to git):

```
YFINANCE_VENV=...          # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...            # Optional: path to chart generation script
CHART_OUTPUT_DIR=...        # Optional: path to chart output directory
```

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Prediction Fill | `prediction_fill.yml` | 22:15 CET (weekdays) | Fill real outcomes, analyze prediction quality |

## Dashboard

**`dashboard/`** — Local web dashboard (Flask API + Vite React).

### Setup
```bash
pip install flask flask-cors          # Backend (one-time)
cd dashboard/frontend && npm install  # Frontend (one-time)
bash dashboard/start.sh               # Start dashboard
# → http://localhost:5173
```

### Architecture
```
predictions.db ──┐
  (watchlist +   │   Flask API (:5050)  →  Vite React (:5173)
   portfolio)    │
yfinance (live) ─┤
chart PNGs ──────┘
```

### Tabs

| Tab | Purpose |
|-----|---------|
| Dashboard | Portfolio overview, open positions, P&L, slots |
| Scanner | Combo signal scanner — RSI + MACD + BB combinations with strength scores |
| Chart | 6-month candlestick with SMA50/200, Bollinger, KO zone, stop/entry/target |
| Track Record | P&L timeline, win rate, discipline tracker |
| Hedge | Hedge setup analyzer — RSI zone + short signals for open runners |

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/portfolio` | Portfolio state (positions, cash, slots) |
| `GET /api/predictions?status=` | All analyses, filterable |
| `GET /api/ohlcv/<symbol>` | OHLCV + indicators for charting (15min cache) |
| `GET /api/scan` | Combo signal scan across watchlist |
| `GET /api/hedge-setup/<symbol>` | Hedge analysis for a symbol |
| `GET /api/track-record` | Trade history from close_events |
| `GET /api/collect/<symbol>` | Live technical data (15min cache) |

## Onboarding

Fork the repo and set up your own independent instance. See:
- `ONBOARDING.md` - Setup guide
- `.env.template` - Environment config template
