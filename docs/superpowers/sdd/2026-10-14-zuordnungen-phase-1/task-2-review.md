# Task 2 review: the graph model (`core/graph.py`)

Base `5432bc6`, head `99a67dd`. Read: brief, context (decisions 2–6, 10, 12, Global Constraints), report, the whole diff, plus Z §6.3–§7.6 for the named risk "proposals in `reaches`".
The suite was not re-run. Two focused probes ran from the scratchpad, read-only, against the tree (results quoted below).

**Spec: ✅** (no Missing, no Misunderstood. Extras judged below, one Minor among them)
**Quality: Changes requested** (1 Important, 6 Minor)

---

## Part 1: spec compliance

Checked key by key against decisions 3 and 4 and the controller rulings:

- The common keys, the entity keys, and the relation keys match exactly (`_COMMON_KEYS`, `_ENTITY_KEYS`, `_RELATION_KEYS`, graph.py:102-108). `test_the_payload_has_exactly_the_contract_keys` holds them.
- `responsibility` is in `LEVELS`. `evidence` is in `EVIDENCE`. Sources are empty exactly with recollection (graph.py:297-302).
- `under` is set exactly on transitive (graph.py:366). Confidence is an int 0..100 and must be null for the operator (graph.py:319-325, 370).
- Entity states with `closed` only for closable (graph.py:677). Relation states `standing`/`retracted`.
- `from {"entity"}` and `to {"entity"} | {"candidates": 2..5 distinct}`, candidates only on open.
- A relation's `period` is allowed only with behavior `period` (graph.py:680). An event as the start is refused.
- Field values follow the ruling: text→str, date→`YYYY-MM-DD`, period→`{"from","to"}`, choice→str, ref→int.
- Recollection is `human:operator` and direct only (graph.py:340-343). A model writes direct only as an approval (graph.py:353).
- Gate kinds are never transitive (graph.py:670). Taken with the F-6 rule, a model's own version of a gate kind can only be open. A direct version of a gate kind by a model is possible only as an approval, which is by design: an approval copies the model as author.
- Winner (decision 10, ruling T2-a): latest direct, else the latest unanswered transitive whose class is known and not revoked with demote, else the latest unanswered open. An unknown `under` counts as open. A retracted version wins and leaves `entities()`/`relations()`.
- Approval may name an open or a transitive version (raw level, so a demoted one too). `objections()` are the pending versions contesting the *current* direct winner. `question()` is the newest waiting open relation with candidates.
- `reaches(start, end, types, *, extra, without)` matches the ruling. `fold_graph` takes rejection rows whose `of` names a graph version.
- Global: no `# type: ignore`, no new suppression, no mock, no private name imported by a test, English throughout.

### Judgement on the reported deviations

| Deviation | Verdict |
|---|---|
| `conformance_problem(..., entity_types: Mapping[int, str])` required | **Accept.** "Enden-Arten nach from/to" cannot be checked from ids alone. Making it required (not optional) stops a caller from silently skipping the lookup. One sentence for "missing" and "not visible" (graph.py:636-641) is the right shape for Review Focus 3. Retracted versions skip ends and refs, which is sound: you can still retract a relation after an end is gone. ⚠️ Task 4 (write path *and* verify, "at the time of the assertion") and Task 6 (visible entities only) must be briefed on how to build it. |
| public `level_of(version, classes)` | **Accept.** One place for "counts as open". Tasks 3, 5 and 6 need the same answer. |
| rules copied from private names in `assertion.py`/`vocabulary.py` | **Accept with Minor M4.** The equivalence tests cover the identifier and language patterns well. They cover the author rule only partly. |
| `reaches`/`relations()` count open proposals and ended edges, not questions | **Ended edges: accept.** `part_of` is acyclic as a structure, not per day, so counting ended edges is conservative and correct. **Questions excluded: accept.** **Open proposals: Important I1.** |
| extra form rules: non-blank text, `from ≤ to`, `under` exactly with transitive, no operator confidence, `contests` needs `subject`, recollection direct | **Accept.** Each derives from decision 3, 4 or 12 and has its own sentence row. The event-start refusal is the exception: Minor M5. |

---

## Part 2: quality

### Important

**I1: an open, unapproved proposal can veto the operator's direct edge.** `src/previously/core/graph.py:838-871` (line 855 walks `self.relations()`, whose winners include open proposals).

Measured with the test helpers: after a model's open `part_of` 10→11 with confidence 10, `graph.reaches(10, 11, PART_OF)` returns `True`. So when Task 4 checks a direct `part_of` 11→10 by the operator, the operator is refused because of a proposal.

