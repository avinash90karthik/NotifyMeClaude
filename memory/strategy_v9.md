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

| Confidence | Total (% portfolio) | Scout % of total | Confirmation % of total |
|------------|---------------------|------------------|-------------------------|
| 60–65% | 15% | **40%** (inverted, v9 Rule 20) | **60%** |
| 65–70% | 20% | 60% (classic) | 40% |
| 70%+ | 25% | 60% (classic) | 40% |

Confirmation trigger is unchanged from v7: Scout +5% in profit OR clear
regime confirmation.

## 8. Open Questions

- Hedging both open positions simultaneously — not yet validated (needs
  live test).
- v9 live validation — re-run backtest after 5 more trades under the v9
  ruleset.
- DB: implement `pivot` CLI command properly (currently still manual
  `cert_type` flip).
- Track-Record: separate hedge P&L from directional-trade P&L in dashboard
  (deferred to PR-B / PR-C).
