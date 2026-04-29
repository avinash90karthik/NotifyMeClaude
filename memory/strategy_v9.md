# Strategy v9 — Reference Document

> Single source of truth for **strategy rationale** (the "why"). Hard rules
> themselves live in `prompts/`. This document is **not auto-loaded** by Claude;
> it is referenced from prompts when the rationale is needed (e.g. via
> `see strategy_v9.md § Why Rule 5`).

## 1. Pipeline Architecture

The trading system runs as a four-step pipeline preceded by a pre-flight
script. Each step has a dedicated prompt file under `prompts/`:

| Step | Prompt | Purpose |
|------|--------|---------|
| 0 | `preflight_check.py` | Date/market status + yfinance news + mandatory search queries |
| 1 | `prompts/01_data_collection.md` | Price, indicators, chart, news, macro, patterns, events |
| 2 | `prompts/02_investment_debate.md` | Bull vs Bear debate, 6-axis scorecard |
| 3 | `prompts/03_judge_risk.md` | Signal + confidence, KO, reversion guard, risk audit, stock trade plan |
| 4 | `prompts/04_summary_send.md` | Trading card, cert request, prediction DB record |

Scripts that drive each step:
- `collect_data.py` (Step 1.2)
- `price_action_check.py` (Step 1.4)
- `indicator_context.py` (Step 1.4 — sigmoid adjusts + STRONGEST AXIS aggregation)
- `day_pattern.py`, `pattern_timeline.py` (Step 1.8 / 1.8a)
- `earnings_pattern.py` (Step 1.8b — sigmoid adjust, earnings-specific n thresholds)
- `event_impact.py` (Step 1.9)
- `reversion_guard.py` (Step 2 + Step 3)
- `entry_calibration.py` (Step 3)
- `prediction_db.py record / open / confirm / close` (Step 4)

Portfolio state lives in `memory/predictions.db` and is the single source of
truth for positions, cash, slot count, and analysis history.

## 2. Strategy History v5 → v9

- **v5 (core).** Scout/Confirmation entry, Gate at 60% confidence, 80%/+20%
  exit, 3-slot cap, KO from max(ATR, chart), Time-Stops at 3d/5d.
- **v6 (Blind Re-Analysis).** When a cert hits −20%, re-run analysis without
  portfolio context. If blind verdict flips → close immediately. If neutral →
  halve position. If same direction → continue.
- **v7 (Direct Position Hedge + Pivot).** Replaces v5 index-hedging (which
  failed live: DAX-short −€27 in one day during ENR.DE drawdown). Uses a
  short-turbo on the **same** underlying as the long position, sized 50–65%
  of long exposure. Pivot rule: at LONG −40% AND SHORT in profit → close
  long, redeploy proceeds into short, treat as a normal turbo position with
  +15% recovery exits. See § 3 + § 4.
- **v8 (Exits + Overnight Rule).** 80% out at +20% **immediately** (replaces
  v5 66%-rule), rest max +30%. Trump events / known overnight catalysts →
  close everything before the event. Triggered by a +€500 → −€300 overnight
  flip on a Trump speech.
- **v9 (Sigmoid + Aggregation + Scout-Inversion + Oversold-Bonus).** Confidence
  adjusts switched from bucketed `>65% → +3%` to a continuous sigmoid
  `5 × tanh((g − 0.5) × 4) × sample_weight`. Indicator-context aggregation
  uses the STRONGEST single axis (max |adjust|) instead of naive sum across
  RSI/BB/DistHigh, because those axes are positively correlated for trend
  stocks. Scorecard caps loosened (Reversion-Edge LONG max 8/10, Price-Action
  cap fires only on confirmed stabilization). Differential penalty smoothed
  to `1 − 0.15 × exp(−Diff/4)` — no cliff at Diff = 10. Two new explicit
  rules: Rule 19 Extreme-Oversold-Bonus and Rule 20 Scout-Inversion.

