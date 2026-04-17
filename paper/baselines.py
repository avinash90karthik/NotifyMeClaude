"""Phase 5 — baseline strategies for comparison.

Three baselines that run on the exact same universe and window as
frozen_v9, with the same cost model and position sizing where feasible:

  1. Buy-and-Hold SPY  — the simplest possible baseline.
  2. Naive Textbook-RSI — enter LONG when RSI14 < 30, exit when RSI14 > 50.
     No per-stock calibration, no gate, no vetos. Same stop/target/cost
     structure as frozen_v9 for comparability.
  3. Random-entry Control — on each day pick a symbol uniformly at random
     from the universe, enter with the same sizing and exit rules as
     frozen_v9. Run N times with different seeds and report mean/std of
     the performance metrics. This controls for "any system with stops
     might outperform B&H in a specific period".

All three use the same HistoricalMarketView / OHLCV pipeline — no
lookahead is possible.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from paper.backtest import Backtest, BacktestConfig, OpenPosition, ClosedTrade
from paper.historical_view import HistoricalMarketView, _load_ohlcv
from paper.frozen_v9 import _rsi_wilder
from paper.universe import symbols as universe_symbols, BACKTEST_START, BACKTEST_END


# ---------------------------------------------------------------------------
# 1. Buy-and-Hold SPY
# ---------------------------------------------------------------------------

def buy_and_hold_spy(
    start: str = BACKTEST_START,
    end: str = BACKTEST_END,
    initial_capital: float = 10_000.0,
) -> dict:
    """Return summary metrics for a simple buy-and-hold of SPY."""
    df = _load_ohlcv("SPY")
    df = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]
    if df.empty:
        raise RuntimeError("SPY cache empty — add SPY to Phase 1 fetch or re-run data_quality")
    start_px = float(df["Close"].iloc[0])
    end_px = float(df["Close"].iloc[-1])
    shares = initial_capital / start_px
    final_equity = shares * end_px
    total_return = (final_equity / initial_capital - 1) * 100

    # Daily returns for Sharpe/DD
    daily = df["Close"].pct_change().dropna()
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else None
    equity = initial_capital * (df["Close"] / start_px)
    peak = equity.cummax()
    dd = (equity / peak - 1) * 100
    max_dd = float(dd.min())

    return {
        "strategy": "buy_and_hold_spy",
        "start_equity": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "n_trades": 1,
        "win_rate_pct": None,
        "avg_hold_days": None,
    }


# ---------------------------------------------------------------------------
# 2. Naive textbook RSI baseline
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NaiveRSISignal:
    symbol: str
    direction: str       # always LONG in the classic setup
    close: float
    rsi: float


def _naive_rsi_approved(
    view: HistoricalMarketView, symbol: str, rsi_entry: float, rsi_exit: float
) -> NaiveRSISignal | None:
    """Classic RSI mean-reversion entry: RSI14 < rsi_entry."""
    try:
        snap = view.get_indicators(symbol)
    except Exception:
        return None
    if snap is None or snap.rsi14 is None or snap.atr_pct is None:
        return None
    if snap.rsi14 >= rsi_entry:
        return None
    # ATR > 7% veto retained for fair comparison (same V1 the frozen_v9 uses)
    if snap.atr_pct > 7.0:
        return None
    return NaiveRSISignal(symbol=symbol, direction="LONG",
                          close=snap.price, rsi=snap.rsi14)


def naive_rsi_backtest(
    start: str = BACKTEST_START,
    end: str = BACKTEST_END,
    initial_capital: float = 10_000.0,
    rsi_entry: float = 30.0,
    rsi_exit: float = 50.0,
    position_pct: float = 15.0,
) -> dict:
    """Classic textbook RSI: enter LONG when RSI<30, exit when RSI>50.

    Same cost model and slot cap as frozen_v9. Fixed 15% sizing (matches
    the low-confidence production bracket size). No per-stock cali-
    bration, no multi-agent gate — just RSI14 thresholds.
    """
    cfg = BacktestConfig(
        start=start, end=end, initial_capital=initial_capital,
    )
    universe = universe_symbols()

    cash = initial_capital
    positions: list[OpenPosition] = []
    closed: list[ClosedTrade] = []
    equity_curve: list[tuple[pd.Timestamp, float]] = []

    # Pre-compute trading day union (same as Backtest)
    union = pd.DatetimeIndex([])
    for s in universe:
        try:
            df = _load_ohlcv(s)
        except Exception:
            continue
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        union = union.union(df.loc[mask].index)
    days = union.sort_values()

    from paper.universe import UNIVERSE as _UNI
    symbol_bucket = {e.symbol: e.bucket for e in _UNI}

    def _mtm(view: HistoricalMarketView) -> float:
        eq = cash
        for p in positions:
            px = view.last_close(p.symbol)
            if px is None:
                px = p.entry_price
            eq += p.shares * px
        return eq

    for day in days:
        view = HistoricalMarketView(day)

        # Exits first: stop / target / RSI exit condition
        still_open: list[OpenPosition] = []
        for p in positions:
            df = _load_ohlcv(p.symbol)
            if p.entry_date >= view.as_of or day not in df.index:
                still_open.append(p)
                continue
            bar = df.loc[day]
            high = float(bar["High"])
            low = float(bar["Low"])
            close = float(bar["Close"])

            hit_stop = low <= p.stop_price
            hit_target = high >= p.target_price
            # RSI exit condition on today's close
            snap = view.get_indicators(p.symbol)
            rsi_exit_hit = (snap is not None and snap.rsi14 is not None
                            and snap.rsi14 > rsi_exit)
            reason = None
            exit_px = None
            if hit_stop:
                reason, exit_px = "stop", p.stop_price
            elif hit_target:
                reason, exit_px = "target", p.target_price
            elif rsi_exit_hit:
                reason, exit_px = "rsi_exit", close

            if reason is None:
                still_open.append(p)
                continue

            fill = exit_px * (1 - cfg.slippage_pct - cfg.spread_pct / 2)
            gross = p.shares * fill
            pnl_eur = gross - p.size_eur - cfg.fixed_order_cost
            cash += gross - cfg.fixed_order_cost
            closed.append(ClosedTrade(
                symbol=p.symbol, bucket=p.bucket, direction=p.direction,
                entry_date=str(p.entry_date.date()),
                exit_date=str(day.date()),
                entry_price=round(p.entry_price, 4),
                exit_price=round(fill, 4),
                shares=round(p.shares, 4),
                pnl_eur=round(pnl_eur, 2),
                pnl_pct=round(pnl_eur / p.size_eur * 100, 3),
                exit_reason=reason,
                hold_days=int((day - p.entry_date).days),
                entry_confidence=0.0,
                size_eur_at_entry=round(p.size_eur, 2),
            ))

        positions = still_open

        equity = _mtm(view)

        # Entries
        for sym in universe:
            if len(positions) >= cfg.max_open_positions:
                break
            if any(p.symbol == sym for p in positions):
                continue
            sig = _naive_rsi_approved(view, sym, rsi_entry, rsi_exit)
            if sig is None:
                continue
            nxt = view.next_open(sym)
            if nxt is None:
                continue
            fill_date, next_open = nxt
            fill_price = next_open * (1 + cfg.slippage_pct + cfg.spread_pct / 2)
            size_eur = min(equity * position_pct / 100, cash * 0.95)
            if size_eur < 100:
                continue
            shares = size_eur / fill_price
            if shares <= 0:
                continue
            cash -= size_eur + cfg.fixed_order_cost
            # Naive stop at -3%, target at +2.5% — match frozen_v9 target
            # so the comparison is fair on the exit side.
            stop = fill_price * 0.97
            target = fill_price * 1.025
            positions.append(OpenPosition(
                symbol=sym,
                bucket=symbol_bucket.get(sym, "unknown"),
                direction="LONG",
                entry_date=fill_date,
                entry_price=fill_price,
                shares=shares,
                stop_price=stop,
                target_price=target,
                size_eur=size_eur,
                entry_confidence=0.0,
            ))

        equity_curve.append((day, _mtm(view)))

    eq_df = pd.DataFrame(equity_curve, columns=["date", "equity"])
    trades_df = pd.DataFrame([asdict(t) for t in closed])
    daily = eq_df["equity"].pct_change().dropna()
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if len(daily) > 30 and daily.std() > 0 else None
    peak = eq_df["equity"].cummax()
    dd = (eq_df["equity"] / peak - 1) * 100
    max_dd = float(dd.min()) if not dd.empty else 0.0
    final = float(eq_df["equity"].iloc[-1]) if not eq_df.empty else initial_capital
    win_rate = None
    avg_hold = None
    if not trades_df.empty:
        win_rate = float((trades_df["pnl_eur"] > 0).sum() / len(trades_df) * 100)
        avg_hold = float(trades_df["hold_days"].mean())
    return {
        "strategy": "naive_textbook_rsi",
        "start_equity": initial_capital,
        "final_equity": round(final, 2),
        "total_return_pct": round((final / initial_capital - 1) * 100, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "n_trades": len(trades_df),
        "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
        "avg_hold_days": round(avg_hold, 2) if avg_hold is not None else None,
        "_equity_curve": eq_df,
        "_trades": trades_df,
    }


# ---------------------------------------------------------------------------
# 3. Random-entry control
# ---------------------------------------------------------------------------

def random_entry_backtest(
    start: str = BACKTEST_START,
    end: str = BACKTEST_END,
    initial_capital: float = 10_000.0,
    entry_probability: float = 0.20,
    position_pct: float = 15.0,
    seed: int = 0,
) -> dict:
    """Random-entry baseline.

    On every trading day, with probability `entry_probability`, pick a
    random symbol from the universe and enter a LONG with the same
    sizing and exit rules as frozen_v9 (stop = -3%, target = +2.5%,
    max_hold = 10 days).

    `entry_probability` is calibrated so that the total trade count
    roughly matches frozen_v9 (which took ~505 trades over 2014-2023).
    The 3-slot cap bounds how many of the triggered entries actually
    fill; empirically p≈0.20 per trading day produces ~500 filled
    trades across the 10-year window.
    """
    cfg = BacktestConfig(
        start=start, end=end, initial_capital=initial_capital,
    )
    universe = universe_symbols()
    rng = np.random.default_rng(seed)

    cash = initial_capital
    positions: list[OpenPosition] = []
    closed: list[ClosedTrade] = []
    equity_curve: list[tuple[pd.Timestamp, float]] = []

    union = pd.DatetimeIndex([])
    for s in universe:
        try:
            df = _load_ohlcv(s)
        except Exception:
            continue
        mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
        union = union.union(df.loc[mask].index)
    days = union.sort_values()

    from paper.universe import UNIVERSE as _UNI
    symbol_bucket = {e.symbol: e.bucket for e in _UNI}

    def _mtm(view: HistoricalMarketView) -> float:
        eq = cash
        for p in positions:
            px = view.last_close(p.symbol)
            if px is None:
                px = p.entry_price
            eq += p.shares * px
        return eq

    for day in days:
        view = HistoricalMarketView(day)

        # Exits: stop / target / max-hold
        still_open: list[OpenPosition] = []
        for p in positions:
            df = _load_ohlcv(p.symbol)
            if p.entry_date >= view.as_of or day not in df.index:
                still_open.append(p)
                continue
            bar = df.loc[day]
            high = float(bar["High"])
            low = float(bar["Low"])
            close = float(bar["Close"])
            hold_days = int((day - p.entry_date).days)
            reason = None
            exit_px = None
            if low <= p.stop_price:
                reason, exit_px = "stop", p.stop_price
            elif high >= p.target_price:
                reason, exit_px = "target", p.target_price
            elif hold_days >= cfg.max_hold_days:
                reason, exit_px = "max_hold", close
            if reason is None:
                still_open.append(p)
                continue
            fill = exit_px * (1 - cfg.slippage_pct - cfg.spread_pct / 2)
            gross = p.shares * fill
            pnl_eur = gross - p.size_eur - cfg.fixed_order_cost
            cash += gross - cfg.fixed_order_cost
            closed.append(ClosedTrade(
                symbol=p.symbol, bucket=p.bucket, direction="LONG",
                entry_date=str(p.entry_date.date()),
                exit_date=str(day.date()),
                entry_price=round(p.entry_price, 4),
                exit_price=round(fill, 4),
                shares=round(p.shares, 4),
                pnl_eur=round(pnl_eur, 2),
                pnl_pct=round(pnl_eur / p.size_eur * 100, 3),
                exit_reason=reason,
                hold_days=hold_days,
                entry_confidence=0.0,
                size_eur_at_entry=round(p.size_eur, 2),
            ))
        positions = still_open

        equity = _mtm(view)

        # Random entry
        if (rng.random() < entry_probability
                and len(positions) < cfg.max_open_positions):
            sym = universe[int(rng.integers(0, len(universe)))]
            if not any(p.symbol == sym for p in positions):
                nxt = view.next_open(sym)
                if nxt is not None:
                    fill_date, next_open = nxt
                    fill_price = next_open * (1 + cfg.slippage_pct + cfg.spread_pct / 2)
                    size_eur = min(equity * position_pct / 100, cash * 0.95)
                    if size_eur >= 100:
                        shares = size_eur / fill_price
                        cash -= size_eur + cfg.fixed_order_cost
                        positions.append(OpenPosition(
                            symbol=sym,
                            bucket=symbol_bucket.get(sym, "unknown"),
                            direction="LONG",
                            entry_date=fill_date,
                            entry_price=fill_price,
                            shares=shares,
                            stop_price=fill_price * 0.97,
                            target_price=fill_price * 1.025,
                            size_eur=size_eur,
                            entry_confidence=0.0,
                        ))

        equity_curve.append((day, _mtm(view)))

    eq_df = pd.DataFrame(equity_curve, columns=["date", "equity"])
    trades_df = pd.DataFrame([asdict(t) for t in closed])
    daily = eq_df["equity"].pct_change().dropna()
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if len(daily) > 30 and daily.std() > 0 else None
    peak = eq_df["equity"].cummax()
    dd = (eq_df["equity"] / peak - 1) * 100
    max_dd = float(dd.min()) if not dd.empty else 0.0
    final = float(eq_df["equity"].iloc[-1]) if not eq_df.empty else initial_capital
    return {
        "strategy": f"random_seed_{seed}",
        "seed": seed,
        "start_equity": initial_capital,
        "final_equity": round(final, 2),
        "total_return_pct": round((final / initial_capital - 1) * 100, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown_pct": round(max_dd, 2),
        "n_trades": len(trades_df),
    }


def random_entry_aggregate(n_runs: int = 100, **kwargs) -> dict:
    """Run the random baseline N times with different seeds; return stats."""
    runs = [random_entry_backtest(seed=s, **kwargs) for s in range(n_runs)]
    sharpes = np.array([r["sharpe_ratio"] or 0.0 for r in runs])
    returns = np.array([r["total_return_pct"] for r in runs])
    dds = np.array([r["max_drawdown_pct"] for r in runs])
    ns = np.array([r["n_trades"] for r in runs])
    return {
        "strategy": f"random_entry_{n_runs}runs",
        "n_runs": n_runs,
        "sharpe_mean": round(float(sharpes.mean()), 3),
        "sharpe_std": round(float(sharpes.std(ddof=1)), 3),
        "sharpe_p5": round(float(np.percentile(sharpes, 5)), 3),
        "sharpe_p95": round(float(np.percentile(sharpes, 95)), 3),
        "return_mean_pct": round(float(returns.mean()), 2),
        "return_std_pct": round(float(returns.std(ddof=1)), 2),
        "max_dd_mean_pct": round(float(dds.mean()), 2),
        "n_trades_mean": round(float(ns.mean()), 1),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=BACKTEST_START)
    p.add_argument("--end", default=BACKTEST_END)
    p.add_argument("--capital", type=float, default=10_000.0)
    p.add_argument("--random-runs", type=int, default=100)
    p.add_argument("--out", default="paper/results/phase5_baselines")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = {}
    print("→ Running Buy-and-Hold SPY...", flush=True)
    try:
        results["buy_and_hold_spy"] = buy_and_hold_spy(args.start, args.end, args.capital)
    except Exception as e:
        print(f"  (SPY cache not available; downloading or skipping: {e})")
        # Attempt to populate SPY cache once
        try:
            _load_ohlcv("SPY")
            results["buy_and_hold_spy"] = buy_and_hold_spy(args.start, args.end, args.capital)
        except Exception as e2:
            results["buy_and_hold_spy"] = {"error": str(e2)}

    print("→ Running Naive Textbook-RSI...", flush=True)
    naive = naive_rsi_backtest(args.start, args.end, args.capital)
    naive_out = {k: v for k, v in naive.items() if not k.startswith("_")}
    # Persist the curves as CSV for later plotting
    naive["_equity_curve"].to_csv(out / "naive_rsi_equity.csv", index=False)
    naive["_trades"].to_csv(out / "naive_rsi_trades.csv", index=False)
    results["naive_textbook_rsi"] = naive_out

    print(f"→ Running Random-Entry Control ({args.random_runs} seeds)...", flush=True)
    results["random_entry"] = random_entry_aggregate(
        n_runs=args.random_runs, start=args.start, end=args.end,
        initial_capital=args.capital,
    )

    (out / "summary.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n--- Baselines Summary ---")
    for name, r in results.items():
        print(f"\n[{name}]")
        for k, v in r.items():
            print(f"  {k:24s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
