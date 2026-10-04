## Task 1: Das Protokoll `LogStore[Conn]` — und zwei Ausnahmen fallen ersatzlos

**Files:**
- Create: `src/previously/contract/rows.py`, `src/previously/contract/store.py`
- Delete: `src/previously/storage/rows.py`
- Modify: `src/previously/core/append.py:48-60,324-325`, `src/previously/core/verify.py:29-40,178`, `src/previously/storage/postgres.py:14-24`, `.importlinter`, `tests/test_contracts.py`, `tests/test_storage.py`, `tests/test_rows.py`, `tests/test_hashing.py`, `CLAUDE.md`, `docs/explanation/module-boundaries.md`

**Interfaces:**
- Produces: `previously.contract.rows.{Tip, EventRow, UnitRow}` (unverändert im Inhalt, neuer Ort); `previously.contract.store.LogStore[Conn]` mit genau acht Methoden: `begin() -> AbstractContextManager[Conn]`, `tip(conn) -> Tip | None`, `lookup(conn, source, external_id) -> int | None`, `insert_event(conn, row, units, key) -> None`, `read(conn, from_id, limit) -> Iterator[EventRow]`, `units_by_event(conn, event_ids) -> dict[int, list[UnitRow]]`, `count_events(conn) -> int`, `source_keys(conn, event_ids) -> dict[int, tuple[str, str]]`. `append` und `verify` sind generisch: `def append[Conn](storage: LogStore[Conn], …)`, `def verify[Conn](storage: LogStore[Conn], *, batch: int = 1000)`.

- [ ] **Schritt 1: Messen, was fallen wird**

Run: `uv run lint-imports`
Erwartet: zweimal `KEPT (2 ignored imports)`. Diese Ausgabe kommt in den Bericht — sie ist die Vorher-Messung für die negative Zusage in Spec §9 Zeile 1.

Run: `grep -rln "previously.storage.rows" src tests migrations`
Erwartet: sechs Dateien (`core/verify.py`, `storage/postgres.py`, `core/append.py`, `tests/test_storage.py`, `tests/test_rows.py`, `tests/test_hashing.py`). Zähl sie, die Liste unten ist von 2026-10-04.

- [ ] **Schritt 2: Die Zeilentypen nach `contract` verschieben**

```bash
git mv src/previously/storage/rows.py src/previously/contract/rows.py
```

Dann in `src/previously/contract/rows.py` den Modul-Docstring anpassen — die Begründung bleibt, der Ort ändert sich:

```python
"""Rows, not domain objects — the field contract between `core` and `storage`.

`storage` does not know the domain ({ref}`module-boundaries`): `kind` is
text, `payload` is uninterpreted JSON. That is why the type is called
`EventRow` and not `Event` — `core` interprets, `storage` transports.

These types live in `contract` and not in `storage` because the store
protocols in `contract.store` name them, and `contract` is the bottom layer:
it may import nothing above it. Measured on 2026-10-04 against
`.importlinter` — a `contract -> storage` import breaks the `layers` contract.
"""
```

In allen sechs Dateien aus Schritt 1: `from previously.storage.rows import X` → `from previously.contract.rows import X`. `ruff check --fix` sortiert die Importe danach (isort-Stil: `force-single-line`, `no-sections`).

- [ ] **Schritt 3: Das Protokoll schreiben**

`src/previously/contract/store.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The store protocols: what `core` may ask of a store, and nothing more.

`LogStore` is what `append` and `verify` call — eight methods, read off
`storage/postgres.py` on 2026-10-04 with
`grep -o 'storage\\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py`,
not copied from the method list of the implementation. Typing `core` against
this protocol instead of against `PostgresStorage` removes the edge
`core -> storage.postgres`, and with it the two named exemptions in
`.importlinter` and the test that guarded them ({ref}`module-boundaries`).

