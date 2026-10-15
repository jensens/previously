# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What a call of the MCP server reads, and what the policy lets it show.

Every event a call would show passes `decide`, with the people and the source
of the event and the client's processing chain as the only candidate
({ref}`mcp-client-processor`).
An event that fails comes back as a placeholder with a reason built from
policy names only: no subject, no participant, no address, since all of those
are content.
An erased event comes back as a placeholder too.

Nothing here knows MCP or renders text; `render` lays the items out, and the
server writes the access log from what reached the page (`logged`).
"""

from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from functools import partial
from previously.contract.rows import EventRow
from previously.core.access import Delivered
from previously.core.access import NO_RULE
from previously.core.access import RULE as RULE_CODE
from previously.core.access import Withheld
from previously.core.assertion import approval_note
from previously.core.assertion import changes
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import overdue
from previously.core.assertion import parse_statement
from previously.core.assertion import REJECTION
from previously.core.assertion import REJECTION_NOTE
from previously.core.assertions import ASSERTION
from previously.core.assertions import assertion_decisions
from previously.core.assertions import erased_assertion
from previously.core.assertions import read_events
from previously.core.assertions import read_source_events
from previously.core.assertions import read_threads
from previously.core.assertions import rejections_of
from previously.core.assertions import source_identities
from previously.core.assertions import SourceEvents
from previously.core.assertions import thread_circles
from previously.core.canonical import MAX_SAFE_INT
from previously.core.chain import read_references
from previously.core.decide import Candidate
from previously.core.decide import circles_of
from previously.core.decide import decide
from previously.core.decide import Decision
from previously.core.graph import claim_changes
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import level_of
from previously.core.graph import RECOLLECTION
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import TRANSITIVE
from previously.core.graph import value_text
from previously.core.graph_read import reader_bracket_edges
from previously.core.graph_write import claim_decisions
from previously.core.graph_write import claim_sources
from previously.core.graph_write import read_claim_events
from previously.core.graph_write import relation_ends
from previously.core.graph_write import relation_visible
from previously.core.hashing import iso_utc
from previously.core.members import deciding_edges
from previously.core.members import members
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import RULE
from previously.core.vocabulary import display_label
from previously.core.vocabulary import NAME_FIELD
from previously.core.vocabulary import read_vocabulary
from previously.core.vocabulary import REF
from previously.mcp_server.render import ErasedMark
from previously.mcp_server.render import ErrorMark
from previously.mcp_server.render import Head
from previously.mcp_server.render import Item
from previously.mcp_server.render import PAGE_CHARS
from previously.mcp_server.render import Shown
from previously.mcp_server.render import Stated
from previously.mcp_server.render import WithheldMark
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import UnitRow
    from previously.contract.store import LogStore
    from previously.core.assertion import Source
    from previously.core.assertion import Statement
    from previously.core.assertion import Thread
    from previously.core.assertion import Version
    from previously.core.graph import Claim
    from previously.core.graph import ClassState
    from previously.core.graph import Graph
    from previously.core.graph import GraphThread
    from previously.core.graph import GraphVersion
    from previously.core.members import Members
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.core.vocabulary import Vocabulary
    from previously.mcp_server.render import Page

# Rows per query of the chronicle. A page holds at most 60,000 characters, and
# a mail of the pilot runs from a few hundred to a few thousand, so one batch
# fills a page unless a circle filter or a bracket (`within`) drops most of
# the rows; then the loop reads the next batch, and so on until the page is
# full or the log ends. The bound is per query, not per call: how many rows a
# sparse circle or a small bracket costs is an open limit of the pilot, and a
# derived view of its own waits until reading the log is too slow
# ({ref}`mcp-open-limits`).
BATCH: Final = 200

# How much of a page an item is taken to fill before it is rendered: its text
# and an allowance for the heading and the fence. Reading stops once the items
# read exceed a page by this measure, and one more matching item exists; the
# renderer then decides exactly what fits.
_ITEM_ALLOWANCE: Final = 300

MAX_IDS: Final = 20
_EMAIL: Final = "email"
_SENDER_ROLES: Final = ("from", "sender")
_RECIPIENT_ROLES: Final = frozenset({"to", "cc", "bcc"})


def event_uri(event_id: int) -> str:
    return f"previously://event/{event_id}"


@dataclass(frozen=True)
class Read:
    """One item a call read: what it shows, what the access log gets if it
    reaches the page (`None` for an error), the ids of the rule events its
    decision applied, and the event id."""

    item: Item
    entry: Delivered | Withheld | None
    rules: tuple[int, ...] = ()
    # The id the item stands for, where it may be written: `None` for an id
    # out of range.
    event: int | None = None


@dataclass(frozen=True)
class Seen:
    """The items of a call in order, and whether more match beyond them."""

    reads: tuple[Read, ...]
    more: bool = False

    @property
    def items(self) -> tuple[Item, ...]:
        return tuple(read.item for read in self.reads)


def logged(seen: Seen, page: Page) -> tuple[tuple[Delivered, ...], tuple[Withheld, ...]]:
    """The entries of the access log for what reached `page`: only the items
    it consumed, and of a shown event only the units that appeared on it
    (ruling R-9 of the 2026-10-11 MCP read access plan)."""
    delivered: list[Delivered] = []
    withheld: list[Withheld] = []
    for read, units in zip(seen.reads[: page.consumed], page.units, strict=True):
        if isinstance(read.entry, Delivered):
            delivered.append(replace(read.entry, units=units))
        elif isinstance(read.entry, Withheld):
            withheld.append(read.entry)
    return tuple(delivered), tuple(withheld)


def rule_ids(seen: Seen, consumed: int) -> list[int]:
    """The ids of the rule events that decided the consumed items, ascending."""
    return sorted({rule for read in seen.reads[:consumed] for rule in read.rules})


# --- the decision for one event ---------------------------------------------------


def _identities(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
    listed = payload.get("channel_identities")
    if not isinstance(listed, list):
        return []
    return [
        cast("Mapping[str, object]", entry)
        for entry in cast("list[object]", listed)
        if isinstance(entry, dict)
    ]


def _verdict(
    policy: Policy,
    client: Client,
    identities: Sequence[Mapping[str, object]],
    source: str | None,
) -> Decision:
    candidate = Candidate(provider=client.processor, model="", effort=None)
    return decide(policy, identities=identities, source=source, candidates=(candidate,))


def _rules_of(policy: Policy, decision: Decision) -> tuple[int, ...]:
    return tuple(
        policy.ids[(RULE, scope)]
        for scope in decision.rule_keys
        if scope != LOCAL_ONLY and (RULE, scope) in policy.ids
    )


def withholding(policy: Policy, client: Client, decision: Decision) -> tuple[str, str]:
    """The reason code and the sentence for a decision that lets the client's
    chain not pass. Both are made of policy names: circles, scopes, the
    client, its provider and the provider's declared properties."""
    provider = policy.providers.get(client.processor)
    local = provider is not None and provider.local
    who = f"this client ({client.name}) processes with {client.processor}"
    if decision.fallback is not None and not local:
        circles = decision.fallback.circles
        if len(circles) > 1:
            scope = f"circles {', '.join(circles)} have no rule"
        elif circles:
            scope = f"circle {circles[0]} has no rule"
        else:
            scope = "no rule covers this content"
        return NO_RULE, f"{scope}, so only local processing is allowed; {who}, which is not local"
    prefix = f"{client.processor}/: "
    sentence = decision.reasons[-1] if decision.reasons else "it does not pass"
    sentence = sentence.removeprefix(prefix)
    scopes = [scope for scope in decision.rule_keys if scope != LOCAL_ONLY]
    named = f"the rules of {', '.join(scopes)}" if scopes else "the built-in rule local_only"
    processor = f"{client.processor}, the processor of this client ({client.name})"
    return RULE_CODE, f"{named} do not allow {processor}: {sentence}"


