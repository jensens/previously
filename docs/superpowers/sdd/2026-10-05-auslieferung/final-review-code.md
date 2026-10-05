# Final review, code and configuration: delivery (`d16f3fc..4a9048d`)

Reviewer: read-only on the tree, no subagent, nothing pushed.
Read: `progress.md` (every `Ruling` and every `deferred` line), `global-constraints.md`, spec §2–§11, the current `Dockerfile`, `.dockerignore`, `scripts/smoke-image.sh`, `release.yml`, `gates.yml`, `storage/migrate.py`, `migrations/{__init__,env,dsn}.py`, the diffs of `postgres.py`, `errors.py`, `cli.py`, `pyproject.toml`, `.importlinter`, `alembic.ini`, `CLAUDE.md`, `DEPENDENCIES.md`, `uv.lock`, and the tests per doubt (`test_migrate.py`, `test_wheel.py`, `test_storage.py`, `test_contracts.py`, `test_docs_references.py`, the DSN table in `test_cli.py`). Task 4's review was read so as not to repeat it.

Measured myself on 2026-10-05:

- Gates 1–5 against the project configuration: `ruff check .` clean, `ruff format --check .` 73 files formatted, `pyright` 0 errors, `lint-imports` 6 kept / 0 broken (contract names as printed are true), `pytest --cov --cov-report=term-missing` **800 passed**, total coverage 98.06 %. Gate 6 not run (the documentation reviewer's). `pip-audit --skip-editable`: no finding.
- Rules: five `noqa` (`grep -rn noqa src tests docs/conf.py`), the same five `CLAUDE.md` lists; no `# type: ignore` (the one hit is prose in `test_schema.py:297`); no mock (the `monkeypatch` uses set environment variables or a temp dir, as before); no private name imported from a test; every commit message carries `Assisted-By:` only, no `Co-Authored-By`, no "Generated with". `T201` count: 34, as `pyproject.toml` says. `tests/` holds 7 `§` in three files and `test_the_reference_quotes_what_the_code_actually_prints` stands at C901 10, as the comments in `test_docs_references.py` say.
- The image, built from a wheel of the head (`0.1.dev184`) with the `Dockerfile` as committed, 313 MB, then removed. Against a throwaway `postgres:17`: two `migrate` at once → one `migrated: (empty) -> 0004_event_blob`, one `up to date: 0004_event_blob`, both exit 0; then wrong password, missing database, unknown host, unparsable DSN, `?password=`, `postgresql+psycopg2://`, `sslmode=require` against a non-TLS server, a `connect_timeout` to a black hole, an unknown newer revision: each one line on stderr, exit 2, no traceback, the 22-character password absent. The plain `postgresql://` scheme resolves to the psycopg driver (SQLAlchemy 2.1.2).
- A throwaway `kind` cluster for Important 1, then deleted.
- Base image digest, `postgres:17` and `rustfs/rustfs:1.0.1` are all indexes with `linux/arm64`; `uv.lock` has `manylinux aarch64` wheels for every native dependency (`psycopg-binary` cp314, `pyrage` abi3, `sqlalchemy`, `markupsafe`), so the arm64 build installs no sdist.
- `uv export --frozen --no-dev --no-emit-project --no-hashes` in a directory with only `pyproject.toml` and `uv.lock` and no git: works, so the shallow checkout of the `image` job is enough for the smoke test.
- `ScriptDirectory.from_config(Config("alembic.ini"))` in the checkout resolves `previously:migrations` to `src/previously/migrations`, so `alembic revision` writes into the tree, not into a copy.
- The `setup-uv` `enable-cache: auto` claim at `release.yml:87-91`, against `action.yml` at the pinned commit: true.

### Strengths

- The DSN grammar (`postgres.py`, `_DSN`/`_url_of`) is the right end of five rounds: the operator's string is never parsed by SQLAlchemy, the URL is built with `URL.create`, and every refusal is one fixed sentence that quotes nothing. The CloudNativePG `uri` form, as Go writes it, is inside it and has a test.
- `migrate` is small and correct where it matters: the lock on its own autocommit connection, no unlock on the error path (closing the session drops it), the upgrade on a second connection handed to `env.py` through `config.attributes`, `SET CONSTRAINTS ALL IMMEDIATE` before the commit so a deferred failure is still `MigrationFailed`. Alembic sees the external transaction and leaves the commit to `storage.begin()`. The two lock tests poll `pg_stat_activity` to a deadline instead of sleeping.
- `_transaction` now separates the three cases honestly: no SQLSTATE → failed to connect, with libpq's first line; SQLSTATE → `OperationFailed`; `ProgrammingError` before the connection stood → a fixed sentence. `MigrationPending` names `previously migrate`.
- `release.yml`: explicit `!cancelled() && needs.X.result == 'success'` conditions, the tag check before any upload, `pep440` with `latest=false` (measured, ruling T4-a), the smoke test against the pushed image before the digest is exported, permissions per job, no `${{ }}` interpolated into a `run:`. Traced for its first real run (push to `main`: `fetch-depth: 0` + `local_scheme = "no-local-version"` → `0.1.devN`; release `v0.1.0a1`: tag ref matches the `pypi` tag policy, OIDC from a job in `release.yml` itself, not from the called workflow; arm64 runner free on a public repository; `openssl`, Docker and `uv` present on both runners; host uid 1001 handled by `--user`) — nothing found that would break it, beyond what Task 4's review already named.
- The smoke script runs as the host user and thereby also proves the image under a foreign uid; its version check is one-directional for a measured reason (`tzdata`).
- Coverage by path (ruling T1-c) is the honest number, and the comment says why.

### Issues

#### Critical

None.

#### Important

1. **`Dockerfile:28` — a non-numeric `USER` stops a pod that sets `runAsNonRoot: true` without `runAsUser`.**
   What: `USER previously` is a name. Kubelet cannot verify a name is not root, so it refuses to start the container.
   Measured in a `kind` cluster with the image as built: `runAsNonRoot: true` alone → `CreateContainerConfigError`, "container has runAsNonRoot and image has non-numeric user (previously), cannot verify user is non-root"; with `runAsUser: 1000` beside it → `Completed`.
   Control: the same image with `USER 1000:1000` and `runAsNonRoot: true` alone → `Completed`, prints the help.
   Why: `runAsNonRoot` is what the Kubernetes "restricted" pod security profile asks for, so kup6s hits this in ordinary use; and the handoff says the opposite (`docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md:55`: "`runAsUser`, `runAsNonRoot` and `readOnlyRootFilesystem` are all fine").
   How: `USER 1000:1000` (the `groupadd`/`useradd` lines stay, so `id` still names the user). The smoke test's `id -u` = 1000 check is unaffected. The handoff sentence then holds as written.

2. **`Dockerfile:17` — no bytecode in the image, and user 1000 cannot write any: every command compiles its imports from source.**
   What: `uv sync` and `uv pip install` do not compile by default; the venv belongs to root, so Python's `__pycache__` writes fail silently at every start.
   Measured, three runs each, `previously log` against a migrated database from inside the container: 1.93 s as built, 0.73 s with the site-packages compiled; image 313 MB → 333 MB.
   Why: ordinary use — every Job, CronJob (`project` "in short intervals", spec §6) and `kubectl exec` pays 1.2 s, and the pilot's ingest will call the image per run. It also dwarfs the 70 ms import of `alembic` that ruling T2-e set aside.
   How: `ENV UV_COMPILE_BYTECODE=1` before the `uv sync` line; it applies to the `uv pip install` too.

3. **`Dockerfile:30-32` — the published image claims to be `uv`.**
   What: only `source`, `licenses` and `version` are set; `title`, `description`, `url`, `revision` and `created` are inherited from the base image. Measured with `docker inspect`: title "uv", description "An extremely fast Python package and project manager, written in Rust.", url `https://github.com/astral-sh/uv`, revision `46b84fd…` (a uv commit), created 2026-10-03.
   Why: this is published metadata on every release, and `revision` points provenance at another project's commit — the same class as a false comment, in output. The implementer named it (handoff, map), but under the working rule it arises in ordinary use, not misuse.
   How: set `title`, `description` and `url` in the `Dockerfile`; set `revision` from `github.sha` (a build argument, or the `labels:` input of `build-push-action`) and either set `created` the same way or blank it. Unmeasured, for the package page: for a multi-platform image GHCR reads the description from the index, `docker buildx imagetools create --annotation "index:org.opencontainers.image.description=…"` in `manifest`.

#### Minor

1. **`.github/workflows/release.yml:6-9`, `:34`, `:40`, `:83-85` — four comments that claim more than is true** (Task 4 review, Minor 1–4, deferred to here): `tag` runs beside `gates`, not after it; `cancel-in-progress: false` still cancels a *pending* run; a job-level `permissions:` replaces the default, it does not widen it; before the first tag the version on `main` is `0.1.devN`, not `0.1.0a2.dev3`. Fix the four sentences.
2. **`src/previously/storage/migrate.py:93-96` — the docstring says the connection failure sentence "names database, host and port and nothing else of the string".** Measured: `Error: connecting to database app at rvw-pg:5432 failed: connection to server at "10.200.6.2", port 5432 failed: FATAL:  password authentication failed for user "app"` — libpq's line names the user. The pages were corrected for exactly this in fix round 3 (task 2); this docstring was not. Say "names database, host and port, and quotes the first line of libpq's reason, which can name the user".
3. **`src/previously/storage/postgres.py:909-911` (`_unreadable` docstring) — "every part takes the escape"**: scheme, host and port take none (`_DSN`). Deferred from task 2. "every part but scheme, host and port".
4. **`scripts/smoke-image.sh:39-44` — "the key could not be removed"** describes fix round 1's 0777 directory. With `mktemp -d` (0700, owned by the host user) a container running as uid 1000 on a host with another uid could not write into `$WORK` at all. Deferred from task 3. Say that instead.
5. **Four new ruling citations without their plan**: `src/previously/storage/postgres.py:1020` (T2-j), `tests/test_cli.py:637` (T2-l), `tests/test_cli.py:665` (T2-j), `tests/test_migrate.py:521` (T2-l). `CLAUDE.md` (*A ruling citation is provenance*) asks a new citation to name the plan's date, and the ledger they point at is `.superpowers/sdd/2026-10-05-auslieferung/progress.md`, which `.gitignore` excludes (`git check-ignore`: `.gitignore:24`). Each reason stands beside its label, so nothing collapses; but before the merge the ledger ships under `docs/superpowers/sdd/2026-10-05-auslieferung/` (as stage 1c's did in `681e6a5`) and the four become `ruling T2-j of the 2026-10-05 delivery plan`.
6. **`DEPENDENCIES.md:32` — hatchling "builds the wheel in its own process"** reads as a subprocess, while `tests/test_wheel.py`'s docstring says it builds "in this process … no subprocess". "in the test's own process".
7. **`Dockerfile:34` — `previously` runs as PID 1 and ignores SIGTERM.** Measured: `docker stop -t 10` on a waiting `log` took 10.2 s and ended with 137 (SIGKILL). A deleted Job or a `compose` stop waits the whole grace period. Harmless for short commands; name it in the handoff (`docker run --init`, or an init in the image), or leave it named.
8. **Session-level lock and a transaction-mode pooler** (unmeasured, from how PgBouncer works): if kup6s ever points `PREVIOUSLY_DSN` at a CloudNativePG `Pooler` in transaction mode, `pg_advisory_lock` and `pg_advisory_unlock` can land on different server connections, and a lock left on a pooled server connection would make every later `migrate` wait. The handoff asks for no pooler, so nothing breaks today; one sentence there ("`migrate` connects to the `-rw` service directly") closes it.
9. **The release wheel is built by an unlocked backend.** `uv build` resolves `[build-system] requires = ["hatchling", "hatch-vcs"]` fresh, so what reaches PyPI is built by whatever hatchling is current that day, not the 1.32.4 that `uv.lock` holds and `test_wheel.py` uses. Not a second pin, an absent one; name it, or constrain the build (`uv build --build-constraint …`).
10. **`CLAUDE.md:11-17`, the English list** names `src/`, `tests/`, `.github/` and the root configuration by file, but not `scripts/`, the `Dockerfile` or `.dockerignore` (all English today). Related: the `` {ref}`delivery` `` in the `Dockerfile` (ruling P-1) is outside `test_docs_references.py`'s `*.py` field of view, so a renamed label would leave it stale silently.
11. Misuse, named only: two rows in `alembic_version` (a hand edit or a branched history) make `migrate` end in a traceback with exit 1 (`CommandError` from `get_current_revision`), measured; no password in it.

