# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection `graph` ({ref}`graph-projection`).

The assurance is `test_property_the_projection_stands_where_the_fold_does`:
random histories of versions at every level, rejections, approvals,
erasures and class events, caught up at random points and in batches of
random size, and after every catch-up each row of `p_graph_thread` is what
`fold_graph` over the whole log makes of its thread. The tests before it
name one way each that a thread changes, so that a mutation that stops
marking one of them fails a test that says which.
"""

from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from hypothesis import given
from hypothesis import HealthCheck
from hypothesis import settings
from hypothesis import strategies as st
from previously.contract.rows import GraphThreadRow
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
from previously.core.assertions import AssertionRefused
from previously.core.assertions import write_statements
from previously.core.classes import ApprovalClass
from previously.core.classes import ClassRefused
from previously.core.classes import read_classes
from previously.core.classes import set_class
from previously.core.errors import RedactionRefused
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import Graph
from previously.core.graph import Period
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import SOURCES
from previously.core.graph import STANDING
from previously.core.graph import TRANSITIVE
from previously.core.graph_read import check_graph
from previously.core.graph_read import projected_graph
from previously.core.graph_read import read_brackets
from previously.core.graph_write import GraphRefused
from previously.core.graph_write import read_graph
from previously.core.graph_write import write_claims
from previously.core.members import bracket_edges
from previously.core.members import bracket_kinds
from previously.core.members import members
from previously.core.projection import GRAPH
from previously.core.projection import PROJECTIONS
from previously.core.projection.graph import summary
from previously.core.projection.worker import catch_up
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import read_vocabulary
from previously.storage.postgres import PostgresStorage
from previously.storage.schema import p_graph_thread
from previously.storage.schema import p_graph_version
from sqlalchemy import Engine
from sqlalchemy import Text
from sqlalchemy import text
from typing import TYPE_CHECKING

import contextlib
import pytest
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence
    from previously.contract.rows import ProjectionState
    from previously.core.projection.worker import Outcome
    from sqlalchemy import Connection


T0 = datetime(2026, 10, 15, 9, 0, 0, tzinfo=UTC)
MODEL = model_author("claude")

PEOPLE = ApprovalClass(
    "claude_people",
    MODEL,
    ENTITY,
    frozenset({"person", "project"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)
ASSIGNMENTS = ApprovalClass(
    "claude_assignments",
    MODEL,
    RELATION,
    frozenset({"concerns"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)
CLASSES = (PEOPLE, ASSIGNMENTS)
MAILS = 3
# A random history erases some of its mails, and has more to rest on.
HISTORY_MAILS = 6
FIRST_MAIL = Source(1, None)


def _mail(external_id: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two.")),
        payload={"text": "One. Two."},
        channel_identities=(ChannelIdentity("email", "from", "anna@huber.example"),),
    )


def _setup(db: Engine, mails: int = MAILS) -> PostgresStorage:
    """Mails 1 to `mails`, the base vocabulary, and the two classes."""
    storage = PostgresStorage(db)
    append(storage, [_mail(f"m{n}") for n in range(1, mails + 1)], recorded_at=T0)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    for item in CLASSES:
        set_class(storage, item, statement="the model is good at this", recorded_at=T0)
    return storage


def entity(
    kind: str,
    name: str,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    source: Source = FIRST_MAIL,
    subject: int | None = None,
    confidence: int | None = None,
) -> Claim:
    return Claim(
        ENTITY,
        author,
        responsibility,
        SOURCES,
        (source,),
        None,
        None,
        subject,
        None,
        None,
        confidence,
        None,
        EntityBody(kind, "de", {"name": name}, ACTIVE),
    )


def relation(
    kind: str,
    start: int | Source,
    to: int | None,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    source: Source = FIRST_MAIL,
    subject: int | None = None,
    confidence: int | None = None,
    candidates: tuple[int, ...] | None = None,
    period: Period | None = None,
) -> Claim:
    """A relation resting on `source`, or on its start where it starts at
    an event."""
    sources = (start,) if isinstance(start, Source) else (source,)
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
        RelationBody(kind, start, to, candidates, period, {}, STANDING),
    )


def _write(storage: PostgresStorage, *claims: Claim, at: datetime = T0) -> tuple[int, ...]:
    return write_claims(storage, storage, claims, recorded_at=at).ids


def _reject(
    storage: PostgresStorage,
    of: int,
    *,
    sources: tuple[Source, ...] = (FIRST_MAIL,),
    at: datetime = T0,
) -> int:
    """The operator's rejection of `of`, which takes the sources of what it
    rejects."""
    rejection = Statement(REJECTION, OPERATOR, DIRECT, sources, None, None, None, None, of, None)
    (rejection_id,) = write_statements(storage, storage, [rejection], recorded_at=at)
    return rejection_id


def _project(storage: PostgresStorage, *, batch_size: int = 500) -> None:
    catch_up(storage, storage, GRAPH, batch_size=batch_size)


def _rows(storage: PostgresStorage) -> list[GraphThreadRow]:
    with storage.begin() as conn:
        return storage.read_graph_threads(conn)


def _folded(storage: PostgresStorage) -> list[GraphThreadRow]:
    """What `fold_graph` over the whole log makes of every thread, under the
    classes in force: the oracle."""
    with storage.begin() as conn:
        graph = read_graph(storage, conn)
        classes = read_classes(storage, conn).states
    found = [summary(thread, classes) for thread in graph.threads.values()]
    return sorted((row for row in found if row is not None), key=lambda row: row.subject)


def _snapshot(db: Engine) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    with db.begin() as c:
        versions = [tuple(r) for r in c.execute(text("SELECT * FROM p_graph_version ORDER BY id"))]
        threads = [
            tuple(r) for r in c.execute(text("SELECT * FROM p_graph_thread ORDER BY subject"))
        ]
    return versions, threads


def _rebuilt(storage: PostgresStorage, db: Engine) -> tuple[object, ...]:
    """Both tables after a rebuild from nothing, in one batch per event."""
    with storage.begin() as c:
        storage.truncate_projection(c, GRAPH.name)
        c.execute(text("DELETE FROM projection_state WHERE name = 'graph'"))
    _project(storage, batch_size=1)
    return _snapshot(db)


def _row(storage: PostgresStorage, subject: int) -> GraphThreadRow | None:
    return next((row for row in _rows(storage) if row.subject == subject), None)


def _level(storage: PostgresStorage, subject: int) -> str:
    row = _row(storage, subject)
    assert row is not None
    return row.level


# --- The tables -------------------------------------------------------------------


def test_the_tables_hold_ids_counts_and_vocabulary_words_and_no_content() -> None:
    """No content in the projection (decision 5 of the 2026-10-15
    assignments plan): what a reader shows it reads from the log by id, so an
    erasure holds without the projection deleting content. The column names
    are held here, and the only text columns are words of the vocabulary and
    of the fold — measured red with a column `name` added to `p_graph_thread`."""
    assert [column.name for column in p_graph_version.columns] == [
        "id",
        "subject",
        "kind",
        "under",
    ]
    assert [column.name for column in p_graph_thread.columns] == [
        "subject",
        "kind",
        "type",
        "winner_id",
        "level",
        "state",
        "start_entity",
        "start_event",
        "start_units",
        "to_entity",
        "candidates",
        "period_start",
        "period_end",
        "pending",
        "objections",
        "question",
    ]
    texts = [
        f"{table.name}.{column.name}"
        for table in (p_graph_version, p_graph_thread)
        for column in table.columns
        if isinstance(column.type, Text)
    ]
    assert texts == [
        "p_graph_version.kind",
        "p_graph_thread.kind",
        "p_graph_thread.type",
        "p_graph_thread.level",
        "p_graph_thread.state",
    ]


@pytest.mark.db
def test_a_rebuild_empties_both_tables(db: Engine) -> None:
    storage = _setup(db)
    _write(storage, entity("person", "Anna"))
    _project(storage)
    assert _snapshot(db) != ([], [])
    with storage.begin() as c:
        storage.truncate_projection(c, GRAPH.name)
    assert _snapshot(db) == ([], [])


def test_the_graph_is_the_third_projection_the_command_line_catches_up() -> None:
    assert [projection.name for projection in PROJECTIONS] == ["chronicle", "source-stats", "graph"]


# --- What a thread stands at ------------------------------------------------------


@pytest.mark.db
def test_an_entity_and_its_relations_stand_with_their_ends_and_level(db: Engine) -> None:
    storage = _setup(db)
    project, anna = _write(storage, entity("project", "XZ"), entity("person", "Anna"))
    whole, unit, involved = _write(
        storage,
        relation("concerns", Source(1, None), project),
        relation("concerns", Source(2, (2,)), project),
        relation("involved_in", anna, project, period=Period(date(2026, 1, 1), None)),
    )
    _project(storage)
    rows = {row.subject: row for row in _rows(storage)}
    assert rows[project] == GraphThreadRow(
        project, ENTITY, "project", project, DIRECT, ACTIVE,
        None, None, None, None, None, None, None, 0, 0, False,
    )  # fmt: skip
    assert rows[whole] == GraphThreadRow(
        whole, RELATION, "concerns", whole, DIRECT, STANDING,
        None, 1, None, project, None, None, None, 0, 0, False,
    )  # fmt: skip
    assert (rows[unit].start_event, rows[unit].start_units) == (2, (2,))
    assert (rows[involved].start_entity, rows[involved].start_event) == (anna, None)
    assert (rows[involved].period_start, rows[involved].period_end) == (date(2026, 1, 1), None)
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_a_question_stands_with_its_candidates_until_it_is_answered(db: Engine) -> None:
    storage = _setup(db)
    one, two = _write(storage, entity("project", "XZ"), entity("project", "YZ"))
    (asked,) = _write(
        storage,
        relation(
            "concerns", Source(1, None), None,
            author=MODEL, responsibility=OPEN, confidence=50, candidates=(one, two),
        ),
    )  # fmt: skip
    _project(storage)
    question = _row(storage, asked)
    assert question is not None
    assert (question.level, question.to_entity, question.candidates, question.question) == (
        OPEN,
        None,
        (one, two),
        True,
    )
    _write(storage, relation("concerns", Source(1, None), two, subject=asked))
    _project(storage)
    answered = _row(storage, asked)
    assert answered is not None
    assert (answered.level, answered.to_entity, answered.question) == (DIRECT, two, False)
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_a_model_version_under_a_class_is_transitive_and_its_objection_counts(
    db: Engine,
) -> None:
    storage = _setup(db)
    (anna,) = _write(storage, entity("person", "Anna"))
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=90)
    )
    (_objection,) = _write(
        storage,
        entity("person", "Anna H", author=MODEL, responsibility=OPEN, confidence=90, subject=anna),
    )
    _project(storage)
    assert _row(storage, guessed) is not None
    assert _level(storage, guessed) == TRANSITIVE
    anna_row = _row(storage, anna)
    assert anna_row is not None
    assert (anna_row.level, anna_row.pending, anna_row.objections) == (DIRECT, 1, 1)
    assert _rows(storage) == _folded(storage)


# --- Each way a thread changes, and the mutation each one is measured against -----


@pytest.mark.db
def test_an_erased_version_takes_its_thread_with_it(db: Engine) -> None:
    """A redaction of a version, read after the version: its thread has no
    winner left and loses its row. Measured red with the redactions of a batch
    marking nothing; the control, the thread beside it, keeps its row."""
    storage = _setup(db)
    anna, bert = _write(storage, entity("person", "Anna"), entity("person", "Bert"))
    _project(storage)
    redact_event(storage, storage, anna, reason="wrong person", recorded_at=T0)
    _project(storage)
    assert [row.subject for row in _rows(storage)] == [bert]
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_an_erased_mail_takes_its_assignment_by_the_cascade(db: Engine) -> None:
    """Review Focus 1: the mail is erased, the cascade erases the assignment
    with a redaction of its own, and the projection follows it."""
    storage = _setup(db)
    (project,) = _write(storage, entity("project", "XZ", source=Source(2, None)))
    (assigned,) = _write(storage, relation("concerns", Source(1, (2,)), project))
    _project(storage)
    assert _row(storage, assigned) is not None
    redact_units(storage, storage, 1, [2], reason="a third party", recorded_at=T0)
    _project(storage)
    assert _row(storage, assigned) is None
    assert [row.subject for row in _rows(storage)] == [project]
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_a_rejection_takes_the_proposal_it_rejects(db: Engine) -> None:
    storage = _setup(db)
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=10)
    )
    _project(storage)
    assert _row(storage, guessed) is not None
    _reject(storage, guessed)
    _project(storage)
    assert _row(storage, guessed) is None
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
@pytest.mark.parametrize("demote", [True, False], ids=["demote", "control"])
def test_a_class_revoked_with_demote_turns_what_stands_under_it_open(
    db: Engine, demote: bool
) -> None:
    """The class is revoked after the projection folded the version under it:
    with `demote` the version counts as open, without it it stays
    transitive. Measured red with a class event marking nothing."""
    storage = _setup(db)
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=90)
    )
    _project(storage)
    assert _level(storage, guessed) == TRANSITIVE
    set_class(
        storage,
        replace(PEOPLE, revoked=True, demote=demote),
        statement="no longer",
        recorded_at=T0,
    )
    _project(storage)
    assert _level(storage, guessed) == (OPEN if demote else TRANSITIVE)
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_an_erased_class_event_turns_what_stands_under_it_open(db: Engine) -> None:
    """A class event is an action, and an erasure can take it: what stood
    under it has no class left and counts as open."""
    storage = _setup(db)
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=90)
    )
    _project(storage)
    with storage.begin() as conn:
        _item, class_id = read_classes(storage, conn).by_name[PEOPLE.name]
    redact_event(storage, storage, class_id, reason="set by mistake", recorded_at=T0)
    _project(storage)
    assert _level(storage, guessed) == OPEN
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_a_thread_whose_first_version_was_erased_unread_keeps_its_later_ones(db: Engine) -> None:
    """The first version of a thread is erased before the projection ever
    read it, so it has no row in `p_graph_version`; a later version of the
    thread still stands in the fold, which takes an erased subject as one
    that was there. Measured red with the refold reading only the rows the
    table lists, without the subject itself: the thread had no row."""
    storage = _setup(db)
    (anna,) = _write(storage, entity("person", "Anna", source=Source(2, None)))
    (later,) = _write(storage, entity("person", "Anna Huber", subject=anna))
    redact_event(storage, storage, anna, reason="the first one was wrong", recorded_at=T0)
    _project(storage)
    row = _row(storage, anna)
    assert row is not None
    assert row.winner_id == later
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_an_approval_of_a_proposal_erased_unread_stands_as_the_fold_has_it(db: Engine) -> None:
    """A model objects to the operator's entity, the operator approves the
    objection, and the objection is erased before the projection read it,
    so it has no row in `p_graph_version`. The approval names an erased
    version, which counts for the fold, and the approval wins. A later
    objection folds the thread again in a batch of its own, where the
    erased version is no subject any batch touches, and the approval has to
    win there too. Measured red with the refold leaving out the erased rows
    a version names: the operator's first version won."""
    storage = _setup(db)
    (anna,) = _write(storage, entity("person", "Anna"))
    objection = entity(
        "person", "Anna H", author=MODEL, responsibility=OPEN, confidence=90,
        source=Source(2, None), subject=anna,
    )  # fmt: skip
    (objected,) = _write(storage, objection)
    approval = replace(objection, responsibility=DIRECT, approves=objected)
    (approved,) = _write(storage, approval)
    redact_event(storage, storage, objected, reason="wrong mail", recorded_at=T0)
    _project(storage)
    _write(storage, replace(objection, body=replace(objection.body, fields={"name": "Anna M"})))
    _project(storage)
    row = _row(storage, anna)
    assert row is not None
    assert (row.winner_id, row.objections) == (approved, 1)
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_an_erased_rejection_lets_its_proposal_wait_again(db: Engine) -> None:
    """`redact event` on a rejection: the fold no longer counts it, so the
    objection it rejected waits for the operator again, and its row leaves
    `p_graph_version`, as a rebuild would not write it. Measured red with the
    erasure of a rejection row touching only the rejection as a subject and
    not the thread it names: the thread kept `pending` 0."""
    storage = _setup(db)
    (anna,) = _write(storage, entity("person", "Anna"))
    (objected,) = _write(
        storage,
        entity("person", "Anna H", author=MODEL, responsibility=OPEN, confidence=90, subject=anna),
    )
    rejection = _reject(storage, objected)
    _project(storage)
    before = _row(storage, anna)
    assert before is not None
    assert (before.pending, before.objections) == (0, 0)
    redact_event(storage, storage, rejection, reason="rejected by mistake", recorded_at=T0)
    _project(storage)
    after = _row(storage, anna)
    assert after is not None
    assert (after.winner_id, after.pending, after.objections) == (anna, 1, 1)
    assert _rows(storage) == _folded(storage)
    versions = [row[0] for row in _snapshot(db)[0]]
    assert rejection not in versions
    assert versions == [anna, objected]


