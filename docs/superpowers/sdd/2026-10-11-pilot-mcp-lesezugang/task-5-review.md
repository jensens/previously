# Task 5 review: the server (3d9b911..5694f77)

Reviewer: Opus. Read-only on the tree. I ran these focused checks:

- `pytest tests/test_mcp_server.py`: 61 passed.
- `pyright`: 0 errors, both on `mcp_server` and on the whole tree.
- `lint-imports`: 9 kept.
- `ruff check .` and `ruff format --check .`: green.
- The T201 count.
- A `--collect-only` run with the tutorial's seed.
- Four probe tests from the scratchpad, run against the real server through the test fixtures:
  - a cursor walk where placeholders fall on page edges;
  - `get_event` cut with two ids;
  - resources and prompts that the SDK refused;
  - HTTP identity, the `Origin` check, and the PRM path without a token.

## Spec compliance

| Requirement | Verdict |
|---|---|
| Every content path goes through `decide` with `Candidate(provider=client.processor, model="", effort=None)` (R-1). This covers the tool `previously`, `get_event`, both templates, `from_unit`, the cursor continuation and legacy. | ✅ `read.py:1269`. `_shown` is reached only after `_decided` has returned `read is None` (`read.py:1397–1402`, `1471–1476`, `1524–1536`). Prompts render no content. One code path serves both generations. |
| Placeholders carry the URI and a reason built from policy names only | ✅ `withholding` (`read.py:1281`) uses names of circles, scopes, client and provider, plus `decide`'s sentence. That sentence, checked in `core/decide.py:162–227`, holds only provider names, regions and days. |
| `reason_code` `no_rule` or `rule`. `Withheld.circles` and `Delivered.circles` hold the circles at call time (R-3). | ✅ |
| `Error:` per id, with the rest untouched (R-8). Attachments and provenance inside the fence. | ✅ Review Focus 5 test, plus probes. |
| `mcp_access` names exactly what is on the page (R-9) | ✅ Probe: `get_event [big, small]` logs `big` with 61 of 81 units, does not log `small`, and names `small` in the footer. The chronicle cut is covered by a test. |
| `mcp_access` on every call: errors, a revoked client, calls the SDK refused (tool, resource, prompt) | ✅ Probe: an unknown resource, a prompt without `circle` and an unknown prompt each write `error` with `era`. |
| No `mcp_access` for a 401 (R-12) | ✅ It is tested, and `cli.md` says so. |
| Rotation and revocation take effect from the next call | ✅ Over HTTP `[200, 401, 200, 401]`. On stdio a revoked client gets `error`. |
| A missing or garbage `Authorization` gives 401 with the concept §7 sentence and `WWW-Authenticate: Bearer` | ✅ |
| A header is never identity | ✅ in code. ⚠️ The test does not measure it (I-3). |
| The token is neither logged nor echoed | ✅ by reading: nothing logs headers, and `uvicorn` runs at `warning`. |
| `allowed_hosts` applies | ✅ A foreign `Host` gets 421 and is let through once listed. Probe: a foreign `Origin` gets 403. |
| Paging has no gap and no duplicate across a cursor, including placeholders | ✅ Probe: 80 mails interleaved shown and withheld, three pages. The first cursor ended on a withheld item. `seen == store order`, no duplicates. A circle that is only placeholders gives 42 items on one page. |
| A cursor with other filters gets `Error:` | ✅ Probe: `Error: cursor is not valid for these filters; call again without a cursor for the first page`. |
| The bound per batch | ✅ `BATCH = 200` per query. Per call it is unbounded, which R-12 names as a limit. |
| Result form: one text block, `structured_content is None`, no `resource_link`, no integer over 2^53, `isError` on errors | ✅ `_text()` holds every tool test to this form. |
| Tool-list checksum: canonical JSON (sorted keys, compact, by name) over name, description and `inputSchema` | ✅ The field descriptions are part of the schema. The descriptions are declarative noun phrases with no customer data. |
| `DEPENDENCIES.md` verdicts with date, version and evidence | ✅ The lock agrees: `mcp` 2.3.0, `mcp-types` 2.3.0, `uvicorn` 0.54.0. |
| New import contract, named edge by edge, with the layer comment updated and no existing contract widened | ✅ |
| SDK middleware typed without casts that hide errors | ✅ The casts follow `isinstance` checks. pyright reports 0. |
| `cli.md`, `configuration.md` and `module-boundaries.md` match the code | ✅ except one sentence (M-1). Counts checked: 24/16/8 edges, 14 outgoing, 9 contracts, the grep blocks, the six `log.` methods. |
| Tutorial block retyped from one run | ✅ consistent with one run. `--collect-only --randomly-seed=1372394948` gives the block's file order and every per-file count, 1509 in total. |
| T201 at 64 | ✅ `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` finds 64. |
| No new suppression (R-11) | ❌ `server.py:714` (I-1) |

