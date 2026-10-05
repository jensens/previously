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

The references to blobs are part of the content, so `prepare` mixes them
into the payload, and `read_references` reads them back out of a payload the
store returns ({ref}`blobs`).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.contract.rows import EventRow
from previously.contract.rows import UnitRow
from previously.contract.types import BlobRef
from previously.core.blob import is_address
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import new_salt
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash_v2
from typing import cast
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
    # The distinct hashes of the blobs the payload names, as bytes and
    # ascending: the rows of the blob register ({ref}`blobs`).
    blobs: tuple[bytes, ...] = ()


# The key the references go under. Reserved like `evidence`: a payload that
# already carries it is refused, so that it is not silently overwritten.
_BLOBS = "blobs"


def _references(blobs: Sequence[BlobRef]) -> list[dict[str, object]]:
    """The references as they stand in the payload, each with its four keys,
    in the order given. A reference that is not one is refused with its
    index, before anything is hashed or written."""
    references: list[dict[str, object]] = []
    for index, blob in enumerate(blobs):
        where = f"blob reference {index}"
        if not is_address(blob.sha256):
            raise InvalidPayload(f"{where}: sha256 is not 64 hexadecimal characters, lower case")
        if blob.size < 0:
            raise InvalidPayload(f"{where}: size must be at least 0, is {blob.size}")
        if not blob.media_type:
            raise InvalidPayload(f"{where}: media_type is empty")
        references.append(
            {
                "sha256": blob.sha256,
                "size": blob.size,
                "media_type": blob.media_type,
                "filename": blob.filename,
            }
        )
    return references


_REFERENCE_KEYS = frozenset({"sha256", "size", "media_type", "filename"})


def _read_reference(value: object) -> BlobRef | None:
    """One reference as `_references` writes it, or `None`."""
    if not isinstance(value, dict):
        return None
    fields = cast("dict[str, object]", value)
    if frozenset(fields) != _REFERENCE_KEYS:
        return None
    sha256, size = fields["sha256"], fields["size"]
    media_type, filename = fields["media_type"], fields["filename"]
    if not isinstance(sha256, str) or not is_address(sha256):
        return None
    # `bool` is a subclass of `int` in Python, and `true` in JSON is no size.
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        return None
    if not isinstance(media_type, str) or not media_type:
        return None
    if filename is not None and not isinstance(filename, str):
        return None
    return BlobRef(sha256=sha256, size=size, media_type=media_type, filename=filename)


def read_references(payload: Mapping[str, object]) -> tuple[BlobRef, ...] | None:
    """The references a stored payload names under `blobs`, in their order —
    none when it has no such key — or `None` when the list does not have the
    form `prepare` writes ({ref}`blobs`).

    For the readers of a payload that came back out of the store, where
    anything may stand: `verify` holds the register against it, and `show`
    prints it.
    """
    listed = payload.get(_BLOBS, [])
    if not isinstance(listed, list):
        return None
    references: list[BlobRef] = []
    for value in cast("list[object]", listed):
        reference = _read_reference(value)
        if reference is None:
            return None
        references.append(reference)
    return tuple(references)


def prepare(
    *,
    kind: str,
    occurred_at: datetime,
    payload: Mapping[str, object],
    units: Sequence[RawUnit],
    key: tuple[str, str] | None,
    blobs: Sequence[BlobRef] = (),
) -> Prepared:
    """Draws one salt for the payload and one per unit, and computes the
    payload digest, every unit digest and the units digest over them.

    A fresh salt per call: the same content prepared twice gives two different
    digests. That is the point of the salt, and it is why `append` prepares
    an event once and keeps the result across its retries.

    The references to blobs are mixed into the payload here, under `blobs`,
    and only when there are any, so that an event without attachments has the
    payload it had before blobs existed ({ref}`blobs`). Here and nowhere else:
    mixed in at two places — once for the digest, once for the row — the two
    could drift apart, for the reason `append` gives for `evidence`.

    Raises `InvalidPayload` for a payload that already carries `blobs`, for a
    reference that is not one, for whatever the canonical form refuses, and
    for a `seq` that appears twice. That one is refused here although `append`
    refuses it earlier, because `prepare` has more than one caller: two units
    under one `seq` would leave one digest in the mapping the units digest is
    taken over, so the digest would attest fewer units than the event
    carries, and the store's primary key on `(event_id, seq)` would then
    refuse the second row with an exception from the driver.
    """
    if _BLOBS in payload:
        raise InvalidPayload(
            f"payload already carries the key '{_BLOBS}' — it is reserved for the attachments"
        )
    if blobs:
        payload = {**payload, _BLOBS: _references(blobs)}
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
        blobs=tuple(sorted({bytes.fromhex(blob.sha256) for blob in blobs})),
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
