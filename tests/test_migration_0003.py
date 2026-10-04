# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The way down from `0003_hash_version_2`, in a container of its own.

Its own container because this test downgrades, and the session database the
other tests share must never stand below `head`.
"""

from alembic import command
from alembic.config import Config
from alembic.util import CommandError
from datetime import datetime
from datetime import UTC
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.units import split_plaintext
from previously.storage.postgres import PostgresStorage
from sqlalchemy import create_engine
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

import pytest


NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)


@pytest.mark.db
def test_the_downgrade_refuses_once_version_2_is_written() -> None:
    """On an empty database the way down is open; with one event that
    `append` wrote in version 2 it refuses with a sentence, and the database
    stays at `head`."""
    with PostgresContainer("postgres:17", driver="psycopg") as container:
        engine = create_engine(container.get_connection_url())
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", container.get_connection_url())
        try:
            command.upgrade(config, "head")
            command.downgrade(config, "0002_projections")
            command.upgrade(config, "head")

            append(
                PostgresStorage(engine),
                [
                    RawEvent(
                        source="cli",
                        external_id="a",
                        occurred_at=NOW,
                        evidence=Evidence.RECOLLECTION,
                        units=split_plaintext("Hello"),
                        payload={},
                    )
                ],
                recorded_at=NOW,
            )
            with pytest.raises(CommandError) as caught:
                command.downgrade(config, "0002_projections")
            assert str(caught.value) == (
                "refusing to downgrade below 0003_hash_version_2: the log holds events in "
                "hash format 2, which cannot be verified without the salts this would drop"
            )

            with engine.connect() as c:
                revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                salts = c.execute(text("SELECT count(payload_salt) FROM event")).scalar_one()
            assert revision == "0003_hash_version_2"
            assert salts == 1
        finally:
            engine.dispose()
