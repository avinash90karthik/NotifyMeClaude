#!/usr/bin/env python3
"""Step 0 — Pre-Flight Check (v1.0).

Four hard-stop checks before any analysis. No data fetching beyond a single
symbol-resolve call. No news, no Reddit, no Trump, no macro — those live in
Step 1+.

Output is structured per `prompts/00_preflight.md`:

    TIMESTAMP, WEEKDAY
    MARKET_HOURS_TODAY: US + DE
    SYMBOL_VALIDITY: symbol/exchange/resolved
    HARD_STOPS:
      Max_3_Slots:  <X>/3 turbos open → ok | STOP
      Cooldown_24h: last stop on SYMBOL was <date> → ok | STOP
    STATUS: READY_FOR_STEP_1 | STOP

Usage:
    python3 scripts/analysis/preflight_check.py SYMBOL
    python3 scripts/analysis/preflight_check.py SYMBOL --json

Exit codes:
    0 = READY_FOR_STEP_1
    1 = STOP (any hard veto fired)
    2 = error (symbol resolve / DB read failed)
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO / 'memory' / 'predictions.db'

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from lib.risk_audit import MAX_OPEN_TURBOS

try:
    import yfinance as yf
except ImportError:
    print('FATAL: yfinance not installed', file=sys.stderr)
    sys.exit(2)


CET = ZoneInfo('Europe/Berlin')
NY = ZoneInfo('America/New_York')

WEEKDAYS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# US market hours in CET (DST-naive heuristic — fallback only).
# Primary truth comes from yfinance info.marketState in Step 1; here we
# only need today's open window for the banner.
US_OPEN_CET = (15, 30)   # 15:30 CET
US_CLOSE_CET = (22, 0)   # 22:00 CET
DE_OPEN_CET = (9, 0)     # 09:00 CET (XETRA)
DE_CLOSE_CET = (17, 30)  # 17:30 CET


def market_window(open_h: tuple[int, int], close_h: tuple[int, int],
                  now: datetime) -> tuple[str, str]:
    """Return (status_str, hours_or_reason)."""
    if now.weekday() >= 5:
        return 'closed', 'weekend'
    o = f'{open_h[0]:02d}:{open_h[1]:02d}'
    c = f'{close_h[0]:02d}:{close_h[1]:02d}'
    return 'open', f'{o}-{c} CET'


def date_block() -> dict:
    now_cet = datetime.now(CET)
    now_ny = datetime.now(NY)
    us_status, us_hours = market_window(US_OPEN_CET, US_CLOSE_CET, now_cet)
    de_status, de_hours = market_window(DE_OPEN_CET, DE_CLOSE_CET, now_cet)
    return {
        'timestamp_cet': now_cet.isoformat(timespec='seconds'),
        'weekday': WEEKDAYS_EN[now_cet.weekday()],
        'us_status': us_status,
        'us_hours': us_hours,
        'de_status': de_status,
        'de_hours': de_hours,
        'now_ny': now_ny.isoformat(timespec='seconds'),
    }


def resolve_symbol(symbol: str) -> dict:
    """Single yfinance call — does the symbol exist, what's its exchange?"""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
    except Exception as e:
        return {'symbol': symbol, 'resolved': False, 'exchange': None,
                'error': f'yfinance lookup failed: {e}'}
    # A non-existent symbol typically has empty info or only a few fallback
    # keys. Use the presence of `regularMarketPrice` OR `previousClose` OR
    # `quoteType` as the resolve signal.
    has_quote = any(info.get(k) is not None for k in
                    ('regularMarketPrice', 'previousClose', 'quoteType'))
    return {
        'symbol': symbol,
        'resolved': bool(has_quote),
        'exchange': info.get('fullExchangeName') or info.get('exchange'),
        'currency': info.get('currency'),
        'short_name': info.get('shortName'),
        'error': None,
    }


