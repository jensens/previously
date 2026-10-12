# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assertions in the log: the write path, reading by folding, and what the
policy says of a thread.

`core/assertion.py` holds the form and the folding and touches no database;
this module writes and reads.

**The write path** is the second one beside `append` for an event that is not
an action. It writes a batch in one transaction, the way `append` does, and
retries a lost chain position the way `append` does ({ref}`concurrency`).
Inside that transaction, in this order:

- it locks every source event, ascending, with the row lock an erasure takes
  ({ref}`erasure`), and refuses a source that is missing, erased or no
  observation, and a cited unit that is missing or erased;
- it reads the tip, and below it every assertion: a handle that one of them
  carries already makes the call a repeat, and the ids of those are the
  answer, with nothing written;
- it checks what each statement names (`subject`, `approves`, `of`,
  `replaces`) against what stands below the tip, the statements before it in
  the same batch included;
- it writes every statement on that tip.

The lock is what keeps an erasure from falling between the check and the
write. An erasure that comes first is committed when the lock is granted,
and the source reads as erased. An erasure that comes second waits at the
lock, and once it holds it, reads the assertions again and finds the one
written here (`core/redact.py`).

An assertion rests on observations only. A source that is an action or
another assertion would make the cascade of an erasure follow a cascade, and
an assertion is meant to say in its own words what was observed.

