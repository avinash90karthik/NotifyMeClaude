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

# Watchlist mit Aktien befuellen
python3 admin_stocks.py seed
```

---

## Schritt 4: Testen

```bash
# Test 1: Watchlist anzeigen
python3 browse_stocks.py
# -> Zeigt die Watchlist (noch ohne Preise)

# Test 2: Preise aktualisieren
python3 update_stocks.py
# -> Holt aktuelle Preise, RSI, SMAs

# Test 3: Watchlist nochmal anzeigen
python3 browse_stocks.py
# -> Jetzt mit Preisen, RSI, Ratings!

# Test 4: Schneller technischer Snapshot
python3 collect_data.py AAPL
# -> Komplette Daten fuer Apple
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

## Portfolio-Tracking

Dein Portfolio-State lebt in `memory/predictions.db` (SQLite).

```bash
# Aktuellen Stand anzeigen
python3 prediction_db.py portfolio

# Cash-Balance setzen
python3 prediction_db.py cash 10000

# Nach Trade-Eroeffnung
python3 prediction_db.py open ID --shares 50 --cert-price 2.50

# Position schliessen
python3 prediction_db.py close ID --exit-price 3.10 --reason target
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
Ja! `python3 admin_stocks.py add SYMBOL "Name" "Sector"` - du bist Admin deiner eigenen Watchlist.

**Wie aktualisiere ich den Code?**
```bash
git remote add upstream https://github.com/AbdullahKaratas/NotifyMeClaude.git
git pull upstream main
```
