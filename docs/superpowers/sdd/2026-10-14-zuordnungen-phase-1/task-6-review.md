# Task 6 review: MCP — reading, writing, questions, the header

Reviewed: base `3a23a9b`, head `364a971`, via `review-3a23a9b..364a971.diff` (5,327 lines).
I reviewed it in six passes: cli.py/core/confirm.py; read.py; render.py; server.py (three chunks); tests (removed lines first, then every new test); docs.
I looked at code outside the diff only for the named risks: `SourceEvents.named`, `claim_changes`/`_texts_of`, obligation `_entry`/`assertions`, `withholding`, `relation_visible`, `check_claims`/`_check_claim`/`closes_cycle`/`_levelled`, `read_graph`/`parse_claim`, `Classes.level`, the SDK's `to_thread.run_sync` sites, and the `_CALL` middleware.
I ran no tests. No doubt needed one: each of the findings below follows from a single, unambiguous code path, and I name the path.

**Spec: ✅**
**Quality: Changes requested** (two Important findings; each needs a ruling more than a code fix)

Every requested piece is present: the five tool names, the header suffix shown only when N > 0, `language` on `build_server`/`build_app` and passed from the CLI, the author set by the server, `confidence`, a preview showing level/`under`/`contests`, the decisions sealed and compared (`CLASS_CHANGED`/`DIRECT_WRITTEN`), old handles still opening, a hidden end/subject/ref getting the sentence of a missing one, decision 12 for recollections and relation ends, `write_triage_answer` with the ask mark writing the approval with `to = choice`, approve/reject for graph versions with a refusal for a question, the header counted once per call over what the client sees, INSTRUCTIONS quoted whole, fifteen tools with checksum and name list retaken, and a section and table per tool.

---

## Findings

### Important

**I1 — The cycle check of the preview reveals relations the client may not see.**
`src/previously/mcp_server/server.py:1657` (`claims_staged` → `claims_checked`) → `core/graph_write.py:453` (`_check_claim` → `closes_cycle`, `:275`).
`check_claims` folds the whole log with no client filter.
For a model's write (open, or transitive), `closes_cycle` asks whether `to` already reaches `from` over edges of that kind.
For an open write it counts edges of **every** level (ruling T2-b), so other clients' proposals count too.
The edges it counts include relations the client may not see: ones resting on a mail in a circle it has no rule for, and ones through an entity it may not see.
`part_of` is acyclic in the base vocabulary (`vocabulary.toml:78–80`), so this works on a default install.
A client that sees A and B, but not the hidden X in `A part_of X part_of B`, calls `write_relation` with `B part_of A` and no `confirm`.
It gets `the relation would close a cycle over a kind that is acyclic`, against a preview for the control.
That answer says that A reaches B through something hidden.
The preview writes nothing and leaves no trace beyond an access entry, so probing is free and can be repeated to map reachability.
`_refuse_unseen` closes this for ends, subjects and refs (Review Focus 3), but not for the cycle check, and no page names the channel.
Named risk 1 ("a refusal sentence") is exactly this.
Options, for a ruling:
- (a) Hold a **model's** write against the edges the client sees.
  For example, `check_claims`/`write_claims` could take an optional set of thread ids to leave out, built from `GraphView`.
  The operator's approval keeps checking every direct/transitive edge, as T2-b's fallback already foresees: "an approval … that closes a cycle is refused at approval time".
- (b) Accept the channel as one bit of structure per probe, and name it on `mcp-tools.md` and in the map.

**I2 — `list_triage`'s fourth section says that something waits on a thread the client may not see, and names hidden relation ids.**
`src/previously/mcp_server/read.py:1434–1435` (the `hidden` set in `triage`).
A withheld entity or relation gets a placeholder in `list_triage` only when something waits on it.
That breaks two rules the code itself states:
- **The header.** `objections_seen` leaves out hidden objections "so that the header tells nothing of what the policy keeps from it".
  But when another client writes an objection or a proposal on a hidden entity, a placeholder appears in triage, and it goes away when that is resolved.
  So the client learns what the header was built to hide, as "a placeholder appeared".
