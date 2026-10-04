# Fix wave after the final whole-branch review — report

Branch `worktree-stufe-1b-projektionen`, base of this wave `4c52091`,
tip after it `ff3c261`. Everything below was run from
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen`.
Tests ran against a real PostgreSQL 17 testcontainer.

Commits:

- `d4bcb53` — `rules: ruling labels are per plan, and most of what they name is lost`
  (`CLAUDE.md`, plus the ruling-pointer hunks of `.importlinter`)
- `ff3c261` — `fix: escape every printed field, read the lag in one statement, retire three stale numbers`
  (everything else)

The two commits split `.importlinter` by hunk: the ruling pointers (I-6, one
story with B.2) went into `d4bcb53`, the contract rename (a minor of the
review) into `ff3c261`. Staged with `git apply --cached -p0 --unidiff-zero`
over a hand-split `git diff -U0`, because interactive staging is not
available here.

---

## A. From the final review

### I-1 — `source` and `external_id` reached the stream unescaped

**Changed.** `src/previously/cli.py`: `_cmd_chronicle` now prints
`escape_field(row.source or '')`, `escape_field(row.external_id or '')` and
`escape_field(row.content)`; `_cmd_stats` prints `escape_field(row.source)`.
`escape_field`'s docstring carries the measurement and says the escaping
applies to every string field, not to `content` alone.
`docs/reference/cli.md`: the escaping paragraph in the `chronicle` section
says "in every field and not in `content` alone" and names why `source` and
`external_id` need it; the `stats` section says `source` is escaped the same
way.

**Measurement before (HEAD `4c52091`, 2026-10-04, throwaway test file,
deleted afterwards).** One event appended with `--source 'de<TAB>sk'` and
`--external-id 'id<NL>x'`:

```
chronicle: repr='1\t1\t2026-10-01T09:00:00+00:00\tde\tsk\tid\nx\tplain\n'
chronicle: 2 line(s), fields per line [6, 2]
stats: repr='de\tsk\t1\t1\t2026-10-01T09:00:00+00:00\t2026-10-01T09:00:00+00:00\n'
stats: 1 line(s), fields per line [6]
```

So one unit came out as **two** lines with six and two fields instead of one
line with six, and the `stats` line carried **six** fields instead of five.

**Measurement after.** Folded into the two existing tests rather than adding
one, so the collected count stays 232:

- `test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source`
  appends a fourth event with those two characters, expects
  `4\t1\t2026-10-03T09:00:00+00:00\tde\\tsk\tid\\nx\traw`, and asserts
  `[len(line.split("\t")) for line in out.splitlines()] == [6, 6, 6, 6]`.
- `test_stats_prints_one_line_per_source` appends a fourth source `de<TAB>sk`,
  expects `de\\tsk\t1\t1\t…`, and asserts `[5, 5, 5]`.

**Mutation, red.** `escape_field` dropped from `chronicle`'s `source`:

```
E  At index 3 diff: '4\t1\t2026-10-03T09:00:00+00:00\tde\tsk\tid\\nx\traw'
                 != '4\t1\t2026-10-03T09:00:00+00:00\tde\\tsk\tid\\nx\traw'
FAILED tests/test_cli.py::test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source
1 failed, 1 passed, 33 deselected in 8.90s
```

**Control, green.** The same run left `test_stats_prints_one_line_per_source`
passing (`1 passed`).

**Mutation, red (the other half).** `escape_field` dropped from `stats`:

```
E  At index 1 diff: 'de\tsk\t1\t1\t2026-10-04T09:00:00+00:00\t2026-10-04T09:00:00+00:00'
                 != 'de\\tsk\t1\t1\t2026-10-04T09:00:00+00:00\t2026-10-04T09:00:00+00:00'
FAILED tests/test_cli.py::test_stats_prints_one_line_per_source
1 failed, 1 passed, 33 deselected in 6.45s
```

**Control, green.** The chronicle test passed in that same run — each
assertion reads its own command.

Restored, then `tests/test_cli.py`: `35 passed in 18.99s`.

### I-2 — one transaction is not one moment under READ COMMITTED

**Changed.** `src/previously/contract/rows.py` gains the frozen
`TipAndBookmark(tip_id, up_to_id)`.
`src/previously/storage/postgres.py` gains `tip_and_bookmark(conn, name)`
among the reads for the command line, outside the protocols, beside
`read_chronicle`. One statement, two scalar subqueries, each under a
`coalesce(…, 0)`; compiled against the PostgreSQL dialect it is

```sql
SELECT coalesce((SELECT max(event.id) AS max_1 FROM event), %(coalesce_1)s::INTEGER) AS tip_id,
       coalesce((SELECT projection_state.up_to_id FROM projection_state
                 WHERE projection_state.name = %(name_1)s::VARCHAR), %(coalesce_2)s::INTEGER) AS up_to_id
