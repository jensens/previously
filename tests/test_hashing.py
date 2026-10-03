# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import tzinfo
from datetime import UTC
from previously.contract.types import RawUnit
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash
from previously.core.hashing import iso_utc
from previously.core.hashing import payload_hash
from previously.core.hashing import units_hash
from previously.storage.rows import UnitRow

import hashlib
import pytest


RECORDED = datetime(2026, 10, 2, 14, 0, 0, tzinfo=UTC)
OCCURRED = datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)
DIGEST = b"\x01" * 32
UNITS_DIGEST = b"\x04" * 32


def test_iso_utc_form() -> None:
    m = datetime(2026, 10, 2, 14, 23, 45, 123456, tzinfo=UTC)
    assert iso_utc(m) == "2026-10-02T14:23:45.123456Z"


def test_iso_utc_converts_to_utc() -> None:
    m = datetime(2026, 10, 2, 16, 23, 45, 123456, tzinfo=timezone(timedelta(hours=2)))
    assert iso_utc(m) == "2026-10-02T14:23:45.123456Z"


def test_iso_utc_always_has_six_fractional_digits() -> None:
    m = datetime(2026, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
    assert iso_utc(m) == "2026-01-01T00:00:00.000000Z"


@pytest.mark.parametrize(
    ("year", "expected"),
    [(1, "0001"), (5, "0005"), (99, "0099"), (999, "0999"), (1000, "1000")],
)
def test_iso_utc_pads_a_year_below_1000_to_four_digits(year: int, expected: str) -> None:
    """Pins today's behaviour for years under 1000 (finding G-2).

    The hashed form is ISO 8601 ({ref}`hash-format`), and that wants four
    digits of year. `iso_utc` gets them from `strftime("%Y")`, and whether
    `%Y` pads is **not** specified by the C standard — measured, CPython
    itself is of two minds about it:

        time.strftime("%Y", (5, …))      -> '5'
        datetime(5, …).strftime("%Y")    -> '0005'

    `iso_utc` goes through `datetime.strftime`, so it pads today. Nothing held
    that down, and `iso_utc` sits in the hash path: a year with three digits
    would be a different byte string and therefore a different hash for the
    same moment.

    **This test deliberately does not change `iso_utc`.** An explicit
    `f"{moment.year:04d}"` would be a change in the hash path for a case that
    does not occur — `occurred_at` and `recorded_at` are timestamps of project
    events. Should CPython ever change, this test goes red and somebody
    decides then, with the chain in front of them. Until that day, the
    behaviour is pinned instead of assumed.
    """
    assert iso_utc(datetime(year, 1, 2, 3, 4, 5, 6, tzinfo=UTC)).startswith(f"{expected}-01-02T")


def test_iso_utc_rejects_a_naive_timestamp() -> None:
    # Naive on purpose: that a naive timestamp gets rejected cannot be tested
    # without building one, and `DTZ001` forbids exactly that construction.
    # That is the whole justification for the suppression (finding G-4: it
    # used to stand there without one).
    naive = datetime(2026, 10, 2, 14, 0, 0)  # noqa: DTZ001 — deliberate, see above
    with pytest.raises(InvalidPayload, match="time zone"):
        iso_utc(naive)


class _NoOffset(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None


def test_iso_utc_rejects_a_tzinfo_without_an_offset() -> None:
    """A tzinfo can be present and still yield no offset."""
    with pytest.raises(InvalidPayload, match="time zone"):
        iso_utc(datetime(2026, 10, 2, 14, 0, 0, tzinfo=_NoOffset()))


def test_payload_hash_is_sha256_of_the_canonical_bytes() -> None:
    expected = hashlib.sha256(b'{"a":1}').digest()
    assert payload_hash({"a": 1}) == expected


def test_payload_hash_is_independent_of_key_order() -> None:
    assert payload_hash({"a": 1, "b": 2}) == payload_hash({"b": 2, "a": 1})


def _event_hash(
    *,
    event_id: int = 1,
    kind: str = "observation",
    recorded_at: datetime = RECORDED,
    occurred_at: datetime = OCCURRED,
    prev_hash: bytes | None = None,
    payload_digest: bytes = DIGEST,
    units_digest: bytes = UNITS_DIGEST,
    source: str | None = "cli",
    external_id: str | None = "x1",
) -> bytes:
    return event_hash(
        event_id=event_id,
        kind=kind,
        recorded_at=recorded_at,
        occurred_at=occurred_at,
        prev_hash=prev_hash,
        payload_digest=payload_digest,
        units_digest=units_digest,
        source=source,
        external_id=external_id,
    )


def test_event_hash_depends_on_every_field() -> None:
    base = _event_hash()
    assert _event_hash(event_id=2) != base
    assert _event_hash(kind="assertion") != base
    assert _event_hash(recorded_at=datetime(2026, 10, 2, 14, 0, 1, tzinfo=UTC)) != base
    assert _event_hash(occurred_at=datetime(2026, 10, 1, 9, 0, 1, tzinfo=UTC)) != base
    assert _event_hash(prev_hash=b"\x02" * 32) != base
    assert _event_hash(payload_digest=b"\x03" * 32) != base
    # The three fields out of correction K1: without them the hash stayed the
    # same while the units or the source attribution were rewritten.
    assert _event_hash(units_digest=b"\x05" * 32) != base
    assert _event_hash(source="invented") != base
    assert _event_hash(external_id="y") != base


def test_event_hash_without_a_source_attribution_is_its_own_hash() -> None:
    """`source=None`/`external_id=None` is the keyless case
    ({ref}`hash-chain`) and has to differ from every hash *with* a key —
    otherwise an erased `source_key` row would not be distinguishable from a
    key that was never written, and that is exactly what the hash is supposed
    to deliver."""
    without = _event_hash(source=None, external_id=None)
    assert without != _event_hash()
    assert without != _event_hash(source=None)
    assert without != _event_hash(external_id=None)
    assert without == _event_hash(source=None, external_id=None)


def test_event_hash_length() -> None:
    assert len(_event_hash()) == 32


def test_units_hash_length() -> None:
    assert len(units_hash([RawUnit(seq=1, content="a")])) == 32


def test_units_hash_sorts_by_seq_itself() -> None:
    """The order goes into the hash, so it has to be settled — and `units_hash`
    settles it itself instead of relying on the caller. Without that, `append`
    hashed the connector's order and `verify` the `seq` order out of the
    database: a forgery report on an intact chain."""
    ascending = [RawUnit(seq=1, content="a"), RawUnit(seq=2, content="b")]
    scrambled = [RawUnit(seq=2, content="b"), RawUnit(seq=1, content="a")]
    assert units_hash(scrambled) == units_hash(ascending)


def test_units_hash_depends_on_every_field() -> None:
    base = units_hash([RawUnit(seq=1, content="a", start_ms=1, end_ms=2, speaker="A")])
    assert units_hash([RawUnit(seq=2, content="a", start_ms=1, end_ms=2, speaker="A")]) != base
    assert units_hash([RawUnit(seq=1, content="b", start_ms=1, end_ms=2, speaker="A")]) != base
    assert units_hash([RawUnit(seq=1, content="a", start_ms=9, end_ms=2, speaker="A")]) != base
    assert units_hash([RawUnit(seq=1, content="a", start_ms=1, end_ms=9, speaker="A")]) != base
    assert units_hash([RawUnit(seq=1, content="a", start_ms=1, end_ms=2, speaker="B")]) != base
    # The fields that are always empty in stage 1a are not the same as fields
    # that are set: from stage 2 on, a transcript carries real values there.
    assert units_hash([RawUnit(seq=1, content="a")]) != base


def test_units_hash_notices_a_missing_unit() -> None:
    """The forgery that no individual comparison finds: what is missing cannot
    be checked against itself."""
    two = [RawUnit(seq=1, content="a"), RawUnit(seq=2, content="b")]
    assert units_hash(two[1:]) != units_hash(two)
    assert units_hash([]) != units_hash(two)


def test_units_hash_rejects_non_canonicalizable_values() -> None:
    """`units_hash` goes through the same canonicaliser as the payload and
    therewith inherits its limits ({ref}`payload-range`). Out of the database
    that is not reachable — `int4` always lies inside the safe range —, but
    `verify` catches the exception and reports instead of raising (finding
    W1); this test proves that there is anything to catch there at all."""
    with pytest.raises(InvalidPayload, match="safe range"):
        units_hash([RawUnit(seq=1, content="a", start_ms=2**60)])


def test_units_hash_treats_rawunit_and_unitrow_alike() -> None:
    """`append` hashes `RawUnit`, `verify` hashes `UnitRow` — were the two to
    yield different digests, the check would report a forgery on every intact
    chain. `event_id` deliberately does not belong in the digest: it already
    stands as `id` in the event hash."""
    from_the_contract = [RawUnit(seq=1, content="a", speaker="A")]
    from_the_row = [UnitRow(event_id=7, seq=1, content="a", speaker="A")]
    assert units_hash(from_the_row) == units_hash(from_the_contract)


# ---------------------------------------------------------------------------
# The pinned test vector (review finding W5 of the final review).
#
# Before, this tree checked reproducibility with
# `assert _event_hash() == _event_hash()` — a tautology that would stay green
# even with a completely broken hash. Acceptance condition 5 ("the same hash
# across process boundaries and restarts") hung on that.
#
# What stands here instead are the hex literals and **all** the inputs that go
# with them, plus the canonical JCS bytes themselves. Such a test fires when
# the hash range changes unintentionally in the future — an additional field in
# the hash, a different key sorting, a different form of timestamp, a different
# escaping for "ä" — and is therewith the actual proof for acceptance
# condition 5. Should the hash range change **deliberately**, `HASH_VERSION`
# belongs raised and this vector recomputed; both then come to notice
# together.
#
# The input strings below are German and stay that way: they go **into** the
# hash, and the hex literals next to them were computed from exactly these
# bytes. Translating them and then recomputing the literals would destroy the
# very proof the vector exists for.
# ---------------------------------------------------------------------------

VECTOR_UNITS = (
    RawUnit(seq=1, content="Preis bleibt 1000 Euro."),
    RawUnit(seq=2, content="Bitte bestätigen.", start_ms=1500, end_ms=2500, speaker="Anna"),
)
VECTOR_PAYLOAD = {"text": "Preis bleibt 1000 Euro.", "evidence": "verbatim"}
VECTOR_PREV = bytes(range(32))
VECTOR_RECORDED = datetime(2026, 10, 2, 14, 23, 45, 123456, tzinfo=UTC)
VECTOR_OCCURRED = datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)

VECTOR_PAYLOAD_HEX = "6f3604dd00c587c361ebf0398cd6a2c9c2d7319341d4fa7708ffaf831ec8a15d"
VECTOR_UNITS_HEX = "0628194c7313b4793d419cdae5d31c21889512f0872ed3ef7dc1efcda9594510"
VECTOR_EVENT_HEX = "6839b69aee7b621d2ded904b677aa770ad9988cdb9ba12b43247e605df8797c3"

# The canonical bytes that SHA-256 runs over. They stand here verbatim,
# because the hash alone does not say *what* was hashed: should the test fire,
# comparing these strings shows immediately which field has changed.
JCS_PAYLOAD = '{"evidence":"verbatim","text":"Preis bleibt 1000 Euro."}'
JCS_UNITS = (
    '{"domain":"previously/units","units":['
    '{"content":"Preis bleibt 1000 Euro.","end_ms":null,"seq":1,'
    '"speaker":null,"start_ms":null},'
    '{"content":"Bitte bestätigen.","end_ms":2500,"seq":2,'
    '"speaker":"Anna","start_ms":1500}'
    '],"v":1}'
)
JCS_EVENT = (
    '{"domain":"previously/event","external_id":"nachricht-1","id":42,'
    '"kind":"observation","occurred_at":"2026-10-01T09:00:00.000000Z",'
    f'"payload":"{VECTOR_PAYLOAD_HEX}",'
    f'"prev":"{VECTOR_PREV.hex()}",'
    '"recorded_at":"2026-10-02T14:23:45.123456Z","source":"email",'
    f'"units":"{VECTOR_UNITS_HEX}","v":1}}'
)


def test_vector_payload_hash() -> None:
    assert payload_hash(VECTOR_PAYLOAD).hex() == VECTOR_PAYLOAD_HEX
    assert payload_hash(VECTOR_PAYLOAD) == hashlib.sha256(JCS_PAYLOAD.encode("utf-8")).digest()


def test_vector_units_hash() -> None:
    assert units_hash(VECTOR_UNITS).hex() == VECTOR_UNITS_HEX
    assert units_hash(VECTOR_UNITS) == hashlib.sha256(JCS_UNITS.encode("utf-8")).digest()


def test_vector_event_hash() -> None:
    computed = event_hash(
        event_id=42,
        kind="observation",
        recorded_at=VECTOR_RECORDED,
        occurred_at=VECTOR_OCCURRED,
        prev_hash=VECTOR_PREV,
        payload_digest=payload_hash(VECTOR_PAYLOAD),
        units_digest=units_hash(VECTOR_UNITS),
        source="email",
        external_id="nachricht-1",
    )
    assert computed.hex() == VECTOR_EVENT_HEX
    assert computed == hashlib.sha256(JCS_EVENT.encode("utf-8")).digest()
