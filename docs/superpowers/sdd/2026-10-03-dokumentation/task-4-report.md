# Task 4 report — How-to guides

Status: **DONE**
Branch: `worktree-dokumentation`, worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`
Base: `06dd2f5`
Commits: `738dfec` (task 4), fix round 1 adds `f3e010f`.

## Fix round 1 — a test that outran the docs, and an overpromising title

Both findings accepted. Both are fixes, not disputes.

**1. `add-a-migration.md`'s warning was stale, through no fault of this
task.** Between this task's commit and the coordinator's review, the
coordinator landed `c3d67e8`
(`test_the_declared_nulls_not_distinct_reaches_the_database`) directly in
`tests/`, without checking the page that had just described the gap that
test closes. Read the new test's code and docstring directly, not the
coordinator's message, to state its coverage precisely:

- `test_the_declared_indexes_exist_in_the_migrated_database` (the original,
  name-only check) still does **not** catch a `NULLS NOT DISTINCT` mismatch
  — confirmed by reading it again: it builds `declared` from `index.name`
  only, and a name can't carry a flag.
- `test_the_declared_nulls_not_distinct_reaches_the_database` does catch it,
  for every index `metadata` declares, in both directions — confirmed by
  reading its query against `pg_index.indnullsnotdistinct`, joined and
  compared to `index.dialect_options["postgresql"]["nulls_not_distinct"]` for
  every declared index, not just `event_prev_hash_idx`.

Rewrote the warning to name both tests and say which one does what, and
changed the page's final "confirm" step to run both test IDs instead of
one. The underlying hazard — an `alembic revision --autogenerate` that
drops the flag when the two declarations disagree — is still real; what
changed is that it's now caught by a test instead of passing silently, and
the page now says that distinction instead of the now-false "nothing here
catches the mismatch."

Did not touch `tests/test_schema.py` itself — out of scope for a docs-only
task, and not asked for. One incidental observation, not acted on: the new
test lacks the `@pytest.mark.db` decorator every other test using the `db`
fixture in that file carries (checked with `grep -n
'^@pytest.mark.db\|^def test_the_declared_nulls_not_distinct'
tests/test_schema.py`). It still runs and passes — the marker isn't what
wires up the fixture — so this doesn't block anything; flagging it only
because the project's culture rewards naming small discrepancies rather
than quietly stepping around them.

**2. `restore-from-a-backup.md`'s title promised a procedure the page
doesn't contain.** "How to restore from a backup" reads as the full restore
walkthrough; the page only ever covered the verify-after-restore step,
since no restore path exists in this repository. Kept the filename —
the coordinator's own call, and the right one: the page is the correct
long-term home once a real deployment adds an actual restore procedure, and
renaming it now only to rename it back later is pure churn. Retitled the H1
to name today's real goal: "How to check that a restore brought the chain
back." Used "chain," not "log" (the coordinator's own suggestion used "the
log"), to match the vocabulary this project's own docs already use for what
`verify` checks — `cli-reference` and this page both say "chain," and
introducing a second word for the same thing would be its own small
inconsistency.

Checked for duplication before adding the "arrives with a later stage's
deployment" sentence, as asked: lines 11–12 already said the restoring
tooling isn't part of this repository, so folded the new fact into that
existing sentence ("...and that tooling arrives with a later stage's
deployment, not with this repository") rather than adding a second,
separate sentence saying the same thing twice. Also trimmed the opening
sentence, which had started to echo the "not merely that PostgreSQL
starts" contrast made more precisely a few lines further down — one
statement of that contrast, not two.

## `verify-the-chain.md`

**Quadrant test applied:** "Does this solve a specific real-world problem for
someone who already has the skill?" Yes — "I ran `verify`, now what do I do
with the result" is a concrete operational question, not a learning path.

**Temptation to explain instead of instruct:** the closing two sentences,
on what the check does *not* prove (a deleted tip, or an event appended with
its own self-consistent chain). The brief asks for exactly this content, but
with a `{ref}` to the Explanation. Per the coordinating instructions for this
task, that label (`hash-chain`, produced by task 5) doesn't exist yet, and a
forward `{ref}` would read `WARNING: undefined label` and fail `-W`. Stated
the two limits as plain facts — no reasoning for *why* appending a
self-consistent chain defeats the check, that's the explanation page's job —
and closed with "see the explanation of the hash chain," worded so a later
cross-reference pass can wrap it in a real `{ref}` without touching the
sentence around it.

Second temptation: documenting the individual `<reason>` strings `verify`
can print (checked them all in `src/previously/core/verify.py`, e.g.
`"hash does not match the fields"`, `"units_hash does not match the units"`).
Inlining a decoder table would duplicate Reference content and go stale the
next time a finding's wording changes. Wrote instead that the reason is
self-describing text, not a code to look up, and linked `{ref}`cli-reference``
for the output format itself.

## `restore-from-a-backup.md`

**What I found:** there is no restore path anywhere in `src/`, `tests/`, or
`migrations/` — grepped for `backup|restore|passphrase` across the whole
tree and found nothing but the two matches in `docs/superpowers/...` design
records. The architecture spec (§10.4–§10.5) is explicit that
backup/restore is a deployment-layer concern: pgBackRest via a CNPG-I plugin
(Dalibo's or Opera's — "a build-time decision," not yet made), client-side
AES-256-CBC encryption, the key delivered through the External Secrets
Operator from a vault outside both the database's namespace and the backup
target. None of that exists in this repository today, and the specific
restore commands (`kubectl`, the plugin's CLI, whatever it turns out to be)
aren't decided, so I didn't invent any.

The brief's instruction to "verweise auf die Reference für die Konfiguration"
for the passphrase doesn't have a literal target either:
`docs/reference/configuration.md` documents exactly one thing,
`PREVIOUSLY_DSN`, and says nothing about the passphrase — which lives in a
Kubernetes Secret, not in Previously's own configuration surface, per the
same architecture section. I did not invent a reference entry for it or
link `{ref}`configuration-reference`` as though it covered the passphrase.
Instead I used that link where it's actually true: pointing `PREVIOUSLY_DSN`
at the restored instance before running `verify` is a real configuration
step this repo does own, and `configuration-reference` documents it
correctly.

**How I handled the gap, instead of inventing something:** scoped the page
down to the one piece of the restore procedure that is Previously's own
responsibility and genuinely exists today — pointing the tools at the
restored database and running `previously verify` against it, then treating
exit `1` as a failed restore regardless of whether PostgreSQL itself came up
clean. The admonition text from the brief ("A restore that was never
rehearsed isn't a backup" — contracted for `Microsoft.Contractions`, see
Vale below) and the passphrase fact (without it, no restore at all; losing
it means losing the backups permanently, per §10.5 of the architecture spec)
are both stated as given, without the mechanics behind them. I judged this
writable rather than BLOCKED, because the page still solves a real problem
for a real reader — "I just restored something, how do I know it's
trustworthy" — using tools that exist; it does not claim to show *how* to
run the restore itself, and says so in its second paragraph.

**Quadrant test applied:** same as above — "how do I know a restore I just
performed is trustworthy" is a real-world problem with an existing,
actionable answer, even though "how do I perform the restore" (a different,
not-yet-answerable question) is explicitly out of scope.

**Temptation to explain:** the architecture spec's case for client-side
encryption over Hetzner's SSE-C (Ceph's `CopyObject` limits, barman-cloud's
missing GPG support, the three-way A/B/C trade-off) is genuinely interesting
and was tempting to summarize for context. Left all of it out — stated only
the operative facts a reader needs to act on (no passphrase, no restore;
run `verify` after) and closed with the same forward-compatible,
not-yet-`{ref}`'d gesture to "the explanation of backup encryption" as
task 5/6 will need for `hash-chain`.

## `add-a-migration.md`

**What I checked in the code:** `postgresql_nulls_not_distinct=True` is
declared in both places today, confirmed by reading both files directly:

- `src/previously/storage/schema.py`, on the `Index("event_prev_hash_idx",
  event.c.prev_hash, unique=True, postgresql_nulls_not_distinct=True)`
  object.
- `migrations/versions/0001_log.py`, on the matching
  `op.create_index("event_prev_hash_idx", "event", ["prev_hash"],
  unique=True, postgresql_nulls_not_distinct=True)` call.

I also read `tests/test_schema.py::test_the_declared_indexes_exist_in_the_migrated_database`
precisely to state its coverage accurately rather than assume: it compares
`{index.name for table in metadata.tables.values() for index in
table.indexes}` against `SELECT indexname FROM pg_indexes`, by **name only**.
It would catch an index declared in `schema.py` but never created by a
migration; it would *not* catch one that exists under the right name in both
places but disagrees on `NULLS NOT DISTINCT`. That asymmetry is exactly what
the warning in the page states, and I wrote it as a fact about what the test
does and doesn't do rather than a decoder of Alembic's autogenerate
internals.

**Quadrant test applied:** "I need to add a schema change, how do I do it in
this project's migration tooling" — a real task for someone who already
knows Alembic and SQLAlchemy Core.

**Temptation to explain:** the `NULLS NOT DISTINCT` warning itself. The
brief frames this as a severe, previously-real finding, which invites
explaining *why* a single-genesis guarantee matters for the hash chain. Left
that out — the warning states the mechanical hazard (mismatch between the
two declarations, autogenerate's silent drop) and nothing about why the
constraint exists in the first place; that belongs to the concurrency
explanation task 6 produces, not here.

## Vale vocabulary

**No words added.** First `make -C docs vale` run reported 4 errors / 1
warning, all style mechanics, not vocabulary:

- `Microsoft.Contractions` on "is not" in the brief's literal admonition
  text → changed to "isn't".
- `Microsoft.Dashes` (spaced em dash in running prose) twice → both changed
  to the unspaced form, matching the existing convention already in
  `docs/tutorials/record-your-first-event.md` ("schema—the log").
- `Vale.Spelling` on "Postgres" (the short form) → changed to "PostgreSQL",
  matching every other use of the word across the English docs; no reason
  to introduce a second spelling of the same product, so no vocabulary
  entry either.
- `Microsoft.Adverbs` on "silently" in the migration warning → reworded to
  "without telling you", which keeps the exact meaning (the drop produces no
  warning) without the flagged adverb.

Checked each individually against the rule it triggered before fixing it;
none warranted a vocabulary entry, so `.vale-styles/config/vocabularies/Previously/accept.txt`
is unchanged.

## Gates

First pass (before fix round 1):

```
make -C docs html       -> build succeeded (0 warnings)
make -C docs vale       -> 0 errors, 0 warnings, 0 suggestions in 13 files
make -C docs linkcheck  -> build succeeded, no broken links
uv run pytest -q        -> 188 passed in 16.36s
```

188 at that point — no code touched by task 4 itself.

Rerun after fix round 1 (which touches no code, but runs after the
coordinator's own `c3d67e8` landed a new test):

```
make -C docs html       -> build succeeded (0 warnings)
make -C docs vale       -> 1 error (Microsoft.Dashes on a new spaced em
                            dash in add-a-migration.md), fixed, then
                            0 errors, 0 warnings, 0 suggestions in 13 files
