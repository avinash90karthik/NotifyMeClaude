#!/usr/bin/env python3
"""Silver Hawk Trading - Backtest Engine.
Validates v5 scoring against historical data using a rolling-window approach.
Uses the same calc_technicals() and score_long()/score_short() as production.

Usage:
    python backtest.py AAPL              # Single symbol
    python backtest.py AAPL NVDA TSM     # Multiple symbols
    python backtest.py --watchlist       # All from watchlist.md
    python backtest.py AAPL --telegram   # With Telegram delivery
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.md')
SCORE_THRESHOLD = 40
MIN_HISTORY_DAYS = 300  # Need ~1y+ of history


def parse_watchlist_symbols():
    """Extract symbols from memory/watchlist.md."""
    import re
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        content = f.read()
    symbols = []
    for line in content.splitlines():
        if not line.startswith('|'):
            continue
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if not cols or cols[0] in ('Symbol', '---', '-----'):
            continue
        if '---' in cols[0]:
            continue
        sym = cols[0].strip()
        if sym and re.match(r'^[A-Za-z0-9=.\-^]+$', sym):
            symbols.append(sym)
    return symbols


def backtest_symbol(symbol, period='2y', forward_days=None, capture_components=False):
    """Backtest v5 scoring for a symbol over a historical period.

    Rolling-window approach: for each trading day in the backtest period,
    compute technicals using only data up to that day, score long + short,
    then compare with actual forward returns.

    If capture_components=True, also decomposes score into individual components.
    Returns (analysis_dict, records) if capture_components else analysis_dict.
    """
    import yfinance as yf
    from indicators import calc_technicals
    from morning_screener import score_long, score_short

    if forward_days is None:
        forward_days = [1, 5, 20]

    print(f'  Downloading {symbol} ({period})...')
    try:
        df = yf.download(symbol, period=period, progress=False)
    except Exception as e:
        print(f'  {symbol}: download failed — {e}')
        return None
    # Flatten MultiIndex columns from yf.download single symbol
    if df is not None and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    if df is None or len(df) < MIN_HISTORY_DAYS:
        print(f'  {symbol}: insufficient data ({len(df) if df is not None else 0} days)')
        return None

    # Need at least 200 days for SMA200 + forward window
    max_forward = max(forward_days)
    backtest_start = 250  # Start backtesting from day 250 onward (need SMA200 warmup)
    backtest_end = len(df) - max_forward  # Stop early enough for forward returns

    if backtest_start >= backtest_end:
        print(f'  {symbol}: not enough data for backtest window')
        return None

    records = []
    errors = 0
    total_days = backtest_end - backtest_start
    print(f'  Backtesting {symbol}: {total_days} days...')

    for i in range(backtest_start, backtest_end):
        # Use only data up to day i
        window = df.iloc[:i + 1].copy()

        try:
            data = calc_technicals(window, [symbol], single=True)
            if symbol not in data:
                continue
            d = data[symbol]
            if d.get('rsi') is None:
                continue

            rw = d.get('regime_weights')
            ls, _ = score_long(d, regime=rw)
            ss, _ = score_short(d, regime=rw)
            regime = d.get('regime', 'TRANSITIONAL')

            # Actual forward returns
            fwd = {}
            for fd in forward_days:
                future_idx = i + fd
                if future_idx < len(df):
                    future_price = float(df['Close'].iloc[future_idx])
                    current_price = float(df['Close'].iloc[i])
                    if current_price > 0:
                        fwd[fd] = round((future_price - current_price) / current_price * 100, 4)

            record = {
                'date': str(df.index[i].date()),
                'price': d['price'],
                'rsi': d['rsi'],
                'regime': regime,
                'long_score': ls,
                'short_score': ss,
                'forward_returns': fwd,
            }

            if capture_components:
                _, _, components = score_long(d, regime=rw, decompose=True)
                record['components'] = components

            records.append(record)
        except (KeyError, ValueError, ZeroDivisionError, IndexError):
            errors += 1
            continue

    if errors > 0:
        print(f'  {symbol}: {errors}/{total_days} days had calc errors')

    if not records:
        print(f'  {symbol}: no valid backtest records')
        return (None, []) if capture_components else None

    analysis = analyze_results(symbol, records, forward_days)
    if capture_components:
        return (analysis, records)
    return analysis


def analyze_feature_importance(records, forward_days=None):
    """Analyze which score components best predict forward returns.
    Returns dict with per-component correlation and predictive spread."""
    if forward_days is None:
        forward_days = [5]

    results = {}
    for fd in forward_days:
        # Filter records with both components and forward returns
        valid = [r for r in records if r.get('components') and fd in r.get('forward_returns', {})]
        if len(valid) < 20:
            continue

        component_names = list(valid[0]['components'].keys())
        for comp in component_names:
            vals = np.array([r['components'][comp] for r in valid])
            fwd_rets = np.array([r['forward_returns'][fd] for r in valid])

            # Correlation
            if np.std(vals) > 0 and np.std(fwd_rets) > 0:
                corr = float(np.corrcoef(vals, fwd_rets)[0, 1])
            else:
                corr = 0.0

            # Split at median
            median_val = np.median(vals)
            high_mask = vals > median_val
            low_mask = vals <= median_val

            avg_high = float(np.mean(fwd_rets[high_mask])) if high_mask.sum() > 0 else 0
            avg_low = float(np.mean(fwd_rets[low_mask])) if low_mask.sum() > 0 else 0
            spread = avg_high - avg_low

            # Signal strength
            if abs(corr) >= 0.15 and spread > 0.3:
                signal = 'STARK'
            elif abs(corr) >= 0.08 or spread > 0.15:
                signal = 'MITTEL'
            else:
                signal = 'SCHWACH'

            key = f'{comp}_{fd}d'
            results[key] = {
                'component': comp,
                'forward_days': fd,
                'correlation': round(corr, 4),
                'avg_high': round(avg_high, 3),
                'avg_low': round(avg_low, 3),
                'spread': round(spread, 3),
                'signal': signal,
            }

    return results


def generate_weight_report(symbol, feature_results):
    """Generate memory/backtest_results.md with feature importance data."""
    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'backtest_results.md')

    lines = [
        '# Backtest Feature Importance',
        '',
        f'**Generiert:** {datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")}',
        f'**Symbol:** {symbol}',
        '',
        '## Component Analysis',
        '',
        '| Component | Correlation | Avg High | Avg Low | Spread | Signal |',
        '|-----------|-------------|----------|---------|--------|--------|',
    ]

    for key, fr in sorted(feature_results.items()):
        emoji = '🟢' if fr['signal'] == 'STARK' else '🟡' if fr['signal'] == 'MITTEL' else '⚪'
        lines.append(
            f'| {emoji} {fr["component"]} ({fr["forward_days"]}d) | '
            f'{fr["correlation"]:+.4f} | {fr["avg_high"]:+.3f}% | '
            f'{fr["avg_low"]:+.3f}% | {fr["spread"]:+.3f}% | {fr["signal"]} |'
        )

    lines.extend([
        '',
        '## Empfehlungen',
        '',
        '- **STARK:** Komponente hat hohe Vorhersagekraft, Gewichtung beibehalten oder erhöhen',
        '- **MITTEL:** Beitrag vorhanden, Gewichtung angemessen',
        '- **SCHWACH:** Wenig Vorhersagekraft, Gewichtung prüfen',
        '',
        '> Diese Daten werden von `score_long()`/`score_short()` in morning_screener.py referenziert.',
        '',
    ])

    with open(report_file, 'w') as f:
        f.write('\n'.join(lines))
    print(f'  Written: {report_file}')


def analyze_results(symbol, records, forward_days):
    """Analyze backtest records and compute statistics."""
    total = len(records)

    # Signal distribution
    long_signals = [r for r in records if r['long_score'] >= SCORE_THRESHOLD]
    short_signals = [r for r in records if r['short_score'] >= SCORE_THRESHOLD]

    # Hit rates per forward window
    hit_rates = {}
    for fd in forward_days:
        # LONG hit: positive forward return when long signal
        long_with_fwd = [r for r in long_signals if fd in r['forward_returns']]
        if long_with_fwd:
            long_hits = sum(1 for r in long_with_fwd if r['forward_returns'][fd] > 0)
            long_avg = np.mean([r['forward_returns'][fd] for r in long_with_fwd])
            hit_rates[f'LONG_{fd}d'] = {
                'hit_rate': round(long_hits / len(long_with_fwd) * 100, 1),
                'avg_return': round(long_avg, 2),
                'count': len(long_with_fwd),
            }

        # SHORT hit: negative forward return when short signal
        short_with_fwd = [r for r in short_signals if fd in r['forward_returns']]
        if short_with_fwd:
            short_hits = sum(1 for r in short_with_fwd if r['forward_returns'][fd] < 0)
            short_avg = np.mean([r['forward_returns'][fd] for r in short_with_fwd])
            hit_rates[f'SHORT_{fd}d'] = {
                'hit_rate': round(short_hits / len(short_with_fwd) * 100, 1),
                'avg_return': round(short_avg, 2),
                'count': len(short_with_fwd),
            }

    # Regime analysis
    regime_hit_rates = {}
    for regime in ('TRENDING', 'RANGE', 'CHOPPY', 'TRANSITIONAL'):
        regime_longs = [r for r in long_signals if r['regime'] == regime and 5 in r['forward_returns']]
        if len(regime_longs) >= 5:  # Need at least 5 samples
            hits = sum(1 for r in regime_longs if r['forward_returns'][5] > 0)
            regime_hit_rates[regime] = {
                'hit_rate': round(hits / len(regime_longs) * 100, 1),
                'count': len(regime_longs),
            }

    return {
        'symbol': symbol,
        'total_days': total,
        'long_signals': len(long_signals),
        'short_signals': len(short_signals),
        'long_pct': round(len(long_signals) / total * 100, 1),
        'short_pct': round(len(short_signals) / total * 100, 1),
        'hit_rates': hit_rates,
        'regime_hit_rates': regime_hit_rates,
    }


def format_results(result):
    """Format backtest results as readable text."""
    if not result:
        return 'No results.\n'

    sym = result['symbol']
    lines = [
        f'BACKTEST: {sym} ({result["total_days"]} Tage)',
        '=' * 45,
        '',
        'Signal-Verteilung:',
        f'  LONG (Score >= {SCORE_THRESHOLD}):  {result["long_signals"]} Tage ({result["long_pct"]}%)',
        f'  SHORT (Score >= {SCORE_THRESHOLD}): {result["short_signals"]} Tage ({result["short_pct"]}%)',
        '',
        'Hit Rate (Signal korrekt):',
    ]

    for key, hr in sorted(result['hit_rates'].items()):
        direction, period = key.split('_')
        lines.append(f'  {direction} {period}:  {hr["hit_rate"]}% | avg {hr["avg_return"]:+.2f}% | n={hr["count"]}')

    if result['regime_hit_rates']:
        lines.append('')
        lines.append('Regime-Analyse (LONG 5d):')
        overall_5d = result['hit_rates'].get('LONG_5d', {}).get('hit_rate', 0)
        for regime, rhr in sorted(result['regime_hit_rates'].items()):
            delta = rhr['hit_rate'] - overall_5d
            marker = ' ✅' if delta > 5 else (' ⚠️' if delta < -5 else '')
            lines.append(f'  {regime:14s} {rhr["hit_rate"]}% (n={rhr["count"]}){marker}')

    lines.append('')
    return '\n'.join(lines)


def format_telegram(results):
    """Format multiple results for Telegram."""
    msg = f'<b>BACKTEST REPORT</b>\n'
    msg += f'{datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")}\n\n'

    for r in results:
        if not r:
            continue
        sym = r['symbol']
        msg += f'<b>{sym}</b> ({r["total_days"]}d)\n'
        msg += f'  L:{r["long_signals"]} ({r["long_pct"]}%) | S:{r["short_signals"]} ({r["short_pct"]}%)\n'

        for key in ('LONG_5d', 'SHORT_5d'):
            hr = r['hit_rates'].get(key)
            if hr:
                direction = key.split('_')[0]
                emoji = '🟢' if hr['hit_rate'] >= 55 else '🔴' if hr['hit_rate'] < 45 else '🟡'
                msg += f'  {emoji} {direction} 5d: {hr["hit_rate"]}% ({hr["avg_return"]:+.2f}%)\n'

        if r['regime_hit_rates']:
            best = max(r['regime_hit_rates'].items(), key=lambda x: x[1]['hit_rate'])
            worst = min(r['regime_hit_rates'].items(), key=lambda x: x[1]['hit_rate'])
            msg += f'  Best regime: {best[0]} {best[1]["hit_rate"]}%\n'
            if worst[0] != best[0]:
                msg += f'  Worst: {worst[0]} {worst[1]["hit_rate"]}%\n'

        msg += '\n'

    msg += f'<i>Score Threshold: {SCORE_THRESHOLD} | Backtest Engine v1</i>'
    return msg


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Backtest Engine')
    parser.add_argument('symbols', nargs='*', help='Symbols to backtest')
    parser.add_argument('--watchlist', action='store_true', help='Backtest all watchlist symbols')
    parser.add_argument('--telegram', action='store_true', help='Send results via Telegram')
    parser.add_argument('--period', default='2y', help='Data period (default: 2y)')
    parser.add_argument('--feature-importance', action='store_true', help='Analyze feature importance')
    args = parser.parse_args()

    if args.watchlist:
        symbols = parse_watchlist_symbols()
        if not symbols:
            print('No symbols found in watchlist.md')
            sys.exit(1)
        print(f'Backtesting {len(symbols)} watchlist symbols...')
    elif args.symbols:
        symbols = args.symbols
    else:
        parser.print_help()
        sys.exit(1)

    results = []
    all_records = {}
    for sym in symbols:
        print(f'\n{"="*50}')
        if args.feature_importance:
            out = backtest_symbol(sym, period=args.period, capture_components=True)
            if out and out[0]:
                result, records = out
                print(format_results(result))
                results.append(result)
                all_records[sym] = records
        else:
            result = backtest_symbol(sym, period=args.period)
            if result:
                print(format_results(result))
                results.append(result)

    if not results:
        print('No valid backtest results.')
        sys.exit(1)

    # Summary
    print(f'\n{"="*50}')
    print(f'SUMMARY: {len(results)}/{len(symbols)} symbols backtested')
    avg_hit = np.mean([r['hit_rates'].get('LONG_5d', {}).get('hit_rate', 0) for r in results if r['hit_rates'].get('LONG_5d')])
    if not np.isnan(avg_hit):
        print(f'Average LONG 5d hit rate: {avg_hit:.1f}%')

    # Feature importance analysis
    if args.feature_importance and all_records:
        print(f'\n{"="*50}')
        print('FEATURE IMPORTANCE ANALYSIS')
        for sym, recs in all_records.items():
            fi = analyze_feature_importance(recs, forward_days=[5])
            if fi:
                print(f'\n{sym}:')
                for key, fr in sorted(fi.items()):
                    print(f'  {fr["component"]:8s} corr={fr["correlation"]:+.4f} '
                          f'spread={fr["spread"]:+.3f}% {fr["signal"]}')
                generate_weight_report(sym, fi)

    if args.telegram:
        from send_telegram import send_message
        msg = format_telegram(results)
        send_message(msg)


if __name__ == '__main__':
    main()
