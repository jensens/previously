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


@dataclass(frozen=True)
class UnitRow:
    event_id: int
    seq: int
    content: str
    start_ms: int | None = None
    end_ms: int | None = None
    speaker: str | None = None


@dataclass(frozen=True)
class ProjectionState:
    """One row of `projection_state`: how far a projection has been built."""

    name: str
    up_to_id: int
    version: int
    built_at: datetime


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
