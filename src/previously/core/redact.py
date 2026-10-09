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

An erasure reaches further than its target when a `model_call` read it. The
result of that call is derived from what was erased, so the call's units are
erased with it, by a redaction of their own in the same transaction
({ref}`erasure`).

The calls are found first, from a read of every action, and then locked in
**one** ascending round together with the targets, before any chain position
is taken. That order is what keeps two concurrent erasures from deadlocking:
the other order, locking the target, taking a position for the redaction and
only then locking the calls, lets erasure A of an event and erasure B of a call
that read it meet in a cycle. A holds the event and waits for the call's row,
which B holds, and B waits for the chain position A took. With one round, B
waits at the row lock of the call before it has taken any position, and A
cannot be waiting for B. A call appended after the read goes unlocked and
uncascaded, the same race between reading and erasing that the blob section
above names; a later erasure of the same target finds the call.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from previously.core.action import MODEL_CALL
from previously.core.action import REDACTION
from previously.core.action import retrying
from previously.core.action import write_action
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
from previously.core.units import normalize_line_endings
from typing import cast
from typing import TYPE_CHECKING


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


# A redaction is an action of the system ({ref}`erasure`): the kind `action`.
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
    # Whether the payload of the target holds the wording of a unit this
    # erasure of units erased: some string in it, at any depth, contains the
    # content of one of those units. A redaction of units leaves the payload
    # as it is, so that wording can still be read there afterwards. Decided
    # under the lock, from the units as they were read before they were
    # erased; that is a fact about the target, and the command line says what
    # follows from it.
    payload_holds_wording: bool = False
    # The `model_call` events whose units this erasure erased with it, because
    # the call read what was erased. Empty when no call did, or when the
    # units of every such call were gone already.
    cascaded: tuple[int, ...] = ()


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
    # Only a redaction is refused: its payload is what `verify` measures the
    # tombstones against, and erasing it would leave them without their
    # order. The other actions can be erased, a policy event (it then counts
    # as nothing, like a revocation) and a `model_call` (its payload is the
    # record of a call, and the cascade erases its units the same way). The
    # name decides and not the kind: the kind `action` holds all three. An
    # action whose payload is already gone was erased by a redaction, so it
    # is no redaction itself.
    if row.kind == _KIND and row.payload is not None and row.payload.get("action") == REDACTION:
        raise RedactionRefused(
            f"event {event_id} is a redaction, and a redaction cannot be redacted"
        )
    return row


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


def _reads(payload: Mapping[str, object], wanted: Callable[[Mapping[str, object]], bool]) -> bool:
    """Whether an entry of the `inputs` of a `model_call` is one `wanted`
    accepts. An entry that is not an object is skipped: `verify` reports a
    call whose `inputs` are malformed."""
    inputs = payload.get("inputs")
    if not isinstance(inputs, list):
        return False
    return any(
        wanted(cast("Mapping[str, object]", entry))
        for entry in cast("list[object]", inputs)
        if isinstance(entry, dict)
    )


def _calls[Conn](
    log: LogStore[Conn], conn: Conn, wanted: Callable[[Mapping[str, object]], bool]
) -> list[int]:
    """The ids of the `model_call` events that read what `wanted` accepts,
    ascending. Found by reading every action, which is fine for a pilot and
    the cost an index would remove. The read is not under a lock: the caller
    locks the calls together with its targets before it writes anything."""
    return [
        row.id
        for row in log.read_by_kind(conn, _KIND)
        if row.payload is not None
        and row.payload.get("action") == MODEL_CALL
        and _reads(row.payload, wanted)
    ]


