(erasure)=

# About erasure

An append-only log and a right to erasure pull in opposite directions.
The log promises that nothing it holds changes; erasure demands that something it holds goes away.
Previously reconciles the two by erasing content and never digests, and by recording every erasure as an event in the same chain it erases from.
This page explains what an erasure takes, what it leaves, why it's an event, and what it doesn't achieve.
{ref}`cli-reference` lists the commands, their output, and the findings `verify` reports about erasure.

## What an erasure takes and what stays

An erasure has a target, and the target is a whole event, some units of one event, or a blob.

| Target | What disappears | What stays |
|---|---|---|
| An event | The payload with its salt, and with it the kind of evidence (`evidence`) and the file names of its attachments; the content, speaker, timestamps and salt of every unit; every blob to which no reference that isn't erased points afterward | Every hash; `id`, `kind`, and both timestamps; the source key `(source, external_id)`; the rows of the units, as tombstones—attested in hash format 2, and in hash format 1 by nothing, as the section on erasing in part explains; the rows of the blob register |
| Units | The content, speaker, timestamps and salt of the named units | Their `seq` and their digest; everything else about the event |
| A blob | The object in the blob store, for every event that uses the blob at that moment | The references in the payloads and the rows of the register: the hash stays as the evidence that something was there |

A tombstone is what an erased row turns into: the row stays, and the columns that carried content hold SQL `NULL`.
The digests stay because the chain depends on them, which {ref}`tombstone-seam` explains.
The salts go because a digest without its salt can't be tried against, which {ref}`hash-version-2` explains.
The database holds every erasure to that second rule: it refuses a payload set to `NULL` beside its salt, and a unit without content that keeps its salt, its speaker or its timestamps.
So an erasure that forgot a column fails when it's written instead of leaving half of its job undone.

## Why an erasure is an event

Before stage 1c, a tombstone and a forgery looked the same.
Setting a payload to `NULL` by hand left the chain check satisfied, measured in stage 1a as `verify() -> []`, because every hash still held and nothing anywhere said whether a warranted erasure or a quiet deletion had taken the payload.
{ref}`tombstone-seam` disclosed that price when the seam was opened and named the way to pay it off.

An erasure writes a redaction: an event of kind `action`, without units and without a source key, whose payload names what it erases and why.

```json
{"action": "redaction",
 "scope": "units",
 "target": {"event": 7, "units": [2, 3]},
 "reason": "a phone number of a third party"}
```

The redaction and its tombstones are written in one transaction, so neither exists without the other.
Because the redaction is an event, its warrant stands in the chain, with its time and its reason, hashed like everything else and as unchangeable as everything else.
And because it stands in the chain, the check can hold every tombstone against it.
The same statement that passed in stage 1a is a finding now, measured on 2026-10-05 against the seventh event of a log, its payload and salt set to `NULL` by hand:

```text
FINDING 7: payload is erased without a redaction
```

`verify` demands both directions, the order and its execution.
A tombstone that no redaction covers is a finding at the event that holds it.
A redaction whose target still carries what it erased is a finding at the redaction.
A redaction whose target doesn't exist, or doesn't stand before it in the chain, is a finding too, because a redaction can only order the erasure of something recorded before it.
The check matches tombstones and redactions only at the end of its pass, inside the same snapshot: a redaction always stands behind its target in the chain, so at the target's row it hasn't been read yet.

The kind of an event has three values, `observation`, `assertion` and `action`, and erasure doesn't add a fourth.
What kind of action an event records stands in its payload, under `action`.
`verify` holds every action to that rule and reports one without a readable form, since a redaction that can't be read covers nothing and a forged one shouldn't pass as merely odd.

## When a blob has to lie in the store

A blob lies outside the database, and an erasure of the log can't take it along in its transaction.
So whether a blob still has to lie in the store follows from one rule, and both sides compute it the same way: `redact` deletes what the rule says no longer has to lie, and `verify --blobs` reports what breaks it.

