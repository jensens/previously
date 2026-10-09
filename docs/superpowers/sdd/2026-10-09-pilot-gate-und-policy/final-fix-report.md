# Final fix report — Pilot, Einheit 3: Gate und Policy

Fixer: Opus 5.5, 2026-10-09, one wave (ruling R-15). Base b9276e7.

Commits:

- `89a79f0` gate: write a call under the lock of its input, and the final review's code fixes
- `13241a5` docs: the pages follow the fix wave, and the final review's documentation fixes
- `f08ca34` map: the fix wave of the gate's final review

Mutations were made in the working tree from a copy in the scratchpad, measured, and the copy restored; none is committed.

## Code

### I-1 (ruling R-14): an erasure during the provider call

What changed:

- `core/redact.py`: new public `append_call(log, eraser, payload, units, *, recorded_at) -> AppendedCall(call_id, erased_by)`. In its own transaction (`retrying`) it locks every input event with `_lock_ascending` (the `FOR NO KEY UPDATE` row lock `redact` takes), reads the redaction index again, finds the first redaction that erased an input's event, a read unit or a read blob (`_erasure_of`, the same three questions `verify` asks), writes the call, and if one did, runs `_cascade` on the call itself with `trigger` = that redaction (`cascade of redaction <id>`), all in one transaction.
- `core/redact.py`: the other order needed a fix too, which the review's proposal did not name. `redact` read the calls before its lock, so a call the gate committed while `redact` waited at the gate's lock was not in its list. New `_lock_round`: read calls, lock targets + calls in one ascending round (R-12 unchanged), then read the calls again and lock the newcomers in a second round. A newcomer was not committed at the first read, so its id is above every row of the first round and the order stays ascending. Used by `redact_event`, `redact_units`, `redact_blob`.
- Module docstring of `core/redact.py`: the sentence "A call appended after the read goes unlocked and uncascaded …" replaced; it now says that from the gate's side the window was the whole provider call (seconds, up to the adapter timeout), not the moment between an erasure's read and its lock, and how both sides close it.
- `gate/gate.py`: `call(log, eraser, task, …)` takes the eraser (same store, as `redact_event` does); every outcome is written with `append_call`. `Called.erased_by` names the redaction; an `ok` whose answer was erased has `output=None` and a message. Module docstring names the window.
- `cli.py` `gate try`: for such a call prints `model_call: event N` and on stderr `erased: the input was erased by redaction R while the call ran; the answer is erased with it`, exit 2.
- `tests/conftest.py`: `ModelServer.enqueue(…, hold=threading.Event)` holds an answer until the test releases it.

Tests (`tests/test_gate.py`):

- `test_an_erasure_while_the_provider_answers_erases_the_answer[erased-meanwhile]`: provider holds the answer, the test runs `redact_event` on the mail, releases; asserts `redaction.cascaded == ()`, `called.erased_by == redaction.redaction_id`, `output is None`, units `[None]`, cascade reason `cascade of redaction <id>`, `verify == []`.
- `…[control]`: no erasure, units kept, `erased_by is None`, `verify == []`.
- `test_an_erasure_that_waits_at_the_lock_of_the_gate_finds_the_call`: a `PostgresStorage` subclass pauses the gate right after it took the lock; `redact_event` starts in a thread and is seen waiting at a row lock (`pg_stat_activity`); then the gate goes on. Asserts `redaction.cascaded == (call_id,)`, units `[None]`, `verify == []`.
- `test_gate_try_whose_input_is_erased_during_the_call_prints_no_answer`: the command line, exit 2, stdout only the event line, the `erased:` sentence, `verify == []`.

Mutations, `uv run pytest tests/test_gate.py -q -p no:randomly -k "erasure or erasing"` (plus `test_cascade.py` for B):

| Mutation | Result |
|---|---|
| A: gate re-check removed (`trigger = None` in `append_call`) | `1 failed, 3 passed`: `[erased-meanwhile]` red with `assert [Finding(…'keeps the result of erased input')] == []`; control green |
| B: second read in `_lock_round` removed (`late = []`) | `1 failed, 37 passed`: `…waits_at_the_lock_of_the_gate_finds_the_call` red with `assert () == (6,)`; every cascade test green |
| C: gate's lock removed in `append_call` | `1 failed, 3 passed`: the waits-at-the-lock test red, but by its own wait timing out (`assert False` on `holding.wait`), not by `verify` — the hook never fires without the lock; noted as a structural signal only |
| `erased:` line removed from `cli.py` | `test_gate_try_whose_input_is_erased_during_the_call_prints_no_answer` red, the other 13 selected green |

