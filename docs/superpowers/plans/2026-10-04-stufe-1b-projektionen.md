# Stufe 1b: Projektionen — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zwei Protokolle, die `core` von `PostgresStorage` lösen, eine Projektionsmaschinerie mit dem Nachweis „ableitbar und wegwerfbar", zwei Projektionen (`p_chronicle`, `p_source_stats`) und drei Kommandos (`project`, `chronicle`, `stats`) — mit der Doku im selben Zweig und dem Spec, der am Ende einfriert.

**Architecture:** `LogStore[Conn]` und `ProjectionStore[Conn]` in `previously.contract` (die Zeilentypen wandern mit, siehe Korrektur unten); `core.projection` mit reiner Ableitung (`derive`, `merge`) und einem gestapelt nachziehenden Arbeiter (`catch_up`), der Zeilen und `up_to_id` in einer Transaktion bewegt; `storage.postgres` implementiert beide Protokolle; drei neue Tabellen per Migration `0002_projections`. Der Arbeiter ist ein Kommando — keine Warteschlange (Spec §1.1).

**Tech Stack:** Python 3.14 (PEP 695-Generics, `class LogStore[Conn](Protocol)`), SQLAlchemy Core, Alembic, PostgreSQL ≥ 15 via testcontainers, Hypothesis, Sphinx/MyST + Vale.

**Spec:** `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md` — abgenommen am 2026-10-04. Der Plan argumentiert aus dem Spec; wer eine Aufgabe umsetzt, liest beide. Der Spec ist bis zum Einfrieren (Aufgabe 8) das maßgebliche Dokument; weicht dieser Plan von ihm ab, steht die Abweichung unten unter „Was der Plan am Spec korrigiert".

## Was der Plan am Spec korrigiert

Vier Dinge sind beim Planen herausgekommen, alle im Spec als datierte Korrekturblöcke nachgetragen (Commit mit diesem Plan):

