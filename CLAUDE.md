# Silver Hawk Trading - Project Guide

## Overview

Trading notification system built around a Telegram bot and a multi-agent analysis framework. All notifications, price alerts, and analysis results are delivered via Telegram.

Each user runs their own independent instance: own Telegram bot, own GitHub Actions. No database required — portfolio state lives in `memory/portfolio.md`. See `ONBOARDING.md` (DE) or `ONBOARDING_EN.md` (EN).

---

## TRADING KONTEXT (Silver Hawk)

### Ausgangslage
- **Startkapital:** 957 EUR (Ende Januar 2026)
- **Ziel:** 1.914 EUR (Verdopplung) bis Ende Februar 2026
- **Instrumente:** Turbo-Zertifikate (Knockout-Produkte, Long UND Short)
- **Plattform:** Trade Republic
- **Gehandelte Assets:** Aktien, Rohstoffe (Gold, Silber) - alles via Turbos

### Risk Management Regeln

```
╔═══════════════════════════════════════════════════════════════╗
║  DIESE REGELN GELTEN IMMER - KEINE AUSNAHMEN!                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. Max. Verlust pro Trade:      10% des Portfolios          ║
║  2. Max. gleichzeitig riskiert:  40% des Portfolios          ║
║  3. Max. Sektor-Konzentration:   60% in einem Sektor         ║
║  4. Nach 2 Verlusten in Folge:   Positionsgröße halbieren    ║
║  5. Nach -20% Drawdown:          24h Trading-Pause           ║
║                                                               ║
║  Credentials NIEMALS in committed Files!                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### Analyse-Prinzipien

Die konkreten Trading-Entscheidungen (Entry, Exit, Stop, KO-Abstand) kommen aus der 4-Schritt-Analyse - nicht aus festen Regeln. Die Analyse liefert Support/Resistance, Konfidenz und Positionsgröße pro Trade.

**Kernprinzipien:**
- **Gewinne mitnehmen** wenn die Analyse es zeigt (D-Wave Lektion: waren +30% im Plus, nicht mitgenommen)
- **LONG und SHORT sind gleichwertig** - die Analyse entscheidet die Richtung, nicht ein Bias
- **KO-Berechnung: ATR + Chart kombiniert** - KO liegt IMMER unter dem stärksten Support (LONG) bzw. über Resistance (SHORT). ATR-Multiplikator nach Asset-Klasse (Large Cap 2x, Small Cap 2.5x, Rohstoffe 3x)
- **Time-Stops einhalten** - nach 5 Tagen ohne Bewegung halbieren, nach 8 Tagen raus
- **Korrelation prüfen** - vor jedem neuen Trade Sektor-Konzentration checken
- **Vor Earnings absichern** - min. 50% der Position vor dem Event sichern oder ATR-Multiplikator erhöhen
- **Keine festen EUR-Beträge** - Positionsgröße in % vom Portfolio (skaliert automatisch)

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
- State (prev_prices, alerted_levels) persisted in Supabase `tracker_state` table

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
- Position sizing in % vom Portfolio (5% Mini / 15% Klein / 30% Standard / 20% Ohne Hebel)
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

## Stock Watchlist

Curated watchlist managed via `admin_stocks.py`, updated automatically via GitHub Actions.

### Scripts

**`admin_stocks.py`** - Admin CLI for managing the watchlist.
- `python admin_stocks.py list` - Show all stocks
- `python admin_stocks.py add NVDA "NVIDIA" Technology` - Add a stock
- `python admin_stocks.py remove NVDA` - Deactivate (soft delete)
- `python admin_stocks.py seed` - Seed initial watchlist

**`update_stocks.py`** - Fetches yfinance data and updates Supabase.
- Updates: price, change_pct, RSI, SMA50, SMA200, market_cap, volume, analyst_rating
- Workflow: `.github/workflows/update_stocks.yml` (every 30 min during market hours)

**`browse_stocks.py`** - Read-only watchlist browser.
- `python browse_stocks.py` - Formatted table grouped by sector
- `python browse_stocks.py --json` - JSON output

## GitHub Actions

| Workflow | File | Schedule | Purpose |
|----------|------|----------|---------|
| Stock Updater | `update_stocks.yml` | Every 30 min (market hours) | Update prices, RSI, SMAs |
| Price Tracker | `tracker.yml` | Every 10 min (market hours) | Price alerts via Telegram |
| Portfolio Check | `portfolio_check.yml` | 3x daily (08:00, 15:00, 21:00 CET) | RSI alerts, stop/KO proximity |
| Morning Screener | `morning_screener.yml` | 08:00 CET (weekdays) | LONG/SHORT scoring, top picks |

Secrets needed: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Onboarding

Friends fork the repo and set up their own independent instance. See:
- `ONBOARDING.md` - German setup guide
- `ONBOARDING_EN.md` - English setup guide
- `.env.template` - Environment config template
