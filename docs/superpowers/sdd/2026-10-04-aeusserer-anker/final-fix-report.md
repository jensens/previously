# Fix wave after the final review — report

Implementer: Claude Opus 5.5, 2026-10-04. BASE `7c936be`.

Commits:

- `59072c4` fix: the chain check reads one snapshot (F2 alone)
- `059ccbd` fix: the final review's findings on the anchor, its input and its guides

Both commits are green on `uv run pytest` (267 and 270 passed, each with the tutorial block retyped from a real run in the same commit).

## A. Final review

### F2 — `examine` reads one snapshot (commit `59072c4`)

Changed:

- `src/previously/contract/store.py`: `LogStore.snapshot() -> AbstractContextManager[Conn]`. Module docstring: "eight methods" → "nine methods", re-measured (see C1).
- `src/previously/storage/postgres.py`: `self._snapshot_engine = engine.execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)`. `begin()` and `snapshot()` both return `self._transaction(engine)`, one private `@contextmanager` that carries the `OperationalError`/`ProgrammingError` translation (no second copy). `begin()` stays at READ COMMITTED; `append` and the worker untouched. Docstring of `snapshot` gives the reason, and the one-sentence safety statement checked against PostgreSQL 17's documentation: transaction-iso.html, "read-only transactions will never have serialization conflicts", and mvcc-intro.html, "reading never blocks writing and writing never blocks reading". The comment above `read` now says that one transaction is one snapshot only via `snapshot`.
- `src/previously/core/verify.py`: `examine` uses `storage.snapshot()`; the comment above it and the inner comment on the count reconciliation say "snapshot", and why one transaction is not enough.
- `docs/explanation/hash-chain.md`: the sentence at old line 281 rewritten (one snapshot, not one transaction; the measurement; `REPEATABLE READ`, read-only). Lines 268 and 309 ("in the same snapshot") are true now and left as they were.
- `docs/explanation/concurrency.md`: a paragraph after the one on `READ COMMITTED` being set by name: the chain check reads in a read-only `REPEATABLE READ` transaction, and why that leaves the appending procedure alone.
- `docs/reference/`: `grep -n "READ COMMITTED\|isolation\|snapshot" docs/reference/*.md` → nothing; no change.

Read-only is one execution option and measures as such (scratch `postgres:17`):

```
snapshot on repeatable read
begin off read committed
InternalError (psycopg.errors.ReadOnlySqlTransaction) cannot execute CREATE TABLE in a read-only transaction
begin after off read committed
```

(`SHOW transaction_read_only`, `SHOW transaction_isolation` inside each; a `begin()` after a `snapshot()` on the same pool is back at off/read committed.)

Tests (`tests/test_storage.py`):

- `test_a_snapshot_does_not_see_an_append_that_commits_inside_it` (assurance)
- `test_a_transaction_from_begin_sees_an_append_that_commits_inside_it` (control)

Mutation `isolation_level="READ COMMITTED"` in `snapshot`'s engine:

```
>           assert storage.count_events(c) == before == 1
E           assert 2 == 1
1 failed, 1 passed, 26 deselected in 6.21s
```

Restored: `2 passed, 26 deselected in 6.17s`.