@pytest.mark.db
def test_an_objection_against_an_erased_direct_version_still_waits(db: Engine) -> None:
    """The operator writes a second direct version, the model objects to it
    (the write path sets `contests` to it), and the second version is erased
    and its row pruned. The objection contests an erased version, which the
    fold lets stand as a proposal; a later version folds the thread again in
    a batch where the erased version is no subject touched. Measured red
    with the refold reading only the erased rows `approves` names, not those
    `contests` names: the objection was dropped and `pending` was 1."""
    storage = _setup(db)
    (anna,) = _write(storage, entity("person", "Anna"))
    (second,) = _write(storage, entity("person", "Anna Huber", subject=anna))
    objection = entity(
        "person", "Anna H", author=MODEL, responsibility=OPEN, confidence=90,
        source=Source(2, None), subject=anna,
    )  # fmt: skip
    (objected,) = _write(storage, objection)
    redact_event(storage, storage, second, reason="wrong", recorded_at=T0)
    _project(storage)
    assert second not in [row[0] for row in _snapshot(db)[0]]
    _write(storage, replace(objection, body=replace(objection.body, fields={"name": "Anna M"})))
    _project(storage)
    row = _row(storage, anna)
    assert row is not None
    assert (row.winner_id, row.pending, row.objections) == (anna, 2, 1)
    assert objected in [version[0] for version in _snapshot(db)[0]]
    assert _rows(storage) == _folded(storage)


