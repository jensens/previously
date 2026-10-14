# Task 6 report: MCP — reading, writing, questions, the header

Status: DONE_WITH_CONCERNS (the concerns are below; none blocks the gates).
Commits on `worktree-zuordnungen`, base `3a23a9b`:

- `830d2fe` mcp: entities, relations, triage and the objections pending in the header
- `364a971` tutorial: retype the test run from one green run, 2602 passed

## What was built

### Tools (10 → 15)

| Tool | Kind | Where |
|---|---|---|
| `list_entities(types?, state?, proposals?, subject?, history?, cursor?)` | read | `server.py` `_graph_tools`, `Service.entity_page`; `read.py` `entities` |
| `list_triage(cursor?)` | read | `Service.triage_page`; `read.py` `triage` |
| `write_entity(items, confirm?)` | write, two calls | `Service.entity_write` → `claims_staged` |
| `write_relation(items, confirm?)` | write, two calls | `Service.relation_write` → `claims_staged` |
| `write_triage_answer(question, choice, reason?)` | write, one call, `meta=_ASK_THE_PERSON` | `Service.triage_answer_write` → `claims_answering` |

`write_approve` and `write_reject` now take versions of entities and relations
(`graph_approval_write`, `graph_rejection_write`), dispatching on what the id
names, as the CLI does; their `_meta` mark is unchanged. An approval of a
question id refuses with `event N is a question: answer it with
write_triage_answer`; a call naming both families refuses with the CLI's
sentence `one call approves obligations and decisions, or entities and
relations, not both`. Obligation behaviour is unchanged (the graph branch is
taken only when an id is not a version of an obligation thread at all).

### Visibility (decision 12, Review Focus 3) — `read.py` `GraphView`

- An entity or a relation is decided over the identities of the source events
  of every standing version (`claim_sources`), with `recollection = any
  version is a recollection` (`claim_decisions`, below). A recollection without
  a rule `source:recollection` is withheld; the `Withheld.source` is
  `recollection`.
- A relation additionally needs every entity that any of its versions names
  (start, `to`, candidates) to be seen; the first blocking decision of an end
  becomes the relation's withholding (so the placeholder gets a policy-made
  reason). An end whose every version is erased (no thread) withholds nothing.
- A relation that starts at an event (phase 2 form) is never shown and gets no
  placeholder.
- Withheld items: `[withheld: previously://event/<id> — <reason>]`, the reason
  from the existing `withholding`.
- A `ref` field naming an entity the client may not see — or one that is gone —
  reads `entity N (not shown)`: one text for both.

### Writing (`server.py` `claims_staged`)

Order, all in the call's snapshot: item form → every source visible
(`event N is not one this client can use as a source`) → `_refuse_unseen` →
line bound → payload digest → without `confirm`: `check_claims` (levels),
preview with each claim's level/`under`/`contests`, handle sealed with the
decisions; with `confirm`: `open_sealed(..., decisions=True)`, then after the
snapshot `write_claims(..., expect=<sealed decisions>)`.

