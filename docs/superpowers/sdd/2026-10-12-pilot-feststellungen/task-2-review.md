# Task 2 review — write path, erasure cascade, verify (482ceb9..69bd77f)

Reviewer: Opus, adversarial, read-only.
Measured on 2026-10-12.
`uv run pytest tests/test_assertions.py tests/test_cascade.py tests/test_verify.py`: 163 passed.
`uv run pyright` on the three changed core modules: 0 errors.
Four probes ran against real PostgreSQL from the scratchpad; they are quoted below.
The 19 mutations were not re-run, because the repo is read-only to me.

## Spec compliance

- ✅ `AssertionRefused`, `write_statements`, `read_threads`, `source_identities`, `assertion_verdict` and `thread_circles` have the signatures the brief names (`core/assertions.py:90`, `:366`, `:108`, `:440`, `:465`, `:497`).
- ✅ One transaction through `retrying`, in this order (`assertions.py:390-423`): lock the sources ascending, read the tip, look up the handle, check the sources, check the references against the fold below the tip plus the batch, then link.
  The brief puts "read the tip" first.
  Locking first is the better order: the tip is read above any redaction the lock waited for. The module docstring (`:13-30`) says so.
- ✅ Decision 5 and ruling F-3 on the write path.
  A second approval, an approval after a rejection, and an approval of an erased or direct version are each refused (`assertions.py:213-223`, `:263-282`).
  So are two approvals of one proposal in one batch (`_View.add`, `:198-206`).
  An approval takes the body, the sources and the author unchanged (`:275-282`), and the form makes it direct (`assertion.py:335`).
- ✅ §3.4: a rejection takes its proposal's sources unchanged (`assertions.py:233`), is direct (form), and cannot reject a direct version (`_proposal`, `:217`).
- ✅ Decision 8: the sources are locked ascending (`:388`, `:394`), and an erased, missing or non-observation source is refused, as is an erased or missing cited unit (`:299-329`).
- ✅ §8 cascade for `redact_event` and `redact_units`.
  The assertions are found and locked in the same ascending round as the calls, with a second read after the lock (`redact.py:195-226`).
  A redaction of the whole assertion is written in the same transaction (`redact.py:292-324`).
  `Redacted.cascaded` lists calls and assertions together, ascending, and `cascaded_assertions` tells them apart (`redact.py:484-487`, `:585-591`).
  The CLI prints `cascaded: assertion <id>` (`cli.py:1320-1322`).
- ⚠️ `redact_blob` and `append_call` have no assertion cascade, although the brief names all three `redact_*` and `append_call`.
  This can be defended from spec §8, which names whole events and units only. More in M-3.
- ✅ `verify` has a branch for `kind == "assertion"` before the action check (`verify.py:433`).
  It checks the form, an assertion that has units, and sources that point forward (`:533-555`).
  It checks `subject`, `approves`, `of` and `replaces` for direction and kind (`:569-607`), and reports F-3 (`:576`, `:602`).
  `reconcile` checks the kind of each source, its cited units, and "assertion stands on an erased source" (`:609-650`).
- ❌ **Ruling F-5 is not implemented.**
  F-5 came after the implementation and is listed here without blame, as I-1.
  `verify` already says nothing about the case. The fold still drops the approval.
- ✅ Decision 7 (`assertions.py:465-485`) and spec §7 (`:497-515`): the policy reads the sources only, and the filter reads the sources plus the actors.
- ✅ Documentation follows: `docs/reference/cli.md`, `docs/how-to/erase-something.md`, and the tutorial block retyped from one run (1816 collected, 1816 passed).

## Strengths

- **The race is closed on both sides, and the tests show it with two connections.**
  - Write first: the erasure waits at the source lock, reads the assertions again, finds the new one and cascades it.
  - Erase first: the write path waits and then reads the source as erased.
  - Each test has a control.
  - I checked the lock order: every locker takes `lock_event` in ascending order. The eraser's second round only adds ids above its first round. Both sides take every lock before taking any chain position. So there is no wait cycle among `write_statements`, `redact_event`, `redact_units`, `append_call` and two concurrent writes.
