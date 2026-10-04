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

from typing import TYPE_CHECKING

import ast
import pathlib
import re


if TYPE_CHECKING:
    from collections.abc import Mapping

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["src", "tests", "migrations"]

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


def _quoted_block(page: str, after: str) -> list[str]:
    """The lines of the first `text` block after the sentence `after`."""
    assert after in page, f"cli.md no longer carries the sentence {after!r}"
    rest = page.split(after, 1)[1]
    block = rest.split("```text", 1)[1].split("```", 1)[0]
    return [line for line in block.splitlines() if line.strip()]


def _static_parts(node: ast.expr) -> list[str]:
    """What stays of a string literal once the interpolations are taken out.

    A plain literal is one part, an f-string is its `Constant` values in
    order. Only the direct children of the `JoinedStr` count: a literal
    nested inside an interpolation -- `_plural(lag, 'event')` is the case in
    this tree -- is an argument, not text of the message.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else []
    if isinstance(node, ast.JoinedStr):
        parts = [
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ]
        if not "".join(parts):
            return []
        # An interpolation at either end becomes an empty part there, so that
        # `_is_the_same_sentence` lets the line open or close with whatever
        # was interpolated: `f"there is no event {event_id}"` ends in a number,
        # not in `event `. Measured on 2026-10-04, when `redact` brought the
        # first quoted messages that end in an interpolation and the check
        # refused every one of them.
        if not isinstance(node.values[0], ast.Constant):
            parts.insert(0, "")
        if not isinstance(node.values[-1], ast.Constant):
            parts.append("")
        return parts
    return []


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

    The second half holds the five standard-error sentences and the two
    lines of `redact` on standard output that `cli.md` quotes, in five
    blocks, against the literals in `cli.py`; the five refusals of `redact`
    against the messages `core/redact.py` and `cli.py` raise as
    `RedactionRefused`; and the twelve findings it quotes, three from the
    anchors and nine from the hash formats and erasure, against the reasons
    `core/verify.py` hands to `Finding`. The first two sentences were quoted and covered by nothing
    until 2026-10-04: the first half of this test reads the *Payload range*
    table and nothing else, and the command line's notices reach no other
    check. They cannot be produced by calling the code the way a refusal can
    — the truncation sentence needs a cut window and the lag sentence a
    projection that is behind — so this half matches the page's line against
    the message's static parts instead, which is the strongest form available
    without a database.

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
        ("`redact` prints one of two lines to standard output", 2),
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
    quoted = _quoted_block(page, "Five refusals")
    assert len(quoted) == 5, quoted
    for line in quoted:
        prefix, _, refusal = line.partition(": ")
        assert prefix == "Error", f"cli.md quotes the refusal {line!r} without `Error: `"
        assert any(_is_the_same_sentence(parts, refusal) for parts in refusals), (
            f"cli.md quotes the refusal {refusal!r} and no `RedactionRefused` raises it. "
            "Either the code's wording changed, or the page's did."
        )

    reasons = _finding_patterns(ROOT / "src" / "previously" / "core" / "verify.py")
    findings = [
        *_quoted_block(page, "Three findings come from the anchors"),
        *_quoted_block(page, "Nine findings come from the hash formats and from erasure"),
    ]
    assert len(findings) == 12, findings
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
