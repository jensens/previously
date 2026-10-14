# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What belongs to a bracket: `members` over the hierarchy and assignments,
`bracket_kinds`, which takes both from a vocabulary, and `bracket_edges`,
which takes the edges from a folded graph.

Pure functions, so there is no database to start. The kinds named here are
test data: the code takes them from the vocabulary it is handed.
"""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import Source
from previously.core.graph import Claim
from previously.core.graph import claim_payload
from previously.core.graph import ClassState
from previously.core.graph import fold_graph
from previously.core.graph import Period
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import STANDING
from previously.core.graph import TRANSITIVE
from previously.core.members import bracket_edges
from previously.core.members import bracket_kinds
from previously.core.members import BracketEdge
from previously.core.members import BracketKinds
from previously.core.members import members
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import built_in_kinds
from previously.core.vocabulary import KindSpec
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import RELATION_KIND
from previously.core.vocabulary import Vocabulary
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
CLASS = 900


def _vocabulary(*extra: KindSpec) -> Vocabulary:
    specs = (*built_in_kinds(), *parse_file(base_vocabulary()), *extra)
    return Vocabulary({(spec.declares, spec.name): spec for spec in specs}, {})


def _relation_kind(
    name: str,
    from_: tuple[str, ...],
    to: tuple[str, ...],
    behaviors: frozenset[str] = frozenset(),
    *,
    retired: bool = False,
) -> KindSpec:
    return KindSpec(RELATION_KIND, name, {"en": name}, (), behaviors, from_, to, retired)


BASE = _vocabulary()
KINDS = bracket_kinds(BASE)
HIERARCHY = "part_of"
ASSIGNMENT = "concerns"


def part(subject: int, start: int, to: int, level: str = DIRECT) -> BracketEdge:
    return BracketEdge(subject, HIERARCHY, start, to, level)


def assign(subject: int, start: Source, to: int, level: str = DIRECT) -> BracketEdge:
    return BracketEdge(subject, ASSIGNMENT, start, to, level)


# --- the kinds come from the vocabulary --------------------------------------------


def test_the_base_vocabulary_has_one_hierarchy_and_one_assignment_kind() -> None:
    assert BracketKinds(frozenset({"part_of"}), frozenset({"concerns"})) == KINDS


def test_a_second_transitive_kind_makes_a_second_hierarchy() -> None:
    """Ruling T2-a of the 2026-10-15 assignments plan, phase 2: declaring
    `transitive` is what makes a kind carry upward. Measured red with
    `part_of` named in `bracket_kinds` again."""
    sub = _relation_kind("subproject_of", ("project",), ("project",), frozenset({"transitive"}))
    kinds = bracket_kinds(_vocabulary(sub))
    edges = (
        BracketEdge(1, "subproject_of", 10, 11, DIRECT),
        assign(2, Source(5, None), 10),
    )

    assert kinds.hierarchy == {"part_of", "subproject_of"}
    assert members(edges, 11, kinds).holds(5, 1)
    assert not members(edges, 11, KINDS).holds(5, 1)


def test_a_kind_other_than_concerns_that_starts_at_an_event_is_an_assignment() -> None:
    """Measured red with `concerns` named in `bracket_kinds` again."""
    mentions = _relation_kind("mentions", ("event",), ("*",))
    kinds = bracket_kinds(_vocabulary(mentions))
    edges = (BracketEdge(1, "mentions", Source(5, (2,)), 10, DIRECT),)

    assert kinds.assignments == {"concerns", "mentions"}
    assert members(edges, 10, kinds).holds(5, 2)
    assert not members(edges, 10, KINDS).holds(5, 2)


def test_a_kind_the_gate_reads_is_no_assignment_even_when_it_starts_at_an_event() -> None:
    """Ruling T2-e: `in_circle` is to start at an event in phase 3, and a
    circle is no bracket. A vocabulary written by hand in which it already
    does still feeds nothing into `members`. The control is `concerns` in
    the same vocabulary."""
    in_circle = _relation_kind("in_circle", ("event",), ("circle",))
    kinds = bracket_kinds(_vocabulary(in_circle))
    edges = (
        BracketEdge(1, "in_circle", Source(5, None), 10, DIRECT),
        assign(2, Source(6, None), 10),
    )

    assert "in_circle" not in kinds.assignments
    assert not members(edges, 10, kinds).holds(5, 1)
    assert members(edges, 10, kinds).holds(6, 1)


def test_a_retired_kind_still_counts_for_what_stands() -> None:
    old = _relation_kind("concerned", ("event",), ("*",), retired=True)
    whole = _relation_kind("within", ("project",), ("project",), frozenset({"transitive"}))
    kinds = bracket_kinds(_vocabulary(old, replace(whole, retired=True)))

    assert "concerned" in kinds.assignments
    assert "within" in kinds.hierarchy


# --- Markus's mail, the example of the 2026-10-14 assignments specification -------
#
# Markus writes about the project XZ, and his last paragraph says the caterer
# has agreed: that is about the summer party of the club, not about XZ. The
# mail is assigned to XZ as a whole, its last unit to the summer party, and the
# summer party is part of the club.

XZ, PARTY, CLUB = 10, 11, 12
MAIL = 1


def _markus(level: str = DIRECT) -> tuple[BracketEdge, ...]:
    return (
        assign(20, Source(MAIL, None), XZ),
        assign(21, Source(MAIL, (4,)), PARTY, level),
        part(22, PARTY, CLUB),
    )


def test_the_units_about_xz_belong_to_xz_and_the_last_one_does_not() -> None:
    found = members(_markus(), XZ, KINDS)

    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [True, True, True, False]
    assert found.events == {MAIL: None}
    assert found.excluded == {MAIL: frozenset({4})}


def test_the_summer_party_holds_the_last_unit_only() -> None:
    found = members(_markus(), PARTY, KINDS)

    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [False, False, False, True]
    assert found.events == {MAIL: frozenset({4})}
    assert found.excluded == {}


def test_the_club_holds_the_last_unit_through_the_summer_party() -> None:
    found = members(_markus(), CLUB, KINDS)

    assert found.brackets == {CLUB, PARTY}
    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [False, False, False, True]


def test_a_transitive_assignment_of_a_unit_replaces_as_a_direct_one_does() -> None:
    assert not members(_markus(TRANSITIVE), XZ, KINDS).holds(MAIL, 4)


def test_a_proposal_for_a_unit_adds_it_and_takes_nothing_from_its_events_assignment() -> None:
    """Ruling T2-c: a model's open assignment of the last unit to the summer
    party finds the unit there, and the operator's assignment of the whole
    mail to XZ keeps it. Measured red with the level ignored."""
    proposed = _markus(OPEN)

    assert members(proposed, XZ, KINDS).holds(MAIL, 4)
    assert members(proposed, XZ, KINDS).excluded == {}
    assert members(proposed, PARTY, KINDS).holds(MAIL, 4)


def test_whoever_wants_the_last_unit_in_both_assigns_it_to_both() -> None:
    both = (*_markus(), assign(23, Source(MAIL, (4,)), XZ))

    assert members(both, XZ, KINDS).holds(MAIL, 4)
    assert members(both, PARTY, KINDS).holds(MAIL, 4)
    assert members(both, XZ, KINDS).excluded == {}


def test_the_hierarchy_carries_upward_and_not_downward() -> None:
    """What belongs to the club belongs to nothing below it: the club's own
    mail is not the summer party's."""
    edges = (*_markus(), assign(24, Source(2, None), CLUB))

    assert members(edges, CLUB, KINDS).holds(2, 1)
    assert not members(edges, PARTY, KINDS).holds(2, 1)
    assert members(edges, PARTY, KINDS).brackets == {PARTY}


