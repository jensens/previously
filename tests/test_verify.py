# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from previously.contract.types import Evidence, RawEvent
from previously.core.append import append
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage

NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)


def _event(external_id: str) -> RawEvent:
    return RawEvent(
        source="cli",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext(f"content {external_id}"),
        payload={"note": external_id},
    )


# The text out of the measured finding K1 (F1–F3). Two units, so that F2 can
# really delete *one of two*: with only one unit an empty set of units would
# be left over, and that is a different case from a unit withheld among
# others.
#
# The German original of this text is pinned in `tests/test_hashing.py` as the
# hash vector's input and stays German there. Here the hash is computed at
# runtime on both sides, so the wording is free.
_MESSAGE = "Price remains 1000 Euro.\n\nPlease confirm."


def _message(external_id: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=split_plaintext(_MESSAGE),
        payload={"text": _MESSAGE},
    )


@pytest.mark.db
def test_an_empty_chain_passes(db: Engine) -> None:
    assert verify(PostgresStorage(db)) == []


@pytest.mark.db
def test_an_intact_chain_passes(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    assert verify(storage) == []


@pytest.mark.db
def test_a_manipulated_payload_fires(db: Engine) -> None:
    """Exactly one finding: the self-hash check computes against the *stored*
    `payload_hash`, and that one stays unchanged, because only `payload` was
    manipulated. Event 2 links to the (unchanged) `hash` of event 1 and is
    therefore unaffected."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE event SET payload = CAST(:p AS jsonb) WHERE id = 1"),
            {"p": '{"note":"forged"}'},
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert "payload_hash" in findings[0].reason


@pytest.mark.db
def test_a_tombstone_passes(db: Engine) -> None:
    """Setting payload to NULL does not break the chain."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))
    assert verify(storage) == []


@pytest.mark.db
def test_a_broken_linkage_fires(db: Engine) -> None:
    """A manipulated `prev_hash` breaks two checks at once, not just one.

    `prev_hash` goes into the event hash itself (`core/hashing.py`, the key
    `"prev"` in the canonicalised object). The linkage check compares
    `row.prev_hash` against the hash of the predecessor and fires. The
    self-hash check recomputes `event_hash` with the (manipulated) `prev_hash`
    and compares against the stored `hash`, which was computed with the
    *original* `prev_hash` — and therefore fires independently as well. Both
    statements are true in their own right; suppressing the second one merely
    because the first had already fired would obscure the case in which both
    are wrong independently of each other (ruling T8-a).
    """
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET prev_hash = :p WHERE id = 2"), {"p": b"\xff" * 32})
    findings = verify(storage)
    assert [f.event_id for f in findings] == [2, 2]

    reasons = [f.reason for f in findings]
    linkage = [r for r in reasons if "prev_hash" in r]
    self_hash = [r for r in reasons if "prev_hash" not in r]
    assert len(linkage) == 1
    assert len(self_hash) == 1
    assert "hash" in self_hash[0]


@pytest.mark.db
def test_a_manipulated_event_hash_fires(db: Engine) -> None:
    """Exactly one finding: there is only this one event, hence no successor
    whose linkage the manipulation could break."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\xee" * 32})
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]


@pytest.mark.db
def test_a_first_event_with_a_prev_hash_fires(db: Engine) -> None:
    """Covers the fourth checking branch, which none of the six tests of the
    extract exercises: the first row read having `prev_hash` set instead of
    NULL. As in `test_a_broken_linkage_fires` (ruling T8-a), two independent
    findings arise here too, not one: the first-event check fires because
    `prev_hash` at `id=1` is not NULL, and the self-hash check fires in
    addition because `event_hash` covers this (now different) `prev_hash`,
    while the stored `hash` was still computed with the original `prev_hash`
    (NULL)."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET prev_hash = :p WHERE id = 1"), {"p": b"\xaa" * 32})
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1, 1]

    reasons = [f.reason for f in findings]
    assert any("first event" in r for r in reasons)
    assert any(r == "hash does not match the fields" for r in reasons)