def hard_stops(symbol: str, db_path: Path) -> dict:
    """V5 slot check + SW2 24h cooldown."""
    if not db_path.exists():
        return {'max_3_slots': {'verdict': 'STOP',
                                'detail': f'DB missing at {db_path}'},
                'cooldown_24h': {'verdict': 'STOP',
                                 'detail': f'DB missing at {db_path}'}}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Max_3_Slots: count open turbo positions
        open_count = conn.execute(
            "SELECT COUNT(*) FROM predictions "
            "WHERE status='open' AND (cert_type='turbo' OR cert_type IS NULL)"
        ).fetchone()[0]
        max_3_slots = {
            'open_turbos': open_count,
            'cap': MAX_OPEN_TURBOS,
            'verdict': 'STOP' if open_count >= MAX_OPEN_TURBOS else 'ok',
            'detail': f'{open_count}/{MAX_OPEN_TURBOS} turbos open',
        }

        # Cooldown_24h: any stop trigger on this symbol within the last 24h?
        # Source: close_events.reason LIKE 'stop%' joined to the predictions row.
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)
                  ).strftime('%Y-%m-%d %H:%M:%S')
        row = conn.execute("""
            SELECT ce.closed_at, ce.reason
              FROM close_events ce
              JOIN predictions p ON p.id = ce.prediction_id
             WHERE p.symbol = ?
               AND lower(ce.reason) LIKE 'stop%'
               AND ce.closed_at > ?
             ORDER BY ce.closed_at DESC
             LIMIT 1
        """, (symbol.upper(), cutoff)).fetchone()

        if row is None:
            cooldown_24h = {
                'last_stop_on_symbol': None,
                'verdict': 'ok',
                'detail': 'no stop in last 24h',
            }
        else:
            cooldown_24h = {
                'last_stop_on_symbol': row['closed_at'],
                'verdict': 'STOP',
                'detail': f"stop triggered {row['closed_at']}",
            }
    finally:
        conn.close()

    return {'max_3_slots': max_3_slots, 'cooldown_24h': cooldown_24h}


def render_text(symbol: str, d: dict, sym: dict, hs: dict, status: str) -> str:
    bar = '=' * 60
    out = []
    out.append(bar)
    out.append(f'  STEP 0 — PRE-FLIGHT  {symbol}')
    out.append(bar)
    out.append(f'TIMESTAMP: {d["timestamp_cet"]}')
    out.append(f'WEEKDAY:   {d["weekday"]}')
    out.append('')
    out.append('MARKET_HOURS_TODAY:')
    us_line = (f'  US: open {d["us_hours"]}'
               if d['us_status'] == 'open'
               else f'  US: closed ({d["us_hours"]})')
    de_line = (f'  DE: open {d["de_hours"]}'
               if d['de_status'] == 'open'
               else f'  DE: closed ({d["de_hours"]})')
    out.append(us_line)
    out.append(de_line)
    out.append('')
    out.append('SYMBOL_VALIDITY:')
    out.append(f'  symbol:   {sym["symbol"]}')
    out.append(f'  exchange: {sym["exchange"] or "—"}')
    out.append(f'  resolved: {"yes" if sym["resolved"] else "no"}')
    if sym.get('error'):
        out.append(f'  error:    {sym["error"]}')
    out.append('')
    out.append('HARD_STOPS:')
    s = hs['max_3_slots']
    c = hs['cooldown_24h']
    out.append(f'  Max_3_Slots:  {s["detail"]} → {s["verdict"]}')
    out.append(f'  Cooldown_24h: {c["detail"]} → {c["verdict"]}')
    out.append('')
    out.append(f'STATUS: {status}')
    out.append(bar)
    return '\n'.join(out)


def determine_status(sym: dict, hs: dict) -> str:
    if not sym['resolved']:
        return 'STOP'
    if hs['max_3_slots']['verdict'] != 'ok':
        return 'STOP'
    if hs['cooldown_24h']['verdict'] != 'ok':
        return 'STOP'
    return 'READY_FOR_STEP_1'


def main() -> int:
    p = argparse.ArgumentParser(description='Step 0 pre-flight check')
    p.add_argument('symbol')
    p.add_argument('--json', action='store_true', help='Emit JSON instead of text')
    p.add_argument('--db', default=str(DB_PATH))
    args = p.parse_args()

    symbol = args.symbol.upper()

    d = date_block()
    sym = resolve_symbol(symbol)
    hs = hard_stops(symbol, Path(args.db))
    status = determine_status(sym, hs)

    if args.json:
        print(json.dumps({
            'date_block': d,
            'symbol': sym,
            'hard_stops': hs,
            'status': status,
        }, indent=2, default=str))
    else:
        print(render_text(symbol, d, sym, hs, status))

    if status == 'READY_FOR_STEP_1':
        return 0
    if not sym['resolved']:
        return 2
    return 1


if __name__ == '__main__':
    sys.exit(main())
