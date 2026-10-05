# Task 1 report: the migrations move into the package

**Status: DONE.** Commit `dadaa95` (`build: the migrations move into the package`). All six gates are green, each run as its own command, and `git status --short` is clean.

The first round ended NEEDS_CONTEXT because the tutorial count turned the pytest gate red.
The controller's rulings T1-a to T1-e resolved that, and this report covers both rounds.

## What changed, file by file

- `migrations/` → `src/previously/migrations/` with `git mv`. The root `migrations/` no longer exists. All files except `dsn.py` and `env.py` are 100 % renames.
- `src/previously/migrations/__init__.py` (new): licence header and a docstring saying what the package is and that Alembic finds it through `script_location = previously:migrations`.
- `src/previously/migrations/env.py`: imports `previously.migrations.dsn`.
- `src/previously/migrations/dsn.py`: the docstring says `import previously.migrations.env`. Remeasured: the import fails with `AttributeError: module 'alembic.context' has no attribute 'config'`, as the docstring claims.
- `alembic.ini`:
  - `script_location = previously:migrations`, with the template comment above it rewritten to describe a package resource.
  - The DSN comment names `src/previously/migrations/dsn.py`.
  - `prepend_sys_path = .` and its template comment are removed (T1-e).
- `pyproject.toml`:
  - dev dependencies gain `hatchling>=1.32` and `hatch-vcs>=0.5`.
  - pyright `include = ["src", "tests"]`, with the comment rewritten.
  - `pythonpath = ["."]` and its comment are removed.
  - `[tool.coverage.run] source = ["src/previously"]`, with the reason beside it (T1-c).
- `uv.lock`: adds hatchling 1.32.4, hatch-vcs 0.5.0, pathspec, setuptools 84.0.0, setuptools-scm 10.3.4, tomlkit, trove-classifiers, vcs-versioning.
- `.importlinter`: `previously.core | previously.migrations` form the second layer, and the contract is renamed `Layers: core beside migrations, both above storage, contract below all`.
- `tests/test_wheel.py` (new): verbatim from the brief.
- `tests/test_migrations_dsn.py`: imports and docstring use the new path.
- `tests/test_docs_references.py`:
  - `SOURCE_DIRS = ["src", "tests"]` and `OUTPUT_DIRS = ["src"]`, with the comment rewritten.
  - The count of paragraph signs in `tests/` was rechecked: "nine" became "seven", counted on 2026-10-05. T1-f accepted this.
  - The fix-round-2 docstring measurement now notes that the migrations lay outside `src/` until 2026-10-05.
- `CLAUDE.md` (four places in total):
  - *Language* and *Documentation*, as the brief named them. The *Language* paragraph was reflowed to keep its wrap.
  - Both census commands (T1-e).
- `DEPENDENCIES.md`: both rows name the second use.
  - `hatchling` was rechecked: 1.32.4 was uploaded on 2026-09-20 (from `uv.lock`) and it ships `py.typed`.
  - For `hatch-vcs` the claim was measured: without it, the in-process build fails with `UnknownPluginError: Unknown version source: vcs`. The venv was restored afterwards with `uv sync --all-extras`.
- `docs/how-to/add-a-migration.md`: the paths point at `src/previously/migrations/versions/`. Measured: `uv run alembic revision -m probe` wrote `src/previously/migrations/versions/50413e9c3689_probe.py`, and the probe was deleted.
- `docs/reference/configuration.md`: names `previously.migrations.dsn.resolve_dsn` (T1-f accepted this).
- `docs/explanation/module-boundaries.md` (T1-b): see point 2 below.
- `docs/tutorials/record-your-first-event.md` (T1-a): see point 1 below.

The following were left alone:
- `core/append.py:121` and `tests/test_migration_0003.py:88`: both give paths relative to the package, so they are still true.
- `design-records.md:91` and `:101`, and `DEPENDENCIES.md:85`: these are dated measurements.

## Point 1 (T1-a): the tutorial

1. The body of the pytest block was replaced with the uncommitted placeholder `PLACEHOLDER: retyped from a green run, claims no count`.
2. `uv run pytest` ran with exit 0: `645 passed in 85.88s (0:01:25)`, seed 3655200436.
3. The whole block was replaced with that run's output by script, dropping only the `rootdir:` line. That covers the session header, `collected 645 items`, every per-file line and the last line. No number was edited by hand.

