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
| `anthropic` | The Anthropic client in `gate/adapters/anthropic.py`, the one module allowed to import it ([About the module boundaries](docs/explanation/module-boundaries.md)) | calling the HTTP API by hand would mean our own request and error handling for a provider whose parameters (`output_config`, `inference_geo`) the SDK already types | 2026-10-09, active — 1.13.0 on 2026-10-09, 226 releases; repository `anthropics/anthropic-sdk-python` pushed 2026-10-09, not archived, MIT; ships `py.typed`. Brings `pydantic` (2.14.0, 2026-10-08), `httpx2` (2.13.1, 2026-09-23, 18 releases; the HTTP client both SDKs now depend on; repository `pydantic/httpx2`), `anyio`, `jiter`, `sniffio`, `docstring-parser` and `typing-inspection`. Built with `max_retries=0`: the gate records every attempt |
| `openai` | The client for OpenAI-compatible endpoints in `gate/adapters/openai_compatible.py`, the one module allowed to import it; it serves Mistral and a local Ollama | `mistralai`, the vendor's own client, would add a second dependency for what the OpenAI-compatible endpoint does measured on 2026-10-09 (`mistral-small-2603`), and Ollama has no other SDK worth the name | 2026-10-09, active — 3.27.0 on 2026-10-09, 445 releases; repository `openai/openai-python` pushed 2026-10-09, not archived, Apache-2.0; ships `py.typed`. Shares its transitive dependencies with `anthropic`. Built with `max_retries=0` |
| `pydantic` | The output schema of a task of the gate, in `gate/task.py` and `gate/tasks/`: `model_json_schema` is the schema a provider is asked to keep, and `model_validate_json` is the check the gate makes of every answer itself | `jsonschema` would need stubs for pyright strict, and a second description of each output beside the code that reads it | 2026-10-09, active — 2.14.0 on 2026-10-08, 207 releases; repository `pydantic/pydantic` pushed 2026-10-09, not archived, MIT; ships `py.typed`. Installed since 2026-10-09 as a dependency of `anthropic` and `openai`, and declared since the same day, when `src/` first imported it |
| `mcp` | The MCP server in `mcp_server/server.py`, the one module allowed to import it ([About the module boundaries](docs/explanation/module-boundaries.md)); `MCPServer` serves the revisions `2026-07-28` and `2025-11-25` from one endpoint with `stateless_http=True`, measured on 2026-10-09 (`docs/superpowers/recherche/2026-10-10-mcp-messungen.md`, M1) | FastMCP 4.1.0 builds on this SDK and adds 40 packages the read access does not use (68 against 28, measured on 2026-10-09 with `uv pip install --dry-run`), its type gate is `ty` with error classes switched off rather than pyright; writing the protocol by hand would rebuild both eras, header routing and the host check, which the SDK proves in its conformance runs (`docs/superpowers/recherche/2026-10-09-mcp-stand-und-designgrundlagen.md`, section 7) | 2026-10-11, active, **one maintainer carries it** — 2.3.0 on 2026-10-02, 73 releases, the 2.x line since 2026-07-28 and 1.x on security fixes; repository `modelcontextprotocol/python-sdk` pushed 2026-10-05, not archived, MIT; 84 of the last 100 commits by one person (`maxisbey`, employed by Anthropic to maintain it), 5 by `Kludex` — recount at every check. Ships `py.typed` and runs pyright strict over its own source; pyright strict over a minimal server under this project's configuration reported 0 errors on 2026-10-09 (M2). Brings `mcp-types` (2.3.0, in lockstep), `starlette`, `sse-starlette`, `uvicorn`, `httpx2`, `jsonschema`, `pyjwt[crypto]`, `python-multipart`, `opentelemetry-api` and `pydantic`. Its `TokenVerifier` is not used: with `auth=` it would publish Protected Resource Metadata, which the read access must not do while there is no authorization server, so `mcp_server/auth.py` checks the bearer token in an ASGI wrapper of its own |
| `uvicorn` | Runs the ASGI app of `previously serve`, started in `mcp_server/server.py`, the one module allowed to import it; declared because `src` imports it directly, although `mcp` brings it too, the rule `starlette` and `botocore` follow as well | `hypercorn` would be a second server beside the one the SDK already depends on (`uvicorn>=0.31.1`), for nothing the single process of the pilot needs | 2026-10-11, active — 0.54.0 on 2026-09-25, 204 releases; repository `Kludex/uvicorn` (formerly `encode/uvicorn`) pushed 2026-10-10, not archived, BSD-3-Clause; 73 of the last 100 commits by its maintainer `Kludex`, who also maintains `starlette`. Ships `py.typed`. Brings `click` and `h11` |
| `starlette` | The HTTP side of the MCP server: `mcp_server/server.py` checks that a request is a Starlette `Request` before it reads the client the token named, and adds the token check to the app; `mcp_server/auth.py` types the ASGI wrapper with it. Declared on 2026-10-11 because `src` imports it directly, although `mcp` brings it too | an ASGI type of our own and duck typing would avoid the import, but `build_app` returns the SDK's Starlette app and adds a middleware to it through Starlette's own method, so the dependency would stay, only unnamed | 2026-10-11, active — 1.7.0 on 2026-09-23, 203 releases; repository `Kludex/starlette` (formerly `encode/starlette`) pushed 2026-10-09, not archived, BSD-3-Clause; 60 of the last 100 commits by its maintainer `Kludex`, who maintains `uvicorn` too. Ships `py.typed` |
| `botocore` | The exceptions and the client configuration of the S3 client in `storage/s3.py`, the one module allowed to import it beside `boto3`. Declared on 2026-10-11, when the rule that every package `src` imports directly is declared was applied to the whole tree: it had come in through `boto3` alone since 2026-10-05 | — | 2026-10-11, active — 1.43.111 on 2026-10-09, the lock holds 1.43.108; 2533 releases, the same rhythm as `boto3`; repository `boto/botocore` pushed 2026-10-09, not archived, Apache-2.0. Ships no `py.typed`; its types come from `botocore-stubs` through `types-boto3-lite[s3]` |
| `anyio` | Runs the tests of the MCP server (`tests/test_mcp_server.py`): the SDK's clients are coroutines, and `anyio.run` drives them from a plain test function. In the `test` group. `src` uses `asyncio` from the standard library instead and imports no `anyio` | the `pytest` plugin of `anyio` would need each of these tests written as a coroutine; with `anyio.run` they stay plain functions like the rest of the suite | 2026-10-11, active — 4.15.1 on 2026-09-05, 72 releases; repository `agronholm/anyio` pushed 2026-10-11, not archived, MIT; 25 of the last 100 commits by its maintainer `agronholm`, most of the rest automated. Ships `py.typed`. Installed since 2026-10-09 through the vendor SDKs |
| `httpx2` | The HTTP client of the tests that call the app of `previously serve` in the same process, through its ASGI transport (`tests/test_mcp_server.py`). In the `test` group | a server on a real port in the test would need a free port and a second thread or process, and the SDK's own client takes an `httpx2` client | 2026-10-11, active — see the `anthropic` row: 2.13.1 on 2026-09-23, 18 releases, repository `pydantic/httpx2` pushed 2026-10-08, not archived, BSD-3-Clause. Ships `py.typed`. Its youth, five months, is the risk to watch; the SDKs of the gate and of MCP both depend on it |
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

**`pydantic` went and came back.** It stood in this table until 2026-10-03
with "validation of payloads" as the purpose, and nothing imported it: the
validation of stage 1a is done by hand in `core/canonical.py`. A declared but
never imported dependency is the zombie in its purest form (§10.7 of the
architecture), so it went, to come back with a user. The one foreseen then
was the schema export of the MCP interface (§8.6 of the architecture); the
one that brought it back on 2026-10-09 is the gate, whose tasks describe
their output as a pydantic model. The ruff entry the return needed,
`runtime-evaluated-base-classes = ["pydantic.BaseModel"]`, came with it:
without it ruff moves the `BaseModel` imports under `TYPE_CHECKING`, and
pydantic fails at runtime.

**No library for JCS.** The permitted payload range is so restricted (no
floating point numbers, ASCII keys, integers inside the safe range) that
`json.dumps` with fixed flags is canonical already — see `core/canonical.py`.
Getting rid of a dependency is better than checking it.
