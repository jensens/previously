# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The MCP server: ten tools, two resource templates and two prompts.

Every call that reaches a handler here reads the policy anew, finds its
client in it, and writes an `mcp_access` after it has read and before it
answers, whatever became of it ({ref}`mcp-access-log`).
A request refused before that writes none: a missing or invalid token (401),
a host the DNS-rebinding check refuses (421), or a protocol version the SDK's
transport does not take (400).
The client is the one `previously mcp` was started for on stdio, or the one
whose bearer token the HTTP wrapper resolved (`auth.guarded`); a header is
never an identity.
A client that is not in force gets an error, and the entry says so.

Every result is one text block, without `structuredContent` and without a
`resource_link`: measured on 2026-10-10, either costs one of the two clients
content, Vibe the whole result ({ref}`mcp-text-block`).
An error starts with `Error: ` and sets `isError` as well, since Vibe's
older harness drops the flag.

One code path serves both protocol generations: the SDK answers
`server/discover` and `initialize` at the same endpoint with
`stateless_http=True`, measured on 2026-10-09, and nothing here branches on
the generation; it is recorded in the access log, nothing more
({ref}`mcp-generations`).

The descriptions are declarative and name no customer data, and a test
holds the tool list against a checksum, so a change to it is a deliberate
one ({ref}`mcp-tool-list`).

