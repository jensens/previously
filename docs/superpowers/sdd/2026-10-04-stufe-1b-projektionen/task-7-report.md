# Task 7 — Bericht: How-to, `projections.md` letzter Abschnitt, README, Vokabular

Commit `773cf4a` auf `worktree-stufe-1b-projektionen`, Arbeitsbaum sauber.
Vorgänger `daea417`. Alle sechs Tore grün, Vale 0 Fehler in 22 Dateien,
`pytest` 232 passed (unverändert).

## Was geschrieben wurde, Abschnitt für Abschnitt

### 1. `docs/how-to/rebuild-a-projection.md` (neu, 82 Zeilen)

Label `(rebuild-a-projection)=`, Titel `# How to rebuild a projection`
(Abweichung, siehe unten), Eröffnung „This guide shows you how to …".
Drei Abschnitte mit den Titeln aus der Beauftragung, wörtlich:

- `## Check how far behind a projection is` — `previously chronicle`
  beziehungsweise `previously stats` laufen lassen; die Rückstandszeile auf
  `stderr` wörtlich aus `cli.py` `_lag_line` zitiert
  (`projection is 12 events behind; run \`previously project\``); Fehlen der
  Zeile heißt aktuell; beide Kommandos geben in jedem Fall 0 zurück, also
  `stderr` lesen und nicht den Exit-Code; Hinweis, dass `chronicle` dort eine
  **zweite** Zeile (Kappung durch `--limit`) drucken kann, mit Verweis auf
  `{ref}`cli-reference``; jedes Kommando meldet den Rückstand seiner eigenen
  Projektion. Dann `previously project`, mit Verweis auf die vier Ausgänge in
  der Reference statt deren Aufzählung hier.
- `## Force a rebuild after a change to the derivation` — `version` im Code
  erhöhen, mit beiden Fundstellen benannt: `ChronicleProjection.version` in
  `src/previously/core/projection/chronicle.py` und
  `SourceStatsProjection.version` in
  `src/previously/core/projection/source_stats.py`, beide bei `1`. Ausgabe
  `chronicle       rebuilt: version 1 -> 2, 12 events, up_to_id 12`.
  Ein Satz dazu, dass eine Versionserhöhung die Zeilen neu baut und Spalten
  und Indizes unberührt lässt, mit Verweis `{ref}`add-a-migration`` für eine
  Strukturänderung.
- `## Force a rebuild without a code change` — `DELETE FROM projection_state
  WHERE name = 'chronicle'` über `psql`, dann `previously project` →
  `chronicle       built: 12 events, up_to_id 12`. Ein `:::{warning}` (das
  einzige Admonition der Seite). Zum Schluss der Satz, dass `source-stats` an
  der Stelle von `chronicle` dasselbe für die Statistik tut, und der Verweis
  „For why a rebuild yields the same rows as the incremental path, see
  {ref}`projections`."

Toctree in `docs/how-to/index.md` nach `add-a-migration` ergänzt.