## Point 2 (T1-b): `module-boundaries.md`

- **Intro.** The page now names five modules, with `cli` above `core` and `migrations`, which share a layer, above `storage` above `contract`. It says when and why `migrations` joined. A short paragraph says what `migrations` is and why it sits beside `core`.
- **Diagram.** It gains `migrations --> storage`, `migrations --> sqlalchemy` and `migrations --> alembic`. The caption reads "seven between its own modules … Five arrows leave the package". The sentence about held arrows now covers `alembic`: forbidden for `core` by `core-is-clean`.
- **Edge count.** The layer order permits nine edges: `cli` 4, `core` 2, `migrations` 2, `storage` 1. No edge runs between `core` and `migrations`, because they share a layer. Seven of the nine exist. The missing two are `cli → migrations` and `migrations → contract`. A sentence on the seventh edge was added.
- **Grep block.** Retyped from runs on 2026-10-05, with a fifth command for `src/previously/migrations`, and dated. The prose claim that two `storage` modules mention `previously.core` only in prose was rechecked: `storage/errors.py:7` and `storage/postgres.py:77`, and there are no `import previously…` statements.
- **Contracts block.** Retyped from a real `uv run lint-imports`, and identical to the final gate run. Two paragraphs were added:
  - The rename, and a measurement that sharing a layer forbids both directions: an import of `migrations.dsn` in `core/units.py` broke the layers contract, and `core-is-clean` too, through `migrations.dsn -> alembic`.
  - The T1-d finding that the contract does not read `versions/`.
- **BROKEN block** (formerly 2026-10-04). Remeasured on 2026-10-05 with a throwaway `from previously.storage.errors import StorageError` in `contract/store.py`. It is retyped with the new contract name and `(l.63)`, and the date is changed to 2026-10-05.
- Every throwaway import was reverted and confirmed with `git status --short`.

## Point 3 (T1-c): coverage

| Measurement | Statements | Missed | Total |
|---|---|---|---|
| Before the move, head `934a9a3`, `source = ["previously"]` | 2121 | 34 | 98.40% |
| After the move, by package name (not committed) | 2156 | 58 | 97.31%, with `env.py` falsely at 0% and the revisions absent |
| **After the move, `source = ["src/previously"]` (committed)** | 2238 | 45 | **97.99%** |

Committed rows for the migrations:

```
src/previously/migrations/__init__.py                           0      0   100%
src/previously/migrations/dsn.py                               11      0   100%
src/previously/migrations/env.py                               24      4    83%   43-51, 84
src/previously/migrations/versions/0001_log.py                 19      3    84%   107-109
src/previously/migrations/versions/0002_projections.py         16      4    75%   62-65
src/previously/migrations/versions/0003_hash_version_2.py      31      0   100%
src/previously/migrations/versions/0004_event_blob.py          16      0   100%
```

The cause was confirmed in Alembic's source. In `alembic/util/pyfiles.py`, `load_python_file` sets `module_id = re.sub(r"\W", "_", filename)` and loads the file through `spec_from_file_location`, so the module is called `env_py`. `script/base.py:550` loads `env.py` that way, and `:1039` loads the revisions the same way.

`relative_files = true` and `[tool.coverage.report]` needed no change. With the path form the report lists every file under `src/previously` with relative names, and `fail_under = 90` passes. Nothing was excluded.

## Point 4 (T1-d): import-linter does not read `versions/`

No change was made in this task.

Measured with two throwaway imports at once: `from previously.cli import main` in `versions/0004_event_blob.py` and `import previously.cli` in `dsn.py`. `lint-imports` reported only `previously.migrations.dsn -> previously.cli (l.21)`, and the dependency count went from 184 to 185, so the revision's edge was not counted. `versions/` has no `__init__.py`.

Both imports were reverted. The finding is now also stated on `module-boundaries.md`, for task 5's map entry.

## Point 5 (T1-e): `CLAUDE.md` census commands and `alembic.ini`

`grep -n "migrations" CLAUDE.md` found exactly the two commands, lines 433 and 494. In each, `migrations` was removed from the path list. Nothing else changed beyond the two places the brief names.