def test_a_cycle_through_a_proposal_ends_the_walk() -> None:
    edges = (part(30, 1, 2, OPEN), part(31, 2, 1), assign(32, Source(5, None), 1))

    assert members(edges, 2, KINDS).brackets == {1, 2}
    assert members(edges, 2, KINDS).holds(5, 7)


def test_edges_of_other_kinds_and_starts_are_not_read() -> None:
    edges = (
        BracketEdge(40, "holds", 1, 2, DIRECT),
        BracketEdge(41, ASSIGNMENT, 1, 2, DIRECT),
        BracketEdge(42, HIERARCHY, Source(5, None), 2, DIRECT),
        BracketEdge(43, "involved_in", Source(6, None), 2, DIRECT),
    )

    found = members(edges, 2, KINDS)

    assert found.brackets == {2}
    assert found.events == {}
    assert not found.holds(5, 1)


def test_an_event_nothing_assigns_belongs_nowhere() -> None:
    assert not members(_markus(), XZ, KINDS).holds(99, 1)


# --- bracket_edges ----------------------------------------------------------------


def _relation(
    kind: str,
    start: int | Source,
    to: int | None,
    *,
    responsibility: str = DIRECT,
    candidates: tuple[int, ...] | None = None,
    state: str = STANDING,
    subject: int | None = None,
    period: Period | None = None,
) -> Claim:
    sources = (start,) if isinstance(start, Source) else (Source(1, None),)
    model = responsibility != DIRECT
    return Claim(
        RELATION,
        model_author("claude") if model else OPERATOR,
        responsibility,
        SOURCES,
        sources,
        None,
        None,
        subject,
        None,
        CLASS if responsibility == TRANSITIVE else None,
        90 if model else None,
        None,
        RelationBody(kind, start, to, candidates, period, {}, state),
    )