1. **Die Zeilentypen müssen nach `contract`, nicht in `storage/rows.py` bleiben.** Spec §2.2 sagte, die Protokolle in `contract` nähmen die Typen aus `storage/rows.py`. Gemessen gegen `.importlinter`: `contract` ist die **unterste** Schicht des `layers`-Vertrags, und `contract → storage` wäre ein Import nach oben — `BROKEN`. Also wandert `storage/rows.py` komplett nach `contract/rows.py` (sechs Importstellen, gemessen mit `grep -rln "previously.storage.rows" src tests migrations`), und `storage/rows.py` wird gelöscht, kein Re-Export. Folge für die Doku: `storage` importiert dann `contract`, und `module-boundaries.md:37` („five of the six edges … `storage → contract` doesn't exist") wird **sechs von sechs**.
2. **`\r` gehört in die Entschärfung.** Spec §6.3 nannte `\t`, `\n`, `\\`. Ein `\r` im Inhalt (ein Konnektor kann es liefern; `split_plaintext` normalisiert nur den eigenen Weg) bricht eine Terminalzeile genauso. Also auch `\r` → die zwei Zeichen `\r`.
3. **Der erste Bau heißt `built`, nicht `rebuilt`.** Spec §6.1 zählt drei Ausgaben (`caught up`, `rebuilt`, `up to date`); der erste Lauf auf eine leere `projection_state` ist ein vierter Fall. `rebuilt: version 0 -> 1` wäre wörtlich falsch, es gab nichts zu *re*-bauen. Also `built: 42 events, up_to_id 42`.
4. **Singular, wo einer ist.** Spec §5.4 schrieb `projection is 1 events behind`. Die Meldungen zählen richtig: `1 event`, `12 events`.

## Global Constraints

Aus `CLAUDE.md`, für jede Aufgabe verbindlich:

- **Alle sechs Tore**, namentlich, je einzeln gefahren und im Bericht mit Ausgabe. Den Block kopieren, nicht aus dem Gedächtnis aufzählen — ein Fünfer-Verzeichnis hat am 2026-10-03 einen roten `pyright` durch zwei Prüfungen gelassen:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- **Englisch** in `src/`, `tests/`, `migrations/`, `docs/` (außer `docs/superpowers/`), Wurzelkonfiguration — Kommentare, Docstrings, Testnamen, Meldungen. Deutsch nur in Spec, Plan, `.superpowers/`.
- **Trailer `Assisted-By: Claude <Modell> <noreply@anthropic.com>`**, mit dem Modell, das die Arbeit getan hat. **Niemals `Co-Authored-By:`, niemals „Generated with"**, auch wenn die Umgebung es vorgibt — `CLAUDE.md` übersteuert das ausdrücklich.
- **Kein `# type: ignore`.** pyright strict ist der Boden; `cast` ist das Mittel.
- **Kein Mock** für Zeit, Datenbank oder Zufall. Tests gegen echtes PostgreSQL via testcontainers (`db`-Fixture aus `tests/conftest.py`).
- **Suppressions** nur als einzelnes `# noqa: RULE` mit Grund daneben, und jede neue in die Liste in `CLAUDE.md` — die Liste ist vollständig gemeint. Aufgabe 1 **entfernt** eine (`S603`), also sinkt die Zahl dort auf fünf.
- **Ein Kommentar ist eine Behauptung.** Jede Zahl, die in einen Kommentar oder eine Seite geht, wird am Code gemessen, nicht aus einem Bericht übernommen. Drei falsche Kommentarzahlen am 2026-10-03, der Code war jedes Mal richtig.
- **Eine Zusage braucht einen Test, von dem gemessen ist, dass er bricht** — mit einer Kontrolle daneben, die gemessen grün bleibt. Die Mutationen stehen in den Schritten.
- **Doku im selben Zweig, je Aufgabe**: wer Code ändert, zieht die Seite nach, die ihn beschreibt. Diátaxis, ein Quadrant je Seite, **ein Satz pro Zeile**, Überschriften in Satzschreibung, Bindestriche in Dateinamen, amerikanisches Englisch. Prosa-Direktiven (`note`, `warning`) in `:::`-Fences, Mermaid in Backtick-Fences. `Vale.Terms` nagelt die Schreibweise **jedes** Vokabeleintrags fest — ein kleingeschriebener Eintrag darf keinen Satz beginnen.
- **`Microsoft.HeadingAcronyms`**: keine Überschrift mit `SQL`, `NULL`, `JSON`, `FK`.
- **Keine neue Abhängigkeit** ohne Eintrag in `DEPENDENCIES.md`. Dieser Plan braucht keine.
- **`MAX_BATCH = 500` ist nicht tragend** (Spec §4.1): kein Test hängt von der Zahl ab.
- **`batch_size` im Abbruchtest ist 2**, damit zehn Events fünf Stapel sind.

## Review Focus

Fünf Eingaben, die der Spec impliziert, aber keine Aufgabe von sich aus prüft — je mit der Aufgabe, die den Test bekommt:

1. **Leeres Fenster** (`--since` ≥ `--until`): `chronicle` druckt nichts, Rückgabe 0, **kein** Kappungshinweis — ein leeres Fenster ist nicht gekappt. → Aufgabe 6.
2. **`--since` ohne Zeitzone**: `parse_moment` lehnt ab, Rückgabe 2, Meldung nennt die Zone. Dieselbe Funktion wie `--occurred-at`, derselbe Fehlerpfad. → Aufgabe 6.
3. **`\r` im Inhalt** einer Einheit: eine Ausgabezeile, `\r` als zwei Zeichen (Korrektur 2 oben). → Aufgabe 6.
4. **Code-Version kleiner als Tabellenversion** (Zurücknahme): Neubau, Ausgabe `rebuilt: version 3 -> 2`. Das ist der Grund für `!=` statt `<` in Spec §4.1. → Aufgabe 5.
5. **Leeres Log**: `project` meldet `up to date, up_to_id 0` für beide; `chronicle` und `stats` drucken nichts, kein Rückstand auf `stderr`. → Aufgabe 5 (Arbeiter) und 6 (Kommandos).

---

## Dateistruktur

**Neu:**
- `src/previously/contract/rows.py` — `Tip`, `EventRow`, `UnitRow` (verschoben aus `storage/rows.py`) + `ProjectionState`, `ChronicleRow`, `SourceStatsRow`
- `src/previously/contract/store.py` — `LogStore[Conn]`, `ProjectionStore[Conn]`
- `src/previously/core/projection/__init__.py` — Re-Exporte, `PROJECTIONS`
- `src/previously/core/projection/worker.py` — `Batch`, `Projection`, `Outcome`, `catch_up`
- `src/previously/core/projection/chronicle.py` — `derive`, `ChronicleProjection`, `CHRONICLE`
- `src/previously/core/projection/source_stats.py` — `derive`, `merge`, `SourceStatsProjection`, `SOURCE_STATS`
- `migrations/versions/0002_projections.py`
- `tests/test_projection_derive.py`, `tests/test_projection_worker.py`, `tests/test_projection_store.py`
- `docs/explanation/projections.md`, `docs/how-to/rebuild-a-projection.md`

**Geändert:** `core/append.py`, `core/verify.py`, `core/errors.py`, `storage/postgres.py`, `storage/schema.py`, `cli.py`, `.importlinter`, `tests/conftest.py`, `tests/test_contracts.py`, `tests/test_storage.py`, `tests/test_rows.py`, `tests/test_hashing.py`, `tests/test_cli.py`, `CLAUDE.md`, `README.md`, `docs/explanation/module-boundaries.md`, `docs/explanation/index.md`, `docs/how-to/index.md`, `docs/reference/cli.md`, `docs/reference/database-schema.md`, `docs/explanation/design-records.md`, `docs/tutorials/record-your-first-event.md`, `.vale-styles/config/vocabularies/Previously/accept.txt`, der Spec (Einfrier-Kopf).

**Gelöscht:** `src/previously/storage/rows.py`; in `tests/test_contracts.py` der Test `test_the_exempted_core_modules_load_no_sql_at_runtime` samt `_EXEMPTED_MODULES`, `_FORBIDDEN_AT_RUNTIME`, `_RUNTIME_PROBE`, `import sys`.

---

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

## Task 2: Schema und Migration — `projection_state`, `p_chronicle`, `p_source_stats`

**Files:**
- Modify: `src/previously/storage/schema.py`, `tests/conftest.py:34-42`, `docs/reference/database-schema.md`, `docs/explanation/index.md`
- Create: `migrations/versions/0002_projections.py`, `docs/explanation/projections.md`
- Test: `tests/test_schema.py` (bestehende Tests decken neue Tabellen automatisch, ein neuer kommt dazu)

**Interfaces:**
- Produces: `previously.storage.schema.{projection_state, p_chronicle, p_source_stats}` als `Table`-Objekte; Index `p_chronicle_occurred_idx`. Tabellen- und Spaltennamen genau wie Spec §3.

- [ ] **Schritt 1: Den Test schreiben, der die Tabellen verlangt**

In `tests/test_schema.py` anfügen:

```python
@pytest.mark.db
def test_the_projection_tables_exist(db: Engine) -> None:
    """Stage 1b adds three tables ({ref}`projections`); the migration has to
    create all three, the metadata has to declare all three, and the two
    have to agree — `test_the_declared_indexes_exist` above covers the index
    the same way."""
    with db.connect() as c:
        names = set(
            c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            .scalars()
            .all()
        )
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= names
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= set(metadata.tables)
```

- [ ] **Schritt 2: Laufen lassen — rot**

Run: `uv run pytest tests/test_schema.py::test_the_projection_tables_exist -v`
Erwartet: `FAILED`, die drei Namen fehlen in `names`.

- [ ] **Schritt 3: Die Tabellen deklarieren**

Ans Ende von `src/previously/storage/schema.py`:

```python
# --- Projections ({ref}`projections`) ---------------------------------------
#
# Derivable and disposable (architecture §4.4, frozen design record): these
# tables carry no truth of their own, so they carry no foreign keys onto one
# another — only onto `event`, because a projection of an event that does not
# exist must never be built. Prefix `p_`.

projection_state = Table(
    "projection_state",
    metadata,
    Column("name", Text, primary_key=True),
    # 0 = nothing built yet. Unambiguous because events number from 1.
    Column("up_to_id", BigInteger, nullable=False),
    # The rebuild trigger: the worker compares it with the version the code
    # declares, and any difference — not only a lower one — empties the table
    # and starts over.
    Column("version", Integer, nullable=False),
    Column("built_at", TIMESTAMP(timezone=True), nullable=False),
)

p_chronicle = Table(
    "p_chronicle",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("kind", Text, nullable=False),
    # NULL when the payload was erased: the kind of evidence lives in the
    # payload, and a tombstone has none. NOT NULL here would mean the chronicle
    # cannot show an erased event at all — a row in the log, silently missing.
    Column("evidence", Text),
    # NULL when the event carries no source attribution; `source_key` enforces
    # at most one per event, not at least one.
    Column("source", Text),
    Column("external_id", Text),
    Column("speaker", Text),
    Column("start_ms", Integer),
    Column("end_ms", Integer),
    PrimaryKeyConstraint("event_id", "seq"),
)

# The primary key carries chain order; this index carries time order
# (architecture §4.1 wants both). `chronicle` reads in index direction, and the
# triple is unique, so the output is deterministic.
Index("p_chronicle_occurred_idx", p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq)

p_source_stats = Table(
    "p_source_stats",
    metadata,
    Column("source", Text, primary_key=True),
    Column("events", BigInteger, nullable=False),
    Column("units", BigInteger, nullable=False),
    Column("first_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_event_id", BigInteger, ForeignKey("event.id"), nullable=False),
)
```

- [ ] **Schritt 4: Die Migration**

`migrations/versions/0002_projections.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projections: state, chronicle, source statistics

Revision ID: 0002_projections
Revises: 0001_log

A forward migration, unlike the corrections folded into `0001_log`: nothing
here touches the log, so there is nothing a rebuild would have to redo. The
three tables are derivable and disposable ({ref}`projections`); dropping them
loses no truth, and `previously project` builds them again from the log.
"""

from alembic import op

import sqlalchemy as sa


revision = "0002_projections"
down_revision = "0001_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_state",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("up_to_id", sa.BigInteger, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        "p_chronicle",
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text),
        sa.Column("source", sa.Text),
        sa.Column("external_id", sa.Text),
        sa.Column("speaker", sa.Text),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.PrimaryKeyConstraint("event_id", "seq"),
    )
    op.create_index("p_chronicle_occurred_idx", "p_chronicle", ["occurred_at", "event_id", "seq"])
    op.create_table(
        "p_source_stats",
        sa.Column("source", sa.Text, primary_key=True),
        sa.Column("events", sa.BigInteger, nullable=False),
        sa.Column("units", sa.BigInteger, nullable=False),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("p_source_stats")
    op.drop_index("p_chronicle_occurred_idx", table_name="p_chronicle")
    op.drop_table("p_chronicle")
    op.drop_table("projection_state")
```

- [ ] **Schritt 5: Das `db`-Fixture leert auch die neuen Tabellen**

`tests/conftest.py`, die `TRUNCATE`-Zeile in `db`:

```python
    with engine.begin() as c:
        c.execute(text("TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event"))
```

Docstring des Fixtures: „All three tables" → „All six tables". Ohne diese Zeile leckt der Zustand einer Projektion in den nächsten Test, und der Fehler sieht aus wie ein falsches Nachziehen.

- [ ] **Schritt 6: Laufen lassen — grün, und die bestehenden Schema-Tests mit**

Run: `uv run pytest tests/test_schema.py -v`
Erwartet: alle `PASSED`, darunter `test_the_declared_indexes_exist` (der neue Index ist in `metadata` **und** in der Datenbank) und `test_the_declared_nulls_not_distinct_reaches_the_database` (die neuen Indizes haben das Flag nicht, auf beiden Seiten).

- [ ] **Schritt 7: `database-schema.md` um drei Abschnitte**

Nach dem Muster der drei bestehenden (`## event` … `### Constraints and indexes`): je Tabelle eine Spaltentabelle mit Name, Typ, Nullbarkeit, Bedeutung — **abgelesen aus einer migrierten Datenbank**, nicht aus `schema.py`. Die Abschlussprüfung der Doku hat genau so gemessen (gegen `information_schema.columns` und `pg_indexes` in einem Container). Dazu je `### Constraints and indexes` mit den von PostgreSQL erzeugten Namen (`projection_state_pkey`, `p_chronicle_pkey`, `p_chronicle_event_id_fkey`, `p_chronicle_occurred_idx`, `p_source_stats_pkey`, `p_source_stats_last_event_id_fkey`) — **nachgeschlagen**, nicht geraten.

Reference-Ton: Tatsachen, keine Begründung. Für das Warum ein Satz: „{ref}`projections` explains why these tables carry no foreign keys onto one another."

- [ ] **Schritt 8: `projections.md` anlegen — mit dem, was jetzt schon stimmt**

`docs/explanation/projections.md`, Label `(projections)=`, Titel `# About derived views`. Diese Aufgabe schreibt die **ersten zwei Abschnitte**; Aufgaben 5, 6 und 7 fügen ihre an. Explanation-Ton, ein Satz pro Zeile.

Abschnitt 1, `## Derivable and disposable`: §4.4 der Architektur verspricht, dass Projektionen keine eigene Wahrheit tragen; was das praktisch heißt (wegwerfen und beim Neubau dasselbe bekommen); warum deshalb kein Fremdschlüssel zwischen Projektionen, wohl aber auf `event`.

Abschnitt 2, `## What the two tables are for`: `p_chronicle` ist eine Zeile je **Einheit** über vier Tabellen — der Unterschied zu `log`; warum `evidence` nullable ist (die Belegart steht in der Nutzlast, ein Grabstein hat keine — ein `NOT NULL` ließe eine Zeile des Logs still verschwinden); warum `source` nullable ist. `p_source_stats` als Aggregation, mit dem Satz aus Spec §3.3: inkrementell nachziehbar **nur, weil das Log append-only ist** — könnte eine Zeile verschwinden, bräuchte ein Minimum einen Neubau. Und der Vorgriff, dass genau das die Projektion zum Prüfstein macht (Aufgabe 5 schreibt den Abschnitt dazu).

In `docs/explanation/index.md` den Toctree um `projections` ergänzen (nach `module-boundaries`).

Run: `make -C docs html && make -C docs vale && make -C docs linkcheck`
Erwartet: grün, Vale **21 files**.

- [ ] **Schritt 9: Alle sechs Tore, Commit**

Run: der Block. Erwartet: grün, `pytest` **194 passed** (193 + 1).

```bash
git add -A
git commit -F - <<'MSG'
feat: the three projection tables, by migration 0002

`projection_state`, `p_chronicle` and `p_source_stats` as in spec §3,
declared in `schema.py` and created by `0002_projections`, which is a
plain forward migration: nothing touches the log. The `db` fixture
truncates all six tables now — without that, projection state leaks into
the next test and looks like a wrong catch-up.

`evidence` is nullable on purpose: the kind of evidence lives in the
payload and a tombstone has none, so NOT NULL would make the chronicle
unable to show an erased event. `p_chronicle_occurred_idx` carries time
order; the primary key carries chain order.

`database-schema.md` gains three sections read off a migrated database,
and `projections.md` opens with the two sections that are true already.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 3: `ProjectionStore[Conn]` und seine PostgreSQL-Implementierung

**Files:**
- Modify: `src/previously/contract/rows.py`, `src/previously/contract/store.py`, `src/previously/storage/postgres.py`
- Create: `tests/test_projection_store.py`

**Interfaces:**
- Produces: `contract.rows.{ProjectionState, ChronicleRow, SourceStatsRow}` (frozen dataclasses, Felder wie unten). `contract.store.ProjectionStore[Conn]` mit sieben Methoden. `PostgresStorage` implementiert sie, dazu **außerhalb** der Protokolle zwei Lesemethoden für die Kommandozeile: `read_chronicle(conn, *, since, until, limit) -> list[ChronicleRow]` und `read_source_stats(conn) -> list[SourceStatsRow]` — wie `units()` eine Methode, die nur `cli` ruft.

- [ ] **Schritt 1: Die Zeilentypen**

Ans Ende von `src/previously/contract/rows.py`:

```python
@dataclass(frozen=True)
class ProjectionState:
    """One row of `projection_state`: how far a projection has been built."""

    name: str
    up_to_id: int
    version: int
    built_at: datetime


@dataclass(frozen=True)
class ChronicleRow:
    event_id: int
    seq: int
    content: str
    occurred_at: datetime
    kind: str
    evidence: str | None
    source: str | None
    external_id: str | None
    speaker: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class SourceStatsRow:
    source: str
    events: int
    units: int
    first_seen: datetime
    last_seen: datetime
    last_event_id: int
```

- [ ] **Schritt 2: Das Protokoll**

In `src/previously/contract/store.py`, Importe ergänzen (`from datetime import datetime`, `ChronicleRow`, `ProjectionState`, `SourceStatsRow`) und anfügen:

```python
class ProjectionStore[Conn](Protocol):
    """A projection store: emptied, filled, updated — disposable by design.

    Separate from `LogStore` so that "carries no truth of its own"
    (architecture §4.4, frozen design record) stays a type and not a
    comment: nothing typed against `LogStore` can truncate, and nothing typed
    against this protocol can append to the log.

    `upsert_source_stats` writes the rows it is given. The arithmetic that
    merges an existing row with a batch — count plus count, earliest of two
    `first_seen` — is domain logic and lives in `core.projection.source_stats`,
    where a unit test reaches it without a database. Done in SQL
    (`ON CONFLICT DO UPDATE SET …`) the correctness of the incremental step
    would sit in `storage`, and the claim "derivation without SQL" would be
    false.
    """

    def begin(self) -> AbstractContextManager[Conn]: ...
    def projection_state(self, conn: Conn, name: str) -> ProjectionState | None: ...
    def set_projection_state(self, conn: Conn, state: ProjectionState) -> None: ...
    def truncate_projection(self, conn: Conn, name: str) -> None: ...
    def insert_chronicle(self, conn: Conn, rows: Sequence[ChronicleRow]) -> None: ...
    def source_stats(self, conn: Conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]: ...
    def upsert_source_stats(self, conn: Conn, rows: Sequence[SourceStatsRow]) -> None: ...
```

- [ ] **Schritt 3: Die Tests zuerst**

`tests/test_projection_store.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection half of `PostgresStorage`, method by method.

These are storage tests, not projection tests: they check that what goes in
comes back out, that truncation empties the right table, and that the state
row upserts. Whether the rows are the *right* rows is `test_projection_worker`.
"""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import ChronicleRow
from previously.contract.rows import EventRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import SourceStatsRow
from previously.contract.rows import UnitRow
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text

import pytest


NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)


def _event(storage: PostgresStorage, event_id: int) -> None:
    """One log row, so that the projection rows have an `event` to reference."""
    row = EventRow(
        id=event_id,
        kind="observation",
        recorded_at=NOW,
        occurred_at=NOW,
        prev_hash=None if event_id == 1 else bytes([event_id - 1]) * 32,
        hash=bytes([event_id]) * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x01" * 32,
        payload={"evidence": "recollection"},
    )
    with storage.begin() as c:
        storage.insert_event(c, row, [UnitRow(event_id, 1, "x")], ("cli", f"e{event_id}"))


@pytest.mark.db
def test_projection_state_is_absent_then_upserted(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.projection_state(c, "chronicle") is None
        storage.set_projection_state(c, ProjectionState("chronicle", 0, 1, NOW))
        storage.set_projection_state(c, ProjectionState("chronicle", 7, 1, NOW))
        state = storage.projection_state(c, "chronicle")
    assert state == ProjectionState("chronicle", 7, 1, NOW)


@pytest.mark.db
def test_chronicle_rows_round_trip(db: Engine) -> None:
    storage = PostgresStorage(db)
    _event(storage, 1)
    rows = [
        ChronicleRow(1, 1, "first", NOW, "observation", "recollection", "cli", "e1"),
        ChronicleRow(1, 2, "second", NOW, "observation", None, None, None, "alice", 10, 20),
    ]
    with storage.begin() as c:
        storage.insert_chronicle(c, rows)
        back = storage.read_chronicle(c, since=None, until=None, limit=10)
    assert back == rows


@pytest.mark.db
def test_read_chronicle_orders_by_time_then_chain_and_filters_a_half_open_window(db: Engine) -> None:
    """`(occurred_at, event_id, seq)` is the order ({ref}`projections`), and
    `--since` is inclusive while `--until` is exclusive."""
    storage = PostgresStorage(db)
    for event_id in (1, 2, 3):
        _event(storage, event_id)
    t1, t2, t3 = (datetime(2026, 10, d, tzinfo=UTC) for d in (1, 2, 3))
    with storage.begin() as c:
        # id 3 happened first, id 1 last: time order and chain order disagree.
        storage.insert_chronicle(
            c,
            [
                ChronicleRow(1, 1, "late", t3, "observation", None, None, None),
                ChronicleRow(2, 1, "middle", t2, "observation", None, None, None),
                ChronicleRow(3, 1, "early", t1, "observation", None, None, None),
            ],
        )
        everything = storage.read_chronicle(c, since=None, until=None, limit=10)
        window = storage.read_chronicle(c, since=t1, until=t3, limit=10)
    assert [r.content for r in everything] == ["early", "middle", "late"]
    assert [r.content for r in window] == ["early", "middle"]


@pytest.mark.db
def test_source_stats_round_trip_and_upsert(db: Engine) -> None:
    storage = PostgresStorage(db)
    _event(storage, 1)
    first = SourceStatsRow("cli", 1, 1, NOW, NOW, 1)
    second = SourceStatsRow("cli", 2, 3, NOW, NOW, 1)
    with storage.begin() as c:
        storage.upsert_source_stats(c, [first])
        storage.upsert_source_stats(c, [second])
        by_source = storage.source_stats(c, ["cli", "nobody"])
        listed = storage.read_source_stats(c)
    assert by_source == {"cli": second}
    assert listed == [second]


@pytest.mark.db
def test_truncate_empties_only_the_named_projection(db: Engine) -> None:
    storage = PostgresStorage(db)
    _event(storage, 1)
    with storage.begin() as c:
        storage.insert_chronicle(c, [ChronicleRow(1, 1, "x", NOW, "observation", None, None, None)])
        storage.upsert_source_stats(c, [SourceStatsRow("cli", 1, 1, NOW, NOW, 1)])
        storage.truncate_projection(c, "chronicle")
        chronicle = c.execute(text("SELECT count(*) FROM p_chronicle")).scalar_one()
        stats = c.execute(text("SELECT count(*) FROM p_source_stats")).scalar_one()
    assert (chronicle, stats) == (0, 1)


@pytest.mark.db
def test_truncating_an_unknown_projection_is_an_error(db: Engine) -> None:
    storage = PostgresStorage(db)
    with pytest.raises(ValueError, match="unknown projection"), storage.begin() as c:
        storage.truncate_projection(c, "nothing")


@pytest.mark.db
def test_empty_batches_make_no_round_trip(db: Engine) -> None:
    """`IN ()` is not valid SQL, and an empty insert is a pointless statement —
    both return without touching the connection, like `source_keys` does."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_chronicle(c, [])
        storage.upsert_source_stats(c, [])
        assert storage.source_stats(c, []) == {}
```

- [ ] **Schritt 4: Laufen lassen — rot**

Run: `uv run pytest tests/test_projection_store.py -v`
Erwartet: `AttributeError`, `PostgresStorage` hat die Methoden nicht.

- [ ] **Schritt 5: Die Implementierung**

In `src/previously/storage/postgres.py`: Importe ergänzen —

```python
from previously.contract.rows import ChronicleRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import SourceStatsRow
from previously.storage.schema import p_chronicle
from previously.storage.schema import p_source_stats
from previously.storage.schema import projection_state
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
```

und unter `TYPE_CHECKING` `from datetime import datetime`. Nach `source_keys` anfügen:

```python
    # --- ProjectionStore ({ref}`projections`) --------------------------------

    # Name as the caller knows it -> table. `truncate_projection` takes the
    # name and not the table, because `core` must not know a `Table`.
    _PROJECTION_TABLES = {"chronicle": p_chronicle, "source-stats": p_source_stats}

    def projection_state(self, conn: Connection, name: str) -> ProjectionState | None:
        row = conn.execute(
            select(projection_state).where(projection_state.c.name == name)
        ).one_or_none()
        if row is None:
            return None
        return ProjectionState(
            name=row.name, up_to_id=row.up_to_id, version=row.version, built_at=row.built_at
        )

    def set_projection_state(self, conn: Connection, state: ProjectionState) -> None:
        statement = pg_insert(projection_state).values(
            name=state.name,
            up_to_id=state.up_to_id,
            version=state.version,
            built_at=state.built_at,
        )
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[projection_state.c.name],
                set_={
                    "up_to_id": statement.excluded.up_to_id,
                    "version": statement.excluded.version,
                    "built_at": statement.excluded.built_at,
                },
            )
        )

    def truncate_projection(self, conn: Connection, name: str) -> None:
        """Empties one projection table. A plain DELETE, not TRUNCATE: TRUNCATE
        takes an ACCESS EXCLUSIVE lock and is not transactional in the sense
        that matters here — the caller's transaction has to be able to roll
        it back together with the state row."""
        try:
            table = self._PROJECTION_TABLES[name]
        except KeyError:
            raise ValueError(f"unknown projection {name!r}") from None
        conn.execute(delete(table))

    def insert_chronicle(self, conn: Connection, rows: Sequence[ChronicleRow]) -> None:
        if not rows:
            return
        conn.execute(
            insert(p_chronicle),
            [
                {
                    "event_id": r.event_id,
                    "seq": r.seq,
                    "content": r.content,
                    "occurred_at": r.occurred_at,
                    "kind": r.kind,
                    "evidence": r.evidence,
                    "source": r.source,
                    "external_id": r.external_id,
                    "speaker": r.speaker,
                    "start_ms": r.start_ms,
                    "end_ms": r.end_ms,
                }
                for r in rows
            ],
        )

    def source_stats(self, conn: Connection, sources: Sequence[str]) -> dict[str, SourceStatsRow]:
        if not sources:
            return {}
        return {
            row.source: SourceStatsRow(
                source=row.source,
                events=row.events,
                units=row.units,
                first_seen=row.first_seen,
                last_seen=row.last_seen,
                last_event_id=row.last_event_id,
            )
            for row in conn.execute(
                select(p_source_stats).where(p_source_stats.c.source.in_(sources))
            )
        }

    def upsert_source_stats(self, conn: Connection, rows: Sequence[SourceStatsRow]) -> None:
        """Writes the rows as given — the merge arithmetic lives in `core`
        ({ref}`projections`), so a unit test reaches it without a database."""
        if not rows:
            return
        statement = pg_insert(p_source_stats)
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[p_source_stats.c.source],
                set_={
                    "events": statement.excluded.events,
                    "units": statement.excluded.units,
                    "first_seen": statement.excluded.first_seen,
                    "last_seen": statement.excluded.last_seen,
                    "last_event_id": statement.excluded.last_event_id,
                },
            ),
            [
                {
                    "source": r.source,
                    "events": r.events,
                    "units": r.units,
                    "first_seen": r.first_seen,
                    "last_seen": r.last_seen,
                    "last_event_id": r.last_event_id,
                }
                for r in rows
            ],
        )

    # --- Reads for the command line, outside the protocols -------------------
    # Like `units`: only `cli` calls these. The protocols hold what `core`
    # needs, and `core` never reads a projection back.

    def read_chronicle(
        self,
        conn: Connection,
        *,
        since: datetime | None,
        until: datetime | None,
        limit: int,
    ) -> list[ChronicleRow]:
        """Time order, half-open window: `since` inclusive, `until` exclusive."""
        query = select(p_chronicle)
        if since is not None:
            query = query.where(p_chronicle.c.occurred_at >= since)
        if until is not None:
            query = query.where(p_chronicle.c.occurred_at < until)
        query = query.order_by(
            p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq
        ).limit(limit)
        return [
            ChronicleRow(
                event_id=row.event_id,
                seq=row.seq,
                content=row.content,
                occurred_at=row.occurred_at,
                kind=row.kind,
                evidence=row.evidence,
                source=row.source,
                external_id=row.external_id,
                speaker=row.speaker,
                start_ms=row.start_ms,
                end_ms=row.end_ms,
            )
            for row in conn.execute(query)
        ]

    def read_source_stats(self, conn: Connection) -> list[SourceStatsRow]:
        return [
            SourceStatsRow(
                source=row.source,
                events=row.events,
                units=row.units,
                first_seen=row.first_seen,
                last_seen=row.last_seen,
                last_event_id=row.last_event_id,
            )
            for row in conn.execute(select(p_source_stats).order_by(p_source_stats.c.source))
        ]
