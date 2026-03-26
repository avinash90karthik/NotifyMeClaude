# Silver Hawk Trading - Onboarding Guide

Du brauchst: einen Mac/PC, 30 Minuten, und eine Claude Pro Subscription ($20/Monat).

Alles ist komplett privat - dein eigener Bot, deine eigenen Alerts.

---

## Schritt 1: Claude Code installieren

```bash
# Terminal oeffnen und ausfuehren:
npm install -g @anthropic-ai/claude-code
```

Falls npm nicht installiert ist: https://nodejs.org herunterladen und installieren.

---

## Schritt 2: Telegram Bot erstellen

1. Telegram oeffnen
2. Nach **@BotFather** suchen und oeffnen
3. `/newbot` eingeben
4. Namen vergeben (z.B. "Mein Trading Bot")
5. Username vergeben (muss auf `_bot` enden, z.B. `mein_trading_bot`)
6. **Bot Token kopieren** - das brauchst du gleich!

Deine Chat-ID herausfinden:
1. Schicke deinem neuen Bot eine Nachricht (irgendwas)
2. Oeffne im Browser: `https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates`
3. Suche nach `"chat":{"id":` - die Zahl dahinter ist deine **Chat ID**

---

## Schritt 3: Repo forken und einrichten

1. Gehe zum GitHub Repo (Link vom Admin)
2. Klicke **Fork** (oben rechts)
3. Dann im Terminal:

```bash
git clone https://github.com/DEIN_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude

# .env aus Template erstellen
cp .env.template .env
```

Jetzt `.env` bearbeiten und ALLE Felder ausfuellen:
```
TELEGRAM_BOT_TOKEN=dein_bot_token
TELEGRAM_CHAT_ID=deine_chat_id
TELEGRAM_BOT_USERNAME=dein_bot_username
```

---

## Schritt 4: Python einrichten + Watchlist befuellen

```bash
# Dependencies installieren
pip3 install yfinance numpy

# Watchlist mit Aktien befuellen
python3 admin_stocks.py seed
```

---

## Schritt 5: Testen

```bash
# Test 1: Telegram Bot
python3 send_telegram.py "Hallo von Silver Hawk!"
# -> Du solltest eine Nachricht in Telegram bekommen

# Test 2: Watchlist anzeigen
python3 browse_stocks.py
# -> Zeigt die Watchlist (noch ohne Preise)

# Test 3: Preise aktualisieren
python3 update_stocks.py
# -> Holt aktuelle Preise, RSI, SMAs

# Test 4: Watchlist nochmal anzeigen
python3 browse_stocks.py
# -> Jetzt mit Preisen, RSI, Ratings!
```

---

## Schritt 6: GitHub Actions einrichten (empfohlen!)

Damit laufen Preis-Updates automatisch - auch wenn dein Rechner aus ist.

1. Gehe zu deinem Fork auf GitHub
2. **Settings > Secrets and variables > Actions**
3. Fuege diese 2 Secrets hinzu:

| Secret | Wert |
|--------|------|
| `TELEGRAM_BOT_TOKEN` | Dein Bot Token aus Schritt 2 |
| `TELEGRAM_CHAT_ID` | Deine Chat ID aus Schritt 2 |

4. Gehe zu **Actions** Tab
5. Klicke **"I understand my workflows, go ahead and enable them"**
6. Fertig! Der **Stock Updater** (`update_stocks.yml`) aktualisiert Preise alle 30 Min automatisch.

### Optional: Preis-Alerts einrichten

Fuer automatische Preis-Alerts (Telegram-Benachrichtigungen bei grossen Moves):

```bash
# Template kopieren und mit deinen Stocks befuellen
cp tracker_check_template.py tracker_check.py
```

Bearbeite `tracker_check.py` und fuege deine Symbole + Alert-Levels hinzu. Dann aktiviert `tracker.yml` automatische Alerts:
- Stuendliche Zusammenfassungen (leise)
- Sofort-Alerts bei grossen Moves (>1.5% in 5 Min)
- Alerts wenn wichtige Preis-Levels erreicht werden

---

## Aktien analysieren

Starte Claude Code und gib ein:

```
Analysiere SYMBOL @prompts/00_master.md
```

Das startet eine 4-Schritt-Analyse:
1. Daten sammeln (yfinance + News)
2. Bull vs Bear Debatte
3. Urteil + Risikoanalyse
4. Trading Card an deinen Telegram Bot

Schau mit `python3 browse_stocks.py` was auf der Watchlist steht, oder analysiere jedes beliebige Symbol.

---

## Sprache aendern

Die Analyse-Ausgabe ist standardmaessig auf **Deutsch**. Um auf Englisch umzustellen:

Oeffne `prompts/00_master.md` in deinem Fork und aendere:
```
{{LANGUAGE}} = English
```

Alle Analysen, Tabellen und Texte kommen dann auf Englisch.

> English speakers: see `ONBOARDING.md` for the full setup guide in English.

---

## Watchlist verwalten

```bash
# Aktie hinzufuegen
python3 admin_stocks.py add SYMBOL "Name" Sector

# Aktie entfernen
python3 admin_stocks.py remove SYMBOL

# Alle anzeigen
python3 admin_stocks.py list
```

---

## FAQ

**Kostet das was?**
Claude Pro: $20/Monat. Telegram und GitHub Actions: kostenlos.

**Kann jemand meine Daten sehen?**
Nein. Du hast deinen eigenen Bot und deine eigenen Alerts. Alles komplett privat.

**Muss ich Coding koennen?**
Nein! Du brauchst nur Terminal oeffnen und die obigen Befehle ausfuehren.

**Kann ich eigene Aktien zur Watchlist hinzufuegen?**
Ja! `python3 admin_stocks.py add SYMBOL "Name" "Sector"` - du bist Admin deiner eigenen Watchlist.

**Wie aktualisiere ich den Code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
