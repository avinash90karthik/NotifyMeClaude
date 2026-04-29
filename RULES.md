# Rules — Single Registry

> Single owner of rule rationale, evidence, and falsification triggers
> for the Silver Hawk Trading pipeline. Operational mechanics
> (thresholds, output formatting, score tables) live in the prompt that
> enforces each rule; this file links to that owner. The DB schema lives
> in `scripts/prediction_db.py`; strategy version history lives in `git
> log`.

## Severity legend

Every rule in this file falls into exactly one of four severities. The
severity determines what happens when the rule fires:

- **Veto** — blocks hard. An active Veto means signal = NO-TRADE or analysis abort. No override.
- **Soft Veto** — blocks by default (NO-TRADE), but Judge / user can override with an explicit, documented reason in the Step-3 card.
- **Warning** — does not block, but mandates an adjustment to the trade plan, sizing, or confidence. Skipping the adjustment is a rule violation.
- **Soft Warning** — recommendation with a default behaviour. Override allowed when the user accepts the trade-off in writing.

Rules are grouped by severity below and numbered within each group
(V1–V5 / SV1–SV3 / W1–W12 / SW1–SW2). Numbering is local to the
severity group; there is no "global rule 14" any more.

---

# Vetos

The five Vetos block trading or abort the analysis without exception.
Owner of the operational table for V4 / V5: [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md).

## V1 — KO is computed, never estimated

- **Severity:** Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § KO Level](prompts/03_judge_risk.md)
- **One-line summary:** Both ATR-based and chart-based KO must be computed; the further-of-the-two is final. If calculation fails, the analysis aborts.
- **Rationale:** Estimated KO levels invariably end up "round-number friendly" (e.g. €150 because it looks clean) rather than data-derived. Round-number stops cluster with retail orders → liquidity sweeps that knock out positions for no fundamental reason. ATR-based + chart-based gives two independent anchors; the further-out value provides a buffer against single-method failure. If both methods fail to compute, the trade is invalid — not because we lack a number, but because we lack the information the calculation requires.
- **Evidence base:** Operational.
- **Falsification trigger:** Estimated-KO outcomes not worse than computed-KO at n≥20. Tracking infrastructure required (DB has no `ko_method` field); deferred until that exists.

## V2 — SHORT scorecard is mandatory

- **Severity:** Veto
- **Owner (mechanics):** [`prompts/02_investment_debate.md` § Round 1 / Scorecard](prompts/02_investment_debate.md)
- **One-line summary:** The 6-axis scorecard is filled for BOTH directions in every analysis. SHORT is not optional. An analysis missing the SHORT side is invalid and must be redone before any signal is emitted.
- **Rationale:** Multiple historical analyses showed asymmetric scoring: when the bull thesis was emotionally compelling, the scorecard was filled out for LONG only and the SHORT side was implicitly dismissed. Forcing both sides through the same 6-axis scoring catches the cases where SHORT actually has the higher total — which then triggers the mirror test in Step 3. Without this rule, the system silently develops a directional bias.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## V3 — Prices and FX come from APIs, never from web search

- **Severity:** Veto
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.2](prompts/01_data_collection.md) (and `scripts/collect_data.py`)
- **One-line summary:** All prices (underlying spot, cert bid/ask, FX) come from a structured API. Never hardcode fallbacks; never derive prices from web search. When the US market is closed, use premarket / postmarket data via the same API. If all APIs fail, the analysis aborts.
- **Source order:**
  1. **yfinance** — primary for underlying spot, OHLC, FX (`yf.Ticker(SYMBOL).info`, `.history(period='1d', interval='5m', prepost=True)` for premarket / postmarket).
  2. **pytr** — primary for cert bid/ask on Trade Republic exchanges (TUB / SGL / LSX). Use when the cert price is the answer the question needs.
  3. **twelvedata** — fallback when yfinance is unreachable for the underlying. The Basic plan does NOT support pre-/postmarket — do not waste time on it for extended-hours data.
  4. **Web search** — never used for prices. Only for news, macro context, and qualitative information.
