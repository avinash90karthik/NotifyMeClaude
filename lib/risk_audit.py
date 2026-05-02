"""Risk constants for v1.0.

Most of the legacy V/SV/W rule audit machinery is gone in v1.0 — risk
reasoning is the LLM's job in Step 2/3, on raw data. The only surviving
hard veto enforced in code is V5 (Max 3 Slots), checked from
preflight_check.py and prediction_db.py.

This module exists solely so the slot-cap constant has a stable import
path. Bumping the cap is one edit here; do NOT scatter the literal 3
across the codebase.
"""

MAX_OPEN_TURBOS = 3