### M-1: verify reports a policy event with units

`core/verify.py`: new `_form_finding` (also takes the complexity of `observe` back under C901) adds `policy event has units`. `cli.md` names the finding.
Test `tests/test_policy.py::test_verify_reports_a_policy_event_with_units[with-units|control]`: a policy event via `append_action` with a `RawUnit` → `verify == [Finding(id, "policy event has units")]`; control via `set_policy` → `[]`.
Mutation `if units and False:` → `1 failed, 2 passed` (`[with-units]` red, control green).

### M-2: T201 count

`uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` → `Found 51 errors.` (50 before this wave, +1 for the `erased:` line). `pyproject.toml` now says fifty-one, and that `redact`'s `cascaded:` line made fifty, which the count had missed.

### M-3: set_policy under READ COMMITTED

Code made true rather than the docstring weakened. `core/action.py`: new `write_action_at(log, conn, tip, …)`; `write_action` calls it with `log.tip(conn)`. `set_policy` reads the tip first, then the policy, checks, and writes right after that tip; a statement that committed in between holds the position, `ChainPositionTaken` → `retrying` → the next attempt checks again. Docstring rewritten to say exactly that.
Test `tests/test_policy.py::test_a_membership_checked_while_its_circle_is_revoked_is_refused[revoked-meanwhile|control]`: a store subclass whose first `read_by_kind` materialises its rows, then commits a revocation of `xz` through another store, then hands the rows on. `revoked-meanwhile` → `PolicyRefused('no circle "xz" exists')`, membership absent; control → membership written.
Mutation (`write_action_at(log, conn, log.tip(conn), …)`, the old behaviour) → `1 failed, 1 passed` (`[revoked-meanwhile]` red, control green).

### M-4: `processed locally` only where the local model answered

`cli.py`: `_fallback_lines` returns nothing when the decision chose no candidate (covers `gate explain` and `gate try` denials); `gate try` also suppresses it for outcome `error`. Docstrings and `cli.md` say when it appears.
Tests: `test_gate_try_says_the_fallback_on_standard_error` (local answered → line, unchanged, the control); new `test_gate_try_says_no_fallback_when_the_call_is_denied` (no local provider → only `denied: …`); `test_gate_try_against_a_local_server_that_does_not_run` (now: exactly one line, the `Error:` sentence); `test_gate_explain_says_no_fallback_for_a_denial` (renamed, stderr empty).
Mutations, `-k "fallback or denied or does_not_run or erased_during"`: dropping `or decision.chosen is None` → `2 failed, 12 passed` (the two denial tests); `answered = True` → `1 failed, 13 passed` (the unreachable-server test). The control stayed green both times.

### M-5: `policy provider --storage` required

`cli.py`: `--storage` `nargs="*", required=True`; given with no region it means "stores nothing". `cli.md` synopsis and option table follow. Test `tests/test_cli.py::test_policy_provider_requires_storage[omitted|empty|eu]`: omitted → `SystemExit(2)`, `the following arguments are required: --storage`, nothing written; empty → `storage: []`; `eu` → `["eu"]`.
Mutation (`default=[]` back instead of `required=True`) → `1 failed, 2 passed` (`[omitted]` red).
Side effect, mapped: `policy provider --revoke` now needs `--storage` as well as `--retention-days` (measured: `the following arguments are required: --storage, --retention-days`).

### M-6: ruling citations

`tests/test_gate.py`: `Ruling R-6` and `Ruling R-9` now read "Ruling R-6 of the 2026-10-09 gate plan" / "Ruling R-9 of …". Census `grep -rnE '\bR-[0-9]+\b' src tests | grep -v "of the 2026-10-09 gate plan"` → empty; the qualified citations are R-5, R-6, R-9, R-11, R-12, R-14 (three of R-14, new). The CLAUDE.md census pattern does not match `R-` labels: mapped, CLAUDE.md not touched.

## Documentation