v5/v6/v7/v8 mechanics are still active where v9 did not replace them
(scout/confirmation, slot cap, KO methodology, hedge, pivot, overnight
rule, time-stops). v9 is **cumulative**, not a clean rewrite.

## 3. Hedge Logic (Direct Position Hedge)

Trigger and conditions (all four must hold):

1. The cert is at **−20% from entry** — act immediately, do not wait for
   −25% / −30%.
2. v6 Blind Re-Analysis was performed and the **blind verdict matches the
   original direction** (the thesis is still intact).
3. Momentum is **clearly against** the position — at least 2 of 3:
   - MACD bearish and expanding
   - SMA50 broken
   - Macro headwind (geopolitics, risk-off)
4. The catalyst is **external** (macro), not stock-specific.

Action:

- Open a **short turbo on the same underlying**, never an index, never a
  sector ETF. This eliminates basis risk that v5 index-hedging suffered from.
- Size: lottery-style, `max = smallest open long position`. Goal is to
  hedge 50–65% of long exposure. Never hedge 100% — at 100% the hedge is
  effectively a closed position with extra cost.
- Short-turbo KO must be **above the next resistance**, minimum 10% above
  current price. Wider KO = lower leverage = safer.
- DB: `cert_type = 'hedge'` — does NOT count as a normal slot, tracked
  separately in win-rate.

Hedge exits — three triggers + one time-stop:

1. **Momentum turns** (green day + RSI back above 35–40, MACD histogram
   flips positive) → close short, let long run.
2. **Catalyst dissolves** (de-escalation, macro shift) → close short
   immediately, snap-back is dangerous.
3. **Long stop hit** → close both, net loss is meaningfully smaller than
   without the hedge.
4. **Time-stop: max 5 days hedge open**, no exceptions. Day 5 → close or
   pivot.

## 4. Pivot Logic (Hedge → Direction Flip)

Trigger: **LONG cert at −40% AND SHORT in profit.**

Action:

1. Close the long immediately, accept the loss.
2. Redeploy the proceeds into the short (add to position).
3. From this point the short is a **normal directional position**, not a
   hedge. `cert_type` flips from `'hedge'` to `'turbo'` in the DB. It now
   counts as a normal slot.
4. Recovery exits apply: 50% out at +15% (more conservative than the
   standard +20%), rest with trailing stop to break-even.

Why −40% and not earlier: at −20% the hedge has just opened; at −30% the
counter-momentum still needs to confirm; at −40% the long is too far gone
for a realistic recovery and the short has proven directional momentum.

## 5. Why Each Hard Rule Exists

These are the post-mortems that justify the hard rules currently embedded
in the prompts. The prompts state the rule; this section explains why.

### § Why Rule 5 — KO is computed, never estimated

Estimated KO levels invariably end up "round-number friendly" (e.g. €150
because it looks clean) rather than data-derived. Round-number stops cluster
with retail orders → liquidity sweeps that knock out positions for no
fundamental reason. ATR-based + chart-based gives two independent anchors;
taking the further-out value provides a buffer against single-method failure.
If both methods fail to compute, the trade is invalid — not because we lack
a number, but because we lack the **information** the calculation requires.

### § Why Rule 6 — SHORT scorecard is mandatory

Multiple historical analyses showed asymmetric scoring: when the bull thesis
was emotionally compelling, the scorecard was filled out for LONG only and
the SHORT side was implicitly dismissed. Forcing both sides through the same
6-axis scoring catches the cases where SHORT actually has the higher total —
which then triggers the mirror test in Step 3. Without this rule, the system
silently develops a directional bias.

### § Why Rule 7 — EUR/USD is always live from yfinance

Past habit was to "approximate" FX with a recent value (e.g. "1.10") when
yfinance was slow. With cert position sizes in EUR and underlying prices in
USD, a 0.5% FX drift over a hold period becomes a 5–10× larger error in cert
P&L because of leverage. yfinance pulls live FX with every collect_data run;
hardcoded fallback FX values are forbidden because the consequence is
silently mis-sized positions.

### § Why Rule 8 — Position recommendations are in % of portfolio

