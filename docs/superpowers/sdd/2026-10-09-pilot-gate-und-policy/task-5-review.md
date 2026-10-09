# Task 5 review: the gate (c9552f8..9362d0a)

Reviewer: read-only. I read the diff in three passes: the gate source, the CLI with core (`gaps`, `verify`, `action`) and the adapters, then the tests and the docs. I did not run the suite. I ran two focused checks:

1. `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` gives **49**, which matches the comment in `pyproject.toml`.
2. A scratch probe, for one doubt: does a key with a trailing newline leak? This is the classic Kubernetes secret mistake. I called both adapters with `api_key="sk-CONSPICUOUS-…\n"` against a dead port. Both raise `AdapterError` with `call failed (APIConnectionError): Connection error.` and the key does not appear. The doubt is cleared.

### Spec Compliance

**§3.2 flow / §8.9 (every call becomes one `model_call`).** Each path is checked, and each writes exactly one event: the tests use `(row,) = model_calls(storage)`.
- Denied by the policy writes `DENIED`, and no provider is reached. The code is at gate.py:259-262 and the test at test_gate.py:488.
- An erased event is denied with the reason `the event is erased`, with no request and `inputs.units == []`. The code is at gate.py:146-147 and the tests at test_gate.py:517 and 1046 (exit 2, one sentence).
- An event whose units are all tombstones is denied with `NO_UNITS` (gate.py:148-149).
- A missing adapter is an `error` with `kind: not_configured`. The code is at gate.py:275-282 and the test at test_gate.py:659 (CLI test at 1126).
- An `AdapterError` gives an `error` whose payload holds only `{provider, kind, status}`, which satisfies R-9. The code is at gate.py:284-286 and the test at test_gate.py:631, which uses unit 2's real text `Liebe Eva` as the echo.
- A refusal is `refused`, with `response` kept and no units (gate.py:295-299; test_gate.py:539 and 1295).
- An answer against the schema is `schema_invalid` with no units: an extra field, a missing field, and non-JSON all go through `model_validate_json` (gate.py:300-304; test_gate.py:569, CLI test at 1070).
- An answer the schema takes but the log cannot store (NUL) is also `schema_invalid` (gate.py:305-308; test_gate.py:610).
- `ok` stores one unit of canonical JSON (gate.py:309-312).
- A missing event raises `PreviouslyError` and writes nothing: exit 2, `Error: there is no event N` (gate.py:104-107; test_gate.py:705 and 1265). This is sound: no call could have read anything, and a `model_call` whose `inputs` names a nonexistent event would be a false record.

**Exit codes (§5).** `ok` returns 0. Every other outcome returns 2. `ok` with an alarm returns 3. A refused or schema-invalid call with an alarm returns 2, and the alarm is still printed (cli.py `_cmd_gate_try`). This matches "ein Alarm bei sonst gelungenem Aufruf gibt 3".

**§8.11 / risk 2 (region).**
- `Request.inference_geo = decision.inference_geo` (gate.py:272), and the same value goes into `policy.inference_geo` (gate.py:194).
- The alarm fires only when `requested is not None and reported != requested` (gate.py:293). With `global` requested and `global` reported, there is no alarm, which matches the 2026-10-09 measurement. The parametrized test at test_gate.py:391 covers it.
- For R-6, the test at test_gate.py:420 shows that Mistral gets no field.
- The mismatch alarm and exit 3 are tested at test_gate.py:445 and 1025.
- One good side effect: the OpenAI-compatible adapter ignores `inference_geo`. If `decide` ever named a region for such a provider, `reported None != requested` would raise the alarm instead of dropping it silently.

**§8.10 / risk 1 (no content).**
- `inputs.units` holds sequence numbers.
- `task` holds name, version and two hashes.
- `policy` holds circle names, rule and provider ids, regions, and reasons built only from policy names (decide.py:141-170).
- `fallback` holds circle names.
- `error` holds the provider, the class name and an int.
- `response` holds provider metadata only, and the answer of a refused or schema-invalid call is never stored.

I found no path from unit text, the subject (unit 1), headers, addresses or the prompt into the payload. `content_of` covers the text of every unit, every line of 8 or more characters, and the addresses and names in `channel_identities`. `strings_in` walks every string recursively, keys included. Coverage: see Minor 1.

