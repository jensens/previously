# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Where the built-in rule `local_only` acted: the circles and sources whose
calls fell back, with how often and when last.

A read over the `model_call` events and nothing else, no table: a call under
the built-in rule carries `policy.fallback`, with the circles that had no
rule, or with none when no rule applied at all. In that second case it is the
source of the event the call read that has no rule, and the source is not in
the payload; it is read from the source key of that event. A local model on
CPU is weaker than the ones a rule would allow, and one call that fell back
is seen by whoever runs it; a hundred calls of a batch are seen by nobody
but this list.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.core.action import MODEL_CALL
from typing import cast
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import LogStore


@dataclass(frozen=True)
class Gap:
    """A scope without a rule, as `circle:<name>` or `source:<source>`, or
    `event:<id>` for a call over an event with no source; how many calls
    fell back for it, and the `recorded_at` of the last."""

    what: str
    count: int
    last: datetime


def _input_event(payload: Mapping[str, object]) -> int | None:
    inputs = payload.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        return None
    first = cast("list[object]", inputs)[0]
    if not isinstance(first, Mapping):
        return None
    event = cast("Mapping[str, object]", first).get("event")
    return event if isinstance(event, int) and not isinstance(event, bool) else None


def gaps[Conn](log: LogStore[Conn], conn: Conn, *, since: datetime | None) -> list[Gap]:
    """Every scope that fell back, at or after `since` (all time without
    it), sorted by name. An erased `model_call` counts for nothing: its
    payload, and with it the fallback, is gone."""
    fell_back: list[tuple[datetime, tuple[str, ...], int | None]] = []
    for row in log.read_by_kind(conn, "action"):
        payload = row.payload
        if payload is None or payload.get("action") != MODEL_CALL:
            continue
        if since is not None and row.recorded_at < since:
            continue
        policy = payload.get("policy")
        if not isinstance(policy, Mapping):
            continue
        fallback = cast("Mapping[str, object]", policy).get("fallback")
        if not isinstance(fallback, Mapping):
            continue
        circles = cast("Mapping[str, object]", fallback).get("circles")
        names = tuple(
            name
            for name in (cast("list[object]", circles) if isinstance(circles, list) else [])
            if isinstance(name, str)
        )
        fell_back.append((row.recorded_at, names, _input_event(payload)))

    sources = log.source_keys(
        conn, sorted({event for _, names, event in fell_back if not names and event is not None})
    )
    found: dict[str, Gap] = {}
    for recorded_at, names, event in fell_back:
        if names:
            scopes = [f"circle:{name}" for name in names]
        elif event is not None and event in sources:
            scopes = [f"source:{sources[event][0]}"]
        else:
            scopes = [f"event:{event}"]
        for scope in scopes:
            known = found.get(scope)
            found[scope] = (
                Gap(scope, 1, recorded_at)
                if known is None
                else Gap(scope, known.count + 1, max(known.last, recorded_at))
            )
    return [found[scope] for scope in sorted(found)]
