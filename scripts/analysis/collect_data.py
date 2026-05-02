#!/usr/bin/env python3
"""Step 1.2 — raw data collection for the v1.0 pipeline.

Hands the LLM the maximum yfinance gives, formatted but not aggregated:

  MARKET_STATUS, CURRENT (price + provenance)
  OHLCV_DAILY        — last ~250 bars
  OHLCV_INTRADAY_5MIN — last 5 sessions
  OHLCV_INTRADAY_1MIN — last 2 sessions, every 5th bar (size-managed)
  KEY_LEVELS         — 52w/3m H+L (index lookups, no math)
  STOCK_META         — exchange, currency, market cap, beta, vol, PE, analyst rec
  EARNINGS           — next date + last 4 reports (when present)
  YFINANCE_NEWS      — last 7-10 items
  MACRO_LIVE         — VIX, DXY, US_10Y, EURUSD

No verdicts. No tags. No scoring. No support detection. No computed
indicators (ATR, SMA, RSI, MACD). All reasoning and indicator math is
the LLM's job in Step 2/3, on the raw bars above.

Usage:
    python3 collect_data.py SYMBOL              # human-readable text
    python3 collect_data.py SYMBOL --json-only  # JSON (for piping / programmatic)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lib.market_status import classify_market_status, select_live_price


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _format_daily_table(hist: pd.DataFrame, n: int = 250) -> str:
    """date | O | H | L | C | Volume[M] — last n bars."""
    sl = hist.tail(n).copy()
    if 'Volume' in sl.columns:
        sl['Volume'] = (sl['Volume'] / 1e6).round(2)
    for col in ('Open', 'High', 'Low', 'Close'):
        if col in sl.columns:
            sl[col] = sl[col].round(2)
    sl.index = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in sl.index]
    return sl[['Open', 'High', 'Low', 'Close', 'Volume']].to_string()


def _format_intraday_table(df: pd.DataFrame, sample_every: int = 1) -> str:
    """datetime_CET | O | H | L | C | Volume."""
    if df.empty:
        return '(no intraday data)'
    sl = df.copy()
    if sample_every > 1:
        sl = sl.iloc[::sample_every]
    if sl.index.tz is None:
        sl.index = sl.index.tz_localize('UTC')
    sl.index = sl.index.tz_convert('Europe/Berlin')
    sl.index = [d.strftime('%Y-%m-%d %H:%M') for d in sl.index]
    if 'Volume' in sl.columns:
        sl['Volume'] = sl['Volume'].fillna(0).astype(int)
    for col in ('Open', 'High', 'Low', 'Close'):
        if col in sl.columns:
            sl[col] = sl[col].round(2)
    return sl[['Open', 'High', 'Low', 'Close', 'Volume']].to_string()


def _key_levels(hist: pd.DataFrame) -> dict:
    """Index lookups only — no math, no aggregation. The 52w/3m extremes
    are bar references the LLM would otherwise have to scan 250 bars to find."""
    out = {'52w_high': None, '52w_low': None, '3m_high': None, '3m_low': None}
    y = hist.tail(252)
    if not y.empty:
        out['52w_high'] = {'value': round(float(y['High'].max()), 2),
                           'date': y['High'].idxmax().strftime('%Y-%m-%d')}
        out['52w_low'] = {'value': round(float(y['Low'].min()), 2),
                          'date': y['Low'].idxmin().strftime('%Y-%m-%d')}
    three_m = hist.tail(63)
    if not three_m.empty:
        out['3m_high'] = {'value': round(float(three_m['High'].max()), 2),
                          'date': three_m['High'].idxmax().strftime('%Y-%m-%d')}
        out['3m_low'] = {'value': round(float(three_m['Low'].min()), 2),
                         'date': three_m['Low'].idxmin().strftime('%Y-%m-%d')}
    return out


def _stock_meta(info: dict, ticker: yf.Ticker) -> dict:
    rec_summary = '—'
    try:
        rec = ticker.recommendations
        if rec is not None and not rec.empty:
            row = rec.iloc[0]
            n_total = info.get('numberOfAnalystOpinions') or '—'
            rec_summary = (
                f"strongBuy={int(row.get('strongBuy', 0))}, "
                f"buy={int(row.get('buy', 0))}, "
                f"hold={int(row.get('hold', 0))}, "
                f"sell={int(row.get('sell', 0))}, "
                f"strongSell={int(row.get('strongSell', 0))} "
                f"(total {n_total}, key: {info.get('recommendationKey', '—')})"
            )
    except Exception:
        pass
    if rec_summary == '—' and info.get('recommendationKey'):
        rec_summary = info.get('recommendationKey')
    return {
        'exchange': info.get('fullExchangeName') or info.get('exchange'),
        'currency': info.get('currency'),
        'market_cap': info.get('marketCap'),
        'beta': info.get('beta'),
        'shares_outstanding': info.get('sharesOutstanding'),
        'avg_volume_10d': info.get('averageDailyVolume10Day') or info.get('averageVolume10days'),
        'trailing_pe': info.get('trailingPE'),
        'forward_pe': info.get('forwardPE'),
        'analyst_recommendations': rec_summary,
    }


def _earnings(ticker: yf.Ticker) -> dict:
    out = {'next_date': None, 'days_until': None, 'last_4_reports': []}
    # Next earnings date via calendar
    try:
        cal = ticker.calendar
        if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
            dates = cal['Earnings Date']
            if dates:
                ed = dates[0]
                if hasattr(ed, 'date'):
                    ed = ed.date()
                if ed >= datetime.now(timezone.utc).date():
                    out['next_date'] = str(ed)
                    out['days_until'] = (ed - datetime.now(timezone.utc).date()).days
    except Exception:
        pass
    # Earnings history (EPS_estimate, EPS_actual, surprise)
    try:
        eh = ticker.earnings_history
        if eh is not None and not eh.empty:
            tail = eh.tail(4)
            for idx, row in tail.iterrows():
                date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                out['last_4_reports'].append({
                    'date': date_str,
                    'eps_estimate': float(row.get('epsEstimate')) if not pd.isna(row.get('epsEstimate')) else None,
                    'eps_actual': float(row.get('epsActual')) if not pd.isna(row.get('epsActual')) else None,
                    'surprise_pct': float(row.get('surprisePercent')) if not pd.isna(row.get('surprisePercent')) else None,
                })
    except Exception:
        pass
    return out


def _yfinance_news(ticker: yf.Ticker, max_items: int = 10) -> list[dict]:
    out = []
    try:
        news = ticker.news or []
    except Exception:
        return out
    for item in news[:max_items]:
        c = item.get('content') if isinstance(item, dict) else None
        if c:
            title = c.get('title', '')
            provider = (c.get('provider') or {}).get('displayName', '')
            url = (c.get('canonicalUrl') or {}).get('url', '')
            pub = c.get('pubDate') or c.get('displayTime', '')
            summary = c.get('summary', '') or c.get('description', '')
        else:
            title = item.get('title', '')
            provider = item.get('publisher', '')
            url = item.get('link', '')
            ts = item.get('providerPublishTime')
            pub = (datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                   if ts else '')
            summary = item.get('summary', '')
        if not title:
            continue
        out.append({
            'date': pub,
            'provider': provider,
            'title': title,
            'url': url,
            'summary': (summary or '')[:300],
        })
    return out


def _macro_live() -> dict:
    """VIX / DXY / US_10Y / EURUSD via yfinance — single batch."""
    tickers = {'VIX': '^VIX', 'DXY': 'DX-Y.NYB', 'US_10Y': '^TNX', 'EURUSD': 'EURUSD=X'}
    out = {}
    for label, sym in tickers.items():
        try:
            h = yf.Ticker(sym).history(period='5d')
            if not h.empty:
                out[label] = round(float(h['Close'].iloc[-1]), 4 if label == 'EURUSD' else 2)
            else:
                out[label] = None
        except Exception:
            out[label] = None
    return out


# ----------------------------------------------------------------------
# Main collector
# ----------------------------------------------------------------------

def collect(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    daily = ticker.history(period='2y', auto_adjust=False)
    if daily.empty:
        return {'error': f'No daily data for {symbol}'}

    # Pence -> Pound normalisation for GBp listings (LSE)
    raw_currency = (info.get('currency') or 'USD')
    is_pence = raw_currency in ('GBp', 'GBX')
    if is_pence:
        for col in ('Open', 'High', 'Low', 'Close'):
            if col in daily.columns:
                daily[col] = daily[col] / 100.0

    last_close = float(daily['Close'].iloc[-1])
    prev_close_info = info.get('previousClose')
    prev_close = (float(prev_close_info)
                  if prev_close_info and prev_close_info > 0
                  else (float(daily['Close'].iloc[-2]) if len(daily) >= 2 else last_close))
    if is_pence and prev_close_info:
        prev_close = prev_close_info / 100.0

    # Market status + live price selection (with staleness check on extended hours)
    market_status, market_status_source = classify_market_status(info.get('marketState'))
    pick = select_live_price(info, prev_close=prev_close,
                             market_status=market_status, last_close=last_close)
    price = pick['price']
    if is_pence and price is not None:
        price = price / 100.0

    if not price or price <= 0:
        return {'error': f'Invalid price for {symbol}'}

    # Intraday histories
    try:
        intra_5m = ticker.history(period='5d', interval='5m', prepost=True, auto_adjust=False)
    except Exception:
        intra_5m = pd.DataFrame()
    try:
        intra_1m = ticker.history(period='2d', interval='1m', prepost=True, auto_adjust=False)
    except Exception:
        intra_1m = pd.DataFrame()
    if is_pence:
        for df in (intra_5m, intra_1m):
            for col in ('Open', 'High', 'Low', 'Close'):
                if col in df.columns:
                    df[col] = df[col] / 100.0

    bid = info.get('bid')
    ask = info.get('ask')

    return {
        'symbol': symbol,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'market_status': market_status,
        'market_status_source': market_status_source,
        'currency': info.get('currency'),
        'short_name': info.get('shortName'),
        'current': {
            'price': round(price, 2),
            'price_source': pick['price_source'],
            'price_timestamp': pick['price_timestamp'],
            'change_from_close_pct': pick['change_from_close_pct'],
            'extended_change_pct': pick['extended_change_pct'],
            'prev_close': round(prev_close, 2),
            'bid': round(float(bid), 2) if bid else None,
            'ask': round(float(ask), 2) if ask else None,
            'warnings': pick['warnings'],
        },
        'ohlcv_daily': _format_daily_table(daily, n=250),
        'ohlcv_intraday_5m': _format_intraday_table(intra_5m),
        'ohlcv_intraday_1m_every5': _format_intraday_table(intra_1m, sample_every=5),
        'key_levels': _key_levels(daily),
        'stock_meta': _stock_meta(info, ticker),
        'earnings': _earnings(ticker),
        'yfinance_news': _yfinance_news(ticker),
        'macro_live': _macro_live(),
    }


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------

def render_text(d: dict) -> str:
    if 'error' in d:
        return f'ERROR: {d["error"]}'

    out = []
    sym = d['symbol']
    out.append(f'SYMBOL: {sym}')
    if d.get('short_name'):
        out.append(f'NAME:   {d["short_name"]}')
    out.append(f'TIMESTAMP: {d["timestamp_utc"]}')
    out.append(f'MARKET_STATUS: {d["market_status"]} (via {d["market_status_source"]})')
    out.append('')

    cur = d['current']
    out.append('CURRENT:')
    out.append(f'  price:                  {cur["price"]} {d.get("currency") or ""}')
    out.append(f'  price_source:           {cur["price_source"]}')
    if cur.get('price_timestamp'):
        out.append(f'  price_timestamp:        {cur["price_timestamp"]}')
    if cur.get('change_from_close_pct') is not None:
        out.append(f'  change_from_close_pct:  {cur["change_from_close_pct"]:+.3f}')
    if cur.get('extended_change_pct') is not None:
        out.append(f'  extended_change_pct:    {cur["extended_change_pct"]:+.3f}')
    out.append(f'  prev_close:             {cur["prev_close"]}')
    if cur['bid'] is not None or cur['ask'] is not None:
        out.append(f'  bid / ask:              {cur["bid"]} / {cur["ask"]}')
    if cur['warnings']:
        for w in cur['warnings']:
            out.append(f'  WARN: {w}')
    out.append('')

    out.append('OHLCV_DAILY (last 250 bars, Volume[M]):')
    out.append(d['ohlcv_daily'])
    out.append('')

    out.append('OHLCV_INTRADAY_5MIN (last 5 sessions):')
    out.append(d['ohlcv_intraday_5m'])
    out.append('')

    out.append('OHLCV_INTRADAY_1MIN (last 2 sessions, every 5th bar):')
    out.append(d['ohlcv_intraday_1m_every5'])
    out.append('')

    kl = d['key_levels']
    out.append('KEY_LEVELS:')
    if kl.get('52w_high'):
        out.append(f'  52w_high: {kl["52w_high"]["value"]} on {kl["52w_high"]["date"]}')
    if kl.get('52w_low'):
        out.append(f'  52w_low:  {kl["52w_low"]["value"]} on {kl["52w_low"]["date"]}')
    if kl.get('3m_high'):
        out.append(f'  3m_high:  {kl["3m_high"]["value"]} on {kl["3m_high"]["date"]}')
    if kl.get('3m_low'):
        out.append(f'  3m_low:   {kl["3m_low"]["value"]} on {kl["3m_low"]["date"]}')
    out.append('')

    sm = d['stock_meta']
    out.append('STOCK_META:')
    for k in ('exchange', 'currency', 'market_cap', 'beta', 'shares_outstanding',
              'avg_volume_10d', 'trailing_pe', 'forward_pe', 'analyst_recommendations'):
        v = sm.get(k)
        if v is not None:
            out.append(f'  {k}: {v}')
    out.append('')

    e = d['earnings']
    out.append('EARNINGS:')
    out.append(f'  next_date:   {e.get("next_date") or "—"}')
    out.append(f'  days_until:  {e.get("days_until") if e.get("days_until") is not None else "—"}')
    if e.get('last_4_reports'):
        out.append('  last_4_reports:')
        for r in e['last_4_reports']:
            est = r.get('eps_estimate')
            act = r.get('eps_actual')
            sur = r.get('surprise_pct')
            est_s = f'{est:.2f}' if est is not None else '—'
            act_s = f'{act:.2f}' if act is not None else '—'
            sur_s = f'{sur:+.1f}%' if sur is not None else '—'
            out.append(f'    {r["date"]}: estimate={est_s} actual={act_s} surprise={sur_s}')
    out.append('')

    out.append('YFINANCE_NEWS (last 7-10 items):')
    if not d['yfinance_news']:
        out.append('  (no items)')
    else:
        for n in d['yfinance_news']:
            out.append(f'  - [{n.get("date") or "—"}] {n.get("provider") or ""}')
            out.append(f'    {n.get("title", "")}')
            if n.get('url'):
                out.append(f'    {n["url"]}')
            if n.get('summary'):
                out.append(f'    {n["summary"]}')
    out.append('')

    macro = d['macro_live']
    out.append('MACRO_LIVE:')
    for k in ('VIX', 'DXY', 'US_10Y', 'EURUSD'):
        v = macro.get(k)
        out.append(f'  {k:6s}: {v if v is not None else "—"}')
    return '\n'.join(out)


def main() -> int:
    p = argparse.ArgumentParser(description='Step 1.2 raw data collector')
    p.add_argument('symbol')
    p.add_argument('--json-only', action='store_true',
                   help='Emit JSON instead of text (intraday tables stay as preformatted strings)')
    args = p.parse_args()

    d = collect(args.symbol.upper())
    if args.json_only:
        print(json.dumps(d, indent=2, default=str))
    else:
        print(render_text(d))
    return 0 if 'error' not in d else 2


if __name__ == '__main__':
    sys.exit(main())
