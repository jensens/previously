# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx checks cross-references inside the documentation.

Nobody checks a reference that sits in a Python comment. After the migration
there are dozens of them, so this file is the only thing standing between a
renamed label and a comment that points nowhere. The convention these checks
enforce is written down in {ref}`design-records`.

Why the paragraph-sign checks read `.py` only, when the marking rule covers
every English file in the tree: the dividing line is not the extension but
**how the place gets read**. A comment is read on its own, so it carries its
marking on its own line, and a check that reads lines is the right shape for
it. A table is read whole, so one paragraph above it marks every row -- which
is why `DEPENDENCIES.md` says it once instead of thirteen times, and why a
bare citation in `pyproject.toml` is a decision rather than a gap here.

The **label** check is the one exception, and since 2026-10-04 it reads the
two root configuration files as well. A documentation label is not a marking
a reader can judge on the line: it either resolves or it points nowhere, and
nothing but a check can tell which. `.importlinter` had carried one since
stage 1b with no gate in sight.
"""

from previously.core.errors import ArtifactChanged
from typing import Any
from typing import cast
from typing import TYPE_CHECKING

import ast
import json
import pathlib
import pytest
import re


if TYPE_CHECKING:
    from collections.abc import Mapping
    from previously.contract.types import RawEvent
    from sqlalchemy import Engine

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["src", "tests"]

# Two root configuration files carry a documentation label of their own, and
# until 2026-10-04 they lay outside every check: `.importlinter` points at
# {ref}`module-boundaries` for the measurement behind "a named edge, never a
# pattern", and the final review found it there. `pyproject.toml` carries
# none today and is read all the same, because the next one will land in
# whichever of the two the author happens to be editing.
#
# These are read with the plain regexes below and not with `ast`: the AST
# parts of this file serve the checks that have to tell a docstring from a
# message, and neither file holds a Python literal.
CONFIG_FILES = ["pyproject.toml", ".importlinter"]

# Where a message a user reads can come from: the command line, and the
# migration runner whose refusal {ref}`configuration-reference` documents as
# program output. Both are under `src/`, the runner in
# `src/previously/migrations/` since 2026-10-05. A test prints to nobody, so
# `tests/` stays out and the name of the check below stays true.
#
# Taking all of `SOURCE_DIRS` was weighed and would be free today: counted on
# 2026-10-05, `tests/` holds seven occurrences of the sign across three files,
# every one of them in a docstring or a `#` comment, and none in an ordinary
# literal -- which the check would not look at anyway. It was not taken
# because a check whose scope is wider than its name is the kind of claim this
# whole task exists to remove, and because a marked sign in a test literal
# reaches no user. `test_no_bare_paragraph_references_remain` reads `tests/`
# for the bare case.
OUTPUT_DIRS = ["src"]

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


def _referencing_files() -> list[pathlib.Path]:
    """Every file whose reference roles this check resolves."""
    return [*_modules(SOURCE_DIRS), *(ROOT / name for name in CONFIG_FILES)]


def _references() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """The targets referenced from the code, and the roles nothing could read."""
    used: dict[str, list[str]] = {}
    unreadable: dict[str, list[str]] = {}
    for module in _referencing_files():
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
    -- and `cli.py`, with twenty-six `print` calls since `redact` arrived
    (measured on 2026-10-04), is the only file in this tree that writes to
    the terminal. Measured in fix round 2:
    with only `src/` read, a marked citation in `migrations/dsn.py` passed as
    well -- the migrations lay outside `src/` until 2026-10-05 -- and that
    module raises its refusal as an implicitly concatenated f-string, which
    is the exact shape of the two the check was built for.
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


def _quoted_block(page: str, after: str) -> list[str]:
    """The lines of the first `text` block after the sentence `after`."""
    assert after in page, f"cli.md no longer carries the sentence {after!r}"
    rest = page.split(after, 1)[1]
    block = rest.split("```text", 1)[1].split("```", 1)[0]
    return [line for line in block.splitlines() if line.strip()]


def _static_parts(node: ast.expr, constants: Mapping[str, str] | None = None) -> list[str]:
    """What stays of a string literal once the interpolations are taken out.

    A plain literal is one part, an f-string is its `Constant` values in
    order. Only the direct children of the `JoinedStr` count: a literal
    nested inside an interpolation -- `_plural(lag, 'event')` is the case in
    this tree -- is an argument, not text of the message.

    An interpolation of a name in `constants` is text, not a gap: it is a
    module-level string such as `CURSOR_REFUSED`, and left a gap it would let
    any wording stand in for it. Measured on 2026-10-11: with the cursor
    sentence interpolated, `cursor is NOT VALID ANYWHERE; call again without a
    cursor for the first page` passed for a text the server builds.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else []
    if not isinstance(node, ast.JoinedStr):
        return []
    known = constants or {}
    parts: list[str] = []
    text: str | None = None
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            text = (text or "") + value.value
        elif (
            isinstance(value, ast.FormattedValue)
            and isinstance(value.value, ast.Name)
            and value.value.id in known
            and value.format_spec is None
            and value.conversion == -1
        ):
            text = (text or "") + known[value.value.id]
        else:
            # An interpolation at either end becomes an empty part there, so
            # that `_is_the_same_sentence` lets the line open or close with
            # whatever was interpolated: `f"there is no event {event_id}"`
            # ends in a number, not in `event `. Measured on 2026-10-04, when
            # `redact` brought the first quoted messages that end in an
            # interpolation and the check refused every one of them.
            parts.append(text or "")
            text = None
    parts.append(text or "")
    if not "".join(parts):
        return []
    return parts


def _module_strings(*paths: pathlib.Path) -> dict[str, str]:
    """The module-level names of `paths` that are bound to a string literal,
    or to an f-string made only of literals and such names, by name."""
    found: dict[str, str] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target, value = statement.targets[0], statement.value
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                target, value = statement.target, statement.value
            else:
                continue
            if not isinstance(target, ast.Name):
                continue
            parts = _static_parts(value, found)
            if len(parts) == 1:
                found[target.id] = parts[0]
    return found


def _message_patterns(path: pathlib.Path) -> list[list[str]]:
    """The static parts of the strings the module hands to the terminal.

    Both ways it does: the first positional argument of a `print(...,
    file=sys.stderr)` call, and every string a function returns. The second
    is not decoration. `cli.py` prints the lag sentence as
    `print(lag, file=sys.stderr)`, where `lag` came out of `_lag_line`, so a
    check that read only the call sites would see the truncation sentence and
    not the one next to it -- measured on 2026-10-04, with the page's lag line
    falsified and the check green.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            found.append(_static_parts(node.value))
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "print" or not node.args:
            continue
        if any(
            keyword.arg == "file" and ast.unparse(keyword.value) == "sys.stderr"
            for keyword in node.keywords
        ):
            found.append(_static_parts(node.args[0]))
    return [parts for parts in found if parts and len("".join(parts)) >= 10]


def _finding_patterns(path: pathlib.Path) -> list[list[str]]:
    """The static parts of every reason a module hands to `Finding(...)`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        parts
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Finding"
        and len(node.args) == 2
        and (parts := _static_parts(node.args[1]))
    ]


def _raised_patterns(path: pathlib.Path, error: str) -> list[list[str]]:
    """The static parts of every message a module raises as `error(...)`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        parts
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == error
        and node.args
        and (parts := _static_parts(node.args[0]))
    ]


def _outstanding_patterns(path: pathlib.Path) -> list[list[str]]:
    """The static parts of what a module hands to `_unfinished` as what is
    outstanding: the second argument of each call, and every f-string
    assigned to `outstanding`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[list[str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_unfinished"
            and len(node.args) == 2
        ):
            found.append(_static_parts(node.args[1]))
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "outstanding" for target in node.targets
        ):
            found.append(_static_parts(node.value))
    return [parts for parts in found if parts]


