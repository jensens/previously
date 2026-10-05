# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""`previously migrate`: the schema brought up to the newest revision, one
run at a time.

Every test gets a database of its own, created empty on the session's
container and dropped afterwards: the session database is migrated already,
and the container without a migration is shared by tests that rely on every
access to it failing.
"""

from alembic.config import Config
from alembic.script import ScriptDirectory
from dataclasses import dataclass
from previously.cli import main
from previously.storage.errors import UnknownRevision
from previously.storage.migrate import migrate
from previously.storage.migrate import Migrated
from previously.storage.migrate import MIGRATION_LOCK
from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import make_url
from sqlalchemy import text
from typing import TYPE_CHECKING

import itertools
import pytest
import secrets
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Iterator


def _head() -> str:
    """The newest revision, read from the tree rather than typed, so that the
    next migration does not have to come back here."""
    config = Config()
    config.set_main_option("script_location", "previously:migrations")
    head = ScriptDirectory.from_config(config).get_current_head()
    # The tree has one head; `migrate` reports it, and a `None` here would
    # make every comparison below compare against nothing.
    assert head is not None
    return head


HEAD = _head()
_DATABASES = itertools.count(1)


@pytest.fixture
def empty_dsn(engine: Engine) -> Iterator[str]:
    """A connection string to a fresh, empty database on the session's
    container, dropped when the test is done. `WITH (FORCE)` ends whatever
    connection a failed test left open on it."""
    name = f"migrate_{next(_DATABASES)}"
    admin = engine.execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {name}"))
    try:
        yield engine.url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))


_ROLES = itertools.count(1)


@dataclass(frozen=True)
class Role:
    """A login role without any grant beyond what PostgreSQL gives every
    role: it may connect and use schema `public`, and since PostgreSQL 15 it
    may not create anything there."""

    name: str
    password: str

    def on(self, dsn: str) -> str:
        """`dsn` with this role's name and password."""
        url = make_url(dsn).set(username=self.name, password=self.password)
        return url.render_as_string(hide_password=False)


@pytest.fixture
def role(engine: Engine) -> Iterator[Role]:
    """A fresh role, dropped when the test is done. Roles belong to the whole
    server, not to one database, so each test gets a name of its own. A test
    takes this fixture before `empty_dsn`, so that its database, and with it
    whatever the role holds there, is dropped first."""
    made = Role(f"migrate_role_{next(_ROLES)}", secrets.token_hex(16))
    admin = engine.execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"CREATE ROLE {made.name} LOGIN PASSWORD '{made.password}'"))
    try:
        yield made
    finally:
        with admin.connect() as conn:
            conn.execute(text(f"DROP ROLE {made.name}"))


def _advisory_locks(dsn: str) -> int:
    """How many sessions hold or wait for `MIGRATION_LOCK` in the database of
    `dsn`. A key that fits in 32 bits stands in `objid`, with `classid` 0."""
    engine = create_engine(dsn)
    try:
        with engine.connect() as conn:
            return conn.execute(
                text(
                    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                    "AND classid = 0 AND objid = :key "
                    "AND database = (SELECT oid FROM pg_database "
                    "WHERE datname = current_database())"
                ),
                {"key": MIGRATION_LOCK},
            ).scalar_one()
    finally:
        engine.dispose()


def _no_lock_left(dsn: str) -> bool:
    """Whether the lock is gone within ten seconds: a closed connection ends
    its session on the server a moment after the client lets go of it."""
    deadline = time.monotonic() + 10
    while _advisory_locks(dsn):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


@pytest.mark.db
def test_migrate_creates_the_schema_and_then_finds_it_up_to_date(empty_dsn: str) -> None:
    first = migrate(empty_dsn)
    assert first.before is None
    assert first.head == HEAD
    second = migrate(empty_dsn)
    assert second == Migrated(before=HEAD, head=HEAD)


