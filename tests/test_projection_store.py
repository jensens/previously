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
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from previously.contract.store import LogStore
    from previously.contract.store import ProjectionStore


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
def test_read_chronicle_orders_by_time_then_chain_and_filters_a_half_open_window(
    db: Engine,
) -> None:
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


def test_postgres_storage_satisfies_both_protocols() -> None:
    """Static, not dynamic: pyright proves it at the assignment. The function
    exists so the proof has a name a reviewer can point at."""
    from sqlalchemy import Connection
    from sqlalchemy import create_engine

    storage = PostgresStorage(create_engine("postgresql+psycopg://x:y@localhost/z"))
    log: LogStore[Connection] = storage
    projections: ProjectionStore[Connection] = storage
    # The two assignments above are the proof; pyright rejects them if a
    # method is missing. The isinstance checks only give the test a body.
    assert isinstance(log, PostgresStorage)
    assert isinstance(projections, PostgresStorage)
