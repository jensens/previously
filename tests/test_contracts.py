# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The module boundaries as contracts ({ref}`module-boundaries`).

The probe module that the second test writes is the reason this file carries
so much machinery: it lands **inside the package**, because that is what
`lint-imports` analyses, and a copy left lying around breaks the gate for
everybody who works in this tree afterwards — with a violation nobody wrote.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import previously.core
import pytest
import subprocess
import sys
import warnings


if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterator


# Where `previously.core` really lies, read off the imported package instead
# of off the working directory (finding N4): before, the probe module below
# was written to the relative path `src/previously/core/_violation.py`, which
# silently bound this test to being started from the repository root.
# `__file__` of an imported module is the one statement about the location of
# the sources that holds from any working directory.
_CORE_DIRECTORY = Path(previously.core.__file__).parent
# `src/previously/core` → `src/previously` → `src` → the repository root: the
# directory that holds `.importlinter`. The gate is invoked from there, so
# this test invokes it from there too — config discovery and cache directory
# included. Whether the derivation holds is checked in `_gate`, loudly: for an
# installed wheel it would not, and then the contracts would be checked
# against a different tree than the one the probe is written into.
_REPO_ROOT = _CORE_DIRECTORY.parents[2]
_PROBE = _CORE_DIRECTORY / "_violation.py"

# The two modules that `.importlinter` grants a named exemption, and the two
# top-level packages the exemption is about.
_EXEMPTED_MODULES = ("previously.core.append", "previously.core.verify")
_FORBIDDEN_AT_RUNTIME = ("sqlalchemy", "psycopg")

# Imports the two exempted modules and reports which of the forbidden
# packages ended up in `sys.modules`. Runs in a **fresh** interpreter, see the
# test below. Reduced to the top-level names and printed space-separated: one
# sqlalchemy import drags in a hundred submodules, and `sqlalchemy` is the
# whole statement.
_RUNTIME_PROBE = "\n".join(
    [
        "import sys",
        *(f"import {module}" for module in _EXEMPTED_MODULES),
        f"forbidden = set({_FORBIDDEN_AT_RUNTIME!r})",
        'print(" ".join(sorted({n.partition(".")[0] for n in sys.modules} & forbidden)))',
    ]
)


@pytest.fixture(autouse=True, scope="module")
def _sweep_a_left_over_probe() -> Iterator[None]:
    """Clears a probe module out of the way that an aborted run left behind —
    and says so out loud.

    The writer below removes its file in a `finally`, but a killed process
    (Ctrl-C, OOM killer, power cut) never reaches that `finally`. From then on
    `lint-imports` — and `ruff` and `pyright` with it — reports a violation on
    a file nobody wrote, for everybody, until somebody finds it. Removing it
    silently would hide exactly the knowledge that helps: the warning names
    the path, so that the same thing outside a test run is recognisable.
    """
    if _PROBE.exists():
        warnings.warn(
            f"a probe module out of an aborted test run lay at {_PROBE} and has been "
            "removed. Had it stayed, `lint-imports`, `ruff` and `pyright` would have "
            "reported a violation nobody wrote.",
            stacklevel=1,
        )
        _PROBE.unlink()
    yield
    if _PROBE.exists():
        _PROBE.unlink()
        pytest.fail(f"the probe module {_PROBE} was still lying there after the tests")


@contextmanager
def _probe_module(source: str) -> Generator[None]:
    """Writes a throwaway module into `previously.core` and removes it again.

    The removal is what this helper exists for. Should it fail nonetheless,
    the error names the file to be deleted by hand — the alternative is a
    contract broken for a reason nobody can find.
    """
    _PROBE.write_text(source, encoding="utf-8")
    try:
        yield
    finally:
        try:
            _PROBE.unlink()
        except OSError as error:
            raise AssertionError(
                f"could not remove the probe module {_PROBE}: {error}. Delete it by "
                "hand — otherwise `lint-imports` reports a violation nobody wrote."
            ) from error


def _gate() -> subprocess.CompletedProcess[str]:
    """`lint-imports`, run the way the gate runs it."""
    assert (_REPO_ROOT / ".importlinter").is_file(), (
        f"no .importlinter in {_REPO_ROOT} — that path was derived from "
        f"{previously.core.__file__} and holds only for an installation from "
        "sources (`uv sync`), not for a wheel in site-packages"
    )
    return subprocess.run(
        ["lint-imports"],  # noqa: S607 — fixed name from the [dev] dependency, no user input
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )


