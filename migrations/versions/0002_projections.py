# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projections: state, chronicle, source statistics

Revision ID: 0002_projections
Revises: 0001_log

A forward migration, unlike the corrections folded into `0001_log`: nothing
here touches the log, so there is nothing a rebuild would have to redo. The
three tables are derivable and disposable ({ref}`projections`); dropping them
loses no truth, and `previously project` builds them again from the log.
"""

from alembic import op

import sqlalchemy as sa


revision = "0002_projections"
down_revision = "0001_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_state",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("up_to_id", sa.BigInteger, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        "p_chronicle",
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text),
        sa.Column("source", sa.Text),
        sa.Column("external_id", sa.Text),
        sa.Column("speaker", sa.Text),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.PrimaryKeyConstraint("event_id", "seq"),
    )
    op.create_index("p_chronicle_occurred_idx", "p_chronicle", ["occurred_at", "event_id", "seq"])
    op.create_table(
        "p_source_stats",
        sa.Column("source", sa.Text, primary_key=True),
        sa.Column("events", sa.BigInteger, nullable=False),
        sa.Column("units", sa.BigInteger, nullable=False),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("p_source_stats")
    op.drop_index("p_chronicle_occurred_idx", table_name="p_chronicle")
    op.drop_table("p_chronicle")
    op.drop_table("projection_state")
