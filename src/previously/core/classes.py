# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Approval classes: what the operator allows a model to stand for in advance.

A model's statement of an entity or a relation is `open` until the operator
answers it. An approval class lets him answer a whole class of them once: a
model, a kind of statement, some types and a confidence threshold. The write
path gives a statement that fits a class in force the level `transitive` and
names the class in `under`; the operator stands for it, and may approve,
reject or overtake it later like any other version.

A class is an event of the kind `action` with `payload.action =
"approval_class"`. A newer event with the same `name` replaces the older one,
and revoking a class is such an event with `revoked: true`. The level of a
statement is decided when it is written and stays in its event, so a class
that is revoked or changed later does not rewrite what was written under it.
What changes is what the fold makes of it: `states` gives every event that
ever set a name the state of that name's newest event, so a transitive
version under an older event of a class sees a revocation of the class
({ref}`vocabulary-reference`).

The built-in types `circle`, `member_of` and `in_circle` are what the gate
reads, so no class reaches them: `set_class` refuses a class that names one,
and `Classes.level` answers `open` for them even when an event that came
another way names them.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.core.action import APPROVAL_CLASS
from previously.core.action import retrying
from previously.core.action import write_action_at
from previously.core.assertion import DIRECT
from previously.core.assertion import MAX_NAME_LENGTH
from previously.core.assertion import OPEN
from previously.core.errors import PreviouslyError
from previously.core.graph import ClassState
from previously.core.graph import ENTITY
from previously.core.graph import Graph
from previously.core.graph import GraphVersion
from previously.core.graph import RELATION
from previously.core.graph import TRANSITIVE
from previously.core.hashing import iso_utc
from previously.core.vocabulary import GATE_TYPES
from previously.core.vocabulary import read_vocabulary
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import re


if TYPE_CHECKING:
    from previously.contract.store import LogStore

    import random


_ASSERTIONS: Final = (ENTITY, RELATION)
_MODEL_PREFIX: Final = "model:"
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,39}")
MAX_THRESHOLD: Final = 100

_KEYS: Final = frozenset(
    {"action", "name", "author", "assertion", "types", "threshold", "valid", "revoked", "demote"}
    | {"statement"}
)
_VALID_KEYS: Final = frozenset({"from", "until"})


@dataclass(frozen=True)
class ApprovalClass:
    """One class: the statements of `author` about `assertion` of one of
    `types` that state at least `threshold` percent confidence. `valid_from`
    is included and `valid_until` excluded; either may be open."""

    name: str
    author: str
    assertion: str
    types: frozenset[str]
    threshold: int
    valid_from: datetime | None
    valid_until: datetime | None
    revoked: bool
    demote: bool


class ClassRefused(PreviouslyError):
    """The class cannot be accepted. The message is one sentence that says
    why; nothing was written."""


class _FormError(Exception):
    """The payload has the wrong shape; the message finishes the sentence
    'it …'."""


# --- Form -------------------------------------------------------------------------


def _identifier(value: object, what: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise _FormError(f"has {what} {value!r}, which is no identifier of the form a-z0-9_")
    return value


def _flag(value: object, what: str) -> bool:
    if not isinstance(value, bool):
        raise _FormError(f'has no true or false "{what}"')
    return value


def _author(value: object) -> str:
    if isinstance(value, str) and value.startswith(_MODEL_PREFIX):
        client = value[len(_MODEL_PREFIX) :]
        if (
            0 < len(client) <= MAX_NAME_LENGTH
            and client.isprintable()
            and not any(char.isspace() for char in client)
        ):
            return value
    raise _FormError("has an author that is no model:<client>")


def _types(value: object) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise _FormError('has no list "types" with at least one type')
    items = [_identifier(item, "a type") for item in cast("list[object]", value)]
    if len(set(items)) != len(items):
        raise _FormError("names a type twice")
    gate = sorted(set(items) & GATE_TYPES)
    if gate:
        raise _FormError(f'names "{gate[0]}", which the gate reads and no class reaches')
    return frozenset(items)


def _moment(value: object, what: str) -> datetime | None:
    if value is None:
        return None
    try:
        moment = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        moment = None
    if moment is None or moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise _FormError(f'has "{what}" {value!r}, which is no timestamp with a time zone')
    return moment


def _valid(value: object) -> tuple[datetime | None, datetime | None]:
    if value is None:
        return None, None
    if not isinstance(value, dict) or frozenset(cast("dict[str, object]", value)) != _VALID_KEYS:
        raise _FormError('has a "valid" that is neither null nor a table with from and until')
    window = cast("dict[str, object]", value)
    start, end = _moment(window["from"], "from"), _moment(window["until"], "until")
    if start is not None and end is not None and end <= start:
        raise _FormError("is valid until a moment that is not after the one it is valid from")
    return start, end


def _parse(payload: Mapping[str, object]) -> tuple[ApprovalClass, str]:
    """The class and the statement of a payload, or `_FormError`."""
    if frozenset(payload) != _KEYS:
        raise _FormError(f"has the keys {sorted(payload)}, not {sorted(_KEYS)}")
    if payload["action"] != APPROVAL_CLASS:
        raise _FormError("is no approval class event")
    assertion = payload["assertion"]
    if assertion not in _ASSERTIONS:
        raise _FormError(f"has the assertion {assertion!r}, which is neither entity nor relation")
    threshold = payload["threshold"]
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not 0 <= threshold <= MAX_THRESHOLD
    ):
        raise _FormError(f"has the threshold {threshold!r}, which is no whole number from 0 to 100")
    revoked, demote = _flag(payload["revoked"], "revoked"), _flag(payload["demote"], "demote")
    if demote and not revoked:
        raise _FormError("demotes without being revoked")
    start, end = _valid(payload["valid"])
    statement = payload["statement"]
    if not isinstance(statement, str) or not statement.strip():
        raise _FormError('has no "statement"')
    item = ApprovalClass(
        _identifier(payload["name"], "a name"),
        _author(payload["author"]),
        cast("str", assertion),
        _types(payload["types"]),
        threshold,
        start,
        end,
        revoked,
        demote,
    )
    return item, statement


