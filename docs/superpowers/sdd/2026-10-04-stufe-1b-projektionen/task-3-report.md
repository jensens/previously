# Aufgabe 3 — Bericht: `ProjectionStore[Conn]` und seine PostgreSQL-Implementierung

Status: **DONE_WITH_CONCERNS** (alle sechs Tore grün, Baum clean; die
Bedenken sind Beobachtungen für die Prüfung, keine offenen Arbeiten).

Commit: `44bdc66a7f2f3229caae4881ee3430e71cc9391b` — „feat: ProjectionStore[Conn],
and PostgresStorage implements it". Trailer
`Assisted-By: Claude Sonnet 5 <noreply@anthropic.com>`, nie `Co-Authored-By:`.

---

## 1. Abweichungen zwischen Brief und Wirklichkeit

**a) `from datetime import datetime` in `contract/store.py` — wie vom Brief
verlangt, aber unbenutzt.** Schritt 2 des Briefs sagt wörtlich: „Importe
ergänzen (`from datetime import datetime`, `ChronicleRow`, `ProjectionState`,
`SourceStatsRow`)". Keine der sieben Protokollmethoden in `ProjectionStore`
nimmt oder liefert einen bloßen `datetime`-Wert — `ProjectionState.built_at`
ist ein Feld in `contract/rows.py`, nicht in einer Signatur von `store.py`.
Mit dem Import gesetzt, meldete `uv run ruff check src/previously/contract/store.py`:

```
F401 `datetime.datetime` imported but unused
```

Entfernt. Die drei anderen Importe (`ChronicleRow`, `ProjectionState`,
`SourceStatsRow`) sind echt benutzt (in den Signaturen von
`insert_chronicle`, `projection_state`/`set_projection_state`,
`source_stats`/`upsert_source_stats`) und blieben im `TYPE_CHECKING`-Block.

**b) `_PROJECTION_TABLES` ohne `ClassVar`-Annotation verletzt `RUF012`.**
Der Brief gibt die Zeile als

```python
_PROJECTION_TABLES = {"chronicle": p_chronicle, "source-stats": p_source_stats}
```

