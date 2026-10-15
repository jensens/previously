# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
r"""The store protocols: what `core` may ask of a store, and nothing more.

`LogStore` is what the modules of `core` that write or read the log call —
fifteen methods, counted on 2026-10-12 by this command, run from the root of
the repository in bash or fish:

    grep -ohE '(storage|log)\.[a-z_]*\(' $(grep -rl LogStore src/previously/core) \
        | sed 's/.*\.//' | sort -u | wc -l

The files are every module of `core` that names `LogStore`, twelve that day
with `core/assertions.py`, and fifteen on 2026-10-14, when `core/vocabulary.py`,
`core/classes.py` and `core/graph_write.py` joined them and the count stayed
fifteen; sixteen on 2026-10-15, when `core/projection/graph.py` joined them,
reading the log through `events_by_id` and `actions`, and the count stayed
fifteen again; it is not copied from the method list of the implementation.
Where `__pycache__` directories exist, `grep -rl` lists their compiled files
as well, and the first `grep` takes no name out of them, so the count stays
the same. The docstring is raw so that the text in this file is the command, backslashes as
they stand. Until 2026-10-11 the command named its files one by one, six of
them, and the sentence beside it called those "the six modules that name
`LogStore` today" long after `grep -rl` found more: nine at the start of the
MCP work, eleven at its end. The count of thirteen it gave was still right,
since the modules it left out call nothing the six do not, but the sentence
was not.
Without the `sed` stage, as the command stood here until 2026-10-06, `sort -u`
leaves a name once for each of the two prefixes it is called through, and the
claim was a count of those by hand. It was eight until the chain check took
`snapshot` instead of `begin` for its reads, and `append` still takes `begin`,
so both stay; it was nine until stage 1c, whose redactions are read with
`read_by_kind`, and ten until `verify` and `redact` read the blob register with
`blobs_by_event`. The erasure of blobs took it to thirteen: `redact` asks
`events_by_blob`, which until then only the command line asked, and `verify
--blobs` reads the whole register with `blob_references`. The fourteenth is
`actions`, which `core.policy` reads the policy with since 2026-10-11, and
`core.clients` the dates of the clients, so that the policy read of every MCP
call does not read every access entry the calls before it wrote
({ref}`mcp-open-limits`). The fifteenth is `events_by_id`, with which
`core.assertions` reads the source events of every entry a list looks at in
one query since 2026-10-12, where `read` took one query per event
({ref}`assertions-folded`).
The protocol declares sixteen: `observations` came on 2026-10-11 with the MCP
server, and `core` does not call it: `mcp_server/read.py` does, to read the
chronicle of a circle from the log (decision 3 of the 2026-10-11 MCP read
access plan). `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py`
names the eight the server calls, `observations` among them, counted on
2026-10-14; the eighth is `read_by_kind`, with which `mcp_server/read.py`
reads the rejections of a version of an entity or a relation. The sentence
said six until 2026-10-12 and seven until 2026-10-14, each a count no longer
true by then. Typing `core` against this protocol instead of against
`PostgresStorage` removes the edge `core -> storage.postgres`, and with it
the two named exemptions in `.importlinter` and the test that guarded them
({ref}`module-boundaries`).

`Conn` is the connection type. Only `storage` knows what it is; `core` passes
it back to the store it came from and never looks inside.

Nothing imports this module at runtime, and the coverage report says so:
every importer names a protocol only under `TYPE_CHECKING`, so the module
never reaches `sys.modules` and stands at 0%. Measured on 2026-10-04, after
`RedactionStore` arrived, by importing `previously.cli`, `core.append`,
`core.verify`, `core.redact`, `core.redaction` and `core.projection.worker`
and looking. That is the
protocol working as intended rather than something left untested — the method
bodies are `...` and have nothing to execute; what has to hold is that
`PostgresStorage` satisfies the protocol, and pyright checks that at every
call site ({ref}`module-boundaries`).
"""

from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence
    from contextlib import AbstractContextManager
    from datetime import datetime
    from previously.contract.rows import ChronicleRow
    from previously.contract.rows import EventRow
    from previously.contract.rows import GraphThreadRow
    from previously.contract.rows import GraphVersionRow
    from previously.contract.rows import ProjectionState
    from previously.contract.rows import SourceStatsRow
    from previously.contract.rows import Tip
    from previously.contract.rows import UnitRow
    from previously.contract.types import Watermark


class LogStore[Conn](Protocol):
    """The append-only log: write once, read in chain order, never change.

    That holds for this protocol and is its point: what may change in the log
    since erasure exists is a type of its own, `RedactionStore`, and a caller
    typed against this one cannot reach it ({ref}`erasure`).
    """

    def begin(self) -> AbstractContextManager[Conn]: ...
    def snapshot(self) -> AbstractContextManager[Conn]: ...
    def tip(self, conn: Conn) -> Tip | None: ...
    def lookup(self, conn: Conn, source: str, external_id: str) -> int | None: ...
    def insert_event(
        self,
        conn: Conn,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
        blobs: Sequence[bytes] = (),
    ) -> None: ...
    def read(self, conn: Conn, from_id: int, limit: int) -> Iterator[EventRow]: ...
    def events_by_id(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, EventRow]: ...
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
    def read_by_kind(self, conn: Conn, kind: str) -> Iterator[EventRow]: ...
    def actions(self, conn: Conn, action: str) -> Iterator[EventRow]: ...
    def blobs_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[bytes]]: ...
    def events_by_blob(self, conn: Conn, sha256: bytes) -> list[int]: ...
    def blob_references(self, conn: Conn) -> Iterator[tuple[bytes, int]]: ...
    def observations(
        self,
        conn: Conn,
        *,
        since: datetime | None,
        until: datetime | None,
        source: str | None,
        after: tuple[datetime, int] | None,
        limit: int,
    ) -> Iterator[EventRow]: ...


