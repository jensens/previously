# Final code review: pilot unit 4, MCP read access (c90fb40..2e71dc3)

Reviewer: whole-branch code package, read-only.
Date: 2026-10-11.
Scope: `src`, `tests`, `pyproject.toml`, `.importlinter`, `DEPENDENCIES.md`, checked against K, S §10, the plan, `context.md` and rulings R-1 to R-15.
This review looks at the seams between tasks. It does not repeat findings the task reviews already resolved.

## Gates run

Run from the worktree, with the project configuration, on 2026-10-11:

| Gate | Result |
|---|---|
| `uv run ruff check .` | All checks passed (exit 0) |
| `uv run ruff format --check .` | 119 files already formatted (exit 0) |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations (exit 0) |
| `uv run lint-imports` | 9 kept, 0 broken; `only-mcp-server-knows-mcp` with 4 ignored imports (exit 0) |
| `uv run pytest --cov --cov-report=term-missing` | 1522 passed in 210 s, TOTAL 97 % (5608 statements, 151 missed) (exit 0) |

The sixth gate, the docs, belongs to the other package and was not run here.

Probes run besides the gates, all against a fresh testcontainer and with scripts in the session scratchpad. Nothing was written to the worktree.
- `probe.py`: 48 real `mcp_access` rows. Two clients in both generations made 12 calls each: tools, resources, prompts, SDK refusals, a junk cursor and mixed ids. The script then ran `access_problem`, `parse_access`, `verify`, `read_access --circle` and `gaps` over the rows, and made HTTP calls on the wire.
- `scan.py`: how long `read_policy` takes as `mcp_access` rows grow.
- `attach.py`: `render_page` with many attachment names.

## Strengths

- **No path to content skips `decide`.** Every item the server shows comes from `read._decided`. That covers the chronicle, `get_event`, both resources, the `from_unit` continuation and the cursor continuation. `_decided` calls `decide` with `Candidate(client.processor, "", None)` (R-1), and `decide` reads the provider's `operator`, `training`, `subprocessors` and `model_origin` through `_merge_chain`/`_chain_rejection` (`core/decide.py`). So Task 1's chain reaches Task 5's check through the one shared function, not through a copy.
  - The `from_unit` "no unit N" error is only reachable after `decide` passed (`read.py:411-422`), so it says nothing about a withheld event.
  - `resume_point` uses a withheld event's time only to position the cursor; it never shows it (R-13).
  - Prompts, `whoami`, `list_circles` and the error texts carry only policy names and the client's own input.
- **The log's form holds across Tasks 3 and 5.** All 48 real rows pass `access_problem` and parse with `parse_access`, and `verify` returns `[]`. A sample row:
  ```json
  {"era":"2026-07-28","call":{"kind":"tool","name":"get_event","arguments":{"ids":[17,18,19,20,21,22,23,1,"1152921504606846976",999999]}},"action":"mcp_access","client":"claude-code","policy":{"rules":[12,13,14],"client":15,"processor":1},"outcome":"ok","withheld":[{"event":17,"reason":"circle team has no rule, …","circles":["huber","office","team"],"reason_code":"no_rule"}, …],"delivered":[{"event":18,"units":[1,2,3,4],"circles":["huber"]}, …,{"event":23,"units":[],"circles":[]}]}
  ```
  - `recordable` keeps the arguments inside the payload rules: strings above 2^53, no NUL, keys checked against `KEY_PATTERN`.
  - `read_access(circle="team")` finds a `get_event` by the circles of the event (R-3), and finds `local-harness`'s delivery of the `plain` mail.
