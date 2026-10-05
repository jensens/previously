# Final fix wave, part 2: the pages

The final review of the whole branch ran in two halves. The code half is fixed
(part 1, by another implementer). You fix what the documentation half found,
make the pages follow what part 1 changed in the code, carry the new open
points into the map, and retype the tutorial's test block last.

`WS/` means
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs/.superpowers/sdd/2026-10-04-stufe-1c-blobs-und-tilgung/`.

## Read first

1. `WS/final-review-docs.md` — the review of the pages: findings 1 to 21, each
   with file and line. You fix **all** of them. The decisions below say how
   where the review leaves a choice; where the review and this brief differ,
   the brief holds.
2. `WS/final-fix-code-report.md` — what part 1 changed: every new or changed
   wording of the command line, the new errors, the lock, the test count, and
   the three things it left for you.
3. The code itself, wherever you write a sentence about what a command does,
   prints, locks, deletes or refuses. A page must not say something the code
   does not do; that was the defect behind almost every finding of this
   review.

## The findings of the review, with the controller's decisions

1. **Critical — `docs/reference/cli.md`, `redact units`.** The section states
   that the payload stays, and that `previously append --text` puts the whole
   text into the payload as well as into the units, so that for an event it
   wrote the erased wording stays readable there. The `append` section states
   what the payload holds (take it from `src/previously/cli.py` and
   `core/append.py`, not from memory). Part 1 added the notice `redact units`
   now prints on standard error; the section has to read as one piece with it.
2. **The restore guide and `erasure.md`: a blob erased before the restore
   point and attached again after it.** Measured by the controller on
   2026-10-05 at `d02aaf6`, against RustFS 1.0.1: after the restore,
   `previously verify --blobs` prints
   `FINDING 5: blob <address> is erased and still present` and returns 1;
   `previously redact blob <address> --reason …` then prints
   `already redacted by event 6`, writes no redaction, and deletes the object;
   `verify --blobs` is clean afterwards. Add the case and its cure to
   `restore-from-a-backup.md`, and narrow the sentence "no check reports it"
   there and its counterpart in `erasure.md` to what is true. If you show
   output on the page, run it yourself and type what you get; the lines above
   are facts for your prose, not a block to paste.
3. **`keep-the-blob-key-safe.md`, a key missing from the backup**: as the
   review says — copy it from the identity directory into the backup now; only
   if the directory lacks it too is every object sealed to it lost.
4. **Hash format 1**: the README and `erase-something.md` say that an event
   written before stage 1c has no salt, so short erased content stays
   guessable from its digests, with a link to `erasure`.
5. **A bucket with versioning or object lock**: `erasure.md` (what an erasure
   doesn't do), `erase-something.md` and `verify-the-chain.md` say that such a
   bucket keeps erased blobs and that `verify --blobs` cannot see it. Nothing
   in the code checks the bucket; say only that.
6. **The chain findings of `verify`** go into `cli.md` with their conditions,
   every one `core/verify.py` can produce, in the form the page already uses
   for the others. `tests/test_docs_references.py` holds quoted messages
   against the code; let it hold these too.
7. **`configuration.md`**, the two sentences that contradict the table: as the
   review says, and consistent with what part 1 added about the identity
   directory.
8. **`erase-something.md`, *Erase units*** (ruling E-7): the sentence that the
   payload stays, and that an event written by `append --text` keeps its whole
   text there, is the **first** thing under the heading, before the command.
   The example stays — its output is measured and the command line cannot
   write an event without the payload copy — but the page says before the
   command what the example shows and what it does not achieve. The command
   now prints a notice on standard error as well: **retype** that block from a
   real run, and every other block on any page that shows `redact units`.
9. `keep-the-blob-key-safe.md`: the rehearsal's step 5 also unsets the three
   `AWS_*` variables.
10. Same page: the `head-object` example names a recipient the reader creates
    only later. The output is measured and stays; one sentence says which key
    it is.
11. **The identity directory.** Part 1 changed the code: a
    `PREVIOUSLY_BLOB_IDENTITIES` that points at no directory is now an error
    with exit code 2 (`PREVIOUSLY_BLOB_IDENTITIES is not a directory: <path>`),
    while an existing directory that lacks an identity still gives
    `cannot be opened` and exit code 1 for each blob sealed to that key. Say in
    `verify-the-chain.md` and `restore-from-a-backup.md` what each of the two
    means on a restored or new machine.
12. **The record of an erasure** (`erase-something.md`,
    `restore-from-a-backup.md`) also carries the source key
    `(source, external_id)` of the target (ruling E-7). Reason: after a
    restore, an event that was lost and is delivered again comes back under a
    new `id` and a new hash, the hash check rightly refuses it, and only the
    source key says that it is the same submission. Check which command shows
    an event's source key and which, if any, finds an event by it, and write
    only what is true. If no command finds an event by its source key, say so
    in one sentence and put it into the map.
13. README: beside the blobs, the limit with the highest cost — losing the
    identity loses every blob for good — with a link to the key guide.
14. `docs/index.md`: the cards name the new guides and explanations.
15. `module-boundaries.md`: a third protocol, `RedactionStore`, and why
    erasure got its own. Recount whatever the page counts; part 1 added a
    method to `ProjectionStore`.
16. `blobs.md`: the provider sees each object's name, which is the SHA-256 of
    the plaintext without a salt, so whoever holds a candidate file can
    confirm that it is in the bucket.
17. `erasure.md`, *What "covered" means*: the lock set as the section above it
    has it.
18. `cli.md`, `--blobs`: the verb the later paragraph uses; an erased blob is
    asked for, not read.
19. `database-schema.md`: the refusal of `0003_hash_version_2`'s downgrade —
    with the condition as part 1 left it (any hash format other than 1).
20. `blobs.md`: the heading with `verify` in code formatting.
21. `hash-chain.md`: the sentence on domains, as `hash-format.md` has it.

## From the hands-on session

22. `previously blob get --output FILE` **replaces** an existing file. Measured
    on 2026-10-05: `wrote 42 bytes to agenda.txt` over a file that was there.
    `cli.md` only says that an existing file is unchanged on every error. Say
    it outright in `cli.md` and in `attach-and-fetch-a-file.md`.

## What part 1 left for you

23. `docs/explanation/projections.md` quotes counts of the tests in
    `tests/test_projection_worker.py` that are stale. A count on a page is a
    claim: recount from the tree, or word the sentence so that it carries no
    count nobody maintains.
24. The catch-up lock is explained nowhere. `projections.md` and
    `concurrency.md` say: two catch-ups of one projection take turns at its
    state row; each batch reads its position and its version from the locked
    row; why — the measured interleaving in which erased text stayed in the
    chronicle (it is in `WS/final-review-code.md`, Critical 1); what
    `ProjectionRebuilt` means and what to do then. Likewise wherever a page
    names the erasure's lock as `FOR UPDATE`: it is `FOR NO KEY UPDATE` now,
    and the page says why (it no longer waits behind the foreign-key checks of
    the projections).
25. Every wording part 1 added or changed is on the reference page that owns
    it, exactly as the code prints it — part 1 changed the pages its changes
    made false, but check each wording of its report against `cli.md` and
    `configuration.md` yourself, and `grep` the other pages for the old form
    of each (the sentence of an unfinished `redact`; what `verify --blobs`
    prints beside an error; `redact units`).

## From the re-review of part 1

The re-review is `WS/final-fix-code-re-review.md`; its items B and C are yours.

26. `docs/explanation/concurrency.md`, line 8, still promises to say "what the
    one row lock in the system is for". There are two kinds of row lock now:
    the erasure's on `event`, and the catch-up's on `projection_state`. Finding
    24 gives the page its explanation; make the introduction true as well, and
    `grep` the pages for other places that count the locks.
27. `docs/reference/cli.md` names the case `ProjectionRebuilt` for `project`
    and says nothing an operator can act on. What is true (check it in
    `core/projection/worker.py`): the error means that a catch-up of **another
    version of the code** is running against the same database, or that the
    state row was removed by hand while this catch-up ran; a catch-up rebuilds
    whenever the version it finds differs from its own, in either direction, so
    running the same release again rebuilds the table back. Inside `redact`
    the error arrives wrapped in the sentence of an unfinished redaction, which
    ends "run the same command again" — true once only one release runs. The
    reference states those facts; `docs/how-to/rebuild-a-projection.md` gets
    the step: find and stop the process of the other release, then run
    `project` (or the `redact`) again with the release that is meant to run.

The mini-round that followed the re-review changed two more things in the
code; its section is at the end of `WS/final-fix-code-report.md`: the help of
`redact units`, and the payload notice also on an unfinished `redact units`.
Check `cli.md` against both.

## The map (`docs/superpowers/landkarte.md`, German)

New open points, each under the unit it belongs to (ruling E-6, E-7):

- `redact_event` nimmt die Blobs eines Events nur aus dem Register; an einem
  beschädigten Register, das `verify` meldet, nennt und löscht die Tilgung den
  Blob nicht. Vereinigen mit der Nutzlast oder abweisen — nicht entschieden.
- Nichts prüft, dass der Bucket ohne Versionierung und Objektsperre ist;
  `verify --blobs` könnte es melden. (If an entry on this exists, extend it
  rather than adding a second.)
- `N blobs match` zählt getilgte, zu Recht fehlende Blobs mit.
- The existing point "das Ziel ist eine `id`, und eine `id` übersteht eine
  Wiederherstellung nicht" gains what the code review proposes: an option
  `--hash` on `redact event` and `redact units`, checked against the locked
  row before anything is written — recommended before the pilot.
- Nach einer Wiederherstellung kann ein getilgtes Event neu eingeliefert
  werden und trägt dann eine neue `id` und einen neuen Hash; die Aufzeichnung
  führt deshalb den Quellschlüssel. For the pilot, whose ingest reads a
  mailbox again.
- The existing point on `redact units` and `append --text` says what stands
  now: the command prints a notice on standard error (ruling E-3), and whether
  `append --text` keeps putting the text into the payload is the maintainer's
  decision, still open.
- Keine Seite sagt einem Betreiber, der von Stufe 1b kommt, dass er
  `alembic upgrade head` ausführen muss, und was mit seinen Events im
  Format 1 ist (the documentation review set this aside as a gap of the
  project).
- Whatever your own work on findings 12 and 24 turns up.

Check the open points the map already lists against what part 1 changed: a
point the code wave closed gets struck with its commit (`git log --oneline
1ec0b2e..HEAD` lists them), and a point whose description is no longer true of
the code gets reworded — for example the point that `_catch_up_after` stops at
the first projection that fails: it still does, but a failed deletion no longer
keeps the catch-up from running. Count before and after with the command from
`CLAUDE.md`, and report both numbers and what was added, struck and reworded.

## The tutorial, last

`tests/test_docs_typed_output.py` is red at the head you start from: the
tutorial says `606 passed`, and the tree has more tests now. When everything
else is committed and the tree has stopped moving, run the suite once and
**retype the whole pytest block** from that run — the collected count, the
per-file lines, the last line. Do not edit a number inside the old block.

## Rules

- The pages follow the `plone-doc-style:author` skill: one Diátaxis quadrant
  per page, one sentence per line, sentence-case headings, American English,
  shell blocks without prompts, no ellipsis inside a block presented as real
  output, at most one or two admonitions per page. A how-to gives steps; the
  reasoning goes to the explanation, linked.
- Typed output is a measurement: every block you add or change comes from a
  run of yours on the head you are working on, and your report says which
  blocks you retyped and from which run. Blocks you do not touch stay as they
  are.
- No secret on any page, in the report or in a commit message. Keys and
  secrets for your runs are generated at run time and deleted afterwards;
  pages show an identity only as `AGE-SECRET-KEY-1…`.
- No software is installed on the host. `age` and the AWS command line run in
  containers, as in your first run. Remove every container, network and
  volume you start (`docker rm -f -v`), and say so.
- You change no file under `src/`, `tests/` or `migrations/`. If a page cannot
  be made true without a code change, stop and report it.
- You do not touch the frozen specifications, the plan, or `CLAUDE.md`.
- You never dispatch a subagent.

## Commits

A few commits by subject (the reference; the guides; the explanations; README
and index; the map; the tutorial last), on top of the head named in the
message that brought you this brief. Stage files by name, never `git add -A`.
Messages go to files in `WS/` (`final-fix-docs-commit-msg-<n>.txt`),
`git commit -F`. Trailer on every commit:

```
Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Never `Co-Authored-By`, never "Generated with".

## Gates

All six, each as its own command, after the last commit, and all six green —
the typed-output test included:

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run pytest --cov --cov-report=term-missing
make -C docs html && make -C docs vale && make -C docs linkcheck
```

## Report

Return the report as your final message; do not try to write a report file.
Per finding 1 to 27: what you changed, with file and line, and for every
sentence about behavior the code line it rests on. Then: the blocks you
retyped and the runs they come from; the map (count before and after, added,
struck, reworded); the commits; the last line of each gate; anything you could
not settle or disagree with; the containers you started and that they are
gone.
