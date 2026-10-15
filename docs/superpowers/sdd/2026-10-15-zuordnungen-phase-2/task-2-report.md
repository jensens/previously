# Task 2 report

Status: done. Commit `fbdd05e` on `worktree-zuordnungen-2` (base `5f791e6`), not pushed.
Six gates green, run after the last edit; the outputs are below.

## What was built

1. **The start is a source (decision 3).**
   It is a rule of the **form**, in `core/graph.py`: `START_NOT_A_SOURCE` (:99), `covers(source, start)` (:469) and `_start_problem` (:493), which `_relation_problem` calls after `from`, `to` and the sources have been checked (:512).
   One source entry must cover the start, and `units: null` covers every unit.
   Because it is a form rule, `parse_claim` returns None for a payload that breaks it.
   So the fold drops a forged row, which can't stand in a place where the cascade wouldn't find it.
   `verify` reports it as `assertion has no valid form: the event a relation starts at must be among its sources`.
   A recollection with an event start is refused by the same rule, because a recollection has no sources.
2. **`sources_with_start(start, sources)`** (graph.py:479) is shared by the CLI and MCP.
   It appends the event start when no source names its event.
   When a source names the event but doesn't cover the start, it leaves the sources as they are, and the form refuses the claim; nothing is merged.
3. **`core/members.py`** (new): `PART_OF`, `CONCERNS`, `BracketEdge(subject, type, start: int | Source, to)`, `Members(brackets, events, excluded)` with `holds(event, seq)`, `bracket_edges(graph)` and `members(edges, bracket)`, following ruling P-2.
   The walk goes downward from the bracket over `part_of` edges that start at an entity, and it keeps a visited set.
   It reads only `concerns` edges that start at a `Source`; every other kind and start is ignored.
   The more specific replaces the general.
   `events[e]` is `None` when an edge of the whole event points into the set, and `excluded[e]` then lists the units whose own edges all point outside it.
   Otherwise `events[e]` is the frozenset of units whose own edges point in.
   The class docstring documents `excluded`.
   `bracket_edges` takes the edges from `Graph.relations()`: standing winners of every level, open proposals included, with questions and retractions left out.
   It ignores periods.
4. **CLI.** `relate TYPE --from-event EVENT[:SEQ,SEQ]` sits in a mutually exclusive group with `--from` (cli.py:3954), and the start is added as a source (:3194).
   The missing-option sentence now reads `--from or --from-event` (:3199).
   `relations`, `triage` and `classes sample` show the start as `event E` or `event E #3,4` (`_event_start_text` and `_start_text`, :3336 and :3344).
   `--subject N --retract` works on an assignment as on any relation.
5. **MCP.** `EventStartItem {event, units=None}` (server.py:570).
   `RelationItem.from` is `int | EventStartItem`, and the `sources` description says the start gets added.
   `_relation_claim` builds the `Source` start and calls `sources_with_start` (:2272).
   `write_record` records the event of an event start under `sources`, not under `ends` (:2443).
   The preview and triage line read `from: previously://event/N` or `…#unit-K` (read.py:1077).
   The `_WRITE_RELATION` description has one added sentence.
   `TOOLS_SHA256` was retaken: `553dad73f5890918477268800521b902e3b300900183d67074d9e5abb83f1ef7`.
6. **Docs.** `docs/reference/cli.md` covers the `relate` synopsis, `--from-event`, the source rule and its refusal, the start format in `relations` and `triage`, and the fact that the entity page doesn't list assignments.
   `docs/reference/mcp-tools.md` covers the `write_relation` event start, the `from` and `sources` fields, and the access-log keys `sources` and `ends`.
   The tutorial's test block was retyped from one green `uv run pytest` run: 2713 passed.
7. **Stale comments.** I fixed the three the Task 1 minor named: graph.py `RelationBody` docstring, graph.py `_end_problem` comment and vocabulary.py:230 (`in_circle`).
   I also fixed the docstring of the test `…closes_no_cycle` ("Phase 1 refuses") and `_graph_log` in test_cli ("id 12 … nine events", which is 13 and ten since Task 1).

## Where the event-start refusal was lifted, or where an event start is now handled (ruling P-1)

Lines are those of `fbdd05e`.

- `core/graph_write.py:776` `relation_visible`: the `isinstance(start, Source) → False` refusal is gone.
  Because the start is a source, the policy decides over the mail, and the docstring says so.
