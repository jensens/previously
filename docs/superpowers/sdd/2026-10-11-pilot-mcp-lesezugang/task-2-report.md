# Task 2 report: clients as principals

## What
- `core/policy.py`: kind `client` (`CLIENT`, `Client(name, processor, token_sha256)`), in `KINDS`, `key_of`, `to_payload`, `_parse`, `_check` (non-empty name and processor, token hash = 64 lower-case hex digits), `refusal` (processor must be a declared provider unless revoking), `Policy.clients` (last field, defaulted, so existing constructors still work).
- `core/clients.py` (new): `mint_token` (`secrets.token_urlsafe(32)`), `token_hash`, `client_for_token` (`hmac.compare_digest` per client, no early exit), `add_client`, `revoke_client` (repeats the hash it lifts; refuses an unknown name), `client_rows` (for `list`).
- `cli.py`: `client add|revoke|list`; the replacement notice goes to stderr before `write? [y/N]`; refusal comes before the question; stdout of `add` is exactly `client <name>: token <token>` and `shown once; store it now`; help `add, revoke and list MCP clients`. R-2(a): `--model-origin unknown` maps to `None`.
- R-2(b): `.vale.ini` now reads "Sixteen of the twenty-four entries" (recounted: `awk 'NF && /^[a-z]/'` gives 16, 24 non-empty lines).
- `pyproject.toml`: T201 count 51 -> 61, re-measured with the comment's command (61 errors).
- Docs: `cli.md` (fifteen subcommands, exit-code row, `--model-origin NAME|unknown`, new `client` section), `policy-and-model-calls.md` (six kinds, client row and key table), `tests/test_docs_references.py` (six kinds, client keys held against `to_payload`), tutorial test block retyped (T1-b).

## Tests
`tests/test_clients.py` (10), additions in `tests/test_policy.py` (7 incl. parametrized) and `tests/test_cli.py` (8 incl. parametrized). Total 1304 -> 1329.

## RED
Before the implementation: `tests/test_clients.py` ImportError at collection; the policy and cli tests `14 failed, 1 passed` (the one pass is the `--model-origin us` control).

## Mutations (each applied, red, reverted)
1. Token stored in the payload instead of the hash (`Client(name, processor, token)` plus form check off): 5 red, among them `test_the_token_is_in_no_payload_only_its_hash` and `test_client_add_prints_the_token_once_and_stores_only_its_hash`.
2. Replacement keeps the old token valid (key and `clients` map include the hash): 7 red, among them `test_adding_a_name_again_replaces_the_client_and_the_old_token_stops_matching`.
3. Control (reverted): 23 passed.

## Six gates
ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), `pytest --cov` (1329 passed; clients.py 100%), docs html, vale, linkcheck: all green.
The tutorial block: the doc first carried `1329 passed` (the guard only reads that number), then ONE run of `uv run pytest` (seed 2948148521, 1329 passed) was typed in whole, minus the `rootdir:` line as the page says.

## Concerns
- `client add` checks the processor in the CLI with a placeholder hash before the question (the real hash needs the token). Comment says why.
- `policy show` does not list clients (the spec names `client list` as the surface).
- Not done: other explanation pages that may say "five statements" were grepped (`five kinds` only on the reference page) and none found.

## Fix round 1
1. cli.md now says what `add` prints: the summary (`client NAME` and `processor PROVIDER`, separated by a tab), the question, then the two token lines, and nothing after. Pinned by `test_client_add_prints_the_summary_then_the_two_lines_and_the_page_says_so` (stdout lines exactly, page sentences quoted).
2. The token line uses `escape_field(args.name)`. The same test uses a name with a tab. Mutation (unescaped): red.
3. Finding premise differs from the code: `_parse` already ends in `_check(item, sentence)`, which includes `_check_client`, so a damaged hash is already malformed and skipped. No code change; added `test_a_client_event_with_a_damaged_hash_is_skipped_and_a_lookup_returns_none` (non-ASCII hash written via `append_action`). Mutation (form check off): red; control (restored): green.
Tests 1329 -> 1331; tutorial block retyped from one `uv run pytest` run (1331 passed). Six gates green: ruff, format, pyright 0, lint-imports 8 kept, `pytest --cov` 1331 passed (clients.py 100%), docs html/vale (0 errors)/linkcheck.
