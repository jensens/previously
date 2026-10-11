(backup-encryption)=

# About what a backup has to meet

Previously runs no backup of its own, and this repository builds none: backing up the database is the work of the environment that hosts it.
What Previously does depend on is a handful of properties that any backup has to have, whatever system takes it.
This page names them and says why each one is there.
Which system meets them is the operator's choice: pgBackRest, Barman, `pg_dump` through `gpg` or `age`, or something else.

Until 2026-10-11 this page argued for one system instead, and the section at the end says what changed and why.

## Encrypted before it leaves the database's host

A backup of the database holds every unit in plain text, because the database does, and {ref}`trust-boundaries` counts it among the places where the content leaves the system.
So a backup is encrypted before it leaves the host the database runs on, and the key that opens it lies outside the system it protects.

Encryption by the storage provider doesn't meet that, and at the provider this project uses it isn't even available as a default.
Checked on 2026-10-03 against the documentation of Hetzner Object Storage:

> There is no default data-at-rest encryption of objects, but you can encrypt your data during the upload using SSE-C.

SSE-C, where the client hands the key over with every request, is the one server-side mode on offer, and it breaks on copies.
The same documentation states that a copy of an SSE-C encrypted object isn't supported, and that `CopyObject` works only within the same bucket; underneath lies a Ceph cluster, whose object gateway supports `CopyObject` under none of its server-side encryption modes.
The sister project kup6s, on the same provider, keeps the standing rule *never use server-side encryption* for that reason.
And even where server-side encryption works, the provider holds the key and can open the backup when pressed.
For a store whose purpose is a defensible history of client projects, who holds the key outranks every convenience of the tooling.

The key that opens the backup lies neither beside the database nor in the backup target.
A key that lies beside its data protects nothing from whoever reaches the data, and goes down with it in the same incident.
Public-key encryption helps here: the host that takes the backup needs only the public key, and the private key that opens it never has to come near the database at all.

The price is said out loud, because it's of the same family as everything else in this design: **whoever loses the key that opens the backups loses the backups, for good.**
With server-side encryption the provider could help; here nobody can, by construction.
So the key needs the same care as the data it protects, and a **rehearsed** way to obtain it again and open a backup with it.
A key that has never opened a backup is as little a key as an untested restore is a backup.

The blobs follow the same line: they're sealed in the `age` format before they leave the process, and the identity that opens them lies apart from the bucket, as {ref}`blobs` explains.
The two keys stay separate, because blobs and backups aren't the same loss, and {ref}`keep-the-blob-key-safe` shows how the blob key is kept.
Which vault holds either key is a decision of the platform, not of this project; Previously asks only that neither key lies where the data it opens lies, and that obtaining it again has been rehearsed.

## A named retention

An erasure takes content out of the log and out of the bucket, and leaves it in every backup taken before it; {ref}`erasure` explains why it can't do more.
So a backup's retention isn't only how far back a restore can reach.
It's also how long an erased content stays readable for whoever holds the backup and its key, and that bounds every promise of erasure.

So the retention is named, as a number: of the database's backups, of a write-ahead log archive where one is kept, and of every backup or copy of the bucket.
Whoever promises erasure within a period chooses these retentions by it.
The encryption doesn't shorten that period: a backup that opens for a restore opens for the erased content as well, until it's deleted.

The promise reaches what Previously holds and what it passed on itself, and no further.
A mail server and its backups are the source's, and their retention belongs to no erasure promise of Previously; {ref}`erasure` draws that line.

## A stated recovery point, and what's lost up to it

Every backup has a recovery point: the newest state a restore can bring back.
With a base backup and a write-ahead log archive, it can be any moment the archive reaches, which is point-in-time recovery.
With dumps, it's the moment the newest dump took its snapshot, and nothing in between.
Either is acceptable, as long as it's stated, because what a restore loses is everything written after it.

For the log, that's every event since the recovery point.
The mail the ingest took in comes back without anybody's help.
The connector's watermark lives in the same database as the log, and it's written only after the batch it covers is appended, so a backup never holds a watermark ahead of its log; {ref}`connectors` explains the order.
After a restore, the next run of `ingest imap` reads the folder from the restored watermark and takes in again what the restore gave up, as new events whose `id` values may repeat those the restore gave up.
It appends nothing twice: a mail the restored log holds already, because the backup fell between an append and the watermark that followed it, is found under its source key and counted as known.
That holds only for what the folder still holds: a mail taken in after the recovery point and removed from the folder since is gone with the restore.

The rest doesn't come back by itself.
What the operator recorded since the recovery point, such as an `append`, a policy statement or a new client, has to be recorded again.
The records of the model calls and of the clients' accesses since then are gone, and nothing can write them again.
An erasure since the recovery point is undone by the restore, and the log can't say which ones those were, since its record of them is what the restore took away.
That's why every erasure is noted in a record kept outside the database, and repeated from it after a restore, as {ref}`restore-from-a-backup` shows.

## A restore probe, checked against the anchors

