# Task 6 — Bericht: die Kommandos `project`, `chronicle`, `stats`

Commit `a2dbe17` auf `worktree-stufe-1b-projektionen`, Arbeitsbaum sauber.

## Was umgesetzt wurde

`src/previously/cli.py`

- `escape_field(text) -> str` (öffentlich, Auflösung 1 der Beauftragung):
  Rückstrich, Tabulator, Umbruch, Wagenrücklauf je zwei Zeichen, Rückstrich
  zuerst.
- `_plural(n, noun)`, `_describe(outcome)`, `_lag_line(tip_id, up_to_id)` —
  `_lag_line` nimmt zwei Zahlen, nicht die Verbindung (Auflösung 2); `cli`
  importiert nichts aus SQLAlchemy.
- `_cmd_project`, `_cmd_chronicle`, `_cmd_stats`; `_cmd_verify` bekommt
  `_args: argparse.Namespace`, damit alle sieben Kommandofunktionen eine
  Signatur haben.
- Drei Unterparser; `--since`, `--until`, `--limit` (Vorgabe 50) an
  `chronicle`.
- Der Dispatch in `main` ist eine Tabelle; der unerreichbare
  `return 2  # pragma: no cover` fällt weg.
- Hilfetext von `log`: „print the chronicle" → „print the log in chain order"
  (Auflösung 7), mit Begründung im Kommentar darüber.

`tests/test_cli.py` — neun neue Tests, 26 → 35 in der Datei.

`docs/reference/cli.md` — sieben Unterkommandos, drei Zeilen in der
Exit-Code-Tabelle, drei neue Abschnitte, `{ref}`projections`` als Verweis für
das Warum. `docs/explanation/projections.md` — `## Two orders, two commands`
und `## Saying what it doesn't know`. `docs/tutorials/record-your-first-event.md`
— nur der Testlauf-Block, aus einem echten Lauf eingesetzt.

Zusätzlich zwei Zahlen, die meine eigenen `print`-Aufrufe widerlegt haben
(siehe Abweichung 1): `pyproject.toml` und
`tests/test_docs_references.py`.

## Rot

```
$ uv run pytest tests/test_cli.py -v -p no:randomly
...
tests/test_cli.py:6: in <module>
    from previously.cli import escape_field
E   ImportError: cannot import name 'escape_field' from 'previously.cli'
=========================== short test summary info ============================
ERROR tests/test_cli.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

Die zweite Hälfte der Erwartung (`argparse` kennt die drei Kommandos nicht)
verdeckt der `ImportError`, weil er die Sammlung abbricht. Deshalb separat
gegen dieselbe unveränderte `cli.py` gemessen:

```
$ uv run python -c "from previously.cli import main; main(['project'])"
previously: error: argument command: invalid choice: 'project'
            (choose from append, log, verify, show)
['project'] -> SystemExit 2
['chronicle'] -> SystemExit 2
['stats'] -> SystemExit 2
```

## Grün

```
$ uv run pytest tests/test_cli.py -v -p no:randomly
...
tests/test_cli.py::test_escape_field_folds_tab_newline_return_and_backslash_into_two_characters_each PASSED
tests/test_cli.py::test_project_on_an_empty_log_is_up_to_date_at_zero_but_still_names_a_rebuild PASSED
tests/test_cli.py::test_project_says_which_path_it_took PASSED
tests/test_cli.py::test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source PASSED
tests/test_cli.py::test_both_reading_commands_report_the_lag_on_stderr_and_only_there PASSED
tests/test_cli.py::test_chronicle_window_is_half_open_and_an_empty_window_is_not_truncated PASSED
tests/test_cli.py::test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise PASSED
tests/test_cli.py::test_chronicle_rejects_a_naive_since PASSED
tests/test_cli.py::test_stats_prints_one_line_per_source PASSED

