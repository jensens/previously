# Task 8 — Re-Review Fixrunde 1 (Sonnet), Diff `fee6d2b..4c52091`

Wörtlich, wie vom Prüfer zurückgegeben.

---

### Finding Verdicts

**I1 — "Not one line points at the specification of its own stage" war falsch.** ADDRESSED. `tests/test_cli.py:478` lautet jetzt `"""One unit is one line ({ref}\`cli-reference\`) plus review focus 3.` und `tests/test_cli.py:591` `"""Time order, not chain order ({ref}\`projections\`).` — kein `§` mehr in der Datei (`grep -rn "§" src tests migrations` listet 15 Treffer, keiner in `tests/test_cli.py`). Beide Label inhaltlich geprüft: `docs/reference/cli.md:90,102` trägt „one line per unit" und die Vier-Zeichen-Entschärfung (§6.3-Inhalt); `docs/explanation/projections.md:160-174` „Two orders, two commands" trägt Zeit- vs. Kettenordnung (§6.2-Inhalt) — beide Zuordnungen passen. `docs/explanation/design-records.md:81-82` (neue Zeilennummern im Fix) nennt jetzt den gemessenen Bereich „Measured over `src/`, `tests/` and `migrations/`" und fügt den Satz „Two citations in the test suite did point at this specification, as `§6.2` and `§6.3` … fix round 1 of the freezing task sent them to the pages" an. `uv run pytest tests/test_cli.py tests/test_docs_references.py -q` laut Bericht `40 passed` — Dateizahlen stimmen mit dem vollen Testlauf-Block überein (35 + 5 = 40).