`_refuse_unseen` (Review Focus 3): per claim, in order, before the write path:
form (`claim_problem`), then a subject the client may not see is refused with
the write path's sentence `the subject N names no entity or relation that
stands`, then `conformance_problem` against `GraphView.entity_types()` — the
standing entities **this client may see**. A hidden end therefore gets exactly
`an end of the relation is not an entity that stands`, as a missing one does.
Because the pre-check runs before the write path, claim by claim, the answer
for a batch is the same whether the end is hidden or missing (I checked the
ordering argument: running it after `check_claims` would have leaked through a
different sentence from a later claim of the batch).

The author is `model_author(client.name)`; items carry no author and no level
(`extra="forbid"`: an item with `responsibility` is refused by the schema).
Each item carries `confidence` (int); its range is the form check's sentence.

`write_triage_answer`: hidden, missing, not-a-question and no-longer-waiting
all refuse with `event N is no question that waits`; a non-candidate with the
write path's `the answer names N, which is none of the candidates`. Idempotent:
the identical answer standing already is answered with its id.

Written results: `assertion N · LEVEL` for `write_entity`/`write_relation`
(the level matters to the model); `assertion N` for the one-call tools, as
before.

### The handle change (`confirm.py`)

- `seal(..., decided: Sequence[Decided] | None = None)` adds a body key
  `decided: [{"level", "under", "contests"}, ...]` only when given. `Decided` is
  `core.graph_write.Decided` (no second dataclass).
- `open_sealed(..., decisions: bool = False) -> Opened(nonce, decided)`;
  `open_handle` is unchanged in signature and returns `open_sealed(...).nonce`.
- `payload_digest` is unchanged (over the payloads without `handle`). For graph
  tools the digest is over the claims as the client gave them (open, before
  levelling), so the confirm call hashes the same thing whatever the levels
  are now.
- A write_assertion handle has exactly the four keys it always had, so any
  handle sealed before the upgrade still opens within its 10 minutes;
  `tests/test_confirm.py` and every write_assertion test stayed green
  **unchanged**.
- A handle with decisions where none are wanted, without where they are, or
  with other than one per payload → `the handle was sealed for other statements
  than these; …`. Malformed `decided` (sealed with the key) → `the handle is not
  one this server sealed; …`.

### The header (`render.py`)

`objections_note(n)`: ` · N objections pending` / ` · 1 objection pending` /
`""`. `render_page(..., objections=0)` puts it after the title and before
` · page N`; `render_text(..., objections=0)` after the title and before
` · N control characters removed`. The count is computed once per call in
`Service.answer`, inside the snapshot, after the client is resolved and before
the body (`read.objections_seen`), and handed to every render call of that call
through a `ContextVar` (`_PENDING`), reset in `finally`. Only objections on
threads the client sees count. Documented on `mcp-tools.md` `### The header`.
The docs example page test stays green (default 0).

### `INSTRUCTIONS`

Kept every pinned substring and added: entities and relations with the
vocabulary declaring their kinds and fields; honest `confidence`, the server
decides the level from the approval classes; contradicting a direct version
becomes an objection and never replaces it; an unclear relation gets
candidates and is not guessed; `list_triage`; the header counts objections;
`write_triage_answer` answers in the operator's name and the client asks first.
"Three tools write" became "Six tools write". Quoted whole on `mcp-tools.md`
(docs test green).

### `mcp_access` (decision 15)

`write_record`: `write_entity` → `{statements, sources, confirm, written}`;
`write_relation` → the same plus `ends` (sorted ids from `from`, `to`,
candidates); `write_triage_answer` → `{statements, proposals: [question], ends:
[choice], written}`. The `write_assertion` record is unchanged. `list_entities`
and `list_triage` record their given arguments. All new names are in `TOOLS`,
the writers in `WRITERS`. Delivered: an entity under its id with the circles of
its own sources; a triage item under the version id; a placeholder under the
thread id. Rules: of every decision taken, ends included.

### Language (ruling P-1)

`build_server(..., language="en")`, `build_app`, `run_stdio`, `run_http` take
it; `build_server` refuses a non-tag with `ValueError`. `previously mcp` and
`serve` pass `_language()` (`PREVIOUSLY_LANGUAGE`, validated before storage is
opened). Labels: `display_label(..., language=<entity's working language>,
default=<server language>)`.

## Deviations

1. **`list_entities(types?)` instead of `type?`.** Ruff A002 refuses a
   parameter named `type` (it shadows the builtin), the SDK maps a parameter's
   schema name from the Python name (an alias breaks the call: measured in
   `func_metadata.model_dump_one_level`), and the constraints forbid a new
   suppression. `types` is a list of kinds; the item field stays `type`, as in
   the payload.
2. **Core touched once:** `core/graph_write.py` gained `claim_decisions(...)`
   returning every decision with its source; `claim_verdict` now uses it
   (behaviour identical; `tests/test_graph_write.py` unchanged and green). The
   MCP side needs every decision for rules and the source for `Withheld`.
