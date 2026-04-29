# Live Trading System — Deviations Log (main branch)

This file tracks methodology changes and important findings affecting
the live trading pipeline on `main`. Detailed v11-research-branch
tracking lives on `refactor/v11-stochastic`; only main-relevant
deviations are recorded here.

---

## Deviations from Plan

> Anything that diverges from the v9 baseline must be logged here with
> date + reason. Reviewer-relevant: this is the audit trail for
> "did you change methodology mid-implementation?".

### 2026-04-27 — Cross-Source Convergence (Step 1.8c): new diagnostic, lib refactor

A new Step 1 sub-section `convergence_check.py` was added to surface
cross-source disagreement on fwd-5d green-rate estimates. Three
independent conditional types are now compared:

  1. Indicator Context strongest-axis (RSI/BB/DistHigh — narrow per-stock)
  2. Pattern Timeline Mode 1 (disjoint return-bucket)
  3. Pattern Timeline Mode 2 (analog window match: corr + RSI + ATR-regime)

Output is **descriptive, not capping**. The LLM must cite the spread
and reading explicitly when synthesising Bull/Bear in Step 2/3 — no
automatic confidence penalty. HIGH SPREAD threshold = 20pp, MODERATE
= 10-20pp, TIGHT = <10pp.

**Lib refactor (sample-base parity):** Inline green-rate logic from
`indicator_context.py`, `pattern_timeline.py`, `day_pattern.py` was
canonicalised in `lib/conditional_stats.py`. The disjoint return-bucket
logic from `pattern_timeline.py` is now canonical; `day_pattern.py`
previously used overlapping bands (>= +3 was a subset of >= +1) — this
shifts numbers slightly at bucket edges (e.g. NVDA `>= +3%` n went
75→76 on 2026-04-27). Both `indicator_context.py` and
`convergence_check.py` now share the same `prepare_indicator_history`
sample base, so the strongest-axis green-rate cited by Convergence is
**identical** to the one Rating-1 uses.

**Two follow-up notes documented for future work, not addressed today:**

