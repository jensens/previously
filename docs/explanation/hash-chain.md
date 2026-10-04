(hash-chain)=

# About the hash chain

Previously computes three SHA-256 digests for every event: one over the payload, one over the units, and one over the event's own fields.
That third digest names the predecessor's hash, and the naming is the chain.
{ref}`hash-format` lists which fields go into each digest.
This page explains why those fields and not others, and where the chain's promise ends.

The promise is narrower than it first looks, and the last sentence of this page states it outright.
Everything before that sentence is the reasoning that earned it.
Each of the eleven fields in the event hash is there for a reason somebody had to learn, and three of them were learned from forgeries that a working check waved through.

(tombstone-seam)=

## The chain covers a digest, not the content

The event hash doesn't cover the payload.
It covers `payload_hash`, the payload's own digest, as a hexadecimal string.
The units take the same detour: the event hash carries `units_hash` and never a unit's text.

The diagram below shows that detour for both of them, two hops where an obvious design would have one.

```{mermaid}
:caption: Payload and units reach the event hash through their own digests.

graph LR
    payload[payload] --> payload_hash[payload_hash]
    units[units] --> units_hash[units_hash]
    payload_hash --> event_hash[event hash]
    units_hash --> event_hash
```

The detour exists for one purpose, and the purpose lies in the future: erasure.
An append-only store and a right to erasure don't get along on their own, and the mechanism for it isn't built yet.
But a chain that hashes the payload inline would break on every erasure, over all old data at once, and no later change could repair that.
Through `payload_hash` the chain survives it: an erasure replaces `payload` with a tombstone and keeps `payload_hash` standing.
The check runs through unchanged, and it stays provable *what* stood there without holding it any more.
The cost today is one column.
The cost of adding it afterward would be the whole chain.

The same seam stays open for the units, although stage 1a has no erasure of units and therefore no skip for them either.
`unit.content` is `NOT NULL` today, because skip logic for a behavior that doesn't exist is dead code.
Opening the seam later takes `ALTER COLUMN content DROP NOT NULL` and the same skip that `payload IS NULL` already gets, and it breaks nothing: no existing row and no existing hash changes.

:::{important}
The seam has a price, and whoever uses it should know the price.
**A tombstone is indistinguishable from a forgery.**
`UPDATE event SET payload = NULL` leaves the check satisfied, measured as `verify() -> []`, and that result is the behavior the acceptance condition for stage 1a demands.
The check can't do better: it sees that `payload` is missing, and whether a warranted erasure or a quiet deletion took it stands nowhere.

Stage 1a has no erasure at all.
So today *every* `NULL` in `payload` is a forgery, and the check reports none of them.
That's a gap in the bookkeeping, not a defect in the code.

The price gets paid off by making an erasure an event in the log itself.
Then the warrant stands *in* the chain, with its time, its cause and its author, hashed like everything else and as unchangeable as everything else.
The check can demand from that point on: every tombstone has an erasure event that ordered it.
A tombstone without that event becomes a finding, and the seam costs nothing further.
Until that event exists, the gap stands.
:::

## The tombstone that wasn't one

The seam has a second price, and this one was a defect.
The `psycopg` driver maps SQL `NULL` and JSON `null` both onto Python `None`.
The chain check asks `row.payload is None`; the specification prescribed `payload IS NULL`.
The two were never equivalent, and the gap between them was a permanent content deletion that left no trace.

Measured against a real PostgreSQL 17, before the correction, with row 1 erased for real and row 2 forged:

```text
 id | payload IS NULL | jsonb_typeof       What Python sees:
  1 | True            | None               id 1: None  (the real tombstone)
  2 | False           | null               id 2: None  (the forgery)

Tombstone bookkeeping `WHERE payload IS NULL` finds: [1]   <- id 2 is missing
verify() -> []
```

Row 2 was erased as far as the check could tell, and invisible to any bookkeeping that looks for tombstones at the SQL level.
The announced way of paying off the seam's price slips exactly here: a tombstone without an erasure event would become a finding, but this row is no tombstone *in the sense of that query*.

The fix sits in the schema and not in the check: `CHECK (payload IS NULL OR jsonb_typeof(payload) = 'object')`, listed in {ref}`database-schema` as `event_payload_object_check`.
Two things are worth saying about it.

