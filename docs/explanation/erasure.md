(erasure)=

# About erasure

An append-only log and a right to erasure pull in opposite directions.
The log promises that nothing it holds changes; erasure demands that something it holds goes away.
Previously reconciles the two by erasing content and never digests, and by recording every erasure as an event in the same chain it erases from.
This page explains what an erasure takes, what it leaves, why it's an event, and what it doesn't achieve.
{ref}`cli-reference` lists the commands, their output, and the findings `verify` reports about erasure.

## What an erasure takes and what stays

An erasure has a target, and the target is either a whole event or some units of one event.

| Target | What disappears | What stays |
|---|---|---|
| An event | The payload with its salt, and with it the kind of evidence (`evidence`); the content, speaker, timestamps and salt of every unit | Every hash; `id`, `kind`, and both timestamps; the source key `(source, external_id)`; the rows of the units, as tombstones |
| Units | The content, speaker, timestamps and salt of the named units | Their `seq` and their digest; everything else about the event |

A tombstone is what an erased row turns into: the row stays, and the columns that carried content hold SQL `NULL`.
The digests stay because the chain depends on them, which {ref}`tombstone-seam` explains.
The salts go because a digest without its salt can't be tried against, which {ref}`hash-version-2` explains.
The database holds every erasure to that second rule: it refuses a payload set to `NULL` beside its salt, and a unit without content that keeps its salt, its speaker or its timestamps.
So an erasure that forgot a column fails when it's written instead of leaving half of its job undone.

## Why an erasure is an event

Before stage 1c, a tombstone and a forgery looked the same.
Setting a payload to `NULL` by hand left the chain check satisfied, measured as `verify() -> []`, because every hash still held and nothing anywhere said whether a warranted erasure or a quiet deletion had taken the payload.
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
The same statement that passed in stage 1a is a finding now:

```text
FINDING 1: payload is erased without a redaction
```

`verify` demands both directions, the order and its execution.
A tombstone that no redaction covers is a finding at the event that holds it.
A redaction whose target still carries what it erased is a finding at the redaction.
A redaction whose target doesn't exist, or doesn't stand before it in the chain, is a finding too, because a redaction can only order the erasure of something recorded before it.
The check matches tombstones and redactions only at the end of its pass, inside the same snapshot: a redaction always stands behind its target in the chain, so at the target's row it hasn't been read yet.

The kind of an event has three values, `observation`, `assertion` and `action`, and erasure doesn't add a fourth.
What kind of action an event records stands in its payload, under `action`.
`verify` holds every action to that rule and reports one without a readable form, since a redaction that can't be read covers nothing and a forged one shouldn't pass as merely odd.

## Why the payload can't be erased in part

The payload stands under one digest.
Erasing one field of it would leave a payload that no longer matches its digest, and the check couldn't tell that erasure from a forgery of the field.
Whatever has to go out of a payload—a file name, an address—takes the whole payload with it, so the target is the event.

Units are different because hash format 2 gives each unit a digest of its own.
An event written in hash format 1 has one digest over the texts of all its units, so its units can only be erased all together, with the event.
`redact units` refuses such an event and says so, and `verify` reports a version 1 event with only some of its units erased, whoever ordered it.

## Why a redaction can't be redacted

A redaction's payload is what the check measures the tombstones against.
Erase it, and every tombstone it ordered becomes a tombstone without an order, which is a finding.
A redaction that could be erased would also let anybody erase the record that an erasure happened, and that record is the whole point of making an erasure an event.
The reason a redaction carries is permanent for the same reason, and it must not contain what it erases.
The command can't check that.

## What "covered" means

An erasure doesn't order the same thing twice.
Before it writes, it locks the row of its target and reads the redactions, and whatever a redaction already covers it leaves out: an event that a redaction of the event covers, and a unit that a redaction of that unit or of its event covers.
If nothing is left, it writes no event and reports the redaction that covers the target.
It still sets the tombstones, so a second call finishes an erasure whose order stands and whose execution doesn't.

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
Whatever an erasure took stands in every backup of the database and in the write-ahead log archive until their retention runs out.
The promise of an erasure is therefore as long as that retention, and whoever promises erasure within a deadline chooses the retention by it.

**Restoring brings it back.**
Whoever restores to a point before an erasure has the content again and the redaction no longer.
Nothing reports that for a payload or a unit, because the restored state is consistent with itself.
The erasures since that point have to be repeated, and the log can't say which ones they were, since its record of them is what the restore took away.

**The hashes stay.**
With the salt gone, the content can't be guessed from its digest, and it can't even be confirmed.
That holds for hash format 2 only: an event written in hash format 1 carries no salt, and its digests stay searchable for content short enough to try, which {ref}`hash-version-2` measures.

**The source key stays.**
`source` and `external_id` go into the event hash and have no digest of their own to stand in for them.
A message identifier carries a domain, and whoever can't let that stand can't erase it without breaking the chain.

**What was derived or copied stays where it went.**
Output printed in a terminal, a copy in another system, anything outside the log is beyond the reach of any erasure.
Inside it, the chronicle is a projection of the log, and it doesn't follow an erasure yet: the rows it built before the erasure stay until the projection is rebuilt, which {ref}`rebuild-a-projection` shows.

The anchors, by contrast, keep holding: an erasure changes no event hash, so an anchor taken before an erasure holds after it, and an anchor taken after it holds exactly.