- **The obligation listing.** `_entry` in `read.py` says a withheld entry passes every filter that looks at content, "so that the same placeholder appears under every one of them and none of them tells what it holds".
  Whether something waits is such a filter, and here it decides whether the placeholder appears at all.

It also names the id of a hidden **relation**, which no other tool shows: `list_entities` lists only entities, and it hides a relation without a placeholder.
The test `test_list_triage_puts_objections_first_…` holds this behaviour as intended, and report deviation 7 states it, so this is a conscious choice that needs a ruling:
- (a) drop the fourth section, which matches the header; or
- (b) make it unconditional, a placeholder for every withheld entity whether or not anything waits, which matches `list_entities`, and no relation placeholders.

### Minor

**M1 — The access entry of a thread that mixes a recollection with sourced versions carries no circles.**
`read.py:944` (`GraphView.delivered` takes `verdict.decisions[-1][1].circles`) with `core/graph_write.py:692` (`claim_decisions` appends the recollection decision **last**, with `identities=()`).
For an entity that has the operator's recollection and also a model's version on a mail, the last decision is the recollection's, and its circles are empty.
So `previously access --circle X` does not find the delivery, though the mail in circle X went to the client.
The obligation code's `decisions[-1]` works because every decision there sees every identity.
Fix: take the circles of the first source decision, or the union over the source decisions.

