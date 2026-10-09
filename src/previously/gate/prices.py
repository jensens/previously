# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The price file and the estimate of what a call cost.

The price file is TOML, read with `tomllib` from the standard library: the
date the prices were read, per model the price of a million input and a
million output tokens in US dollars, and per inference region the factor a
provider charges on top. A default lies in the package; `load_prices` takes
another path, and the command line passes the one `PREVIOUSLY_PRICES` names.

Every number is read as a `Decimal` and never as a float: the estimate goes
into the chain as a string of a decimal number, and the chain takes no
floating point ({ref}`payload-range`). It is an estimate. What a call cost
is what the provider bills, and a price file that nobody updated makes only
the estimate wrong, never the call.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from importlib import resources
from previously.core.errors import PreviouslyError
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import tomllib


if TYPE_CHECKING:
    from pathlib import Path


_MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class Prices:
    """A price file, read: when the prices were read, the SHA-256 of the file
    as it lay on disk, model → (input, output) per million tokens, and
    inference region → the factor on both."""

    as_of: date
    sha256: str
    table: Mapping[str, tuple[Decimal, Decimal]]
    surcharges: Mapping[str, Decimal]


class PricesUnreadable(PreviouslyError):
    """A price file that cannot be read: one sentence naming the file."""


def _number(value: object, where: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)
    raise PricesUnreadable(f"{where} is not a number")


def _table(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PricesUnreadable(f"{where} is not a table")
    return cast("dict[str, object]", value)


def _parse(data: bytes, name: str) -> Prices:
    try:
        document = tomllib.loads(data.decode("utf-8"), parse_float=Decimal)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise PricesUnreadable(f"the price file {name} is not TOML: {error}") from None
    as_of = document.get("as_of")
    if not isinstance(as_of, date):
        raise PricesUnreadable(f"the price file {name} has no date as_of")
    table: dict[str, tuple[Decimal, Decimal]] = {}
    for model, entry in _table(document.get("models", {}), f"{name}: models").items():
        fields = _table(entry, f"{name}: models.{model}")
        table[model] = (
            _number(fields.get("input"), f"{name}: models.{model}.input"),
            _number(fields.get("output"), f"{name}: models.{model}.output"),
        )
    surcharges = {
        geo: _number(factor, f"{name}: surcharges.{geo}")
        for geo, factor in _table(document.get("surcharges", {}), f"{name}: surcharges").items()
    }
    return Prices(as_of, hashlib.sha256(data).hexdigest(), table, surcharges)


def load_prices(path: Path | None = None) -> Prices:
    """The price file at `path`, or the one in the package without it.

    The SHA-256 is taken over the bytes as they lie on disk, so a
    `model_call` names exactly the file its estimate came from.
    """
    if path is None:
        data = resources.files("previously.gate").joinpath("prices.toml").read_bytes()
        return _parse(data, "in the package")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise PricesUnreadable(
            f"the price file {path} cannot be read: {error.strerror or error}"
        ) from None
    return _parse(data, str(path))


def estimate(
    prices: Prices,
    model: str,
    geo: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> str | None:
    """What a call cost by the price file, in US dollars, as a decimal
    string; `None` for a model the file does not price, or where the
    provider did not say how many tokens it counted.

    Exact, not rounded: a call of a few hundred tokens costs fractions of a
    cent, and a rounding to cents would make every one of them zero.
    """
    entry = prices.table.get(model)
    if entry is None or input_tokens is None or output_tokens is None:
        return None
    price_in, price_out = entry
    cost = (input_tokens * price_in + output_tokens * price_out) / _MILLION
    if geo is not None:
        cost *= prices.surcharges.get(geo, Decimal(1))
    return format(cost.normalize(), "f")
