# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Appending to the log (§4 of the 1a spec).

The serialisation is done exclusively by the unique indexes on `prev_hash`
and `id`. No advisory lock, no `SELECT … FOR UPDATE`, no coordination between
processes — the loser retries.

Two classes of conflict, two recoveries:

- `event_prev_hash_idx`, `event_pkey` and `event_hash_idx` are the **same
  incident**: two writers computed the same `id` and the same `prev_hash` out
  of the same tip — and therewith, because both go into the event hash,
  inevitably the same `hash` as well. Which of the three indexes fires first
  is undetermined. Re-read the tip, retry. `storage` translates all three
  into `ChainPositionTaken`.
- `source_key_pkey` is **idempotency in the race**: the source event exists
  already. Re-read `lookup` for the whole batch; are **all** of them found,
  return their identifiers and do not retry. Is only part of them found, the
  rest genuinely does not exist yet and has to be appended, so retry — see
  the `except SourceKeyTaken` branch, and §4.2, which said "no retry" without
  that qualification until finding G-7 of the second final review. `storage`
  translates this conflict into `SourceKeyTaken`.

Telling the two classes of conflict apart happens in `storage` already, via
`diag.constraint_name` of the psycopg diagnosis — measured, dependable,
unlike a substring search in the error text, which would depend on language
and version. This module sees only the two translated exceptions, no driver
error.
"""

from previously.core.errors import BatchTooLarge
from previously.core.errors import ChainConflict
from previously.core.errors import InvalidPayload
from previously.core.hashing import event_hash
from previously.core.hashing import iso_utc
from previously.core.hashing import payload_hash
from previously.core.hashing import units_hash
from previously.storage.errors import ChainPositionTaken
from previously.storage.errors import SourceKeyTaken
from previously.storage.rows import EventRow
from previously.storage.rows import UnitRow
from typing import TYPE_CHECKING

import random
import time


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.types import RawEvent
    from previously.contract.types import RawUnit
    from previously.storage.postgres import PostgresStorage


MAX_RETRIES = 8

# A limited batch size against starvation (§4.4 of the 1a spec): a very large
# transaction holds for a long time and loses the conflict against every small
# submission that commits meanwhile.
MAX_BATCH = 500

# Fixed to "observation": everything that comes out of connectors and the
# command line is an observation. Assertions come from the model and therefore
# only in a later stage. A constant instead of the same literal in two places
# (hash and row) — the same danger of divergence that the payload further down
# is forced into a single place against.
_KIND = "observation"

# Backing off between the attempts (§4.2 of the 1a spec, review finding W3):
# eight attempts cost, in the worst case (seven waits between eight attempts,
# every one of them at the cap), markedly less than a second — noticeable
# enough to bring two concurrent writers out of lockstep, too small to slow
# the test suite down.
BACKOFF_BASIS = 0.005
BACKOFF_CAP = 0.2

# `random.SystemRandom` instead of the module functions (`random.uniform` &
# co.): not because jitter needed cryptography, but because ruff's rule S311
# ("unsuitable random number generator") is satisfied that way without any
# lint exemption — and a `Random` object of its own with a state of its own
# instead of the shared module state is the cleaner tool for this purpose
# anyway.
_random = random.SystemRandom()


def backoff_delay(attempt: int) -> float:
    """The wait, in seconds, before the next attempt.

    Full jitter: a uniformly distributed random number out of
    `[0, basis * 2**attempt]`, capped at `BACKOFF_CAP` — not a fixed interval
    and not "half the wait plus jitter". With a fixed wait, two concurrent
    writers would stay in lockstep, only slower; precisely the behaviour that
    backing off was invented against.

    Public, not private: the retry policy is documented behaviour, not an
    implementation detail — `MAX_RETRIES` and `MAX_BATCH` have long stood
    publicly beside it in this very module. A test that reaches for a private
    name has to justify a `reportPrivateUsage` suppression; what deserves a
    direct test deserves a public name instead.
    """
    upper_bound = min(BACKOFF_BASIS * 2**attempt, BACKOFF_CAP)
    return _random.uniform(0, upper_bound)


# `unit.start_ms`/`unit.end_ms` are `sqlalchemy.Integer` (see
# `storage/schema.py` and `migrations/versions/0001_log.py`) — on PostgreSQL
# the 4-byte column `integer`. Measured against a real PostgreSQL 17
# container, not taken over from memory (review finding G1 of the first final
# review): an `INSERT` of `2**31-1` and of `-(2**31)` succeeds, one of `2**31`
# and of `-(2**31)-1` fails with
# `psycopg.errors.NumericValueOutOfRange: integer out of range`.
_UNIT_INT_MIN = -(2**31)
_UNIT_INT_MAX = 2**31 - 1


def _is_text(value: object) -> bool:
    """A boundary check at the type boundary (review finding G1, first final
    review).

    `RawUnit.content` is statically declared as `str` — an `isinstance` test
    against it would be a dead check, which pyright (`strict`) rejects as
    `reportUnnecessaryIsInstance`, because from the type checker's point of
    view it can never fail. But a connector from stage 2 on builds `RawUnit`
    without a runtime check by the type checker — the `object` parameter keeps
    this check honest instead of pretending to pyright that there is nothing
    to check here.
    """
    return isinstance(value, str)


def _check_identity(field: str, value: object) -> None:
    """Checks `source` and `external_id` before they leave `core` (finding W-1).

    Both go into the event hash as JSON strings, so §3.2's canonicalisation is
    what decides about them — but it decides **too late**: `event_hash` is
    computed only after `storage.lookup`, and `lookup` is the first thing that
    carries these two values out of `core` and into the driver.

    Measured against a real PostgreSQL 17 before this check existed. Counted
    on stderr of the real command (`uv run previously append …`), which is
    what a user sees — in-process through `main()` it is one line fewer,
    because the console-script frame is missing:

        lone surrogate in --source       96 lines of traceback,
                                         UnicodeEncodeError out of psycopg
        lone surrogate in --external-id  96 lines, the same

    A lone surrogate really does arrive this way: `argv` carries bytes, and
    Python decodes undecodable ones with `surrogateescape`, so any argument
    that is not valid UTF-8 becomes a string with surrogates in it.

    The **null byte** cannot come from a command line at all — measured,
    `os.execv` and `subprocess.run` refuse an argument containing one with
    `ValueError: embedded null byte`. It is reachable through a direct
    `main()` call and, from stage 2 on, through a connector, and it was
    measured that way: 89 lines, `sqlalchemy.exc.DataError`. It is checked
    here for that path, not for the command line.

    In every case a foreign exception left a layer that is not supposed to
    know it, with the interpreter's exit code 1 instead of this command line's
    2 — the same class as review finding W2 of the first final review.

    The two content conditions are exactly the ones `canonical` applies to
    every string, because that is what these values are measured against
    later. The type check is the same boundary check as in `_check_units`:
    `RawEvent.source` is statically a `str`, but a connector from stage 2 on
    builds `RawEvent` without a runtime check by the type checker.

    `isinstance` directly, and not `_is_text` as in `_check_units`: the
    parameter here is already `object`, so the test is not a dead one that
    pyright would reject as `reportUnnecessaryIsInstance` — and it narrows the
    type for the two checks below, which a helper returning `bool` would not.
    """
    if not isinstance(value, str):
        raise InvalidPayload(f"{field}: value is not a string, but {type(value).__name__}")
    if "\x00" in value:
        raise InvalidPayload(f"{field} contains a null byte — PostgreSQL text cannot store it")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InvalidPayload(
            f"{field}: not representable as UTF-8 ({error.reason}) — "
            "a lone UTF-16 surrogate, for instance"
        ) from error


def _check_units(units: Sequence[RawUnit]) -> None:
    """Check the units before hashing them, not only in the database (G1).

    `split_plaintext` builds only valid units in stage 1a; from stage 2 on
    every connector brings its own along, unchecked. Without this check they
    produce a raw sqlalchemy error **out of `core`** — `unit_seq_check`, the
    primary key constraint on `(event_id, seq)` or PostgreSQL's `integer`
    overflow —, instead of a message that says which unit and what. Empty
    content is deliberately **not** checked: `split_plaintext` discards empty
    sections already, and an empty unit out of another medium is not an error
    this stage knows about.
    """
    seen_seqs: set[int] = set()
    for unit in units:
        if not _is_text(unit.content):
            raise InvalidPayload(f"unit {unit.seq}: content is not a string")
        if unit.seq < 1:
            raise InvalidPayload(f"unit {unit.seq}: seq must be >= 1, is {unit.seq}")
        if unit.seq in seen_seqs:
            raise InvalidPayload(f"unit {unit.seq}: seq is not unique within the event")
        seen_seqs.add(unit.seq)
        if "\x00" in unit.content:
            raise InvalidPayload(f"unit {unit.seq} contains a null byte")
        for field, value in (("start_ms", unit.start_ms), ("end_ms", unit.end_ms)):
            if value is not None and not (_UNIT_INT_MIN <= value <= _UNIT_INT_MAX):
                raise InvalidPayload(
                    f"unit {unit.seq}: {field}={value} lies outside the "
                    f"32-bit integer range [{_UNIT_INT_MIN}, {_UNIT_INT_MAX}]"
                )
        if unit.start_ms is not None and unit.end_ms is not None and unit.start_ms > unit.end_ms:
            raise InvalidPayload(
                f"unit {unit.seq}: start_ms ({unit.start_ms}) lies after end_ms ({unit.end_ms})"
            )


def _prepare(
    events: Sequence[RawEvent],
) -> list[tuple[RawEvent, Mapping[str, object], bytes, bytes]]:
    """Checks every event and computes what stays invariant across retries.

    A function of its own since finding N-5 added one more branch and `append`
    thereby measured a cyclomatic complexity of 11 against a threshold of 10
    (`C901`, this project's ruff selection) — a real gate violation, and the
    cause is removable rather than suppressible: `append` was doing two things
    at once, preparing a batch and walking the retry loop. The split changes
    no behaviour, only the structure, exactly as it did for `cli.main` before.

    Everything here runs **once**, before the first attempt. That is not a
    saving but a requirement for two of the three results: were the kind of
    evidence mixed in at two places (once for the hash, once for the row),
    the two could drift apart — and then one would hash something other than
    what one stores. The chain check of §3.4 computes
    `payload_hash(row.payload)` against `row.payload_hash` and would uncover
    that, but only there. The units digest is invariant for the same reason:
    the units of an event never change between two attempts.
    """
    prepared: list[tuple[RawEvent, Mapping[str, object], bytes, bytes]] = []
    # The idempotency keys already seen in **this** batch, with the index they
    # first appeared at — see the refusal below (finding N-5).
    seen_keys: dict[tuple[str, str], int] = {}
    for index, event in enumerate(events):
        iso_utc(event.occurred_at)
        # Before `_check_units` and, above all, before the retry loop: these
        # two are the first values that leave `core` (through `lookup`), so
        # they have to be checked before anything of this event touches the
        # driver (finding W-1).
        _check_identity("source", event.source)
        _check_identity("external_id", event.external_id)

        # The same (source, external_id) twice **within one batch** is refused
        # (finding N-5). Measured against the version before this check:
        #
        #     append([first, second])  ->  [1, 1]
        #     event rows:  [(1, {'note': 'the first', ...})]
        #     unit rows:   [(1, 1, 'First content.')]
        #     verify():    []
        #
        # The second entry's payload and units were **not stored**, no
        # exception, no finding, no warning — and the caller got two
        # identifiers back as though both had been recorded. In an append-only
        # store that is irretrievable.
        #
        # The distinction that makes this a refusal and not a widening:
        # idempotency **between** calls is the wanted property — the same
        # submission twice yields the same event, and the loop body below
        # relies on it. Idempotency **within** a batch nobody asked for, and
        # it is indistinguishable from a caller's mistake. Are the two entries
        # equal, the refusal costs nothing, because the caller can
        # deduplicate. Are they different, the caller has a bug — and silently
        # taking the first is the worst possible answer, because it does not
        # come to notice.
        key = (event.source, event.external_id)
        first_index = seen_keys.get(key)
        if first_index is not None:
            raise InvalidPayload(
                f"({event.source!r}, {event.external_id!r}) appears twice in the batch, "
                f"at index {first_index} and index {index} — idempotency holds between "
                "calls, not inside one batch, and only the first entry would be "
                "written. Deduplicate the batch."
            )
        seen_keys[key] = index

        _check_units(event.units)
        if "evidence" in event.payload:
            # The kind of evidence (§5.1) separates proof from report and
            # cannot be supplied after the fact in an append-only store once
            # it has been written. The key is therefore reserved, so that a
            # payload which already carries it is not silently overwritten.
            raise InvalidPayload(
                "payload already carries the key 'evidence' — it is reserved for the "
                "kind of evidence (§5.1), so that it is not silently overwritten"
            )
        payload: Mapping[str, object] = {
            **event.payload,
            "evidence": event.evidence.value,
        }
        prepared.append((event, payload, payload_hash(payload), units_hash(event.units)))

    return prepared


def append(
    storage: PostgresStorage,
    events: Sequence[RawEvent],
    *,
    recorded_at: datetime,
) -> list[int]:
    """Appends events as a sub-chain and yields their identifiers.

    `recorded_at` is **input, not product**: it goes into the hash and has to
    stay stable across retries, or else the hash is not reproducible.
    """
    if len(events) > MAX_BATCH:
        raise BatchTooLarge(
            f"{len(events)} events in one transaction, {MAX_BATCH} are allowed — "
            "larger batches starve against small submissions"
        )
    iso_utc(recorded_at)  # fail early if naive
    prepared = _prepare(events)

    for attempt in range(MAX_RETRIES):
        try:
            with storage.begin() as conn:
                ids: list[int] = []
                tip = storage.tip(conn)
                next_id = 1 if tip is None else tip.id + 1
                prev = None if tip is None else tip.hash

                for event, payload, payload_digest, units_digest in prepared:
                    existing = storage.lookup(conn, event.source, event.external_id)
                    if existing is not None:
                        ids.append(existing)
                        continue

                    this_hash = event_hash(
                        event_id=next_id,
                        kind=_KIND,
                        recorded_at=recorded_at,
                        occurred_at=event.occurred_at,
                        prev_hash=prev,
                        payload_digest=payload_digest,
                        units_digest=units_digest,
                        source=event.source,
                        external_id=event.external_id,
                    )
                    storage.insert_event(
                        conn,
                        EventRow(
                            id=next_id,
                            kind=_KIND,
                            recorded_at=recorded_at,
                            occurred_at=event.occurred_at,
                            prev_hash=prev,
                            hash=this_hash,
                            payload_hash=payload_digest,
                            units_hash=units_digest,
                            payload=payload,
                        ),
                        [
                            UnitRow(
                                event_id=next_id,
                                seq=u.seq,
                                content=u.content,
                                start_ms=u.start_ms,
                                end_ms=u.end_ms,
                                speaker=u.speaker,
                            )
                            for u in event.units
                        ],
                        (event.source, event.external_id),
                    )
                    ids.append(next_id)
                    prev = this_hash
                    next_id += 1
                return ids

        except SourceKeyTaken:  # pragma: no cover
            # Structurally unreachable out of `append` itself (review finding
            # W1, task 7, fix round 2), hence without test coverage — but not
            # removable: `insert_event` can raise this error, and a future
            # caller (a connector with a different insertion order, say) could
            # reach it.
            #
            # For `SourceKeyTaken` to arrive here, our event INSERT would have
            # to go through and only `source_key` fail. But a competitor who
            # already holds our (source, external_id) has inevitably committed
            # its event on an `id` out of our range, because `id` is derived
            # from the tip (above: `tip.id + 1`). Did it commit BEFORE our
            # `lookup`, then `lookup` finds it (READ COMMITTED, a new snapshot
            # per statement) and we skip it up in the loop body. Did it commit
            # AFTERWARDS, then our event INSERT fails first, because
            # `insert_event` inserts in the order event → unit → source_key —
            # never the other way round. In both cases never `source_key`.
            #
            # That holds only as long as **four** preconditions hold: `id` is
            # derived from the tip, `insert_event` inserts event before
            # source_key, the isolation level is READ COMMITTED, and no
            # `source_key` row ever arises for an **already committed** event.
            # Should one of them change, this comment is the signpost, not the
            # surprise.
            #
            # The fourth one was missing until finding N-1, and it is the one
            # somebody actually walked: the reviewer reached this branch by
            # writing an event **without** a source attribution
            # (`insert_event(..., key=None)`, which §5 permits) and then
            # hanging a `source_key` row onto that already committed event by
            # raw SQL. `append` itself never does either of those two things,
            # so the `pragma` stays right as it is worded ("out of `append`
            # itself") — but an unreachability argument that leaves out a path
            # somebody has taken is not an argument.
            #
            # Idempotency struck in the race. Two cases, and §4.2 was wrong
            # about the second one until finding G-7 of the second final
            # review — it said "no retry" without qualification:
            #
            # - **all** keys of the batch are taken: there is nothing to
            #   append, so return the existing identifiers and do **not**
            #   retry. Retrying would be exactly the loop-spinning §4.2 warns
            #   about.
            # - only **part** of them: the rest genuinely does not exist yet,
            #   and the transaction is rolled back, so it is written nowhere.
            #   `append` has to return exactly one `int` per event (§7), so
            #   without a retry the only options left would be a shorter list,
            #   a `None` mixed in, or an invented `id` — the first two break
            #   the signature, the third breaks the chain. The retry resolves
            #   it completely: on the next attempt `lookup` finds the foreign
            #   key (the competitor has committed) and skips it, and the
            #   really new event gets appended. `MAX_RETRIES` bounds the loop.
            #
            # **No backing off here, deliberately**, unlike the
            # `ChainPositionTaken` branch below (review finding W3 of the
            # first final review). And the reason is not observation but the
            # isolation level: under READ COMMITTED a `source_key_pkey`
            # violation can only arise **after** the competitor has
            # committed — before that, the duplicate INSERT **blocks** on the
            # competitor's uncommitted row instead of failing. So there
            # *cannot* be a partner in lockstep here, and the retry has
            # nothing to get out of step with. (Argument contributed by the
            # review of fix round 1, which measured this branch with a probe:
            # `SourceKeyTaken(source_key_pkey)`, 0 backoffs, 3 transactions,
            # exactly one `int` per event.)
            #
            # Should the retry collide with a *third* writer, it collides on
            # the chain position — and that is the branch that does back off.
            with storage.begin() as conn:
                reread = [storage.lookup(conn, e.source, e.external_id) for e in events]
            if all(i is not None for i in reread):
                return [i for i in reread if i is not None]
            continue
        except ChainPositionTaken:
            # Back off before the next attempt (review finding W3 of the
            # first final review) — not
            # before the first: that one is undertaken above without a wait,
            # only a failed attempt triggers a wait before the next one.
            time.sleep(backoff_delay(attempt))
            continue  # re-read the tip, try again

    raise ChainConflict(
        f"chain position not acquired after {MAX_RETRIES} attempts — "
        "under lasting contention the answer would be a single appending "
        "process, not a lock"
    )