============================= 35 passed in 13.09s ==============================
```

## Mutationen: jede Zusage einmal rot gemessen

Die Kontrolle ist der unmutierte Lauf oben, 35 grün. Jede Mutation wurde
einzeln angewandt, `tests/test_cli.py` lief dazu, danach wurde die Datei
wiederhergestellt.

| Mutation | rot |
|---|---|
| `escape_field`: Rückstrich zuletzt statt zuerst | `test_escape_field_…`, `test_chronicle_prints_one_line_per_unit_…` (2 failed, 33 passed) |
| `_describe`: `events == 0` über die Versionsabfrage gehoben | `test_project_on_an_empty_log_…_but_still_names_a_rebuild` (1/34) |
| `_describe`: `built`-Zweig gelöscht (erster Bau als „caught up") | `test_project_says_which_path_it_took` (1/34) |
| `_describe`: `rebuilt`-Zweig ganz gelöscht | beide `project`-Tests (2/33) |
| `_lag_line`: `lag < 0` statt `<= 0` (Rückstand 0 wird gedruckt) | vier Tests (4/31) |
| `chronicle`: `>=` statt `>` bei der Kappung | `test_chronicle_limit_warns_…` (1/34) |
| `_cmd_stats` liest das Lesezeichen von `chronicle` | `test_both_reading_commands_report_the_lag_…` (1/34) |
| `_cmd_chronicle` liest das Lesezeichen von `source-stats` | `test_both_reading_commands_report_the_lag_…` (1/34) |

Die letzten drei Zeilen sind der Grund für zwei Änderungen am Zuschnitt der
Tests, siehe Abweichungen 2 und 3: ohne sie waren `rebuilt:` und der
Rückstand von `stats` Formate, die die Referenzseite zusagt und nichts
erzeugt — und der Satz „jedes Kommando liest das Lesezeichen seiner eigenen
Projektion" war eine Behauptung ohne Messung.

## Die sechs Tore

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
48 files already formatted

$ uv run pyright
0 errors, 0 warnings, 0 informations

$ uv run lint-imports
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT
Only storage imports sqlalchemy KEPT
No vendor SDK in stage 1a KEPT
Contracts: 4 kept, 0 broken.

$ uv run pytest --cov --cov-report=term-missing
src/previously/cli.py                              159      0   100%
TOTAL                                              744     20    97%
Required test coverage of 90.0% reached. Total coverage: 97.31%
============================= 232 passed in 20.55s =============================

$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded.
✔ 0 errors, 0 warnings and 0 suggestions in 21 files.
build succeeded.
```

232 wie beauftragt (223 + 9). `cli.py` steht bei 100 % Zeilenabdeckung.

## Geänderte Dateien

- `src/previously/cli.py`
- `tests/test_cli.py`
- `docs/reference/cli.md`
- `docs/explanation/projections.md`
- `docs/tutorials/record-your-first-event.md`
- `pyproject.toml` — nicht in der Liste der Beauftragung, siehe Abweichung 1
- `tests/test_docs_references.py` — ebenso, Abweichung 1

`git status --short` war vor dem `git add` genau diese sieben und sonst
nichts.

## Abweichungen

1. **Zwei Dateien mehr als die Liste in Auflösung 8.** Die drei Kommandos
   bringen `cli.py` von dreizehn auf neunzehn `print`-Aufrufe. Zwei Stellen
   nannten die dreizehn als Zahl: die Begründung der `T201`-Ausnahme in
   `pyproject.toml` und der Docstring von
   `test_no_program_output_cites_a_specification`. Gemessen gegen die
   Projektkonfiguration mit nur dieser einen Ausnahme gehoben —
   `ruff check --select T201 --config 'lint.per-file-ignores = {}'
   src/previously/cli.py` → `Found 19 errors`, und über `src` und
   `migrations` ist `cli.py` weiterhin die einzige Datei mit Treffern. Nach
   „Ein Kommentar ist eine Behauptung" ist eine Zahl, die mein Commit falsch
   macht, in meinem Commit zu korrigieren; Auflösung 8 liest sich als Schutz
   vor fremden Änderungen im Baum, nicht als Verbot einer notwendigen
   Folgeänderung. Beide Stellen sagen jetzt neunzehn und nennen das
   Messkommando. **Wenn der Zuschnitt anders gewollt ist, sind das zwei
   isolierte Hunks.**

