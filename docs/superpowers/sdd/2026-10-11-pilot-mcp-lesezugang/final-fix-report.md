# Final fix wave — report

Date: 2026-10-11. Worktree `worktree-mcp-konzept`, from `2e71dc3`.

Commits:

- `5102e1d` mcp_server: final fix wave (code, tests, the pages that follow the code)
- `d51b671` map, unit spec header, handoff
- `fb890d9` tutorial: retype the test run, 1537 passed

Every mutation below was applied to the working tree, measured, and reverted
(`git diff` checked after each revert). "Control" is the test or case that
stays green under the same mutation, or the unmutated run.

## Code

### 1. `policy gaps` named circles with a rule (code I-1, ruling R-16)

- `Withheld` has two new required fields, `uncovered` (the circles of the
  event without a rule, from `decision.fallback.circles`, empty when there is
  no fallback) and `source` (the event's source key source, or `None`).
  `read._decided` fills both. Payload keys `uncovered` and `source`;
  `_WITHHELD_KEYS`, `_payload`, `parse_access`, the form check
  (`_withheld_problem`, split out of `_entry_problem` for C901) follow.
- `_mcp_gaps` counts `uncovered`; with none, `source:<source>`; with no
  source, `event:<id>` — the gate's resolution.
- `uncovered` is filled from the fallback whatever the reason code (true
  statement of fact); `gaps` still counts only `no_rule`.
- Tests: `test_gaps_count_only_the_circles_without_a_rule_and_else_the_source`
  (three circles, two with a rule → only `circle:team`; two no-circle events
  of `email` → `source:email 2`; one without source → `event:8`);
  `test_policy_gaps_counts_what_this_server_withheld_for_lack_of_a_rule` now
  asserts the whole mcp list is `["- circle:team · mcp · 2"]` (reviewer's
  probe shape: `plain` involves huber, office, team); the server test of the
  `plain` mail asserts `uncovered == ("team",)`, `source == "email"`;
  form-check list has four new broken cases; the sketch test carries both
  keys; the no-content tests run with the new fields.
- Mutations:
  - old counting (`item.circles or event:`): 3 red (the new unit test, both
    generations of the server test); control `test_gaps_count_what_mcp_withheld…`
    and `test_gaps_ignore_a_withholding_that_a_rule_caused` green.
  - source branch disabled: new unit test red, 3 others green.
  - `uncovered` form check removed: `test_verify_finds_a_broken_form` red.
- `cli.md`'s `policy gaps` example: the output format did not change, so it
  was not retyped; the prose now says what is counted. `mcp-tools.md` gained
  a `source:` line and two sentences.

### 2. Every call read every action (code I-2, ruling R-17)

- `LogStore.actions(conn, action)` in the protocol and in
  `PostgresStorage`: `kind = 'action' AND payload->>'action' = %s`, chain
  order, server-side cursor; no migration, no index. `read_policy` and
  `clients.client_rows` (which reads only policy actions) use it.
  `read_by_kind`'s docstring names the exception.
- Not switched (not policy actions): `read_access`, `gaps`, `redaction`,
  `redact._calls`. Named in the map and on the explanation page.
- Test wrappers: `_ContestedLog` (test_redact) delegates `actions`;
  `_RevokingAfterTheRead` (test_policy) now hooks `actions`, since that is
  what `read_policy` reads.
- New test `test_actions_yields_only_the_actions_of_that_name_in_chain_order`
  (control: an observation whose payload names `policy`, an erased action, an
  action without the name).
- Mutations: name filter removed → red; kind filter removed → red;
  `read_policy` back on `read_by_kind` → the revoked-meanwhile case of
  `test_a_membership_checked_while_its_circle_is_revoked_is_refused` red,
  its control green.
- **Timing** (scratch test, testcontainer `postgres:17`, best of 3, each row
  20 delivered + 10 withheld entries, 2026-10-11):

  | `mcp_access` rows | before | after |
  |---|---|---|
  | 0 | 0.0009 s | 0.0010 s |
  | 2,000 | 0.1246 s | 0.0038 s |
  | 6,000 | 0.3413 s | 0.0101 s |

  The reviewer measured 0.425 s at 6,000 before, on the same day; both
  figures are in the map entry.
- M-4: `contract/store.py` docstring rewritten. The command now takes its
  files from `grep -rl LogStore src/previously/core` (11 modules) and counts
  14 (13 + `actions`), measured in fish 3.7 and bash. Rechecked: 9 modules
  and 13 methods at `c90fb40`, 11 and 13 at `2e71dc3` — "the modules it left
  out call nothing the six do not" holds. The protocol declares 15.
  `module-boundaries.md` follows.

### 3. A `get_event` page could exceed `PAGE_CHARS` (code I-3)

- `_MAX_ATTACHMENTS = 10`, then `+N more`, each name still capped at 200
  (comment at `_FIELD_CHARS` extended to say the prefix is bounded).
- Test `test_a_mail_with_400_attachments_stays_within_the_page_and_shows_text`:
  length ≤ `PAGE_CHARS`, `+390 more`, `page.units == ((1,),)` and the page
  shows `#unit-1` followed by text (1,000 `z`).
- Mutation: cap removed → red (`73510 <= 60000`); 90 other render tests green.
- Decision: no extra guard in `_shown_block` for "marker only". With every
  prefix line capped, the room is always tens of thousands of characters, so
  a guard would be unreachable through the public `render_page` and could
  only be tested through a private name. The test holds the property instead.

### 4. Readiness without a token (code point 8, ruling R-18)

- `auth.guarded(app, resolve=…, ready=…)`: `GET` with path exactly
  `/healthz` is answered before the token check with `ok` (200) or
  `Error: the database does not answer` (503). `build_app` passes `ready`.
- **Departure from the brief, the code wins:** the brief says `SELECT 1`
  through the store's connection. `mcp_server` is typed against
  `LogStore[Conn]` with an opaque `Conn` and has no way to run SQL; a
  `SELECT 1` would need either a new protocol method or SQL outside
  `storage`. `ready` uses `log.tip(conn)` inside `log.snapshot()`: one
  index-backed query for the newest id and hash, nothing of which leaves the
  function. If the maintainer wants a literal `SELECT 1`, it is a
  `LogStore.ping` method.
- The probe is also answered before the SDK's host check, so a kubelet's
  `Host` (the pod address) needs no allowed-hosts entry. Tested and
  documented (cli.md, handoff).
- Tests: 200 `ok` without a token and no `mcp_access`; 503 against a real
  `PostgresStorage` on `127.0.0.1:9` (no mock: a real engine that cannot
  connect); seven other method/path pairs without a token → 401
  (`POST`/`HEAD /healthz`, `/healthz/`, `/healthz/mcp`, `/healthzz`, `/mcp`,
  `/`); `/healthz` with Host `10.1.2.3:8765` → `ok`, control: same Host on
  `/mcp` with a token → 421.
- Mutations: prefix match → 3 red (`/healthz/`, `/healthz/mcp`, `/healthzz`);
  method ignored → 2 red (`POST`, `HEAD`); `ready` ignored → the 503 test red.
  Others green in each run.
- Handoff readiness section rewritten: HTTP `GET /healthz` probe;
  `server/discover` with a token stays as the maintainer's manual check,
  with one of his own clients' tokens, so no reading credential sits in a
  pod secret (this also disposes of docs M-2). Departure from S §8 noted in
  the frozen header.

### 5. Cache hints (code point 7, ruling R-19)

- `MCPServer(..., cache_hints=_CACHE_HINTS)` with
  `{"resources/read": CacheHint(ttl_ms=0, scope="private")}`
  (`mcp.server.CacheHint`, type `mcp.server.caching.CacheableMethod` under
  `TYPE_CHECKING`; no new import-linter edge).
- Test `test_a_read_resource_may_be_kept_only_by_the_client_that_asked`: over
  HTTP in revision 2026-07-28, a response hook keeps the raw body of the
  `resources/read` request and asserts `cacheScope` `private`, `ttlMs` 0.
- Mutation: `scope="public"` → red (`('public', 0) == ('private', 0)`).

### 6. Minors, code

- M-1: named on `mcp-interface.md` (token section) and in the map. No code.
- M-2: `server.py` module docstring and `safety_net` docstring say a call
  that reaches a handler writes one; 401, 421 and transport 400 write none.
- M-3: `render.decode_cursor` removed; `tests/test_render.py` uses
  `decode_position`.
- M-5: `_CHRONICLE` uses `f"{PAGE_CHARS:,}"`, `_GET_EVENT` and `_IDS` use
  `MAX_IDS`. The text is unchanged, so `TOOLS_SHA256` stays the same literal.
  Mutations: `PAGE_CHARS = 50_000` → checksum red (2); `MAX_IDS = 21` →
  checksum red (2).
- M-6 (ruling R-20): `mcp-tools.md` says an erased event was delivered as
  its placeholder and no unit reached the client.
- `record_access` docstring corrected (written before the answer leaves;
  a lost answer stands as delivered; a failed write gives the client an
  error).
- auth.py:13 citation now names the plan (docs M-11).

## Docs

### 7. The named limit the wrong way round (docs I-1, ruling R-21)

`mcp-interface.md` (access-log section and the open-limits bullet, retitled
"A record can name an answer that never arrived"), `trust-boundaries.md`
(heading "A record can name an answer that never arrived"), the map entry,
and the frozen unit spec header (§7 departure) all say: written before the
answer; an answer lost afterward (stdin closed, HTTP dropped, process
stopped) stands as delivered; a failed write gives the SDK's error, never
content. Checked against `Service.answer`'s `finally` and `Service.net`.

### 8. Quotation test (docs I-2)

- `_static_parts(node, constants)` inlines a `FormattedValue` that names a
  module-level string constant (no conversion, no format spec), merging it
  with the neighboring text; `_module_strings` collects the constants of
  `render.py`, `read.py`, `server.py` (resolves `_CURSOR_AGAIN` through
  `CURSOR_REFUSED`). Behavior without constants is unchanged (all 22 tests
  green).
- New `test_the_mcp_reference_quotes_the_reasons_the_decision_builds` builds
  the three `no_rule` reasons and the `rule` reason with `decide` and
  `withholding` on a minimal `Policy` and compares the page's lines exactly.
  The two reason blocks left the fragment loop.
- Mutations (each red, control 5 passed): page rule line reworded; page
  no-rule line reworded (the reviewer's "lacks any rule … uses"); page
  `cursor is NOT VALID ANYWHERE`; page `since is not a date at all`; code
  `who` reworded in `read.py`; code `named` reworded in `read.py`.
- The `cli.md` 503 body and `ok` are held against `auth.NOT_READY`/`READY`
  in `test_the_reference_quotes_what_mcp_and_serve_say`; mutation of the
  page body → red.

### 9. The M4 table (docs I-3)

Row "An embedded resource | Arrives. | Arrives. | Not measured." added
(M4 record: ✔ / ✔ / —). The sentence now says structured content and a
resource link each cost content; two blocks and an embedded resource
arrived; one text block is the form both carry whole.

### 10. Minors, docs

- M-1: the MCP handoff corrects the gate handoff's "nothing inbound /
  nowhere else" for this release; the intro line says so.
- M-2: no readiness token any more (item 4).
- M-3, M-4, M-5 in `mcp-tools.md` (`policy` row, `call.name` for a refused
  resource, "where the result has one").
- M-6: the garbled sentence in `mcp-interface.md`.
- M-7: 60 seconds in the map's chronicle entry and the open-limits bullet.
- M-8: `/mcp refresh` unmeasured in the how-to and the map's Vibe entry;
  `cacheScope` is no longer unchecked (item 5), so no map entry for it.
- M-9: compose tokens via `docker compose run --rm mcp previously client add …`
  and a health check on `/healthz`.
- M-10: heading without sender and recipients, `processor NAME: not
  declared`, a statement reading `erased`.
- M-11: done. M-12: left, as the brief says.

### 11. Pages that follow

`cli.md` (`/healthz`, the 401 sentence's "every other path", host checks,
gaps prose), `mcp-tools.md` (access entry: `uncovered`, `source`, example
JSON, written-before-answer, 421/400; attachments cap; `cacheScope`),
`mcp-interface.md`, `trust-boundaries.md`, `module-boundaries.md`, the how-to,
the handoff, the map, the frozen unit spec header (three departures: R-16,
R-21, R-18). `configuration.md` needed nothing: no new variable.

## Map count

`awk '/^## Offene Punkte/{f=1} /^## Erledigt/{f=0} f && /^- /{n++} END{print n}' docs/superpowers/landkarte.md`:
200 before, 202 after (new: a projection of the policy; the rotation
window). The other changes rewrote or extended existing entries.

## Gates (final tree, after the retype, 2026-10-11)

```
uv run ruff check .                      All checks passed!
uv run ruff format --check .             119 files already formatted
uv run pyright                           0 errors, 0 warnings, 0 informations
uv run lint-imports                      Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                         1537 passed in 206.92s; TOTAL 5650 / 153 missed / 97%
make -C docs html                        build succeeded.
make -C docs vale                        0 errors, 0 warnings and 0 suggestions in 41 files.
make -C docs linkcheck                   build succeeded; output.txt empty
uv run pip-audit --skip-editable         No known vulnerabilities found
```

The tutorial block was retyped from one green `uv run pytest` run (seed
1940192102, 1537 passed in 206.64 s), the `rootdir:` line left out as the
page says. To get a green run to type, the `N passed` figure was set to 1537
first, then the run was made and the whole block typed from it.

No new `noqa`, no `# type: ignore`, no mocks; T201 unchanged (no `print`
added).

## Concerns

1. `SELECT 1` vs `tip` (item 4): the code could not do the literal form
   without a new store method; `tip` is the trivial query used. Maintainer's
   call whether to add `LogStore.ping`.
2. `/healthz` also bypasses the DNS-rebinding host check. Deliberate (a
   kubelet names the pod IP; the probe shows nothing), tested and documented,
   but it goes one step beyond the ruling's wording.
3. `actions` still makes the database visit every action (no index without a
   migration); the cost grows about 34× slower but still linearly. `access`,
   `gaps`, `redaction` and `redact` still read all actions. Both named in the
   map.
4. The first commit (`5102e1d`) alone fails `test_docs_typed_output` until
   the retype commit `fb890d9`; the branch head is green.
5. The ledger `progress.md` was not touched; R-16 to R-21 were already there.
