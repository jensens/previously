You are re-reviewing the fix wave that followed the final whole-branch review of "the external anchor" of "Previously". The final review produced findings; one implementer has attempted to fix them in one wave. Your job is to verdict each item and inspect the fix diff — nothing else. This is the last review before the pull request.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, with the one exception named under *Tests*. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What you verify against

- The final review, for the exact wording of each finding (F1 to F10, and the section *Deferred items*): `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-review.md`
- What the implementer was told to do, item by item, with the controller's rulings — read it in full, it defines what ADDRESSED means for each item and what was deliberately left out: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-fix-dispatch.md`
- The four findings on the restore guide that the wave took over from a task review (M1 to M4): `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-re-review-2.md`, section `### New breakage in the fix diff`.
- `CLAUDE.md` in the worktree root — the six gates by name; "A comment is a claim"; "An assurance needs a test measured to fail", with a case measured to stay green beside it; the suppression list complete at five; no `# type: ignore`, no mock; one Diátaxis quadrant per page, one sentence per line, at most two admonitions per page; typed output is a measurement; a label numbered per plan names its plan and stands beside its reason; *Operations are part of every design* (plain commands that look the same in Kubernetes and on one host with docker-compose, no tool prescribed); `Assisted-By:` only.
- The table and the promise on `docs/explanation/hash-chain.md` under `(external-anchor)=`: no sentence anywhere may promise more.

## The fix

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-fix-report.md`

**Fix base:** `7c936be` (the head the final review saw)
**Head:** `059ccbd` (two commits: `59072c4` for F2, `059ccbd` for the rest)
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-7c936be..059ccbd.diff`

The suite stands at 270 tests according to the report (267 after the first commit).

The implementer reports one concern, one observation and one choice. Judge each:

- **The F2 commit does not stand alone on the docs.** `59072c4` left `docs/explanation/module-boundaries.md` stale — its list of the protocol's methods and a count of them went out of date with `snapshot()` — and `059ccbd` fixes it, because amending was not allowed. Confirm the page is true at HEAD, and say whether anything else that names or counts the protocol's methods was missed (`grep -rn "eight methods\|nine methods\|count_events" docs --include=*.md` outside `docs/superpowers/` and `docs/_build/`).
- **A false claim the wave found and did not touch:** the comment in `_cmd_log` in `src/previously/cli.py` (around lines 237 to 241) says that `show` reads the event and its units "in the same snapshot"; `show` reads under `begin()`, at `READ COMMITTED`, in more than one statement. It is outside the wave's items, so it is not a NOT ADDRESSED. Say what is true — does anything observable depend on it, given that an event and its units are written in one transaction and are not rewritten afterwards? — and what the smallest fix is that leaves no false sentence: the comment, or `snapshot()` for `show`.
- **The race after the fix ran fewer times than before:** 19 of 563 before, 0 of 161 and 0 of 116 after. Say from the report why the counts differ (the scratch database grows with every run, and the walk covers the whole log) and whether 277 clean runs are enough against a rate of 19 in 563.
- **The container path names two forms only** — `docker exec -i` and `docker compose exec -T`, the two the final review measured; `kubectl` was left out because nobody measured it. The maintainer's own hosting is Kubernetes. Say whether the page, as worded, serves that reader without naming the tool: is the general statement (pass standard input through, allocate no terminal) in front of the examples, so that the examples read as examples?

Read the diff file once — commit list, stat summary, full diff with context. Do not re-run git commands to rebuild it. You may run `git log 7c936be..HEAD --format='%h %s%n%b'` once for the commit messages and trailers.

## You do not dispatch subagents

Do all of this review yourself.

## Scope

Verdict every item of the fix dispatch: section A (F2, F1, F3, F4, F5 and F6, F7, F8, F9), section B (B2, B3, B4, B7 with M1 to M4). ADDRESSED or NOT ADDRESSED, with file:line evidence — "attempted" is not addressed. Then inspect the fix diff for new problems the fix itself introduced. Items the dispatch lists as not in this wave are not findings. Anything outside the fix diff goes under out-of-scope observations and does not block.

Seven specific checks, because this wave changes behavior in the storage layer and the project's failure mode is a claim that reads like competent work:

