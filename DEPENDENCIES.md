# Dependency register

Method and reasoning: §10.7 of the architecture. Every line carries **what
for**, **alternative rejected because** and **last checked on** together with
the judgement — a date on its own decides nothing.

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
| `hatch-vcs` | The version out of Git tags | — | 2026-10-02, **over a year old, judgement: finished, not abandoned** — a few lines of glue around `setuptools-scm` |

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