```

— no outer `FROM`, one snapshot. `_cmd_chronicle` and `_cmd_stats` use it for
the lag line and nothing else; `_lag_line`'s docstring now says "one
statement" and points at the method. The isolation level is untouched, and
`postgres.py`'s pre-existing `verify` paragraph is untouched.

**No new test, on purpose, and the docstring says why:** nothing observable
distinguishes one snapshot from two here — a concurrent append can only make
the lag larger and a concurrent catch-up only smaller, so both readings stay
plausible. What guards the property is the shape of the body, and the
docstring names that as the thing not to split.

The existing lag tests stayed green: `test_both_reading_commands_report_the_lag_on_stderr_and_only_there`
and `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise`
pass in the final `232 passed`.

`docs/explanation/projections.md` now argues it: two numbers read at two
moments give a difference that was never true at either of them; one
transaction does not buy that, because the reading connection runs at READ
COMMITTED and under READ COMMITTED PostgreSQL gives every statement a
snapshot of its own; one statement that asks for both numbers at once sees
one moment. `docs/reference/cli.md` states no mechanism and needed no change
for this item.

### I-3 — "all nine tests in this file"

**Changed.** `tests/test_projection_worker.py` says "all twelve tests in this
file". Measured: `pytest --collect-only -q tests/test_projection_worker.py`
→ `12 tests collected`. The second "nine" in that docstring is about
`test_projection_derive.py` and stays: `9 tests collected` there.

**Re-measured with the mutation the docstring names** —
`first_seen=addition.first_seen` in `src/previously/core/projection/source_stats.py`:

```
tests/test_projection_worker.py   ............   12 passed in 8.93s
tests/test_projection_derive.py   FAILED test_source_stats_aggregates_a_batch_per_source
                                  FAILED test_merge_adds_counts_and_keeps_the_extremes
                                  2 failed, 7 passed in 0.11s
