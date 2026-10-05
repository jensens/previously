# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import replace
from datetime import datetime
from datetime import UTC
from previously.contract.rows import ChronicleRow
from previously.contract.rows import EventRow
from previously.contract.rows import UnitRow
from previously.storage.errors import ChainPositionTaken
from previously.storage.errors import InvalidDsn
from previously.storage.errors import MigrationPending
from previously.storage.errors import ServerUnreachable
from previously.storage.errors import SourceKeyTaken
from previously.storage.errors import StorageError
from previously.storage.errors import TransactionAborted
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from typing import TYPE_CHECKING

import pytest
import threading


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
def test_version_and_salt_round_trip(db: Engine) -> None:
    """`insert_event` writes `hash_version` out of the row, not through the
    column's default, and `read` gives both new fields back."""
    storage = PostgresStorage(db)
    row = replace(_row(1, None), hash_version=2, payload_salt=b"\x2a" * 32)
    with storage.begin() as c:
        storage.insert_event(c, row, [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        read_back = next(iter(storage.read(c, from_id=1, limit=1)))
    assert read_back.hash_version == 2
    assert read_back.payload_salt == b"\x2a" * 32


@pytest.mark.db
def test_unit_digest_and_salt_round_trip_through_both_readers(db: Engine) -> None:
    storage = PostgresStorage(db)
    unit = UnitRow(1, 1, "a", digest=b"\x3b" * 32, salt=b"\x4c" * 32)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [unit], ("cli", "x1"))
    with storage.begin() as c:
        assert storage.units(c, 1) == [unit]
        assert storage.units_by_event(c, [1]) == {1: [unit]}


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
    and the caller hashes `null` for it ({ref}`hash-chain`)."""
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
def test_a_snapshot_does_not_see_an_append_that_commits_inside_it(db: Engine) -> None:
    """Every statement in `snapshot` sees the same state ({ref}`hash-chain`):
    the chain check reads its batches and then counts, and an append that
    commits in between must not make the two disagree. The append runs on its
    own connection, the way a concurrent writer's does."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.snapshot() as c:
        before = storage.count_events(c)
        with storage.begin() as writer:
            storage.insert_event(writer, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x2"))
        assert storage.count_events(c) == before == 1


@pytest.mark.db
def test_a_transaction_from_begin_sees_an_append_that_commits_inside_it(db: Engine) -> None:
    """The control beside the snapshot test: the same sequence inside `begin`
    counts one more, because READ COMMITTED gives every statement a snapshot
    of its own. Without this, a green snapshot test would only show that no
    append happened, not that the snapshot hid it."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [UnitRow(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        before = storage.count_events(c)
        with storage.begin() as writer:
            storage.insert_event(writer, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x2"))
        assert storage.count_events(c) == before + 1 == 2


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


# --- The blob register ({ref}`blobs`) ---------------------------------------

_BLOB_A = b"\xaa" * 32
_BLOB_B = b"\xbb" * 32
_BLOB_C = b"\xcc" * 32


@pytest.mark.db
def test_blobs_are_registered_with_the_event_and_read_back_by_batch(db: Engine) -> None:
    """The hashes an event is written with come back in one query for the
    batch, grouped by event and ascending. They are handed in descending, so
    a reader that did not order would hand them back that way. Event 3 uses
    no blob and event 4 does not exist: both are absent, as in `units_by_event`.
    """
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [], ("cli", "x1"), [_BLOB_B, _BLOB_A])
        storage.insert_event(c, _row(2, b"\x01" * 32), [], ("cli", "x2"), [_BLOB_C])
        storage.insert_event(c, _row(3, b"\x02" * 32), [], ("cli", "x3"))
    with storage.begin() as c:
        assert storage.blobs_by_event(c, [1, 2, 3, 4]) == {1: [_BLOB_A, _BLOB_B], 2: [_BLOB_C]}


@pytest.mark.db
def test_events_by_blob_lists_every_event_that_uses_it(db: Engine) -> None:
    """Every event that names a blob, ascending, and an empty list for a
    blob no event names."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [], ("cli", "x1"), [_BLOB_A])
        storage.insert_event(c, _row(2, b"\x01" * 32), [], ("cli", "x2"), [_BLOB_B])
        storage.insert_event(c, _row(3, b"\x02" * 32), [], ("cli", "x3"), [_BLOB_B, _BLOB_A])
    with storage.begin() as c:
        assert storage.events_by_blob(c, _BLOB_A) == [1, 3]
        assert storage.events_by_blob(c, _BLOB_B) == [2, 3]
        assert storage.events_by_blob(c, _BLOB_C) == []


@pytest.mark.db
def test_blob_references_come_ordered_by_hash_and_then_by_event(db: Engine) -> None:
    """Every row of the register, by hash and then by event. Written so that
    neither the order of insertion nor the order within an event is the
    order asked for."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _row(1, None), [], ("cli", "x1"), [_BLOB_B])
        storage.insert_event(c, _row(2, b"\x01" * 32), [], ("cli", "x2"), [_BLOB_C, _BLOB_A])
        storage.insert_event(c, _row(3, b"\x02" * 32), [], ("cli", "x3"), [_BLOB_B, _BLOB_A])
    with storage.begin() as c:
        assert list(storage.blob_references(c)) == [
            (_BLOB_A, 2),
            (_BLOB_A, 3),
            (_BLOB_B, 1),
            (_BLOB_B, 3),
            (_BLOB_C, 2),
        ]


@pytest.mark.db
def test_blobs_by_event_with_an_empty_batch(db: Engine) -> None:
    """`IN ()` is not valid SQL — the empty batch returns without a query,
    and the statements the engine sends are counted to show it. The batch of
    one beside it is the control: the count has to see its one statement."""
    from sqlalchemy import event

    sent: list[str] = []

    def count(*args: object) -> None:
        sent.append(str(args[2]))

    storage = PostgresStorage(db)
    with storage.begin() as c:
        event.listen(db, "before_cursor_execute", count)
        try:
            assert storage.blobs_by_event(c, []) == {}
            empty = len(sent)
            assert storage.blobs_by_event(c, [1]) == {}
        finally:
            event.remove(db, "before_cursor_execute", count)
    assert empty == 0
    assert len(sent) == 1


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


# --- RedactionStore ({ref}`erasure`) ------------------------------------------
#
# The two `UPDATE`s on the log, and the row lock in front of them. What a
# tombstone may keep is the database's to enforce (`event_payload_salt_check`
# and `unit_tombstone_check`); these tests hold that the methods ask for no
# more and no less than that.


def _salted(event_id: int, prev: bytes | None) -> EventRow:
    return replace(_row(event_id, prev), hash_version=2, payload_salt=b"\x2a" * 32)


def _unit(event_id: int, seq: int, content: str) -> UnitRow:
    return UnitRow(
        event_id,
        seq,
        content,
        start_ms=seq * 1000,
        end_ms=seq * 1000 + 500,
        speaker="A",
        digest=bytes([seq]) * 32,
        salt=bytes([seq + 16]) * 32,
    )


@pytest.mark.db
def test_lock_event_returns_the_row_or_none(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        assert storage.lock_event(c, 1) == _salted(1, None)
        assert storage.lock_event(c, 2) is None


@pytest.mark.db
def test_lock_event_makes_a_second_locker_wait(db: Engine) -> None:
    """The second connection waits for the first: with a `lock_timeout` it
    gives up while the first holds the row, and gets it once the first has
    committed. A plain read of the same row does not wait, which is the
    control that shows the timeout comes from the lock and not from the
    connection."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as first:
        assert storage.lock_event(first, 1) is not None
        with db.connect() as second:
            second.execute(text("SET lock_timeout = '200ms'"))
            assert [r.id for r in storage.read(second, from_id=1, limit=1)] == [1]
            with pytest.raises(OperationalError, match="lock timeout"):
                storage.lock_event(second, 1)
    with db.connect() as second:
        second.execute(text("SET lock_timeout = '200ms'"))
        assert storage.lock_event(second, 1) is not None


def _chronicle_row(event_id: int) -> ChronicleRow:
    return ChronicleRow(
        event_id=event_id,
        seq=1,
        content="a",
        occurred_at=datetime(2026, 10, 4, 12, 0, tzinfo=UTC),
        kind="observation",
        evidence="recollection",
        source="cli",
        external_id="x1",
        speaker=None,
        start_ms=None,
        end_ms=None,
    )


@pytest.mark.db
def test_lock_event_and_a_foreign_key_check_on_the_event_do_not_wait_for_each_other(
    db: Engine,
) -> None:
    """A catch-up that inserts a chronicle row of an event takes a key-share
    lock on that event's row through the foreign key, and an erasure that
    locks the row must not wait behind it, nor the insert behind the
    erasure. Each direction with a `lock_timeout`, which a wait would run
    into. Measured on 2026-10-05 with `lock_event` at `FOR UPDATE`: both
    directions ran into it. `test_lock_event_makes_a_second_locker_wait` is
    the control: two lockers still wait for each other."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))

    with db.connect() as first:
        storage.insert_chronicle(first, [_chronicle_row(1)])
        with db.connect() as second:
            second.execute(text("SET lock_timeout = '200ms'"))
            assert storage.lock_event(second, 1) is not None
            second.rollback()
        first.rollback()

    with db.connect() as first:
        assert storage.lock_event(first, 1) is not None
        with db.connect() as second:
            second.execute(text("SET lock_timeout = '200ms'"))
            storage.insert_chronicle(second, [_chronicle_row(1)])
            second.rollback()
        first.rollback()


@pytest.mark.db
def test_a_deadlock_becomes_a_storage_error_that_says_to_run_again(db: Engine) -> None:
    """Two transactions lock two rows in opposite order, and PostgreSQL
    aborts one of them. That arrives as an `OperationalError` from inside the
    transaction, and is reported as an aborted operation, not as a server
    that does not answer. Measured on 2026-10-05 with the translation taken
    out: the deadlock came out as `ServerUnreachable`."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))
        storage.insert_event(c, _salted(2, b"\x01" * 32), [], None)
    both_hold_one = threading.Barrier(2)
    errors: list[BaseException] = []

    def lock(first: int, then: int) -> None:
        try:
            with storage.begin() as c:
                assert storage.lock_event(c, first) is not None
                both_hold_one.wait(timeout=10)
                storage.lock_event(c, then)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=lock, args=pair) for pair in ((1, 2), (2, 1))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive(), "thread is hanging"

    (error,) = errors
    assert isinstance(error, TransactionAborted)
    assert str(error) == (
        "the database aborted the operation in a conflict with a concurrent one; "
        "run the command again"
    )


@pytest.mark.db
def test_a_lock_not_granted_in_time_becomes_the_same_storage_error(db: Engine) -> None:
    """`55P03`, a `lock_timeout` run out inside a transaction of `begin`,
    is the same case: the server answered and refused to wait longer."""
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as first:
        assert storage.lock_event(first, 1) is not None
        with pytest.raises(TransactionAborted), storage.begin() as second:
            second.execute(text("SET LOCAL lock_timeout = '200ms'"))
            storage.lock_event(second, 1)


@pytest.mark.db
def test_erase_payload_takes_the_salt_along(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), [_unit(1, 1, "a")], ("cli", "x1"))
    with storage.begin() as c:
        storage.erase_payload(c, 1)
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
    assert (row.payload, row.payload_salt) == (None, None)
    assert row.payload_hash == _salted(1, None).payload_hash
    assert row.hash == _salted(1, None).hash


