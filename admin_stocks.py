#!/usr/bin/env python3
"""Silver Hawk Trading - Admin CLI for managing the stock watchlist.
Reads and writes memory/watchlist.json."""

import json
import os
import sys


WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memory', 'watchlist.json')


def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


def save_watchlist(stocks):
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(stocks, f, indent=2)


def list_stocks():
    stocks = sorted(load_watchlist(), key=lambda s: (s.get('sector', ''), s['symbol']))
    if not stocks:
        print('No stocks in watchlist.')
        return

    current_sector = None
    print(f'\n{"Symbol":<10} {"Name":<25} {"Sector":<15}')
    print('-' * 55)

    for s in stocks:
        sector = s.get('sector') or 'Unknown'
        if sector != current_sector:
            current_sector = sector
            print(f'\n  --- {sector} ---')
        print(f"{s['symbol']:<10} {s.get('name', ''):<25} {sector:<15}")

    print(f'\nTotal: {len(stocks)} stocks')


def add_stock(symbol, name, sector=None):
    symbol = symbol.upper()
    stocks = load_watchlist()
    existing = next((s for s in stocks if s['symbol'] == symbol), None)
    if existing:
        existing.update({'name': name, 'sector': sector})
        print(f'Updated: {symbol}')
    else:
        stocks.append({'symbol': symbol, 'name': name, 'sector': sector})
        print(f'Added: {symbol} ({name}) [{sector or "no sector"}]')
    save_watchlist(stocks)


def remove_stock(symbol):
    symbol = symbol.upper()
    stocks = load_watchlist()
    before = len(stocks)
    stocks = [s for s in stocks if s['symbol'] != symbol]
    if len(stocks) < before:
        save_watchlist(stocks)
        print(f'Removed: {symbol}')
    else:
        print(f'Not found: {symbol}')


SEED_STOCKS = [
    ('AAPL', 'Apple', 'Technology'),
    ('ARM', 'ARM Holdings', 'Technology'),
    ('NVDA', 'NVIDIA', 'Technology'),
    ('GOOGL', 'Alphabet', 'Technology'),
    ('QBTS', 'D-Wave Quantum', 'Technology'),
    ('IREN', 'IREN', 'Technology'),
    ('APLD', 'Applied Digital', 'Technology'),
    ('SAP.DE', 'SAP SE', 'Technology'),
    ('ASML', 'ASML Holding', 'Technology'),
    ('VST', 'Vistra Energy', 'Energy'),
    ('CEG', 'Constellation Energy', 'Energy'),
    ('ENR.DE', 'Siemens Energy', 'Energy'),
    ('SI=F', 'Silver Futures', 'Commodities'),
    ('GC=F', 'Gold Futures', 'Commodities'),
]


def seed_watchlist():
    print('Seeding watchlist...')
    for symbol, name, sector in SEED_STOCKS:
        add_stock(symbol, name, sector)
    print(f'\nDone! Seeded {len(SEED_STOCKS)} stocks.')


USAGE = """
Silver Hawk Trading - Stock Admin

Usage:
  python admin_stocks.py list                          Show all stocks
  python admin_stocks.py add NVDA "NVIDIA" Technology  Add a stock
  python admin_stocks.py remove NVDA                   Remove a stock
  python admin_stocks.py seed                          Seed initial watchlist
"""

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == 'list':
        list_stocks()
    elif cmd == 'add':
        if len(sys.argv) < 4:
            print('Usage: python admin_stocks.py add SYMBOL "Name" [Sector]')
            sys.exit(1)
        sector = sys.argv[4] if len(sys.argv) > 4 else None
        add_stock(sys.argv[2], sys.argv[3], sector)
    elif cmd == 'remove':
        if len(sys.argv) < 3:
            print('Usage: python admin_stocks.py remove SYMBOL')
            sys.exit(1)
        remove_stock(sys.argv[2])
    elif cmd == 'seed':
        seed_watchlist()
    else:
        print(USAGE)
