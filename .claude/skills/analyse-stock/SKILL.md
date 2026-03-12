---
name: analyse-stock
description: "Run full 4-step multi-agent trading analysis for a stock. Use when the user says 'Analysiere', 'Analyse', 'analyze', or asks for a trading analysis of any stock symbol."
argument-hint: "<SYMBOL> [LANGUAGE]"
---

# 4-Schritt Multi-Agent Trading Analyse für $ARGUMENTS

## QUALITAETS-ANFORDERUNGEN

- **KEIN Schritt darf übersprungen werden**
- **yfinance IMMER zuerst** - keine Web-Suche für Preisdaten
- **Chart wird von JEDEM Schritt analysiert**
- **Jedes Argument: 4-6 Sätze mit konkreten Zahlen**
- **Sprache:** Deutsch (Standard). JSON-Keys Englisch.
- **LONG und SHORT sind gleichwertig** - kein LONG-Bias!
- **Wenn du merkst dass du abkürzt -> STOPP -> Mach es richtig!**

## RISK MANAGEMENT (IMMER BEACHTEN!)

```
╔═══════════════════════════════════════════════════════════════╗
║  Max. Verlust pro Trade:      10% des Portfolios             ║
║  Max. gleichzeitig riskiert:  40% des Portfolios             ║
║  Max. Sektor-Konzentration:   60% in einem Sektor            ║
║  Time-Stop: 3 Tage kein +5% → halbieren, 5 Tage → raus     ║
║  Vor Earnings: min. 50% sichern oder KO-Abstand erhöhen     ║
╚═══════════════════════════════════════════════════════════════╝
```

## ABLAUF

Führe die 4 Schritte **nacheinander** aus. Jeder Schritt baut auf den vorherigen auf.

### Schritt 0: Portfolio-Sync (PFLICHT - VOR ALLEM ANDEREN!)
- Lies die Supabase `portfolio` Tabelle (offene Positionen + Cash)
- Zeige den aktuellen Stand kurz an (Gesamtwert, Cash frei, Sektor-Verteilung)
- Prüfe Sektor-Konzentration: Wenn der neue Trade den 60%-Limit überschreiten würde → WARNUNG
- Wenn Supabase-Verbindung fehlschlägt → STOPP, User informieren, NICHT mit geschätzten Daten weiterarbeiten

### Schritt 1: Datensammlung
Lies und führe aus: `prompts/01_data_collection.md`
- Ersetze `{{SYMBOL}}` mit dem Stock-Symbol aus $ARGUMENTS
- yfinance Python-Script ausführen (PFLICHT!)
- Chart generieren und visuell analysieren (PFLICHT!)
- News via Web-Suche (mindestens 5 mit Datum)
- Makro-Faktoren (Fed, DXY, CPI, Geopolitik)
- Short Interest analysieren
- **NEU: Korrelations-Check gegen offene Positionen aus Supabase (PFLICHT!)**
- **NEU: Event-Kalender (Earnings, Fed, CPI) mit Impact-Bewertung**
- **JSON-Block am Ende generieren (PFLICHT!)**

### Schritt 2: Investment Debate
Lies und führe aus: `prompts/02_investment_debate.md`
- Input: Datenblock + Chart aus Schritt 1
- 2 vollständige Runden Bull vs Bear
- Konkrete Preisziele pro Seite
- **NEU: SHORT-Trade Scorecard (LONG vs SHORT, je 0-10 über 6 Kriterien)**
- **NEU: Wenn SHORT Score >= LONG Score → SHORT-Setup ausarbeiten**
- **JSON-Block am Ende generieren (PFLICHT!)**

### Schritt 3: Judge, Risk & Positionierung
Lies und führe aus: `prompts/03_judge_risk.md`
- Judge bewertet UNABHÄNGIG (inkl. Chart!)
- Signal + Konfidenz-Score
- **NEU: KO-Berechnung in 3 Schritten:**
  - A) ATR-Multiplikator nach Asset-Klasse (Large Cap 2x, Small Cap 2.5x, Rohstoffe 3x)
  - B) Chart-Support als Mindestabstand (KO unter stärkstem Support + Puffer)
  - C) Finales KO = das WEITER ENTFERNTE von A und B
- **NEU: Earnings/Event-Warnung** (ATR-Multiplikator +0.5 wenn Event < 5 Tage)
- **NEU: Risk-per-Trade Check** (10% max, 40% gleichzeitig, gegen Portfolio aus Supabase)
- **NEU: Time-Stops** (3 Tage → halbieren, 5 Tage → raus, vor Earnings → 50% sichern)
- Positions-Matrix: 4 Szenarien in % vom Portfolio (Mini 5% / Klein 15% / Standard 30% / Ohne Hebel 20%)
- **JSON-Block am Ende generieren (PFLICHT!)**
- Stop-Loss Strategie (mentaler Stop ÜBER KO)

### Schritt 4: Zusammenfassung & Versand
Lies und führe aus: `prompts/04_summary_send.md`
- Trading Card erstellen (inkl. Risiko-Check Block und gestaffelte Exits)
- Chart zu Supabase hochladen
- Analyse als Reminder in Supabase speichern
- **NEU: Trading Card via Telegram senden (PFLICHT!)**
- **NEU: Chart als Telegram-Foto senden**

## KONTEXT

Portfolio-Stand (offene/geschlossene Positionen, Cash) aus der Supabase `portfolio` Tabelle lesen.
Analysen stehen in `reminders`, Watchlist in `stocks`.

## LEARNINGS (IMMER BEACHTEN!)

- **Gewinne mitnehmen!** D-Wave war +30% im Plus, nicht realisiert. Gestaffelte Exits einhalten!
- **Keine festen Regeln erfinden** - die Analyse liefert Entry/Exit/Stop/KO pro Trade
- **Trade Republic hat Long UND Short Turbos** - SHORT ist gleichwertig!
- **Gold/Silber sind Rohstoffe** - brauchen 3x ATR-Multiplikator (Makro-Schocks!)
- **Credentials NIEMALS in committed Files**
- **3 volle 4-Schritt-Analysen passen in eine Session**