Portfolio value moves continuously (P&L, deposits, withdrawals). A
recommendation in absolute EUR ages immediately — by the next analysis it
is the wrong size. A recommendation in % is stable: 20% of portfolio means
20% regardless of current value. Cert count in EUR is computed only at the
last moment in Step 4 from `Scout EUR / cert ask price` against the current
portfolio snapshot.

### § Why Rule 21 — Earnings proximity is never a skip reason

Three real cases (HIMS, HOOD, RKLB on 2026-04-20) were skipped with
"earnings too close, hold time limited" — generic textbook reasoning. But
each stock has its own pre-earnings behavior: HIMS coin-flip, HOOD
historically bullish drift T-8 → T-3 (80% green, +1.57% avg), RKLB its own
pattern. A blanket skip ignores the per-stock data that `earnings_pattern.py`
exposes specifically for this case. The correct response is: run the script,
read the per-stock pre-earnings green-rate, treat it as a confidence
adjustment (sigmoid), and adjust **hold time** (exit one day before
earnings) — but never reject the trade itself.

## 6. Backtest Rationale (v9)

Date: 2026-04-16. Backtest on 40 filled predictions revealed two patterns
that drove v9.

### 6.1 The forgotten edge under 50% confidence

5 of 40 predictions landed below 50% confidence and were rejected. All 5
moved in the signal direction, average +8.82% fwd-5d, 100% accuracy.

Common pattern:
- RSI extremely oversold (15–30)
- Commodities or stocks after a sharp crash
- System penalties ("TRENDING down", "Pre-Open weak", "CHOPPY") pulled
  confidence below the 60% gate

The stock's own fwd-5d green-rate at RSI <20 was consistently >65% [SOLID].
Regime penalties had overridden this direct mean-reversion evidence. Rule
19 (Extreme-Oversold-Bonus) was added to let stock-specific historical
green-rate override regime penalties via a controlled +5% / +8% bonus.

### 6.2 The 60–65% coin-flip bracket

Accuracy by confidence bracket (fwd-5d):

| Bracket | Accuracy | Avg Move |
|---------|----------|----------|
| 60–65% | 56% | +0.33% |
| 65–70% | 60% | +8.22% |
| 70%+ | 75% | +6.83% |

60–65% is effectively a coin-flip. The classic Scout/Confirmation split
(60/40) puts the **larger** initial size into the **least certain** bucket.
Rule 20 (Scout-Inversion) flips this to 40/60 in the 60–65% bracket: smaller
initial scout to limit damage on a wrong signal, larger confirmation only
after the trend confirms (Scout +5% in profit).

### 6.3 Sigmoid adjusts replace bucket cliffs

Old bucketed mapping (`>65% → +3%`) created arbitrary 2% jumps at bucket
edges (a stock at green-rate 64.9% got +1%, a stock at 65.1% got +3%).
Sigmoid `5 × tanh((g − 0.5) × 4) × sample_weight` gives a smooth curve with
the same asymptotic ±5% bounds and no edge cliffs. Same function used by
`indicator_context.py` (per-axis) and `earnings_pattern.py` (trade-window
mode), with earnings-specific sample thresholds (SOLID n≥8 instead of n≥30)
because earnings sample size is structurally small (max ~10 quarters).

### 6.4 Strongest-Axis aggregation

Naive sum of RSI-adjust + BB-adjust + DistHigh-adjust was wrong because
those three axes are positively correlated for trend stocks (a stock near
3M-high tends to also have high BB and elevated RSI). Summing double-counts
the same underlying signal. Strongest-axis (max |adjust|) is a conservative
single estimate. ENR.DE 2026-04-22 example: old naive sum gave +5% LONG
adjust; strongest-axis correctly gave +3.17% (DistHigh, the highest-quality
single signal of the three correlated axes).

### 6.5 Smooth differential penalty

