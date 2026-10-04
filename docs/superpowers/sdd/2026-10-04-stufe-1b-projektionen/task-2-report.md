# Aufgabe 2 — Bericht: `projection_state`, `p_chronicle`, `p_source_stats`, Migration `0002_projections`

Status: **DONE_WITH_CONCERNS** (alle sechs Tore grün, Baum clean; die
Bedenken sind Beobachtungen für die Prüfung, keine offenen Arbeiten).

Commit: `refactor: feat: the three projection tables, by migration 0002`
— siehe Commit-Hash in der Rückmeldung. Trailer
`Assisted-By: Claude Sonnet 5 <noreply@anthropic.com>`, nie
`Co-Authored-By:`.

---

## 1. Die abgelesenen Spalten- und Beschränkungsnamen

Gemessen gegen eine frisch migrierte PostgreSQL 17 in einem Testcontainer,
mit dem Skript `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/read_projection_schema.py`
(`PostgresContainer("postgres:17", driver="psycopg")`,
`command.upgrade(config, "head")`, wie in `tests/conftest.py`). Befehl:

```
$ uv run python /tmp/.../scratchpad/read_projection_schema.py
```

**Spalten** (`information_schema.columns`), alle drei Tabellen genau wie in
Spec §3 und wie vom Brief in `schema.py`/der Migration vorgegeben — `bigint`,
`integer`, `text`, `timestamp with time zone`, Nullbarkeit wie deklariert.
Keine Abweichung zum Brief.

**Indizes** (`pg_indexes`):

```
p_chronicle       | p_chronicle_occurred_idx    | ... USING btree (occurred_at, event_id, seq)
p_chronicle       | p_chronicle_pkey            | ... USING btree (event_id, seq)
p_source_stats    | p_source_stats_pkey         | ... USING btree (source)
projection_state  | projection_state_pkey       | ... USING btree (name)
```

**Constraints** (`pg_constraint`):

```
p_chronicle       | p_chronicle_event_id_fkey          | f | FOREIGN KEY (event_id) REFERENCES event(id)
p_chronicle       | p_chronicle_pkey                   | p | PRIMARY KEY (event_id, seq)
p_source_stats    | p_source_stats_last_event_id_fkey  | f | FOREIGN KEY (last_event_id) REFERENCES event(id)
p_source_stats    | p_source_stats_pkey                | p | PRIMARY KEY (source)
projection_state  | projection_state_pkey              | p | PRIMARY KEY (name)
```

Alle sechs Namen stimmen exakt mit denen überein, die der Brief in Schritt 7
vorhersagte (`projection_state_pkey`, `p_chronicle_pkey`,
`p_chronicle_event_id_fkey`, `p_chronicle_occurred_idx`,
`p_source_stats_pkey`, `p_source_stats_last_event_id_fkey`) — nachgeschlagen,
nicht geraten. `database-schema.md` trägt diese sechs Namen und die
Spaltentabellen jetzt als drei neue Abschnitte.

## 2. Abweichungen zwischen Brief und Wirklichkeit

**a) `schema.py`: eine bare Paragraphenreferenz im wörtlich übernommenen
Kommentar.** Der Brief gibt für den Index-Kommentar wörtlich:

```
# The primary key carries chain order; this index carries time order
# (architecture §4.1 wants both). `chronicle` reads in index direction, and the
# triple is unique, so the output is deterministic.
```

So eingefügt, meldet `tests/test_docs_references.py::test_no_bare_paragraph_references_remain`
einen Fund: die Zeile trägt `§4.1` ohne die Markierung „frozen design
record", die dieselbe Datei an drei anderen Stellen (`§10.1`, `§3.4`, `§4.4`)
trägt. Behoben durch Einfügen der Markierung in dieselbe Zeile:
„architecture §4.1, frozen design record, wants both". Keine inhaltliche
Änderung, nur die Konvention aus `design-records.md` nachgezogen, die der
Brief an dieser einen Stelle nicht einhielt.

**b) `schema.py`: die Index-Deklaration aus dem Brief ist zu lang.**
Der Brief gibt den Aufruf einzeilig:

```python
Index("p_chronicle_occurred_idx", p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq)
```

103 Zeichen, `uv run ruff check .` meldet `E501` (Limit 100,
`pyproject.toml`). Umgebrochen auf fünf Zeilen, nach dem Muster, das
`event_prev_hash_idx` im selben Modul schon verwendet. Keine inhaltliche
Änderung.