```

Der Docstring der Klasse (Zeile 5–10 der Datei) sagt „no update, no delete". Das stimmt für das **Log** weiter und wird für die Projektionen bewusst gebrochen — einen Satz dazu: „The projection methods below delete and update, and that is the point: a projection is disposable, the log is not; the two protocols in `contract.store` keep the two apart."

- [ ] **Schritt 6: Laufen lassen — grün**

Run: `uv run pytest tests/test_projection_store.py -v`
Erwartet: sieben `PASSED`.

Run: `uv run pyright`
Erwartet: `0 errors` — insbesondere muss `PostgresStorage` jetzt `ProjectionStore[Connection]` erfüllen. Das prüft erst Aufgabe 5 durch Benutzung; hier eine Zeile in `tests/test_projection_store.py` dafür:

```python
def test_postgres_storage_satisfies_both_protocols() -> None:
    """Static, not dynamic: pyright proves it at the assignment. The function
    exists so the proof has a name a reviewer can point at."""
    from previously.contract.store import LogStore
    from previously.contract.store import ProjectionStore
    from sqlalchemy import Connection
    from sqlalchemy import create_engine

    storage = PostgresStorage(create_engine("postgresql+psycopg://x:y@localhost/z"))
    log: LogStore[Connection] = storage
    projections: ProjectionStore[Connection] = storage
    # The two assignments above are the proof; pyright rejects them if a
    # method is missing. The isinstance checks only give the test a body.
    assert isinstance(log, PostgresStorage)
    assert isinstance(projections, PostgresStorage)
```

(`create_engine` verbindet nicht; es parst nur.)

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **202 passed** (194 + 8).

```bash
git add -A
git commit -F - <<'MSG'
feat: ProjectionStore[Conn], and PostgresStorage implements it

Seven methods in `contract.store`, kept apart from `LogStore` so that
"carries no truth of its own" is a type: nothing typed against the log can
truncate, nothing typed against a projection can append.

`upsert_source_stats` writes rows as given; the merge arithmetic is domain
logic and goes to `core` in the next task, where a unit test reaches it
without a database. `truncate_projection` is a DELETE, not TRUNCATE, so the
caller's transaction can roll it back together with the state row.

Two reads for the command line stay outside the protocols, like `units`:
`read_chronicle` in time order with a half-open window, `read_source_stats`
by source. Three new row types in `contract.rows`.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 4: Reine Ableitung — `chronicle.derive`, `source_stats.derive`, `source_stats.merge`

**Files:**
- Create: `src/previously/core/projection/__init__.py`, `src/previously/core/projection/worker.py` (nur `Batch` in dieser Aufgabe), `src/previously/core/projection/chronicle.py`, `src/previously/core/projection/source_stats.py`, `tests/test_projection_derive.py`

**Interfaces:**
- Produces: `core.projection.worker.Batch(events: tuple[EventRow, ...], units: Mapping[int, Sequence[UnitRow]], keys: Mapping[int, tuple[str, str]])`; `chronicle.derive(batch) -> list[ChronicleRow]`; `source_stats.derive(batch) -> dict[str, SourceStatsRow]`; `source_stats.merge(existing: SourceStatsRow | None, addition: SourceStatsRow) -> SourceStatsRow`. Alles ohne Datenbank, ohne SQL.

- [ ] **Schritt 1: `Batch` — der Eingabetyp**

`src/previously/core/projection/worker.py` (in dieser Aufgabe nur das; `catch_up` kommt in Aufgabe 5 in dieselbe Datei):

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection worker ({ref}`projections`): batches, and the catch-up."""

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.rows import EventRow
    from previously.contract.rows import UnitRow


@dataclass(frozen=True)
class Batch:
    """What one catch-up step reads from the log: a run of events in chain
    order with their units and source attributions, fetched by batch — one
    query each, not one per event, for the reason `units_by_event` and
    `source_keys` exist."""

    events: tuple[EventRow, ...]
    units: Mapping[int, Sequence[UnitRow]]
    keys: Mapping[int, tuple[str, str]]
```

`src/previously/core/projection/__init__.py` vorerst nur mit Lizenzkopf und Docstring `"""Projections: derived, disposable views over the log ({ref}`projections`)."""` — die Re-Exporte kommen in Aufgabe 5.

- [ ] **Schritt 2: Die Tests zuerst**

`tests/test_projection_derive.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The derivation functions, without a database.

They take row types and return row types; that is the whole point of keeping
the arithmetic in `core` ({ref}`projections`), and it is why these tests
carry no `db` marker.
"""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import EventRow
from previously.contract.rows import SourceStatsRow
from previously.contract.rows import UnitRow
from previously.core.projection import chronicle
from previously.core.projection import source_stats
from previously.core.projection.worker import Batch


T1 = datetime(2026, 10, 1, tzinfo=UTC)
T2 = datetime(2026, 10, 2, tzinfo=UTC)
T3 = datetime(2026, 10, 3, tzinfo=UTC)


def _event(event_id: int, occurred_at: datetime, payload: dict[str, object] | None) -> EventRow:
    return EventRow(
        id=event_id,
        kind="observation",
        recorded_at=T3,
        occurred_at=occurred_at,
        prev_hash=None,
        hash=bytes([event_id]) * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x01" * 32,
        payload=payload,
    )


def test_chronicle_derives_one_row_per_unit_with_the_source_attribution() -> None:
    batch = Batch(
        events=(_event(1, T1, {"evidence": "verbatim", "text": "a\n\nb"}),),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b", speaker="alice")]},
        keys={1: ("email", "msg-1")},
    )
    rows = chronicle.derive(batch)
    assert [(r.event_id, r.seq, r.content) for r in rows] == [(1, 1, "a"), (1, 2, "b")]
    assert {(r.source, r.external_id, r.evidence) for r in rows} == {("email", "msg-1", "verbatim")}
    assert rows[1].speaker == "alice"
    assert rows[0].occurred_at == T1


