# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolution of the database URL for Alembic migrations.

A module of its own instead of living in `env.py`, for a measured reason:
`env.py` reads `context.config` at module level — that is the usual alembic
layout, but `context` is a proxy that carries something only inside a running
`EnvironmentContext` (that is, during a real Alembic run). A bare
`import previously.migrations.env` outside such a run therefore always fails with
`AttributeError: module 'alembic.context' has no attribute 'config'` —
independently of any change to this file. This resolution depends only on
`alembic.config.Config` and the environment, not on `context`, and is
therefore testable without a container or a running migration.
"""

from typing import TYPE_CHECKING

import os


if TYPE_CHECKING:
    from alembic.config import Config

# The same name as in previously.cli._storage() — one environment variable,
# one convention, not two.
ENV_VAR = "PREVIOUSLY_DSN"


def resolve_dsn(config: Config) -> str:
    """The database URL for a migration run.

    The order is explicitly this one: an already set `sqlalchemy.url`
    **wins** — `tests/conftest.py` relies on that, setting it
    programmatically to the test container before it migrates.
    `PREVIOUSLY_DSN` is the fallback for the human at the command line
    ({ref}`configuration-reference`) who does not want to touch
    `alembic.ini`.
    """
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    url = os.environ.get(ENV_VAR)
    if url:
        return url
    raise RuntimeError(
        "No database URL found: neither is `sqlalchemy.url` set in "
        f"alembic.ini, nor is {ENV_VAR} set in the environment. "
        f"Either `export {ENV_VAR}=postgresql+psycopg://…` before the call, "
        'or programmatically via `config.set_main_option("sqlalchemy.url", …)` '
        "before the migration run (the way tests/conftest.py does it for the "
        "test container)."
    )
