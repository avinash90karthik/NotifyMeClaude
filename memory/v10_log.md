# v10 Decision Log

Tracks pending v10 components and their evaluation data. Robust v10 components
(Sizing flatten, Concentration tightening V3/V4/V6) are LIVE and not tracked
here — they are documented in `RULES.md` § Rule 20 and § V3/V4/V6.

## Pending Components

(None.)

## Closed v10 components (no longer tracked here)

- **Rule 20 v10** (Sizing flatten): live in `prompts/03_judge_risk.md` §
  Position Sizing.
- **V3 / V4 / V6** (Concentration tightening): live in `lib/risk_audit.py` and
  `prompts/03_judge_risk.md` § Risk Audit.
- **Rule 28** (Trader-Day Circuit-Breaker): dropped 2026-04-29. The April n=12
  evidence base could not separate Tilt vs. Market-confound vs. Selection-bias.
  Rule 27 (24h re-entry cooldown on the just-stopped symbol) covers the worst
  tilt sub-case and is retained as a Soft warning.