2. **Ein Testname geändert, eine Zusage mehr geprüft.**
   `test_chronicle_reports_the_lag_on_stderr_and_only_there` heißt
   `test_both_reading_commands_report_the_lag_on_stderr_and_only_there` und
   prüft `stats` daneben. Grund: `_cmd_stats` kam ohne das nie in den
   Rückstandszweig (Zeile 288 war die einzige unabgedeckte Zeile in `cli.py`),
   und die Mutation „`stats` liest das Lesezeichen von `chronicle`" überlebte.
   Der zweite Teil zieht die beiden Lesezeichen per SQL auseinander, weil nur
   dann das falsche Lesezeichen eine andere Zahl liefert.

3. **Zwei bestehende Tests um je einen Fall erweitert**, nach dem Muster von
   Auflösung 5 (eine Zusicherung mehr, kein neuer Test, Zahl bleibt neun):
   - `test_project_says_which_path_it_took` setzt am Ende
     `projection_state.version = 2` für `chronicle` und erwartet
     `rebuilt: version 2 -> 1, 2 events, up_to_id 2` neben
     `source-stats    up to date, up_to_id 2`. Ohne das war `rebuilt:` ein
     Format, das `cli.md` zusagt und nichts erzeugt (Zeile 104 unabgedeckt).
   - `test_project_on_an_empty_log_is_up_to_date_at_zero` heißt jetzt
     `…_but_still_names_a_rebuild` und prüft im zweiten Teil
     `rebuilt: version 2 -> 1, 0 events, up_to_id 0`. Das ist die einzige
     Lage, in der die Reihenfolge aus Auflösung 3 (Ruling P-1) überhaupt
     messbar ist: Versionswechsel **mit** null Events.

4. **Die C901-Begründung des Plans ist widerlegt, und der Kommentar sagt
   jetzt die Messung.** Der Plan schreibt, sieben `if`-Zweige plus
   `try/except` sässen „genau auf der Schwelle". Gemessen am 2026-10-04 mit
   `ruff check --select C901 --config 'lint.mccabe.max-complexity = N'
   src/previously/cli.py`: die Kette bringt `main` auf 9 bei einer Schwelle
   von 10, die Tabelle auf 2. Die Kette wäre also **grün** durchgekommen,
   einen Zweig unter der Schwelle. Die Tabelle bleibt — aber als
   Abstandsargument, nicht als Torverletzung, und Kommentar wie
   Commit-Nachricht sagen das so. (Die Zahl 13 aus der Vorgeschichte ist
   unverändert korrekt übernommen und nicht neu gemessen; sie stammt aus
   einer Fassung, die es im Baum nicht mehr gibt.)

5. **`_append` im Test ist zweizeilig** statt ein `assert` über 100 Zeichen,
   und die drei Fensteraufrufe in `test_chronicle_window_…` benennen ihre
   Argumentlisten (`inside`, `backward`, `empty`), weil `ruff format` die
   Fassung des Plans in `assert (\n … \n == 0\n)` zerlegt hätte.
   `escape_field` steht als eine Zeile, weil `ruff format` die Kette
   zusammenzieht (99 Zeichen).

6. **`_setup` aus dem Plan behalten**, obwohl die Beauftragung sagt, bei
   Abweichung gewinne das Muster im Baum. Die beiden weichen nicht ab:
   `_setup` enthält genau die drei Zeilen, die die bestehenden `db`-Tests
   inline haben (`from sqlalchemy import Engine`, `isinstance`,
   `render_as_string(hide_password=False)`). Wo ein Test zusätzlich rohes SQL
   braucht, steht der `isinstance`-Anker wie bisher im Test selbst, damit
   pyright `db` dort verengt.

7. **Formulierungen in `cli.md` an die Hilfetexte angeglichen** (zwei
   Sätze): „Prints the chronicle in time order, one line per unit." und
   „Prints the per-source statistics, one line per source." — damit Seite und
   `--help` wörtlich übereinstimmen.

## Selbstprüfung

- Alle sieben Hilfetexte gegen `cli.md` gelesen; keine Aussage widerspricht
  der anderen.