— ein `dict`-Literal als Klassenattribut ohne Annotation. `ruff` (Regel-Set
„RUF" ist in `[tool.ruff.lint] select` aktiv) meldet dafür `RUF012` („Mutable
default value for class attribute"). Behoben durch Annotation mit
`typing.ClassVar[dict[str, Table]]` (`Table` aus `sqlalchemy`, importiert
unter `TYPE_CHECKING`, `ClassVar` echt importiert, da zur Laufzeit an der
Klasse ausgewertet). Keine inhaltliche Änderung — dieselben zwei Einträge,
derselbe Zugriff per `self._PROJECTION_TABLES[name]`. Keine neue
Lint-Suppression: das ist eine Typkorrektur, kein `# noqa`.

**c) Der vorgegebene Testcode aus Schritt 3/6 verletzt drei Regeln, unverändert
übernommen.** Wörtlich eingefügt (wie beauftragt: „den du wörtlich
übernimmst"), meldete `uv run ruff check tests/test_projection_store.py`:

- `E501` auf der Signaturzeile von
  `test_read_chronicle_orders_by_time_then_chain_and_filters_a_half_open_window(db: Engine) -> None:`
  — 101 Zeichen gegen das Limit 100 (`pyproject.toml`, `line-length = 100`).
  Behoben durch Umbruch auf drei Zeilen (`db: Engine,` auf eigener Zeile),
  keine inhaltliche Änderung, Name unverändert.
- `TC001` zweimal auf `from previously.contract.store import LogStore` und
  `...ProjectionStore` innerhalb von `test_postgres_storage_satisfies_both_protocols`
  — beide Namen stehen nur in lokalen Variablenannotationen
  (`log: LogStore[Connection] = storage`), die zur Laufzeit nie ausgewertet
  werden (gemessen: `x: Undefined = 5` in einer Funktion wirft keinen
  `NameError`). `ruff --unsafe-fixes --diff` schlägt vor, beide Importe in
  einen modulweiten `if TYPE_CHECKING:`-Block zu heben, genau das Muster, das
  Aufgabe 1 in `contract/store.py` selbst etabliert hat. Übernommen. `Connection`
  und `create_engine` aus `sqlalchemy` blieben als echte Importe in der
  Funktion (letzterer wird aufgerufen, ersterer wird von `ruff` aus Gründen,
  die ich nicht vollständig nachvollzogen habe, hier nicht als
  typing-only erkannt — isoliert getestet verhält sich derselbe Import anders
  und wird dort als `TC001` gemeldet; im Kontext der echten Testdatei nicht.
  Keine Suppression nötig, da `ruff check` nach den beiden Fixes grün ist).

Alle drei Fixes sind mechanisch (Umbruch, Verschiebung eines Imports,
Typannotation) und ändern an keiner Stelle Testverhalten oder Testnamen.

## 2. Was `pyright` zu den `on_conflict_do_update`-Aufrufen und den
`Row`-Attributen gesagt hat

**Nichts** — `uv run pyright` meldete nach der vollständigen Implementierung
auf Anhieb `0 errors, 0 warnings, 0 informations`, ohne dass an
`statement.on_conflict_do_update(...)`, `statement.excluded.*` oder an einem
`row.<spalte>`-Zugriff auf ein SQLAlchemy-`Row`-Objekt (etwa `row.event_id`,
`row.built_at`, `row.source`) ein Fehler auftrat. Das deckt sich mit dem
Muster, das schon `insert_event`, `tip`, `units` etc. im selben Modul zeigen:
SQLAlchemy Core typisiert `Row`-Attributzugriff über `__getattr__`
hinreichend permissiv, dass `pyright strict` keinen Fehler auslöst, und
`pg_insert(...).on_conflict_do_update(...)` ist in den installierten
SQLAlchemy-Stubs so typisiert, dass `index_elements`, `set_` und
`.excluded.<spalte>` ohne `cast` durchgehen. Kein `getattr`-Workaround wie in
`_constraint_name` war nötig, weil hier kein fremder (psycopg-)Typ im Spiel
ist, nur SQLAlchemys eigene, von pyright verstandene Typen. Auch die neue
Protokoll-Erfüllung (`log: LogStore[Connection] = storage`,
`projections: ProjectionStore[Connection] = storage` in
`test_postgres_storage_satisfies_both_protocols`) ging ohne Fehler durch —
`PostgresStorage` erfüllt beide Protokolle strukturell, ohne dass irgendeine
Methode fehlte oder eine Signatur abwich.

## 3. Testzahl

**202 passed**, wie erwartet (194 + 8). `uv run pytest --collect-only -q`
bestätigt `202 tests collected`. Die acht neuen Tests: die sieben
`@pytest.mark.db`-Tests aus Schritt 3 und `test_postgres_storage_satisfies_both_protocols`
aus Schritt 6 (kein `@pytest.mark.db`, braucht keine Datenbank, nur
`create_engine` zum Parsen). `tests/test_docs_typed_output.py` ist grün, das
Tutorial `docs/tutorials/record-your-first-event.md` trägt ein frisch
abgetipptes Transkript (Seed `3130907343`, `collected 202 items`, 16 Punktzeilen
inklusive `tests/test_projection_store.py ........`, Schlusszeile
`202 passed in 18.69s`), ohne die `rootdir:`-Zeile.

## 4. Die sechs Tore

| # | Befehl | Ausgabe |
|---|--------|---------|
| 1 | `uv run ruff check .` | `All checks passed!` |
| 2 | `uv run ruff format --check .` | `42 files already formatted` |
| 3 | `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| 4 | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` (vier `KEPT`, unverändert zu Aufgabe 1/2 — diese Aufgabe fügt keine neue Importkante ein, die Projektionsmethoden laufen über dieselbe `storage`-Schicht) |
| 5 | `uv run pytest --cov --cov-report=term-missing` | `202 passed in 24.00s`, `storage/postgres.py` 100 % (134/134 Stmts), `contract/store.py` weiterhin 0 % (erwartet, Protokollkörper sind `...`), `Total coverage: 96.55%` |
| 6 | `make -C docs html && make -C docs vale && make -C docs linkcheck` | `build succeeded.` / `✔ 0 errors, 0 warnings and 0 suggestions in 21 files.` / `build succeeded.` |

Jedes Tor einzeln gefahren, keines aus dem Gedächtnis zitiert.

## 5. `docs/explanation/module-boundaries.md`

Überschrift Zeile 216 von „## The protocol that made the exemptions
unnecessary" auf „## The protocols that made the exemptions unnecessary"
(Plural). Der Futur-Absatz (Zeile 271) von

> A second protocol is coming, for the projection store ({ref}`projections`), …

auf Präsens:

> A second protocol exists now, `ProjectionStore[Conn]`, for the projection
> store ({ref}`projections`), …

Die zweite Fundstelle aus dem `grep` (Zeile 256: „…worth knowing when a second
protocol follows") **nicht** geändert — sie behauptet nicht, dass das zweite
Protokoll noch ausstehe, sondern begründet allgemein, warum die
`contract/rows.py`-Verschiebung aus Aufgabe 1 wichtig war „wenn ein zweites
Protokoll folgt"; das bleibt als Aussage wahr, unabhängig davon, ob es inzwischen
existiert. Der Auftrag verlangte ausdrücklich „Ändere nur das; der Rest der
Seite bleibt", mit „das" im Singular auf Überschrift + den einen
Futur-Absatz bezogen.

## 6. Bedenken

**1. Die zweite Fundstelle aus `grep` (Zeile 256) wurde stehen gelassen —
Interpretationsspielraum.** Siehe Abschnitt 5. Ich lese „der Absatz" im
Auftrag als den einen Satz in Futur (Zeile 271), nicht als jede der drei
`grep`-Trefferzeilen. Eine Prüfung könnte das anders lesen und auch Zeile 256
ins Präsens ziehen wollen — inhaltlich wäre das vertretbar, aber dann hätte
der Auftrag „Ändere nur das" wohl nicht im Singular stehen sollen.

**2. Der neue Docstring von `ProjectionStore` verweist auf
`core.projection.source_stats`, das es noch nicht gibt.** Wörtlich aus dem
Brief übernommen (Schritt 2), weil er explizit zum wörtlichen Protokollcode
gehört und keine Aussage über den aktuellen Baum trifft, sondern eine über
den Zielzustand nach Aufgabe 4 — die Instruktion des Auftrags, „jede Zahl, die
du schreibst, misst du", bezieht sich auf Zahlen und Messungen, nicht auf
Vorwärtsreferenzen auf künftige Module in einem wörtlich zu übernehmenden
Docstring. Kein Gate prüft das (kein Import, keine `{ref}`-Prüfung auf
Python-Modulpfade), aber Aufgabe 4 sollte den Pfad verifizieren, sobald
`core/projection.py` existiert.

**3. `_PROJECTION_TABLES` als `ClassVar[dict[str, Table]]` statt der
brief-eigenen unannotierten Zeile — eine Typkorrektur, keine
Verhaltensänderung, aber eine Abweichung vom wörtlichen Code in Schritt 5.**
Aufgeführt in Abschnitt 1b. Die Werte, Schlüssel und der Zugriff sind
identisch; nur die Annotation ist neu. Ohne sie wäre Tor 1 (`ruff check`) rot
gewesen (`RUF012`), und eine Suppression war nach Auftrag ausgeschlossen
(„Keine neue Lint-Suppression. Brauchst du eine, melde es als Bedenken statt
sie zu setzen") — hier war aber keine Suppression nötig, die Typannotation
war der echte Fix, deshalb kein Bedenken im Sinne dieser Klausel, nur eine
dokumentierte Abweichung vom wörtlichen Codeblock.

**4. Warum `ruff` den `Connection`-Import in der echten Testdatei nicht als
`TC001` meldet, isoliert aber doch — nicht vollständig geklärt.** Siehe
Abschnitt 1c. Verhaltensrelevant ist das nicht (beide Formen sind
lauffähig und typsicher), aber falls eine künftige Ruff-Version das anders
entscheidet, würde Tor 1 an dieser Stelle neu rot werden können.
