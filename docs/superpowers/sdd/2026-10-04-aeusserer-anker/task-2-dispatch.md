You are implementing Task 2 of the plan "the external anchor" for the project "Previously": the command line — `previously anchor`, `previously verify --anchors FILE [--exact]` — with its tests, the reference page, and the check that holds the reference's quotations against the code.

## Where this fits

Previously is an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). Its hash chain attests that the log is unaltered, not that it is complete. An anchor is the tip `(id, hash)` written down outside the database. Task 1, already on the branch, built the core: the type `Anchor`, `parse_anchors` and `format_anchor`, and `examine`, the one pass that checks the chain and the anchors and returns `Examination(findings, tip)`. Your task puts that behind two commands. Task 3 follows with the how-to guides, README and tutorial. The command line is only the entry point until an MCP server exists: it reads the file and formats, and everything else stays in the core.

## Task description

Read your task brief first — it is your requirements, with the exact values to use verbatim (test code, function bodies, the sentences `cli.md` has to carry, the commit message):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-brief.md`

The brief is in German; everything you write into `src/`, `tests/`, `docs/` (outside `docs/superpowers/`) and `pyproject.toml` is English. Read `CLAUDE.md` in the worktree root once before you start — it is binding. The parts that bite here: the six gates by name; no `# type: ignore`, no mock, no new `# noqa` (the suppression list stays at five); "A comment is a claim" (every number in a comment is measured against the tree — two comments in `cli.py`, one in `pyproject.toml` and one docstring in `tests/test_docs_references.py` carry counts your change makes wrong); "An assurance needs a test measured to fail" (the brief's step 7 lists the mutations); one quadrant per page — `docs/reference/cli.md` is reference: facts and tables, no reasoning; one sentence per line, American English; typed output is a measurement; `Assisted-By:` and never `Co-Authored-By`.

For `cli.md`, invoke the skill `plone-doc-style:author` (exactly that name) for the reference quadrant.

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker` (git worktree, branch `worktree-aeusserer-anker`). Run every command from there. Never touch the parent checkout `/home/jensens/ws/jwk/previously`.

## Interfaces from Task 1 — check them against the tree before you rely on them

- `previously.contract.types.Anchor(id: int, hash: bytes)` — frozen dataclass.
- `previously.core.anchor.parse_anchors(lines: Iterable[str]) -> tuple[Anchor, ...]` — raises `InvalidPayload` naming the line; raises it too for input without a single anchor.
- `previously.core.anchor.format_anchor(anchor) -> str` — `<id> <hash>`, no line end.
- `previously.core.verify.examine(storage, *, anchors=(), exact=False, batch=1000) -> Examination`, with `Examination(findings: tuple[Finding, ...], tip: Anchor | None)`; it raises `InvalidPayload` for `exact=True` without anchors.
- The three finding reasons, produced in `core/verify.py`: `hash does not match the anchor`; `anchored event is missing (the log ends at <tip>)`; `the log continues past the newest anchor (<id>)`.
- The label `(external-anchor)=` on `docs/explanation/hash-chain.md`.

**What Task 1 turned out differently from the plan, and what it leaves you:**

- The part of `examine` that runs after the pass lives in a helper `_closing_findings` in `core/verify.py`, because the single function exceeded `C901`. Two of the three finding texts are produced there. Your extension of the quotation check reads every `Finding(...)` call in the module, so it does not care which function holds them — check that against the file.
- The parser in the core refuses a line that starts with a byte order mark (its `id` is not ASCII digits). That is right for the core, which gets lines; reading the file is yours, and `utf-8-sig` in `_read_anchors` is what makes a file saved with a mark read like one without. The test for it is in your brief.
- **A label numbered per plan names its plan.** Task 1's review found three docstrings that cited "review focus N" bare, one of them nothing but the label. Your brief's docstrings are already corrected: the reason comes first and the label reads `review focus N of the 2026-10-04 external-anchor plan`. Keep that form for anything you add, and never write a docstring that is only a label.
- **Mutations in the tree are allowed.** The permission system refused Task 1's implementer the first mutation as "Security Test Removal"; the maintainer then explicitly allowed measuring in the tree: change one line, run the covering tests, restore the file with `git checkout -- <file>`. Your step 7 has four mutations and a control. If the permission system refuses you all the same, do not look for another route: say so in the report, name the mutation, and the controller measures.
- The functions your brief prescribes were measured for complexity before dispatch: `_read_anchors` 4, `_cmd_verify` 5, `_cmd_anchor` 4, against a threshold of 10.

## Facts from the tree (measured before Task 1; re-check the line numbers)

- `src/previously/cli.py`: `_plural(n, noun)` and `_storage()` exist; `_cmd_verify(_args)` calls `verify(_storage())` and prints `FINDING <id>: <reason>` lines or `chain intact`; the parser for `verify` is the single line `sub.add_parser("verify", help="check the chain")`; the dispatch table `commands` has seven entries; `main` catches `(PreviouslyError, StorageError)` and prints `Error: <message>` to standard error with exit code 2. Two comments in `main` say "seven": one inside the comment that carries the measured `C901` series (seven commands → 9, eight → 10, nine → 11, the table → 2, and `C901` fires strictly above the threshold of 10), one below the table ("one of the seven keys").
- `grep -c "print(" src/previously/cli.py` was 19 before your change; `pyproject.toml` (the comment on the `T201` exemption) and a docstring in `tests/test_docs_references.py` both say "nineteen".
- `tests/test_cli.py` has `_setup(db, monkeypatch)` and `_append(source, external_id, text, occurred_at)`, imports `main` and others from `previously.cli` at the top, one name per line, and has no `TYPE_CHECKING` block yet. Its two existing `verify` tests read standard output and the exit code only.
- `tests/test_docs_references.py` has `_quoted_notices(page)`, `_static_parts(node)`, `_message_patterns(path)` and `_is_the_same_sentence(parts, line)`. The last one matches a quoted line by the message's fixed beginning **and** its fixed end — which is why the finding texts end on fixed text and must not be reworded. `_message_patterns` reads the first positional argument of `print(..., file=sys.stderr)` calls and every returned string literal, from the source; a message held in a constant and printed by name is invisible to it.
- `docs/reference/cli.md`: the opening says "seven subcommands"; the exit-code table has one row per command; `## \`verify\`` is six lines and says "It takes no arguments."; the `chronicle` section has the sentence "Two notices go to standard error" followed by a `text` block with two lines.