- **R-9 is enforced, not hoped for.** `logged` zips `reads[:consumed]` with `page.units` under `strict=True`.
- **The protocol era cannot be forged into the log.** A tools/call whose `MCP-Protocol-Version` header I changed to `2099-01-01`, or to 3,000 characters, gets HTTP 400 from the SDK and writes nothing.
- **The safety net's context variable works across the worker thread.** The SDK runs sync tools, templates and prompts through `anyio.to_thread.run_sync`, which copies the context. The tests' exact row counts prove it: a missed mark would add a second row.
- **Numbers in comments, rechecked:**
  - T201 is 64, measured with the command `pyproject.toml` gives, and the breakdown 51 + 10 + 2 + 1 matches the added `print` calls.
  - The import-time figures in `_cmd_mcp` match: 0.34–0.38 s for `cli` alone, plus 0.31–0.34 s.
  - Variation selectors: 16 + 240 = 256.
  - `TOKEN_BYTES` 32 gives 43 characters.
  - Batch 200 × allowance 300 = 60,000, so one batch fills a page, as `read.py` says.
  - The six `log.` methods in `mcp_server` and the 13-method count of `store.py` both hold.
- **Simplicity:**
  - No migration and no new table.
  - One process; one token per client, stored as a SHA-256.
  - No `# type: ignore` and no new `noqa`.
  - Tests mock nothing except environment variables, and no test reaches a private name.

## Issues

### Important

**I-1. `policy gaps` reports circles that have a rule as MCP gaps.**
`src/previously/core/gaps.py:126` together with `src/previously/mcp_server/read.py:275`.

- **What.** Task 5 fills `Withheld.circles` with `decision.circles`: every circle of the event, as R-3 wants it for `previously access --circle`. Task 3's `_mcp_gaps` counts every circle in that field as a missing rule. Task 3's own fixture (`tests/test_access.py:83`) modeled the field as "the circle without a rule".
- **Reproducer.** In the test world of `test_mcp_server.py`, after the probe's calls, `gaps()` returns:
  ```
  [('circle:huber','mcp',10), ('circle:office','mcp',10), ('circle:team','mcp',18)]
  ```
  `huber` and `office` both have a rule (`regions any`). The `plain` mail is withheld only because `team` has none. Both the CLI (`mcp:circle:huber`) and the tool `policy_gaps` print these lines. `test_policy_gaps_counts_what_this_server_withheld_for_lack_of_a_rule` asserts only that the `team` line exists, so it stays green.
- **Second, smaller seam in the same function.** A `no_rule` withholding of an event with no circle stands as `event:<id>`, once per event. The gate resolves it to `source:<source>` (`gaps.py:92-97`). Mail of no circle with no source rule therefore gives one line per mail, where the gate gives one line per source.
- **Why it matters.** `policy gaps` exists to tell the operator which rule is missing (K §5, S §7). Here it names rules that exist.
- **Fix.**
  - Record the circles without a rule on the entry, for example a field `uncovered` filled from `decision.fallback.circles`. Add it to `_WITHHELD_KEYS`, `_payload` and `parse_access`, and let `_mcp_gaps` count it.
  - Leave `circles` as it is, because `access --circle` needs it.
  - Resolve "no circle" to `source:` as the gate does, through `log.source_keys`.
  - No rows exist in production yet, so changing the form costs nothing.
- **Test.** Extend the `policy_gaps` test so that no `circle:huber` or `circle:office` line appears. Measure it red with the current `item.circles`.

**I-2. Every HTTP request reads every action event twice, and every call adds one.**
`src/previously/mcp_server/server.py:830-833` (token resolution) and `server.py:363-364` (`answer`), both through `read_policy`, `src/previously/core/policy.py:571`.

- **What.** `read_policy` streams every event of kind `action` with its payload and keeps the policy ones. `mcp_access` is an action, so the log the token check reads grows with each call it answers.
- **Measured** (`scan.py`, best of 3, payload of 20 delivered and 10 withheld entries):

  | `mcp_access` rows | one `read_policy` |
  |---|---|
  | 0 | 0.0011 s |
  | 2,000 | 0.106 s |
  | 6,000 | 0.425 s |

