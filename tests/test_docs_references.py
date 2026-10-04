# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx checks cross-references inside the documentation.

Nobody checks a reference that sits in a Python comment. After the migration
there are dozens of them, so this file is the only thing standing between a
renamed label and a comment that points nowhere. The convention these checks
enforce is written down in {ref}`design-records`.

Why the checks read `.py` only, when the marking rule covers every English
file in the tree: the dividing line is not the extension but **how the place
gets read**. A comment is read on its own, so it carries its marking on its
own line, and a check that reads lines is the right shape for it. A table is
read whole, so one paragraph above it marks every row -- which is why
`DEPENDENCIES.md` says it once instead of thirteen times, and why a bare
citation in `pyproject.toml` is a decision rather than a gap here.
"""

from typing import TYPE_CHECKING

import ast
import pathlib
import re


if TYPE_CHECKING:
    from collections.abc import Mapping

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["src", "tests", "migrations"]

# Where a message a user reads can come from: the command line under `src/`
# and the migration runner under `migrations/`, whose refusal
# {ref}`configuration-reference` documents as program output. A test prints
# to nobody, so `tests/` stays out and the name of the check below stays
# true.
#
# Taking all of `SOURCE_DIRS` was weighed and would be free today: counted,
# `tests/` holds nine occurrences of the sign across three files, every one of
# them in a docstring or a `#` comment, and none in an ordinary literal --
# which the check would not look at anyway. It was not taken because a check
# whose scope is wider than its name is the kind of claim this whole task
# exists to remove, and because a marked sign in a test literal reaches no
# user. `test_no_bare_paragraph_references_remain` reads `tests/` for the
# bare case.
OUTPUT_DIRS = ["src", "migrations"]

DOCS = ROOT / "docs"

# The paragraph sign, built from its code point instead of written out.
# Written out, this file would be an offender against its own check, and
# excluding the file would leave the one place where a new bare citation can
# hide. The measurements the checks come from are recorded in words below.
SECTION = chr(0xA7)

# Every role call is located first and parsed second, so that one that cannot
# be parsed is **reported** rather than skipped: a reference this file cannot
# read is a reference nothing checks. Measured, two forms used to slip through
# as non-references instead of as errors -- `hash_chain` with an underscore,
# and a call wrapped between the role and its opening backtick, which a
# comment reflowed at column 79 produces because the role is six characters
# wide.
#
# `TARGET` then accepts both forms Sphinx accepts, the bare target and a title
# with the target in angle brackets. The documentation uses the second twice,
# so a check that knew only the first would read a renamed label there as
# nothing at all.
ROLE = re.compile(r"\{ref\}")
# No `\A` here: this one is applied with a `pos`, which `match` anchors at
# already, while `\A` would keep pointing at the real start of the file.
AFTER_ROLE = re.compile(r"(?:\s|#)*`([^`]*)`", re.S)
TARGET = re.compile(r"\A(?:[^<>]*<(?P<titled>[^<>]+)>|(?P<plain>[a-z0-9_-]+))\Z")
LABEL = re.compile(r"^\(([a-z0-9-]+)\)=\s*$", re.MULTILINE)


def _labels() -> set[str]:
    found: set[str] = set()
    for page in DOCS.rglob("*.md"):
        if "superpowers" in page.parts or "_build" in page.parts:
            continue
        found.update(LABEL.findall(page.read_text(encoding="utf-8")))
    return found


def _modules(directories: list[str]) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for directory in directories:
        found.extend(sorted((ROOT / directory).rglob("*.py")))
    return found


def _references() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """The targets referenced from the code, and the roles nothing could read."""
    used: dict[str, list[str]] = {}
    unreadable: dict[str, list[str]] = {}
    for module in _modules(SOURCE_DIRS):
        where = str(module.relative_to(ROOT))
        text = module.read_text(encoding="utf-8")
        for role in ROLE.finditer(text):
            call = AFTER_ROLE.match(text, role.end())
            if call is None:
                unreadable.setdefault("<role with no target>", []).append(where)
                continue
            parsed = TARGET.match(call.group(1))
            if parsed is None:
                unreadable.setdefault(call.group(1), []).append(where)
                continue
            target = parsed.group("titled") or parsed.group("plain")
            used.setdefault(target.strip(), []).append(where)
    return used, unreadable


def test_every_doc_reference_in_the_code_resolves() -> None:
    labels = _labels()
    used, unreadable = _references()
    assert not unreadable, (
        f"These reference roles cannot be read as a target: {unreadable}. "
        "Write either the bare label or a title with the label in angle brackets."
    )
    dangling = {name: files for name, files in used.items() if name not in labels}
    assert not dangling, (
        f"These labels are referenced from code but defined in no page: {dangling}. "
        "Either the label was renamed or the page was not written yet."
    )


def test_no_bare_paragraph_references_remain() -> None:
    """A bare paragraph number points at a frozen German document silently."""
    offenders: dict[str, int] = {}
    for module in _modules(SOURCE_DIRS):
        text = module.read_text(encoding="utf-8")
        bare = [
            line
            for line in text.splitlines()
            if SECTION in line and "frozen design record" not in line
        ]
        if bare:
            offenders[str(module.relative_to(ROOT))] = len(bare)
    assert not offenders, (
        f"Bare paragraph references remain: {offenders}. Map them to a "
        "documentation label or mark them as pointing at a frozen design record."
    )


def _docstrings(tree: ast.Module) -> set[int]:
    """The identities of the string nodes that are docstrings, not output."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            found.add(id(first.value))
    return found


