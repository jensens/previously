You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a whole-branch review happens after all tasks.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, and run no mutation. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What was requested

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-brief.md`

Then the controller's dispatch to the implementer, with the interfaces from Task 1, facts from the tree and ten resolutions the implementer was bound by: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-dispatch.md`

The specification, for what the commands must do: `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` (German; read §2, §3, §4).

Global constraints that bind this task (from the plan and `CLAUDE.md` in the worktree root, which you read once):
- English in `src/`, `tests/`, `docs/` outside `docs/superpowers/`, and `pyproject.toml`.
- All six gates named and run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`. A report that names fewer is a finding.
- No `# type: ignore`; no mock for time, database or randomness; no new `# noqa` (the list in `CLAUDE.md` stays at five).
- "A comment is a claim": every number and every statement about behavior in a comment, docstring or page is measured. Four counts are in play here: the `print` count in `pyproject.toml` and in a docstring of `tests/test_docs_references.py`, and the two "seven" in comments of `main`.
- "An assurance needs a test measured to fail": the brief's step 7 lists four mutations and a control; the report must show each with what turned red. Mutations in the tree were allowed to the implementer by the maintainer; you run none.
- A label numbered per plan names its plan and stands beside its reason: `review focus N of the 2026-10-04 external-anchor plan`, never bare, never a docstring that is only a label. Code cites pages (`` {ref}`external-anchor` ``), never a paragraph sign, and nothing that is printed carries a citation.
- Contractual texts, character for character: the anchor line `<id> <hash>`; standard output `chain intact`, `chain intact, 1 anchor holds`, `chain intact, N anchors hold`, with the suffix `, the tip is the newest anchor` under `--exact`; standard error ``no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor` `` and `the log is empty: nothing to anchor`; the input error `--exact needs --anchors`; the findings `hash does not match the anchor`, `anchored event is missing (the log ends at <tip>)`, `the log continues past the newest anchor (<id>)`.
- Exit codes: 0 no finding; 1 at least one finding from the chain or the anchors; 2 input error (anchor file unreadable, malformed or without an anchor; `--exact` without `--anchors`) or storage error. An input error prints nothing on standard output.
- The command line reads the file and formats; what a line has to look like and what is checked stay in the core. `cli` imports nothing from SQLAlchemy.
- `docs/reference/cli.md` is a reference page: facts and tables, no reasoning; one sentence per line; sentence-case headings; American English.
- In the tutorial only the test-run block changes, retyped from a real run, without a `rootdir:` line. Its `verify` block is knowingly one line short until Task 3.

## What the implementer claims they built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-report.md`

## Diff under review

**Base:** `4d1720a`
**Head:** `2637c8e`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-4d1720a..2637c8e.diff`

Read the diff file once — commit list, stat summary, full diff with context. The context lines ARE the changed files: do not Read a changed file separately unless a hunk you must judge is cut off, and say so. Do not re-run git commands. Inspect code outside the diff only for a concrete named risk, one focused check each, and name both in your report.

## You do not dispatch subagents

Do all of this review yourself.

## Do not trust the report

Treat the implementer's report as unverified claims. Verify against the diff. A stated rationale never downgrades a finding.

## Tests

The implementer ran the tests, the mutations and the six gates. Do not re-run the suite. Run a test only on a specific doubt no existing run answers — a focused one (`uv run pytest tests/test_cli.py -k <name> -p no:randomly -q`; needs Docker). The quotation check has no database: `uv run pytest tests/test_docs_references.py -q -p no:randomly` is cheap, and so are `uv run ruff check .` and `make -C docs vale`.

Six specific checks, because this project's failure mode is a claim that reads like competent work:

1. **The order inside `_cmd_verify`** — the `--exact`-without-`--anchors` check, then reading the anchors, then the database — and that an input error leaves standard output empty. Confirm the hint is printed only on an intact chain and only without anchors.
2. **`anchor` prints the tip of the pass.** It must take the tip from `examine`'s result, not from a second query, and print no line on a finding.
3. **The quotation check holds what it says it holds.** Read `_quoted_block`, `_finding_patterns` and the new assertions: three notice blocks with counts 2, 1 and 1, and three findings matched against the reasons `core/verify.py` hands to `Finding`. Then read `docs/reference/cli.md` and confirm each quoted line is word for word what the code prints. Run the check once. Judge whether a wording change on either side would really turn it red, by reading `_is_the_same_sentence` against each quoted line — in particular the lines that carry an interpolated number.
4. **The four counts.** Measure them: `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found` against the number in `pyproject.toml` and in the docstring (the implementer reports 24, and that the dispatch's `tail -1` returned ruff's "No fixes available" line instead of the count — a defect of the dispatch, not of the work); `grep -n "seven\|eight" src/previously/cli.py` against the number of entries in the dispatch table; and read the `C901` comment for a claim it does not support — the implementer was told to state what was measured and what follows from the recorded series, not to re-measure a chain that no longer exists.
5. **`cli.md` as a reference page.** Eight subcommands named; the exit-code rows for `verify` and `anchor`; the `verify` section's facts against the code (what a line looks like, what counts as an input error, what "contains" and `--exact` check); no reasoning beyond a pointer to the explanation page; the three contractual introductory sentences present.
6. **The tutorial block.** `collected N items` and `N passed` agree, the per-file counts sum to N, no `rootdir:` line; measure N with `uv run pytest --collect-only -q -p no:randomly | tail -1`.

One concern of the implementer is yours to judge rather than to repeat: the findings check runs from the page to the code only, so a reason in `core/verify.py` that `cli.md` does not quote goes unnoticed, and the test's docstring says so. Say whether that direction is what the brief asked for, and whether the docstring states the limit truthfully. Two other concerns are already owned by Task 3 and are not findings here: `docs/how-to/verify-the-chain.md` still says `verify` takes no arguments, and the tutorial's `verify` block is one line short.

## Part 1: Spec compliance

Missing requirements, extras not asked for, right feature built the wrong way — against the brief and the dispatch. Six files must have their hunks. Anything you cannot verify from the diff alone: a ⚠️ item.

## Part 2: Code quality

Separation of concerns (does `cli` only read and format?), error handling (every way a file can fail to be a file), types under pyright strict, edge cases; tests verify real behavior against the database; names say what things are. File:line for every finding.

## Calibration

Important means the task cannot be trusted until it is fixed: incorrect or fragile behavior, a missed requirement, a wrong claim in prose, a test that asserts nothing. Polish is Minor. If the brief itself mandates something this rubric calls a defect, report it as Important, labeled plan-mandated. Name what was done well, specifically, first.

## Your report goes into a file

Write the full report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-review.md`

Structure: `### Spec Compliance` (✅ / ❌ / ⚠️ lines with file:line), `### Strengths`, `### Issues` with `#### Critical`, `#### Important`, `#### Minor` (each: file:line, what is wrong, why it matters, how to fix if not obvious), `### Checks run` (every command you ran and its result), `### Assessment` (**Task quality:** Approved | Needs fixes, and one or two sentences of reasoning).

Then reply with ONLY (under 15 lines):
- **Task quality:** Approved | Needs fixes
- Spec compliance: ✅ or ❌
- One line per Critical and Important finding (file:line, the claim alone)
- The count of Minor findings
- The count of ⚠️ items, if any
- The report file path

The controller reads the file; do not repeat it in your reply.
