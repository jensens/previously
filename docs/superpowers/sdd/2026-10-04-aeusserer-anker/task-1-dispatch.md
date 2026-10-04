You are implementing Task 1 of the plan "the external anchor" for the project "Previously": the core — a type `Anchor`, reading and writing anchor lines, and `examine`, the one pass that checks the hash chain and the anchors against it — plus the section of the explanation page the code cites.

## Where this fits

Previously is an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). Its hash chain attests that what the log says is unaltered; it does not attest that the log is complete — with the tip deleted, `verify` still reports "chain intact". An anchor is the tip `(id, hash)` written down outside the database, and checking against it closes that. Task 1 builds the core, Task 2 the command line and the reference page, Task 3 the how-to guides, README and tutorial. The command line is only the entry point until an MCP server exists, which is why the core returns structured results and no sentences.

## Task description

Read your task brief first — it is your requirements, with the exact values to use verbatim (test code, function bodies, the three finding texts, the commit message):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-brief.md`

The brief is in German; everything you write into `src/`, `tests/` and `docs/` (outside `docs/superpowers/`) is English. Read `CLAUDE.md` in the worktree root once before you start — it is binding. The parts that bite here: the six gates by name; no `# type: ignore`, no mock, no new `# noqa` (the suppression list stays at five); "A comment is a claim" (every number in prose is measured against the tree, including the numbers this dispatch and the brief give you); "An assurance needs a test measured to fail" (the brief's step 9 lists four mutations: run each, record red and the green control); one sentence per line in docs, American English; typed output is a measurement; `Assisted-By:` trailer and never `Co-Authored-By`.

For the documentation step, invoke the skill `plone-doc-style:author` (exactly that name) for the explanation quadrant before touching `docs/explanation/hash-chain.md`.

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (git worktree, branch `worktree-aeusserer-anker`, HEAD `edcb9e0`). Run every command from there. Never touch the parent checkout `/home/jensens/ws/jwk/previously`.

## Facts from the tree the brief relies on (measured before dispatch)

- The environment is set up: `uv sync --locked --all-extras` has run, and `uv run pytest --collect-only -q -p no:randomly | tail -1` reports `232 tests collected`. Re-measure; if it differs, count before you go on.
- `src/previously/core/verify.py`: `verify[Conn](storage, *, batch=1000) -> list[Finding]` is one function with one `while True` loop inside `with storage.begin() as conn:`; the branch `if not rows:` ends in `return findings`; `Finding` is a frozen dataclass `(event_id: int, reason: str)`; `InvalidPayload` is already imported there. The brief tells you which five places change and that everything else in the body, comments included, stays.
- `tests/test_verify.py` has the helpers `_event(external_id)` and `_message(external_id)`, the constant `NOW`, and imports `append`, `verify`, `PostgresStorage`, `Engine`, `text`, `pytest`.
- `tests/conftest.py` has the fixture `truncate_statement` (a `str` holding one `TRUNCATE` over all tables); the brief's rewrite test takes it as a parameter.
- `event_hash` in `src/previously/core/hashing.py` puts `"id": event_id` into the hashed object — that is the fact behind the page's sentence about what the `id` adds beside the hash. Read it there before you write the sentence.
- `Tip(id, hash)` in `src/previously/contract/rows.py` has the same two fields as the new `Anchor`. Do not merge them and do not reuse `Tip`: `Tip` is what the store reports now, `Anchor` is a statement from outside about an earlier moment, and it lives in `contract/types.py` beside `RawEvent`.
- `docs/explanation/hash-chain.md` ends its section `## What the chain doesn't cover` with the sentence about an external anchor that "closes all three at once", followed by "So the promise, in full:" and two italic lines. The labels `(hash-chain)=` and `(tombstone-seam)=` exist on that page; `(external-anchor)=` does not yet — you create it, and `tests/test_docs_references.py` resolves every `` {ref}`…` `` in `src/`, `tests/` and `migrations/` against the labels under `docs/`, so the label has to exist before the gate runs.

## Resolutions

1. **The page may name the switches `--anchors` and `--exact` and the command `previously anchor`,** although Task 2 builds them: the names are fixed by the plan, and the forward reference lasts one task. Keep the page on the concept — what an anchor is, the two kinds of check, what each sees — and name a command only where the sentence needs it.
2. **`{ref}` labels, never a paragraph sign.** Code and tests cite `` {ref}`external-anchor` `` or `` {ref}`hash-chain` ``. No `§`, and no citation inside a string that becomes program output or a finding text.
3. **The three finding texts end on fixed text, deliberately.** `hash does not match the anchor`, `anchored event is missing (the log ends at <tip>)`, `the log continues past the newest anchor (<id>)`. Task 2's quotation check matches a sentence by its fixed beginning and its fixed end. Do not reword them.
4. **In the tutorial you change only the test-run block**, retyped from a real `uv run pytest` run without the `rootdir:` line. The page says at the end of the block that the line is left out.
5. **Stage by name.** Before `git add`, run `git status --short` and add only the seven files of the brief's commit step. Anything else that shows up modified: do not add it, report it.
6. **Trailer:** `Assisted-By: Claude <the model you are> <noreply@anthropic.com>`; if you do not know which model you are, `Claude Opus 5`.

## Your job

1. The brief's steps in order: baseline, tests first, red, implementation, green, the four mutations with their measured results, the page, the tutorial's test block.
2. All six gates, each run separately, each closing line quoted in full in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
   Expected `pytest`: 251 passed — a prediction; count what you have.
3. Commit with the brief's message.
4. Self-review your own diff (completeness against the brief, names, no overbuilding, test output pristine), then report.

While iterating, run the focused test for what you are changing; run the full suite once before committing. The tests need Docker for a PostgreSQL testcontainer; `uv run pytest` handles it.

If the brief contradicts the tree, or a mutation does not turn red the test the brief names, the measurement wins: say so in the report and do not bend the result to the table.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to implement part of the task, and never spawn a reviewer to check your work. After you report, the controller dispatches a fresh reviewer against your diff.

## When you are in over your head

It is always OK to stop and say so. Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on, what you tried, and what would unblock you.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-report.md`

It contains: what you implemented; the RED runs (command, the relevant failing output) and the GREEN runs; the four mutations, each with the tests that turned red and the closing line, and the green control; every number you put on the page and where you read it; the six closing lines; files changed; every deviation from the brief or this dispatch and why; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line test summary (count, coverage)
- Concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering tests, append a fix report to the same report file, and reply with the same short contract.
