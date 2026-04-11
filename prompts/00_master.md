# MULTI-AGENT TRADING ANALYSIS

**Asset:** {{SYMBOL}} | **Language:** {{LANGUAGE}} (Default: English)

> **Entry point:** natural-language request ("Analysiere PLTR", "Analyze ENR.DE").
> There is no slash-command skill — enforcement lives in `preflight_check.py` (hard script output)
> and the CLAUDE.md hard rules. Mini-analyses are forbidden: all steps below are mandatory.

## Pipeline

Execute these steps sequentially. Each builds on the previous. **No step may be skipped, no "mini version" allowed.**

| Step | File | Purpose |
|------|------|---------|
| 0 | `preflight_check.py` | Date/weekday/market-status + yfinance news + mandatory search queries (Trump/Reddit/day-news) |
| 1 | `prompts/01_data_collection.md` | Run `python collect_data.py {{SYMBOL}}`, chart, news, macro |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate (2 rounds + synthesis), SHORT scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO calculation, risk audit, trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, prediction DB record |

**Step 0 command:** `python3 preflight_check.py {{SYMBOL}}` — must run FIRST, output must appear in the analysis, checklist must be echoed back with answers.

## Rules (always active)

- **Primary ruleset: `CLAUDE.md`** — aktuellste Quick-Reference (Gate, Exits, KO, Position Sizing, Hard Rules). Bei jedem Analyse-Start kurz gegen CLAUDE.md abgleichen, falls sich Regeln geändert haben.
- Strategy details: `memory/strategy_v7_draft.md` (v7 hedge, pivot, overnight rules)
- Feedback & learnings: `memory/feedback.md`
- Portfolio state: `python prediction_db.py portfolio` (run BEFORE Step 1)
- yfinance = truth for all price data (never web search for prices)
- Every trade needs: entry, stop, KO, exits, time-stop
- No step may be skipped

## ⚠️ PRE-FLIGHT CHECKLIST (wiederkehrende Blindstellen — NICHT überspringen)

Diese vier Fehler sind mehrfach aufgetreten. Vor JEDER Analyse abarbeiten (Detail in `01_data_collection.md` Pre-Flight-Block):

1. **DATUM-CHECK:** Python-Script für echtes Datum + Wochentag + CET/NY-Zeit. "Friday" aus Web-Suche IMMER gegen lokales Datum abgleichen. Bei Wochenende: alle "heute" Events = gestern.
2. **TRUMP-POSTS:** Explizite Web-Suche `Trump Truth Social {{SYMBOL}}` letzte 7 Tage. Besonders bei Defense/AI/Energy/China/Pharma/Tariff. Trump-Post = Strategy-Regel "keine Overnight-Positionen" aktiv.
3. **REDDIT-FLOW:** r/wallstreetbets, r/wallstreetbetsGer, r/stocks, r/investing (+ asset-spezifisch) — Retail-Sentiment-Flag setzen.
4. **NEUTRALITÄT:** Keine Default-Richtung (weder LONG, SHORT noch NO-TRADE). Signal folgt den Daten, nicht Erwartungen. "Spätes Einsteigen" / "R/R nicht perfekt" sind KEINE Gate-Gründe — nur Confidence <60% + Veto-Liste V1-V5. Spiegel-Test: Würde ich bei spiegelbildlichen Daten dieselben Argumente gelten lassen?

## Quality Gate

Before completing Step 4, record the prediction in the database:
```bash
python prediction_db.py record {{SYMBOL}} --direction [LONG|SHORT] --confidence [XX] --entry [XX.XX] --stop [XX.XX] --target [XX.XX] --ko [XX.XX]
```
