# Final fix wave — pilot unit 4 (MCP read access)

One wave, then one re-review. Close every item below completely; there is no
second round. The two review reports carry the reproducers:

- code: `final-code-review.md`
- docs: `final-docs-review.md`

(both in this directory). The ledger `progress.md` holds rulings R-1 to R-15;
the new ones for this wave are R-16 to R-21 below and stand in the ledger too.

## Code

1. **`policy gaps` names circles that have a rule** (code I-1). Ruling R-16:
   `Withheld` gets a field with only the circles that lack a rule (from the
   decision's fallback, `decision.fallback.circles` or wherever `decide`
   exposes them) and the event's `source`; `gaps` counts that field, and an
   event in no circle is grouped under `source:<source>` as the gate does.
   Neither field is customer content (circle names are policy names; a source
   is `email`). Form check, parse, `previously access`, sketch and no-content
   tests follow. Test with the reviewer's probe shape: three circles, two with
   a rule — only the third appears. Measure red against the old counting.
   Retype the `policy gaps` example in `docs/reference/cli.md` from one real
   run if its output changes.
2. **Every call reads every action event** (code I-2). Ruling R-17: a store
   method that reads only the actions of one kind, filtered in SQL
   (`payload->>'action' = %s`, or the form the schema allows), **without a
   migration** (K §9: no table, no migration); `read_policy` uses it, and so
   does anything else that reads only policy actions. Name it in
   `LogStore`'s protocol and in `storage/postgres.py`; recheck the docstring
   that counts the modules naming `LogStore` (code M-4: it says six, the grep
   finds eleven — count it yourself). Measure `read_policy` before and after
   with 6,000 `mcp_access` rows (the reviewer measured 0.425 s before) and
   write both figures, dated, into the report and the map entry. A projection
   of the policy stays an open point in the map.
3. **A `get_event` page can exceed `PAGE_CHARS`** (code I-3). Cap the
   attachment names as recipients are capped (`+N more`), so a page never
   exceeds the limit; a unit counts as delivered only if text of it reached
   the page, not just its marker. Test with 400 attachment names: within
   `PAGE_CHARS`, and `Delivered.units` matches what is visible. Measure red.
4. **Readiness without a token** (code point 8). Ruling R-18: the auth wrapper
   answers `GET /healthz` before the token check — a constant body after a
   trivial database query (`SELECT 1` through the store's connection; 503 and
   a constant body if it fails), no MCP, no data, no `mcp_access`. Every other
   path still needs the token. Tests: 200 without a token, 503 when the
   database is unreachable if that is testable without a mock (otherwise say
   so), and any other path without a token still 401 (measure red with the
   route matched by prefix). The handoff's readiness probe becomes an HTTP GET
   on `/healthz`; `server/discover` with a token stays as a manual end-to-end
   check. Deviates from S §8 ("Bereitschaft über `server/discover`") — note
   that in the unit spec's frozen header as the earlier departures are noted.
5. **Cache hints** (code point 7). Ruling R-19: pass the SDK's cache hints to
   `MCPServer` explicitly as private (look up the parameter in the installed
   `mcp`), and add a wire test that `resources/read` in 2026-07-28 answers
   `"cacheScope":"private"`.
6. **Minors, code:**
   - M-1 (rotation between token check and handler serves one request under
     the new record): name it on the explanation page; no code change.
   - M-2: the docstrings that say "every call writes one" say what is true —
     a call that reaches a handler; 401, 421 and transport 400 write nothing.
   - M-3: `render.decode_cursor` is unused in `src` — remove it, or have the
     server use it; no function that only tests call.
   - M-5: the tool descriptions take `PAGE_CHARS` and the id limit from their
     constants; the checksum test is updated to the resulting literal.
   - M-6: an erased event logged under `delivered` with no units — Ruling
     R-20: keep it, and say so in the reference page's `mcp_access` section
     (an erased event was "delivered" as its placeholder; no unit reached the
     client).
   - The `record_access` docstring in `core/access.py` states the wrong limit
     (docs I-1) — correct it.

## Docs

7. **The named limit is the wrong way round** (docs I-1). Ruling R-21: the
   record is written before the answer returns; what can happen is an answer
   lost **after** the record is committed — stdin closed, an HTTP connection
   dropped, the process stopped — so the log names a delivery the client
   never received. A failed write gives the client the SDK's error, never
   content. Correct `mcp-interface.md`, `trust-boundaries.md` (the heading "A
   call can go unrecorded here too" is false), the map entry, and add the
   departure from S §7 to the unit spec's frozen header.
8. **The quotation test holds quotes by fragments** (docs I-2). Build the
   `rule` and `no_rule` reasons with the pure `decide` and the withholding
   function and compare them exactly against the page; inline module-level
   string constants (`CURSOR_REFUSED`, `_MOMENT_HELP` or their current names)
   so their wording is held. Mutate a reason's wording on the page and in the
   code → red; control green.
9. **The M4 table** (docs I-3): add the embedded-resource row, and narrow the
   sentence to what the measurement shows — `structuredContent` and
   `resource_link` cost content; the result stays one text block because that
   is what both clients carry whole.
10. **Minors, docs** (each in `final-docs-review.md`): the gate handoff's
    "nothing inbound" sentence (say in the MCP handoff that it is superseded);
    `mcp-tools.md` lines named in the review (the `policy` row, `call.name`
    for a refused resource, "counted in the header"); the garbled sentence in
    `mcp-interface.md`; K §9's 60-second call limit and `/mcp refresh` into
    the map; where `previously client add` runs under docker-compose; the
    small reference nits; `auth.py:13` citation form. The `tests/test_gate.py`
    and `tests/test_cascade.py` citations are out of scope — leave them.
11. **Pages that follow the code changes above:** `cli.md` (`/healthz`, the
    gaps output), `configuration.md`, the handoff, the reference page, the
    explanation page, `module-boundaries.md` if the store method changes it,
    the map.

## Rules

- Six gates and `pip-audit` before the commit:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  uv run pip-audit --skip-editable
  ```
- Every new assurance measured red under mutation with a green control.
- Retype the tutorial's pytest block from ONE run, last.
- Recount every number in a comment you touch; T201 if `print` calls change.
- Ruling citations: `ruling R-<n> of the 2026-10-11 MCP read access plan`, one
  `ruling` per label, the reason beside it.
- No `# type: ignore`, no new `noqa`, no mocks of time, database, randomness.
- Stage files by name; trailer `Assisted-By: Claude Opus 5.5
  <noreply@anthropic.com>`; never `pkill -f`; no subagents.
