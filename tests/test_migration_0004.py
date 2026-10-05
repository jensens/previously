# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The way down from `0004_event_blob`, in a container of its own, for the
reason `tests/test_migration_0003.py` gives."""

from alembic import command
from alembic.config import Config
from alembic.util import CommandError
from sqlalchemy import create_engine
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

import pytest


@pytest.mark.db
def test_the_downgrade_refuses_once_the_register_names_a_blob() -> None:
    """On an empty register the way down is open; with one row it refuses
    with a sentence, and the database stays at `0004_event_blob` with the row
    in place ({ref}`blobs`)."""
    with PostgresContainer("postgres:17", driver="psycopg") as container:
        engine = create_engine(container.get_connection_url())
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", container.get_connection_url())
        try:
            command.upgrade(config, "0004_event_blob")
            command.downgrade(config, "0003_hash_version_2")
            command.upgrade(config, "0004_event_blob")

            with engine.begin() as c:
                c.execute(
                    text(
                        "INSERT INTO event (id, kind, recorded_at, occurred_at, prev_hash, "
                        "hash, payload_hash, units_hash, payload) VALUES "
                        "(1, 'observation', now(), now(), NULL, :h, :p, :u, '{}'::jsonb)"
                    ),
                    {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x03" * 32},
                )
                c.execute(
                    text("INSERT INTO event_blob (event_id, sha256) VALUES (1, :s)"),
                    {"s": b"\x04" * 32},
                )
            with pytest.raises(CommandError) as caught:
                command.downgrade(config, "0003_hash_version_2")
            assert str(caught.value) == (
                "refusing to downgrade below 0004_event_blob: the register names blobs, "
                "and without it nothing says which events use them"
            )

            with engine.connect() as c:
                revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                rows = c.execute(text("SELECT count(*) FROM event_blob")).scalar_one()
            assert revision == "0004_event_blob"
            assert rows == 1
        finally:
            engine.dispose()