### Deferred findings

| Source (ledger) | Finding | Verdict |
|---|---|---|
| Task 1 | `module-boundaries.md:183`/`:188`, old blocks marked as history only at `:105` | **leave named** — documentation, the other reviewer's |
| Task 2, ruling T2-e | `statement_timeout` reported as "does not answer" | **already gone** — `OperationFailed` (`postgres.py`, SQLSTATE branch), test `test_cli_migrate_names_an_error_after_connecting_as_one_of_the_operation` |
| Task 2, ruling T2-e | importing `alembic` costs every command ~70 ms | **leave named** — but see Important 2, which costs 1.2 s and is the thing to fix |
| Task 2, fix round 1 | autocommit and "no unlock on the error path" each prevent the masking; the test goes red only when both are gone | **leave named** — two independent guards are a strength; a test per guard would need a fault injection the no-mock rule forbids |
| Task 2 → task 5 | rest (3): `sslrootcert`, `sslkey` quoted by libpq | **already gone** in the code (`_url_of` docstring names both, measured cases); `cli.md:14` is the documentation reviewer's |
| Task 2 | `_unreadable` docstring "every part takes the escape" | **fix now** — Minor 3 |
| Task 3 | `trap` after `mktemp` | **already gone** in effect — `trap` is the next line after `mktemp`, nothing between them can fail; in the map (`landkarte.md:396`) |
| Task 3 | `uv` and `openssl` not named in the script header | **leave named** — `run-the-image.md` and the map say it; `release.yml` provides both |
| Task 3 | an abort can leave a `--rm` container and the network | **leave named** — ephemeral runners; in the map |
| Task 3 | `useradd --system` warning for uid 1000 | **leave named** — harmless, in the map |
| Task 3, fix round 2 | the comment over `run()` says "the key could not be removed" | **fix now** — Minor 4 |
| Task 3, fix round 2 | rootless Docker maps `--user` to a subuid; a host uid 0 runs the image as root | **leave named** — the uid-1000 check runs without `--user` and still holds |
| Task 4 | four comments in `release.yml` | **fix now** — Minor 1 |
| Task 4 → task 5 | nothing checks the built version against the tag; `latest` moves back for an older line; the wait polls the JSON API, the install reads the simple index | **leave named** — named on `cut-a-release.md:55`, `:92`, `:138-139` and `delivery.md:48-49`, `:85`; each fails safe or is irrelevant before a maintenance line exists |

### Declined to judge

- The documentation, the handoff's prose beyond the one false sentence in Important 1, and gate 6: the other reviewer's.
- Behavior of GitHub that only a run on `main` can show: OIDC claims as PyPI receives them, the environment deployment policies on the `release` event, `imagetools create` over two indexes that carry provenance attestations. Reasoned from documentation and Task 4's API checks, not measured; spec §11 condition 8 is where they get measured.
- The 58-form DSN table in `test_cli.py` line by line: five rounds of attack reviews measured it; I re-ran a dozen forms through the built image and found nothing new.

### Assessment

**Ready to merge: With fixes.**
Nothing is critical, and the code behind `migrate` and the DSN is in good shape — every failure I drove through the image was one sentence, exit 2, with no password and no traceback.
The three Important findings all sit in the `Dockerfile`, cost a line or three each, and all three arise in ordinary use: a pod under `runAsNonRoot` that won't start, 1.2 s added to every command, and image metadata that names another project.
The Minor ones are false comments and citations, cheap enough to go in the same fix wave.
