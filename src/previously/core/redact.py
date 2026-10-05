# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Erasing an event, units of it, or a blob: the second write path
({ref}`erasure`).

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

An erasure that touches a blob locks every event that uses the blob, in
ascending order, so that two erasures that share one wait for each other
instead of each concluding that the other's reference still stands, and
neither waits for the other in turn. What has to lie in the store
afterwards follows from `redaction.blob_expected`, and `Redacted` says it;
deleting is the caller's, after the transaction, since the store takes part
in none.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from previously.core.append import backoff_delay
from previously.core.append import MAX_RETRIES
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import ChainConflict
from previously.core.errors import InvalidPayload
from previously.core.errors import RedactionRefused
from previously.core.hashing import HASH_VERSION_1
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import is_address
from previously.core.hashing import iso_utc
from previously.core.redaction import blob_erasure
from previously.core.redaction import blob_expected
from previously.core.redaction import blob_payload
from previously.core.redaction import event_payload
from previously.core.redaction import parse
from previously.core.redaction import read_index
from previously.core.redaction import units_payload
from previously.storage.errors import ChainPositionTaken
from typing import cast
from typing import TYPE_CHECKING

import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import EventRow
    from previously.contract.store import LogStore
    from previously.contract.store import RedactionStore
    from previously.core.redaction import Redaction
    from previously.core.redaction import RedactionIndex


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
    # The blobs of the target that no longer have to lie in the store, and
    # the ones that stay, each with the events that still use it. Computed
    # by every call, the one that writes nothing included: that is what lets
    # a second call finish a deletion the first did not get to.
    obsolete_blobs: tuple[str, ...] = ()
    kept_blobs: Mapping[str, tuple[int, ...]] = field(default_factory=dict[str, tuple[int, ...]])


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


def _lock_ascending[Conn](
    eraser: RedactionStore[Conn], conn: Conn, event_ids: Iterable[int]
) -> dict[int, EventRow | None]:
    """Locks the rows of the events in ascending order, each once, and
    returns them. One order for every erasure, so that two that lock the same
    rows cannot each hold one the other waits for."""
    return {event_id: eraser.lock_event(conn, event_id) for event_id in sorted(set(event_ids))}


def _unerased(index: RedactionIndex, sha256: str, event_ids: Iterable[int]) -> tuple[int, ...]:
    """The events whose reference to the blob no redaction has erased."""
    return tuple(e for e in event_ids if index.of_reference(e, sha256) is None)


def _blobs_after[Conn](
    log: LogStore[Conn], conn: Conn, index: RedactionIndex, blobs: Iterable[str]
) -> tuple[tuple[str, ...], dict[str, tuple[int, ...]]]:
    """What the rule says of each blob once the redaction stands in `index`:
    obsolete, or kept with the events that still use it."""
    obsolete: list[str] = []
    kept: dict[str, tuple[int, ...]] = {}
    for sha256 in sorted(set(blobs)):
        users = log.events_by_blob(conn, bytes.fromhex(sha256))
        if blob_expected(index, sha256, users):
            kept[sha256] = _unerased(index, sha256, users)
        else:
            obsolete.append(sha256)
    return tuple(obsolete), kept


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
    """Erases the payload of an event and the content of all its units, and
    says which of the blobs it named no longer have to lie in the store.

    Two parameters for one store, the way `catch_up` takes two: Python has no
    intersection of two protocols, and the store that can erase is the store
    that holds the log.
    """
    _check_input(reason, recorded_at)

    def once(conn: Conn) -> Redacted:
        # The blobs the event names, out of the register, and every event
        # that shares one of them, both read before the lock. The register
        # rows of an event are written with it and never change, so the
        # first list is final. The second can grow while this runs, through
        # an append that names one of the blobs, and an event appended after
        # the read goes unlocked. That is still correct: its reference is
        # not erased, so the blob is kept for it (`_blobs_after` reads the
        # register again), and any erasure that touches that event later
        # locks every user of the blob, this target included, so the two
        # meet on a shared row.
        registered = [
            sha256.hex() for sha256 in log.blobs_by_event(conn, [event_id]).get(event_id, [])
        ]
        sharing = [
            e for sha256 in registered for e in log.events_by_blob(conn, bytes.fromhex(sha256))
        ]
        _target(_lock_ascending(eraser, conn, [event_id, *sharing])[event_id], event_id)
        # After the lock, never before: a second erasure of this target has
        # waited at the lock and now sees the redaction the first one wrote.
        index = read_index(log, conn)
        covering = index.of_event(event_id)
        if covering is None:
            # Once the payload is erased, the list of blobs in the redaction
            # is what attests them ({ref}`blobs`).
            payload = event_payload(event_id, blobs=registered, reason=reason)
            redaction_id = _write(log, conn, payload, recorded_at)
            index.add(parse(redaction_id, payload))
        else:
            redaction_id = covering.id
        eraser.erase_payload(conn, event_id)
        eraser.erase_units(conn, event_id, _seqs(log, conn, event_id))
        obsolete, kept = _blobs_after(log, conn, index, registered)
        return Redacted(
            redaction_id=redaction_id,
            written=covering is None,
            obsolete_blobs=obsolete,
            kept_blobs=kept,
        )

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


def redact_blob[Conn](
    log: LogStore[Conn],
    eraser: RedactionStore[Conn],
    sha256: str,
    *,
    reason: str,
    recorded_at: datetime,
) -> Redacted:
    """Erases a blob for every event that uses it now ({ref}`erasure`).

    The redaction names the events whose reference to the blob is not erased
    yet, and writes nothing when none is left; it then names the newest of
    the redactions that erased them. The payloads and units of the events
    stay as they are: the reference in them is the evidence that something
    was there. An event that names the same content later is not named, and
    its blob has to lie again.
    """
    _check_input(reason, recorded_at)
    if not is_address(sha256):
        raise InvalidPayload(
            f"{sha256} is not a blob address: 64 hexadecimal characters, lower case"
        )

    def once(conn: Conn) -> Redacted:
        users = log.events_by_blob(conn, bytes.fromhex(sha256))
        if not users:
            raise RedactionRefused(f"no event uses blob {sha256}")
        _lock_ascending(eraser, conn, users)
        index = read_index(log, conn)
        fresh = _unerased(index, sha256, users)
        if fresh:
            payload = blob_payload(sha256, fresh, reason=reason)
            redaction_id = _write(log, conn, payload, recorded_at)
            index.add(parse(redaction_id, payload))
        else:
            # Every reference is erased, so there is a redaction to name.
            redaction_id = cast("Redaction", blob_erasure(index, sha256, users)).id
        obsolete, kept = _blobs_after(log, conn, index, [sha256])
        return Redacted(
            redaction_id=redaction_id,
            written=bool(fresh),
            obsolete_blobs=obsolete,
            kept_blobs=kept,
        )

    return _retrying(log, once)
