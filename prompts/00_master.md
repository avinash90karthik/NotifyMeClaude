# MULTI-AGENT TRADING ANALYSE - ORCHESTRATOR

**Asset:** {{SYMBOL}}
**Sprache / Language:** {{LANGUAGE}} *(Standard: Deutsch)*

---

## ABLAUF

Du führst eine vollständige Multi-Agent Trading-Analyse für **{{SYMBOL}}** durch.

Lies und führe die folgenden 4 Prompts **nacheinander** aus. Jeder Schritt baut auf den vorherigen auf.

### Schritt 1: Datensammlung
```
Lies: prompts/01_data_collection.md
```
- Führe ALLE Aktionen aus (yfinance, Chart, News, Makro)
- **Output:** Strukturierter Datenblock mit Preis, Technicals, Chart-Analyse, News, Fundamentals

### Schritt 2: Investment Debate
```
Lies: prompts/02_investment_debate.md
```
- **Input:** Datenblock + Chart aus Schritt 1
- Führe 2 vollständige Debate-Runden durch (Bull vs Bear)
- **Output:** Vollständiges Debate-Transkript

### Schritt 3: Judge, Risk & Positionierung
```
Lies: prompts/03_judge_risk.md
```
- **Input:** Datenblock aus Schritt 1 + Debate aus Schritt 2 + Chart
- Judge bewertet unabhängig, gibt Signal + Konfidenz
- 3 Risk-Analysten definieren KO-Levels (ATR-basiert!)
- Positions-Matrix: 4 Szenarien (Mini/Klein/Standard/Ohne Hebel)
- Stop-Loss Strategie mit mentalem Stop über KO
- **Output:** Signal, Konfidenz, 3 KO-Strategien, Positions-Empfehlungen

### Schritt 4: Zusammenfassung & Versand
```
Lies: prompts/04_summary_send.md
```
- **Input:** ALLE Outputs der vorherigen Schritte
- Trading Card, ausführliche Analyse, JSON Output
- Chart + Analyse via Telegram senden
- **Output:** Telegram-Nachricht mit vollständiger Analyse

---

## QUALITAETS-ANFORDERUNGEN

- **KEIN Schritt darf übersprungen werden**
- **yfinance IMMER zuerst** - keine Web-Suche für Preisdaten
- **Chart wird von JEDEM Agenten analysiert**
- **Jedes Argument: 4-6 Sätze mit konkreten Zahlen**
- **Sprache:** {{LANGUAGE}} (Standard: Deutsch). Alle Analysen, Tabellen und Texte in dieser Sprache. JSON-Keys bleiben Englisch.
- **Wenn du merkst dass du abkürzt -> STOPP -> Mach es richtig!**