Three tools write: `write_assertion` proposes, `write_approve` and
`write_reject` answer a proposal. `write_assertion` takes two calls, a preview
that hands back a sealed handle and a call with `confirm=<handle>` that writes
(`confirm.py`); an answer is one call, because the client's prompt before it
is the person's confirmation and a preview would only reach the model
({ref}`assertions-proposals`). Without the setting `PREVIOUSLY_MCP_CONFIRM_KEY`,
or without a store to lock the sources with, all three answer that writing is
not configured.
A writing call reads and decides in the snapshot as every call does, and
writes after the snapshot is closed, in a transaction of its own.
A source, an entry or a proposal the client may not see is refused with the
sentence an id that names nothing gets, so that the answer does not tell that
it exists. The access entry of a writing call holds counts and ids, and never
the text it wrote ({ref}`mcp-tools`).
"""

from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import UTC
from importlib.metadata import version
from mcp.server import CacheHint
from mcp.server.mcpserver import Context
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult
from mcp.types import TextContent
from previously.core.access import Access
from previously.core.access import ACCESS_ERROR
from previously.core.access import ACCESS_OK
from previously.core.access import Delivered
from previously.core.access import record_access
from previously.core.access import Withheld
from previously.core.assertion import DECISION
from previously.core.assertion import DECISION_STATES
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import OBLIGATION_STATES
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import payload_of
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.assertion import Thread
from previously.core.assertion import Version
from previously.core.assertions import AssertionRefused
from previously.core.assertions import check_statements
from previously.core.assertions import read_threads
from previously.core.assertions import rejections_of
from previously.core.assertions import write_statements
from previously.core.canonical import KEY_PATTERN
from previously.core.canonical import MAX_SAFE_INT
from previously.core.clients import client_for_token
from previously.core.errors import InvalidPayload
from previously.core.gaps import gaps
from previously.core.policy import CIRCLE
from previously.core.policy import CLIENT
from previously.core.policy import PROVIDER
from previously.core.policy import read_policy
from previously.mcp_server.auth import CLIENT_STATE
from previously.mcp_server.auth import guarded
from previously.mcp_server.confirm import expiry
from previously.mcp_server.confirm import HandleRefused
from previously.mcp_server.confirm import key_of
from previously.mcp_server.confirm import open_handle
from previously.mcp_server.confirm import payload_digest
from previously.mcp_server.confirm import seal
from previously.mcp_server.read import assertions
from previously.mcp_server.read import chronicle
from previously.mcp_server.read import circle_verdict
from previously.mcp_server.read import event_hidden
from previously.mcp_server.read import event_uri
from previously.mcp_server.read import events
from previously.mcp_server.read import Listing
from previously.mcp_server.read import logged
from previously.mcp_server.read import MAX_IDS
from previously.mcp_server.read import resume_point
from previously.mcp_server.read import rule_ids
from previously.mcp_server.read import source_verdict
from previously.mcp_server.read import statement_lines
from previously.mcp_server.read import thread_hidden
from previously.mcp_server.read import thread_seen
from previously.mcp_server.render import CURSOR_REFUSED
from previously.mcp_server.render import decode_position
from previously.mcp_server.render import encode_cursor
from previously.mcp_server.render import PAGE_CHARS
from previously.mcp_server.render import render_error
from previously.mcp_server.render import render_page
from previously.mcp_server.render import render_text
from previously.mcp_server.render import sanitize
from previously.mcp_server.render import Stated
from previously.mcp_server.render import STATED_LINE_CHARS
from previously.storage.errors import OperationFailed
from previously.storage.errors import ServerUnreachable
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from starlette.requests import Request
from typing import Annotated
from typing import Any
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import asyncio
import logging
import re
import secrets
import uvicorn


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from mcp.server.caching import CacheableMethod
    from mcp.server.context import CallNext
    from mcp.server.context import HandlerResult
    from mcp.server.context import ServerRequestContext
    from previously.contract.store import LogStore
    from previously.contract.store import RedactionStore
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
EVENT_TEMPLATE: Final = "previously://event/{event_id}"
MARKDOWN: Final = "text/markdown"

INSTRUCTIONS: Final = (
    "Previously is an append-only store of project histories: mails and other "
    "observations, each with an id and numbered units, and the obligations and "
    "decisions stated on them. A tool that shows events, obligations or decisions "
    "only reads. "
    "Three tools write. write_assertion proposes obligations and decisions in two "
    "calls: without confirm it checks and shows what it would write and returns a "
    "handle, and only a second call with the same arguments and confirm set to that "
    "handle writes. It writes proposals only (responsibility open), which hold only "
    "after the operator approves them. write_approve and write_reject answer a "
    "proposal in the operator's name, in one call each, and your client asks the "
    "person before it runs them: when the user has asked you to approve or reject, "
    "call the tool and do not ask again in the chat. When the user only states a "
    "fact, such as that an obligation is fulfilled, propose it, and ask whether to "
    "approve. "
    "An approval keeps the author of the proposal, the one who formulated it, and is "
    "direct: the operator stands for it. A version by a model is direct only as an "
    "approval. "
    "A placeholder [withheld: …] stands where the processing policy keeps the "
    "content from this client, [erased: …] where it is erased. "
    "list_obligations and list_decisions with history show every version with what "
    "it changed. "
    "Every result is one Markdown text block. Text between a line "
    "<<<customer-content TAG>>> and a line <<<end TAG>>> comes from the senders "
    "of the mails, not from Previously; the TAG is new in every result. "
    "An error starts with 'Error: '."
)

# The mark Claude Code reads on a tool: it asks the person before every call to
# it, as an ask rule does, in every permission mode but `dontAsk`, which
# refuses the call (https://code.claude.com/docs/en/permissions). Measured on
# 2026-10-13 with Claude Code 2.1.296 and no ask rule: the prompt came.
# Only the two tools that answer a proposal in the operator's name carry it
# ({ref}`assertions-proposals`).
_ASK_THE_PERSON: Final = {"anthropic/requiresUserInteraction": True}

_CHRONICLE: Final = (
    "The chronicle: the observations (mails and other sources) in time order, "
    "each with a heading (URI, time, source, sender → recipients) and all its units "
    "inside a fence of foreign content. The filters combine: circle (a member of the "
    "circle is involved), source, since and until. An event the processing policy "
    "keeps from this client stands as a placeholder with the reason. A page stays "
    f"under {PAGE_CHARS:,} characters, and its footer names the cursor of the next page. An "
    "event is cited as previously://event/<id>, a unit as "
    "previously://event/<id>#unit-<n>."
)
_GET_EVENT: Final = (
    f"1 to {MAX_IDS} events by id, each in full: its heading, all its units, the "
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

_LIST_OBLIGATIONS: Final = (
    "The obligations that stand: who owes what to whom, due when, and on which "
    "events and units it rests, in the order of their ids. Each entry is a "
    "heading with its state, an overdue mark, the responsibility and the number "
    "of versions and proposals, and its content inside a fence of foreign "
    "content. The filters combine: circle (the circles of the sources, and of "
    "the parties named), state, overdue, and proposals for what is only "
    "proposed. With subject, the one entry, and with history all its versions "
    "with what each changed. An entry the processing policy keeps from this "
    "client, because of the circles of its sources, stands as a placeholder "
    "with the reason. A page stays under "
    f"{PAGE_CHARS:,} characters, and its footer names the cursor of the next page."
)
_LIST_DECISIONS: Final = (
    "The decisions that stand: what was decided, by whom, on which day, and on "
    "which events and units it rests, in the order of their ids. Each entry is "
    "a heading with its state, the responsibility and the number of versions "
    "and proposals, and its content inside a fence of foreign content. The "
    "filters combine: circle (the circles of the sources, and of the deciders "
    "named), state, and proposals for what is only proposed. With subject, the "
    "one entry, and with history all its versions with what each changed. An "
    "entry the processing policy keeps from this client, because of the circles "
    "of its sources, stands as a placeholder with the reason. A page stays under "
    f"{PAGE_CHARS:,} characters, and its footer names the cursor of the next page."
)

# How many statements one writing call takes: as many as a person can read
# in one preview.
MAX_STATEMENTS: Final = 20
_WRITE_ASSERTION: Final = (
    f"Proposes 1 to {MAX_STATEMENTS} obligations or decisions, each resting on "
    "observations this client can see. What it writes is always a proposal, by "
    "model:<this client> and with the responsibility open: it never outranks what a "
    "person stated, and it stands until a person approves or rejects it. An item "
    "with subject is a new, complete version of that entry. Two calls: without "
    "confirm, the statements are checked and shown as they would be written, with a "
    "handle, and nothing is written; with the same items and confirm set to that "
    "handle, within ten minutes, they are written and their ids returned. "
    "Confirming the same handle again writes nothing and returns the same ids."
)
_WRITE_APPROVE: Final = (
    f"Approves 1 to {MAX_STATEMENTS} proposals: each becomes a direct version of its "
    "entry with the content, the sources and the author of the proposal, which the "
    "operator now stands for. Only for a proposal whose entry and sources this "
    "client can see. One call writes; it is idempotent: an approval that stands "
    "already is returned, not repeated. A person decides an approval: the client "
    "asks the person before the call."
)
_WRITE_REJECT: Final = (
    "Rejects one proposal, with an optional reason: it leaves what is proposed and "
    "stays in the history. Only for a proposal whose entry and sources this client "
    "can see. One call writes; it is idempotent: the same rejection with the same "
    "reason is returned, not repeated. A person decides a rejection: the client "
    "asks the person before the call."
)

_MOMENT_HELP: Final = "an ISO 8601 date, or a moment with a zone"
_CIRCLE = Field(description="the name of a circle, as list_circles gives it")
_SOURCE = Field(description="a source, such as email")
_SINCE = Field(description=f"from this time on, inclusive: {_MOMENT_HELP}")
_UNTIL = Field(description=f"before this time, exclusive: {_MOMENT_HELP}")
_CURSOR = Field(description="the cursor from the footer of the previous page")
_IDS = Field(description=f"1 to {MAX_IDS} event ids")
_OBLIGATION_STATE = Field(description="only this state: open, fulfilled or cancelled")
_DECISION_STATE = Field(description="only this state: valid or revoked")
_OVERDUE = Field(description="only what is open and due before today (UTC)")
_PROPOSALS = Field(
    description="list what has a proposal pending, or stands as one, instead of what stands"
)
_SUBJECT = Field(description="the id of one entry, as the heading gives it; the other filters rest")
_HISTORY = Field(description="show all versions of the entry, each with what it changed")
_FROM_UNIT = Field(description="start every event at this unit, for the rest of a cut event")
_ITEMS = Field(description=f"1 to {MAX_STATEMENTS} obligations or decisions")
_CONFIRM = Field(description="the handle of the preview, to write what it showed")
_PROPOSALS_TO_APPROVE = Field(
    description=f"1 to {MAX_STATEMENTS} ids of proposals, as the history of an entry names them"
)
_PROPOSAL = Field(description="the id of a proposal, as the history of an entry names it")
_REJECTION_REASON = Field(description="why the proposal is not taken")
_REFERENCE_HELP: Final = "own, circle:NAME, address:ADDRESS or name:TEXT"


class SourceItem(BaseModel):
    """An event a statement rests on, as write_assertion takes it."""

    model_config = ConfigDict(extra="forbid")

    event: Annotated[int, Field(description="the id of an observation this client can see")]
    units: Annotated[
        list[int] | None,
        Field(description="the units of it that are cited, ascending; left out for all of it"),
    ] = None


class StatementItem(BaseModel):
    """An obligation or a decision as write_assertion takes it, without the fields of the other."""

    model_config = ConfigDict(extra="forbid")

    kind: Annotated[str, Field(description="obligation or decision")]
    sources: Annotated[list[SourceItem], Field(description="the events it rests on, at least one")]
    what: Annotated[str, Field(description="what is owed, or what was decided")]
    state: Annotated[
        str | None,
        Field(
            description=(
                "an obligation open, fulfilled or cancelled, open when left out; "
                "a decision valid or revoked, valid when left out"
            )
        ),
    ] = None
    reason: Annotated[str | None, Field(description="why this version, for the history")] = None
    subject: Annotated[
        int | None,
        Field(description="the id of the entry this is a new, complete version of"),
    ] = None
    debtor: Annotated[
        str | None, Field(description=f"an obligation's: who owes, {_REFERENCE_HELP}")
    ] = None
    creditor: Annotated[
        str | None, Field(description="an obligation's: who is owed, a reference as for debtor")
    ] = None
    due: Annotated[
        str | None, Field(description="an obligation's: by when, YYYY-MM-DD; may lie in the past")
    ] = None
    by: Annotated[
        list[str] | None,
        Field(description="a decision's: who decided, references as for debtor"),
    ] = None
    on: Annotated[
        str | None, Field(description="a decision's: when it was decided, YYYY-MM-DD")
    ] = None
    replaces: Annotated[
        int | None, Field(description="a decision's: the id of the decision it replaces")
    ] = None


# What a client may keep of a read resource, as the protocol revision
# 2026-07-28 lets a server say: nothing past the answer, and only for the
# client that asked, since what a resource shows depends on who reads it.
# The SDK defaults to the same, measured on 2026-10-11 with `mcp` 2.3.0; it
# is named here so that a changed default does not change what this server
# says (ruling R-19 of the 2026-10-11 MCP read access plan: a silent change
# of a default is the risk, not today's answer).
_CACHE_HINTS: Final[Mapping[CacheableMethod, CacheHint]] = {
    "resources/read": CacheHint(ttl_ms=0, scope="private")
}

# The tools/call, resources/read and prompts/get of MCP, by the kind the
# access log gives them.
_KINDS: Final = {"tools/call": "tool", "resources/read": "resource", "prompts/get": "prompt"}

_NO_CLIENT: Final = (
    "this server has no client for the call; over HTTP it needs a bearer token, "
    f"over stdio the variable {CLIENT_VARIABLE}"
)
# One sentence for every cursor that does not lead on: malformed, for other
# filters, or naming no observation. Which of the three it was would tell a
# forger which ids exist.
_CURSOR_AGAIN: Final = f"{CURSOR_REFUSED}; call again without a cursor for the first page"
_FAILED: Final = "the call failed inside the server; its log says why, this result cannot"
_NOT_CONFIGURED: Final = "writing is not configured on this server"
_PREVIEW_TOO_LONG: Final = (
    "the preview of these statements is longer than a page; write fewer in one call"
)
_LINE_TOO_LONG: Final = (
    f"a line of these statements is longer than the {STATED_LINE_CHARS:,} characters "
    "a preview shows of it; shorten it"
)
_ID_RANGE: Final = "a whole number from 1 to 2^53 - 1"
_DAY: Final = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
WRITERS: Final = frozenset({"write_assertion", "write_approve", "write_reject"})
# Every tool the server registers, which the test of the tool list holds
# against what a client lists: a call of any other name is recorded without
# the values of its arguments.
TOOLS: Final = WRITERS | {
    "previously",
    "get_event",
    "list_obligations",
    "list_decisions",
    "list_circles",
    "whoami",
    "policy_gaps",
}

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


@dataclass(frozen=True)
class Answered:
    """A proposal a writing call answers, found and visible to the client,
    with what the access log records of showing it: the delivered entry of
    its thread and the ids of the rules that decided."""

    thread: Thread
    version: Version
    delivered: Delivered
    rules: tuple[int, ...]


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
    # The ids a writing call wrote, or found already written, for the
    # `written` of its access entry; `None` for every other answer.
    written: tuple[int, ...] | None = None


# What the body of a call returns: its answer, or for a writing call the
# write still to do, which `Service.answer` runs once the snapshot is closed.
type Outcome = Answer | Callable[[], Answer]


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
    client: `stdio_client` on stdio, the HTTP wrapper's state otherwise.

    It writes only with both a `locker`, the store that locks the sources
    while a statement is written, and a `key` to seal handles with.
    """

    def __init__(
        self,
        log: LogStore[Conn],
        *,
        stdio_client: str | None,
        locker: RedactionStore[Conn] | None = None,
        key: bytes | None = None,
    ) -> None:
        self.log = log
        self.stdio_client = stdio_client
        self.locker = locker
        self.key = key

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
        recorded = dict(arguments)
        if answer.written is not None:
            recorded["written"] = list(answer.written)
        access = Access(
            client=client,
            policy_ids=policy_ids,
            kind=kind,
            name=name,
            arguments=cast("Mapping[str, object]", recordable(recorded)),
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
        body: Callable[[Conn, Policy, Client], Outcome],
    ) -> Answer:
        """Runs `body` for the client of the call against the policy in force,
        in one snapshot, and writes the access entry afterwards, whatever
        became of the call.

        A body that writes returns the write instead of its answer, and it
        runs here once the snapshot is closed: the snapshot only reads, and
        the write path takes its own transaction, its own locks and a tip of
        its own, so nothing it would gain from the snapshot is worth holding
        a second connection open beside it. Its refusal is the call's, and the
        one access entry is written after it, with the ids it wrote."""
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
                outcome = body(conn, policy, client)
            answer = outcome if isinstance(outcome, Answer) else outcome()
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
            if kind == "tool" and name in WRITERS:
                # What the SDK refused may hold the text the client meant
                # to write: the entry keeps what it keeps of any writing call.
                arguments = write_record(name, arguments)
            elif kind == "tool" and name not in TOOLS:
                # A name this server lacks, a misspelled writing tool among
                # them, may carry text a client derived from a mail; only the
                # names of its arguments are kept (ruling F-13 of the
                # 2026-10-12 assertions plan), so none outlives an erasure.
                arguments = {key: cast("object", None) for key in arguments}
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
        the schema. So every call that reaches this middleware writes one;
        a request the transport refused before it never gets here
        ({ref}`mcp-access-log`)."""
        kind = _KINDS.get(ctx.method)
        if kind is None or ctx.request_id is None:
            return await call_next(ctx)
        mark = _Mark()
        token = _CALL.set(mark)
        try:
            result = await call_next(ctx)
        except Exception:
            if not mark.recorded:
                await asyncio.to_thread(self.net, ctx, kind, None)
            raise
        finally:
            _CALL.reset(token)
        if mark.recorded:
            return result
        replaced = await asyncio.to_thread(self.net, ctx, kind, _first_text(result))
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
                raise Refused(_CURSOR_AGAIN) from error
            after = resume_point(self.log, conn, position.after)
            if after is None:
                raise Refused(_CURSOR_AGAIN)
            page = position.page
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
            return encode_cursor(cast("int", seen.reads[index].event), filters, page=page + 1)

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

    def assertion_page(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        listing: Listing,
        cursor: str | None,
    ) -> Answer:
        """The obligations or the decisions a client may see, as a page."""
        states = OBLIGATION_STATES if listing.kind == OBLIGATION else DECISION_STATES
        if listing.state is not None and listing.state not in states:
            raise Refused(f"state takes one of {', '.join(states)}")
        if listing.circle is not None and listing.circle not in policy.circles:
            raise Refused(f"no circle {listing.circle} exists; list_circles names the circles")
        if listing.subject is not None and not 1 <= listing.subject <= MAX_SAFE_INT:
            raise Refused("subject is the id of an entry, a whole number from 1 to 2^53 - 1")
        filters = {
            key: value
            for key, value in (
                ("kind", listing.kind),
                ("circle", listing.circle),
                ("state", listing.state),
                ("overdue", "true" if listing.overdue else None),
                ("proposals", "true" if listing.proposals else None),
            )
            if value is not None
        }
        after: int | None = None
        page = 1
        if cursor is not None and listing.subject is None:
            try:
                position = decode_position(cursor, filters)
            except ValueError as error:
                raise Refused(_CURSOR_AGAIN) from error
            after, page = position.after, position.page
        seen = assertions(self.log, conn, policy, client, listing, after=after)

        def cursor_for(index: int) -> str:
            return encode_cursor(cast("int", seen.reads[index].event), filters, page=page + 1)

        title = " · ".join(
            [
                f"list_{listing.kind}s",
                *(f"{key} {value}" for key, value in filters.items() if key != "kind"),
            ]
        )
        rendered = render_page(title, seen.items, cursor_for=cursor_for, page=page, more=seen.more)
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

    # --- the writing tools ----------------------------------------------------------

    def writing(self) -> tuple[RedactionStore[Conn], bytes]:
        if self.locker is None or self.key is None:
            raise Refused(_NOT_CONFIGURED)
        return self.locker, self.key

    def assertion_write(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        items: Sequence[StatementItem],
        confirm: str | None,
    ) -> Outcome:
        """`write_assertion`: the items as proposals of this client.

        Every source, a `subject` and a decision `replaces` are checked to be
        visible to the client before anything else looks at them. The write
        path's checks name a missing source, an erased one and the kind of an
        entry, and run only on what the client may see anyway.
        """
        self.writing()
        if not 1 <= len(items) <= MAX_STATEMENTS:
            raise Refused(
                f"items takes 1 to {MAX_STATEMENTS} statements, this call gave {len(items)}"
            )
        statements = [_proposed(number, item, client.name) for number, item in enumerate(items, 1)]
        threads = read_threads(self.log, conn)
        for statement in statements:
            for source in statement.sources:
                if event_hidden(self.log, conn, policy, client, source.event):
                    raise Refused(
                        f"event {source.event} is not one this client can use as a source"
                    )
            subject = statement.subject
            if subject is not None and thread_hidden(
                self.log, conn, policy, client, threads.get(subject)
            ):
                raise Refused(f"subject {subject} is not an entry this client can see")
            body = statement.body
            replaces = body.replaces if isinstance(body, DecisionBody) else None
            if replaces is not None and thread_hidden(
                self.log, conn, policy, client, threads.get(replaces)
            ):
                raise Refused(f"replaces {replaces} is not an entry this client can see")
        shown = [
            Stated(
                f"statement {number}",
                statement.kind,
                _proposal_label(statement),
                tuple(statement_lines(statement)),
            )
            for number, statement in enumerate(statements, 1)
        ]
        return self.staged(conn, client, "write_assertion", statements, shown, confirm)

    def approval_write(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        ids: Sequence[int],
    ) -> Outcome:
        """`write_approve`: each proposal made direct, as `previously
        approve` makes it, in one call; an id named twice is approved once.

        A proposal that an identical approval made its own already is
        answered with that approval's id and writes nothing, so that a retry
        after a lost answer is a success
        ({ref}`assertions-proposals`)."""
        self.writing()
        unique = list(dict.fromkeys(ids))
        if not 1 <= len(unique) <= MAX_STATEMENTS:
            raise Refused(
                f"ids takes 1 to {MAX_STATEMENTS} different proposals, this call gave {len(unique)}"
            )
        if any(not 1 <= proposal <= MAX_SAFE_INT for proposal in unique):
            raise Refused(f"ids holds an id that is not {_ID_RANGE}")
        threads = read_threads(self.log, conn)
        slots: list[Statement | int] = []
        answered: list[Answered] = []
        for proposal in unique:
            found = self.answerable(conn, policy, client, threads, proposal)
            answered.append(found)
            approval = replace(
                found.version.statement,
                responsibility=DIRECT,
                handle=None,
                subject=found.thread.subject,
                approves=found.version.id,
            )
            standing = next(
                (
                    v.id
                    for v in found.thread.versions
                    if v.statement.approves == proposal
                    and replace(v.statement, handle=None) == approval
                ),
                None,
            )
            slots.append(approval if standing is None else standing)
        return self.answering(
            conn,
            "write_approve",
            slots,
            [statement_lines(a) for a in slots if isinstance(a, Statement)],
            _shown_of(answered),
        )

    def rejection_write(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        proposal: int,
        reason: str | None,
    ) -> Outcome:
        """`write_reject`: a direct rejection by this client, with the
        sources of the proposal, so that it goes with the proposal when one
        of them is erased, in one call.

        A second rejection of the same proposal with the same reason by the
        same client answers with the id of the first and writes nothing."""
        self.writing()
        if not 1 <= proposal <= MAX_SAFE_INT:
            raise Refused(f"proposal is not {_ID_RANGE}")
        threads = read_threads(self.log, conn)
        found = self.answerable(conn, policy, client, threads, proposal)
        version = found.version
        statement = Statement(
            REJECTION,
            model_author(client.name),
            DIRECT,
            version.statement.sources,
            reason,
            None,
            None,
            None,
            version.id,
            None,
        )
        standing = next(
            (
                event_id
                for event_id, _at, earlier in rejections_of(self.log, conn, found.thread)
                if replace(earlier, handle=None) == statement
            ),
            None,
        )
        slot: Statement | int = statement if standing is None else standing
        # The proposal's content with the reason of the rejection: the lines
        # the reading tools would cut, as for an approval.
        lines = [statement_lines(replace(version.statement, reason=reason))]
        return self.answering(conn, "write_reject", [slot], lines, _shown_of([found]))

    def answerable(
        self,
        conn: Conn,
        policy: Policy,
        client: Client,
        threads: Mapping[int, Thread],
        proposal: int,
    ) -> Answered:
        """The thread and the version `proposal` names, when the client may
        see the entry and every source of the version; otherwise the
        sentence an id that names nothing gets ({ref}`assertions-proposals`;
        review focus 2 of the 2026-10-12 assertions plan). Whether the version is still an open
        proposal is the write path's question, asked of what the client
        sees.

        The answer rests on the proposal's content, so the call records the
        thread as delivered, with its circles and rules, as a list would."""
        for thread in threads.values():
            version = next((v for v in thread.versions if v.id == proposal), None)
            if version is None:
                continue
            seen = thread_seen(self.log, conn, policy, client, thread)
            if seen is not None and not any(
                event_hidden(self.log, conn, policy, client, source.event)
                for source in version.statement.sources
            ):
                return Answered(thread, version, *seen)
            break
        raise Refused(f"event {proposal} is not a proposal this client can answer")

    def answering(
        self,
        conn: Conn,
        tool: str,
        slots: Sequence[Statement | int],
        lines: Sequence[Sequence[str]],
        seen: tuple[tuple[Delivered, ...], tuple[int, ...]],
    ) -> Outcome:
        """The one call of an answer to proposals: the client's own prompt
        before it is the person's confirmation, and the preview of a second
        call would only ever have reached the model
        ({ref}`assertions-proposals`).

        `slots` holds, in the order asked, a statement to write or the id of
        an identical answer that stands already. The checks run on what is
        to be written, in the order of the write path's: the line bound, the
        form, then `check_statements`; `answer` runs the write after the
        snapshot. `seen` is what the access log records as delivered, with
        the rule ids.
        """
        locker, _key = self.writing()
        # A line the reading tools cut is refused, not cut: the model would
        # answer a proposal it cannot read whole
        # ({ref}`assertions-proposals`; ruling F-12 of the 2026-10-12
        # assertions plan). The raw length is the bound: sanitizing only ever
        # shortens a line.
        if any(len(line) > STATED_LINE_CHARS for item in lines for line in item):
            raise Refused(_LINE_TOO_LONG)
        fresh = [slot for slot in slots if isinstance(slot, Statement)]
        if fresh:
            self.checked(conn, fresh)

        def write() -> Answer:
            ids: tuple[int, ...] = ()
            if fresh:
                try:
                    ids = write_statements(self.log, locker, fresh, recorded_at=datetime.now(UTC))
                except AssertionRefused as refused:
                    raise Refused(str(refused)) from refused
            written = iter(ids)
            numbers = [next(written) if isinstance(slot, Statement) else slot for slot in slots]
            text = render_text(f"{tool} · written", [f"assertion {n}" for n in numbers])
            return Answer(text, delivered=seen[0], rules=seen[1], written=ids)

        return write

    def staged(
        self,
        conn: Conn,
        client: Client,
        tool: str,
        statements: Sequence[Statement],
        shown: Sequence[Stated],
        confirm: str | None,
    ) -> Outcome:
        """The two steps of `write_assertion`, for statements the client may
        see. Without `confirm`, the write path's checks and a preview with a
        sealed handle; with it, the handle opened, the checks again with its
        nonce in every statement, and the write, which `answer` runs after
        the snapshot.

        The handle is opened before the checks so that a second
        confirmation finds the statements its nonce wrote and answers with
        their ids, where the checks would otherwise refuse a statement that
        is written already.
        """
        locker, key = self.writing()
        # A line the preview would cut is refused, not cut: the write would
        # carry the whole text, and the reading tools cut at the same place,
        # so no call would ever show what was confirmed
        # ({ref}`assertions-proposals`; ruling F-12 of the 2026-10-12
        # assertions plan).
        # The raw length is the bound: sanitizing only ever shortens a line.
        if any(len(line) > STATED_LINE_CHARS for item in shown for line in item.lines):
            raise Refused(_LINE_TOO_LONG)
        payloads = [payload_of(statement) for statement in statements]
        try:
            payload_digest(payloads)
        except InvalidPayload as error:
            # The canonical form names a path and what it refused, never the
            # text it found there, as on the write path.
            raise Refused(f"a statement cannot be written: {error}") from error
        now = datetime.now(UTC)
        if confirm is None:
            self.checked(conn, statements)
            nonce = secrets.token_urlsafe(16)
            handle = seal(key, client=client.name, payloads=payloads, now=now, nonce=nonce)
            text = _preview(tool, shown, handle, expiry(now))
            return Answer(text, delivered=(), rules=(), written=())
        try:
            nonce = open_handle(key, confirm, client=client.name, payloads=payloads, now=now)
        except HandleRefused as refused:
            raise Refused(str(refused)) from refused
        sealed = [replace(statement, handle=nonce) for statement in statements]
        self.checked(conn, sealed)

        def write() -> Answer:
            try:
                ids = write_statements(self.log, locker, sealed, recorded_at=datetime.now(UTC))
            except AssertionRefused as refused:
                raise Refused(str(refused)) from refused
            lines = [f"assertion {event_id}" for event_id in ids]
            text = render_text(f"{tool} · written", lines)
            return Answer(text, delivered=(), rules=(), written=ids)

        return write

    def checked(self, conn: Conn, statements: Sequence[Statement]) -> None:
        try:
            check_statements(self.log, conn, statements)
        except AssertionRefused as refused:
            raise Refused(str(refused)) from refused


def _shown_of(answered: Sequence[Answered]) -> tuple[tuple[Delivered, ...], tuple[int, ...]]:
    """The delivered entries of the threads of `answered`, each once, and
    the ids of their rules, ascending."""
    delivered = {found.delivered.event: found.delivered for found in answered}
    rules = sorted({rule for found in answered for rule in found.rules})
    return tuple(delivered.values()), tuple(rules)


def _state_of(statement: Statement) -> str:
    """The state of an obligation or a decision; a rejection has none."""
    return cast("ObligationBody | DecisionBody", statement.body).state


def _proposal_label(statement: Statement) -> str:
    """What the preview says of a proposal outside the fence: nothing in it
    comes from the client but the author's name, which is its own."""
    where = (
        "new entry"
        if statement.subject is None
        else f"new version of {event_uri(statement.subject)}"
    )
    return f"proposed · {_state_of(statement)} · by {statement.author} · {where}"


