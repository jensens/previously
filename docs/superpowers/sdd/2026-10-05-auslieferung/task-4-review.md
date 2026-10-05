# Task 4 review: the release workflow (`aa5ee8c..ea7ceb2`)

Reviewer: read-only on the tree. Read the whole diff, `release.yml` whole, `gates.yml`, the brief, the global constraints, ruling T4-a, spec §3, the fuellhorn model, `Dockerfile`, `.dockerignore`, the committed `scripts/smoke-image.sh` (`git show HEAD:`, since another implementer is editing it), `pyproject.toml`, `.gitignore`.

Measured myself on 2026-10-05:

- **actionlint 1.7.8** over `release.yml`, `gates.yml`, `audit.yml`, tree mounted read-only: no output, `exit=0`.
- **Pins**: every tag resolved through `gh api …/git/ref/tags/<tag>` (one more step for the annotated `pypa/gh-action-pypi-publish` tag). All nine commits match the version comments, all nine are the `releases/latest` of their repository, and `checkout` and `setup-uv` carry the same commits as `gates.yml`.
- **metadata-action at `dc802804…`, `src/meta.ts`**: `procSemver` calls `semver.valid(vraw)` *without* `loose` (line 178) and returns with the warning "is not a valid semver" — so `v0.1.0a1` gets no tag from a `type=semver` rule; the implementer's claim holds from the source too. `procPep440` (lines 224–236) accepts it and, for a pre-release, emits only `pep440.clean(vraw)` whatever the pattern — so both pep440 rules yield `0.1.0a1` (deduplicated), and `<major>.<minor>` exists only for stable releases, as ruling T4-a accepts.
- **setup-uv `action.yml` at `c18668ad…`**: `enable-cache` default `auto`, "except for release, tag push, pull_request_target, and workflow_run events" — the comment at `release.yml:87-91` quotes it correctly.
- **Environments** through the API: `pypi` has a tag policy `v*`, `testpypi` a branch policy `main`; repository public, default branch `main`.
- **actions/runner#2205** open, **#491** closed — as the header comment says.
- **The version today**: `setuptools_scm.get_version(local_scheme='no-local-version')` on this tree gives `0.1.dev178` — no tag exists yet, so the first Test-PyPI uploads are `0.1.devN`, a version Test-PyPI accepts.
- **The name** `previously`: 404 on both `pypi.org` and `test.pypi.org` JSON APIs.
- **Two tags on one commit** (scratch repository): `git describe --tags --long` picks `v1.0.0` over `v1.0.0rc1` when both are lightweight and when the final one is annotated.