def test_import_contracts_hold() -> None:
    result = _gate()
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_deliberately_wrong_import_breaks_the_named_contracts() -> None:
    """An import of sqlalchemy inside core must break the contracts — by name,
    with the offending import in the reasoning.

    The return code on its own is not enough (finding G2): `lint-imports`
    answers a **configuration error** with 1 just the same. Measured against a
    deliberately broken config (`type = does-not-exist`): return code 1,
    output `does-not-exist`, no contract name, no import. Measured from a
    different working directory as well: return code 1, `Could not read any
    configuration.` In both cases the former assertion `returncode != 0` was
    green although no contract had been checked at all — and acceptance
    condition 4, "a deliberately wrong import lets CI fail", hung on exactly
    that assertion. That condition is numbered in the stage 1a specification
    §11 (frozen design record).

    The contract names are checked against the strings in `.importlinter`,
    because those names **are** the gate's output. Renaming one of them turns
    this test red on purpose: whoever renames a contract is changing what the
    gate reports.
    """
    # The probe source carries no bare suppression comment any more. It did,
    # and that made a left-over probe quieter instead of louder: measured,
    # `ruff check .` stays silent on the suppressed line and reports
    # `F401 sqlalchemy imported but unused` on the bare one. A stale probe
    # therefore now trips gate 1 as well as gate 4, naming its own path — and
    # CLAUDE.md forbids a bare suppression anyway, generated content included.
    with _probe_module("import sqlalchemy\n"):
        result = _gate()
    output = result.stdout + result.stderr

    assert result.returncode != 0, output
    # Both contracts that forbid sqlalchemy in `core`, reported by name …
    assert "core knows no foreign system and no model BROKEN" in output, output
    assert "Only storage imports sqlalchemy BROKEN" in output, output
    # … and the import that breaks them, in the reasoning underneath. A
    # configuration error carries no import — that is what tells the two
    # apart.
    assert "previously.core._violation -> sqlalchemy" in output, output


def test_the_exempted_core_modules_load_no_sql_at_runtime() -> None:
    """The bolt behind the two named exemptions in `.importlinter` — **ruling
    T7-g**, which is the label the stage 1a specification refers to it by in
    §12 (frozen design record; finding N-2 of fix round 2 found the label
    pointing at nothing).

    `core.append` and `core.verify` import `PostgresStorage` only under
    `if TYPE_CHECKING:`, and the two exemptions are granted for exactly that
    reason. But they hang on the import **edge**, not on its
    TYPE_CHECKING property: were somebody to pull one of the two imports out
    of its `if TYPE_CHECKING:` block, the exemption would keep covering it,
    `core` would load sqlalchemy at runtime, and the separation of layers
    would be broken — and of the gates, only this one would say so. `ruff`
    does catch the simplest form with `TC001`, but only for as long as the
    symbol appears in annotations and nowhere else; add one use of it outside
    an annotation and ruff falls silent, which is exactly the case that hurts,
    because that is when `core` really does load the driver. Measured against
    the project configuration, with the import out of the block **and** an
    `isinstance` call on the symbol: `lint-imports` 4 kept 0 broken,
    `ruff check .` all checks passed, this test the only failure.

    A **fresh interpreter** is necessary. Inside the test process sqlalchemy
    and psycopg have long been loaded — through `conftest.py`, through
    `storage`, through testcontainers — so `sys.modules` says nothing there.

    This bolt is green today (measured): it holds a state that already
    obtains, instead of uncovering an error. That is what it is for — the
    exemptions are the one place in this tree where a correct decision and a
    wrong one look exactly alike in the configuration.

    **Measured that it goes red**, in a throwaway worktree: pulling the import
    out of the `TYPE_CHECKING` block of `core/verify.py` — and separately of
    `core/append.py` — left `lint-imports` at *4 kept, 0 broken*, because the
    exemption covers the edge either way, while this test failed with
    "loaded sqlalchemy at runtime". That is the whole argument for its
    existence, and without it written down the test looks like redundancy and
    somebody deletes it.

    It falls away without replacement once `core` is typed against a generic
    `LogStore[Conn]` protocol in `contract` instead of the concrete
    `PostgresStorage` — the stage 1a specification
    §12 (frozen design record) carries that as an open point.
    """
    result = subprocess.run(  # noqa: S603 — our own interpreter, our own script, no input
        [sys.executable, "-c", _RUNTIME_PROBE],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    loaded = result.stdout.split()
    assert loaded == [], (
        f"importing {' and '.join(_EXEMPTED_MODULES)} loaded {', '.join(loaded)} at "
        "runtime. One of the imports exempted in `.importlinter` has presumably left "
        "its `if TYPE_CHECKING:` block — the exemption still covers it, but the "
        "separation of layers is broken."
    )
