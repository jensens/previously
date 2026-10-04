You are the final whole-branch reviewer for "the external anchor" of "Previously". Three tasks were implemented one at a time, each with its own task review and fix rounds; this review looks at the branch as a whole — what the task reviews, each scoped to one diff, could not see: seams between tasks, claims that drifted while later tasks moved on, the shape of the result against the specification, and whether an operator can actually use it.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, with the one exception named under *Assurances*. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What was implemented

Previously is an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL via testcontainers in tests, AGPL). Its hash chain attests that what is in the log is unaltered — not that the log is complete: deleting the tip, appending a self-hashed event, and rewriting the chain each leave a result that is consistent in itself. This branch adds the external anchor, the tip `(id, hash)` written down outside the database:

- `previously.contract.types.Anchor`; `previously.core.anchor` with `parse_anchors` (strict; a file without an anchor is an error) and `format_anchor`; `previously.core.verify.examine`, the one pass that checks the chain and the anchors and returns `Examination(findings, tip)`; `verify()` keeps its signature and delegates.
- Commands: `previously anchor` prints the tip of an intact chain as `<id> <hash>`; `previously verify --anchors FILE [--exact]` (`-` reads standard input). Two checks: "contains" (each anchored event exists with the anchored hash) and `--exact` (in addition, the tip is the newest anchor). Without anchors, `verify` says on standard error what it does not attest.
- Documentation in the same branch: `docs/explanation/hash-chain.md` (section `external-anchor`, the table of four forgeries against two checks, the promise), `docs/reference/cli.md`, the how-to guides for checking the chain and for restoring from a backup, the tutorial retyped from one run, README, `design-records.md`, and the specification frozen under its dated header.
- `CLAUDE.md` gained two sections on this branch: *A merge into `main` is the acceptance* is from before; *Operations are part of every design* is new here.

The command line is the entry point only until an MCP server exists. The design intent is that the core returns structured results and the command line reads a file and formats.

## Requirements

- The specification (German, frozen in the last task): `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`. Read it in full; it is about 420 lines. §4.3 to §4.5 are the contractual texts and exit codes, §5 the table and the promise, §5.1 operations, §7 the assurances with their mutations, §9 the acceptance table, §10 what was deliberately left open.
- The plan: `docs/superpowers/plans/2026-10-04-aeusserer-anker.md` (German, long). Read only `## Global Constraints` and `## Review Focus`, and skim the task headings. Dated `> **Nachtrag` / `> **Korrektur` blocks are amendments made during execution.
- The project's working agreements: `CLAUDE.md` in the worktree root. Read it once in full. The parts that bite here: the six gates by name; "A comment is a claim"; "An assurance needs a test measured to fail"; the suppression list is complete at five; one Diátaxis quadrant per page; typed output is a measurement; *Citing a reason from code* and *A ruling citation is provenance, never the reason* (a label numbered per plan names the plan's date and the reason stands beside it); *Operations are part of every design*; `Assisted-By:` and never `Co-Authored-By`.
- The ledger of this execution, with every ruling the controller made and the findings the task reviews deferred to you: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/progress.md`. Read the `Ruling` lines and the section `## Rückstandsliste vor der Endprüfung`. The mutation records are `task-1-mutations.md` and the mutation section of `task-2-report.md` in the same directory.

## Git range

**Base:** `b0396b6` (main before this branch)
**Head:** `7c936be`

Two review packages, so you do not read the German design records as a diff:

- Code and configuration: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-review-code-b0396b6..7c936be.diff` — `src/`, `tests/`, `migrations/`, `pyproject.toml`, `.importlinter`.
- English documentation: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-review-docs-b0396b6..7c936be.diff` — `docs/` without `docs/superpowers/`, `README.md`, `CLAUDE.md`, `.vale.ini`, `.vale-styles/`.

The suite stands at 265 tests.

**The specification is frozen and is not edited any more**, by the fix wave that follows you either. Where it and a page disagree, the page wins (`CLAUDE.md`). One such place is known: its §5.1 describes the second restore case as if the anchor at the restore point were the newest line of the anchor file. `docs/how-to/restore-from-a-backup.md` went through two fix rounds over that — first to check a restore to an earlier point against a cut file, then to take the yardstick for the cut from the place the anchor file is kept rather than from the restored log. If you find the specification wrong somewhere else, report it as a finding against the specification; the fix goes to the page, and the execution record notes the difference.

