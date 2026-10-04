# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle: one row per unit, each with its source attribution.

A denormalization over four tables — `event`, `unit`, `source_key` and the
payload for the kind of evidence — cut to the question "what happened, line
by line, and how do I know". That is what makes it a projection and not a
copy of `log` ({ref}`projections`).
"""

from __future__ import annotations

from dataclasses import dataclass
from previously.contract.rows import ChronicleRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def _evidence(payload: Mapping[str, object] | None) -> str | None:
    """The kind of evidence out of the payload, or None for a tombstone.

    `append` mixes it in under the reserved key ({ref}`canonicalization`);
    a value that is not a string is not one this projection can name.
    """
    if payload is None:
        return None
    value = payload.get("evidence")
    return value if isinstance(value, str) else None


def derive(batch: Batch) -> list[ChronicleRow]:
    rows: list[ChronicleRow] = []
    for event in batch.events:
        key = batch.keys.get(event.id)
        evidence = _evidence(event.payload)
        for unit in batch.units.get(event.id, ()):
            rows.append(
                ChronicleRow(
                    event_id=event.id,
                    seq=unit.seq,
                    content=unit.content,
                    occurred_at=event.occurred_at,
                    kind=event.kind,
                    evidence=evidence,
                    source=None if key is None else key[0],
                    external_id=None if key is None else key[1],
                    speaker=unit.speaker,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                )
            )
    return rows


@dataclass(frozen=True)
class ChronicleProjection:
    """Name and version as `projection_state` knows them, and the write step.

    A frozen dataclass rather than module constants, so a test can say
    `ChronicleProjection(version=2)` to force a rebuild without touching this
    module.
    """

    name: str = "chronicle"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        store.insert_chronicle(conn, derive(batch))


CHRONICLE = ChronicleProjection()
