# Task 6 re-review (fix base 364a971, head fc0d6f0)

## Verdicts
- I1 ADDRESSED. closes_cycle returns False for level OPEN (graph_write.py ~L284, `if level == OPEN: return False`), the DIRECT/TRANSITIVE-only graph is used for the rest; Classes._covering (classes.py, `ACYCLIC in spec.behaviors -> []`) gives open for an acyclic kind even for a hand-written class event; _refusal/set_class/class_refusal refuse such a class; verify passes vocabulary to covers() and uses level_of for closes_cycle.
  Paths checked (no model path refused or levelled by hidden edges):
  - write_entity preview/confirm: no edge logic at all; _refuse_unseen (server.py L2027) only sees the client's view.
  - write_relation preview (check_claims -> _checked -> _levelled -> _check_claim): model claim is OPEN for acyclic kind, closes_cycle False. Objection (contests a direct winner) is OPEN too. Question is OPEN.
  - write_relation confirm (write_claims with expect): same _checked; the level cannot depend on edges, so _check_expected cannot move because of them.
  - model self-edge: also OPEN, not refused.
  - write_assertion: not relation-bearing.
  - write_reject: retraction/rejection, not a standing relation, closes_cycle False.
  - write_triage_answer and write_approve: DIRECT, cycle-checked over all edges (see the new Important-free observation 1).
- I2 ADDRESSED. read.py triage(): no `hidden` set, no WITHHELD section, TRIAGE_SECTIONS has three entries; every item is gated on view.verdict(...).shown; header uses objections_seen over view.seen. Cursors/`more` are computed from the visible `found` list only. test asserts no `[withheld:` and no Lea id. list_entities still shows placeholders for hidden entities (by design, unchanged, not a function of waiting items).
- M1 ADDRESSED (read.py GraphView.delivered unions circles of all decisions; test with control).
- M2 ADDRESSED (test_a_vocabulary_changed_between_preview_and_confirmation_refuses_the_write; asserts exact error and no write; control present).
- M3 ADDRESSED (core relation_visible takes the thread, uses relation_ends of every version, None for erased end withholds nothing, missing end not seen; GraphView.verdict calls it; a non-entity end maps to False; forged-relation test).
- M4 ADDRESSED (`len(_assertions(world)) == count`).
- M5 ADDRESSED (_Folded context var, graph_now; entities/triage take graph; counting-store test).

## New Critical/Important problems introduced
none

## Out-of-scope observations
1. write_triage_answer (person-confirmed, ask mark) writes a DIRECT answer, which is cycle-checked over hidden edges, so it has the same one-bit residual as write_approve. mcp-tools.md documents the residual under write_approve only; one sentence under write_triage_answer would complete it (Minor).
2. ThreadVerdict docstring says a relation starting at an event "has no `blocked` either"; the code does not clear `blocked` there (own decisions are still taken). Harmless: only entities get placeholders (read.py L1237), so nothing consumes it for relations (Minor, docstring claim).
3. Map entry for the T6-a residual is not written (Task 7's file), as the report says.
