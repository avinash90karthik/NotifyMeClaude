#!/usr/bin/env python3
"""Step 1.3 — pre-open / pre-market snapshot.

Hands the LLM the pre-trading window for today (or the most recent session
if the market is currently open). Raw extraction from 5-minute intraday
bars — no pattern analysis, no aggregation beyond min/max/sum/last over
the pre-trading window itself (which is just selection from the bars).

  US-Stocks: pre-market window 04:00–09:30 ET, in CET-aware terms
             that varies with DST: ~10:00–15:30 CET in summer,
             09:00–14:30 in winter. We rely on yfinance's UTC bars and
             the symbol's market_state / extended-hours behaviour
             instead of hard-coding a window — pre-market is "all 5m
             bars between yesterday's regular-hours close and today's
             regular-hours open".
  DE-Stocks: XETRA pre-trading window 08:00–09:00 CET. yfinance does
             return some pre-trading bars for XETRA when --prepost is
             requested, but coverage is patchy.

Output blocks:

  PRE_OPEN_SNAPSHOT:
    market: US | DE
    premarket_high: <X.XX>
    premarket_low: <X.XX>
    premarket_volume: <X>
    premarket_last_price: <X.XX>
    gap_vs_prev_close_pct: <±X.XX>

Or one of the markers:
    MARKET_OPEN_NO_PREOPEN_DATA   — regular session is currently active
    NO_PREOPEN_TRADING_TODAY      — no pre-trading bars in yfinance feed

Usage:
    python3 preopen_snapshot.py SYMBOL
    python3 preopen_snapshot.py SYMBOL --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


CET = ZoneInfo('Europe/Berlin')
ET = ZoneInfo('America/New_York')


def is_us_symbol(symbol: str) -> bool:
    return not any(symbol.endswith(suf) for suf in
                   ('.DE', '.PA', '.AS', '.L', '.MI', '.MC', '.SW', '.F'))


def market_classification(symbol: str) -> str:
    return 'US' if is_us_symbol(symbol) else 'DE'


def select_us_premarket_bars(intra_5m: pd.DataFrame) -> pd.DataFrame:
    """Pre-market = bars after most recent ET 16:00 close, before today's 09:30 open.

    Walks the bars in ET, finds the last regular session boundary, returns
    bars between that boundary and the next 09:30 ET (or end-of-bars).
    """
    if intra_5m.empty:
        return intra_5m
    df = intra_5m.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    df_et = df.tz_convert(ET)

    now_et = datetime.now(ET)
    today_et = now_et.date()

    # Today's pre-market window: 04:00 ET → 09:30 ET on today's date.
    open_today = datetime.combine(today_et, dtime(9, 30), tzinfo=ET)
    pre_open_start = datetime.combine(today_et, dtime(4, 0), tzinfo=ET)

    if now_et < pre_open_start:
        # We're before today's pre-market window; nothing yet
        return df_et.iloc[0:0]
    if now_et >= open_today:
        # Regular session reached or passed; the snapshot is effectively
        # the full pre-market window (we still surface it as today's snapshot)
        cutoff_end = open_today
    else:
        cutoff_end = now_et

    return df_et[(df_et.index >= pre_open_start) & (df_et.index < cutoff_end)]


def select_de_pretrading_bars(intra_5m: pd.DataFrame) -> pd.DataFrame:
    """XETRA pre-trading: 08:00–09:00 CET on today's date."""
    if intra_5m.empty:
        return intra_5m
    df = intra_5m.copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    df_cet = df.tz_convert(CET)

    now_cet = datetime.now(CET)
    today_cet = now_cet.date()

    pre_start = datetime.combine(today_cet, dtime(8, 0), tzinfo=CET)
    pre_end = datetime.combine(today_cet, dtime(9, 0), tzinfo=CET)

    if now_cet < pre_start:
        return df_cet.iloc[0:0]
    cutoff_end = min(now_cet, pre_end)
    return df_cet[(df_cet.index >= pre_start) & (df_cet.index < cutoff_end)]


def is_market_currently_open(market: str) -> bool:
    """Crude check via local clock — only used for the
    MARKET_OPEN_NO_PREOPEN_DATA marker decision."""
    if market == 'US':
        now_et = datetime.now(ET)
        if now_et.weekday() >= 5:
            return False
        return dtime(9, 30) <= now_et.time() < dtime(16, 0)
    now_cet = datetime.now(CET)
    if now_cet.weekday() >= 5:
        return False
    return dtime(9, 0) <= now_cet.time() < dtime(17, 30)