**§8.14 / risk 4 (key).**
- The 401 echo test (test_gate.py:1148) checks stdout, stderr, every payload and every unit, with a control showing that the request reached the server.
- Both adapters wrap every client exception with `from None` (anthropic.py, openai_compatible.py). That leaves no chained traceback and the key removed from the sentence.
- `main` turns `PreviouslyError` into one line (cli.py:1748-1760).
- I found no path where an exception carrying the key escapes uncaught.
- My probe of the trailing-newline key came back clean.

**§2.6 / §8.7 / risk 5 (fallback, explain, gaps).**
- The fallback is marked in the event (test_gate.py:318 and 351), on stderr (test_gate.py:982 and 1006), and in `policy gaps` (test_gate.py:895 and 1274, with `--since`).
- The controls under a real rule show no mark and empty stderr (test_gate.py:367, 922 and 957).
- `explain` opens a read transaction and calls `_decide`, with no write path (gate.py:159-166). The event count is unchanged both at the API (test_gate.py:806) and on the CLI (test_gate.py:1209).
- `gaps` reads `read_by_kind("action")`, keeps only `payload.action == model_call` with a mapping `policy.fallback`, and filters by `recorded_at >= since` (gaps.py:53-71).

**§4.3 (verify).** The form is held: an outcome from `OUTCOMES`, units exactly at `ok`, `inputs` a list whose every entry has an int `event` (verify.py `_model_call_problem`). All six findings are tested, both ways against cli.md (test_gate.py:854-881, 1316). A written `model_call` passes `verify` (test_gate.py:884).

**§3.4 (cost).** `estimate` is exact Decimal math: 1830/212 at 0.10/0.50 gives `"0.000289"` and `us` gives `"0.0003179"`, both checked by hand. An unknown model gives `None`. Prices are parsed with `parse_float=Decimal`. The SHA-256 is taken over the bytes on disk.

**Risk 6 / deviation 1 (`Task.template` + `render(units)`).** This deviation is sound and consistent with §4.1. `prompt_sha256` is `sha256(canonical({system, template}))`, the hash of the template before any content goes in (task.py:58-61). A callable field, as the brief had it, cannot be hashed at all. The joining logic in `render` (`"\n\n"`, tombstones skipped) is outside the hash, but `version` covers that. Mutation M4 and the form test (test_gate.py:775-780, which pins `prompt_sha256 == MAIL_OVERVIEW.prompt_sha256()`) would both catch a hash of the rendered prompt.

**Deviation 2 (`Prices.surcharges`).** Sound. The brief itself asks for the `us` 1.1 as its own entry.

**Deviation 3 (`Called.reported_geo`).** Sound. The alarm sentence needs it, and its default of `None` keeps construction compatible.

**R-2.** pydantic is declared with a floor, `runtime-evaluated-base-classes` is set, and `DEPENDENCIES.md` has a dated row with evidence. **R-9**: the docstring is aligned. **R-10**: `ANTHROPIC_BASE_URL` is documented in configuration.md.

**Docs follow the code.**
- cli.md has the `gate` section, the exit-code row, exit 3, `policy gaps`, and the model_call findings.
- configuration.md now counts seventeen variables, 13 + 4, which is correct.
- module-boundaries.md and README are recounted.
- test_docs_references holds two more blocks, and "seventeen"/"thirteen" are consistent with the +1/+5 sentences and +2 blocks.

**⚠️ Not verified:**
- The six gates and the 1233 count (not re-run, by instruction).
- The import-time figures in the `_adapters` docstring (1.3-1.5 s against 0.5 s).
- The price figures at their sources.
- Whether Mistral strict mode and Ollama accept pydantic's `title` keys (report concern 7; acceptance 10).

**Missing or misread against the spec (plan-mandated, not an implementer defect).** Spec §5 says `gate try` prints "Ergebnis, Entscheidung und die Id". The binding wordings table narrows stdout to the JSON and the id, so the decision is printed only on a denial. The implementation follows the table.

### Strengths

