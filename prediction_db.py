#!/usr/bin/env python3
"""Silver Hawk — Prediction Database.

Records every analysis prediction and backtests against real outcomes.
SQLite-based, zero dependencies beyond yfinance.

Usage:
    # Record a prediction (from Step 4 of analysis)
    python prediction_db.py record NVDA --direction LONG --confidence 68 \
        --entry 135.50 --stop 128.00 --target 155.00 --ko 120.00

    # Fill outcomes for all open predictions (run daily or after trades close)
    python prediction_db.py fill

    # Analyze prediction quality
    python prediction_db.py analyze

    # Analyze with Telegram delivery
    python prediction_db.py analyze --telegram

    # Show all predictions
    python prediction_db.py list

    # Export as CSV
    python prediction_db.py export

    # Mark a prediction as actually traded
    python prediction_db.py trade 1 --actual-entry 135.00 --actual-exit 155.00 \
        --actual-pnl 14.8 --notes "Scout only, no confirmation"
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'memory', 'predictions.db')


def get_db():
    """Get database connection, create tables if needed."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
        confidence INTEGER NOT NULL CHECK(confidence BETWEEN 0 AND 100),
        entry_price REAL NOT NULL,
        stop_price REAL NOT NULL,
        target_price REAL NOT NULL,
        ko_level REAL,
        regime TEXT,
        atr_pct REAL,

        -- Outcomes (filled by 'fill' command)
        price_1d REAL,
        price_3d REAL,
        price_5d REAL,
        price_10d REAL,
        price_20d REAL,
        max_favorable REAL,
        max_adverse REAL,
        stop_triggered INTEGER DEFAULT 0,
        stop_triggered_day INTEGER,
        target_hit INTEGER DEFAULT 0,
        target_hit_day INTEGER,
        plus20_hit INTEGER DEFAULT 0,
        plus20_hit_day INTEGER,
        outcome_filled INTEGER DEFAULT 0,
        outcome_filled_at TEXT,

        -- Trade tracking (optional: filled if trade was actually taken)
        trade_taken INTEGER DEFAULT 0,
        actual_entry REAL,
        actual_exit REAL,
        actual_pnl_pct REAL,
        trade_notes TEXT
    )''')
    conn.commit()
    return conn


def record_prediction(args):
    """Record a new analysis prediction."""
    conn = get_db()
    conn.execute('''INSERT INTO predictions
        (symbol, direction, confidence, entry_price, stop_price, target_price,
         ko_level, regime, atr_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (args.symbol.upper(), args.direction.upper(), args.confidence,
         args.entry, args.stop, args.target,
         args.ko, args.regime, args.atr_pct))
    conn.commit()
    rid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    print(f'Prediction #{rid} recorded: {args.symbol} {args.direction} '
          f'conf={args.confidence}% entry=${args.entry} stop=${args.stop} target=${args.target}')
    conn.close()