## Strengths

- **The check per content has one entry point.** `_decided` is the only way to a `Shown`, so no path can render content without a decision. That includes the chronicle, `get_event`, `from_unit`, both templates and legacy.
- **R-9 is built from the page and not from what was read.** `logged` zips `reads[:consumed]` with `page.units` under `strict=True`, so a drift between the two raises rather than lies.
- **The safety net is a real fix, not a patch.**
  - The `ContextVar` mark stops double entries.
  - SDK refusals of tools, resources and prompts all land in the log.
  - `era` comes from `request_context.protocol_version` there too.
- **Identity comes only from server-side state.** It is `scope["state"]`, set by the wrapper, or `stdio_client`. Nothing reads a header.
- **The cursor is checked before it reaches a query.** That covers a naive moment, ranges and the page number.
- **`recordable` keeps client arguments payload-safe:** no float, int over 2^53 turned into a string, keys restricted to the key pattern, no NUL.
- **The documentation counts were measured, not copied.** I re-measured several of them and found them right: the T201 count, the edges and contracts in `module-boundaries.md`, the six `log.` methods in the `store.py` docstring, and the tutorial block.

## Issues

### Important

**I-1 (R-11, binding for the fix round; not the implementer's fault).** The finding sits at `src/previously/mcp_server/server.py:714` (`def event(id: str, ctx: Context) -> str:  # noqa: A002 …`), `EVENT_TEMPLATE` at `server.py:2153` in the diff, and `CLAUDE.md` (the added sixth-suppression paragraph and "five" changed to "six").

- **What:** a new lint suppression, and an edit to `CLAUDE.md` that records it.
- **Why:** "Remove the cause before you suppress the symptom." The template variable can be renamed instead.
- **Fix:**
  - Rename the template to `previously://event/{event_id}`.
  - Rename the parameter to `event_id` and drop the `noqa`.
  - Revert the `CLAUDE.md` hunk completely, back to "That is five suppressions".
  - Update everything that names the template: the `("resource", EVENT_TEMPLATE, {"id": id})` arguments become `{"event_id": …}`, and so do the tests. `test_every_call_writes_…` expects `"previously://event/{id}"`, and `test_the_resources_are_templates_…` expects the sorted templates.
  - Check whether the tool-list digest changes. It should not, because templates are outside the tool list.

**I-2. The cursor gives the exact `occurred_at` of a withheld (or erased) event to the client.**

- **Where:** `server.py:2514–2516` (`cursor_for` encodes `seen.reads[index].position`) and `render.py` `encode_cursor`. The position of a `WithheldMark` or `ErasedMark` is `(row.occurred_at, row.id)` (`read.py:1388–1401`).
- **Reproducer** (probe, mode `auto`, client `claude-code`):
  - Setup: 40 long mails of `huber`, each followed 30 s later by a short mail of `team`, which has no rule.
  - The first page ends on a placeholder.
  - Decoding its cursor gives `{"after": ["2026-10-06T10:12:30+00:00", 50], …}`.
  - Event 50 is withheld, and its Date header reaches the cloud client to the second.
  - A circle that is all placeholders leaks one exact timestamp per page.
- **Why it matters:** the placeholder is meant to carry the URI and the reason and nothing else. Global constraint: "Kein Inhalt eines Events … in einem Platzhalter". The cursor is "opaque" only by convention. Base64 JSON is one decode away, and the brief asks for exactly this kind of leak check.
- **The cursor format is plan decision 6, so this needs a ruling.** Either:
  - **(a) Fix it.** Encode only the event id (plus filters and page), and resolve `occurred_at` on the server when decoding. Read the row with `log.read(conn, id, 1)`, and refuse unless the id is an observation. A forged id then teaches only an order the client can already page through.
  - **(b) Name it** as a limit in the explanation page and in the map.

  (a) is about 15 lines in `render.py` and `server.py`. The test would decode a cursor that ends on a placeholder and assert that it holds no time.

**I-3. The test for "a header is no identity" cannot fail for the mutation it is meant to catch.**

- **Where:** `tests/test_mcp_server.py`, `test_a_header_naming_a_client_is_no_identity`. It sends no `Authorization` header and asserts 401.
- **Why it misses:** take a mutation in which `Service.client_name` prefers an `X-Previously-Client` header once the token check has passed. The test stays green, because the 401 comes from the token check. CLAUDE.md: "Mutate the assurance and measure that the test goes red."
- **The code is right.** Probe: the `local-harness` token plus `X-Previously-Client: claude-code` and `Mcp-Client: claude-code` gives `whoami` answering `client local-harness`.
- **Fix:**
  - Send the `local-harness` token together with headers that name `claude-code`.
  - Assert that `whoami` says `local-harness`, and that `access.client == "local-harness"`.
  - Measure the mutation above red.
  - Keep the tokenless 401 case as a second assertion.

### Minor

**M-1. `docs/reference/cli.md` (serve section) is wrong for a request without a token.**

- **What it says:** "so `/.well-known/oauth-protected-resource` answers 404".
- **Measured:** only a request with a valid token gets 404. Without one the answer is 401, because the wrapper guards every path.
- **Fix:** add "to a request with a valid token; without one, 401 like every other path".

**M-2. `starlette`, `mcp_types` (the package `mcp-types`) and `anyio` are imported directly by `src/` but not declared.**

- **Where:** `auth.py:27` imports `anyio`, and `server.py:78–79,2087,2119` import `anyio`, `mcp_types` and `starlette`.
- **Why it is inconsistent:** the `uvicorn` row in `DEPENDENCIES.md` justifies declaring it with "declared because that module imports it, although `mcp` brings it too", and plan decision 2 says "direkt importiert, also deklariert".
- **Precedent the other way:** `botocore` is imported by `storage/s3.py` and is not declared.
- **Fix:** either declare the three with verdicts, or reword the `uvicorn` reason so that it does not set a rule the same commit breaks. It is a choice for the controller.

**M-3. The ruling citations of this plan are inconsistent and do not resolve yet.**

- `tests/test_mcp_server.py` (the comments "ruling R-9: pages" and "ruling R-9: the access names …") cite the label without a plan.
- `render.py:81,288` say "2026-10-11 pilot plan", while `render.py:119,164,439` and `read.py:110` say "2026-10-11 MCP read access plan".
- The ledger is still in the git-ignored `.superpowers/sdd/`. Until it moves to `docs/superpowers/sdd/2026-10-11-pilot-mcp-lesezugang/`, no `R-` label resolves.
- **Fix:** one plan name everywhere and a date on every citation. Moving the ledger belongs to Task 6.

**M-4. `conn: Any` in the resource and prompt bodies loses the store's connection type.**

- **Where:** `server.py:2763` (`def body(conn: Any, …)`) and `2790` / `2820` (`_conn: Any`).
- **Fix:** they sit inside the generic `_resources[Conn]` and `_prompts[Conn]`, so annotate with `Conn` instead.

**M-5. A test name says the opposite of what the test passes.**

- **Where:** `tests/test_render.py`, `test_without_more_and_without_items_no_cursor_follows`. The test passes `more=True`.
- **Fix:** rename it, for example to `test_more_without_items_gives_no_cursor`.

**M-6. Two assurances are tested only by proxy.**

- `test_no_token_stands_in_the_log` makes no server call before it searches. It re-proves Task 2's `add_client`.
  - Run the HTTP calls first: success, 401, rotation and revocation.
  - Assert the tokens are absent from the action payloads and from `caplog`.
- The refusal of a cursor with other filters is tested only at `decode_position`. My probe shows it works through the tool, and one tool-level assertion would pin it.

**Named, not chased** (operator failure or edge cases, per the 2026-10-05 working rule):

- If `record_access` itself fails after a successful read, the client gets the SDK's `Error executing tool previously`. That does not start with `Error: `. It fails closed: nothing is delivered.
- An out-of-range id (`ErrorMark` with `event=None`) that does not fit the page is left out of the footer's `ids=[…]`.
- `withholding` can say "the built-in rule local_only do not allow" (subject–verb agreement) for a local provider that fails under `local_only`.

## Assessment

**Needs fixes.**

- **I-1** (R-11) is binding.
- **I-2** needs a ruling from the controller: either fix it with the cursor holding only the id, or name it as a limit.
- **I-3** is a test that cannot fail for its assurance.

The minors fit into the same round. Otherwise the server holds up adversarially:

- no path shows content without `decide`;
- identity cannot be taken over by a header;
- the access log names what is on the page, refusals included;
- paging has no gap and no duplicate, even with placeholders on the page edge.
