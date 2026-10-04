You are re-reviewing the fix wave after the final whole-branch review of stage 1b of "Previously" (projections). The final review produced findings; the controller adjudicated them together with a list of items deferred by the task reviews; one implementer closed them in two commits, `d4bcb53` (the `CLAUDE.md` rule change with the `.importlinter` pointers) and `ff3c261` (everything else). Your job is to verdict each item and inspect the fix diff — nothing else. After you, the controller ships the plan's execution record and finishes the branch.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, and do not create files inside the worktree — scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## The items

The implementer's dispatch lists every item with its file, the measurement to take and the mutation to run: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-fix-dispatch.md`. Read it in full; it is the list you verdict — section A (I-1 to I-6 and the minors; I-7 is the controller's and not under verification), section B (items 1, 2, 3, 4, 6, 7; items 5 and the length question are deferred by ruling and not under verification), section C (re-measured numbers, tutorial block if the count moved, six gates, commit hygiene).

The final review itself, for the exact wording of each finding: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-review.md`.

Project rules that bind this review: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/CLAUDE.md` — note that this fix wave **edits** `CLAUDE.md` (items B.2 and I-6); read the file at HEAD and judge the edited sections on their own terms: *A ruling citation is provenance, never the reason* and *A specification starts in German and then freezes*. Binding throughout: "A comment is a claim" (every number measured), "An assurance needs a test measured to fail" (every new assertion with a mutation measured red and a control green in the report), one quadrant per page, one sentence per line, the suppression list at five, `Assisted-By:` only.

## The fix

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-fix-report.md`

**Fix base:** `4c52091` (the head the final review saw)
**Head:** `ff3c261`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/review-4c52091..ff3c261.diff`

Read the diff file once — the fix commits, a stat summary, the diff with context. Do not re-run git commands to rebuild it.

## You do not dispatch subagents

Do all of this review yourself. Never spawn a subagent or a second reviewer.

## Scope

Verdict every item. Inspect the fix diff for new problems the fix itself introduced. Anything outside the fix diff goes under Out-of-Scope Observations and does not block.

Specific checks, because this project's failure mode is a claim that reads like competent work:

1. **I-1, escaping every field.** Read the two print sites in `src/previously/cli.py` and confirm `escape_field` wraps every string field in both commands. Find the folded assertion in `tests/test_cli.py` (a `--source` with a tab, an `--external-id` with a newline) and confirm it asserts the field count after splitting on tab. The report must show the old behavior measured and the mutation red.
2. **I-2, one statement.** Read the new method in `src/previously/storage/postgres.py`: both numbers must come from **one** `SELECT` (two scalar subqueries or an equivalent single statement), and both commands must call it for the lag. Confirm nothing else changed in the isolation level. Read the page's new sentence in `docs/explanation/projections.md` and judge whether it claims exactly what PostgreSQL's READ COMMITTED gives (a snapshot per statement) and no more. If the implementer chose a different path than the ruling (REPEATABLE READ, or weakening the sentence), say so — it is a deviation to report, not necessarily a defect.
3. **I-3, I-4, I-5 — the three numbers.** Measure: `grep -c "^def test_" tests/test_projection_worker.py` (expect 12); `uv run ruff format --check .` (file count at HEAD); `uv run pytest --collect-only -q -p no:randomly | tail -1`. Confirm the docstring says twelve, and the `module-boundaries.md` block makes no present-tense claim about 40 or 193.
4. **I-6 and B.1, B.2 — the ruling citations and `CLAUDE.md`.** Run the census the dispatch prescribes — `grep -rnoE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests migrations pyproject.toml .importlinter | sort -u` — and confirm: the `P-1` citation in `tests/test_cli.py` names the 2026-10-04 stage 1b plan; both `.importlinter` pointers no longer send the reader to `docs/superpowers/sdd/` for stage 1a decisions; `CLAUDE.md` carries (a) labels per plan with the plan date in a citation, (b) the measured state, (c) no "three frozen records" where four exist, and the census as a **command line**. On (b) the implementer corrected the controller's numbers, and the controller re-measured and agrees: the census must be case-insensitive (`grep -rnoiE …`, because a sentence-initial `Ruling T6-b` exists) and then finds **14** distinct labels, not ten; **none** of them resolves to the decision it names — `T5-b` and `T7-a` do find a line of that name in `docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`, but each is a different decision there (`Ruling T5-b` there is about `Vale.Terms`; `tests/test_schema.py` cites `T5-b` for an index seam) — and the stage 1a ledger, which the other twelve belong to, is **lost**. `CLAUDE.md` must say exactly that, keep "this ledger holds every ruling of its execution" (true of each shipped ledger) apart from "the citations in the tree resolve there" (false), and require one `ruling` per label so the census sees each. Re-measure (b) yourself: the case-insensitive census; for each label `grep -c "Ruling <label>" docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`; for `T5-b` and `T7-a` read the ledger line and the citing comment side by side. Confirm the frozen 2026-10-03 record is untouched (no hunk).
5. **The minors** — each one line: `cli.md` stderr order matches the code; `project` exit-2 cell names the gap; `database-schema.md` no longer says "stage 1a" for `p_chronicle`; the `.importlinter` contract name no longer says "stage 1a" and every quotation of the old name in `docs/` and `CLAUDE.md` follows (grep the old name tree-wide: zero hits outside `docs/superpowers/`); `test_docs_references.py` scans `.importlinter` and `pyproject.toml` for labels, with a mutation measured; `CHRONICLE.name`/`SOURCE_STATS.name` instead of literals; `expected[0]`; the how-to duplicate removed; the `TRUNCATE` helper done or declined with a reason.
6. **B.3 and B.4** — the `catch_up` docstring names the `batch_size` guard; `log --limit < 1` is refused like `chronicle`'s with the assertion folded into the existing `log` test, old behavior measured; `cli.md`'s `log` section says so.
7. **Section C** — if the collected count changed, the tutorial block was retyped from a real run (compare against the transcript in the report, `rootdir:` absent); if it did not change, the block is untouched. All six gates quoted in full, `linkcheck` included.

## Tests

The implementer ran the six gates and quoted the closing lines. Treat them as claims; confirm the report shows all six. Run the four cheap gates yourself (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`) and `make -C docs vale`; run `uv run pytest tests/test_cli.py tests/test_docs_references.py -q -p no:randomly` once (needs Docker) because two of the items add assertions there. Do not run the full suite or `linkcheck`.

## Output format

Your final message is the report itself, in German (identifiers and quoted English stay as they are): begin directly with the first item's verdict. Every line a verdict, a finding with file:line, or a check you ran.

### Item verdicts
For each item of sections A and B under verification, in order: **[one-liner]** — ADDRESSED | NOT ADDRESSED | DEVIATED (with what was done instead), with file:line evidence.

### New breakage in the fix diff
Severity and file:line. "None" if clean.

### Out-of-scope observations
Non-blocking. "None" if none.

### Verdict
**Fix wave:** [All items addressed, no new Critical/Important breakage | Items remain open] — list the open ones.
