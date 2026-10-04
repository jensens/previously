# Task 1 report: the core — `Anchor`, reading and writing, `examine`

Status: DONE_WITH_CONCERNS. The main concern is that the four mutations of step 9 were **not measured** (see below).

Commit: `11de3f6 feat: examine — the chain, and the anchors against it` on `worktree-aeusserer-anker`, parent `edcb9e0`.

## What was implemented

- `Anchor(id: int, hash: bytes)`, a frozen dataclass in `src/previously/contract/types.py` after `RawEvent`, using the brief's docstring verbatim.
- `src/previously/core/anchor.py` (new), with `format_anchor` and `parse_anchors` exactly as in the brief, except for one ruff-format reflow (see deviations).
- `src/previously/core/verify.py`:
  - adds `Examination(findings, tip)`.
  - renames `verify` to `examine` with the brief's signature and docstring and the `exact`-without-anchors refusal. It sets up `pending`, turns `return findings` into `break`, checks pending anchors per row, and sets `tip` after `checked += 1`.
  - keeps a new `verify` with its old signature, delegating to `examine`.
  - leaves every comment in the old body untouched, including the one about the single transaction.
- `tests/test_anchor.py` (new) and the eight DB tests and two helpers appended to `tests/test_verify.py`, all verbatim from the brief.
- `docs/explanation/hash-chain.md` replaces the "closes all three at once" sentence with a pointer to the new section. It also adds a new section `(external-anchor)=` / `## The external anchor` with the eight required points in order.
- `docs/tutorials/record-your-first-event.md` has its test-run block retyped from a real `uv run pytest` run, without the `rootdir:` line. Nothing else in the tutorial was touched, and the existing sentence below the block already says the `rootdir:` line is left out.

## Baseline

`uv sync --locked --all-extras`, then `uv run pytest --collect-only -q -p no:randomly | tail -1` gives `232 tests collected in 0.17s`, which matches the brief.

## RED runs

- `uv run pytest tests/test_anchor.py -q -p no:randomly` fails at collection with `E   ImportError: cannot import name 'Anchor' from 'previously.contract.types'` and ends with `1 error in 0.18s`.
- `uv run pytest tests/test_verify.py -q -p no:randomly` fails at collection with `E   ImportError: cannot import name 'examine' from 'previously.core.verify'` and ends with `1 error in 0.20s`.

## GREEN runs

- `uv run pytest tests/test_anchor.py -q -p no:randomly` gives `11 passed in 0.09s`.
- `uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly` gives `36 passed in 7.01s`. That is 25 in `test_verify.py` (17 before plus 8 new) and 11 in `test_anchor.py`.
- After the C901 refactor (see deviations), the same command gives `36 passed in 6.92s`.

## The four mutations: NOT MEASURED

The first mutation was an Edit that replaced `if anchored != row.hash:` with `if False:` in `verify.py`. The Claude Code auto-mode permission classifier denied it ("Security Test Removal"). The denial says not to pursue the same outcome through another tool or path, so I did not attempt any of the four mutations by other means: no sed, no copy in the scratchpad, no git-stash trick.

The test run that followed the denied edit (`36 passed in 6.90s`) ran on **unmutated** code. It is effectively the green control and nothing more.

So:

| Mutation | Expected red (brief) | Measured |
|---|---|---|
| `if anchored != row.hash:` becomes `if False:` | rewrite test, two-lines test, batch test | not measured (edit denied) |
| remove the `anchored event is missing` block | deleted-tip test, empty-log test | not measured |
| `if exact:` becomes `if False:` | appended-event test | not measured |
| remove `len(fields) != 2` in `parse_anchors` | two cases of the parametrized test | not measured |

Green control without a mutation: `36 passed` (above).

