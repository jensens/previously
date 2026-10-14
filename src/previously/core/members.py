# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What belongs to a bracket: the events and units assigned to it, or to
anything that is part of it.

A bracket is any entity an assignment can point at: a project, a matter, an
organization. An assignment is a relation of the kind `concerns` that starts
at an event, at the whole of it or at some of its units, and points at the
bracket. A relation of the kind `part_of` carries what belongs to the part up
to the whole: what concerns the summer party of a club belongs to the club.

Pure: `members` takes the edges and computes the set, and the caller decides
where the edges come from — `bracket_edges` takes them from a folded graph.
Finding is not authority: the edges are the standing winners of every level,
open proposals included, as `Graph.relations()` gives them, and what a client
may read of an event the policy decides elsewhere, event by event.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from previously.core.assertion import Source
from types import MappingProxyType
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from previously.core.graph import Graph
    from previously.core.graph import RelationBody


PART_OF: Final = "part_of"
CONCERNS: Final = "concerns"


@dataclass(frozen=True)
class BracketEdge:
    """One standing relation as `members` reads it: its id, its kind, where
    it starts — the id of an entity, or an event with the units it names,
    `units` None for the whole event — and the entity it points at."""

    subject: int
    type: str
    start: int | Source
    to: int


@dataclass(frozen=True)
class Members:
    """What belongs to one bracket.

    `brackets` holds the bracket and every entity below it over `part_of`.

    `events` maps each event of which anything belongs to `None` or to a set
    of units. A set means exactly those units. `None` means the whole event,
    because an assignment of the whole event points into `brackets`, with
    the exception of the units `excluded` names for that event: those have
    assignments of their own, none of which points into `brackets`, and the
    more specific replaces the general. The exceptions are kept here so that
    `holds` answers for any unit without the units of the event, which only
    the log knows.
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


def bracket_edges(graph: Graph) -> tuple[BracketEdge, ...]:
    """The relations of `graph` that `members` reads, by id: every one of
    the kinds `part_of` and `concerns` that `Graph.relations()` gives, a
    proposal included, and a question, which points at nothing yet, not."""
    found = graph.relations()
    edges: list[BracketEdge] = []
    for subject in sorted(found):
        body = cast("RelationBody", found[subject].claim.body)
        if body.type in (PART_OF, CONCERNS):
            edges.append(BracketEdge(subject, body.type, body.start, cast("int", body.to)))
    return tuple(edges)


def _below(edges: Iterable[BracketEdge], bracket: int) -> frozenset[int]:
    """`bracket` and every entity from which a path of `part_of` edges leads
    to it. The edges may hold a cycle that runs through a proposal (see
    `Graph.relations`), so the walk keeps a visited set."""
    parts: dict[int, set[int]] = {}
    for edge in edges:
        if edge.type == PART_OF and not isinstance(edge.start, Source):
            parts.setdefault(edge.to, set()).add(edge.start)
    found = {bracket}
    frontier = [bracket]
    while frontier:
        for part in parts.get(frontier.pop(), ()):
            if part not in found:
                found.add(part)
                frontier.append(part)
    return frozenset(found)


def members(edges: Iterable[BracketEdge], bracket: int) -> Members:
    """What belongs to `bracket`, by the edges given.

    A unit belongs when an assignment of its own points into the bracket or
    below it. A unit without an assignment of its own belongs when an
    assignment of its whole event does. An assignment of some units is the
    more specific one: it replaces that of the whole event for those units,
    so a unit whose own assignments all point elsewhere does not belong,
    whatever its event's assignment says. An edge of another kind, a
    `concerns` that starts at an entity and a `part_of` that starts at an
    event are not read.
    """
    given = tuple(edges)
    brackets = _below(given, bracket)
    whole: dict[int, bool] = {}  # event -> whether an assignment of all of it points in
    own: dict[int, dict[int, bool]] = {}  # event -> unit -> whether one of its own points in
    for edge in given:
        start = edge.start
        if edge.type != CONCERNS or not isinstance(start, Source):
            continue
        inside = edge.to in brackets
        if start.units is None:
            whole[start.event] = whole.get(start.event, False) or inside
            continue
        units = own.setdefault(start.event, {})
        for seq in start.units:
            units[seq] = units.get(seq, False) or inside
    events: dict[int, frozenset[int] | None] = {}
    excluded: dict[int, frozenset[int]] = {}
    for event_id in sorted(whole.keys() | own.keys()):
        units = own.get(event_id, {})
        if whole.get(event_id, False):
            events[event_id] = None
            outside = frozenset(seq for seq, inside in units.items() if not inside)
            if outside:
                excluded[event_id] = outside
            continue
        inside_units = frozenset(seq for seq, inside in units.items() if inside)
        if inside_units:
            events[event_id] = inside_units
    return Members(brackets, MappingProxyType(events), MappingProxyType(excluded))
