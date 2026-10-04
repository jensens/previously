You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a whole-branch review happens after it. The task is documentation only, and its failure mode is the one that is hardest to see: a sentence that reads like competent work and promises more than the software holds.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What was requested

Read the task brief, down to the line `## Nach Aufgabe 3` — what follows that line is the controller's work, not the task's: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-brief.md`

Then the controller's dispatch to the implementer, with eight resolutions the implementer was bound by: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-dispatch.md`

The sources of truth the pages are held against:
- `docs/explanation/hash-chain.md`, the section under `(external-anchor)=`: the table of four forgeries against two checks, and the promise.
- `docs/reference/cli.md`, sections `verify` and `anchor`, and `src/previously/cli.py`: what the commands print, character for character.
- `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` §5.1: the two restore cases.

Global constraints that bind this task (from the plan and `CLAUDE.md` in the worktree root, which you read once):
- English under `docs/` outside `docs/superpowers/` and in `README.md`; the specification stays German.
- One Diátaxis quadrant per page: the two guides are how-to (action, conditional imperatives, links instead of reasons), the tutorial is a tutorial (one guaranteed path, first-person plural, no choices, no explanation beyond what is needed to proceed). One sentence per line, sentence-case headings, American English, at most two admonitions per page.
- "Typed-out output is a measurement": every block of the tutorial's session comes from one real run, the test-run block from a real `uv run pytest` run, without a `rootdir:` line. The report carries the raw transcript.
- *Operations are part of every design*: the guides show the routine as plain commands that look the same in Kubernetes and on one host with docker-compose — no manifest, no compose file.
- "A comment is a claim": every number on a page is measured.
- All six gates named and run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`. A report that names fewer is a finding.
- `CLAUDE.md` is not edited by this task.

## What the implementer claims they built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-report.md`

## Diff under review

