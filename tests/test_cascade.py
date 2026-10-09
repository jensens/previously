# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The erasure cascade: the result of a `model_call` goes with its input
({ref}`erasure`)."""

from datetime import datetime
from datetime import UTC
from previously.cli import main
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import MODEL_CALL
from previously.core.append import append
from previously.core.errors import RedactionRefused
from previously.core.policy import Circle
from previously.core.policy import OwnIdentity
from previously.core.policy import read_policy
from previously.core.policy import set_policy
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import hashlib
import pytest


if TYPE_CHECKING:
    from previously.contract.rows import EventRow
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
