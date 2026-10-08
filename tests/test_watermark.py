# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The watermark: how far a connector has read, kept beside the log.

These are storage tests, in the form of `tests/test_projection_store.py`: what
goes in comes back out, one row per connector, and a second write replaces the
first. What a connector does with its watermark is the connector's own test.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from previously.contract.types import Watermark
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from previously.contract.store import WatermarkStore


NOW = datetime(2026, 10, 6, 9, 30, 0, tzinfo=UTC)


@pytest.mark.db
def test_a_connector_without_a_watermark_reads_none(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        assert storage.watermark(c, "imap") is None


@pytest.mark.db
def test_a_watermark_round_trips_as_a_plain_dict(db: Engine) -> None:
    storage = PostgresStorage(db)
    mark = Watermark("imap", {"uidvalidity": "17", "uid": "4711"}, NOW)
    with storage.begin() as c:
        storage.set_watermark(c, mark)
    with storage.begin() as c:
        read = storage.watermark(c, "imap")
    assert read == mark
    assert read is not None
    assert type(read.position) is dict


@pytest.mark.db
def test_a_second_write_replaces_the_first(db: Engine) -> None:
    storage = PostgresStorage(db)
    later = NOW + timedelta(hours=1)
    with storage.begin() as c:
        storage.set_watermark(c, Watermark("imap", {"uidvalidity": "17", "uid": "1"}, NOW))
        storage.set_watermark(c, Watermark("imap", {"uid": "2"}, later))
        read = storage.watermark(c, "imap")
        rows = c.execute(text("SELECT count(*) FROM watermark")).scalar_one()
    # The position is replaced as a whole, not merged key by key: `uidvalidity`
    # of the first write is gone.
    assert read == Watermark("imap", {"uid": "2"}, later)
    assert rows == 1


@pytest.mark.db
def test_each_connector_keeps_its_own_watermark(db: Engine) -> None:
    storage = PostgresStorage(db)
    with storage.begin() as c:
        storage.set_watermark(c, Watermark("imap", {"uid": "5"}, NOW))
        storage.set_watermark(c, Watermark("other", {"offset": "9"}, NOW))
        assert storage.watermark(c, "imap") == Watermark("imap", {"uid": "5"}, NOW)
        assert storage.watermark(c, "other") == Watermark("other", {"offset": "9"}, NOW)


@pytest.mark.db
def test_a_watermark_rolls_back_with_its_transaction(db: Engine) -> None:
    """The watermark is written in the transaction of the events it covers, so
    that the two stand or fall together; this is the half of that which
    belongs to the store."""
    storage = PostgresStorage(db)

    class Abort(Exception):
        pass

    with pytest.raises(Abort), storage.begin() as c:
        storage.set_watermark(c, Watermark("imap", {"uid": "5"}, NOW))
        raise Abort
    with storage.begin() as c:
        assert storage.watermark(c, "imap") is None


@pytest.mark.db
def test_a_moment_in_another_zone_reads_back_as_the_same_instant(db: Engine) -> None:
    storage = PostgresStorage(db)
    moment = datetime(2026, 10, 6, 11, 30, 0, tzinfo=timezone(timedelta(hours=2)))
    with storage.begin() as c:
        storage.set_watermark(c, Watermark("imap", {}, moment))
        read = storage.watermark(c, "imap")
    assert read is not None
    # 11:30 at +02:00 is the instant `NOW` names.
    assert read.set_at == NOW


@pytest.mark.db
def test_a_moment_without_a_zone_is_refused(db: Engine) -> None:
    """Local time would be meant, and PostgreSQL would read it in the session's
    zone: the sentence of `core.hashing.iso_utc`, said by the store. The naive
    moment comes from `fromisoformat`, which needs no suppression where the
    constructor would."""
    storage = PostgresStorage(db)
    naive = datetime.fromisoformat("2026-10-06T09:30:00")
    with pytest.raises(ValueError, match="no time zone"), storage.begin() as c:
        storage.set_watermark(c, Watermark("imap", {"uid": "1"}, naive))
    with storage.begin() as c:
        assert storage.watermark(c, "imap") is None


def test_postgres_storage_satisfies_the_watermark_protocol() -> None:
    """The protocol, in the form of the projection test: pyright rejects the
    assignment if a method is missing; the `isinstance` gives the test a body."""
    from sqlalchemy import Connection
    from sqlalchemy import create_engine

    storage = PostgresStorage(create_engine("postgresql+psycopg://x:y@localhost/z"))
    marks: WatermarkStore[Connection] = storage
    assert isinstance(marks, PostgresStorage)
