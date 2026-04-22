# Silver Hawk Trading - Onboarding Guide

You need: a Mac/PC, 15 minutes, and a Claude Pro subscription ($20/month).

Everything is completely local — state lives in your own SQLite file.

---

## Step 1: Install Claude Code

```bash
# Open Terminal and run:
npm install -g @anthropic-ai/claude-code
```

If npm is not installed: download and install from https://nodejs.org

---

## Step 2: Fork the Repo and Configure

1. Go to the GitHub repo (link from admin)
2. Click **Fork** (top right)
3. Then in Terminal:

```bash
git clone https://github.com/YOUR_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude

# Create .env from template (optional paths only)
cp .env.template .env
```

The `.env` file is optional — only fill in the paths if you use a dedicated Python venv or external chart script.

---

## Step 3: Install Python Dependencies + Seed Watchlist

```bash
# Install dependencies
pip3 install yfinance numpy
```

The watchlist is stored in `memory/predictions.db` (SQLite). It is created on first use; manage entries directly via SQL when you need to (see "Manage Your Watchlist" below).

---

## Step 4: Test Everything

```bash
# Test 1: Show portfolio + slot count
python3 scripts/prediction_db.py portfolio

# Test 2: Quick technical snapshot for a symbol
python3 scripts/collect_data.py AAPL
# -> Full data dump for Apple

# Test 3: Pre-flight check (what claude runs first on every analysis)
python3 scripts/preflight_check.py AAPL
```

---

## Analyze Stocks

Start Claude Code and type:

```
Analyze SYMBOL @prompts/00_master.md
```

This launches a 4-step analysis:
1. Data collection (yfinance + news)
2. Bull vs Bear debate
3. Verdict + risk analysis
4. Trading card in terminal + `memory/predictions.db` updated

You can analyze any symbol — the watchlist is just a convenience for tracking.

---

## Language Setting

The analysis prompts default to **German** output. To switch to English:

Open `prompts/00_master.md` in your fork and change:
```
{{LANGUAGE}} = English
```

This will make all analysis output appear in English.

---

## Manage Your Watchlist

The watchlist lives in the `watchlist` table inside `memory/predictions.db`. Add or remove entries with sqlite3 directly:

```bash
# Show what's on the watchlist
sqlite3 memory/predictions.db "SELECT symbol, name, sector FROM watchlist ORDER BY symbol;"

# Add a stock
sqlite3 memory/predictions.db "INSERT INTO watchlist(symbol, name, sector) VALUES('AAPL', 'Apple Inc.', 'Technology');"

# Remove a stock
sqlite3 memory/predictions.db "DELETE FROM watchlist WHERE symbol='AAPL';"
```

You don't have to use the watchlist — every analysis works on any symbol you pass to it.

---

## Portfolio Tracking

Your portfolio state lives in `memory/predictions.db` (SQLite).

```bash
# Show current state
python3 scripts/prediction_db.py portfolio

# Set your cash balance
python3 scripts/prediction_db.py cash 10000

# After a trade is opened
python3 scripts/prediction_db.py open ID --shares 50 --cert-price 2.50

# Close a position
python3 scripts/prediction_db.py close ID --exit-price 3.10 --reason target
```

---

## FAQ

**Does this cost anything?**
Claude Pro: $20/month. Everything else is free (yfinance, local SQLite).

**Can anyone see my data?**
No. Everything is local — your own SQLite file, no cloud, no tracking.

**Do I need to know how to code?**
No! You just need to open Terminal and run the commands above.

**Can I add my own stocks to the watchlist?**
Yes! Use sqlite3 directly: `sqlite3 memory/predictions.db "INSERT INTO watchlist(symbol, name, sector) VALUES('SYMBOL', 'Name', 'Sector');"`. You are the admin of your own watchlist. Or skip the watchlist entirely — every analysis works on any symbol you pass.

**How do I update the code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
