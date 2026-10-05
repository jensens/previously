# Final review — English documentation and handoff, d16f3fc..4a9048d

Reviewer: Opus, read-only on the tree, 2026-10-05. Also the task review of task 5 (ruling E-1).
Package: `final-docs.diff`, read in full; every page held against `src/previously/cli.py`, `storage/postgres.py`, `storage/migrate.py`, `Dockerfile`, `release.yml`, `scripts/smoke-image.sh`.

What I ran (nothing in the tree changed; `git status` clean afterward):

- `uv run previously --help`, `migrate --help`, `verify --help`: eleven subcommands, `--help` exits 0.
- `make -C docs html` (succeeded), `make -C docs vale` (0 errors, 0 warnings, 0 suggestions in 31 files). Not `linkcheck`.
- `uv run lint-imports`: the six contract lines match `module-boundaries.md:93-101` verbatim.
- The tutorial's test block against `pytest --collect-only`: per-file counts identical for all 31 files, sum 800.
- `grep -rn "§" src tests | grep -v "frozen design record"`: empty; 15 lines in 7 files, as `design-records.md` says.
- Map count with the `CLAUDE.md` command: 99 at `d16f3fc`, 117 at head, as reported.
- `gh api …/environments`: `pypi` and `testpypi` exist; their policies print exactly the two lines `cut-a-release.md:26-27` shows; `pypi` has no required reviewer. `pypi.org/pypi/previously/json`: 404.
- SQLAlchemy 2.1.2: `create_engine('postgresql://…').dialect.driver` is `psycopg`; `psycopg2` is not installed.
- **A schema one revision behind** (throwaway `postgres:17`, `alembic upgrade 0003_hash_version_2`, removed afterward): `previously append` (no attachment) exit 0, `log` exit 0, `project` exit 0 (built both projections), `verify` exit 2 with the "schema incomplete" sentence, then `migrate` printed `migrated: 0003_hash_version_2 -> 0004_event_blob`.
- `docker image inspect previously-review:local` (the code reviewer's image, `Dockerfile` of this head): `User=previously`, no health check, volumes or ports; in it `/bin/sh` (dash) and `/usr/bin/sleep` exist, `curl`, `wget` and `aws` don't.

### Strengths

- The handoff keeps to *what, why, how to recognize it* throughout; there is no line of cdk8s, no manifest, no Helm, and every section ends in a checkable "It stands when".
- The secret split is exactly spec §6, and right against the code: the identity only for the tools pod and the nightly `verify --blobs`, the recipient only for whoever ingests, the five bucket settings for whoever writes, reads or deletes blobs, `redact` included. The "Read by" column matches `configuration.md` and `cli.py` (`_blob_store`, `_recipient`, `_identities`, `_delete_obsolete`).
- The connection string section answers the kup6s question precisely: percent-encoding, the CloudNativePG `uri` accepted as is (with the measurement and the source fact about its passwords), `password` refused in the query, the eight keys. It also warns that libpq's line can name the user.
- `configuration.md`'s grammar table and bullets match `_DSN`, `_USERINFO`, `_PART`, `_VALUE`, `_LABEL`, `_REFUSED_CATEGORIES` and `DSN_QUERY_KEYS` character for character; the misuse table carries every residual of rulings T2-j and T2-m, plus the TLS keys handed to task 5, measured rather than copied from the ledger (`sslcert` alone dropped, with a reason).
- `delivery.md` gives real reasons, not restatements: the price of installing from PyPI, `tzdata` as the measured cause of the one-way check, `pep440` against `semver` as a measurement, the session lock and why it needs no cleanup, the tag check moved before the upload.
- The release how-to covers the tag forms, the leading zero, `latest` moving back, the JSON-versus-simple-index lag and the ghcr.io visibility step; the deferred task-4 points all have a home on a page.
- Every operator-facing `alembic upgrade head` is gone outside `docs/superpowers/` (only `add-a-migration.md` and the tutorial had one at the base); the tutorial is retyped consistently, and its test block agrees with the tree file by file.
- Ruling P-1 is honored: `{ref}`delivery`` in `storage/migrate.py` (gate-checked) and in the `Dockerfile` comment.

### Issues

#### Critical

None.

#### Important

1. **`runAsNonRoot` doesn't work as the handoff promises.**
   `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md:42` and `:55` ("So `runAsUser`, `runAsNonRoot` and `readOnlyRootFilesystem` are all fine").
   *What:* the image's user is a **name**: `Dockerfile:28` `USER previously`, confirmed by `docker image inspect` (`User=previously`).
   The kubelet refuses `runAsNonRoot: true` for an image whose user is non-numeric unless the pod also sets `runAsUser` ("container has runAsNonRoot and image has non-numeric user (previously), cannot verify user is non-root"); that's kubelet behavior, not measured here, since there's no cluster to measure against.
   *Why:* `runAsNonRoot` is what the Pod Security "restricted" profile requires, so it's the first setting the kup6s agent reaches for, and the handoff tells it that's fine on its own.
   Every pod would then fail with `CreateContainerConfigError`.
   *How:* better in the code, `USER 1000:1000` in the `Dockerfile` (the smoke test's `id -u` = 1000 check still holds, and the handoff's sentence becomes true).
   Otherwise the handoff says that `runAsNonRoot` needs `runAsUser` set alongside it, because the image names its user.

2. **"Every other command refuses a database whose schema is behind": measured false.**
   `handoff:153`, `docs/how-to/run-the-image.md:74`, `docs/how-to/cut-a-release.md:73`, `docs/explanation/delivery.md:73-74`; `handoff:158` reads the same way, because its bold sentence stands without the word `migrate`.
   *What:* there's no revision check outside `migrate`.
   `MigrationPending` is raised only when a statement hits a `ProgrammingError` (`storage/postgres.py:280-302`), so a command that doesn't touch the missing table or column runs.
   Measured at revision 0003 against head 0004: `append`, `log` and `project` exit 0, and only `verify` refuses.
   By the same mechanism, an older image's commands run against a newer schema; only its `migrate` refuses (`UnknownRevision`).
   So `cut-a-release.md:73`'s "an older image refuses a database a newer one has migrated" and `delivery.md:74`'s "Silence there would let an older image run against a schema it doesn't know" both promise a guard that exists only in `migrate`.
   *Why:* the handoff presents "migrate first" as protected by a refusal, and the release notes rest on the same claim.
   With a future migration that adds a constraint or a default rather than a table, a forgotten migration job would write silently.
   The release how-to and the handoff are where an operator decides how strict the ordering has to be.
   *How:* say what the code does: `migrate` is the only command that compares revisions.
   Any other command fails with the "schema incomplete" sentence only where it touches a table or column the schema lacks, so the migration job's order is the guard, not the commands.
   If that's not good enough, the alternative is a revision check in `_storage()`, which is a decision for the maintainer and the code review, not for this wave.
   `cli.md:43` ("against a database without it") is accurate and can stay.

3. **The `publish-pypi` row leads to a rerun that cannot succeed.**
   `docs/how-to/cut-a-release.md:138`: "If it's there, continue as for `image`."
   *What:* when `publish-pypi` fails, `image` and `manifest` are skipped.
   The `image` row's first remedies are "rerun the failed jobs", and a rerun repeats `publish-pypi`.
   That job has no `skip-existing` (`release.yml:134-135`, on purpose), so a file already on PyPI fails the upload again, every time.
   This run can't produce an image for that version.
   *Why:* this is the step the brief singles out ("welcher Schritt hat was schon veröffentlicht"), and the reader is the maintainer in the middle of a failed release.
   *How:* split the row.
   If the version isn't on PyPI, fix the cause (such as a missing trusted publisher) and rerun the failed jobs.
   If it is, even partly (one of the two files), this version stays on PyPI without an image: fix the cause on `main` and release the next version.

#### Minor

1. **`readOnlyRootFilesystem` is claimed beyond what was measured.**
   `handoff:54-56`: the measured set was `migrate` with `--user 12345:12345 --read-only`, and `append`, `verify`, `project`, `anchor` with `--read-only` (task-5 report).
   No blob command (`append --attach`, `verify --blobs`, `blob get`) ran with a read-only root.
   The claim is likely true, since boto3 and pyrage write nothing, but either measure those three or say which commands were measured.

2. **"Network out" omits the database.**
   `handoff:201-206` lists the S3 server and the mail server.
   An agent that builds a default-deny egress policy from this list cuts PostgreSQL (the CloudNativePG `-rw` service, port 5432) and DNS.
   Add both, and the place the anchor file lives if that's outside the cluster.

3. **The anchor file has no way in or out of the image.**
   `handoff:184-191`: the routine says "fetch the anchor file … put the file back", and the nightly `verify --anchors - --blobs` needs the same file on standard input, which the bullet doesn't say.
   The image has `/bin/sh` (dash), `sleep`, Python with boto3 and `uv`, but no `curl`, `wget` or `aws` (measured).
   The agent should hear that the fetching and putting back happen outside the `previously` container, or with a tool it brings.
   That's a *what*, not a *how*.

4. **Trusted publishers are stated as set up.**
   `handoff:19-22` ("The maintainer has set up the publishing side …") and `cut-a-release.md:13` ("it's in place").
   The environments are set up (measured above).
   Spec §11 condition 8 and plan "Nach Aufgabe 5", point 5, schedule trusted publishing *after* the merge, and nothing measured that it exists.
   Spec §9 asks the release how-to for "das einmalige Einrichten aus §3.4".
   Say that the environments exist, and have the page say what to enter if the publisher is missing.
   The page already names every value the PyPI form needs, plus the project name `previously` for a pending publisher.

5. **`imagetools inspect` before the package is public needs a login.**
   `cut-a-release.md:114`: on the first release the package is still private, so `docker buildx imagetools inspect` fails unless the maintainer is logged in to `ghcr.io`.
   Move the check after "Make the image public, once", or name the login.

6. **The digest artifacts expire after one day.**
   `cut-a-release.md:139-141` ("rerun the failed jobs" for `image` and `manifest`): `release.yml:263` keeps them for `retention-days: 1`.
   A rerun more than a day later finds one or both digests gone, and `manifest` fails.
   One sentence on the page would cover it.

7. **The tutorial's `+psycopg` sentence is stale.**
   `docs/tutorials/record-your-first-event.md:48-49`: "without it SQLAlchemy reaches for one that isn't installed here".
   That's false with SQLAlchemy 2.1.2, whose default PostgreSQL driver is `psycopg` (measured).
   Since this branch, `postgresql://` is an accepted form that `configuration.md` and the handoff promise for the CloudNativePG `uri`.
   The sentence predates the branch, but the branch made it contradict two pages.

8. **Tag statements in `delivery.md` disagree with each other and with the how-to.**
   `delivery.md:46` says "each image has exactly one tag, its version", but the intermediate `-linux-<arch>` tags exist (the handoff says so).
   An alpha published *without* the pre-release mark gets `latest`, which the page itself says (the mark decides).
   `delivery.md:85` lists "a tag on a commit that carries a second tag" as a mistake that passes the check, while `cut-a-release.md:58` calls the same case safe, measured, and the map says "scheitern sicher".
   Make the three agree, for example: it passes the check and does no harm.

9. **`configuration.md:29-32` leaves out a few things the grammar refuses.**
   A password needs a user name: `postgresql://:pw@host/db` is refused, while libpq would take it.
   Query keys are lowercase only, a value can't be empty, and a host may end in `.`.
   Only the first is likely to cost an operator time.

10. **A task-3 deferral to name is missing.**
    The ledger (`progress.md:116`, task 3, "deferred, benennen") says rootless Docker maps `--user` onto a subuid, and a host running as uid 0 runs the smoke test's containers as root.
    It's named neither in the map nor on a page.

11. **The bucket's S3 operations aren't listed.**
    `handoff:79`: "access credentials … that reach that bucket and nothing else".
    If the agent writes that as a per-operation policy, it needs `HeadObject`, `PutObject` with multipart (`upload_fileobj`), `GetObject` and `DeleteObject` (`storage/s3.py:175-244`).
    On AWS-like servers it also needs `ListBucket`, or a missing object answers 403 instead of 404, and `append --attach` of new content fails.
    That's AWS semantics, unmeasured against kup6s's store, so it belongs in the handoff as a note, flagged as unmeasured.

### The handoff, as its reader

Read as the kup6s agent, with only this file and the repository:

- **Acts without guessing:** where the image lives, which tag to pin and why, the platforms, the entry point and the sleep override, uid 1000, no ports or volumes, the database (CloudNativePG, version 17, at least 15), the restore probe and its check, the bucket without versioning or object lock with its check commands, each variable and who gets it, the encoding of `PREVIOUSLY_DSN` and that the CloudNativePG `uri` goes in unchanged, the migration job with its output, exit codes and lock, the tools pod and what to run in it, the three CronJobs with `Forbid`, their schedules, exit-code semantics and alarm, the recognition checklist.
- **Would fail on the first try:** `runAsNonRoot` (Important 1).
- **Would have to guess:** where the anchor file comes from and how it gets into and out of a container that has no fetch tool, for the daily job and the nightly one alike (Minor 3); egress to the database (Minor 2); which S3 operations a narrow credential needs (Minor 11); that the identity files of a mounted secret have to be readable by the pod's uid.
  With a restrictive `defaultMode` the files are root-owned and unreadable by 1000, but `blob get` then names the path and the kind of failure, so the agent would find it quickly.
  A half-sentence would save the round.
- **Would rely on a false promise:** that a forgotten or late migration job gets refused by every other command (Important 2).
- **Builds nothing here:** no cdk8s, no manifest; "a Deployment", "CronJob", `concurrencyPolicy: Forbid` and "a sleep as command" are spec §6's own *what*.
  The optional measurement namespace goes beyond spec §6, but it's a request with a scope and an end, not a build instruction.
- **No secret and no secret-shaped placeholder:** confirmed.

### Declined to judge

- That a new ghcr.io package is private, that `gh run rerun --failed` reruns the dependents of the failed jobs ("including dependencies" in gh 2.99.0's help, and GitHub's documented behavior), and that `workflow_dispatch` needs the file on the default branch: all consistent with GitHub's documentation as I know it, and none measurable before the merge.
- Whether a trusted publisher exists on PyPI or Test-PyPI: needs the maintainer's account.
- The CloudNativePG `uri` shape and password generator: taken from the task-2 attack 3 measurement and its source reading, not rechecked.
- The image's inherited `uv` labels: reported by task 5 and named in handoff and map; not inspected beyond `User`, `Entrypoint` and `Cmd`.
- `make -C docs linkcheck`: not run (network); the report says it was clean.
- The German map entries beyond the count, the *Auslieferung* section and the deferrals: the map is maintained German prose, outside the English pages' brief.

### Assessment

**Ready to merge: with fixes.**
0 Critical, 3 Important, 11 Minor.
The three Important ones are in the two documents an operator acts on: the handoff and the release how-to.
Each is a few sentences; Important 1 is better fixed with one line in the `Dockerfile`.
Important 2 is the one to decide consciously: fixing the wording is enough for this branch, and a revision check in the commands would be a code change, which is the maintainer's choice.
