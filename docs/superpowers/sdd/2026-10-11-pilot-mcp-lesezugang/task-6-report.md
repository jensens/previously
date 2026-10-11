# Task 6 report: docs, handoff, map, freeze

Status: DONE_WITH_CONCERNS (concerns at the end; none blocks).
Base 964584f. Commits:

| Commit | What |
|---|---|
| `8b49768` | pages (three new, five changed), index pages, README, and the test that holds the new reference page |
| `7aaadd7` | handoff `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md` |
| `d86fbfe` | map, and both specs frozen |
| `7896b56` | code comments repointed; the test_policy.py docstring |
| `2e71dc3` | tutorial pytest block retyped from one run |

## Pages and what each carries

- **`docs/explanation/mcp-interface.md`** (new, label `mcp-interface`; title "About the client interface" — vale's Microsoft.HeadingAcronyms warns on "MCP" in a heading, so no heading carries it; the first sentence spells MCP out). Sections with labels for the code:
  - `mcp-client-processor` — a client is a processor (decision 2026-10-10), `decide` with the client's chain as only candidate, the "without a rule only local" default for clients and its three visible places, the chain beyond a name (four properties, unknown fails, also for a local provider), what is no customer content (circle names, rules, member counts, promises; no addresses).
  - `mcp-text-block` — the M4 table in English (all eight rows measured, "Not measured" where the measurements file has a dash), and the conclusions (one block, no structured content, no resource link, no number above 2^53, `Error:` first, `isError` set and never relied on, URIs).
  - `mcp-fence` — fence as a bet; real boundary: read-only tools, `write_` naming plus two-step confirmation later, the policy; the two named gaps (forgeable `#unit-<n>`, display names outside the fence, ~2,200 characters); invisible characters removed on output only, why (hash chain), the 256-value variation-selector channel, emoji and Hangul cost (ruling R-6).
  - `mcp-access-log` — why in the log, no content so no cascade, circles per delivered event (R-3), what reached the page and not what was read (R-9), 401 without entry, stdio revocation logged as `error`, SDK refusals logged by a hook.
  - `mcp-generations` — the two generations measured, the 2026-10-10 decision, nothing branches, Vibe as test not brake.
  - `mcp-tool-list` — stable list, checksum test, declarative descriptions.
  - `mcp-token` — token not network, own wrapper instead of the SDK verifier (no PRM), stdio has no token.
  - `mcp-open-limits` — the named limits: unit over a page (R-5), PAGE_CHARS estimate, chronicle reads the log without a per-call bound, order of placeholders (R-13), record without delivery and delivery without record (R-12, S §7), provisional SDK hook, volume.
- **`docs/reference/mcp-tools.md`** (new, label `mcp-tools`, title "Server tools, resources and prompts", label `mcp-access-payload` on the access entry section): server name, version and the instructions quoted whole; form of a result (header, event heading, fence, inside-fence lines of `get_event`, placeholders, cut notes, footers, `No results.`); an example chronicle page; the sanitizer list; each tool with an argument table and output; errors of a call; item errors; withheld reasons; resource templates (`{event_id}`, R-11); prompts with their real text; the `mcp_access` payload key by key with a JSON example.
- **`docs/how-to/connect-claude-code-and-vibe.md`** (new): declare a provider per client, a rule per circle, `client add`, `serve`, Claude Code over HTTP and over stdio (marked untested), Vibe with `headers`, the harness cache, check with `whoami` and `previously access`, rotate/revoke, and the dated list of tested configurations.
- **`trust-boundaries.md`**: a table row for the MCP server; a section "Clients that read the log" (four properties, what every client sees); the "nobody guards" list dated 2026-10-11 with three MCP entries (provider retention of a client, names outside the fence, call without record / record without delivery); writing outward alone stays ahead.
- **`processing-policy.md`**: intro names the chain; merge sentence extended by the four restrictions; a new subsection "A promise describes a chain, not a name" (four properties, unknown fails, local is no answer to training); pointer to `mcp-interface`.
- **`design-records.md`**: eleven records, the last two frozen 2026-10-11; a paragraph on the two MCP records (architecture §8 and §8.7 superseded, what is kept and what changed, which pages took what, the fourth handoff); the table gains twelve rows for every paragraph the build cited, each marked whether code still cites it; "the last five rows" reworded since the table no longer ends with them.
- **Index pages** (explanation, reference, how-to, `docs/index.md`) and **README** (state line, a bullet for MCP read access, eighteen commands, "no MCP tool that writes", "no network interface but the MCP server", and the specification table: eleven records — the gate's record was missing from it since 2026-10-09, added together with the two new ones).
- Not changed because Task 5 had them right: `cli.md`, `configuration.md`, `module-boundaries.md`, `policy-and-model-calls.md`.

## Each carry item

Named limits (explanation page; map where marked):

1. Fence a bet, forgeable `#unit-<n>` — `mcp-fence`. Verified: units are rendered as `#unit-{seq}` inside the fence (render.py `_shown_block`).
2. Display names outside the fence, 200 chars, 10 recipients, `+N more`, ~2.2k — `mcp-fence` and trust-boundaries. Verified against `_FIELD_CHARS`, `_MAX_RECIPIENTS`, `_heading`.
3. Unit over a page, rest not served (R-5) — `mcp-open-limits`; map entry with `from_char`.
4. Order of placeholders (R-13) — `mcp-open-limits`. Verified: `encode_cursor` carries `after`, `filters`, `page`, no time.
5. stdio written-never-sent (R-12), and the S §7 opposite — `mcp-open-limits`, trust-boundaries, and one map entry.
6. No read bound per call, batches of 200 — `mcp-open-limits`; map. Verified `BATCH = 200` and the loop in `chronicle`.
7. `PAGE_CHARS` not measured — `mcp-open-limits`; map, due with condition 9.
8. 401 without token writes no entry; known client not in force → `error`. **The code qualifies the second half:** over HTTP a revoked client's token no longer resolves in `guarded`, so it gets the 401 and no entry; the `error` entry happens on stdio (client fixed at start) or in the race between wrapper and handler. Written that way.
9. SDK middleware provisional — `mcp-open-limits`; map. Verified in `mcp` 2.3.0 `server/mcpserver/server.py` at the `middleware` property: "Provisional - the signature may change in a 2.x minor release".
10. Sanitizer list — reference "Sanitizing", reasons in `mcp-fence`. Checked against render.py. **Correction:** besides U+2028/9, the line feed and tab are flattened too; the carriage return is in `_LINE_BREAKS` but `sanitize` removes it first (category Cc), so it is removed, not flattened (measured: `sanitize('a\rb c') == ('ab c', 1)`). The 8-bit DCS/SOS/PM/APC forms (U+0090, U+0098, U+009E, U+009F) go with their sequence as well, listed. DEL is in `Cc` and goes.

How-to:

- Local provider needs `--training no --subprocessors none`: **the carry overstates it** ("or the new restrictions withhold everything from it"). Without a rule, `local_only` lets a local provider through regardless; only a rule that sets `--no-training` or `--no-subprocessors` withholds from a local provider that left them unknown. The how-to and the explanation say it that way.
- Vibe `headers`, not `api_key_env` — written, with the M3 detail that Vibe reported nothing.
- Vibe harness caches the tool list — written. The measurement file's third run shows `--legacy-harness` did call the two new tools, so the how-to says that was measured.
- Dated list: Claude Code 2.1.289 (`2026-07-28`), Vibe 2.26.1 (`2025-11-25`), measured 2026-10-10, against a throwaway server on `mcp` 2.3.0, **not against `previously serve`**. The measurement records only the `headers` key of the Vibe entry; `name`, `transport`, `url` follow Vibe's documentation (linked; linkcheck reached it). The stdio form for Claude Code is marked as not tested.

Reference:

- `previously://event/{event_id}` (R-11) — verified `EVENT_TEMPLATE`.
- Cursor: id + filters (+ page), base64url without padding, not sealed — verified `encode_cursor`/`decode_position`.
- PRM 401/404 — already in `cli.md` (Task 5, tested); the reference points at `cli-serve` instead of repeating it.
- `mcp_access` payload field by field as `core/access.py` checks it, `era` required with null, `circles` on every delivered entry; the JSON example is held by `access_problem` in a test.
- Every quotation real: see the test below.

Code comments:

- Repointed, see below. Ruling citations untouched.
- Deferred docstring: **it is in `tests/test_policy.py`, not `tests/test_clients.py`** (`test_a_client_event_with_a_damaged_hash_is_skipped_and_a_lookup_returns_none`). Rewritten to say the read skips the damaged hash, so no lookup compares against it.

Map: see the counts. All listed items are there: projects with counter-thesis under *Feststellungen und Entitäten* (unit 5), "Vibe on `mcp` 2.x", the `mcp_access` volume, items 3, 6, 7, 9, and K §10 points 4–8 and S §13 points 1–2; condition 9; the S §7/R-12 pair; the three "named, not chased" items of the Task 5 review as one Kleinkram entry. K §10 point 7 (Tasks) cross-references the existing "MRTR and Tasks" entry, which now also records what Claude Code reported on 2026-10-10 (`roots`, `elicitation`, no tasks).

Handoff: release `v0.1.0a3`, no migration (no migration in the branch: `git diff c90fb40..HEAD --name-only` lists none), deployment `previously-mcp` running `previously serve`, one replica, Service, the variables (`PREVIOUSLY_MCP_HOST=0.0.0.0` in the pod), no blob/API/IMAP secrets, readiness via `server/discover`, stages A and A2 (`PREVIOUSLY_MCP_ALLOWED_HOSTS`, 421/403), B not asked, tokens created by the maintainer in the tools pod, none in the file; delivered together with the gate's handoff and its model server; docker-compose paragraph; a checklist.

**Readiness was measured, and the measurement changed what the handoff says.** Every request needs a token, `server/discover` included, so the probe needs a client of its own. Measured on 2026-10-11 against `build_server(...).streamable_http_app(...)` behind `guarded` with a stub resolver (no database): `server/discover` answers with a `result` only with the headers `MCP-Protocol-Version: 2026-07-28` and `Mcp-Method: server/discover` and the `_meta` envelope keys `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities`; without the two headers it answers HTTP 200 with a JSON-RPC `Method not found`, with only one of them 400. The handoff gives the exact request and says to check the body, not the status. `server/discover` writes no `mcp_access` (only `tools/call`, `resources/read`, `prompts/get` are in `_KINDS`).

## Map counts

Command from CLAUDE.md: **185 before, 200 after** (14 entries in the new section *MCP-Lesezugang (Pilot, Einheit 4)*, 1 for the projects under *Feststellungen und Entitäten*). Unit 4 stands as "gebaut, nicht abgenommen"; unit 3 moved into the accepted table (its row sat under "built, not accepted" with PR #9 as acceptance); the legend gains MK, ML, P-ML; *Was als Nächstes kommt* names the merge, `v0.1.0a3`, condition 9, the two handoffs together, then unit 5.

## Frozen headers

Both specs carry the frozen-record block of the stage 1b and gate records, dated 2026-10-11, and a status line "eingefroren am 2026-10-11 …":

- Unit spec: departures listed — no `TokenVerifier` (§9; decision 1, R-10); `{event_id}` (§6; R-11); cursor without time (§5.1; R-13); unit over a page not served (§5.1; R-5); `PAGE_CHARS` not measured in the build (§5.1; condition 9); the wording for a non-observation (§5.2); "auch ein abgewiesener" means a known client no longer in force (§7; R-12); `circles` on delivered entries and only what reached the page (R-3, R-9). §1 notes the freeze happened; §13 opens with the past-tense paragraph pointing to the map.
- Concept: superseding architecture §8 noted; departures — no `TokenVerifier` (§7); the §6 example (no total pages, subject as unit 1 inside the fence, `#unit-<n>`, eight hex characters); the §3.3 reason wording; `circles`/`reason_code`/`era` in §5. §10 opens with the past-tense paragraph.

## Repointed comments

| Where | Before | After |
|---|---|---|
| `mcp_server/auth.py` docstring | concept section 7; decision 1 over S section 9 by R-10 | `{ref}mcp-token` for the reason; "§9 (frozen design record)" with decision 1 and R-10 as provenance |
| `mcp_server/read.py` docstring | concept section 3.3 | `{ref}mcp-client-processor` |
| `mcp_server/read.py` `BATCH` | S §13 point 1 | `{ref}mcp-open-limits` |
| `mcp_server/render.py` `PAGE_CHARS` | S 5.1, S §13 point 2, plan decision 4 | `{ref}mcp-open-limits`; "§5.1 … (frozen design record)" for where it was set |
| `mcp_server/render.py` `_MAX_SAFE` | concept section 6, M4 | measured 2026-10-10, `{ref}mcp-text-block` |
| `mcp_server/render.py` `Shown` | spec section 5.2 | `{ref}mcp-tools` |
| `mcp_server/server.py` module docstring | S section 7, M4, M1, concept section 8 | `{ref}mcp-access-log`, `{ref}mcp-text-block`, measured 2026-10-09 + `{ref}mcp-generations`, `{ref}mcp-tool-list` |
| `mcp_server/server.py` `safety_net`, `_tools`, `_resources`, `_prompts` | S sections 7, 5, 6, 6 | `{ref}mcp-access-log`, `{ref}mcp-tools` ×3 |
| `tests/test_mcp_server.py` docstring | S section 10 | `{ref}mcp-generations`; plus one line saying the "assurance N" section comments number as "§10 of the unit specification (frozen design record)" and that a review focus is the plan's |
| `tests/test_mcp_server.py` `_text` | S section 10 point 5 | `{ref}mcp-text-block` |
| `tests/test_access.py` sketch test | "the sketch" | "§5 of the concept specification (frozen design record)" |
| `tests/test_render.py` concept-example test | none | docstring "§6 of the concept specification (frozen design record)" |

`grep -rn "§" src tests | grep -v "frozen design record"` prints nothing; every new `{ref}` label resolves (`test_every_doc_reference_in_the_code_resolves` green).

## The test for the reference page

`tests/test_docs_references.py` gained five tests. `test_docs_references` finds quotations by the sentence that introduces each block, so the new page is covered by tests of its own:

- the instructions block equals `INSTRUCTIONS`;
- the example page is rendered again by `render_page` from the items it describes, with the tag the page shows, and must be equal character for character;
- every quoted error, item error, withheld reason, cut note, footer (and its hint) and both prompt texts match the static parts of a string literal of `server.py`, `read.py` or `render.py`, as the `cli.md` sentences are matched;
- the tool headings and their argument tables match the `server.tool(name=…)` functions' parameters, the template table matches `CHRONICLE_TEMPLATE`/`EVENT_TEMPLATE`, the prompt table the `server.prompt` names;
- the JSON example passes `access_problem`, and the two key tables equal its keys and its call's keys.

Measured red under eleven mutations (an error wording, the instructions, the footer, a withheld reason, an item error, a cut note, a prompt text, a renamed tool argument, a renamed key in the example, a renamed key in the table, a renamed tool heading); green with a control change to the `get_event` description, which the page doesn't quote.

## Gates

All on the final tree (`2e71dc3`):

```
uv run ruff check .                          All checks passed!
uv run ruff format --check .                 119 files already formatted
uv run pyright                               0 errors, 0 warnings, 0 informations
uv run lint-imports                          Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing   1522 passed in 210.58s; TOTAL 97%
make -C docs html                            build succeeded
make -C docs vale                            0 errors, 0 warnings and 0 suggestions in 41 files
make -C docs linkcheck                       build succeeded; output.txt empty (the new Vibe link "working")
uv run pip-audit --skip-editable             No known vulnerabilities found
```

Tutorial: the count went from 1517 to 1522 (five new tests). The numbers were set to 1522 first so that `test_docs_typed_output` would pass in the run, then the whole block was retyped from one run of `uv run pytest` (seed 1063858237, 213.63 s), `rootdir:` left out as the page says. No vocabulary or `.vale.ini` change was needed; the vale findings were reworded instead.

## Concerns

1. **The quotation test matches static parts**, like the existing `cli.md` checks: a message that opens with an interpolation (`_CURSOR_AGAIN`, the withheld sentences) is held only from its first literal part on, and the direction is page to code only. A message the page doesn't quote is not looked for.
2. **Unmeasured statements in the how-to**, all marked there: the Claude Code stdio form (`claude mcp add --transport stdio --env … -- previously mcp`) and the Vibe keys other than `headers`. The provider values in the how-to's examples (`claude-max --training no`, `vibe-free --training unknown`) are examples, and the page says to write what the account says.
3. **The readiness request** was measured with a stand-in for the token lookup, not against PostgreSQL; with a real token the lookup reads the policy, which the handoff states as what a passing check means. Whether the image has `curl` is unchecked, and the handoff says so.
4. **Out of scope, seen in passing:** `tests/test_gate.py` cites the frozen gate record as "Spec section 2.6", "section 8, point 11" and others, without the marking; the paragraph-sign gate doesn't see the word "section". Not touched.
5. The concept's `cacheScope: private` for the resource templates (K §4.4) is neither checked nor documented: the `server/discover` result carries `cacheScope: private` at the server level, and I didn't verify the templates.
6. The ledger ships after the final review (controller); the frozen unit spec's status line already names its future path `docs/superpowers/sdd/2026-10-11-pilot-mcp-lesezugang/`.