@pytest.mark.db
def test_the_check_continues_across_a_batch_boundary(db: Engine) -> None:
    """Ruling T8-b: no test in the extract exercises a change of batch, and
    the batch loop is exactly the kind of code that runs silently wrong —
    missed rows or an endless loop, both without an error message. With
    `batch=1` every pass reads exactly one row; that proves that the loop
    advances across batch boundaries and does not lose `previous_hash` along
    the way — otherwise the linkage check would fire falsely on an actually
    intact chain."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    assert verify(storage, batch=1) == []


# ---------------------------------------------------------------------------
# Regression tests for K1: the chain covers units and source attribution.
#
# All four forgeries below ran **silently** against the version before K1 —
# `verify` reported `[]`, three times "chain intact" on a permanent forgery
# (findings F1–F3 of the final review). In an append-only store that is
# irretrievable: there is no correcting a row after the fact. Without these
# tests the gap can come back, and unnoticed at that.
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_k1_f1_a_rewritten_unit_content_fires(db: Engine) -> None:
    """F1: the content of a unit is rewritten.

    Exactly one finding, and that one over the units digest: the event hash
    carries the **stored** `units_hash`, and that one stays unchanged, because
    only `unit.content` was manipulated — the same distinction as with
    `payload`/`payload_hash`. "The content was altered" and "the row was
    altered" therewith stay two different statements.
    """
    storage = PostgresStorage(db)
    append(storage, [_message("message-1")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE unit SET content = :new WHERE event_id = 1 AND seq = 1"),
            {"new": "Price remains 100000 Euro."},
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "units_hash does not match the units"


@pytest.mark.db
def test_k1_f2_a_deleted_unit_fires(db: Engine) -> None:
    """F2: one of two units is deleted.

    This is the forgery that no content comparison finds: what is missing
    cannot be checked against itself. Only a digest over the **whole** set of
    units notices the missing unit.
    """
    storage = PostgresStorage(db)
    append(storage, [_message("message-1")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("DELETE FROM unit WHERE event_id = 1 AND seq = 1"))
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "units_hash does not match the units"


@pytest.mark.db
def test_k1_f3_a_rewritten_source_attribution_fires(db: Engine) -> None:
    """F3: the source attribution is forged.

    `source` and `external_id` go into the event hash but have no digest of
    their own in the row — which is why the finding here is the hash
    comparison, and that is the right statement: the fields of the event no
    longer match its hash.
    """
    storage = PostgresStorage(db)
    append(storage, [_message("message-1")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE source_key SET source = 'invented', external_id = 'x' WHERE event_id = 1")
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "hash does not match the fields"


@pytest.mark.db
def test_k1_a_deleted_source_attribution_fires(db: Engine) -> None:
    """Removing the source attribution entirely is no finding of its own but
    leads via the same hash comparison: `verify` reads `null`, but the values
    were hashed. A missing row and a rewritten row are both "the fields do not
    match the hash" — and the check need not distinguish more than that,
    because both have the same consequence."""
    storage = PostgresStorage(db)
    append(storage, [_message("message-1")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 1"))
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "hash does not match the fields"


# ---------------------------------------------------------------------------
# Finding W1 of the final review: one single poisoned row blinded the check of
# the **whole** chain, because `verify` broke off with `InvalidPayload`. That
# is the opposite of what an integrity check is supposed to deliver — whoever
# can forge one row could hide every further forgery behind it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        # A floating point number: the canonicalisation rejects it (§3.2),
        # because its rendering is language-dependent. jsonb preserves `1.5` as
        # a number with decimal places, psycopg returns it as a `float`.
        ("float", '{"note":1.5,"evidence":"recollection"}'),
        # An upper-case key: violates `^[a-z][a-z0-9_]*$`.
        ("uppercase", '{"Note":"b","evidence":"recollection"}'),
    ],
)
@pytest.mark.db
def test_w1_a_non_canonicalizable_payload_reports_and_does_not_break_off(
    db: Engine, name: str, payload: str
) -> None:
    """A chain of three events with the middle one poisoned: one finding for
    the middle one, no break-off, and event 3 is demonstrably still checked.

    The proof for "it carries on" is not the absence of an exception —
    `verify` could also stop silently after event 2. That is why event 3 is
    forged **in addition**: if its finding appears, the check really skipped
    the poisoned row and did not leave the chain.
    """
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE event SET payload = CAST(:p AS jsonb) WHERE id = 2"),
            {"p": payload},
        )
        c.execute(text("UPDATE event SET hash = :h WHERE id = 3"), {"h": b"\xee" * 32})

    findings = verify(storage)
    assert [f.event_id for f in findings] == [2, 3], f"{name}: {findings}"
    assert findings[0].reason.startswith("payload not canonicalizable: ")
    assert findings[1].reason == "hash does not match the fields"


@pytest.mark.db
def test_w1_a_poisoned_payload_does_not_blind_the_unit_check(db: Engine) -> None:
    """Two broken things in **one** row yield **two** findings.

    This is the test that holds down the separation of the two `try` blocks in
    `core/verify.py` (review finding B5 of fix round 1). The reasoning for it
    stood only in the comment before, and as measured all 124 tests stayed
    green when the blocks were put back together — an assurance without a test
    is no assurance.

    With a shared `try` around both recomputations, only one finding would
    come out here: the poisoned payload jumps out of the block, and the unit
    check never takes place. Then one forgery would obscure the other —
    precisely the blinding that finding W1 objects to, only one level smaller.
    Whoever can make a payload non-canonicalizable could otherwise rewrite the
    units of the same row at will.
    """
    storage = PostgresStorage(db)
    append(storage, [_message("message-1")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE event SET payload = CAST(:p AS jsonb) WHERE id = 1"),
            {"p": '{"Note":"poisoned"}'},
        )
        c.execute(
            text("UPDATE unit SET content = :new WHERE event_id = 1 AND seq = 1"),
            {"new": "Price remains 100000 Euro."},
        )

    findings = verify(storage)
    assert [f.event_id for f in findings] == [1, 1], findings
    assert findings[0].reason.startswith("payload not canonicalizable: ")
    assert findings[1].reason == "units_hash does not match the units"


# ---------------------------------------------------------------------------
# Finding B1 of fix round 1: `verify` began fixed at `id = 1` and `read`
# filters `id >= from_id` — a row with `id <= 0` was therefore **never
# checked**, but was displayed by `log --from=-5`. Measured:
#
#     row with id = 0 smuggled in
#         verify()        -> []        <- "chain intact"
#         read(from_id=1) -> [1]       <- that is what verify saw
#         read(from_id=-5)-> [0, 1]    <- that is what `log --from=-5` saw
#
# Since then `verify` counts the rows it checked and compares them against
# `count_events` in the same snapshot.
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_b1_a_row_smuggled_in_below_id_1_fires(db: Engine) -> None:
    """The row carries an **arbitrary, unused** `prev_hash`, not `NULL`: a
    genesis-like `id=0` row cannot be smuggled in at all, because
    `event_prev_hash_idx` with `NULLS NOT DISTINCT` permits exactly one entry
    with `prev_hash IS NULL`. With `NULL` this test would therefore have
    checked the index instead of `verify`."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(0, 'observation', now(), now(), :prev, :h, :p, :u, '{}'::jsonb)"
            ),
            {"prev": b"\x7f" * 32, "h": b"\x7e" * 32, "p": b"\x7d" * 32, "u": b"\x7c" * 32},
        )

    findings = verify(storage)
    assert len(findings) == 1, findings
    assert findings[0].event_id == 0
    assert findings[0].reason == "event has 2 rows, 1 checked — the rest is unreachable"


@pytest.mark.db
def test_b1_a_gapless_chain_reports_no_count_error(db: Engine) -> None:
    """The counter-test to the count reconciliation, across a batch boundary:
    with `batch=2` `verify` reads two batches plus an empty one. Were it to
    count rows twice or to lose a batch, it would report a count error here on
    a completely intact chain."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    assert verify(storage, batch=2) == []
