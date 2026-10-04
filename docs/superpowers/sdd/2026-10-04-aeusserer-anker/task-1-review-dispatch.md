You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a whole-branch review happens after all tasks.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state. The one file you create is your report (below); scratch files go to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What was requested

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-brief.md`

Then the controller's dispatch to the implementer, which carries facts from the tree and six resolutions the implementer was bound by: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-dispatch.md`

The specification the plan argues from, for what the anchor is and what it does not close: `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` (German; read §1.1, §2, §4, §5).

Global constraints that bind this task (from the plan and `CLAUDE.md` in the worktree root, which you read once):
- English in `src/`, `tests/`, `docs/` outside `docs/superpowers/`.
- All six gates named and run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`. A report that names fewer is a finding.
- No `# type: ignore`; no mock for time, database or randomness; no new `# noqa` (the suppression list in `CLAUDE.md` stays at five).
- "A comment is a claim": every number and every statement about behavior in a comment, docstring or page is measured against the code. Check each one you meet in the diff.
- "An assurance needs a test measured to fail": the brief's step 9 lists four mutations; the report must show each with the tests that turned red and a green control.
- Code cites pages, never a paragraph of the specification: `` {ref}`external-anchor` `` or `` {ref}`hash-chain` ``, no `§`, and no citation inside a string that becomes program output or a finding text.
- The three finding texts are contractual, character for character: `hash does not match the anchor`; `anchored event is missing (the log ends at <tip>)`; `the log continues past the newest anchor (<id>)`.
- `verify(storage, *, batch=1000) -> list[Finding]` keeps its signature; existing callers and tests are not edited.
- The core returns structured results (`Examination(findings, tip)`), no sentences beyond the finding reasons; `core/anchor.py` touches no file and no database.
- Documentation: `docs/explanation/hash-chain.md` is an explanation page — reasoning, no instruction; one sentence per line; sentence-case headings; American English; at most two admonitions on the page.
- In the tutorial only the test-run block changes, retyped from a real run, without a `rootdir:` line.

## What the implementer claims they built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-report.md`

## Diff under review

**Base:** `edcb9e0`
**Head:** `11de3f6`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-edcb9e0..11de3f6.diff`

Read the diff file once — commit list, stat summary, full diff with context. The diff's context lines ARE the changed files: do not Read a changed file separately unless a hunk you must judge is cut off, and say so in your report. Do not re-run git commands. Inspect code outside the diff only to evaluate a concrete risk you can name — one focused check per risk, and name both in your report.

## You do not dispatch subagents

Do all of this review yourself. Never spawn a subagent or a second reviewer.

## Do not trust the report

Treat the implementer's report as unverified claims about the code. Verify them against the diff. Design rationales in the report are claims too; a stated rationale never downgrades a finding.

## Tests

The implementer ran the tests and the six gates and reported the results. Do not re-run the suite to confirm their report. Run a test only when reading the code raises a specific doubt that no existing run answers — then a focused test (`uv run pytest tests/test_verify.py -k <name> -p no:randomly -q`; needs Docker), never the whole suite.

**The four mutations of the brief's step 9 were not measured.** The permission system refused the implementer the edit that removes the hash comparison, and the implementer stopped there; the question whether the measurement may run is with the maintainer. **Do not run any mutation yourself**, not in the tree and not on a copy: an action refused to one agent is not done by another. Instead, for each of the four mutations, reason from the code which of the new tests would turn red and say so, clearly marked as reasoning and not as a measurement; and if you find a mutation that, by your reading, no test would catch, that is an Important finding.

Five specific checks, because this project's failure mode is a claim that reads like competent work:

1. **`examine` is the old `verify` with five changes and nothing else.** Compare the removed and added lines of `src/previously/core/verify.py`: the body's comments must have survived, the count reconciliation must still run inside the same transaction, and the anchor checks must happen in the walk — no second read of the event table.
2. **What the tests pin is what the spec says the anchor closes — and what it does not.** `test_an_appended_event_passes_contains_and_fails_exact` and `test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check` pin limits; judge whether each asserts the limit honestly (both halves, with the control), and whether any test asserts nothing.
3. **Every claim on the page section.** The table of four forgeries against two checks must agree with the tests cell by cell. The sentence about what the `id` adds beside the hash must be true of `event_hash` in `src/previously/core/hashing.py` (one focused look) and must not call the `id` "the important half". The old sentence "closes all three at once" must be gone, and nothing on the page may still say that stage 1a "has none" as a present-tense fact about the tree. Numbers on the page must be the tests' numbers.
4. **The parser's strictness.** `parse_anchors` refuses a third field, a non-positive or non-ASCII `id`, a hash that is not 64 hex characters, and a file with no anchor; each refusal names the line. Look for an input that slips through or raises something other than `InvalidPayload` — one focused experiment in a Python one-liner is fine.
5. **The tutorial block.** `collected N items` and `N passed` agree, the per-file counts sum to N, no `rootdir:` line; measure N with `uv run pytest --collect-only -q -p no:randomly | tail -1`.

## Part 1: Spec compliance

Missing requirements, extras not asked for, right feature built the wrong way — against the brief and the dispatch. Seven files must have their hunks. Anything you cannot verify from the diff alone: a ⚠️ item.

## Part 2: Code quality

Separation of concerns, error handling, types under pyright strict, DRY without premature abstraction, edge cases; tests verify real behavior against the database; names say what things are. File:line for every finding.

## Calibration

Important means the task cannot be trusted until it is fixed: incorrect or fragile behavior, a missed requirement, a wrong claim in prose, a test that asserts nothing. Polish is Minor. If the brief itself mandates something this rubric calls a defect, report it as Important, labeled plan-mandated. Name what was done well, specifically, first.

## Your report goes into a file

Write the full report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-review.md`

Structure: `### Spec Compliance` (✅ / ❌ / ⚠️ lines with file:line), `### Strengths`, `### Issues` with `#### Critical`, `#### Important`, `#### Minor` (each: file:line, what is wrong, why it matters, how to fix if not obvious), `### Checks run` (every command you ran and its result), `### Assessment` (**Task quality:** Approved | Needs fixes, and one or two sentences of reasoning).

Then reply with ONLY (under 15 lines):
- **Task quality:** Approved | Needs fixes
- Spec compliance: ✅ or ❌
- One line per Critical and Important finding (file:line, the claim alone)
- The count of Minor findings
- The count of ⚠️ items, if any
- The report file path

The controller reads the file; do not repeat it in your reply.
