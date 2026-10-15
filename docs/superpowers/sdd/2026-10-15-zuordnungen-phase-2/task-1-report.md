# Task 1 report
Status: done. Six gates green (pytest 2666 passed, coverage 100% on graph.py and vocabulary.py; docs html/vale/linkcheck ok).
Changes: EVENT_START/ANY_ENTITY in core/vocabulary.py (form check and file parser share `_parse`; sentences for event in `to`, `*` in `from`, `*` beside others, entity kind named `event`); reference check skips both; `concerns` in vocabulary.toml; conformance_problem/_ends_conformance in core/graph.py; reference page; CLI tests shifted by one event; tutorial test block retyped (2666).
Mutation: dropping the `*` clause in _ends_conformance -> 5 test_graph failures; removing concerns from the base -> 2 failures; controls (holds, concerns with a listed kind) stay green.
Ruling P-1 kept: nothing else lifted.
Concerns: I added a refusal for an entity kind named `event` (not in brief). Refusal sentence for an event start on a kind lacking `event` was reworded (old test updated).
