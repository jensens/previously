# Task 1 review

Spec: ✅
Quality: Approved (Minor findings only)

## Named risks

1. Event start accepted outside vocabulary and `conformance_problem`? No new acceptance path.
   `conformance_problem` is the shared gate, so its callers (graph_write `_check_claim`, verify, the MCP preview at server.py:2082, the cli mark at cli.py:3343) now see a `concerns` event start as fitting. That is the intended lift (P-1).
   Everything else stays closed: `closes_cycle` returns False for a Source start (graph_write.py:273), the MCP read filter hides such a relation (graph_write.py:771), the acyclic fold skips it (graph.py:897), and the MCP write model takes `start: int` only (server.py:573).
   No test pins "the write path still refuses" an event start, but that refusal was never in the write path, only in `conformance_problem`.
2. `test_cli.py` id shifts: only numbers. One extra base event (concerns) shifts every later id by one (9 to 10 events, 10 to 11, 12 to 13). Each assertion keeps the same meaning (same shape of output, same relation between counts).

## Deviations

- Entity kind may not be named `event` (vocabulary.py `_parse`): sound. Otherwise `from = ["event"]` would be ambiguous with an entity kind. Applies to entity declarations only; tested with control (`TEAM`). Accept.
- Event-start sentence reworded ("needs a relation kind that starts at an event"): accept; the old text ("comes with assignments") would now be false. Test updated and a green control added.
- Unknown-type check now runs before the event-start check: accept. An unknown type now gets the type sentence instead of the event sentence; it needs the spec to decide anyway.

## Decisions checked

`event` only in `from`, `*` only in `to` and only alone: enforced in `_parse`/`_starts`/`_targets`, covered by END_ERRORS cases (form and file). `concerns` is in the base file, not BUILT_IN/GATE_TYPES. Phase-1 log gets exactly `concerns` (test with add_only, differing_kinds empty, second apply empty). `*` accepts any entity that stands; unknown end and, via the lookup, retracted-to-gone end still refused; a retracted version is not looked up. Mutation noted in the tests.

## Findings

- Minor, src/previously/core/graph.py:142 and :426-429: comments say `conformance_problem` "refuses until then / until phase 2". No longer true: it refuses unless the kind starts at an event. Update both (a comment is a claim).
- Minor, src/previously/core/vocabulary.py:230-231: `in_circle` comment still says "until phase 3 gives a relation that start", fine, but the docs reworded it to "built-in relation"; harmless, consistent enough.
- Minor, docs/tutorials/record-your-first-event.md: the diff changes only the random seed line, though the suite grew (new tests). The typed block's `N passed` and collected counts are not retyped here; `test_docs_typed_output` guards only `N passed`. Retype at the end of the phase (CLAUDE.md: type it last), not necessarily now.
- Minor, tests: no test that `*` with a retracted-to target in an existing thread is refused (only unknown id 99). Retracted entities are absent from `entity_types`, so the same branch; low value.

Counts: Critical 0, Important 0, Minor 4.
