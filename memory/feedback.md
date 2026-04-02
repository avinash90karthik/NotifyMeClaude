# Silver Hawk Trading - Feedback & Learnings

> Single source for all trading learnings. Referenced by analysis prompts and strategy.
> Add new entries at the top (newest first).

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
