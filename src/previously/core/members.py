# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What belongs to a bracket: the events and units assigned to it, or to
anything that is part of it.

A bracket is any entity an assignment can point at: a project, a matter, an
organization. Which relations say what the vocabulary in force says, and no
kind is named here (`bracket_kinds`):

- an **assignment** is a relation of a kind that starts at `event`, at the
  whole of an event or at some of its units, and points at the bracket;
- the **hierarchy** is every relation of a kind with the behavior
  `transitive` between two entities, from the part to the whole, and it
  carries what belongs to the part up to the whole: what concerns the summer
  party of a club belongs to the club.

Pure: `members` takes the edges and computes the set, and the caller decides
where the edges come from — `bracket_edges` takes them from a folded graph.
Finding is not authority: the edges are the standing winners of every level,
open proposals included, as `Graph.relations()` gives them, and what a client
may read of an event the policy decides elsewhere, event by event. Periods
play no part: a hierarchy or an assignment whose period has ended still
holds what it held.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from previously.contract.rows import ChronicleSelection
from previously.core.assertion import DIRECT
from previously.core.assertion import Source
from previously.core.graph import level_of
from previously.core.graph import TRANSITIVE as TRANSITIVE_LEVEL
from previously.core.vocabulary import EVENT_START
from previously.core.vocabulary import GATE_TYPES
from previously.core.vocabulary import RELATION_KIND
from previously.core.vocabulary import TRANSITIVE as TRANSITIVE_BEHAVIOR
from types import MappingProxyType
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from previously.core.graph import Graph
    from previously.core.graph import RelationBody
    from previously.core.vocabulary import Vocabulary


# The levels at which an assignment of units stands for someone, and so
# replaces the assignment of its whole event for those units.
_STANDS_FOR: Final = frozenset({DIRECT, TRANSITIVE_LEVEL})


@dataclass(frozen=True)
class BracketKinds:
    """The relation kinds `members` reads, by name: those of the hierarchy
    and those of an assignment."""

    hierarchy: frozenset[str]
    assignments: frozenset[str]


def bracket_kinds(vocabulary: Vocabulary) -> BracketKinds:
    """The kinds of `vocabulary` that make the hierarchy and the
    assignments.

    The hierarchy is every relation kind with the behavior `transitive`. An
    assignment is every relation kind whose `from` names `event`, except a
    kind the gate reads: the gate decides what a model may see, and a
    circle is no bracket to find mails in. A retired kind counts, since
    what was written under it still stands.
    """
    hierarchy: set[str] = set()
    assignments: set[str] = set()
    for (declares, name), spec in vocabulary.kinds.items():
        if declares != RELATION_KIND:
            continue
        if TRANSITIVE_BEHAVIOR in spec.behaviors:
            hierarchy.add(name)
        if EVENT_START in (spec.from_ or ()) and name not in GATE_TYPES:
            assignments.add(name)
    return BracketKinds(frozenset(hierarchy), frozenset(assignments))


@dataclass(frozen=True)
class BracketEdge:
    """One standing relation as `members` reads it: its id, its kind, where
    it starts — the id of an entity, or an event with the units it names,
    `units` None for the whole event —, the entity it points at, and the
    level its winner counts at (`level_of`)."""

    subject: int
    type: str
    start: int | Source
    to: int
    level: str


@dataclass(frozen=True)
class Members:
    """What belongs to one bracket.

    `brackets` holds the bracket and every entity below it in the
    hierarchy.

    `events` maps each event of which anything belongs to `None` or to a set
    of units. A set means exactly those units. `None` means the whole event,
    because an assignment of the whole event points into `brackets`, with
    the exception of the units `excluded` names for that event: each of
    those has an assignment of its own that stands for someone, direct or
    transitive, and none of its own assignments points into `brackets` —
    the more specific replaces the general. The exceptions are kept here so
    that `holds` answers for any unit without the units of the event, which
    only the log knows.

    Periods play no part, see the module docstring.
    """

    brackets: frozenset[int]
    events: Mapping[int, frozenset[int] | None]
    excluded: Mapping[int, frozenset[int]]

    def holds(self, event_id: int, seq: int) -> bool:
        """Whether unit `seq` of event `event_id` belongs to the bracket."""
        if event_id not in self.events:
            return False
        units = self.events[event_id]
        if units is None:
            return seq not in self.excluded.get(event_id, frozenset())
        return seq in units


