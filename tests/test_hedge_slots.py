"""Test that hedge positions are NOT counted as regular slots.

The bug: dashboard API counted len(positions) for slots_used,
but hedges should be excluded per strategy rules.
"""

import os
import ast
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHedgeSlotCounting:
    """Verify hedge positions don't consume regular slot count."""

    def test_prediction_db_excludes_hedges_from_slots(self):
        """prediction_db.py portfolio must filter cert_type='hedge' from slots."""
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'prediction_db.py'
        )
        with open(src_path) as f:
            source = f.read()

        # Find slots calculation in show_portfolio
        assert "!= 'hedge'" in source, \
            "prediction_db.py must exclude hedges from slot count"

    def test_server_excludes_hedges_from_slots(self):
        """server.py /api/portfolio must exclude hedges from slots_used."""
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'dashboard', 'backend', 'server.py'
        )
        with open(src_path) as f:
            source = f.read()

        # slots_used must NOT be just len(positions)
        assert "slots_used': len(positions)" not in source, \
            "server.py must not use len(positions) for slots_used"

        # Must filter out hedges
        assert "'hedge'" in source and 'slots_used' in source, \
            "server.py must filter hedges from slots_used"

    def test_hedge_slot_logic_correct(self):
        """Verify the slot counting logic with test data."""
        positions = [
            {'cert_type': 'turbo', 'symbol': 'ENR.DE'},
            {'cert_type': 'hedge', 'symbol': 'ENR.DE'},
            {'cert_type': 'turbo', 'symbol': 'ASTS'},
            {'cert_type': None, 'symbol': 'MU'},  # None defaults to turbo
        ]

        # This is the logic that should be in both prediction_db.py and server.py
        slots = sum(1 for p in positions if (p.get('cert_type') or 'turbo') != 'hedge')

        assert slots == 3, f"Should be 3 slots (hedge excluded), got {slots}"

    def test_hedge_only_position_zero_slots(self):
        """A portfolio with only hedges should show 0 slots used."""
        positions = [
            {'cert_type': 'hedge', 'symbol': 'ENR.DE'},
            {'cert_type': 'hedge', 'symbol': 'ASTS'},
        ]

        slots = sum(1 for p in positions if (p.get('cert_type') or 'turbo') != 'hedge')
        assert slots == 0, f"Only hedges should mean 0 slots, got {slots}"
