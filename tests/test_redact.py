# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The second write path: erasing an event or units of it ({ref}`erasure`)."""

from dataclasses import replace
from datetime import datetime
from datetime import UTC
from itertools import pairwise
from previously.contract.types import Anchor
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.append import MAX_RETRIES
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import ChainConflict
from previously.core.errors import RedactionRefused
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.redact import Redacted
from previously.core.redaction import blob_expected
from previously.core.redaction import parse
from previously.core.redaction import read_index
from previously.core.units import split_plaintext
from previously.core.verify import examine
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.storage.errors import ChainPositionTaken
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Connection
from sqlalchemy import Engine
from sqlalchemy import text
from typing import TYPE_CHECKING

import pytest
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Sequence
    from contextlib import AbstractContextManager
    from previously.contract.rows import EventRow
    from previously.contract.rows import Tip
    from previously.contract.rows import UnitRow
    from previously.contract.store import LogStore


NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 4, 13, 0, 0, tzinfo=UTC)
TEXT = "Price remains 1000 Euro.\n\nPlease confirm.\n\nRegards."

# The `write_version_1` fixture from `conftest.py`, under a `type` alias for
# the reason its docstring gives.
type WriteVersion1 = Callable[[PostgresStorage, Sequence[RawEvent], datetime], list[int]]


def _message(external_id: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=split_plaintext(TEXT),
        payload={"text": TEXT},
    )


def _rows(storage: PostgresStorage) -> list[EventRow]:
    with storage.begin() as c:
        return list(storage.read(c, from_id=1, limit=100))


def _unit_state(db: Engine, event_id: int) -> list[tuple[object, ...]]:
    with db.begin() as c:
        return [
            tuple(r)
            for r in c.execute(
                text(
                    "SELECT seq, content IS NULL, salt IS NULL, digest IS NULL FROM unit "
                    "WHERE event_id = :e ORDER BY seq"
                ),
                {"e": event_id},
            )
        ]


