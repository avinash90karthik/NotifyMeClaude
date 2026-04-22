"""Test currency handling in collect_data.py.

The bug: ENR.DE prices are in EUR but were labeled as USD,
then divided by EUR/USD again → all EUR values ~15% wrong.
Also: no GBP support, hardcoded 1.05 fallback.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCurrencyDetection:
    """Verify that collect_data.py handles EUR/USD/GBP correctly."""

    def test_eur_symbol_detected(self):
        """Symbols ending in .DE must have native_currency=EUR."""
        from unittest.mock import patch, MagicMock
        from scripts.collect_data import collect

        mock_info = {
            'currency': 'EUR',
            'currentPrice': 165.38,
            'previousClose': 147.74,
            'dayHigh': 166.3,
            'dayLow': 161.24,
            'fiftyTwoWeekHigh': 171.65,
            'fiftyTwoWeekLow': 49.02,
            'marketCap': 141_000_000_000,
            'shortPercentOfFloat': None,
            'shortRatio': None,
            'targetMeanPrice': 166.0,
            'targetHighPrice': 220.0,
            'targetLowPrice': 89.0,
            'recommendationKey': 'buy',
            'beta': 1.8,
        }

        mock_eurusd_info = {'regularMarketPrice': 1.17}

        import pandas as pd
        import numpy as np
        n = 250
        idx = pd.date_range('2025-04-01', periods=n, freq='B')
        mock_hist = pd.DataFrame({
            'Open': np.linspace(100, 165, n),
            'High': np.linspace(102, 167, n),
            'Low': np.linspace(98, 163, n),
            'Close': np.linspace(100, 165, n),
            'Volume': [3_000_000] * n,
        }, index=idx)

        with patch('scripts.collect_data.yf') as mock_yf:
            # Main ticker
            main_ticker = MagicMock()
            main_ticker.info = mock_info
            main_ticker.history.return_value = mock_hist
            main_ticker.calendar = {}

            # EUR/USD ticker
            eurusd_ticker = MagicMock()
            eurusd_ticker.info = mock_eurusd_info

            def ticker_factory(sym):
                if sym == 'EURUSD=X':
                    return eurusd_ticker
                return main_ticker

            mock_yf.Ticker.side_effect = ticker_factory

            result = collect('ENR.DE')

        assert 'error' not in result, f"collect() returned error: {result.get('error')}"
        assert result['native_currency'] == 'EUR'
        assert result['price_eur'] == 165.38, \
            f"EUR price should be native: {result['price_eur']} != 165.38"
        assert result['price_native'] == 165.38
        # price_usd should be EUR * EURUSD
        expected_usd = round(165.38 * 1.17, 2)
        assert result['price_usd'] == expected_usd, \
            f"USD price should be {expected_usd}, got {result['price_usd']}"

    def test_usd_symbol_detected(self):
        """US symbols must have native_currency=USD."""
        from unittest.mock import patch, MagicMock
        from scripts.collect_data import collect

        mock_info = {
            'currency': 'USD',
            'currentPrice': 95.0,
            'previousClose': 92.0,
            'dayHigh': 96.0,
            'dayLow': 93.0,
            'fiftyTwoWeekHigh': 130.0,
            'fiftyTwoWeekLow': 20.0,
            'marketCap': 30_000_000_000,
            'shortPercentOfFloat': 0.2,
            'shortRatio': 3.9,
            'targetMeanPrice': 88.0,
            'targetHighPrice': 139.0,
            'targetLowPrice': 41.0,
            'recommendationKey': 'hold',
            'beta': 2.5,
        }

        mock_eurusd_info = {'regularMarketPrice': 1.17}

        import pandas as pd
        import numpy as np
        n = 250
        idx = pd.date_range('2025-04-01', periods=n, freq='B')
        mock_hist = pd.DataFrame({
            'Open': np.linspace(50, 95, n),
            'High': np.linspace(52, 97, n),
            'Low': np.linspace(48, 93, n),
            'Close': np.linspace(50, 95, n),
            'Volume': [5_000_000] * n,
        }, index=idx)

        with patch('scripts.collect_data.yf') as mock_yf:
            main_ticker = MagicMock()
            main_ticker.info = mock_info
            main_ticker.history.return_value = mock_hist
            main_ticker.calendar = {}

            eurusd_ticker = MagicMock()
            eurusd_ticker.info = mock_eurusd_info

            def ticker_factory(sym):
                if sym == 'EURUSD=X':
                    return eurusd_ticker
                return main_ticker

            mock_yf.Ticker.side_effect = ticker_factory

            result = collect('ASTS')

        assert 'error' not in result, f"collect() returned error: {result.get('error')}"
        assert result['native_currency'] == 'USD'
        assert result['price_usd'] == 95.0
        expected_eur = round(95.0 / 1.17, 2)
        assert result['price_eur'] == expected_eur

    def test_no_hardcoded_eurusd_fallback(self):
        """If EUR/USD fetch fails, collect() must error — not use 1.05 fallback."""
        from unittest.mock import patch, MagicMock
        from scripts.collect_data import collect

        import pandas as pd
        import numpy as np
        n = 250
        idx = pd.date_range('2025-04-01', periods=n, freq='B')
        mock_hist = pd.DataFrame({
            'Open': np.linspace(50, 95, n),
            'High': np.linspace(52, 97, n),
            'Low': np.linspace(48, 93, n),
            'Close': np.linspace(50, 95, n),
            'Volume': [5_000_000] * n,
        }, index=idx)

        with patch('scripts.collect_data.yf') as mock_yf:
            main_ticker = MagicMock()
            main_ticker.info = {'currency': 'USD', 'currentPrice': 95.0, 'previousClose': 92.0}
            main_ticker.history.return_value = mock_hist

            # EUR/USD ticker raises exception
            eurusd_ticker = MagicMock()
            eurusd_ticker.info = {'regularMarketPrice': None}  # unavailable

            def ticker_factory(sym):
                if sym == 'EURUSD=X':
                    return eurusd_ticker
                return main_ticker

            mock_yf.Ticker.side_effect = ticker_factory

            result = collect('AAPL')

        assert 'error' in result, "Must return error when EUR/USD unavailable"
        assert 'hardcoded' in result['error'].lower() or 'unavailable' in result['error'].lower()

    def test_analyst_targets_have_currency_annotation(self):
        """JSON output must include analyst_target_currency field."""
        from unittest.mock import patch, MagicMock
        from scripts.collect_data import collect

        import pandas as pd
        import numpy as np
        n = 250
        idx = pd.date_range('2025-04-01', periods=n, freq='B')
        mock_hist = pd.DataFrame({
            'Open': np.linspace(100, 165, n),
            'High': np.linspace(102, 167, n),
            'Low': np.linspace(98, 163, n),
            'Close': np.linspace(100, 165, n),
            'Volume': [3_000_000] * n,
        }, index=idx)

        with patch('scripts.collect_data.yf') as mock_yf:
            main_ticker = MagicMock()
            main_ticker.info = {
                'currency': 'EUR',
                'currentPrice': 165.0,
                'previousClose': 150.0,
                'targetMeanPrice': 166.0,
                'targetHighPrice': 220.0,
                'targetLowPrice': 89.0,
                'recommendationKey': 'buy',
                'marketCap': 100_000_000_000,
            }
            main_ticker.history.return_value = mock_hist
            main_ticker.calendar = {}

            eurusd_ticker = MagicMock()
            eurusd_ticker.info = {'regularMarketPrice': 1.17}

            def ticker_factory(sym):
                if sym == 'EURUSD=X':
                    return eurusd_ticker
                return main_ticker

            mock_yf.Ticker.side_effect = ticker_factory

            result = collect('ENR.DE')

        assert 'error' not in result
        assert 'analyst_target_currency' in result, \
            "Must include analyst_target_currency in JSON output"
        assert result['analyst_target_currency'] == 'EUR'