def _preview(tool: str, shown: Sequence[Stated], handle: str, until: datetime) -> str:
    """The statements inside the fence, as a list shows an entry, and the
    handle with its expiry outside it. A preview is never cut, neither a line
    (`Service.staged` refuses a line longer than a preview shows) nor the
    page: what is not shown cannot be confirmed."""
    page = render_page(f"{tool} · preview", shown, cursor_for=lambda _index: "")
    if page.consumed < len(shown):
        raise Refused(_PREVIEW_TOO_LONG)
    return "\n".join(
        [
            page.text,
            "",
            f"handle: {handle}",
            f"expires: {until.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC",
            f"Nothing is written yet: to write, call {tool} again with the same "
            f"arguments and confirm={handle}.",
        ]
    )


def _event_id(number: int, value: int) -> int:
    if not 1 <= value <= MAX_SAFE_INT:
        raise Refused(f"item {number}: an event id is {_ID_RANGE}")
    return value


def _optional_id(number: int, value: int | None) -> int | None:
    return None if value is None else _event_id(number, value)


def _day(number: int, name: str, text: str | None) -> date | None:
    """A date written `YYYY-MM-DD` and nothing else, as the payload carries
    it: `date.fromisoformat` alone would take `20261130` too."""
    if text is None:
        return None
    refusal = f"item {number}: {name} is not a date written YYYY-MM-DD"
    if _DAY.fullmatch(text) is None:
        raise Refused(refusal)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise Refused(refusal) from error


