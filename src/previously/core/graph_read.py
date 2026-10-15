# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading the graph from its projection ({ref}`graph-projection`).

A reader catches the projection up first, with `catch_up(log, store,
GRAPH)` in transactions of its own, and then reads in a snapshot of its own:
`projected_graph` gives a `Graph` there that answers the questions of a
reader — which entities, which relations, what waits, what is objected to —
from the tables of the projection, and folds from the log only the threads
the answer names. What a reader shows of a thread, its names, fields and
versions, comes from the log, by id; the projection holds no content and
only says which threads to fold.

A thread folded this way is the one `fold_graph` over the whole log gives,
since nothing outside its own rows changes what the fold makes of it, so a
reader shows what it showed when it folded the log, and runs the same code
on what it shows. Where the projection itself drifted from the log, which
the page names, `previously project --check` reports the threads.

`--as-of` and the write path still fold the log: the projection knows only
what stands now, and the write path checks under the tip it locks.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import fields
from datetime import date
from previously.core.assertion import Source
from previously.core.classes import read_classes
from previously.core.graph import ENTITY
from previously.core.graph import fold_graph
from previously.core.graph import Graph
from previously.core.graph import GraphThread
from previously.core.graph import RELATION
from previously.core.graph_write import relation_ends
from previously.core.members import bracket_edges
from previously.core.members import bracket_kinds
from previously.core.members import BracketEdge
from previously.core.members import members
from previously.core.projection.graph import class_states
from previously.core.projection.graph import fold_threads
from previously.core.projection.graph import rebuilt_versions
from previously.core.projection.graph import summary
from previously.core.vocabulary import read_vocabulary
from typing import cast
from typing import Final
from typing import override
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Sequence
    from previously.contract.rows import GraphThreadRow
    from previously.contract.rows import GraphVersionRow
    from previously.contract.store import GraphStore
    from previously.contract.store import LogStore
    from previously.core.graph import GraphVersion
    from previously.core.members import Members
    from previously.core.projection.worker import Outcome


_ASSERTION: Final = "assertion"


class ThreadsFromLog(Mapping[int, GraphThread]):
    """The threads of a graph, each folded from the log the first time it is
    asked for, and kept for the rest of the read.

    Asked for one id, it folds that thread; `load` folds many in one go, for
    a reader that knows what it is going to show. Walking every thread folds
    every thread there is, which is correct and as slow as folding the log:
    the readers of the projection ask `ProjectedGraph` for what they show
    instead.
    """

    def __init__(
        self,
        fold: Callable[[Sequence[int]], Mapping[int, GraphThread]],
        subjects: Callable[[], Iterable[int]],
    ) -> None:
        self._fold = fold
        self._subjects = subjects
        self._found: dict[int, GraphThread | None] = {}

    def load(self, subjects: Iterable[int]) -> None:
        """Folds the threads of `subjects` not folded yet, together."""
        missing = sorted({subject for subject in subjects if subject not in self._found})
        if not missing:
            return
        folded = self._fold(missing)
        for subject in missing:
            self._found[subject] = folded.get(subject)

    @override
    def __getitem__(self, key: int) -> GraphThread:
        self.load((key,))
        found = self._found[key]
        if found is None:
            raise KeyError(key)
        return found

    @override
    def __iter__(self) -> Iterator[int]:
        subjects = sorted(set(self._subjects()))
        self.load(subjects)
        return iter([subject for subject in subjects if self._found[subject] is not None])

    @override
    def __len__(self) -> int:
        return sum(1 for _subject in self)


class GraphIndex[Conn]:
    """The store of the projection and the snapshot a `ProjectedGraph` asks
    it in. A class of its own and no field of the graph, since the fields of
    a dataclass are read at runtime and the store protocols are imported
    for the type checker alone."""

    def __init__(self, store: GraphStore[Conn], conn: Conn) -> None:
        self.store = store
        self.conn = conn


