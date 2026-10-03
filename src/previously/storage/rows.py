# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rows, not domain objects.

`storage` does not know the domain ({ref}`module-boundaries`): `kind` is
text, `payload` is uninterpreted JSON. That is why the type is called
`EventRow` and not `Event` — `core` interprets, `storage` transports.
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
