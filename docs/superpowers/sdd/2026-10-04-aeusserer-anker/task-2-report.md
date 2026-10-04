# Task 2 report — the command line: `anchor`, `verify --anchors [--exact]`

**Status:** DONE_WITH_CONCERNS (concerns are outside this task's six files; see the end)
**Commit:** `2637c8e feat: anchor, and verify --anchors` on `worktree-aeusserer-anker`, parent `4d1720a`.

## What was implemented

- `src/previously/cli.py`: `_read_anchors(source)` (file with `utf-8-sig`, or stdin for `-`; `OSError` and `UnicodeDecodeError` become `InvalidPayload`); `_cmd_verify` rewritten to the brief's body (order: `--exact` without `--anchors` check, then reading anchors, then `_storage()`, per resolution 1); the new `_cmd_anchor`; the `verify` parser with `--anchors FILE` and `--exact`; the `anchor` parser; `"anchor": _cmd_anchor` after `"verify"` in `commands`. Import of `verify` replaced by `examine` (nothing else in `cli.py` used `verify`); `format_anchor`, `parse_anchors` imported; `Anchor` under `TYPE_CHECKING`. Both standard-error sentences are literals inside the `print` call (resolution 2).
- Two comments in `main` restated: the `C901` comment (see measurement below) and "one of the eight keys".
- `tests/test_cli.py`: `io`, `re`, `sys` imported beside `pytest`; `from typing import TYPE_CHECKING` plus `if TYPE_CHECKING: import pathlib` (resolution 6); the brief's nine test functions (twelve test cases) appended verbatim.
- `tests/test_docs_references.py`: `_quoted_notices` replaced by `_quoted_block(page, after)` with the readable assertion; `_finding_patterns` added; the second half of `test_the_reference_quotes_what_the_code_actually_prints` replaced by the brief's block. Docstring of that test restated (four standard-error sentences in three blocks, three findings, the readable failure, page-to-code direction only). Docstring of `test_no_program_output_cites_a_specification` restated from "nineteen" to the measured twenty-four.
- `pyproject.toml`: `T201` comment carries twenty-four, history continued by one sentence.
- `docs/reference/cli.md`: eight subcommands; exit-code rows for `verify` (rewritten) and `anchor` (new) with the brief's wording; `## verify` rewritten (argument table, anchor-line and file format, input errors, what "holds"/`--exact` check, the three findings block, the three success lines as a table, the standard-error hint block); `## anchor` new after `verify` (no arguments, the `<id> <hash>` line, findings and no line, the empty-log block). The three contractual introductory sentences are present verbatim; `Two notices go to standard error` unchanged. Written under `plone-doc-style:author`, reference quadrant; the reason is a `{ref}` to `external-anchor`.
- `docs/tutorials/record-your-first-event.md`: only the test-run block, retyped from a real run without `rootdir:` (resolution 7). The `verify` block above it was not touched.

## RED and GREEN

RED, `uv run pytest tests/test_cli.py -q -p no:randomly -k "anchor or exact"` before any change to `cli.py`:

```
12 failed, 35 deselected in 7.96s
```

All twelve via `SystemExit: 2` from argparse (`invalid choice: 'anchor'` / unknown `--anchors`/`--exact`) except `test_verify_without_an_anchor_says_what_it_does_not_attest`, which fails on the missing hint in `err`.

GREEN, `uv run pytest tests/test_cli.py -q -p no:randomly`:

```
47 passed in 14.21s
```

The two existing `verify` tests stayed green unchanged; neither reads `stderr`.

## Mutations of step 7

Each run with `uv run pytest tests/test_docs_references.py -q -p no:randomly`; `cli.md` restored from a byte copy (`cmp` confirmed), `core/verify.py` with `git checkout --` (it was clean before). The permission system did not refuse any of them.

| Mutation | Result | Message |
|---|---|---|
| `cli.md` hint: `unchanged` → `unaltered` | `1 failed, 4 passed in 0.17s` | `cli.md quotes 'no anchor given: verify attests that the log is unaltered, not that it is complete; see `previously anchor`' on standard error and no message in cli.py says that. ...` |
| `cli.md` second finding: `missing` → `absent` | `1 failed, 4 passed in 0.16s` | `cli.md quotes the finding 'anchored event is absent (the log ends at 40)' and core/verify.py produces no such reason. ...` |
| `core/verify.py`: `"hash does not match the anchor"` → `"hash differs from the anchor"` (run with `tests/test_docs_references.py tests/test_verify.py`) | `4 failed, 26 passed in 7.12s` | the quotation test (`cli.md quotes the finding 'hash does not match the anchor' and core/verify.py produces no such reason.`) **and** three in `test_verify.py`: `test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor`, `test_two_lines_for_one_position_are_both_checked`, `test_anchors_are_checked_across_a_batch_boundary` |
| `cli.md`: `Three findings come from the anchors:` → `The anchors produce three findings:` | `1 failed, 4 passed in 0.15s` | `AssertionError: cli.md no longer carries the sentence 'Three findings come from the anchors'` — readable, no `IndexError` |

Controls: without mutation `5 passed in 0.12s`; with the `chronicle` block's `projection is 12 events behind` → `7 events behind` (confirmed applied, 1 match), `5 passed in 0.12s`. After restoring: `tests/test_docs_references.py tests/test_verify.py` → `30 passed in 7.00s`.

## The two measurements

Print count:

```
$ uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | tail -3
Found 24 errors.
No fixes available (24 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

Note: the dispatch's `tail -1` shows only the "No fixes available" line; the count is on the line above. `grep -c "print(" src/previously/cli.py` agrees: 24 (19 + 2 more in `verify` + 3 in `anchor`).

`C901`:

```
$ uv run ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py
C901 `_read_anchors` is too complex (4 > 1)
C901 `_cmd_verify` is too complex (5 > 1)
C901 `_cmd_anchor` is too complex (4 > 1)
C901 `main` is too complex (2 > 1)
(and eleven other functions; Found 15 errors.)
```

`main` with the table: 2. Values for the three new functions match the dispatch's pre-measurement (4, 5, 4). The comment now says what was measured (table at 2, after `anchor` arrived), what is read off the 2026-10-04 series and not re-measured (the chain would stand at 10 with eight commands, passing; a ninth would break the gate). It no longer says "two branches of headroom", which was true for seven commands only.

## The six gates (closing lines, final tree)

```
uv run ruff check .                      -> All checks passed!
uv run ruff format --check .             -> 50 files already formatted
uv run pyright                           -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                      -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                         -> ============================= 263 passed in 23.97s =============================
                                            (Total coverage: 97.64%; cli.py 200 stmts, 0 miss, 100%)
make -C docs html                        -> build succeeded.
make -C docs vale                        -> ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                   -> build succeeded.
```

263 passed, as predicted (251 + 12).

## Files changed

- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/src/previously/cli.py`
- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/tests/test_cli.py`
- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/tests/test_docs_references.py`
- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/docs/reference/cli.md`
- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/pyproject.toml`
- `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/docs/tutorials/record-your-first-event.md`

Nothing else was modified; `git status --short` was clean after the commit apart from this report.

## Deviations

1. `ruff format` joined the brief's two-line `raise InvalidPayload(f"cannot read the anchor file ...")` into one line (fits within the line length). Content unchanged.
2. Step 5's `tail -1` returns the fixes line, not the count; the count was read from the line above (see measurement).
3. The tutorial block: the first full run failed only on `test_docs_typed_output` (page claimed 251). I set the `N passed` figure to 263, ran `uv run pytest` again (green, 263 passed, seed 546515917), and typed **that** run's output whole, minus `rootdir:`. Every line in the block is from that one run.
4. In `test_the_reference_quotes_what_the_code_actually_prints`, the brief's block rebinds `page` (first `hash-format.md`, then `cli.md`). Kept as the brief has it; pyright is fine with it.
5. Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>` (the model I run as), per resolution 10.

## Concerns

- `docs/how-to/verify-the-chain.md` line 8 still says "It takes no arguments." about `verify`, which is now false. Not in this task's file list; Task 3 (how-to guides) has to pick it up.
- The `verify` block in the tutorial now shows one line fewer than a real run (the hint on standard error), as the dispatch anticipated; Task 3 retypes it.
- The findings check goes page to code only: a new reason in `core/verify.py` that `cli.md` does not quote is not noticed. Stated in the test's docstring; not a regression, but the reviewer should know the direction.
- `cli.md` says the anchor file accepts "Unix or Windows line ends" and "with or without a byte order mark": covered by `test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read`. It says `verify` prints nothing to standard output on an input error: covered by `test_a_broken_anchor_file_is_an_input_error` and `test_exact_without_anchors_is_an_input_error`. "`0` for an empty log" in `the log ends at` comes from `_closing_findings` (`tip_id = 0 if tip is None`) and has no CLI test of its own.

## Fix round 1

**Commit:** `81992f9 fix: standard input is read the way a file is`. It is a new commit on top of `2637c8e`; nothing was amended.

### Per finding

- **Important 1 (`--anchors -`).** `_read_anchors` now has the body from ruling T2-a word for word, plus `import io` in `cli.py`. Both sources are read as bytes, decoded once with `utf-8-sig` inside one `try`, and parsed after the `try` from `io.StringIO(text, newline=None)`.
  - The docstring is rewritten. It says that both sources are read alike, that standard input is not decoded with the terminal's settings, and why exit code 1 would be wrong.
  - It also says why `StringIO(newline=None)` and not `splitlines()`. Measured in a scratch script: `StringIO` splits `"a b\x0cc\r\nd\re f\x85g\n"` into `['a b\x0cc\n', 'd\n', 'e f\x85g\n']`, while `splitlines()` gives six pieces.
  - Complexity of `_read_anchors` is still 4. The file messages are unchanged.
- **Tests (`tests/test_cli.py`).**
  - `test_verify_reads_the_anchors_from_standard_input` now feeds bytes through `io.TextIOWrapper(io.BytesIO(...))`.
  - New: `test_a_byte_order_mark_and_windows_line_ends_on_standard_input_are_read`, which needs the database.
  - New: `test_bytes_that_are_not_utf8_on_standard_input_are_an_input_error`, which needs no database. Its docstring says why exit code 1 would be wrong.
- **Page, `docs/reference/cli.md`.** The input paragraph now names both sources: "The anchor lines come from the file named by `--anchors`, or from standard input for `-`. Both sources are read the same way: …". It also says "Input without a single anchor line … input that isn't UTF-8 text". I re-read every sentence against the code.
- **Minor 1.** The sentence about a repeated `id` is now two facts:
  - each line is compared with the event's `hash`, and each line that doesn't match gives its own finding;
  - a missing event gives one finding for its `id`, however many lines name it.

  Checked against `core/verify.py`: `pending.pop(row.id, ())` loops over the hashes, and `sorted(pending)` loops over the ids.
- **Minor 2 (ruling T2-c).** `line.partition(": ")`, then `re.fullmatch(r"FINDING [0-9]+", prefix)`, with a message that names the line. The comment beside it says that the form is written into this test, and that the other end is held by `test_verify_reports_a_deleted_tip_against_the_anchor` and `test_anchor_prints_the_tip_and_verify_holds_it` in `tests/test_cli.py`. Both compare whole finding lines exactly.
- **Minor 3.** The docstring now states the page-to-code limit for both halves: the reasons in `core/verify.py`, and a new `print(..., file=sys.stderr)` in `cli.py`.

### Mutations

Each mutation was made in the tree. `cli.py` and `cli.md` were restored from byte copies, and `cmp` confirmed the restore.

| Mutation | Turned red | Stayed green |
|---|---|---|
| `raw.decode("utf-8-sig")` → `raw.decode("utf-8")` | `test_a_byte_order_mark_and_windows_line_ends_on_standard_input_are_read`, `test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read` (`2 failed, 2 passed, 45 deselected`) | `test_verify_reads_the_anchors_from_standard_input`, `test_bytes_that_are_not_utf8_on_standard_input_are_an_input_error` |
| `if source == "-": return parse_anchors(sys.stdin)` ahead of the `try` | `test_a_byte_order_mark_and_windows_line_ends_on_standard_input_are_read`, `test_bytes_that_are_not_utf8_on_standard_input_are_an_input_error` (with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`) (`2 failed, 2 passed`) | `test_verify_reads_the_anchors_from_standard_input`, plus the file BOM test |
| `cli.md`: `FINDING 42: hash does not match the anchor` → `FINDINGS 42: …` | quotation test, `1 failed, 4 passed`: `cli.md quotes the finding line 'FINDINGS 42: hash does not match the anchor', and its prefix is not `FINDING <id>: `, which is what cli.py prints before a reason.` | without the mutation: `5 passed` |

