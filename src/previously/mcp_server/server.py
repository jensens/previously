# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The MCP server: five tools, two resource templates and two prompts.

Every call reads the policy anew, finds its client in it, and writes an
`mcp_access` after it has read, whatever became of it (unit specification,
section 7).
The client is the one `previously mcp` was started for on stdio, or the one
whose bearer token the HTTP wrapper resolved (`auth.guarded`); a header is
never an identity.
A client that is not in force gets an error, and the entry says so.

Every result is one text block, without `structuredContent` and without a
`resource_link`: measured on 2026-10-10, either costs one of the two clients
content, Vibe the whole result (measurement M4).
An error starts with `Error: ` and sets `isError` as well, since Vibe's
older harness drops the flag.

One code path serves both protocol generations: the SDK answers
`server/discover` and `initialize` at the same endpoint with
`stateless_http=True` (measurement M1), and nothing here branches on the
generation; it is recorded in the access log, nothing more.

The descriptions are declarative and name no customer data
(concept specification, section 8); a test holds the tool list against a
checksum, so a change to it is a deliberate one.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import UTC
from importlib.metadata import version
from mcp.server.mcpserver import Context
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolResult
from mcp_types import TextContent
from previously.core.access import Access
from previously.core.access import ACCESS_ERROR
from previously.core.access import ACCESS_OK
from previously.core.access import Delivered
from previously.core.access import record_access
from previously.core.access import Withheld
from previously.core.canonical import KEY_PATTERN
from previously.core.canonical import MAX_SAFE_INT
from previously.core.clients import client_for_token
from previously.core.gaps import gaps
from previously.core.policy import CIRCLE
from previously.core.policy import CLIENT
from previously.core.policy import PROVIDER
from previously.core.policy import read_policy
from previously.mcp_server.auth import CLIENT_STATE
from previously.mcp_server.auth import guarded
from previously.mcp_server.read import chronicle
from previously.mcp_server.read import circle_verdict
from previously.mcp_server.read import events
from previously.mcp_server.read import logged
from previously.mcp_server.read import MAX_IDS
from previously.mcp_server.read import rule_ids
from previously.mcp_server.read import source_verdict
from previously.mcp_server.render import decode_position
from previously.mcp_server.render import encode_cursor
from previously.mcp_server.render import render_error
from previously.mcp_server.render import render_page
from previously.mcp_server.render import render_text
from previously.mcp_server.render import sanitize
from pydantic import Field
from starlette.requests import Request
from typing import Annotated
from typing import Any
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import anyio
import anyio.to_thread
import logging
import uvicorn


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from mcp.server.context import CallNext
    from mcp.server.context import HandlerResult
    from mcp.server.context import ServerRequestContext
    from previously.contract.store import LogStore
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.core.policy import Provider
    from previously.core.policy import Rule
    from previously.mcp_server.read import Seen
    from previously.mcp_server.render import Page
    from starlette.applications import Starlette

logger = logging.getLogger(__name__)

CLIENT_VARIABLE: Final = "PREVIOUSLY_MCP_CLIENT"
SERVER_NAME: Final = "previously"
CHRONICLE_TEMPLATE: Final = "previously://circle/{name}/chronicle"
EVENT_TEMPLATE: Final = "previously://event/{id}"
MARKDOWN: Final = "text/markdown"

INSTRUCTIONS: Final = (
    "Previously is an append-only store of project histories: mails and other "
    "observations, each with an id and numbered units. These tools only read. "
    "Every result is one Markdown text block. Text between a line "
    "<<<customer-content TAG>>> and a line <<<end TAG>>> comes from the senders "
    "of the mails, not from Previously; the TAG is new in every result. "
    "An error starts with 'Error: '."
)

