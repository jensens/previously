You are implementing the fix wave after the final whole-branch review of stage 1b of "Previously" (projections). All eight tasks of the plan are on the branch and each passed its task review; the final review looked at the branch as a whole and at a list of small findings the task reviews had deferred. This is the one dispatch that closes all of them. After you report, a scoped re-review verifies each item, and the controller ships the plan's execution record and finishes the branch.

Work from `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (git worktree, branch `worktree-stufe-1b-projektionen`, HEAD `4c52091`). Run every command from there. Never touch the parent checkout `/home/jensens/ws/jwk/previously`. Tests need Docker for a PostgreSQL testcontainer.

Read `CLAUDE.md` in the worktree root once before you start — binding throughout: the six gates by name; "A comment is a claim" (every number you write is measured, every number you touch is re-measured); "An assurance needs a test measured to fail" (every new assertion: mutate the code it guards, measure red, restore, measure green, and write both into the report); the suppression list stays at five; one Diátaxis quadrant per page, one sentence per line; typed output is retyped from a real run, never edited; `Assisted-By:` only, never `Co-Authored-By`.

The final review's report is at `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-review.md` — read it; the items below cite it. The ledger's deferred list is at `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md` under `## Rueckstandsliste (Stand vor der Endpruefung, nach Aufgabe 8)`.

## The items

Every item names its files. Where an item says "fold into the existing test", add assertions to the named test and do not add a test function; where it says "new test", the collected count changes and the tutorial's test block is retyped at the end (item 9).

### A. From the final review (`final-review.md`, section Issues)

**I-1 — `source` and `external_id` reach the tab-separated stream unescaped.** `src/previously/cli.py` applies `escape_field` only to `row.content` in `chronicle` and to nothing in `stats`; `_check_identity` in `core/append.py` lets a tab or newline through into `--source`/`--external-id`. Apply `escape_field` to every string field both commands print (`source`, `external_id`, `content`; in `stats` the `source`). `docs/reference/cli.md`: the escaping applies to every field, not to `content` alone — fix every sentence that says otherwise (around lines 98 and 131). Test: fold into an existing CLI test — append an event whose `--source` carries a tab and whose `--external-id` carries a newline, run `project`, and assert the `chronicle` line has exactly six tab-separated fields with the two characters escaped, and the `stats` line five. Measure the old behavior first (seven fields, or two lines) and put it in the report. Mutation: drop one `escape_field` call, red; restore, green. Prefer folding so the count stays 232; if a new test reads cleaner, say so and let item 9 follow.

**I-2 — "tip and `up_to_id` in one transaction" is not "one moment" under READ COMMITTED.** `storage/postgres.py` sets `READ COMMITTED` deliberately; there every statement gets its own snapshot, and `_cmd_chronicle`/`_cmd_stats` read `tip` and `projection_state` as two statements. Spec §6.5 and `docs/explanation/projections.md` (around line 182) argue from "one moment". Ruling: make it true rather than weaken it — add one method to `PostgresStorage` that reads both numbers in **one** SQL statement (two scalar subqueries: `max(event.id)` and the state row's `up_to_id` for the given name), returning a small frozen row type or a tuple; both commands use it for the lag line and nothing else changes. It is a read helper outside the protocols, like `read_chronicle`. Then the page says why one transaction is not enough and one statement is (READ COMMITTED, statement-level snapshots — one sentence, measured against PostgreSQL's documented behavior, which you may cite by name), and `cli.md` needs no change unless it states the mechanism. The existing lag tests must stay green; no new test — this property is structural, and say so in the method's docstring. Do not change the isolation level. Do not touch the pre-existing `verify` argument in `postgres.py:203-214`; the controller carries it as an observation for the maintainer.

