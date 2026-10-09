# Task 7 report: documentation, handoff, map, freeze

Commits on worktree-pilot-gate (base a1f632a): e6bbe89 (pages, tests, indexes, README, vocabulary, tutorial block, design-records), d7651f7 (handoff), 82bb0de (map), b9276e7 (freeze).

## Pages

| Page | Quadrant | Label | What it argues |
|---|---|---|---|
| docs/explanation/trust-boundaries.md | Explanation | trust-boundaries | Table of every place content crosses (IMAP, S3, backups, anchor, gate) with who guards it and the page; the gate per provider (Anthropic 30 days/US storage, Mistral EU/retention unknown, local); only gate imports the SDKs; a record of every attempt, no content, no key; R-10 ANTHROPIC_BASE_URL (environment is the operator's, like the keys); gaps: provider retention (30 days Anthropic, unknown Mistral) reached by no erasure, unknown participants bind no rule where a source rule applies, a call can go unrecorded if the process dies between answer and write, a write error after a paid call, MCP and writing outward ahead. |
| docs/explanation/processing-policy.md | Explanation | processing-policy | Two checks (processing vs. before writing outward, "disclosure check" dropped); circles after Simmel, explicit membership, own identities removed; strictest wins, R-8 (first rule for a circle / first rule at all lifts local_only on purpose, replacing may loosen); promise vs. report with the measurement that `global` is reported back as `global`; R-7 (widest fitting region, no ranking, 1.1x cost of `us`); without a rule only local, qwen3:4b needs `reasoning_effort: none` (>600 s otherwise) and is weaker, so the fallback is visible in three places; policy is an action not an assertion; audit in the log, result in units; R-11 (observations only, cascade stays one level); what the pilot leaves open. |
| docs/reference/policy-and-model-calls.md | Reference | policy-and-model-calls | Policy events (common keys, five kinds with replacement key, rule/provider keys, built-in rule), model_call payload (top level, task, inputs, policy, fallback, response, error), outcomes, unit of an ok call, alarm, denial reasons, two JSON examples. |
| docs/how-to/set-a-policy-and-try-a-call.md | How-to | set-a-policy-and-try-a-call | Ollama + qwen3:4b; declare providers, circle, member, own identity; explain; try; gaps; rule any/eu; hosted keys; revoke. |

Outputs typed in the how-to were produced by a real run on 2026-10-09 (throwaway Postgres 17 in Docker, the test mail plain.eml appended through `map_mail`, real Ollama 0.13.2 with qwen3:4b, 15 s): explain with local_only, try, gaps, rule any -> anthropic/global, rule eu -> mistral. Hosted-model calls were not run (no keys); the page says only what the code and a run showed. Container removed afterwards.

Also edited: indexes of the three quadrants and docs/index.md, README (state, a bullet, the "does not do" paragraph), docs/explanation/design-records.md (nine records; paragraph for this one, four departures), vocabulary (Ollama, Simmel, Georg added to .vale-styles accept.txt, tracked).

## Quoted wordings and how they are held

New tests in tests/test_docs_references.py (4, plus an optional `name` argument on `_first_cells`):
- keys of every policy statement: common keys, kinds table == KINDS, per-kind "further keys" cell == keys of `to_payload`, replacement-key cell names only payload keys, rule/provider keys table.
- keys of a model_call: tables of payload/task/inputs/policy/fallback/response/error equal the string keys of the dict displays in gate/gate.py (`call`, `_policy_part`, `_response_part`) plus the `payload["x"] =` assignments; the JSON example held key by key.
- the rule example whole: `to_payload` rewrites it to the same dict.
- words: KNOWN_ACTIONS, OUTCOMES, GEO_MISMATCH, NOT_OBSERVATION/ERASED/NO_UNITS, NO_LOCAL_PROVIDER, NO_RULE, MailOverview.model_fields.

Mutations (all red, control green): page key renamed; extra key in example; outcome renamed; denial reason reworded; provider key renamed; in the code: ERASED reworded, extra response key, `alarms` key renamed, alarm renamed. Found for free: my contraction pass had turned the quoted "is not an observation" into "isn't" and the full run went red on exactly that test; fixed.
Not held: the replacement key of `membership` ("circle and member") is checked only as a subset of payload keys, since `key_of` returns values, not field names.

## Map

Open points before: 152; after: 178 (command from CLAUDE.md). +1 under *Feststellungen und Entitäten* (project scope), +25 in the new section *Gate und Policy (Pilot, Einheit 3)*. The way via prompt, the Batch API and Pydantic arrival were merged into existing bullets of *Spätere Teilprojekte*; the Teilprojekt-4 point "Verarbeitungsräume der Anbieter" was struck to *Erledigt* (commits 5cbdf9d, 26f4cb4) together with the "next alpha release" (v0.1.0a2 of 2026-10-09, handoff of the ingest handed over). Table row for unit 3 (built, merge pending; condition 10 follows), units 3 and 4 use "Verarbeitungsprüfung", "Das Gate" struck as precondition, new precondition row for the check before writing outward, "Was jetzt kommt" rewritten. The new section includes all deferred minors of the ledger (Tasks 3 to 6) and two findings of this task (`policy rule --revoke` demands `--regions`; the price file does not model Haiku's >100k-token surcharge). I cite the execution record as P-PG (`sdd/2026-10-09-pilot-gate-und-policy/`, "folgt mit der Endprüfung"): it does not exist in the tree yet.

## Freeze

Spec b9276e7: frozen header like the others, status line (dated 2026-10-09, plan, the same-day amendments 62d044f/5a2fa6f/26f4cb4, condition 10 follows the merge, four departures of the build), the sentence about freezing in past tense, §11 in the past tense pointing to the map, list kept as that day's state.

## Gates (once, at the end)

ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept, 0 broken), pytest --cov --cov-report=term-missing 1255 passed, 98.00 %, docs html (build succeeded, no warnings), vale 0/0/0 in 38 files, linkcheck succeeded; pip-audit --skip-editable: No known vulnerabilities found.
Tutorial block (T1-b): placeholders set to 1255 first, then one plain `uv run pytest` (green, 1255 passed in 187.93 s) retyped whole, `rootdir:` line dropped; the 1255 before the retyping came from a first plain run that had 1 failure (the contraction slip above), so the block comes from the second.

## Concerns

- The map says "merge steht aus" and has no PR number; the controller must correct it after the merge (and the status row, as for the ingest).
- The ledger (progress.md) is not in the tree yet, so every P-PG citation in the map and the frozen spec header points at a record that arrives with the controller's step 3.
- `policy rule --revoke` requires `--regions` (value ignored): documented, left as is.
- The hosted-provider paths in the how-to (key set, anthropic try, alarm) are described, not typed; Condition 10 is where they get run.
- Handoff: model server memory/CPU unmeasured and said so; the release number of the gate release is not known, so it reads "the first after 0.1.0a2".
