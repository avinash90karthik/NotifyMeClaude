"""Thin CLI entry point that runs all phases end-to-end.

Usage:
  python3 -m paper.paper_backtest all
  python3 -m paper.paper_backtest phase1
  python3 -m paper.paper_backtest phase4
  ...

This is a convenience wrapper. Each phase can still be invoked directly
via its own module (python3 -m paper.data_quality, paper.backtest, ...).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(mod: str, *args: str) -> int:
    cmd = [sys.executable, "-m", mod, *args]
    print(f"\n$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "phase",
        choices=["phase1", "phase3", "phase4", "phase5", "phase6", "all"],
        help="Which phase to run (or 'all')",
    )
    p.add_argument("--capital", type=float, default=10_000.0)
    p.add_argument("--random-runs", type=int, default=100)
    args = p.parse_args()

    steps: list[tuple[str, list[str]]] = []
    if args.phase in ("phase1", "all"):
        steps.append(("paper.data_quality",
                      ["--output", "paper/results/phase1_data_quality.md"]))
    if args.phase in ("phase3", "all"):
        # Phase 3 is a pure library; its tests are the executable step
        steps.append(("pytest", ["paper/tests/test_frozen_v9.py", "-q"]))
    if args.phase in ("phase4", "all"):
        steps.append(("paper.backtest",
                      ["--capital", str(args.capital),
                       "--out", "paper/results/phase4_frozen_v9"]))
        steps.append(("paper.signal_quality",
                      ["--cadence-days", "5",
                       "--out", "paper/results/phase4_signal_quality"]))
    if args.phase in ("phase5", "all"):
        steps.append(("paper.baselines",
                      ["--capital", str(args.capital),
                       "--random-runs", str(args.random_runs),
                       "--out", "paper/results/phase5_baselines"]))
    if args.phase in ("phase6", "all"):
        steps.append(("paper.stats",
                      ["--out", "paper/results/paper_results.md"]))

    rc = 0
    for mod, modargs in steps:
        if mod == "pytest":
            r = subprocess.call([sys.executable, "-m", "pytest", *modargs])
        else:
            r = _run(mod, *modargs)
        if r != 0:
            rc = r
    return rc


if __name__ == "__main__":
    sys.exit(main())
