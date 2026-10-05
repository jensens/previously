# Task 3 report: image and smoke test

Status: DONE_WITH_CONCERNS. Commit `aa5ee8c` (Dockerfile, .dockerignore, scripts/smoke-image.sh; the script is mode 755).

## Build (last lines)

```
#11 [stage-0 5/6] RUN --mount=type=bind,from=wheels,target=/wheels uv pip install ... "previously==0.0.0.dev0"
#11 0.706 Resolved 1 package in 303ms
#11 0.760  + previously==0.0.0.dev0
#12 [stage-0 6/6] RUN groupadd --system --gid 1000 previously && useradd ...
#12 0.285 useradd warning: previously's uid 1000 is greater than SYS_UID_MAX 999
#13 naming to docker.io/library/previously:local done
```

Wheel: `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0 uv build --wheel` gave `previously-0.0.0.dev0-py3-none-any.whl`.
Image size: 313 MB (`docker images`). The image was removed afterwards.

The `useradd warning` is harmless (a system user with uid 1000), but it is the only noise in the build.

## Smoke test, full output (green)

```
::group::the image runs as user 1000
::endgroup::
::group::installed versions match uv.lock
Using Python 3.14.8 environment at: /app/.venv
::endgroup::
::group::the bucket and a key made at run time
::endgroup::
::group::migrate, twice
migrated: (empty) -> 0004_event_blob
::endgroup::
::group::a blob in and out
1
wrote 25 bytes to fetched.txt
chain intact, 1 blob matches
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
1 d91e84de485df6a2335fae4096569087c6b2fd67b2000e94ffca0a3fe00b159e
::endgroup::
smoke test passed: previously:local
```

(The first green run, before the mutations, was identical except for the anchor hash on the last line; the final control run is the one above.)
The container names `previously-smoke-<pid>-pg` and `-s3` satisfy the DSN grammar.

## Mutations (each restored at once, `git status --short` showed only the three untracked paths afterwards)

