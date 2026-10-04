# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The derivation functions, without a database.

They take row types and return row types; that is the whole point of keeping
the arithmetic in `core` ({ref}`projections`), and it is why these tests carry
no `db` marker.
"""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import EventRow
from previously.contract.rows import SourceStatsRow
from previously.contract.rows import UnitRow
from previously.core.projection import chronicle
from previously.core.projection import source_stats
from previously.core.projection.worker import Batch
from previously.core.redaction import event_payload
from previously.core.redaction import units_payload


T1 = datetime(2026, 10, 1, tzinfo=UTC)
T2 = datetime(2026, 10, 2, tzinfo=UTC)
T3 = datetime(2026, 10, 3, tzinfo=UTC)


def _event(
    event_id: int,
    occurred_at: datetime,
    payload: dict[str, object] | None,
    kind: str = "observation",
) -> EventRow:
    return EventRow(
        id=event_id,
        kind=kind,
        recorded_at=T3,
        occurred_at=occurred_at,
        prev_hash=None,
        hash=bytes([event_id]) * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x01" * 32,
        payload=payload,
    )


def test_chronicle_derives_one_row_per_unit_with_the_source_attribution() -> None:
    batch = Batch(
        events=(_event(1, T1, {"evidence": "verbatim", "text": "a\n\nb"}),),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b", speaker="alice")]},
        keys={1: ("email", "msg-1")},
    )
    rows = chronicle.derive(batch)
    assert [(r.event_id, r.seq, r.content) for r in rows] == [(1, 1, "a"), (1, 2, "b")]
    assert {(r.source, r.external_id, r.evidence) for r in rows} == {("email", "msg-1", "verbatim")}
    assert rows[1].speaker == "alice"
    assert rows[0].occurred_at == T1


def test_chronicle_leaves_source_null_for_an_event_without_a_key() -> None:
    batch = Batch(
        events=(_event(1, T1, {"evidence": "recollection"}),),
        units={1: [UnitRow(1, 1, "a")]},
        keys={},
    )
    (row,) = chronicle.derive(batch)
    assert (row.source, row.external_id) == (None, None)


def test_chronicle_still_derives_rows_for_a_payload_erased_without_a_redaction() -> None:
    """A payload set to `NULL` with the units left standing is no erasure
    `redact` writes: that one takes the units too, and the redaction it
    records is what takes the rows out ({ref}`projections`). What is left is a
    tombstone without an order, which `verify` reports, and for that the
    chronicle shows the units it still finds, with `evidence` NULL.
    `test_erasures_names_what_a_redaction_takes_out` is the test about the
    erasure that has an order."""
    batch = Batch(
        events=(_event(1, T1, None),), units={1: [UnitRow(1, 1, "a")]}, keys={1: ("cli", "x")}
    )
    (row,) = chronicle.derive(batch)
    assert row.evidence is None
    assert row.content == "a"


def test_chronicle_derives_no_row_for_a_unit_without_content() -> None:
    """An erased unit has nothing to show, and the chronicle is a view of what
    was said: its neighbour keeps its row, the erased unit gets none."""
    batch = Batch(
        events=(_event(1, T1, {"evidence": "verbatim"}),),
        units={1: [UnitRow(1, 1, None, digest=b"\x02" * 32), UnitRow(1, 2, "b")]},
        keys={1: ("cli", "x")},
    )
    assert [(r.seq, r.content) for r in chronicle.derive(batch)] == [(2, "b")]


def test_chronicle_derives_nothing_for_an_event_without_units() -> None:
    batch = Batch(events=(_event(1, T1, {"evidence": "recollection"}),), units={}, keys={})
    assert chronicle.derive(batch) == []


def test_erasures_names_what_a_redaction_takes_out() -> None:
    """A redaction of an event takes every row of it, a redaction of units
    the rows of those units, in chain order ({ref}`projections`). An action
    of another name takes nothing, nor does one that cannot be read as a
    redaction, nor a redaction of a blob: the chronicle holds no blob. An observation that
    carries the form of a redaction in its payload orders nothing either,
    since only the kind `action` is a redaction's. And a redaction that names
    an event after itself takes nothing, because it can order the erasure only
    of something before it."""
    blob: dict[str, object] = {
        "action": "redaction",
        "scope": "blob",
        "target": {"blob": "ab" * 32, "events": [5]},
        "reason": "r",
    }
    batch = Batch(
        events=(
            _event(6, T1, event_payload(5, blobs=(), reason="r"), kind="action"),
            _event(7, T1, {"action": "redaction", "scope": "event"}, kind="action"),
            _event(8, T1, units_payload(5, [3, 1], reason="r"), kind="action"),
            _event(9, T1, blob, kind="action"),
            _event(10, T1, event_payload(4, blobs=(), reason="r")),
            _event(11, T1, None, kind="action"),
            _event(12, T1, event_payload(13, blobs=(), reason="r"), kind="action"),
            _event(13, T1, {"action": "something-else"}, kind="action"),
        ),
        units={},
        keys={},
    )
    assert chronicle.erasures(batch) == [(5, None), (5, (1, 3))]


def test_source_stats_aggregates_a_batch_per_source() -> None:
    batch = Batch(
        events=(_event(1, T1, {}), _event(2, T2, {}), _event(3, T3, {})),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b")], 2: [UnitRow(2, 1, "c")], 3: []},
        keys={1: ("email", "m1"), 2: ("email", "m2"), 3: ("cli", "x")},
    )
    stats = source_stats.derive(batch)
    assert stats == {
        "email": SourceStatsRow(
            "email", events=2, units=3, first_seen=T1, last_seen=T2, last_event_id=2
        ),
        "cli": SourceStatsRow(
            "cli", events=1, units=0, first_seen=T3, last_seen=T3, last_event_id=3
        ),
    }


def test_source_stats_ignores_an_event_without_a_source() -> None:
    batch = Batch(events=(_event(1, T1, {}),), units={1: [UnitRow(1, 1, "a")]}, keys={})
    assert source_stats.derive(batch) == {}


def test_merge_adds_counts_and_keeps_the_extremes() -> None:
    existing = SourceStatsRow("email", 2, 3, T1, T2, 2)
    addition = SourceStatsRow("email", 1, 1, T3, T3, 3)
    assert source_stats.merge(existing, addition) == SourceStatsRow("email", 3, 4, T1, T3, 3)


def test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older() -> None:
    """The regression case the stage 1b specification names ({ref}`projections`):
    an event that *arrives* later but *happened* earlier. Never updating
    `first_seen` agrees with the minimum on every in-order sequence and parts
    here. Measured on 2026-10-04, two mutations of `merge`: with
    `first_seen=existing.first_seen` (never update) this test fails alone and
    `test_merge_adds_counts_and_keeps_the_extremes` stays green — that one is
    the control. With `first_seen=addition.first_seen` (overwrite) the in-order
    test fails and this one stays green, because an older late arrival happens
    to be the minimum. The two tests together catch both natural mistakes."""
    existing = SourceStatsRow("email", 1, 1, T2, T2, 1)
    late_but_older = SourceStatsRow("email", 1, 1, T1, T1, 2)
    merged = source_stats.merge(existing, late_but_older)
    assert merged.first_seen == T1
    assert merged.last_seen == T2
    assert merged.last_event_id == 2


def test_merge_with_nothing_existing_is_the_addition() -> None:
    addition = SourceStatsRow("email", 1, 1, T1, T1, 1)
    assert source_stats.merge(None, addition) == addition
