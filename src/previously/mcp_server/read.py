# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What a call of the MCP server reads, and what the policy lets it show.

Every event a call would show passes `decide`, with the people and the source
of the event and the client's processing chain as the only candidate
(concept specification, section 3.3).
An event that fails comes back as a placeholder with a reason built from
policy names only: no subject, no participant, no address, since all of those
are content.
An erased event comes back as a placeholder too.

Nothing here knows MCP or renders text; `render` lays the items out, and the
server writes the access log from what reached the page (`logged`).
"""

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from previously.contract.rows import EventRow
from previously.core.access import Delivered
from previously.core.access import NO_RULE
from previously.core.access import RULE as RULE_CODE
from previously.core.access import Withheld
from previously.core.canonical import MAX_SAFE_INT
from previously.core.chain import read_references
from previously.core.decide import Candidate
from previously.core.decide import circles_of
from previously.core.decide import decide
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import RULE
from previously.mcp_server.render import ErasedMark
from previously.mcp_server.render import ErrorMark
from previously.mcp_server.render import Head
from previously.mcp_server.render import Item
from previously.mcp_server.render import PAGE_CHARS
from previously.mcp_server.render import Shown
from previously.mcp_server.render import WithheldMark
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.rows import UnitRow
    from previously.contract.store import LogStore
    from previously.core.decide import Decision
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.mcp_server.render import Page

# Rows per query of the chronicle. A page holds at most 60,000 characters, and
# a mail of the pilot runs from a few hundred to a few thousand, so one batch
# fills a page unless a circle filter drops most of the rows; then the loop
# reads the next batch, and so on until the page is full or the log ends.
# The bound is per query, not per call: how many rows a sparse circle costs is
# open point 1 of section 13 of the unit specification (a projection of its
# own, once reading the log is too slow).
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
    reaches the page (`None` for an error), where it stands in time order,
    the ids of the rule events its decision applied, and the event id."""

    item: Item
    entry: Delivered | Withheld | None
    position: tuple[datetime, int] | None
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
    position = (row.occurred_at, row.id)
    payload = row.payload
    if payload is None:
        entry = Delivered(row.id, (), ())
        mark = ErasedMark(event_uri(row.id))
        return _Pending(row, key, Read(mark, entry, position, event=row.id))
    source = key[0] if key is not None else None
    decision = _verdict(policy, client, _identities(payload), source)
    rules = _rules_of(policy, decision)
    if decision.chosen is None:
        code, reason = withholding(policy, client, decision)
        mark = WithheldMark(event_uri(row.id), reason)
        entry = Withheld(row.id, code, decision.circles, reason)
        return _Pending(row, key, Read(mark, entry, position, rules, row.id))
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
    return Read(item, entry, (row.occurred_at, row.id), pending.rules, row.id)


def _weight(read: Read) -> int:
    if isinstance(read.item, Shown):
        return _ITEM_ALLOWANCE + sum(len(text) for _, text in read.item.units)
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
            reads.append(Read(ErrorMark(f"ids[{index}]", message), None, None))
            continue
        row = next(iter(log.read(conn, event_id, 1)), None)
        uri = event_uri(event_id)
        if row is None or row.id != event_id:
            reads.append(Read(ErrorMark(uri, "no event has this id"), None, None, event=event_id))
            continue
        if row.kind != "observation":
            message = (
                f"the event is not an observation but an {row.kind}; get_event serves observations"
            )
            reads.append(Read(ErrorMark(uri, message), None, None, event=event_id))
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
            reads.append(Read(ErrorMark(uri, message), None, None, event=event_id))
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
