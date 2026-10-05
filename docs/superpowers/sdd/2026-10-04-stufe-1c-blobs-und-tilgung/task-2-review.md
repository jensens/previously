# Task 2 review — hash format v2 end to end (72a0044..ebb68e8)

Method: the diff file was read in three passes (source, migration and schema; tests; documentation).
No changed file was read separately.
Outside the diff, one focused check per named risk:
- *Every reader of `UnitRow.content` handles `None`*: `grep -rn '\.content\b' src/`. The hits outside the diff (`cli.py:433`, `postgres.py:441`, `postgres.py:565`) are `ChronicleRow.content`, not `UnitRow`. The `UnitRow` readers are `cli.py:371`, `chronicle.py:44`, `verify.py:115` and `verify.py:177`, and all four handle `None`.
- *Every `EventRow` built or read carries the new fields where it matters*: `grep -rn 'EventRow('`. In `src/` the only builders are `chain.link` (explicit `HASH_VERSION_2` and salt) and `postgres.read` (both fields read back). `insert_event` writes `hash_version=row.hash_version` explicitly, so it never goes through the column default. The test builders rely on the default `1` without a salt, which is correct for what they build.
- *Migration and `schema.py` agree*: compared in the diff. Columns, nullability, `server_default`, both constraint names and the SQL text are identical. `test_the_declared_columns_match_the_migrated_database` holds names and `NOT NULL` against the database, but not types.
- *Linkage checked for an unknown version*: read `verify.py:290-322` together with the test at `tests/test_verify.py:473`. See I-1.
- *`HASH_VERSION` is read by nothing*: grep over `src tests migrations`. True, so the new comment in `hashing.py` holds.

No test was run and nothing in the tree was mutated.

### Spec Compliance

- ✅ Spec compliant, with one gap that sits under Important (I-1) rather than under Missing: the brief's sentence "Die Kettenverknüpfung (prev_hash) wird trotzdem geprüft" is implemented, but no test reads it.
  - Interfaces: `EventRow.hash_version`/`payload_salt` and `UnitRow.content`/`digest`/`salt` sit at the end with the specified defaults. `PreparedUnit`, `Prepared`, `prepare` and `link` match the brief field for field and in signature. The `LogStore` signatures are unchanged.
  - Schema: all four columns, `content` nullable, both `CHECK`s with the exact SQL and names, and no `CHECK` on `hash_version`. The migration matches `schema.py`. `downgrade()` checks before it drops anything and raises `CommandError` with one sentence. The report says the real CLI was measured printing `FAILED: …` without a traceback.
  - Step 1: all six tests are present.
  - Step 2: both round-trip tests are present. `insert_event` writes `hash_version` explicitly.
  - Step 3: all six tests are present, plus the duplicate-`seq` test from ruling T2-b. The salt mutation was reported red with a green control.
  - Step 4: `_prepare` returns `(RawEvent, Prepared)`. The checks keep their order. The retry loop and both `except` branches are verbatim; only the row-building lines changed, plus `prev = row.hash`. The docstring says the salts are drawn once.
  - Step 5: all eight named tests are present, plus the K1 v1 twin and `p8`. The three plan mutations were reported red with green controls. Both wordings are exact: `unit <seq> does not match its digest` and `hash_version <n> is not known`.
  - Step 6: all three readers are handled, `test_chronicle_derives_no_row_for_a_unit_without_content` is present, and the projection version stays 1.
  - Step 7: the `hashing.py` docstring and the `schema.py` comments are updated, and `conftest.py`'s "All six tables" still holds (six tables in `metadata`).
  - Step 8: both pages are updated.
  - Ruling P-1 is applied at all four forged tombstones, with the reason beside each citation.
  - Ruling T2-a is applied (`test_append.py:249`).
  - Ruling T2-b, item 1: eight tests are parametrized over both formats and the W1 v1 twin is added. Item 2: the duplicate-`seq` refusal is in `prepare`. Item 3: `write_version_1` is a fixture in `conftest.py`.
  - The rulings themselves look right to me. P-1 changes the arrangement, not the claim. T2-a keeps the property and lets the function follow the format, and `test_append_writes_version_2_…` pins the format beside it.
  - The departures are judged on their merits. Canonicalizing the payload first in `prepare` and `_payload_finding_v2` is justified, keeps the documented `$.text` path, and has a test that goes red without it. The extra pages (`cli.md`, `hash-chain.md`) are the documentation following the code, which `CLAUDE.md` demands.
- ⚠️ Cannot verify from the diff:
  - The commit-message trailers of `4c078ad` and `ebb68e8` (the diff package holds subjects only, and I was told not to run git).
  - The per-file counts in the typed tutorial run (unguarded by `test_docs_typed_output.py`; only `330 passed` is held).
  - The mutation that the brief's step 1 asks for: remove `payload_salt` from `schema.py`, then run. The report measured the opposite direction instead: columns declared in `schema.py` before the migration existed. Both directions break a set equality, so I expect red, but the brief's own measurement is not on record.

### Strengths

