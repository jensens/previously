# Task 5 report: the server

Status: DONE_WITH_CONCERNS. Commits `71218db` (dependencies) and `5694f77` (server, tests, docs) on `worktree-mcp-konzept`, base `3d9b911`.

## What was built

- **`contract/store.py`, `storage/postgres.py`:** `LogStore.observations(conn, *, since, until, source, after, limit)`. It reads observations in `(occurred_at, id)` order, strictly after `after`, half-open window, source via `EXISTS` on `source_key`, server-side cursor. `after` and `limit` go beyond the brief's signature, because the ruling asks for a bounded batch after the cursor. The store docstring now says the fourteenth method is called by `mcp_server`, not `core`; the `core` count command still gives 13 (measured). The test double `_ContestedLog` in `tests/test_redact.py` got the method.
- **`mcp_server/render.py`:**
  - R-8: `Shown.attachments` and `Shown.provenance`, both inside the fence; `ErrorMark(label, message)` rendered as `Error: <label> — <message>`, sanitized, one line.
  - R-9: `Page.consumed` and `Page.units`. A unit cut inside counts as appeared.
  - `render_page(..., more=False, next_hint=None)`. `more` puts a cursor after a last item when more items exist; `next_hint` words the footer's way on for `get_event`, and then the header names no cursor.
  - The `render_page` docstring is fixed for R-5.
  - The cursor carries the page number (`encode_cursor(..., page=2)`, `Position`, `decode_position`); `decode_cursor` keeps its contract. A decoded cursor refuses a naive moment, ids and pages outside 0..2^53-1, and a page below 2.
  - `render_text(title, lines)` renders results without customer content.
- **`mcp_server/read.py`:**
  - `chronicle` and `events` return a `Seen` of `Read`s (item, log entry, position, rule ids, event id).
  - `logged(seen, page)` builds `Delivered`/`Withheld` from the page only (R-9).
  - `withholding` gives the reason code and a sentence of policy names.
  - `circle_verdict` and `source_verdict` serve `list_circles` and `whoami`.
  - `BATCH = 200` is named and justified in its comment.
- **`mcp_server/auth.py`:**
  - `guarded(app, *, resolve)` checks `Authorization: Bearer` on every request, resolving on a worker thread.
  - Without a valid token it answers 401 with `Error: a valid bearer token is required` and `WWW-Authenticate: Bearer`.
  - It writes the client name into `scope["state"]["previously_client"]`.
  - Lifespan passes through; websocket scopes get nothing.
- **`mcp_server/server.py`:**
  - `build_server(log, *, stdio_client)` registers the five tools, two templates and two prompts; `build_app(log, *, allowed_hosts)` and `transport_security(...)` build the HTTP side; `run_stdio` and `run_http` start them.
  - `Service.answer` runs each call in one snapshot against the policy read anew, then writes `mcp_access` in `finally`. `era` comes from `ctx.protocol_version`.
  - A middleware safety net writes the access for calls the SDK refused before a handler ran, and rewords the refusal to `Error: <name> did not run: …`.
  - Arguments are recorded in a payload-safe form (`recordable`).
- **`cli.py`:** `mcp` and `serve`. Both import the server lazily: measured 0.67 s against 0.36 s for `import previously.cli`.
- **`.importlinter`:**
  - `mcp_server` joins the layer of `connectors | gate`, and the name follows.
  - A new contract, "Only the MCP server imports the MCP SDK", forbids `mcp`, `mcp_types`, `starlette` and `uvicorn`. Its five named edges are `server ->` each of the four, and `auth -> starlette`.
- **Docs:**
  - `cli.md`: 18 subcommands, the `mcp` and `serve` sections, exit-code rows, and the access example reason updated to the real wording.
  - `configuration.md`: 21 variables and a "Server settings" section.
  - `module-boundaries.md`: eight modules, 24/16/8 edges, the measured grep block (the pattern now `[a-z_]+`), nine contracts, and a section on the new contract.
  - Tutorial block retyped.
- **pyproject:** T201 measured at 64; `serve`'s start line is the new print.
- **CLAUDE.md:** the sixth suppression, recorded (see the decisions below).

## Decisions where the brief was silent

