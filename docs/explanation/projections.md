(projections)=

# About derived views

Stage 1b adds three tables that carry no truth of their own: `projection_state`, `p_chronicle`, and `p_source_stats`.
This page explains what that promise means in practice and why the two content-bearing tables look the way they do.
Three sections follow on the worker that keeps them current: how it catches up in batches, why a gap in the log can't arise and is checked for all the same, and which test makes the promise more than a claim.

## Derivable and disposable

The architecture's §4.4 (frozen design record) promises that every projection table is derivable and disposable.
Practically, that means two things have to hold at once: the table can be thrown away, and rebuilding it from the log gives back exactly the same rows.
Nothing may come to depend on a projection that a rebuild wouldn't reproduce, because that dependency would be an undocumented second copy of the truth, and the whole point of a projection is to carry none.

The consequence lands on the schema itself.
A projection carries a foreign key onto `event`, because a projection built for an event that doesn't exist must never stand.
It carries no foreign key onto another projection, because that would make one derived table depend on another derived table's current state rather than on the log—exactly the dependency the promise rules out.
{ref}`database-schema` lists the three tables with their columns; this page is where the reason for that missing foreign key belongs.

## What the two tables are for

`p_chronicle` holds one row per unit, not one row per event.
That's the difference from `log`, which reads the chain one event at a time: a chronicle row answers "what happened, line by line, and how it's known," by pulling together fields from `event`, `unit`, `source_key`, and the payload's evidence field into a single row.

`evidence` is nullable on purpose.
The kind of evidence lives in the payload, and an erased payload is `NULL`, so a `NOT NULL` column here would mean the chronicle can't show an erased event's units at all—a row from the log disappearing rather than showing up with its evidence missing.
`source` is nullable for a different reason: `source_key` enforces at most one source attribution per event, not at least one, so an event with no attribution still gets a chronicle row, just with an empty `source` and `external_id`.
From `p_source_stats` that same event is absent altogether, because there's no source it could be attributed to, and the chronicle is where it stays visible.

`p_source_stats` aggregates the same log, one row per source, and its content is plain on purpose: a count of events, a count of units, and the earliest and latest `occurred_at`.
The plainness is beside the point; what makes this aggregation worth building is its **form**.
Catching it up incrementally, rather than rebuilding it from scratch on every event, is correct only because the log is append-only.
If a row could ever disappear from the log, a minimum such as `first_seen` couldn't be caught up incrementally at all, since nothing about a stored minimum says whether the row that produced it still exists.
That's exactly the property that turns this aggregation into the test of the promise above, and not merely an example of it.

## Catching up in batches, and what an abort leaves behind

The worker reads the log from `up_to_id + 1` to the tip and writes one batch of derived rows per transaction.
One rule carries the whole design: the rows and the new `up_to_id` move in the same transaction, or neither moves.
That's the entire reason `up_to_id` is a stored number at all.
An abort halfway through leaves a partial projection that agrees with its own bookmark, and the next run continues from there instead of starting over.

A single transaction over the whole log would be the opposite of that.
{ref}`concurrency` names the long transaction as a risk in the appending direction, where a transaction that stays open loses the chain position to every small submission that commits meanwhile.
A projection rebuild doesn't compete for a chain position, so it doesn't starve—but it does hold one transaction open for as long as the rebuild takes, and an abort near the end discards the whole run.
Batching turns one all-or-nothing rebuild into a sequence of resumable ones, and the stored bookmark is what makes the sequence resumable.

`batch_size` defaults to 500 because `MAX_BATCH` in `append` is 500, and one number is easier to keep in mind than two.
Nothing rests on the value, and the abort test sets it to 2 so that a failure lands in the middle of the log rather than at its end:

```text
ten events, two units each, batch size 2
a store wrapper that raises on the third insert_chronicle

  after the abort:  up_to_id 4, highest event_id in p_chronicle 4, 8 rows
  the next run:     6 events, up_to_id 10
```

Four events, not six: the third batch covers events 5 and 6, and its transaction rolled back whole.
The eight rows are the units of the first four events, and `up_to_id` names those same four.
Whoever reads the projection at that moment sees less than the log holds and nothing the log doesn't hold.

## Why there are no gaps to worry about

Reading from `up_to_id + 1` to the tip assumes two things about the log: that it has no holes, and that no row appears below the tip afterward.
Here both are consequences rather than hopes.
An event takes `id = predecessor.id + 1`, and the unique index on `prev_hash` admits one successor per event, so the identifiers form an unbroken run from 1 up to the tip.
{ref}`hash-chain` carries the reasoning for deriving identifiers that way instead of out of a database sequence.

A sequence is where this gets hard, and the contrast deserves stating, because most event logs are built on one.
Sequence values are handed out before a transaction commits, so the transaction holding 41 can commit after the one holding 42.
A worker that has stored 42 as its bookmark then reads from 43 and loses 41 for good, with nothing to show that a row was skipped.
Stage 1b is the first place where the absence of a sequence pays for itself outside the chain check.

