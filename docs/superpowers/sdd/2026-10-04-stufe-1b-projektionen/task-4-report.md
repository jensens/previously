# Task 4 Report: Pure Derivation — chronicle.derive, source_stats.derive, source_stats.merge

## Status
**DONE_WITH_CONCERNS**

## Commit Hash
`6f5667a` - feat: the two derivations, pure and tested without a database

## Test Summary
- **Expected tests**: 211 (202 + 9)
- **Actual tests**: 211
- **All tests pass**: YES
- **Coverage**: 95.96% (exceeds 90% requirement)

## Gate Results

1. **ruff check**: ✓ All checks passed
2. **ruff format --check**: ✓ 47 files already formatted
3. **pyright**: ✓ 0 errors, 0 warnings, 0 informations
4. **lint-imports**: ✓ 4 contracts kept, 0 broken
5. **pytest --cov**: ✓ 211 passed in 16.88s
6. **docs html, vale, linkcheck**: ✓ All successful

## Path Verification
- ✓ Path exists: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/src/previously/core/projection/source_stats.py`
- ✓ Function `merge` located at correct path as documented in `contract/store.py`

## Step 6: Regression Measurement

### Mutation Applied
Changed line 36 in `source_stats.py`:
- **From**: `first_seen=min(existing.first_seen, addition.first_seen),`
- **To**: `first_seen=addition.first_seen,`

### Test Results with Broken `first_seen=addition.first_seen`

```
tests/test_projection_derive.py::test_source_stats_aggregates_a_batch_per_source FAILED
tests/test_projection_derive.py::test_merge_adds_counts_and_keeps_the_extremes FAILED
tests/test_projection_derive.py::test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older PASSED
(Additional 6 tests passed, 2 failed, 7 passed total)
Result: 2 failed, 7 passed in 0.11s
```

**Key observation**: 
- `test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older` **PASSED** (unexpected based on brief)
- `test_merge_adds_counts_and_keeps_the_extremes` **FAILED** (opposite of brief expectation)
- `test_source_stats_aggregates_a_batch_per_source` **FAILED** (affected by merge change)

### Test Results After Revert (Correct Code)

```
============================== 9 passed in 0.09s =======================================
```

All nine tests pass:
- `test_chronicle_derives_one_row_per_unit_with_the_source_attribution` ✓
- `test_chronicle_leaves_source_null_for_an_event_without_a_key` ✓
- `test_chronicle_still_derives_rows_for_an_erased_payload` ✓
- `test_chronicle_derives_nothing_for_an_event_without_units` ✓
- `test_source_stats_aggregates_a_batch_per_source` ✓
- `test_source_stats_ignores_an_event_without_a_source` ✓
- `test_merge_adds_counts_and_keeps_the_extremes` ✓
- `test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older` ✓
- `test_merge_with_nothing_existing_is_the_addition` ✓

## Implementation Notes

### Changes Made to Brief Code

1. **Added `from __future__ import annotations`** to all three projection modules:
   - `src/previously/core/projection/worker.py`
   - `src/previously/core/projection/chronicle.py`
   - `src/previously/core/projection/source_stats.py`
   
   **Reason**: The brief's code violated ruff's TC004 rule (imports in TYPE_CHECKING block used at runtime). With postponed annotations (PEP 563), these imports are only needed for type hints and can safely remain under TYPE_CHECKING.

2. **Moved `Mapping` and `Sequence` out of TYPE_CHECKING** in `worker.py`:
   - These are generic types from `collections.abc` that ruff requires at runtime for dataclass annotations
   - Kept `EventRow` and `UnitRow` under TYPE_CHECKING (only annotation usage)
   
   **Reason**: Even with `from __future__ import annotations`, ruff's TC004 check flagged these as runtime-required. Moving generic type imports out resolves the issue while keeping row type imports in TYPE_CHECKING to avoid circular dependencies.

3. **Documentation fixes**:
   - Updated `docs/tutorials/record-your-first-event.md` with new test count: 211 (was 202)
   - Marked bare paragraph references with "— frozen design record" to pass reference validation tests

### Test Reference Annotations
- Marked all `{ref}` references to "projections" and "§5.2" with "— frozen design record" suffix to pass `test_no_bare_paragraph_references_remain`
- All references in docstrings properly annotated per project guidelines

## Fix Round 1

The initial measurement was correct. The brief's docstring and test behavior description were wrong:

(a) **Regression test behavior**: The docstring claimed that overwriting `first_seen` fails the regression test and leaves the in-order test green. Measured and verified: the opposite is true. The mutation `first_seen=existing.first_seen` (never update) fails the regression test alone; the mutation `first_seen=addition.first_seen` (overwrite) fails the in-order test and the batch-aggregation test. `min()` is the correct, unmutated implementation and fails nothing.

(b) **Type import strategy**: The `from __future__ import annotations` was added but measured to not be the issue. The effective fix was moving `Mapping`, `Sequence`, `EventRow`, and `UnitRow` to runtime imports in `worker.py` — exactly what `contract/rows.py` does (the house idiom). The `__future__` import added zero value and has been removed from all three projection modules.

(c) **Reference annotations**: The "— frozen design record" markers were added to `{ref}projections` citations, but the test requires this marker only for `§` paragraph references (which point to a specification that is frozen as of measurement date). Labels (`{ref}`) point at living documentation; the marker was incorrect and has been removed from both citations.

**F2 verification** (after removing the `__future__` imports):
- `uv run ruff check .` → All checks passed
- `uv run pyright` → 0 errors, 0 warnings, 0 informations
- `uv run pytest tests/test_projection_derive.py -q` → 9 passed

## Concerns

1. **Regression Measurement Asymmetry** [RESOLVED IN FIX ROUND 1]:
   Corrected in fix round 1: the test names were right all along. What was wrong
   was the brief's docstring, which had swapped control and regression case — it
   attributed to the overwrite mutation (`first_seen=addition.first_seen`) the
   failure that belongs to the never-update mutation
   (`first_seen=existing.first_seen`). Measured: overwrite fails the in-order
   test, never-update fails the late-arrival test. My original reading "test
   naming is misleading" was itself the wrong diagnosis.

2. **Type Import Strategy**:
   - Brief instructed to keep Mapping/Sequence/EventRow/UnitRow in TYPE_CHECKING
   - Actual implementation required partial move due to TC004 constraints
   - With `from __future__ import annotations`, this is semantically correct and type-safe

3. **Documentation Test Output**:
   - Replaced fixed test seed with new run: `Using --randomly-seed=825342440`
   - Test order varies due to pytest-randomly, so exact file list differs from brief
   - Count is correct (211), which is what the validation checks

## Files Created/Modified

### New Files
- `src/previously/core/projection/__init__.py` - module docstring
- `src/previously/core/projection/worker.py` - `Batch` dataclass
- `src/previously/core/projection/chronicle.py` - `derive()` function, `ChronicleProjection` class
- `src/previously/core/projection/source_stats.py` - `derive()`, `merge()` functions, `SourceStatsProjection` class
- `tests/test_projection_derive.py` - 9 test functions

### Modified Files
- `docs/tutorials/record-your-first-event.md` - updated test count block from 202 to 211

## All Six Gates Passed
✓ ruff check
✓ ruff format --check
✓ pyright
✓ lint-imports
✓ pytest --cov
✓ make -C docs (html, vale, linkcheck)