- `call` keeps the dangerous parts structurally separate:
  - The payload is assembled from decision and metadata before the prompt exists.
  - The rendered prompt lives only in `Request`.
  - The provider's error text goes only into `Called.message`.
- `else:` keeps a payload `InvalidPayload` from being misfiled as `schema_invalid` (gate.py:300-312).
- The tests are strong:
  - The no-content test has a positive control: the same search finds the wording in the request the server received (test_gate.py:747-749).
  - The key test proves the key was there to leak.
  - The R-6 test asserts that the field is absent rather than null.
- Ten mutations are reported, each mapped to an assurance, with controls. M1, M2, M4, M5, M6 and M9 hit exactly the silent failures this gate exists to prevent.
- The comment numbers I checked are correct: T201 = 49 (measured), seventeen variables, and the counts in test_docs_references.

### Issues

#### Critical
None.

#### Important
None.

#### Minor

1. **The no-content search does not walk the payloads of denied, refused or schema-invalid calls.** test_gate.py:720 parametrizes `None`/`any`/`us`, and all three end `ok`. The R-9 test (631) covers the error path with one marker.
   - Today those paths add only constants and provider metadata, so there is no leak.
   - But a later change that put content into a denial's `reason`, for example, would not be caught.
   - Extending the parametrization with a denied case and a schema-invalid case would close it cheaply.
2. **A paid call can go unrecorded when the provider's metadata is unstorable.** `_response_part` copies `response.model`, `request_id` and `stop_reason` into the payload (gate.py:205-216).
   - A NUL character or a lone surrogate there makes `canonical` raise `InvalidPayload` inside `record()`.
   - That error is outside both `try` blocks, so it escapes `call`: the CLI exits 2 and no `model_call` is written, against §3.2 "Ein Aufruf, der stattfand, steht immer im Log".
   - Only a misbehaving provider triggers it, and the implementer named it (concern 5). Name it in the map; do not chase it.
3. **"processed locally" is printed when nothing was processed locally.** On a denial under `local_only` with no local provider, the fallback line still goes to stderr: cli.py `_fallback_lines`, tested in test_gate.py:1243-1261 next to `decision denied`. The same happens on an `error` when the local server is down (test_gate.py:1116). The wording is fixed by the table, but printing it on a denial reads as a false statement. Consider printing it only when the chosen provider is local.
4. **A suggested fix that `policy` would refuse.** `event:<id>` scope, cli.py `_fallback_lines` and gaps.py:86-88: for an input event without a source, the stderr line suggests `previously policy rule event:<id> …`, which is not a scope `policy rule` accepts. This is reachable mainly through misuse (`gate try` on an action event), so name it.
5. **String literals instead of constants in the CLI.** cli.py `_failure_line` compares against `"denied"`, `"refused"` and `"schema_invalid"` instead of the constants in `core.action`. `_explain_lines` uses `("rule", scope)` instead of `RULE`. Polish.
6. **Two policy reads.** cli.py `_cmd_gate_explain` reads the policy twice in separate transactions: once inside `explain`, once for `rule_ids`. A policy write between the two could print rule ids that don't belong to the decision. This is cosmetic for a read-only command.
7. **Refusal on the OpenAI-compatible path.** An OpenAI-style refusal or `finish_reason: content_filter` is recorded as `schema_invalid`, not `refused` (concern 4). Name it.
8. **A function-level import in a test.** test_gate.py:708 and 1352 import inside test functions, which is the style the task 2 minor already named.

### Assessment

**Approved.**

The task meets §2.6, §3, §4.1, §4.3, §5 and §8 points 9, 10, 11 and 14, and all named risks check out against the spec.
- No path carries content into the payload.
- The region `decide` names is the one sent.
- The alarm fires on exactly the requested-but-different case, consistent with `global` → `global`.
- Every outcome writes one `model_call`, with exit codes 0, 2 and 3.
- The key reaches no output.
- `explain` writes nothing, and `gaps` reads only `model_call` events with a fallback.

The three interface deviations are sound, and tasks 6 and 7 need to be briefed on `Task.template`/`render(units)`, `Prices.surcharges` and `Called.reported_geo`. The minors are polish, or named edge cases for the map. Minor 1 is the one worth taking in a fix round if one happens anyway.
