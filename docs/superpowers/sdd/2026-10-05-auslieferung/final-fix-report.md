# Final fix wave — report (ruling E-2)

Branch `worktree-auslieferung`, base `4a9048d`, head `f6aac32`. Nothing pushed, no subagent.

## Commits

| Commit | Subject |
|---|---|
| `d1813df` | image: a numeric user, compiled bytecode, and labels of its own |
| `794e91e` | cli: SIGTERM ends a command with 143, and a migration rolls back |
| `72327ea` | comments: three claims made true, ruling citations name their plan |
| `ee97f44` | docs: the pages and the handoff say what the code and the image do |
| `f6aac32` | map: three points struck, six named after the final review |

Messages in `final-fix-commit-msg-1.txt` … `-5.txt`, each with `Assisted-By:` only. `d1813df` and `72327ea` were amended once before anything followed them: the first message mixed two measurement series for `log`, the second's title said "four claims" where it carried three.

## Per finding

### Code review (`final-review-code.md`)

| Finding | What changed, or where it is named |
|---|---|
| Important 1, `USER previously` | `Dockerfile`: `USER 1000:1000`, comment why; `groupadd`/`useradd` stay, `id` in the image prints `uid=1000(previously) gid=1000(previously)`. `smoke-image.sh`'s `id -u` = 1000 check holds (smoke green). Handoff: table row and a paragraph say the user is numeric and `runAsNonRoot` needs no `runAsUser` (the kind measurement is the code reviewer's, attributed so). |
| Important 2, no bytecode | `Dockerfile`: `ENV UV_COMPILE_BYTECODE=1` before `uv sync`, applies to `uv pip install` too; comment with the measurement. |
| Important 3, labels from `uv` | `Dockerfile`: all eight labels the base sets are set (title, description from `pyproject.toml`, url, source, licenses, version, revision, created). `revision` and `created` are `ARG`s with an empty default (a local build blanks them, no moving default); `release.yml` passes `github.sha` and `github.event.release.published_at`, both fixed per release. Index annotation for the GHCR package page: not done, named in the map (unmeasured). |
| Minor 1, four `release.yml` comments | Fixed in `d1813df`: diagram `gates and tag, side by side`; concurrency comment says a waiting run can be replaced; `permissions:` replaces; `0.1.devN` before the first tag. Map entry struck. |
| Minor 2, `migrate.py` docstring | Fixed in `72327ea`: quotes libpq's first line, which can name the user. |
| Minor 3, `_unreadable` | Fixed in `72327ea`: "every part but the scheme, the host and the port". Map entry struck. |
| Minor 4, `smoke-image.sh` comment | Fixed in `d1813df`: as uid 1000 the container could not write into `$WORK` (`mktemp -d`, 0700, host user). |
| Minor 5, four ruling citations | Fixed: `postgres.py` (T2-j), `test_cli.py` ×2 (T2-l, T2-j) in `72327ea`; `test_migrate.py` (T2-l) in `794e91e` (same file as the SIGTERM tests). Census (`CLAUDE.md` command, plus `git diff d16f3fc HEAD` for `ruling` lines added on the branch): only these four belong to this execution; `pyproject.toml:103` T9-c is an old one reflowed. No `E-` label in the tree. Not done: shipping the ledger under `docs/superpowers/sdd/2026-10-05-auslieferung/` (the controller's step before the merge; until then the citations name a ledger that doesn't ship). |
| Minor 6, `DEPENDENCIES.md` | Fixed in `72327ea`: "in the test's own process, without a subprocess". |
| Minor 7, SIGTERM | Fixed in `794e91e`, see below. Handoff and `cli.md` say it. |
| Minor 8, pooler in transaction mode | Named in the handoff (connection-string section), flagged as unmeasured. |
| Minor 9, unlocked hatchling | Named only: map, *Auslieferung*. |
| Minor 10, `CLAUDE.md` language rule; `{ref}` in `Dockerfile` | For the maintainer (below); also put into the map under *Tore und Werkzeuge*. |
| Minor 11, two rows in `alembic_version` | Named only: map, *Kommandozeile*. |

### Docs review (`final-review-docs.md`)