def _rows(*claims: Claim) -> list[tuple[int, datetime, Mapping[str, object] | None]]:
    return [
        (row_id, NOW + timedelta(minutes=row_id), claim_payload(claim))
        for row_id, claim in enumerate(claims, 1)
    ]


def test_bracket_edges_takes_every_level_and_leaves_out_questions_retractions_and_other_kinds() -> (
    None
):
    """Finding is no authority: a proposal is found as a direct edge is,
    each with the level its winner counts at. A question points at nothing
    yet, and a retraction takes its edge back."""
    classes = {CLASS: ClassState(CLASS, revoked=False, demote=False)}
    graph = fold_graph(
        _rows(
            _relation("concerns", Source(1, (2,)), 10),
            _relation("concerns", Source(1, None), 11, responsibility=OPEN),
            _relation("part_of", 10, 12, responsibility=TRANSITIVE),
            _relation("holds", 13, 14),
            _relation("concerns", Source(1, None), None, responsibility=OPEN, candidates=(10, 11)),
            _relation("part_of", 11, 12),
            _relation("part_of", 11, 12, state=RETRACTED, subject=6),
        ),
        classes,
    )

    assert bracket_edges(graph, BASE) == (
        BracketEdge(1, "concerns", Source(1, (2,)), 10, DIRECT),
        BracketEdge(2, "concerns", Source(1, None), 11, OPEN),
        BracketEdge(3, "part_of", 10, 12, TRANSITIVE),
    )


def test_a_hierarchy_edge_whose_period_ended_still_carries_what_it_held() -> None:
    """Ruling T2-d: finding ignores periods. Measured red with
    `graph.relations(at=…)` in `bracket_edges`."""
    ended = Period(date(2019, 1, 1), date(2020, 12, 31))
    graph = fold_graph(
        _rows(
            _relation("part_of", 11, 12, period=ended),
            _relation("concerns", Source(5, None), 11, period=ended),
        ),
        {},
    )

    found = members(bracket_edges(graph, BASE), 12, KINDS)

    assert found.brackets == {11, 12}
    assert found.holds(5, 1)


# --- the property -----------------------------------------------------------------
#
# Entities 1 to 6, events 101 to 103 with units 1 to 4. The oracle walks
# upward from what an assignment points at, and decides unit by unit;
# `members` walks downward from the bracket, and works event by event. The
# two share nothing but the edges.

ENTITIES = st.integers(min_value=1, max_value=6)
EVENTS = st.integers(min_value=101, max_value=103)
UNITS = st.integers(min_value=1, max_value=4)
LEVELS = st.sampled_from([DIRECT, TRANSITIVE, OPEN])
STARTS = st.one_of(
    st.builds(Source, EVENTS, st.none()),
    st.builds(
        Source,
        EVENTS,
        st.frozensets(UNITS, min_size=1).map(lambda units: tuple(sorted(units))),
    ),
)
# Every pair of entities, so the walks meet cycles and edges to themselves,
# which open proposals may hold.
PARTS = st.lists(st.tuples(ENTITIES, ENTITIES), max_size=10)
ASSIGNMENTS = st.lists(st.tuples(STARTS, ENTITIES, LEVELS), max_size=10)
# Edges `members` must not read: another kind, an assignment that starts at
# an entity, a hierarchy edge that starts at an event.
NOISE = st.lists(
    st.one_of(
        st.tuples(st.just("holds"), ENTITIES, ENTITIES),
        st.tuples(st.just(ASSIGNMENT), ENTITIES, ENTITIES),
        st.tuples(st.just(HIERARCHY), STARTS, ENTITIES),
    ),
    max_size=4,
)