- `verify` stays readable despite doubling its scope. The version dispatch through `_CHECKS` makes "compute the row in the version it names and in no other" structural rather than an `if/elif` that could grow a fall-through. Mutation 4 in the report shows what the alternative costs: a row reading 3 that is hashed as 2 produced no finding at all.
- `_event_hash_finding` is shared by both versions, which keeps the "stored digests, not recomputed ones" argument in one place.
- Missing salts and digests become findings at the digest they belong to, never exceptions, and `test_v2_a_missing_salt_or_digest_fires_and_does_not_break_off` holds that down across two rows.
- The canonical-first departure is argued in the comment, carries a date, and is pinned by a tightened assertion (`$: key 'Note'`) with a mutation that turned it red. That is exactly the "comment is a claim" discipline.
- `test_the_declared_columns_match_the_migrated_database` closes a real, pre-existing blind spot between `schema.py` and the migrations, for all six tables and not only for this migration.
- The T2-b round is solid. The version 1 twins run the version 1 path: the fixture writes `hash_version=HASH_VERSION_1` with the v1 functions. The pair of mutations (v1 payload check off, then v2 payload check off) shows each half of the parametrization reading its own path.
- Comments and pages were turned over past the brief's list, and each turnover is correct at this commit. Examples are the `append.py` module docstring ("a duplicate `hash` can only come from such a pair"), the `postgres.py` remark "only `event_kind_check` stays untranslated", which was already false, and the past-tense rewrite of `hash-chain.md`. No page or comment claims that an erasure exists in this tree.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

**I-1. "The linkage is checked for an unknown version too" has no test that can fail.**
`src/previously/core/verify.py:290-322` states it in the docstring of `_check_event`, the brief requires it, and the docstring of the named test at `tests/test_verify.py:473` claims it: "The linkage is checked all the same, and so is the next row."
The test cannot see it.
The unknown version sits on row 1, which is the first row and has `prev_hash = NULL`, so moving the linkage block below an early `return` for an unknown version leaves every test green.
"And so is the next row" *is* held, by the exact finding list on row 2.
Under `CLAUDE.md` ("An assurance needs a test measured to fail"), the linkage half is a comment, not an assurance, and the test docstring claims coverage it does not have.

Fix: put the unknown version on a row whose linkage is also forged, and expect both findings. For example, set `hash_version = 3` and `prev_hash = '\xff…'` on row 2 of three, expect `prev_hash does not match the predecessor` and `hash_version 3 is not known` there, and keep a separate forgery on row 3. Then measure the mutation: linkage moved into the known-version branch → red. Alternatively, narrow the test docstring and add a separate test.

#### Minor (Nice to Have)

**M-1. The `downgrade()` refusal on units without content is untested.**
See `migrations/versions/0003_hash_version_2.py:67-68`.
`tests/test_migration_0003.py` reaches only the `hash_version = 2` branch.
The second branch, and the joined two-reason sentence, would go through unnoticed if the `EXISTS` query were wrong.
Nothing in this tree can produce a unit without content except raw SQL, and the brief only named the v2 case, so this is Minor.
It is a cheap addition to the same container test: a raw `UPDATE unit SET content = NULL, salt = NULL` before the second downgrade, with both reasons in the expected string.

**M-2. The v2 unit-tombstone skip is unreached and has no test.**
See `src/previously/core/verify.py:177-178` (the report's "line 178").
The docstring of `_unit_findings` and `hash-chain.md:309` ("each unit that has content") state the skip.
Deleting the `continue` would call `unit_digest(content=None)`, which yields a mismatch finding, and no test would notice.
The report defers this to task 3, which builds unit erasure.
A raw-SQL v2 unit tombstone with `verify(...) == []` would cost five lines now; at the latest, task 3 must cover it.

**M-3. `_event_hash_finding` takes `compute: Callable[..., bytes]`.**
See `src/previously/core/verify.py:222`.
`...` switches off pyright's checking of the nine keyword arguments at both call sites.
`event_hash` and `event_hash_v2` share one signature, so a `Protocol` with that `__call__`, or `Callable[[…], bytes]` via a small typed alias, would keep strict mode doing its job.

**M-4. Two prose slips in `docs/explanation/hash-chain.md`.**
- Line 303: "The database already holds an erasure to that" does not parse; "holds an erasure to that standard" is meant, or more plainly "The database already enforces half of that:".
- Line 346: "when the two blocks were merged back into one" now refers back to a sentence (line 344) that no longer speaks of two `try` blocks. It says "the payload inside a `try` block of its own". The antecedent is gone; "when the payload's block was widened to cover the units" would match the rewritten sentence.

**M-5. No reference page lists the new finding `unit <seq> does not match its digest`.**
`hash_version <n> is not known` appears in `hash-format.md:47`.
The per-unit finding is a contractual wording (global constraints) that appears on no reference page.
The brief's step 8 did not ask for it, and the reference pages never enumerated the chain findings, so this is a gap to carry, not a defect of this task.

**M-6. The direction of the step 1 measurement.**
See the ⚠️ item above.
The brief asked for "take `payload_salt` out of `schema.py`" (database has more than declared), and the report measured "declared before migrated" (declared has more).
Both break the equality, but the requested one is not on record.

### Assessment

**Task quality:** Needs fixes

**Reasoning:** The implementation matches the brief and the rulings, is carefully built and correctly documented. One explicit assurance of this task, that the linkage is checked on a row with an unknown version, rests on a test that cannot fail and whose docstring claims otherwise (I-1). That is a small, local fix.
