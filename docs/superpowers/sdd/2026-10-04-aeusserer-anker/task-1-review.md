# Task 1 review: `Anchor`, lesen und schreiben, `examine`

Prüfer: frischer Reviewer, read-only, keine Subagenten. Basis `edcb9e0`, Kopf `11de3f6`. Grundlage: die Diff-Datei `review-edcb9e0..11de3f6.diff` (einmal gelesen, kein Hunk abgeschnitten), dazu gezielte Blicke außerhalb des Diffs, die unter *Checks run* einzeln mit ihrem Risiko stehen.

### Spec Compliance

- ✅ Sieben Dateien, alle mit Hunks: `docs/explanation/hash-chain.md`, `docs/tutorials/record-your-first-event.md`, `src/previously/contract/types.py`, `src/previously/core/anchor.py` (neu), `src/previously/core/verify.py`, `tests/test_anchor.py` (neu), `tests/test_verify.py`. Nichts sonst im Commit; `git status --short` leer.
- ✅ `Anchor(id: int, hash: bytes)`, eingefroren, nach `RawEvent`, Docstring wortgleich zum Brief (`src/previously/contract/types.py:184-197` im Diff). `Tip` nicht wiederverwendet, wie die Dispatch verlangt.
- ✅ `parse_anchors` / `format_anchor` (`src/previously/core/anchor.py`) wortgleich zum Brief bis auf eine ruff-format-Umbrechung der Hash-Längen-Meldung; Text unverändert. Kein Datei- und kein Datenbankzugriff.
- ✅ `Examination(findings: tuple[Finding, ...], tip: Anchor | None)` (`verify.py`, Diff-Zeilen 301-311).
- ✅ `examine` mit der Signatur des Briefs, Docstring wortgleich, Ablehnung von `exact` ohne Anker im Kern.
- ✅ Die fünf Stellen des Briefs sind die einzigen Änderungen am alten Rumpf: Signatur/Docstring; `tip` und `pending` vor dem `with`; `return findings` → `break` (Zählabgleich davor unverändert, also weiter in derselben Transaktion); Ankerprüfung im `for row in rows` direkt nach `_check_event`; `tip = Anchor(...)` nach `checked += 1`. Alle Kommentare des Rumpfs stehen noch, der Kommentar zu G4/Transaktion unberührt. Keine zweite Lesung der Event-Tabelle: `pending.pop(row.id, ())` läuft auf den Zeilen, die der Gang ohnehin liest.
- ✅ Schritt 5 des Briefs liegt in `_closing_findings` statt am Funktionsende — Abweichung, begründet durch C901 (siehe Bewertung unten); Verhalten, Reihenfolge der Befunde und alle drei Texte unverändert.
- ✅ Die drei Befundtexte zeichengenau: `hash does not match the anchor`; `anchored event is missing (the log ends at {tip_id})`; `the log continues past the newest anchor ({newest})`.
- ✅ `verify(storage, *, batch=1000) -> list[Finding]` mit unveränderter Signatur, ruft `examine`; bestehende Tests in `tests/test_verify.py` unverändert (nur Importe ergänzt, Tests angehängt).
- ✅ Zitate im Code nur als `` {ref}`external-anchor` `` / `` {ref}`hash-chain` ``, kein `§`, keine Zitate in Befundtexten oder `InvalidPayload`-Meldungen.
- ✅ Kein `# type: ignore`, kein neues `# noqa`, kein Mock.
- ✅ Seite: Label `(external-anchor)=` vor `## The external anchor`; alter Satz „closes all three at once … stage 1a has none" entfernt; die acht Punkte in Reihenfolge; Satzfall-Überschrift; ein Satz pro Zeile; weiterhin genau ein Admonition auf der Seite (`:::{important}`, Zeile 46).
- ✅ Tutorial: nur der Testlauf-Block geändert, aus einem echten Lauf, ohne `rootdir:`-Zeile; 251/251, Dateisummen stimmen (siehe Checks).
- ✅ Commit-Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`, kein `Co-Authored-By`.
- ❌ Schritt 9 (vier Mutationen) nicht gemessen — durch eine Ablehnung des Berechtigungssystems, nicht durch Nachlässigkeit; die Frage liegt beim Maintainer. Unten nur als Begründung aus dem Code, ausdrücklich keine Messung.
- ⚠️ Die sechs Tore: vom Umsetzer mit allen sechs Schlusszeilen berichtet; von mir laut Auftrag nicht wiederholt. Unverifiziert außer `--collect-only` (251).
- ⚠️ C901 = 11 für den Brief-Rumpf ist nur durch Nachzählen der Verzweigungen plausibilisiert (siehe Bewertung 1), nicht gemessen; eine Rekonstruktion des Brief-Rumpfs auf einer Kopie habe ich bewusst unterlassen.

### Strengths

- Die Grenze zwischen „was der Gang sieht" und „was erst danach sagbar ist" ist sauber: Hash-Vergleich im Gang, fehlende Anker und `exact` danach, `tip` aus der letzten gesehenen Zeile statt aus einer zweiten Abfrage — genau das, was der `Examination`-Docstring behauptet, und es stimmt.
- `pending: dict[int, list[bytes]]` mit `pop` erledigt doppelte und widersprüchliche Zeilen für eine Position ohne Sonderfall; `test_two_lines_for_one_position_are_both_checked` hält beides fest.
- `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one` und `test_an_appended_event_passes_contains_and_fails_exact` sind ehrlich gebaut: jeweils Kontrolle (`verify == []` bzw. `exact` in Ruhe `== ()`) und Wirkung in einem Test.
- Der Parser hält in meinem Experiment allen elf Grenzfällen stand und wirft nie etwas anderes als `InvalidPayload` (siehe Checks).
- Der Umsetzer hat die verweigerte Mutation nicht über einen anderen Weg erzwungen und das im Bericht klar als „nicht gemessen" ausgewiesen, statt den grünen Lauf danach als Messung auszugeben. Die Stelle für Mutation 2 nach der Verschiebung in `_closing_findings` hat er gleich mitgeteilt.
- Die Seite trennt die Zusage ohne Anker („Without one, the chain speaks for itself alone.") sauber von der mit Anker und nennt die `id` nicht „die wichtige Hälfte", sondern „length" — und begründet, warum der Hash allein das Präfix schon festnagelt.

### Bewertung der drei vorab bekannten Punkte

1. **Helfer `_closing_findings`.** Verhalten unverändert: derselbe Code, dieselbe Reihenfolge (Ketten- und Hash-Befunde im Gang, dann Zählbefund beim `break`, dann fehlende Anker sortiert, dann `exact`), dieselben drei Texte. Nachgezählt nach McCabe: der Brief-Rumpf hat 1 + `if exact and not anchors` + `for anchor` + `while` + `if not rows` + `if count_finding` + `for row` + `for anchored` + `if anchored !=` + `if exact` + `if tip_id > newest` = 11, nach der Verschiebung 9 — plausibel, nicht gemessen. Eine Aufgabe: „die Ankerbefunde, die erst nach dem Gang sagbar sind". Der Docstring-Verweis auf den Grund von `_check_event` (Schleife braucht die Verbindung, der Rest nicht) trifft zu. Liest sich nicht schlechter als die Einzelfunktion; dass `anchors` nur für `max(...)` hereingereicht wird, ist vertretbar (siehe Minor 4). Akzeptiert.
2. **Zwei Kommentare mit `verify`.** Getrennt beurteilt:
   - `verify.py:121` (`_check_event`-Docstring): „because `verify` would otherwise do two things at once: walk over batches and check an event" — **jetzt falsch**. `verify` geht über keinen Stapel mehr; der Gang ist `examine`. Und `_closing_findings` verweist ausdrücklich auf genau diesen Grund. → Important 2.
   - `verify.py:246` (Stapel-Kommentar): „and `verify` is the routine that runs over the whole history" — wörtlich noch wahr (`verify` läuft über `examine` über die ganze Geschichte), aber der Kommentar begründet Code in `examine`. → Minor 1.
   „Der Rumpf bleibt, Kommentare eingeschlossen" heißt nicht, dass ein Name im Kommentar falsch werden darf; ein umbenannter Bezeichner ist die mildeste Form, den Kommentar zu erhalten.
3. **Seite ohne `--anchors`/`--exact`.** Reicht. Die Seite erklärt die zwei Prüfarten als Begriffe (*contains*, *exact*), die Namen decken sich mit dem Parameter `exact` des Kerns; die Schalter sind Sache der Reference in Aufgabe 2. Für eine Explanation-Seite ist das die richtige Höhe. Nur der Testhelfer `_anchor_of` nennt `previously anchor` schon vorwärts — einen Task lang, laut Resolution 1 erlaubt.

### Mutationen — begründet aus dem Code, NICHT gemessen

| Mutation | Nach meiner Lesung rot | Begründung |
|---|---|---|
| `if anchored != row.hash:` → `if False:` | `test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor`, `test_two_lines_for_one_position_are_both_checked` (zweite Assertion), `test_anchors_are_checked_across_a_batch_boundary` (zweite Assertion) | alle drei erwarten `Finding(…, "hash does not match the anchor")`; mit `if False` bleibt `findings == ()`. Die erste Assertion des Stapeltests bliebe grün. |
| Block „anchored event is missing" entfernt (jetzt in `_closing_findings`) | `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one`, `test_an_empty_log_has_no_tip_and_misses_every_anchor` (zweite Assertion) | beide erwarten genau diesen Befund; sonst feuert dort nichts. |
| `if exact:` → `if False:` (in `_closing_findings`) | `test_an_appended_event_passes_contains_and_fails_exact` (letzte Assertion) | einziger Test, der den „continues past"-Befund erwartet. `test_exact_without_an_anchor_is_refused` hängt an der anderen Zeile `if exact and not anchors` und bliebe grün. |
| `len(fields) != 2` in `parse_anchors` entfernt | `test_a_broken_line_is_refused_with_its_line_number[…extra…]` und `[1-…]` | `id_text, hash_text = fields` wirft dann `ValueError` (too many / not enough values to unpack), nicht `InvalidPayload` → `pytest.raises(InvalidPayload)` schlägt fehl. |

Keine der vier bleibt nach meiner Lesung unentdeckt. Grüne Kontrolle: der vom Umsetzer berichtete Lauf `36 passed` auf unmutiertem Code. Weitere Mutationen, die ich durchgedacht habe: `tip_id > newest` → `>=` (rot: Ruhe-Assertion im Anhänge- und im Stapeltest), `max` → `min` (rot: Stapeltest erste Assertion, Anker 3 und 5), `pending.pop` → `pending.get` (rot: jeder Anker zusätzlich „missing"), `tip = …` entfernt (rot: `_anchor_of`). Unentdeckt bliebe `sorted(pending)` → `pending` (kein Test mit zwei fehlenden Ankern) und ein Abschalten der Fehlend-/Hash-Prüfung nur unter `exact=True` (siehe Minor 3).

### Issues

#### Critical

Keine.

#### Important

1. **`tests/test_verify.py` — `test_an_empty_log_has_no_tip_and_misses_every_anchor` (Docstring `"""Review focus 4."""`), dazu `test_anchors_are_checked_across_a_batch_boundary` („Review focus 3.") und `tests/test_anchor.py` `test_a_broken_line_is_refused_with_its_line_number` („`²` is review focus 5"). Plan-mandated.**
   Was falsch ist: Ein Label pro Plan ohne Planangabe. `docs/superpowers/plans/2026-10-03-dokumentation.md` hat ebenfalls eine „Review Focus"-Liste, und dort ist Punkt 4 der Vale-Geltungsbereich (Zeile 254) — wer „Review focus 4" im Baum nachschlägt, kann bei der falschen Entscheidung landen. Der erste Docstring besteht nur aus dem Zitat und bricht ohne es zusammen.
   Warum es zählt: `CLAUDE.md` („A ruling citation is provenance, never the reason"): Labels werden pro Plan vergeben, eine Zitierung nennt das Plandatum, und der Grund muss danebenstehen; ein Verweis, der auf die falsche Entscheidung auflöst, ist schlimmer als keiner. Die Regel ist für Rulings formuliert, trifft aber genau diesen Fall.
   Fix: „review focus 4 of the 2026-10-04 external-anchor plan" und den Grund in einem Satz daneben (für 4 etwa: „an empty log has no tip, so every anchor is missing and the log ends at 0").

2. **`src/previously/core/verify.py:121` — Docstring von `_check_event`: „because `verify` would otherwise do two things at once: walk over batches and check an event".**
   Was falsch ist: `verify` walkt keine Stapel mehr; das tut `examine`. Als Aussage über den heutigen Code ist der Satz falsch, und `_closing_findings` (Diff-Zeile 430) stützt seine eigene Begründung ausdrücklich auf ihn.
   Warum es zählt: „A comment is a claim" — eine falsche Aussage in Prosa; der Brief, der die Kommentare zu erhalten verlangte, hat die Umbenennung nicht bedacht.
   Fix: `verify` → `examine` in diesem Docstring.

#### Minor

1. `src/previously/core/verify.py:246` — „and `verify` is the routine that runs over the whole history": wörtlich noch wahr, begründet aber Code in `examine`; ebenfalls auf `examine` umstellen.
2. `docs/explanation/hash-chain.md:316` — „An external anchor closes two of the three" überzeichnet leicht: das Löschen der Spitze ist nur bis zum jüngsten Anker geschlossen, oberhalb nicht (Tabellenzeile 3, Abschnitt „The interval between anchors is the gap"). Vorschlag: „closes two of the three up to the newest anchor". Dazu steht Zeile 292 („Three manipulations pass, and no change to the code can stop them.") jetzt in Spannung zum Pointer; als Aussage über die Kette allein haltbar, ein Halbsatz („… the chain alone …") würde es glätten.
3. `docs/explanation/hash-chain.md:350-351` — Die Zellen *exact / seen* in den Zeilen „tip deleted, below the newest anchor" und „chain rewritten up to an anchor" sind wahr (die Fehlend- und Hash-Prüfung laufen unabhängig von `exact`), aber kein Test ruft dort `examine(..., exact=True)` auf. Die übrigen sechs Zellen sind von Tests gedeckt. Fix: in `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one` und `test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor` je eine Assertion mit `exact=True` und demselben Befund. Plan-mandated (Tests wortgleich aus dem Brief).
4. `src/previously/core/verify.py` `_closing_findings` — nimmt `anchors` nur für `max(anchor.id …)` entgegen; `newest: int | None` zu übergeben wäre schmaler. Geschmack, kein Fehler.
5. `tests/test_verify.py` `test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check` — es gibt keine sichtbare Kontrolle, dass Event 3 existierte und danach weg ist; nur indirekt über die `exact`-Assertion, die selbst vom Anhänge-Test gepinnt ist. `assert examine(storage).tip == anchor` nach dem Löschen (oder `tip.id == 3` davor) würde die Grenze für sich allein lesbar machen. Ehrlich ist der Test dennoch: beide Prüfarten werden behauptet, und er wird rot, wenn jemand die Lücke schließt.
6. `src/previously/core/anchor.py` — eine Zeile mit BOM (`"﻿1 <hash>"`) wird als `the id has to be a positive integer, got '﻿1'` abgelehnt. Für Aufgabe 1 korrekt (der Kern bekommt Zeilen), aber Review Focus 1 des 2026-10-04-Plans verlangt, dass eine BOM-Datei gelesen wird — Aufgabe 2 muss beim Öffnen `utf-8-sig` nehmen. Als Hinweis für Aufgabe 2, kein Fehler hier.

### Checks run

- Gelesen: `task-1-review-dispatch.md`, `task-1-brief.md`, `task-1-dispatch.md`, `task-1-report.md`, die Diff-Datei (vollständig).
- `git rev-parse HEAD` → `11de3f63…`; `git status --short` → leer.
- Risiko „weitere veraltete `verify`-Erwähnungen in `verify.py`": `grep -n verify src/previously/core/verify.py` → Zeilen 121, 169 (historische Messung `verify() -> []`, wahr), 246, 312 (Definition).
- Risiko „Review-focus-Labels mehrdeutig": `grep -n -i "review focus"` über Spec und `docs/superpowers/plans/` → Listen in `2026-10-03-dokumentation.md:121` und `2026-10-04-aeusserer-anker.md:60`; Punkt 4 der älteren Liste ist der Vale-Geltungsbereich (Zeile 254).
- Risiko „Seite behauptet noch ‚stage 1a has none' / Admonitions > 2": `grep -n -i "anchor\|stage 1a\|:::"` über `hash-chain.md` → „has none" nicht mehr da; „Stage 1a" nur in den Abschnitten über Erasure (Zeilen 42, 49, 52, 177, 194), sachlich unberührt; ein Admonition (Zeile 46).
- Risiko „die ‚drei' im Pointer-Satz": `hash-chain.md` Zeilen 270-314 gelesen → die drei sind Spitze löschen, selbstgehashtes Event anhängen, Kette von vorn umschreiben; Messung „three events, row 3 deleted, `verify: chain intact`" stimmt mit der neuen Seite und mit dem Test überein.
- Risiko „Satz über die `id` neben dem Hash": `grep` in `event_hash` (`src/previously/core/hashing.py`) → Zeile 144 `"id": event_id,`, Zeile 148 `"prev": prev_hash.hex() …` — beide Seitenaussagen wahr.
- Risiko „Kommentar-Begründung von `_closing_findings`": `verify.py:111-160` gelesen (`_check_event`-Docstring).
- Parser-Experiment (`scratchpad/parse_probe.py`, `uv run --directory <worktree> python …`), elf Eingaben: BOM vor der id → `InvalidPayload` (id); Fullwidth-Ziffern im Hash → `InvalidPayload` (not hexadecimal); arabisch-indische Ziffer als id → `InvalidPayload`; `007` → angenommen als 7; `+1` → `InvalidPayload`; 30-stellige id → angenommen; NBSP als Trenner → angenommen (`str.split()`); Inline-Kommentar → `InvalidPayload` (4 fields); `0x…` → `InvalidPayload` (not hexadecimal); `1_0` → `InvalidPayload`; 63×`a`+`g` → `InvalidPayload`. Nie eine andere Ausnahme.
- `uv run --directory <worktree> pytest --collect-only -q -p no:randomly` → `251 tests collected in 0.18s`; 11 in `test_anchor.py`, 25 in `test_verify.py` (17 + 8).
- Tutorial-Block (`scratchpad/count_dots.py`): 19 Dateizeilen, Punkte summieren sich zu 251, alle Prozentangaben gleich `kumuliert*100 // 251`; `collected 251 items` und `251 passed` stimmen überein; keine `rootdir:`-Zeile.
- `git log -1 --format=%B 11de3f6` → Nachricht wortgleich zum Brief, Trailer `Assisted-By: Claude Opus 5.5`.
- Nicht ausgeführt, laut Auftrag: die sechs Tore, die Testsuite, jede Mutation.

### Assessment

**Task quality:** Needs fixes

Der Kern ist korrekt, eng am Brief, ohne zweite Lesung, und die Tests pinnen sowohl, was der Anker schließt, als auch, was er nicht schließt. Zu beheben sind zwei kleine Prosa-Punkte — der jetzt falsche `verify` im `_check_event`-Docstring und die planbedingten, nicht nach Plan qualifizierten „Review focus"-Zitate —, und die vier Mutationen müssen noch gemessen werden, sobald der Maintainer das erlaubt.