def fill_outcomes(args):
    """Fill real market outcomes for all predictions that are old enough."""
    import yfinance as yf
    conn = get_db()

    rows = conn.execute('''SELECT * FROM predictions
        WHERE outcome_filled = 0
        AND created_at < datetime('now', '-1 day')
    ''').fetchall()

    if not rows:
        print('No predictions to fill.')
        conn.close()
        return

    print(f'Filling outcomes for {len(rows)} predictions...')

    for row in rows:
        pid = row['id']
        sym = row['symbol']
        direction = row['direction']
        entry = row['entry_price']
        stop = row['stop_price']
        target = row['target_price']
        created = datetime.fromisoformat(row['created_at'])

        start = created.date()
        end = start + timedelta(days=35)
        today = datetime.now(timezone.utc).date()
        if end > today:
            end = today

        try:
            df = yf.download(sym, start=str(start), end=str(end), progress=False)
            if df is not None and df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f'  #{pid} {sym}: download error -- {e}')
            continue

        if df is None or len(df) < 2:
            print(f'  #{pid} {sym}: insufficient data')
            continue

        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values

        price_1d = float(closes[1]) if len(closes) > 1 else None
        price_3d = float(closes[3]) if len(closes) > 3 else None
        price_5d = float(closes[5]) if len(closes) > 5 else None
        price_10d = float(closes[10]) if len(closes) > 10 else None
        price_20d = float(closes[20]) if len(closes) > 20 else None

        # Max favorable / adverse excursion
        if direction == 'LONG':
            max_favorable = round((float(max(highs[1:])) - entry) / entry * 100, 2) if len(highs) > 1 else 0
            max_adverse = round((float(min(lows[1:])) - entry) / entry * 100, 2) if len(lows) > 1 else 0
        else:
            max_favorable = round((entry - float(min(lows[1:]))) / entry * 100, 2) if len(lows) > 1 else 0
            max_adverse = round((float(max(highs[1:])) - entry) / entry * 100, 2) if len(highs) > 1 else 0

        # Stop triggered?
        stop_triggered = 0
        stop_day = None
        for i in range(1, len(df)):
            if direction == 'LONG' and float(lows[i]) <= stop:
                stop_triggered = 1
                stop_day = i
                break
            elif direction == 'SHORT' and float(highs[i]) >= stop:
                stop_triggered = 1
                stop_day = i
                break

        # Target hit?
        target_hit = 0
        target_day = None
        for i in range(1, len(df)):
            if direction == 'LONG' and float(highs[i]) >= target:
                target_hit = 1
                target_day = i
                break
            elif direction == 'SHORT' and float(lows[i]) <= target:
                target_hit = 1
                target_day = i
                break

        # +20% on certificate (not underlying) — approximate via leverage
        ko = row['ko_level']
        plus20_hit = 0
        plus20_day = None
        if ko and ko > 0:
            leverage = entry / abs(entry - ko) if abs(entry - ko) > 0.01 else 1
            needed_move_pct = 20.0 / leverage

            for i in range(1, len(df)):
                if direction == 'LONG':
                    move = (float(highs[i]) - entry) / entry * 100
                elif direction == 'SHORT':
                    move = (entry - float(lows[i])) / entry * 100
                else:
                    move = 0
                if move >= needed_move_pct:
                    plus20_hit = 1
                    plus20_day = i
                    break

        # Only mark as filled if we have enough data (at least 5 days)
        days_available = len(df) - 1
        if days_available < 5:
            print(f'  #{pid} {sym}: only {days_available} days available, waiting...')
            continue

        conn.execute('''UPDATE predictions SET
            price_1d=?, price_3d=?, price_5d=?, price_10d=?, price_20d=?,
            max_favorable=?, max_adverse=?,
            stop_triggered=?, stop_triggered_day=?,
            target_hit=?, target_hit_day=?,
            plus20_hit=?, plus20_hit_day=?,
            outcome_filled=1, outcome_filled_at=?
            WHERE id=?''',
            (price_1d, price_3d, price_5d, price_10d, price_20d,
             max_favorable, max_adverse,
             stop_triggered, stop_day,
             target_hit, target_day,
             plus20_hit, plus20_day,
             datetime.now(timezone.utc).isoformat(),
             pid))

        stop_str = f'day {stop_day}' if stop_triggered else 'NO'
        tgt_str = f'day {target_day}' if target_hit else 'NO'
        p20_str = f'day {plus20_day}' if plus20_hit else 'NO'
        print(f'  #{pid} {sym} {direction}: MFE={max_favorable:+.1f}% MAE={max_adverse:+.1f}% '
              f'Stop={stop_str} Target={tgt_str} +20%={p20_str}')

    conn.commit()
    conn.close()


