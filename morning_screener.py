#!/usr/bin/env python3
"""Silver Hawk Trading - Morning Screener v3.
Scans NASDAQ-100 + custom watchlist + futures before market open.
Scores LONG and SHORT independently with RSI delta, divergence, ADX,
directional volume, Bollinger squeeze, and wrong-side penalties.
Two-phase: fast batch yf.download(), then individual enrichment for top picks.
Runs daily at 08:00 CET via GitHub Actions."""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from supabase_client import supabase_request

FUTURES = {'SI=F', 'GC=F'}
MIN_VOLUME = 100_000
MIN_SCORE = 25
TOP_N = 5
ENRICH_N = 10
SECTOR_LIMIT = 0.60


def fetch_nasdaq100_symbols():
    """Fetch NASDAQ-100 constituents + ICB sectors + company names from Wikipedia."""
    try:
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        req = urllib.request.Request(url, headers={'User-Agent': 'SilverHawk/1.0'})
        resp = urllib.request.urlopen(req, timeout=20)
        html = resp.read().decode()
        parts = html.split('id="constituents"')
        if len(parts) < 2:
            print('  Wikipedia: NASDAQ-100 constituents table not found')
            return [], {}, {}
        table_html = parts[1].split('</table>')[0]
        rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
        tickers = []
        sectors = {}
        names = {}
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 3:
                # Columns: [0]=Ticker, [1]=Company, [2]=ICB Industry, [3]=ICB Subsector
                ticker = re.sub(r'<[^>]+>', '', cells[0]).strip().replace('.', '-')
                if ticker and re.match(r'^[A-Z][A-Z0-9-]{0,5}$', ticker):
                    tickers.append(ticker)
                    name_text = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if name_text:
                        names[ticker] = name_text
                    sector_text = re.sub(r'<[^>]+>', '', cells[2]).strip()
                    if sector_text:
                        sectors[ticker] = sector_text
        return tickers, sectors, names
    except Exception as e:
        print(f'  Wikipedia fetch failed: {e}')
        return [], {}, {}


def get_watchlist():
    result = supabase_request('GET', 'stocks?select=symbol,name,sector&is_active=eq.true')
    return result or []


def get_open_positions():
    result = supabase_request('GET', 'portfolio?select=*&status=eq.open')
    return result or []


def get_position_directions(positions, price_data=None):
    """Infer LONG/SHORT direction from KO vs current stock price.
    entry_price is the Turbo certificate price, NOT the stock price,
    so we compare KO against the live stock price instead."""
    dirs = {}
    for p in positions:
        sym = p['symbol']
        ko = p.get('ko_level')
        current_price = price_data.get(sym, {}).get('price') if price_data else None
        if ko and current_price:
            dirs[sym] = 'LONG' if ko < current_price else 'SHORT'
        else:
            dirs[sym] = '?'
    return dirs


def detect_rsi_divergence(close_vals, rsi_vals, lookback=20):
    """Detect bullish or bearish RSI divergence over last N bars."""
    import numpy as np
    if len(close_vals) < lookback or len(rsi_vals) < lookback:
        return None
    c = close_vals[-lookback:]
    r = rsi_vals[-lookback:]
    valid = ~np.isnan(r)
    if valid.sum() < lookback - 5:
        return None

    swing_lows = []
    swing_highs = []
    for i in range(2, len(c) - 2):
        if not valid[i]:
            continue
        if c[i] < c[i-1] and c[i] < c[i-2] and c[i] < c[i+1] and c[i] < c[i+2]:
            swing_lows.append(i)
        if c[i] > c[i-1] and c[i] > c[i-2] and c[i] > c[i+1] and c[i] > c[i+2]:
            swing_highs.append(i)

    # Bullish: price lower low, RSI higher low
    if len(swing_lows) >= 2:
        p, cu = swing_lows[-2], swing_lows[-1]
        if c[cu] < c[p] and r[cu] > r[p]:
            return 'bullish'

    # Bearish: price higher high, RSI lower high
    if len(swing_highs) >= 2:
        p, cu = swing_highs[-2], swing_highs[-1]
        if c[cu] > c[p] and r[cu] < r[p]:
            return 'bearish'

    return None


