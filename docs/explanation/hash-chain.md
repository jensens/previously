(hash-chain)=

# About the hash chain

Previously computes three SHA-256 digests for every event: one over the payload, one over the units, and one over the event's own fields.
That third digest names the predecessor's hash, and the naming is the chain.
Version 2 of the hash format, which every new event is written in, adds one digest per unit, and {ref}`hash-version-2` says why.
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

The detour exists for one purpose: erasure.
An append-only store and a right to erasure don't get along on their own, and the mechanism that reconciles them arrived only in stage 1c, long after the chain's format was fixed; {ref}`erasure` describes it.
But a chain that hashes the payload inline would break on every erasure, over all old data at once, and no later change could repair that.
Through `payload_hash` the chain survives it: an erasure replaces `payload` with a tombstone and keeps `payload_hash` standing.
The check runs through unchanged, and it stays provable *what* stood there without holding it any more.
The cost today is one column.
The cost of adding it afterward would be the whole chain.

The same seam stays open for the units.
Stage 1a kept `unit.content` `NOT NULL`, because skip logic for a behavior that didn't exist would have been dead code.
Stage 1c opened the seam with the migration that brought version 2: `unit.content` accepts `NULL` now, and that change broke nothing, because no existing row and no existing hash changed.
In version 1 of the hash format that seam opens only for all units of an event at once, because one digest covers all their texts; {ref}`hash-version-2` explains why version 2 gives every unit a digest of its own.

The seam had a price, and for two stages the log paid it.
**A tombstone was indistinguishable from a forgery.**
`UPDATE event SET payload = NULL` left the check satisfied, measured as `verify() -> []`, and that result was the behavior the acceptance condition for stage 1a demanded.
The check couldn't do better: it saw that `payload` was missing, and whether a warranted erasure or a quiet deletion had taken it stood nowhere.
Stages 1a and 1b had no erasure at all, so every `NULL` in `payload` was a forgery, and the check reported none of them.

Stage 1c paid the price off the way it had been announced, by making an erasure an event in the log itself.
The warrant now stands *in* the chain, hashed like everything else, and the check demands that every tombstone has a redaction that ordered it.
The same statement is a finding today, and the seam costs nothing further.
{ref}`erasure` explains the redaction event and what the check holds it to.

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
The way the seam's price was later paid off would have slipped exactly here: a tombstone without a redaction is a finding now, but this row was no tombstone *in the sense of that query*.

The fix sits in the schema and not in the check: `CHECK (payload IS NULL OR jsonb_typeof(payload) = 'object')`, listed in {ref}`database-schema` as `event_payload_object_check`.
Two things are worth saying about it.

The constraint restricts nothing the contract allows.
A payload is a JSON object; an array, a scalar and `null` were never admissible there.
So the database enforces what the specification already presupposed, and *that* is what makes `payload IS NULL` and `row.payload is None` equivalent, because JSON `null` can no longer reach the column.
The code wasn't bent toward the specification, and the specification wasn't bent toward the code.

And the finding deserves no inflation.
A forger gained nothing then from JSON `null` that plain `payload = NULL` wouldn't also have given, since both left the check satisfied.
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
Version 2 adds a digest per unit and keeps this one over the whole set, now taken over the unit digests.

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

Every wrapped digest carries a version and a domain, two digests in version 1 and all four in version 2, and {ref}`hash-format` holds every pair; the units digest of version 2 keeps the domain of version 1 on purpose, and its version tells the two apart.
The pair keeps a digest from another context out.
A units digest, in particular, must never be able to count as an event digest, which is why the units get a domain of their own rather than riding along in the event's.

The version promises something that the columns of stage 1a couldn't deliver, and the promise deserves spelling out rather than quiet repetition.
A format change, so the promise goes, becomes a version increase instead of a silent break.
But `v` stood only inside the hashed object and not in the row: the `event` table had no version column.
While every row was version 1 that was enough, because the check never had to guess.
With mixed versions the check wouldn't know which domain to recompute a given row under, and guessing—try version 2 first, then version 1—would be no check at all but an offer to the forger, who could then pick whichever version makes a row add up.

Version 2 therefore came with a per-row version: `event.hash_version`, a `smallint NOT NULL DEFAULT 1`, and the check picks the hash format row by row.
A version the check doesn't know is a finding, and the check computes that row in no version at all rather than in one it does know.
The migration that added the column worked at the moment it was needed, because every row written until then was version 1 by definition.
`DEFAULT 1` entered the right value for every old row, and not one hash got recomputed.

The contrast with the correction that widened the hash is the point.
There a retrofit was impossible, because the hashes themselves would have had to be recomputed, and recomputing the hashes means rewriting the chain, which is the one thing an append-only log must never be able to do.
A column with a default invents no statement; it writes down a statement that already holds.

