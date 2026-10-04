# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from datetime import UTC
from previously.contract.types import Anchor
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.errors import InvalidPayload
from previously.core.hashing import unit_digest
from previously.core.units import split_plaintext
from previously.core.verify import Examination
from previously.core.verify import examine
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence


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


# The `write_version_1` fixture from `conftest.py`, under a `type` alias for
# the reason its docstring gives.
type WriteVersion1 = Callable[[PostgresStorage, Sequence[RawEvent], datetime], list[int]]

# The forgery tests whose finding is the same in both hash formats run once
# per format: version 1 written by hand, as every event before stage 1c was,
# and version 2 through `append`. Version 1 stays verifiable for good
# ({ref}`hash-version-2`), and without its half every forgery test here would
# exercise version 2 alone.
WRITTEN_IN = pytest.mark.parametrize("version", [1, 2], ids=["version-1", "version-2"])


def _write(
    version: int,
    storage: PostgresStorage,
    events: list[RawEvent],
    write_version_1: WriteVersion1,
) -> None:
    if version == 1:
        write_version_1(storage, events, NOW)
    else:
        append(storage, events, recorded_at=NOW)


@pytest.mark.db
def test_an_empty_chain_passes(db: Engine) -> None:
    assert verify(PostgresStorage(db)) == []


