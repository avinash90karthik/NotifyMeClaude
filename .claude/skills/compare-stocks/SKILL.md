---
name: compare-stocks
description: "Quick comparison of 2-4 stock tickers. Use when the user says 'Vergleiche', 'Compare', or wants a quick screening of multiple symbols."
argument-hint: "<SYMBOL1> <SYMBOL2> [SYMBOL3] [SYMBOL4]"
---

# Quick Comparison: $ARGUMENTS

## PURPOSE

Quick screening of 2-4 tickers without a full 4-step analysis.
Result: Ranking + recommendation which ticker to fully analyze.

**No chart, no debate, no judge** — pure data screening.

---

## STEP 1: Fetch data in parallel

Run this yfinance script for ALL tickers:

```python
import yfinance as yf

symbols = "$ARGUMENTS".split()
results = []

# Fetch EUR/USD live
eurusd = yf.Ticker("EURUSD=X").info.get("regularMarketPrice", 1.05)

for sym in symbols:
    try:
        t = yf.Ticker(sym)
        info = t.info
        hist = t.history(period='3mo')

        price = info.get('currentPrice', 0)
        atr14 = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]
        atr_pct = (atr14 / price * 100) if price > 0 else 0

        # Calculate RSI (Wilder's smoothing)
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        results.append({
            'symbol': sym,
            'price': price,
            'price_eur': price / eurusd,
            'atr_pct': atr_pct,
            'atr_usd': atr14,
            'rsi': rsi,
            'beta': info.get('beta', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', 'N/A'),
            'volume': info.get('averageVolume', 0),
            'short_pct': info.get('shortPercentOfFloat', 0) * 100 if info.get('shortPercentOfFloat') else 0,
            'sma50': info.get('fiftyDayAverage', 0),
            'sma200': info.get('twoHundredDayAverage', 0),
            'target_mean': info.get('targetMeanPrice', 0),
            'recommendation': info.get('recommendationKey', 'N/A'),
        })
        print(f"✅ {sym} loaded")
    except Exception as e:
        print(f"❌ {sym} error: {e}")

print(f"\n💱 EUR/USD: {eurusd:.4f}")
print(f"\n{'='*80}")
print(f"{'Symbol':<8} {'Price $':>10} {'ATR%':>7} {'RSI':>6} {'Beta':>6} {'Sector':<15} {'Short%':>7}")
print(f"{'='*80}")
for r in results:
    beta_str = f"{r['beta']:.2f}" if isinstance(r['beta'], (int, float)) else r['beta']
    print(f"{r['symbol']:<8} {r['price']:>10.2f} {r['atr_pct']:>6.1f}% {r['rsi']:>5.1f} {beta_str:>6} {r['sector']:<15} {r['short_pct']:>6.1f}%")
```

---

## STEP 2: Create comparison table

Build this table with the yfinance data:

| Criterion | SYMBOL1 | SYMBOL2 | SYMBOL3 | SYMBOL4 |
|-----------|---------|---------|---------|---------|
| **Price (USD)** | $XX.XX | $XX.XX | | |
| **Price (EUR)** | €XX.XX | €XX.XX | | |
| **ATR% (14)** | X.X% | X.X% | | |
| **RSI (14)** | XX.X | XX.X | | |
| **Beta** | X.XX | X.XX | | |
| **Sector** | Tech | Energy | | |
| **Market Cap** | $XXB | $XXB | | |
| **Short %** | X.X% | X.X% | | |
| **SMA 50** | above/below | above/below | | |
| **SMA 200** | above/below | above/below | | |
| **Analyst Target** | $XXX | $XXX | | |
| **Recommendation** | BUY/HOLD | BUY/HOLD | | |

---

## STEP 3: Evaluate turbo suitability

Rate each ticker for turbo trading (0-10):

| Criterion | Weight | SYMBOL1 | SYMBOL2 | ... |
|-----------|--------|---------|---------|-----|
| **ATR%** (higher = more movement) | 25% | X/10 | X/10 | |
| **Liquidity** (volume + market cap) | 20% | X/10 | X/10 | |
| **KO safety** (beta, gaps) | 20% | X/10 | X/10 | |
| **Sector diversification** (vs portfolio) | 20% | X/10 | X/10 | |
| **Technical setup** (RSI, SMA trend) | 15% | X/10 | X/10 | |
| **TOTAL (weighted)** | 100% | **X.X** | **X.X** | |

**Sector check against portfolio:**
- Read open positions from `predictions.db` via `python prediction_db.py portfolio`
- Which ticker diversifies best?
- ⚠️ If all tickers in same sector as existing positions → WARNING

---

## STEP 4: Ranking & recommendation

```
╔══════════════════════════════════════════════════════╗
║  RANKING                                             ║
╠══════════════════════════════════════════════════════╣
║  🥇 #1: SYMBOL (Score X.X) - [1 sentence why]       ║
║  🥈 #2: SYMBOL (Score X.X) - [1 sentence why]       ║
║  🥉 #3: SYMBOL (Score X.X) - [1 sentence why]       ║
║                                                      ║
║  → Recommendation: fully analyze SYMBOL              ║
║    (/analyse-stock SYMBOL)                           ║
╚══════════════════════════════════════════════════════╝
```

---

## ENFORCEMENT

- ✅ All data from yfinance (no estimates)
- ✅ EUR/USD fetched live
- ✅ Sector check against existing portfolio
- ✅ Clear ranking with reasoning
