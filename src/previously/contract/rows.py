# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rows, not domain objects — the field contract between `core` and `storage`.

`storage` does not know the domain ({ref}`module-boundaries`): `kind` is
text, `payload` is uninterpreted JSON. That is why the type is called
`EventRow` and not `Event` — `core` interprets, `storage` transports.

These types live in `contract` and not in `storage` because the store
protocols in `contract.store` name them, and `contract` is the bottom layer:
it may import nothing above it. Measured on 2026-10-04 against
`.importlinter` — a `contract -> storage` import breaks the `layers` contract.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Tip:
    """Tip of the chain: both values come out of a single SELECT."""

    id: int
    hash: bytes


@dataclass(frozen=True)
class EventRow:
    id: int
    kind: str
    recorded_at: datetime
    occurred_at: datetime
    prev_hash: bytes | None
    hash: bytes
    payload_hash: bytes
    # Digest over the units of the event (`unit`), mirroring payload_hash:
    # the digest stands in the row, the content in its own table.
    units_hash: bytes
    payload: Mapping[str, object] | None
    # The hash format the row was written in ({ref}`hash-version-2`), and the
    # salt of its payload digest in version 2. The defaults mirror the
    # columns: a row that says nothing is version 1, which has no salt.
    hash_version: int = 1
    payload_salt: bytes | None = None


@dataclass(frozen=True)
class UnitRow:
    event_id: int
    seq: int
    # `None` is the tombstone of an erased unit.
    content: str | None
    start_ms: int | None = None
    end_ms: int | None = None
    speaker: str | None = None
    # The unit's own digest and its salt, both version 2 only
    # ({ref}`hash-version-2`); `None` on a version 1 unit.
    digest: bytes | None = None
    salt: bytes | None = None


@dataclass(frozen=True)
class ProjectionState:
    """One row of `projection_state`: how far a projection has been built."""

    name: str
    up_to_id: int
    version: int
    built_at: datetime


@dataclass(frozen=True)
class TipAndBookmark:
    """The two numbers a lag is the difference of, read in one statement.

    Not a lag: the difference is formed where it is printed, because the
    reading command decides what to do with a zero. Each number is 0 in its
    own empty case: `tip_id` when the log is empty, `up_to_id` when the
    projection has no state row yet — the reading of `up_to_id 0` is
    "nothing yet", so a missing state row and a state row at 0 give the same
    lag, which is the whole log.
    """

    tip_id: int
    up_to_id: int


@dataclass(frozen=True)
class ChronicleRow:
    event_id: int
    seq: int
    content: str
    occurred_at: datetime
    kind: str
    evidence: str | None
    source: str | None
    external_id: str | None
    speaker: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class SourceStatsRow:
    source: str
    events: int
    units: int
    first_seen: datetime
    last_seen: datetime
    last_event_id: int
