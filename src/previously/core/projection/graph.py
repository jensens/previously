# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The graph: what each entity and relation stands at, without folding the
whole log for it ({ref}`graph-projection`).

Two tables. `p_graph_version` says which versions and rejections belong to
which thread, and `p_graph_thread` holds, per thread with a winner, what the
fold makes of them: the winner, its level and state, its ends, and the counts
of pending versions and objections. Neither holds content. A reader that
shows a version reads it from the log by id, so an erasure holds there
without this projection having content of its own to delete.

A batch marks the threads it touches, and only those are folded again, from
their rows in the log and under the approval classes as of the batch's last
event. A thread is touched by a version of it, by a rejection of one of its
versions, by an erasure of one of its rows or of its subject, and by an
approval class event of a name one of its versions stands under, or the
erasure of any class event. Nothing else that the write path and an erasure
write changes what the fold makes of a thread, so the projection stands where
`fold_graph` over the whole log does, which `tests/test_projection_graph.py`
holds for random histories. What lies outside — a version written around the
write path that names a version of another thread, a payload set to `NULL`
by hand — the page names.

Marking too much is never wrong, only slower: the fold of a thread is the
same however often it runs. Marking too little leaves a thread where it
stood, and nothing would say so — the failure the equivalence test exists
for.
"""

from dataclasses import dataclass
from dataclasses import field
from previously.contract.rows import GraphThreadRow
from previously.contract.rows import GraphVersionRow
from previously.core.action import APPROVAL_CLASS
from previously.core.assertion import parse_statement
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.classes import ClassFold
from previously.core.graph import fold_graph
from previously.core.graph import Graph
from previously.core.graph import GRAPH_KINDS
from previously.core.graph import level_of
from previously.core.graph import parse_claim
from previously.core.graph import RelationBody
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.rows import EventRow
    from previously.contract.store import LogReader
    from previously.contract.store import ProjectionStore
    from previously.core.graph import ClassState
    from previously.core.graph import GraphThread
    from previously.core.projection.worker import Batch


REJECTION_ROW: Final = "rejection"

_ASSERTION: Final = "assertion"
_ACTION: Final = "action"


def summary(thread: GraphThread, classes: Mapping[int, ClassState]) -> GraphThreadRow | None:
    """What a thread stands at under `classes`, or `None` when no version of
    it wins: every one erased, rejected or answered."""
    winner = thread.winner(classes)
    if winner is None:
        return None
    body = winner.claim.body
    start_entity = start_event = to_entity = None
    start_units = candidates = None
    period_start = period_end = None
    if isinstance(body, RelationBody):
        if isinstance(body.start, Source):
            start_event, start_units = body.start.event, body.start.units
        else:
            start_entity = body.start
        to_entity, candidates = body.to, body.candidates
        if body.period is not None:
            period_start, period_end = body.period.start, body.period.end
    return GraphThreadRow(
        subject=thread.subject,
        kind=thread.kind,
        type=body.type,
        winner_id=winner.id,
        level=level_of(winner, classes),
        state=body.state,
        start_entity=start_entity,
        start_event=start_event,
        start_units=start_units,
        to_entity=to_entity,
        candidates=candidates,
        period_start=period_start,
        period_end=period_end,
        pending=len(thread.pending(classes)),
        objections=len(thread.objections(classes)),
        question=thread.question(classes) is not None,
    )


def version_row(event: EventRow) -> GraphVersionRow | None:
    """The row of a version of an entity or a relation, or `None` for an
    event that is none, as `GraphFold.add` reads it: an erased one, one of
    another kind, and one with a form fault."""
    payload = event.payload
    if event.kind != _ASSERTION or payload is None or payload.get("assertion") not in GRAPH_KINDS:
        return None
    claim = parse_claim(payload)
    if claim is None:
        return None
    subject = event.id if claim.subject is None else claim.subject
    return GraphVersionRow(event.id, subject, claim.kind, claim.under)


def rejected(event: EventRow) -> int | None:
    """The version a rejection names, when it names one before itself, or
    `None`. A rejection of a later event can reject nothing: the fold reads
    in chain order and has not met that version yet."""
    payload = event.payload
    if event.kind != _ASSERTION or payload is None or payload.get("assertion") != REJECTION:
        return None
    statement = parse_statement(payload)
    if statement is None or statement.of is None or statement.of >= event.id:
        return None
    return statement.of


def rebuilt_versions(events: Iterable[EventRow]) -> list[GraphVersionRow]:
    """The rows of `p_graph_version` a rebuild writes from `events`, read in
    chain order as they stand now: every version, and every rejection whose
    `of` names a version before it, under that version's subject. An erased
    row writes none, and so neither does a rejection of an erased version;
    that is what the catch-up leaves behind too, since it takes out the rows
    a rebuild would not write. `previously project --check` holds the table
    against this."""
    known: dict[int, GraphVersionRow] = {}
    found: list[GraphVersionRow] = []
    for event in events:
        if (row := version_row(event)) is not None:
            known[row.id] = row
            found.append(row)
        elif (of := rejected(event)) is not None and of in known:
            found.append(GraphVersionRow(event.id, known[of].subject, REJECTION_ROW, None))
    return found


def _erased_target(event: EventRow) -> int | None:
    """The event a redaction of a whole event names. A redaction of units
    or of a blob changes no assertion: an assertion has neither, and the
    cascade erases the assertions that rest on them with redactions of
    their own."""
    if event.kind != _ACTION or event.payload is None:
        return None
    try:
        redaction = parse(event.id, event.payload)
    except MalformedAction:
        return None
    return redaction.event if redaction.scope == "event" else None


@dataclass
class Marks:
    """What a batch holds that the graph has to follow, in chain order."""

    versions: list[GraphVersionRow] = field(default_factory=lambda: [])
    rejections: list[tuple[int, int]] = field(default_factory=lambda: [])  # (id, of)
    erased: list[int] = field(default_factory=lambda: [])
    classes: list[int] = field(default_factory=lambda: [])


def marks(batch: Batch) -> Marks:
    """The versions, rejections, erasures and class events of a batch. A
    vocabulary event is none of them: the fold does not read the
    vocabulary, and what fits it is for the reader to decide."""
    found = Marks()
    for event in batch.events:
        if (row := version_row(event)) is not None:
            found.versions.append(row)
        elif (of := rejected(event)) is not None:
            found.rejections.append((event.id, of))
        elif (target := _erased_target(event)) is not None:
            found.erased.append(target)
        elif (
            event.kind == _ACTION
            and event.payload is not None
            and event.payload.get("action") == APPROVAL_CLASS
        ):
            found.classes.append(event.id)
    return found


def class_states[Conn](log: LogReader[Conn], conn: Conn, up_to: int) -> Mapping[int, ClassState]:
    """The class states as of event `up_to`, as `read_classes` reads them
    for the whole log: a batch is folded at its own end, and a class event
    a later batch holds marks the threads it changes when that batch comes.
    `previously project --check` folds the log at the projection's
    `up_to_id` under them."""
    folded = ClassFold()
    for row in log.actions(conn, APPROVAL_CLASS):
        if row.id <= up_to:
            folded.add(row.id, row.payload)
    return folded.classes().states


def _same_name(states: Mapping[int, ClassState], event_ids: Iterable[int]) -> set[int]:
    """Every class event of the names `event_ids` set. All of a name's
    events share the state of its newest one, so a new event of a name
    changes the level of what stands under any of them."""
    newest = {states[event_id].id for event_id in event_ids if event_id in states}
    return {event_id for event_id, state in states.items() if state.id in newest}


def _named(payload: Mapping[str, object]) -> set[int]:
    """The ids a version names besides its subject: an erased one counts for
    an approval or an objection that names it (`GraphFold.add`)."""
    return {
        value
        for key in ("approves", "contests")
        if isinstance(value := payload.get(key), int) and not isinstance(value, bool)
    }


def _rows[Conn](
    log: LogReader[Conn], conn: Conn, known: Mapping[int, EventRow], wanted: Iterable[int]
) -> dict[int, EventRow]:
    """The rows of `wanted`, out of `known` where it holds them and in one
    query for the rest, none when `known` holds them all."""
    ids = set(wanted)
    found = {event_id: known[event_id] for event_id in ids if event_id in known}
    missing = sorted(ids - found.keys())
    return found | log.events_by_id(conn, missing)


def _known(batch: Batch) -> dict[int, EventRow]:
    return {event.id: event for event in batch.events}


def _folded[Conn](
    log: LogReader[Conn],
    conn: Conn,
    subjects: Sequence[int],
    ids: Mapping[int, Sequence[int]],
    classes: Mapping[int, ClassState],
    known: Mapping[int, EventRow],
) -> tuple[Graph, dict[int, EventRow]]:
    """`fold_threads`, and the rows it read."""
    rows = _rows(log, conn, known, [*subjects, *(i for found in ids.values() for i in found)])
    named = {
        other for row in rows.values() if row.payload is not None for other in _named(row.payload)
    }
    # Outside its thread, the fold reads a row only for whether it is
    # erased; the rest of what a version names is in its own thread.
    rows |= {
        event_id: row
        for event_id, row in _rows(log, conn, known, named - rows.keys()).items()
        if row.payload is None
    }
    graph = fold_graph(
        (
            (row.id, row.recorded_at, row.payload)
            for row in sorted(rows.values(), key=lambda row: row.id)
            if row.kind == _ASSERTION
        ),
        classes,
    )
    return graph, rows


def fold_threads[Conn](
    log: LogReader[Conn],
    conn: Conn,
    subjects: Sequence[int],
    ids: Mapping[int, Sequence[int]],
    classes: Mapping[int, ClassState],
) -> Graph:
    """The threads of `subjects` folded again from what the log holds now,
    under `classes`: from the rows `ids` names for each, which
    `p_graph_version` holds, the subject itself, and the rows their
    versions approve or contest where those are erased. A thread is the
    same as in `fold_graph` over the whole log, since nothing outside these
    rows changes what the fold makes of it; the catch-up folds a touched
    thread this way, and a reader each thread it shows. The graph holds the
    threads of `subjects` that have a version, and none other."""
    graph, _rows_read = _folded(log, conn, subjects, ids, classes, {})
    return Graph({s: graph.threads[s] for s in subjects if s in graph.threads}, classes)


def _stale(ids: Sequence[int], rows: Mapping[int, EventRow]) -> list[int]:
    """The rows of one thread a rebuild would not write: an erased version
    or rejection, and a rejection whose version is erased. What stands in
    `p_graph_version` is then what reading the log now gives, whichever
    order the catch-ups took."""
    standing: set[int] = set()
    rejections: list[tuple[int, int | None]] = []
    stale: list[int] = []
    for event_id in ids:
        row = rows.get(event_id)
        if row is None or row.payload is None:
            stale.append(event_id)
        elif row.payload.get("assertion") == REJECTION:
            rejections.append((event_id, rejected(row)))
        else:
            standing.add(event_id)
    stale.extend(event_id for event_id, of in rejections if of not in standing)
    return sorted(stale)


@dataclass(frozen=True)
class GraphProjection:
    """Name and version as `projection_state` knows them, and the write step."""

    name: str = "graph"
    version: int = 1

    def write[Conn](
        self, store: ProjectionStore[Conn], log: LogReader[Conn], conn: Conn, batch: Batch
    ) -> None:
        found = marks(batch)
        known = {row.id: row for row in found.versions}
        looked_up = [of for _id, of in found.rejections if of not in known]
        looked_up += [target for target in found.erased if target not in known]
        known |= store.graph_versions(conn, sorted(set(looked_up)))

        rows = list(found.versions)
        touched = {row.subject for row in found.versions}
        for rejection_id, of in found.rejections:
            target = known.get(of)
            if target is not None and target.kind != REJECTION_ROW:
                rows.append(GraphVersionRow(rejection_id, target.subject, REJECTION_ROW, None))
                touched.add(target.subject)
        store.insert_graph_versions(conn, rows)

        # An erased row stands in the fold of its thread as erased, and an
        # erased subject lets later versions of it stand (`GraphFold.add`),
        # so the target is touched as a subject too.
        unknown = [target for target in found.erased if target not in known]
        touched.update(found.erased)
        touched.update(known[target].subject for target in found.erased if target in known)
        if not (touched or found.classes):
            return

        classes = class_states(log, conn, batch.events[-1].id)
        under = _same_name(classes, found.classes)
        if any(row.kind == _ACTION for row in _rows(log, conn, _known(batch), unknown).values()):
            # An erased action may have been a class event, and its name is
            # gone with its payload: every thread under any class is folded
            # again. An erasure of an action is rare, and refolding is safe.
            under |= set(classes) | set(unknown)
        touched |= store.class_subjects(conn, sorted(under))
        self._refold(store, log, conn, batch, sorted(touched), classes)

    def _refold[Conn](
        self,
        store: ProjectionStore[Conn],
        log: LogReader[Conn],
        conn: Conn,
        batch: Batch,
        subjects: Sequence[int],
        classes: Mapping[int, ClassState],
    ) -> None:
        """Folds the threads of `subjects` again from what the log holds now,
        and writes what each stands at, or takes its row where none wins."""
        ids = store.graph_version_ids(conn, subjects)
        graph, rows = _folded(log, conn, subjects, ids, classes, _known(batch))
        standing: list[GraphThreadRow] = []
        gone: list[int] = []
        for subject in subjects:
            thread = graph.threads.get(subject)
            folded = None if thread is None else summary(thread, classes)
            if folded is None:
                gone.append(subject)
            else:
                standing.append(folded)
        store.upsert_graph_threads(conn, standing)
        store.delete_graph_threads(conn, gone)
        store.delete_graph_versions(
            conn, [stale for found in ids.values() for stale in _stale(found, rows)]
        )


GRAPH = GraphProjection()
