# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projections: derived, disposable views over the log ({ref}`projections`)."""

from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.source_stats import SOURCE_STATS
from previously.core.projection.worker import Batch
from previously.core.projection.worker import catch_up
from previously.core.projection.worker import Outcome
from previously.core.projection.worker import Projection


# Every projection the command line catches up, in this order.
PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)

__all__ = ["CHRONICLE", "PROJECTIONS", "SOURCE_STATS", "Batch", "Outcome", "Projection", "catch_up"]