- **Cost per call.** A tool call over HTTP runs the read twice, and a legacy round trip runs it again for `initialize`. The map's own estimate, "einige tausend im Monat", puts a call above one second of policy reading within about two months, and the total cost grows quadratically. The gate's `read_policy` slows the same way, because it scans the MCP rows too.
- **Not named.** The map names the volume of `mcp_access` ("beobachten und eine Schwelle nennen"). It does not say that the token check and the policy read of every call scan it.
- **Fix (a design decision for the maintainer).** A store method that returns only the policy actions, filtered in SQL. This bends the "storage does not interpret a payload" line in `read_by_kind`, but it needs no migration.
- **Before merge, at least:** name the effect in the map beside the volume point, with these figures, so that the pilot run (condition 9) watches for it.

**I-3. A `get_event` page exceeds `PAGE_CHARS` for a mail with many attachments.**
`src/previously/mcp_server/render.py:313-315`.

- **What.** Recipients are capped at 10 and each name at 200 characters, but the list of attachment names has no cap.
- **Measured** (`attach.py`, 150-character names):

  | Attachment names | Page length |
  |---|---|
  | 10 | 2,203 |
  | 400 | 73,469 |
  | 1,000 | 183,269 |

- **The log overclaims too.** `_shown_block` computes a negative `room` and emits only the marker `#unit-1`, while `page.units == ((1,),)` logs unit 1 as delivered.
- **Why it matters.**
  - This breaks assurance 8 (S §10).
  - The attachment line repeats on every `from_unit` call, so a client with an output cap (Claude Code, 25,000 tokens) can never read such a mail.
  - The chronicle is not affected, because it renders without attachments (`full=False`).
  - The trigger is rare, but it is a real input, not a misuse case.
- **Fix.** Cap the names the way recipients are capped (`_MAX_ATTACHMENTS`, then `+N more`), so that the comment at `_FIELD_CHARS` holds for the whole prefix.
- **Test.** A render test with 400 attachments that asserts `len(text) <= PAGE_CHARS` and that every logged unit has text on the page.

### Minor

**M-1. A rotation between the token check and the call serves the old token once, under the new record.**
`src/previously/mcp_server/auth.py:86-90`, `server.py:357-365`.

- **What.** The wrapper resolves token → name in one transaction. `answer` looks the client up **by name** in a later snapshot.
- **Effect.**
  - If `client add` for the same name commits in between, the request that carried the old token is served under the new record, which can name another processor.
  - The same holds for revoke followed by re-add.
  - The race the implementer named covers only revocation, which gives an `error` row.
- **Window.** One request.
- **Fix.** Put the token's hash into `scope["state"]` and check `client.token_sha256` against it inside `answer`'s snapshot. Otherwise name the race on the explanation page.

**M-2. Refusals at the transport, with a valid token, write no `mcp_access`.**

- **What.** The host check (421) and the protocol-version mismatch (400, measured above) both refuse before the middleware runs.
- **Assessment.** This is consistent with R-12's reading of the 401. But the docstrings "every call writes one" (`server.py:6-8`, `418`) claim slightly more than happens.
- **Fix.** Name it; do not fix it.

**M-3. `decode_cursor` is dead in `src`.**
`render.py:564-567`. Only `tests/test_render.py` uses it, since `server.py` moved to `decode_position`. Remove it and let the tests use `decode_position`.

**M-4. A figure in a touched comment is stale.**
`src/previously/contract/store.py`, module docstring.

- The branch edited this docstring but left "the six modules that name `LogStore` today, found with `grep -rl LogStore src/previously/core`". That grep finds 11 modules now; it found 9 at `c90fb40`, so the figure was already stale.
- The 13-method count still holds (measured 13).
- CLAUDE.md, *A comment is a claim*: a comment somebody touches gets its figures rechecked.

**M-5. The tool descriptions hard-code their limits.**
`server.py:125` and `server.py:130`/`157` hard-code "60,000" and "1 to 20" beside `PAGE_CHARS` and `MAX_IDS`.

