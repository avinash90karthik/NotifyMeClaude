#!/usr/bin/env python3
"""v1.0 DB schema migration for predictions.db.

Adds the columns and CHECK-constraint relaxation that Step 4 v1.0 needs.
Idempotent — safe to run multiple times.

Changes:
  + entry_low REAL          (NULL allowed)
  + entry_high REAL         (NULL allowed)
  + target1 REAL            (NULL allowed)
  + target2 REAL            (NULL allowed)
  + ko REAL                 (NULL allowed; v1.0 wording — old "ko_level" stays for legacy)
  + cert_isin TEXT          (NULL allowed)
  + run_id TEXT             (NULL allowed; format SYMBOL_YYYYMMDD_HHMMSS)
  ~ direction CHECK relaxed to allow 'NO_TRADE'

Legacy columns kept (still readable by old code):
  entry_price, stop_price, target_price, ko_level

Usage:
  python3 scripts/ops/migrate_v1_0.py            # apply migration
  python3 scripts/ops/migrate_v1_0.py --dry-run  # show plan only

Backups: take one manually before running (the script does not back up).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO / 'memory' / 'predictions.db'

NEW_COLUMNS = [
    ('entry_low', 'REAL'),
    ('entry_high', 'REAL'),
    ('target1', 'REAL'),
    ('target2', 'REAL'),
    ('ko', 'REAL'),
    ('cert_isin', 'TEXT'),
    ('run_id', 'TEXT'),
]


def existing_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(predictions)").fetchall()
    return {r[1] for r in rows}


def current_check_allows_no_trade(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='predictions'"
    ).fetchone()
    if not row:
        return False
    sql = row[0] or ''
    return "'NO_TRADE'" in sql


def add_missing_columns(conn: sqlite3.Connection, dry_run: bool) -> list[str]:
    have = existing_columns(conn)
    plan = []
    for name, kind in NEW_COLUMNS:
        if name in have:
            continue
        stmt = f"ALTER TABLE predictions ADD COLUMN {name} {kind}"
        plan.append(stmt)
        if not dry_run:
            conn.execute(stmt)
    return plan


def relax_direction_check(conn: sqlite3.Connection, dry_run: bool) -> list[str]:
    """SQLite cannot ALTER a CHECK constraint in place — we rebuild the table.

    Steps:
      1. Create predictions_new with the relaxed CHECK
      2. Copy all rows from predictions
      3. Drop predictions
      4. Rename predictions_new to predictions
    """
    if current_check_allows_no_trade(conn):
        return []

    # Build the new CREATE TABLE by reading the current one and patching the
    # CHECK clause. Safer than re-listing every column manually because we may
    # have added v1.0 columns earlier in this migration run.
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='predictions'"
    ).fetchone()
    old_sql = row[0]

    # Determine if our ALTERs from this run are committed yet — we need the
    # *intended* schema (post-ALTER) here. PRAGMA table_info reflects ALTERs
    # immediately, so we rebuild from that.
    cols = conn.execute("PRAGMA table_info(predictions)").fetchall()
    col_defs = []
    for cid, name, kind, notnull, dflt, pk in cols:
        parts = [f'"{name}"', kind or '']
        if pk:
            parts.append('PRIMARY KEY AUTOINCREMENT')
        if notnull and not pk:
            parts.append('NOT NULL')
        if dflt is not None:
            # Expression defaults (functions, parens already-stripped) need
            # to be wrapped in parens for SQLite's CREATE TABLE syntax.
            # Literals (numbers, quoted strings) do not.
            d = str(dflt).strip()
            is_literal = (
                d.startswith("'") and d.endswith("'")
                or d.lstrip('-').replace('.', '', 1).isdigit()
                or d.upper() in {'NULL', 'TRUE', 'FALSE', 'CURRENT_TIMESTAMP'}
            )
            if is_literal:
                parts.append(f"DEFAULT {d}")
            else:
                parts.append(f"DEFAULT ({d})")
        if name == 'direction':
            parts.append("CHECK(direction IN ('LONG', 'SHORT', 'NO_TRADE'))")
        if name == 'confidence':
            parts.append('CHECK(confidence BETWEEN 0 AND 100)')
        if name == 'status':
            # status was NOT NULL DEFAULT 'analysis' in legacy; keep if so
            pass
        col_defs.append(' '.join(p for p in parts if p))

    new_sql = (
        'CREATE TABLE predictions_new (\n  '
        + ',\n  '.join(col_defs)
        + '\n)'
    )

    # Build column list for INSERT … SELECT (preserve order)
    col_names = [c[1] for c in cols]
    quoted = ', '.join(f'"{n}"' for n in col_names)

    plan = [
        new_sql,
        f'INSERT INTO predictions_new ({quoted}) SELECT {quoted} FROM predictions',
        'DROP TABLE predictions',
        'ALTER TABLE predictions_new RENAME TO predictions',
    ]
    if not dry_run:
        for stmt in plan:
            conn.execute(stmt)
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--db', default=str(DB_PATH))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f'DB not found: {db}', file=sys.stderr)
        return 1

    print(f'DB: {db}')
    print(f'Mode: {"DRY RUN" if args.dry_run else "APPLY"}\n')

    conn = sqlite3.connect(str(db))
    try:
        if not args.dry_run:
            conn.execute('BEGIN')

        col_plan = add_missing_columns(conn, args.dry_run)
        check_plan = relax_direction_check(conn, args.dry_run)

        all_plan = col_plan + check_plan
        if not all_plan:
            print('Schema already at v1.0 — nothing to do.')
        else:
            for stmt in all_plan:
                head = stmt.replace('\n', ' ')
                if len(head) > 100:
                    head = head[:97] + '...'
                print(f'  {head}')

        if not args.dry_run:
            conn.commit()
            print('\nMigration applied.')
        elif all_plan:
            print('\nDry run only — re-run without --dry-run to apply.')
    except Exception as e:
        if not args.dry_run:
            conn.rollback()
        print(f'ERROR: {e}', file=sys.stderr)
        return 2
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
