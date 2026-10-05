# Task 2 report — hash format v2 end to end

Status: DONE_WITH_CONCERNS
Commit: `4c078ad feat: append writes hash format 2, verify checks each row by its version`
Measured test count: **318** (brief predicted 315; +3 explained below).

## What was implemented, step by step

1. **Rows and schema.** `EventRow` gained `hash_version: int = 1`, `payload_salt: bytes | None = None`; `UnitRow.content` is `str | None`, plus `digest`, `salt` (default `None`). `schema.py` and `migrations/versions/0003_hash_version_2.py` add the four columns, drop `NOT NULL` on `unit.content`, and add `event_payload_salt_check` and `unit_tombstone_check` with the exact SQL of the brief. `downgrade()` checks first (`EXISTS` on `hash_version = 2` and on `content IS NULL`) and raises `alembic.util.CommandError` with one sentence before dropping anything.
2. **Storage.** `insert_event` writes `hash_version` and `payload_salt` explicitly from the row, and `digest`/`salt` per unit; `read`, `units`, `units_by_event` return them.
3. **`core/chain.py`.** `PreparedUnit`, `Prepared`, `prepare`, `link` with the exact signatures of the brief. `prepare` first calls `canonical(payload)` (see departure 2), then draws salts, then computes the digests.
4. **`append`.** `_prepare` returns `list[tuple[RawEvent, Prepared]]`; the checks keep their place and order; the loop calls `link(ready, event_id=next_id, prev_hash=prev, recorded_at=recorded_at)` and `storage.insert_event(conn, row, units, ready.key)`. Both `except` branches are untouched. Docstring of `_prepare` says the salts are drawn once, before the first attempt.
5. **`verify`.** `_check_event` checks the linkage, then looks the version up in `_CHECKS = {1: _check_version_1, 2: _check_version_2}`; unknown → `hash_version <n> is not known`, nothing else computed for the row. v2 is split into `_payload_finding_v2`, `_unit_findings`, `_units_finding_v2`, `_event_hash_finding` (shared by both versions, takes the hash function). v1 `_units_finding` returns the units finding if any unit lacks content. `ruff --select C901` passes.
6. **Readers of `UnitRow.content`.** `chronicle.derive` skips units without content (version stays 1); `cli show` prints `  ¶<seq> <erased>`; `verify` as above.
7. **Sentences** — see below.
8. **Docs** — `database-schema.md`, `hash-format.md`, `hash-chain.md`, `cli.md` (show line), tutorial typed run. `plone-doc-style:author` was invoked first.

## TDD evidence

| Step | RED (command → output) | why expected | GREEN |
|---|---|---|---|
| 1 rows | `uv run pytest tests/test_rows.py -q` → `AttributeError: 'EventRow' object has no attribute 'hash_version'`, `AttributeError: 'UnitRow' object has no attribute 'digest'`, 2 failed | fields did not exist | 6 passed |
| 1 schema | `uv run pytest tests/test_schema.py -q` → `psycopg.errors.UndefinedColumn: column "hash_version" does not exist` (3 failed: default, salt check, unit tombstone) | columns not migrated | 17 passed after migration |
| 1 columns test | `test_the_declared_columns_match_the_migrated_database` was green before `schema.py` changed (correct: metadata == db). After adding columns to `schema.py` **without** the migration: `AssertionError: event … Right contains 2 more items: {'hash_version': False, 'payload_salt': True}` | the requested measurement: a column in `schema.py` missing from the migration now fails a gate | green with migration |
| 1 migration | `uv run pytest tests/test_migration_0003.py` → `Failed: DID NOT RAISE CommandError` | `append` still wrote v1, so nothing to refuse | green after step 4 |
| 2 storage | `-k round_trip` → `assert 1 == 2` (hash_version) and `UnitRow(… digest=None, salt=None) != UnitRow(… digest=b';;;…', salt=b'LLL…')` | storage did not carry fields | 30 passed |
| 3 chain | `tests/test_chain.py` → collection error (module missing) | module did not exist | 6 passed |
| 4 append | `-k version_2` → `assert 1 == 2` (`hash_version=1, payload_salt=None`) | append wrote v1 | green |
| 5 verify | `tests/test_verify.py` → 31 failed, 6 passed | v2 rows computed with v1 functions | 37 passed (later 38) |
| 6 derive | `assert [(1, None), (2, 'b')] == [(2, 'b')]` | no skip | 10 passed |
| 6 cli | `assert '  ¶1 <erased>\n  ¶2 Two\n' in '…  ¶1 None\n  ¶2 Two\n'` | printed `None` | green |
| p8 | written after verify; green on first run (property test, no RED by construction) | — | green |