class RedactionStore[Conn](Protocol):
    """What an erasure may change in the log, and nothing more ({ref}`erasure`).

    A protocol of its own, so that "the log never changes" stays a statement
    about `LogStore` and the exception is a type: nothing typed against
    `LogStore` can erase, and what can erase is listed here.

    `lock_event` reads the row with `FOR NO KEY UPDATE`, so that two erasures
    that lock the same event run one after the other, while a foreign-key
    check on that event does not wait for either. `erase_payload` sets
    `payload` and `payload_salt` to `NULL` in one `UPDATE`; `erase_units` sets
    `content`, `salt`, `speaker`, `start_ms` and `end_ms` of the named units
    to `NULL` in one `UPDATE`, and an empty sequence is no statement. Every
    digest stays: the chain depends on them.
    """

    def lock_event(self, conn: Conn, event_id: int) -> EventRow | None: ...
    def erase_payload(self, conn: Conn, event_id: int) -> None: ...
    def erase_units(self, conn: Conn, event_id: int, seqs: Sequence[int]) -> None: ...


class ProjectionStore[Conn](Protocol):
    """A projection store: emptied, filled, updated — disposable by design.

    Separate from `LogStore` so that "carries no truth of its own"
    (architecture §4.4, frozen design record) stays a type and not a
    comment: nothing typed against `LogStore` can truncate, and nothing typed
    against this protocol can append to the log.

    `lock_projection_state` reads the state row of one projection and locks
    it until the transaction ends, so that two catch-ups of the same
    projection run one after the other and each takes `up_to_id` and the
    version from the row, never from what it read before. Without a row it
    writes one in its place, at `up_to_id` 0 and version 0, holds that the
    same way, and returns `None`: a second transaction asking meanwhile
    waits until the first ends and then finds the row the first committed.
    Version 0 is no version a projection declares, so a placeholder that
    were ever committed as it is would only make the next catch-up rebuild.

    `delete_chronicle` takes the chronicle rows of one event: those of the
    named units, or with `None` every row of the event; an empty sequence is
    no statement. It is how the chronicle follows an erasure
    ({ref}`projections`).

    `upsert_source_stats` writes the rows it is given. The arithmetic that
    merges an existing row with a batch — count plus count, earliest of two
    `first_seen` — is domain logic and lives in `core.projection.source_stats`,
    where a unit test reaches it without a database. Done in SQL
    (`ON CONFLICT DO UPDATE SET …`) the correctness of the incremental step
    would sit in `storage`, and the claim "derivation without SQL" would be
    false.

    The graph projection keeps two tables under one name, and
    `truncate_projection("graph")` empties both. `insert_graph_versions`
    writes rows of `p_graph_version`, `graph_versions` reads those of the
    given ids, `graph_version_ids` the ids of every row of the given
    subjects, and `class_subjects` the subjects of the versions under any of
    the given approval class events; `delete_graph_versions` takes the rows
    of the given ids. `upsert_graph_threads` writes rows of `p_graph_thread`
    as given, replacing what stood under their subjects, and
    `delete_graph_threads` takes the rows of the given subjects. Which
    threads to fold again and what they stand at is decided in
    `core.projection.graph`, for the reason `upsert_source_stats` gives. An
    empty sequence is no statement for any of them.
    """

    def begin(self) -> AbstractContextManager[Conn]: ...
    def lock_projection_state(self, conn: Conn, name: str) -> ProjectionState | None: ...
    def set_projection_state(self, conn: Conn, state: ProjectionState) -> None: ...
    def truncate_projection(self, conn: Conn, name: str) -> None: ...
    def insert_chronicle(self, conn: Conn, rows: Sequence[ChronicleRow]) -> None: ...
    def delete_chronicle(self, conn: Conn, event_id: int, seqs: Sequence[int] | None) -> None: ...
    def source_stats(self, conn: Conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]: ...
    def upsert_source_stats(self, conn: Conn, rows: Sequence[SourceStatsRow]) -> None: ...
    def insert_graph_versions(self, conn: Conn, rows: Sequence[GraphVersionRow]) -> None: ...
    def graph_versions(self, conn: Conn, ids: Sequence[int]) -> dict[int, GraphVersionRow]: ...
    def graph_version_ids(self, conn: Conn, subjects: Sequence[int]) -> dict[int, list[int]]: ...
    def class_subjects(self, conn: Conn, under_ids: Sequence[int]) -> set[int]: ...
    def delete_graph_versions(self, conn: Conn, ids: Sequence[int]) -> None: ...
    def upsert_graph_threads(self, conn: Conn, rows: Sequence[GraphThreadRow]) -> None: ...
    def delete_graph_threads(self, conn: Conn, subjects: Sequence[int]) -> None: ...


class WatermarkStore[Conn](Protocol):
    """How far each connector has read, one row per connector.

    A protocol of its own, so that what a connector remembers stays apart
    from the log: nothing typed against `LogStore` can write a watermark, and
    nothing typed against this one can append. `watermark` reads the row of
    one connector, or `None` when it has read nothing yet. `set_watermark`
    writes the row and replaces whatever stood there, the position as a
    whole; it runs in the caller's transaction, so that a watermark can stand
    or fall with the events it covers. It refuses a `set_at` without a time
    zone with a `ValueError`.
    """

    def watermark(self, conn: Conn, connector: str) -> Watermark | None: ...
    def set_watermark(self, conn: Conn, mark: Watermark) -> None: ...
