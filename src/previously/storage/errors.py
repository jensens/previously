# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The error classes of the storage layer.

They deliberately inherit from `Exception`, not from
`previously.core.errors.PreviouslyError`: the layer contract (`core` above
`storage` above `contract`) forbids `storage` any import out of `core` — the
error root included.
"""


class StorageError(Exception):
    """Root of the storage errors."""


class ChainPositionTaken(StorageError):
    """The chain position was already taken.

    Two concurrent writers computed the same `id` and the same `prev_hash`
    from the same tip — and therewith, because both values go into the event
    hash, inevitably the same `hash` as well. Which of the three indexes
    (`event_pkey`, `event_prev_hash_idx`, `event_hash_idx`) fires first is
    undetermined; the recovery is the same one: re-read the tip and retry.
    """


class SourceKeyTaken(StorageError):
    """The source event was already recorded.

    Idempotency struck in the race. Do not retry; re-read `lookup` and return
    the existing identifier instead.
    """


class InvalidDsn(StorageError):
    """`PREVIOUSLY_DSN` is not a valid connection string (review finding W2).

    Translates `sqlalchemy.exc.ArgumentError` out of `create_engine`, which
    rejects the DSN while parsing it, before any connection attempt takes
    place at all.
    """


class ServerUnreachable(StorageError):
    """The database server does not answer (review finding W2).

    Translates `sqlalchemy.exc.OperationalError`, which arises while the
    connection is actually being established — the DSN was valid, but nobody
    answers at that address.
    """


class MigrationPending(StorageError):
    """The database schema is incomplete (review finding W2).

    Translates `sqlalchemy.exc.ProgrammingError`, which arises when something
    is written to or read from a table that `alembic upgrade head` has not
    created yet.
    """