def test_chronicle_leaves_source_null_for_an_event_without_a_key() -> None:
    batch = Batch(events=(_event(1, T1, {"evidence": "recollection"}),), units={1: [UnitRow(1, 1, "a")]}, keys={})
    (row,) = chronicle.derive(batch)
    assert (row.source, row.external_id) == (None, None)


def test_chronicle_still_derives_rows_for_an_erased_payload() -> None:
    """A tombstone empties the payload and leaves the units standing
    ({ref}`projections`): the chronicle shows them, with `evidence` NULL.
    Whoever builds an erasure that deletes units has to change this test on
    purpose."""
    batch = Batch(events=(_event(1, T1, None),), units={1: [UnitRow(1, 1, "a")]}, keys={1: ("cli", "x")})
    (row,) = chronicle.derive(batch)
    assert row.evidence is None
    assert row.content == "a"


def test_chronicle_derives_nothing_for_an_event_without_units() -> None:
    batch = Batch(events=(_event(1, T1, {"evidence": "recollection"}),), units={}, keys={})
    assert chronicle.derive(batch) == []


def test_source_stats_aggregates_a_batch_per_source() -> None:
    batch = Batch(
        events=(_event(1, T1, {}), _event(2, T2, {}), _event(3, T3, {})),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b")], 2: [UnitRow(2, 1, "c")], 3: []},
        keys={1: ("email", "m1"), 2: ("email", "m2"), 3: ("cli", "x")},
    )
    stats = source_stats.derive(batch)
    assert stats == {
        "email": SourceStatsRow("email", events=2, units=3, first_seen=T1, last_seen=T2, last_event_id=2),
        "cli": SourceStatsRow("cli", events=1, units=0, first_seen=T3, last_seen=T3, last_event_id=3),
    }


def test_source_stats_ignores_an_event_without_a_source() -> None:
    batch = Batch(events=(_event(1, T1, {}),), units={1: [UnitRow(1, 1, "a")]}, keys={})
    assert source_stats.derive(batch) == {}


def test_merge_adds_counts_and_keeps_the_extremes() -> None:
    existing = SourceStatsRow("email", 2, 3, T1, T2, 2)
    addition = SourceStatsRow("email", 1, 1, T3, T3, 3)
    assert source_stats.merge(existing, addition) == SourceStatsRow("email", 3, 4, T1, T3, 3)


def test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older() -> None:
    """The regression case the spec names (§5.2): an event that *arrives*
    later but *happened* earlier. Assignment and minimum agree on every
    in-order sequence and part here. Measured on 2026-10-04: with
    `first_seen=addition.first_seen` this test fails and the one above stays
    green — the one above is the control."""
    existing = SourceStatsRow("email", 1, 1, T2, T2, 1)
    late_but_older = SourceStatsRow("email", 1, 1, T1, T1, 2)
    merged = source_stats.merge(existing, late_but_older)
    assert merged.first_seen == T1
    assert merged.last_seen == T2
    assert merged.last_event_id == 2


def test_merge_with_nothing_existing_is_the_addition() -> None:
    addition = SourceStatsRow("email", 1, 1, T1, T1, 1)
    assert source_stats.merge(None, addition) == addition
```

- [ ] **Schritt 3: Laufen lassen — rot**

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: `ModuleNotFoundError` für `chronicle`/`source_stats`.

- [ ] **Schritt 4: `chronicle.py`**

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle: one row per unit, each with its source attribution.

A denormalization over four tables — `event`, `unit`, `source_key` and the
payload for the kind of evidence — cut to the question "what happened, line
by line, and how do I know". That is what makes it a projection and not a
copy of `log` ({ref}`projections`).
"""

from dataclasses import dataclass
from previously.contract.rows import ChronicleRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def _evidence(payload: Mapping[str, object] | None) -> str | None:
    """The kind of evidence out of the payload, or None for a tombstone.

    `append` mixes it in under the reserved key ({ref}`canonicalization`);
    a value that is not a string is not one this projection can name.
    """
    if payload is None:
        return None
    value = payload.get("evidence")
    return value if isinstance(value, str) else None


def derive(batch: Batch) -> list[ChronicleRow]:
    rows: list[ChronicleRow] = []
    for event in batch.events:
        key = batch.keys.get(event.id)
        evidence = _evidence(event.payload)
        for unit in batch.units.get(event.id, ()):
            rows.append(
                ChronicleRow(
                    event_id=event.id,
                    seq=unit.seq,
                    content=unit.content,
                    occurred_at=event.occurred_at,
                    kind=event.kind,
                    evidence=evidence,
                    source=None if key is None else key[0],
                    external_id=None if key is None else key[1],
                    speaker=unit.speaker,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                )
            )
    return rows


@dataclass(frozen=True)
class ChronicleProjection:
    """Name and version as `projection_state` knows them, and the write step.

    A frozen dataclass rather than module constants, so a test can say
    `ChronicleProjection(version=2)` to force a rebuild without touching this
    module.
    """

    name: str = "chronicle"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        store.insert_chronicle(conn, derive(batch))


CHRONICLE = ChronicleProjection()
```

- [ ] **Schritt 5: `source_stats.py`**

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Per-source statistics: the aggregate that puts the assurance to the test.

Counts are additive and `first_seen`/`last_seen` are extremes, and they can be
caught up incrementally **only because the log is append-only**: were a row
able to disappear, a minimum would need a rebuild, because a minimum does not
show whether its carrier still exists ({ref}`projections`).

The merge arithmetic is here and not in SQL. Done as `ON CONFLICT DO UPDATE
SET events = events + excluded.events, first_seen = least(…)` the
correctness of the incremental step would sit in `storage`, and the claim
"derivation without SQL" would be false. Here a unit test reaches it without a
database — and the one that matters is the late arrival that happened
earlier, where assignment and minimum part.
"""

from dataclasses import dataclass
from previously.contract.rows import SourceStatsRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def merge(existing: SourceStatsRow | None, addition: SourceStatsRow) -> SourceStatsRow:
    if existing is None:
        return addition
    return SourceStatsRow(
        source=existing.source,
        events=existing.events + addition.events,
        units=existing.units + addition.units,
        first_seen=min(existing.first_seen, addition.first_seen),
        last_seen=max(existing.last_seen, addition.last_seen),
        last_event_id=max(existing.last_event_id, addition.last_event_id),
    )


def derive(batch: Batch) -> dict[str, SourceStatsRow]:
    """The batch folded per source. Events without a source attribution do not
    count: there is no source to attribute them to. The chronicle shows them,
    this table does not — a decision, so it is written down."""
    out: dict[str, SourceStatsRow] = {}
    for event in batch.events:
        key = batch.keys.get(event.id)
        if key is None:
            continue
        source = key[0]
        addition = SourceStatsRow(
            source=source,
            events=1,
            units=len(batch.units.get(event.id, ())),
            first_seen=event.occurred_at,
            last_seen=event.occurred_at,
            last_event_id=event.id,
        )
        out[source] = merge(out.get(source), addition)
    return out


@dataclass(frozen=True)
class SourceStatsProjection:
    name: str = "source-stats"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        additions = derive(batch)
        if not additions:
            return
        existing = store.source_stats(conn, sorted(additions))
        store.upsert_source_stats(
            conn, [merge(existing.get(source), row) for source, row in sorted(additions.items())]
        )


SOURCE_STATS = SourceStatsProjection()
```

- [ ] **Schritt 6: Laufen lassen — grün, dann die Mutation**

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: neun `PASSED`.

**Messung, nicht committen — zwei Mutationen, je eine Kontrolle.**

(a) In `merge` `first_seen=min(existing.first_seen, addition.first_seen)` durch `first_seen=existing.first_seen` ersetzen (nie nachziehen).

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: **genau einer** rot — `test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older`; `test_merge_adds_counts_and_keeps_the_extremes` bleibt grün (die Kontrolle: in Zeitreihenfolge bleibt das erste das erste, Nie-Nachziehen und Minimum sind gleich).

(b) Zurücksetzen, dann durch `first_seen=addition.first_seen` ersetzen (immer überschreiben).

Run: dasselbe.
Erwartet: **genau einer** rot — `test_merge_adds_counts_and_keeps_the_extremes` (das Überschreiben setzt T3 statt T1); der Nachzügler-Test bleibt grün, weil der ältere Nachzügler zufällig das Minimum *ist*.

Zurücksetzen. Alle neun grün. Beide Messungen in den Bericht und in den Docstring des Regressionstests — der muss sagen, **welche** Mutation ihn fallen lässt (a) und dass die andere (b) vom In-Order-Test gefangen wird. Zusammen fangen die zwei Tests beide natürlichen Fehler.

> Die erste Fassung dieses Schritts hatte nur Mutation (b) und erwartete,
> dass sie den Nachzügler-Test fällt. Gemessen vom Umsetzer der Aufgabe 4:
> umgekehrt. Spec §5.2 trug dasselbe falsche Beispiel; dort korrigiert.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **211 passed** (202 + 9). `lint-imports`: `core.projection.*` importiert `contract.rows`, `contract.store` — beides erlaubt, `4 kept, 0 broken`.

```bash
git add -A
git commit -F - <<'MSG'
feat: the two derivations, pure and tested without a database

`chronicle.derive` flattens an event, its units and its source attribution
into one row per unit; `evidence` is None for a tombstone, and the rows
still exist — the test pins that on purpose, so a future erasure has to
change it deliberately.

`source_stats.derive` folds a batch per source and `merge` folds a batch
into an existing row: counts add, extremes take the minimum and maximum.
The regression case the spec names is a test: an event that arrives later
but happened earlier. Measured — with `first_seen = addition.first_seen`
that test fails alone and the in-order test stays green, which is what
makes the in-order test the control and not a duplicate.

`Batch` in `worker.py` is the input type; the worker itself follows.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 5: Der Arbeiter `catch_up` — und die Zusage gegen den inkrementellen Weg

**Files:**
- Modify: `src/previously/core/projection/worker.py`, `src/previously/core/projection/__init__.py`, `src/previously/core/errors.py`, `docs/explanation/projections.md`
- Create: `tests/test_projection_worker.py`

**Interfaces:**
- Consumes: `Batch`, `CHRONICLE`, `SOURCE_STATS`, beide Protokolle.
- Produces: `worker.Projection` (Protocol: `name: str`, `version: int`, `write[Conn](store, conn, batch) -> None`); `worker.Outcome(name, version, rebuilt_from: int | None, events: int, up_to_id: int)`; `worker.catch_up[Conn](log: LogStore[Conn], store: ProjectionStore[Conn], projection: Projection, *, batch_size: int = 500) -> Outcome`; `core.projection.PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)`; `core.errors.ProjectionGap`.

- [ ] **Schritt 1: Der Fehlertyp für das, was §4.2 ausschließt**

Ans Ende von `src/previously/core/errors.py`:

```python
class ProjectionGap(PreviouslyError):
    """The log has a gap above `up_to_id` — which {ref}`projections` says it
    cannot have: `id = predecessor.id + 1` and the unique index on `prev_hash`
    leave no room for one. Raised rather than skipped over, because a worker
    that silently moved past a gap would turn an impossible state into a
    silent loss."""
```

- [ ] **Schritt 2: Die Tests zuerst**

`tests/test_projection_worker.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The worker, and the assurance that justifies it ({ref}`projections`).

The one test that matters is `test_incremental_equals_rebuilt`: build the
projections one event at a time, then from scratch, and compare rows. A
rebuild-only test proves determinism; only the comparison catches a wrong
incremental step, and that is the failure that kills projections.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.contract.rows import ChronicleRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import SourceStatsRow
from previously.contract.store import ProjectionStore
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.projection import PROJECTIONS
from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.chronicle import ChronicleProjection
from previously.core.projection.source_stats import SOURCE_STATS
from previously.core.projection.source_stats import SourceStatsProjection
from previously.core.projection.worker import catch_up
from previously.core.units import split_plaintext
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Connection
from sqlalchemy import Engine
from sqlalchemy import text
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Sequence
    from contextlib import AbstractContextManager

NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)


def _raw(n: int, source: str, occurred_at: datetime, text_: str = "one\n\ntwo") -> RawEvent:
    return RawEvent(
        source=source,
        external_id=f"{source}-{n}",
        occurred_at=occurred_at,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext(text_),
        payload={"text": text_},
    )


def _snapshot(db: Engine) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    """Both projection tables as sorted tuples — rows, not a digest, so a
    failure names the field that moved (the lesson of the pinned hash vector)."""
    with db.begin() as c:
        chronicle = [tuple(r) for r in c.execute(text("SELECT * FROM p_chronicle ORDER BY event_id, seq"))]
        stats = [tuple(r) for r in c.execute(text("SELECT * FROM p_source_stats ORDER BY source"))]
    return chronicle, stats


def _project_all(storage: PostgresStorage) -> None:
    for projection in PROJECTIONS:
        catch_up(storage, storage, projection)


def _force_rebuild(storage: PostgresStorage) -> None:
    """The path spec §5.2 names: truncate and `up_to_id = 0`, version
    unchanged — the worker then catches up from scratch."""
    with storage.begin() as c:
        for projection in PROJECTIONS:
            storage.truncate_projection(c, projection.name)
            storage.set_projection_state(c, ProjectionState(projection.name, 0, projection.version, NOW))


@pytest.mark.db
def test_incremental_equals_rebuilt(db: Engine) -> None:
    """Spec §5.2, with the named case folded in: event 3 happened before
    event 2, so `first_seen` for `email` has to come out of the minimum and
    not out of the last write."""
    storage = PostgresStorage(db)
    moments = [NOW, NOW + timedelta(days=1), NOW - timedelta(days=5)]
    for n, moment in enumerate(moments, start=1):
        append(storage, [_raw(n, "email", moment)], recorded_at=NOW)
        _project_all(storage)  # the incremental path, one event at a time
    incremental = _snapshot(db)

    _force_rebuild(storage)
    _project_all(storage)
    rebuilt = _snapshot(db)

    assert incremental == rebuilt
    (stats_row,) = rebuilt[1]
    assert stats_row[3] == NOW - timedelta(days=5)  # first_seen is the earliest, not the last


@pytest.mark.db
def test_a_version_bump_rebuilds_and_without_it_nothing_moves(db: Engine) -> None:
    """Spec §5.4: poison a row, bump the version, the poison is gone — and
    the control: without the bump the poison stays."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    catch_up(storage, storage, SOURCE_STATS)
    with db.begin() as c:
        c.execute(text("UPDATE p_source_stats SET events = 999"))

    unchanged = catch_up(storage, storage, SOURCE_STATS)  # control: same version
    with db.begin() as c:
        assert c.execute(text("SELECT events FROM p_source_stats")).scalar_one() == 999
    assert unchanged.rebuilt_from is None
    assert unchanged.events == 0

    outcome = catch_up(storage, storage, SourceStatsProjection(version=2))
    with db.begin() as c:
        assert c.execute(text("SELECT events FROM p_source_stats")).scalar_one() == 1
        version = c.execute(text("SELECT version FROM projection_state WHERE name = 'source-stats'")).scalar_one()
    assert version == 2
    assert outcome.rebuilt_from == 1
    assert outcome.events == 1