@dataclass(frozen=True)
class ProjectedGraph[Conn](Graph):
    """A graph whose questions the projection answers, in the snapshot of
    `index`.

    Each question asks the projection which threads it concerns, folds
    those from the log, and asks the same question of a `Graph` of them:
    the answer is the one the whole fold gives, by the same code. With them
    come the threads their relations name as ends, folded in the same go,
    since a reader names every end it shows. `entity_kinds` alone is read
    off the rows, which hold the kind of each winner.
    """

    index: GraphIndex[Conn]

    def _found(self) -> ThreadsFromLog:
        return cast("ThreadsFromLog", self.threads)

    def _graph_of(self, subjects: Iterable[int]) -> Graph:
        """The threads of `subjects` as a graph of their own, with the ends
        of their relations folded alongside."""
        wanted = sorted(set(subjects))
        found = self._found()
        found.load(wanted)
        threads = {subject: found[subject] for subject in wanted if subject in found}
        found.load(
            end
            for thread in threads.values()
            if thread.kind == RELATION
            for end in relation_ends(thread)
        )
        return Graph(threads, self.classes)

    @override
    def winners(
        self, kind: str, *, types: Collection[str] | None = None
    ) -> dict[int, GraphVersion]:
        rows = self.index.store.read_graph_threads(
            self.index.conn, kind=kind, types=None if types is None else sorted(types)
        )
        return self._graph_of(row.subject for row in rows).winners(kind, types=types)

    @override
    def entity_kinds(self) -> dict[int, str]:
        rows = self.index.store.read_graph_threads(self.index.conn, kind=ENTITY)
        return {row.subject: row.type for row in rows}

    @override
    def relations(
        self,
        *,
        at: date | None = None,
        types: Collection[str] | None = None,
        start: int | None = None,
        to: int | None = None,
        touching: int | None = None,
    ) -> Mapping[int, GraphVersion]:
        rows = self.index.store.graph_relations(
            self.index.conn,
            at=at,
            types=None if types is None else sorted(types),
            start=start,
            to=to,
            touching=touching,
        )
        return self._graph_of(row.subject for row in rows).relations(
            at=at, types=types, start=start, to=to, touching=touching
        )

    @override
    def waiting(self) -> Mapping[int, GraphThread]:
        rows = self.index.store.graph_waiting(self.index.conn)
        return self._graph_of(row.subject for row in rows).waiting()

    @override
    def objected(self) -> Mapping[int, GraphThread]:
        rows = self.index.store.graph_objected(self.index.conn)
        return self._graph_of(row.subject for row in rows).objected()

    @override
    def under(self, class_ids: Collection[int]) -> Mapping[int, GraphThread]:
        subjects = self.index.store.class_subjects(self.index.conn, sorted(class_ids))
        return self._graph_of(subjects).under(class_ids)


def projected_graph[Conn](
    log: LogStore[Conn], store: GraphStore[Conn], conn: Conn
) -> ProjectedGraph[Conn]:
    """The graph of a reader, read from the projection in the snapshot
    `conn` belongs to, under the approval classes in force. The caller has
    caught the projection up before it opened the snapshot."""
    classes = read_classes(log, conn).states

    def fold(subjects: Sequence[int]) -> Mapping[int, GraphThread]:
        ids = store.graph_version_ids(conn, subjects)
        return fold_threads(log, conn, subjects, ids, classes).threads

    threads = ThreadsFromLog(fold, lambda: store.graph_subjects(conn))
    return ProjectedGraph(threads, classes, GraphIndex(store, conn))


def read_brackets[Conn](
    log: LogStore[Conn], store: GraphStore[Conn], conn: Conn, bracket: int
) -> Members:
    """`members` of `bracket`, over the edges the projection holds: the
    relations of the kinds `bracket_kinds` names under the vocabulary in
    force, as `bracket_edges` takes them from a fold. A row holds the ends
    and the level of its winner, which is all an edge is, so nothing is
    read from the log but the vocabulary. The caller has caught the
    projection up before it opened the snapshot."""
    kinds = bracket_kinds(read_vocabulary(log, conn))
    rows = store.graph_relations(conn, types=sorted(kinds.hierarchy | kinds.assignments))
    edges = [
        BracketEdge(
            row.subject,
            row.type,
            (
                cast("int", row.start_entity)
                if row.start_event is None
                else Source(row.start_event, row.start_units)
            ),
            cast("int", row.to_entity),
            row.level,
        )
        for row in rows
    ]
    return members(edges, bracket, kinds)


def bracket_members[Conn](log: LogStore[Conn], conn: Conn, graph: Graph, bracket: int) -> Members:
    """`members` of `bracket` in the graph a reader reads in the snapshot of
    `conn`: over the rows of the projection where `graph` is read from it
    (`read_brackets`), and over the edges of the fold where the reader
    folded the log instead, because the projection didn't stand where its
    catch-up left it. A reader finds the members in the graph it shows."""
    if isinstance(graph, ProjectedGraph):
        projected = cast("ProjectedGraph[Conn]", graph)
        return read_brackets(log, projected.index.store, conn, bracket)
    vocabulary = read_vocabulary(log, conn)
    return members(bracket_edges(graph, vocabulary), bracket, bracket_kinds(vocabulary))


