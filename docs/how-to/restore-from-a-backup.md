(restore-from-a-backup)=

# How to check how much of the chain a restore brought back

This guide shows you how to check, after a restore, how much of the chain you got back, and how to bring the blobs and the erasures in line with it.

:::{important}
A restore that was never rehearsed isn't a backup.
:::

Restoring the data itself runs through the backup system your deployment chose, and performing it isn't covered here.
{ref}`backup-encryption` says what that system has to meet.

Without the key that opens the backup, the restore can't proceed at all.
Treat that key with the same care as the data it protects.

Once the restore gives you a running PostgreSQL instance, point `PREVIOUSLY_DSN` at it.
See {ref}`configuration-reference` for its exact form.

Before you rely on that instance, check it against the anchor file you keep outside the database.
How to take anchors is in {ref}`verify-the-chain`.

## Check against the anchors as of the backup

Check the restored log against the anchor file as it stood at the backup's recovery point: the snapshot of a dump, or the target of a point-in-time recovery.

1.  Find that moment.
    For a dump that `pg_dump --format=custom` wrote, decrypt it first with the key that opens it, and run `pg_restore --list` on the decrypted file:

    ```shell
    pg_restore --list previously.dump | grep 'Archive created at'
    ```

    It prints the moment `pg_dump` created the archive, just before it took its snapshot.
    Use that moment: an anchor file from slightly earlier can only leave out an anchor the dump holds, never add one it lacks.
    For a point-in-time recovery, the moment is the recovery target you set.

2.  Get the version of the anchor file from before that moment from the place you keep it: under version control, or as a copy or message.
    The file doesn't date its own lines, so you can't read that version off the current file.
    In a Git repository that holds the file as `anchors.txt` on `main`, this takes the last version committed before the moment:

    ```shell
    rev=$(git rev-list -1 --before='2026-10-11 03:00:00 UTC' main)
    test -n "$rev" && git show "$rev":anchors.txt > anchors-restored.txt
    ```

    If `git rev-list` prints no commit, `test` fails and no file is written: the backup predates every anchor, so there's nothing to check against yet.
    Run `previously verify` without `--anchors` instead, and continue with *After the check* below.

    Don't take a version recorded after the moment: it holds anchors from after it, and each of those reads as a loss.
    If the backup is newer than the newest anchor, that version is the file as it stands today.
    If the file didn't exist yet at that moment, or held no anchor line, see *After the check* below.
    If you can't get it, see *If the anchor file has no history* below.

3.  Check against that file:

    ```shell
    previously verify --anchors anchors-restored.txt
    ```

    Exit code `0` means that up to the newest anchor in that file, nothing is lost and nothing is rewritten.
    Whatever the restored log holds after that anchor, this check doesn't vouch for it.
    Whatever it should hold there and doesn't, this check doesn't see.
    An `anchored event is missing` finding against that file is a loss: the restore stopped short of an anchor taken before the backup, and it failed.

4.  If the tip of the restored log is the last anchor in that file, add `--exact`:

    ```shell
    previously verify --anchors anchors-restored.txt --exact
    ```

    Exit code `0` then means, in addition, that the tip of the restored log is exactly that anchor.
    Otherwise, don't add `--exact`: it reports any event after the newest anchor as a finding, and that finding says nothing about loss.

Against the anchor file as it stands today, every anchor taken after the recovery point reports a finding of this form:

```text
FINDING 3: anchored event is missing (the log ends at 2)
```

Those findings are true: the restore gave up those events, and that's why you check against the earlier file instead.
For why a restore looks like this to the anchors, see {ref}`external-anchor`.

### If the anchor file has no history

If the anchor file was only ever appended to in one place, you can't tell which lines it held at the recovery point.
Then cut it at the tip of the restored log instead, and know its limit before you start.
The cut shows that nothing up to the last anchor it keeps was rewritten.
It can't show that the restore reached the point you meant, because the cut comes from the result of the restore itself.

1.  Run the check against the whole file, and read the tip of the restored log from a finding: the number after `the log ends at`.

    ```shell
    previously verify --anchors anchors.txt
    ```

    If it reports no `anchored event is missing` finding, whether it exits `0` or reports only other findings, the restore reached the newest anchor and there's nothing to cut.
    Read its result as step 3 of *Check against the anchors as of the backup* says.

2.  Number the lines of the anchor file:

    ```shell
    cat -n anchors.txt
    ```

    Find the last anchor line whose `id`, the first field, isn't above that tip, and note its line number, the number `cat -n` prints in front of it.
    If no anchor line has an `id` at or below the tip, don't cut; see *After the check* below.

3.  Copy the file up to and including that line into a new file.
    Pass the line number to `head -n`, not the `id`, even though both are `2` in this example:

    ```shell
    head -n 2 anchors.txt > anchors-restored.txt
    ```

4.  Check against the new file, as in steps 3 and 4 of *Check against the anchors as of the backup*, keeping in mind what the cut can't show.
    Exit code `0` there doesn't mean that the restore reached the point you meant.
    Add `--exact` only if the `id` of its last anchor is the tip of the restored log.

### After the check

Keep `anchors.txt` unchanged in either case below: it records what the restore gave up.

