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
| `hatchling` | Build backend; also a dev dependency since 2026-10-05, because `tests/test_wheel.py` builds the wheel in the test's own process, without a subprocess, with hatchling's `WheelBuilder` | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active; rechecked 2026-10-05 — 1.32.4 on 2026-09-20, ships `py.typed` |
| `ruff` | Lint and format | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pyright` | Type checking, strict | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `import-linter` | The architectural boundaries of §2 checked as contracts | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pytest` | Test framework | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `coverage` | Coverage measurement, `fail_under = 90` | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pytest-randomly` | Random test order, uncovers dependencies between tests | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pre-commit` | Git hooks before the commit | reasoning in §10.6 of the architecture (choice of tooling) | 2026-10-02, active |
| `pip-audit` | Audits the locked environment against published advisories, in `.github/workflows/audit.yml` | — | 2026-10-04, active — last release 2.10.1 on 2026-06-10; repository `pypa/pip-audit` maintained under the Python Packaging Authority, pushed 2026-10-01, not archived, maintainer commits up to 2026-08-31 |
| `hatch-vcs` | The version out of Git tags; also a dev dependency since 2026-10-05, because the wheel `tests/test_wheel.py` builds in its own process takes its version from it | — | 2026-10-02, **over a year old, judgement: finished, not abandoned** — a few lines of glue around `setuptools-scm` |
| `sphinx` | Builds the documentation | — | 2026-10-03, active — last release 2025-12-31, repository pushed 2026-09-21 |
| `myst-parser` | Reads Markdown instead of reStructuredText | — | 2026-10-03, active — last release 2026-05-13 |
| `sphinx-book-theme` | Theme | `plone-sphinx-theme` wraps exactly this theme, so every markup choice the `plone-doc-style` skill makes stays valid and nothing needs rewriting | 2026-10-03, active — last release 2026-07-19 |
| `sphinx-design` | Grids and cards for the landing pages | — | 2026-10-03, active — last release 2026-01-19, repository pushed 2026-09-28 |
| `sphinx-copybutton` | Copy button on code blocks | — | 2026-10-03, **last release 2023-04-14, judgement: finished, not abandoned** — repository pushed 2026-09-28, not archived; an extension that appends a copy button is, at some point, simply finished |
| `sphinxcontrib-mermaid` | Renders the four Mermaid diagrams (see the plan's Diagrams section) | — | 2026-10-03, active — last release 2026-09-01, repository pushed 2026-10-01 |
| `vale` | Checks style and American English | — | 2026-10-03, active — last release 2026-09-18 |
| `linkify-it-py` | Turns bare URLs into links; `conf.py`'s `myst_enable_extensions` turns on `linkify`, and markdown-it-py's linkify rule raises `ModuleNotFoundError` without this installed | — | 2026-10-03, active — last release 2026-08-29, repository pushed the same day, not archived |
| `boto3` | The S3 client in `storage/s3.py`, the one module allowed to import it ([About blobs](docs/explanation/blobs.md)) | the MinIO Python SDK: last release 7.2.20 on 2025-11-27, and the server project it belongs to, `minio/minio`, is archived (checked 2026-10-05) | 2026-10-05, active — 1.43.108 on 2026-10-02, a release on each of the four working days before it; repository `boto/boto3` pushed 2026-10-02, not archived. Brings `botocore` (same day), `s3transfer` (0.19.2, 2026-07-22) and `jmespath` (1.1.0, 2026-01-22) |
| `pyrage` | Seals and opens blobs in the `age` format in `core/sealing.py`, the one module allowed to import it | `cryptography` with AES-GCM in one piece holds the plaintext, the ciphertext and the opened copy at once and stops at 2 GiB — measured on 2026-10-05 with `docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/measure_gcm.py`: a peak of 793 MiB at 256 MiB, and at 2048 MiB `OverflowError: Data or associated data too long. Max 2**31 - 1 bytes`; with a chunked scheme of our own it would be security-critical code and a format of our own; Tink pulls in `protobuf`, `absl-py` and `bazel-runfiles` | 2026-10-05, **released rarely, judgement: acceptable because the format carries it** — 1.4.0 on 2026-08-23, before that 2025-06-14 and 2025-04-02; one maintainer; repository `woodruffw/pyrage` pushed 2026-09-30, last commit 2026-09-27, not archived, MIT. A thin binding to the Rust crate `age` (0.12.1, per the wheel's SBOM), with no Python dependencies and `abi3` wheels from Python 3.10. The judgement rests on the **format, not on the binding**: should the binding be orphaned, every other `age` implementation — the `age` tool, `rage` — still reads the blobs |
| `html2text` | Turns every HTML part of the body of a mail into text in `core/mail.py`, the one module allowed to import it; its version goes into the payload as `body.converter` | `inscriptis` 2.7.5 loses the marking of a quote and brings `lxml` and `requests`; `beautifulsoup4` 4.15.0 splits a signature and table cells into units of their own — both measured on 2026-10-06 against six invented HTML mails, in the plan `docs/superpowers/plans/2026-10-06-pilot-imap-aufnahme.md`. None of the three fetches anything from the network while converting | 2026-10-06, **released rarely, judgement: finished, not abandoned**, like `hatch-vcs` — 2025.4.15 on 2025-04-15, before that 2024-02-27 and 2024-02-25, 38 releases; repository `Alir3z4/html2text` last pushed 2025-10-28, not archived, 99 open issues. No dependencies, ships `py.typed`. GPL-3.0-or-later, which section 13 of the AGPL lets this project combine with; the first runtime dependency under a strong copyleft (`psycopg` is LGPL-3.0-only), accepted by the maintainer on 2026-10-06. Should it be orphaned, the converter is one function in `core/mail.py`, and `inscriptis` is the replacement measured. One setting is not optional: without `unicode_snob` it writes the entity `&uuml;` as `u`, measured on 2026-10-06 |
| `pyrage-stubs` | Types for `pyrage`, for pyright strict; the wheel of `pyrage` ships no `py.typed` and no `.pyi` (checked against its `RECORD`) | — | 2026-10-05, active — 1.4.0 on 2026-08-23, the same day as `pyrage` 1.4.0, out of the same repository; MIT. Only for type checking |
| `types-boto3-lite[s3]` | Types for `boto3` and its S3 client, for pyright strict; neither `boto3` nor `botocore` ships a `py.typed` | `types-boto3[s3]`, the full flavor: under strict mode `boto3.client` is "partially unknown" with it, because its overloads point into the unknown for every service that is not installed; with `lite` and `pyrage-stubs` pyright reports nothing. Both halves are the measurement of 2026-10-04 against a draft of the adapter, recorded in the header of `docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/blob_spike.py`; not repeated here. What was measured on 2026-10-05 is only that the tree, with `lite`, reports 0 errors under strict mode | 2026-10-05, active — 1.43.108 on 2026-10-02, generated daily; MIT. Brings `types-boto3-s3` (1.43.106, 2026-09-30), `botocore-stubs` (1.43.67, 2026-08-08) and `types-s3transfer` (0.16.0, 2025-12-08). Only for type checking |

**Not in the plan's dependency table.** `linkify-it-py` is the eighth new
dependency, found by running `make -C docs html`, not by review: the
Sphinx build failed with `ModuleNotFoundError: Linkify enabled but not
installed.` The plan's table in task 1, step 2 covers seven packages and
says they were already checked; this one was checked the same way and on
the same day, for the same reason it was missing — running the build is
what surfaced it.

**`rustfs/rustfs:1.0.1` is no package, and a dependency of the tests all the
same.** `tests/conftest.py` starts it as the S3 server the blob tests run
against, through the generic container of the `testcontainers` already
listed, with no module of its own; the image is named there as a literal, like
`postgres:17`. Checked on 2026-10-05: the tag was pushed to Docker Hub on
2026-10-03; the repository `rustfs/rustfs` is Apache-2.0, pushed 2026-10-04
and not archived. A release two days old is enough for tests, and measured it
carries the whole blob path. The store of the operation is a different one —
an S3 service of the hosting provider —, and what is different there only
operation will show. MinIO, the obvious choice, is out: checked on
2026-10-05, its repository `minio/minio` is archived and Docker Hub answers
404 for its image `minio/minio`.

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
