# Aufgabe 5 — Bericht: der Arbeiter `catch_up`

Stand: 2026-10-04 · Status: fertig, mit Bedenken (siehe unten)

Geändert: `src/previously/core/errors.py`, `src/previously/core/projection/worker.py`,
`src/previously/core/projection/__init__.py`, `docs/explanation/projections.md`,
`docs/tutorials/record-your-first-event.md`.
Neu: `tests/test_projection_worker.py`.

---

## 1. Die Messblöcke

### 1.1 Abbruch — Zeilen und `up_to_id` in einer Transaktion

Aus `test_an_abort_leaves_rows_and_up_to_id_in_step`, zehn Events mit je zwei
Einheiten, `batch_size=2`, ein `ProjectionStore`-Wrapper, der beim dritten
`insert_chronicle` eine `RuntimeError` wirft:

```
nach dem Abbruch:  up_to_id 4, max(event_id) in p_chronicle 4, 8 Zeilen
Folgelauf:         6 Events, up_to_id 10
```

Vier statt sechs Events, weil der dritte Stapel die Events 5 und 6 trägt und
seine Transaktion ganz zurückgerollt wird. Die Zahlen sind Zusicherungen im
Test (`assert (state.up_to_id, highest, rows) == (4, 4, 8)` und
`assert (outcome.events, outcome.up_to_id) == (6, 10)`), und der Test ist grün
— sie sind also gemessen, nicht aus dem Brief übernommen. Sie stimmen mit den
Zahlen des Briefs überein.

Der Wrapper hat alle sieben `ProjectionStore`-Methoden und ist kein Mock;
pyright hat die Zuweisung `failing: ProjectionStore[Connection]` ohne Klage
angenommen, also ist er strukturell vollständig.

### 1.2 Versionsbump, mit Kontrolle

Die Kontrolle steht im Test selbst und ist grün: nach `UPDATE p_source_stats
SET events = 999` lässt ein `catch_up` bei unveränderter Version das Gift
stehen (`events` bleibt 999, `rebuilt_from is None`, `events == 0`), während
`SourceStatsProjection(version=2)` die Tabelle leert und neu baut
(`events == 1`, `projection_state.version == 2`, `rebuilt_from == 1`).

Mutation gemessen (Mutation D): in `catch_up` die Bedingung
`if state is None or state.version != projection.version:` auf
`if state is None:` verkürzt — also der Versionsauslöser entfernt:

```
FAILED tests/test_projection_worker.py::test_a_version_bump_rebuilds_and_without_it_nothing_moves
FAILED tests/test_projection_worker.py::test_a_lower_code_version_rebuilds_too
2 failed, 7 passed in 9.47s
```

Zurückgesetzt: 9 passed. Der zweite Fehlschlag ist der `!=`-gegen-`<`-Fall
(Code bei Version 2, Tabelle bei Version 3), mit
`Outcome(..., rebuilt_from=None, ...)` statt `rebuilt_from == 3`.

### 1.3 Die `min`-Mutation gegen den zentralen Test — mit einer Abweichung

Vorgabe: in `source_stats.merge` `min(existing.first_seen,
addition.first_seen)` durch `existing.first_seen` ersetzen, der zentrale Test
muss rot werden. **Er wird rot — aber nicht an der Stelle, die der Brief und
der Spec erwarten.**

```
MUTATION A (nie nachziehen) gegen tests/test_projection_worker.py::test_incremental_equals_rebuilt
> assert stats_row[3] == NOW - timedelta(days=5)
E AssertionError: assert datetime.datetime(2026, 10, 4, 12, 0, tzinfo=zoneinfo.ZoneInfo(key='Etc/UTC'))
E   == (datetime.datetime(2026, 10, 4, 12, 0, tzinfo=datetime.timezone.utc) - datetime.timedelta(days=5))
1 failed in 6.31s
```

Rot an der **festgenagelten** `first_seen`-Zusicherung, nicht an
`assert incremental == rebuilt`. Der Grund ist eine Eigenschaft von `merge`,
die der Spec nicht sieht: `merge` faltet den Stapel **und** mischt die Faltung
mit der gespeicherten Zeile. Eine Mutation darin verschiebt den inkrementellen
Weg und den Neubau gleichermaßen, und die beiden bleiben gleich.

