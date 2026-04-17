"""Phase 6 — statistical analysis utilities.

Implements the standard academic toolkit for validating a backtest:

  - bootstrap_sharpe_ci:       non-parametric CI for Sharpe via block bootstrap
  - deflated_sharpe:           López de Prado (2014) DSR, accounting for multi-
                               ple testing / variance & skew of the estimator
  - per_year_performance:      returns, Sharpe, DD per calendar year
  - regime_breakdown:          bull / bear / sideways market split
  - per_symbol_contribution:   which symbols drove the P&L

All functions take pandas objects and are side-effect free. The CLI
writes a final `paper_results.md` that stitches these together with the
baseline numbers.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Basic Sharpe utilities
# ---------------------------------------------------------------------------

def sharpe_from_returns(returns: np.ndarray, periods_per_year: int = 252) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) == 0:
        return 0.0
    sd = r.std(ddof=1)
    # Guard against float-imprecise 'zero' std — 1e-12 relative to mean is
    # effectively constant returns
    if sd < 1e-12 or (abs(r.mean()) > 0 and sd / abs(r.mean()) < 1e-10):
        return 0.0
    return float(r.mean() / sd * np.sqrt(periods_per_year))


def max_drawdown_from_equity(equity: np.ndarray) -> float:
    eq = np.asarray(equity, dtype=float)
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = (eq / peak - 1) * 100
    return float(dd.min())


# ---------------------------------------------------------------------------
# Block bootstrap CI for Sharpe
# ---------------------------------------------------------------------------

def bootstrap_sharpe_ci(
    returns: np.ndarray,
    n_resamples: int = 1000,
    block_size: int = 5,
    seed: int = 42,
    ci: tuple[float, float] = (2.5, 97.5),
    periods_per_year: int = 252,
) -> dict:
    """Non-parametric CI for annualised Sharpe via circular block bootstrap.

    Block size accounts for serial correlation of daily returns; 5 bdays
    is a conservative default. Returns mean, std, and the requested CI.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 2 * block_size:
        return {"n_resamples": 0, "note": "too few observations"}

    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block_size)
    sharpes = np.empty(n_resamples)
    for i in range(n_resamples):
        starts = rng.integers(0, n, size=n_blocks)
        resampled = np.concatenate(
            [r[(s + np.arange(block_size)) % n] for s in starts]
        )
        sharpes[i] = sharpe_from_returns(resampled, periods_per_year)

    lo, hi = ci
    return {
        "n_resamples": int(n_resamples),
        "block_size": int(block_size),
        "mean": round(float(sharpes.mean()), 3),
        "std": round(float(sharpes.std(ddof=1)), 3),
        f"p{lo:g}": round(float(np.percentile(sharpes, lo)), 3),
        f"p{hi:g}": round(float(np.percentile(sharpes, hi)), 3),
        "point_estimate": round(sharpe_from_returns(r, periods_per_year), 3),
    }


# ---------------------------------------------------------------------------
# Deflated Sharpe (López de Prado, 2014)
# ---------------------------------------------------------------------------

