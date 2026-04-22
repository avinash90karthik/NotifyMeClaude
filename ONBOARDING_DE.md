# Silver Hawk Trading - Onboarding Guide

Du brauchst: einen Mac/PC, 15 Minuten, und eine Claude Pro Subscription ($20/Monat).

Alles ist komplett lokal — der State lebt in deiner eigenen SQLite-Datei.

---

## Schritt 1: Claude Code installieren

```bash
# Terminal oeffnen und ausfuehren:
npm install -g @anthropic-ai/claude-code
```

Falls npm nicht installiert ist: https://nodejs.org herunterladen und installieren.

---

## Schritt 2: Repo forken und einrichten

1. Gehe zum GitHub Repo (Link vom Admin)
2. Klicke **Fork** (oben rechts)
3. Dann im Terminal:

```bash
git clone https://github.com/DEIN_USERNAME/NotifyMeClaude.git
cd NotifyMeClaude

# .env aus Template erstellen (nur optionale Pfade)
cp .env.template .env
```

Die `.env` ist optional — fuelle nur Pfade ein, wenn du eine dedizierte Python-venv oder ein externes Chart-Script nutzt.

---

## Schritt 3: Python einrichten + Watchlist befuellen

```bash
# Dependencies installieren
pip3 install yfinance numpy
```

Die Watchlist liegt in `memory/predictions.db` (SQLite). Sie wird beim ersten Lauf erzeugt; Eintraege verwaltest du direkt per SQL (siehe "Watchlist verwalten" unten).

---

## Schritt 4: Testen

```bash
# Test 1: Portfolio + Slot-Stand anzeigen
python3 scripts/prediction_db.py portfolio

# Test 2: Schneller technischer Snapshot fuer ein Symbol
python3 scripts/collect_data.py AAPL
# -> Komplette Daten fuer Apple

# Test 3: Pre-Flight (was Claude bei jeder Analyse zuerst laeuft)
python3 scripts/preflight_check.py AAPL
```

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
4. Trading Card im Terminal + `memory/predictions.db` wird aktualisiert

Du kannst jedes Symbol analysieren — die Watchlist ist nur ein bequemer Tracker.

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

Die Watchlist liegt in der `watchlist`-Tabelle in `memory/predictions.db`. Eintraege fuegst du mit sqlite3 direkt hinzu oder loescht sie:

```bash
# Watchlist anzeigen
sqlite3 memory/predictions.db "SELECT symbol, name, sector FROM watchlist ORDER BY symbol;"

# Aktie hinzufuegen
sqlite3 memory/predictions.db "INSERT INTO watchlist(symbol, name, sector) VALUES('AAPL', 'Apple Inc.', 'Technology');"

# Aktie entfernen
sqlite3 memory/predictions.db "DELETE FROM watchlist WHERE symbol='AAPL';"
```

Du musst die Watchlist nicht nutzen — jede Analyse funktioniert mit jedem Symbol das du uebergibst.

---

## Portfolio-Tracking

Dein Portfolio-State lebt in `memory/predictions.db` (SQLite).

```bash
# Aktuellen Stand anzeigen
python3 scripts/prediction_db.py portfolio

# Cash-Balance setzen
python3 scripts/prediction_db.py cash 10000

# Nach Trade-Eroeffnung
python3 scripts/prediction_db.py open ID --shares 50 --cert-price 2.50

# Position schliessen
python3 scripts/prediction_db.py close ID --exit-price 3.10 --reason target
```

---

## FAQ

**Kostet das was?**
Claude Pro: $20/Monat. Alles andere ist kostenlos (yfinance, lokale SQLite).

**Kann jemand meine Daten sehen?**
Nein. Alles ist lokal — deine eigene SQLite-Datei, keine Cloud, kein Tracking.

**Muss ich Coding koennen?**
Nein! Du brauchst nur Terminal oeffnen und die obigen Befehle ausfuehren.

**Kann ich eigene Aktien zur Watchlist hinzufuegen?**
Ja! Direkt per sqlite3: `sqlite3 memory/predictions.db "INSERT INTO watchlist(symbol, name, sector) VALUES('SYMBOL', 'Name', 'Sector');"` — du bist Admin deiner eigenen Watchlist. Oder uebergehe die Watchlist komplett — jede Analyse arbeitet mit jedem uebergebenen Symbol.

**Wie aktualisiere ich den Code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