`Conn` is the connection type. Only `storage` knows what it is; `core` passes
it back to the store it came from and never looks inside.
"""

from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import AbstractContextManager
from previously.contract.rows import EventRow
from previously.contract.rows import Tip
from previously.contract.rows import UnitRow
from typing import Protocol


class LogStore[Conn](Protocol):
    """The append-only log: write once, read in chain order, never change."""

    def begin(self) -> AbstractContextManager[Conn]: ...
    def tip(self, conn: Conn) -> Tip | None: ...
    def lookup(self, conn: Conn, source: str, external_id: str) -> int | None: ...
    def insert_event(
        self,
        conn: Conn,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
    ) -> None: ...
    def read(self, conn: Conn, from_id: int, limit: int) -> Iterator[EventRow]: ...
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
```

`ProjectionStore` kommt in Aufgabe 3 in dieselbe Datei — nicht jetzt, es gibt noch keine Tabellen dafür.

- [ ] **Schritt 4: `append` und `verify` gegen das Protokoll typen**

`src/previously/core/append.py`, der `TYPE_CHECKING`-Block (heute Zeilen 52–57):

```python
if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.store import LogStore
    from previously.contract.types import RawEvent
    from previously.contract.types import RawUnit
```

und die Signatur (heute Zeile 324):

```python
def append[Conn](
    storage: LogStore[Conn],
```

Der Rest der Signatur bleibt. `src/previously/core/verify.py`, `TYPE_CHECKING`-Block (heute Zeilen 35–39) analog — `from previously.contract.store import LogStore` statt `from previously.storage.postgres import PostgresStorage`, die beiden `rows`-Importe auf `contract.rows` —, und Zeile 178:

```python
def verify[Conn](storage: LogStore[Conn], *, batch: int = 1000) -> list[Finding]:
```

Innerhalb beider Funktionen ändert sich **nichts**: `with storage.begin() as conn:` liefert `Conn`, und jeder Aufruf gibt es zurück.

Run: `uv run pyright`
Erwartet: `0 errors`. Fällt hier ein Fehler, dann stimmt eine Signatur im Protokoll nicht mit `postgres.py` überein — **das Protokoll anpassen**, nicht `postgres.py`, denn das Protokoll wurde abgelesen.

- [ ] **Schritt 5: Messen, dass das Protokoll bricht, wenn der Store es verletzt**

Nicht committen — eine Messung. In `src/previously/storage/postgres.py` die Methode `count_events` vorübergehend in `count_rows` umbenennen.

Run: `uv run pyright`
Erwartet: Fehler in `core/verify.py` an der Stelle, wo `verify(_storage())` beziehungsweise `storage.count_events(conn)` steht — pyright meldet, dass `PostgresStorage` nicht `LogStore[Connection]` erfüllt. Die erste Fehlerzeile kommt in den Bericht.

Umbenennung zurücknehmen. Run: `uv run pyright` → `0 errors`.

- [ ] **Schritt 6: Die Ausnahmen aus `.importlinter` nehmen**

In beiden Verträgen (`core-is-clean`, `only-storage-knows-sql`) die zwei Zeilen

```
ignore_imports =
    previously.core.append -> previously.storage.postgres
    previously.core.verify -> previously.storage.postgres
```

**löschen** (den ganzen `ignore_imports`-Block). Die Kommentarblöcke zu Ruling T7-a und T8-c auf das reduzieren, was wahr bleibt:

```
# Until 2026-10-04 this contract carried two named exemptions,
# `core.append -> storage.postgres` and `core.verify -> storage.postgres`,
# because both modules typed their `storage` parameter as the concrete
# `PostgresStorage` under `TYPE_CHECKING` (rulings T7-a and T8-c of stage 1a,
# in docs/superpowers/sdd/). They were enumerated by name and not matched by
# a wildcard, so that a third module following the same pattern would break
# this contract until somebody granted it deliberately — measured with a
# throwaway module, a wildcard let the new edge through silently.
#
# Stage 1b typed `core` against `contract.store.LogStore[Conn]` instead, and
# the edge is gone. There is nothing to exempt. Should an exemption ever come
# back here, it is a named edge, never a pattern; {ref}`module-boundaries`
# carries the measurement that says why.
```

Run: `uv run lint-imports`
Erwartet:

```
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT
Only storage imports sqlalchemy KEPT
No vendor SDK in stage 1a KEPT

Contracts: 4 kept, 0 broken.
```

**Kein `(N ignored imports)` mehr.** Diese Ausgabe wörtlich in den Bericht und in Schritt 9.

- [ ] **Schritt 7: Den Riegel löschen, der nichts mehr bewacht**

In `tests/test_contracts.py` löschen: `test_the_exempted_core_modules_load_no_sql_at_runtime` (ganze Funktion samt Docstring), die Konstanten `_EXEMPTED_MODULES`, `_FORBIDDEN_AT_RUNTIME`, `_RUNTIME_PROBE`, und `import sys`. Der Modul-Docstring sagt „The probe module that the second test writes" — stimmt weiter (zwei Tests bleiben). Der Kommentar über `_EXEMPTED_MODULES` („The two modules that `.importlinter` grants a named exemption") geht mit.

Damit verschwindet `# noqa: S603` aus dem Baum. In `CLAUDE.md`, Abschnitt *Lint suppressions*: den Halbsatz „`S603` on starting a fresh interpreter in the same place — our own interpreter, our own script, no input —" streichen und „That is six suppressions in the whole tree" auf **five** setzen. Messen, nicht glauben:

Run: `grep -rn "noqa:" --include="*.py" . | grep -v .venv | wc -l`
Erwartet: `5`.

Run: `uv run pytest tests/test_contracts.py -v`
Erwartet: zwei Tests, beide `PASSED`. `test_a_deliberately_wrong_import_breaks_the_named_contracts` ist jetzt die **einzige** Gegenprobe und bleibt — sie misst, dass ein `import sqlalchemy` in `core` die zwei Verträge namentlich bricht.

- [ ] **Schritt 8: Die Gegenprobe zu Spec §9 Zeile 2 fahren**

Nicht committen. In `src/previously/core/verify.py` oberhalb des `TYPE_CHECKING`-Blocks eine Zeile `from previously.storage.postgres import PostgresStorage  # probe` einfügen.

Run: `uv run lint-imports`
Erwartet: `core knows no foreign system and no model BROKEN` und `Only storage imports sqlalchemy BROKEN`, darunter `previously.core.verify -> previously.storage.postgres`. Beide Zeilen in den Bericht.

Zeile entfernen. Run: `uv run lint-imports` → `4 kept, 0 broken`.

- [ ] **Schritt 9: `module-boundaries.md` nachziehen — die Seite beschreibt genau diese Änderung**

Die Seite hat heute fünf Abschnitte (Zeilen 15, 44, 84, 125, 177). Nach dieser Aufgabe stimmen vier davon nicht mehr. Jeder Messblock wird **neu gefahren und eingesetzt**, nicht umgeschrieben.

1. **Diagramm** (Zeile 20ff): die zwei gestrichelten Kanten `core.append -.exempted.-> storage.postgres` und `core.verify -.-> storage.postgres` **entfernen**. Neue Kanten: `core --> contract` (über `contract.store` und `contract.rows`) und `storage --> contract` (über `contract.rows`). Caption anpassen: keine „exempted edges" mehr.
2. **„The edges, and the two that are exempted"** → Überschrift wird `## The edges`. Zeile 37 „five of the six edges the order permits exist; only `storage → contract` does not" wird falsch: **alle sechs** existieren jetzt, weil `storage.postgres` `contract.rows` importiert. Nachzählen wie im Hauptbuch der Doku-Ausführung (`grep` je Modulpaar) und die Zahl mit dem Befehl hinschreiben. Die Absätze über die Ausnahmen (Zeile 41ff) werden Vergangenheit: *bis 1b* reichte `core` via `storage.postgres` transitiv an SQLAlchemy.
3. **„Four contracts, and the names are the output"**: den Block mit `KEPT (2 ignored imports)` durch die Ausgabe aus Schritt 6 ersetzen. Der Satz über `2 ignored imports` als zählbare Kosten wird zu: die Zahl stand dort, bis sie bezahlt war.
4. **„Why the two exemptions are enumerated and not matched"**: bleibt als **Begründung in der Vergangenheit** — die Wegwerfmodul-Messung (`3 ignored imports` gegen `BROKEN`) ist die Lehre, warum eine künftige Ausnahme namentlich sein muss. Einleitungssatz: dass es die Ausnahmen bis 2026-10-04 gab und warum sie so geschrieben waren.
5. **„The bolt in the test run"**: **ersetzen** durch einen kurzen Abschnitt `## The bolt that is gone`: was er bewachte, warum er nötig war (die Ausnahme hing an der Kante, nicht an `TYPE_CHECKING`), und dass er mit der Kante ersatzlos fiel — `tests/test_contracts.py` hat seit 1b zwei Tests. Der `TC001`-Messblock bleibt als Begründung, warum ruff nicht gereicht hätte.
6. **„The protocol that would make all of this unnecessary"** → `## The protocols that made the exemptions unnecessary`. Präsens. **Zwei** Protokolle, und warum zwei (Spec §1.1, letzter Punkt: ein Protokoll für beides verwischte „carries no truth of its own"). Dass die Zeilentypen mitwandern mussten, mit der Messung aus Korrektur 1 oben (`contract → storage` wäre `BROKEN`). Der ehrliche Schlusssatz der alten Fassung („The exemptions aren't a compromise anybody is proud of") wird: sie waren es nicht, und darum stand die Zahl im Torprotokoll, bis sie bezahlt war.

Dazu ein `{ref}`projections`` **nicht** setzen — die Seite gibt es erst ab Aufgabe 2.

Run: `make -C docs html && make -C docs vale && make -C docs linkcheck`
Erwartet: `build succeeded`, `0 errors … in 20 files`, `build succeeded`. Schlägt Vale an `Vale.Terms` an, steht ein kleingeschriebener Vokabeleintrag am Satzanfang — umformulieren, nicht die Großform eintragen (`.vale.ini` erklärt, warum).

- [ ] **Schritt 10: Alle sechs Tore**

Run: der Block aus den Global Constraints, jedes Tor einzeln.
Erwartet: alle grün. `pytest`: **193 passed** (194 minus der gelöschte Riegel). Weicht die Zahl ab, zähl nach, was fehlt oder dazukam.

- [ ] **Schritt 11: Commit**

```bash
git add -A
git commit -F - <<'MSG'
refactor: type core against LogStore[Conn], and two exemptions fall

`core.append` and `core.verify` take `LogStore[Conn]` from
`contract.store` instead of the concrete `PostgresStorage`. The edge
`core -> storage.postgres` no longer exists, so the two named exemptions
in `.importlinter` are deleted from both contracts, and
`test_the_exempted_core_modules_load_no_sql_at_runtime` goes with them —
it guarded an edge that is gone. `lint-imports` reports `KEPT` without
`(2 ignored imports)` at both places; measured before and after.

The row types moved from `storage/rows.py` to `contract/rows.py`. The
spec had them staying in `storage`, and that was wrong: `contract` is the
bottom layer and may not import `storage`, measured as BROKEN against the
`layers` contract. Six import sites updated, the old module deleted.

The protocol has eight methods, counted with grep over the two callers,
not copied from the implementation's method list. Counter-probes
measured: renaming `count_events` turns pyright red; re-adding the import
to `core/verify.py` turns both contracts BROKEN by name.

`module-boundaries.md` re-measured and rewritten where it described the
exemptions as present. All six edges the layer order permits exist now,
because `storage` imports `contract.rows`.

One suppression fewer in the tree (`S603`), CLAUDE.md's list says five.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