def _proposed(number: int, item: StatementItem, client: str) -> Statement:
    """The proposal an item of `write_assertion` states, by `model:<client>`
    and open, or the refusal of an item that is none. The form of the
    payload is the write path's check; this one refuses only what the
    arguments cannot say."""
    given: dict[str, object] = {
        "debtor": item.debtor,
        "creditor": item.creditor,
        "due": item.due,
        "by": item.by,
        "on": item.on,
        "replaces": item.replaces,
    }
    kinds = {OBLIGATION: ("debtor", "creditor", "due"), DECISION: ("by", "on", "replaces")}
    if item.kind not in kinds:
        raise Refused(
            f"item {number}: kind is obligation or decision; write_reject rejects a proposal"
        )
    other = DECISION if item.kind == OBLIGATION else OBLIGATION
    for name in kinds[other]:
        if given[name] is not None:
            raise Refused(
                f"item {number}: {name} belongs to {_article(other)} {other}, "
                f"not to {_article(item.kind)} {item.kind}"
            )
    needed = kinds[item.kind][:2]
    if any(given[name] is None for name in needed):
        raise Refused(
            f"item {number}: {_article(item.kind)} {item.kind} needs {' and '.join(needed)}"
        )
    sources = tuple(
        Source(
            _event_id(number, source.event), None if source.units is None else tuple(source.units)
        )
        for source in item.sources
    )
    body: ObligationBody | DecisionBody
    if item.kind == OBLIGATION:
        body = ObligationBody(
            cast("str", item.debtor),
            cast("str", item.creditor),
            item.what,
            _day(number, "due", item.due),
            "open" if item.state is None else item.state,
        )
    else:
        body = DecisionBody(
            item.what,
            tuple(cast("list[str]", item.by)),
            cast("date", _day(number, "on", item.on)),
            "valid" if item.state is None else item.state,
            _optional_id(number, item.replaces),
        )
    return Statement(
        item.kind,
        model_author(client),
        OPEN,
        sources,
        item.reason,
        None,
        _optional_id(number, item.subject),
        None,
        None,
        body,
    )


