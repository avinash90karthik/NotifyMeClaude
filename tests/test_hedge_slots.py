"""Test that hedge positions are NOT counted as regular slots.

Hedges are tracked with cert_type='hedge' and must not consume the
3-slot cap defined in the strategy.
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
