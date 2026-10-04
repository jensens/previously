# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Per-source statistics: the aggregate that puts the assurance to the test.

Counts are additive and `first_seen`/`last_seen` are extremes, and they can be
caught up incrementally **only because the log is append-only**: were a row
able to disappear, a minimum would need a rebuild, because a minimum does not
show whether its carrier still exists ({ref}`projections`).

The merge arithmetic is here and not in SQL. Done as `ON CONFLICT DO UPDATE
SET events = events + excluded.events, first_seen = least(…)` the
correctness of the incremental step would sit in `storage`, and the claim
"derivation without SQL" would be false. Here a unit test reaches it without a
database — and the one that matters is the late arrival that happened
earlier, where assignment and minimum part.
"""

from __future__ import annotations

from dataclasses import dataclass
from previously.contract.rows import SourceStatsRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def merge(existing: SourceStatsRow | None, addition: SourceStatsRow) -> SourceStatsRow:
    if existing is None:
        return addition
    return SourceStatsRow(
        source=existing.source,
        events=existing.events + addition.events,
        units=existing.units + addition.units,
        first_seen=min(existing.first_seen, addition.first_seen),
        last_seen=max(existing.last_seen, addition.last_seen),
        last_event_id=max(existing.last_event_id, addition.last_event_id),
    )


def derive(batch: Batch) -> dict[str, SourceStatsRow]:
    """The batch folded per source. Events without a source attribution do not
    count: there is no source to attribute them to. The chronicle shows them,
    this table does not — a decision, so it is written down."""
    out: dict[str, SourceStatsRow] = {}
    for event in batch.events:
        key = batch.keys.get(event.id)
        if key is None:
            continue
        source = key[0]
        addition = SourceStatsRow(
            source=source,
            events=1,
            units=len(batch.units.get(event.id, ())),
            first_seen=event.occurred_at,
            last_seen=event.occurred_at,
            last_event_id=event.id,
        )
        out[source] = merge(out.get(source), addition)
    return out


@dataclass(frozen=True)
class SourceStatsProjection:
    name: str = "source-stats"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        additions = derive(batch)
        if not additions:
            return
        existing = store.source_stats(conn, sorted(additions))
        store.upsert_source_stats(
            conn, [merge(existing.get(source), row) for source, row in sorted(additions.items())]
        )


SOURCE_STATS = SourceStatsProjection()
