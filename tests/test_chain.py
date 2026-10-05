# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Preparing and linking a version 2 event, without a database."""

from datetime import datetime
from datetime import UTC
from previously.contract.types import BlobRef
from previously.contract.types import RawUnit
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.chain import read_references
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import SALT_BYTES
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash_v2
from typing import cast
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from previously.core.chain import Prepared

OCCURRED = datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)
RECORDED = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
PAYLOAD: dict[str, object] = {"text": "a\n\nb", "evidence": "verbatim"}
UNITS = (
    RawUnit(seq=1, content="a"),
    RawUnit(seq=2, content="b", start_ms=1500, end_ms=2500, speaker="Anna"),
)


def _prepared(key: tuple[str, str] | None = ("email", "message-1")) -> Prepared:
    return prepare(kind="observation", occurred_at=OCCURRED, payload=PAYLOAD, units=UNITS, key=key)


def test_prepare_draws_one_salt_for_the_payload_and_one_per_unit() -> None:
    prepared = _prepared()
    salts = [prepared.payload_salt, *(unit.salt for unit in prepared.units)]
    assert [len(salt) for salt in salts] == [SALT_BYTES] * 3
    assert len(set(salts)) == 3


def test_prepare_computes_what_the_hash_functions_compute() -> None:
    prepared = _prepared()
    assert prepared.payload_digest == payload_hash_v2(PAYLOAD, prepared.payload_salt)
    for raw, unit in zip(UNITS, prepared.units, strict=True):
        assert unit.digest == unit_digest(
            seq=raw.seq,
            content=raw.content,
            start_ms=raw.start_ms,
            end_ms=raw.end_ms,
            speaker=raw.speaker,
            salt=unit.salt,
        )
    assert prepared.units_digest == units_hash_v2({u.seq: u.digest for u in prepared.units})


def test_prepare_twice_gives_two_different_digests_for_the_same_input() -> None:
    """The salt is drawn, not derived: the same payload twice is two digests,
    which is what keeps an erased one from being found by hashing a guess."""
    assert _prepared().payload_digest != _prepared().payload_digest


def test_link_hangs_the_event_into_the_chain() -> None:
    prepared = _prepared()
    prev = b"\x01" * 32
    row, units = link(prepared, event_id=7, prev_hash=prev, recorded_at=RECORDED)
    assert (row.id, row.prev_hash, row.hash_version) == (7, prev, HASH_VERSION_2)
    assert row.payload_salt == prepared.payload_salt
    assert (row.payload_hash, row.units_hash) == (prepared.payload_digest, prepared.units_digest)
    assert row.hash == event_hash_v2(
        event_id=7,
        kind="observation",
        recorded_at=RECORDED,
        occurred_at=OCCURRED,
        prev_hash=prev,
        payload_digest=prepared.payload_digest,
        units_digest=prepared.units_digest,
        source="email",
        external_id="message-1",
    )
    assert [(u.event_id, u.seq, u.content, u.digest, u.salt) for u in units] == [
        (7, p.seq, p.content, p.digest, p.salt) for p in prepared.units
    ]
    assert (units[1].start_ms, units[1].end_ms, units[1].speaker) == (1500, 2500, "Anna")


def test_link_without_a_key_hashes_no_source() -> None:
    prepared = _prepared(key=None)
    row, _ = link(prepared, event_id=1, prev_hash=None, recorded_at=RECORDED)
    assert row.hash == event_hash_v2(
        event_id=1,
        kind="observation",
        recorded_at=RECORDED,
        occurred_at=OCCURRED,
        prev_hash=None,
        payload_digest=prepared.payload_digest,
        units_digest=prepared.units_digest,
        source=None,
        external_id=None,
    )


def test_prepare_refuses_a_seq_that_appears_twice() -> None:
    """Two units under one `seq` would leave one digest in the mapping the
    units digest is taken over, so the digest would attest fewer units than
    the event carries. `prepare` refuses that itself rather than relying on
    each caller to have checked."""
    twice = (RawUnit(seq=1, content="a"), RawUnit(seq=1, content="b"))
    with pytest.raises(InvalidPayload, match=r"^unit 1: seq is not unique within the event$"):
        prepare(kind="observation", occurred_at=OCCURRED, payload=PAYLOAD, units=twice, key=None)


def test_prepare_refuses_what_the_canonical_form_refuses() -> None:
    """The path in the message runs from the payload, as {ref}`payload-range`
    documents it, and not from the header the version 2 digest wraps it in."""
    with pytest.raises(InvalidPayload, match=r"^\$\.amount: floating point"):
        prepare(
            kind="observation",
            occurred_at=OCCURRED,
            payload={"amount": 1.5},
            units=UNITS,
            key=None,
        )