**c) `tests/test_properties.py` — vom Brief nicht genannt, aber ohne Fix
bricht die Testsuite.** Der Brief listet unter „Files" nur
`tests/conftest.py:34-42`. `tests/test_properties.py` trägt an fünf Stellen
(Zeilen 169, 198, 226, 281, 340 vor der Änderung) ein eigenes, zur
Fixture-TRUNCATE-Zeile paralleles `TRUNCATE source_key, unit, event` — nötig,
weil Hypothesis' `@given` mehrere Beispiele pro Testlauf erzeugt und jedes
Beispiel eine leere Tabelle braucht, während das `db`-Fixture nur einmal pro
Testfunktion truncatet. Mit den zwei neuen Fremdschlüsseln auf `event`
scheiterte das volle `uv run pytest` fünffach:

```
sqlalchemy.exc.NotSupportedError: (psycopg.errors.FeatureNotSupported)
cannot truncate a table referenced in a foreign key constraint
DETAIL:  Table "p_chronicle" references "event".
```

Alle fünf Stellen auf dieselbe Tabellenliste gezogen wie das Fixture:
`TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event`.
Das ist eine notwendige Folge des Schemas, keine Designentscheidung — ohne
den Fix ist Tor 5 (`pytest --cov`) rot.

**d) Zeilenlängen der neuen TRUNCATE-Zeile.** Die verlängerte TRUNCATE-Liste
überschreitet an allen sechs Stellen (`conftest.py` einmal, `test_properties.py`
fünfmal) die 100-Zeichen-Grenze. Jede auf einen `c.execute(\n    text(...)\n)`-Block
umgebrochen; inhaltlich identisch.

**e) `projections.md`: vier Vale-Treffer, keiner durch neue Vokabel behoben.**
Der erste `make -C docs vale`-Lauf meldete 3 Fehler, 3 Warnungen, alle in der
neuen Seite:

```
23:102  error    Punctuation should be inside the quotes.            Microsoft.Quotes
23:143  warning  Use first person (such as 'I') sparingly.           Microsoft.FirstPerson
23:158  error    Did you really mean 'denormalizing'?                Vale.Spelling
26:204  warning  Remove 'silently' …                                 Microsoft.Adverbs
29:82   warning  Remove 'deliberately' …                              Microsoft.Adverbs
33:1    error    Use 'that's' instead of 'That is'.                   Microsoft.Contractions
```

Entsprechend Brief-Punkt 6 („ein neues Wort nur eintragen, wenn Vale es
verlangt") habe ich zuerst geprüft, ob Umformulieren reicht, statt
`denormalizing` in die Vokabelliste zu setzen — reicht: „by pulling together
fields from `event`, `unit`, …" statt „by denormalizing across …". Die
Anführungszeichen-Kommasetzung, das „I" und die beiden Adverbien ebenso durch
Umformulierung behoben, „That is" → „That's". Danach `0 errors, 0 warnings
and 0 suggestions in 21 files` — die vom Brief vorhergesagte Zahl, ohne dass
`.vale-styles/config/vocabularies/Previously/accept.txt` angefasst wurde.

**f) Tutorial-Transkript neu abgetippt, nicht nur die Zahl editiert.** Wie in
Punkt 2 der Aufgabenstellung verlangt: `uv run pytest` frisch gefahren
(Seed `2260138176`, alle 194 grün), das komplette Transkript — Seed,
`collected 194 items`, alle 15 Punktzeilen samt neuer `pytest-randomly`-
Reihenfolge und Prozentspalte, Schlusszeile — ersetzt die alte Fassung, ohne
die `rootdir:`-Zeile. `test_schema.py` trägt jetzt 13 Punkte statt 12.

**g) Zwei Anschlussstellen in `module-boundaries.md` gesetzt**, wie vom
Auftrag (nicht vom Brief) verlangt. Gefunden mit
`grep -n "projection" docs/explanation/module-boundaries.md`: Zeilen 271 und
273. `{ref}`projections`` je einmal angehängt:

```
A second protocol is coming, for the projection store ({ref}`projections`), and …
A projection store empties, inserts and updates, because a projection is derivable and disposable by design ({ref}`projections`).
```

Keine dritte Stelle gefunden, die inhaltlich zu `projections.md` passt; die
dritte Erwähnung von „projection" in diesem Absatz (Zeile 274) beschreibt die
Typgrenze zwischen den beiden Protokollen, nicht das Wegwerf-Versprechen, und
bekam deshalb keinen Verweis.

