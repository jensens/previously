# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erasing an event or units of it: the second write path ({ref}`erasure`).

An erasure is a redaction event and the tombstones it orders, written in
**one** transaction: the order without its execution, or the execution
without its order, would each be a finding of `verify`. The redaction joins
the chain the way `append` joins it, through `chain.prepare` and `chain.link`
on the tip it read, and a lost chain position is retried the way `append`
retries it ({ref}`concurrency`).

What `append` does not need is the lock. Two erasures of the same target have
to run one after the other, so that the second sees what the first wrote and
writes nothing; the target's row is therefore locked first, and the
redactions are read only once the lock is held. The lock is on the target,
never on the tip: the chain position stays the unique indexes' to decide.
"""

from dataclasses import dataclass
from previously.core.append import backoff_delay
from previously.core.append import MAX_RETRIES
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import ChainConflict
from previously.core.errors import RedactionRefused
from previously.core.hashing import HASH_VERSION_1
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import iso_utc
from previously.core.redaction import event_payload
from previously.core.redaction import read_index
from previously.core.redaction import units_payload
from previously.storage.errors import ChainPositionTaken
from typing import TYPE_CHECKING

import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import EventRow
    from previously.contract.store import LogStore
    from previously.contract.store import RedactionStore


# A redaction is something the system does, not something a source reported:
# the kind `action`, with what kind of action it is in `payload.action`.
_KIND = "action"


@dataclass(frozen=True)
class Redacted:
    """What an erasure did.

    `written` is `False` when the target was already covered by a redaction
    and no event was written; `redaction_id` then names the redaction that
    covers it. The tombstones are set either way, so a call on a covered
    target finishes an erasure whose order stands and whose execution does
    not.
    """

    redaction_id: int
    written: bool
    # The units a redaction already covered, which this one does not name.
    skipped_units: tuple[int, ...] = ()


def _check_input(reason: str, recorded_at: datetime) -> None:
    # The form of a redaction demands a reason (`redaction.parse`), so an
    # empty one would be written as an action `verify` cannot read. Blanks
    # alone are no reason either: the reason is the brake on an erasure, and
    # one that says nothing brakes nothing.
    if not reason.strip():
        raise RedactionRefused("a redaction needs a reason, and the reason is empty")
    iso_utc(recorded_at)  # fail early if naive


def _target(row: EventRow | None, event_id: int) -> EventRow:
    """The locked target, or the refusal that says why there is none."""
    if row is None:
        raise RedactionRefused(f"there is no event {event_id}")
    # Every action this system writes is a redaction, so the kind decides. A
    # redaction's payload is what `verify` measures the tombstones against;
    # erasing it would leave them without their order.
    if row.kind == _KIND:
        raise RedactionRefused(
            f"event {event_id} is a redaction, and a redaction cannot be redacted"
        )
    return row


def _write[Conn](
    log: LogStore[Conn], conn: Conn, payload: Mapping[str, object], recorded_at: datetime
) -> int:
    """Appends the redaction event on the tip and returns its `id`.

    Prepared here, on every attempt, and not once before the first as
    `append` does: what the redaction names depends on the redactions read
    under the lock, and those can differ between two attempts. `occurred_at`
    is `recorded_at`, because an action of the system happens when it is
    recorded.
    """
    prepared = prepare(kind=_KIND, occurred_at=recorded_at, payload=payload, units=(), key=None)
    tip = log.tip(conn)
    row, units = link(
        prepared,
        event_id=1 if tip is None else tip.id + 1,
        prev_hash=None if tip is None else tip.hash,
        recorded_at=recorded_at,
    )
    log.insert_event(conn, row, units, None)
    return row.id


def _retrying[Conn](log: LogStore[Conn], once: Callable[[Conn], Redacted]) -> Redacted:
    """Runs `once` in a transaction of its own until it gets a chain position.

    The policy is `append`'s ({ref}`concurrency`): a lost chain position rolls
    the transaction back and the next attempt starts from the lock. The
    position is lost at `insert_event`, before any tombstone is set, so the
    rollback undoes the lock and nothing else. The tombstones are written by
    an attempt that got its position, or by one that needed none because a
    redaction already covers its target and it writes no event. Every other
    error rolls back as well and is not retried.
    """
    for attempt in range(MAX_RETRIES):
        try:
            with log.begin() as conn:
                return once(conn)
        except ChainPositionTaken:
            time.sleep(backoff_delay(attempt))
    raise ChainConflict(
        f"chain position not acquired after {MAX_RETRIES} attempts — "
        "under lasting contention the answer would be a single writing "
        "process, not a lock"
    )


def _seqs[Conn](log: LogStore[Conn], conn: Conn, event_id: int) -> list[int]:
    return [unit.seq for unit in log.units_by_event(conn, [event_id]).get(event_id, [])]


def redact_event[Conn](
    log: LogStore[Conn],
    eraser: RedactionStore[Conn],
    event_id: int,
    *,
    reason: str,
    recorded_at: datetime,
) -> Redacted:
    """Erases the payload of an event and the content of all its units.

    Two parameters for one store, the way `catch_up` takes two: Python has no
    intersection of two protocols, and the store that can erase is the store
    that holds the log.
    """
    _check_input(reason, recorded_at)

    def once(conn: Conn) -> Redacted:
        _target(eraser.lock_event(conn, event_id), event_id)
        # After the lock, never before: a second erasure of this target has
        # waited at the lock and now sees the redaction the first one wrote.
        covering = read_index(log, conn).of_event(event_id)
        if covering is None:
            payload = event_payload(event_id, blobs=(), reason=reason)
            redaction_id = _write(log, conn, payload, recorded_at)
        else:
            redaction_id = covering.id
        eraser.erase_payload(conn, event_id)
        eraser.erase_units(conn, event_id, _seqs(log, conn, event_id))
        return Redacted(redaction_id=redaction_id, written=covering is None)

    return _retrying(log, once)


def redact_units[Conn](
    log: LogStore[Conn],
    eraser: RedactionStore[Conn],
    event_id: int,
    seqs: Sequence[int],
    *,
    reason: str,
    recorded_at: datetime,
) -> Redacted:
    """Erases the content of the named units of a version 2 event.

    The units are ordered and each named once. A unit a redaction already
    covers is set to a tombstone again and not named again; it comes back in
    `skipped_units`. Is every named unit covered, nothing is written, and the
    result names the newest of the redactions that cover them.
    """
    _check_input(reason, recorded_at)
    wanted = sorted(set(seqs))
    if not wanted:
        raise RedactionRefused("a redaction of units needs at least one unit")

    def once(conn: Conn) -> Redacted:
        target = _target(eraser.lock_event(conn, event_id), event_id)
        # Version 1 attests all units of an event in one digest, so the units
        # left standing beside an erased one would be attested by nothing.
        if target.hash_version == HASH_VERSION_1:
            raise RedactionRefused(
                f"event {event_id} was written in hash format 1, which attests its "
                "units only together: use `previously redact event`"
            )
        # A format nobody knows says nothing about how its units are attested,
        # so nothing can be claimed about it either — `verify` reports such a
        # row as a finding of its own.
        if target.hash_version != HASH_VERSION_2:
            raise RedactionRefused(
                f"event {event_id} names hash format {target.hash_version}, which is not known"
            )
        present = set(_seqs(log, conn, event_id))
        for seq in wanted:
            if seq not in present:
                raise RedactionRefused(f"event {event_id} has no unit {seq}")
        index = read_index(log, conn)
        covering = {seq: index.of_unit(event_id, seq) for seq in wanted}
        skipped = tuple(seq for seq, by in covering.items() if by is not None)
        fresh = [seq for seq, by in covering.items() if by is None]
        if fresh:
            payload = units_payload(event_id, fresh, reason=reason)
            redaction_id = _write(log, conn, payload, recorded_at)
        else:
            redaction_id = max(by.id for by in covering.values() if by is not None)
        eraser.erase_units(conn, event_id, wanted)
        return Redacted(redaction_id=redaction_id, written=bool(fresh), skipped_units=skipped)

    return _retrying(log, once)
