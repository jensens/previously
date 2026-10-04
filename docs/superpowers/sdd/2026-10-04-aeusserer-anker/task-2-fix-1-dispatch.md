Task 2, fix round 1. The task review found one Important finding and three Minor ones. The Important one is a defect of the brief, not of your work: the body the plan gave you for `_read_anchors` left the standard-input branch outside the `try` and outside `utf-8-sig`, and you were told to use it verbatim.

The full review, for the exact wording of each finding (section `### Issues`):
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-review.md`

Work in `/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker`, as before. FIX_BASE is `2637c8e`. Make one new commit; do not amend.

## What to fix

### 1. Important 1 — `--anchors -` has to read standard input the way a file is read

Measured by the reviewer on the command line: bytes that are not UTF-8 on standard input end in a `UnicodeDecodeError` traceback and exit code 1 — and exit code 1 means "a finding" to the cron job that runs this, so an input error is reported as tampering. A byte order mark on standard input is refused, because only the file branch uses `utf-8-sig`. Both contradict `docs/reference/cli.md` lines 64 to 69 for `-`, and `-` is the path the specification names for a host where the command runs in a container and the file lives outside.

The controller's ruling (T2-a in the ledger): **both sources are read as bytes and decoded once, in one place, inside one `try`.** Then nothing can be true of a file and false of standard input. This body was measured in a scratch file before it was handed to you — plain input, a byte order mark with Windows line ends, bytes that are not UTF-8, empty input, each from a file and from standard input; a missing file and a directory; complexity 4, as before:

```python
def _read_anchors(source: str) -> tuple[Anchor, ...]:
    name = "standard input" if source == "-" else f"the anchor file {source!r}"
    try:
        if source == "-":
            raw = sys.stdin.buffer.read()
        else:
            with open(source, "rb") as handle:
                raw = handle.read()
        text = raw.decode("utf-8-sig")
    except OSError as error:
        raise InvalidPayload(f"cannot read {name}: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise InvalidPayload(f"{name} is not UTF-8 text") from error
    return parse_anchors(io.StringIO(text, newline=None))
```

Three things about it that are measured, so that the docstring you write can say them:

- `io.StringIO(text, newline=None)` yields lines the way a file opened in text mode does: `\r\n` and `\r` become `\n`, and nothing else is a line end (`"a b\x0cc\n"` stays one line). `str.splitlines()` would also break on those other characters, and one bad line would then be reported under two line numbers; do not use it.
- The messages for a file are unchanged word for word (`cannot read the anchor file '<path>': <strerror>`, `the anchor file '<path>' is not UTF-8 text`), so the existing tests stay as they are. For `-` they read `cannot read standard input: …` and `standard input is not UTF-8 text`.
- The parser now runs after the `try`, so an `InvalidPayload` it raises never passes through these two `except` clauses.

If you find a reason to build it differently, measure and say so; the behavior is what is ruled, not the lines. Rewrite the function's docstring for what it does now — it still says "a file that is no file".

**Tests** in `tests/test_cli.py`. Standard input has to arrive as bytes, the way a pipe delivers it: `io.TextIOWrapper(io.BytesIO(data))` has a `.buffer`, `io.StringIO` has none.

- `test_verify_reads_the_anchors_from_standard_input`: supply the line as bytes. It stays the good case and becomes the control for the mutation below.
- New: a byte order mark and Windows line ends on standard input are read, and the anchors hold — the `-` twin of `test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read`.
- New: bytes that are not UTF-8 on standard input are an input error — exit code 2, `Error: standard input is not UTF-8 text` on standard error, nothing on standard output. No database needed for it, like `test_exact_without_anchors_is_an_input_error`, and say in the docstring why that matters: exit code 1 would tell a scheduled job that the log was tampered with.

Each docstring gives its reason first; if you cite the plan's label, it is `review focus 1` or `review focus 2` `of the 2026-10-04 external-anchor plan`.

**Mutations**, in the tree (allowed, as before; restore with `git checkout -- <file>` or from a byte copy, and confirm the tree is as you left it):

| Mutation | Must turn red | Must stay green |
|---|---|---|
| `raw.decode("utf-8-sig")` → `raw.decode("utf-8")` | both byte-order-mark tests, file and standard input | the plain standard-input test; the not-UTF-8 test |
| the `-` branch back to what it was: `if source == "-": return parse_anchors(sys.stdin)` ahead of the `try` | the not-UTF-8 test on standard input, and the byte-order-mark test on standard input | the plain standard-input test |

If a row does not come out as the table says, the measurement wins: report what happened.

**By hand, once, and put the two lines of output into the report** — no database is needed, the error comes before it is asked for:

```
printf '\xff\xfe junk\n' | uv run previously verify --anchors - ; echo "exit=$?"
printf '\xef\xbb\xbf# c\n' | uv run previously verify --anchors - ; echo "exit=$?"
```

Expected: `Error: standard input is not UTF-8 text` and `exit=2`; then the sentence for input without an anchor and `exit=2`.

**The page.** `docs/reference/cli.md`, the paragraph from "The anchor file is read as UTF-8 text" to "returns 2": reword it so that every sentence is true of both sources, and re-read each one against the code after you have. Reference quadrant: facts, no reasons.

### 2. Minor 1 — `docs/reference/cli.md:73`

"A file may name the same `id` on several lines, and each line is checked." True for the comparison of hashes; a missing event is reported once per `id`, not once per line (`_closing_findings` iterates the ids). Say both, as two facts. Check the sentence you write against `core/verify.py`.

### 3. Minor 2 — the quoted finding lines lose their prefix unchecked

`tests/test_docs_references.py`, where the test does `line.split(": ", 1)[1]`: the prefix `FINDING <id>: ` is thrown away, so a page that quotes `FINDINGS 42: …` stays green. Ruling T2-c: hold the prefix too — split it off, assert that it has the form `FINDING <digits>`, with a message that names the line. The code's side of that form is pinned by the exact comparisons in `tests/test_cli.py`; say so in the comment, because the form is then written down in the test rather than read from `cli.py`, and a reader should know which test holds the other end.

Mutation: on the page, `FINDING 42: hash does not match the anchor` → `FINDINGS 42: hash does not match the anchor` must turn the quotation test red with that message; unmutated it is green.

### 4. Minor 3 — the docstring states the limit for the findings only

`tests/test_docs_references.py`, the docstring of `test_the_reference_quotes_what_the_code_actually_prints`: the check runs from the page to the code for the notices on standard error as well — a new `print(..., file=sys.stderr)` in `cli.py` that the page does not quote goes unnoticed. Say it for both.

## Then

- The tutorial's test-run block again, last, from a real green `uv run pytest` run without the `rootdir:` line: the count moves by the tests you add. Measure it (`uv run pytest --collect-only -q -p no:randomly | tail -1`); 265 is a prediction.
- The print count does not move (no new `print`); confirm with `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found` and leave `pyproject.toml` alone if it still says 24.
- All six gates, each run separately, each closing line in the report:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `git status --short`, then stage by name — only what you changed among `src/previously/cli.py`, `tests/test_cli.py`, `tests/test_docs_references.py`, `docs/reference/cli.md`, `docs/tutorials/record-your-first-event.md` — and commit:

  ```
  fix: standard input is read the way a file is

  `verify --anchors -` decoded standard input with the terminal's settings
  and outside the handler that turns an unreadable file into an input
  error. Bytes that are not UTF-8 ended in a traceback and exit code 1,
  which a scheduled job reads as a finding; a byte order mark was refused.
  Both sources are now read as bytes and decoded in one place.

  The reference says of a repeated id what happens for a missing event,
  and the check on its quotations holds the prefix of a finding line too.

  Assisted-By: Claude <the model you are> <noreply@anthropic.com>
  ```

  Adjust the body if what you built differs from it.

## Report

Append a section `## Fix round 1` to
`/home/jensens/ws/jwk/previously/.claude/worktrees/aeusserer-anker/.superpowers/sdd/2026-10-04-aeusserer-anker/task-2-report.md`:
what you changed per finding; the mutation table with what turned red and what stayed green; the two hand-run lines; the measured test count; the six closing lines; deviations and why.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line test summary (count, coverage)
- Concerns and disagreements, one line each
- The report file path