A reference, an event naming a blob, is erased when the event is erased whole or a redaction of the blob names the event; a blob has to lie in the store as long as at least one of its references isn't erased.

Three consequences follow from it without a special case.
A blob shared by two events stays when one of them is erased, and `redact` names it and the event that still uses it.
When the last event that uses a blob is erased, the blob goes with it.
When the same content arrives again after a redaction of the blob, at a new event, it has to lie again, because the redaction named the events of its time and not this one.

The shared blob is the case that decides the rule.
The same attachment can hang on two mails, and erasing one mail must not damage the other: the second mail still names the blob, and its payload digest still vouches that those bytes belong to it.
Whoever wants a content gone everywhere erases the blob, and that redaction names every event that uses it at that moment.

A redaction of a blob leaves the payloads alone.
The payload stands under one digest and can't lose a reference without losing everything else, so the hash stays in the payload and in the register, as the evidence that something was there.
`show` marks such a reference as erased, and `blob get` refuses it and names the redaction.

### First the transaction, then the store

An erasure first writes its redaction and its tombstones in one transaction, then deletes from the store what the rule says no longer has to lie, and only then catches the projections up.
The order is the one in which a failure leaves something unfinished rather than something wrong.
A blob deleted before the redaction stands would be gone for an erasure that might still fail, with nothing in the log to say why.
A blob that's still there after the redaction stands is only a deletion that hasn't happened yet.

When deleting fails, the command says that the redaction is recorded and what's outstanding, and running the same command again finishes it.
That works because `redact` computes what has to go on every call, also on the one that finds its target covered and writes nothing: the second call writes no second redaction, deletes what the first didn't get to, and catches up.
Deleting a blob that's already gone is no error, so the second call can't fail on what the first one did.

Two erasures that touch the same blob could each conclude that the other's reference still stands, and then neither would delete it.
So an erasure that touches a blob locks every event that uses the blob, in ascending order, before it reads the redactions.
The second waits for the first and sees its redaction, and the one order means that neither can hold a row the other is waiting for.

## Why the payload can't be erased in part

The payload stands under one digest.
Erasing one field of it would leave a payload that no longer matches its digest, and the check couldn't tell that erasure from a forgery of the field.
Whatever has to go out of a payload—a file name, an address—takes the whole payload with it, so the target is the event.

Units are different because hash format 2 gives each unit a digest of its own.
An event written in hash format 1 has one digest over the texts of all its units, so its units can only be erased all together, with the event.
`redact units` refuses such an event and says so, and `verify` reports a version 1 event with only some of its units erased, whoever ordered it.

A unit's own digest pays off only where the payload doesn't repeat the unit.
`previously append --text` keeps the whole text in the payload as well, under `text`, so erasing units of an event it wrote leaves their wording standing in the payload; only an erasure of the event takes it.
Which events carry their text in the payload alone, in the units alone, or in both is for the contract of the connectors to settle, and until it does, erasing units reaches less than its name suggests.

Erasing all of them has a cost of its own, and version 1 carries it beside its unsalted digests.
Once every text is gone, nothing is left to recompute the units digest from, so the check computes nothing for the units of that event.
The rows stay as tombstones, but their number and their `seq` values are attested by nothing.
A tombstone row deleted, or one added with an invented `seq`, passes the check without a finding.
In hash format 2 the same forgery is a finding, because the units digest runs over the digests the tombstones keep.
`test_the_tombstone_rows_of_a_fully_erased_version_1_event_are_attested_by_nothing` pins that limit, with the version 2 case beside it as the control.

## Why a redaction can't be redacted

A redaction's payload is what the check measures the tombstones against.
Erase it, and every tombstone it ordered becomes a tombstone without an order, which is a finding.
A redaction that could be erased would also let anybody erase the record that an erasure happened, and that record is the whole point of making an erasure an event.
The reason a redaction carries is permanent for the same reason, and it must not contain what it erases.
The command can't check that.

## What "covered" means

