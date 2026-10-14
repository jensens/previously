# Task 4 re-review of fix round 1 (a93ee1b..dac79b0)

Verdicts, from reading the diff (suite not re-run; the report's mutation tables were read, not repeated).

- I1 ADDRESSED. graph_write.py `_levelled` (after the direct-winner rule, before the class lookup) writes a model claim open, under=None, contests=None when `pending_question` is set and `names_a_candidate` is false. A transitive claim naming a candidate falls through to the class and still answers. `_check_answer` shares the helpers. `verify` `_claim_rules` reports a transitive or direct-standing claim that answers with a non-candidate. Retractions by a model are written open (T4-g).
- M1 ADDRESSED. `Decided(level, under, contests)`, `decided()`, `_check_expected`: contests differs -> `DIRECT_WRITTEN`, level or under differs -> `CLASS_CHANGED`. Length mismatch is ValueError.
- M2 ADDRESSED. `starts_thread(claim, thread)` is new for subject None, or a direct/transitive non-retraction on a thread with no direct/transitive version. Used by both the write path (`_check_claim`) and `verify` (`_claim_rules`), with the same `thread` meaning (thread before the claim, None if erased).
- M3 ADDRESSED. verify.py `_claim_level` (operator open, model after a direct winner that is not the objection) and `_claim_rules` (answer outside candidates). cli.md rows and the three finding lines are added, and the docs test is extended (per report).
- M4 ADDRESSED. `GraphFold.current` returns `Graph(MappingProxyType(self._built()), ...)`, so there is no per-row copy. verify and `_checked` use it. The timings are in the `_Claims` docstring (10,000 relations 4.90 s -> 2.67 s; still quadratic with acyclic edges, and the docstring says so).
- M5 ADDRESSED. `_Erasures.observe` feeds `claims.action` before `_form_finding`, so a vocabulary or class event with units counts in verify as it does in `read_vocabulary`/`read_classes`. Both folds ignore broken-form payloads, so moving the call earlier changes nothing for those.
- M6 ADDRESSED. The assertions.py docstring now says this module reads the classes after the tip, and only for a graph rejection; graph_write reads the vocabulary too.
- M7 ADDRESSED. Both `_repeated` functions filter on the assertion kind (`KINDS` in assertions.py, `GRAPH_KINDS` in graph_write.py), so each matches only its own write path's rows.

## GraphFold.current read-only check
The view is a `MappingProxyType` over the live `_threads` dict, so no holder can mutate it. `GraphThread` is a frozen dataclass with tuple/frozenset fields. `Graph` has no caches, only `_winners`, `entities` and `relations`, which build fresh dicts. `_built()` is the only mutator, and it runs inside `current`/`graph`. In `_checked` the graph is used by `_levelled`, `_check_expected` and `_check_claim` before `folded.add`, and is not kept past the iteration. In verify, `claim_reason` computes the reason before `self.fold(row)`, and `_found` uses its graph immediately. I found no case where a view stays alive across an `add`, so it cannot be mutated or go stale through the fixed call sites. The one hazard is a future caller that holds `current()` across `add`; the docstring states that it follows the fold.

## New Critical/Important problems introduced
None.

## Out-of-scope observations
- `starts_thread` treats a thread with every version erased (None) as not new. That is deliberate and documented.
- A pre-existing quirk: `_check_answer` and `names_a_candidate` require `body.to in candidates`, so a direct standing question with `candidates` set is refused on a thread with a pending question. Not touched by this diff.
