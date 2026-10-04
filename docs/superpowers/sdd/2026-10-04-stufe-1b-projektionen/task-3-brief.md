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

