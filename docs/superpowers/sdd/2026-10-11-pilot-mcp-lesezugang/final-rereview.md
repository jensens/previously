# Final re-review, pilot unit 4 (MCP read access)

Gates run by me: pytest on test_mcp_server, test_access, test_docs_references, test_docs_typed_output, test_render, test_storage, test_policy (297 passed; there is no tests/test_gaps.py, the gaps tests live in test_access.py), pyright 0/0/0, lint-imports 9 kept, `make -C docs html` clean. Vale, linkcheck and the full suite not run (not allowed here).

## Per item
1. policy gaps (R-16): RESOLVED. `core/access.py` Withheld.uncovered/source, form check `_withheld_problem`, `read.py:275` fills from `decision.fallback.circles`, `core/gaps.py` counts `uncovered`, else `source:`, else `event:`. Tests: test_access.py:345 (three circles, two with a rule), :278-279 form check; no-content tests green. Spec header notes it.
2. read_policy SQL filter (R-17): RESOLVED. `LogStore.actions` (contract/store.py, storage/postgres.py), `policy.py:571` uses it, test_storage.py:802 and a counting subclass in test_policy.py:331. No migration: `git diff --stat 2e71dc3..fb890d9 -- src/previously/migrations` is empty. Figures 0.341 s to 0.010 s at 6,000 rows, dated, in report and map. Projection kept open in map. Docstring count rewritten (14 methods).
3. 400 attachments: RESOLVED. `render.py` `_MAX_ATTACHMENTS` with `+N more`; test_render.py:446 asserts len <= PAGE_CHARS, `+390 more`, `page.units == ((1,),)` and unit text visible.
4. /healthz (R-18): RESOLVED. auth.py `_is_health` is method GET and exact path equality (no prefix). Tests test_mcp_server.py:1104-1147: 200 without token and no mcp_access, any host, 503 against a real unreachable store, and POST/HEAD `/healthz`, `/healthz/`, `/healthz/mcp`, `/healthzz`, GET `/mcp`, `/` all 401. Body is the constant `ok` or the constant error text; no data. Both accepted deviations are safe: `ready()` calls only `log.tip` inside `snapshot()`, its result discarded; the bypass is exact-path so every other path still passes host check and token check. The host-check test has the control (same foreign host on /mcp with token gives 421). Handoff and cli.md updated; spec header notes the departure from S section 8.
5. Cache hints (R-19): RESOLVED. server.py `_CACHE_HINTS` passed as `cache_hints=`; wire test test_mcp_server.py:1063 asserts `("private", 0)`.
6. Minors: RESOLVED. M-1 mcp-interface.md:163; M-2 server.py docstrings; M-3 `decode_cursor` removed; M-5 constants (`PAGE_CHARS`, `MAX_IDS`) in descriptions; M-6/R-20 stated in mcp-tools.md ("delivered as its placeholder"); `record_access` docstring corrected.
7. Wrong-way limit (R-21): RESOLVED. trust-boundaries.md:146-151 new heading "A record can name an answer that never arrived", mcp-interface.md:199, map entry, `record_access` docstring, spec header. The old heading "A call can go unrecorded here too" is gone (grep). The remaining "A call can go unrecorded." at trust-boundaries.md:134 is the gate's `model_call`, which is true.
8. Quotation test: RESOLVED on the evidence of the diff (test_docs_references.py rewritten, +148 lines) and a green run. I did not re-mutate it.
9. M4 table: RESOLVED. Embedded-resource row at mcp-interface.md:59 and the narrowed sentence at :64.
10. Doc minors: RESOLVED where I checked (gate handoff supersession sentence, K section 9 60-second limit and `/mcp refresh` in the map, docker-compose `client add` at handoff:120, auth.py citation form). The small reference nits were not each checked.
11. Following pages: RESOLVED (cli.md, handoff, reference, explanation, module-boundaries, map touched).

## Specific checks
- (a) OK, see item 4. (b) OK, item 1. (c) OK, item 2. (d) OK, item 3. (e) OK, item 5. (f) OK, item 7.
- (g) Tutorial block: collected 1537, progress-line counts sum to 1537, every percentage equals int(100*cum/1537) (checked by script, zero mismatches), "1537 passed", and `pytest --collect-only` gives 1537 now.
- (h) Map count: 202.

## New issues
- Minor: the M4 table's embedded-resource row reads "Not measured" in its third column; fine as honest, but the sentence above it says the embedded resource "arrived in both clients", so the third client column is the only gap. No action needed.
- Minor: the full suite, vale, linkcheck and pip-audit are outside this re-review; the implementer's report claims them, unverified here.

No Important issues found.

## Verdict
Approved
