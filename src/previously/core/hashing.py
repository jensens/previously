# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hashes for payload, units and event ({ref}`hash-format`).

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

from datetime import datetime
from datetime import UTC
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload
from typing import Protocol
from typing import TYPE_CHECKING

import hashlib
import secrets


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

# Two formats stand side by side ({ref}`hash-version-2`). Version 1 is what
# every event written before stage 1c carries, and it stays verifiable for
# good; version 2 is the one new events are meant to be written in. The check
# must compute the version a row was written in and no other, so the row has
# to name it; until it can, every row is version 1, because nothing calls the
# version 2 functions yet.
HASH_VERSION_1 = 1
HASH_VERSION_2 = 2
# The version new events are meant to be written in. Nothing reads this name
# in order to verify.
HASH_VERSION = HASH_VERSION_2
HASH_DOMAIN = "previously/event"

# An own range identifier for the units, for the same reason `HASH_DOMAIN`
# exists: a units digest must not be able to pass as an event digest, not even
# by accident and not through a future caller who mixes up the two.
UNITS_DOMAIN = "previously/units"

# Version 2 hashes the payload and each unit under a range of its own, for the
# reason the two above exist: no digest may pass for one of another kind.
PAYLOAD_DOMAIN = "previously/payload"
UNIT_DOMAIN = "previously/unit"

# 32 random bytes go into every version 2 digest over content, and they are
# erased together with that content ({ref}`hash-version-2`): a digest that
# stays behind must not let anybody guess what it was computed from.
SALT_BYTES = 32


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
    in and `contract.rows.UnitRow` on the way out. `append` hashes the one,
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
        "v": HASH_VERSION_1,
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
    """The event hash as {ref}`hash-format` defines it.

    `source` and `external_id` are hashed as `null` when no idempotency key
    exists: `insert_event` permits `key=None`, and `assertion`/`action` carry
    none at all ({ref}`hash-chain`). That stays unambiguous — an event that
    was written *with* a key hashes the values; should the row disappear
    later, `verify` reads `null`, the hash does not match, and there is a
    finding. An event that was keyless from the start hashes `null` and reads
    `null`.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION_1,
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


def new_salt() -> bytes:
    """A fresh salt out of the operating system's random source.

    `secrets` and not `random`: the salt is all that stands between a digest
    left behind by an erasure and whoever tries candidates against it.
    """
    return secrets.token_bytes(SALT_BYTES)


def payload_hash_v2(payload: Mapping[str, object], salt: bytes) -> bytes:
    """The payload digest of version 2: version, range and salt around the
    payload, where version 1 hashed the payload and nothing else."""
    header: Mapping[str, object] = {
        "v": HASH_VERSION_2,
        "domain": PAYLOAD_DOMAIN,
        "salt": salt.hex(),
        "payload": payload,
    }
    return hashlib.sha256(canonical(header)).digest()


def unit_digest(
    *,
    seq: int,
    content: str,
    start_ms: int | None,
    end_ms: int | None,
    speaker: str | None,
    salt: bytes,
) -> bytes:
    """The digest of one unit, the piece version 1 does not have.

    Keyword arguments and no protocol like `HashableUnit`: a stored unit may
    have lost its content to an erasure, and such a unit has nothing to
    compute a digest from. The caller settles that before it calls, and the
    type of `content` says so.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION_2,
        "domain": UNIT_DOMAIN,
        "salt": salt.hex(),
        "seq": seq,
        "content": content,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "speaker": speaker,
    }
    return hashlib.sha256(canonical(header)).digest()


def units_hash_v2(digests: Mapping[int, bytes]) -> bytes:
    """The units digest of version 2: over the unit digests, not the contents.

    That is what lets one unit be erased while the others stay attested: the
    erased unit keeps its digest, so this digest can still be computed.

    A mapping from `seq` to digest, sorted here for the reason `units_hash`
    sorts: the order goes into the hash. `seq` is not repeated in the list,
    because every unit digest already covers its own.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION_2,
        "domain": UNITS_DOMAIN,
        "units": [digests[seq].hex() for seq in sorted(digests)],
    }
    return hashlib.sha256(canonical(header)).digest()


def event_hash_v2(
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
    """The event hash of version 2: the fields of `event_hash`, under `"v": 2`.

    A function of its own and not a `version` parameter on `event_hash`, so
    that the version 1 function and its pinned vector stay untouched, and so
    that no caller gets version 1 by leaving an argument out.
    """
    header: Mapping[str, object] = {
        "v": HASH_VERSION_2,
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