def _cascade[Conn](
    log: LogStore[Conn],
    eraser: RedactionStore[Conn],
    conn: Conn,
    calls: Iterable[int],
    *,
    trigger: int,
    recorded_at: datetime,
) -> tuple[int, ...]:
    """Erases the units of the `calls` (already locked, see `_calls`) that
    still have content, and returns the ids of those calls.

    One redaction of units per call, naming the units that still have
    content: a call whose units are all gone gets none, which is what makes
    the second erasure of a target write nothing. The units are read here,
    under the lock, so a second erasure that waited finds them erased.
    """
    ids = sorted(set(calls))
    held = log.units_by_event(conn, ids)
    cascaded: list[int] = []
    for call_id in ids:
        live = [unit.seq for unit in held.get(call_id, []) if unit.content is not None]
        if not live:
            continue
        payload = units_payload(call_id, live, reason=f"cascade of redaction {trigger}")
        write_action(log, conn, payload, (), recorded_at=recorded_at)
        eraser.erase_units(conn, call_id, live)
        cascaded.append(call_id)
    return tuple(cascaded)


def _entry_event(entry: Mapping[str, object]) -> object:
    return entry.get("event")


def _entry_list(entry: Mapping[str, object], key: str) -> list[object]:
    value = entry.get(key)
    return cast("list[object]", value) if isinstance(value, list) else []


def _seqs[Conn](log: LogStore[Conn], conn: Conn, event_id: int) -> list[int]:
    return [unit.seq for unit in log.units_by_event(conn, [event_id]).get(event_id, [])]


