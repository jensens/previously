# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from datetime import UTC
from previously.storage.errors import ChainPositionTaken
from previously.storage.errors import InvalidDsn
from previously.storage.errors import MigrationPending
from previously.storage.errors import ServerUnreachable
from previously.storage.errors import SourceKeyTaken
from previously.storage.errors import StorageError
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from previously.storage.rows import EventRow
from previously.storage.rows import UnitRow
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from sqlalchemy import Engine

# An unreachable port: nothing listens there, the connection fails at once
# with "connection refused" instead of with a connection timeout — measured
# at under 2 ms, see review finding W2.
_UNREACHABLE_DSN = "postgresql+psycopg://user:SECRET123@localhost:1/db"


def _row(event_id: int, prev: bytes | None) -> EventRow:
    return EventRow(
        id=event_id,
        kind="observation",
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        prev_hash=prev,
        hash=bytes([event_id]) * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x11" * 32,
        payload={"text": f"Event {event_id}"},
    )


@pytest.mark.db
def test_tip_is_empty(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.tip(c) is None


@pytest.mark.db
def test_insert_and_tip(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        tip = storage.tip(c)
    assert tip is not None
    assert tip.id == 1
    assert tip.hash == b"\x01" * 32


@pytest.mark.db
def test_tip_takes_the_highest_id(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x2"))
    with storage.begin() as c:
        tip = storage.tip(c)
    assert tip is not None
    assert tip.id == 2


@pytest.mark.db
def test_lookup(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        assert storage.lookup(c, "cli", "x1") == 1
        assert storage.lookup(c, "cli", "unknown") is None
        assert storage.lookup(c, "imap", "x1") is None


@pytest.mark.db
def test_read_yields_in_id_order(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x2"))
    with storage.begin() as c:
        assert [r.id for r in storage.read(c, from_id=1, limit=10)] == [1, 2]
        assert [r.id for r in storage.read(c, from_id=2, limit=10)] == [2]


@pytest.mark.db
def test_read_gives_an_iterator_not_a_list(db: Engine) -> None:
    """Reprojecting over years of history must materialise nothing."""
    from collections.abc import Iterator

    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert isinstance(storage.read(c, from_id=1, limit=10), Iterator)


@pytest.mark.db
def test_units_are_read_back(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(
            c,
            _row(1, None),
            [UnitRow(1, 1, "first"), UnitRow(1, 2, "second", speaker="A")],
            ("cli", "x1"),
        )
    with storage.begin() as c:
        units = storage.units(c, 1)
    assert [(u.seq, u.content, u.speaker) for u in units] == [
        (1, "first", None),
        (2, "second", "A"),
    ]


@pytest.mark.db
def test_payload_round_trip(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        read_back = next(iter(storage.read(c, from_id=1, limit=1)))
    assert read_back.payload == {"text": "Event 1"}
    assert read_back.prev_hash is None
    assert read_back.recorded_at == datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)


@pytest.mark.db
def test_a_second_genesis_becomes_a_chain_conflict(db: Engine) -> None:
    """event_prev_hash_idx (NULLS NOT DISTINCT): two events with prev_hash=None
    are two genesis entries — the chain may have only one."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with pytest.raises(ChainPositionTaken) as error, storage.begin() as c:
        storage.insert_event(c, _row(2, None), [UnitRow(2, 1, "b")], ("cli", "x2"))
    assert error.value.args == ("event_prev_hash_idx",)


@pytest.mark.db
def test_a_duplicate_id_becomes_a_chain_conflict(db: Engine) -> None:
    """event_pkey: the same id, but a different prev_hash and a different
    hash — otherwise event_prev_hash_idx or event_hash_idx would fire by
    accident instead of the constraint that is meant."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    colliding = EventRow(
        id=1,
        kind="observation",
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        prev_hash=b"\xff" * 32,
        hash=b"\x02" * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x11" * 32,
        payload={"text": "Event 1 again"},
    )
    with pytest.raises(ChainPositionTaken) as error, storage.begin() as c:
        storage.insert_event(c, colliding, [UnitRow(1, 1, "b")], ("cli", "x2"))
    assert error.value.args == ("event_pkey",)


@pytest.mark.db
def test_a_duplicate_source_key_becomes_a_source_conflict(db: Engine) -> None:
    """source_key_pkey: the same (source, external_id) twice for different
    events — idempotency struck in the race."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with pytest.raises(SourceKeyTaken) as error, storage.begin() as c:
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x1"))
    assert error.value.args == ("source_key_pkey",)


@pytest.mark.db
def test_insert_without_units(db: Engine) -> None:
    """units=[] is a branch of its own in insert_event — the skipping branch
    (`if units:`) has no statement of its own and therefore stays undetected
    by statement coverage unless this test exercises it."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [], ("cli", "x1"))
    with storage.begin() as c:
        tip = storage.tip(c)
        units = storage.units(c, 1)
    assert tip is not None
    assert tip.id == 1
    assert units == []


@pytest.mark.db
def test_insert_without_a_source_key(db: Engine) -> None:
    """key=None is the second skipping branch (`if key is not None:`),
    likewise without a statement of its own and therefore undetected without a
    test of its own."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], None)
    with storage.begin() as c:
        tip = storage.tip(c)
        found = storage.lookup(c, "cli", "x1")
    assert tip is not None
    assert tip.id == 1
    assert found is None


@pytest.mark.db
def test_source_keys_reads_by_batch(db: Engine) -> None:
    """One query for the whole batch, and events without a row are absent from
    the return value instead of standing in it as `None`. Event 2 is inserted
    without a key, event 3 does not exist — both cases are the same absence,
    and the caller hashes `null` for it (§3.1 of the 1a spec)."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], None)
    with storage.begin() as c:
        assert storage.source_keys(c, [1, 2, 3]) == {1: ("cli", "x1")}


@pytest.mark.db
def test_count_events_counts_what_read_does_not_see_too(db: Engine) -> None:
    """The counter carries **no** `id` condition — therein lies its whole
    purpose (review finding B1): `read` filters `id >= from_id`, and a row
    below the reading window is supposed to come to notice precisely through
    the difference. Were `count_events` to carry the same condition, it would
    have the same gap."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.count_events(c) == 0
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(0, 'observation', now(), now(), :prev, :h, :p, :u, '{}'::jsonb)"
            ),
            {"prev": b"\x7f" * 32, "h": b"\x7e" * 32, "p": b"\x7d" * 32, "u": b"\x7c" * 32},
        )
    with storage.begin() as c:
        assert storage.count_events(c) == 2
        assert [r.id for r in storage.read(c, from_id=1, limit=10)] == [1]


@pytest.mark.db
def test_source_keys_with_an_empty_batch(db: Engine) -> None:
    """`IN ()` is not valid SQL — the empty batch returns without a query."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.source_keys(c, []) == {}


@pytest.mark.db
def test_units_by_event_groups_and_keeps_the_seq_order(db: Engine) -> None:
    """One query for the whole batch, grouped by `event_id`, every group
    ascending by `seq` (finding N2).

    The `seq` order is the point of this test, not a nicety: it goes into
    `units_hash` and therewith into the event hash. The units are therefore
    **inserted** in descending `seq` here, so that an unordered query would
    hand them back exactly that way and the test would notice. Event 3 is
    inserted without units and event 4 does not exist — both are the same
    absence and are absent from the return value, like in `source_keys`.
    """
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(
            c,
            _row(1, None),
            [UnitRow(1, 2, "one-second"), UnitRow(1, 1, "one-first")],
            ("cli", "x1"),
        )
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "two-first")], ("cli", "x2"))
        storage.insert_event(c, _row(3, b"\x02" * 32), [], ("cli", "x3"))

    with storage.begin() as c:
        grouped = storage.units_by_event(c, [1, 2, 3, 4])

    assert sorted(grouped) == [1, 2]
    assert [(u.seq, u.content) for u in grouped[1]] == [(1, "one-first"), (2, "one-second")]
    assert [(u.seq, u.content) for u in grouped[2]] == [(1, "two-first")]


@pytest.mark.db
def test_units_by_event_with_an_empty_batch(db: Engine) -> None:
    """`IN ()` is not valid SQL — the empty batch returns without a query."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.units_by_event(c, []) == {}


@pytest.mark.db
def test_a_duplicate_hash_becomes_a_chain_conflict(db: Engine) -> None:
    """event_hash_idx is the same incident as event_pkey and
    event_prev_hash_idx, not an independent deterministic error (ruling T6-b
    was wrongly reasoned here — corrected as review finding W2 of task 7, fix
    round 2): `id` and `prev_hash` go into
    `previously.core.hashing.event_hash`, which is why a duplicate `hash` can
    only arise at the same chain position. Two concurrent writers who compute
    the same `id` and the same `prev_hash` out of the same tip therewith
    inevitably compute the same `hash` as well — and must therefore be treated
    the same way as a conflict on `event_pkey` or `event_prev_hash_idx`:
    re-read the tip, retry."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    colliding = EventRow(
        id=2,
        kind="observation",
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        prev_hash=b"\x01" * 32,
        hash=b"\x01" * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x11" * 32,
        payload={"text": "Event 2"},
    )
    with pytest.raises(ChainPositionTaken) as error, storage.begin() as c:
        storage.insert_event(c, colliding, [UnitRow(2, 1, "b")], ("cli", "x2"))
    assert error.value.args == ("event_hash_idx",)


@pytest.mark.db
def test_a_duplicate_hash_and_a_duplicate_id_become_a_chain_conflict_regardless_of_order(
    db: Engine,
) -> None:
    """Independence of order (review finding W2, task 7, fix round 2): this
    INSERT violates event_pkey (same id) and event_hash_idx (same hash) at the
    same time — a different prev_hash is not needed for that, it only shows
    that event_prev_hash_idx does not play along here. Which of the two
    PostgreSQL reports depends on the physical order of the index OIDs, not on
    a decision. That is why this test checks the type of error, not the
    constraint name — both names must lead to the same outcome."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    colliding = EventRow(
        id=1,
        kind="observation",
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        prev_hash=b"\xff" * 32,
        hash=b"\x01" * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x11" * 32,
        payload={"text": "Event 1 again"},
    )
    with pytest.raises(ChainPositionTaken), storage.begin() as c:
        storage.insert_event(c, colliding, [UnitRow(1, 1, "b")], ("cli", "x2"))


@pytest.mark.db
def test_the_check_constraint_is_not_translated(db: Engine) -> None:
    """event_kind_check is a deterministic programming error, not a
    concurrency incident (ruling T6-b): translated as `ChainPositionTaken` the
    caller would retry it pointlessly until its attempts are exhausted and
    report a misleading chain conflict in the end, instead of seeing the
    actual programming error at once. That is why the `IntegrityError` must
    come through unchanged — not as a `StorageError`.
    `pytest.raises(IntegrityError)` alone did already cover a faulty
    translation (the storage errors do not inherit from `IntegrityError`, so a
    `ChainPositionTaken` would break out of the block), but only as an
    unexpected failure, not as an assurance that holds the intention down.
    Denying `StorageError` explicitly turns the side effect into a readable
    property."""
    storage = PostgresStorage(db)
    nonsense = EventRow(
        id=1,
        kind="nonsense",
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        prev_hash=None,
        hash=b"\x01" * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x11" * 32,
        payload={"text": "Event 1"},
    )
    with pytest.raises(IntegrityError) as error, storage.begin() as c:
        storage.insert_event(c, nonsense, [UnitRow(1, 1, "a")], ("cli", "x1"))
    assert not isinstance(error.value, StorageError)


def test_an_unparsable_dsn_becomes_a_storage_error() -> None:
    """Case 1 out of review finding W2: `create_engine` parses the DSN at once
    and raises `ArgumentError` inside `from_dsn` already, before any
    connection attempt."""
    with pytest.raises(InvalidDsn, match="PREVIOUSLY_DSN"):
        from_dsn("not-a-dsn")


def test_an_unparsable_dsn_shows_no_password() -> None:
    """The raw DSN could carry a password — it must therefore not turn up in
    the translated message, not even as an excerpt."""
    with pytest.raises(InvalidDsn) as error:
        from_dsn("not-a-DSN-with-SECRET123")
    assert "SECRET123" not in str(error.value)


def test_an_unreachable_server_becomes_a_storage_error() -> None:
    """Case 2 out of review finding W2: the DSN is valid, but nobody answers."""
    storage = PostgresStorage(create_engine(_UNREACHABLE_DSN))
    with pytest.raises(ServerUnreachable, match="localhost"), storage.begin():
        pass


def test_an_unreachable_server_shows_no_password() -> None:
    storage = PostgresStorage(create_engine(_UNREACHABLE_DSN))
    with pytest.raises(ServerUnreachable) as error, storage.begin():
        pass
    assert "SECRET123" not in str(error.value)


@pytest.mark.db
def test_a_missing_table_becomes_a_storage_error(unmigrated_engine: Engine) -> None:
    """Case 3 out of review finding W2: `log` or `append` run before `alembic
    upgrade head` has created the tables. The exception arises here only
    **inside** the `with` block, at `tip`, not during the connection setup
    itself — exactly the case the long comment at `begin()` describes."""
    storage = PostgresStorage(unmigrated_engine)
    with pytest.raises(MigrationPending, match="alembic upgrade head"), storage.begin() as c:
        storage.tip(c)