1. **Strongest-axis tie-breaking.** ENR.DE 2026-04-27 showed the RSI
   axis at adjust=+2.59% and BB at adjust=+2.59% — an effective tie
   resolved by floating-point noise on the 3rd decimal. Currently
   `max(...)` is order-dependent in Python and produces different
   strongest-axis selection across runs when adjusts are near-equal.
   Future: add tie-breaking rule (e.g. "if |adjust|-difference < 0.10pp
   among multiple axes, prefer RSI > BB > DistHigh"), document the
   choice. Not a hot bug; in NVDA/MU the strongest is well-separated
   so live decisions are unaffected. Action item, not blocker.

2. **THIN Mode 2 reading convention.** Mode 2 SOLID/WEAK/THIN tagging
   uses the standard 30/15/threshold from `conditional_stats.py`, but
   the entry threshold for Mode 2 is `min_analogs=10`. Therefore Mode 2
   can be "available" (n=10..14) but tagged THIN. The convention used:
   THIN Mode 2 is shown as a fully valid third source in the table,
   but the Reading line emits a directive — *"Mode 2 n=X THIN — analog
   matching available but sample below robustness threshold (THIN<15).
   Treat as directional hint; weight SOLID sources higher in synthesis."*
   This keeps `min_analogs` (entry gate) and SOLID/WEAK/THIN (reliability
   layer) as separate concerns — consistent with the per-stock band tagging.



Tag 11 bucket EV analysis on Posterior B (P(Trade-Win | RSI-band,
BB-pos, DistHigh)) triggered locked falsification rule (a) on both
directions: no Train-bucket has EV-CI lower bound > 0 under the locked
stop_pct=0.015 / limit_pct=0.030 outcome definition.

Key numbers: LONG population 98.9% in B1+B2 (predictions < 0.50),
Spearman rho=0.79 p=0.11 (right-sign ordinal trend, not significant).
SHORT three populated buckets all EV-CI strictly negative, Spearman
rho=-0.63 p=0.37 (anti-correlated trend, sample-up-drift confound).

Decision: v11 Posterior-B is NOT integrated into Step 3 confidence-
scoring. Live pipeline remains v9 with Wavelet patch (2026-04-27) and
trade-horizon documentation update (2026-04-28). The
`refactor/v11-stochastic` branch is preserved as scientific artifact
for the Aug-paper but is not merged.

Side-finding (separate from Posterior B falsification): Tag 8
augmentation showed that underlying-stops below 1.5% on US-equities
sit structurally inside the typical overnight-gap envelope (POOLED-17
P75 = 1.43%, strong asset-class heterogeneity: futures P75 0.86%,
indices 0.64%, US-equities 1.38%, EU-equities 1.02%, post-2021-listings
2.35%). Operative implication for live trading not codified — the
existing v10 chart-based two-stage exit remains unchanged. Re-evaluate
after 2-4 weeks of live observation if gap-stop events accumulate.

### 2026-04-28 — Trade-horizon documentation update

Empirical observation 2026-04-28: in v10 production, trades almost never
reached the full 5-day horizon — either take-profit limit or stop-loss
triggered earlier. Median observed hold time was 1-3 trading days. The
Step-1-3 prompts previously documented "1-5 days only" as the trade
horizon. Updated to "1-3 days primary, up to 5d if structurally
justified" to reflect operational reality. The underlying scripts
(pattern_timeline.py, earnings_pattern.py) continue to report Day+1 to
Day+5 windows; the change is in how the LLM consumes those values for
the final decision — Day+1 to Day+3 is the primary signal, Day+4 to
Day+5 is secondary.

### 2026-04-27 — Wavelet denoising disabled in collect_data.py

`lib/wavelet_utils.wavelet_denoise()` was identified as non-causal:
`pywt.wavedec` operates over the full signal, the universal threshold
sigma is a global statistic over the full detail-coefficient series,
and cycle-spinning rolls the array end-to-end. Indicator values
computed via `denoise_ohlcv()` therefore mixed information across the
full available history, including post-anchor data.

Operative impact (measured on 17-symbol watchlist, 2y, 30 anchors per
symbol):
  BB regime flip rate (above/upper/middle/lower/below) : median 87%
  RSI 5-pt band flip rate (today_rsi ± 5)              : median 100%
  DistHigh regime flip rate                            : median 20%

End-to-end v10 decision drift on the full 17-symbol watchlist
(distribution, not central-tendency, because the aggregate is bimodal):
  cluster A (academic, <10%) :  6 symbols (CEG, APLD, GC=F, IREN, MU, VST)
  cluster B (bounded, 10-30%):  7 symbols (ENR.DE, ^GDAXI, NVDA, SI=F,
                                            QBTS, SAP.DE, ASTS)
  cluster C (operational, ≥30%): 4 symbols (ARM, ASML, GOOGL, AAPL)

Patch applied 2026-04-27: `HAS_WAVELET = False` in
`scripts/collect_data.py` (commit `0a04d06`). Future analyses no longer
call `denoise_ohlcv()`; the indicator pipeline operates on raw Close
prices.

Open trades at patch time:
  ENR.DE #131: closed 2026-04-27 (stop hit, manual re-stop at same level;
                                  closure independent of patch decision).
  AMD    #130: kept open under original entry conditions; manual
               monitoring; no v11 / patched-v10 re-analysis until exit
               (memory entry `project_amd_130_no_reanalyze.md`).

### 2026-04-28 — Open methodological gap (logged for v11.2 follow-up)

The Pre-Analysis pipeline (Step 1 indicator_context, reversion_guard,
pattern_timeline, earnings_pattern, pre-open check, V-Vetos, W-Warnings)
is implemented in production but was NOT applied during the v11
walk-forward calibration on the research branch. Posterior B was
calibrated on every anchor day, not on anchor days that would have
produced a signal under the live pipeline. A deterministic
pipeline-shadow simulation (running the non-LLM filters on each
historical anchor) is an Aug-paper follow-up. Estimated 2-3 days
engineering when prioritised. Not blocking live trading on `main`.

---

## Cross-references

- v11 research-branch detailed tracking: `refactor/v11-stochastic` -> `plan.md`
- v11.1 trade-path simulator spec: `paper/v11_1_TRADE_PATH_SPEC.md` (on v11 branch)
- Live rules: `RULES.md`
- Live pipeline entry: `prompts/00_master.md`