@pytest.mark.db
def test_redacting_an_event_writes_an_action_and_leaves_tombstones(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    result = redact_event(storage, storage, 1, reason="sent to the wrong list", recorded_at=LATER)

    assert result == Redacted(redaction_id=2, written=True)
    erased, redaction = _rows(storage)
    assert (erased.payload, erased.payload_salt) == (None, None)
    # seq, content IS NULL, salt IS NULL, digest IS NULL
    assert _unit_state(db, 1) == [
        (1, True, True, False),
        (2, True, True, False),
        (3, True, True, False),
    ]
    assert (redaction.kind, redaction.hash_version) == ("action", 2)
    assert redaction.occurred_at == redaction.recorded_at == LATER
    assert redaction.payload == {
        "action": "redaction",
        "scope": "event",
        "target": {"event": 1, "blobs": []},
        "reason": "sent to the wrong list",
    }
    with storage.begin() as c:
        assert storage.units_by_event(c, [2]) == {}
        assert storage.source_keys(c, [2]) == {}
    assert verify(storage) == []


@pytest.mark.db
def test_the_redaction_of_an_event_names_its_blobs(db: Engine) -> None:
    """Once the payload is erased, the list in the redaction is what attests
    which blobs the event named ({ref}`blobs`). It comes from the register,
    each hash once and ascending; the references are handed in descending
    and one of them twice, so that neither order nor repetition carries
    through by accident."""
    storage = PostgresStorage(db)
    high, low = "f" * 64, "0" * 64
    event = replace(
        _message("m"),
        blobs=(
            BlobRef(sha256=high, size=1, media_type="text/plain", filename="b.txt"),
            BlobRef(sha256=low, size=1, media_type="text/plain", filename="a.txt"),
            BlobRef(sha256=high, size=1, media_type="text/plain", filename="b-copy.txt"),
        ),
    )
    append(storage, [event], recorded_at=NOW)

    redact_event(storage, storage, 1, reason="r", recorded_at=LATER)

    redaction = _rows(storage)[1]
    assert redaction.payload is not None
    assert redaction.payload["target"] == {"event": 1, "blobs": [low, high]}
    assert verify(storage) == []


@pytest.mark.db
def test_redacting_units_leaves_the_others_attested(db: Engine) -> None:
    """The erased unit is skipped by the check on unit digests, and the
    others are still checked: a unit rewritten after the erasure is found."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    result = redact_units(storage, storage, 1, [2], reason="a price", recorded_at=LATER)

    assert result == Redacted(redaction_id=2, written=True)
    assert _unit_state(db, 1) == [
        (1, False, False, False),
        (2, True, True, False),
        (3, False, False, False),
    ]
    assert verify(storage) == []
    with db.begin() as c:
        c.execute(
            text("UPDATE unit SET content = 'Price is 1 Euro.' WHERE event_id = 1 AND seq = 1")
        )
    assert verify(storage) == [Finding(1, "unit 1 does not match its digest")]


class _FailingEraser:
    """The real store, except that erasing units raises — the shape of
    `_FailingStore` in `tests/test_projection_worker.py`."""

    def __init__(self, inner: PostgresStorage) -> None:
        self._inner = inner

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        return self._inner.lock_event(conn, event_id)

    def erase_payload(self, conn: Connection, event_id: int) -> None:
        self._inner.erase_payload(conn, event_id)

    def erase_units(self, conn: Connection, event_id: int, seqs: Sequence[int]) -> None:
        raise RuntimeError("injected failure")


@pytest.mark.db
def test_redaction_and_tombstones_arrive_together_or_not_at_all(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    with pytest.raises(RuntimeError, match="injected"):
        redact_event(storage, _FailingEraser(storage), 1, reason="r", recorded_at=LATER)

    rows = _rows(storage)
    assert [r.id for r in rows] == [1]
    assert rows[0].payload == {"text": TEXT, "evidence": "verbatim"}
    assert rows[0].payload_salt is not None
    assert all(not erased for _, erased, _, _ in _unit_state(db, 1))


@pytest.mark.db
def test_a_second_redaction_of_the_same_event_writes_nothing(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    first = redact_event(storage, storage, 1, reason="r", recorded_at=LATER)

    second = redact_event(storage, storage, 1, reason="again", recorded_at=LATER)

    assert first == Redacted(redaction_id=2, written=True)
    assert second == Redacted(redaction_id=2, written=False)
    assert len(_rows(storage)) == 2
    assert verify(storage) == []


@pytest.mark.db
def test_redacting_units_again_skips_what_is_covered(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    redact_units(storage, storage, 1, [2], reason="r", recorded_at=LATER)

    result = redact_units(storage, storage, 1, [3, 2], reason="more", recorded_at=LATER)

    assert result == Redacted(redaction_id=3, written=True, skipped_units=(2,))
    newest = _rows(storage)[-1]
    assert newest.payload is not None
    assert parse(newest.id, newest.payload).units == (3,)
    assert verify(storage) == []

    again = redact_units(storage, storage, 1, [2, 3], reason="all of it", recorded_at=LATER)
    assert again == Redacted(redaction_id=3, written=False, skipped_units=(2, 3))
    assert len(_rows(storage)) == 3


@pytest.mark.db
def test_redact_units_orders_deduplicates_and_refuses_a_missing_seq(db: Engine) -> None:
    """Review focus 4 of the 2026-10-04 stage 1c plan: a `seq` twice and out
    of order is erased once, and the redaction names it once, in order; a
    `seq` the event does not have is a refusal before anything is written."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    with pytest.raises(RedactionRefused, match=r"^event 1 has no unit 4$"):
        redact_units(storage, storage, 1, [1, 4], reason="r", recorded_at=LATER)
    assert len(_rows(storage)) == 1
    assert all(not erased for _, erased, _, _ in _unit_state(db, 1))

    redact_units(storage, storage, 1, [3, 1, 3], reason="r", recorded_at=LATER)
    newest = _rows(storage)[-1]
    assert newest.payload is not None
    assert newest.payload["target"] == {"event": 1, "units": [1, 3]}
    assert [erased for _, erased, _, _ in _unit_state(db, 1)] == [True, False, True]
    assert verify(storage) == []


@pytest.mark.db
def test_a_redaction_cannot_be_redacted(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    redact_units(storage, storage, 1, [1], reason="r", recorded_at=LATER)

    refusal = r"^event 2 is a redaction, and a redaction cannot be redacted$"
    with pytest.raises(RedactionRefused, match=refusal):
        redact_event(storage, storage, 2, reason="r", recorded_at=LATER)
    with pytest.raises(RedactionRefused, match=refusal):
        redact_units(storage, storage, 2, [1], reason="r", recorded_at=LATER)
    assert len(_rows(storage)) == 2
    assert _rows(storage)[1].payload is not None


@pytest.mark.db
def test_a_missing_event_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    for erase in (
        lambda: redact_event(storage, storage, 7, reason="r", recorded_at=LATER),
        lambda: redact_units(storage, storage, 7, [1], reason="r", recorded_at=LATER),
    ):
        with pytest.raises(RedactionRefused, match=r"^there is no event 7$"):
            erase()
    assert len(_rows(storage)) == 1


@pytest.mark.db
def test_units_of_a_version_1_event_are_refused_and_the_event_is_not(
    db: Engine, write_version_1: WriteVersion1
) -> None:
    """Version 1 attests the units of an event in one digest, so erasing some
    of them would leave the others unattested; erasing all of them leaves
    nothing to attest."""
    storage = PostgresStorage(db)
    write_version_1(storage, [_message("m")], NOW)

    with pytest.raises(RedactionRefused) as refused:
        redact_units(storage, storage, 1, [1], reason="r", recorded_at=LATER)
    assert str(refused.value) == (
        "event 1 was written in hash format 1, which attests its units only together: "
        "use `previously redact event`"
    )
    assert len(_rows(storage)) == 1

    assert redact_event(storage, storage, 1, reason="r", recorded_at=LATER).written
    assert _unit_state(db, 1) == [
        (1, True, True, True),
        (2, True, True, True),
        (3, True, True, True),
    ]
    assert verify(storage) == []


@pytest.mark.db
def test_a_tombstone_without_an_order_gets_one(db: Engine) -> None:
    """Review focus 7 of the 2026-10-04 stage 1c plan: a payload erased by
    hand, without a redaction, is not covered. `redact` writes the order for
    it and erases what still stands, and the redaction carries a later date
    than the tombstone it covers ({ref}`erasure`)."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        # The salt goes with the payload, or `event_payload_salt_check`
        # refuses the statement (ruling P-1 of the 2026-10-04 stage 1c plan).
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"))
    assert verify(storage) == [Finding(1, "payload is erased without a redaction")]

    result = redact_event(storage, storage, 1, reason="found erased", recorded_at=LATER)

    assert result == Redacted(redaction_id=2, written=True)
    assert all(erased for _, erased, _, _ in _unit_state(db, 1))
    assert verify(storage) == []


@pytest.mark.db
def test_a_redaction_racing_an_append_keeps_the_chain(db: Engine) -> None:
    """Review focus 8 of the 2026-10-04 stage 1c plan, in the pattern of
    `test_a_conflict_on_the_chain_position_is_retried` in `test_append.py`:
    both writers read the same tip, one loses the chain position and tries
    again, and both events stand on one chain."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def do_redact() -> None:
        try:
            barrier.wait(timeout=10)
            redact_event(storage, storage, 1, reason="r", recorded_at=LATER)
        except BaseException as e:
            errors.append(e)

    def do_append() -> None:
        try:
            barrier.wait(timeout=10)
            append(storage, [_message("n")], recorded_at=LATER)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=do_redact), threading.Thread(target=do_append)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors
    rows = _rows(storage)
    assert sorted(r.kind for r in rows) == ["action", "observation", "observation"]
    for before, after in pairwise(rows):
        assert after.prev_hash == before.hash
        assert after.id == before.id + 1
    assert verify(storage) == []


class _MeetingEraser:
    """The real store, except that the first `lock_event` waits at a barrier
    until the other thread reaches its own: both erasures then ask for the
    lock at the same moment, and one of them has to wait for the other."""

    def __init__(self, inner: PostgresStorage, barrier: threading.Barrier) -> None:
        self._inner = inner
        self._barrier = barrier
        self._met = False

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        if not self._met:
            self._met = True
            self._barrier.wait(timeout=10)
        return self._inner.lock_event(conn, event_id)

    def erase_payload(self, conn: Connection, event_id: int) -> None:
        self._inner.erase_payload(conn, event_id)

    def erase_units(self, conn: Connection, event_id: int, seqs: Sequence[int]) -> None:
        self._inner.erase_units(conn, event_id, seqs)


@pytest.mark.db
def test_two_redactions_of_one_event_at_once_write_one(db: Engine) -> None:
    """The second erasure waits at the lock on the target and reads the
    redactions only once it holds it, so it sees the first one's and writes
    nothing. Read before the lock, both would see none and both would write."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)

    results: list[Redacted] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def do_redact() -> None:
        try:
            eraser = _MeetingEraser(storage, barrier)
            results.append(redact_event(storage, eraser, 1, reason="r", recorded_at=LATER))
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=do_redact) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors
    assert sorted(r.written for r in results) == [False, True]
    assert {r.redaction_id for r in results} == {2}
    assert [r.kind for r in _rows(storage)] == ["observation", "action"]
    assert verify(storage) == []


@pytest.mark.db
def test_the_anchors_hold_after_every_kind_of_redaction(db: Engine) -> None:
    """Erasure leaves every event hash standing, so an anchor taken before
    still holds, and one taken after holds exactly."""
    storage = PostgresStorage(db)
    append(storage, [_message("m"), _message("n")], recorded_at=NOW)
    before = examine(storage).anchor
    assert before is not None

    redact_event(storage, storage, 1, reason="r", recorded_at=LATER)
    redact_units(storage, storage, 2, [1, 3], reason="r", recorded_at=LATER)

    assert examine(storage, anchors=[before]).findings == ()
    after = examine(storage).anchor
    assert after is not None
    assert after == Anchor(4, _rows(storage)[-1].hash)
    assert examine(storage, anchors=[before, after], exact=True).findings == ()


@pytest.mark.db
def test_what_is_erased_cannot_be_guessed_from_what_stays(db: Engine) -> None:
    """Before the erasure the stored salt reproduces the stored digests from
    the content — the control that the salt is what the digest was computed
    with. After it the digests are the same and the salts are gone, so a
    guess at the content has nothing to be computed with."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    row = _rows(storage)[0]
    with storage.begin() as c:
        unit = storage.units(c, 1)[0]
    assert row.payload is not None and row.payload_salt is not None
    assert payload_hash_v2(row.payload, row.payload_salt) == row.payload_hash
    assert unit.content is not None and unit.salt is not None
    recomputed = unit_digest(
        seq=1, content=unit.content, start_ms=None, end_ms=None, speaker=None, salt=unit.salt
    )
    assert recomputed == unit.digest

    redact_event(storage, storage, 1, reason="r", recorded_at=LATER)

    erased = _rows(storage)[0]
    with storage.begin() as c:
        erased_unit = storage.units(c, 1)[0]
    assert (erased.payload, erased.payload_salt) == (None, None)
    assert erased.payload_hash == row.payload_hash
    assert (erased_unit.content, erased_unit.salt) == (None, None)
    assert erased_unit.digest == unit.digest


def test_an_empty_reason_or_no_unit_is_refused_before_the_store_is_asked() -> None:
    """The form of a redaction demands a reason and, for units, at least one,
    so `redact` refuses either rather than write an action `verify` cannot
    read. The command line cannot send either; a caller in code can. The
    store here points at nothing, and the refusal comes before anything asks
    it."""
    from sqlalchemy import create_engine

    nowhere = PostgresStorage(create_engine("postgresql+psycopg://x:y@localhost:1/z"))
    # Blanks alone are no reason: the reason is the brake on an erasure.
    for reason in ("", " \t\n"):
        with pytest.raises(RedactionRefused, match="reason is empty"):
            redact_event(nowhere, nowhere, 1, reason=reason, recorded_at=LATER)
        with pytest.raises(RedactionRefused, match="reason is empty"):
            redact_units(nowhere, nowhere, 1, [1], reason=reason, recorded_at=LATER)
    with pytest.raises(RedactionRefused, match=r"^a redaction of units needs at least one unit$"):
        redact_units(nowhere, nowhere, 1, [], reason="r", recorded_at=LATER)


@pytest.mark.db
def test_read_index_passes_over_what_it_cannot_read(db: Engine) -> None:
    """`read_index` takes every redaction it can read, the form for a blob
    included, and passes over an action without a valid form and an action
    whose payload is gone: reporting those is `verify`'s business, and the
    findings below are that report. The redaction of a blob names an event
    that uses the blob, so `verify` finds nothing against it."""
    storage = PostgresStorage(db)
    blob = "ab" * 32
    append(storage, [_attached("m", blob)], recorded_at=NOW)
    for payload in (
        {"action": "redaction", "scope": "blob", "target": {"blob": blob, "events": [1]},
         "reason": "r"},
        {"note": "no name"},
        {"action": "something", "of": "another kind"},
        {"action": "redaction", "scope": "units", "target": {"event": 1, "units": [1]},
         "reason": "r"},
    ):  # fmt: skip
        prepared = prepare(kind="action", occurred_at=LATER, payload=payload, units=(), key=None)
        with storage.begin() as c:
            tip = storage.tip(c)
            assert tip is not None
            row, _ = link(prepared, event_id=tip.id + 1, prev_hash=tip.hash, recorded_at=LATER)
            storage.insert_event(c, row, [], None)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 5"))

    with storage.begin() as c:
        index = read_index(storage, c)
    assert [(r.id, r.scope, r.blob) for r in index] == [(2, "blob", blob)]
    assert verify(storage) == [
        Finding(3, "action has no valid form"),
        Finding(5, "payload is erased without a redaction"),
    ]


class _ContestedLog:
    """The real store, except that `insert_event` raises `ChainPositionTaken`
    for its first `losses` calls, or for every call when `losses` is `None` —
    a lost chain position on demand, in the shape of `_FailingStore` in
    `tests/test_projection_worker.py`. The waits between the attempts are the
    real backoff, at most 0.715 s in all over eight attempts."""

    def __init__(self, inner: PostgresStorage, losses: int | None) -> None:
        self._inner = inner
        self._losses = losses
        self.inserts = 0

    def begin(self) -> AbstractContextManager[Connection]:
        return self._inner.begin()

    def snapshot(self) -> AbstractContextManager[Connection]:
        return self._inner.snapshot()

    def tip(self, conn: Connection) -> Tip | None:
        return self._inner.tip(conn)

    def lookup(self, conn: Connection, source: str, external_id: str) -> int | None:
        return self._inner.lookup(conn, source, external_id)

    def insert_event(
        self,
        conn: Connection,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
        blobs: Sequence[bytes] = (),
    ) -> None:
        self.inserts += 1
        if self._losses is None or self.inserts <= self._losses:
            raise ChainPositionTaken("event_prev_hash_idx")
        self._inner.insert_event(conn, row, units, key, blobs)

    def read(self, conn: Connection, from_id: int, limit: int) -> Iterator[EventRow]:
        return self._inner.read(conn, from_id, limit)

    def units_by_event(
        self, conn: Connection, event_ids: Sequence[int]
    ) -> dict[int, list[UnitRow]]:
        return self._inner.units_by_event(conn, event_ids)

    def count_events(self, conn: Connection) -> int:
        return self._inner.count_events(conn)

    def source_keys(self, conn: Connection, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]:
        return self._inner.source_keys(conn, event_ids)

    def read_by_kind(self, conn: Connection, kind: str) -> Iterator[EventRow]:
        return self._inner.read_by_kind(conn, kind)

    def blobs_by_event(self, conn: Connection, event_ids: Sequence[int]) -> dict[int, list[bytes]]:
        return self._inner.blobs_by_event(conn, event_ids)

    def events_by_blob(self, conn: Connection, sha256: bytes) -> list[int]:
        return self._inner.events_by_blob(conn, sha256)

    def blob_references(self, conn: Connection) -> Iterator[tuple[bytes, int]]:
        return self._inner.blob_references(conn)


@pytest.mark.db
def test_a_lost_chain_position_is_retried_and_leaves_nothing_behind(db: Engine) -> None:
    """The first attempt loses its chain position at `insert_event`, the
    second gets one: one redaction, the tombstones set, and nothing of the
    first attempt in the log."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    contested = _ContestedLog(storage, losses=1)
    log: LogStore[Connection] = contested

    result = redact_event(log, storage, 1, reason="r", recorded_at=LATER)

    assert result == Redacted(redaction_id=2, written=True)
    assert contested.inserts == 2
    assert [r.kind for r in _rows(storage)] == ["observation", "action"]
    assert all(erased for _, erased, _, _ in _unit_state(db, 1))
    assert verify(storage) == []


@pytest.mark.db
def test_a_chain_position_never_won_ends_in_a_chain_conflict(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    contested = _ContestedLog(storage, losses=None)
    log: LogStore[Connection] = contested

    with pytest.raises(ChainConflict, match=f"after {MAX_RETRIES} attempts"):
        redact_units(log, storage, 1, [1], reason="r", recorded_at=LATER)

    assert contested.inserts == MAX_RETRIES
    rows = _rows(storage)
    assert [r.kind for r in rows] == ["observation"]
    assert rows[0].payload is not None
    assert all(not erased for _, erased, _, _ in _unit_state(db, 1))


@pytest.mark.db
def test_units_of_an_event_in_an_unknown_hash_format_are_refused(db: Engine) -> None:
    """A format nobody knows makes no claim about its units, so the refusal
    does not borrow version 1's sentence for it."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash_version = 3 WHERE id = 1"))

    with pytest.raises(RedactionRefused) as refused:
        redact_units(storage, storage, 1, [1], reason="r", recorded_at=LATER)
    assert str(refused.value) == "event 1 names hash format 3, which is not known"
    assert len(_rows(storage)) == 1


# --- Erasing blobs ({ref}`erasure`) ------------------------------------------
#
# The references below name blobs no store holds: `core` does not delete, it
# says what no longer has to lie, and the command line deletes it.

_OWN = "b" * 64
_SHARED = "5" * 64


def _attached(external_id: str, *addresses: str) -> RawEvent:
    return replace(
        _message(external_id),
        blobs=tuple(
            BlobRef(sha256=address, size=1, media_type="text/plain") for address in addresses
        ),
    )


@pytest.mark.db
def test_redacting_the_only_event_of_a_blob_makes_it_obsolete(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _OWN)], recorded_at=NOW)

    result = redact_event(storage, storage, 1, reason="r", recorded_at=LATER)

    assert result == Redacted(redaction_id=2, written=True, obsolete_blobs=(_OWN,))


