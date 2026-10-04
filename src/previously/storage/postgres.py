# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The storage interface against PostgreSQL.

Deliberately narrow (architecture §5, frozen design record): no update, no
delete, no transaction control to the outside, no SQL passthrough, no
returning of database objects. Those five are the interface's own argument and
have no page in `docs/`; {ref}`module-boundaries` settles which module may
import which, not which methods this one has.
"""

from contextlib import contextmanager
from previously.contract.rows import EventRow
from previously.contract.rows import Tip
from previously.contract.rows import UnitRow
from previously.storage.errors import ChainPositionTaken
from previously.storage.errors import InvalidDsn
from previously.storage.errors import MigrationPending
from previously.storage.errors import ServerUnreachable
from previously.storage.errors import SourceKeyTaken
from previously.storage.schema import event
from previously.storage.schema import source_key
from previously.storage.schema import unit
from sqlalchemy import Connection
from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy.exc import ArgumentError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import ProgrammingError
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterator
    from collections.abc import Sequence

# Three indexes mark the same class of conflict. Ruling T6-b had excluded
# event_hash_idx here, on the grounds that a duplicate `hash` means "the same
# event was built twice" — recomputed (review finding W2, task 7, fix round 2)
# that is wrong: `id` and `prev_hash` go into
# `previously.core.hashing.event_hash`, so two concurrent writers can only
# compute the same `hash` if they computed the same `id` and the same
# `prev_hash` out of the same tip — that is, at the same chain position.
# event_hash_idx is therewith the same incident as event_pkey and
# event_prev_hash_idx, not an independent deterministic error. Which of the
# three PostgreSQL reports depends on the physical order of the index OIDs,
# not on a decision — all three therefore have to be translated alike, or else
# a `REINDEX CONCURRENTLY`, a `pg_repack` or a future migration makes the
# appending procedure dependent on the index order. Only event_kind_check
# stays untranslated: it is independent of any chain position.
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

    @contextmanager
    def begin(self) -> Generator[Connection]:
        """A connection with a transaction — and the place where two of the
        three sqlalchemy exceptions out of review finding W2 are translated.

        `OperationalError` (server unreachable) arises only while the
        connection is actually being established, that is, inside
        `self._engine.begin()`. `ProgrammingError` (schema missing), by
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
            with self._engine.begin() as conn:
                yield conn
        except OperationalError as error:
            address = self._engine.url.render_as_string(hide_password=True)
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
    # different snapshots instead of one. A check report over several points in
    # time is no statement about the chain: a forgery could wander back and
    # forth between two reads and appear consistent in every single snapshot.
    # The transaction boundary therefore belongs to the caller, who knows what
    # has to be read together.
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
            yield EventRow(
                id=row.id,
                kind=row.kind,
                recorded_at=row.recorded_at,
                occurred_at=row.occurred_at,
                prev_hash=row.prev_hash,
                hash=row.hash,
                payload_hash=row.payload_hash,
                units_hash=row.units_hash,
                payload=row.payload,
            )

    def units(self, conn: Connection, event_id: int) -> list[UnitRow]:
        return [
            UnitRow(
                event_id=row.event_id,
                seq=row.seq,
                content=row.content,
                start_ms=row.start_ms,
                end_ms=row.end_ms,
                speaker=row.speaker,
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