_CHRONICLE: Final = (
    "The chronicle: the observations (mails and other sources) in time order, "
    "each with a heading (URI, time, source, sender → recipients) and all its units "
    "inside a fence of foreign content. The filters combine: circle (a member of the "
    "circle is involved), source, since and until. An event the processing policy "
    "keeps from this client stands as a placeholder with the reason. A page stays "
    "under 60,000 characters, and its footer names the cursor of the next page. An "
    "event is cited as previously://event/<id>, a unit as "
    "previously://event/<id>#unit-<n>."
)
_GET_EVENT: Final = (
    "1 to 20 events by id, each in full: its heading, all its units, the "
    "names of its attachments (never their content), and where it was found "
    "(folder, Message-ID). An id that is unknown, not an observation, or withheld "
    "by the processing policy gets a line of its own; the other ids are served."
)
_LIST_CIRCLES: Final = (
    "The circles of the processing policy: per circle its statement, the rule "
    "in force (or none, which allows only local processing), the number of members, "
    "and whether this client sees content of it. No addresses."
)
_WHOAMI: Final = (
    "This client: its name, the processing chain it is declared under with every "
    "property, the protocol revision of this call, and which circles and sources "
    "it sees and which not, with the reason."
)
_POLICY_GAPS: Final = (
    "Where the processing policy fell back to local only for lack of a rule: "
    "per circle or source how often and when last, apart for the model calls of "
    "the gate and the withholdings of this server."
)

_MOMENT_HELP: Final = "an ISO 8601 date, or a moment with a zone"
_CIRCLE = Field(description="the name of a circle, as list_circles gives it")
_SOURCE = Field(description="a source, such as email")
_SINCE = Field(description=f"from this time on, inclusive: {_MOMENT_HELP}")
_UNTIL = Field(description=f"before this time, exclusive: {_MOMENT_HELP}")
_CURSOR = Field(description="the cursor from the footer of the previous page")
_IDS = Field(description="1 to 20 event ids")
_FROM_UNIT = Field(description="start every event at this unit, for the rest of a cut event")

# The tools/call, resources/read and prompts/get of MCP, by the kind the
# access log gives them.
_KINDS: Final = {"tools/call": "tool", "resources/read": "resource", "prompts/get": "prompt"}

_NO_CLIENT: Final = (
    "this server has no client for the call; over HTTP it needs a bearer token, "
    f"over stdio the variable {CLIENT_VARIABLE}"
)
_FAILED: Final = "the call failed inside the server; its log says why, this result cannot"

# What the access log keeps of a caller's arguments: text cut to this length,
# lists and objects to this many entries, and nesting to this depth. The
# arguments are the client's input, not customer content, but they have to be
# a payload the log takes: no floating point number, no integer beyond 2^53,
# lower-case ASCII keys, no NUL.
_TEXT_LIMIT: Final = 1_000
_ENTRY_LIMIT: Final = 50
_DEPTH_LIMIT: Final = 4


