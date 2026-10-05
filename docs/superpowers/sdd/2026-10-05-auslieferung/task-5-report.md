# Task 5 — report

Status: **DONE_WITH_CONCERNS** (concerns at the end; none blocks).
Base `4d7e4b9`, five commits:

| Commit | Subject |
|---|---|
| `edc284a` | handoff: what kup6s needs to run Previously from its image |
| `61768c7` | docs: delivery gets its pages — the release, the image, and why |
| `fc006d2` | map: delivery as unit 0 of the pilot, and the points it leaves open |
| `13fe7f8` | spec: the delivery specification freezes, its pages stand |
| `4a9048d` | docs: the tutorial is retyped with previously migrate, 800 passed |

All with `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`, files staged by name, messages in `task-5-commit-msg-<n>.txt`. Not pushed. `scripts/smoke-image.sh` untouched.

## Per file

**`docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md`** (new, English). Spec §6 point by point, each with what / why / "It stands when": the setup before the first image (environments and trusted publishers as existing state; ghcr.io package private after first push, made public once, or a pull secret); the image (table: location, platforms, tags stable vs. pre-release, entry point, uid, no ports); PostgreSQL via CNPG with WAL archive and restore probe (`restore-from-a-backup`, `verify --anchors`); the bucket (no versioning/object lock, own credentials, backup retention is part of the erasure promise); secrets table with the reading commands copied from `configuration.md`; the connection string (percent-encoding, CNPG `uri` accepted as is — measured by the task 2 attack, `&$,;` → `migrate` 0; no `password` in the query; the eight allowed keys); the identity (directory, one file per recipient, `AGE-SECRET-KEY-1…`, only tools pod and nightly `verify --blobs`, ingest needs none, backup apart); migration job (output lines, exit 2 for an older image, lock); tools pod (`sleep infinity`, `/usr/bin/sleep` measured in the image); three CronJobs with `Forbid`; network out; a six-point "recognize" checklist; closing section "Optional: a namespace for measurements".
Added from measurement (this task, local image `0.0.0.dev0`): `migrate` under `--user 12345:12345 --read-only`; `append`, `verify`, `project`, `anchor` under `--read-only`; `verify --anchors -` through `docker run -i`; only `blob get` writes (temp file in the output directory). Also named: the inherited `uv` labels (see concerns). No secret, no secret-shaped placeholder.

**`docs/explanation/delivery.md`** (new, label `(delivery)=`). Why the image installs from PyPI (and the price); why the lock check is one-directional (`tzdata`); why no `latest` for alphas, decided by the release mark; why no `<major>.<minor>` for a pre-release (ruling T4-a, `pep440` vs. `semver`); `latest` follows the release published last (older line moves it back); why the migrations ship in the package; why `migrate` takes the session lock; why the tag check precedes the upload, and what it does not catch (built version vs. tag: leading zero, two tags on a commit); why no token (trusted publishing + environment policies).

**`docs/how-to/cut-a-release.md`** (new). Check the setup (two `gh api` commands with their output, typed from a run on 2026-10-05; trusted publishers; last run on `main`); that the workflow can't run by hand before the merge (spec §10 point 7 vs. plan decision 1); the tag forms; leading zero; nothing compares built version and tag; rc→final on one commit safe; operator notes (`git diff --name-only --diff-filter=A <last tag> main -- src/previously/migrations/versions/`); the command `gh release create v0.1.0a1 --prerelease --generate-notes --target main`, and `--notes` (prepends, from `gh release create --help`, gh 2.99.0); tags by mark; `latest` moving back; jobs in order; `docker buildx imagetools inspect`; make the package public once; failure table per job (what is published, what to do), including the JSON-API-vs-simple-index lag with "rerun failed jobs" (`gh run rerun <id> --failed`, flag checked against `--help`).

**`docs/how-to/run-the-image.md`** (new). Choose the image (pin the version), the network and database, `-e PREVIOUSLY_DSN` pass-through, `migrate` first (both output lines), one `docker run` per command, the anchor pair with `-i`, attach and fetch with `--user "$(id -u):$(id -g)"` and the identities mounted read-only, local build from a wheel and the smoke test, cleanup. **Every command on the page ran** on 2026-10-05 against the local image tagged for the run as `ghcr.io/jensens/previously:0.1.0a1` (tag removed afterwards), with RustFS and the bucket from `run-a-blob-store-on-your-machine`, key from the image's `pyrage` (no `age-keygen` on this host): `migrate` 0 twice, `append` 1, `project`, `verify`, anchor routine 0, `append --attach` 2, `blob get` "wrote 17 bytes", `cmp` equal, file `-rw-------` owned by the host user. The smoke test against `previously:local`: `smoke test passed: previously:local`, nothing left behind.

