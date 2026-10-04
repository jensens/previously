Task 3, fix round 2. The re-review found all eight points of round 1 addressed, and two new Important problems in the section the round added — `## Restore to an earlier point` on `docs/how-to/restore-from-a-backup.md`. Both go back to the controller's ruling T3-c, which told you where the cut comes from, and told you wrong. You followed it.

The re-review, for the exact wording (section `### New breakage in the fix diff`, N1 to N6, and out-of-scope observation 1):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-re-review-1.md`

Work in `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker`, as before. FIX_BASE is `da79b41`. One new commit; no amend; no push. Invoke `plone-doc-style:author` (how-to) before you write.

## What is wrong, in one paragraph

The page takes its yardstick from the result it is checking. It reads the tip of the restored log from the finding and cuts the anchor file at the last anchor not above that tip. Against a file cut that way, `anchored event is missing` cannot occur — every line left has an `id` at or below the tip — so the second case can see a rewrite and never a truncation. A replay that stopped short of where the operator meant it to end produces exactly the findings the page says to expect, and the operator who follows the steps leaves with exit code `0`. The page that exists to catch a short restore talks them out of one.

## The ruling that replaces it (T3-f)

**The yardstick is the anchor file as it stood at the point the restore was meant to reach, and that is known from outside the restored database** — from the place the file is kept: the version of that time if it is under version control, the copy or the message from that time if it is copied or mailed off the host. An anchor line carries no time of its own.

The section carries these facts — your wording, how-to form:

1. **Take the anchor file as it stood at the restore point**, from the place you keep it. Say that the file does not date its own lines, so this cannot be read off the current file. Keep it hosting-neutral: no tool is prescribed, name the kinds of place in half a sentence.
2. **Check against that file.** Against it, exit code `0` means what it means in the first case, up to that file's newest anchor. And — this is the sentence the page lacks — **`anchored event is missing` against that file is a loss**: the restore stopped short of an anchor that was taken before the point it was meant to reach.
3. **`--exact`** if the restore point coincides with the last anchor of that file; then exit code `0` means in addition that the tip is exactly that anchor.
4. **What the newer file says, as a note and not as a step:** against the anchor file as it stands today, every anchor taken after the restore point reports `anchored event is missing (the log ends at <tip>)`. Those findings are true — the restore gave those events up — and they are why the check is against the earlier file. Keep the pointer to `` {ref}`external-anchor` `` for the why.
5. **Afterwards**, as now: the routine continues against the earlier file; the newer one is kept unchanged as the record of what the restore gave up.
6. **If you cannot tell which lines the file held at the restore point** — it was only ever appended in one place, with no history. This is where the steps you wrote in round 1 belong, as the weaker fallback, with its limit said first and plainly: a file cut at the last anchor not above the restored tip shows that nothing up to that anchor was rewritten; it **cannot** show that the restore reached the point you meant, because the cut is taken from the restore's own result. In those steps, fix N4: the number for `head -n` is the line number from `cat -n`, not the `id` — say so in the step, since in your example both are `2`.
7. **N1 — no anchor at or below the restore point** (a restore to before the first anchor; in the fallback, no anchor line at or below the tip): no anchor describes the restored log. What is left is `previously verify` without `--anchors`, with what that means, and the routine starts over with a first anchor in a new file as `` {ref}`verify-the-chain` `` shows. Do not let a reader arrive at `head -n 0`.

And outside that section:

- **First case, N2's second half:** say in `## Restore to the latest state` that there, every `anchored event is missing` is a loss — nothing to cut, the restore failed. A reader must not be able to carry "expect these findings" from the second section into the first.
- **N6:** a restore to a point after the newest anchor belongs to the first case; make its heading or its opening sentence cover it.
- **N5**, line 35: "although nothing is missing" states what no check sees. The finding `--exact` gives on events after the newest anchor says nothing about loss; say that.
- **N3**, `README.md` line 89: the link text still quotes the page's old title. Run `grep -rn "brought the chain back" README.md docs --include=*.md --exclude-dir=_build --exclude-dir=superpowers` and expect nothing afterwards.
- **`docs/how-to/verify-the-chain.md`, one sentence after the routine** (out-of-scope observation 1, taken in): when no event arrived since the last run, the routine appends the same line again; that is harmless, and it means the count in `chain intact, <n> anchors hold` counts lines, not events. Your round 1 session measured it in step 5.
- **`## Read the result`** has to agree with all of the above; reread it against the two sections once they are written.

Check the paragraph you added to `docs/explanation/hash-chain.md` in round 1 against the new section: if a sentence there now says something the guide no longer does, fix it; if not, leave the file alone.

## Measured or taken from the code

Every command the section shows was run in your round 1 session, and the output it quotes is in that transcript — the finding for a later anchor is step 4's first command, which is also what a restore that stopped short looks like against the file of the meant point. You do not need a new session unless you show a command that session did not run; if you do, run it and add the transcript. Say in the report which is which.

## Then

- Read the page top to bottom three times, as three operators, and write one line each into the report on where the page takes them:
  1. restored to the latest state, and the replay stopped short of the newest anchor;
  2. restored on purpose to a point three weeks back, anchor file under version control;
  3. restored on purpose to a point three weeks back, anchor file only ever appended on one host.
  The first must end at "the restore failed". The second must end at exit code `0` against the earlier file, or at a loss if the replay stopped short. The third must know, before they type anything, what their check cannot show.
- All six gates, each run separately, each closing line in the report:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `git status --short`, then stage by name — only what you changed among `docs/how-to/restore-from-a-backup.md`, `docs/how-to/verify-the-chain.md`, `docs/explanation/hash-chain.md`, `README.md` — and commit:

  ```
  fix: the restore check takes its yardstick from the restore point, not from the result

  The section on a restore to an earlier point cut the anchor file at the
  tip of the restored log. Against a file cut that way no anchor can be
  missing, so a restore that stopped short passed as the one that was
  meant. The file to check against is the anchor file as it stood at the
  restore point, known from the place it is kept; against it, a missing
  anchor is a loss. Cutting at the restored tip remains as the fallback for
  a file without a history, with what it cannot show said first.

  The guide also covers a restore to before the first anchor, says in the
  first case that a missing anchor is a loss, and no longer says of events
  after the newest anchor that nothing is missing. The README links the
  page by its current title.

  Assisted-By: Claude <the model you are> <noreply@anthropic.com>
  ```

  Adjust the body if what you built differs from it.

## Report

Append a section `## Fix round 2` to
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-report.md`:
what you changed per item; the three operator lines; which outputs are from the round 1 transcript and which are new; the six closing lines; deviations and why.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line gate summary (pytest count, Vale file count and errors)
- Concerns and disagreements, one line each
- The report file path
