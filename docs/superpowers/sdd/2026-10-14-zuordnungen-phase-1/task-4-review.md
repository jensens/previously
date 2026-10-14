# Task 4 review: write path, reading, verify, cascade (516ba45..a93ee1b)

Spec: ❌ (one binding rule of ruling T4-a is not held on one path; everything else matches)
Quality: Changes requested

Reviewed in four passes over the diff:
1. `core/graph_write.py` in full, read from the worktree at a93ee1b; `core/graph.py` in full, because the level and fold rules the write path relies on live there.
2. `core/assertions.py`: is unit 5 unchanged?
3. `core/verify.py`, `core/classes.py`, `core/vocabulary.py`.
4. The tests (`test_graph_write.py`, `test_cascade.py`, `test_verify.py`, `test_assertions.py`), the `cli.md` block and the trailer.

I wrote one scratch test file in the scratchpad (`scratchpad/t4/test_doubt.py`, which imports the helpers of `tests/test_graph_write.py`) for two specific doubts.
Both doubts were confirmed (I1, M1).
I did not re-run the suite.

## Findings

### Important

**I1: a transitive version answers a pending question with an entity outside its candidates.** `src/previously/core/graph_write.py:362-376` (`_check_answer`, the guard at line 367).
- Ruling T4-a: "an answer to a pending question must name one of its candidates".
- Ruling T2-c: a later transitive version answers a question, as a direct one does. `GraphThread.question()` implements this: the transitive version becomes the anchor, and the question is no longer `_waiting`.
- `_check_answer` returns early unless `claim.responsibility == DIRECT`. So a model claim on the question's thread that a class makes transitive is written with any `to`, and the question disappears from triage.
- Measured: `_question(storage)`, then a class covering `post_in` at threshold 10, then a model claim `post_in chair → three` with `subject=question` and confidence 90. Result: `Written(levels=('transitive',))`, `question()` is `None` afterwards, and the winner is the transitive version with `to = three`, which is not a candidate. No test covers this, and `verify` has no answer check either (see M3).
- Why it matters:
  - A question is the model saying "I don't know which". A class then answers it, for the operator, with an entity the question never offered, and nobody sees it.
  - It is also the one path where the answer rule depends on the level, which T4-a does not allow.
- Fix (the controller rules which): either hold transitive versions to the candidates in `_check_answer` (`responsibility in (DIRECT, TRANSITIVE)`), or have `_levelled` write `open` for a model claim that would answer a pending question outside its candidates. The second keeps the claim as a proposal instead of refusing it.
- Add a test measured red under the current guard, with a green control: a transitive answer that names a candidate.

### Minor

**M1: a preview and a write can disagree on `contests` without a refusal.** `graph_write.py:290` and `:423`.
- `expect_levels` compares `responsibility` only.
- Measured: a model's preview on thread `anna` showed `('open', contests=15)`. The operator then wrote a direct version 16, and the write with `expect_levels=('open',)` went through, writing `contests=16`.
- The same happens when a preview shows a plain open proposal and a direct winner appears before the write: the claim becomes an objection with the same level.
- The same holds for `under`: a class swapped for another at the same level is written under the new class.
- None of this is unsafe, since the level is unchanged and open stays open. But the client was shown something else than what was written. Review Focus 2 names only the level, so this is a note for Task 6, or a wider comparison (`responsibility`, `contests`, `under`).

**M2: the retired-kind rule for approvals is inconsistent.** `graph_write.py:187-192` (`starts_thread`, deviation 3).
- An approval of a thread's first version counts as new and is refused for a retired kind. That refusal also hits a first version that is transitive and already stands for the operator. Yet a plain direct version on the same thread is allowed.
- Conversely, an approval of a later open version (`approves != subject`) on a thread that never had a direct or transitive version is not "new". It makes an entity of a retired kind stand for the operator for the first time, which is exactly the case deviation 3 means to refuse.
- Deviation 3 can stand. The rule should be "the thread has no version the operator stands for" (no anchor), not "approves the first version", with a test for each of the two cases above.

**M3: `verify` does not report three things the write path refuses.**
- The places are `verify.py:649` (`claim_reason`); the write path's rules are at `graph_write.py:281-290` and `:362-376`. The three cases:
  - a direct (or, after I1, transitive) answer outside the candidates;
  - a transitive or plain open model version on a thread whose winner was direct, which the write path makes an objection;
  - an open version by the operator.
- All three need a forged row, and all are harmless in phase 1.
- The `_Claims` docstring says only the cycle rule is "exactly what the write path would have refused", so no comment claims more.
- Either record this as a known limit or add the checks. The answer check matters most once I1 is fixed.

**M4: `verify`'s per-row cost is quadratic in every graph row, not only in acyclic edges.** `verify.py:654`, and `graph.py` `GraphFold.graph`, which returns `Graph(dict(self._threads), …)`.
- `claim_reason` calls `graph()` once per entity or relation row, and every call copies the whole thread dict.
- Measured here: one copy takes 0.76 ms at 100,000 threads and 0.025 ms at 10,000. That is an estimated ~40 s of copying alone for a `verify` over 100,000 graph rows, before the acyclic walk.
- The `_Claims` docstring and concern 1 name only the acyclic walk. Ruling T4-c measures `verify` at 10,000 acyclic edges, so it should also measure at 100,000 relations, or `graph()` should hand out a read-only view instead of a copy.

