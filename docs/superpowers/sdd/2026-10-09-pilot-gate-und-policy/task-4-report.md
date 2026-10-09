# Task 4 report

Status: DONE (with concerns below). Commit: c9552f8 on worktree-pilot-gate.

## What
- `gate/__init__.py`, `gate/adapters/__init__.py` (Request, Response, AdapterError, Adapter, `adapter_error` helper), `anthropic.py`, `openai_compatible.py`.
- `tests/conftest.py`: `ModelServer` + `model_server` fixture (ThreadingHTTPServer, port 0, daemon thread, `enqueue(path, status, body, *, delay=0.0)`, `requests`; unqueued request answered 500 and still recorded).
- `tests/test_gate_adapters.py` (22 tests), `tests/test_contracts.py` (+4 parametrized probe tests: anthropic/openai x core/adapters).
- `.importlinter`, `pyproject.toml` (`anthropic>=1.13.0`, `openai>=3.27.0`; no pydantic per R-2), `uv.lock`, `DEPENDENCIES.md`, `module-boundaries.md`, tutorial test block retyped.
- Call shapes as measured: Anthropic `output_config` (+effort only when set), `inference_geo` via SDK `omit` when None; OpenAI-compatible `response_format` strict, `extra` via `extra_body`. `max_retries=0` in both. Anthropic `max_tokens=4096` (required by API, my choice).
- Error text: `"<provider>: call failed (<ExceptionClass>): <text>"`, key replaced by `[key removed]`, whitespace collapsed, cut at 200 chars.

## RED / GREEN
RED: collection error `ModuleNotFoundError: No module named 'previously.gate'`. GREEN: 22 passed.

## Mutations (each applied, run, reverted)
- M1 `inference_geo` always sent (`or "global"`): 1 failed (`..._no_geo_field_when_none_is_set`). M1b never sent: 1 failed (`..._carries_geo_schema_and_effort`).
- M2 `max_retries=0` removed from both clients: 6 failed (500 tests for both adapters incl. `test_a_500_is_not_retried_silently[0,1]`, timeout tests).
- M3 key not removed: 5 failed (401/500 x2 adapters echo test, `test_the_key_is_removed...`).
- Control: unmutated, 22 passed.

## lint-imports measurement
`import anthropic` in `core/probe_sdk.py`: `Only the gate adapters import vendor SDKs BROKEN`, `previously.core.probe_sdk -> anthropic`. Same with `import openai` in `gate/probe_sdk.py`. Reverted; 8 kept, 0 broken. Both now permanent tests in `test_contracts.py`.
Layers contract name: `Layers: cli, connectors beside gate, core beside migrations, storage, contract`.

## Six gates (final tree)
ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), pytest --cov (1172 collected; 97.91% total; the earlier run failed only `test_typed_test_counts_match_the_tree`, the expected stale tutorial count), docs html/vale (0/0/0)/linkcheck all green. Retype (T1-a): set only the `N passed` number to 1172 to unblock, ran `uv run pytest` once to a green 1172 passed, then replaced the block with that run's output (rootdir line dropped, as the page says). The block now shows the `anyio-4.15.1` plugin, a real consequence of the new dependencies.
`uv run pip-audit --skip-editable`: No known vulnerabilities found.

## DEPENDENCIES.md evidence (2026-10-09)
- anthropic 1.13.0 (2026-10-09), 226 releases, repo anthropics/anthropic-sdk-python pushed 2026-10-09, not archived, MIT, py.typed.
- openai 3.27.0 (2026-10-09), 445 releases, repo openai/openai-python pushed 2026-10-09, not archived, Apache-2.0, py.typed.
- New transitive: pydantic 2.14.0 (2026-10-08), httpx2 2.13.1 (2026-09-23, 18 releases, repo pydantic/httpx2), anyio 4.15.1, jiter 0.17.0, sniffio, docstring-parser, typing-inspection, h11, httpcore2, truststore, annotated-types, pydantic-core.
- The "No pydantic — not yet" paragraph stays (R-2); I appended a sentence that it is installed transitively but not declared.

## Concerns
1. `cli -> gate` does not exist yet: module-boundaries.md counts 11 existing of 19 permitted edges (`cli -> gate` listed as absent). Task 5 must update that page when the edge appears (diagram, counts, grep block for cli).
2. pydantic is now in uv.lock transitively; Task 5 adds the declaration, its DEPENDENCIES row and the ruff `runtime-evaluated-base-classes` entry.
3. Error text includes up to 200 chars of the provider's own message (key stripped). A provider echoing the prompt in an error body would put prompt text into the sentence; the brief says text after key removal, so I kept it, truncated. Task 5 should not store it somewhere that must be prompt-free without thinking about it.
4. `ModelServer` does not override `log_message` (A002/pyright conflict on `format`), so http.server access lines go to stderr; pytest captures them.
5. `OpenAICompatibleAdapter.extra` default is `{}` per the interface (no B006 hit, copied into a dict).
6. No new lint suppressions, no type: ignore.