1. **F2 — one snapshot.** Read `snapshot()` in `src/previously/storage/postgres.py` and its use in `examine`.
   - Is the isolation level set where it takes effect — before the transaction's first statement — and does it leave `begin()` at `READ COMMITTED`? Confirm from the code, and once from the database: a three-line script or a focused test run that prints `SHOW transaction_isolation` inside `snapshot()` and inside `begin()`. Say what you ran.
   - Does a connection that was used for `snapshot()` go back to the pool at `READ COMMITTED`? An engine-level option on a second engine view and a per-connection option behave differently here; say which the code uses and why a later `begin()` on the same pooled connection is not left at `REPEATABLE READ`.
   - Is the translation of `OperationalError` and `ProgrammingError` shared, not copied, and do `verify` against a missing schema and against an unreachable server still print their sentences (the existing tests for it, named, in the report's run)?
   - The test: does the assurance fail when `snapshot()` is at `READ COMMITTED` (the report's mutation), and is the control — the same sequence inside `begin()` seeing one more — in the test itself, so that the test shows it reads the right thing?
   - The race, before and after, in the report: two closing lines, the first with findings, the second with none, and the number of runs in the second large enough to mean something (the first was 539 runs).
   - Every sentence the fix touched or should have touched: the two comments in `examine`, the comment above `read` in `storage/postgres.py`, the three sentences on `docs/explanation/hash-chain.md` about one snapshot, the addition on `docs/explanation/concurrency.md`. Each must be true of the code as it is now. Check the claim that a read-only `REPEATABLE READ` transaction cannot fail with a serialization error and blocks no writer against what PostgreSQL's documentation on transaction isolation says; if the docstring says more than that documentation supports, that is a finding.
   - Anything else that calls `begin()` and argues from "one snapshot" or "one moment" in a comment the wave did not touch: `grep -rn "snapshot\|one moment\|same state" src docs --include=*.py --include=*.md` outside `docs/superpowers/` and `docs/_build/`, and judge each hit.
2. **F1 — the rule is in the core.** `Examination.anchor` gives the tip only without findings; `_cmd_anchor` decides nothing that the core now decides, and prints exactly what it printed (its tests untouched in the diff, or changed only where the report says why). Is there still a path on which a caller of the core gets a tip of a broken chain presented as an anchor — a docstring that says so, a helper that formats `tip`?
3. **F3 — a set per `id`.** Different hashes for one `id` are still each compared; the order of findings is still deterministic where a test or a page depends on it; `docs/reference/cli.md` says what is true now.
4. **F4, B3 — messages.** The new sentences, and `the input holds no anchor`: every place that quoted the old wording follows (`grep -rn "holds no anchor\|anchor file holds" src tests docs README.md` outside `docs/superpowers/` and `docs/_build/`), and nothing that is printed echoes a 5000-digit `id` back.
5. **The guides** — `docs/how-to/verify-the-chain.md` and `docs/how-to/restore-from-a-backup.md` at HEAD, read in full once more, each as an operator who has only the page. The first anchor is checked with the tool; the container path says what has to be passed through and what must not be allocated, prescribing no tool; the file's way out and back is on the page; M1 — no instruction on the restore guide leads to a command that overwrites `anchors.txt`; M2 to M4 as worded. And no sentence promises more than the table.
6. **Counts and typed output.** `uv run pytest --collect-only -q -p no:randomly | tail -1` against the tutorial's `collected N items` and `N passed`, the per-file counts summing to N, no `rootdir:` line; the `print` count in `pyproject.toml` and in the docstring of `test_no_program_output_cites_a_specification` against `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found`; every other number the report says it touched.
7. **Commits.** Each commit of the wave is said to be green on `uv run pytest`. You cannot check out an intermediate commit; judge it from the diff of each commit as the package shows it (does a commit that adds a test also carry the retyped block?) and from the report. English subjects, `Assisted-By:` trailers, no `Co-Authored-By`, no "Generated with"; F2 in a commit of its own, first.

## Tests

The implementer ran the six gates and quoted the closing lines. Run them yourself once on HEAD and quote each closing line — this is the last review before the pull request: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing` (needs Docker; under a minute), `make -C docs html`, `make -C docs vale`. Do not run `linkcheck` (network); confirm the report shows it. A gate you did not run is a gate you report as not run.

You may run one mutation yourself if a doubt about an assurance is specific and the report does not answer it; the maintainer has allowed measuring in the tree. Restore with `git checkout -- <file>` and confirm `git status --short` is empty afterwards. If the permission system refuses, do not look for another route: report the doubt.

## Your report goes into a file

Write the report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-re-review.md`

Structure: `### Item verdicts` (each item: ADDRESSED | NOT ADDRESSED with file:line evidence), `### Gates run`, `### New breakage in the fix diff` (severity and file:line, or "None"), `### Out-of-scope observations`, `### Checks run`, `### Verdict` (**Ready for the pull request?** Yes | No | With fixes, and two or three sentences).

Then reply with ONLY (under 15 lines):
- **Ready for the pull request?** Yes | No | With fixes
- One line per item that is NOT ADDRESSED
- One line per new Critical or Important breakage
- The count of new Minor findings and of out-of-scope observations
- Gates: which ran green, which did not run
- The report file path