3. `relation_visible` is not called: `GraphView` applies the same rule but needs
   the blocking decision for the reason. It differs in one point, deliberately:
   an erased end does not withhold (relation_visible treats an unknown id as
   not visible). Documented on the page and in the class docstring.
4. Two sentences of the write path are duplicated in `server.py` so the
   pre-check can say them first (`the subject N names no entity or relation
   that stands`, `a statement has no valid form: …`), plus the candidate
   sentence as the CLI duplicates it. The tests hold the equality.
5. A new version via MCP is a complete version (nothing merged from the old
   one), as `write_assertion` items are; the CLI merges. Documented.
6. No "does not fit the vocabulary" mark in MCP listings (the CLI has it): it
   would run conformance against entities the client may not see.
7. `list_triage` shows one placeholder per withheld thread with anything waiting,
   in a fourth section after the three, not one per version (how much and what
   waits is content).
8. Tests changed beyond additions: the tool-name list and `TOOLS_SHA256`
   (`c25cff3f…dca0`), the ask-mark test (renamed `…_three_answering_tools…`,
   set of three), and the INSTRUCTIONS substring list (extended).
9. `_tools` was split (`_graph_tools` holds the two new reading tools) because
   C901 counted 11 with them inside.

## Tests

`tests/test_mcp_server.py` (+21 test functions, each ×2 via `MODES`),
`tests/test_render.py` (+2, one parametrized ×3), `tests/test_confirm.py` (+4).
Suite: **2602 passed** (was 2552 collected before this task).

Covered: list_entities with relations, placeholder, the control client; a
relation with a hidden end not shown; recollection withheld until
`source:recollection`; filters, history, missing subject; language (de/en, the
working language first, a bad tag); write_entity preview/confirm/repeat by the
model; the level is the write path's (transitive under a class, open below the
threshold, an item naming a level refused by the schema); a class revoked or
set between preview and confirm → `CLASS_CHANGED`; a direct version between →
`DIRECT_WRITTEN`; an objection never replaces (with a class and confidence
100); the header with 0, 1, 2 and with a hidden objection not counted (and the
local client counting 3), on a page, a text result and the chronicle; hidden
vs missing end and subject give the same sentence, with and without confirm,
nothing written; question in triage, answered with a candidate, a stranger
refused, idempotent repeat, access record; a hidden question = missing = not a
question; client proposal approved via write_approve (Z §17 point 1) and
repeated; approve of a question, a mixed call, a hidden version alone and next
to visible ones; write_reject of an objection drops it from the header,
idempotent; triage order objection → question → proposal → placeholder; triage
paging across sections without gap or double (81 items, several pages);
access entries hold counts and ids and no text (with the control search in the
stored payloads); a write_assertion handle does not confirm write_entity and
vice versa; render header 0/1/2 and the page bound with the note; sealed
decisions round trip, the old handle form unchanged, crossing refused, malformed
decisions refused.

## Mutations (each change → red, restore → green; files compared byte-equal after)

| # | Change | Tests run | Mutated | Restored |
|---|---|---|---|---|
| M1 | confirm not held to the preview: `expect=` dropped from `write_claims` in `claims_staged` | class-changes, direct-version-between | 4 failed | 4 passed |
| M2 | preview shows the client's (unlevelled) claim instead of `check_claims`'s | level-is-the-write-path's, objection-never-replaces | 4 failed | 4 passed |
| M3 | "level from the client": `EntityItem.responsibility` added and used | level-is-the-write-path's | 2 failed | 2 passed |
| M4 | header counts hidden objections (`if view.seen` dropped) | header-counts, triage-order | 4 failed | 4 passed |
| M5 | hidden end checked against every entity, not the visible ones | `end_the_client_may_not_see` (2 tests ×2) | 2 failed, **2 passed (control: the relation-not-shown test)** | 4 passed |
| M5b | hidden end refused with a sentence of its own | same | 2 failed, 2 passed (control) | 4 passed |
| M6 | recollection decided as sourceless content | recollection | 2 failed | 2 passed |
| M7 | a relation shown whatever its ends | relation-with-an-end | 2 failed | 2 passed |

