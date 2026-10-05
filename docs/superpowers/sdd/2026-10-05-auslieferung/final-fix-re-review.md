# Re-review of the final fix wave (ruling E-2), `4a9048d..f6aac32`

Reviewer: Opus, read-only on the tree, no subagent, 2026-10-05.
Read: `final-review-code.md`, `final-review-docs.md`, ruling E-2 in `progress.md`, `final-fix-report.md`, and the whole of `review-4a9048d..f6aac32.diff`; then `release.yml`, `cli.py` around `main`, the `_DSN` grammar, `s3.py`'s client calls, `_fetch_to`, `delivery.md` and `cut-a-release.md` around the tags.

Measured myself:

- `uv run ruff check .` clean; `ruff check --select S603,S607` on `tests/test_migrate.py` clean; `ruff format --check .` 73 files; `pyright` 0 errors.
  `grep -rn noqa src tests docs/conf.py`: five, the five `CLAUDE.md` lists.
- The three new tests (`-k "sigterm or process_of_its_own"`): 3 passed. `pytest --collect-only`: 803, as the tutorial says; `test_docs_typed_output.py` and `test_docs_references.py` green. Map count by the `CLAUDE.md` command: 120.
  Not run: the full `pytest --cov`, and gate 6 (`html`/`vale`/`linkcheck`); those numbers are the fixer's.
- An image from a wheel of the head (`0.1.dev189`), throwaway tag, removed afterward:
  `User=1000:1000`; eight labels, title `previously`, description and url its own, `revision` and `created` empty strings without the build arguments; the pinned base sets exactly these eight keys (`imagetools inspect` of the digest), so none survives from `uv`.
  Bytecode: Previously itself 38 `.py` / 38 `.pyc`, its migrations 7 / 7, site-packages 691 / 691.
  `--user 12345:12345 --help` runs. Under `--user 12345:12345 --read-only`, `tempfile.gettempdir()` raises `FileNotFoundError … ['/tmp', '/var/tmp', '/usr/tmp', '/app']`, as the handoff says.
  Import of `previously.cli` in the container: 0.70, 0.73, 0.72 s.
  `docker stop -t 6` on a `migrate` against a black-hole host: right after `docker run -d` → 6.2 s, exit 137; two seconds after start → 0.31 s, exit 143, nothing in the log.
- Ruling census (the command of the brief, with `E`): the four citations this execution added (`postgres.py:1021`, `test_cli.py:637`, `:665`, `test_migrate.py:526`) each name "the 2026-10-05 delivery plan"; `git diff d16f3fc HEAD` adds no other `ruling` line except `pyproject.toml:103`, an old T9-c that now names "the stage 1a execution". `pyproject.toml:129` T2-e is stage 1a's (blame `07561a8`). No `E-` label in the tree; none in `Dockerfile`, `scripts/`, `.github/`.

### Finding Verdicts

Code review (`final-review-code.md`):