Every row came out as the dispatch's table said.

### By hand

```
$ printf '\xff\xfe junk\n' | uv run previously verify --anchors - ; echo "exit=$?"
Error: standard input is not UTF-8 text
exit=2
$ printf '\xef\xbb\xbf# c\n' | uv run previously verify --anchors - ; echo "exit=$?"
Error: the anchor file holds no anchor
exit=2
```

### Measurements

- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected in 0.17s`.
- Print count: `Found 24 errors.`, unchanged, so `pyproject.toml` was not touched.
- The tutorial's test-run block was retyped from a real green run (seed 1404143297, `265 passed in 23.20s`), without `rootdir:`.

### Six gates (final tree)

```
uv run ruff check .                      -> All checks passed!
uv run ruff format --check .             -> 50 files already formatted
uv run pyright                           -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                      -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                         -> ============================= 265 passed in 22.50s =============================
                                            (Total coverage: 97.65%; cli.py 204 stmts, 0 miss)
make -C docs html                        -> build succeeded.
make -C docs vale                        -> ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                   -> build succeeded.
```

The first `vale` run failed with `cli.md 76:10 Microsoft.Contractions` on "An event that is missing". I reworded it to "A missing event", then reran `html`, `vale`, `linkcheck` and the pytest gate on the final tree. The results are the lines above.

### Deviations and concerns

- No deviation from the ruled body or the commit message.
- Concern: for `-`, the core's message for input without an anchor still reads `the anchor file holds no anchor` (`core/anchor.py`). The dispatch expected exactly that sentence. Still, "anchor file" is slightly off for a pipe, and it lives in Task 1's code, which is outside this fix.
- Still open from round 0: `docs/how-to/verify-the-chain.md:8` says that `verify` "takes no arguments", which is for Task 3.