**M2 — No MCP test for Review Focus 1, a vocabulary changed between preview and confirmation.**
The plan assigns it to Tasks 4 and 6.
Core covers it (`tests/test_graph_write.py:695`), and the confirm path does go through `write_claims`.
But no test holds that the MCP confirmation cannot skip that check, for example after a refactor that writes from the sealed claims.
One test (retire `person` between the two calls, expect the write path's sentence, nothing written) would hold it.

**M3 — Two rules for "does a client see this relation".**
`core/graph_write.py:727` `relation_visible` is now used only by tests.
It also disagrees with `GraphView` in two places: an erased end hides the relation in core and shows as `(erased)` in MCP, and core looks at one version's ends while MCP looks at every version's.
The report names this (concern 4).
Align them or remove the core one; this can wait for the whole-branch review or Task 7, but it shouldn't ship with two answers.

**M4 — An assertion that checks nothing.**
`tests/test_mcp_server.py:3458`: `assert ids.anna  # the world is the same throughout` is always true.
That test also doesn't check that nothing was written, which its sibling (`…class_that_changes…`) does with `len(_assertions(world)) == count`.

**M5 — `list_entities` and `list_triage` fold the graph twice per call.**
Once for the header (`objections_seen`, `server.py:913`) and once in the body.
Passing the folded graph, or the `GraphView`, through would halve their cost.
This belongs to the ⚠️ on cost below.

---

## ⚠️ To adjudicate (report concerns and deviations)

- **The header folds the graph on every call**, `whoami` and `get_event` included: 26 ms at 1,000 entities and 132 ms at 5,000, growing linearly.
  The final measurement (decision 14) has to include `objections_seen` at 10,000 and 100,000 relations.
  At that size every unit-5 tool pays for it, and the measurement decides whether phase 2 needs a projection.
  I recommend a ruling now that adds it to the measurement list, as T4-c did for `verify`.
- **The count is taken before a resolving write.** This is documented on `mcp-tools.md` and follows the dispatch ("once per call"). Acceptable.
- **Visibility is not re-checked at the write.** The check runs in the snapshot and the write runs after it, the same as `write_assertion` in unit 5. Acceptable, and consistent.
- **The context variable is safe; checked.** The SDK runs each sync tool through `anyio.to_thread.run_sync` (`mcp/server/mcpserver/utilities/func_metadata.py:164`) in a copy of the task's context, which the existing `_CALL` mark already depends on.
  `_PENDING` is set and reset inside one synchronous `Service.answer` frame (`finally`), and the deferred `write()` runs inside that frame too.
  Concurrent HTTP calls each run in their own copied context, so a count cannot cross calls.
  An explicit parameter would be clearer, but nothing is wrong with the current form.
- **Deviation 1, `types` instead of `type`.** Accept: A002 rules out `type`, an alias breaks the SDK's mapping, and the item field stays `type`.
- **Deviation 2, `claim_decisions` in core.** Accept: `claim_verdict` behaves the same, and `test_graph_write.py` is unchanged and green. See M1 for the consequence of its ordering.
- **Deviation 3, erased ends shown marked.** No leak, since `get_event` names erased events to any client too. The divergence is M3.
- **Deviation 8, three existing tests changed.** Confirmed: the only removed or changed lines in existing tests are `TOOLS_SHA256` plus the name list, the ask-mark test (renamed, set of three), and the INSTRUCTIONS substring list, which was only extended. `tests/test_confirm.py` only gains tests.

---

## Named risks: what I checked, and the result

1. **Leakage.** *Count:* `objections_seen` counts only threads where `view.seen` holds. A thread is seen only if the sources of **every** version are, so an objection with hidden sources hides its thread and is not counted. The test's hidden-Lea case and mutation M4 hold this. *Refusal sentences:* hidden and missing give the same sentence for an end, a subject and a ref (`_refuse_unseen` against `entity_types()` of seen entities only, run before the write path, claim by claim); for a question (`event N is no question that waits`, three cases); and for approve/reject (`event N is not a proposal this client can answer`, alone and beside a visible id). Sentences about a visible thread (already approved, overtaken, candidates) name only visible ids. **The exception is the cycle sentence, I1.** *Timing:* hidden and missing ids take the same code path; the graph branch of approve/reject runs for every id that is not an obligation version, whether or not it is visible. I found no differential worth naming. *Placeholders:* the reasons come from `withholding`, which uses policy names only. **Triage's waiting-only placeholders are I2.** *Ids:* `claim_changes`/`_texts_of` render ends and refs as bare ids, and a ref to an entity the client may not see reads `(not shown)`, the same as one that is gone. **Hidden relation ids appear only through I2.**
2. **Self-authorization: holds.** `EntityItem`/`RelationItem` use `extra="forbid"` and have no author, responsibility, `under`, `contests` or `approves`. The test refuses `responsibility` through the schema, and mutation M3 holds it. `_entity_claim`/`_relation_claim` set `model_author(client.name)` and `OPEN`. `_levelled` passes a claim through unchanged only when it is an approval, and an approval is built only by `write_approve`/`write_triage_answer`, both of which carry the ask mark. Gate kinds: `Classes.level` returns open for `GATE_TYPES` (`core/classes.py:261`). A question is forced open, and so is an objection against a direct winner. `takes_proposal` keeps the approval to the proposal and lets only a question's `to` become one of its candidates.
3. **The handle: holds.** *Another client:* `client` is compared with `compare_digest`. *Expiry:* checked. *Changed items:* the digest is over the payloads as the client gave them, before levelling. *Changed decision:* `decided` sits inside the HMAC'd body and goes to `write_claims` as `expect`, which compares it under the tip; the tests cover a class revoked, a class set, and a direct version written between the calls. *Old handles:* they keep the same four body keys, and `open_handle` uses `decisions=False`. *New handles on the old path:* refused with `_OTHER_CONTENT`, either way round (`test_a_handle_of_write_assertion_does_not_confirm_write_entity_or_the_other_way`, and the `test_confirm.py` cases). A forged `decided` fails the MAC; a malformed one under a valid MAC gives `_NOT_SEALED`.
4. **Unit-5 tools: unchanged.** `write_approve` takes the graph branch only when some id is not an obligation version, and that branch returns `None` (back to the obligation path) unless one of the ids is a graph version the client may see. `write_reject` takes it only when the id is no obligation version. The obligation path's refusals and its record are unchanged, and the tests were edited only in the three listed places.
5. **`mcp_access`: holds.** `write_record` keeps counts, source ids, ends, `confirm` and the ids written; `write_triage_answer` doesn't pass `reason` into the record at all. The test searches every stored access payload for the private name, reason and text, with a control that finds them in the assertions themselves.
6. **The context variable: holds.** See the ⚠️ above.