@pytest.mark.db
def test_incremental_equals_rebuilt_for_both_tables(db: Engine) -> None:
    """The rows of `p_graph_version` a rebuild would not write are taken out
    when their thread is folded again: an erased version, and the rejection
    of a version erased after it. Measured red with `_stale` returning
    nothing: the incremental path kept both rows."""
    storage = _setup(db)
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=10)
    )
    (anna,) = _write(storage, entity("person", "Anna"))
    _project(storage)
    _reject(storage, guessed)
    _project(storage)
    redact_event(storage, storage, guessed, reason="wrong", recorded_at=T0)
    _project(storage)
    incremental = _snapshot(db)
    assert [row[0] for row in incremental[0]] == [anna]
    assert _rebuilt(storage, db) == incremental


# --- Two catch-ups at once (Review Focus 5) ---------------------------------------


def _waiting_on_a_lock(db: Engine) -> bool:
    with db.connect() as c:
        return bool(
            c.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        )


class _Holding(PostgresStorage):
    """The real store, except that a catch-up through it stops once it has
    written the rows and the `up_to_id` of each of its batches, uncommitted,
    until `may_go_on()` is true; `holding` is set at the first."""

    def __init__(self, engine: Engine, may_go_on: Callable[[], bool]) -> None:
        super().__init__(engine)
        self.holding = threading.Event()
        self._may_go_on = may_go_on

    def set_projection_state(self, conn: Connection, state: ProjectionState) -> None:
        super().set_projection_state(conn, state)
        if state.up_to_id > 0:
            self.holding.set()
            deadline = time.monotonic() + 10
            while not self._may_go_on():
                assert time.monotonic() < deadline, "the other catch-up never came"
                time.sleep(0.01)


