(restore-from-a-backup)=

# How to check that a restore brought the chain back

This guide shows you how to confirm, after any restore, that you got the chain back.

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
The events after the newest anchor came back from the write-ahead log, and this check doesn't vouch for them.
Don't add `--exact` here: it would report those events as a finding although nothing is missing.

## Restore to a fixed point that coincides with an anchor

If you restored to a fixed point, and an anchor was taken at exactly that point, add `--exact`:

```shell
previously verify --anchors anchors.txt --exact
```

Exit code `0` means, in addition, that the tip of the restored log is exactly that anchor.
This fits a named restore point set right after an anchor was taken, or a logical dump taken together with its anchor.

## Read the result

If `previously verify` exits `1`, the restore failed, even if PostgreSQL itself started without complaint.
Discard the instance and restore again.

If you have no anchor file, `previously verify` without `--anchors` is the only check left.
Its exit code `0` means that the restored chain is consistent in itself, and nothing more: a restore from an older state is a shorter chain that passes as well.

Don't treat a restored instance as a backup until it has passed this check.
For what each check sees and what it can't, see {ref}`external-anchor`.
For why losing the passphrase means losing the backups for good, see {ref}`backup-encryption`.