Old penalty had a cliff: `Diff < 10 → ×0.9, Diff ≥ 10 → ×1.0`. This means
a scorecard with Diff = 9 got 10% penalty, Diff = 10 got 0% — arbitrary.
New form `1 − 0.15 × exp(−Diff/4)` gives:
- Diff = 0 → 0.85 (max penalty for a tied scorecard)
- Diff = 4 → 0.94
- Diff = 10 → 0.987
- Diff = 20 → 0.999 (effectively no penalty for a clear setup)

No cliff. Reflects the actual confidence we should have in a setup based
on how clearly the scorecard separates the two sides.

## 7. Position Sizing Reference

> Updated 2026-04-28 (v10): see § 9.A v10 Sizing Update for deltas vs v9.

| Confidence | Total (% portfolio) | Scout % of total | Confirmation % of total |
|------------|---------------------|------------------|-------------------------|
| 60–65% | 10% | **40%** (inverted, Rule 20) | **60%** |
| 65%+ | 20% | **50%** | **50%** |

Confirmation trigger is unchanged from v7: Scout +5% in profit OR clear
regime confirmation.

### 9.A v10 Sizing Update (2026-04-28)

Three changes vs v9:

1. **70%+ bracket dropped.** Replaced with single 65%+ bracket. April 2026
   live data: trades >€1.500 (the v9 70%+ bucket) had 25% win-rate and
   −€1.771 cumulative P&L vs 100% win-rate for €1.000-1.500 trades.
   Correlation between position size and P&L% on losing trades: −0,66.
   Backtest 2026-04-16 already showed 65-70% as the sweet spot
   (avg move +8,22% vs 70%+ at +6,83%).
2. **65%+ Total dropped 25% → 20%.** Conservative reset — the data does not
   support sizing above 20% even at high confidence in the current regime.
3. **65%+ split changed 60/40 → 50/50.** At 60-65% accuracy in the live
   sample, a smaller scout limits damage on Wrong-Confirm-trigger cases
   (~17% less initial exposure vs 60/40, no downside if Confirm fires).

The 60-65% Total drops from 15% to 10% as well, since the same April-2026
finding showed the lowest-confidence bracket tilting negative per-trade.

Re-evaluate after 30 additional trades under v10. If the retired 70%+ bracket
shows consistently better risk-adjusted return in fresh data,
re-introduce a higher tier. Not before.

## 8. Open Questions

- Hedging both open positions simultaneously — not yet validated (needs
  live test).
- v9 live validation — re-run backtest after 5 more trades under the v9
  ruleset.
- DB: implement `pivot` CLI command properly (currently still manual
  `cert_type` flip).
- Track-Record reporting: a future surface to separate hedge P&L from
  directional-trade P&L (deferred — no consumer right now).

## 9. Rule 26 — Tiered Stop Strategy (added 2026-04-28)

**Rule statement:** Loss exits are tiered, not single-shot. Reference
unit is cert-% (not underlying-%) because the user trades leveraged
turbo-certs.

```
Tier 1: cert −10%  →  4h watch; sell 50% if no recovery to −5%
Tier 2: cert −15%  →  HARD sell 50% immediately
Tier 3: cert −25%  →  HARD sell 100% + Rule 27 re-entry cooldown
```

**Empirical basis (n=271 closed trades, 2026-04 sample):**

Outcome distribution buckets (`account_transactions.csv` reconstruction):

| Final P&L bucket | n | % |
|------------------|---|---|
| ≤ −50% | 11 | 4.1% |
| −50% to −40% | 13 | 4.8% |
| −40% to −30% | 18 | 6.6% |
| −30% to −20% | 21 | 7.7% |
| −20% to −15% | 16 | 5.9% |
| −15% to −10% | 20 | 7.4% |
| −10% to 0% | 58 | 21.4% |
| 0% to +20% | 71 | 26.2% |
| +20% to +30% | 22 | 8.1% |
| +30%+ | 21 | 7.7% |

**Tail-loss findings:**

| Threshold | Frequency | Avg final outcome |
|-----------|-----------|-------------------|
| Trades that ended ≤ −15% | 79/271 = 29.2% | **−33.3%** |
| Trades that ended ≤ −25% | 52/271 = 19.2% | (worse) |
| Trades that ended ≤ −35% | 28/271 = 10.3% | (worst) |