1. **401 without a known client writes no access.** Concept §5 and unit spec §7 say "every call, a rejected one too". A request with no or an unknown or revoked token has no principal: `Access.client` is required, and the wrapper doesn't know which MCP method the body holds. So it writes nothing, as R-10 allowed. A client known by name but no longer in force (stdio, or a revocation between the wrapper and the handler) writes an entry with the outcome `error`. The spec's "abgewiesen" is read as this case.
2. **The SDK refuses some calls before a handler runs:** arguments against the schema, or an unknown tool. These are caught by a middleware (`server.middleware`, which the SDK marks provisional), so assurance 3 holds for them too. A `ContextVar` mark stops double entries.
3. **An erased event is logged as `Delivered(event, (), ())`.** The placeholder is on the page, and R-9 says the log names what is on the page.
4. **`Head.subject = None`.** The subject is unit 1 of a mail, inside the fence, and is not repeated.
5. **Sender and recipients.** The sender is the first `from`/`sender` identity, the recipients are `to`/`cc`/`bcc`, each shown by name or else by address.
6. **Attachments** are rendered as `name (media_type, N bytes)`. The raw mail is left out, and an unnamed attachment shows as `unnamed`.
7. **Provenance** is rendered as `Found in`, then `Message-ID` (email, not `sha256:`) or else `Source key`, then `Forwarded in`.
8. **`get_event`:**
   - duplicate ids are served once;
   - `from_unit` applies to every id;
   - an id out of range is labelled `ids[<index>]`, since the number may not appear;
   - `from_unit` past the last unit gives an error line;
   - ids that don't fit the page are named in the footer as `call get_event with ids=[…]`.
9. **The chronicle with an unknown circle is an error**, not an empty page. An erased event drops out of a circle filter.
10. **`whoami`** lists source rules and "content of no circle and no source rule". **`list_circles`** decides each circle with only its own memberships.
11. **The reason wording:**
    - no rule: `circle X has no rule, so only local processing is allowed; this client (C) processes with P, which is not local` (`circles X, Y have no rule` when several);
    - a rule: `the rules of S do not allow P, the processor of this client (C): <decide's sentence>`.
12. **The tool descriptions are declarative noun phrases.** Field descriptions are in the schema. Pinned digest `393fe0fd…bd3fc`.
13. **`since`/`until`** take a date (midnight UTC) or a zoned moment; a naive moment is refused.
14. **The prompts' `since`/`until` are optional.** Client arguments echoed in a prompt are sanitized.
15. **Resource names in the access log:**
    - `name` is the template, such as `previously://event/{id}`;
    - the chronicle resource records `{"circle": name}`, so `access --circle` finds it.
16. **`A002` suppression on `id`.** The SDK binds URI template variables to parameters by name and refuses a mismatch (measured: `Mismatch between URI parameters {'id'} and function parameters {'event_id'}`), and `{id}` is the contractual template. CLAUDE.md demands that a new suppression be listed there, so I added one paragraph and changed "five" to "six". **This edits CLAUDE.md**; the controller may want to confirm it with the maintainer.
17. **Specs are cited from code as "unit specification, section N" or "concept specification, section N"**, without `§`, as in Task 4. They aren't frozen yet; Task 6 may want to repoint them to the new explanation page.

## Assurances 1–12

Every test in `tests/test_mcp_server.py` runs over `Client(server)` and `Client(server, mode="legacy")`, unless noted.

