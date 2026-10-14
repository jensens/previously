# Task 3 report: approval classes (`core/classes.py`)

Commit 516ba45 (one commit). Status: DONE with concerns below.

## Built
- `core/classes.py`: `ApprovalClass`, `ClassRefused`, `class_problem`, `class_payload`, `Classes` (`by_name`, `states`, `level`), `read_classes`, `set_class`, `HitRate`, `hit_rates`, `sample`.
- `core/action.py`: `APPROVAL_CLASS`, in `KNOWN_ACTIONS` (six names). `core/verify.py`: branch via `_statement_finding("approval_class", ...)`, so a broken form or units give `approval_class event ...`.
- Pinned tests and pages updated: `tests/test_action.py`, `tests/test_docs_references.py`, `docs/reference/cli.md` (unknown action row), `docs/reference/policy-and-model-calls.md`. `tests/test_access.py` only asserts membership, left alone. Tutorial test block retyped from one green run (2439 passed; rootdir line left out as the page says).
- No new reference page for the payload: left for Task 7 (the policy page names `approval_class` in one clause).

## Deviations
1. `level(...)` keyword is `type_name`, not `type`: ruff A002 (builtin shadowing) fails on `type`, and no suppression is allowed. Task 4 must call `level(type_name=...)`.
2. `hit_rates` counts a version by the level it was **written** (`claim.responsibility == TRANSITIVE`), not by `level_of`: with `level_of`, versions under a class revoked with `demote` would drop out of `total`, and the record of how the class fared would vanish with the class. `level_of` is used in a test to show such a version counts as open in the fold.
3. `corrected` also counts a version the operator **rejected** (`thread.rejected`), next to a later direct version and a retraction (a retraction is a later direct version). `confirmed` is checked first.
4. `sample` resolves the class name through `graph.classes[under].id == class_id` (all events of a name share the newest id), so it needs no `Classes`. Unknown `class_id` or `count <= 0` gives `()`.
5. `valid.from >= valid.until` is a form fault (extra check). A revocation (`revoked=True`) is not held against the vocabulary, so a class stays revocable after a kind it names was retired. Test pins it.
6. `by_name` keeps revoked classes (newest event per name); `level` skips revoked ones.

## Tests (`tests/test_classes.py`, 61 tests, 5 db-backed groups)
Form round trip and 20 single form faults; every GATE type refused in the form and in `set_class`; level over/at/under threshold (80/100/79/None, zero), window edges (start included, end excluded, half-open), other author/kind/type, revoked, highest threshold then oldest event, GATE type hand-forced into `Classes` stays open; fold states (older events see the newest state, revocation reaches the older event, re-enabling makes them active again), `at`, erased event, vocabulary refusals (unknown, wrong declares, retired but revocable); `verify` finding for a broken `approval_class` with a green control; hit rate (confirmed, corrected by later direct, retraction, rejection, standing, sum, demote, zero, later transitive overtakes nothing); sample (distinct, in class, sorted, fewer than asked, SystemRandom).

## Mutations (changed -> red, restored -> green)
- level without the GATE_TYPES check -> 4 red (`test_a_built_in_type_is_open_even_if_an_event_names_it[...]`, the by-hand log case).
- form without the GATE_TYPES check -> red (`test_a_built_in_type_is_a_form_fault[...]`).
- `>=` to `>` on the threshold -> red (`test_a_threshold_of_zero_takes_every_confidence`, and the 80 boundary).
- states only for the newest event -> red (`test_every_event_of_a_name_sees_the_newest_state`).
- Control after each restore: 60 passed (61 after the last test added).

## Gates
ruff check: All checks passed. ruff format --check: 133 files formatted. pyright: 0 errors. lint-imports: 9 kept, 0 broken. pytest: 2439 passed (tutorial block retyped; `test_docs_typed_output` green). Docs: html built, vale 0 errors/0 warnings/0 suggestions in 46 files, linkcheck "build succeeded". Coverage of `classes.py`: 99%; line 307 (payload None / wrong action in `read_classes`) is unreachable through `log.actions`, kept as the same defense `read_vocabulary` has.

## Concerns
- Deviation 1 changes the interface text of the brief (`type` -> `type_name`).
- The `T201` count and other Phase 1 moving numbers are untouched (no `print` added).
- Full pytest is ~4 minutes; the first full run before the last test addition showed the tutorial test red until retyped, as expected.