```

So the claim holds with the corrected number, and the control is the derive
file going red where the docstring says it does. Restored.

### I-4 and I-5 — the dated measurement block

**Changed.** `docs/explanation/module-boundaries.md`: `(40 today)` is gone
from the block, the block is otherwise untouched (not retyped), and the prose
below it no longer speaks in the present tense. It now says the numbers are
those of 2026-10-03, that three of the lines have moved, and gives today's
measured values; the surviving point about the fifth line is that the test
which failed there is the one stage 1b deleted, so a run today has nothing to
put in its place.

**Measured on 2026-10-04 (all three named in the page):**

| command | result |
|---|---|
| `uv run ruff format --check .` | `48 files already formatted` |
| `uv run pytest` | `232 passed` |
| `make -C docs vale` | `0 errors, 0 warnings and 0 suggestions in 22 files.` |

The `lint-imports` line of that block (`Contracts: 4 kept, 0 broken.`) has
not moved, which is why the page says three lines and not four.

### I-6 — two unqualified ruling pointers in `.importlinter`, one wrong

**Changed**, in `d4bcb53` together with `CLAUDE.md`. The `core-is-clean`
comment names `ruling T7-a` and `ruling T8-c` singly (so the census sees
them), attributes them to the 2026-10-02 stage 1a plan, says that execution's
ledger was never shipped and is lost, drops the `docs/superpowers/sdd/`
pointer, and records what was measured about it. The `only-storage-knows-sql`
comment no longer carries a bare `ruling T8-c`; it points at the sibling
comment for the reasoning and for what the labels are worth.

**Measured.** In `docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`:
`grep -n "Ruling T7-a"` → line 697, `Ruling T7-a: **Es sind drei Klassen von
Verweis, nicht eine …**` — a different decision; `grep -c "Ruling T8-c"` →
`0`. `ls docs/superpowers/sdd/` → `2026-10-03-dokumentation` only.

### I-7 — the frozen spec names a path that does not exist yet

**Not touched**, as dispatched. The controller ships the execution record.

### Minors

- **`cli.md` notice order.** The page now lists truncation first, lag second,
  and says a single run can print both in that order. The code order is
  unchanged. Newly guarded: see *Order* under ledger item 6 below.
- **`cli.md:17`, exit code 2 for `project`.** "Storage raised an error, or
  the worker found a gap in the log."
- **`database-schema.md`.** `p_chronicle`'s `speaker`/`start_ms`/`end_ms` say
  "always `NULL` until stage 2"; the table did not exist in stage 1a. The
  `unit` table's rows, which legitimately say "in stage 1a", are untouched.
- **Contract name.** `.importlinter`: `No vendor SDK in the package`.
  `uv run lint-imports` prints it:

  ```
  Layers: core above storage, contract below both KEPT
  core knows no foreign system and no model KEPT
  Only storage imports sqlalchemy KEPT
  No vendor SDK in the package KEPT

  Contracts: 4 kept, 0 broken.
  ```

  Grep over `docs/` and `CLAUDE.md` for the old name found six places. One is
  a living page and was updated: `docs/explanation/module-boundaries.md:77`,
  the quoted gate output. `CLAUDE.md` does not mention it. The other five are
  frozen or historical and were deliberately left alone —
  `docs/superpowers/plans/2026-10-04-stufe-1b-projektionen.md:249`, four task
  reports under `docs/superpowers/sdd/2026-10-03-dokumentation/`, and
  `docs/superpowers/specs/2026-10-02-stufe-1a-log.md:953`. (A sixth and
  seventh hit sit under `docs/_build/`, which is build output.)
- **`.importlinter`'s label.** `tests/test_docs_references.py` resolves labels
  in `.importlinter` and `pyproject.toml` as well now, through a new
  `CONFIG_FILES` list and `_referencing_files()`; the AST parts stay on
  `*.py`. The module docstring says which check widened and why.

  Mutation, red — `{ref}`module-boundaries`` broken to
  `{ref}`module-boundries`` in `.importlinter`:

  ```
  E  AssertionError: These labels are referenced from code but defined in no page:
     {'module-boundries': ['.importlinter']}. …
  FAILED tests/test_docs_references.py::test_every_doc_reference_in_the_code_resolves
  1 failed, 4 passed in 0.21s
  ```

  Control, green — same breakage with `CONFIG_FILES = []`: `5 passed in
  0.12s`. So the new file list is exactly what catches it. Both restored.
- **`CHRONICLE.name` / `SOURCE_STATS.name`** replace the two literals in
  `cli.py`, imported from `previously.core.projection`. The `_cmd_stats`
  comment says what a rename would otherwise have done silently.
- **`worker.py`'s gap message** interpolates `expected[0]`. It is provably
  non-empty at the `raise`: when `ids` is empty so is `expected`, and then
  `ids != expected` is false. `test_a_gap_in_the_log_raises_instead_of_being_skipped`
  matches `above id 4` and still passes.
- **`rebuild-a-projection.md`** says once what it said twice; the actionable
  half of the second sentence survives as "Run both commands if you want to
  know about both projections."
- **The seven TRUNCATE copies** are now one `TRUNCATE_ALL` in
  `tests/conftest.py`, derived from `previously.storage.schema.metadata`
  (`reversed(metadata.sorted_tables)` → `unit, source_key, p_source_stats,
  p_chronicle, projection_state, event`). The six places that need it in a
  test body reach it through a `truncate_statement` fixture — no import of the
  conftest module, no `sys.path` trick.

  It hands over a `str` and not a callable, and that is a measured decision:
  hypothesis reads every `@given` function's signature with `eval_str`, so
  `truncate_all: Callable[[], None]` with `Callable` imported under
  `TYPE_CHECKING` failed at collection with `NameError: name 'Callable' is not
  defined` in all six places. A runtime import of `Callable` would have needed
  either a `# noqa` or a new `runtime-evaluated-decorators` entry for
  `hypothesis.given` in `pyproject.toml`; a `str` annotation needs neither, so
  the suppression list stays at five. Measured: five `# noqa` lines in the
  tree (`core/canonical.py`, `tests/test_hashing.py`, `tests/test_append.py`,
  `tests/test_contracts.py`, `docs/conf.py`) — unchanged.
- **Not in this wave**, as dispatched: an upper bound on `--limit`, and the
  `set(sub.choices) == set(commands)` test.

## B. Deferred by the task reviews

1. **`ruling P-1`** in `tests/test_cli.py` reads `ruling P-1 of the
   2026-10-04 stage 1b plan, recorded in
   docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`. The
   reason beside it is untouched.