**I2 — Abbildungstabelle ohne Architektur-Zeilen für §4.1/§4.4.** ADDRESSED. Diff `docs/explanation/design-records.md` fügt `| §4.1 | architecture | {ref}\`projections\` |` und `| §4.4 | architecture | {ref}\`projections\`; {ref}\`module-boundaries\` where the citation is about the two store protocols staying apart |` ein. Gegen die Kommentare geprüft, nicht gegen die Vermutung des Dispatchs: `src/previously/storage/schema.py:173` (§4.1, Zeitordnungs-Index) passt zu `projections.md:164` (zitiert dieselbe Architekturstelle); `src/previously/storage/schema.py:132` (§4.4, „carry no truth of their own") passt zu `projections.md:11-20` „Derivable and disposable" (zitiert §4.4 selbst); `src/previously/contract/store.py:66` (§4.4, Protokolltrennung) ist inhaltlich ein anderer Punkt und passt zu `docs/explanation/module-boundaries.md:271-274` — der Umsetzer hat das korrekt unterschieden statt die Dispatch-Vermutung blind zu übernehmen. Die Einleitung „§4.1, §4.4 and §5 appear twice each" stimmt mit der Tabelle überein.

**I3 — „Fourteen of the 72 still do" war 12.** ADDRESSED. Selbst gemessen: `git grep -o "§" cdc508a -- src tests migrations | wc -l` = 14 (Branchpunkt, deckt sich mit `main`); `git grep -o "§" 4c52091 -- src tests migrations | wc -l` = 15; `grep -rn "§" src tests migrations` im Arbeitsbaum listet genau 15 Zeilen, davon drei neu aus Stufe 1b (`contract/store.py:66` §4.4, `storage/schema.py:132` §4.4, `storage/schema.py:173` §4.1) → 15 − 3 = 12 der ursprünglichen 14 überleben, zwei fielen mit den `§12`-Zitaten in `tests/test_contracts.py` (dort bestätigt per `git show cdc508a:tests/test_contracts.py | grep -n "§12"` → Zeilen 175/213; `grep -rn "§12" src tests migrations` im Baum → leer). `design-records.md:10` sagt jetzt „Twelve of the 72 still do, two were dropped from error messages the user reads, two left with the test that cited them, and the remaining 56 name a page instead." — Rechnung 12+2+2+56 = 72, stimmt. Die Zeile `| §12 | stage 1a | nowhere; frozen design record, and no longer cited since stage 1b deleted the test that cited it |` ist angepasst statt gelöscht, wie gefordert.

**I4 — §10 Punkt 8 „zählt unter" war die falsche Richtung.** ADDRESSED. `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md:767-776` (neue Fassung) nennt jetzt alle drei Richtungen: `p_chronicle` (`PrimaryKeyConstraint("event_id", "seq")`, `src/previously/storage/schema.py:169`) plus `insert_chronicle` ohne `ON CONFLICT` (`src/previously/storage/postgres.py:381-400`, geprüft: kein `on_conflict_do_update` an dieser Stelle, nur bei `set_projection_state`/`upsert_source_stats`) → laute Unique-Verletzung; `source_stats.merge` addiert `events`/`units` (`src/previously/core/projection/source_stats.py:29-36`, geprüft) → Überzählung; Unterzählung nur über den Neubau-Pfad (`truncate_projection` + `up_to_id=0` in `worker.py:103-110`). Die Handlungshälfte (Sperre/`FOR UPDATE`/Advisory-Lock) blieb erhalten. Ruling T8-g korrekt angewendet: der Spec ist seit `fee6d2b` eingefroren, die Korrektur erfolgt trotzdem, weil die Aufgabe noch nicht abgeschlossen war.

**Minor „Heute kann sie niemand starten".** ADDRESSED. Jetzt „Heute startet das System keine zwei Läufe: der Arbeiter ist ein Kommando, und eine Warteschlange gibt es nicht (Punkt 4) — zwei Terminals können es trotzdem." (`…1b…:772-774`).

**Minor zwei Komma-Spleiße (Tutorial `:126`/`:144`).** ADDRESSED. Diff zeigt beide Stellen in je zwei Sätze/Zeilen gesplittet: „…and they start out empty." / „One command fills them both." und „…and the log hasn't grown since." / „There was nothing left to project."

**Minor Next-steps-Zusammenfassung.** ADDRESSED. `docs/tutorials/record-your-first-event.md` Next steps nennt jetzt „read the chronicle and the counts per source" zusätzlich zu den zwei Sichten — deckungsgleich mit der Einleitung.

**Minor README-Tabellendaten.** ADDRESSED. Diff `README.md:66-72`: alle drei älteren Zeilen tragen jetzt „Frozen design record, 2026-10-03: …", die 1b-Zeile bereits „2026-10-04" — vier Zeilen, eine Form.

**Minor Rohprotokoll des Testlaufs im Bericht.** ADDRESSED. `task-8-report.md` trägt jetzt am Ende den Anhang „Anhang: das Rohprotokoll des abgetippten Testlaufs" mit dem vollständigen `uv run pytest`-Output (Seed `1705979683`, 232 passed in 21.69s, Dateireihenfolge und Prozente), zeichengleich mit dem Tutorial-Block minus `rootdir:`-Zeile.

### New Breakage in the Fix Diff

None. Eigene Gegenproben: `make -C docs vale` → „✔ 0 errors, 0 warnings and 0 suggestions in 22 files." (bestätigt die im Bericht erwähnte Vale-Korrektur von „docstrings" zu „citations in the test suite"); `make -C docs html` → „build succeeded." mit `-W` (Warnungen als Fehler); `git status --short` vor und nach beiden Läufen leer — kein Eingriff in den Baum. Die Tabellenzeilen-Erweiterungen in `design-records.md` sind formal korrekt (bestehendes Zweispalten-Schema mit Qualifizierer, Präzedenz dafür existiert bereits in Zeilen wie §3.1/§4.2/§5/§9). Commit `51c3cfb` trägt `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`, kein `Co-Authored-By`, kein „Generated with".

### Out-of-Scope Observations

- `CLAUDE.md:72` zählt weiterhin „three frozen records" — laut Aufgabenstellung nicht Teil dieser Prüfung (Fixwelle), im Fixbericht als Bedenken 1 weiterhin offen notiert.
- Der Pfad `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md` in §10 verweist auf ein Verzeichnis, das laut Fixbericht (Bedenken 2) noch nicht existiert — bricht kein Tor, aber Ruling T8-a wäre erst mit dem Abschluss-Commit eingelöst. Vorbestehend aus der ersten Runde, nicht durch diesen Fix verändert.
- Commit `4c52091` (Controller-Plannotiz, Ruling T8-f dokumentiert) liegt wie angewiesen außerhalb der Prüfung — nur auf Isoliertheit geprüft: betrifft ausschließlich `docs/superpowers/plans/2026-10-04-stufe-1b-projektionen.md`, keine Überlappung mit den fünf Fix-Dateien.

### Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage.
