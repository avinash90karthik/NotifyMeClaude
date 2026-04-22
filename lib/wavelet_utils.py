"""Wavelet denoising utilities for price data.

Uses Daubechies-4 wavelet with soft thresholding to remove microstructure
noise from OHLCV data while preserving trends and turning points.
Graceful fallback: returns original data if PyWavelets is unavailable."""

import warnings

import numpy as np
import pandas as pd

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    warnings.warn('PyWavelets not installed — wavelet denoising disabled, using raw data.')

MIN_DATAPOINTS = 50


def wavelet_denoise(series, wavelet='db4', level=3, mode='soft'):
    """Denoise a pandas Series using wavelet thresholding with cycle-spinning.

    Args:
        series: pd.Series of price data (Close, High, Low).
        wavelet: Wavelet family (default: Daubechies-4).
        level: Decomposition level (default: 3).
        mode: Thresholding mode — 'soft' or 'hard' (default: soft).

    Returns:
        pd.Series: Denoised series with same length and index as input.
                   Returns original if pywt unavailable or series too short.
    """
    if not HAS_PYWT:
        return series

    if len(series) < MIN_DATAPOINTS:
        return series

    values = series.values.astype(float)
    n = len(values)
    n_shifts = 4  # cycle-spinning shifts for shift-invariance

    denoised_sum = np.zeros(n)

    for shift in range(n_shifts):
        shifted = np.roll(values, shift)

        # Decompose
        coeffs = pywt.wavedec(shifted, wavelet, level=level)

        # Universal threshold (VisuShrink) on detail coefficients
        # Estimate noise sigma from finest detail coefficients (d1)
        d1 = coeffs[-1]
        sigma = np.median(np.abs(d1)) / 0.6745
        threshold = sigma * np.sqrt(2 * np.log(n))

        # Threshold detail coefficients (d1, d2, d3), keep approximation (a3)
        thresholded = [coeffs[0]]  # a3 unchanged
        for detail in coeffs[1:]:
            thresholded.append(pywt.threshold(detail, threshold, mode=mode))

        # Reconstruct
        reconstructed = pywt.waverec(thresholded, wavelet)

        # Trim to original length (waverec may produce extra samples)
        reconstructed = reconstructed[:n]

        # Undo shift
        denoised_sum += np.roll(reconstructed, -shift)

    denoised = denoised_sum / n_shifts

    return pd.Series(denoised, index=series.index, name=series.name)


def denoise_ohlcv(df, columns=None):
    """Denoise OHLCV DataFrame, keeping raw values as *_raw columns.

    Args:
        df: DataFrame with OHLCV columns.
        columns: List of columns to denoise (default: ['Close', 'High', 'Low']).

    Returns:
        DataFrame with denoised columns + original values as {col}_raw.
        Volume is never denoised.
    """
    if columns is None:
        columns = ['Close', 'High', 'Low']

    result = df.copy()

    for col in columns:
        if col not in result.columns:
            continue
        raw = result[col].dropna()
        if len(raw) < MIN_DATAPOINTS:
            result[f'{col}_raw'] = result[col]
            continue
        denoised = wavelet_denoise(raw)
        result[f'{col}_raw'] = result[col]
        result.loc[denoised.index, col] = denoised

    return result