## Resolutions

1. **Order inside `_cmd_verify`:** the `--exact`-without-`--anchors` check first, then reading the anchors, then `_storage()`. An input error is reported before the database is asked for; `test_exact_without_anchors_is_an_input_error` runs without a database for that reason.
2. **The two standard-error sentences are literals inside the `print` call**, not constants — see the fact about `_message_patterns` above.
3. **The introductory sentences in `cli.md` are contractual**, because the check finds its blocks by them: `Three findings come from the anchors`, `Without anchors, one notice goes to standard error`, `On an empty log, one notice goes to standard error`. The existing `Two notices go to standard error` stays.
4. **The `C901` comment is measured, not edited.** Run `uv run ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py` after your change, and restate the comment for eight commands: what you measured (the table), what follows from the recorded series (the chain would stand at 10 and still pass, a ninth command would break it), and the date. Do not reconstruct the `if` chain to re-measure it; say that the series is the one measured on 2026-10-04.
5. **The print count is measured**: `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | tail -1`. Put the measured number into `pyproject.toml` and the docstring, with the date, continuing the history that comment already tells.
6. **`pathlib` in `tests/test_cli.py`** is needed for the annotation `tmp_path: pathlib.Path` only; put the import where `ruff` wants it (a `TYPE_CHECKING` block, as `tests/conftest.py` has one).
7. **In the tutorial you change only the test-run block**, retyped from a real `uv run pytest` run without the `rootdir:` line. The `verify` block above it now shows one line too few; leave it — Task 3 retypes the whole session.
8. **`{ref}` labels, never a paragraph sign,** in comments and docstrings; no citation in anything that is printed.
9. **Stage by name.** `git status --short` before `git add`; add only the six files of the brief's commit step. Anything else modified: do not add it, report it.
10. **Trailer:** `Assisted-By: Claude <the model you are> <noreply@anthropic.com>`; if you do not know, `Claude Opus 5`.

## Your job

1. The brief's steps in order: tests first, red, the commands, green, the print count, `cli.md`, the quotation check with its mutations, the tutorial's test block.
2. All six gates, each run separately, each closing line quoted in full in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
   Expected `pytest`: 263 passed — a prediction; count what you have.
3. Commit with the brief's message.
4. Self-review your own diff, then report.

If the brief contradicts the tree, or a mutation does not turn red what the brief names, the measurement wins: say so in the report.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to implement part of the task, and never spawn a reviewer. The controller dispatches a fresh reviewer against your diff after you report.

## When you are in over your head

Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on, what you tried, and what would unblock you.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-report.md`

It contains: what you implemented; the RED and GREEN runs; the mutations of step 7, each with what turned red and the closing line, and the green control; the two measurements (print count, `C901`) with command and output; the six closing lines; files changed; every deviation from the brief or this dispatch and why; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line test summary (count, coverage)
- Concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering tests, append a fix report to the same report file, and reply with the same short contract.
