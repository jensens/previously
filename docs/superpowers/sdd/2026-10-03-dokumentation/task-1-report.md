# Task 1 report — Werkzeugkette, Makefile und das sechste Tor

Status: **DONE**
Commits: `9f2804a` — `docs: a Sphinx toolchain and a sixth gate`;
`fefe40c` — `docs: colon fences so Vale actually checks the grid cards`
Branch: `worktree-dokumentation`, worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`

## Fix round 1 — Vale's backtick blind spot

Reviewer finding (medium severity, accepted): Vale treats any backtick-fenced
block as a code block and skips its content outright, even when a MyST
directive is inside and the content is prose, not code. Measured at
`docs/index.md:42`: "does not cover" sat inside a ```` ```{grid-item-card} ````
fence and passed `make -C docs vale` silently, while the same expression
outside a fence (in `docs/explanation/index.md`) had already been corrected
to "doesn't" in the original task — i.e. the gate was checking some prose and
silently skipping other prose on the same page, with no signal that it had
skipped anything.

**Fix:** convert every directive that carries prose from backtick fences to
colon fences (`colon_fence` is already enabled in `conf.py`), outer fence
with more colons than any nested one, matching how backtick nesting already
works (`::::{grid}` wrapping `:::{grid-item-card}`). Code blocks are
unaffected — none of the five pages had one, so there was nothing to leave
alone, but the rule (kept backticks for code) is now in the plan's Global
Constraints for the seven following tasks.

**Scope checked:** all five pages task 1 wrote. Only `docs/index.md` had a
directive with prose in it — one `{grid}` plus four `{grid-item-card}`, all
converted. The four quadrant `index.md` files have only an empty `{toctree}`
(no prose) and left as backticks; there was nothing in them to be in a blind
spot.

**Vale output before the fence conversion** (backtick fences, the state
task 1 ended in):

```
✔ 0 errors, 0 warnings and 0 suggestions in 5 files.
```

**Vale output right after the fence conversion**, wording still
unchanged ("does not cover"), to actually observe the catch rather than
assume it:

```
 docs/index.md
 42:88  error  Use 'doesn't' instead of 'does not'.  Microsoft.Contractions

✖ 1 error, 0 warnings and 0 suggestions in 5 files.
```

One spot came out of the blind spot: `docs/index.md:42`. Fixed the same way
as the first round ("does not" → "doesn't", meaning unchanged):

```
✔ 0 errors, 0 warnings and 0 suggestions in 5 files.
```

