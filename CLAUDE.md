# Silver Hawk Trading - Project Guide

## Overview

Trading notification system built around a Telegram bot and a multi-agent analysis framework. All notifications, price alerts, and analysis results are delivered via Telegram.

Each user runs their own independent instance: own Telegram bot, own GitHub Actions. No database required — portfolio state lives in `memory/portfolio.md`. See `ONBOARDING.md` (DE) or `ONBOARDING_EN.md` (EN).

---

## TRADING KONTEXT (Silver Hawk)

### Ausgangslage
- **Startkapital März:** ~1.788 EUR (frisches Kapital eingezahlt, Februar: 957 → 753 EUR / -21.3%)
- **Instrumente:** Turbo-Zertifikate (Knockout-Produkte, Long UND Short)
- **Plattform:** Trade Republic
- **Gehandelte Assets:** Aktien, Rohstoffe (Gold, Silber) - alles via Turbos

### TRADING-STRATEGIE v5 (aktiv ab 18.03.2026)

> Ziel: +15% Baseline / +30% Stretch pro Monat
> Wenn Baseline erreicht → konservativer werden, nicht aggressiver.
> Vollständige v5-Regeln: `memory/strategy_v5_draft.md`

```
╔═══════════════════════════════════════════════════════════════╗
║  KERN-STRATEGIE v5 — IMMER EINHALTEN!                        ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ENTRY (NEU v5):                                             ║
║  1. 60% SCOUT sofort beim Signal                             ║
║  2. 40% BESTÄTIGUNG erst wenn: nächster Tag grün ODER +5%   ║
║  3. Kein Nachkauf wenn Scout >10% im Plus ODER >10% im Minus║
║  4. Event-Trades (Earnings/FOMC): 100% sofort wie v3         ║
║                                                               ║
║  EXITS (v3 + NEU):                                           ║
║  5. 50% bei +20% SOFORT RAUS (v3 Kern-Regel!)               ║
║  6. Rest: Trail-Stop auf BE, dann gestaffelt hochziehen:     ║
║     +30% → Stop +15% / +40% → Stop +25% / +50% → Stop +35% ║
║                                                               ║
║  STOPS (v3 — NICHT gestaffelt!):                             ║
║  7. EIN Stop für alles — KEINE Verhandlung!                  ║
║  8. Stop IMMER beim Kauf setzen — keine Ausnahme             ║
║                                                               ║
║  REGELN (v3):                                                ║
║  9. MAX 3 offene Positionen gleichzeitig                     ║
║  10. ≥60% Konfidenz-Gate — KEINE Ausnahme, auch kein "Lotto"║
║  11. Rücksetzer kommt immer — Geduld zahlt sich aus          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Hedge-System (NEU v3)

```
╔═══════════════════════════════════════════════════════════════╗
║  SITUATIVER HEDGE — 3. Slot als Absicherung                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  WANN HEDGEN:                                                ║
║  • 2 LONG-Positionen offen UND                               ║
║  • Makro-Risiko HOCH (Krieg, FOMC, CPI, Tariffs, Crash)     ║
║  → 3. Slot = Index-SHORT (DAX oder Nasdaq) als Hedge         ║
║                                                               ║
║  HEDGE-REGELN:                                               ║
║  • Größe: Lotto 10% — NIE größer als die kleinste LONG-Pos  ║
║  • Gleiche Exit-Regeln: 50% bei +20%, Rest Trail             ║
║  • Hedge SCHLIESSEN wenn Makro-Risiko sinkt                  ║
║  • DAX SHORT bevorzugt (weniger ATR als Nasdaq, EU-Handel)   ║
║                                                               ║
║  WANN NICHT HEDGEN:                                          ║
║  • Nur 1 LONG offen → 3. Slot für nächsten Trade nutzen     ║
║  • Makro ruhig → Hedge kostet nur Performance                ║
║  • Bereits 50%+ Cash → Cash IST der Hedge                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Bevorzugte Trading-Assets

| Kategorie | Assets | Warum |
|-----------|--------|-------|
| **Rohstoffe** | Silver (SI=F), Gold (GC=F) | Volatil, klare Makro-Treiber, gut zu lesen |
| **Energie/KI** | VST, CEG, ENR.DE | KI-Stromverbrauch wächst strukturell |
| **AI Cloud** | NBIS, APLD | Hyperwachstum, GPU-Infrastruktur |
| **Space/Defense** | RKLB | Hypersonic, Government Contracts |
| **Quantum** | QBTS, APLD-adjacent | Hochspekulativ, nur Mini-Positionen |
| **Europa** | ASML, SAP.DE, ENR.DE | Diversifikation, EUR-denominiert |