| Finding | What changed, or where it is named |
|---|---|
| Important 1, `runAsNonRoot` | Fixed by `USER 1000:1000`; handoff says the user is numeric. |
| Important 2, "every other command refuses" | Reworded at all five places: handoff "Why first" and the older-image paragraph (which now says only `migrate` refuses), `run-the-image.md`, `cut-a-release.md`, `delivery.md`. Map: open point under *Kommandozeile*, the maintainer's decision. |
| Important 3, `cut-a-release.md:138` | Row split: not on PyPI → fix the cause, rerun; on PyPI (even one file) → the version stays without an image, next version. |
| Minor 1, `readOnlyRootFilesystem` | Measured further: `append --attach` seals into `tempfile.TemporaryFile`; with `--read-only` and the default working directory `/app`, Python finds no usable temp dir (`FileNotFoundError … ['/tmp', '/var/tmp', '/usr/tmp', '/app']`); a smoke variant with `--read-only` on every `run()` (freeze step dropped) passed because `-w /work` is writable. Handoff: `readOnlyRootFilesystem` fine with one exception, `append --attach` needs a writable `/tmp` (an `emptyDir`). |
| Minor 2, network out | Handoff: database (`-rw`, 5432), DNS, the anchor file's place. |
| Minor 3, anchor file in and out | Handoff: the image has no `curl`/`wget`/`aws` (rechecked on the new image), fetching happens outside the `previously` container, the nightly job takes the file on stdin. |
| Minor 4, trusted publishers stated as set up | **Not in E-2's list; not changed.** See concerns. |
| Minor 5, `imagetools inspect` login | `cut-a-release.md`: log in first, or check after making it public. |
| Minor 6, digest retention | `release.yml`: `retention-days: 7` with the reason; `cut-a-release.md`: one sentence beside the rerun. |
| Minor 7, `+psycopg` sentence | Tutorial: `postgresql://` reaches the same driver (rechecked: `create_engine('postgresql://…').dialect.driver` = `psycopg`). |
| Minor 8, tag statements | `delivery.md`: one tag *meant for use* for a pre-release, intermediate tags named, an unmarked alpha gets `latest`; two tags on a commit "passes the check and does no harm", agreeing with `cut-a-release.md:58` and the map. |
| Minor 9, password needs a user | `configuration.md` table row and handoff (rechecked: `postgresql://:pw@host/db` → `InvalidDsn`). The other three grammar details the review named are not added (E-2 lists only this one). |
| Minor 10, rootless Docker / uid 0 | Named only: map, *Auslieferung*. |
| Minor 11, S3 operations | Handoff: `HeadObject`, `PutObject` with multipart, `GetObject`, `DeleteObject` (from `storage/s3.py`), `ListBucket` flagged as AWS behavior, unmeasured. |

## SIGTERM

`main` installs `_terminate` for the command's run and restores the previous handler in a `finally`. The handler ignores further `SIGTERM` and raises `SystemExit(128 + signum)`. `SystemExit` unwinds (transactions roll back, `finally: storage.close()` runs), and psycopg cancels a query it waits on when `SystemExit` reaches it (`_INTERRUPTED = (KeyboardInterrupt, SystemExit)` in psycopg 3's `connection.py`). C901 of `main` stays 3, measured; the comment says so.

Tests (`tests/test_migrate.py`), started as `[sys.executable, "-c", "import sys; from previously.cli import main; sys.exit(main())", "migrate"]`, which is what the installed script runs. No suppression: ruff's `S603` doesn't fire for literals plus `sys.executable` (as in `test_docs_typed_output.py`); it fired, measured, for the script's path and for the same string in a constant.

- `test_previously_migrate_as_a_process_of_its_own_runs`: the control, no signal, exit 0 and the line.
- `test_sigterm_ends_a_migrate_that_waits_for_the_lock`: test holds the advisory lock, SIGTERM → `(143, "")` on stderr, the wait already gone when the process has ended, no lock left, no `alembic_version`.
- `test_sigterm_in_the_middle_of_an_upgrade_rolls_it_back`: database at `0003_hash_version_2`, test holds `ACCESS EXCLUSIVE` on `event`, the upgrade to 0004 waits on it inside its transaction; SIGTERM → `(143, "")`, database stays at 0003 without `event_blob`, the next `migrate` goes `0003 → head`.

Mutations (each measured, then reverted):

| Mutation | Lock test | Rollback test | Control |
|---|---|---|---|
| no handler (`signal.getsignal` instead of `signal.signal`) | red, `-15` | red, `-15` | green |
| handler raises `RuntimeError` | red | red (`(2, 'Exceptio… in progress')` in one) | green |
| handler calls `os._exit(143)` | red, the server still showed the wait | **green** | green |

The third row is why the rollback test's docstring says it holds the outcome and not the mechanism: PostgreSQL rolls back the transaction of any client that disappears. Eight repeated runs of the three tests, green each time.

In the image: `docker stop -t 10` on a `migrate` waiting for the lock — head image 10.2 s, exit 137; new image 0.4 s, exit 143, nothing on stderr; revision unchanged.