2. **`CLAUDE.md`, three edits**, commit `d4bcb53`.

   (a) *A ruling citation is provenance, never the reason* now says labels are
   assigned per plan, that a citation names the plan's **date** because the
   record directory is named after it, and that the older citations stay bare
   until somebody touches one.

   (b) The measured state, and the two statements separated. I re-ran both
   measurements rather than copying the dispatch's, and **they disagree with
   it** — see *Disagreements* below.

   The census went in as a command, not a number:

   ```
   grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter | sort -u
   ```

   Measured on 2026-10-04 at the tip: **22 occurrences, 14 distinct labels.**
   Each held against `grep -c "Ruling <label>"` in
   `docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`:

   | label | hits | label | hits |
   |---|---|---|---|
   | `P-1` | 0 | `T8-b` | 0 |
   | `T2-e` | 0 | `T8-c` | 0 |
   | `T5-b` | 1 | `T9-a` | 0 |
   | `T6-b` | 0 | `T9-c` | 0 |
   | `T7-a` | 1 | `T10-a` | 0 |
   | `T8-a` | 0 | `T10-b` | 0 |
   | | | `T10-c` | 0 |
   | | | `T10-d` | 0 |

   Thirteen of the fourteen were already in the tree at the branch base:
   `git grep -hioE 'ruling (P|T[0-9]+)-[a-z0-9]+' cdc508a -- src tests
   pyproject.toml .importlinter` gives the same thirteen plus nothing new.

   Two notes on the pattern, both in `CLAUDE.md` now. `-i` is right here and
   wrong for the `W`/`G`/`B`/`K`/`N` census: there the label stands alone and
   `-i` catches test names, while here the word `ruling` must precede it —
   without `-i` the census misses `Ruling T6-b` at `storage/postgres.py:59`
   and `Ruling T8-b` at `tests/test_verify.py:159`. And the pattern cannot see
   a plural: `rulings T7-a and T8-c` in `.importlinter` was invisible to it,
   which is the second hole behind I-6. Both labels are written singly now, so
   the census sees them.

   (c) The frozen-records paragraph no longer counts. It says the records are
   the output of a repeating step, names the dates (three on 2026-10-03, the
   stage 1b specification on 2026-10-04), and states that the number keeps
   moving. The paragraph after it records what the sentence used to say and
   since which commit it was false (`fee6d2b`). I checked the rest of that
   paragraph for other counts: "Each of the three says so in its own dated
   header" became "each record says so in its own dated header".

   One further count in the same section came out rather than being carried:
   "Measured on 2026-10-03, all sixteen do". I touched that sentence, and a
   figure measured on a day the tree no longer has cannot be rechecked against
   the tree, so it now points at the census instead of naming a number. The
   frozen 2026-10-03 record was not edited.

3. **`catch_up`'s docstring** names the guard: "A `batch_size` below 1 is a
   caller error and is refused with `ValueError` before the first transaction
   opens, so a bad argument changes nothing at all." Behavior unchanged;
   `test_batch_size_below_one_is_a_caller_error_not_a_gap` still passes.

4. **`log --limit`.** `_cmd_log` refuses a limit below 1 with
   `InvalidPayload(f"--limit must be at least 1, got {args.limit}")`, in
   `chronicle`'s words, before `_storage()`.

   **Measurement before (HEAD `4c52091`):**

   ```
   log --limit 0  -> exit 0 out='' err=''
   log --limit -2 -> raised sqlalchemy.exc.DataError:
                     (psycopg.errors.InvalidRowCountInLimitClause) LIMIT must not be negative
   ```

   So `0` was a silent empty answer indistinguishable from an empty log, and
   `-2` was an uncaught foreign exception — a stack trace and the
   interpreter's exit code 1 instead of this command line's 2.

   **After**, folded into `test_append_log_and_verify_together`: both values
   give exit 2, empty stdout, and
   `Error: --limit must be at least 1, got <value>` on stderr.

   **Mutation, red** (guard removed):

   ```
   >   assert main(["log", "--limit", limit]) == 2
   E   AssertionError: assert 0 == 2
   FAILED tests/test_cli.py::test_append_log_and_verify_together
   1 failed, 1 passed, 33 deselected in 6.40s
   ```

   **Control, green.** `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise`
   passed in the same run — the `chronicle` guard is a different bolt.

   `docs/reference/cli.md`: the `log` argument table says "at least 1", the
   section says a limit below 1 is refused before anything is read with exit
   2 and one sentence naming `--limit`, and the exit-code row for `log` reads
   "The input was invalid, or storage raised an error."

