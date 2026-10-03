# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hashes for payload, units and event (§3.1 of the 1a spec).

The event hash goes over a **canonicalised object**, not over a concatenation
of the fields: concatenation is ambiguous, because `"ab"+"c"` and `"a"+"bc"`
yield the same byte stream. `v` and `domain` fence off the range and turn a
future change of format into a version bump instead of a silent break.

Payload and units go in as a **hash**, not as content — that is the erasure
seam: once `payload` becomes a tombstone, the event hash stays valid, and the
same holds for the units as soon as `unit.content` may be `NULL`.

The source attribution (`source`, `external_id`) and the units digest arrived
with correction K1. Before that the event hash did not cover them, and three
permanent forgeries — the content of a unit rewritten, a unit deleted, the
source faked — ran, as measured, silently through `verify`.
"""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

HASH_VERSION = 1
HASH_DOMAIN = "previously/event"

# An own range identifier for the units, for the same reason `HASH_DOMAIN`
# exists: a units digest must not be able to pass as an event digest, not even
# by accident and not through a future caller who mixes up the two.
UNITS_DOMAIN = "previously/units"


def iso_utc(moment: datetime) -> str:
    """The canonical form of a timestamp: UTC, six fractional digits, `Z`."""
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise InvalidPayload("timestamp without time zone — local time would not be reproducible")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def payload_hash(payload: Mapping[str, object]) -> bytes:
    return hashlib.sha256(canonical(payload)).digest()


class HashableUnit(Protocol):
    """What `units_hash` needs of a unit — structurally, not nominally.

    Two types carry the same five fields: `contract.types.RawUnit` on the way
    in and `storage.rows.UnitRow` on the way out. `append` hashes the one,
    `verify` the other, and both must yield the same digest. A protocol holds
    the two directions together without `core.hashing` having to import
    either of the two types — the definition of the hash is then independent
    of where a unit comes from.

    Read-only properties, no mutable attributes: `RawUnit` and `UnitRow` are
    frozen dataclasses, and a protocol with writable attributes would not
    match them.
    """

    @property
    def seq(self) -> int: ...
    @property
    def content(self) -> str: ...
    @property
    def start_ms(self) -> int | None: ...
    @property
    def end_ms(self) -> int | None: ...
    @property
    def speaker(self) -> str | None: ...


def units_hash(units: Sequence[HashableUnit]) -> bytes:
    """Digest over the **whole** set of units of an event.

    Over the whole set, not per unit: a deleted unit is the forgery that no
    individual comparison finds — what is missing cannot be checked against
    itself.

    **Ascending by `seq`**, and sorted here, not at the caller: the order goes
    into the hash, so it has to be settled. `storage.units` already reads
    sorted by `seq`, but a connector may hand its units over in any order.
    Without the sorting at this one place, `append` hashed the connector's
    order and `verify` the `seq` order — and the check reported a forgery on
    an intact chain.

    All five fields go in, the ones that are always empty in stage 1a
    included (`start_ms`, `end_ms`, `speaker`): they stand in the table and
    are therefore forgeable. A transcript from stage 2 on carries real values
    there — were they not in the hash, "who said that, and when" would remain
    unattested.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION,
        "domain": UNITS_DOMAIN,
        "units": [
            {
                "seq": unit.seq,
                "content": unit.content,
                "start_ms": unit.start_ms,
                "end_ms": unit.end_ms,
                "speaker": unit.speaker,
            }
            for unit in sorted(units, key=lambda u: u.seq)
        ],
    }
    return hashlib.sha256(canonical(header)).digest()


def event_hash(
    *,
    event_id: int,
    kind: str,
    recorded_at: datetime,
    occurred_at: datetime,
    prev_hash: bytes | None,
    payload_digest: bytes,
    units_digest: bytes,
    source: str | None,
    external_id: str | None,
) -> bytes:
    """The event hash after §3.1.

    `source` and `external_id` are hashed as `null` when no idempotency key
    exists: `insert_event` permits `key=None`, and `assertion`/`action` carry
    none at all (§5). That stays unambiguous — an event that was written
    *with* a key hashes the values; should the row disappear later, `verify`
    reads `null`, the hash does not match, and there is a finding. An event
    that was keyless from the start hashes `null` and reads `null`.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION,
        "domain": HASH_DOMAIN,
        "id": event_id,
        "kind": kind,
        "recorded_at": iso_utc(recorded_at),
        "occurred_at": iso_utc(occurred_at),
        "prev": prev_hash.hex() if prev_hash is not None else None,
        "payload": payload_digest.hex(),
        "units": units_digest.hex(),
        "source": source,
        "external_id": external_id,
    }
    return hashlib.sha256(canonical(header)).digest()
