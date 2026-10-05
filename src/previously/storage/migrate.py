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
from dataclasses import dataclass
from previously.storage.errors import UnknownRevision
from previously.storage.postgres import from_dsn
from sqlalchemy import text


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


def migrate(dsn: str) -> Migrated:
    """Brings the database at `dsn` to the newest revision, one run at a time.

    Two migration jobs of one release can start at once in a cluster, and
    without the lock both would run the same DDL; the second waits now, and
    then finds the schema up to date.

    The lock sits on a connection of its own, and `command.upgrade` opens a
    second one through `env.py`: a session-level lock belongs to the session
    that holds it, so the second connection is not in its way, and every other
    `migrate` queues behind the first. The revision is read after the lock is
    granted, and under the READ COMMITTED of `begin` that read takes a fresh
    snapshot, so it sees what a `migrate` that held the lock before committed.

    The connection comes out of `from_dsn` and `begin`, the way every command
    gets one, so an unparsable string, a server that does not answer or a
    password it refuses become the same one sentence as there, without the
    password. `command.upgrade` runs inside the same `with`, so a failure to
    connect on Alembic's own connection is translated the same way.
    """
    config = Config()
    config.set_main_option("script_location", "previously:migrations")
    # Escaped, because Alembic's configuration is a `ConfigParser` that reads
    # `%` as the start of an interpolation, and a password with a character
    # a URL has to escape arrives percent-encoded. Unescaped, it raised
    # `ValueError: invalid interpolation syntax`, quoting the whole string,
    # password included. `env.py` escapes it again when it sets it back.
    config.set_main_option("sqlalchemy.url", dsn.replace("%", "%%"))
    script = ScriptDirectory.from_config(config)
    # `None` only when the directory holds no revision at all; several heads
    # raise instead. The tree has one head, and the tests read it from here.
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("previously:migrations holds no revision")
    storage = from_dsn(dsn)
    try:
        with storage.begin() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            try:
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
                    command.upgrade(config, "head")
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
            return Migrated(before=before, head=head)
    finally:
        storage.close()
