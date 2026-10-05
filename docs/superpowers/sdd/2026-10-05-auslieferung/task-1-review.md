### Spec Compliance

Held against `task-1-brief.md` as amended by rulings P-1, P-2 and T1-a to T1-e in `progress.md`.

- ✅ Move with history: every file under `src/previously/migrations/` is a `git mv` rename; `dsn.py` (96 %) and `env.py` (98 %) are the only renames with content changes. The root `migrations/` no longer exists.
- ✅ `src/previously/migrations/__init__.py:1-9` — licence header, docstring names `script_location = previously:migrations`.
- ✅ `src/previously/migrations/env.py:6` imports `previously.migrations.dsn`. `git grep -n "from migrations\|import migrations"` outside `docs/superpowers/` finds nothing; no test, `tests/__init__.py` or `docs/conf.py` relies on the repository root being on `sys.path`.
- ✅ `alembic.ini:8` `script_location = previously:migrations`; `prepend_sys_path` removed (T1-e). Measured from the repository root: `uv run alembic heads` → `0004_event_blob (head)`, `uv run alembic history` lists all four revisions.
- ✅ `pyproject.toml:140-145` pyright `include = ["src", "tests"]`, comment rewritten and true. `pythonpath = ["."]` removed; the report's measurement (full suite green without it) is consistent with the absence of any root-relative import.
- ✅ `pyproject.toml:157-162` (T1-c): `source = ["src/previously"]`. The comment checks out against the installed code: `alembic/util/pyfiles.py:109` builds `module_id = re.sub(r"\W", "_", filename)` and `script/base.py:550`/`:1039` load `env.py` and the revisions through it; `coverage/inorout.py:458-467` admits a frame by module name when `source` is a package name. P-2: both numbers reported (98.40 % before, 97.99 % after), nothing excluded.
- ✅ `.importlinter:9-16`: `previously.core | previously.migrations` as the second layer (`|` = independent siblings), `migrations` above `storage`. `uv run lint-imports`: 6 kept, 0 broken, and the first line printed is exactly `Layers: core beside migrations, both above storage, contract below all KEPT`, which is what `module-boundaries.md:92` quotes. No other page or test quotes the layers contract name (`git grep "Layers:"`). `core-is-clean` unchanged.
- ✅ `tests/test_migrations_dsn.py` imports and docstring on the new path.
- ✅ `tests/test_docs_references.py:37,65` — `SOURCE_DIRS = ["src", "tests"]`, `OUTPUT_DIRS = ["src"]`; comments name the new place. The remeasured count at `:57-58` is right: `grep -rno "§" tests --include=*.py` gives seven occurrences in three files (`test_contracts.py` 1, `test_properties.py` 4, `test_schema.py` 2), all in docstrings or comments — and it was already seven at `934a9a3`, so "nine" had been wrong before this task.
- ✅ `CLAUDE.md` — four places changed, all covered by the brief and T1-e: *Language* (`:11-14`), *Documentation* (`:279`), and only the path list in the two census commands (`:434`, `:495`). `grep -rEo '\b(W|G|B|K|N)-?[0-9]+\b' --include='*.py' src tests` → 105 lines, the same count the old command gives over `934a9a3` with `migrations` (git grep, 105); the revisions now appear as `src/previously/migrations/versions/0001_log.py:K1` etc. `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter | sort -u` → 41 lines, no error. The surrounding text claims no count either command contradicts.
- ✅ `DEPENDENCIES.md:32,41` — both rows name the second use. `uv.lock` confirms hatchling 1.32.4 uploaded `2026-09-20T22:48:45Z`; `.venv/.../hatchling/py.typed` exists.
- ✅ `docs/how-to/add-a-migration.md:13-14` — paths on `src/previously/migrations/versions/`.
- ✅ `docs/explanation/design-records.md:91` left as the brief ordered (but see Minor 1).
- ✅ `tests/test_wheel.py` — verbatim from the brief. Mutation re-measured without touching the tree: building with `WheelBuilder(root, config=…)` and `exclude = ["src/previously/migrations/versions/0004_event_blob.py"]` produced a wheel with 0001–0003 only, so the loop's assertion on `0004_event_blob.py` fails and names it; the unmutated build contains `README`, `__init__.py`, `dsn.py`, `env.py`, `script.py.mako` and all four revisions, no `__pycache__`. Focused run: `1 passed in 0.19s`. It needs git metadata (hatch-vcs → setuptools-scm); the CI checkout (`actions/checkout`, shallow, no tags) yields a `0.1.devN` version and the build succeeds — measured here `previously-0.1.dev167`. Outside a git checkout (a source tarball) it would fail with setuptools-scm's lookup error; nothing in this project runs the suite there. Not flaky, not slow; `git status --short` stays clean after the build.
- ✅ T1-a: tutorial block (`record-your-first-event.md:196-238`) retyped as a whole. Per-file counts held against `uv run pytest --collect-only -q`: identical for all 32 files, total 645; every percentage is the floored cumulative share of 645.
- ✅ T1-b: `module-boundaries.md` — five modules; the order permits nine edges between distinct modules (cli 4, core 2, migrations 2, storage 1; none inside the shared layer); seven exist; the missing two are `cli → migrations` and `migrations → contract`. Rerunning the five greps reproduces the block at `:57-77` exactly. Five external arrows in the diagram, matching the caption. Both gate blocks carry the new name.
- ✅ T1-d: no `__init__.py` in `versions/`; the page states the gap (`:106-108`) for task 5's map entry.
- ✅ Commit trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`, no `Co-Authored-By`.
- ⚠️ Cannot verify from the diff: the BROKEN block at `module-boundaries.md:309-314` (`(l.63)` and the blank line after the header) — it was retyped from a probe I was not allowed to repeat. The gates other than `lint-imports` and the focused tests were not rerun (by instruction).
- ⚠️ "T1-f" is cited twice in the report as a controller ruling that accepted two edits outside the brief (`tests/test_docs_references.py` count, `docs/reference/configuration.md:14`). No `Ruling T1-f` line exists in `progress.md`. Both edits are correct on their merits; see Minor 4.

### Strengths

- The coverage change was diagnosed down to the line in Alembic and coverage rather than papered over with an exclusion, and the committed comment says exactly what was measured.
- `module-boundaries.md` keeps the history honest: the old contract name is quoted with the date it changed, and the seventh edge is explained as older than its module rather than as new.
- The "nine" paragraph-sign count was wrong before this task; the implementer recounted instead of carrying it over.
- The probe for "sharing a layer forbids both directions" also showed the second contract breaking through `migrations.dsn → alembic` — a measurement the page now carries.
- `alembic revision` was run against the new `script_location` to confirm the how-to's path, and the probe file removed.

### Issues

#### Critical

None.

#### Important

1. **`.importlinter:53` — the gate now prints a false claim: `Only storage imports sqlalchemy`.**
   What: until this commit, `storage` held the only `sqlalchemy` imports in the `previously` package. Since the move, `src/previously/migrations/env.py` and all four revisions import it inside the root package, and `module-boundaries.md:37` draws `migrations --> sqlalchemy` five lines above the block (`:94`) where the gate says only `storage` does.
   Why: `CLAUDE.md` (*Language*) and `module-boundaries.md:9` treat contract names as program output and as part of the design; the task renamed the layers contract for exactly this reason and left this one, which the same move made untrue. The contract still checks what it should (sources are `core` and `contract`), so no gate is red — this is the kind of failure that "looks like competent work".
   How: rename it to what it checks (for example `core and contract import no sqlalchemy`), then follow in `tests/test_contracts.py:156` (asserts the name) and retype `module-boundaries.md:94` from a run, with a dated sentence like `:103`; the historical blocks at `:179`/`:184` stay. If the controller prefers to keep this task narrow, a ruling that defers it with an entry for task 5's map is the alternative — but it should not stay silent.

#### Minor

1. **`docs/explanation/design-records.md:91` and `:101` — two statements on a maintained page that the move made untrue.**
   `:91` says "`src/`, `tests/` and `migrations/`, the directories `tests/test_docs_references.py` walks" in the present tense; the test walks `src/` and `tests/` now. `:101` gives a runnable command, `grep -rn "§" src tests migrations | grep -v …`, which now writes `grep: migrations: No such file or directory`.
   The brief protected `:91` as a dated measurement, and both are dated; but a half-sentence ("the migrations have lived under `src/` since later that day") would keep them true without touching the measurement, the way `tests/test_docs_references.py:223` was handled. Controller's call.
2. **`pyproject.toml:85` — the isort comment names "the separation of `cli` → `core` → `storage` → `contract`".** Not false, but incomplete now that a fifth module sits in the second layer. One word fixes it.
3. **`docs/explanation/module-boundaries.md:106-109` — the new `versions/` paragraph runs into the older sentence "The second and third lines read `KEPT (2 ignored imports)` until 2026-10-04."** There is no blank line between `:108` and `:109`, so "the second and third lines" now reads as a continuation of the paragraph about revisions. Insert a blank line before `:109` (or move the new paragraph after the old one).
4. **`progress.md` — "T1-f" has no `Ruling T1-f` line.** The report cites it as the controller's acceptance of two edits outside the brief. This is the controller's ledger, not the implementer's diff, but a ruling cited in a report that the ledger does not hold is the unresolvable-label problem `CLAUDE.md` describes. Record it.

### Assessment

**Task quality:** Needs fixes — the move is complete and every number I rechecked holds (edges, counts, census, tutorial, coverage reasoning, wheel mutation), but the move made the gate-printed name `Only storage imports sqlalchemy` false and the task left it; rename it or defer it by ruling.