def calc_adx(high, low, close, period=14):
    """Calculate ADX, +DI, -DI using Wilder smoothing."""
    import numpy as np
    import pandas as pd

    plus_dm = high.diff().copy()
    minus_dm = (-low.diff()).copy()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    both = (plus_dm > 0) & (minus_dm > 0)
    plus_dm[both & (plus_dm < minus_dm)] = 0
    minus_dm[both & (minus_dm < plus_dm)] = 0

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.Series(
        np.maximum(np.maximum(tr1.values, tr2.values), tr3.values),
        index=high.index
    )

    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, min_periods=period).mean()
    smooth_plus = plus_dm.ewm(alpha=alpha, min_periods=period).mean()
    smooth_minus = minus_dm.ewm(alpha=alpha, min_periods=period).mean()

    plus_di = 100 * smooth_plus / atr
    minus_di = 100 * smooth_minus / atr
    di_sum = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / di_sum.replace(0, 1)
    adx = dx.ewm(alpha=alpha, min_periods=period).mean()

    return float(adx.iloc[-1]), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])


def calc_bollinger(close, sma_period=20, num_std=2, lookback=120):
    """Calculate Bollinger Bands, bandwidth percentile, and price position."""
    import numpy as np
    if len(close) < sma_period:
        return {'bb_width_percentile': None, 'bb_position': None}

    sma = close.rolling(sma_period).mean()
    std = close.rolling(sma_period).std()
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    bb_width = (upper - lower) / sma

    recent = bb_width.dropna().iloc[-min(lookback, len(bb_width.dropna())):]
    cur_w = float(bb_width.iloc[-1])
    if len(recent) > 0 and not np.isnan(cur_w):
        bb_pctl = round(float((recent < cur_w).sum() / len(recent) * 100), 1)
    else:
        bb_pctl = None

    band_range = float(upper.iloc[-1] - lower.iloc[-1])
    bb_pos = round((float(close.iloc[-1]) - float(lower.iloc[-1])) / band_range, 2) if band_range > 0 else None

    return {'bb_width_percentile': bb_pctl, 'bb_position': bb_pos}


def batch_download(symbols):
    """Batch download 1 year of OHLCV data for all symbols."""
    import yfinance as yf
    return yf.download(symbols, period='1y', group_by='ticker', threads=True, progress=False)


