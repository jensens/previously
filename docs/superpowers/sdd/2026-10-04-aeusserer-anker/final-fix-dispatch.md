You are implementing the fix wave after the final whole-branch review of "the external anchor" of "Previously". All three tasks of the plan are on the branch and each passed its task review; the final review looked at the branch as a whole, used the commands by hand against a database, and judged a list of small findings the task reviews had deferred. This is the one dispatch that closes all of them. After you report, a scoped re-review verifies each item, and the controller ships the plan's execution record and opens the pull request.

Work from `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (git worktree, branch `worktree-aeusserer-anker`, HEAD `7c936be`). Run every command from there. Never touch the parent checkout `/home/jensens/ws/jwk/previously`. Tests need Docker for a PostgreSQL testcontainer. Do not push.

Read `CLAUDE.md` in the worktree root once before you start — binding throughout: the six gates by name; "A comment is a claim" (every number you write is measured, every number you touch is re-measured); "An assurance needs a test measured to fail" (every new assertion: mutate the code it guards, measure red, restore, measure green, and write both into the report — the maintainer has explicitly allowed mutations in the tree; if the permission system refuses one all the same, do not look for another route: say so in the report and the controller measures); the suppression list stays at five; one Diátaxis quadrant per page, one sentence per line, at most two admonitions per page; typed output is retyped from a real run, never edited; a label numbered per plan names its plan and stands beside its reason (`… of the 2026-10-04 external-anchor plan`); code cites pages (`` {ref}`external-anchor` ``), never a paragraph sign, and nothing that is printed carries a citation; `Assisted-By:` only, never `Co-Authored-By`.

For every page you touch, invoke the skill `plone-doc-style:author` (exactly that name) for that page's quadrant first.

The final review's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-review.md` — read it; section A below cites it by identifier. The findings the task reviews deferred, with the controller's rulings: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/progress.md`, section `## Rückstandsliste vor der Endprüfung`; the four on the restore guide are worded in `task-3-re-review-2.md` in the same directory, section `### New breakage in the fix diff`.

**The specification under `docs/superpowers/specs/` is frozen. Do not edit it**, whatever a finding says about it; where it and a page disagree, the page wins.

## The items

Every item names its files. Where an item says "fold into the existing test", add assertions to the named test and do not add a test function; where it adds a test, the collected count changes and the tutorial's test block is retyped at the end (section C).

### A. From the final review (`final-review.md`, section Issues)

**F2 first, in a commit of its own — `examine` reads one snapshot.** (Ruling E-1.)

Measured by the final review: with appends running concurrently, 27 of 539 runs of `examine` returned a false finding `event has N rows, N-1 checked — the rest is unreachable`. The cause: `PostgresStorage` sets `READ COMMITTED` on purpose (the appending procedure rests on it — `docs/explanation/concurrency.md`), and under `READ COMMITTED` every statement gets a snapshot of its own. `examine` reads its batches and then `count_events` as separate statements in one transaction, and an append that commits between the last, empty read and the count makes the two disagree. The comment in `examine` above `with storage.begin() as conn:` ("only that way do all the reads see the same snapshot"), the comment above `read` in `storage/postgres.py`, and three sentences on `docs/explanation/hash-chain.md` (around lines 268, 281 and 309: "taken in the same snapshot", "have to see one snapshot") all claim what the code does not do. `tip_and_bookmark` in `storage/postgres.py` already says the truth for its own case, and `docs/explanation/projections.md` around line 184 says it on a page. The specification left this open in its §10; this branch makes a scheduled `verify` the documented routine and tells the operator to treat any exit code other than `0` as an alarm, so the false alarm is no longer something to leave open.

What to build:

- A way for the core to ask the storage for **a read transaction in which every statement sees the same state**: one new method on the `LogStore` protocol in `src/previously/contract/store.py` — `snapshot()`, returning what `begin()` returns — implemented in `PostgresStorage` with `REPEATABLE READ`. `examine` uses it instead of `begin()`. Nothing else changes isolation: `begin()` stays at `READ COMMITTED`, and `append` and the projection worker are not touched.
- The translation of `OperationalError` and `ProgrammingError` that `begin()` carries must hold for `snapshot()` too, **without a second copy of that block**: one private helper both use. `verify` against a server that is down, or a schema that is missing, must print the sentence it prints today — the existing tests for that stay green untouched.
- Make it read-only as well if that is one execution option and it measures as such (`SHOW transaction_read_only` inside the transaction); if it is more than that, leave it out and say so.
- A read-only `REPEATABLE READ` transaction in PostgreSQL cannot fail with a serialization error and blocks no writer; say that in the docstring in one sentence, as the reason this is safe beside the appending procedure, and check it against PostgreSQL's documentation on transaction isolation before you write it.

Tests, in `tests/test_storage.py` or wherever the storage's own tests live, against the real database:

- **The assurance:** inside `snapshot()`, count the events; append one through the ordinary path (its own connection); count again inside the same `snapshot()` — the same number. And the control beside it: the same sequence inside `begin()` gives one more. That control is what shows the test reads the right thing.
- **Mutation:** `snapshot()` at `READ COMMITTED` → the assurance turns red, the control stays green. Restore, green.
- **The race, measured before and after** — not a test, a measurement for the report. The reviewer's script is at `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/race/race.py`; it needs a scratch database (a `postgres:17` container as the tutorial sets one up, schema by `alembic upgrade head`; adjust the DSN in a copy of the script, do not edit the original). Run it on the tree as it is (expect runs with findings), and again after the fix (expect none). Put both closing lines into the report. Remove the container afterwards.

Then make every sentence true. The comment in `examine`; the inner comment about the count reconciliation "in the same transaction"; the comment above `read` in `storage/postgres.py`; the three sentences on `hash-chain.md` — each either is true now or gets the word that makes it true (a snapshot, not merely a transaction). `docs/explanation/concurrency.md` describes `READ COMMITTED` as set on the engine: add where it fits that the chain check reads under `REPEATABLE READ` and why that does not disturb the appending procedure — a sentence or two, explanation quadrant. If `docs/reference/` states the isolation level anywhere, it follows.

Commit this alone, before the rest: subject `fix: the chain check reads one snapshot`, a body that carries the measurement (27 of 539 before, the number after) and says that the specification had left it open.

**F1 — the rule "no anchor on a broken chain" lives only in `_cmd_anchor`.** (Ruling E-2.) `Examination.tip` is set whether or not the pass found something, and the docstring of `Examination` says an anchor printed from it describes the chain that was checked — without the condition. A second entry point that returns `examine(...).tip` certifies a broken chain unless its author copies the rule out of `cli.py`. Move the rule into the core: `Examination` gets a property `anchor` — the tip when the pass has no finding, `None` otherwise — and its docstring says why (an anchor taken on a chain with a finding would vouch for the break). `tip` stays, for "the log ends at". `_cmd_anchor` formats what `anchor` gives and decides nothing: its output, its exit codes and its two messages stay exactly as they are, and its existing tests stay green untouched. New test in `tests/test_verify.py`: a broken chain has a `tip` and no `anchor`; an intact one has both, equal; an empty log has neither. Mutation: the property returns `tip` unconditionally → the new test red **and** `test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain` red; restore, green.

**F3 — the same anchor line twice gives the same finding twice.** (Ruling E-3.) The routine appends the same line again whenever no event arrived, so after a quiet weekend one rewritten event prints dozens of identical lines. In `examine`, keep the pending hashes per `id` as a set instead of a list: the same hash is compared once, different hashes for one `id` each on their own, as now. `test_two_lines_for_one_position_are_both_checked` stays green untouched. Fold the new assertion into it or add a test beside it: the same line three times and a rewritten event → one `hash does not match the anchor`. Mutation: back to a list → three → red. `docs/reference/cli.md`, the sentences about a repeated `id`: say what is true now. The count in `chain intact, <n> anchors hold` still counts lines; leave it.