- **Idempotency holds under concurrency.**
  Probe: four threads confirm one handle with a batch of two at the same moment. In five rounds, every call returned `(3, 4)`, the log held 4 events, and no call raised an error.
  The source lock serializes the calls, and READ COMMITTED lets the second call see the first call's rows.
- **One predicate, `stands_on_erased`, serves both the cascade and `verify`.**
  So the cascade erases exactly what `verify` would otherwise report.
  The `units: null` rule depends on position: only a unit redaction newer than the assertion counts. That rule is consistent in the cascade, in `verify`, and on a repeat erasure that writes nothing (`test_a_unit_erased_before_the_assertion_does_not_take_the_whole_event_with_it`).
- Reading the sources leniently for the cascade means a forged assertion is over-erased, never left standing, and `verify` still reports its form.
- No refusal sentence contains the text of an assertion or an address. The canonical-form error is wrapped without the string it refused (`:360-363`).

## Issues

### Important

**I-1 — Ruling F-5 is missing. The fold drops an approval whose proposal was erased on its own, the whole obligation disappears, and `verify` stays green.**
`src/previously/core/assertion.py:560-567`
- What happens: in `fold`, `proposal = next(... v.id == statement.approves)` is `None` once the proposal is erased, and the approval is skipped with `continue`.
- Probe: write a proposal P, approve it, then `redact_event(P)`.
  ```
  cascaded ()
  threads {}
  verify []
  ```
  A direct obligation that the maintainer approved vanishes from every list, and nothing reports it.
  This is the silent loss that the `_Assertions` docstring says `verify` exists to prevent.
- `verify` (`verify.py:597`) already passes over the erased proposal, so it matches F-5 as it stands.
- Fix:
  - In `fold`, keep a version whose `approves` is in `erased` instead of skipping it. Keep the existing checks for a proposal that stands.
  - Add a test: erasing the proposal alone leaves the approval as the direct winner, and `verify` returns `[]`.
  - Measure it with a mutation that reverts the change and goes red, plus a control in which the proposal is erased through a source, so that the approval goes with it.

**I-2 — The core writes a direct version by a `model:` author without `approves`, and that version outranks the maintainer.**
`src/previously/core/assertion.py:327-338` (`_version_problem`), reached through `assertions.py:332-348`
- Probe: write a human direct version, then `obligation(subject=human, author=model_author("claude-code"), responsibility=DIRECT, what="something else")`.
  ```
  winner 4 model:claude-code direct
  verify []
  ```
- Why it matters: spec §6 allows exactly one way for a model-authored version to be direct, and that way is an approval.
  Today the only guard is that Task 5's MCP tool sets `open` itself.
  If Task 5 has a bug, or a row is forged, a proposal becomes a newer direct version that beats the operator's, and `verify` is green.
  This is precisely the "lets a proposal outrank the maintainer" defect.
- Fix: add a form rule in `_version_problem`, so that the write path refuses it and `verify` reports it:
  ```python
  if author.startswith(MODEL_PREFIX) and responsibility == DIRECT and approves is None:
      return "a version by a model is direct only as an approval"
  ```
  - Leave rejections out: spec §6 has `write_reject` writing a direct rejection by `model:<client>`.
  - Add a test with a mutation, plus a control: a `model:` approval is accepted.

### Minor

**M-1 — A replayed handle after its assertion was erased on its own writes the assertion again.**
`assertions.py:402-409`
- Probe: write a proposal with handle `nonce-1` (id 3), run `redact_event(3)`, then write the same batch again. The result is `(5,)`: a new write.
- The same mechanism means that if one assertion of a batch is erased, a replay returns a subset of the ids.
- The handle lives in the payload, and the erasure takes the payload, so "confirming twice writes nothing" (spec §6.1) stops holding once the operator has erased the result.
- The window is short, at most ten minutes of handle lifetime, and the client holds the text anyway. That is why this is Minor.
- Options, for a ruling:
  - Accept it and say so in the docstring.
  - Carry the nonce as the source key of the first assertion: `source_key` survives erasure, and `lookup` already exists. This deviates from the brief's `key=None`.