Gegenprobe, Mutation B (Überschreiben, `addition.first_seen`):

```
MUTATION B gegen tests/test_projection_worker.py
9 passed in 9.31s
```

Alle neun grün, auch die festgenagelte Zusicherung — der ältere Nachzügler ist
zufällig das Minimum, genau wie der datierte Korrekturblock in §5.2 sagt. Und
auch die Hypothesis-Eigenschaft bleibt grün, aus demselben Grund wie oben.

Also habe ich eine dritte Mutation gemessen, die wirklich ein **falscher
inkrementeller Schritt** ist: in `SourceStatsProjection.write`
`merge(existing.get(source), row)` zu `merge(None, row)`, also die
gespeicherte Zeile ignorieren.

```
MUTATION C gegen tests/test_projection_derive.py + tests/test_projection_worker.py
FAILED tests/test_projection_worker.py::test_incremental_equals_rebuilt
FAILED tests/test_projection_worker.py::test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild
2 failed, 16 passed in 57.22s
```

Die neun reinen Tests in `test_projection_derive.py` bleiben grün, die
festgenagelte `first_seen`-Zusicherung bleibt grün — nur der Vergleich der
zwei Wege und die Eigenschaft fallen. **Das** ist die Messung, die den
zentralen Test rechtfertigt, und sie steht so im Docstring und auf der Seite.

### 1.4 Die zwei Mutationen aus Aufgabe 4, neu gemessen

Für den Messblock auf der Seite, gegen `tests/test_projection_derive.py`:

```
merge mit first_seen = existing.first_seen  (nie nachziehen)
  FAILED test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older
  1 failed, 8 passed in 0.10s

merge mit first_seen = addition.first_seen  (überschreiben)
  FAILED test_source_stats_aggregates_a_batch_per_source
  FAILED test_merge_adds_counts_and_keeps_the_extremes
  2 failed, 7 passed in 0.11s
```

Das bestätigt die Zuordnung, die der Auftrag nennt: Nie-Nachziehen fällt genau
den Nachzügler-Test, Überschreiben fällt den In-Order-Test **und** den
Stapel-Aggregationstest und lässt den Nachzügler-Test grün. Zurückgesetzt:
9 passed.

### 1.5 Hypothesis-Beispielzahl

```
tests/test_projection_worker.py::test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild:
  - during reuse phase (0.35 seconds): 3 passing, 0 failing, 0 invalid
  - during generate phase (2.29 seconds): 22 passing, 0 failing, 0 invalid
  - Stopped because settings.max_examples=25
```

25 Beispiele, wie vorgesehen.

---

## 2. Die sechs Tore

Jedes einzeln gefahren, alle grün:

