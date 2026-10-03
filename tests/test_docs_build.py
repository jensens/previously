# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The documentation build is a gate, so its scope is a gate too."""

import pathlib
import pytest


DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


def test_sphinx_excludes_the_frozen_design_records() -> None:
    """Without this exclusion Sphinx builds 2000 lines of German and
    publishes the plans. The exclusion is load-bearing, so it is pinned."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    assert '"superpowers/**"' in conf


@pytest.mark.parametrize("quadrant", ["tutorials", "how-to", "reference", "explanation"])
def test_every_quadrant_has_an_index(quadrant: str) -> None:
    """The skill requires an index.md in every directory, and the toctree in
    docs/index.md references exactly these four."""
    assert (DOCS / quadrant / "index.md").is_file()


def test_vale_runs_on_the_quadrants_only() -> None:
    """Vale checks American English. Pointed at the German design records it
    reports hundreds of hits and gets switched off, which is worse than not
    running it."""
    makefile = (DOCS / "Makefile").read_text(encoding="utf-8")
    assert "QUADRANTS" in makefile
    assert "superpowers" not in makefile
