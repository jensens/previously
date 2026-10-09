# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle shows observations, and only those ({ref}`projections`)."""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import ProjectionState
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import MODEL_CALL
from previously.core.append import append
from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.worker import catch_up
from previously.core.units import split_plaintext
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text

import pytest


NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)


def _observation() -> RawEvent:
    return RawEvent(
        source="email",
        external_id="m-1",
        occurred_at=NOW,
        evidence=Evidence.VERBATIM,
        units=split_plaintext("one\n\ntwo"),
        payload={"text": "one\n\ntwo"},
    )


def _rows(db: Engine) -> list[tuple[object, ...]]:
    with db.begin() as conn:
        return [
            tuple(r) for r in conn.execute(text("SELECT * FROM p_chronicle ORDER BY event_id, seq"))
        ]


def _write_both(storage: PostgresStorage) -> None:
    append(storage, [_observation()], recorded_at=NOW)
    append_action(
        storage,
        {"action": MODEL_CALL},
        (RawUnit(seq=1, content="the answer of a model"),),
        recorded_at=NOW,
    )


@pytest.mark.db
def test_an_action_with_units_is_not_in_the_chronicle_and_an_observation_is(db: Engine) -> None:
    storage = PostgresStorage(db)
    _write_both(storage)
    catch_up(storage, storage, CHRONICLE)
    rows = _rows(db)
    assert [(r[0], r[1]) for r in rows] == [(1, 1), (1, 2)]
    assert {r[4] for r in rows} == {"observation"}


@pytest.mark.db
def test_the_upgrade_to_version_3_rebuilds_and_ends_as_a_fresh_build(db: Engine) -> None:
    """A table that version 2 built holds the rows of an action's units. The
    state row says version 2, the rows are put in by hand the way version 2
    derived them, and the first catch-up of version 3 rebuilds the table."""
    storage = PostgresStorage(db)
    _write_both(storage)
    catch_up(storage, storage, CHRONICLE)
    fresh = _rows(db)
    with db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO p_chronicle (event_id, seq, content, occurred_at, kind) "
                "VALUES (2, 1, 'the answer of a model', :t, 'action')"
            ),
            {"t": NOW},
        )
    with storage.begin() as conn:
        storage.set_projection_state(conn, ProjectionState("chronicle", 2, 2, NOW))
    assert len(_rows(db)) == len(fresh) + 1

    outcome = catch_up(storage, storage, CHRONICLE)
    assert outcome.rebuilt_from == 2
    assert _rows(db) == fresh
