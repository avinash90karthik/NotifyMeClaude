#!/usr/bin/env python3
"""One-time migration: predictions table NOT NULL → NULL on entry/stop/target.

Required by Rule 27 NO-TRADE Output Clamp (clarification 2026-04-29). When a
re-eval is clamped under same-symbol cooldown, the analysis is recorded with
NULL trade-plan fields to signal "cooldown-clamped, not actioned" semantically
(vs. sentinel values, which would corrupt downstream aggregations).

Affected columns:
    entry_price   REAL NOT NULL  →  REAL
    stop_price    REAL NOT NULL  →  REAL
    target_price  REAL NOT NULL  →  REAL

ko_level was already nullable; status remains NOT NULL with default.

SQLite does not support `ALTER COLUMN ... DROP NOT NULL` directly. This
script performs the standard table-swap migration:

    1. Backup predictions.db → predictions.db.bak-rule27-YYYYMMDD-HHMM
    2. CREATE TABLE predictions_new with the relaxed schema (preserving
       all other columns + check constraints + defaults)
    3. INSERT INTO predictions_new SELECT ... FROM predictions
    4. DROP TABLE predictions
    5. ALTER TABLE predictions_new RENAME TO predictions
    6. Verify row count + sample integrity
    7. Commit OR rollback

Idempotent: if the schema is already migrated, the script reports
"already migrated" and exits 0 without touching the DB.

Usage:
    python3 scripts/migrate_rule27_nullable.py            # run migration
    python3 scripts/migrate_rule27_nullable.py --dry-run  # check only, no mutation
    python3 scripts/migrate_rule27_nullable.py --verify   # show schema state, exit
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, 'memory', 'predictions.db')

TARGET_COLS = ('entry_price', 'stop_price', 'target_price')


def get_schema_state(conn):
    """Return dict {col_name: notnull_flag} for predictions table."""
    rows = conn.execute('PRAGMA table_info(predictions)').fetchall()
    return {row[1]: row[3] for row in rows}  # name → notnull


def needs_migration(schema):
    """True if any of the three target columns still has NOT NULL set."""
    return any(schema.get(col, 0) == 1 for col in TARGET_COLS)


def backup_db():
    """Copy predictions.db to a timestamped backup. Returns backup path."""
    if not os.path.exists(DB_FILE):
        sys.exit(f'❌ DB file not found: {DB_FILE}')
    ts = datetime.now().strftime('%Y%m%d-%H%M')
    backup_path = f'{DB_FILE}.bak-rule27-{ts}'
    shutil.copy2(DB_FILE, backup_path)
    print(f'✅ Backup created: {backup_path}')
    return backup_path


def get_create_sql(conn):
    """Fetch the original CREATE TABLE statement for predictions."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='predictions'"
    ).fetchone()
    if not row:
        sys.exit('❌ predictions table not found in DB')
    return row[0]


def build_new_create_sql(original_sql):
    """Rewrite the CREATE TABLE statement to drop NOT NULL on three columns.

    Handles the canonical form used in scripts/prediction_db.py:
        entry_price REAL NOT NULL,
        stop_price REAL NOT NULL,
        target_price REAL NOT NULL,

    Renames the table to predictions_new in the new statement.
    """
    new_sql = original_sql

    # Replace table name first
    new_sql = new_sql.replace(
        'CREATE TABLE predictions ',
        'CREATE TABLE predictions_new ',
        1,
    )
    # SQLite stores it without IF NOT EXISTS in sqlite_master, but handle both
    new_sql = new_sql.replace(
        'CREATE TABLE IF NOT EXISTS predictions ',
        'CREATE TABLE predictions_new ',
        1,
    )

    # Strip NOT NULL from the three target columns. Match conservatively to
    # avoid clobbering other columns that legitimately stay NOT NULL.
    replacements = [
        ('entry_price REAL NOT NULL', 'entry_price REAL'),
        ('stop_price REAL NOT NULL', 'stop_price REAL'),
        ('target_price REAL NOT NULL', 'target_price REAL'),
    ]
    for old, new in replacements:
        if old not in new_sql:
            sys.exit(
                f'❌ Could not find expected column definition: "{old}".\n'
                f'   The schema in your DB may differ from scripts/prediction_db.py.\n'
                f'   Inspect with: sqlite3 {DB_FILE} ".schema predictions"\n'
                f'   Then either edit this script or do a manual migration.'
            )
        new_sql = new_sql.replace(old, new, 1)

    return new_sql


