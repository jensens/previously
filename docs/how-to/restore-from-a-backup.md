(restore-from-a-backup)=

# How to check how much of the chain a restore brought back

This guide shows you how to check, after a restore, how much of the chain you got back.

:::{important}
A restore that was never rehearsed isn't a backup.
:::

Restoring the data itself runs through your deployment's own backup tooling, and that tooling arrives with a later stage's deployment, not with this repository.
Performing the restore itself isn't covered here.

Without the backup's encryption passphrase, the restore can't proceed at all.
Treat that passphrase with the same care as the data it protects.

Once the restore gives you a running PostgreSQL instance, point `PREVIOUSLY_DSN` at it.
See {ref}`configuration-reference` for its exact form.

Before you rely on that instance, check it against the anchor file you keep outside the database.
How to take anchors is in {ref}`verify-the-chain`.
Which check to run depends on what you restored to.

## Restore to the latest state

If you restored a base backup and replayed the write-ahead log to the latest state, check that the log contains every anchor:

```shell
previously verify --anchors anchors.txt
```

Exit code `0` means that up to the newest anchor, nothing is lost and nothing is rewritten.
Whatever the restored log holds after the newest anchor, this check doesn't vouch for it.
Whatever it should hold there and doesn't, this check doesn't see.
Don't add `--exact` here: any event after the newest anchor would be reported as a finding, although nothing is missing.

## Restore to an earlier point

If you restored to a point earlier than the newest anchor, first run the same check against the whole anchor file:

```shell
previously verify --anchors anchors.txt
```

Each anchor taken after the restore point reports a finding of this form, with exit code `1`:

```text
FINDING 3: anchored event is missing (the log ends at 2)
```

Expect these findings here: those lines anchor events that this restore gave up.
Don't discard the instance because of them.
For why a restore looks like this to the anchors, see {ref}`external-anchor`.

Check the restore against the anchor file as it stood at the restore point instead:

1.  Read the tip of the restored log from the finding: the number after `the log ends at`.

2.  Number the lines of the anchor file:

    ```shell
    cat -n anchors.txt
    ```

    Find the last anchor line whose `id`, the first field, isn't above that tip.

3.  Copy the file up to and including that line into a new file.
    For that line as line 2:

    ```shell
    head -n 2 anchors.txt > anchors-restored.txt
    ```

4.  Check against the new file.
    If the `id` of its last anchor is the tip of the restored log, add `--exact`:

    ```shell
    previously verify --anchors anchors-restored.txt --exact
    ```

    Exit code `0` means that up to that anchor, nothing is lost and nothing is rewritten, and that the tip is exactly that anchor.

    If the tip is above that anchor, run the check without `--exact`:

    ```shell
    previously verify --anchors anchors-restored.txt
    ```

    Exit code `0` then means the same as in the first case, and it vouches for nothing after the newest anchor in the new file.

From now on, run the routine from {ref}`verify-the-chain` against `anchors-restored.txt`.
Against `anchors.txt`, it would raise the alarm on every run.
Keep `anchors.txt` unchanged: it records what the restore gave up.

## Read the result

If `previously verify` exits `1` against the anchor file that fits your case, the restored instance doesn't hold what the anchors say it should, even if PostgreSQL itself started without complaint.
Discard the instance and restore again.

If `previously verify` exits `2`, it didn't check anything: the anchor file is missing or unreadable, or a line in it isn't an anchor line, or storage raised an error.
The message on standard error names the problem; see {ref}`cli-reference` for what counts as an input error.

If you have no anchor file, `previously verify` without `--anchors` is the only check left.
Its exit code `0` means that the restored chain is consistent in itself, and nothing more: a restore from an older state is a shorter chain that passes as well.

Don't treat a restored instance as a backup until it has passed this check.
For what each check sees and what it can't, see {ref}`external-anchor`.
For why losing the passphrase means losing the backups for good, see {ref}`backup-encryption`.