A backup that was never restored isn't known to be a backup.
So a restore runs again and again, into a scratch database, as a probe.

The probe ends with `previously verify --anchors`, not with PostgreSQL starting.
The hash chain checks the restored holdings themselves, and an anchor kept outside the database adds whether anything up to the newest anchor is lost or rewritten; {ref}`external-anchor` says what each check sees.
The anchors it checks against are those that stood when the backup was taken.
An anchor taken after the recovery point describes events the backup can't hold, and against it the restore reads as a loss: a true one, but not the one the probe looks for.
The anchor file doesn't date its own lines, so the version as of the backup has to come from somewhere: a history of the file, such as the Git history of a repository that holds it, gives it for any moment.

The probe runs at a rhythm the operator names, because a backup that restored last month says little about the one taken last night.
It needs the key that opens the backup, which is the one place where that key comes near the database's environment.
The environment chooses where the probe holds it, under the requirement above: the key lies outside the system it protects.
A probe run by hand, with the key brought in for it alone, meets the requirement as long as it keeps the rhythm; one that waits for somebody to remember it doesn't.

(backup-deletion)=

## Out of reach of what handles foreign content

**No credential that a process handling foreign content holds can delete or overwrite a backup.**
Those processes are the ingest, which parses mail from outside; the gate, which sends content to a provider and reads its answer; the MCP server, which answers the requests of a client; and wherever an operator runs the commands by hand, such as a tools pod.
A backup is the way back after the database or the bucket is damaged, and those processes are the likeliest to be taken over.
If one of their credentials can also delete the backups, one compromise takes the data and the way back together.
Encryption doesn't help here: it keeps a backup from being read, not from being deleted.

The credentials of the blob bucket are the case that matters in practice.
The ingest and the operator's commands hold them, and where they reach further than the blob bucket they may reach the backups, which {ref}`blob-bucket-requirements` rules out from the other side.
Object Lock on the bucket of the backups, with a retention as long as the named one, is one way to meet this requirement: no credential can then delete a backup before its time, and the named retention that bounds every erasure promise stays what it was.
It doesn't fit the blob bucket, where an erasure has to be able to delete.

## The blob bucket

The bucket keeps neither versions nor locked objects, because an erasure deletes an object and trusts the store that it's gone; {ref}`erasure` gives the reason.
The bucket doesn't go back with the database either: after a restore, the blobs and the log are brought in line as {ref}`restore-from-a-backup` shows.
Whether the bucket itself is backed up or copied is the operator's choice.
If so, that copy is part of the data an erasure promise covers, so its retention is named beside the database's.
Who may reach the bucket at all is a requirement of its own, stated in {ref}`blob-bucket-requirements`.

## Two ways to meet the requirements

The kup6s environment, where the pilot runs, dumps the database every hour with `pg_dump --format=custom` and streams the dump through `gpg --encrypt` to a backup key, into a bucket of its own that keeps each dump for seven days.
The cluster holds the public key only, and the private key lies in a password vault; there's no point-in-time recovery, so the recovery point is the newest hourly dump.
In its test phase, kup6s doesn't yet meet two of the requirements: the credentials of the blob bucket reach the bucket of the dumps as well, and the restore probe runs by hand when somebody starts it.

A host run with a `docker-compose` file meets the same requirements with one scheduled `cron` job: `pg_dump --format=custom`, piped through `age -r` with a recipient whose identity lives elsewhere, or through `gpg --encrypt`, into a file that's copied off the host, to a place no container of Previously can write to, and a second job that deletes the files older than the retention.
The restore probe there is the same commands as anywhere else, run against a second database container.

## What changed on 2026-10-11

Until 2026-10-11 this page chose a system: the pgBackRest plugin for CNPG-I, with client-side `aes-256-cbc` encryption of base backups and write-ahead log archives, against Barman with server-side encryption at another provider and Barman in the clear.
That choice came from §10.5 of the frozen architecture record, which weighed those three paths and picked pgBackRest because, under it, only the project holds the key.

When the kup6s environment had to put real mail into a backup, it checked the candidates on 2026-10-09 and rejected all of them, as its feedback of 2026-10-11 reports, in `docs/superpowers/handoffs/2026-10-11-kup6s-feedback-delivery-and-ingest.md`.
Both pgBackRest plugins for CNPG-I call themselves experimental, the one from Opera had no commit since 2026-08-28 and the one from Dalibo two since September, and neither had been tested against Hetzner or Ceph.
The Barman Cloud tools have no client-side encryption, and the requests for it are open.
Barman behind an encrypting S3 proxy, `rclone serve s3` with `crypt`, rests on a command that documents itself as experimental.
What kup6s built instead, encrypted dumps, wasn't among the three paths at all.

So on 2026-10-11 the maintainer changed what this page decides: no longer a system, but the requirements any system has to meet, with the choice of system left to whoever runs it.
The reason that drove the old choice survives as the first requirement.
A backup encrypted by the provider, or not at all, still doesn't meet it, and that was the whole case against the two paths the architecture record rejected.