Stage 1a added no such column, and that was right while nothing wrote any other version.
The column would have had exactly one possible value, and a column that distinguishes nothing is readiness cost without readiness benefit.
It arrived together with the second value.

The corrections of stage 1a, among them the widening above, went into version 1 rather than into a version 2.
That was right at the time: none of it had reached `main` yet, so version 1 was still being defined, not departed from.
Stage 1a reached `main` on 2026-10-03, and from then on version 1 is a format that a log outside this repository may hold.
Redefining it would make every such row fail the check while nothing about the row had changed, and it would turn the pinned vector of version 1 into a recomputed one.
So the next change of format became a version of its own, and the next section says why there had to be one.

(hash-version-2)=

## Version 2, with a digest per unit and a salt

Version 2 changes two things about the digests over content, and both exist for erasure.
{ref}`hash-format` lists the fields of each version 2 digest.

The first change is a digest per unit.
In version 1 the content of every unit of an event goes into one hash: `units_hash` runs over one canonical object that holds each unit together with its text.
Take the text of one unit away and that hash can't be computed any more.
The other units of the event would still be readable, and nothing would attest them.
In version 2 every unit gets a digest of its own, and the units hash runs over those digests rather than over the texts.
An erased unit keeps its digest, so the hash over the digests stays computable, and the units that remain stay attested.
The property from earlier on this page survives the change: the units hash still covers the whole set, so a deleted unit still breaks it.

The second change is a salt.
An erasure leaves the digests standing, because the chain depends on them.
But a digest over short content can be searched.
Measured on 2026-10-04 with `docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/measure_guessing.py`, on one core in plain Python: a unit made of a phone number with seven unknown digits came back from its unsalted digest after 1,234,568 candidates in 0.76 to 0.79 seconds, about 1.6 million candidates per second, over four runs.
Short content is exactly what gets erased: a name, a number, one sentence.
An erasure that leaves its content guessable from what stays behind isn't an erasure.

A salt is 32 random bytes that go into the digest, and the salt is meant to be erased together with the content.
As long as the content stands, the salt stands beside it, and the check has every part of the input.
Once both are gone, whoever tries candidates against the digest is missing 32 random bytes of what went into it as well as the content.
A salt needs no attestation of its own: it's an input of the digest, and a forged salt breaks the digest like forged content would.
The payload gets the same treatment, a salt and a domain of its own, where version 1 hashed the payload and nothing else.

Neither change can be retrofitted.
A digest without a salt stays one for good, and so does a units hash over texts.
Giving an old event a salt or a per-unit digest would mean computing its hashes again, and computing the hashes again means rewriting the chain, the one thing the log must never be able to do.
That's why version 1 stays verifiable for good instead of being converted.

Version 1 keeps a cost, and an event written in it carries that cost for as long as it exists.
Its units are attested only together, so it can only be erased as a whole.
And its digests carry no salt, so whatever content it held stays guessable from them.

`append` writes version 2, and a log can hold events of both versions side by side.
The salt protects content only once an erasure takes the salt away along with the content; until then, it's an input like any other.
The database holds every erasure to that rule: it refuses a payload set to `NULL` while its salt stays, and a unit without content that keeps its salt, its speaker or its timestamps.
{ref}`erasure` describes the erasure the format was built for.

## Counting the rows the check has seen

The check reads the chain in `id` order inside a single transaction and establishes six things; {ref}`cli-reference` gives the lines they print as.
Four belong to an event, and three of those four compare a digest against the thing it covers: the payload digest against the payload, the units digest against the units, and the event hash against the event's fields.
In version 2 the units part runs in two steps: each unit that has content against its own digest, and the units digest against the stored unit digests.
In version 1 the units digest is computed only while every unit of the event still has its text, since it runs over the texts; an event with erased units leaves it nothing to compute.
The row's `hash_version` says which format the three are computed in, and a value the check doesn't know is reported in their place.
The fourth compares one stored digest against another, `prev_hash` against the predecessor's `hash`, which makes it the link itself rather than a seal over content.
The fifth belongs to no event at all, compares a number against a number, and exists because the check doesn't oversee its own reading window.
The sixth is erasure: every tombstone against a redaction that ordered it, and every redaction against its target, matched once the pass has read the whole chain; {ref}`erasure` explains why, and what a version 1 event erased in full leaves unattested.

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
The payload digest and the units are recomputed one after the other, the payload inside a `try` block of its own, and every result is collected, so a row whose payload and whose units are both forged yields two findings rather than one.
Share one block between them and the poisoned payload leaves it before the units are compared at all: whoever can make a payload non-canonicalizable could then rewrite the units of the same row at will, one forgery covering the other.
`tests/test_verify.py` holds that separation down, and it had to, because reading the code didn't: when the payload and the units were once recomputed inside one shared `try` block, every test stayed green.

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