The constraint restricts nothing the contract allows.
A payload is a JSON object; an array, a scalar and `null` were never admissible there.
So the database enforces what the specification already presupposed, and *that* is what makes `payload IS NULL` and `row.payload is None` equivalent, because JSON `null` can no longer reach the column.
The code wasn't bent toward the specification, and the specification wasn't bent toward the code.

And the finding deserves no inflation.
A forger gains nothing today from JSON `null` that plain `payload = NULL` wouldn't also give, since both leave the check satisfied.
The sharpness lies in the fact that a disclosed boundary and an announced remedy both failed to catch this one case.

## The identifier comes from the predecessor, not from a sequence

An event's `id` is its predecessor's `id` plus one.
There's no sequence behind it and no identity column, which also settles the question of `ALWAYS` against `BY DEFAULT`: neither, because no such column exists.

A sequence hands out numbers in the order the numbers are asked for, and that's not the order the transactions commit in.
Two writers can take 10 and 11 and commit the other way round.
The chain would then read 9 → 11 → 10 while the check walks it in `id` order, and the check would fire on a chain that nothing had touched.
That's the reason no sequence stands here.
It isn't thrift.

Deriving the `id` from the predecessor buys something beyond correctness.
Because `id` order equals chain order by construction, the check stays a sequential scan instead of a chain walk over millions of single reads.

Gaps don't arise from losing a race: whoever loses the chain position consumes no number.
A gap is therefore a finding and not normality, and the check still doesn't look for one, because a row missing *in the middle* breaks the hash linkage anyway and shows up that way.
Measured against a real PostgreSQL 17, on a chain of three events with row 2 deleted:

```text
FINDING 3: prev_hash does not match the predecessor
[exit 1]
```

The phrase "in the middle" carries the whole argument, and the end of this page says what happens without it.

(timestamps)=

## Timestamps are input, not output

The caller sets `recorded_at`.
Neither the database nor the append loop produces it.

The reason is the hash.
A `DEFAULT now()` isn't known yet at the moment of hashing, so a database default can't work at all.
A value the append loop made up for itself would be worse: the loop retries on a lost race, the timestamp would differ between two attempts, and the hash would then differ between two attempts of writing the same event.
Everything that has to stay invariant across retries gets computed once, before the first attempt, for exactly this reason.

Inside the hash the timestamp is a canonical string, and {ref}`hash-format` holds its exact shape.
PostgreSQL `timestamptz` stores microseconds, so the round trip loses nothing, and what gets hashed is that canonical string rather than whatever a language library happens to print.

Two consequences follow, and neither is comfortable.

`recorded_at` may be non-monotonic between processes.
Clock drift is admissible here, because the order of the log is the `id` and not the timestamp.
A reader who sorts a chronicle by `recorded_at` is sorting by something the chain never promised.

And a reader can't recompute an event's hash from what `previously show` prints.
Four of the eleven hashed fields can't be recovered from that output at all: `recorded_at`, `prev`, `source` and `external_id`; see {ref}`cli-reference` for what `show` does print.
Reproducing a hash by hand needs the database, not the command line.

## What the chain has to cover, and the forgeries that taught it

The specification once listed eight hash fields, and units and source attribution weren't among them.
At the same time its acceptance table promised chain integrity as **complete**, its own chapter on units called the splitting essential, and the design document counted units as part of perception.
Both couldn't be true at once, and the contradiction sat in the specification rather than in the code.

Measured against a real PostgreSQL, against the version before the correction:

```text
content of one unit rewritten   ->  verify() -> []
one of two units deleted        ->  verify() -> []
source attribution forged       ->  verify() -> []
control test, payload changed   ->  verify() -> [payload_hash does not match the payload]
```

Three permanent forgeries, three times the verdict `chain intact`, and nothing in the output to suggest otherwise.
The control test is the point of the measurement: the check worked, and the hash *range* was too narrow.
The code implemented the specification to the letter, and the specification was wrong.
The event hash wraps eleven fields today instead of eight.

The lesson generalizes past these three cases.
Whatever stands in a table and not in the hash can be forged without recourse in an append-only store, because there's no earlier version to compare the forgery against.

Three smaller decisions follow from the same reasoning.

The digest runs over the whole set of units and not over each unit on its own.
A deleted unit is the forgery that no entry-by-entry comparison finds, since whatever is gone can't be checked against itself.

The set enters the digest sorted by `seq`, and the sorting belongs to `units_hash` rather than to its caller.
The order goes into the hash, so the order has to be fixed somewhere; and if it weren't fixed in one single place, `append` would hash a connector's arbitrary order while the check hashes `seq` order, and every event would fail.

