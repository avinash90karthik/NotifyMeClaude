# Silver Hawk Trading - Onboarding Guide

You need: a Mac/PC, 30 minutes, and a Claude Pro subscription ($20/month).

Everything is completely private - your own bot, your own alerts.

---

## Step 1: Install Claude Code

```bash
# Open Terminal and run:
npm install -g @anthropic-ai/claude-code
```

If npm is not installed: download and install from https://nodejs.org

---

## Step 2: Create a Telegram Bot

1. Open Telegram
2. Search for **@BotFather** and open it
3. Type `/newbot`
4. Choose a name (e.g. "My Trading Bot")
5. Choose a username (must end with `_bot`, e.g. `my_trading_bot`)
6. **Copy the Bot Token** - you'll need it shortly!

Find your Chat ID:
1. Send your new bot a message (anything)
2. Open in browser: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Look for `"chat":{"id":` - the number after that is your **Chat ID**

---

## Step 3: Fork the Repo and Configure

1. Go to the GitHub repo (link from admin)
2. Click **Fork** (top right)
3. Then in Terminal:

```bash
git clone https://github.com/YOUR_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude

# Create .env from template
cp .env.template .env
```

Now edit `.env` and fill in ALL fields:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_BOT_USERNAME=your_bot_username
```

---

## Step 4: Install Python Dependencies + Seed Watchlist

```bash
# Install dependencies
pip3 install yfinance numpy

# Seed the watchlist with stocks
python3 admin_stocks.py seed
```

---

## Step 5: Test Everything

```bash
# Test 1: Telegram Bot
python3 send_telegram.py "Hello from Silver Hawk!"
# -> You should receive a message in Telegram

# Test 2: Show watchlist
python3 browse_stocks.py
# -> Shows the watchlist (no prices yet)

# Test 3: Update prices
python3 update_stocks.py
# -> Fetches current prices, RSI, SMAs

# Test 4: Show watchlist again
python3 browse_stocks.py
# -> Now with prices, RSI, ratings!
```

---

## Step 6: Set Up GitHub Actions (recommended!)

This runs price updates automatically - even when your computer is off.

1. Go to your fork on GitHub
2. **Settings > Secrets and variables > Actions**
3. Add these 2 secrets:

| Secret | Value |
|--------|-------|
| `TELEGRAM_BOT_TOKEN` | Your Bot Token from Step 2 |
| `TELEGRAM_CHAT_ID` | Your Chat ID from Step 2 |

4. Go to the **Actions** tab
5. Click **"I understand my workflows, go ahead and enable them"**
6. Done! The **Stock Updater** (`update_stocks.yml`) automatically updates prices every 30 min.

### Optional: Price Alerts

For automatic price alerts (Telegram notifications on big moves):

```bash
# Copy template and add your stocks
cp tracker_check_template.py tracker_check.py
```

Edit `tracker_check.py` and add your symbols + alert levels. Then `tracker.yml` will automatically send:
- Hourly summaries (silent)
- Instant alerts on big moves (>1.5% in 5 min)
- Alerts when important price levels are reached

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
4. Trading card sent to your Telegram bot

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

## FAQ

**Does this cost anything?**
Claude Pro: $20/month. Telegram and GitHub Actions: free.

**Can anyone see my data?**
No. You have your own bot and your own alerts. Everything is completely private.

**Do I need to know how to code?**
No! You just need to open Terminal and run the commands above.

**Can I add my own stocks to the watchlist?**
Yes! `python3 admin_stocks.py add SYMBOL "Name" "Sector"` - you are the admin of your own watchlist.

**How do I update the code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
