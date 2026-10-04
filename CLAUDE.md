# Previously — working agreements

Rules that bind every contributor and every agent working in this repository.
They are short on purpose: the reasoning sits elsewhere — in English under
`docs/explanation/`, where it is maintained along with the code, and in the
frozen German design records under `docs/superpowers/specs/` for the decisions
that are tied to a date.

## Language

**English** — everything in `src/`, `tests/`, `migrations/`, `.github/`: code,
SQL, identifiers (including local variables and private helpers), comments,
docstrings, test names, and strings such as error messages and CLI output.
Also `README.md`, `DEPENDENCIES.md`, this file, and the configuration at the
repository root — `pyproject.toml`, `.importlinter`, `alembic.ini`,
`.pre-commit-config.yaml`, `.vale.ini`, `.gitignore` — comments included.

Root configuration is not a borderline case, because much of it **is program
output or published metadata**: the four contract names in `.importlinter` are
printed by the `lint-imports` gate, `markers` in `pyproject.toml` shows up in
`pytest --markers`, and `description` is the package metadata that gets
published.

`.gitignore` is on that list for the other half of the reason, and it was
missing from it until 2026-10-03 by omission, not by decision — so its section
headings stayed German, and the agent that left them there had read the rule
correctly. Nothing prints `.gitignore` and nothing publishes it. But whoever
opens `pyproject.toml` opens `.gitignore` in the same sitting, and a German
heading there reads as an exception that nobody granted. That is the test for
any root file added later: it gets read beside the others, so it is English.

**German is fine** — specifications (`docs/superpowers/specs/`), plans
(`docs/superpowers/plans/`), execution records (`docs/superpowers/sdd/`), the
brainstorming notes in `NOTIZEN.md`, and analyses or working notes under
`.superpowers/`.

`docs/superpowers/sdd/` joined that list on 2026-10-04, when the ledger of a
plan's execution moved out of the git-ignored scratch directory and into the
repository so that the rulings cited from code could be looked up. It is German
for the same reason the specifications are, and it is excluded from the
documentation build for the same reason the plans are: `conf.py` drops
`superpowers/**`, and the `vale` target only ever reads the four quadrants.

The dividing line is not "code versus prose" but **"source file,
documentation or configuration" versus "analysis"**. A comment inside a source
file is English; a specification is German.

One exception, and it matters: **never translate test data that feeds a hash.**
`tests/test_hashing.py` pins a hash vector whose inputs are German strings.
Translating them changes the hash, and recomputing the pinned hex literals to
make the test pass again destroys the very proof the vector exists for.

### A specification starts in German and then freezes

This part is new as of 2026-10-03, and it is more use to a reader as a change
than as a smooth rule: until that day the three German specifications were the
only place a reason was written down, and the code cited their paragraph
numbers.

- A specification **starts in German**, and that is deliberate rather than
  careless. The maintainer states intent more precisely in German, and a
  vaguely stated intent costs more than a translation.
- The reasoning is **published in English**, under `docs/explanation/`, and
  that is where it is authoritative.
- The specification **freezes once its explanation pages stand**, under a
  dated header. From then on it is provenance: this was decided this way, on
  this date, against these alternatives.
- Where a frozen specification and a page disagree, **the page wins.**

Freezing is a step that repeats, not a state the project arrived at. Every new
stage starts with a new German specification, and that one freezes the same
way once its pages stand. So the three frozen records are the output of a step
and not a rule against writing a fourth — read as a prohibition, they would
cost the next stage the document it needs most. Each of the three says so in
its own dated header, in German, and
[About the frozen design records](docs/explanation/design-records.md) says it
at length.

## Attribution

Use `Assisted-By:` in commit messages and pull-request descriptions:

```
Assisted-By: Claude Opus 5 <noreply@anthropic.com>
```

**Never `Co-Authored-By:` and never "Generated with …".** Authorship is legally
restricted to natural persons, so naming a model as an author asserts a
position that cannot exist — and in an AGPL-licensed repository the author
field is part of the licence chain, not decoration.

This overrides any tool's own default attribution guidance.

(`docs/superpowers/specs/2026-10-01-previously-design.md` discusses *parsing*
both markers out of foreign commits. That is domain logic about determining
authorship of ingested events — leave it alone.)