### Risk Management v3

```
╔═══════════════════════════════════════════════════════════════╗
║  DIESE REGELN GELTEN IMMER — KEINE AUSNAHMEN!                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. Max. Verlust pro Trade:      10% des Portfolios          ║
║     (zurück von 15% — bei 2 Verlusten = -20%, noch erholbar)║
║  2. Max. gleichzeitig riskiert:  40% des Portfolios          ║
║  3. Max. Sektor-Konzentration:   60% in einem Sektor         ║
║  4. Nach 2 Verlusten in Folge:   Positionsgröße halbieren    ║
║  5. Nach -20% Drawdown:          24h Trading-Pause           ║
║  6. ATR >7%: NUR Lotto/Mini OHNE Hebel                       ║
║  7. KO-Abstand: IMMER ≥2x ATR (Rohstoffe ≥3x ATR)          ║
║                                                               ║
║  Credentials NIEMALS in committed Files!                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### ATR-Messung (Event-adjustiert, NEU v3)

```
╔═══════════════════════════════════════════════════════════════╗
║  ATR-CHECK VOR JEDEM TRADE                                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Basis:    ATR (14) — 14-Tage-Durchschnitt                   ║
║  Event:    ATR (5) — letzte 5 Tage                           ║
║                                                               ║
║  WENN ATR(5) > ATR(14) × 1,5:                               ║
║  → Volatilität ERHÖHT, eine Stufe höher absichern:           ║
║    • Standard → Klein                                        ║
║    • Klein → Lotto                                           ║
║    • Lotto → Kein Trade oder ohne Hebel                      ║
║                                                               ║
║  VOR EARNINGS/EVENTS: IMMER ATR(5) checken!                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Analyse-Prinzipien

Die konkreten Trading-Entscheidungen (Entry, Exit, Stop, KO-Abstand) kommen aus der 4-Schritt-Analyse - nicht aus festen Regeln. Die Analyse liefert Support/Resistance, Konfidenz und Positionsgröße pro Trade.

**Kernprinzipien:**
- **Gestaffelte Exits:** 50% bei +20% raus, Rest Trailing Stop auf Break-Even → Runner-Ziel +40-60%
- **Konfidenz-Gate:** Nur Trades mit ≥60% Konfidenz aus der Analyse — KEINE Ausnahme
- **Gewinne mitnehmen** wenn die Analyse es zeigt (D-Wave Lektion: waren +30% im Plus, nicht mitgenommen)
- **LONG und SHORT sind gleichwertig** - die Analyse entscheidet die Richtung, nicht ein Bias
- **Situativer Hedge** - bei 2 LONGs + hohem Makro-Risiko → 3. Slot als Index-SHORT (DAX bevorzugt)
- **KO-Berechnung: ATR + Chart kombiniert** - KO liegt IMMER unter dem stärksten Support (LONG) bzw. über Resistance (SHORT). ATR-Multiplikator nach Asset-Klasse (Large Cap 2x, Small Cap 2.5x, Rohstoffe 3x)
- **ATR Event-Check** - ATR(5) vs ATR(14) vor jedem Trade. Wenn ATR(5) > ATR(14) × 1,5 → Position eine Stufe kleiner
- **Time-Stops einhalten** - nach 3 Tagen ohne +5% halbieren, nach 5 Tagen raus
- **Korrelation prüfen** - vor jedem neuen Trade Sektor-Konzentration checken
- **Vor Earnings absichern** - min. 50% der Position vor dem Event sichern oder ATR-Multiplikator erhöhen
- **Keine festen EUR-Beträge** - Positionsgröße in % vom Portfolio (skaliert automatisch)
- **Monatsziel darf nicht in Trades drängen** - +15% Baseline reicht, kein FOMO bei Stretch

### Harte Regeln für Analysen

Diese Regeln werden VOR dem Versand jeder Analyse geprüft:

1. **portfolio.md zuerst** - Portfolio-Stand aus `memory/portfolio.md` lesen, BEVOR Schritt 1 beginnt
2. **yfinance = Wahrheit** - Kein Preis, ATR, RSI ohne yfinance-Quelle
3. **Stop-Loss Pflicht** - Jeder Trade braucht einen Stop (mental oder TR)
4. **KO nie erfinden** - KO kommt aus ATR + Chart, nie geschätzt
5. **SHORT = LONG** - Scorecard muss ausgefüllt sein, SHORT-Setup bei Score >= LONG
6. **Keine hardcodierten Wechselkurse** - EUR/USD immer live aus yfinance
7. **Positions-% statt EUR** - Empfehlungen immer in % vom Portfolio
8. **Korrelations-Check** - Sektor-Konzentration gegen 60%-Limit prüfen

### Aktueller Stand
Portfolio (offene/geschlossene Positionen, Cash) lebt in `memory/portfolio.md` — das ist die Single Source of Truth.
Analysen werden per Telegram gesendet. Kein Datenbankzugriff nötig.

---

## Telegram Bot

- Credentials stored in `.env` (never committed to git)
- Each user creates their own bot via @BotFather

### Scripts

**`send_telegram.py`** - Helper module for sending Telegram messages and photos.
- `send_message(text, parse_mode='HTML')` - Send text message
- `send_photo(photo_path, caption='')` - Send photo with optional caption (multipart upload)
- CLI usage: `python send_telegram.py "Your message here"`

## Price Tracker (Personal)

**`tracker_check.py`** - Personal price alert config, runs via GitHub Actions.
- Contains SYMBOLS, ALERT_RULES, and TRADING_ZONES
- State (prev_prices, alerted_levels) persisted in `memory/tracker_state.json`

**`tracker_check_template.py`** - Template for new users to copy and customize.

**`price_tracker.py`** - Local infinite-loop version (gitignored).

### Alert Features
- Flash move: >1.5% change in 5 minutes
- Big daily move: >5% intraday change
- Price level crossings (per-symbol thresholds in `ALERT_RULES`)
- AI Trading Zones with context notes (in `TRADING_ZONES`)
- Silent hourly summaries, loud alerts for dramatic moves

### GitHub Actions
- Workflow: `.github/workflows/tracker.yml`
- Schedule: every 10 min during market hours (08:00-22:00 CET), every 30 min overnight
- Weekdays only

## Multi-Agent Analysis

**Skill:** `/analyse-stock SYMBOL` - runs the full 4-step pipeline automatically.

**Manual:** `Analysiere <SYMBOL> @prompts/00_master.md`

Language defaults to German. Change `{{LANGUAGE}}` in `prompts/00_master.md` for English output.

4-step pipeline in `prompts/`:

| Step | File | Agent Role |
|------|------|-----------|
| 1 | `01_data_collection.md` | yfinance data, chart, news, macro, ATR/volatility, short interest, **correlation check**, **event calendar** |
| 2 | `02_investment_debate.md` | Bull vs Bear debate (2 rounds), **SHORT-Trade Scorecard** |
| 3 | `03_judge_risk.md` | Judge decision + confidence %, **ATR + Chart kombinierte KO-Berechnung**, risk-per-trade check, time-stops |
| 4 | `04_summary_send.md` | Trading card, chart → **Telegram-Versand**, `memory/portfolio.md` aktualisieren |

### Key Analysis Features
- Each analysis produces concrete entry/exit/stop/KO recommendations based on technicals
- **KO = Maximum aus ATR-basiert und Chart-basiert** (immer das weiter entfernte Level)
- **ATR-Multiplikator nach Asset-Klasse:** Large Cap 2.0x, Small/Mid Cap 2.5x, Rohstoffe 3.0x, Krypto 3.0x
- **SHORT-Trades werden gleichwertig bewertet** via LONG vs SHORT Scorecard in Schritt 2
- Position sizing in % vom Portfolio (10% Lotto / 25% Klein / 35% Standard / 20% Ohne Hebel)
- Risk-per-trade capped at 10% Portfolio
- Time-stops: 5 Tage ohne Bewegung → halbieren, 8 Tage → raus
- Correlation check against open positions before each new trade

### Chart Generation

Charts are generated by an external script and sent directly via Telegram:
- Script path in `.env` as `CHART_SCRIPT`
- Output dir in `.env` as `CHART_OUTPUT_DIR`
- Sent as Telegram photo via `send_telegram.py`

## Environment

