# Task 1 review: form and fold (`core/assertion.py`)

Verdict: Needs fixes. Measured: 122 tests pass in `tests/test_assertion.py`. Not re-run: coverage, pyright, the other gates, the mutations.

## Spec compliance
- Payload contract (decision 2), keys, dates, `payload_of`/`parse_statement` round trip: OK (assertion.py:228-380).
- Reference grammar (decision 3): OK with a note on circle names, see Minor 3.
- Fold: not compliant with spec section 8, "falls back to the next standing version" (assertion.py:~443, Important 2).
- `pending()` contradicts ruling F-1 (assertion.py:~394, Important 1).
- A new suppression is forbidden by the constraints (assertion.py:259, Important 3).
- The tutorial block is not one run (Important 4).

## Strengths
- Pure module, `cast` instead of ignores, problem sentences really quote nothing (probed `address:`, `name:`, `circle:` cases).
- `_date` guards `fromisoformat` with an ASCII regex, so `20260203` and `2026-W05-1` are refused.
- U+2028/2029 are in the forbidden set (probed: both refused).
- A rejection that names a rejection, a dangling `subject`, a version of the wrong kind, an approval in another thread and a `subject` pointing at a rejection are all skipped (probed and parametrized tests).
- Rejecting a direct version only enters `rejected`; `_candidates` considers open versions only, so it is harmless.

## Findings listed as requested

### Named risk 1: the Hypothesis property
- The expected winner is computed from the rows via `parse_statement` and plain list logic, not via `Thread`. That is independent enough.
- It would catch "open beats direct when newer": `expected = direct[-1]`, and ops can place an open version after a direct one (min 1 step, max 14).
- It mirrors fold's semantics, not the contract, on two points; see Important 5.
- Its `pending` branch asserts the pre-F-1 behavior (`unanswered` including the winner, test_assertion.py ~658-663). It has to change with F-1.

### Named risk 2: fold edge cases (probed with `uv run python`)
- Approval of an erased proposal: skipped (fine).
- Approval in another thread: skipped (fine).
- Rejection of a direct version: harmless (fine).
- `subject` pointing at a rejection: skipped (fine).
- Approving twice: a second direct version is appended and wins (`double approve versions [2,3,4]`, winner 4).
- Approving after rejection: accepted, versions `[2,4]`, `rejected={2}`.
- Both are rejected on the write path (plan decision 5), but fold, which also runs over old or hand-made data, accepts them silently. See Important 5.
- First version erased, later ones stand: `fold` returns `{}` (probed). Spec section 8 wants the fallback.
  - Recommendation: keep the thread alive. Key the draft by `subject`, create it lazily from the first standing version and take `kind` from it.
  - Reason 1: the cascade erases a later version only when its own sources are hit, and a later version may cite other sources than the first.
  - Reason 2: dropping the whole thread silently loses a standing, correctly sourced fact.
  - Cost: `approves`/`of` pointing at the erased first version are already skipped. A later version is a full statement ("everything that holds after it"), so nothing is lost.
  - Add a test for it.

### Named risk 3: form strictness
- Extra keys are refused by `frozenset(payload) != keys` (assertion.py:~343).
  - For `verify` over old data this is a reason to refuse, not to be lenient: the form is hashed in for good and there is no old data yet.
  - It means a later new key needs a form version. Acceptable now; note it in the docs.
- Circle names use `_is_label` (1..200 chars, non-blank, no Cc/Cf/2028/2029). The policy only requires non-empty (`policy.py:259 _check_text`), so there is no stricter grammar to follow. A policy circle named with control characters or over 200 characters could never be referenced. Minor 3.
- Problem sentences quote nothing: confirmed. One sentence is mislabeled, see Minor 1.

### Named risk 4: the tutorial block (b)
- Progress lines sum to exactly 1744 and every percentage equals `int(100*cum/N)` (computed).
- But line 126 reads `tests/test_docs_typed_output.py F  [ 77%]`, followed by `1744 passed`. A failed test inside a block that claims "passed" is not one run. It confirms the disclosure.
- Retype the block from one single green run, last.

## Issues

### Critical
None.

### Important
1. `Thread.pending()` includes the winner when there is no direct version (assertion.py `pending`, docstring says "the winner among them included"; test ~663). Ruling F-1 says never.
   - Fix: with no direct version, return candidates minus `winner()`. With a direct version, keep the current logic.
   - Update the docstring, the brief's interface comment and the property.
2. A thread whose first version is erased is dropped (assertion.py `fold`, the `draft is None` branch). Fix as recommended in risk 2.
3. New `# noqa: C901` on `_sources_problem` (assertion.py:259).
   - Forbidden by constraints and CLAUDE.md, and "one check per rule" is not a stated false positive.
   - If it stays, it also has to appear in CLAUDE.md's list. It should not stay.
   - Fix: split into `_source_problem(item)` (one entry) and `_units_problem(units)`.
4. Tutorial block (b) is a mix of runs, with an `F` in it. Retype from one run after the tree stops moving.
5. Fold accepts a second approval and an approval after rejection as new direct versions.
   - Decide and test it explicitly: either skip such an approval in fold (`proposal.id in draft.approved` or in `draft.rejected` means skip), or document that fold is lenient and `verify` reports it.
   - Skipping is consistent with the docstring ("names nothing standing of the matching kind"). The property currently encodes the lenient behavior, so a tightening has to be mirrored there.

### Minor
1. `_address_problem` returns "needs a part before and after the @" when `_has_forbidden_character` fires with both parts present (assertion.py ~120). The sentence is wrong for that case. Use a separate sentence.
2. `Statement` carries `of`, `subject` and `approves` as `int | None` while `fold` uses `cast("int", statement.of)`. Parse already guarantees it for rejections. Acceptable, but a `RejectionBody` would remove the casts.
3. Circle names: document that they are stricter than the policy, or accept the policy's looser rule.
4. `pending` and `_direct_winner` use `self.versions.index(direct)` and `v in newer` (dataclass equality on tuples, O(n^2)). Fine at pilot size; use ids if the 5 000-item measurement shows a cost.

## Assessment
Needs fixes: Important 1 to 5. No Critical issue; the module is otherwise careful and well tested. Re-review after the fix round should re-run all six gates.
