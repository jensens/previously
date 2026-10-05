# Handoff to kup6s: running Previously from its image

**Date:** 2026-10-05
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-05-auslieferung.md`, §6 (German, frozen), and what building the image and the release workflow measured since

This file says **what** Previously needs in kup6s, **why**, and **how to recognize that it stands**.
It never says how to build it in cdk8s: that's yours to decide, with ArgoCD and the CloudNativePG operator kup6s already runs.
Nothing in this repository deploys anything into kup6s.

Previously is a command line, not a service: an append-only event log in PostgreSQL, with every event hash-linked to its predecessor, and attached files ("blobs") sealed with `age` in an S3 bucket.
Until its MCP server exists, everything in kup6s is a job, a CronJob or a tools pod that runs one `previously` command at a time.

The documentation the sections below point at is under `docs/` in the repository; each reference names the file.

## Before the first image exists

The maintainer has set up the publishing side, and you need nothing from it:

- the GitHub environments `pypi`, deployable only from tags `v*`, and `testpypi`, deployable only from `main`;
- a trusted publisher on PyPI and on Test-PyPI for the workflow `release.yml` and those two environments, so no upload token exists anywhere.

The first image appears with the first published GitHub release, `v0.1.0a1`.
Until then, there's nothing to pull.

The package on ghcr.io is **private** after its first push, which is GitHub's default.
The maintainer makes it public once, after that first release, so that kup6s pulls it without credentials.
If he decides to keep it private instead, he gives you a pull secret, and this file is the place where that gets added.

**It stands when** `docker pull ghcr.io/jensens/previously:0.1.0a1` works without logging in.

## The image

| Property | Value |
|---|---|
| Location | `ghcr.io/jensens/previously` |
| Platforms | `linux/amd64` and `linux/arm64`, one manifest list |
| Tags of a stable release | `<version>`, `<major>.<minor>`, and `latest` |
| Tags of a pre-release | `<version>` only, such as `0.1.0a1` |
| Entry point | `previously`; without arguments it prints its help and exits `0` |
| User | uid 1000 and gid 1000 by default, set by number (`USER 1000:1000`); any other uid works as well |
| Ports, health check, volumes | none |

**Pin the exact version.**
Every release until `1.0.0` is an alpha, and an alpha has only its exact version tag: no `<major>.<minor>`, no `latest`.
Even for a stable release, `latest` is the wrong thing to follow, because a later release of an older line moves it back.
The tags `<version>-linux-amd64` and `<version>-linux-arm64` also exist; they're intermediate tags of the release workflow, and nobody is meant to use them.

**Why:** the image holds exactly the package that is on PyPI, installed into dependencies taken exactly from the project's `uv.lock`, and a smoke test on each platform ran that image against PostgreSQL 17 and an S3 server before the tags you use were created.
`docs/explanation/delivery.md` gives the reasoning.

**Any uid works.**
Measured on 2026-10-05: the smoke test runs every command as the host's user, which is uid 1001 on a GitHub runner; `migrate` also ran under `--user 12345:12345` with `--read-only`, and `append`, `verify`, `project` and `anchor` with `--read-only`.
The image names its user by number, so `runAsNonRoot` works on its own, without `runAsUser` beside it; with a name, the kubelet can't tell that the user isn't root, and refuses to start the pod.
The final review measured both in a `kind` cluster on 2026-10-05.
So `runAsUser` and `runAsNonRoot` are fine, and `readOnlyRootFilesystem` is fine with one exception.

The exception is `previously append --attach`: it seals the file into a temporary file before the upload, and with a read-only root it finds no directory for it, because neither `/tmp` nor the working directory `/app` is writable.
Wherever `append --attach` runs, which is the tools pod and later the ingest, give it a writable `/tmp`, such as an `emptyDir`.
Measured on 2026-10-05 with `docker run --read-only`: Python found no usable temporary directory under the default working directory, and the whole smoke test, `append --attach`, `blob get` and `verify --blobs` included, passed with a writable working directory instead.
The only command that writes a file of its own is `previously blob get --output <file>`, and it writes a temporary file in the directory of `<file>` and renames it; that directory has to be writable.

`previously` ends on `SIGTERM` with exit code `143` and nothing on standard error, also as process 1 of its container, so a container that gets stopped ends at once rather than at the end of its grace period.
That holds once the command has started: a `SIGTERM` within about the first 0.7 s, while it imports, isn't caught, and that container ends only at the end of its grace period.
A migration it was running rolls back.
Measured on 2026-10-05 with `docker stop`, which sends `SIGTERM` the way the kubelet does: on a `migrate` that waited for the lock, it took 0.4 s and ended with `143`, where the image before took the full ten seconds and ended with `137`.

The image's labels carry `org.opencontainers.image.title` (`previously`), `description`, `url`, `source`, `licenses` (`AGPL-3.0-or-later`) and `version`, and from the release workflow `revision`, the commit of the release, and `created`, the moment the release was published.

## PostgreSQL

PostgreSQL 17 through CloudNativePG, with a base backup, a write-ahead log archive, and a **restore probe**: a scheduled restore into a scratch cluster that then gets checked.
Previously needs PostgreSQL 15 or newer; 17 is what the tests and the smoke test run against.

**Why:** the log is the record, and nothing derives it from anywhere else.
A backup that was never restored is not a backup.

The routine for checking a restore is `docs/how-to/restore-from-a-backup.md`, and its check is `previously verify --anchors`: against the anchors kept outside the database, it says whether the restore brought back everything up to the newest anchor.
That page assumes the restore itself is done by the platform's tooling, which is what you build.

The application's role creates the schema on the first `previously migrate`, so it has to be allowed to create tables and indexes in the database's `public` schema; on PostgreSQL 15 and newer, the owner of the database is.
A role that may not is refused with a sentence that names the database's own reason, such as `permission denied for schema public`.

**It stands when** a restore probe has run once, and `previously verify --anchors` against the restored copy exited `0`.

## The bucket

One S3 bucket for the blobs, **without versioning and without object lock**, with access credentials of its own that reach that bucket and nothing else.

If you write those credentials as a policy per operation, Previously uses `HeadObject`, `PutObject` with multipart upload, `GetObject` and `DeleteObject` on the bucket's objects.
On a server that follows AWS, it also needs `ListBucket`: without it, a missing object answers `403` instead of `404`, and `append --attach` of new content fails.
That second sentence is AWS's documented behavior, not measured against the store kup6s uses.

**Why:** an erasure in Previously deletes the blob from the bucket.
On a bucket with versioning or object lock, deleting keeps a copy, and the erasure doesn't take what it promises.
Nothing in Previously checks the bucket for either, and `verify --blobs` can't see it.

The same holds for any backup or copy of the bucket, and of the database: how long they're kept is part of every erasure promise, because an erased content stays in each backup taken before the erasure, until that backup expires.
No retention is chosen yet; whatever you set, tell the maintainer, since it's the number an erasure promise has to name.

**It stands when** asking the bucket for its versioning returns no status, and asking it for its object lock configuration returns "configuration does not exist"; `docs/how-to/run-a-blob-store-on-your-machine.md` shows both requests.

## Secrets, split by who needs them

Previously reads all of its settings from environment variables; there's no configuration file.
`docs/reference/configuration.md` is the authoritative list, and the table below takes from it which command reads each.

| Variable | Read by | Give it to |
|---|---|---|
| `PREVIOUSLY_DSN` | every command, `migrate` included | every pod and job |
| `PREVIOUSLY_BLOB_ENDPOINT` | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob | whoever writes, reads or deletes blobs |
| `PREVIOUSLY_BLOB_REGION` | the same | the same |
| `PREVIOUSLY_BLOB_BUCKET` | the same | the same |
| `PREVIOUSLY_BLOB_ACCESS_KEY` | the same | the same |
| `PREVIOUSLY_BLOB_SECRET_KEY` | the same | the same |
| `PREVIOUSLY_BLOB_RECIPIENT` | `append --attach` | whoever ingests; it's public |
| `PREVIOUSLY_BLOB_IDENTITIES` | `blob get`, `verify --blobs` | **only** the tools pod and the nightly `verify --blobs` |

### The connection string

`PREVIOUSLY_DSN` has the form `postgresql://user:password@host:5432/database`, or `postgresql+psycopg://` with the same rest.
`previously` reads it by a strict grammar before it connects, and refuses anything else with one sentence that names no part of it.
`docs/reference/configuration.md` gives the grammar in full; three points of it matter for kup6s:

- Special characters in the user name and the password have to be **percent-encoded**, such as `%40` for `@` and `%2F` for `/`.
- The `uri` key of the secret CloudNativePG writes for an application's role is accepted **as it is**.
  Measured on 2026-10-05 against the form Go writes, a password with `&$,;` included: `previously migrate` exited `0`.
  CloudNativePG's own passwords are letters and digits only.
- The password stands in the user part and **nowhere else**: `password` as a query parameter is refused.
  The query takes only the keys `application_name`, `channel_binding`, `connect_timeout`, `require_auth`, `sslcert`, `sslkey`, `sslmode` and `sslrootcert`.

A message about the database names its database, host and port, and never the password.
When connecting fails, the sentence quotes the first line of the client library's reason, which can name the user.

A password needs a user name in front of it: `postgresql://:password@host/database` is refused.

Point `PREVIOUSLY_DSN` at the database directly, such as CloudNativePG's `-rw` service, and not at a pooler in transaction mode.
`migrate` holds its lock on the session, and a pooler in that mode can take the lock and its release through two different server connections, which would leave the lock behind and make every later `migrate` wait.
That follows from how such a pooler works and isn't measured.

### The identity

`PREVIOUSLY_BLOB_IDENTITIES` names a **directory** that holds one file per key, each named after its recipient (`age1…`) and holding the identity, one line of the form `AGE-SECRET-KEY-1…`.
Mount it as files from a secret; `docs/how-to/keep-the-blob-key-safe.md` says how a key is made and laid out.