def calc_technicals(batch_data, symbols, single=False):
    """Calculate all v3 technicals from batch OHLCV data."""
    import numpy as np

    results = {}
    for sym in symbols:
        try:
            df = batch_data if single else batch_data[sym]
            close = df['Close'].dropna()
            high = df['High'].dropna()
            low = df['Low'].dropna()
            volume = df['Volume'].dropna()

            if len(close) < 30:
                continue
            price = float(close.iloc[-1])
            if price <= 0:
                continue
            prev = float(close.iloc[-2]) if len(close) >= 2 else price
            change_pct = round((price - prev) / prev * 100, 2)

            # RSI 14 (Wilder's smoothing)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
            loss_s = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
            rs = gain / loss_s
            rsi_series = 100 - (100 / (1 + rs))
            rsi_val = float(rsi_series.iloc[-1])
            if np.isnan(rsi_val):
                continue
            rsi = round(rsi_val, 1)

            # RSI delta (5-day)
            rsi_delta = None
            rsi_clean = rsi_series.dropna()
            if len(rsi_clean) >= 6:
                r5 = float(rsi_clean.iloc[-6])
                if not np.isnan(r5):
                    rsi_delta = round(rsi - r5, 1)

            # RSI divergence
            rsi_divergence = detect_rsi_divergence(close.values, rsi_series.values)

            # RSI range quality (last 20 days)
            rsi_range = None
            rsi_had_extreme = False
            if len(rsi_clean) >= 20:
                rsi_20 = rsi_clean.iloc[-20:]
                rsi_20_vals = rsi_20[~np.isnan(rsi_20.values)]
                if len(rsi_20_vals) >= 10:
                    rsi_range = round(float(rsi_20_vals.max() - rsi_20_vals.min()), 1)
                    rsi_had_extreme = bool((rsi_20_vals < 35).any() or (rsi_20_vals > 65).any())

            # MACD + histogram direction
            macd_cur = macd_prev = None
            macd_hist_dir = None
            macd_converging = False
            if len(close) >= 35:
                exp12 = close.ewm(span=12, adjust=False).mean()
                exp26 = close.ewm(span=26, adjust=False).mean()
                macd_line = exp12 - exp26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line
                macd_cur = round(float(histogram.iloc[-1]), 4)
                macd_prev = round(float(histogram.iloc[-2]), 4)
                macd_hist_dir = 'increasing' if macd_cur > macd_prev else 'decreasing'
                macd_converging = (
                    abs(float(macd_line.iloc[-1] - signal_line.iloc[-1])) <
                    abs(float(macd_line.iloc[-2] - signal_line.iloc[-2]))
                )

            # ATR%
            atr_pct = None
            if len(high) >= 15 and len(low) >= 15 and len(close) >= 15:
                h = high.values[-15:]
                l = low.values[-15:]
                c = close.values[-15:]
                tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
                atr_pct = round(float(np.mean(tr)) / price * 100, 2)

            # ADX
            adx_val = plus_di = minus_di = None
            if len(high) >= 30 and len(low) >= 30 and len(close) >= 30:
                try:
                    adx_val, plus_di, minus_di = calc_adx(high, low, close)
                    if np.isnan(adx_val):
                        adx_val = None
                    else:
                        adx_val = round(adx_val, 1)
                except Exception:
                    pass

            # SMAs + distance
            sma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
            sma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None
            sma200_dist = round((price - sma200) / sma200 * 100, 2) if sma200 else None
            sma50_dist = round((price - sma50) / sma50 * 100, 2) if sma50 else None

            # Volume (use last complete trading day if current day has partial volume)
            avg_vol = int(volume.tail(20).mean()) if len(volume) >= 20 else 0
            vol_today = int(volume.iloc[-1]) if len(volume) > 0 else 0
            if avg_vol > 0 and vol_today < avg_vol * 0.1 and len(volume) >= 2:
                vol_today = int(volume.iloc[-2])
            vol_ratio = round(vol_today / avg_vol, 2) if avg_vol > 0 else 0

            # Bollinger Bands
            bb = calc_bollinger(close)

            # 5-day change
            change_5d = None
            if len(close) >= 6:
                c5 = float(close.iloc[-6])
                change_5d = round((price - c5) / c5 * 100, 2)

            results[sym] = {
                'price': price, 'change_pct': change_pct,
                # RSI
                'rsi': rsi, 'rsi_delta': rsi_delta, 'rsi_divergence': rsi_divergence,
                'rsi_range': rsi_range, 'rsi_had_extreme': rsi_had_extreme,
                # MACD
                'macd_hist': macd_cur, 'macd_hist_prev': macd_prev,
                'macd_hist_direction': macd_hist_dir, 'macd_converging': macd_converging,
                # ATR + ADX
                'atr_pct': atr_pct,
                'adx': adx_val, 'plus_di': plus_di, 'minus_di': minus_di,
                # SMAs
                'sma50': sma50, 'sma200': sma200,
                'sma200_distance_pct': sma200_dist, 'sma50_distance_pct': sma50_dist,
                # Volume
                'volume': avg_vol, 'vol_today': vol_today, 'vol_ratio': vol_ratio,
                # Bollinger
                'bb_width_percentile': bb.get('bb_width_percentile'),
                'bb_position': bb.get('bb_position'),
                # Other
                'change_5d': change_5d,
                # Enrichment (Phase 2)
                'analyst_rating': None, 'short_pct': None,
                'earnings_date': None, 'market_cap': None, 'sector': None,
            }
        except Exception:
            continue
    return results


