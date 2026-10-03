# Task 3 report — Tutorial, and the README shrinks

Status: **DONE**
Branch: `worktree-dokumentation`, worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`
Base: `73bcb5e`
Commits: `3eb41ec` (task 3), fix round 1 adds a second commit (see below).

## Fix round 1 — a stale "five gates", and the two Vale warnings

Three findings accepted as-is (the README restructuring, the RUF100 fix, and
the port disclosure); two fixes:

**1. `README.md:58` said "the five gates"; it's six.** Task 1 added a sixth
gate (documentation) to `.github/workflows/gates.yml`. Re-measured, not just
taken on the coordinator's word: `grep -c '^      - name: Gate'
.github/workflows/gates.yml` → `6`. Fixed the one number. Left `CLAUDE.md`'s
own `## Gates` section alone — it still says "All five pass" and lists only
five commands, which is the same staleness one level up, but task 8 ("Die
Regeln nachziehen") explicitly owns bringing `CLAUDE.md`'s gate list in line
with the documentation gates; not re-litigating that scope here.

**2. The two `Microsoft.We` warnings in the tutorial's opening sentence are
gone — via a path-scoped Vale exception, not a rewrite.** The coordinator's
reasoning: a warning that's supposed to be permanently ignored trains the
reader (or the next person running `make vale`) to skip the output, and then
a real one gets missed too. Rewriting away from "we"/"let's" was rejected for
the opposite reason — the skill's Tutorial quadrant (section 2a) requires
first-person plural, so Microsoft style and the skill genuinely disagree here,
and the skill wins for this project.

Added to `.vale.ini`:

```ini
[docs/tutorials/*.md]
Microsoft.We = NO
```

with a comment stating the conflict and why the skill wins, scoped to the one
quadrant the skill's instruction actually governs.

Measured both directions, not assumed:

- `make -C docs vale` across all five quadrants: `✔ 0 errors, 0 warnings and
  0 suggestions in 10 files.` — the tutorial's "we"/"our" no longer reports.
- The exception doesn't overreach: a throwaway `docs/how-to/zz-scratch.md`
  with "We will check the chain. Let's look at our log." still gets three
  `Microsoft.We` warnings (`We`, `Let's`, `our`) when run directly, confirming
  the rule still fires everywhere outside `docs/tutorials/`. Scratch file
  deleted after the check.

## The typed-out session

Done in a fresh `git clone` of this worktree's `HEAD` (`73bcb5e`) at
`/tmp/previously-task3-fresh`, against a dedicated PostgreSQL 17 container
(`previously-docs-fresh`, started with `docker run -d --name
previously-docs-fresh -p 5544:5432 -e POSTGRES_USER=previously -e
POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously postgres:17`), in one
continuous session. Both the container and the checkout were removed after
the session; neither is part of the repository.

**Port substitution, disclosed:** the real session ran against port `5544`,
not `5432`, because another project's container already held `5432` and
`5433` in this shared Docker daemon. The tutorial text shows `5432` — the port
the `docker run` command it gives the reader actually publishes — not `5544`,
which was an artifact of this measurement environment, not of Previously.
Everything else below is the unedited output of the commands as run.

```console
$ uv sync --all-extras
Using CPython 3.14.3
Creating virtual environment at: .venv
Resolved 74 packages in 0.65ms
Installed 71 packages in 159ms
 + accessible-pygments==0.0.5
 ... (71 packages total; full list omitted here, see the tutorial page for
     the same trim)
```

```console
$ export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5544/previously
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
```

```console
$ uv run previously append \
    --source email \
    --external-id 2026-10-03-kickoff@example.org \
    --text "The client approved the new homepage design.

Next milestone: content migration starts Monday."
1
```

```console
$ uv run previously log
1	2026-10-03T15:41:19.888666+00:00	observation	495362ef39c9

$ uv run previously verify
chain intact

$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-03T15:41:19.888666+00:00
hash=495362ef39c9af8358eaee83acc956d4813464cdd07057bd38c44680e3410dcc
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
```

A sanity-check `uv run pytest -q` at this point (before `tests/test_docs_typed_output.py`
existed) returned `187 passed in 17.04s` — confirming, independently, that
README's `181` was already stale (task 2's own gate run had already shown
`187`; this re-measures the same fact from a clean checkout). This run is
**not** the one quoted in the tutorial — see "The test count" below for why.

## Errors the typing found