def _citing_string_literals(path: pathlib.Path) -> list[int]:
    """The lines whose string literals carry a paragraph sign.

    Read with `ast` and not line by line, for a reason that was measured: a
    line-based search has to tell a comment, a docstring and a message apart
    from the characters on the line, and the second of the two messages this
    check exists for does not look like a message on its own line. It is the
    continuation of an implicitly concatenated literal, so it carries neither
    `raise` nor an `f` prefix, and a heuristic built on those waved it
    through. The parser knows which literal a line belongs to.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = _docstrings(tree)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in docstrings:
            continue
        if isinstance(node.value, str) and SECTION in node.value:
            lines.add(node.lineno)
    return sorted(lines)


def test_no_program_output_cites_a_specification() -> None:
    """A paragraph reference in an error message is a dead pointer.

    Whoever runs `previously append` has no `docs/superpowers/specs/`, so the
    citation buys them nothing even before the freeze makes it stale. Measured
    on 2026-10-03: two messages carried one, `canonical.py:53` with the
    canonicalisation paragraph and the literal beginning at `append.py:309`
    with the perception paragraph. Marking them as a frozen design record
    would pass `test_no_bare_paragraph_references_remain` while making the
    output worse, which is why this test exists beside it.

    Every module that can produce output is read, not the files that happened
    to carry a citation. Measured in fix round 1: with two files named, a
    marked message in `core/verify.py` and a `print` in `cli.py` both passed
    -- and `cli.py`, with nineteen `print` calls since stage 1b, is the only
    file in this tree that writes to the terminal. Measured in fix round 2:
    with only `src/` read, a marked citation in `migrations/dsn.py` passed as
    well, and that module raises its refusal as an implicitly concatenated
    f-string, which is the exact shape of the two the check was built for.
    """
    offenders = {
        str(path.relative_to(ROOT)): found
        for path in _modules(OUTPUT_DIRS)
        if (found := _citing_string_literals(path))
    }
    assert not offenders, (
        f"These lines print a paragraph reference to the user: {offenders}. "
        "Move the reasoning into the comment above and drop it from the message."
    )


def _quoted_messages(page: str) -> set[str]:
    """The `Message` column of the Payload range table, unquoted."""
    section = page.split("## Payload range", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    quoted: set[str] = set()
    for row in rows[2:]:  # the header and the delimiter row are not data
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 2, f"not a two-column row: {row!r}"
        message = cells[1]
        assert message.startswith("`") and message.endswith("`"), (
            f"the Message cell has to be a code span: {row!r}"
        )
        quoted.add(message[1:-1])
    return quoted


def _refusal(payload: Mapping[str, object]) -> str:
    """What `canonical` says about a payload, without the path prefix.

    The page prefixes no path, the message does: everything up to the first
    `: ` is the path, which is `$` for the payload itself, `.name` for an
    object member and `[n]` for an array element.
    """
    from previously.core.canonical import canonical
    from previously.core.errors import InvalidPayload

    try:
        canonical(payload)
    except InvalidPayload as error:
        return str(error).split(": ", 1)[1]
    raise AssertionError(f"{payload!r} was accepted")


def test_the_reference_quotes_what_the_code_actually_prints() -> None:
    """The Payload range table quotes five messages verbatim.

    Nothing else holds them: the typed-output gate covers only the `N passed`
    counts in the tutorial. A string search across the two files would not
    help -- it would follow a changed message into the page. So the messages
    are produced by calling the code, which is the only form of this check
    that can fail for the right reason.

    The two sets have to be **equal**, and the reason is measured. Containment
    in one direction let the page keep a citation the code had stopped
    printing; containment in the other let the page grow a sixth row that
    nothing produces, and let the float quote move out of the table into
    prose. Equality closes both.

    What it does not close is a sixth restriction that reaches the code and
    not the page, and the five payloads below are why: they are enumerated
    here, not derived from `canonical`, so no message is produced for a
    restriction nobody listed. Measured on 2026-10-03, with a sixth
    restriction added to `_check` and `hash-format.md` untouched: `5 passed`.
    The same restriction written into the table alone fails this test. So the
    gate fires when a restriction arrives on the **page**, and stays silent
    when it arrives in the code — then `hash-format.md` goes on saying "The
    five restrictions below" with a row missing. Deriving the payloads from
    the code is the fix and it is not built yet.
    """
    produced = {
        _refusal(payload)
        for payload in (
            {"amount": 1.5},
            {"Total": 1},
            {"amount": 2**53},
            {"text": "a\x00b"},
            {"text": "a\ud800b"},
        )
    }
    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    assert _quoted_messages(page) == produced, (
        "The Payload range table and the messages the code produces have come "
        f"apart.\nonly in the table: {_quoted_messages(page) - produced}\n"
        f"only in the code:  {produced - _quoted_messages(page)}"
    )


def test_the_reference_quotes_the_refusal_by_type_name() -> None:
    """The sixth quote on the page stands in prose, not in the table.

    `Any other type is refused by name, for example ...` is the one message
    the table cannot hold, because it has no restriction of its own to stand
    beside. It was quoted and covered by nothing until fix round 1.
    """
    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    quoted = _refusal({"members": {1, 2}})
    assert f"`{quoted}`" in page, (
        f"hash-format.md does not quote {quoted!r}. The code's message changed; "
        "the Payload range section has to change in the same commit."
    )