**Der Warnhinweis ist nach der Messung des Dispatch geschrieben, nicht nach
dem Wortlaut der Beauftragung** („bis zum nächsten `project` ist die Chronik
leer" ist falsch). Was dort steht, in der Reihenfolge: das `DELETE` wirft das
Lesezeichen weg und lässt die Zeilen von `p_chronicle` stehen; bis zum
nächsten `previously project` druckt `previously chronicle` diese alten Zeilen
und meldet das **ganze Log** als Rückstand; `previously project` leert die
Tabelle dann in seiner ersten Transaktion und füllt sie stapelweise, ein
`chronicle`-Lauf während eines langen Neubaus sieht also eine Teilchronik, und
die Rückstandszeile sagt, wie weit er ist. Gegen den Code geprüft:
`worker.catch_up` leert in der Transaktion **vor** der Schleife
(`storage.truncate_projection`, `ProjectionState(name, 0, version, …)`) und
zieht danach stapelweise nach.

**Dass ich `stats` im Warnhinweis nicht mitnenne, ist Absicht.** Der Dispatch
schreibt „`chronicle` und `stats` drucken die alten Zeilen und melden das ganze
Log als Rückstand" — das gilt nur, wenn **beide** Zustandszeilen gelöscht
werden. Das `DELETE` der Beauftragung trifft `name = 'chronicle'`, und
`_cmd_stats` liest `projection_state` für `source-stats`
(`cli.py:296`), ist also unberührt. `docs/reference/cli.md` sagt dasselbe:
„The two commands report the lag of the projection each one reads." Statt der
unzutreffenden Aufzählung steht der Satz „To force the statistics the same
way, use `source-stats` in place of `chronicle`." nach dem Hinweis.

**Zur `psql`-Aufrufzeile, gemessen am 2026-10-04 auf dieser Maschine
(`/usr/bin/psql`):** `PREVIOUSLY_DSN` trägt die SQLAlchemy-Treiberform
`postgresql+psycopg://…` (`docs/reference/configuration.md`, `from_dsn`).
`psql "postgresql+psycopg://previously:previously@localhost:5432/previously"`
scheitert mit `connection to server on socket "/var/run/postgresql/.s.PGSQL.5432"
failed` — `libpq` erkennt das Schema nicht als URI, liest den ganzen Wert als
Datenbanknamen und geht auf den lokalen Socket, **Host und Port werden
ignoriert**. Dieselbe Zeile ohne `+psycopg` geht nach `localhost (::1) port
5432` und meldet `Connection refused`, parst also als URI. Die Seite zeigt
darum die reine `postgresql://`-Form (mit den Zugangsdaten aus dem Tutorial)
und sagt in einem Satz, warum nicht `$PREVIOUSLY_DSN`.

### 2. `docs/explanation/projections.md`

Neuer letzter Abschnitt `## What a chronicle per unit teaches about erasure`,
16 Prosazeilen in vier Absätzen (21 Zeilen mit Überschrift und Leerzeilen):

1. Tilgung ist nicht gebaut, die Form steht: Grabstein, `payload` auf SQL
   `NULL`, Kette überlebt es, weil der Event-Hash den Abdruck der Nutzlast
   trägt. Verweis `{ref}`tombstone-seam``. Was die Form nicht anfasst, ist
   `unit` — eine eigene Tabelle, also zeigt eine Chronik je Einheit den Inhalt
   eines getilgten Events weiter, mit leerer `evidence`-Spalte daneben.
2. §4.6 der Architektur (frozen design record) beschreibt diesen Grabstein und
   **übersieht** die Einheiten; nötig war das nie, weil es noch keinen Leser
   auf Einheitenebene gab. 1b baut den ersten, und damit kommt der Fund: wer
   tilgt, muss die Einheiten mittilgen, oder der Inhalt war nie getilgt — eine
   Vorgabe an das Tilgungs-Event, keine Entscheidung dieser Stufe. Dazu der
   Satz, dass eine Projektion je Event die Frage hinter einer leeren
   Nutzlastspalte versteckt hätte: der Fund kommt aus der **Form** der
   Projektion, nicht aus einer Änderung am Log.
3. Die zweite Folge: `p_source_stats.units` zählt die Einheiten der bereits
   eingefalteten Events, und der Arbeiter sieht unter sein Lesezeichen nie
   wieder. Eine Tilgung, die Einheiten löscht, ließe die Zahl stehen, und kein
   Nachziehen korrigiert sie — hier verdient die wegwerfbare Hälfte der Zusage
   ihr Geld: eine Versionserhöhung holt die Zahl umsonst zurück, weil nur das
   Log sie entscheidet. Eine Zahl, die kein Neubau reproduzieren kann, wäre
   eine zweite Kopie der Wahrheit gewesen.
4. `test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` nagelt
   das heutige Verhalten fest; der Pin ist, was den Fund davor bewahrt, eine
   Notiz zu sein, die jemand beachten mag oder nicht.

Die Einleitung der Seite (Zeile 6–9) **kartiert alle Abschnitte**
(„Three sections follow … Two more follow …"), also wäre sie durch einen
achten Abschnitt falsch geworden. Ein Satz ergänzt: „A last section follows on
what the unit-level chronicle makes visible about an erasure that empties a
payload."

Seite als Ganzes nachgelesen: ein Quadrant (kein „do this", keine Faktentabelle
— die Codeblöcke sind Messprotokolle und Mutationsbefunde, keine Referenz),
ein Satz pro Zeile, Überschriften in Satzschreibung ohne Akronyme, **null**
Admonitions auf der Seite (Grenze zwei).

### 3. `README.md`

- `## State`: „Stage 1a is built and runs: the append-only log with its hash
  chain." → „Stages 1a and 1b are built and run: the append-only log with its
  hash chain, and the projections derived from it." Folgesatz „so that the
  stage is *runnable*" → „so that each stage is *runnable*".
- **What it does**, drei neue Punkte vor der Kommandozeile: Projektionen
  (`project`), ableitbar und wegwerfbar, mit `projection_state` und
  Versionsneubau; die Chronik (`chronicle`), eine Zeile je Einheit mit
  Quellenangabe, in Zeitordnung statt Aufzeichnungsordnung; die
  Quellenstatistik (`stats`) mit Events, Einheiten und frühestem/spätestem
  `occurred_at`.
- „the four commands `append`, `log`, `verify` and `show`" → „the seven
  commands `append`, `log`, `verify`, `show`, `project`, `chronicle` and
  `stats`".
- **What it does not do**: „no projections (header, chronicle as a view —
  stage 1b)" gestrichen, dafür drei Punkte: kein Kopf — ein Kopf ruht auf
  Feststellungen, und die kommen aus dem Gate; keine Zuordnung von Events zu
  Projekten, also ist die Chronik die des ganzen Logs und nicht eines
  Projekts; keine Auftragswarteschlange — der Projektionsarbeiter ist ein
  Kommando. Der Rest (Konnektoren, MCP, Sprachmodell, Suche, Tilgung,
  Benutzerverwaltung, Netzschnittstelle) unverändert.

Der README wird von Vale **nicht** gelesen (`docs/Makefile`:
`QUADRANTS = index.md tutorials how-to reference explanation`), darum bleibt
seine vorhandene Schreibung (`canonicalised`, `Licence`) unangetastet.

### 4. Die beiden mitgetragenen Funde

- `docs/reference/database-schema.md`, Zeile 5 und Diagrammbeschriftung:
  Einleitung nennt jetzt alle sechs Tabellen in zwei Gruppen — drei tragen das
  Log (`event`, `unit`, `source_key`), drei tragen Projektionen, abgeleitet und
  wegwerfbar (`projection_state`, `p_chronicle`, `p_source_stats`), mit
  `{ref}`projections``. `declares them` → `declares all six`. Beschriftung:
  „The three tables of the log, with their foreign keys; the projection tables
  are described below." Das `erDiagram` selbst ist **unverändert**.
- `tests/test_schema.py:351`: `test_the_declared_indexes_exist` →
  `test_the_declared_indexes_exist_in_the_migrated_database` (der Test steht in
  Zeile 256).

`docs/explanation/module-boundaries.md` nicht angefasst.

## Jede Zahl auf den Seiten, und wo sie abgelesen ist

| Zahl / Zeichenfolge | Seite | Quelle im Baum, gelesen |
|---|---|---|
| Stapelgröße 2 | `projections.md` (vorhanden) | `tests/test_projection_worker.py:221` `catch_up(…, batch_size=2)` |
| zehn Events | `projections.md` (vorhanden) | `test_projection_worker.py:217` `range(1, 11)` |
| `up_to_id 4`, höchste `event_id` 4, 8 Zeilen | `projections.md` (vorhanden) | `test_projection_worker.py:228` `assert (state.up_to_id, highest, rows) == (4, 4, 8)` |
| Folgelauf 6 Events, `up_to_id 10` | `projections.md` (vorhanden) | `test_projection_worker.py:231` `== (6, 10)` |
| 25 Beispiele | `projections.md` (vorhanden) | `test_projection_worker.py:369` `max_examples=25` |
| drei Quellen | `projections.md` (vorhanden) | `test_projection_worker.py` `st.sampled_from(["email", "chat", "cli"])` |
| „leaves the other ten green" | `projections.md` (vorhanden) | `grep -c "def test_" tests/test_projection_worker.py` = 12, zwei Versionstests → zehn andere. **Stimmt, nicht neu gemessen, nicht geändert.** |
| „all nine tests in test_projection_derive.py" | `projections.md` (vorhanden) | `grep -c "def test_" tests/test_projection_derive.py` = 9 |
| „two chronicle rows", `evidence` null in beiden | `projections.md` (neu) | `test_projection_worker.py:296` `== [("one", None), ("two", None)]`; `_raw` Vorgabetext `"one\n\ntwo"` (Zeile 52) → zwei Einheiten |
| `version` beide bei `1` | How-to | `core/projection/chronicle.py:69` und `core/projection/source_stats.py:67`, je `version: int = 1` |
| `projection is 12 events behind; …` | How-to | `cli.py:124` `_lag_line`, Wortlaut identisch mit `docs/reference/cli.md:114` |
| `chronicle` + 7 Leerzeichen + `rebuilt: …` / `built: …` | How-to | gemessen: `python -c "print(repr(f'{\"chronicle\":<15} ' + …))"` → `'chronicle       rebuilt: …'`, Zeichen für Zeichen gleich der Seite (`cli.py:234` `f"{outcome.name:<15} {_describe(outcome)}"`) |
| `rebuilt: version 1 -> 2, 12 events, up_to_id 12` / `built: 12 events, up_to_id 12` | How-to | Formate aus `cli.py:102–109` `_describe`; die 12 ist ein frei gewähltes Beispiellog, keine Messung |
| sechs Tabellen, 3 + 3 | `database-schema.md` | Die Seite dokumentiert sechs Abschnitte; `src/previously/storage/schema.py` erklärt sechs `Table`-Objekte |
| 22 Dateien, 0 Fehler (Vale) | Bericht/Commit | `make -C docs vale` |
| 15 Einträge, 11 klein (`.vale.ini`) | unverändert | `wc -l` = 15, `awk 'NF && /^[a-z]/' … \| wc -l` = 11 |

## Vokabular: die Fehlerzahlenfolge

**Es gibt keine Folge — die erste Messung war schon null.**

```
make -C docs vale   (nach How-to, projections.md, database-schema.md)
✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
```

Also **kein Wort** zu `.vale-styles/config/vocabularies/Previously/accept.txt`
hinzugefügt, und damit auch keine Änderung an `.vale.ini`. Die Beauftragung
erwartete Treffer auf `upsert`, `denormalization`, `catch-up` — keines dieser
Wörter steht in dem, was ich geschrieben habe, und was ich geschrieben habe
(`bookmark`, `catch-up` im How-to-Titel nicht, `tombstone`, `unit-level`,
`psql`, `libpq` in Code-Spans) läuft durch. Code-Spans prüft Vale nicht, und
`psql`/`libpq` stehen ausschließlich in Code-Spans.

Beide Zahlen im `.vale.ini`-Kommentar trotzdem nachgezählt, nicht
übernommen:

```
$ awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt | wc -l
11
$ wc -l < .vale-styles/config/vocabularies/Previously/accept.txt
15
```

„Eleven of the fifteen entries are lowercase" stimmt also weiter; der Kommentar
bleibt unangetastet, die „task 6"-Geschichte darin erst recht.

## Die sechs Tore, jedes einzeln

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
Required test coverage of 90.0% reached. Total coverage: 97.32%
232 passed in 22.62s

$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded.          (html, -W --keep-going)
✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
build succeeded.          (linkcheck)
```

`pytest` 232 passed, unverändert gegenüber der Erwartung — meine Änderung in
`tests/test_schema.py` ist ein Docstring-Wort, kein Test. Die vier Codetore
und `pytest` sind **nach** der letzten Dokumentationsänderung noch einmal
gelaufen, weil `test_docs_build.py`, `test_docs_references.py` und
`test_docs_typed_output.py` den Dokumentationsbaum lesen.

## Geänderte Dateien

```
README.md                            | 29 ++++++++++++++------
docs/explanation/projections.md      | 23 +++++++++++++++++
docs/how-to/index.md                 |  1 +
docs/how-to/rebuild-a-projection.md  | 82 ++++++++++++++++++++++ (neu)
docs/reference/database-schema.md    |  8 ++++---
tests/test_schema.py                 |  4 ++--
```

`git status --short` vor dem `git add` zeigte genau diese sechs und nichts
sonst; nichts Fremdes war modifiziert. `.vale.ini` und `accept.txt` sind
**nicht** im Commit, weil sich nichts an ihnen ändern musste. Arbeitsbaum nach
dem Commit sauber.

## Abweichungen von Beauftragung und Dispatch

1. **Titel `# How to rebuild a projection` statt `# Rebuild a projection`.**
   Die drei Geschwisterseiten heißen „How to check the chain in operation",
   „How to check that a restore brought the chain back", „How to add a
   migration" — der Toctree in `docs/how-to/index.md` zeigt diese Titel
   untereinander, und ein vierter ohne „How to" steht als Ausnahme darin, die
   niemand beschlossen hat. Die `plone-doc-style:author`-Regel für den
   How-to-Quadranten („Title states the goal") ist mit beiden Formen erfüllt.
   Label, Dateiname und die drei Abschnittstitel sind wörtlich wie beauftragt.
   Einzeiler, falls der Betreuer den Wortlaut der Beauftragung vorzieht.
2. **Warnhinweis nach der Messung, nicht nach dem Wortlaut** — so vom Dispatch
   angeordnet; zusätzlich ohne `stats`, siehe die Begründung oben.
3. **Ein Satz zu `psql` und `PREVIOUSLY_DSN`**, den weder Beauftragung noch
   Dispatch verlangen. Ohne ihn führt der einzige in der Beauftragung
   vorgesehene Weg zum Zustandszeilen-Löschen in die Irre: `psql
   "$PREVIOUSLY_DSN"` verbindet sich still auf den lokalen Socket. Ein How-to,
   dessen Befehl nicht läuft, ist schlimmer als einer, der eine Zeile länger
   ist.
4. **Zweiter Absatz in der Commit-Nachricht** für den Schema-Reference-Fund.
   Der Dispatch verlangt nur den Satz zum Test-Docstring; eine geänderte Datei
   ohne Grund in der Nachricht wäre aber eine Lücke.
5. **Die Vokabular-Absätze der Commit-Nachricht umgeschrieben**, weil ihr
   Wortlaut („Vocabulary extended one word at a time") nach der Messung falsch
   gewesen wäre. Jetzt: kein Wort nötig, 0 Fehler in 22 Dateien, Kleinschreib-
   zahl nachgezählt und unverändert.
6. **Ein Satz in der Einleitung von `projections.md`** (die Abschnittskarte),
   nicht verlangt, aber sonst lügt die Karte über die Seite.

## Nicht angefasst, aber gesehen

- `docs/index.md`, Zeile 24: die How-to-Karte zählt „restore a backup, add a
  migration, check the chain in operation" auf — jetzt drei von vier Seiten.
  Die Datei steht nicht auf der Dateiliste des Dispatch, also habe ich sie
  nicht angefasst. Die Aufzählung liest sich als Beispiel, nicht als Index;
  wenn sie vollständig sein soll, ist „rebuild a projection" ein Einzeiler.
- `README.md`, Zeile 9–10: „The name is the main view: the header and the
  chronicle of a project" — der Kopf fehlt noch und die Chronik ist die des
  ganzen Logs. Der Satz beschreibt die Zielansicht, nicht den Stand, und
  „What it does not do" sagt jetzt beides ausdrücklich. Darum stehen gelassen.
- `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md` §10 Punkt 2 ist
  die Quelle des neuen Abschnitts; das Einfrieren des Specs ist Task 8.

## Bedenken

1. **„Both stand at `1`" im How-to veraltet bei der ersten echten
   Versionserhöhung.** Es ist heute gemessen richtig und für den Leser
   nützlich, aber es ist eine Zahl in Prosa über Code, der sich genau an dieser
   Stelle ändern soll. Wer eine Version erhöht, muss den Satz mitziehen; kein
   Tor erzwingt das.
2. **Die `psql`-Zeile trägt Zugangsdaten aus dem Tutorial**
   (`previously:previously@localhost:5432`). Das ist der Wegwerf-Container des
   Tutorials, kein Geheimnis — aber es ist eine Form, die zum Kopieren
   einlädt. Eine Alternative wäre, nur das SQL zu zeigen und das Verbinden dem
   Leser zu lassen; dann fehlt dem How-to der ausführbare Befehl.
3. **Der Abschnitt in `projections.md` argumentiert über ein Tilgungs-Event,
   das es nicht gibt.** Er sagt das im ersten Satz („Erasure isn't built"), und
   §4.6 der Architektur tut dasselbe. Trotzdem ist es der einzige Abschnitt der
   Seite, dessen Gegenstand nicht im Baum steht, und er wird mit dem echten
   Tilgungs-Event neu gelesen werden müssen.
4. **Die Seite `projections.md` ist mit diesem Abschnitt 215 Zeilen lang.** Ein
   Quadrant, aber am obersten Ende dessen, was eine Explanation-Seite tragen
   sollte. Der offene Minor zur Länge von `module-boundaries.md` wartet auf die
   Endprüfung; hier könnte derselbe Befund entstehen.

---

# Fixrunde 1 — Bericht

Commit `af5f5de` auf `worktree-stufe-1b-projektionen`, Arbeitsbaum sauber.
Vorgänger `773cf4a`. Drei Dateien, 12 Einfügungen, 20 Löschungen. Alle sechs
Tore grün, `pytest` 232 passed (kein Test berührt), Vale 0 Fehler in 22
Dateien.

## I1 — `docs/index.md:24`

„Solve a specific problem: restore a backup, add a migration, check the chain
in operation." → „… restore a backup, add a migration, **rebuild a
projection**, check the chain in operation." Vierter Eintrag vor dem letzten
eingefügt, damit die Aufzählung der Reihenfolge der Karte nichts Neues
behauptet.

## I2 — „Both stand at `1`." fällt

`docs/how-to/rebuild-a-projection.md:35` lautet jetzt „Read the current value
there." Die beiden Fundstellen stehen unverändert in `:34`. Damit steht auf der
Seite keine Zahl mehr über Code, den die Seite selbst zu ändern anleitet.

## I3 — die drei `text`-Blöcke sind weg, Prosaform wie bei `verify-the-chain.md`

Nach der Auflösung umgesetzt. Kein `text`-Block mehr auf der Seite; die
verbleibenden vier Codeblöcke sind drei `shell` (Befehle) und ein `python`
(`version: int = 2`).

- Rückstand (`:15`): „Each command reports the lag of the projection it read as
  one line on standard error: the line names how many events are missing and
  recommends `previously project`."
- Versionssprung (`:43–44`): „The line for the projection you raised begins with
  `rebuilt:`, names the version it moved from and to, and ends with the number
  of events projected and the new `up_to_id`." / „The line for the projection
  you left alone reports `up to date`."
- `DELETE` (`:62–63`): „With no state row left to compare against, that
  projection's line begins with `built:` instead of `rebuilt:`." / „The line for
  the other projection again reports `up to date`."
- Der Nebenbefund ist damit an **beiden** Stellen geschlossen: zweimal steht
  ausdrücklich, was die jeweils andere Zeile meldet, und `:28` sagt weiter
  „prints one line per projection".
- Kein echter Lauf eingebaut, wie angeordnet.

**Eine Änderung über die Auflösung hinaus:** den Satz „See {ref}`cli-reference`
for its exact wording." habe ich nicht stehen gelassen, sondern in den
vorhandenen Verweis in `:19` gezogen — „see {ref}`cli-reference` for the exact
wording of **both**" (Rückstandszeile und Kappungszeile). Sonst stünde derselbe
Verweis dreimal in einem Abschnitt gestanden (nach `:15`, dann `:19`, dann
`:29`); die Auflösung nennt `:33` (heute `:29`) als den, der den Wortlaut
ohnehin holt.

## I4 — Platzhalterverbindung

`:54`: `psql postgresql://USER:PASSWORD@HOST:PORT/DATABASE \`. Die
Tutorial-Zugangsdaten sind weg. `:59` (der gemessene `libpq`-Satz) steht
wörtlich unverändert. `:60` trägt jetzt die Auflösung der Platzhalter:
„Take the host, port, database and credentials from the value you have set; see
{ref}`configuration-reference` for its form." — der Verweis **ersetzt** die
Zugangsdaten, er ergänzt sie nicht mehr.

## Minor 1 — `:71`

„To force the statistics the same way, use `'source-stats'` in place of
`'chronicle'` in the `DELETE`." Beide Werte in Anführungszeichen **und** im
Code-Span, wie sie im `DELETE` stehen; damit ist die Verwechslung mit dem
Kommando `previously chronicle` ausgeschlossen, und ein `previously
source-stats`, das es nicht gibt, legt der Satz niemandem mehr in den Mund.

## Minor 2 — `projections.md:202–203`

Ein Satz hinter „overlooks the units" („overlooks" bleibt):

> What it does say is the sharper evidence—an erasure takes the proof and not
> the derived facts, and what disappears is the wording—because the wording is
> what `unit.content` holds, and a chronicle per unit goes on printing it.

Gegen `docs/superpowers/specs/2026-10-01-architektur.md:457–459` gelesen: „dass
etwas vereinbart wurde, verschwindet nicht, weil jemand Löschung verlangt — was
verschwindet, ist der Wortlaut", unter „Was eine Tilgung kostet": „Sie nimmt
den **Beleg**, nicht die **abgeleiteten Fakten**."

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
============================= 232 passed in 21.61s =============================

$ make -C docs html
build succeeded.

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 22 files.

$ make -C docs linkcheck
build succeeded.
```

Reihenfolge der Messung: erst die drei Dokumentationstore gezielt, dann alle
sechs einzeln, dann nach dem Commit noch einmal alle sechs (die Zeilen oben
sind der Lauf nach dem Commit).

## Geänderte Dateien

```
docs/explanation/projections.md      |  1 +
docs/how-to/rebuild-a-projection.md  | 22 ++++++----------------
docs/index.md                        |  2 +-
```

`git status --short` vor dem `git add` zeigte genau diese drei. Die Seite ist
von 82 auf 73 Zeilen geschrumpft.

## Widerspruch

Keiner. Zwei Beobachtungen, die kein Widerspruch sind:

1. Der `psql`-Befehl ist jetzt **nicht mehr kopierbar lauffähig** — das ist der
   Preis der Platzhalterform und mit der Auflösung bewusst bezahlt; `:60` sagt,
   woher die vier Werte kommen.
2. Die Prosaform nennt den Wortlaut der Ausgänge (`rebuilt:`, `built:`,
   `up to date`) weiter in Code-Spans. Das sind Zeilenanfänge, keine getippten
   Läufe, und `docs/reference/cli.md` ist die Stelle, die sie vollständig
   führt — dort bleiben sie gegen `_describe` in `cli.py` prüfbar, wie der
   Zitat-Test es für die Reference tut.