| Finding | E-2 | Verdict |
|---|---|---|
| Important 1, non-numeric `USER` | fix | **Fixed.** `USER 1000:1000`, name kept; foreign uid still runs (measured), smoke check of uid 1000 unaffected. |
| Important 2, no bytecode | fix | **Fixed.** `UV_COMPILE_BYTECODE=1` before both installs; dependencies **and** Previously (incl. migrations) compiled, measured by count. |
| Important 3, labels of `uv` | fix | **Fixed.** All eight base keys overridden; `revision`/`created` are `ARG`s defaulting to empty, so a local build carries no misleading value; `release.yml` passes `github.sha` and `github.event.release.published_at`, both set on the only event that reaches `image` (it needs `publish-pypi`, which runs only on `release`), and stable across a rerun. Index annotation named in the map. |
| Minor 1, four `release.yml` comments | fix | **Fixed.** Diagram, concurrency (running vs. waiting run), `permissions:` replaces (the two publish jobs check nothing out and name only `id-token`; `image`/`manifest` name `contents: read`), `0.1.devN`. All four now true. |
| Minor 2, `migrate.py` docstring | fix | **Fixed.** |
| Minor 3, `_unreadable` docstring | fix | **Fixed as asked.** Nit, not reopened: a query *key* (`[a-z_]+`) takes no escape either; harmless, the key set is fixed. |
| Minor 4, `smoke-image.sh` comment | fix | **Fixed.** True for `mktemp -d` 0700. |
| Minor 5, four ruling citations | fix | **Fixed** in the tree. Still open outside the wave: the ledger has to ship under `docs/superpowers/sdd/2026-10-05-auslieferung/` before the merge, or the four name a git-ignored file (controller's step, fixer's concern 3). |
| Minor 6, `DEPENDENCIES.md` hatchling | fix | **Fixed.** |
| Minor 7, SIGTERM at PID 1 | fix | **Fixed, with a gap** — see New Breakage 1. 143, no traceback, transaction rolled back, lock gone (tests and image measured). SIGINT is untouched; the handler is restored in `finally`, so in-process `main()` calls in the suite keep pytest's handler; no thread in the suite calls `main`. |
| Minor 8, pooler in transaction mode | name | **Named** in the handoff, flagged unmeasured. |
| Minor 9, unlocked hatchling | name | **Named** in the map. |
| Minor 10, `CLAUDE.md` language rule, `{ref}` in `Dockerfile` | name | **Named** in the map and for the maintainer. |
| Minor 11, two rows in `alembic_version` | name | **Named** in the map. |

Docs review (`final-review-docs.md`):

| Finding | E-2 | Verdict |
|---|---|---|
| Important 1, `runAsNonRoot` | fix | **Fixed** (by the `Dockerfile`; handoff true now). |
| Important 2, "every other command refuses" | fix (wording) | **Fixed.** All five places reworded to what was measured; no leftover in `docs/` (grep). Revision check in every command named in the map. |
| Important 3, `publish-pypi` row | fix | **Fixed.** Row split; the "on PyPI" branch no longer leads to an impossible rerun. |
| Minor 1, `readOnlyRootFilesystem` | fix | **Fixed**, and improved: a real exception found (`append --attach` needs a writable `/tmp`), confirmed by my probe. |
| Minor 2, network out | fix | **Fixed.** |
| Minor 3, anchor file in and out | fix | **Fixed.** |
| Minor 4, trusted publishers stated as set up | not in E-2 | Not changed; the controller verified it true (progress line 130). Nothing to do. |
| Minor 5, `imagetools inspect` login | fix | **Fixed.** |
| Minor 6, digest retention | fix | **Fixed.** `retention-days: 7` with a true comment; one sentence on `cut-a-release.md`. |
| Minor 7, `+psycopg` sentence | fix | **Fixed.** |
| Minor 8, tag statements | fix | **Partly fixed.** The second-tag case now agrees across `delivery.md`, `cut-a-release.md` and the map, and the intermediate tags are named. The unmarked-alpha sentence is new and false — New Breakage 2. |
| Minor 9, password needs a user | fix (that one) | **Fixed** (`configuration.md`, handoff); the grammar refuses `:pw@` (user part needs `+`). |
| Minor 10, rootless Docker / uid 0 | name | **Named** in the map. |
| Minor 11, S3 operations | fix | **Fixed.** The four operations match `s3.py`'s calls (`head_object`, `upload_fileobj`, `get_object`, `delete_object`); `ListBucket` flagged as unmeasured AWS behavior. |

### New Breakage