To unblock this, the user (or the controller, with the user's permission) has to allow the temporary source edits, or run the four mutations by hand. Note for mutation 2: that block now lives in `_closing_findings` in `verify.py` (see deviations), not at the end of `examine`.

## Numbers on the page and where they come from

- "three events with the tip deleted", "event 3", and `anchored event is missing (the log ends at 2)` come from `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one` in `tests/test_verify.py`. That test appends three events, asserts `anchor.id == 3`, deletes event 3, and expects `Finding(3, "anchored event is missing (the log ends at 2)")`.
- "closes two of the three" comes from the table: of the three manipulations named in the section above it, deletion below the anchor and rewriting are seen, and appending is not seen by contains. Appending is seen by exact only at rest, which is why the page says "two".
- "four forgeries" is the four rows of the table the brief prescribes.
- That `event_hash` takes the `id` comes from `src/previously/core/hashing.py:144`, `"id": event_id,`.
- That every hash covers its predecessor's through `prev_hash` comes from `event_hash`, which takes `prev_hash` (called in `_check_event` with `prev_hash=row.prev_hash`).
- The tutorial block was retyped from the run with seed `1203233239`: `collected 251 items` and `251 passed in 22.81s`.

## Six gates, closing lines

```
uv run ruff check .                     -> All checks passed!
uv run ruff format --check .            -> 50 files already formatted
uv run pyright                          -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                     -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        -> Required test coverage of 90.0% reached. Total coverage: 97.53%
                                           ============================= 251 passed in 22.40s =============================
make -C docs html                       -> build succeeded. / The HTML pages are in _build/html.
make -C docs vale                       -> ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                  -> build succeeded. (`_build/linkcheck/output.txt` is empty, so nothing is broken)
```

`core/anchor.py` and `core/verify.py` are both at 100% coverage.

## Files changed (seven, staged by name, `git status --short` showed nothing else)

- `src/previously/contract/types.py`
- `src/previously/core/anchor.py` (new)
- `src/previously/core/verify.py`
- `tests/test_anchor.py` (new)
- `tests/test_verify.py`
- `docs/explanation/hash-chain.md`
- `docs/tutorials/record-your-first-event.md`

## Deviations from the brief and dispatch

1. **C901 on `examine` (11 > 10).**
   - Cause: with the brief's body verbatim, `ruff check .` reported `C901 examine is too complex (11 > 10)`.
   - Fix: CLAUDE.md forbids a new suppression (the list stays at five) and says to remove the cause. So I moved the brief's step-5 tail (the missing-anchor findings and the `exact` comparison) into a helper, `_closing_findings(pending, anchors, tip, *, exact) -> list[Finding]`. Its code and comment are the brief's own, and its docstring gives the same reason `_check_event`'s docstring gives for being separate.
   - Effect: `examine` now ends with `findings.extend(_closing_findings(pending, anchors, tip, exact=exact))` and `return Examination(tuple(findings), tip)`.
   - What did not change: behavior and finding texts.
2. **ruff format reflows.**
   - The brief's two-line f-string `"...64 hex characters, " "got {len(hash_text)}"` in `anchor.py` became one line, and the message is unchanged.
   - The `findings.append(Finding(...newest anchor...))` call is on one line.
   - The `test_verify.py` import order is ruff's (`Examination` before `examine`, case-sensitive), not the brief's order.
3. **Trailer.** The commit message is the brief's text verbatim, with `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`. CLAUDE.md overrides the harness reminder that asked for `Co-Authored-By`.
4. **The pointer sentence.**
   - In `## What the chain doesn't cover`, the replaced sentence is now "An external anchor closes two of the three, and the next section says which two and why not the third." It is followed by "Without one, the chain speaks for itself alone." That sentence frames the unchanged "So the promise, in full:" block as the promise without an anchor.
   - The new section's promise is introduced as "So the promise, with an anchor, in full:".
5. **The page does not name `previously anchor`, `--anchors` or `--exact`.** Resolution 1 allowed that, but none of the sentences needed it, so the page stays on the concept. It calls the two checks *contains* and *exact*.

## Concerns

- The **mutations are unmeasured**, as described above. Under CLAUDE.md ("An assurance needs a test measured to fail"), this task's assurances are not established until someone runs them.
- **Stale names in kept comments.** Two places in `verify.py` still say `verify` where the function that does the work is now `examine`. One is the docstring of `_check_event` ("because `verify` would otherwise do two things at once"). The other is the batch comment ("and `verify` is the routine that runs over the whole history"). The brief said to keep the body and its comments, so I did not change them. Under "a comment is a claim", the reviewer may want them renamed.
- **Generated files.** The vale gate downloaded the vale binary into `.venv` and synced `.vale-styles/`. Neither showed up in `git status`, so both are ignored.

---

# Fix round 1

Commit: `c7d8b47 fix: the pass is examine, and a label names its plan` on top of `11de3f6`.
It changes four files, staged by name: `src/previously/core/verify.py`, `tests/test_verify.py`, `tests/test_anchor.py` and `docs/explanation/hash-chain.md`.

## Step 9, the mutations

The controller measured them at `11de3f6`, with the maintainer's permission.
See `.superpowers/sdd/2026-10-04-aeusserer-anker/task-1-mutations.md`: M1 turned three tests red, M2 two, M3 one and M4 two, and the control was green.
I did not repeat them.

## Items

- **I1, the review-focus labels.**
  All three docstrings now say what their test pins and why, and keep the label as `review focus N of the 2026-10-04 external-anchor plan`.
  - In `test_anchor.py`, the `²` case is described as the one that pins a non-ASCII digit being refused as a bad id rather than reaching a `ValueError`.
  - The empty-log test uses the controller's reason verbatim in substance: no tip, every anchor missing, and the log ends at 0.
  - The batch test says why it exists: anchors are checked as the pass comes by them, including in later batches.
- **I2, comments that still said `verify`.**
  The `_check_event` docstring and the batch-fetch comment in `verify.py` now say `examine`.
  `verify() -> []` in the `_count_finding` docstring stays, because it quotes a measurement taken when `verify` was the pass.
- **Minor 2, `hash-chain.md`.**
  - "Three manipulations pass, and no change to the code can stop them" now reads "Three manipulations pass the chain, and no change to the chain check can stop them."
  - The pointer sentence now reads "An external anchor closes two of the three up to the newest anchor, and the next section …".
- **Minor 3, the untested *exact* cells.**
  The deleted-tip test and the rewritten-chain test each gain an `exact=True` assertion that expects the same single finding.
  For the deleted tip, the tip is 2 and the newest anchor is 3, so no "continues past" finding is added.
  For the rewritten chain, the tip and the newest anchor are both 2.
- **Minor 5, the control in the test above the newest anchor.**
  Before the deletion, the test asserts that `examine(storage).tip` is not `None` and has id 3.
  After the deletion, it asserts that `examine(storage).tip == anchor`.

## Runs

`uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly` gives `36 passed in 6.87s`.
The count is unchanged, so the tutorial was not retyped.

Six gates, closing lines:

```
uv run ruff check .            -> All checks passed!
uv run ruff format --check .   -> 50 files already formatted
uv run pyright                 -> 0 errors, 0 warnings, 0 informations
uv run lint-imports            -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                               -> Required test coverage of 90.0% reached. Total coverage: 97.53%
                                  ============================= 251 passed in 22.16s =============================
make -C docs html              -> build succeeded.
make -C docs vale              -> ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck         -> build succeeded.
```

## Disagreements

None.
I added one sentence of my own judgment, under I2: I left `verify() -> []` in the `_count_finding` docstring alone, because it is a historical measurement and not a claim about today's code.
