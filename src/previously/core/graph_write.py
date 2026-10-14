# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Entities and relations in the log: the write path and its preview,
reading the graph, and what the policy says of a claim.

`core/graph.py` holds the form and the fold and touches no database; this
module writes and reads, as `core/assertions.py` does for obligations and
decisions, and in the same order inside one transaction ({ref}`concurrency`):

- it locks every source event, ascending, with the row lock an erasure takes,
  and refuses a source with the sentences of `check_sources`, the ones an
  obligation's source is refused with;
- it reads the tip, and below it every assertion: a handle that one of them
  carries already makes the call a repeat, and the ids of those are the
  answer, with nothing written;
- it reads the vocabulary and the approval classes, after the tip: an event
  of either that joins the chain after the tip takes the position this write
  wanted, the insert fails, and the next attempt reads again;
- it takes the claims one by one, sets the level of each, and checks its
  form, what it names, the vocabulary, the answer to a question and the
  cycle rule against the graph folded from below the tip and from the claims
  before it in the batch, as they will stand once written;
- it writes every claim on that tip.

**The level is the write path's**, never the client's. The operator's claims
are direct as given. A model's claim that is no approval becomes an
objection, open and contesting the winner, when the thread it names has a
direct winner (the operator stands for that one, and a model does not
overwrite it), and stays open on a thread whose question it does not answer
with a candidate; otherwise the approval classes decide between transitive
and open. `check_claims` says what the write would decide now, and
`write_claims` with `expect` refuses a batch whose decision has moved since,
instead of writing it otherwise than shown.

**A cycle needs no lock of its own** (decision 13 of the 2026-10-14
assignments plan): the graph is folded under the tip, and every claim goes
right after it, so two writes that each close half a cycle cannot both win
the position; the one that loses tries again, with the other's edge folded
in, and is refused.

