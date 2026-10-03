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
