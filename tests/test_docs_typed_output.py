# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed-out output is a measurement with a date, so it needs a gate.

The test count in the README went stale twice in one session: it was typed
out, then later commits added tests. Only one number in the documentation is
derivable from the tree, and this test derives it.
"""

import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = [ROOT / "docs" / "tutorials" / "record-your-first-event.md"]


def _collected() -> int:
    # All arguments are literal strings, so ruff's S603 (subprocess call: check
    # for execution of untrusted input) doesn't even fire here — measured,
    # confirmed by `ruff check` reporting the suppression itself as unused.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, result.stdout
    return int(match.group(1))


def test_typed_test_counts_match_the_tree() -> None:
    expected = _collected()
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        for claimed in re.findall(r"(\d+) passed", text):
            assert int(claimed) == expected, (
                f"{page.name} claims {claimed} passing tests, the tree has {expected}. "
                "Retype the test run; it is the last thing you do."
            )