def recordable(value: object, depth: int = 0) -> object:
    """`value` in a form the log takes as part of a payload."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= MAX_SAFE_INT else str(value)
    if isinstance(value, str):
        clean = value.encode("utf-8", "replace").decode("utf-8").replace("\x00", "")
        return clean[:_TEXT_LIMIT]
    if depth >= _DEPTH_LIMIT:
        return "…"
    if isinstance(value, list | tuple):
        members = cast("Sequence[object]", value)
        return [recordable(member, depth + 1) for member in members[:_ENTRY_LIMIT]]
    if isinstance(value, dict):
        entries = cast("dict[object, object]", value)
        return {
            key: recordable(member, depth + 1)
            for key, member in list(entries.items())[:_ENTRY_LIMIT]
            if isinstance(key, str) and KEY_PATTERN.fullmatch(key)
        }
    return recordable(str(value), depth)


class Refused(Exception):
    """An error of the call, worded for the client. It never quotes content."""


@dataclass(frozen=True)
class Answer:
    """What a call returns, and what its access entry records."""

    text: str
    error: bool = False
    delivered: tuple[Delivered, ...] = ()
    withheld: tuple[Withheld, ...] = ()
    rules: tuple[int, ...] = ()


@dataclass
class _Mark:
    """Set by a call that wrote its own access entry, so that the safety net
    around it writes none."""

    recorded: bool = False


_CALL: ContextVar[_Mark | None] = ContextVar("previously_mcp_call", default=None)


def moment(text: str | None, what: str) -> datetime | None:
    """A date (midnight UTC) or a moment with a zone, or `Refused`."""
    if text is None:
        return None
    try:
        return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise Refused(f"{what} is not {_MOMENT_HELP}, such as 2026-09-01") from error
    if parsed.tzinfo is None:
        raise Refused(
            f"{what} has no zone; give a date, or a moment such as 2026-09-01T09:00+02:00"
        )
    return parsed


def _yes(flag: bool | None) -> str:
    return "unknown" if flag is None else "yes" if flag else "no"


def _names(names: frozenset[str] | None) -> str:
    return "unknown" if names is None else ", ".join(sorted(names)) or "none"


def chain_line(provider: Provider | None, name: str) -> str:
    """Every declared property of the provider a client is processed under."""
    if provider is None:
        return f"processor {name}: not declared"
    inference = "; ".join(
        f"{space.name} in {', '.join(sorted(space.regions))}" for space in provider.inference
    )
    retention = "unknown" if provider.retention_days is None else f"{provider.retention_days} days"
    return (
        f"processor {name}: operator {provider.operator or 'unknown'} · "
        f"inference {inference or 'none'} · storage {_names(provider.storage)} · "
        f"retention {retention} · training {_yes(provider.training)} · "
        f"subprocessors {_names(provider.subprocessors)} · "
        f"model origin {provider.model_origin or 'unknown'} · local {_yes(provider.local)}"
    )


def rule_line(rule: Rule | None) -> str:
    if rule is None:
        return "none — only local processing"
    parts = [f"regions {', '.join(sorted(rule.regions))}"]
    if rule.max_retention_days is not None:
        parts.append(f"retention at most {rule.max_retention_days} days")
    if rule.excluded_providers:
        parts.append(f"excludes providers {', '.join(sorted(rule.excluded_providers))}")
    if rule.no_training:
        parts.append("no training")
    if rule.no_subprocessors:
        parts.append("no subprocessors")
    if rule.excluded_operators:
        parts.append(f"excludes operators {', '.join(sorted(rule.excluded_operators))}")
    if rule.excluded_model_origins:
        parts.append(f"excludes model origins {', '.join(sorted(rule.excluded_model_origins))}")
    return ", ".join(parts)


def _ok(answer: Answer) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=answer.text)], is_error=answer.error
    )


class Service[Conn]:
    """The calls of the server against one log, for one way of naming the
    client: `stdio_client` on stdio, the HTTP wrapper's state otherwise."""

    def __init__(self, log: LogStore[Conn], *, stdio_client: str | None) -> None:
        self.log = log
        self.stdio_client = stdio_client

    def client_name(self, request: object) -> str | None:
        if self.stdio_client is not None:
            return self.stdio_client
        if isinstance(request, Request):
            state = request.scope.get("state")
            if isinstance(state, dict):
                name = cast("dict[str, object]", state).get(CLIENT_STATE)
                if isinstance(name, str):
                    return name
        return None

    def record(
        self,
        client: str,
        policy_ids: Mapping[str, object],
        call: tuple[str, str, Mapping[str, object]],
        answer: Answer,
        era: str | None,
    ) -> None:
        kind, name, arguments = call
        access = Access(
            client=client,
            policy_ids=policy_ids,
            kind=kind,
            name=name,
            arguments=cast("Mapping[str, object]", recordable(dict(arguments))),
            delivered=answer.delivered,
            withheld=answer.withheld,
            outcome=ACCESS_ERROR if answer.error else ACCESS_OK,
            era=era,
        )
        record_access(self.log, access, recorded_at=datetime.now(UTC))

    def answer(
        self,
        request: object,
        era: str | None,
        call: tuple[str, str, Mapping[str, object]],
        body: Callable[[Conn, Policy, Client], Answer],
    ) -> Answer:
        """Runs `body` for the client of the call against the policy in force,
        in one snapshot, and writes the access entry afterwards, whatever
        became of the call."""
        mark = _CALL.get()
        if mark is not None:
            mark.recorded = True
        name = self.client_name(request)
        answer = Answer(render_error(_FAILED), error=True)
        policy_ids: dict[str, object] = {}
        try:
            if name is None:
                raise Refused(_NO_CLIENT)
            with self.log.snapshot() as conn:
                policy = read_policy(self.log, conn)
                client = policy.clients.get(name)
                if client is None:
                    raise Refused(
                        f"the client {name} is not in force: it was revoked or never added"
                    )
                policy_ids = {
                    "client": policy.ids.get((CLIENT, name)),
                    "processor": policy.ids.get((PROVIDER, client.processor)),
                    "rules": [],
                }
                answer = body(conn, policy, client)
                policy_ids["rules"] = list(answer.rules)
        except Refused as refused:
            answer = Answer(render_error(str(refused)), error=True)
        except Exception:
            logger.exception("an MCP call failed")
        finally:
            if name is not None:
                self.record(name, policy_ids, call, answer, era)
        return answer

    def net(
        self, request_context: ServerRequestContext[Any, Any], kind: str, text: str | None
    ) -> HandlerResult:
        """Records a call that never reached a handler here, and words the
        refusal of a tool call as an error of ours."""
        params: Mapping[str, object] = request_context.params or {}
        if kind == "resource":
            name, arguments = str(params.get("uri", "")), {}
        else:
            name = str(params.get("name", ""))
            given = params.get("arguments")
            arguments = cast("dict[str, object]", given) if isinstance(given, dict) else {}
        message = f"{name} did not run: {text or 'the request was refused'}"
        answer = Answer(render_error(message), error=True)
        client = self.client_name(request_context.request)
        if client is not None:
            self.record(
                client,
                {},
                (kind, cast("str", recordable(name)), arguments),
                answer,
                request_context.protocol_version,
            )
        if kind != "tool":
            return None
        return _ok(answer)

    async def safety_net(
        self, ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        """The access entry for a call the SDK refused before it reached one
        of the functions below: an unknown name, or arguments that do not fit
        the schema. Every call writes one (unit specification, section 7)."""
        kind = _KINDS.get(ctx.method)
        if kind is None or ctx.request_id is None:
            return await call_next(ctx)
        mark = _Mark()
        token = _CALL.set(mark)
        try:
            result = await call_next(ctx)
        except Exception:
            if not mark.recorded:
                await anyio.to_thread.run_sync(self.net, ctx, kind, None)
            raise
        finally:
            _CALL.reset(token)
        if mark.recorded:
            return result
        replaced = await anyio.to_thread.run_sync(self.net, ctx, kind, _first_text(result))
        return replaced if replaced is not None else result

    # --- the tools ---------------------------------------------------------------

    def chronicle_page(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        filters: Mapping[str, str],
        cursor: str | None,
    ) -> Answer:
        circle = filters.get("circle")
        if circle is not None and circle not in policy.circles:
            raise Refused(f"no circle {circle} exists; list_circles names the circles")
        since = moment(filters.get("since"), "since")
        until = moment(filters.get("until"), "until")
        after: tuple[datetime, int] | None = None
        page = 1
        if cursor is not None:
            try:
                position = decode_position(cursor, filters)
            except ValueError as error:
                raise Refused(f"{error}; call again without a cursor for the first page") from error
            after, page = position.after, position.page
        seen = chronicle(
            self.log,
            conn,
            policy,
            client,
            circle=circle,
            source=filters.get("source"),
            since=since,
            until=until,
            after=after,
        )

        def cursor_for(index: int) -> str:
            position = cast("tuple[datetime, int]", seen.reads[index].position)
            return encode_cursor(position, filters, page=page + 1)

        title = " · ".join(["chronicle", *(f"{key} {value}" for key, value in filters.items())])
        rendered = render_page(title, seen.items, cursor_for=cursor_for, page=page, more=seen.more)
        return _paged(seen, rendered)

    def event_page(
        self, conn: Conn, policy: Policy, client: Client, ids: Sequence[int], from_unit: int | None
    ) -> Answer:
        if not 1 <= len(ids) <= MAX_IDS:
            raise Refused(f"ids takes 1 to {MAX_IDS} event ids, this call gave {len(ids)}")
        if from_unit is not None and not 1 <= from_unit <= MAX_SAFE_INT:
            raise Refused("from_unit is a unit number, 1 or more")
        seen = events(self.log, conn, policy, client, ids, from_unit=from_unit)

        def rest_after(index: int) -> str:
            rest = [str(read.event) for read in seen.reads[index + 1 :] if read.event is not None]
            return ", ".join(rest)

        def next_hint(rest: str) -> str:
            start = "" if from_unit is None else f" from_unit={from_unit}"
            return f"call get_event with ids=[{rest}]{start}"

        title = f"get_event · {len(seen.reads)} of {len(ids)} ids"
        rendered = render_page(title, seen.items, cursor_for=rest_after, next_hint=next_hint)
        return _paged(seen, rendered)

    def circles(self, conn: Conn, policy: Policy, client: Client) -> Answer:
        lines: list[str] = []
        for name in sorted(policy.circles):
            members = sum(1 for m in policy.memberships if m.circle == name)
            verdict = circle_verdict(policy, client, name)
            sees = "sees its content" if verdict.sees else f"does not see it: {verdict.reason}"
            lines.append(
                f"- {name} · statement: {self.statement(conn, policy.ids[(CIRCLE, name)])} · "
                f"rule: {rule_line(policy.rules.get(f'circle:{name}'))} · "
                f"{members} {'member' if members == 1 else 'members'} · "
                f"this client {sees}"
            )
        return Answer(render_text("circles", lines))

    def statement(self, conn: Conn, event_id: int) -> str:
        row = next(iter(self.log.read(conn, event_id, 1)), None)
        payload = row.payload if row is not None else None
        sentence = payload.get("statement") if payload is not None else None
        return sentence if isinstance(sentence, str) else "erased"

    def whoami(self, policy: Policy, client: Client, era: str | None) -> Answer:
        lines = [
            f"client {client.name}",
            chain_line(policy.providers.get(client.processor), client.processor),
            f"protocol revision of this call: {era or 'unknown'}",
            "circles:",
        ]
        for name in sorted(policy.circles):
            verdict = circle_verdict(policy, client, name)
            lines.append(f"- circle {name}: {_seen(verdict.sees, verdict.reason)}")
        lines.append("sources:")
        for scope in sorted(policy.rules):
            if scope.startswith("source:"):
                verdict = source_verdict(policy, client, scope.removeprefix("source:"))
                lines.append(f"- {scope}: {_seen(verdict.sees, verdict.reason)}")
        verdict = source_verdict(policy, client, None)
        lines.append(
            f"- content of no circle and no source rule: {_seen(verdict.sees, verdict.reason)}"
        )
        return Answer(render_text("whoami", lines))

    def gaps(self, conn: Conn, since: str | None) -> Answer:
        found = gaps(self.log, conn, since=moment(since, "since"))
        lines = [
            f"- {gap.what} · {gap.origin} · {gap.count} · last {_minute(gap.last)}" for gap in found
        ]
        if not lines:
            lines = ["No call fell back to local only."]
        return Answer(render_text("policy gaps", lines))


def _minute(moment: datetime) -> str:
    return f"{moment.astimezone(UTC):%Y-%m-%d %H:%M} UTC"


def _seen(sees: bool, reason: str) -> str:
    return "sees it" if sees else f"does not see it: {reason}"


def _paged(seen: Seen, page: Page) -> Answer:
    """The answer for a laid-out page, with the access entries of exactly
    what reached it."""
    delivered, withheld = logged(seen, page)
    return Answer(
        page.text,
        delivered=delivered,
        withheld=withheld,
        rules=tuple(rule_ids(seen, page.consumed)),
    )


def _first_text(result: HandlerResult) -> str | None:
    """The text of the first content block of a tool result, as the SDK
    worded its refusal, or `None`."""
    if isinstance(result, CallToolResult):
        first = result.content[0] if result.content else None
        return first.text if isinstance(first, TextContent) else None
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list) and content:
            first = cast("list[object]", content)[0]
            if isinstance(first, dict):
                text = cast("dict[str, object]", first).get("text")
                return text if isinstance(text, str) else None
    return None


