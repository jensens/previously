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

Run `previously verify` against that instance before you rely on it.

If `previously verify` exits `1`, the restore failed, even if PostgreSQL itself started without complaint.
Discard the instance and restore again.

If `previously verify` exits `0`, the restore is trustworthy.
This check matches every event's hash against its predecessor, so it catches a restore that booted but didn't bring back an intact history—not merely that PostgreSQL starts.

Don't treat a restored instance as a backup until it has passed this check.
For why losing the passphrase means losing the backups for good, see {ref}`backup-encryption`.
