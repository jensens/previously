# Task 3 report — documentation, tutorial retyped, spec frozen

Status: DONE_WITH_CONCERNS (concerns are small; see the end)

Commit: `a09f56a docs: the anchoring routine, a restore in two cases, and the spec frozen`
Trailer: `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>` (the session's system reminder asked for a `Co-Authored-By` line; `CLAUDE.md` forbids it and overrides it, so it is not there).

## What I wrote, page by page

### `docs/how-to/verify-the-chain.md`
- Dropped "It takes no arguments."
- The exit-code-0 sentence now says what a terminal shows: `chain intact` on stdout plus the no-anchor notice on stderr.
- Exit code 1: "the chain or an anchor has at least one finding" (matches the exit-code table in `cli.md`). Exit code 2: "invalid input or a storage error" (same table).
- Closing paragraph rewritten into what exit code 0 means **without** anchors: consistent in itself, nothing more; a deleted tip, an appended event, or a chain rewritten from the start can each pass (the three manipulations of the chain alone on `hash-chain.md`). Points to the new section only as "check the log up to a point you recorded outside the database" — no promise beyond the table.
- New section `## Anchor the chain, and check against the anchors`: where the file lives (where the DB's writer can't write; not on the DB's own host or volume), first time `previously anchor > anchors.txt` (once the log holds an event — on an empty log `anchor` prints nothing, and an anchor file without a line is an input error per `cli.md`), the routine `previously verify --anchors anchors.txt && previously anchor >> anchors.txt`, non-zero exit is an alarm, `-` for stdin with `previously verify --anchors - < anchors.txt` (run for real, see transcript), links to `cli-reference` and `external-anchor`. No Kubernetes or compose syntax. No admonition.

### `docs/how-to/restore-from-a-backup.md`
- "the restore is trustworthy" is gone.
- Two new sections: `## Restore to the latest state` (`verify --anchors anchors.txt`; 0 = up to the newest anchor nothing lost or rewritten; events after it came from the WAL and are not vouched for; don't add `--exact`, it would report them although nothing is missing) and `## Restore to a fixed point that coincides with an anchor` (adds `--exact`; 0 additionally = the tip is exactly that anchor; fits a named restore point right after anchoring or a logical dump taken with its anchor) — both from spec §5.1.
- `## Read the result`: exit 1 = restore failed; without an anchor file, exit 0 = consistent in itself, nothing more, and a restore from an older state passes too.
- Passphrase paragraph and the `important` "never rehearsed" admonition kept; one admonition on the page. Links to `verify-the-chain`, `external-anchor`, `backup-encryption`, `configuration-reference`.

### `README.md`
- "the seven commands …" → "the eight commands `append`, `log`, `verify`, `anchor`, `show`, `project`, `chronicle` and `stats`".
- Limit paragraph rewritten: the chain by itself attests unchanged, not complete; an external anchor adds completeness up to the newest anchor (deleted or rewritten event below it shows); a tip deleted above the newest anchor shows nowhere; a forged appended event shows only against an anchor taken at rest. Checked row by row against the table on `hash-chain.md`.
- "four specifications" → "five", fifth table row `External anchor`, "Frozen design record, 2026-10-04", with the pages carrying its reasoning and routines.
- "What it does not do" untouched. I had briefly added a "What it does" bullet for the anchor and removed it again because resolution 4 says "Nothing else" — see concerns.

### `docs/tutorials/record-your-first-event.md`
- Every session block retyped from one run (transcript below): `log`, `verify`, the new pin step, `show`, `project` ×2, `chronicle`, `stats` share timestamp `2026-10-04T13:24:54.151385+00:00` and hash `52a060a8734b…`.
- `verify` block now shows both lines; text after it: first line says `chain intact`, "Notice that a second line follows, and that it names a command we haven't run yet", stderr shown below it by the terminal.
- New `## Pin the tip` after `## Check the chain`, the two commands from the brief with their real output, "Notice that the first line is now a different one …" and "Notice also that the second line is gone." No explanation of what an anchor closes; a new line under *Next steps* links to `external-anchor`.
- Intro sentence and *Next steps* summary gain "pin its tip".
- `uv sync` block left as it was: the fresh run on a TTY printed a machine path (`Building previously @ file:///tmp/…`, and `previously==0.1.dev91 (from file:///tmp/…)` in the package list) plus a uv hardlink warning; the page says no output names a directory.
- Test block retyped last from a real `uv run pytest` run at 265, `rootdir:` line removed.

### `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`
- Header copied byte for byte from lines 3–14 of the stage 1b spec (by script, not by hand); date 2026-10-04 = commit date.
- `Status: Entwurf, zur Abnahme` → `Status: eingefroren`.
- Intro: the freeze announcement dropped. Kept "Dieser Spec ist klein: keine Stufe, sondern die Einlösung einer Zusage." **plus** the next sentence (maintainer gave the commitment on 2026-10-04, it was point 1 in §10 of the 1b spec) — see deviations.
- §10 intro in the past tense: was maintained while the spec lived, had taken over 1b §10 and the 1b execution record's items, "seine fünfzehn Punkte gehören in den Spec, der diesem folgt". Counted: `grep -cE '^[0-9]+\. '` over §10 → 15; read by eye 1–15, no gaps.
- Line 400 (§8, "fünfte eingefrorene Bericht, wenn dieser Spec einfriert") left as written: it is the frozen plan of the time.

### `docs/explanation/design-records.md`
- "Four German documents …" → five, naming the external anchor; "the other two on 2026-10-04".
- New paragraph after the stage 1b paragraph: the anchor spec, dated 2026-10-04, no stage but a promise kept, froze once its pages stood; `external-anchor` carries its reasoning, `cli-reference` the facts, `verify-the-chain` and `restore-from-a-backup` the routines.
- After the stage 1b measurement: "No row names the specification of the external anchor either … Measured … on 2026-10-04, every paragraph sign … carries the `(frozen design record)` marking, and the fifteen lines that hold one are the same fifteen as before the anchor was built …". `CLAUDE.md` not touched.

## The two greps

```
$ grep -rn "§" src tests migrations | grep -v "frozen design record"
(empty)
$ grep -rn "§" src tests migrations | wc -l
15
```

The page names no current count before my edit (it names the historic 72); I added "fifteen". Control: `git grep -h "§" main -- src tests migrations | sort` against `grep -rh "§" src tests migrations | sort` → identical, so the anchor branch added no `§` line and none points at its spec.

## Raw transcript of the tutorial run

Fresh clone of the branch HEAD (`1df139c`) into the scratchpad, fresh `postgres:17` container started with the tutorial's own `docker run` line on port 5432, `PREVIOUSLY_DSN` as on the page; every command run under `script` (a pty, so stdout and stderr interleave as on a terminal); ANSI codes stripped afterwards. The `append` was typed on one line rather than with the page's backslash continuations — same argv. The `cat anchors.txt` and the stdin line are extra checks, not on the tutorial page. The `uv sync` package list (`+ …` lines) is cut here; it contained `previously==0.1.dev91 (from file:///tmp/claude-1000/…/scratchpad/run)`.

```
$ uv sync --all-extras
Using CPython 3.14.3
Creating virtual environment at: .venv
Resolved 74 packages in 0.93ms
[progress spinner] Building previously @ file:///tmp/claude-1000/-home-jensens-ws-jwk-previously
[progress spinner] Built previously @ file:///tmp/claude-1000/-home-jensens-ws-jwk-previously
Prepared 1 package in 573ms
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
Installed 71 packages in 207ms
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
INFO  [alembic.runtime.migration] Running upgrade 0001_log -> 0002_projections, Projections: state, chronicle, source statistics
$ uv run previously append --source email --external-id 2026-10-03-kickoff@example.org --text "The client approved the new homepage design.

Next milestone: content migration starts Monday."
1
$ uv run previously log
1	2026-10-04T13:24:54.151385+00:00	observation	52a060a8734b
$ uv run previously verify
chain intact
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
$ uv run previously anchor > anchors.txt
$ uv run previously verify --anchors anchors.txt
chain intact, 1 anchor holds
$ cat anchors.txt
1 52a060a8734ba42c073985683adce79da3ba550a9d26902a6f7a60fb451f9f17
$ uv run previously verify --anchors - < anchors.txt
chain intact, 1 anchor holds
$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-04T13:24:54.151385+00:00
hash=52a060a8734ba42c073985683adce79da3ba550a9d26902a6f7a60fb451f9f17
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
$ uv run previously project
chronicle       built: 1 event, up_to_id 1
source-stats    built: 1 event, up_to_id 1
$ uv run previously project
chronicle       up to date, up_to_id 1
source-stats    up to date, up_to_id 1
$ uv run previously chronicle
1	1	2026-10-04T13:24:54.151385+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-04T13:24:54.151385+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
$ uv run previously stats
email	1	2	2026-10-04T13:24:54.151385+00:00	2026-10-04T13:24:54.151385+00:00
```

Container removed afterwards (`docker rm -f previously`).

## Raw transcript of the test run (the tutorial's block)

Run in the worktree after all page edits (docs tests read the pages), before the commit:

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=600064971
rootdir: /home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0, randomly-5.0.0, platformdirs-4.12.2, hypothesis-6.168.3
collected 265 items

tests/test_verify.py .........................                           [  9%]
tests/test_cli.py .................................................      [ 27%]
tests/test_schema.py .............                                       [ 32%]
tests/test_docs_references.py .....                                      [ 34%]
tests/test_hashing.py ........................                           [ 43%]
tests/test_rows.py ....                                                  [ 45%]
tests/test_projection_store.py ........                                  [ 48%]
tests/test_migrations_dsn.py ...                                         [ 49%]
tests/test_projection_derive.py .........                                [ 52%]
tests/test_contracts.py ..                                               [ 53%]
tests/test_docs_typed_output.py .                                        [ 53%]
tests/test_projection_worker.py ............                             [ 58%]
tests/test_properties.py .........                                       [ 61%]
tests/test_append.py ..............................                      [ 73%]
tests/test_docs_build.py ......                                          [ 75%]
tests/test_canonical.py ...............                                  [ 81%]
tests/test_anchor.py ...........                                         [ 85%]
tests/test_storage.py ..........................                         [ 95%]
tests/test_units.py .............                                        [100%]

============================= 265 passed in 22.23s =============================
```

## Measured test count

`uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected in 0.16s`.

## The six gates (run separately, after the last edit, before the commit)

```
uv run ruff check .                          → All checks passed!
uv run ruff format --check .                 → 50 files already formatted
uv run pyright                               → 0 errors, 0 warnings, 0 informations
uv run lint-imports                          → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 265 passed in 23.00s =============================
                                               (Total coverage: 97.65%)
make -C docs html                            → build succeeded.
make -C docs vale                            → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                       → build succeeded.  (0 "broken" in _build/linkcheck/output.txt)
```

## Files changed (all six staged by name; `git status --short` was clean of anything else, and clean after the commit)

- `README.md`
- `docs/explanation/design-records.md`
- `docs/how-to/restore-from-a-backup.md`
- `docs/how-to/verify-the-chain.md`
- `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`
- `docs/tutorials/record-your-first-event.md`

## Deviations

1. **Spec intro kept one sentence more than the brief's wording.** The brief: the intro "fällt bis auf den Satz, dass der Spec klein ist und eine Zusage einlöst". I kept that sentence and the one after it (who gave the commitment, when, and that it was point 1 of the 1b spec's §10), because dropping it would erase the provenance of the commitment from the one document that is provenance. Easy to cut if the controller reads the brief strictly.
2. **`design-records.md` names a count ("fifteen").** The page named no current `§` count to compare against; I stated the measured one with its date.
3. **Tutorial `append` run on one line**, not with the page's backslash continuations; the argv is identical.
4. **Test block typed from the worktree run**, not the fresh clone; the clone was at the pre-docs HEAD, and the docs tests must read the edited pages. Same code otherwise.

## Concerns

- **README "What it does" has no anchor bullet.** The list names every other feature with a bullet and now mentions `anchor` only inside the eight-commands line. I removed my bullet to respect "Nothing else" in resolution 4; the controller may want it back.
- **`verify-the-chain.md` says "A file on the database's own host or volume doesn't count."** That is spec §5.1's single-host argument (root writes both) compressed into one line; it is a judgement, not something the code checks.
- **The first-anchor step on an empty log:** I wrote "Once the log holds at least one event" because `anchor` prints nothing on an empty log and `verify --anchors` on a file without an anchor line is an input error (per `cli.md`). Not run for real in this task.
- The routine line `verify --anchors … && anchor >> …` was not run end to end as one line; its two halves were (`anchor > anchors.txt`, `verify --anchors anchors.txt`, and the stdin form).

## Fix round 1

Commit: `da79b41 fix: a restore to an earlier point is checked against the anchors of that point` (on top of FIX_BASE `a09f56a`, no amend, not pushed; five files staged by name, tree clean afterwards). The trailer is `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`. The commit body is the dispatch's text, unchanged, because what I built matches it.

### Changes per finding

- **Important 1 (ruling T3-c).** In `restore-from-a-backup.md` the second case is now `## Restore to an earlier point`. It works in this order:
  1. Check against the whole file first. Every later anchor gives `FINDING <id>: anchored event is missing (the log ends at <tip>)`; the page quotes the measured line and says these findings are expected and are no reason to discard the instance. It links `external-anchor` for the why.
  2. A numbered procedure: read the tip from the finding; run `cat -n anchors.txt`; find the last line whose `id` isn't above the tip; cut with `head -n 2 anchors.txt > anchors-restored.txt` (shown for line 2 as an example); check with `--exact` only if the last anchor's `id` is the tip, otherwise without it, and say what each exit code `0` means.
  3. Afterwards the routine continues against `anchors-restored.txt`, and `anchors.txt` is kept unchanged as the record of what the restore gave up.

  In *Read the result*, exit code `1` now applies to "the anchor file that fits your case".
- **Important 2.** Replaced with two sentences: whatever the restored log holds after the newest anchor, the check doesn't vouch for; whatever it should hold there and doesn't, the check doesn't see. The `--exact` warning in the first case now reads "any event after the newest anchor would be reported", with no claim that the events came back.
- **T3-d, `hash-chain.md`.** A new paragraph after the gap paragraph under `(external-anchor)=`:
  - A restore to an earlier point looks like a deleted tip because it is one.
  - Every later anchor reports its event missing, and the report is true.
  - An anchor file describes one history, which after such a restore has ended at an earlier line.
  - The lines up to it still describe the restored log, and the ones after it record what was given up.

  It contains no steps and promises nothing beyond the table. It is row 1 of the table, applied.
- **Minor 1, `verify-the-chain.md`.**
  - After the first anchor, the reader checks that the exit code is `0` and that the file holds exactly one line. The page names the two ways that fails: an empty log gives no stdout, exit 0 and an empty file; a chain with a finding puts `FINDING` lines on stdout, exit 1, and they end up in the file. The reader then deletes the file and fixes the cause.
  - For the routine: if the second command exits other than `0`, what it printed to standard output is in the file and has to be removed by hand.
  - The empty-log half is measured (step 1 below). The finding half comes from `_cmd_anchor` (`src/previously/cli.py:286-290`: it prints the `FINDING` lines with `print` to stdout and returns 1) and from `test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain` (`tests/test_cli.py:1006`). I did not run it in the session.
- **Minor 2.** The opening now reads "how to check, after a restore, how much of the chain you got back". The title made the same promise ("brought the chain back") and is now "How to check how much of the chain a restore brought back". The label `restore-from-a-backup` is unchanged, so no reference breaks.
- **Minor 3.** *Read the result* now covers exit `2`: nothing was checked; the anchor file is missing or unreadable, a line isn't an anchor line, or storage raised an error; the message on stderr names it; a pointer to `cli-reference`. Measured: a missing file gives `Error: cannot read the anchor file 'no-such-file.txt': No such file or directory`, exit 2.
- **Minor 4 (T3-a).** Added a README bullet "**the external anchor** (`anchor`, `verify --anchors`)":
  - what `anchor` prints and where it is kept;
  - what `verify --anchors` checks;
  - "so that up to the newest anchor nothing can go missing or be rewritten unseen".

  That matches table rows 1 and 2 and claims nothing above the newest anchor.
- **Minor 5.** `design-records.md` now reads "… that can, up to the newest anchor."
- **Not changed:**
  - the specification, including the sentence about who gave the commitment (T3-b);
  - `cli.md`, the tutorial, code and tests.

  The test count was measured again at 265 (`265 tests collected in 0.17s`), so the tutorial's test block stays as it is.
- **Vale caught two `Microsoft.Contractions` errors in my new text** ("as it is", "that's what it is"). I reworded both: "unchanged", and "because it's one".

### Session transcript

Setup:
- a fresh `postgres:17` container, started with the tutorial's `docker run` line;
- the clone's venv from the first round in the scratchpad (code identical to the branch);
- `alembic upgrade head`;
- the scratch directory `…/scratchpad/fix1`, outside the worktree;
- `previously` called as on the guide, with stdout and stderr merged, and `[exit N]` added after each command;
- events appended with `previously append --source email --external-id mN --text "Event N"`;
- raw SQL through `docker exec … psql`, in the order `_delete_event` uses.

```
## step 1: empty log
$ previously anchor > anchors.txt
the log is empty: nothing to anchor
[exit 0]
$ wc -l < anchors.txt; cat anchors.txt
0
[exit 0]
## step 2
(appended event 1)
$ previously anchor > anchors.txt
[exit 0]
$ wc -l < anchors.txt
1
[exit 0]
(appended event 2)
$ previously verify --anchors anchors.txt && previously anchor >> anchors.txt
chain intact, 1 anchor holds
[exit 0]
(appended event 3)
$ previously verify --anchors anchors.txt && previously anchor >> anchors.txt
chain intact, 2 anchors hold
[exit 0]
$ cat anchors.txt
1 7081052bc9b00fdb40b5360e0018a462a8113c4eb2b2e3b0bb235ef3e4c851be
2 0cda004f8539ed33ea84c43c58962d54f07cc4171e00256bcfc6e2c51d17cf45
3 0d43f7a6b8958e2d1a7164d45e403db9eaf83f51af7c885d6005ddc43e5e1d57
[exit 0]
## step 3: event 4, no anchor
(appended event 4)
$ previously verify --anchors anchors.txt
chain intact, 3 anchors hold
[exit 0]
$ previously verify --anchors anchors.txt --exact
FINDING 4: the log continues past the newest anchor (3)
[exit 1]
## step 4: stand-in restore to the point of the second anchor
$ psql: DELETE FROM source_key WHERE event_id = 4; DELETE FROM unit WHERE event_id = 4; DELETE FROM event WHERE id = 4;
$ psql: DELETE FROM source_key WHERE event_id = 3; DELETE FROM unit WHERE event_id = 3; DELETE FROM event WHERE id = 3;
$ previously verify --anchors anchors.txt
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ previously verify --anchors anchors.txt --exact
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ head -n 2 anchors.txt > anchors-restored.txt
[exit 0]
$ cat anchors-restored.txt
1 7081052bc9b00fdb40b5360e0018a462a8113c4eb2b2e3b0bb235ef3e4c851be
2 0cda004f8539ed33ea84c43c58962d54f07cc4171e00256bcfc6e2c51d17cf45
[exit 0]
$ previously verify --anchors anchors-restored.txt --exact
chain intact, 2 anchors hold, the tip is the newest anchor
[exit 0]
## step 5: routine against the cut file
$ previously verify --anchors anchors-restored.txt && previously anchor >> anchors-restored.txt
chain intact, 2 anchors hold
[exit 0]
$ cat anchors-restored.txt
1 7081052bc9b00fdb40b5360e0018a462a8113c4eb2b2e3b0bb235ef3e4c851be
2 0cda004f8539ed33ea84c43c58962d54f07cc4171e00256bcfc6e2c51d17cf45
2 0cda004f8539ed33ea84c43c58962d54f07cc4171e00256bcfc6e2c51d17cf45
[exit 0]
## extra: missing anchor file
$ previously verify --anchors no-such-file.txt
Error: cannot read the anchor file 'no-such-file.txt': No such file or directory
[exit 2]
```

Container removed afterwards.

### Where the measurement differed from the dispatch, or adds to it

- Every step behaved as the dispatch describes.
- In step 1, stderr carries `the log is empty: nothing to anchor`. That is what the guide says: nothing on stdout, exit 0, empty file.
- In step 4, `--exact` against the whole file reports only `anchored event is missing`, not also `continues past`. The tip (2) is below the newest anchor (3), so that is correct.
- Step 5, an addition: when the routine runs with no new event since the last anchor, it appends a duplicate line for the same tip. `cli.md` allows the same `id` on several lines, and the next run counts every line ("n anchors hold"). It is harmless, but the anchor count grows with runs, not with events. I did not document it.

### Six gates, after the last edit

```
uv run ruff check .                           → All checks passed!
uv run ruff format --check .                  → 50 files already formatted
uv run pyright                                → 0 errors, 0 warnings, 0 informations
uv run lint-imports                           → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 265 passed in 24.26s =============================
make -C docs html                             → build succeeded.
make -C docs vale                             → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                        → build succeeded.  (0 "broken" in output.txt)
```

### Deviations

- **The cut uses a concrete `head -n 2` example, not a `<N>` placeholder.** A placeholder in a `shell` block reads as a redirect, and the example matches the measured session. The steps around it say how to find the line.
- **The page title was changed (Minor 2).** The label is unchanged.

### The read at three in the morning

The situation: a restored instance, and an anchor file three weeks longer than the backup.
1. The operator runs the whole-file check and gets several `anchored event is missing (the log ends at T)` findings.
2. The page says these are expected for a restore to an earlier point, and not to discard the instance.
3. `cat -n` → find the last line with id ≤ T → `head -n <that line>` → check (with `--exact` only if that id equals T).
4. Continue the routine against the new file, and keep the old one.

Every step can be carried out as written. What remains is that the operator has to know whether they restored to the latest state or to an earlier point. On a latest-state restore, the same findings mean a real loss, and *Read the result* sends that to "discard". Both sections say which restore they are for.

## Fix round 2

Commit: `7c936be fix: the restore check takes its yardstick from the restore point, not from the result` (on top of FIX_BASE `da79b41`, no amend, not pushed). I staged three files by name: `README.md`, `docs/how-to/restore-from-a-backup.md`, `docs/how-to/verify-the-chain.md`. The tree was clean afterwards. The commit body is the dispatch's text plus one clause about the duplicate-line sentence. The trailer is `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Changes per item (ruling T3-f)

- **Items 1 to 3, the main path of `## Restore to an earlier point`.**
  - **Step 1:** get the anchor file as it stood at the restore point from where you keep it (the version of that time under version control, or the copy or message from that time). The step says the file doesn't date its own lines, so that version can't be read off the current file. It saves the file as `anchors-restored.txt`, and forks to *After the check* (no file or no anchor yet) or to the fallback (no history).
  - **Step 2:** check against that file. Exit `0` means nothing lost or rewritten up to that file's newest anchor, with the same limit as in the first case. An `anchored event is missing` against it is a loss: the restore stopped short.
  - **Step 3:** `--exact` if the restore point coincides with the file's last anchor.
- **Item 4.** A paragraph after the steps, not a step:
  - against today's file, every later anchor reports `FINDING 3: anchored event is missing (the log ends at 2)` (quoted from the round 1 transcript, step 4);
  - those findings are true, which is why the check runs against the earlier file;
  - the pointer to `external-anchor` stays.
- **Item 5.** `### After the check`: the routine continues against `anchors-restored.txt`, and `anchors.txt` is kept unchanged.
- **Item 6.** `### If the anchor file has no history`:
  - It states the limit first, before any command: the cut shows that nothing up to its last anchor was rewritten; it can't show that the restore reached the point you meant, because the cut comes from the result of the restore itself.
  - Then the round-1 steps. Step 1 runs the whole-file check to read the tip.
  - N4: the line says "note its line number, the number `cat -n` prints in front of it" and "Pass the line number to `head -n`, not the `id`, even though both are `2` in this example".
- **Item 7 (N1).**
  - Under *After the check*: if no anchor is at or below the restore point (for example, a restore to before the first anchor), no anchor describes the restored log. Run `previously verify` without `--anchors` (consistent in itself only, as *Read the result* says), then start over with a first anchor in a new file per `verify-the-chain`.
  - The fallback's step 2 says "If no anchor line has an `id` at or below the tip, don't cut" and points there, so no reader reaches `head -n 0`.
  - The main step 1 points there as well.
- **N2, second half.** `## Restore to the latest state` now says: "Here, every `anchored event is missing` finding is a loss: the restore stopped short of an anchor, and it failed. There's nothing to cut; see *Read the result*."
- **N6.** That section's opening now reads "… to the latest state, or to any point after the newest anchor".
- **N5.** Now reads: "Don't add `--exact` here: it reports any event after the newest anchor as a finding, and that finding says nothing about loss."
- **N3.** The README link text now reads "How to check how much of the chain a restore brought back". `grep -rn "brought the chain back" README.md docs --include=*.md --exclude-dir=_build --exclude-dir=superpowers` → no output (rc 1).
- **`verify-the-chain.md` (observation 1).** After the routine: "If no event arrived since the last run, the routine appends the same line again. That's harmless, and it means that the count in `chain intact, <n> anchors hold` counts lines, not events." This is measured in round 1, step 5.
- **`## Read the result`, reread against both sections.**
  - Exit `1` now ends with "and the restore failed … Discard the instance and restore again."
  - One sentence names the single check whose findings are expected: the fallback's first step, which only reads the tip.
  - Exit `2` gains "holds no anchor line". That is the `head -n 0` / empty-file case (`parse_anchors`, and `cli.md`'s "input without a single anchor line").
  - The no-anchor paragraph now also covers "no anchor describes the restored log".
- **`hash-chain.md`: left alone.** Its round-1 paragraph says a restore to an earlier point is a deleted tip, that the later anchors report truthfully, and that the anchors up to the restore point still describe the restored log. All of that still agrees with the guide; nothing in it relied on the cut-at-the-tip yardstick.
- **Vale caught one error in new text** (`Vale.Spelling` on "restore's"). It now reads "the result of the restore itself".

### Where the outputs come from

- **No new session.** Every command the section shows was run in the round 1 session: `verify --anchors anchors.txt`, `cat -n`'s counterpart `cat`, `head -n 2 anchors.txt > anchors-restored.txt`, `verify --anchors anchors-restored.txt [--exact]`, and plain `verify`. The file names match.
- `cat -n anchors.txt` itself was not run. It only numbers lines and its output is not quoted on the page.
- The one quoted output, `FINDING 3: anchored event is missing (the log ends at 2)`, is from round 1, step 4, first command.
- In the main path, the same command against a restore-point file is the same invocation with a file taken from elsewhere. Its result was not separately measured: a restore that stopped short against the meant file would look like round 1, step 4.

### The three operators

1. Restored to the latest state and the replay stopped short of the newest anchor. They run the first section's check, get `anchored event is missing`, and the section says "every … finding is a loss … it failed. There's nothing to cut; see *Read the result*", which says "the restore failed … Discard the instance and restore again."
2. Restored on purpose three weeks back, anchor file under version control. Main step 1 takes the file at that version, step 2 checks against it. Exit `0` ends in *After the check* (continue the routine against that file, keep `anchors.txt`). If the replay stopped short, step 2 reports `anchored event is missing`, which the step calls a loss, and *Read the result* says the restore failed.
3. Restored on purpose three weeks back, file only ever appended on one host. Step 1 sends them to *If the anchor file has no history*, whose first four sentences state what the cut can't show before the first command. Then they cut by line number, or, with no anchor at or below the tip, go to *After the check* and plain `verify`.

### Six gates, after the last edit

```
uv run ruff check .                           → All checks passed!
uv run ruff format --check .                  → 50 files already formatted
uv run pyright                                → 0 errors, 0 warnings, 0 informations
uv run lint-imports                           → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 265 passed in 23.89s =============================
make -C docs html                             → build succeeded.
make -C docs vale                             → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                        → build succeeded.  (0 "broken" in output.txt)
```

### Deviations

- **The restore-point file is named `anchors-restored.txt`, the same name as the fallback's cut file.** Every command shown then matches the round 1 session, and both paths continue the routine against one name.
- **I added `### After the check` as a subsection.** It is shared by the main path and the fallback, so the routine and no-anchor guidance is written once.
- **One extra clause in the commit body** (the duplicate-line sentence on `verify-the-chain.md`). The dispatch said to adjust the body if needed.
