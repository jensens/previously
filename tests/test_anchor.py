# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading and writing anchor lines ({ref}`external-anchor`), without a database."""

from previously.contract.types import Anchor
from previously.core.anchor import format_anchor
from previously.core.anchor import parse_anchors
from previously.core.errors import InvalidPayload

import pytest
import re


HASH = "ab" * 32


def test_an_anchor_survives_the_round_trip() -> None:
    anchor = Anchor(42, bytes.fromhex(HASH))
    assert format_anchor(anchor) == f"42 {HASH}"
    assert parse_anchors([format_anchor(anchor)]) == (anchor,)


def test_reading_tolerates_comments_blank_lines_case_and_whitespace() -> None:
    """What a file kept by hand looks like: a comment above, a blank line, a
    hash somebody pasted in upper case, a tab instead of a space, a line end
    from another system."""
    lines = [
        "# kept outside the database\n",
        "\n",
        f"1 {HASH}\n",
        f"  2\t{HASH.upper()}\r\n",
        "   ",
    ]
    assert parse_anchors(lines) == (
        Anchor(1, bytes.fromhex(HASH)),
        Anchor(2, bytes.fromhex(HASH)),
    )


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (f"1 {HASH} extra", "expected `<id> <hash>`"),
        ("1", "expected `<id> <hash>`"),
        (f"0 {HASH}", "positive integer"),
        (f"-3 {HASH}", "positive integer"),
        (f"² {HASH}", "positive integer"),
        pytest.param(f"{'9' * 5000} {HASH}", "more than 19 digits", id="5000-digit-id"),
        (f"1 {HASH[:-1]}", "64 hex characters"),
        (f"1 {'zz' * 32}", "not hexadecimal"),
    ],
)
def test_a_broken_line_is_refused_with_its_line_number(line: str, message: str) -> None:
    """A damaged file is not read by halves ({ref}`external-anchor`): a check
    against some of the anchors would look like a check against all of them.
    The `²` case pins that a digit outside ASCII is refused as a bad id and
    not let through to a `ValueError`: `str.isdigit()` takes it for a number
    and `int()` does not (review focus 5 of the 2026-10-04 external-anchor
    plan). The 5000 digits pin the same for a different `ValueError`, the one
    `int()` raises beyond its digit limit, and the length bound on the
    message pins that a damaged line is not echoed back whole."""
    with pytest.raises(InvalidPayload, match=re.escape(message)) as caught:
        parse_anchors([f"1 {HASH}", line])
    assert "anchor line 2" in str(caught.value)
    assert len(str(caught.value)) < 100


@pytest.mark.parametrize("lines", [[], ["", "# only a comment", "   "]])
def test_a_file_without_an_anchor_is_refused(lines: list[str]) -> None:
    """`chain intact, 0 anchors hold` would be the weak statement dressed as
    the strong one."""
    with pytest.raises(InvalidPayload, match=r"^the input holds no anchor$"):
        parse_anchors(lines)