- **Rationale:** With cert position sizes in EUR and underlying prices in USD, even small FX or price drifts become several-times-larger errors in cert P&L because of leverage. APIs return structured, timestamped data with known precision; web search returns text that may be stale, paraphrased, or simply wrong. The penalty for using a stale web price on a leveraged cert is a silently mis-sized position or a wrong KO calculation — both invisible until the trade goes wrong. When the US market is closed, premarket via `prepost=True` is the only honest live signal; using yesterday's close while the rest of the analysis is real-time creates a hidden inconsistency.
- **Evidence base:** Operational — formalised after multiple mis-sized positions traced to non-API price inputs.
- **Falsification trigger:** Operational — no outcome falsification.

## V4 — ATR > 7%

- **Severity:** Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md)
- **One-line summary:** ATR > 7% → cert is the wrong instrument. Use warrants or options instead, not a turbo cert.
- **Rationale:** At ATR > 7%, normal daily noise puts cert positions at Tier-2 risk every other day. Leverage on a high-vol underlying compounds; the cert decays via spread + financing before the directional move materialises. The instrument is the problem, not the thesis.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## V5 — Maximum 3 open turbo positions

- **Severity:** Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md)
- **One-line summary:** No more than 3 open turbo positions at any time.
- **Rationale:** Each open turbo demands continuous attention (stop management, cert-% tracking, overnight checks). 3 is the upper bound at which a non-fulltime trader can still manage every position cleanly; above that, attention dilutes faster than diversification compensates. Three genuinely independent setups at once is rare in practice — the cap is a ceiling, not a target. Concentration of risk across multiple correlated positions on a single theme is caught separately by SV2 (correlation veto).
- **Evidence base:** Operational — current cap reflects sustainable attention bandwidth.
- **Falsification trigger:** Operational — no outcome falsification.

---

# Soft Vetos

Default behaviour is NO-TRADE, but the Judge may override with an
explicit `"<rule>-override: <reason>"` line in the Step-3 card. The
override forces the Judge to name what the rule's classifier missed
before acting.

## SV1 — CHOPPY regime + Score < 50

- **Severity:** Soft Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md)
- **One-line summary:** CHOPPY regime AND scorecard total < 50 → no trade by default. Override with `"SV1-override: <reason>"` if there is a specific stock-level signal the regime classifier missed.
- **Rationale:** CHOPPY regime + weak scorecard is the textbook "no setup" case. Default no trade — but the regime label is a coarse classifier and can mislabel; an explicit override forces the Judge to name the specific signal that the classifier missed before acting on it.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## SV2 — 60-day daily-return correlation ≥ 0,7

- **Severity:** Soft Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md). Implementation: `lib/risk_audit.py::compute_correlation(sym_a, sym_b)`.
- **One-line summary:** 60-day daily-return correlation ≥ 0,7 between the candidate symbol and ANY open position → no trade by default. Override with `"SV2-override: <reason>"` citing why correlation breakdown is expected (e.g. divergent earnings, sector-rotation thesis).
- **Rationale:** corr ≥ 0,7 means 49% shared variance — two positions become effectively one trade. Substring-matching on ticker text (the previous approach) missed this because it didn't compute actual correlation; SV2 computes it explicitly.
- **Indeterminate fallback:** if either symbol has < 60 days of yfinance history, SV2 returns "inconclusive, n<60" and does NOT auto-block. Falling back avoids over-caution where the rule has no empirical foundation. The 80% overlap rule (`if len(merged) < days * 0.8: return None`) catches mismatched trading-day calendars (e.g. ENR.DE vs NVDA — different holidays).
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## SV3 — Sector > 40%

- **Severity:** Soft Veto
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / V Vetos](prompts/03_judge_risk.md). Implementation: `lib/risk_audit.py::get_effective_sector(symbol)`.
- **One-line summary:** Sector concentration > 40% of portfolio after the candidate trade → no trade by default. AI-semi basket `{NVDA, AMD, AVGO, MRVL, TSM, ASML}` treated as ONE effective sector regardless of yfinance label. Override with `"SV3-override: <reason>"` naming the divergence the sector label misses.
- **Rationale:** A sector cap above 40% allows roughly half the portfolio in single-name beta dressed up as diversification. The AI-semi grouping prevents the "AMD + NVDA + AVGO are different sectors per yfinance" trap when in practice they trade as one beta cluster. Soft Veto because a documented sector-rotation or single-name divergence thesis can override the cluster heuristic.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