Every MCP test carries its own control (the client that may see, a class
below its threshold, the stored-payload search); M5/M5b show the control
staying green while the assurance goes red.

## The six gates (after both commits)

```
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
135 files already formatted
$ uv run pyright
0 errors, 0 warnings, 0 informations
$ uv run lint-imports
Contracts: 9 kept, 0 broken.
$ uv run pytest --cov --cov-report=term-missing
TOTAL 10572 251 98%
2602 passed in 268.96s (0:04:28)
  graph_write.py 100%, confirm.py 100%, read.py 95%, render.py 97%, server.py 93%
$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded (warnings are errors)
✔ 0 errors, 0 warnings and 0 suggestions in 46 files.
build succeeded; 0 broken links
```

The tutorial's test block was retyped whole from one green `uv run pytest` run
(seed 2925154327, 2602 passed in 267.78s; the `rootdir:` line left out as the
page says). To get a green run at all, the stale `2552 passed` was first set to
2602, since the typed-output test is part of the run it measures.
The known flake (`test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence[auto]`)
did not fail in any run of this task.

## Docs

`docs/reference/mcp-tools.md`: fifteen tools; the instructions whole; `### The
header` with the objections note and where it stands; a new `(mcp-entity-form)=`
`### An entity or a relation`; `### \`list_entities\``, `### \`list_triage\``,
`### \`write_entity\`` (+ `#### The fields of an entity`), `### \`write_relation\``
(+ `#### The fields of a relation`), `### \`write_triage_answer\`` with its
ask mark; writing in two calls and answering in one call extended; new
refusals; the access-entry keys (`ends`). `cli.md` and `configuration.md`:
`PREVIOUSLY_LANGUAGE` read by `mcp` and `serve`, and its refusal in their exit
codes. Explanation pages (objections, levels over MCP) are left to Task 7; the
how-to `connect-claude-code-and-vibe.md` keeps its dated "ten tools"
measurements, which are measurements of their day.

## Concerns

1. **Every call now folds the graph** for the header count (`read_graph` reads
   every assertion and the classes). Measured on this branch, one snapshot,
   median of three: `objections_seen` 26 ms at 1,000 entities, 132 ms at 5,000;
   a `whoami` call 63 ms and 145 ms end to end. Linear, so the plan's final
   measurement (decision 14) should include it; a projection in phase 2 would
   remove it. `list_entities`/`list_triage` fold a second time in the same call.
2. The count is read before a writing call writes, so the result of
   `write_reject` of an objection still shows the count from before it (as the
   ruling says: once, inside the snapshot). Documented.
3. Visibility is checked in the snapshot and the write follows after it, as for
   `write_assertion`: a policy change in between is not re-checked.
