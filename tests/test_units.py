# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from previously.core.errors import InvalidPayload
from previously.core.units import split_plaintext

import pytest


def test_a_single_paragraph() -> None:
    units = split_plaintext("Hello world")
    assert len(units) == 1
    assert units[0].seq == 1
    assert units[0].content == "Hello world"


def test_two_paragraphs_separated_by_a_blank_line() -> None:
    units = split_plaintext("first\n\nsecond")
    assert [(u.seq, u.content) for u in units] == [(1, "first"), (2, "second")]


def test_several_blank_lines_separate_just_the_same() -> None:
    units = split_plaintext("a\n\n\n\nb")
    assert [u.content for u in units] == ["a", "b"]


def test_whitespace_at_the_edges_is_stripped() -> None:
    units = split_plaintext("  a  \n\n\t b \t")
    assert [u.content for u in units] == ["a", "b"]


def test_a_line_break_within_a_unit_stays() -> None:
    units = split_plaintext("a\nb\n\nc")
    assert [u.content for u in units] == ["a\nb", "c"]


def test_numbering_starts_at_one_and_has_no_gaps() -> None:
    units = split_plaintext("a\n\nb\n\nc")
    assert [u.seq for u in units] == [1, 2, 3]


def test_empty_text_rejected() -> None:
    """Review Focus 2: an event without units is pointless."""
    with pytest.raises(InvalidPayload, match="no units"):
        split_plaintext("")


def test_whitespace_only_rejected() -> None:
    """Review Focus 2, variant."""
    with pytest.raises(InvalidPayload, match="no units"):
        split_plaintext("   \n\n \t \n ")


def test_splitting_is_deterministic() -> None:
    text = "a\n\n  b  \n\n\nc"
    assert split_plaintext(text) == split_plaintext(text)


def test_crlf_separates() -> None:
    """RFC 5322 prescribes CRLF — e-mail is the first planned source."""
    units = split_plaintext("first\r\n\r\nsecond")
    assert [u.content for u in units] == ["first", "second"]


def test_crlf_and_lf_yield_the_same() -> None:
    """The source's choice of line endings must not change the hash."""
    assert split_plaintext("a\r\n\r\nb") == split_plaintext("a\n\nb")


def test_a_lone_cr_separates() -> None:
    units = split_plaintext("a\r\rb")
    assert [u.content for u in units] == ["a", "b"]


def test_cr_does_not_stay_in_the_content() -> None:
    """A break within a unit is kept, but as `\\n`, not as `\\r\\n`."""
    units = split_plaintext("a\r\nb\n\nc")
    assert [u.content for u in units] == ["a\nb", "c"]