---

# Warnings

Warnings do not block trades. They mandate an adjustment to the trade
plan, sizing, or confidence; skipping the adjustment is a rule
violation.

## W1 — Position recommendations are in % of available Cash

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Position Sizing](prompts/03_judge_risk.md)
- **One-line summary:** Position size = % of **available Cash**, not % of (Cash + invested). Pull live Cash from `pytr portfolio` at sizing time, not from the DB. Cert count in EUR is computed only at the end of Step 4 from `Scout EUR / cert ask price`.
- **Rationale:** Available Cash is the only capital that can fund a new position. The mark-to-market value of open positions is unrealised — it shifts with every tick, can't be deployed, and reverts on a stop. Sizing against `Cash + invested` overstates the deployable budget on red days and understates on green days. The DB-Cash field lags real Cash because TR's booking pipeline is asynchronous; `pytr portfolio` returns the broker's live figure, which is the truth at the moment the order is placed.
- **Evidence base:** Operational — DB-vs-pytr Cash divergence observed during 2026-04 trading.
- **Falsification trigger:** Operational — no outcome falsification.

## W2 — Price-Action Reality Check (Greens-10d penalty)

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.4 Price-Action Reality Check](prompts/01_data_collection.md)
- **One-line summary:** When MACD-Histogram or RSI signals a bullish turn AND `price_action_check.py` reports Greens-10d < 5, the Judge MUST apply a confidence penalty in the range −5% to −10%. Penalty depth scales with how few green days exist; Judge cites the chosen value, the Greens-10d count, and which indicator-turn fired in the Step-3 card.
- **Penalty mapping:**
  - Greens-10d = 0–1 → −10% (lowest price-action confirmation)
  - Greens-10d = 2–3 → −7% to −8% (Judge's discretion within these two values)
  - Greens-10d = 4 → −5% (right at the threshold)
  - Greens-10d ≥ 5 → no penalty triggered (verdict is "confirmed up-flow"; W2 does not fire)
- **Rationale:** MACD-Histogram is a smoothed second derivative of price; it can flip "rising" mathematically while the underlying trend is still firmly down. RSI exiting the oversold band is the same pattern. Greens-10d < 5 means the price itself has not yet confirmed the indicator-turn. Indicator-only LONG entries against a low-greens backdrop have historically been the dominant cause of "catching a falling knife" trades. The penalty range exists because Greens=1 (almost pure bear month) is a meaningfully different setup from Greens=4 (right at the confirmation threshold); a flat single penalty would over-punish Greens=4 or under-punish Greens=1.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## W3 — Indicator Context Check (strongest-axis aggregation)

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.4 Indicator Context Check](prompts/01_data_collection.md) and `scripts/indicator_context.py::print_aggregation`
- **One-line summary:** Use this stock's own historical conditional probabilities (per-stock RSI/BB/DistHigh green-rate) instead of textbook overbought/oversold priors; aggregate via the strongest single axis (max |adjust|), not by summing.
- **Rationale:** Textbook rules ("RSI >70 is overbought") are cross-asset priors averaged over thousands of stocks. They do not apply to a stock whose own history disagrees. Naive sum across RSI/BB/DistHigh double-counts the same underlying signal because those axes are positively correlated for trend stocks (a stock near 3M-high tends to also have elevated BB and elevated RSI — adding the three adjusts conflates one signal as three). Strongest-axis is a conservative single estimate that avoids the double-count. The script computes per-stock green-rates fresh from the latest history on every run, so the rule adapts as the stock's regime evolves.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## W4 — Entry: Center for the DB, vol-derived range for the broker

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Optimal Entry](prompts/03_judge_risk.md)
- **One-line summary:** Entry has two artifacts — a single Center level (recorded in DB as `--entry`) and a range around it (Primary low / Fallback high, sent to the broker). Center is the mid expected fill; the range is the actual order. Never use the Close as Center; never use a single point limit as the broker order.
- **Mechanics (mandatory format):**
  - **Center** = `Close − 1×ATR` (Reversion-Pflicht) OR `Buy-range upper / P25 dip` (no Reversion-Edge) OR `trigger level` (real breakout). Per Reversion-Guard verdict.
  - **Half-width** = `max(0.25 × ATR, 0.5% × Close, 0.10 €)`
  - **Primary** = Center − half-width (range low, optimistic)
  - **Fallback** = Center + half-width (range high, defensive, valid 60–90 min after Primary)
  - **No-Chase** = Center + 2 × half-width — trade expires above this
  - Step-3 card prints all four levels. DB record uses Center as `--entry`. Pre-commit check: the value passed to `--entry` MUST equal the Center value cited in the Step-3 card; if they differ, stop and reconcile before recording.
