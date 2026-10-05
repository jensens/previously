# Task 3 report — erasure of events and units

Status: DONE_WITH_CONCERNS. Commit `a0377ba` (base `30f7768`), one commit, six gates green.
`git status --short` before work: clean. Nothing foreign in the tree.

## What was implemented, step by step

1. **`core/redaction.py`** (pure): `Redaction`, `MalformedAction`, `event_payload`, `units_payload`,
   `action_name`, `parse` (strict, all three forms incl. `blob`), `RedactionIndex`
   (`add`, `of_event`, `of_unit` — own unit redaction, else whole-event redaction —, `__iter__`;
   first redaction of a target wins), `read_index` (skips payload-`NULL` actions and malformed ones).
2. **Store:** `LogStore.read_by_kind`; new protocol `RedactionStore` (`lock_event` FOR UPDATE,
   `erase_payload`, `erase_units`). `PostgresStorage` implements them; a shared `_event_row`
   helper now builds `EventRow` for `read`, `read_by_kind`, `lock_event`.
   **Measured finding:** `erase_payload` with `payload=None` wrote JSON `null`, and
   `event_payload_object_check` refused it (`CheckViolation`). Uses `sqlalchemy.null()`;
   comment beside it.
3. **`core/redact.py`:** `Redacted`, `redact_event`, `redact_units`, procedure as briefed
   (lock → refusals → `read_index` after the lock → covered/skip → `prepare`/tip/`link`/`insert_event`
   → tombstones; one transaction; `ChainPositionTaken` → `backoff_delay`, `MAX_RETRIES`, `ChainConflict`).
   Prepared per attempt (not once), because what is named depends on the redactions read under the lock.
   `RedactionRefused` in `core/errors.py`.
4. **`verify`:** class `_Erasures` (`observe` per row, `reconcile` at the end inside the snapshot,
   right beside the count reconciliation) and function `_execution_findings` (reads target via
   `read(conn, from_id=target, limit=1)` + `units_by_event`). v1 `_units_finding` no longer
   reports a unit without content; partial v1 erasure is decided in `reconcile`.
   Blob-scope redactions are parsed and indexed, and skipped in `_execution_findings` (task 7).
5. **CLI:** `redact event|units` (second-level subparsers), `COMMANDS` entry after `append`;
   `--reason` empty → `RedactionRefused("--reason must not be empty")`; stdout via `_redacted_line`
   (a returned string, so `test_docs_references` reaches it), stderr per skipped unit.
   `show` reads `read_index`, prints `<erased by event N>` / `<erased>`, `evidence=` only if the key exists.
6. Sentences turned over — list below.
7. **`docs/explanation/erasure.md`** (label `erasure`), in `explanation/index.md` after `hash-chain`.
8. **`docs/reference/cli.md`:** nine subcommands, exit-code row, `redact` section (forms, payload,
   two stdout lines, stderr notice, five refusals), `show` lines, nine findings (two from task 2,
   seven from this task) as a quoted block plus table.
9. Tutorial test run retyped from a real run: **389 passed**.

## TDD evidence

| Step | RED | why expected | GREEN |
|---|---|---|---|
| 1 | `pytest tests/test_redaction.py` → `ModuleNotFoundError: No module named 'previously.core.redaction'` | module absent | 15 passed (later 17 with two added parse cases) |
| 2 | `pytest tests/test_storage.py -k "lock_event or erase or read_by_kind"` → 5 failed, `AttributeError` | methods absent | after implementation 1 failed (`erase_payload`: `CheckViolation event_payload_object_check`, the JSON-null finding above), then 35 passed |
| 2 | protocol test: pyright | — | 0 errors; mutation: `erase_units` renamed → pyright `"PostgresStorage" is incompatible with protocol "RedactionStore[Connection]"`, restored → 0 errors |
| 3 | `pytest tests/test_redact.py` → collection error (`RedactionRefused`/`core.redact` absent) | absent | 12 passed, 2 failed — `test_units_of_a_version_1…` (`units_hash does not match the units`) and `test_a_tombstone_without_an_order_gets_one` (`verify` reported nothing): both need step 4, as expected |
| 4 | `pytest tests/test_verify.py` → 14 failed (every new test and the flipped ones) | `verify` knew no erasure | 75 passed over test_verify + test_redact; `test_tombstone_and_redaction_are_matched_across_batch_boundaries` was green before (it guards the per-batch mutation, see below) |
| 5 | `pytest tests/test_cli.py -k "redact or show_says"` → 8 failed, `SystemExit: 2` | no `redact` command | 59 passed |
| 5 | docs-references: `{ref}` `erasure` dangling, then the quote check refused `redacted by event 42` | page absent; `_is_the_same_sentence` demanded the line end with the last literal part, which an f-string ending in an interpolation never satisfies | 5 passed after `_static_parts` marks an interpolation at either end with an empty part (comment beside it) |

