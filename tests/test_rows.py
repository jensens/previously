# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rows, not domain objects — the field contract of {ref}`database-schema`."""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import EventRow
from previously.contract.rows import Tip
from previously.contract.rows import UnitRow


def test_tip_carries_id_and_hash() -> None:
    tip = Tip(id=7, hash=b"\x01" * 32)
    assert tip.id == 7
    assert tip.hash == b"\x01" * 32


def test_event_row_carries_every_field() -> None:
    moment = datetime(2026, 10, 2, 14, 0, 0, tzinfo=UTC)
    row = EventRow(
        id=1,
        kind="observation",
        recorded_at=moment,
        occurred_at=moment,
        prev_hash=None,
        hash=b"\x01" * 32,
        payload_hash=b"\x02" * 32,
        units_hash=b"\x03" * 32,
        payload={"text": "hello"},
    )
    assert row.kind == "observation"
    assert row.prev_hash is None
    assert row.payload == {"text": "hello"}


def test_event_row_payload_may_be_absent_tombstone() -> None:
    """payload=None is the tombstone ({ref}`tombstone-seam`): payload_hash stays."""
    moment = datetime(2026, 10, 2, 14, 0, 0, tzinfo=UTC)
    row = EventRow(
        id=1,
        kind="observation",
        recorded_at=moment,
        occurred_at=moment,
        prev_hash=None,
        hash=b"\x01" * 32,
        payload_hash=b"\x02" * 32,
        units_hash=b"\x03" * 32,
        payload=None,
    )
    assert row.payload is None
    assert row.payload_hash == b"\x02" * 32


def test_unit_row_optional_fields_default_to_none() -> None:
    row = UnitRow(event_id=1, seq=1, content="Text")
    assert row.start_ms is None
    assert row.end_ms is None
    assert row.speaker is None


def test_an_event_row_that_says_nothing_is_version_1_without_a_salt() -> None:
    """The defaults mirror the columns: a row that names no hash version is a
    version 1 row, and a version 1 row has no salt ({ref}`hash-version-2`)."""
    moment = datetime(2026, 10, 2, 14, 0, 0, tzinfo=UTC)
    row = EventRow(
        id=1,
        kind="observation",
        recorded_at=moment,
        occurred_at=moment,
        prev_hash=None,
        hash=b"\x01" * 32,
        payload_hash=b"\x02" * 32,
        units_hash=b"\x03" * 32,
        payload={"text": "hello"},
    )
    assert row.hash_version == 1
    assert row.payload_salt is None


def test_a_unit_row_may_lack_its_content_and_carries_digest_and_salt() -> None:
    """`content=None` is the tombstone of a unit; digest and salt default to
    `None`, because a version 1 unit has neither."""
    erased = UnitRow(event_id=1, seq=2, content=None)
    assert erased.content is None
    plain = UnitRow(event_id=1, seq=1, content="Text")
    assert plain.digest is None
    assert plain.salt is None