**A refusal** is `AssertionRefused` with one sentence. The sentence names ids
and never the text of an assertion or an address: it can end up on a
terminal, in a log of the MCP server, or in front of a client that may not see
the sources.
"""

from dataclasses import dataclass
from dataclasses import field
from previously.core.action import retrying
from previously.core.append import MAX_BATCH
from previously.core.assertion import assertion_problem
from previously.core.assertion import DecisionBody
from previously.core.assertion import fold
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import payload_of
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.decide import Candidate
from previously.core.decide import circles_of
from previously.core.decide import decide
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.hashing import iso_utc
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import EventRow
    from previously.contract.store import LogStore
    from previously.contract.store import RedactionStore
    from previously.core.assertion import Thread
    from previously.core.chain import Prepared
    from previously.core.decide import Decision
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.core.redaction import RedactionIndex


ASSERTION: Final = "assertion"
_OBSERVATION: Final = "observation"
_CIRCLE: Final = "circle:"
_ADDRESS: Final = "address:"


class AssertionRefused(PreviouslyError):
    """A batch the write path does not write: one sentence, nothing written,
    no text of an assertion and no address in it."""


# --- reading ------------------------------------------------------------------------


def _rows[Conn](
    log: LogStore[Conn], conn: Conn, *, up_to: int | None = None
) -> list[tuple[int, datetime, Mapping[str, object] | None]]:
    return [
        (row.id, row.recorded_at, row.payload)
        for row in log.read_by_kind(conn, ASSERTION)
        if up_to is None or row.id <= up_to
    ]


def read_threads[Conn](log: LogStore[Conn], conn: Conn) -> dict[int, Thread]:
    """Every thread that stands, by its name, folded from every assertion in
    the log. Nothing is kept beside the log: the state is computed, and an
    erased version falls out of it the moment it is erased."""
    return fold(_rows(log, conn))


def sources_named(payload: Mapping[str, object]) -> tuple[Source, ...]:
    """The sources a payload names, read leniently: an entry without an
    event id is passed over, and units that are not a list of whole numbers
    count as the whole event.

    For the erasure cascade, which has to find an assertion whose form is
    broken as well (`verify` reports the form): reading more of an event than
    the assertion meant can only erase more, which is the safe direction.
    """
    listed = payload.get("sources")
    if not isinstance(listed, list):
        return ()
    found: list[Source] = []
    for entry in cast("list[object]", listed):
        if not isinstance(entry, dict):
            continue
        named = cast("Mapping[str, object]", entry)
        event = named.get("event")
        if not isinstance(event, int) or isinstance(event, bool):
            continue
        units = named.get("units")
        seqs = (
            [seq for seq in cast("list[object]", units) if isinstance(seq, int)]
            if isinstance(units, list)
            else None
        )
        found.append(Source(event, tuple(seqs) if seqs else None))
    return tuple(found)


def stands_on_erased(index: RedactionIndex, assertion_id: int, sources: Iterable[Source]) -> bool:
    """Whether a redaction erased what the assertion `assertion_id` rests on:
    a source event, a unit it cites, or, for a source it cites whole, a unit
    of that event erased **after** the assertion.

    The last condition is the one that needs the position. A whole event
    whose unit was erased before the assertion was written is what stood
    then, and the assertion carries nothing of the erased unit; a unit erased
    after it may be what the assertion repeats. The erasure cascade and
    `verify` both ask this question, so that the cascade erases exactly what
    `verify` would otherwise report.
    """
    for source in sources:
        if index.of_event(source.event) is not None:
            return True
        if source.units is not None:
            if any(index.of_unit(source.event, seq) is not None for seq in source.units):
                return True
            continue
        if any(
            redaction.scope == "units"
            and redaction.event == source.event
            and redaction.id > assertion_id
            for redaction in index
        ):
            return True
    return False


# --- writing ------------------------------------------------------------------------


@dataclass
class _View:
    """What stands below the tip, and what the statements of the batch so far
    added to it: enough to check what a statement names."""

    kinds: dict[int, str] = field(default_factory=lambda: {})  # thread name -> kind
    versions: dict[int, tuple[int, Statement]] = field(default_factory=lambda: {})
    approved: set[int] = field(default_factory=lambda: set[int]())
    rejected: set[int] = field(default_factory=lambda: set[int]())

    @classmethod
    def of(cls, threads: Mapping[int, Thread]) -> _View:
        view = cls()
        for name, thread in threads.items():
            view.kinds[name] = thread.kind
            for version in thread.versions:
                view.versions[version.id] = (name, version.statement)
            view.approved |= thread.approved
            view.rejected |= thread.rejected
        return view

    def add(self, event_id: int, statement: Statement) -> None:
        if statement.kind == REJECTION:
            self.rejected.add(cast("int", statement.of))
            return
        name = event_id if statement.subject is None else statement.subject
        self.kinds.setdefault(name, statement.kind)
        self.versions[event_id] = (name, statement)
        if statement.approves is not None:
            self.approved.add(statement.approves)


def _named(kind: str) -> str:
    return f"an {kind}" if kind[0] in "aeiou" else f"a {kind}"


def _proposal(view: _View, version_id: int) -> Statement:
    """The statement of an open version that is neither approved nor
    rejected, or the refusal that says why `version_id` is none."""
    _name, statement = view.versions[version_id]
    if statement.responsibility != OPEN:
        raise AssertionRefused(f"the version {version_id} is no proposal: it is direct")
    if version_id in view.approved:
        raise AssertionRefused(f"the proposal {version_id} is already approved")
    if version_id in view.rejected:
        raise AssertionRefused(f"the proposal {version_id} is already rejected")
    return statement


def _check_rejection(view: _View, statement: Statement) -> None:
    of = cast("int", statement.of)
    if of not in view.versions:
        raise AssertionRefused(f"of names {of}, which is no proposal that stands")
    proposal = _proposal(view, of)
    # A rejection takes the sources of its proposal, so that it goes with
    # the proposal when one of them is erased.
    if statement.sources != proposal.sources:
        raise AssertionRefused("a rejection takes the sources of its proposal unchanged")


def _check_version(view: _View, statement: Statement) -> None:
    """What a version of an obligation or a decision names: a subject that
    stands and is of its kind, a decision it replaces, and for an approval an
    open version of its thread that is neither approved nor rejected yet,
    taken over unchanged. Approving twice, or after a rejection, would let a
    second answer to one proposal stand beside the first
    ({ref}`assertions-approval`; decision 5 of the 2026-10-12 assertions plan,
    and ruling F-3 of the 2026-10-12 assertions plan)."""
    subject = statement.subject
    if subject is not None:
        kind = view.kinds.get(subject)
        if kind is None:
            raise AssertionRefused(
                f"the subject {subject} names no obligation or decision that stands"
            )
        if kind != statement.kind:
            raise AssertionRefused(
                f"the subject {subject} is {_named(kind)}, "
                f"and this statement is {_named(statement.kind)}"
            )
    body = statement.body
    if (
        isinstance(body, DecisionBody)
        and body.replaces is not None
        and view.kinds.get(body.replaces) != "decision"
    ):
        raise AssertionRefused(f"replaces names {body.replaces}, which is no decision that stands")
    approves = statement.approves
    if approves is None:
        return
    found = view.versions.get(approves)
    if found is None or found[0] != subject:
        raise AssertionRefused(
            f"approves names {approves}, which is no proposal of the subject {subject}"
        )
    proposal = _proposal(view, approves)
    # Approving is making the proposal one's own: the content, the sources
    # and the author stay, and only the responsibility changes.
    # The reason may be the approver's.
    if (
        statement.body != proposal.body
        or statement.sources != proposal.sources
        or statement.author != proposal.author
    ):
        raise AssertionRefused(
            "an approval takes the content, the sources and the author of its proposal unchanged"
        )


def _check_references(
    threads: Mapping[int, Thread], statements: Sequence[Statement], first_id: int
) -> None:
    """Each statement against what stands below the tip and what the ones
    before it in the batch add, as they will stand once written."""
    view = _View.of(threads)
    for offset, statement in enumerate(statements):
        if statement.kind == REJECTION:
            _check_rejection(view, statement)
        else:
            _check_version(view, statement)
        view.add(first_id + offset, statement)


def _check_sources[Conn](
    log: LogStore[Conn],
    conn: Conn,
    rows: Mapping[int, EventRow | None],
    statements: Sequence[Statement],
) -> None:
    """Every source exists, is an observation and is not erased, and every
    unit it cites exists and is not erased; `rows` are the locked rows."""
    for event_id, row in rows.items():
        if row is None:
            raise AssertionRefused(f"there is no event {event_id} to rest on")
        if row.kind != _OBSERVATION:
            raise AssertionRefused(
                f"event {event_id} is not an observation, and only one can be a source"
            )
        if row.payload is None:
            raise AssertionRefused(f"event {event_id} is erased and cannot be a source")
    cited = sorted(
        {s.event for statement in statements for s in statement.sources if s.units is not None}
    )
    units = log.units_by_event(conn, cited)
    for statement in statements:
        for source in statement.sources:
            held = {unit.seq: unit for unit in units.get(source.event, [])}
            for seq in source.units or ():
                if seq not in held:
                    raise AssertionRefused(f"event {source.event} has no unit {seq}")
                if held[seq].content is None:
                    raise AssertionRefused(
                        f"unit {seq} of event {source.event} is erased and cannot be a source"
                    )


def _check_batch(statements: Sequence[Statement]) -> list[Mapping[str, object]]:
    """The payloads of the batch, or the refusal of a batch that cannot be
    written whatever the log holds."""
    if not statements:
        raise AssertionRefused("there is no statement to write")
    if len(statements) > MAX_BATCH:
        raise AssertionRefused(f"a batch holds at most {MAX_BATCH} statements")
    if len({statement.handle for statement in statements}) > 1:
        raise AssertionRefused("the statements of one batch carry different handles")
    payloads: list[Mapping[str, object]] = []
    for statement in statements:
        payload = payload_of(statement)
        problem = assertion_problem(payload)
        if problem is not None:
            raise AssertionRefused(f"a statement has no valid form: {problem}")
        payloads.append(payload)
    return payloads


def _prepare(payloads: Sequence[Mapping[str, object]], recorded_at: datetime) -> list[Prepared]:
    """Prepared once, before the first attempt, as `append` prepares: the
    payload does not depend on anything read under the lock, and a retry only
    links again."""
    try:
        return [
            prepare(kind=ASSERTION, occurred_at=recorded_at, payload=p, units=(), key=None)
            for p in payloads
        ]
    except InvalidPayload as error:
        # The canonical form names a path and what it refused, never the
        # string it found there.
        raise AssertionRefused(f"a statement cannot be written: {error}") from error


def _repeated(
    below: Sequence[tuple[int, datetime, Mapping[str, object] | None]], handle: str | None
) -> tuple[int, ...]:
    """The ids of the assertions below the tip that carry `handle`."""
    if handle is None:
        return ()
    return tuple(
        event_id
        for event_id, _at, payload in below
        if payload is not None and payload.get("handle") == handle
    )


def _check_all[Conn](
    log: LogStore[Conn],
    conn: Conn,
    rows: Mapping[int, EventRow | None],
    below: Sequence[tuple[int, datetime, Mapping[str, object] | None]],
    statements: Sequence[Statement],
    top: int,
) -> None:
    """The checks the write path runs under its locks and `check_statements`
    runs without: the sources, then the references against what stands below
    the tip and what the batch adds."""
    _check_sources(log, conn, rows, statements)
    _check_references(fold(below), statements, top + 1)


def check_statements[Conn](
    log: LogStore[Conn], conn: Conn, statements: Sequence[Statement]
) -> None:
    """Refuses with `AssertionRefused` a batch that `write_statements` would
    refuse now, with the same sentence, and writes and locks nothing.

    For a preview, so that nobody confirms what cannot be written. It is no
    promise: an erasure can still fall between this check and the write, and
    the write path checks again under its locks. A batch whose handle an
    assertion in the log carries is a repeat, which `write_statements`
    answers with the ids and does not refuse, so it passes here too.
    """
    _check_batch(statements)
    events = sorted({source.event for statement in statements for source in statement.sources})
    rows: dict[int, EventRow | None] = {}
    for event_id in events:
        row = next(iter(log.read(conn, event_id, 1)), None)
        rows[event_id] = row if row is not None and row.id == event_id else None
    tip = log.tip(conn)
    top = 0 if tip is None else tip.id
    below = _rows(log, conn, up_to=top)
    if _repeated(below, statements[0].handle):
        return
    _check_all(log, conn, rows, below, statements, top)


def write_statements[Conn](
    log: LogStore[Conn],
    locker: RedactionStore[Conn],
    statements: Sequence[Statement],
    *,
    recorded_at: datetime,
) -> tuple[int, ...]:
    """Writes the statements in one transaction and returns their ids, or
    refuses the batch with `AssertionRefused` and writes nothing.

    A batch whose handle an assertion in the log carries already writes
    nothing and returns the ids of the assertions that carry it and still
    stand: confirming twice is harmless ({ref}`mcp-writing`; decision 9 of
    the 2026-10-12 assertions plan). The module
    docstring says in which order the rest happens and why.

    The handle lives in the payload, and an erasure takes the payload, so a
    batch whose assertions were all erased since is written again when its
    handle comes back. That is accepted ({ref}`assertions-limits`; ruling
    F-7 of the 2026-10-12 assertions plan): the operator erased them, a
    handle lives ten minutes at most, and the client holds the text anyway.
    A source key would survive the erasure, and would be a second truth
    beside the payload. Where only
    some of the batch were erased, the ids of the ones that stand come back.

    The caller guarantees that one handle means one content: the lookup
    compares the handle and nothing else. Decision 9 has the MCP server seal
    the digest of the payloads into the handle, which binds the two.

    Two parameters for one store, the way `redact_event` takes them: the
    store that holds the log is the store that locks its rows.
    """
    iso_utc(recorded_at)  # fail early if naive
    payloads = _check_batch(statements)
    handle = statements[0].handle
    prepared = _prepare(payloads, recorded_at)
    events = sorted({source.event for statement in statements for source in statement.sources})

    def once(conn: Conn) -> tuple[int, ...]:
        # The locks first and the tip after them: a lock that waited for an
        # erasure returns the row as that erasure left it, and the tip read
        # afterwards stands above the redaction it wrote.
        rows = {event_id: locker.lock_event(conn, event_id) for event_id in events}
        tip = log.tip(conn)
        top = 0 if tip is None else tip.id
        # Every assertion in the log, read in this transaction: fine at the
        # volumes of the pilot, and what an index or a projection would
        # remove. The final review of the 2026-10-12 assertions plan
        # measures it at 5 000 assertions ({ref}`assertions-folded`).
        below = _rows(log, conn, up_to=top)
        repeated = _repeated(below, handle)
        if repeated:
            return repeated
        _check_all(log, conn, rows, below, statements, top)
        ids: list[int] = []
        prev_hash = None if tip is None else tip.hash
        for ready in prepared:
            row, linked = link(
                ready, event_id=top + 1 + len(ids), prev_hash=prev_hash, recorded_at=recorded_at
            )
            log.insert_event(conn, row, linked, None)
            ids.append(row.id)
            prev_hash = row.hash
        return tuple(ids)

    return retrying(log, once)


# --- policy -------------------------------------------------------------------------


def _identities(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
    listed = payload.get("channel_identities")
    if not isinstance(listed, list):
        return []
    return [
        cast("Mapping[str, object]", entry)
        for entry in cast("list[object]", listed)
        if isinstance(entry, dict)
    ]


def source_identities[Conn](
    log: LogStore[Conn], conn: Conn, thread: Thread
) -> tuple[list[Mapping[str, object]], tuple[str | None, ...]]:
    """The identities of every source event of every standing version of the
    thread, together, and the distinct sources (the `source` of the source
    key, `None` for an event without one) of those events, in the order of
    the events.

    Every version and not only the winner: a list shows the winner and counts
    the proposals, and the history shows them all, so the strictest rule
    among all of them is the one that holds. An event read as erased adds no
    identity; the cascade has erased an assertion on it by then.
    """
    events = sorted({s.event for version in thread.versions for s in version.statement.sources})
    keys = log.source_keys(conn, events)
    identities: list[Mapping[str, object]] = []
    for event_id in events:
        row = next(iter(log.read(conn, event_id, 1)), None)
        if row is None or row.id != event_id or row.payload is None:
            continue
        identities.extend(_identities(row.payload))
    sources = tuple(dict.fromkeys(keys[e][0] if e in keys else None for e in events))
    return identities, sources


def assertion_decisions(
    policy: Policy,
    client: Client,
    identities: Sequence[Mapping[str, object]],
    sources: Sequence[str | None],
) -> tuple[Decision, ...]:
    """The decisions for an assertion ({ref}`assertions-mentioned`; decision 7
    of the 2026-10-12 assertions plan): `decide` once per distinct source,
    each with the identities of all source events, in the order of the
    sources. No source at all is decided once, without one.

    Every decision is returned, so that a caller that records which rules
    decided (the access log of the MCP server) sees the rule of every source
    and not only of the one that happened to be last.
    """
    candidate = Candidate(provider=client.processor, model="", effort=None)
    order: tuple[str | None, ...] = tuple(sources) or (None,)
    return tuple(
        decide(policy, identities=identities, source=source, candidates=(candidate,))
        for source in order
    )


def assertion_verdict(
    policy: Policy,
    client: Client,
    identities: Sequence[Mapping[str, object]],
    sources: Sequence[str | None],
) -> Decision:
    """The decision that holds for an assertion: the first of
    `assertion_decisions` that chooses nothing, so that the strictest rule
    holds; when every one chooses, the last."""
    decisions = assertion_decisions(policy, client, identities, sources)
    return next((d for d in decisions if d.chosen is None), decisions[-1])


def _actors(statement: Statement) -> tuple[str, ...]:
    body = statement.body
    if isinstance(body, ObligationBody):
        return (body.debtor, body.creditor)
    if isinstance(body, DecisionBody):
        return body.by
    return ()


def thread_circles(
    policy: Policy, identities: Sequence[Mapping[str, object]], statement: Statement
) -> tuple[str, ...]:
    """Where an assertion appears when a list is filtered by circle:
    the circles of its sources, every `circle:` it names as an actor, and the
    circles of every `address:` it names.

    The filter sorts and grants nothing: what the policy withholds stays a
    placeholder. A `circle:` counts whether or not the policy knows the
    circle, since an assertion describes the world and not the policy; an
    address counts as a source's does, own addresses left out.
    """
    circles = set(circles_of(policy, identities))
    for actor in _actors(statement):
        if actor.startswith(_CIRCLE):
            circles.add(actor.removeprefix(_CIRCLE))
        elif actor.startswith(_ADDRESS):
            circles.update(circles_of(policy, [{"address": actor.removeprefix(_ADDRESS)}]))
    return tuple(sorted(circles))
