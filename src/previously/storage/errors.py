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
    """Connecting to the database failed (review finding W2).

    Translates `sqlalchemy.exc.OperationalError`, which arises while the
    connection is actually being established — the DSN was valid, and nobody
    answers at that address, or the server answers and refuses: a wrong
    password, a database that does not exist. The message quotes libpq's
    first line, which says which, and never the password.
    """


class TransactionAborted(StorageError):
    """The database aborted a transaction because of a concurrent one: a
    deadlock or a serialization failure (SQLSTATE class 40), or a lock it
    could not get in time (`55P03`).

    Translates the `sqlalchemy.exc.OperationalError` that carries one of
    those states. Nothing was committed by the aborted transaction, and the
    same command run again starts it afresh; the server answered, so
    `ServerUnreachable` would send the operator to the wrong place.
    """


class MigrationPending(StorageError):
    """The database schema is incomplete (review finding W2).

    Translates `sqlalchemy.exc.ProgrammingError`, which arises when something
    is written to or read from a table that `previously migrate` has not
    created yet.
    """


class MigrationFailed(StorageError):
    """The database refused a step of `previously migrate`: reading the
    revision it is at, or applying a revision.

    Translates every `sqlalchemy.exc.DBAPIError` that arises there but an
    `OperationalError`, which stays a failure to connect: a role without the
    right to create a table or to read `alembic_version`, an event trigger
    that refuses DDL. It is not `MigrationPending`: the schema may well be
    missing, but the cause is the database's answer, and the message names
    that answer, never the connection string.
    """


class UnknownRevision(StorageError):
    """The database is at a schema revision this version of previously does
    not know.

    An older package against a database that a newer one has migrated
    already. Doing nothing would leave the old code working against a schema
    it was not written for, and Alembic itself would stop at the unknown
    revision with a traceback; this says what was found and what is known,
    and `migrate` touches nothing.
    """


class BlobStoreUnreachable(StorageError):
    """The blob store does not answer, or broke off while it was sending.

    Translates the `botocore` errors about a connection: no connection, a
    connect or read timeout, a connection that closed, a stream that broke
    off or ended before its length. The message names the endpoint, never
    the credentials.
    """


class BlobStoreRefused(StorageError):
    """The blob store answered and refused — wrong credentials, a bucket
    that does not exist, a request it does not allow — or the settings are
    such that the client will not send the request at all.

    Translates every `botocore.exceptions.ClientError` that does not mean
    "no such object", and every other `BotoCoreError` that `botocore` does
    not file under a connection, such as `ParamValidationError`. The message
    names the endpoint, the bucket and the store's code or the error's
    class, never the credentials.
    """


class IdentityUnreadable(StorageError):
    """A file in the key directory is there and cannot be read — no
    permission, a directory in its place, bytes that are not text.

    Distinct from a missing identity, which is `None`: this one is a fault in
    the key directory that an operator has to fix. The message names the
    path and the kind of failure, never what the file holds.
    """