4. A relation whose end entity was erased is shown, naming the end
   `(erased)`; `relation_visible` in core would hide it. One of the two should
   probably change so that core and MCP agree (I kept MCP consistent with the
   CLI's `(erased)` rendering and with `get_event` naming erased events).
5. The ContextVar for the count is implicit state; it is set and reset in one
   function and read only in `server.py`, but a reviewer may prefer an explicit
   parameter through every body.

---

# Fix round 1 of 1 (review `task-6-review.md`, rulings T6-a, T6-b, T6-c)

Commits, on top of `364a971`, not pushed:

- `f9ff79c` mcp: fix round 1, no cycle refusal for a model, triage without placeholders, one fold
- `fc0d6f0` tutorial: retype the test run from one green run, 2616 passed

## I1, ruling T6-a

- `core/classes.py`: `Classes.level` and `Classes.covers` take a required `vocabulary`. `_covering` returns nothing for a relation kind with the behavior `acyclic`, as it already did for `GATE_TYPES`. `set_class` and `class_refusal` refuse such a kind with `the approval class names "part_of", a relation kind that is acyclic, which no class reaches`. A revocation is still taken. The module docstring says why.
- `core/graph_write.py`: `closes_cycle` returns `False` for `level == OPEN`, and holds direct and transitive writes against direct and transitive edges only, as before. `_levelled` passes the vocabulary of the write to `classes.level`. The docstrings name T6-a.
- `core/verify.py`: `_claim_level` passes the vocabulary in force at the row to `covers`. A transitive version of an acyclic kind under a hand-written class is now the existing finding `assertion is transitive under no approval class in force for it`. The cycle finding follows `closes_cycle`, so a model's open version is no finding.
- Docs:
  - `mcp-tools.md`, under `write_relation`: no class covers an acyclic kind, and a client's version is never refused for a cycle.
  - `mcp-tools.md`, under `write_approve`: the residual. An approval that would close a cycle is refused, counting relations the client may not see. That tells a call the person confirmed one bit, and it is the only way an MCP client learns of a cycle.
  - `cli.md`: the `classes` section names acyclic kinds among the refused ones, and the `verify` findings table is updated for both findings.
- The map entry the ruling also names is not written here. The map is Task 7's file, and I did not touch it.
- Existing tests changed:
  - `test_an_open_edge_does_not_veto_the_operator_but_closes_a_cycle_for_a_model` is now `test_an_open_edge_neither_vetoes_the_operator_nor_is_refused_for_a_cycle`. A model's edge that closes a cycle, and a model's self-edge, are written open; the operator closing the same cycle is refused (the control). The part about a transitive `part_of` edge went, because no such edge can be written now.
  - `test_a_class_does_not_make_a_question_transitive` now uses `POSTS` and `post_in`, because `EDGES` over `part_of` is refused now.
- New tests:
  - `test_no_class_reaches_an_acyclic_kind` (graph_write): `set_class` and `class_refusal` give the sentence above. A hand-written class event over `part_of` gives the level open. The controls: a revocation is taken, and `POSTS` is taken.
  - `test_an_acyclic_kind_is_open_even_if_an_event_names_it` (classes, pure): `level` and `covers` for `part_of`, with `involved_in` as the control.
  - `test_a_models_proposal_that_closes_a_cycle_is_no_finding` (verify): `verify` is clean for the model's open edges. The control: the operator's same edge, forged, is still a finding.
  - `test_a_cycle_through_a_hidden_entity_is_not_refused_for_the_model` (MCP ×2): A part_of X part_of B, with X on the plain mail. A `write_relation` of B part_of A gets a preview and a confirmation, both pass, the claim is `open`, and `verify` is clean. The control: the operator's B part_of A raises `GraphRefused` for the cycle.

## I2, ruling T6-b

`read.triage` drops the `hidden` set, the `WITHHELD` section and its placeholders, so `TRIAGE_SECTIONS` has three entries. The `list_triage` description and `mcp-tools.md` say that what waits on a thread the client may not see is left out, without a placeholder. `TOOLS_SHA256` was retaken: `58faeb7e…b902`. The test is now `…_and_hides_the_rest`: there is no `[withheld:`, Lea's id doesn't appear, and the local control still sees her objection.

## Ruling T6-c

- **M1:** `GraphView.delivered` takes the union of the circles of every decision, in order. The decision of a recollection names nobody and comes last, so it no longer replaces the circles of the mail. Test `test_an_entity_of_a_recollection_and_a_mail_is_delivered_with_the_circles_of_the_mail`: `("office",)`; the control, a recollection alone, gives `()`.
- **M2:** `test_a_vocabulary_changed_between_preview_and_confirmation_refuses_the_write`. A `team` kind is added, then retired between the preview and the confirmation. The confirmation gets `Error: the kind is retired and takes no new entity` and nothing is written. The control: a `post` is written.
- **M3:** core `relation_visible(policy, client, thread, ends, identities, sources)` is now the one rule. It looks at a thread, not a version. Its ends are those of every version, from `relation_ends`, which moved to core. `ends` maps each end to `True`, `False`, or `None` for an erased end, which withholds nothing; an end the map lacks is not seen. A recollection in any version counts, and so does an event start in any version.
  - `GraphView.verdict` calls it for a relation and keeps the blocking decision only for the reason.
  - An end that names a relation, which only a forged payload can, is not seen and gets no placeholder.
  - Core tests: the visibility test was rewritten for a thread. New: `test_an_erased_end_withholds_nothing_and_every_version_names_its_ends`. MCP test: `test_a_relation_is_shown_by_the_one_rule_of_core`, a forged relation to a relation id.
- **M4:** `assert ids.anna` is replaced by `len(_assertions(world)) == count`.
- **M5:** `Service.answer` folds the graph once (`_FOLDED`, a context variable holding the graph and the count). `Service.graph_now` hands that graph to `list_entities`, `list_triage` and every writing tool. `objections_seen`, `entities` and `triage` take `graph` as an argument. Test `test_a_call_folds_the_graph_once_for_its_header_and_its_body` uses a subclass of the real store that counts its reads of every assertion. One fold for `list_entities`, `list_entities` with a subject, `list_triage` and `whoami`.

## Timings after M5

These are medians of three calls through the in-process client, with one objection pending, measured on 2026-10-14.

| Entities | `whoami` | `list_entities` with a subject |
|---|---|---|
| 1,000 | 53 ms (72, 53, 53) | 54 ms (55, 54, 53) |
| 5,000 | 153 ms (151, 153, 218) | 161 ms (154, 161, 219) |

Before M5, `list_entities` folded twice; `whoami` was 63 ms and 145 ms. The cost is still linear in the assertions. Ruling T6-c puts it into the final measurement, beside T4-c, at 10,000 and 100,000 relations.

## Mutations (each change → red, restore → green; all four files compared byte-equal after)

| # | Change | Mutated | Restored |
|---|---|---|---|
| A | cycle check holds open writes again | 4 failed, **2 passed (control: the operator's cycle refused)** | 6 passed |
| B | `_covering` covers an acyclic kind | 2 failed | 2 passed |
| C | `set_class` takes an acyclic kind | 1 failed | 1 passed |
| D | triage lists what waits on a hidden thread | 2 failed | 2 passed |
| E | circles of the last decision only (M1) | 2 failed | 2 passed |
| F | write path's vocabulary check removed | **2 passed**: the MCP pre-check catches it on its own | — |
| F2 | both guards removed, the write path's and `_refuse_unseen` on confirm | 2 failed | 2 passed |
| F3 | only the MCP guard removed | 2 passed: the write path catches it | — |
| G1 | `relation_visible` reads the newest version's ends only | 1 failed | 1 passed |
| G2 | an erased end withholds | 1 failed, **1 passed (control)** | 2 passed |
| G3 | MCP decides a relation without `relation_visible` | 2 failed | 2 passed |
| H | the body folds again (M5) | 2 failed | 2 passed |

F and F3 are worth a note: the confirmation is guarded twice. `_refuse_unseen` runs on confirm too, against the vocabulary of the confirm's snapshot, and `write_claims` checks again under the tip. Each guard alone keeps the test green, and the test goes red only when both are gone.

## Tests and gates

- The five named files: 502 passed, before the last two tests were added.
- The full suite: 2616 passed.
- One run failed the known flake, `test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence[auto]`, at `_text`'s number check (`int(number) <= MAX_SAFE`), as diagnosed. The rerun was green, and the tutorial was retyped from that run: seed 3878700850, 2616 passed in 259.85s.

```
$ uv run ruff check .                 All checks passed!
$ uv run ruff format --check .        135 files already formatted
$ uv run pyright                      0 errors, 0 warnings, 0 informations
$ uv run lint-imports                 Contracts: 9 kept, 0 broken.
$ uv run pytest --cov --cov-report=term-missing
                                      TOTAL 10584 252 98%; 2616 passed in 263.90s
$ make -C docs html && make -C docs vale && make -C docs linkcheck
                                      build succeeded; 0 errors, 0 warnings, 0 suggestions in 46 files; build succeeded, 0 broken
```

## Left undone

- The map entry for the T6-a residual, which ruling T6-a also asks for. `mcp-tools.md` carries it.
- The header's cost at 10,000 and 100,000 relations. That is the final measurement's, by ruling T6-c.