def _string_constants(path: pathlib.Path, function: str) -> set[str]:
    """Every string literal in the body of one function of a module, its
    docstring included, which matches no finding's wording."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            return {
                found.value
                for found in ast.walk(node)
                if isinstance(found, ast.Constant) and isinstance(found.value, str)
            }
    raise AssertionError(f"{path.name} has no function {function}")


def _is_the_same_sentence(parts: list[str], line: str) -> bool:
    """Whether `line` is that message with its interpolations filled in.

    The first part has to open the line and the last has to close it, or a
    message whose end was rewritten would still pass on the strength of its
    beginning.
    """
    if not line.startswith(parts[0]) or not line.endswith(parts[-1]):
        return False
    position = 0
    for part in parts:
        found = line.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


def _assert_raised(quoted: list[str], raised: list[list[str]], error_class: str) -> None:
    """Every quoted line is `Error: ` and then a message one of `raised` says.

    A function of its own for ruff's `C901`, whose threshold here is ten.
    Measured on 2026-10-05 with `ruff check --select C901 --config
    'lint.mccabe.max-complexity = 1' tests/test_docs_references.py`: the
    test that calls it stood at nine, the loop over the errors of `migrate`
    with these assertions written inline took it to eleven, and with them
    here it stands at ten.
    """
    for line in quoted:
        prefix, _, error = line.partition(": ")
        assert prefix == "Error", f"cli.md quotes the error {line!r} without `Error: `"
        assert any(_is_the_same_sentence(parts, error) for parts in raised), (
            f"cli.md quotes the error {error!r} and no `{error_class}` raises it. "
            "Either the code's wording changed, or the page's did."
        )


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

    The second half holds the twenty-two standard-error sentences, the two
    lines of `redact` and the three of `migrate` on standard output that
    `cli.md` quotes, in fifteen blocks, against the literals in `cli.py` — not
    the line `blob get` prints on success, which `_message_patterns` does
    not collect, since it reads standard-error sentences and returned lines
    only; the seven refusals of `redact` against the messages
    `core/redact.py` and `cli.py` raise as `RedactionRefused`; the three
    errors of `migrate` against the messages `storage/migrate.py` raises as
    `UnknownRevision` and `MigrationFailed`, the missing schema against the
    one `storage/postgres.py` raises as `MigrationPending`, the four
    failures to connect against the two it raises as `ServerUnreachable`,
    the failed operation against `OperationFailed` and the refused
    connection string against `InvalidDsn`; the nine errors of the blob commands and of an
    unfinished redaction against the messages `cli.py` raises as
    `PreviouslyError` or `InvalidPayload` and `core/blob.py` raises as
    `BlobError`;
    the refused address and the renamed host of `ingest imap` against
    `cli.py`, its four errors that end the run against the messages
    `connectors/imap.py` raises as `MailboxUnreachable`, its eight errors of
    a folder against those it raises as `ImapError`, behind the folder's
    prefix, and its line on standard output against the f-string `cli.py`
    prints it with;
    the fourteen findings it quotes, three from the anchors, ten from
    the hash formats, erasure and action names and one from the blob register, against the
    reasons `core/verify.py` hands to `Finding`; and the four findings about
    blobs against the reasons `_blob_reason` in `core/verify.py` returns,
    since the `Finding` they stand in interpolates the reason whole. The first two sentences
    were quoted and covered by nothing until 2026-10-04: the first half of
    this test reads the *Payload range* table and nothing else, and the
    command line's notices reach no other check. They cannot be produced by
    calling the code the way a refusal can — the truncation sentence needs a
    cut window and the lag sentence a projection that is behind — so this
    half matches the page's line against the message's static parts instead,
    which is the strongest form available without a database.

    Each block is found by the sentence that introduces it, and
    a sentence that vanishes from the page fails with a message naming it.
    Until 2026-10-04 that was an `IndexError`. The direction is page to code
    only, for both halves: a reason in `core/verify.py` that the page does not
    quote is not looked for, and neither is a new `print(..., file=sys.stderr)`
    in `cli.py` that the page does not quote.
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

    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    patterns = _message_patterns(ROOT / "src" / "previously" / "cli.py")
    for after, expected in (
        ("Two notices go to standard error", 2),
        ("Without anchors, one notice goes to standard error", 1),
        ("On an empty log, one notice goes to standard error", 1),
        ("For each unit it skips, one notice goes to standard error", 1),
        ("one notice goes to standard error, naming the blob and those events", 2),
        ("When a string anywhere in the payload of the target", 1),
        ("For each approval that stands of the target, one notice goes to standard error", 1),
        ("`redact` prints one of two lines to standard output", 2),
        ("`migrate` prints one line to standard output, in one of two forms", 3),
        ("When no event names the blob, `blob get` returns 1", 1),
        ("When every reference to the blob is erased, `blob get` returns 1", 1),
        ("For each variant, one notice goes to standard error", 1),
        ("When no call fell back, standard output stays empty, and one notice goes", 1),
        ("`gate try` writes these lines to standard error as well", 6),
        ("`gate explain` writes one more line to standard error", 2),
        ("does the same after one more line", 2),
    ):
        notices = _quoted_block(page, after)
        assert len(notices) == expected, f"{after!r}: {notices}"
        for notice in notices:
            assert any(_is_the_same_sentence(parts, notice) for parts in patterns), (
                f"cli.md quotes {notice!r} as output and no message in cli.py "
                "says that. Either the code's wording changed, or the page's did."
            )

    # The refusals of `redact` come out of `core/redact.py`, and the one about
    # `--reason` out of `cli.py`; the command line prints each behind
    # `Error: `, which is held here the way the `FINDING` prefix is below.
    refusals = [
        *_raised_patterns(ROOT / "src" / "previously" / "core" / "redact.py", "RedactionRefused"),
        *_raised_patterns(ROOT / "src" / "previously" / "cli.py", "RedactionRefused"),
    ]
    quoted = _quoted_block(page, "Seven refusals")
    assert len(quoted) == 7, quoted
    for line in quoted:
        prefix, _, refusal = line.partition(": ")
        assert prefix == "Error", f"cli.md quotes the refusal {line!r} without `Error: `"
        assert any(_is_the_same_sentence(parts, refusal) for parts in refusals), (
            f"cli.md quotes the refusal {refusal!r} and no `RedactionRefused` raises it. "
            "Either the code's wording changed, or the page's did."
        )

    # The errors of `migrate` come out of `storage/migrate.py`, raised as
    # `UnknownRevision` or `MigrationFailed`, and the one every other command
    # gives against a database without the schema out of `storage/postgres.py`,
    # raised as `MigrationPending`, and the failure to connect, the failed
    # operation and the refused string out of `storage/postgres.py`, raised as
    # `ServerUnreachable`, `OperationFailed` and `InvalidDsn`; the command
    # line prints each behind `Error: `. What `MigrationFailed`,
    # `ServerUnreachable` and `OperationFailed` say after their last colon is
    # the reason the server or the client library gives, which
    # `tests/test_migrate.py` and `tests/test_cli.py` hold against a real
    # database.
    storage = ROOT / "src" / "previously" / "storage"
    for after, module, error_class, expected in (
        ("is refused, and nothing changes", "migrate.py", "UnknownRevision", 1),
        ("the database's own reason", "migrate.py", "MigrationFailed", 2),
        ("against a database without it prints one sentence", "postgres.py", "MigrationPending", 1),
        ("When connecting to the database fails", "postgres.py", "ServerUnreachable", 4),
        ("When the database ends an operation", "postgres.py", "OperationFailed", 1),
        (
            "is refused before anything connects, with one sentence that names no part of it",
            "postgres.py",
            "InvalidDsn",
            1,
        ),
    ):
        quoted = _quoted_block(page, after)
        assert len(quoted) == expected, quoted
        _assert_raised(quoted, _raised_patterns(storage / module, error_class), error_class)

    # The errors of `blob get` and the input errors of the blob commands come
    # out of `cli.py`, raised as `PreviouslyError` or `InvalidPayload`; the
    # one about the temporary file out of `core/blob.py`, as `BlobError`, and
    # it is held against that module alone. Held against both, it passed in
    # any wording that began with `cannot write ` and had a colon in it:
    # `cannot write <file>: <reason>` from `cli.py` took the rest as the
    # file (measured on 2026-10-05, fix round 1 of task 6).
    from_cli = [
        *_raised_patterns(ROOT / "src" / "previously" / "cli.py", "PreviouslyError"),
        *_raised_patterns(ROOT / "src" / "previously" / "cli.py", "InvalidPayload"),
    ]
    from_blob = _raised_patterns(ROOT / "src" / "previously" / "core" / "blob.py", "BlobError")
    blocks = (
        ("A file that can't be opened, that can't be read twice", from_cli, "cli.py"),
        ("A temporary file for the sealed form that can't be created", from_blob, "core/blob.py"),
        ("and refuses anything else as an input error", from_cli, "cli.py"),
        ("Four errors of `blob get`", from_cli, "cli.py"),
        ("If deleting a blob or the catch-up fails", from_cli, "cli.py"),
    )
    quoted = 0
    for after, errors, module in blocks:
        for line in _quoted_block(page, after):
            quoted += 1
            prefix, _, error = line.partition(": ")
            assert prefix == "Error", f"cli.md quotes the error {line!r} without `Error: `"
            assert any(_is_the_same_sentence(parts, error) for parts in errors), (
                f"cli.md quotes the error {error!r} and {module} raises no such message. "
                "Either the code's wording changed, or the page's did."
            )
    assert quoted == 9, quoted

    # `ingest imap`: the refused address and the renamed host out of
    # `cli.py`, the errors of the
    # server and the connection out of `connectors/imap.py`, raised as
    # `MailboxUnreachable` or `ImapError` and held against that module alone,
    # and the line on standard output against the one f-string in `cli.py`
    # that says `appended`, since `_message_patterns` reads standard error
    # only.
    refused = _quoted_block(page, "is refused the same way, and so is a `PREVIOUSLY_IMAP_HOST`")
    assert len(refused) == 2, refused
    _assert_raised(refused, from_cli, "PreviouslyError")
    whole = _quoted_block(page, _MAILBOX_ERRORS)
    assert len(whole) == 4, whole
    _assert_raised(whole, _mailbox_errors(), "MailboxUnreachable")
    of_folder = _quoted_block(page, _FOLDER_ERRORS)
    assert len(of_folder) == 8, of_folder
    _assert_raised(_behind_the_folder(of_folder), _imap_errors(), "ImapError")
    counts = _quoted_block(page, "`ingest imap` prints one line to standard output for each folder")
    assert len(counts) == 1, counts
    said = [
        parts
        for node in ast.walk(ast.parse((ROOT / "src" / "previously" / "cli.py").read_text("utf-8")))
        if isinstance(node, ast.JoinedStr)
        and " appended, " in "".join(parts := _static_parts(node))
    ]
    assert len(said) == 1, said
    assert _is_the_same_sentence(said[0], counts[0]), (
        f"cli.md quotes {counts[0]!r} as the line of `ingest imap` and cli.py prints "
        f"{said[0]!r}. Either the code's wording changed, or the page's did."
    )

    # An unfinished redaction says what is outstanding inside an interpolation
    # of `_unfinished`, so the sentence above holds only its frame; what
    # stands between `finished: ` and `; run` is held against the phrases
    # `cli.py` builds for it, in the assignments and calls that name it.
    outstanding = _outstanding_patterns(ROOT / "src" / "previously" / "cli.py")
    for line in _quoted_block(page, "If deleting a blob or the catch-up fails"):
        phrase = line.split("but it is not finished: ", 1)[1].rsplit("; run the same", 1)[0]
        assert any(_is_the_same_sentence(parts, phrase) for parts in outstanding), (
            f"cli.md quotes {phrase!r} as outstanding and cli.py builds no such phrase. "
            "Either the code's wording changed, or the page's did."
        )

    reasons = _finding_patterns(ROOT / "src" / "previously" / "core" / "verify.py")
    findings = [
        *_quoted_block(page, "Three findings come from the anchors"),
        *_quoted_block(
            page,
            "Ten findings come from the hash formats, from erasure and from the names of actions",
        ),
        *_quoted_block(page, "One finding comes from the blob register"),
    ]
    assert len(findings) == 14, findings
    for line in findings:
        # The prefix is held as well, or a page quoting `FINDINGS 42: ...`
        # would pass on the strength of its reason. Its form is written down
        # here rather than read from `cli.py`, where it is an f-string with
        # nothing but `FINDING ` and `: ` around the id. The other end is held
        # in `tests/test_cli.py`: `test_verify_reports_a_deleted_tip_against_the_anchor`
        # and `test_anchor_prints_the_tip_and_verify_holds_it` compare whole
        # finding lines exactly, so a change to the code's prefix fails there.
        prefix, _, reason = line.partition(": ")
        assert re.fullmatch(r"FINDING [0-9]+", prefix), (
            f"cli.md quotes the finding line {line!r}, and its prefix is not "
            "`FINDING <id>: `, which is what cli.py prints before a reason."
        )
        assert any(_is_the_same_sentence(parts, reason) for parts in reasons), (
            f"cli.md quotes the finding {reason!r} and core/verify.py produces no such "
            "reason. Either the code's wording changed, or the page's did."
        )

    # The findings about blobs are `f"blob {sha256} {reason}"`, whose static
    # parts would let any line that begins with `blob ` pass; the reason is
    # held against the strings `_blob_reason` returns instead.
    blob_reasons = _string_constants(
        ROOT / "src" / "previously" / "core" / "verify.py", "_blob_reason"
    )
    blob_findings = _quoted_block(page, "Four findings come from the blobs")
    assert len(blob_findings) == 4, blob_findings
    for line in blob_findings:
        matched = re.fullmatch(r"FINDING [0-9]+: blob [0-9a-f]{64} (.+)", line)
        assert matched is not None, f"cli.md quotes the blob finding {line!r} in another form"
        assert matched[1] in blob_reasons, (
            f"cli.md quotes the blob finding {matched[1]!r} and `_blob_reason` returns "
            "no such reason. Either the code's wording changed, or the page's did."
        )


def _imap_errors() -> list[list[str]]:
    return _raised_patterns(ROOT / "src" / "previously" / "connectors" / "imap.py", "ImapError")


def _mailbox_errors() -> list[list[str]]:
    return _raised_patterns(
        ROOT / "src" / "previously" / "connectors" / "imap.py", "MailboxUnreachable"
    )


# The sentences that open the two blocks of errors of `ingest imap` in cli.md.
_MAILBOX_ERRORS = "Errors that every folder of the mailbox would meet alike"
_FOLDER_ERRORS = "Errors of a folder print one line to standard error"
# The folder every quoted error of a folder names.
_QUOTED_FOLDER = "Kunde Müller"


def _behind_the_folder(quoted: list[str]) -> list[str]:
    """Each quoted error of a folder as `Error: ` and the sentence after the
    folder's prefix, the form `_assert_raised` holds.

    The prefix is held here as well, against the one f-string in `cli.py`
    that prints an error with a folder in it, or a page quoting
    `Error: Ordner Kunde Müller: ...` would pass on the strength of the
    sentence behind it.
    """
    tree = ast.parse((ROOT / "src" / "previously" / "cli.py").read_text("utf-8"))
    printed = [
        parts
        for node in ast.walk(tree)
        if isinstance(node, ast.JoinedStr)
        and (parts := _static_parts(node))
        and parts[0].startswith("Error: folder ")
    ]
    assert printed == [["Error: folder ", ": ", ""]], printed
    prefix = f"Error: folder {_QUOTED_FOLDER}: "
    for line in quoted:
        assert line.startswith(prefix), f"cli.md quotes the error {line!r} without {prefix!r}"
    return ["Error: " + line.removeprefix(prefix) for line in quoted]


def test_the_reference_quotes_every_error_of_ingest_imap() -> None:
    """Two pages promise that `cli.md` lists every error of `ingest imap`,
    so every sentence the connector raises is quoted there — the direction
    from the code to the page, which the test above does not take. Five were
    missing until the fix wave of 2026-10-06. Since a run reads several
    folders, each sentence has to stand in the right one of two blocks: one
    raised as `MailboxUnreachable` among the errors that end the run, one
    raised as `ImapError` among the errors of a folder.

    The two refusals of the log that come back at every run are held as
    well, behind the folder's prefix: the batch that is too large against
    what `core/append.py` raises as `BatchTooLarge`, and the variant key held
    with another content by raising `ArtifactChanged` with the hashes the
    page shows, two that share their first 64 bits."""
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    for raised, after, block in (
        (_mailbox_errors(), _MAILBOX_ERRORS, _quoted_block(page, _MAILBOX_ERRORS)),
        (_imap_errors(), _FOLDER_ERRORS, _behind_the_folder(_quoted_block(page, _FOLDER_ERRORS))),
    ):
        quoted = [line.partition(": ")[2] for line in block]
        for parts in raised:
            assert any(_is_the_same_sentence(parts, line) for line in quoted), (
                f"connectors/imap.py raises {parts!r} and cli.md quotes no such error "
                f"in the block after {after!r}. Quote it there."
            )

    variant, batch = _behind_the_folder(
        _quoted_block(page, "Two refusals of the log come back at every run")
    )
    _assert_raised(
        [batch],
        _raised_patterns(ROOT / "src" / "previously" / "core" / "append.py", "BatchTooLarge"),
        "BatchTooLarge",
    )
    shared = bytes.fromhex("afe0b335e95e6b9e")
    refused = ArtifactChanged(
        "email",
        "20261005101500.4711@example.net#afe0b335e95e6b9e",
        known=shared + bytes(24),
        arrived=shared + bytes([0xFF] * 24),
    )
    assert variant == f"Error: {refused}", variant


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


def test_the_reference_quotes_the_refusal_of_another_artifact() -> None:
    """Both pages quote the sentence of `ArtifactChanged`, and both quotes
    are produced by raising it with the values each page names: the two
    hashes of `append --text A` and `--text B` in `cli.md`, and two made-up
    hashes in `hash-format.md`. Calling the code holds the hashes and their
    16-character cut as well, which a match against the static parts of the
    message would let pass in any form."""
    from previously.core.errors import ArtifactChanged
    from previously.core.identity import artifact_hash_of

    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    quoted = _quoted_block(page, "and another text or other attachments is refused")
    produced = ArtifactChanged(
        "cli",
        "a",
        known=artifact_hash_of({"text": "A", "attachments": []}),
        arrived=artifact_hash_of({"text": "B", "attachments": []}),
    )
    assert quoted == [f"Error: {produced}"], quoted

    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    quoted = _quoted_block(page, "its message shows the first 16 hexadecimal characters")
    produced = ArtifactChanged(
        "email", "m1", known=bytes.fromhex("11" * 32), arrived=bytes.fromhex("22" * 32)
    )
    assert quoted == [str(produced)], quoted


def test_the_reference_quotes_the_refusal_of_a_reserved_identity_key() -> None:
    """`hash-format.md` quotes the refusal of `artifact_hash` and
    `channel_identities` with `<key>` where the name goes; held against the
    static parts of what `core/append.py` raises as `InvalidPayload`."""
    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    lead = "carries `artifact_hash` or `channel_identities` with `"
    assert lead in page, f"hash-format.md no longer carries {lead!r}"
    quoted = page.split(lead, 1)[1].split("`", 1)[0]
    raised = _raised_patterns(ROOT / "src" / "previously" / "core" / "append.py", "InvalidPayload")
    assert any(_is_the_same_sentence(parts, quoted) for parts in raised), (
        f"hash-format.md quotes {quoted!r} and core/append.py raises no such message. "
        "Either the code's wording changed, or the page's did."
    )


# The page on the mapping of a mail quotes the fixed sentences of its units
# and names the keys of its payload, and both are held here against what the
# code produces for the test mails, which are invented. No server and no
# database: the mapping is called directly, and the keys the run adds are
# read out of `core/ingest.py`.
MAIL_PAGE = DOCS / "reference" / "mail-mapping.md"
MAILS = ROOT / "tests" / "mails"


def _mapped_events(name: str) -> list[RawEvent]:
    """The event of the test mail `name` and of every mail inside it."""
    from datetime import datetime
    from datetime import UTC
    from previously.core.mail import map_mail

    found: list[RawEvent] = []
    pending = [
        map_mail(
            (MAILS / name).read_bytes(),
            internaldate=datetime(2026, 10, 6, 9, 0, tzinfo=UTC),
            found_in={"connector": "imap:pilot@mail.example.org/Kunde Müller", "uid": "1"},
        )
    ]
    while pending:
        mapped = pending.pop()
        found.append(mapped.event)
        pending.extend(mapped.inner)
    return found


def _first_cells(page: str, heading: str, after: str, *, name: str = "mail-mapping.md") -> set[str]:
    """The code spans in the first column of the first table after the
    sentence `after`, in the section under `heading`."""
    assert heading in page, f"{name} no longer has the section {heading!r}"
    section = page.split(heading, 1)[1].split("\n## ", 1)[0]
    assert after in section, f"{name} no longer carries the sentence {after!r}"
    rows: list[str] = []
    for line in section.split(after, 1)[1].splitlines():
        if line.startswith("|"):
            rows.append(line)
        elif rows:
            break
    cells: set[str] = set()
    for row in rows[2:]:  # the header and the delimiter row are not data
        first = row.strip("|").split("|", 1)[0].strip()
        assert first.startswith("`") and first.endswith("`"), (
            f"the first cell has to be a code span: {row!r}"
        )
        cells.add(first[1:-1])
    return cells


def _keys_the_run_adds() -> set[str]:
    """The keys `core/ingest.py` writes into a payload: the string keys of
    every dict display in it that spreads another mapping into itself."""
    tree = ast.parse((ROOT / "src" / "previously" / "core" / "ingest.py").read_text("utf-8"))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and None in node.keys:
            keys.update(
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    return keys


def test_the_mail_mapping_quotes_the_units_of_a_mail_without_text() -> None:
    """The three sentences of a mail without a readable body, and the unit
    of a mail that does not map, each produced by mapping a test mail of
    that case: what the page quotes is the unit the code writes."""
    page = MAIL_PAGE.read_text(encoding="utf-8")
    produced = [
        _mapped_events(name)[0].units[-1].content
        for name in ("encrypted.eml", "attachments_only.eml", "empty.eml")
    ]
    quoted = _quoted_block(page, "has one unit in place of the body, with one of three sentences")
    assert quoted == produced, quoted
    unreadable = _mapped_events("unreadable_header.eml")[0].units
    quoted = _quoted_block(page, "which can quote a header, as in this one")
    assert quoted == [unit.content for unit in unreadable], quoted


def test_the_mail_mapping_names_every_key_the_mapping_writes() -> None:
    """The payload table names exactly the keys that the mapping writes for
    the test mails, every mail inside them included, and that the run adds;
    the table of a body entry names exactly the keys of one.

    Equality, for the reason the Payload range check above gives: a key the
    code stopped writing and a key the page never named both fail. A key
    that no test mail produces cannot be held this way; the test mails carry
    a case for each optional key of the mapping, and the two keys only the
    run writes, `raw` and `variant_of`, come out of `core/ingest.py`.
    """
    page = MAIL_PAGE.read_text(encoding="utf-8")
    events = [
        event
        for name in sorted(path.name for path in MAILS.glob("*.eml"))
        for event in _mapped_events(name)
    ]
    written = {key for event in events for key in event.payload}
    named = _first_cells(page, "## Payload", "The mapping and the run write these keys")
    assert named == written | _keys_the_run_adds(), (
        f"only on the page: {named - written - _keys_the_run_adds()}\n"
        f"only in the code: {(written | _keys_the_run_adds()) - named}"
    )
    entries = {
        key
        for event in events
        for entry in cast("list[dict[str, object]]", event.payload.get("body", []))
        for key in entry
    }
    assert _first_cells(page, "## Payload", "Each entry of `body`") == entries


def test_the_mail_mapping_names_the_converter_and_quotes_the_batch_refusal() -> None:
    """The converter's name and version as the payload writes them, and the
    refusal of a mail that makes too many events, held against what
    `core/append.py` raises as `BatchTooLarge`."""
    from previously.core.mail import CONVERTER

    page = MAIL_PAGE.read_text(encoding="utf-8")
    assert f"as `{CONVERTER}`" in page, f"mail-mapping.md does not name {CONVERTER!r}"
    _assert_raised(
        _quoted_block(page, "makes more than 500 events is refused at every run"),
        _raised_patterns(ROOT / "src" / "previously" / "core" / "append.py", "BatchTooLarge"),
        "BatchTooLarge",
    )


# The reference on policy events and model calls names the keys of two kinds of
# payload and quotes the fixed words of a model call: its outcomes, its alarm,
# its reasons for a denial. Every one of them is held here against the code
# that writes it. The keys are read out of the dict displays of `gate/gate.py`
# and `core/policy.py` and not from a payload written by a test, because a key
# that only some path writes, such as `error`, would be missing from a payload
# of the path that was run. The two examples on the page are held whole: the
# policy event against `to_payload`, the model call against the key sets.
POLICY_PAGE = DOCS / "reference" / "policy-and-model-calls.md"
GATE_MODULE = ROOT / "src" / "previously" / "gate" / "gate.py"
POLICY_PAGE_NAME = "policy-and-model-calls.md"


def _policy_cells(heading: str, after: str) -> set[str]:
    return _first_cells(
        POLICY_PAGE.read_text(encoding="utf-8"), heading, after, name=POLICY_PAGE_NAME
    )


def _display_keys(function: str, *markers: str) -> set[str]:
    """The string keys of the smallest dict display in a function of
    `gate/gate.py` that has all of `markers` among its keys."""
    tree = ast.parse(GATE_MODULE.read_text(encoding="utf-8"))
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == function
    ]
    assert len(functions) == 1, f"gate.py has {len(functions)} functions named {function}"
    found: list[set[str]] = []
    for node in ast.walk(functions[0]):
        if isinstance(node, ast.Dict):
            keys = {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if set(markers) <= keys:
                found.append(keys)
    assert found, f"gate.py:{function} has no dict display with the keys {markers}"
    return min(found, key=len)


def _payload_keys_set_later() -> set[str]:
    """The keys `call` sets on the payload after the dict display: every
    `payload["key"] = ...` in it, the nested `record` included."""
    tree = ast.parse(GATE_MODULE.read_text(encoding="utf-8"))
    (call,) = (
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "call"
    )
    return {
        target.slice.value
        for node in ast.walk(call)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and target.value.id == "payload"
        and isinstance(target.slice, ast.Constant)
        and isinstance(target.slice.value, str)
    }


def _json_block(after: str) -> dict[str, Any]:
    """The first `json` code block after the sentence `after`."""
    page = POLICY_PAGE.read_text(encoding="utf-8")
    assert after in page, f"{POLICY_PAGE_NAME} no longer carries the sentence {after!r}"
    block = page.split(after, 1)[1].split("```json\n", 1)[1].split("\n```", 1)[0]
    return cast("dict[str, Any]", json.loads(block))


def test_the_policy_reference_names_the_keys_of_every_statement() -> None:
    """The four common keys, the replacement key of each kind and the keys of
    a rule and of a provider, each held against what `to_payload` writes."""
    from previously.core.policy import Circle
    from previously.core.policy import Client
    from previously.core.policy import Inference
    from previously.core.policy import key_of
    from previously.core.policy import KINDS
    from previously.core.policy import Membership
    from previously.core.policy import OwnIdentity
    from previously.core.policy import Provider
    from previously.core.policy import Rule
    from previously.core.policy import to_payload

    statements = [
        Circle("xz"),
        Membership("xz", "@example.net"),
        OwnIdentity("@example.org"),
        Rule("circle:xz", frozenset({"eu"}), None, frozenset()),
        Provider("p", (Inference("eu", frozenset({"eu"})),), frozenset({"eu"}), None, False, True),
        Client("c", "p", "0" * 64),
    ]
    payloads = [to_payload(item, statement="s") for item in statements]
    common: set[str] = set(payloads[0]).intersection(*(set(payload) for payload in payloads[1:]))
    assert _policy_cells("## Policy events", "Four keys are common to all six kinds.") == common
    assert _policy_cells("### The six kinds", "beside the four common ones:") == set(KINDS)
    assert [payload["policy"] for payload in payloads] == list(KINDS)
    page = POLICY_PAGE.read_text(encoding="utf-8")
    for item, payload in zip(statements, payloads, strict=True):
        kind, _ = key_of(item)
        row = next(line for line in page.splitlines() if line.startswith(f"| `{kind}` |"))
        _, replacement, further = (cell.strip() for cell in row.strip("|").split("|"))
        own = [name for name in payload if name not in common]
        assert further == ", ".join(f"`{name}`" for name in own), (
            f"the row of {kind!r} on {POLICY_PAGE_NAME} names other keys than {own}"
        )
        assert set(re.findall(r"`([a-z_]+)`", replacement)) <= set(own), replacement
    rule_and_provider = (set(payloads[3]) | set(payloads[4])) - common
    assert (
        _policy_cells(
            "### The six kinds", "The keys of a `rule` and a `provider`, with their values:"
        )
        == rule_and_provider
    )
    assert (
        _policy_cells("### The six kinds", "The keys of a `client`, with their values:")
        == set(payloads[5]) - common
    )


def test_the_policy_reference_names_the_keys_of_a_model_call() -> None:
    """The payload, its six entries and the examples, against the dict displays
    of `gate/gate.py`; the example against the keys it would have to hold."""
    top = _display_keys("call", "action", "task", "inputs", "policy") | _payload_keys_set_later()
    task = _display_keys("call", "prompt_sha256")
    inputs = _display_keys("call", "event", "units", "blobs")
    policy = _display_keys("_policy_part", "decision")
    fallback = _display_keys("_policy_part", "reason", "circles")
    response = _display_keys("_response_part", "request_id")
    usage = _display_keys("_response_part", "input_tokens")
    error = _display_keys("call", "provider", "kind", "status")
    for heading, after, expected in (
        ("### The payload", "The keys of the payload:", top),
        ("### The payload", "The entry of `task`:", task),
        ("### The payload", "An entry of `inputs`:", inputs),
        ("### The payload", "The entry of `policy`:", policy),
        ("### The payload", "The entry of `fallback`:", fallback),
        ("### The payload", "The entry of `response`:", response),
        ("### The payload", "The entry of `error`:", error),
    ):
        assert _policy_cells(heading, after) == expected, after
    assert usage == {"input_tokens", "output_tokens"}
    example = _json_block("A call that recorded an answer looks like this:")
    assert set(example) | {"error"} == top
    assert set(example["task"]) == task
    assert set(example["inputs"][0]) == inputs
    assert set(example["policy"]) == policy
    assert set(example["response"]) == response
    assert set(example["response"]["usage"]) == usage


def test_the_policy_reference_example_is_what_the_code_writes() -> None:
    """The example of a rule, whole: written again by `to_payload` from what
    it says, it is the same payload."""
    from previously.core.policy import Rule
    from previously.core.policy import to_payload

    example = _json_block("A rule written like this holds for content of the circle `xz`:")
    written = to_payload(
        Rule(
            "circle:xz",
            frozenset(example["regions"]),
            None,
            frozenset(example["excluded_providers"]),
            example["no_training"],
            example["no_subprocessors"],
            frozenset(example["excluded_operators"]),
            frozenset(example["excluded_model_origins"]),
        ),
        statement=example["statement"],
    )
    assert written == example


def test_the_policy_reference_holds_the_words_the_gate_writes() -> None:
    """The action names `verify` accepts, the outcomes, the alarm, the
    fallback reason and the reasons for a denial, as the code defines them."""
    from previously.core.action import KNOWN_ACTIONS
    from previously.core.action import OUTCOMES
    from previously.core.decide import NO_LOCAL_PROVIDER
    from previously.core.decide import NO_RULE
    from previously.gate.gate import ERASED
    from previously.gate.gate import GEO_MISMATCH
    from previously.gate.gate import NO_UNITS
    from previously.gate.gate import NOT_OBSERVATION
    from previously.gate.tasks.mail_overview import MailOverview

    page = POLICY_PAGE.read_text(encoding="utf-8")
    names = ("redaction", "policy", "model_call", "mcp_access", "vocabulary", "approval_class")
    assert set(KNOWN_ACTIONS) == set(names)
    listed = "`redaction`, `policy`, `model_call`, `mcp_access`, `vocabulary` and `approval_class`"
    assert f"exactly six names there: {listed}" in page
    assert _policy_cells("### The outcomes", "The outcome of a call is one of these:") == set(
        OUTCOMES
    )
    assert _policy_cells("### Alarms", "The alarms the gate raises:") == {GEO_MISMATCH}
    assert _policy_cells("### Reasons for a denial", "has one of these reasons:") == {
        NOT_OBSERVATION,
        ERASED,
        NO_UNITS,
    }
    assert _policy_cells("### Reasons for a denial", "under `local_only`, one more:") == {
        NO_LOCAL_PROVIDER
    }
    assert f"| `reason` | `{NO_RULE}`. |" in page
    assert _policy_cells("### The unit of an `ok` call", "with these keys:") == set(
        MailOverview.model_fields
    )


def test_the_reference_quotes_what_mcp_and_serve_say() -> None:
    """The two errors of `mcp`, the line and the two refusals of `serve`,
    and the sentence of a 401, as `cli.md` and `configuration.md` quote them,
    held against the code: the errors against what `cli.py` raises as
    `PreviouslyError`, the line against what it prints to standard error,
    and the 401 and both answers of the readiness probe against the
    constants the HTTP wrapper sends, whole."""
    from previously.mcp_server.auth import NOT_READY
    from previously.mcp_server.auth import READY
    from previously.mcp_server.auth import REFUSAL

    cli = ROOT / "src" / "previously" / "cli.py"
    raised = _raised_patterns(cli, "PreviouslyError")
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    quoted = _quoted_block(page, "and otherwise returns 2 with one of two sentences")
    assert len(quoted) == 2, quoted
    _assert_raised(quoted, raised, "PreviouslyError")
    address = _quoted_block(page, "without the address that took its place, are refused before")
    assert len(address) == 2, address
    _assert_raised(address, raised, "PreviouslyError")
    (line,) = _quoted_block(page, "On start it prints one line to standard error")
    assert any(_is_the_same_sentence(parts, line) for parts in _message_patterns(cli)), line
    assert _quoted_block(page, "and one sentence as its body") == [REFUSAL]
    assert _quoted_block(page, "with the status 503 and this body") == [NOT_READY]
    assert "with the status 200 and the body `" + READY + "`," in page

    configuration = (DOCS / "reference" / "configuration.md").read_text(encoding="utf-8")
    unset = _quoted_block(configuration, "and returns 2 when it's unset or empty")
    assert len(unset) == 1, unset
    _assert_raised(unset, raised, "PreviouslyError")
    # The address settings: both renamed hosts, and the refusal of each form.
    for after, count in (
        ("is set, it returns 2 with a sentence that names the new setting", 1),
        ("is set, `serve` returns 2 before it listens anywhere", 1),
        ("names the setting and the form, and quotes the value", 3),
    ):
        quoted = _quoted_block(configuration, after)
        assert len(quoted) == count, quoted
        _assert_raised(quoted, raised, "PreviouslyError")


# The reference of the MCP server quotes its instructions, an example page,
# the errors of a call and of one id, the reasons of a withheld event, the
# notes of a cut event, the footers, the text of both prompts and an access
# entry, and it names the tools with their arguments, the resource templates
# and the prompts. What can be produced without a database is produced: the
# instructions, the example page and the form of the access entry. The rest
# is matched against the static parts of the string literals of the module
# that builds it, as the sentences of the command line are above, and the
# names against the decorators of `mcp_server/server.py`.
MCP_PAGE = DOCS / "reference" / "mcp-tools.md"
MCP_PAGE_NAME = "mcp-tools.md"
MCP_DIR = ROOT / "src" / "previously" / "mcp_server"


def _mcp_page() -> str:
    return MCP_PAGE.read_text(encoding="utf-8")


def _mcp_block(after: str, language: str = "text") -> str:
    """The first code block in `language` after the sentence `after`."""
    page = _mcp_page()
    assert after in page, f"{MCP_PAGE_NAME} no longer carries the sentence {after!r}"
    return page.split(after, 1)[1].split(f"```{language}\n", 1)[1].split("\n```", 1)[0]


def _mcp_lines(after: str) -> list[str]:
    return [line for line in _mcp_block(after).splitlines() if line.strip()]


def _literal_patterns(module: str) -> list[list[str]]:
    """The static parts of every string literal of a module of the server
    that is no docstring, with at least ten characters of text; a module
    constant of the server interpolated into one counts as its text."""
    tree = ast.parse((MCP_DIR / module).read_text(encoding="utf-8"))
    docstrings = _docstrings(tree)
    constants = _module_strings(*(MCP_DIR / name for name in ("render.py", "read.py", "server.py")))
    found = [
        _static_parts(node, constants)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant | ast.JoinedStr) and id(node) not in docstrings
    ]
    return [parts for parts in found if len("".join(parts)) >= 10]


def _said(line: str, patterns: list[list[str]], what: str) -> None:
    assert any(_is_the_same_sentence(parts, line) for parts in patterns), (
        f"{MCP_PAGE_NAME} quotes {line!r} and {what} builds no such text. "
        "Either the code's wording changed, or the page's did."
    )


def _decorated(kind: str) -> dict[str, list[str]]:
    """The functions of `server.py` decorated with `server.<kind>(name=...)`,
    by that name, each with its parameters but `ctx`."""
    tree = ast.parse((MCP_DIR / "server.py").read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == kind
            ):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    arguments = [*node.args.args, *node.args.kwonlyargs]
                    found[str(keyword.value.value)] = [
                        argument.arg for argument in arguments if argument.arg != "ctx"
                    ]
    return found


def _section_cells(heading: str, end: str) -> set[str]:
    """The code spans in the first column of the tables between `heading`
    and the next heading that starts with `end`."""
    page = _mcp_page()
    assert heading in page, f"{MCP_PAGE_NAME} no longer has the section {heading!r}"
    section = page.split(heading, 1)[1].split(end, 1)[0]
    cells: set[str] = set()
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        first = line.strip("|").split("|", 1)[0].strip()
        cells.add(first[1:-1])
    return cells


def test_the_mcp_reference_quotes_the_instructions_whole() -> None:
    from previously.mcp_server.server import INSTRUCTIONS

    assert _mcp_block("It sends these instructions to every client:") == INSTRUCTIONS


def test_the_mcp_reference_example_page_is_what_the_renderer_lays_out() -> None:
    """The example, rendered again from the items its sentence names, with the
    tag the page shows: the same text, character for character."""
    from datetime import datetime
    from datetime import UTC
    from previously.mcp_server.render import encode_cursor
    from previously.mcp_server.render import ErasedMark
    from previously.mcp_server.render import Head
    from previously.mcp_server.render import render_page
    from previously.mcp_server.render import Shown
    from previously.mcp_server.render import WithheldMark

    block = _mcp_block("with one event shown, one withheld and one erased, and more to follow:")
    tag = re.search(r"<<<customer-content ([0-9a-f]{8})>>>", block)
    assert tag is not None, "the example shows no fence"
    filters = {"circle": "huber", "since": "2026-09-01"}
    head = Head(
        "previously://event/42",
        datetime(2026, 9, 12, 9, 14, tzinfo=UTC),
        "email",
        "Eva Huber",
        ("Jens Klein",),
        None,
    )
    units = (
        (1, "Re: server installation of the foobar connector"),
        (2, "The server is up; the TLS access is still missing. By Friday?"),
    )
    reason = (
        "circle team has no rule, so only local processing is allowed; "
        "this client (claude-code) processes with claude-max, which is not local"
    )
    items = [
        Shown(head, units),
        WithheldMark("previously://event/43", reason),
        ErasedMark("previously://event/44"),
    ]
    ids = [42, 43, 44]
    page = render_page(
        "chronicle · circle huber · since 2026-09-01",
        items,
        cursor_for=lambda index: encode_cursor(ids[index], filters, page=2),
        more=True,
        candidates=iter([tag.group(1)]),
    )
    assert page.text == block


def test_the_mcp_reference_quotes_what_the_server_says() -> None:
    """Every error, reason, note, footer and prompt text the page quotes is
    a text the module that builds it can produce."""
    server = _literal_patterns("server.py")
    read = _literal_patterns("read.py")
    render = _literal_patterns("render.py")
    for after in (
        "A call that fails as a whole answers with one sentence after `Error: `, such as these:",
        "An `event_id` that isn't a whole number in ASCII digits is refused:",
        "The refusals of the server are these, each with nothing written:",
    ):
        for line in _mcp_lines(after):
            prefix, _, message = line.partition(": ")
            assert prefix == "Error", f"{MCP_PAGE_NAME} quotes {line!r} without `Error: `"
            _said(message, server, "server.py")
    for line in _mcp_lines("An id that can't be served gets a line of its own"):
        prefix, _, rest = line.partition(": ")
        label, _, message = rest.partition(" — ")
        assert prefix == "Error", f"{MCP_PAGE_NAME} quotes {line!r} without `Error: `"
        assert re.fullmatch(r"previously://event/\d+|ids\[\d+\]", label), line
        _said(message, read, "read.py")
    for line in _mcp_lines("A note after its fence says where the rest is:"):
        _said(line, render, "render.py")
    for line in _mcp_lines("When more follows, the result ends with a footer:"):
        _said(line, render, "render.py")
        _, _, hint = line.partition(". More results: ")
        _said(hint, server + render, "neither server.py nor render.py")
    for after in (
        "`chronicle_summary` with `circle` set to `huber` and `since` set to `2026-09-01` returns:",
        "`whats_open` with `circle` set to `huber` returns:",
    ):
        (line,) = _mcp_lines(after)
        _said(line, server, "server.py")


def test_the_mcp_reference_quotes_the_refusals_of_a_handle_as_they_are_made() -> None:
    """The four refusals of a handle, made by `open_handle` itself and
    compared whole, in the order the page lists them: a seal of another key,
    another client, other statements, and a moment after the expiry."""
    from datetime import datetime
    from datetime import timedelta
    from datetime import UTC
    from previously.mcp_server.confirm import HANDLE_SECONDS
    from previously.mcp_server.confirm import HandleRefused
    from previously.mcp_server.confirm import open_handle
    from previously.mcp_server.confirm import seal

    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    key = b"k" * 32
    payloads = [{"assertion": "obligation"}]
    handle = seal(key, client="claude-code", payloads=payloads, now=now, nonce="n")
    made: list[str] = []
    for other_key, client, other_payloads, moment in (
        (b"q" * 32, "claude-code", payloads, now),
        (key, "vibe", payloads, now),
        (key, "claude-code", [{"assertion": "decision"}], now),
        (key, "claude-code", payloads, now + timedelta(seconds=HANDLE_SECONDS + 1)),
    ):
        with pytest.raises(HandleRefused) as refused:
            open_handle(other_key, handle, client=client, payloads=other_payloads, now=moment)
        made.append(f"Error: {refused.value}")
    assert _mcp_lines("A handle that doesn't let the call write is refused") == made


def test_the_mcp_reference_quotes_the_reasons_the_decision_builds() -> None:
    """The reasons of a withheld event, built by `decide` and `withholding`
    for the client and the circles the page names, and compared whole: a
    pattern of the f-string would hold the `rule` reason by its first
    thirteen characters, `the rules of `, and nothing after them."""
    from previously.core.decide import Candidate
    from previously.core.decide import decide
    from previously.core.policy import Circle
    from previously.core.policy import Client
    from previously.core.policy import Inference
    from previously.core.policy import Membership
    from previously.core.policy import Policy
    from previously.core.policy import Provider
    from previously.core.policy import Rule
    from previously.mcp_server.read import withholding

    us = frozenset({"us"})
    policy = Policy(
        circles={name: Circle(name) for name in ("bauer", "eva", "team")},
        memberships=(
            Membership("bauer", "@bauer.example"),
            Membership("eva", "eva@example.org"),
            Membership("team", "team@example.org"),
        ),
        own=(),
        rules={"circle:bauer": Rule("circle:bauer", frozenset({"eu"}), None, frozenset())},
        providers={
            "claude-max": Provider("claude-max", (Inference("us", us),), us, 30, False, False)
        },
        ids={},
    )
    client = Client("claude-code", "claude-max", "0" * 64)

    def reason(*addresses: str) -> tuple[str, str]:
        decision = decide(
            policy,
            identities=[{"address": address} for address in addresses],
            source=None,
            candidates=(Candidate(client.processor, "", None),),
        )
        assert decision.chosen is None
        return withholding(policy, client, decision)

    no_rule = [reason("team@example.org"), reason("eva@example.org", "team@example.org"), reason()]
    assert {code for code, _ in no_rule} == {"no_rule"}
    assert _mcp_lines("and the sentence is one of these:") == [line for _, line in no_rule]
    code, line = reason("lea@bauer.example")
    assert code == "rule"
    assert _mcp_lines("and the sentence ends in the reason the decision gives") == [line]


def test_the_mcp_reference_names_every_tool_template_and_prompt() -> None:
    """The tools with their arguments, the two templates and the prompts,
    against what `server.py` registers."""
    from previously.mcp_server.server import CHRONICLE_TEMPLATE
    from previously.mcp_server.server import EVENT_TEMPLATE

    page = _mcp_page()
    tools = _decorated("tool")
    tools_section = page.split("\n## Tools\n", 1)[1].split("\n## ", 1)[0]
    headings = set(re.findall(r"^### `([a-z_]+)`$", tools_section, re.MULTILINE))
    assert headings == set(tools), f"{MCP_PAGE_NAME} names the tools {headings}"
    for name, arguments in tools.items():
        cells = _section_cells(f"### `{name}`", "\n#")
        assert cells == set(arguments), f"{MCP_PAGE_NAME} gives {name} the arguments {cells}"
    assert _section_cells("## Resource templates", "\n## ") == {
        CHRONICLE_TEMPLATE,
        EVENT_TEMPLATE,
    }
    assert _section_cells("## Prompts", "\n## ") == set(_decorated("prompt"))


def test_the_mcp_reference_access_entry_has_the_form_verify_holds() -> None:
    """The example passes the check `verify` applies, and the two tables
    name exactly its keys and the keys of its call."""
    from previously.core.access import access_problem

    example = cast("dict[str, Any]", json.loads(_mcp_block("looks like this:", "json")))
    assert access_problem(example) is None
    page = _mcp_page()
    heading = "## The access entry `mcp_access`"
    assert _first_cells(page, heading, "The keys of the payload:", name=MCP_PAGE_NAME) == set(
        example
    )
    assert _first_cells(page, heading, "The entry of `call`:", name=MCP_PAGE_NAME) == set(
        example["call"]
    )


# --- the assertions section of cli.md -----------------------------------------------


def _assertions_section() -> str:
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    return page.split("\n## Assertions\n", 1)[1].split("\n(cli-mcp)=", 1)[0]


def test_the_assertions_reference_quotes_only_sentences_the_code_says() -> None:
    """Every `Error: ` the "Assertions" section of `cli.md` quotes, in a block
    or inline, is a message `cli.py` raises, one the write path in
    `core/assertions.py` refuses with, or, behind an option name, one that
    `core/assertion.py` returns; and the hint is the sentence `cli.py`
    builds. A sentence changed on the page alone, or in the code alone, fails.

    Measured on 2026-10-12: with `already approved` turned into `already
    answered` on the page, this test goes red; the unchanged page is the
    control. Patterns shorter than ten characters are left out, or the bare
    `{option}: {problem}` would stand in for any sentence with a colon.
    """
    section = _assertions_section()
    quoted = re.findall(r"^Error: (.+)$", section, re.MULTILINE)
    quoted += re.findall(r"`Error: ([^`]+)`", section)
    assert len(quoted) >= 8, quoted
    source = ROOT / "src" / "previously"
    own = [
        parts
        for parts in [
            *_raised_patterns(source / "cli.py", "PreviouslyError"),
            *_raised_patterns(source / "core" / "assertions.py", "AssertionRefused"),
        ]
        if len("".join(parts)) >= 10
    ]
    core = _message_patterns(source / "core" / "assertion.py")
    for sentence in quoted:
        behind_option = re.sub(r"^--[a-z-]+: ", "", sentence)
        assert any(_is_the_same_sentence(parts, sentence) for parts in own) or (
            behind_option != sentence
            and any(_is_the_same_sentence(parts, behind_option) for parts in core)
        ), f"cli.md quotes {sentence!r} and neither cli.py nor core/assertion.py says it"
    hints = re.findall(r"^hint: (.+)$", section, re.MULTILINE)
    assert len(hints) == 1
    code = (source / "cli.py").read_text(encoding="utf-8")
    assert hints[0].partition(" ")[2] in code.replace('"\n        "', "")


@pytest.mark.db
def test_the_assertions_reference_names_every_label_the_commands_print(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first word of every line of the page of an entry and of its
    history, and the seven fields of a list line, are named on the page. A
    label the code prints and the page leaves out fails; the page's `seven`
    is held against the list line the command prints."""
    from previously.cli import main

    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    decide = ["assert", "decision", "--what", "d", "--by", "own", "--on", "2026-10-30"]
    owe = ["assert", "obligation", "--debtor", "own", "--creditor", "name:x", "--what", "w"]
    run = [
        ["append", "--source", "s", "--external-id", "1", "--text", "One. Two."],
        [*owe, "--due", "2020-01-01", "--source", "1", "--yes"],
        ["assert", "obligation", "--subject", "2", "--state", "fulfilled", "--yes"],
        [*decide, "--source", "1", "--yes"],
        [*decide, "--source", "1", "--replaces", "4", "--yes"],
    ]
    for argv in run:
        assert main(argv) == 0
    _write_proposals(db)
    assert main(["reject", "6", "--reason", "no", "--yes"]) == 0
    assert main(["approve", "7", "--yes"]) == 0
    section = _assertions_section()
    prose = re.sub(r"```.*?```", "", section, flags=re.DOTALL)
    spans = set(re.findall(r"`([^`]+)`", prose))
    printed: set[str] = set()
    for argv in (
        ["obligation", "2"],
        ["obligation", "2", "--history"],
        ["decision", "4"],
        ["obligation", "6", "--history"],
    ):
        capsys.readouterr()
        assert main(argv) == 0
        for line in capsys.readouterr().out.splitlines():
            label = line.split("\t")[0]
            printed.add(
                label.split(" ")[0] if label.startswith(("obligation", "decision")) else label
            )
    for label in printed - {"obligation", "decision"}:
        base = label.removesuffix(" ID")
        assert any(span == base or span.startswith(base + " ") for span in spans), (
            f"the command prints the label {label!r} and the Assertions section names no `{label}`"
        )
    capsys.readouterr()
    assert main(["obligations"]) == 0
    fields = capsys.readouterr().out.splitlines()[0].split("\t")
    assert len(fields) == 7
    assert "Each line holds seven tab-separated fields" in section


