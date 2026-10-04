(concurrency)=

# About appending under concurrency

Two processes read the same chain tip, derive the same `id` and the same `prev_hash` from it, and both try to write the event that follows.
One of them has to lose, and the whole of what makes it lose is two unique indexes.
There's no advisory lock in Previously, no `SELECT … FOR UPDATE`, and no coordination between processes of any kind.
{ref}`database-schema` names the indexes; this page says why two of them are enough, what the loser does afterward, and why one of the two recoveries behaves differently from the way the specification first described it.

## The indexes are the serialization

`append` opens one transaction per call, at `READ COMMITTED`, and what it does inside that transaction asks the database to hold nothing for it.
It reads the tip once, with `SELECT id, hash FROM event ORDER BY id DESC LIMIT 1`—a backward index scan on the primary key, the cheapest query available, and both values out of one statement rather than two.
From the tip it derives `id` and `prev_hash`, computes the hashes, and inserts.
The insert either lands or it violates a unique index, and that violation is the whole answer to the race.

The sequence below is the race itself, with the loser's recovery attached.

```{mermaid}
:caption: Two writers derive the same chain position from the same tip; the loser reads it again.

sequenceDiagram
    participant A as Writer A
    participant DB as PostgreSQL
    participant B as Writer B
    A->>DB: tip
    DB-->>A: id 7, hash h7
    B->>DB: tip
    DB-->>B: id 7, hash h7
    A->>DB: INSERT event id 8, prev_hash h7
    B->>DB: INSERT event id 8, prev_hash h7
    DB-->>A: COMMIT
    DB-->>B: 23505, unique violation
    Note over B: roll back, back off, read the tip again
    B->>DB: tip
    DB-->>B: id 8, hash h8
    B->>DB: INSERT event id 9, prev_hash h8
    DB-->>B: COMMIT
```

`READ COMMITTED` is set on the engine by name instead of being left to a default, and that isn't tidiness.
The procedure works at that level precisely because the unique index does the serializing.
Under `SERIALIZABLE` the same race would come back as a serialization failure instead—also recoverable, and a different class of error, raised at a different moment and caught in a different place.
Building on a default here would be a trap: whoever changed it later would change the error class of the busiest code path in the system without touching that path.

One reader runs at a different level, and on purpose.
The chain check needs every statement of its pass to see the same state, which `READ COMMITTED` doesn't give, so it reads in a read-only `REPEATABLE READ` transaction of its own; {ref}`hash-chain` says what went wrong without it.
That leaves the procedure above untouched, for two reasons PostgreSQL's documentation on transaction isolation states: a read-only transaction at `REPEATABLE READ` never has a serialization conflict, and under MVCC reading never blocks writing.
A check running alongside the busiest code path neither fails because of it nor makes it wait.

The loser rolls back, waits, reads the tip again and starts over from the top.
The wait is full jitter, a uniformly distributed random number out of `[0, 0.005 * 2**attempt]` seconds, capped at `0.2`.
Not a fixed interval, and not half the wait plus jitter: with a fixed wait two concurrent writers stay in lockstep, only slower, which is the behavior backing off exists against.
Eight attempts is the limit, and the bounds double until they reach the cap: `0.005`, `0.01`, `0.02`, `0.04`, `0.08`, `0.16`, `0.2`, `0.2` seconds.
Eight of them and not seven, because the loop sleeps after every failed attempt, the eighth included, whose wait is spent just before giving up.
Those are bounds and not waits—`backoff_delay` draws uniformly from `[0, bound]`, so the average is half of each—and summed they put the worst case at `0.715` seconds: long enough to bring two writers out of step, short enough not to slow the test suite down.
After the eighth attempt `append` raises `ChainConflict` instead of spinning.

That a lost race costs nothing but time is a consequence of where the `id` comes from.
Whoever loses the chain position consumed no number, so a retry leaves no gap behind to explain; {ref}`hash-chain` carries that argument in full, including why a sequence would have been worse.

## The index clause that isn't optional