@pytest.mark.db
def test_two_catch_ups_at_once_write_every_row_once_and_end_where_the_fold_does(
    db: Engine,
) -> None:
    """Two readers catch up at the same moment, as two MCP calls or a call
    and the scheduled `project` would, over six events in batches of two.
    The first holds every batch uncommitted until the second waits at the
    state row or has returned. So each commit of the first hands the lock to
    a second that already waits for it, and PostgreSQL gives a row lock to
    the transaction that waited first: the second takes at least the batch
    after the first's last hold, starting where the first committed, and
    the turns follow by construction rather than by the scheduler. Holding
    only the first batch, as this test did before, left the two to race for
    the lock of the second batch, since the second's first wait is in the
    short transaction that checks the version, and under load the first
    could take all six events. Each, when it returns, finds
    the tables where the fold of the whole log is, so neither ended on half
    a state; no row is written twice — the primary key of `p_graph_version`
    would refuse the second — and a rebuild gives the same tables.

    Measured red with `lock_projection_state` reading the row without
    locking it, and with only its `FOR UPDATE` taken out: both times a
    catch-up read a batch the other had taken and failed on the primary key.
    With one batch, as this test ran before, the second variant stayed
    green: the second catch-up then waited at the placeholder insert of
    `lock_projection_state`, as `pg_stat_activity` showed."""
    storage = _setup(db)
    (project,) = _write(storage, entity("project", "XZ"))
    _project(storage)
    (guessed,) = _write(
        storage, entity("person", "Bert", author=MODEL, responsibility=OPEN, confidence=90)
    )
    _write(storage, relation("concerns", Source(1, None), project))
    _write(storage, relation("concerns", Source(2, (1,)), project))
    _reject(storage, guessed)
    (anna,) = _write(storage, entity("person", "Anna"))
    _write(storage, entity("person", "Anna H", subject=anna))
    second_done = threading.Event()
    first = _Holding(db, lambda: second_done.is_set() or _waiting_on_a_lock(db))
    errors: list[BaseException] = []
    outcomes: dict[str, Outcome] = {}
    seen: dict[str, bool] = {}

    def run_first() -> None:
        try:
            outcomes["first"] = catch_up(first, first, GRAPH, batch_size=2)
            seen["first"] = _rows(storage) == _folded(storage)
        except BaseException as error:
            errors.append(error)

    def run_second() -> None:
        try:
            assert first.holding.wait(timeout=10)
            outcomes["second"] = catch_up(storage, storage, GRAPH, batch_size=2)
            seen["second"] = _rows(storage) == _folded(storage)
        except BaseException as error:
            errors.append(error)
        finally:
            second_done.set()

    threads = [threading.Thread(target=run_first), threading.Thread(target=run_second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive(), "a catch-up is hanging"

    assert errors == []
    assert seen == {"first": True, "second": True}
    assert outcomes["first"].events + outcomes["second"].events == 6
    assert outcomes["first"].events >= 2
    assert outcomes["second"].events >= 2
    assert _rows(storage) == _folded(storage)
    incremental = _snapshot(db)
    assert _rebuilt(storage, db) == incremental


# --- Random histories (Review Focus 2) --------------------------------------------


@dataclass(frozen=True)
class _Entity:
    """A new person or project, or with `on` a new version of an entity
    picked by position; by the operator, or by the model at a confidence
    that a class does or does not cover. A model's version of an entity the
    operator stands for becomes an objection on the write path."""

    kind: str
    by_model: bool
    confidence: int
    on: int | None


@dataclass(frozen=True)
class _Relation:
    """A new relation, or with `on` a new version of one: an assignment of a
    mail or of some of its units to any entity, a person involved in a
    project, or a project part of another; with `ask`, a model's question
    between two entities."""

    kind: str
    by_model: bool
    confidence: int
    start: int
    to: int
    units: tuple[int, ...] | None
    ask: bool
    on: int | None


@dataclass(frozen=True)
class _Approve:
    """The operator approves a version picked by position, answering a
    question with its candidate `answer`."""

    pick: int
    answer: int


@dataclass(frozen=True)
class _Reject:
    pick: int


@dataclass(frozen=True)
class _EraseVersion:
    pick: int


@dataclass(frozen=True)
class _EraseMail:
    """An erasure of a mail other than the first, whole or one of its units:
    the cascade takes the claims that rest on what it erases. Mail 1 stays,
    so that the persons and projects a history opens with stand to the end,
    and later steps rest on the mails that stand."""

    mail: int
    units: tuple[int, ...] | None


@dataclass(frozen=True)
class _Class:
    """A class event for one of the two names: set again, or revoked with
    or without `demote`."""

    which: int
    revoked: bool
    demote: bool


@dataclass(frozen=True)
class _EraseClass:
    pick: int


@dataclass(frozen=True)
class _CatchUp:
    batch_size: int


_picks = st.integers(min_value=0, max_value=30)
_confidences = st.sampled_from([10, 90, 90])
_by_model = st.sampled_from([True, True, False])
_entities = st.builds(
    _Entity,
    st.sampled_from(["person", "project"]),
    _by_model,
    _confidences,
    st.one_of(st.none(), st.none(), _picks),
)
_relations = st.builds(
    _Relation,
    st.sampled_from(["concerns", "concerns", "involved_in", "part_of"]),
    _by_model,
    _confidences,
    _picks,
    _picks,
    st.one_of(st.none(), st.sampled_from([(1,), (2,), (1, 2)])),
    st.booleans(),
    st.one_of(st.none(), _picks),
)
_catch_ups = st.builds(_CatchUp, st.sampled_from([1, 2, 5, 500]))
# Writing is drawn more often than the rest, so that a history has threads
# for its answers, erasures and class events to change.
_steps = st.lists(
    st.one_of(
        _entities,
        _entities,
        _relations,
        _relations,
        _relations,
        st.builds(_Approve, _picks, _picks),
        st.builds(_Reject, _picks),
        st.builds(_EraseVersion, _picks),
        st.builds(
            _EraseMail,
            st.integers(min_value=2, max_value=HISTORY_MAILS),
            st.one_of(st.none(), st.sampled_from([(1,), (2,)])),
        ),
        st.builds(_Class, st.integers(min_value=0, max_value=1), st.booleans(), st.booleans()),
        st.builds(_EraseClass, _picks),
        _catch_ups,
        _catch_ups,
    ),
    min_size=8,
    max_size=30,
)

type _Step = (
    _Entity
    | _Relation
    | _Approve
    | _Reject
    | _EraseVersion
    | _EraseMail
    | _Class
    | _EraseClass
    | _CatchUp
)
_REFUSED = (GraphRefused, AssertionRefused, ClassRefused, RedactionRefused)


@dataclass
class _History:
    """What a history has written so far, for the steps to pick from."""

    storage: PostgresStorage
    people: list[int]
    projects: list[int]
    relations: list[int]
    versions: list[int]
    proposals: list[int]
    classes: list[int]
    mails: list[int]
    moment: datetime = T0

    def mail(self, pick: int) -> int:
        """A mail no erasure has touched yet, picked by position."""
        return self.mails[pick % len(self.mails)]

    def at(self) -> datetime:
        self.moment += timedelta(seconds=1)
        return self.moment

    def write(self, claim: Claim) -> tuple[int, ...]:
        try:
            ids = _write(self.storage, claim, at=self.at())
        except GraphRefused:
            return ()
        self.versions.extend(ids)
        if claim.author != OPERATOR:
            self.proposals.extend(ids)
        return ids

    def claim_of(self, version_id: int) -> tuple[int, Claim] | None:
        """The thread and the claim of a version that stands in the fold."""
        with self.storage.begin() as conn:
            graph = read_graph(self.storage, conn)
        for thread in graph.threads.values():
            for version in thread.versions:
                if version.id == version_id:
                    return thread.subject, version.claim
        return None


def _answers(graph: Graph, subjects: Sequence[int]) -> tuple[object, ...]:
    """What the readers ask of a graph, each question for every thread
    where it takes one."""
    return (
        graph.winners(ENTITY),
        graph.winners(RELATION),
        graph.entity_kinds(),
        dict(graph.relations()),
        {subject: dict(graph.relations(touching=subject)) for subject in subjects},
        dict(graph.waiting()),
        dict(graph.objected()),
        dict(graph.under(graph.classes)),
        {subject: graph.threads.get(subject) for subject in subjects},
    )


def _readers_agree(storage: PostgresStorage) -> None:
    """The graph a reader reads from the projection answers as the fold of
    the whole log does, and the members of every entity read off the rows
    are those of the fold's edges ({ref}`graph-projection`)."""
    with storage.snapshot() as conn:
        folded = read_graph(storage, conn)
        projected = projected_graph(storage, storage, conn)
        subjects = sorted(folded.threads)
        assert _answers(projected, subjects) == _answers(folded, subjects)
        vocabulary = read_vocabulary(storage, conn)
        edges, kinds = bracket_edges(folded, vocabulary), bracket_kinds(vocabulary)
        for subject in folded.winners(ENTITY):
            expected = members(edges, subject, kinds)
            assert read_brackets(storage, storage, conn, subject) == expected


def _pick(items: list[int], pick: int) -> int | None:
    return items[pick % len(items)] if items else None


def _entity_step(history: _History, step: _Entity) -> None:
    author, level = (MODEL, OPEN) if step.by_model else (OPERATOR, DIRECT)
    confidence = step.confidence if step.by_model else None
    threads = history.people if step.kind == "person" else history.projects
    subject = None if step.on is None else _pick(threads, step.on)
    if step.on is not None and subject is None:
        return
    claim = entity(
        step.kind,
        f"{step.kind} {len(history.versions)}",
        author=author,
        responsibility=level,
        source=Source(history.mail(len(history.versions)), None),
        subject=subject,
        confidence=confidence,
    )
    ids = history.write(claim)
    if subject is None:
        threads.extend(ids)


def _relation_step(history: _History, step: _Relation) -> None:
    author, level = (MODEL, OPEN) if step.by_model or step.ask else (OPERATOR, DIRECT)
    confidence = step.confidence if author == MODEL else None
    ends = {
        "concerns": (None, history.people + history.projects),
        "involved_in": (history.people, history.projects),
        "part_of": (history.projects, history.projects),
    }
    starts, tos = ends[step.kind]
    start: int | Source | None = (
        Source(history.mail(step.start), step.units)
        if starts is None
        else _pick(starts, step.start)
    )
    to = _pick(tos, step.to)
    other = _pick(tos, step.to + 1)
    subject = None if step.on is None else _pick(history.relations, step.on)
    if start is None or to is None or other is None or (step.on is not None and subject is None):
        return
    if step.ask and to == other:
        return
    claim = relation(
        step.kind,
        start,
        None if step.ask else to,
        author=author,
        responsibility=level,
        source=Source(history.mail(len(history.versions)), step.units),
        subject=subject,
        confidence=confidence,
        candidates=(to, other) if step.ask else None,
    )
    ids = history.write(claim)
    if subject is None:
        history.relations.extend(ids)


def _approve(history: _History, step: _Approve) -> None:
    version_id = _pick(history.proposals, step.pick)
    found = None if version_id is None else history.claim_of(version_id)
    if found is None:
        return
    subject, claim = found
    body = claim.body
    if isinstance(body, RelationBody) and body.candidates is not None:
        answer = body.candidates[step.answer % len(body.candidates)]
        body = replace(body, to=answer, candidates=None)
    approval = replace(
        claim,
        responsibility=DIRECT,
        subject=subject,
        approves=version_id,
        under=None,
        contests=None,
        body=body,
    )
    history.write(approval)


def _erase(history: _History, step: _EraseVersion | _EraseMail | _EraseClass) -> None:
    storage, at = history.storage, history.at()
    match step:
        case _EraseVersion(pick=pick):
            target = _pick(history.versions, pick)
        case _EraseClass(pick=pick):
            target = _pick(history.classes, pick)
        case _EraseMail(mail=mail, units=units):
            target = mail
            if mail in history.mails:
                history.mails.remove(mail)
            if units is not None:
                redact_units(storage, storage, mail, units, reason="a third party", recorded_at=at)
                return
    if target is not None:
        redact_event(storage, storage, target, reason="wrong", recorded_at=at)


def _run(history: _History, step: _Step) -> None:
    storage = history.storage
    match step:
        case _Entity():
            _entity_step(history, step)
        case _Relation():
            _relation_step(history, step)
        case _Approve():
            _approve(history, step)
        case _Reject(pick=pick):
            of = _pick(history.proposals, pick)
            found = None if of is None else history.claim_of(of)
            if of is not None and found is not None:
                # Among the versions, so that an erasure can pick it: then
                # the proposal it rejected waits again.
                history.versions.append(
                    _reject(storage, of, sources=found[1].sources, at=history.at())
                )
        case _EraseVersion() | _EraseMail() | _EraseClass():
            _erase(history, step)
        case _Class(which=which, revoked=revoked, demote=demote):
            item = replace(CLASSES[which], revoked=revoked, demote=revoked and demote)
            history.classes.append(
                set_class(storage, item, statement="changed", recorded_at=history.at())
            )
        case _CatchUp(batch_size=batch_size):
            _project(storage, batch_size=batch_size)
            assert _rows(storage) == _folded(storage)
            _readers_agree(storage)
            with storage.snapshot() as conn:
                state = storage.projection_state(conn, GRAPH.name)
                assert state is not None
                assert check_graph(storage, storage, conn, state.up_to_id) == []


@pytest.mark.db
@settings(
    max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(steps=_steps)
def test_property_the_projection_stands_where_the_fold_does(
    db: Engine, truncate_statement: str, steps: list[_Step]
) -> None:
    """Review Focus 2 of the 2026-10-15 assignments plan: after every
    catch-up, at random points of a random history and in batches of random
    size, every row of `p_graph_thread` is what `fold_graph` over the whole
    log makes of its thread under the classes in force, and a thread without
    a winner has no row; at the end, a rebuild writes both tables as the
    incremental path left them. After every catch-up, too, the graph a
    reader reads from the projection answers every question as the fold
    does, the members of every entity are those of the fold's edges, and
    `check_graph` finds no difference in either table.

    A step the write path or an erasure refuses writes nothing, and the
    history goes on: what the projection meets is only ever what the log
    can hold. Measured red on 2026-10-15, each mutation against this test
    alone, with the redactions of a batch marking nothing, with a class
    event marking nothing, with a rejection marking nothing, with an erased
    action marking nothing, with the refold leaving out the subject itself,
    and with `_stale` returning nothing. With the refold leaving out the
    erased rows a version names it stayed green, for `approves` and for
    `contests` alike: those histories need an erasure the projection reads
    before a later batch on the same thread, and
    `test_an_approval_of_a_proposal_erased_unread_stands_as_the_fold_has_it`
    and `test_an_objection_against_an_erased_direct_version_still_waits` are
    the tests that go red for them. With an erased rejection touching only
    itself it went red, since rejections are among the versions a history
    erases.
    """
    with db.begin() as c:
        c.execute(text(truncate_statement))
    storage = _setup(db, HISTORY_MAILS)
    with storage.begin() as conn:
        classes = sorted(read_classes(storage, conn).states)
    # Two persons and two projects the operator stands for, so that every
    # history has ends to relate and versions to object to, and a person and
    # an assignment the model wrote under the two classes, folded once
    # before the history starts, so that a class event has something to
    # change that the projection already holds.
    anna, bert, xz, yz = _write(
        storage,
        entity("person", "Anna"),
        entity("person", "Bert"),
        entity("project", "XZ"),
        entity("project", "YZ"),
    )
    guessed, assigned = _write(
        storage,
        entity("person", "Clara", author=MODEL, responsibility=OPEN, confidence=90),
        relation("concerns", Source(1, (1,)), xz, author=MODEL, responsibility=OPEN, confidence=90),
    )
    _project(storage)
    history = _History(
        storage,
        [anna, bert, guessed],
        [xz, yz],
        [assigned],
        [anna, bert, xz, yz, guessed, assigned],
        [guessed, assigned],
        classes,
        list(range(1, HISTORY_MAILS + 1)),
    )
    for step in steps:
        with contextlib.suppress(*_REFUSED):
            _run(history, step)
    _project(storage, batch_size=3)
    assert _rows(storage) == _folded(storage)
    incremental = _snapshot(db)
    assert _rebuilt(storage, db) == incremental
