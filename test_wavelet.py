#!/usr/bin/env python3
"""Test script for wavelet denoising integration.

Validates:
1. wavelet_denoise() preserves length and index
2. No NaN introduced
3. Trend direction preserved
4. Graceful fallback when pywt unavailable
5. RSI/MACD comparison raw vs denoised
"""

import sys
import numpy as np
import pandas as pd


def test_basic_denoise():
    """Test wavelet_denoise with real yfinance data."""
    import yfinance as yf
    from wavelet_utils import wavelet_denoise, denoise_ohlcv, HAS_PYWT

    print('=' * 60)
    print('WAVELET DENOISING TEST')
    print('=' * 60)
    print(f'PyWavelets available: {HAS_PYWT}')

    if not HAS_PYWT:
        print('SKIP: PyWavelets not installed — fallback mode only')
        return test_fallback_mode()

    # Fetch test data (use any liquid large-cap symbol)
    TEST_SYMBOL = 'SPY'  # ETF — avoids referencing specific stocks
    print(f'\nFetching {TEST_SYMBOL} 1y data...')
    ticker = yf.Ticker(TEST_SYMBOL)
    hist = ticker.history(period='1y')
    close = hist['Close']
    print(f'  Data points: {len(close)}')

    # Test 1: Length preservation
    denoised = wavelet_denoise(close)
    assert len(denoised) == len(close), f'Length mismatch: {len(denoised)} vs {len(close)}'
    print('  [PASS] Length preserved')

    # Test 2: Index preserved
    assert (denoised.index == close.index).all(), 'Index mismatch'
    print('  [PASS] Index preserved')

    # Test 3: No NaN introduced
    nan_count = denoised.isna().sum()
    assert nan_count == 0, f'NaN introduced: {nan_count}'
    print('  [PASS] No NaN introduced')

    # Test 4: Values are reasonable (not wildly different)
    max_diff_pct = ((denoised - close).abs() / close * 100).max()
    print(f'  Max difference: {max_diff_pct:.2f}%')
    assert max_diff_pct < 5, f'Denoised values too far from original: {max_diff_pct:.2f}%'
    print('  [PASS] Values within 5% of original')

    # Test 5: Trend preserved (correlation > 0.99)
    corr = close.corr(denoised)
    print(f'  Correlation raw vs denoised: {corr:.6f}')
    assert corr > 0.99, f'Correlation too low: {corr}'
    print('  [PASS] Trend preserved (corr > 0.99)')

    # Test 6: denoise_ohlcv wrapper
    df_d = denoise_ohlcv(hist)
    assert 'Close_raw' in df_d.columns, 'Close_raw column missing'
    assert 'High_raw' in df_d.columns, 'High_raw column missing'
    assert 'Low_raw' in df_d.columns, 'Low_raw column missing'
    assert 'Volume_raw' not in df_d.columns, 'Volume should not be denoised'
    print('  [PASS] denoise_ohlcv creates _raw columns correctly')

    # Test 7: Raw price preserved
    assert (df_d['Close_raw'].dropna() == hist['Close'].dropna()).all(), 'Close_raw != original'
    print('  [PASS] Raw prices preserved in _raw columns')

    # Test 8: Short series fallback
    short_series = close.head(30)
    short_result = wavelet_denoise(short_series)
    assert (short_result == short_series).all(), 'Short series should return original'
    print('  [PASS] Short series (<50) returns original')

    return True