- **Rationale:** Recording the Close as entry biases the backtest — the next analysis assumes a fill that was never realistic. A point limit ("exactly $89,00") systematically misses fills when the market only just touches the value. Center reflects the mid expected fill price after a normal intraday dip; the range absorbs intraday noise without overpaying. The half-width formula has three terms because each protects against a different failure: `0.25 × ATR` reflects stock-specific intraday vol, `0.5% × Close` is the floor for low-ATR names, `0.10 €` is the absolute tick floor for warrants/turbos whose spread step exceeds the computed range.
- **Evidence base:** Operational.
- **Falsification trigger:** Center-fill performance not better than Close-fill at n≥30 entries. Tracking infrastructure required (DB has no `entry_method` field); deferred until that exists.

## W5 — Extreme-Oversold Bonus

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.4 v9 Extreme-Oversold Bonus](prompts/01_data_collection.md) and [`prompts/03_judge_risk.md` § Signal + Confidence](prompts/03_judge_risk.md)
- **One-line summary:** RSI < 20 with stock's own fwd-5d green-rate ≥ 65% (n ≥ 20 SOLID) → +5% LONG; RSI < 15 with green-rate ≥ 70% → +8% (capitulation low). Bonus is added AFTER the differential penalty.
- **Rationale:** Extreme oversold setups in a TRENDING-down regime get penalised by the regime classifier, often pushing confidence below the 60% gate even when this stock's own forward distribution is bullish at that RSI level. Without the bonus, regime penalties override direct mean-reversion evidence; this controlled bonus lets stock-specific empiricism override regime penalties at the very deepest oversold readings, where the per-stock conditional is strongest.
- **Evidence base:** Operational.
- **Falsification trigger:** Bonus-triggered trades' fwd-5d green-rate < 60% at n≥20.

## W6 — Position Sizing (Scout / Confirmation)

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Position Sizing](prompts/03_judge_risk.md) — numeric table lives there, this file does not duplicate it.
- **One-line summary:** Confidence 60–65% → Total 10% of available **Cash** with inverted Scout (40/60); Confidence 65%+ → Total 20% of Cash with classic 50/50 Scout/Confirmation. Confirmation fires only after Scout +5% in profit OR clear regime evidence.
- **Rationale:**
  - **Why inverted in 60–65%:** the bracket sits closest to a coin-flip on historical data, so the classic 60/40 Scout/Confirm split would put the larger initial size into the least-certain bucket. Inverting (40/60) places the smaller commitment first, larger Confirmation only after the trend confirms in profit.
  - **Why 50/50 above 65%:** at moderate-but-not-overwhelming hit-rates, a smaller initial Scout limits damage when Confirmation never triggers. 50/50 keeps the upside intact when Confirmation does fire.
  - **Why no 70%+ bracket:** higher-confidence trades historically did not yield proportionally larger returns risk-adjusted, while a single 20% Cash position is already meaningful relative to the 10% bracket. A separate larger tier added size without adding edge.
  - **Why Total 10% in 60–65%:** the lowest-confidence bracket compounds two coin-flip risks — the signal itself plus the day-noise. A smaller total pot lets the inverted Scout do its job without making the right leg too small to matter.
- **Evidence base:** Sized from v9 backtest + v10 live data; specific numerical findings live in git history rather than here, since the bracket parameters are subject to re-evaluation as more trades close.
- **Falsification trigger:** After ~30 additional trades under the current bracket configuration: if a higher-confidence tier shows consistently better risk-adjusted return in fresh data, re-introduce one; if 60–65% still tilts negative, drop the bracket entirely.

