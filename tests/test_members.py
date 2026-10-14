# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What belongs to a bracket: `members` over `part_of` and assignments, and
`bracket_edges`, which takes the edges from a folded graph.

Pure functions, so there is no database to start.
"""

from dataclasses import replace
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
from previously.core.graph import fold_graph
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import STANDING
from previously.core.members import bracket_edges
from previously.core.members import BracketEdge
from previously.core.members import CONCERNS
from previously.core.members import members
from previously.core.members import PART_OF
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

# --- Markus's mail, the example of the 2026-10-14 assignments specification -------
#
# Markus writes about the project XZ, and his last paragraph says the caterer
# has agreed: that is about the summer party of the club, not about XZ. The
# mail is assigned to XZ as a whole, its last unit to the summer party, and the
# summer party is part of the club.

XZ, PARTY, CLUB = 10, 11, 12
MAIL = 1


def _markus() -> tuple[BracketEdge, ...]:
    return (
        BracketEdge(20, CONCERNS, Source(MAIL, None), XZ),
        BracketEdge(21, CONCERNS, Source(MAIL, (4,)), PARTY),
        BracketEdge(22, PART_OF, PARTY, CLUB),
    )


def test_the_units_about_xz_belong_to_xz_and_the_last_one_does_not() -> None:
    found = members(_markus(), XZ)

    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [True, True, True, False]
    assert found.events == {MAIL: None}
    assert found.excluded == {MAIL: frozenset({4})}


def test_the_summer_party_holds_the_last_unit_only() -> None:
    found = members(_markus(), PARTY)

    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [False, False, False, True]
    assert found.events == {MAIL: frozenset({4})}
    assert found.excluded == {}


def test_the_club_holds_the_last_unit_through_the_summer_party() -> None:
    found = members(_markus(), CLUB)

    assert found.brackets == {CLUB, PARTY}
    assert [found.holds(MAIL, seq) for seq in (1, 2, 3, 4)] == [False, False, False, True]


def test_whoever_wants_the_last_unit_in_both_assigns_it_to_both() -> None:
    both = (*_markus(), BracketEdge(23, CONCERNS, Source(MAIL, (4,)), XZ))

    assert members(both, XZ).holds(MAIL, 4)
    assert members(both, PARTY).holds(MAIL, 4)
    assert members(both, XZ).excluded == {}


def test_part_of_carries_upward_and_not_downward() -> None:
    """What belongs to the club belongs to nothing below it: the club's own
    mail is not the summer party's."""
    edges = (*_markus(), BracketEdge(24, CONCERNS, Source(2, None), CLUB))

    assert members(edges, CLUB).holds(2, 1)
    assert not members(edges, PARTY).holds(2, 1)
    assert members(edges, PARTY).brackets == {PARTY}


def test_a_cycle_through_a_proposal_ends_the_walk() -> None:
    edges = (
        BracketEdge(30, PART_OF, 1, 2),
        BracketEdge(31, PART_OF, 2, 1),
        BracketEdge(32, CONCERNS, Source(5, None), 1),
    )

    assert members(edges, 2).brackets == {1, 2}
    assert members(edges, 2).holds(5, 7)


def test_edges_of_other_kinds_and_starts_are_not_read() -> None:
    edges = (
        BracketEdge(40, "holds", 1, 2),
        BracketEdge(41, CONCERNS, 1, 2),
        BracketEdge(42, PART_OF, Source(5, None), 2),
        BracketEdge(43, "involved_in", Source(6, None), 2),
    )

    found = members(edges, 2)

    assert found.brackets == {2}
    assert found.events == {}
    assert not found.holds(5, 1)


def test_an_event_nothing_assigns_belongs_nowhere() -> None:
    assert not members(_markus(), XZ).holds(99, 1)


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
) -> Claim:
    sources = (start,) if isinstance(start, Source) else (Source(1, None),)
    model = responsibility == OPEN
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
        None,
        40 if model else None,
        None,
        RelationBody(kind, start, to, candidates, None, {}, state),
    )


def _rows(*claims: Claim) -> list[tuple[int, datetime, Mapping[str, object] | None]]:
    return [
        (row_id, NOW + timedelta(minutes=row_id), claim_payload(claim))
        for row_id, claim in enumerate(claims, 1)
    ]


