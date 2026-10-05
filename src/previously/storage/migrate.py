# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bringing a database to the newest revision of the schema.

This is how an installed previously creates and upgrades its schema: a
container image carries the package and nothing else, so the way that works
in a checkout, `alembic upgrade head` beside `alembic.ini`, is not there. The
migrations live in the package, `previously:migrations`, so this works from
an installed wheel without a checkout and without `alembic.ini`.

Only forward: going back stays `alembic downgrade`, in development.
"""

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from contextlib import contextmanager
from dataclasses import dataclass
from previously.storage.errors import MigrationFailed
from previously.storage.errors import UnknownRevision
from previously.storage.postgres import diagnosis
from previously.storage.postgres import from_dsn
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import OperationalError
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Generator

# The key of the session-level advisory lock `migrate` holds while it runs.
# Public because the test that holds it against a waiting `migrate` takes the
# same lock. The four bytes spell "prev" in ASCII. Advisory locks are scoped
# to one database, and this is the only one previously takes, so only another
# program on the same database that picked the same number could collide.
MIGRATION_LOCK = 0x70726576


@dataclass(frozen=True)
class Migrated:
    """What `migrate` found and where it left the database."""

    before: str | None  # None: the database had no revision
    head: str


@contextmanager
def _refusals(head: str) -> Generator[None]:
    """The database's own reason, for any database error in the block but a
    failure to connect.

    A failure to connect is `_transaction`'s to translate, and goes on to it
    unchanged. Any other database error is the database answering and
    refusing: a role that may not read `alembic_version` or create a table,
    an event trigger that refuses DDL. That is not the missing schema
    `MigrationPending` reports, whose advice would be to run this very
    command again; the server's own reason is what helps, and it carries no
    connection string.
    """
    try:
        yield
    except DBAPIError as error:
        if isinstance(error, OperationalError):
            raise
        reason = diagnosis(error, "message_primary") or type(error.orig).__name__
        raise MigrationFailed(f"the database refused the migration to {head}: {reason}") from error


def migrate(dsn: str) -> Migrated:
    """Brings the database at `dsn` to the newest revision, one run at a time.

    Two migration jobs of one release can start at once in a cluster, and
    without the lock both would run the same DDL; the second waits now, and
    then finds the schema up to date.

    The lock sits on a connection of its own, and the upgrade runs on a
    second one: a session-level lock belongs to the session that holds it,
    so the second connection is not in its way, and every other `migrate`
    queues behind the first. The lock is released only once the upgrade has
    committed, so whoever comes next reads the new revision.

    The lock connection runs in autocommit, out of `autocommit`: the lock,
    the read of the revision and the release are each a statement of their
    own, with no transaction around them that an error could abort. The read
    comes after the lock is granted, so it sees what a `migrate` that held
    the lock before committed.

    Both connections come out of `from_dsn`, the way every command gets one,
    so an unparsable string, a server that does not answer or a password it
    refuses become the same one sentence as there, which names database,
    host and port and nothing else of the string. The upgrade's connection
    is handed to `env.py` in Alembic's `attributes`, and Alembic never gets
    the string: `from_dsn` reads it by a grammar of its own and builds the
    URL from the parts, and a string handed on would be parsed a second
    time, by SQLAlchemy's parser, whose cut would be one more thing to hold
    to the grammar's. Alembic's configuration also reads `%` as the start of
    an interpolation; measured on 2026-10-05, a string with a percent-encoded
    password handed to it unescaped raised a `ValueError` that quoted it.
    """
    config = Config()
    config.set_main_option("script_location", "previously:migrations")
    script = ScriptDirectory.from_config(config)
    # `None` only when the directory holds no revision at all; several heads
    # raise instead. The tree has one head, and the tests read it from here.
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("previously:migrations holds no revision")
    storage = from_dsn(dsn)
    try:
        with storage.autocommit() as conn:
            with _refusals(head):
                # Inside: a database that does not let this role call
                # `pg_advisory_lock` refuses it with a `ProgrammingError`,
                # which outside would become `MigrationPending`, the advice to
                # run this very command again.
                conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
                before = MigrationContext.configure(conn).get_current_revision()
            if before is not None:
                try:
                    script.get_revision(before)
                except CommandError as error:
                    raise UnknownRevision(
                        f"the database is at revision {before}, which this version of "
                        f"previously does not know; it knows revisions up to {head}"
                    ) from error
            if before != head:
                # `_refusals` inside the `with`, so that a refusal reaches
                # `_transaction` as `MigrationFailed` and not as the
                # `ProgrammingError` it turns into `MigrationPending`.
                with storage.begin() as upgrade, _refusals(head):
                    config.attributes["connection"] = upgrade
                    command.upgrade(config, "head")
            # Released here, after success, and not in a `finally`: on the way
            # out with an error, `storage.close()` below closes the session,
            # and the lock goes with it. An unlock on that way could only fail
            # on a connection that is broken, and its error would hide the one
            # that matters.
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
            return Migrated(before=before, head=head)
    finally:
        storage.close()
