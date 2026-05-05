# STEP 1: DATA COLLECTION

**Asset:** {{SYMBOL}}

Pre-flight (Step 0) abgeschlossen, Checkliste oberhalb von § 1.1. Falls nicht → STOP.

Ziel: Rohdaten für das LLM zusammenstellen. Keine Verdicts, keine Tags, keine Caps, keine Aggregation. Reasoning ist Aufgabe von Step 2/3.

Run-Output wird gespeichert unter `runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step1_data.md` plus Chart-PNG fü den User. 

---

## 1.1 Portfolio

Vorrausetzung: user muss eingeloggt sein. Wenn der User nicht eingeloggt ist, bitte den User sich einzulogen. 

```bash
pytr portfolio
python3 scripts/ops/prediction_db.py portfolio
```

`pytr` = aktuelle Holdings, Cash, Sektoren.
`prediction_db` = realisierte Trades (Backtest und Doublettenschutz).

Output:
```
Cash: <EUR>
Open positions: <symbol, side, size, sector>
Sector exposure: <sector, % of equity> for each sector with positions
```

Pending-Signal-Tracking (Limit-Orders, die noch nicht gefüllt sind) kommt mit dem DB-Schema-Update — vorerst nicht enthalten.

## 1.2 Preise & Indikatoren

```bash
python3 scripts/analysis/collect_data.py {{SYMBOL}}
```

Skript holt das Maximum an verfügbaren Rohdaten von yfinance und liefert:

```
SYMBOL: {{SYMBOL}}
TIMESTAMP: <ISO + CET>
MARKET_STATUS: PRE | OPEN | POST | CLOSED  (via market_state)

CURRENT:
  price: <native>
  price_source: premarket | live | postmarket | last_close
  change_from_close_pct: <±X.XX>
  prev_close: <X.XX>
  bid / ask: <X.XX> / <X.XX>

OHLCV_DAILY (max available, target ~250 bars / ~1 trading year):
  date | O | H | L | C | Volume
  [Tabelle]

OHLCV_INTRADAY_5MIN (last 5 sessions):
  datetime_CET | O | H | L | C | Volume
  [Tabelle]

OHLCV_INTRADAY_1MIN (last 2 sessions, every 5th bar):
  datetime_CET | O | H | L | C | Volume
  [Tabelle]

KEY_LEVELS:
  52w_high: <X.XX> on <date>
  52w_low:  <X.XX> on <date>
  3m_high:  <X.XX> on <date>
  3m_low:   <X.XX> on <date>
  # Index lookups only — no computed indicators. ATR / SMA / RSI / MACD are
  # the LLM's job in Step 2/3, computed on demand from OHLCV_DAILY.

STOCK_META:
  exchange: <code>
  currency: <code>
  market_cap: <value>
  beta: <value>
  shares_outstanding: <value>
  avg_volume_10d: <value>
  trailing_pe / forward_pe: <values>
  analyst_recommendations_summary: <strongBuy/buy/hold/sell/strongSell counts>

EARNINGS:
  next_date: <date>
  days_until: <N>
  last_4_reports: [date | EPS_estimate | EPS_actual | next_day_return]

YFINANCE_NEWS (last 7-10 items from yfinance .news):
  [date | provider | title | url | summary]
```

Hinweise zu yfinance-Limits (handled by collect_data.py, nicht User-relevant):
- 1m-Bars: nur letzte 7 Tage
- 5m-Bars: nur letzte 60 Tage
- Daily-Bars: keine relevante Begrenzung
- US-Stocks haben separate `preMarketPrice`/`postMarketPrice`-Felder
- DE-Stocks (XETRA) haben Pre-/Post-Trading nur in den Intraday-Bars

## 1.3 Pre-Open / Pre-Market Snapshot

```bash
python3 scripts/analysis/preopen_snapshot.py {{SYMBOL}}
```

Skript-Logik:
- **US-Stocks**: `info.preMarketPrice` + Pre-Market-Range aus 5min-Bars (04:00-15:30 CET)
- **DE-Stocks**: Pre-Trading-Range aus 5min-Bars (08:00-09:00 CET, XETRA pre-trading window)
- Falls Markt offen → Marker `MARKET_OPEN_NO_PREOPEN_DATA`
- Falls keine Pre-Trading-Aktivität → Marker `NO_PREOPEN_TRADING_TODAY`