**M-2 — The same handle with different statements returns the old ids.**
- Probe: write one proposal with `nonce-2`, then a batch of two different proposals with `nonce-2`. The result is `(3,)`.
- That is correct only because Task 5 binds the nonce to the digest of the payloads through the HMAC.
- Fix: the `write_statements` docstring should say that the caller guarantees one handle means one content, so that Task 5 does not lean on the core for it.

**M-3 — The deviation from the brief on `redact_blob` and `append_call` is reasonable, but it is not recorded as a ruling.**
- Spec §8 names whole events and units.
- An assertion cannot name a blob.
- MCP serves only attachment names, never blob content (`mcp_server/read.py:218`, `render.py:118`).
- `append_call` writes calls, which no assertion rests on.
- Fix: a ruling in the ledger. Today it appears only as the implementer's own decision in the Task 2 line.

**M-4 — Comments and pages that fell behind the code:**
- `redact.py:443` still says that `redact units` "locks only its target and the calls". It now locks the assertions on the event as well.
- `redact.py:59` says "any unit of an event it cites whole" without "erased after the assertion". `stands_on_erased` and `docs/reference/cli.md` both include that condition.
- `docs/how-to/erase-something.md:165` says "An obligation or a decision", but rejections are cascaded too. "An assertion" covers all three.

**M-5 — `verify` does not hold an approval's or a rejection's sources against its proposal's (implementer concern 2).**
- Only the write path enforces this (`assertions.py:233`, `:275-282`).
- A forged approval or rejection that leaves out one of its proposal's sources survives the erasure of that source while carrying the proposal's content or a `reason`. `verify` reports nothing.
- Fix: keep the sources of each open version in `_Joined`. Then report a difference while the proposal stands; F-5 means there is nothing to compare once it is erased. Comparing the body is optional.
- A related forged-only gap: a `subject` that names an earlier erased assertion that was never a thread name, such as a rejection or a later version, is not reported (`verify.py:584`).

**M-6 — `assertion_verdict` returns the last decision when every decision chooses (`assertions.py:480-485`).**
- That follows decision 7 to the letter.
- `decide` adds a `source:` scope per source (`decide.py:251-252`), so the `rule_keys` and constraints of the other sources' decisions are lost.
- This matters for Task 4 if the access log takes its rule ids from this decision.
- Fix: none in Task 2. Hand it to Task 4.

### Judged and found sound (no issue)

- **The `units: null` id rule.**
  The cascade and `verify` agree on it, including after a repeat erasure that writes nothing.
  The stricter alternative would refuse a whole-event source once any of its units is erased, and drop the position test.
  It would not close the remaining leak: text a writer read before the erasure and cites after it.
  That leak exists in the same form for an explicit citation of the wrong unit, and the log cannot see either one.
  Over-erasure stays the direction of every doubt.
- **Rejecting a direct version** is refused. An approval with `open` is a form fault.
- **Legitimate histories that `verify` leaves green:**
  - a repeated erasure;
  - an erased proposal with its approval standing (F-5, already silent);
  - a rejection of a proposal that was erased on its own;
  - an erased first version (F-2);
  - an erased approval followed by a fresh approval.
  The fold and `verify` agree on each of these.
- **Implementer concern 3**, that every redaction reads all assertions twice: the same holds for `_calls`, and the plan's final review measures it.
- **Implementer concern 5**, the § citations removed: right, because the specification is not frozen.
  The one ruling citation, "ruling F-3", names its plan and has its reason beside it.
  It resolves once Task 6 ships the ledger to `docs/superpowers/sdd/` (plan, step 2).

## Assessment

**Needs fixes.**
- I-1 (F-5) is required by the ruling.
- I-2 is the risk this task was briefed against: a proposal outranking the maintainer, with `verify` green.
- Both fixes are a few lines in `core/assertion.py`, which the fix round touches anyway.
- M-4 is a few edits to comments and one page; fold it into the same round.
- M-1, M-3 and M-5 need a ruling or a sentence, not code, unless the controller decides otherwise.
