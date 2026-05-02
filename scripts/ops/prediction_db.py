#!/usr/bin/env python3
"""Silver Hawk — Trading Database v2.

Single source of truth for analyses, trades, and portfolio state.
Replaces both prediction_db.py v1 AND portfolio.md.

Workflow:
    # 1. Analysis done (ALWAYS saved — traded or not)
    python prediction_db.py record SYMBOL --direction LONG --confidence 68 \\
        --entry 135.50 --stop 128.00 --target 155.00 --ko 120.00 \\
        --regime TRENDING --atr-pct 4.5 --reason "Your thesis here"

    # 1a. Analysis under SW2 cooldown clamp (NO-TRADE Output Clamp)
    #     entry/stop/target/ko OMITTED — recorded as NULL
    python prediction_db.py record SYMBOL --direction LONG --confidence 70 \\
        --regime TRENDING --atr-pct 4.5 \\
        --reason "SW2 cooldown clamp. Case B. eligible_at=..."

    # 2. User confirms trade
    python prediction_db.py open 3 --shares 75 --cert-price 2.67

    # 3. v5 confirmation buy
    python prediction_db.py confirm 3 --shares 49 --cert-price 2.81

    # 4. Partial/full exit
    python prediction_db.py close 3 --shares 62 --exit-price 3.31 --reason target

    # 5. Check portfolio state
    python prediction_db.py portfolio

    # 6. Update cash
    python prediction_db.py cash 852.07

    # 7. Fill real outcomes for backtesting (run daily)
    python prediction_db.py fill

    # 8. Analyze prediction quality (traded vs skipped)
    python prediction_db.py analyze

    # Other: list [--open|--closed], export

Schema note (2026-04-29): entry_price / stop_price / target_price are
nullable to support SW2 NO-TRADE Output Clamp.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_FILE = os.path.join(PROJECT_ROOT, 'memory', 'predictions.db')

# Allow `from lib.X` when invoked directly as `python3 scripts/ops/prediction_db.py`
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from lib.risk_audit import MAX_OPEN_TURBOS


# ─── Database ────────────────────────────────────────────────────────

def get_db():
    """Get database connection, create/migrate tables."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')

    conn.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT', 'NO_TRADE')),
        confidence INTEGER NOT NULL CHECK(confidence BETWEEN 0 AND 100),

        -- Legacy trade-plan columns (still written by old `record` paths, kept for history)
        entry_price REAL,
        stop_price REAL,
        target_price REAL,
        ko_level REAL,

        -- v1.0 trade-plan columns (Step 4 of v1.0 pipeline writes these)
        entry_low REAL,
        entry_high REAL,
        target1 REAL,
        target2 REAL,
        ko REAL,
        cert_isin TEXT,
        run_id TEXT,

        regime TEXT,
        atr_pct REAL,
        reason TEXT,

        -- Position tracking
        status TEXT NOT NULL DEFAULT 'analysis',
        shares INTEGER DEFAULT 0,
        cert_buyin REAL,
        cert_type TEXT DEFAULT 'turbo',
        invested_eur REAL DEFAULT 0,

        -- Outcomes (filled by 'fill' command — works for ALL, traded or not)
        price_1d REAL, price_3d REAL, price_5d REAL,
        price_10d REAL, price_20d REAL,
        max_favorable REAL, max_adverse REAL,
        stop_triggered INTEGER DEFAULT 0, stop_triggered_day INTEGER,
        target_hit INTEGER DEFAULT 0, target_hit_day INTEGER,
        plus20_hit INTEGER DEFAULT 0, plus20_hit_day INTEGER,
        outcome_filled INTEGER DEFAULT 0, outcome_filled_at TEXT,

        -- Realized results
        shares_closed INTEGER DEFAULT 0,
        realized_pnl_eur REAL DEFAULT 0,
        closed_at TEXT,

        -- Legacy compat
        trade_taken INTEGER DEFAULT 0,
        exit_eur REAL,
        actual_entry REAL, actual_exit REAL, actual_pnl_pct REAL,
        trade_notes TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS close_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id INTEGER NOT NULL,
        closed_at TEXT NOT NULL DEFAULT (datetime('now')),
        shares INTEGER NOT NULL,
        cert_exit_price REAL NOT NULL,
        pnl_eur REAL,
        reason TEXT,
        FOREIGN KEY (prediction_id) REFERENCES predictions(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS portfolio_state (
        key TEXT PRIMARY KEY,
        value REAL,
        updated_at TEXT DEFAULT (datetime('now'))
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        sector TEXT NOT NULL DEFAULT 'Unknown',
        added_at TEXT NOT NULL DEFAULT (datetime('now')),
        active INTEGER NOT NULL DEFAULT 1,
        price REAL, change_pct REAL, rsi REAL, sma50 REAL, sma200 REAL,
        market_cap INTEGER, analyst_rating TEXT, last_updated TEXT
    )''')

    # Migrate: add watchlist columns if missing (for existing DBs)
    wl_existing = {row[1] for row in conn.execute('PRAGMA table_info(watchlist)').fetchall()}
    for col, typ in [('price', 'REAL'), ('change_pct', 'REAL'), ('rsi', 'REAL'),
                     ('sma50', 'REAL'), ('sma200', 'REAL'), ('market_cap', 'INTEGER'),
                     ('analyst_rating', 'TEXT'), ('last_updated', 'TEXT')]:
        if col not in wl_existing:
            conn.execute(f'ALTER TABLE watchlist ADD COLUMN {col} {typ}')

    # Migrate: add columns if missing (for existing DBs upgrading to v2 or v1.0)
    existing = {row[1] for row in conn.execute('PRAGMA table_info(predictions)').fetchall()}
    new_cols = [
        ('status', "TEXT NOT NULL DEFAULT 'analysis'"),
        ('shares', 'INTEGER DEFAULT 0'),
        ('cert_buyin', 'REAL'),
        ('cert_type', "TEXT DEFAULT 'turbo'"),
        ('shares_closed', 'INTEGER DEFAULT 0'),
        ('realized_pnl_eur', 'REAL DEFAULT 0'),
        ('closed_at', 'TEXT'),
        ('invested_eur', 'REAL DEFAULT 0'),
        ('reason', 'TEXT'),
        # v1.0 trade-plan columns
        ('entry_low', 'REAL'),
        ('entry_high', 'REAL'),
        ('target1', 'REAL'),
        ('target2', 'REAL'),
        ('ko', 'REAL'),
        ('cert_isin', 'TEXT'),
        ('run_id', 'TEXT'),
    ]
    for col, typ in new_cols:
        if col not in existing:
            conn.execute(f'ALTER TABLE predictions ADD COLUMN {col} {typ}')

    # CHECK-constraint diagnostic: SQLite cannot ALTER a CHECK in place,
    # so the v1.0 migration in scripts/ops/migrate_v1_0.py must have run
    # at least once. If it hasn't, every NO_TRADE record will fail with
    # a confusing constraint error. Surface that early.
    table_sql_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='predictions'"
    ).fetchone()
    table_sql = (table_sql_row[0] if table_sql_row else '') or ''
    if "'NO_TRADE'" not in table_sql:
        print(
            "WARN: predictions.direction CHECK constraint does not allow "
            "'NO_TRADE'. Run `python3 scripts/ops/migrate_v1_0.py` once to "
            "relax the constraint; otherwise NO_TRADE records will fail "
            "with a CHECK violation.",
            file=sys.stderr,
        )

    conn.commit()
    return conn


# ─── Record (Step 4 of analysis — ALL analyses saved) ───────────────

def record_prediction(args):
    """Record a new analysis prediction.

    Two write modes:
      legacy (v2): --entry --stop --target --ko    → entry_price/stop_price/target_price/ko_level
      v1.0:        --entry-low --entry-high --target1 --target2 --ko-v1
                   plus --cert-isin --run-id        → entry_low/entry_high/target1/target2/ko/...

    Direction can be LONG / SHORT / NO_TRADE. NO_TRADE records keep all
    trade-plan columns NULL (caller passes none).
    """
    direction = args.direction.upper()
    if direction not in {'LONG', 'SHORT', 'NO_TRADE'}:
        sys.exit(f'❌ direction must be LONG | SHORT | NO_TRADE, got {direction}')

    # v1.0 takes precedence if any v1.0 flag is set
    v1_flags = (
        getattr(args, 'entry_low', None),
        getattr(args, 'entry_high', None),
        getattr(args, 'target1', None),
        getattr(args, 'target2', None),
        getattr(args, 'ko_v1', None),
        getattr(args, 'cert_isin', None),
        getattr(args, 'run_id', None),
    )
    is_v1 = any(v is not None for v in v1_flags)

    conn = get_db()
    if is_v1:
        conn.execute('''INSERT INTO predictions
            (symbol, direction, confidence,
             entry_low, entry_high, target1, target2, ko, cert_isin, run_id,
             regime, atr_pct, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'analysis')''',
            (args.symbol.upper(), direction, args.confidence,
             args.entry_low, args.entry_high, args.target1, args.target2,
             args.ko_v1, args.cert_isin, args.run_id,
             args.regime, args.atr_pct, args.reason))
    else:
        conn.execute('''INSERT INTO predictions
            (symbol, direction, confidence, entry_price, stop_price, target_price,
             ko_level, regime, atr_pct, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'analysis')''',
            (args.symbol.upper(), direction, args.confidence,
             args.entry, args.stop, args.target,
             args.ko, args.regime, args.atr_pct, args.reason))
    conn.commit()
    rid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    if direction == 'NO_TRADE':
        print(f'✅ Analysis #{rid}: {args.symbol} NO_TRADE conf={args.confidence}% '
              f'(reason recorded, no trade-plan fields)')
    elif is_v1:
        elo = f'${args.entry_low:.2f}' if args.entry_low is not None else 'NULL'
        ehi = f'${args.entry_high:.2f}' if args.entry_high is not None else 'NULL'
        t1 = f'${args.target1:.2f}' if args.target1 is not None else 'NULL'
        t2 = f'${args.target2:.2f}' if args.target2 is not None else 'NULL'
        ko = f'${args.ko_v1:.2f}' if args.ko_v1 is not None else 'NULL'
        print(f'✅ Analysis #{rid}: {args.symbol} {direction} '
              f'conf={args.confidence}% entry={elo}-{ehi} t1={t1} t2={t2} ko={ko} '
              f'cert={args.cert_isin or "—"} run={args.run_id or "—"}')
    elif args.entry is None and args.stop is None and args.target is None:
        # SW2 NO-TRADE Output Clamp record (legacy path)
        print(f'✅ Analysis #{rid}: {args.symbol} {direction} '
              f'conf={args.confidence}% [SW2 cooldown clamp — '
              f'entry/stop/target/ko = NULL]')
    else:
        entry_str = f'${args.entry:.2f}' if args.entry is not None else 'NULL'
        stop_str = f'${args.stop:.2f}' if args.stop is not None else 'NULL'
        target_str = f'${args.target:.2f}' if args.target is not None else 'NULL'
        print(f'✅ Analysis #{rid}: {args.symbol} {direction} '
              f'conf={args.confidence}% entry={entry_str} stop={stop_str} target={target_str}')
    conn.close()


# ─── Open (user confirms: "gekauft!") ───────────────────────────────

def open_position(args):
    """Mark an analysis as traded — open position."""
    conn = get_db()
    row = conn.execute('SELECT * FROM predictions WHERE id = ?', (args.id,)).fetchone()
    if not row:
        sys.exit(f'❌ #{args.id} not found.')
    if row['status'] == 'open':
        sys.exit(f'⚠️  #{args.id} already open. Use "confirm" to add shares.')
    if row['status'] == 'closed':
        sys.exit(f'❌ #{args.id} already closed.')

    # NO_TRADE records have no trade plan and cannot be opened
    if row['direction'] == 'NO_TRADE':
        sys.exit(f'❌ #{args.id} is NO_TRADE — no trade plan, cannot open.')

    # Guard: cannot open a record without any trade plan (legacy SW2 clamp
    # OR a v1.0 record that somehow has neither legacy nor v1.0 fields).
    cols = row.keys()
    has_legacy = (
        row['entry_price'] is not None
        and row['stop_price'] is not None
        and row['target_price'] is not None
    )
    has_v1 = (
        'entry_low' in cols and row['entry_low'] is not None
        and 'entry_high' in cols and row['entry_high'] is not None
        and 'ko' in cols and row['ko'] is not None
    )
    if not (has_legacy or has_v1):
        sys.exit(
            f'❌ #{args.id} has no usable trade plan (neither legacy entry/stop/target '
            f'nor v1.0 entry_low/entry_high/ko). Likely an SW2 cooldown clamp — '
            f'run a fresh analysis instead of opening this record.'
        )

    invested = round(args.shares * args.cert_price, 2)
    cert_type = args.cert_type or 'turbo'
    cert_isin = getattr(args, 'cert_isin', None)
    if cert_isin:
        conn.execute('''UPDATE predictions SET
            status='open', trade_taken=1,
            shares=?, cert_buyin=?, cert_type=?, invested_eur=?, cert_isin=?
            WHERE id=?''',
            (args.shares, args.cert_price, cert_type, invested, cert_isin, args.id))
    else:
        conn.execute('''UPDATE predictions SET
            status='open', trade_taken=1,
            shares=?, cert_buyin=?, cert_type=?, invested_eur=?
            WHERE id=?''',
            (args.shares, args.cert_price, cert_type, invested, args.id))
    conn.commit()
    extra = f' isin={cert_isin}' if cert_isin else ''
    print(f'✅ #{args.id} {row["symbol"]} OPEN: {args.shares} Stk @ €{args.cert_price:.2f} '
          f'= €{invested:.2f} ({cert_type}){extra}')
    conn.close()


# ─── Confirm (v5 confirmation buy) ──────────────────────────────────

def confirm_position(args):
    """v5 confirmation — add shares to existing open position."""
    conn = get_db()
    row = conn.execute('SELECT * FROM predictions WHERE id = ?', (args.id,)).fetchone()
    if not row:
        sys.exit(f'❌ #{args.id} not found.')
    if row['status'] != 'open':
        sys.exit(f'❌ #{args.id} not open (status: {row["status"]}). Use "open" first.')

    old_shares = row['shares'] or 0
    old_invested = row['invested_eur'] or 0
    add_invested = round(args.shares * args.cert_price, 2)

    total_shares = old_shares + args.shares
    total_invested = old_invested + add_invested
    new_avg = round(total_invested / total_shares, 4) if total_shares else 0

    conn.execute('''UPDATE predictions SET
        shares=?, cert_buyin=?, invested_eur=?
        WHERE id=?''',
        (total_shares, new_avg, total_invested, args.id))
    conn.commit()
    print(f'✅ #{args.id} {row["symbol"]} CONFIRMED: +{args.shares} @ €{args.cert_price:.2f}')
    print(f'   Total: {total_shares} Stk @ €{new_avg:.4f} = €{total_invested:.2f}')
    conn.close()


# ─── Close (partial or full exit) ───────────────────────────────────

def close_position(args):
    """Close (partial or full) a position."""
    conn = get_db()
    row = conn.execute('SELECT * FROM predictions WHERE id = ?', (args.id,)).fetchone()
    if not row:
        sys.exit(f'❌ #{args.id} not found.')
    if row['status'] != 'open':
        sys.exit(f'❌ #{args.id} not open (status: {row["status"]}).')

    remaining = (row['shares'] or 0) - (row['shares_closed'] or 0)
    close_shares = args.shares if args.shares else remaining

    if close_shares > remaining:
        sys.exit(f'❌ Only {remaining} shares remaining (requested {close_shares}).')

    cert_buyin = row['cert_buyin'] or 0
    pnl_eur = round(close_shares * (args.exit_price - cert_buyin), 2)

    conn.execute('''INSERT INTO close_events
        (prediction_id, shares, cert_exit_price, pnl_eur, reason)
        VALUES (?, ?, ?, ?, ?)''',
        (args.id, close_shares, args.exit_price, pnl_eur, args.reason))

    new_closed = (row['shares_closed'] or 0) + close_shares
    new_pnl = round((row['realized_pnl_eur'] or 0) + pnl_eur, 2)
    fully_closed = new_closed >= (row['shares'] or 0)

    updates = 'shares_closed=?, realized_pnl_eur=?'
    params = [new_closed, new_pnl]
    if fully_closed:
        updates += ", status='closed', closed_at=datetime('now')"
        updates += ', exit_eur=?'
        params.append(round((row['invested_eur'] or 0) + new_pnl, 2))
    params.append(args.id)

    conn.execute(f'UPDATE predictions SET {updates} WHERE id=?', params)
    conn.commit()

    left = (row['shares'] or 0) - new_closed
    status = 'CLOSED' if fully_closed else f'{left} Stk offen'
    reason = f' ({args.reason})' if args.reason else ''
    print(f'✅ #{args.id} {row["symbol"]}: -{close_shares} Stk @ €{args.exit_price:.2f} '
          f'= {pnl_eur:+.2f} EUR{reason}')
    print(f'   {status} | Realized: {new_pnl:+.2f} EUR')
    conn.close()


# ─── Portfolio (replaces portfolio.md) ───────────────────────────────

def show_portfolio(args):
    """Show current portfolio state."""
    conn = get_db()

    cash_row = conn.execute("SELECT value FROM portfolio_state WHERE key='cash'").fetchone()
    cash = cash_row['value'] if cash_row else 0

    positions = conn.execute(
        "SELECT * FROM predictions WHERE status='open' ORDER BY created_at").fetchall()
    closed = conn.execute(
        "SELECT * FROM predictions WHERE status='closed' ORDER BY closed_at DESC LIMIT 10"
    ).fetchall()
    analyses = conn.execute(
        "SELECT COUNT(*) as n FROM predictions WHERE status='analysis'").fetchone()['n']

    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    print(f'PORTFOLIO — {now}')
    print('=' * 70)
    print(f'💰 Cash: {cash:,.2f} EUR\n')

    total_invested = 0
    if positions:
        print('OPEN POSITIONS:')
        hdr = f'  {"#":>3} {"Symbol":<9} {"Dir":<6} {"Stk":>5} {"Avg":>7} {"Invested":>9} {"Type":<8} {"Conf":>4} {"Realized":>10}'
        print(hdr)
        print(f'  {"-" * (len(hdr) - 2)}')
        for p in positions:
            shares_open = (p['shares'] or 0) - (p['shares_closed'] or 0)
            inv_open = round(shares_open * (p['cert_buyin'] or 0), 2)
            total_invested += inv_open
            real = p['realized_pnl_eur'] or 0
            real_str = f'{real:+.0f} EUR' if real else ''
            ctype = p["cert_type"] or "turbo"
            hedge_marker = ' [H]' if ctype == 'hedge' else ''
            print(f'  {p["id"]:>3} {p["symbol"]:<9} {p["direction"]:<6} {shares_open:>5} '
                  f'€{p["cert_buyin"] or 0:>5.2f} €{inv_open:>8.2f} '
                  f'{ctype:<8} {p["confidence"]:>3}% {real_str:>10}{hedge_marker}')
    else:
        print('Keine offenen Positionen.')

    portfolio_total = cash + total_invested
    slots = sum(1 for p in positions if (p['cert_type'] or 'turbo') != 'hedge')
    hedges = sum(1 for p in positions if (p['cert_type'] or 'turbo') == 'hedge')
    hedge_str = f' + {hedges}H' if hedges else ''
    print(f'\n  Invested: {total_invested:,.2f} EUR | Cash: {cash:,.2f} EUR')
    print(f'  Portfolio: ~{portfolio_total:,.0f} EUR | Slots: {slots}/{MAX_OPEN_TURBOS}{hedge_str}')

    if closed:
        print(f'\nGESCHLOSSENE TRADES:')
        for c in closed:
            pnl = c['realized_pnl_eur'] or 0
            dur = ''
            if c['closed_at'] and c['created_at']:
                try:
                    d1 = datetime.fromisoformat(c['created_at'])
                    d2 = datetime.fromisoformat(c['closed_at'])
                    dur = f' ({(d2 - d1).days}d)'
                except Exception:
                    pass
            inv = c['invested_eur'] or 0
            pct = (pnl / inv * 100) if inv else 0
            print(f'  #{c["id"]} {c["symbol"]:<8} {c["direction"]:<5} '
                  f'{pnl:+.2f} EUR ({pct:+.0f}%){dur}')

    if analyses:
        print(f'\n📊 Ungehandelte Analysen: {analyses} (werden trotzdem gebacktestet)')

    conn.close()


# ─── Cash ────────────────────────────────────────────────────────────

def update_cash(args):
    """Set current cash balance."""
    conn = get_db()
    conn.execute('''INSERT OR REPLACE INTO portfolio_state (key, value, updated_at)
        VALUES ('cash', ?, datetime('now'))''', (args.amount,))
    conn.commit()
    print(f'✅ Cash: {args.amount:,.2f} EUR')
    conn.close()


# ─── Fill (backtest outcomes — ALL predictions, traded or not) ───────

def fill_outcomes(args):
    """Fill real market outcomes for predictions old enough."""
    try:
        import yfinance as yf
    except ImportError:
        sys.exit('yfinance required: pip install yfinance')

    conn = get_db()
    # Skip cooldown-clamped records (no trade plan to evaluate). Two record
    # shapes are accepted:
    #   legacy v2 — entry_price + stop_price + target_price + ko_level
    #   v1.0      — entry_low + entry_high + target1 + ko (entry-range mid is the
    #               proxy entry; cert-stop-staircase replaces stop_price)
    rows = conn.execute('''SELECT * FROM predictions
        WHERE direction != 'NO_TRADE'
          AND outcome_filled = 0
          AND created_at < datetime('now', '-1 day')
          AND (
                (entry_price IS NOT NULL AND stop_price IS NOT NULL AND target_price IS NOT NULL)
             OR (entry_low IS NOT NULL AND entry_high IS NOT NULL AND target1 IS NOT NULL AND ko IS NOT NULL)
          )
    ''').fetchall()

    if not rows:
        print('No predictions to fill.')
        conn.close()
        return

    print(f'Filling outcomes for {len(rows)} predictions...')
    for row in rows:
        pid, sym = row['id'], row['symbol']
        direction = row['direction']
        cols = row.keys()

        is_v1 = (
            'entry_low' in cols and row['entry_low'] is not None
            and 'entry_high' in cols and row['entry_high'] is not None
            and 'target1' in cols and row['target1'] is not None
            and 'ko' in cols and row['ko'] is not None
        )

        if is_v1:
            entry = (float(row['entry_low']) + float(row['entry_high'])) / 2.0
            target = float(row['target1'])  # primary take-profit (50%)
            ko = float(row['ko'])
            # No underlying-stop in v1.0; cert-staircase handles risk on the
            # cert side. For the "stop_triggered" outcome metric we re-purpose
            # the underlying KO as the stop level — KO IS the stop on the
            # underlying side (it's the auto-knockout boundary).
            stop = ko
            schema_tag = 'v1.0'
        else:
            entry = float(row['entry_price'])
            stop = float(row['stop_price'])
            target = float(row['target_price'])
            ko = float(row['ko_level']) if row['ko_level'] is not None else None
            schema_tag = 'legacy'

        created = datetime.fromisoformat(row['created_at'])

        start = created.date()
        end = min(start + timedelta(days=35), datetime.now(timezone.utc).date())

        try:
            df = yf.download(sym, start=str(start), end=str(end), progress=False)
            if df is not None and df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f'  #{pid} {sym}: download error — {e}')
            continue

        if df is None or len(df) < 2:
            print(f'  #{pid} {sym}: insufficient data')
            continue

        if len(df) - 1 < 5:
            print(f'  #{pid} {sym}: only {len(df)-1} days, waiting...')
            continue

        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values

        price_1d = float(closes[1]) if len(closes) > 1 else None
        price_3d = float(closes[3]) if len(closes) > 3 else None
        price_5d = float(closes[5]) if len(closes) > 5 else None
        price_10d = float(closes[10]) if len(closes) > 10 else None
        price_20d = float(closes[20]) if len(closes) > 20 else None

        if direction == 'LONG':
            max_fav = round((float(max(highs[1:])) - entry) / entry * 100, 2)
            max_adv = round((float(min(lows[1:])) - entry) / entry * 100, 2)
        else:
            max_fav = round((entry - float(min(lows[1:]))) / entry * 100, 2)
            max_adv = round((float(max(highs[1:])) - entry) / entry * 100, 2)

        stop_hit, stop_day = 0, None
        for i in range(1, len(df)):
            hit = (direction == 'LONG' and float(lows[i]) <= stop) or \
                  (direction == 'SHORT' and float(highs[i]) >= stop)
            if hit:
                stop_hit, stop_day = 1, i
                break

        tgt_hit, tgt_day = 0, None
        for i in range(1, len(df)):
            hit = (direction == 'LONG' and float(highs[i]) >= target) or \
                  (direction == 'SHORT' and float(lows[i]) <= target)
            if hit:
                tgt_hit, tgt_day = 1, i
                break

        p20_hit, p20_day = 0, None
        if ko and ko > 0:
            leverage = entry / abs(entry - ko) if abs(entry - ko) > 0.01 else 1
            needed = 20.0 / leverage
            for i in range(1, len(df)):
                if direction == 'LONG':
                    move = (float(highs[i]) - entry) / entry * 100
                else:
                    move = (entry - float(lows[i])) / entry * 100
                if move >= needed:
                    p20_hit, p20_day = 1, i
                    break

        conn.execute('''UPDATE predictions SET
            price_1d=?, price_3d=?, price_5d=?, price_10d=?, price_20d=?,
            max_favorable=?, max_adverse=?,
            stop_triggered=?, stop_triggered_day=?,
            target_hit=?, target_hit_day=?,
            plus20_hit=?, plus20_hit_day=?,
            outcome_filled=1, outcome_filled_at=?
            WHERE id=?''',
            (price_1d, price_3d, price_5d, price_10d, price_20d,
             max_fav, max_adv, stop_hit, stop_day, tgt_hit, tgt_day,
             p20_hit, p20_day, datetime.now(timezone.utc).isoformat(), pid))

        s = f'day {stop_day}' if stop_hit else 'NO'
        t = f'day {tgt_day}' if tgt_hit else 'NO'
        p = f'day {p20_day}' if p20_hit else 'NO'
        status = row['status']
        traded_str = f' [{status.upper()}]' if status != 'analysis' else ' [SKIPPED]'
        stop_label = 'KO' if schema_tag == 'v1.0' else 'Stop'
        target_label = 'Tgt1' if schema_tag == 'v1.0' else 'Tgt'
        print(f'  #{pid} {sym} {direction}{traded_str} ({schema_tag}): '
              f'MFE={max_fav:+.1f}% MAE={max_adv:+.1f}% '
              f'{stop_label}={s} {target_label}={t} +20%={p}')

    conn.commit()
    conn.close()


# ─── Analyze (traded vs skipped comparison) ──────────────────────────

def analyze_predictions(args):
    """Analyze prediction quality — traded vs skipped."""
    conn = get_db()

    filled = conn.execute('SELECT * FROM predictions WHERE outcome_filled = 1').fetchall()
    total = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
    unfilled = total - len(filled)

    if not filled:
        print(f'No filled predictions yet. Total: {total} | Unfilled: {unfilled}')
        conn.close()
        return

    lines = [f'PREDICTION ANALYSIS ({len(filled)} filled, {unfilled} pending)', '=' * 65]

    stop_hits = sum(1 for r in filled if r['stop_triggered'])
    tgt_hits = sum(1 for r in filled if r['target_hit'])
    p20_hits = sum(1 for r in filled if r['plus20_hit'])
    avg_mfe = sum(r['max_favorable'] or 0 for r in filled) / len(filled)
    avg_mae = sum(r['max_adverse'] or 0 for r in filled) / len(filled)

    lines.append(f'\nOverall (n={len(filled)}):')
    lines.append(f'  Stop triggered:  {stop_hits}/{len(filled)} ({stop_hits/len(filled)*100:.0f}%)')
    lines.append(f'  Target hit:      {tgt_hits}/{len(filled)} ({tgt_hits/len(filled)*100:.0f}%)')
    lines.append(f'  +20% cert hit:   {p20_hits}/{len(filled)} ({p20_hits/len(filled)*100:.0f}%)')
    lines.append(f'  Avg MFE: {avg_mfe:+.1f}% | Avg MAE: {avg_mae:+.1f}%')

    # ── Traded vs Skipped ──
    traded = [r for r in filled if r['status'] in ('open', 'closed')]
    skipped = [r for r in filled if r['status'] == 'analysis']

    if traded and skipped:
        lines.append(f'\n{"─" * 65}')
        lines.append('TRADED vs SKIPPED:')
        for label, group in [('Traded', traded), ('Skipped', skipped)]:
            n = len(group)
            s_pct = sum(1 for r in group if r['stop_triggered']) / n * 100
            t_pct = sum(1 for r in group if r['target_hit']) / n * 100
            mfe = sum(r['max_favorable'] or 0 for r in group) / n
            mae = sum(r['max_adverse'] or 0 for r in group) / n
            lines.append(f'  {label:<8} (n={n:>2}): Stop={s_pct:>4.0f}% Target={t_pct:>4.0f}% '
                         f'MFE={mfe:>+5.1f}% MAE={mae:>+5.1f}%')
        # Quality check
        t_tgt = sum(1 for r in traded if r['target_hit']) / len(traded) * 100 if traded else 0
        s_tgt = sum(1 for r in skipped if r['target_hit']) / len(skipped) * 100 if skipped else 0
        if s_tgt > t_tgt + 10:
            lines.append(f'  ⚠️  Skipped trades hit target MORE often! Missed opportunities.')
        elif t_tgt > s_tgt + 10:
            lines.append(f'  ✅ Good trade selection — traded analyses outperform skipped.')

    # ── By confidence bracket ──
    lines.append(f'\n{"─" * 65}')
    lines.append('BY CONFIDENCE:')
    lines.append(f'  {"Bracket":<10} {"n":>3} {"Stop%":>6} {"Tgt%":>6} {"+20%":>6} {"MFE":>7} {"MAE":>7}')
    for lo, hi in [(50, 59), (60, 69), (70, 79), (80, 100)]:
        b = [r for r in filled if lo <= r['confidence'] <= hi]
        if not b:
            continue
        n = len(b)
        lines.append(f'  {lo}-{hi}%    {n:>3} {sum(1 for r in b if r["stop_triggered"])/n*100:>5.0f}% '
                     f'{sum(1 for r in b if r["target_hit"])/n*100:>5.0f}% '
                     f'{sum(1 for r in b if r["plus20_hit"])/n*100:>5.0f}% '
                     f'{sum(r["max_favorable"] or 0 for r in b)/n:>+6.1f}% '
                     f'{sum(r["max_adverse"] or 0 for r in b)/n:>+6.1f}%')

    # ── By direction ──
    for d in ('LONG', 'SHORT'):
        group = [r for r in filled if r['direction'] == d]
        if not group:
            continue
        n = len(group)
        lines.append(f'\n{d} (n={n}): '
                     f'Stop={sum(1 for r in group if r["stop_triggered"])/n*100:.0f}% '
                     f'Target={sum(1 for r in group if r["target_hit"])/n*100:.0f}%')

    # ── Key question ──
    lines.append(f'\n{"=" * 65}')
    lines.append('DOES CONFIDENCE PREDICT SUCCESS?')
    hi_c = [r for r in filled if r['confidence'] >= 70]
    lo_c = [r for r in filled if r['confidence'] < 65]
    if hi_c and lo_c:
        ht = sum(1 for r in hi_c if r['target_hit']) / len(hi_c) * 100
        lt = sum(1 for r in lo_c if r['target_hit']) / len(lo_c) * 100
        lines.append(f'  High (>=70%, n={len(hi_c)}): Target={ht:.0f}%')
        lines.append(f'  Low  (<65%, n={len(lo_c)}):  Target={lt:.0f}%')
        lines.append(f'  → {"YES" if ht > lt else "NO"}: {"correlates" if ht > lt else "does NOT correlate"}')
    else:
        lines.append('  Not enough data yet.')

    # ── Realized P&L (actual trades) ──
    realized = [r for r in conn.execute(
        "SELECT * FROM predictions WHERE status='closed'").fetchall()]
    if realized:
        total_pnl = sum(r['realized_pnl_eur'] or 0 for r in realized)
        total_inv = sum(r['invested_eur'] or 0 for r in realized)
        wins = sum(1 for r in realized if (r['realized_pnl_eur'] or 0) > 0)
        lines.append(f'\n{"─" * 65}')
        lines.append(f'REALIZED P&L: {total_pnl:+.2f} EUR from {total_inv:.2f} EUR '
                     f'({len(realized)} trades, {wins} wins)')

    output = '\n'.join(lines)
    print(output)

    conn.close()


# ─── List ────────────────────────────────────────────────────────────

def list_predictions(args):
    """List predictions with optional status filter."""
    conn = get_db()

    if hasattr(args, 'status_filter') and args.status_filter:
        rows = conn.execute(
            'SELECT * FROM predictions WHERE status=? ORDER BY created_at DESC',
            (args.status_filter,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM predictions ORDER BY created_at DESC').fetchall()

    if not rows:
        print('No predictions found.')
        conn.close()
        return

    print(f'{"#":>3} {"Date":<10} {"Symbol":<9} {"Dir":<5} {"Conf":>4} '
          f'{"Entry":>8} {"Stop":>8} {"Target":>8} {"Status":<8} {"Stk":>5} {"P&L":>10}')
    print('-' * 95)

    for r in rows:
        date = r['created_at'][:10]
        status = r['status'].upper()[:7]

        # P&L for closed trades
        pnl_str = ''
        if r['status'] == 'closed':
            pnl = r['realized_pnl_eur'] or 0
            inv = r['invested_eur'] or 0
            pct = (pnl / inv * 100) if inv else 0
            pnl_str = f'{pnl:+.0f}E ({pct:+.0f}%)'
        elif r['status'] == 'open':
            real = r['realized_pnl_eur'] or 0
            pnl_str = f'{real:+.0f}E real' if real else 'offen'
        elif r['outcome_filled']:
            s = '⛔' if r['stop_triggered'] else ('🎯' if r['target_hit'] else '—')
            pnl_str = s

        shares = (r['shares'] or 0) - (r['shares_closed'] or 0)
        shares_str = str(shares) if shares else ''

        reason = r['reason'] or ''
        if len(reason) > 60:
            reason = reason[:57] + '...'

        # Handle NULL trade-plan fields (SW2 cooldown clamp)
        entry_str = f'${r["entry_price"]:>7.2f}' if r["entry_price"] is not None else '   NULL  '
        stop_str = f'${r["stop_price"]:>7.2f}' if r["stop_price"] is not None else '   NULL  '
        target_str = f'${r["target_price"]:>7.2f}' if r["target_price"] is not None else '   NULL  '

        print(f'{r["id"]:>3} {date:<10} {r["symbol"]:<9} {r["direction"]:<5} {r["confidence"]:>3}% '
              f'{entry_str} {stop_str} {target_str} '
              f'{status:<8} {shares_str:>5} {pnl_str:>10}')
        if reason:
            print(f'    └ {reason}')

    conn.close()


# ─── Export ──────────────────────────────────────────────────────────

def export_predictions(args):
    """Export predictions as CSV."""
    conn = get_db()
    rows = conn.execute('SELECT * FROM predictions ORDER BY created_at').fetchall()
    if not rows:
        print('No predictions.')
        conn.close()
        return

    cols = [d[0] for d in conn.execute('SELECT * FROM predictions LIMIT 1').description]
    path = os.path.join(PROJECT_ROOT, 'memory', 'predictions_export.csv')
    with open(path, 'w') as f:
        f.write(','.join(cols) + '\n')
        for r in rows:
            f.write(','.join(str(r[c]) if r[c] is not None else '' for c in cols) + '\n')
    print(f'Exported {len(rows)} predictions to {path}')
    conn.close()


# ─── Pivot (v7: hedge → normal position) ──────────────────────────

def pivot_position(args):
    """v7 Pivot: convert hedge to normal position (direction change confirmed)."""
    conn = get_db()
    row = conn.execute('SELECT * FROM predictions WHERE id = ?', (args.id,)).fetchone()
    if not row:
        sys.exit(f'❌ #{args.id} not found.')
    if row['status'] != 'open':
        sys.exit(f'❌ #{args.id} not open (status: {row["status"]}).')
    if (row['cert_type'] or 'turbo') != 'hedge':
        sys.exit(f'⚠️  #{args.id} is not a hedge (cert_type: {row["cert_type"]}). Pivot only for hedges.')

    conn.execute("UPDATE predictions SET cert_type='turbo' WHERE id=?", (args.id,))
    conn.commit()
    shares_open = (row['shares'] or 0) - (row['shares_closed'] or 0)
    print(f'✅ #{args.id} {row["symbol"]} PIVOT: hedge → turbo ({shares_open} Stk, zählt jetzt als Slot)')
    conn.close()


# ─── Watchlist ─────────────────────────────────────────────────────

def watchlist_add(args):
    """Add a symbol to the watchlist."""
    conn = get_db()
    sym = args.symbol.upper()
    conn.execute(
        'INSERT INTO watchlist (symbol, name, sector) VALUES (?, ?, ?) '
        'ON CONFLICT(symbol) DO UPDATE SET name=excluded.name, sector=excluded.sector, active=1',
        (sym, args.name, args.sector))
    conn.commit()
    print(f'Added: {sym} ({args.name}, {args.sector})')
    conn.close()


def watchlist_remove(args):
    """Remove (deactivate) a symbol from the watchlist."""
    conn = get_db()
    sym = args.symbol.upper()
    r = conn.execute('UPDATE watchlist SET active=0 WHERE symbol=?', (sym,))
    conn.commit()
    if r.rowcount:
        print(f'Removed: {sym}')
    else:
        print(f'Not found: {sym}')
    conn.close()


def watchlist_list(args):
    """List all active watchlist symbols."""
    conn = get_db()
    rows = conn.execute(
        'SELECT symbol, name, sector FROM watchlist WHERE active=1 ORDER BY sector, symbol'
    ).fetchall()
    if not rows:
        print('Watchlist is empty. Add symbols with: python prediction_db.py watchlist-add SYMBOL "Name" Sector')
        conn.close()
        return
    cur_sector = None
    for r in rows:
        if r['sector'] != cur_sector:
            cur_sector = r['sector']
            print(f'\n  {cur_sector}')
        print(f'    {r["symbol"]:10s} {r["name"]}')
    print(f'\n  Total: {len(rows)} symbols')
    conn.close()


def get_watchlist_symbols():
    """Return list of dicts [{symbol, name, sector}, ...] for active watchlist entries.
    Can be imported by other scripts."""
    conn = get_db()
    rows = conn.execute(
        'SELECT symbol, name, sector FROM watchlist WHERE active=1 ORDER BY symbol'
    ).fetchall()
    result = [{'symbol': r['symbol'], 'name': r['name'], 'sector': r['sector']} for r in rows]
    conn.close()
    return result


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Silver Hawk Trading DB v2')
    sub = p.add_subparsers(dest='command')

    # record (entry/stop/target now optional — SW2 cooldown clamp omits them)
    s = sub.add_parser('record', help='Record analysis (always, even if not traded)')
    s.add_argument('symbol')
    s.add_argument('--direction', required=True, choices=['LONG', 'SHORT', 'NO_TRADE'])
    s.add_argument('--confidence', required=True, type=int)
    # Legacy v2 fields
    s.add_argument('--entry', type=float, help='Legacy: single entry price (v2 path)')
    s.add_argument('--stop', type=float, help='Legacy: stop price (v2 path)')
    s.add_argument('--target', type=float, help='Legacy: single target price (v2 path)')
    s.add_argument('--ko', type=float, help='Legacy: KO level (writes ko_level)')
    # v1.0 fields (Step 4 v1.0 pipeline)
    s.add_argument('--entry-low', type=float, help='v1.0: trade-window range low')
    s.add_argument('--entry-high', type=float, help='v1.0: trade-window range high')
    s.add_argument('--target1', type=float, help='v1.0: first take-profit (50 pct)')
    s.add_argument('--target2', type=float, help='v1.0: stretch target (remaining 50 pct)')
    s.add_argument('--ko-v1', dest='ko_v1', type=float,
                   help='v1.0: KO level (writes ko column, separate from legacy ko_level)')
    s.add_argument('--cert-isin', type=str, help='v1.0: chosen cert ISIN from Phase A')
    s.add_argument('--run-id', type=str, help='v1.0: run folder ID (SYMBOL_YYYYMMDD_HHMMSS)')
    # Common
    s.add_argument('--regime', type=str)
    s.add_argument('--atr-pct', type=float)
    s.add_argument('--reason', type=str)

    # open
    s = sub.add_parser('open', help='Mark analysis as traded (position opened)')
    s.add_argument('id', type=int)
    s.add_argument('--shares', required=True, type=int)
    s.add_argument('--cert-price', required=True, type=float)
    s.add_argument('--cert-type', type=str, default='turbo')
    s.add_argument('--cert-isin', type=str,
                   help='Optional: cert ISIN (also written by record --cert-isin in v1.0)')

    # confirm
    s = sub.add_parser('confirm', help='v5 confirmation (add shares)')
    s.add_argument('id', type=int)
    s.add_argument('--shares', required=True, type=int)
    s.add_argument('--cert-price', required=True, type=float)

    # close
    s = sub.add_parser('close', help='Close position (partial or full)')
    s.add_argument('id', type=int)
    s.add_argument('--shares', type=int, help='Shares to close (default: all)')
    s.add_argument('--exit-price', required=True, type=float, help='Cert exit price')
    s.add_argument('--reason', type=str, help='stop/target/manual/time-stop/knockout')

    # portfolio
    sub.add_parser('portfolio', help='Show current portfolio')

    # cash
    s = sub.add_parser('cash', help='Set cash balance')
    s.add_argument('amount', type=float)

    # fill
    sub.add_parser('fill', help='Fill market outcomes (run daily)')

    # analyze
    sub.add_parser('analyze', help='Analyze prediction quality')

    # list
    s = sub.add_parser('list', help='List predictions')
    s.add_argument('--open', dest='status_filter', action='store_const', const='open')
    s.add_argument('--closed', dest='status_filter', action='store_const', const='closed')
    s.add_argument('--analysis', dest='status_filter', action='store_const', const='analysis')

    # pivot (v7)
    s = sub.add_parser('pivot', help='v7: Convert hedge to normal position')
    s.add_argument('id', type=int)

    # export
    sub.add_parser('export', help='Export as CSV')

    # watchlist-add
    s = sub.add_parser('watchlist-add', help='Add symbol to watchlist')
    s.add_argument('symbol')
    s.add_argument('name', help='Display name')
    s.add_argument('sector', help='Sector classification')

    # watchlist-remove
    s = sub.add_parser('watchlist-remove', help='Remove symbol from watchlist')
    s.add_argument('symbol')

    # watchlist
    sub.add_parser('watchlist', help='List watchlist symbols')

    args = p.parse_args()
    cmds = {
        'record': record_prediction, 'open': open_position,
        'confirm': confirm_position, 'close': close_position,
        'pivot': pivot_position,
        'portfolio': show_portfolio, 'cash': update_cash,
        'fill': fill_outcomes, 'analyze': analyze_predictions,
        'list': list_predictions, 'export': export_predictions,
        'watchlist-add': watchlist_add, 'watchlist-remove': watchlist_remove,
        'watchlist': watchlist_list,
    }
    fn = cmds.get(args.command)
    if fn:
        fn(args)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
