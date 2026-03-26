#!/usr/bin/env python3
"""Silver Hawk Trading Dashboard — Flask API Backend.
Wraps existing Python modules (prediction_db, collect_data, indicators)
as JSON endpoints for the React frontend."""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS

# Add project root to path so we can import existing modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

DB_PATH = os.path.join(PROJECT_ROOT, 'memory', 'predictions.db')
# Watchlist is stored in predictions.db (via prediction_db.get_watchlist_symbols)
PATTERNS_PATH = os.path.join(PROJECT_ROOT, 'memory', 'preopen_patterns.json')
ANALYSES_DIR = os.path.join(PROJECT_ROOT, 'dashboard', 'data', 'analyses')

# Load .env
env_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

CHART_OUTPUT_DIR = os.environ.get('CHART_OUTPUT_DIR', os.path.join(PROJECT_ROOT, 'charts'))

# ── Simple TTL Cache ──
_cache = {}

def cached(ttl_seconds=900):
    """Simple in-memory TTL cache decorator."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{kwargs}"
            now = time.time()
            if key in _cache and now - _cache[key]['ts'] < ttl_seconds:
                return _cache[key]['val']
            result = fn(*args, **kwargs)
            _cache[key] = {'val': result, 'ts': now}
            return result
        return wrapper
    return decorator


# ── Database Helpers ──
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def row_to_dict(row):
    return dict(row) if row else None


# ── API Endpoints ──

@app.route('/api/portfolio')
def portfolio():
    """Portfolio overview: open positions, cash, closed trades."""
    conn = get_db()
    try:
        # Cash
        cash_row = conn.execute("SELECT value FROM portfolio_state WHERE key='cash'").fetchone()
        cash = float(cash_row['value']) if cash_row else 0

        # Open positions
        rows = conn.execute("""
            SELECT id, created_at, symbol, direction, confidence, entry_price,
                   stop_price, target_price, ko_level, regime, atr_pct, reason,
                   status, shares, cert_buyin, cert_type, invested_eur, realized_pnl_eur
            FROM predictions WHERE status='open'
            ORDER BY id
        """).fetchall()
        positions = [row_to_dict(r) for r in rows]

        # Closed trades — from close_events (single source for ALL sales)
        closed = conn.execute("""
            SELECT ce.id, p.symbol, p.direction, p.confidence, ce.pnl_eur as realized_pnl_eur,
                   ce.closed_at, p.cert_buyin, ce.shares, ce.reason
            FROM close_events ce
            JOIN predictions p ON p.id = ce.prediction_id
            ORDER BY ce.closed_at DESC LIMIT 20
        """).fetchall()
        closed_trades = [row_to_dict(r) for r in closed]

        total_invested = sum(p.get('invested_eur', 0) or 0 for p in positions)
        return jsonify({
            'cash': cash,
            'positions': positions,
            'closed_trades': closed_trades,
            'total_invested': total_invested,
            'portfolio_value': cash + total_invested,
            'slots_used': len(positions),
            'slots_max': 3,
        })
    finally:
        conn.close()


@app.route('/api/predictions')
def predictions():
    """All predictions, filterable by status."""
    status = request.args.get('status')
    conn = get_db()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM predictions WHERE status=? ORDER BY id DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM predictions ORDER BY id DESC").fetchall()
        return jsonify([row_to_dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/predictions/<int:pred_id>')
def prediction_detail(pred_id):
    """Single prediction with all fields."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM predictions WHERE id=?", (pred_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        result = row_to_dict(row)

        # Check for full analysis JSON
        analysis_files = [f for f in os.listdir(ANALYSES_DIR)
                          if f.startswith(f"{pred_id}_")] if os.path.exists(ANALYSES_DIR) else []
        if analysis_files:
            with open(os.path.join(ANALYSES_DIR, analysis_files[0])) as f:
                result['full_analysis'] = json.load(f)

        return jsonify(result)
    finally:
        conn.close()


@app.route('/api/analysis/<int:pred_id>')
def analysis_full(pred_id):
    """Full 4-step analysis JSON (if saved by Step 4)."""
    if not os.path.exists(ANALYSES_DIR):
        return jsonify({'error': 'No analyses directory'}), 404

    matches = [f for f in os.listdir(ANALYSES_DIR) if f.startswith(f"{pred_id}_")]
    if not matches:
        return jsonify({'error': f'No analysis found for #{pred_id}'}), 404

    with open(os.path.join(ANALYSES_DIR, matches[0])) as f:
        return jsonify(json.load(f))


@app.route('/api/collect/<symbol>')
@cached(ttl_seconds=900)
def collect_symbol(symbol):
    """Live technical data via collect_data.py (15min cache)."""
    try:
        from collect_data import collect
        data = collect(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ohlcv/<symbol>')
@cached(ttl_seconds=120)
def ohlcv(symbol):
    """OHLCV data + indicators for charting (15min cache)."""
    try:
        import yfinance as yf
        import numpy as np

        period = request.args.get('period', '6mo')
        df = yf.download(symbol, period=period, interval='1d', progress=False)
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            df.columns = df.columns.droplevel(1)

        if df.empty:
            return jsonify({'error': f'No data for {symbol}'}), 404

        # Detect currency
        try:
            ticker_info = yf.Ticker(symbol).info
            currency = ticker_info.get('currency', 'USD')
        except Exception:
            currency = 'USD'

        # Calculate overlays
        closes = df['Close'].values.astype(float)
        sma50 = df['Close'].rolling(50).mean()
        sma200 = df['Close'].rolling(200).mean()

        # Bollinger Bands
        bb_sma = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std

        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        candles = []
        for i, (idx, row) in enumerate(df.iterrows()):
            candle = {
                'time': idx.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']),
            }
            if not np.isnan(sma50.iloc[i]):
                candle['sma50'] = round(float(sma50.iloc[i]), 2)
            if not np.isnan(sma200.iloc[i]):
                candle['sma200'] = round(float(sma200.iloc[i]), 2)
            if not np.isnan(bb_upper.iloc[i]):
                candle['bb_upper'] = round(float(bb_upper.iloc[i]), 2)
                candle['bb_lower'] = round(float(bb_lower.iloc[i]), 2)
                candle['bb_middle'] = round(float(bb_sma.iloc[i]), 2)
            if not np.isnan(rsi.iloc[i]):
                candle['rsi'] = round(float(rsi.iloc[i]), 1)
            candles.append(candle)

        # Fetch today's live price and append as latest candle
        try:
            today_df = yf.download(symbol, period='1d', interval='1m', progress=False)
            if hasattr(today_df.columns, 'levels') and len(today_df.columns.levels) > 1:
                today_df.columns = today_df.columns.droplevel(1)
            if not today_df.empty:
                today_str = datetime.now().strftime('%Y-%m-%d')
                # Only add if it's a new day (not already in candles)
                if candles and candles[-1]['time'] != today_str:
                    today_open = round(float(today_df['Open'].iloc[0]), 2)
                    today_high = round(float(today_df['High'].max()), 2)
                    today_low = round(float(today_df['Low'].min()), 2)
                    today_close = round(float(today_df['Close'].iloc[-1]), 2)
                    today_vol = int(today_df['Volume'].sum())
                    candles.append({
                        'time': today_str,
                        'open': today_open,
                        'high': today_high,
                        'low': today_low,
                        'close': today_close,
                        'volume': today_vol,
                    })
                elif candles and candles[-1]['time'] == today_str:
                    # Update today's candle with latest data
                    candles[-1]['high'] = max(candles[-1]['high'], round(float(today_df['High'].max()), 2))
                    candles[-1]['low'] = min(candles[-1]['low'], round(float(today_df['Low'].min()), 2))
                    candles[-1]['close'] = round(float(today_df['Close'].iloc[-1]), 2)
                    candles[-1]['volume'] = int(today_df['Volume'].sum())
        except Exception as e:
            print(f"  Live price fetch failed for {symbol}: {e}")

        # Get S/R levels and open position KO
        ko_level = None
        conn = get_db()
        try:
            pos = conn.execute(
                "SELECT ko_level, stop_price, entry_price, target_price, direction "
                "FROM predictions WHERE symbol=? AND status='open' LIMIT 1", (symbol,)
            ).fetchone()
            if pos:
                ko_level = {
                    'ko': pos['ko_level'],
                    'stop': pos['stop_price'],
                    'entry': pos['entry_price'],
                    'target': pos['target_price'],
                    'direction': pos['direction'],
                }
        finally:
            conn.close()

        last_date = candles[-1]['time'] if candles else None
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        return jsonify({
            'symbol': symbol,
            'currency': currency,
            'last_updated': now_str if last_date == datetime.now().strftime('%Y-%m-%d') else last_date,
            'candles': candles,
            'position': ko_level,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/watchlist')
def watchlist():
    """Current watchlist data from DB."""
    from prediction_db import get_watchlist_symbols
    return jsonify(get_watchlist_symbols())


@app.route('/api/patterns/<symbol>')
def patterns(symbol):
    """Pre-open pattern data for a symbol."""
    if not os.path.exists(PATTERNS_PATH):
        return jsonify({'error': 'No patterns file'}), 404
    with open(PATTERNS_PATH) as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/scan')
def scan():
    """Pattern scan with combo signals across watchlist + open positions."""
    try:
        from collect_data import collect

        # Get symbols to scan: open positions + watchlist favorites
        symbols = set()

        # Open positions
        conn = get_db()
        try:
            rows = conn.execute("SELECT DISTINCT symbol FROM predictions WHERE status='open'").fetchall()
            for r in rows:
                symbols.add(r['symbol'])
        finally:
            conn.close()

        # Watchlist from DB
        from prediction_db import get_watchlist_symbols
        for s in get_watchlist_symbols():
            symbols.add(s['symbol'])

        # Extra symbol from frontend (e.g. custom symbol tab)
        extra = request.args.get('extra', '').strip().upper()
        if extra:
            symbols.add(extra)

        symbols.discard('')

        results = []
        for sym in sorted(symbols):
            try:
                d = collect(sym)
                signals = detect_combo_signals(d)
                results.append({
                        'symbol': sym,
                        'price': d.get('price_usd'),
                        'price_eur': d.get('price_eur'),
                        'rsi': d.get('rsi'),
                        'rsi_slope': d.get('rsi_slope_3d'),
                        'macd_signal': d.get('macd_signal'),
                        'regime': d.get('regime'),
                        'atr_pct': d.get('atr_pct'),
                        'change_pct': d.get('change_pct'),
                        'signals': signals,
                    })
            except Exception as e:
                print(f"  Scan {sym}: {e}")

        results.sort(key=lambda x: max((s.get('strength', 0) for s in x['signals']), default=0), reverse=True)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/hedge-setup/<symbol>')
def hedge_setup(symbol):
    """Hedge setup: current position + RSI zone + combo signals + recommended KO."""
    try:
        from collect_data import collect

        d = collect(symbol)

        # Check if we have an open position
        conn = get_db()
        try:
            pos = conn.execute(
                "SELECT * FROM predictions WHERE symbol=? AND status='open' LIMIT 1", (symbol,)
            ).fetchone()
            position = row_to_dict(pos) if pos else None
        finally:
            conn.close()

        signals = detect_combo_signals(d)
        short_signals = [s for s in signals if s.get('direction') == 'short']

        # RSI zone analysis
        rsi = d.get('rsi', 50)
        rsi_zone = 'neutral'
        if rsi > 70:
            rsi_zone = 'overbought'
        elif rsi > 60:
            rsi_zone = 'elevated'
        elif rsi > 50:
            rsi_zone = 'mid'
        elif rsi < 30:
            rsi_zone = 'oversold'

        # Recommended short KO
        atr = d.get('atr14_usd', 0)
        price = d.get('price_usd', 0)
        market_cap = d.get('market_cap', 0)

        if market_cap > 50e9:
            multiplier = 2.0  # Large cap
        elif market_cap > 5e9:
            multiplier = 2.5  # Mid cap
        else:
            multiplier = 3.0  # Small cap / commodity

        if d.get('atr_elevated'):
            multiplier += 0.5

        short_ko = price + (atr * multiplier)

        hedge_recommended = (
            position is not None
            and position.get('realized_pnl_eur', 0) and position['realized_pnl_eur'] > 0
            and len(short_signals) > 0
            and rsi > 55
        )

        return jsonify({
            'symbol': symbol,
            'current_price': price,
            'rsi': rsi,
            'rsi_zone': rsi_zone,
            'position': position,
            'is_runner': position is not None and (position.get('realized_pnl_eur') or 0) > 0,
            'combo_signals': signals,
            'short_signals': short_signals,
            'recommended_short_ko': round(short_ko, 2),
            'ko_distance_pct': round((short_ko / price - 1) * 100, 1) if price > 0 else 0,
            'hedge_recommended': hedge_recommended,
            'hedge_confidence': min(len(short_signals) * 20 + (10 if rsi > 65 else 0), 80),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart/<symbol>')
def chart_image(symbol):
    """Serve existing chart PNG."""
    # Try various filename patterns
    for name in [f'{symbol}_chart.png', f'{symbol.replace("=", "_")}_chart.png',
                 f'{symbol.replace(".", "_")}_chart.png']:
        path = os.path.join(CHART_OUTPUT_DIR, name)
        if os.path.exists(path):
            return send_file(path, mimetype='image/png')
    return jsonify({'error': f'No chart for {symbol}'}), 404


@app.route('/api/backtest')
def backtest():
    """Prediction quality analysis from DB."""
    conn = get_db()
    try:
        # All filled predictions
        rows = conn.execute("""
            SELECT id, symbol, direction, confidence, status,
                   price_1d, price_3d, price_5d, price_10d,
                   max_favorable, max_adverse,
                   stop_triggered, target_hit, plus20_hit,
                   realized_pnl_eur, entry_price, target_price, stop_price
            FROM predictions WHERE outcome_filled=1
            ORDER BY id
        """).fetchall()

        traded = [row_to_dict(r) for r in rows if r['status'] in ('open', 'closed')]
        skipped = [row_to_dict(r) for r in rows if r['status'] == 'analysis']

        def stats(items):
            if not items:
                return {}
            confs = [i['confidence'] for i in items]
            mfes = [i['max_favorable'] for i in items if i['max_favorable'] is not None]
            maes = [i['max_adverse'] for i in items if i['max_adverse'] is not None]
            stops = sum(1 for i in items if i.get('stop_triggered'))
            targets = sum(1 for i in items if i.get('target_hit'))
            return {
                'count': len(items),
                'avg_confidence': round(sum(confs) / len(confs), 1) if confs else 0,
                'avg_mfe': round(sum(mfes) / len(mfes), 2) if mfes else 0,
                'avg_mae': round(sum(maes) / len(maes), 2) if maes else 0,
                'stop_rate': round(stops / len(items) * 100, 1) if items else 0,
                'target_rate': round(targets / len(items) * 100, 1) if items else 0,
            }

        # Confidence brackets
        brackets = {}
        for r in [row_to_dict(r) for r in rows]:
            conf = r['confidence']
            bracket = f"{(conf // 10) * 10}-{(conf // 10) * 10 + 9}"
            if bracket not in brackets:
                brackets[bracket] = []
            brackets[bracket].append(r)

        bracket_stats = {}
        for b, items in sorted(brackets.items()):
            bracket_stats[b] = stats(items)

        return jsonify({
            'traded': stats(traded),
            'skipped': stats(skipped),
            'brackets': bracket_stats,
            'total_predictions': len(rows),
        })
    finally:
        conn.close()


@app.route('/api/track-record')
def track_record():
    """Personal trading track record for TrackRecord view."""
    conn = get_db()
    try:
        # Use close_events for ALL sales (including partial closes of open positions)
        events = conn.execute("""
            SELECT ce.id, ce.prediction_id, ce.closed_at, ce.shares, ce.cert_exit_price,
                   ce.pnl_eur, ce.reason,
                   p.symbol, p.direction, p.confidence, p.cert_buyin, p.invested_eur,
                   p.entry_price, p.stop_price, p.target_price, p.status
            FROM close_events ce
            JOIN predictions p ON p.id = ce.prediction_id
            ORDER BY ce.closed_at
        """).fetchall()
        events_list = [row_to_dict(r) for r in events]

        # Calculate cumulative P&L from ALL close events
        cum_pnl = 0
        pnl_timeline = []
        winners = 0
        losers = 0
        total_win = 0
        total_loss = 0
        for t in events_list:
            pnl = t.get('pnl_eur', 0) or 0
            cum_pnl += pnl
            pnl_timeline.append({
                'date': t.get('closed_at', ''),
                'symbol': t['symbol'],
                'pnl': round(pnl, 2),
                'cumulative': round(cum_pnl, 2),
                'shares': t.get('shares', 0),
                'reason': t.get('reason', ''),
                'status': t.get('status', ''),
            })
            if pnl > 0:
                winners += 1
                total_win += pnl
            elif pnl < 0:
                losers += 1
                total_loss += abs(pnl)
        total_events = winners + losers

        # All analyses (traded + skipped) for discipline tracking
        all_analyses = conn.execute(
            "SELECT confidence, status FROM predictions"
        ).fetchall()
        under_gate = sum(1 for a in all_analyses if a['confidence'] < 60 and a['status'] != 'analysis')
        total_analyses = len(all_analyses)

        return jsonify({
            'trades': events_list,
            'pnl_timeline': pnl_timeline,
            'cumulative_pnl': round(cum_pnl, 2),
            'total_trades': total_events,
            'winners': winners,
            'losers': losers,
            'win_rate': round(winners / total_events * 100, 1) if total_events else 0,
            'avg_win': round(total_win / winners, 2) if winners > 0 else 0,
            'avg_loss': round(total_loss / losers, 2) if losers > 0 else 0,
            'discipline': {
                'total_analyses': total_analyses,
                'traded_under_gate': under_gate,
                'gate_compliance': round((1 - under_gate / max(total_analyses, 1)) * 100, 1),
            },
        })
    finally:
        conn.close()


@app.route('/api/events')
def events():
    """SSE endpoint for live updates."""
    def generate():
        last_check = time.time()
        while True:
            time.sleep(30)
            try:
                conn = get_db()
                # Check for new predictions since last check
                new = conn.execute(
                    "SELECT id, symbol, direction, confidence, status FROM predictions "
                    "WHERE created_at > datetime('now', '-1 minute') ORDER BY id DESC LIMIT 5"
                ).fetchall()
                conn.close()

                if new:
                    data = json.dumps([row_to_dict(r) for r in new])
                    yield f"event: prediction\ndata: {data}\n\n"
                else:
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': time.time()})}\n\n"
            except Exception:
                yield f"event: heartbeat\ndata: {json.dumps({'ts': time.time()})}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Combo Signal Engine ──

def detect_combo_signals(d):
    """Detect combination signals from collect_data output."""
    signals = []
    rsi = d.get('rsi', 50)
    macd = d.get('macd_signal', '')
    atr_pct = d.get('atr_pct', 0)
    bb_pos = d.get('bb_position', 0.5)
    bb_width = d.get('bb_width_pctl', 50)
    adx = d.get('adx', 20)
    plus_di = d.get('plus_di', 20)
    minus_di = d.get('minus_di', 20)
    regime = d.get('regime', 'TRANSITIONAL')
    change = d.get('change_pct', 0)
    rsi_slope = d.get('rsi_slope_3d', 0)
    rsi_divergence = d.get('rsi_divergence')
    golden = d.get('golden_cross', False)
    dist_sma50 = d.get('dist_sma50_pct', 0)

    # ── LONG Signals ──
    if rsi < 30:
        strength = 60 + (30 - rsi)  # Lower RSI = stronger signal
        signals.append({
            'name': 'RSI Oversold',
            'direction': 'long',
            'strength': min(strength, 90),
            'detail': f'RSI {rsi:.1f} < 30',
        })

    if rsi < 35 and bb_pos < 0.05:
        signals.append({
            'name': 'RSI + BB Lower Combo',
            'direction': 'long',
            'strength': 75,
            'detail': f'RSI {rsi:.1f} + BB Position {bb_pos:.2f}',
        })

    if rsi < 40 and rsi_slope > 2:
        signals.append({
            'name': 'RSI Recovery',
            'direction': 'long',
            'strength': 65,
            'detail': f'RSI {rsi:.1f} mit Slope +{rsi_slope:.1f}',
        })

    if 'BULLISH' in macd and rsi < 50:
        signals.append({
            'name': 'MACD Bullish + Low RSI',
            'direction': 'long',
            'strength': 60,
            'detail': f'MACD {macd}, RSI {rsi:.1f}',
        })

    if rsi_divergence == 'bullish':
        signals.append({
            'name': 'Bullish RSI Divergence',
            'direction': 'long',
            'strength': 80,
            'detail': 'Price lower low, RSI higher low',
        })

    if bb_width < 15 and bb_pos < 0.3:
        signals.append({
            'name': 'BB Squeeze (Long)',
            'direction': 'long',
            'strength': 55,
            'detail': f'BB Width {bb_width:.0f}% + Position {bb_pos:.2f}',
        })

    if golden and abs(dist_sma50) < 2 and rsi < 45:
        signals.append({
            'name': 'SMA50 Pullback Support',
            'direction': 'long',
            'strength': 65,
            'detail': f'Golden Cross + SMA50 dist {dist_sma50:+.1f}%',
        })

    # ── SHORT Signals ──
    if rsi > 70:
        strength = 60 + (rsi - 70)
        signals.append({
            'name': 'RSI Overbought',
            'direction': 'short',
            'strength': min(strength, 90),
            'detail': f'RSI {rsi:.1f} > 70',
        })

    if rsi > 65 and 'BEARISH' in macd:
        signals.append({
            'name': 'RSI High + MACD Bearish',
            'direction': 'short',
            'strength': 75,
            'detail': f'RSI {rsi:.1f} + MACD {macd}',
        })

    if rsi > 55 and change < -2:
        signals.append({
            'name': 'Reversal Warning',
            'direction': 'short',
            'strength': 60,
            'detail': f'RSI {rsi:.1f} + Today {change:+.1f}%',
        })

    if rsi > 70 and bb_pos > 0.95:
        signals.append({
            'name': 'RSI + BB Upper Combo',
            'direction': 'short',
            'strength': 80,
            'detail': f'RSI {rsi:.1f} + BB Position {bb_pos:.2f}',
        })

    if rsi_divergence == 'bearish':
        signals.append({
            'name': 'Bearish RSI Divergence',
            'direction': 'short',
            'strength': 80,
            'detail': 'Price higher high, RSI lower high',
        })

    if bb_width < 15 and bb_pos > 0.7:
        signals.append({
            'name': 'BB Squeeze (Short)',
            'direction': 'short',
            'strength': 55,
            'detail': f'BB Width {bb_width:.0f}% + Position {bb_pos:.2f}',
        })

    if minus_di > plus_di * 1.5 and adx > 25:
        signals.append({
            'name': 'Strong Bear Trend (-DI >> +DI)',
            'direction': 'short',
            'strength': 70,
            'detail': f'-DI {minus_di:.1f} >> +DI {plus_di:.1f}, ADX {adx:.1f}',
        })

    return signals


# ── Main ──
if __name__ == '__main__':
    print(f"Silver Hawk Dashboard API")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  DB: {DB_PATH}")
    print(f"  Charts: {CHART_OUTPUT_DIR}")
    print(f"  Analyses: {ANALYSES_DIR}")
    print(f"  Server: http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=True)