# --- events into items ------------------------------------------------------------


def _head(row: EventRow, payload: Mapping[str, object], source: str | None) -> Head:
    sender: str | None = None
    recipients: list[str] = []
    for identity in _identities(payload):
        role = identity.get("role")
        name = identity.get("name")
        address = identity.get("address")
        shown = name if isinstance(name, str) and name else address
        if not isinstance(shown, str):
            continue
        if role in _SENDER_ROLES and sender is None:
            sender = shown
        elif role in _RECIPIENT_ROLES:
            recipients.append(shown)
    return Head(
        uri=event_uri(row.id),
        occurred_at=row.occurred_at,
        source=source or "unknown",
        sender=sender,
        recipients=tuple(recipients),
        subject=None,  # the subject is unit 1 of a mail, inside the fence
    )


def _texts(units: Sequence[UnitRow], from_unit: int | None) -> tuple[tuple[int, str], ...]:
    """The units as (seq, text); an erased unit has no text and is left out."""
    start = from_unit or 1
    return tuple(
        (unit.seq, unit.content) for unit in units if unit.content is not None and unit.seq >= start
    )


def _attachments(payload: Mapping[str, object]) -> tuple[str, ...]:
    """The names of the blobs an event names, the raw mail left out; never
    their content."""
    raw = payload.get("raw")
    names: list[str] = []
    for reference in read_references(payload) or ():
        if reference.sha256 == raw:
            continue
        name = reference.filename or "unnamed"
        names.append(f"{name} ({reference.media_type}, {reference.size} bytes)")
    return tuple(names)


