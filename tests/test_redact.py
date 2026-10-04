# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The second write path: erasing an event or units of it ({ref}`erasure`)."""

from datetime import datetime
from datetime import UTC
from itertools import pairwise
from previously.contract.types import Anchor
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import RedactionRefused
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.redact import Redacted
from previously.core.redaction import parse
from previously.core.redaction import read_index
from previously.core.units import split_plaintext
from previously.core.verify import examine
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Connection
from sqlalchemy import Engine
from sqlalchemy import text
from typing import TYPE_CHECKING

import pytest
import threading


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence
    from previously.contract.rows import EventRow


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
    with pytest.raises(RedactionRefused, match="reason is empty"):
        redact_event(nowhere, nowhere, 1, reason="", recorded_at=LATER)
    with pytest.raises(RedactionRefused, match="reason is empty"):
        redact_units(nowhere, nowhere, 1, [1], reason="", recorded_at=LATER)
    with pytest.raises(ValueError, match="at least one seq"):
        redact_units(nowhere, nowhere, 1, [], reason="r", recorded_at=LATER)


@pytest.mark.db
def test_read_index_passes_over_what_it_cannot_read(db: Engine) -> None:
    """`read_index` takes every redaction it can read, the form for a blob
    included, and passes over an action without a valid form and an action
    whose payload is gone: reporting those is `verify`'s business, and the
    findings below are that report. A redaction of a blob names no event, so
    `verify` holds nothing against the log for it."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    blob = "ab" * 32
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
