# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle shows observations, and only those ({ref}`projections`);
and of a bracket, the units that belong to it ({ref}`chronicle-of-a-bracket`)."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from hypothesis import given
from hypothesis import HealthCheck
from hypothesis import settings
from hypothesis import strategies as st
from previously.contract.rows import ProjectionState
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import MODEL_CALL
from previously.core.append import append
from previously.core.members import chronicle_selection
from previously.core.members import Members
from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.worker import catch_up
from previously.core.units import split_plaintext
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text

import pytest


NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)


def _observation() -> RawEvent:
    return RawEvent(
        source="email",
        external_id="m-1",
        occurred_at=NOW,
        evidence=Evidence.VERBATIM,
        units=split_plaintext("one\n\ntwo"),
        payload={"text": "one\n\ntwo"},
    )


def _rows(db: Engine) -> list[tuple[object, ...]]:
    with db.begin() as conn:
        return [
            tuple(r) for r in conn.execute(text("SELECT * FROM p_chronicle ORDER BY event_id, seq"))
        ]


def _write_both(storage: PostgresStorage) -> None:
    append(storage, [_observation()], recorded_at=NOW)
    append_action(
        storage,
        {"action": MODEL_CALL},
        (RawUnit(seq=1, content="the answer of a model"),),
        recorded_at=NOW,
    )


@pytest.mark.db
def test_an_action_with_units_is_not_in_the_chronicle_and_an_observation_is(db: Engine) -> None:
    storage = PostgresStorage(db)
    _write_both(storage)
    catch_up(storage, storage, CHRONICLE)
    rows = _rows(db)
    assert [(r[0], r[1]) for r in rows] == [(1, 1), (1, 2)]
    assert {r[4] for r in rows} == {"observation"}


@pytest.mark.db
def test_the_upgrade_to_version_3_rebuilds_and_ends_as_a_fresh_build(db: Engine) -> None:
    """A table that version 2 built holds the rows of an action's units. The
    state row says version 2, the rows are put in by hand the way version 2
    derived them, and the first catch-up of version 3 rebuilds the table."""
    storage = PostgresStorage(db)
    _write_both(storage)
    catch_up(storage, storage, CHRONICLE)
    fresh = _rows(db)
    with db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO p_chronicle (event_id, seq, content, occurred_at, kind) "
                "VALUES (2, 1, 'the answer of a model', :t, 'action')"
            ),
            {"t": NOW},
        )
    with storage.begin() as conn:
        storage.set_projection_state(conn, ProjectionState("chronicle", 2, 2, NOW))
    assert len(_rows(db)) == len(fresh) + 1

    outcome = catch_up(storage, storage, CHRONICLE)
    assert outcome.rebuilt_from == 2
    assert _rows(db) == fresh


# --- the units of a bracket, selected in the query ----------------------------------
#
# Three observations of four units each, the second the earliest, so that the
# order of the chronicle is not the order of the ids. The selections name
# event 4 and unit 5 too, which the log doesn't have.

_EVENT_IDS = st.integers(min_value=1, max_value=4)
_SEQS = st.integers(min_value=1, max_value=5)


@st.composite
def _members(draw: st.DrawFn) -> Members:
    events = draw(
        st.dictionaries(_EVENT_IDS, st.one_of(st.none(), st.frozensets(_SEQS, min_size=1)))
    )
    excluded = {
        event: draw(st.frozensets(_SEQS, min_size=1))
        for event, units in sorted(events.items())
        if units is None and draw(st.booleans())
    }
    return Members(frozenset(), events, excluded)


def _three_observations(storage: PostgresStorage) -> None:
    """Writes them once, for every example of the property to read."""
    with storage.begin() as conn:
        if storage.tip(conn) is not None:
            return
    for number, hours in enumerate((2, 0, 1), 1):
        raw = RawEvent(
            source="email",
            external_id=f"m-{number}",
            occurred_at=NOW + timedelta(hours=hours),
            evidence=Evidence.VERBATIM,
            units=split_plaintext("a\n\nb\n\nc\n\nd"),
            payload={"text": "a b c d"},
        )
        append(storage, [raw], recorded_at=NOW)
    catch_up(storage, storage, CHRONICLE)


@pytest.mark.db
@settings(
    max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(found=_members(), limit=st.integers(min_value=1, max_value=13))
def test_the_query_selects_the_units_a_bracket_holds_before_its_limit(
    db: Engine, found: Members, limit: int
) -> None:
    """`chronicle_selection` and the query of `read_chronicle` together
    select exactly the units `Members.holds` holds, in the order of the
    chronicle, and the limit counts only those: the whole chronicle,
    filtered by `holds` in Python, is the oracle."""
    storage = PostgresStorage(db)
    _three_observations(storage)
    selection = chronicle_selection(found)
    with storage.begin() as conn:
        everything = storage.read_chronicle(conn, since=None, until=None, limit=100)
        selected = storage.read_chronicle(conn, since=None, until=None, limit=100, within=selection)
        limited = storage.read_chronicle(
            conn, since=None, until=None, limit=limit, within=selection
        )
    assert len(everything) == 12
    expected = [row for row in everything if found.holds(row.event_id, row.seq)]
    assert selected == expected
    assert limited == expected[:limit]


@pytest.mark.db
def test_the_query_meets_each_form_of_a_bracket(db: Engine) -> None:
    """A fixed example of the property, so a reader sees it without a seed:
    the whole of event 1 but its unit 3, units 2 and 4 of event 2, and
    nothing of event 3."""
    storage = PostgresStorage(db)
    _three_observations(storage)
    found = Members(frozenset(), {1: None, 2: frozenset({2, 4})}, {1: frozenset({3})})
    with storage.begin() as conn:
        rows = storage.read_chronicle(
            conn, since=None, until=None, limit=100, within=chronicle_selection(found)
        )
    assert [(row.event_id, row.seq) for row in rows] == [(2, 2), (2, 4), (1, 1), (1, 2), (1, 4)]