def _provenance(
    payload: Mapping[str, object], key: tuple[str, str] | None
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    found_in = payload.get("found_in")
    if isinstance(found_in, dict):
        where = cast("dict[str, object]", found_in)
        pairs.append(("Found in", ", ".join(f"{k} {v}" for k, v in sorted(where.items()))))
    if key is not None:
        source, external_id = key
        if source == _EMAIL and not external_id.startswith("sha256:"):
            pairs.append(("Message-ID", external_id))
        else:
            pairs.append(("Source key", f"{source} {external_id}"))
    forwarded = payload.get("forwarded_in")
    if isinstance(forwarded, str):
        pairs.append(("Forwarded in", forwarded))
    return tuple(pairs)


@dataclass(frozen=True)
class _Pending:
    """An event decided, before its units are read."""

    row: EventRow
    key: tuple[str, str] | None
    read: Read | None  # set for a placeholder; `None` for an event to show
    circles: tuple[str, ...] = ()
    rules: tuple[int, ...] = ()


def _decided(
    policy: Policy, client: Client, row: EventRow, key: tuple[str, str] | None
) -> _Pending:
    payload = row.payload
    if payload is None:
        entry = Delivered(row.id, (), ())
        mark = ErasedMark(event_uri(row.id))
        return _Pending(row, key, Read(mark, entry, event=row.id))
    source = key[0] if key is not None else None
    decision = _verdict(policy, client, _identities(payload), source)
    rules = _rules_of(policy, decision)
    if decision.chosen is None:
        code, reason = withholding(policy, client, decision)
        mark = WithheldMark(event_uri(row.id), reason)
        uncovered = decision.fallback.circles if decision.fallback is not None else ()
        entry = Withheld(row.id, code, decision.circles, reason, uncovered, source)
        return _Pending(row, key, Read(mark, entry, rules, row.id))
    return _Pending(row, key, None, decision.circles, rules)


def _shown(
    pending: _Pending,
    units: Sequence[UnitRow],
    *,
    full: bool,
    from_unit: int | None,
) -> Read:
    row = pending.row
    payload = cast("Mapping[str, object]", row.payload)
    source = pending.key[0] if pending.key is not None else None
    texts = _texts(units, from_unit)
    item = Shown(
        _head(row, payload, source),
        texts,
        attachments=_attachments(payload) if full else (),
        provenance=_provenance(payload, pending.key) if full else (),
    )
    entry = Delivered(row.id, tuple(seq for seq, _ in texts), pending.circles)
    return Read(item, entry, pending.rules, row.id)


def _weight(read: Read) -> int:
    if isinstance(read.item, Shown):
        return _ITEM_ALLOWANCE + sum(len(text) for _, text in read.item.units)
    if isinstance(read.item, Stated):
        return _ITEM_ALLOWANCE + sum(len(line) for line in read.item.lines)
    return _ITEM_ALLOWANCE


# --- the chronicle ------------------------------------------------------------------


def chronicle[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    *,
    circle: str | None,
    source: str | None,
    since: datetime | None,
    until: datetime | None,
    after: tuple[datetime, int] | None,
    within: Members | None = None,
) -> Seen:
    """The observations after `after` in time order, as many as fill a page
    and one more if it exists, each shown or as a placeholder.

    `circle` keeps the events a member of the circle is involved in, as
    `decide` counts it, own identities left out; an erased event has no
    participants any more and drops out of a circle filter.

    `within` keeps the events of which anything belongs to a bracket, as
    the client finds it (`seen_members`), and of each shown event the units
    that do; an event left with no unit to show is left out. It selects and
    releases nothing ({ref}`chronicle-of-a-bracket`): the policy decides
    every event it keeps as it decides without it, so a unit shown is one
    the client sees without `within` too. The scan ends at the last event
    of the bracket rather than at the end of the log, and reads nothing
    for a bracket nothing belongs to.
    """
    last: tuple[datetime, int] | None = None
    if within is not None:
        last = _last_member(log, conn, within)
        if last is None or (after is not None and after >= last):
            return Seen(())
    reads: list[Read] = []
    size = 0
    position = after
    while True:
        rows = list(
            log.observations(
                conn, since=since, until=until, source=source, after=position, limit=BATCH
            )
        )
        keys = log.source_keys(conn, [row.id for row in rows])
        pending = [
            _decided(policy, client, row, keys.get(row.id))
            for row in rows
            if _filtered_in(policy, row, circle, within)
        ]
        shown_ids = [item.row.id for item in pending if item.read is None]
        units = log.units_by_event(conn, shown_ids)
        for item in pending:
            read = _read_of(item, units.get(item.row.id, []), within)
            if read is None:
                continue
            if size > PAGE_CHARS:
                return Seen(tuple(reads), more=True)
            reads.append(read)
            size += _weight(read)
        if len(rows) < BATCH:
            return Seen(tuple(reads), more=False)
        position = (rows[-1].occurred_at, rows[-1].id)
        if last is not None and position >= last:
            return Seen(tuple(reads), more=False)


def _filtered_in(policy: Policy, row: EventRow, circle: str | None, within: Members | None) -> bool:
    """Whether the filters `circle` and `within` keep `row`, before the
    policy decides it."""
    if circle is not None and (
        row.payload is None or circle not in circles_of(policy, _identities(row.payload))
    ):
        return False
    return within is None or row.id in within.events


def _read_of(item: _Pending, units: Sequence[UnitRow], within: Members | None) -> Read | None:
    """The read of a decided event: its placeholder, or the event with the
    units `within` keeps; `None` for one shown with no unit left to show
    under `within`, which the bracket's chronicle leaves out."""
    if item.read is not None:
        return item.read
    if within is not None:
        units = [unit for unit in units if within.holds(item.row.id, unit.seq)]
        if all(unit.content is None for unit in units):
            return None
    return _shown(item, units, full=False, from_unit=None)


def _last_member[Conn](
    log: LogStore[Conn], conn: Conn, within: Members
) -> tuple[datetime, int] | None:
    """Where the chronicle meets the last event of a bracket, as
    `(occurred_at, id)`, or `None` when no observation belongs to it: one
    read of the events of the bracket, so that a page of a bracket whose
    events lie early in the log doesn't read the rest of it."""
    rows = log.events_by_id(conn, sorted(within.events))
    found = [(row.occurred_at, row.id) for row in rows.values() if row.kind == "observation"]
    return max(found, default=None)


def seen_members[Conn](
    log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, graph: Graph, bracket: int
) -> Members:
    """What belongs to `bracket` as `client` finds it: over the edges it may
    see, an assignment or a hierarchy edge counting only where
    `relation_visible` lets it through ({ref}`chronicle-of-a-bracket`). A
    hidden link stops the walk, an assignment of a mail the client may not
    see doesn't count, and neither does a hidden assignment of a unit of
    its own, which then doesn't take the unit from its mail's bracket.

    The edges are first walked all, which gives every event that can belong;
    visibility is then decided only for the edges `deciding_edges` names,
    the ones the result can turn on, so a call reads the sources of the
    bracket's edges and not those of every assignment there is."""
    edges, kinds = reader_bracket_edges(log, conn, graph)
    deciding = deciding_edges(edges, members(edges, bracket, kinds), kinds)
    if not deciding:
        return members((), bracket, kinds)
    view = graph_view(log, conn, policy, client, graph, [edge.subject for edge in deciding])
    return members([edge for edge in deciding if view.seen(edge.subject)], bracket, kinds)


def resume_point[Conn](
    log: LogStore[Conn], conn: Conn, event_id: int
) -> tuple[datetime, int] | None:
    """Where the chronicle goes on after the event a cursor names: its
    `(occurred_at, id)` out of the log, or `None` when no observation has
    that id. The cursor carries the id alone (`render.encode_cursor`)."""
    row = next(iter(log.read(conn, event_id, 1)), None)
    if row is None or row.id != event_id or row.kind != "observation":
        return None
    return row.occurred_at, row.id


# --- single events ------------------------------------------------------------------


def events[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    ids: Sequence[int],
    *,
    from_unit: int | None,
) -> Seen:
    """Each requested event in the order asked, a repeated id once: shown in
    full with its attachments' names and its provenance, or as a placeholder,
    or as the error of that one id. `from_unit` starts every shown event at
    that unit."""
    reads: list[Read] = []
    seen: set[int] = set()
    for index, event_id in enumerate(ids):
        if event_id in seen:
            continue
        seen.add(event_id)
        if not 1 <= event_id <= MAX_SAFE_INT:
            # The id itself may not appear: a number beyond 2^53 is rounded
            # by a client that reads JSON numbers as doubles.
            message = "the id is out of range: an event id is a whole number from 1 to 2^53 - 1"
            reads.append(Read(ErrorMark(f"ids[{index}]", message), None))
            continue
        row = next(iter(log.read(conn, event_id, 1)), None)
        uri = event_uri(event_id)
        if row is None or row.id != event_id:
            reads.append(Read(ErrorMark(uri, "no event has this id"), None, event=event_id))
            continue
        if row.kind != "observation":
            message = (
                f"the event is not an observation but an {row.kind}; get_event serves observations"
            )
            reads.append(Read(ErrorMark(uri, message), None, event=event_id))
            continue
        key = log.source_keys(conn, [event_id]).get(event_id)
        pending = _decided(policy, client, row, key)
        if pending.read is not None:
            reads.append(pending.read)
            continue
        units = log.units_by_event(conn, [event_id]).get(event_id, [])
        if from_unit is not None and not any(
            unit.seq >= from_unit and unit.content is not None for unit in units
        ):
            last = max((unit.seq for unit in units), default=0)
            message = f"the event has no unit {from_unit} or later to show; its last unit is {last}"
            reads.append(Read(ErrorMark(uri, message), None, event=event_id))
            continue
        reads.append(_shown(pending, units, full=True, from_unit=from_unit))
    return Seen(tuple(reads))


def event_hidden[Conn](
    log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, event_id: int
) -> bool:
    """Whether a client may not learn that the event `event_id` exists: no
    event has the id, or it is an observation the policy withholds from this
    client, as `get_event` decides it.

    An erased event and one that is no observation are not hidden, since
    `get_event` names both to any client; a writing tool lets the write path
    refuse them with its own sentence.
    """
    if not 1 <= event_id <= MAX_SAFE_INT:
        return True
    row = next(iter(log.read(conn, event_id, 1)), None)
    if row is None or row.id != event_id:
        return True
    if row.kind != "observation":
        return False
    pending = _decided(policy, client, row, log.source_keys(conn, [event_id]).get(event_id))
    return pending.read is not None and isinstance(pending.read.entry, Withheld)


# --- what a client sees in principle ------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    """Whether the client sees content of one scope, and why not."""

    sees: bool
    reason: str


def circle_verdict(policy: Policy, client: Client, circle: str) -> Verdict:
    """Whether content of `circle` alone reaches this client: decided for a
    member of it, with every other membership left out, so that no second
    circle decides along. A source rule can still narrow it."""
    members = [m for m in policy.memberships if m.circle == circle]
    if not members:
        return Verdict(False, "the circle has no members, so no content belongs to it")
    alone = replace(policy, memberships=tuple(members), own=())
    decision = _verdict(alone, client, [{"address": members[0].member}], None)
    if decision.chosen is not None:
        return Verdict(True, "a rule allows this client's processing chain")
    return Verdict(False, withholding(alone, client, decision)[1])


def source_verdict(policy: Policy, client: Client, source: str | None) -> Verdict:
    """Whether content of no circle from `source` reaches this client; with
    `None`, content of no circle under no source rule."""
    decision = _verdict(policy, client, [], source)
    if decision.chosen is not None:
        return Verdict(True, "a rule allows this client's processing chain")
    return Verdict(False, withholding(policy, client, decision)[1])


# --- obligations and decisions -----------------------------------------------------

_NONE: Final = "none"


@dataclass(frozen=True)
class Listing:
    """What a call of `list_obligations` or `list_decisions` asked for.

    With `subject`, the call shows that one entry and the other filters are
    not applied; `today` is the UTC date the caller passes in, the day
    "overdue" is judged on.
    """

    kind: str
    today: date
    circle: str | None = None
    state: str | None = None
    overdue: bool = False
    proposals: bool = False
    subject: int | None = None
    history: bool = False


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _uris(statement: Statement) -> str:
    """The sources as URIs: a unit of an event as `#unit-<n>`, an event
    cited whole as itself."""
    uris: list[str] = []
    for source in statement.sources:
        if source.units is None:
            uris.append(event_uri(source.event))
        else:
            uris.extend(f"{event_uri(source.event)}#unit-{seq}" for seq in source.units)
    return ", ".join(uris)


def statement_lines(statement: Statement) -> list[str]:
    """The lines of a statement inside the fence: its text, its actors, its
    dates, its reason and its sources as URIs; the state is the label's."""
    body = statement.body
    lines: list[str] = []
    if isinstance(body, ObligationBody):
        lines.append(f"what: {body.what}")
        lines.append(f"debtor → creditor: {body.debtor} → {body.creditor}")
        lines.append(f"due: {_NONE if body.due is None else body.due.isoformat()}")
    elif isinstance(body, DecisionBody):
        lines.append(f"what: {body.what}")
        lines.append(f"decided by: {', '.join(body.by)}")
        lines.append(f"on: {body.on.isoformat()}")
        if body.replaces is not None:
            lines.append(f"replaces: {event_uri(body.replaces)}")
    lines.append(f"reason: {_NONE if statement.reason is None else statement.reason}")
    lines.append(f"sources: {_uris(statement)}")
    return lines


def _history_lines(
    thread: Thread, rejections: Sequence[tuple[int, datetime, Statement]] = ()
) -> list[str]:
    """Every standing version in chain order: who stated it, and what it
    changed against the version before it; and among them the rejections,
    each with its reason, as `previously obligation --history` shows them."""
    shown: list[tuple[int, list[str]]] = []
    before: Statement | None = None
    for version in thread.versions:
        statement = version.statement
        head = [
            f"version {version.id}",
            iso_utc(version.recorded_at),
            statement.responsibility,
            statement.author,
        ]
        if version.id in thread.rejected:
            head.append("rejected")
        elif version.id in thread.approved:
            head.append("approved")
        elif (note := approval_note(statement)) is not None:
            head.append(note)
        lines = [" · ".join(head)]
        if before is None:
            lines.extend(f"set {line}" for line in statement_lines(statement))
        else:
            lines.extend(
                f"change {name}: {old} → {new}" for name, old, new in changes(before, statement)
            )
        shown.append((version.id, lines))
        before = statement
    for event_id, recorded_at, rejection in rejections:
        head = f"rejection {event_id} · {iso_utc(recorded_at)} · {rejection.author}"
        reason = _NONE if rejection.reason is None else rejection.reason
        shown.append(
            (event_id, [f"{head} · rejects {rejection.of}", f"reason: {REJECTION_NOTE} — {reason}"])
        )
    return [line for _event_id, lines in sorted(shown) for line in lines]


def _label(thread: Thread, winner: Version | None, today: date) -> str:
    versions = _plural(len(thread.versions), "version")
    proposals = _plural(len(thread.pending()), "proposal")
    if winner is None or winner.statement.body is None:
        return f"no version stands · {versions} · {proposals}"
    body = winner.statement.body
    state = body.state
    if isinstance(body, ObligationBody) and overdue(body, today):
        state += " · overdue"
    # `proposed` says the responsibility is open; naming it again read as a
    # duplicate of the state, as in `proposed · open · open` (the acceptance
    # run of 2026-10-13).
    if winner.statement.responsibility == OPEN:
        return f"proposed · {state} · {versions} · {proposals}"
    responsibility = winner.statement.responsibility
    if (note := approval_note(winner.statement)) is not None:
        responsibility = f"{responsibility} · {note}"
    return f"{state} · {responsibility} · {versions} · {proposals}"


def _stands(thread: Thread, listing: Listing) -> bool:
    """Whether the thread is an entry of the kind the call lists: one whose
    winner stands. That much decides whether an entry is there at all, and
    a placeholder says it too."""
    winner = thread.winner()
    return thread.kind == listing.kind and winner is not None and winner.statement.body is not None


def _kept(thread: Thread, listing: Listing) -> bool:
    """Whether the filters that look at the content keep an entry the client
    sees. Without `proposals`, an entry with a direct winner, a pending
    proposal or not; with it, one that has a proposal pending or stands as
    one: a proposal never passes for an entry that stands."""
    winner = cast("Version", thread.winner())
    body = cast("ObligationBody | DecisionBody", winner.statement.body)
    proposed = winner.statement.responsibility == OPEN
    listed = (proposed or bool(thread.pending())) if listing.proposals else not proposed
    if not listed:
        return False
    if listing.state is not None and body.state != listing.state:
        return False
    return not (
        listing.overdue and not (isinstance(body, ObligationBody) and overdue(body, listing.today))
    )


def _entry(
    policy: Policy,
    client: Client,
    thread: Thread,
    listing: Listing,
    read: SourceEvents,
    rejections: Sequence[tuple[int, datetime, Statement]] = (),
) -> Read | None:
    """The entry of one thread, shown or as a placeholder, or `None` when a
    filter drops it.

    The policy decides over the identities of the sources of every standing
    version, one decision per distinct source, and the first that chooses
    nothing holds. The actors an assertion names are not in it: they say who
    owes or decided, and no more than that about the people in the sources.

    The policy decides before any filter that looks at the content: a
    withheld entry passes `state`, `overdue` and `proposals` whatever they
    ask, so that the same placeholder appears under every one of them and
    none of them tells what it holds. It is filtered by the circles of its
    sources alone, so that a placeholder never tells which circle an actor
    belongs to. With `listing.subject` no filter applies but the circle,
    which the caller clears. The `rejections` are those a history shows, and
    the policy decides over their sources too.
    """
    identities, sources = read.of(thread, [rejection for _, _, rejection in rejections])
    decisions = assertion_decisions(policy, client, identities, sources)
    rules = tuple(sorted({rule for d in decisions for rule in _rules_of(policy, d)}))
    uri = event_uri(thread.subject)
    blocked = next((i for i, d in enumerate(decisions) if d.chosen is None), None)
    if blocked is not None:
        decision = decisions[blocked]
        if listing.circle is not None and listing.circle not in decision.circles:
            return None
        code, reason = withholding(policy, client, decision)
        uncovered = decision.fallback.circles if decision.fallback is not None else ()
        source = (tuple(sources) or (None,))[blocked]
        entry = Withheld(thread.subject, code, decision.circles, reason, uncovered, source)
        return Read(WithheldMark(uri, reason), entry, rules, thread.subject)
    if listing.subject is None and not _kept(thread, listing):
        return None
    winner = thread.winner()
    if listing.circle is not None and (
        winner is None or listing.circle not in thread_circles(policy, identities, winner.statement)
    ):
        return None
    if listing.history or winner is None:
        lines = _history_lines(thread, rejections)
    else:
        lines = statement_lines(winner.statement)
    item = Stated(uri, thread.kind, _label(thread, winner, listing.today), tuple(lines))
    delivered = Delivered(thread.subject, (), decisions[-1].circles)
    return Read(item, delivered, rules, thread.subject)


def thread_seen[Conn](
    log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, thread: Thread | None
) -> tuple[Delivered, tuple[int, ...]] | None:
    """What the access log records of an obligation or a decision a call
    shows, as `list_obligations` records an entry: the delivered entry with
    the circles of its sources, and the ids of the rules of every decision.
    `None` when the client may not see it: there is none (`thread` is
    `None`), or the policy withholds it over the sources of every standing
    version."""
    if thread is None:
        return None
    identities, sources = source_identities(log, conn, thread)
    decisions = assertion_decisions(policy, client, identities, sources)
    if any(decision.chosen is None for decision in decisions):
        return None
    rules = tuple(sorted({rule for d in decisions for rule in _rules_of(policy, d)}))
    return Delivered(thread.subject, (), decisions[-1].circles), rules


def thread_hidden[Conn](
    log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, thread: Thread | None
) -> bool:
    """Whether a client may not learn that an obligation or a decision
    stands: `thread_seen` has nothing to record of it."""
    return thread_seen(log, conn, policy, client, thread) is None


def assertions[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    listing: Listing,
    *,
    after: int | None,
) -> Seen:
    """The obligations or decisions that stand, by their ids after `after`,
    as many as fill a page and one more if it exists; each shown, or a
    placeholder where the policy keeps it from this client.

    With `listing.subject` the one entry, whatever the other filters say;
    the placeholder of an erased event when the id names an assertion an
    erasure took and no entry stands under it; or the error that none of
    that kind stands under the id.

    An erased id answers as `get_event` answers it, to any client: the
    kind of an event stays in the log, and whether the assertion was an
    obligation or a decision went with its payload ({ref}`assertions-erasure`).
    """
    threads = read_threads(log, conn)
    if listing.subject is not None:
        subject = listing.subject
        uri = event_uri(subject)
        thread = threads.get(subject)
        if thread is None and erased_assertion(log, conn, subject):
            return Seen((Read(ErasedMark(uri), Delivered(subject, (), ()), event=subject),))
        if (
            thread is None
            or thread.kind != listing.kind
            or (thread.winner() is None and not listing.history)
        ):
            message = f"no {listing.kind} stands under this id"
            return Seen((Read(ErrorMark(uri, message), None, event=subject),))
        rejections = rejections_of(log, conn, thread) if listing.history else ()
        beside = [rejection for _, _, rejection in rejections]
        sources = read_source_events(log, conn, [thread], beside)
        read = _entry(policy, client, thread, replace(listing, circle=None), sources, rejections)
        return Seen((cast("Read", read),))
    names = [
        name
        for name in sorted(threads)
        if (after is None or name > after) and _stands(threads[name], listing)
    ]
    sources = read_source_events(log, conn, [threads[name] for name in names])
    reads: list[Read] = []
    size = 0
    for name in names:
        read = _entry(policy, client, threads[name], listing, sources)
        if read is None:
            continue
        if size > PAGE_CHARS:
            return Seen(tuple(reads), more=True)
        reads.append(read)
        size += _weight(read)
    return Seen(tuple(reads))


# --- entities and relations ---------------------------------------------------------

# The sections of `list_triage`, in the order a person works through them:
# objections to what the operator stands for first, so that one does not go
# under, as the 2026-10-14 assignments specification asks of them, then
# questions, then every other proposal.
OBJECTION: Final = "objection"
QUESTION: Final = "question"
PROPOSAL: Final = "proposal"
TRIAGE_SECTIONS: Final = (OBJECTION, QUESTION, PROPOSAL)


@dataclass(frozen=True)
class ThreadVerdict:
    """What the policy says of an entity or a relation for one client.

    `decisions` are those over the thread's own sources, each with the
    source it was taken for; `ends` those of the entities a relation names,
    which decide along; `blocked` is the first that chooses nothing, with
    its source, or `None`. `shown` is whether the client sees the thread,
    for a relation as `relation_visible` decides it, an assignment, which
    starts at an event, among them: that event is one of its sources.
    """

    decisions: tuple[tuple[str | None, Decision], ...]
    ends: tuple[Decision, ...]
    blocked: tuple[str | None, Decision] | None
    shown: bool


class GraphView:
    """The graph of one call as one client may see it.

    An entity is decided over the identities of the source events of every
    version that stands, as an obligation is, and a recollection as a source
    `recollection` without identities, which the policy withholds until a
    rule `source:recollection` exists (decision 12 of the 2026-10-14
    assignments plan; `claim_verdict`). A relation is decided the same way,
    and is seen only where every entity that any of its versions names is
    seen as well: a relation shows the names of its ends. That rule is
    `relation_visible`'s, and the view only adds which decision withholds:
    the relation's own, else that of an end. An end whose every version is
    erased withholds nothing, since nothing of it is left to show; the
    relation names it as erased, as `get_event` names an erased event to
    any client. An end that names something other than an entity, which
    only a forged payload does, is not seen, and gets no placeholder.

    The verdicts are taken once per thread and kept for the call. The
    source events of a thread are those read with the view, and with `more`
    those of a thread asked about later are read when it is: a graph read
    from its projection folds the end of a relation, or an entity a `ref`
    names, only when a line names it. Without `more`, a thread whose events
    were not read is refused as `SourceEvents.named` refuses it.
    """

    def __init__(
        self,
        policy: Policy,
        client: Client,
        graph: Graph,
        events: SourceEvents,
        more: Callable[[Iterable[int]], SourceEvents] | None = None,
    ) -> None:
        self.policy = policy
        self.client = client
        self.graph = graph
        self._events = events
        self._more = more
        self._verdicts: dict[int, ThreadVerdict] = {}

    def _read(self, thread: GraphThread) -> None:
        """Reads the source events of `thread` the view has not read yet."""
        wanted = {s.event for version in thread.versions for s in version.claim.sources}
        missing = wanted - self._events.read
        if missing and self._more is not None:
            more, known = self._more(missing), self._events
            self._events = SourceEvents(
                known.read | more.read,
                {**known.identities, **more.identities},
                {**known.sources, **more.sources},
            )

    def verdict(self, subject: int) -> ThreadVerdict:
        found = self._verdicts.get(subject)
        if found is not None:
            return found
        thread = self.graph.threads[subject]
        self._read(thread)
        identities, sources = claim_sources(self._events, thread)
        recollection = any(v.claim.evidence == RECOLLECTION for v in thread.versions)
        own = claim_decisions(
            self.policy, self.client, identities, sources, recollection=recollection
        )
        blocked = next(((s, d) for s, d in own if d.chosen is None), None)
        ends: list[Decision] = []
        shown = blocked is None
        if thread.kind == RELATION:
            seen: dict[int, bool | None] = {}
            for end in relation_ends(thread):
                named = self.graph.threads.get(end)
                if named is None:
                    seen[end] = None
                    continue
                if named.kind != ENTITY:
                    seen[end] = False
                    continue
                verdict = self.verdict(end)
                seen[end] = verdict.shown
                ends.extend(decision for _source, decision in verdict.decisions)
                if blocked is None and verdict.blocked is not None:
                    blocked = verdict.blocked
            shown = relation_visible(self.policy, self.client, thread, seen, identities, sources)
        found = ThreadVerdict(own, tuple(ends), blocked, shown)
        self._verdicts[subject] = found
        return found

    def seen(self, subject: int) -> bool:
        """Whether the client sees the thread `subject`; `False` for an id
        that names none."""
        return subject in self.graph.threads and self.verdict(subject).shown

    def rules(self, verdict: ThreadVerdict) -> tuple[int, ...]:
        decisions = [d for _source, d in verdict.decisions] + list(verdict.ends)
        return tuple(sorted({rule for d in decisions for rule in _rules_of(self.policy, d)}))

    def delivered(self, event: int, verdict: ThreadVerdict) -> Delivered:
        """The access entry of a thread the client sees, under `event`, with
        the circles of its own sources, as an obligation has them: of every
        decision, since the one of a recollection, which names nobody, has
        none, and comes last."""
        circles = dict.fromkeys(c for _source, d in verdict.decisions for c in d.circles)
        return Delivered(event, (), tuple(circles))

    def withheld(self, event: int, verdict: ThreadVerdict) -> tuple[WithheldMark, Withheld]:
        """The placeholder of a thread the policy keeps from the client, and
        its access entry, under `event`."""
        source, decision = cast("tuple[str | None, Decision]", verdict.blocked)
        code, reason = withholding(self.policy, self.client, decision)
        uncovered = decision.fallback.circles if decision.fallback is not None else ()
        entry = Withheld(event, code, decision.circles, reason, uncovered, source)
        return WithheldMark(event_uri(event), reason), entry

    def entity_types(self) -> dict[int, str]:
        """The kind of every entity that stands and that the client sees,
        by id: what a claim of this client may name as an end or a `ref`,
        so that an entity it may not see is refused with the sentence of
        one that does not exist (Review Focus 3 of the 2026-10-14
        assignments plan)."""
        return {
            subject: version.claim.body.type
            for subject, version in self.graph.entities().items()
            if self.seen(subject)
        }


def graph_view[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    graph: Graph,
    subjects: Iterable[int] | None = None,
) -> GraphView:
    """The view of `graph` for `client`, with the source events of the
    threads `subjects` names, of every entity those name as an end, or of
    every thread with `None`, read in two queries; those of a thread asked
    about later are read when it is."""
    if subjects is None:
        threads = list(graph.threads.values())
    else:
        wanted = {s for s in subjects if s in graph.threads}
        for subject in list(wanted):
            wanted.update(
                end for end in relation_ends(graph.threads[subject]) if end in graph.threads
            )
        threads = [graph.threads[s] for s in sorted(wanted)]
    return GraphView(
        policy,
        client,
        graph,
        read_claim_events(log, conn, threads),
        lambda events: read_events(log, conn, events),
    )


def objections_seen[Conn](
    log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, graph: Graph
) -> int:
    """How many objections wait that the client may see: those on an entity
    or a relation it sees, for the header of every result
    ({ref}`mcp-tools`). One the client may not see is not counted, so that
    the header tells nothing of what the policy keeps from it. `graph` is
    the one the call reads, the body as well; read from the projection, it
    folds only the threads with an objection, and none when none waits."""
    waiting = graph.objected()
    if not waiting:
        return 0
    view = graph_view(log, conn, policy, client, graph, waiting)
    return sum(
        len(thread.objections(graph.classes))
        for subject, thread in waiting.items()
        if view.seen(subject)
    )


def graph_rejections[Conn](
    log: LogStore[Conn], conn: Conn, thread: GraphThread
) -> tuple[tuple[int, datetime, Statement], ...]:
    """The rejections that stand of versions of an entity or a relation, in
    chain order, as `rejections_of` finds those of an obligation."""
    named = {version.id for version in thread.versions}
    found: list[tuple[int, datetime, Statement]] = []
    for row in log.read_by_kind(conn, ASSERTION):
        statement = None if row.payload is None else parse_statement(row.payload)
        if statement is not None and statement.kind == REJECTION and statement.of in named:
            found.append((row.id, row.recorded_at, statement))
    return tuple(found)


def graph_version(graph: Graph, event_id: int) -> tuple[GraphThread, GraphVersion] | None:
    """The thread and the version `event_id` names, or `None`."""
    for thread in graph.threads.values():
        for version in thread.versions:
            if version.id == event_id:
                return thread, version
    return None


# --- the lines of an entity or a relation ---------------------------------------------


def _name_of(claim: Claim) -> str | None:
    value = claim.body.fields.get(NAME_FIELD)
    return None if value is None else value_text(value)


def entity_text(view: GraphView, entity: int, *, ref: bool = False) -> str:
    """An entity a line names: `entity N` and its name, or what became of
    it. An end of a relation the client sees is always one it sees, or one
    erased; an entity a `ref` field names may be neither, and reads `(not
    shown)` whether the policy keeps it from the client or it is gone, so
    that the line does not tell the two apart."""
    thread = view.graph.threads.get(entity)
    if thread is None or thread.kind != ENTITY or not view.seen(entity):
        return f"entity {entity} ({'not shown' if ref else 'erased'})"
    winner = thread.winner(view.graph.classes)
    if winner is None:
        return f"entity {entity} (none stands)"
    if winner.claim.body.state == RETRACTED:
        return f"entity {entity} (retracted)"
    name = _name_of(winner.claim)
    return f"entity {entity}" if name is None else f"entity {entity} {name}"


def _source_uris(sources: Iterable[Source]) -> str:
    """Events as URIs, and the units cited of one as a URI per unit."""
    uris: list[str] = []
    for source in sources:
        if source.units is None:
            uris.append(event_uri(source.event))
        else:
            uris.extend(f"{event_uri(source.event)}#unit-{seq}" for seq in source.units)
    return ", ".join(uris)


def _evidence_line(claim: Claim) -> str:
    if claim.evidence == RECOLLECTION:
        return "sources: none, the operator's recollection"
    return f"sources: {_source_uris(claim.sources)}"


def claim_lines(view: GraphView, vocabulary: Vocabulary, claim: Claim) -> list[str]:
    """The lines of an entity or a relation inside the fence: its kind,
    what it names, its fields, its state, its reason and its sources as
    URIs, each of which a client or a mail may have written."""
    body = claim.body
    lines = [f"type: {body.type}"]
    if isinstance(body, EntityBody):
        if body.language is not None:
            lines.append(f"language: {body.language}")
    else:
        start = body.start
        lines.append(
            f"from: {entity_text(view, start) if isinstance(start, int) else _source_uris([start])}"
        )
        if body.candidates is not None:
            named = ", ".join(entity_text(view, item) for item in body.candidates)
            lines.append(f"to one of: {named}")
        else:
            lines.append(f"to: {entity_text(view, cast('int', body.to))}")
        if body.period is not None:
            lines.append(f"period: {value_text(body.period)}")
    spec = vocabulary.kind(claim.kind, body.type)
    refs = {item.name for item in (spec.fields if spec is not None else ()) if item.type == REF}
    for name in sorted(body.fields):
        value = body.fields[name]
        if name in refs and isinstance(value, int):
            text = entity_text(view, value, ref=True)
        else:
            text = value_text(value)
        lines.append(f"field {name}: {text}")
    lines.append(f"state: {body.state}")
    lines.append(f"reason: {_NONE if claim.reason is None else claim.reason}")
    lines.append(_evidence_line(claim))
    return lines


def kind_label(vocabulary: Vocabulary, claim: Claim, language: str) -> str:
    """The label of the claim's kind, in the entity's working language or
    in `language`, as `display_label` gives it."""
    body = claim.body
    working = body.language if isinstance(body, EntityBody) else None
    return display_label(vocabulary, claim.kind, body.type, language=working, default=language)


def level_words(version: GraphVersion, classes: Mapping[int, ClassState]) -> list[str]:
    """What a label says of the level of a version: `proposed`, or
    `transitive under URI` with `class revoked` where its class was revoked
    without `demote`, or `direct`."""
    level = level_of(version, classes)
    if level == OPEN:
        return ["proposed"]
    if level != TRANSITIVE:
        return [level]
    under = cast("int", version.claim.under)
    words = [f"transitive under {event_uri(under)}"]
    state = classes.get(under)
    if state is not None and state.revoked:
        words.append("class revoked")
    return words


def _graph_label(view: GraphView, thread: GraphThread, kind: str) -> str:
    classes = view.graph.classes
    versions = _plural(len(thread.versions), "version")
    proposals = _plural(len(thread.pending(classes)), "proposal")
    winner = thread.winner(classes)
    if winner is None:
        return f"{kind} · no version stands · {versions} · {proposals}"
    words = level_words(winner, classes)
    state = winner.claim.body.state
    parts = [kind, *(["proposed", state] if words == ["proposed"] else [state, *words])]
    parts += [versions, proposals]
    parts += [f"contested by {event_uri(v.id)}" for v in thread.objections(classes)]
    return " · ".join(parts)


def _graph_history(view: GraphView, vocabulary: Vocabulary, thread: GraphThread) -> list[str]:
    """Every standing version in chain order: who stated it and at which
    level, and what it changed against the version before it."""
    lines: list[str] = []
    before: Claim | None = None
    for version in thread.versions:
        claim = version.claim
        head = [f"version {version.id}", iso_utc(version.recorded_at), claim.responsibility]
        if claim.under is not None:
            head.append(f"under {event_uri(claim.under)}")
        head.append(claim.author)
        if claim.contests is not None:
            head.append(f"contests {event_uri(claim.contests)}")
        if version.id in thread.rejected:
            head.append("rejected")
        elif version.id in thread.approved:
            head.append("approved")
        lines.append(" · ".join(head))
        if before is None:
            lines.extend(f"set {line}" for line in claim_lines(view, vocabulary, claim))
        else:
            lines.extend(
                f"change {name}: {old} → {new}" for name, old, new in claim_changes(before, claim)
            )
        before = claim
    return lines


def _relation_lines(
    view: GraphView, vocabulary: Vocabulary, subject: int, language: str
) -> list[str]:
    """The relations an entity is an end of that the client sees, each on a
    line of its own: its kind, which way it points, the other end, its
    period and its level where it is not direct."""
    lines: list[str] = []
    classes = view.graph.classes
    relations = view.graph.relations(touching=subject)
    for relation_id in sorted(relations):
        relation = relations[relation_id]
        body = cast("RelationBody", relation.claim.body)
        # An assignment of a mail is no relation between two entities, and a
        # bracket may have many: the page stays the entity's.
        if not isinstance(body.start, int) or not view.seen(relation_id):
            continue
        if body.start == subject:
            way, other = "→", cast("int", body.to)
        elif body.to == subject:
            way, other = "←", body.start
        else:
            continue
        label = display_label(vocabulary, RELATION, body.type, language=None, default=language)
        parts = [f"relation {event_uri(relation_id)}: {label} {way} {entity_text(view, other)}"]
        if body.period is not None:
            parts.append(value_text(body.period))
        level = level_words(relation, classes)
        if level != [DIRECT]:
            parts.extend(level)
        lines.append(" · ".join(parts))
    return lines


# --- list_entities ----------------------------------------------------------------------


@dataclass(frozen=True)
class EntityListing:
    """What a call of `list_entities` asked for. With `subject`, the call
    shows that one entity and the other filters are not applied."""

    types: tuple[str, ...] | None = None
    state: str | None = None
    proposals: bool = False
    subject: int | None = None
    history: bool = False


def _state_listed(state: str, listing: EntityListing) -> bool:
    """Whether a visible entity in `state` is listed under the state filter
    of `listing`, as `previously entities` lists it: with a state asked for,
    only that state; without, a retracted entity not, unless what is asked
    for is the proposals."""
    if listing.state is not None:
        return state == listing.state
    return state != RETRACTED or listing.proposals


def _entity_entry(
    view: GraphView,
    vocabulary: Vocabulary,
    thread: GraphThread,
    listing: EntityListing,
    language: str,
) -> Read | None:
    """The entry of one entity, shown or as a placeholder, or `None` when a
    filter drops it. The policy decides before every filter that looks at
    the content, so that a placeholder stands under every one of them alike,
    as an obligation's does."""
    subject = thread.subject
    verdict = view.verdict(subject)
    rules = view.rules(verdict)
    if verdict.blocked is not None:
        mark, entry = view.withheld(subject, verdict)
        return Read(mark, entry, rules, subject)
    classes = view.graph.classes
    winner = thread.winner(classes)
    if listing.subject is None:
        if winner is None:
            return None
        body = winner.claim.body
        proposed = level_of(winner, classes) == OPEN
        pending = bool(thread.pending(classes))
        listed = (proposed or pending) if listing.proposals else not proposed
        kept = (listing.types is None or body.type in listing.types) and _state_listed(
            body.state, listing
        )
        if not listed or not kept:
            return None
    shown = winner if winner is not None else thread.versions[-1]
    label = _graph_label(view, thread, kind_label(vocabulary, shown.claim, language))
    if listing.history or winner is None:
        lines = _graph_history(view, vocabulary, thread)
    else:
        lines = [
            *claim_lines(view, vocabulary, winner.claim),
            *_relation_lines(view, vocabulary, subject, language),
        ]
    item = Stated(event_uri(subject), ENTITY, label, tuple(lines))
    return Read(item, view.delivered(subject, verdict), rules, subject)


def entities[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    listing: EntityListing,
    *,
    after: int | None,
    language: str,
    graph: Graph,
) -> Seen:
    """The entities, by their ids after `after`, as many as fill a page and
    one more if it exists; each shown with the relations of it the client
    sees, or a placeholder where the policy keeps it from this client.

    With `listing.subject` the one entity, whatever the other filters say;
    the placeholder of an erased event when the id names an assertion an
    erasure took and no entity stands under it; or the error that none
    stands under the id, as `list_obligations` answers. `graph` is the one
    the call folded.
    """
    vocabulary = read_vocabulary(log, conn)
    if listing.subject is not None:
        subject = listing.subject
        view = graph_view(log, conn, policy, client, graph, (subject,))
        uri = event_uri(subject)
        thread = graph.threads.get(subject)
        if thread is None and erased_assertion(log, conn, subject):
            return Seen((Read(ErasedMark(uri), Delivered(subject, (), ()), event=subject),))
        if (
            thread is None
            or thread.kind != ENTITY
            or (thread.winner(graph.classes) is None and not listing.history)
        ):
            missing = ErrorMark(uri, "no entity stands under this id")
            return Seen((Read(missing, None, event=subject),))
        return Seen((cast("Read", _entity_entry(view, vocabulary, thread, listing, language)),))
    standing = graph.winners(ENTITY)
    view = graph_view(log, conn, policy, client, graph, standing)
    reads: list[Read] = []
    size = 0
    for subject in sorted(standing):
        if after is not None and subject <= after:
            continue
        read = _entity_entry(view, vocabulary, graph.threads[subject], listing, language)
        if read is None:
            continue
        if size > PAGE_CHARS:
            return Seen(tuple(reads), more=True)
        reads.append(read)
        size += _weight(read)
    return Seen(tuple(reads))


# --- list_triage ------------------------------------------------------------------------


@dataclass(frozen=True)
class Triaged(Seen):
    """`Seen` with the section of each read, which a cursor of `list_triage`
    carries."""

    sections: tuple[str, ...] = ()


def waiting_versions(graph: Graph) -> dict[str, list[tuple[GraphThread, GraphVersion]]]:
    """What waits for the operator, by section, each by id: as `previously
    triage` sorts it. A version is in one section, and a proposal that
    stands as the winner of its thread counts as one."""
    found: dict[str, list[tuple[GraphThread, GraphVersion]]] = {
        section: [] for section in (OBJECTION, QUESTION, PROPOSAL)
    }
    classes = graph.classes
    for thread in graph.waiting().values():
        winner = thread.winner(classes)
        waiting = list(thread.pending(classes))
        if winner is not None and level_of(winner, classes) == OPEN:
            waiting.append(winner)
        objections = {version.id for version in thread.objections(classes)}
        question = thread.question(classes)
        for version in waiting:
            if version.id in objections:
                found[OBJECTION].append((thread, version))
            elif question is not None and version.id == question.id:
                found[QUESTION].append((thread, version))
            else:
                found[PROPOSAL].append((thread, version))
    for versions in found.values():
        versions.sort(key=lambda pair: pair[1].id)
    return found


def _triage_label(view: GraphView, thread: GraphThread, version: GraphVersion, kind: str) -> str:
    claim = version.claim
    parts = [claim.kind, kind, *level_words(version, view.graph.classes), f"by {claim.author}"]
    if claim.contests is not None:
        parts.append(f"contests {event_uri(claim.contests)}")
    if version.id == thread.subject:
        parts.append(f"new {claim.kind}")
    else:
        parts.append(f"version of {event_uri(thread.subject)}")
    return " · ".join(parts)


def _triage_read(
    view: GraphView,
    vocabulary: Vocabulary,
    section: str,
    thread: GraphThread,
    version: GraphVersion,
    language: str,
) -> Read:
    verdict = view.verdict(thread.subject)
    claim = version.claim
    lines = claim_lines(view, vocabulary, claim)
    winner = thread.winner(view.graph.classes)
    if winner is not None and winner.id != version.id:
        lines += [
            f"change {name}: {old} → {new}" for name, old, new in claim_changes(winner.claim, claim)
        ]
    label = _triage_label(view, thread, version, kind_label(vocabulary, claim, language))
    item = Stated(event_uri(version.id), section, label, tuple(lines))
    return Read(item, view.delivered(version.id, verdict), view.rules(verdict), version.id)


def triage[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    *,
    after: tuple[str, int] | None,
    language: str,
    graph: Graph,
) -> Triaged:
    """What waits for the operator, after `after` (a section and an id), as
    many as fill a page and one more if it exists: the objections, the
    questions and the proposals of entities and relations the client sees,
    and nothing of the others, not even a placeholder (ruling T6-b of the
    2026-10-14 assignments plan): one that appeared when somebody wrote on
    an entity the client may not see, and went when it was answered, would
    tell what the header leaves out. `graph` is the one the call folded."""
    vocabulary = read_vocabulary(log, conn)
    waiting = waiting_versions(graph)
    subjects = {thread.subject for pairs in waiting.values() for thread, _version in pairs}
    view = graph_view(log, conn, policy, client, graph, subjects)
    found: list[tuple[str, int, Callable[[], Read]]] = []
    for section, pairs in waiting.items():
        for thread, version in pairs:
            if view.verdict(thread.subject).shown:
                found.append(
                    (
                        section,
                        version.id,
                        partial(_triage_read, view, vocabulary, section, thread, version, language),
                    )
                )
    start = 0
    if after is not None:
        section, last = after
        rank = TRIAGE_SECTIONS.index(section)
        start = next(
            (
                index
                for index, (s, event, _read) in enumerate(found)
                if TRIAGE_SECTIONS.index(s) > rank or (s == section and event > last)
            ),
            len(found),
        )
    reads: list[Read] = []
    sections: list[str] = []
    size = 0
    for section, _event, make in found[start:]:
        if size > PAGE_CHARS:
            return Triaged(tuple(reads), more=True, sections=tuple(sections))
        read = make()
        reads.append(read)
        sections.append(section)
        size += _weight(read)
    return Triaged(tuple(reads), sections=tuple(sections))
