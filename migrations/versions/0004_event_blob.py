# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The blob register: which event names which blob

Revision ID: 0004_event_blob
Revises: 0003_hash_version_2

An ordinary forward migration: a new table, and nothing already in the log
is touched. No event written before it names a blob, so the register starts
empty and is complete ({ref}`blobs`).

The way back refuses once the table holds a row. The references stay in the
payloads, but without the register nothing answers which events use a blob,
and `previously blob get` asks exactly that before it fetches one.
"""

from alembic import op
from alembic.util import CommandError

import sqlalchemy as sa


revision = "0004_event_blob"
down_revision = "0003_hash_version_2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_blob",
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.Column("sha256", sa.LargeBinary, nullable=False),
        sa.PrimaryKeyConstraint("event_id", "sha256"),
        sa.CheckConstraint("octet_length(sha256) = 32", name="event_blob_sha256_check"),
    )
    op.create_index("event_blob_sha256_idx", "event_blob", ["sha256"])


def downgrade() -> None:
    # Checked before anything is dropped, for the reason `0003_hash_version_2`
    # gives: the run is one transaction, and the error leaves the database
    # where the command found it.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM event_blob)")).scalar():
        raise CommandError(
            "refusing to downgrade below 0004_event_blob: the register names blobs, "
            "and without it nothing says which events use them"
        )
    op.drop_index("event_blob_sha256_idx", table_name="event_blob")
    op.drop_table("event_blob")
