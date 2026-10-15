# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The graph projection: versions by thread, and what each thread stands at

Revision ID: 0006_graph
Revises: 0005_watermark

A forward migration like `0002_projections`: two projection tables, and
nothing in the log is touched. They start empty, and the first catch-up of
the projection `graph` builds them from the log ({ref}`projections`).

The way back drops both and the state row of the projection with them. The
tables are derivable and disposable, so dropping them loses no truth; the
state row goes too, because one left behind would say the projection is
built up to an id when there is no table to hold it, and the next upgrade
would start from there with empty tables.
"""

from alembic import op

import sqlalchemy as sa


revision = "0006_graph"
down_revision = "0005_watermark"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "p_graph_version",
        sa.Column(
            "id", sa.BigInteger, sa.ForeignKey("event.id"), primary_key=True, autoincrement=False
        ),
        sa.Column("subject", sa.BigInteger, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("under", sa.BigInteger),
        sa.CheckConstraint(
            "kind IN ('entity','relation','rejection')", name="p_graph_version_kind_check"
        ),
    )
    op.create_index("p_graph_version_subject_idx", "p_graph_version", ["subject"])
    op.create_index(
        "p_graph_version_under_idx",
        "p_graph_version",
        ["under"],
        postgresql_where=sa.text("under IS NOT NULL"),
    )
    op.create_table(
        "p_graph_thread",
        sa.Column(
            "subject",
            sa.BigInteger,
            sa.ForeignKey("event.id"),
            primary_key=True,
            autoincrement=False,
        ),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("winner_id", sa.BigInteger, nullable=False),
        sa.Column("level", sa.Text, nullable=False),
        sa.Column("state", sa.Text, nullable=False),
        sa.Column("start_entity", sa.BigInteger),
        sa.Column("start_event", sa.BigInteger),
        sa.Column("start_units", sa.ARRAY(sa.Integer)),
        sa.Column("to_entity", sa.BigInteger),
        sa.Column("candidates", sa.ARRAY(sa.BigInteger)),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("pending", sa.Integer, nullable=False),
        sa.Column("objections", sa.Integer, nullable=False),
        sa.Column("question", sa.Boolean, nullable=False),
        sa.CheckConstraint("kind IN ('entity','relation')", name="p_graph_thread_kind_check"),
    )
    op.create_index("p_graph_thread_kind_type_idx", "p_graph_thread", ["kind", "type"])
    op.create_index("p_graph_thread_to_entity_idx", "p_graph_thread", ["to_entity"])
    op.create_index("p_graph_thread_start_event_idx", "p_graph_thread", ["start_event"])


def downgrade() -> None:
    op.drop_index("p_graph_thread_start_event_idx", table_name="p_graph_thread")
    op.drop_index("p_graph_thread_to_entity_idx", table_name="p_graph_thread")
    op.drop_index("p_graph_thread_kind_type_idx", table_name="p_graph_thread")
    op.drop_table("p_graph_thread")
    op.drop_index("p_graph_version_under_idx", table_name="p_graph_version")
    op.drop_index("p_graph_version_subject_idx", table_name="p_graph_version")
    op.drop_table("p_graph_version")
    op.execute(sa.text("DELETE FROM projection_state WHERE name = 'graph'"))