All five unit fields go in, including `start_ms`, `end_ms` and `speaker`, which are always empty in stage 1a.
They stand in the table, so they can be forged.
A transcript from stage 2 carries real values there, and without them in the hash, who said what and when would stay unattested.

`source` and `external_id` hash as `null` when an event has no idempotency key, which is the normal case for an `assertion` and an `action`: those arise inside the system and not at a source.
The rule stays determinate in both directions.
An event written *with* a key hashes the key's values, so if the `source_key` row later disappears, the check reads `null`, the hash no longer matches, and there's a finding.
An event that never had a key hashes `null` and reads `null`.

One last detail of the check belongs here, because it's the reason the seam from the first section stays usable.
The event-hash comparison uses the digests *stored* in the row, not the digests recomputed from payload and units a moment earlier.
Only that keeps two statements apart: "the content changed" is one finding, "the row changed" is another.

## What a unit is

An event's units are what later statements point at, so the splitting has to be reproducible for everyone who looks.
It's mechanical and deterministic, and it's laid down per medium.
Stage 1a knows one medium, plain text: split at one or more blank lines, strip the whitespace off each section's edges, discard the empty sections, and number from 1.
No language detection, no attribution, no classification; those are assertions and come later.

One step in that list doesn't appear in the numbered rule, and leaving it out cost this project one of its {ref}`five silent losses of data <silent-losses>`.
Line endings get normalized to `\n` first, the pair `\r\n` before the single `\r`.

Without it the splitting would fail on the most important source of all.
RFC 5322 prescribes CRLF for email, the separator pattern knows of no `\r` between the two `\n`, and a whole mail text would therefore arrive as **one** unit.
That one unit would take the attribution model with it, since a commitment that spans units 3 and 4 of a message has nothing to attach to in a message that has only unit 1.
And were the `\r` left standing inside a unit's content instead, the same text submitted with LF and with CRLF endings would produce different contents, different digests and different hashes for the same message.

## At most one source attribution per event

The hash covers the source attribution, so the attribution has to be determinate.
That's the whole reason for the unique constraint on `source_key.event_id` in {ref}`database-schema`.
Without it several `(source, external_id)` pairs could point at one event, and nothing would settle *which* pair belongs in the hash.
The constraint writes down what already holds, since `append` writes one such row per event anyway, rather than leaving the question to a future caller.

A requirement for every future connector falls out of that, and it isn't arbitrary.
**An `external_id` names the artifact, not the transport.**
For email that's the Message-ID from the header, as RFC 5322 defines it, and not the IMAP UID: the Message-ID belongs to the message, the UID belongs to the mailbox, and one mail in two mailboxes has a different UID in each and the same Message-ID in both.
In the general case it's the identifier the source gives the *artifact*, such as an issue number, a commit hash or a document identifier, and not the identifier some fetch assigns, such as a line number in an export, the position in a retrieval, or a request identifier.

With an artifact-stable `external_id`, the restriction costs nothing even in the awkward case.
The same mail arriving over IMAP and over a forwarded webhook computes the same key both times, the lookup finds the existing event, and the idempotency takes effect by itself: one event, one key.
The rule is the condition under which one key per event suffices, which is why it reads as a requirement and not as advice.

The other direction was considered and rejected.
Hashing the set of keys sorted by `(source, external_id)`, the way `units_hash` hashes the set of units, would allow several keys per event.
It isn't wrong, and it isn't needed, and it would be a format change rather than a relaxed constraint.
Whoever drops the unique constraint without reading this far appears to loosen a restriction and in fact breaks the determinacy of the hash: two keys, and the check no longer knows which one to compute.

(hash-domain)=

## Separating the domains

Both of the wrapped digests carry a version and a domain of their own, and {ref}`hash-format` holds both pairs.
The pair keeps a digest from another context out.
A units digest, in particular, must never be able to count as an event digest, which is why the units get a domain of their own rather than riding along in the event's.

The version promises something that today's columns can't deliver, and the promise deserves spelling out rather than quiet repetition.
A format change, so the promise goes, becomes a version increase instead of a silent break.
But `v` stands only inside the hashed object and not in the row: the `event` table has no version column.
While every row is version 1 that's enough, because the check never has to guess.
With mixed versions the check wouldn't know which domain to recompute a given row under, and guessing—try version 2 first, then version 1—would be no check at all but an offer to the forger, who could then pick whichever version makes a row add up.

