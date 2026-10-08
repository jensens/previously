# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The way down from `0005_watermark`, in a container of its own, for the
reason `tests/test_migration_0003.py` gives."""

from alembic import command
from alembic.config import Config
from alembic.util import CommandError
from sqlalchemy import create_engine
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

import pytest


@pytest.mark.db
def test_the_downgrade_refuses_once_a_connector_has_a_watermark() -> None:
    """On an empty table the way down is open and takes the table with it;
    with one row it refuses with a sentence, and the database stays at
    `0005_watermark` with the row in place. Without the refusal the next run
    of the connector would find no watermark and read the whole folder again."""
    with PostgresContainer("postgres:17", driver="psycopg") as container:
        engine = create_engine(container.get_connection_url())
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", container.get_connection_url())
        try:
            command.upgrade(config, "0005_watermark")
            command.downgrade(config, "0004_event_blob")
            with engine.connect() as c:
                assert c.execute(text("SELECT to_regclass('watermark')")).scalar() is None
            command.upgrade(config, "0005_watermark")

            with engine.begin() as c:
                c.execute(
                    text(
                        "INSERT INTO watermark (connector, position, set_at) "
                        "VALUES ('imap', '{\"uid\": \"7\"}'::jsonb, now())"
                    )
                )
            with pytest.raises(CommandError) as caught:
                command.downgrade(config, "0004_event_blob")
            assert str(caught.value) == (
                "refusing to downgrade below 0005_watermark: the table says how far "
                "each connector has read, and without it the next run reads from the start"
            )

            with engine.connect() as c:
                revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                rows = c.execute(text("SELECT count(*) FROM watermark")).scalar_one()
            assert revision == "0005_watermark"
            assert rows == 1
        finally:
            engine.dispose()