The output of each command after the change, run from the worktree root, is at the end of this report. It has 105 lines and 41 lines respectively. The revisions now show up under `src/previously/migrations/versions/` (K1 and K-1 in 0001 and 0003), and neither command errors.

For `prepend_sys_path = .`, measured without it:
- `uv run alembic heads` → `0004_event_blob (head)`.
- Offline mode, which loads `env.py`: `PREVIOUSLY_DSN=postgresql+psycopg://probe/probe uv run alembic upgrade head --sql` ends with `UPDATE alembic_version SET version_num='0004_event_blob' …; COMMIT;`.
- Online mode: the full suite, whose conftest runs `command.upgrade` in-process, passed 645.

So it is removed.

## Point 6 (T1-f)

The two edits outside the brief are accepted and committed unchanged.

## TDD evidence and mutation (from the first round, unchanged)

- RED before hatchling was installed: `ModuleNotFoundError: No module named 'hatchling'`.
- RED before the move: `AssertionError: assert 'previously/migrations/env.py' in {...}`, `1 failed`.
- GREEN after the move: `1 passed`. pyright reports 0 errors and no `cast` was needed.
- Mutation: `exclude = ["src/previously/migrations/versions/0004_event_blob.py"]` under `[tool.hatch.build.targets.wheel]` produced `AssertionError: assert 'previously/migrations/versions/0004_event_blob.py' in {...}`, `1 failed`.
- After restoring it, the control run gave `1 passed`.

## The `pythonpath` measurement

With the line removed, the full suite showed no `ModuleNotFoundError`. In the first round the only failure was the tutorial count. In the final run everything passed (645). The line stays removed.

## The six gates (final tree, before the commit)

```
uv run ruff check .                              All checks passed!
uv run ruff format --check .                     71 files already formatted
uv run pyright                                   0 errors, 0 warnings, 0 informations
uv run lint-imports                              Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing    645 passed in 85.91s (0:01:25)   Total coverage: 97.99%
make -C docs html                                The HTML pages are in _build/html.
make -C docs vale                                ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
make -C docs linkcheck                           build succeeded.
```

After the gates, two comment reflows were made, with no change of content: `CLAUDE.md` *Language* and the DSN comment in `alembic.ini`. `uv run alembic heads` was rerun and still parses the ini. No gate reads either file as Python.

`git grep -n "from migrations\|import migrations"` finds only the plan itself, which quotes the old import.

## Self-review and remaining concerns

- import-linter does not read `versions/` (T1-d). This is an open point for task 5's map.
- The coverage gaps that remain are real: the offline branch of `env.py`, and the `downgrade()` of 0001 and 0002.
- One phrase in the commit message is loose: "Both suites and alembic were measured without them" means the test suite run and the alembic commands. It is not worth an amend.

## Census output after T1-e

`grep -rEo '\b(W|G|B|K|N)-?[0-9]+\b' --include='*.py' src tests` (105 lines):

