# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The store protocols: what `core` may ask of a store, and nothing more.

`LogStore` is what the modules of `core` that write or read the log call —
eleven methods, counted on 2026-10-05 as the distinct names that
`grep -ohE '(storage|log)\\.[a-z_]*\\(' FILES | sort -u` prints, with FILES
the five modules that name `LogStore` today — `append.py`, `verify.py`,
`redact.py`, `redaction.py` and `projection/worker.py` under
`src/previously/core/` — and not copied from the method list of the
implementation. It was eight until the chain
check took `snapshot` instead of `begin` for its reads, and `append` still
takes `begin`, so both stay; it was nine until stage 1c, whose redactions
are read with `read_by_kind`, and ten until `verify` and `redact` read the
blob register with `blobs_by_event`. The protocol declares a twelfth,
`events_by_blob`, which no module of `core` calls on 2026-10-05: the
command line asks it before `blob get` fetches, and it stands here so that
`core` can be typed against it when an erasure of a blob asks the same
question. Typing `core` against
this protocol instead of against `PostgresStorage` removes the edge
`core -> storage.postgres`, and with it the two named exemptions in
`.importlinter` and the test that guarded them ({ref}`module-boundaries`).

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
    from previously.contract.rows import ChronicleRow
    from previously.contract.rows import EventRow
    from previously.contract.rows import ProjectionState
    from previously.contract.rows import SourceStatsRow
    from previously.contract.rows import Tip
    from previously.contract.rows import UnitRow


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
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
    def read_by_kind(self, conn: Conn, kind: str) -> Iterator[EventRow]: ...
    def blobs_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[bytes]]: ...
    def events_by_blob(self, conn: Conn, sha256: bytes) -> list[int]: ...


class RedactionStore[Conn](Protocol):
    """What an erasure may change in the log, and nothing more ({ref}`erasure`).

    A protocol of its own, so that "the log never changes" stays a statement
    about `LogStore` and the exception is a type: nothing typed against
    `LogStore` can erase, and what can erase is listed here.

    `lock_event` reads the row with `FOR UPDATE`, so that two erasures of the
    same target run one after the other. `erase_payload` sets `payload` and
    `payload_salt` to `NULL` in one `UPDATE`; `erase_units` sets `content`,
    `salt`, `speaker`, `start_ms` and `end_ms` of the named units to `NULL` in
    one `UPDATE`, and an empty sequence is no statement. Every digest stays:
    the chain depends on them.
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
    """

    def begin(self) -> AbstractContextManager[Conn]: ...
    def projection_state(self, conn: Conn, name: str) -> ProjectionState | None: ...
    def set_projection_state(self, conn: Conn, state: ProjectionState) -> None: ...
    def truncate_projection(self, conn: Conn, name: str) -> None: ...
    def insert_chronicle(self, conn: Conn, rows: Sequence[ChronicleRow]) -> None: ...
    def delete_chronicle(self, conn: Conn, event_id: int, seqs: Sequence[int] | None) -> None: ...
    def source_stats(self, conn: Conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]: ...
    def upsert_source_stats(self, conn: Conn, rows: Sequence[SourceStatsRow]) -> None: ...
