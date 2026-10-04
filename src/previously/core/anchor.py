# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Anchor lines: reading them and writing them ({ref}`external-anchor`).

Pure. No file, no database: the entry point reads the file and hands the
lines in, and a second entry point can hand in lines it got some other way.
"""

from previously.contract.types import Anchor
from previously.core.errors import InvalidPayload
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable

# `len(str(2**63 - 1))`: the largest `bigint`, which the `id` column is.
_MAX_ID_DIGITS = 19


def format_anchor(anchor: Anchor) -> str:
    """`<id> <hash>`, the hash in lower-case hex, no line end."""
    return f"{anchor.id} {anchor.hash.hex()}"


def parse_anchors(lines: Iterable[str]) -> tuple[Anchor, ...]:
    """Every anchor in `lines`, or `InvalidPayload` naming the first bad line.

    Blank lines and lines starting with `#` do not count, so that a file kept
    by hand can be annotated. Everything else that is not `<id> <hash>` is an
    error and not a line to skip: a check against half the anchors would look
    like a check against all of them. For the same reason a file without a
    single anchor is an error too.
    """
    anchors: list[Anchor] = []
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 2:
            raise InvalidPayload(
                f"anchor line {number}: expected `<id> <hash>`, got {len(fields)} fields"
            )
        id_text, hash_text = fields
        # The length before `int()`, for the same reason as `isascii` below:
        # beyond 4300 digits `int()` raises a `ValueError` nobody translated.
        # 19 digits is the length of the largest `bigint`, so no event `id`
        # is longer; the digits are not echoed, a damaged file can hold
        # thousands of them.
        if len(id_text) > _MAX_ID_DIGITS:
            raise InvalidPayload(
                f"anchor line {number}: the id has more than {_MAX_ID_DIGITS} digits, "
                "longer than any event id"
            )
        # `isascii` first: `str.isdigit()` is true for `²`, and `int()` then
        # raises a `ValueError` nobody translated.
        if not (id_text.isascii() and id_text.isdigit() and int(id_text) >= 1):
            raise InvalidPayload(
                f"anchor line {number}: the id has to be a positive integer, got {id_text!r}"
            )
        if len(hash_text) != 64:
            raise InvalidPayload(
                f"anchor line {number}: the hash has to be 64 hex characters, got {len(hash_text)}"
            )
        try:
            digest = bytes.fromhex(hash_text)
        except ValueError:
            raise InvalidPayload(f"anchor line {number}: the hash is not hexadecimal") from None
        anchors.append(Anchor(int(id_text), digest))
    if not anchors:
        raise InvalidPayload("the input holds no anchor")
    return tuple(anchors)
