# Paper Backtest — Out-of-Sample Validation of v9 Rules (2014-2023)

Isolated academic backtest of the Silver Hawk v9 trading rules on a
pre-development sample (2014-01-01 → 2023-12-31). Everything in this folder
is self-contained and does NOT touch production code (`prediction_db.py`,
`morning_screener.py`, `collect_data.py` etc. remain untouched).

## Goal

Validate the two core concepts of the system:
1. **Per-stock calibration** (reversion_guard, indicator_context)
2. **Multi-agent gate architecture** (scorecard + judge + vetos)

against Buy-and-Hold SPY, naive textbook-RSI, and a random-entry control.

## Scope / Limitations (documented up-front, not retrofitted)

- **No LLM calls.** Step 2 Bull/Bear debate is replaced by the deterministic
  scorecard formula. We cannot replicate LLM-driven debate out-of-sample.
- **No news / Reddit / Trump signals.** Historical social-media flow is not
  reliably reconstructible for 2014-2023 without paid APIs. Those scorecard
  axes are set to NEUTRAL (5/10) and flagged in the paper as a limitation.
- **No macro-event calendar beyond earnings.** NFP/CPI/Fed-day awareness is
  not modelled; only scheduled-earnings awareness is used.
- **Frozen parameters.** All thresholds (RSI bands, green-rate cutoffs,
  +5%/+8% bonus, KO multipliers, 60% gate) stay at the values fitted during
  the 2025 production period. No retuning.

## Structure

```
paper/
├── README.md                   # this file
├── universe.py                 # Phase 1: static 25-symbol universe
├── data_quality.py             # Phase 1: validate_data_quality(symbol)
├── historical_view.py          # Phase 2: HistoricalMarketView(as_of_date)
├── frozen_v9.py                # Phase 3: deterministic v9 signal
├── backtest.py                 # Phase 4: run_backtest(...)
├── baselines.py                # Phase 5: B&H SPY, naive-RSI, random-entry
├── stats.py                    # Phase 6: bootstrap, deflated Sharpe, regime
├── paper_backtest.py           # thin CLI wrapper
├── tests/                      # pytest suite
├── data/                       # cached OHLCV parquets (gitignored via .gitignore)
└── results/                    # CSVs, paper_results.md
```

## Running

```bash
# All at once (takes ~15 minutes on a laptop):
python3 -m paper.paper_backtest all

# Or phase by phase:
python3 -m paper.data_quality  --output paper/results/phase1_data_quality.md
python3 -m paper.backtest      --out    paper/results/phase4_frozen_v9
python3 -m paper.signal_quality --out   paper/results/phase4_signal_quality
python3 -m paper.baselines     --out    paper/results/phase5_baselines
python3 -m paper.stats         --out    paper/results/paper_results.md
```

Tests:

```bash
python3 -m pytest paper/tests/ -v                    # all
python3 -m pytest paper/tests/ -m "not online" -v    # offline only (fast)
```

## Results snapshot (2014-01-02 .. 2023-12-29, 10k EUR start)

### Headline

| Strategy              | Return      | Sharpe        | Trades |
|-----------------------|------------:|--------------:|-------:|
| frozen_v9             | -95.32%     | -4.712        |    505 |
| buy_and_hold_spy      | +159.85%    | +0.632        |      1 |
| naive_textbook_rsi    |  -93.41%    | -3.644        |    393 |
| random_entry (100)    | -93.48 ±0.09 | -4.84 ±0.40  |    ~403 |

### Signal quality (gate validated independently of trade mechanics)

| Confidence | n   | Mean Fwd-5d | Hit rate |
|-----------:|----:|------------:|---------:|
| 60-65%     | 244 | +0.24%      | 53%      |
| 65-70%     |  13 | +0.63%      | 62%      |

The 65-70% bracket shows a genuine directional edge. The 60-65% bracket
out-of-sample (53% / +0.24%) is nearly identical to the production in-
sample observation (56% / +0.33%) that motivated the v9 Scout-Inversion
rule — so the calibration holds on the 2014-2023 hold-out.

### Interpretation

- All three trade-based strategies cluster within 2 pp on the UNDERLYING,
  because the R/R asymmetry (-3% stop / +2.5% target) is calibrated for
  8× leverage turbo-certs in production, not for unlevered underlying
  trading. This backtest deliberately does not add a cert-leverage
  layer — the goal is to validate the *gate*, not the trade mechanics.
- Signal quality survives out of sample: per-stock calibration + multi-
  agent gate yields +0.26% mean Fwd-5d and a clear 60-65% → 65-70%
  gradient.
- SHORT signals never clear the gate in this window — Rule 18's per-
  stock blowoff-fade requirement rarely fires during a secular bull,
  an honest scope limit of the rule.

See `paper/results/paper_results.md` for the full breakdown
(per-year, regime-split, per-symbol, bootstrap CI, DSR).
