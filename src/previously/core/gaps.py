# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Where the built-in rule `local_only` acted: the circles and sources whose
calls fell back, with how often and when last.

A read over the `model_call` events, no table: a call under the built-in
rule carries `policy.fallback`, with the circles of the content that had no
rule, or with none where the content belongs to no circle and no rule
applied. In that second case it is the source of the event the call read that
has no rule, and the source is not in the payload; it is read from the source
key of that event, which is all this reads beside the calls. A local model on
CPU is weaker than the ones a rule would allow, and one call that fell back
is seen by whoever runs it; a hundred calls of a batch are seen by nobody
but this list.

The MCP server withholds an event of a circle that has no rule for the client
and writes that into its `mcp_access` (`reason_code` `no_rule`); those are
counted too, under the origin `mcp`, by the circles the entry names as having
no rule, and by its source where the event belongs to no circle, as here.

An entity or a relation the operator stated from memory (`evidence:
recollection`) has no source event and no circle; the policy decides it as a
source `recollection`, and without a rule for it every client but a local one
sees a placeholder. No call and no withholding need have happened yet, so
this reads the graph: while no rule `source:recollection` exists, the list
counts those entities and relations under `graph:source:recollection`, the
rule that would open them.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.core.access import NO_RULE
from previously.core.access import parse_access
from previously.core.action import MCP_ACCESS
from previously.core.action import MODEL_CALL
from previously.core.decide import decide
from previously.core.graph import RECOLLECTION
from previously.core.graph import RETRACTED
from previously.core.graph_write import read_graph
from previously.core.policy import read_policy
from typing import cast
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import LogStore


@dataclass(frozen=True)
class Gap:
    """A scope without a rule, as `circle:<name>` or `source:<source>`, or
    `event:<id>` for a call over an event with no source; how many calls
    fell back for it, and the `recorded_at` of the last. `origin` is `gate`
    for a model call, `mcp` for a withholding of the MCP server and `graph`
    for what stands on a recollection that no rule covers."""

    what: str
    count: int
    last: datetime
    origin: str = "gate"


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
    return (
        [found[scope] for scope in sorted(found)]
        + _mcp_gaps(log, conn, since=since)
        + _recollection_gaps(log, conn, since=since)
    )


def _mcp_gaps[Conn](log: LogStore[Conn], conn: Conn, *, since: datetime | None) -> list[Gap]:
    """What the MCP server withheld for lack of a rule: per circle a
    `withheld` entry with `reason_code` `no_rule` names as `uncovered`, one
    count for each entry. Its other circles have a rule and are no gap. An
    entry with no such circle stands under `source:<source>` as the gate's
    does, and under `event:<id>` where the event had no source. Kept apart
    from the gate's by `origin`: the same missing rule shows up in both, and
    the list should say who ran into it."""
    found: dict[str, Gap] = {}
    for row in log.read_by_kind(conn, "action"):
        payload = row.payload
        if payload is None or payload.get("action") != MCP_ACCESS:
            continue
        if since is not None and row.recorded_at < since:
            continue
        access = parse_access(payload)
        if access is None:
            continue
        for item in access.withheld:
            if item.reason_code != NO_RULE:
                continue
            if item.uncovered:
                scopes = [f"circle:{name}" for name in item.uncovered]
            elif item.source is not None:
                scopes = [f"source:{item.source}"]
            else:
                scopes = [f"event:{item.event}"]
            for scope in scopes:
                known = found.get(scope)
                found[scope] = (
                    Gap(scope, 1, row.recorded_at, "mcp")
                    if known is None
                    else Gap(scope, known.count + 1, max(known.last, row.recorded_at), "mcp")
                )
    return [found[scope] for scope in sorted(found)]


def _recollection_gaps[Conn](
    log: LogStore[Conn], conn: Conn, *, since: datetime | None
) -> list[Gap]:
    """The entities and relations that stand on the operator's recollection
    while no rule covers a source `recollection`: one line,
    `graph:source:recollection`, with how many and the `recorded_at` of the
    latest of their recollections. A retracted one stands no more and is not
    counted. With `since`, only those with a recollection recorded at or
    after it. The policy is asked, not the rules read, so that this keeps
    the meaning of a rule that the write path and the MCP server give it."""
    decision = decide(read_policy(log, conn), identities=(), source=RECOLLECTION, candidates=())
    if decision.fallback is None:
        return []
    graph = read_graph(log, conn)
    count = 0
    last: datetime | None = None
    for thread in graph.threads.values():
        winner = thread.winner(graph.classes)
        if winner is None or winner.claim.body.state == RETRACTED:
            continue
        times = [
            version.recorded_at
            for version in thread.versions
            if version.claim.evidence == RECOLLECTION
            and (since is None or version.recorded_at >= since)
        ]
        if not times:
            continue
        count += 1
        last = max(times) if last is None else max(last, max(times))
    if last is None:
        return []
    return [Gap(f"source:{RECOLLECTION}", count, last, "graph")]