- Keine Zitation in Programmausgabe: die neuen `print`-Zeichenketten tragen
  weder `{ref}` noch das Absatzzeichen; `test_no_program_output_cites_a_specification`
  grün. Das Absatzzeichen in den beiden Test-Docstrings steht auf einer Zeile
  mit „(frozen design record)", wie `test_no_bare_paragraph_references_remain`
  es verlangt.
- Kein `# type: ignore`, kein `# noqa`, keine neue Unterdrückung; die Liste
  der fünf in `CLAUDE.md` bleibt unverändert richtig.
- Keine Attrappe, kein Zeitstempel-Mock; alle neun Tests laufen gegen echtes
  PostgreSQL im Container.
- `worker.py` nicht angefasst (Auflösung 6); die Docstring-Zitation von
  `Outcome` landet jetzt auf den beiden neuen Abschnitten.
- Tutorial: nur der Testlauf-Block, aus einem echten `uv run pytest`
  eingesetzt, ohne `rootdir:`-Zeile und ohne Maschinenpfad.
- Nichts am elterlichen Checkout.

## Bedenken

1. **`README.md` ist ab diesem Commit veraltet.** Zeile 29 sagt „the four
   commands `append`, `log`, `verify` and `show`", und der Abschnitt „What it
   does not do" nennt „no projections (header, chronicle as a view — stage
   1b)". Beides gehört laut Zuschnitt zu Task 7 — aber eine Seite, die
   nachläuft, wird als aktuell gelesen. Task 7 muss beide Stellen anfassen.
2. **Das Tutorial nennt `log` eine Chronik.** Die Überschrift „## Look at the
   chronicle" über `previously log` kollidiert jetzt mit dem Kommando
   `chronicle`. Die Beauftragung erlaubt mir im Tutorial nur den
   Testlauf-Block, also bleibt es stehen; Task 8 sollte es mit den getippten
   Abschnitten umbenennen.
3. **Die beiden `stderr`-Sätze auf `cli.md` prüft kein Tor.** Die Tests
   pinnen sie, aber gegen die Seite hält sie nichts — anders als bei
   `hash-format.md`, wo `test_the_reference_quotes_what_the_code_actually_prints`
   die Nachrichten erzeugt und vergleicht. Dieselbe Lücke haben die
   Ausgabeformate von `log` und `show` seit Stufe 1a. Ein Test nach dem
   Vorbild jener Prüfung wäre machbar, hätte aber die zugesagte Zahl 232
   bewegt; ich habe es deshalb nicht gebaut, sondern melde es.
4. **Der Modul-Docstring von `cli.py` heißt weiter „The minimal submission
   path"** und spricht von Stufe 1a. Mit drei Lesekommandos mehr stimmt der
   Satz nicht mehr ganz; ich habe ihn nicht angerührt, weil er nicht zum
   Auftrag gehörte.
5. **`stats` kennt die Spalte `last_event_id` nicht.** `SourceStatsRow` trägt
   sie, die Ausgabe hat fünf Felder nach Spezifikation §6.4. Kein Fehler,
   nur eine Information, die auf keinem Weg nach draußen kommt.
6. **Die zitierte Ruling P-1 ist noch nicht nachschlagbar.** Ein Docstring in
   `tests/test_cli.py` nennt sie als Herkunft. `CLAUDE.md` verlangt seit
   2026-10-04, dass das Protokoll unter
   `docs/superpowers/sdd/<Plandatum>-<Planname>/` liegt; dort steht bislang
   nur `2026-10-03-dokumentation`, während das Protokoll dieses Plans im von
   `.gitignore` ausgeschlossenen `.superpowers/sdd/…` liegt — samt diesem
   Bericht, weil die Beauftragung diesen Pfad nennt. Der Satz neben der
   Zitation trägt den Grund allein, die Prüfung „ohne das Etikett hält es
   noch" also bestanden; nachschlagbar wird P-1 erst mit dem Umzug.

---

# Fixrunde 1 — Bericht

Commit `daea417`, Elternteil `eae7357` (Plankorrektur des Controllers).
Vier Dateien, wie beauftragt: `src/previously/cli.py`, `tests/test_cli.py`,
`docs/reference/cli.md`, `pyproject.toml`. `git status --short` vor dem
`git add` war genau diese vier und sonst nichts; danach sauber.

## I1 — der C901-Kommentar

