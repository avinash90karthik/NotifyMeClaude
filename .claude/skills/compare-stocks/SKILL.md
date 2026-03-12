---
name: compare-stocks
description: "Quick comparison of 2-4 stock tickers. Use when the user says 'Vergleiche', 'Compare', or wants a quick screening of multiple symbols."
argument-hint: "<SYMBOL1> <SYMBOL2> [SYMBOL3] [SYMBOL4]"
---

# Schnell-Vergleich: $ARGUMENTS

## ZWECK

Schnelles Screening von 2-4 Tickern ohne volle 4-Schritt-Analyse.
Ergebnis: Ranking + Empfehlung welchen Ticker man voll analysieren sollte.

**Kein Chart, keine Debate, kein Judge** - reines Daten-Screening.

---

## SCHRITT 1: Daten parallel holen

Führe dieses yfinance-Script für ALLE Ticker aus:

```python
import yfinance as yf

symbols = "$ARGUMENTS".split()
results = []

# EUR/USD live holen
eurusd = yf.Ticker("EURUSD=X").info.get("regularMarketPrice", 1.05)

for sym in symbols:
    try:
        t = yf.Ticker(sym)
        info = t.info
        hist = t.history(period='3mo')

        price = info.get('currentPrice', 0)
        atr14 = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]
        atr_pct = (atr14 / price * 100) if price > 0 else 0

        # RSI berechnen (Wilder's smoothing)
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
        print(f"✅ {sym} geladen")
    except Exception as e:
        print(f"❌ {sym} Fehler: {e}")

print(f"\n💱 EUR/USD: {eurusd:.4f}")
print(f"\n{'='*80}")
print(f"{'Symbol':<8} {'Preis $':>10} {'ATR%':>7} {'RSI':>6} {'Beta':>6} {'Sektor':<15} {'Short%':>7}")
print(f"{'='*80}")
for r in results:
    beta_str = f"{r['beta']:.2f}" if isinstance(r['beta'], (int, float)) else r['beta']
    print(f"{r['symbol']:<8} {r['price']:>10.2f} {r['atr_pct']:>6.1f}% {r['rsi']:>5.1f} {beta_str:>6} {r['sector']:<15} {r['short_pct']:>6.1f}%")
```

---

## SCHRITT 2: Vergleichstabelle erstellen

Erstelle diese Tabelle mit den yfinance-Daten:

| Kriterium | SYMBOL1 | SYMBOL2 | SYMBOL3 | SYMBOL4 |
|-----------|---------|---------|---------|---------|
| **Preis (USD)** | $XX.XX | $XX.XX | | |
| **Preis (EUR)** | €XX.XX | €XX.XX | | |
| **ATR% (14)** | X.X% | X.X% | | |
| **RSI (14)** | XX.X | XX.X | | |
| **Beta** | X.XX | X.XX | | |
| **Sektor** | Tech | Energy | | |
| **Market Cap** | $XXB | $XXB | | |
| **Short %** | X.X% | X.X% | | |
| **SMA 50** | über/unter | über/unter | | |
| **SMA 200** | über/unter | über/unter | | |
| **Analyst Target** | $XXX | $XXX | | |
| **Empfehlung** | BUY/HOLD | BUY/HOLD | | |

---

## SCHRITT 3: Turbo-Eignung bewerten

Bewerte jeden Ticker für Turbo-Trading (0-10):

| Kriterium | Gewicht | SYMBOL1 | SYMBOL2 | ... |
|-----------|---------|---------|---------|-----|
| **ATR%** (höher = mehr Bewegung) | 25% | X/10 | X/10 | |
| **Liquidität** (Volume + MarketCap) | 20% | X/10 | X/10 | |
| **KO-Sicherheit** (Beta, Gaps) | 20% | X/10 | X/10 | |
| **Sektor-Diversifikation** (vs. Portfolio) | 20% | X/10 | X/10 | |
| **Technisches Setup** (RSI, SMA-Trend) | 15% | X/10 | X/10 | |
| **GESAMT (gewichtet)** | 100% | **X.X** | **X.X** | |

**Sektor-Check gegen Portfolio:**
- Lies offene Positionen aus Supabase `portfolio` Tabelle
- Welcher Ticker diversifiziert am besten?
- ⚠️ Wenn alle Ticker im selben Sektor wie bestehende Positionen → WARNUNG

---

## SCHRITT 4: Ranking & Empfehlung

```
╔══════════════════════════════════════════════════════╗
║  RANKING                                             ║
╠══════════════════════════════════════════════════════╣
║  🥇 #1: SYMBOL (Score X.X) - [1 Satz warum]        ║
║  🥈 #2: SYMBOL (Score X.X) - [1 Satz warum]        ║
║  🥉 #3: SYMBOL (Score X.X) - [1 Satz warum]        ║
║                                                      ║
║  → Empfehlung: SYMBOL voll analysieren               ║
║    (/analyse-stock SYMBOL)                           ║
╚══════════════════════════════════════════════════════╝
```

---

## SCHRITT 5: Telegram senden

```bash
source .env
python send_telegram.py "$(cat <<'EOF'
📊 TICKER-VERGLEICH

[Ranking-Tabelle]

→ Empfehlung: SYMBOL voll analysieren
EOF
)"
```

---

## ENFORCEMENT

- ✅ Alle Daten aus yfinance (keine Schätzungen)
- ✅ EUR/USD live geholt
- ✅ Sektor-Check gegen bestehendes Portfolio
- ✅ Klares Ranking mit Begründung
- ✅ Telegram-Versand