| # | Tests |
|---|---|
| 1 | `test_what_the_policy_withholds_never_appears_only_its_placeholder`, `test_a_rule_that_does_not_allow_the_chain_withholds_with_the_reason_code_rule` |
| 2 | `test_a_circle_without_a_rule_is_withheld_for_lack_of_a_rule_and_a_local_client_sees_it` (Review Focus 3), `test_two_circles_without_a_rule_are_named_together` |
| 3 | `test_every_call_writes_an_access_with_the_era_and_the_ids_of_the_policy`, `test_a_failed_call_writes_an_access_with_the_outcome_error`, `test_a_call_the_sdk_refuses_before_it_runs_writes_an_access_too`, `test_no_access_entry_carries_content_of_an_event`, `test_an_event_resource_with_an_id_that_is_no_number_is_an_error` |
| 4 | `test_a_client_revoked_while_the_stdio_server_runs_is_refused_from_its_next_call`, `test_a_rotated_token_stops_working_with_the_next_request_and_the_new_one_works` (Review Focus 2, over HTTP, then revoked), `test_without_a_valid_token_http_answers_401_with_one_sentence` (4 header variants), `test_no_protected_resource_metadata_is_published`, `test_a_header_naming_a_client_is_no_identity`, `test_no_token_stands_in_the_log` |
| 5 | `test_every_tool_answers_with_one_text_block_and_nothing_else`; `_text()` holds every result to the form in every test |
| 6 | `test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence` (plus the Task 4 render tests) |
| 7 | `test_control_characters_are_removed_and_counted_and_the_stored_bytes_stay` (`verify` stays green) |
| 8 | `test_the_cursor_walks_the_chronicle_without_gap_or_double` (37 observations, at least 2 pages, each ≤ `PAGE_CHARS`, equal to the store's order), `test_a_mail_over_the_page_is_cut_and_get_event_serves_the_rest` (Review Focus 4 and R-9) |
| 9 | Task 1's `tests/test_decide.py::test_adding_a_rule_never_widens_the_passing_candidates` (Hypothesis) and the restriction tests there; this task did not touch `decide` |
| 10 | `test_the_tool_list_matches_its_checksum` |
| 11 | `test_both_generations_give_the_same_results`: texts with the fence tags normalized and the era masked, plus the access entries without `era` |
| 12 | `tests/test_docs_references.py::test_the_reference_quotes_what_mcp_and_serve_say` (new), alongside the existing checks |

Further tests:

- Review Focus 5: `test_get_event_answers_every_id_on_its_own_line`, with valid, unknown, action, withheld, erased and 2^60 ids. It also checks the access entries and the recorded arguments, where 2^60 becomes a string.
- `test_get_event_refuses_more_than_twenty_ids_as_a_whole`, `test_list_circles_…`, `test_whoami_…`, `test_policy_gaps_…`, `test_the_resources_are_templates_…`, `test_the_prompts_…`, `test_the_window_and_the_source_narrow_the_chronicle`.
- HTTP: `test_with_a_token_http_serves_the_client_it_names` (both modes over `httpx2.ASGITransport`) and `test_the_host_check_lets_through_only_the_allowed_names`. A foreign Host gets 421, and 200 once it's in `allowed_hosts`.
- `tests/test_render.py`: 19 new tests for R-8, R-9, `more`, `next_hint`, the page in the cursor, forged cursors, and `render_text`.
- `tests/test_cli.py`: help names `mcp` and `serve`; `mcp` without the variable returns 2 before it connects; `mcp` for a revoked or unknown client returns 2; `serve` with a bad port returns 2.
- `tests/test_contracts.py`: `test_the_mcp_sdk_outside_the_server_breaks_its_contract`, 4 packages × {core, mcp_server}.

## Mutations

Each mutation was measured red with the code restored afterwards. The control, `tests/test_mcp_server.py` plus `tests/test_docs_references.py` unmutated, was green with 73 passed (before the last 2 tests were added).

| Mutation | Result |
|---|---|
| 1. The per-content check removed (`if False:` instead of `decision.chosen is None`) | red, 2 failed |
| 2. `mcp_access` only on success | red, 4 failed (failed-call and revoked-client tests) |
| 3. The `WithheldMark` reason carries the mail's headers (subject, addresses) | red, 2 failed |
| 4. The wrapper lets through without a token | red, 5 failed (401 and rotation) |
| 5. One description changed by a comma | checksum red, 2 failed |
| 6. `import mcp` appended to `core/units.py` | `lint-imports`: "Only the MCP server imports the MCP SDK BROKEN", `previously.core.units -> mcp`; restored, 9 kept. A permanent probe test exists too. |
| 7. R-9: all read items logged, with their read units | red, 2 failed. The units half alone is red at `delivered.units` (1..81 against 1..61). |
| 8. The safety-net middleware removed | red, 2 failed |
| 9. The page's 401 sentence changed | doc reference test red |

## Gates

All six gates were run on the final tree, before the commits.

| Gate | Result |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 119 files already formatted |
| `uv run pyright` | 0 errors |
| `uv run lint-imports` | 9 kept, 0 broken |
| `uv run pytest --cov --cov-report=term-missing` | 1509 passed, total coverage 97.31%. Server modules: auth 91%, read 96%, render 96%, server 92%. |
| `make -C docs html` / `vale` / `linkcheck` | build succeeded / 0 errors / build succeeded, `output.txt` empty |
| `uv run pip-audit --skip-editable` | No known vulnerabilities found |

The tutorial block was retyped from one run of `uv run pytest` on the final tree: 1509 passed, seed 1372394948. To make that one run green, the page's `N passed` was first set to the tree's count; then the whole block was replaced by that run's output, without its `rootdir:` line.

The server was also run by hand against a throwaway `postgres:17` container, now stopped:

- `previously mcp` over piped stdio answered `initialize` and `tools/call`.
- `previously serve` on 127.0.0.1:18765 answered 401 with the sentence, and a legacy `initialize` with a token.
- `serve` exits 143 on SIGTERM (as every command) and 0 on SIGINT; `cli.md` says so.

## Concerns

1. **CLAUDE.md edited** (the sixth suppression, `A002`), as its own rule demands. Please confirm with the maintainer.
2. **The safety net uses the SDK's middleware API, which the SDK calls provisional** ("the signature may change in a 2.x minor release"). pyright would catch a signature change, and mutation 8 a silent loss.
3. **Named limit, observed by hand:**
   - On stdio, a call still running when stdin closes writes its `mcp_access`, but its answer is never sent: the entry names a delivery the client didn't receive.
   - Over HTTP the mirror case is the named limit of unit spec §7.
4. **The chronicle bound is per query (`BATCH = 200`), not per call.** A sparse circle filter reads the log in batches until a page is full or the log ends. This is spec §13 open point 1, a projection of its own.
5. **`PAGE_CHARS` is still not measured against real mail.** Spec §13 point 2, left for the acceptance run.
6. **The concept example shows the subject above the fence; here it is unit 1, inside it** (consistent with R-4).
7. **`pyproject.toml`'s T201 comment change landed in the dependency commit `71218db`, not in the server commit.** Cosmetic.
8. **For Task 6:**
   - the spec citations in the code are not yet repointed;
   - the reference page for tools, resources and prompts doesn't exist yet;
   - `cli.md` quotes the 401 sentence and the `mcp`/`serve` errors, held by the new doc test.

## Fix round 1

The fix round is commit `964584f` on top of `5694f77`, and it closes every item.

### I-1 / R-11: no new suppression

- The template is now `previously://event/{event_id}` and the parameter is `event_id`. The `# noqa: A002` is gone.
- `src` has one `noqa` left, the old `C901`.
- The access arguments are now `{"event_id": …}`, and the tests expect the new template.
- CLAUDE.md is reverted: `git diff 3d9b911 -- CLAUDE.md` is empty.
- The tool-list digest is unchanged, because templates aren't part of the tool list.

### I-2 / R-13: the cursor carries no time

- **`render.py`:**
  - `encode_cursor(after: int, filters, *, page)` now writes `{"after": <id>, "filters": …, "page": n}`.
  - `decode_position` checks the id and the page against 0..2^53-1, and requires the page to be at least 2.
  - `decode_cursor` returns the id.
  - `CURSOR_REFUSED` is public.
  - The docstring says why the cursor holds no time, and that what stays visible is the order of placeholders between visible events.
- **`read.py`:** `resume_point(log, conn, id)` returns `(occurred_at, id)` for an observation, and `None` otherwise. `Read.position` is removed.
- **`server.py`:** a malformed cursor, one for other filters, and one that names no observation all give the same sentence: `Error: cursor is not valid for these filters; call again without a cursor for the first page`. A distinct answer would tell a forger which ids exist.
- **New test `test_a_cursor_after_a_placeholder_tells_no_time`** (both modes):
  - Three long `huber` mails, each followed by a `team` mail. The first page ends on a withheld placeholder, and that is asserted.
  - The test decodes the cursor and pops the filters, which are the client's own echo; nothing left may match a date or a time.
  - It then pages on: 6 items, no duplicates.
  - **Measured red against the old format:** the decoded cursor was `{'after': ['2026-10-06T10:02:30+00:00', 28], 'page': 2}`, which is the time of the withheld `team` mail.
  - The gap-free test `test_the_cursor_walks_the_chronicle_without_gap_or_double` stays green.
- **Render tests:**
  - The cursor tests are updated, including a forged-payload list with the old list form, a string id, 2^60, -1, `True`, page 1 and page `True`.
  - New: `test_a_cursor_carries_an_id_and_no_time`.
- **Concern for Task 6:** this changes plan decision 6. The explanation page should name the limit that the order of placeholders stays visible.

### I-3: identity by token only

- `test_a_header_naming_a_client_is_no_identity` (both modes, over HTTP):
  - It sends the `local-harness` token plus `X-Previously-Client: claude-code` and `Mcp-Client: claude-code`.
  - `whoami` says `client local-harness`, and the access entry's client is `local-harness`.
  - Without a token the request still gets 401.
- **Mutation:** `client_name` prefers `X-Previously-Client`. The test goes red in both modes (`'client claude-code' == 'client local-harness'`). Restored: green.

### M-1: what the PRM path answers

`cli.md` now says that `/.well-known/oauth-protected-resource` answers 404 with a valid token and 401 without one. `test_no_protected_resource_metadata_is_published` asserts `(404, 401)`.

### M-2 / R-14: every direct import is declared

I measured the third-party imports of `src` and `tests` with an AST walk.

- **Avoided:**
  - `anyio` in `src`: `asyncio.to_thread` and `asyncio.run` replace it.
  - `mcp_types` in `src` and in the tests: `mcp.types` re-exports `CallToolResult`, `TextContent` and `TextResourceContents`.
  - The edge `server -> mcp_types` is gone from `.importlinter`, which now has 4 ignored imports. `mcp_types` stays forbidden.
- **Declared, with verdicts in DEPENDENCIES.md** (date, version, evidence):
  - `starlette>=0.48` in the main dependencies. The verdict says why avoiding it isn't clean: `build_app` returns the SDK's Starlette app and adds the middleware through Starlette's own method.
  - `botocore>=1.43` in the main dependencies. It was imported by `storage/s3.py` since 2026-10-05 without being declared; I applied the rule tree-wide.
  - `anyio>=4.10` and `httpx2>=2.10` in the `test` extra. That is where the project's test-only imports already live (pytest, hypothesis, testcontainers); there is no separate "dev group" for tests.
- `uvicorn`'s reason now reads "declared because `src` imports it directly, although `mcp` brings it too, the rule `starlette` and `botocore` follow as well".
- `uv.lock` changes only in metadata: no version moved.
- `module-boundaries.md` follows: 13 arrows leave the package, the diagram has no `mcp_types` arrow, 4 ignored imports, and a sentence says that `mcp_types` is imported nowhere.

### M-3: ruling citations

Every `R-` citation in `src` and `tests` now reads `ruling R-<n> of the 2026-10-11 MCP read access plan`, one `ruling` per label:

- `render.py`: R-5 twice, R-6, R-8, R-9, R-13;
- `read.py`: R-9;
- `auth.py`: R-10;
- `tests/test_mcp_server.py`: R-9 twice, R-13;
- `tests/test_render.py`: R-8, R-9.

Each keeps its reason beside it. Checked with the census `grep -rnioE 'ruling (P|T[0-9]+|R)-…'`.

### M-4, M-5, M-6

- **M-4:** the resource and prompt bodies take `conn: Conn`.
- **M-5:** the misnamed test is now `test_more_without_items_gives_no_cursor`.
- **M-6:**
  - The token test is now `test_no_token_stands_in_the_log_or_the_server_log`. Before it searches, it makes real HTTP calls: one served, one wrong token, a rotation, the old token refused, the new one served, a revocation, the new one refused. It then asserts that no token is in the action payloads or in `caplog` at DEBUG.
  - New: `test_a_cursor_that_does_not_lead_on_is_an_error` (both modes). It covers, through the tool, a cursor for other filters and forged cursors naming a policy event and a missing id, each getting the fixed `Error:` and an `error` access entry.

### Mutations re-run on the fixed tree

All nine mutations from the first round are still red, and the control is green (`tests/test_mcp_server.py` plus `tests/test_docs_references.py`, 82 passed). The new ones:

- the cursor in the old format: red;
- a wrapper or tool that prefers the header: red.

### Gates (fix round, final tree)

| Gate | Result |
|---|---|
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 119 files already formatted |
| `uv run pyright` | 0 errors |
| `uv run lint-imports` | 9 kept, 0 broken; the MCP contract has 4 ignored imports |
| `uv run pytest --cov --cov-report=term-missing` | 1517 passed, total coverage 97.31% |
| `make -C docs html` / `vale` / `linkcheck` | build succeeded / 0 errors, 0 warnings / build succeeded, `output.txt` empty |
| `uv run pip-audit --skip-editable` | No known vulnerabilities found |

- T201 is unchanged at 64.
- The tutorial block was retyped from one run of `uv run pytest`: 1517 passed, seed 1000530603. To make that one run green, the page's count was first set to the tree's count; then the whole block was replaced by that run's output.

### Concerns after the fix round

1. **Plan decision 6 changed** (the cursor holds the id only). Task 6's explanation page should name the limit that the order of placeholders stays visible.
2. **`botocore` is now declared tree-wide.** It is outside this task's own code, but R-14 is general.
3. **The test dependencies went into the `test` extra rather than `dev`**, to match where pytest and hypothesis already are.
4. **The three edge cases the review named only are left as they were.**
