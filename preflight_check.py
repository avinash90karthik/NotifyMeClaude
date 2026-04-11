#!/usr/bin/env python3
"""Silver Hawk — Pre-flight check for analyses (MANDATORY FIRST STEP).

Runs BEFORE any analysis begins. Purpose: eliminate the recurring blind spots
that have burned the user multiple times:

    1. Wrong date / weekday ("Friday CPI" while today is Saturday)
    2. Missed Trump Truth Social posts (market manipulator → gap risk)
    3. Missed Reddit retail-sentiment flow
    4. Missed yfinance news (day-news catalyst missed)
    5. Bias toward a default direction (LONG/SHORT/NO-TRADE)

Prints an in-your-face banner with the ground truth (date, market status,
recent news) and a checklist Claude MUST echo back before Step 1.

Usage:
    python3 preflight_check.py SYMBOL
    python3 preflight_check.py SYMBOL --json   # machine-readable

Exit codes:
    0 = OK
    2 = symbol invalid or data fetch failed (analysis MUST abort)
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

try:
    import pytz
except ImportError:
    print("FATAL: pytz not installed. Run: pip install pytz", file=sys.stderr)
    sys.exit(2)

try:
    import yfinance as yf
except ImportError:
    print("FATAL: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(2)


WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def get_date_context():
    """Ground truth for date/time/market — the ONE source Claude must trust."""
    berlin = pytz.timezone("Europe/Berlin")
    ny = pytz.timezone("America/New_York")
    now_b = datetime.now(berlin)
    now_ny = datetime.now(ny)

    wd = now_b.weekday()
    is_weekend = wd >= 5

    # US market: 09:30-16:00 NY = 15:30-22:00 CET (DST-aware via pytz)
    ny_hour = now_ny.hour + now_ny.minute / 60
    us_open = (not is_weekend) and (9.5 <= ny_hour < 16.0)

    # EU (XETRA): 09:00-17:30 Berlin
    b_hour = now_b.hour + now_b.minute / 60
    eu_open = (not is_weekend) and (9.0 <= b_hour < 17.5)

    # "Yesterday" resolves to last trading day (weekend → Friday)
    last_trading_day = now_b - timedelta(days=1)
    while last_trading_day.weekday() >= 5:
        last_trading_day -= timedelta(days=1)

    return {
        "date_cet": now_b.strftime("%Y-%m-%d"),
        "time_cet": now_b.strftime("%H:%M"),
        "weekday_cet": WEEKDAYS_DE[wd],
        "date_ny": now_ny.strftime("%Y-%m-%d"),
        "time_ny": now_ny.strftime("%H:%M"),
        "is_weekend": is_weekend,
        "us_market": "OPEN" if us_open else "CLOSED",
        "eu_market": "OPEN" if eu_open else "CLOSED",
        "last_trading_day": last_trading_day.strftime("%Y-%m-%d (%A)"),
        "yesterday_cet": (now_b - timedelta(days=1)).strftime("%Y-%m-%d"),
    }


def fetch_yfinance_news(symbol, lookback_days=7):
    """Pull recent news from yfinance's free .news field.

    Returns list of {date, title, publisher, link, age_days}, newest first.
    Only items within lookback_days are returned.
    """
    try:
        t = yf.Ticker(symbol)
        raw = t.news or []
    except Exception as e:
        return [], f"yfinance news fetch failed: {e}"

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=lookback_days)
    out = []

    for item in raw:
        # yfinance .news format varies across versions. Normalize both shapes.
        content = item.get("content") if isinstance(item, dict) else None
        if content:
            title = content.get("title") or ""
            publisher = (content.get("provider") or {}).get("displayName") or ""
            link = (content.get("canonicalUrl") or {}).get("url") or ""
            pub_date_str = content.get("pubDate") or content.get("displayTime") or ""
            try:
                pub_dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            except Exception:
                pub_dt = None
        else:
            title = item.get("title", "")
            publisher = item.get("publisher", "")
            link = item.get("link", "")
            ts = item.get("providerPublishTime")
            pub_dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None

        if not title or not pub_dt:
            continue
        if pub_dt < cutoff:
            continue

        age = (now_utc - pub_dt).total_seconds() / 86400
        out.append({
            "date": pub_dt.strftime("%Y-%m-%d %H:%M UTC"),
            "title": title,
            "publisher": publisher,
            "link": link,
            "age_days": round(age, 1),
        })

    out.sort(key=lambda x: x["age_days"])
    return out, None


def fetch_earnings_context(symbol):
    """Check if earnings are near. If yes, flag for full pattern analysis."""
    try:
        t = yf.Ticker(symbol)
        ed = t.get_earnings_dates(limit=20)
        if ed is None or len(ed) == 0:
            return None, None

        import pandas as pd
        now = pd.Timestamp.now(tz="America/New_York")
        future = ed[ed.index > now]
        if len(future) == 0:
            return None, None

        next_ed = future.index.min()
        days = (next_ed - now).days
        return {
            "next_date": next_ed.strftime("%Y-%m-%d"),
            "days_to_earnings": days,
            "near": days <= 30,
            "very_near": days <= 10,
        }, None
    except Exception as e:
        return None, f"Earnings fetch failed: {e}"


def fetch_price_snapshot(symbol):
    """Minimal price snapshot — just enough so Claude knows the ticker is real."""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        hist = t.history(period="5d")
        if hist.empty:
            return None, f"No history for {symbol}"
        price = info.get("currentPrice") or info.get("regularMarketPrice") or float(hist["Close"].iloc[-1])
        prev = info.get("previousClose") or float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        chg = ((price - prev) / prev * 100) if prev else 0.0
        return {
            "price": round(float(price), 2),
            "prev_close": round(float(prev), 2),
            "change_pct": round(chg, 2),
            "currency": info.get("currency", "USD"),
            "name": info.get("shortName") or info.get("longName") or symbol,
        }, None
    except Exception as e:
        return None, f"Price fetch failed: {e}"


def build_search_queries(symbol, date_ctx):
    """Exact search strings Claude must run. No paraphrasing allowed."""
    today = date_ctx["date_cet"]
    return {
        "trump_truth": [
            f'Trump Truth Social "{symbol}"',
            f'Trump "{symbol}" site:truthsocial.com',
            f'"Donald Trump" "{symbol}" tweet OR truth OR post last 7 days',
        ],
        "reddit": [
            f'site:reddit.com/r/wallstreetbets {symbol}',
            f'site:reddit.com/r/wallstreetbetsGer {symbol}',
            f'site:reddit.com/r/stocks {symbol}',
            f'site:reddit.com/r/investing {symbol}',
        ],
        "day_news": [
            f'{symbol} news {today}',
            f'{symbol} stock catalyst today',
            f'{symbol} premarket news',
        ],
        "events": [
            f'economic calendar {today}',
            f'CPI NFP FOMC {date_ctx["last_trading_day"][:10]}',
        ],
    }


def print_banner(symbol, date_ctx, price_snap, price_err, news, news_err, queries, earnings_ctx=None):
    bar = "=" * 72
    print(bar)
    print(f"  PRE-FLIGHT CHECK — {symbol}")
    print(bar)
    print()
    print("  [GROUND TRUTH — DO NOT GUESS, DO NOT PARAPHRASE]")
    print(f"  Datum heute (CET):  {date_ctx['date_cet']}  {date_ctx['weekday_cet']}  {date_ctx['time_cet']}")
    print(f"  Datum heute (NY):   {date_ctx['date_ny']}  {date_ctx['time_ny']}")
    print(f"  Wochenende?         {'JA' if date_ctx['is_weekend'] else 'NEIN'}")
    print(f"  US-Markt:           {date_ctx['us_market']}")
    print(f"  EU-Markt:           {date_ctx['eu_market']}")
    print(f"  Letzter Handelstag: {date_ctx['last_trading_day']}")
    print(f"  Gestern (CET):      {date_ctx['yesterday_cet']}")
    print()

    if date_ctx["is_weekend"]:
        print("  ⚠  ACHTUNG: Wochenende — ALLE 'heute' Events aus Web-Suchen sind GESTERN")
        print("     oder früher. Ein 'CPI Freitag' Ergebnis = bereits passiert, NICHT kommend.")
        print()

    print(bar)
    print(f"  PRICE SNAPSHOT — {symbol}")
    print(bar)
    if price_err:
        print(f"  ERROR: {price_err}")
    else:
        print(f"  {price_snap['name']}")
        print(f"  Price: {price_snap['price']} {price_snap['currency']}  "
              f"Change: {price_snap['change_pct']:+.2f}%  "
              f"(prev close: {price_snap['prev_close']})")
    print()

    print(bar)
    print(f"  EARNINGS STATUS — {symbol}")
    print(bar)
    if earnings_ctx is None:
        print(f"  No earnings data (index / commodity / futures)")
    else:
        print(f"  Next Earnings: {earnings_ctx['next_date']}")
        print(f"  Days to Earnings: {earnings_ctx['days_to_earnings']}")
        if earnings_ctx['very_near']:
            print(f"  ⚠  EARNINGS SEHR NAH (≤10 Tage) — Pattern-Analyse PFLICHT")
            print(f"     → python3 earnings_pattern.py {symbol}")
            print(f"     → Time-Stop: 5 Tage vor Earnings (v5/v8 Regel)")
        elif earnings_ctx['near']:
            print(f"  ⚠  EARNINGS NAH (≤30 Tage) — Pattern-Analyse PFLICHT")
            print(f"     → python3 earnings_pattern.py {symbol}")
            print(f"     → Trade-Haltezeit limitiert bis max {max(1, earnings_ctx['days_to_earnings'] - 5)} Tage")
        else:
            print(f"  Earnings nicht nah (>30 Tage) — Standard Day-Pattern reicht")
    print()

    print(bar)
    print(f"  YFINANCE NEWS (last 7 days) — {symbol}")
    print(bar)
    if news_err:
        print(f"  WARN: {news_err}")
    elif not news:
        print("  (no news items in yfinance feed — web search MANDATORY)")
    else:
        for n in news[:10]:
            print(f"  [{n['date']}] ({n['age_days']}d) {n['publisher']}")
            print(f"     {n['title']}")
    print()

    print(bar)
    print("  MANDATORY SEARCHES — run EACH query, document findings")
    print(bar)
    print("  [A] TRUMP TRUTH SOCIAL / TWEETS (market manipulator — gap risk)")
    for q in queries["trump_truth"]:
        print(f"      → {q}")
    print()
    print("  [B] REDDIT RETAIL FLOW")
    for q in queries["reddit"]:
        print(f"      → {q}")
    print()
    print("  [C] DAY NEWS / CATALYSTS")
    for q in queries["day_news"]:
        print(f"      → {q}")
    print()
    print("  [D] EVENT CALENDAR (macro)")
    for q in queries["events"]:
        print(f"      → {q}")
    print()

    print(bar)
    print("  CLAUDE — CHECKLIST TO ECHO BACK (VERBATIM) BEFORE STEP 1.1")
    print(bar)
    print(f"""
  PRE-FLIGHT {symbol}:
  [ ] DATUM bestätigt: {date_ctx['date_cet']} {date_ctx['weekday_cet']} (Wochenende: {'JA' if date_ctx['is_weekend'] else 'NEIN'})
  [ ] US-Markt-Status: {date_ctx['us_market']}
  [ ] Trump-Search durchgeführt: [JA/NEIN + Ergebnis: keine Posts / Post gefunden @ datum]
  [ ] Reddit-Subs durchsucht (WSB, WSB-Ger, stocks, investing): [EUPHORIC/BULLISH/NEUTRAL/BEARISH/PANIC/QUIET]
  [ ] Day-News (yfinance + web) gesichtet: [X items, notable: ...]
  [ ] Neutralität: kein Default-Bias (weder LONG, SHORT, noch NO-TRADE)
  [ ] Spiegel-Test: bei spiegelbildlichen Daten würde ich dieselben Argumente gelten lassen
