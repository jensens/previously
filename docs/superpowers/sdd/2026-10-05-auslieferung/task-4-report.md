# Task 4 report: the release workflow

Status: DONE_WITH_CONCERNS. Commit `ea7ceb2` (`.github/workflows/gates.yml` modified, `.github/workflows/release.yml` new), base `aa5ee8c`.

## Actions and their commits

Resolved on 2026-10-05: `releases/latest`, then `git/ref/tags/<tag>`, and for an annotated tag one more step through `git/tags/<sha>`.

| Action | Version | Commit | Ref type |
|---|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | commit (same as gates.yml) |
| astral-sh/setup-uv | v10.2.0 | `c18668ad3cf93ea998bef934396af7bb5c839dc7` | commit (same as gates.yml) |
| actions/upload-artifact | v7.0.1 | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | commit |
| actions/download-artifact | v8.0.1 | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` | commit |
| pypa/gh-action-pypi-publish | v1.14.2 | `dc37677b2e1c63e2034f94d8a5b11f265b73ba33` | annotated tag, dereferenced |
| docker/login-action | v4.6.0 | `dbcb813823bdd20940b903addbd779551569679f` | commit |
| docker/setup-buildx-action | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | commit |
| docker/build-push-action | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | commit |
| docker/metadata-action | v6.2.0 | `dc802804100637a589fabce1cb79ff13a1411302` | commit |

The inputs used (`name`, `path`, `pattern`, `merge-multiple`, `if-no-files-found`, `retention-days`, `repository-url`, `skip-existing`, `context`, `build-contexts`, `build-args`, `platforms`, `tags`, `flavor`, `images`) were checked against each action's `action.yml` at that commit.

## Tag check (Step 3)

The lines of the `tag` job, in `bash -e` (GNU bash 5.2.21), one fresh shell per tag:

```
v0.1.0a1       exit=0
v1.2.3         exit=0
v1.2.3rc4      exit=0
v0.1.0-alpha1  exit=1 ::error::tag v0.1.0-alpha1 is not vX.Y.Z, vX.Y.ZaN, vX.Y.ZbN or vX.Y.ZrcN
v0.1           exit=1 ::error::tag v0.1 is not vX.Y.Z, vX.Y.ZaN, vX.Y.ZbN or vX.Y.ZrcN
0.1.0a1        exit=1 ::error::tag 0.1.0a1 is not vX.Y.Z, vX.Y.ZaN, vX.Y.ZbN or vX.Y.ZrcN
```

The regex sits in a variable (`re=...; [[ "$GITHUB_REF_NAME" =~ $re ]]`) rather than inline as in the brief; same expression, the usual bash idiom.

## actionlint (Step 4)

`rhysd/actionlint:1.7.8` (digest `sha256:96d4a8c87dbbfb3bdd324f8fdc285fc3df5261e2decc619a4dd7e8ee52bbfd46`), which bundles ShellCheck 0.11.0 and pyflakes, so the `run:` blocks are shellchecked too.

Control, the committed files, over `gates.yml`, `audit.yml` and `release.yml`: no output, `exit=0`.

Mutation A (the brief's): `image` gets `needs: publish-pypy`:

```
.github/workflows/release.yml:148:3: job "image" needs job "publish-pypy" which does not exist in this workflow [job-needs]
.github/workflows/release.yml:152:29: property "publish-pypi" is not defined in object type {} [expression]
exit=1
```

Mutation B: `build`'s condition asks for `needs.tags.result` instead of `needs.tag.result`:

```
.github/workflows/release.yml:69:65: property "tags" is not defined in object type {gates: {outputs: {}; result: string}; tag: {outputs: {}; result: string}} [expression]
exit=1
```

Mutation C (is ShellCheck reading the blocks?): the manifest command put back into fuellhorn's unquoted `$(jq ...)` form:

```
.github/workflows/release.yml:319:9: shellcheck reported issue in this script: SC2046:warning:9:33: Quote this to prevent word splitting [shellcheck]
exit=1
```

Each mutation was restored by copy from a backup, `cmp` confirmed byte for byte, and the control run after it was `exit=0`. (Line numbers are from before the last comment edit; the final file was linted again, `exit=0`.)

## Measurements beyond the brief

**metadata-action, run locally.** I ran the action's own `dist/index.cjs` at the pinned commit (sha256 `91b260f1…`) under node 22, with the inputs of `release.yml`, a release event payload, and a scratch HTTP stand-in for `api.github.com` (the action insists on fetching the repository record; I did not hand it a real token). Results:

| Tag | Prerelease mark | Rules | Tags |
|---|---|---|---|
| v1.2.3 | false | pep440 + `latest=false` | `1.2.3`, `1.2`, `latest` |
| v1.2.3 | true | pep440 + `latest=false` | `1.2.3`, `1.2` |
| v0.1.0a1 | true | pep440 + `latest=false` | `0.1.0a1` |
| v0.1.0a1 | false | pep440 + `latest=false` | `0.1.0a1`, `latest` (misuse: the mark decides) |
| v1.2.3rc4 | true | pep440 + `latest=false` | `1.2.3rc4` |
| v1.2.3 | true | pep440, default flavor | `1.2.3`, `1.2`, `latest` (the auto latest ignores the mark) |
| v0.1.0a1 | true | **the brief's semver rules** | **none**: "v0.1.0a1 is not a valid semver", "No Docker tag has been generated" |
| v1.2.3 | false | the brief's semver rules | `1.2.3`, `1.2`, `latest`, `latest` |

So the brief's `type=semver` would have failed the first release (`0.1.0a1`) at the manifest, after PyPI and both platform images. Changed to `type=pep440`, plus `flavor: latest=false` so that only the explicit rule (the release's mark) sets `latest`. Both stated in the workflow comment with the measurement.

**The manifest's shell block**, extracted from the committed file and run with `docker` replaced by a function printing its arguments, fed by the action's real `DOCKER_METADATA_OUTPUT_JSON`: it produces `buildx imagetools create -t <tag>… <image>@sha256:<d1> <image>@sha256:<d2>` as intended. I rewrote fuellhorn's `$(jq …) $(printf …)` into arrays, because ShellCheck flags the original (mutation C).

**`uv export` needs no Python.** In `ghcr.io/astral-sh/uv:latest` (uv 0.12.23, no interpreter) with `UV_PYTHON_DOWNLOADS=never`, `uv export --frozen --no-dev --no-emit-project --no-hashes` on this tree exits 0 and prints the 42-line export. So the `image` job's setup-uv has no `python-version`; only `build` sets 3.14.

**Smoke-test images exist for arm64**: `docker manifest inspect` lists `arm64` for `rustfs/rustfs:1.0.1` and `postgres:17`.

**Environments**, read through the API: `pypi` has a deployment policy of type tag, `v*`; `testpypi` of type branch, `main`. Unchanged. The trusted publishers on (Test-)PyPI are not visible to me; the header comment's statement about them comes from the brief.

**setup-uv's cache**: its `action.yml` says `enable-cache: auto` "enables caching on GitHub-hosted runners except for release, tag push, pull_request_target, and workflow_run events". Left at the default, so the PyPI build runs without a cache.

## The job graph

Every job after `tag` carries `if: ${{ !cancelled() && needs.<parent>.result == 'success' && … }}`, not the brief's `always()` and not the implicit `success()`. Reason: on main, `tag` is skipped, and the implicit `success()` treats a skipped job as not passed, directly (actions/runner#491, closed) and also two levels up, below a job that ran (actions/runner#2205, open as read on 2026-10-05). With the implicit form, `publish-testpypi` would never run on main. `!cancelled()` instead of `always()` keeps a cancelled run from going on.

**Push to main** (and a manual start on main):
gates (called) → tag *skipped* (not a release) → build (gates success, tag skipped counts as passed) → publish-testpypi (ref is main) → done.
publish-pypi skipped (not a release) → image skipped (needs publish-pypi success) → manifest skipped.

**Manual start elsewhere**: gates → build → everything else skipped (ref not main, not a release). The spec's §3.1 table says "like a push to main"; the `testpypi` environment would refuse a non-main ref anyway.

**Published release**:
gates → tag (regex) → build (fetch-depth 0, hatch-vcs gives the tag's version) → publish-pypi (environment `pypi`) → image ×2 (wait for PyPI, build and push `<version>-linux-<arch>` with an empty `wheels` context and `PREVIOUSLY_VERSION`, smoke test, digest) → manifest (pep440 tags, `latest` only when not marked pre-release, `imagetools create`).
publish-testpypi skipped (ref is a tag).

**Failures**: a failed gate or a failed tag check gives `build` a false condition → skipped → every job below is skipped, because each asks for `success` from its parent. A failed smoke test on either platform makes the matrix result `failure` → manifest skipped; only the intermediate tags exist.

Permissions: workflow default `contents: read`; `id-token: write` only in the two publish jobs; `packages: write` (with `contents: read`) only in `image` and `manifest`.

## Gates, each as its own command

```
uv run ruff check .                          -> All checks passed!
uv run ruff format --check .                 -> 73 files already formatted
uv run pyright                               -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                          -> Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> 800 passed in 94.50s; total coverage 98.06%
make -C docs html                            -> build succeeded (pages in _build/html)
make -C docs vale                            -> 0 errors, 0 warnings and 0 suggestions in 28 files
make -C docs linkcheck                       -> build succeeded
```

`git status --short` after the commit: empty. Scratch (scripts, the downloaded action, npm libraries) is under the scratchpad directory only.

## Concerns

1. **Two departures from the brief** (`type=pep440` instead of `type=semver`; `flavor: latest=false`), measured above. Without the first, the first release fails at its last step.
2. **No `<major>.<minor>` for a pre-release.** metadata-action gives a pre-release only `{{version}}`. Spec §3.2 item 6 names `<version>` and `<major>.<minor>`, and §3.3 says alphas are the normal case until 1.0.0, so in practice `0.1`-style tags will not exist for a long time. Whether a floating tag for alphas is wanted is the maintainer's call; I did not build one. Task 5's documentation should state what the tags actually are.
3. **The condition form deviates from the brief** (`!cancelled()` and explicit `needs.<parent>.result == 'success'` on every job after `tag`). Reason above; I could not run the workflow, so the transitive-skip behavior rests on the open issue #2205, not on a run of my own.
4. **The gates run twice on a push to main**: once from `gates.yml`'s own `push` trigger, once called from `release.yml`. Named in a comment; it costs minutes, not correctness.
5. **Misuse named in comments, not engineered around**: a tag whose form and pre-release mark disagree (the mark decides `latest`); a leading zero (`v1.02.3`) passes the regex but hatch-vcs normalizes it to `1.2.3` while `image` waits for `1.02.3`.
6. **The ghcr.io package starts private** (GitHub's default for a first push). The smoke test pulls with the job's login, so it works; kup6s needs the maintainer to make it public (spec §3.4).
7. **Nothing of this has run on GitHub.** `workflow_dispatch` works only for files on the default branch. The first run after the merge is a push to main, which reaches Test-PyPI and is the first real measurement of `gates` as a called workflow and of the trusted publisher.
