# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The gate: one model call, from the event it reads to the `model_call` that
records it.

`call` reads the event, its units, its source and the policy in force; asks
`decide` which candidate may see the content and in which inference region;
calls that candidate's adapter with the region `decide` named, and nothing
narrower or wider; checks the answer against the task's schema itself; and
writes one event of the kind `action` with `payload.action = "model_call"`,
whatever became of the call. A denial is written as well, and an error, a
refusal by the model and an answer against the schema: a call that happened
is in the log, and so is one the policy stopped.

The payload of a `model_call` holds no content: ids, hashes, numbers and
names. The prompt is recorded by the hash of its two halves, before any
content goes in, and an error by its provider, its class and its HTTP status,
never by the words of the provider, which can echo what it was sent. The
answer, when there is one, goes into a unit as canonical JSON, where an
erasure can reach it.

The event is written after the call. A process that dies between the answer
and the write leaves a paid call that no event records; the pilot accepts
that limit, and writing a second event before every call would close it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from previously.contract.rows import EventRow
from previously.contract.rows import UnitRow
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import DENIED
from previously.core.action import ERROR
from previously.core.action import MODEL_CALL
from previously.core.action import OK
from previously.core.action import REFUSED
from previously.core.action import SCHEMA_INVALID
from previously.core.canonical import canonical
from previously.core.decide import decide
from previously.core.decide import Decision
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.hashing import iso_utc
from previously.core.policy import Policy
from previously.core.policy import PROVIDER
from previously.core.policy import read_policy
from previously.core.policy import RULE
from previously.gate.adapters import AdapterError
from previously.gate.adapters import Request
from previously.gate.prices import estimate
from pydantic import BaseModel
from pydantic import ValidationError
from typing import Any
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.store import LogStore
    from previously.gate.adapters import Adapter
    from previously.gate.adapters import Response
    from previously.gate.prices import Prices
    from previously.gate.task import Task


GEO_MISMATCH: Final = "geo_mismatch"
ERASED: Final = "the event is erased"
NO_UNITS: Final = "no unit of the event holds content"
NOT_CONFIGURED: Final = "not_configured"
# The stop reason a provider gives when the model declines the task, as
# Anthropic's Messages API names it.
_REFUSAL: Final = "refusal"


@dataclass(frozen=True)
class Called:
    """What became of one call: the id of the `model_call` that records it,
    the outcome, the decision, the checked output where there is one, the
    alarms, the sentence for the person at the terminal, and the region the
    provider reported."""

    event_id: int
    outcome: str
    decision: Decision
    output: BaseModel | None
    alarms: tuple[str, ...]
    message: str | None
    reported_geo: str | None = None


@dataclass(frozen=True)
class _Read:
    row: EventRow
    units: list[UnitRow]
    source: str | None
    policy: Policy


def _read[Conn](log: LogStore[Conn], conn: Conn, event_id: int, at: datetime | None) -> _Read:
    rows = list(log.read(conn, from_id=event_id, limit=1))
    if not rows or rows[0].id != event_id:
        raise PreviouslyError(f"there is no event {event_id}")
    key = log.source_keys(conn, [event_id]).get(event_id)
    return _Read(
        row=rows[0],
        units=log.units_by_event(conn, [event_id]).get(event_id, []),
        source=None if key is None else key[0],
        policy=read_policy(log, conn, at=at),
    )


def _denied(reason: str) -> Decision:
    """The decision for an event there is nothing to decide about."""
    return Decision(
        circles=(),
        rule_keys=(),
        regions=frozenset(),
        max_retention_days=None,
        excluded_providers=frozenset(),
        local_only=False,
        chosen=None,
        inference_geo=None,
        fallback=None,
        reasons=(reason,),
    )


def _readable(read: _Read) -> list[UnitRow]:
    """The units a prompt may be built from: none of an erased event, and
    none that is a tombstone."""
    if read.row.payload is None:
        return []
    return [unit for unit in read.units if unit.content]


def _decide(read: _Read, task: Task[Any]) -> Decision:
    """The decision for the event, or a denial where it holds nothing to
    read: an erased event leaves tombstones, and a prompt out of tombstones
    would ask a model about nothing."""
    payload = read.row.payload
    if payload is None:
        return _denied(ERASED)
    if not _readable(read):
        return _denied(NO_UNITS)
    identities = payload.get("channel_identities")
    involved = [
        cast("Mapping[str, object]", identity)
        for identity in (cast("list[object]", identities) if isinstance(identities, list) else [])
        if isinstance(identity, Mapping)
    ]
    return decide(read.policy, identities=involved, source=read.source, candidates=task.candidates)


def explain[Conn](
    log: LogStore[Conn], task: Task[Any], event_id: int, *, at: datetime | None = None
) -> Decision:
    """The decision `call` would take for this event, with the policy as it
    stood at `at`, or now. It calls nothing and writes nothing."""
    with log.begin() as conn:
        read = _read(log, conn, event_id, at)
    return _decide(read, task)


