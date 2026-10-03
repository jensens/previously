# Previously — working agreements

Rules that bind every contributor and every agent working in this repository.
They are short on purpose; the reasoning behind each one is in the specs under
`docs/superpowers/specs/`.

## Language

**English** — everything in `src/`, `tests/`, `migrations/`, `.github/`: code,
SQL, identifiers (including local variables and private helpers), comments,
docstrings, test names, and strings such as error messages and CLI output.
Also `README.md`, `DEPENDENCIES.md`, this file, and the configuration at the
repository root — `pyproject.toml`, `.importlinter`, `alembic.ini`,
`.pre-commit-config.yaml` — comments included.

Root configuration is not a borderline case, because much of it **is program
output or published metadata**: the four contract names in `.importlinter` are
printed by the `lint-imports` gate, `markers` in `pyproject.toml` shows up in
`pytest --markers`, and `description` is the package metadata that gets
published.

**German is fine** — specifications (`docs/superpowers/specs/`), plans
(`docs/superpowers/plans/`), the brainstorming notes in `NOTIZEN.md`, and
analyses or working notes under `.superpowers/`.

The dividing line is not "code versus prose" but **"source file,
documentation or configuration" versus "analysis"**. A comment inside a source
file is English; a specification is German.

One exception, and it matters: **never translate test data that feeds a hash.**
`tests/test_hashing.py` pins a hash vector whose inputs are German strings.
Translating them changes the hash, and recomputing the pinned hex literals to
make the test pass again destroys the very proof the vector exists for.

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

## Gates

All five pass before anything is called done:

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run pytest --cov --cov-report=term-missing
```

- **Never widen an import-linter contract to make a build pass.** Exemptions
  are enumerated by name, never by pattern — the friction is the point.
- **No `# type: ignore`.** pyright strict is the floor; if the types do not
  work out, fix the types. An intermediate annotation does not satisfy strict
  mode — `cast` does.
- No mock standing in for time, the database, or randomness. Tests run
  against real PostgreSQL via testcontainers.
- An explicit assurance needs a test that fails when someone takes it back.
  Otherwise it is a comment, not an assurance.

### Lint suppressions

Remove the cause before you suppress the symptom. `random.SystemRandom()`
satisfies `S311` without a suppression; reach for that kind of fix first.

A suppression is acceptable only when the rule is a false positive for a
reason you can state, and then only as a single `# noqa: RULE` on the line
it applies to, with that reason written beside it. Never a bare `# noqa`,
never file-level, never a whole rule switched off in `pyproject.toml`.

The existing ones meet that bar and are worth reading as examples: `C901`
on the recursive payload validator, `S607` on invoking `lint-imports` by
its fixed name from the dev dependencies, `S603` on starting a fresh
interpreter in the same place — our own interpreter, our own script, no
input — and `DTZ001` where a naive datetime is constructed on purpose: you
cannot test that it gets rejected without building one.

That is five suppressions in the whole tree, and the list is meant to stay
complete. If you add one, add it here — a rule whose own file does not keep
it is an invitation to ignore it.

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
second. Checked across the tree, the convention holds at all 83 citations —
that is what makes a bare `W3` unambiguous (finding N-4 of fix round 2, which
found three citations where a reader would otherwise have landed on the wrong
finding). Where a sentence has room, name the round as well; where it has not,
the hyphen carries it.
