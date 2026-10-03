# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The connector contract as pure types. No logic, no dependencies."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Evidence(StrEnum):
    """Quality of evidence: the verbatim wording, or a report from memory."""

    VERBATIM = "verbatim"
    RECOLLECTION = "recollection"


@dataclass(frozen=True)
class RawUnit:
    seq: int
    content: str
    start_ms: int | None = None
    end_ms: int | None = None
    speaker: str | None = None


@dataclass(frozen=True)
class RawEvent:
    source: str
    external_id: str
    occurred_at: datetime
    evidence: Evidence
    units: tuple[RawUnit, ...]
    # dict[str, object], not a bare dict: pyright (strict) would otherwise
    # infer dict[Unknown, Unknown], because with a bare `dict` the type
    # parameter is not carried over from the annotation. The generic alias is
    # callable and produces the origin type — no difference in behaviour.
    payload: Mapping[str, object] = field(default_factory=dict[str, object])
