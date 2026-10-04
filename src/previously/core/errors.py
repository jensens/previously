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
