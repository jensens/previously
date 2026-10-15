# Task 2 review — base 5f791e6, head fbdd05e

Spec: ❌ (only because of ruling T2-a, decided after the implementation; everything else in the brief, decisions 3, 4 and 12, the dispatch decisions and rulings P-1, P-2 and T2-b is met)
Quality: Changes requested

Reviewed: the brief, context.md (decisions 3, 4, 12, Review Focus 1 and 4, the Global Constraints), progress.md (P-1, P-2, T2-a, T2-b), the report, the whole diff, and the code at fbdd05e around it (write path, `check_sources`, `verify`'s source pass, the redaction cascade, `GraphView`, `claims_staged`, `_refuse_unseen`, every `.start` consumer).
I did not re-run the six gates or any test. The report's gate figures are unverified by me.

## Findings

### Important

**I-1 — `members` names kinds in code (ruling T2-a).**
`core/members.py:35` `PART_OF = "part_of"` and `:36` `CONCERNS = "concerns"` are the logic, used at `:89` (`bracket_edges` filters `body.type in (PART_OF, CONCERNS)`), `:100` (`_below` walks only `PART_OF`) and `:130` (`members` reads only `CONCERNS`).
Docstrings name them too: `:8-11`, `:55`, `:83`, `:95`, `:121`.
T2-a wants the hierarchy from every relation kind with behaviour `transitive` and assignments from every relation kind whose `from` names `event`, both from the vocabulary in force.
So `bracket_edges` needs a vocabulary, and either `BracketEdge` carries a role (hierarchy or assignment) in place of a kind name, or `members` takes the two sets of kinds. That choice also fixes what Task 4 has to build from projection rows (ruling P-2).
`tests/test_members.py` imports `PART_OF` and `CONCERNS` from `members` and builds all its edges with them, so the tests have to change too. The Hypothesis property can stay as it is if the roles come in as parameters.
Elsewhere `concerns` appears only as text, not logic: CLI help `cli.py:3957`, the comment `cli.py:3576`, the MCP descriptions `mcp_server/server.py:410`, `:572`, `:579`, `:596` (pinned by `TOOLS_SHA256`), the docstring `core/graph.py:144` and the comment `core/vocabulary.py:85`.
`part_of` appears in logic nowhere else (`core/verify.py:596` is a comment about a measurement).

**I-2 — the units of an event start go unchecked when a wider source covers them.**
`_checked` checks only `claim.sources` (`core/graph_write.py:483`), and `verify` checks only the units of the sources (`core/verify.py:996`).
`covers` (`core/graph.py:469`, used at `:505`) accepts any start units under a source that cites the whole event.
So `relate concerns --from-event 1:99 --to N --source 1` and MCP `from: {"event": 1, "units": [99]}, sources: [{"event": 1}]` are both written, and `verify` reports nothing.
The same holds for a unit erased **before** the assignment: `check_sources` refuses an erased unit only when the source cites it. `stands_on_erased` leaves the assignment standing, because the redaction is older than the assertion and the source is the whole event. `members(...).holds(1, 3)` is then true for a unit that no longer exists.
That breaks the report's "the start checked as a source (missing event, missing unit, not an observation)" (`test_the_start_of_an_assignment_is_checked_as_a_source`). The claim holds only when the start is the source itself, which is the only case the CLI test (`event 1 has no unit 9`) and the graph-write test exercise.
Nothing leaks, since the unit holds no content. But an assignment of a missing or erased unit is a record that the write path should have refused and `verify` should report.
Fix: check the event start like a source in `_checked`, in the preview (`check_claims`, the same function) and in `verify`'s source pass: exists, cited units exist, none erased. Add a test for each with a whole-event `--source`, measured red against today's code.

### Minor

**M-1 — two spellings of one start in one history.**
`_claim_fields` (`cli.py:3512`) prints the first version's start as `event 1 #2`.
The change lines come from `claim_changes` → `_texts_of` → `_sources_text` (`core/graph.py:1147-1151`) and print `event 1 units 2`.
The docstring of `_claim_fields` says the two "read alike".
For entity starts they already differed in phase 1 (`10` against `entity 10`), so this is not new, but the new format adds a second mismatch.

**M-2 — the property only checks `holds`.**
`test_a_unit_belongs_by_its_own_assignments_else_by_its_events` compares `found.holds` with the oracle. It never checks `found.events`, `found.excluded` or `found.brackets`.
Tasks 4 and 5 will most likely pick events by `events` keys and units by its values.
A mutation that adds an event with an empty `frozenset` to `events`, or one whose units are all excluded, stays green.
Cheap to add: `event in found.events` iff some unit of it holds under the oracle (or, for `None`, that an event-level edge points in), and `found.brackets == {e | bracket in _wholes(e, parts)}`.

**M-3 — `START_NOT_A_SOURCE` splits a block of constants.**
`core/graph.py:99` sits between `MAX_CONFIDENCE` and `MIN_CANDIDATES`/`MAX_CANDIDATES`, with a blank line above it and none below.

## The named risks, one by one

1. **Erasure.** Every graph write goes through `write_claims` → `_payload` → `claim_problem`: the CLI (`relate`, `approve`, `answer`), MCP (`write_relation`, approvals and answers through `answering`) and batches alike. Every fold goes through `parse_claim`.
   Because the start rule is a form rule (`_start_problem`, `core/graph.py:493`), no path can write an event-start relation whose start no source covers. A forged row does not stand, and `verify` reports it.
   Approvals copy the proposal's sources (`cli.py:2553`), and answers take the question's sources and start.
   The cascade finds the assignment by `sources` (`core/redact.py:286`) and decides by `stands_on_erased`. `tests/test_cascade.py` covers the mail, a unit, and a whole-mail assignment against a later unit (T2-b).
   The gap is I-2: a start whose units no source *cites*, only *covers*, is not checked against the log.
2. **Policy.** `claims_staged` refuses a hidden source before anything else (`mcp_server/server.py:1717-1722`), and the start is among the sources by then (`sources_with_start` in `_relation_claim`).
   A narrower source is a form refusal and says nothing about the log. A hidden bracket is refused by `_refuse_unseen` with the missing-entity sentence.
   Listings: MCP `list_entities` skips assignments (`read.py:1183`), and `list_triage` shows one only when `relation_visible` lets it through, which now decides over the mail. The test pins both modes and both clients.
   The CLI is the operator's, with no policy.
   I found no listing that shows an assignment, or its event, to a client that may not see the mail.
3. **`members` against its oracle.** Independent: the oracle walks upward from each target over raw `(part, whole)` tuples and decides per unit. `members` walks downward and works per event with `excluded`. They share only the input.
   Generated inputs: 6 entities, 3 events with 4 units each, up to 10 hierarchy and 10 assignment edges, noise, cycles and self-edges, 400 examples.
   Both cases come up often under those sizes: a unit's own edge outside while its event's edge is inside (`excluded`), and a unit's own edge inside while its event has none.
   Fixed examples pin both (`test_the_property_meets_…`, Markus). See M-2 for what the property does not compare.
4. **The 19 places (CF §1).** I checked each against fbdd05e, and every `.start` consumer in `src/` handles a `Source` start:
   - the refusal is gone from `relation_visible`;
   - `closes_cycle`, `reaches` and `relation_ends` skip an event start correctly;
   - `_marks` judges conformance, which accepts `concerns`;
   - `_cmd_relations --from` matches no event start, as documented;
   - `_claim_label`, `_relation_line`, `_claim_fields` and MCP `claim_lines` print the event;
   - both entity pages skip assignments on purpose;
   - `hit_rates` and `sample` never read `start`;
   - `verify` reads the start through the sources.
   I found no consumer that crashes or mislabels one.
5. **Unit-5 and phase-1 tests.** I found nothing weakened. The removed lines are:
   - the phase-1 assertion that an event-start `holds` is shown to nobody (`test_graph_write.py`), which pinned the refusal P-1 lifts; its replacement is `test_an_assignment_is_decided_over_its_mail_…`;
   - the `relation` helper in `test_graph.py`, which now cites an event start as its source; without that, every phase-1 test that builds an event-start relation would break on the new form rule rather than test what it tested;
   - two docstrings, and `TOOLS_SHA256`, retaken.

## ⚠️ For the controller

- **A proposal narrows a direct assignment.** `bracket_edges` counts open proposals, as dispatched ("any level"), and "the more specific replaces the general" ignores level. So a model's open unit-level proposal (unit 4 → summer party) takes unit 4 out of the operator's direct whole-mail assignment to XZ, before anyone approves it. Finding is not authority, but here an unconfirmed proposal removes something from a chronicle. Confirm that this is intended, or restrict replacement to edges at the same or a higher level.
- **Periods are ignored.** `bracket_edges` calls `Graph.relations()` without `at` (`core/members.py:85`), so a `part_of` or an assignment whose period has ended still counts. Decision 4 says "geltende Gewinner"; the report states that periods are ignored, but nothing decides it.
- **T2-a has consequences beyond `concerns`.** Read from the vocabulary, every kind that starts at `event` becomes an assignment. `in_circle` is meant to start at an event in phase 3 (`core/vocabulary.py:230-233`), and it would then feed `members` with circles as brackets. A retired kind that starts at `event` also needs a ruling: does it still count?
- **T2-b deviation.** A `units: null` assignment falls with a later unit erasure, which differs from the brief's literal "die des ganzen Events steht". It is ruled and tested. The report suggests telling the maintainer.
- **Help and tool descriptions** name `concerns` as the example, and `TOOLS_SHA256` pins that text. This is text only and consistent with the base vocabulary, but under T2-a's spirit the maintainer may want neutral wording.
- **`docs/explanation/graph.md:13`** still says assignments come in later phases. The report leaves this to Task 6, and the PR must not ship without it.
- I did not re-run the gates. The report's figures (2713 passed, 97.71 %, pyright 0) are as stated by the implementer.