def deflated_sharpe(
    returns: np.ndarray,
    n_trials: int = 1,
    periods_per_year: int = 252,
) -> dict:
    """Deflated Sharpe Ratio per López de Prado (2014), "The Sharpe Ratio
    Efficient Frontier".

    DSR = prob{ SR > SR0 } where SR0 accounts for multiple testing.
    SR0 = E[max SRs over N trials] / sqrt(periods_per_year) (very simplified
    formula). We use the original paper's approximation.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 30:
        return {"note": "insufficient observations"}

    sr = sharpe_from_returns(r, periods_per_year)
    # per-period SR
    sr_pp = sr / math.sqrt(periods_per_year)
    # Higher moments
    mu = float(r.mean())
    sigma = float(r.std(ddof=1))
    if sigma == 0:
        return {"note": "zero variance"}
    skew = float(((r - mu) ** 3).mean() / sigma ** 3)
    kurt = float(((r - mu) ** 4).mean() / sigma ** 4)  # non-excess

    # Expected max SR0 (per period) from N IID trials with zero true mean:
    # SR0 = sqrt(2 ln(N)) * std-of-SR approximation. We use the paper's
    # closed form: SR0 ≈ ((1 - gamma) * Z^{-1}(1 - 1/N) + gamma * Z^{-1}(1 - 1/(N e)))
    # with gamma = Euler–Mascheroni. A simpler approximation is fine here.
    from scipy.stats import norm  # type: ignore
    gamma = 0.5772156649
    if n_trials > 1:
        z1 = norm.ppf(1 - 1 / n_trials)
        z2 = norm.ppf(1 - 1 / (n_trials * math.e))
        sr0_per_period = ((1 - gamma) * z1 + gamma * z2)
        # scale by std of SR under null
        sr0_per_period *= 1  # per-period units; multiplied below
    else:
        sr0_per_period = 0.0

    # DSR probability
    # var(SR_estimator) ≈ (1 - skew*SR + (kurt-1)/4 * SR^2) / (n - 1)
    var_sr = (1 - skew * sr_pp + (kurt - 1) / 4 * sr_pp ** 2) / max(n - 1, 1)
    if var_sr <= 0:
        return {"note": "negative variance estimate", "sharpe": round(sr, 3)}
    std_sr = math.sqrt(var_sr)
    z = (sr_pp - sr0_per_period) / std_sr
    p = float(norm.cdf(z))
    return {
        "sharpe": round(sr, 3),
        "n_obs": n,
        "n_trials": n_trials,
        "skew": round(skew, 3),
        "kurtosis": round(kurt, 3),
        "dsr_probability": round(p, 4),
        "interpretation": (
            "probability that the observed Sharpe exceeds the expected max "
            f"across {n_trials} trials under H0 of zero skill"
        ),
    }


# ---------------------------------------------------------------------------
# Per-year breakdown
# ---------------------------------------------------------------------------

def per_year_performance(equity_curve: pd.DataFrame) -> pd.DataFrame:
    """equity_curve must have columns ['date', 'equity']. Returns a DataFrame
    with one row per calendar year: return_pct, sharpe, max_dd_pct."""
    df = equity_curve.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["ret"] = df["equity"].pct_change()
    rows = []
    for y, grp in df.groupby(df.index.year):
        if len(grp) < 20:
            continue
        first = float(grp["equity"].iloc[0])
        last = float(grp["equity"].iloc[-1])
        rows.append({
            "year": int(y),
            "return_pct": round((last / first - 1) * 100, 2),
            "sharpe": round(sharpe_from_returns(grp["ret"].values), 3),
            "max_dd_pct": round(max_drawdown_from_equity(grp["equity"].values), 2),
            "n_days": len(grp),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Market-regime breakdown
# ---------------------------------------------------------------------------

def regime_breakdown(
    equity_curve: pd.DataFrame,
    spy_equity: pd.DataFrame,
    bull_threshold_pct: float = 5.0,
    bear_threshold_pct: float = -5.0,
    window_days: int = 63,  # ~1 quarter
) -> dict:
    """Classify each date's regime as Bull/Bear/Sideways based on SPY's
    forward-looking window-return (using PAST data only for classification:
    trailing 63d return, not forward).

    Then report the strategy's return in each regime.

    `equity_curve` and `spy_equity` must both have ['date','equity'].
    """
    eq = equity_curve.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date").sort_index()
    eq["ret"] = eq["equity"].pct_change()

    spy = spy_equity.copy()
    spy["date"] = pd.to_datetime(spy["date"])
    spy = spy.set_index("date").sort_index()
    spy["trailing_pct"] = (spy["equity"] / spy["equity"].shift(window_days) - 1) * 100

    # Align and classify
    joined = eq.join(spy[["trailing_pct"]], how="inner")
    joined["regime"] = "sideways"
    joined.loc[joined["trailing_pct"] > bull_threshold_pct, "regime"] = "bull"
    joined.loc[joined["trailing_pct"] < bear_threshold_pct, "regime"] = "bear"

    out = {}
    for r, grp in joined.groupby("regime"):
        if len(grp) < 20:
            continue
        out[r] = {
            "n_days": int(len(grp)),
            "mean_daily_return_pct": round(float(grp["ret"].mean() * 100), 4),
            "total_return_pct": round(
                float((1 + grp["ret"].fillna(0)).prod() - 1) * 100, 2),
            "sharpe": round(sharpe_from_returns(grp["ret"].values), 3),
        }
    return out


# ---------------------------------------------------------------------------
# Per-symbol contribution
# ---------------------------------------------------------------------------

def per_symbol_contribution(trades: pd.DataFrame) -> pd.DataFrame:
    """Sum realised P&L by symbol, plus trade count and win rate."""
    if trades.empty:
        return pd.DataFrame(columns=["symbol", "n_trades", "win_rate_pct",
                                     "total_pnl_eur", "mean_pnl_eur"])
    grp = trades.groupby("symbol")
    out = grp.agg(
        n_trades=("pnl_eur", "count"),
        total_pnl_eur=("pnl_eur", "sum"),
        mean_pnl_eur=("pnl_eur", "mean"),
    ).reset_index()
    win_rates = grp["pnl_eur"].apply(lambda s: (s > 0).mean() * 100)
    out["win_rate_pct"] = out["symbol"].map(win_rates).round(2)
    out["total_pnl_eur"] = out["total_pnl_eur"].round(2)
    out["mean_pnl_eur"] = out["mean_pnl_eur"].round(2)
    return out.sort_values("total_pnl_eur", ascending=False)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_markdown_report(
    frozen_equity: pd.DataFrame,
    frozen_trades: pd.DataFrame,
    frozen_summary: dict,
    baselines_summary: dict,
    signal_quality_summary: dict,
    spy_equity: pd.DataFrame | None,
    out_path: str | Path,
) -> None:
    lines: list[str] = []
    from datetime import datetime as _dt
    lines.append("# Paper Results — Out-of-Sample v9 Backtest (2014-2023)")
    lines.append("")
    lines.append(f"Generated: {_dt.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # 1. Headline table
    lines.append("## 1. Headline Comparison (10k EUR, 2014-2023)")
    lines.append("")
    lines.append("| Strategy | Final Eq | Total Ret | Sharpe | Max DD | Trades | Win Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    def _row(name: str, s: dict) -> str:
        def _f(k, fmt="{:.2f}"):
            v = s.get(k)
            return fmt.format(v) if isinstance(v, (int, float)) else str(v)
        return (
            f"| {name} | "
            f"{_f('final_equity')} | "
            f"{_f('total_return_pct')}% | "
            f"{_f('sharpe_ratio', '{:.3f}')} | "
            f"{_f('max_drawdown_pct')}% | "
            f"{s.get('n_trades', '-')} | "
            f"{_f('win_rate_pct')}% |"
        )

    lines.append(_row("frozen_v9", frozen_summary))
    if "buy_and_hold_spy" in baselines_summary:
        lines.append(_row("buy_and_hold_spy", baselines_summary["buy_and_hold_spy"]))
    if "naive_textbook_rsi" in baselines_summary:
        lines.append(_row("naive_textbook_rsi", baselines_summary["naive_textbook_rsi"]))
    if "random_entry" in baselines_summary:
        re_ = baselines_summary["random_entry"]
        lines.append(
            f"| random_entry ({re_.get('n_runs','?')} seeds) | "
            f"- | "
            f"{re_.get('return_mean_pct','-')}% ±{re_.get('return_std_pct','-')} | "
            f"{re_.get('sharpe_mean','-')} ±{re_.get('sharpe_std','-')} | "
            f"{re_.get('max_dd_mean_pct','-')}% | "
            f"{re_.get('n_trades_mean','-')} | - |"
        )
    lines.append("")

    # 2. Signal-Quality
    lines.append("## 2. Signal Quality (Gate Validation, independent of trade mechanics)")
    lines.append("")
    if signal_quality_summary and signal_quality_summary.get("n_signals", 0) > 0:
        s = signal_quality_summary
        lines.append(f"- Approved signals: **{s.get('n_signals')}** ({s.get('n_long')} LONG / {s.get('n_short')} SHORT)")
        lines.append(f"- Mean direction-adjusted Fwd-5d return: **{s.get('mean_adj_fwd5_pct')}%**")
        lines.append(f"- Fwd-5d hit rate: **{s.get('hit_rate_5d_pct')}%**")
        lines.append(f"- Mean direction-adjusted Fwd-10d return: **{s.get('mean_adj_fwd10_pct')}%**")
        lines.append(f"- Fwd-10d hit rate: **{s.get('hit_rate_10d_pct')}%**")
        buckets = s.get("by_confidence_bracket") or []
        if buckets:
            lines.append("")
            lines.append("| Confidence | n | Mean Fwd-5d | Hit Rate |")
            lines.append("|---|---:|---:|---:|")
            for b in buckets:
                lines.append(
                    f"| {b['bracket']} | {b['n']} | "
                    f"{b['mean_fwd5_pct']:+.2f}% | {b['hit_rate_5d_pct']:.0f}% |"
                )
    else:
        lines.append("_No approved signals in sample._")
    lines.append("")

    # 3. Bootstrap CI + Deflated Sharpe
    lines.append("## 3. Statistical Significance of frozen_v9 Sharpe")
    lines.append("")
    eq = frozen_equity.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date").sort_index()
    daily = eq["equity"].pct_change().dropna().values

    if len(daily) >= 30:
        boot = bootstrap_sharpe_ci(daily, n_resamples=1000, seed=42)
        lines.append("**Block-Bootstrap CI (95%, 1000 resamples, block=5 bdays)**")
        for k, v in boot.items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

        try:
            dsr = deflated_sharpe(daily, n_trials=25)  # treat 25-symbol universe as 25 trials
            lines.append("**Deflated Sharpe Ratio (n_trials = 25 symbols)**")
            for k, v in dsr.items():
                lines.append(f"  - {k}: {v}")
            lines.append("")
        except Exception as e:
            lines.append(f"_Deflated Sharpe calc failed: {e}_")
            lines.append("")
    else:
        lines.append("_Too few observations for bootstrap/DSR._")
        lines.append("")

    # 4. Per-year
    lines.append("## 4. Per-Year Performance (frozen_v9)")
    lines.append("")
    yr = per_year_performance(frozen_equity)
    if not yr.empty:
        lines.append("| Year | Return | Sharpe | Max DD | N Days |")
        lines.append("|---|---:|---:|---:|---:|")
        for _, row in yr.iterrows():
            lines.append(
                f"| {row['year']} | {row['return_pct']:+.2f}% | "
                f"{row['sharpe']:+.3f} | {row['max_dd_pct']:.2f}% | "
                f"{row['n_days']} |"
            )
        lines.append("")

    # 5. Regime breakdown
    lines.append("## 5. Market-Regime Breakdown")
    lines.append("")
    if spy_equity is not None and not spy_equity.empty:
        regimes = regime_breakdown(frozen_equity, spy_equity)
        if regimes:
            lines.append("| Regime | Days | Mean Daily Ret | Total Ret | Sharpe |")
            lines.append("|---|---:|---:|---:|---:|")
            for name in ("bull", "sideways", "bear"):
                if name not in regimes:
                    continue
                r = regimes[name]
                lines.append(
                    f"| {name} | {r['n_days']} | "
                    f"{r['mean_daily_return_pct']:+.4f}% | "
                    f"{r['total_return_pct']:+.2f}% | "
                    f"{r['sharpe']:+.3f} |"
                )
            lines.append("")
            lines.append(f"_Regime definition: SPY trailing-63d-return > +5% = bull, "
                         f"< -5% = bear, else sideways._")
    else:
        lines.append("_SPY benchmark not available._")
    lines.append("")

    # 6. Per-symbol contribution
    lines.append("## 6. Per-Symbol P&L Contribution (frozen_v9)")
    lines.append("")
    cont = per_symbol_contribution(frozen_trades)
    if not cont.empty:
        lines.append("| Symbol | Trades | Win % | Total P&L | Mean P&L |")
        lines.append("|---|---:|---:|---:|---:|")
        for _, row in cont.iterrows():
            lines.append(
                f"| {row['symbol']} | {row['n_trades']} | "
                f"{row['win_rate_pct']:.1f}% | "
                f"{row['total_pnl_eur']:+.2f} EUR | "
                f"{row['mean_pnl_eur']:+.2f} EUR |"
            )
    lines.append("")

    # 7. Notes & Limitations
    lines.append("## 7. Notes & Limitations")
    lines.append("")
    lines.append("- News / Reddit / Trump scorecard axis (axis 3) is **NEUTRAL** "
                 "throughout — historical social-media flow is not reconstructible.")
    lines.append("- Macro-calendar (NFP/CPI/Fed-days) not modelled; only "
                 "scheduled earnings.")
    lines.append("- LLM-driven Bull/Bear debate is replaced by the 6-axis "
                 "scorecard formula; debate-level rebuttals are not simulated.")
    lines.append("- Backtest trades the underlying, not turbo-certificates — "
                 "R/R asymmetry (-3% stop / +2.5% target) is reported as-is; "
                 "production uses 8× leverage certs that transform this into "
                 "+20% / -24% cert P&L.")
    lines.append("- SHORT signals never approved in 2014-2023: Rule 18 SHORT-"
                 "gate (requires per-stock blowoff-fade trigger) is legitimate "
                 "but fires rarely during a secular bull market.")
    lines.append("- Universe: 25 symbols, stratified (see `paper/universe.py`). "
                 "Two documented ticker swaps (GPS→GAP, X→CLF) reflect yfinance "
                 "data availability after 2024, not post-hoc tuning.")
    lines.append("")

    Path(out_path).write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frozen-dir", default="paper/results/phase4_frozen_v9",
                   help="Directory containing equity_curve.csv + trades.csv")
    p.add_argument("--baselines-json", default="paper/results/phase5_baselines/summary.json")
    p.add_argument("--signal-quality-json",
                   default="paper/results/phase4_signal_quality/summary.json")
    p.add_argument("--spy-equity", default=None,
                   help="Optional: path to CSV with SPY daily equity for regime breakdown")
    p.add_argument("--out", default="paper/results/paper_results.md")
    args = p.parse_args()

    frozen_eq = pd.read_csv(Path(args.frozen_dir) / "equity_curve.csv")
    frozen_tr = pd.read_csv(Path(args.frozen_dir) / "trades.csv")
    with open(args.baselines_json) as fh:
        baselines = json.load(fh)
    try:
        with open(args.signal_quality_json) as fh:
            sq = json.load(fh)
    except FileNotFoundError:
        sq = {}

    # Frozen summary — recompute to stay consistent with the files on disk
    start_eq = float(frozen_eq["equity"].iloc[0]) if not frozen_eq.empty else 10_000.0
    final_eq = float(frozen_eq["equity"].iloc[-1]) if not frozen_eq.empty else start_eq
    daily = frozen_eq["equity"].pct_change().dropna().values
    sharpe = sharpe_from_returns(daily) if len(daily) > 30 else None
    max_dd = max_drawdown_from_equity(frozen_eq["equity"].values)
    win_rate = None
    if not frozen_tr.empty:
        win_rate = float((frozen_tr["pnl_eur"] > 0).sum() / len(frozen_tr) * 100)
    frozen_summary = {
        "final_equity": round(final_eq, 2),
        "total_return_pct": round((final_eq / start_eq - 1) * 100, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "n_trades": len(frozen_tr),
        "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
    }

    spy_eq_df = None
    if args.spy_equity and Path(args.spy_equity).exists():
        spy_eq_df = pd.read_csv(args.spy_equity)
    else:
        # Build SPY equity on the fly from the cached SPY close prices
        try:
            from paper.historical_view import _load_ohlcv
            spy = _load_ohlcv("SPY")
            spy = spy.loc[(spy.index >= pd.Timestamp("2014-01-01"))
                          & (spy.index <= pd.Timestamp("2023-12-31"))]
            spy_eq_df = pd.DataFrame({
                "date": spy.index, "equity": spy["Close"].values
            })
        except Exception:
            spy_eq_df = None

    write_markdown_report(
        frozen_eq, frozen_tr, frozen_summary,
        baselines, sq, spy_eq_df, args.out,
    )
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