def enrich_candidates(symbols, data):
    """Fetch individual yfinance info for top candidates."""
    import yfinance as yf
    today = datetime.now(timezone.utc).date()

    for sym in symbols:
        if sym not in data:
            continue
        try:
            t = yf.Ticker(sym)
            info = t.info
            data[sym]['analyst_rating'] = info.get('recommendationKey')
            data[sym]['short_pct'] = info.get('shortPercentOfFloat', 0)
            data[sym]['market_cap'] = info.get('marketCap', 0)
            data[sym]['sector'] = info.get('sector', '')
            try:
                cal = t.calendar
                if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if dates:
                        ed = dates[0].date() if hasattr(dates[0], 'date') else dates[0]
                        if ed >= today:
                            data[sym]['earnings_date'] = str(ed)
            except Exception:
                pass
        except Exception as e:
            print(f'  Enrich {sym}: {e}')


def passes_hard_gates(sym, d):
    if not d or not d.get('price') or d.get('rsi') is None:
        return False
    if sym in FUTURES:
        return True
    if (d.get('volume') or 0) < MIN_VOLUME:
        return False
    # RSI Range Quality: must oscillate (range >= 15) AND hit an extreme in 20 days
    rsi_range = d.get('rsi_range')
    rsi_had_extreme = d.get('rsi_had_extreme', False)
    if rsi_range is not None and (rsi_range < 15 or not rsi_had_extreme):
        return False
    return True