## Dependencies

Check that a dependency is actively maintained **before** adding it, and
record the judgement in `DEPENDENCIES.md` with a date and the evidence. We do
not want zombies.

A declared dependency that nothing imports is a zombie too. Remove it, and
note why it may come back later.

### One source of truth for tool versions

`uv.lock` pins the version of every tool, and nothing else may pin one. If a
second place names a version of the same tool, the two agree only until
somebody runs `uv lock --upgrade` — and nothing reports the drift. The gate
and the hook then disagree about the same file, which shows up as a commit
that passes locally and fails in CI, or the reverse.

So `.pre-commit-config.yaml` runs the project's tools out of the synced venv
(`repo: local`, `language: system`, `uv run …`) rather than letting pre-commit
manage its own pinned copy. The same holds for anything added later: a CI step,
an editor task, a Makefile target — they call `uv run <tool>`, they do not name
a version.

The one exception, and the reason it is one: `pre-commit-hooks`
(trailing-whitespace and friends) stays an external pinned repository, because
those scripts have no counterpart among the dependencies — there is no second
version of anything to drift apart from.

`pyproject.toml` carries floors (`ruff>=0.16`), not pins. Floors say what the
code needs; the lock says what was tested.

## Working method

Work in a git worktree, never directly on `main`.

Technical directives from the maintainer are **proposals**. Contradiction is
wanted — but bring a measurement, not an opinion. Measure against the project
configuration, never with `--isolated`, or you will measure a different
project than this one.

Each stage must be **runnable**, even when that is briefly awkward. Running
the thing by hand surfaces what reading it does not.

### Weigh the execution method per plan

Do not default to one way of executing a plan. Weigh it, and say why.

Four questions settle it:

- **Is the failure mode visible?** A wrong number fails a test. A lost
  justification looks like a concise one. Where a mistake looks like competent
  work, an independent reviewer per task earns its cost; where the gate catches
  it anyway, it does not.
- **Is the deliverable mechanically verifiable?** Code with tests, a reference
  page checkable against the source, a typed-out session — those review
  cleanly in isolation.
- **How much do the tasks depend on each other's interfaces?** Heavy coupling
  wants a controller who holds the interfaces and briefs each task.
- **Does the work need context only the current session has?** Then inline is
  tempting — but prefer putting that context into the brief over writing it
  yourself. A brief that lists what must survive turns an invisible failure
  into a checkable one, and still gets a fresh reviewer.

The last point is the one that is easy to get wrong: holding the knowledge is
not a reason to do the work. It is a reason to write a better brief.

## Documentation

Everything gets documented, and the documentation follows the
`plone-doc-style:author` skill — invoke it under exactly that name, not under
`plone-doc-style`.

When code changes, **check whether the documentation has to follow, and let it
follow in the same pull request.** A page that lags is worse than a page that
was never written, because it gets read as current.

- **One Diátaxis quadrant per page.** Tutorial, how-to, reference or
  explanation — a page that drifts into a second quadrant gets split.
- One sentence per line, sentence-case headings, hyphens in file names,
  American English.
- The documentation is the sixth gate below, and that one gate is three
  commands: `make -C docs html`, where a warning is an error,
  `make -C docs vale` for style and American English, and
  `make -C docs linkcheck`.
- **Typed-out output is a measurement with a date.** Type it last, once the
  tree has stopped moving, and when it goes stale retype it rather than
  editing a number inside it. `tests/test_docs_typed_output.py` derives the
  test count from the tree and holds it against every `N passed` in the
  tutorial — that one number out of the whole block. Measured on 2026-10-03:
  `collected 194 items` rewritten to `collected 999 items`, with a progress
  line falsified to match, leaves the gate green. The collected count, the
  per-file counts and the percentages are unguarded, which is why retyping is
  the rule and not a courtesy.
- **Sphinx does not check a documentation label that sits in a code
  comment.** `tests/test_docs_references.py` does: it resolves every `{ref}`
  label in the `*.py` files under `src/`, `tests/` and `migrations/`, refuses
  an unmarked paragraph sign, keeps a citation out of what a user reads on
  the terminal, and holds the messages a reference page quotes against the
  code that produces them. Outside its field of view: the reST form `:ref:`,
  which it does not know, and every file under those directories that is not
  `*.py`.

