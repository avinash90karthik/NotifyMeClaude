#!/usr/bin/env python3
"""Silver Hawk — Automated data collection for the 4-step analysis.
Replaces ~300 lines of inline Python that was embedded in prompts/01_data_collection.md.
Outputs a structured JSON block that the LLM prompts consume directly.

Usage:
    python collect_data.py SYMBOL              # Full collection
    python collect_data.py SYMBOL --json-only  # JSON only (for piping)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import yfinance as yf

from indicators import calc_adx, calc_bollinger, detect_regime

try:
    from wavelet_utils import wavelet_denoise
    HAS_WAVELET = True
except ImportError:
    HAS_WAVELET = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Futures → ETF proxy for RSI/MACD (avoids rollover distortion)
FUTURES_ETF_PROXY = {
    'SI=F': 'SLV', 'GC=F': 'GLD', 'CL=F': 'USO', 'NG=F': 'UNG',
}

EXCHANGE_MAP = {
    'US': (14.5, 21.0), 'EU': (7.0, 15.5), 'FUT': (23.0, 22.0),
}


def detect_exchange(symbol):
    if symbol.endswith(('.DE', '.PA', '.AS', '.L')):
        return 'EU'
    if '=F' in symbol:
        return 'FUT'
    return 'US'


def is_market_open(exchange):
    now = datetime.now(timezone.utc)
    h = now.hour + now.minute / 60
    wd = now.weekday()
    if wd >= 5:
        return False
    if exchange == 'FUT':
        return not (22.0 <= h < 23.0)
    o, c = EXCHANGE_MAP.get(exchange, (14.5, 21.0))
    return o <= h < c


def calc_rsi(close, periods=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1 / periods, min_periods=periods).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1 / periods, min_periods=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calc_macd(close):
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def detect_divergence_detailed(close_vals, rsi_vals, lookback=30):
    """Detect bullish/bearish RSI divergence with detail strings.

    Returns (type, details_list) — richer than indicators.detect_rsi_divergence."""
    if len(close_vals) < lookback or len(rsi_vals) < lookback:
        return None, []
    c = close_vals[-lookback:]
    r = rsi_vals[-lookback:]

    lows, highs = [], []
    for i in range(2, len(c) - 2):
        if np.isnan(r[i]):
            continue
        if c[i] < c[i - 1] and c[i] < c[i - 2] and c[i] < c[i + 1] and c[i] < c[i + 2]:
            lows.append((i, c[i], r[i]))
        if c[i] > c[i - 1] and c[i] > c[i - 2] and c[i] > c[i + 1] and c[i] > c[i + 2]:
            highs.append((i, c[i], r[i]))

    details = []
    div_type = None

    if len(lows) >= 2:
        p, cu = lows[-2], lows[-1]
        if cu[1] < p[1] and cu[2] > p[2]:
            div_type = 'bullish'
            details.append(f'Low1 ${p[1]:.2f} RSI={p[2]:.1f} -> Low2 ${cu[1]:.2f} RSI={cu[2]:.1f}')

    if len(highs) >= 2:
        p, cu = highs[-2], highs[-1]
        if cu[1] > p[1] and cu[2] < p[2]:
            div_type = div_type or 'bearish'
            details.append(f'High1 ${p[1]:.2f} RSI={p[2]:.1f} -> High2 ${cu[1]:.2f} RSI={cu[2]:.1f}')

    return div_type, details


def parse_support_resistance(hist, price):
    """Simple S/R from recent swing highs/lows."""
    highs, lows = [], []
    h = hist['High'].values
    lo = hist['Low'].values
    for i in range(5, len(h) - 5):
        if h[i] == max(h[i - 5:i + 6]):
            highs.append(float(h[i]))
        if lo[i] == min(lo[i - 5:i + 6]):
            lows.append(float(lo[i]))

    supports = sorted(set(round(l, 2) for l in lows if l < price), reverse=True)[:3]
    resistances = sorted(set(round(r, 2) for r in highs if r > price))[:3]
    return supports, resistances


def collect(symbol):
    """Collect all data for a symbol. Returns structured dict."""
    ticker = yf.Ticker(symbol)
    info = ticker.info
    hist = ticker.history(period='3mo')

    if hist.empty:
        return {'error': f'No data for {symbol}'}

    price = info.get('currentPrice') or info.get('regularMarketPrice')
    if not price:
        price = float(hist['Close'].iloc[-1])
    if price <= 0:
        return {'error': f'Invalid price for {symbol}'}

    # EUR/USD
    try:
        eurusd = yf.Ticker('EURUSD=X').info.get('regularMarketPrice', 1.05)
    except Exception:
        eurusd = 1.05

    # Technicals source: ETF proxy for futures
    proxy = FUTURES_ETF_PROXY.get(symbol)
    if proxy:
        proxy_hist = yf.Ticker(proxy).history(period='3mo')
        close_ta = wavelet_denoise(proxy_hist['Close']) if HAS_WAVELET else proxy_hist['Close']
        high_ta = proxy_hist['High']
        low_ta = proxy_hist['Low']
        ta_source = f'{proxy} (ETF proxy)'
    else:
        close_ta = wavelet_denoise(hist['Close']) if HAS_WAVELET else hist['Close']
        high_ta = hist['High']
        low_ta = hist['Low']
        ta_source = symbol

    # RSI
    rsi_series = calc_rsi(close_ta)
    rsi = round(float(rsi_series.iloc[-1]), 1)
    rsi_prev = round(float(rsi_series.iloc[-2]), 1)
    rsi_delta_1d = round(rsi - rsi_prev, 1)
    rsi_delta_5d = round(rsi - float(rsi_series.iloc[-6]), 1) if len(rsi_series) > 6 else 0
    rsi_slope = rsi_series.diff().rolling(3).mean()
    rsi_slope_val = round(float(rsi_slope.iloc[-1]), 2)

    # RSI Divergence (detailed version for analysis prompts)
    div_type, div_details = detect_divergence_detailed(close_ta.values, rsi_series.values)

    # MACD
    macd_line, signal_line, histogram = calc_macd(close_ta)
    macd_hist = round(float(histogram.iloc[-1]), 4)
    macd_hist_prev = round(float(histogram.iloc[-2]), 4)
    macd_signal = 'BULLISH_CROSS' if macd_hist_prev < 0 and macd_hist > 0 else \
                  'BEARISH_CROSS' if macd_hist_prev > 0 and macd_hist < 0 else \
                  'BULLISH' if macd_hist > 0 else 'BEARISH'

    # ATR
    atr14 = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]
    atr5 = (hist['High'] - hist['Low']).rolling(5).mean().iloc[-1]
    atr_pct = round(float(atr14) / price * 100, 2)
    atr_ratio = round(float(atr5 / atr14), 2) if atr14 > 0 else 1.0

    # SMAs
    sma50 = info.get('fiftyDayAverage', 0)
    sma200 = info.get('twoHundredDayAverage', 0)
    dist_sma50 = round((price / sma50 - 1) * 100, 1) if sma50 and sma50 > 0 else None
    dist_sma200 = round((price / sma200 - 1) * 100, 1) if sma200 and sma200 > 0 else None

    # ADX + Regime (using shared indicators.py)
    adx_val, plus_di, minus_di = None, None, None
    regime = 'TRANSITIONAL'
    bb_pctl = 50
    bb_pos = None
    try:
        if len(high_ta) >= 30 and len(low_ta) >= 30 and len(close_ta) >= 30:
            adx_val, plus_di, minus_di = calc_adx(high_ta, low_ta, close_ta)
            adx_val = round(adx_val, 1)
            plus_di = round(plus_di, 1)
            minus_di = round(minus_di, 1)

        bb = calc_bollinger(close_ta)
        bb_pctl = bb.get('bb_width_percentile', 50)
        bb_pos = bb.get('bb_position')

        regime, _ = detect_regime(adx_val, atr_pct, bb_pctl, plus_di, minus_di)
    except Exception:
        pass

    # Support / Resistance
    supports, resistances = parse_support_resistance(hist, price)

    # Exchange / Market status
    exchange = detect_exchange(symbol)
    market_open = is_market_open(exchange)

    # Earnings
    earnings_date = None
    try:
        cal = ticker.calendar
        if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
            dates = cal['Earnings Date']
            if dates:
                ed = dates[0].date() if hasattr(dates[0], 'date') else dates[0]
                if ed >= datetime.now(timezone.utc).date():
                    earnings_date = str(ed)
    except Exception:
        pass

    # Volume
    avg_vol = int(hist['Volume'].tail(20).mean()) if len(hist['Volume']) >= 20 else 0
    vol_today = int(hist['Volume'].iloc[-1]) if len(hist['Volume']) > 0 else 0

    now = datetime.now(timezone.utc)

    return {
        'symbol': symbol,
        'timestamp': now.isoformat(),
        'ta_source': ta_source,
        'wavelet': HAS_WAVELET,
        'exchange': exchange,
        'market_open': market_open,

        # Price
        'price_usd': round(price, 2),
        'price_eur': round(price / eurusd, 2),
        'eurusd': round(eurusd, 4),
        'day_high': info.get('dayHigh', 0),
        'day_low': info.get('dayLow', 0),
        'prev_close': info.get('previousClose', 0),
        'change_pct': round((price - info.get('previousClose', price)) / info.get('previousClose', price) * 100, 2) if info.get('previousClose') else 0,
        'week52_high': info.get('fiftyTwoWeekHigh', 0),
        'week52_low': info.get('fiftyTwoWeekLow', 0),

        # RSI (all derivatives)
        'rsi': rsi,
        'rsi_prev': rsi_prev,
        'rsi_delta_1d': rsi_delta_1d,
        'rsi_delta_5d': rsi_delta_5d,
        'rsi_slope_3d': rsi_slope_val,
        'rsi_status': 'OVERBOUGHT' if rsi > 70 else 'OVERSOLD' if rsi < 30 else 'NEUTRAL',
        'rsi_divergence': div_type,
        'rsi_divergence_details': div_details,

        # MACD
        'macd_hist': macd_hist,
        'macd_hist_prev': macd_hist_prev,
        'macd_signal': macd_signal,

        # Volatility
        'atr14_usd': round(float(atr14), 2),
        'atr_pct': atr_pct,
        'atr5_atr14_ratio': atr_ratio,
        'atr_elevated': atr_ratio > 1.5,
        'beta': info.get('beta', None),
        'ann_volatility': round(float(hist['Close'].pct_change().std() * (252 ** 0.5) * 100), 0),

        # Trend
        'sma50': round(sma50, 2) if sma50 else None,
        'sma200': round(sma200, 2) if sma200 else None,
        'dist_sma50_pct': dist_sma50,
        'dist_sma200_pct': dist_sma200,
        'golden_cross': sma50 > sma200 if sma50 and sma200 else None,

        # ADX / Regime
        'adx': adx_val,
        'plus_di': plus_di,
        'minus_di': minus_di,
        'bb_width_pctl': bb_pctl,
        'bb_position': bb_pos,
        'regime': regime,

        # Fundamentals
        'market_cap': info.get('marketCap', 0),
        'short_pct_float': round(info.get('shortPercentOfFloat', 0) * 100, 1) if info.get('shortPercentOfFloat') else 0,
        'short_ratio_days': info.get('shortRatio', 0),
        'analyst_target_mean': info.get('targetMeanPrice', 0),
        'analyst_target_high': info.get('targetHighPrice', 0),
        'analyst_target_low': info.get('targetLowPrice', 0),
        'recommendation': info.get('recommendationKey', 'N/A'),

        # Volume
        'avg_volume_20d': avg_vol,
        'volume_today': vol_today,

        # Levels
        'supports': supports,
        'resistances': resistances,

        # Events
        'earnings_date': earnings_date,
    }


def print_human_readable(d):
    """Print formatted output for human consumption."""
    if 'error' in d:
        print(f'ERROR: {d["error"]}')
        return

    sym = d['symbol']
    print(f'{"=" * 60}')
    print(f'{sym} -- COLLECTED DATA')
    print(f'{"=" * 60}')
    print(f'Time: {d["timestamp"]}  |  Source: {d["ta_source"]}  |  Wavelet: {d["wavelet"]}')
    mkt = 'OPEN' if d['market_open'] else 'CLOSED (wider spreads!)'
    print(f'Market ({d["exchange"]}): {mkt}')
    print()

    print(f'PRICE:  ${d["price_usd"]}  (EUR {d["price_eur"]})  |  Change: {d["change_pct"]:+.2f}%')
    print(f'Range:  ${d["day_low"]} - ${d["day_high"]}  |  52W: ${d["week52_low"]} - ${d["week52_high"]}')
    print()

    rsi_arrow = '^' if d['rsi_delta_1d'] > 0 else 'v'
    print(f'RSI:    {d["rsi"]} ({d["rsi_status"]})  d1d={d["rsi_delta_1d"]:+.1f}{rsi_arrow}  d5d={d["rsi_delta_5d"]:+.1f}  Slope={d["rsi_slope_3d"]:+.2f}')
    if d['rsi_divergence']:
        print(f'        DIVERGENCE: {d["rsi_divergence"].upper()}  {d["rsi_divergence_details"]}')

    print(f'MACD:   {d["macd_signal"]}  Hist={d["macd_hist"]:+.4f} (prev={d["macd_hist_prev"]:+.4f})')
    print(f'ATR:    ${d["atr14_usd"]} ({d["atr_pct"]}%)  ATR5/14={d["atr5_atr14_ratio"]}x {"ELEVATED!" if d["atr_elevated"] else ""}')
    print(f'ADX:    {d["adx"]}  +DI={d["plus_di"]}  -DI={d["minus_di"]}  -> REGIME: {d["regime"]}')
    sma50_str = f'{d["sma50"]} ({d["dist_sma50_pct"]:+.1f}%)' if d['sma50'] and d['dist_sma50_pct'] is not None else 'N/A'
    sma200_str = f'{d["sma200"]} ({d["dist_sma200_pct"]:+.1f}%)' if d['sma200'] and d['dist_sma200_pct'] is not None else 'N/A'
    print(f'SMA50:  {sma50_str}  SMA200: {sma200_str}  Golden: {d["golden_cross"]}')
    print()

    print(f'SHORT:  {d["short_pct_float"]}% float  |  {d["short_ratio_days"]:.1f} days to cover')
    print(f'ANALYST: {d["recommendation"].upper()}  Target: ${d["analyst_target_low"]}-${d["analyst_target_mean"]}-${d["analyst_target_high"]}')
    print(f'S/R:    S={d["supports"]}  R={d["resistances"]}')
    if d['earnings_date']:
        print(f'EARNINGS: {d["earnings_date"]}')


def main():
    parser = argparse.ArgumentParser(description='Silver Hawk Data Collection')
    parser.add_argument('symbol', help='Ticker symbol')
    parser.add_argument('--json-only', action='store_true', help='Output JSON only')
    args = parser.parse_args()

    data = collect(args.symbol.upper())

    if args.json_only:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_human_readable(data)
        print(f'\n{"=" * 60}')
        print('JSON OUTPUT:')
        print(json.dumps(data, indent=2, default=str))


if __name__ == '__main__':
    main()