@pytest.mark.db
def test_a_shared_blob_is_kept_until_its_last_event_goes(db: Engine) -> None:
    """Erasing one of two events that share a blob leaves the blob, named
    with the event that still uses it; erasing the second lets it go."""
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _SHARED), _attached("n", _SHARED)], recorded_at=NOW)

    first = redact_event(storage, storage, 1, reason="r", recorded_at=LATER)
    assert (first.obsolete_blobs, first.kept_blobs) == ((), {_SHARED: (2,)})

    second = redact_event(storage, storage, 2, reason="r", recorded_at=LATER)
    assert (second.obsolete_blobs, second.kept_blobs) == ((_SHARED,), {})


@pytest.mark.db
def test_redacting_a_blob_names_every_event_that_uses_it(db: Engine) -> None:
    """The redaction carries the form of a blob and names both events; the
    payloads and units of the events stay as they were, the other blob of
    the first event included, and `verify` finds nothing."""
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _SHARED, _OWN), _attached("n", _SHARED)], recorded_at=NOW)
    before = _rows(storage)
    units_before = [_unit_state(db, 1), _unit_state(db, 2)]

    result = redact_blob(storage, storage, _SHARED, reason="r", recorded_at=LATER)

    assert result == Redacted(redaction_id=3, written=True, obsolete_blobs=(_SHARED,))
    *events, redaction = _rows(storage)
    assert redaction.payload == {
        "action": "redaction",
        "scope": "blob",
        "target": {"blob": _SHARED, "events": [1, 2]},
        "reason": "r",
    }
    assert events == before
    assert [_unit_state(db, 1), _unit_state(db, 2)] == units_before
    assert verify(storage) == []