def class_problem(payload: Mapping[str, object]) -> str | None:
    """What `verify` reports about the form of an approval class payload, or
    `None` when it is sound. Never raises.

    The write path would have refused anything found here: a finding means
    the event came another way.
    """
    try:
        _parse(payload)
    except _FormError as error:
        return f"has no valid form: it {error}"
    return None


def class_payload(item: ApprovalClass, *, statement: str) -> dict[str, object]:
    return {
        "action": APPROVAL_CLASS,
        "name": item.name,
        "author": item.author,
        "assertion": item.assertion,
        "types": sorted(item.types),
        "threshold": item.threshold,
        "valid": None
        if item.valid_from is None and item.valid_until is None
        else {
            "from": None if item.valid_from is None else iso_utc(item.valid_from),
            "until": None if item.valid_until is None else iso_utc(item.valid_until),
        },
        "revoked": item.revoked,
        "demote": item.demote,
        "statement": statement,
    }


# --- Reading and deciding ---------------------------------------------------------


@dataclass(frozen=True)
class Classes:
    """The approval classes in force at a moment.

    `by_name` holds the newest event of every name, revoked ones included,
    with the id of that event. `states` gives every event that ever set a
    name the state of the newest event of that name.
    """

    by_name: Mapping[str, tuple[ApprovalClass, int]]
    states: Mapping[int, ClassState]

    def _covers(
        self, item: ApprovalClass, *, author: str, kind: str, type_name: str, recorded_at: datetime
    ) -> bool:
        return (
            not item.revoked
            and (item.valid_from is None or item.valid_from <= recorded_at)
            and (item.valid_until is None or recorded_at < item.valid_until)
            and item.author == author
            and item.assertion == kind
            and type_name in item.types
        )

    def level(
        self,
        *,
        author: str,
        kind: str,
        type_name: str,
        confidence: int | None,
        recorded_at: datetime,
    ) -> tuple[str, int | None]:
        """The level a model statement gets: `(TRANSITIVE, id of the class's
        newest event)` when a class in force covers it, else `(OPEN, None)`.

        A class covers a statement that is in its window, of its author and
        its kind of statement, of one of its types, and whose confidence
        reaches the threshold. Of several classes that cover it, the one with
        the highest threshold wins, then the oldest event. A statement
        without a confidence is covered by none, and a built-in type by none.
        """
        if confidence is None or type_name in GATE_TYPES:
            return OPEN, None
        covering = [
            (item.threshold, event_id)
            for item, event_id in self.by_name.values()
            if self._covers(
                item, author=author, kind=kind, type_name=type_name, recorded_at=recorded_at
            )
            and confidence >= item.threshold
        ]
        if not covering:
            return OPEN, None
        _threshold, event_id = min(covering, key=lambda entry: (-entry[0], entry[1]))
        return TRANSITIVE, event_id