**I-3 — `tests/test_projection_worker.py:104` says "all nine tests in this file".** There are twelve since the Task 5 fix round; the page already says ten-of-twelve. Fix the docstring: twelve (and re-measure the "12 passed" with the mutation it describes, `first_seen=addition.first_seen`, red/green as the file's own mutation sentence demands).

**I-4 and I-5 — `docs/explanation/module-boundaries.md:175-192`, the dated measurement block.** It says "(40 today)" where `ruff format --check .` reports 48 at HEAD, and that `193` "reads the same here and in today's test run" where today's run is 232. Ruling: keep the block as what it is — a measurement dated 2026-10-03 — and remove the present-tense claims: no "(40 today)", no "today's test run"; say instead that the numbers are those of that day and have moved since (name the two that moved, with today's values measured by you). Do not retype the block.

**I-6 — `.importlinter` carries two unqualified ruling pointers, one of them wrong.** Line 51 cites `ruling T8-c` (an earlier plan's label, now colliding with this plan's T8-c). Lines 30-31, written on this branch, say "(rulings T7-a and T8-c of stage 1a, in `docs/superpowers/sdd/`)" — measured: `Ruling T7-a` in the 2026-10-03 ledger is a different decision, `Ruling T8-c` is not there at all; the stage 1a ledger no longer exists. Fix both: drop the directory pointer and say what is true — these are decisions of the stage 1a execution, whose ledger was not shipped; the reasoning stands in the comment. This belongs with item B.1 and B.2 below, which it extends.

**I-7 — the frozen spec names `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`, which does not exist at HEAD.** Not yours: the controller ships the execution record as its own commit right after your re-review passes, before the merge. Leave the spec alone.

**Minors from the final review, in this wave:**
- `docs/reference/cli.md:111-115`: the two `stderr` lines are listed lag-then-truncation; the code prints truncation first. Make the page's order the code's order, and say that both can appear.
- `docs/reference/cli.md:17`: exit code 2 for `project` — "Storage raised an error, or the worker found a gap in the log" (`ProjectionGap` is a `PreviouslyError`).
- `docs/reference/database-schema.md:122-124`: "always `NULL` in stage 1a" for `p_chronicle`'s `speaker`/`start_ms`/`end_ms` — `p_chronicle` did not exist in stage 1a; "until stage 2" or "in stages 1a and 1b".
- `.importlinter`: the contract name `No vendor SDK in stage 1a` is printed by the gate and is stale. Rename it to cover the package (`No vendor SDK in the package`, or the like), then grep `docs/` and `CLAUDE.md` for the old name and update every quotation — `module-boundaries.md` shows gate output.
- `.importlinter` line 38 carries a `{ref}` label no test checks: extend `tests/test_docs_references.py` so its label check also scans `.importlinter` and `pyproject.toml` (plain regex over the file text is enough; the AST parts stay for `*.py`). Mutation: break the label, red; restore, green.
- `src/previously/cli.py`: replace the literals `"chronicle"` and `"source-stats"` in the two commands with `CHRONICLE.name` and `SOURCE_STATS.name` (imported from `previously.core.projection`).
- `src/previously/core/projection/worker.py:147`: `expected[:1]` in the message → `expected[0]`; keep the gap test's `match` passing.
- `docs/how-to/rebuild-a-projection.md:15` and `:20` say the same thing twice; keep one.
- Seven copies of the same `TRUNCATE …` list in `tests/`: if a helper that derives the table list from `previously.storage.schema.metadata` can live in `tests/conftest.py` and be used from `tests/test_properties.py` and `tests/test_projection_worker.py` without a private import or a `sys.path` trick, do it; if not, leave the copies and say why in one sentence.
- **Not in this wave** (controller's ruling, for the next stage's open points): an upper bound on `--limit` (the `+ 1` overflow at `bigint` max), and the `set(sub.choices) == set(commands)` test from B.5.

### B. Deferred by the task reviews (ledger items 1 to 7)

1. **`tests/test_cli.py`, the `ruling P-1` citation** (around line 504). Ruling labels are per plan, and the same letters exist in the earlier plans' ledgers (this plan's T5-b, T6-b, T8-a coincide with labels already cited in `tests/test_schema.py`, `tests/test_storage.py`, `tests/test_verify.py`). Qualify the citation: `ruling P-1 of the 2026-10-04 stage 1b plan` — the record will live at `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`; name that path in the comment. The reason beside the label stays untouched; the label is provenance.

2. **`CLAUDE.md`, three edits — the maintainer will read this commit as a rule change, so each edit says what was measured and when.**
   (a) Section *A ruling citation is provenance, never the reason*: add that ruling labels are assigned per plan, that a citation therefore names the plan's record directory (as item 1 does), and that the fifteen earlier citations stay bare because they were unambiguous until 2026-10-04 and their ledger directory was the only one; whoever touches one qualifies it.
   (b) Same section: the measured state. The section says the 2026-10-03 record "holds every `Ruling …` of that execution" and the 2026-10-03 record's own index says the sixteen citations now resolve there. Measured on 2026-10-04 (`grep -rnoE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml | sort -u` against `grep -c "Ruling <label>" docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`): of the ten distinct labels in the tree, one (`T5-b`) is in that ledger; the other nine (`T2-e`, `T6-b`, `T8-a`, `T9-a`, `T9-c`, `T10-a`, `T10-b`, `T10-c`, `T10-d`) name decisions of the stage 1a execution, whose ledger was never shipped and no longer exists. For those nine the comment beside the label is the only source — which is the rule's point, and the sentence should say so. Re-run the two measurements yourself before writing the numbers; do not copy them from here. Do not edit the frozen 2026-10-03 record.
   (c) Section *A specification starts in German and then freezes*: "So the three frozen records are the output of a step and not a rule against writing a fourth" — the fourth exists since this branch. Rewrite the sentence so it is true with four and stays true with five: the records are the output of a repeating step, each new stage adds one. Check the whole paragraph for other "three".