def analyze_predictions(args):
    """Analyze prediction quality."""
    conn = get_db()

    filled = conn.execute('SELECT * FROM predictions WHERE outcome_filled = 1').fetchall()
    total = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
    unfilled = total - len(filled)

    if not filled:
        print('No filled predictions to analyze yet.')
        print(f'Total predictions: {total} | Unfilled: {unfilled}')
        conn.close()
        return

    lines = []
    lines.append(f'PREDICTION ANALYSIS ({len(filled)} filled, {unfilled} pending)')
    lines.append('=' * 60)

    stop_hits = sum(1 for r in filled if r['stop_triggered'])
    target_hits = sum(1 for r in filled if r['target_hit'])
    plus20_hits = sum(1 for r in filled if r['plus20_hit'])

    lines.append(f'\nOverall (n={len(filled)}):')
    lines.append(f'  Stop triggered:  {stop_hits}/{len(filled)} ({stop_hits/len(filled)*100:.0f}%)')
    lines.append(f'  Target hit:      {target_hits}/{len(filled)} ({target_hits/len(filled)*100:.0f}%)')
    lines.append(f'  +20% cert hit:   {plus20_hits}/{len(filled)} ({plus20_hits/len(filled)*100:.0f}%)')

    avg_mfe = sum(r['max_favorable'] for r in filled) / len(filled)
    avg_mae = sum(r['max_adverse'] for r in filled) / len(filled)
    lines.append(f'  Avg MFE (max favorable): {avg_mfe:+.1f}%')
    lines.append(f'  Avg MAE (max adverse):   {avg_mae:+.1f}%')

    # By confidence bracket
    brackets = [(50, 59), (60, 69), (70, 79), (80, 100)]
    lines.append(f'\nBy Confidence Bracket:')
    lines.append(f'  {"Bracket":<10} {"n":>4} {"Stop%":>7} {"Target%":>8} {"+20%":>6} {"MFE":>7} {"MAE":>7}')
    lines.append(f'  {"-"*50}')

    for low, high in brackets:
        b = [r for r in filled if low <= r['confidence'] <= high]
        if not b:
            continue
        n = len(b)
        s_pct = sum(1 for r in b if r['stop_triggered']) / n * 100
        t_pct = sum(1 for r in b if r['target_hit']) / n * 100
        p20 = sum(1 for r in b if r['plus20_hit']) / n * 100
        mfe = sum(r['max_favorable'] for r in b) / n
        mae = sum(r['max_adverse'] for r in b) / n
        label = f'{low}-{high}%'
        lines.append(f'  {label:<10} {n:>4} {s_pct:>6.0f}% {t_pct:>7.0f}% {p20:>5.0f}% {mfe:>+6.1f}% {mae:>+6.1f}%')

    # By direction
    for direction in ('LONG', 'SHORT'):
        d = [r for r in filled if r['direction'] == direction]
        if not d:
            continue
        n = len(d)
        s_pct = sum(1 for r in d if r['stop_triggered']) / n * 100
        t_pct = sum(1 for r in d if r['target_hit']) / n * 100
        lines.append(f'\n{direction} (n={n}): Stop={s_pct:.0f}% Target={t_pct:.0f}%')

    # By regime
    regimes = set(r['regime'] for r in filled if r['regime'])
    if regimes:
        lines.append(f'\nBy Regime:')
        for regime in sorted(regimes):
            rg = [r for r in filled if r['regime'] == regime]
            n = len(rg)
            s_pct = sum(1 for r in rg if r['stop_triggered']) / n * 100
            t_pct = sum(1 for r in rg if r['target_hit']) / n * 100
            lines.append(f'  {regime:<15} n={n:>3} Stop={s_pct:.0f}% Target={t_pct:.0f}%')

    # Key question: Does higher confidence = better outcome?
    lines.append(f'\n{"=" * 60}')
    lines.append('KEY QUESTION: Does confidence predict success?')
    high_conf = [r for r in filled if r['confidence'] >= 70]
    low_conf = [r for r in filled if r['confidence'] < 65]
    if high_conf and low_conf:
        hc_target = sum(1 for r in high_conf if r['target_hit']) / len(high_conf) * 100
        lc_target = sum(1 for r in low_conf if r['target_hit']) / len(low_conf) * 100
        hc_stop = sum(1 for r in high_conf if r['stop_triggered']) / len(high_conf) * 100
        lc_stop = sum(1 for r in low_conf if r['stop_triggered']) / len(low_conf) * 100
        lines.append(f'  High conf (>=70%, n={len(high_conf)}): Target={hc_target:.0f}% Stop={hc_stop:.0f}%')
        lines.append(f'  Low conf  (<65%, n={len(low_conf)}):  Target={lc_target:.0f}% Stop={lc_stop:.0f}%')
        if hc_target > lc_target:
            lines.append(f'  -> YES: Higher confidence correlates with better outcomes (+{hc_target-lc_target:.0f}% target rate)')
        else:
            lines.append(f'  -> NO: Confidence does NOT predict success. Recalibrate!')
    else:
        lines.append('  Not enough data in both brackets yet.')

    # Forward return distribution
    lines.append(f'\nForward Returns (from entry):')
    for day_col, label in [('price_5d', '5d'), ('price_10d', '10d'), ('price_20d', '20d')]:
        vals = [(float(r[day_col]) - r['entry_price']) / r['entry_price'] * 100
                for r in filled if r[day_col] is not None]
        if vals:
            import numpy as np
            vals_arr = np.array(vals)
            win_pct = (vals_arr > 0).sum() / len(vals_arr) * 100
            lines.append(f'  {label}: avg={np.mean(vals_arr):+.1f}% med={np.median(vals_arr):+.1f}% win={win_pct:.0f}% (n={len(vals_arr)})')

    output = '\n'.join(lines)
    print(output)

    if args.telegram:
        msg = f'<b>PREDICTION ANALYSIS</b>\n'
        msg += f'{datetime.now(timezone.utc).strftime("%d.%m.%Y")}\n\n'
        msg += f'Predictions: {len(filled)} filled, {unfilled} pending\n'
        msg += f'Stop rate: {stop_hits/len(filled)*100:.0f}%\n'
        msg += f'Target rate: {target_hits/len(filled)*100:.0f}%\n'
        msg += f'+20% cert rate: {plus20_hits/len(filled)*100:.0f}%\n'
        msg += f'MFE/MAE: {avg_mfe:+.1f}% / {avg_mae:+.1f}%\n'

        try:
            from send_telegram import send_message
            send_message(msg)
            print('Telegram sent.')
        except Exception as e:
            print(f'Telegram error: {e}')

    conn.close()