def run_migration(dry_run=False):
    """Execute the table-swap migration. Returns True if work was done."""
    if not os.path.exists(DB_FILE):
        sys.exit(f'❌ DB file not found: {DB_FILE}')

    conn = sqlite3.connect(DB_FILE)
    schema = get_schema_state(conn)

    if not needs_migration(schema):
        print('✅ Schema already migrated. NOT NULL flags on '
              f'{TARGET_COLS} are already cleared. No action taken.')
        conn.close()
        return False

    print('Schema state BEFORE migration:')
    for col in TARGET_COLS:
        flag = schema.get(col, 'MISSING')
        print(f'  {col}: notnull={flag}')

    original_sql = get_create_sql(conn)
    new_sql = build_new_create_sql(original_sql)

    print('\nMigration plan:')
    print('  1. Backup predictions.db → predictions.db.bak-rule27-YYYYMMDD-HHMM')
    print('  2. CREATE TABLE predictions_new (relaxed schema)')
    print('  3. INSERT INTO predictions_new SELECT * FROM predictions')
    print('  4. DROP TABLE predictions')
    print('  5. ALTER TABLE predictions_new RENAME TO predictions')
    print('  6. Verify row count + commit')

    if dry_run:
        print('\n[DRY-RUN] Would execute the above. Exiting without changes.')
        print('\nNew CREATE TABLE statement that would be used:')
        print(new_sql)
        conn.close()
        return False

    # Real run
    conn.close()  # close before backup to ensure no open handle interferes
    backup_path = backup_db()

    conn = sqlite3.connect(DB_FILE)
    conn.execute('PRAGMA foreign_keys = OFF')  # temporarily for the swap

    try:
        # Pre-flight row count
        n_before = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
        print(f'\nRow count before migration: {n_before}')

        conn.execute('BEGIN TRANSACTION')
        conn.execute(new_sql)
        conn.execute('INSERT INTO predictions_new SELECT * FROM predictions')
        conn.execute('DROP TABLE predictions')
        conn.execute('ALTER TABLE predictions_new RENAME TO predictions')

        # Post-flight check
        n_after = conn.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
        if n_after != n_before:
            conn.rollback()
            sys.exit(
                f'❌ Row count mismatch: before={n_before}, after={n_after}.\n'
                f'   Transaction rolled back. DB unchanged.\n'
                f'   Backup retained at: {backup_path}'
            )

        # Verify the schema is now relaxed
        new_schema = get_schema_state(conn)
        if needs_migration(new_schema):
            conn.rollback()
            sys.exit(
                '❌ Migration did not relax the NOT NULL constraints. '
                'Transaction rolled back. Backup retained.'
            )

        conn.commit()
        print(f'\n✅ Migration committed. Row count preserved: {n_after}')
        print('\nSchema state AFTER migration:')
        for col in TARGET_COLS:
            flag = new_schema.get(col, 'MISSING')
            print(f'  {col}: notnull={flag}')

        # Re-enable FK
        conn.execute('PRAGMA foreign_keys = ON')

    except Exception as e:
        conn.rollback()
        print(f'❌ Migration failed: {e}', file=sys.stderr)
        print(f'   Transaction rolled back. DB unchanged.', file=sys.stderr)
        print(f'   Backup retained at: {backup_path}', file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f'\nBackup retained at: {backup_path}')
    print('Keep the backup at least 7 days before deleting.')
    return True


def verify_only():
    """Print current schema state, exit."""
    if not os.path.exists(DB_FILE):
        sys.exit(f'❌ DB file not found: {DB_FILE}')
    conn = sqlite3.connect(DB_FILE)
    schema = get_schema_state(conn)
    conn.close()

    print('Current schema state:')
    for col in TARGET_COLS:
        flag = schema.get(col, 'MISSING')
        marker = '⚠️ NEEDS MIGRATION' if flag == 1 else '✅ relaxed'
        print(f'  {col}: notnull={flag}  {marker}')

    if needs_migration(schema):
        print('\nRun without --verify to migrate.')
        sys.exit(0)
    else:
        print('\nNo migration needed.')
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Rule 27 schema migration: drop NOT NULL on '
                    'entry_price/stop_price/target_price'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show migration plan without mutating DB',
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Print current schema state and exit',
    )
    args = parser.parse_args()

    if args.verify:
        verify_only()
    run_migration(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