Not rerun by me, because the brief keeps me read-only on the tree and they write into it (`.coverage`, `docs/_build`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`. The commit touches only `.github/workflows/`; no test and no documentation page outside `docs/superpowers/` reads that directory (grep), so the implementer's six green results are not contradicted by anything in the diff.

### Spec Compliance

**Job graph, traced by hand.**

| Event | gates | tag | build | publish-testpypi | publish-pypi | image ×2 | manifest |
|---|---|---|---|---|---|---|---|
| push to `main` | runs | skipped (`event_name`) | runs if gates `success` and tag `skipped` | runs (`ref` is main) | skipped (`event_name`) | skipped (parent not `success`) | skipped (parent not `success`) |
| `workflow_dispatch` on `main` | runs | skipped | runs | runs | skipped | skipped | skipped |
| `workflow_dispatch` elsewhere | runs | skipped | runs | skipped (`ref`) | skipped | skipped | skipped |
| published release | runs | runs | runs only if both `success` | skipped (`refs/tags/…`) | runs (env `pypi`, tag `v*`) | runs after PyPI | runs only if both platforms `success` |

- On `main`, the run consists of gates → build → Test-PyPI; skipped jobs do not fail a run, so nothing release-only turns it red. The explicit `!cancelled() && needs.<parent>.result == 'success'` is the right form: with the implicit `success()`, the skipped `tag` would block `build` directly and `publish-testpypi` transitively (#2205).
- On a release, a failed `tag` or failed `gates` makes `build`'s condition false; every later job asks for `success` from its parent and is skipped. No upload is reachable. A failed smoke test on one platform fails the matrix (fail-fast cancels the other), so `manifest` is skipped and no usable tag is created.
- `tag` runs **parallel** to `gates`, not after it, as spec §3.2 ("jeder erst nach dem vorigen") would literally have it; the brief laid it out that way, and the property that matters — both before any upload — holds.
- Spec §3.1 says a manual start is "wie ein Push auf main"; on `main` it is identical, elsewhere it stops after the build, which the `testpypi` environment would enforce anyway. Compliant with the intent ("erreicht nichts außer Test-PyPI").

**Permissions.** Workflow `contents: read`. The `gates` call job inherits it, and `gates.yml` asks for no more. `id-token: write` only in `publish-testpypi` and `publish-pypi` (which then have no `contents` at all — they need none, `download-artifact` uses the runtime token). `packages: write` plus `contents: read` only in `image` and `manifest`. Environment names `testpypi` and `pypi` match the GitHub environments and spec §3.4. No `${{ }}` is interpolated into a `run:` block; everything goes through `env:`.

**Version.** `fetch-depth: 0` on the build checkout; `local_scheme = "no-local-version"` in `pyproject.toml`; `dist/` is git-ignored, so `uv build` does not dirty the tree before the version is read. On a release, the tag check guarantees a form PEP 440 leaves unchanged (leading zeros aside, named), so the package version equals `${GITHUB_REF_NAME#v}`, and `image` waits for exactly that on PyPI.

**Image job.** Empty `$RUNNER_TEMP/wheels` as `build-contexts: wheels=…`; `PREVIOUSLY_VERSION` as build argument, matching `ARG PREVIOUSLY_VERSION` in the `Dockerfile`; `context: .` with a `.dockerignore` that admits only `pyproject.toml` and `uv.lock`; `ubuntu-24.04-arm` for arm64; setup-uv before the smoke test, `openssl` is on both runner images; the script is run as `bash scripts/smoke-image.sh "$IMAGE"` from the default working directory, the repository root. Order: build and push → smoke test → export digest → upload digest, so a failing image never reaches the manifest.

**Tags.** `type=pep440` for `{{version}}` and `{{major}}.{{minor}}`, `flavor: latest=false`, `type=raw,value=latest,enable=${{ github.event.release.prerelease == false }}`. Matches ruling T4-a; the missing `<major>.<minor>` for pre-releases is the accepted deviation from spec §3.2 item 6, to be written down in task 5.

**Pins.** All verified (above).

**`gates.yml`.** `workflow_call:` added; header comment extended and still true; permissions unchanged.

### Issues

**Critical** — none.

**Important** — none.

**Minor**

1. `.github/workflows/release.yml:8` — the header draws `gates -> tag -> build`, but `tag` has no `needs:` and runs parallel to `gates`. A comment is a claim; `gates, tag -> build` (or "gates and tag, side by side") would be true.
2. `.github/workflows/release.yml:34` — "none cancelled by a newer one" holds for a *running* run only. With `cancel-in-progress: false`, GitHub keeps one running and one pending run per group, and a newer run cancels the *pending* one. On `main` that is harmless (the newer commit reaches Test-PyPI), and a pending run has uploaded nothing, so the reason given ("cut off halfway") stays right — but the sentence overstates.
3. `.github/workflows/release.yml:40` — "the jobs that publish widen it for themselves": a job-level `permissions:` replaces the default, it does not add to it. The publish jobs end up with `id-token: write` and no `contents` at all, which is fine and arguably better, but "replace" is the true word.
4. `.github/workflows/release.yml:83-85` — "on main a development version such as 0.1.0a2.dev3 counted from the last tag": until the first tag exists there is no last tag, and the version is `0.1.devN` (measured: `0.1.dev178` today). Spec §3.2 item 3 has the same example; both are fine after `v0.1.0a1`, and both read as if it were so already.
5. Named, not to fix (misuse class, per the project's rule): nothing between `build` and `publish-pypi` checks that the built version equals the tag. The leading-zero case is named in the comment at `release.yml:56-58` and ends with a version on PyPI without an image. A second class, not named: promoting a release candidate to a final on the **same commit** with two tags; measured, `git describe` picks the final one when both are lightweight or the final is annotated, and if it ever picked the RC, PyPI would refuse the duplicate before anything else happens, so the failure is safe. A one-line guard in `build` (`ls dist/previously-"${GITHUB_REF_NAME#v}"-*.whl`) would turn every such class into a failure before the upload; the maintainer's call.
6. Named, not to fix: a stable release published *after* a newer one (a backport such as `v0.9.1` after `v1.0.0`) moves `latest` backwards, because `enable` reads only the pre-release mark, and the event payload does not carry GitHub's "latest release" flag. Irrelevant while there are no maintenance branches.
7. Named, not to fix: the wait step polls the JSON API, while `uv pip install` in the `Dockerfile` reads the simple index; PyPI purges both on upload, and fuellhorn has run the same loop for months. If the simple index ever lags, the image build fails after PyPI, and "Re-run failed jobs" repeats only `image` and `manifest`, which is the right recovery.

The implementer's concerns 1–7 in `task-4-report.md` are accurate as far as I could check them; concern 4 (gates run twice on `main`) is named in the comment at `release.yml:46-48`.

### Assessment

**Approved.** The job graph, the permissions, the version path, the image job and the tags do what spec §3, the brief and ruling T4-a ask; the deviations from the brief (`pep440`, `latest=false`, the explicit condition form) are measured and justified in the file. The four comment inaccuracies (Minor 1–4) are worth a sentence each when the file is next touched, not a fix round of their own; 5–7 are misuse or recovery notes for the documentation of task 5.