| Tor | Ausgabe |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `48 files already formatted` |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` |
| `uv run pytest --cov --cov-report=term-missing` | `220 passed in 20.52s`, `Total coverage: 96.79%` |
| `make -C docs html && make -C docs vale && make -C docs linkcheck` | `build succeeded.` · `0 errors, 0 warnings and 0 suggestions in 21 files.` · `build succeeded.` |

Testzahl **220**, genau 211 + 9 wie erwartet.

Unabgedeckt im neuen Code: `worker.py:116`, der `raise ProjectionGap(…)`. Das
ist beabsichtigt — der Zustand ist nach §4.2 unmöglich, und ein Test, der ihn
herstellt, müsste das Log fälschen. (Daneben weiter unabgedeckt, nicht von
dieser Aufgabe: `source_stats.py:72`, der frühe `return` für einen Stapel
ohne jede Quellenangabe, und `append.py:483`.)

---

## 3. Abweichungen zwischen Brief und Wirklichkeit

1. **Ruling T5-a umgesetzt.** Sieben nackte `§`-Zitate im Briefcode ersetzt
   (nicht sechs — `_force_rebuild` trug ein siebtes): `_force_rebuild`,
   `test_incremental_equals_rebuilt`, `test_a_version_bump_…`,
   `test_an_abort_…`, `test_an_event_without_a_source_…`,
   `test_a_tombstoned_event_…`, `test_property_…`. Alle durch
   `{ref}`projections`` oder Prosa ohne Zeichen. `test_docs_references.py` ist
   grün, also ist keines übrig.

2. **`ProjectionStore` musste unter `TYPE_CHECKING`.** Der Brief hatte es im
   Testmodul auf Modulebene. Ruffs `TC002` hat es gemeldet, weil es nur in
   einer lokalen Variablenannotation vorkommt und kein anderer Name aus
   `previously.contract.store` zur Laufzeit gebraucht wird — genau wie in
   `test_projection_store.py`. `ChronicleRow` und `SourceStatsRow` durften
   oben bleiben, weil `ProjectionState` aus demselben Modul zur Laufzeit
   gebraucht wird.

3. **`st.datetimes` und `DTZ001`.** Der Briefcode baut die Grenzen als
   `datetime(2026, 1, 1)` — naiv, weil `st.datetimes` die Zeitzone selbst
   anhängt und naive Grenzen verlangt. Ruffs `DTZ001` schlägt darauf an. Statt
   einer Suppression sind die Grenzen jetzt aware gebaut und mit
   `.replace(tzinfo=None)` entschärft (`WINDOW_FROM`, `WINDOW_UNTIL`), mit dem
   Grund als Kommentar daneben. **Keine neue Suppression im Baum**; es bleiben
   die fünf aus `CLAUDE.md`.

4. **Ein Kommentar musste umformuliert werden.** Die Begründung zu Punkt 3
   enthielt zunächst den Text `# noqa: DTZ001` wörtlich, und ruff liest den
   auch in einem Prosakommentar als Direktive
   (`warning: Invalid # noqa directive`). Jetzt steht dort „a suppression of
   DTZ001".

5. **Zeilenlängen.** Vier Zeilen des Briefcodes sind über 100 Zeichen;
   `ruff format` hat sie umgebrochen. Inhalt unverändert.

6. **`events: list[RawEvent] = []`** im Eigenschaftstest — pyright strict
   konnte `list[Unknown]` sonst nicht auflösen.

7. **Der Docstring des zentralen Tests sagt etwas anderes als der Brief.**
   Siehe 1.3: die `min`-Mutation fällt die festgenagelte Zusicherung, nicht
   den Vergleich. Der Docstring trägt jetzt alle drei Messungen.

8. **Schritt 5 des Briefs erwartet acht `PASSED`.** Es sind neun, weil die
   Eigenschaft aus Schritt 6 in derselben Datei steht.

9. **Spaltenindizes geprüft**, nicht übernommen: `p_chronicle` hat `source` an
   Position 6 und `p_source_stats` `events` an 1 und `first_seen` an 3 —
   abgelesen in `storage/schema.py`. Stimmt mit dem Brief.

10. **Der vorausblickende Satz der Einleitung** von `projections.md` hat sich
    geändert: er versprach die Abschnitte „once they exist". Jetzt nennt er
    die drei Abschnitte in der Reihenfolge, in der sie kommen — nötig, weil
    der Schlusssatz von „What the two tables are for" auf die Zusage
    vorausweist und zwei Abschnitte dazwischenliegen.

11. **Doku-Formulierungen gegen Vale.** Vier Treffer: `afterwards` →
    `afterward` (`Microsoft.Terms`), `quietly` und `very` gestrichen
    (`Microsoft.Adverbs`), `interleavings` ist `Vale.Spelling` unbekannt →
    „interleaved sequences", danach `randomly` gestrichen und der Satz
    geteilt. **Kein neuer Vokabeleintrag** — umformuliert, wie `.vale.ini` es
    verlangt.

12. **Die getippte Ausgabe** im Tutorial ist ein echter Lauf von
    `uv run pytest` (Seed 2553335422, `220 passed in 20.35s`), ohne die
    `rootdir:`-Zeile. Die Reihenfolge der Dateien und die Prozente sind die
    dieses Laufs, nicht die des alten Blocks.

---

## 4. Bedenken