- `core/graph_write.py:274` `closes_cycle`: kept, with a comment; an assignment is no edge, and it closes no cycle.
- `core/graph.py` `Graph.reaches`: unchanged; it skips a `Source` start, which is correct for an edge between entities.
- `core/graph.py` `claim_payload`, `_body_of`, `_end_problem`, `_texts_of`/`claim_changes`, `conformance_problem` and `_ends_conformance`: these already handled a `Source` start (Task 1 covers conformance); only comments changed.
- `core/graph_write.py` `relation_ends`: unchanged (it lists entity ends only, which is correct).
- `core/verify.py`: no change needed.
  The form finding carries the new rule, `stands_on_erased` and `reconcile` read the start through the sources, and `_claim_rules` → `conformance_problem` was lifted in Task 1.
- `cli.py:3401` `_claim_label`, `:3465` `_relation_line`, `_claim_fields`: these now show `event E [#…]` in place of `(an event)`.
- `cli.py` `_marks`: unchanged; it already judges only the int ends, and conformance accepts an event start.
- `cli.py` `_cmd_relations --from`: unchanged; `--from ID` matches no event start, and the docs say so.
- `cli.py:3575` entity page: it skips assignments on purpose, with a comment and a docs line; `relations --type concerns --to ID` lists them.
- `cli.py` `_relation_claim` and `_relate_arguments`: `--from-event`, and the start as a source.
- `mcp_server/server.py` `RelationItem`, `_relation_claim`, `write_record`: see item 5.
- `mcp_server/read.py:1077` `claim_lines`: shows the start's URI; the `ThreadVerdict` docstring was updated (:849).
- `mcp_server/read.py:1181` `_relation_lines` (`list_entities` entity page): skips assignments on purpose, with a comment.
- `core/classes.py` `hit_rates` and `sample`: these never read `start`, so nothing changed (`classes sample` prints through `_claim_label`).

## Deviations

1. **The refusal carries the form prefix.** It reads `a statement has no valid form: the event a relation starts at must be among its sources`.
   The rule is a form rule, so it gets the prefix every form refusal gets, on the write path, in the preview and in MCP `_refuse_unseen`.
   `verify` prints `assertion has no valid form: …`.
   The contractual sentence is the constant itself.
   The reason: as a form rule, a forged row doesn't stand, and nothing else makes an assignment that can't be cascaded vanish from the graph.
2. **MCP `from` for an entity stays a bare integer** (`int | {"event", "units"}`), and not `{"entity": int}`.
   The current tool takes an int, `to` is an int, and changing the form would break every existing client call for no gain.
   If the controller wants `{"entity": int}`, that is a one-line model change and a retaken checksum.
3. **Cascade, middle clause.** The brief says that the assignment of the whole event stands when a unit is erased.
   The existing `stands_on_erased` (F §8) erases an assertion that cites a whole event when a unit of it is erased **after** the assertion.
   An event-level assignment needs a `units: null` source, so under the controller's third bullet it falls.
   The tests prove this:
   - mail erased: both assignments erased;
   - unit 3 erased: the assignment of `[3]` erased, the one of `[1,2]` stands;
   - `units: null` assignment: falls with a later unit erasure, and one written after the erasure stands.
   The brief's "die des ganzen Events steht" doesn't hold literally; the maintainer may want to know.
4. **`members` hard-codes `part_of` and `concerns`** as names (members.py), and doesn't read the vocabulary behavior `transitive`.
   Task 4 builds the edges from projection rows without a vocabulary.
   The map point "transitive declared, read by nothing" stays open.
5. Two sources of the same event that cover the start only together don't count; one entry must cover it, as decision 3 is worded.
   This is tested.

## Tests (new or changed)

- `tests/test_members.py` (new, 11 tests): the Markus example (members of XZ hold units 1–3 but not 4, the summer party only 4, the club 4 through `part_of`), assignment to both, upward and not downward, a cycle, ignored kinds and starts, an unknown event, and `bracket_edges` (levels, question, retraction, other kinds).
  It also holds the Hypothesis property: 400 examples over arbitrary `part_of` digraphs, cycles and self-edges included, with event and unit edges and noise edges, against an independent upward-walking oracle.
- `tests/test_graph.py`: the source rule (4 covering cases, 4 refused cases, recollection, an entity start as the control), `covers` and `sources_with_start`.
  The `relation` helper now cites an event start as its source.