**Damage attribution:**
- Total loss% sum (all losing trades): −3141%
- Loss% sum from ≤−15% tail: **−2631% = 84% of total damage**

**Why this matters:** A position at −15% has a 16% probability of
recovering to BE; the modal outcome is to continue to −33% (median),
because the cert leverage compounds against you. Disciplined exit at
Tier 2 caps the loss at −15% on 50% of position vs. waiting and
losing −33%+ on the full position. EV-positive by ~18 pp per trade.

**Why tier 3 at −25%, not −20% or −30%:**
- −20% is too tight: catches normal-volatility cert noise (1× ATR ≈
  20% cert move on 5× leverage = false positives)
- −30% is too late: by then we're in the −33% empirical mean already
- −25% is the inflection point where "noise" becomes "thesis broken"
  for our 1-3d horizon, validated by the 19.2% ≤−25% bucket

**Forbidden patterns (auto-veto in Step 3 reasoning):**
- "Hold to KO and re-enter" — KO is a backstop for runaway gaps,
  not a managed exit
- "Hedge with opposite cert at −20%" — negative-EV due to spread
  + dual leverage decay
- "Stop calculation in underlying-%" — wrong unit for cert trades
- Any "tighten stop by 2%" once −25% breached

## 10. Rule 27 — Re-Entry Cooldown (added 2026-04-28, clarified 2026-04-29)

**Rule statement:** After ANY exit on symbol X (Tier-2/3 stop or full +20%
take-profit), a structured cooldown protocol governs re-entry. Re-evaluation
is always allowed; trade-plan output is hard-clamped while the cooldown is
active. Full mechanics in `prompts/03_judge_risk.md` § Rule 27 (Decision
tree Cases A/B/C + NO-TRADE Output Clamp).

### Why Rule 27 — Evidence Base

This rule has **insufficient statistical evidence for inference** (n=1
documented same-symbol re-entry-after-exit incident in the trade history at
the time of introduction). It is retained as **operational discipline**,
not statistical inference, on three explicit grounds:

1. **Asymmetric downside.** The cost of a wrong "block re-entry" decision
   is foregone profit on a setup that may have been valid. The cost of a
   wrong "allow re-entry" decision after a stop is compounded loss plus
   cumulative tilt risk on subsequent trades. The downside tail is
   structurally larger than the upside tail, which justifies asymmetric
   defensive bias even without n≥30 evidence.

2. **Operational discipline > statistical inference at small n.** Trading
   literature treats post-loss re-entry as a known behavioural failure mode
   independent of any individual trader's history. A rule that mechanically
   prevents this pattern reduces decision-load in stress moments, where
   discretion historically performs worst.

3. **Explicit insufficient evidence.** The rule does NOT claim "n=1 proves
   the pattern." It claims "n=1 is consistent with the literature pattern,
   and the asymmetric-downside structure justifies retention until the
   tracking trigger fires."

### Tracking trigger (n ≥ 10 same-symbol re-entry attempts)

Logged in `memory/v10_log.md` § Same-Symbol Re-Entry Attempts alongside the
Rule 28 tracking block. Per attempt the log captures: exit timestamp, exit
reason (Tier/TP), re-eval timestamp, criteria pass/fail (C2/C3/C4
individually), trade executed Y/N, and P&L if executed.

Re-evaluation at n ≥ 10:

- If Win-Rate of executed re-entries trails the baseline Win-Rate by ≥15pp:
  rule confirmed by data, retain as hard.
- If Win-Rate of executed re-entries is within ±5pp of baseline: the
  asymmetric-downside argument no longer holds, demote to Pending or drop.
- If criteria pass rarely (<20% of re-eval attempts) and no asymmetry is
  detectable: the rule may be over-restrictive, recalibrate the +10pp /
  NEW-catalyst thresholds.

Status: HARD active, evidence-base disclosed, tracking armed.

### Decision-tree clarification (2026-04-29)