**M5: the vocabulary and class folds of `verify` skip an event that `read_vocabulary` and `read_classes` take.** `verify.py:463-473`.
- `_Erasures.observe` feeds `claims.action` only when `_form_finding` is `None`, and `_statement_finding` also refuses a vocabulary or class event that has units.
- `VocabularyFold.add` and `ClassFold.add` in the read path check the form only.
- So a forged vocabulary event with units governs the write path and not `verify`. Claims written under it then show up as findings too.
- It needs a forgery, and the event itself is already a finding, so this is low weight. The cleanest fix is to feed the fold on `problem is None`, regardless of units.

**M6: the new paragraph in the module docstring of `core/assertions.py` is broader than that module.** `assertions.py:28`.
- It says "A vocabulary or class event read after the tip…". `assertions.py` reads the classes only; `graph_write.py` reads both.
- The sentence is true for both paths taken together. Saying "a class event (and in `graph_write.py` a vocabulary event)" keeps the claim to the module.

**M7: a repeated handle answers across write paths.** `graph_write.py:432-441`, `:465-468` and `:538-542`.
- `_repeated` matches any assertion with that handle, as `write_statements` does.
- A graph batch whose handle an obligation batch used gets that batch's ids from `write_claims`, and an empty tuple from `check_claims`, because `parse_claim` gives `None` for obligation payloads.
- This is the same handle space as unit 5, so it is consistent. Task 6 should not show an empty preview as "nothing to write". Note only.

## The named risks, one by one

- **A GATE_TYPES claim at a level other than direct or open:** not through the write path.
  - `Classes._covering` excludes `GATE_TYPES`, so `level` never returns transitive for them.
  - `conformance_problem` refuses a transitive gate kind as a second line.
  - An approval is direct, and an objection is open with `under=None`.
  - Each claim of a batch goes through `_levelled` and `_check_claim` on its own.
  - `verify` reports a transitive gate kind through `conformance_problem`.
  - ⚠️ below for the fold.
- **A model's claim direct other than as an approval:** no.
  - `_levelled` replaces the level of every model claim that is not an approval: objection, question, or the class level, with `under` and `contests` reset.
  - `claim_problem` forbids a direct model version without `approves`.
  - `_check_approval` runs for every approval, since the form requires a subject.
  - The answer-by-approval of deviation 2 is still an approval of the question, and `takes_proposal` restricts the change to `to ∈ candidates`.
  - Mutation D in the report covers the client-given level.
- **A preview and a write disagreeing without a refusal:**
  - A vocabulary change is re-checked under the tip, and a change the claim no longer fits is refused.
  - A class change or a new direct winner that changes the level gets `CLASS_CHANGED`.
  - The residue is M1 (`contests` and `under` at the same level).
- **Unit 5 unchanged:** yes.
  - `check_sources` iterates the same sources in the same order, with the same sentences.
  - `_check_all` keeps its order: sources first, then references.
  - The graph lookup in `_check_rejection` runs only where unit 5 would already refuse (`of not in view.versions`), and then falls back to the unchanged sentence.
  - `SourceEvents.of` → `named` keeps the sorted unique order, because `_source_events` already sorted.
  - `read_sources` is the old inline loop, moved.
- **Error messages:** no payload text and no address.
  - Every sentence in `graph_write.py` names ids, kinds, or field names as the vocabulary declares them.
  - `claim_problem` and `InvalidPayload` are passed through as in unit 5, and `AssertionRefused` is re-raised unchanged.
- **verify:**
  - A graph rejection goes to `claims.rejection_reason` before the obligation check, so it is not "names no open proposal" unless the version really is direct.
  - The vocabulary and the classes are folded in chain order in the same single pass (`_Erasures.observe` runs per row, interleaved with `_Assertions.observe`), so they are the ones in force at the claim's position.
  - The residue is M5 (an event with units).
- **Race safety:** sound.
  - Rows are read with `up_to=top`.
  - Vocabulary and classes read after the tip can only be newer when an event took `tip+1`, and then the insert fails and `retrying` folds again.
  - The two-connection test meets at the tip with a barrier and checks that the loser read the tip twice. It is a real test of decision 13.
- **Deviations (ruling T4-b):**
  - 1 (batch by fold) is right and better than `extra`. A batch's open edge does not count against a later transitive edge of the same batch (T2-b), and a non-winning version contributes no edge.
  - 2, 4 and 5 are acceptable.
  - 3 stands, with M2.

## ⚠️ Items (not findings against this task)

- **The fold trusts `under` for gate kinds.**
  - Area: `graph.py` `level_of`, Task 2's code. A forged `{type: circle, responsibility: transitive, under: <any class event id>}` counts as transitive in `fold_graph` and `read_graph`; only `verify` reports it.
  - Harmless in phase 1, since `core/decide.py` does not read the graph.
  - Before the gate reads circles and memberships (phase 2 and 3), `level_of` should count a transitive gate kind as open, the same fail-safe as an unknown class.
- **Task 6 must set `author`.**
  - The core takes the author from the claim. A caller that let a client write `human:operator` would get direct non-approval claims.
  - The MCP server has to set `model:<client>` itself, as it does for obligations, and Review Focus 3's same-sentence refusal of invisible ends also belongs to Task 6 (report concern 3).
- **A pending question blocks an operator's other answers.** While a question is pending, any direct standing version on its thread, an approval of another pending proposal among them, must name a candidate. The operator's way out is to reject the question first. That is the consequence of T4-a; the how-to (Task 7) should say so.
- **Relations can point at an erased entity.** After a cascade erases an entity, relations naming it stay in `relations()`, with an end that `entities()` no longer has. `relation_visible` hides them, because an id missing from `ends` is not visible. Task 5's listings should skip or mark them.

## Counts

Critical 0, Important 1, Minor 7.
