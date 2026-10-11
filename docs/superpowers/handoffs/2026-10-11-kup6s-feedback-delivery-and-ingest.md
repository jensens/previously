# Feedback from kup6s: delivery and ingest handoffs

**Date:** 2026-10-11
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-05-kup6s-delivery.md` and `handoffs/2026-10-06-kup6s-ingest.md`

Both handoffs stand.
This file says what runs, where kup6s deviates from the handoffs and why, the numbers the handoffs asked for, and what the Previously docs may want to take over.

## What stands

Every check of both handoffs passed, on `0.1.0a2`:

| Check | Result |
|---|---|
| Image pulls without credentials | yes, since `0.1.0a1` |
| Migration job | `migrated: 0004_event_blob -> 0005_watermark` |
| Tools pod: `append --attach`, `blob get`, `verify --blobs` | all `0`, against Hetzner Object Storage hel1 |
| Restore probe, then `verify --anchors` | `chain intact, 5 anchors hold`, `1 blob matches` (2026-10-09) |
| CronJobs `project`, `anchor`, `verify` with `0` | yes; anchors daily since 2026-10-06 |
| Identity backup apart and rehearsed | yes, from the password vault, `age -d` opened a blob from the bucket (2026-10-11) |
| Ingest secret only in the ingest job, no identity | yes |
| First ingest run | `imap: 10 appended, 1 known, 0 variants, up to uid 9` (9 mails) |
| Second run | `0 appended` |
| `chronicle` and `blob get` of a raw mail | yes; the raw mail's SHA-256 is its address |
| Flags in the folder unchanged | yes, nothing marked as read |

The log holds one event before the mails: `--source kup6s-smoke`, the smoke test of the first install.
It stays; the data will be reset before regular use anyway.

## Deviations, and why

**PostgreSQL 18, not 17.**
The handoff says 17 without a reason; the specs only set a floor of 15 (`NULLS NOT DISTINCT`).
kup6s runs 18 fleet-wide, and every check above ran against 18.
Please add 18 to the tests and the smoke test.

**Backups are encrypted `pg_dump` files, not barman and not pgBackRest.**
The delivery handoff asked for a base backup and a WAL archive and was silent on encryption, while the architecture (§10.5) and `explanation/backup-encryption.md` chose the pgBackRest CNPG-I plugin with client-side encryption, and `restore-from-a-backup.md` assumes a passphrase.
Once the ingest brought real mail, plaintext barman backups at Hetzner were no longer acceptable.
Checked on 2026-10-09, and rejected:

- the pgBackRest CNPG-I plugins: both call themselves experimental, the Opera one has had no commit since 2026-08-28, the Dalibo one two since September, and neither was ever tested against Hetzner or Ceph;
- barman-cloud with client-side encryption: it doesn't exist (EnterpriseDB/barman#1155, plugin-barman-cloud#911 and #1017 are open);
- barman behind an encrypting S3 proxy (`rclone serve s3` with crypt): `serve s3` documents itself as experimental.

What runs instead: every hour, `pg_dump --format=custom` streams through `gpg --encrypt` to a backup key, and the ciphertext goes to its own bucket, kept seven days.
The cluster holds the public key only; the private key is in the password vault.
barman is gone, so no WAL and no base backup leaves the cluster in plaintext; two CNPG instances protect against losing a node instead.
The architecture's three paths A, B and C didn't include logical dumps; they may be worth a line there.

What this costs: there is no point-in-time recovery, and the recovery point is the newest hourly dump.
For the ingest that costs nothing, because its watermark lives in the same database: after a restore, the next run reads the folder from the restored position and writes nothing twice.
Entries made by hand and erasures since the newest dump are lost; the record of erasures outside the database that `restore-from-a-backup.md` asks for covers the latter.
`restore-from-a-backup.md` speaks of the backup's "encryption passphrase"; on kup6s that's the private GPG key, which the restore needs in the same way.

**The bucket credentials reach more than the bucket.**
Hetzner S3 keys are valid for every bucket of a project, and kup6s uses one project.
A bucket policy with `NotPrincipal` can keep other keys out of a bucket, but can't keep a key out of other buckets.
For the test phase, the blob bucket and the dump bucket use the fleet's credentials: blobs and dumps are encrypted, and `verify --blobs` detects a deleted or replaced blob, though nothing prevents it.
Please say whether "credentials for this bucket and nothing else" remains a requirement for regular use; then it takes a Hetzner project of its own.

**The anchor file lives in Git on a separate server, not at a third party.**
`git.bluedynamics.eu/jensens/previously-anchors`, `anchors.txt` on `main`, which refuses force pushes and accepts pushes from the anchor job's deploy key only.
That server runs outside the kup6s cluster, so whoever takes over the cluster can only append.
It's run by the same people, so it's not a third party in the sense of the anchor spec.
The Git history gives the anchor file as it stood at any point, which `restore-from-a-backup.md` needs for a restore to an earlier point.
A first anchor needs a log with at least one event; until then `verify --anchors` exits `2`, which the handoff's "each CronJob exits 0" didn't account for.

**The restore probe runs by hand.**
It needs the private backup key, which comes into the cluster only for the probe.
The handoff asks for a scheduled probe; that waits for a decision on where a scheduled job may hold that key.

## The numbers you asked for

Retention, for every erasure promise:

| Copy | Retention |
|---|---|
| Encrypted dumps of the database | 7 days |
| Blob bucket | no backup or copy |
| Mailu mailbox, where the mails stay after the ingest | 7 daily backups of the mail volume, plaintext, on a Storage Box |

So an erasure promise for content that came in by mail has to name seven days, and it has to include deleting the mail in the folder.

## For the Previously docs

- Object Lock exists at Hetzner (retention and legal hold, enabled only when the bucket is created); the anchor spec lists it as unchecked.
- `blob get --output` has to write to a writable directory; in a read-only container that means `/tmp`, because the working directory `/app` isn't writable.
- `kubectl cp` works with the image, because it has `tar`.
- The ingest reached Mailu from inside the cluster through its public name and load balancer, with the certificate verified; the PROXY protocol in front of Mailu didn't get in the way.
- A single run failed with `Operation not permitted` while connecting to the database during a cluster-wide incident on the night of 2026-10-11; the next run picked up the rest, as the ingest handoff says it would.