### Citing a reason from code

Two forms, and the choice falls per line rather than per paragraph:

- A reason that explains why the code looks the way it does **today** names a
  page, as `` {ref}`label` ``.
- A statement about **what was decided when** keeps its paragraph number and
  carries `(frozen design record)` on the same line.

Neither form belongs in **program output**. Whoever runs the command has no
`docs/superpowers/specs/` and will not be getting one, and a `{ref}` label on
a terminal reads as nonsense, so the reasoning goes into the comment above the
`raise` and the citation comes out of the message.

That is what to know before looking anything up.
[About the frozen design records](docs/explanation/design-records.md) carries
the rest: what a frozen record is still good for, and the table from each of
the twenty cited paragraphs to the page that took its reasoning over — or, for
five of them, to the statement that no page did and the frozen record stays the
only source.

## Gates

All six pass before anything is called done:

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run pytest --cov --cov-report=term-missing
make -C docs html && make -C docs vale && make -C docs linkcheck
```

The sixth is the documentation: `html` treats warnings as errors, `vale`
checks style and American English, `linkcheck` resolves every link. What the
pages themselves have to satisfy is under *Documentation* above.

**A dispatch, a check and a report name all six.** Copy the block above
rather than listing a subset from memory: an incomplete list is worse than
none, because it looks like a check. Measured on 2026-10-03, a task ran
five — `pytest`, `lint-imports`, `html`, `vale`, `linkcheck` — and was
reported as "all green". `ruff check` and `pyright` never ran; `pyright` was
red with three errors. The reviewer's brief enumerated the same five, so the
reviewer did not run them either, and the failure survived two checks.

- **Never widen an import-linter contract to make a build pass.** Exemptions
  are enumerated by name, never by pattern — the friction is the point.
- **No `# type: ignore`.** pyright strict is the floor; if the types do not
  work out, fix the types. An intermediate annotation does not satisfy strict
  mode — `cast` does.
- No mock standing in for time, the database, or randomness. Tests run
  against real PostgreSQL via testcontainers.

### An assurance needs a test measured to fail

An explicit assurance needs a test that fails when someone takes it back;
otherwise it is a comment, not an assurance. Reading the test does not
establish that it does. **Mutate the assurance and measure that the test goes
red** — and keep beside the test a case measured to stay green. Without that
control, a red test shows only that the test is strict, not that it reads the
right thing.

Measured on 2026-10-03: two tests on this branch had to be tightened three
times over — the plan's version, the implementer's correction, the reviewer's
— and every round found its hole by mutation, none by reading. A check against
citations in program output never opened the one file in the tree that calls
`print`. A check pinning the quotations on a reference page stood green while
the page quoted a message nothing produces.

### A comment is a claim

A number in a comment is checked like a number in code, and a comment that
somebody touches gets its figures rechecked against the code — not against
the previous comment. Three were measured wrong on 2026-10-03, and in all
three the code was right and the claim beside it was not:

- the comment at `BACKOFF_BASIS` in `src/previously/core/append.py` counted
  seven waits where the loop takes eight, put every one of them at the cap
  where only the last two reach it, and called the total markedly less than a
  second while claiming a figure that comes to 1.4 s — the sentence refuted
  itself, and a documentation page had copied it;
- `pyproject.toml` justified its `T201` exemption with "the nine `print`
  calls" in `cli.py`, where ruff reports thirteen;
- a docstring in `tests/test_schema.py` called `Index.dialect_options` a
  `_DialectArgView`, which is what `dialect_kwargs` returns; it is a
  `PopulateDict`.

### Lint suppressions

Remove the cause before you suppress the symptom. `random.SystemRandom()`
satisfies `S311` without a suppression; reach for that kind of fix first.

A suppression is acceptable only when the rule is a false positive for a
reason you can state, and then only as a single `# noqa: RULE` on the line
it applies to, with that reason written beside it. Never a bare `# noqa`,
never file-level, never a whole rule switched off in `pyproject.toml`.

