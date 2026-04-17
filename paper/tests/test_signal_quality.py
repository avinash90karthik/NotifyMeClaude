"""Smoke test for signal_quality.summarize — no network, small fake data."""

import pandas as pd

from paper.signal_quality import summarize


def test_summarize_empty():
    assert summarize(pd.DataFrame()) == {"n_signals": 0}


def test_summarize_handles_mixed_directions():
    df = pd.DataFrame([
        {"direction": "LONG", "confidence": 62, "fwd_5d_pct": 2.0,
         "fwd_10d_pct": 3.0, "direction_5d_hit": True, "direction_10d_hit": True},
        {"direction": "LONG", "confidence": 62, "fwd_5d_pct": -1.0,
         "fwd_10d_pct": -0.5, "direction_5d_hit": False, "direction_10d_hit": False},
        {"direction": "SHORT", "confidence": 67, "fwd_5d_pct": -1.5,
         "fwd_10d_pct": -2.0, "direction_5d_hit": True, "direction_10d_hit": True},
    ])
    s = summarize(df)
    assert s["n_signals"] == 3
    assert s["n_long"] == 2
    assert s["n_short"] == 1
    # Direction-adjusted fwd5: [2.0, -1.0, +1.5] → mean ≈ 0.833
    assert abs(s["mean_adj_fwd5_pct"] - 0.833) < 0.01
    # Hit rate: 2/3 = 66.67%
    assert abs(s["hit_rate_5d_pct"] - 66.67) < 0.1
