# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chain check ({ref}`hash-chain`).

Checking in `id` order is permissible because the `id` comes from the
predecessor and not out of a sequence: that makes `id` order equal to chain
order, by construction. Which is why the check stays a sequential scan instead
of a chain walk over millions of individual accesses.

Gaps are not checked separately: a missing row breaks the hash linkage anyway,
and checking the same thing twice would be redundant.

That the check has seen **all** the rows, by contrast, it does check
explicitly, via a count reconciliation against `count_events` (review finding
B1 of fix round 1): the sequential scan begins at `id = 1`, and whatever lies
below that lay outside its field of view before.

The check **reports and does not raise** (review finding W1 of the final
review). Before, it broke off with `InvalidPayload` as soon as a payload had
been manipulated into a floating point number or an upper-case key — one
single poisoned row thereby blinded the check of the **whole** chain. That is
the opposite of what an integrity check is supposed to deliver: whoever can
forge one row could have hidden every further forgery behind it.

With `blobs`, the check also holds the blob store against the rule of
{ref}`erasure`, after the snapshot (`_blob_findings`).
"""

from dataclasses import dataclass
from dataclasses import replace
from previously.contract.blobs import BlobStore
from previously.contract.blobs import KeyProvider
from previously.contract.types import Anchor
from previously.core.access import access_problem
from previously.core.action import APPROVAL_CLASS
from previously.core.action import KNOWN_ACTIONS
from previously.core.action import MCP_ACCESS
from previously.core.action import MODEL_CALL
from previously.core.action import OK
from previously.core.action import OUTCOMES
from previously.core.action import POLICY
from previously.core.action import REDACTION
from previously.core.action import VOCABULARY
from previously.core.assertion import assertion_problem
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import parse_statement
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertions import ASSERTION
from previously.core.assertions import stands_on_erased
from previously.core.blob import fetch_blob
from previously.core.canonical import canonical
from previously.core.chain import read_references
from previously.core.classes import class_problem
from previously.core.classes import ClassFold
from previously.core.errors import AddressMismatch
from previously.core.errors import CannotOpen
from previously.core.errors import InvalidPayload
from previously.core.graph import claim_problem
from previously.core.graph import conformance_problem
from previously.core.graph import GRAPH_KINDS
from previously.core.graph import GraphFold
from previously.core.graph import GraphVersion
from previously.core.graph import level_of
from previously.core.graph import parse_claim
from previously.core.graph import RelationBody
from previously.core.graph import rests_on
from previously.core.graph import STANDING
from previously.core.graph import TRANSITIVE
from previously.core.graph_write import closes_cycle
from previously.core.graph_write import EntityTypes
from previously.core.graph_write import names_a_candidate
from previously.core.graph_write import pending_question
from previously.core.graph_write import starts_thread
from previously.core.graph_write import takes_proposal
from previously.core.hashing import event_hash
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_1
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import payload_hash
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash
from previously.core.hashing import units_hash_v2
from previously.core.policy import check_payload
from previously.core.redaction import action_name
from previously.core.redaction import blob_expected
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
from previously.core.redaction import RedactionIndex
from previously.core.sealing import NullSink
from previously.core.vocabulary import vocabulary_problem
from previously.core.vocabulary import VocabularyFold
from typing import cast
from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.rows import EventRow
    from previously.contract.rows import UnitRow
    from previously.contract.store import LogStore
    from previously.core.assertion import Statement
    from previously.core.classes import Classes
    from previously.core.graph import Claim
    from previously.core.graph import Graph
    from previously.core.graph import GraphThread
    from previously.core.hashing import HashableUnit
    from previously.core.redaction import Redaction


@dataclass(frozen=True)
class Finding:
    event_id: int
    reason: str


@dataclass(frozen=True)
class BlobCheck:
    """What `examine` needs to check the blobs: the store, and the identities
    that open what lies in it ({ref}`blobs`)."""

    store: BlobStore
    keys: KeyProvider


@dataclass(frozen=True)
class Examination:
    """What one pass over the chain found, and where the chain ended.

    `tip` is the last row the pass saw, not the answer to a second query
    after it ({ref}`external-anchor`), whether or not the pass found
    something — it is where the log ends. `None` for an empty log.

    `blobs_checked` is the number of distinct blobs the register names, each
    held against the store; 0 without a `BlobCheck`.
    """

    findings: tuple[Finding, ...]
    tip: Anchor | None
    blobs_checked: int = 0

    @property
    def anchor(self) -> Anchor | None:
        """The anchor to take: the tip, but only when the pass found nothing.

        Taken on a chain with a finding, an anchor would vouch for the break:
        every later check against it would confirm the forged state as the
        one recorded outside. The rule lives here and not in the command
        line, so that a second entry point that hands out anchors gets it
        without copying it. `None` on a finding and on an empty log.
        """
        return None if self.findings else self.tip


def _payload_finding(row: EventRow) -> Finding | None:
    """`payload_hash` against the stored payload in version 1, or `None`.

    Skipped on `payload IS NULL`: that is the tombstone, and `payload_hash`
    stays standing in that case ({ref}`tombstone-seam`). Whether a redaction
    ordered the tombstone is not this row's question but the pass's, which
    answers it once it has read the redactions (`_Erasures`).
    """
    if row.payload is None:
        return None
    try:
        computed = payload_hash(row.payload)
    except InvalidPayload as error:
        return Finding(row.id, f"payload not canonicalizable: {error}")
    if computed != row.payload_hash:
        return Finding(row.id, "payload_hash does not match the payload")
    return None


def _units_finding(row: EventRow, units: Sequence[UnitRow]) -> Finding | None:
    """`units_hash` against the stored units in version 1, or `None`.

    This is the check that correction K1 brought: without it, three permanent
    forgeries ran, as measured, silently through — the content of a unit
    rewritten, one of two units deleted, and both of them with the finding
    "chain intact".

    Version 1 takes the texts of all units into one digest, so a unit
    without content leaves nothing to compute it from ({ref}`hash-version-2`),
    and the digest is not computed. What such an event is owed is decided at
    the end of the pass, by `_Erasures`: all of its units erased by a
    redaction is an erasure version 1 can carry, and some of them is not
    ({ref}`erasure`).
    """
    if any(unit.content is None for unit in units):
        return None
    try:
        # Every unit carries content, which the line above established and
        # the type of `UnitRow.content` cannot say: the cast states it.
        computed = units_hash(cast("Sequence[HashableUnit]", units))
    except InvalidPayload as error:  # pragma: no cover
        # Unreachable out of the database, hence without test coverage — but
        # not removable. `unit.content` is `text` and in a UTF-8 database can
        # carry neither a null byte nor a lone surrogate; `seq`, `start_ms`
        # and `end_ms` are `int4` and therewith inevitably inside the safe
        # range of numbers. That `units_hash` has anything to raise at all is
        # proven in
        # `tests/test_hashing.py::test_units_hash_rejects_non_canonicalizable_values`;
        # unreachable is only the way there through this table.
        #
        # The branch stays standing because the precondition hangs on the
        # column types and not on a decision of this module: a future column,
        # a different column type or a database with a different encoding must
        # not be able to blind the check of the **remaining** chain. That is
        # exactly what finding W1 was.
        return Finding(row.id, f"units not canonicalizable: {error}")
    if computed != row.units_hash:
        return Finding(row.id, "units_hash does not match the units")
    return None


def _payload_finding_v2(row: EventRow) -> Finding | None:
    """The version 2 payload digest against the stored payload, or `None`.

    Skipped on the tombstone, as in version 1. A payload without its salt has
    nothing to be computed with, which is the same statement as a digest that
    does not match: the stored digest does not attest this payload.

    The payload is canonicalized on its own first, so that the finding names
    the path from the payload, as it does in version 1, and not from the
    header the digest wraps it in — the reason `chain.prepare` gives.
    """
    if row.payload is None:
        return None
    if row.payload_salt is None:
        return Finding(row.id, "payload_hash does not match the payload")
    try:
        canonical(row.payload)
        computed = payload_hash_v2(row.payload, row.payload_salt)
    except InvalidPayload as error:
        return Finding(row.id, f"payload not canonicalizable: {error}")
    if computed != row.payload_hash:
        return Finding(row.id, "payload_hash does not match the payload")
    return None


def _unit_findings(row: EventRow, units: Sequence[UnitRow]) -> list[Finding]:
    """Every unit **with content** against its own version 2 digest.

    A unit without content is skipped: its digest stays standing for the units
    digest, as `payload_hash` does for a tombstoned payload. A unit that kept
    its content and lost its salt or its digest has nothing to be computed
    against, and that is its finding.
    """
    findings: list[Finding] = []
    for unit in units:
        if unit.content is None:
            continue
        mismatch = Finding(row.id, f"unit {unit.seq} does not match its digest")
        if unit.salt is None or unit.digest is None:
            findings.append(mismatch)
            continue
        try:
            computed = unit_digest(
                seq=unit.seq,
                content=unit.content,
                start_ms=unit.start_ms,
                end_ms=unit.end_ms,
                speaker=unit.speaker,
                salt=unit.salt,
            )
        except InvalidPayload as error:  # pragma: no cover
            # Unreachable out of the database for the reason the same branch
            # in `_units_finding` gives, and kept standing for the same reason.
            findings.append(Finding(row.id, f"unit {unit.seq} not canonicalizable: {error}"))
            continue
        if computed != unit.digest:
            findings.append(mismatch)
    return findings


def _units_finding_v2(row: EventRow, units: Sequence[UnitRow]) -> Finding | None:
    """The version 2 units digest over the **stored** unit digests, or `None`.

    Over the stored digests and not over recomputed ones, so that it holds for
    an erased unit — and so that a unit rewritten together with its digest
    still fails here: the unit agrees with itself, the set no longer agrees
    with the row. A unit without a digest leaves the set incomplete, which is
    this digest's finding and not a crash.
    """
    digests: dict[int, bytes] = {}
    for unit in units:
        if unit.digest is None:
            return Finding(row.id, "units_hash does not match the units")
        digests[unit.seq] = unit.digest
    if units_hash_v2(digests) != row.units_hash:
        return Finding(row.id, "units_hash does not match the units")
    return None


def _register_finding(row: EventRow, registered: Sequence[bytes]) -> Finding | None:
    """The blob register against the references in the payload, or `None`
    ({ref}`blobs`).

    The register carries no truth of its own: what the event hash covers is
    the payload, and the register is held against it as a set — the same
    content twice is two references and one row. A list without its form
    names no set, and that is the same finding. An event without a payload
    is held against its redaction instead, at the end of the pass
    (`_Erasures`), because the redaction stands behind it in the chain.
    """
    if row.payload is None:
        return None
    references = read_references(row.payload)
    named = None if references is None else {bytes.fromhex(r.sha256) for r in references}
    if named != set(registered):
        return Finding(row.id, "blob register does not match the payload")
    return None


class _EventHash(Protocol):
    """The signature `event_hash` and `event_hash_v2` share, spelled out so
    that pyright checks every keyword at the call below; `Callable[..., bytes]`
    would accept any arguments at all."""

    def __call__(
        self,
        *,
        event_id: int,
        kind: str,
        recorded_at: datetime,
        occurred_at: datetime,
        prev_hash: bytes | None,
        payload_digest: bytes,
        units_digest: bytes,
        source: str | None,
        external_id: str | None,
    ) -> bytes: ...


def _event_hash_finding(
    row: EventRow, source_key: tuple[str, str] | None, compute: _EventHash
) -> Finding | None:
    """The event hash over the row's fields, computed by `compute`.

    The comparison uses the **stored** digests `payload_hash` and
    `units_hash`, not the ones just recomputed. That is exactly what keeps the
    two statements apart: "the content was altered" (the digest does not match
    the content) against "the row was altered" (the fields do not match the
    hash). And only that way does the erasure seam stay open — an erased
    content leaves its digest standing, and the event hash remains valid.
    """
    source, external_id = source_key if source_key is not None else (None, None)
    expected = compute(
        event_id=row.id,
        kind=row.kind,
        recorded_at=row.recorded_at,
        occurred_at=row.occurred_at,
        prev_hash=row.prev_hash,
        payload_digest=row.payload_hash,
        units_digest=row.units_hash,
        source=source,
        external_id=external_id,
    )
    if expected != row.hash:
        return Finding(row.id, "hash does not match the fields")
    return None


def _check_version_1(
    row: EventRow, units: Sequence[UnitRow], source_key: tuple[str, str] | None
) -> list[Finding]:
    """Payload, units and event hash of a row written in version 1."""
    found = (
        _payload_finding(row),
        _units_finding(row, units),
        _event_hash_finding(row, source_key, event_hash),
    )
    return [finding for finding in found if finding is not None]


def _check_version_2(
    row: EventRow, units: Sequence[UnitRow], source_key: tuple[str, str] | None
) -> list[Finding]:
    """Payload, each unit, units and event hash of a row written in version 2.

    Each in a function of its own and every result collected, for the reason
    {ref}`hash-chain` gives: a forgery one recomputation trips over must not
    keep the next recomputation from running.
    """
    payload = _payload_finding_v2(row)
    findings = [] if payload is None else [payload]
    findings.extend(_unit_findings(row, units))
    found = (_units_finding_v2(row, units), _event_hash_finding(row, source_key, event_hash_v2))
    findings.extend(finding for finding in found if finding is not None)
    return findings


# The versions the check knows, and how it computes each. A row is computed in
# the version it names and in no other ({ref}`hash-version-2`): trying one
# version after another would let a forger pick whichever one adds up.
_CHECKS: Mapping[
    int, Callable[[EventRow, Sequence[UnitRow], tuple[str, str] | None], list[Finding]]
] = {
    HASH_VERSION_1: _check_version_1,
    HASH_VERSION_2: _check_version_2,
}


class _Erasures:
    """The tombstones and the redactions one pass has seen, and the findings
    that need both ({ref}`erasure`).

    A tombstone is matched against the redactions only once the pass has
    ended, still inside its snapshot: a redaction stands behind its target in
    the chain, so at the target's row it has not been read yet, and it may be
    batches away.

    What it keeps is small: the position of every tombstone, the register
    rows of every event whose payload is a tombstone, and the redactions,
    which are few. The form of every action is checked as it comes by,
    because that needs nothing but the row.
    """

    def __init__(self) -> None:
        self._redactions = RedactionIndex()
        self._payloads: list[int] = []
        self._units: list[tuple[int, int]] = []
        self._partial: list[int] = []
        self._registered: dict[int, frozenset[bytes]] = {}
        # The `model_call` events that still keep a result, with what they
        # read: (id, [(event, units, blobs)]). The ones whose units are all
        # gone keep nothing and are not remembered.
        self._calls: list[tuple[int, list[tuple[int, list[int], list[str]]]]] = []
        self._assertions = _Assertions()

    @property
    def redactions(self) -> RedactionIndex:
        """The redactions the pass has read so far, all of them once it has
        ended."""
        return self._redactions

    def observe(
        self, row: EventRow, units: Sequence[UnitRow], blobs: Sequence[bytes]
    ) -> list[Finding]:
        """Remembers the tombstones of one row and, for a payload tombstone,
        its register rows; reads the row if it is an action; the finding
        about the form of an action, if any."""
        if row.payload is None:
            self._payloads.append(row.id)
            self._registered[row.id] = frozenset(blobs)
        erased = [unit.seq for unit in units if unit.content is None]
        self._units.extend((row.id, seq) for seq in erased)
        # Some units of a version 1 event and not all: its digest takes the
        # texts of all of them, so the ones left standing are attested by
        # nothing, whoever ordered the erasure.
        if row.hash_version == HASH_VERSION_1 and 0 < len(erased) < len(units):
            self._partial.append(row.id)
        if row.kind == ASSERTION:
            return self._assertions.observe(row, units)
        if row.kind != "action" or row.payload is None:
            return []
        try:
            name = action_name(row.payload)
            if name == REDACTION:
                self._redactions.add(parse(row.id, row.payload))
        except MalformedAction:
            return [Finding(row.id, "action has no valid form")]
        # A name nobody here knows cannot be read, and so cannot be told from
        # a forgery. The form of the known names is checked where each is read.
        if name not in KNOWN_ACTIONS:
            return [Finding(row.id, f'unknown action "{name}"')]
        # Before the finding about the form: a vocabulary or class event with
        # units is a finding, and the read path takes it all the same, since
        # it reads the form alone; so the claims after it are held against
        # it here too (ruling T4-e of the 2026-10-14 assignments plan).
        self._assertions.claims.action(name, row.id, row.payload)
        if (finding := _form_finding(name, row.id, row.payload, units)) is not None:
            return [finding]
        if name == MODEL_CALL and any(unit.content is not None for unit in units):
            self._calls.append((row.id, _inputs_read(row.payload)))
        return []

    def reconcile[Conn](self, storage: LogStore[Conn], conn: Conn) -> list[Finding]:
        """The order against the execution: every tombstone needs a
        redaction, and every redaction needs its tombstones."""
        index = self._redactions
        findings = [
            Finding(event_id, "payload is erased without a redaction")
            for event_id in self._payloads
            if index.of_event(event_id) is None
        ]
        findings.extend(
            Finding(event_id, f"unit {seq} is erased without a redaction")
            for event_id, seq in self._units
            if index.of_unit(event_id, seq) is None
        )
        findings.extend(
            Finding(event_id, "units are erased in part, which version 1 cannot attest")
            for event_id in self._partial
        )
        findings.extend(self._register_findings())
        for redaction in index:
            findings.extend(_execution_findings(storage, conn, redaction))
        findings.extend(
            Finding(call_id, f"model_call {call_id} keeps the result of erased input")
            for call_id, read in self._calls
            if any(_erased(index, event, units, blobs) for event, units, blobs in read)
        )
        findings.extend(self._assertions.reconcile(storage, conn, index))
        return findings

    def _register_findings(self) -> list[Finding]:
        """The register of every erased event against the blobs its
        redaction names ({ref}`blobs`): once the payload is gone, that list
        is what attests them. A tombstone without a redaction has no list to
        be held against, and its finding is already that it has no order."""
        findings: list[Finding] = []
        for event_id, registered in self._registered.items():
            redaction = self._redactions.of_event(event_id)
            if redaction is None:
                continue
            if frozenset(bytes.fromhex(sha256) for sha256 in redaction.blobs) != registered:
                findings.append(Finding(event_id, "blob register does not match the payload"))
        return findings


@dataclass(frozen=True)
class _Joined:
    """A version of an obligation or a decision that stands in its thread:
    its kind, the name of its thread, its responsibility, and what an
    approval or a rejection of it has to take unchanged: its sources, and
    for an approval its content and its author too."""

    kind: str
    thread: int
    responsibility: str
    sources: tuple[Source, ...]
    body: ObligationBody | DecisionBody | None
    author: str


def _untaken(approval: Statement, proposal: _Joined) -> str | None:
    """What an approval of a standing proposal does not take unchanged.

    The fold counts it all the same. One with other content or another
    author would say that the operator made the proposal their own when
    they made something else theirs; one that left a source out would
    outlive the erasure of that source with the proposal's content. The
    reason may differ: it is the approver's.
    """
    if approval.body != proposal.body or approval.author != proposal.author:
        return "approval does not take the content and the author of its proposal"
    if approval.sources != proposal.sources:
        return "approval does not take the sources of its proposal"
    return None


class _Claims:
    """The entities and relations one pass has seen, held against what stood
    before each of them in the chain ({ref}`vocabulary-reference`).

    It folds them row by row as `core/graph.py` does, and beside them the
    vocabulary and the approval classes as the pass meets their events, so
    that an entity or a relation is held against the vocabulary and the
    classes in force where it stands, not against today's. A kind retired
    since, or a class revoked since, does not make a finding of what was
    written under it; a claim of a kind declared only after it does.

    What the fold passes over in silence is a finding here, as with an
    obligation, and so is what the write path would have refused or written
    otherwise: the operator's level, the objection against a direct winner,
    the class of a transitive version, the answer to a pending question, an
    approval of a proposal that a direct version overtook, and the cycle
    rule, which is the write path's own question, `closes_cycle`. The batch
    a claim was written in is not known here: the claims before it in the
    batch are rows before it, which the write path folds in the same way.
    Not held: that a model's open version would have been transitive under
    a class; an open version stands for nobody. Not held either, though the
    write path refuses them: what a vocabulary event names beyond its form
    (a kind that does not stand, the retirement of a kind another one needs,
    a built-in kind reshaped), and what an approval class names beyond its
    form (a type that does not stand, an acyclic type). The read path makes
    both harmless, and `docs/superpowers/landkarte.md` keeps the two checks
    as an open point.

    Its cost: each row asks a live view of the fold, which builds again only
    the threads the row before it changed, and a claim of an acyclic kind
    walks the edges that stood before it, so the pass grows faster than the
    number of such claims, at most with its square. Measured on 2026-10-14,
    one run each, after fix round 1 of Task 4 of the 2026-10-14 assignments
    plan: a chain of `part_of` edges between projects took `verify` 0.57 s
    at 1,000 edges and 1.77 s at 2,000, about three times as long for twice
    the edges; posts in one organization by `post_in`, no acyclic kind, took
    0.56 s at 2,000 relations and 2.67 s at 10,000. With the thread map
    copied once per row, as before that round, the 10,000 took 4.90 s. What
    a whole log costs at 10,000 relations and beyond, as the final review
    of the plan measured it, is on {ref}`graph-cost`.
    """

    def __init__(self) -> None:
        self._fold = GraphFold()
        self._vocabulary = VocabularyFold()
        self._classes = ClassFold()

    def action(self, name: str, event_id: int, payload: Mapping[str, object]) -> None:
        """Takes in an action of a known name: a vocabulary or class event
        of a sound form changes what holds for the claims after it, with
        units or without, as `read_vocabulary` and `read_classes` take it;
        any other changes nothing."""
        if name == VOCABULARY:
            self._vocabulary.add(event_id, payload)
        elif name == APPROVAL_CLASS:
            self._classes.add(event_id, payload)

    def fold(self, row: EventRow) -> None:
        """Takes in an assertion row after its findings: an erased one, a
        rejection, an entity or a relation."""
        self._fold.add(row.id, row.recorded_at, row.payload, self._classes.classes().states)

    def names(self, version_id: int) -> bool:
        """Whether `version_id` is a standing version of an entity or a
        relation."""
        return self._fold.subject_of(version_id) is not None

    def _found(self, version_id: int) -> tuple[Graph, GraphThread, GraphVersion]:
        graph = self._fold.current(self._classes.classes().states)
        thread = graph.threads[cast("int", self._fold.subject_of(version_id))]
        return graph, thread, next(v for v in thread.versions if v.id == version_id)

    def rejection_reason(self, statement: Statement) -> str | None:
        """What is wrong with a rejection of a version of an entity or a
        relation, which `names` knows: it has to be open or transitive, by
        `level_of` under the classes in force here, unanswered, and taken
        with its sources."""
        graph, thread, version = self._found(cast("int", statement.of))
        if level_of(version, graph.classes) == DIRECT:
            return "rejection names no open proposal"
        if version.id in thread.approved or version.id in thread.rejected:
            return "rejection of a proposal that is already approved or rejected"
        if statement.sources != version.claim.sources:
            return "rejection does not take the sources of its proposal"
        return None

    def _approval_reason(
        self, thread: GraphThread | None, claim: Claim, graph: Graph
    ) -> str | None:
        """What is wrong with an approval of a version that stands; one of an
        erased version is accepted, as with an obligation."""
        approves = cast("int", claim.approves)
        answered = thread is not None and (
            approves in thread.approved or approves in thread.rejected
        )
        if self._fold.erased(approves):
            return (
                "approval of a proposal that is already approved or rejected" if answered else None
            )
        versions = () if thread is None else thread.versions
        proposal = next((v for v in versions if v.id == approves), None)
        if proposal is None or level_of(proposal, graph.classes) == DIRECT:
            return "approval names no open proposal of its subject"
        if answered:
            return "approval of a proposal that is already approved or rejected"
        # The write path refuses it, and the fold would take it: a forged
        # approval of an old proposal becomes the newest direct version and
        # quietly replaces the one that won.
        newer = max((v.id for v in versions if v.claim.responsibility == DIRECT), default=0)
        if newer > approves:
            return f"approval of a proposal that the direct version {newer} overtook"
        if not takes_proposal(replace(claim, sources=proposal.claim.sources), proposal.claim):
            return "approval does not take the content and the author of its proposal"
        if claim.sources != proposal.claim.sources:
            return "approval does not take the sources of its proposal"
        return None

    def claim_reason(self, row: EventRow, claim: Claim) -> str | None:
        """The first thing wrong with what an entity or a relation names,
        with its level, or with the vocabulary, a question or the cycle
        rule, or `None`; then it joins the fold either way, as the fold reads
        it either way."""
        classes = self._classes.classes()
        graph = self._fold.current(classes.states)
        thread = None if claim.subject is None else graph.threads.get(claim.subject)
        reason = (
            self._claim_references(thread, claim, graph)
            or self._claim_level(thread, claim, graph, row, classes)
            or self._claim_rules(thread, claim, graph, row)
        )
        self.fold(row)
        return reason

    def _claim_references(
        self, thread: GraphThread | None, claim: Claim, graph: Graph
    ) -> str | None:
        """What `subject`, `approves` and `contests` name."""
        subject, contests = claim.subject, claim.contests
        if subject is not None and thread is None and not self._fold.erased(subject):
            return "assertion has a subject that names no earlier entity or relation"
        if thread is not None and thread.kind != claim.kind:
            return "assertion has a subject of another kind"
        if claim.approves is not None:
            return self._approval_reason(thread, claim, graph)
        if contests is not None and not self._fold.erased(contests):
            target = (
                next((v for v in thread.versions if v.id == contests), None) if thread else None
            )
            if target is None or target.claim.responsibility != DIRECT:
                return "objection contests no earlier direct version of its subject"
        return None

    def _claim_level(
        self,
        thread: GraphThread | None,
        claim: Claim,
        graph: Graph,
        row: EventRow,
        classes: Classes,
    ) -> str | None:
        """The level against the rules the write path sets it by: the
        operator's versions are direct, a model's version after a direct
        winner is an objection against it, and a transitive one stands
        under a class in force that covers it."""
        if claim.author == OPERATOR and claim.responsibility == OPEN:
            return "assertion is open but written by the operator"
        winner = None if thread is None else thread.winner(graph.classes)
        if (
            claim.author != OPERATOR
            and claim.approves is None
            and winner is not None
            and level_of(winner, graph.classes) == DIRECT
            and not (claim.responsibility == OPEN and claim.contests == winner.id)
        ):
            return "assertion by a model follows a direct version and does not object to it"
        if claim.responsibility == TRANSITIVE and not classes.covers(
            cast("int", claim.under),
            author=claim.author,
            kind=claim.kind,
            type_name=claim.body.type,
            confidence=claim.confidence,
            recorded_at=row.recorded_at,
            vocabulary=self._vocabulary.vocabulary(),
        ):
            return "assertion is transitive under no approval class in force for it"
        return None

    def _claim_rules(
        self, thread: GraphThread | None, claim: Claim, graph: Graph, row: EventRow
    ) -> str | None:
        """The vocabulary in force here, the answer to a pending question,
        and the cycle rule."""
        vocabulary = self._vocabulary.vocabulary()
        problem = conformance_problem(
            claim,
            vocabulary,
            new_thread=starts_thread(claim, thread),
            entity_types=EntityTypes(graph),
        )
        if problem is not None:
            return f"assertion does not fit the vocabulary of its time: {problem}"
        asked = pending_question(thread, graph.classes)
        standing = isinstance(claim.body, RelationBody) and claim.body.state == STANDING
        # The write path refuses a direct version that stands and names none
        # of the candidates, and writes a model's that a class would make
        # transitive as open instead.
        answers = (claim.responsibility == DIRECT and standing) or (
            claim.responsibility == TRANSITIVE
        )
        if asked is not None and answers and not names_a_candidate(claim, asked):
            return "relation answers a question with none of its candidates"
        level = level_of(GraphVersion(row.id, row.recorded_at, claim), graph.classes)
        if closes_cycle(graph, claim, vocabulary, level=level):
            return "relation closes a cycle over a kind that is acyclic"
        return None


class _Assertions:
    """The assertions one pass has seen, and the findings about them
    ({ref}`erasure`).

    It follows the fold of `core/assertion.py` row by row: a version joins
    its thread, an approval or a rejection marks its proposal. What the fold
    passes over in silence is a finding here, so that a version that came
    around the write path does not just disappear from every list.

    What it keeps is one small entry per assertion, and the sources of every
    assertion that stands, to be held against the erasures and the units of
    their events once the pass has ended.

    Its limit: an approval that names an erased assertion is accepted,
    whatever that assertion was. An approval of a proposal erased on its own
    stands, as the fold has it (ruling F-5 of the 2026-10-12 assertions
    plan), and the erasure took the payload that said whether the erased
    assertion was a proposal, of which thread, and with what content. So a
    hand-written approval that names an erased direct version, an erased
    rejection or an erased proposal of another thread is no finding, and
    neither is one whose content its erased proposal never held
    ({ref}`assertions-limits`).
    """

    def __init__(self) -> None:
        self._erased: set[int] = set()
        self._joined: dict[int, _Joined] = {}
        self._threads: dict[int, str] = {}  # name -> kind
        self._approved: set[int] = set()
        self._rejected: set[int] = set()
        self._standing: list[tuple[int, tuple[Source, ...]]] = []
        # Erased versions an approval named, with the subject it named them
        # under: one named under another subject was no thread.
        self._placed: dict[int, int] = {}
        self.claims = _Claims()

    def observe(self, row: EventRow, units: Sequence[UnitRow]) -> list[Finding]:
        """The finding about the form of an assertion or about what it names,
        if any; remembers the rest."""
        if row.payload is None:
            self._erased.add(row.id)
            self.claims.fold(row)
            return []
        # An entity or a relation is an assertion of a form of its own, which
        # `assertion_problem` would call none of obligation, decision and
        # rejection.
        if row.payload.get("assertion") in GRAPH_KINDS:
            return self._claim(row, units)
        problem = assertion_problem(row.payload)
        if problem is not None:
            return [Finding(row.id, f"assertion has no valid form: {problem}")]
        findings: list[Finding] = []
        # An assertion says in its payload what it says, and the payload is
        # what an erasure takes; units would stay behind.
        if units:
            findings.append(Finding(row.id, "assertion has units"))
        statement = cast("Statement", parse_statement(row.payload))
        if any(source.event >= row.id for source in statement.sources):
            findings.append(
                Finding(row.id, "assertion names a source that does not stand before it")
            )
        else:
            self._standing.append((row.id, statement.sources))
        # What it names is checked either way, as the fold reads it either way.
        reason = (
            self._rejection(statement)
            if statement.kind == REJECTION
            else self._version(row.id, statement)
        )
        if reason is not None:
            findings.append(Finding(row.id, reason))
        if statement.kind == REJECTION:
            self.claims.fold(row)
        return findings

    def _claim(self, row: EventRow, units: Sequence[UnitRow]) -> list[Finding]:
        """`observe` for an entity or a relation."""
        payload = cast("Mapping[str, object]", row.payload)
        problem = claim_problem(payload)
        if problem is not None:
            self.claims.fold(row)
            return [Finding(row.id, f"assertion has no valid form: {problem}")]
        findings: list[Finding] = []
        if units:
            findings.append(Finding(row.id, "assertion has units"))
        claim = cast("Claim", parse_claim(payload))
        if any(source.event >= row.id for source in claim.sources):
            findings.append(
                Finding(row.id, "assertion names a source that does not stand before it")
            )
        else:
            # The event a relation starts at with its own units, which a
            # source citing the whole event covers without naming them.
            self._standing.append((row.id, rests_on(claim)))
        reason = self.claims.claim_reason(row, claim)
        if reason is not None:
            findings.append(Finding(row.id, reason))
        return findings

    def _named(self, event_id: int) -> _Joined | None:
        return self._joined.get(event_id)

    def _open(self, proposal: _Joined | None) -> bool:
        return proposal is not None and proposal.responsibility == OPEN

    def _answered(self, proposal_id: int) -> bool:
        return proposal_id in self._approved or proposal_id in self._rejected

    def _rejection(self, statement: Statement) -> str | None:
        proposal_id = cast("int", statement.of)
        if proposal_id in self._erased:
            return None  # its kind is gone; the fold passes it over
        proposal = self._named(proposal_id)
        if proposal is None and self.claims.names(proposal_id):
            # A version of an entity or a relation, which the graph holds
            # with three levels (decision 5 of the 2026-10-14 assignments
            # plan).
            return self.claims.rejection_reason(statement)
        if proposal is None or not self._open(proposal):
            return "rejection names no open proposal"
        if self._answered(proposal_id):
            return "rejection of a proposal that is already approved or rejected"
        self._rejected.add(proposal_id)
        # The fold counts it all the same; what differs is that it would
        # outlive the erasure of a source it left out, with its reason.
        if statement.sources != proposal.sources:
            return "rejection does not take the sources of its proposal"
        return None

    def _no_thread(self, subject: int) -> bool:
        """Whether `subject` names nothing a version can join: no thread
        that stands, and no erased assertion that may have been one. An
        erased assertion keeps no `subject`, so it counts as a thread unless
        an approval named it under another subject."""
        if subject in self._threads:
            return False
        if subject not in self._erased:
            return True
        return self._placed.get(subject, subject) != subject

    def _version(self, event_id: int, statement: Statement) -> str | None:
        """The first thing wrong with what a version names, or `None`, and
        then it joins its thread."""
        subject = event_id if statement.subject is None else statement.subject
        kind = self._threads.get(subject)
        if statement.subject is not None:
            if self._no_thread(subject):
                return "assertion has a subject that names no earlier obligation or decision"
            if kind is not None and kind != statement.kind:
                return "assertion has a subject of another kind"
        replaces = statement.body.replaces if isinstance(statement.body, DecisionBody) else None
        if (
            replaces is not None
            and replaces not in self._erased
            and self._threads.get(replaces) != "decision"
        ):
            return "decision replaces no earlier decision"
        reason: str | None = None
        approves = statement.approves
        if approves is not None:
            if approves in self._erased:
                # An approval of a proposal erased on its own stands, and
                # nothing of the proposal is left to compare
                # ({ref}`assertions-approval`; ruling F-5 of the 2026-10-12
                # assertions plan).
                self._placed.setdefault(approves, subject)
            else:
                proposal = self._named(approves)
                if proposal is None or not self._open(proposal) or proposal.thread != subject:
                    return "approval names no open proposal of its subject"
                reason = _untaken(statement, proposal)
            if self._answered(approves):
                return "approval of a proposal that is already approved or rejected"
            self._approved.add(approves)
        self._threads.setdefault(subject, statement.kind)
        self._joined[event_id] = _Joined(
            statement.kind,
            subject,
            statement.responsibility,
            statement.sources,
            statement.body,
            statement.author,
        )
        return reason

    def reconcile[Conn](
        self, storage: LogStore[Conn], conn: Conn, index: RedactionIndex
    ) -> list[Finding]:
        """The sources against what the log holds: each an observation, each
        cited unit there, and nothing the assertion rests on erased while it
        stands.

        One read per distinct source event for its kind, and one for the
        units of all of them: the sources are read by `id`, as the targets of
        the redactions are, because keeping the kind of every row of the
        pass would cost memory in proportion to the log.
        """
        events = sorted({s.event for _, sources in self._standing for s in sources})
        kinds: dict[int, str] = {}
        for event_id in events:
            row = next(iter(storage.read(conn, from_id=event_id, limit=1)), None)
            if row is not None and row.id == event_id:
                kinds[event_id] = row.kind
        cited = sorted(
            {s.event for _, sources in self._standing for s in sources if s.units is not None}
        )
        held = storage.units_by_event(conn, cited)
        findings: list[Finding] = []
        for assertion_id, sources in self._standing:
            if any(kinds.get(source.event) != "observation" for source in sources):
                findings.append(
                    Finding(assertion_id, "assertion names a source that is not an observation")
                )
                continue
            seqs = {
                source.event: {unit.seq for unit in held.get(source.event, [])}
                for source in sources
            }
            if any(seq not in seqs[s.event] for s in sources for seq in s.units or ()):
                findings.append(
                    Finding(assertion_id, "assertion names a unit its source does not have")
                )
            if stands_on_erased(index, assertion_id, sources):
                findings.append(Finding(assertion_id, "assertion stands on an erased source"))
        return findings


def _statement_finding(
    label: str, event_id: int, problem: str | None, units: Sequence[UnitRow]
) -> Finding | None:
    """The finding about an action that is a statement of the operator, a
    policy event or a vocabulary event, or `None`.

    Such an event holds nothing a source said, so it has no units; one that
    has them did not come through its write path, and its units could hold
    anything."""
    if problem is not None:
        return Finding(event_id, f"{label} event {problem}")
    if units:
        return Finding(event_id, f"{label} event has units")
    return None


def _form_finding(
    name: str, event_id: int, payload: Mapping[str, object], units: Sequence[UnitRow]
) -> Finding | None:
    """The finding about the form of an action of a known name, or
    `None`."""
    if name == POLICY:
        return _statement_finding("policy", event_id, check_payload(payload), units)
    if name == VOCABULARY:
        return _statement_finding("vocabulary", event_id, vocabulary_problem(payload), units)
    if name == APPROVAL_CLASS:
        return _statement_finding("approval_class", event_id, class_problem(payload), units)
    if name == MODEL_CALL and (problem := _model_call_problem(payload, units)) is not None:
        return Finding(event_id, f"model_call has no valid form: {problem}")
    if name == MCP_ACCESS:
        # An access holds ids and names and no content, so it has no units; one
        # that has them did not come through `record_access`.
        if (problem := access_problem(payload)) is not None:
            return Finding(event_id, f"mcp_access has no valid form: {problem}")
        if units:
            return Finding(event_id, "mcp_access has units")
    return None


def _inputs_read(payload: Mapping[str, object]) -> list[tuple[int, list[int], list[str]]]:
    """What a well-formed `model_call` read: per entry of `inputs`, the event,
    its units and its blobs. An entry or a list of another shape is left out;
    `_model_call_problem` reports the call whose event is missing, and a
    `units` or `blobs` that is no list names nothing that could be erased."""
    read: list[tuple[int, list[int], list[str]]] = []
    for entry in cast("list[object]", payload.get("inputs")):
        named = cast("Mapping[str, object]", entry)
        units = named.get("units")
        blobs = named.get("blobs")
        read.append(
            (
                cast("int", named["event"]),
                [u for u in cast("list[object]", units) if isinstance(u, int)]
                if isinstance(units, list)
                else [],
                [b for b in cast("list[object]", blobs) if isinstance(b, str)]
                if isinstance(blobs, list)
                else [],
            )
        )
    return read


def _erased(index: RedactionIndex, event: int, units: Sequence[int], blobs: Sequence[str]) -> bool:
    """Whether a redaction covers the event, one of the units or one of the
    blobs that a call read."""
    return (
        index.of_event(event) is not None
        or any(index.of_unit(event, seq) is not None for seq in units)
        or any(index.of_reference(event, sha256) is not None for sha256 in blobs)
    )


def _model_call_problem(payload: Mapping[str, object], units: Sequence[UnitRow]) -> str | None:
    """What is wrong with the form of a `model_call`, or `None`.

    Units exactly at `ok`: the answer goes into the units, and only a call
    that got a valid answer has one. A unit erased by a cascade is still a
    row, so an erased answer keeps its call sound. `inputs` is what an
    erasure of a source follows to the calls that read it, so an entry
    without an event would be a call no erasure can reach.
    """
    outcome = payload.get("outcome")
    if not isinstance(outcome, str):
        return "it has no outcome"
    if outcome not in OUTCOMES:
        return f'it has the unknown outcome "{outcome}"'
    if outcome == OK and not units:
        return "it is ok and has no units"
    if outcome != OK and units:
        return f"it is {outcome} and has units"
    inputs = payload.get("inputs")
    if not isinstance(inputs, list):
        return 'it has no list "inputs"'
    for entry in cast("list[object]", inputs):
        event = (
            cast("Mapping[str, object]", entry).get("event") if isinstance(entry, dict) else None
        )
        if not isinstance(event, int) or isinstance(event, bool):
            return 'it has an "inputs" entry without an event'
    return None


def _execution_findings[Conn](
    storage: LogStore[Conn], conn: Conn, redaction: Redaction
) -> list[Finding]:
    """Whether the target of one redaction stands before it in the chain,
    has what it names, and no longer carries what it erased.

    The target is **read**, by `id`, and not inferred from the tombstones the
    pass counted: a tombstone says only that something is missing, and a
    redaction whose unit still carries its text has to be told apart from one
    whose unit does not. One read per redaction, because redactions are few.
    """
    missing = [Finding(redaction.id, "redaction names a target that does not exist")]
    if redaction.event is None:
        # A redaction of a blob, the one scope without an event of its own
        # (`redaction.parse`), which the cast states. It erased nothing in
        # the log: every event it names has to stand before it and use the
        # blob. What it erased in the store is checked with the blobs.
        blob = cast("str", redaction.blob)
        users = set(storage.events_by_blob(conn, bytes.fromhex(blob)))
        if all(event_id < redaction.id and event_id in users for event_id in redaction.events):
            return []
        return missing
    target = redaction.event
    row = next(iter(storage.read(conn, from_id=target, limit=1)), None)
    if target >= redaction.id or row is None or row.id != target:
        return missing
    units = {unit.seq: unit for unit in storage.units_by_event(conn, [target]).get(target, [])}
    if redaction.scope == "event":
        if row.payload is None and all(unit.content is None for unit in units.values()):
            return []
        return [Finding(redaction.id, f"redaction of event {target} is not carried out")]
    if any(seq not in units for seq in redaction.units):
        return missing
    return [
        Finding(redaction.id, f"redaction of unit {seq} of event {target} is not carried out")
        for seq in redaction.units
        if units[seq].content is not None
    ]


def _check_event(
    row: EventRow,
    units: Sequence[UnitRow],
    source_key: tuple[str, str] | None,
    blobs: Sequence[bytes],
    *,
    previous_hash: bytes | None,
    first: bool,
) -> list[Finding]:
    """The findings of a single event, in the order they are checked.

    A function of its own, because `examine` would otherwise do two things at
    once: walk over batches and check an event. The batch loop needs the
    connection, the check only rows — and the smaller the check, the easier it
    is to read as a whole.

    The linkage is checked for every row, whatever its version: `prev_hash`
    against the predecessor's `hash` needs no hash format. A version the check
    does not know is a finding, nothing else is computed for that row, and the
    pass goes on with the next one. The blob register needs no hash format
    either, and is held against the payload whatever the version.
    """
    findings: list[Finding] = []

    if first:
        if row.prev_hash is not None:
            findings.append(Finding(row.id, "first event has prev_hash, expected NULL"))
    elif row.prev_hash != previous_hash:
        findings.append(Finding(row.id, "prev_hash does not match the predecessor"))

    check = _CHECKS.get(row.hash_version)
    if check is None:
        findings.append(Finding(row.id, f"hash_version {row.hash_version} is not known"))
    else:
        findings.extend(check(row, units, source_key))
    register = _register_finding(row, blobs)
    if register is not None:
        findings.append(register)
    return findings


def _count_finding(checked: int, total: int) -> Finding | None:
    """The count reconciliation: has the check seen **all** the rows?

    Needed because the check does not survey its own reading window (finding
    B1 of fix round 1): it begins at `id = 1` and `read` filters
    `id >= from_id`, so a smuggled-in row with `id <= 0` lay outside —
    measured `verify() -> []`, while `log --from=-5` displayed it. Displayed,
    but never checked.

    Reconciled against the total, **not** by pulling `from_id` down to a very
    small value. A smaller `from_id` catches only the one construction we know
    of today; the count reconciliation covers every unreachable row — one that
    a future change introduces included, and one that nobody thought of while
    writing this code included. That is the difference between a sticking
    plaster and a statement.

    The `event_id` of the finding is **0**. There is no single row it could
    point at: it says something about the chain as a whole. 0 is the most
    comprehensible value for that, because 0 is no valid chain position — `id`
    begins at 1 and counts upwards from the predecessor
    ({ref}`hash-chain`), so a 0 can never be an ordinary finding. That
    `id = 0` is precisely the most obvious place to smuggle something in does
    not get in the way here but fits: the text of the finding names numbers,
    no row, and is distinguishable from every row-related finding.
    """
    if checked == total:
        return None
    return Finding(0, f"event has {total} rows, {checked} checked — the rest is unreachable")


def examine[Conn](
    storage: LogStore[Conn],
    *,
    anchors: Sequence[Anchor] = (),
    exact: bool = False,
    batch: int = 1000,
    blobs: BlobCheck | None = None,
    before_blobs: Callable[[Sequence[Finding]], None] | None = None,
) -> Examination:
    """The one pass: the chain, and the anchors against it.

    Without anchors this is the chain check and nothing else. With anchors it
    also checks that each anchored event exists and carries the anchored hash
    — "contains" — and with `exact` that the tip is the newest anchor
    ({ref}`external-anchor`). The anchors are checked as the pass comes by
    them; there is no second read.

    With `blobs`, it also holds every blob the register names against the
    store, after the snapshot; `_blob_findings` says how. Without it, no
    blob is touched.

    `before_blobs` is handed the findings of the chain and the anchors once
    the pass is done and before any blob is checked, with or without
    `blobs`. The check of the blobs can end in an error rather than a
    finding — a store that does not answer — and the error leaves this
    function without an `Examination`; a caller that reports the findings
    there has reported them before the error can take them along. They
    stand at the head of `Examination.findings` as well.

    Returns structured results and no sentences: the command line formats
    them today, and a second entry point formats them its own way.
    """
    if exact and not anchors:
        raise InvalidPayload("exact needs at least one anchor to compare the tip with")
    findings: list[Finding] = []
    erasures = _Erasures()
    previous_hash: bytes | None = None
    next_id = 1
    expect_first = True
    checked = 0
    tip: Anchor | None = None
    # Anchors still waiting for their event, by `id`. A set of hashes per
    # `id`: two lines that disagree about one position are each checked, and
    # the same line repeated is checked once — the routine appends the same
    # line again whenever no event arrived, and one rewritten event would
    # otherwise be reported once per copy.
    pending: dict[int, set[bytes]] = {}
    for anchor in anchors:
        pending.setdefault(anchor.id, set()).add(anchor.hash)

    # One snapshot over the **whole** check (review finding G4 of the final
    # review): read over several points in time, the report would be a
    # statement about several states and none about the chain — a forgery
    # could wander between two reads and appear consistent in every one taken
    # on its own. One transaction is not enough for that: under the READ
    # COMMITTED of `begin`, every statement sees a state of its own, which is
    # why this is `snapshot` ({ref}`hash-chain`).
    with storage.snapshot() as conn:
        while True:
            rows = list(storage.read(conn, from_id=next_id, limit=batch))
            if not rows:
                # The count reconciliation belongs in the **same** snapshot as
                # the check, or else it counts a different state than the one
                # checked and reports a count error whenever an append commits
                # between the last read and the count.
                count_finding = _count_finding(checked, storage.count_events(conn))
                if count_finding is not None:
                    findings.append(count_finding)
                # In the same snapshot for the same reason: the targets read
                # here have to be the rows the pass checked.
                findings.extend(erasures.reconcile(storage, conn))
                # And the references of every blob, so that the rule is
                # applied to the register the pass checked.
                references = _references(storage, conn, blobs)
                break

            # Source attributions **and** units of the whole batch, each in
            # one query. Asking per event would be two million queries with a
            # million events — and `examine` is the routine that runs over the
            # whole history. Until finding N2 the source attributions were
            # fetched by batch with exactly this reasoning while the units
            # were fetched per event six lines further down, which made the
            # comment and the code contradict each other.
            #
            # A missing row is no finding of its own, in either case: it leads
            # via the hash comparison to "hash does not match the fields" or
            # to "units_hash does not match the units", and that is the right
            # statement. Which is why `.get` with an empty default stands here
            # and no check for presence.
            event_ids = [r.id for r in rows]
            keys = storage.source_keys(conn, event_ids)
            units_of = storage.units_by_event(conn, event_ids)
            # The blob register by batch as well, for the same reason.
            blobs_of = storage.blobs_by_event(conn, event_ids)

            for row in rows:
                units = units_of.get(row.id, [])
                registered = blobs_of.get(row.id, [])
                findings.extend(
                    _check_event(
                        row,
                        units,
                        keys.get(row.id),
                        registered,
                        previous_hash=previous_hash,
                        first=expect_first,
                    )
                )
                findings.extend(erasures.observe(row, units, registered))
                for anchored in pending.pop(row.id, ()):
                    if anchored != row.hash:
                        findings.append(Finding(row.id, "hash does not match the anchor"))
                expect_first = False
                previous_hash = row.hash
                next_id = row.id + 1
                checked += 1
                tip = Anchor(row.id, row.hash)

    findings.extend(_closing_findings(pending, anchors, tip, exact=exact))
    if before_blobs is not None:
        before_blobs(tuple(findings))
    blob_findings = _blob_findings(references, erasures.redactions, blobs)
    findings.extend(blob_findings)
    return Examination(tuple(findings), tip, blobs_checked=len(references))


def _references[Conn](
    storage: LogStore[Conn], conn: Conn, blobs: BlobCheck | None
) -> dict[str, list[int]]:
    """Every row of the register, as the events that name each blob,
    ascending — or nothing at all without a `BlobCheck`.

    All of it is held in the memory of the process until the blobs are
    checked, one address and its event ids per blob: that is the limit of
    `verify --blobs`, and a register of millions of rows costs that much
    memory. The alternative was to check each blob while the cursor still
    stands, inside the snapshot, which would hold a transaction open for as
    long as reading every byte in the store takes.
    """
    if blobs is None:
        return {}
    grouped: dict[str, list[int]] = {}
    for sha256, event_id in storage.blob_references(conn):
        grouped.setdefault(sha256.hex(), []).append(event_id)
    return grouped


def _blob_findings(
    references: Mapping[str, Sequence[int]], index: RedactionIndex, blobs: BlobCheck | None
) -> list[Finding]:
    """Every blob the register names, held against the store by the rule of
    {ref}`erasure`, each finding under the smallest `id` that names the blob.

    Run after the snapshot and not in it: reading every byte in the store
    takes as long as the store is large, and a transaction held open for
    that long holds back the database's cleanup. So the store is seen later
    than the log, and that can show either way. A blob erased and deleted
    since the snapshot is reported as missing. A blob whose redaction the
    snapshot holds can be reported as erased and still present, while a
    concurrent `redact` has not deleted it yet, or because the same content
    was attached again after the snapshot. The next run reports none of
    them.

    Only the blobs the register names are checked: an object in the store
    that no event names is reported by nothing.

    A blob that has to lie is fetched whole into a `NullSink`, through the
    check of its address: one that is not there is missing, one that opens
    to another content does not match its address, and one that names no
    key, whose key has no identity at hand, or that `age` refuses cannot be
    opened. A blob that does not have to lie is only asked for, and if it is
    there, it is erased and still present.

    Where the line runs: a finding says something about the log and its
    blobs. What says that the check could not be made is raised and ends
    the check — a store that does not answer or refuses (`storage.errors`),
    an identity file that exists and cannot be read (`IdentityUnreadable`),
    an identity that is not one (`InvalidKey`), a stream that breaks off.
    Turned into findings, they would report blobs as broken that nobody
    looked at.
    """
    if blobs is None:
        return []
    findings: list[Finding] = []
    for sha256, event_ids in references.items():
        reason = _blob_reason(blobs, sha256, expected=blob_expected(index, sha256, event_ids))
        if reason is not None:
            findings.append(Finding(min(event_ids), f"blob {sha256} {reason}"))
    return findings


def _blob_reason(blobs: BlobCheck, sha256: str, *, expected: bool) -> str | None:
    """What is wrong with one blob in the store, or `None`."""
    if not expected:
        return None if blobs.store.stat(sha256) is None else "is erased and still present"
    try:
        size = fetch_blob(blobs.store, blobs.keys, sha256, NullSink())
    except AddressMismatch:
        return "does not match its address"
    except CannotOpen:
        return "cannot be opened"
    return "is missing" if size is None else None


def _closing_findings(
    pending: Mapping[int, Collection[bytes]],
    anchors: Sequence[Anchor],
    tip: Anchor | None,
    *,
    exact: bool,
) -> list[Finding]:
    """The anchor findings that can only be stated once the pass has ended.

    A function of its own for the reason `_check_event` is one: `examine`
    walks the batches, and what is left to say after the walk does not need
    the connection.
    """
    findings: list[Finding] = []
    tip_id = 0 if tip is None else tip.id
    # What is still pending never came by: the log ends before it, or the row
    # is gone from the middle — and then the chain itself has a finding too.
    findings.extend(
        Finding(anchor_id, f"anchored event is missing (the log ends at {tip_id})")
        for anchor_id in sorted(pending)
    )
    if exact:
        newest = max(anchor.id for anchor in anchors)
        if tip_id > newest:
            findings.append(Finding(tip_id, f"the log continues past the newest anchor ({newest})"))
    return findings


def verify[Conn](storage: LogStore[Conn], *, batch: int = 1000) -> list[Finding]:
    """The chain alone, as a list — what every caller asked for before there
    were anchors. `examine` is the pass; this is its findings without any."""
    return list(examine(storage, batch=batch).findings)