The original wording "If criteria not met: extend cooldown by 48h" was
ambiguous about when the criteria are checked and when the +48h anchor
starts. Three textually defensible readings (cooldown extends from exit,
from re-eval attempt, or only post-24h) collapse into a single mechanic
in `prompts/03_judge_risk.md` § Rule 27. Pre-24h re-evals that pass
criteria are informative only — there is no override path; pre-24h passes
are logged as data, not as trade triggers.

### Output clamp (2026-04-29)

When the cooldown is active, Step 3 / Step 4 output omits Entry Plan, KO
Computation, Stop levels, Position Sizing, and Cert-Request blocks. The
DB record stores `--direction` and `--confidence` for tracking but writes
NULL into `entry_price`, `stop_price`, `target_price`, `ko_level`. This
required a schema migration on those columns from NOT NULL to NULL-allowed
(2026-04-29). Rationale: handleable levels in a NO-TRADE card become
ambient temptation in the next stress moment.

## 11. Rule 28 — Trader-Day Circuit-Breaker (PENDING, re-evaluate 2026-05-29)

**Status:** PENDING. Originally introduced 2026-04-28 as hard veto in v10.0.
Demoted 2026-04-29 to soft warning + tracking, after the evidence base was
re-examined. Tracking and decision schema live in `memory/v10_log.md`.

**Current behavior:** `scripts/preflight_check.py::check_rule_28()` still
detects Tier-2 / Tier-3 / Support-Override stops in the trailing 32-hour
window. On match, preflight emits a `[RULE 28 PENDING — TRACKING]` notice
to stderr **but does NOT exit** — the pipeline continues. The notice
includes a reminder to log the stop in `memory/v10_log.md`.

### Why demoted from hard veto to pending

The April 2026 evidence base (n=12 follow-up trades after a Tier-2/3 stop)
is too small to distinguish three observationally equivalent hypotheses:

1. **Tilt hypothesis:** trader makes worse decisions in the hours after a stop
2. **Market hypothesis:** Tier-2/3 stops cluster on bad market days, follow-up
   trade suffers from the same market environment
3. **Selection hypothesis:** fewer good setups exist on stop-days because the
   broader market is bearish — follow-up sample is biased toward weaker setups

A hard veto under hypothesis 1 is correct intervention. Under hypothesis 2,
the correct intervention is a market-state filter (not a stop-state filter).
Under hypothesis 3, the correct intervention is tighter setup-quality gating.
Without S&P-500 and sector-ETF returns alongside follow-up outcomes, all
three hypotheses produce the same observed Win-Rate gap (33% after loss vs
78% after win in April).

### Backtest contribution — corrected estimate

The April-2026 v10 backtest reported +€1029 vs original baseline. The
commit message did not break this down by component. Realistic isolated
attribution for Rule 28: 3 prevented trades × expected P&L at the
loss-after-loss baseline (33% Win-Rate, +€82 on win, −€136 on loss):
1×82 − 2×136 = **+€190**. Sizing flatten (Rule 20 v10) and Concentration
tightening (V3/V4/V6) carry the bulk of the +€1029 edge. Rule 28 is the
weakest of the three v10 changes by April backtest, and its evidence base
is also the smallest.

### April 2026 baseline data (still relevant for tracking calibration)

| Cohort | n | Avg P&L | Win-rate |
|--------|---|---------|----------|
| Trade after a LOSS | 12 | −€136 | 33% |
| Trade after a WIN  | 13 | +€82  | 78% |
| Baseline (all)     | 31 | −€22  | 58% |

The Tilt-style interpretation predicted by these numbers is real if and only
if the May tracking shows the same Win-Rate gap **with S&P returns near zero
on stop-days**. If the gap shrinks under S&P-controlled comparison, the
April pattern was market-confounded.

### Specific case study — ENR 2026-04-28