make -C docs linkcheck  -> build succeeded, no broken links
uv run pytest -q        -> 189 passed in 16.35s
```

189 — the one new test from `c3d67e8`, not from this round's own changes.

## Files

- Created: `docs/how-to/verify-the-chain.md` (label `(verify-the-chain)=`),
  `docs/how-to/restore-from-a-backup.md` (label `(restore-from-a-backup)=`),
  `docs/how-to/add-a-migration.md` (label `(add-a-migration)=`).
- Modified: `docs/how-to/index.md` (toctree entries for the three pages).
- Fix round 1 additionally modified: `docs/how-to/add-a-migration.md`
  (warning and confirm step rewritten for the new test),
  `docs/how-to/restore-from-a-backup.md` (H1 and opening sentence
  retitled; one sentence folded to avoid duplication).

None of the three pages are required to produce a label for task 7 — the
plan's own "Produces" field lists labels only for tasks 2, 5, and 6. I added
one to each page anyway, matching the convention every other content page in
the tree already follows.

## Deviations from the brief

1. **The passphrase cross-reference.** The brief says "Verweise auf die
   Reference für die Konfiguration" for the passphrase step. No reference
   page documents the passphrase — `configuration-reference` covers only
   `PREVIOUSLY_DSN`, and the passphrase is Kubernetes-Secret/External-Secrets-Operator
   territory per the architecture spec, outside Previously's own
   configuration surface entirely. I didn't invent an entry or mislink;
   I used `{ref}`configuration-reference`` for the one configuration fact
   this guide genuinely needs (pointing `PREVIOUSLY_DSN` at the restored
   instance) and stated the passphrase fact without a reference link.
2. **No commands for the restore itself.** The brief's content list for
   `restore-from-a-backup.md` opens with "wiederherstellen" but gives no
   commands, unlike the migration page, which gives exact ones. That absence
   matches reality — there's nothing to command — and I read it as
   intentional rather than an oversight, but flagging it per the task's own
   "if you find the page isn't sensibly writable without existing tools,
   report that" instruction: I judged it *was* sensibly writable, scoped to
   the verify-after-restore step, rather than unwritable outright.

No other deviations found; the `add-a-migration.md` content matched the
code exactly on direct inspection.

## Concerns

None blocking. The one thing worth a human's attention before task 7 runs:
both forward-compatible closing sentences ("see the explanation of the hash
chain" / "...of backup encryption") are plain prose by design, so task 7's
cross-reference pass needs to actually find and convert them — they won't
show up as `grep`-able `{ref}` placeholders or TODOs. I didn't mark them any
more visibly than that because the task brief for this page explicitly
forbids adding the `{ref}` now, and a visible TODO marker risked reading as
Vale-checkable prose with a stray marker in it.

## Commits

`738dfec` — `docs: how-to guides for verification, restore and migrations`
`f3e010f` — `docs: fix round 1 — the new schema test, and an honest how-to title`
