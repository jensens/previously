# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests `migrations.dsn.resolve_dsn` without a container.

No `@pytest.mark.db`: `resolve_dsn` depends only on
`alembic.config.Config` and `os.environ`, not on a running database. Not on
`alembic.context` either — unlike `env.py` itself, which reads
`context.config` at module level already and is therefore not importable in
isolation outside a running migration (see the docstring of
`migrations/dsn.py`). That is precisely why the resolution lives in a module
of its own.
"""

from alembic.config import Config
from migrations.dsn import ENV_VAR
from migrations.dsn import resolve_dsn

import pytest


def test_with_neither_it_raises_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    with pytest.raises(RuntimeError, match=ENV_VAR):
        resolve_dsn(Config())


def test_the_environment_variable_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "postgresql+psycopg://from/the-environment")
    assert resolve_dsn(Config()) == "postgresql+psycopg://from/the-environment"


def test_a_set_option_wins_over_the_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`tests/conftest.py` sets `sqlalchemy.url` programmatically for the test
    container — that must not be overwritten by a `PREVIOUSLY_DSN` that
    happens to be set."""
    monkeypatch.setenv(ENV_VAR, "postgresql+psycopg://from/the-environment")
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://programmatically/set")
    assert resolve_dsn(config) == "postgresql+psycopg://programmatically/set"
