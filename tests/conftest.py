# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test setup: real PostgreSQL in a container, migrations run against the container."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator


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

    All three tables stand in one statement, and it is not the order of the
    names that makes this compatible with the foreign keys: PostgreSQL does
    not check foreign keys against each other within a single joint TRUNCATE.
    """
    with engine.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    yield engine


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