def _write_proposals(db: Engine) -> None:
    from datetime import date
    from datetime import datetime
    from datetime import UTC
    from previously.core.assertion import model_author
    from previously.core.assertion import OBLIGATION
    from previously.core.assertion import ObligationBody
    from previously.core.assertion import OPEN
    from previously.core.assertion import Source
    from previously.core.assertion import Statement
    from previously.core.assertions import write_statements
    from previously.storage.postgres import PostgresStorage

    def proposal(what: str, subject: int | None) -> Statement:
        body = ObligationBody("own", "name:x", what, date(2026, 12, 1), "open")
        return Statement(
            OBLIGATION,
            model_author("claude-code"),
            OPEN,
            (Source(1, None),),
            None,
            None,
            subject,
            None,
            None,
            body,
        )

    storage = PostgresStorage(db)
    now = datetime(2026, 11, 1, tzinfo=UTC)
    write_statements(storage, storage, [proposal("p", None)], recorded_at=now)  # 6
    write_statements(storage, storage, [proposal("q", 2)], recorded_at=now)  # 7


def test_the_reference_quotes_the_findings_about_assertions() -> None:
    """The sixteen findings `verify` reports about an assertion, as `cli.md`
    quotes them under `verify`: each a reason `core/verify.py` gives, with the
    first fault of the form, behind `assertion has no valid form: `, held
    against the sentences `core/assertion.py` returns. Every finding the code
    gives about an assertion is quoted, so a new one fails here too.

    "Every finding" has three limits, all in how the code's side is
    collected. A reason counts only when it opens with one of the four
    words in `starts`: a new finding that opened with another would be
    missed, and the page could leave it out. A reason handed to `Finding`
    counts only as a plain string, so one with an interpolation would be
    missed the same way; the one there is, the fault of the form, is held
    against `core/assertion.py` instead. And a returned reason counts only
    from the three functions named below, which is why `_untaken` joined
    them on 2026-10-12, when the approval's content and author came to be
    compared there.

    Measured on 2026-10-12: `approval names no open proposal of its subject`
    turned into `... of its entry` on the page goes red, and so does a block
    with one line deleted; the unchanged page is the control.
    """
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    verify = ROOT / "src" / "previously" / "core" / "verify.py"
    literal = {parts[0] for parts in _finding_patterns(verify) if len(parts) == 1}
    returned = (
        _string_constants(verify, "_rejection")
        | _string_constants(verify, "_version")
        | _string_constants(verify, "_untaken")
    )
    forms = _message_patterns(ROOT / "src" / "previously" / "core" / "assertion.py")
    starts = ("assertion ", "approval ", "rejection ", "decision ")
    in_code = {text for text in literal | returned if text.startswith(starts)}
    form_prefix = "assertion has no valid form: "
    quoted: set[str] = set()
    lines = _quoted_block(page, "Sixteen findings come from assertions")
    assert len(lines) == 16, lines
    for line in lines:
        prefix, _, reason = line.partition(": ")
        assert re.fullmatch(r"FINDING [0-9]+", prefix), line
        if reason.startswith(form_prefix):
            problem = reason.removeprefix(form_prefix)
            assert any(_is_the_same_sentence(parts, problem) for parts in forms), (
                f"cli.md quotes the fault {problem!r}, which core/assertion.py never returns"
            )
            continue
        assert reason in in_code, (
            f"cli.md quotes the finding {reason!r} and core/verify.py gives no such reason"
        )
        quoted.add(reason)
    assert in_code == quoted, f"cli.md leaves out the findings {sorted(in_code - quoted)}"


