# STEP 0: PRE-FLIGHT CHECK

**Asset:** {{SYMBOL}}

Zweck: Vier Hard-Stop-Checks vor jeder Analyse. Wenn STOP → Pipeline abbrechen, kein Step 1.

Kein News, kein Reddit, kein Macro, kein Pending — alles in Step 1+ behandelt. Nur das Minimum, das eine Analyse überhaupt legitimiert.

---

## Run

```bash
python3 scripts/analysis/preflight_check.py {{SYMBOL}}
```

## Output

```
TIMESTAMP: <ISO + CET>
WEEKDAY: <Mon..Sun>

MARKET_HOURS_TODAY:
  US: open <HH:MM-HH:MM CET> | closed (<weekend|holiday>)
  DE: open <HH:MM-HH:MM CET> | closed (<weekend|holiday>)

SYMBOL_VALIDITY:
  symbol: {{SYMBOL}}
  exchange: <NASDAQ | NYSE | XETRA | ...>
  resolved: yes | no

HARD_STOPS:
  Max_3_Slots:    <X>/3 turbos open → <ok | STOP>
  Cooldown_24h:   last stop on {{SYMBOL}} <date or "none"> → <ok | STOP>

STATUS: READY_FOR_STEP_1 | STOP
```

## User-Quittung

Echo des Output-Blocks zurück mit "OK" oder "STOP" pro Sektion. Ohne Quittung kein Step 1.

## Hard-Stop-Behandlung

| STATUS | Aktion |
|--------|--------|
| `READY_FOR_STEP_1` | Pipeline fortsetzen |
| `STOP` (Max 3 Slots oder 24h Cooldown) | Pipeline abbrechen, User informieren mit Begründung |

## Implementation Notes

- DB-Query für Slot-Check und Cooldown-Check läuft lokal (schnell)
- yfinance-Symbol-Resolve via `yf.Ticker(SYMBOL).info` (0.5-2s, akzeptabel)
- Markt-Status via Datum + Wochenende-Check (kein API-Call). Feiertags-Logik ist nicht implementiert — der Banner zeigt an US-/DE-Holidays "open" obwohl der Markt zu ist. Schadet nicht (Step 1.2 nutzt yfinance.info.marketState als autoritative Quelle, Step 0 ist nur informativ).
- Kein pytr-Aufruf hier (läuft in Step 1.1)
- Kein Pending-Check (DB-Schema noch nicht da, kommt später)
- Kein FOMC/CPI/Earnings-Check (gehört zu Macro in Step 1, nicht zu Pre-Flight)

## Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | `READY_FOR_STEP_1` — alle Checks ok |
| 1 | `STOP` — mindestens ein Hard-Stop hat gefired (Slot-Cap, Cooldown) |
| 2 | Fehler — Symbol nicht resolvbar oder DB-Read fehlgeschlagen |

```
[STEP 0 COMPLETE]
```