def _said(value: str) -> str:
    """A client's argument as a prompt repeats it: sanitized, on one line."""
    return " ".join(sanitize(value)[0].split())[:_TEXT_LIMIT]


def _given(**arguments: object) -> dict[str, object]:
    return {key: value for key, value in arguments.items() if value is not None}


def build_server[Conn](log: LogStore[Conn], *, stdio_client: str | None) -> MCPServer:
    """The server against `log`. With `stdio_client` every call is that
    client's; without, a call is the client the HTTP wrapper named."""
    service = Service(log, stdio_client=stdio_client)
    server: MCPServer = MCPServer(
        SERVER_NAME,
        version=version("previously"),
        instructions=INSTRUCTIONS,
        log_level="WARNING",
    )
    server.middleware.append(service.safety_net)
    _tools(server, service)
    _resources(server, service)
    _prompts(server, service)
    return server


def _tools[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The five tools (unit specification, section 5)."""

    @server.tool(name="previously", description=_CHRONICLE)
    def previously(
        ctx: Context,
        circle: Annotated[str | None, _CIRCLE] = None,
        source: Annotated[str | None, _SOURCE] = None,
        since: Annotated[str | None, _SINCE] = None,
        until: Annotated[str | None, _UNTIL] = None,
        cursor: Annotated[str | None, _CURSOR] = None,
    ) -> CallToolResult:
        filters = cast(
            "dict[str, str]", _given(circle=circle, source=source, since=since, until=until)
        )
        call = ("tool", "previously", _given(**filters, cursor=cursor))
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                call,
                lambda conn, policy, client: service.chronicle_page(
                    conn, policy, client, filters, cursor
                ),
            )
        )

    @server.tool(name="get_event", description=_GET_EVENT)
    def get_event(
        ctx: Context,
        ids: Annotated[list[int], _IDS],
        from_unit: Annotated[int | None, _FROM_UNIT] = None,
    ) -> CallToolResult:
        call = ("tool", "get_event", _given(ids=ids, from_unit=from_unit))
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                call,
                lambda conn, policy, client: service.event_page(
                    conn, policy, client, ids, from_unit
                ),
            )
        )

    @server.tool(name="list_circles", description=_LIST_CIRCLES)
    def list_circles(ctx: Context) -> CallToolResult:
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                ("tool", "list_circles", {}),
                service.circles,
            )
        )

    @server.tool(name="whoami", description=_WHOAMI)
    def whoami(ctx: Context) -> CallToolResult:
        era = ctx.protocol_version
        return _ok(
            service.answer(
                ctx.request_context.request,
                era,
                ("tool", "whoami", {}),
                lambda _conn, policy, client: service.whoami(policy, client, era),
            )
        )

    @server.tool(name="policy_gaps", description=_POLICY_GAPS)
    def policy_gaps(ctx: Context, since: Annotated[str | None, _SINCE] = None) -> CallToolResult:
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                ("tool", "policy_gaps", _given(since=since)),
                lambda conn, _policy, _client: service.gaps(conn, since),
            )
        )


def _resources[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The two resource templates (unit specification, section 6); no
    resource of its own, so `resources/list` is empty."""

    @server.resource(
        CHRONICLE_TEMPLATE,
        name="circle_chronicle",
        description="The first page of the chronicle of a circle, as the tool previously gives it.",
        mime_type=MARKDOWN,
    )
    def circle_chronicle(name: str, ctx: Context) -> str:
        return service.answer(
            ctx.request_context.request,
            ctx.protocol_version,
            ("resource", CHRONICLE_TEMPLATE, {"circle": name}),
            lambda conn, policy, client: service.chronicle_page(
                conn, policy, client, {"circle": name}, None
            ),
        ).text

    @server.resource(
        EVENT_TEMPLATE,
        name="event",
        description="One event in full, as the tool get_event gives it.",
        mime_type=MARKDOWN,
    )
    def event(id: str, ctx: Context) -> str:  # noqa: A002 — the name of the URI template's variable
        def body(conn: Any, policy: Policy, client: Client) -> Answer:
            if not (id.isascii() and id.isdigit()):
                raise Refused("an event id is a whole number, such as previously://event/42")
            return service.event_page(conn, policy, client, [int(id)], None)

        return service.answer(
            ctx.request_context.request,
            ctx.protocol_version,
            ("resource", EVENT_TEMPLATE, {"id": id}),
            body,
        ).text


def _prompts[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The two prompts (unit specification, section 6): a request to the
    client that names the tools, with no content of its own."""

    @server.prompt(
        name="chronicle_summary",
        description=(
            "A request to summarize the chronicle of a circle between two dates, "
            "citing each statement by its URI."
        ),
    )
    def chronicle_summary(
        circle: str, ctx: Context, since: str | None = None, until: str | None = None
    ) -> str:
        def body(_conn: Any, _policy: Policy, _client: Client) -> Answer:
            name = _said(circle)
            window = "".join(
                f", {key}={_said(value)}"
                for key, value in (("since", since), ("until", until))
                if value is not None
            )
            return Answer(
                f"Summarize what happened in the circle {name}. Read it with the tool "
                f"previously (circle={name}{window}) and follow the cursor to the last "
                "page; fetch a mail in full with get_event where the chronicle cuts it "
                "short. Cite every statement as previously://event/<id>#unit-<n>, and "
                "name the events that were withheld."
            )

        return service.answer(
            ctx.request_context.request,
            ctx.protocol_version,
            ("prompt", "chronicle_summary", _given(circle=circle, since=since, until=until)),
            body,
        ).text

    @server.prompt(
        name="whats_open",
        description=(
            "A request to list what is open in a circle: unanswered questions, "
            "promised work, dates ahead."
        ),
    )
    def whats_open(circle: str, ctx: Context) -> str:
        def body(_conn: Any, _policy: Policy, _client: Client) -> Answer:
            name = _said(circle)
            return Answer(
                f"List what is open in the circle {name}: questions without an answer, "
                "work promised without a sign that it was done, and dates still ahead. "
                f"Read the chronicle with the tool previously (circle={name}), every "
                "page, and fetch single mails in full with get_event. Cite each point as "
                "previously://event/<id>#unit-<n>."
            )

        return service.answer(
            ctx.request_context.request,
            ctx.protocol_version,
            ("prompt", "whats_open", {"circle": circle}),
            body,
        ).text


# The hosts a request may name on the default binding, as the SDK lists them
# for its DNS-rebinding check; `PREVIOUSLY_MCP_ALLOWED_HOSTS` adds to them.
_LOCAL_HOSTS: Final = ("127.0.0.1", "localhost", "[::1]")


def transport_security(allowed_hosts: Sequence[str]) -> TransportSecuritySettings:
    """The SDK's check of `Host` and `Origin` against DNS rebinding: the
    local names, and every name in `allowed_hosts`, with any port."""
    hosts = [*_LOCAL_HOSTS, *allowed_hosts]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[form for host in hosts for form in (host, f"{host}:*")],
        allowed_origins=[
            f"{scheme}://{form}"
            for host in hosts
            for scheme in ("http", "https")
            for form in (host, f"{host}:*")
        ],
    )


def build_app[Conn](log: LogStore[Conn], *, allowed_hosts: Sequence[str]) -> Starlette:
    """The ASGI app of `previously serve`: Streamable HTTP under `/mcp`,
    answers as JSON, stateless so that both generations are served, behind the
    token check."""
    server = build_server(log, stdio_client=None)
    app = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=transport_security(allowed_hosts),
    )

    def resolve(token: str) -> str | None:
        with log.begin() as conn:
            client = client_for_token(read_policy(log, conn), token)
        return None if client is None else client.name

    app.add_middleware(guarded, resolve=resolve)
    return app


def run_stdio[Conn](log: LogStore[Conn], client: str) -> None:
    """Serves MCP over stdin and stdout for `client` until stdin closes."""
    anyio.run(build_server(log, stdio_client=client).run_stdio_async)


def run_http[Conn](
    log: LogStore[Conn], *, host: str, port: int, allowed_hosts: Sequence[str]
) -> None:
    """Serves the app of `build_app` with uvicorn until it is stopped."""
    uvicorn.run(
        build_app(log, allowed_hosts=allowed_hosts), host=host, port=port, log_level="warning"
    )