def _waiting_on_the_lock(engine: Engine) -> int:
    """How many other backends of this database wait on an advisory lock."""
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid() "
                "AND wait_event_type = 'Lock' AND wait_event = 'advisory'"
            )
        ).scalar_one()


@pytest.mark.db
def test_migrate_waits_for_a_migration_that_holds_the_lock(empty_dsn: str) -> None:
    """The test takes the lock itself, starts `migrate` in a thread, sees it
    wait in `pg_stat_activity`, releases the lock, and sees it finish.

    Without the lock, two migration jobs of one release would run the same DDL
    at once; the second would fail on a table the first just created. The
    poll asks until a deadline instead of sleeping for a moment it hopes is
    long enough, and it stops early once the thread has ended, which is what
    a `migrate` that does not wait does."""
    engine = create_engine(empty_dsn)
    results: list[Migrated] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            results.append(migrate(empty_dsn))
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run)
    try:
        with engine.connect() as holder:
            holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            thread.start()
            deadline = time.monotonic() + 10
            seen = False
            while thread.is_alive() and time.monotonic() < deadline:
                if _waiting_on_the_lock(engine):
                    seen = True
                    break
                time.sleep(0.01)
            assert seen, f"migrate did not wait for the lock: {results or errors}"
            assert results == []
            holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
            holder.commit()
        thread.join(timeout=30)
        assert not thread.is_alive(), "migrate is hanging"
        assert errors == []
        assert results == [Migrated(before=None, head=HEAD)]
    finally:
        engine.dispose()


@pytest.mark.db
def test_migrate_holds_the_lock_until_its_upgrade_has_committed(empty_dsn: str) -> None:
    """Two `migrate` wait behind the test's lock and are let go together:
    exactly one migrates, and the other finds the schema up to date.

    The test above shows that `migrate` waits for a lock somebody holds, and
    not that `migrate` holds it long enough. A lock released before the
    upgrade commits lets the second read the empty revision as well and run
    the same DDL again, which is what the lock exists to prevent."""
    engine = create_engine(empty_dsn)
    results: list[Migrated] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            results.append(migrate(empty_dsn))
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=run) for _ in range(2)]
    try:
        with engine.connect() as holder:
            holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            for thread in threads:
                thread.start()
            deadline = time.monotonic() + 10
            while _waiting_on_the_lock(engine) < 2:
                assert time.monotonic() < deadline, f"not both waited: {results or errors}"
                time.sleep(0.01)
            holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
            holder.commit()
        for thread in threads:
            thread.join(timeout=30)
        assert not any(thread.is_alive() for thread in threads), "migrate is hanging"
        assert errors == []
        assert sorted(results, key=lambda result: result.before or "") == [
            Migrated(before=None, head=HEAD),
            Migrated(before=HEAD, head=HEAD),
        ]
    finally:
        engine.dispose()


@pytest.mark.db
def test_migrate_refuses_a_revision_it_does_not_know(empty_dsn: str) -> None:
    """A database that an older package meets after a newer one migrated it.
    Raw SQL, as the forgery tests do."""
    migrate(empty_dsn)
    engine = create_engine(empty_dsn)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '9999_future'"))
    finally:
        engine.dispose()
    with pytest.raises(UnknownRevision) as caught:
        migrate(empty_dsn)
    assert str(caught.value) == (
        "the database is at revision 9999_future, which this version of previously "
        f"does not know; it knows revisions up to {HEAD}"
    )


@pytest.mark.db
def test_migrate_takes_a_password_with_a_percent_sign(empty_dsn: str) -> None:
    """A password with a character a URL has to escape arrives percent-encoded
    in the connection string. Alembic's configuration reads `%` as the start
    of an interpolation, so the string has to reach it escaped.

    Measured on 2026-10-05 without the escaping: `ValueError: invalid
    interpolation syntax`, a traceback whose message quoted the connection
    string, password included. Every character of the container's password is
    encoded here, so the string carries `%` and still names the same
    password."""
    url = make_url(empty_dsn)
    assert url.password is not None
    encoded = "".join(f"%{byte:02X}" for byte in str(url.password).encode())
    dsn = empty_dsn.replace(f":{url.password}@", f":{encoded}@", 1)
    assert "%" in dsn
    assert migrate(dsn) == Migrated(before=None, head=HEAD)