**F4 — an `id` of more than 4300 digits ends in a traceback and exit code 1.** `int()` raises `ValueError` beyond Python's digit limit, in `src/previously/core/anchor.py`; the comment two lines above argues for `isascii` precisely so that no untranslated `ValueError` gets through. Refuse an `id` longer than an event `id` can be (19 digits, the length of the largest `bigint`) with an `InvalidPayload` that names the line and does **not** echo the digits back. One more case in the parametrized test for broken lines; mutation: remove the length check → that case fails with `ValueError`; restore, green. `docs/reference/cli.md` says "a positive integer": add the bound only if the page would otherwise be false.

**F5 and F6 — `docs/how-to/verify-the-chain.md`.** How-to quadrant, hosting-neutral as before: no manifest, no compose file.
- *The first anchor is checked with the tool, not by eye.* Replace "check that the file holds exactly one line" by the check that cannot be fooled: right after taking the first anchor, `previously verify --anchors anchors.txt`, which prints `chain intact, 1 anchor holds`. An empty file, or a file that holds a notice or a `FINDING` line instead of an anchor, is exit code `2` there. Keep the two sentences on how such a file comes about. Run this once for real before you write it (the scratch container from F2 serves).
- *The container path.* Whatever runs the command inside a container has to pass standard input through and must not allocate a terminal: without the first, `--anchors -` receives nothing and reports input without an anchor; with a terminal, standard error is mixed into standard output and the notice for an empty log lands in the anchor file. Say that as two facts the reader can act on. You may name the usual switches of one or two tools in half a sentence as examples; the page prescribes no tool. The reviewer measured this with `docker exec` and `docker compose exec`; take it from `final-review.md`, section *Hands-on session*, part 4, and say in the report that you did.
- *F6: the file has to get out and come back.* The page demands a place outside the database's reach, and the routine writes `>> anchors.txt` locally. One or two sentences: the routine runs between fetching the file from that place and putting it back, and an anchor that has not left the host is not yet an anchor. No tool named.

**F7 — `pyproject.toml`, `(ruling T9-c)`** in the comment block this branch rewrapped. `CLAUDE.md`: whoever touches a bare ruling citation qualifies it. T9-c is a decision of the stage 1a execution, whose ledger is lost; say that in the citation, in the words `CLAUDE.md` uses for it, and leave the reason beside it as it is.

**F8 — the tutorial leaves `anchors.txt` in the clone.** `docs/tutorials/record-your-first-event.md`: the session writes the file into the root of the clone, where `git status` shows it. Do not change a typed block for this. One sentence where the tutorial cleans up, or right after the block: the file is this tutorial's alone, remove it; where a real one has to live is in the guide. Tutorial quadrant: an instruction, not an explanation.

**F9 — assurance 7 of the specification has no measured mutation.** "`verify` prints the notice only with no finding." Measure it: in `_cmd_verify`, make the notice print even when there are findings; name the test that turns red, or — if none does — add the assertion that makes one turn red (on a chain with a finding and without `--anchors`, standard error is empty), fold it into the existing test for that case, and measure again. Restore, green. Report the result; the execution record will list which assurances are measured.

**Not in this wave:** F10 (cosmetic, the reference explains "the log ends at" correctly). And the reviewer's opinion on ledger item 6 — `anchor` printing its findings on standard error instead of standard output — is the maintainer's decision, because the specification fixes the current behavior; do not change it.

### B. Deferred by the task reviews (the ledger's list, by its numbers)

**B2 — `src/previously/cli.py`, the docstring of `_read_anchors`** is not a raw string, so the `\r\n`, `\r` and `\n` it names are control characters at run time and `help()` breaks the sentence at the place it explains. Write them the way `src/previously/core/units.py:25` does (doubled backslashes). Measure: `uv run python -c "import previously.cli as c; print(repr(c._read_anchors.__doc__))"` shows no `\r` or bare newline inside that sentence afterwards — and since that command reaches into a private name, run it from the shell only; it does not go into a test.