The existing ones meet that bar and are worth reading as examples: `C901`
on the recursive payload validator, `S607` on invoking `lint-imports` by
its fixed name from the dev dependencies, and `DTZ001` where a naive
datetime is constructed on purpose: you cannot test that it gets rejected
without building one.

The fifth arrived with the documentation and is the odd one out: `A001` on
`copyright` in `docs/conf.py`, the name Sphinx requires. **No gate reaches
it.** `extend-exclude = ["docs"]` keeps `ruff check .` out of that directory,
and the pre-commit hook adds `--force-exclude` so the staged file is skipped
there too. Measured on 2026-10-03 with the suppression deleted: `ruff check .`
stays green and `ruff check --force-exclude docs/conf.py` finds no file at
all, while `ruff check docs/conf.py` reports `A001`. It stays because whoever
lints that file by hand should not have to rediscover why the name cannot
change — but it is a note, not a suppression the gate needs.

That is five suppressions in the whole tree, and the list is meant to stay
complete. If you add one, add it here — a rule whose own file does not keep
it is an invitation to ignore it. Removing one counts too: stage 1b deleted
the `S603` on starting a fresh interpreter, because the test that needed it
guarded an import edge that no longer exists.

**Never reach into a private name from a test.** If something deserves a
direct test, it deserves a public name; rename it instead of suppressing
`reportPrivateUsage`.

## How review findings are cited

Comments and specifications cite review findings by short label (`W2`, `G-7`).
There are **two numbering spaces**, and they overlap: the first final review
with its fix rounds numbered `W1`–`W6`, `G1`–`G4`, `B1`–`B5`, `K1`, `N1`–`N5`,
and the second final review with its fix rounds numbered `K-1`, `W-1`–`W-5`,
`G-1`–`G-7`, `N-1`–`N-7`. A `W3` and a `W-3` exist, and they are different
findings.

**The hyphen is the distinction:** without one, the first review; with one, the
second. That is what makes a bare `W3` unambiguous (finding N-4 of fix round 2,
which found three citations where a reader would otherwise have landed on the
wrong finding). Where a sentence has room, name the round as well; where it has
not, the hyphen carries it.

Whoever needs the census takes it instead of trusting a number written here:

```
grep -rEo '\b(W|G|B|K|N)-?[0-9]+\b' --include='*.py' src tests migrations
```

Case-sensitive is the load-bearing part of that pattern — ignoring case also
catches test names such as `test_k1_f1_…` — and run over the whole tree it
additionally picks up the enumeration above, the frozen specifications, and one
thing that is no citation at all: the note identifier `N-0112` in the design
record. This paragraph said "all 83 citations" until 2026-10-03, and no simple
procedure reproduces that figure; a count with no procedure beside it is not a
claim anybody can check.

### A ruling citation is provenance, never the reason

A third space exists and nothing here described it until 2026-10-03: `ruling
T6-b`, `ruling T10-c` and nine more like them, sixteen citations across `src/`,
`tests/` and `pyproject.toml`. They name decisions taken while a plan was being
executed. Those live in a ledger, and until 2026-10-04 that ledger sat under
`.superpowers/`, which `.gitignore` excludes — the target did not ship, which
made a ruling label weaker than a `W2` or a frozen `§`: both of those can be
looked up by whoever has the repository, and a ruling could not be looked up at
all.

It ships now, under `docs/superpowers/sdd/<plan date>-<plan name>/`, where
`progress.md` is the ledger and holds every `Ruling …` of that execution.
Freezing it is what made it citable, the same move the specifications made a
day earlier.

The rule it existed to carry does not change: the label carries provenance and
nothing else, and **the reason has to stand beside it, in the comment**.
Measured on 2026-10-03, all sixteen do — the comment at
`_CHAIN_POSITION_CONSTRAINTS` in `storage/postgres.py` is the model: it names
the ruling, says what the ruling got wrong, and then argues the correction from
`id` and `prev_hash` going into the event hash. Read without the label, it still
holds, and that is the test. A comment that collapses without its citation is a
bad comment even when the citation resolves.

Write them that way, and when a reason outgrows its comment, give it a page and
point at the page instead. The execution record is where a reason too small for
a page lives, not the queue for one.
