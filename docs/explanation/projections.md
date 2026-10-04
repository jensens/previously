(projections)=

# About derived views

Stage 1b adds three tables that carry no truth of their own: `projection_state`, `p_chronicle`, and `p_source_stats`.
This page explains what that promise means in practice and why the two content-bearing tables look the way they do.
The worker that keeps them current, and the test that proves the promise holds under an incremental catch-up, get their own sections once they exist.

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

`p_source_stats` aggregates the same log, one row per source, and its content is plain on purpose: a count of events, a count of units, and the earliest and latest `occurred_at`.
The plainness is beside the point; what makes this aggregation worth building is its **form**.
Catching it up incrementally, rather than rebuilding it from scratch on every event, is correct only because the log is append-only.
If a row could ever disappear from the log, a minimum such as `first_seen` couldn't be caught up incrementally at all, since nothing about a stored minimum says whether the row that produced it still exists.
That's exactly the property that turns this aggregation into the test of the promise above, and not merely an example of it.