## Mutations

All done in the tree with `sed`, covering tests run, reverted; `grep -rn MUTATION src tests migrations` empty afterwards.

1. **`prepare` uses one salt for all units** (`salt = new_salt()` → `salt = bytes(SALT_BYTES)`):
   `uv run pytest tests/test_chain.py -k "draws_one_salt or computes_what"` →
   `AssertionError: assert 2 == 3` in `test_prepare_draws_one_salt_for_the_payload_and_one_per_unit` (FAILED); `test_prepare_computes_what_the_hash_functions_compute` passed. `1 failed, 1 passed`.
2. **v2 rows computed with v1 functions** (`HASH_VERSION_2: _check_version_1`):
   `FAILED test_an_intact_chain_passes`, `PASSED test_a_version_1_chain_still_passes`. `1 failed, 1 passed`.
3. **per-unit check removed** (`findings.extend(_unit_findings(row, units))` → `pass`):
   `FAILED test_v2_a_rewritten_unit_fires_on_that_unit_and_not_on_its_neighbour` (`assert [] == [Finding(… 'unit 2 does not match its digest')]`), `PASSED test_v2_a_deleted_unit_row_fires`.
4. **unknown version computed as v2** (`_CHECKS.get(row.hash_version, _check_version_2)`):
   `FAILED test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on` — row 1 produced **no finding at all** (`At index 0 diff: Finding(event_id=2, …payload…) != Finding(event_id=1, reason='hash_version 3 is not known')`): the column says 3, the function hashes `"v": 2`, everything adds up. `PASSED test_a_flipped_hash_version_fires`.
5. (mine) **payload-first `canonical` dropped in `prepare`**: `FAILED test_prepare_refuses_what_the_canonical_form_refuses` (`Regex pattern did not match`), `FAILED test_cli.py::test_an_unrepresentable_character_in_argv_gives_one_sentence[--text-\ud800-…]` (`'Error: $.payload.text: string not representable…'`); controls `test_prepare_computes_what_the_hash_functions_compute` and the four other cli parameters passed.
6. (mine) **payload-first `canonical` dropped in `verify`**: `FAILED test_w1_a_poisoned_payload_does_not_blind_the_unit_check` (`"payload not canonicalizable: $.payload: key 'Note' …"`), both `test_w1_a_non_canonicalizable_payload_…` parameters passed (they only check `startswith("payload not canonicalizable: ")`).
7. (mine) **v1 "unit without content" guard dropped** (`if False:`): `test_v1_a_unit_without_content_is_the_units_hash_finding` **stays green** — `canonical` hashes `None` as JSON `null`, so the digest simply mismatches. The guard is there for the type (`cast` to `HashableUnit`), not for behaviour; no test can tell it apart. Recorded as concern 4.

## Existing tests: arrangement changed under ruling P-1

Each `UPDATE event SET payload = NULL` became `UPDATE event SET payload = NULL, payload_salt = NULL`, with a comment citing the ruling and its reason:
- `tests/test_verify.py::test_a_tombstone_passes`
- `tests/test_schema.py::test_a_real_tombstone_stays_permitted_and_passes_verification`
- `tests/test_cli.py::test_show_says_so_when_the_payload_is_erased`
- `tests/test_projection_worker.py::test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null`
No unit tombstone was forged by raw SQL in an existing test.

