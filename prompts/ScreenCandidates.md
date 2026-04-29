# ScreenCandidates.md

## Purpose
Pre-market scan: surface trending tickers from retail communities, cross-reference with Silver Hawk DB, return curated KO-Zertifikate candidates.

---

## Data Sources

**Primary — apewisdom.io (no auth):**
- `https://apewisdom.io/api/v1.0/filter/wallstreetbets`
- `https://apewisdom.io/api/v1.0/filter/options`
- `https://apewisdom.io/api/v1.0/filter/stocks`
- `https://apewisdom.io/api/v1.0/filter/all-stocks`

**Fallback:**
- `https://www.reddit.com/r/{sub}/hot.json` for: wallstreetbets, options, Vitards, biotechplays, mauerstrassenwetten

**Local:**
- Silver Hawk SQLite DB
- yfinance for market context

---

## Workflow

1. **Fetch & aggregate** trending tickers across sources.
2. **Filter** down to candidates worth deeper look — use judgment, not hard cutoffs. Velocity, cross-sub presence, and unusual movement all matter.
3. **Cross-reference Silver Hawk DB** — existing predictions, watchlist hits, prior trade performance.
4. **Pull market context** via yfinance — price action, ATR, upcoming earnings, liquidity.
5. **Reason about KO-suitability** — does this ticker fit the strategy, given mention dynamics, Silver Hawk signals, and market state?
6. **Return ranked candidates** with reasoning per ticker. Flag risks (earnings, low liquidity, conflicting signals) inline.