- I-1: frozen spec header: amendments now "§8 Punkt 3 (Commits `da6c574`, `5a2fa6f`)", plus the sentence that §2.5 Punkt 5 was not amended; six departures as a list, R-7 (frozen "`us` nur, wenn `regions` auf `us` beschränkt ist, sonst `global`" vs. the widest fitting space, `{eu, us}` → `us`) and R-6 (frozen §3.2 Punkt 4, §8 Punkt 11 "immer ausdrücklich setzen" vs. no region for a provider with one space); the page wins. Body text untouched. `design-records.md`: "six places". `processing-policy.md`'s "always sets the region" now says "wherever the provider offers a choice".
- I-2: how-to: both `policy rule … --yes` blocks now carry the printed JSON and `policy event 9` / `policy event 10`; the first `gate explain` block now in terminal order, the fallback line last, and the text says "the last line, on standard error". Measured 2026-10-09 against a throwaway Postgres 17 in Docker, `plain.eml` appended through `map_mail`, the how-to's commands replayed in order (events 2–7 the six statements, 8 the `gate try` against Ollama `qwen3:4b`, 9 and 10 the rules), each output captured with `script -q -c … /dev/null` (a pseudo-terminal, so stdout/stderr order as on a terminal), one run each. The `gate try` and `policy gaps` blocks keep the Task 7 measurement (this run's model answer was correct, 14 s, so the page's sentence about the model's error belongs to the kept block). Container removed.
- I-3 (R-5): `processing-policy.md` — a paragraph why a revoked circle has no members (else it would keep binding its former members to `local_only`) and its consequence (content goes by the rules left, the source rule, possibly `any`; to keep it local revoke the rule and keep the circle; re-creating the circle revives the memberships). `policy-and-model-calls.md` — four sentences after the kinds table. How-to — after the revoke step, measured: after the revocation `gate explain 1` shows `circles -`, `rules local_only`, fallback for `source:email`.
- Factually wrong minors: "Budgetfunktionalität" instead of the direction of the delay (how-to and map); stderr order (above); hosted-key step exports `MISTRAL_API_KEY`, the error sentence is `Error: mistral: the provider is not configured — set MISTRAL_API_KEY` (measured in the same run).
- Four imprecise wordings: `fallback.circles` (reference, explanation, `core/decide.py` comment, `core/gaps.py` docstring: empty only where the content belongs to no circle and no rule applied); the "When" of `the event is not an observation` (any other kind, a redaction included; also in `cli.md`); `prompt_sha256` (the object `{"system", "template"}` as UTF-8 JSON, sorted keys, no white space); what `policy gaps` reads (`cli.md`, `processing-policy.md`, `gaps.py`).
- Also fixed on the same pages, cheaper than mapping: M-3 ("the examples above"), M-5 (provider revoke), M-6 (own identities mechanism), M-11 ("an earlier version of the project's map"), M-12 (`append` is a second door), M-15 (handoff: denial vs. `error` naming the variable or the server), M-16 (`inference_geo` null when denied, `usage` values may be null). M-13 and M-14 corrected in the map itself.
- Followed the code: `erasure.md` (a call in flight), `cli.md` (`erased:` line, `processed locally` conditions, `--storage`, `policy event has units`, `gate explain`'s stderr line), local provider in the how-to now `--storage` with no region.
- Tutorial test block retyped from one run of exactly `uv run pytest` (`1267 passed in 195.11s`, seed 1318060385), `rootdir:` line dropped as before; the count set to 1267 before that run.

## Map

`awk '/^## Offene Punkte/{f=1} /^## Erledigt/{f=0} f && /^- /{n++} END{print n}' docs/superpowers/landkarte.md`: **178 before (b9276e7), 183 after (f08ca34).**
Struck to *Erledigt* (with `89a79f0`): the call between read and lock of the cascade (with the window corrected to the whole provider call), `processed locally` on a denial. Added: `provider --revoke` needs `--storage` and `--retention-days`; up to 200 characters of provider error text on stderr, customer content in container logs once a job runs the gate; a CronJob for `policy gaps`; R-5's consequence as an open question; code M-7; code M-8; the CLAUDE.md census misses `R-` labels. Corrected: "Budgetfunktionalität" and the source of the 7–15 s (handoff), "gegen keinen gehosteten Anbieter".
Not touched (controller): the unit-3 status row, P-PG "folgt mit der Endprüfung", docs I-4.

## Gates (once, at the end, at f08ca34)

```
uv run ruff check .                                  All checks passed!
uv run ruff format --check .                         108 files already formatted
uv run pyright                                       0 errors, 0 warnings, 0 informations
uv run lint-imports                                  Contracts: 8 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing        1267 passed in 213.64s; TOTAL 98%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                                     rc 0; html build succeeded; vale 0 errors, 0 warnings, 0 suggestions in 38 files; linkcheck build succeeded
uv run pip-audit --skip-editable                     No known vulnerabilities found
```

Coverage left open in the new code: `core/redact.py:283`, the `return None` of `_erasure_of` for an `inputs` entry without an integer event (only reachable by a malformed call, which `verify` reports).

## Not fixed

Nothing in scope left open. Docs I-4 (shipping the ledger, the status row after the merge) is the controller's.