That contradicts Z §7.1 ("`open`: ein Vorschlag, niemand steht dafür"; "direkt vor transitiv vor offen"). It also contradicts the module's own fail-safe principle (docstring, graph.py:20-22: "a statement nobody authorized stands for nothing"). A model gets a veto over the operator's writes, and his only recourse is to reject the proposal first.

The brief's "über Gewinner, für Zyklen" does lead here, and the implementer flagged it. But `reaches` gives Task 4 no clean way to choose: the only lever is `without` with every open relation id, which is a hack.

Proposed fix, for a ruling before Task 4:
- Give `reaches` a level filter, e.g. `levels: frozenset[str] = frozenset(LEVELS)`, evaluated with `level_of` against `self.classes`.
- Test it: a red case where an open edge is ignored under `{DIRECT, TRANSITIVE}`, and a green control where it counts under all levels.
- Let Task 4 pick per write. An open write is checked against all edges, because a proposal must not close a cycle with anything. A direct or transitive write is checked against direct and transitive edges only. An approval is itself a direct write and gets checked again at that moment.

The consequence must be stated in the ruling: the winner graph `relations()` may then hold a cycle that runs through an open edge. Any upward walk over `part_of` (behavior `transitive`) needs a visited set, as `reaches` already has.

If the controller instead rules "proposals block", then add a comment and a test that pin it, and Task 4's refusal sentence should say that a proposal stands in the way.

### Minor

**M1: a choice value spelled like a date is refused once it has been parsed.** graph.py:524-526 together with graph.py:599-600.

`_value_of` turns any real-date string into a `date`, and the CHOICE branch demands `str`. Measured:
- The vocabulary accepts `FieldSpec("phase", "choice", ("2026-01-01", "later"), ...)`.
- `conformance_problem` on the *built* claim says `None`.
- On `parse_claim(claim_payload(...))` it says `the field "phase" holds none of the values its kind allows`.

So the write path (built claim) and `verify` (parsed payload) would disagree about the same event.

Fix: treat CHOICE like TEXT, i.e. accept a `date` whose `isoformat()` is among the values. Add a red/green pair.

The underlying smell is concern 2 of the report: the Python type of a field value depends on its spelling, not on its declared type. Keeping field values as `str` in the claim and interpreting them by `FieldSpec.type` would remove the class of bug. That is a larger change, and the ruling's `FieldValue` permits the current one.

**M2: a question, and every older proposal, goes silent behind a later *transitive* version.** graph.py:739-746 and graph.py:758-800.

The ruling says a question is "answered by a later direct version". Decision 5 and Z §7.3 say "die Antwort ist eine direkte Fassung". Measured: a question, then a transitive version of the same relation under an active class, gives `question()` = `None` and `pending()` = `[]`.

That is defensible (Z §7.1: the operator stands for a transitive version), but it is a deviation from the ruling's wording, and the Hypothesis expectation encodes the same anchor, so nothing would catch a disagreement.

Confirm it by a ruling. Otherwise anchor `question()` on direct versions only.

**M3: a rejection that names a direct version still lands in `rejected`.** graph.py:906-914.

Measured: `[entity(), rejection(1)]` gives `rejected == {1}` while 1 remains the winner. It has no effect on the winner, but a consumer of `rejected` (status, triage, Task 5) would show a direct version as rejected.

Decision 5 limits `of` to an open or transitive graph version. Skip a rejection whose target is direct, the way `_approvable` skips one.

**M4: the copied author rule is only half held.** graph.py:100 and tests/test_graph.py:549-568.

- `_MAX_CLIENT = 200` re-declares a bound that `assertion.py` exports publicly as `MAX_NAME_LENGTH`. Import it instead of copying the number.
- The equivalence test has no client of 200 or 201 characters (`"m" * 5` lacks the `model:` prefix), and no U+2028/U+2029. A drift in the length bound or the line separators stays green.
- `_units_problem` and `_source_problem` are copied with no equivalence test at all. The difference is intended only in `_evidence_problem`.

Add those cases, or ask for a ruling to make the helpers public in `assertion.py`.

**M5: an event as the start is a form fault, where plan decision 4 says "die Form ist dafür offen, der Schreibweg weist es in Phase 1 ab".** graph.py:439-443.

In phase 1 the effect is nil, since nothing writes one. But the sentence is now `claim_problem`'s, so `verify` would call a phase-2 event malformed. Phase 2 must change the form check, not only the write path.