@pytest.mark.db
def test_a_lower_code_version_rebuilds_too(db: Engine) -> None:
    """Review Focus 4: `!=`, not `<`. Code at version 2, table at version 3
    — a rolled-back release derives differently from the table it meets."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    catch_up(storage, storage, ChronicleProjection(version=3))
    outcome = catch_up(storage, storage, ChronicleProjection(version=2))
    assert outcome.rebuilt_from == 3
    assert outcome.version == 2
    assert outcome.events == 1


class _FailingStore:
    """A `ProjectionStore` that raises on the n-th `insert_chronicle`.

    Everything else delegates. That this wrapper is twenty lines and no mock
    is the dividend of the protocol ({ref}`module-boundaries`): typed against
    the concrete `PostgresStorage` there would be no such thing.
    """

    def __init__(self, inner: PostgresStorage, fail_on_call: int) -> None:
        self._inner = inner
        self._fail_on = fail_on_call
        self._calls = 0

    def begin(self) -> AbstractContextManager[Connection]:
        return self._inner.begin()

    def projection_state(self, conn: Connection, name: str) -> ProjectionState | None:
        return self._inner.projection_state(conn, name)

    def set_projection_state(self, conn: Connection, state: ProjectionState) -> None:
        self._inner.set_projection_state(conn, state)

    def truncate_projection(self, conn: Connection, name: str) -> None:
        self._inner.truncate_projection(conn, name)

    def insert_chronicle(self, conn: Connection, rows: Sequence[ChronicleRow]) -> None:
        self._calls += 1
        if self._calls == self._fail_on:
            raise RuntimeError("injected failure")
        self._inner.insert_chronicle(conn, rows)

    def source_stats(self, conn: Connection, sources: Sequence[str]) -> dict[str, SourceStatsRow]:
        return self._inner.source_stats(conn, sources)

    def upsert_source_stats(self, conn: Connection, rows: Sequence[SourceStatsRow]) -> None:
        self._inner.upsert_source_stats(conn, rows)


@pytest.mark.db
def test_an_abort_leaves_rows_and_up_to_id_in_step(db: Engine) -> None:
    """Spec §4.1: rows and `up_to_id` move in one transaction or not at all.
    Batch size 2, ten events, failure in the third batch: four events are
    projected and `up_to_id` says four. The next run closes the gap."""
    storage = PostgresStorage(db)
    append(storage, [_raw(n, "email", NOW) for n in range(1, 11)], recorded_at=NOW)
    failing: ProjectionStore[Connection] = _FailingStore(storage, fail_on_call=3)

    with pytest.raises(RuntimeError, match="injected"):
        catch_up(storage, failing, CHRONICLE, batch_size=2)

    with db.begin() as c:
        highest = c.execute(text("SELECT max(event_id) FROM p_chronicle")).scalar_one()
        rows = c.execute(text("SELECT count(*) FROM p_chronicle")).scalar_one()
    state = _state(storage, "chronicle")
    assert state is not None
    assert (state.up_to_id, highest, rows) == (4, 4, 8)  # two units per event

    outcome = catch_up(storage, storage, CHRONICLE, batch_size=2)
    assert (outcome.events, outcome.up_to_id) == (6, 10)


def _state(storage: PostgresStorage, name: str) -> ProjectionState | None:
    with storage.begin() as c:
        return storage.projection_state(c, name)


@pytest.mark.db
def test_a_second_run_changes_nothing(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    _project_all(storage)
    before = _snapshot(db)
    outcomes = [catch_up(storage, storage, p) for p in PROJECTIONS]
    assert _snapshot(db) == before
    assert all(o.events == 0 and o.rebuilt_from is None for o in outcomes)


@pytest.mark.db
def test_an_empty_log_is_up_to_date_at_zero(db: Engine) -> None:
    """Review Focus 5."""
    storage = PostgresStorage(db)
    outcome = catch_up(storage, storage, CHRONICLE)
    assert (outcome.rebuilt_from, outcome.events, outcome.up_to_id) == (0, 0, 0)
    assert _snapshot(db) == ([], [])


@pytest.mark.db
def test_an_event_without_a_source_is_in_the_chronicle_and_not_in_the_stats(db: Engine) -> None:
    """Spec §3.3: no source, nothing to attribute to. Written through
    `insert_event` with `key=None`, which `append` never does — a connector
    for assertions would."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    from previously.contract.rows import EventRow
    from previously.contract.rows import UnitRow

    with storage.begin() as c:
        tip = storage.tip(c)
        assert tip is not None
        storage.insert_event(
            c,
            EventRow(2, "observation", NOW, NOW, tip.hash, b"\x02" * 32, b"\x00" * 32, b"\x01" * 32, {}),
            [UnitRow(2, 1, "orphan")],
            None,
        )
    _project_all(storage)
    chronicle, stats = _snapshot(db)
    assert any(r[0] == 2 and r[6] is None for r in chronicle)  # event_id 2, source NULL
    assert [r[0] for r in stats] == ["email"]
    assert stats[0][1] == 1  # one event counted, not two


@pytest.mark.db
def test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null(db: Engine) -> None:
    """Spec §1.1: erasing the payload does not erase the units. Pinned, so
    that an erasure which deletes units has to change this on purpose."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))
    catch_up(storage, storage, CHRONICLE)
    with db.begin() as c:
        rows = c.execute(text("SELECT content, evidence FROM p_chronicle ORDER BY seq")).all()
    assert [tuple(r) for r in rows] == [("one", None), ("two", None)]


@pytest.mark.db
def test_a_gap_in_the_log_raises_instead_of_being_skipped(db: Engine) -> None:
    """The log cannot have a gap ({ref}`projections`), and the worker checks
    anyway, because a check that cannot fire is a comment. Measured before this
    test existed: with id 5 deleted by hand at `up_to_id` 4, the worker
    projected 6..10 and set `up_to_id = 10` — the silent loss `ProjectionGap` is
    named after. The gap is forged here with plain SQL; nothing in the append
    path can produce it."""
    storage = PostgresStorage(db)
    append(storage, [_raw(n, "email", NOW) for n in range(1, 11)], recorded_at=NOW)
    failing: ProjectionStore[Connection] = _FailingStore(storage, fail_on_call=3)
    with pytest.raises(RuntimeError, match="injected"):
        catch_up(storage, failing, CHRONICLE, batch_size=2)
    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 5"))
        c.execute(text("DELETE FROM unit WHERE event_id = 5"))
        c.execute(text("DELETE FROM event WHERE id = 5"))

    with pytest.raises(ProjectionGap, match="above id 4"):
        catch_up(storage, storage, CHRONICLE, batch_size=2)

    with db.begin() as c:
        highest = c.execute(text("SELECT max(event_id) FROM p_chronicle")).scalar_one()
        rows = c.execute(text("SELECT count(*) FROM p_chronicle")).scalar_one()
    state = _state(storage, "chronicle")
    assert state is not None
    assert (state.up_to_id, highest, rows) == (4, 4, 8)  # nothing moved past the gap


@pytest.mark.db
def test_batch_size_below_one_is_a_caller_error_not_a_gap(db: Engine) -> None:
    """Measured before the guard: `batch_size=0` ran `LIMIT 0` into an empty
    read and reported a gap in the log that was not there; `-1` surfaced a raw
    `DataError` from the driver. A caller error is named as one, before any
    transaction opens."""
    storage = PostgresStorage(db)
    for bad in (0, -1):
        with pytest.raises(ValueError, match="batch_size"):
            catch_up(storage, storage, CHRONICLE, batch_size=bad)


@pytest.mark.db
def test_a_batch_without_any_source_leaves_the_stats_untouched(db: Engine) -> None:
    """The early return in `SourceStatsProjection.write`: a batch in which no
    event carries a source attribution writes nothing — not even an upsert of
    unchanged rows. The sourceless event has to arrive in a batch of its own,
    after a first catch-up, or it shares a batch with a sourced one and the
    return is never reached; that is why the other sourceless test did not
    cover this line."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    _project_all(storage)
    before = _snapshot(db)[1]
    with storage.begin() as c:
        tip = storage.tip(c)
        assert tip is not None
        storage.insert_event(
            c,
            EventRow(2, "observation", NOW, NOW, tip.hash, b"\x02" * 32, b"\x00" * 32, b"\x01" * 32, {}),
            [UnitRow(2, 1, "orphan")],
            None,
        )
    outcome = catch_up(storage, storage, SOURCE_STATS)
    assert outcome.events == 1
    assert _snapshot(db)[1] == before
