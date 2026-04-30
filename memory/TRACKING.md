# Tracking Log — pending rules and gathered evidence for re-evaluation

Tracks rules whose status depends on data accumulating over time
(Pending rules, Soft Warnings under observation). Rules with confirmed
edge or operational discipline live in `RULES.md` and are not tracked
here.

## Pending Components

### day_pattern.py vs. pattern_timeline.py Mode 1 — subsumption claim

**Status:** unverified, both scripts currently kept in `prompts/01_data_collection.md § 1.8`.

**Claim to verify:** Does `pattern_timeline.py` Mode 1 (return-band conditional) functionally cover the streak-conditional row in `day_pattern.py` ("After X red days streak"), or is the streak-conditional a structurally different signal that must be retained?

**Hypothesis:** Streak is a *sequence* conditional (last N days' direction), Mode 1 is a *single-day* conditional (today's return band). They are not the same — the streak row should stay.

**Action:** Read both scripts, confirm hypothesis. If confirmed, leave both in § 1.8. If Mode 1 actually does subsume streak, drop `day_pattern.py` from § 1.8 with a one-line removal note here.

**Added:** 2026-04-30 (during 01_data_collection.md compression review).
