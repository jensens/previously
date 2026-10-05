# Final fix wave, part 1: code

You are fixing what the final review of the whole branch found in the **code**.
A second part follows after you and fixes the documentation pages; you change a
page only where your own change makes it false (see *Pages* below).

## Where this fits

"Previously" is an append-only event log with a hash chain (Python 3.14,
SQLAlchemy Core, PostgreSQL). Stage 1c added hash format 2, erasure as an event
(`previously redact event|units|blob`), and blobs sealed with `age` in an S3
bucket. Eight tasks are done and reviewed; the branch head is `1ec0b2e`.

The repository is the git worktree
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs`. Run every
command from there; never `cd` out of it, and never touch another worktree.
`WS/` below means
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs/.superpowers/sdd/2026-10-04-stufe-1c-blobs-und-tilgung/`.

## Read first

1. `WS/final-review-code.md` — the review. Its findings are numbered Critical 1,
   Important 1–3, Minor 1–9. This brief says which you fix and how the
   controller decided each; where the review and this brief differ, the brief
   holds.
2. `WS/global-constraints.md` — the rules every task of this plan got,
   including the table of contractual wordings of the command line.
3. `CLAUDE.md` at the root of the worktree — the sections *Gates*, *An
   assurance needs a test measured to fail*, *A comment is a claim*, *Lint
   suppressions*, *Citing a reason from code*, *A ruling citation is
   provenance, never the reason*.

## What you fix

### 1. Critical 1 — two catch-ups of one projection are not serialized

`src/previously/core/projection/worker.py`, reached from
`src/previously/cli.py` (`project`, and since this stage every `redact`).
`catch_up` keeps `up_to_id` in memory and locks nothing. The reviewer measured
this interleaving against real PostgreSQL: `project` reads event 1; `redact
event 1` commits; another event is appended; both catch-ups commit. The
chronicle keeps the erased text at `up_to_id 3`, `redact` exits 0, `project`
ends in an `IntegrityError` traceback, and a further catch-up says "up to
date". Only a rebuild clears it.

The reviewer's scratch test is at
`/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/race/test_race.py`.

Order of work:

1. **Measure first.** Reproduce the failure in the tree's test setup, before
   you change anything. If you cannot reproduce it, stop and report.
2. **Fix at the cause.** Two catch-ups of the same projection run one after the
   other, per batch: each batch transaction locks the projection's state row
   and takes `up_to_id` and the version **from the locked row**, never from
   memory. This holds for the first build (when no state row exists yet — two
   first builds at once must not both build) and for a rebuild after a version
   change. The lock belongs behind the `ProjectionStore` protocol in
   `contract/store.py`; `core` does not learn SQL.
3. **A regression test in the tree**, deterministic (it pauses one worker
   between real calls; no sleep that hopes for a timing, no mock), measured
   **red without the lock** and green with it, and beside it the control the
   reviewer describes (without the extra append the run ends clean either
   way). Report the mutation and both outcomes.
4. The same test, or one beside it, pins that neither command ends in a
   traceback: after the fix `redact`'s own catch-up cannot meet rows a
   concurrent `project` holds uncommitted.
5. Check that the new lock cannot deadlock with the event locks of `redact`
   (`core/redact.py`): say in your report which transaction holds which locks
   and why no cycle exists. If you find one, report it rather than paper over
   it.

### 2. Important 1 — `redact units` reports success while the text stays in the payload

`previously append --text` writes the whole text into the payload as well as
into the units (`src/previously/cli.py:410`). `redact units` erases the units
and prints `redacted by event <id>`; the text stays readable in the payload.

Decision (ruling E-3): whenever the payload of the target still stands after a
`redact units`, the command prints one notice on **standard error**:

```
the payload of event <id> is not erased and may hold the same text; `previously redact event <id>` erases it
```

Standard output stays the one line; the exit code stays 0. The notice also
comes on a rerun that finds the units already covered (`already redacted by
event <id>`), because the payload stands then as well. `core` reports the fact
(the target is locked and read anyway); the sentence is the command line's.
`redact units --help` says that the payload stays. Do **not** change what
`append --text` writes: that is the maintainer's decision and is still open.