Output-Format gleich für US und DE (transparent für Step 2/3):

```
PRE_OPEN_SNAPSHOT:
  market: US | DE
  premarket_high: <X.XX>
  premarket_low: <X.XX>
  premarket_volume: <X>
  premarket_last_price: <X.XX>
  gap_vs_prev_close_pct: <±X.XX>
```

Historische Pre-Open-Pattern-Analyse (Pre-Market-Gap → First-Hour-Reaktion → Day-Close) leitet sich aus den `OHLCV_INTRADAY_5MIN`-Bars in § 1.2 ab. Das LLM rekonstruiert das Pattern selbst aus den letzten 5 Sessions, statt es als pre-aggregierte Tabelle zu konsumieren.

## 1.4 Chart

```bash
python3 scripts/analysis/render_chart.py {{SYMBOL}} --run-id {{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}
```

`--run-id` ist erforderlich, wenn das PNG in einen bereits angelegten Run-Folder geschrieben werden soll (Standard-Pipeline-Verhalten). Ohne `--run-id` legt das Skript einen neuen Run-Folder mit eigenem Timestamp an — das produziert einen Parallel-Folder, was die Pipeline durcheinanderbringt. Optional `--no-imessage` falls keine Push-Benachrichtigung gewünscht.

Erzeugt PNG: 60 Daily Bars + Volume-Subplot. Keine SMA-Overlays, keine Annotations, keine Indikator-Overlays (konsistent mit § 1.2 — falls das LLM Bezugspunkte braucht, rechnet es sie aus den Daily Closes). PNG wird ans LLM-Prompt angehängt und parallel via iMessage an User.

Skript-Ziel: `runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step1_chart.png`.

## 1.5 Context (Stock-Specific + Market-Wide)

### Stock-Specific

`YFINANCE_NEWS` (aus § 1.2) liefert bereits 7-10 stabile Items kostenlos. Für die folgenden drei Quellen nutzt das LLM seine WebSearch direkt im Step-1-Prompt — keine separaten Fetch-Skripte.

**News (WebSearch):**
- Query: `"{{SYMBOL}}" news site:reuters.com OR site:bloomberg.com OR site:seekingalpha.com last 7 days`
- 5-10 Items in Rohform übernehmen.

Output:
```
WEB_NEWS_LAST_7D:
  [date | source | title | url | first_paragraph_or_excerpt]
```

**Trump Truth Social (WebSearch):**
- Query: `Trump Truth Social {{SYMBOL}}` und (falls relevant) Sektor-Schlüsselwort.
- Caveat: WebSearch ist nicht autoritativ für Truth Social — false-negatives möglich. Bei kritischer Lage (große Position, Earnings-Woche) zusätzlich manuell prüfen.

Output:
```
TRUMP_HIT: yes | no | uncertain
[falls hit: date | original_text_or_paraphrase | url | confidence: high|medium|low]
```

**Reddit (Bash mit Subreddit-Whitelist + Company-Name)**

Reddit's `/search.json?q={SYMBOL}` liefert für kurze, common-word Tickers (HOOD, AMC, GME, ARM) global trending Müll, weil der Ticker auch normale Wörter ("hood", "arm") matcht und Cashtag-Operator ohne API-Auth ignoriert wird. Workflow:

1. **Per-Subreddit-Suche** auf Trading-Whitelist mit `restrict_sr=on`. Für jedes der vier Whitelist-Subreddits einen Call:
   ```bash
   for sr in wallstreetbets stocks investing options; do
     curl -sA "silver-hawk/1.0" \
       "https://www.reddit.com/r/$sr/search.json?q={{SYMBOL}}&restrict_sr=on&sort=new&t=week&limit=5"
   done
   ```

