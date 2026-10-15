# Task 5 report — the chronicle of a bracket

Status: DONE_WITH_CONCERNS. Commit `c205fea` on `worktree-zuordnungen-2` (base `b64d43f`), not pushed.
Test count 2770 → 2790 (`2790 passed`).

## What was built

### Core

- `core/graph_read.py` `bracket_members(log, conn, graph, bracket) -> Members`: ruling T5-a's T4-b fallback in one place. When the reader's graph is a `ProjectedGraph` (the projection stood where the catch-up left it) it calls `read_brackets` over the projection rows; otherwise (the reader folded) `members(bracket_edges(graph, vocabulary), bracket, bracket_kinds(vocabulary))`. So a reader finds the members in the very graph it decided to read; CLI `_reader_graph` and MCP `Service.read_graph` stay the only places that decide projection-vs-fold.
- `core/members.py` `chronicle_selection(found: Members) -> ChronicleSelection`: `Members` as a query takes it.
- `contract/rows.py` `ChronicleSelection(events: frozenset[int], excluded: frozenset[(event, seq)], units: frozenset[(event, seq)])`: every unit of `events` except `excluded`, plus each of `units`.

### CLI `chronicle --within N` (cli.py `_cmd_chronicle`, `_bracket_selection`)

- `--within` (`type=int`, `metavar=N`). With it: `_caught_up(storage)` before the snapshot, then in a snapshot `tip_and_bookmark`, `_reader_graph` (fallback + stderr line as the listings), the stands check, `bracket_members`, `chronicle_selection`, `read_chronicle(..., within=selection)`. Same output line, truncation notice, lag line.
- The command now reads in `storage.snapshot()` for both paths (was `begin()`): T4-b's `projection_stands` is meaningful only in a snapshot, and members and rows are read at one moment. `tip_and_bookmark` stays one statement. All phase-1 chronicle tests unchanged and green.
- Refusal: `not 1 <= N <= MAX_SAFE_INT or N not in EntityTypes(graph)` → `InvalidPayload("--within N is not an entity that stands")` → `Error: …`, exit 2. Covers a missing id, a relation, an event, a retracted entity, 0. An empty bracket prints nothing, exit 0.
- `chronicle --within` added to the cli.md sentence that lists the readers that catch the graph up.

### SQL versus Python: SQL, exactly

`PostgresStorage.read_chronicle(..., within: ChronicleSelection | None = None)` selects precisely in the query, so `LIMIT` counts only the bracket's units (a Python refinement after the SQL limit would give short pages and wrong truncation notices — measured, m4 below):

```sql
WHERE (event_id = ANY(:events::BIGINT[]) AND (event_id, seq) NOT IN (SELECT … FROM unnest(:e::BIGINT[], :s::INTEGER[]) AS anon(event_id, seq)))
   OR (event_id, seq) IN (SELECT … FROM unnest(:e2::BIGINT[], :s2::INTEGER[]) AS anon(event_id, seq))
```

Arrays (five bind parameters in all) rather than an expanding `IN`, so a big bracket doesn't hit PostgreSQL's bind-parameter limit. `_pairs` builds the `unnest` with `table_valued(...).render_derived()` (without `render_derived` the column names were not rendered: first run failed as "schema incomplete", i.e. an undefined column mapped to `MigrationPending`).

### MCP `previously(within=N)`

- Tool parameter `within: int | None` (after `until`, before `cursor`); `_WITHIN` field description; `_CHRONICLE` description extended (`within` combines with the other filters; a withheld event is a placeholder "with within as without"). `INSTRUCTIONS` untouched.
- `filters` gets `within` as text (`str(within)`): it enters the cursor and the title (`chronicle · within N`). The access entry's `call` records `within` as the int the client gave (`_given(**{**filters, "within": within}, cursor=cursor)`).
- `Service.bracket(conn, policy, client, N) -> Members`: graph of the call (`graph_now`), then `1 <= N <= MAX_SAFE_INT`, `N in EntityTypes(graph)` and `graph_view(…, (N,)).seen(N)`; any failing → `Refused(f"within {N} is not an entity that stands")` — one sentence for hidden, missing, relation, event, 0. Then `bracket_members`.
- `read.chronicle(..., within: Members | None = None)`: after the circle filter, events not in `within.events` are skipped; everything else goes through `_decided` (the policy) unchanged; for a shown event the units passed to `_shown` are filtered by `within.holds`, so `Delivered` names only shown units. Filtering in Python over `observations` as ruling T5-a says; `LogStore` unchanged.
- Resource template and prompts unchanged (they pass no `within`).
- `TOOLS_SHA256` retaken: `56be7eefe6910b3eef50c74d80f7543ac1364bfac0316cc5d1d5abfe4d26cbec`.

