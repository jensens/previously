# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The connector protocol: what `core` may ask of a source of foreign data,
and nothing more.

A connector takes in and does not interpret. It reads from its source and
hands over bytes with the position they stand at; turning the bytes into an
event is `core`'s job, and remembering how far it got is the watermark's.
"""

from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator
    from previously.contract.types import Fetched
    from previously.contract.types import Watermark


class Connector(Protocol):
    """A source of foreign data that can be read from where it was left.

    `name` is the key of the connector's watermark. `fetch` yields what is
    new since `since`, oldest first, or everything the source holds when
    `since` is `None`. Each `Fetched` carries the position that stands once
    it is taken in, so that a caller who stops after any piece can write that
    piece's position as the watermark and lose nothing.
    """

    name: str

    def fetch(self, since: Watermark | None) -> Iterator[Fetched]: ...
