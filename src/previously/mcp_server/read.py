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
from previously.contract.rows import EventRow
from previously.core.access import Delivered
from previously.core.access import NO_RULE
from previously.core.access import RULE as RULE_CODE
from previously.core.access import Withheld
from previously.core.assertion import changes
from previously.core.assertion import DecisionBody
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import overdue
from previously.core.assertions import assertion_decisions
from previously.core.assertions import read_threads
from previously.core.assertions import source_identities
from previously.core.assertions import thread_circles
from previously.core.canonical import MAX_SAFE_INT
from previously.core.chain import read_references
from previously.core.decide import Candidate
from previously.core.decide import circles_of
from previously.core.decide import decide
from previously.core.hashing import iso_utc
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import RULE
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
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import UnitRow
    from previously.contract.store import LogStore
    from previously.core.assertion import Statement
    from previously.core.assertion import Thread
    from previously.core.assertion import Version
    from previously.core.decide import Decision
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.mcp_server.render import Page

# Rows per query of the chronicle. A page holds at most 60,000 characters, and
# a mail of the pilot runs from a few hundred to a few thousand, so one batch
# fills a page unless a circle filter drops most of the rows; then the loop
# reads the next batch, and so on until the page is full or the log ends.
# The bound is per query, not per call: how many rows a sparse circle costs is
# an open limit of the pilot, and a derived view of its own waits until
# reading the log is too slow ({ref}`mcp-open-limits`).
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
) -> Seen:
    """The observations after `after` in time order, as many as fill a page
    and one more if it exists, each shown or as a placeholder.

    `circle` keeps the events a member of the circle is involved in, as
    `decide` counts it, own identities left out; an erased event has no
    participants any more and drops out of a circle filter.
    """
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
        pending: list[_Pending] = []
        for row in rows:
            if circle is not None and (
                row.payload is None or circle not in circles_of(policy, _identities(row.payload))
            ):
                continue
            pending.append(_decided(policy, client, row, keys.get(row.id)))
        shown_ids = [item.row.id for item in pending if item.read is None]
        units = log.units_by_event(conn, shown_ids)
        for item in pending:
            if size > PAGE_CHARS:
                return Seen(tuple(reads), more=True)
            read = item.read or _shown(item, units.get(item.row.id, []), full=False, from_unit=None)
            reads.append(read)
            size += _weight(read)
        if len(rows) < BATCH:
            return Seen(tuple(reads), more=False)
        position = (rows[-1].occurred_at, rows[-1].id)


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


def _statement_lines(statement: Statement) -> list[str]:
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


def _history_lines(thread: Thread) -> list[str]:
    """Every standing version in chain order: who stated it, and what it
    changed against the version before it."""
    lines: list[str] = []
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
        elif statement.approves is not None:
            head.append(f"approves {statement.approves}")
        lines.append(" · ".join(head))
        if before is None:
            lines.extend(f"set {line}" for line in _statement_lines(statement))
        else:
            lines.extend(
                f"change {name}: {old} → {new}" for name, old, new in changes(before, statement)
            )
        before = statement
    return lines


def _label(thread: Thread, winner: Version | None, today: date) -> str:
    versions = _plural(len(thread.versions), "version")
    proposals = _plural(len(thread.pending()), "proposal")
    if winner is None or winner.statement.body is None:
        return f"no version stands · {versions} · {proposals}"
    body = winner.statement.body
    state = body.state
    if isinstance(body, ObligationBody) and overdue(body, today):
        state += " · overdue"
    if winner.statement.responsibility == OPEN:
        state = f"proposed · {state}"
    return f"{state} · {winner.statement.responsibility} · {versions} · {proposals}"


def _listed(thread: Thread, listing: Listing) -> bool:
    """Whether the filters that look at the winner keep the thread. Without
    `proposals`, only an entry with a direct winner; with it, only one that
    has a proposal pending or stands as one: a proposal never passes for an
    entry that stands."""
    winner = thread.winner()
    if thread.kind != listing.kind or winner is None or winner.statement.body is None:
        return False
    proposed = winner.statement.responsibility == OPEN
    if listing.proposals != (proposed or bool(thread.pending())):
        return False
    body = winner.statement.body
    if listing.state is not None and body.state != listing.state:
        return False
    return not (
        listing.overdue and not (isinstance(body, ObligationBody) and overdue(body, listing.today))
    )


def _entry[Conn](
    log: LogStore[Conn],
    conn: Conn,
    policy: Policy,
    client: Client,
    thread: Thread,
    listing: Listing,
) -> Read | None:
    """The entry of one thread, shown or as a placeholder, or `None` when the
    circle filter drops it.

    The policy decides over the identities of the sources of every standing
    version, one decision per distinct source, and the first that chooses
    nothing holds. The actors an assertion names are not in it: they say who
    owes or decided, and no more than that about the people in the sources.
    A withheld entry is filtered by the circles of its sources alone, so that
    a placeholder never tells which circle an actor belongs to.
    """
    identities, sources = source_identities(log, conn, thread)
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
    winner = thread.winner()
    if listing.circle is not None and (
        winner is None or listing.circle not in thread_circles(policy, identities, winner.statement)
    ):
        return None
    if listing.history or winner is None:
        lines = _history_lines(thread)
    else:
        lines = _statement_lines(winner.statement)
    item = Stated(uri, thread.kind, _label(thread, winner, listing.today), tuple(lines))
    delivered = Delivered(thread.subject, (), decisions[-1].circles)
    return Read(item, delivered, rules, thread.subject)


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

    With `listing.subject` the one entry, whatever the other filters say, or
    the error that none of that kind stands under the id.
    """
    threads = read_threads(log, conn)
    if listing.subject is not None:
        thread = threads.get(listing.subject)
        if (
            thread is None
            or thread.kind != listing.kind
            or (thread.winner() is None and not listing.history)
        ):
            uri = event_uri(listing.subject)
            message = f"no {listing.kind} stands under this id"
            return Seen((Read(ErrorMark(uri, message), None, event=listing.subject),))
        read = _entry(log, conn, policy, client, thread, replace(listing, circle=None))
        return Seen((cast("Read", read),))
    reads: list[Read] = []
    size = 0
    for name in sorted(threads):
        if (after is not None and name <= after) or not _listed(threads[name], listing):
            continue
        read = _entry(log, conn, policy, client, threads[name], listing)
        if read is None:
            continue
        if size > PAGE_CHARS:
            return Seen(tuple(reads), more=True)
        reads.append(read)
        size += _weight(read)
    return Seen(tuple(reads))
