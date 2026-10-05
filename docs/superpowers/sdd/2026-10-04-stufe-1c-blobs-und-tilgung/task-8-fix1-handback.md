# Task 8, fix round 1 — the implementer's report, as handed back

Filed by the controller on 2026-10-05. The controller asked for this report as
the implementer's final message instead of a file; what follows is that
message, unchanged apart from this note.

---

**Status:** DONE. All eight findings are fixed in one commit, `1ec0b2e` on top of `789533e`. It touches pages, the README and the map only. No source, test, migration, frozen spec or `CLAUDE.md` changed. The commit message is in `.superpowers/sdd/2026-10-04-stufe-1c-blobs-und-tilgung/task-8-fix1-commit-msg.txt`, trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`. I started no container and no output block was edited.

**Gates** (run after the commit, each on its own):
- `uv run ruff check .`: All checks passed!
- `uv run ruff format --check .`: 69 files already formatted
- `uv run pyright`: 0 errors, 0 warnings, 0 informations
- `uv run lint-imports`: Contracts: 6 kept, 0 broken.
- `uv run pytest --cov --cov-report=term-missing`: ======================== 606 passed in 72.60s (0:01:12) ========================
- `make -C docs html`: build succeeded.
- `make -C docs vale`: ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
- `make -C docs linkcheck`: exit 0, nothing broken.

**Map count:** the awk command now gives **94**. No page or sentence outside the execution records names 93 (checked with grep over `README.md` and `docs/`).

## Finding 1 — repeating an erasure after a restore

### The four questions, answered from the code

1. **Which erasures still have their target.**
   - `redact event` and `redact units` name an event by its `id`.
   - Every new id is tip + 1: `redact.py:136` (`event_id=1 if tip is None else tip.id + 1`) and `append.py:365`.
   - The restored log holds the same events as before up to its tip, so an erasure whose target id is at or below the restored tip still has its target.
   - A target above the tip was appended after the restore point and went with the restore. That erasure needs no repeat, but its id is free again and can belong to another event.
   - Confirming by **hash** works, and I found no reason in the code against it:
     - `show` prints `hash=…` for every event, erased ones included (`cli.py:559`, unconditional).
     - The hash is the restored row's own value.
     - The hash covers `id`, `prev_hash` and the salt, so another event at the same id has another hash.
2. **How the reader learns the restored tip.** `cli.md` says `previously anchor` prints `<id> <hash>` of the last event. The guide uses that. `log` has no "tip" output.
3. **What a repeated `redact blob` reaches.**
   - It reads the blob's users when it runs (`redact.py:342`: `events_by_blob`, then `_unerased`).
   - So it erases the reference of every event that uses the blob at that moment, including an event that attached the same content again after the restore.
   - If nothing has been appended since the restore, the events it reaches are restored events that the original erasure also named.
4. **Order.**
   - For `redact blob`, order matters. It must run before anything else appends, or it reaches new events.
   - For `redact event` and `redact units`, the hash check makes order irrelevant. Even a tip learned after new appends only lets more targets through to the hash check, which then refuses them.
   - I did not claim more than that.

### What changed
- **`docs/how-to/restore-from-a-backup.md`** (section "Check the blobs, and repeat the erasures"):
  - Repeat only the erasures whose target the restored log still holds.
  - The record kept outside the database holds the command, its date, and for `redact event` and `redact units` the target id and its hash.
  - "Don't repeat … by its `id` alone", with the reason: a restore frees ids.
  - Learn the tip from `previously anchor`; a target above it went with the restore.
  - Otherwise run `previously show <id>` and compare the hash:
    - same hash → repeat the command as it was;
    - different hash or `No event 42` → don't repeat.
  - The `redact blob` paragraph: what a repeat reaches, and that blob erasures are repeated before anything else appends.
- **`docs/how-to/erase-something.md`**: a new section "Keep a record of the erasure" with the same fields. It says `show` prints the hash on its third line and that an erasure doesn't change it, so the reader notes it when erasing.
- **`docs/explanation/erasure.md`** (the "Restoring brings it back" paragraph): the reason in four sentences — ids are freed, the hash survives and is unique, a pointer to the guide, and the reach of a repeated `redact blob`.
- **Other places:** grep for repeat/repeated/wiederhol over `README.md` and `docs/` finds only `erasure.md:161` and the restore guide as places that tell the reader to repeat erasures. `blobs.md`, `backup-encryption.md` and `README.md` don't, so they needed no limit.
- **Map, under *Tilgung*:** a new point: the target is an id, an id doesn't survive a restore, the guide confirms by hash, and whether `redact` should check against the hash itself is undecided.

## Finding 2 — the reach of `redact units`
- **`erasure.md`, Units row of the table:** "What stays" now adds: "including a copy of their wording where the payload repeats it, as it does for every event `previously append --text` writes".
- **`erasure.md`, *What an erasure doesn't do*:** a new bold item, "An erasure of units leaves what the payload repeats.", pointing to the earlier paragraph.
- **`README.md`, limits paragraph:** one clause — "an erasure of units leaves their wording in the payload, where `append --text` puts the whole text of every event it writes".
- **`erase-something.md`, closing section:** one sentence to the same effect.
- I did not decide which event shapes erasing units is meant for.

## Findings 3 to 8
3. **Tutorial, line 39:** "…and a warning that uv can't link its files from its cache, which it prints when its cache and your checkout lie on different file systems." I wrote "link" because Vale rejects "hardlink" as a misspelling.
4. **`backup-encryption.md`:**
   - Line 5 → "The backups this design plans for Previously are encrypted on the client … ; no backup runs yet."
   - Line 100 → "The backups this design plans are encrypted…"
5. **Tutorial, line 67** → "The third brings hash format 2, in which every event gets a salt of its own, and our event is written in it; the fourth prepares the log for attached files, which this tutorial doesn't use."
6. **Map, lines 24 to 33:**
   - The intro reads: "Stufe 1c ist auf dem Zweig `worktree-stufe-1c-blobs` gebaut; abgenommen ist sie mit dem Merge dieses Zweigs nach `main`, und nicht vorher".
   - The acceptance column reads: "der Merge des Zweigs `worktree-stufe-1c-blobs` nach `main`".
   - The Teilprojekt sentence reads: "Abgeschlossen ist es mit dem Merge dieses Zweigs."
   - All three hold before and after the merge.
7. **`verify-the-chain.md`, line 92** → "`--blobs` reads every blob that has to lie in the store, opens it, and checks it against its address, and it asks the store whether an erased blob is gone…" The README bullet said the same wrong thing and got the same fix: "every blob that has to lie in the store is read…".
8. **`erase-something.md`** (old line 137, now further down after the new section) → "Without `--blobs`, `verify` reads no blob setting; leave `--blobs` out if the log names no blob."

## Disagreements or open items
None.