@pytest.mark.db
def test_an_intact_chain_passes(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    assert verify(storage) == []


@WRITTEN_IN
@pytest.mark.db
def test_a_manipulated_payload_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """Exactly one finding: the self-hash check computes against the *stored*
    `payload_hash`, and that one stays unchanged, because only `payload` was
    manipulated. Event 2 links to the (unchanged) `hash` of event 1 and is
    therefore unaffected."""
    storage = PostgresStorage(db)
    _write(version, storage, [_event("a"), _event("b")], write_version_1)
    with db.begin() as c:
        c.execute(
            text("UPDATE event SET payload = CAST(:p AS jsonb) WHERE id = 1"),
            {"p": '{"note":"forged"}'},
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert "payload_hash" in findings[0].reason


@WRITTEN_IN
@pytest.mark.db
def test_a_tombstone_passes(db: Engine, write_version_1: WriteVersion1, version: int) -> None:
    """Setting payload to NULL does not break the chain."""
    storage = PostgresStorage(db)
    _write(version, storage, [_event("a"), _event("b")], write_version_1)
    with db.begin() as c:
        # The salt goes with the payload, or `event_payload_salt_check`
        # refuses the statement (ruling P-1 of the 2026-10-04 stage 1c plan).
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"))
    assert verify(storage) == []


@WRITTEN_IN
@pytest.mark.db
def test_a_broken_linkage_fires(db: Engine, write_version_1: WriteVersion1, version: int) -> None:
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
    _write(version, storage, [_event("a"), _event("b")], write_version_1)
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


@WRITTEN_IN
@pytest.mark.db
def test_a_manipulated_event_hash_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """Exactly one finding: there is only this one event, hence no successor
    whose linkage the manipulation could break."""
    storage = PostgresStorage(db)
    _write(version, storage, [_event("a")], write_version_1)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\xee" * 32})
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]


@WRITTEN_IN
@pytest.mark.db
def test_a_first_event_with_a_prev_hash_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """Covers the fourth checking branch, which none of the six tests of the
    extract exercises: the first row read having `prev_hash` set instead of
    NULL. As in `test_a_broken_linkage_fires` (ruling T8-a), two independent
    findings arise here too, not one: the first-event check fires because
    `prev_hash` at `id=1` is not NULL, and the self-hash check fires in
    addition because `event_hash` covers this (now different) `prev_hash`,
    while the stored `hash` was still computed with the original `prev_hash`
    (NULL)."""
    storage = PostgresStorage(db)
    _write(version, storage, [_event("a"), _event("b")], write_version_1)
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

    Exactly one finding, and that one over the unit's own digest: `append`
    writes version 2, where every unit has one ({ref}`hash-version-2`). The
    units digest is taken over the **stored** unit digests, and those stay
    unchanged, as does the event hash over the stored units digest — the same
    distinction as with `payload`/`payload_hash`. "The content was altered"
    and "the row was altered" therewith stay two different statements.
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
    assert findings[0].reason == "unit 1 does not match its digest"


@pytest.mark.db
def test_k1_f1_a_rewritten_unit_content_fires_in_version_1(
    db: Engine, write_version_1: WriteVersion1
) -> None:
    """F1 on a version 1 event, which K1 was measured on and which stays
    verifiable for good: version 1 has no digest per unit, so the finding is
    the one over the units digest."""
    storage = PostgresStorage(db)
    write_version_1(storage, [_message("message-1")], NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE unit SET content = :new WHERE event_id = 1 AND seq = 1"),
            {"new": "Price remains 100000 Euro."},
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "units_hash does not match the units"


@WRITTEN_IN
@pytest.mark.db
def test_k1_f2_a_deleted_unit_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """F2: one of two units is deleted.

    This is the forgery that no content comparison finds: what is missing
    cannot be checked against itself. Only a digest over the **whole** set of
    units notices the missing unit.
    """
    storage = PostgresStorage(db)
    _write(version, storage, [_message("message-1")], write_version_1)
    with db.begin() as c:
        c.execute(text("DELETE FROM unit WHERE event_id = 1 AND seq = 1"))
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "units_hash does not match the units"


@WRITTEN_IN
@pytest.mark.db
def test_k1_f3_a_rewritten_source_attribution_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """F3: the source attribution is forged.

    `source` and `external_id` go into the event hash but have no digest of
    their own in the row — which is why the finding here is the hash
    comparison, and that is the right statement: the fields of the event no
    longer match its hash.
    """
    storage = PostgresStorage(db)
    _write(version, storage, [_message("message-1")], write_version_1)
    with db.begin() as c:
        c.execute(
            text("UPDATE source_key SET source = 'invented', external_id = 'x' WHERE event_id = 1")
        )
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "hash does not match the fields"


@WRITTEN_IN
@pytest.mark.db
def test_k1_a_deleted_source_attribution_fires(
    db: Engine, write_version_1: WriteVersion1, version: int
) -> None:
    """Removing the source attribution entirely is no finding of its own but
    leads via the same hash comparison: `verify` reads `null`, but the values
    were hashed. A missing row and a rewritten row are both "the fields do not
    match the hash" — and the check need not distinguish more than that,
    because both have the same consequence."""
    storage = PostgresStorage(db)
    _write(version, storage, [_message("message-1")], write_version_1)
    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 1"))
    findings = verify(storage)
    assert [f.event_id for f in findings] == [1]
    assert findings[0].reason == "hash does not match the fields"


# ---------------------------------------------------------------------------
# Hash format version 2 ({ref}`hash-version-2`): the check computes each row
# in the version the row names, and a log may hold both.
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_a_version_1_chain_still_passes(db: Engine, write_version_1: WriteVersion1) -> None:
    storage = PostgresStorage(db)
    write_version_1(storage, [_event("a"), _message("m"), _event("c")], NOW)
    assert verify(storage) == []


@pytest.mark.db
def test_a_chain_of_both_versions_passes(db: Engine, write_version_1: WriteVersion1) -> None:
    storage = PostgresStorage(db)
    write_version_1(storage, [_message("m")], NOW)
    append(storage, [_event("b")], recorded_at=NOW)
    with storage.begin() as c:
        versions = [row.hash_version for row in storage.read(c, from_id=1, limit=10)]
    assert versions == [1, 2]
    assert verify(storage) == []


@pytest.mark.db
def test_v1_a_unit_without_content_is_the_units_hash_finding(
    db: Engine, write_version_1: WriteVersion1
) -> None:
    """Version 1 takes the texts of all units into one digest, so a unit
    without content leaves it nothing to be computed from. That is a finding
    at the units digest, not a crash."""
    storage = PostgresStorage(db)
    write_version_1(storage, [_message("m")], NOW)
    with db.begin() as c:
        c.execute(text("UPDATE unit SET content = NULL WHERE event_id = 1 AND seq = 1"))
    assert verify(storage) == [Finding(1, "units_hash does not match the units")]


@pytest.mark.db
def test_v2_a_rewritten_unit_fires_on_that_unit_and_not_on_its_neighbour(db: Engine) -> None:
    """The digest per unit names the unit: unit 2 rewritten, unit 2 reported,
    and the units digest over the stored unit digests stays intact."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE unit SET content = 'Please deny.' WHERE event_id = 1 AND seq = 2"))
    assert verify(storage) == [Finding(1, "unit 2 does not match its digest")]


@pytest.mark.db
def test_v2_a_rewritten_salt_fires(db: Engine, truncate_statement: str) -> None:
    """A salt needs no attestation of its own: it is an input of its digest,
    and a rewritten salt breaks the digest like rewritten content would."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload_salt = :s WHERE id = 1"), {"s": b"\x01" * 32})
    assert verify(storage) == [Finding(1, "payload_hash does not match the payload")]

    with db.begin() as c:
        c.execute(text(truncate_statement))
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(
            text("UPDATE unit SET salt = :s WHERE event_id = 1 AND seq = 1"), {"s": b"\x01" * 32}
        )
    assert verify(storage) == [Finding(1, "unit 1 does not match its digest")]