## Mutations

All via a scratch script applying exactly one replacement and restoring the original.

| Mutation | Red | Control green |
|---|---|---|
| `erase_units` leaves `salt` | 12 failed (11 in test_redact + `test_erase_units_touches_only_the_named`), all `CheckViolation … "unit_tombstone_check"` | `test_a_missing_event_is_refused` passed (also `test_units_of_a_version_1…`: v1 units have no salt) |
| `redact_event` sets tombstones in a second transaction | `test_redaction_and_tombstones_arrive_together_or_not_at_all`: `assert [1, 2] == [1]` | `test_redacting_an_event_writes_an_action_and_leaves_tombstones` passed |
| `read_index` before `lock_event` | `test_two_redactions_of_one_event_at_once_write_one` red in **20 of 20** runs (`20× 1 failed`) | `test_a_second_redaction_of_the_same_event_writes_nothing` passed; unmutated, the two-thread test passed **20 of 20** runs |
| reconciliation dropped | `test_a_tombstone_without_a_redaction_fires[version-1]`, `[version-2]` | `test_an_intact_chain_passes` passed |
| reconciliation per batch (reconcile + fresh `_Erasures` after each batch) | `test_tombstone_and_redaction_are_matched_across_batch_boundaries` | `test_a_tombstone_without_a_redaction_fires` (both) passed |
| target not read, a counted tombstone at the event taken as execution | `test_a_redaction_of_units_that_was_not_carried_out_fires[version-1]`, `[version-2]` | `test_redacting_units_leaves_the_others_attested` passed |
| v2 skip over a unit without content removed (deferred M-2) | `test_redacting_units_leaves_the_others_attested`: extra `Finding(1, 'unit 2 does not match its digest')` | `test_a_missing_event_is_refused` passed |
| cli.md quotes `there is no such event 9` | `cli.md quotes the refusal 'there is no such event 9' and no RedactionRefused raises it` | restored → 5 passed |
| cli.md quotes `redaction names a target that is missing` | `…core/verify.py produces no such reason` | restored → 5 passed |
| cli.md quotes `already erased by event 42` | `cli.md quotes 'already erased by event 42' as output and no message in cli.py says that` | restored → 5 passed |

Two-thread test design: a store wrapper (`_MeetingEraser`, shape of `_FailingStore`) waits at a
`threading.Barrier` inside its first `lock_event`, so both erasures ask for the lock at the same
moment; that makes the mutation deterministic rather than timing-dependent.

## Complexity (`ruff check --select C901 --config 'lint.mccabe.max-complexity = 1'`)

`examine` 9 (also 9 at `30f7768`, measured on a copy of the committed file), `parse` 9,
`_cmd_show` 7, `observe` 6, `_execution_findings` 6, `redact_units.once` 5, `_cmd_redact` 4,
`main` 3, `reconcile` 2, `redact_event.once` 2. Threshold 10.

## Existing tests whose arrangement or expectation changed

- `test_verify.py::test_a_tombstone_passes` → `test_a_tombstone_without_a_redaction_fires`, expectation `[Finding(1, "payload is erased without a redaction")]` (brief).
- `test_verify.py::test_v1_a_unit_without_content_is_the_units_hash_finding` → `…_is_an_erasure_finding_not_the_units_hash_finding`: expects `unit 1 is erased without a redaction` + `units are erased in part, which version 1 cannot attest`. Reason: the brief turns the v1 case into the two decisions; the old expectation is what task 3 removes. Kept as the "no redaction" case beside the new `test_partial_unit_tombstones_in_version_1_fire` ("with redaction" case).
- `test_schema.py::test_a_real_tombstone_stays_permitted_and_passes_verification` → `…_and_is_found_without_a_redaction`, expectation the one erasure finding; docstring says which half held and which turned (brief).
- `test_cli.py::test_show_says_so_when_a_unit_is_erased` and `…_payload_is_erased`: docstrings only ("nothing in the tree erases a unit yet" was false); expectations unchanged.
- `test_docs_references.py`: `_static_parts` now marks an interpolation at either end (reason above); new `_raised_patterns`; the main test reads two more output blocks, the refusals and the nine findings; docstrings recounted (five stderr sentences + two stdout lines in five blocks, twelve findings, twenty-six `print`s).