Selbst nachgemessen, nicht übernommen. Mit
`ruff check --select C901 --config 'lint.mccabe.max-complexity = N'
src/previously/cli.py` und einer Kette, der je ein weiterer
`if args.command == …`-Zweig angehängt wurde:

```
if chain, 7 commands: C901 `main` is too complex (9 > 8)   (feuert zuerst bei N=8)
if chain, 8 commands: C901 `main` is too complex (10 > 9)  (feuert zuerst bei N=9)
if chain, 9 commands: C901 `main` is too complex (11 > 10) (feuert zuerst bei N=10)
dispatch table:       C901 `main` is too complex (2 > 1)   (feuert zuerst bei N=1)
```

Der Prüfer hat recht, und zwar genau: `C901` feuert strikt oberhalb der
Schwelle, bei Projektschwelle 10 wäre das **achte** Kommando mit 10 noch
grün, erst das neunte mit 11 rissig. Zwei Zweige Luft. Kein Widerspruch.

Der Kommentar steht jetzt in drei Absätzen: erst der **strukturelle** Grund
(der Dispatch ist die eine Stelle, die mit jedem Kommando wächst; ein Lookup
fügt keinen Zweig hinzu, jedes `if` einen), dann die Messung mit allen vier
Zahlen, dem Satz „fires strictly **above** its threshold", dem achten
Kommando als noch grün und dem neunten als rissig — und ausdrücklich, dass
Plan und erste Kommentarfassung in dieselbe Richtung falsch lagen. Der
dritte Absatz kennzeichnet die **13** als historische Zahl aus einer Fassung,
die es im Baum nicht mehr gibt, nicht neu gemessen.

Die Botschaft von `a2dbe17` bleibt unangetastet; die von `daea417` nennt die
Abweichung in ihrem ersten Absatz.

## I2 — `cli.md`, Rückgabecode 2 von `stats`