""")
    print(bar)
    print("  HARD RULES — violating any = INVALID analysis, must restart")
    print(bar)
    print("""
  1. NIEMALS ein Event als 'heute/morgen' klassifizieren ohne Abgleich
     gegen das Datum oben. Wochenende? Dann war 'Freitag CPI' GESTERN.
  2. NIEMALS eine volle Analyse als 'Mini-Analyse' abkürzen.
     Eine Analyse = IMMER alle 4 Steps (01→02→03→04), keine Ausnahmen.
  3. NIEMALS eine Default-Richtung annehmen. Daten sprechen.
  4. NIEMALS yfinance-News ignorieren wenn sie etwas Material zeigen.
  5. NIEMALS Trump/Reddit-Search überspringen — beides pflicht für Step 1.5.
""")
    print(bar)
    print("  PRE-FLIGHT DONE — now execute Step 1 (prompts/01_data_collection.md)")
    print(bar)


def main():
    parser = argparse.ArgumentParser(description="Silver Hawk pre-flight check")
    parser.add_argument("symbol", help="Ticker symbol (e.g. PLTR, ENR.DE)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--lookback-days", type=int, default=7, help="News lookback window")
    args = parser.parse_args()

    symbol = args.symbol.upper()

    date_ctx = get_date_context()
    price_snap, price_err = fetch_price_snapshot(symbol)
    news, news_err = fetch_yfinance_news(symbol, args.lookback_days)
    earnings_ctx, earnings_err = fetch_earnings_context(symbol)
    queries = build_search_queries(symbol, date_ctx)

    if args.json:
        print(json.dumps({
            "symbol": symbol,
            "date_context": date_ctx,
            "price": price_snap,
            "price_error": price_err,
            "news": news,
            "news_error": news_err,
            "earnings": earnings_ctx,
            "earnings_error": earnings_err,
            "mandatory_searches": queries,
        }, indent=2, default=str))
    else:
        print_banner(symbol, date_ctx, price_snap, price_err, news, news_err, queries, earnings_ctx)

    # Abort if ticker is unreachable — no point running analysis on nothing
    if price_err:
        sys.exit(2)


if __name__ == "__main__":
    main()
