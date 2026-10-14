# Final review: Zuordnungen phase 1 (01eb4ac..9967268)

**Verdict: ready to merge after the fix wave.**
Critical 0 · Important 2 · Minor 12 (plus the F-a/T7-a items already in the wave).

## How this was reviewed

The source diff was read in passes, mostly from the tree at HEAD because most of the files are new:

1. `core/graph.py`, `core/graph_write.py`, `core/classes.py` and `core/vocabulary.py` were read in full.
2. The diffs of `core/verify.py`, `core/assertions.py`, `core/action.py` and `pyproject.toml`.
3. MCP: the `confirm.py` and `render.py` diffs, `server.py` lines 500–960 (items, header, `Service.answer`), 1245–1360 (`approval_write`, `rejection_write`) and 1500–2215 (every graph method), and `read.py` lines 425–545 and 835–1446.
4. CLI: approve, reject, entity, relate, triage, status, answer and vocabulary apply (`cli.py` 1908–1942, 2490–2620, 3003–3230, 3610–3705).
5. The task reviews, re-reviews and the ledger; the spec §7.4–§7.6, §9.3 and the phase-3 acceptance points 12–17; `docs/explanation/graph.md` in full; the new map entries; and the tool and command counts on the pages.

I did not run the suite, and I wrote no scratch test.
The machine rebooted during the review, and no scratch file had been made before that.
I measured these by command, against the project configuration:
- `ruff --select T201 … --statistics` on `cli.py`;
- the `contract/store.py` census for `core` and for `mcp_server`;
- `grep` for removed lines in the existing tests;
- the page counts.

The coordinator's measurements at 10,000 relations, received during the review, are weighed under I2.

---

## Important

### I1. An MCP client can make a `circle` or a `member_of` direct, through `write_approve` or `write_triage_answer`

**Where.**
- `src/previously/mcp_server/server.py:1782-1835` (`graph_approval_write`) and `:1877-1931` (`triage_answer_write`). Neither looks at `body.type`.
- `core/graph_write.py:343-344`: `_levelled` passes an approval through unchanged.
- `core/graph.py:699`: `conformance_problem` refuses a gate kind only when it is *transitive*.

**What happens.**
1. A model writes an open `member_of` (person → circle), or an open `circle`, through `write_relation` or `write_entity`. That is allowed, since `Classes.level` gives open for `GATE_TYPES`.
2. The same client then calls `write_approve` with that id.
3. The result is a direct `member_of` whose author is `model:<client>`, with `approves` set.

The log cannot tell this approval from the operator's `previously approve` of the same proposal: both copy the model as author, and both are `direct`.
Only a cross-reference to the `written` ids of an `mcp_access` entry separates them.
No test covers a gate kind over MCP (grep of `tests/test_mcp_server.py`).

**Why it matters.**
- **The spec.**
  - Z §7.6.1 says "`member_of` und `in_circle` gelten nur `direct`".
  - Z §9.3 says "nur direct, nur vom Betreiber".
  - Phase-3 acceptance 14 says "keine Klasse, **kein Modell** erreicht sie".
  - Plan decision 6 says "ein Modell schreibt sie nie anders als `open`".
- **The ask mark is advisory.** The mark is only a hint to the client. Claude Code offers "Yes, and don't ask again" (connect-claude-code-and-vibe.md:184), and Vibe's handling is unmeasured. Once a person has said "don't ask again" for `write_approve`, a model can make memberships direct on its own.
- **The log keeps it.** The gate does not read the graph in phase 1, so nothing leaks today. But the log is permanent, and every direct `member_of` written this way in phases 1 and 2 is something phase 3 must either trust or work out to distrust.
- **A page claims the opposite.** `docs/explanation/graph.md` §graph-gate-kinds says "a model writes them `open` and never otherwise", and that is not true of the code.

**Proposed fix.**
- `graph_approval_write` and `triage_answer_write` refuse a version whose `body.type` is in `GATE_TYPES`, with one sentence, for example: `event N is of a kind the gate reads; the operator approves it on the command line`.
  - The client already sees the thread, so the sentence reveals nothing.
  - `write_reject` may stay as it is, since a rejection makes nothing stand.
- Add a test measured red without the guard, with a green control: a `project` approval in the same call shape.
- `mcp-tools.md` (sections `write_approve` and `write_triage_answer`) and `graph.md` §graph-gate-kinds then say it, and the claim on the page becomes true.
- An alternative that keeps the approval needs a ruling. It would also need a way for phase 3 to tell an MCP approval apart in the log, which today exists only through `mcp_access`.

### I2. Every MCP call, the unit-5 tools among them, pays a full fold of the graph for the header

