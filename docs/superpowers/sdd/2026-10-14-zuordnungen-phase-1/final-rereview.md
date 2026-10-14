# Final re-review of the fix wave 9967268..992029c

Read from the diff; ran only the awk count, the store.py docstring commands and `pytest --collect-only -q` (2645 collected).

1. F-a/T7-a: ADDRESSED. vocabulary.py `missing_kinds`/`differing_kinds`, `apply_vocabulary(add_only)` computing the set inside the write transaction under the tip; cli.py `_cmd_vocabulary_apply` (base path uses missing_kinds, `apply FILE` unchanged, differs lines + sentence). Handoff, club how-to and adapt how-to now say safe/never retires; adapt how-to line 103 keeps the FILE semantics. No destructive instruction remains (grep).
2. F-b/M1: ADDRESSED. server.py `_refuse_gate_kind` called in graph_approval_write and triage_answer_write before any write; write_reject untouched; CLI approve test present. `level_of` returns OPEN for GATE_TYPES. Tests carry mutation notes and in-test controls (holds proposal; holds-control).
3. F-c: ADDRESSED. graph.md section graph-cost, the map and the handoff carry every required figure with dates (0.52/1.72/0.47/2.77; 7.35/135/7.69/23.7/7.5/7.34; part_of 0.84/2.34/14.84/78.6, tree 0.78/2.10/13.05). Phase 2 projection or incremental fold stated; header cost names the fold and objections_seen.
4. F-d: ADDRESSED for all items.
   - M2: verify.py approval reason "overtook" plus test with control.
   - M6: graph.md placeholder claim replaced.
   - M7: store.py says eight; command output re-measured: begin, observations, read, read_by_kind, snapshot, source_keys, tip, units_by_event = 8. core count 15, 15 modules naming LogStore.
   - M9: author_problem / is_identifier / is_language_tag shared; copies gone; private-use case (U+E000) accepted by both rules, tested both sides.
   - M10: `extra` removed, _Shown protocol, value_text shared.
   - M11: ThreadVerdict docstring.
   - M12: cli.py `_entity_claim` guard, cli.md quotes it, test with control.
   - Task 7 minors: header cost wording, "etwa quadratisch" with factor, "rest still to be taken" gone.
   - Map: 225 at 9967268 -> 233 now (awk). Struck items are in Erledigt.
5. Tutorial: ADDRESSED. "collected 2645 items" and "2645 passed", equal to the measured collect count.

## New Critical/Important problems
none.

## Out-of-scope observations
- `apply --base` also prints a `differs` block for built-in kinds (member_of etc.) whenever their labels in the base differ from the code form; harmless noise, no test seen for it.
- M2 guard `newer > approves` relies on `versions` excluding the row under check; it holds by the fold order, and the test covers it.
