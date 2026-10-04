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
```

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
            if not events:
                raise ProjectionGap(
                    f"no event above id {state.up_to_id} although the tip is {tip.id}"
                )
            ids = [event.id for event in events]
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
Erwartet: acht `PASSED`.

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

Erwartet: `pytest` **220 passed** (211 + 9).

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

