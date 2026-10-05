# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The error classes of the core."""


class PreviouslyError(Exception):
    """Root of every error of this project."""


class InvalidPayload(PreviouslyError, ValueError):
    """A payload violates the rules of {ref}`payload-range`."""


class ChainConflict(PreviouslyError):
    """The chain position could not be acquired after all attempts.

    Raised only once the retries are exhausted — the ordinary conflict is
    handled inside `append` and never handed outwards. Inherits from
    `PreviouslyError` so that the command line shows a message instead of a
    stack trace.
    """


class BatchTooLarge(PreviouslyError, ValueError):
    """Too many events in one transaction ({ref}`concurrency`).

    A very large transaction holds for a long time and loses the conflict
    against every small submission that commits meanwhile — starvation.
    """


class ProjectionGap(PreviouslyError):
    """The log has a gap above `up_to_id` — which {ref}`projections` says it
    cannot have: `id = predecessor.id + 1` and the unique index on `prev_hash`
    leave no room for one. Raised rather than skipped over, because a worker
    that silently moved past a gap would turn an impossible state into a
    silent loss.

    The check compares the identifiers the batch read with the run that has to
    start at `up_to_id + 1`. The first version checked the read for emptiness
    instead, and that check was measured on 2026-10-04 to be unable to fire
    for any gap at all: the tip is itself a row with
    `id >= up_to_id + 1` and `read` filters on `id >= from_id`, so the result
    is empty only for a `batch_size` below one. With id 5 deleted by hand at
    `up_to_id` 4 the worker projected 6 to 10 and stored `up_to_id = 10` —
    exactly what this type says it refuses.
    """


class RedactionRefused(PreviouslyError):
    """An erasure that cannot be carried out as asked ({ref}`erasure`).

    Raised before anything is written: the target does not exist, is itself a
    redaction, names a unit it does not have, or was written in a hash format
    that cannot attest part of its units. The command line shows the one
    sentence and returns 2, like every other `PreviouslyError`.
    """


class BlobError(PreviouslyError):
    """Root of what can go wrong between a content and its sealed object
    ({ref}`blobs`). Raised as itself when `pyrage` refuses to seal, which it
    does when the source breaks off while it is being read.

    No message of this family names an identity: an identity is the secret
    half of a key, and a message ends up on a terminal and in a log.
    """


class InvalidKey(BlobError, ValueError):
    """A recipient or an identity is not an age X25519 key.

    A malformed recipient is named in the message, since a recipient is
    public. A malformed identity is not: what stands in its place may be a
    real identity with a typo in it.
    """


class CannotOpen(BlobError):
    """A sealed object cannot be opened: it names no key, no identity for its
    key is at hand, the identity belongs to another key, or `age` refuses it
    — the wrong identity, or bytes that are not an age file."""


class SourceUnreadable(BlobError):
    """The content to be stored could not be read: the source raised an
    `OSError` while it was hashed or sealed. `reason` is the system's
    description of the failure, which a caller that knows the source's name
    puts beside it; the source itself says nothing about its name."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"the content cannot be read: {reason}")
        self.reason = reason


class AddressMismatch(BlobError):
    """An object opened, and its plaintext is not the content its address
    names. The bytes written so far are to be thrown away."""