Race (copy of the reviewer's script, DSN `localhost:55433/previously`, original untouched):

- before (tree at `7c936be`): `examine runs: 563, appends: 1493, runs with findings: 19`
- after: `examine runs: 161, appends: 1075, runs with findings: 0`
- after, second run: `examine runs: 116, appends: 1064, runs with findings: 0`

(Fewer runs after: the log grew across runs, ~2600 then ~3700 events.) Container `ff-anchor` removed (`docker rm -f ff-anchor`).

Miss in this commit, closed in the next: `docs/explanation/module-boundaries.md` quotes the protocol's method list (the grep output) and "eight methods"; `59072c4` left it stale. `059ccbd` retypes that block from the real grep (nine names including `storage.snapshot(`) and changes "eight" → "nine" and "would have carried nine" → "ten" (nine plus `units`).

### F1 — `Examination.anchor`

`src/previously/core/verify.py`: property `anchor` — `None if self.findings else self.tip`, docstring says why. `Examination`'s docstring no longer says an anchor printed from `tip` describes the checked chain unconditionally; it says `tip` is where the log ends, finding or not.

`_cmd_anchor` (`src/previously/cli.py`) restructured so the CLI decides nothing about the anchor: prints findings, prints `format_anchor(anchor)` if `anchor` is not None, else the empty-log notice only when there is no finding, returns `1 if findings else 0`. Output, exit codes and the two messages unchanged; existing tests green untouched. (The previous early `return 1` had to go: with it, the mutation below would not have reached the CLI test.)

New test `tests/test_verify.py::test_only_an_intact_chain_gives_an_anchor` (empty: neither; intact: both, equal; broken: tip, no anchor).

Mutation `return self.tip`:

```
FAILED tests/test_verify.py::test_only_an_intact_chain_gives_an_anchor - Asse...
FAILED tests/test_cli.py::test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain
2 failed, 74 passed in 14.41s
```

(The CLI one printed `FINDING 1: hash does not match the fields\n1 0000…0000\n`.) Restored: `76 passed in 14.40s`.

### F3 — repeated line, one finding

`examine`: `pending: dict[int, set[bytes]]`, `.add`; comment rewritten. `_closing_findings` takes `Mapping[int, Collection[bytes]]`. `test_two_lines_for_one_position_are_both_checked` untouched and green. New test beside it: `test_the_same_line_repeated_gives_one_finding` — three copies, rewritten event → `hash does not match the fields` + one `hash does not match the anchor`.

Mutation back to list/append:

```
E         Left contains 2 more items, first extra item: Finding(event_id=1, reason='hash does not match the anchor')
FAILED tests/test_verify.py::test_the_same_line_repeated_gives_one_finding - ...
1 failed, 26 passed in 6.84s
```

Restored: `27 passed in 6.75s`.

`docs/reference/cli.md`: lines repeating the same hash for an `id` count as one; lines with different hashes each compared. `<n>` still counts lines (unchanged, true: `count = len(anchors)`).

### F4 — `id` of more than 19 digits

`src/previously/core/anchor.py`: `_MAX_ID_DIGITS = 19` (`len(str(2**63 - 1))` = 19, measured; `event.id` is `BigInteger`, `schema.py:30`). Checked before `int()`; message `anchor line N: the id has more than 19 digits, longer than any event id` — no echo. New parametrized case `pytest.param(f"{'9' * 5000} {HASH}", "more than 19 digits", id="5000-digit-id")`, plus `assert len(str(caught.value)) < 100` for every case (pins no echo).

Mutation `if False:` in place of the length check:

```
E           ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; use sys.set_int_max_str_digits() to increase the limit
1 failed, 11 passed in 0.10s
```

Restored: `12 passed in 0.08s`. `cli.md`: "a positive integer" → "a positive integer of at most 19 digits" (otherwise false: a 20-digit positive integer is refused).

### F5 and F6 — `docs/how-to/verify-the-chain.md`

- First anchor: `previously verify --anchors anchors.txt` right after taking it, `chain intact, 1 anchor holds`; exit `2` when the file holds none; the two sentences on how such a file comes about kept.
- Container path: two conditions as a list — standard input passed through (`-i` for `docker exec`), no terminal (`-T` for `docker compose exec`), each with its consequence. Taken from `final-review.md`, *Hands-on session*, part 4 (`docker exec` without `-i` passes no input; `docker exec -t` mixes stderr into stdout). I named only the two tools measured there; `kubectl exec` (named in F5 but not in part 4's measurements) is left out.
- F6: the routine runs "between fetching the anchor file from the place you keep it and putting it back there"; "Put the file back after every run: an anchor that hasn't left the database's host isn't an anchor yet."

Hand-run session (fresh `postgres:17`, database `howto`; `P` = `uv run --project <worktree> previously`; stderr and stdout merged):

```
### empty log
$ P anchor > anchors.txt
the log is empty: nothing to anchor
[exit 0]
$ wc -c < anchors.txt
0
$ P verify --anchors anchors.txt
Error: the input holds no anchor
[exit 2]
### a file that holds the empty-log notice (what a terminal-allocating container exec writes)
$ P anchor > notice.txt 2>&1
[exit 0]
$ cat notice.txt
the log is empty: nothing to anchor
$ P verify --anchors notice.txt
Error: anchor line 1: expected `<id> <hash>`, got 7 fields
[exit 2]
### one event, first anchor
$ P append --source email --external-id h1 --text 'Hello' > /dev/null
[exit 0]
$ P anchor > anchors.txt
[exit 0]
$ P verify --anchors anchors.txt
chain intact, 1 anchor holds
[exit 0]
### a file that holds a FINDING line
$ P anchor > finding.txt
[exit 1]
$ cat finding.txt
FINDING 1: hash does not match the fields
$ P verify --anchors finding.txt
Error: anchor line 1: expected `<id> <hash>`, got 8 fields
[exit 2]
### the empty standard input of a container exec without -i
$ P verify --anchors - < /dev/null
Error: the input holds no anchor
[exit 2]
```

### F7

`pyproject.toml`: `(ruling T9-c of the stage 1a execution, whose ledger is lost, so the label resolves nowhere)`; reason beside it unchanged.

### F8

Tutorial, right after the *Pin the tip* block (no typed block changed): "This `anchors.txt` is this tutorial's alone, so delete it from your clone once you finish; {ref}`verify-the-chain` shows where a real one has to live."

### F9 — assurance 7

Mutation in `_cmd_verify`: the notice moved before `if examination.findings: return 1` (printed once whenever there are no anchors, findings or not):

```
>       assert err == ""
E       AssertionError: assert 'no anchor gi...sly anchor`\n' == ''
FAILED tests/test_cli.py::test_verify_without_an_anchor_says_what_it_does_not_attest
1 failed, 80 passed in 14.46s
```

The existing test already turns red (its second half asserts `err == ""` on a chain with a finding); no assertion added. Restored: `49 passed` (`tests/test_cli.py`). Assurance 7 is measured.

## B. Ledger items

- **B2**: docstring of `_read_anchors` writes `` `\\r\\n` and `\\r` become `\\n` ``. Before (HEAD, via `ast` on `git show`): `'text mode does: `\r\n` and `\r` become `\n`, and nothing else\n    ends a l'`. After (`uv run python -c "import previously.cli as c; …"`, shell only): `'text mode does: `\\r\\n` and `\\r` become `\\n`, and nothing else\nends a line. …'`; `chr(13) in doc` → `False`. The only newline left in that stretch is the docstring's own line break.
- **B3**: `the input holds no anchor`. `grep -rn "holds no anchor" src tests docs README.md` outside superpowers/_build: `core/anchor.py` (changed), `tests/test_anchor.py` (now `match=r"^the input holds no anchor$"`), `tests/test_cli.py` (fragment now `Error: the input holds no anchor`), `restore-from-a-backup.md:126` "holds no anchor line" — a description of the file case on a page about anchor files, not a quotation; judged true and left. `cli.md` describes it as "Input without a single anchor line" — already source-neutral. Mutation back to the old text in the core:
  ```
  FAILED tests/test_anchor.py::test_a_file_without_an_anchor_is_refused[lines0]
  FAILED tests/test_anchor.py::test_a_file_without_an_anchor_is_refused[lines1]
  FAILED tests/test_cli.py::test_a_broken_anchor_file_is_an_input_error[-Error: the input holds no anchor]
  3 failed, 58 passed in 13.99s
  ```
  Restored: `61 passed in 13.76s`. (Before this change, the `tests/test_anchor.py` check matched only `holds no anchor` and would have stayed green.)
- **B4**: `cli.md`: "a file or standard input that can't be read".
- **B7** (`restore-from-a-backup.md`):
  - M1: *After the check* now opens with "Keep `anchors.txt` unchanged in either case below", then the no-anchor case ("If no anchor was taken before the restore point …"), which names a new file `anchors-new.txt`, "never `anchors.txt`", and says to take the first anchor as the guide shows with that name in place of `anchors.txt`; then "Otherwise" the routine against `anchors-restored.txt`.
  - M2: Read the result: "… first step of *If the anchor file has no history*, after a restore on purpose to an earlier point"; fallback step 4: "keeping in mind what the cut can't show. Exit code `0` there doesn't mean that the restore reached the point you meant."
  - M3: fallback step 1: "If it reports no `anchored event is missing` finding, whether it exits `0` or reports only other findings, the restore reached the newest anchor and there's nothing to cut. Treat it as the first case, *Restore to the latest state*, and read its result there."
  - M4: "the last version of the anchor file from before that point"; step 1 adds: "Don't take a version recorded after the restore point: it holds anchors from after it, and each of those reads as a loss."
  - Still one admonition on the page.

## C. Closing

1. Numbers touched, re-measured:
   - `LogStore` methods: `grep -o 'storage\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py | sed 's/^[^:]*://' | sort -u` → 9 names (begin, count_events, insert_event, lookup, read, snapshot, source_keys, tip, units_by_event). In `contract/store.py` and `module-boundaries.md` (block retyped from that run; "ten" for a protocol copied from the implementation = nine + `units`).
   - `print` count: `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found` → `Found 24 errors.`; `pyproject.toml` says twenty-four, `tests/test_docs_references.py:219` says twenty-four. Unchanged.
   - 19 digits: `python3 -c "print(len(str(2**63-1)))"` → `19`.
   - 27 of 539 in the `snapshot` docstring and on `hash-chain.md`: the final review's measurement, cited as such (dated 2026-10-04); my own before figure (19 of 563) is in the commit message and here.
2. Quotations: `cli.md` changed no quoted message (the `Error:` sentence for empty input is not quoted on the page). `uv run pytest tests/test_docs_references.py -q -p no:randomly` → `5 passed in 0.11s`.
3. Tutorial: collected count changed twice (265 → 267 → 270); the test block was retyped from a real green `uv run pytest` run in each commit (rootdir line dropped, by a script that replaces the block with the run's output). No command of the tutorial session prints differently (`anchor`, `verify` outputs unchanged; the empty-input message is not in the session), so no session block was retyped. One sentence added (F8).
4. Gates, at `059ccbd`:
   - `uv run ruff check .` — `All checks passed!`
   - `uv run ruff format --check .` — `50 files already formatted`
   - `uv run pyright` — `0 errors, 0 warnings, 0 informations`
   - `uv run lint-imports` — `Contracts: 4 kept, 0 broken.`
   - `uv run pytest --cov --cov-report=term-missing` — `============================= 270 passed in 22.55s =============================` (`Total coverage: 97.56%`; `cli.py`, `core/anchor.py`, `core/verify.py`, `storage/postgres.py` 100 %)
   - `make -C docs html` — `The HTML pages are in _build/html.`; `make -C docs vale` — `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`; `make -C docs linkcheck` — exit 0, `grep -c broken docs/_build/linkcheck/output.txt` → `0`.
   (Also run before `59072c4`: the same five closing lines with `267 passed`, html/vale/linkcheck green.)
5. Hygiene: `git status --short` before each `git add`; only the changed files staged by name; nothing else appeared. Suppressions: none added (still five). No `§` added; `(frozen design record)` appears only in the commit message.

## Files changed

`59072c4`: `src/previously/contract/store.py`, `src/previously/storage/postgres.py`, `src/previously/core/verify.py`, `tests/test_storage.py`, `docs/explanation/hash-chain.md`, `docs/explanation/concurrency.md`, `docs/tutorials/record-your-first-event.md`.

`059ccbd`: `src/previously/cli.py`, `src/previously/core/anchor.py`, `src/previously/core/verify.py`, `tests/test_anchor.py`, `tests/test_cli.py`, `tests/test_verify.py`, `pyproject.toml`, `docs/reference/cli.md`, `docs/how-to/verify-the-chain.md`, `docs/how-to/restore-from-a-backup.md`, `docs/tutorials/record-your-first-event.md`, `docs/explanation/module-boundaries.md`.

## Open, and observations

- Nothing from the dispatch left open.
- F2's commit does not stand fully alone on the docs: `module-boundaries.md`'s method list went stale in `59072c4` and is fixed in `059ccbd` (no amend allowed).
- Out of scope, same class as F2: `src/previously/cli.py:237–241`, the comment in `_cmd_log`, says "for `show` it is not — there, event and units belong in the same snapshot", and `_cmd_show` reads under `begin()` (READ COMMITTED), so its event and units reads are two snapshots. Not changed (behavior of `show` was not in this wave); a candidate for `snapshot()` next.
- F10 and ledger items 1, 5, 6, 8, 9 not touched, as instructed.

## Residuals after the re-review

Commit `c2828b9` fix: four sentences that said more than is true, and one test for the snapshot's errors (BASE `059ccbd`).

1. **The serialization sentence names the level.** In `storage/postgres.py`, the `snapshot()` docstring now says "a read-only transaction at REPEATABLE READ never has a serialization conflict …". It adds one sentence on why the level matters: at SERIALIZABLE, the same page says, what even a read-only transaction reads is valid only once it commits, unless it is deferrable. Checked against the Serializable section of PostgreSQL 17's transaction-iso.html. In `docs/explanation/concurrency.md:48`, the sentence now reads "a read-only transaction at `REPEATABLE READ` never has a serialization conflict".
2. **Anchor id length.** In `core/anchor.py`, the constant is renamed `_MAX_ID_LENGTH` and the check stays before anything is echoed. The message is now `anchor line N: the id is longer than 19 characters, longer than any event id`, and the comment says why it speaks of characters. In `tests/test_anchor.py`, the `5000-digit-id` case follows the new wording. A new case `5000-letter-id` (`'x' * 5000`) has the same expectation and the same `< 100` bound. "of at most 19 digits" in `cli.md` stays, because it is still true.
   Mutation (`if False:` in place of the check):
   ```
   E           ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits; …
   E       AssertionError: Regex pattern did not match.
   E         Expected regex: 'longer\\ than\\ 19\\ characters'
   E         Actual message: "anchor line 2: the id has to be a positive integer, got 'xxxx…   (the 5000 letters echoed whole)
   FAILED tests/test_anchor.py::test_a_broken_line_is_refused_with_its_line_number[5000-digit-id]
   FAILED tests/test_anchor.py::test_a_broken_line_is_refused_with_its_line_number[5000-letter-id]
   2 failed, 11 deselected in 0.11s
   ```
   Under the mutation the non-digit case raises no `ValueError`, because `isdigit` refuses it. It is refused with the "positive integer" message instead, which echoes the whole field. The regex check fails first, and the `< 100` bound would fail as well. Restored: `13 passed in 0.08s`.
3. **The `snapshot()` error translation is now under test.** In `tests/test_cli.py`, `test_an_unreachable_server_shows_one_sentence` and `test_a_missing_table_shows_one_sentence` now also run `main(["verify"]) == 2`. They assert that its sentence equals the one from `log`. Each docstring says why `verify` is there: it reads through a different entrance to the storage (`snapshot`, not `begin`). No new test function.
   Mutation `return self._snapshot_engine.begin()` in `snapshot()`:
   ```
   E           sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed: connection to server at "127.…
   E           sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable) relation "event" does not exist
   FAILED tests/test_cli.py::test_an_unreachable_server_shows_one_sentence - sql...
   FAILED tests/test_cli.py::test_a_missing_table_shows_one_sentence - sqlalchem...
   2 failed, 47 deselected in 6.70s
   ```
   Restored (`git diff --stat` on the file is empty): `2 passed, 47 deselected in 6.12s`.
4. **The `_cmd_log` comment.** It now says that `show` reads an event and its units in one transaction but in two statements, which are two snapshots under READ COMMITTED. It shows one state for a different reason: `insert_event` writes both inside the one transaction of `append` (`core/append.py:345`/`:368`, event then units on the same `conn`). Nothing in `src` rewrites or deletes either afterwards; a `grep` for update/delete in `src` finds only the projection tables. `show` was not moved to `snapshot()`.

Count: `uv run pytest --collect-only -q -p no:randomly | tail -1` → `271 tests collected in 0.17s` (was 270). The tutorial's test block was retyped from a real green `uv run pytest` run (`271 passed in 21.87s`), without the `rootdir:` line.

Gates on the tree committed as `c2828b9`:

- `uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `50 files already formatted`
- `uv run pyright` — `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` — `Contracts: 4 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` — `============================= 271 passed in 21.57s =============================` (`Total coverage: 97.56%`)
- `make -C docs html` — `The HTML pages are in _build/html.`; `make -C docs vale` — `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`; `make -C docs linkcheck` — exit 0, 0 broken.

`git status --short` before `git add` showed exactly the seven changed files, and they were staged by name; nothing else.
The out-of-scope observation above on `_cmd_log` is closed by item 4.
