# Paper Results — Out-of-Sample v9 Backtest (2014-2023)

Generated: 2026-04-17 06:39 UTC

## 1. Headline Comparison (10k EUR, 2014-2023)

| Strategy | Final Eq | Total Ret | Sharpe | Max DD | Trades | Win Rate |
|---|---:|---:|---:|---:|---:|---:|
| frozen_v9 | 468.21 | -95.32% | -4.712 | -95.32% | 505 | 15.64% |
| buy_and_hold_spy | 25984.58 | 159.85% | 0.632 | -34.10% | 1 | None% |
| naive_textbook_rsi | 658.58 | -93.41% | -3.644 | -93.44% | 393 | 35.37% |
| random_entry (100 seeds) | - | -93.48% ±0.09 | -4.836 ±0.402 | -93.49% | 403.4 | - |

## 2. Signal Quality (Gate Validation, independent of trade mechanics)

- Approved signals: **257** (257 LONG / 0 SHORT)
- Mean direction-adjusted Fwd-5d return: **0.256%**
- Fwd-5d hit rate: **53.31%**
- Mean direction-adjusted Fwd-10d return: **0.552%**
- Fwd-10d hit rate: **54.09%**

| Confidence | n | Mean Fwd-5d | Hit Rate |
|---|---:|---:|---:|
| 60-65% | 244 | +0.24% | 53% |
| 65-70% | 13 | +0.63% | 62% |

## 3. Statistical Significance of frozen_v9 Sharpe

**Block-Bootstrap CI (95%, 1000 resamples, block=5 bdays)**
  - n_resamples: 1000
  - block_size: 5
  - mean: -4.725
  - std: 0.197
  - p2.5: -5.132
  - p97.5: -4.35
  - point_estimate: -4.712

**Deflated Sharpe Ratio (n_trials = 25 symbols)**
  - sharpe: -4.712
  - n_obs: 2583
  - n_trials: 25
  - skew: -4.767
  - kurtosis: 35.583
  - dsr_probability: 0.0
  - interpretation: probability that the observed Sharpe exceeds the expected max across 25 trials under H0 of zero skill

## 4. Per-Year Performance (frozen_v9)

| Year | Return | Sharpe | Max DD | N Days |
|---|---:|---:|---:|---:|
| 2014.0 | -12.97% | -4.175 | -12.97% | 258.0 |
| 2015.0 | -15.58% | -5.066 | -15.91% | 259.0 |
| 2016.0 | -18.26% | -4.816 | -18.26% | 258.0 |
| 2017.0 | -30.05% | -7.679 | -30.05% | 258.0 |
| 2018.0 | -30.70% | -7.154 | -30.70% | 258.0 |
| 2019.0 | -47.96% | -9.039 | -48.03% | 259.0 |
| 2020.0 | -68.38% | -7.608 | -68.38% | 259.0 |
| 2021.0 | +0.00% | +0.000 | 0.00% | 259.0 |
| 2022.0 | +0.00% | +0.000 | 0.00% | 258.0 |
| 2023.0 | +0.00% | +0.000 | 0.00% | 258.0 |

## 5. Market-Regime Breakdown

| Regime | Days | Mean Daily Ret | Total Ret | Sharpe |
|---|---:|---:|---:|---:|
| bull | 876 | -0.1647% | -76.67% | -5.272 |
| sideways | 1346 | -0.0957% | -72.58% | -4.861 |
| bear | 294 | -0.1018% | -26.08% | -3.717 |

_Regime definition: SPY trailing-63d-return > +5% = bull, < -5% = bear, else sideways._

## 6. Per-Symbol P&L Contribution (frozen_v9)

| Symbol | Trades | Win % | Total P&L | Mean P&L |
|---|---:|---:|---:|---:|
| SHEL.L | 2 | 0.0% | -13.70 EUR | -6.85 EUR |
| F | 2 | 0.0% | -15.91 EUR | -7.96 EUR |
| CLF | 8 | 25.0% | -21.69 EUR | -2.71 EUR |
| RRC | 2 | 0.0% | -33.87 EUR | -16.93 EUR |
| BA | 14 | 35.7% | -55.05 EUR | -3.93 EUR |
| XOM | 8 | 12.5% | -62.49 EUR | -7.81 EUR |
| SI=F | 4 | 0.0% | -87.09 EUR | -21.77 EUR |
| NESN.SW | 10 | 0.0% | -92.05 EUR | -9.20 EUR |
| GC=F | 11 | 0.0% | -94.38 EUR | -8.58 EUR |
| MOS | 12 | 16.7% | -100.86 EUR | -8.40 EUR |
| GOOGL | 13 | 15.4% | -108.88 EUR | -8.38 EUR |
| CL=F | 11 | 18.2% | -141.10 EUR | -12.83 EUR |
| V | 17 | 5.9% | -142.37 EUR | -8.37 EUR |
| JPM | 15 | 6.7% | -143.50 EUR | -9.57 EUR |
| JNJ | 22 | 13.6% | -150.01 EUR | -6.82 EUR |
| MSFT | 22 | 4.5% | -155.18 EUR | -7.05 EUR |
| GPRO | 4 | 0.0% | -210.76 EUR | -52.69 EUR |
| ASML.AS | 43 | 27.9% | -246.81 EUR | -5.74 EUR |
| GAP | 21 | 19.1% | -252.43 EUR | -12.02 EUR |
| SAP.DE | 22 | 13.6% | -305.39 EUR | -13.88 EUR |
| AMZN | 44 | 15.9% | -318.65 EUR | -7.24 EUR |
| META | 20 | 5.0% | -321.18 EUR | -16.06 EUR |
| MC.PA | 54 | 13.0% | -356.18 EUR | -6.60 EUR |
| AAPL | 58 | 17.2% | -397.90 EUR | -6.86 EUR |
| NVDA | 66 | 22.7% | -654.34 EUR | -9.91 EUR |

## 7. Notes & Limitations

- News / Reddit / Trump scorecard axis (axis 3) is **NEUTRAL** throughout — historical social-media flow is not reconstructible.
- Macro-calendar (NFP/CPI/Fed-days) not modelled; only scheduled earnings.
- LLM-driven Bull/Bear debate is replaced by the 6-axis scorecard formula; debate-level rebuttals are not simulated.
- Backtest trades the underlying, not turbo-certificates — R/R asymmetry (-3% stop / +2.5% target) is reported as-is; production uses 8× leverage certs that transform this into +20% / -24% cert P&L.
- SHORT signals never approved in 2014-2023: Rule 18 SHORT-gate (requires per-stock blowoff-fade trigger) is legitimate but fires rarely during a secular bull market.
- Universe: 25 symbols, stratified (see `paper/universe.py`). Two documented ticker swaps (GPS→GAP, X→CLF) reflect yfinance data availability after 2024, not post-hoc tuning.