```

> Die drei letzten Tests kamen in Fixrunde 1 dazu (Prüfbefunde F1, F2 und
> das Bedenken 4 des Umsetzers). Gegen den alten Code war der Lückentest
> **rot mit `DID NOT RAISE`** — und eine Wegwerfsonde ohne die Erwartung zeigte,
> was der alte Arbeiter stattdessen tat: 6..10 projiziert, `up_to_id = 10`.
> Das ist die Messung, die den Test rechtfertigt. `EventRow` und `UnitRow`
> gehören dafür an den Dateikopf.

Die Reihenfolge der Spalten in `_snapshot` ist die der Tabelle: `p_chronicle` hat `source` an Position 6 (0-basiert), `p_source_stats` hat `events` an 1 und `first_seen` an 3. Wer die Tabelle ändert, ändert die Indizes hier mit — darum stehen die Kommentare daneben.

- [ ] **Schritt 3: Laufen lassen — rot**

Run: `uv run pytest tests/test_projection_worker.py -v`
Erwartet: `ImportError` (`catch_up`, `PROJECTIONS`).

- [ ] **Schritt 4: Der Arbeiter**

In `src/previously/core/projection/worker.py` nach `Batch` anfügen; Importe oben ergänzen (`from dataclasses import replace`, `from datetime import datetime, UTC` zur Laufzeit, `from previously.contract.rows import ProjectionState`, `from previously.core.errors import ProjectionGap`, `from typing import Protocol`; unter `TYPE_CHECKING` die beiden Protokolle):

```python
class Projection(Protocol):
    """What the worker needs to know about a projection: its name as
    `projection_state` keys it, the version the code declares, and the write
    step. `write` is generic over the connection so that the protocol itself
    is not — a `Projection[Conn]` would be invariant in `Conn`, and a module
    constant could not be both `Projection[Connection]` and anything else.

    `name` and `version` are read-only properties, not attributes: the
    implementations are frozen dataclasses, whose fields pyright treats as
    read-only, and a protocol attribute `name: str` is mutable — the two
    would not match."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> int: ...

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None: ...


@dataclass(frozen=True)
class Outcome:
    """What one `catch_up` did, for the command line to say which path it
    took ({ref}`projections`): a version-triggered rebuild is otherwise
    invisible."""

    name: str
    version: int
    # None: an ordinary catch-up. 0: nothing existed, first build. n > 0: the
    # table was at version n and the code at another, so it was rebuilt.
    rebuilt_from: int | None
    events: int
    up_to_id: int


def catch_up[Conn](
    log: LogStore[Conn],
    store: ProjectionStore[Conn],
    projection: Projection,
    *,
    batch_size: int = 500,
) -> Outcome:
    """Brings one projection up to the tip of the log, in batches.

    **Rows and `up_to_id` move in one transaction or not at all.** An abort in
    the middle leaves a consistent partial projection, and the next run
    continues at `up_to_id + 1` — that is the whole reason `up_to_id` exists.
    One transaction over the whole log would be the opposite of that.

    `batch_size` is 500 for no stronger reason than that `MAX_BATCH` in
    `append` is 500 and one number is easier to keep than two. It is not
    load-bearing; the abort test sets it to 2 on purpose.

    Reading from `up_to_id + 1` skips nothing, because the log has no gaps:
    `id = predecessor.id + 1` and the unique index on `prev_hash` leave no
    room for one ({ref}`hash-chain`). With a sequence this would be the hard
    part — a transaction with id 41 can commit after one with id 42, and a
    worker that has seen 42 loses 41 for good.
    """
    if batch_size < 1:
        # A caller error, named as one. `LIMIT 0` would return an empty read
        # and the loop below would report a gap in the log that is not there.
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")

    rebuilt_from: int | None = None
    with store.begin() as conn:
        state = store.projection_state(conn, projection.name)
        if state is None or state.version != projection.version:
            # `!=` and not `<`: a rolled-back release derives differently from
            # the table it meets, in either direction.
            rebuilt_from = 0 if state is None else state.version
            store.truncate_projection(conn, projection.name)
            state = ProjectionState(projection.name, 0, projection.version, datetime.now(UTC))
            store.set_projection_state(conn, state)

    processed = 0
    while True:
        with store.begin() as conn:
            tip = log.tip(conn)
            if tip is None or tip.id <= state.up_to_id:
                break
            events = tuple(log.read(conn, from_id=state.up_to_id + 1, limit=batch_size))
            ids = [event.id for event in events]
            # The log has no gaps ({ref}`hash-chain`), so the batch has to be
            # exactly the next `len(ids)` identifiers. Checking only "not
            # empty" was measured insufficient on 2026-10-04: with id 5 deleted
            # by hand and `up_to_id` at 4, `read(from_id=5)` returns 6..10, and
            # a worker that only checks for emptiness projects them and sets
            # `up_to_id = 10` — the silent loss this error exists to refuse.
            expected = list(range(state.up_to_id + 1, state.up_to_id + 1 + len(ids)))
            if ids != expected:
                raise ProjectionGap(
                    f"expected events {expected[:1]}.. above id {state.up_to_id}, "
                    f"read {ids[:3]}{'…' if len(ids) > 3 else ''}; the tip is {tip.id}"
                )
            batch = Batch(
                events=events,
                units=log.units_by_event(conn, ids),
                keys=log.source_keys(conn, ids),
            )
            projection.write(store, conn, batch)
            state = replace(state, up_to_id=events[-1].id, built_at=datetime.now(UTC))
            store.set_projection_state(conn, state)
            processed += len(events)

    return Outcome(
        name=projection.name,
        version=projection.version,
        rebuilt_from=rebuilt_from,
        events=processed,
        up_to_id=state.up_to_id,
    )
```

`src/previously/core/projection/__init__.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projections: derived, disposable views over the log ({ref}`projections`)."""

from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.source_stats import SOURCE_STATS
from previously.core.projection.worker import Batch
from previously.core.projection.worker import catch_up
from previously.core.projection.worker import Outcome
from previously.core.projection.worker import Projection


# Every projection the command line catches up, in this order.
PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)

__all__ = ["CHRONICLE", "PROJECTIONS", "SOURCE_STATS", "Batch", "Outcome", "Projection", "catch_up"]
```

`chronicle.py` und `source_stats.py` importieren `Batch` nur unter `TYPE_CHECKING` aus `worker` — kein Zirkel zur Laufzeit.

- [ ] **Schritt 5: Laufen lassen — grün**

Run: `uv run pytest tests/test_projection_worker.py -v`
Erwartet: elf `PASSED` (acht aus der ersten Fassung, drei aus Fixrunde 1).

Run: `uv run pyright`
Erwartet: `0 errors`. Meldet pyright, `_FailingStore` erfülle `ProjectionStore[Connection]` nicht, fehlt eine Methode im Wrapper — **den Wrapper** ergänzen, nicht das Protokoll kürzen.

- [ ] **Schritt 6: Die Eigenschaft**

In `tests/test_projection_worker.py` anfügen (Importe: `from hypothesis import given, settings, HealthCheck`, `from hypothesis import strategies as st`):

```python
SLOW = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

# Steps: each is one to three events from a handful of sources, with
# `occurred_at` drawn at random and therefore out of order — the case that
# tells a minimum from an assignment.
steps = st.lists(
    st.lists(
        st.tuples(
            st.sampled_from(["email", "chat", "cli"]),
            st.datetimes(
                min_value=datetime(2026, 1, 1),
                max_value=datetime(2026, 12, 31),
                timezones=st.just(UTC),
            ),
        ),
        min_size=1,
        max_size=3,
    ),
    min_size=1,
    max_size=6,
)


@pytest.mark.db
@SLOW
@given(steps=steps)
def test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild(
    db: Engine, steps: list[list[tuple[str, datetime]]]
) -> None:
    """Spec §5.3: random interleavings of "append k events" and "catch up",
    against one rebuild at the end."""
    with db.begin() as c:
        c.execute(text("TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event"))
    storage = PostgresStorage(db)
    n = 0
    for step in steps:
        events = []
        for source, moment in step:
            n += 1
            events.append(_raw(n, source, moment))
        append(storage, events, recorded_at=NOW)
        _project_all(storage)
    incremental = _snapshot(db)
    _force_rebuild(storage)
    _project_all(storage)
    assert _snapshot(db) == incremental
```

Das `TRUNCATE` am Anfang ist nötig, weil Hypothesis die Funktion je Beispiel aufruft und das `db`-Fixture nur einmal je Test leert — `test_properties.py` macht es genauso (`HealthCheck.function_scoped_fixture`).

Run: `uv run pytest tests/test_projection_worker.py -k property -v`
Erwartet: `PASSED`, 25 Beispiele.

- [ ] **Schritt 7: `projections.md` um die Abschnitte des Arbeiters**

Nach den zwei Abschnitten aus Aufgabe 2 anfügen:

`## Catching up in batches, and what an abort leaves behind`: die Invariante (Zeilen und `up_to_id` in einer Transaktion); warum nicht eine Transaktion über alles (die 1a-Spec nennt die sehr große Transaktion als Risiko); dass `batch_size` nicht tragend ist; die Messung aus `test_an_abort_leaves_rows_and_up_to_id_in_step` als Block (Stapelgröße 2, zehn Events, Abbruch im dritten → `up_to_id 4`, 8 Zeilen, Folgelauf 6 Events bis 10).

`## Why there are no gaps to worry about`: §4.2 des Specs — `id = predecessor.id + 1`, der Index auf `prev_hash`, und der Kontrast zur Sequenz, bei der ein Arbeiter 41 verliert, wenn er 42 schon gesehen hat. Verweis auf `{ref}`hash-chain``, wo begründet ist, warum es keine Sequenz gibt.

`## The assurance, and the test that can actually fail`: der Kern (Spec §5.1/§5.2). Dass Bauen-Löschen-Neubauen nur Determinismus beweist; dass die Fehlerart der falsche inkrementelle Schritt ist; **das `first_seen`-Beispiel als Codeblock, in der korrigierten Fassung aus dem Spec** — die falsche Fassung ist das **Nie-Nachziehen** (`first_seen` bleibt), grün nach einem Event, grün nach zehn in Reihenfolge, rot beim ersten älteren Nachzügler; **nicht** das Überschreiben, das in Reihenfolge sofort fällt (der datierte Korrekturblock in Spec §5.2 erklärt die Verwechslung); warum die Aggregation prüft, was die Chronik nicht kann; **beide** Mutationen aus Aufgabe 4 Schritt 6 als Messblock (welche Mutation welchen Test fällt, und dass das Paar beide natürlichen Fehler fängt). Und der Versionstest mit seiner Kontrolle.

Run: Doku-Tore. Erwartet: grün.

- [ ] **Schritt 8: Alle sechs Tore, Commit**

Erwartet: `pytest` **223 passed** (211 + 12; die erste Fassung sagte 220 mit neun Tests, Fixrunde 1 brachte drei dazu).

```bash
git add -A
git commit -F - <<'MSG'
feat: catch_up — rows and up_to_id move together, or not at all

The worker reads from `up_to_id + 1` to the tip in batches, one
transaction each, and advances `up_to_id` in the same transaction as the
rows. Measured: batch size 2, ten events, an injected failure in the third
batch leaves `up_to_id` at 4 with eight rows, and the next run closes the
gap with six events. The failing store is a twenty-line wrapper, not a
mock — the protocol's dividend.

A version that differs — not only a lower one — empties the table and
rebuilds; a rolled-back release derives differently in either direction.
Poison a stats row, bump the version, the poison is gone; without the bump
it stays, which is the control.

The test that justifies the stage: incremental equals rebuilt, both
projections, with the third event happening before the second so that
`first_seen` has to come out of the minimum. A Hypothesis property runs
random interleavings of append and catch-up against one final rebuild.

A gap above `up_to_id` raises `ProjectionGap` rather than being skipped;
the log cannot have one, and a worker that moved past one would turn an
impossible state into a silent loss.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 6: Die Kommandos `project`, `chronicle`, `stats`

**Files:**
- Modify: `src/previously/cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/explanation/projections.md`

**Interfaces:**
- Consumes: `PROJECTIONS`, `catch_up`, `Outcome`, `PostgresStorage.{read_chronicle, read_source_stats, projection_state, tip}`, `parse_moment`.
- Produces: drei Unterkommandos; Hilfsfunktionen `_escape(text) -> str`, `_plural(n, noun) -> str`, `_describe(outcome) -> str`; der Dispatch in `main` als Tabelle statt `if`-Kette.

- [ ] **Schritt 1: Die Tests zuerst**

In `tests/test_cli.py` anfügen (das Gerüst ist das der bestehenden `db`-Tests: `db: object`, `isinstance(db, Engine)`, `monkeypatch.setenv("PREVIOUSLY_DSN", …)`, `capsys`):

```python
from previously.cli import escape_field


def test_escape_field_folds_tab_newline_return_and_backslash_into_two_characters_each() -> None:
    """Spec §6.3 plus review focus 3: one unit is one line, and the escaping
    is reversible because the backslash is escaped first."""
    assert escape_field("a\tb\nc\rd\\e") == "a\\tb\\nc\\rd\\\\e"
    assert escape_field("plain") == "plain"


def _setup(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))


def _append(source: str, external_id: str, text: str, occurred_at: str) -> None:
    assert main(["append", "--source", source, "--external-id", external_id, "--text", text, "--occurred-at", occurred_at]) == 0