A version 2 therefore needs a per-row version first: `ALTER TABLE event ADD COLUMN hash_version smallint NOT NULL DEFAULT 1`, after which the check picks the hash domain row by row.
And that migration still works at the moment it's needed, because every row written until then is version 1 by definition.
`DEFAULT 1` enters the right value for every old row, and not one hash gets recomputed.

The contrast with the correction that widened the hash is the point.
There a retrofit was impossible, because the hashes themselves would have had to be recomputed, and recomputing the hashes means rewriting the chain, which is the one thing an append-only log must never be able to do.
A column with a default invents no statement; it writes down a statement that already holds.

Hence no column today.
It would have exactly one possible value, and a column that distinguishes nothing is readiness cost without readiness benefit.
`HASH_VERSION` stays 1 for the same kind of reason: version 1 was never written to a production database, so version 1 is still being defined here, not departed from.

## Counting the rows the check has seen

The check reads the chain in `id` order inside a single transaction and establishes five things; {ref}`cli-reference` gives the one line each of them prints as.
Four belong to an event, and three of those four compare a digest against the thing it covers: the payload digest against the payload, the units digest against the units, and the event hash against the event's fields.
The fourth compares one stored digest against another, `prev_hash` against the predecessor's `hash`, which makes it the link itself rather than a seal over content.
The fifth belongs to no event at all, compares a number against a number, and exists because the check doesn't oversee its own reading window.

The scan begins at `id = 1`, and the read filters `id >= from_id`.
A row smuggled in below that lay outside the field of view:

```text
row with id = 0 smuggled in  ->  verify() -> []
                                 read(from_id=-5) -> [0, 1]
```

Displayed by `previously log --from=-5`, and never checked.
The fifth check closes it by counting the rows it walked against `count(*)`, taken in the same snapshot, and reporting a finding when the two disagree.

Reconciling against the total rather than pulling `from_id` down to some small number is the deliberate half of the fix.
A smaller `from_id` catches the one construction known today.
The count catches every unreachable row: a gap in the middle as well, and a construction some future change introduces.
The finding carries `event_id = 0`, because no single row exists for it to point at, and 0 is no valid chain position: the chain starts at 1.

Something learned while measuring that explains why a forger has to work for this one.
A *genesis-like* `id = 0` row with `prev_hash = NULL` can't be smuggled in at all, because `event_prev_hash_idx` with `NULLS NOT DISTINCT` admits exactly one entry without a predecessor; see {ref}`configuration-reference` for why that puts PostgreSQL 15 at the floor.
The forgery needs some other, unused `prev_hash`.
A test that reaches for `NULL` is testing the index, not the check.

Two further properties of the check come from the same instinct of not trusting its own field of view.
It reads the whole chain in one snapshot, because event, units, source attribution and the count have to see one state: read across several points in time, the report would be a statement about several states and none about the chain, and a forgery could travel between two reads and look consistent in each of them.
One transaction alone doesn't give that.
Under the `READ COMMITTED` the rest of the store runs at, every statement sees a snapshot of its own, and an append that committed between the last read and the count made the check report rows it hadn't reached: 27 of 539 runs did, measured with appends running alongside.
So the check reads in a read-only `REPEATABLE READ` transaction, which keeps the snapshot of its first statement to the end; {ref}`concurrency` explains why that leaves the appending procedure alone.
And a payload that resists canonicalization produces a finding rather than an exception.
The check used to raise there, so a single poisoned row blinded the check of the entire chain, which inverts what an integrity check is for: whoever can forge one row could have hidden every later forgery behind it.

The same blinding has a smaller form, inside one row, and the check closes that one too.
The payload digest and the units digest are recomputed in two `try` blocks of their own, and both results are collected, so a row whose payload and whose units are both forged yields two findings rather than one.
Share one block between them and the poisoned payload leaves it before the units are compared at all: whoever can make a payload non-canonicalizable could then rewrite the units of the same row at will, one forgery covering the other.
`tests/test_verify.py` holds that separation down, and it had to, because reading the code didn't: every test stayed green when the two blocks were merged back into one.

## What the chain doesn't cover

Three manipulations pass the chain, and no change to the chain check can stop them.
Delete the tip.
Append a self-hashed event.
Rewrite the chain from the beginning.
What they share is that the result is consistent with itself, and a chain can only ever check itself for consistency.