Other arrangement change (not P-1): `tests/test_hashing.py::test_units_hash_treats_rawunit_and_unitrow_alike` passes `cast("list[HashableUnit]", from_the_row)` — pyright rejects `UnitRow` for `HashableUnit` since `content` is optional. Pinned vector untouched.

## Existing tests whose expectation changed

1. `test_k1_f1_a_rewritten_unit_content_fires` → `unit 1 does not match its digest` (named by the brief); twin `test_k1_f1_a_rewritten_unit_content_fires_in_version_1` keeps `units_hash does not match the units` on a hand-written v1 event.
2. `test_verify.py::test_w1_a_poisoned_payload_does_not_blind_the_unit_check`: second finding `units_hash does not match the units` → `unit 1 does not match its digest` (same forgery, v2 now names the unit). First finding **tightened** from `startswith("payload not canonicalizable: ")` to `startswith("payload not canonicalizable: $: key 'Note' ")`, to pin the path (mutation 6).
3. **`test_append.py::test_the_kind_of_evidence_lands_in_the_payload` — finding, against the brief's instruction.** The brief says existing `test_append.py` tests stay green without touching an expectation, and a red one is a finding, not a reason to adapt. It went red: `assert payload_hash(row.payload) == row.payload_hash` → `At index 0 diff: b'\xe2' != b'\x00'`, because the stored digest is now the salted v2 one. All six gates must be green at the final commit, so I changed it to `assert row.hash_version == 2`, `payload_salt is not None`, `payload_hash_v2(row.payload, row.payload_salt) == row.payload_hash`. The stated property ("payload and payload_hash have to mean the same payload") is unchanged; the function computing it follows the format. **The controller should rule on this.** If it should stay red, revert that one hunk.

## Departures from the brief

