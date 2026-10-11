# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The access log: every call an MCP client makes is an action `mcp_access`.

A call is a tool, a resource or a prompt, and each one is written, whatever
became of it, including a call that failed. The payload holds ids, names,
reason codes, the sentences that say why something was withheld, and the
arguments of the call: those are the client's input (circle names, ids,
dates), not customer content. It holds no text of any event, no subject and no
address, so an erasure has nothing to cascade into here: the ids of an erased
event point at its tombstones.

`read_access` answers what a client saw, and what was withheld from it, as the
rows of the log; `previously access` prints them. A circle filter matches the
circle a call named in its arguments and the circles of what it withheld, and
nothing else, because the payload names no circle for what it delivered.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from previously.core.action import append_action
from previously.core.action import MCP_ACCESS
from typing import cast
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import LogStore

NO_RULE = "no_rule"
RULE = "rule"
REASON_CODES: frozenset[str] = frozenset({NO_RULE, RULE})
KINDS: frozenset[str] = frozenset({"tool", "resource", "prompt"})
OK = "ok"
ERROR = "error"
OUTCOMES: frozenset[str] = frozenset({OK, ERROR})

_FIELDS: frozenset[str] = frozenset(
    {"action", "client", "policy", "call", "delivered", "withheld", "outcome", "era"}
)


@dataclass(frozen=True)
class Withheld:
    """An event the call did not get: `reason_code` is `no_rule` where a
    circle had no rule for this client, `rule` where a rule said no."""

    event: int
    reason_code: str
    circles: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Delivered:
    """An event the call got, with the units of it."""

    event: int
    units: tuple[int, ...]


@dataclass(frozen=True)
class Access:
    """One call of a client: what it asked, what it got and what it did not."""

    client: str
    policy_ids: Mapping[str, object]
    kind: str
    name: str
    arguments: Mapping[str, object]
    delivered: tuple[Delivered, ...]
    withheld: tuple[Withheld, ...]
    outcome: str
    era: str | None


@dataclass(frozen=True)
class AccessRow:
    """An access with the id and the time of the event that records it."""

    id: int
    recorded_at: datetime
    access: Access


def _payload(access: Access) -> dict[str, object]:
    return {
        "action": MCP_ACCESS,
        "client": access.client,
        "policy": dict(access.policy_ids),
        "call": {"kind": access.kind, "name": access.name, "arguments": dict(access.arguments)},
        "delivered": [
            {"event": item.event, "units": list(item.units)} for item in access.delivered
        ],
        "withheld": [
            {
                "event": item.event,
                "reason_code": item.reason_code,
                "circles": list(item.circles),
                "reason": item.reason,
            }
            for item in access.withheld
        ],
        "outcome": access.outcome,
        "era": access.era,
    }


def record_access[Conn](log: LogStore[Conn], access: Access, *, recorded_at: datetime) -> int:
    """Writes the access in a transaction of its own, after the call has read
    what it answered with, and returns the `id` of the event. A stop between
    the answer and this write loses the entry, the same named limit as the
    gate's."""
    return append_action(log, _payload(access), (), recorded_at=recorded_at)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _entries(payload: Mapping[str, object], key: str) -> list[Mapping[str, object]] | str:
    """The list under `key` as objects, or the problem with it."""
    value = payload.get(key)
    if not isinstance(value, list):
        return f'it has no list "{key}"'
    entries: list[Mapping[str, object]] = []
    for entry in cast("list[object]", value):
        if not isinstance(entry, dict) or not _is_int(
            cast("dict[str, object]", entry).get("event")
        ):
            return f'it has a "{key}" entry without an event'
        entries.append(cast("dict[str, object]", entry))
    return entries


def _call_problem(payload: Mapping[str, object]) -> str | None:
    call = payload.get("call")
    if not isinstance(call, dict):
        return "it has no call"
    named = cast("dict[str, object]", call)
    if named.get("kind") not in KINDS:
        return "its call has no known kind"
    if not isinstance(named.get("name"), str):
        return "its call has no name"
    if not isinstance(named.get("arguments"), dict):
        return "its call has no arguments"
    return None


def _entries_problem(payload: Mapping[str, object]) -> str | None:
    delivered = _entries(payload, "delivered")
    if isinstance(delivered, str):
        return delivered
    withheld = _entries(payload, "withheld")
    if isinstance(withheld, str):
        return withheld
    if any(entry.get("reason_code") not in REASON_CODES for entry in withheld):
        return 'a "withheld" entry has no known reason_code'
    return None


def access_problem(payload: Mapping[str, object]) -> str | None:
    """What is wrong with the form of an `mcp_access` payload, or `None`."""
    unknown = sorted(set(payload) - _FIELDS)
    if unknown:
        return f'it has the unknown field "{unknown[0]}"'
    if not isinstance(payload.get("client"), str):
        return "it has no client"
    if not isinstance(payload.get("policy"), dict):
        return "it has no policy"
    if (problem := _call_problem(payload) or _entries_problem(payload)) is not None:
        return problem
    outcome = payload.get("outcome")
    if not isinstance(outcome, str):
        return "it has no outcome"
    if outcome not in OUTCOMES:
        return f'it has the unknown outcome "{outcome}"'
    era = payload.get("era")
    if era is not None and not isinstance(era, str):
        return "its era is neither text nor null"
    return None


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in cast("list[object]", value) if isinstance(item, str))


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _ints(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in cast("list[object]", value) if isinstance(item, int))


def parse_access(payload: Mapping[str, object]) -> Access | None:
    """The access a well-formed payload describes, or `None` for one that is
    not (`verify` reports it)."""
    if access_problem(payload) is not None:
        return None
    call = cast("Mapping[str, object]", payload["call"])
    delivered = cast("list[Mapping[str, object]]", payload["delivered"])
    withheld = cast("list[Mapping[str, object]]", payload["withheld"])
    return Access(
        client=cast("str", payload["client"]),
        policy_ids=cast("Mapping[str, object]", payload["policy"]),
        kind=cast("str", call["kind"]),
        name=cast("str", call["name"]),
        arguments=cast("Mapping[str, object]", call["arguments"]),
        delivered=tuple(
            Delivered(cast("int", item["event"]), _ints(item.get("units"))) for item in delivered
        ),
        withheld=tuple(
            Withheld(
                cast("int", item["event"]),
                cast("str", item["reason_code"]),
                _strings(item.get("circles")),
                _text(item.get("reason")),
            )
            for item in withheld
        ),
        outcome=cast("str", payload["outcome"]),
        era=cast("str | None", payload.get("era")),
    )


def _names_circle(access: Access, circle: str) -> bool:
    return access.arguments.get("circle") == circle or any(
        circle in item.circles for item in access.withheld
    )


def read_access[Conn](
    log: LogStore[Conn],
    conn: Conn,
    *,
    client: str | None,
    circle: str | None,
    since: datetime | None,
) -> list[AccessRow]:
    """The accesses in the order of the chain, narrowed to one client, to the
    calls that named a circle or had something of it withheld, and to those
    recorded at or after `since`. An erased entry and one with a form
    `verify` reports are left out."""
    rows: list[AccessRow] = []
    for row in log.read_by_kind(conn, "action"):
        payload = row.payload
        if payload is None or payload.get("action") != MCP_ACCESS:
            continue
        if since is not None and row.recorded_at < since:
            continue
        access = parse_access(payload)
        if access is None:
            continue
        if client is not None and access.client != client:
            continue
        if circle is not None and not _names_circle(access, circle):
            continue
        rows.append(AccessRow(row.id, row.recorded_at, access))
    return rows