**Why it goes almost nowhere:** the identity is the one thing that opens a blob.
Whoever holds it and the bucket holds every attached file in the clear.
The job that ingests needs no identity at all: sealing needs only the public recipient.

**Its backup lies apart** from the database and from the bucket, and from their backups.
Losing the identity loses every blob sealed to it, for good: the bucket holds ciphertext only, and no command and no provider can open it again.

**It stands when** a blob that was attached in the tools pod can be fetched with `previously blob get` there, and the backup of the identity has been rehearsed once as `docs/how-to/keep-the-blob-key-safe.md` describes.

## A migration job per release

One job per release, before anything else of that release starts:

```shell
previously migrate
```

It prints one line and exits `0`:

```text
migrated: (empty) -> 0004_event_blob
up to date: 0004_event_blob
```

The first form names the revision the database was at, `(empty)` for a database without a schema, and the newest one; the second means nothing had to run.

**Why first:** the order of the jobs is the only guard, because `migrate` is the only command that compares revisions.
Every other command fails on a schema that's behind only where it touches a table or a column the schema lacks, with ``Error: database schema incomplete — `previously migrate` has not run yet`` and exit code `2`; where it touches none, it runs.
Measured on 2026-10-05 against a database one revision behind: `append`, `log` and `project` exited `0`, and `verify` refused.
So a migration job that's forgotten or late doesn't stop the commands of the new release; let nothing of the release start before its migration job has succeeded.

**Two at once are safe.**
`migrate` holds a PostgreSQL advisory lock while it runs, so a second migration job waits and then reports `up to date`.

**An older image's `migrate` against a newer database is refused**, with exit code `2`, and changes nothing:

```text
Error: the database is at revision 0005_example, which this version of previously does not know; it knows revisions up to 0004_event_blob
```

The older image's other commands aren't refused, for the same reason as above: they run against the newer schema as far as it still has what they touch.

`migrate` only goes forward; going back is a restore, not a command.