@pytest.mark.db
def test_cli_migrate_prints_one_line_each_way(
    empty_dsn: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PREVIOUSLY_DSN", empty_dsn)
    assert main(["migrate"]) == 0
    assert capsys.readouterr() == (f"migrated: (empty) -> {HEAD}\n", "")
    assert main(["migrate"]) == 0
    assert capsys.readouterr() == (f"up to date: {HEAD}\n", "")


@pytest.mark.db
def test_cli_migrate_names_no_password_and_gives_one_sentence(
    empty_dsn: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrong password: exit code 2, one line on standard error, the
    password nowhere — and the same sentence `log` gives for the same
    string, because both go through the one translation in `storage`. The
    wrong password is drawn at run time, so that no output can hold it by
    coincidence."""
    secret = f"wrong-{secrets.token_hex(8)}"
    wrong = make_url(empty_dsn).set(password=secret).render_as_string(hide_password=False)
    monkeypatch.setenv("PREVIOUSLY_DSN", wrong)
    assert main(["migrate"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 1, err
    assert err.startswith("Error: ")
    assert secret not in err
    assert main(["log"]) == 2
    assert capsys.readouterr() == ("", err)


@pytest.mark.db
def test_cli_migrate_as_a_role_that_cannot_read_the_revision_gives_one_sentence(
    role: Role,
    empty_dsn: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The owner migrates, and then a role without `SELECT` on
    `alembic_version` runs `migrate`: one sentence with the database's reason,
    exit code 2, and the lock gone afterwards.

    Measured on 2026-10-05 with the lock taken inside a transaction: the read
    aborted the transaction, the unlock in `finally` failed on the aborted
    transaction, and its `InFailedSqlTransaction` came out as a traceback with
    exit code 1, hiding the refusal."""
    migrate(empty_dsn)
    monkeypatch.setenv("PREVIOUSLY_DSN", role.on(empty_dsn))
    assert main(["migrate"]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the database refused the migration to {HEAD}: "
        "permission denied for table alembic_version\n",
    )
    assert _no_lock_left(empty_dsn)


@pytest.mark.db
def test_cli_migrate_as_a_role_that_cannot_create_names_the_reason(
    role: Role,
    empty_dsn: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A role that may not create a table in `public`, which since
    PostgreSQL 15 is every role but the database's owner, gets the
    database's reason, not the advice to run the command it just ran.

    Measured on 2026-10-05 before `MigrationFailed`: "Error: database schema
    incomplete — `uv run alembic upgrade head` has not run yet"."""
    monkeypatch.setenv("PREVIOUSLY_DSN", role.on(empty_dsn))
    assert main(["migrate"]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the database refused the migration to {HEAD}: "
        "permission denied for schema public\n",
    )
    assert _no_lock_left(empty_dsn)


@pytest.mark.db
def test_cli_migrate_translates_a_failure_on_alembics_own_connection(
    role: Role,
    empty_dsn: str,
    engine: Engine,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`command.upgrade` opens a connection of its own through `env.py`. A
    role allowed one connection gets the lock connection and not that one,
    and the failure ends as one sentence with exit code 2, without the
    password, because the upgrade runs inside the translation of the lock
    connection."""
    with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        conn.execute(text(f"ALTER ROLE {role.name} CONNECTION LIMIT 1"))
    monkeypatch.setenv("PREVIOUSLY_DSN", role.on(empty_dsn))
    assert main(["migrate"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 1, err
    assert err.startswith("Error: database server at ")
    assert role.password not in err
