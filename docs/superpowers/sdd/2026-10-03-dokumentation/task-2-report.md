# Task 2 report — Reference quadrant (command line, configuration, schema, hash format)

Status: **DONE**
Commits: `8abda3b` — `docs: reference for the command line, configuration, schema and hash format`;
fix round 1 (see below) adds a second commit.
Branch: `worktree-dokumentation`, worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`

## Fix round 1 — a committed Vale vocabulary, and the mermaid `:alt:` that lied

Two of the six deviations below (5 and 6) came back from review with
decisions instead of an accept-as-is, both confirmed by the reviewer's own
remeasurement first:

**1. The Vale vocabulary gap has a real fix.** The reviewer confirmed the
finding (`vale sync` only ever populates `.vale-styles/Microsoft/`, so
`.vale-styles/` on `.gitignore` was too wide) and specified the fix in four
parts, all applied:

- `.gitignore`: `.vale-styles/` narrowed to `.vale-styles/Microsoft/` — only
  the synced package is ignored now.
- `.vale-styles/config/vocabularies/Previously/accept.txt` created and
  committed. Checked against the real path Vale expects (an empty vocab
  directory first raised `'Previously' vocabulary not found; searched: …
  .vale-styles/config/vocabularies/Previously`, which is what fixed the path),
  not assumed.
- `.vale.ini`: added `Vocab = Previously`.
- `docs/Makefile`: the sync guard now tests `.vale-styles/Microsoft`, not
  `.vale-styles` (which the vocabulary file now keeps present on every
  checkout, making the old guard a no-op). Comment next to it corrected — it
  had named `.gitignore`'s exclusion wrong.

**What went into `accept.txt`, and how it was decided, not guessed:**
measured every candidate in isolation before adding anything.
`SQLAlchemy`, `canonicalized`, `subcommand`, `subcommands`, `nullable`, and
`Nullable` all failed `Vale.Spelling` — those six are in the file.
`PostgreSQL` was also checked and already passes (Vale's own dictionary has
it) — not added, because "nur prüfen, nicht raten" cuts both ways: adding a
word that already passes would be noise, not a fix.
`psycopg`, `testcontainers`, and `idempotency` were checked too, on the
reviewer's suggestion, and do fail in isolation — but none of the four pages
in this task uses any of them outside a code span (`psycopg` appears once,
inside `` `postgresql+psycopg://user:pass@host:5432/database` ``, which Vale
already skips), so adding them now would be guessing at what a *future* task
needs. Left out; whoever writes the page that first uses one of them in
prose adds it then, with the same measure-first discipline.

**Reverted the four reworded spots**, now that the vocabulary accepts the
real words:

| File | Reworded (fix round 0) | Reverted to |
|---|---|---|
| `cli.md` | "four commands" / "Every command reads" | "four subcommands" / "Every subcommand reads" |
| `database-schema.md` | "declares every column, index, and constraint below" | "declares them as SQLAlchemy Core tables, with no ORM" |
| `database-schema.md` | column header `Null?` (×3) | column header `Nullable` (×3) |
| `hash-format.md` | "the SHA-256 digest of the payload's canonical JSON bytes" | "the SHA-256 digest of the event's `payload`, canonicalized directly" |