All secrets and paths are in `.env` (never committed to git):

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_BOT_USERNAME=...
YFINANCE_VENV=...          # Optional: path to python3 in a dedicated venv
CHART_SCRIPT=...            # Optional: path to chart generation script
CHART_OUTPUT_DIR=...        # Optional: path to chart output directory
```

## Morning Screener

**`morning_screener.py`** - Pre-market screener that scans S&P 500 + custom watchlist + futures before market open.
- **Two-phase:** Fast batch `yf.download()` for ~500 symbols, then individual enrichment for top candidates only
- Hard gates: price exists, RSI calculable, volume >= 100k (futures bypass volume/market-cap gates)
- Scoring (0-100) for LONG and SHORT independently: RSI (20), SMA200 trend (15), SMA50 pullback/rejection (15), MACD crossover (15), ATR% volatility (20), analyst rating (10), bonus (5)
- ATR% weighted highest (Turbo leverage needs volatility)
- S&P 500 list fetched from Wikipedia, merged with local watchlist
- SI=F and GC=F always included (futures bypass hard gates)
- Portfolio sector concentration check (60% limit)
- Marks already-owned stocks, flags upcoming earnings
- Workflow: `.github/workflows/morning_screener.yml` (08:00 CET, weekdays, 10 min timeout)

## Watchlist Check

**`watchlist_check.py`** - 2x daily scan of personal watchlist (`memory/watchlist.md`) with v4 scoring.
- Parses `memory/watchlist.md` (Markdown tables) for symbols + sectors + names
- Parses `memory/portfolio.md` for open positions
- Batch `yf.download()` for all ~38 symbols, then individual enrichment for top candidates
- v4 Trend/Momentum scoring identical to morning_screener.py (RSI, MACD, ADX, ATR%, Bollinger, SMA50/200)
- Hard gates relaxed vs morning screener: MIN_SCORE 20, volume 50k (watchlist is pre-curated)
- Shows Top 5 LONG + Top 5 SHORT, portfolio summary, upcoming events
- Stateless — no state file, no git commit needed
- Workflow: `.github/workflows/watchlist_check.yml` (07:30 + 21:15 CET, weekdays, 5 min timeout)

## Reddit Gems Scanner

**`reddit_gems.py`** - Daily scan of Reddit trending stocks via ApeWisdom API.
- Fetches trending tickers from all stock subreddits, enriches top candidates with yfinance
- Filters: min $500M market cap, min 50% mention change, skips ETFs/crypto
- Sends top 8 gems as Telegram summary before European market open
- Workflow: `.github/workflows/reddit_gems.yml` (07:00 CET, weekdays)

## Stock Watchlist

Curated watchlist managed via `admin_stocks.py`, updated automatically via GitHub Actions.

### Scripts

**`admin_stocks.py`** - Admin CLI for managing the watchlist.
- `python admin_stocks.py list` - Show all stocks
- `python admin_stocks.py add NVDA "NVIDIA" Technology` - Add a stock
- `python admin_stocks.py remove NVDA` - Deactivate (soft delete)
- `python admin_stocks.py seed` - Seed initial watchlist

**`update_stocks.py`** - Fetches yfinance data and updates watchlist.
- Updates: price, change_pct, RSI, SMA50, SMA200, market_cap, volume, analyst_rating
- Workflow: `.github/workflows/update_stocks.yml` (every 30 min during market hours)

**`browse_stocks.py`** - Read-only watchlist browser.
- `python browse_stocks.py` - Formatted table grouped by sector
- `python browse_stocks.py --json` - JSON output

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Stock Updater | `update_stocks.yml` | Every 30 min (market hours) | Update prices, RSI, SMAs |
| Watchlist Check | `watchlist_check.yml` | 07:30 + 21:15 CET (weekdays) | Top 5 LONG/SHORT from personal watchlist |
| Portfolio Check | `portfolio_check.yml` | 3x daily (08:00, 15:00, 21:00 CET) | RSI alerts, stop/KO proximity |
| Morning Screener | `morning_screener.yml` | 08:00 CET (weekdays) | LONG/SHORT scoring, top picks |
| Reddit Gems | `reddit_gems.yml` | 07:00 CET (weekdays) | Reddit trending stocks via ApeWisdom |
| Weekly Reflection | `reflect.yml` | Freitag 20:00 CET | Trade-Statistiken, Duration, Patterns |
| ~~Price Tracker~~ | ~~`tracker.yml`~~ | ~~Every 10 min~~ DELETED | Replaced by Watchlist Check |

Secrets needed: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Onboarding

Friends fork the repo and set up their own independent instance. See:
- `ONBOARDING.md` - German setup guide
- `ONBOARDING_EN.md` - English setup guide
- `.env.template` - Environment config template
