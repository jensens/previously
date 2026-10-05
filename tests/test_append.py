# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from datetime import UTC
from itertools import pairwise
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.append import append
from previously.core.append import BACKOFF_CAP
from previously.core.append import backoff_delay
from previously.core.append import MAX_BATCH
from previously.core.errors import BatchTooLarge
from previously.core.errors import InvalidPayload
from previously.core.hashing import payload_hash_v2
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text
from typing import cast

import pytest
import threading


NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
OCCURRED = datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)


def _event(external_id: str, content: str = "Hello") -> RawEvent:
    return RawEvent(
        source="cli",
        external_id=external_id,
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext(content),
        payload={"note": content},
    )


@pytest.mark.db
def test_the_first_event_is_genesis(db: Engine) -> None:
    storage = PostgresStorage(db)
    ids = append(storage, [_event("a")], recorded_at=NOW)
    assert ids == [1]
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
    assert row.prev_hash is None


@pytest.mark.db
def test_append_writes_version_2_with_a_salt_for_the_payload_and_each_unit(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event("a", "First.\n\nSecond.")], recorded_at=NOW)
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
        units = storage.units(c, 1)
    assert row.hash_version == 2
    assert row.payload_salt is not None
    assert len(row.payload_salt) == 32
    assert len(units) == 2
    for unit in units:
        assert unit.digest is not None
        assert unit.salt is not None
        assert (len(unit.digest), len(unit.salt)) == (32, 32)


@pytest.mark.db
def test_the_id_comes_from_the_predecessor(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    ids = append(storage, [_event("b")], recorded_at=NOW)
    assert ids == [2]
    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=10))
    assert rows[1].prev_hash == rows[0].hash


@pytest.mark.db
def test_a_sub_chain_in_one_call(db: Engine) -> None:
    storage = PostgresStorage(db)
    ids = append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    assert ids == [1, 2, 3]
    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=10))
    assert rows[1].prev_hash == rows[0].hash
    assert rows[2].prev_hash == rows[1].hash


@pytest.mark.db
def test_idempotency_same_id_no_new_event(db: Engine) -> None:
    storage = PostgresStorage(db)
    first = append(storage, [_event("a")], recorded_at=NOW)
    second = append(storage, [_event("a")], recorded_at=NOW)
    assert first == second == [1]
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM unit")).scalar_one() == 1