```
src/previously/core/hashing.py:K1
src/previously/storage/errors.py:W2
src/previously/storage/errors.py:W2
src/previously/storage/errors.py:W2
tests/test_schema.py:K-1
tests/test_schema.py:K1
src/previously/core/append.py:G-7
src/previously/core/append.py:W3
src/previously/core/append.py:G1
src/previously/core/append.py:G1
src/previously/core/append.py:W-1
src/previously/core/append.py:W2
src/previously/core/append.py:G1
src/previously/core/append.py:N-5
src/previously/core/append.py:N-5
src/previously/core/append.py:W-1
src/previously/core/append.py:N-5
src/previously/core/append.py:W1
src/previously/core/append.py:N-1
src/previously/core/append.py:G-7
src/previously/core/append.py:W3
src/previously/core/append.py:W3
src/previously/migrations/versions/0003_hash_version_2.py:K1
src/previously/migrations/versions/0003_hash_version_2.py:K1
src/previously/storage/postgres.py:W2
src/previously/storage/postgres.py:W2
src/previously/storage/postgres.py:G4
src/previously/storage/postgres.py:W-3
src/previously/storage/postgres.py:K1
src/previously/storage/postgres.py:N2
src/previously/storage/postgres.py:B1
src/previously/storage/postgres.py:K-1
src/previously/storage/postgres.py:W2
src/previously/cli.py:G3
src/previously/cli.py:W2
src/previously/cli.py:G3
src/previously/cli.py:W-1
src/previously/cli.py:G4
src/previously/cli.py:G-1
src/previously/cli.py:W2
src/previously/cli.py:W2
src/previously/cli.py:W2
tests/test_append.py:G-4
tests/test_append.py:W3
tests/test_append.py:G1
tests/test_append.py:G1
tests/test_append.py:N5
tests/test_append.py:N5
tests/test_append.py:W-1
tests/test_append.py:N-5
src/previously/storage/schema.py:K-1
src/previously/core/verify.py:B1
src/previously/core/verify.py:W1
src/previously/core/verify.py:K1
src/previously/core/verify.py:W1
src/previously/core/verify.py:B1
src/previously/core/verify.py:G4
src/previously/core/verify.py:N2
tests/conftest.py:W2
tests/test_canonical.py:N5
tests/test_canonical.py:N5
src/previously/migrations/versions/0001_log.py:K1
src/previously/migrations/versions/0001_log.py:K-1
src/previously/migrations/versions/0001_log.py:K1
src/previously/migrations/versions/0001_log.py:K-1
tests/test_contracts.py:N4
tests/test_contracts.py:G2
tests/test_hashing.py:G-2
tests/test_hashing.py:G-4
tests/test_hashing.py:K1
tests/test_hashing.py:W1
tests/test_hashing.py:W5
tests/test_properties.py:W4
tests/test_properties.py:N3
tests/test_properties.py:W4
tests/test_storage.py:W2
tests/test_storage.py:B1
tests/test_storage.py:N2
tests/test_storage.py:W2
tests/test_storage.py:W2
tests/test_storage.py:W2
tests/test_storage.py:W2
tests/test_storage.py:W2
tests/test_cli.py:W2
tests/test_cli.py:G4
tests/test_cli.py:G-1
tests/test_cli.py:W2
tests/test_cli.py:W2
tests/test_cli.py:W2
tests/test_cli.py:W2
tests/test_cli.py:G3
tests/test_cli.py:G3
tests/test_cli.py:G3
tests/test_cli.py:N1
tests/test_cli.py:W-1
tests/test_cli.py:W2
tests/test_cli.py:W2
tests/test_verify.py:K1
tests/test_verify.py:K1
tests/test_verify.py:K1
tests/test_verify.py:K1
tests/test_verify.py:W1
tests/test_verify.py:B5
tests/test_verify.py:W1
tests/test_verify.py:B1
```

`grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter | sort -u` (41 lines):

```
.importlinter:30:ruling T7-a
.importlinter:31:ruling T8-c
.importlinter:38:Ruling T7-a
.importlinter:38:Ruling T8-c
pyproject.toml:102:ruling T9-c
pyproject.toml:128:ruling T2-e
src/previously/cli.py:169:ruling T9-a
src/previously/cli.py:189:ruling T9-a
src/previously/storage/postgres.py:73:Ruling T6-b
src/previously/storage/postgres.py:819:ruling T9-a
src/previously/storage/s3.py:190:ruling T6-a
tests/test_blob.py:322:Ruling T6-a
tests/test_blob.py:377:Ruling T6-c
tests/test_cli.py:204:ruling P-1
tests/test_cli.py:2080:Ruling T6-a
tests/test_cli.py:2141:Ruling T6-c
tests/test_cli.py:2497:ruling T6-a
tests/test_cli.py:598:ruling P-1
tests/test_projection_store.py:192:ruling P-2
tests/test_projection_worker.py:313:ruling P-1
tests/test_projection_worker.py:377:ruling P-1
tests/test_properties.py:101:ruling T10-c
tests/test_properties.py:147:ruling T10-a
tests/test_properties.py:255:ruling T10-b
tests/test_properties.py:47:ruling T10-d
tests/test_properties.py:56:ruling T10-a
tests/test_redact.py:430:ruling P-1
tests/test_s3.py:219:ruling T5-a
tests/test_s3.py:256:Ruling T6-a
tests/test_schema.py:206:ruling P-1
tests/test_schema.py:268:ruling T5-b
tests/test_sealing.py:184:Ruling T6-c
tests/test_sealing.py:252:Ruling T6-c
tests/test_storage.py:454:ruling T6-b
tests/test_storage.py:514:ruling T6-b
tests/test_verify.py:1143:ruling P-1
tests/test_verify.py:158:ruling P-1
tests/test_verify.py:176:ruling T8-a
tests/test_verify.py:215:ruling T8-a
tests/test_verify.py:235:Ruling T8-b
tests/test_verify.py:905:ruling P-1
```