def _article(kind: str) -> str:
    return "an" if kind[0] in "aeiou" else "a"


def _event_ids(values: object) -> list[int]:
    listed = cast("list[object]", values) if isinstance(values, list) else []
    return [value for value in listed if isinstance(value, int) and not isinstance(value, bool)]


def write_record(name: str, arguments: Mapping[str, object]) -> dict[str, object]:
    """What the access entry of a writing call keeps of its arguments
    ({ref}`assertions-erasure`; decision 10 of the 2026-10-12 assertions
    plan): how many statements, the ids of the sources or of the proposals
    answered, and for `write_assertion` whether `confirm` was given;
    `Service.record` adds the ids written. No text: a text that a
    client derived from a mail would otherwise stand in the log and outlive
    the erasure of the mail. Read leniently, since a call the SDK refused
    has arguments of any form.
    """
    if name == "write_assertion":
        items = arguments.get("items")
        listed = cast("list[object]", items) if isinstance(items, list) else []
        events: set[int] = set()
        for item in listed:
            found = (
                cast("dict[str, object]", item).get("sources") if isinstance(item, dict) else None
            )
            for source in cast("list[object]", found) if isinstance(found, list) else []:
                if isinstance(source, dict):
                    events.update(_event_ids([cast("dict[str, object]", source).get("event")]))
        return {
            "statements": len(listed),
            "sources": sorted(events),
            "confirm": arguments.get("confirm") is not None,
            "written": [],
        }
    asked = arguments.get("ids") if name == "write_approve" else [arguments.get("proposal")]
    proposals = list(dict.fromkeys(_event_ids(asked)))
    return {"statements": len(proposals), "proposals": proposals, "written": []}


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


