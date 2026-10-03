(silent-losses)=

# About the five silent losses of data

Building stage 1a turned up five ways in which this store would have lost data without saying so.
Three other pages refer to them in passing, so this page names them.
They're collected rather than scattered because the list is more instructive than any single entry on it, and because the thing they have in common is the one lesson of this project that transfers to the next.

Each is described here in a few sentences, with a pointer to the page that carries the full argument.
None of them is a defect that stayed in the code.

## The reserved key that would have been overwritten

`append` mixes one field of its own into every payload, under the key `evidence`, which records whether a statement is a verbatim wording or a recollection.
A payload that already used that key for something else would have had its value overwritten without a word, and in an append-only store the caller's value would have been gone for good—as would the distinction the field exists to carry, since nobody can supply the kind of evidence after the event is hashed and chained.
It's the cheapest of the five to prevent, and `append` now refuses such a payload with the key named, before anything is written; {ref}`canonicalization` has the reasoning.

## The mail that would have arrived as one unit

An event's content gets split into units at blank lines, and the units are what later statements point at.
The splitting rule said nothing about line endings, and RFC 5322 prescribes CRLF for email: the separator pattern knows of no `\r` between the two `\n`, so an entire mail would have arrived as **one** unit.
That one unit would have taken the attribution model with it, because a commitment spanning units 3 and 4 of a message has nothing to attach to in a message that has only unit 1—and had the `\r` been left standing inside the content instead, the same text submitted with LF and with CRLF endings would have produced different digests for the same message.
{ref}`hash-chain` describes the normalization that closes it.

## The three forgeries the chain waved through

The specification listed eight hash fields, and neither the units nor the source attribution was among them, while the same document promised chain integrity as complete.
Measured against a real PostgreSQL, with the version before the correction, three permanent forgeries passed as `chain intact`: the content of a unit rewritten, one of two units deleted, and the source attribution replaced.
A control test with a changed payload produced the expected finding, which is what made the measurement conclusive—the check worked, and the hash range was too narrow.
The event hash wraps eleven fields today instead of eight, and {ref}`hash-chain` carries the argument that generalizes past those three cases.

## The tombstone that no tombstone query found

SQL `NULL` in the payload column marks a tombstone after an erasure, and the chain check skips such a row's payload on purpose.
The driver maps SQL `NULL` and JSON `null` both onto Python `None`, so a row holding JSON `null` was taken for a tombstone by the check—while `SELECT id FROM event WHERE payload IS NULL` didn't list it.
Content erased as far as the check could tell, and invisible to any bookkeeping that asks the database rather than Python, which also meant that the announced remedy for tombstones would have skipped it: the row is no tombstone *in the sense of that query*.
A check constraint in the schema closes it, and {ref}`tombstone-seam` explains why that constraint restricts nothing the contract ever allowed.

## The batch entry that vanished

`append` takes a batch, and a batch carrying the same `(source, external_id)` in two entries used to write the first and drop the second without a word:

```text
append([first, second])  ->  [1, 1]

event rows:      [(1, {'note': 'the first', 'evidence': 'verbatim'})]
unit rows:       [(1, 1, 'First content.')]
source_key rows: [('email', 'message-1', 1)]
verify():        []

payload of the second entry   ->  NOT stored
units of the second entry     ->  NOT stored
```

No exception, no finding, no warning, and the caller received two identifiers back as though both entries had been recorded.
The case was refused once it was understood, with both batch positions named, and {ref}`canonicalization` sets out why refusing beats tolerating here although idempotency is a wanted property everywhere else in this system.

## What the five have in common

**Not one of them was a programming error.**
One of the five came of a specification that said something false—the hash range—and there the code was wrong with it to the letter.
Three came of a specification that said nothing at all: nothing about the line endings, nothing about the key collision, nothing about the duplicate inside a batch, and so the gap had no owner.
The fifth, the tombstone, is a kind of its own, and it's the one that looks most like a programming error: the specification prescribed `payload IS NULL`, the code asked `row.payload is None`, and the specification itself records that the two were never equivalent.
They weren't equivalent because the instruction was realizable in Python only under a precondition—a payload is a JSON object—that the specification presupposed and nothing enforced.
So the correction went into the precondition and not into the check, which is why `event_payload_object_check` sits in the schema today.
Reviewing the implementation against the plan would have found none of the five, because at the level a review reads, the implementation agreed with the plan.

Each was a gap between a promise and the world, and there are five of those too.
A payload promised to be the caller's own and had one of its keys claimed by the store without a word.
A rule promised a reproducible splitting and left the most common line ending undecided.
A chain promised integrity and covered eight of the eleven hashed fields—and the three it left out are exactly where the three forgeries landed.
A column promised a tombstone and accepted a value that looked like one to Python and not to SQL.
An interface promised one identifier per event and gave two for one stored event.

And every one of them was found by **measuring**, not by reading.
Against a real database, with the version before the correction, and with a control test beside the finding so that a green result couldn't be mistaken for a working check.
That pattern is why the pages in this quadrant quote their measurements rather than summarizing them: a summary of a measurement is an assertion again, and assertions are what produced all five.

The last thing they share is why the count matters at all.
This is an append-only store.
There's no earlier version to compare against, no `UPDATE` to put right what was lost, and no way to tell a reader later that an event's payload was once something else.
Every one of the five would have been **irretrievable**, and none of the five would have announced itself.
