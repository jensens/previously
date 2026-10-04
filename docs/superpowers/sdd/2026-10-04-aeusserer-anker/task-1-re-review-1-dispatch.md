You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## The task

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-brief.md`

The previous review, for the exact wording of each finding (section `### Issues`): `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-review.md`

Project rules that bind this review: `CLAUDE.md` in the worktree root — "A comment is a claim"; *A ruling citation is provenance, never the reason* (a per-plan label names the plan's date, and the reason stands beside it); "An assurance needs a test measured to fail"; one sentence per line in docs; `Assisted-By:` only.

## The findings under verification

- **The four mutations of the brief's step 9 were unmeasured.** They are measured now, by the controller, with the maintainer's explicit permission: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-mutations.md`. Verdict this as ADDRESSED if that record shows each of the four mutations with the tests that turned red and a green control before and after, and if the red tests are the ones the brief's table names. Do not run any mutation yourself.
- **I1 — three docstrings cite a per-plan label bare.** `tests/test_verify.py`: `test_an_empty_log_has_no_tip_and_misses_every_anchor` (`"""Review focus 4."""`) and `test_anchors_are_checked_across_a_batch_boundary` ("Review focus 3."); `tests/test_anchor.py`: `test_a_broken_line_is_refused_with_its_line_number` ("review focus 5"). Each must now say what the test pins and why, and a label that stays must name the plan: `review focus N of the 2026-10-04 external-anchor plan`.
- **I2 — `src/previously/core/verify.py`, the docstring of `_check_event`** said `verify` walks over batches; `examine` does. Must say `examine`. With it Minor 1: the comment above the batch fetch that called `verify` "the routine that runs over the whole history" while reasoning about code now in `examine`.
- **Minor 2 — `docs/explanation/hash-chain.md`:** "An external anchor closes two of the three" must be limited to "up to the newest anchor", and "Three manipulations pass, and no change to the code can stop them" must read as a statement about the chain alone.
- **Minor 3 — two untested table cells:** `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one` and `test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor` must each carry an assertion with `exact=True` and the same finding.
- **Minor 5 — `test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check`** must show that event 3 existed before the deletion and that the tip is the anchor after it.

Not under verification (ruled by the controller): Minor 4 (the helper's parameter) stays; Minor 6 (a byte order mark in a line) is Task 2's.

## The fix

Read the implementer's report (the fix report is appended at the end): `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-report.md`

**Fix base:** `11de3f6` (the head the previous review saw)
**Head:** `c7d8b47`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-11de3f6..c7d8b47.diff`

Read the diff file once. Do not re-run git commands to rebuild it.

## You do not dispatch subagents

Do all of this review yourself.

## Scope

Verdict every finding. Inspect the fix diff for new problems the fix itself introduced. Anything outside the fix diff goes under out-of-scope observations and does not block.

Two specific checks:

1. **The new assertions assert something.** For Minor 3, the `exact=True` assertions must compare against the concrete finding, not merely check that something was returned. For Minor 5, the control must hold before and after the deletion.
2. **Every sentence the fix touched is true.** Read the changed comments against `examine` and `_closing_findings`, and the changed page sentences against the table on the same page.

## Tests

The implementer re-ran the covering tests and the six gates and quoted the closing lines. Treat them as claims: confirm the report shows them. You may run `uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly` once (needs Docker; about ten seconds) and `make -C docs vale`; do not run the whole suite.

## Your report goes into a file

Write the report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-re-review-1.md`

Structure: `### Finding verdicts` (each finding: ADDRESSED | NOT ADDRESSED with file:line evidence — "attempted" is not addressed), `### New breakage in the fix diff` (severity and file:line, or "None"), `### Out-of-scope observations`, `### Checks run`, `### Verdict`.

Then reply with ONLY (under 12 lines):
- **Fix round:** all findings addressed | findings remain open
- One line per finding that is NOT ADDRESSED
- One line per new Critical or Important breakage
- The count of out-of-scope observations
- The report file path