1. **Der zentrale Test ist schwächer, als Spec §5.2 glaubt — und der Spec
   sollte das erfahren.** Der Vergleich „inkrementell gegen neu gebaut" kann
   eine Mutation in `source_stats.merge` grundsätzlich nicht fangen, weil
   `merge` auf beiden Wegen liegt: es faltet den Stapel und mischt die
   Faltung mit der gespeicherten Zeile. Dasselbe gilt für die
   Hypothesis-Eigenschaft. Was die beiden fangen, ist ein Schritt, der nur auf
   **einem** Weg falsch ist (Mutation C). Die festgenagelte
   `first_seen`-Zusicherung und die reinen Tests in
   `test_projection_derive.py` fangen die Arithmetik. Die Zusage hält damit,
   aber **nur weil drei Tests zusammenarbeiten** — nicht weil der eine
   zentrale Test sie allein trägt. Das steht jetzt auf der Seite und im
   Docstring; §5.2 des Specs verdient einen zweiten datierten
   Korrekturblock, der das nachträgt. Ich habe den Spec nicht angefasst, weil
   er nicht zu dieser Aufgabe gehört.

2. **`ProjectionGap` ist ungetestet.** Eine Zusage ohne Test ist laut
   `CLAUDE.md` ein Kommentar. Hier ist der Zustand aber nach §4.2 unmöglich,
   und ihn herzustellen hieße, das Log zu fälschen (eine Zeile aus `event`
   löschen, obwohl die Spitze höher steht — das bricht auch die Kettenprüfung).
   Ich halte den `raise` für richtig und den fehlenden Test für vertretbar,
   melde ihn aber, weil die Zeile unabgedeckt im Bericht steht.

3. **`batch_size` ist nicht validiert.** Am Code abgelesen, nicht gemessen:
   `catch_up(…, batch_size=0)` liest über `LIMIT 0` leer und läuft damit in
   den `ProjectionGap` — eine irreführende Diagnose für einen Aufruferfehler.
   Ein `batch_size <= 0`-Riegel wäre billig; er stand nicht im Brief, also
   habe ich ihn nicht gebaut.

4. **`source_stats.py:72` bleibt unabgedeckt.** Der frühe `return` für einen
   Stapel ohne jede Quellenangabe wird von keinem Test erreicht; mein
   `test_an_event_without_a_source_…` projiziert beide Events in einem Stapel,
   und da ist `additions` nicht leer. Ein Test, der erst projiziert und dann
   das quellenlose Event anfügt, würde die Zeile treffen. Nicht im Brief, also
   nicht gebaut.

5. **Der Abbruchtest ruht auf „zwei Einheiten je Event".** `_raw` erzeugt
   `"one\n\ntwo"`, und die Zahl 8 in der Zusicherung ist 4 × 2. Der Kommentar
   `# two units per event` steht daneben, aber wer `_raw`s Vorgabetext ändert,
   bricht den Test mit einer Zahl, die nichts erklärt. Lebbar, weil der
   Kommentar da ist.

---

# Fixrunde 1 — Bericht

Stand: 2026-10-04

## 5. Die Messung, die den Lückentest rechtfertigt

### 5.1 Eigene Sonde gegen den alten (ungeschützten) Arbeiter

Eine Wegwerfdatei `tests/test_zz_gap_probe.py`, gegen den Code **vor** den
Guards, danach gelöscht. Zehn Events projiziert, `p_chronicle` ab `event_id 5`
geleert, `up_to_id` auf 4 gesetzt, dann `source_key`/`unit`/`event` für id 5
gelöscht und erneut `catch_up(…, batch_size=2)`:

```
PROBE outcome: events=5 up_to_id=10
PROBE projected event ids: [1, 2, 3, 4, 6, 7, 8, 9, 10]
1 passed in 6.24s
```

Deckungsgleich mit der Messung des Prüfers: **kein** `ProjectionGap`, Event 5
stillschweigend verloren, `up_to_id` auf 10. Der alte `if not events` konnte
dafür nicht feuern.

Zweite Sonde, derselbe alte Code, schlechte Stapelgrößen:

```
PROBE batch_size=0: ProjectionGap: no event above id 0 although the tip is 1
PROBE batch_size=-1: DataError: (psycopg.errors.InvalidRowCountInLimitClause) LIMIT must not be negative
```

Beide Behauptungen aus F2 bestätigt.

### 5.2 Widerspruch: der Lückentest war **nicht** grün gegen den alten Code

Der Auftrag sagt, ich solle berichten, „dass er dort grün war, obwohl id 5
fehlte". Das kann nicht sein und ist es auch nicht: der Test enthält
`with pytest.raises(ProjectionGap, match="above id 4")`, und gegen den alten
Code wird daraus ein Fehlschlag:

```
> with pytest.raises(ProjectionGap, match="above id 4"):
E Failed: DID NOT RAISE ProjectionGap
tests/test_projection_worker.py:317: Failed

FAILED tests/test_projection_worker.py::test_a_gap_in_the_log_raises_instead_of_being_skipped
FAILED tests/test_projection_worker.py::test_batch_size_below_one_is_a_caller_error_not_a_gap
2 failed, 1 passed, 9 deselected in 6.38s
```

Das ist die bessere Messung — rot gegen den alten Code, grün gegen den neuen
ist genau die Form, die `CLAUDE.md` für eine Zusage verlangt. Was „grün war,
obwohl id 5 fehlte" meint, ist das **Verhalten** des alten Arbeiters, und das
ist in 5.1 mit eigener Sonde festgehalten. Der dritte Test
(`test_a_batch_without_any_source_leaves_the_stats_untouched`) war schon gegen
den alten Code grün — er deckt eine Zeile ab, er sichert keine neue Zusage.

**Folge für die Commit-Botschaft:** Die vorgegebene Zeile „a test forges the
gap with plain SQL and was green against the old code" wäre falsch. Sie steht
im Commit als „was red against the old code with `DID NOT RAISE`, while the
worker itself quietly projected 6..10" — gemessen, und mit derselben Aussage.

## 6. F1 bis F8

- **F1** — `catch_up` prüft jetzt Zusammenhang statt Leere: die gelesenen
  Kennungen gegen `range(up_to_id + 1, up_to_id + 1 + len(ids))`, wörtlich wie
  vorgegeben; die alte `ids = …`-Zeile stand nur einmal und ist jetzt vor der
  Prüfung. Nachricht mit `expected[:1]..` und `ids[:3]`, also „expected events
  [5].. above id 4, read [6, 7]; the tip is 10" im Testfall.
- **F2** — `batch_size < 1` wirft `ValueError` als erste Anweisung in
  `catch_up`, vor jeder Transaktion; wörtlich wie vorgegeben.
- **Drei Tests** — `test_a_gap_in_the_log_raises_instead_of_being_skipped`,
  `test_batch_size_below_one_is_a_caller_error_not_a_gap`,
  `test_a_batch_without_any_source_leaves_the_stats_untouched`, hinter
  `test_a_tombstoned_event_…` und vor dem Hypothesis-Teil, damit `SLOW`,
  `WINDOW_*` und `steps` beim Eigenschaftstest zusammenbleiben. `EventRow` und
  `UnitRow` jetzt am Dateikopf (Ruff hat nicht geklagt: beide werden zur
  Laufzeit konstruiert), `ProjectionGap` aus `previously.core.errors`
  importiert.
- **Docstring `ProjectionGap`** — vier Sätze dazu: dass die Prüfung die
  gelesenen Kennungen mit dem Lauf ab `up_to_id + 1` vergleicht, dass die
  erste Fassung nur auf Leere prüfte, warum die für keine Lücke feuern konnte
  (die Spitze liegt immer im Leseergebnis, `read` filtert auf dieselbe
  Schranke), und die Messung mit id 5.
- **Seite, Absatz zu den Lücken** (jetzt Z. 75-78) — neu geschrieben: keine
  Lücke möglich, Prüfung trotzdem, „a check that can't fire is a comment
  rather than a check", die Messung mit id 5 und `up_to_id = 10`, und was die
  Prüfung jetzt vergleicht. `{ref}`silent-losses`` bleibt und ist nach dem Fix
  wieder ehrlich.
- **F3** — neuer Absatz „Three layers, then, and none of them covers
  another": die reinen Tests nageln die Arithmetik, die festgenagelte
  `first_seen`-Zusicherung fängt sie Ende-zu-Ende (die Nie-Nachziehen-Mutation
  macht den zentralen Test **an dieser Zusicherung** rot, nicht am Vergleich),
  und Vergleich samt Eigenschaft fangen den Ein-Weg-Schritt.
