# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from collections.abc import Iterator
from collections.abc import Mapping
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload

import json
import pytest


def test_key_order_does_not_matter() -> None:
    a = canonical({"b": 1, "a": 2})
    b = canonical({"a": 2, "b": 1})
    assert a == b
    assert a == b'{"a":2,"b":1}'


def test_no_whitespace() -> None:
    assert canonical({"a": [1, 2]}) == b'{"a":[1,2]}'


def test_utf8_is_not_escaped() -> None:
    assert canonical({"a": "naïve café"}) == '{"a":"naïve café"}'.encode()


def test_floating_point_number_rejected() -> None:
    with pytest.raises(InvalidPayload, match="floating point"):
        canonical({"confidence": 0.75})


def test_null_byte_rejected() -> None:
    """Review Focus 1: PostgreSQL jsonb cannot store \\u0000."""
    with pytest.raises(InvalidPayload, match="null byte"):
        canonical({"text": "before\x00after"})


def test_too_large_integer_rejected() -> None:
    """Review Focus 4: beyond 2^53-1 the number is not exact across languages."""
    with pytest.raises(InvalidPayload, match="safe range"):
        canonical({"n": 2**53})
    assert canonical({"n": 2**53 - 1}) == b'{"n":9007199254740991}'


def test_key_must_be_ascii_lower_case() -> None:
    # "must match" instead of "key" (finding N5): three of the five messages in
    # `canonical` carry the word "key" — the path fragment `$.<key>` carries it
    # for any payload with a key of that name as well — so "key" would stay
    # green on a quite different complaint. "must match" belongs to the key
    # pattern and to nothing else.
    with pytest.raises(InvalidPayload, match="must match"):
        canonical({"Naïve": 1})
    with pytest.raises(InvalidPayload, match="must match"):
        canonical({"camelCase": 1})


def test_permitted_types() -> None:
    assert (
        canonical({"a": None, "b": True, "c": 0, "d": "x", "e": [], "f": {}})
        == b'{"a":null,"b":true,"c":0,"d":"x","e":[],"f":{}}'
    )


def test_nested_values_are_checked_too() -> None:
    with pytest.raises(InvalidPayload, match="floating point"):
        canonical({"a": {"b": [1, 2.5]}})


def test_bool_is_not_int() -> None:
    """True must not be serialised as 1."""
    assert canonical({"a": True}) == b'{"a":true}'


def test_bytes_rejected() -> None:
    """bytes, bytearray and range are Sequence, but not JSON-serialisable."""
    with pytest.raises(InvalidPayload, match="type bytes"):
        canonical({"blob": b"abc"})
    with pytest.raises(InvalidPayload, match="type bytearray"):
        canonical({"blob": bytearray(b"abc")})
    with pytest.raises(InvalidPayload, match="type range"):
        canonical({"span": range(3)})
    # tuple is permitted and becomes an array
    assert canonical({"a": (1, 2)}) == b'{"a":[1,2]}'


def test_foreign_mapping_rejected() -> None:
    """json.dumps serialises only dict, not arbitrary Mapping implementations."""

    class ForeignMapping(Mapping[str, object]):
        def __init__(self, data: dict[str, object]) -> None:
            self._data = data

        def __getitem__(self, key: str) -> object:
            return self._data[key]

        def __iter__(self) -> Iterator[str]:
            return iter(self._data)

        def __len__(self) -> int:
            return len(self._data)

    # The type by name (finding N5): "not allowed" ends three different
    # messages in `canonical` — floating point number, null byte and
    # impermissible type — so it would stay green if a foreign Mapping were
    # turned down for one of the other two reasons.
    with pytest.raises(InvalidPayload, match="type ForeignMapping not allowed"):
        canonical({"map": ForeignMapping({"x": 1})})


def test_lone_surrogate_rejected() -> None:
    """A valid Python str can contain a UTF-16 surrogate."""
    lone = json.loads('{"text": "\\ud800"}')["text"]
    with pytest.raises(InvalidPayload, match="UTF-8"):
        canonical({"text": lone})


def test_key_with_line_break_rejected() -> None:
    """Regex match() ends before \\n, which is why fullmatch() has to force it."""
    with pytest.raises(InvalidPayload, match="must match"):
        canonical({"abc\n": 1})


def test_impermissible_type_rejected() -> None:
    """The catch-all branch for types that are not on the allow list."""
    with pytest.raises(InvalidPayload, match="type set not allowed"):
        canonical({"a": {1, 2}})
