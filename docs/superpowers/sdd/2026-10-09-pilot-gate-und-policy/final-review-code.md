# Final review, code package — Pilot, Einheit 3: Gate und Policy

Range 78b0d85..a1f632a (code). Reviewer: Opus, 2026-10-09, read-only.

How it was read: spec (all of it), plan (all of it), ledger (all of it); the
new modules in full from the tree (`core/action.py`, `core/policy.py`,
`core/decide.py`, `core/gaps.py`, `gate/gate.py`, `gate/task.py`,
`gate/tasks/mail_overview.py`, `gate/adapters/*`, `gate/prices.py`,
`prices.toml`); the changed modules as diffs (`cli.py`, `core/redact.py`,
`core/redaction.py`, `core/verify.py`, `chronicle.py`, `.importlinter`,
`pyproject.toml`, `tests/test_contracts.py`); the tests by name plus the
bodies behind every Review Focus item and R-12. The 9010-line diff package was
used for the ruling-citation census, not read end to end. Between a1f632a and
HEAD only `tests/test_docs_references.py` changed under `src/`/`tests/`.

Measured here, against the project configuration:

- `ruff check .`, `ruff format --check .`, `pyright`, `lint-imports` green at
  HEAD (b9276e7). pytest and the docs gate were not re-run (brief).
- Two probes in the scratchpad (not in the tree), run with the project's
  `tests/conftest.py` against the testcontainer: findings I-1 and M-1 below.
- `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py`:
  50 at HEAD; 49 at 9362d0a, 50 at a1f632a (finding M-2).

## Strengths

- The seams line up end to end. `Policy.ids` is keyed by `key_of`, and the gate
  looks up exactly `(RULE, scope)` for each `Decision.rule_keys` scope and
  `(PROVIDER, name)` for each consulted candidate; `local_only` has no id and
  is visible through `fallback`. `inputs` is written by the gate as
  `[{event, units: [readable seqs], blobs: []}]`, and the cascade
  (`_entry_event`, `_entry_list`) and `verify` (`_inputs_read`, `_erased` via
  `of_event`/`of_unit`/`of_reference`) read the same three keys with the same
  meaning. `fallback.circles` feeds `gaps`, which resolves the empty case to the
  source key, and `_fallback_lines` resolves it the same way.
- No customer content reaches a chained payload on any path I could find. The
  `model_call` payload is built from task constants and hashes, unit seqs,
  operator-set names and ids, decision sentences that only name providers,
  models, regions and days, and provider metadata; R-9 keeps the provider's
  words out of `error`; `canonical` failures of the answer are caught and
  recorded as `schema_invalid`. Template formatting puts content in as a
  format *argument*, so braces in a mail are harmless.
- `decide` is genuinely pure and errs strict: unknown retention fails a limit,
  empty region intersection passes nothing that infers, a revoked circle has no
  members (R-5), own identities are dropped before resolution, domain
  case-insensitive / local part exact. R-7's "widest fitting space" is
  monotone, and the Hypothesis property covers the R-8 scope.
- The R-12 lock round is right: targets and calls in one ascending round before
  any chain position, a cascade position loss rolls the whole erasure back, and
  the A/B pair is shown by a real two-transaction test. R-11 (observations only)
  is the cheap and correct way to keep the cascade one level deep.
- Adapters: `max_retries=0`, one request per `complete` proven against a real
  HTTP server, key scrubbed from exception text, `raise … from None`; the vendor
  SDKs are lazily imported by the CLI and fenced by two named import-linter
  edges with probes in `core` and beside the adapters.
- All five Review Focus items have tests at the level the plan named, most on
  both the function and the command line: 1 → `test_gate.py:582`, `:1111`;
  2 → `test_decide.py:420`; 3 → `test_gate.py:634` (three variants), `:1135`;
  4 → `test_gate.py:747`, `:1160`; 5 → `test_policy.py:179`,
  `test_cli.py` (member in missing circle, `project:` rule).

## Issues

### Critical

None.

### Important

