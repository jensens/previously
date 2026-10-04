# Task 6 — Prüfung (Opus), Diff `71dc078..a2dbe17`

Wörtlich, wie vom Prüfer zurückgegeben; Controller-Rulings stehen im Hauptbuch.

---

### Spec Compliance

- ❌ Issues found: zwei falsche Behauptungen in gelieferter Prosa — `src/previously/cli.py:328-336` (die `C901`-Begründung behauptet mehr als die Messung trägt, Wortlaut auch in der Commit-Nachricht) und `docs/reference/cli.md:19` (Exit-Code-Zelle nennt für das argumentlose `stats` „The input was invalid").
- ✅ Vollständigkeit gegen den Brief: alle vier beauftragten Dateien haben ihren Hunk (`cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/explanation/projections.md`) plus der Testlauf-Block im Tutorial; drei Unterkommandos, `escape_field`/`_plural`/`_describe`/`_lag_line`, Dispatch als Tabelle, `_cmd_verify(_args)`, neun neue Tests, 232 gesammelt.
- ✅ Auflösung 2 gehalten: `grep -n sqlalchemy src/previously/cli.py` findet nur das Wort in einem Kommentar (Zeile 358), keinen Import; `_lag_line(tip_id, up_to_id)` nimmt zwei Zahlen.
- ✅ Auflösung 3 (Ruling P-1): Reihenfolge in `_describe` (cli.py:197-204) ist Version → `events == 0` → `rebuilt_from == 0` → `caught up`; `if outcome.rebuilt_from:` unterscheidet `None`/`0`/`n>0` korrekt über Wahrheitswert.
- ✅ Auflösung 4 (F10) sitzt im richtigen Quadranten: `docs/explanation/projections.md:84`, ein Satz, nichts davon in `cli.md` oder im Code.
- ✅ Auflösung 5: `since == until` ist eine zusätzliche Zusicherung im bestehenden Fenstertest (`tests/test_cli.py`, Fall `empty`), kein neuer Test.
- ✅ Auflösung 7: Hilfetext `log` → „print the log in chain order"; `cli.md:46` sagt denselben Satz und `cli.md:14` zieht die Exit-Code-Zelle („The chronicle was printed" → „The log was printed") nach, was der Brief nicht verlangt hatte.
- ✅ Prüfung 1 der Beauftragung: `cli.py:252` liest `limit + 1`, `cli.py:261` druckt die Kappung nur bei `len(rows) > limit`; leeres Fenster → `rows == []` → weder Kappungssatz noch `stdout`; `cli.py:251` liest `projection_state(conn, "chronicle")`, `cli.py:277` `"source-stats"`, beide mit `tip` in derselben Transaktion.
- ⚠️ Nicht aus dem Diff prüfbar: die acht Mutationen im Bericht (laut Auftrag nicht nachgemessen) — der Controller sollte nichts davon als gemessen weiterverwenden, was dort nur behauptet ist.
- ⚠️ Nicht aus dem Diff prüfbar: die sechs Torausgaben sind im Bericht mit `...` gekürzt; dass `pytest` keine Warnungen ausgibt, stützt nur der getippte Tutorial-Block (echter Lauf, Abschlusszeile ohne `warnings`).

### Strengths

- Der getippte Testlauf-Block ist eine echte Messung, nicht eine Hand-Edition: `collected 232`, Summe aller Punkte = 232, jede Prozentzahl = abgeschnittener Kumulativwert, und alle 18 Dateizahlen stimmen exakt mit `uv run pytest --collect-only -q -p no:randomly` im Baum überein (test_cli.py 35); keine `rootdir:`-Zeile, kein Maschinenpfad, keine Warnungszeile.
- Die zwei zusätzlichen Hunks sind inhaltlich richtig und reine Prosa: `grep -c "print(" src migrations` → nur `src/previously/cli.py:19`, und `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src migrations` → „Found 19 errors"; der Hunk in `tests/test_docs_references.py` fasst nur den Docstring neu um, der Assertion-Körper bleibt unberührt.
- Die drei Teständerungen schließen drei echte Lücken, die die Brief-Fassung gelassen hätte: `rebuilt:` mit 0 Events (die einzige Lage, in der Ruling P-1 überhaupt messbar ist), `rebuilt:` mit Events, und der Rückstandszweig von `stats`; die zweite Hälfte von `test_both_reading_commands_report_the_lag_…` zieht die beiden Lesezeichen per `UPDATE projection_state SET up_to_id = 0` auseinander — erst dadurch liefert das falsche Lesezeichen eine andere Zahl, und „jedes Kommando liest sein eigenes Lesezeichen" ist eine Messung statt eines Kommentars.
- Beide umbenannten Tests behalten die Zusicherung des alten Namens wörtlich (`out == ""` plus der Rückstandssatz für `chronicle`; `up to date, up_to_id 0` für das leere Log) und die neuen Namen benennen genau die hinzugefügte Hälfte — `…_but_still_names_a_rebuild` und `test_both_reading_commands_…` sind ehrlich.
- Die Kappung über `limit + 1` hat ihre grüne Kontrolle direkt daneben (`--limit 3` bei drei Zeilen: kein Satz), und der Kommentar bei `cli.py:249-251` begründet, warum das Zählen der gedruckten Zeilen das nicht könnte.
- `escape_field` ist öffentlich mit dem Grund im Docstring, kein `reportPrivateUsage`; keine `# noqa`, kein `# type: ignore` in beiden Dateien (`grep -c` → 0/0), die Liste der fünf Unterdrückungen in `CLAUDE.md` bleibt richtig.
- `cli.md` widerspricht keinem der sieben Hilfetexte; `project`/`chronicle`/`stats` übernehmen die Formulierung des jeweiligen `help=` wörtlich erweitert.

### Issues

#### Critical (Must Fix)

- Keine.

#### Important (Should Fix)

- `src/previously/cli.py:333-334` — „So the chain would pass — one branch short of breaking the gate, which is the argument for writing the table at the seventh command rather than at the eighth" ist falsch; gemessen am 2026-10-04: `C901` schlägt strikt oberhalb der Schwelle zu (`--config 'lint.mccabe.max-complexity = 2'` meldet das heutige `main` bei 2 **nicht**, bei `= 1` meldet es „`main` is too complex (2 > 1)"), die rekonstruierte `if`-Kette mit sieben Kommandos steht bei 9 (bei Schwelle 9 nicht gemeldet), und eine Kette mit einem achten Kommando steht bei 10 und wird bei der Projektschwelle 10 ebenfalls **nicht** gemeldet. Die Kette wäre also zwei Zweige von der Torverletzung entfernt, nicht einen, und das Tor bräche erst beim neunten Kommando (11 > 10) — die Schlussfolgerung „beim siebten statt beim achten" folgt aus der Messung nicht. Nach „Ein Kommentar ist eine Behauptung" ist das der Fehlertyp, den der Plan-Widerspruch gerade heilen sollte. Korrektur: „zwei Zweige" bzw. „das Tor bräche beim neunten Kommando", oder das Abstandsargument streichen und nur die Struktur begründen. Dieselbe Formulierung steht in der Commit-Nachricht von `a2dbe17` („One branch short of breaking the gate is not a margin worth carrying") — die lässt sich nur per Amend ändern; mindestens der Kommentar muss stimmen, und die Abweichung ist zu vermerken. (Nebenbefund derselben Stelle: die 13 bei `cli.py:335` ist aus dem Vorgängerkommentar übernommen und nicht nachgemessen — der Bericht sagt das, der Kommentar sagt nicht, dass es eine historische Zahl zu einer Fassung ist, die es im Baum nicht mehr gibt.)
- `docs/reference/cli.md:19` — die Exit-Code-Zeile für `stats` nennt als Ursache von 2 „The input was invalid, or storage raised an error", aber `stats` hat keine Argumente (`cli.md:125` sagt es selbst, `cli.py:303` legt keinen Parameter an). Die Seite hält ihre eigene Konvention zwei Zeilen darüber anders: `project` (ebenfalls argumentlos, `cli.md:17`) und `verify` (`cli.md:11`) nennen nur „Storage raised an error." Die Zelle verspricht damit eine Ursache, die nicht auftreten kann. **Plan-mandatiert** (Brief Schritt 5 verlangt „`chronicle` und `stats`: … 2 ungültige Eingabe oder Storage-Fehler"), Behebung ist eine Tabellenzelle.

#### Minor (Nice to Have)

- `docs/reference/cli.md:83` — Bedingung für `up to date` lautet „No event was projected.", gilt aber auch für den Fall `rebuilt: version 2 -> 1, 0 events, up_to_id 0`, den `tests/test_cli.py` pinnt; die Tabelle sagt nicht, dass die Versionsprüfung vorgeht. Vorschlag: „No event was projected, and the version was unchanged."
- `docs/reference/cli.md:129` — „…, because there is no source to attribute it to" ist eine Begründung im Referenz-Quadranten (sie spiegelt den Docstring von `src/previously/core/projection/source_stats.py:42-44`); die Tatsache allein genügt hier, der Grund steht auf der Erklärseite. Die Tatsache selbst ist geprüft und stimmt: `derive` überspringt Ereignisse ohne Attributionsschlüssel.
- `src/previously/cli.py:252` und `:261` — `--limit` wird nicht geprüft: `chronicle --limit 0` liest eine Zeile, druckt keine und meldet dann „output truncated at 0 lines; raise --limit…", obwohl nichts gekappt wurde; `--limit -2` gibt `LIMIT -1` an Postgres weiter, und `read_chronicle` (`src/previously/storage/postgres.py:471`) hat keine Schranke und wickelt den DBAPI-Fehler nicht in `StorageError`. Geerbt, nicht eingeführt: `read` für `log` ist seit Stufe 1a genauso offen (`postgres.py:224`) — aber Task 5 hat `batch_size 0` abgewiesen, der Projektmaßstab läge also höher.
- `src/previously/cli.py:337-350` — kein Test pinnt, dass jeder Unterparser-Name einen Tabelleneintrag hat; mit dem (beauftragt) entfallenen `return 2` wird ein vergessener Eintrag zum `KeyError`-Traceback statt zu Rückgabecode 2. Eine Zusicherung `set(sub.choices) == set(commands)` würde das tragen.
- `docs/reference/cli.md:99` verspricht „two empty fields in place of `source` and `external_id`", und der Zweig `row.source or ''` (`cli.py:256`) ist laut `src/previously/core/projection/chronicle.py:50` konstruktionsgemäß erreichbar, aber kein Test erzeugt ihn; die 100 % Zeilenabdeckung von `cli.py` verdeckt das, weil Zweigabdeckung nicht an ist. Dieselbe Klasse wie die `rebuilt:`-Lücke, die der Implementierer geschlossen hat.
- `pyproject.toml:90-94` — „The count is measured against this configuration with this one entry lifted" steht neben einem Befehl, der mit `lint.per-file-ignores = {}` die ganze Tabelle leert (identisches Ergebnis, weil nur `src/previously/cli.py` als Pfad folgt, aber Satz und Befehl sagen nicht dasselbe); und „it has gone stale twice already: it read nine while ruff reported thirteen" nennt den ersten Fall Veralten, während der ersetzte Kommentar ihn als bloß falsche Zahl beschrieb.
- `tests/test_cli.py:501` — die zitierte `ruling P-1` ist nicht nachschlagbar: `CLAUDE.md` verlangt seit 2026-10-04 das Protokoll unter `docs/superpowers/sdd/<Plandatum>-<Planname>/`, dieses Plans Protokoll liegt noch im von `.gitignore` ausgeschlossenen `.superpowers/sdd/…`. Der Grund steht daneben, das Etikett ist also nur Herkunft — der Umzug ist Sache des Controllers bzw. einer späteren Aufgabe, nicht dieser.

### Assessment

**Task quality:** Needs fixes
**Reasoning:** Funktional ist die Aufgabe sauber und die Testarbeit überdurchschnittlich — die drei Umbauten machen drei zugesagte Ausgabeformate erstmals messbar, und der getippte Block ist nachgerechnet eine echte Messung; zu reparieren sind zwei Prosa-Behauptungen: der `C901`-Kommentar ist um einen Zweig zu scharf formuliert (gemessen: Kette 9, Schwelle wirkt erst oberhalb, achtes Kommando noch grün) und die Exit-Code-Zelle für das argumentlose `stats` nennt eine unmögliche Ursache.
