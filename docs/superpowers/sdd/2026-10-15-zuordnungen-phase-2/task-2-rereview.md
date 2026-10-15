# Task 2 re-review (fbdd05e..a6d358a)

- I-1 ADDRESSED: members.py:542-561 (`bracket_kinds`), :623-641 (`bracket_edges(graph, vocabulary)`), :678 (`members(edges, bracket, kinds)`). `grep '"part_of"\|"concerns"' src/previously/core` finds nothing. Retired kinds count, GATE_TYPES excluded; tests in test_members.py (second transitive, mentions, in_circle with control, retired).
- I-2 ADDRESSED: graph.py:347 `rests_on`, used in graph_write.py:484/553/623 (write, preview, `_checked`) and verify.py:874. Tests: test_graph_write (missing and erased unit, write and preview, control), test_verify (two), test_cli (1:9 under --source 1). Mutation "sources only" is reported red (task-2-report.md mutation table); by reading it must be: a whole-event source passes `check_sources` and verify's standing check alone. Not re-run by me (read-only).
- T2-c ADDRESSED: members.py:530 `_STANDS_FOR`, :717-720, :730-732; open edge adds, excludes only on direct/transitive. Oracle in the property matches.
- T2-d ADDRESSED: documented in module and `Members` docstrings; period test (test_members.py, `at=` mutation red).
- M-1 ADDRESSED for spelling (cli.py:3503-3510 uses `_sources_text`), but see Minor below.
- M-2 ADDRESSED: property compares brackets, events, excluded (test_members.py ~1487-1502).
- M-3 ADDRESSED: graph.py:324 constant after MIN/MAX_CANDIDATES.

## New issues
Critical/Important: none.

Minor: `_claim_fields`' relation branch (cli.py:3503-3510) is dead code. Its only caller is `_entity_history_lines` (cli.py:3635), and entity threads carry no relation. The implementer is right that nothing reaches it; the branch is untested and the "agree with claim_changes" fix guards a path that cannot run. Recommend removing the relation branch (and `_claim_fields` relation handling) rather than keeping it aligned; if kept, say it is unreachable. Not blocking.

## Out of scope
Nothing found.