@pytest.mark.db
def test_the_same_content_at_a_new_event_after_a_blob_redaction_is_expected_again(
    db: Engine,
) -> None:
    """The redaction named the events that used the blob when it was
    written, and not the event that comes after it: that reference is not
    erased, so the blob has to lie again. Erasing it again names that event
    alone."""
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _OWN)], recorded_at=NOW)
    redact_blob(storage, storage, _OWN, reason="r", recorded_at=LATER)
    append(storage, [_attached("n", _OWN)], recorded_at=LATER)

    with storage.begin() as c:
        users = storage.events_by_blob(c, bytes.fromhex(_OWN))
        index = read_index(storage, c)
    assert users == [1, 3]
    assert blob_expected(index, _OWN, users)

    again = redact_blob(storage, storage, _OWN, reason="r", recorded_at=LATER)
    assert again == Redacted(redaction_id=4, written=True, obsolete_blobs=(_OWN,))
    payload = _rows(storage)[-1].payload
    assert payload is not None
    assert parse(4, payload).events == (3,)


@pytest.mark.db
def test_a_second_blob_redaction_writes_nothing_and_still_names_the_blob_obsolete(
    db: Engine,
) -> None:
    """What the second call says is what lets it finish a deletion the first
    did not get to: `obsolete_blobs` is computed whether or not anything is
    written."""
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _OWN)], recorded_at=NOW)
    redact_blob(storage, storage, _OWN, reason="r", recorded_at=LATER)

    second = redact_blob(storage, storage, _OWN, reason="r", recorded_at=LATER)

    assert second == Redacted(redaction_id=2, written=False, obsolete_blobs=(_OWN,))
    assert len(_rows(storage)) == 2


