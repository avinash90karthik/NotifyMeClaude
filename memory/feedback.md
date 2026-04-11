# Silver Hawk Trading - Feedback & Learnings

> Single source for all trading learnings. Referenced by analysis prompts and strategy.
> Add new entries at the top (newest first).

---

## #6 — PLTR-Analyse: vier Fehler in einer Session (11.04.2026)

**Auslöser:** User wollte eine unbiased Analyse zu PLTR (lehnte selbst SHORT, sagte es aber nicht). Die Session lief in vier separate Blindstellen:

1. **Mini-Analyse statt full** — anstelle der vollen 4-Step-Pipeline kam eine abgekürzte Version. Grund: `.claude/skills/analyse-stock/SKILL.md` existierte nicht, obwohl CLAUDE.md darauf verwies. Claude improvisierte einen Kurzlauf.
2. **Falsches Datum** — Output sagte "no trade possible, Friday is CPI" an einem **Samstag**. CPI war am Vortag bereits gelaufen. Die Web-Suche zeigte "CPI Friday" ohne Jahr/Woche-Kontext und Claude übernahm es blind, ohne gegen das lokale Datum abzugleichen.
3. **Trump Truth Social Post übersehen** — Trump hatte PLTR als "guten Kauf" bezeichnet (marktbewegendes Event, Gap-Risiko). Die Analyse enthielt den Post nicht, obwohl die Checkliste in `prompts/01_data_collection.md` einen Trump-Check vorsieht.
4. **Reddit-Flow übersehen** — keine WSB/WSB-Ger/stocks/investing-Suche, obwohl in der Checkliste gefordert.

**Root Cause:** Alle vier Fehler haben die gleiche Ursache — die Pre-Flight-Checkliste war **weiche Guidance** (Prompt-Text), nicht **harter Script-Output**. Leicht überspringbar. Eine Skill-Datei hätte daran nichts geändert (Skills sind nur Prompt-Expansion, keine Denkkraft).

**Regel (technisch erzwungen):**

1. **`preflight_check.py` ist jetzt Pflicht-Step 0.** Druckt Datum, Wochentag, Markt-Status, yfinance News (7 Tage), MANDATORY Search Queries für Trump/Reddit/Day-News/Events. Output muss in der Analyse erscheinen, Checkliste muss verbatim mit Antworten echoed werden. Bei Price-Fetch-Fehler Exit 2 → Analyse bricht ab, kein Fallback auf Mini-Version.
2. **CLAUDE.md Hard-Rule #1:** Pre-Flight vor allem anderen. Hard-Rule #11: "No mini-analyses". Hard-Rule #12: "No default direction".
3. **yfinance `.news`** wird im Pre-Flight gezogen — Day-News-Blindstelle geschlossen ohne zusätzliche API. ABER: yfinance aggregiert Reuters/Bloomberg/Yahoo mit Delay, enthält KEINE direkten Truth-Social-/X-/Reddit-Posts. Deshalb sind Web-Searches weiterhin mandatory.
4. **Trump-Search + Reddit-Search sind MANDATORY** für jeden Ticker — nicht nur "sensitive" Sektoren. Die exakten Query-Strings stehen im Pre-Flight-Banner, kein Paraphrasieren erlaubt.
5. **Neutralität ist Pflicht-Checkbox im Pre-Flight.** Spiegel-Test vor finalem Signal.
6. **Kein Slash-Command-Skill.** Ausprobiert und verworfen: eine Skill hätte nur die Prompts dupliziert, ohne echte Enforcement. Natural-Language-Intent + CLAUDE.md + Preflight-Script reichen.

**Merke:** Guidance in Prompts wird übersprungen. Scripts, die unübersehbar auf den Screen drucken, werden nicht übersprungen. Wenn eine Regel mehrfach gerissen wird → in Code gießen, nicht in Text. Eine weitere Abstraktions-Schicht (Skill über Prompts über Regeln) wäre nur mehr Text gewesen.

---

## #5 — Datengetriebener Entry, KEIN Market Buy (07.04.2026)