**Indexes:** `how-to/index.md` (+`run-the-image`, `cut-a-release`), `explanation/index.md` (+`delivery`), `docs/index.md` (both cards).

**`README.md`:** new section *Install* (`pip install --pre previously`, the image with exact tag, `migrate` first, links to the two how-tos); one sentence in *State*; in the freeze commit: "seven specifications" and a row for the delivery record. "eleven commands" was already there (task 2).

**`docs/reference/configuration.md`** and the `_url_of` docstring (`storage/postgres.py`): residual 3 now names `sslrootcert` (with `sslmode` `verify-ca`/`verify-full`) and `sslkey` (beside an `sslcert` that names a certificate). **Measured** on 2026-10-05 with `postgres:17 -c ssl=on` (snakeoil certificate) and `uv run previously log`, the value a 23-character fake password: `sslrootcert` quoted under `verify-ca` and `verify-full` (`root certificate file "<SECRET>" does not exist`), silent under `prefer`, `require`, unset; `sslcert` alone silent in every mode (a missing client certificate is skipped); `sslkey` quoted under `require` beside an existing `sslcert` (`certificate present, but not private key file "<SECRET>"`), silent under `prefer` (falls back to no TLS). So the ledger's "also `sslcert`" is not borne out; the page and docstring name what was measured. `cli.md:14` ("lists each such case") is true with it.

**Ruling P-1:** `{ref}`delivery`` added to the module docstring of `storage/migrate.py` and to the `Dockerfile` comment. `test_every_doc_reference_in_the_code_resolves`: green; mutation (label renamed to `delivery-x`) red with `{'delivery': ['src/previously/storage/migrate.py']}`; reverted. The `Dockerfile` reference checked by hand (no gate reads it).

**`docs/explanation/design-records.md`:** seven records, the last two froze on 2026-10-05; a paragraph on the delivery record (pages that took reasoning, facts, routines; the handoff; the first record a page contradicts on the day it froze — §10 point 7, with `cut-a-release` saying how it is); "No row names the specification of delivery either", measured: `grep -rn "§" src tests | grep -v "frozen design record"` prints nothing, 15 lines in the same 7 files.

**`docs/tutorials/record-your-first-event.md`:** see *Typed blocks*.

Changes under `src/`: exactly the `{ref}` in `migrate.py` and the one bullet of the `_url_of` docstring. Nothing else.

## Typed blocks and their runs

| Page | Block | Run |
|---|---|---|
| `cut-a-release.md` | the two `deployment-branch-policies` lines | `gh api` against `jensens/previously`, 2026-10-05 |
| `run-the-image.md` | `migrated: (empty) -> 0004_event_blob`, `up to date: 0004_event_blob`, `smoke test passed: previously:local` | the page's commands against the local image; `bash scripts/smoke-image.sh previously:local` |
| `tutorial` | `uv sync` (109 resolved, 106 installed, times), `migrate`, `append`, `log`, `verify`, `anchor`/`verify --anchors`, `show 1`, `project` ×2, `chronicle`, `stats` | fresh `git clone` of `13fe7f8` into the scratchpad, fresh `postgres:17` on 5432, 2026-10-05 18:31 UTC; the `verify` line order measured again under `script` (a pseudo-terminal): `chain intact` first, as before |
| `tutorial` | the test block, 800 passed in 94.38s, seed 1887216001 | `uv run pytest` in the worktree with an uncommitted `PLACEHOLDER` in place of the block (no count on the page), exit 0; typed whole, without the `rootdir:` line |

The handoff's two output blocks (`migrated:`/`up to date:`, the unknown-revision sentence) are copied from `cli.md` (the latter with its `0005_example`), not typed from a run.

## The map

Count with the command in `CLAUDE.md`: **99 before, 117 after** (+18).