| Mutation | Result |
|---|---|
| `USER previously` deleted from the Dockerfile | RED: output stops after `::group::the image runs as user 1000`, exit 1 |
| `cmp attachment.txt fetched.txt` changed to compare against `expected.txt` | RED: `attachment.txt expected.txt differ: byte 1, line 1`, exit 1 |
| `uv sync --frozen` to `--upgrade` (the brief's mutation) | NOT MEASURED, see below. The image does not build. |
| Substitute mutation: after `uv sync --frozen`, `uv pip install "urllib3<2.8.0"` | RED: `urllib3==2.7.0`, `::error::installed versions differ from uv.lock`, exit 1 |
| Control: unchanged | GREEN: `smoke test passed: previously:local` |

The brief's `--upgrade` mutation does not reach the lock comparison.
Without `--frozen`, `uv sync` has to read the project's metadata even with `--no-install-project`, and the build context holds neither `src/` nor a git checkout, so hatch-vcs/setuptools-scm fails: `Failed to build previously @ file:///app ... unable to detect version` (build step 4 of 6 errors, exit 1).
So that mutation is red, but at the build and not in the smoke test; it says nothing about the version comparison.
I replaced it with the urllib3 drift above, which measures the comparison directly.
`urllib3<2.8.0` resolved to 2.7.0 while the lock has 2.8.0.
The comparison also works only because of its stated one-direction rule; the control shows that it does not fire on the unchanged image.

## shellcheck

`koalaman/shellcheck:v0.11.0`, ShellCheck 0.11.0. The GitHub API reports v0.11.0 as the latest release (published 2025-08-04), so it is the newest tag. Image digest `sha256:61862eba1fcf09a484ebcc6feea46f1782532571a34ed51fedf90dd25f925a8d`.
Output on `scripts/smoke-image.sh`: none, exit 0.
The shellcheck image was removed afterwards.

## Gates (each as its own command)

```
uv run ruff check .                 -> All checks passed!
uv run ruff format --check .        -> 73 files already formatted
uv run pyright                      -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                 -> Contracts: 6 kept, 0 broken.
uv run pytest --cov ...             -> 800 passed in 91.53s; coverage 98.06% (required 90%)
make -C docs html                   -> build succeeded
make -C docs vale                   -> 0 errors, 0 warnings and 0 suggestions in 28 files
make -C docs linkcheck              -> build succeeded
```

No Python test was added; the test count (800) is unchanged by this task.
I did not compare it against the tutorial's `N passed`; `tests/test_docs_typed_output.py` is part of the 800 and passed.

## Cleanup

No container, network, volume or image of mine remains (checked `docker ps -a` and `docker network ls` for `previously-smoke`; `docker rmi` of `previously:local` and the shellcheck image).
Scratch (wheel, mutation script, copies) is under the scratchpad directory, not in the worktree.

## Concerns

1. The brief's `--upgrade` mutation cannot be measured as written (see above). Task 4 or the plan should drop it or replace it with a drift mutation. The urllib3 pin mutation is a candidate.
2. Dockerfile comment: the `{ref}` label was left out per ruling P-1. Task 5 must add a pointer to the delivery page if wanted.
3. The `useradd` warning about uid 1000 above SYS_UID_MAX is cosmetic; `--system` could be dropped to silence it, but I kept the brief's text.
4. The smoke test needs `uv` and `openssl` on the host and runs from the repository root (`uv export`); the CI job in task 4 must provide both.
5. The commit message carries the `Assisted-By: Claude Sonnet 5.5` trailer as instructed; `global-constraints.md` names Opus 5.5 there.

## Fix round 1 (commit 05372db, on top of ea7ceb2; only `scripts/smoke-image.sh`)

Important 1 (cleanup fails for a host user other than 1000):
Chosen: the script now makes `$WORK/identities` on the host (`mkdir`) and sets `chmod 0777` on `$WORK` and `$WORK/identities` before the first `run`.
Why this and not a cleanup through a container: the directory then belongs to the host user, and removing the key file inside it needs write permission on the directory only, which the host user has whatever its uid is; the container (uid 1000) can still write into it because it is open to all. It is two lines, adds no further `docker run` to the cleanup, and the cleanup stays free of the image.
Measured (no way to become uid 1001 here, so the reviewer's stand-in, with real uids, using the built image for every step): host steps as `--user 1001`, the identity write as `--user 1000` with mode 0600, then `rm -rf` as 1001.
- Old layout (container makes `identities`): `rm: cannot remove '/base/work/identities/k': Permission denied`, `cleanup exit=1`, directory `work` left behind.
- New layout: `cleanup exit=0`, nothing left.
Stand-in script: `standin.sh old|new` in the scratchpad.

Minor 1 (`pg_isready` without `-h`): now `pg_isready -h localhost ...`, with a comment saying why.
The loop is not mutation-testable in a measured way: the race is a few seconds at container start; I only measured that the TCP check works against the real image (the full run below is green).

End to end, host user 1000, after the fix: `smoke test passed: previously:local`, `EXIT=0`, no new `/tmp/tmp.*` directory (one `/tmp/tmp.1sxL9SFIqD` existed before my run and is not mine). shellcheck v0.11.0: no output, exit 0.
Gates: ruff check clean, ruff format 73 files formatted, pyright 0 errors, lint-imports 6 kept 0 broken, pytest 800 passed (98.06% coverage), docs html / vale (0 errors, 0 warnings, 0 suggestions in 28 files) / linkcheck all succeeded.
Cleanup: `previously:local` and the shellcheck image removed; no `previously-smoke` container or network remains.

## Fix round 2 (commit 4d7e4b9, on top of 05372db; only `scripts/smoke-image.sh`; ruling T3-c)

Problem (from the round 1 re-review): `blob get` writes through `mkstemp`, so `fetched.txt` is owned by uid 1000 with mode 0600; as host uid 1001, `cmp` fails with Permission denied and `set -e` stops the script before `verify --blobs` and `anchor`.

Fix, the class and not the file: `run()` now passes `--user "$(id -u):$(id -g)"`.
The one step that checks the image's default user uses a plain `docker run --rm --entrypoint id "$IMAGE" -u` with no `--user` (it needs no environment), so it still measures uid 1000.
A comment above `run()` gives the reason.
The `mkdir "$WORK/identities"` and `chmod 0777` of round 1 are removed. Measured as not needed: `$WORK` comes from `mktemp -d` and belongs to the host user, and the container now writes as that same user, so it can create `identities/` and every other file itself, and the host user can read and remove all of it. The full run as uid 1001 without them is green (below).

Image under a foreign uid: it works. `/app/.venv` is readable and executable for uid 1001 (python, pyrage, boto3, migrate, append, blob get, verify, anchor all ran as 1001:1001), and `uv pip freeze` works with the `UV_CACHE_DIR` the script already sets. No Dockerfile finding.

Measured as a host user of uid 1001, with a real second uid: a scratch image `smoke-host:scratch` (`docker:cli` plus bash, openssl, coreutils, diffutils, grep, sed and the `uv` binary from the pinned uv image) run with `--user 1001:1001 --group-add <docker socket gid>`, the Docker socket mounted, the worktree mounted read-only and a 0777 `TMPDIR` mounted at the same paths so the daemon resolves the bind mounts. The script ran inside it, unchanged (`id` showed `uid=1001 gid=1001`). Helper: `inner.sh` in the scratchpad.
- Round 1 version (05372db) as uid 1001, control: `cmp: .../fetched.txt: Permission denied`, `EXIT=2`. This reproduces the reviewer's finding.
- New version as uid 1001: `smoke test passed: previously:local`, `EXIT=0`, `TMPDIR` empty afterwards (no leftover directory).
- New version as host uid 1000 (normal user): `smoke test passed: previously:local`, `EXIT=0`. This run cannot tell the two layouts apart, since the host user is the image's user.

shellcheck v0.11.0 on the script: no output, exit 0.
Gates, each as its own command: ruff check clean; ruff format 73 files already formatted; pyright 0 errors; lint-imports 6 kept, 0 broken; pytest 800 passed (98.06% coverage); docs html, vale (0 errors, 0 warnings, 0 suggestions in 28 files) and linkcheck succeeded.
Cleanup: `previously:local`, `smoke-host:scratch` and the shellcheck image removed; the scratch `TMPDIR` removed; no `previously-smoke` container or network remains.