`| stats | … | Not used. | Storage raised an error. |` — wie `project` und
`verify`. Gegengeprüft, dass die Zelle stimmt: `stats` hat keinen
Unterparser-Parameter, also ist `_storage()` der einzige Weg zu
`PreviouslyError` („PREVIOUSLY_DSN is not set"), und das ist
Konfiguration, kein Argument. Für `chronicle` bleibt „The input was invalid"
stehen und ist jetzt durch zwei Pfade belegt, `--since`/`--until` ohne Zone
und `--limit` unter 1.

## Die fünf Minors

1. **`cli.md:83`** — `| up to date, up_to_id <id> | No event was projected,
   and the version was unchanged. |`. Die Tabelle sagt damit, dass die
   Versionsprüfung vorgeht, was der Test
   `…_but_still_names_a_rebuild` mit `rebuilt: version 2 -> 1, 0 events`
   pinnt.
2. **`cli.md:129`** — Grund gestrichen, Tatsache bleibt: „An event with no
   source attribution appears in no line." Nachgeprüft, dass der Grund
   wirklich auf der Erklärseite steht: `projections.md`, Abschnitt „What the
   two tables are for" — „From `p_source_stats` that same event is absent
   altogether, because there's no source it could be attributed to".
3. **`pyproject.toml:90-94`** — Satz nach dem Befehl formuliert: der Befehl
   leert mit `lint.per-file-ignores = {}` die **ganze** Tabelle, also auch
   die `tests/*`-Zeile, was hier nichts kostet, weil der Befehl eine Datei
   unter `src/` nennt. Und: „has been wrong twice: it read nine against
   thirteen, which was a miscount and not a drift, and then thirteen until
   stage 1b's three commands took it to nineteen".
4. **`--limit < 1`** — in `_cmd_chronicle`, **vor** `parse_moment` und vor
   jedem Lesen: `raise InvalidPayload(f"--limit must be at least 1, got
   {args.limit}")`. **Entscheidung gegen ein argparse-`type=`**, am Code
   begründet: ein `type=`-Aufruf, der wirft, geht über `parser.error()` nach
   `sys.exit(2)` — ein echter Prozessabbruch statt eines `return 2` aus
   `main`, und genau dagegen existiert `_parse_evidence` statt `choices=`
   (Befund W2, „both branches return exit code 2"). `catch_up` weist sein
   `batch_size` unter 1 mit demselben Satzbau ab, das ist die Entsprechung im
   Baum. Der Kommentar nennt beides.

   Das alte Verhalten ist **gemessen**, nicht vermutet — mit entfernter
   Prüfung gegen das echte PostgreSQL 17:

   ```
   limit=0  code=0  out=''  err='output truncated at 0 lines; raise --limit or narrow --since/--until'
   limit=-2 sqlalchemy.exc.DataError: (psycopg.errors.InvalidRowCountInLimitClause)
            LIMIT must not be negative
   ```

   Der negative Fall ist damit **schärfer als beauftragt**: nicht nur „roh an
   PostgreSQL gereicht", sondern eine fremde Ausnahme, die `main` nicht
   fängt — ein Traceback und Rückgabecode 1 des Interpreters statt 2,
   die Klasse von Befund W2. Kommentar in `cli.py` und Testkommentar sagen
   jetzt diese Messung. (Die Formulierung in der Commit-Botschaft, „reached
   PostgreSQL raw", ist die beauftragte und bleibt wörtlich stehen.)

   Als Zusicherung in `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise`
   gefaltet, `0` und `-2` in einer Schleife, kein neuer Test. `log --limit`
   nicht angefasst.
5. **Der quellenlose Zweig** — in
   `test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source`
   kommt ein drittes Event ohne `source_key` über
   `PostgresStorage(db).insert_event(conn, EventRow(3, …, tip.hash, …, {}),
   [UnitRow(3, 1, "orphan")], None)` hinzu, `occurred_at` auf
   `2026-10-01T12:00`, damit es in der Zeitordnung **zwischen** die beiden
   anderen fällt und die Ordnung mitgeprüft bleibt. Erwartet sind jetzt drei
   Zeilen, die mittlere `3\t1\t2026-10-01T12:00:00+00:00\t\t\torphan`. Zahl
   bleibt 232.

## Beide neuen Zusicherungen rot gemessen

Kontrolle: unmutiert 35 grün in `tests/test_cli.py`.

| Mutation | rot |
|---|---|
| `if args.limit < 1: raise …` entfernt | `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise` (1 failed, 34 passed) |
| `row.source or ''` → `row.source` (und ebenso `external_id`) | `test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source` (1 failed, 34 passed) |

## Die sechs Tore, Schlusszeilen ungekürzt

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
48 files already formatted

$ uv run pyright
0 errors, 0 warnings, 0 informations

$ uv run lint-imports
Contracts: 4 kept, 0 broken.

$ uv run pytest --cov --cov-report=term-missing
Required test coverage of 90.0% reached. Total coverage: 97.32%
============================= 232 passed in 26.27s =============================

$ make -C docs html
build succeeded.

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 21 files.

$ make -C docs linkcheck
build succeeded.
```

`cli.py` bleibt bei 100 % Zeilenabdeckung; die Projektsumme geht von 744 auf
746 Anweisungen (die zwei Zeilen der `--limit`-Prüfung), unerreicht bleiben
dieselben 20 wie vorher, 19 davon in `contract/store.py` und eine in
`append.py`. Die getippte Zahl im Tutorial ist unverändert richtig: es kam
kein Test hinzu, nur Zusicherungen in bestehenden, und
`test_docs_typed_output.py` ist grün.

## Widerspruch

Keiner. Alle sieben Punkte angenommen; I1 habe ich vor der Umsetzung selbst
nachgemessen und bestätige die Messung des Prüfers Zahl für Zahl.

## Was weiterhin offen steht (nicht in dieser Runde)

- `README.md:29` („the four commands …") und der Absatz „What it does not do"
  mit „no projections" bleiben veraltet — Aufgabe 7.
- Die Tutorial-Überschrift „## Look at the chronicle" über `previously log`
  bleibt, weil mir dort nur der Testlauf-Block erlaubt ist — Aufgabe 8.
- Wie beauftragt nicht angefasst: `set(sub.choices) == set(commands)` als
  eigener Test, `log --limit` unter 1, und `ruling P-1` nachschlagbar machen.