## Tests (20 new)

`tests/test_cli.py` (6):
- `test_chronicle_within_shows_the_units_of_a_bracket_and_one_level_up_those_of_the_club` — Markus (Z §17 point 2): party → `1/3`, club → `1/3`, XZ → `1/1, 1/2`; control: whole chronicle 6 lines. Then a unit assigned after `project`: the reader catches the graph up and finds it, and stderr carries the lag line; XZ loses unit 2. Then `redact units 1 3`: party keeps only unit 2, XZ is empty (the whole-mail assignment falls, T2-b), `verify` clean.
- `…_counts_its_limit_and_its_window_among_the_units_of_the_bracket` — A, C, D assigned, B not: `--limit 3` exact, `--limit 2` → A, C + truncation notice, window → C; control: same window without `--within` has 2 lines.
- `…_refuses_what_is_not_an_entity_that_stands_and_shows_an_empty_one` — 999999, a relation, an event, a retracted entity, 0; control: empty entity → no lines, exit 0.
- `…_finds_from_the_projection_what_the_fold_finds` — `_listed_history` + an open proposal of unit 1 → party: projection vs `projected_graph` swapped for the fold, four brackets; also pins T2-c (the proposal adds unit 1 to party and XZ keeps it).
- `…_folds_the_log_when_the_projection_does_not_stand[rebuilt|failed]` — T4-b: same lines, exactly one stderr line.

`tests/test_chronicle.py` (2):
- `test_the_query_selects_the_units_a_bracket_holds_before_its_limit` — Hypothesis (200 examples) against PostgreSQL: random `Members` (events 1–4, units 1–5, incl. ids the log lacks) → `read_chronicle(within=chronicle_selection(m))` equals the whole chronicle filtered by `holds`, and with a random limit its prefix. Holds `chronicle_selection` and the SQL together.
- `test_the_query_meets_each_form_of_a_bracket` — fixed example.

`tests/test_mcp_server.py` (6 × 2 modes = 12):
- `test_previously_within_shows_of_markus_mail_only_the_units_of_the_bracket` — Markus over MCP: title `previously · chronicle · within N · page 1`; party → unit 4 only (the caterer), club → 4, XZ → 1–3; access entry `{"within": N}`, delivered `(mail, (4,))`; control: without `within` the mail shows 1–4 among others.
- `…_finds_by_the_fold_what_it_finds_by_the_projection` — server without the projection (fold) gives the same pages for 4 brackets; only the missing id is an error.
- **RF3** `…_shows_a_withheld_mail_as_the_placeholder_it_is_without` — a `team` mail (no rule) assigned to the party: `claude-code` gets the identical placeholder line with and without `within`, its content absent, access `withheld` names it; control: `local-harness` sees the content.
- **RF3** `…_shows_no_unit_the_client_does_not_see_without_it` — for both clients and three brackets (with withheld mails of `team`, `huber/team` and `bauer` assigned), delivered `(event, unit)` with `within` ⊆ without, withheld ⊆ withheld.
- **RF3** `…_a_bracket_the_client_may_not_see_is_refused_as_a_missing_one` — Lea (hidden), 999999, a relation, the mail, 0 → one text after replacing the id: `Error: within ID is not an entity that stands`; control: `local-harness` gets Lea's (empty) chronicle.
- `…_carries_within_in_its_cursor_from_page_to_page` — five long member mails interleaved with five non-members: ≥2 pages, title on each, cursor filters `{"within": "N"}`, seen == members + Markus mail in order; the cursor without `within` is refused.

Before implementation: the 6 CLI tests and 8 of the 12 MCP tests red (unknown argument). The 4 green ones before were the fold-equivalence test (both servers errored alike — since then strengthened: only the missing id may be an error) and the RF3 subset test, which is vacuous without `within` and whose strength comes from m1 below.

## Mutations (each red; restore → green; harness `scratchpad/p2t5/mutate.py`, run over the `within`/`query` tests: 52)