If the form of the notices this command already prints (the `stays in the
store` notices) uses different punctuation or quoting, follow that form and
say so in your report.

### 3. Important 2 — the lock mode, and what a lock failure is called

The reviewer reasoned, and did not measure, that `lock_event`'s `FOR UPDATE`
(`src/previously/storage/postgres.py`) conflicts with the `FOR KEY SHARE` of
the foreign-key checks that projection writes take on `event`, that a deadlock
with the source-stats upsert is possible, and that any aborted transaction is
reported as "database server … does not answer".

1. **Measure**: does `lock_event` wait behind an open transaction that has
   inserted a row referencing the same event (and the reverse)? Report what
   you measured.
2. If it waits: lock with `FOR NO KEY UPDATE`
   (`with_for_update(key_share=True)`). Two erasures of the same target must
   still wait for each other — the existing tests that pin that stay green,
   unchanged. A test pins the new behavior, measured red with the old mode.
3. A transaction the database aborts — SQLSTATE class 40 (deadlock,
   serialization failure) and `55P03` (lock not available) — becomes a storage
   error of its own, with one sentence that says the database aborted the
   operation and to run the command again. It must not be reported as "does
   not answer". Follow the existing classes in `storage/errors.py` and the way
   `cli.py` turns them into one sentence and exit code 2. A test produces a
   real deadlock (two transactions, two rows, opposite order) and pins the
   error; no mock.

### 4. Important 3 — two comments describe the lock as it was before task 7

`src/previously/storage/schema.py` (around lines 107–109) and
`src/previously/storage/postgres.py` (around lines 489–490) say the lock is on
the erased event only. Since task 7 `redact event` also locks every event that
shares a blob with its target, and `redact blob` locks every user of its blob.
Make both true of the code as it stands **after** your changes (the lock mode
included), checked against the code and not against the old comment.

### 5. The small findings that ride along (ruling E-5)

- **Minor 2** — `migrations/versions/0003_hash_version_2.py`: `downgrade()`
  refuses on `hash_version <> 1`, not on `= 2`. A test with a row of another
  version (raw SQL) pins it, red with the old test.
- **Minor 3** — `append --attach` must not upload before the database is known
  to be configured: an unset `PREVIOUSLY_DSN` leaves no object in the bucket
  (test: the bucket is empty afterwards). And an address that is no address
  (`redact blob`, `blob get`) is reported before anything else is asked, also
  before a missing DSN.
- **Minor 4** — after the redaction is committed, `_cmd_redact` attempts
  **both** outstanding steps, the deletion from the store and the catch-up of
  the projections, whatever happens to the first, and names everything that is
  outstanding in the one sentence, which still ends with the advice to run the
  same command again, exit code 2. Reason: with either fixed order, a lasting
  failure of the first step keeps the second from ever running. Keep the form
  of the existing sentence (`the redaction is recorded as event <id>, but it
  is not finished: …; run the same command again`) and fit two reasons into
  it. Tests: store down → the chronicle no longer shows the erased text, the
  sentence names the blob; both failing → both named.
- **Minor 5** — `RedactionIndex.of_unit` (`core/redaction.py`) names the
  earlier redaction, as its class docstring says and as `of_reference` does.
- **Minor 6** — `verify --blobs`: when the blob phase ends in an error (store
  unreachable or refusing, identity unreadable, invalid key), the findings the
  chain pass already collected are still printed as `FINDING` lines on
  standard output; the error sentence goes to standard error; the exit code is
  2. A store hiccup must not hide a forgery finding. With no chain finding the
  output is as today.
- **Minor 7** — the census command in the comment at the top of
  `src/previously/contract/store.py` prints 21 lines while the comment claims
  13 methods. Make the command print the claim, and recount after your own
  changes to the protocols.
- **From the documentation review (its Minor 11), because it is code** — a
  `PREVIOUSLY_BLOB_IDENTITIES` that points at no directory is a configuration
  error: one sentence, exit code 2, for `blob get` and `verify --blobs`. Today
  `DirectoryKeys` (`storage/keys.py`) answers "no identity" for every key, and
  `verify --blobs` reports every blob as `cannot be opened` with exit code 1,
  which reads as a lost key on a freshly restored machine. An existing
  directory that lacks one identity stays what it is today: a finding for that
  blob.