If no anchor was taken before the recovery point, for example because the backup is older than the first anchor, no anchor describes the restored log.
Run `previously verify` without `--anchors`, which checks only that the chain is consistent in itself, as *Read the result* says.
Then start over with a first anchor in a file of a new name, for example `anchors-new.txt`, never `anchors.txt`.
Take it as {ref}`verify-the-chain` shows, with that name in place of `anchors.txt`, and run the routine against it from then on.

Otherwise, run the routine from {ref}`verify-the-chain` against `anchors-restored.txt` from now on.
Against `anchors.txt`, it would raise the alarm on every run, unless the backup was newer than its newest anchor and the two files are the same.

## Read the result

If `previously verify` exits `1` against the anchor file that fits your case, the restored instance doesn't hold what the anchors say it should, and the restore failed, even if PostgreSQL itself started without complaint.
Discard the instance and restore again.
The one check whose findings you expect is the first step of *If the anchor file has no history*, after a restore to a point before the newest anchor: there, they only give you the tip.

If `previously verify` exits `2`, it didn't check anything: the anchor file is missing or unreadable, holds no anchor line, or holds a line that isn't an anchor line, or storage raised an error.
The message on standard error names the problem; see {ref}`cli-reference` for what counts as an input error.

If you have no anchor file, or no anchor describes the restored log, `previously verify` without `--anchors` is the only check left.
Its exit code `0` means that the restored chain is consistent in itself, and nothing more: a restore from an older state is a shorter chain that passes as well.

Don't treat a restored instance as a backup until it has passed this check.
For what each check sees and what it can't, see {ref}`external-anchor`.

## Check the blobs, and repeat the erasures

The blob store doesn't go back with the database.
Once the chain check above passes, check the blobs against the restored log:

```shell
previously verify --blobs
```

It needs the blob settings; see {ref}`configuration-reference`.
On a restored or new machine, two of its answers are about the identities and not about the blobs:

- `Error: PREVIOUSLY_BLOB_IDENTITIES is not a directory: <path>`, with exit code 2, means that the setting names no directory on this machine.
  Restore the directory of identities from its backup, point the setting at it, and run the check again.
- `cannot be opened` for every blob, with exit code 1, means that the directory exists and holds no identity for the keys of those blobs.
  Restore the missing identity files from their backup, as {ref}`keep-the-blob-key-safe` shows, before you read the findings as damage.

Read its findings apart from the chain check: a `missing` blob here doesn't mean that the restore failed.

A blob reported as `missing` after a restore is, as a rule, one that an erasure deleted after the point you restored to.
The restore took that erasure's redaction away, so its event names the blob again, and with an erased event, its payload and units stand there again with their content.
Other erasures since that point came back without any finding: an erased payload or unit is simply there again.

Repeat the erasures since the point you restored to whose target the restored log still holds.
The log can't tell you which erasures those were: its record of them is what the restore took away.
Take them from a record kept outside the database, which names for each erasure the command, its date, and for `redact event` and `redact units` the target's `id`, its `hash` and its source key; {ref}`erase-something` shows where to note them.
If you promise erasure to anybody, keep that record from the first erasure on; without it, nothing tells you what to repeat.

Don't repeat a `redact event` or `redact units` by its `id` alone.
A restore frees every `id` above the tip of the restored log, and an event appended since can hold the `id` your record names.
Learn the tip with `previously anchor`: the first field of the line it prints is the `id` of the last event.
An erasure whose target `id` lies above the tip you learned has lost its target to the restore.
For every other erasure of an event or of units in your record, run `previously show` with its `id`, and compare the `hash=` line with the hash in your record:

```shell
previously show 42
```

- If the hash is the one in your record, the event is the one you erased: repeat the command as it was.
- If `show` prints a different hash, or `No event 42`, the event you erased was appended after the point you restored to and went with the restore.
  Don't repeat that erasure: it would erase another event, and nothing undoes an erasure.

An event that went with the restore can come back: when its source delivers the same submission again, it's appended under a new `id`, with a new hash.
The source key in your record says that it's the submission you erased.
No command finds an event by its source key; `previously chronicle` prints the source key beside each unit, so look for it there, and erase the event you find under its new `id`, noting the new `id` and hash in your record.

A `redact blob` names the blob by its address, which a restore doesn't change.
Repeated, it erases the blob for every event that uses it when it runs, including an event that attached the same content again after the restore.
Repeat the erasures of blobs before anything else appends to the restored log, so that they reach no event the first erasure didn't reach.
See {ref}`cli-reference` for `show` and `anchor`.

Then run `previously verify --blobs` again.
Once every erasure is repeated, no `missing` finding is left.

A blob that was erased before the point you restored to, and attached again after it, lies in the bucket again, while the restored log names it only through erased references.
`previously verify --blobs` reports it as `erased and still present`, and returns 1.
Run `previously redact blob` with its address and a reason: it finds the blob covered, prints `already redacted by event <id>`, writes no redaction, and deletes the object.
Then run `previously verify --blobs` once more.

An object uploaded after the point you restored to, for a content that no event of the restored log names, stays in the bucket, and no check reports it.
For why losing the key that opens the backups means losing them for good, see {ref}`backup-encryption`.