def build_server[Conn](
    log: LogStore[Conn],
    *,
    stdio_client: str | None,
    locker: RedactionStore[Conn] | None = None,
    confirm_key: str | None = None,
) -> MCPServer:
    """The server against `log`. With `stdio_client` every call is that
    client's; without, a call is the client the HTTP wrapper named.

    The writing tools write with `locker`, the store of `log` that locks
    rows, and seal their handles with `confirm_key`; without either, or with
    a key shorter than 32 characters, they answer that writing is not
    configured, and the reading tools work as before."""
    service = Service(log, stdio_client=stdio_client, locker=locker, key=key_of(confirm_key))
    server: MCPServer = MCPServer(
        SERVER_NAME,
        version=version("previously"),
        instructions=INSTRUCTIONS,
        log_level="WARNING",
        cache_hints=_CACHE_HINTS,
    )
    server.middleware.append(service.safety_net)
    _tools(server, service)
    _writing_tools(server, service)
    _resources(server, service)
    _prompts(server, service)
    return server


def _tools[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The seven tools that read ({ref}`mcp-tools`)."""

    def listing(
        kind: str,
        *,
        circle: str | None,
        state: str | None,
        overdue: bool,
        proposals: bool,
        subject: int | None,
        history: bool,
    ) -> Listing:
        return Listing(
            kind,
            datetime.now(UTC).date(),
            circle=circle,
            state=state,
            overdue=overdue,
            proposals=proposals,
            subject=subject,
            history=history,
        )

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

    @server.tool(name="list_obligations", description=_LIST_OBLIGATIONS)
    def list_obligations(
        ctx: Context,
        circle: Annotated[str | None, _CIRCLE] = None,
        state: Annotated[str | None, _OBLIGATION_STATE] = None,
        overdue: Annotated[bool, _OVERDUE] = False,
        proposals: Annotated[bool, _PROPOSALS] = False,
        subject: Annotated[int | None, _SUBJECT] = None,
        history: Annotated[bool, _HISTORY] = False,
        cursor: Annotated[str | None, _CURSOR] = None,
    ) -> CallToolResult:
        asked = listing(
            OBLIGATION,
            circle=circle,
            state=state,
            overdue=overdue,
            proposals=proposals,
            subject=subject,
            history=history,
        )
        call = (
            "tool",
            "list_obligations",
            _given(
                circle=circle,
                state=state,
                overdue=overdue,
                proposals=proposals,
                subject=subject,
                history=history,
                cursor=cursor,
            ),
        )
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                call,
                lambda conn, policy, client: service.assertion_page(
                    conn, policy, client, asked, cursor
                ),
            )
        )

    @server.tool(name="list_decisions", description=_LIST_DECISIONS)
    def list_decisions(
        ctx: Context,
        circle: Annotated[str | None, _CIRCLE] = None,
        state: Annotated[str | None, _DECISION_STATE] = None,
        proposals: Annotated[bool, _PROPOSALS] = False,
        subject: Annotated[int | None, _SUBJECT] = None,
        history: Annotated[bool, _HISTORY] = False,
        cursor: Annotated[str | None, _CURSOR] = None,
    ) -> CallToolResult:
        asked = listing(
            DECISION,
            circle=circle,
            state=state,
            overdue=False,
            proposals=proposals,
            subject=subject,
            history=history,
        )
        call = (
            "tool",
            "list_decisions",
            _given(
                circle=circle,
                state=state,
                proposals=proposals,
                subject=subject,
                history=history,
                cursor=cursor,
            ),
        )
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                call,
                lambda conn, policy, client: service.assertion_page(
                    conn, policy, client, asked, cursor
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


def _writing_tools[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The three tools that write ({ref}`mcp-tools`): the arguments of each
    are recorded as `write_record` keeps them, never as given."""

    @server.tool(name="write_assertion", description=_WRITE_ASSERTION)
    def write_assertion(
        ctx: Context,
        items: Annotated[list[StatementItem], _ITEMS],
        confirm: Annotated[str | None, _CONFIRM] = None,
    ) -> CallToolResult:
        given = {"items": [item.model_dump() for item in items], "confirm": confirm}
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                ("tool", "write_assertion", write_record("write_assertion", given)),
                lambda conn, policy, client: service.assertion_write(
                    conn, policy, client, items, confirm
                ),
            )
        )

    @server.tool(name="write_approve", description=_WRITE_APPROVE, meta=_ASK_THE_PERSON)
    def write_approve(
        ctx: Context,
        ids: Annotated[list[int], _PROPOSALS_TO_APPROVE],
    ) -> CallToolResult:
        given = {"ids": ids}
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                ("tool", "write_approve", write_record("write_approve", given)),
                lambda conn, policy, client: service.approval_write(conn, policy, client, ids),
            )
        )

    @server.tool(name="write_reject", description=_WRITE_REJECT, meta=_ASK_THE_PERSON)
    def write_reject(
        ctx: Context,
        proposal: Annotated[int, _PROPOSAL],
        reason: Annotated[str | None, _REJECTION_REASON] = None,
    ) -> CallToolResult:
        given = {"proposal": proposal}
        return _ok(
            service.answer(
                ctx.request_context.request,
                ctx.protocol_version,
                ("tool", "write_reject", write_record("write_reject", given)),
                lambda conn, policy, client: service.rejection_write(
                    conn, policy, client, proposal, reason
                ),
            )
        )


