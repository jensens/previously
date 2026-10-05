# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Log, units, idempotency key

Revision ID: 0001_log
Revises:

Correction K1 changes this revision instead of laying a `0002` down beside
it. The reason: a forward migration onto the new hash range is **impossible
in principle**. `units_hash` could be recomputed for existing rows, but the
event hash could not — recomputing it means rewriting the chain, and that is
exactly what an append-only log must not be able to do. A database with data
therefore has to be rebuilt (`dropdb`, or a fresh container); a `0002` that
feigned completeness would be a lie in the repository. That is free today,
because there is no production data, and impossible from the first real write
on.

Correction K-1 of fix round 1 (`event_payload_object_check`) is added here as
well, and the reason is **not** the same, so it is stated separately:
`ALTER TABLE … ADD CONSTRAINT` would be a perfectly ordinary forward
migration. It goes in here because this revision has never been shipped — the
only databases that carry it are test containers and development copies, and
every one of them has to be rebuilt for correction K1 anyway. A `0002` beside
it would suggest a migration path for a tree that has none, and would make
`0001_log` the revision that creates a table the specification does not allow.
From the first real write on, this would have to be a `0002`.
"""

from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

import sqlalchemy as sa


revision = "0001_log"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("prev_hash", sa.LargeBinary),
        sa.Column("hash", sa.LargeBinary, nullable=False),
        sa.Column("payload_hash", sa.LargeBinary, nullable=False),
        sa.Column("units_hash", sa.LargeBinary, nullable=False),
        sa.Column("payload", JSONB),
        sa.CheckConstraint("kind IN ('observation','assertion','action')", name="event_kind_check"),
        # Correction K-1: SQL `NULL` is the tombstone, JSON `null` must not be
        # able to pass for one — psycopg turns both into Python `None`, so
        # `verify` would take the forged row for a tombstone and skip its
        # payload, while `WHERE payload IS NULL` would not list it. The
        # constraint restricts nothing the contract allows: the payload range
        # is a JSON object ({ref}`payload-range`). See `storage/schema.py`
        # for the full reasoning.
        sa.CheckConstraint(
            "payload IS NULL OR jsonb_typeof(payload) = 'object'",
            name="event_payload_object_check",
        ),
    )
    op.create_index("event_occurred_idx", "event", ["occurred_at"])
    op.create_index("event_kind_occurred_idx", "event", ["kind", "occurred_at"])
    op.create_index("event_hash_idx", "event", ["hash"], unique=True)

    # NULLS NOT DISTINCT is not optional: without it several NULL count as
    # distinct, and every process could write its own genesis entry — that is,
    # precisely the branching the index is meant to prevent.
    op.create_index(
        "event_prev_hash_idx",
        "event",
        ["prev_hash"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    op.create_table(
        "unit",
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.Column("speaker", sa.Text),
        sa.PrimaryKeyConstraint("event_id", "seq"),
        sa.CheckConstraint("seq >= 1", name="unit_seq_check"),
    )

    op.create_table(
        "source_key",
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("external_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.PrimaryKeyConstraint("source", "external_id"),
        # At most one source attribution per event: the event hash covers it
        # and needs uniqueness for that ({ref}`hash-chain`).
        sa.UniqueConstraint("event_id", name="source_key_event_id_key"),
    )


def downgrade() -> None:
    op.drop_table("source_key")
    op.drop_table("unit")
    op.drop_table("event")