The index on `prev_hash` carries `NULLS NOT DISTINCT`, and the phrase looks like a detail of index tuning.
It's load-bearing.
PostgreSQL's default treats every `NULL` as distinct from every other, so a plain unique index on `prev_hash` would admit any number of rows with `prev_hash IS NULL`.
A row with no predecessor is the genesis entry, the first link of the chain—and under the default every process could write one of its own, in parallel, each the start of a chain of its own.
That's exactly the branching the index exists to prevent, so the index without the clause would guard the whole chain except its one most consequential position.

With the clause, the several `NULL` count as one value and the index admits a single entry without a predecessor.
The clause arrived in PostgreSQL 15, which is where {ref}`configuration-reference` puts the floor for this project, and the version requirement is therefore not a preference.
A side effect of the same clause shows up in {ref}`hash-chain`: a forged genesis-like row with `id = 0` and `prev_hash = NULL` can't be smuggled in at all, because the index already holds that position.

(conflict-classes)=

## Three classes of conflict, two recoveries

Every conflict arrives as PostgreSQL error `23505`, a unique violation, and treating them all alike is the point at which a retry loop turns wrong.
The specification sorts them into three classes that group into two recoveries.
A violation of `event_prev_hash_idx` means the chain position is gone.
A violation of `event_pkey` means the same chain position, recognized through a different index.
Both recover the same way: roll back, read the tip again, start over.
A violation of `source_key_pkey` means something else—idempotency struck in the race, the source event is recorded already—and the recovery there is to read `lookup` again for the whole batch rather than to retry.
Whoever treats the third like the first two either duplicates events or spins the loop.

The code names a fourth constraint in the first group, and following why is worth the paragraph, because the first version of this decision had it backwards.
`event_hash_idx` was left out of the chain-position group on the reasoning that a duplicate `hash` means the same event was built twice, which would be a deterministic mistake rather than a race.
Recomputed, that's false.
Both `id` and `prev_hash` go into the event hash, so two writers can arrive at the same `hash` only if they arrived at the same `id` and the same `prev_hash` out of the same tip—which is to say, at the same chain position.
A duplicate `hash` is therefore the same incident as a duplicate `id`, and `_CHAIN_POSITION_CONSTRAINTS` in `storage/postgres.py` holds all three names.

Which of the three fires first is nobody's decision.
PostgreSQL checks the indexes in the physical order of their `oid` values, so the constraint name that comes back depends on how the indexes happen to be laid out, not on what went wrong.
Measured against a real PostgreSQL 17:

```text
INSERT with a fresh id and the tip's hash
  ->  ChainPositionTaken('event_hash_idx')

INSERT with the tip's id and the tip's hash and a foreign prev_hash
  (event_pkey and event_hash_idx violated at once, event_prev_hash_idx not)
  ->  ChainPositionTaken
```

The second measurement is the one that settles the design, and it's also why the test behind it asserts the *type* of the error and not the constraint name.
Both names have to lead to the same outcome, so a test that pinned one of them would pin the index layout along with it.

Translating all three into one error is what keeps the appending procedure independent of that layout.
`REINDEX CONCURRENTLY` builds a replacement index and gives it a fresh OID; `pg_repack` and any future migration can reorder them just as well.
Had `event_hash_idx` stayed untranslated, the first maintenance operation that reordered those values would have turned an ordinary lost race into an untranslated `IntegrityError`—a SQLAlchemy exception travelling out of `core`, past an `append` that catches only the two translated errors, to a caller with no business knowing that SQLAlchemy exists.
Not one line of the appending code would have changed in between.
The failure would have looked like a database problem and would have been a layering problem.

One constraint stays untranslated on purpose.
`event_kind_check` rejects a `kind` outside the three permitted values, and that's a deterministic mistake at any degree of concurrency.
Dressed as `ChainPositionTaken` it would make the caller retry it eight times and then report a chain conflict, hiding the real error behind a plausible one, so the `IntegrityError` has to come through unchanged.
The test for it denies `StorageError` by name rather than leaning on the side effect that the storage errors don't inherit from `IntegrityError`—the side effect already caught a faulty translation, but only as an unexpected failure, never as a property somebody can read.

## The source-key branch doesn't back off, and that's not an omission

The chain-position branch waits before its next attempt; the source-key branch continues at once.
The asymmetry looks like something nobody got round to, and the argument for it comes from the isolation level rather than from an observation, so it's worth following to the end.

