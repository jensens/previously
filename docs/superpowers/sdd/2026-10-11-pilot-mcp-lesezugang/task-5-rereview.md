# Task 5 re-review (fix round 1, 5694f77..964584f)

- I-1 (R-11): RESOLVED. Template `previously://event/{event_id}` at src/previously/mcp_server/server.py:106; the only `noqa` in src is the old C901 at core/canonical.py:41; `git diff 3d9b911 -- CLAUDE.md` is empty.
- I-2 (R-13): RESOLVED. render.py:~520-560 `encode_cursor` writes only `{"after": id, "filters", "page"}` (probe: `{"after":28,"filters":{"circle":"x"},"page":2}`); old list form is refused; `resume_point` (read.py:359) looks up `occurred_at`, returns None for a non-observation or a missing id; server.py:458-460 maps None to the fixed refusal. test_a_cursor_after_a_placeholder_tells_no_time (tests/test_mcp_server.py:1154) covers the placeholder page and gap-free paging; the existing gap-free walk test is still green.
- I-3: RESOLVED. tests/test_mcp_server.py:988 test_a_header_naming_a_client_is_no_identity (both modes).
- M-1: RESOLVED. docs/reference/cli.md:1105 states 404 with a token, 401 without; test at tests/test_mcp_server.py:966.
- M-2 (R-14): RESOLVED. Third-party top-level imports in src: alembic, anthropic, boto3, botocore, html2text, mcp, openai, pydantic, pyrage, sqlalchemy, starlette, uvicorn (types_boto3_s3 via types-boto3-lite[s3], type-checking only). All declared in pyproject.toml; anyio and httpx2 are in the test extra. DEPENDENCIES.md:59 botocore row has date (2026-10-11) and evidence (1.43.111, 2533 releases, pushed 2026-10-09, not archived, Apache-2.0); starlette (:58), anyio (:60), httpx2 (:61) likewise. lint-imports: 9 kept, 0 broken.
- M-3: RESOLVED. All 13 R-citations in src/ and in tests/test_render.py and tests/test_mcp_server.py read "of the 2026-10-11 MCP read access plan" with the reason beside them. (R-labels in tests/test_gate.py, test_cascade.py and test_decide.py are untouched by this round and belong to another plan; out of scope.) Minor: tests/test_mcp_server.py:567 and :614 have the qualifier on the line after the label, acceptable.
- M-4: RESOLVED. `conn: Conn` in server.py:502, 516, 543.
- M-5: RESOLVED. tests/test_render.py:603 test_more_without_items_gives_no_cursor.
- M-6: RESOLVED. test_no_token_stands_in_the_log_or_the_server_log at tests/test_mcp_server.py:458; test_a_cursor_that_does_not_lead_on_is_an_error at :1181 covers other filters, a policy event id and a missing id (999_999), each the fixed `Error:` sentence and an `error` access entry.

Check (a): cursor holds no timestamp (probe above). Check (b): forged nonexistent id and non-observation id both give `Error:` through the tool, no exception (test above, passing). Check (e): the tutorial block sums to 1517 = `collected 1517 items` = `uv run pytest --collect-only` (1517); every percentage equals int(100*cumulative/1517); 0 mismatches.

Runs: pytest tests/test_mcp_server.py tests/test_render.py: 156 passed. lint-imports: 9 kept. pyright src/previously/mcp_server: 0 errors.

## New issues
None.

## Verdict
Approved
