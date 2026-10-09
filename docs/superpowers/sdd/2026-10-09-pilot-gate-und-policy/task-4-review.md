# Task 4 review (26f4cb4..c9552f8)

Read the diff once, in passes (uv.lock only skimmed: additive, 15 new packages, no removals or bumps of existing ones). No git re-run, no suite re-run.

### Spec Compliance
- Interfaces (Request, Response, AdapterError, Adapter, both adapter constructors, MISTRAL_BASE_URL, ModelServer with enqueue/requests/url): match the brief. `enqueue` has an extra keyword `delay`, which the timeout test needs; harmless extension.
- Call shapes: Anthropic `output_config` with `format` plus `effort` only when set, `inference_geo` via SDK `omit` when None (anthropic.py:49-57); `usage.inference_geo` becomes `reported_geo`; `stop_reason` passed through, refusal tested. OpenAI-compatible: `response_format` strict, `extra` via `extra_body`, `reported_geo=None`. `max_retries=0` in both clients (anthropic.py:41, openai_compatible.py:48). OK.
- `.importlinter`: contract name and the two named `ignore_imports` exactly as the brief; `connectors | gate` in one layer; layer-contract name follows. No pattern exemption. OK.
- Dependencies: anthropic and openai added, no pydantic (R-2 respected; DEPENDENCIES.md paragraph explains that it is installed transitively). Rows carry date, release, repo push date, archived state, licence, py.typed. OK.
- module-boundaries.md: I recomputed the edge counts (6+4+4+2+2+1 = 19 permitted; 8 absent; 11 existing; 10 external arrows). Consistent.
- Tests required by the brief all exist: geo/schema/effort, no geo field when None, strict + extra + reported_geo None, 401/500/timeout/refused with a conspicuous key, exactly one request. Mutation and lint-imports probe measurements are reported and now permanent (test_contracts.py, 4 parametrized probes, covering both SDKs from `core` and from beside the adapters).
- No suppression: grep of the added lines for `noqa`, `type: ignore`, `pyright: ignore` finds none in this diff (the hits in other review-*.diff files belong to other tasks). `cast` used for `OutputConfigParam`.
- Test-server responses: both bodies are complete for what the SDKs read (id, type, role, model, content, stop_reason, usage / choices, usage); the tests assert fields that only parse if the SDK model accepted them (e.g. `reported_geo == "us"`, token counts). Real HTTP, real SDK, no mock. See Minor 2 on tolerance.
- Key stripped on every AdapterError path: all exceptions go through one `adapter_error` (`except Exception ... from None`), replacement runs before truncation and whitespace collapsing. 401/500 echo tests plus a double-occurrence test. Timeout and refused-connection paths use the same function and assert the key is absent. ⚠ Those two tests cannot go red under the key-not-removed mutation (the key never occurs in those texts); the echo tests carry that mutation, which is fine because the code path is shared.
- Exactly one request on a 500: `test_a_500_is_not_retried_silently` queues 500 then 200, so a silent retry would turn the call into a success and fail the test; also `len(requests) == 1` on timeout and 401/500. Good design.

### Strengths
- The queued-500-then-200 construction makes the no-retry assertion discriminating, not just a count.
- Unqueued request answers 500 and is recorded, so retries show up as data rather than a hang.
- Single funnel for errors; `from None` keeps the original exception (with request headers) out of the printed traceback.
- Probe tests derive the package name instead of hard-coding it, and show the exemption is the two named modules, not the package.
- Tutorial block retyped from one run (new `anyio` plugin line honestly shown); docs counts verified.

### Issues
**Critical:** none.

**Important:** none.

**Minor**
1. `adapters/__init__.py:84-86`: the f-string with a conditional is one 100+ character line; style only. More relevant: the error text carries up to 200 characters of the provider's own message (the brief allows it). A provider that echoes the prompt would put prompt text into the sentence, contradicting the class docstring's "holds neither the key nor the prompt" (`adapters/__init__.py:57`). The docstring claim is stronger than the code; soften it or note the limit. The report already flags the downstream risk for Task 5.
2. Test bodies are well-formed but the SDKs (pydantic construct) tolerate missing fields, so no test would notice a body that omits, say, `usage.cache_creation`; acceptable since only fields the adapter reads are asserted. Not a defect.
3. Key removal is a literal `str.replace`: a key that appears JSON/repr-escaped in the exception text (quotes, backslashes) would survive. The key test checks `json.dumps(KEY)[1:-1]` but the test key has no characters that escape, so that assertion is vacuous. Real API keys are URL-safe, so low risk; note it or drop the vacuous assertion (`tests/test_gate_adapters.py`, last lines of `test_the_key_is_removed_from_the_text_of_the_exception`).
4. `anthropic.py` ends with `__all__ = ["AdapterError", "AnthropicAdapter"]` re-exporting a name it never uses except in the list; `openai_compatible.py` has no `__all__`. Inconsistent; drop or add in both.
5. pyproject floors `anthropic>=1.13.0`, `openai>=3.27.0` are the day's latest, three components, while the other floors are two (`boto3>=1.43`). CLAUDE.md says floors say what the code needs; no measurement is given that `output_config`/`inference_geo` need exactly 1.13.0.
6. `uv.lock` header `revision = 3` becomes `5`: the lockfile format was rewritten by a newer uv than whatever wrote it before. Confirm CI's uv reads revision 5; otherwise this is churn that could make a lock check fail.
7. `ModelServer` leaves `log_message` alone, so access lines go to stderr (report concern 4); harmless under pytest capture.
8. Anthropic `MAX_TOKENS = 4096` is the implementer's choice, documented in a comment; a truncated reply surfaces as `stop_reason == "max_tokens"` with invalid JSON for the gate to reject, which matches the "adapter does not validate" rule.

### Assessment
**Approved.** No Important or Critical findings; the named risks (geo omitted when None, one request on 500, key stripping on all paths, no suppressions, SDK-parsed response shapes) all check out in the diff. Minor items are for the implementer's discretion or a later task.