Each contains the full diff with context; the first also has the commit list. Read both. Context lines are the changed files; where a hunk you must judge is cut off, read the file at HEAD and say so. You may run `git log --oneline b0396b6..HEAD` and `git show <sha> --stat`; do not rebuild the diffs.

## The spec is a vision document

The spec says what the software must do. It does not enumerate every input, environment, or condition the software will meet. For behavior the spec is silent on, judge by what a reasonable person operating this software would expect: a reasonable person's expectation is a requirement, and a spec's silence is not permission. Grade such findings by their effect on that person, not by whether the spec mentions the trigger.

## Declined to judge

Before your verdict, list every behavior you considered and set aside as outside the plan or spec, one line each, with the reason. The controller rules on each line; nothing you set aside is dropped silently. An empty list means you set nothing aside.

## You do not dispatch subagents

Do all of this review yourself. If the diff feels too large for one pass, review it in passes yourself and say so in your report.

## Tests and gates

The implementers ran the six gates after every task. Run them yourself once on HEAD and quote each closing line: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing` (needs Docker; under a minute), `make -C docs html && make -C docs vale`. Do not run `linkcheck` (network). A gate you did not run is a gate you report as not run.

## What to check

**Use it.** This is the check no task review made. Start a database the way the tutorial does, and run the routine an operator would run, by hand: append, `previously anchor >> anchors.txt`, append again, `previously verify --anchors anchors.txt`, the same with `--exact`, the same with `--anchors -` fed from a pipe. Then forge with raw SQL — the tests show how (`tests/test_verify.py`): delete the tip; rewrite an anchored event's hash — and read what the commands print and return. Then follow the two how-to guides literally, as a reader who has only the page: `docs/how-to/verify-the-chain.md`, the routine line exactly as printed — the first time, when no file exists yet; on a log that is still empty; on every later run — and `docs/how-to/restore-from-a-backup.md`, both cases, as far as they can be played without a real backup (a second database that holds a shorter or a longer log than the anchors stands in for a restore). The implementer of the guides ran the parts of the routine but not the line as printed, and took the condition for the first anchor from the reference page rather than from a run. Judge the output as the person who has to act on it at three in the morning: does a finding say what is wrong, which anchor it came from, and does the exit code let a script decide? Put the transcript into your report. Leave no container running.

**The promise** — the single thing this branch must not get wrong. The table on `docs/explanation/hash-chain.md` under `(external-anchor)=` says what each check sees. Read every sentence in `README.md`, `docs/how-to/`, `docs/tutorial/`, `docs/reference/cli.md` and the docstrings in `core/verify.py` and `core/anchor.py` that says what an anchor closes, proves or attests, and hold it against that table. In particular: an event appended after the newest anchor is not seen by "contains"; a tip deleted above the newest anchor is seen by neither check; `--exact` reports a finding on an honest log that simply grew. A sentence that promises more is Critical.

**Seams between tasks:**
- Does `cli.py` use `examine`, `parse_anchors` and `format_anchor` exactly as the core exposes them, with nothing about the line format or the checks decided in `cli`?
- Do `cli.md`'s facts match what `_cmd_verify`, `_cmd_anchor` and `_read_anchors` do — every quoted line, every exit code, what counts as an input error?
- Do the two how-to guides use the commands as shipped, and does the restore guide's choice of check per case follow from the table (restore to the latest state → "contains"; restore to a fixed point that coincides with an anchor → `--exact`)?
- Does the tutorial's typed session agree with the commands as shipped, and with itself across blocks (the same hash in `log`, `show` and the anchor line)?
- Does the frozen spec's §10 list what the ledger says was left open, and does `design-records.md` list the fifth record consistently with the README table?

**Inputs a reasonable operator produces** and no task's tests may exercise: an anchor file with Windows line ends, with a byte order mark, with a trailing blank line, with a blank line in the middle, with the same anchor twice, with anchors out of order, with an id of 0 or a negative id, with an upper-case hash; a directory given as the file; `--anchors -` with nothing on standard input; `anchor` on a log whose chain is broken; an anchor whose id is beyond the tip together with one that holds. For each: what happens, and is it what that person would expect? Read the parser and the tests first; try by hand only what reading leaves open.

**Claims** — every number and every assertion in a comment, docstring or page the branch added or touched. Spot-check at least ten, choosing the ones a wrong value would hurt most, and say which ones you checked and how. Among them: the `print` count in `pyproject.toml` and `tests/test_docs_references.py`; the command count in the comments of `main` in `cli.py` and the `C901` series there; the test counts in the tutorial block (`uv run pytest --collect-only -q -p no:randomly | tail -1`); "five" frozen records.

**Citations.** `grep -rnE '§|review focus|[Rr]uling ' src tests` over the lines this branch added: no paragraph sign pointing at this branch's own specification, every per-plan label with its plan's date and its reason beside it, and nothing that is printed carrying a citation.

**Assurances** — the spec's §7 names the assurances and the mutation that must turn each test red; the two mutation records say what was measured. Judge whether the tests as written match that description, and whether an assurance the spec gives has no test at all. You may run one mutation yourself if a doubt is specific; the maintainer has allowed measuring in the tree. Restore the file with `git checkout -- <file>` and confirm `git status --short` is empty afterwards. If the permission system refuses, do not look for another route: report the doubt and the controller measures.

**Architecture** — `Anchor` in `contract.types`; `core/anchor.py` free of I/O; one pass over the log in `examine`, with the anchors checked in it rather than by a query per anchor; `verify()` unchanged for its callers; the layering `cli > core > storage > contract` and no SQLAlchemy import in `cli` or `core`; the error type for every input error and the exit code it leads to. And the question the maintainer asked of the design: when an MCP server replaces the command line as the entry point, what in `cli.py` would have to be written a second time? Anything beyond reading a file and formatting lines is a finding.

**Operations** — `CLAUDE.md` now requires every design to say what it means for operations, with Kubernetes as the maintainer's hosting and a single host with docker-compose kept possible. Do the guides show the routine as plain commands that look the same in both? Is anything in the code or the pages tied to one of them? Is there a step an operator needs that no page gives?

**Code quality, tests, production readiness** per the usual rubric: separation of concerns, error handling, edge cases; tests against the real database and no mocks; documentation complete and in the right quadrant.

**Commits.** `git log b0396b6..HEAD --format='%h %s%n%b'`: English subjects, `Assisted-By:` trailers, no `Co-Authored-By` and no "Generated with".

**The deferred list** — for each item in `## Rückstandsliste vor der Endprüfung`: fix before merge, fix later, or drop, and why.