def _cell(value: object) -> str:
    """A value of a row as a line of `previously project --check` shows it."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return ",".join(str(item) for item in cast("tuple[object, ...]", value))
    return str(value)


def differences(rows: Iterable[GraphThreadRow], graph: Graph) -> list[tuple[int, str]]:
    """Every subject on which the rows of `p_graph_thread` and `graph`
    disagree, by subject, with what differs: each column as `name projected
    instead of folded`, or a row where the fold has no winner, or none where
    it has one."""
    projected = {row.subject: row for row in rows}
    folded = {
        subject: row
        for subject, thread in graph.threads.items()
        if (row := summary(thread, graph.classes)) is not None
    }
    found: list[tuple[int, str]] = []
    for subject in sorted(projected.keys() | folded.keys()):
        here, there = projected.get(subject), folded.get(subject)
        if here == there:
            continue
        if here is None:
            what = f"no row instead of winner {cast('GraphThreadRow', there).winner_id}"
        elif there is None:
            what = f"winner {here.winner_id} instead of no row"
        else:
            what = ", ".join(
                f"{column.name} {_cell(getattr(here, column.name))} instead of "
                f"{_cell(getattr(there, column.name))}"
                for column in fields(here)
                if getattr(here, column.name) != getattr(there, column.name)
            )
        found.append((subject, what))
    return found


def _version_text(row: GraphVersionRow) -> str:
    under = "" if row.under is None else f" under {row.under}"
    return f"{row.kind} of {row.subject}{under}"


def version_differences(
    rows: Iterable[GraphVersionRow], rebuilt: Iterable[GraphVersionRow]
) -> list[tuple[int, str]]:
    """Every id on which the rows of `p_graph_version` and those a rebuild
    writes disagree, by id: each column as `version row name projected
    instead of rebuilt`, a row the rebuild doesn't write, or none where it
    writes one."""
    projected = {row.id: row for row in rows}
    expected = {row.id: row for row in rebuilt}
    found: list[tuple[int, str]] = []
    for event_id in sorted(projected.keys() | expected.keys()):
        here, there = projected.get(event_id), expected.get(event_id)
        if here == there:
            continue
        if here is None:
            what = f"no version row instead of {_version_text(cast('GraphVersionRow', there))}"
        elif there is None:
            what = f"version row {_version_text(here)} instead of none"
        else:
            what = "version row " + ", ".join(
                f"{column.name} {_cell(getattr(here, column.name))} instead of "
                f"{_cell(getattr(there, column.name))}"
                for column in fields(here)
                if getattr(here, column.name) != getattr(there, column.name)
            )
        found.append((event_id, what))
    return found


def check_graph[Conn](
    log: LogStore[Conn], store: GraphStore[Conn], conn: Conn, up_to: int
) -> list[tuple[int, str]]:
    """What differs between the projection and the log up to event `up_to`,
    the projection's `up_to_id`: `differences` of the threads against the
    fold under the classes as of that event, then `version_differences` of
    the version rows against what a rebuild would write. The readers fold
    the threads they show from the version rows, so a wrong one there is as
    much a fault as a wrong thread."""
    events = [row for row in log.read_by_kind(conn, _ASSERTION) if row.id <= up_to]
    graph = fold_graph(
        ((row.id, row.recorded_at, row.payload) for row in events), class_states(log, conn, up_to)
    )
    return differences(store.read_graph_threads(conn), graph) + version_differences(
        store.read_graph_versions(conn), rebuilt_versions(events)
    )


def projection_stands[Conn](store: GraphStore[Conn], conn: Conn, outcome: Outcome) -> bool:
    """Whether the projection stands, in the snapshot of `conn`, where the
    catch-up of `outcome` left it: at the same version, and up to its
    `up_to_id` or beyond. It doesn't where another catch-up rebuilt it in
    between, by another version of the code or after a forced rebuild, and
    a reader then folds the log for that read rather than show an empty or
    half-built projection as if it were the graph."""
    state = store.projection_state(conn, outcome.name)
    return (
        state is not None
        and state.version == outcome.version
        and state.up_to_id >= outcome.up_to_id
    )