def _holds_any(value: object, wordings: Sequence[str]) -> bool:
    """Whether a string anywhere in `value` — nested objects and arrays
    included — contains one of `wordings`. Only the values are searched: a
    key is limited to `^[a-z][a-z0-9_]*$` ({ref}`payload-range`), and it
    names a field rather than holding what somebody wrote.

    The line endings of each string are normalized before the comparison,
    the way `split_plaintext` normalizes a text before it splits it: a
    payload that keeps a text with CRLF endings, as e-mail has them, holds
    the line breaks inside a paragraph as `\\r\\n`, and the unit made from
    that paragraph holds them as `\\n`. The one caller, `redact_units`,
    passes `wordings` normalized the same way. The split changes
    nothing else inside a paragraph: it cuts at blank lines and strips the
    edges of each part, and a search for a substring is not hurt by either.
    """
    if isinstance(value, str):
        text = normalize_line_endings(value)
        return any(wording in text for wording in wordings)
    if isinstance(value, Mapping):
        return any(
            _holds_any(item, wordings) for item in cast("Mapping[str, object]", value).values()
        )
    if isinstance(value, list):
        return any(_holds_any(item, wordings) for item in cast("list[object]", value))
    return False


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
        # the read goes unlocked. If that event commits before `_blobs_after`
        # reads the register again, its reference is not erased and the blob
        # is kept for it. If it commits later, this erasure does not see it
        # and deletes the blob it names: the race between attaching and
        # erasing that {ref}`concurrency` names, which no lock here prevents.
        # A later `redact event` or `redact blob` that touches that event
        # locks every user of the blob, this target included, so those two
        # meet on a shared row; `redact units` locks only its target and the calls, and
        # erases no reference.
        registered = [
            sha256.hex() for sha256 in log.blobs_by_event(conn, [event_id]).get(event_id, [])
        ]
        sharing = [
            e for sha256 in registered for e in log.events_by_blob(conn, bytes.fromhex(sha256))
        ]
        calls = _calls(log, conn, lambda entry: _entry_event(entry) == event_id)
        _target(_lock_ascending(eraser, conn, [event_id, *sharing, *calls])[event_id], event_id)
        # After the lock, never before: a second erasure of this target has
        # waited at the lock and now sees the redaction the first one wrote.
        index = read_index(log, conn)
        covering = index.of_event(event_id)
        if covering is None:
            # Once the payload is erased, the list of blobs in the redaction
            # is what attests them ({ref}`blobs`).
            payload = event_payload(event_id, blobs=registered, reason=reason)
            redaction_id = write_action(log, conn, payload, (), recorded_at=recorded_at)
            index.add(parse(redaction_id, payload))
        else:
            redaction_id = covering.id
        eraser.erase_payload(conn, event_id)
        eraser.erase_units(conn, event_id, _seqs(log, conn, event_id))
        cascaded = _cascade(log, eraser, conn, calls, trigger=redaction_id, recorded_at=recorded_at)
        obsolete, kept = _blobs_after(log, conn, index, registered)
        return Redacted(
            redaction_id=redaction_id,
            written=covering is None,
            obsolete_blobs=obsolete,
            kept_blobs=kept,
            cascaded=cascaded,
        )

    # `retrying` is `append`'s policy ({ref}`concurrency`). The position is
    # lost at `insert_event`, before any tombstone is set, so the rollback of a
    # lost attempt undoes the lock and nothing else. The tombstones are written
    # by an attempt that got its position, or by one that needed none because
    # a redaction already covers its target and it writes no event. The
    # cascade takes positions of its own, after the tombstones of the target;
    # a position lost there rolls the whole transaction back, so the next
    # attempt starts from the top and the cascade is never half written.
    return retrying(log, once)


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
        calls = _calls(
            log,
            conn,
            lambda entry: (
                _entry_event(entry) == event_id
                and any(seq in _entry_list(entry, "units") for seq in wanted)
            ),
        )
        target = _target(_lock_ascending(eraser, conn, [event_id, *calls])[event_id], event_id)
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
        units = log.units_by_event(conn, [event_id]).get(event_id, [])
        present = {unit.seq for unit in units}
        for seq in wanted:
            if seq not in present:
                raise RedactionRefused(f"event {event_id} has no unit {seq}")
        # The wording of the named units, read before they are erased below,
        # with its line endings normalized as `_holds_any` normalizes the
        # payload's. A unit already erased has no content left to compare, so
        # when every named unit is erased already there is nothing to look
        # for, and `payload_holds_wording` is `False` although the payload may
        # still hold that wording: the gone content cannot be compared, and
        # the call that erased it is the one that could say so. An empty
        # content is left out too: every string contains it, and it holds
        # nothing that could still be read.
        wordings = [
            normalize_line_endings(unit.content)
            for unit in units
            if unit.seq in wanted and unit.content
        ]
        index = read_index(log, conn)
        covering = {seq: index.of_unit(event_id, seq) for seq in wanted}
        skipped = tuple(seq for seq, by in covering.items() if by is not None)
        fresh = [seq for seq, by in covering.items() if by is None]
        if fresh:
            payload = units_payload(event_id, fresh, reason=reason)
            redaction_id = write_action(log, conn, payload, (), recorded_at=recorded_at)
        else:
            redaction_id = max(by.id for by in covering.values() if by is not None)
        eraser.erase_units(conn, event_id, wanted)
        cascaded = _cascade(log, eraser, conn, calls, trigger=redaction_id, recorded_at=recorded_at)
        return Redacted(
            redaction_id=redaction_id,
            written=bool(fresh),
            skipped_units=skipped,
            payload_holds_wording=_holds_any(target.payload, wordings),
            cascaded=cascaded,
        )

    return retrying(log, once)


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
        # Over-cascading is the safe direction: the entry's event is not held
        # against the events this redaction names, so a call that read the
        # blob through an event whose reference is erased already is erased
        # again, never one that read it and keeps its result.
        calls = _calls(log, conn, lambda entry: sha256 in _entry_list(entry, "blobs"))
        _lock_ascending(eraser, conn, [*users, *calls])
        index = read_index(log, conn)
        fresh = _unerased(index, sha256, users)
        if fresh:
            payload = blob_payload(sha256, fresh, reason=reason)
            redaction_id = write_action(log, conn, payload, (), recorded_at=recorded_at)
            index.add(parse(redaction_id, payload))
        else:
            # Every reference is erased, so there is a redaction to name.
            redaction_id = cast("Redaction", blob_erasure(index, sha256, users)).id
        cascaded = _cascade(log, eraser, conn, calls, trigger=redaction_id, recorded_at=recorded_at)
        obsolete, kept = _blobs_after(log, conn, index, [sha256])
        return Redacted(
            redaction_id=redaction_id,
            written=bool(fresh),
            obsolete_blobs=obsolete,
            kept_blobs=kept,
            cascaded=cascaded,
        )

    return retrying(log, once)