**Base:** `1df139c`
**Head:** `a09f56a`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-1df139c..a09f56a.diff`

The implementer reports five things as concerns or deviations. Judge each; none is settled:

- **The routine was not run as one line.** `previously verify --anchors anchors.txt && previously anchor >> anchors.txt` appears in the checking guide; its parts were run, the line as printed was not. The whole-branch review that follows this one runs the guides by hand against a database, so you do not have to — but read the line and its surroundings for what a literal reader would hit: the first time, when no file exists; a log that is still empty; a finding in the first command.
- **"Once the log holds at least one event"** as a condition for the first anchor was taken from `cli.md`, not run. Hold the sentence against `_cmd_anchor` in `src/previously/cli.py` (an empty log prints nothing to standard output and returns 0 — so `> anchors.txt` leaves an empty file) and against `parse_anchors` in `src/previously/core/anchor.py` (input without an anchor is an error).
- **The frozen specification's introduction keeps one sentence more than the brief allowed** — who gave the commitment and when. Say whether it belongs in a frozen record.
- **README has no bullet for the anchor under "What it does"**; the implementer wrote one and removed it because the dispatch said "Nothing else". Say whether a reader of the README now learns that the anchor exists and what it is for, from the paragraph about the limit of the chain alone.
- **`design-records.md` states the count of paragraph signs as "fifteen".** The report carries the two grep outputs; hold the number against them and judge whether the sentence around it is true.

Read the diff file once — commit list, stat summary, full diff with context. The context lines ARE the changed files: do not Read a changed file separately unless a hunk you must judge is cut off, and say so. Do not re-run git commands. Inspect files outside the diff only for a concrete named risk, one focused check each, and name both in your report.

## You do not dispatch subagents

Do all of this review yourself.

## Do not trust the report

Treat the implementer's report as unverified claims. Verify against the diff. A stated rationale never downgrades a finding.

## Tests

The implementer ran the six gates. Do not re-run the suite. Cheap and allowed: `make -C docs html`, `make -C docs vale`, `uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly`, `uv run pytest --collect-only -q -p no:randomly | tail -1`.

Seven specific checks:

1. **No sentence promises more than the table.** List every sentence the diff adds or changes, in the two guides, the README and the tutorial, that says what an anchor, `verify`, or exit code 0 proves, closes, attests or guarantees. Hold each against the table on `hash-chain.md`. Three facts are the ones that get lost: an event appended after the newest anchor is not seen by the ordinary check; a tip deleted above the newest anchor is seen by neither check; `--exact` reports a finding on an honest log that has simply grown since the newest anchor. A sentence that contradicts one of them, or that a hurried operator would read as contradicting one of them, is Important at least.
2. **The restore guide's two cases.** A restore to the latest state is checked without `--exact`, and the page says what that does not attest. `--exact` appears only for a restore to a fixed point that coincides with an anchor. The old sentence that exit code 0 makes the restore trustworthy is gone, and the page says what exit code 0 means without anchors. The two existing admonitions are still there and no third was added.
3. **The routine in the checking guide.** The command line `previously verify --anchors anchors.txt && previously anchor >> anchors.txt`; the first time, with no file yet; where the file has to live; `-` for standard input; a non-zero exit code is an alarm; a pointer to `` {ref}`external-anchor` `` for the why. And nothing hosting-specific.
4. **The tutorial against the transcript.** Compare every `console` block of the session with the raw transcript in the report, character for character: the same event id, timestamp and hash across `log`, `show`, `chronicle`, `stats` and the anchor line; the `verify` block with its second line; `## Pin the tip` after `## Check the chain`, with real output and a "Notice that"; no explanation of what an anchor closes, a pointer under *Next steps* instead. Then the test block: `collected N items` and `N passed` agree with each other and with the measured count, the per-file counts sum to N, no `rootdir:` line.
5. **The frozen header.** Compare the header of `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` with lines 3 to 14 of `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`: word for word apart from what must differ (the date, the pages named). `Status: eingefroren`. In §10, count the points yourself and hold the count against the number the introduction names.
6. **`design-records.md` and the README table.** Five documents, wherever a count appears on the page — search the page for "four" and "three" and judge each hit. The anchor record introduced with its date, its topic and the pages that carry its reasoning; every `{ref}` label it names resolves (the `html` gate would fail otherwise — confirm the report shows it green, or run it). The two grep outputs in the report against the numbers the page states. The README table has its fifth row, and README says eight commands and names `anchor`.
7. **Nothing else changed.** Six files in the commit, none other; `CLAUDE.md` untouched; no page outside the six edited in passing.

## Part 1: Spec compliance

Missing requirements, extras not asked for, right thing built the wrong way — against the brief and the dispatch. Anything you cannot verify from the diff alone: a ⚠️ item.

## Part 2: Quality

Read each guide once as an operator who has never seen the project and has to act on it: is every step there, in order, and can each be carried out as written? Read the tutorial once end to end as a newcomer. Quadrant discipline, one sentence per line, headings, links. File:line for every finding.

## Calibration

Important means the task cannot be trusted until it is fixed: a promise the software does not hold, a step that does not work as written, typed output that no run produced, a wrong number, a missed requirement, a page in the wrong quadrant. Polish is Minor. If the brief itself mandates something this rubric calls a defect, report it as Important, labeled plan-mandated. Name what was done well, specifically, first.

## Your report goes into a file

Write the full report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-review.md`

Structure: `### Spec Compliance` (✅ / ❌ / ⚠️ lines with file:line), `### Strengths`, `### Issues` with `#### Critical`, `#### Important`, `#### Minor` (each: file:line, what is wrong, why it matters, how to fix if not obvious), `### Checks run` (every command you ran and its result), `### Assessment` (**Task quality:** Approved | Needs fixes, and one or two sentences of reasoning).

Then reply with ONLY (under 15 lines):
- **Task quality:** Approved | Needs fixes
- Spec compliance: ✅ or ❌
- One line per Critical and Important finding (file:line, the claim alone)
- The count of Minor findings
- The count of ⚠️ items, if any
- The report file path

The controller reads the file; do not repeat it in your reply.
