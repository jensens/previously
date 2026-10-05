# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hash format version 2: version, salts and unit digests

Revision ID: 0003_hash_version_2
Revises: 0002_projections

An ordinary forward migration, and correction K1 was not one. K1 widened what
the event hash covers, so every existing hash would have had to be computed
again, and computing the hashes again means rewriting the chain; it went into
`0001_log` while nothing had reached `main`. Here no hash is computed again:
`hash_version` gets `DEFAULT 1`, and that writes down for every existing row
what already holds, because every row written before this migration is
version 1. The salts and unit digests stay NULL on those rows, which is what
version 1 has ({ref}`hash-version-2`).

The way back refuses once it would lose something. Without its salts an
event written in version 2 can no longer be verified, and a unit without
content cannot be made `NOT NULL` again.
"""

from alembic import op
from alembic.util import CommandError

import sqlalchemy as sa


revision = "0003_hash_version_2"
down_revision = "0002_projections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event",
        sa.Column("hash_version", sa.SmallInteger, nullable=False, server_default=sa.text("1")),
    )
    op.add_column("event", sa.Column("payload_salt", sa.LargeBinary))
    op.create_check_constraint(
        "event_payload_salt_check", "event", "payload IS NOT NULL OR payload_salt IS NULL"
    )
    op.alter_column("unit", "content", existing_type=sa.Text, nullable=True)
    op.add_column("unit", sa.Column("digest", sa.LargeBinary))
    op.add_column("unit", sa.Column("salt", sa.LargeBinary))
    op.create_check_constraint(
        "unit_tombstone_check",
        "unit",
        "content IS NOT NULL OR "
        "(salt IS NULL AND speaker IS NULL AND start_ms IS NULL AND end_ms IS NULL)",
    )


def downgrade() -> None:
    # Checked before anything is dropped: `migrations/env.py` runs a whole
    # `alembic downgrade` in one transaction, and an error raised here rolls
    # it back and leaves the database at the revision the command started
    # from — this one, or a later one whose downgrade had already run.
    # `CommandError` is what the `alembic` command line prints as one line
    # instead of a traceback.
    bind = op.get_bind()
    reasons: list[str] = []
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM event WHERE hash_version = 2)")).scalar():
        reasons.append(
            "the log holds events in hash format 2, which cannot be verified "
            "without the salts this would drop"
        )
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM unit WHERE content IS NULL)")).scalar():
        reasons.append("the log holds units without content, which cannot be NOT NULL again")
    if reasons:
        raise CommandError("refusing to downgrade below 0003_hash_version_2: " + "; ".join(reasons))

    op.drop_constraint("unit_tombstone_check", "unit", type_="check")
    op.drop_column("unit", "salt")
    op.drop_column("unit", "digest")
    op.alter_column("unit", "content", existing_type=sa.Text, nullable=False)
    op.drop_constraint("event_payload_salt_check", "event", type_="check")
    op.drop_column("event", "payload_salt")
    op.drop_column("event", "hash_version")