def read_classes[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Classes:
    """The classes in force: every approval class event up to `at` (all of
    them without it), the newest per name.

    An event whose payload was erased counts as nothing, and one whose form
    is broken is skipped as `verify` reports it; neither stops the read.
    """
    by_name: dict[str, tuple[ApprovalClass, int]] = {}
    ids: dict[str, list[int]] = {}
    for row in log.actions(conn, APPROVAL_CLASS):
        payload = row.payload
        if payload is None or payload.get("action") != APPROVAL_CLASS:
            continue
        if at is not None and row.recorded_at > at:
            continue
        try:
            item, _statement = _parse(payload)
        except _FormError:
            continue
        by_name[item.name] = (item, row.id)
        ids.setdefault(item.name, []).append(row.id)
    states = {
        event_id: ClassState(newest, item.revoked, item.demote)
        for name, (item, newest) in by_name.items()
        for event_id in ids[name]
    }
    return Classes(by_name, states)


# --- The write path ---------------------------------------------------------------


def _refusal(item: ApprovalClass, statement: str, kinds: Mapping[str, bool]) -> str | None:
    """The sentence that says why a class cannot be written, or `None`.
    `kinds` maps every type of the vocabulary under the tip to whether it
    stands. A revocation is not held against the vocabulary: a class has to
    stay revocable after a kind it names was retired."""
    try:
        _parse(class_payload(item, statement=statement))
    except _FormError as error:
        return f"the approval class {error}"
    if item.revoked:
        return None
    for name in sorted(item.types):
        if not kinds.get(name, False):
            return (
                f'the approval class names "{name}", which is no {item.assertion} '
                "kind that stands in the vocabulary"
            )
    return None


def set_class[Conn](
    log: LogStore[Conn], item: ApprovalClass, *, statement: str, recorded_at: datetime
) -> int:
    """Writes one approval class event and returns its id; refuses with
    `ClassRefused` and writes nothing.

    The tip is read before the vocabulary and the classes, and the event is
    written right after that tip: a vocabulary or class event that joined
    the chain in between takes the position, and the next attempt checks
    again ({ref}`concurrency`).
    """

    def once(conn: Conn) -> int:
        tip = log.tip(conn)
        vocabulary = read_vocabulary(log, conn)
        kinds = {
            name: not spec.retired
            for (declares, name), spec in vocabulary.kinds.items()
            if declares == item.assertion
        }
        if (sentence := _refusal(item, statement, kinds)) is not None:
            raise ClassRefused(sentence)
        payload = class_payload(item, statement=statement)
        return write_action_at(log, conn, tip, payload, (), recorded_at=recorded_at)

    return retrying(log, once)


# --- Hit rate and sample ----------------------------------------------------------


@dataclass(frozen=True)
class HitRate:
    """How the transitive versions under one class name fared.

    `total` is `confirmed + corrected + standing`. `class_id` is the newest
    event of the name.
    """

    class_id: int
    name: str
    total: int
    confirmed: int
    corrected: int
    standing: int


def _under(graph: Graph, version: GraphVersion) -> int | None:
    """The newest event of the class a transitive version stands under, or
    `None` for a version that is not transitive or whose class is unknown."""
    claim = version.claim
    if claim.responsibility != TRANSITIVE or claim.under is None:
        return None
    state = graph.classes.get(claim.under)
    return None if state is None else state.id


def hit_rates(graph: Graph, classes: Classes) -> tuple[HitRate, ...]:
    """One `HitRate` per class name, sorted by name.

    A version counts at the level it was written, so the versions under a
    class revoked with `demote` stay in its numbers: the record of how the
    class fared outlives the class.

    Confirmed: the operator approved it. Corrected: a later direct version
    that is not its approval overtook it, or the operator rejected it.
    Standing: neither has happened.
    """
    counts = {name: [0, 0, 0] for name in classes.by_name}
    name_of = {event_id: name for name, (_item, event_id) in classes.by_name.items()}
    for thread in graph.threads.values():
        for index, version in enumerate(thread.versions):
            newest = _under(graph, version)
            if newest is None or newest not in name_of:
                continue
            tally = counts[name_of[newest]]
            later_direct = any(
                later.claim.responsibility == DIRECT for later in thread.versions[index + 1 :]
            )
            if version.id in thread.approved:
                tally[0] += 1
            elif version.id in thread.rejected or later_direct:
                tally[1] += 1
            else:
                tally[2] += 1
    return tuple(
        HitRate(classes.by_name[name][1], name, sum(tally), *tally)
        for name, tally in sorted(counts.items())
    )


def sample(graph: Graph, class_id: int, count: int, rng: random.Random) -> tuple[GraphVersion, ...]:
    """`count` different transitive versions under the class whose newest
    event is `class_id`, or all of them when there are fewer, sorted by id.
    A `class_id` that names no class gives none."""
    found = sorted(
        (
            version
            for thread in graph.threads.values()
            for version in thread.versions
            if _under(graph, version) == class_id
        ),
        key=lambda version: version.id,
    )
    if count >= len(found):
        return tuple(found)
    return tuple(sorted(rng.sample(found, max(count, 0)), key=lambda version: version.id))