def chronicle_selection(found: Members) -> ChronicleSelection:
    """The units of the chronicle that `found` holds, in the form a query
    takes them: `ChronicleSelection` selects exactly the `(event_id, seq)`
    for which `Members.holds` answers yes."""
    return ChronicleSelection(
        events=frozenset(event for event, units in found.events.items() if units is None),
        excluded=frozenset((event, seq) for event, seqs in found.excluded.items() for seq in seqs),
        units=frozenset(
            (event, seq) for event, seqs in found.events.items() if seqs is not None for seq in seqs
        ),
    )


def bracket_edges(graph: Graph, vocabulary: Vocabulary) -> tuple[BracketEdge, ...]:
    """The relations of `graph` that `members` reads, by id, with the
    level each counts at: every one of a kind `bracket_kinds` names that
    `Graph.relations()` gives, a proposal included, a question, which
    points at nothing yet, not, and whatever its period."""
    kinds = bracket_kinds(vocabulary)
    read = kinds.hierarchy | kinds.assignments
    found = graph.relations()
    edges: list[BracketEdge] = []
    for subject in sorted(found):
        version = found[subject]
        body = cast("RelationBody", version.claim.body)
        if body.type in read:
            level = level_of(version, graph.classes)
            edges.append(BracketEdge(subject, body.type, body.start, cast("int", body.to), level))
    return tuple(edges)


def _below(edges: Iterable[BracketEdge], bracket: int, hierarchy: frozenset[str]) -> frozenset[int]:
    """`bracket` and every entity from which a path of hierarchy edges
    leads to it. The edges may hold a cycle that runs through a proposal
    (see `Graph.relations`), so the walk keeps a visited set."""
    parts: dict[int, set[int]] = {}
    for edge in edges:
        if edge.type in hierarchy and not isinstance(edge.start, Source):
            parts.setdefault(edge.to, set()).add(edge.start)
    found = {bracket}
    frontier = [bracket]
    while frontier:
        for part in parts.get(frontier.pop(), ()):
            if part not in found:
                found.add(part)
                frontier.append(part)
    return frozenset(found)


@dataclass
class _Units:
    """What the assignments of one event's units say of each unit: whether
    one of them points in, and whether one stands for someone."""

    inside: dict[int, bool]
    firm: dict[int, bool]


def members(edges: Iterable[BracketEdge], bracket: int, kinds: BracketKinds) -> Members:
    """What belongs to `bracket`, by the edges given and the kinds of
    `kinds`.

    A unit belongs when an assignment of its own points into the bracket or
    below it, at any level. A unit without an assignment of its own that
    stands for someone belongs when an assignment of its whole event does:
    an assignment of some units that is direct or transitive is the more
    specific one, and replaces that of the whole event for those units. A
    proposal of a unit's own adds the unit where it points and takes
    nothing away from its event's assignment: a proposal nobody stands for
    must not remove what the operator set. An edge of another kind, an
    assignment that starts at an entity and a hierarchy edge that starts at
    an event are not read.
    """
    given = tuple(edges)
    brackets = _below(given, bracket, kinds.hierarchy)
    whole: dict[int, bool] = {}  # event -> whether an assignment of all of it points in
    own: dict[int, _Units] = {}
    for edge in given:
        start = edge.start
        if edge.type not in kinds.assignments or not isinstance(start, Source):
            continue
        inside = edge.to in brackets
        if start.units is None:
            whole[start.event] = whole.get(start.event, False) or inside
            continue
        units = own.setdefault(start.event, _Units({}, {}))
        firm = edge.level in _STANDS_FOR
        for seq in start.units:
            units.inside[seq] = units.inside.get(seq, False) or inside
            units.firm[seq] = units.firm.get(seq, False) or firm
    events: dict[int, frozenset[int] | None] = {}
    excluded: dict[int, frozenset[int]] = {}
    for event_id in sorted(whole.keys() | own.keys()):
        units = own.get(event_id, _Units({}, {}))
        if whole.get(event_id, False):
            events[event_id] = None
            outside = frozenset(
                seq for seq, inside in units.inside.items() if units.firm[seq] and not inside
            )
            if outside:
                excluded[event_id] = outside
            continue
        inside_units = frozenset(seq for seq, inside in units.inside.items() if inside)
        if inside_units:
            events[event_id] = inside_units
    return Members(brackets, MappingProxyType(events), MappingProxyType(excluded))