@pytest.mark.db
def test_v2_a_missing_salt_or_digest_fires_and_does_not_break_off(db: Engine) -> None:
    """A version 2 row that lost a salt or a digest beside its content has
    nothing to compute against. That is a finding at the digest it belongs
    to, never an exception: a payload salt set to NULL is the payload's
    finding, a unit digest set to NULL is the unit's and the units digest's."""
    storage = PostgresStorage(db)
    append(storage, [_message("m"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload_salt = NULL WHERE id = 1"))
        c.execute(text("UPDATE unit SET digest = NULL WHERE event_id = 2 AND seq = 1"))
    assert verify(storage) == [
        Finding(1, "payload_hash does not match the payload"),
        Finding(2, "unit 1 does not match its digest"),
        Finding(2, "units_hash does not match the units"),
    ]


@pytest.mark.db
def test_v2_a_deleted_unit_row_fires(db: Engine) -> None:
    """The units digest still covers the whole set: a deleted unit has no
    digest of its own left to fail, and the set it is missing from does."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("DELETE FROM unit WHERE event_id = 1 AND seq = 2"))
    assert verify(storage) == [Finding(1, "units_hash does not match the units")]


@pytest.mark.db
def test_v2_a_unit_rewritten_together_with_its_digest_fires(db: Engine) -> None:
    """Content, salt and digest of one unit rewritten so that they agree with
    one another: the unit on its own holds, and the units digest, which the
    event hash attests, does not."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    salt = b"\x02" * 32
    forged = unit_digest(
        seq=1,
        content="Price remains 100000 Euro.",
        start_ms=None,
        end_ms=None,
        speaker=None,
        salt=salt,
    )
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE unit SET content = 'Price remains 100000 Euro.', salt = :s, digest = :d "
                "WHERE event_id = 1 AND seq = 1"
            ),
            {"s": salt, "d": forged},
        )
    assert verify(storage) == [Finding(1, "units_hash does not match the units")]


@pytest.mark.db
def test_a_flipped_hash_version_fires(db: Engine) -> None:
    """The version stands in the row and in the hashed object. Flipped in the
    row alone, the row is computed in a format it was not written in, and
    nothing adds up — least of all the event hash."""
    storage = PostgresStorage(db)
    append(storage, [_message("m")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash_version = 1 WHERE id = 1"))
    assert Finding(1, "hash does not match the fields") in verify(storage)


@pytest.mark.db
def test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on(db: Engine) -> None:
    """A version the check doesn't know is reported and not computed in some
    version it does know, which would be guessing. The linkage is checked all
    the same, and so is the next row."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash_version = 3 WHERE id = 1"))
        c.execute(
            text(
                "UPDATE event SET payload = jsonb_set(payload, '{note}', '\"forged\"') WHERE id = 2"
            )
        )
    assert verify(storage) == [
        Finding(1, "hash_version 3 is not known"),
        Finding(2, "payload_hash does not match the payload"),
    ]


# ---------------------------------------------------------------------------
# Finding W1 of the final review: one single poisoned row blinded the check of
# the **whole** chain, because `verify` broke off with `InvalidPayload`. That
# is the opposite of what an integrity check is supposed to deliver — whoever
# can forge one row could hide every further forgery behind it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        # A floating point number: the canonicalisation rejects it, because
        # its rendering is language-dependent ({ref}`canonicalization`). jsonb
        # preserves `1.5` as a number with decimal places, psycopg returns it
        # as a `float`.
        ("float", '{"note":1.5,"evidence":"recollection"}'),
        # An upper-case key: violates `^[a-z][a-z0-9_]*$`.
        ("uppercase", '{"Note":"b","evidence":"recollection"}'),
    ],
)
@WRITTEN_IN
@pytest.mark.db
def test_w1_a_non_canonicalizable_payload_reports_and_does_not_break_off(
    db: Engine, write_version_1: WriteVersion1, version: int, name: str, payload: str
) -> None:
    """A chain of three events with the middle one poisoned: one finding for
    the middle one, no break-off, and event 3 is demonstrably still checked.

    The proof for "it carries on" is not the absence of an exception —
    `verify` could also stop silently after event 2. That is why event 3 is
    forged **in addition**: if its finding appears, the check really skipped
    the poisoned row and did not leave the chain.
    """
    storage = PostgresStorage(db)
    _write(version, storage, [_event("a"), _event("b"), _event("c")], write_version_1)
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
    # The path runs from the payload, as in version 1, and not from the header
    # the version 2 digest wraps the payload in (`$.payload: key 'Note' …`).
    assert findings[0].reason.startswith("payload not canonicalizable: $: key 'Note' ")
    # The unit's own digest since `append` writes version 2; in version 1 the
    # same forgery is the units digest's finding.
    assert findings[1].reason == "unit 1 does not match its digest"


@pytest.mark.db
def test_w1_a_poisoned_payload_does_not_blind_the_unit_check_in_version_1(
    db: Engine, write_version_1: WriteVersion1
) -> None:
    """The same two forgeries in one version 1 row: the payload and the units
    are recomputed one after the other there too, so the poisoned payload
    does not keep the units digest from being compared."""
    storage = PostgresStorage(db)
    write_version_1(storage, [_message("message-1")], NOW)
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
    assert findings[0].reason.startswith("payload not canonicalizable: $: key 'Note' ")
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


def _anchor_of(storage: PostgresStorage) -> Anchor:
    """The tip of an intact chain, the way `previously anchor` prints it."""
    examination = examine(storage)
    assert examination.findings == ()
    assert examination.tip is not None
    return examination.tip


def _delete_event(db: Engine, event_id: int) -> None:
    """Forged with plain SQL: nothing in the append path can delete."""
    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = :id"), {"id": event_id})
        c.execute(text("DELETE FROM unit WHERE event_id = :id"), {"id": event_id})
        c.execute(text("DELETE FROM event WHERE id = :id"), {"id": event_id})


@pytest.mark.db
def test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one(db: Engine) -> None:
    """The case stage 1a measured and could not close ({ref}`external-anchor`):
    three events, the tip deleted, and the chain that is left is consistent in
    itself. The first assertion is the control — without an anchor nothing is
    amiss — and the second is what the anchor adds."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    assert anchor.id == 3
    _delete_event(db, 3)

    assert verify(storage) == []
    assert examine(storage, anchors=[anchor]).findings == (
        Finding(3, "anchored event is missing (the log ends at 2)"),
    )
    assert examine(storage, anchors=[anchor], exact=True).findings == (
        Finding(3, "anchored event is missing (the log ends at 2)"),
    )


@pytest.mark.db
def test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor(
    db: Engine, truncate_statement: str
) -> None:
    """Rewriting the whole chain is the forgery in its purest form: the result
    is a chain the append path itself produced. Emptied and filled again with
    other events here, which is that."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    with db.begin() as c:
        c.execute(text(truncate_statement))
    append(storage, [_event("x"), _event("y")], recorded_at=NOW)

    assert verify(storage) == []
    assert examine(storage, anchors=[anchor]).findings == (
        Finding(2, "hash does not match the anchor"),
    )
    assert examine(storage, anchors=[anchor], exact=True).findings == (
        Finding(2, "hash does not match the anchor"),
    )


@pytest.mark.db
def test_an_appended_event_passes_contains_and_fails_exact(db: Engine) -> None:
    """An anchor pins a prefix ({ref}`external-anchor`). An event appended
    after it looks like growth — and a forged one is not told apart from a
    legitimate one, which is why it is appended the ordinary way here. Only
    the comparison of the tip with the anchor sees it, and only while nothing
    legitimate was added: the first assertion is that moment of rest."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    assert examine(storage, anchors=[anchor], exact=True).findings == ()

    append(storage, [_event("c")], recorded_at=NOW)
    assert examine(storage, anchors=[anchor]).findings == ()
    assert examine(storage, anchors=[anchor], exact=True).findings == (
        Finding(3, "the log continues past the newest anchor (2)"),
    )


@pytest.mark.db
def test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check(db: Engine) -> None:
    """The limit of every anchor, pinned ({ref}`external-anchor`): it attests
    only what existed when it was taken. Event 3 arrived after the anchor and
    was deleted again; nothing shows that it ever existed. Whoever closes this
    later will see this test turn red."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    append(storage, [_event("c")], recorded_at=NOW)
    tip = examine(storage).tip
    assert tip is not None
    assert tip.id == 3
    _delete_event(db, 3)
    assert examine(storage).tip == anchor

    assert examine(storage, anchors=[anchor]).findings == ()
    assert examine(storage, anchors=[anchor], exact=True).findings == ()


@pytest.mark.db
def test_exact_without_an_anchor_is_refused(db: Engine) -> None:
    """There is nothing to compare the tip with. Refused in the core and not
    only at the command line, so that a second entry point gets the same
    answer."""
    with pytest.raises(InvalidPayload, match="at least one anchor"):
        examine(PostgresStorage(db), exact=True)


@pytest.mark.db
def test_an_empty_log_has_no_tip_and_misses_every_anchor(db: Engine) -> None:
    """An empty log has no tip, so every anchor is missing and the finding says
    the log ends at 0 (review focus 4 of the 2026-10-04 external-anchor
    plan)."""
    storage = PostgresStorage(db)
    assert examine(storage) == Examination((), None)
    stray = Anchor(1, b"\x11" * 32)
    assert examine(storage, anchors=[stray]).findings == (
        Finding(1, "anchored event is missing (the log ends at 0)"),
    )


@pytest.mark.db
def test_only_an_intact_chain_gives_an_anchor(db: Engine) -> None:
    """`anchor` is the tip only when the pass found nothing: an anchor taken on
    a broken chain would vouch for the break ({ref}`external-anchor`). The
    rule lives in the core so that a second entry point cannot hand out the
    tip of a broken chain by forgetting it. `tip` stays set either way — it
    is where the log ends."""
    storage = PostgresStorage(db)
    empty = examine(storage)
    assert (empty.tip, empty.anchor) == (None, None)

    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    intact = examine(storage)
    assert intact.tip is not None
    assert intact.anchor == intact.tip

    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 2"), {"h": b"\x00" * 32})
    broken = examine(storage)
    assert broken.findings
    assert broken.tip == Anchor(2, b"\x00" * 32)
    assert broken.anchor is None


@pytest.mark.db
def test_the_same_line_repeated_gives_one_finding(db: Engine) -> None:
    """The routine appends the same line again whenever no event arrived, so
    a quiet weekend leaves many copies of one anchor in the file. A rewritten
    event is reported against that anchor once, not once per copy."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\x00" * 32})

    assert examine(storage, anchors=[anchor, anchor, anchor]).findings == (
        Finding(1, "hash does not match the fields"),
        Finding(1, "hash does not match the anchor"),
    )


@pytest.mark.db
def test_two_lines_for_one_position_are_both_checked(db: Engine) -> None:
    """The same line twice is harmless; two lines that disagree about one
    position cannot both hold, and the one that does not is reported."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    wrong = Anchor(1, b"\x22" * 32)

    assert examine(storage, anchors=[anchor, anchor]).findings == ()
    assert examine(storage, anchors=[anchor, wrong]).findings == (
        Finding(1, "hash does not match the anchor"),
    )


@pytest.mark.db
def test_anchors_are_checked_across_a_batch_boundary(db: Engine) -> None:
    """Anchors are checked as the pass comes by them, so an anchor and the tip
    that lie in later batches than the first are checked all the same (review
    focus 3 of the 2026-10-04 external-anchor plan). Five events in batches of
    two: the anchor at 3 lies in the second batch, the tip in the third."""
    storage = PostgresStorage(db)
    append(storage, [_event(str(n)) for n in range(5)], recorded_at=NOW)
    tip = _anchor_of(storage)
    assert tip.id == 5
    with db.begin() as c:
        third = c.execute(text("SELECT hash FROM event WHERE id = 3")).scalar_one()

    anchors = [Anchor(3, bytes(third)), tip]
    assert examine(storage, anchors=anchors, exact=True, batch=2) == Examination((), tip)
    assert examine(storage, anchors=[Anchor(3, b"\x33" * 32)], batch=2).findings == (
        Finding(3, "hash does not match the anchor"),
    )
