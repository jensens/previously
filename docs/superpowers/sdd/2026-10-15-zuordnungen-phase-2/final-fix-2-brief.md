# Fix round F2 — readers read the projection only (ruling F-c, F-d)

Branch `worktree-zuordnungen-2`, base `a4c04f2`, PR #26 open (phase 2 of the assignments plan, `docs/superpowers/plans/2026-10-15-zuordnungen-phase-2.md`). Read `progress.md` in this directory, section "After the PR opened", rulings F-c and F-d: they are your requirements. Read `CLAUDE.md` in the repo root before you start; its rules bind you (English in code, no `# type: ignore`, no new `noqa`, no mocks for time/DB/randomness, assurances measured to fail, "a comment is a claim", documentation follows in the same change, plone-doc-style for docs).

## The decision, in short

Today a reader of the graph (CLI `_reader_catch_up`/`_reader_graph` around `src/previously/cli.py:3478-3510`, MCP `caught_up`/`read_graph` at `src/previously/mcp_server/server.py:931-963`) catches up the projection and falls back to `read_graph(log, conn)` — the whole fold — on any `PreviouslyError`/`StorageError` of the catch-up, and when `projection_stands` fails. And `catch_up` (`src/previously/core/projection/worker.py:85`) truncates and rebuilds whenever the state row is missing or at another version, whoever calls it.

After this round:

1. **Only `previously project` rebuilds.** `catch_up` gets a keyword-only switch (name it well, e.g. `rebuild: bool`), and every caller other than `_cmd_project` passes the value that forbids a rebuild: the CLI readers, the MCP server, and `redact`'s `_catch_up_after` (`cli.py:1334`). A forbidden rebuild (no state row, or another version) raises a `PreviouslyError` subclass in `core/errors.py` whose sentence says what was found, what this code declares, and that `previously project` builds it. Decide whether `ProjectionRebuilt` covers it or a new class is clearer; argue it in the report. `redact` already turns a failed catch-up into its "outstanding" sentence — check that sentence still reads right.
2. **No reader falls back to the whole fold.** Remove the fallback in the CLI and the MCP server. A catch-up error propagates: the CLI's `main` turns a `PreviouslyError` into its sentence and exit code, as for any other; over MCP it becomes the tool error the server gives any `PreviouslyError` (find how). A `StorageError` goes the way a `StorageError` goes everywhere else. Nothing about the projection is logged as a warning and swallowed any more.
3. **One retry for a rebuild in between.** Where `projection_stands` fails (same version rebuilt or emptied by `project` between the reader's catch-up and its snapshot), the reader leaves that snapshot, catches up once more, opens a new snapshot and checks again. A second miss raises (a clear sentence). Exactly one retry; make the count a named constant with a comment saying why one.
4. **The MCP server checks before it serves.** Where the server is built with the projection, it catches up once (no rebuild) before serving; failing that, it refuses to start with the sentence. The readiness probe (`ready` in `mcp_server/auth.py:96`, find where it is wired) reports not ready while the graph projection is not at this code's version. Keep `/healthz` cheap: one read of the state row, not a catch-up.
5. **The misleading warning** (map: a role without write access to the projection tables is told the schema is incomplete) must be gone for good: whatever a role without privileges now gets must not misname the cause. Measure it: a role with SELECT only on the projection tables, in testcontainers, and type what it gets into the report.
6. **Kept, and documented as not a fallback:** the whole fold for `verify`, `project --check`, `--as-of`, and the write path. Do not touch those paths.

Residuals (ruling F-d), in the same round:
- `docs/superpowers/landkarte.md` (around line 574) states line counts of `cli.py` and `server.py`; recount at your final HEAD (`wc -l`), or better, drop the figure if the sentence holds without it.
- `docs/explanation/module-boundaries.md:425` says the graph tables "hold no content": add the period dates (compare how `projections.md:10` words it).

## Tests

- Remove or rewrite the tests that pin the fallback (grep `folds the log`, `fallback`, `rebuilt since`, `could not be caught up` in `tests/`). Do not leave a test that asserts the old behavior under a new name.
- New assurances, each **mutated and measured red**, each with a control measured green, and the mutation written into the report:
  - a reader (CLI and MCP) meeting another version fails with the sentence and **leaves the projection's tables and state row untouched** (mutate: let it rebuild);
  - a reader meeting no state row fails likewise;
  - `previously project` still builds from scratch and still rebuilds on a version change;
  - a rebuild between catch-up and snapshot is retried once and the read then succeeds (mutate: zero retries);
  - two misses fail (mutate: retry twice — the test must still pin "once", so construct the case so that a second retry would succeed and the assertion is that it is not taken);
  - `ProjectionGap` reaches the caller as an error (CLI exit code and MCP tool error), not a fold;
  - the MCP server refuses to start without a usable projection, and readiness is false while the version differs;
  - `redact` does not rebuild.
- Real PostgreSQL via testcontainers as everywhere; no mock of the database, time or randomness.

## Documentation (same change)

- `docs/explanation/projections.md`, "How a reader reads it" (about lines 334-378) and wherever it says a reader folds the log on failure: rewrite to the new behavior, with the reason (ruling F-c's why, argued in prose, no ruling label needed in docs).
- `docs/how-to/rebuild-a-projection.md`: who rebuilds now, the rolling-update case (old pods fail graph calls until replaced; run `previously project` in the upgrade step before the new version serves).
- The upgrade/release how-tos (find `cut-a-release.md` and the upgrade guide): an upgrade whose projection version changes, and the first one with migration 0006, runs `previously project` after the migration and before serving.
- `docs/reference/` pages quoting messages: every new or changed sentence quoted where the reference lists messages; `tests/test_docs_references.py` holds quotations against the code.
- The handoff `docs/superpowers/handoffs/2026-10-15-kup6s-graph-phase-2.md` (German is fine there if it is German now; keep its language): the upgrade to this version must run `previously project` after `migrate` and before the server serves; readiness stays false until then; what an operator sees if it is skipped. State it as a requirement with its reason (CLAUDE.md, "Previously demands, the environment provides").
- `docs/superpowers/landkarte.md` (German): strike the misleading-warning point, naming PR #26; add two watch points under the unit they belong to, as observations with thresholds, not planned work: (a) catch-up inside a call after a large import (the first reader pays; the next counter-measure is the write path catching up in its transaction, a `LISTEN/NOTIFY` worker only after that), (b) rebuild time against the upgrade window (35 s at 100k, linear; beyond the window: build the new version beside the old in shadow tables and switch). The maintainer noted mass imports of 10,000 mails are unlikely or very rare — say so.
- Comments and docstrings: every one that says a reader falls back, folds on failure, or "never an error" must follow (`grep -rn "folds the log\|fall back\|falls back\|never an error" src tests docs`). A comment is a claim.
- Retype the tutorial's typed test output from one green run at your final HEAD (`tests/test_docs_typed_output.py` checks `N passed`; retype the block, don't edit a number).

## Gates, all six, before you report

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run pytest --cov --cov-report=term-missing
make -C docs html && make -C docs vale && make -C docs linkcheck
```

## Rules for you

- Do not dispatch subagents.
- Commit with explicit paths (never `git add -A`), English messages, ending with `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `Co-Authored-By`. Do not push.
- If you cite a ruling in code, write `ruling F-c of the 2026-10-15 assignments plan`, one `ruling` per label, and the reason beside it.
- Write your full report to `final-fix-2-report.md` in this directory: what changed per point, the measured mutations (what was mutated, red/green), the privilege measurement, gate output summary, and anything you decided that the brief did not settle. Return only status, commits, one test-summary line and concerns.
