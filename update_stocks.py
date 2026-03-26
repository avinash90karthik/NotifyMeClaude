#!/usr/bin/env python3
"""Silver Hawk Trading - Stock Data Updater (GitHub Actions).
Reads symbols from predictions.db watchlist, fetches yfinance data, writes prices back to DB."""

import os
from datetime import datetime, timezone


def get_active_symbols():
    """Load active symbols from the watchlist table in predictions.db."""
    from prediction_db import get_watchlist_symbols
    return [s['symbol'] for s in get_watchlist_symbols()]


def fetch_stock_data(symbols):
    import yfinance as yf
    import numpy as np
    from wavelet_utils import wavelet_denoise

    results = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info = t.info
            hist = t.history(period='3mo')

            rsi = sma50 = sma200 = None

            if len(hist) >= 14:
                close_d = wavelet_denoise(hist['Close'])
                delta = close_d.diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
                rsi_val = float((100 - (100 / (1 + gain / loss))).iloc[-1])
                if not np.isnan(rsi_val):
                    rsi = round(rsi_val, 1)

            if len(hist) >= 50:
                sma50 = round(float(hist['Close'].rolling(50).mean().iloc[-1]), 2)

            hist_long = t.history(period='1y')
            if len(hist_long) >= 200:
                sma200 = round(float(hist_long['Close'].rolling(200).mean().iloc[-1]), 2)

            rating = info.get('recommendationKey')
            if rating:
                rating = rating.replace('_', ' ').title()

            results[sym] = {
                'price': info.get('regularMarketPrice'),
                'change_pct': round(info.get('regularMarketChangePercent', 0), 2),
                'rsi': rsi,
                'sma50': sma50,
                'sma200': sma200,
                'market_cap': info.get('marketCap'),
                'analyst_rating': rating,
            }
            r = results[sym]
            print(f'  {sym}: ${r["price"]} ({r["change_pct"]:+.1f}%) RSI={rsi} [{rating}]')

        except Exception as e:
            print(f'  {sym}: ERROR - {e}')
            results[sym] = None

    return results


def update_watchlist_db(data):
    """Write updated stock data back to the watchlist table in predictions.db."""
    from prediction_db import get_db

    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    updated = 0
    for sym, d in data.items():
        if not d:
            continue
        # Store latest price data as JSON in a 'data' column (added dynamically)
        try:
            conn.execute('''
                UPDATE watchlist SET
                    price = ?, change_pct = ?, rsi = ?, sma50 = ?, sma200 = ?,
                    market_cap = ?, analyst_rating = ?, last_updated = ?
                WHERE symbol = ? AND active = 1
            ''', (d.get('price'), d.get('change_pct'), d.get('rsi'),
                  d.get('sma50'), d.get('sma200'), d.get('market_cap'),
                  d.get('analyst_rating'), now, sym))
            updated += 1
        except Exception as e:
            print(f'  {sym}: DB update error - {e}')
    conn.commit()
    conn.close()
    return updated


def main():
    now = datetime.now(timezone.utc)
    print(f'[{now.strftime("%H:%M:%S")} UTC] Stock Data Update')

    symbols = get_active_symbols()
    if not symbols:
        print('  No symbols in watchlist.')
        return

    print(f'  Updating {len(symbols)} symbols: {", ".join(symbols)}')
    data = fetch_stock_data(symbols)
    updated = update_watchlist_db(data)
    print(f'  Done! Updated {updated}/{len(symbols)} stocks in predictions.db')


if __name__ == '__main__':
    main()
