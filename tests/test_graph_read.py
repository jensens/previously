# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading the graph from its projection ({ref}`graph-projection`).

The assurance is that a reader shows what it showed when it folded the
log: `ProjectedGraph` answers every question of `Graph` as the fold of the
whole log does, which the history below holds for one of each kind of
thread, and the property in `tests/test_projection_graph.py` for random
histories. The command line and the MCP server hold their listings against
the fold in their own test files.
"""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import UTC
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.append import append
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.assertions import write_statements
from previously.core.classes import ApprovalClass
from previously.core.classes import set_class
from previously.core.errors import ProjectionNotBuilt
from previously.core.errors import ProjectionRebuilt
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import Graph
from previously.core.graph import Period
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import STANDING
from previously.core.graph_read import differences
from previously.core.graph_read import graph_snapshot
from previously.core.graph_read import projected_graph
from previously.core.graph_read import read_brackets
from previously.core.graph_read import reader_bracket_edges
from previously.core.graph_read import REBUILD_RETRIES
from previously.core.graph_write import read_graph
from previously.core.graph_write import write_claims
from previously.core.members import bracket_edges
from previously.core.members import bracket_kinds
from previously.core.members import members
from previously.core.projection import GRAPH
from previously.core.projection.worker import catch_up
from previously.core.redact import redact_event
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import read_vocabulary
from previously.storage.postgres import PostgresStorage
from typing import override
from typing import TYPE_CHECKING

import contextlib
import pytest


if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Sequence
    from previously.contract.rows import EventRow
    from sqlalchemy import Connection
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 15, 9, 0, 0, tzinfo=UTC)
MODEL = model_author("claude")
PEOPLE = ApprovalClass(
    "claude_people",
    MODEL,
    ENTITY,
    frozenset({"person"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)
FIRST_MAIL = Source(1, None)


def _mail(external_id: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two."), RawUnit(3, "Three.")),
        payload={"text": "One. Two. Three."},
        channel_identities=(ChannelIdentity("email", "from", "anna@huber.example"),),
    )


def entity(
    kind: str,
    name: str,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    subject: int | None = None,
    confidence: int | None = None,
    state: str = ACTIVE,
    contests: int | None = None,
) -> Claim:
    return Claim(
        ENTITY,
        author,
        responsibility,
        SOURCES,
        (FIRST_MAIL,),
        None,
        None,
        subject,
        None,
        None,
        confidence,
        contests,
        EntityBody(kind, "de", {"name": name}, state),
    )


def relation(
    kind: str,
    start: int | Source,
    to: int | None,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    confidence: int | None = None,
    candidates: tuple[int, ...] | None = None,
    period: Period | None = None,
    subject: int | None = None,
    state: str = STANDING,
) -> Claim:
    sources = (start,) if isinstance(start, Source) else (FIRST_MAIL,)
    return Claim(
        RELATION,
        author,
        responsibility,
        SOURCES,
        sources,
        None,
        None,
        subject,
        None,
        None,
        confidence,
        None,
        RelationBody(kind, start, to, candidates, period, {}, state),
    )


def _write(storage: PostgresStorage, *claims: Claim) -> tuple[int, ...]:
    return write_claims(storage, storage, claims, recorded_at=T0).ids


def _project(storage: PostgresStorage) -> None:
    catch_up(storage, storage, GRAPH, rebuild=True)


class _Counting(PostgresStorage):
    """The real store, counting the rows `events_by_id` reads: what folding
    a thread from the log costs."""

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine)
        self.fetched: list[int] = []

    @override
    def events_by_id(self, conn: Connection, event_ids: Sequence[int]) -> dict[int, EventRow]:
        self.fetched.extend(event_ids)
        return super().events_by_id(conn, event_ids)


def _history(db: Engine) -> tuple[_Counting, dict[str, int]]:
    """One thread of every kind the readers tell apart: entities the
    operator stands for, one retracted, one with an objection pending, a
    model's proposal of a new one and one standing transitive under a class,
    a relation with a period, a question, a rejected proposal, an
    assignment of a mail and one of a unit, a part of a project, and a
    version erased."""
    storage = _Counting(db)
    append(storage, [_mail(f"m{n}") for n in (1, 2)], recorded_at=T0)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    set_class(storage, PEOPLE, statement="good at people", recorded_at=T0)
    ids: dict[str, int] = {}
    ids["anna"], ids["bert"], ids["xz"], ids["party"], ids["club"] = _write(
        storage,
        entity("person", "Anna"),
        entity("person", "Bert"),
        entity("project", "XZ"),
        entity("matter", "Sommerfest"),
        entity("organization", "Verein"),
    )
    (ids["gone"],) = _write(storage, entity("person", "Gone"))
    _write(storage, entity("person", "Gone", subject=ids["gone"], state=RETRACTED))
    ids["guess"], ids["through"] = _write(
        storage,
        entity("person", "Clara", author=MODEL, responsibility=OPEN, confidence=40),
        entity("person", "Dora", author=MODEL, responsibility=OPEN, confidence=90),
    )
    (ids["objection"],) = _write(
        storage,
        entity(
            "person",
            "Anna Huber",
            author=MODEL,
            responsibility=OPEN,
            confidence=40,
            subject=ids["anna"],
            contests=ids["anna"],
        ),
    )
    ids["involved"], ids["part"], ids["mail"], ids["unit"] = _write(
        storage,
        relation("involved_in", ids["anna"], ids["xz"], period=Period(date(2026, 1, 1), None)),
        relation("part_of", ids["party"], ids["club"]),
        relation("concerns", Source(2, None), ids["xz"]),
        relation("concerns", Source(2, (3,)), ids["party"]),
    )
    ids["question"], ids["rejected"], ids["erased"] = _write(
        storage,
        relation(
            "involved_in",
            ids["bert"],
            None,
            author=MODEL,
            responsibility=OPEN,
            confidence=40,
            candidates=(ids["xz"], ids["party"]),
        ),
        relation(
            "concerns",
            Source(1, (1,)),
            ids["club"],
            author=MODEL,
            responsibility=OPEN,
            confidence=40,
        ),
        entity("person", "Erased"),
    )
    rejection = Statement(
        REJECTION,
        OPERATOR,
        DIRECT,
        (Source(1, (1,)),),
        None,
        None,
        None,
        None,
        ids["rejected"],
        None,
    )
    write_statements(storage, storage, [rejection], recorded_at=T0)
    redact_event(storage, storage, ids["erased"], reason="wrong", recorded_at=T0)
    _project(storage)
    return storage, ids


def _answers(graph: Graph, ids: dict[str, int]) -> tuple[object, ...]:
    """Every question `Graph` answers, each asked so that it narrows."""
    return (
        graph.winners(ENTITY),
        graph.winners(RELATION),
        graph.winners(ENTITY, types=("person",)),
        dict(graph.entities()),
        graph.entity_kinds(),
        dict(graph.relations()),
        dict(graph.relations(at=date(2025, 12, 31))),
        dict(graph.relations(at=date(2026, 1, 1))),
        dict(graph.relations(types=("concerns",))),
        dict(graph.relations(start=ids["anna"])),
        dict(graph.relations(to=ids["xz"])),
        {name: dict(graph.relations(touching=subject)) for name, subject in ids.items()},
        dict(graph.waiting()),
        dict(graph.objected()),
        dict(graph.under(graph.classes)),
        {name: graph.threads.get(subject) for name, subject in ids.items()},
    )


@pytest.mark.db
def test_a_graph_read_from_the_projection_answers_every_question_as_the_fold_does(
    db: Engine,
) -> None:
    storage, ids = _history(db)
    with storage.snapshot() as conn:
        folded = read_graph(storage, conn)
        projected = projected_graph(storage, storage, conn)
        expected, found = _answers(folded, ids), _answers(projected, ids)
        # The history holds what it was built for: each question has an
        # answer to give, so that agreeing is not agreeing on nothing.
        assert set(folded.waiting()) == {ids["anna"], ids["guess"], ids["question"]}
        assert set(folded.objected()) == {ids["anna"]}
        assert set(folded.under(folded.classes)) == {ids["through"]}
        assert ids["gone"] in folded.winners(ENTITY)
        assert ids["gone"] not in folded.entities()
    assert found == expected


@pytest.mark.db
def test_a_thread_is_folded_from_the_log_when_it_is_asked_for_and_once(db: Engine) -> None:
    """Opening the graph reads no thread; the first question of a thread
    folds it, the second does not read it again; asking for what waits
    folds what waits and the entities its relations name, and nothing
    else."""
    storage, ids = _history(db)
    with storage.snapshot() as conn:
        storage.fetched.clear()
        graph = projected_graph(storage, storage, conn)
        assert storage.fetched == []
        assert graph.threads[ids["bert"]].subject == ids["bert"]
        assert ids["bert"] in storage.fetched
        storage.fetched.clear()
        assert graph.threads.get(ids["bert"]) is not None
        assert storage.fetched == []
        assert set(graph.waiting()) == {ids["anna"], ids["guess"], ids["question"]}
        # The question names its candidates, which come along; the other
        # threads of the log are not read.
        read = set(storage.fetched)
        assert {ids["anna"], ids["guess"], ids["question"], ids["xz"], ids["party"]} <= read
        assert ids["club"] not in read
        assert ids["involved"] not in read


@pytest.mark.db
def test_walking_every_thread_folds_every_thread_there_is(db: Engine) -> None:
    """The way of last resort, for a reader that walks the whole graph: it
    gives every thread the fold gives, the erased one not, each the same."""
    storage, ids = _history(db)
    with storage.snapshot() as conn:
        folded = read_graph(storage, conn)
        projected = projected_graph(storage, storage, conn)
        assert list(projected.threads) == sorted(folded.threads)
        assert ids["erased"] not in projected.threads
        assert dict(projected.threads) == dict(folded.threads)
        assert len(projected.threads) == len(folded.threads)


@pytest.mark.db
def test_the_store_narrows_relations_by_kind_end_and_day(db: Engine) -> None:
    """The period of a relation holds on both its days, and an open end on
    every day on its side, as `Period.holds` says."""
    storage, ids = _history(db)
    (ended,) = _write(
        storage,
        relation(
            "involved_in",
            ids["bert"],
            ids["xz"],
            period=Period(date(2025, 3, 1), date(2025, 3, 31)),
        ),
    )
    _project(storage)

    def subjects(
        *,
        at: date | None = None,
        types: list[str] | None = None,
        start: int | None = None,
        to: int | None = None,
        touching: int | None = None,
    ) -> list[int]:
        with storage.snapshot() as conn:
            found = storage.graph_relations(
                conn, at=at, types=types, start=start, to=to, touching=touching
            )
        return [row.subject for row in found]

    assert subjects(at=date(2025, 3, 1)) == [ids["part"], ids["mail"], ids["unit"], ended]
    assert subjects(at=date(2025, 3, 31)) == [ids["part"], ids["mail"], ids["unit"], ended]
    assert subjects(at=date(2025, 4, 1)) == [ids["part"], ids["mail"], ids["unit"]]
    assert ids["involved"] in subjects(at=date(2026, 1, 1))
    assert ids["involved"] not in subjects(at=date(2025, 12, 31))
    assert subjects(types=["concerns"]) == [ids["mail"], ids["unit"]]
    assert subjects(start=ids["bert"]) == [ended]
    assert subjects(to=ids["xz"]) == [ids["involved"], ids["mail"], ended]
    assert subjects(touching=ids["party"]) == [ids["part"], ids["unit"]]


@pytest.mark.db
def test_differences_name_a_missing_row_an_extra_one_and_a_column_that_differs(
    db: Engine,
) -> None:
    storage, ids = _history(db)
    with storage.snapshot() as conn:
        folded = read_graph(storage, conn)
        rows = storage.read_graph_threads(conn)
    # The control: the rows as they stand differ in nothing.
    assert differences(rows, folded) == []
    by_subject = {row.subject: row for row in rows}
    edits = {
        ids["bert"]: {"objections": 3, "level": OPEN},
        ids["involved"]: {"period_start": None},
        ids["question"]: {"candidates": None, "question": False},
    }
    changed = [
        replace(row, **edits.get(row.subject, {})) for row in rows if row.subject != ids["xz"]
    ]
    extra = replace(by_subject[ids["club"]], subject=ids["erased"], winner_id=ids["erased"])
    assert differences([*changed, extra], folded) == [
        (ids["bert"], "level open instead of direct, objections 3 instead of 0"),
        (ids["xz"], f"no row instead of winner {ids['xz']}"),
        (ids["involved"], "period_start - instead of 2026-01-01"),
        (
            ids["question"],
            f"candidates - instead of {ids['xz']},{ids['party']}, question false instead of true",
        ),
        (ids["erased"], f"winner {ids['erased']} instead of no row"),
    ]


@pytest.mark.db
def test_the_members_of_a_bracket_read_from_the_projection_are_those_of_the_fold(
    db: Engine,
) -> None:
    """The edges `members` reads are the rows of the projection: the same
    events and units for every bracket as from the edges of the fold, the
    proposal that stands among them, the rejected one not."""
    storage, ids = _history(db)
    (proposed,) = _write(
        storage,
        relation(
            "concerns",
            Source(1, (2,)),
            ids["club"],
            author=MODEL,
            responsibility=OPEN,
            confidence=40,
        ),
    )
    _project(storage)
    with storage.snapshot() as conn:
        vocabulary = read_vocabulary(storage, conn)
        edges = bracket_edges(read_graph(storage, conn), vocabulary)
        kinds = bracket_kinds(vocabulary)
        for bracket in ids.values():
            expected = members(edges, bracket, kinds)
            assert read_brackets(storage, storage, conn, bracket) == expected
        club = read_brackets(storage, storage, conn, ids["club"])
    assert proposed in {edge.subject for edge in edges}
    assert club.holds(1, 2)
    assert not club.holds(1, 1)
    assert club.holds(2, 3)


def _projection_rows(db: Engine) -> tuple[object, ...]:
    """Everything of the graph projection: its state row and both tables."""
    from sqlalchemy import text

    with db.begin() as c:
        return (
            c.execute(text("SELECT * FROM projection_state WHERE name = 'graph'")).all(),
            c.execute(text("SELECT * FROM p_graph_thread ORDER BY subject")).all(),
            c.execute(text("SELECT * FROM p_graph_version ORDER BY id")).all(),
        )


class _RebuiltBeforeSnapshot(PostgresStorage):
    """The real store, where `previously project` empties the graph
    projection, at its own version, between a reader's catch-up and its
    snapshot, as after an operator deleted the state row: before each of the
    first `misses` snapshots, the state row goes back to `up_to_id` 0 and the
    tables are emptied. Every snapshot after those finds it as it is."""

    def __init__(self, engine: Engine, misses: int) -> None:
        super().__init__(engine)
        self.misses = misses
        self.snapshots = 0

    @override
    @contextlib.contextmanager
    def snapshot(self) -> Generator[Connection]:
        from sqlalchemy import text

        self.snapshots += 1
        if self.snapshots <= self.misses:
            with self.begin() as conn:
                conn.execute(text("UPDATE projection_state SET up_to_id = 0 WHERE name = 'graph'"))
                conn.execute(text("DELETE FROM p_graph_thread"))
                conn.execute(text("DELETE FROM p_graph_version"))
        with super().snapshot() as conn:
            yield conn


def _listed(storage: PostgresStorage) -> list[int]:
    """The entities a reader lists, read in `graph_snapshot`."""
    with graph_snapshot(storage, storage, storage) as conn:
        return sorted(projected_graph(storage, storage, conn).winners(ENTITY))


@pytest.mark.db
@pytest.mark.parametrize(
    "change",
    [
        "DELETE FROM projection_state WHERE name = 'graph'",
        "UPDATE projection_state SET version = version + 1 WHERE name = 'graph'",
    ],
    ids=["no-state-row", "other-version"],
)
def test_a_reader_meeting_a_projection_it_would_have_to_build_fails_and_touches_nothing(
    db: Engine, change: str
) -> None:
    """Ruling F-c of the 2026-10-15 assignments plan: only `previously
    project` builds. A reader meeting no state row, or one at another
    version, fails with the sentence that names `previously project`, and
    the state row and both tables are what they were, the rows of the
    version it met included. Measured red by letting `graph_snapshot` catch
    up with `rebuild=True`: the read succeeds, and the rows are rebuilt."""
    from sqlalchemy import text

    storage, _ids = _history(db)
    with db.begin() as c:
        c.execute(text(change))
    before = _projection_rows(db)
    with pytest.raises(ProjectionNotBuilt) as raised:
        _listed(storage)
    found = (
        "is not built" if change.startswith("DELETE") else f"stands at version {GRAPH.version + 1}"
    )
    assert str(raised.value).startswith(f"projection graph {found}, and this code declares ")
    assert "`previously project`" in str(raised.value)
    assert _projection_rows(db) == before
    # The control: `previously project` builds it, and the reader reads.
    _project(storage)
    assert _listed(storage)


@pytest.mark.db
def test_a_rebuild_between_catch_up_and_snapshot_is_caught_up_once_more_and_then_read(
    db: Engine,
) -> None:
    """Ruling F-c of the 2026-10-15 assignments plan: a `previously project`
    that empties the projection at its own version between a reader's
    catch-up and its snapshot costs one more catch-up, which carries the
    build on, and the reader reads the graph it would have read. Measured
    red with `REBUILD_RETRIES` at 0: `ProjectionRebuilt`."""
    _history(db)
    expected = _listed(PostgresStorage(db))
    assert expected
    rebuilt = _RebuiltBeforeSnapshot(db, misses=1)
    assert _listed(rebuilt) == expected
    assert rebuilt.snapshots == 2


@pytest.mark.db
def test_two_rebuilds_in_a_row_fail_the_reader_though_a_third_try_would_read(
    db: Engine,
) -> None:
    """One retry, not two: with the projection emptied before each of the
    first two snapshots, a third try would read, and is not taken. Measured
    red with `REBUILD_RETRIES` at 2: the read succeeds on the third
    snapshot."""
    _history(db)
    assert REBUILD_RETRIES == 1
    rebuilt = _RebuiltBeforeSnapshot(db, misses=2)
    with pytest.raises(ProjectionRebuilt, match="on each of 2 tries"):
        _listed(rebuilt)
    assert rebuilt.snapshots == 2
    # The control: the same store, past its misses, reads.
    assert _listed(rebuilt)
    assert rebuilt.snapshots == 3


@pytest.mark.db
def test_a_version_change_between_catch_up_and_snapshot_is_not_caught_up_again(
    db: Engine,
) -> None:
    """A projection rebuilt at another version in between is no miss to
    retry: a catch-up cannot change a version, and the reader fails at the
    first snapshot that finds it."""
    from sqlalchemy import text

    _history(db)

    class _OtherVersion(PostgresStorage):
        snapshots = 0

        @override
        @contextlib.contextmanager
        def snapshot(self) -> Generator[Connection]:
            _OtherVersion.snapshots += 1
            with self.begin() as conn:
                conn.execute(text("UPDATE projection_state SET version = 7 WHERE name = 'graph'"))
            with super().snapshot() as conn:
                yield conn

    with pytest.raises(ProjectionNotBuilt, match="stands at version 7"):
        _listed(_OtherVersion(db))
    assert _OtherVersion.snapshots == 1


@pytest.mark.db
def test_a_reader_finds_a_brackets_edges_in_the_projection_and_refuses_a_fold(
    db: Engine,
) -> None:
    """Ruling F-e of the 2026-10-15 assignments plan: a reader has one way to
    the graph, so `reader_bracket_edges` takes the edges from the rows of the
    projection and refuses a fold handed in, rather than walk the fold.
    Measured red by giving the fold branch back. The control: the graph read
    from the projection gives the edges the fold gives."""
    storage, _ids = _history(db)
    with graph_snapshot(storage, storage, storage) as conn:
        projected, kinds = reader_bracket_edges(
            storage, conn, projected_graph(storage, storage, conn)
        )
        folded = read_graph(storage, conn)
        expected = bracket_edges(folded, read_vocabulary(storage, conn))
        assert set(projected) == set(expected)
        assert len(projected) == len(expected) > 0
        assert kinds == bracket_kinds(read_vocabulary(storage, conn))
        with pytest.raises(TypeError, match="this graph is a fold"):
            reader_bracket_edges(storage, conn, folded)
