# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The write path every action takes."""

from datetime import datetime
from datetime import UTC
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import KNOWN_ACTIONS
from previously.core.action import MODEL_CALL
from previously.core.action import POLICY
from previously.core.action import REDACTION
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text

import pytest


NOW = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)


def test_the_known_actions_are_the_three_names() -> None:
    assert {REDACTION, POLICY, MODEL_CALL} == KNOWN_ACTIONS
    assert (REDACTION, POLICY, MODEL_CALL) == ("redaction", "policy", "model_call")


@pytest.mark.db
def test_an_action_is_written_without_a_key_at_the_time_it_was_recorded(db: Engine) -> None:
    storage = PostgresStorage(db)
    units = (RawUnit(seq=1, content="first"), RawUnit(seq=2, content="second"))
    event_id = append_action(storage, {"action": MODEL_CALL, "task": "t"}, units, recorded_at=NOW)

    with storage.begin() as conn:
        (row,) = storage.read_by_kind(conn, "action")
        assert row.id == event_id
        assert row.occurred_at == NOW
        assert row.recorded_at == NOW
        assert row.payload == {"action": MODEL_CALL, "task": "t"}
        assert [(u.seq, u.content) for u in storage.units_by_event(conn, [event_id])[event_id]] == [
            (1, "first"),
            (2, "second"),
        ]
    with db.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM source_key")).scalar_one() == 0


@pytest.mark.db
def test_actions_chain_on_the_tip_and_verify_passes(db: Engine) -> None:
    storage = PostgresStorage(db)
    first = append_action(storage, {"action": POLICY}, (), recorded_at=NOW)
    second = append_action(storage, {"action": MODEL_CALL}, (), recorded_at=NOW)
    assert (first, second) == (1, 2)
    assert verify(storage) == []
