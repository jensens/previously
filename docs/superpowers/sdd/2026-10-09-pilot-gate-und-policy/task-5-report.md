# Task 5 report: the gate

Status: DONE_WITH_CONCERNS. Commit `9362d0a` on `worktree-pilot-gate`, on top of `c9552f8`.

## What was built

- `gate/task.py`: `Task[Out: BaseModel]` with `name`, `version`, `system`, `template`, `output`, `candidates`; `render(units)`, `schema()`, `prompt_sha256()` (SHA-256 of canonical `{system, template}`), `schema_sha256()` (sorted, compact JSON of `model_json_schema()`).
- `gate/tasks/mail_overview.py`: `MailOverview` (`extra="forbid"`), `MAIL_OVERVIEW` with candidates `anthropic/claude-haiku-5-5` (`low`), `mistral/mistral-small-2603`, `local/qwen3:4b`.
- `gate/prices.py` + `gate/prices.toml`: `Prices(as_of, sha256, table, surcharges)`, `load_prices(path=None)` (package file through `importlib.resources`, numbers read with `parse_float=Decimal`), `estimate()` exact and unrounded (`format(normalize(), "f")`), `PricesUnreadable` (a `PreviouslyError`, exit 2).
- `gate/gate.py`: `Called`, `explain()`, `call()`. Erased event → `denied`, reason `the event is erased`, no request. All units tombstones → `denied`, `no unit of the event holds content`. `stop_reason == "refusal"` → `refused`. `ValidationError` → `schema_invalid`; an answer canonical JSON refuses (NUL) → `schema_invalid` too. `AdapterError` or missing adapter → `error`; the payload carries `error: {provider, kind, status}` and never the provider's text (R-9). Alarm `geo_mismatch` when a region was requested and the reported one differs (`None` counts as different). Payload keys exactly as Spec §4.1 (+ `error` on `outcome: error`), `policy.rules` mapped through `Policy.ids[("rule", scope)]`, `local_only` left out (no id; `fallback` says it), `policy.providers` = declarations of the candidates consulted up to the chosen one.
- `core/gaps.py`: `Gap(what, count, last)`, `gaps(log, conn, since=)`; circles from `policy.fallback.circles`, otherwise `source:<source>` via `source_keys` of the input event, otherwise `event:<id>`.
- `core/action.py`: `OK`, `DENIED`, `REFUSED`, `SCHEMA_INVALID`, `ERROR`, `OUTCOMES`.
- `core/verify.py`: `model_call has no valid form: …` — no/unknown outcome, ok without units, units without ok, `inputs` not a list, an entry without an int `event`.
- `gate/adapters/__init__.py`: `AdapterError` now carries `provider`, `kind`, `status` (from `status_code` of both SDKs); docstring softened per R-9 (the sentence may hold up to `MAX_DETAIL` characters of the provider's words, the audit takes the fields alone). `openai_compatible.py` raises with the fields.
- `cli.py`: `gate explain EVENT`, `gate try EVENT`, `policy gaps [--since]`; help `gate` — `explain or try a model call`. Adapters built from `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `PREVIOUSLY_LOCAL_MODEL_URL` (local with `reasoning_effort: none`), prices from `PREVIOUSLY_PRICES` or the package. Exit 0 / 2 / 3. Wordings from the Global Constraints table.
- pydantic declared (`pydantic>=2.14`, `uv lock`), `runtime-evaluated-base-classes = ["pydantic.BaseModel"]` set, `DEPENDENCIES.md` row with judgement; the "No pydantic — not yet" paragraphs replaced by a short history that keeps its §10.7 and §8.6 citations, so the header's count of thirteen references still holds (recounted).
- `T201` re-measured: 49 (was 40), comment updated.
- Docs: `cli.md` (fourteen subcommands, exit-code row, exit 3, `policy gaps`, new `gate` section with label `cli-gate`, model_call findings), `configuration.md` (seventeen variables, new section *Model provider settings*: the four variables, who reads what, `ANTHROPIC_BASE_URL`, the price file format), `module-boundaries.md` (recounted: thirteen edges, `cli → gate` and `gate → contract` new, six absent; grep block retyped 2026-10-09; one paragraph on the lazy adapter import), README command count (fourteen). Tutorial test block retyped.

## Deviations from the brief's interfaces

1. `Task.render` is a method over a `template` field, not a `Callable[[EventRow, Sequence[UnitRow]], str]` field. Reason: `prompt_sha256` must hash what turns content into a prompt, and a callable cannot be hashed; with `template` the hash covers it. Signature: `render(units: Sequence[UnitRow]) -> str`.
2. `Prices` has a fourth field `surcharges: Mapping[str, Decimal]` (the `us` 1.1 as its own entry, `[surcharges]` in the TOML).
3. `Called` has a seventh field `reported_geo: str | None = None`, needed for the alarm sentence.

## Files

New: `src/previously/core/gaps.py`, `src/previously/gate/gate.py`, `src/previously/gate/prices.py`, `src/previously/gate/prices.toml`, `src/previously/gate/task.py`, `src/previously/gate/tasks/__init__.py`, `src/previously/gate/tasks/mail_overview.py`, `tests/test_gate.py`.
Changed: `src/previously/cli.py`, `src/previously/core/action.py`, `src/previously/core/verify.py`, `src/previously/gate/adapters/__init__.py`, `src/previously/gate/adapters/openai_compatible.py`, `tests/conftest.py` (test server silent: `log_message` overridden, see concerns), `tests/test_action.py` and `tests/test_verify.py` (their bare `{"action": "model_call"}` is a finding now; given the smallest sound form), `tests/test_cli.py` (help line), `tests/test_docs_references.py` (two more blocks held), `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md`, `README.md`, `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/explanation/module-boundaries.md`, `docs/tutorials/record-your-first-event.md`.

## RED

Skeletons with `NotImplementedError` and no `gate` command, then `uv run pytest tests/test_gate.py -p no:randomly`: `53 failed, 2 passed` (the two passing were the data-only checks of the candidates and the schema). Failures were `NotImplementedError` and `SystemExit: 2` (argparse without `gate`), not import errors.

## GREEN

`tests/test_gate.py`: 60 tests. Full run `uv run pytest --cov --cov-report=term-missing`: `1233 passed in 192.83s`, coverage 97.97 %.

Spec §8 coverage (R-3): 9 (every outcome written: denied, erased, refused, three schema_invalid cases, unstorable answer, error from 400, missing adapter, local server down), 10 (no unit text, no line ≥ 8 chars, no address or name in any string of the payload, keys included; for no rule, `any` and `us`; control: the same search finds the wording in the request the server received), 11 (region set for `any`→`global`, `us`, `{eu,us}`→`us`; R-6 control: Mistral gets no field; mismatch → alarm, exit 3), 14 (401 echoing the key: not on stdout, stderr, any payload or unit; control: the request reached the server). Fallback: event, stderr, `policy gaps` (and `--since`), and the controls with a rule. Review focus 1, 3, 4 at both the gate and the command line.

## Mutations (each applied, measured, reverted; file diffed back)

| # | Mutation | Result |
|---|---|---|
| M1 | `inference_geo=None` in the request | 3 region tests red; R-6 control green |
| M2 | alarm dropped (`alarms = ()`) | 2 red (gate, CLI exit 3) |
| M3 | denied call writes no event | 3 red |
| M4 | prompt text in place of `prompt_sha256` | 3 no-content tests red |
| M5 | schema check replaced by `model_construct(**json.loads(...))` | 4 red (3 RF3 cases + CLI) |
| M6 | provider's sentence added to `payload.error` | R-9 test red |
| M7 | `policy.fallback` always `None` | 4 red (event, circle, gaps, CLI gaps) |
| M8 | verify skips the model_call form | 5 red |
| M9 | key not removed in `adapter_error` | key test red |
| M10 | cli.md: refused line, alarm line, explain line reworded | 3 red (gate refused CLI, explain, docs_references) |
| Control | unmutated | `55 passed` (before the later additions), then `60 passed` |

## Six gates (after the last change)

```
uv run ruff check .                -> All checks passed!
uv run ruff format --check .       -> 107 files already formatted
uv run pyright                     -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                -> Contracts: 8 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> 1233 passed, 97.97 %
make -C docs html && make -C docs vale && make -C docs linkcheck -> build succeeded; ✔ 0 errors in 34 files; build succeeded, 0 broken
uv run pip-audit --skip-editable   -> No known vulnerabilities found
```

The tutorial block was typed from one complete green `--cov` run (1233 passed in 201.24s), its session part only (the `rootdir:` line and the coverage table left out, as the page's command `uv run pytest` prints neither). After typing, two test files got type annotations only (pyright); the gate run above was repeated on the final tree with the same count, the block was not retyped from it.

## Price sources (read 2026-10-09)

- Claude Haiku 5.5: https://platform.claude.com/docs/en/about-claude/pricing — $0.10 in / $0.50 out per MTok for prompts up to 100k tokens; `inference_geo: "us"` 1.1x on all token categories. Long prompts (>100k) pay more; the file does not model that (stated in its header).
- Mistral Small 4, `mistral-small-2603`: https://docs.mistral.ai/models/mistral-small-4-0-26-03 and https://docs.mistral.ai/inference/pricing — $0.15 in / $0.6 out per MTok (standard mode). The marketing page mistral.ai/pricing lists no per-model price.
- `qwen3:4b`: not in the file, `cost_usd: null`.

## Concerns

1. **Interface deviations** 1–3 above; tasks 6 and 7 should read `Task.template`/`render(units)`, `Prices.surcharges`, `Called.reported_geo`.
2. **`ANTHROPIC_BASE_URL`**: the Anthropic SDK reads it when the adapter passes no `base_url`, so in production a set variable redirects calls (and the key) elsewhere. The CLI tests use it to reach the test server; `configuration.md` says it. The OpenAI SDK likewise reads `OPENAI_ORG_ID`/`OPENAI_PROJECT_ID` and would send them as headers to Mistral or the local server; not documented, not chased.
3. **Lazy import** of the adapters inside `cli._adapters()`: measured 1.3–1.5 s for `import previously.cli` + Anthropic adapter against 0.5 s without; a top-level import would slow every command and widen the SIGTERM window. Documented in the code and on `module-boundaries.md`.
4. **Refusal on the OpenAI-compatible path**: only Anthropic's `stop_reason: refusal` maps to `refused`; an OpenAI-style `message.refusal` with empty content becomes `schema_invalid`. Named, not chased.
5. **Provider metadata in the payload** (`response.model`, `request_id`, `stop_reason`) goes into the chain as given; a control character there would make `append_action` raise after a paid call, leaving it unrecorded. Only with a misbehaving provider; named, not chased.
6. **Alarm when nothing is reported**: a requested region with `reported_geo is None` counts as a mismatch (printed `reported nothing`). Errs toward alarm; only Anthropic gets a region today, and it reports.
7. **pydantic's schema carries `title` keys** (`"title": "MailOverview"`, per field). The calls of 2026-10-09 were measured with a hand-written schema without titles; whether Mistral strict mode and Ollama accept the titles is unmeasured until acceptance 10.
8. **README** still says "no language model … and no action but the redaction" under *What it does not do*; only the command count was fixed here, the rest belongs to task 7.
9. **`tests/conftest.py`**: `ModelServer`'s handler now overrides `log_message` (silent) — the access lines on stderr broke every CLI test of `gate try` (task 4 named that concern).
10. **`policy show` vs `policy gaps`**: `gaps` with nothing to report prints `no call fell back to local only` on stderr and returns 0 (documented).