def test_the_reference_quotes_the_findings_about_entities_and_relations() -> None:
    """The five findings `verify` reports about an entity or a relation alone,
    as `cli.md` quotes them under `verify` after the sixteen of every
    assertion: each a reason `_Claims.claim_reason` in `core/verify.py`
    returns, with the reason of the vocabulary, behind its prefix, held
    against the sentences `core/graph.py` returns. Every such reason the
    method returns is quoted, the ones already in the block of the sixteen
    aside, so a new one fails here too.

    The limits are those of the test above, with one function instead of
    three, and the openings `objection ` and `relation ` beside
    `assertion `.

    Measured on 2026-10-14: `relation closes a cycle over a kind that is
    acyclic` turned into `... an acyclic kind` on the page goes red, a block
    with one line deleted goes red, and so does the vocabulary reason with
    a sentence `core/graph.py` does not return; the unchanged page is the
    control.
    """
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    verify = ROOT / "src" / "previously" / "core" / "verify.py"
    common = {line.partition(": ")[2] for line in _quoted_block(page, "Sixteen findings come from")}
    starts = ("assertion ", "objection ", "relation ")
    returned = _string_constants(verify, "claim_reason")
    in_code = {text for text in returned if text.startswith(starts)} - common
    forms = _message_patterns(ROOT / "src" / "previously" / "core" / "graph.py")
    vocabulary_prefix = "assertion does not fit the vocabulary of its time: "
    quoted: set[str] = set()
    lines = _quoted_block(page, "Five more come from entities and relations alone")
    assert len(lines) == 5, lines
    for line in lines:
        prefix, _, reason = line.partition(": ")
        assert re.fullmatch(r"FINDING [0-9]+", prefix), line
        if reason.startswith(vocabulary_prefix):
            problem = reason.removeprefix(vocabulary_prefix)
            assert any(_is_the_same_sentence(parts, problem) for parts in forms), (
                f"cli.md quotes the reason {problem!r}, which core/graph.py never returns"
            )
            quoted.add(vocabulary_prefix)
            continue
        assert reason in in_code, (
            f"cli.md quotes the finding {reason!r} and core/verify.py gives no such reason"
        )
        quoted.add(reason)
    assert in_code == quoted, f"cli.md leaves out the findings {sorted(in_code - quoted)}"


