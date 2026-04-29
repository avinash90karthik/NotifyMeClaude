# Anekdoten-Audit (open)

Hard rules in this codebase that are currently justified by single
incidents rather than aggregated data. Tracked here for transparency
and scheduled re-evaluation.

The Rule 28 demotion (2026-04-29) is the template: an existing rule
with a known confound and a small sample (n=12) was demoted to
Pending with a locked decision schema and a tracking trigger.

Anecdote-rules with n=1 don't have a confound problem; they have an
**evidence-quality problem**. They are NOT auto-demoted to Pending.
They are retained with the evidence base disclosed (see
`strategy_v9.md` § 10 for the Rule 27 template) until the tracking
trigger fires.

## Audit table

| Rule | Anekdote | Source File(s) | Falsification trigger | Tracking infrastructure |
|---|---|---|---|---|
| Rule 27 — Re-Entry Cooldown | n=1 (AMD #130, 2026-04-27) | `strategy_v9.md` § 10, `prompts/03_judge_risk.md`, `CLAUDE.md` | Operational discipline (24h cooldown). No falsification trigger — the rule is no longer outcome-evaluated. | **Retired** 2026-04-29 (rule simplified to flat 24h cooldown; pipeline is the re-eval criterion — no separate tracking needed) |
| Rule 21 — Earnings is never a skip reason | HIMS / HOOD / RKLB on 2026-04-20 | `strategy_v9.md` § Why Rule 21, `prompts/01_data_collection.md` § 1.8b | Trade-Window-pattern green-rate < 50% across n≥30 earnings-window trades | **Active** (implicit): each `earnings_pattern.py` run is logged in DB; aggregation script TBD |
| Rule 18 — Entry = Center, never Close | HDD.DE #82 | `prompts/03_judge_risk.md` § Optimal Entry | Center-fill performance not better than Close-fill at n≥30 entries | **Tracking infrastructure required before re-evaluation** — DB has no `entry_method` field; deferred |
| Rule 5 — KO computed, never estimated | Unspecified "post-mortem" reference | `prompts/03_judge_risk.md` § KO Level | Estimated-KO outcomes not worse than computed-KO at n≥20 | **Tracking infrastructure required before re-evaluation** — DB has no `ko_method` field; deferred |
| Geopolitical Triggers Mandatory | Iran-ceasefire-expiry 2026-04-21 | `prompts/01_data_collection.md` § 1.6 | Geopol-blind analyses don't underperform geopol-aware analyses at n≥30 | **Tracking infrastructure required before re-evaluation** — A/B comparison structurally hard, no isolated geopol-blind cohort exists; deferred |

## Re-evaluation discipline

Each rule's tracking trigger is the precondition for re-evaluation.
Without n at the trigger threshold, the rule stays hard and the
anecdote-justification is disclosed (see `strategy_v9.md` § 10
"Why Rule 27 — Evidence Base" for the disclosure template).

The Rule 27 entry has active tracking. The other four entries have
tracking infrastructure gaps explicitly noted. Closing those gaps
(adding `entry_method` / `ko_method` columns; designing a geopol A/B
cohort) is the precondition for any re-evaluation, and is deferred —
not hidden in the falsification-trigger column.

## Schedule

Re-pass scheduled for 2026-05-29 alongside the Rule 28 evaluation.

If any tracking trigger reaches its n threshold earlier, the rule is
processed out-of-band without waiting for the calendar date.
