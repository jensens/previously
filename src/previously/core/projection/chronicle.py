# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle: one row per unit, each with its source attribution.

A denormalization over four tables — `event`, `unit`, `source_key` and the
payload for the kind of evidence — cut to the question "what happened, line
by line, and how do I know". That is what makes it a projection and not a
copy of `log` ({ref}`projections`).

It follows an erasure by two rules, and the two together are why the
incremental path and a rebuild end alike: a unit without content gives no
row, and a redaction deletes the rows of what it erased. A worker that reads
the target before its redaction builds the rows and deletes them when it
reads the redaction; one that reads it after builds none, and the deletion
meets nothing. A rebuild always goes the second way ({ref}`projections`).
"""

from dataclasses import dataclass
from previously.contract.rows import ChronicleRow
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
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
        # The chronicle tells what happened, line by line, as sources
        # reported it. An action is something the system did; its units (a
        # model call keeps its answer as units) are not a statement of a
        # source and would stand among them as one.
        if event.kind != "observation":
            continue
        key = batch.keys.get(event.id)
        evidence = _evidence(event.payload)
        for unit in batch.units.get(event.id, ()):
            # An erased unit gets no row: the chronicle shows what was said,
            # and of an erased unit nothing is left to show.
            if unit.content is None:
                continue
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


def erasures(batch: Batch) -> list[tuple[int, tuple[int, ...] | None]]:
    """What the redactions of a batch take out of the chronicle, in chain
    order: the event, and the units named or `None` for all of them.

    Only an event of kind `action` is read, the kind every redaction is
    written in. An action of another name takes nothing, and neither does one
    that cannot be read as a redaction: reporting that is the business of
    `verify`, as it is for `read_index`. A redaction of a blob takes nothing
    either, since the chronicle holds no blob; the events that use it keep
    their units.
    """
    out: list[tuple[int, tuple[int, ...] | None]] = []
    for event in batch.events:
        if event.kind != "action" or event.payload is None:
            continue
        # `parse` refuses an action of any other name as well, so another
        # kind of action takes nothing through the same `except`.
        try:
            redaction = parse(event.id, event.payload)
        except MalformedAction:
            continue
        # A redaction can only order the erasure of something before it in
        # the chain ({ref}`erasure`); one that names a later event is a
        # finding of `verify` and takes nothing here. Taken, it would
        # delete rows in a rebuild, where the target shares its batch, and
        # none on the incremental path, where the target came later.
        if redaction.event is None or redaction.event >= event.id:
            continue
        out.append((redaction.event, None if redaction.scope == "event" else redaction.units))
    return out


@dataclass(frozen=True)
class ChronicleProjection:
    """Name and version as `projection_state` knows them, and the write step.

    A frozen dataclass rather than module constants, so a test can say
    `ChronicleProjection(version=4)` to force a rebuild without touching this
    module.

    Version 2 since the chronicle reads redactions: a table version 1 built
    can still hold the rows of an erased unit, and the version is what makes
    the first catch-up of version 2 rebuild it.

    Version 3 since the chronicle shows observations only: a table version 2
    built can hold the rows of an action's units, and the version is what
    makes the first catch-up of version 3 rebuild it.
    """

    name: str = "chronicle"
    version: int = 3

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        # Insert first, then delete. A redaction that `redact` wrote finds
        # its target's units erased already, and the order makes no
        # difference to it. It does to a target that still carries what its
        # redaction erased — an order without its execution, which `verify`
        # reports: the redaction takes those rows whether it shares a batch
        # with its target or not, so the batch boundaries, which differ
        # between a catch-up and a rebuild, cannot change the result
        # (`test_an_order_without_its_execution_ends_alike_on_both_paths`).
        store.insert_chronicle(conn, derive(batch))
        for event_id, seqs in erasures(batch):
            store.delete_chronicle(conn, event_id, seqs)


CHRONICLE = ChronicleProjection()
