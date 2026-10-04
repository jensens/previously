# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Preparing and linking a version 2 event, without a database."""

from datetime import datetime
from datetime import UTC
from previously.contract.types import RawUnit
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import SALT_BYTES
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash_v2
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
