# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Canonicalisation of payloads after RFC 8785, for a restricted range.

The permitted range is deliberately small ({ref}`payload-range`): no floating
point numbers, keys in ASCII lower case only, integers only inside the safe
range. That alone makes `json.dumps` with fixed flags JCS-conformant already,
and no foreign library is needed:

- `sort_keys=True` sorts by code point; with ASCII keys that is the same
  order as JCS' sorting by UTF-16 code units
- `separators=(",", ":")` removes every bit of whitespace
- `ensure_ascii=False` yields the UTF-8 representation with minimal escaping
  that JCS demands
- without floating point numbers the language-dependent rendering of numbers
  falls away, which is the hardest part of any canonicalisation

`_check` is the gate in front of `json.dumps`: whatever passes it is
serialisable. That is why it checks against the **concrete** types that
`json.dumps` handles (`dict`, `list`, `tuple`), not against the abstract
`Mapping`/`Sequence` — `bytes`, `bytearray` and `range` are `Sequence` but not
serialisable, and a foreign `Mapping` is not a `dict`.
"""

from previously.core.errors import InvalidPayload
from typing import cast
from typing import TYPE_CHECKING

import json
import re


if TYPE_CHECKING:
    from collections.abc import Mapping

MAX_SAFE_INT = 2**53 - 1
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _check(value: object, path: str) -> None:  # noqa: C901 — Recursive validation of several types requires several branches
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INT:
            raise InvalidPayload(
                f"{path}: integer outside the safe range "
                f"(±{MAX_SAFE_INT}) — not exact across languages"
            )
        return
    if isinstance(value, float):
        # The message says what the caller can do instead and nothing about
        # where that is written down: whoever runs `previously append` has no
        # specification at hand. Why floating point numbers are out at all —
        # their rendering is language-dependent, and a hash that comes out
        # differently per runtime is worthless — is in
        # {ref}`canonicalization`; {ref}`payload-range` lists the restriction
        # itself.
        raise InvalidPayload(
            f"{path}: floating point number not allowed — state a scale as an integer"
        )
    if isinstance(value, str):
        if "\x00" in value:
            raise InvalidPayload(
                f"{path}: null byte not allowed — PostgreSQL jsonb cannot store it"
            )
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise InvalidPayload(
                f"{path}: string not representable as UTF-8 "
                f"({error.reason}) — a lone UTF-16 surrogate, for instance"
            ) from error
        return
    if isinstance(value, dict):
        items = cast("dict[object, object]", value)
        for key, subvalue in items.items():
            if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
                raise InvalidPayload(f"{path}: key {key!r} must match {KEY_PATTERN.pattern}")
            _check(subvalue, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        members = cast("list[object] | tuple[object, ...]", value)
        for i, subvalue in enumerate(members):
            _check(subvalue, f"{path}[{i}]")
        return
    raise InvalidPayload(f"{path}: type {type(value).__name__} not allowed")


def canonical(payload: Mapping[str, object]) -> bytes:
    """The canonical JCS bytes of the payload. Raises `InvalidPayload`."""
    _check(payload, "$")
    text = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return text.encode("utf-8")
