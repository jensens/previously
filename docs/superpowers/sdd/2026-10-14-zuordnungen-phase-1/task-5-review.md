# Task 5 review: the command line

Spec: ✅ (all contractual wordings, rulings and named risks hold)
Quality: Changes requested (one Important documentation finding)

## Verified
- T201: `ruff ... --statistics` gives 96 on cli.py; pyproject.toml says "ninety-six" twice; the narrative lists 15 new prints (3 shared + 2 + 5 listing/status + 5 classes), which is 81 + 15 = 96.
- Existing tests: `git diff` of tests/test_cli.py has no removed line (908 insertions only), so the unit-5 approve/reject tests are unedited.
- approve/reject for obligations and decisions: `_proposal_of` and the old statement build are untouched. The graph is read only when some id is not a named obligation or decision. A mixed call raises at `_cmd_approve` before `check_claims`, the preview and the question, so nothing is written (test: `test_one_approval_does_not_mix...`, count unchanged, controls green).
- Refusals before writing: `_stated` runs `check_claims` before the preview and the question; `answer` checks the candidate before; `classes` calls `class_refusal` before the question; `reject` calls `check_statements` before the preview. The write path rechecks under the tip (races only).
- Wordings: help texts of the eight new commands equal the table (pinned by a test); `assertion <id>`, `approval class event <id>` printed as specified; `PREVIOUSLY_LANGUAGE` default `en`, validated, fallback mark ` (<tag>)`, `display_label` in core/vocabulary.py.
- `status` prints `objections`, `questions`, `proposals` with counts; `triage` orders objection, question, proposal.
- Carry-over: relation to an erased entity shows `ID (erased)`, retracted shows `ID (retracted)`, and the relation stays listed.
- Deviations judged on the merits: all six acceptable. The `answer` pre-check pinned equal to the write path's sentence by a test is sound. `class_refusal` shares `_standing_kinds` with `set_class` (no duplicated logic). `--count` as PreviouslyError is consistent with the doc test. `(none stands)` is reasonable but see Minor 1.

## Findings

### Important
1. docs/reference/cli.md:6 (stale claim). The page still says "It has twenty-five subcommands" and lists 25 names. `COMMANDS` now has 34 entries. Eight of the nine missing ones are this task's (`entity`, `relate`, `entities`, `relations`, `classes`, `triage`, `answer`, `status`); `vocabulary` was already missing from the list after task 1. CLAUDE.md: a page that lags is read as current. No gate catches it. Fix: retype the count and list (or drop the count), in the same change.

### Minor
1. cli.md `entities` and `relations` section documents `(erased)` and `(retracted)` ends but not `ID (none stands)`, which `_end_text` (cli.py) prints when an entity has no winner (for example only a pending proposal). Add one sentence.
2. `relate TYPE --from A --to B --source S --retract` without `--subject` writes a first version that is already retracted (same for `entity --state retracted`). Harmless and consistent with the write path, but the help says "with --subject"; either refuse or accept knowingly.
3. Listings show the label, not the identifier, in the type column. `--type` takes the identifier, so a script that reads a listing cannot feed it back without `entity N`. Accepted as reported; worth one sentence in cli.md (the page of an entity shows both).
4. cli.md `triage` paragraph uses "he works through it"; the rest of the page uses neutral wording ("the operator"). Cosmetic.

### ⚠️ Not verified / judgement
- I did not re-run the suite or the mutations; the report's 14 mutations are claims. I read the tests for the three named risks (mixed approve, answer, contractual help) and they have controls.
- `approve N` on a question id builds an approval that keeps `candidates`; I did not run it to see which sentence the write path gives (graph_write.py:354 suggests a refusal). Not covered by a test in this task.
- "The same day" in the pyproject T201 narrative: I did not check the date it refers to.