**I-1. An erasure that lands while a provider call is in flight leaves the
answer standing; `verify` goes red with two legitimate commands.**
`src/previously/gate/gate.py:247-249`, `:263-267`, `:293`.
`call` reads the event and its units in one transaction, then calls the
provider outside any transaction (seconds; up to the 60 s timeout), then
`append_action`s the `model_call` with the answer in a unit — without locking
or re-reading its input. A `redact event` that commits in that window finds no
call to cascade (it is not written yet), and the call is then written with a
live answer derived from erased content.
Measured with a scratch probe: an adapter whose `complete` runs
`redact_event` on the source before answering → `redact` returns
`cascaded: ()`, the call is written `ok` with its unit, and `verify` reports
`model_call 7 keeps the result of erased input`.
Why it matters: the product's erasure promise. An operator erasing a mail on
request while someone runs `gate try` on it (or, later, a batch of the
AI layer) keeps a derived summary that only `verify` reveals. The redact
docstring (`core/redact.py:41`) and the map entry ("ein `model_call`, der
zwischen dem Lesen und dem Sperren der Kaskade entsteht") describe the window
from redact's side, as milliseconds between its read and its lock; from the
gate's side the window is the whole provider latency and nothing names it.
Recovery exists: `verify` names the call, and `redact units <call> 1` or a
second `redact event` of the source clears it.
Fix: in the gate's write transaction, lock the input event row with the same
row lock `redact` takes (`RedactionStore.lock_event`; `PostgresStorage` is
both), re-read its payload and the read units, and if anything read is now
erased, write the call and in the same transaction a units redaction of it
with `cascade of redaction <id>` (reuse `_cascade` from `core/redact.py`).
Then redact either waits at the row lock and finds the call, or committed
first and the gate cascades itself. A test: the probe above, asserting
`verify == []`, with the mutation "skip the re-read" measured red.
If the maintainer prefers the map: correct the map entry and the redact
docstring to say the window opens at the gate's read and spans the provider
call, and name it on `erasure.md`/`trust-boundaries.md`.

### Minor

**M-1. `verify` does not check that a policy event has no units.**
`src/previously/core/verify.py:433`. Spec §4.3 point 2 says "ein Policy-Event
hat seine Art unter `payload.policy` und deren Schlüssel, und keine
Einheiten"; `check_payload` gets the payload only, and nothing else looks at a
policy event's units. Measured: `append_action(to_payload(Circle("xz"), …),
[RawUnit(1, "secret customer text")])` → `verify(storage) == []`. Only an event
that bypassed `set_policy` can have units, so the effect is a forgery or a bug
that `verify` exists to catch and does not. Fix: `if name == POLICY and units:
finding "policy event has units"`, plus a test measured red with the check
removed and a green control (a policy event from `set_policy`).

**M-2. The `T201` count in `pyproject.toml` is stale.** `pyproject.toml:106-107`,
`:128`. It says forty-nine; measured 50 at HEAD with the command the comment
names. Task 6 added `print(f"cascaded: model_call {call_id}")` to `_cmd_redact`
after Task 5 measured 49. This is the exact class of claim `CLAUDE.md` lists
under "A comment is a claim". Fix: fifty, and a sentence that `redact`'s
`cascaded:` line took it there.

**M-3. `set_policy`'s docstring claims a guarantee READ COMMITTED does not
give.** `src/previously/core/policy.py:311-313`: "The check against the circles
that exist and the write are one transaction, so a circle revoked in between
cannot be named by a membership that passed the check." Under READ COMMITTED
(`storage/postgres.py:157`) `read_policy` and `log.tip` are two statements with
two snapshots; a revocation committed between them moves the tip, `write_action`
writes at the new tip+1 without a conflict, and the membership is written. R-5
makes such a membership inert in `decide` until the circle is created again,
when it silently becomes live. Fix: reword to what holds (the check and the
write are one attempt; a concurrent revocation can slip between them, and R-5
makes the result inert), or take the tip before reading the policy and insert
only at that position so a concurrent write forces a retry. Map the race either
way.

**M-4. `processed locally: …` is printed when nothing was processed.**
`src/previously/cli.py:1527`, `:1542`. Ledger minor of Task 5, triaged here
because of who hits it: in kup6s, until the model server exists, every call
without a rule ends `denied: … no local provider is declared`, preceded by
`processed locally: no rule for source:email — …`. The first line is false and
the second contradicts it. Same with an unreachable local server. Fix: print
the line only when the call ran locally (`outcome == ok` or the chosen provider
is local and the outcome is not `error`), or reword it to
`local only: no rule for … — set one with …` so it is true in every case; the
plan's wording table and the tests at `test_gate.py:1047`, `:1308` follow.

**M-5. `policy provider --storage` is optional and defaults to the loosest
value.** `src/previously/cli.py:1305`. Spec §5 lists `--storage …` as a required
part of `policy provider`; the code has `nargs="*", default=[]`, and an empty
storage means "stores nothing", which passes every region rule
(`decide._inside`). A forgotten flag declares the provider loosest. No effect on
the pilot's providers (Anthropic fails `eu` on inference, Mistral is `eu`
anyway), and the structured form shows `"storage": []` before the question.
Fix: `required=True` (a local provider then passes `--storage` with no value),
and a test that the omission is refused.

**M-6. Two ruling citations do not name their plan.** `tests/test_gate.py:421`
(`Ruling R-6:`), `:699` (`Ruling R-9:`). `CLAUDE.md`: labels are per plan, so a
citation names the plan's date. The neighbours already do ("Ruling R-11 of the
2026-10-09 gate plan"). Also note for the docs package: the census command in
`CLAUDE.md` matches only `ruling (P|T[0-9]+)-…`, so none of the new `R-` labels
are found by it.

**M-7. `gate try` on an erased or non-observation event cites every provider.**
`src/previously/gate/gate.py:183-190`. With `chosen is None`, `consulted` is
every candidate, so a call denied as `the event is erased` records
`policy.providers` with all three declarations and `regions: []`, although no
candidate was weighed. An auditor reads "these promises were consulted". Fix:
for `_denied(...)` decisions write `providers: []` (e.g. return early when
`decision.circles == () and not decision.rule_keys`), or leave and map.

**M-8. A malformed `PREVIOUSLY_LOCAL_MODEL_URL` breaks every `gate try`, with a
traceback.** `src/previously/cli.py` `_adapters`. Measured:
`OpenAICompatibleAdapter(base_url="http://[::1")` raises `httpx.InvalidURL` at
construction, before the decision, so a call that would go to Anthropic fails
too, outside the `PreviouslyError` handling. Misconfiguration: name it, map it.

## Deferred-minor triage

| Ledger minor | Verdict |
|---|---|
| T1: `test_chronicle` reads columns by index | map (style) |
| T1: no own test for `append_action`'s retry | map — `retrying` is shared with `redact`, whose retry is tested |
| T2: `cli.md` says `policy` refuses `--regions` without a region; argparse does | fix before merge, docs package (a page that says something false; one line) |
| T2: `test_cli._action_count` imports in the function, `db: object` | map |
| T3: provider with an empty `inference` list never passes; odd reason | map (misdeclaration) |
| T4: `AdapterError` docstring vs R-9 | closed — the docstring now says the sentence may hold provider text and the audit takes the fields only |
| T4: floors `anthropic>=1.13.0`, `openai>=3.27.0` three-part | map |
| T4: `__all__` only in `adapters/anthropic.py` (and it re-exports `AdapterError`) | map |
| T4: key removal by `str.replace` misses an encoded form | map (already on the map) |
| T5: no-content test runs over `ok` only | map — every outcome builds its payload from the same parts; `ok` is the superset |
| T5: NUL / lone surrogate in provider metadata fails the write after a paid call | map (already on the map) |
| T5: `processed locally` on denial and unreachable server | **fix before merge** — see M-4; false on the default kup6s path |
| T5: without a source, the line proposes `policy rule event:<id>` | map — not misuse (an `append` without a key is legitimate), but rare in the pilot; reword when touched |
| T5: CLI uses strings instead of `core.action` / `RULE` constants | map |
| T5: `gate explain` reads the policy twice in two transactions | map |
| T5: OpenAI-format refusal ends `schema_invalid` | map (already on the map) |
| T5: two tests import in the function | map |
| T6: `cascaded:` lines missing on the `unfinished` path | map (already on the map); a two-line move if someone is in `_cmd_redact` anyway |

## Declined to judge

- R-7 against the spec's literal "`us` nur, wenn `regions` auf `us` beschränkt": the ruling is the maintainer's reading, and monotonicity holds.
- `reports_inference_geo` is declared, stored and shown but read by nothing in `decide` or the gate: the spec defines it as a declaration only.
- `gate try` prints output and event id but not the decision (spec §5 says it prints the decision): the plan's wording table is the contract and `gate explain` gives the decision.
- Membership events hold customer addresses in chained payloads, and erasing one acts as a revocation (the previous version revives): by spec (§2.1), and erasable.
- An address in a header the mail parser raises on contributes no identity, so its circle does not bind: a stage-1 mapping decision, and the spec names unknown participants as a limit (§2.2).
- `redact event <model_call>` erases the audit record itself: R-4 allows it, and the redaction stays in the chain.
- `model_call` with `inputs: []` passes `verify`: only reachable by bypassing the gate; forgery-level.
- `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `OPENAI_ORG_ID` read from the environment by the SDKs: operator-set environment, R-10 routes it to the trust-boundaries page.
- `PREVIOUSLY_LOCAL_MODEL_URL` printed on a local error could carry userinfo credentials: no such URL in the plan or handoff.
- `read_policy(at=…)` filters by `recorded_at` while replacement goes by chain order: equal under a wall-clock `recorded_at`, which is the only one the CLI writes.
- The policy and the event are read in one READ COMMITTED transaction in `_read`, so two snapshots: same class as M-3, harmless for a decision.
- Mutation measurements claimed in the ledger were not repeated; I measured only the two new findings above.
- Docs, handoff, map and the frozen spec are the docs package.

## Assessment

Ready to merge: **yes with fixes**. The seams between policy, decide, gate,
cascade and verify line up. No customer content reaches a chained payload. Keys
stay out, and every Review Focus item is tested. The one real fault is I-1: an
erasure during an in-flight provider call keeps the answer, `verify` turns red,
and the code does not name that window from the gate's side. Fix it with the
row lock and self-cascade described there, or have the maintainer move it to
the map with the wording corrected. M-1 to M-4 and M-6 are each a few lines and
should go in the same fix wave.