- `tests/test_graph_write.py`: assignments written with `verify` clean, a start not covered (write and preview), the start checked as a source (missing event, missing unit, not an observation), a model assignment at its class level and a question with candidates, a retraction, and `relation_visible` for an assignment.
- `tests/test_cascade.py`: the three erasure cases (Review Focus 1).
- `tests/test_verify.py`: the forged assignment is a finding, and the covered one is the control.
- `tests/test_cli.py`: the Markus mail through `relate` (payloads, `relations` lines, `members` over `read_graph`, the entity page, `verify`), source kept, added or refused, a bad `--from-event`, a missing unit, a missing start, `--from` together with `--from-event`, a retraction, and a model's question answered with `answer`.
- `tests/test_mcp_server.py` (each test in both modes): write and confirm with the start added and the access record, a hidden and a missing mail giving one sentence (local control), a narrower source refused, a question in `list_triage` plus a retraction, and an assignment of a hidden mail absent from claude-code's triage but present in local-harness's.
  `TOOLS_SHA256` retaken.

## Mutations

Each mutation was measured red, and after each restore the suite was green again (the full run below).

| Mutation | Red | Stayed green (control) |
|---|---|---|
| `_start_problem` always None (rule removed) | 10: test_graph ×5, graph_write refusal, verify finding, CLI narrower/recollection, MCP narrower ×2 | 155 selected others, among them `covers`, the write tests, cascade |
| `members`: exclusion dropped (the more specific no longer replaces) | Hypothesis property, Markus XZ, the fixed example | 8 of 11 (cycle, other kinds, party, club …) |
| `members`: `part_of` walked upward | Hypothesis property, `test_part_of_carries_upward_and_not_downward`, club | 8 of 11 |
| `sources_with_start` never adds | 13: CLI ×4, MCP ×8, test_graph helper | 20 selected others |
| `relation_visible` with the phase-1 refusal back | graph_write assignment visibility, MCP triage ×2, MCP hidden-mail ×2 | 14 selected others |

## Gates (last run, after the last edit, at `fbdd05e`'s tree)

```
uv run ruff check .                 → All checks passed!
uv run ruff format --check .        → 137 files already formatted
uv run pyright                      → 0 errors, 0 warnings, 0 informations
uv run lint-imports                 → Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                    → 2713 passed in 291.60s; TOTAL 97.71%;
                                      core/graph.py, core/graph_write.py, core/members.py 100%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                    → exit 0; vale: 0 errors, 0 warnings and 0 suggestions in 50 files
```

The tutorial count was retyped from a green `uv run pytest` run (2713 passed in 289.24s).

## Concerns

- Deviation 3: the brief's cascade wording contradicts F §8 and `stands_on_erased`.
  I followed the controller's third bullet.
- Deviation 2: MCP `from` for an entity stays an int.
- `relations` lists only non-open winners, so a model's open assignment shows in `triage` and not in `relations --type concerns`; that is the existing behavior for every relation kind.
- Nothing in this task touches projections; `members` is pure and has no reader on the CLI or MCP yet (Tasks 4 and 5).
- `docs/explanation/graph.md:13` still says assignments come in later phases.
  I left the explanation pages to Task 6.

---

# Fix round 1 (review of `fbdd05e`; rulings T2-a, T2-c to T2-f)

Status: done. Commit `a6d358a` (on top of `fbdd05e`), not pushed.

## Signature changes (for Task 4)

```python
@dataclass(frozen=True)
class BracketKinds:
    hierarchy: frozenset[str]      # relation kinds with the behavior `transitive`
    assignments: frozenset[str]    # relation kinds whose `from` names `event`, minus GATE_TYPES

def bracket_kinds(vocabulary: Vocabulary) -> BracketKinds          # retired kinds count

@dataclass(frozen=True)
class BracketEdge:
    subject: int
    type: str
    start: int | Source
    to: int
    level: str                     # NEW: the level of the winner, by `level_of`

def bracket_edges(graph: Graph, vocabulary: Vocabulary) -> tuple[BracketEdge, ...]   # was (graph)
def members(edges: Iterable[BracketEdge], bracket: int, kinds: BracketKinds) -> Members  # was (edges, bracket)
```

- The constants `PART_OF` and `CONCERNS` are gone.
- Task 4 builds `BracketEdge` from projection rows, with `type` and `level` taken straight from `p_graph_thread`.
- Task 4 calls `bracket_kinds(read_vocabulary(...))` once and passes the result to `members`; that is the same decision `bracket_edges` makes for a graph.
- An edge is hierarchy when its kind is in `kinds.hierarchy` and its start is an entity.
  An edge is an assignment when its kind is in `kinds.assignments` and its start is a `Source`.
  A kind that does both is read by its start.
- Also new in `core/graph.py`: `rests_on(claim) -> tuple[Source, ...]`, the sources plus an event start with exactly its units.

## What changed

