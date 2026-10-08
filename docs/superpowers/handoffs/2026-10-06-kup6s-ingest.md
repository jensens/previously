# Handoff to kup6s: taking mail in from an IMAP folder

**Date:** 2026-10-06
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-06-pilot-imap-aufnahme.md`, §6 (German, frozen), and what running the command in the image measured since

This file adds to the handoff of 2026-10-05, `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md`, and assumes everything that one asks for: the database, the bucket, the secrets split by who needs them, the migration job, the tools pod and the three CronJobs.
Like that one, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.
Nothing in this repository deploys anything into kup6s.

What it adds is one job: `previously ingest imap`, which reads the mail of one IMAP folder and appends each mail to the log as an event, with the raw mail and every attachment as blobs in the bucket.
It's the first thing in kup6s that brings real data into the log, and the first that talks to a server outside the cluster's own services.

## The image

The first release that has `ingest imap` is the first after `0.1.0a1`; `0.1.0a1` itself doesn't have it.
Pin its exact version, as the first handoff says for every release until `1.0.0`.

Run the migration job of that release before the CronJob below starts, as for every release.
The release brings the revision `0005_watermark`, a table that records how far each folder has been read.
Measured on 2026-10-06 against a database that the image `0.1.0a1` had migrated, the migration job of an image built from this branch printed:

```text
migrated: 0004_event_blob -> 0005_watermark
```

**It stands when** the migration job's log shows `migrated:` or `up to date:` with `0005_watermark`.

## A mailbox of its own

The maintainer copies the mails that belong in the log into a folder of a mailbox on his Mailu server.
That mailbox is a **user of its own**, for this job alone, such as `previously@<mail domain>`, and not the maintainer's own mailbox.
Whoever administers that Mailu creates the user; if that's you, the maintainer will ask.

**Why:** the password that kup6s holds opens that one mailbox and nothing else.
A leaked secret then exposes the mail somebody chose to put into the log, not everybody's mail.

The password has to be ASCII: `previously` sends the login in ASCII only, through Python's `imaplib`, and refuses any other character with a sentence rather than sending it.

## The secret of the folder

Five settings, in a secret of their own that only this job mounts:

| Variable | Value |
|---|---|
| `PREVIOUSLY_IMAP_HOST` | The host name of the Mailu server, **as its certificate names it**, such as `mail.<mail domain>`. |
| `PREVIOUSLY_IMAP_PORT` | `993`; left out, it's `993` as well. |
| `PREVIOUSLY_IMAP_USER` | The user above. |
| `PREVIOUSLY_IMAP_PASSWORD` | Its password. |
| `PREVIOUSLY_IMAP_FOLDER` | The full name of the folder on the server, in plain characters, umlauts as they are; the maintainer gives it to you. |

`docs/reference/configuration.md` is the authoritative description of each.

Beside them, the job needs `PREVIOUSLY_DSN`, the five settings of the bucket and `PREVIOUSLY_BLOB_RECIPIENT`, as in the first handoff's table under "whoever ingests".
It needs **no** `PREVIOUSLY_BLOB_IDENTITIES`: taking mail in seals blobs and opens none, so the identity stays where the first handoff put it, in the tools pod and the nightly check.

**Keep the host, the user and the folder as they are once the job has run.**
The three make the name under which `previously` remembers how far it has read, `imap:<user>@<host>/<folder>`.
A change to any of them reads the folder from the start again.
That's harmless, because every mail the log holds counts as known and nothing is written twice, but it fetches every mail of the folder once more.
The port isn't part of the name.

No message of `previously` prints the password, also not when the server refuses the login.

## TLS and the certificate

`ingest imap` connects over TLS only, on port 993, and verifies the server's certificate and host name against the trust store of the image; no setting turns either off.
The image carries Debian's trust store, measured on 2026-10-06 in an image built from this branch: 150 certificate authorities in the default context of Python's `ssl`.
A certificate from a public authority, such as Let's Encrypt, verifies with nothing added.

If the Mailu server presents a certificate of a private authority, mount that authority's certificate as a file and point `SSL_CERT_FILE` at it; OpenSSL then reads that file in place of the trust store.
If the job reaches the server under a name the certificate doesn't carry, such as a cluster-internal service name, the verification fails by design; use the name the certificate carries.

## The CronJob

Every 5 to 15 minutes, with `concurrencyPolicy: Forbid`:

```shell
previously ingest imap
previously project
```

`project` after `ingest`, so that the chronicle shows the new mail at once; the `project` CronJob of the first handoff stays as it is, and the two may run side by side.
Run `ingest` as an init container of the job and `project` as its container: the regular containers of a pod start together, and only an init container runs first.
With the image's entrypoint, `previously`, each runs as process 1 of its container and ends on `SIGTERM` with `143`.
Running both in one container takes the entrypoint set to `/bin/sh` and `sh -c 'previously ingest imap && exec previously project'`; a `SIGTERM` during the ingest then reaches the shell and not `previously`, and the pod ends when its grace period does, which loses nothing either.

`ingest imap` prints one line to standard output and returns `0` when the run went through:

```text
imap: 5 appended, 0 known, 0 variants, up to uid 4
```

`appended` counts the events this run wrote, `known` the ones the log already held, and `variants` the mails that came under a known Message-ID with another content; each variant also prints one line to standard error, `variant of <message-id>: event <id>`.
**Alarm on any exit code but `0`**, a failed Job, and pass every line of standard error on to whoever reads the alarm; a variant is no error and returns `0`.
The codes mean:

| Code | Meaning |
|---|---|
| `2` | `previously` refused, with one sentence on standard error: a missing setting, a server that can't be reached or refuses the login or the folder, a connection that broke off, an error of the database or the bucket, or a batch the log refuses. |
| `1` | An unexpected failure: an exception `previously` doesn't know, with a stack trace on standard error. |
| `137` | Killed, such as by the kernel at the memory limit below. |
| `143` | Stopped with `SIGTERM`, such as at the deadline of the Job. |

Two refusals with `2` come back at every run until the mail that causes them leaves the folder: a mail that makes more than 500 events with the mails attached to it, and a variant key the log already holds with another content, which takes two artifact hashes that share their first 64 bits.
`docs/reference/cli.md` lists every sentence of `2`.

**Why `Forbid` and why a failure costs nothing:** a run moves its position in the folder only after the events it covers are in the log, so a run that fails, is stopped, or runs out of time leaves the position where the last finished batch left it.
The next run fetches the rest again, finds the blobs already in the bucket and the events in the log, and writes nothing twice.
Two runs at once wouldn't break that, but they would fetch the same mail twice for nothing.
A socket operation that waits longer than 60 seconds ends the run with `2`, so a server that stops answering doesn't hold the job until the next schedule.

`previously` ends on `SIGTERM` with `143`, as the first handoff says, and an ingest that ends that way loses nothing either.

### Memory

**A memory limit of 768 MiB.**
A mail is taken in one at a time, and its raw bytes, its mapping and its blobs are what the run holds, so the peak follows the largest mail and not the number of mails.
Mailu accepts mails up to 50 MB by default.

Measured on 2026-10-06 in an image built from this branch, with `previously ingest imap` against a test server, invented mails of 49.5 MiB with an attachment of 36.2 MiB and of 27.4 MiB with one of 20 MiB, two runs each, with `--memory 768m` except for one of the two runs of a single 49.5 MiB mail, which ran with `--memory 512m`:

| Mails in the run | Resident peak of the process | `memory.peak` of the container |
|---|---|---|
| 1 of 49.5 MiB | 529 to 530 MiB | 511 MiB |
| 3 of 49.5 MiB | 529 to 531 MiB | 511 to 513 MiB |
| 1 of 27.4 MiB | 335 to 336 MiB | 316 to 317 MiB |
| 6 of 27.4 MiB | 335 to 336 MiB | 317 to 318 MiB |

The container ran with `/tmp` as a `tmpfs`, which counts against the limit, so `memory.peak` includes the temporary file below; the resident peak of the process doesn't.
A limit of 512 MiB still passed the mail of 49.5 MiB, with `memory.peak` at 511 MiB, which is too close to call a margin.

The image sets `MALLOC_MMAP_THRESHOLD_=131072`, glibc's default, fixed; without it, the peak grows with the number of large mails in one run, by about 25 MiB for three or six mails of 27.4 MiB in this image, and by more on other versions of glibc.
Keep it; the `Dockerfile` says why.

### A writable `/tmp`

`ingest imap` seals each blob into a temporary file before it uploads it, as `append --attach` does, so a read-only root needs a writable `/tmp`, such as an `emptyDir`.
It holds one sealed blob at a time, at most the size of the largest mail, so about 50 MB.
An `emptyDir` with `medium: Memory` counts against the memory limit, and the measurement above includes that case.

## Network out

- The Mailu server, on port 993, under the host name its certificate carries.
- DNS, to resolve that name.
- The database and the S3 server of the bucket, as for every other job.

Nothing inbound.

## The first run takes in the real folder

The maintainer runs the first ingest of a real customer folder **here**, not on his own machine.
His local runs are rehearsals: he discards that database and that bucket afterward, and the lasting log begins in kup6s, by reading the folder from the start.
Reading a folder is idempotent, so nothing about the rehearsal carries over or gets in the way.

Before the first run, the restore probe and the backup of the identity of the first handoff should stand: from this run on, the database holds real mail, which has no other copy in the log's form.

## Erasure reaches the mail server too

`previously` never changes the folder: it opens it read-only and reads each mail without marking it as read.
So an erasure in the log doesn't erase the mail from the mailbox.
Whoever promises the erasure of a mail deletes it in the folder as well, and in every backup of the Mailu server.

How long the backups of the mail server are kept is therefore part of every erasure promise, beside the retention of the database and the bucket the first handoff asks for.
Whatever retention you set for the mail server's backups, tell the maintainer.

## How to recognize that it stands

1. The migration job of the release reports `0005_watermark`.
2. The secret of the folder exists and only the ingest job mounts it; the job has no identity.
3. The first run exits `0`, with an `appended` count of at most the events the folder's mails make: the mails, plus one for each mail attached as a mail, down to five levels; a copy of a mail already counted is `known` instead.
4. The second run exits `0` and reports `0 appended`.
5. In the tools pod, `previously chronicle` shows the mails with their subjects, and `previously blob get` fetches the raw mail of one of them, whose address `previously show <id>` prints as its first `blob` line.
6. The flags of the mails in the folder are as they were: nothing in it was marked as read.
7. The retention of the mail server's backups is known to the maintainer.
