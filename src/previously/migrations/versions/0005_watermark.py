# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The watermark: how far each connector has read

Revision ID: 0005_watermark
Revises: 0004_event_blob

An ordinary forward migration: a new table, and nothing already in the log is
touched. No connector has run before it, so the table starts empty and
complete.

The way back refuses once the table holds a row. The log is untouched by
dropping it, but a connector without its watermark reads its source from the
start, and everything it has taken in already is fetched again.
"""

from alembic import op
from alembic.util import CommandError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TIMESTAMP

import sqlalchemy as sa


revision = "0005_watermark"
down_revision = "0004_event_blob"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watermark",
        sa.Column("connector", sa.Text, primary_key=True),
        sa.Column("position", JSONB, nullable=False),
        sa.Column("set_at", TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Checked before anything is dropped, for the reason `0003_hash_version_2`
    # gives: the run is one transaction, and the error leaves the database
    # where the command found it.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM watermark)")).scalar():
        raise CommandError(
            "refusing to downgrade below 0005_watermark: the table says how far "
            "each connector has read, and without it the next run reads from the start"
        )
    op.drop_table("watermark")