**Where.**
- `server.py:926-929`: `Service.answer` runs `read_graph` and `objections_seen` before every body, including `whoami`, `get_event`, `list_obligations` and `policy_gaps`.

**The numbers** (the coordinator's measurements, medians):

| Call | 2,000 relations | 10,000 relations (5,000 entities) |
|---|---|---|
| `whoami` | 0.10 s | 0.52 s |
| `list_entities` | 0.28 s | 1.72 s |
| `read_graph` alone | — | 0.47 s |

The growth is linear, so 100,000 relations come to about 5 s for every call of every tool.

**Why it matters.**
- Before this branch the unit-5 tools never read the graph. This is a regression in existing behavior, and its cost does not depend on whether the client uses the graph at all.
- Claude Code and Vibe call tools in bursts.
- The measurement decides the phase-2 projection (plan decision 14), but nothing obliges the header to pay for a fold on every call until then.

**Proposed fix** (contained, in `Service`).
- Memoize the folded graph by the id of the tip read in the call's snapshot.
- Memoize the objection count by `(tip id, client name)`.

Why the tip is a sound key: everything the graph and the count depend on moves the tip in the same transaction.
- Assertions, vocabulary and class events are appended events.
- Policy events are actions.
- An erasure writes its redaction event in the transaction that nulls the payloads (`core/redact.py` module docstring).

The tip id comes from the snapshot, so a cached fold always matches the snapshot it is used in.

Tests:
- an erasure between two calls changes what the second call reads (measured red with a cache keyed on something that does not move);
- a policy change changes the count;
- a counting-store test that shows the second call does not fold.

⚠️ The fix should confirm one assumption: that neither `fold_graph` nor `decide` reads the clock (I found no `now` in either). If the wave cannot carry this, the alternative is a ruling that accepts the cost for phase 1, with the 10,000-relation figures on `graph.md` and in the map, and a release note. I recommend the fix, because the cost lands on tools that have nothing to do with the graph.

Related, folded into the same item:
- `read.py:1000-1011` `graph_rejections` reads and parses every assertion again for each `write_reject` of a graph version. It could take the rejections from the fold the call already has.
- `graph.md` §graph-cost promises figures "when that review is done". The fix wave puts the 10,000 (and, when it lands, the 100,000) figures there and in the map. Ruling T7-a's wording minors belong to the same edit.

---

## Already in the fix wave (rulings F-a and T7-a; not re-derived)

- `vocabulary apply --base` adds only missing base kinds, and never retires or overwrites a kind.
- The handoff and the club how-to stop telling the operator to re-run `--base` blindly.
- The three T7 wording minors: the header cost, "quadratisch" → "überlinear", and the `graph.md` cost section.

One observation for that change: `_cmd_vocabulary_apply` (`cli.py:1908-1929`) shows the differences it computed in one transaction. `apply_vocabulary` then recomputes them under the tip, and it writes whatever differs *then*. A vocabulary event that falls between the two gets written over without being shown. This is the same pattern as `policy`, and it is harmless with one operator, so the map is the right place for it. But the new `--base` path should not widen it: compute "missing kinds" inside `apply_vocabulary`'s transaction, not in the CLI.

---

## Minor

**M1. A forged transitive gate kind counts as transitive in the fold.** `core/graph.py:737-748` `level_of`.
- Task 4's ⚠️ was never placed: not in the map, not fixed.
- `level_of` trusts `under` for a `circle`, `member_of` or `in_circle` row that came around the write path. Only `verify` reports it.
- Fix now, one line: a transitive version of a `GATE_TYPES` type counts as `OPEN`. This is the same fail-safe as an unknown class.
- Test: a hand-written transitive `member_of` under a class in force gives `level_of == OPEN`, with a `project` control.

**M2. `verify` does not report an approval of an overtaken proposal, and the fold accepts one.**
- The write path refuses it (`graph_write.py:423-427`).
- `GraphFold.add`/`_approvable` (`graph.py:940-949`) accepts it, and `verify` `_approval_reason` (`verify.py`, `_Claims`) does not check it.
- A forged approval of a proposal older than the newest direct version becomes the latest direct, and it silently replaces the winner.
- Fix: the same `newer > approves` check in `_approval_reason`, with a finding sentence, and a red/green test.
- The fold may stay as it is, as it does for obligations. Add the check to `_Claims`' list of what the write path refuses.

**M3. Rules the write path enforces that `verify` does not.** These are the gaps I found. Everything else is listed under *Consistency* below.
- Vocabulary `refusal`, `core/vocabulary.py:520-536`: a relation kind or a `ref` naming a kind that does not stand, a retirement of a needed kind, and a built-in reshaped. `verify` checks the form only (`vocabulary_problem`).
  - The read path neutralizes the built-in case (labels only).
  - The other cases need a forgery and do no harm, since `conformance_problem` refuses ends of kinds that do not stand.
  - `verify` already folds the vocabulary in chain order (`VocabularyFold`), so it could run `refusal(before, [spec])` per event.
- Class `_refusal`, `core/classes.py:403-428`: a type that does not stand, and an acyclic type. `verify` checks the form only.
  - Both are neutralized on read (`_covering` checks acyclic, and `conformance_problem` checks the kind).
  - Proposal: say so in the `_Claims` docstring now, and put the two `verify` checks in the map. A docstring that lists what `verify` does not hold is cheaper than a red build later.

**M4. Open (proposed) entities count as ends that stand.** `graph_write.py:181-206` `EntityTypes` and `graph.py:854-860` `entities()`.
- A direct relation by the operator, or an approval, can point at an entity that only a model proposed. That includes a direct `member_of` to a proposed `circle`.
- `relations()` likewise returns open winners (`graph.py:867-870`, documented there).
- Harmless in phase 1. Phase 2 (`chronicle --in`) and phase 3 (the gate) must filter both ends and the edge by `level_of == DIRECT` (gate) or by a stated level.
- Map, under phase 3, with the sentence that the gate reads only direct ends.

**M5. Built-in kinds live in code, so `verify` holds old claims against today's built-in spec.** `vocabulary.py:187-215`, and `VocabularyFold.add:448`, which replaces a built-in's spec with the code's at every position.
- When phase 3 gives `member_of` other `from` kinds (address, domain) and `in_circle` an event start, every earlier `member_of` is re-judged by the new code.
- If phase 3 drops `person`/`organization` from `from`, phase-1 memberships become `verify` findings.
- Map, under phase 3: built-in connections may only widen, or the built-in spec gets a version.

**M6. `docs/explanation/graph.md:189` is wrong about relations.**
- The page says "otherwise the client gets a placeholder, as for any other content".
- A hidden relation gets no placeholder anywhere. `mcp-tools.md:162` and `:443` say so correctly, and `read.py` `_relation_lines` and `triage` drop it.
- Fix the sentence. Ruling T6-b is the reason.

**M7. A counted claim: `contract/store.py:44-46`.**
- The page says "`grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py` names the seven the server calls … counted on 2026-10-12".
- Measured now, it names **eight**: this branch added `log.read_by_kind` (`read.py:1007`, `graph_rejections`).
- If I2's fix makes `graph_rejections` use the fold, the count goes back to seven and the sentence stands.
- Otherwise retype it with the date, as the docstring did for six → seven.
- The `core` count, fifteen methods, still measures fifteen. "Twelve modules that day" is dated and true for its day; today the command lists fifteen modules, but the claim names its day, so it needs no change.

**M8. Two copies of triage, approval and answer, one per surface.**
- `cli.py:3610-3632` `_waiting` ≡ `mcp_server/read.py:1334-1358` `waiting_versions`.
- `cli.py:2511-2525` `_approval_of` ≡ the `replace(...)` in `server.py:1824-1832`.
- `cli.py:3683-3693` (answer) ≡ `server.py:1906-1916`.
- Z §7.5 wants `status` and the MCP header to show the same, and two sort routines will drift.
- Fix: move `waiting_versions`, `approval_of(thread, version, reason)` and `answer_of(question, choice, reason)` into `core/graph_write.py` (or `core/graph.py`), used by both. This is mechanical, and the existing tests hold it.

**M9. Three copies of the identifier and author rules, and one of them differs.**
- `_IDENTIFIER` exists in `vocabulary.py:84`, `graph.py:102` (held against vocabulary by a test) and `classes.py:73` (held by no test).
- The author rule exists in `assertion.py` (private), `graph.py:255-268` (a copy, tested) and `classes.py:125-134`. The class copy uses `isprintable()`, which also refuses Co, Cn and Cs, where the others refuse Cc, Cf and U+2028/9.
- A client named with a private-use character can write claims, but can get no class.
- `classes.py:72` `_MODEL_PREFIX` re-declares `assertion.MODEL_PREFIX`.
- Fix: export `IDENTIFIER` and `is_model_author` once (from `core/assertion.py` and `core/vocabulary.py`) and import them. That also makes the equivalence tests in `test_graph.py` unnecessary.
- If the wave is full, at least import `MODEL_PREFIX` and the graph's author check in `classes.py`.

**M10. Dead code and duplicates.**
- `Graph.reaches(extra=…)`, `graph.py:887` and `:915-916`, has no caller in `src` since ruling T4-b replaced it with the batch fold. Only tests use it. Remove it, and the tests that exercise it.
- `server.py:1972-1977` `_shown_of` and `:1992-1998` `_graph_shown` have identical bodies. Use one helper over a small protocol with `.delivered` and `.rules`.
- `graph.py:1093-1141`, `read.py:1031-1042` and `cli.py:3230-3246` each have their own `_period_text`/`_value_text`.
  - The first two print the same.
  - Keep the one in `graph.py` public, and import it.

**M11. The `ThreadVerdict` docstring claims more than the code does** (deferred Task 6 minor). `read.py:841-851` says a relation that starts at an event "has no `blocked` either", but `verdict()` does not clear `blocked`. Reword it. Nothing reads it for relations.

**M12. `entity … --state retracted` without `--subject` writes a first version that is already retracted** (deferred Task 5 minor). `relate` refuses the same thing (`cli.py:3124-3127`). Add the symmetric guard in `_entity_claim` and its test, and the two commands agree.

### Size and names

- `cli.py` is 4,274 lines, `server.py` 3,036 and `read.py` 1,446.
- In `cli.py` the graph commands are one contiguous block (about 2,995–3,950), which could become `previously/cli_graph.py` without touching behavior. Not for this wave; I put it in the map.
- No name collisions are a hazard. Both `TRANSITIVE` constants carry a comment (`graph.py:78-80`), the `Claim`/`Statement` split carries its reason, and the triage section names are consistent.

---

## The security boundary, across tasks

### Gate kinds: direct-by-operator or open?
Not in every case. Classes cannot reach them (`_types`, `_covering`, the transitive refusal in `conformance_problem`, with a test at each layer). The CLI writes `human:operator`.
- **Exception, I1:** a model's proposal approved over MCP.
- **Exception, M1:** a forged transitive row counts as transitive in the fold.
- `in_circle` can't be written at all in phase 1, since `from_` is `()`.

### A model becomes direct only through an approval?
Yes, through `write_approve` and `write_triage_answer`, both carrying the ask mark (`server.py:2777`, `:2796`).
- `EntityItem`/`RelationItem` are `extra="forbid"` and carry no author, level, `under`, `contests` or `approves`.
- `_entity_claim` and `_relation_claim` set `model:<client>`, and `_levelled` decides the level.
- `claim_problem` refuses a direct model version without `approves`.
- A confirmation is held to the sealed `Decided` values.

The weakness is that the ask mark is advisory; that is unit 5's accepted risk, and I1 is where it matters more.

### What a client learns about withheld content
I checked each channel.

| Channel | Result |
|---|---|
| Header count | Seen threads only, where every version's sources and every end must be seen. |
| Refusal sentences | `_refuse_unseen` runs first, with the visible `entity_types`, and gives the sentence of a missing subject, end or ref. |
| Sources | `event_hidden` is checked first. |
| Approve and reject | The ids of hidden and missing proposals take the same path and get the same sentence. The mixed-call refusal is asked of visible obligations only. |
| Cycles | A model's open version is never cycle-checked (T6-a). The residual is one bit behind the ask mark, and it is documented on `mcp-tools.md:680-681` and `:698-699` and in the map. |
| Triage | Visible threads only, with no placeholders (T6-b). |
| `list_entities` | A placeholder for each hidden entity that has a winner. |
| Ids | Assertion ids were already nameable through `get_event` ("not an observation"), so no new channel. |
| Previews and labels | They name ids of the visible thread only. |
| Class and level | Depend on the client's own class and the visible thread. |
| Hit rate and sample | CLI only, never over MCP. |

A weak residual remains, and I record it without a finding: a hidden entity's placeholder in `list_entities` disappears when its last proposal is rejected (`read.py:1311`, a thread with no winner is skipped). That is one bit about activity on a hidden thread, the class of signal T6-b removed from triage. Obligations behave alike, so it goes to the map with T6-b's reasoning.

### The gate is untouched?
Yes. `core/decide.py` is not in the diff. Its new callers are:
- `graph_write.claim_decisions`, which calls `decide(..., source="recollection")` and `assertion_decisions`;
- `read.GraphView`, through `claim_decisions`.

Both feed only the visibility of graph claims (plan decision 12). No class or vocabulary value reaches `decide`.

---

## Consistency: write path, `verify`, fold

| Rule the write path enforces | `verify` | Note |
|---|---|---|
| Form (`claim_problem`) | ✓ | |
| Canonical payload | ✓ (hash) | |
| Batch: empty, size, one handle | — | Not knowable from rows; docstring says so |
| Source exists, is an observation, not erased, units present | ✓ | shared source checks; "source before it" |
| Operator claim is direct | ✓ `_claim_level` | |
| Model after a direct winner becomes an objection | ✓ | |
| Transitive only under a covering class in force | ✓ `covers` | any covering class, not the highest; fine |
| Question and answer outside candidates become open | ✓ `_claim_rules` | |
| Subject names a thread of the same kind | ✓ | erased subject accepted (cannot date the erasure) |
| Approval: names a version, not direct, unanswered, `takes_proposal`, sources | ✓ | |
| Approval: not overtaken by a newer direct version | **✗** | M2 |
| Vocabulary conformance, retired kind on a new thread | ✓ same function | |
| Answer must name a candidate (direct) | ✓ | |
| Cycle rule | ✓ same function, `level_of` | |
| Rejection of a graph version: not direct, unanswered, sources | ✓ `rejection_reason` | |
| Visibility of ends, subject, sources (MCP) | — | depends on the policy at call time; not a log invariant |
| `expect` (`Decided`) | — | session state |
| Vocabulary `refusal` (references, built-ins, retirements) | **✗** | M3; neutralized on read |
| Class `_refusal` (types that stand, acyclic) | **✗** | M3; neutralized on read |
| First version already retracted | — / — | neither enforces it; M12 makes the CLI agree |

The fold skips what the write path refuses, except the overtaken approval (M2) and a forged transitive gate kind (M1).

## Unit 5 unchanged

- `git diff 01eb4ac..HEAD` on `tests/test_assertions.py`, `tests/test_cli.py`, `tests/test_confirm.py`, `tests/test_verify.py`, `tests/test_cascade.py` and `tests/test_render.py` removes **no** line.
- `tests/test_mcp_server.py` removes only:
  - `TOOLS_SHA256`;
  - the ask-mark test (renamed, extended from two tools to three);
  - nothing else. The INSTRUCTIONS substring list was only extended.
- `test_action.py` and `test_docs_references.py` change only the pinned set of known actions.

In the code:
- `assertions.py` keeps the order (sources, then references) and the sentences.
- The graph lookup in `_check_rejection` runs only where unit 5 already refused.
- `_repeated` now filters on `KINDS`. That is a narrowing, so a graph batch can't answer an obligation handle.
- `approval_write` and `rejection_write` go to the graph branch only for ids that name no obligation version, and fall back unchanged.

The one behavioral change on unit-5 tools is the header suffix (specified) and its cost (I2).

## Design against later phases

- **`RelationBody.start: int | Source`.** This is sound. The form admits `{"event","units"}`, and `conformance_problem` refuses it with a phase-2 sentence. `reaches`, `closes_cycle`, `relation_ends` and `relation_visible` all skip it.
  Phase 2 changes `conformance_problem` (the refusal and `_ends_conformance`'s `int` cast), `EntityTypes`/ends, and `relation_visible` (which returns False for any Source start).
  Map it with that list, so phase 2 does not have to rediscover it.
- **M4** (open ends and open edges) and **M5** (built-ins in code, judged retroactively): phase 3.
- **`RelationBody.to`** is always an entity. `in_circle` (event → circle) has its event at `from`, so this holds.
- **Approval classes keep `under` as the newest event id per name** (T3-a). A class *renamed* in the future would orphan its versions, and they would count as open. That is fail-safe. Map it only if renaming is ever planned.

## Counted claims, measured

- **T201.** `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py --statistics` gives **96**, and `pyproject.toml` says ninety-six twice. The narrative adds 5 + 15, which is 81 + 15 = 96. ✓
- **`contract/store.py`.** `core` uses fifteen methods, measured 15 ✓. The `mcp_server` count says seven and measures **eight** (M7).
- **Tools.** `TOOLS` has 15 entries ✓. `mcp-tools.md:5`, `README.md:89` and `server.py:4` say fifteen ✓. `connect-claude-code-and-vibe.md:134-137` says ten → fifteen, dated and correct.
- **Commands.** `cli.md` says thirty-four, held by `test_docs_references` against `COMMANDS` ✓.
- **`graph.md` figures.** They are the dated Task 4 and Task 6 measurements, labeled as `verify` and header ✓. The 10,000 figures are now available and belong there (I2).

---

## Triage of the deferred minors in the ledger

| Ledger line | Decision |
|---|---|
| T1: `_text` uses `isprintable()` (refuses NBSP in labels) | **Map.** Stricter is safe. Fold it into M9's shared rule if the wave touches it. |
| T1: retiring `person` while built-in `member_of` names it | **Map** (already there). Phase 3 rewrites `member_of`'s `from`; see M5. |
| T1: a ref to a relation kind is a write-time refusal, not a form error | **Map**, with M3 (verify's vocabulary checks). |
| T1: `Vocabulary.label` takes one language | **Closed.** `display_label` (ruling T5-a) does the default step, used by the CLI and MCP. |
| T1: the "never raises" test asserts None-or-str | **Drop.** Its purpose (no exception) is real. |
| T1: `test_wheel.py` builds twice | **Map**, low. Test time only. |
| T3: hit rate counts v1 as corrected when a later transitive v2 is approved | **Map** (already there). |
| T3: tie-break "oldest" by the newest event id per name | **Map** (already there). |
| T3: cosmetic test comment and docstring ref | **Drop.** |
| T4: a direct standing relation with candidates refused on a thread with a pending question | **Close and strike from the map.** The case is unreachable: `_to_problem` (`graph.py:482-483`) already refuses candidates on any non-open version as a form fault. |
| T5: the type column shows the label | **Map** (already there; `cli.md` documents it). |
| T5: `entity … --retract` without `--subject` | **Fix now** (M12). |
| T6: `mcp-tools.md` names the cycle residual under `write_approve` only | **Closed.** `mcp-tools.md:680-681` names it under `write_triage_answer` too. |
| T6: `ThreadVerdict` docstring about `blocked` | **Fix now** (M11). |
| T7 three minors (→ final wave) | **Fix now**, per ruling T7-a, with I2's figures. |

**New map entries this review asks for:**
- M3 (vocabulary and class checks in `verify`);
- M4 (open ends and edges before phase 2 and 3);
- M5 (built-ins in code);
- the phase-2 list for a Source start;
- the `list_entities` placeholder bit;
- the stale-vocabulary window in `vocabulary apply`;
- the split of `cli.py`.

Also: if M1 is fixed now, nothing about it goes to the map; if it is not, it goes there under phase 3.

## Fix-wave order (suggested)

1. I1 and M1: gate kinds, the safety items.
2. F-a/T7-a, then I2 with the figures on `graph.md` and in the map, M6 and M7 (one docs pass).
3. M2 and M12, each with red/green tests.
4. M8, M9 and M10, mechanical, with the existing tests as the net.
5. M11 and the map entries.

## ⚠️ Not settled

- **I2's cache.** It rests on "everything the count depends on moves the tip, in the same transaction". I confirmed this for erasures (`core/redact.py`) and appended events. I did not confirm that `decide` and `objections_seen` read no clock. The fix must test it.
- **`cli.py` listings.** I did not read `cli.py` 3230-3590 (listing lines, the entity page) or the classes commands (3716-3830). Task 5's review covered them, and nothing in the cross-task questions led there.
- **The `server.py` tool descriptions** (lines 1-450) and `INSTRUCTIONS`: I read only the `INSTRUCTIONS` text as quoted on `mcp-tools.md:17`. With I1 fixed, its sentence "and so does write_triage_answer for a question" stays true.
- **Whether the ruling-citation census** (`ruling (P|T…)`) resolves for the new labels: the ledger ships with the final review per the map, so the labels resolve then. I did not run the census.

---

## Final fix wave

One wave, base `9967268`, commits `1f802ef`, `b75af5e`, `1b5fbf4`, `22d571e`, `8613d6c`, `bf41e0a`, `c120539`, `992029c`.
Every mutation below was made in the working tree, measured, and reverted from a copy; none was committed.

### F-a / T7-a — `vocabulary apply --base` (`1f802ef`, docs `22d571e`)

- `core/vocabulary.py`: `missing_kinds` (kinds of the base the log does not hold at all; a retired kind counts as held) and `differing_kinds`; `apply_vocabulary(..., add_only=False)`. With `add_only` the set to write is computed inside the write transaction, under the tip, as the review asked, so `--base` does not widen the stale-vocabulary window.
- `cli.py`: `--base` prints `add` lines for the missing kinds, then a `differs` line per kind the base holds in another form, with attribute lines (log value, base value), then the sentence `--base changes no kind the log holds; to take a difference, edit the output of `previously vocabulary show` and apply that file`. Nothing missing: `nothing to change`, exit 0, no question. `apply FILE` is unchanged, retiring included. The help of `--base` says what it does.
- Tests: `test_adding_the_base_writes_only_the_kinds_the_log_does_not_hold` (log with the operator's own `team`, `project` relabelled, `post`/`holds`/`post_in` missing: writes exactly the three, keeps `team` and the label, reports `project`), `test_adding_the_base_keeps_a_kind_the_operator_retired`, control `test_applying_the_base_as_a_whole_file_still_retires_and_changes`; CLI `test_vocabulary_apply_base_after_an_update_adds_and_names_what_differs`.
- Mutations: `add_only` falling back to `differences` in core → 3 red (the two core tests, the CLI test); controls green (whole-file control, the existing empty-log `--base` CLI test). CLI passing `add_only=False` → the CLI test red.
- Docs: `adapt-the-vocabulary.md` "After an update" (run `--base`, it's safe; take a `differs` change with show → edit → apply FILE; FILE retires what it leaves out), `keep-a-club-and-its-offices.md`, the handoff (safe after an update; still the operator's step, not a job, because the `differs` lines are for a person), `reference/cli.md` (the output and the sentence), `reference/vocabulary.md`.

### F-b + M1 — gate kinds (`b75af5e`, docs `22d571e`)

- `server.py`: `_refuse_gate_kind` in `graph_approval_write` (after the visibility check, before the question check, inside the loop that runs before any write) and in `triage_answer_write` (after the "no question that waits" check). Sentence: `event N is of a kind the gate reads; a circle or a membership is approved on the command line`. `write_reject` unchanged.
- `core/graph.py` `level_of`: a transitive version of a `GATE_TYPES` type counts as `OPEN`.
- Tests: MCP `test_a_membership_a_model_proposed_is_not_made_direct_over_mcp` (both modes; a model proposes `member_of` and asks a `member_of` question; both calls refused, assertion count unchanged; control in the same test: a `holds` proposal approved the same way works); CLI `test_approve_makes_a_membership_a_model_proposed_direct_on_the_command_line`; `test_a_forged_transitive_version_of_a_gate_kind_counts_as_open[holds-control|member_of|circle]`.
- Mutations: guard a no-op → MCP test red in both modes (`write_approve` wrote assertion 47); only the triage guard removed → red (the answer wrote assertion 48); the `holds` control and the CLI test green. Gate line removed from `level_of` → `member_of` and `circle` red, `holds-control` green.
- Docs: `graph.md` §graph-gate-kinds (why: the ask mark is advisory, "don't ask again", the log can't tell the approval from the operator's, phase 3 would inherit it; the fold's fail-safe), `mcp-tools.md` (`write_approve`, `write_triage_answer`, the error list). The page's claim "a model writes them `open` and never otherwise" is now true of the code. The handoff names it under "The gate is untouched".

### F-c — the cost (`22d571e`, `bf41e0a`, `c120539`)

No code change. `graph.md` §graph-cost now has: the 2,000 / 10,000 table (median of three, 2026-10-14: `read_graph` 0.08 / 0.47 s, `entities` 0.10 / 0.53, `relations --at` 0.10 / 0.54, one write 0.08 / 0.47, `verify` 0.62 / 2.77, MCP `whoami` 0.10 / 0.52, `list_entities` 0.28 / 1.72); the confirmed 100,000 figures (fixed checkout of `9967268`, i7-11370H: `read_graph` 7.35 s median, single runs `whoami` 7.69 s, `list_entities` 23.7 s, with 20 objections 7.33 / 24.2 s, `entities` 7.59, `relations --at` 7.50, one write 7.34, `verify` 135 s); that every MCP call pays the fold and `objections_seen`, the reason a tip-keyed cache doesn't help, the judgement (carries at 10,000 with `list_entities` above a second; nothing carries at 100,000; `verify` acceptable daily), and that phase 2 needs a projection or an incremental fold before the data grows past the pilot. `verify` over `part_of` alone (chain 0.84 / 2.34 / 14.84 s at 1,000 / 2,000 / 5,000 edges, tree 0.78 / 2.10 / 13.05, chain of 10,000 78.6 s) replaces Task 4's two chain figures; Task 4's `post_in` figures and Task 6's entities-only header figures stay beside them, dated. The map (*Zuordnungen*) and the handoff carry the same, German in the map. The `_Claims` docstring keeps Task 4's dated figures and points at §graph-cost.

### F-d — minors (`1b5fbf4` unless noted)

- **M2:** `_Claims._approval_reason` reports `approval of a proposal that the direct version N overtook`; `_Claims` docstring lists it. Test `test_an_approval_of_a_proposal_a_direct_version_overtook_is_a_finding` (control in the test: an objection after the direct version, approved through the write path, no finding). Mutation check off → red; control green.
- **M6:** `graph.md` no longer claims a placeholder for a hidden relation (`22d571e`).
- **M7:** `contract/store.py`: measured with its own command, the MCP server calls **eight** (`begin`, `observations`, `read`, `read_by_kind`, `snapshot`, `source_keys`, `tip`, `units_by_event`); the docstring says eight, names `read_by_kind`, dated 2026-10-14. Rechecked: `core` count 15 ✓ (unchanged), modules naming `LogStore` 15 today (the dated "twelve that day" kept, a dated sentence for fifteen added), protocol declares 16 ✓.
- **M9:** `author_problem` public in `core/assertion.py`, `is_identifier` public in `core/vocabulary.py`; `classes.py` and `graph.py` use them, their copies (and `classes._MODEL_PREFIX`, `graph._LANGUAGE`, which now uses `is_language_tag`) are gone. Real difference fixed: the class rule used `isprintable()` and refused a private-use character a claim takes. Tests `test_a_class_takes_the_authors_a_claim_takes` (10 authors), control `test_the_class_author_cases_fall_on_both_sides`, `test_a_class_is_named_by_the_identifiers_a_kind_is_named_by`. With the old class rule restored: `model:x` and the control-sides test red, the other 9 cases green; the identifier rules were already equal (green both ways). The existing equivalence tests in `test_graph.py` stay; they compare behaviour, not copies.
- **M10:** `Graph.reaches(extra=…)` removed, its test rewritten to `without` only; `_shown_of`/`_graph_shown` merged over a `_Shown` protocol (in `b75af5e`); `read.py`'s `_period_text`/`_value_text` replaced by `graph.value_text` (public). The CLI's `_field_text` stays: it prints `FROM..TO`, the input syntax, by design.
- **M11:** `ThreadVerdict` docstring: `blocked` is not cleared for an event-start relation; nothing reads it for a relation (only `_entity_entry` and `verdict` for entity ends read it).
- **M12:** `entity … --state retracted` without `--subject` refused before writing with `--state retracted needs --subject: only an entity that stands can be retracted` (there is no `entity --retract` flag); `cli.md` quotes it. Test `test_a_first_version_of_an_entity_cannot_be_a_retraction` (control in the test: the same state with `--subject`). Mutation guard off → red; control green.
- **M3 (partial, docstring):** `_Claims` says what `verify` does not hold of vocabulary and class events; the checks go to the map.
- **Task 7 minors:** the header cost names the fold and `objections_seen` (`graph.md`, handoff); the map says "überlinear, etwa quadratisch" with the factor (2.5× edges → 6× time) instead of "quadratisch"; the "rest are still to be taken" wording is gone with the rewritten cost section.

### The map (`8613d6c`, `bf41e0a`, `c120539`)

Count with the command from `CLAUDE.md`: **225 before, 233 after.**
- New top-level points (8): M3, M4, M5, M8, the `list_entities` placeholder that vanishes when a hidden entity's last proposal is rejected, what phase 2 changes for an event as the start of a relation, the stale vocabulary in `apply FILE`, the split of `cli.py`.
- Updated: the `verify` point (überlinear/etwa quadratisch, final figures) and the header point (F-c figures and judgement).
- Sub-points added under the deferred minors: T1 `_text`/`isprintable` (NBSP in labels), T1 `test_wheel.py` builds twice. T1 "retiring `person`", T3's two and T5's type column were already there.
- Struck, to *Erledigt*: `entity` retracted without `--subject` (`1b5fbf4`), Task 4's candidates case (cannot happen: `_to_problem` refuses candidates on any non-open version). Both were sub-points, so the count does not drop.
- "Wo das Projekt steht" points at the figures instead of promising them.

### Gates (final tree `992029c`)

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        135 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing   2645 passed in 289.68s, coverage 97.63% (floor 90%)
make -C docs html                   build succeeded (warnings are errors)
make -C docs vale                   0 errors, 0 warnings and 0 suggestions in 50 files
make -C docs linkcheck              build succeeded, 0 broken
uv run pip-audit --skip-editable    No known vulnerabilities found
```

The tutorial's block is typed from one green `uv run pytest`: `2645 passed in 287.95s`, seed 3109946931, `rootdir:` left out as the page says. To make that run green, the guarded `N passed` line was set to 2645 first (the earlier run, on the same test tree, gave 2644 passed and the one typed-output failure); after the run, only the tutorial changed. The fence flake did not hit.

### Left undone and notes

- The first 100,000 run's MCP part crashed with `ImportError: cannot import name 'value_text'`: it imported the worktree's source while this wave was editing it. The coordinator's confirmation ran on a fixed checkout; its figures are the ones on the page.
- The coverage-gate runs and the `uv run pytest` runs of this wave shared the machine with the coordinator's measurements for part of the time.
- `README.md`, the tutorial text and INSTRUCTIONS needed no change: none names `--base`'s old behaviour or the approval of gate kinds.