def score_long(d):
    """Score LONG potential (0-100). v4 Trend/Momentum scoring.
    Rewards: uptrend + pullback + momentum resuming.
    Penalizes: falling knives, no trend, overextended."""
    score = 0
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 < 0:
            # Below SMA200: heavy penalty, kills the setup
            score -= 15
            signals.append('UNTER SMA200')
        elif 0 <= dist200 <= 5:
            score += 15; signals.append('Uptrend nah SMA200')
        elif 5 < dist200 <= 15:
            score += 12; signals.append('Uptrend')
        elif 15 < dist200 <= 30:
            score += 8
        else:
            score += 4  # Very extended above SMA200

    # SMA50 pullback timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 >= 0:
        if -3 <= dist50 <= 1:
            score += 12; signals.append('SMA50 Pullback')
        elif -5 <= dist50 <= 3:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 > 3:
            score += 4  # Above SMA50, trending

    # RSI sweet spot (0-12)
    if 35 <= rsi <= 45:
        score += 12; signals.append(f'RSI {rsi:.0f} Pullback-Zone')
    elif 45 < rsi <= 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 30 <= rsi < 35:
        score += 6; signals.append(f'RSI {rsi:.0f} niedrig')
    elif 55 < rsi <= 65:
        score += 5  # Still ok, momentum
    elif rsi > 70:
        score -= 5  # Overbought = bad entry for LONG
    elif rsi < 30:
        score -= 8  # Falling knife territory

    # RSI delta: momentum resuming (0-8)
    if rd is not None:
        if rd > 5 and 30 <= rsi <= 55:
            score += 8; signals.append(f'RSI dreht +{rd:.0f}')
        elif rd > 3 and rsi <= 55:
            score += 5
        elif rd > 0:
            score += 2
        elif rd < -5:
            score -= 3  # Momentum fading

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bullish' and dist200 is not None and dist200 >= 0:
        score += 5; signals.append('DIV bullish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp < 0 and mc > 0:
            score += 10; signals.append('MACD Cross UP')
        elif mc > 0 and m_dir == 'increasing':
            score += 8; signals.append('MACD steigend')
        elif mc > 0:
            score += 5
        elif mp < 0 and mc < 0 and m_dir == 'increasing':
            score += 3  # Converging from below = potential cross

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            score += 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            score += 14
        elif atr >= 2.5:
            score += 9
        elif atr >= 1.5:
            score += 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2  # No trend = bad for momentum

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg > 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg > 0:
        score += 5
    elif vr >= 1.5 and chg < -1:
        score -= 3  # High vol on red = distribution

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.20:
        score += 4; signals.append(f'SI {si*100:.0f}%')
    elif si >= 0.10:
        score += 2

    rating = d.get('analyst_rating') or ''
    if rating in ('strong_buy', 'strongBuy'):
        score += 3
    elif rating in ('buy',):
        score += 2

    c5d = d.get('change_5d')
    if c5d is not None and -8 <= c5d <= -2 and dist200 is not None and dist200 >= 0:
        score += 5; signals.append('5d Pullback im Uptrend')

    return max(0, min(100, score)), signals


def score_short(d):
    """Score SHORT potential (0-100). v4 Trend/Momentum scoring.
    Rewards: downtrend + bounce to resistance + momentum fading.
    Penalizes: strong uptrends, oversold bounces."""
    score = 0
    signals = []
    rsi = d['rsi']
    price = d['price']
    dist200 = d.get('sma200_distance_pct')
    dist50 = d.get('sma50_distance_pct')
    adx = d.get('adx')
    rd = d.get('rsi_delta')

    # Trend alignment: SMA200 (0-15)
    if dist200 is not None:
        if dist200 > 0:
            # Above SMA200: heavy penalty, kills the setup
            score -= 15
            signals.append('UEBER SMA200')
        elif -5 <= dist200 < 0:
            score += 15; signals.append('Downtrend nah SMA200')
        elif -15 <= dist200 < -5:
            score += 12; signals.append('Downtrend')
        elif -30 <= dist200 < -15:
            score += 8
        else:
            score += 4  # Very extended below SMA200

    # SMA50 rejection timing (0-12)
    if dist50 is not None and dist200 is not None and dist200 < 0:
        if -1 <= dist50 <= 3:
            score += 12; signals.append('SMA50 Abprall')
        elif -3 <= dist50 <= 5:
            score += 8; signals.append('Nahe SMA50')
        elif dist50 < -3:
            score += 4  # Below SMA50, trending down

    # RSI sweet spot (0-12)
    if 55 <= rsi <= 65:
        score += 12; signals.append(f'RSI {rsi:.0f} Bounce-Zone')
    elif 50 <= rsi < 55:
        score += 10; signals.append(f'RSI {rsi:.0f} neutral')
    elif 65 < rsi <= 70:
        score += 6; signals.append(f'RSI {rsi:.0f} hoch')
    elif 40 <= rsi < 50:
        score += 5  # Still ok
    elif rsi < 30:
        score -= 5  # Oversold = bad entry for SHORT
    elif rsi > 75:
        score -= 8  # Extreme = could be strong momentum, risky short

    # RSI delta: momentum fading (0-8)
    if rd is not None:
        if rd < -5 and 45 <= rsi <= 70:
            score += 8; signals.append(f'RSI faellt {rd:.0f}')
        elif rd < -3 and rsi >= 45:
            score += 5
        elif rd < 0:
            score += 2
        elif rd > 5:
            score -= 3  # Momentum picking up = bad for short

    # RSI divergence (0-5)
    div = d.get('rsi_divergence')
    if div == 'bearish' and dist200 is not None and dist200 < 0:
        score += 5; signals.append('DIV bearish')

    # MACD confirmation (0-13)
    mc = d.get('macd_hist')
    mp = d.get('macd_hist_prev')
    m_dir = d.get('macd_hist_direction')
    if mc is not None and mp is not None:
        if mp > 0 and mc < 0:
            score += 10; signals.append('MACD Cross DOWN')
        elif mc < 0 and m_dir == 'decreasing':
            score += 8; signals.append('MACD fallend')
        elif mc < 0:
            score += 5
        elif mp > 0 and mc > 0 and m_dir == 'decreasing':
            score += 3  # Converging from above = potential cross down

    # ATR% volatility (0-18)
    atr = d.get('atr_pct')
    if atr is not None:
        if atr >= 5.0:
            score += 18; signals.append(f'ATR {atr:.1f}%')
        elif atr >= 3.5:
            score += 14
        elif atr >= 2.5:
            score += 9
        elif atr >= 1.5:
            score += 4

    # ADX trend strength (0-10)
    if adx is not None:
        if adx >= 35:
            score += 10; signals.append(f'ADX {adx:.0f} stark')
        elif adx >= 25:
            score += 7; signals.append(f'ADX {adx:.0f}')
        elif adx >= 20:
            score += 3
        else:
            score -= 2  # No trend = bad for momentum

    # Volume confirmation (0-8)
    vr = d.get('vol_ratio') or 0
    chg = d.get('change_pct', 0)
    if vr >= 2.5 and chg < 0:
        score += 8; signals.append(f'Vol {vr:.1f}x')
    elif vr >= 1.5 and chg < 0:
        score += 5
    elif vr >= 1.5 and chg > 1:
        score -= 3  # High vol on green = accumulation

    # Bollinger squeeze (0-5)
    bb_pct = d.get('bb_width_percentile')
    bb_pos = d.get('bb_position')
    if bb_pct is not None and bb_pos is not None:
        if bb_pct < 15 and adx and adx >= 20:
            score += 5; signals.append('BB Squeeze')
        elif bb_pct < 25:
            score += 2

    # Extras (0-7)
    si = d.get('short_pct') or 0
    if si >= 0.25:
        score -= 5  # Too crowded, squeeze risk
    elif si >= 0.15:
        score -= 2
    elif si < 0.05:
        score += 2  # Low SI = room to short

    rating = d.get('analyst_rating') or ''
    if rating in ('sell', 'strong_sell', 'strongSell'):
        score += 3
    elif rating in ('underperform',):
        score += 2

    c5d = d.get('change_5d')
    if c5d is not None and 2 <= c5d <= 8 and dist200 is not None and dist200 < 0:
        score += 5; signals.append('5d Bounce im Downtrend')

    return max(0, min(100, score)), signals


def calc_sector_concentration(positions, sector_map):
    sector_values = {}
    total = 0
    for pos in positions:
        sym = pos['symbol']
        sector = sector_map.get(sym, 'Unbekannt')
        value = (pos.get('entry_price', 0) or 0) * (pos.get('quantity', 0) or 0)
        sector_values[sector] = sector_values.get(sector, 0) + value
        total += value
    if total == 0:
        return {}
    return {s: round(v / total * 100, 1) for s, v in sector_values.items()}


def fmt_candidate(i, score, sym, sector, d, signals, direction, pos_dirs, name=''):
    """Format a single candidate line for Telegram."""
    emoji = '🟢' if direction == 'LONG' else '🔴'
    name_str = f' {name}' if name else ''
    line = f'{emoji} {i}. <b>{sym}</b>{name_str} ({sector}) {score}/100'

    if sym in pos_dirs:
        pd = pos_dirs[sym]
        if (direction == 'LONG' and pd == 'LONG') or (direction == 'SHORT' and pd == 'SHORT'):
            line += f' [{pd}] ✅'
        elif pd in ('LONG', 'SHORT'):
            line += f' [{pd}] ⚠️ GEGEN!'
        else:
            line += ' [BESITZ]'
    line += '\n'

    # Core indicators
    rsi_str = f'RSI {d["rsi"]:.0f}'
    if d.get('rsi_delta') is not None:
        rsi_str += f' (Δ{d["rsi_delta"]:+.0f})'
    line += f'   {rsi_str}'
    if d.get('adx') is not None:
        warn = '⚠️' if d['adx'] < 20 else ''
        line += f' | ADX {d["adx"]:.0f}{warn}'
    if d.get('atr_pct'):
        line += f' | ATR {d["atr_pct"]:.1f}%'
    line += '\n'

    # Signals
    if signals:
        line += f'   {", ".join(signals[:4])}\n'

    # Extras: volume, SI, BB, divergence
    extras = []
    if d.get('vol_ratio') and d['vol_ratio'] >= 1.5:
        arrow = '↑' if d.get('change_pct', 0) > 0 else '↓'
        extras.append(f'Vol {d["vol_ratio"]:.1f}x{arrow}')
    if d.get('short_pct') and d['short_pct'] >= 0.05:
        extras.append(f'SI {d["short_pct"]*100:.0f}%')
    if d.get('bb_width_percentile') is not None and d['bb_width_percentile'] < 20:
        extras.append('BB🔥')
    if d.get('rsi_divergence') == 'bullish':
        extras.append('DIV↑')
    elif d.get('rsi_divergence') == 'bearish':
        extras.append('DIV↓')
    if extras:
        line += f'   {" | ".join(extras)}\n'

    if d.get('earnings_date'):
        line += f'   Earnings: {d["earnings_date"]}\n'

    return line


def build_message(all_data, positions, sector_map, scan_time, total_scanned, pos_dirs, name_map=None):
    """Build the Telegram screener message."""
    name_map = name_map or {}
    passed = {sym: d for sym, d in all_data.items() if passes_hard_gates(sym, d)}

    long_scores = []
    short_scores = []
    for sym, d in passed.items():
        ls, lsig = score_long(d)
        ss, ssig = score_short(d)
        sector = sector_map.get(sym, d.get('sector') or '?')
        long_scores.append((ls, sym, sector, d, lsig))
        short_scores.append((ss, sym, sector, d, ssig))

    long_scores.sort(key=lambda x: x[0], reverse=True)
    short_scores.sort(key=lambda x: x[0], reverse=True)
    top_long = long_scores[:TOP_N]
    top_short = short_scores[:TOP_N]

    sector_conc = calc_sector_concentration(positions, sector_map)

    msg = f'<b>MORNING SCREENER v3</b> | {scan_time}\n'
    msg += f'Gescannt: {total_scanned} | Bestanden: {len(passed)}\n'

    if positions:
        msg += f'\n<b>PORTFOLIO</b>\n'
        for sec, pct in sorted(sector_conc.items(), key=lambda x: x[1], reverse=True):
            warn = ' WARNUNG!' if pct > SECTOR_LIMIT * 100 else ''
            msg += f'  {sec}: {pct:.0f}%{warn}\n'

    msg += f'\n<b>TOP LONG</b>\n'
    if top_long and top_long[0][0] >= MIN_SCORE:
        for i, (sc, sym, sec, d, sig) in enumerate(top_long, 1):
            if sc < MIN_SCORE:
                break
            msg += fmt_candidate(i, sc, sym, sec, d, sig, 'LONG', pos_dirs, name_map.get(sym, ''))
    else:
        msg += '  Keine starken Setups\n'

    msg += f'\n<b>TOP SHORT</b>\n'
    if top_short and top_short[0][0] >= MIN_SCORE:
        for i, (sc, sym, sec, d, sig) in enumerate(top_short, 1):
            if sc < MIN_SCORE:
                break
            msg += fmt_candidate(i, sc, sym, sec, d, sig, 'SHORT', pos_dirs, name_map.get(sym, ''))
    else:
        msg += '  Keine starken Setups\n'

    events = [(d.get('earnings_date'), sym) for sym, d in passed.items() if d.get('earnings_date')]
    events.sort()
    if events:
        msg += f'\n<b>EVENTS</b>\n'
        for date, sym in events[:5]:
            msg += f'  {sym}: Earnings {date}\n'

    msg += f'\n<i>Score Min: {MIN_SCORE} | Analyse via Claude Code</i>'
    return msg


def send_telegram(text):
    """Send message via Telegram. Splits if over 4096 chars."""
    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']
    api = f'https://api.telegram.org/bot{token}/sendMessage'

    chunks = []
    if len(text) <= 4096:
        chunks = [text]
    else:
        current = ''
        for line in text.split('\n'):
            if len(current) + len(line) + 1 > 4000:
                chunks.append(current)
                current = line
            else:
                current = current + '\n' + line if current else line
        if current:
            chunks.append(current)

    result = None
    for chunk in chunks:
        body = urllib.parse.urlencode({
            'chat_id': chat_id, 'parse_mode': 'HTML', 'text': chunk,
        }).encode()
        req = urllib.request.Request(api, data=body)
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
    return result


def main():
    now = datetime.now(timezone.utc)
    scan_time = now.strftime('%d.%m.%Y %H:%M UTC')
    print(f'[{now.strftime("%H:%M:%S")} UTC] Morning Screener v3')

    print('  Fetching NASDAQ-100 list...')
    ndx100, ndx100_sectors, ndx100_names = fetch_nasdaq100_symbols()
    print(f'  NASDAQ-100: {len(ndx100)} symbols')

    watchlist = get_watchlist()
    positions = get_open_positions()
    print(f'  Watchlist: {len(watchlist)} | Positions: {len(positions)} open')

    watchlist_syms = {s['symbol'] for s in watchlist}
    position_syms = {p['symbol'] for p in positions}
    all_symbols = sorted(set(ndx100) | watchlist_syms | position_syms | FUTURES)
    total_scanned = len(all_symbols)
    print(f'  Total universe: {total_scanned} symbols')

    if not all_symbols:
        print('  No symbols to scan.')
        return

    sector_map = dict(ndx100_sectors)
    for s in watchlist:
        sector_map.setdefault(s['symbol'], s.get('sector', 'Unbekannt'))

    name_map = dict(ndx100_names)
    for s in watchlist:
        name_map.setdefault(s['symbol'], s.get('name', s['symbol']))
    sector_map.setdefault('SI=F', 'Commodities')
    sector_map.setdefault('GC=F', 'Commodities')

    print(f'  Phase 1: Batch downloading {total_scanned} symbols...')
    single = len(all_symbols) == 1
    batch_data = batch_download(all_symbols)
    print('  Download complete.')

    print('  Calculating technicals...')
    data = calc_technicals(batch_data, all_symbols, single=single)
    print(f'  Technicals for {len(data)} symbols')

    pos_dirs = get_position_directions(positions, data)
    for sym, d in pos_dirs.items():
        print(f'    {sym}: {d}')

    passed = {sym: d for sym, d in data.items() if passes_hard_gates(sym, d)}
    print(f'  Hard gates: {len(passed)} passed')

    long_pre = sorted([(score_long(d)[0], sym) for sym, d in passed.items()], reverse=True)
    short_pre = sorted([(score_short(d)[0], sym) for sym, d in passed.items()], reverse=True)

    enrich_syms = {sym for _, sym in long_pre[:ENRICH_N]} | {sym for _, sym in short_pre[:ENRICH_N]}
    enrich_syms |= (FUTURES | position_syms) & set(data.keys())

    print(f'  Phase 2: Enriching {len(enrich_syms)} candidates...')
    enrich_candidates(list(enrich_syms), data)

    for sym in enrich_syms:
        if sym in data and data[sym].get('sector'):
            sector_map.setdefault(sym, data[sym]['sector'])

    msg = build_message(data, positions, sector_map, scan_time, total_scanned, pos_dirs, name_map)
    print(f'\n{msg}\n')

    result = send_telegram(msg)
    print(f'  Telegram sent: {result.get("ok", False)}')


if __name__ == '__main__':
    main()