## W7 — Earnings proximity is NEVER a skip reason

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.8b Earnings Window Pattern](prompts/01_data_collection.md)
- **One-line summary:** Run `earnings_pattern.py`. Use the per-stock pre-earnings green-rate as a sigmoid confidence adjust (~±5%), not as a gate. Adjust hold time (typically exit one day before earnings) — never reject the trade itself.
- **Rationale:** Each stock has its own pre-earnings behaviour — some drift bullishly into the print, some sell off, some are coin-flips. A blanket skip on "earnings too close" applies a textbook prior across stocks where the per-stock empiric disagrees. The script computes the conditional green-rate from this specific stock's history; that number is the right input, not a generic skip-rule. The trade-horizon adjustment (exit T-1) is real, but it is a hold-time constraint, not a setup veto.
- **Evidence base:** Operational.
- **Falsification trigger:** Per-stock pre-earnings green-rate < 50% across n≥30 earnings-window trades that the rule allowed in. Tracking is implicit (each `earnings_pattern.py` run logs to DB); a dedicated aggregation script is future work.

## W8 — Sizing Pre-Flight Gate

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Sizing Pre-Flight Gate](prompts/03_judge_risk.md)
- **One-line summary:** Before any EUR sizing number is written, three checks must PASS: Confidence-Bias-Check, Correlation/Cluster-Check, Cash-Basis. Any FLAG / USER-CONFIRMATION-NEEDED / AMBIGUOUS → STOP and reconcile before continuing.
- **Rationale:** Sizing errors compound silently. A bias in Rating 1, a stale portfolio snapshot, and a correlation rule applied against a position that is already closed each look like minor inputs in isolation — but their product is a wrong EUR number that the user will execute. The pre-flight gate forces each input to be re-cited from its primary source before the EUR figure is committed, making the error surface visible while it is still fixable.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## W9 — Tiered Stop Strategy

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Loss Exits](prompts/03_judge_risk.md) and `scripts/tr/place_exits.py`
- **One-line summary:** Cert −15% → HARD sell 50% immediately (Tier 2); cert −25% → HARD sell 100% (Tier 3) and activate SW2 cooldown. Reference unit is cert-%, not underlying-%. Support-Override: if underlying closes below the strongest support level, force HARD sell 50% even if cert hasn't hit −15%.
- **Rationale:** A position at −15% has a ~16% probability of recovering to BE; the modal outcome is to continue to roughly −33% (median), because cert leverage compounds against you. Disciplined exit at Tier 2 caps the loss at −15% on 50% of position vs. waiting and losing −33%+ on the full position. Tier 3 at −25% is the inflection point where "noise" becomes "thesis broken" for the 1–3d horizon: −20% catches normal-vol cert noise as false positives, −30% is too late (already at the empirical mean). The Tier-1 (−10% watch) was removed because a 4h watch is operationally unrealistic for a non-fulltime trader; a rule that can't be executed reliably is worse than no rule.
- **Evidence base:** Initial calibration on n=271 closed trades (April 2026 sample) showed roughly 29% of trades ended ≤ −15% with an average final outcome near −33%, and the ≤ −15% tail accounted for ~84% of total damage across all losing trades. The DB accumulates further closed trades on every exit; this initial calibration is the rule's starting point, not a frozen evidence base — re-derive against the live DB before challenging the parameters.
- **Falsification trigger:** Re-run the tail analysis against the live DB. W9 should be reconsidered if the disciplined-Tier-2-exit cohort's average P&L is worse than the no-stop-hold cohort at n≥30 disciplined exits, or if the ≤ −15% tail's share of total damage drops materially below the original ~84%.

## W10 — Earnings < 5 days

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / W Warnings](prompts/03_judge_risk.md)
- **One-line summary:** KO multiplier +0.5 when earnings within 5 days.
- **Rationale:** Earnings windows have wider intraday range; pulling KO out by 0.5× ATR avoids stop-out on event-day vol expansion.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## W11 — KO < 2× ATR (too tight)

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / W Warnings](prompts/03_judge_risk.md)
- **One-line summary:** Push KO out, raise multiplier when computed KO is closer than 2× ATR.
- **Rationale:** KO < 2× ATR is structurally too tight — normal daily noise will hit it. The W11 push restores the intended buffer.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## W12 — Overnight event < 24h

