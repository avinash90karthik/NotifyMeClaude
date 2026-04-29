"""Test risk_audit.py — RULES.md alignment.

Verifies:
  - parse_portfolio_summary() returns cash + invested correctly
  - V5 slot veto fires at MAX_OPEN_TURBOS, not before
  - Soft Vetos surface in soft_vetoes (not vetoes), do NOT block approved
  - Hard Vetos block approved
"""

import os
import sqlite3
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

    conn.execute("INSERT INTO portfolio_state (key, value) VALUES ('cash', 5000.0)")

    # Open position: 200 shares @ 3.00 = 600 EUR invested
    conn.execute("""INSERT INTO predictions
        (id, symbol, direction, confidence, entry_price, stop_price, target_price,
         status, shares, cert_buyin, invested_eur, cert_type)
        VALUES (1, 'ENR.DE', 'LONG', 68, 155.0, 148.0, 172.0,
                'open', 200, 3.00, 600.0, 'turbo')""")

    conn.commit()
    conn.close()

    monkeypatch.setattr('scripts.ops.prediction_db.DB_FILE', db_path)

    return db_path


class TestPortfolioSummary:
    """Verify parse_portfolio_summary uses invested_eur correctly."""

    def test_portfolio_value_includes_invested(self, test_db):
        """Portfolio value must be cash + invested, not just cash."""
        from lib.risk_audit import parse_portfolio_summary

        summary = parse_portfolio_summary()

        assert summary['cash'] == 5000.0
        assert summary['portfolio_value'] == 5600.0, \
            f"Portfolio should be cash(5000) + invested(600) = 5600, got {summary['portfolio_value']}"