**None of the three historically-named errors recurred**, because step 1 of
the brief instructs typing the *corrected* sequence directly (`uv sync
--all-extras` from the start, `PREVIOUSLY_DSN` set before `alembic`) rather
than re-enacting the missing-DSN and missing-extras mistakes — those are
already fixed and documented history, not something a Tutorial (one
guaranteed path, no alternatives) should re-demonstrate to a reader.

The typing did find one real, new defect, in the brief's own supplied code
for `tests/test_docs_typed_output.py`:

**The brief's `# noqa: S603` on the `subprocess.run` call is unused.**
`uv run ruff check` on the file as supplied reports `RUF100 Unused 'noqa'
directive (unused: S603)`. Ruff's S603 only fires when it cannot prove every
argument is a literal; the existing precedent this comment was modeled on
(`tests/test_contracts.py:206`) passes a variable (`_RUNTIME_PROBE`) and
therefore does need the suppression, but the brief's call passes five
literal strings (`sys.executable, "-m", "pytest", "--collect-only", "-q"`),
which ruff accepts as safe without a suppression at all. Keeping the
unneeded `# noqa` would have failed `uv run ruff check .` outright (`RUF100`
is itself an error). Fixed by removing the directive and replacing it with a
comment stating what was measured, rather than padding CLAUDE.md's
suppression registry with a sixth entry that isn't actually needed — CLAUDE.md
is unchanged by this task.

## The test count, and when it was typed

