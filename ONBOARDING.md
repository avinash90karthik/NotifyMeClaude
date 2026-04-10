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

# Seed the watchlist with stocks
python3 admin_stocks.py seed
```

---

## Step 4: Test Everything

```bash
# Test 1: Show watchlist
python3 browse_stocks.py
# -> Shows the watchlist (no prices yet)

# Test 2: Update prices
python3 update_stocks.py
# -> Fetches current prices, RSI, SMAs

# Test 3: Show watchlist again
python3 browse_stocks.py
# -> Now with prices, RSI, ratings!

# Test 4: Quick technical snapshot
python3 collect_data.py AAPL
# -> Full data dump for Apple
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

Check `python3 browse_stocks.py` to see what's on the watchlist, or analyze any symbol you want.

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

```bash
# Add a stock
python3 admin_stocks.py add SYMBOL "Name" Sector

# Remove a stock
python3 admin_stocks.py remove SYMBOL

# Show all
python3 admin_stocks.py list
```

---

## Portfolio Tracking

Your portfolio state lives in `memory/predictions.db` (SQLite).

```bash
# Show current state
python3 prediction_db.py portfolio

# Set your cash balance
python3 prediction_db.py cash 10000

# After a trade is opened
python3 prediction_db.py open ID --shares 50 --cert-price 2.50

# Close a position
python3 prediction_db.py close ID --exit-price 3.10 --reason target
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
Yes! `python3 admin_stocks.py add SYMBOL "Name" "Sector"` — you are the admin of your own watchlist.

**How do I update the code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