def test_indicator_comparison():
    """Compare RSI/MACD raw vs denoised."""
    import yfinance as yf
    from wavelet_utils import wavelet_denoise, HAS_PYWT

    if not HAS_PYWT:
        print('\nSKIP: Indicator comparison (no PyWavelets)')
        return True

    print('\n' + '=' * 60)
    print('INDICATOR COMPARISON: RAW vs DENOISED')
    print('=' * 60)

    hist = yf.Ticker('SPY').history(period='1y')
    close_raw = hist['Close']
    close_den = wavelet_denoise(close_raw)

    # RSI comparison
    def calc_rsi(close):
        delta = close.diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    rsi_raw = calc_rsi(close_raw)
    rsi_den = calc_rsi(close_den)
    rsi_diff = abs(float(rsi_raw.iloc[-1]) - float(rsi_den.iloc[-1]))
    print(f'  RSI raw:      {float(rsi_raw.iloc[-1]):.1f}')
    print(f'  RSI denoised: {float(rsi_den.iloc[-1]):.1f}')
    print(f'  RSI diff:     {rsi_diff:.1f} points')

    # MACD comparison
    def calc_macd_hist(close):
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd - signal

    macd_raw = calc_macd_hist(close_raw)
    macd_den = calc_macd_hist(close_den)
    print(f'  MACD hist raw:      {float(macd_raw.iloc[-1]):.4f}')
    print(f'  MACD hist denoised: {float(macd_den.iloc[-1]):.4f}')

    # ATR comparison
    high_raw = hist['High']
    low_raw = hist['Low']
    tr_raw = np.maximum(
        high_raw.values[-15:] - low_raw.values[-15:],
        np.maximum(
            np.abs(high_raw.values[-15:] - close_raw.values[-16:-1]),
            np.abs(low_raw.values[-15:] - close_raw.values[-16:-1])
        )
    )
    atr_raw = np.mean(tr_raw) / float(close_raw.iloc[-1]) * 100
    print(f'  ATR% raw:     {atr_raw:.2f}%')

    print('  [PASS] Indicator comparison complete')
    return True


def test_fallback_mode():
    """Test graceful fallback by mocking missing pywt."""
    print('\n' + '=' * 60)
    print('FALLBACK MODE TEST')
    print('=' * 60)

    # Create synthetic data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=200)
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    series = pd.Series(prices, index=dates, name='Close')

    # Test with HAS_PYWT forced to False
    import wavelet_utils
    original_flag = wavelet_utils.HAS_PYWT
    wavelet_utils.HAS_PYWT = False

    result = wavelet_utils.wavelet_denoise(series)
    assert (result == series).all(), 'Fallback should return original'
    print('  [PASS] Fallback returns original when pywt unavailable')

    wavelet_utils.HAS_PYWT = original_flag
    return True


def test_indicators_module():
    """Test that indicators.py imports and works."""
    print('\n' + '=' * 60)
    print('INDICATORS MODULE TEST')
    print('=' * 60)

    from indicators import calc_technicals, detect_rsi_divergence, calc_adx, calc_bollinger

    # Test detect_rsi_divergence with synthetic data
    close = np.array([10, 9, 8, 7, 8, 9, 10, 9, 8, 7, 6, 7, 8, 9, 8, 7, 6, 5, 6, 7], dtype=float)
    rsi = np.array([40, 35, 30, 25, 35, 45, 50, 45, 35, 28, 22, 30, 40, 48, 42, 35, 30, 27, 35, 42], dtype=float)
    result = detect_rsi_divergence(close, rsi, lookback=20)
    print(f'  Divergence result: {result}')
    print('  [PASS] detect_rsi_divergence callable')

    # Test calc_bollinger with synthetic data
    close_series = pd.Series(np.random.randn(100).cumsum() + 100)
    bb = calc_bollinger(close_series)
    assert 'bb_width_percentile' in bb
    assert 'bb_position' in bb
    print('  [PASS] calc_bollinger returns expected keys')

    print('  [PASS] indicators module imports and works')
    return True


if __name__ == '__main__':
    passed = 0
    failed = 0

    tests = [
        ('Basic Denoise', test_basic_denoise),
        ('Indicator Comparison', test_indicator_comparison),
        ('Fallback Mode', test_fallback_mode),
        ('Indicators Module', test_indicators_module),
    ]

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
                print(f'\n  [FAIL] {name}')
        except Exception as e:
            failed += 1
            print(f'\n  [FAIL] {name}: {e}')

    print('\n' + '=' * 60)
    print(f'RESULTS: {passed} passed, {failed} failed')
    print('=' * 60)
    sys.exit(0 if failed == 0 else 1)