5. **`set(sub.choices) == set(commands)`** — not added, as dispatched.

6. **The two `stderr` sentences `cli.md` quotes.** Done, by extending
   `test_the_reference_quotes_what_the_code_actually_prints` rather than
   adding a test. New helpers in `tests/test_docs_references.py`:
   `_quoted_notices` reads the fenced block after "Two notices go to standard
   error"; `_message_patterns` takes the static parts of the strings `cli.py`
   hands to the terminal; `_is_the_same_sentence` requires the first static
   part to open the page's line and the last to close it, with the rest in
   order.

   **Why the candidate set is wider than the dispatch's wording.** A check
   restricted to `print(..., file=sys.stderr)` call sites sees the truncation
   sentence and **not** the lag sentence: `cli.py` prints the latter as
   `print(lag, file=sys.stderr)`, where `lag` came out of `_lag_line`. So
   `_message_patterns` collects from the stderr `print` calls **and** from
   every `return` of a string literal, and the docstring says so. Making
   `_lag_line` public to call it directly was the alternative and is a wider
   change than the item carries.

   **Mutation, red.** `previously project` falsified to `previously catch-up`
   in the page's quoted lag line:

   ```
   E  AssertionError: cli.md quotes 'projection is 12 events behind; run `previously catch-up`'
      on standard error and no message in cli.py says that. …
   ```

   **Control, green.** Only the interpolated values changed on the page —
   `50 lines` → `9 lines` and `12 events` → `7 events`: `5 passed in 0.19s`.
   That is the control that matters: the check reads the wording and not the
   example numbers, so it cannot go red for the wrong reason. Restored:
   `5 passed`.

   **Order.** The review's other half — nothing makes both notices fire
   together — is now closed too, as a fold into
   `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise`: a
   fourth event is appended and deliberately not projected, so the window is
   cut *and* the projection is behind, and `err.splitlines()` is asserted
   equal to the two lines with truncation first.

   Mutation, red (the two `print`s in `_cmd_chronicle` swapped):

   ```
   E  At index 0 diff: 'projection is 1 event behind; run `previously project`'
                    != 'output truncated at 2 lines; raise --limit or narrow --since/--until'
   FAILED tests/test_cli.py::test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise
   1 failed, 1 passed, 33 deselected in 6.44s
   ```

   Control, green: `test_both_reading_commands_report_the_lag_on_stderr_and_only_there`
   passed in that run. Restored: `35 passed`.

7. **Page lengths** — nothing done, as dispatched. The two wording items in
   `module-boundaries.md` are done: "That measurement was the whole argument"
   became "The six-gate block further up, not the `pyright` line right above,
   is the measurement that argued for the test's existence …", and "when a
   second protocol follows" became "before another protocol is added".

## 8. Every number touched, re-measured

| number | command | result |
|---|---|---|
| formatted files (`module-boundaries.md`) | `uv run ruff format --check .` | `48 files already formatted` |
| test count (`module-boundaries.md`, tutorial) | `uv run pytest --cov --cov-report=term-missing` | `232 passed`, `Total coverage: 97.35%` |
| vale files (`module-boundaries.md`) | `make -C docs vale` | `0 errors, 0 warnings and 0 suggestions in 22 files.` |
| tests in `test_projection_worker.py` | `uv run pytest --collect-only -q tests/test_projection_worker.py` | `12 tests collected` |
| tests in `test_projection_derive.py` | `uv run pytest --collect-only -q tests/test_projection_derive.py` | `9 tests collected` |
| ruling citations | `grep -rnioE 'ruling (P\|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter \| sort -u` | 22 occurrences, 14 distinct labels |
| labels resolving in the shipped ledger | `grep -c "Ruling <label>"` per label | 2 of 14 find a line, both a different decision |
| frozen specifications | `ls docs/superpowers/specs/` | 4 |
| `print` calls in `cli.py` (`pyproject.toml`'s "nineteen") | `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` | `Found 19 errors.` — unchanged |
| `main`'s complexity (`cli.py`'s "at 2") | `uv run ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py` | `` C901 `main` is too complex (2 > 1) `` — unchanged |
| lint suppressions | `grep -rn "# noqa" src tests migrations docs/conf.py` | 5 — unchanged |

## 9. The tutorial's test block