**A refusal** is `GraphRefused` with one sentence, for a source too, whose
sentences the two write paths share. The sentence names ids and never a
value of a field or an address, for the reasons `core/assertions.py`
gives.
"""

from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import replace
from previously.core.action import retrying
from previously.core.append import MAX_BATCH
from previously.core.assertion import DIRECT
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import Source
from previously.core.assertions import ASSERTION
from previously.core.assertions import assertion_decisions
from previously.core.assertions import AssertionRefused
from previously.core.assertions import check_sources
from previously.core.assertions import read_events
from previously.core.assertions import read_sources
from previously.core.canonical import canonical
from previously.core.chain import link
from previously.core.chain import prepare
from previously.core.classes import read_classes
from previously.core.decide import Candidate
from previously.core.decide import decide
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.graph import claim_payload
from previously.core.graph import claim_problem
from previously.core.graph import conformance_problem
from previously.core.graph import ENTITY
from previously.core.graph import fold_graph
from previously.core.graph import GRAPH_KINDS
from previously.core.graph import GraphFold
from previously.core.graph import GraphVersion
from previously.core.graph import level_of
from previously.core.graph import LEVELS
from previously.core.graph import parse_claim
from previously.core.graph import RECOLLECTION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import STANDING
from previously.core.graph import TRANSITIVE
from previously.core.hashing import iso_utc
from previously.core.vocabulary import ACYCLIC
from previously.core.vocabulary import read_vocabulary
from previously.core.vocabulary import RELATION_KIND
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import EventRow
    from previously.contract.rows import Tip
    from previously.contract.store import LogStore
    from previously.contract.store import RedactionStore
    from previously.core.assertions import SourceEvents
    from previously.core.classes import Classes
    from previously.core.decide import Decision
    from previously.core.graph import Claim
    from previously.core.graph import ClassState
    from previously.core.graph import Graph
    from previously.core.graph import GraphThread
    from previously.core.policy import Client
    from previously.core.policy import Policy
    from previously.core.vocabulary import Vocabulary


CLASS_CHANGED: Final = "the approval class changed since the preview; call again without confirm"
DIRECT_WRITTEN: Final = "a direct version was written since the preview; call again without confirm"

type _Row = tuple[int, datetime, Mapping[str, object] | None]


class GraphRefused(PreviouslyError):
    """A batch of entities and relations the write path does not write: one
    sentence, nothing written, no value of a field and no address in it."""


@dataclass(frozen=True)
class Decided:
    """What the write path decided for one claim, as a preview shows it:
    its level, the class it stands under, and the direct version it
    contests as an objection."""

    level: str
    under: int | None
    contests: int | None


def decided(claim: Claim) -> Decided:
    """The decision a claim that `check_claims` returned carries."""
    return Decided(claim.responsibility, claim.under, claim.contests)


@dataclass(frozen=True)
class Written:
    """The ids of a batch, in its order, and the level each was written at."""

    ids: tuple[int, ...]
    levels: tuple[str, ...]


# --- reading ------------------------------------------------------------------------


def _rows[Conn](log: LogStore[Conn], conn: Conn, *, up_to: int | None = None) -> list[_Row]:
    return [
        (row.id, row.recorded_at, row.payload)
        for row in log.read_by_kind(conn, ASSERTION)
        if up_to is None or row.id <= up_to
    ]


def read_graph[Conn](log: LogStore[Conn], conn: Conn, *, as_of: datetime | None = None) -> Graph:
    """The graph folded from every assertion in the log, under the approval
    classes in force; with `as_of`, from those recorded up to that moment,
    under the classes in force then.

    An erasure is for good: what was erased reads as erased under every
    `as_of`, as a past day of the policy does.
    """
    classes = read_classes(log, conn, at=as_of)
    rows = [
        (row.id, row.recorded_at, row.payload)
        for row in log.read_by_kind(conn, ASSERTION)
        if as_of is None or row.recorded_at <= as_of
    ]
    return fold_graph(rows, classes.states)


class EntityTypes(Mapping[int, str]):
    """The kind of every entity that stands in a graph, by id, looked up one
    id at a time.

    What `graph.entities()` gives, without walking every thread: a check of
    one claim asks for its ends and its `ref` fields, and the write path and
    `verify` ask once per claim.
    """

    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    def __getitem__(self, key: int) -> str:
        thread = self._graph.threads.get(key)
        winner = None if thread is None else thread.winner(self._graph.classes)
        if thread is None or thread.kind != ENTITY or winner is None:
            raise KeyError(key)
        if winner.claim.body.state == RETRACTED:
            raise KeyError(key)
        return winner.claim.body.type

    def __iter__(self) -> Iterator[int]:
        return iter(self._graph.entities())

    def __len__(self) -> int:
        return len(self._graph.entities())


def starts_thread(claim: Claim, thread: GraphThread | None) -> bool:
    """Whether a claim makes a new entity or relation, which a retired kind
    does not take (Review Focus 4 of the 2026-10-14 assignments plan).

    A first version is new. So is a version that would stand for the
    operator, direct or transitive, on a thread on which no direct or
    transitive version ever stood, an approval of any of its proposals
    among them: until then the entity was only proposed, and the proposal
    of a kind retired since must not become one that stands (ruling T4-e
    of the 2026-10-14 assignments plan). A further version of one that
    stood is not new, so it may be renamed, closed or retracted, and
    neither is an open one, which stands for nobody, or a retraction,
    which makes nothing stand. `thread` is the thread before the claim;
    `None` for a subject whose every version is erased, of which nothing
    is known any more, and which is not counted as new.
    """
    if claim.subject is None:
        return True
    if thread is None or claim.responsibility == OPEN or claim.body.state == RETRACTED:
        return False
    return not any(v.claim.responsibility in (DIRECT, TRANSITIVE) for v in thread.versions)


def pending_question(
    thread: GraphThread | None, classes: Mapping[int, ClassState]
) -> RelationBody | None:
    """The body of the question that waits on `thread`, or None."""
    question = None if thread is None else thread.question(classes)
    body = None if question is None else question.claim.body
    return body if isinstance(body, RelationBody) else None


def names_a_candidate(claim: Claim, asked: RelationBody) -> bool:
    """Whether a claim is a relation that stands and points at one of the
    candidates of the question `asked`: the only way to answer it."""
    body = claim.body
    return (
        isinstance(body, RelationBody)
        and body.state == STANDING
        and body.to in (asked.candidates or ())
    )


def closes_cycle(graph: Graph, claim: Claim, vocabulary: Vocabulary, *, level: str) -> bool:
    """Whether a standing relation of a kind with the behavior `acyclic`
    would close a cycle if it stood: an edge from an entity to itself, or one
    whose end already reaches its start over the relations of its kind.

    `graph` is what stands before the claim. The claim's own thread is left
    out, since the claim replaces its edge, so a new version that turns an
    edge around is held against the other edges and not against its own
    old one. An open write is held against the edges of every level, and a
    direct or transitive one against direct and transitive edges only: a
    proposal nobody stands for does not veto what the operator stands for
    (ruling T2-b of the 2026-10-14 assignments plan). The write path and
    `verify` ask this one question, so that `verify` reports exactly what
    the write path would have refused.
    """
    body = claim.body
    if not isinstance(body, RelationBody) or body.state != STANDING or body.to is None:
        return False
    if isinstance(body.start, Source):
        return False
    spec = vocabulary.kind(RELATION_KIND, body.type)
    if spec is None or ACYCLIC not in spec.behaviors:
        return False
    if body.start == body.to:
        return True
    levels = frozenset(LEVELS) if level == OPEN else frozenset({DIRECT, TRANSITIVE})
    without = frozenset[int]() if claim.subject is None else frozenset({claim.subject})
    return graph.reaches(
        body.to, body.start, frozenset({body.type}), without=without, levels=levels
    )


def takes_proposal(approval: Claim, proposal: Claim) -> bool:
    """Whether an approval takes its proposal unchanged: the content, the
    evidence, the sources, the author and the confidence; the reason may be
    the approver's.

    One change is allowed, to a question: its approval answers it, with `to`
    one of the candidates in place of the candidates. That is how the
    operator answers a model's question in the model's words, as an approval
    keeps them (Task 6 of the 2026-10-14 assignments plan).
    """
    if (
        approval.author != proposal.author
        or approval.evidence != proposal.evidence
        or approval.sources != proposal.sources
        or approval.confidence != proposal.confidence
    ):
        return False
    body, asked = approval.body, proposal.body
    if body == asked:
        return True
    return (
        isinstance(body, RelationBody)
        and isinstance(asked, RelationBody)
        and asked.candidates is not None
        and body.candidates is None
        and body.to in asked.candidates
        and replace(body, to=None, candidates=asked.candidates) == asked
    )


# --- writing ------------------------------------------------------------------------


def _named(kind: str) -> str:
    return f"an {kind}" if kind[0] in "aeiou" else f"a {kind}"


def _check_batch(claims: Sequence[Claim]) -> None:
    """The refusal of a batch that cannot be written whatever the log holds,
    in the sentences of `core/assertions.py`."""
    if not claims:
        raise GraphRefused("there is no statement to write")
    if len(claims) > MAX_BATCH:
        raise GraphRefused(f"a batch holds at most {MAX_BATCH} statements")
    if len({claim.handle for claim in claims}) > 1:
        raise GraphRefused("the statements of one batch carry different handles")


def _levelled(claim: Claim, graph: Graph, classes: Classes, recorded_at: datetime) -> Claim:
    """The claim at the level the write path gives it: the operator's as
    given and direct, an approval as given, and a model's other claims an
    objection against a direct winner, else at the level of its class."""
    if claim.approves is not None:
        return claim
    if claim.author == OPERATOR:
        if claim.responsibility != DIRECT:
            raise GraphRefused("a version by the operator is direct")
        return claim
    thread = None if claim.subject is None else graph.threads.get(claim.subject)
    winner = None if thread is None else thread.winner(graph.classes)
    if winner is not None and level_of(winner, graph.classes) == DIRECT:
        # A model never overwrites what the operator stands for: it objects,
        # and the objection waits for him whatever its confidence.
        return replace(claim, responsibility=OPEN, under=None, contests=winner.id)
    asked = pending_question(thread, graph.classes)
    if asked is not None and not names_a_candidate(claim, asked):
        # A transitive version answers a question (ruling T2-c), and a class
        # must not answer it with what it never offered: the claim stays a
        # proposal, and the question stays pending (ruling T4-d of the
        # 2026-10-14 assignments plan).
        return replace(claim, responsibility=OPEN, under=None, contests=None)
    body = claim.body
    if isinstance(body, RelationBody) and body.candidates is not None:
        # A question asks the operator; no class answers it in advance.
        return replace(claim, responsibility=OPEN, under=None, contests=None)
    level, under = classes.level(
        author=claim.author,
        kind=claim.kind,
        type_name=body.type,
        confidence=claim.confidence,
        recorded_at=recorded_at,
    )
    return replace(claim, responsibility=level, under=under, contests=None)


def _payload(claim: Claim) -> Mapping[str, object]:
    payload = claim_payload(claim)
    problem = claim_problem(payload)
    if problem is not None:
        raise GraphRefused(f"a statement has no valid form: {problem}")
    # As in core/assertions.py: refused here, so that the preview refuses it
    # too, naming a path and never the string it found there.
    try:
        canonical(payload)
    except InvalidPayload as error:
        raise GraphRefused(f"a statement cannot be written: {error}") from error
    return payload


def _check_subject(graph: Graph, claim: Claim) -> GraphThread | None:
    subject = claim.subject
    if subject is None:
        return None
    thread = graph.threads.get(subject)
    if thread is None:
        raise GraphRefused(f"the subject {subject} names no entity or relation that stands")
    if thread.kind != claim.kind:
        raise GraphRefused(
            f"the subject {subject} is {_named(thread.kind)}, "
            f"and this statement is {_named(claim.kind)}"
        )
    return thread


def _check_approval(graph: Graph, thread: GraphThread, claim: Claim) -> None:
    """An approval names an open or transitive version of its thread that is
    neither approved nor rejected and that no direct version overtook, and
    takes it unchanged; the sentences are those of `core/assertions.py`
    where they mean the same."""
    approves, subject = claim.approves, thread.subject
    version = next((v for v in thread.versions if v.id == approves), None)
    if version is None:
        raise GraphRefused(
            f"approves names {approves}, which is no proposal of the subject {subject}"
        )
    if level_of(version, graph.classes) == DIRECT:
        raise GraphRefused(f"the version {approves} is no proposal: it is direct")
    if version.id in thread.approved:
        raise GraphRefused(f"the proposal {approves} is already approved")
    if version.id in thread.rejected:
        raise GraphRefused(f"the proposal {approves} is already rejected")
    newer = max((v.id for v in thread.versions if v.claim.responsibility == DIRECT), default=0)
    if newer > version.id:
        raise GraphRefused(
            f"the proposal {approves} is overtaken: the direct version {newer} came after it"
        )
    if not takes_proposal(claim, version.claim):
        raise GraphRefused(
            "an approval takes the content, the sources and the author of its proposal unchanged"
        )


def _check_answer(graph: Graph, thread: GraphThread | None, claim: Claim) -> None:
    """A direct relation that stands, on a thread whose question is pending,
    answers it, and has to name one of its candidates. A retraction asserts
    nothing about the ends and answers it with none."""
    body = claim.body
    if claim.responsibility != DIRECT or not isinstance(body, RelationBody):
        return
    if body.state != STANDING:
        return
    asked = pending_question(thread, graph.classes)
    if asked is not None and not names_a_candidate(claim, asked):
        raise GraphRefused(f"the answer names {body.to}, which is none of the candidates")


def _check_claim(graph: Graph, claim: Claim, vocabulary: Vocabulary) -> None:
    """What one claim at its level names, against `graph`, which holds what
    stands before it."""
    thread = _check_subject(graph, claim)
    if claim.approves is not None and thread is not None:
        _check_approval(graph, thread, claim)
    problem = conformance_problem(
        claim,
        vocabulary,
        new_thread=starts_thread(claim, thread),
        entity_types=EntityTypes(graph),
    )
    if problem is not None:
        raise GraphRefused(problem)
    _check_answer(graph, thread, claim)
    if closes_cycle(graph, claim, vocabulary, level=claim.responsibility):
        raise GraphRefused("the relation would close a cycle over a kind that is acyclic")


def _checked[Conn](
    log: LogStore[Conn],
    conn: Conn,
    rows: Mapping[int, EventRow | None],
    below: Sequence[_Row],
    claims: Sequence[Claim],
    top: int,
    *,
    recorded_at: datetime,
    expect: Sequence[Decided] | None,
) -> list[tuple[Claim, Mapping[str, object]]]:
    """The checks the write path runs under its locks and `check_claims`
    runs without, and the claims at their levels with their payloads."""
    try:
        check_sources(log, conn, rows, [s for claim in claims for s in claim.sources])
    except AssertionRefused as error:
        # The sentence of obligations, under the one class a caller of this
        # write path catches.
        raise GraphRefused(str(error)) from error
    vocabulary = read_vocabulary(log, conn)
    classes = read_classes(log, conn)
    folded = GraphFold()
    for row_id, at, payload in below:
        folded.add(row_id, at, payload, classes.states)
    checked: list[tuple[Claim, Mapping[str, object]]] = []
    for offset, given in enumerate(claims):
        graph = folded.current(classes.states)
        claim = _levelled(given, graph, classes, recorded_at)
        if expect is not None:
            _check_expected(expect[offset], decided(claim))
        payload = _payload(claim)
        _check_claim(graph, claim, vocabulary)
        folded.add(top + 1 + offset, recorded_at, payload, classes.states)
        checked.append((claim, payload))
    return checked


def _check_expected(shown: Decided, now: Decided) -> None:
    """Refuses a claim whose decision under the tip is not the one the
    preview showed (Review Focus 2 of the 2026-10-14 assignments plan;
    ruling T4-e). A direct version written since turns a claim into an
    objection, or into one against another version, and says so; any other
    change of the level or the class is a class that changed."""
    if shown.contests != now.contests:
        raise GraphRefused(DIRECT_WRITTEN)
    if (shown.level, shown.under) != (now.level, now.under):
        raise GraphRefused(CLASS_CHANGED)


def _repeated(below: Sequence[_Row], handle: str | None) -> list[tuple[int, Mapping[str, object]]]:
    """The entities and relations below the tip that carry `handle`.

    Only these: an obligation batch with the same handle is another write
    path's, and answering with its ids would hand the caller ids of
    something it never wrote (ruling T4-e of the 2026-10-14 assignments
    plan). `core/assertions.py` keeps to its own kinds the same way.
    """
    if handle is None:
        return []
    return [
        (event_id, payload)
        for event_id, _at, payload in below
        if payload is not None
        and payload.get("assertion") in GRAPH_KINDS
        and payload.get("handle") == handle
    ]


def check_claims[Conn](
    log: LogStore[Conn], conn: Conn, claims: Sequence[Claim], *, recorded_at: datetime
) -> tuple[Claim, ...]:
    """The claims at the levels `write_claims` would give them now, or the
    refusal it would give now, with the same sentence; locks and writes
    nothing (decision 9 of the 2026-10-14 assignments plan).

    For a preview, and no promise: a vocabulary event, a class or an
    erasure can still fall between it and the write, which checks again
    under the tip. A batch whose handle an assertion in the log carries is a
    repeat, which the write answers with what it wrote then, so it is
    answered here with the claims that stand under that handle.
    """
    iso_utc(recorded_at)  # fail early if naive
    _check_batch(claims)
    events = sorted({source.event for claim in claims for source in claim.sources})
    rows = read_sources(log, conn, events)
    tip = log.tip(conn)
    top = 0 if tip is None else tip.id
    below = _rows(log, conn, up_to=top)
    repeated = _repeated(below, claims[0].handle)
    if repeated:
        return tuple(
            claim for _id, payload in repeated if (claim := parse_claim(payload)) is not None
        )
    checked = _checked(log, conn, rows, below, claims, top, recorded_at=recorded_at, expect=None)
    return tuple(claim for claim, _payload in checked)


def _append[Conn](
    log: LogStore[Conn],
    tip: Tip | None,
    conn: Conn,
    payloads: Sequence[Mapping[str, object]],
    recorded_at: datetime,
) -> tuple[int, ...]:
    ids: list[int] = []
    prev_hash = None if tip is None else tip.hash
    top = 0 if tip is None else tip.id
    for payload in payloads:
        # Prepared on every attempt, as an action is: the level, and with it
        # the payload, depends on what this attempt read under the tip.
        ready = prepare(
            kind=ASSERTION, occurred_at=recorded_at, payload=payload, units=(), key=None
        )
        row, linked = link(
            ready, event_id=top + 1 + len(ids), prev_hash=prev_hash, recorded_at=recorded_at
        )
        log.insert_event(conn, row, linked, None)
        ids.append(row.id)
        prev_hash = row.hash
    return tuple(ids)


def write_claims[Conn](
    log: LogStore[Conn],
    locker: RedactionStore[Conn],
    claims: Sequence[Claim],
    *,
    recorded_at: datetime,
    expect: Sequence[Decided] | None = None,
) -> Written:
    """Writes the claims in one transaction, at the levels the write path
    gives them, and returns their ids and levels; or refuses the batch with
    `GraphRefused` and writes nothing.

    With `expect`, the decisions a preview showed, one per claim, as
    `decided` gives them for what `check_claims` returned: a claim that
    under the tip contests another direct version, or none where it
    contested one, is refused with `DIRECT_WRITTEN`, and one at another
    level or under another class with `CLASS_CHANGED` (Review Focus 2 of
    the 2026-10-14 assignments plan). Without the comparison, a class
    revoked or set since the preview, or a direct version written since,
    would have the claim written otherwise than anybody was shown.

    A batch whose handle an assertion in the log carries writes nothing and
    returns the ids and levels of the assertions that carry it and still
    stand, as `write_statements` does. The module docstring says in which
    order the rest happens and why.
    """
    iso_utc(recorded_at)  # fail early if naive
    _check_batch(claims)
    if expect is not None and len(expect) != len(claims):
        raise ValueError("expect gives one decision per claim")
    handle = claims[0].handle
    events = sorted({source.event for claim in claims for source in claim.sources})

    def once(conn: Conn) -> Written:
        # The locks first and the tip after them, as in core/assertions.py.
        rows = {event_id: locker.lock_event(conn, event_id) for event_id in events}
        tip = log.tip(conn)
        top = 0 if tip is None else tip.id
        below = _rows(log, conn, up_to=top)
        repeated = _repeated(below, handle)
        if repeated:
            return Written(
                tuple(event_id for event_id, _payload in repeated),
                tuple(str(payload.get("responsibility")) for _id, payload in repeated),
            )
        checked = _checked(
            log,
            conn,
            rows,
            below,
            claims,
            top,
            recorded_at=recorded_at,
            expect=expect,
        )
        ids = _append(log, tip, conn, [payload for _claim, payload in checked], recorded_at)
        return Written(ids, tuple(claim.responsibility for claim, _payload in checked))

    return retrying(log, once)


# --- policy -------------------------------------------------------------------------


def read_claim_events[Conn](
    log: LogStore[Conn], conn: Conn, threads: Iterable[GraphThread]
) -> SourceEvents:
    """The source events of every standing version of `threads`, in two
    queries whatever their number, as `read_source_events` reads them for
    obligations and decisions."""
    return read_events(
        log,
        conn,
        (
            s.event
            for thread in threads
            for version in thread.versions
            for s in version.claim.sources
        ),
    )


def claim_sources(
    events: SourceEvents, thread: GraphThread
) -> tuple[list[Mapping[str, object]], tuple[str | None, ...]]:
    """The identities of every source event of every standing version of
    `thread`, and their distinct sources: what `SourceEvents.of` gives for an
    obligation, and for the same reason every version and not the winner
    alone."""
    return events.named(s.event for version in thread.versions for s in version.claim.sources)


def claim_decisions(
    policy: Policy,
    client: Client,
    identities: Sequence[Mapping[str, object]],
    sources: Sequence[str | None],
    *,
    recollection: bool,
) -> tuple[tuple[str | None, Decision], ...]:
    """Every decision `claim_verdict` takes, each with the source it was
    taken for: those of `assertion_decisions`, in their order, and then
    `recollection` for a recollection. For a caller that records which
    rules decided, and which source a withholding came from, as the MCP
    server does for an obligation."""
    candidate = Candidate(provider=client.processor, model="", effort=None)
    decisions: list[tuple[str | None, Decision]] = []
    if sources or identities or not recollection:
        decided_on = assertion_decisions(policy, client, identities, sources)
        decisions.extend(zip(tuple(sources) or (None,), decided_on, strict=True))
    if recollection:
        decisions.append(
            (
                RECOLLECTION,
                decide(policy, identities=(), source=RECOLLECTION, candidates=(candidate,)),
            )
        )
    return tuple(decisions)


def claim_verdict(
    policy: Policy,
    client: Client,
    identities: Sequence[Mapping[str, object]],
    sources: Sequence[str | None],
    *,
    recollection: bool,
) -> Decision:
    """The decision that holds for a claim (decision 12 of the 2026-10-14
    assignments plan).

    A recollection has no source event and names nobody, so the policy
    decides over it as over a source `recollection` without identities: it
    is held back until the operator sets a rule `source:recollection`, the
    fail-safe way that exists already. With sources too, as in a thread of
    which one version is a recollection, every decision is taken, those of
    the sources and that of the recollection, and the first that chooses
    nothing holds, as in `assertion_verdict`.
    """
    decisions = [
        decision
        for _source, decision in claim_decisions(
            policy, client, identities, sources, recollection=recollection
        )
    ]
    return next((d for d in decisions if d.chosen is None), decisions[-1])


def relation_visible(
    policy: Policy,
    client: Client,
    relation: GraphVersion,
    ends: Mapping[int, bool],
    identities: Sequence[Mapping[str, object]],
    sources: Sequence[str | None],
) -> bool:
    """Whether a client sees a relation: its own sources let it through, by
    `claim_verdict`, and every entity it names is one the client sees, by
    `ends` (id of an entity to whether it is visible; an id it lacks is not).
    A question names its candidates as ends. A relation that starts at an
    event is no relation between entities, and phase 1 shows none."""
    body = relation.claim.body
    if not isinstance(body, RelationBody) or isinstance(body.start, Source):
        return False
    verdict = claim_verdict(
        policy,
        client,
        identities,
        sources,
        recollection=relation.claim.evidence == RECOLLECTION,
    )
    named = [body.start, *([body.to] if body.to is not None else body.candidates or ())]
    return verdict.chosen is not None and all(ends.get(end, False) for end in named)