Changed outside the open points: 1c moved to the accepted table (PR #5, `d16f3fc`) — it was still listed as "built, accepted with the merge"; delivery as built, accepted with the merge of `worktree-auslieferung` (true before and after the merge), with condition 8 after it; the pilot table gets unit 0 (delivery, spec frozen 2026-10-05); unit 2 "beginnt beim Image aus Einheit 0 … der Handoff liegt"; the kup6s question answered for unit 2; the *Was vor was* row and the *Zwei Stücke* paragraph updated. Legend: **AL**, **P-AL**.

Added (18):
- New section *Auslieferung* (10): AL §12 points 1, 2, 6 (point 6 with condition 8 and the impossible trial run before the merge); built version vs. tag (task 4 minor); `latest` moving back (task 4 minor); JSON API vs. simple index (task 4 minor); pre-release only `<version>` (ruling T4-a); the four `release.yml` comment minors (task 4, deferred to the fix wave — listed so they have a home; strike them there if fixed); the four smoke-script minors (task 3); the inherited `uv` labels (new, this task).
- *Betrieb* (+1): AL §12 point 3 (`migrate` only forward). AL §12 point 4 folded into the existing anchor-location point (no new bullet).
- *Kommandozeile* (+4): the DSN grammar's named limits as one point (rulings T2-j, T2-k, T2-m, residuals incl. the TLS keys, `alembic` in a checkout); the `_unreadable` docstring claim (task 2 minor); the 70 ms `alembic` import (ruling T2-e); a COMMIT error escaping `_refusals` (task 2 round 5 concern).
- *Tore und Werkzeuge* (+3): ruling T1-d (import-linter doesn't read `versions/`); `module-boundaries.md` old blocks (task 1 minor); the two lock mechanisms and the one test (task 2 minor).
- AL §12 point 5 went into the existing MCP bullet (no new bullet).

Reworded: the operations point "Deployment-Mechanismus; Image; …" (image built, rest with the kup6s agent); the 1b-operator point (migration is now said; format 1 stays open); "zehn Kommandos" → "elf". Struck into *Erledigt*: `~~Image~~` with commits `aa5ee8c`, `ea7ceb2`, `05372db`, `4d7e4b9`.
Not added because closed: the `statement_timeout` minor (round 2 gave it its own sentence) and the task 2 → task 5 minor on TLS keys (closed in `61768c7`).

## The freeze diff

`docs/superpowers/specs/2026-10-05-auslieferung.md`, 20 insertions, 3 deletions: the 12-line blockquote header copied verbatim from the stage 1c record (date `2026-10-05`); the status line (`eingefroren am 2026-10-05; zuvor Entwurf, vom Betreuer am 2026-10-05 durchgesehen, Grundlage des Plans …`); the introduction of §12 in the past tense, worded like the 1c record. Nothing else; §10 point 7 stays as it was.

## Gates (final tree, `4a9048d`)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            73 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        800 passed in 90.85s; Total coverage: 98.06%
make -C docs html                       build succeeded.
make -C docs vale                       ✔ 0 errors, 0 warnings and 0 suggestions in 31 files.
make -C docs linkcheck                  build succeeded; _build/linkcheck/output.txt empty
uv run pip-audit --skip-editable        No known vulnerabilities found
```

Every container, network and image started here is removed (`previously:local` included; it was rebuilt from cache, 313 MB).

## Concerns

1. **The image's labels describe `uv`.** `docker image inspect` shows `org.opencontainers.image.title` = `uv`, `description` = "An extremely fast Python package and project manager…", `url` = astral's, `revision` = uv's commit — inherited from the base. `source`, `licenses`, `version` are ours. Named in the handoff and the map; fixing it means three `LABEL`s in the `Dockerfile`, outside my file list.
2. **The ledger's `sslcert` is not borne out by measurement** (above); I named `sslrootcert` and `sslkey` only, with the conditions. If the controller wants `sslcert` named too, there is no run that shows it quoted.
3. **The `release.yml` comment minors are in the map** although they're slated for the fix wave; strike them there with the commit if fixed.
4. The tutorial's commands ran in a fresh clone, its test block in the worktree (with the placeholder, as the trick needs a tree that holds the page); the `rootdir:` line is left out either way.
5. A few handoff and page statements rest on GitHub/CNPG behavior not measured here: workflow_dispatch needs the file on the default branch (plan decision 1); a new ghcr.io package is private; on PostgreSQL 15+ the database owner may create in `public`; `gh run rerun --failed` re-runs dependents (gh's help says "including dependencies").
6. In the map I moved 1c into the accepted table (it was merged as PR #5 but the map still said "accepted with the merge"); not asked for, but the map is maintained and was wrong.
