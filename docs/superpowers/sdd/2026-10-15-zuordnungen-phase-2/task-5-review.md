# Task 5 review — the chronicle of a bracket (b64d43f..c205fea)

Spec: ❌ (ruling T5-b not implemented; the tests and pages pin the behavior T5-b forbids)
Quality: Changes requested

Counts: Critical 0 · Important 2 · Minor 2 · ⚠️ 7

Read in passes: source (cli.py, rows.py, graph_read.py, members.py, read.py, server.py, postgres.py), tests (test_chronicle.py, test_cli.py, test_mcp_server.py), pages (graph.md, projections.md, the new how-to, cli.md, mcp-tools.md). Read beside the diff: `relation_visible` (core/graph_write.py:753), `GraphView` and `graph_view` (mcp_server/read.py:874–1020), `_decided` and `_shown` (read.py:318–355), `EntityTypes` (graph_write.py:182), `_given`, `recordable`, and the renderer's cut notes. No test was run: every finding below follows from code that the existing tests already pin.

What holds, and was checked rather than taken from the report:

- **Release (risk 1): no unit and no text gets out.** Over MCP, `within` only drops rows (read.py:413) before `_decided`, so every kept event goes through the policy exactly as without `within`. A shown event's units are cut down by `within.holds` before `_shown`, so `Delivered` names only the units that were shown. An excluded unit, a unit assigned elsewhere and a withheld mail never show more than the whole chronicle shows. Page boundaries cannot release anything either: the cut note of an event that stands alone on its page points at `get_event`, and the policy decides that call again (see ⚠️ 5). A cursor reused with another `within` fails `decode_position` (tested). A cursor reused by another client is safe because `Service.bracket` runs on every call, before the cursor is decoded (server.py:1133–1134), so a bracket hidden from the second client is refused (not tested, ⚠️ 6). The m1 mutation (bypass the policy) going red is the right assurance for this.
- **Correctness (risk 3).** Both readers find through the one `members`, so the specific-replaces-general rule is the same code in both. The CLI selection is held to `Members.holds` by a 200-example Hypothesis property against PostgreSQL that includes the limit. That property draws empty `excluded` sets and ids the log doesn't have, and I found no gap in it. `--since`, `--until` and `--limit` are applied in the same query as the selection (postgres.py `read_chronicle`), so they count only the bracket's units, and the CLI limit test shows it with a control. Over MCP, `since`, `until` and `source` stay in SQL, and `within` is applied before the page weight is taken.
- **The Markus test asserts Z §17 point 2.** Mail assigned to the topic (the summer party), and `chronicle --within` shows it for the topic and, one level up, for the club (party → `1/3`, club → `1/3`). It also asserts that XZ loses unit 3, which is the specific-replaces-general rule. The MCP twin uses a mail from the firm address.
- **The access entry (risk 4)** records `within` as the int the client gave (server.py `previously`, `_given(**{**filters, "within": within}, …)`), drops it when `None`, and passes it through `recordable`. The refusal is `within N is not an entity that stands`: the id the client gave, no name and no text. The test asserts `arguments == {"within": 0}` on a refusal.
- **Hidden bracket vs. missing bracket:** one sentence for hidden, missing, relation, event and 0, and a visible empty bracket gives an empty page. The m3 mutation goes red.
- **CLI snapshot:** reading `p_chronicle` in `storage.snapshot()` instead of `begin()` does no harm. `tip_and_bookmark` stays one statement, and the phase-1 tests are unchanged.

---

## Important

### I-1 — `within` walks edges the client may not see (ruling T5-b), and this exposes assignments the rest of the server hides

`src/previously/mcp_server/server.py:1175–1191` (`Service.bracket`) → `core/graph_read.py:258` (`bracket_members`) → `read_brackets` / `members` over **every** standing edge.

T5-b binds the fix round: over MCP, `members` walks only the edges that `relation_visible` lets through for the client. The implementation walks all of them. Three inference channels follow. None of them releases content, but each reveals an edge the client is not shown anywhere else:

1. **A withheld mail's assignment surfaces as a placeholder** (the strongest channel). `relation_visible` treats an assignment's start as one of its sources (graph_write.py:770–774), so a client that may not see the mail does not see the assignment either. `test_an_assignment_of_a_mail_the_client_may_not_see_is_not_shown_to_it` pins exactly that for `list_triage`. Under `within=B`, though, the withheld mail appears as a placeholder in B's chronicle, and the whole chronicle has no such filter. So the client learns "this withheld event, id and reason, is assigned to B", a fact `list_triage` and `list_relations` keep from it. Amount: one hidden edge per withheld member, with the event id. **T5-b closes it**: the assignment is not visible, so the mail is not a member and doesn't appear at all.
2. **A path through something hidden.** A visible mail E is assigned to C, C `part_of` B, and B is visible. If C is hidden, or the `part_of` relation is hidden (its own sources withheld, or C as an end not seen), E still appears under `within=B`. The client learns that E belongs to B through something it may not see, though not through which thing. The implementer reported this as concern 1 and documented it on graph.md:226–228. **T5-b closes it**, because a hidden hierarchy edge or assignment stops the walk.
3. **An excluded unit reveals a hidden assignment of that unit.** E is visible and assigned whole to B, and its unit k carries its own standing assignment to a hidden bracket H. "The more specific replaces the general" removes k from B's chronicle. The gap at k tells the client that unit k has an assignment of its own somewhere it can't see. Amount: one bit per unit, namely that a hidden direct or transitive unit assignment exists. **T5-b closes this only if** the visibility filter is applied to the whole edge list that `members` reads. That list includes edges into brackets *outside* the walk, because the exclusion reads every standing edge of a unit. A fix that filters only "the edges on the walk" (the hierarchy below B and the assignments into the set) leaves this channel open. The fix round's brief must say so, and a test must hold it (I-2).

The fix needs the threads of the edges to decide `relation_visible`. A `ProjectedGraph` has them only by folding from the log. `graph_view(…, subjects)` over every assignment in the store would read the source events of every assigned mail on every call (see ⚠️ 3 for a bound).

### I-2 — The tests and pages assert the behavior T5-b forbids, and the T5-b assurances have no test

- `tests/test_mcp_server.py:4822` `test_previously_within_shows_a_withheld_mail_as_the_placeholder_it_is_without` asserts channel 1 of I-1: the withheld `team` mail *appears* as a placeholder under `within`. Under T5-b it must be **absent** under `within`, and present as a placeholder in the whole chronicle as before. The brief's Step 1 wording ("bleibt Platzhalter, auch mit within") predates T5-b. As far as I can tell, T5-b supersedes it for every withheld mail, because an assignment's start is always among its sources (decision 3) and so is never visible when the mail is withheld. The controller should confirm this reading (⚠️ 1).
- `docs/explanation/graph.md:222` ("stands as the same placeholder with `within` and without it"), graph.md:226–228 ("What the filter doesn't hide is the assignment itself …"), and `docs/reference/mcp-tools.md:265` ("stands as the same placeholder") describe the pre-T5-b behavior. Each must state the T5-b rule: over MCP, an edge counts only where the client sees it. They must also state the resulting difference from the CLI: the operator walks every edge.
- Missing tests, each measured red with the T5-b filter removed, with a green control (a client that sees the edge, such as `local-harness`, finds the member):
  - (a) a withheld mail assigned to a visible bracket is absent under `within` and still a placeholder without it;
  - (b) a visible mail assigned to a hidden child C `part_of` a visible B is absent under `within=B`;
  - (c) a `part_of` edge whose own source the client may not see, with both ends visible, stops the walk;
  - (d) channel 3: E whole → B, unit k → hidden H; under `within=B` the client gets unit k (the hidden excluding edge does not count), while the CLI omits k.
- `test_previously_within_shows_no_unit_the_client_does_not_see_without_it` (4853) stays valid as a subset check, but it cannot detect any of channels 1–3, because they hide nothing and release nothing in units. Its `withheld ⊆ withheld` half becomes nearly vacuous after T5-b, and that is fine.