Either keep it and note in the map that phase 2 changes `claim_problem` and `RelationBody.start`, or move the refusal to Task 4.

**M6: the module docstring overclaims.** graph.py:27-28 says both checks return "one sentence that never contains text found in the payload". But `_field_problem` and the required-field sentence (graph.py:608-612, 629) quote the field name, which is a payload key.

The name is a declared identifier from the vocabulary, not statement text, so the code is fine and the claim is wrong. Reword it, e.g. "never a value from the payload; a field it names is named as the vocabulary declares it".

### What holds (checked, no finding)

- **Erasure.**
  - A first version erased: the thread continues (test).
  - An erased approval: its target becomes approvable again, since the row is skipped.
  - An approval or a contest naming an erased id stands, as with obligations.
  - Rejections of erased versions are ignored.
  - The property draws erasures over all row ids.
- **Approval chains.**
  - A second approval of the same target and an approval of a direct version are skipped.
  - An approval of a rejected target is skipped.
  - An approval of a demoted transitive version is accepted.
  - An approval copies `author`, so the F-6 form rule admits it.
- **Periods.** Both ends are inclusive, as Z §6.3's "bis 2019" reads, and `from == to` holds on that day. Ten boundary cases are tested, including open ends and no period. `from > to` is a form fault.
- **Error messages.** No sentence interpolates a payload value. The interpolations are a constant key name, `claim.kind` (already validated), and the vocabulary's field name (M6).
- **`claim_problem` never raises.** The checks run in order, so every later cast reads a validated key. The test covers every key × 9 odd values × 3 bases.
- **Behavior tests.** The tests assert the fold's results, not internals. Report mutations M1–M13 each name a red test and a green control. That fits the rule, though I did not re-measure them.

### The Hypothesis property

`tests/test_graph.py:1224-1363`.

**Independent of `fold_graph`: yes.** `expected_versions` re-derives acceptance from the rows: rejection when `of` is already a version, contest when the target is erased or a standing direct version, approval when unanswered and erased or a standing open or transitive version. `expected_level` re-derives the demote and unknown-class rule. Winner, anchor, `pending` and `objections` are then computed from those lists. The property never reads the fold's own output to build its expectation.

It is a restatement of the same rules, so a misconception shared by both sides passes (M2 is an example). That is inherent in a model-based property.

**Catches "transitive beats direct": yes, twice.** With the `_anchor` order swapped, `expected` (direct first) differs as soon as an unanswered transitive version under a class in force follows a direct one. The explicit guard at lines 1360-1363 fails as well. The generator draws first=direct with probability 1/3, transitive steps under 901/902 in force with probability 1/3 each, up to 14 steps and 400 examples. The report's 10/10 seeds is plausible.

**Catches "demote ignored": yes.** It needs a transitive version under a revoked-with-demote class and no direct version, which shifts both the anchor and the winner. The reasoning behind 400 examples (measured 3/5 seeds at 100, 10/10 at 400) is written beside `@settings`, as a dated measurement.

**Gaps (no finding):**
- one entity thread only;
- no relations, questions or retractions;
- `approved` is not asserted.

Unit tests cover those cases.

---

## ⚠️ What the diff cannot show

1. **Keying of `classes` (Task 3).** `level_of` looks up `classes.get(claim.under)`, where `under` is the event id of the class version the model wrote under. Classes are replaced per `name` by newer events, so a revocation is a *new* event id.
   - Task 3 must map **every** event id of a class name to that name's current `ClassState`.
   - If it keys by the latest event only, every transitive version under an earlier event turns open (unknown class) at the first class update, including a mere threshold change.
   - Fail-safe, but wrong.
2. **Gate kinds in `relations()`.** Open and transitive winners appear in `relations()`, and an open `member_of` winner is among them. Z §7.6.1 says `member_of`/`in_circle` "gelten nur direct". Phase 1 leaves `decide.py` untouched, but any later consumer feeding the gate from the graph must filter by `level_of == DIRECT`.
3. **Not checked by the fold (Task 4):**
   - that an answer's `to.entity` is one of the question's candidates;
   - that an approval copies the content of what it approves.
4. **An open retraction by a model wins in a thread that has only open versions** (measured: the entity leaves `entities()`, also when the earlier open version was the operator's). That is decision 10 as written ("retracted wins like any version"). Task 6 may want to say so in the instructions.
5. **The tutorial block was retyped mid-plan** because `test_docs_typed_output.py` forced it. The Global Constraint "zuletzt" still requires a final retype after Task 7.