def test_bracket_edges_takes_every_level_and_leaves_out_questions_retractions_and_other_kinds() -> (
    None
):
    """Finding is no authority: a proposal is found as a direct edge is. A
    question points at nothing yet, and a retraction takes its edge back."""
    graph = fold_graph(
        _rows(
            _relation(CONCERNS, Source(1, (2,)), 10),
            _relation(CONCERNS, Source(1, None), 11, responsibility=OPEN),
            _relation(PART_OF, 10, 12),
            _relation("holds", 13, 14),
            _relation(CONCERNS, Source(1, None), None, responsibility=OPEN, candidates=(10, 11)),
            _relation(PART_OF, 11, 12),
            _relation(PART_OF, 11, 12, state=RETRACTED, subject=6),
        ),
        {},
    )

    assert bracket_edges(graph) == (
        BracketEdge(1, CONCERNS, Source(1, (2,)), 10),
        BracketEdge(2, CONCERNS, Source(1, None), 11),
        BracketEdge(3, PART_OF, 10, 12),
    )


# --- the property -----------------------------------------------------------------
#
# Entities 1 to 6, events 101 to 103 with units 1 to 4. The oracle walks
# upward from what an assignment points at; `members` walks downward from the
# bracket. The two walks share nothing but the edges.

ENTITIES = st.integers(min_value=1, max_value=6)
EVENTS = st.integers(min_value=101, max_value=103)
UNITS = st.integers(min_value=1, max_value=4)
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
ASSIGNMENTS = st.lists(st.tuples(STARTS, ENTITIES), max_size=10)
# Edges `members` must not read: another kind, an assignment that starts at
# an entity, a `part_of` that starts at an event.
NOISE = st.lists(
    st.one_of(
        st.tuples(st.just("holds"), ENTITIES, ENTITIES),
        st.tuples(st.just(CONCERNS), ENTITIES, ENTITIES),
        st.tuples(st.just(PART_OF), STARTS, ENTITIES),
    ),
    max_size=4,
)


def _wholes(start: int, parts: list[tuple[int, int]]) -> set[int]:
    """`start` and everything it is part of, by following `part_of` from
    part to whole."""
    reached = {start}
    changed = True
    while changed:
        changed = False
        for part, whole in parts:
            if part in reached and whole not in reached:
                reached.add(whole)
                changed = True
    return reached


def _belongs(
    event: int,
    seq: int,
    bracket: int,
    parts: list[tuple[int, int]],
    assignments: list[tuple[Source, int]],
) -> bool:
    own = [to for start, to in assignments if start.event == event and seq in (start.units or ())]
    general = [to for start, to in assignments if start.event == event and start.units is None]
    targets = own or general
    return any(bracket in _wholes(target, parts) for target in targets)


@settings(deadline=None, max_examples=400)
@given(
    parts=PARTS,
    assignments=ASSIGNMENTS,
    noise=NOISE,
    bracket=st.integers(min_value=1, max_value=7),
)
def test_a_unit_belongs_by_its_own_assignments_else_by_its_events(
    parts: list[tuple[int, int]],
    assignments: list[tuple[Source, int]],
    noise: list[tuple[str, int | Source, int]],
    bracket: int,
) -> None:
    """Review Focus 4 of the 2026-10-15 assignments plan, phase 2: a unit
    with an assignment of its own to another bracket does not appear in the
    bracket of its event, and a unit without one does."""
    edges = [
        *(BracketEdge(0, PART_OF, part, whole) for part, whole in parts),
        *(BracketEdge(0, CONCERNS, start, to) for start, to in assignments),
        *(BracketEdge(0, kind, start, to) for kind, start, to in noise),
    ]
    found = members(edges, bracket)

    for event in range(101, 104):
        for seq in range(1, 5):
            expected = _belongs(event, seq, bracket, parts, assignments)
            assert found.holds(event, seq) == expected, (event, seq)


def test_the_property_meets_a_unit_whose_own_assignment_replaces_its_events() -> None:
    """A fixed example of what the property is about, so a reader sees it
    without a seed: unit 2 is assigned elsewhere, unit 1 inherits."""
    edges = [
        BracketEdge(0, CONCERNS, Source(101, None), 1),
        BracketEdge(0, CONCERNS, Source(101, (2,)), 2),
    ]
    found = members(edges, 1)

    assert (found.holds(101, 1), found.holds(101, 2)) == (True, False)
    assert replace(found, excluded={}).holds(101, 2)
