# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection worker ({ref}`projections`): batches, and the catch-up."""

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from previously.contract.rows import EventRow
from previously.contract.rows import UnitRow


@dataclass(frozen=True)
class Batch:
    """What one catch-up step reads from the log: a run of events in chain
    order with their units and source attributions, fetched by batch — one
    query each, not one per event, for the reason `units_by_event` and
    `source_keys` exist."""

    events: tuple[EventRow, ...]
    units: Mapping[int, Sequence[UnitRow]]
    keys: Mapping[int, tuple[str, str]]