Under `READ COMMITTED` a `source_key_pkey` violation can arise only **after** the competitor has committed.
Before that moment the duplicate `INSERT` doesn't fail at all: it blocks on the competitor's uncommitted row and waits for the outcome.
So by the time this branch runs, the writer it lost against is finished and gone.
There *can't* be a partner in lockstep here, and backing off would have nothing to get out of step with.
Should the retry collide with a *third* writer, it collides on the chain position—and that's the branch that does back off.

Measured with a probe against this branch: `SourceKeyTaken(source_key_pkey)`, no wait at all, three transactions, and exactly one `int` per event.

The branch also carries an argument that nothing can reach it, and that argument is narrower than it reads: out of `append` itself, nothing can.
For `SourceKeyTaken` to arrive there, the event insert would have to go through and only `source_key` fail; but a competitor already holding this `(source, external_id)` has committed its event at an `id` outside the range, because `id` comes from the tip.
Did it commit before `lookup`, then `lookup` finds it—`READ COMMITTED` takes a fresh snapshot per statement—and the loop body skips it.
Did it commit afterward, then the event insert fails first, because `insert_event` writes event, then units, then `source_key`, never the other way round.

That holds as long as four conditions hold: `id` derives from the tip, `insert_event` writes the event before the key, the isolation level is `READ COMMITTED`, and no `source_key` row ever appears for an already committed event.
The fourth was missing from the argument until a reviewer walked the path it leaves out—an event written *without* a source attribution, which the contract permits, and a `source_key` row hung onto that committed event by raw SQL afterward.
`append` does neither of those two things, so the claim survives as worded, which is why it says *out of `append` itself*.
But a claim of unreachable code that omits a path somebody has taken isn't a claim worth having, and the branch stays in the code for the callers that come after this stage.

## The partial hit, and the shorter list that would have been silent

The source-key recovery reads `lookup` again for every event of the batch, and then the two cases part company.
Are **all** the keys taken, there's nothing left to append: return the identifiers that came back and don't retry, because retrying would be the loop-spinning this whole section exists to prevent.
Is only **part** of them taken, the specification said the same—"no retry"—without qualification, and the code retried.
The contradiction was resolved in favor of the code, because the instruction can't be carried out in the batch case at all.

A batch can hold events whose key a competitor already owns, so `lookup` finds them, **and** events that genuinely don't exist yet, so `lookup` doesn't.
The transaction is rolled back, so the second kind is written nowhere.
And `append` owes the caller exactly one `int` per event.
Without a retry the only moves left would be to return a shorter list, to mix a `None` into it, or to invent an `id`—the first two break the signature, the third breaks the chain.
The shorter list is the dangerous one, because a caller that zips its own batch against the returned identifiers would pair every entry after the gap with the wrong `id`, and nothing anywhere would say so.
That failure belongs to the same family as the losses collected in {ref}`silent-losses`: no exception, no finding, and a result that looks like success.

Retrying resolves it completely.
On the next attempt `lookup` finds the foreign key, because the competitor has committed, and skips it; the event nobody else holds yet gets appended; and `MAX_RETRIES` bounds the loop, so it doesn't spin.
The specification's wording stays right for the case it was written for, which is the one where every key of the batch is taken.

## Batching is the remedy against contention, not its amplifier

A worker that appends a hundred events in one transaction occupies one chain position, not a hundred.
The bottleneck is the number of transactions and not the number of events, because the chain takes arbitrarily many events per transaction: the second event of a batch derives its `id` and `prev_hash` from the first rather than reading the tip again, so a batch is a sub-chain built inside a single position.
Anybody who reaches for concurrency to get throughput here has the lever the wrong way round.

The risk runs in the other direction, and it deserves naming.
A transaction that carries hundreds of events is open for a long time, and every small submission that commits meanwhile makes it lose the conflict.
It retries and loses again.
**Starvation is possible**, and no part of this design rules it out.

The treatment is plain on purpose: a bounded batch size, `MAX_BATCH = 500`, and bounded retries, `MAX_RETRIES = 8`.
Beyond that there's a statement rather than a mechanism, and it's the honest one for a system with one user and six processes.
Should contention ever hurt for real, the answer is a single appending process, not a lock.
A lock would be a second mechanism to reason about beside the indexes, and it would make every reader of this code ask which of the two actually decides the chain position.