**h) Kleine Ungenauigkeit im Brief, nicht korrigiert.** Der Docstring-Text
aus Schritt 1 zitiert `test_the_declared_indexes_exist` — der tatsächliche
Name in `tests/test_schema.py` ist
`test_the_declared_indexes_exist_in_the_migrated_database`. Wörtlich aus dem
Brief übernommen (Auftrag: „den vollständigen Code … wörtlich übernimmst"),
weil es eine Prosa-Referenz in einem Docstring ist und kein Importpfad — kein
Gate prüft das. Erwähnt hier, damit es nicht als übersehen gilt.

## 3. Testzahl

**194 passed**, wie erwartet (193 + 1 neuer Test). Keine weitere Abweichung.
`uv run pytest --collect-only -q` bestätigt `194 tests collected`, und
`tests/test_docs_typed_output.py::test_typed_test_counts_match_the_tree`
ist grün.

## 4. Die sechs Tore

| # | Befehl | Ausgabe |
|---|--------|---------|
| 1 | `uv run ruff check .` | `All checks passed!` |
| 2 | `uv run ruff format --check .` | `41 files already formatted` |
| 3 | `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| 4 | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` (vier `KEPT`, keine Klammerzahl — unverändert zu Aufgabe 1, diese Aufgabe rührt die Protokollkante nicht an) |
| 5 | `uv run pytest --cov --cov-report=term-missing` | `194 passed in 16.87s`, `Total coverage: 97.67%` |
| 6 | `make -C docs html && make -C docs vale && make -C docs linkcheck` | `build succeeded.` / `0 errors, 0 warnings and 0 suggestions in 21 files.` / `build succeeded.` |

Jedes Tor einzeln gefahren, keines aus dem Gedächtnis zitiert.

## 5. Bedenken

**1. Zwei Stellen im Brief hätten die Tore ohne Korrektur rot gelassen.**
Punkt 2a und 2b oben (bare Paragraphenreferenz, zu lange `Index`-Zeile) sind
mechanische Defekte im wörtlich vorgegebenen Code, nicht in meiner
Umsetzung. Ich habe sie behoben statt sie wörtlich stehen zu lassen, weil
„wörtlich übernehmen" und „alle sechs Tore grün" im Auftrag beide stehen und
im Konfliktfall die Tore nach `CLAUDE.md` nicht verhandelbar sind. Für
künftige Briefs: ein Probelauf von `ruff check` und `test_docs_references.py`
gegen den vorgeschlagenen Codeblock vor dem Schreiben des Briefs hätte beide
gefunden.

**2. `tests/test_properties.py` fehlt in der Dateiliste des Briefs, trifft
aber real.** Punkt 2c ist die gewichtigste Abweichung: ohne den Fix bricht
`pytest --cov` fünffach, nicht an einer Stelle, die ein Diff gegen die
genannten Dateien je gefunden hätte. Jede künftige Aufgabe, die eine Tabelle
mit Fremdschlüssel auf `event` einführt, sollte `grep -rn "TRUNCATE" tests/`
in den Brief aufnehmen, nicht nur `conftest.py`.

**3. Die zwei Anschlussstellen in `module-boundaries.md` sind eine
Interpretation, kein Zitat.** Der Auftrag sagt „zwei vorbereitete
Anschlussstellen", nennt aber keine Zeilennummern. Ich habe die zwei Sätze
gewählt, die das Wegwerf-Versprechen direkt aussprechen (Zeilen 271, 273) und
den dritten (Zeile 274, Typgrenze zwischen den Protokollen) ausgelassen. Eine
Prüfung sollte das gegenzählen, falls eine andere Zuordnung gemeint war.

**4. Der Vorgriff am Ende von Abschnitt 2 von `projections.md` nennt keine
künftige Überschrift.** Der letzte Satz („That's exactly the property that
turns this aggregation into the test of the promise above, and not merely an
example of it.") kündigt an, ohne auf einen Abschnittstitel zu verweisen, weil
Aufgabe 5 den Abschnitt erst schreibt und ein vorab benannter Titel falsch
sein könnte. Aufgabe 5 sollte beim Anhängen prüfen, ob der Übergang noch
passt, statt den Satz unverändert stehen zu lassen.

**5. Kein neuer Vokabeleintrag, aber eine Umformulierung, die stilistisch
abwägbar ist.** „by pulling together fields from `event`, `unit`, …" ist
blasser als „by denormalizing across …", das den fachlich präziseren Begriff
getroffen hätte. Entschieden für die blassere Formulierung, weil Brief-Punkt
6 ausdrücklich verlangt, eine neue Vokabel nur einzutragen, wenn Vale sie
verlangt, und hier eine Umformulierung ausreichte. Vertretbar, aber keine
erzwungene Entscheidung — eine Prüfung könnte stattdessen `denormalizing` in
die Vokabelliste aufnehmen und den präziseren Satz zurückholen.