**188.** Collected and run in the fresh checkout (`/tmp/previously-task3-fresh`),
*after* `tests/test_docs_typed_output.py`, the finished tutorial page, and the
shrunk `README.md` all existed — copied into that checkout from this worktree
for the final capture, so the number reflects exactly what ships, not a
number computed by hand. `uv run pytest --collect-only -q` there reported
`188 tests collected`; the full `uv run pytest` run that follows is the exact,
unedited text now embedded in the tutorial's last code block (`188 passed in
16.48s`, seed `117658426`).

187 is the pre-task-3 baseline (confirmed independently above and matching
task 2's own gate output of `187 passed`); 188 = 187 + the one new test
function in `tests/test_docs_typed_output.py`.

In the worktree itself (the actual commit target), `uv run pytest -q` and
`uv run pytest tests/test_docs_typed_output.py -v` both also return 188/1
passed — see Gates below.

## The README's "Language" section — decision

**Removed outright, not rewritten in place.** Found a real discrepancy, not
just staleness: README's section mirrors the *pre-refactor* wording of
`CLAUDE.md`'s own Language section almost verbatim (three German-exception
categories — specifications, plans, "the working notes" — and no mention of
root configuration at all). Commit `68aa66f` (`refactor(config): translate
the root configuration to English`) added a fourth category by name
(`NOTIZEN.md`) and the entire root-configuration clause (`pyproject.toml`,
`.importlinter`, `alembic.ini`, `.pre-commit-config.yaml`, with the "program
output or published metadata" reasoning) to `CLAUDE.md` — and nobody carried
that forward into README. README's own closing sentence already says
"`CLAUDE.md` carries the binding wording," which is the tell: a page that
states a rule and immediately defers to another page as authoritative is
duplicating a fact it admits it doesn't own, and the duplicate had already
drifted (measured above) by the time this task started. Fixed by deleting the
section; the existing Documents table's `CLAUDE.md` row ("The working
agreements: language, attribution, dependencies, the five gates" — fixed to
"six" in fix round 1, see top of this report) is the pointer the brief asks
for, so no new link needed adding.

## Other README decisions

- **Kept, not required by the brief's literal four-item list but not part of
  "the walkthrough" either:** nothing — on reflection, "Drin bleiben: A, B, C,
  D" was read as exhaustive (matching the task's own "schrumpft auf einen
  Zeiger" framing, repeated identically in the task text, the brief, and the
  plan), so "The basic idea" and "What it is not" were **removed**, not kept.
  Their content isn't yet duplicated anywhere in the Sphinx docs — tasks 5–6
  (Explanation) will eventually cover related ground, but not this task's
  problem to pre-empt. Flagging this explicitly since it's the one judgment
  call in this task that isn't forced by a measurement.
- The existing Documents table stays (it isn't "der Durchlauf" — it's
  pointers to specs/working notes the Sphinx build deliberately excludes), now
  under a new "## Documentation" heading with a lead paragraph pointing at
  `docs/` and explicitly naming the tutorial.
- README can't use MyST `{ref}` roles (GitHub renders it as plain Markdown),
  so "Die README verweist auf das Label" is satisfied with a relative link to
  the tutorial's source file — the practical equivalent given the renderer.

## Vale vocabulary

Three words added to `.vale-styles/config/vocabularies/Previously/accept.txt`:
`uv`, `toolchain`, `idempotency`. Each checked in isolation first (a
throwaway `docs/tutorials/zz-scratch.md`, one word per sentence, run through
`uv run --extra docs vale`, then deleted): all three failed `Vale.Spelling`
on their own, confirming the combined-file run wasn't a context artifact.
`idempotency` was explicitly flagged as deferred in task 2's report ("whoever
writes the page that first uses one of them in prose adds it then, with the
same measure-first discipline") — this is that page.

Also fixed, not vocabulary: `Microsoft.Dashes` ("Remove the spaces around
'—'") on two em dashes in running prose. The existing reference pages only
use em dashes inside table cells, where Markdown's own cell-trimming removes
the adjacent whitespace before Vale sees it; prose em dashes need the
no-space form. Changed `word — word` to `word—word` in both places.

Two `Microsoft.We` warnings originally remained in the tutorial's opening
sentence ("we will", "our") — measured that Vale's exit code stayed `0` with
only warnings present, so they didn't fail `make -C docs vale` on their own.
**Fix round 1 removed them anyway**, via a path-scoped `.vale.ini` exception
rather than a rewrite — see "Fix round 1" at the top of this report for the
full reasoning and the measurement that the exception doesn't overreach.

Also fixed, not vocabulary: two passive constructions caught on manual
re-read ("the flag was left out", "that list is left out") — reworded to
active voice per the skill's style rule; Vale's own `Microsoft.Passive`
didn't flag either, but the skill's rule isn't conditional on Vale catching
it.

## Gates

First pass (before fix round 1):

```
make -C docs html        -> build succeeded (0 warnings)
make -C docs vale         -> 0 errors, 2 warnings (Microsoft.We, see above), 0 suggestions in 10 files; exit 0
make -C docs linkcheck    -> build succeeded, the one new external link (docs.astral.sh/uv) resolves
uv run ruff check .       -> All checks passed!
uv run ruff format --check . -> 38 files already formatted
uv run pyright            -> 0 errors, 0 warnings, 0 informations
uv run lint-imports        -> Contracts: 4 kept, 0 broken
uv run pytest -q          -> 188 passed in 16.41s
uv run pytest --cov --cov-report=term-missing -> 188 passed, 99.80% coverage (required: 90.0%)
```

Rerun after fix round 1 (README's gate count, the `.vale.ini` exception):

```
make -C docs html        -> build succeeded (0 warnings)
make -C docs vale         -> 0 errors, 0 warnings, 0 suggestions in 10 files
make -C docs linkcheck    -> build succeeded
uv run ruff check .       -> All checks passed!
uv run ruff format --check . -> 38 files already formatted
uv run pyright            -> 0 errors, 0 warnings, 0 informations
uv run lint-imports        -> Contracts: 4 kept, 0 broken
uv run pytest -q          -> 188 passed in 16.46s
```

`uv run pytest tests/test_docs_typed_output.py -v`, run explicitly as required, after fix round 1:

```
tests/test_docs_typed_output.py::test_typed_test_counts_match_the_tree PASSED [100%]
============================== 1 passed in 0.76s ===============================
```

Test count unchanged at **188** — fix round 1 touched no test file.

## Files

- Created: `docs/tutorials/record-your-first-event.md` (label
  `(first-event-tutorial)=`), `tests/test_docs_typed_output.py`.
- Modified: `docs/tutorials/index.md` (toctree entry), `README.md` (shrunk;
  see decisions above, plus the "five" → "six" gates fix), `.vale-styles/config/vocabularies/Previously/accept.txt`
  (three words, each checked in isolation — not in the brief's file list, but
  the designated, measure-first place for exactly this, per the task's own
  instruction and task 2's precedent).
- Fix round 1 additionally modified: `.vale.ini` (path-scoped
  `Microsoft.We = NO` for `docs/tutorials/*.md`, with a comment).
- `CLAUDE.md` deliberately **not** touched, in either round — in round 0 the
  suppression that would have required updating its registry turned out not
  to be needed; in round 1 its own stale "All five pass" is task 8's to fix,
  not this task's.

## Commits

`3eb41ec` — `docs: a tutorial that was actually typed out, and a shorter README`
`7a35ba6` — `docs: six gates in the README, and the skill over Microsoft style in tutorials`