---

# Fix round 1

**Status: DONE.** Commit `4de9be9` (`fix: the sqlalchemy contract says what it checks`). All six gates are green and `git status --short` is clean.

## Important 1: the sqlalchemy contract name

- `.importlinter`:
  - `name = core and contract import no sqlalchemy`.
  - The section id is also renamed, from `only-storage-knows-sql` to `core-and-contract-know-no-sql`. The old id stated the same falsehood, and `git grep` found no reference to it outside `docs/superpowers/`.
  - A dated comment under the contract says why it was renamed and that the contract itself did not change: its sources were always `core` and `contract`.
- `tests/test_contracts.py:156` asserts `"core and contract import no sqlalchemy BROKEN"`.
- `docs/explanation/module-boundaries.md`:
  - The gate block is retyped from a fresh `uv run lint-imports`, and is identical to the gate-4 output below.
  - Two sentences say what the third line read until 2026-10-05, and why. The historical blocks at `:179`/`:184` keep the name of their day, and the page says so.
- `git grep -n "Only storage imports"` outside `docs/superpowers/{specs,plans,sdd}` now finds four lines, and every one of them quotes the old name as history: the two historical blocks at `module-boundaries.md:183` and `:188`, the new dated sentence at `module-boundaries.md:104`, and the dated comment at `.importlinter:68`.

Covering test, with a measured mutation:
- `uv run pytest tests/test_contracts.py -q -p no:randomly` → `4 passed in 0.55s`.
- With `name = Only storage imports sqlalchemy` restored in `.importlinter`, the same run gives `E  assert 'core and contract import no sqlalchemy BROKEN' in '…previously.core._violation -> sqlalchemy (l.1)…'` and `1 failed, 3 passed in 0.56s`.
- Restored: `4 passed in 0.56s`.

## Minor 1: `design-records.md`

- `:91` now reads "the directories `tests/test_docs_references.py` walked until the migrations moved under `src/` on 2026-10-05". The measurement itself is unchanged.
- `:101` keeps the command of that day, and its verb is now in the past ("printed nothing"). A new sentence gives the command after the move, `grep -rn "§" src tests | grep -v "frozen design record"`, which was measured to print nothing.
- The claim of the same fifteen lines in the same seven files was rechecked: `grep -rn "§" src tests | wc -l` → 15, and `grep -rl` lists the same seven files as `git grep -c "§" 934a9a3 -- src tests migrations` (1+2+1+4+1+4+2).

## Minor 2: the isort comment in `pyproject.toml`

The comment now reads "`cli` → `core` | `migrations` → `storage` → `contract`, where `core` and `migrations` share a layer and import nothing from each other".

"Import nothing from each other" was measured in both directions:
- `from previously.migrations.dsn import ENV_VAR` in `core/units.py` broke the layers contract. That was measured in the first round.
- New this round: `import previously.core.units` in `migrations/dsn.py` broke it with `previously.migrations is not allowed to import previously.core: - previously.migrations.dsn -> previously.core.units (l.21)`. The probe was reverted and checked with `git status --short`.

`module-boundaries.md` claimed both directions but showed only one, so it now carries the second measurement in one sentence.

## Minor 3

A blank line now separates the `versions/` paragraph from "The second and third lines read `KEPT (2 ignored imports)` until 2026-10-04" on `module-boundaries.md`.

## The six gates (final tree)

```
uv run ruff check .                              All checks passed!
uv run ruff format --check .                     71 files already formatted
uv run pyright                                   0 errors, 0 warnings, 0 informations
uv run lint-imports                              Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing    645 passed in 88.53s (0:01:28)   Total coverage: 97.99%
make -C docs html                                The HTML pages are in _build/html.
make -C docs vale                                ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
make -C docs linkcheck                           build succeeded.
```

The test count is unchanged at 645, so the tutorial block from `dadaa95` still holds. `test_docs_typed_output` was green in the run above.

## Concerns

None new. The T1-d gap (import-linter does not read `versions/`) stands for task 5's map.
