"""Sync Silver Hawk DB position-state from Trade Republic via pytr.

Architecture (per design discussion 2026-05-03):
- DB is the audit log for analysis quality, NOT the source of truth for positions.
- TR (via pytr) is the position-truth.
- Auto-write only on TRIVIAL_MATCH (1 DB-open with cert_isin=X ↔ 1 TR-position with ISIN=X).
- All other classifications (DB_ORPHAN, TR_ORPHAN, DB_AMBIG, NULL_ISIN) print a report.
- DB_ORPHAN auto-closes with realized PnL derived from pytr sells if available;
  if no matching sells, realized=0 with a "verify manually" reason (Q2 a).

Usage:
    python3 scripts/ops/sync_from_pytr.py            # Auto-write trivial matches + report
    python3 scripts/ops/sync_from_pytr.py --dry-run  # Report only, no writes
    python3 scripts/ops/sync_from_pytr.py --quiet    # Pre-flight banner mode (1-line summary)
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_FILE = os.path.join(PROJECT_ROOT, 'memory', 'predictions.db')


# ─── pytr fetch ────────────────────────────────────────────────────────

@dataclass
class TRPosition:
    isin: str
    name: str
    shares: float
    avg_cost: float
    net_value: float

    @property
    def is_dust(self) -> bool:
        return self.net_value < 15.0  # under 15 EUR is splittersplitter / dust


@dataclass
class TRTransaction:
    date: str  # ISO
    type: str  # 'Buy' / 'Sell' / 'Removal' / 'Deposit' / 'Interest'
    value: float
    note: str
    isin: str
    shares: float


def fetch_pytr_portfolio() -> list[TRPosition]:
    """Run `pytr portfolio` and parse its stdout. Raises RuntimeError on pytr failure."""
    try:
        result = subprocess.run(
            ['pytr', 'portfolio'],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except FileNotFoundError:
        sys.exit('❌ pytr binary not found in PATH.')
    except subprocess.TimeoutExpired:
        sys.exit('❌ pytr portfolio timed out (30s).')

    if result.returncode != 0 or 'Traceback' in result.stderr:
        err_excerpt = (result.stderr or '').strip().splitlines()[-3:]
        raise RuntimeError(
            'pytr portfolio failed — likely session expired or rate-limited:\n  '
            + '\n  '.join(err_excerpt)
            + '\nFix: run `pytr login` interactively, then retry sync.'
        )

    out = result.stdout
    positions: list[TRPosition] = []
    for line in out.splitlines():
        if not line or line.startswith('Name') or line.startswith('Depot') or line.startswith('Cash') or line.startswith('Total'):
            continue
        m = re.match(
            r'^(.{1,25}?)\s+([A-Z]{2}[A-Z0-9]{9}\d)\s+([\d,\.]+)\s+\*\s+'
            r'([\d,\.]+)\s+=\s+([\d,\.]+)\s+->\s+([\d,\.]+)\s+([\d,\.]+)',
            line,
        )
        if not m:
            continue
        name = m.group(1).strip()
        isin = m.group(2)
        avg_cost = float(m.group(3).replace(',', '.'))
        shares = float(m.group(4).replace(',', '.'))
        net_value = float(m.group(6).replace(',', '.'))
        positions.append(TRPosition(
            isin=isin, name=name, shares=shares, avg_cost=avg_cost, net_value=net_value,
        ))
    return positions


def fetch_pytr_transactions(days: int = 30) -> list[TRTransaction]:
    """Run `pytr export_transactions` and parse the resulting CSV."""
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, 'tx.csv')
        try:
            subprocess.run(
                ['pytr', 'export_transactions',
                 '--last_days', str(days),
                 '--export-format', 'csv',
                 '--no-decimal-localization',
                 out_path],
                capture_output=True, text=True, timeout=60, check=False,
            )
        except FileNotFoundError:
            sys.exit('❌ pytr binary not found in PATH.')

        if not os.path.exists(out_path):
            return []

        txs: list[TRTransaction] = []
        with open(out_path, newline='') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                try:
                    txs.append(TRTransaction(
                        date=row['Date'],
                        type=row['Type'],
                        value=float(row['Value'] or 0),
                        note=row['Note'] or '',
                        isin=row['ISIN'] or '',
                        shares=float(row['Shares'] or 0),
                    ))
                except (KeyError, ValueError):
                    continue
        return txs


# ─── Match classification ───────────────────────────────────────────────

@dataclass
class DBPosition:
    id: int
    symbol: str
    cert_isin: Optional[str]
    shares: int
    cert_buyin: Optional[float]


@dataclass
class MatchReport:
    trivial: list[tuple[DBPosition, TRPosition]] = field(default_factory=list)
    db_orphan: list[DBPosition] = field(default_factory=list)
    tr_orphan: list[TRPosition] = field(default_factory=list)
    db_ambig: list[tuple[str, list[DBPosition]]] = field(default_factory=list)
    null_isin: list[DBPosition] = field(default_factory=list)


def classify(db_open: list[DBPosition], tr_positions: list[TRPosition]) -> MatchReport:
    rpt = MatchReport()
    by_isin: dict[str, list[DBPosition]] = {}
    for p in db_open:
        if not p.cert_isin:
            rpt.null_isin.append(p)
            continue
        by_isin.setdefault(p.cert_isin, []).append(p)

    tr_by_isin = {p.isin: p for p in tr_positions if not p.is_dust}
    seen_tr_isins: set[str] = set()

    for isin, db_list in by_isin.items():
        if len(db_list) > 1:
            rpt.db_ambig.append((isin, db_list))
            continue
        db_p = db_list[0]
        tr_p = tr_by_isin.get(isin)
        if tr_p is None:
            rpt.db_orphan.append(db_p)
        else:
            rpt.trivial.append((db_p, tr_p))
            seen_tr_isins.add(isin)

    for isin, tr_p in tr_by_isin.items():
        if isin not in seen_tr_isins:
            rpt.tr_orphan.append(tr_p)

    return rpt


# ─── DB writes ─────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_db_open() -> list[DBPosition]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, symbol, cert_isin, shares, cert_buyin FROM predictions WHERE status='open'"
    ).fetchall()
    conn.close()
    return [
        DBPosition(id=r['id'], symbol=r['symbol'], cert_isin=r['cert_isin'],
                   shares=r['shares'] or 0, cert_buyin=r['cert_buyin'])
        for r in rows
    ]


def apply_trivial_match(db_p: DBPosition, tr_p: TRPosition) -> Optional[str]:
    """Update DB shares + cert_buyin to match TR. Return change description or None if no-op.

    TR is truth for net-position state. shares_closed is reset to 0 because the
    TR `shares` value is already net of any partial sells — keeping a non-zero
    shares_closed would double-count and produce a wrong "shares remaining" display.
    """
    target_shares = int(round(tr_p.shares))
    target_buyin = round(tr_p.avg_cost, 4)

    if db_p.shares == target_shares and abs((db_p.cert_buyin or 0) - target_buyin) < 0.001:
        return None

    conn = get_db()
    conn.execute(
        "UPDATE predictions SET shares=?, cert_buyin=?, shares_closed=0 WHERE id=?",
        (target_shares, target_buyin, db_p.id),
    )
    conn.commit()
    conn.close()
    return (
        f'#{db_p.id} {db_p.symbol}: '
        f'{db_p.shares} → {target_shares} Stk, '
        f'avg {db_p.cert_buyin or 0:.4f} → {target_buyin:.4f} EUR'
    )


def apply_db_orphan_close(db_p: DBPosition, txs: list[TRTransaction]) -> str:
    """Auto-close a DB-orphan with realized PnL from matching pytr sells.
    Q2 (a): if no matching sell, realized=0 with verify-manually reason."""
    matching_sells = [
        t for t in txs
        if t.isin == db_p.cert_isin and t.type == 'Sell'
    ]

    if matching_sells and db_p.cert_buyin is not None:
        total_sell_value = sum(t.value for t in matching_sells)
        total_sell_shares = sum(t.shares for t in matching_sells)
        if total_sell_shares > 0:
            avg_sell_price = total_sell_value / total_sell_shares
            realized = round((avg_sell_price - db_p.cert_buyin) * db_p.shares, 2)
            reason = (
                f'auto-sync: closed via pytr (avg sell {avg_sell_price:.4f} EUR over '
                f'{len(matching_sells)} tx, {int(total_sell_shares)} shares matched)'
            )
        else:
            realized = 0.0
            reason = 'auto-sync: closed (matching sells found but shares=0)'
    else:
        realized = 0.0
        reason = 'auto-sync: closed (no matching sell in pytr — verify manually)'

    conn = get_db()
    conn.execute(
        "UPDATE predictions SET status='closed', closed_at=datetime('now'), "
        "shares_closed=?, realized_pnl_eur=?, trade_notes=? WHERE id=?",
        (db_p.shares, realized, reason, db_p.id),
    )
    conn.commit()
    conn.close()
    return f'#{db_p.id} {db_p.symbol}: closed, realized {realized:+.2f} EUR ({reason})'


# ─── Reporting ─────────────────────────────────────────────────────────

def render_report(rpt: MatchReport, writes: list[str], dry_run: bool, quiet: bool) -> int:
    drift_count = (
        len(writes)
        + len(rpt.tr_orphan)
        + len(rpt.db_ambig)
        + len(rpt.null_isin)
    )

    if quiet:
        if drift_count == 0:
            print('SYNC: clean (no drift)')
        else:
            mode = 'reported' if dry_run else 'applied'
            parts = []
            if writes:
                parts.append(f'{len(writes)} {mode}')
            if rpt.tr_orphan:
                parts.append(f'{len(rpt.tr_orphan)} TR-only')
            if rpt.db_ambig:
                parts.append(f'{len(rpt.db_ambig)} ambig')
            if rpt.null_isin:
                parts.append(f'{len(rpt.null_isin)} no-ISIN')
            print(f'SYNC: drift detected — {", ".join(parts)}')
        return drift_count

    print('=' * 60)
    print('  SYNC FROM PYTR' + ('  (DRY-RUN)' if dry_run else ''))
    print('=' * 60)

    if writes:
        print(f'\n✅ TRIVIAL MATCHES ({len(writes)} {"would update" if dry_run else "updated"}):')
        for w in writes:
            print(f'  {w}')

    if rpt.tr_orphan:
        print(f'\n⚠️  TR_ORPHAN ({len(rpt.tr_orphan)}) — TR has position, DB has no open record:')
        for tr in rpt.tr_orphan:
            print(f'  {tr.isin} {tr.name}: {tr.shares:.0f} Stk @ {tr.avg_cost:.4f} EUR '
                  f'(net {tr.net_value:.2f} EUR) — record missing in DB')

    if rpt.db_ambig:
        print(f'\n⚠️  DB_AMBIG ({len(rpt.db_ambig)}) — multiple DB rows share a cert_isin:')
        for isin, rows in rpt.db_ambig:
            print(f'  {isin}: {[r.id for r in rows]} — manual reconciliation required')

    if rpt.null_isin:
        print(f'\n⚠️  NULL_ISIN ({len(rpt.null_isin)}) — DB open without cert_isin (legacy):')
        for r in rpt.null_isin:
            print(f'  #{r.id} {r.symbol} {r.shares} Stk @ {r.cert_buyin or 0:.4f} EUR')

    if drift_count == 0:
        print('\n✅ DB and TR are in sync.')
    else:
        print(f'\nDrift summary: {drift_count} item(s).')

    print('=' * 60)
    return drift_count


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Sync DB position-state from Trade Republic via pytr')
    p.add_argument('--dry-run', action='store_true', help='Report only, no DB writes')
    p.add_argument('--quiet', action='store_true', help='1-line summary mode (for pre-flight)')
    p.add_argument('--tx-days', type=int, default=14, help='Lookback window for transactions (default 14d)')
    args = p.parse_args()

    db_open = fetch_db_open()
    try:
        tr_positions = fetch_pytr_portfolio()
    except RuntimeError as e:
        if args.quiet:
            print(f'SYNC: pytr unavailable — drift unknown')
            sys.exit(0)
        print(f'❌ {e}')
        sys.exit(2)
    rpt = classify(db_open, tr_positions)

    writes: list[str] = []
    if not args.dry_run:
        for db_p, tr_p in rpt.trivial:
            change = apply_trivial_match(db_p, tr_p)
            if change:
                writes.append(change)
        if rpt.db_orphan:
            txs = fetch_pytr_transactions(days=args.tx_days)
            for db_p in rpt.db_orphan:
                writes.append(apply_db_orphan_close(db_p, txs))
    else:
        for db_p, tr_p in rpt.trivial:
            target_shares = int(round(tr_p.shares))
            if db_p.shares != target_shares or abs((db_p.cert_buyin or 0) - tr_p.avg_cost) >= 0.001:
                writes.append(
                    f'#{db_p.id} {db_p.symbol}: would update '
                    f'{db_p.shares} → {target_shares} Stk, '
                    f'avg {db_p.cert_buyin or 0:.4f} → {tr_p.avg_cost:.4f}'
                )
        for db_p in rpt.db_orphan:
            writes.append(f'#{db_p.id} {db_p.symbol}: would auto-close (cert_isin={db_p.cert_isin})')

    drift = render_report(rpt, writes, args.dry_run, args.quiet)
    sys.exit(0 if drift == 0 else 0)  # never block, sync is informational


if __name__ == '__main__':
    main()