@pytest.mark.db
def test_an_idempotent_skip_does_not_shift_the_chain(db: Engine) -> None:
    """The subtlest property of `append`: an event that is skipped by
    idempotency within the same batch must not shift the chain position of the
    events that come after it — `next_id` and `prev` must not move on while
    skipping."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    ids = append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    assert ids == [1, 2]
    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=10))
    assert [r.id for r in rows] == [1, 2]
    assert rows[1].prev_hash == rows[0].hash


@pytest.mark.db
def test_the_units_are_written(db: Engine) -> None:
    storage = PostgresStorage(db)
    append(storage, [_event("a", "first\n\nsecond")], recorded_at=NOW)
    with storage.begin() as c:
        assert [u.content for u in storage.units(c, 1)] == ["first", "second"]


@pytest.mark.db
def test_a_conflict_on_the_chain_position_is_retried(db: Engine) -> None:
    """Two connections grab the same tip. Both events land, the chain is intact."""
    storage = PostgresStorage(db)
    append(storage, [_event("groundwork")], recorded_at=NOW)

    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def do_append(external_id: str) -> None:
        try:
            barrier.wait(timeout=10)
            append(storage, [_event(external_id)], recorded_at=NOW)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=do_append, args=(f"p{i}",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        # Without this proof, a hanging thread failed on a follow-up assertion
        # or on an IndexError — not with "thread is hanging".
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors
    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=10))
    assert len(rows) == 3
    for before, after in pairwise(rows):
        assert after.prev_hash == before.hash
        assert after.id == before.id + 1


@pytest.mark.db
def test_idempotency_in_the_race_produces_no_duplicate(db: Engine) -> None:
    """Two concurrent appends with identical content yield exactly one event
    and the same identifier. That runs **not** via `SourceKeyTaken` — that
    branch is structurally unreachable out of `append`, see the comment at the
    `except SourceKeyTaken` branch in `core/append.py` — but via
    `ChainPositionTaken`: the loser fails with its event INSERT on the chain
    position (`event_pkey`/`event_prev_hash_idx`/`event_hash_idx`), re-reads
    the tip, finds the winner's event via `lookup` and returns its identifier
    instead of inserting again."""
    storage = PostgresStorage(db)
    results: list[list[int]] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def do_append() -> None:
        try:
            barrier.wait(timeout=10)
            results.append(append(storage, [_event("same")], recorded_at=NOW))
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=do_append) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors
    assert results[0] == results[1]
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 1


@pytest.mark.db
def test_a_too_large_batch_is_rejected(db: Engine) -> None:
    """A limited batch size against starvation ({ref}`concurrency`)."""
    storage = PostgresStorage(db)
    too_many = [_event(f"e{i}") for i in range(MAX_BATCH + 1)]
    with pytest.raises(BatchTooLarge, match="starve"):
        append(storage, too_many, recorded_at=NOW)


@pytest.mark.db
def test_occurred_at_without_a_time_zone_is_rejected(db: Engine) -> None:
    """Review Focus 3, the core side: a naive timestamp is not reproducible."""
    storage = PostgresStorage(db)
    # Naive on purpose: that a naive timestamp gets rejected cannot be tested
    # without building one, and `DTZ001` forbids exactly that construction.
    # That is the whole justification for the suppression (finding G-4: it
    # used to stand there without one).
    naive_occurred = datetime(2026, 10, 1, 9, 0, 0)  # noqa: DTZ001 — deliberate, see above
    naive = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=naive_occurred,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("x"),
        payload={},
    )
    with pytest.raises(InvalidPayload, match="time zone"):
        append(storage, [naive], recorded_at=NOW)


@pytest.mark.db
def test_the_kind_of_evidence_lands_in_the_payload(db: Engine) -> None:
    """The kind of evidence is otherwise irretrievably lost after this stage
    ({ref}`canonicalization`): nobody reads `RawEvent.evidence` in `append`
    before this task mixes it into the payload under the reserved key
    `evidence`."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.VERBATIM,
        units=split_plaintext("Hello"),
        payload={"note": "Hello"},
    )
    append(storage, [event], recorded_at=NOW)
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
    assert row.payload is not None
    assert row.payload["evidence"] == "verbatim"
    assert row.payload["note"] == "Hello"
    # The property that task 8 needs for the chain check: payload and
    # payload_hash have to mean the same payload. Computed in the hash format
    # `append` writes, which is version 2 since stage 1c, with the row's salt.
    assert row.hash_version == 2
    assert row.payload_salt is not None
    assert payload_hash_v2(row.payload, row.payload_salt) == row.payload_hash


@pytest.mark.db
def test_the_reserved_key_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("Hello"),
        payload={"evidence": "anything"},
    )
    with pytest.raises(InvalidPayload, match="reserved"):
        append(storage, [event], recorded_at=NOW)


# --- References to blobs ({ref}`blobs`) --------------------------------------

_ADDRESS = "5" * 64


def _with_blobs(*blobs: BlobRef, payload: dict[str, object] | None = None) -> RawEvent:
    return RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("Hello"),
        payload={"note": "Hello"} if payload is None else payload,
        blobs=blobs,
    )


def _register(db: Engine) -> list[tuple[int, bytes]]:
    with db.connect() as c:
        rows = c.execute(text("SELECT event_id, sha256 FROM event_blob ORDER BY 1, 2")).all()
    return [(event_id, sha256) for event_id, sha256 in rows]


@pytest.mark.db
def test_blob_references_land_in_the_payload_and_in_the_register(db: Engine) -> None:
    storage = PostgresStorage(db)
    reference = BlobRef(sha256=_ADDRESS, size=12, media_type="text/plain", filename="notes.txt")
    append(storage, [_with_blobs(reference)], recorded_at=NOW)
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
        registered = storage.blobs_by_event(c, [1])
    assert row.payload is not None
    assert row.payload["blobs"] == [
        {"sha256": _ADDRESS, "size": 12, "media_type": "text/plain", "filename": "notes.txt"}
    ]
    assert registered == {1: [bytes.fromhex(_ADDRESS)]}
    assert verify(storage) == []


@pytest.mark.db
def test_an_event_without_blobs_carries_no_blobs_key(db: Engine) -> None:
    """Its payload is the one it would have had before blobs existed."""
    storage = PostgresStorage(db)
    append(storage, [_with_blobs()], recorded_at=NOW)
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
    assert row.payload == {"note": "Hello", "evidence": "recollection"}
    assert _register(db) == []


