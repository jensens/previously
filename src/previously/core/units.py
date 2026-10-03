# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mechanical splitting of content into units ({ref}`hash-chain`).

Mechanical and deterministic, not interpreting: no language detection, no
attribution, no classification. Those are assertions and come later.

Further media bring their own documented rule along.
"""

from previously.contract.types import RawUnit
from previously.core.errors import InvalidPayload

import re


_SEPARATOR = re.compile(r"\n[ \t]*\n[\s]*")


def split_plaintext(text: str) -> tuple[RawUnit, ...]:
    """Plain text: split at blank lines, strip the edges, number from 1.

    Line endings are normalised to `\\n` before the split — first the pair
    `\\r\\n`, then the single `\\r`. Without that it would hit the most
    important source first: RFC 5322 prescribes CRLF for e-mail, and
    `_SEPARATOR` knows of no `\\r` between the two `\\n`, so a whole mail text
    would arrive as a single unit. And were the `\\r` additionally left
    standing in the content, the same text with LF and with CRLF endings would
    yield different contents and therefore different hashes.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = (part.strip() for part in _SEPARATOR.split(normalized))
    units = tuple(RawUnit(seq=i, content=part) for i, part in enumerate((p for p in parts if p), 1))
    if not units:
        raise InvalidPayload("input yields no units — empty or whitespace only")
    return units