def list_predictions(args):
    """List all predictions."""
    conn = get_db()
    rows = conn.execute('SELECT * FROM predictions ORDER BY created_at DESC').fetchall()

    if not rows:
        print('No predictions yet.')
        conn.close()
        return

    print(f'{"ID":>4} {"Date":<12} {"Symbol":<8} {"Dir":<6} {"Conf":>4} {"Entry":>8} {"Stop":>8} {"Target":>8} {"Filled":>6} {"Stop?":>5} {"Tgt?":>5}')
    print('-' * 90)

    for r in rows:
        date = r['created_at'][:10]
        filled = 'YES' if r['outcome_filled'] else '...'
        stop = 'HIT' if r['stop_triggered'] else ('--' if not r['outcome_filled'] else 'OK')
        tgt = 'HIT' if r['target_hit'] else ('--' if not r['outcome_filled'] else 'NO')
        print(f'{r["id"]:>4} {date:<12} {r["symbol"]:<8} {r["direction"]:<6} {r["confidence"]:>3}% '
              f'${r["entry_price"]:>7.2f} ${r["stop_price"]:>7.2f} ${r["target_price"]:>7.2f} {filled:>6} {stop:>5} {tgt:>5}')

    conn.close()


def export_predictions(args):
    """Export predictions as CSV."""
    conn = get_db()
    rows = conn.execute('SELECT * FROM predictions ORDER BY created_at').fetchall()

    if not rows:
        print('No predictions to export.')
        conn.close()
        return

    cols = [desc[0] for desc in conn.execute('SELECT * FROM predictions LIMIT 1').description]
    output_path = os.path.join(SCRIPT_DIR, 'memory', 'predictions_export.csv')

    with open(output_path, 'w') as f:
        f.write(','.join(cols) + '\n')
        for r in rows:
            values = [str(r[c]) if r[c] is not None else '' for c in cols]
            f.write(','.join(values) + '\n')

    print(f'Exported {len(rows)} predictions to {output_path}')
    conn.close()


def mark_trade(args):
    """Mark a prediction as trade-taken with actual results."""
    conn = get_db()
    conn.execute('''UPDATE predictions SET
        trade_taken = 1,
        actual_entry = ?,
        actual_exit = ?,
        actual_pnl_pct = ?,
        trade_notes = ?
        WHERE id = ?''',
        (args.actual_entry, args.actual_exit, args.actual_pnl, args.notes, args.id))
    conn.commit()
    print(f'Prediction #{args.id} marked as traded: PnL={args.actual_pnl:+.1f}%')
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Prediction Database')
    sub = parser.add_subparsers(dest='command')

    # Record
    p_rec = sub.add_parser('record', help='Record a new prediction')
    p_rec.add_argument('symbol', help='Ticker symbol')
    p_rec.add_argument('--direction', required=True, choices=['LONG', 'SHORT'])
    p_rec.add_argument('--confidence', required=True, type=int)
    p_rec.add_argument('--entry', required=True, type=float)
    p_rec.add_argument('--stop', required=True, type=float)
    p_rec.add_argument('--target', required=True, type=float)
    p_rec.add_argument('--ko', type=float, default=None)
    p_rec.add_argument('--regime', type=str, default=None)
    p_rec.add_argument('--atr-pct', type=float, default=None)

    # Fill
    sub.add_parser('fill', help='Fill outcomes for open predictions')

    # Analyze
    p_ana = sub.add_parser('analyze', help='Analyze prediction quality')
    p_ana.add_argument('--telegram', action='store_true')

    # List
    sub.add_parser('list', help='List all predictions')

    # Export
    sub.add_parser('export', help='Export as CSV')

    # Mark trade
    p_trade = sub.add_parser('trade', help='Mark prediction as traded')
    p_trade.add_argument('id', type=int)
    p_trade.add_argument('--actual-entry', type=float, required=True)
    p_trade.add_argument('--actual-exit', type=float, required=True)
    p_trade.add_argument('--actual-pnl', type=float, required=True)
    p_trade.add_argument('--notes', type=str, default='')

    args = parser.parse_args()

    if args.command == 'record':
        record_prediction(args)
    elif args.command == 'fill':
        fill_outcomes(args)
    elif args.command == 'analyze':
        analyze_predictions(args)
    elif args.command == 'list':
        list_predictions(args)
    elif args.command == 'export':
        export_predictions(args)
    elif args.command == 'trade':
        mark_trade(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