- 11:12 CET: Tier 2 (€1,60) trigger, 193 shares closed at −€55.
- 11:29 CET: Tier 3 (€1,46) trigger, 192 shares closed at −€97.
- Position completed loss in **17 minutes**.
- Within hours, NVDA Scout opened (102 shares @ €1,96, €200 deployed).
- This is the founding case for Rule 28. Under Pending, the pattern is now
  observable but not blocked — it becomes one logged data point among 30
  that the 2026-05-29 evaluation will use.

### Decision schema 2026-05-29

See `memory/v10_log.md` § "Decision schema for 2026-05-29" for the locked
numerical schema (S&P-500 mean × Follow-up Win-Rate matrix). Schema is
locked in advance to prevent post-hoc redefinition.

### Implementation notes (kept for restoration if Rule 28 promoted to hard)

- Free-text matching on `close_events.reason` was chosen over a schema
  column because the column already carries strings like *"Both Tier 2
  (€1.60) + Tier 3 (€1.41) triggered within 17 min..."*. Closed
  vocabulary {tier 2, tier 3, support-override} is robust against
  reason-text drift.
- 32-hour trailing window covers both Tier-2 (block until 22:00 same
  day = 11h) and Tier-3 (block today + next day = 32h) cases in one SQL.

### Restoration path (if 2026-05-29 promotes back to hard)

In `scripts/preflight_check.py::main()` replace the Pending notice block
with the original hard-veto block (`print(veto_msg, file=sys.stderr);
sys.exit(2)`). Update CLAUDE.md hard-rule list and this § 11 status line.
Single commit, no schema or DB migration needed.

## 12. v10 Concentration Tightening (added 2026-04-28)

Three parameter changes to existing concentration limits, no new rule numbers
needed beyond V6 (which slot was free):

**V3:** slot cap 3 → 2 turbo positions. Hedges (cert_type='hedge') excluded
from the count, consistent with existing § 3 hedge logic.

**V4:** sector cap 60% → 40%, with AI-semi grouping rule. The grouped
basket is `{NVDA, AMD, AVGO, MRVL, TSM, ASML}`, treated as ONE effective
sector regardless of yfinance label. Implementation in
`lib/risk_audit.py::get_effective_sector(symbol)`.

**V6 (was W2):** correlation halve-size → hard veto at 60-day daily-return
correlation ≥ 0,7. Implementation in
`lib/risk_audit.py::compute_correlation(sym_a, sym_b)`. If either symbol
has < 60d yfinance history, V6 returns indeterminate → soft warning
"V6 inconclusive, n<60" without auto-veto.

### Rationale — April 2026 clustering

April 2026 had four days with >€2.000 deployed across 3+ buys
(2026-04-02: €3.404 / >50% portfolio across 4 buys). 2026-04-27 had AMD
long + NVDA scout simultaneously — 60d correlation ~0,85, effectively a
single AI-semi trade. When AMD broke down on 28.04, NVDA was unprotected
(correlation contagion). The existing V3/V4/W2 settings were too loose to
prevent this clustering:

- V3=3 allowed three simultaneous turbos (no diversification benefit when
  all three are leveraged on the same theme).
- V4=60% allowed 2/3 of capital concentrated in a single sector — the very
  definition of single-name beta dressed up as diversification.
- W2 substring-matched ticker text ("AMD" matches "AMDA"), did NOT compute
  actual correlation. Two near-identical positions (AMD + NVDA) registered
  as W2 PASS, no halve.

**v10 reset:** V3=2 ensures focused attention. V4=40% prevents single-sector
blow-ups. V6 replaces soft W2 with a hard correlation veto at the level
where two positions become effectively one trade (corr ≥ 0,7 = 49% shared
variance).

### V6 indeterminate fallback

For symbols with < 60 trading days of history (recent IPOs, illiquid
small-caps), correlation is unreliable. Falling back to a soft warning
rather than vetoing avoids over-caution on cases where the rule has no
empirical foundation.

The 80% overlap rule (`if len(merged) < days * 0.8: return None`) catches
mismatched trading-day calendars (e.g. ENR.DE vs NVDA — different
holidays). When overlap is too thin, the correlation is statistically
unreliable.