The gap can't arise, and the worker checks for one anyway, because a check that can't fire is a comment rather than a check.
The first version of it checked the batch read for emptiness, and measured, that version could never fire for a gap at all: the tip is itself a row with an identifier above `up_to_id`, and the read filters on the same bound, so an empty result means a `batch_size` below one and nothing else.
With id 5 deleted by hand at `up_to_id` 4, the worker read 6 to 10, projected them and stored `up_to_id = 10`—the quiet loss {ref}`silent-losses` is about, out of the code that claimed to refuse it.
The check now compares the identifiers the batch read against the run that has to start at `up_to_id + 1`, and raises `ProjectionGap` at any difference, and a test forges the gap with plain SQL so that the check has to stay able to fire.

## The assurance, and the test that can actually fail

"Derivable and disposable" is worth as much as the test behind it, and the obvious test is the weak one.
Building a projection, dropping it and building it again shows that the derivation is deterministic.
Determinism isn't the failure that kills projections.
That failure is a wrong incremental step: a catch-up that reaches a different answer from a rebuild, because it folded the new events into the stored rows the wrong way.
Seeing it requires both paths at once.

The central test therefore walks the incremental path in full—append one event, catch up, append the next, catch up—then forces a rebuild from zero and compares the two results row by row.
Forcing the rebuild takes one of two paths, a version the table doesn't match or an emptied table with `up_to_id = 0` at an unchanged version, and the test takes the second one, so that the version trigger keeps a measurement of its own.
Rows, not a digest: a digest says that something differs, rows say which field moved.
That's the lesson of the pinned hash vector from stage 1a.

The case folded into that test is the late arrival that happened earlier.
`occurred_at` is when something happened, not when it arrived, so the third event of the test is five days older than the first:

```python
first_seen = first_seen                    # wrong: never catch up
first_seen = min(first_seen, occurred_at)  # right
```

Both lines agree after a single event.
Both still agree after ten events that arrive in the order they happened, because the first one stays the first.
They part the moment an older event arrives late, which is the ordinary case as soon as yesterday's mail is read in today.

None of this is reachable in `p_chronicle`.
Each chronicle row stands for one unit and nothing is added up, so a catch-up there can't reach a different answer from a rebuild.
That's why the second projection is an aggregation: counts and extremes are the part where the promise is at risk.

Which test fails for which mistake was measured, and the pair of tests is what covers both natural mistakes:

```text
merge with first_seen = existing.first_seen  (never catch up)
  -> test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older
     fails, alone among the pure tests
  -> test_incremental_equals_rebuilt fails as well, on its pinned first_seen
     value and not on the comparison between the two paths

merge with first_seen = addition.first_seen  (overwrite)
  -> test_merge_adds_counts_and_keeps_the_extremes fails
  -> test_source_stats_aggregates_a_batch_per_source fails
  -> the late-arrival test stays green, because the older late arrival
     happens to be the minimum
```

The second block is why the wrong example is tempting.
Overwriting looks like the natural mistake for a minimum, and it's the natural mistake for `last_seen`, where it's right in order and lowers the maximum at the first older late arrival.
For a minimum, though, overwriting shows up on the first in-order sequence and so never reaches the late arrival.
Never catching up is the version that survives every in-order sequence and parts at the first older late arrival, which is why the example above pins that one.

Neither of those two mutations reaches the comparison between the two paths, and measuring that was worth more than the measurement it confirmed.
`merge` folds a batch and also merges the fold with the stored row, so a mutation inside it moves the incremental path and the rebuild alike, and the two stay equal.
What the comparison catches is a step that goes wrong on one path only:

```text
SourceStatsProjection.write merges None instead of the stored row
  -> test_incremental_equals_rebuilt fails
  -> the property fails
  -> all nine tests in test_projection_derive.py stay green
```

That mutation is invisible to every test that runs without a database and to the pinned `first_seen` value as well, and it's the reason the comparison exists.

Three layers, then, and none of them covers another.
The pure tests in `test_projection_derive.py` pin the arithmetic where it lives, without a database.
The pinned `first_seen` value inside the central test catches that same arithmetic end to end: the never-catch-up mutation turns the central test red on that value, and not on the comparison.
The comparison and the property catch the step that goes wrong on one path only, which neither of the other two layers can see.

Beside the comparison stands a property that interleaves "append some events" and "catch up" in an order drawn at random and compares the result against one rebuild at the end.
Twenty-five examples per run, with `occurred_at` drawn at random as well and sources from a set of three, so that something is aggregated at all.

The version trigger gets the same treatment.
A projection declares its version in the code, and a catch-up that meets a different version in `projection_state` empties the table and starts over—any difference, not only a higher one, because a rolled-back release derives differently from the table it meets.
The test poisons a row in `p_source_stats`, raises the version, and finds the poison gone.
Its control sits right next to it: a catch-up at the unchanged version leaves the poison in place.
Without that control the first half would show only that the worker writes, not that the version is what set it off.
Dropping the version comparison from the worker turns both version tests red and leaves the other ten green.
