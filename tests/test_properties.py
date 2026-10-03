# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Properties of the chain and of the canonicalisation (§10.2 of the 1a spec).

Property-based testing is clearly superior here: "rebuilt yields the same" and
"no branching possible" are invariants over random sequences of events, not
example tests.
"""

import json
import threading
from datetime import UTC, datetime
from itertools import pairwise

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, text

from previously.contract.types import Evidence, RawEvent
from previously.core.append import append
from previously.core.canonical import MAX_SAFE_INT, canonical
from previously.core.errors import InvalidPayload
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage

NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)

# Only the permitted payload range: no floating point numbers, ASCII keys,
# integers inside the safe range, no null bytes.
#
# The filter excludes the reserved key `evidence`: `append` mixes it into
# every payload and refuses a payload that already carries it (§5.1). The
# regex could produce it in theory, but as measured (3000 examples, searched
# for deliberately as well) not a single hit — the filter is documentation of
# the restricted payload range here, not protection against an observed error
# (ruling T10-d).
keys = st.from_regex(r"\A[a-z][a-z0-9_]{0,12}\Z").filter(lambda k: k != "evidence")
# Category Cs (lone UTF-16 surrogates, U+D800–U+DFFF) excluded: without this
# exclusion `st.characters` produces valid Python str characters that
# `canonical` has rejected since a fix round in task 2, because they are not
# representable as UTF-8. Without the exclusion test_p4 is flaky — as measured
# around 0.17 % of the examples are affected, so with hypothesis' default of
# 100 examples on average every sixth run goes red, with a message that looks
# like an error in the canonicalisation instead of like a test strategy drawn
# too wide (ruling T10-a). Do not remove again without measuring anew.
texts = st.text(
    alphabet=st.characters(blacklist_characters="\x00", blacklist_categories=["Cs"]),
    min_size=0,
    max_size=40,
)
scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-MAX_SAFE_INT, max_value=MAX_SAFE_INT),
    texts,
)
payloads = st.dictionaries(keys, scalars, max_size=6)

SLOW = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

# Settings of their own for the concurrency property (finding W4): ten
# examples instead of SLOW's twenty-five, and two to four writers instead of
# more.
#
# The reason is the cost per example, and it is measured, not estimated: every
# example truncates three tables, starts real threads with real connections
# against the test container and makes them collide on the same chain
# position, whereupon the losers back off and repeat. Measured, ten examples
# run 0.39 s net (27–54 ms each) — SLOW's twenty-five would be a second of
# suite time for a property whose input space holds 28 combinations in total.
#
# Two writers are the smallest number that can collide at all, and from three
# on a loser can lose a second time, which is the branch `MAX_RETRIES` and
# `backoff_delay` exist for. Four therefore already covers "lost repeatedly",
# while the engine's default pool (five connections) still serves every
# thread without queueing — queueing would make the test measure the pool
# instead of the chain.
CONCURRENT = settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

# The sample text for test_p5: a module constant instead of a repeated
# literal, so that the upper bound on the position below is derived from its
# length and can no longer drift apart from it (ruling T10-c). The extract
# wrote the bound as a number (0–30) next to a string 36 characters long and
# left the positions 31–35 unchecked, although the test name claims "every
# single-byte change".
SAMPLE_TEXT = "abcdefghijklmnopqrstuvwxyz0123456789"


def test_the_sample_text_for_p5_is_pure_ascii() -> None:
    """The precondition under test_p5's name, pinned (finding N3).

    `test_p5` claims "every single-byte change" and draws its positions out of
    `range(len(SAMPLE_TEXT))` — those are **character** positions. The two
    coincide only as long as the text is pure ASCII; with "ä" in the constant
    the test would still change one character, but no longer one byte, and its
    name would be claiming something it does not check.

    Not the name weakened, therefore, but the precondition fastened down: it
    is cheaper to keep than the distinction between characters and bytes is to
    explain, and whoever changes the constant finds out here instead of
    believing a name.
    """
    assert SAMPLE_TEXT.isascii()


@given(payloads)
def test_p4_key_order_does_not_change_the_hash(
    payload: dict[str, object],
) -> None:
    """P4: guards reproducibility across languages."""
    reversed_payload = dict(reversed(list(payload.items())))
    assert canonical(payload) == canonical(reversed_payload)


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_p6_a_floating_point_number_is_rejected(value: float) -> None:
    """P6."""
    with pytest.raises(InvalidPayload):
        canonical({"x": value})


# Produce values directly outside the safe range instead of sieving with
# `.filter()`: `st.integers()` draws overwhelmingly small magnitudes, so
# `.filter(lambda n: abs(n) > MAX_SAFE_INT)` discards so many examples that
# hypothesis' `HealthCheck.filter_too_much` fires — measured, not merely
# suspected: five runs of `test_p6b` reproduced that once (`7 inputs were
# generated successfully, while 50 inputs were filtered out`). The same kind
# of flake as ruling T10-a, only in the integer case instead of the text case,
# and not foreseen by the extract. Two disjoint ranges instead of one filter
# hit the same range without the discarding.
large_integers = st.one_of(
    st.integers(max_value=-MAX_SAFE_INT - 1),
    st.integers(min_value=MAX_SAFE_INT + 1),
)


@given(large_integers)
def test_p6b_a_too_large_integer_is_rejected(value: int) -> None:
    with pytest.raises(InvalidPayload):
        canonical({"x": value})


@pytest.mark.db
@SLOW
@given(st.lists(payloads, min_size=1, max_size=6))
def test_p1_every_sequence_passes_the_check(
    db: Engine, payload_sequence: list[dict[str, object]]
) -> None:
    """P1: for every sequence of appends, verify passes."""
    with db.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    storage = PostgresStorage(db)
    events = [
        RawEvent(
            source="hyp",
            external_id=f"e{i}",
            occurred_at=NOW,
            evidence=Evidence.RECOLLECTION,
            units=split_plaintext(f"unit {i}"),
            payload=payload,
        )
        for i, payload in enumerate(payload_sequence)
    ]
    append(storage, events, recorded_at=NOW)
    assert verify(storage) == []


@pytest.mark.db
@SLOW
@given(st.integers(min_value=2, max_value=5))
def test_p7_id_order_is_chain_order(db: Engine, count: int) -> None:
    """P7: the property that permits checking in id order at all.

    Over a **sequential** writer: one `append` with a sub-chain. The
    concurrent interleavings that §10.2 words P7 over are the business of
    `test_p3_...` below, which starts real threads for them.
    """
    with db.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    storage = PostgresStorage(db)
    events = [
        RawEvent(
            source="hyp",
            external_id=f"e{i}",
            occurred_at=NOW,
            evidence=Evidence.RECOLLECTION,
            units=split_plaintext(f"x{i}"),
            payload={},
        )
        for i in range(count)
    ]
    append(storage, events, recorded_at=NOW)
    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=100))
    assert [r.id for r in rows] == list(range(1, count + 1))
    for before, after in pairwise(rows):
        assert after.prev_hash == before.hash
        assert after.id == before.id + 1


@pytest.mark.db
@SLOW
@given(st.integers(min_value=0, max_value=len(SAMPLE_TEXT) - 1))
def test_p5_any_single_byte_change_fails_verification(db: Engine, position: int) -> None:
    """P5: checks the security property directly, not via a stand-in."""
    with db.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    storage = PostgresStorage(db)
    append(
        storage,
        [
            RawEvent(
                source="hyp",
                external_id="e1",
                occurred_at=NOW,
                evidence=Evidence.RECOLLECTION,
                units=split_plaintext("content"),
                payload={"text": SAMPLE_TEXT},
            )
        ],
        recorded_at=NOW,
    )
    changed = (
        SAMPLE_TEXT[:position]
        + ("X" if SAMPLE_TEXT[position] != "X" else "Y")
        + SAMPLE_TEXT[position + 1 :]
    )
    # Change only the field `text`, do not replace the whole payload: `append`
    # mixes the reserved key `evidence` into the stored payload (§5.1). An
    # UPDATE of the whole column would throw it away, and `verify` would then
    # fire for two reasons — a broken payload_hash *and* a missing key —
    # instead of for the one the test name claims (ruling T10-b). `jsonb_set`
    # really changes one field only, `evidence` stays standing untouched.
    #
    # `CAST(:new AS jsonb)`, not `:new::jsonb`: SQLAlchemy's `text()` treats a
    # doubled colon sequence directly after a bind parameter as an escape for
    # a literal colon, not as a parameter followed by the PostgreSQL cast —
    # measured with `text(...).compile().params`: `{}` instead of
    # `{"new": None}`, the parameter is not bound at all, and psycopg receives
    # `:new` literally and fails with a syntax error. `CAST(... AS jsonb)` is
    # the same operation without this conflict and is this code base's
    # convention already (see `tests/test_append.py`, `tests/test_verify.py`).
    with db.begin() as c:
        c.execute(
            text(
                "UPDATE event SET payload = jsonb_set(payload, '{text}', "
                "CAST(:new AS jsonb)) WHERE id = 1"
            ),
            {"new": json.dumps(changed)},
        )
    assert verify(storage) != []


@pytest.mark.db
@SLOW
@given(st.integers(min_value=2, max_value=4))
def test_p2_idempotency_across_repeated_appends(db: Engine, repetitions: int) -> None:
    """P2: the same (source, external_id) twice → the same id, the number of
    events unchanged."""
    with db.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    storage = PostgresStorage(db)
    event = RawEvent(
        source="hyp",
        external_id="always-the-same",
        occurred_at=NOW,
        evidence=Evidence.RECOLLECTION,
        units=split_plaintext("x"),
        payload={},
    )
    results = [append(storage, [event], recorded_at=NOW) for _ in range(repetitions)]
    assert all(r == results[0] for r in results)
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 1


@pytest.mark.db
@CONCURRENT
@given(st.lists(st.integers(min_value=1, max_value=2), min_size=2, max_size=4))
def test_p3_concurrent_writers_leave_one_gapless_chain_with_each_event_once(
    db: Engine, batch_sizes: list[int]
) -> None:
    """P3, and the concurrent half of P7 (§10.2, finding W4).

    The whole concurrency control of this stage is "the loser repeats" — no
    advisory lock, no `SELECT … FOR UPDATE`, only the unique indexes
    serialising. A single-threaded test checks none of that, and the plan had
    no P3 at all, so the property the mechanism exists for had never been
    stated.

    Real threads against the real database, therefore, and nothing imitated: a
    collision that is acted out proves nothing about collisions. The barrier
    is what makes the writers collide instead of queue — each one waits until
    all of them are there, so they read the **same** tip and at most one can
    commit on it.

    Measured, that puts `len(batch_sizes) - 1` writers or more through the
    `ChainPositionTaken` branch: counted over 20 collisions, two writers gave
    exactly 1 retry and three writers 2 to 3. It is **not** guaranteed,
    though — in the very first collision against a cold connection pool the
    count was 0, because establishing the connection took longer than the
    winner's entire transaction. The property has to hold either way; that is
    what "arbitrary interleavings" means, and that is why the assertions below
    are about the result and not about the number of retries.

    What the strategy draws is **one batch size per writer**, not merely the
    number of writers (measured: with `integers(2, 4)` the search space holds
    three values, hypothesis reports "Stopped because nothing left to do"
    after three examples, and seven of the ten never happen). A list over
    `{1, 2}` of length 2 to 4 holds 28 combinations, so the ten examples are
    ten real ones — and a writer with two events holds the chain position for
    both, which means the loser repeats a whole **sub-chain** and not just a
    single insert. That is §4.4's territory, and only this shape reaches it.

    Afterwards four things have to hold; the fourth is the one a count alone
    would not see.
    """
    with db.begin() as c:
        c.execute(text("TRUNCATE source_key, unit, event"))
    storage = PostgresStorage(db)

    batches = [[f"w{writer}-{i}" for i in range(size)] for writer, size in enumerate(batch_sizes)]
    external_ids = [external_id for batch in batches for external_id in batch]
    errors: list[BaseException] = []
    barrier = threading.Barrier(len(batches))

    def write(batch: list[str]) -> None:
        try:
            barrier.wait(timeout=10)
            append(
                storage,
                [
                    RawEvent(
                        source="hyp",
                        external_id=external_id,
                        occurred_at=NOW,
                        evidence=Evidence.RECOLLECTION,
                        units=split_plaintext(f"unit {external_id}"),
                        payload={},
                    )
                    for external_id in batch
                ],
                recorded_at=NOW,
            )
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=write, args=(batch,)) for batch in batches]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        # Without this, a hanging thread fails on one of the assertions below
        # or on an IndexError instead of saying "thread is hanging" — the same
        # reasoning as in `tests/test_append.py`.
        assert not t.is_alive(), "thread is hanging"

    assert not errors, errors

    # 1. the check is without a finding
    assert verify(storage) == []

    with storage.begin() as c:
        rows = list(storage.read(c, from_id=1, limit=100))
        keys = storage.source_keys(c, [r.id for r in rows])

    # 2. the ids are gapless from 1 — losing consumes no number
    assert [r.id for r in rows] == list(range(1, len(external_ids) + 1))

    # 3. every prev_hash is the hash of the predecessor, and the first event
    #    is genesis. §10.2 words P3 as "no prev_hash occurs twice"; that
    #    follows from these two, and the distinctness is asserted alongside
    #    anyway, because it is the sentence the unique index with
    #    `NULLS NOT DISTINCT` actually enforces.
    assert rows[0].prev_hash is None
    for before, after in pairwise(rows):
        assert after.prev_hash == before.hash
    prev_hashes = [r.prev_hash for r in rows]
    assert len(set(prev_hashes)) == len(prev_hashes)

    # 4. every event is there exactly once. Over the source attributions and
    #    not over the row count: the same count would also come out if one
    #    writer had landed twice and another not at all.
    assert sorted(external_id for _, external_id in keys.values()) == sorted(external_ids)
