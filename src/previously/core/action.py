# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The write path every action of the system takes.

An action is something the system does, not something a source reported: the
kind `action`, with the name of what kind of action it is in `payload.action`.
It carries no source key, because nothing outside the system reported it, and
its `occurred_at` is `recorded_at`, because an action happens when it is
recorded. It may carry units: a model call keeps the answer it received as
units, so that an erasure can take them out one by one.

`write_action` appends on the tip inside the transaction of the caller, for an
action that has to be written together with something else (a redaction with
its tombstones, {ref}`erasure`). `append_action` opens a transaction of its
own and retries a lost chain position the way `append` does
({ref}`concurrency`).

`KNOWN_ACTIONS` is the list of names `verify` accepts. A name outside it is a
finding: an action nobody here knows how to read cannot be told from a
forgery.
"""

from previously.core.append import backoff_delay
from previously.core.append import MAX_RETRIES
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.errors import ChainConflict
from previously.core.hashing import iso_utc
from previously.storage.errors import ChainPositionTaken
from typing import TYPE_CHECKING

import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.store import LogStore
    from previously.contract.types import RawUnit


REDACTION = "redaction"
POLICY = "policy"
MODEL_CALL = "model_call"

KNOWN_ACTIONS: frozenset[str] = frozenset({REDACTION, POLICY, MODEL_CALL})

_KIND = "action"


def write_action[Conn](
    log: LogStore[Conn],
    conn: Conn,
    payload: Mapping[str, object],
    units: Sequence[RawUnit],
    *,
    recorded_at: datetime,
) -> int:
    """Appends the action on the tip, inside the transaction of the caller,
    and returns its `id`.

    Prepared here, on every attempt, and not once before the first as
    `append` does: what an action names can depend on what the caller read
    under a lock, and that can differ between two attempts.
    """
    prepared = prepare(kind=_KIND, occurred_at=recorded_at, payload=payload, units=units, key=None)
    tip = log.tip(conn)
    row, linked = link(
        prepared,
        event_id=1 if tip is None else tip.id + 1,
        prev_hash=None if tip is None else tip.hash,
        recorded_at=recorded_at,
    )
    log.insert_event(conn, row, linked, None)
    return row.id


def retrying[Conn, T](log: LogStore[Conn], once: Callable[[Conn], T]) -> T:
    """Runs `once` in a transaction of its own until it gets a chain position.

    The policy is `append`'s ({ref}`concurrency`): a lost chain position rolls
    the transaction back and the next attempt starts again from the top.
    Every other error rolls back as well and is not retried.
    """
    for attempt in range(MAX_RETRIES):
        try:
            with log.begin() as conn:
                return once(conn)
        except ChainPositionTaken:
            time.sleep(backoff_delay(attempt))
    raise ChainConflict(
        f"chain position not acquired after {MAX_RETRIES} attempts — "
        "under lasting contention the answer would be a single writing "
        "process, not a lock"
    )


def append_action[Conn](
    log: LogStore[Conn],
    payload: Mapping[str, object],
    units: Sequence[RawUnit],
    *,
    recorded_at: datetime,
) -> int:
    """Appends one action in a transaction of its own and returns its `id`."""
    iso_utc(recorded_at)  # fail early if naive
    return retrying(
        log, lambda conn: write_action(log, conn, payload, units, recorded_at=recorded_at)
    )