## Calibration

Categorize by actual severity. Critical: a page or message that promises what the check does not hold; a forgery the table says is seen and the code does not see; a gate that lies. Important: incorrect or fragile behavior, a missed requirement, a wrong claim in prose, a page in the wrong quadrant, maintainability damage you would block a merge over. Minor: polish. Acknowledge what was done well, specifically, before the issues. If you find deviations from the plan, name them and say whether the ledger's ruling on them holds up. If you find issues with the spec or plan itself rather than the implementation, say so.

## Your report goes into a file

Write the full report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-review.md`

Structure:

### Strengths
### Gates run
One line per gate you ran, with its closing line; one line per gate you did not run.
### Hands-on session
The transcript, and what you conclude from it.
### Issues
#### Critical (Must Fix)
#### Important (Should Fix)
#### Minor (Nice to Have)
For each: an identifier (`K-1`, `W-1`, `M-1` are taken by earlier reviews of this project — use `F1`, `F2`, … in one sequence), file:line, what is wrong, why it matters, how to fix if not obvious.
### Deferred items
### Declined to judge
### Recommendations
### Assessment
**Ready to merge?** [Yes | No | With fixes] and two or three sentences of reasoning.

Then reply with ONLY (under 20 lines):
- **Ready to merge?** Yes | No | With fixes
- One line per Critical and Important finding (identifier, file:line, the claim alone)
- The count of Minor findings
- The count of lines under *Declined to judge*
- Gates: which ran green, which did not run
- The report file path

The controller reads the file; do not repeat it in your reply.