@pytest.mark.db
def test_the_key_blobs_is_reserved(db: Engine) -> None:
    """Reserved like `evidence`, with or without attachments: a payload that
    already carries the key is refused rather than overwritten, and nothing
    is written."""
    storage = PostgresStorage(db)
    for blobs in ((), (BlobRef(sha256=_ADDRESS, size=1, media_type="text/plain"),)):
        with pytest.raises(InvalidPayload) as caught:
            append(storage, [_with_blobs(*blobs, payload={"blobs": []})], recorded_at=NOW)
        assert str(caught.value) == (
            "payload already carries the key 'blobs' — it is reserved for the attachments"
        )
    with storage.begin() as c:
        assert storage.count_events(c) == 0


@pytest.mark.db
def test_the_same_content_twice_at_one_event_is_two_references_and_one_register_row(
    db: Engine,
) -> None:
    """Review focus 3 of the 2026-10-04 stage 1c plan: two attachments of one
    mail with the same content under two names. Two references, because each
    names its use; one row, because the register answers which events use a
    blob, and the primary key on `(event_id, sha256)` would refuse a second."""
    storage = PostgresStorage(db)
    append(
        storage,
        [
            _with_blobs(
                BlobRef(sha256=_ADDRESS, size=4, media_type="image/png", filename="logo.png"),
                BlobRef(sha256=_ADDRESS, size=4, media_type="image/png", filename="logo-1.png"),
            )
        ],
        recorded_at=NOW,
    )
    with storage.begin() as c:
        row = next(iter(storage.read(c, from_id=1, limit=1)))
    assert row.payload is not None
    blobs = cast("list[dict[str, object]]", row.payload["blobs"])
    assert [blob["filename"] for blob in blobs] == ["logo.png", "logo-1.png"]
    assert _register(db) == [(1, bytes.fromhex(_ADDRESS))]
    assert verify(storage) == []


@pytest.mark.db
@pytest.mark.parametrize(
    ("reference", "message"),
    [
        (
            BlobRef(sha256="A" * 64, size=1, media_type="text/plain"),
            "blob reference 1: sha256 is not 64 hexadecimal characters, lower case",
        ),
        (
            BlobRef(sha256=_ADDRESS[:63], size=1, media_type="text/plain"),
            "blob reference 1: sha256 is not 64 hexadecimal characters, lower case",
        ),
        (
            BlobRef(sha256=_ADDRESS, size=-1, media_type="text/plain"),
            "blob reference 1: size must be at least 0, is -1",
        ),
        (
            BlobRef(sha256=_ADDRESS, size=1, media_type=""),
            "blob reference 1: media_type is empty",
        ),
    ],
    ids=["upper-case", "63-characters", "negative-size", "empty-media-type"],
)
def test_a_blob_reference_that_is_not_one_is_refused(
    db: Engine, reference: BlobRef, message: str
) -> None:
    """The second reference is the broken one, behind a good one, so that the
    index in the message is the reference's and not always 0. Refused before
    anything reaches the store: no event and no register row."""
    storage = PostgresStorage(db)
    good = BlobRef(sha256="6" * 64, size=1, media_type="text/plain")
    with pytest.raises(InvalidPayload) as caught:
        append(storage, [_with_blobs(good, reference)], recorded_at=NOW)
    assert str(caught.value) == message
    with storage.begin() as c:
        assert storage.count_events(c) == 0
    assert _register(db) == []


# --- Finding W3: backing off between the attempts ------------------------
#
# `backoff_delay` is a pure function — checked directly, without putting the
# clock or `time.sleep` out of joint (as the review finding required). That the
# retry loop itself keeps working stays the business of the existing
# concurrency tests above (`test_a_conflict_on_the_chain_position_...`,
# `test_idempotency_in_the_race_...`) and of
# `test_p3_concurrent_writers_...` in `tests/test_properties.py`: those run
# against a real, contended database, and a counting wrapper around
# `backoff_delay` measured 1 retry for two writers and 2 to 3 for three, over
# 20 collisions — the backing off is therewith a real part of that path and
# not merely claimed.
#
# **Not on every run, though.** The same measurement counted 0 retries for the
# very first collision against a cold connection pool: establishing the
# connection took longer there than the winner's whole transaction, so the
# loser read the tip only after the winner had committed and never collided.
# Whoever relies on the retry branch being exercised is relying on timing. The
# properties the concurrency tests assert hold either way, which is the point;
# this note stands here so that the earlier wording ("on every run") does not
# come back as an assurance nobody measured.


def test_backoff_delay_is_never_negative() -> None:
    for attempt in range(10):
        for _ in range(30):
            assert backoff_delay(attempt) >= 0


