# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The module boundaries as contracts ({ref}`module-boundaries`).

The probe modules that the tests after the first write are the reason this
file carries so much machinery: they land **inside the package**, because that
is what `lint-imports` analyses, and a copy left lying around breaks the gate
for everybody who works in this tree afterwards — with a violation nobody
wrote.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import previously.core
import previously.storage
import pytest
import subprocess
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
# The second place a probe goes: `storage`, for the contract that keeps
# `pyrage` in `core.sealing`. A probe in `core` cannot show that one breaks,
# since `core` is where the one allowed importer lives.
_STORAGE_PROBE = Path(previously.storage.__file__).parent / "_violation.py"
_PROBES = (_PROBE, _STORAGE_PROBE)


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
    for probe in _PROBES:
        if probe.exists():
            warnings.warn(
                f"a probe module out of an aborted test run lay at {probe} and has been "
                "removed. Had it stayed, `lint-imports`, `ruff` and `pyright` would have "
                "reported a violation nobody wrote.",
                stacklevel=1,
            )
            probe.unlink()
    yield
    left = [probe for probe in _PROBES if probe.exists()]
    for probe in left:
        probe.unlink()
    if left:
        pytest.fail(f"the probe modules {left} were still lying there after the tests")


@contextmanager
def _probe_module(source: str, probe: Path = _PROBE) -> Generator[None]:
    """Writes a throwaway module into the package and removes it again —
    into `previously.core` unless `probe` names another of `_PROBES`.

    The removal is what this helper exists for. Should it fail nonetheless,
    the error names the file to be deleted by hand — the alternative is a
    contract broken for a reason nobody can find.
    """
    probe.write_text(source, encoding="utf-8")
    try:
        yield
    finally:
        try:
            probe.unlink()
        except OSError as error:
            raise AssertionError(
                f"could not remove the probe module {probe}: {error}. Delete it by "
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
    assert "core and contract import no sqlalchemy BROKEN" in output, output
    # … and the import that breaks them, in the reasoning underneath. A
    # configuration error carries no import — that is what tells the two
    # apart.
    assert "previously.core._violation -> sqlalchemy" in output, output


def test_boto3_outside_storage_s3_breaks_its_contract() -> None:
    """`boto3` in `core` breaks the contract that keeps it in `storage.s3`,
    by name, with the offending import underneath.

    The exemption for `storage.s3` is one named edge, so this probe is the
    proof that the contract covers the rest of the package and not only the
    layer above it: the layer contract alone would not mind, since `boto3` is
    not a layer.
    """
    with _probe_module("import boto3\n"):
        result = _gate()
    output = result.stdout + result.stderr

    assert result.returncode != 0, output
    assert "Only storage.s3 imports boto3 BROKEN" in output, output
    assert "previously.core._violation -> boto3" in output, output


def test_pyrage_outside_core_sealing_breaks_its_contract() -> None:
    """`pyrage` in `storage` breaks the contract that keeps it in
    `core.sealing`: the store gets and gives ciphertext only, so a storage
    module that could open what it stores is the mistake this contract is
    for ({ref}`blobs`).
    """
    with _probe_module("import pyrage\n", _STORAGE_PROBE):
        result = _gate()
    output = result.stdout + result.stderr

    assert result.returncode != 0, output
    assert "Only core.sealing imports pyrage BROKEN" in output, output
    assert "previously.storage._violation -> pyrage" in output, output
