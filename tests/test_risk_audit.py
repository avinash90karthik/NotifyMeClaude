"""Test risk_audit.py — especially V5 drawdown veto.

The bug: risk_audit queried non-existent column cert_entry_price,
so invested capital was always 0 and V5 drawdown veto never triggered.
"""

import os
import sqlite3
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a test predictions.db with known data."""
    db_path = str(tmp_path / 'predictions.db')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript('''
        CREATE TABLE predictions (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence INTEGER,
            entry_price REAL,
            stop_price REAL,
            target_price REAL,
            ko_level REAL,
            status TEXT DEFAULT 'analysis',
            shares INTEGER DEFAULT 0,
            cert_buyin REAL,
            cert_type TEXT DEFAULT 'turbo',
            invested_eur REAL DEFAULT 0,
            realized_pnl_eur REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT,
            shares_closed INTEGER DEFAULT 0,
            regime TEXT,
            atr_pct REAL,
            reason TEXT,
            trade_taken INTEGER DEFAULT 0,
            exit_eur REAL
        );

        CREATE TABLE close_events (
            id INTEGER PRIMARY KEY,
            prediction_id INTEGER,
            closed_at TEXT DEFAULT (datetime('now')),
            shares INTEGER,
            cert_exit_price REAL,
            pnl_eur REAL,
            reason TEXT
        );

        CREATE TABLE portfolio_state (
            key TEXT PRIMARY KEY,
            value REAL,
            updated_at TEXT DEFAULT (datetime('now'))
        );
    ''')

    # Insert test data
    conn.execute("INSERT INTO portfolio_state (key, value) VALUES ('cash', 5000.0)")

    # Open position: 200 shares @ 3.00 = 600 EUR invested
    conn.execute("""INSERT INTO predictions
        (id, symbol, direction, confidence, entry_price, stop_price, target_price,
         status, shares, cert_buyin, invested_eur, cert_type)
        VALUES (1, 'ENR.DE', 'LONG', 68, 155.0, 148.0, 172.0,
                'open', 200, 3.00, 600.0, 'turbo')""")

    conn.commit()
    conn.close()

    # Patch DB_FILE in prediction_db and risk_audit
    monkeypatch.setattr('prediction_db.DB_FILE', db_path)

    return db_path


class TestRiskAuditV5:
    """Verify V5 drawdown veto uses invested_eur, not phantom column."""

    def test_portfolio_value_includes_invested(self, test_db):
        """Portfolio value must be cash + invested, not just cash."""
        from risk_audit import parse_portfolio_summary

        summary = parse_portfolio_summary()

        assert summary['cash'] == 5000.0
        assert summary['portfolio_value'] == 5600.0, \
            f"Portfolio should be cash(5000) + invested(600) = 5600, got {summary['portfolio_value']}"

    def test_v5_triggers_on_heavy_loss(self, test_db):
        """V5 must VETO when monthly drawdown > 20%."""
        # Add a big loss this month
        conn = sqlite3.connect(test_db)
        conn.execute("""INSERT INTO close_events
            (prediction_id, shares, cert_exit_price, pnl_eur, closed_at)
            VALUES (1, 100, 1.00, -1200.0, datetime('now'))""")
        conn.commit()
        conn.close()

        from risk_audit import parse_portfolio_summary, risk_audit

        summary = parse_portfolio_summary()
        # -1200 on 5600 portfolio = -21.4%
        assert summary['monthly_pnl_pct'] < -20, \
            f"Monthly P&L should be < -20%, got {summary['monthly_pnl_pct']:.1f}%"

        approved, vetoes, warnings = risk_audit(
            'ASTS', {'atr_pct': 4.0, 'regime': 'TRANSITIONAL'},
            portfolio_state=summary
        )
        assert not approved, "V5 should VETO the trade"
        assert any('V5' in v for v in vetoes), f"V5 veto missing from: {vetoes}"

    def test_v5_passes_on_small_loss(self, test_db):
        """V5 must PASS when monthly drawdown < 20%."""
        conn = sqlite3.connect(test_db)
        conn.execute("""INSERT INTO close_events
            (prediction_id, shares, cert_exit_price, pnl_eur, closed_at)
            VALUES (1, 50, 2.00, -200.0, datetime('now'))""")
        conn.commit()
        conn.close()

        from risk_audit import parse_portfolio_summary, risk_audit

        summary = parse_portfolio_summary()
        # -200 on 5600 = -3.6%
        assert summary['monthly_pnl_pct'] > -20

        approved, vetoes, warnings = risk_audit(
            'ASTS', {'atr_pct': 4.0, 'regime': 'TRANSITIONAL'},
            portfolio_state=summary
        )
        assert not any('V5' in v for v in vetoes), f"V5 should not veto: {vetoes}"

    def test_v3_slot_limit(self, test_db):
        """V3 must veto when 3 non-hedge positions are open."""
        conn = sqlite3.connect(test_db)
        # Add 2 more open positions (total 3)
        conn.execute("""INSERT INTO predictions
            (symbol, direction, confidence, entry_price, stop_price, target_price,
             status, shares, cert_buyin, invested_eur, cert_type)
            VALUES ('ASTS', 'LONG', 65, 90.0, 80.0, 110.0,
                    'open', 100, 5.00, 500.0, 'turbo')""")
        conn.execute("""INSERT INTO predictions
            (symbol, direction, confidence, entry_price, stop_price, target_price,
             status, shares, cert_buyin, invested_eur, cert_type)
            VALUES ('MU', 'LONG', 70, 100.0, 90.0, 120.0,
                    'open', 80, 4.00, 320.0, 'turbo')""")
        conn.commit()
        conn.close()

        from risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        approved, vetoes, warnings = risk_audit(
            'TSM', {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary
        )
        assert any('V3' in v for v in vetoes), f"V3 slot limit should veto: {vetoes}"
