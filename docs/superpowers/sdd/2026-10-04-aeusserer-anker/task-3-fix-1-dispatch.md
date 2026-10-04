Task 3, fix round 1. The task review found two Important findings, both on `docs/how-to/restore-from-a-backup.md`, and six Minor ones. The first Important one goes back to the specification, not to your work: its §5.1 describes the second restore case as if the anchor at the restore point were the newest line in the file, and the routine you documented on the other guide keeps appending lines.

The full review, for the exact wording of each finding (section `### Issues`):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-review.md`

Work in `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker`, as before. FIX_BASE is `a09f56a`. Make one new commit; do not amend; do not push. Invoke `plone-doc-style:author` again before you write: how-to for the two guides, explanation for the one paragraph on `hash-chain.md`.

## What to fix

### 1. Important 1 — a restore to an earlier point, checked against a file that has grown since

What the reviewer found, from the code: `--exact` compares the tip with the **newest** anchor in the file, and the ordinary check wants **every** anchor in the file. After a restore to an earlier point, every anchor taken after that point reports `anchored event is missing`, exit code 1 — and the page then says "the restore failed … Discard the instance and restore again". A correct restore is thrown away, and every repetition fails the same way.

The controller's ruling (T3-c in the ledger). The findings in that situation are **true**: a restore to an earlier point is a truncation, and seeing a truncation is what the anchors are for. So the page must not call them a failed restore, and it must say how to check the restore that was intended. The second case becomes **a restore to an earlier point**, and it carries these facts — your wording, in how-to form, each one checked against a real run:

- Checked against the whole anchor file, each anchor taken after the restore point reports `anchored event is missing (the log ends at <tip>)`. That is expected here: those lines anchor events this restore gave up.
- The check that fits is against the anchor file **as it stood at the restore point**: its lines up to and including the last anchor taken at or before that point. Show the cut as one plain shell line that works on any host (`head -n <N> anchors.txt > <another file>`), and the check against the cut file.
- How to find the line: the finding names the tip of the restored log (`the log ends at <tip>`); the cut is after the last anchor whose `id` is not above that tip.
- `--exact` belongs to this case **only if** the restore point coincides with that last anchor — its `id` is the tip. Then exit code `0` means in addition that the tip is exactly that anchor. Otherwise the ordinary check, and what it does not see above the newest anchor is the same as in the first case.
- Afterwards: the routine continues against the cut file, because against the old one it would raise the alarm on every run. Keep the old file; it is the record of what the restore gave up.

*Read the result* has to follow: exit code `1` is no longer one sentence. Against the file that fits the case, a finding means the restore does not hold what the anchors say. And say what exit code `2` is (Minor 3 below).

**Run it before you write it down**, in a scratch directory outside the worktree, against a fresh container the way the tutorial sets one up, and put the transcript into the report. One session covers this finding, the routine line you had not run as printed, and Minor 1:

1. On the empty log: `previously anchor > anchors.txt`, the exit code, and what the file holds.
2. Append an event; take the first anchor as the guide says. Twice more: append an event, then the routine line **exactly as the guide prints it**. Three anchors.
3. Append a fourth event and take no anchor. This is the first case: the ordinary check against `anchors.txt`, and the same with `--exact` — the second is the finding your page warns of.
4. Now stand in for a restore to the point of the second anchor: remove events 4 and 3 with raw SQL, newest first, the way `_delete_event` in `tests/test_verify.py` does it. Then: the check against the whole file; the cut; the check against the cut file with `--exact`.
5. The routine line once more against the cut file.

If a step does not behave as this dispatch says, the measurement wins: write what happens, and say so in the report.

### 2. Important 2 — `restore-from-a-backup.md`, "The events after the newest anchor came back from the write-ahead log, and this check doesn't vouch for them."

The first half states as a fact what no check can see. A replay that stopped early loses events above the newest anchor and passes all the same — row three of the table on `hash-chain.md`. Say it in both directions: what the restored log holds after the newest anchor is not vouched for, and what it should hold there and does not is not seen.

### 3. One short paragraph on `docs/explanation/hash-chain.md` (ruling T3-d)

The restore guide is a how-to and links instead of reasoning; the reason it now needs has no page yet. Under `(external-anchor)=`, where the page says that the interval between anchors is the gap, add a short paragraph: a restore to an earlier point is, to the anchors, the same thing as a deleted tip — because it is one — so every anchor taken after that point reports its event missing, truthfully; an anchor file describes one history, and after such a restore the history it describes has ended at an earlier line. Explanation quadrant: reasons, no steps. It must not promise anything the table on the same page does not hold. Then let the guide point there for the why.

### 4. Minor 1 — `verify-the-chain.md`, the first anchor and the routine

After the first anchor, have the reader check that the exit code is `0` and that the file holds one line, and say the two ways it does not: on an empty log `anchor` prints nothing to standard output and exits `0`, so the file is empty; on a chain with a finding it prints the `FINDING` lines to standard output and exits `1`, so they are in the file. For the routine, one sentence: if the second command exits other than `0`, what it printed is in the anchor file and has to be removed by hand before the next run. Step 1 of the session above measures the empty-log half; take the other half from `_cmd_anchor` and its test, and say in the report that you did.

### 5. Minor 2 — `restore-from-a-backup.md`, the opening sentence

"confirm, after any restore, that you got the chain back" promises more than the page holds. Say what the page does: check, after a restore, how much of the chain you got back. Look at the page title with the same eye and change it only if it makes the same promise.

### 6. Minor 3 — *Read the result* knows `1` and `0`, not `2`

A missing or broken anchor file is exit code `2`, an input error — a likely case right after a restore. One sentence, with a pointer to `` {ref}`cli-reference` ``.

### 7. Minor 4 — README, no bullet for the anchor under "What it does" (ruling T3-a)

The dispatch's "Nothing else" was too tight, and you followed it. Add the bullet in the style of its neighbors: what `anchor` and `verify --anchors` do. It promises nothing beyond the table on `hash-chain.md`.

### 8. Minor 5 — `docs/explanation/design-records.md`, "the one reference point outside the database that can"

Add the limit: up to the newest anchor.

### Not to change

- Minor 6: the sentence in the specification's introduction that says who gave the commitment and when **stays** (ruling T3-b) — provenance is what a frozen record is for.
- The specification is frozen and stays as you committed it. Its §5.1 is incomplete on the second restore case; where a frozen record and a page disagree, the page wins, and the execution record will say so. Do not edit `docs/superpowers/specs/`.
- `docs/reference/cli.md`, the tutorial, the code and the tests: untouched. The test count stays at 265, so the tutorial's test block stays as it is; confirm the count and leave the block.

## Then

- All six gates, each run separately, each closing line in the report:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- Read `restore-from-a-backup.md` once more as an operator at three in the morning with a restored instance and an anchor file that is three weeks longer than the backup: is every step there, in order, and can each be carried out as written?
- `git status --short`, then stage by name — only what you changed among `docs/how-to/restore-from-a-backup.md`, `docs/how-to/verify-the-chain.md`, `docs/explanation/hash-chain.md`, `docs/explanation/design-records.md`, `README.md` — and commit:

  ```
  fix: a restore to an earlier point is checked against the anchors of that point

  The restore guide had its second case check with --exact against the
  whole anchor file. --exact compares the tip with the newest anchor, and
  the routine keeps appending anchors, so a correct restore to an earlier
  point reported every later anchor as missing and the page said to
  discard it. Those findings are true — such a restore is a truncation —
  and the guide now says so, cuts the file at the restore point, and
  says which file the routine continues with.

  It no longer states that the events after the newest anchor came back:
  no check sees that. The guide for the routine says what the anchor file
  holds when the first anchor is taken on an empty log or the second
  command fails, the README names the anchor among what the software does,
  and the explanation says why a restore looks like a deleted tip.

  Assisted-By: Claude <the model you are> <noreply@anthropic.com>
  ```

  Adjust the body if what you built differs from it.

## Report

Append a section `## Fix round 1` to
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-3-report.md`:
what you changed per finding; the raw transcript of the session; where a step behaved differently from this dispatch; the six closing lines; deviations and why.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line gate summary (pytest count, Vale file count and errors)
- Concerns and disagreements, one line each
- The report file path
