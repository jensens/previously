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
"""

from dataclasses import dataclass
from previously.contract.types import Anchor
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash
from previously.core.hashing import event_hash_v2
from previously.core.hashing import HASH_VERSION_1
from previously.core.hashing import HASH_VERSION_2
from previously.core.hashing import payload_hash
from previously.core.hashing import payload_hash_v2
from previously.core.hashing import unit_digest
from previously.core.hashing import units_hash
from previously.core.hashing import units_hash_v2
from previously.core.redaction import action_name
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
from previously.core.redaction import REDACTION
from previously.core.redaction import RedactionIndex
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
    from previously.core.hashing import HashableUnit
    from previously.core.redaction import Redaction


@dataclass(frozen=True)
class Finding:
    event_id: int
    reason: str


@dataclass(frozen=True)
class Examination:
    """What one pass over the chain found, and where the chain ended.

    `tip` is the last row the pass saw, not the answer to a second query
    after it ({ref}`external-anchor`), whether or not the pass found
    something — it is where the log ends. `None` for an empty log.
    """

    findings: tuple[Finding, ...]
    tip: Anchor | None

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

    What it keeps is small: the position of every tombstone, and the
    redactions, which are few. The form of every action is checked as it
    comes by, because that needs nothing but the row.
    """

    def __init__(self) -> None:
        self._redactions = RedactionIndex()
        self._payloads: list[int] = []
        self._units: list[tuple[int, int]] = []
        self._partial: list[int] = []

    def observe(self, row: EventRow, units: Sequence[UnitRow]) -> list[Finding]:
        """Remembers the tombstones of one row, and reads it if it is an
        action; the finding about the form of an action, if any."""
        if row.payload is None:
            self._payloads.append(row.id)
        erased = [unit.seq for unit in units if unit.content is None]
        self._units.extend((row.id, seq) for seq in erased)
        # Some units of a version 1 event and not all: its digest takes the
        # texts of all of them, so the ones left standing are attested by
        # nothing, whoever ordered the erasure.
        if row.hash_version == HASH_VERSION_1 and 0 < len(erased) < len(units):
            self._partial.append(row.id)
        if row.kind != "action" or row.payload is None:
            return []
        try:
            if action_name(row.payload) == REDACTION:
                self._redactions.add(parse(row.id, row.payload))
        except MalformedAction:
            return [Finding(row.id, "action has no valid form")]
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
        for redaction in index:
            findings.extend(_execution_findings(storage, conn, redaction))
        return findings


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
    if redaction.event is None:
        # A redaction of a blob names no event to read here; what it erased
        # lies in the blob store, and its check comes with the blobs.
        return []
    target = redaction.event
    missing = [Finding(redaction.id, "redaction names a target that does not exist")]
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
    pass goes on with the next one.
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
) -> Examination:
    """The one pass: the chain, and the anchors against it.

    Without anchors this is the chain check and nothing else. With anchors it
    also checks that each anchored event exists and carries the anchored hash
    — "contains" — and with `exact` that the tip is the newest anchor
    ({ref}`external-anchor`). The anchors are checked as the pass comes by
    them; there is no second read.

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

            for row in rows:
                units = units_of.get(row.id, [])
                findings.extend(
                    _check_event(
                        row,
                        units,
                        keys.get(row.id),
                        previous_hash=previous_hash,
                        first=expect_first,
                    )
                )
                findings.extend(erasures.observe(row, units))
                for anchored in pending.pop(row.id, ()):
                    if anchored != row.hash:
                        findings.append(Finding(row.id, "hash does not match the anchor"))
                expect_first = False
                previous_hash = row.hash
                next_id = row.id + 1
                checked += 1
                tip = Anchor(row.id, row.hash)

    findings.extend(_closing_findings(pending, anchors, tip, exact=exact))
    return Examination(tuple(findings), tip)


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