def _policy_part(decision: Decision, policy: Policy, task: Task[Any]) -> dict[str, object]:
    """`policy` of the payload: what the decision rested on, by the ids of
    the events that set it, and what it chose."""
    chosen = decision.chosen
    consulted = (
        task.candidates if chosen is None else task.candidates[: task.candidates.index(chosen) + 1]
    )
    providers: list[int] = []
    for candidate in consulted:
        declared = policy.ids.get((PROVIDER, candidate.provider))
        if declared is not None and declared not in providers:
            providers.append(declared)
    fallback = decision.fallback
    return {
        "circles": list(decision.circles),
        # `local_only` has no event, so no id: `fallback` says that it acted.
        "rules": [
            policy.ids[(RULE, scope)] for scope in decision.rule_keys if (RULE, scope) in policy.ids
        ],
        "providers": providers,
        "regions": sorted(decision.regions),
        "max_retention_days": decision.max_retention_days,
        "decision": "denied" if chosen is None else "allowed",
        "provider": None if chosen is None else chosen.provider,
        "model": None if chosen is None else chosen.model,
        "inference_geo": decision.inference_geo,
        "fallback": None
        if fallback is None
        else {"reason": fallback.reason, "circles": list(fallback.circles)},
        "reason": "; ".join(decision.reasons) or None,
    }


def _response_part(
    response: Response, model: str, geo: str | None, prices: Prices
) -> dict[str, object]:
    return {
        "request_id": response.request_id,
        "model": response.model,
        "inference_geo": response.reported_geo,
        "stop_reason": response.stop_reason,
        "usage": {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens},
        # By the model the task named, not the one the provider reports: the
        # price file prices pinned ids, and a provider may answer with a
        # longer name for the same model.
        "cost_usd": estimate(prices, model, geo, response.input_tokens, response.output_tokens),
        "prices_sha256": prices.sha256,
    }


def call[Conn](
    log: LogStore[Conn],
    task: Task[Any],
    event_id: int,
    adapters: Mapping[str, Adapter],
    prices: Prices,
    *,
    recorded_at: datetime,
) -> Called:
    """Runs `task` over the event `event_id` and records the call.

    `adapters` holds one adapter per provider that is configured; a provider
    the decision chooses and `adapters` lacks is an error outcome, recorded
    like a call that failed. Raises `PreviouslyError` only for an event that
    does not exist, and then writes nothing: there is nothing a call could
    have read.
    """
    iso_utc(recorded_at)  # fail early if naive
    with log.begin() as conn:
        read = _read(log, conn, event_id, None)
    decision = _decide(read, task)
    readable = _readable(read)
    payload: dict[str, object] = {
        "action": MODEL_CALL,
        "task": {
            "name": task.name,
            "version": task.version,
            "prompt_sha256": task.prompt_sha256(),
            "schema_sha256": task.schema_sha256(),
        },
        "inputs": [{"event": event_id, "units": [unit.seq for unit in readable], "blobs": []}],
        "policy": _policy_part(decision, read.policy, task),
    }

    def record(outcome: str, alarms: Sequence[str], units: Sequence[str] = ()) -> int:
        payload["outcome"] = outcome
        payload["alarms"] = list(alarms)
        raw = [RawUnit(seq, content) for seq, content in enumerate(units, 1)]
        return append_action(log, payload, raw, recorded_at=recorded_at)

    chosen = decision.chosen
    if chosen is None:
        reason = "; ".join(decision.reasons)
        return Called(record(DENIED, ()), DENIED, decision, None, (), reason)

    name = f"{chosen.provider}/{chosen.model}"
    request = Request(
        model=chosen.model,
        effort=chosen.effort,
        system=task.system,
        user=task.render(readable),
        schema=task.schema(),
        schema_name=task.name,
        inference_geo=decision.inference_geo,
    )
    try:
        adapter = adapters.get(chosen.provider)
        if adapter is None:
            raise AdapterError(
                f"{chosen.provider}: the provider is not configured",
                provider=chosen.provider,
                kind=NOT_CONFIGURED,
                status=None,
            )
        response = adapter.complete(request)
    except AdapterError as error:
        payload["error"] = {"provider": error.provider, "kind": error.kind, "status": error.status}
        return Called(record(ERROR, ()), ERROR, decision, None, (), str(error))

    payload["response"] = _response_part(response, chosen.model, decision.inference_geo, prices)
    requested = decision.inference_geo
    # Where a region was set, the provider has to report that region. Where
    # none was set there is nothing to compare: the provider has a single
    # space, and what it promised there is in its declaration.
    alarms = (GEO_MISMATCH,) if requested is not None and response.reported_geo != requested else ()

    if response.stop_reason == _REFUSAL:
        message = f"{name} declined the task"
        return Called(
            record(REFUSED, alarms), REFUSED, decision, None, alarms, message, response.reported_geo
        )
    try:
        output = task.output.model_validate_json(response.output)
        unit = canonical(output.model_dump(mode="json")).decode()
    except ValidationError:
        message = f"the answer of {name} does not match the schema of {task.name}"
    except InvalidPayload:
        # The schema took it and the log does not, such as a NUL character in
        # a string: the call happened and is recorded, its answer is not.
        message = f"the answer of {name} cannot be stored in the log"
    else:
        return Called(
            record(OK, alarms, (unit,)), OK, decision, output, alarms, None, response.reported_geo
        )
    return Called(
        record(SCHEMA_INVALID, alarms),
        SCHEMA_INVALID,
        decision,
        None,
        alarms,
        message,
        response.reported_geo,
    )
