# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The built wheel carries what an installed Previously needs at run time.

An image installs Previously from PyPI, without a checkout beside it, so
whatever `previously migrate` reads has to be inside the wheel. Built in this
process with hatchling's own builder, the backend `pyproject.toml` names, so
that no subprocess and no suppression is needed for it.
"""

from hatchling.builders.wheel import WheelBuilder
from pathlib import Path

import zipfile


ROOT = Path(__file__).resolve().parent.parent
REVISIONS = sorted(path.name for path in (ROOT / "src/previously/migrations/versions").glob("*.py"))


def test_the_wheel_carries_every_migration(tmp_path: Path) -> None:
    builder = WheelBuilder(str(ROOT))
    (built,) = builder.build(directory=str(tmp_path), versions=["standard"])
    with zipfile.ZipFile(built) as wheel:
        names = set(wheel.namelist())
    assert "previously/migrations/env.py" in names
    assert "previously/migrations/script.py.mako" in names
    assert REVISIONS, "no revision found in the tree"
    for revision in REVISIONS:
        assert f"previously/migrations/versions/{revision}" in names