**`make -C docs html` after the conversion:** still ends in "build
succeeded." with no warning line. Checked at the HTML, not the silence, same
as the first round: `docs/_build/html/index.html` has exactly 4 `sd-card`
elements inside 1 `sd-row`, and all four card titles ("Tutorials", "How-to
guides", "Reference", "Explanation") are present. `make -C docs linkcheck`
still succeeds (still nothing to check). The five pre-existing gates were
re-run after this change and are unchanged green (187 passed, 99.80%
coverage, ruff/pyright/lint-imports clean).

`docs/superpowers/plans/2026-10-03-dokumentation.md`'s Global Constraints
and its new "Warum Doppelpunkt-Fences" section were already modified in the
working tree when this fix round started — not by me, and outside task 1's
file list, so I left that file alone.

## 1. `make -C docs html`

Run against a clean `_build/` (`rm -rf docs/_build && make -C docs html`).
Full tail of the output:

```
reading sources... [ 20%] explanation/index
reading sources... [ 40%] how-to/index
reading sources... [ 60%] index
reading sources... [ 80%] reference/index
reading sources... [100%] tutorials/index

looking for now-outdated files... none found
pickling environment... done
checking consistency... done
preparing documents... done
copying assets...
copying static files...
copying extra files...
copying assets: done
writing output... [ 20%] explanation/index
writing output... [ 40%] how-to/index
writing output... [ 60%] index
writing output... [ 80%] reference/index
writing output... [100%] tutorials/index

generating indices... genindex done
writing additional pages... search done
dumping search index in English (code: en)... done
dumping object inventory... done
build succeeded.

The HTML pages are in _build/html.
```

**No warning line anywhere in the log** — `checking consistency... done` has no
`toc.not_included` entries, i.e. the three still-empty quadrant index pages
(`tutorials`, `how-to`, `reference` beyond the worked example, `explanation`)
did **not** trigger "document isn't included in any toctree", because
`docs/index.md`'s hidden toctree already lists all four. The brief
anticipated having to strip the empty `{toctree}` directive from the three
bare index pages if this warning showed up — it did not show up, so I left
those directives in place. Nothing for task 2 to re-add.

I verified the four landing-page cards actually render (not just "no
warning"): `grep` on `_build/html/index.html` finds exactly 4
`sd-card` elements and one `sd-row` wrapper, with the text "Tutorials",
"How-to guides", "Reference", "Explanation" each present once.

## 2. `make -C docs vale`

```
cd .. && test -d .vale-styles || uv run --extra docs vale sync
cd .. && uv run --extra docs vale docs/index.md docs/tutorials docs/how-to docs/reference docs/explanation
✔ 0 errors, 0 warnings and 0 suggestions in 5 files.
```

First run from a clean checkout (no `.vale-styles/`) printed, before that
final line:

```
* vale not found. Downloading it...
* Detected architecture: 64-bit
* https://github.com/errata-ai/vale/releases/download/v3.22.0/vale_3.22.0_Linux_64-bit.tar.gz downloaded to ...
* Copying ... to .../vale/vale_bin
* vale extracted and copied to module path.
Syncing Microsoft [1/1] ██████████████████████████████████████████████ 100% | 0s
 SUCCESS  Synced 1 package(s) to '.../.vale-styles'.
```

Second run (the one quoted above) skipped straight to the vale call —
confirms the cache guard works. Before the two wording fixes below, this
same command reported:

```
 docs/index.md
 4:112  error  Use 'can't' instead of 'cannot'.  Microsoft.Contractions

 docs/explanation/index.md
 3:53  error  Use 'doesn't' instead of 'does not'.  Microsoft.Contractions

✖ 2 errors, 0 warnings and 0 suggestions in 5 files.
```

## 3. `make -C docs linkcheck`

```
build succeeded.

Look for any errors in the above output or in _build/linkcheck/output.txt
```

Task 1's content has no external links yet (those arrive with later tasks'
content, and `conf.py`'s `linkcheck_ignore` is already in place for them), so
this is a clean pass with nothing to actually check — worth saying plainly
rather than letting "build succeeded" imply more coverage than it has.

## 4. The step-8 test, red then green

**Before step 10** (quadrant index pages did not exist yet),
`uv run pytest tests/test_docs_build.py -v`:

```
FAILED tests/test_docs_build.py::test_every_quadrant_has_an_index[how-to] - AssertionError: assert False
 +  where False = is_file()
 +    where is_file = ((PosixPath('.../docs') / 'how-to') / 'index.md').is_file
FAILED tests/test_docs_build.py::test_every_quadrant_has_an_index[reference] - AssertionError: assert False
FAILED tests/test_docs_build.py::test_every_quadrant_has_an_index[explanation] - AssertionError: assert False
FAILED tests/test_docs_build.py::test_every_quadrant_has_an_index[tutorials] - AssertionError: assert False
========================= 4 failed, 2 passed in 0.11s ==========================
```

(The two tests that did not depend on the missing files —
`test_sphinx_excludes_the_frozen_design_records` and
`test_vale_runs_on_the_quadrants_only` — passed immediately, which is
correct: `conf.py` and `Makefile` already existed at that point.)

**After step 10** (the four `index.md` files created):

```
tests/test_docs_build.py::test_every_quadrant_has_an_index[reference] PASSED
tests/test_docs_build.py::test_every_quadrant_has_an_index[explanation] PASSED
tests/test_docs_build.py::test_sphinx_excludes_the_frozen_design_records PASSED
tests/test_docs_build.py::test_every_quadrant_has_an_index[how-to] PASSED
tests/test_docs_build.py::test_every_quadrant_has_an_index[tutorials] PASSED
tests/test_docs_build.py::test_vale_runs_on_the_quadrants_only PASSED
============================== 6 passed in 0.08s ===============================
```

## 5. The `vale sync` gap — how I solved it

`docs/Makefile`'s `vale` target now does, before the real vale call:

```make
vale:
	cd .. && test -d .vale-styles || uv run --extra docs vale sync
	cd .. && uv run --extra docs vale $(addprefix docs/,$(QUADRANTS))
```

Reasoning, also written as the comment above the target: `vale sync` fetches
the packages `.vale.ini` declares (`Packages = Microsoft`) over the network,
and Vale does not do this on its own — without it the run fails with a
missing-styles error (measured: that is exactly what happened on the first
attempt, before this fix existed). `.vale-styles/` is on `.gitignore`
(brief, step 7), so a fresh checkout has none of it yet; syncing once there
and reusing the cached directory afterward means a local `make -C docs vale`
does not hit the network on every run, only on the first one after a clone
or after deleting the cache. `test -d .vale-styles || ...` is the guard
for that: measured twice above, the first run downloads and syncs, the
second skips straight to the check. In CI the checkout is fresh every time,
so Gate 6 pays this fetch on every run — the task's own text accepts that
("der Lauf hat Netz"), and there is no project-level cache for
`.vale-styles/` the way there is for `uv`'s package cache, so I did not try
to avoid it there.

## 6. The five existing gates, unchanged and green

Run after all task-1 changes were in place, immediately before committing:

```
=== ruff check . ===
All checks passed!
=== ruff format --check . ===
37 files already formatted
=== pyright ===
0 errors, 0 warnings, 0 informations
=== lint-imports ===
Analyzed 31 files, 61 dependencies.
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT (2 ignored imports)
Only storage imports sqlalchemy KEPT (2 ignored imports)
No vendor SDK in stage 1a KEPT
Contracts: 4 kept, 0 broken.
=== pytest --cov ===
...
TOTAL                                   500      1    99%
Required test coverage of 90.0% reached. Total coverage: 99.80%
============================= 187 passed in 16.30s =============================
```

187 = the 181 that existed before this task, plus the 6 new ones in
`tests/test_docs_build.py`. Coverage is unchanged at 99.80% because the new
test file exercises only `pathlib`/filesystem checks, nothing under
`src/previously`. `uv sync --locked --all-extras` (the exact command Gate 0
of the CI runs) also succeeds cleanly against the updated `uv.lock`.

## 7. The CI workflow — what could and could not be checked from here

I cannot push from this worktree, so GitHub Actions never actually ran this
workflow. What I checked instead:

- `python3 -c "import yaml; yaml.safe_load(...)"` on the file — valid YAML.
- `uv run pre-commit run --files <all staged files>` — the project's
  `check-yaml` hook (and the other five hygiene hooks, plus `ruff`/
  `ruff-format`) all pass on every file this task touches, `gates.yml`
  included.
- Every command the new Gate 6 step runs (`make -C docs html`,
  `make -C docs vale`, `make -C docs linkcheck`) is the exact command I ran
  and verified locally above, and `uv sync --locked --all-extras` — the
  exact install step the workflow runs first — succeeds against the
  committed `uv.lock`.
- I did not touch the two pinned-by-SHA `uses:` lines, `permissions:`, or
  the `on:` triggers; the new step follows the existing steps' naming and
  comment pattern ("Gate N — name").

What is **not** checked: the actual GitHub-hosted runner environment (image
version, network behavior for `vale sync` and `linkcheck` against real
external hosts, cache behavior across runs). That can only be confirmed
once this branch is pushed and the workflow runs for real.

## 8. Deviations from the brief, with reasons

1. **An eighth dependency, `linkify-it-py>=2.2`**, added to the `docs`
   extra in `pyproject.toml` and to `DEPENDENCIES.md`. Not in the brief's
   seven-row table. Found by running `make -C docs html` with the brief's
   literal `conf.py`: `myst_enable_extensions` turns on `"linkify"`, and
   markdown-it-py's linkify rule raises `ModuleNotFoundError: Linkify
   enabled but not installed.` without this package. Checked the same way
   as the other seven (PyPI release date, GitHub `pushed_at`, archived
   flag): latest release 2.2.0, 2026-08-29, repository pushed the same day,
   not archived — active, recorded in `DEPENDENCIES.md` with that evidence
   and a note that it was found by running the build rather than by the
   plan's review.

2. **`docs/index.md`'s outer grid fence widened from ```` ``` ```` to
   ` ```` ` (3 backticks → 4), closing fence likewise.** The brief's literal
   markup nests a `{grid-item-card}` fence inside a `{grid}` fence using the
   same backtick count for both. Measured: with equal counts, the first
   bare ` ``` ` line inside the block closes the *outer* fence early
   (standard CommonMark fence-closing: a closing fence needs no info
   string, and a fence closes at the first such line at or above its own
   backtick count) — the build still "succeeded" but with three
   `[design.grid] The parent of a 'grid-item' should be a 'grid-row'`
   warnings, which `-W` turns into failures. Widening only the outer fence
   is MyST's own documented way to nest same-looking fences; wording and
   structure of the cards are otherwise untouched. Verified after the fix:
   zero warnings, and the built HTML has exactly 4 `sd-card` elements inside
   1 `sd-row`.

3. **Two wording changes for Vale's `Microsoft.Contractions` rule:**
   `docs/index.md` — "cannot" → "can't"; `docs/explanation/index.md` —
   "does not" → "doesn't". Both sentences are given verbatim in the brief
   (step 6 and step 10). Measured: `make -C docs vale` fails on exactly
   these two lines with that rule once the Microsoft style package is
   actually synced and run (shown in section 2 above) — the Global
   Constraints section already specifies Microsoft Writing Style, and this
   is that style's own preference, not a new requirement I introduced.
   Meaning is unchanged; I did not touch any other wording.

4. **`tests/test_docs_build.py`'s import block reordered** (`ruff check
   --fix`): the brief's literal file has a blank line between `import
   pathlib` and `import pytest`; this project's isort config
   (`force-single-line`, `no-sections`) wants both plain imports adjacent
   with no blank line between same-type imports. `ruff check .` failed with
   `I001` on the file as given; `ruff check --fix` closed the gap, nothing
   else in the file changed.

5. **`.github/workflows/gates.yml` comments beyond the new step**: updated
   two existing comments that enumerated "the five gates" to "the six
   gates", and extended the `uv sync --locked --all-extras` comment to
   name `[docs]` alongside `[test]` and `[dev]`, so the file does not claim
   something false about its own step count and installed extras. Did not
   touch `permissions:`, the `on:` triggers, or either pinned `uses:` SHA.

6. **No comment added to `.gitignore`** for the two new lines. The brief
   does not ask for one; the file's existing section comments are German
   and this file is not in CLAUDE.md's explicit list of root-config files
   bound to the English rule (`pyproject.toml`, `.importlinter`,
   `alembic.ini`, `.pre-commit-config.yaml`), so I matched the file's own
   established convention rather than introducing an isolated English
   comment next to German ones.

No existing gate was loosened to make Gate 6 pass. No import-linter
contract, `# type: ignore`, or new lint suppression was added or needed.