- **F4** — der erste Messblock sagt jetzt „fails, alone among the pure tests"
  und nennt in einer zweiten Zeile, dass `test_incremental_equals_rebuilt`
  ebenfalls fällt, an der festgenagelten Zusicherung und nicht am Vergleich.
- **F5** — ein Satz im Absatz zum zentralen Test: ein Neubau wird entweder
  über eine abweichende Version erzwungen oder durch Leeren plus
  `up_to_id = 0` bei unveränderter Version, und der Test nimmt den zweiten
  Weg, damit der Versionsauslöser eine eigene Messung behält.
- **F7** — ein Satz im Abschnitt über die zwei Tabellen: aus `p_source_stats`
  fehlt ein quellenloses Event ganz, weil es keine Quelle gibt, der man es
  zurechnen könnte, und die Chronik ist der Ort, an dem es sichtbar bleibt.
- **F8** — „twenty lines" gestrichen. Selbst nachgemessen: 36 Zeilen, 27 ohne
  Leerzeilen, 21 ohne Docstring. Jetzt „a wrapper of a few dozen lines and no
  mock".
- **F6** — unverändert gelassen, wie angewiesen.

### Zwei Stellen, die der Auftrag nicht nennt und die sonst falsch geworden
wären

1. **Der vorausblickende Satz der Einleitung** sagte „why it never has to
   worry about a gap in the log". Nach F1 prüft der Arbeiter sehr wohl; der
   Satz heißt jetzt „why a gap in the log can't arise and is checked for all
   the same".
2. **Die gemessene Zahl am Ende der Seite** sagte „leaves the other seven
   green" für die Mutation „Versionsauslöser entfernt". Mit zwölf Tests neu
   gemessen: `2 failed, 10 passed in 8.71s`, also „leaves the other ten
   green".

Dazu eine Sprachkorrektur: „onwards" ist britisch und `Vale.Spelling` schlug
an (`1 error`). Auf der Seite **und** im `ProjectionGap`-Docstring steht jetzt
„the run that has to start at `up_to_id + 1`".

## 7. Die zwölf Tests und die sechs Tore

```
uv run pytest tests/test_projection_worker.py -v -p no:randomly
12 passed in 9.19s
```

Alle zwölf namentlich grün, darunter die drei neuen.

| Tor | Ausgabe |
| --- | --- |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `48 files already formatted` |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` |
| `uv run pytest --cov --cov-report=term-missing` | `223 passed in 20.68s`, `Total coverage: 97.10%` |
| `make -C docs html && make -C docs vale && make -C docs linkcheck` | `build succeeded.` · `0 errors, 0 warnings and 0 suggestions in 21 files.` · `build succeeded.` |

Testzahl **223** (220 + 3), wie erwartet. Tutorial neu abgetippt aus einem
echten Lauf (Seed 316378120, `223 passed in 20.67s`), ohne `rootdir:`.

**`worker.py` steht jetzt auf 100 %** — der `raise ProjectionGap` und der
`batch_size`-Riegel sind beide abgedeckt, und damit ist Bedenken 2 aus dem
ersten Bericht erledigt. `source_stats.py` ebenfalls auf 100 %, womit Bedenken
4 erledigt ist. Unabgedeckt bleibt nur noch `append.py:483` (nicht aus dieser
Aufgabe) und `contract/store.py`, das zur Laufzeit niemand importiert und das
seinen eigenen Docstring dazu trägt.

## 8. Wo ich widerspreche

1. **„Der Lückentest war grün gegen den alten Code"** — nein, rot mit
   `DID NOT RAISE`. Siehe 5.2. Die gemeinte Messung ist das Verhalten des
   Arbeiters, und die habe ich mit eigener Sonde gemacht. Eine Zeile der
   vorgegebenen Commit-Botschaft musste deshalb umgeschrieben werden.
2. **Bedenken 3 aus dem ersten Bericht war mit F2 gemeint und ist erledigt**,
   aber der Riegel wirft `ValueError` und nicht `PreviouslyError` — das ist
   so angewiesen und ich halte es für richtig, weise aber darauf hin, dass
   `catch_up` damit die einzige Stelle in `core` ist, deren Fehler nicht unter
   `PreviouslyError` hängt. Wenn Aufgabe 6 `--batch-size` doch an der
   Kommandozeile anbietet, muss die Entscheidung neu fallen.