def build_snapshot(symbol: str) -> dict:
    market = market_classification(symbol)

    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    prev_close = info.get('previousClose')
    if not prev_close:
        try:
            d = ticker.history(period='5d')
            if not d.empty:
                prev_close = float(d['Close'].iloc[-1])
        except Exception:
            prev_close = None

    try:
        intra_5m = ticker.history(period='5d', interval='5m', prepost=True, auto_adjust=False)
    except Exception as e:
        return {
            'symbol': symbol,
            'market': market,
            'error': f'yfinance 5m history failed: {e}',
        }

    if market == 'US':
        bars = select_us_premarket_bars(intra_5m)
    else:
        bars = select_de_pretrading_bars(intra_5m)

    # If we have pre-trading bars from today's window, surface them — even if
    # the regular session is now open. The snapshot is "today's pre-open
    # behaviour", not "live tape".
    if bars.empty:
        # No bars in today's pre-trading window. Distinguish between
        # "market is currently in regular session, so we wouldn't expect
        # post-open pre-market data" vs. "no pre-trading happened at all".
        if is_market_currently_open(market):
            marker = 'MARKET_OPEN_NO_PREOPEN_DATA'
        else:
            marker = 'NO_PREOPEN_TRADING_TODAY'
        return {
            'symbol': symbol,
            'market': market,
            'marker': marker,
            'prev_close': round(float(prev_close), 2) if prev_close else None,
        }

    pre_high = float(bars['High'].max())
    pre_low = float(bars['Low'].min())
    pre_volume = int(bars['Volume'].fillna(0).sum())
    pre_last = float(bars['Close'].iloc[-1])
    pre_first_ts = bars.index[0].isoformat()
    pre_last_ts = bars.index[-1].isoformat()

    gap = None
    if prev_close and prev_close > 0:
        gap = round((pre_last / float(prev_close) - 1.0) * 100, 2)

    return {
        'symbol': symbol,
        'market': market,
        'premarket_high': round(pre_high, 2),
        'premarket_low': round(pre_low, 2),
        'premarket_volume': pre_volume,
        'premarket_last_price': round(pre_last, 2),
        'gap_vs_prev_close_pct': gap,
        'prev_close': round(float(prev_close), 2) if prev_close else None,
        'window_first_bar': pre_first_ts,
        'window_last_bar': pre_last_ts,
        'bar_count': int(len(bars)),
    }


def render_text(d: dict) -> str:
    out = []
    out.append('PRE_OPEN_SNAPSHOT:')
    if 'error' in d:
        out.append(f'  ERROR: {d["error"]}')
        return '\n'.join(out)
    out.append(f'  symbol: {d["symbol"]}')
    out.append(f'  market: {d["market"]}')
    if d.get('marker'):
        out.append(f'  {d["marker"]}')
        if d.get('prev_close') is not None:
            out.append(f'  prev_close: {d["prev_close"]}')
        return '\n'.join(out)
    out.append(f'  premarket_high:        {d["premarket_high"]}')
    out.append(f'  premarket_low:         {d["premarket_low"]}')
    out.append(f'  premarket_volume:      {d["premarket_volume"]}')
    out.append(f'  premarket_last_price:  {d["premarket_last_price"]}')
    if d.get('gap_vs_prev_close_pct') is not None:
        out.append(f'  gap_vs_prev_close_pct: {d["gap_vs_prev_close_pct"]:+.2f}')
    out.append(f'  prev_close:            {d.get("prev_close")}')
    out.append(f'  window_first_bar:      {d["window_first_bar"]}')
    out.append(f'  window_last_bar:       {d["window_last_bar"]}')
    out.append(f'  bar_count:             {d["bar_count"]}')
    return '\n'.join(out)


def main() -> int:
    p = argparse.ArgumentParser(description='Step 1.3 pre-open snapshot')
    p.add_argument('symbol')
    p.add_argument('--json', action='store_true')
    args = p.parse_args()

    d = build_snapshot(args.symbol.upper())

    if args.json:
        print(json.dumps(d, indent=2, default=str))
    else:
        print(render_text(d))

    return 0 if 'error' not in d else 2


if __name__ == '__main__':
    sys.exit(main())