- **Severity:** Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Risk Audit / W Warnings](prompts/03_judge_risk.md)
- **One-line summary:** Position ≥ +10% → BE-stop mandatory; ≥ +15% → 50% partial exit or stop to +5%; < +10% → default = close, or document risk acceptance. Friday: always BE-stop before the weekend.
- **Rationale:** Trump speeches, FOMC, CPI, NFP, earnings — all are gap-risk events. An unprotected overnight position can lose more in 30 seconds than the entire trade gained over its hold. BE-stop at +10% locks in the work; partial exit at +15% takes profit while keeping a runner.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

---

# Soft Warnings

Recommendations with a default behaviour. Override is allowed when the
user accepts the trade-off in writing.

## SW1 — Argument quality over vote count

- **Severity:** Soft Warning
- **Owner (mechanics):** [`prompts/01_data_collection.md` § 1.5 Quality Check](prompts/01_data_collection.md)
- **One-line summary:** Evaluate news/Reddit posts by what is actually argued, not by upvote count, comment volume, or majority direction. Document the strongest 2–3 arguments per side and tag each as HARD or SOFT; if one side carries HARD arguments and the other only SOFT, that side wins regardless of which is the minority.
- **Argument tagging:**
  - **HARD** — verifiable claim with primary source: SEC filing, insider transaction, earnings number, official company statement, dataset, court filing
  - **SOFT** — opinion, narrative, "I think", price target without methodology, vibe, meme, sentiment claim without data
- **Rationale:** Reddit / news sentiment defaults to dip-buying psychology — 70% bullish on a −30% stock is the baseline, not a signal. Upvotes track agreeableness and post timing, not argument quality. Reading the actual content protects against two failure modes: (1) following the loud majority into a setup whose real basis is just narrative, and (2) dismissing a contrarian post that happens to cite hard data because "everyone disagrees with it". The minority is sometimes wrong; the SOFT majority is wrong more often than the HARD minority.
- **Evidence base:** Operational.
- **Falsification trigger:** Operational — no outcome falsification.

## SW2 — Re-Entry Cooldown

- **Severity:** Soft Warning
- **Owner (mechanics):** [`prompts/03_judge_risk.md` § Re-Entry Cooldown](prompts/03_judge_risk.md) and [`prompts/04_summary_send.md` § 1a Trading Card variant](prompts/04_summary_send.md)
- **One-line summary:** After ANY exit on symbol X (Tier-2/3 stop or +20% TP), a 24h cooldown applies from `exit_ts`. During cooldown the pipeline still runs but the output is NO-TRADE-clamped (no Entry Plan / KO / Stop / Sizing / Cert-Request); the user can override with explicit acknowledgement. After 24h: normal trade if the pipeline produces a signal.
- **Rationale:** A discipline rule, not an outcome-edge claim. There is no statistically meaningful evidence that re-entering within 24h underperforms — the rule rests on the behavioural argument that a forced pause between a loss-stress moment and the next decision is a cheap and reasonable default. Soft Warning matches the actual evidence quality: cooldown + output-clamp remain the default, but overriding is allowed if the user accepts the discipline trade-off in writing. The output-clamp specifically prevents handleable levels in a NO-TRADE card from becoming ambient temptation in the next stress moment; that property is preserved under the Soft-Warning status. Schema migration 2026-04-29 (`scripts/migrate_rule27_nullable.py`) made `entry_price` / `stop_price` / `target_price` / `ko_level` columns NULL-allowed for the clamped DB record path.
- **Evidence base:** No statistically robust evidence base. The rule is a behavioural default backed by general tilt-mitigation reasoning, not by an outcome study on this account's data.
- **Falsification trigger:** None — the rule is not outcome-evaluated. Reconsider only if the discipline argument itself stops applying (e.g. mechanical execution removes the trader's same-day re-entry decision entirely).
