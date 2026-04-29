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
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


def _load_env_key(name):
    """Read a key from .env (simple KEY=VALUE parser). Returns None if absent."""
    val = os.environ.get(name)
    if val:
        return val.strip()
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def _fetch_twelvedata_quote(symbol):
    """Fallback price source when yfinance flakes. Returns (snap, err)."""
    api_key = _load_env_key("TWELVEDATA_API") or _load_env_key("TWELVEDATA_API_KEY")
    if not api_key:
        return None, "TWELVEDATA_API not set in .env"
    try:
        params = urllib.parse.urlencode({"symbol": symbol, "apikey": api_key})
        url = f"https://api.twelvedata.com/quote?{params}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") == "error" or "close" not in data:
            return None, f"twelvedata: {data.get('message', 'no data')}"
        price = float(data["close"])
        prev = float(data.get("previous_close") or price)
        chg_raw = data.get("percent_change")
        chg = float(chg_raw) if chg_raw not in (None, "") else (
            ((price - prev) / prev * 100) if prev else 0.0
        )
        return {
            "price": round(price, 2),
            "prev_close": round(prev, 2),
            "change_pct": round(chg, 2),
            "currency": data.get("currency", "USD"),
            "name": data.get("name") or symbol,
            "source": "twelvedata",
        }, None
    except Exception as e:
        return None, f"twelvedata fetch failed: {e}"


def fetch_price_snapshot(symbol):
    """Minimal price snapshot — just enough so Claude knows the ticker is real.

    Primary source: yfinance. Fallback: twelvedata (when Yahoo API flakes).
    """
    yf_err = None
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        try:
            info = t.info or {}
        except Exception:
            info = {}
        if hist.empty and not info:
            yf_err = f"No history or info for {symbol}"
        else:
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or (float(hist["Close"].iloc[-1]) if not hist.empty else None)
            )
            if price is None:
                yf_err = f"No price for {symbol}"
            else:
                if info.get("previousClose"):
                    prev = float(info["previousClose"])
                elif len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
                else:
                    prev = float(price)
                chg = ((price - prev) / prev * 100) if prev else 0.0
                return {
                    "price": round(float(price), 2),
                    "prev_close": round(float(prev), 2),
                    "change_pct": round(chg, 2),
                    "currency": info.get("currency", "USD"),
                    "name": info.get("shortName") or info.get("longName") or symbol,
                    "source": "yfinance",
                }, None
    except Exception as e:
        yf_err = f"yfinance: {e}"

    snap, td_err = _fetch_twelvedata_quote(symbol)
    if snap is not None:
        return snap, None
    return None, f"Price fetch failed — {yf_err}; fallback {td_err}"


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


# ---------------------------------------------------------------------------
# Rule 28 — Trader-Day Circuit-Breaker
# ---------------------------------------------------------------------------
# After Tier-2 stop today: block new symbol entries until 22:00 CET.
# After Tier-3 / Support-Override: block today AND next trading day.
# Existing positions can still be managed (rule does NOT block when the
# candidate symbol already has an open position).
#
# Detection: free-text regex on close_events.reason. The reason field is
# free-text written by prediction_db.py close --reason, but Tier-2/3 exits
# follow conventional language ("Tier 2 ...", "-15%", "Support-Override").
# A schema migration was rejected in favor of regex matching to avoid
# backfilling historical rows.

TIER2_PATTERNS = [r"tier\s*2", r"\-15\s*%", r"−15\s*%"]
TIER3_PATTERNS = [r"tier\s*3", r"\-25\s*%", r"−25\s*%", r"support[\- ]?override"]


def _resolve_db_path() -> Path:
    """Locate predictions.db relative to the repo root, robust to cwd."""
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "memory" / "predictions.db"