def test_prepare_mixes_the_references_in_and_keeps_the_distinct_hashes() -> None:
    """The references go into the payload under `blobs`, in the order given
    and each with its four keys, before the payload is hashed — so the digest
    covers them ({ref}`blobs`). The hashes for the register are the distinct
    ones, as bytes and ascending: the same content twice is one row there."""
    second = "b" * 64
    first = "a" * 64
    references = (
        BlobRef(sha256=second, size=3, media_type="text/plain", filename="b.txt"),
        BlobRef(sha256=first, size=0, media_type="application/octet-stream"),
        BlobRef(sha256=second, size=3, media_type="text/plain", filename="copy of b.txt"),
    )
    prepared = prepare(
        kind="observation",
        occurred_at=OCCURRED,
        payload=PAYLOAD,
        units=UNITS,
        key=None,
        blobs=references,
    )
    assert prepared.payload == {
        **PAYLOAD,
        "blobs": [
            {"sha256": second, "size": 3, "media_type": "text/plain", "filename": "b.txt"},
            {
                "sha256": first,
                "size": 0,
                "media_type": "application/octet-stream",
                "filename": None,
            },
            {"sha256": second, "size": 3, "media_type": "text/plain", "filename": "copy of b.txt"},
        ],
    }
    assert prepared.payload_digest == payload_hash_v2(prepared.payload, prepared.payload_salt)
    assert prepared.blobs == (bytes.fromhex(first), bytes.fromhex(second))
    # Without references, neither the key nor a hash.
    bare = _prepared()
    assert "blobs" not in bare.payload
    assert bare.blobs == ()
    # And the reader gives back what was mixed in, in its order.
    assert read_references(prepared.payload) == references
    assert read_references(bare.payload) == ()


_GOOD: dict[str, object] = {
    "sha256": "a" * 64,
    "size": 1,
    "media_type": "text/plain",
    "filename": None,
}


@pytest.mark.parametrize(
    ("field", "value", "problem"),
    [
        ("sha256", "A" * 64, "sha256 is not 64 hexadecimal characters, lower case"),
        ("sha256", 7, "sha256 is not 64 hexadecimal characters, lower case"),
        ("size", True, "size is not an integer"),
        ("size", "1", "size is not an integer"),
        ("size", -1, "size must be at least 0, is -1"),
        ("media_type", "", "media_type is empty"),
        ("media_type", 3, "media_type is not a string"),
        ("filename", 3, "filename is not a string"),
        ("filename", "", "filename is not a name without a directory"),
        ("filename", "..", "filename is not a name without a directory"),
        ("filename", "notes/a.txt", "filename is not a name without a directory"),
    ],
)
def test_prepare_refuses_what_read_references_refuses(
    field: str, value: object, problem: str
) -> None:
    """Fix round 1 of task 6, the 2026-10-04 stage 1c plan: writer and
    reader share one set of checks, so that `prepare` writes no reference
    that `read_references` would refuse. Each case is refused on both
    sides; a library caller can hand `prepare` what the annotations of
    `BlobRef` do not allow, and the casts below are that caller."""
    fields: dict[str, object] = {**_GOOD, field: value}
    reference = BlobRef(
        sha256=cast("str", fields["sha256"]),
        size=cast("int", fields["size"]),
        media_type=cast("str", fields["media_type"]),
        filename=cast("str | None", fields["filename"]),
    )
    with pytest.raises(InvalidPayload) as caught:
        prepare(
            kind="observation",
            occurred_at=OCCURRED,
            payload=PAYLOAD,
            units=UNITS,
            key=None,
            blobs=(reference,),
        )
    assert str(caught.value) == f"blob reference 0: {problem}"
    assert read_references({"blobs": [fields]}) is None


@pytest.mark.parametrize(
    "listed",
    [
        "not a list",
        ["a" * 64],
        [{k: v for k, v in _GOOD.items() if k != "filename"}],
        [{**_GOOD, "extra": 1}],
        [{**_GOOD, "sha256": "A" * 64}],
        [{**_GOOD, "sha256": 7}],
        [{**_GOOD, "size": True}],
        [{**_GOOD, "size": -1}],
        [{**_GOOD, "size": "1"}],
        [{**_GOOD, "media_type": ""}],
        [{**_GOOD, "filename": 3}],
        [_GOOD, {**_GOOD, "size": -1}],
    ],
    ids=[
        "not-a-list",
        "a-bare-hash",
        "a-key-missing",
        "a-key-too-many",
        "upper-case-hash",
        "hash-not-text",
        "size-a-boolean",
        "size-negative",
        "size-text",
        "media-type-empty",
        "filename-not-text",
        "the-second-broken",
    ],
)
def test_read_references_refuses_a_list_prepare_does_not_write(listed: object) -> None:
    """What comes back out of the store may have been written by anyone, so
    the reader takes only the form `prepare` writes and says `None` for any
    other — `verify` reports that, and `show` prints no line for it."""
    assert read_references({"blobs": listed}) is None
