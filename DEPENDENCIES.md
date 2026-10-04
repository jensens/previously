# Dependency register

Method and reasoning: §10.7 of the architecture. Every line carries **what
for**, **alternative rejected because** and **last checked on** together with
the judgement — a date on its own decides nothing.

Twelve of the thirteen paragraph references on this page point into a **frozen
design record**: the German specifications under `docs/superpowers/specs/`,
which hold how and why something was decided on the date they carry, and which
are not pulled forward any more. That is the right source here, because every
line of this register is itself a dated decision — and because eleven of those
twelve have no page under `docs/` at all: §10.6 eight times, §10.7 twice, and
§8.6. The twelfth, §10.1 in the `sqlalchemy` line, has its outcome recorded
there but not its argument. The one reference that is **not** frozen is §2,
the module boundaries, whose reasoning is maintained along with the code in
[About the module boundaries](docs/explanation/module-boundaries.md).

Both kinds of citation and the difference between them are explained in
[About the frozen design records](docs/explanation/design-records.md). Its
table maps the twenty paragraphs that the **code** cites; of the five cited
here, §2 and §10.1 stand in that table too, while §8.6, §10.6 and §10.7 do
not appear in it at all.

| Package | What for | Alternative rejected because | Last checked |
|---|---|---|---|
| `sqlalchemy` | Schema and queries, Core without an ORM | an ORM solves change tracking, which an append-only store does not need (§10.1) | 2026-10-02, active |
| `psycopg` | PostgreSQL driver | `psycopg2` is the previous generation | 2026-10-02, active |
| `alembic` | Migrations for the log, units, source_key | hand-written DDL is not traceable | 2026-10-02, active |
| `testcontainers` | real PostgreSQL in the test | a mock or SQLite would miss precisely the SQL semantics that 1a rests on | 2026-10-02, active |
| `hypothesis` | Properties of the chain and of the canonicalisation | example tests do not check invariants | 2026-10-02, active |
| `pytest-cov` | Coverage measurement in the test run | a self-built one would only thinly wrap `coverage`, which we need anyway | 2026-10-02, **last release 194 days old, judgement: active, not abandoned** — the source repository has commits up to 21.09.2026, is not archived, has a history of 54 releases; the missing new release mirrors a missing need for change, not standstill |
| `hatchling` | Build backend | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `ruff` | Lint and format | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pyright` | Type checking, strict | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `import-linter` | The architectural boundaries of §2 checked as contracts | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pytest` | Test framework | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `coverage` | Coverage measurement, `fail_under = 90` | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pytest-randomly` | Random test order, uncovers dependencies between tests | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pre-commit` | Git hooks before the commit | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pip-audit` | Audits the locked environment against published advisories, in `.github/workflows/audit.yml` | — | 2026-10-04, active — last release 2.10.1 on 2026-06-10; repository `pypa/pip-audit` maintained under the Python Packaging Authority, pushed 2026-10-01, not archived, maintainer commits up to 2026-08-31 |
| `hatch-vcs` | The version out of Git tags | — | 2026-10-02, **over a year old, judgement: finished, not abandoned** — a few lines of glue around `setuptools-scm` |
| `sphinx` | Builds the documentation | — | 2026-10-03, active — last release 2025-12-31, repository pushed 2026-09-21 |
| `myst-parser` | Reads Markdown instead of reStructuredText | — | 2026-10-03, active — last release 2026-05-13 |
| `sphinx-book-theme` | Theme | `plone-sphinx-theme` wraps exactly this theme, so every markup choice the `plone-doc-style` skill makes stays valid and nothing needs rewriting | 2026-10-03, active — last release 2026-07-19 |
| `sphinx-design` | Grids and cards for the landing pages | — | 2026-10-03, active — last release 2026-01-19, repository pushed 2026-09-28 |
| `sphinx-copybutton` | Copy button on code blocks | — | 2026-10-03, **last release 2023-04-14, judgement: finished, not abandoned** — repository pushed 2026-09-28, not archived; an extension that appends a copy button is, at some point, simply finished |
| `sphinxcontrib-mermaid` | Renders the four Mermaid diagrams (see the plan's Diagrams section) | — | 2026-10-03, active — last release 2026-09-01, repository pushed 2026-10-01 |
| `vale` | Checks style and American English | — | 2026-10-03, active — last release 2026-09-18 |
| `linkify-it-py` | Turns bare URLs into links; `conf.py`'s `myst_enable_extensions` turns on `linkify`, and markdown-it-py's linkify rule raises `ModuleNotFoundError` without this installed | — | 2026-10-03, active — last release 2026-08-29, repository pushed the same day, not archived |

**Not in the plan's dependency table.** `linkify-it-py` is the eighth new
dependency, found by running `make -C docs html`, not by review: the
Sphinx build failed with `ModuleNotFoundError: Linkify enabled but not
installed.` The plan's table in task 1, step 2 covers seven packages and
says they were already checked; this one was checked the same way and on
the same day, for the same reason it was missing — running the build is
what surfaced it.

**`vale` is a wrapper, not the tool.** The PyPI package is a shell that fetches
the Go binary; its version encodes the Vale version (`3.22.0.0` → Vale
`3.22.0`). `uv.lock` therefore pins the binary too — the "one source of
truth" rule holds even though the binary itself ships from a different
ecosystem.

**No `pydantic` — not yet.** It stood in this table until 2026-10-03 with
"validation of payloads" as the purpose and "schema export for MCP later" as
the reason the hand-written alternative had been rejected. Measured,
`grep -rn pydantic src tests migrations` found **nothing**: the validation in
stage 1a is done by hand in `core/canonical.py`, and the reason given was a
reason for **later**. A declared but never imported dependency is the zombie
in its purest form (§10.7 of the architecture) — it gets installed, enlarges
the attack surface, and nobody notices when it is orphaned. So it goes, and
it comes back together with its user: the schema export of the MCP interface
(§8.6 of the architecture) is a real purpose, just not one of stage 1a's.

One thing is already prepared for that return, because it was measured once
and would otherwise have to be measured again (ruling T2-e): as soon as the
first `BaseModel` arises, `[tool.ruff.lint.flake8-type-checking]` needs the
entry `runtime-evaluated-base-classes = ["pydantic.BaseModel"]`, or ruff moves
the `BaseModel` imports under `TYPE_CHECKING` and pydantic fails at runtime.
That note stands in `pyproject.toml`, at the place where it will be needed.

**No library for JCS.** The permitted payload range is so restricted (no
floating point numbers, ASCII keys, integers inside the safe range) that
`json.dumps` with fixed flags is canonical already — see `core/canonical.py`.
Getting rid of a dependency is better than checking it.
