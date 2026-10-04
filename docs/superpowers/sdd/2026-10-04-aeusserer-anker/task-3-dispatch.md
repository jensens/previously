You are implementing Task 3 of the plan "the external anchor" for the project "Previously", the last task: the two how-to guides, the README, the tutorial retyped from one real run, and the specification frozen under its dated header.

## Where this fits

Previously is an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). Tasks 1 and 2, already on the branch, built the external anchor: `previously anchor` prints the tip of an intact chain as a line `<id> <hash>`, and `previously verify --anchors FILE [--exact]` checks such lines in the pass that checks the chain. The explanation is on `docs/explanation/hash-chain.md` under the label `external-anchor`, the facts are in `docs/reference/cli.md`. Your task is documentation only. After you, the controller runs the whole-branch review and opens the pull request.

## Task description

Read your task brief first — it is your requirements, with the section titles, the routine, the two restore cases, the header text and the commit message:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-brief.md`

Your task ends at the line `## Nach Aufgabe 3` in that file. What follows it — the whole-branch review, the execution record, the push and the pull request — is the controller's work: do none of it, and in particular do not push.

The brief is in German; everything you write under `docs/` (outside `docs/superpowers/`) and in `README.md` is English. The specification you freeze is German and stays German. Read `CLAUDE.md` in the worktree root once — binding here: *Documentation* (one Diátaxis quadrant per page, one sentence per line, sentence-case headings, American English, at most two admonitions per page, typed output is a measurement retyped last from a real run); *A specification starts in German and then freezes*; *Operations are part of every design* (the guides show the routine as plain shell commands that look the same in Kubernetes and on one host with docker-compose — no hosting-specific syntax); "A comment is a claim"; the six gates by name; `Assisted-By:` and never `Co-Authored-By`.

Invoke the skill `plone-doc-style:author` (exactly that name) before each quadrant: how-to for the two guides (action, no explanation, links instead of reasons), tutorial for the tutorial (first-person plural, one guaranteed path, "Notice that …").

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (git worktree, branch `worktree-aeusserer-anker`). Run every command from there. Never touch the parent checkout `/home/jensens/ws/jwk/previously`.

## Where to read the facts — do not take them from this dispatch