An erasure doesn't order the same thing twice.
Before it writes, it locks the row of its target event, or for a blob the rows of the events that use it, and reads the redactions, and whatever a redaction already covers it leaves out: an event that a redaction of the event covers, and a unit that a redaction of that unit or of its event covers.
If nothing is left, it writes no event and reports the redaction that covers the target.
It still sets the tombstones and computes which blobs no longer have to lie, so a second call finishes an erasure whose order stands and whose execution doesn't.
For a blob, covered means that every reference to it has been erased already, and the redaction it reports is the newest of those that erased them.

The lock is what makes that hold under concurrency.
Two erasures of the same target run one after the other, and the second reads the redactions only once it holds the lock, so it sees the first one's.
Read before the lock, both would find nothing and both would write; {ref}`concurrency` puts the lock beside the rest of the procedure.

Covered means that a redaction exists, not that the content is missing.
A tombstone without a redaction—a payload set to `NULL` by hand, by an accident or a forgery—isn't covered.
An erasure of that event writes a redaction for it, instead of refusing because there's nothing left to erase.
Refusing would leave a finding standing that nobody could ever clear, since no other path writes a redaction.

That choice stays honest, because what it writes is visibly later than what it covers.
The redaction carries the time it was recorded, and the event it covers was erased before that, by somebody the log doesn't know.
The redaction doesn't claim to have done the erasing; it states that the erasure is warranted from now on and why, in its reason.
Whoever reads the log can see the gap between the two, and the check is quiet again only because somebody accepted the tombstone on the record.

## What an erasure doesn't do

An erasure takes content out of the log's tables, and that's less than taking it out of the world.

**Backups keep it.**
Whatever an erasure took from the log stands in every backup of the database and in the write-ahead log archive until their retention runs out.
A blob isn't in either of those: an erased blob is gone from the store and stays in every backup or replica of the bucket for as long as that copy is kept, and the identity that opens it has a backup of its own, as {ref}`blobs` asks.
The promise of an erasure is therefore as long as the longer of the two retentions, and whoever promises erasure within a deadline chooses both by it.

**Restoring brings it back.**
Whoever restores to a point before an erasure has the content again and the redaction no longer.
Nothing reports that for a payload or a unit, because the restored state is consistent with itself.
For a blob it shows, as far as the restored log names it: the store doesn't go back with the database, so `verify --blobs` reports as missing every blob that an erasure since that point deleted and that an event of the restored log names.
A blob attached after that point and erased since is named by no event of the restored log, and neither is an object uploaded after that point for a content no restored event names; nothing reports either, since `verify --blobs` checks only the blobs the register names.
The erasures since that point have to be repeated, and the log can't say which ones they were, since its record of them is what the restore took away.

**The hashes stay.**
With the salt gone, the content can't be guessed from its digest, and it can't even be confirmed.
That holds for hash format 2 only: an event written in hash format 1 carries no salt, and its digests stay searchable for content short enough to try, which {ref}`hash-version-2` measures.
The address of a blob carries no salt either, by design: it's the hash of the content, so that the same content is one object however often it arrives.
Whoever holds the file already can therefore show that it stood in the log, and an erasure of the blob takes the bytes out of the store, not that proof.

**The source key stays.**
`source` and `external_id` go into the event hash and have no digest of their own to stand in for them.
A message identifier carries a domain, and whoever can't let that stand can't erase it without breaking the chain.

**What was derived or copied stays where it went.**
Output printed in a terminal, a copy in another system, anything outside the log is beyond the reach of any erasure.
Inside it, the chronicle is a projection of the log, and it follows an erasure: `redact` catches the projections up after it, and the rows of what was erased are deleted, as {ref}`projections` explains.
If that catch-up fails, the erasure stands and the chronicle lags behind it until the same command runs again or `project` runs.

The anchors, by contrast, keep holding: an erasure changes no event hash, so an anchor taken before an erasure holds after it, and an anchor taken after it holds exactly.
