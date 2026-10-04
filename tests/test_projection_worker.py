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
from hypothesis import given
from hypothesis import HealthCheck
from hypothesis import settings
from hypothesis import strategies as st
from previously.contract.rows import ChronicleRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import SourceStatsRow
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
    from previously.contract.store import ProjectionStore

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
        chronicle = [
            tuple(r) for r in c.execute(text("SELECT * FROM p_chronicle ORDER BY event_id, seq"))
        ]
        stats = [tuple(r) for r in c.execute(text("SELECT * FROM p_source_stats ORDER BY source"))]
    return chronicle, stats


def _project_all(storage: PostgresStorage) -> None:
    for projection in PROJECTIONS:
        catch_up(storage, storage, projection)


def _force_rebuild(storage: PostgresStorage) -> None:
    """The path {ref}`projections` names: truncate and `up_to_id = 0`, version
    unchanged — the worker then catches up from scratch."""
    with storage.begin() as c:
        for projection in PROJECTIONS:
            storage.truncate_projection(c, projection.name)
            storage.set_projection_state(
                c, ProjectionState(projection.name, 0, projection.version, NOW)
            )


@pytest.mark.db
def test_incremental_equals_rebuilt(db: Engine) -> None:
    """The central assurance ({ref}`projections`), with the named case folded
    in: event 3 happened before event 2, so `first_seen` for `email` has to
    come out of the minimum and not out of the last write.

    Measured on 2026-10-04, three mutations, and the first two say something
    the specification does not. Replacing
    `first_seen=min(existing.first_seen, addition.first_seen)` in
    `source_stats.merge` by `existing.first_seen` — never catching up — turns
    this test red, but on the pinned value below and **not** on
    `assert incremental == rebuilt`: `merge` folds the batch *and* merges the
    fold with the stored row, so that mutation moves both paths alike and
    they stay equal. Replacing it by `addition.first_seen` — overwriting —
    leaves all nine tests in this file green, for the reason the dated
    correction in the specification gives: the older late arrival happens to
    be the minimum.

    What the comparison catches is a wrong *incremental* step, and that was
    measured too. With `SourceStatsProjection.write` merging `None` instead
    of the stored row, this test and the property fail and all nine tests in
    `test_projection_derive.py` stay green — a mutation invisible to every
    pure test and to the pinned value, which is the whole reason this test
    exists.
    """
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
    """A version bump rebuilds ({ref}`projections`): poison a row, bump the
    version, the poison is gone — and the control: without the bump the
    poison stays."""
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
        version = c.execute(
            text("SELECT version FROM projection_state WHERE name = 'source-stats'")
        ).scalar_one()
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
    """Rows and `up_to_id` move in one transaction or not at all
    ({ref}`projections`). Batch size 2, ten events, failure in the third
    batch: four events are projected and `up_to_id` says four. The next run
    closes the gap."""
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
    """No source, nothing to attribute to ({ref}`projections`). Written
    through `insert_event` with `key=None`, which `append` never does — a
    connector for assertions would."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    from previously.contract.rows import EventRow
    from previously.contract.rows import UnitRow

    with storage.begin() as c:
        tip = storage.tip(c)
        assert tip is not None
        storage.insert_event(
            c,
            EventRow(
                2, "observation", NOW, NOW, tip.hash, b"\x02" * 32, b"\x00" * 32, b"\x01" * 32, {}
            ),
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
    """Erasing the payload does not erase the units ({ref}`projections`).
    Pinned, so that an erasure which deletes units has to change this on
    purpose."""
    storage = PostgresStorage(db)
    append(storage, [_raw(1, "email", NOW)], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))
    catch_up(storage, storage, CHRONICLE)
    with db.begin() as c:
        rows = c.execute(text("SELECT content, evidence FROM p_chronicle ORDER BY seq")).all()
    assert [tuple(r) for r in rows] == [("one", None), ("two", None)]


SLOW = settings(
    max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)

# `st.datetimes` attaches the timezone itself and therefore takes **naive**
# bounds. They are built aware and stripped here rather than built naive with
# a suppression of DTZ001: removing the cause beats suppressing the symptom.
WINDOW_FROM = datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)
WINDOW_UNTIL = datetime(2026, 12, 31, tzinfo=UTC).replace(tzinfo=None)

# Steps: each is one to three events from a handful of sources, with
# `occurred_at` drawn at random and therefore out of order — the case that
# tells a minimum from an assignment.
steps = st.lists(
    st.lists(
        st.tuples(
            st.sampled_from(["email", "chat", "cli"]),
            st.datetimes(
                min_value=WINDOW_FROM,
                max_value=WINDOW_UNTIL,
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
    """Random interleavings of "append k events" and "catch up", against one
    rebuild at the end ({ref}`projections`)."""
    with db.begin() as c:
        c.execute(
            text("TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event")
        )
    storage = PostgresStorage(db)
    n = 0
    for step in steps:
        events: list[RawEvent] = []
        for source, moment in step:
            n += 1
            events.append(_raw(n, source, moment))
        append(storage, events, recorded_at=NOW)
        _project_all(storage)
    incremental = _snapshot(db)
    _force_rebuild(storage)
    _project_all(storage)
    assert _snapshot(db) == incremental
