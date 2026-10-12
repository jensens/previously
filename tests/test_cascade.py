# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The erasure cascade: the result of a `model_call` goes with its input,
and an assertion with its sources ({ref}`erasure`)."""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import UTC
from previously.cli import main
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import MODEL_CALL
from previously.core.action import write_action
from previously.core.append import append
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.assertions import AssertionRefused
from previously.core.assertions import read_threads
from previously.core.assertions import write_statements
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import RedactionRefused
from previously.core.policy import Circle
from previously.core.policy import OwnIdentity
from previously.core.policy import read_policy
from previously.core.policy import set_policy
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.redact import Redacted
from previously.core.redaction import units_payload
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import text
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import pytest
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.rows import EventRow
    from previously.contract.rows import Tip
    from previously.contract.rows import UnitRow
    from previously.core.assertion import Thread
    from sqlalchemy import Connection
    from sqlalchemy import Engine


NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 9, 13, 0, 0, tzinfo=UTC)
BLOB = hashlib.sha256(b"attachment").hexdigest()


def _event(external_id: str = "m", *, blobs: tuple[str, ...] = ()) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two."), RawUnit(3, "Three.")),
        payload={"text": "One. Two. Three."},
        blobs=tuple(BlobRef(sha256=b, size=1, media_type="text/plain") for b in blobs),
    )


def _call(
    storage: PostgresStorage,
    event: int,
    *,
    units: tuple[int, ...] = (),
    blobs: tuple[str, ...] = (),
    answer: tuple[str, ...] = ("alpha", "beta"),
) -> int:
    """A `model_call` of the form the gate writes, naming what it read."""
    payload: dict[str, object] = {
        "action": MODEL_CALL,
        "outcome": "ok",
        "alarms": [],
        "inputs": [{"event": event, "units": list(units), "blobs": list(blobs)}],
    }
    raw = [RawUnit(seq, text) for seq, text in enumerate(answer, 1)]
    return append_action(storage, payload, raw, recorded_at=NOW)


def _rows(storage: PostgresStorage) -> list[EventRow]:
    with storage.begin() as conn:
        return list(storage.read(conn, from_id=1, limit=100))


def _content(storage: PostgresStorage, event_id: int) -> list[str | None]:
    with storage.begin() as conn:
        return [unit.content for unit in storage.units_by_event(conn, [event_id]).get(event_id, [])]


def _setup(db: Engine) -> PostgresStorage:
    storage = PostgresStorage(db)
    append(storage, [_event()], recorded_at=NOW)
    return storage


@pytest.mark.db
def test_erasing_an_event_erases_the_result_of_the_call_that_read_it(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2, 3))

    result = redact_event(storage, storage, 1, reason="wrong list", recorded_at=LATER)

    assert result.cascaded == (call,)
    assert _content(storage, call) == [None, None]
    rows = _rows(storage)
    assert rows[call - 1].payload is not None
    cascade = rows[-1]
    assert cascade.payload is not None
    assert cascade.payload["reason"] == f"cascade of redaction {result.redaction_id}"
    assert cascade.payload["scope"] == "units"
    assert cascade.payload["target"] == {"event": call, "units": [1, 2]}
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_a_unit_the_call_read_erases_its_result(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2))

    result = redact_units(storage, storage, 1, [2], reason="wrong", recorded_at=LATER)

    assert result.cascaded == (call,)
    assert _content(storage, call) == [None, None]
    assert verify(storage) == []


@pytest.mark.db
def test_a_unit_the_call_did_not_read_takes_nothing_with_it(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2))

    result = redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _content(storage, call) == ["alpha", "beta"]
    assert len(_rows(storage)) == 3
    assert verify(storage) == []


@pytest.mark.db
def test_a_call_that_read_another_event_is_left_alone(db: Engine) -> None:
    storage = _setup(db)
    append(storage, [_event("n")], recorded_at=NOW)
    call = _call(storage, 2, units=(1, 2, 3))

    result = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _content(storage, call) == ["alpha", "beta"]
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_a_blob_the_call_read_erases_its_result(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event(blobs=(BLOB,))], recorded_at=NOW)
    call = _call(storage, 1, units=(), blobs=(BLOB,))

    result = redact_blob(storage, storage, BLOB, reason="wrong", recorded_at=LATER)

    assert result.cascaded == (call,)
    assert _content(storage, call) == [None, None]
    cascade = _rows(storage)[-1]
    assert cascade.payload is not None
    assert cascade.payload["reason"] == f"cascade of redaction {result.redaction_id}"
    assert verify(storage) == []


@pytest.mark.db
def test_a_call_that_read_another_blob_is_left_alone(db: Engine) -> None:
    storage = PostgresStorage(db)
    other = hashlib.sha256(b"other").hexdigest()
    append(storage, [_event(blobs=(BLOB, other))], recorded_at=NOW)
    call = _call(storage, 1, units=(), blobs=(other,))

    result = redact_blob(storage, storage, BLOB, reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _content(storage, call) == ["alpha", "beta"]
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_twice_writes_no_second_cascade(db: Engine) -> None:
    storage = _setup(db)
    _call(storage, 1, units=(1, 2, 3))
    redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)
    count = len(_rows(storage))

    again = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert again.cascaded == ()
    assert len(_rows(storage)) == count
    assert verify(storage) == []


@pytest.mark.db
def test_a_cascade_by_hand_without_its_order_is_a_finding(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2, 3))
    with storage.begin() as conn:
        storage.erase_units(conn, call, [1, 2])

    findings = [(f.event_id, f.reason) for f in verify(storage)]

    assert findings == [
        (call, "unit 1 is erased without a redaction"),
        (call, "unit 2 is erased without a redaction"),
    ]


@pytest.mark.db
def test_a_call_that_keeps_the_result_of_erased_input_is_a_finding(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2, 3))
    # The call comes after the erasure and still names what it read: a call
    # that kept its result while its input was erased, as a missing cascade
    # leaves it.
    redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)
    late = _call(storage, 1, units=(1,))

    findings = [(f.event_id, f.reason) for f in verify(storage)]

    assert findings == [(late, f"model_call {late} keeps the result of erased input")]
    assert call < late


@pytest.mark.db
def test_a_call_that_keeps_the_result_of_an_erased_blob_is_a_finding(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event(blobs=(BLOB,))], recorded_at=NOW)
    redact_blob(storage, storage, BLOB, reason="wrong", recorded_at=LATER)
    late = _call(storage, 1, blobs=(BLOB,))

    findings = [(f.event_id, f.reason) for f in verify(storage)]

    assert findings == [(late, f"model_call {late} keeps the result of erased input")]


@pytest.mark.db
def test_a_call_that_read_a_unit_that_is_not_erased_is_no_finding(db: Engine) -> None:
    """The control of the two above: the erasure touched another unit."""
    storage = _setup(db)
    redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=LATER)
    _call(storage, 1, units=(1, 2))

    assert verify(storage) == []


@pytest.mark.db
def test_a_model_call_can_be_redacted_and_a_redaction_cannot(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1,))

    result = redact_event(storage, storage, call, reason="wrong", recorded_at=LATER)

    assert result.written
    assert _rows(storage)[call - 1].payload is None
    assert verify(storage) == []
    with pytest.raises(RedactionRefused, match="is a redaction"):
        redact_event(storage, storage, result.redaction_id, reason="r", recorded_at=LATER)


@pytest.mark.db
def test_erasing_a_policy_event_reads_the_previous_version_or_none(db: Engine) -> None:
    """Specification section 2.1: an erased policy event counts as nothing,
    like a revocation, so the key falls back to the version before it."""
    storage = PostgresStorage(db)
    set_policy(storage, OwnIdentity("@example.org"), statement="mine", recorded_at=NOW)
    set_policy(storage, Circle("xz"), statement="a circle", recorded_at=NOW)
    newer = set_policy(storage, Circle("xz"), statement="the same, again", recorded_at=NOW)
    only = set_policy(storage, OwnIdentity("@example.com"), statement="other", recorded_at=NOW)

    redact_event(storage, storage, newer, reason="wrong statement", recorded_at=LATER)
    redact_event(storage, storage, only, reason="wrong statement", recorded_at=LATER)

    with storage.begin() as conn:
        after = read_policy(storage, conn)
    assert [own.member for own in after.own] == ["@example.org"]
    assert list(after.circles) == ["xz"]
    assert after.ids[("circle", "xz")] != newer
    assert verify(storage) == []


@pytest.mark.db
def test_the_command_line_names_the_calls_it_cascaded(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1,))
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))

    assert main(["redact", "event", "1", "--reason", "wrong"]) == 0

    out, _err = capsys.readouterr()
    assert out == f"redacted by event {call + 1}\ncascaded: model_call {call}\n"


@pytest.mark.db
def test_a_call_with_malformed_inputs_does_not_stop_an_erasure(db: Engine) -> None:
    """`verify` reports the call; the erasure reads past it."""
    storage = _setup(db)
    append_action(
        storage,
        {"action": MODEL_CALL, "outcome": "ok", "alarms": [], "inputs": "event 1"},
        [RawUnit(1, "alpha")],
        recorded_at=NOW,
    )

    result = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert [f.event_id for f in verify(storage)] == [2]


def _waiting_on_a_row_lock(db: Engine) -> bool:
    with db.connect() as conn:
        waiting = conn.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
        ).scalar_one()
    return waiting > 0


@pytest.mark.db
def test_an_erasure_waits_at_the_row_lock_of_the_call_before_it_takes_a_chain_position(
    db: Engine,
) -> None:
    """Ruling R-12 of the 2026-10-09 gate plan. Erasure A of event 1 meets
    erasure B of the call 2 that read it; B is held halfway, with the lock
    on the call's row, and then writes its redaction at the tip.

    If A took its chain position before it locked the call, B's write would
    wait for A's position while A waits for B's row, and PostgreSQL would end
    one of them with a deadlock error. The test proves that order for this
    pair: A waits at the row, B's write goes through, both finish, `verify`
    is green. It doesn't prove the absence of a deadlock for other
    interleavings.
    """
    storage = _setup(db)
    call = _call(storage, 1, units=(1, 2, 3))
    outcome: list[Redacted] = []
    failure: list[BaseException] = []

    def erase() -> None:
        try:
            outcome.append(redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER))
        except BaseException as error:
            failure.append(error)

    with storage.begin() as held:
        storage.lock_event(held, call)
        eraser = threading.Thread(target=erase)
        eraser.start()
        deadline = time.monotonic() + 15
        while not _waiting_on_a_row_lock(db):
            assert time.monotonic() < deadline, "A never waited at a row lock"
            time.sleep(0.05)
        # B's own redaction, at the tip, while A waits.
        payload = units_payload(call, [1, 2], reason="B erases the call itself")
        write_action(storage, held, payload, (), recorded_at=LATER)
        storage.erase_units(held, call, [1, 2])
    eraser.join(timeout=30)

    assert not eraser.is_alive()
    assert failure == []
    (result,) = outcome
    assert result.cascaded == ()
    assert _content(storage, call) == [None, None]
    assert verify(storage) == []


# --- assertions ---------------------------------------------------------------------


def _owed(
    *sources: Source,
    responsibility: str = DIRECT,
    subject: int | None = None,
    due: date | None = date(2026, 11, 30),
) -> Statement:
    """An obligation, direct by the operator or, with `OPEN`, proposed by a
    model."""
    return Statement(
        OBLIGATION,
        OPERATOR if responsibility == DIRECT else model_author("claude-code"),
        responsibility,
        sources,
        None,
        None,
        subject,
        None,
        None,
        ObligationBody("own", "circle:huber", "send the offer", due, "open"),
    )


def _assert(storage: PostgresStorage, *statements: Statement) -> tuple[int, ...]:
    return write_statements(storage, storage, statements, recorded_at=NOW)


def _thread(storage: PostgresStorage, subject: int) -> Thread | None:
    with storage.begin() as conn:
        return read_threads(storage, conn).get(subject)


def _erased(storage: PostgresStorage) -> list[int]:
    """The ids of the assertions whose payload is erased."""
    return [row.id for row in _rows(storage) if row.kind == "assertion" and row.payload is None]


def _three_events(db: Engine) -> PostgresStorage:
    storage = _setup(db)
    append(storage, [_event("n"), _event("o")], recorded_at=NOW)
    return storage


@pytest.mark.db
def test_erasing_an_event_erases_every_assertion_that_rests_on_it(db: Engine) -> None:
    storage = _setup(db)
    whole, units = _assert(storage, _owed(Source(1, None)), _owed(Source(1, (2,))))

    result = redact_event(storage, storage, 1, reason="wrong list", recorded_at=LATER)

    assert result.cascaded == (whole, units)
    assert result.cascaded_assertions == (whole, units)
    assert _erased(storage) == [whole, units]
    cascades = [row.payload for row in _rows(storage)[-2:]]
    assert cascades == [
        {
            "action": "redaction",
            "scope": "event",
            "target": {"event": assertion, "blobs": []},
            "reason": f"cascade of redaction {result.redaction_id}",
        }
        for assertion in (whole, units)
    ]
    assert _thread(storage, whole) is None
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_a_unit_the_assertion_names_erases_it(db: Engine) -> None:
    storage = _setup(db)
    (named,) = _assert(storage, _owed(Source(1, (1, 2))))

    result = redact_units(storage, storage, 1, [2], reason="wrong", recorded_at=LATER)

    assert result.cascaded == (named,)
    assert _erased(storage) == [named]
    assert verify(storage) == []


@pytest.mark.db
def test_a_unit_the_assertion_does_not_name_takes_nothing_with_it(db: Engine) -> None:
    """Review focus 3 of the plan, the control: the assertion stands."""
    storage = _setup(db)
    (named,) = _assert(storage, _owed(Source(1, (1, 2))))

    result = redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _erased(storage) == []
    assert _thread(storage, named) is not None
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_any_unit_erases_an_assertion_that_rests_on_the_whole_event(
    db: Engine,
) -> None:
    storage = _setup(db)
    (whole,) = _assert(storage, _owed(Source(1, None)))

    result = redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=LATER)

    assert result.cascaded == (whole,)
    assert verify(storage) == []


@pytest.mark.db
def test_a_unit_erased_before_the_assertion_does_not_take_the_whole_event_with_it(
    db: Engine,
) -> None:
    """An assertion written on the whole event after one of its units was
    erased rests on what stood then. Erasing that unit once more writes
    nothing and takes nothing with it."""
    storage = _setup(db)
    redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=NOW)
    (whole,) = _assert(storage, _owed(Source(1, None)))

    again = redact_units(storage, storage, 1, [3], reason="wrong", recorded_at=LATER)

    assert not again.written
    assert again.cascaded == ()
    assert _thread(storage, whole) is not None
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_one_of_three_sources_erases_the_assertion(db: Engine) -> None:
    storage = _three_events(db)
    (three,) = _assert(storage, _owed(Source(1, None), Source(2, (1,)), Source(3, None)))

    result = redact_event(storage, storage, 2, reason="wrong", recorded_at=LATER)

    assert result.cascaded == (three,)
    assert verify(storage) == []


@pytest.mark.db
def test_an_assertion_on_another_event_is_left_alone(db: Engine) -> None:
    storage = _three_events(db)
    (other,) = _assert(storage, _owed(Source(2, None)))

    result = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _thread(storage, other) is not None
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_a_blob_leaves_an_assertion_standing(db: Engine) -> None:
    """A blob erasure erases neither the payload nor a unit of the event
    that used the blob, so nothing an assertion rests on is gone."""
    storage = PostgresStorage(db)
    append(storage, [_event(blobs=(BLOB,))], recorded_at=NOW)
    (standing,) = _assert(storage, _owed(Source(1, None)))

    result = redact_blob(storage, storage, BLOB, reason="wrong", recorded_at=LATER)

    assert result.cascaded == ()
    assert _thread(storage, standing) is not None
    assert verify(storage) == []


@pytest.mark.db
def test_a_call_and_an_assertion_are_cascaded_together(db: Engine) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1,))
    (owed,) = _assert(storage, _owed(Source(1, (1,))))

    result = redact_units(storage, storage, 1, [1], reason="wrong", recorded_at=LATER)

    assert result.cascaded == (call, owed)
    assert result.cascaded_assertions == (owed,)
    assert verify(storage) == []


@pytest.mark.db
def test_approval_and_rejection_go_with_the_sources_they_copied(db: Engine) -> None:
    storage = _three_events(db)
    proposed = _owed(Source(2, None), responsibility=OPEN)
    first, second = _assert(storage, proposed, proposed)
    approval = replace(proposed, responsibility=DIRECT, subject=first, approves=first)
    rejection = Statement(
        REJECTION, OPERATOR, DIRECT, (Source(2, None),), None, None, None, None, second, None
    )
    approved, rejected = _assert(storage, approval, rejection)

    result = redact_event(storage, storage, 2, reason="wrong", recorded_at=LATER)

    assert result.cascaded == (first, second, approved, rejected)
    assert verify(storage) == []


@pytest.mark.db
def test_erasing_twice_writes_no_second_cascade_of_assertions(db: Engine) -> None:
    storage = _setup(db)
    _assert(storage, _owed(Source(1, None)))
    redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)
    count = len(_rows(storage))

    again = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert again.cascaded == ()
    assert len(_rows(storage)) == count
    assert verify(storage) == []


@pytest.mark.db
def test_the_winner_falls_back_to_the_next_direct_version_and_then_to_the_proposal(
    db: Engine,
) -> None:
    """Review focus 1 of the plan, with real erasures: the winning direct
    version is erased while a proposal stands. The entry falls back to the
    next direct version; once there is none, the proposal appears, as a
    proposal and never as direct."""
    storage = _three_events(db)
    (first,) = _assert(storage, _owed(Source(1, None)))
    (proposed,) = _assert(storage, _owed(Source(3, None), responsibility=OPEN, subject=first))
    (latest,) = _assert(storage, _owed(Source(2, None), subject=first, due=date(2026, 12, 4)))

    redact_event(storage, storage, 2, reason="wrong", recorded_at=LATER)
    thread = _thread(storage, first)

    assert thread is not None
    winner = thread.winner()
    assert winner is not None
    assert winner.id == first
    assert [version.id for version in thread.pending()] == [proposed]
    assert verify(storage) == []

    redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)
    thread = _thread(storage, first)

    assert thread is not None
    assert thread.subject == first  # it keeps its name though the first version is gone
    winner = thread.winner()
    assert winner is not None
    assert winner.id == proposed
    assert winner.statement.responsibility == OPEN
    assert thread.pending() == ()
    assert _erased(storage) == [first, latest]
    assert verify(storage) == []


@pytest.mark.db
def test_the_command_line_names_the_assertions_it_cascaded(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    storage = _setup(db)
    call = _call(storage, 1, units=(1,))
    (owed,) = _assert(storage, _owed(Source(1, None)))
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))

    assert main(["redact", "event", "1", "--reason", "wrong"]) == 0

    out, _err = capsys.readouterr()
    assert out == (
        f"redacted by event {owed + 1}\ncascaded: model_call {call}\ncascaded: assertion {owed}\n"
    )


class _Pausing(PostgresStorage):
    """The real store, except that the first call of the method `at` waits
    until `go_on` is set; `holding` says it is there. Paused at `tip`, the
    write path of assertions holds the locks on its sources; paused at
    `lock_event`, an erasure holds the lock on its target."""

    def __init__(self, engine: Engine, at: str) -> None:
        super().__init__(engine)
        self.at = at
        self.holding = threading.Event()
        self.go_on = threading.Event()

    def _pause(self, method: str) -> None:
        if method == self.at and not self.holding.is_set():
            self.holding.set()
            assert self.go_on.wait(timeout=15)

    def tip(self, conn: Connection) -> Tip | None:
        self._pause("tip")
        return super().tip(conn)

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        row = super().lock_event(conn, event_id)
        self._pause("lock_event")
        return row

    def insert_event(
        self,
        conn: Connection,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
        blobs: Sequence[bytes] = (),
    ) -> None:
        self._pause("insert_event")
        super().insert_event(conn, row, units, key, blobs)


def _until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + 15
    while not condition():
        assert time.monotonic() < deadline, what
        time.sleep(0.02)


@pytest.mark.db
@pytest.mark.parametrize("erased", [True, False], ids=["erased-meanwhile", "control"])
def test_an_erasure_that_waits_at_the_lock_of_the_write_path_finds_the_assertion(
    db: Engine, erased: bool
) -> None:
    """The write path holds the row lock of its source and has not written
    yet; `redact event` of the source reads the assertions (none) and waits
    at that lock. The write path commits; the erasure gets the lock, reads
    the assertions again, finds the new one, and erases it.

    Without the lock the write path reads its source before the erasure and
    writes after it, and the assertion stands on an erased source. The
    control erases nothing and the assertion stands."""
    plain = _setup(db)
    pausing = _Pausing(db, "tip")
    written: list[tuple[int, ...]] = []
    redacted: list[Redacted] = []
    failure: list[BaseException] = []

    def write() -> None:
        try:
            written.append(
                write_statements(pausing, pausing, [_owed(Source(1, None))], recorded_at=NOW)
            )
        except BaseException as error:
            failure.append(error)

    def erase() -> None:
        try:
            redacted.append(redact_event(plain, plain, 1, reason="wrong", recorded_at=LATER))
        except BaseException as error:
            failure.append(error)

    writer = threading.Thread(target=write)
    writer.start()
    assert pausing.holding.wait(timeout=15)
    eraser = threading.Thread(target=erase)
    if erased:
        eraser.start()
        _until(
            lambda: _waiting_on_a_row_lock(db) or not eraser.is_alive(),
            "the erasure neither waited nor ended",
        )
    pausing.go_on.set()
    for thread in (writer, *((eraser,) if erased else ())):
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert failure == []
    ((owed,),) = written
    assert verify(plain) == []
    if not erased:
        assert _thread(plain, owed) is not None
        return
    (result,) = redacted
    assert result.cascaded == (owed,)
    assert _erased(plain) == [owed]


@pytest.mark.db
def test_an_assertion_that_waits_at_the_lock_of_an_erasure_is_refused(db: Engine) -> None:
    """The other order: the erasure holds the lock of the source; the write
    path waits at it, and once it gets it, finds the source erased."""
    plain = _setup(db)
    pausing = _Pausing(db, "lock_event")
    refused: list[AssertionRefused] = []
    failure: list[BaseException] = []

    def write() -> None:
        try:
            write_statements(plain, plain, [_owed(Source(1, None))], recorded_at=NOW)
        except AssertionRefused as error:
            refused.append(error)
        except BaseException as error:
            failure.append(error)

    def erase() -> None:
        try:
            redact_event(pausing, pausing, 1, reason="wrong", recorded_at=LATER)
        except BaseException as error:
            failure.append(error)

    eraser = threading.Thread(target=erase)
    eraser.start()
    assert pausing.holding.wait(timeout=15)
    writer = threading.Thread(target=write)
    writer.start()
    _until(
        lambda: _waiting_on_a_row_lock(db) or not writer.is_alive(),
        "the write path neither waited nor ended",
    )
    pausing.go_on.set()
    for thread in (eraser, writer):
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert failure == []
    assert [str(error) for error in refused] == ["event 1 is erased and cannot be a source"]
    assert verify(plain) == []


@pytest.mark.db
def test_two_erasures_that_reach_one_assertion_erase_it_once(db: Engine) -> None:
    """Erasure A of event 2 holds the lock of the assertion and is about to
    write; erasure B of event 1 found the same assertion standing and waits
    at its lock. Once A has committed, B reads the locked row as erased and
    writes nothing for it."""
    plain = _three_events(db)
    (owed,) = _assert(plain, _owed(Source(1, None), Source(2, None)))
    pausing = _Pausing(db, "insert_event")
    erased: list[Redacted] = []
    failure: list[BaseException] = []

    def erase(storage: PostgresStorage, event_id: int) -> None:
        try:
            erased.append(redact_event(storage, storage, event_id, reason="r", recorded_at=LATER))
        except BaseException as error:
            failure.append(error)

    first = threading.Thread(target=erase, args=(pausing, 2))
    first.start()
    assert pausing.holding.wait(timeout=15)
    second = threading.Thread(target=erase, args=(plain, 1))
    second.start()
    _until(lambda: _waiting_on_a_row_lock(db), "the second erasure never waited")
    pausing.go_on.set()
    for thread in (first, second):
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert failure == []
    assert [result.cascaded for result in erased] == [(owed,), ()]
    assert verify(plain) == []


@pytest.mark.db
def test_an_assertion_with_a_broken_form_goes_with_the_events_it_names(db: Engine) -> None:
    """The cascade reads the sources of an assertion leniently, so a forged
    one goes too: units that are no list count as the whole event, and an
    entry without an event id names nothing. One whose sources are no list
    names nothing, stays, and `verify` reports its form."""
    storage = _setup(db)
    (owed,) = _assert(storage, _owed(Source(1, None)))
    good = dict(cast("Mapping[str, object]", _rows(storage)[owed - 1].payload))
    lenient = _forge(
        storage, {**good, "sources": [{"event": 1, "units": "all"}, "event 1", {"event": "1"}]}
    )
    unreadable = _forge(storage, {**good, "sources": "event 1"})

    result = redact_event(storage, storage, 1, reason="wrong", recorded_at=LATER)

    assert result.cascaded == (owed, lenient)
    assert [(f.event_id, f.reason.split(":")[0]) for f in verify(storage)] == [
        (unreadable, "assertion has no valid form")
    ]


def _forge(storage: PostgresStorage, payload: Mapping[str, object]) -> int:
    """An assertion on the tip that did not come through its write path."""
    prepared = prepare(kind="assertion", occurred_at=NOW, payload=payload, units=(), key=None)
    with storage.begin() as conn:
        tip = storage.tip(conn)
        assert tip is not None
        row, units = link(prepared, event_id=tip.id + 1, prev_hash=tip.hash, recorded_at=NOW)
        storage.insert_event(conn, row, units, None)
    return row.id


@pytest.mark.db
@pytest.mark.parametrize("through", ["proposal", "source"])
def test_an_approval_stands_when_its_proposal_is_erased_on_its_own(
    db: Engine, through: str
) -> None:
    """Ruling F-5 of the 2026-10-12 assertions plan: erasing the proposal on
    its own leaves the approval as the direct winner. The control erases the
    source they share, and the approval goes with the proposal."""
    storage = _setup(db)
    proposed = _owed(Source(1, None), responsibility=OPEN)
    (first,) = _assert(storage, proposed)
    (approved,) = _assert(
        storage, replace(proposed, responsibility=DIRECT, subject=first, approves=first)
    )

    target = first if through == "proposal" else 1
    redact_event(storage, storage, target, reason="wrong", recorded_at=LATER)

    thread = _thread(storage, first)
    assert verify(storage) == []
    if through == "source":
        assert thread is None
        return
    assert thread is not None
    winner = thread.winner()
    assert winner is not None
    assert winner.id == approved
    assert winner.statement.responsibility == DIRECT
