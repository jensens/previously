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
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash
from previously.core.hashing import payload_hash
from previously.core.hashing import units_hash
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence
    from previously.storage.postgres import PostgresStorage
    from previously.storage.rows import EventRow
    from previously.storage.rows import UnitRow


@dataclass(frozen=True)
class Finding:
    event_id: int
    reason: str


def _payload_finding(row: EventRow) -> Finding | None:
    """`payload_hash` against the stored payload, or `None`.

    Skipped on `payload IS NULL`: that is the tombstone, and `payload_hash`
    stays standing in that case ({ref}`tombstone-seam`).
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
    """`units_hash` against the stored units, or `None`.

    This is the check that correction K1 brought: without it, three permanent
    forgeries ran, as measured, silently through — the content of a unit
    rewritten, one of two units deleted, and both of them with the finding
    "chain intact".
    """
    try:
        computed = units_hash(units)
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


def _check_event(
    row: EventRow,
    units: Sequence[UnitRow],
    source_key: tuple[str, str] | None,
    *,
    previous_hash: bytes | None,
    first: bool,
) -> list[Finding]:
    """The findings of a single event, in the order they are checked.

    A function of its own, because `verify` would otherwise do two things at
    once: walk over batches and check an event. The batch loop needs the
    connection, the check only rows — and the smaller the check, the easier it
    is to read as a whole.
    """
    findings: list[Finding] = []

    if first:
        if row.prev_hash is not None:
            findings.append(Finding(row.id, "first event has prev_hash, expected NULL"))
    elif row.prev_hash != previous_hash:
        findings.append(Finding(row.id, "prev_hash does not match the predecessor"))

    for finding in (_payload_finding(row), _units_finding(row, units)):
        if finding is not None:
            findings.append(finding)

    # The hash comparison uses the **stored** digests `payload_hash` and
    # `units_hash`, not the ones just recomputed. That is exactly what keeps
    # the two statements apart: "the content was altered" (the digest does not
    # match the content) against "the row was altered" (the fields do not
    # match the hash). And only that way does the erasure seam stay open — an
    # erased content leaves its digest standing, and the event hash remains
    # valid.
    source, external_id = source_key if source_key is not None else (None, None)
    expected = event_hash(
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
        findings.append(Finding(row.id, "hash does not match the fields"))

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


def verify(storage: PostgresStorage, *, batch: int = 1000) -> list[Finding]:
    findings: list[Finding] = []
    previous_hash: bytes | None = None
    next_id = 1
    expect_first = True
    checked = 0

    # One transaction over the **whole** check (review finding G4 of the final
    # review): only that way do all the reads see the same snapshot. Read over
    # several transactions, the report would be a statement about several
    # points in time and none about the chain — a forgery could wander between
    # two reads and appear consistent in every snapshot taken on its own.
    with storage.begin() as conn:
        while True:
            rows = list(storage.read(conn, from_id=next_id, limit=batch))
            if not rows:
                # The count reconciliation belongs in the **same** transaction
                # as the check, or else it counts a different state than the
                # one checked and would report a count error on every
                # concurrent append.
                count_finding = _count_finding(checked, storage.count_events(conn))
                if count_finding is not None:
                    findings.append(count_finding)
                return findings

            # Source attributions **and** units of the whole batch, each in
            # one query. Asking per event would be two million queries with a
            # million events — and `verify` is the routine that runs over the
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
                findings.extend(
                    _check_event(
                        row,
                        units_of.get(row.id, []),
                        keys.get(row.id),
                        previous_hash=previous_hash,
                        first=expect_first,
                    )
                )
                expect_first = False
                previous_hash = row.hash
                next_id = row.id + 1
                checked += 1