@pytest.mark.db
def test_erase_units_touches_only_the_named(db: Engine) -> None:
    storage = PostgresStorage(db)
    units = [_unit(1, 1, "a"), _unit(1, 2, "b"), _unit(1, 3, "c")]
    with storage.begin() as c:
        storage.insert_event(c, _salted(1, None), units, ("cli", "x1"))
    with storage.begin() as c:
        storage.erase_units(c, 1, [1, 3])
        storage.erase_units(c, 1, [])
    with storage.begin() as c:
        after = storage.units(c, 1)
    assert after == [
        UnitRow(1, 1, None, digest=units[0].digest),
        units[1],
        UnitRow(1, 3, None, digest=units[2].digest),
    ]


@pytest.mark.db
def test_read_by_kind_yields_only_that_kind_in_chain_order(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.insert_event(c, replace(_row(1, None), kind="action"), [], None)
        storage.insert_event(c, _row(2, b"\x01" * 32), [UnitRow(2, 1, "b")], ("cli", "x2"))
        storage.insert_event(c, replace(_row(3, b"\x02" * 32), kind="action"), [], None)
    with storage.begin() as c:
        assert [r.id for r in storage.read_by_kind(c, "action")] == [1, 3]
        assert [r.id for r in storage.read_by_kind(c, "observation")] == [2]
        assert list(storage.read_by_kind(c, "assertion")) == []
