# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The storage interface against PostgreSQL.

Deliberately narrow (architecture §5, frozen design record): no delete on the
log, no update on it beyond the two an erasure needs, no transaction control
to the outside, no SQL passthrough, no returning of database objects. The
architecture said "no update" without that qualification; since stage 1c
the log has exactly two `UPDATE`s and still no `DELETE` — `erase_payload`
and `erase_units`, both behind `RedactionStore`, the third protocol. What
they may set is enumerated in them — the content and its salt, and on a
unit the speaker and the timestamps — and every digest stays
({ref}`erasure`). Nothing typed against `LogStore` reaches either. The five
properties are the interface's own argument and have no page in `docs/`;
{ref}`module-boundaries` settles which module may import which, not which
methods this one has.

The projection methods below delete and update, and that is the point: a
projection is disposable, the log is not; the protocols in `contract.store`
keep the two apart.
"""

from contextlib import contextmanager
from previously.contract.rows import ChronicleRow
from previously.contract.rows import EventRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import SourceStatsRow
from previously.contract.rows import Tip
from previously.contract.rows import TipAndBookmark
from previously.contract.rows import UnitRow
from previously.storage.errors import ChainPositionTaken
from previously.storage.errors import InvalidDsn
from previously.storage.errors import MigrationPending
from previously.storage.errors import ServerUnreachable
from previously.storage.errors import SourceKeyTaken
from previously.storage.schema import event
from previously.storage.schema import p_chronicle
from previously.storage.schema import p_source_stats
from previously.storage.schema import projection_state
from previously.storage.schema import source_key
from previously.storage.schema import unit
from sqlalchemy import Connection
from sqlalchemy import create_engine
from sqlalchemy import delete
from sqlalchemy import Engine
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import null
from sqlalchemy import Row
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import ArgumentError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import ProgrammingError
from typing import Any
from typing import ClassVar
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterator
    from collections.abc import Sequence
    from contextlib import AbstractContextManager
    from datetime import datetime
    from sqlalchemy import Table

# Three indexes mark the same class of conflict. Ruling T6-b had excluded
# event_hash_idx here, on the grounds that a duplicate `hash` means "the same
# event was built twice" — recomputed (review finding W2, task 7, fix round 2)
# that is wrong: `id` and `prev_hash` go into the event hash of either version,
# `event_hash` and `event_hash_v2` in `previously.core.hashing`, so two
# concurrent writers can only compute the same `hash` if they computed the
# same `id` and the same `prev_hash` out of the same tip — that is, at the
# same chain position.
# event_hash_idx is therewith the same incident as event_pkey and
# event_prev_hash_idx, not an independent deterministic error. Which of the
# three PostgreSQL reports depends on the physical order of the index OIDs,
# not on a decision — all three therefore have to be translated alike, or else
# a `REINDEX CONCURRENTLY`, a `pg_repack` or a future migration makes the
# appending procedure dependent on the index order. The `CHECK` constraints
# stay untranslated, `event_kind_check` among them: none of them depends on a
# chain position.
_CHAIN_POSITION_CONSTRAINTS = frozenset({"event_prev_hash_idx", "event_pkey", "event_hash_idx"})
_SOURCE_KEY_CONSTRAINT = "source_key_pkey"


def _constraint_name(error: IntegrityError) -> str | None:
    """Reads the name of the violated constraint out of the psycopg diagnosis.

    `error.orig` is typed by SQLAlchemy only as `BaseException | None`; that
    type does not know `diag`. `getattr` instead of a `cast` onto the psycopg
    type, so that a driver without a `diag` attribute does not break off here
    with an `AttributeError` but yields `None`, and the original error passes
    through untranslated. Deliberately via `diag.constraint_name`, not by a
    substring search in the error text — the text depends on language and
    version, the constraint name does not.
    """
    diag = getattr(error.orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    return name if isinstance(name, str) else None


class PostgresStorage:
    def __init__(self, engine: Engine) -> None:
        # READ COMMITTED explicitly: the appending procedure rests on the
        # unique indexes serialising. Under SERIALIZABLE a serialisation error
        # would come instead — a different class of error.
        self._engine = engine.execution_options(isolation_level="READ COMMITTED")
        # The chain check reads here instead, see `snapshot`.
        self._snapshot_engine = engine.execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        )

    def begin(self) -> AbstractContextManager[Connection]:
        """A connection with a transaction at READ COMMITTED, for writing and
        for every read that does not need one state across its statements."""
        return self._transaction(self._engine)

    def snapshot(self) -> AbstractContextManager[Connection]:
        """A read-only transaction in which every statement sees the same state.

        For the chain check ({ref}`hash-chain`): it reads in batches and then
        counts, and under the READ COMMITTED of `begin` every one of those
        statements gets a snapshot of its own, so an append committing between
        the last read and the count made the two disagree. Measured on
        2026-10-04 with appends running concurrently: 27 of 539 runs of
        `examine` reported rows it had not reached. REPEATABLE READ takes one
        snapshot at the first statement and keeps it to the end
        ({ref}`concurrency`).

        It is safe beside the appending procedure because, as PostgreSQL's
        documentation on transaction isolation says, a read-only transaction
        at REPEATABLE READ never has a serialization conflict, and under MVCC
        reading never blocks writing. The level is part of that sentence: at
        SERIALIZABLE, the same page says, what even a read-only transaction
        reads is valid only once it commits, unless it is deferrable.
        """
        return self._transaction(self._snapshot_engine)

    @contextmanager
    def _transaction(self, engine: Engine) -> Generator[Connection]:
        """A connection with a transaction on `engine` — and the place where
        two of the three sqlalchemy exceptions out of review finding W2 are
        translated, for `begin` and `snapshot` alike.

        `OperationalError` (server unreachable) arises only while the
        connection is actually being established, that is, inside
        `engine.begin()`. `ProgrammingError` (schema missing), by
        contrast, typically arises only once the caller runs a query **inside**
        the `with` block — not during the setup itself. Because the whole
        `with` block stands inside a `try` here, an exception out of the
        caller's body (out of `tip` or `read`, say) reaches this place
        nonetheless: a `@contextmanager` generator gets an exception thrown
        inside the `with` block re-raised at its `yield` (via
        `generator.throw`) before it travels on. The third case,
        `ArgumentError` on an unparsable DSN, does **not** belong here,
        because it arises in `create_engine` already, before this method
        exists at all — see `from_dsn`.

        A fourth, unnamed sqlalchemy exception (`IntegrityError`, say, which
        `insert_event` translates itself) this `try` deliberately does not
        catch: an unknown error dressed up as a handy message is worse than a
        stack trace.
        """
        try:
            with engine.begin() as conn:
                yield conn
        except OperationalError as error:
            address = engine.url.render_as_string(hide_password=True)
            raise ServerUnreachable(
                f"database server at {address} does not answer — is PostgreSQL "
                "running there, and is it reachable from here?"
            ) from error
        except ProgrammingError as error:
            raise MigrationPending(
                "database schema incomplete — `uv run alembic upgrade head` has not run yet"
            ) from error

    def tip(self, conn: Connection) -> Tip | None:
        """Tip of the chain. Both values out of one SELECT, never out of two."""
        row = conn.execute(
            select(event.c.id, event.c.hash).order_by(event.c.id.desc()).limit(1)
        ).one_or_none()
        return None if row is None else Tip(id=row.id, hash=row.hash)

    def lookup(self, conn: Connection, source: str, external_id: str) -> int | None:
        return conn.execute(
            select(source_key.c.event_id).where(
                source_key.c.source == source,
                source_key.c.external_id == external_id,
            )
        ).scalar_one_or_none()

    def insert_event(
        self,
        conn: Connection,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
    ) -> None:
        try:
            conn.execute(
                insert(event).values(
                    id=row.id,
                    kind=row.kind,
                    recorded_at=row.recorded_at,
                    occurred_at=row.occurred_at,
                    prev_hash=row.prev_hash,
                    hash=row.hash,
                    payload_hash=row.payload_hash,
                    units_hash=row.units_hash,
                    payload=row.payload,
                    # Out of the row and never through the column's default:
                    # the default is there for rows older than the column,
                    # and a row written now says which format it was hashed
                    # in ({ref}`hash-version-2`).
                    hash_version=row.hash_version,
                    payload_salt=row.payload_salt,
                )
            )
            if units:
                conn.execute(
                    insert(unit),
                    [
                        {
                            "event_id": u.event_id,
                            "seq": u.seq,
                            "content": u.content,
                            "start_ms": u.start_ms,
                            "end_ms": u.end_ms,
                            "speaker": u.speaker,
                            "digest": u.digest,
                            "salt": u.salt,
                        }
                        for u in units
                    ],
                )
            if key is not None:
                source, external_id = key
                conn.execute(
                    insert(source_key).values(
                        source=source, external_id=external_id, event_id=row.id
                    )
                )
        except IntegrityError as error:
            name = _constraint_name(error)
            if name in _CHAIN_POSITION_CONSTRAINTS:
                raise ChainPositionTaken(name) from error
            if name == _SOURCE_KEY_CONSTRAINT:
                raise SourceKeyTaken(name) from error
            raise

    # The five reading methods below — `read`, `units`, `units_by_event`,
    # `count_events` and `source_keys` — take the `Connection` in, just like
    # `tip`, `lookup` and `insert_event` (review finding G4 of the final
    # review). It said "three" until finding W-3: the count was right when it
    # was written and then `count_events` and `units_by_event` arrived, so it
    # names them now instead of counting them.
    #
    # Before, `read` established a connection of its own and `units` another
    # one per call — with the unit check out of K1 that would have become one
    # connection per event, and the chain check would have seen hundreds of
    # different snapshots. A check report over several points in time is no
    # statement about the chain: a forgery could wander back and forth between
    # two reads and appear consistent in every single snapshot. The
    # transaction therefore belongs to the caller, who knows what has to be
    # read together — and one transaction is one snapshot only when the caller
    # took it from `snapshot`: under the READ COMMITTED of `begin`, every
    # statement sees a snapshot of its own.
    def read(self, conn: Connection, from_id: int, limit: int) -> Iterator[EventRow]:
        """A server-side cursor: materialises nothing."""
        query = (
            select(event)
            .where(event.c.id >= from_id)
            .order_by(event.c.id)
            .limit(limit)
            .execution_options(stream_results=True, yield_per=100)
        )
        for row in conn.execute(query):
            yield _event_row(row)

    def read_by_kind(self, conn: Connection, kind: str) -> Iterator[EventRow]:
        """Every event of one kind, in chain order, through a server-side
        cursor like `read`.

        `storage` does not interpret a payload, so the question "which events
        are redactions" is not asked in SQL here: `core.redaction` reads the
        actions and decides ({ref}`erasure`).
        """
        query = (
            select(event)
            .where(event.c.kind == kind)
            .order_by(event.c.id)
            .execution_options(stream_results=True, yield_per=100)
        )
        for row in conn.execute(query):
            yield _event_row(row)

    def units(self, conn: Connection, event_id: int) -> list[UnitRow]:
        return [
            UnitRow(
                event_id=row.event_id,
                seq=row.seq,
                content=row.content,
                start_ms=row.start_ms,
                end_ms=row.end_ms,
                speaker=row.speaker,
                digest=row.digest,
                salt=row.salt,
            )
            for row in conn.execute(
                select(unit).where(unit.c.event_id == event_id).order_by(unit.c.seq)
            )
        ]

    def units_by_event(
        self, conn: Connection, event_ids: Sequence[int]
    ) -> dict[int, list[UnitRow]]:
        """Units **by batch**: one query per batch, not one per event.

        The batch counterpart to `units`, for the same reason `source_keys`
        exists (finding N2): `verify` fetched the source attributions in one
        query with the explicit reasoning that asking per event would be a
        million queries over a million events — and then asked for the units
        per event six lines further down. A self-contradiction in the code,
        and in the one routine that runs over the whole history at that.

        **Ordered by `(event_id, seq)`**, so that every list comes out
        ascending by `seq`. That order goes into `units_hash` and therewith
        into the event hash, so it has to be settled. `units_hash` sorts by
        `seq` itself as a second line of defence (a connector may hand its
        units over in any order), but that is no reason to deliver them here
        unordered: then two places would have to be right instead of one, and
        the one that was wrong would not show.

        Events without units are absent from the return value, like in
        `source_keys` — the caller hashes the empty set of units for them.
        `insert_event` permits an event without units, and the empty batch
        returns without a query, because `IN ()` is not valid SQL.
        """
        if not event_ids:
            return {}
        grouped: dict[int, list[UnitRow]] = {}
        for row in conn.execute(
            select(unit).where(unit.c.event_id.in_(event_ids)).order_by(unit.c.event_id, unit.c.seq)
        ):
            grouped.setdefault(row.event_id, []).append(
                UnitRow(
                    event_id=row.event_id,
                    seq=row.seq,
                    content=row.content,
                    start_ms=row.start_ms,
                    end_ms=row.end_ms,
                    speaker=row.speaker,
                    digest=row.digest,
                    salt=row.salt,
                )
            )
        return grouped

    def count_events(self, conn: Connection) -> int:
        """The number of **all** rows in `event`, without any `id` condition.

        For the count reconciliation of the chain check ({ref}`hash-chain`,
        review finding B1): `read` filters `id >= from_id`, so out of its
        own reading window the check cannot establish that there are rows
        outside it. This counter is the view from outside and must therefore
        carry no condition — an `id` condition here would have exactly the gap
        it is supposed to close.
        """
        return conn.execute(select(func.count()).select_from(event)).scalar_one()

    def source_keys(self, conn: Connection, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]:
        """Source attributions **by batch**: one query per batch, not per event.

        Events without a row are absent from the return value — `assertion`
        and `action` carry no `source_key` ({ref}`hash-chain`), and an erased
        or never-written key is the same case. The caller hashes `null` for
        that.

        The empty batch returns without a query: `IN ()` is not valid SQL, and
        SQLAlchemy's substitute expression for it would be a round trip for a
        result that is already known.
        """
        if not event_ids:
            return {}
        return {
            row.event_id: (row.source, row.external_id)
            for row in conn.execute(
                select(source_key.c.event_id, source_key.c.source, source_key.c.external_id).where(
                    source_key.c.event_id.in_(event_ids)
                )
            )
        }

    # --- RedactionStore ({ref}`erasure`) -------------------------------------
    #
    # The two `UPDATE`s this module runs on the log, and the lock in front of
    # them. Each sets every column a tombstone must not keep in one statement:
    # `event_payload_salt_check` and `unit_tombstone_check` refuse anything
    # less, so an erasure that forgot the salt would fail here rather than
    # leave a digest that can still be tried against.

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        """The row of one event, locked `FOR UPDATE` until the caller's
        transaction ends, or `None` when there is none.

        The lock is on the target of an erasure, not on the tip: the chain
        position stays the unique indexes' to decide ({ref}`concurrency`).
        """
        row = conn.execute(
            select(event).where(event.c.id == event_id).with_for_update()
        ).one_or_none()
        return None if row is None else _event_row(row)

    def erase_payload(self, conn: Connection, event_id: int) -> None:
        # `null()` and not `None` for the payload: on a JSONB column SQLAlchemy
        # writes Python `None` as JSON `null`, not as SQL `NULL`. Measured on
        # 2026-10-04 with `payload=None` here: `event_payload_object_check`
        # refused the statement, the constraint correction K-1 added for
        # exactly this confusion.
        conn.execute(
            update(event).where(event.c.id == event_id).values(payload=null(), payload_salt=None)
        )

    def erase_units(self, conn: Connection, event_id: int, seqs: Sequence[int]) -> None:
        if not seqs:
            return
        conn.execute(
            update(unit)
            .where(unit.c.event_id == event_id, unit.c.seq.in_(seqs))
            .values(content=None, salt=None, speaker=None, start_ms=None, end_ms=None)
        )

    # --- ProjectionStore ({ref}`projections`) --------------------------------

    # Name as the caller knows it -> table. `truncate_projection` takes the
    # name and not the table, because `core` must not know a `Table`.
    _PROJECTION_TABLES: ClassVar[dict[str, Table]] = {
        "chronicle": p_chronicle,
        "source-stats": p_source_stats,
    }

    def projection_state(self, conn: Connection, name: str) -> ProjectionState | None:
        row = conn.execute(
            select(projection_state).where(projection_state.c.name == name)
        ).one_or_none()
        if row is None:
            return None
        return ProjectionState(
            name=row.name, up_to_id=row.up_to_id, version=row.version, built_at=row.built_at
        )

    def set_projection_state(self, conn: Connection, state: ProjectionState) -> None:
        statement = pg_insert(projection_state).values(
            name=state.name,
            up_to_id=state.up_to_id,
            version=state.version,
            built_at=state.built_at,
        )
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[projection_state.c.name],
                set_={
                    "up_to_id": statement.excluded.up_to_id,
                    "version": statement.excluded.version,
                    "built_at": statement.excluded.built_at,
                },
            )
        )

    def truncate_projection(self, conn: Connection, name: str) -> None:
        """Empties one projection table. A plain DELETE, not TRUNCATE: TRUNCATE
        takes an ACCESS EXCLUSIVE lock and is not transactional in the sense
        that matters here — the caller's transaction has to be able to roll
        it back together with the state row."""
        try:
            table = self._PROJECTION_TABLES[name]
        except KeyError:
            raise ValueError(f"unknown projection {name!r}") from None
        conn.execute(delete(table))

    def insert_chronicle(self, conn: Connection, rows: Sequence[ChronicleRow]) -> None:
        if not rows:
            return
        conn.execute(
            insert(p_chronicle),
            [
                {
                    "event_id": r.event_id,
                    "seq": r.seq,
                    "content": r.content,
                    "occurred_at": r.occurred_at,
                    "kind": r.kind,
                    "evidence": r.evidence,
                    "source": r.source,
                    "external_id": r.external_id,
                    "speaker": r.speaker,
                    "start_ms": r.start_ms,
                    "end_ms": r.end_ms,
                }
                for r in rows
            ],
        )

    def delete_chronicle(self, conn: Connection, event_id: int, seqs: Sequence[int] | None) -> None:
        if seqs is None:
            conn.execute(delete(p_chronicle).where(p_chronicle.c.event_id == event_id))
            return
        if not seqs:
            return
        conn.execute(
            delete(p_chronicle).where(
                p_chronicle.c.event_id == event_id, p_chronicle.c.seq.in_(seqs)
            )
        )

    def source_stats(self, conn: Connection, sources: Sequence[str]) -> dict[str, SourceStatsRow]:
        if not sources:
            return {}
        return {
            row.source: SourceStatsRow(
                source=row.source,
                events=row.events,
                units=row.units,
                first_seen=row.first_seen,
                last_seen=row.last_seen,
                last_event_id=row.last_event_id,
            )
            for row in conn.execute(
                select(p_source_stats).where(p_source_stats.c.source.in_(sources))
            )
        }

    def upsert_source_stats(self, conn: Connection, rows: Sequence[SourceStatsRow]) -> None:
        """Writes the rows as given — the merge arithmetic lives in `core`
        ({ref}`projections`), so a unit test reaches it without a database."""
        if not rows:
            return
        statement = pg_insert(p_source_stats)
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[p_source_stats.c.source],
                set_={
                    "events": statement.excluded.events,
                    "units": statement.excluded.units,
                    "first_seen": statement.excluded.first_seen,
                    "last_seen": statement.excluded.last_seen,
                    "last_event_id": statement.excluded.last_event_id,
                },
            ),
            [
                {
                    "source": r.source,
                    "events": r.events,
                    "units": r.units,
                    "first_seen": r.first_seen,
                    "last_seen": r.last_seen,
                    "last_event_id": r.last_event_id,
                }
                for r in rows
            ],
        )

    # --- Reads for the command line, outside the protocols -------------------
    # Like `units`: only `cli` calls these. The protocols hold what `core`
    # needs, and `core` never reads a projection back.

    def tip_and_bookmark(self, conn: Connection, name: str) -> TipAndBookmark:
        """Both numbers out of **one** statement, for the lag of one projection.

        One transaction is not enough here, and that is the whole reason this
        method exists instead of a call to `tip` followed by one to
        `projection_state`. `__init__` sets the isolation level to READ
        COMMITTED on purpose, and under READ COMMITTED PostgreSQL gives *each
        statement* its own snapshot (PostgreSQL's documentation on transaction
        isolation says so in those words). Two statements in one transaction
        therefore still see two moments, and their difference is a number that
        was never true at either of them. One statement sees one snapshot, so
        the difference is a difference.

        The property is **structural** and has no test of its own: nothing
        observable tells one snapshot from two here, because a concurrent
        append can only make the lag larger and a concurrent catch-up only
        smaller, so both readings stay plausible. What guards it is the shape
        of the body — one `conn.execute`, two scalar subqueries — and whoever
        splits it into two statements takes the assurance back without any
        gate noticing. {ref}`projections` carries the argument.

        `coalesce` in SQL rather than `or 0` in Python: an empty log and a
        projection without a state row both yield NULL, and the reading of
        both is "nothing yet".
        """
        row = conn.execute(
            select(
                func.coalesce(select(func.max(event.c.id)).scalar_subquery(), 0).label("tip_id"),
                func.coalesce(
                    select(projection_state.c.up_to_id)
                    .where(projection_state.c.name == name)
                    .scalar_subquery(),
                    0,
                ).label("up_to_id"),
            )
        ).one()
        return TipAndBookmark(tip_id=row.tip_id, up_to_id=row.up_to_id)

    def read_chronicle(
        self,
        conn: Connection,
        *,
        since: datetime | None,
        until: datetime | None,
        limit: int,
    ) -> list[ChronicleRow]:
        """Time order, half-open window: `since` inclusive, `until` exclusive."""
        query = select(p_chronicle)
        if since is not None:
            query = query.where(p_chronicle.c.occurred_at >= since)
        if until is not None:
            query = query.where(p_chronicle.c.occurred_at < until)
        query = query.order_by(
            p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq
        ).limit(limit)
        return [
            ChronicleRow(
                event_id=row.event_id,
                seq=row.seq,
                content=row.content,
                occurred_at=row.occurred_at,
                kind=row.kind,
                evidence=row.evidence,
                source=row.source,
                external_id=row.external_id,
                speaker=row.speaker,
                start_ms=row.start_ms,
                end_ms=row.end_ms,
            )
            for row in conn.execute(query)
        ]

    def read_source_stats(self, conn: Connection) -> list[SourceStatsRow]:
        return [
            SourceStatsRow(
                source=row.source,
                events=row.events,
                units=row.units,
                first_seen=row.first_seen,
                last_seen=row.last_seen,
                last_event_id=row.last_event_id,
            )
            for row in conn.execute(select(p_source_stats).order_by(p_source_stats.c.source))
        ]


def _event_row(row: Row[Any]) -> EventRow:
    """One row of `event` as the contract's type, for every reader of it."""
    return EventRow(
        id=row.id,
        kind=row.kind,
        recorded_at=row.recorded_at,
        occurred_at=row.occurred_at,
        prev_hash=row.prev_hash,
        hash=row.hash,
        payload_hash=row.payload_hash,
        units_hash=row.units_hash,
        payload=row.payload,
        hash_version=row.hash_version,
        payload_salt=row.payload_salt,
    )


def from_dsn(dsn: str) -> PostgresStorage:
    """Storage out of a connection string.

    Creating the engine belongs here (ruling T9-a), not in the command line:
    `cli` is to need to know neither that SQLAlchemy exists nor what a driver
    URL looks like — only `storage` knows SQL.

    `create_engine` parses the DSN immediately, not only at the first
    connection attempt — an unparsable DSN raises `ArgumentError` here already
    (review finding W2, case 1). The raw `dsn` deliberately does **not** go
    into the message: it could carry a password that failed to parse only
    because there is an error somewhere else in the string.
    """
    try:
        engine = create_engine(dsn)
    except ArgumentError as error:
        raise InvalidDsn(
            "PREVIOUSLY_DSN is not a valid connection string — something like "
            "postgresql+psycopg://user:pass@host:5432/database is expected"
        ) from error
    return PostgresStorage(engine)
