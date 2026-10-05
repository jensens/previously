# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What a redaction says, and the index over all of them ({ref}`erasure`).

A redaction is an event of kind `action` whose payload names the action
under `action` and what it erases under `scope` and `target`. This module
builds that payload, reads it back, and indexes the redactions of a log by
what they cover. It is pure: `read_index` takes the store as a parameter and
asks it for one thing, the events of one kind.

`parse` is strict. The one writer of a redaction is `core.redact`, through the
builders below, so a payload that is not exactly one of the three forms was
not written that way, and `verify` reports it rather than guessing what it
meant.

`blob_expected` is the rule that says when a blob has to lie in the store,
and the one place it is computed: `redact` deletes what it says no longer has
to lie, and `verify --blobs` reports what breaks it ({ref}`erasure`).
"""

from dataclasses import dataclass
from itertools import pairwise
from previously.core.hashing import is_address
from typing import cast
from typing import Literal
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.store import LogStore


REDACTION = "redaction"

type Scope = Literal["event", "units", "blob"]

# The two keys of `target`, per scope.
_TARGET_KEYS: Mapping[str, frozenset[str]] = {
    "event": frozenset({"event", "blobs"}),
    "units": frozenset({"event", "units"}),
    "blob": frozenset({"blob", "events"}),
}
_PAYLOAD_KEYS = frozenset({"action", "scope", "target", "reason"})


@dataclass(frozen=True)
class Redaction:
    """One redaction, read out of its event."""

    # The redaction event itself.
    id: int
    scope: Scope
    reason: str
    # The erased event, for scope `event` and `units`.
    event: int | None = None
    # The erased units, for scope `units`.
    units: tuple[int, ...] = ()
    # For scope `event`: the blobs the erased event referenced.
    blobs: tuple[str, ...] = ()
    # For scope `blob`: the blob and the events that used it.
    blob: str | None = None
    events: tuple[int, ...] = ()


class MalformedAction(ValueError):
    """An action payload that is none of the forms this module writes."""


def event_payload(event_id: int, *, blobs: Sequence[str], reason: str) -> dict[str, object]:
    """The payload of a redaction that erases a whole event."""
    return {
        "action": REDACTION,
        "scope": "event",
        "target": {"event": event_id, "blobs": sorted(set(blobs))},
        "reason": reason,
    }


def units_payload(event_id: int, seqs: Sequence[int], *, reason: str) -> dict[str, object]:
    """The payload of a redaction that erases units of one event, ordered and
    each named once."""
    return {
        "action": REDACTION,
        "scope": "units",
        "target": {"event": event_id, "units": sorted(set(seqs))},
        "reason": reason,
    }


def blob_payload(sha256: str, event_ids: Sequence[int], *, reason: str) -> dict[str, object]:
    """The payload of a redaction that erases a blob for the named events,
    ordered and each named once."""
    return {
        "action": REDACTION,
        "scope": "blob",
        "target": {"blob": sha256, "events": sorted(set(event_ids))},
        "reason": reason,
    }


def action_name(payload: Mapping[str, object]) -> str:
    """The name of the action, `payload.action`; raises `MalformedAction`
    when there is none."""
    name = payload.get("action")
    if not isinstance(name, str) or not name:
        raise MalformedAction("the action has no name")
    return name


def _identifier(value: object) -> int:
    # `bool` is a subclass of `int` in Python, and `true` in JSON is no id.
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedAction("an identifier is not an integer")
    return value


def _ascending[T: (int, str)](values: object, item: Callable[[object], T]) -> tuple[T, ...]:
    """A list whose items pass `item`, strictly ascending: ordered, and none
    twice."""
    if not isinstance(values, list):
        raise MalformedAction("a list is expected")
    items = tuple(item(value) for value in cast("list[object]", values))
    if any(not (a < b) for a, b in pairwise(items)):
        raise MalformedAction("a list is not ascending without duplicates")
    return items


def _blob_address(value: object) -> str:
    if not isinstance(value, str) or not is_address(value):
        raise MalformedAction("a blob address is not 64 lower-case hexadecimal characters")
    return value


def parse(event_id: int, payload: Mapping[str, object]) -> Redaction:
    """The redaction an action event carries; raises `MalformedAction` for
    anything that is not exactly one of the three forms."""
    if frozenset(payload) != _PAYLOAD_KEYS or action_name(payload) != REDACTION:
        raise MalformedAction("not the form of a redaction")
    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise MalformedAction("the reason is not a text with something in it besides blanks")
    scope = payload["scope"]
    target = payload["target"]
    if not isinstance(scope, str) or scope not in _TARGET_KEYS:
        raise MalformedAction("the scope is not known")
    if not isinstance(target, dict):
        raise MalformedAction("the target is not an object")
    named = cast("dict[str, object]", target)
    if frozenset(named) != _TARGET_KEYS[scope]:
        raise MalformedAction("the target does not carry the keys of its scope")
    if scope == "event":
        return Redaction(
            id=event_id,
            scope="event",
            reason=reason,
            event=_identifier(named["event"]),
            blobs=_ascending(named["blobs"], _blob_address),
        )
    if scope == "units":
        units = _ascending(named["units"], _identifier)
        if not units:
            raise MalformedAction("a redaction of units names no unit")
        return Redaction(
            id=event_id,
            scope="units",
            reason=reason,
            event=_identifier(named["event"]),
            units=units,
        )
    return Redaction(
        id=event_id,
        scope="blob",
        reason=reason,
        blob=_blob_address(named["blob"]),
        events=_ascending(named["events"], _identifier),
    )


class RedactionIndex:
    """The redactions of a log, by what they cover.

    The first redaction of a target is the one an index answers with: a
    second one of the same target is what `redact` exists to prevent, and if
    the log holds one anyway, the earlier is the one that ordered the erasure.
    """

    def __init__(self) -> None:
        self._all: list[Redaction] = []
        self._events: dict[int, Redaction] = {}
        self._units: dict[tuple[int, int], Redaction] = {}
        # (event, blob) -> the blob redaction that names the event.
        self._references: dict[tuple[int, str], Redaction] = {}

    def add(self, redaction: Redaction) -> None:
        self._all.append(redaction)
        if redaction.blob is not None:
            for event_id in redaction.events:
                self._references.setdefault((event_id, redaction.blob), redaction)
        if redaction.event is None:
            return
        if redaction.scope == "event":
            self._events.setdefault(redaction.event, redaction)
        for seq in redaction.units:
            self._units.setdefault((redaction.event, seq), redaction)

    def of_event(self, event_id: int) -> Redaction | None:
        """The redaction of the whole event, or `None`."""
        return self._events.get(event_id)

    def of_unit(self, event_id: int, seq: int) -> Redaction | None:
        """The redaction that erased a unit, or `None`: a redaction of units
        that names it, or the redaction of its whole event. When both exist,
        the earlier one, for the reason the class gives."""
        found = [
            redaction
            for redaction in (self._units.get((event_id, seq)), self.of_event(event_id))
            if redaction is not None
        ]
        return min(found, key=lambda redaction: redaction.id, default=None)

    def of_reference(self, event_id: int, sha256: str) -> Redaction | None:
        """The redaction that erased the reference of an event to a blob, or
        `None`: the redaction of the whole event, or a blob redaction that
        names the event. When both exist, the earlier one, for the reason
        the class gives."""
        found = [
            redaction
            for redaction in (self.of_event(event_id), self._references.get((event_id, sha256)))
            if redaction is not None
        ]
        return min(found, key=lambda redaction: redaction.id, default=None)

    def __iter__(self) -> Iterator[Redaction]:
        return iter(self._all)


def blob_expected(index: RedactionIndex, sha256: str, event_ids: Iterable[int]) -> bool:
    """Whether a blob has to lie in the store: as long as at least one of its
    references is not erased ({ref}`erasure`).

    `event_ids` are the events the register names for the blob, all of them,
    erased or not. Without any, the blob has nothing to lie for.
    """
    return any(index.of_reference(event_id, sha256) is None for event_id in event_ids)


def blob_erasure(index: RedactionIndex, sha256: str, event_ids: Iterable[int]) -> Redaction | None:
    """The redaction to name for a blob that no longer has to lie — the
    newest of those that erased its references, the one after which none
    stood — or `None` while it has to lie, or when no event names it."""
    users = list(event_ids)
    if blob_expected(index, sha256, users):
        return None
    erasures = [index.of_reference(event_id, sha256) for event_id in users]
    return max(
        (redaction for redaction in erasures if redaction is not None),
        key=lambda redaction: redaction.id,
        default=None,
    )


def read_index[Conn](log: LogStore[Conn], conn: Conn) -> RedactionIndex:
    """Every redaction the log holds, read in chain order.

    An action that cannot be read as a redaction is passed over: reporting it
    is the business of `verify`, and a reader that refused the whole log for
    one bad row would let that row blind every redaction behind it.
    """
    index = RedactionIndex()
    for row in log.read_by_kind(conn, "action"):
        if row.payload is None:
            continue
        try:
            if action_name(row.payload) == REDACTION:
                index.add(parse(row.id, row.payload))
        except MalformedAction:
            continue
    return index