class TestV5SlotLimit:
    """RULES.md V5 — Maximum MAX_OPEN_TURBOS open turbo positions."""

    def test_v5_passes_below_limit(self, test_db):
        """V5 must NOT veto when open turbos < MAX_OPEN_TURBOS."""
        from lib.risk_audit import parse_portfolio_summary, risk_audit, MAX_OPEN_TURBOS

        # Fixture has 1 open turbo. Add up to MAX_OPEN_TURBOS - 1 total.
        conn = sqlite3.connect(test_db)
        for i in range(MAX_OPEN_TURBOS - 2):
            conn.execute(
                "INSERT INTO predictions "
                "(symbol, direction, confidence, entry_price, stop_price, target_price, "
                " status, shares, cert_buyin, invested_eur, cert_type) "
                "VALUES (?, 'LONG', 65, 100.0, 90.0, 110.0, 'open', 100, 5.0, 500.0, 'turbo')",
                (f'TEST{i}',)
            )
        conn.commit()
        conn.close()

        summary = parse_portfolio_summary()
        result = risk_audit(
            'TSM', {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert not any('V5' in v for v in result['vetoes']), \
            f"V5 should not veto below MAX_OPEN_TURBOS: {result['vetoes']}"

    def test_v5_vetoes_at_limit(self, test_db):
        """V5 must VETO when open turbos == MAX_OPEN_TURBOS."""
        from lib.risk_audit import parse_portfolio_summary, risk_audit, MAX_OPEN_TURBOS

        # Fixture has 1 open turbo. Add up to MAX_OPEN_TURBOS total.
        conn = sqlite3.connect(test_db)
        for i in range(MAX_OPEN_TURBOS - 1):
            conn.execute(
                "INSERT INTO predictions "
                "(symbol, direction, confidence, entry_price, stop_price, target_price, "
                " status, shares, cert_buyin, invested_eur, cert_type) "
                "VALUES (?, 'LONG', 65, 100.0, 90.0, 110.0, 'open', 100, 5.0, 500.0, 'turbo')",
                (f'FILL{i}',)
            )
        conn.commit()
        conn.close()

        summary = parse_portfolio_summary()
        result = risk_audit(
            'TSM', {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert not result['approved'], "V5 should block approved"
        assert any('V5' in v for v in result['vetoes']), \
            f"V5 slot limit should veto at {MAX_OPEN_TURBOS}: {result['vetoes']}"

    def test_v5_excludes_hedges(self, test_db):
        """V5 must NOT count cert_type='hedge' against the slot cap."""
        from lib.risk_audit import parse_portfolio_summary, risk_audit, MAX_OPEN_TURBOS

        # Fixture has 1 turbo. Fill the rest with hedges — no V5 should fire.
        conn = sqlite3.connect(test_db)
        for i in range(MAX_OPEN_TURBOS + 2):
            conn.execute(
                "INSERT INTO predictions "
                "(symbol, direction, confidence, entry_price, stop_price, target_price, "
                " status, shares, cert_buyin, invested_eur, cert_type) "
                "VALUES (?, 'SHORT', 65, 100.0, 110.0, 90.0, 'open', 100, 5.0, 500.0, 'hedge')",
                (f'HDG{i}',)
            )
        conn.commit()
        conn.close()

        summary = parse_portfolio_summary()
        result = risk_audit(
            'TSM', {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert not any('V5' in v for v in result['vetoes']), \
            f"Hedges should not consume V5 slots: {result['vetoes']}"


class TestV4ATR:
    """RULES.md V4 — ATR > 7% blocks hard."""

    def test_v4_vetoes_high_atr(self, test_db):
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        result = risk_audit(
            'WILD', {'atr_pct': 8.5, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert not result['approved']
        assert any('V4' in v for v in result['vetoes']), \
            f"V4 should fire on ATR>7%: {result['vetoes']}"

    def test_v4_passes_normal_atr(self, test_db):
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        result = risk_audit(
            'CALM', {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert not any('V4' in v for v in result['vetoes'])


class TestSoftVetoesDoNotBlock:
    """Soft Vetos surface in `soft_vetoes` and do NOT set approved=False.
    The Judge in the prompt evaluates and may override."""

    def test_sv1_choppy_does_not_block(self, test_db):
        """SV1 (CHOPPY + low score) lands in soft_vetoes, not vetoes."""
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        result = risk_audit(
            'TSM',
            {'atr_pct': 3.0, 'regime': 'CHOPPY',
             '_score_long': 30, '_score_short': 25},
            portfolio_state=summary, sector='Technology',
        )
        assert any('SV1' in sv for sv in result['soft_vetoes']), \
            f"SV1 should fire in soft_vetoes: {result}"
        assert not any('SV1' in v for v in result['vetoes']), \
            "SV1 must NOT appear in hard vetoes"
        assert result['approved'], \
            "Soft Veto alone must not block approved"

    def test_sv3_sector_concentration_does_not_block(self, test_db):
        """SV3 (sector >40%) lands in soft_vetoes, not vetoes."""
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()
        # Fixture has 1 ENR.DE turbo (sector resolved via yfinance — patch
        # on the position dict instead to avoid network).
        for p in summary['positions']:
            p['sector'] = 'Technology'

        result = risk_audit(
            'TSM',
            {'atr_pct': 3.0, 'regime': 'TRENDING'},
            portfolio_state=summary, sector='Technology',
        )
        assert any('SV3' in sv for sv in result['soft_vetoes']), \
            f"SV3 should fire when adding same-sector candidate: {result}"
        assert result['approved'], \
            "Soft Veto alone must not block approved"


class TestW10Earnings:
    """RULES.md W10 — Earnings ≤5d adds KO multiplier +0.5."""

    def test_w10_fires_within_5d(self, test_db):
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        result = risk_audit(
            'TSM',
            {'atr_pct': 3.0, 'regime': 'TRENDING', 'earnings_days_to': 3},
            portfolio_state=summary, sector='Technology',
        )
        assert any('W10' in w for w in result['warnings']), \
            f"W10 should fire on earnings_days_to=3: {result['warnings']}"

    def test_w10_silent_outside_5d(self, test_db):
        from lib.risk_audit import parse_portfolio_summary, risk_audit
        summary = parse_portfolio_summary()

        result = risk_audit(
            'TSM',
            {'atr_pct': 3.0, 'regime': 'TRENDING', 'earnings_days_to': 12},
            portfolio_state=summary, sector='Technology',
        )
        assert not any('W10' in w for w in result['warnings']), \
            f"W10 should be silent at earnings_days_to=12: {result['warnings']}"