1. **Minor — `src/previously/cli.py:1185`: the `SIGTERM` handler is installed only after every import, so a stop in the first ~0.7 s is still lost at PID 1.**
   The entry point is `previously.cli:main`, and `cli.py` imports SQLAlchemy, Alembic, boto3 and the rest at module level before `main` runs; then `argparse` runs; only then `signal.signal`. As PID 1 with the default action, a `SIGTERM` in that window is dropped by the kernel, not deferred.
   Measured on the image of the head: `docker stop -t 6` right after `docker run -d` → 6.2 s, exit 137 (the pre-fix behavior); two seconds after start → 0.31 s, exit 143. Import alone: 0.70–0.73 s.
   Consequence: in that window, the behavior before the fix (full grace period, `SIGKILL`); a migration still rolls back server-side. Rare (a pod stopped within its first second), hence Minor.
   But three texts promise more: `docs/reference/cli.md:65` ("Every command that receives `SIGTERM` while it runs stops with exit code 143 … also as process 1"), the handoff at `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md:64` ("ends at once rather than at the end of its grace period").
   How: either install the handler before the heavy imports (a light entry module, `previously.__main__`-style, that sets it and then imports `cli`), or say "once it has started, which takes under a second" on both pages. Not a reason to hold the merge if named.

2. **Minor — `docs/explanation/delivery.md:48`: "An alpha published without the mark would get `<major>.<minor>` and `latest` as well, because the mark decides."**
   False for `<major>.<minor>`, and it contradicts the same section (`:42-44`: "An alpha gets no `<major>.<minor>` … the action extends a pre-release to its exact version only, whatever pattern it's given") and `release.yml`'s measured comment in `manifest` (`v0.1.0a1` gives the version alone). The mark decides `latest` only (`enable=${{ github.event.release.prerelease == false }}`); the form decides `<major>.<minor>`.
   Correct: an unmarked alpha gets `<version>` and `latest`, not `<major>.<minor>`.
   Same root, pre-existing and not in the diff, so only named: `docs/how-to/cut-a-release.md:89-92` ("The mark decides the image tags, not the tag's form … A release marked as a pre-release gets only the tag `<version>`. A release without the mark gets `<version>`, `<major>.<minor>` and `latest`") — by `release.yml`'s own measurement, `v1.2.3` marked as a pre-release gets `1.2.3` and `1.2`, and an unmarked alpha gets no `1.2`. Docs Minor 8 asked for the three statements to agree; fixing `:48` and these three lines in one go closes it.

3. **Minor (a comment is a claim) — `tests/test_migrate.py:666-668`: "`docker stop`, and Kubernetes stopping a pod, waited the whole grace period and ended it with `SIGKILL`, measured on 2026-10-05."**
   Only `docker stop` was measured (fixer's concern 5; the code review's Minor 7). `_terminate`'s docstring and the handoff word it correctly ("Kubernetes stops a pod the same way"; "which sends `SIGTERM` the way the kubelet does"). Move "measured" to `docker stop` alone.

Observation, not a finding: `main()` now calls `signal.signal`, which raises `ValueError` off the main thread. Nothing calls `main` from a thread today (checked the suite); a later in-process caller (an MCP server) would have to call the commands, not `main`.

### Verdict

**Ready to merge: with fixes (three Minor, text only or one small code change).**
Every finding E-2 sent to be fixed is fixed, and everything it sent to be named is named. The `Dockerfile` does what the brief asked — numeric user, bytecode for the dependencies and for Previously, foreign uid still fine, eight labels of its own, `revision`/`created` from the release and empty locally — and `release.yml`'s retention, build arguments and four comments are true.
New: the `SIGTERM` handler leaves a measured ~0.7 s window at start that two pages don't admit; one new sentence in `delivery.md` about unmarked alphas is false (and `cut-a-release.md:89-92` carries the older half of the same error); one test docstring claims a Kubernetes measurement that was a `docker stop`.
Before the merge, independent of this wave: ship the ledger under `docs/superpowers/sdd/2026-10-05-auslieferung/`.
Everything I built (image `previously-rereview:tmp`, the wheel, two probe scripts, two containers) is removed; `git status` clean.