@pytest.mark.db
def test_project_on_an_empty_log_is_up_to_date_at_zero(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5. Nothing was built, so it does not say `built`."""
    _setup(db, monkeypatch)
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       up to date, up_to_id 0",
        "source-stats    up to date, up_to_id 0",
    ]


@pytest.mark.db
def test_project_says_which_path_it_took(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """First run on a log with events: `built`. Then `caught up`, then
    `up to date`. The first run has to come *after* the first append — a run
    on the empty log already writes the state row, and every later run is an
    ordinary catch-up (found by the plan's pre-flight scan)."""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello\n\nWorld", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    first = capsys.readouterr().out.splitlines()
    assert first == ["chronicle       built: 1 event, up_to_id 1", "source-stats    built: 1 event, up_to_id 1"]

    _append("email", "m2", "Again", "2026-10-02T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    second = capsys.readouterr().out.splitlines()
    assert second == ["chronicle       caught up: 1 event, up_to_id 2", "source-stats    caught up: 1 event, up_to_id 2"]

    assert main(["project"]) == 0
    third = capsys.readouterr().out.splitlines()
    assert third == ["chronicle       up to date, up_to_id 2", "source-stats    up to date, up_to_id 2"]


@pytest.mark.db
def test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec §6.2: time order, not chain order. Event 2 happened before event 1."""
    _setup(db, monkeypatch)
    _append("email", "m1", "late", "2026-10-02T09:00:00Z")
    _append("chat", "c1", "early\ttab", "2026-10-01T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "2\t1\t2026-10-01T09:00:00+00:00\tchat\tc1\tearly\\ttab",
        "1\t1\t2026-10-02T09:00:00+00:00\temail\tm1\tlate",
    ]
    assert err == ""  # up to date: silence


@pytest.mark.db
def test_chronicle_reports_the_lag_on_stderr_and_only_there(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _append("email", "m1", "x", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err.strip() == "projection is 1 event behind; run `previously project`"


@pytest.mark.db
def test_chronicle_window_is_half_open_and_an_empty_window_is_not_truncated(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 1 folded in: `--since` at or after `--until` prints
    nothing, returns 0, and says nothing on stderr."""
    _setup(db, monkeypatch)
    for n, day in enumerate(("01", "02", "03"), start=1):
        _append("email", f"m{n}", f"day {day}", f"2026-10-{day}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle", "--since", "2026-10-01T09:00:00Z", "--until", "2026-10-03T09:00:00Z"]) == 0
    out, err = capsys.readouterr()
    assert [line.split("\t")[-1] for line in out.splitlines()] == ["day 01", "day 02"]
    assert err == ""
    assert main(["chronicle", "--since", "2026-10-05T00:00:00Z", "--until", "2026-10-01T00:00:00Z"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "")


@pytest.mark.db
def test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    for n in range(1, 4):
        _append("email", f"m{n}", f"u{n}", f"2026-10-0{n}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle", "--limit", "2"]) == 0
    out, err = capsys.readouterr()
    assert len(out.splitlines()) == 2
    assert err.strip() == "output truncated at 2 lines; raise --limit or narrow --since/--until"
    assert main(["chronicle", "--limit", "3"]) == 0
    out, err = capsys.readouterr()
    assert (len(out.splitlines()), err) == (3, "")


@pytest.mark.db
def test_chronicle_rejects_a_naive_since(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 2: the same `parse_moment` as `--occurred-at`."""
    _setup(db, monkeypatch)
    assert main(["chronicle", "--since", "2026-10-01T09:00:00"]) == 2
    assert "time zone" in capsys.readouterr().err


@pytest.mark.db
def test_stats_prints_one_line_per_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _append("email", "m1", "a\n\nb", "2026-10-02T09:00:00Z")
    _append("email", "m2", "c", "2026-10-01T09:00:00Z")
    _append("chat", "c1", "d", "2026-10-03T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["stats"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "chat\t1\t1\t2026-10-03T09:00:00+00:00\t2026-10-03T09:00:00+00:00",
        "email\t2\t3\t2026-10-01T09:00:00+00:00\t2026-10-02T09:00:00+00:00",
    ]
    assert err == ""
```

Die Funktion heißt `escape_field` und nicht `_escape`, weil `CLAUDE.md` es so verlangt: wer eine Funktion direkt testet, gibt ihr einen öffentlichen Namen statt `reportPrivateUsage` zu unterdrücken. Und kein `# noqa` an den Import — `PL`-Regeln sind in `pyproject.toml` nicht ausgewählt, ein `noqa` dafür wäre `RUF100`.

- [ ] **Schritt 2: Laufen lassen — rot**

Run: `uv run pytest tests/test_cli.py -v -k "escape or project or chronicle or stats"`
Erwartet: `ImportError` für `escape_field`; die anderen `argparse`-Fehler (unbekanntes Kommando → `SystemExit 2`).

- [ ] **Schritt 3: Die Kommandos**

In `src/previously/cli.py`: Importe ergänzen —

```python
from previously.core.projection import catch_up
from previously.core.projection import Outcome
from previously.core.projection import PROJECTIONS
```

Hilfsfunktionen nach `_parse_evidence`:

```python
def escape_field(text: str) -> str:
    """One unit is one line of `chronicle` ({ref}`projections`), so tab,
    newline, carriage return and the backslash itself come out as two
    characters each. Backslash first, or the other escapes would be escaped
    again and the mapping would stop being reversible. Output format, not
    data: `p_chronicle` holds the content unchanged."""
    return (
        text.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _describe(outcome: Outcome) -> str:
    """Which path the worker took — a version-triggered rebuild is otherwise
    invisible ({ref}`projections`).

    Order matters. A version change is reported even when it processed no
    event, because it changed the state row. A first run over an empty log
    says `up to date`, not `built: 0 events`: nothing was built, and the
    spec's reading of `up_to_id 0` is "nothing yet".
    """
    tail = f"{_plural(outcome.events, 'event')}, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from:  # a version the table was at before: 1, 2, …
        return f"rebuilt: version {outcome.rebuilt_from} -> {outcome.version}, {tail}"
    if outcome.events == 0:
        return f"up to date, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from == 0:
        return f"built: {tail}"
    return f"caught up: {tail}"


def _report_lag(storage: PostgresStorage, conn: object, name: str) -> None:
    """`tip.id` and `up_to_id` of the projection being read, in the caller's
    transaction — two snapshots would give a difference that never existed.
    Silence means current."""
    from sqlalchemy import Connection

    assert isinstance(conn, Connection)
    tip = storage.tip(conn)
    state = storage.projection_state(conn, name)
    tip_id = 0 if tip is None else tip.id
    up_to = 0 if state is None else state.up_to_id
    lag = tip_id - up_to
    if lag > 0:
        print(f"projection is {_plural(lag, 'event')} behind; run `previously project`", file=sys.stderr)
```

**Halt — `_report_lag` so nicht.** `cli` darf SQLAlchemy nicht kennen (ruling T9-a, und `cli` steht über `storage` nur für `from_dsn`/`PostgresStorage`). Der `isinstance`-Umweg ist ein Geruch. Richtig: die Signatur nimmt `conn: Connection` **nicht** an, sondern die Funktion öffnet keine eigene Transaktion und bekommt die Werte übergeben:

```python
def _lag_line(tip_id: int, up_to_id: int) -> str | None:
    lag = tip_id - up_to_id
    if lag <= 0:
        return None
    return f"projection is {_plural(lag, 'event')} behind; run `previously project`"
```

und die Kommandos lesen `tip` und `state` selbst innerhalb ihrer Transaktion. So:

```python
def _cmd_project(_args: argparse.Namespace) -> int:
    storage = _storage()
    for projection in PROJECTIONS:
        outcome = catch_up(storage, storage, projection)
        print(f"{outcome.name:<15} {_describe(outcome)}")
    return 0


def _cmd_chronicle(args: argparse.Namespace) -> int:
    since = parse_moment(args.since) if args.since else None
    until = parse_moment(args.until) if args.until else None
    storage = _storage()
    with storage.begin() as conn:
        tip = storage.tip(conn)
        state = storage.projection_state(conn, "chronicle")
        # One more than the limit: if it comes back, the window was cut.
        rows = storage.read_chronicle(conn, since=since, until=until, limit=args.limit + 1)
    for row in rows[: args.limit]:
        print(
            f"{row.event_id}\t{row.seq}\t{row.occurred_at.isoformat()}\t"
            f"{row.source or ''}\t{row.external_id or ''}\t{escape_field(row.content)}"
        )
    if len(rows) > args.limit:
        print(
            f"output truncated at {args.limit} lines; raise --limit or narrow --since/--until",
            file=sys.stderr,
        )
    lag = _lag_line(0 if tip is None else tip.id, 0 if state is None else state.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0


def _cmd_stats(_args: argparse.Namespace) -> int:
    storage = _storage()
    with storage.begin() as conn:
        tip = storage.tip(conn)
        state = storage.projection_state(conn, "source-stats")
        rows = storage.read_source_stats(conn)
    for row in rows:
        print(
            f"{row.source}\t{row.events}\t{row.units}\t"
            f"{row.first_seen.isoformat()}\t{row.last_seen.isoformat()}"
        )
    lag = _lag_line(0 if tip is None else tip.id, 0 if state is None else state.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0
```

`_cmd_verify()` bekommt einen Parameter `_args: argparse.Namespace`, damit alle Kommandofunktionen dieselbe Signatur haben. Der Unterstrich ist kein `noqa`: ruff hat `ARG` nicht aktiv, und pyright strict meldet unbenutzte Parameter nicht.

In `main`, die Parser:

```python
    sub.add_parser("project", help="bring the projections up to the tip of the log")

    p_chronicle = sub.add_parser("chronicle", help="print the chronicle in time order")
    p_chronicle.add_argument("--since", help="ISO 8601 with a zone, inclusive")
    p_chronicle.add_argument("--until", help="ISO 8601 with a zone, exclusive")
    p_chronicle.add_argument("--limit", type=int, default=50)

    sub.add_parser("stats", help="print the per-source statistics")
```

Der Dispatch — **Tabelle statt `if`-Kette**, und der Grund steht schon in der Datei: `main` hat `C901` einmal gerissen (13 gegen 10). Sieben `if` plus `try/except` säßen genau auf der Schwelle.

```python
    commands: dict[str, Callable[[argparse.Namespace], int]] = {
        "append": _cmd_append,
        "log": _cmd_log,
        "verify": _cmd_verify,
        "show": _cmd_show,
        "project": _cmd_project,
        "chronicle": _cmd_chronicle,
        "stats": _cmd_stats,
    }
    try:
        return commands[args.command](args)
    except (PreviouslyError, StorageError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
```

`from collections.abc import Callable` unter `TYPE_CHECKING`. Der Kommentar „One branch per command instead of all four command bodies in one function" wird: eine Tabelle statt einer `if`-Kette, mit der `C901`-Geschichte als Grund. Der `return 2  # pragma: no cover` am Ende entfällt — `commands[args.command]` wirft `KeyError` nur, wenn argparse versagt hat, und das kann es mit `required=True` nicht.

- [ ] **Schritt 4: Laufen lassen — grün**

Run: `uv run pytest tests/test_cli.py -v`
Erwartet: alle `PASSED`, inklusive der bestehenden.

Run: `uv run ruff check .`
Erwartet: `All checks passed!` — insbesondere kein `C901` auf `main`.

- [ ] **Schritt 5: `cli.md`**

Die Exit-Code-Tabelle um drei Zeilen (`project`: 0 nachgezogen / 1 nicht benutzt / 2 Storage-Fehler; `chronicle` und `stats`: 0 gedruckt / 1 nicht benutzt / 2 ungültige Eingabe oder Storage-Fehler). Drei Abschnitte nach dem Muster von `## log`: Argumenttabelle, dann Ausgabeformat **als Tatsache**:

- `project`: „Prints one line per projection: the name padded to 15 characters, a space, and the outcome — `built: …`, `caught up: …`, `rebuilt: version N -> M, …` or `up to date, …`, each ending in `up_to_id <id>`."
- `chronicle`: die sechs Felder in Reihenfolge; die Ordnung `(occurred_at, event_id, seq)`; `--since` einschließlich, `--until` ausschließlich; die Entschärfung (vier Zeichen, je zwei Ausgabezeichen, Rückstrich zuerst); Rückstand und Kappung auf `stderr`, Rückgabecode 0.
- `stats`: fünf Felder, sortiert nach `source`; Rückstand auf `stderr`.

Ein Verweis für das Warum: „{ref}`projections` explains why `log` and `chronicle` are two commands."

- [ ] **Schritt 6: `projections.md` um `## Two orders, two commands`**

Spec §6.2 wörtlich sinngemäß: `occurred_at` läuft nicht parallel zu `id`; die Mail von letzter Woche; `log` ist Kettenordnung, `chronicle` ist Chronologie; das sind die zwei Zeitordnungen aus §4.1 der Architektur. Dazu `## Saying what it doesn't know`: Rückstand und Kappung auf `stderr`, Schweigen heißt aktuell, derselbe Gedanke zweimal.

Run: Doku-Tore. Erwartet: grün.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **232 passed** (223 + 9).

```bash
git add -A
git commit -F - <<'MSG'
feat: project, chronicle and stats

`project` catches every projection up and says which path it took — a
version-triggered rebuild would otherwise be invisible. `chronicle` is the
chronology, ordered by (occurred_at, event_id, seq) with a half-open
--since/--until window; `log` stays the chain order. Two orders, two
commands, which is what architecture §4.1 asked for.

One unit is one line: tab, newline, carriage return and backslash come out
as two characters each, backslash first so the mapping stays reversible.
Lag and truncation go to stderr, where no consumer reads them as a record,
and silence means current. The lag is tip against the up_to_id of the
projection being read, both in one transaction.

The dispatch in main is a table: seven branches plus the except would have
sat on the C901 threshold this function has already crossed once.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 7: How-to, README, der Tilgungsfund, Vokabular

**Files:**
- Create: `docs/how-to/rebuild-a-projection.md`
- Modify: `docs/how-to/index.md`, `docs/explanation/projections.md`, `README.md`, `.vale-styles/config/vocabularies/Previously/accept.txt`

- [ ] **Schritt 1: Das How-to**

`docs/how-to/rebuild-a-projection.md`, Label `(rebuild-a-projection)=`, Titel `# Rebuild a projection`. How-to-Ton: „This guide shows you how to …", Handlung ohne Erklärung, Verweise statt Begründung. Drei Abschnitte:

- `## Check how far behind a projection is`: `previously chronicle` oder `stats` laufen lassen; eine Zeile auf `stderr` nennt den Rückstand; Schweigen heißt aktuell. Dann `previously project`.
- `## Force a rebuild after a change to the derivation`: die `version` der Projektion im Code erhöhen (`ChronicleProjection.version` beziehungsweise `SourceStatsProjection.version`), `previously project`, Ausgabe `rebuilt: version N -> M`. Dass die Tabellenstruktur davon unberührt bleibt und eine Strukturänderung eine Migration ist — ein Satz, Verweis auf `{ref}`add-a-migration``.
- `## Force a rebuild without a code change`: `DELETE FROM projection_state WHERE name = 'chronicle'` in `psql`, dann `previously project` → `built: …`. Mit `:::{warning}`: bis zum nächsten `project` ist die Chronik leer, und jedes Lesekommando sagt das auf `stderr`.

Toctree in `docs/how-to/index.md` ergänzen. Verweis am Ende: „For why a rebuild yields the same rows as the incremental path, see {ref}`projections`."

- [ ] **Schritt 2: `projections.md` abschließen**

`## What a chronicle per unit teaches about erasure`: der Fund aus Spec §1.1 — eine Tilgung setzt `payload` auf `NULL`, die Einheiten bleiben, die Chronik zeigt den Inhalt weiter; was das für ein künftiges Tilgungs-Event heißt (Einheiten mittilgen oder den Inhalt nicht getilgt haben); dass `p_source_stats.units` dann ohne Neubau falsch wird; dass `test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` das heutige Verhalten festnagelt. Verweis `{ref}`tombstone-seam``.

Dann die Seite als Ganzes lesen: ein Quadrant (Explanation — kein „do this", keine Faktentabelle, die in die Reference gehört), ein Satz pro Zeile, Überschriften in Satzschreibung ohne Akronyme, höchstens zwei Admonitions. Jede Zahl darin (`0.715`? nein — hier: Stapelgröße 2, zehn Events, `up_to_id 4`, 8 Zeilen, 25 Beispiele) gegen die Tests **abgelesen**.

- [ ] **Schritt 3: README**

Abschnitt `## State`: „Stage 1a is built and runs" → „Stages 1a and 1b are built and run". In **What it does** drei Punkte: Projektionen, die aus dem Log ableitbar und wegwerfbar sind, mit `projection_state` und Versionsneubau; die Chronik je Einheit mit Quellenangabe, in Zeitordnung; die Quellenstatistik. In **What it does not do**: „no projections (header, chronicle as a view — stage 1b)" streichen und stattdessen: kein Kopf — der braucht Feststellungen aus dem Gate; keine Zuordnung zu Projekten, also ist die Chronik die des ganzen Logs; keine Warteschlange, der Arbeiter ist ein Kommando. Die vier Kommandos → „the seven commands `append`, `log`, `verify`, `show`, `project`, `chronicle` and `stats`".

- [ ] **Schritt 4: Vokabular messen**

Run: `make -C docs vale`
Erwartet entweder `0 errors`, oder Treffer auf Wörter wie `upsert`, `denormalization`, `catch-up`. **Je Wort einzeln** in `.vale-styles/config/vocabularies/Previously/accept.txt` anfügen und erneut messen (12 → 10 → 7 → 4 war das Muster am 2026-10-03). Kleingeschriebene Einträge dürfen danach keinen Satz beginnen — die Zahl im `.vale.ini`-Kommentar („Eleven of the fifteen entries are lowercase") **nachzählen** und anpassen: `awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt | wc -l` gegen `wc -l`.

- [ ] **Schritt 5: Alle sechs Tore, Commit**

Erwartet: `pytest` **232 passed** (unverändert), Vale **22 files**.

```bash
git add -A
git commit -F - <<'MSG'
docs: rebuild a projection, what a chronicle teaches about erasure, README

The how-to covers the three things an operator does: read the lag, bump a
version, clear a state row. The explanation page gets its last section —
that a tombstone which empties the payload leaves the units in the
chronicle, which no earlier document said, and what that demands of the
erasure event to come. The README says what stage 1b runs and what it
still does not: no header, because that needs assertions.

Vocabulary extended one word at a time, each measured against `make vale`;
the lowercase count in `.vale.ini` recounted, not carried forward.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 8: Einfrieren, Design-Records, Tutorial zuletzt

**Files:**
- Modify: `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, `docs/explanation/design-records.md`, `docs/tutorials/record-your-first-event.md`

- [ ] **Schritt 1: Der Spec friert ein**

Oben in den Spec, unter dem Titel, der Kopf — Wortlaut wie bei den drei anderen (aus `2026-10-02-stufe-1a-log.md` kopieren und das Datum setzen):

```markdown
> **Eingefrorener Entwurfsbericht, Stand <Datum des Commits>.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in der Dokumentation unter
> `docs/` — soweit sie dort steht; wo sie fehlt, ist dieses Dokument die
> einzige Quelle. Weicht es von der Doku ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen. Das Einfrieren als **Ablauf**, und die
> Karte von jedem zitierten Paragraphen zu seiner Seite, stehen in
> [About the frozen design records](../../explanation/design-records.md).
```

„Status: Entwurf, zur Abnahme" → „Status: eingefroren". Der Absatz unter dem Titel („Dieser Spec entsteht auf Deutsch … Bis dahin ist er das maßgebliche Dokument") wird gestrichen — der Kopf sagt es.

**§10 „Was offen bleibt"** wandert nicht mit dem Spec in die Vergangenheit: der Abschnitt bekommt einen Satz, dass er mit dem Einfrieren seine Pflege verliert und seine Punkte in den Spec der nächsten Stufe gehören — und dass der äußere Anker darunter ist.

- [ ] **Schritt 2: `design-records.md`**

Den 1b-Spec in die Liste der eingefrorenen Berichte aufnehmen (Datum, Thema, welche Seiten seine Begründung tragen: `projections`, `module-boundaries`). In der Abbildungstabelle: 1b-Code zitiert **keine** Paragraphen des 1b-Specs — er zitiert `{ref}`-Label von Anfang an, weil `test_no_bare_paragraph_references_remain` ein nacktes `§` nicht durchlässt. Das ist einen Satz wert: die erste Stufe, deren Code nie auf den Spec zeigte, weil die Seiten mit dem Code entstanden.

Run: `grep -rn "§" src/previously/core/projection src/previously/contract/store.py src/previously/contract/rows.py`
Erwartet: nur Verweise auf die **Architektur** mit `(frozen design record)` — keiner auf den 1b-Spec. Zahl in den Bericht.

- [ ] **Schritt 3: Das Tutorial, als Letztes**

Nach dem Abschnitt `## Look at the event in full` drei neue Abschnitte, **als echter abgetippter Lauf** gegen den Container aus dem Tutorial:

`## Build the derived views` — `uv run previously project`, Ausgabe zwei Zeilen `built: 1 event, up_to_id 1`. „Notice that both say `built`: nothing existed, so the worker built from scratch. Run it again and both say `up to date`."

`## Read the chronicle` — `uv run previously chronicle`, zwei Zeilen (zwei Einheiten). „Notice that each line is one unit, and each carries `email` and the message identifier — the source attribution, which is what makes this a chronicle and not a copy of `log`."

`## Count per source` — `uv run previously stats`, eine Zeile.

Dann den Testlauf **neu abtippen** — die Zahl ist jetzt 232 und `test_docs_typed_output.py` hält sie gegen den Baum. **Ohne** die `rootdir:`-Zeile (die Seite sagt am Ende des Blocks, dass sie ausgelassen ist). Kein Maschinenpfad.

Run: `uv run pytest tests/test_docs_typed_output.py -v`
Erwartet: `PASSED`.

- [ ] **Schritt 4: Alle sechs Tore, Commit**

```bash
git add -A
git commit -F - <<'MSG'
docs: freeze the stage 1b specification, and type out the new commands

The spec gets the dated header the three before it carry: its explanation
pages stand, so from here the pages are the authority and the spec is
provenance. Its open points keep the external anchor at the top and move
to the next stage's spec by rule.

`design-records.md` lists it, and notes the one thing new about it: no
line of stage 1b code cites a paragraph of this spec, because the pages
were written alongside the code and the gate refuses a bare paragraph
sign. The tutorial gains project, chronicle and stats as a typed run, and
the test run is retyped last at 232.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** §1 Lieferungen → Aufgaben 1 (Protokoll), 2+3+5 (Maschinerie), 4+5 (zwei Projektionen), 6 (Kommandos). §1.1 Korrekturen → Aufgabe 1 (zwei Protokolle, Kommentar in `.importlinter`), 5 (Arbeiter als Kommando, kein `job`), 5+7 (Tilgungsfund als Test und Abschnitt), 8 (`show` bleibt, steht in §10). §2 → Aufgabe 1 und 3; die Gegenprobe §2.3 → Aufgabe 1 Schritt 8. §3 → Aufgabe 2 (Tabellen) und 3 (Zeilentypen). §4 → Aufgabe 5, inklusive `!=` (Schritt 4 und Review Focus 4) und `ProjectionGap` für §4.2. §5 → Aufgabe 4 (Mutation auf `merge`) und 5 (alle neun Zusagen aus §5.4 haben einen Test; Entschärfung, Rückstand und Kappung in Aufgabe 6). §6 → Aufgabe 6, mit den Korrekturen 2–4 oben. §7 → Aufgabe 4/5 (Paketstruktur mit vier Dateien statt drei — `worker.py` zusätzlich, um den Importzirkel zu vermeiden; der Spec sagt drei und das ist eine Präzisierung, keine Abweichung). §8 → `database-schema.md` (2), `projections.md` (2, 5, 6, 7), `module-boundaries.md` (1), `cli.md` (6), How-to (7), Tutorial (8), Design-Records (8), Einfrieren (8). §9 Abnahmebedingungen: 1→A1 S6, 2→A1 S8, 3→A5, 4→A5 S6, 5→A5, 6→A5, 7→A5, 8→A3+A6, 9→A6, 10→A6, 11→A5, 12→A4, 13→jede Aufgabe, 14→A8. §10 → Aufgabe 8 Schritt 1.

**Nicht gedeckt und bewusst so:** Spec §2.2 nennt `truncate_projection` mit `name` und die Einfüge-/Aktualisierungsmethoden tabellenspezifisch — gemischte Abstraktionsebene, im Plan so übernommen, weil `core` kein `Table` kennen darf und die Tabellen keine gemeinsame Zeilenform haben.

**2. Platzhalter.** Kein „TBD", kein „analog zu Aufgabe N". Die Doku-Schritte tragen Seitenspezifikationen (Abschnitte mit Muss-Inhalt und Messung) — die Form, die der Doku-Plan vom 2026-10-03 etabliert hat.

**3. Namenskonsistenz.** `escape_field` (nicht `_escape`) in Aufgabe 6 Test und Code — der Test oben zeigt die Falle und löst sie im Text; `Outcome.rebuilt_from` mit den drei Bedeutungen in Aufgabe 5 definiert und in `_describe` (6) genau so gelesen; `ProjectionState(name, up_to_id, version, built_at)` positional in Tests, benannt im Worker — gleiche Reihenfolge wie die Dataclass; `_PROJECTION_TABLES`-Schlüssel `"chronicle"`/`"source-stats"` = `ChronicleProjection.name`/`SourceStatsProjection.name` = `projection_state.name` in den CLI-Reads. Testzahlen je Aufgabe: 193, 194, 202, 211, 223, 232, 232, 232 — jede eine Vorhersage, die der Umsetzer **nachzählt**. (Die erste Fassung dieses Plans sagte 229 für Aufgabe 6, zählte nach und fand acht — dann brachte der Vorab-Scan den Test für das leere Log, und es sind wieder neun; die Zahl im Plan blieb zwei Commits lang bei 228 stehen, bis sie beim Nachführen der Aufgabe-5-Zahlen gegen die `def test_` im Text gezählt wurde. Aufgabe 5 bekam in Fixrunde 1 drei Tests dazu, weil `ProjectionGap` gemessen für keine Lücke feuern konnte. Beides zusammen: 223 und 232.)

**4. Review Focus.** Alle fünf haben einen Test: 1 → A6 (`…empty_window_is_not_truncated`), 2 → A6 (`…rejects_a_naive_since`), 3 → A6 (`escape_field`-Test), 4 → A5 (`…lower_code_version_rebuilds_too`), 5 → A5 (`…empty_log…`) und A6 (`project` auf leerem Log).

**Zwei Warnungen an den Ausführenden.** Erstens: `_FailingStore` in Aufgabe 5 muss **jede** Methode von `ProjectionStore` haben, sonst meldet pyright, und die Versuchung ist, das Protokoll zu kürzen — falsch herum. Zweitens: die Spaltenindizes in `_snapshot`-Assertions (`r[6]`, `stats_row[3]`) sind an die Tabellenreihenfolge gebunden; wer `p_chronicle` eine Spalte voranstellt, bricht die Tests, und das ist gewollt.