def check_rule_28(symbol: str, db_path: Path | None = None,
                  now_cet: datetime | None = None) -> tuple[bool, str]:
    """Rule 28: Trader-Day Circuit-Breaker.

    Returns (allowed, message). When allowed=False, caller MUST abort the
    analysis (preflight exits with code 2; calling Claude session sees the
    hard veto).

    Arguments:
        symbol: candidate ticker.
        db_path: override for testing. Defaults to memory/predictions.db.
        now_cet: override for testing. Defaults to live Berlin time.
    """
    if db_path is None:
        db_path = _resolve_db_path()
    if not db_path.exists():
        return True, ""

    berlin = pytz.timezone("Europe/Berlin")
    if now_cet is None:
        now_cet = datetime.now(berlin)
    elif now_cet.tzinfo is None:
        now_cet = berlin.localize(now_cet)

    window_start = now_cet - timedelta(hours=32)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Existing-position carve-out: managing an already-open position
    # is always allowed regardless of recent stops.
    open_row = cur.execute(
        "SELECT 1 FROM predictions WHERE symbol = ? AND status = 'open' LIMIT 1",
        (symbol,),
    ).fetchone()
    if open_row:
        conn.close()
        return True, ""

    # Find recent close events. closed_at is stored as
    # "YYYY-MM-DD HH:MM:SS" via SQLite datetime('now') (UTC).
    rows = cur.execute(
        """
        SELECT p.symbol, ce.reason, ce.closed_at
        FROM close_events ce
        JOIN predictions p ON p.id = ce.prediction_id
        WHERE ce.closed_at >= ?
        ORDER BY ce.closed_at DESC
        """,
        (window_start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()
    conn.close()

    if not rows:
        return True, ""

    # We only care about the most recent qualifying stop event. Earlier
    # ones either already triggered a block that's still live, or were
    # superseded by the most recent one.
    for sym, reason, closed_at_str in rows:
        reason_lower = (reason or "").lower()
        is_tier3 = any(re.search(p, reason_lower) for p in TIER3_PATTERNS)
        is_tier2 = any(re.search(p, reason_lower) for p in TIER2_PATTERNS)
        if not (is_tier2 or is_tier3):
            continue

        # closed_at stored as UTC naive. Localize → Berlin.
        try:
            closed_naive = datetime.strptime(closed_at_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fallback for ISO format with microseconds
            closed_naive = datetime.fromisoformat(closed_at_str.replace("Z", ""))
        closed_utc = closed_naive.replace(tzinfo=timezone.utc)
        closed_cet = closed_utc.astimezone(berlin)

        if is_tier3:
            # Block until end of next trading day (22:00 CET, skip Sat/Sun)
            next_day = closed_cet + timedelta(days=1)
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            unblock = next_day.replace(hour=22, minute=0, second=0, microsecond=0)
            if now_cet < unblock:
                return False, (
                    f"[RULE 28 VETO] Tier-3 / Support-Override stop on {sym} "
                    f"at {closed_cet.strftime('%Y-%m-%d %H:%M CET')}. "
                    f"New entries blocked until {unblock.strftime('%Y-%m-%d 22:00 CET')}. "
                    "Manage existing positions only. "
                    "Override: 'Rule-28-override: <reason citing new catalyst>'."
                )

        if is_tier2 and closed_cet.date() == now_cet.date():
            unblock = closed_cet.replace(hour=22, minute=0, second=0, microsecond=0)
            if now_cet < unblock:
                return False, (
                    f"[RULE 28 VETO] Tier-2 stop on {sym} "
                    f"at {closed_cet.strftime('%H:%M CET')}. "
                    f"New entries blocked until {unblock.strftime('%Y-%m-%d 22:00 CET')}. "
                    "Manage existing positions only. "
                    "Override: 'Rule-28-override: <reason citing new catalyst>'."
                )

        # First qualifying event was checked; nothing more to do.
        # If it didn't trigger a block (e.g. Tier-2 from yesterday → expired),
        # don't keep scanning older rows — they're older than this one.
        break

    return True, ""


def main():
    parser = argparse.ArgumentParser(description="Silver Hawk pre-flight check")
    parser.add_argument("symbol", help="Ticker symbol (e.g. PLTR, ENR.DE)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--lookback-days", type=int, default=7, help="News lookback window")
    args = parser.parse_args()

    symbol = args.symbol.upper()

    # Rule 28 — Trader-Day Circuit-Breaker. PENDING (2026-04-29):
    # Reduced from hard veto to soft warning until 2026-05-29 evaluation.
    # Reason: April n=12 too small to distinguish Tilt vs. Market-confound vs.
    # Selection-bias. Tracking in memory/v10_log.md collects S&P + sector-ETF
    # daily returns alongside follow-up trade outcomes. See memory/strategy_v9.md
    # § 11 for hypotheses and decision schema.
    allowed, veto_msg = check_rule_28(symbol)
    if not allowed:
        # Build a Pending-form notice. veto_msg under v10.0 was a hard block;
        # under Pending we convert it into an awareness ping + logging reminder.
        # Extract the "Tier-... stop on <SYM> at <DATE> ..." prefix and the
        # "blocked until ..." suffix from veto_msg so the pending notice keeps
        # the same time-anchor info but flips the framing.
        prefix_split = veto_msg.split("[RULE 28 VETO] ", 1)
        tail = prefix_split[1] if len(prefix_split) == 2 else veto_msg
        # Strip the obsolete hard-block phrasing from the tail.
        tail = tail.replace(
            " New entries blocked until ",
            " (Hard-veto suspended; old unblock-time was ",
        )
        tail = tail.replace(
            " Manage existing positions only.",
            ").",
        )
        tail = tail.replace(
            " Override: 'Rule-28-override: <reason citing new catalyst>'.",
            "",
        ).strip()
        pending_msg = (
            f"[RULE 28 PENDING — TRACKING] {tail} "
            "Trade decision is yours; please log this stop "
            "in memory/v10_log.md regardless of outcome."
        )
        print(pending_msg, file=sys.stderr)
        # Continue execution — no sys.exit(2). Pipeline runs normally.

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