Coverage: `_terminate`'s two body lines (`cli.py` 1159–1160) run only in the subprocesses and show as missing; total 97.98 % (was 98.06 %).

## Start time (bytecode)

Inside the container (`date` around the command), median of three, two series per image, measured on 2026-10-05:

| | head image (`4a9048d`) | new image |
|---|---|---|
| `previously --help`, series 1 | 1.70 s | 0.83 s |
| `previously log`, series 1 | 1.88 s | 1.09 s |
| `previously --help`, series 2 | 2.01 s | 0.83 s |
| `previously log`, series 2 | 2.11 s | 0.94 s |

Image 313 MB → 332 MB (`docker image inspect … .Size`: 313374814 → 331989521).

## Labels

`docker image inspect` on a local build with `PREVIOUSLY_REVISION=f6aac32…` and `PREVIOUSLY_CREATED=2026-10-05T18:00:00Z`: title `previously`, description `An append-only knowledge store for project histories`, url and source `https://github.com/jensens/previously`, licenses `AGPL-3.0-or-later`, version `0.0.0.dev3`, revision `f6aac3276132cb17a625fd35c5611a76274624a2`, created `2026-10-05T18:00:00Z`; `User=1000:1000`. Without the two arguments, both are empty strings (measured), not the base's values. `actionlint` (`~/go/bin/actionlint`) on `release.yml`: clean.

## Smoke test

`bash scripts/smoke-image.sh previously-fix:final` (image from a wheel of `f6aac32`, `0.0.0.dev3`), last line:

```
smoke test passed: previously-fix:final
```

`shellcheck` 0.9.0 on the script: clean. All images (`previously-fix:before/after/labels/final`), containers and networks I created are removed.

## Gates (at `f6aac32`, each its own command)

```
uv run ruff check .                                   All checks passed!
uv run ruff format --check .                          73 files already formatted
uv run pyright                                        0 errors, 0 warnings, 0 informations
uv run lint-imports                                   Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing         803 passed in 109.88s; Total coverage: 97.98%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                                      build succeeded; 0 errors, 0 warnings and 0 suggestions in 31 files; build succeeded (output.txt empty)
```

`uv run pip-audit --skip-editable`: No known vulnerabilities found.

Tutorial test block retyped whole from a green `uv run pytest` run over an uncommitted placeholder without a count: `803 passed in 96.12s`. No other typed output changed (the `migrate` lines and the error sentences are untouched). Map: open points 117 → 120 by the `CLAUDE.md` command (three struck, six added).

## Named only — where each went

| Item (E-2) | Where |
|---|---|
| Revision check in every command | Map, *Kommandozeile* (the maintainer's decision); pages reworded |
| `uv build` with an unlocked hatchling | Map, *Auslieferung* |
| Two rows in `alembic_version` | Map, *Kommandozeile* |
| Rootless Docker and uid 0 | Map, *Auslieferung* |
| Pooler in transaction mode | Handoff, connection-string section |
| `CLAUDE.md` language rule lacks `scripts/`, `Dockerfile`, `.dockerignore` | **For the maintainer** — and in the map under *Tore und Werkzeuge*, together with the `{ref}` in the `Dockerfile` that `test_docs_references.py` doesn't read |

## Concerns

1. **Docs Minor 4 is outside E-2 and still false-ish**: the handoff ("The maintainer has set up the publishing side … a trusted publisher on PyPI and on Test-PyPI") and `cut-a-release.md:13` ("it's in place") state trusted publishing as done, while spec §11 condition 8 schedules it after the merge and nothing measured it. A two-sentence fix; the controller's call.
2. **New operational finding**: with `readOnlyRootFilesystem`, `append --attach` fails without a writable `/tmp` (Python finds no temp dir). The handoff says so now; nothing in the image changes it. A `TMPDIR` or an `emptyDir` is the platform's to give. I did not run `append --attach` itself under a read-only root with an unwritable working directory (it needs the full setup), only Python's `tempfile.gettempdir()` in the image; the code path is `tempfile.TemporaryFile` in `core/blob.py:116`.
3. The ledger isn't shipped yet, so the four now-qualified citations still point at a git-ignored `progress.md` until the controller copies it to `docs/superpowers/sdd/2026-10-05-auslieferung/`.
4. `cut-a-release.md` says to release the next version when a `manifest` rerun comes after the seven days; rerunning both `image` jobs might also work, but I didn't claim it unmeasured.
5. Unmeasured, said so where written: `ListBucket`/403 (AWS docs), the pooler, the GHCR index annotation, Kubernetes' SIGTERM (measured with `docker stop`, which sends the same signal).
6. The handoff is not in the vale gate; vale on it reports the old findings plus `kubelet`/`pooler` as unknown words.