| Mutation | Red | Control green |
|---|---|---|
| m1 `within` bypasses the policy (member events become `_Pending(row, key, None)`, no `_decided`) | withheld-placeholder test ×2, subset test ×2 | Markus MCP test, refused test, all CLI (48 passed) |
| m2 all units of a member event shown | Markus MCP ×2, placeholder test ×2 (its `_units_shown` check) | subset test, refused test (48 passed) |
| m3 hidden bracket not checked (`seen` dropped) | refused-as-missing ×2 | Markus MCP, placeholder (50 passed) |
| m4 CLI: limit in SQL, selection in Python afterwards | limit test, Markus CLI, projection-vs-fold CLI | refused test, fallback tests, all MCP (49 passed) |
| m5 SQL without the `excluded` clause | property, fixed query example, Markus CLI, projection-vs-fold CLI | limit test, refused test (48 passed) |
| m6 CLI reads `projected_graph` directly, no T4-b fallback | `…does_not_stand[rebuilt]` | `…[failed]` (51 passed) |
| m7 cursor encoded without `within` | cursor test ×2 | Markus MCP (50 passed) |

After restore: files byte-identical to the backups (`cmp`), 52 passed.

## Docs (plone-doc-style:author loaded)

- `reference/cli.md`: `--within` row, a paragraph on what belongs, limit counting, the refusal block (`Error: --within 999 is not an entity that stands`), exit-code row for `chronicle`, `chronicle --within` in the readers-catch-up sentence.
- `reference/mcp-tools.md`: `within` row in the `previously` table, title example, units-only and placeholder sentences, hidden = missing, cursor carries `within` as text / access entry as given; the error line `Error: within 12 is not an entity that stands` in "Errors of a call" (held by `test_the_mcp_reference_quotes_what_the_server_says`).
- `explanation/graph.md`: new `(chronicle-of-a-bracket)=` "The chronicle of a bracket finds, and releases nothing" — declared kinds, the more specific replaces the general (Markus), open proposals, periods, finding after the gate, hidden bracket, and what it does not hide (see concern 1).
- `explanation/projections.md` (graph-readers): the chronicle of a bracket reads only rows; CLI selects in the query, MCP filters while reading the log.
- New how-to `how-to/assign-mails-and-read-a-bracket.md` (in the index after the club how-to). Every command and typed output was run on 2026-10-15 against a scratch PostgreSQL 18 (testcontainers, `tests/database.py` settings; scripts in `scratchpad/p2t5/session{1,2,3}.sh`), container stopped afterwards. The ids (13, 14, 15, 17, 18, 19) and the outputs are those of the run.
- `.vale-styles/…/accept.txt`: `Markus` (capitalized, so the lowercase count in `.vale.ini`'s comment is unchanged).
- Tutorial test block retyped from one green `uv run pytest`: `collected 2790 items`, `2790 passed in 335.65s (0:05:35)` (rootdir line blanked as before).

## Counts re-measured

- `T201`: no `print` added — unchanged.
- `contract/store.py` protocols untouched (`read_chronicle` is outside the protocols); `LogStore` and the MCP `log.` call count unchanged.
- cli.md "thirty-four subcommands" unchanged.

## Gates (final tree, 2026-10-15)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            143 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        2790 passed in 342.06s; TOTAL 98%;
                                        core/graph_read.py, core/members.py,
                                        storage/postgres.py, contract/rows.py 100%;
                                        no new line uncovered in cli.py, read.py, server.py
make -C docs html                       build succeeded
make -C docs vale                       0 errors, 0 warnings and 0 suggestions in 51 files
make -C docs linkcheck                  build succeeded
```

No flake in the final runs. An earlier full run had a 95% total only because comments were edited during it (line numbers shifted under coverage); the final run is on the untouched tree.

## Concerns

1. **The walk doesn't check the client's view of edges.** Members follow every standing assignment and hierarchy edge, whatever the client may see of them. A client that sees event E and bracket B learns that E belongs to B even when the path runs through an entity or a `part_of`/`concerns` relation it may not see (it learns neither which). No content or unit leaks (RF3 holds and is measured), and a placeholder under `within` tells "something withheld belongs here", as one under `circle` does. Documented on the explanation page. Closing it would mean `relation_visible` per edge over the closure — a maintainer decision.
2. **MCP cost on a small bracket in a large log**: the chronicle reads `observations` in batches of 200 and filters in Python (T5-a), so a sparse bracket can read the whole log for one page; same class as the existing `circle` limit, and the BATCH comment now says so. Not measured (final review's measurement plan lists `chronicle --within` on the CLI only).
3. **The CLI `chronicle` now reads in a snapshot also without `--within`.** Behavior is the same (all phase-1 chronicle tests green); stated in the comment.
4. **Cursor filters echo `within` as text** (`"12"`) while the client gave a number; documented in mcp-tools.md. The access entry keeps the number.
5. The how-to says "the release after `0.1.0a7`" for the first release with assignments — Task 6 may want to adjust when the version is cut.
6. Landkarte not touched (Task 6): concern 1 and 2 may belong there.

---

# Fix round 1 (review `task-5-review.md`, rulings T5-b, T5-c) — commit `08b1882`

Test count 2790 → 2804 (`2804 passed`).

## I-1 / T5-c: over MCP an edge counts only where the client sees it

- `core/graph_read.py`: the edge reading is split out. `projected_bracket_edges(store, conn, kinds)` builds the edges from the rows. `reader_bracket_edges(log, conn, graph) -> (edges, kinds)` takes them from the rows of a `ProjectedGraph`, or from the fold otherwise (T4-b). `read_brackets` and `bracket_members` (CLI: every edge) sit on top of these.
- `core/members.py` `deciding_edges(edges, found, kinds)` gives **the reviewer's bound** (⚠️ 3), made exact and proven. `found` is `members` over *all* edges. The deciding edges are:
  - every hierarchy edge (entity start) with `to ∈ found.brackets`;
  - every assignment (event start) whose event is in `found.events`. This includes a unit's own edges into brackets outside the walk, which is channel 3.

  Why nothing else matters: taking edges away only shrinks the walk and the assignments into it. It adds a unit only by removing the own assignment that excluded it, for an event whose whole is assigned into the walk, and that event is already in `found.events`.
- `mcp_server/read.py` `seen_members(log, conn, policy, client, graph, bracket)`:
  - walk all edges;
  - take the deciding edges;
  - build one `graph_view(…, deciding subjects)`, which reads the sources of those threads and their ends;
  - run `members` over the deciding edges with `view.seen(subject)`, which is `relation_visible` for a relation thread.

  The cost is proportional to the bracket's edges, not to every assignment. An empty deciding set returns at once. `Service.bracket` calls it after the hidden/missing check, which is unchanged. The CLI still uses `bracket_members` (the operator walks every edge).
- Tool description `_CHRONICLE` updated ("found only through the assignments and parts this client may see … within leaves it out"). `TOOLS_SHA256` retaken: `bb1cde8cebeb3592d48a7289795433beac4dcbb7a08433e9106c2f710da91f9e`.

## I-2: tests and pages

- `test_previously_within_shows_a_withheld_mail_as_the_placeholder_it_is_without` is replaced by `test_previously_within_leaves_out_a_mail_the_client_may_not_see`, which is case **(a)**. The `team` mail assigned to the party is absent under `within` (no URI, `withheld == ()`) and is a placeholder in the whole chronicle. Control: `local-harness` finds it (`{mail:[4], hidden:[1,2]}`).
- **(b)** `…_does_not_walk_through_an_entity_the_client_may_not_see`: a hidden project C on the plain mail, `C part_of party`, a visible mail assigned to C. `claude-code` gets only `{markus:[4]}` under party. Control: `local-harness` also gets the mail.
- **(c)** `…_does_not_walk_along_a_part_of_the_client_may_not_see`: child visible, `part_of` resting on the plain mail. `claude-code`: the mail is absent under party but present under the child, which is a same-client control. Control: `local-harness` finds it under party.
- **(d)** `…_counts_no_hidden_assignment_of_a_unit_of_its_own`: a mail assigned whole to XZ, with unit 4 assigned to a hidden project. `claude-code` gets `[1,2,3,4]` and `local-harness` gets `[1,2,3]`, which is what the CLI prints.
- `tests/test_members.py`:
  - `test_members_over_any_part_of_the_edges_turn_only_on_the_deciding_ones`: Hypothesis, 400 examples. For random edges and a random "seen" mask, `members(seen ∩ edges) == members(seen ∩ deciding)`.
  - `test_an_excluding_edge_out_of_the_walk_is_among_the_deciding_ones`: a fixed example of channel 3.
- Pages:
  - `graph.md` (chronicle-of-a-bracket): the old sentences at :222 and :226–228 are replaced. New text: finding mustn't reveal what the rest of the server hides; over MCP an edge counts only where the client sees it; what that means for a withheld mail, a hidden part or `part_of`, and a hidden bracket; the CLI walks every edge, so the client can find less, or in case (d) one more unit of a mail it sees.
  - `mcp-tools.md`: the `previously` section states the same rule, the "one more unit" case, that an event with no unit left isn't shown, and that a cut note's `get_event` serves units beyond the bracket (⚠️ 5).
  - `cli.md`: one sentence saying every edge counts on the CLI and only seen ones over MCP.
  - `projections.md`: the bound and the scan stop.
  - The how-to's MCP sentence.

## M-1: the scan is bounded

`read.chronicle` with `within` first calls `_last_member` (one `events_by_id` over the member events → the max `(occurred_at, id)` among observations).
- No member observation, or a cursor already past it → `Seen(())`, without reading any observation.
- Otherwise the loop returns once the position passes the last member.

This works on every page, and also with `since` and `circle`. I chose a position lookup over counting because counting breaks under `circle`/`since`, which drop members, and on later pages.

Cost: one query of the bracket's events, payloads included, per call. `events_by_id` becomes the ninth `LogStore` method the server calls; the count in `contract/store.py` was re-measured and updated.

Test `test_previously_within_reads_the_log_only_up_to_the_last_event_of_the_bracket`:
- uses `_CountingScans`, which counts `observations` calls, with 450 later chat events;
- an empty bracket gives 0 scans and the party (Markus mail before them) gives 1;
- control: a bracket whose only event is the last of the log gives 3.

## M-2

`cli.md`: "refused before the chronicle is read, after the catch-up of the graph projection". The how-to now says "and the chronicle isn't read".

## ⚠️ items

- ⚠️ 7: `_read_of` returns `None` for a shown event with no unit content left under `within`, and the event is skipped before the page-size check. Test `test_previously_within_leaves_out_a_mail_with_no_unit_of_the_bracket_left`: a mail whole → XZ with all four units → party is not under XZ and not in `delivered`. Control: the party shows it whole.
- ⚠️ 6: `test_previously_within_refuses_a_cursor_carried_to_a_client_that_may_not_see_the_bracket`: five long mails assigned to Lea; the cursor from `local-harness` is refused for `claude-code` with `Error: within N is not an entity that stands`. Control: `local-harness` continues with the cursor. This needs no mutation: it holds the existing order of checks.
- ⚠️ 5: documented, not changed.
- ⚠️ 4 (timing of hidden vs. missing): not changed, same class as the write tools.
- The chronicle loop was split into `_filtered_in` and `_read_of` to stay under C901. There is no suppression.

## Mutations (fix round; harness `scratchpad/p2t5/mutate2.py`, over the `within`/`deciding` tests, 32 in all)

| Mutation | Red | Control green |
|---|---|---|
| f1 visibility filter removed (`seen_members` returns `members(edges)`) | (a), (b), (c), (d), both modes | Markus, refused, cursor, scan, no-unit tests (24 passed) |
| f2 deciding assignments limited to edges into the walk (channel 3 open) | (d) ×2, the property, the fixed deciding test, Markus MCP ×2, no-unit ×2 | (a), (b), (c), refused (24 passed) |
| f3 no hierarchy edge among the deciding ones | the property, (b) ×2, (c) ×2, Markus MCP ×2, subset ×2 | (a), (d), refused (23 passed) |
| f4 no early return for an empty bracket | scan test ×2 | all others (30 passed) |
| f5 no stop at the last member | scan test ×2 | all others (30 passed) |
| f6 an event with no unit left is shown | no-unit test ×2 | all others (30 passed) |

After restore the files were byte-identical (`cmp`) and the tests went back to 32 passed.

## Gates (final tree, 2026-10-15, fix round)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            143 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        2804 passed in 351.43s; TOTAL 98%;
                                        core/graph_read.py, core/members.py 100%;
                                        the new lines of mcp_server/read.py covered
make -C docs html                       build succeeded
make -C docs vale                       0 errors, 0 warnings and 0 suggestions in 51 files
make -C docs linkcheck                  build succeeded
```

Before the gates, `tests/test_mcp_server.py`, `test_chronicle.py`, `test_cli.py`, `test_graph_read.py`, `test_members.py` and `test_docs_references.py` passed (868). The tutorial was retyped from one green `uv run pytest`: `collected 2804 items`, `2804 passed in 344.98s (0:05:44)`. No flake.

## Open

- ⚠️ 4 (timing of hidden vs. missing) and ⚠️ 5 (a cut note leaves the bracket) are documented or accepted, not changed.
- `_last_member` reads the payloads of all member events once per call. For a very large bracket that is the price of the bound; not measured.
