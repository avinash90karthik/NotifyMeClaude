"""Shared technical indicator calculations for Silver Hawk Trading.

Originally extracted from screener and watchlist scripts to eliminate
~400 lines of duplicated code. Includes wavelet denoising integration.
Today consumed by collect_data, indicator_context, earnings_pattern,
preopen_check and backtest under scripts/."""

import math

import numpy as np

from lib.wavelet_utils import denoise_ohlcv


def sigmoid_adjust(
    green_rate: float,
    sample_n: int,
    max_adjust: float = 5.0,
    solid_n: int = 30,
    weak_n: int = 15,
) -> float:
    """Continuous Confidence-Adjust from a forward-window green-rate.

    Replaces the bucketed mappings (>65% -> +3% etc.) used previously in
    indicator_context.py and earnings_pattern.py. The sigmoid removes the
    arbitrary cliffs at bucket edges and keeps the same asymptotic bounds.

    Args:
        green_rate: Forward green-rate as a fraction in [0, 1].
        sample_n: Number of observations in the band.
        max_adjust: Asymptotic adjust magnitude. Default 5.0 (percent).
        solid_n: Sample threshold for full weight (1.0). Default 30 for
            indicator-context bands; pass 8 for earnings (max ~10 quarters).
        weak_n: Sample threshold for half weight (0.5). Below this -> 0.0.
            Default 15 for indicator-context; pass 4 for earnings.

    Returns:
        Adjust in [-max_adjust, +max_adjust]. Sample weight:
          n >= solid_n -> 1.0
          weak_n <= n < solid_n -> 0.5
          n < weak_n -> 0.0
    """
    if sample_n < weak_n:
        return 0.0
    weight = 1.0 if sample_n >= solid_n else 0.5
    centered = (green_rate - 0.5) * 4.0
    return max_adjust * math.tanh(centered) * weight


def detect_regime(adx, atr_pct, bb_width_percentile, plus_di, minus_di):
    """Classify market regime: TRENDING, CHOPPY, RANGE, or TRANSITIONAL.

    Returns (regime, weight_adjustments) tuple where weight_adjustments is a dict
    with multipliers for 'trend' (SMA, MACD) and 'oscillator' (RSI, BB) signals."""
    if adx is None:
        return 'TRANSITIONAL', {'trend': 1.0, 'oscillator': 1.0, 'overall': 1.0}

    di_spread = abs(plus_di - minus_di) if plus_di is not None and minus_di is not None else 0

    if adx >= 25 and di_spread > 10:
        return 'TRENDING', {'trend': 1.3, 'oscillator': 0.7, 'overall': 1.0}

    if adx < 20:
        bb_pctl = bb_width_percentile if bb_width_percentile is not None else 50
        if bb_pctl < 30:
            return 'RANGE', {'trend': 0.7, 'oscillator': 1.3, 'overall': 1.0}
        if bb_pctl > 60:
            return 'CHOPPY', {'trend': 1.0, 'oscillator': 1.0, 'overall': 0.7}

    return 'TRANSITIONAL', {'trend': 1.0, 'oscillator': 1.0, 'overall': 1.0}


def detect_rsi_divergence(close_vals, rsi_vals, lookback=20):
    """Detect bullish or bearish RSI divergence over last N bars."""
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


def calc_technicals(batch_data, symbols, single=False):
    """Calculate all v5 technicals from batch OHLCV data.

    Applies wavelet denoising to Close/High/Low before indicator calculation.
    Price and change_pct always come from raw (undenoised) data."""
    results = {}
    for sym in symbols:
        try:
            df = batch_data if single else batch_data[sym]

            # Apply wavelet denoising
            df_d = denoise_ohlcv(df)

            close = df_d['Close'].dropna()       # denoised
            high = df_d['High'].dropna()          # denoised
            low = df_d['Low'].dropna()            # denoised
            volume = df_d['Volume'].dropna()

            # Raw close for price display
            close_raw = df_d['Close_raw'].dropna() if 'Close_raw' in df_d.columns else close

            if len(close) < 30:
                continue

            # Price ALWAYS from raw data
            price = float(close_raw.iloc[-1])
            if price <= 0:
                continue
            prev = float(close_raw.iloc[-2]) if len(close_raw) >= 2 else price
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
                except (ValueError, ZeroDivisionError):
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

            # Regime detection
            regime, regime_weights = detect_regime(
                adx_val, atr_pct, bb.get('bb_width_percentile'), plus_di, minus_di
            )

            # 5-day change (from raw prices)
            change_5d = None
            if len(close_raw) >= 6:
                c5 = float(close_raw.iloc[-6])
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
                # Regime
                'regime': regime, 'regime_weights': regime_weights,
                # Other
                'change_5d': change_5d,
                # Enrichment (Phase 2)
                'analyst_rating': None, 'short_pct': None,
                'earnings_date': None, 'market_cap': None, 'sector': None,
            }
        except (KeyError, ValueError, ZeroDivisionError, IndexError):
            continue
    return results