- **What the commands print**, character for character: `docs/reference/cli.md`, sections `verify` and `anchor`, and `src/previously/cli.py`. The three success lines, the three anchor findings, the notice on standard error without anchors, the notice on an empty log.
- **What an anchor closes and what it does not:** the table of four forgeries against two checks on `docs/explanation/hash-chain.md` under `(external-anchor)=`. No page you write may promise more than that table. In particular: an event appended after an anchor is not seen by the ordinary check, and a tip deleted above the newest anchor is seen by neither.
- **The restore cases:** the specification, §5.1 (`docs/superpowers/specs/2026-10-04-aeusserer-anker.md`): a restore to the latest state brings back events appended after the newest anchor, so `--exact` would report a finding where nothing is missing; "contains" is the right check there. `--exact` fits a restore to a fixed point that coincides with an anchor.
- **The frozen header:** copy it word for word from `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, lines 3 to 14; the date is the date of your commit.
- **The test count:** `uv run pytest --collect-only -q -p no:randomly | tail -1`. It stood at 265 after Task 2's fix round; measure it.

## What Tasks 1 and 2 leave you

- **The explanation page was tightened in Task 1's fix round**, and your pages have to say the same: an anchor closes two of the three manipulations *up to the newest anchor*, and "three manipulations pass" is a statement about *the chain alone*. Read the section as it stands now; do not write from the brief's summary of it.
- **Two things Task 2 knowingly left stale for you.** `docs/how-to/verify-the-chain.md` line 8 still says of `verify` "It takes no arguments." — false since Task 2. And the tutorial's `verify` block shows one line fewer than a real run prints. Both are in your brief; they are named here so that you find them where they are.
- **The reference page is finished and checked**: `docs/reference/cli.md` carries the argument table, the format of the anchor file, what counts as an input error, the three findings, the three success lines and both notices, and `tests/test_docs_references.py` holds its quotations against the code. Link to it; do not restate its tables in a guide.
- **The suite stands at 265** (measured after Task 2's fix round, which added two tests for standard input; you add no test). The tutorial's test block was typed from a run at that count; yours replaces it, typed last. `tests/test_docs_typed_output.py` holds `N passed` against the tree, so a first run may fail on that one test if you retype the count before running — type the block from a run that is green.
- **Vale read 22 files after Task 2.** You add no page, so it reads 22 after you.
- **Standard input.** `verify --anchors -` reads the anchors from standard input exactly the way it reads a file — that was a defect until Task 2's fix round and is tested now; the reference page says what is accepted. Show it in the checking guide as one plain shell line that feeds the file in, and run that line once for real before you write it down.
- **A per-plan label names its plan.** Not likely to come up in prose pages, but if you cite a ruling or a review focus anywhere: `… of the 2026-10-04 external-anchor plan`, with the reason beside it.

## Resolutions

1. **The how-to for checking the chain stays hosting-neutral.** The routine is two commands — check the old anchors, then take a new one — and a sentence on where the file has to live: where whoever can write the database cannot write. Mention that `-` reads the anchors from standard input, for the case that the command runs in a container and the file lives outside. No CronJob manifest, no compose file.
2. **The restore guide loses the sentence "the restore is trustworthy"** as a statement about exit code 0 alone, and gains the two cases. Say plainly what exit code 0 means without anchors: the chain is consistent in itself, and nothing more.
3. **The tutorial is one run.** Follow the tutorial's own steps against a fresh container, and retype every block of the session from that one run, so that the event's timestamp and hash agree across `log`, `show`, `chronicle`, `stats` and the new anchor step. The one block you may leave is the `uv sync` block, if a fresh run would print a machine path; the page says no output names a directory. `verify` now prints a second line on standard error and a terminal shows both: type what the terminal shows. The new section `## Pin the tip` comes after `## Check the chain`, with the two commands from the brief and their real output. The test-run block comes last, from a real `uv run pytest` run, without the `rootdir:` line. Put the raw transcript of the run into your report.
4. **README:** eight commands; the paragraph about the limit of the chain rewritten for a tree that has the anchor; the table of frozen records gets its fifth row with the date. Nothing else.
5. **The specification's §10:** rewrite the introduction for a frozen document, and count the points yourself before you write a number.
6. **`design-records.md`:** five documents; the anchor specification introduced where the others are, with its date, its topic and the pages that carry its reasoning; and the measurement the page already carries for stage 1b repeated for this one — run the two greps from the brief and put the outputs into the report. Do not edit `CLAUDE.md`.
7. **Stage by name.** `git status --short` before `git add`; add only the six files of the brief's commit step. Anything else modified: report it, do not add it.
8. **Trailer:** `Assisted-By: Claude <the model you are> <noreply@anthropic.com>`; if you do not know, `Claude Opus 5`.

## Your job

1. The brief's steps in order; the tutorial's test block last.
2. All six gates, each run separately, each closing line quoted in full in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
3. Commit with the brief's message.
4. Self-review: read each guide once as an operator who has never seen the project, the tutorial once end to end as a newcomer, and check every sentence about what the anchor closes against the table on `hash-chain.md`. Then report.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to write a page, and never spawn a reviewer.

## When you are in over your head

Report `BLOCKED` or `NEEDS_CONTEXT`. If the tutorial's container steps do not work for you (Docker, ports), that is a `BLOCKED`, not a reason to type output from memory.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-report.md`

It contains: what you wrote, page by page; the raw transcript of the tutorial run and of the test run; the two grep outputs; the measured test count; the six closing lines; files changed; every deviation from the brief or this dispatch and why; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line gate summary (pytest count, Vale file count and errors)
- Concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering gates, append a fix report to the same report file, and reply with the same short contract.
