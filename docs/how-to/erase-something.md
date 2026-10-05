(erase-something)=

# How to erase something from the log

This guide shows you how to erase a whole event, some units of an event, or an attached file, and how to check afterward that the erasure holds.
Every erasure is recorded as an event of its own, a redaction; see {ref}`erasure` for what an erasure takes and what stays.

## Choose the target

Pick the smallest target that holds everything that has to go:

- If it stands in the payload, such as a file name, an address in a field, or the text of an event without units, erase the **event**.
  The payload can't be erased in part.
- If it stands in some units of an event, and nowhere in its payload, erase those **units**.
  `previously append --text` puts the whole text into the payload as well, so for an event it wrote, erase the event.
  Units can be erased only at events in hash format 2; for an older event, `previously redact units` refuses and names `previously redact event` instead.
- If it's an attached file that has to go wherever it's attached, erase the **blob**.

Find the event's `id`, the `seq` of each unit, and the address of each blob with `previously show`.

## Write the reason

Every form takes `--reason`, and the reason stays in the log for good, as part of the redaction.
Write why the erasure happens, such as the request it answers.
Don't write what's being erased: no name, no address, no quotation from the content.
`redact` can't check that for you.

## Keep a record of the erasure

If you promise erasure to anybody, note every erasure in a record kept outside the database: the command and its date, and for `redact event` and `redact units` the target's `id`, its `hash`, and its source key `(source, external_id)`.

- `previously show` prints the `hash` on its third line, and an erasure doesn't change it.
- `previously chronicle` prints the source key in its fourth and fifth fields, beside every unit of the event that has a row there; an erasure takes the rows of what it erased out of the chronicle, so note the source key before you erase.
  No command finds an event by its source key.

A restore to an earlier point takes the log's own record of an erasure away, and {ref}`restore-from-a-backup` repeats the erasure from yours.

## Set the blob settings

An erasure of an event with attachments, or of a blob, deletes objects from the blob store.
Set the five settings of the store for those two forms: `PREVIOUSLY_BLOB_ENDPOINT`, `PREVIOUSLY_BLOB_REGION`, `PREVIOUSLY_BLOB_BUCKET`, `PREVIOUSLY_BLOB_ACCESS_KEY` and `PREVIOUSLY_BLOB_SECRET_KEY`.
`redact` needs no recipient and no identity.
See {ref}`configuration-reference` for each of them.

The bucket must have neither versioning nor object lock: on such a bucket, deleting keeps a copy of every erased blob, and nothing in Previously checks the bucket for it.
{ref}`run-a-blob-store-on-your-machine` shows how to ask a bucket for both.

## Erase units

`redact units` erases the named units and leaves the payload of the event as it is.
Every event `previously append` writes holds its whole text in the payload as well, so for such an event the wording of the erased units stays readable there, and `redact units` says so on standard error; erase the event instead.
The example below erases a unit of such an event, and shows what stays.

Name the event and the `seq` of every unit to erase:

```console
$ previously redact units 2 2 --reason "a deadline the client asked to keep out of the record"
redacted by event 3
the payload of event 2 is not erased and may hold the same text; `previously redact event 2` erases it
```

Check the event:

```console
$ previously show 2
id=2 kind=observation
occurred_at=2026-10-05T04:51:23.128681+00:00
hash=3d4758362ff2ab2f05aa122158dd95ef0d5303cc01a4492817570403b4b3c4c4
evidence=recollection
payload={"blobs": [{"filename": "draft.txt", "media_type": "text/plain", "sha256": "b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373", "size": 35}], "evidence": "recollection", "text": "The second draft is attached.\n\nThe client wants it by Friday."}
  ¶1 The second draft is attached.
  ¶2 <erased by event 3>
  blob b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 35 text/plain draft.txt
```

The unit is erased, and the payload still holds the full text, `The client wants it by Friday.` included.

## Erase a blob

Name the blob by its address:

```console
$ previously redact blob b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 --reason "the draft is superseded and must not be kept"
redacted by event 4
```

This erases the blob for every event that names it now, and deletes it from the store.
The events keep their payloads and their units.
`previously show` marks the reference as erased:

```console
$ previously show 2
id=2 kind=observation
occurred_at=2026-10-05T04:51:23.128681+00:00
hash=3d4758362ff2ab2f05aa122158dd95ef0d5303cc01a4492817570403b4b3c4c4
evidence=recollection
payload={"blobs": [{"filename": "draft.txt", "media_type": "text/plain", "sha256": "b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373", "size": 35}], "evidence": "recollection", "text": "The second draft is attached.\n\nThe client wants it by Friday."}
  ¶1 The second draft is attached.
  ¶2 <erased by event 3>
  blob b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 35 text/plain draft.txt <erased by event 4>
```

`previously blob get` refuses it and returns `1`:

```console
$ previously blob get b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 --output draft-copy.txt
blob b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 is erased (event 4)
```

The file name stays in the payload.
If the file name itself has to go, erase the event instead.

## Erase an event

Name the event:

```console
$ previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
redacted by event 5
```

Check the event:

```console
$ previously show 1
id=1 kind=observation
occurred_at=2026-10-05T04:51:22.661609+00:00
hash=7e084ae695ef43e6024f899b8af6ae86203389e4e1d0b1d7bf7594b5956fa02e
payload=<erased by event 5>
  ¶1 <erased by event 5>
  blob 72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 <erased by event 5>
```

The payload, every unit, and the reference to each blob are erased.
A blob that another event still uses stays in the store, and `redact` says so on standard error, naming the blob and those events, in this form:

```text
blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 stays in the store: event 7 still uses it
```

If that blob has to go as well, erase it as a blob, or erase the events that still use it.

## Check the log

After any erasure, check the chain:

```console
$ previously verify --blobs
chain intact, 2 blobs match
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

`--blobs` also asks the store after every erased blob, and reports one that's still there as `erased and still present`.
On a bucket with versioning or object lock, the copy that deleting kept is out of its sight, and it reports nothing.
Without `--blobs`, `verify` reads no blob setting; leave `--blobs` out if the log names no blob.
The anchors you keep hold after an erasure as before, so run your usual check with `--anchors` as well; see {ref}`verify-the-chain`.

## If the command stops with exit code 2

If `redact` prints `the redaction is recorded as event …, but it is not finished`, the redaction stands, and a deletion from the store, the catch-up of the projections, or both are still outstanding; the sentence names each.
Run the same command again, once the cause the sentence names is gone.
It finds the target covered and prints:

```console
$ previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
already redacted by event 5
```

The second run writes no second redaction, and finishes what the first left undone.
If the sentence names a projection that `was rebuilt while this catch-up ran`, follow {ref}`rebuild-a-projection` first.
See {ref}`cli-reference` for every refusal and error of `redact`.

## What the erasure doesn't reach

An erasure takes the content out of the log and the blob out of the store.
It stays in every backup of the database, and in every backup or copy of the bucket, until their retention runs out, and a restore to a point before the erasure brings it back; {ref}`restore-from-a-backup` shows what to do then.
The address of a blob, the source key `(source, external_id)` and every hash stay as well.
An event written before stage 1c, in hash format 1, has no salt, so short erased content stays guessable from its digests; see {ref}`erasure`.
An erasure of units leaves their wording in a payload that repeats it, as *Erase units* says.
For why, see {ref}`erasure`.