## Departures from the brief

- **Signatures:** none. Extra public names: `REDACTION` constant and type alias `Scope` in `core/redaction.py` (verify uses `REDACTION`).
- **`redaction_id` when every named unit is covered by different redactions:** the newest (max id). The brief says "nennt die deckende Tilgung" without saying which; documented in the docstring and on cli.md.
- **Target-is-a-redaction rule:** refuses any event of kind `action` (every action written so far is a redaction); comment says so. When another action kind arrives, this narrows.
- **Empty reason in core:** `redact_*` also refuse an empty reason (`RedactionRefused("a redaction needs a reason, and the reason is empty")`) and `redact_units` an empty `seqs` (`ValueError`), so a code caller cannot write an action `verify` cannot read. Not in the wording table (unreachable from the CLI, which refuses first with the table's `--reason must not be empty`). One extra test covers both.
- **Tests beyond the prediction:** `test_an_empty_reason_or_no_unit_is_refused_before_the_store_is_asked`, `test_read_index_passes_over_what_it_cannot_read` (closes `read_index`'s skip branches and verify's blob-skip line), two parse cases (`units-not-a-list`, `target-not-an-object`). The unit-tombstone, not-carried-out tests run on both versions (`WRITTEN_IN`) as instructed, which adds cases.
- **Files outside the list:** `.vale-styles/config/vocabularies/Previously/accept.txt` (+`redactions`, Vale.Spelling refused the plural) and `.vale.ini` (its comment counts the lowercase entries: now twelve of sixteen, recounted with the `awk` it names); `src/previously/core/hashing.py` (SALT_BYTES comment, per deferred finding).

## Deferred findings

- **M-2 (verify skip over erased v2 unit):** reached by `test_redacting_units_leaves_the_others_attested`; mutation measured above. `verify.py` now at 100 % coverage.
- **M-5 (cli.md lacks task 2's findings):** `unit <seq> does not match its digest` and `hash_version <n> is not known` are in the nine-finding block and table, held by the docs-references test.
- **hashing.py SALT_BYTES / `unit_digest`:** re-read against the tree. `SALT_BYTES` rewritten to say that an erasure takes the salt, `core.redact` erases both in one statement, and the database refuses a tombstone keeping its salt. `unit_digest`'s "a stored unit may have lost its content to an erasure" is true now and stays; `new_salt` and `HashableUnit` docstrings re-read, true.

## Sentences found no longer true and rewritten

- `storage/postgres.py` module docstring: added the two `UPDATE`s behind `RedactionStore`, no `DELETE`, what they may set.
- `contract/store.py`: method count nine → ten with the command and the five modules; "both importers" → every importer, re-measured (`'previously.contract.store' in sys.modules` → `False` after importing cli and the five core modules); `LogStore` docstring says "never change" holds for this protocol and why.
- `cli.py::_cmd_log` comment ("nothing in `src` rewrites or deletes either"): rewritten; it now says `show` reads in three statements and can show a payload from before an erasure beside units from after it.
- `cli.py::_cmd_show` comment (payload line, evidence line).
- `storage/schema.py`: `event_payload_object_check` closing paragraph (past tense, redemption exists); `event_prev_hash_idx` comment (no lock on the tip; the one row lock is on the erased event).
- `core/verify.py`: `_payload_finding` docstring; `_units_finding` docstring.
- `core/append.py` `_KIND` comment.
- `docs/explanation/hash-chain.md`: the `tombstone-seam` admonition replaced by what the seam was, what it cost, that stage 1c paid it, `{ref}erasure`; "the mechanism isn't built yet"; "announced way … would become"; "A forger gains nothing today"; the closing paragraph of the version 2 section ("built for an erasure that doesn't exist yet … nothing erases anything").
- `docs/explanation/concurrency.md`: intro ("no SELECT … FOR UPDATE") narrowed to the tip; new section "Two write paths on one chain".
- `docs/reference/cli.md`: "eight subcommands" → nine; `show` lines.
- `pyproject.toml` T201 comment: twenty-four → twenty-six.

## Measured numbers

- Tests: **389** (`pytest --collect-only -q` → `389 tests collected`; brief predicted 367 from 315; base was 330, so +59).
- `print` calls in `cli.py`: **26** (`ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py --output-format concise | grep -c T201`).

## Six gates, final lines (at `a0377ba`'s tree)

```
uv run ruff check .                          -> All checks passed!
uv run ruff format --check .                 -> 58 files already formatted
uv run pyright                               -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                          -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> ============================= 389 passed in 31.60s =============================
                                                (Required test coverage of 90.0% reached. Total coverage: 97.90%)
make -C docs html                            -> build succeeded. / The HTML pages are in _build/html.
make -C docs vale                            -> ✔ 0 errors, 0 warnings and 0 suggestions in 23 files.
make -C docs linkcheck                       -> build succeeded.
```

## Files changed

Created: `src/previously/core/redaction.py`, `src/previously/core/redact.py`, `tests/test_redaction.py`,
`tests/test_redact.py`, `docs/explanation/erasure.md`.
Modified: `src/previously/{cli.py, contract/store.py, core/append.py, core/errors.py, core/hashing.py, core/verify.py, storage/postgres.py, storage/schema.py}`,
`tests/{test_cli.py, test_docs_references.py, test_projection_store.py, test_schema.py, test_storage.py, test_verify.py}`,
`docs/explanation/{concurrency.md, hash-chain.md, index.md}`, `docs/reference/cli.md`,
`docs/tutorials/record-your-first-event.md`, `pyproject.toml`, `.vale.ini`,
`.vale-styles/config/vocabularies/Previously/accept.txt`.

## Self-review findings and concerns

1. **Stale sentences outside this task's files, left for their owners:**
   `docs/explanation/projections.md` §"What a chronicle per unit teaches about erasure" ("Erasure isn't built …", lines ~199–220) — task 4's file; README "no erasure" — task 8;
   `tests/test_projection_worker.py::test_a_tombstoned_event_keeps_…` docstring — task 4 renames it per its brief.
   Until task 4 the chronicle keeps showing erased units already projected; `erasure.md` says so in one sentence.
2. **`redact.py` line 128 (`ChainConflict` after eight lost races) is uncovered**, like the same line in `append.py` (466). A wrapper LogStore whose `insert_event` always raises would reach it; not written.
3. **`_static_parts` loosening:** an f-string starting or ending with an interpolation now matches any text at that end. Patterns from `_raised_patterns` and `_finding_patterns` have no minimum length (only `_message_patterns` keeps `>= 10`), so a future `raise RedactionRefused(f"{x}")` would match every quoted line; such a pattern is dropped today (empty literal text returns `[]`), but `f"{a}: {b}"` would not be.
4. **v1 event with all units erased:** its `units_hash` is no longer computed, so a deleted unit row on such an event is not found by the units digest (the event hash still covers `units_hash`, but nothing recomputes it). The brief prescribes "wird an ihm keine Einheit geprüft"; noting the consequence.
5. **`show` reads in three statements under READ COMMITTED** and can show a payload from before a concurrent erasure beside units from after it; the comment in `_cmd_log` says so. Not a check path.
6. `.vale.ini` and the vocabulary were touched although not in the file list (Vale refused "redactions").

---

# Fix round 1

Commit `d95882d` on top of `a0377ba` (no amend). Pages edited after invoking `plone-doc-style:author`.

## I-1 — version 1 skip cost (`erasure.md`) and its pinned limit

- `erasure.md`: the event row of the table says the tombstone rows are attested in hash format 2 and by nothing in hash format 1; the section *Why the payload can't be erased in part* gains a paragraph: once all units of a v1 event are erased, nothing recomputes the units digest, so the number and `seq` of its tombstone rows are attested by nothing; a row deleted or added passes; in v2 the same forgery is a finding. Names the test.
- Test `tests/test_verify.py::test_the_tombstone_rows_of_a_fully_erased_version_1_event_are_attested_by_nothing`, parametrized forgery × version (four cases): `redact_event`, `verify() == []`, then `DELETE` of tombstone row seq 2 / `INSERT` of a tombstone row seq 9 (copying a digest). Expectation: version 1 → `[]` (the pinned limit); version 2 → `[Finding(1, "units_hash does not match the units")]` (the control). All four green:
  `uv run pytest tests/test_verify.py tests/test_redact.py tests/test_redaction.py tests/test_cli.py tests/test_migration_0003.py -q -p no:randomly` → `163 passed`.

## I-2 — `hash-chain.md` "five things"

"establishes five things; … the one line each" → "six things; … the lines they print as". Added: in version 1 the units digest is computed only while every unit still has its text. Added the sixth: erasure — tombstones against redactions and redactions against targets, matched after the whole pass, with `{ref}erasure`. Re-read the rest of the section: "The fifth check closes it by counting…" still names the count check correctly (it stays fifth).

## Minor 6 (confirmed gap) — retry path forced deterministically

`tests/test_redact.py` gains `_ContestedLog`, a wrapper around the real storage implementing all ten `LogStore` methods, whose `insert_event` raises `ChainPositionTaken` for its first `losses` calls (or always). Real backoff, at most 0.715 s in all.
- `test_a_lost_chain_position_is_retried_and_leaves_nothing_behind` (losses=1): `Redacted(2, True)`, `inserts == 2`, kinds `["observation", "action"]`, all units tombstones, `verify() == []`.
- `test_a_chain_position_never_won_ends_in_a_chain_conflict` (always): `ChainConflict` matching `after 8 attempts`, `inserts == MAX_RETRIES`, only the observation, payload and units untouched.

Mutation — the `except ChainPositionTaken` branch re-raises:
```
uv run pytest tests/test_redact.py -q -p no:randomly -k "lost_chain_position or never_won or writes_an_action_and_leaves"
E           previously.storage.errors.ChainPositionTaken: event_prev_hash_idx
FAILED tests/test_redact.py::test_a_lost_chain_position_is_retried_and_leaves_nothing_behind
FAILED tests/test_redact.py::test_a_chain_position_never_won_ends_in_a_chain_conflict
2 failed, 1 passed, 16 deselected
```
Control `test_redacting_an_event_writes_an_action_and_leaves_tombstones` green. Reverted. The two-thread race test is unchanged. `redact.py` coverage now **100 %** (85 statements; line 128 `ChainConflict` reached).

## Riding along

- **Minor 1:** `redact.py::_retrying` docstring and `concurrency.md`: the position is lost at `insert_event`, before any tombstone, so the rollback undoes the lock and reads only; only the winning attempt sets tombstones.
- **Minor 2:** v1 refusal now the table's literal sentence (`hash_version == 1`); any other version that is not 2: `event <id> names hash format <n>, which is not known` (**new wording, not in the table**). Test `test_units_of_an_event_in_an_unknown_hash_format_are_refused` (hash_version set to 3 by SQL; exact message; nothing written). `cli.md` lists six refusals now, with a sentence on the fourth; `test_docs_references.py` reads "Six refusals", expects 6 — 5 passed.
- **Minor 4:** empty `seqs` → `RedactionRefused("a redaction of units needs at least one unit")` (new wording, unreachable from the CLI, `nargs="+"`). Covered in `test_an_empty_reason_or_no_unit_is_refused_before_the_store_is_asked`.
- **Minor 5:** blanks-only reason refused in `cli.py` (`args.reason.strip()`, wording `--reason must not be empty`, comment), in `redact._check_input` (`reason.strip()`), and in `redaction.parse` (malformed). Tests: `test_cli.py` param `blank-reason`; the empty-reason test in `test_redact.py` loops over `""` and `" \t\n"`; `test_redaction.py` param `reason-only-blanks`. `cli.md` argument row says "not empty and not blanks alone" plus one sentence under the refusals.
- **Minor 8:** `postgres.py` module docstring's first sentence corrected itself: "no delete on the log, no update on it beyond the two an erasure needs, …", then states that the architecture said "no update" unqualified, and the two UPDATEs.
- **Minor 9:** `hashing.py` SALT_BYTES: "The store erases both in one statement (`erase_payload` and `erase_units` behind `RedactionStore`, called by `core.redact`)".
- **Minor 10 (second half):** `test_migration_0003.py` comment now says the tombstone is made by hand because the downgrade asks only whether a unit without content exists. `chronicle.py:43` left for task 4.

## Counts and gates

- Tests: **398** (`pytest --collect-only -q` → `398 tests collected`; +9: four pin cases, two retry tests, unknown-version test, two blank-reason params). Tutorial block retyped from a real run.
- `print` calls in `cli.py`: unchanged at 26.

```
uv run ruff check .                          -> All checks passed!
uv run ruff format --check .                 -> 58 files already formatted
uv run pyright                               -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                          -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> ============================= 398 passed in 32.21s =============================
                                                (Total coverage: 97.98%; core/redact.py 100%, core/redaction.py 100%)
make -C docs html                            -> build succeeded.
make -C docs vale                            -> ✔ 0 errors, 0 warnings and 0 suggestions in 23 files.
make -C docs linkcheck                       -> build succeeded.
```

## Concerns

1. Two wordings outside the table: the unknown-version refusal (now quoted on `cli.md` and held by the docs test) and the empty-units refusal (core only).
2. The v1 limit is pinned, not closed; whoever closes it (e.g. by counting tombstone rows against something attested) has to turn that test over knowingly.
