#!/usr/bin/env python3
"""Silver Hawk Trading - Admin CLI for managing the stock watchlist.
Thin wrapper around prediction_db.py watchlist commands."""

import sys

USAGE = """Silver Hawk Trading - Stock Admin

Usage:
  python admin_stocks.py list                       Show all stocks
  python admin_stocks.py add SYMBOL "Name" Sector   Add a stock
  python admin_stocks.py remove SYMBOL              Remove a stock

All data is stored in memory/predictions.db (single source of truth).
"""

if __name__ == '__main__':
    from prediction_db import get_watchlist_symbols, get_db

    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == 'list':
        symbols = get_watchlist_symbols()
        if not symbols:
            print('Watchlist is empty.')
            print('Add symbols: python admin_stocks.py add SYMBOL "Name" Sector')
            sys.exit(0)
        cur_sector = None
        for s in sorted(symbols, key=lambda x: (x['sector'], x['symbol'])):
            if s['sector'] != cur_sector:
                cur_sector = s['sector']
                print(f'\n  --- {cur_sector} ---')
            print(f"  {s['symbol']:<10} {s['name']}")
        print(f'\nTotal: {len(symbols)} symbols')

    elif cmd == 'add':
        if len(sys.argv) < 5:
            print('Usage: python admin_stocks.py add SYMBOL "Name" Sector')
            sys.exit(1)
        sym, name, sector = sys.argv[2].upper(), sys.argv[3], sys.argv[4]
        conn = get_db()
        conn.execute(
            'INSERT INTO watchlist (symbol, name, sector) VALUES (?, ?, ?) '
            'ON CONFLICT(symbol) DO UPDATE SET name=excluded.name, sector=excluded.sector, active=1',
            (sym, name, sector))
        conn.commit()
        conn.close()
        print(f'Added: {sym} ({name}, {sector})')

    elif cmd == 'remove':
        if len(sys.argv) < 3:
            print('Usage: python admin_stocks.py remove SYMBOL')
            sys.exit(1)
        sym = sys.argv[2].upper()
        conn = get_db()
        r = conn.execute('UPDATE watchlist SET active=0 WHERE symbol=?', (sym,))
        conn.commit()
        conn.close()
        print(f'Removed: {sym}' if r.rowcount else f'Not found: {sym}')

    else:
        print(USAGE)