### What you do not fix (ruling E-6)

Minor 1 (the blob list from the register only), Minor 8 (nothing checks the
bucket's versioning), Minor 9 (what `N blobs match` counts) and the proposed
`--hash` option go into the map as open points; the second part writes them
there. Leave the code as it is.

## Pages

`docs/reference/cli.md` and `docs/reference/configuration.md` are reference
pages held against the code by `tests/test_docs_references.py`. Where your
change alters a message, an output or an exit code they state — the new notice
of `redact units`, the sentence of an unfinished redaction, `verify --blobs`
printing findings beside an error, the identity directory, the new storage
error, the lock mode in `docs/reference/database-schema.md` or
`docs/explanation/concurrency.md` if they name it — change the page in the same
commit, so that no page is false at any commit. One sentence per line, American
English, facts only on a reference page. Leave every other documentation
finding to the second part.

A page must not say something the code does not do: after your changes, `grep`
the pages for each wording you changed.

## Rules

- TDD: the failing test first, where a test can fail first.
- Every assurance you add gets a test **measured to fail** when the assurance
  is taken back, and a control measured to stay green. Mutations happen in the
  tree: change the line, run the covering tests, restore the line at once. If
  the permission system refuses a mutation, do not look for another route;
  report it, and the controller measures.
- No `# type: ignore`, no new lint suppression, no mock standing in for time,
  the database, the store or randomness, no test reaching into a private name.
  pyright strict.
- Import-linter contracts are not widened. `core` does not import SQLAlchemy,
  `boto3` or `storage`.
- English in code, comments, messages and test names. A comment gives its
  reason itself; where you cite a decision of this execution, write it as
  `ruling E-3 of the 2026-10-04 stage 1c plan` (one `ruling` per label), and
  the comment must still hold with the label removed. No citation and no page
  label in program output.
- No secret in any output, message, `repr`, exception context, report or
  commit: neither the store's secret key nor an age identity.
- Tests run against real PostgreSQL and the real RustFS container through the
  existing fixtures in `tests/conftest.py`.
- Do not touch: the frozen specification under `docs/superpowers/specs/`, the
  plan, `CLAUDE.md`, `docs/superpowers/landkarte.md`, the tutorial's typed
  output (if your change alters the number of tests, say so in the report —
  the second part retypes the block).
- You never dispatch a subagent.

## Commits

Small commits, one per finding or per group that belongs together, on top of
`1ec0b2e`. Stage files by name — never `git add -A`, never `git add .`. Write
each message to a file in `WS/` (`final-fix-code-commit-msg-<n>.txt`) and
commit with `git commit -F`. Subject in the imperative-free style of the
branch (`fix: …`), a body that says why. Trailer on every commit:

```
Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Never `Co-Authored-By`, never "Generated with".

## Gates

All six, each as its own command, after the last commit; report the last line
of each:

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run pytest --cov --cov-report=term-missing
make -C docs html && make -C docs vale && make -C docs linkcheck
```

`tests/test_docs_typed_output.py` holds the tutorial's `N passed` against the
number of tests in the tree, so new tests turn it red. That one failure is
expected in this part and is the second part's to close: report it as such,
with the new count, and make sure it is the **only** failure. Do not edit the
tutorial.

## Report

Write the report to `WS/final-fix-code-report.md`. If the tool refuses to let
you write that file, do not look for another way: return the full report as
your final message and say so in its first line.

Per finding: what you changed (file and line), what you measured before the
change, the test that pins it, the mutation and its red and green outcomes.
Then: every wording of the command line you added or changed, exactly; the
commits; the gate lines; the new test count; anything you could not settle or
disagree with; any container you started and that it is removed.

Otherwise your final message is short: status (DONE, DONE_WITH_CONCERNS,
NEEDS_CONTEXT or BLOCKED), the commits, one line of test summary, the changed
wordings, and your concerns.