@pytest.mark.db
def test_redacting_a_blob_no_event_uses_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _SHARED)], recorded_at=NOW)

    with pytest.raises(RedactionRefused, match=f"^no event uses blob {_OWN}$"):
        redact_blob(storage, storage, _OWN, reason="r", recorded_at=LATER)

    assert len(_rows(storage)) == 1


class _StaleReader(PostgresStorage):
    """The real store, except that it says when it has read the redactions,
    and reads the tip only once `ready` is set: an erasure through it reads
    the redactions at one moment and the tip at a later one."""

    def __init__(self, engine: Engine, ready: threading.Event) -> None:
        super().__init__(engine)
        self.has_read = threading.Event()
        self._ready = ready

    def read_by_kind(self, conn: Connection, kind: str) -> Iterator[EventRow]:
        self.has_read.set()
        return super().read_by_kind(conn, kind)

    def tip(self, conn: Connection) -> Tip | None:
        assert self._ready.wait(timeout=10)
        return super().tip(conn)


class _HoldingEraser:
    """The real store, except that `erase_payload` — after the lock, after
    the redaction is written, before the commit — says it is there and then
    waits until `go_on` says so."""

    def __init__(self, inner: PostgresStorage, go_on: Callable[[], bool]) -> None:
        self._inner = inner
        self._go_on = go_on
        self.holding = threading.Event()

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        return self._inner.lock_event(conn, event_id)

    def erase_payload(self, conn: Connection, event_id: int) -> None:
        self.holding.set()
        deadline = time.monotonic() + 10
        while not self._go_on():
            assert time.monotonic() < deadline, "the other erasure never came"
            time.sleep(0.01)
        self._inner.erase_payload(conn, event_id)

    def erase_units(self, conn: Connection, event_id: int, seqs: Sequence[int]) -> None:
        self._inner.erase_units(conn, event_id, seqs)