**Unchanged, and deliberately so.** The collected count is still 232: every
new assertion was folded into an existing test and no test function was added
or removed. `uv run pytest --collect-only -q` → `232 tests collected`;
`uv run pytest --cov` → `232 passed`. `docs/tutorials/record-your-first-event.md`
was not touched, and `tests/test_docs_typed_output.py` passes.

## 10. All six gates, run separately

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
48 files already formatted

$ uv run pyright
0 errors, 0 warnings, 0 informations

$ uv run lint-imports
Contracts: 4 kept, 0 broken.

$ uv run pytest --cov --cov-report=term-missing
Required test coverage of 90.0% reached. Total coverage: 97.35%
232 passed in 21.44s

$ make -C docs html
build succeeded.

$ make -C docs vale
0 errors, 0 warnings and 0 suggestions in 22 files.

$ make -C docs linkcheck
build succeeded.
```

`docs/_build/linkcheck/output.txt` is 0 bytes. All eight closing lines were
taken from the committed tree at `ff3c261`.

## 11. Commit hygiene

`git status --short` before each `git add`; files staged by name, never
`git add -A`; nothing unexpected showed up at any point and nothing untracked
appeared. The tree is clean at `ff3c261`. Both commits end in
`Assisted-By: Claude Opus 5 <noreply@anthropic.com>`; `git log -2` shows no
`Co-Authored-By` and no "Generated with".

## Files changed

`CLAUDE.md`, `.importlinter`, `docs/explanation/module-boundaries.md`,
`docs/explanation/projections.md`, `docs/how-to/rebuild-a-projection.md`,
`docs/reference/cli.md`, `docs/reference/database-schema.md`,
`src/previously/cli.py`, `src/previously/contract/rows.py`,
`src/previously/core/projection/worker.py`,
`src/previously/storage/postgres.py`, `tests/conftest.py`,
`tests/test_cli.py`, `tests/test_docs_references.py`,
`tests/test_projection_worker.py`, `tests/test_properties.py`.

## Items left open

- **I-7** — the frozen stage 1b specification still names
  `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`, which
  does not exist at `ff3c261`. Left alone as dispatched; the controller ships
  the execution record. The same path is now also named in
  `tests/test_cli.py`'s `ruling P-1` comment, so there are two citations
  waiting on that commit rather than one.
- **`--limit` upper bound** and the **subcommand-table test** — not in this
  wave by the controller's ruling; both belong in the next stage's open
  points.
- **The frozen records' stale contract name.** Five places under
  `docs/superpowers/` still quote `No vendor SDK in stage 1a`. That is what a
  frozen record is for, and the living page was updated, but it is worth
  saying rather than leaving to be noticed.

## Disagreements

- **B.2(b)'s measurement is wrong in the dispatch, and the truth is worse.**
  The dispatch says one label of ten (`T5-b`) is in the 2026-10-03 ledger and
  nine are not. Measured: fourteen distinct labels, not ten, and `T5-b` does
  find a `Ruling T5-b` there — about `Vale.Terms` nailing down every
  vocabulary entry, while `tests/test_schema.py:257` cites `T5-b` for the seam
  where an index created by raw DDL is not declared in `metadata`. Those are
  two unrelated decisions. The same holds for `T7-a`. So the honest statement
  is not "one of ten resolves" but "**none** of the fourteen resolves to the
  decision it names, and two resolve to a different one" — which is the I-6
  failure mode, not the absence of a target. `CLAUDE.md` says it that way.
- **The census pattern needed `-i` and still cannot be complete.** Without
  `-i` it misses `Ruling T6-b` and `Ruling T8-b`, which open sentences; with
  `-i` it is still blind to `rulings T7-a and T8-c`. The command went into
  `CLAUDE.md` with `-i`, and with a sentence requiring one `ruling` per label
  so the blind spot cannot be reached by writing.
- **B.6's candidate set.** "The `print(..., file=sys.stderr)` literals in
  `cli.py`" would have covered one of the two quoted sentences. The lag line
  is returned by `_lag_line` and printed through a variable, so the check
  reads returned literals as well. Stated in the helper's docstring rather
  than left as an open point, because the resulting check does fail for the
  right reason and stays green for the wrong one.
- **The TRUNCATE helper is a `str`, not a callable.** The dispatch asked for
  "a helper … without a private import or a `sys.path` trick"; a callable
  fixture satisfies that but breaks hypothesis's signature evaluation, and
  fixing that would have cost either a suppression or a ruff configuration
  entry. The table list is derived in one place either way, which was the
  point of the item.