---

## Minor

### M-1 — An empty or sparse bracket makes every MCP call read the whole log (cost, risk 5)

`src/previously/mcp_server/read.py:400–430`. The loop reads `observations` 200 rows at a time and calls `source_keys` for each batch, until the page is full or the log ends. With `within`, the full log is read on every call whenever the bracket's members can't fill a page. That happens for a bracket with **no members at all** (`within.events` empty, so every row is dropped), and for one whose members all lie early in time. A page stays bounded in memory, because each batch is discarded, but a call is unbounded in rows read: O(observations) per call, with payloads.

Is that a denial-of-service lever? Yes, for any registered client: name a visible entity with nothing assigned and call repeatedly. It belongs to the same class as a `circle` that matches nothing (the documented open limit `mcp-open-limits`, which the BATCH comment now extends), so it is not new in kind. Not measured.

Cheap bounds that don't need a `LogStore` change:
- return `Seen((), more=False)` at once when `within is not None and not within.events`;
- stop the scan once the position passes the last member event. This needs one lookup of the members' `(occurred_at, id)`. On a first page it can be done without the lookup: count the member events met, and stop at `len(within.events)`.

Both are optional under ruling T5-a, but the first is a single line.

### M-2 — cli.md claims a refusal "before anything is read", and the code reads first

`docs/reference/cli.md:899`. In `_cmd_chronicle`, `--within` first catches up the graph projection (which writes), then reads `tip_and_bookmark`, then the graph (`_reader_graph`), and only then checks the id (cli.py `_bracket_selection`). What is true is "before the chronicle is read". A sentence on a reference page is a claim (CLAUDE.md, *A comment is a claim*).

---

## ⚠️ For the controller

1. **The brief vs. T5-b on placeholders.** Step 1 says a withheld event "bleibt Platzhalter, auch mit within". Under T5-b it disappears instead, as argued in I-2. Confirm that T5-b wins, so that the fix round inverts the test instead of keeping both.
2. **T5-b makes the client and the operator disagree in one direction that adds units.** In channel 3, dropping the hidden excluding edge puts unit k into B's chronicle for the client but not for the operator. That is no release, since k is visible without `within`, but it means T5-b does not only err "on confidentiality", as its own text says: here the client gets more under B than the operator does. The alternative is to let a hidden edge still exclude, but then the gap leaks (channel 3). I recommend filtering every edge and documenting the divergence.
3. **Cost of T5-b.** Deciding `relation_visible` for every edge in the store on every call reads the source events of every assigned mail, which is O(assignments) payloads per call. A bound that keeps the result exact is to walk with all edges first. That gives a superset of members, since filtering only shrinks the walk. Then decide visibility only for the edges that walk used, plus every edge that starts at one of its candidate events (the exclusion edges). Filtering can add units only to events that are already candidates.
4. **Timing: hidden vs. missing.** `Service.bracket` short-circuits at `EntityTypes` for a missing id, but for an existing hidden entity it builds `graph_view` and reads the entity's source events. That is a few milliseconds of difference, and it tells a patient client that an entity stands under the id. It is the same class as the write tools' "refused as one that doesn't exist" (`entity_types()`), so it is not new. Low.
5. **A cut event under `within` continues outside the bracket.** When a member event stands alone on its page and is cut, the note points at `get_event … from_unit=N`, and that serves every unit from N on, members or not. This is no release (the policy decides again), but a reader following the note leaves the bracket silently. Neither page says so.
6. **Untested: a cursor carried to another client.** The code is safe (the bracket check runs before the cursor), but no test hands a cursor of `within=lea` obtained by `local-harness` to `claude-code`.
7. **An event with no member unit left.** Members can hold an event whole with every unit excluded. Over MCP that event shows its heading with an empty fence and `Delivered(event, ())`, while the CLI prints nothing for it. This is cosmetic and releases nothing (the client sees the mail). After T5-b it can only arise through visible edges.
