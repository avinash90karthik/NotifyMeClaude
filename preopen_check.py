#!/usr/bin/env python3
"""Silver Hawk Trading - Pre-Open Verdict.

On-demand check before US open: should you buy NOW or WAIT?
Uses pattern DB from preopen_backtest.py + live technicals.

Usage:
    python preopen_check.py SYMBOL1 SYMBOL2
    python preopen_check.py SYMBOL --telegram
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PATTERNS_FILE = os.path.join(SCRIPT_DIR, 'memory', 'preopen_patterns.json')
ET = ZoneInfo('America/New_York')


ENTRY_TIMING_CACHE = os.path.join(SCRIPT_DIR, 'memory', 'entry_timing_cache.json')


def load_patterns():
    """Load pattern DB."""
    if not os.path.exists(PATTERNS_FILE):
        return None
    with open(PATTERNS_FILE) as f:
        return json.load(f)


def analyze_entry_timing(sym, force=False):
    """Analyze optimal entry timing (Pre-Market vs Open vs First-Hour Dip).

    Downloads 2y daily + hourly data, computes win% per gap bucket.
    Results are cached in memory/entry_timing_cache.json and invalidated
    when preopen_patterns.json is newer than the cache entry.

    Returns dict with best_entry and per-bucket statistics, or None on error.
    """
    import yfinance as yf
    import numpy as np

    # Check cache (invalidate when patterns file is newer)
    if not force and os.path.exists(ENTRY_TIMING_CACHE):
        try:
            with open(ENTRY_TIMING_CACHE) as f:
                cache = json.load(f)
            cached = cache.get(sym)
            if cached:
                cache_ts = cached.get('timestamp', 0)
                patterns_ts = os.path.getmtime(PATTERNS_FILE) if os.path.exists(PATTERNS_FILE) else 0
                if cache_ts > patterns_ts:
                    print(f'  Entry-Timing {sym}: cache hit')
                    return cached['data']
        except (json.JSONDecodeError, OSError):
            pass

    print(f'  Entry-Timing {sym}: computing...')

    try:
        daily = yf.download(sym, period='2y', progress=False)
        if daily is None or daily.empty or len(daily) < 60:
            return None
        if daily.columns.nlevels > 1:
            daily.columns = daily.columns.get_level_values(0)

        hourly = yf.download(sym, period='730d', interval='1h', progress=False)
        if hourly is not None and not hourly.empty:
            if hourly.columns.nlevels > 1:
                hourly.columns = hourly.columns.get_level_values(0)
            # Timezone fix: convert to ET for market-hours filtering
            if hourly.index.tz is not None:
                hourly.index = hourly.index.tz_convert(ET)
            else:
                hourly.index = hourly.index.tz_localize('UTC').tz_convert(ET)
        else:
            hourly = None
    except Exception as e:
        print(f'  Entry-Timing {sym}: download error: {e}')
        return None

    results = []
    for i in range(1, len(daily)):
        prev_close = float(daily.iloc[i - 1]['Close'])
        day_open = float(daily.iloc[i]['Open'])
        day_close = float(daily.iloc[i]['Close'])
        if prev_close == 0:
            continue
        gap_pct = (day_open - prev_close) / prev_close * 100

        fh_low = None
        if hourly is not None:
            trade_date = daily.index[i]
            if hasattr(trade_date, 'date'):
                trade_date = trade_date.date()
            # Filter market hours only: 09:30-10:30 ET for first-hour low
            day_hourly = hourly[hourly.index.date == trade_date]
            fh = day_hourly.between_time('09:30', '10:30')
            if len(fh) > 0:
                fh_low = float(fh['Low'].min())

        results.append({
            'gap_pct': gap_pct,
            'pre_to_close': (day_close - prev_close) / prev_close * 100,
            'open_to_close': (day_close - day_open) / day_open * 100 if day_open != 0 else 0,
            'fh_to_close': (day_close - fh_low) / fh_low * 100 if fh_low and fh_low != 0 else None,
        })

    if not results:
        return None

    # Build buckets: all days, gap-up >1%, gap-up >3%, gap-down <-1%
    import pandas as pd
    df = pd.DataFrame(results)

    buckets = {}
    for label, subset in [
        ('all', df),
        ('gap_up_1pct', df[df['gap_pct'] > 1]),
        ('gap_up_3pct', df[df['gap_pct'] > 3]),
        ('gap_down_1pct', df[df['gap_pct'] < -1]),
    ]:
        n = len(subset)
        if n < 5:
            continue
        fh = subset['fh_to_close'].dropna()
        buckets[label] = {
            'n': n,
            'pre_market_mean': round(float(subset['pre_to_close'].mean()), 2),
            'pre_market_win_pct': round(float((subset['pre_to_close'] > 0).mean() * 100), 0),
            'at_open_mean': round(float(subset['open_to_close'].mean()), 2),
            'at_open_win_pct': round(float((subset['open_to_close'] > 0).mean() * 100), 0),
            'first_hour_dip_mean': round(float(fh.mean()), 2) if len(fh) > 0 else None,
            'first_hour_dip_win_pct': round(float((fh > 0).mean() * 100), 0) if len(fh) > 0 else None,
        }

    if not buckets:
        return None

    # Determine best entry from 'all' bucket
    all_b = buckets.get('all', {})
    pre_win = all_b.get('pre_market_win_pct', 0)
    open_win = all_b.get('at_open_win_pct', 0)
    fh_win = all_b.get('first_hour_dip_win_pct', 0) or 0

    if fh_win > pre_win and fh_win > open_win:
        best_entry = 'FIRST_HOUR_DIP'
    elif pre_win > open_win:
        best_entry = 'PRE_MARKET'
    else:
        best_entry = 'AT_OPEN'

    result = {
        'best_entry': best_entry,
        'buckets': buckets,
    }

    # Save to cache
    try:
        cache = {}
        if os.path.exists(ENTRY_TIMING_CACHE):
            with open(ENTRY_TIMING_CACHE) as f:
                cache = json.load(f)
        cache[sym] = {
            'timestamp': datetime.now(timezone.utc).timestamp(),
            'data': result,
        }
        with open(ENTRY_TIMING_CACHE, 'w') as f:
            json.dump(cache, f, indent=2)
    except (OSError, json.JSONDecodeError):
        pass

    return result


def check_symbol(sym, patterns_db, entry_timing=False, force_timing=False):
    """Run pre-open check for a single symbol.

    Returns dict with verdict, scores, pattern info, and reasoning.
    If entry_timing=True, also runs analyze_entry_timing().
    """
    import yfinance as yf
    from indicators import calc_technicals
    from morning_screener import score_long, score_short
    from preopen_backtest import tag_patterns

    # Daily data up to now (pre-open = yesterday's close is latest)
    daily = yf.download(sym, period='2y', progress=False)
    if daily is None or daily.empty:
        return {'symbol': sym, 'error': 'Keine Daten'}
    if daily.columns.nlevels > 1:
        daily.columns = daily.columns.get_level_values(0)

    if len(daily) < 250:
        return {'symbol': sym, 'error': f'Zu wenig History ({len(daily)}d)'}

    # Technicals on latest daily data
    data = calc_technicals(daily, [sym], single=True)
    if sym not in data:
        return {'symbol': sym, 'error': 'calc_technicals fehlgeschlagen'}

    d = data[sym]
    if d.get('rsi') is None:
        return {'symbol': sym, 'error': 'RSI nicht berechenbar'}

    rw = d.get('regime_weights')
    ls, lsig = score_long(d, regime=rw)
    ss, ssig = score_short(d, regime=rw)
    d['_score_long'] = ls
    d['_score_short'] = ss

    # Gap fill rate from pattern DB
    gap_fill_rates = []
    long_hit_rates = []
    short_hit_rates = []
    best_long_pat = None
    best_short_pat = None

    if patterns_db:
        pats = patterns_db.get('primary_patterns', {})

        for gap_val in (-2.0, 0.0, 2.0):
            tags = tag_patterns(d, gap_val)

            for direction, pat_dict, hit_list in [
                ('LONG', pats.get('LONG', {}), long_hit_rates),
                ('SHORT', pats.get('SHORT', {}), short_hit_rates),
            ]:
                for key, p in pat_dict.items():
                    combo_dims = p['combo'].split('+')
                    pat_vals = p['values'].split('|')
                    if len(combo_dims) != len(pat_vals):
                        continue
                    if all(tags.get(dim) == val for dim, val in zip(combo_dims, pat_vals)):
                        hr = p.get('hit_4h') or p.get('hit_close') or 0
                        n = p.get('n', 0)
                        hit_list.append({'pattern': p['values'], 'combo': p['combo'],
                                         'hit': hr, 'n': n, 'gap_fill': p.get('gap_fill')})
                        if p.get('gap_fill') is not None:
                            gap_fill_rates.append(p['gap_fill'])

        # Best patterns (highest n for reliability)
        if long_hit_rates:
            best_long_pat = max(long_hit_rates, key=lambda x: x['n'])
        if short_hit_rates:
            best_short_pat = max(short_hit_rates, key=lambda x: x['n'])

    # Gap fill summary
    avg_gap_fill = round(sum(gap_fill_rates) / len(gap_fill_rates), 0) if gap_fill_rates else None

    # Compute long vs short bias from patterns
    avg_long_hit = round(sum(p['hit'] for p in long_hit_rates) / len(long_hit_rates), 1) if long_hit_rates else None
    avg_short_hit = round(sum(p['hit'] for p in short_hit_rates) / len(short_hit_rates), 1) if short_hit_rates else None

    # Entry timing analysis
    entry_timing_data = None
    if entry_timing:
        entry_timing_data = analyze_entry_timing(sym, force=force_timing)
        if entry_timing_data:
            d['_entry_timing'] = entry_timing_data

    # Build verdict
    reasons = []
    verdict = 'WAIT'

    gate_passed = ls >= 60 or ss >= 60
    direction = 'LONG' if ls > ss else 'SHORT'
    best_score = max(ls, ss)

    if not gate_passed:
        verdict = 'KEIN TRADE'
        reasons.append(f'Score {best_score} unter 60%-Gate')
    else:
        # Check pattern bias
        if direction == 'LONG' and best_long_pat:
            if best_long_pat['hit'] >= 60:
                verdict = 'LONG'
                reasons.append(f'Pattern {best_long_pat["hit"]:.0f}% LONG (n={best_long_pat["n"]})')
            elif best_long_pat['hit'] < 50:
                verdict = 'WAIT'
                reasons.append(f'Pattern nur {best_long_pat["hit"]:.0f}% LONG — Falle!')
        elif direction == 'SHORT' and best_short_pat:
            if best_short_pat['hit'] >= 60:
                verdict = 'SHORT'
                reasons.append(f'Pattern {best_short_pat["hit"]:.0f}% SHORT (n={best_short_pat["n"]})')
            elif best_short_pat['hit'] < 50:
                verdict = 'WAIT'
                reasons.append(f'Pattern nur {best_short_pat["hit"]:.0f}% SHORT — Falle!')

        if not reasons:
            verdict = direction
            reasons.append(f'Score {best_score} ({direction})')

    # Gap fill warning (from pattern DB)
    if avg_gap_fill is not None and avg_gap_fill >= 80:
        reasons.append(f'Gap Fill {avg_gap_fill:.0f}%')

    # Entry-timing override (from analyze_entry_timing if available)
    entry_timing = d.get('_entry_timing')
    if entry_timing:
        best = entry_timing.get('best_entry', '')
        all_b = entry_timing.get('buckets', {}).get('all', {})
        if best == 'FIRST_HOUR_DIP' and all_b.get('first_hour_dip_win_pct'):
            reasons.append(f'Entry: First-Hour Dip ({all_b["first_hour_dip_win_pct"]:.0f}% Win)')
            if verdict in ('LONG', 'SHORT'):
                verdict = f'{verdict} (NACH OPEN)'
        elif best == 'PRE_MARKET' and all_b.get('pre_market_win_pct'):
            reasons.append(f'Entry: Pre-Market ({all_b["pre_market_win_pct"]:.0f}% Win)')
    elif avg_gap_fill is not None and avg_gap_fill >= 80:
        if verdict in ('LONG', 'SHORT'):
            verdict = f'{verdict} (NACH OPEN)'

    # BB Squeeze warning
    bb = d.get('bb_width_percentile')
    if bb is not None and bb < 10:
        reasons.append('BB Squeeze — Ausbruch kommt, Richtung unsicher')

    # ATR warning
    atr = d.get('atr_pct')
    if atr and atr > 5:
        reasons.append(f'ATR {atr:.1f}% — nur Klein/Lotto')
    if atr and atr > 7:
        reasons.append(f'ATR {atr:.1f}% — NUR ohne Hebel!')

    # Short bias from patterns even if LONG score higher
    if avg_long_hit and avg_short_hit and avg_short_hit > avg_long_hit + 5:
        reasons.append(f'SHORT-Bias aus Patterns ({avg_short_hit:.0f}% vs LONG {avg_long_hit:.0f}%)')

    return {
        'symbol': sym,
        'verdict': verdict,
        'reasons': reasons,
        'long_score': ls,
        'short_score': ss,
        'long_signals': lsig,
        'short_signals': ssig,
        'rsi': d.get('rsi'),
        'atr_pct': atr,
        'adx': d.get('adx'),
        'regime': d.get('regime'),
        'bb_pctl': bb,
        'sma200_dist': d.get('sma200_distance_pct'),
        'gap_fill': avg_gap_fill,
        'pattern_long': best_long_pat,
        'pattern_short': best_short_pat,
        'pattern_long_hit': avg_long_hit,
        'pattern_short_hit': avg_short_hit,
        'entry_timing': entry_timing,
    }


def format_verdict(r):
    """Format a single symbol verdict for console/Telegram."""
    if r.get('error'):
        return f'{r["symbol"]}: {r["error"]}'

    # Verdict emoji
    v = r['verdict']
    if 'LONG' in v:
        emoji = '\U0001f7e2'  # green
    elif 'SHORT' in v:
        emoji = '\U0001f534'  # red
    elif v == 'KEIN TRADE':
        emoji = '\u26d4'  # no entry
    else:
        emoji = '\u23f3'  # hourglass (WAIT)

    sym = r['symbol']
    lines = [f'{emoji} <b>{sym}</b> — {v}']

    # Scores
    lines.append(f'   LONG {r["long_score"]}/100 | SHORT {r["short_score"]}/100')

    # Key indicators
    parts = [f'RSI {r["rsi"]:.0f}']
    if r.get('adx'):
        parts.append(f'ADX {r["adx"]:.0f}')
    if r.get('atr_pct'):
        parts.append(f'ATR {r["atr_pct"]:.1f}%')
    if r.get('regime'):
        parts.append(r['regime'])
    lines.append(f'   {" | ".join(parts)}')

    # Pattern info
    if r.get('pattern_long_hit') or r.get('pattern_short_hit'):
        pat_parts = []
        if r.get('pattern_long_hit'):
            pat_parts.append(f'LONG {r["pattern_long_hit"]:.0f}%')
        if r.get('pattern_short_hit'):
            pat_parts.append(f'SHORT {r["pattern_short_hit"]:.0f}%')
        lines.append(f'   Pattern: {" | ".join(pat_parts)}')

    if r.get('gap_fill') is not None:
        lines.append(f'   Gap Fill: {r["gap_fill"]:.0f}%')

    if r.get('bb_pctl') is not None and r['bb_pctl'] < 10:
        lines.append(f'   BB Squeeze: {r["bb_pctl"]:.1f}%')

    # Entry timing
    et = r.get('entry_timing')
    if et:
        all_b = et.get('buckets', {}).get('all', {})
        best = et.get('best_entry', '?')
        parts = []
        if all_b.get('pre_market_win_pct') is not None:
            parts.append(f'Pre {all_b["pre_market_win_pct"]:.0f}%')
        if all_b.get('at_open_win_pct') is not None:
            parts.append(f'Open {all_b["at_open_win_pct"]:.0f}%')
        if all_b.get('first_hour_dip_win_pct') is not None:
            parts.append(f'FH-Dip {all_b["first_hour_dip_win_pct"]:.0f}%')
        if parts:
            lines.append(f'   Entry: {best} ({" | ".join(parts)})')

    # Reasons
    for reason in r.get('reasons', []):
        lines.append(f'   \u2192 {reason}')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Pre-Open Verdict')
    parser.add_argument('symbols', nargs='+', help='Symbols to check')
    parser.add_argument('--telegram', action='store_true', help='Send via Telegram')
    parser.add_argument('--entry-timing', action='store_true', help='Run entry-timing analysis')
    parser.add_argument('--force-timing', action='store_true', help='Bypass entry-timing cache')
    args = parser.parse_args()

    now_et = datetime.now(ET)
    print(f'Pre-Open Check | {now_et.strftime("%H:%M %Z")} | US-Open 09:30 ET')
    print(f'{"=" * 50}')

    patterns_db = load_patterns()
    if patterns_db:
        print(f'Pattern DB: {patterns_db["total_records"]} records, {len(patterns_db["symbols"])} symbols')
    else:
        print('Pattern DB: nicht vorhanden — Verdicts ohne Pattern-Matching')
    print()

    results = []
    for sym in args.symbols:
        print(f'  Checking {sym}...')
        r = check_symbol(sym, patterns_db,
                         entry_timing=args.entry_timing,
                         force_timing=args.force_timing)
        results.append(r)

    print(f'\n{"=" * 50}')
    msg_parts = [f'<b>PRE-OPEN CHECK</b> | {now_et.strftime("%H:%M %Z %d.%m.%Y")}\n']

    for r in results:
        txt = format_verdict(r)
        print(txt.replace('<b>', '').replace('</b>', ''))
        msg_parts.append(txt)
        print()

    if args.telegram:
        from send_telegram import send_message
        msg = '\n\n'.join(msg_parts)
        result = send_message(msg)
        print(f'Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