1. **I-1 / T2-a / T2-e:** `core/members.py` names no kind.
   - The hierarchy and the assignments come from `bracket_kinds`, as listed above.
   - The docstrings say "hierarchy" and "assignment" instead of naming kinds.
2. **I-2 / T2-f:** `rests_on` is used by the write path and the preview (the locked and read events plus `check_sources`, `graph_write.py`), and by `verify`.
   - In `verify`, `_standing` holds `rests_on(claim)`, so "names a unit its source does not have" and "stands on an erased source" cover the start's own units.
   - The cascade is unchanged: under a whole-event source, a unit erased later takes the assignment along through `stands_on_erased`, and a unit erased earlier is now refused at write time.
3. **T2-c:** a unit's own edge replaces its event's edge only at `direct` or `transitive`.
   An open own edge adds the unit wherever it points and removes nothing.
4. **T2-d:** periods are ignored.
   The module docstring and the `Members` and `bracket_edges` docstrings say so, and a test pins it.
5. **M-1:** `_claim_fields` spells an event start the way `claim_changes` does (`event 1 units 2`).
   Note: that branch has no reachable caller today, because `_claim_fields` serves only `entity --history`, so no test exercises it.
6. **M-2:** the property now also compares `brackets`, `events` (the `None` case, exact sets, absent keys) and `excluded` with the oracle.
7. **M-3:** `START_NOT_A_SOURCE` now sits after the `MIN_CANDIDATES`/`MAX_CANDIDATES` block.
8. **Docs:**
   - `cli.md` and `mcp-tools.md` say that the start's units are checked even under a whole-event source.
   - The tutorial test block was retyped from one green run (2724 passed).

## New tests

- `tests/test_members.py` (19 tests, was 11):
  - the base kinds;
  - a second transitive kind (`subproject_of`) makes a second hierarchy;
  - another event-start kind (`mentions`) is an assignment;
  - a hand-written `in_circle` starting at an event feeds nothing (with `concerns` as the control);
  - retired kinds still count;
  - a transitive unit edge replaces the event's edge;
  - a proposal adds and doesn't remove (T2-c);
  - `bracket_edges` carries levels;
  - an ended period still counts (T2-d);
  - the property, now with levels and the full comparison.
- `tests/test_graph_write.py`: the start's units are checked under a whole-event source, for a missing unit and for a unit erased before, in the write path and in the preview, with a present unit as the control.
- `tests/test_verify.py`: a forged assignment of a missing unit under a whole-event source is a finding (with the control), and so is one of a unit erased before it.
- `tests/test_cli.py`: `--from-event 1:9 --source 1` is refused as `event 1 has no unit 9`.

## Mutations

Each mutation turned tests red, and each restore made them green again.
Command: `uv run pytest tests/test_members.py -q` (I-2: `tests/test_verify.py tests/test_graph_write.py -k "start or erased_before"`).

| Mutation | Red | Green (control) |
|---|---|---|
| `bracket_kinds` names `part_of` | second-transitive, retired | 17 |
| `bracket_kinds` names `concerns` | mentions, retired | 17 |
| `GATE_TYPES` not excluded | in_circle test | 18 (`concerns` in the same test passes before it fails) |
| level ignored (`firm = True`) | T2-c proposal test, property | 17 |
| more specific no longer replaces | property, fixed example, Markus XZ, transitive-replaces | 15 |
| hierarchy walked upward | property, upward-not-downward, period, second-transitive, club | 14 |
| `relations(at=today)` in `bracket_edges` | period test | 18 |
| empty frozenset kept in `events` (M-2) | property | 18 |
| empty entry kept in `excluded` (M-2) | property, proposal, both | 16 |
| `rests_on` returns the sources only (today's code, I-2) | graph_write start-units test, both verify tests | 4 (start-as-source tests) |

## Gates (after the last edit, tree of `a6d358a`)

```
uv run ruff check .                 → All checks passed!
uv run ruff format --check .        → 137 files already formatted
uv run pyright                      → 0 errors, 0 warnings, 0 informations
uv run lint-imports                 → Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                    → 2724 passed in 294.54s; TOTAL 97.71%;
                                      core/graph.py, graph_write.py, members.py, verify.py 100%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                    → exit 0; vale 0 errors, 0 warnings and 0 suggestions in 50 files
```

The named files on their own (members, graph, graph_write, verify, cli, mcp_server, docs_references): 1251 passed in 168.59s.

## Not done, or left open

- The CLI help, the MCP descriptions and `TOOLS_SHA256` still use `concerns` as the example; T2-f allows this, and the checksum is unchanged in this round.
- `docs/explanation/graph.md:13` is left to Task 6, as before.