def test_backoff_delay_stays_below_the_cap() -> None:
    for attempt in range(10):
        for _ in range(30):
            assert backoff_delay(attempt) <= BACKOFF_CAP


def test_the_backoff_upper_bound_grows_with_the_attempt() -> None:
    """Full jitter out of `[0, basis * 2**attempt]`, capped: the upper bound
    per attempt grows until it reaches the cap — not the single return value,
    which is random thanks to the jitter. With a fixed wait (no growing upper
    bound) two writers would stay in lockstep, only slower — precisely the
    behaviour that backing off was invented against.

    Checked over the **maximum of many samples** per attempt, not over a
    single call: a single call says nothing about the upper bound, only a
    distribution does. With 300 samples the maximum of `uniform(0, cap)` lies
    in expectation at `cap · 300/301` — the probability that the maximum of a
    **smaller** cap exceeds that of a **larger** one is astronomically small
    as long as the caps differ markedly (here: a doubling per attempt).
    """
    maxima = [max(backoff_delay(attempt) for _ in range(300)) for attempt in range(5)]
    for smaller, larger in pairwise(maxima):
        assert larger > smaller


def test_backoff_delay_is_random_not_constant() -> None:
    """Not always the same value over many calls — otherwise the jitter would
    be broken and two writers would stay in lockstep."""
    values = {backoff_delay(5) for _ in range(50)}
    assert len(values) > 1


# --- Finding G1: units arrive in the database unchecked ------------------


@pytest.mark.db
def test_a_seq_below_one_is_refused(db: Engine) -> None:
    """Finding G1: the database has `unit_seq_check`, but the message is
    supposed to come out of `core`, not as a raw sqlalchemy error."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=0, content="x"),),
        payload={},
    )
    # The whole clause, not just "seq" (finding N5): four of the six messages
    # in `_check_units` carry the word "seq", so "seq" would stay green on any
    # of the other three complaints about this unit.
    with pytest.raises(InvalidPayload, match=r"seq must be >= 1"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_a_duplicate_seq_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content="x"), RawUnit(seq=1, content="y")),
        payload={},
    )
    with pytest.raises(InvalidPayload, match="unique"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_a_null_byte_in_a_unit_is_refused(db: Engine) -> None:
    """The message is supposed to name the unit ('unit 1 contains a null
    byte'), not the path-based sentence out of `canonical`
    ('$.units[0].content: ...') that `units_hash` would otherwise have raised
    only while hashing."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content="before\x00after"),),
        payload={},
    )
    with pytest.raises(InvalidPayload, match=r"unit 1 contains a null byte"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_a_start_ms_outside_32_bit_is_refused(db: Engine) -> None:
    """Measured (not taken over from memory): a real PostgreSQL 17 container
    accepts `integer` up to 2**31-1 and from -(2**31) on, but fails on 2**31
    and on -(2**31)-1 with `NumericValueOutOfRange`."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content="x", start_ms=2**40),),
        payload={},
    )
    # The complaint along with the field (finding N5): "start_ms" alone is
    # also carried by the message about `start_ms` after `end_ms`, so a value
    # outside the 32-bit range reported with the wrong reason would have
    # stayed green.
    with pytest.raises(InvalidPayload, match=r"start_ms=\d+ lies outside the"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_a_start_ms_at_the_32_bit_boundary_is_accepted(db: Engine) -> None:
    """The boundary values themselves are valid — no off-by-one refusal."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content="x", start_ms=-(2**31), end_ms=2**31 - 1),),
        payload={},
    )
    assert append(storage, [event], recorded_at=NOW) == [1]