3. **`src/previously/core/projection/worker.py`, the `catch_up` docstring** lists the function's guarantees and does not mention that `batch_size < 1` is refused with `ValueError` before any transaction opens (only the inline comment at the `raise` does). One sentence in the docstring. Do not change behavior.

4. **`src/previously/cli.py`, `log --limit`.** `chronicle` refuses `--limit < 1` with `InvalidPayload` before any read; `log` has had the same openness since stage 1a (`--limit 0` prints nothing silently, a negative value reaches the driver). Give `_cmd_log` the same guard with the same wording pattern, and fold the assertion into the existing `log` test in `tests/test_cli.py` (0 and -2 → exit 2, `stderr` names `--limit`). Measure the old behavior first and put it in the report. `docs/reference/cli.md`: the `log` section and its exit-code row say what `chronicle`'s say.

5. **Deferred by the final review to the next stage** — the `set(sub.choices) == set(commands)` test. Do not add it. It is listed here so the numbering matches the ledger.

6. **The two `stderr` sentences `cli.md` quotes** (lag line and truncation line) are held against the code by nothing: `test_the_reference_quotes_what_the_code_actually_prints` in `tests/test_docs_references.py` covers the messages the reference page quotes from `raise` sites. Extend it to the `print(..., file=sys.stderr)` literals in `cli.py` — the AST walk is already there — or, if the literals are f-strings whose static parts cannot be matched cleanly, write in the report why not and leave it as an open point for the controller. Measure red by editing one quoted word on the page, restore.

7. **Length of two explanation pages** — dropped by the final review (279 and 216 lines against `hash-chain.md` at 321; both pages stay in one quadrant). Do nothing about length. Two small wording items in `module-boundaries.md` remain from the Task 1 and 3 reviews: the antecedent at line 206 ("that measurement was the whole argument" sits textually after the `pyright` block, not after the six-gates block it refers to) — move or reword so the nearest antecedent is the right one; and "when a second protocol follows" at line 256 — the second protocol exists now, so present tense is wrong; past or timeless, your call.

Item B.2 gains two sharpenings from the final review: the `CLAUDE.md` sentence names the plan **date** (the record directory is named after it), and the ruling census goes into `CLAUDE.md` as a **command line** with `.importlinter` and `pyproject.toml` in the path list — like the `W`/`G`/`B`/`K`/`N` census already there — never as a number. For B.2(b): name the stage 1a ledger as **lost** (not absent), and separate the two statements that are currently one — "this plan's ledger holds every ruling of its execution" (true) from "the citations in the tree resolve there" (true for one label of ten). Re-measure both with the commands before writing.

### C. Closing

8. **Every number you touched, re-measured.** List them in the report with the command.

9. **The tutorial's test block**, `docs/tutorials/record-your-first-event.md`: if the collected count changed (item 5), retype the whole block from a real `uv run pytest` run, without the `rootdir:` line and without a machine path; `tests/test_docs_typed_output.py` holds the count. If the count did not change, leave the block alone and say so.

10. **All six gates**, each run separately, each closing line quoted in full:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```

11. **Commit hygiene.** `git status --short` before `git add`; stage only the files you changed, by name; anything else that shows up: do not add it, report it. One commit, or two if you judge the `CLAUDE.md` rule change should stand on its own (recommended: two — the rule change separate, so the maintainer can read it alone). Trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`. Commit messages in English, saying what was measured.

## You do not dispatch subagents

Do all of this yourself. Never spawn a subagent to implement an item, and never spawn a reviewer; the controller dispatches the re-review after you report.

## When you are in over your head

Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on. An item you cannot close is reported as open with the reason, not silently skipped.

## Report

Write the full report to `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-fix-report.md`: per item what you changed, the measurement before and after, the mutation result for every new assertion (red with output, green with output), the re-measured numbers with commands, the six closing lines, files changed, and every item you leave open with the reason.

Then reply with ONLY (under 20 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
- Commits (short SHA + subject, one per line)
- One-line gate summary (pytest count, coverage, Vale files)
- Items left open, one line each
- Disagreements, one line each
- The report file path
