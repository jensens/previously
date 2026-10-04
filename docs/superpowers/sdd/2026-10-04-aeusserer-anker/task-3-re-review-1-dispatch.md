You are re-reviewing one task's fix round. A previous review produced findings; an implementer has attempted to fix them. Your job is to verdict each finding and inspect the fix diff — nothing else. The task is documentation, and its failure mode is a sentence that reads like competent work and promises more than the software holds, or a step that cannot be carried out as written.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (branch `worktree-aeusserer-anker`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state. The one file you create is your report (below); scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## The task

The previous review, for the exact wording of each finding (section `### Issues`): `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-review.md`

What the implementer was told to do about them, with the controller's rulings — read it in full, it defines what ADDRESSED means for each finding: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-fix-1-dispatch.md`

The sources of truth the pages are held against:
- `docs/explanation/hash-chain.md`, the section under `(external-anchor)=`: the table of four forgeries against two checks, and the promise.
- `docs/reference/cli.md`, sections `verify` and `anchor`; `_cmd_verify`, `_cmd_anchor`, `_read_anchors` in `src/previously/cli.py`; `examine` and `_closing_findings` in `src/previously/core/verify.py`; `parse_anchors` in `src/previously/core/anchor.py`.

Project rules that bind this review: `CLAUDE.md` in the worktree root — one Diátaxis quadrant per page (a how-to acts and links, an explanation reasons and gives no steps); one sentence per line; at most two admonitions per page; "typed-out output is a measurement"; "a comment is a claim"; *Operations are part of every design* (plain commands that look the same in Kubernetes and on one host with docker-compose); the six gates by name; `Assisted-By:` only.

## The findings under verification

- **Important 1 — the restore guide's second case checked with `--exact` against the whole anchor file**, and called the true findings of a restore to an earlier point a failed restore. Ruled (T3-c): the second case becomes a restore to an earlier point, with the five facts the fix dispatch lists, and *Read the result* follows. ADDRESSED needs each of the five facts on the page, true of the code, in a form a reader can act on — and the session in the report that shows each one.
- **Important 2 — "The events after the newest anchor came back from the write-ahead log"** stated what no check sees. ADDRESSED needs both directions said: what is there after the newest anchor is not vouched for, and what should be there and is not is not seen.
- **Minor 1 — `verify-the-chain.md`: the first anchor and the routine** must say what the anchor file holds when the first anchor is taken on an empty log or on a chain with a finding, have the reader check, and say what to do when the routine's second command fails.
- **Minor 2 — the restore guide's opening sentence** promised that you got the chain back.
- **Minor 3 — *Read the result*** did not know exit code `2`.
- **Minor 4 — README** had no bullet for the anchor under "What it does" (ruled T3-a: add it).
- **Minor 5 — `design-records.md`**, "the one reference point outside the database that can", without "up to the newest anchor".
- **A new paragraph on `hash-chain.md`** (ruled T3-d), not a finding of the previous review but part of this fix: why a restore to an earlier point looks to the anchors like a deleted tip.

Not under verification: Minor 6 (the sentence in the specification's introduction stays, ruling T3-b), and the specification itself, which is frozen and must be untouched by this fix.

## The fix

Read the implementer's report; the fix report is the section `## Fix round 1` at the end, with the raw transcript of a session against a real database: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-report.md`

**Fix base:** `a09f56a` (the head the previous review saw)
**Head:** `da79b41`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/review-a09f56a..da79b41.diff`

The implementer reports two concerns and two deviations. Judge each; none is settled:

- **The routine appends a line for the same tip again whenever no event arrived since the last run**, so the count in `chain intact, <n> anchors hold` grows with runs, not with events. Not documented in the guide. Say whether an operator needs a sentence about it, and where — it also bears on your check 2, because a file the routine produces then names the same `id` on consecutive lines.
- **The restore guide relies on the operator knowing which kind of restore they did**: after a restore to the latest state, the same "missing" findings mean real loss. Say whether the page makes that distinction impossible to miss, or whether a reader who lands in the second section could talk themselves out of a real loss.
- **The cut is shown as `head -n 2`, a concrete example,** not with a placeholder. Say whether a reader can tell which number is theirs.
- **The page title changed** (the label did not). Confirm no link text elsewhere quotes the old title: `grep -rn "brought the chain back" docs README.md`.

Read the diff file once. Do not re-run git commands to rebuild it.

## You do not dispatch subagents

Do all of this review yourself.

## Scope

Verdict every finding. Inspect the fix diff for new problems the fix itself introduced. Anything outside the fix diff goes under out-of-scope observations and does not block.

Five specific checks:

1. **Walk the restore guide as the operator it is written for**: a restored instance, and an anchor file three weeks longer than the backup. Go through the page top to bottom and, at each step, say what the operator types and what comes back — taking the outputs from the transcript, not from the page. Is there a step where the page leaves them without a next move? Does any sentence still tell them to discard a correct restore? Does the page say which file the routine continues with, and what becomes of the old one?
2. **The cut.** The page says how to find the line to cut at. Check that rule against `_closing_findings`: what does `the log ends at <tip>` name, and is "the last anchor whose `id` is not above that tip" right when the file names the same `id` twice, when the anchors are not in ascending order, and when no anchor is at or below the tip at all? A case the rule gets wrong for a file the routine itself produces is Important; a case only a hand-edited file produces is Minor.
3. **Every claim against the transcript.** Each output the two guides quote or describe — the finding for a later anchor, the success line with `--exact`, the empty file after `anchor` on an empty log, the finding `--exact` gives on a log that grew — appears in the transcript as the page says. A claim with no line in the transcript, and not marked in the report as taken from the code, is a finding.
4. **No sentence promises more than the table**, in what the fix added or changed on the two guides, the README bullet, `design-records.md` and the new paragraph on `hash-chain.md`. The three facts that get lost: an event appended after the newest anchor is not seen by the ordinary check; a tip deleted above the newest anchor is seen by neither check; `--exact` reports a finding on an honest log that has grown.
5. **Quadrants and form.** The new paragraph on `hash-chain.md` reasons and gives no steps; the guides act and point there for the why; one sentence per line; no third admonition on either guide; nothing hosting-specific. And: `docs/superpowers/specs/`, `docs/reference/cli.md`, the tutorial, `src/` and `tests/` have no hunk in the diff.

## Tests

The implementer re-ran the six gates and quoted the closing lines. Treat them as claims: confirm the report shows all six. You may run `make -C docs html`, `make -C docs vale`, `uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly` and `uv run pytest --collect-only -q -p no:randomly | tail -1`; do not run the whole suite. If a doubt about a command's behavior is specific and the transcript does not answer it, you may run that command against a scratch database of your own (a container as the tutorial sets one up, removed afterwards); say what you ran.

## Your report goes into a file

Write the report, in German (identifiers and quoted English stay as they are), to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-re-review-1.md`

Structure: `### Finding verdicts` (each finding: ADDRESSED | NOT ADDRESSED with file:line evidence — "attempted" is not addressed), `### New breakage in the fix diff` (severity and file:line, or "None"), `### Out-of-scope observations`, `### Checks run`, `### Verdict`.

Then reply with ONLY (under 12 lines):
- **Fix round:** all findings addressed | findings remain open
- One line per finding that is NOT ADDRESSED
- One line per new Critical or Important breakage
- The count of out-of-scope observations
- The report file path
