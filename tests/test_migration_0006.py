# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The way down from `0006_graph` and up again, in a container of its own,
for the reason `tests/test_migration_0003.py` gives."""

from alembic import command
from alembic.config import Config
from database import postgres
from datetime import datetime
from datetime import UTC
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.append import append
from previously.core.assertion import DIRECT
from previously.core.assertion import OPERATOR
from previously.core.assertion import Source
from previously.core.classes import read_classes
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import SOURCES
from previously.core.graph_write import read_graph
from previously.core.graph_write import write_claims
from previously.core.projection import GRAPH
from previously.core.projection import PROJECTIONS
from previously.core.projection.graph import summary
from previously.core.projection.worker import catch_up
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import parse_file
from previously.storage.postgres import PostgresStorage
from sqlalchemy import create_engine
from sqlalchemy import text

import pytest


NOW = datetime(2026, 10, 15, 9, 0, 0, tzinfo=UTC)


def _a_project(storage: PostgresStorage) -> int:
    """A mail and the operator's project resting on it, with the vocabulary
    between them."""
    append(
        storage,
        [
            RawEvent(
                source="email",
                external_id="m1",
                occurred_at=NOW,
                evidence=Evidence.VERBATIM,
                units=(RawUnit(1, "One."),),
                payload={"text": "One."},
            )
        ],
        recorded_at=NOW,
    )
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=NOW)
    project = Claim(
        ENTITY, OPERATOR, DIRECT, SOURCES, (Source(1, None),), None, None, None, None, None,
        None, None, EntityBody("project", "de", {"name": "XZ"}, ACTIVE),
    )  # fmt: skip
    (project_id,) = write_claims(storage, storage, [project], recorded_at=NOW).ids
    return project_id


@pytest.mark.db
def test_the_way_down_takes_the_state_row_and_the_way_up_builds_the_graph_again() -> None:
    """Down to `0005_watermark` drops both tables and the state row of
    `graph`, so that the way up again finds no bookmark and the first
    catch-up builds the projection from the first event, ending where the
    fold does. Measured red with the `DELETE` taken out of the downgrade:
    the state row of `graph` survived the way down, and with that check
    taken out as well, the catch-up after the way up called the empty
    tables up to date (`rebuilt_from` None, no event read)."""
    with postgres() as container:
        engine = create_engine(container.get_connection_url())
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", container.get_connection_url())
        try:
            command.upgrade(config, "head")
            storage = PostgresStorage(engine)
            project = _a_project(storage)
            for projection in PROJECTIONS:
                catch_up(storage, storage, projection, rebuild=True)

            command.downgrade(config, "0005_watermark")
            with engine.connect() as c:
                assert c.execute(text("SELECT to_regclass('p_graph_thread')")).scalar() is None
                assert c.execute(text("SELECT to_regclass('p_graph_version')")).scalar() is None
                names = c.execute(text("SELECT name FROM projection_state ORDER BY name"))
                assert list(names.scalars()) == ["chronicle", "source-stats"]

            command.upgrade(config, "head")
            outcome = catch_up(storage, storage, GRAPH, rebuild=True)
            assert (outcome.rebuilt_from, outcome.events) == (0, outcome.up_to_id)
            with storage.begin() as conn:
                rows = storage.read_graph_threads(conn)
                graph = read_graph(storage, conn)
                classes = read_classes(storage, conn).states
            folded = [summary(thread, classes) for thread in graph.threads.values()]
            assert [row.subject for row in rows] == [project]
            assert rows == folded
        finally:
            engine.dispose()
