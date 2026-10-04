# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The store protocols: what `core` may ask of a store, and nothing more.

`LogStore` is what `append` and `verify` call — eight methods, read off
`storage/postgres.py` on 2026-10-04 with
`grep -o 'storage\\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py`,
not copied from the method list of the implementation. Typing `core` against
this protocol instead of against `PostgresStorage` removes the edge
`core -> storage.postgres`, and with it the two named exemptions in
`.importlinter` and the test that guarded them ({ref}`module-boundaries`).

`Conn` is the connection type. Only `storage` knows what it is; `core` passes
it back to the store it came from and never looks inside.

Nothing imports this module at runtime, and the coverage report says so: both
importers name `LogStore` only under `TYPE_CHECKING`, so the module never
reaches `sys.modules` and stands at 0%. Measured on 2026-10-04 by importing
`previously.cli`, `core.append` and `core.verify` and looking. That is the
protocol working as intended rather than something left untested — the method
bodies are `...` and have nothing to execute; what has to hold is that
`PostgresStorage` satisfies the protocol, and pyright checks that at every
call site ({ref}`module-boundaries`).
"""

from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence
    from contextlib import AbstractContextManager
    from previously.contract.rows import EventRow
    from previously.contract.rows import Tip
    from previously.contract.rows import UnitRow


class LogStore[Conn](Protocol):
    """The append-only log: write once, read in chain order, never change."""

    def begin(self) -> AbstractContextManager[Conn]: ...
    def tip(self, conn: Conn) -> Tip | None: ...
    def lookup(self, conn: Conn, source: str, external_id: str) -> int | None: ...
    def insert_event(
        self,
        conn: Conn,
        row: EventRow,
        units: Sequence[UnitRow],
        key: tuple[str, str] | None,
    ) -> None: ...
    def read(self, conn: Conn, from_id: int, limit: int) -> Iterator[EventRow]: ...
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
