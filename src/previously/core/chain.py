# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Building a version 2 event in two steps ({ref}`hash-version-2`).

`prepare` draws the salts and computes every digest that does not depend on
where the event lands in the chain. `link` computes what does: the event hash,
which names the `id` and the predecessor's hash. `append` calls `prepare` once
per event, before its first attempt, and `link` on every attempt, because a
lost race moves the event to another chain position and leaves its content as
it was.

Both are pure but for the randomness of the salts, and neither touches the
store.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.contract.rows import EventRow
from previously.contract.rows import UnitRow
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import new_salt
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash_v2
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence
    from previously.contract.types import RawUnit


@dataclass(frozen=True)
class PreparedUnit:
    """A unit with its salt and its digest, not yet assigned to an event."""

    seq: int
    content: str
    start_ms: int | None
    end_ms: int | None
    speaker: str | None
    salt: bytes
    digest: bytes


@dataclass(frozen=True)
class Prepared:
    """Everything about an event that stays the same across attempts."""

    kind: str
    occurred_at: datetime
    payload: Mapping[str, object]
    payload_salt: bytes
    payload_digest: bytes
    units: tuple[PreparedUnit, ...]
    units_digest: bytes
    key: tuple[str, str] | None


def prepare(
    *,
    kind: str,
    occurred_at: datetime,
    payload: Mapping[str, object],
    units: Sequence[RawUnit],
    key: tuple[str, str] | None,
) -> Prepared:
    """Draws one salt for the payload and one per unit, and computes the
    payload digest, every unit digest and the units digest over them.

    A fresh salt per call: the same content prepared twice gives two different
    digests. That is the point of the salt, and it is why `append` prepares
    an event once and keeps the result across its retries.

    Raises `InvalidPayload` for whatever the canonical form refuses, and for
    a `seq` that appears twice. That one is refused here although `append`
    refuses it earlier, because `prepare` has more than one caller: two units
    under one `seq` would leave one digest in the mapping the units digest is
    taken over, so the digest would attest fewer units than the event
    carries, and the store's primary key on `(event_id, seq)` would then
    refuse the second row with an exception from the driver.
    """
    # The payload on its own first, before any salt is drawn, so that a
    # refusal names its path from the payload. `payload_hash_v2` wraps the
    # payload in a header, and refusing there reads `$.payload.text` where the
    # reference documents `$.text` ({ref}`payload-range`) — measured on
    # 2026-10-04, when `test_cli.py` caught exactly that on a lone surrogate.
    canonical(payload)
    payload_salt = new_salt()
    payload_digest = payload_hash_v2(payload, payload_salt)
    prepared_units: list[PreparedUnit] = []
    seen: set[int] = set()
    for unit in units:
        if unit.seq in seen:
            raise InvalidPayload(f"unit {unit.seq}: seq is not unique within the event")
        seen.add(unit.seq)
        salt = new_salt()
        prepared_units.append(
            PreparedUnit(
                seq=unit.seq,
                content=unit.content,
                start_ms=unit.start_ms,
                end_ms=unit.end_ms,
                speaker=unit.speaker,
                salt=salt,
                digest=unit_digest(
                    seq=unit.seq,
                    content=unit.content,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                    speaker=unit.speaker,
                    salt=salt,
                ),
            )
        )
    return Prepared(
        kind=kind,
        occurred_at=occurred_at,
        payload=payload,
        payload_salt=payload_salt,
        payload_digest=payload_digest,
        units=tuple(prepared_units),
        units_digest=units_hash_v2({unit.seq: unit.digest for unit in prepared_units}),
        key=key,
    )


def link(
    prepared: Prepared,
    *,
    event_id: int,
    prev_hash: bytes | None,
    recorded_at: datetime,
) -> tuple[EventRow, list[UnitRow]]:
    """The rows for one chain position: the event hash over the prepared
    digests, the `id` and the predecessor's hash.

    Without a key, `source` and `external_id` go into the hash as `null`, as
    `event_hash_v2` describes.
    """
    source, external_id = prepared.key if prepared.key is not None else (None, None)
    row = EventRow(
        id=event_id,
        kind=prepared.kind,
        recorded_at=recorded_at,
        occurred_at=prepared.occurred_at,
        prev_hash=prev_hash,
        hash=event_hash_v2(
            event_id=event_id,
            kind=prepared.kind,
            recorded_at=recorded_at,
            occurred_at=prepared.occurred_at,
            prev_hash=prev_hash,
            payload_digest=prepared.payload_digest,
            units_digest=prepared.units_digest,
            source=source,
            external_id=external_id,
        ),
        payload_hash=prepared.payload_digest,
        units_hash=prepared.units_digest,
        payload=prepared.payload,
        hash_version=HASH_VERSION_2,
        payload_salt=prepared.payload_salt,
    )
    units = [
        UnitRow(
            event_id=event_id,
            seq=unit.seq,
            content=unit.content,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            speaker=unit.speaker,
            digest=unit.digest,
            salt=unit.salt,
        )
        for unit in prepared.units
    ]
    return row, units