**It stands when** the job's log shows `migrated:` or `up to date:` with the newest revision of the release.

## A tools pod

A Deployment with one pod from the image, whose command is a sleep instead of the entry point, such as `sleep infinity` (the image has `/usr/bin/sleep`), with every secret above, the identity included.

**Why:** until the MCP server exists, the maintainer works with `kubectl exec <pod> -- previously <command>`: appending by hand, fetching a blob, erasing something, reading the chronicle.

**It stands when**, in that pod, `previously append --attach`, `previously blob get` and `previously verify --blobs` each succeed once; see `docs/how-to/attach-and-fetch-a-file.md`.

## CronJobs

Each with `concurrencyPolicy: Forbid`.
Exit code `0` is success and `2` an error that kept the command from doing its work; what `1` means differs per command, a finding of the chain for `verify` and `anchor`, and `docs/reference/cli.md` has the table.

- **`previously project`, at short intervals**, such as every five minutes.
  It brings the two derived views, the chronicle and the counts per source, up to the tip of the log.
  It needs only `PREVIOUSLY_DSN`.
- **The anchor routine, daily.**
  `previously anchor` prints the tip of an intact chain as one line, and that line has to be kept **outside the database**, in a place that whoever can write the database can't write.
  Where is the platform's decision; `docs/how-to/verify-the-chain.md` gives the conditions and the routine: fetch the anchor file, run `previously verify --anchors - < anchors.txt && previously anchor >> anchors.txt`, and put the file back.
  Standard input has to be passed through, and no terminal allocated, or standard error lands in the anchor file.
  It needs only `PREVIOUSLY_DSN`.
  The image has no tool to fetch or put back a file: no `curl`, no `wget`, no `aws`, measured on 2026-10-05; it has `/bin/sh`, `sleep`, and Python with `boto3`.
  So the fetching and putting back happen outside the `previously` container, such as in a container of the job that brings its own tool, and the anchor file reaches `previously` on standard input.
- **`previously verify --anchors - --blobs`, nightly**, with an **alarm on any exit code but `0`**.
  It checks the chain against the anchors, and reads, opens and checks every blob that has to lie in the bucket, so it takes about as long as reading the whole bucket.
  It needs `PREVIOUSLY_DSN`, the five bucket settings and the identity, and the same anchor file as the daily routine on standard input, fetched the same way.

The ingest CronJob comes with the handoff for the ingest, the next unit of work.

**Why:** the projections are derived and disposable, so a late run costs freshness and nothing else.
The anchors are what turns "the log is unchanged" into "the log is complete up to the newest anchor"; without them, a deleted tip passes every check.
The nightly check is the one that sees a blob gone missing or a chain that no longer holds.

**It stands when** each CronJob has run once with exit code `0`, and the anchor file outside the database holds a first line.

## Network out

- The database, such as CloudNativePG's `-rw` service on port 5432.
- DNS, to resolve the names of the database and the S3 server.
- The S3 server of the bucket.
- The place the anchor file lives, if it's outside the cluster, for the container that fetches it and puts it back.
- With the ingest, later: the mail server, on port 993.

Previously opens no port and needs nothing inbound.

## How to recognize that everything stands

1. `docker pull ghcr.io/jensens/previously:<version>` works without credentials.
2. The migration job reports the newest revision.
3. In the tools pod, `previously append --attach`, `previously blob get` and `previously verify --blobs` succeed.
4. A restore probe has run once, and `previously verify --anchors` held against the restored copy afterward.
5. The three CronJobs have each run once with exit code `0`, and the anchor file outside the database holds a line.
6. The backup of the identity lies apart from the database and the bucket, and was rehearsed once.

## Optional: a namespace for measurements

The maintainer may ask you for a temporary namespace with access of its own, restricted to that namespace.
In it, Previously's developer may start pods for measurements, such as how the image behaves under the cluster's security settings, or how long a check takes against the real bucket.
The developer will never use any other kup6s context, and nothing there touches the namespace Previously runs in.
Remove the namespace, and its access, when the maintainer says the measurements are done.
