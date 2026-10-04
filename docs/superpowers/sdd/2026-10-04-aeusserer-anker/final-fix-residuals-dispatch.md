The re-review of your fix wave says: every item addressed, ready for the pull request. It leaves three Minor findings and one false sentence the wave itself had pointed at. The controller rules that all four are closed now, in one small commit, rather than carried — three of them are claims that say more than is true, and one is an assurance without a test.

The re-review, for the exact wording (section `### New breakage in the fix diff`, Minor 1 to 3, and *Bewertung der vier Punkte des Umsetzers*, point 2):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-re-review.md`

Work in `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker`, as before. BASE is `059ccbd`. One new commit; no amend; no push; stage by name.

## The four

1. **`src/previously/storage/postgres.py`, the docstring of `snapshot()`, and `docs/explanation/concurrency.md` around line 48: "a read-only transaction never has a serialization conflict".** PostgreSQL's documentation says that in its section on Repeatable Read; under Serializable a read-only transaction that is not deferrable can still fail. Both sentences have to name the level: a read-only transaction at `REPEATABLE READ`. On the page this matters twice over, because the sentence stands two paragraphs below the one about `SERIALIZABLE`.

2. **`src/previously/core/anchor.py`, the length check: "the id has more than 19 digits"** is also what a field without a single digit gets (measured by the reviewer with a 21-letter field). Keep the check where it is — before anything is echoed, so that no long field of any kind comes back in a message — and make the sentence true of every field it refuses: it is longer than 19 characters, longer than any event `id`. The parametrized case follows the wording; add a second case beside it, a long field that is not digits, with the same expectation and the same bound on the message's length. Mutation as before (the check removed): the digit case fails with `ValueError`; say what the non-digit case does under the mutation, whatever it is. If `docs/reference/cli.md` says "of at most 19 digits", that sentence stays true and stays.

3. **No test holds that `snapshot()` translates the storage errors.** `verify` and `anchor` read through `snapshot()`; the existing tests for the two sentences drive `log` and `begin()`. A `snapshot()` that opened its engine directly, past the shared helper, would leave every gate green and bring back a traceback with exit code 1 — the code of a finding — for `verify` against a server that is down. Fold it into the two existing tests in `tests/test_cli.py` (`test_an_unreachable_server_shows_one_sentence`, `test_a_missing_table_shows_one_sentence`): the same sentence and exit code `2` for `verify` as well, so that the collected count does not move. Mutation: `snapshot()` opens `self._snapshot_engine.begin()` directly, without the helper → both tests red; restore, green. Each docstring you touch says why `verify` is in it: it reads through a different entrance to the storage than `log` does.

4. **`src/previously/cli.py`, the comment in `_cmd_log`** (around lines 237 to 240) says that for `show`, event and units belong in the same snapshot. `_cmd_show` reads them under `begin()`, in two statements, which under `READ COMMITTED` are two snapshots. Fix the comment, not `show`: it shows one state because an event and its units commit together and are never rewritten afterwards — check that against `insert_event` before you write it — and say that this is the reason, not a snapshot. Do not move `show` to `snapshot()`: nothing observable would tell the difference, and an assurance no test can observe is a comment.

## Then

- The collected count stays at 270 unless item 2's second case is a new parametrized case — it is, so measure: `uv run pytest --collect-only -q -p no:randomly | tail -1`. If it moved, the tutorial's test block is retyped from a real green run, without the `rootdir:` line, in this commit.
- All six gates, each run separately, each closing line in the report:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- Commit, subject `fix: four sentences that said more than is true, and one test for the snapshot's errors` or one that fits better; a body that names the four; trailer `Assisted-By: Claude <the model you are> <noreply@anthropic.com>`.

## Report

Append a section `## Residuals after the re-review` to
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/final-fix-report.md`: per item what changed, the two mutations with red and green, the measured count, the six closing lines.

Then reply with ONLY (under 12 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
- Commit (short SHA + subject)
- One-line gate summary (pytest count, coverage, Vale files)
- Concerns, one line each
- The report file path