ASSERTIONS_PAGE = DOCS / "reference" / "assertions.md"


def test_the_assertions_reference_names_every_key_of_the_payload() -> None:
    """The keys each table on `assertions.md` names, against the payload
    `payload_of` writes for an obligation, a decision and a rejection: the
    common keys, the two of a version, and the ones of each kind.

    Measured on 2026-10-12: the row of `handle` deleted from the page goes
    red; the unchanged page is the control.
    """
    from datetime import date
    from previously.core.assertion import DECISION
    from previously.core.assertion import DecisionBody
    from previously.core.assertion import DIRECT
    from previously.core.assertion import OBLIGATION
    from previously.core.assertion import ObligationBody
    from previously.core.assertion import OPERATOR
    from previously.core.assertion import payload_of
    from previously.core.assertion import REJECTION
    from previously.core.assertion import Source
    from previously.core.assertion import Statement

    def statement(kind: str, body: ObligationBody | DecisionBody | None) -> Statement:
        of = 9 if body is None else None
        return Statement(
            kind, OPERATOR, DIRECT, (Source(1, None),), None, None, None, None, of, body
        )

    obligation = set(
        payload_of(statement(OBLIGATION, ObligationBody("own", "own", "w", None, "open")))
    )
    decision = set(
        payload_of(
            statement(DECISION, DecisionBody("w", ("own",), date(2026, 1, 1), "valid", None))
        )
    )
    rejection = set(payload_of(statement(REJECTION, None)))
    page = ASSERTIONS_PAGE.read_text(encoding="utf-8")

    def cells(after: str) -> set[str]:
        return _first_cells(page, "## The payload", after, name="assertions.md")

    common = cells("Every kind has these keys:")
    version = cells("An obligation and a decision add")
    assert common == obligation & decision & rejection
    assert common | version | cells("An obligation adds:") == obligation
    assert common | version | cells("A decision adds:") == decision
    assert common | cells("A rejection adds:") == rejection
    assert not version & (cells("An obligation adds:") | cells("A decision adds:"))
    assert cells("An entry of `sources` holds:") == {"event", "units"}