**B3 — `src/previously/core/anchor.py`, the message `the anchor file holds no anchor`** (ruling T2-d). The core gets lines and does not know where they came from; with `--anchors -` there is no file, and a second entry point will have none either. Make the message name no source: `the input holds no anchor`. Then follow it everywhere: `tests/test_anchor.py` and `tests/test_cli.py` (the parametrized case that pins the sentence), any docstring or comment that quotes it, `docs/reference/cli.md` and `docs/how-to/restore-from-a-backup.md` where they describe that error — grep for `holds no anchor` over `src tests docs README.md` (outside `docs/superpowers/` and `docs/_build/`) and judge every hit. Mutation: change the message back in the core, the tests that pin it turn red; restore, green.

**B4 — `docs/reference/cli.md`, "a file that can't be read"** in the list of input errors leaves out standard input, which the same handler covers (`cannot read standard input: …`). One clause, true of `_read_anchors`.

**B7 — `docs/how-to/restore-from-a-backup.md`, M1 to M4 of the second re-review:**
- **M1, the one that can cost a file:** in *After the check*, the paragraph for the case without an anchor comes before the paragraph about the routine, and it names a file to start over with that is **not** `anchors.txt` — the guide it points to shows `previously anchor > anchors.txt`, which would overwrite the file the page has just said to keep unchanged. Say "no anchor taken before the restore point", not "at or below" a point.
- **M2:** the fallback says when it applies in terms of the file only. Where the page names the one check whose findings are expected, and where the fallback sends the reader back to the steps of the main route, say that this is after a restore on purpose to an earlier point, and keep in front of the reader what the cut cannot show.
- **M3:** the fallback's first step assumes a finding that names the tip. Say what to do when the check against the whole file exits `0` (the restore reached the newest anchor: it is the first case) or reports only `hash does not match the anchor`.
- **M4:** "as it stood at the restore point" → the last version from before that point; a version recorded after it holds anchors from after it, and each of those reads as a loss.

**Not in this wave** — ledger items 1, 5, 6, 8 and 9, unless section A takes one of them up by its identifier.

### C. Closing

1. **Every number you touched, re-measured.** List them in the report with the command. In particular, if you add or remove a `print` in `cli.py`: `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found` against the number in `pyproject.toml` and in the docstring of `test_no_program_output_cites_a_specification`.

2. **The reference's quotations.** `tests/test_docs_references.py` holds what `docs/reference/cli.md` quotes against the code. If an item changes a message the page quotes, or adds one, the page and the check follow in the same commit; run `uv run pytest tests/test_docs_references.py -q -p no:randomly`.

3. **The tutorial**, `docs/tutorials/record-your-first-event.md`. If the collected count changed, retype the whole test block from a real green `uv run pytest` run, without the `rootdir:` line; `tests/test_docs_typed_output.py` holds the count. If an item changed what a command of the tutorial's session prints, that block is retyped from a real run of the session as well — say which. If neither, leave the page alone and say so.

4. **All six gates**, each run separately, each closing line quoted in full:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```

5. **Commit hygiene.** `git status --short` before `git add`; stage only the files you changed, by name; anything else that shows up: do not add it, report it. F2 is a commit of its own, first, so that the maintainer can read it alone. The rest is one commit, or two if code and guides read better apart. **Every commit is green on `uv run pytest`**: `tests/test_docs_typed_output.py` holds the tutorial's `N passed` against the tree, so a commit that changes the collected count carries the retyped test block with it — which means the block may be retyped once per commit; that is the cost of commits that each stand. English messages that say what was measured; trailer `Assisted-By: Claude <the model you are> <noreply@anthropic.com>`. No amend, no push.

## You do not dispatch subagents

Do all of this yourself. Never spawn a subagent to implement an item, and never spawn a reviewer; the controller dispatches the re-review after you report.

## When you are in over your head

Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on. An item you cannot close is reported as open with the reason, not silently skipped. If an item contradicts the tree, the measurement wins: say so.

## Report

Write the full report to `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-fix-report.md`: per item what you changed, the measurement before and after, the mutation result for every new assertion (red with output, green with output), the re-measured numbers with commands, any transcript of a hand-run session, the six closing lines, files changed, and every item you leave open with the reason.

Then reply with ONLY (under 20 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
- Commits (short SHA + subject, one per line)
- One-line gate summary (pytest count, coverage, Vale files)
- Items left open, one line each
- Disagreements, one line each
- The report file path
