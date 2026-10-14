# Task 2 re-review (fix 99a67dd..1156411)
I1 ADDRESSED: graph.py `reaches(levels=...)`, default all LEVELS; filter by level_of; relations() docstring names the open-cycle case; tests red/green (open edge vs STANDS_FOR, control with demoted class).
M2 ADDRESSED: docstrings of pending/question; test_a_later_transitive_version_answers... with demoted control.
M1 ADDRESSED: _field_problem isoformats a date for TEXT/CHOICE; round-trip test 3 cases.
M3 ADDRESSED: _reject takes classes, ignores direct targets; test + property updated.
M5 ADDRESSED: event start is sound form (_entity_problem), refused first in conformance_problem; round-trip, form rows, claim_payload/parse_claim/claim_changes/_sources_text handle Source.
M4 ADDRESSED: MAX_NAME_LENGTH imported; sentence-level equivalence tests, 200/201, U+2028/2029, source equivalence with both-sides controls.
M6 ADDRESSED: module docstring now accurate.
Deviation RelationBody.start: int | Source: sound. Conformance refuses it for every state so no write path produces one; reaches skips Source starts; only a hand-written stored relation can reach tasks 4-6 via relations(), which must handle/skip a Source start (verify reports it). Brief only gave `start: int` in a signature sketch; no non-graph module reads .start.
N8 claim verified: ' '.isspace() and ' '.isspace() are True, and the author rule has `not any(char.isspace() ...)` (graph.py:263, assertion.py:255), so the separator clause cannot change an author verdict. Not a gap. (Note the clause is then dead for authors in graph.py, harmless.)
New Critical/Important: none.
Out of scope: tasks 4-6 must treat Source start in relations().
