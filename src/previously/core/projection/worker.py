# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection worker ({ref}`projections`): batches, and the catch-up."""

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from datetime import UTC
from previously.contract.rows import EventRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import UnitRow
from previously.core.errors import ProjectionGap
from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import LogStore
    from previously.contract.store import ProjectionStore


@dataclass(frozen=True)
class Batch:
    """What one catch-up step reads from the log: a run of events in chain
    order with their units and source attributions, fetched by batch — one
    query each, not one per event, for the reason `units_by_event` and
    `source_keys` exist."""

    events: tuple[EventRow, ...]
    units: Mapping[int, Sequence[UnitRow]]
    keys: Mapping[int, tuple[str, str]]


class Projection(Protocol):
    """What the worker needs to know about a projection: its name as
    `projection_state` keys it, the version the code declares, and the write
    step. `write` is generic over the connection so that the protocol itself
    is not — a `Projection[Conn]` would be invariant in `Conn`, and a module
    constant could not be both `Projection[Connection]` and anything else.

    `name` and `version` are read-only properties, not attributes: the
    implementations are frozen dataclasses, whose fields pyright treats as
    read-only, and a protocol attribute `name: str` is mutable — the two
    would not match."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> int: ...

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None: ...


@dataclass(frozen=True)
class Outcome:
    """What one `catch_up` did, for the command line to say which path it
    took ({ref}`projections`): a version-triggered rebuild is otherwise
    invisible."""

    name: str
    version: int
    # None: an ordinary catch-up. 0: nothing existed, first build. n > 0: the
    # table was at version n and the code at another, so it was rebuilt.
    rebuilt_from: int | None
    events: int
    up_to_id: int


def catch_up[Conn](
    log: LogStore[Conn],
    store: ProjectionStore[Conn],
    projection: Projection,
    *,
    batch_size: int = 500,
) -> Outcome:
    """Brings one projection up to the tip of the log, in batches.

    **Rows and `up_to_id` move in one transaction or not at all.** An abort in
    the middle leaves a consistent partial projection, and the next run
    continues at `up_to_id + 1` — that is the whole reason `up_to_id` exists.
    One transaction over the whole log would be the opposite of that.

    `batch_size` is 500 for no stronger reason than that `MAX_BATCH` in
    `append` is 500 and one number is easier to keep than two. It is not
    load-bearing; the abort test sets it to 2 on purpose.

    Reading from `up_to_id + 1` skips nothing, because the log has no gaps:
    `id = predecessor.id + 1` and the unique index on `prev_hash` leave no
    room for one ({ref}`hash-chain`). With a sequence this would be the hard
    part — a transaction with id 41 can commit after one with id 42, and a
    worker that has seen 42 loses 41 for good.
    """
    if batch_size < 1:
        # A caller error, named as one. `LIMIT 0` would return an empty read
        # and the loop below would report a gap in the log that is not there.
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")

    rebuilt_from: int | None = None
    with store.begin() as conn:
        state = store.projection_state(conn, projection.name)
        if state is None or state.version != projection.version:
            # `!=` and not `<`: a rolled-back release derives differently from
            # the table it meets, in either direction.
            rebuilt_from = 0 if state is None else state.version
            store.truncate_projection(conn, projection.name)
            state = ProjectionState(projection.name, 0, projection.version, datetime.now(UTC))
            store.set_projection_state(conn, state)

    processed = 0
    while True:
        with store.begin() as conn:
            tip = log.tip(conn)
            if tip is None or tip.id <= state.up_to_id:
                break
            events = tuple(log.read(conn, from_id=state.up_to_id + 1, limit=batch_size))
            ids = [event.id for event in events]
            # The log has no gaps ({ref}`hash-chain`), so the batch has to be
            # exactly the next `len(ids)` identifiers. Checking only "not
            # empty" was measured insufficient on 2026-10-04: with id 5 deleted
            # by hand and `up_to_id` at 4, `read(from_id=5)` returns 6..10, and
            # a worker that only checks for emptiness projects them and sets
            # `up_to_id = 10` — the silent loss this error exists to refuse.
            expected = list(range(state.up_to_id + 1, state.up_to_id + 1 + len(ids)))
            if ids != expected:
                raise ProjectionGap(
                    f"expected events {expected[:1]}.. above id {state.up_to_id}, "
                    f"read {ids[:3]}{'…' if len(ids) > 3 else ''}; the tip is {tip.id}"
                )
            batch = Batch(
                events=events,
                units=log.units_by_event(conn, ids),
                keys=log.source_keys(conn, ids),
            )
            projection.write(store, conn, batch)
            state = replace(state, up_to_id=events[-1].id, built_at=datetime.now(UTC))
            store.set_projection_state(conn, state)
            processed += len(events)

    return Outcome(
        name=projection.name,
        version=projection.version,
        rebuilt_from=rebuilt_from,
        events=processed,
        up_to_id=state.up_to_id,
    )