1. **+3 tests beyond the brief:** `test_v2_a_missing_salt_or_digest_fires_and_does_not_break_off` (payload salt NULL beside a payload, unit digest NULL — branches the brief describes but no named test reaches), `test_v1_a_unit_without_content_is_the_units_hash_finding` (v1 behaviour the brief describes), `test_cli.py::test_show_says_so_when_a_unit_is_erased` (the contractual `  ¶<seq> <erased>` wording). 315 + 3 = 318.
2. **`prepare` and `_payload_finding_v2` canonicalize the payload on its own first.** Without it, `test_cli.py::test_an_unrepresentable_character_in_argv_gives_one_sentence[--text-…]` went red: the message said `$.payload.text` instead of `$.text`, which is what `hash-format.md` documents. Costs one extra canonicalization per payload. Brief signatures unchanged.
3. **`hashing.py` beyond the module docstring:** the comments above `HASH_VERSION_1`/`HASH_VERSION` (named by the controller) and one paragraph added to the `HashableUnit` docstring (UnitRow matches only once content is known, `verify` casts).
4. **`docs/reference/cli.md`** (not in the brief's file list): the `show` unit line now names `  ¶<seq> <erased>`.
5. **`docs/explanation/hash-chain.md`** (not in the brief's file list, named by the controller).
6. Downgrade refusal wording (brief gives none): `refusing to downgrade below 0003_hash_version_2: the log holds events in hash format 2, which cannot be verified without the salts this would drop` and, joined by `; `, `the log holds units without content, which cannot be NOT NULL again`. Measured with the real CLI on a scratch container (`uv run alembic downgrade 0002_projections`): exit 255, stdout `FAILED: refusing to downgrade below 0003_hash_version_2: the log holds events in hash format 2, …`, no traceback.
7. `_CHECKS` typed as `Mapping[int, Callable[…]]`; v1/v2 dispatch through it rather than `if/elif`.

## Sentences rewritten beyond those named

- `core/append.py` module docstring: "therewith … inevitably the same `hash` as well" (two writers at one position do not compute the same hash; with salts not even for the same event) → "a duplicate `hash` can only come from such a pair".
- `core/append.py` `_prepare` docstring: "a requirement for two of the three results" and `payload_hash(row.payload)` — rewritten for `Prepared`.
- `storage/postgres.py` `_CHAIN_POSITION_CONSTRAINTS` comment: `previously.core.hashing.event_hash` → both versions; "Only event_kind_check stays untranslated" (already false with `event_payload_object_check`, now three more) → "The `CHECK` constraints stay untranslated".
- `storage/schema.py`: `units_hash` comment (v2 over stored `unit.digest`); K-1 comment "`payload = NULL`" now notes `payload_salt = NULL` on a v2 row.
- `hash-chain.md`: unit-seam paragraph (`NOT NULL today`, "Opening the seam later takes ALTER COLUMN…") → past tense, stage 1c opened it; important box: v2 needs `payload_salt = NULL` too; "today's columns can't deliver … Hence no column today" → past tense, column exists, unknown version is a finding; "both halves of the input" → "every part of the input" and "missing 32 random bytes … as well as the content"; "At this point nothing writes version 2" → append writes v2, log holds both, nothing erases, constraints already refuse a half-done erasure; check section: per-unit step and `hash_version` added; "two `try` blocks" → payload in its own `try`, results collected.
- `hash-format.md`: `## Hash versions` (append writes v2, verify picks by `event.hash_version`, where salts/digests live, v1 leaves them NULL); `HASH_VERSION` "meant to be" → "written in"; the "reason" sentence on `seq` → a statement.
- `database-schema.md`: four columns, `content` nullable, two constraints.

`tests/conftest.py` "All six tables" still true (no new table).

## Gates (run at the final tree, each separately)

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 54 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 318 passed in 30.93s =============================  (Required test coverage of 90.0% reached. Total coverage: 97.46%)
make -C docs html                          → build succeeded.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded. (output.txt: no entry other than ok/redirected/ignored)
```

The tutorial run was typed from `uv run pytest` (seed 3672306110, 318 passed in 30.77s), `rootdir:` line left out.

## Files changed

Created: `migrations/versions/0003_hash_version_2.py`, `src/previously/core/chain.py`, `tests/test_chain.py`, `tests/test_migration_0003.py`.
Modified: `src/previously/{cli.py, contract/rows.py, core/append.py, core/hashing.py, core/projection/chronicle.py, core/verify.py, storage/postgres.py, storage/schema.py}`, `tests/{test_append, test_cli, test_hashing, test_projection_derive, test_projection_worker, test_properties, test_rows, test_schema, test_storage, test_verify}.py`, `docs/{explanation/hash-chain.md, reference/cli.md, reference/database-schema.md, reference/hash-format.md, tutorials/record-your-first-event.md}`.
Not committed, mine: `task-2-commit-msg.txt`, this report (git-ignored dir), and a scratch script in the session scratchpad. `git status --short` before staging showed only my files.

## Self-review findings and concerns

1. **`test_the_kind_of_evidence_lands_in_the_payload`** — see expectations, item 3. Needs a ruling.
2. **v1 coverage shrank.** `append` no longer writes v1, so the v1 tombstone skip and the v1 "payload not canonicalizable" branch in `verify.py` (lines 93, 96-97) are no longer reached by any test (they were via `append` before). v1 stays verifiable for good, so a v1 tombstone test and a v1 poisoned-payload test via `_append_version_1` would be worth adding; I did not, to stay near the brief's count. Line 178 (v2 unit without content skipped) is unreached until task 3 erases units.
3. **`_append_version_1`** lives in `tests/test_verify.py` as a private helper; task 3 may want it elsewhere.
4. The v1 "unit without content" guard (mutation 7) is not behaviourally observable; it exists for the `cast`.
5. `prepare` does not refuse a duplicate `seq` itself: the mapping would drop one digest, and the `unit_pkey` would then refuse the insert with an untranslated `IntegrityError`. `append` refuses duplicates earlier in `_check_units`; the docstring says so.
6. The P-1 comments cite `ruling P-1 of the 2026-10-04 stage 1c plan`; the 2026-10-04 stage 1b plan also has a `P-1` (CLAUDE.md), so the plan name is what disambiguates, and the stage 1c ledger is not shipped under `docs/superpowers/sdd/` yet. The reason stands beside each citation.

## Fix round before review (ruling T2-b)

Commit: `ebb68e8 test: version 1 keeps its forgery tests; prepare refuses a duplicate seq` (on top of `4c078ad`, no amend). Ruling T2-a: the change to `test_the_kind_of_evidence_lands_in_the_payload` stands, so nothing was changed there.

### 1. Version 1 keeps its forgery tests

What changed in `tests/test_verify.py`:
- `WRITTEN_IN = pytest.mark.parametrize("version", [1, 2], ids=["version-1", "version-2"])` and `_write(version, storage, events, write_version_1)`. Version 1 is written by hand through the fixture, and version 2 through `append`.
- The following tests are parametrized over both formats. Names and expectations are unchanged; only `append(...)` became `_write(...)`:
  - `test_a_manipulated_payload_fires`
  - `test_a_tombstone_passes`, where the v1 tombstone passes, as today
  - `test_a_broken_linkage_fires`
  - `test_a_manipulated_event_hash_fires`
  - `test_a_first_event_with_a_prev_hash_fires`
  - `test_k1_f2_a_deleted_unit_fires`
  - `test_k1_f3_a_rewritten_source_attribution_fires`
  - `test_k1_a_deleted_source_attribution_fires`
  - `test_w1_a_non_canonicalizable_payload_reports_and_does_not_break_off`, now 2 payloads × 2 formats. It covers "reports and does not break off".
- New v1 twin where the finding differs: `test_w1_a_poisoned_payload_does_not_blind_the_unit_check_in_version_1`. It expects `payload not canonicalizable: $: key 'Note' …` and then `units_hash does not match the units`. The rewritten-unit twin (`test_k1_f1_…_in_version_1`) existed already.
- RED/GREEN: this item is tests over existing code, so there was no RED. The mutations below are the evidence that the new cases read the right path.

Mutation, v1 path only (`_check_version_1`: `_payload_finding(row),` → `None,`):
```
uv run pytest tests/test_verify.py -q -p no:randomly -k "test_a_manipulated_payload_fires" -rA
E       assert [] == [1]
PASSED tests/test_verify.py::test_a_manipulated_payload_fires[version-2]
FAILED tests/test_verify.py::test_a_manipulated_payload_fires[version-1] - as...
1 failed, 1 passed, 47 deselected
```
Reverse (`_check_version_2`: `payload = _payload_finding_v2(row)` → `payload = None`):
```
E       assert [] == [1]
PASSED tests/test_verify.py::test_a_manipulated_payload_fires[version-1]
FAILED tests/test_verify.py::test_a_manipulated_payload_fires[version-2] - as...
1 failed, 1 passed, 47 deselected
```
Both mutations were reverted; `grep -rn MUTATION src tests` is empty.

`verify.py` coverage at the final tree, from the full `pytest --cov` run:
```
src/previously/core/verify.py                      155      1    99%   178
```
Line 178 is the `continue` for a **version 2** unit without content, in `_unit_findings`. Nothing in the tree erases a v2 unit before task 3, and the brief keeps "a tombstone passes" untested until then. **No line in the version 1 path is unreached.** The two `pragma: no cover` branches, the `units_hash` and `unit_digest` `InvalidPayload` cases, keep their written reasons.

### 2. `chain.prepare` refuses a duplicate `seq`

- RED: `test_prepare_refuses_a_seq_that_appears_twice` failed with `Failed: DID NOT RAISE InvalidPayload`.
- GREEN: a `seen` set in the unit loop raises `InvalidPayload("unit {seq}: seq is not unique within the event")`, which is the wording of `append._check_units`. The test matches `^unit 1: seq is not unique within the event$`. The docstring sentence that said `append` takes care of it was rewritten: `prepare` refuses this itself because it has more than one caller, and the docstring says what would happen otherwise.
- Mutation (`if unit.seq in seen:` → `if False:`):
```
E       Failed: DID NOT RAISE InvalidPayload
PASSED tests/test_chain.py::test_prepare_computes_what_the_hash_functions_compute
FAILED tests/test_chain.py::test_prepare_refuses_a_seq_that_appears_twice - F...
1 failed, 1 passed, 5 deselected
```
The mutation was reverted.

### 3. `write_version_1` fixture in `tests/conftest.py`

- The fixture is `write_version_1() -> WriteVersion1`, where `type WriteVersion1 = Callable[[PostgresStorage, Sequence[RawEvent], datetime], list[int]]`. You call it as `write_version_1(storage, events, recorded_at)` and it returns the new ids. It writes a sub-chain on the current tip with the v1 functions and `hash_version=HASH_VERSION_1`. Units are written without digest or salt. It does not look up existing keys, and its docstring says so.
- Annotation, measured on 2026-10-04 with a throwaway `@given` test in `tests/` that took a fixture. The file was deleted afterwards.
  - Annotated through a module-level `type` alias whose value names a `Callable` imported under `TYPE_CHECKING`: `1 passed`, and ruff and pyright both clean.
  - Annotated with `Callable[[int], None]` written out: `NameError: name 'Callable' is not defined` at collection.
  - A runtime `from collections.abc import Callable` is not a way out either: ruff reports `TC003` for it, measured with `ruff check --stdin-filename tests/…`.

  So a test module that takes the fixture declares the same alias. `test_verify.py` does, and pyright checks that the alias and the fixture agree. The fixture's docstring records this.
- `_append_version_1` was removed from `test_verify.py`. Its four users take the fixture.

### Test count and gates

Test count: **330**, up from 318:
- 8 tests gained a second format: +8.
- The W1 parametrized test doubled: +2.
- The v1 poisoned-payload twin: +1.
- The duplicate-`seq` test: +1.

The tutorial block was retyped from a real `uv run pytest` run: seed 869852770, `330 passed in 30.49s`, with the `rootdir:` line left out.

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 54 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 330 passed in 33.10s =============================  (Total coverage: 97.78%)
make -C docs html                          → build succeeded.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded. (output.txt: no entry other than ok/redirected/ignored)
```

`git status --short` before staging showed only the five files of this round: the tutorial, `chain.py`, `conftest.py`, `test_chain.py` and `test_verify.py`.

Remaining concerns: self-review items 2, 3 and 5 are closed. Item 4 stands: the v1 content guard is there for the `cast` and cannot be observed. Line 178 of `verify.py` stays unreached until task 3.

## Fix round 1

Commit `30f7768 test: the linkage of a row in an unknown hash version is checked`, on top of `ebb68e8`, no amend.

### I-1: linkage is checked for an unknown version

- **Change:** `test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on` now appends three events.
  - Row 2 gets `hash_version = 3, prev_hash = b"\xff"*32`.
  - Row 3 gets a forged payload.
  - Expected findings, exactly: `[Finding(2, "prev_hash does not match the predecessor"), Finding(2, "hash_version 3 is not known"), Finding(3, "payload_hash does not match the payload")]`.
  - The docstring says why the unknown version moved off the first row.
- **Covering tests:** `uv run pytest tests/test_verify.py -q -k unknown_hash_version` → `1 passed`.
- **Mutation:** an early return for an unknown version, placed in `_check_event` before the linkage block (`if row.hash_version not in _CHECKS: return [Finding(... not known)]`).
  - Command: `uv run pytest tests/test_verify.py -q -p no:randomly -k "unknown_hash_version or test_a_broken_linkage_fires" -rA`.
  - Output:
    ```
    E       At index 0 diff: Finding(event_id=2, reason='hash_version 3 is not known') != Finding(event_id=2, reason='prev_hash does not match the predecessor')
    PASSED tests/test_verify.py::test_a_broken_linkage_fires[version-1]
    PASSED tests/test_verify.py::test_a_broken_linkage_fires[version-2]
    FAILED tests/test_verify.py::test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on
    1 failed, 2 passed, 46 deselected
    ```
  - Result: the target test went red, and both linkage tests (the controls) stayed green.
  - The mutation is reverted.

### M-6: the direction the brief asked for

- **Mutation:** line 52 of `src/previously/storage/schema.py`, `Column("payload_salt", LargeBinary),`, replaced by a comment.
- **Command:** `uv run pytest tests/test_schema.py -q -p no:randomly -k "declared_columns or test_kind_is_restricted" -rA`.
- **Output:**
  ```
  E           AssertionError: event
  E             Left contains 1 more item:
  E             {'payload_salt': True}
  PASSED tests/test_schema.py::test_kind_is_restricted
  ```
- **Result:** `test_the_declared_columns_match_the_migrated_database` turns red when a column is in the database but missing from `schema.py`. `test_kind_is_restricted` is the control and stayed green. The test already turned red in the other direction, as measured in step 1, so this is no finding and the test needs no change.
- The mutation is reverted, and `git diff --stat` was empty afterward.

### M-1: downgrade refusal for units without content

- **Change:** `tests/test_migration_0003.py`, after the first refusal, now runs `UPDATE unit SET content = NULL, salt = NULL WHERE event_id = 1`. `speaker`, `start_ms` and `end_ms` were already `NULL`, which `unit_tombstone_check` requires. It then expects the full sentence with both reasons, joined by `; `. The database is still at `0003_hash_version_2` afterward.
- **Covering tests:** `uv run pytest tests/test_migration_0003.py -q` → `1 passed`.
- **Mutation:** the unit check in `downgrade()` short-circuited with `if False and …`.
  ```
  E               AssertionError: assert 'refusing to ...is would drop' == 'refusing to ...OT NULL again'
  E                 -  would drop; the log holds units without content, which cannot be NOT NULL again
  ```
  The test went red. The mutation is reverted.

### M-3: a `Protocol` instead of `Callable[..., bytes]`

- **Change:** `_EventHash(Protocol)` in `verify.py` has a keyword-only `__call__` with the nine parameters that `event_hash` and `event_hash_v2` share. `_event_hash_finding(…, compute: _EventHash)` uses it. `datetime` is imported under `TYPE_CHECKING`.
- **Measurement:** `units_digest=` at the call site was misspelled as `unit_digest=`. `uv run pyright src/previously/core/verify.py` then reported `Argument missing for parameter "units_digest"` and `No parameter named "unit_digest"`, 3 errors. The misspelling is reverted.

### M-4: two prose slips on `hash-chain.md`

`plone-doc-style:author` was invoked before the edit.
- Line 303 now reads: "The database already holds any future erasure to that rule: it refuses …".
- Line 346 now reads: "`tests/test_verify.py` holds that separation down, and it had to, because reading the code didn't: when the payload and the units were once recomputed inside one shared `try` block, every test stayed green."

### Count and gates

- **Test count:** 330, unchanged. No test was added; existing tests were extended. The tutorial still says `330 passed`, `test_docs_typed_output` holds it, and no retype was needed.
- **Covering tests:** `uv run pytest tests/test_verify.py tests/test_migration_0003.py tests/test_schema.py -q` → `67 passed in 13.79s`.
- **`verify.py` coverage:** `158 1 99% 180`. The one missed line is still the `continue` for a version 2 unit without content; it moved from 178 to 180 because of the Protocol and the imports.

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 54 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 330 passed in 31.01s =============================  (Total coverage: 97.78%)
make -C docs html                          → build succeeded.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded. (output.txt: no entry other than ok/redirected/ignored)
```

`git status --short` before staging showed only the four files of this round.