type Assigned = list[tuple[Source, int, str]]


def _wholes(start: int, parts: list[tuple[int, int]]) -> set[int]:
    """`start` and everything it is part of, by following the hierarchy
    from part to whole."""
    reached = {start}
    changed = True
    while changed:
        changed = False
        for whole_of, whole in parts:
            if whole_of in reached and whole not in reached:
                reached.add(whole)
                changed = True
    return reached


def _points_in(target: int, bracket: int, parts: list[tuple[int, int]]) -> bool:
    return bracket in _wholes(target, parts)


def _own(event: int, seq: int, assignments: Assigned) -> list[tuple[int, str]]:
    return [
        (to, level)
        for start, to, level in assignments
        if start.event == event and seq in (start.units or ())
    ]


def _whole_in(
    event: int, bracket: int, parts: list[tuple[int, int]], assignments: Assigned
) -> bool:
    return any(
        _points_in(to, bracket, parts)
        for start, to, _level in assignments
        if start.event == event and start.units is None
    )


def _belongs(
    event: int, seq: int, bracket: int, parts: list[tuple[int, int]], assignments: Assigned
) -> bool:
    own = _own(event, seq, assignments)
    if any(_points_in(to, bracket, parts) for to, _level in own):
        return True
    firm = any(level != OPEN for _to, level in own)
    return not firm and _whole_in(event, bracket, parts, assignments)


@settings(deadline=None, max_examples=400)
@given(
    parts=PARTS,
    assignments=ASSIGNMENTS,
    noise=NOISE,
    bracket=st.integers(min_value=1, max_value=7),
)
def test_a_unit_belongs_by_its_own_assignments_else_by_its_events(
    parts: list[tuple[int, int]],
    assignments: Assigned,
    noise: list[tuple[str, int | Source, int]],
    bracket: int,
) -> None:
    """Review Focus 4 of the 2026-10-15 assignments plan, phase 2: a unit
    with an assignment of its own to another bracket that stands for
    someone does not appear in the bracket of its event, and a unit without
    one does (ruling T2-c). `events`, `excluded` and `brackets` are held to
    the oracle as well as `holds`."""
    edges = [
        *(part(0, whole_of, whole) for whole_of, whole in parts),
        *(assign(0, start, to, level) for start, to, level in assignments),
        *(BracketEdge(0, kind, start, to, DIRECT) for kind, start, to in noise),
    ]
    found = members(edges, bracket, KINDS)

    assert found.brackets == {e for e in range(1, 8) if _points_in(e, bracket, parts)}
    for event in range(101, 104):
        holding = {seq for seq in range(1, 5) if _belongs(event, seq, bracket, parts, assignments)}
        for seq in range(1, 5):
            assert found.holds(event, seq) == (seq in holding), (event, seq)
        if _whole_in(event, bracket, parts, assignments):
            out = {seq for seq in range(1, 5) if _own(event, seq, assignments)} - holding
            assert found.events[event] is None
            assert found.excluded.get(event, frozenset()) == out
            assert event not in found.excluded or out
        else:
            assert found.events.get(event) == (frozenset(holding) if holding else None)
            assert (event in found.events) == bool(holding)
            assert event not in found.excluded


def test_the_property_meets_a_unit_whose_own_assignment_replaces_its_events() -> None:
    """A fixed example of what the property is about, so a reader sees it
    without a seed: unit 2 is assigned elsewhere, unit 1 inherits."""
    edges = [assign(0, Source(101, None), 1), assign(0, Source(101, (2,)), 2)]
    found = members(edges, 1, KINDS)

    assert (found.holds(101, 1), found.holds(101, 2)) == (True, False)
    assert replace(found, excluded={}).holds(101, 2)