The "database URL" → "connection string" rewording in `cli.md` and
`configuration.md` stays as it was: that one resolved a separate, legitimate
`Microsoft.GeneralURL` style warning, not a vocabulary gap, and "connection
string" is the term the project's own code already uses
(`storage/postgres.py::from_dsn`'s docstring: "Storage out of a connection
string.").

Vale, before the vocabulary (accept.txt emptied, `Vocab = Previously` still
set, run against all nine files):

```
docs/reference/cli.md
 6:13  error  Did you really mean 'subcommands'?  Vale.Spelling
 7:7   error  Did you really mean 'subcommand'?   Vale.Spelling

docs/reference/hash-format.md
 11:64  error  Did you really mean 'canonicalized'?  Vale.Spelling

docs/reference/database-schema.md
 6:53   error  Did you really mean 'SQLAlchemy'?  Vale.Spelling
 31:19  error  Did you really mean 'Nullable'?    Vale.Spelling
 57:19  error  Did you really mean 'Nullable'?    Vale.Spelling
 76:19  error  Did you really mean 'Nullable'?    Vale.Spelling

✖ 7 errors, 0 warnings and 0 suggestions in 9 files.
```

Vale, after restoring the real `accept.txt`:

```
✔ 0 errors, 0 warnings and 0 suggestions in 9 files.
```

**2. The mermaid `:alt:` is gone, not kept.** The reviewer rejected the
`mmdc`/Node.js fix (correctly — it would break "`uv.lock` is the only place a
tool version is pinned") and rejected keeping `:alt:` too: an option that
looks like it does accessibility but does nothing is worse than no option,
because someone will eventually trust it. `database-schema.md` now carries
one sentence of plain prose in front of the diagram — "Each event relates to
zero or more units, and to at most one source key." — stating in text what
the diagram shows, and the `:alt:` line is deleted from the `{mermaid}`
block. `:caption:` stays (it does render, confirmed again below). Checked the
rebuilt HTML: the new sentence is present as a real `<p>`, and `grep -n
'alt='` on `database-schema.html` now returns nothing at all — before, it
returned only theme chrome (search, nav, color-mode toggle), never anything
belonging to the diagram, which is what made the old `:alt:` worthless in the
first place.

The `{ref}`concurrency`` omission from fix round 0 stands as shipped — the
reviewer confirmed dropping it was correct and will add the step that wires
it back in once task 5 creates the label.

Gates after this fix round, rerun in full:

```
make -C docs html      -> build succeeded (0 warnings)
make -C docs vale       -> 0 errors, 0 warnings, 0 suggestions in 9 files
make -C docs linkcheck  -> build succeeded
uv run pytest -q        -> 187 passed
```

## What each page was checked against

- `docs/reference/cli.md` — read `src/previously/cli.py` in full (the four `_cmd_*`
  functions, the `main()` argparse setup at lines 168–189, and the single
  `except (PreviouslyError, StorageError)` branch that produces exit code 2).
  Cross-checked the idempotency claim and the within-batch duplicate check
  against `src/previously/core/append.py` (`_prepare`'s `seen_keys` check and
  the `existing = storage.lookup(...)` branch in `append`). Cross-checked
  `--evidence`'s allowed values against the `Evidence` `StrEnum` in
  `src/previously/contract/types.py`.
- `docs/reference/configuration.md` — read `migrations/dsn.py`
  (`resolve_dsn`'s precedence: `sqlalchemy.url` wins, `PREVIOUSLY_DSN` is the
  fallback, neither set is a `RuntimeError` naming both) and
  `src/previously/storage/postgres.py::from_dsn` (the DSN form and the
  `InvalidDsn` message that states
  `postgresql+psycopg://user:pass@host:5432/database`). Cross-checked the
  PostgreSQL 15 floor and the `NULLS NOT DISTINCT` requirement against
  `README.md:65` (not just against the brief).
- `docs/reference/database-schema.md` — read `src/previously/storage/schema.py`
  for every column, type, nullability, and the constraint/index names given
  an explicit `name=`. For the names PostgreSQL assigns itself (unnamed
  `PrimaryKeyConstraint`/`primary_key=True`), ran the real migration against a
  PostgreSQL 17 testcontainer (same setup as `tests/conftest.py`) and queried
  `pg_constraint`, `pg_indexes`, and `information_schema.columns` directly,
  rather than assuming PostgreSQL's naming convention from memory. That
  query is what confirmed `event_pkey`, `unit_pkey`, `source_key_pkey`, and
  the two foreign-key names below.
- `docs/reference/hash-format.md` — read `src/previously/core/hashing.py`
  (`event_hash`'s eleven-field header, `units_hash`'s three-field header plus
  each unit's five fields, `payload_hash`) and `src/previously/core/canonical.py`
  (for the one-sentence characterization "canonical JSON bytes", not the full
  JCS rule set — that belongs to the future `explanation/canonicalization.md`
  page per the plan's "Diagramme" section, so it isn't duplicated here). The
  pinned vector came from `tests/test_hashing.py` via
  `runpy.run_path('tests/test_hashing.py')` in a throwaway script, and every
  one of the three hex digests and three JCS strings written into
  `hash-format.md` was diff-checked byte-for-byte against the values that
  import produced (`value in doc` for each, see below) — never retyped from
  reading the test file.

## The four labels, verbatim

```
(cli-reference)=
(configuration-reference)=
(database-schema)=
(hash-format)=
```

All four render with exactly those ids in the built HTML
(`grep -o 'id="..."' docs/_build/html/reference/*.html` confirmed one match
each), and the two in-page cross-references that use them
(`{ref}`hash-format`` from `database-schema.md`, `{ref}`configuration-reference``
from `cli.md`) resolve to real links in the build.

## Gates

```
make -C docs html        -> build succeeded (0 warnings)
make -C docs vale         -> ✔ 0 errors, 0 warnings and 0 suggestions in 9 files.
make -C docs linkcheck    -> build succeeded
uv run pytest -q          -> 187 passed in 15.78s
```

## The hash vector: copied, not recomputed

Confirmed programmatically, not by eye. `runpy.run_path('tests/test_hashing.py')`
executed the real test file (imports included) and the three hex digests
(`VECTOR_PAYLOAD_HEX`, `VECTOR_UNITS_HEX`, `VECTOR_EVENT_HEX`) plus the three
canonical JCS strings (`JCS_PAYLOAD`, `JCS_UNITS`, `JCS_EVENT`) and
`VECTOR_PREV.hex()` were each checked with `value in doc` against the final
`docs/reference/hash-format.md` — all seven came back `True`. No hash in that
page was computed by me; every one is the literal string Python produced from
running the pinned test module.

## Deviations found between the brief and the code (or the current tree)

1. **The brief's own `{important}` example in step 2 breaks `make -C docs html`
   right now.** `{ref}`concurrency`` doesn't resolve: measured —
   `docs/reference/configuration.md:16: WARNING: undefined label: 'concurrency'
   [ref.ref]`, fatal under `-W`. The `(concurrency)=` label is produced by task 5,
   which the plan (line 947) places *after* task 2. This isn't a brief-vs-code
   mismatch so much as a sequencing gap in the plan: task 2 was handed a
   worked example that only becomes valid once a later task has run. Fixed by
   dropping the `see {ref}`concurrency`` clause from the shipped page (the two
   facts — PostgreSQL 15 floor, `NULLS NOT DISTINCT` not optional — are intact).
   Whoever does task 5 or 7 can re-add the cross-reference once the label
   exists; re-adding it now and leaving it broken was not an option under
   "alle Tore müssen grün sein."

2. **"Derselbe (source, external_id) zweimal im selben Aufruf abgewiesen" doesn't
   describe anything reachable through this CLI.** `_cmd_append` always builds
   exactly one `RawEvent` and calls `append(_storage(), [event], ...)` — a
   single-element list, every time. There is no argument or mechanism that lets
   one `previously append` invocation submit two events, so the within-batch
   duplicate rejection in `core.append._prepare()` (real, and exercised by
   `core.append`'s own tests) can never fire through this command. What a user
   of this CLI actually observes across two separate invocations with the same
   `--source`/`--external-id` is idempotency: the second call returns the first
   call's `id` and exits 0. Documented that instead of the brief's claim.

3. **The brief's return-code rule ("0 bei Erfolg, 1 wenn `verify` einen Befund
   meldet, 2 bei einem Eingabe- oder Speicherfehler") undercounts exit code 1.**
   `_cmd_show` also returns 1, for an unrelated reason — no event exists at the
   given `event_id` (`print(f"No event {args.event_id}", file=sys.stderr); return 1`).
   That path never raises and never touches the `verify`-specific meaning of 1.
   Documented per-command in a table (`append`/`log`/`verify`/`show` × 0/1/2)
   instead of one global sentence, so the two different "1"s don't get
   conflated.

4. **The brief's named list of 8 constraints/indexes is short one, by its own
   stated criterion.** "Weil die Namen in Fehlermeldungen auftauchen" applies
   just as much to `unit_pkey` as to `event_pkey`/`source_key_pkey` — all three
   are PostgreSQL's own default name for an unnamed `PrimaryKeyConstraint`, and
   the real-database check (see above) confirmed `unit_pkey` exists exactly
   that way. Added it to `database-schema.md`. Also added, for completeness
   (not by the brief's "appears in error messages" criterion, just because
   Reference is supposed to be complete): the two non-unique indexes
   `event_occurred_idx` and `event_kind_occurred_idx`, and the two foreign-key
   constraints `unit_event_id_fkey` and `source_key_event_id_fkey` — all four
   confirmed in the same real-database check, none of them guessed.

5. **The skill's `:alt:` requirement for the diagram is satisfied in the
   source but does nothing in the rendered page.** This project's
   `sphinxcontrib-mermaid` runs with the library default
   `mermaid_output_format = "raw"` (client-side rendering via a `<pre
   class="mermaid">` block). Read the installed library
   (`.venv/lib/python3.14/site-packages/sphinxcontrib/mermaid/__init__.py:262-280`):
   `_render_mm_html_raw`, the function used in `"raw"` mode, takes an `alt`
   parameter and never reads it. Confirmed by grepping the built
   `database-schema.html`: no `alt=`, no `aria-label`, nothing — only `:caption:`
   makes it into the output (as a real `<figcaption>`). `:alt:` is kept in the
   source anyway — it's free, forward-compatible, and matches the skill's own
   instruction — but it buys no accessibility today. A real fix needs
   `mermaid_output_format = "svg"` or `"png"` in `docs/conf.py`, which needs
   the `mmdc` CLI (a new, Node.js-based dependency with its own
   `DEPENDENCIES.md` entry) — out of scope for a task whose file list is four
   reference pages plus `reference/index.md`, and a decision for whoever owns
   `conf.py`.

6. **Vale's spelling dictionary doesn't know several ordinary technical words
   this quadrant needs.** Measured by isolating each word in a throwaway file
   and running `vale` on it directly: `SQLAlchemy`, `canonicalized`,
   `subcommand`/`subcommands`, and `nullable`/`Nullable` (any casing) all fail
   `Vale.Spelling`, with no project vocabulary configured to accept them. A
   durable fix (a `Vocab = Previously` entry in `.vale.ini` plus
   `.vale-styles/Vocab/Previously/accept.txt`) isn't possible without touching
   `.gitignore`: task 1 put the entire `.vale-styles/` tree on `.gitignore`
   (correctly — it's `vale sync`'s fetch target), but that also swallows the
   one place Vale's own convention wants a project vocabulary to live. Fixing
   that is a `.vale.ini`/`.gitignore` change outside this task's file list, so
   instead every flagged word was reworded away with no loss of accuracy:
   "commands" for "subcommands", "connection string" for "database URL" (which
   also silences a legitimate `Microsoft.GeneralURL` warning on the same
   line), "canonical JSON bytes" for "canonicalized", and a `Null?` column
   header instead of `Nullable`. This will recur on later tasks that need the
   same ordinary words (task 5/6's explanation pages will want "SQLAlchemy"
   for `module-boundaries.md`, for instance) — worth fixing centrally once,
   rather than every task rediscovering and rewording around it.