2. **Company-Name-Fallback** falls < 5 Hits oder Ticker = common-word: zusätzlich global mit Firmen-Name (`Robinhood`, `Palantir`, etc.):
   ```bash
   curl -sA "silver-hawk/1.0" "https://www.reddit.com/search.json?q={{COMPANY_NAME}}&sort=top&t=week&limit=15"
   ```
   Aus dem Ergebnis nur Posts behalten, deren Subreddit in `{wallstreetbets, wallstreetbetsGER, stocks, investing, options, smallstreetbets, dividends, EconomyCharts, CryptoCurrency}` liegt.

3. Kombiniere die Treffer, dedupliziere per `permalink`, sortiere nach `score`.

Output:
```
REDDIT_LAST_7D:
  [post_date | subreddit | upvotes | num_comments | title | url | excerpt]
```

Kein Sentiment-Tag, kein Score, keine Aggregation. Das LLM liest selbst.

### Market-Wide

VIX, DXY, US_10Y und EURUSD kommen direkt aus `collect_data.py` (yfinance liefert sie kostenlos via `^VIX`, `DX-Y.NYB`, `^TNX`, `EURUSD=X`). Block heißt `MACRO_LIVE`:

```
MACRO_LIVE:
  VIX:    <X.X>
  DXY:    <X.XX>
  US_10Y: <X.XX>
  EURUSD: <X.XXXX>
```

CNN F&G, Fed-Termine, CPI, Geopolitical-Triggers via WebSearch im Prompt:

- Query 1: `CNN Fear and Greed Index current value`
- Query 2: `Fed next FOMC meeting date {{current month/year}}`
- Query 3: `latest US CPI release date and value`
- Query 4: `geopolitical events next 7 days deadlines tariffs sanctions central bank decisions`

Output:
```
MACRO_WEB:
  CNN_FG: <X> (<label verbatim>)
  Fed_next_FOMC: <date> (<N> days)
  Last_CPI_release: <date> | <value>

Geopolitical_active_triggers_next_7d:
  [name | status | next_deadline | one-line context]
or: NO_ACTIVE_TRIGGERS
```

## 1.6 Korrelation

Sektor pro offener Position via yfinance (`info.sector` für jedes Symbol). Direkt im Prompt als kleiner Inline-Block, kein separates Skript:

```python
# Wird vom LLM via Bash ausgeführt — ein Aufruf pro offene Position + Kandidat
import yfinance as yf
for sym in [<offene Symbols + {{SYMBOL}}>]:
    print(sym, yf.Ticker(sym).info.get('sector'))
```

Output:
```
Sectors_after_this_trade:
  [sector | new_pct_of_equity]

All_LONG_bias_after_this_trade: <yes/no>
```

Kein Schwellwert, kein Verdict — die Konzentrations-Beurteilung ist Step-3-Aufgabe.

---

## Output für Step 2

Das LLM (Claude Code) schreibt am Ende des Step-1-Runs selbst die folgenden Dateien — keine separate Compose-Logik, keine Pipeline-Plumbing:

```
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step1_data.md
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/step1_chart.png    (vom render_chart.py erzeugt)
runs/{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}/metadata.json
```

`step1_data.md` ist ein zusammenhängender Markdown-Block mit allen Sektions-Outputs (1.1 bis 1.6) — Rohdaten verbatim wie von den Skripten / WebSearch zurückgegeben.

`metadata.json` enthält:
- `run_id` (`{{SYMBOL}}_{{YYYYMMDD}}_{{HHMMSS}}`)
- `started_at`, `completed_at` (ISO UTC)
- `scripts_run` (Liste aller ausgeführten Bash-Befehle)
- `web_searches` (Liste der WebSearch-Queries)
- `symbol`, `cutoff_price`, `market_status`

**Keine Ratings. Keine Verdicts. Keine Caps. Keine Aggregation.**

Step 2 (Investment Debate) debattiert Long-vs-Short direkt auf den Daten und schreibt nach `step2_debate.md`.
Step 3 (Judge) urteilt mit Per-Stock-Conditioning ("ist ein +6% 5d-Move ungewöhnlich für DIESE Aktie in DIESEM Regime?") und entscheidet final, schreibt nach `step3_judgment.md`.

```
[STEP 1 COMPLETE]
```