Deleting the tip is the one that looks like it should be caught, so here's the measurement, on a chain of three events with row 3 deleted:

```text
1	2026-10-03T02:26:40.862890+00:00	observation	bf8c2a93aec8
2	2026-10-03T02:26:41.153105+00:00	observation	be18cc2ae461
verify: chain intact
[exit 0]
```

A chain 1→2 with a deleted 3 is indistinguishable from a chain that only ever was 1→2.
That's the known blind spot of every hash chain without an external anchor, and not an implementation gap.
The count reconciliation doesn't help against it either: it compares the rows walked with the count in the same snapshot, and after the deletion the two numbers agree again.
This is also why the argument about gaps above held only for a row in the middle, since the last row has no successor whose `prev_hash` could break.

Of the three, appending is the one to worry about.
Deleting takes a statement away from the store; appending puts one into its mouth.
A reader who finds an event missing has a chance of noticing the absence from somewhere else, from a mail client, a calendar, a memory.
A reader who finds an event that was never recorded has nothing to notice it against, and the chain will vouch for it.
An external anchor closes two of the three up to the newest anchor, and {ref}`the next section <external-anchor>` says which two and why not the third.
Without one, the chain speaks for itself alone.

So the promise, in full:

*What the log says is unaltered.*
*That it's complete, the log can't attest by itself.*

(external-anchor)=

## The external anchor

An anchor is the tip of the chain at one moment, its `id` and its hash, written down as one line in a place the database's writer can't reach.
That place is the whole point.
An anchor kept in the database would be no anchor at all, because whoever rewrites the chain would rewrite the anchor along with it.
The line carries no timestamp and no signature, because the place it's kept in supplies the time: a commit in another repository, a mail in another person's inbox, a sheet of paper.

The hash alone would already pin the prefix.
`event_hash` takes the `id` into the hashed object, and every hash covers its predecessor's through `prev_hash`, so a hash that matches at one position vouches for every event up to it.
What the `id` adds beside the hash is length.
It says how long the log was at least, and it tells the check which row the hash belongs to, which is exactly what comparing the tip with an anchor needs.

An anchor pins a prefix, not the tip.
Truncating the log below the anchor shows, because the anchored row is gone.
Rewriting the chain up to the anchor shows, because the anchored row now carries a different hash, however consistent the new chain is in itself.
An event appended after the anchor looks like growth, which is what a log is for, and the next anchor taken would pin the forgery together with everything legitimate.

That leaves two ways to check against anchors.
The first, *contains*, asks whether every anchored event still exists and carries the anchored hash.
The second, *exact*, asks that as well, and in addition that the tip is the newest anchor, so that nothing came after it.
Against the four forgeries, they compare like this:

| Forgery | contains | exact |
|---|---|---|
| tip deleted, below the newest anchor | seen | seen |
| chain rewritten up to an anchor | seen | seen |
| tip deleted, above the newest anchor | not seen | not seen |
| event appended | not seen | seen, while nothing legitimate was added since |

The last row is why exact is no mode for a running log.
Once a legitimate event arrives after the anchor, exact reports that one too, and it can't tell growth from forgery any better than contains can.
Exact belongs to a moment of rest, when nothing should have been written since the anchor was taken.

The interval between anchors is the gap.
Whatever arrived since the newest anchor isn't anchored, and an event that arrived and was deleted again in that interval leaves no trace in either check.
How often anchors get taken decides how wide that gap is, and no check can narrow it after the fact.

A restore to an earlier point looks, to the anchors, exactly like a deleted tip, because it's one: the log ends earlier than it once did.
So every anchor taken after that point reports its event missing, and the report is true.
An anchor file describes one history, and after such a restore the history it describes has ended at an earlier line.
The anchors up to that line still describe the restored log, and the ones after it now record what the restore gave up.

So the promise, with an anchor, in full:

*What the log says is unaltered.*
*What it said up to the newest anchor is complete.*
*That nothing was forged onto it since is attested only by comparing the tip with an anchor taken at rest.*

What stays open is forged appending outside that moment of rest.
Only a signature of the writer on every event would close it, so that an appended event could be told from a legitimate one by itself, and Previously has no such signature.

The measurement from the previous section, three events with the tip deleted and the verdict `chain intact`, is a finding now.
`tests/test_verify.py` holds both halves in one test.
Without an anchor, the check of the remaining chain still finds nothing.
Against the anchor taken before the deletion, it reports event 3 with `anchored event is missing (the log ends at 2)`.