@pytest.mark.db
def test_a_start_ms_after_end_ms_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content="x", start_ms=200, end_ms=100),),
        payload={},
    )
    with pytest.raises(InvalidPayload, match="lies after"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_a_content_that_is_not_a_string_is_refused(db: Engine) -> None:
    """`content` is statically declared as `str` — `cast` here deliberately
    feigns a connector that builds `RawUnit` without a runtime check by the
    type checker (reachable from stage 2 on, not in 1a via the CLI, because
    `split_plaintext` builds the units itself)."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source="cli",
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=(RawUnit(seq=1, content=cast("str", 123)),),
        payload={},
    )
    with pytest.raises(InvalidPayload, match="content is not a string"):
        append(storage, [event], recorded_at=NOW)


# --- Finding W-1: source and external_id are checked in `core` ------------


@pytest.mark.db
@pytest.mark.parametrize("field", ["source", "external_id"])
@pytest.mark.parametrize(
    ("probe", "expected"),
    [("\ud800", "not representable as UTF-8"), ("\x00", "contains a null byte")],
)
def test_an_unrepresentable_identity_is_refused(
    db: Engine, field: str, probe: str, expected: str
) -> None:
    """`source` and `external_id` reach the driver through `lookup` **before**
    `event_hash` canonicalises them — so the canonicalisation
    ({ref}`payload-range`) decided about them too late. Measured through the
    command line before the fix: 95 lines of
    `UnicodeEncodeError` out of psycopg for the surrogate, 89 lines of
    `sqlalchemy.exc.DataError` for the null byte.

    The message has to name the field, because the sentence is otherwise no
    instruction for what to correct.
    """
    storage = PostgresStorage(db)
    values = {"source": "cli", "external_id": "a"}
    values[field] = f"value{probe}"
    event = RawEvent(
        source=values["source"],
        external_id=values["external_id"],
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("x"),
        payload={},
    )
    with pytest.raises(InvalidPayload, match=f"{field}.*{expected}"):
        append(storage, [event], recorded_at=NOW)


@pytest.mark.db
def test_the_same_key_twice_in_one_batch_is_refused(db: Engine) -> None:
    """Finding N-5: the fifth silent data loss of this session.

    Exactly the measured case — two entries with the same
    `(source, external_id)` but a **different payload and different units**.
    Measured against the version before the check:

        append([first, second])  ->  [1, 1]

        event rows:      [(1, {'note': 'the first', 'evidence': 'verbatim'})]
        unit rows:       [(1, 1, 'First content.')]
        source_key rows: [('email', 'message-1', 1)]
        verify():        []

        payload {'note': 'the second'}       -> NOT stored
        units 'Second content, quite ...'    -> NOT stored

    No exception, no finding, no warning — and the caller got **two**
    identifiers back as though both had been recorded. In an append-only store
    that is irretrievable.

    Idempotency **between** calls is the wanted property. Idempotency
    **within** a batch nobody asked for, and it is indistinguishable from a
    caller's mistake: are the entries equal, refusing costs nothing; are they
    different, the caller has a bug, and silently taking the first is the
    worst possible answer because it does not come to notice.
    """
    storage = PostgresStorage(db)
    first = RawEvent(
        source="email",
        external_id="message-1",
        occurred_at=OCCURRED,
        evidence=Evidence.VERBATIM,
        units=split_plaintext("First content."),
        payload={"note": "the first"},
    )
    second = RawEvent(
        source="email",
        external_id="message-1",
        occurred_at=OCCURRED,
        evidence=Evidence.VERBATIM,
        units=split_plaintext("Second content, quite different."),
        payload={"note": "the second"},
    )

    # The message has to name the key and both batch positions, or it does not
    # say what to deduplicate.
    with pytest.raises(InvalidPayload, match=r"appears twice in the batch, at index 0 and index 1"):
        append(storage, [first, second], recorded_at=NOW)

    # And nothing at all was written: the refusal happens in the preparation,
    # before the first transaction opens.
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 0
        assert c.execute(text("SELECT count(*) FROM unit")).scalar_one() == 0


@pytest.mark.db
def test_the_same_key_in_two_separate_calls_still_gives_the_same_id(db: Engine) -> None:
    """The counter-test to the refusal above, and the property it must not
    break: idempotency **between** calls stays, which is what the idempotency
    is for ({ref}`canonicalization`). Without this test the batch check could
    be widened to span calls, and nothing would notice."""
    storage = PostgresStorage(db)
    assert append(storage, [_event("a")], recorded_at=NOW) == [1]
    assert append(storage, [_event("a")], recorded_at=NOW) == [1]
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 1


@pytest.mark.db
def test_an_identity_that_is_not_a_string_is_refused(db: Engine) -> None:
    """The same boundary check as for `unit.content`: `RawEvent.source` is
    statically a `str`, and `cast` here feigns the connector from stage 2 on
    that builds `RawEvent` without a runtime check by the type checker. Without
    the check, psycopg decides — out of `core`, as a foreign exception."""
    storage = PostgresStorage(db)
    event = RawEvent(
        source=cast("str", 123),
        external_id="a",
        occurred_at=OCCURRED,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("x"),
        payload={},
    )
    with pytest.raises(InvalidPayload, match="source: value is not a string, but int"):
        append(storage, [event], recorded_at=NOW)
