#!/usr/bin/env python3
"""Silver Hawk Trading - Pre-Open Pattern Recognition.

Historical backtesting of pre-open signals against post-open intraday outcomes.
Rolling-window approach: calc_technicals() + score_long()/score_short() on daily
data through yesterday, then measure what happened intraday from hourly bars.

Produces pattern statistics: "Score 75+ in TRENDING + MACD bullish -> 72% hit rate".

Usage:
    python preopen_backtest.py                              # Full watchlist
    python preopen_backtest.py --symbols SYMBOL1 SYMBOL2    # Specific symbols
    python preopen_backtest.py --telegram                   # With Telegram report
    python preopen_backtest.py --min-samples 30             # Higher sample threshold
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_JSON = os.path.join(SCRIPT_DIR, 'memory', 'watchlist.json')
PATTERNS_FILE = os.path.join(SCRIPT_DIR, 'memory', 'preopen_patterns.json')
ET = ZoneInfo('America/New_York')
WARMUP_DAYS = 250
MIN_SAMPLES_DEFAULT = 20
EU_SUFFIXES = ('.DE', '.PA', '.L', '.AS')

# Primary pattern combos (3 dimensions each, 6 combos)
COMBOS = [
    ('score', 'regime', 'macd'),
    ('score', 'regime', 'gap'),
    ('score', 'rsi_zone', 'regime'),
    ('score', 'regime', 'volume'),
    ('score', 'regime', 'bb'),
    ('score', 'gap', 'macd'),
]

ALL_DIMS = ('score', 'rsi_zone', 'regime', 'gap', 'macd', 'volume', 'bb', 'futures')


def get_watchlist_symbols():
    """Load US symbols from watchlist.json (skip EU stocks)."""
    if not os.path.exists(WATCHLIST_JSON):
        return []
    with open(WATCHLIST_JSON) as f:
        data = json.load(f)
    return [s['symbol'] for s in data
            if not any(s['symbol'].endswith(sfx) for sfx in EU_SUFFIXES)]


def build_es_overnight(es_df):
    """Pre-build dict of date -> ES=F overnight change % for fast lookup."""
    if es_df is None or len(es_df) < 2:
        return {}
    overnights = {}
    for i in range(1, len(es_df)):
        prev_close = float(es_df['Close'].iloc[i - 1])
        curr_open = float(es_df['Open'].iloc[i])
        if prev_close > 0:
            dt = es_df.index[i]
            d = dt.date() if hasattr(dt, 'date') and callable(dt.date) else dt
            overnights[d] = round((curr_open - prev_close) / prev_close * 100, 4)
    return overnights


def extract_intraday(sym_hourly_et, trade_date):
    """Extract intraday outcomes for a trading day from ET-indexed hourly bars.

    Returns dict with open/close/1h/4h returns and max up/down, or None.
    """
    day_mask = sym_hourly_et.index.date == trade_date
    bars = sym_hourly_et[day_mask]
    if len(bars) < 3:
        return None

    market = bars.between_time('09:30', '15:59')
    if len(market) < 3:
        return None

    open_p = float(market['Open'].iloc[0])
    close_p = float(market['Close'].iloc[-1])
    if open_p <= 0:
        return None

    max_hi = float(market['High'].max())
    max_lo = float(market['Low'].min())

    # 1h after open (~10:30 bar)
    h1 = market.between_time('10:00', '11:00')
    h1_p = float(h1['Close'].iloc[0]) if len(h1) > 0 else None

    # 4h after open (~13:30 bar)
    h4 = market.between_time('13:00', '14:00')
    h4_p = float(h4['Close'].iloc[0]) if len(h4) > 0 else None

    return {
        'open': open_p,
        'close': close_p,
        'ret_1h': round((h1_p - open_p) / open_p * 100, 4) if h1_p else None,
        'ret_4h': round((h4_p - open_p) / open_p * 100, 4) if h4_p else None,
        'ret_close': round((close_p - open_p) / open_p * 100, 4),
        'max_up_pct': round((max_hi - open_p) / open_p * 100, 4),
        'max_down_pct': round((max_lo - open_p) / open_p * 100, 4),
    }


def tag_patterns(d, gap_pct, es_overnight_pct=None):
    """Tag a data point with 8 pattern dimensions.

    Args:
        d: Technical data dict from calc_technicals() with _score_long/_score_short added
        gap_pct: Gap % (Today Open vs Previous Close)
        es_overnight_pct: ES=F overnight change (optional)

    Returns: dict with dimension tags
    """
    tags = {}

    # 1. Score bracket
    best = max(d.get('_score_long', 0), d.get('_score_short', 0))
    if best >= 75:
        tags['score'] = '75+'
    elif best >= 60:
        tags['score'] = '60-74'
    elif best >= 40:
        tags['score'] = '40-59'
    else:
        tags['score'] = '<40'

    # 2. RSI zone
    rsi = d.get('rsi', 50)
    tags['rsi_zone'] = 'oversold' if rsi < 30 else ('overbought' if rsi > 70 else 'neutral')

    # 3. Regime
    tags['regime'] = d.get('regime', 'TRANSITIONAL')

    # 4. Gap direction
    tags['gap'] = 'up' if gap_pct > 1 else ('down' if gap_pct < -1 else 'flat')

    # 5. MACD state
    mc, mp = d.get('macd_hist'), d.get('macd_hist_prev')
    if mc is not None and mp is not None:
        if mp < 0 and mc > 0:
            tags['macd'] = 'bullish_xover'
        elif mp > 0 and mc < 0:
            tags['macd'] = 'bearish_xover'
        elif mc > 0:
            tags['macd'] = 'bullish'
        else:
            tags['macd'] = 'bearish'
    else:
        tags['macd'] = 'neutral'

    # 6. Volume state
    vr = d.get('vol_ratio') or 1.0
    tags['volume'] = 'high' if vr > 1.5 else ('low' if vr < 0.5 else 'normal')

    # 7. Bollinger state
    bb = d.get('bb_width_percentile')
    if bb is not None and bb < 10:
        tags['bb'] = 'squeeze'
    elif bb is not None and bb > 80:
        tags['bb'] = 'wide'
    else:
        tags['bb'] = 'normal'

    # 8. Futures sentiment
    if es_overnight_pct is not None:
        if es_overnight_pct > 0.3:
            tags['futures'] = 'bullish'
        elif es_overnight_pct < -0.3:
            tags['futures'] = 'bearish'
        else:
            tags['futures'] = 'neutral'
    else:
        tags['futures'] = 'neutral'

    return tags


def aggregate_patterns(records, min_samples=20):
    """Aggregate records into primary patterns, feature-level stats, and traps.

    Primary: 6 three-dimension combos, LONG + SHORT, min_samples filter.
    Feature: each dimension individually.
    Traps: Score >= 60 but hit rate < 50%.
    """
    primary = {'LONG': {}, 'SHORT': {}}

    for direction in ('LONG', 'SHORT'):
        for combo in COMBOS:
            groups = defaultdict(list)
            for r in records:
                key = '|'.join(r['tags'].get(dim, '?') for dim in combo)
                groups[key].append(r)

            combo_name = '+'.join(combo)
            for gkey, grecs in groups.items():
                if len(grecs) < min_samples:
                    continue

                with_4h = [r for r in grecs if r.get('ret_4h') is not None]

                if direction == 'LONG':
                    hits_4h = sum(1 for r in with_4h if r['ret_4h'] > 0)
                    hits_close = sum(1 for r in grecs if r['ret_close'] > 0)
                else:
                    hits_4h = sum(1 for r in with_4h if r['ret_4h'] < 0)
                    hits_close = sum(1 for r in grecs if r['ret_close'] < 0)

                rets_4h = [r['ret_4h'] for r in with_4h]
                rets_close = [r['ret_close'] for r in grecs]

                # Gap fill rate
                gap_fills = gap_total = 0
                for r in grecs:
                    g = r.get('gap_pct', 0)
                    if abs(g) > 1:
                        gap_total += 1
                        if (g > 1 and r.get('max_down_pct', 0) < 0) or \
                           (g < -1 and r.get('max_up_pct', 0) > 0):
                            gap_fills += 1

                avg_4h = float(np.mean(rets_4h)) if rets_4h else None
                avg_close = float(np.mean(rets_close))

                pkey = f'{combo_name}:{gkey}'
                primary[direction][pkey] = {
                    'combo': combo_name,
                    'values': gkey,
                    'n': len(grecs),
                    'hit_4h': round(hits_4h / len(with_4h) * 100, 1) if with_4h else None,
                    'hit_close': round(hits_close / len(grecs) * 100, 1),
                    'avg_4h': round(avg_4h, 3) if avg_4h is not None and not np.isnan(avg_4h) else None,
                    'avg_close': round(avg_close, 3) if not np.isnan(avg_close) else None,
                    'gap_fill': round(gap_fills / gap_total * 100, 1) if gap_total >= 5 else None,
                }

    # Feature-level (single dimension)
    features = {'LONG': {}, 'SHORT': {}}
    for direction in ('LONG', 'SHORT'):
        for dim in ALL_DIMS:
            groups = defaultdict(list)
            for r in records:
                groups[r['tags'].get(dim, '?')].append(r)
            for val, grecs in groups.items():
                if len(grecs) < 5:
                    continue
                if direction == 'LONG':
                    hits = sum(1 for r in grecs if r['ret_close'] > 0)
                else:
                    hits = sum(1 for r in grecs if r['ret_close'] < 0)
                avg = float(np.mean([r['ret_close'] for r in grecs]))
                features[direction][f'{dim}:{val}'] = {
                    'n': len(grecs),
                    'hit_rate': round(hits / len(grecs) * 100, 1),
                    'avg_return': round(avg, 3) if not np.isnan(avg) else None,
                }

    # Trap detection: Score >= 60 but hit rate < 50%
    traps = []
    for direction in ('LONG', 'SHORT'):
        for key, s in primary[direction].items():
            if '75+' in s['values'] or '60-74' in s['values']:
                hr = s.get('hit_4h') or s.get('hit_close')
                if hr is not None and hr < 50:
                    traps.append({
                        'direction': direction,
                        'pattern': key,
                        'values': s['values'],
                        'hit_rate': hr,
                        'n': s['n'],
                        'avg_return': s.get('avg_4h') or s.get('avg_close'),
                    })

    return primary, features, traps


def flatten_multi(df):
    """Flatten MultiIndex columns from yf.download (single symbol)."""
    if df is not None and hasattr(df, 'columns') and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    return df


def run_backtest(symbols, min_samples=20):
    """Run the full pre-open pattern backtest."""
    import yfinance as yf
    from indicators import calc_technicals
    from morning_screener import score_long, score_short

    single = len(symbols) == 1

    # Download data
    print(f'  Downloading daily data (2y) for {len(symbols)} symbols...')
    if single:
        daily = yf.download(symbols[0], period='2y', progress=False)
    else:
        daily = yf.download(symbols, period='2y', group_by='ticker', threads=True, progress=False)
    if daily is None or daily.empty:
        print('  No daily data.')
        return None
    print(f'  Downloading hourly data (730d)...')
    if single:
        hourly = yf.download(symbols[0], period='730d', interval='1h', progress=False)
    else:
        hourly = yf.download(symbols, period='730d', interval='1h', group_by='ticker', threads=True, progress=False)
    if hourly is None or hourly.empty:
        print('  No hourly data.')
        return None

    if single:
        daily = flatten_multi(daily)
        hourly = flatten_multi(hourly)

    # ES=F for futures sentiment
    print('  Downloading ES=F for futures sentiment...')
    try:
        es_raw = yf.download('ES=F', period='2y', progress=False)
        es_raw = flatten_multi(es_raw)
        es_overnight = build_es_overnight(es_raw)
    except Exception:
        es_overnight = {}
    print(f'  ES=F overnight data: {len(es_overnight)} days')

    all_records = []

    for sym in symbols:
        print(f'\n  {sym}...')

        # Daily data for this symbol
        if single:
            sym_daily = daily
        else:
            try:
                sym_daily = daily[sym].dropna(how='all')
            except (KeyError, TypeError):
                print(f'    no daily data')
                continue
            sym_daily = flatten_multi(sym_daily)

        if len(sym_daily) < WARMUP_DAYS + 10:
            print(f'    insufficient daily ({len(sym_daily)}d)')
            continue

        # Hourly data for this symbol, convert to ET
        if single:
            sym_hourly = hourly.copy()
        else:
            try:
                sym_hourly = hourly[sym].dropna(how='all').copy()
            except (KeyError, TypeError):
                print(f'    no hourly data')
                continue
            sym_hourly = flatten_multi(sym_hourly)

        if sym_hourly.index.tz is None:
            sym_hourly.index = sym_hourly.index.tz_localize('UTC').tz_convert(ET)
        else:
            sym_hourly.index = sym_hourly.index.tz_convert(ET)

        hourly_dates = set(sym_hourly.index.date)

        # Rolling window
        count = errors = 0
        for i in range(WARMUP_DAYS, len(sym_daily)):
            raw_idx = sym_daily.index[i]
            trade_date = raw_idx.date() if hasattr(raw_idx, 'date') and callable(raw_idx.date) else raw_idx

            if trade_date not in hourly_dates:
                continue

            # Window up to previous day (pre-open: we don't know today's data)
            window = sym_daily.iloc[:i].copy()

            try:
                data = calc_technicals(window, [sym], single=True)
                if sym not in data:
                    continue
                d = data[sym]
                if d.get('rsi') is None:
                    continue

                rw = d.get('regime_weights')
                ls, _ = score_long(d, regime=rw)
                ss, _ = score_short(d, regime=rw)
                d['_score_long'] = ls
                d['_score_short'] = ss

                # Intraday outcome
                intraday = extract_intraday(sym_hourly, trade_date)
                if intraday is None:
                    continue

                # Gap vs previous close
                prev_close = float(sym_daily['Close'].iloc[i - 1])
                gap_pct = round((intraday['open'] - prev_close) / prev_close * 100, 4) if prev_close > 0 else 0

                # ES=F overnight
                es_pct = es_overnight.get(trade_date)

                tags = tag_patterns(d, gap_pct, es_pct)

                all_records.append({
                    'symbol': sym,
                    'date': str(trade_date),
                    'score_long': ls,
                    'score_short': ss,
                    'regime': d.get('regime', 'TRANSITIONAL'),
                    'rsi': d.get('rsi'),
                    'gap_pct': gap_pct,
                    'tags': tags,
                    'ret_1h': intraday['ret_1h'],
                    'ret_4h': intraday['ret_4h'],
                    'ret_close': intraday['ret_close'],
                    'max_up_pct': intraday['max_up_pct'],
                    'max_down_pct': intraday['max_down_pct'],
                })
                count += 1

            except (KeyError, ValueError, ZeroDivisionError, IndexError):
                errors += 1
                continue

        if errors > 0:
            print(f'    {errors} calc errors')
        print(f'    {count} records')

    if not all_records:
        print('No valid records.')
        return None

    print(f'\nTotal: {len(all_records)} records from {len(symbols)} symbols')

    primary, features, traps = aggregate_patterns(all_records, min_samples)

    output = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'total_records': len(all_records),
        'symbols': symbols,
        'min_samples': min_samples,
        'primary_patterns': primary,
        'feature_level': features,
        'traps': traps,
    }

    with open(PATTERNS_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'Saved: {PATTERNS_FILE}')

    return output


def format_telegram(output):
    """Format pattern results for Telegram."""
    if not output:
        return 'Keine Ergebnisse.'

    n_records = output['total_records']
    n_symbols = len(output['symbols'])

    msg = f'<b>PRE-OPEN PATTERNS</b> ({n_symbols} Symbole, {n_records:,} Tage)\n'
    msg += f'{datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")}\n\n'

    # Top 5 LONG patterns (sorted by hit_4h)
    long_pats = output['primary_patterns'].get('LONG', {})
    long_sorted = sorted(
        long_pats.values(),
        key=lambda x: x.get('hit_4h') or x.get('hit_close') or 0,
        reverse=True,
    )

    msg += '<b>TOP 5 LONG</b>\n'
    for i, p in enumerate(long_sorted[:5], 1):
        hr = p.get('hit_4h') or p.get('hit_close') or 0
        avg = p.get('avg_4h') or p.get('avg_close') or 0
        label = p['values'].replace('|', ' + ')
        gf = f' | GapFill {p["gap_fill"]:.0f}%' if p.get('gap_fill') else ''
        msg += f'{i}. {label}\n'
        msg += f'   {hr:.0f}% (n={p["n"]}) | Avg {avg:+.2f}%/4h{gf}\n'
    if not long_sorted:
        msg += '  Keine Patterns mit genug Samples\n'

    # Top 5 SHORT patterns
    short_pats = output['primary_patterns'].get('SHORT', {})
    short_sorted = sorted(
        short_pats.values(),
        key=lambda x: x.get('hit_4h') or x.get('hit_close') or 0,
        reverse=True,
    )

    msg += '\n<b>TOP 5 SHORT</b>\n'
    for i, p in enumerate(short_sorted[:5], 1):
        hr = p.get('hit_4h') or p.get('hit_close') or 0
        avg = p.get('avg_4h') or p.get('avg_close') or 0
        label = p['values'].replace('|', ' + ')
        msg += f'{i}. {label}\n'
        msg += f'   {hr:.0f}% (n={p["n"]}) | Avg {avg:+.2f}%/4h\n'
    if not short_sorted:
        msg += '  Keine Patterns mit genug Samples\n'

    # Traps
    traps = output.get('traps', [])
    if traps:
        traps_sorted = sorted(traps, key=lambda t: t['hit_rate'])
        msg += '\n<b>FALLEN</b>\n'
        for t in traps_sorted[:5]:
            label = t['values'].replace('|', ' + ')
            msg += f'  {t["direction"]} {label}\n'
            msg += f'  {t["hit_rate"]:.0f}% (n={t["n"]}) — Vorsicht!\n'

    # Feature-level summary
    long_feat = output.get('feature_level', {}).get('LONG', {})
    msg += '\n<b>FEATURES (LONG)</b>\n'

    for key in ('score:75+', 'score:60-74', 'score:40-59', 'score:<40'):
        f = long_feat.get(key)
        if f:
            msg += f'  {key.split(":")[1]}: {f["hit_rate"]}% (n={f["n"]})\n'

    for key in ('regime:TRENDING', 'regime:RANGE', 'regime:CHOPPY'):
        f = long_feat.get(key)
        if f:
            msg += f'  {key.split(":")[1]}: {f["hit_rate"]}% (n={f["n"]})\n'

    msg += f'\n<i>Min Samples: {output["min_samples"]} | Pre-Open Engine v1</i>'
    return msg


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Pre-Open Pattern Backtest')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to backtest')
    parser.add_argument('--telegram', action='store_true', help='Send results via Telegram')
    parser.add_argument('--min-samples', type=int, default=MIN_SAMPLES_DEFAULT,
                        help=f'Min samples per pattern (default: {MIN_SAMPLES_DEFAULT})')
    args = parser.parse_args()

    if args.symbols:
        symbols = args.symbols
    else:
        symbols = get_watchlist_symbols()
        if not symbols:
            print('No symbols found. Use --symbols or add to watchlist.json')
            sys.exit(1)

    print(f'Pre-Open Pattern Backtest')
    print(f'Symbols: {len(symbols)} | Min Samples: {args.min_samples}')
    print(f'{"=" * 50}')

    output = run_backtest(symbols, min_samples=args.min_samples)

    if not output:
        print('Backtest failed.')
        sys.exit(1)

    # Print summary
    print(f'\n{"=" * 50}')
    print(f'RESULTS: {output["total_records"]:,} records')

    for direction in ('LONG', 'SHORT'):
        patterns = output['primary_patterns'].get(direction, {})
        print(f'\n{direction} Patterns: {len(patterns)}')
        top = sorted(patterns.values(), key=lambda x: x.get('hit_4h') or 0, reverse=True)[:3]
        for p in top:
            hr = p.get('hit_4h') or p.get('hit_close') or 0
            print(f'  {p["values"]}: {hr:.1f}% (n={p["n"]})')

    traps = output.get('traps', [])
    if traps:
        print(f'\nTraps: {len(traps)}')
        for t in sorted(traps, key=lambda x: x['hit_rate'])[:3]:
            print(f'  {t["direction"]} {t["values"]}: {t["hit_rate"]:.1f}% (n={t["n"]})')

    if args.telegram:
        from send_telegram import send_message
        msg = format_telegram(output)
        result = send_message(msg)
        print(f'Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
