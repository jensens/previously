# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The tables as SQLAlchemy Core. No ORM (architecture §10.1, frozen design record)."""

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TIMESTAMP


metadata = MetaData()

event = Table(
    "event",
    metadata,
    # The id comes from the predecessor, not out of a sequence: a sequence
    # guarantees no commit order, and then id order diverges from chain order
    # ({ref}`hash-chain`).
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("kind", Text, nullable=False),
    Column("recorded_at", TIMESTAMP(timezone=True), nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("prev_hash", LargeBinary),
    Column("hash", LargeBinary, nullable=False),
    Column("payload_hash", LargeBinary, nullable=False),
    # Mirrors payload_hash: the digest stands in the row, the content in
    # `unit`. That makes the event hash cover the units without containing
    # them — and the erasure seam stays open for them ({ref}`tombstone-seam`).
    Column("units_hash", LargeBinary, nullable=False),
    # NULL = tombstone after an erasure. payload_hash stays, the chain holds.
    Column("payload", JSONB),
    CheckConstraint("kind IN ('observation','assertion','action')", name="event_kind_check"),
    # Correction K-1: SQL `NULL` is the tombstone, JSON `null` must not be
    # able to pass for one.
    #
    # psycopg turns **both** into Python `None`, so `row.payload is None` in
    # `core/verify.py` cannot tell them apart. Measured against a real
    # PostgreSQL 17: `UPDATE event SET payload = 'null'::jsonb` left
    # `verify() -> []`, because the check took the row for a tombstone and
    # skipped its payload — while `SELECT id FROM event WHERE payload IS NULL`
    # did **not** list the row. Content silently and permanently erased for
    # the check, and invisible to every piece of bookkeeping that asks the
    # database rather than Python.
    #
    # This constraint **restricts nothing the contract allows.** The payload
    # range is `Mapping[str, object]`, that is a JSON object
    # ({ref}`payload-range`); a JSON array, a scalar or `null` were never
    # permissible there. The database only enforces what the specification
    # already presupposed.
    #
    # And that is the better half of it: the stage 1a specification
    # §3.4 (frozen design record) prescribes `payload IS NULL`, the code asks
    # `row.payload is None` — the two were never equivalent. With this
    # constraint they are, because JSON `null` can no longer stand in the
    # column. The code is not being bent to fit the spec; the database is made
    # to enforce what the spec took for granted.
    #
    # The honest limit: *today* a forger gains nothing here that
    # `payload = NULL` would not also give. The sharpness is that the
    # disclosed limit ({ref}`tombstone-seam`) and the redemption it
    # announces — a tombstone without an accompanying erasure event becomes a
    # finding — do not catch this case, because it is no tombstone *in the
    # sense of the query*.
    CheckConstraint(
        "payload IS NULL OR jsonb_typeof(payload) = 'object'",
        name="event_payload_object_check",
    ),
)

Index("event_occurred_idx", event.c.occurred_at)
Index("event_kind_occurred_idx", event.c.kind, event.c.occurred_at)
Index("event_hash_idx", event.c.hash, unique=True)

# Together with event_pkey this carries the entire concurrency control for
# append ({ref}`concurrency`): no advisory lock, no FOR UPDATE, but two
# unique indexes decide which writer gets the chain position. The loser
# re-reads the tip and retries.
#
# NULLS NOT DISTINCT is not optional: without it several NULL count as
# distinct, and every process could write its own genesis entry
# (prev_hash IS NULL) — that is, precisely the branching this index is meant
# to prevent.
Index(
    "event_prev_hash_idx",
    event.c.prev_hash,
    unique=True,
    postgresql_nulls_not_distinct=True,
)

unit = Table(
    "unit",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("start_ms", Integer),
    Column("end_ms", Integer),
    Column("speaker", Text),
    PrimaryKeyConstraint("event_id", "seq"),
    CheckConstraint("seq >= 1", name="unit_seq_check"),
)

source_key = Table(
    "source_key",
    metadata,
    Column("source", Text, nullable=False),
    Column("external_id", Text, nullable=False),
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    PrimaryKeyConstraint("source", "external_id"),
    # At most one source attribution per event. Without this constraint
    # several (source, external_id) could point at the same event, and then it
    # would not be determined *which* source attribution belongs in the event
    # hash — the hash needs uniqueness ({ref}`hash-chain`). `append` writes
    # only one row per event anyway; the constraint writes down what already
    # holds instead of leaving it to the whim of future callers.
    UniqueConstraint("event_id", name="source_key_event_id_key"),
)
