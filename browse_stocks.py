#!/usr/bin/env python3
"""Silver Hawk Trading - Stock Watchlist Browser.
Read-only view of the watchlist from memory/watchlist.json."""

import json
import os
import sys


WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.json')


def fetch_stocks():
    """Load stocks from local watchlist file."""
    if not os.path.exists(WATCHLIST_FILE):
        print(f'Watchlist not found: {WATCHLIST_FILE}')
        return []
    with open(WATCHLIST_FILE) as f:
        stocks = json.load(f)
    return sorted(stocks, key=lambda s: (s.get('sector', ''), s['symbol']))


def format_table(stocks):
    """Format stocks as a readable table grouped by sector."""
    if not stocks:
        print('No stocks in watchlist.')
        return

    print()
    print('=' * 60)
    print('  SILVER HAWK TRADING - Watchlist')
    print('=' * 60)
    print(f'  {"Symbol":<10} {"Name":<25} {"Sector":<15}')
    print('  ' + '-' * 55)

    current_sector = None
    for s in stocks:
        sector = s.get('sector') or 'Other'
        if sector != current_sector:
            current_sector = sector
            print(f'\n  {sector}')

        name = s.get('name', '')
        print(f'  {s["symbol"]:<10} {name:<25} {sector:<15}')

    print()
    print(f'  {len(stocks)} stocks total')
    print()
    print('  To analyze a stock:')
    print('    /analyse-stock SYMBOL')
    print()


if __name__ == '__main__':
    stocks = fetch_stocks()

    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        print(json.dumps(stocks, indent=2))
    else:
        format_table(stocks)