def _waiting_on_a_lock(db: Engine) -> bool:
    with db.connect() as c:
        return bool(
            c.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        )


@pytest.mark.db
def test_two_redactions_of_events_sharing_a_blob_let_it_go_however_they_meet(
    db: Engine,
) -> None:
    """Two events share a blob, and their erasures overlap in the one order
    the chain position does not settle: the second reads the redactions
    before the first commits, and the tip after. The first holds its
    transaction open until the second has either read the redactions or is
    waiting on a lock. Each erasure locks every event that uses a blob of its
    target, in ascending order, so the second waits at the lock of the first
    event, reads the redactions once the first has committed, and says the
    blob is obsolete. Locking the target alone, the second would read no
    redaction of the first event, write on the tip after it, and keep the
    blob — and nothing would delete it."""
    storage = PostgresStorage(db)
    append(storage, [_attached("m", _SHARED), _attached("n", _SHARED)], recorded_at=NOW)

    first_done = threading.Event()
    second_log = _StaleReader(db, first_done)
    first_eraser = _HoldingEraser(
        storage, lambda: second_log.has_read.is_set() or _waiting_on_a_lock(db)
    )
    results: dict[int, Redacted] = {}
    errors: list[BaseException] = []

    def first() -> None:
        try:
            results[1] = redact_event(storage, first_eraser, 1, reason="r", recorded_at=LATER)
        except BaseException as e:
            errors.append(e)
        finally:
            first_done.set()

    def second() -> None:
        try:
            assert first_eraser.holding.wait(timeout=10)
            results[2] = redact_event(second_log, storage, 2, reason="r", recorded_at=LATER)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors
    assert (results[1].obsolete_blobs, results[2].obsolete_blobs) == ((), (_SHARED,))
    assert verify(storage) == []
