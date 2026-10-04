# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test setup: real PostgreSQL in a container, migrations run against the container."""

from alembic import command
from alembic.config import Config
from previously.storage.schema import metadata
from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator

# Every table of the schema in one statement, derived from `metadata` rather
# than typed out: the same list stood in seven places before, and a seventh
# table would have meant seven edits with nothing to catch the one that was
# forgotten. `sorted_tables` comes parents first, so reversed it is children
# first — which reads the way one expects even though the order does not
# matter here, for the reason the `db` fixture gives below.
TRUNCATE_ALL = "TRUNCATE " + ", ".join(table.name for table in reversed(metadata.sorted_tables))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:17", driver="psycopg") as container:
        db_engine = create_engine(container.get_connection_url())
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", container.get_connection_url())
        command.upgrade(config, "head")
        yield db_engine
        db_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Engine]:
    """An empty schema per test. TRUNCATE instead of re-creating: faster and sufficient.

    All six tables stand in one statement, and it is not the order of the
    names that makes this compatible with the foreign keys: PostgreSQL does
    not check foreign keys against each other within a single joint TRUNCATE.
    """
    with engine.begin() as c:
        c.execute(text(TRUNCATE_ALL))
    yield engine


@pytest.fixture
def truncate_statement() -> str:
    """The statement from `TRUNCATE_ALL`, for the tests that need it themselves.

    A property test takes its fixtures once and then runs many examples
    against them, so it has to empty the schema at the head of every example
    — which is where the six copies of the table list came from.

    A fixture and not a helper imported from this file: `from conftest import
    TRUNCATE_ALL` works only because pytest puts the test directory on
    `sys.path`, and a shared value that a test reaches through the fixture
    protocol does not depend on that.

    A `str` and not a callable that does the emptying, for a reason measured
    on 2026-10-04: hypothesis reads the signature of every `@given` function
    with `eval_str`, so an annotation of `Callable[[], None]` imported under
    `TYPE_CHECKING` raised `NameError: name 'Callable' is not defined` at
    collection time, in all six places. A `str` annotation needs no import,
    and no rule has to be loosened to keep one.
    """
    return TRUNCATE_ALL


@pytest.fixture(scope="session")
def unmigrated_engine() -> Iterator[Engine]:
    """An own container **without** `alembic upgrade head` (review finding W2,
    case 3: `log` or `append` run against a database on which the migration
    has not run yet, and are supposed to see `ProgrammingError` →
    `MigrationPending` for that, not a stack trace). Shared session-wide:
    every access to it is supposed to fail, so there is nothing one test could
    spoil for the next.
    """
    with PostgresContainer("postgres:17", driver="psycopg") as container:
        yield create_engine(container.get_connection_url())