- Built with an f-string, a change of the constant would change the description, and the checksum test would make that change deliberate.
- As written, the constant can move and leave the description stale.

**M-6. An erased event is logged under `delivered`.**
`read.py:266` logs it with empty `units` and `circles`.

- It is harmless, because the placeholder holds nothing.
- But in `previously access` it reads as "delivered", the same as an event whose every unit was erased.
- A note on the reference page is enough.

## Recommendations

### Point 7: `cacheScope: private` (K §4.4)

- **The server does not set it, the SDK does.** `mcp_types.CacheableResult` defaults to `ttl_ms=0` and `cache_scope="private"`.
- **Measured on the wire** through `build_app` on 2026-10-11:
  - Revision 2026-07-28: `resources/read` answers `{"result":{"cacheScope":"private",…,"ttlMs":0}}`.
  - Revision 2025-11-25: the answer carries no field. The SDK's own client treats a legacy answer as private (`mcp/client/caching.py:348`).
- **So its absence does not matter today.** The risk is a default that changes silently in a 2.x minor release. The MCP middleware is already provisional there.
- **Recommendation, two lines and a test:**
  - Pass `cache_hints={"resources/read": CacheHint(ttl_ms=0, scope="private")}` to `MCPServer` explicitly. `MCPServer.__init__` accepts it (`mcp/server/mcpserver/server.py:183`).
  - Add an HTTP test in the modern era that asserts `"cacheScope":"private"` on `resources/read`, measured red with `scope="public"`.

### Point 8: readiness without a token

**Recommendation: add a token-free readiness route, and keep `server/discover` with a token only as a manual end-to-end check.**

The route:
- `GET /healthz` (or `/ready`), answered by the wrapper in `auth.py` before the token check.
- Exact path, `GET` only, a constant body such as `ok`.
- A trivial query through `log.snapshot()`, so that it says "process and database answer".
- No MCP, no policy names, no access row.

Reasons, weighed against K §7 and S §8:

1. **The readiness client is a reading principal.** Its token can call `previously` and `get_event`. What it sees depends on its processor, and no declaration guarantees it sees nothing: a non-local provider passes every rule whose regions and properties it meets. Keeping a credential that reads content in a pod secret, just to learn "up or down", widens the blast radius for nothing.
2. **K §7 makes the token mandatory so that the access log knows the principal.** A health route makes no call, returns no data and writes no log entry, so that reason does not reach it. The token's doctrine stays whole for MCP itself.
3. **S §8 chose `server/discover` assuming it could serve as a probe.** The Task 6 measurement showed that it needs a token and two `MCP-…` headers. It also answers 200 with a JSON-RPC error when those headers are missing, which a status-only probe cannot tell from success.
4. **It costs less to operate.** An HTTP `GET` probe replaces an exec probe that starts Python every period. The token-checked probe would also pay I-2's growing `read_policy` scan, twice, every period.
5. **It is simpler.** One route and one test, against a client, a secret and a rotation procedure. That is the simplicity check of S §8.

The test should show:
- `GET /healthz` without a token gives 200 and the constant body.
- Another method on that path, and every other path, still give 401 without a token.
- The route writes no `mcp_access`.

The handoff's readiness section changes with it.

Nothing here blocks the merge: the handoff, as written, works.

## Assessment

**Ready after fixes.**

- **I-1** gives the operator wrong advice from the one list that exists to show missing rules.
- **I-3** breaks assurance 8 and can make a mail permanently unreadable.
- Both are small, local fixes, each with a test that can be measured red.
- **I-2** needs, before the merge, at least a named entry with the measured slope. The structural fix is the maintainer's decision.
- **Minors M-1 to M-6:** name or fix them in the same wave, at the maintainer's choice.

No leak was found. Every content path passes `decide` with the client's chain, and every `mcp_access` row the server writes passes the form check and `verify`.