**Auslöser:** ENR.DE Turbo bei 1,632€ per Market gekauft, innerhalb von 2h auf 1,38€ gefallen (-15,4%). Daten zeigten: Median-Dip 2,04%, 58% der Tagestiefs kommen nachmittags, Limit bei 1,30€ wäre realistisch gewesen. Ersparnis bei Limit: ~20%.

**Problem:** Analyse sagte "Market Buy OK" weil Ersparnis < 3% — aber das war falsch berechnet (nur vs. aktuellem Kurs, nicht vs. realistischem Intraday-Dip). Bei 10x Hebel = 2% besser am Underlying = 20% besser am Cert.

**Regel:**
1. IMMER datengetriebenen Buy-Bereich berechnen (Median-Dip, ATR, Tagestief-Timing)
2. IMMER Limit-Order als Default — Market Buy nur als letzter Fallback
3. Entry-Plan mit 3 Stufen: Limit → Anheben → Fallback mit Zeitfenster
4. Cert-Preise bei verschiedenen Underlying-Levels ausrechnen und in Summary zeigen
5. "Market Buy OK" ist VERBOTEN als Empfehlung ohne datengetriebene Begründung

**Merke:** Bei Turbos ist der Entry genauso wichtig wie die Analyse. Jeder Cent zählt mit Hebel.

---

## #4 — v8 Exit-Regel (April 2026)

**Änderung:** 80% bei +20% (statt v7 66%). Rest maximal bis +30%.
**Warum:** Gewinne sichern > Gewinne maximieren bei Turbos. Mehrfach +15-20% Gewinne wieder abgegeben.
**Sonderregel:** Trump-Events = alles raus, keine Overnight-Positionen.

---

## #3 — Overnight-Gewinne schützen (April 2026)

**Auslöser:** +500 EUR laufende Gewinne über 3 Tage. Trump hält über Nacht Rede → Markt gapt, Stop zieht. Ergebnis: +500 → -300 EUR.

**Problem:** Keine Regel für "Gewinne vor Overnight-Events sichern". v7 Hedge greift erst bei -20%, aber Overnight-Gap springt direkt drüber hinweg.

**Regel (jetzt in Strategy v7 § Overnight-Event-Regel):**
- Bekanntes Event heute Nacht + offene Position im Plus → Stop auf BE (PFLICHT wenn ≥+10%)
- Position ≥+15% vor Event → 50% Teilverkauf ODER Stop auf +5%
- Freitag = immer auf BE vor Wochenende (gilt auch für "Event Eves")
- Event-Check ist Teil von Step 3 (W5 in Risk Audit)

**Merke:** Turbo-Zertifikate und Overnight-Gaps vertragen sich nicht.

---

## #2 — Event-Check VOR jeder Analyse (02.04.2026)

**Auslöser:** Trump "Liberation Day" Rede bereits am Vorabend gehalten. Nicht erkannt, als "heute Abend" kommuniziert. DAX SHORT bei BE geschlossen (statt +5-10%), ENR.DE LONG ohne volles Bild gekauft.

**Regel:**
1. Bei JEDER Analyse als ERSTEN Schritt: "Gibt es angekündigte Events? Sind sie SCHON passiert?"
2. Premarket-Kurse als Signal — wenn MU -14% im Premarket, ist ETWAS passiert
3. In CET denken — "Heute Abend US" = "gestern Nacht CET" möglich
4. Wenn Event bereits stattfand: Marktreaktion analysieren BEVOR Trade-Empfehlung
5. Gap-Downs > 2% = IMMER zuerst fragen "Was ist passiert?"

---

## #1 — ATR >7% → kein KO-Zertifikat (März 2026)

**Auslöser:** KO-Zertifikat auf hochvolatilen Basiswert → Knockout durch normale Tagesschwankung.
**Regel:** ATR >7% = Warrants/Optionen oder Aktien direkt. KEINE KO-Zertifikate.
**In Risk Audit als V1 implementiert.**

---

## #0 — These vs Timing (laufend)

**Regel:** These intakt → halten. These gebrochen → raus.
**Nicht verwechseln:** Schlechtes Timing ≠ falsche These. Wenn die Fundamentals stimmen und nur das Timing schlecht war → nachkaufen statt panisch verkaufen.