def _resources[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The two resource templates ({ref}`mcp-tools`); no
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
    def event(event_id: str, ctx: Context) -> str:
        def body(conn: Conn, policy: Policy, client: Client) -> Answer:
            if not (event_id.isascii() and event_id.isdigit()):
                raise Refused("an event id is a whole number, such as previously://event/42")
            return service.event_page(conn, policy, client, [int(event_id)], None)

        return service.answer(
            ctx.request_context.request,
            ctx.protocol_version,
            ("resource", EVENT_TEMPLATE, {"event_id": event_id}),
            body,
        ).text


def _prompts[Conn](server: MCPServer, service: Service[Conn]) -> None:
    """The two prompts ({ref}`mcp-tools`): a request to the
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
        def body(_conn: Conn, _policy: Policy, _client: Client) -> Answer:
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
        def body(_conn: Conn, _policy: Policy, _client: Client) -> Answer:
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


def build_app[Conn](
    log: LogStore[Conn],
    *,
    allowed_hosts: Sequence[str],
    locker: RedactionStore[Conn] | None = None,
    confirm_key: str | None = None,
) -> Starlette:
    """The ASGI app of `previously serve`: Streamable HTTP under `/mcp`,
    answers as JSON, stateless so that both generations are served, behind the
    token check. `locker` and `confirm_key` are those of `build_server`."""
    server = build_server(log, stdio_client=None, locker=locker, confirm_key=confirm_key)
    app = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=transport_security(allowed_hosts),
    )

    def resolve(token: str) -> str | None:
        with log.begin() as conn:
            client = client_for_token(read_policy(log, conn), token)
        return None if client is None else client.name

    def ready() -> bool:
        # The newest event's id and hash, one indexed query: the cheapest
        # question `LogStore` has, and nothing of it leaves this function.
        try:
            with log.snapshot() as conn:
                log.tip(conn)
        except (ServerUnreachable, OperationFailed) as error:
            # A database that does not answer is an expected state, not a
            # fault of this process: a switchover of the primary refuses
            # connections for seconds (`ServerUnreachable`) or ends one in
            # mid-use (`OperationFailed`), measured in kup6s on 2026-10-13.
            # The storage error's sentence says what a traceback chain of
            # three or four exceptions would, once per failed check.
            logger.warning("the readiness probe found no database: %s", error)
            return False
        except Exception:
            logger.exception("the readiness probe failed for an unexpected reason")
            return False
        return True

    app.add_middleware(guarded, resolve=resolve, ready=ready)
    return app


def run_stdio[Conn](
    log: LogStore[Conn], client: str, *, locker: RedactionStore[Conn], confirm_key: str | None
) -> None:
    """Serves MCP over stdin and stdout for `client` until stdin closes."""
    server = build_server(log, stdio_client=client, locker=locker, confirm_key=confirm_key)
    asyncio.run(server.run_stdio_async())


def run_http[Conn](
    log: LogStore[Conn],
    *,
    host: str,
    port: int,
    allowed_hosts: Sequence[str],
    locker: RedactionStore[Conn],
    confirm_key: str | None,
) -> None:
    """Serves the app of `build_app` with uvicorn until it is stopped."""
    app = build_app(log, allowed_hosts=allowed_hosts, locker=locker, confirm_key=confirm_key)
    uvicorn.run(app, host=host, port=port, log_level="warning")