def test_the_assertions_reference_examples_have_the_form_the_code_checks() -> None:
    """Each payload the page shows as an example is one `assertion_problem`
    finds no fault with, and the three are the three kinds.

    Measured on 2026-10-12: the `due` of the example written `30.11.2026`
    goes red; the unchanged page is the control.
    """
    from previously.core.assertion import assertion_problem
    from previously.core.assertion import KINDS

    page = ASSERTIONS_PAGE.read_text(encoding="utf-8")
    section = page.split("### Examples", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```json\n(.*?)\n```", section, re.DOTALL)
    examples = [cast("dict[str, object]", json.loads(block)) for block in blocks]
    assert [example["assertion"] for example in examples] == list(KINDS)
    for example in examples:
        assert assertion_problem(example) is None, (example, assertion_problem(example))


def test_the_assertions_reference_holds_the_limits_of_the_code() -> None:
    """The figures the page states, against the constants that set them: the
    length of a name and of an address, and the size of a batch on the write
    path and over MCP.

    Measured on 2026-10-12: `at most 254 characters` turned into `at most
    255` on the page goes red; the unchanged page is the control.
    """
    from previously.core.append import MAX_BATCH
    from previously.core.assertion import MAX_ADDRESS_LENGTH
    from previously.core.assertion import MAX_NAME_LENGTH
    from previously.mcp_server.server import MAX_STATEMENTS

    page = ASSERTIONS_PAGE.read_text(encoding="utf-8")
    for sentence in (
        f"has at most {MAX_ADDRESS_LENGTH} characters, exactly one `@`",
        f"`TEXT` has 1 to {MAX_NAME_LENGTH} characters",
        f"of 1 to {MAX_NAME_LENGTH} characters, without white space",
        f"One batch holds 1 to {MAX_BATCH} statements",
        f"Over MCP, one call holds 1 to {MAX_STATEMENTS}.",
    ):
        assert sentence in page, f"assertions.md no longer says {sentence!r}"
