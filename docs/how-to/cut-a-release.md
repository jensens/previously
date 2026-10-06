(cut-a-release)=

# How to cut a release

This guide shows you how to publish a release of Previously: the package on PyPI, and the image for two platforms on `ghcr.io`.
For why the release takes the path it takes, see {ref}`delivery`.

A release happens only when you publish a GitHub release.
A tag alone publishes nothing, and neither does a merge: a push to `main` builds a development version and puts it on Test-PyPI, and nothing else.

## Check the setup

The setup below is done once, by the maintainer, and it's in place.
Check it before a release rather than assume it, because a missing piece fails only after the gates ran.

Check that the two GitHub environments exist and deploy only from where they should:

```shell
gh api repos/jensens/previously/environments/pypi/deployment-branch-policies --jq '.branch_policies[] | {name, type}'
gh api repos/jensens/previously/environments/testpypi/deployment-branch-policies --jq '.branch_policies[] | {name, type}'
```

The first must print the tag rule for `pypi`, and the second the branch rule for `testpypi`:

```text
{"name":"v*","type":"tag"}
{"name":"main","type":"branch"}
```

Check on PyPI and on Test-PyPI, under {guilabel}`Publishing` in the project's or your account's settings, that a trusted publisher names the repository `jensens/previously`, the workflow `release.yml`, and the environment `pypi` or `testpypi`.
Before the first release, PyPI lists it as a pending publisher, because the project doesn't exist there yet.

Check that the last run of the workflow on `main` passed, and that it put a development version on Test-PyPI:

```shell
gh run list --workflow release.yml --branch main --limit 1
```

That run is also the only trial of the workflow there is.
GitHub starts a workflow by hand only from a file on the default branch, so `release.yml` can't run on a branch before it's merged; the first push to `main` after the merge is its trial run.

## Choose the version

A release tag has one of four forms, and the workflow refuses any other before it uploads anything:

| Form | Example | Kind |
|---|---|---|
| `vX.Y.Z` | `v1.2.3` | Stable |
| `vX.Y.ZaN` | `v0.1.0a1` | Alpha |
| `vX.Y.ZbN` | `v0.1.0b1` | Beta |
| `vX.Y.ZrcN` | `v1.0.0rc1` | Release candidate |

Until `1.0.0`, a release is an alpha.
Take a number that has never been on PyPI: a version that was uploaded once can't be uploaded again, even after a failed release.
Don't write a leading zero, such as `v1.02.3`.
It passes the check, but the package's version reads as `1.2.3`, while the image job takes the tag's own text, `1.02.3`, and the two no longer meet.
Nothing compares the version the run builds with the tag, so the tag is all there is to get right.
A stable release on the commit of a release candidate is safe: measured, the build reads the stable tag there, and if it ever read the other one, PyPI would refuse the upload as a duplicate before anything else is published.

## Write the notes for operators

The generated notes list the merged pull requests.
Add what an operator has to do, above them.

If the release brings a new migration, say so first.
List the revisions added since the last release, with that release's tag in place of `v0.1.0a1`:

```shell
git diff --name-only --diff-filter=A v0.1.0a1 main -- src/previously/migrations/versions/
```

If that lists a file, the notes have to say that `previously migrate` runs before anything else of this release.
Nothing else enforces that order: `migrate` is the only command that compares revisions, and the other commands fail on a schema that's behind only where they touch a table or a column it lacks.
An older image's `migrate` refuses a database a newer one has migrated; its other commands don't.

## Publish the release

Publish the release from `main`:

```shell
gh release create v0.1.0a1 --prerelease --generate-notes --target main
```

Leave out `--prerelease` for a stable release, and add the notes for operators with `--notes`:

```shell
gh release create v1.0.0 --generate-notes --target main --notes 'Run `previously migrate` before anything else of this release: it adds the revision 0006_example.'
```

The version decides `<major>.<minor>`, and the mark decides `latest`.
A pre-release version, such as `0.1.0a1`, gets the tag `<version>` and never `<major>.<minor>`.
A stable version gets `<version>` and `<major>.<minor>`.
`latest` comes only with a release published without the pre-release mark.
`latest` goes to the stable release published last, so a stable release of an older line, published after a newer one, moves `latest` back to it.

## Watch the run

Follow the run the release started:

```shell
gh run watch
```

The jobs run in this order:

1. `gates` and `tag`, side by side: the six gates, and the tag's form.
2. `build`: the source archive and the wheel, with the version from the tag.
3. `publish-pypi`: the upload to PyPI, in the environment `pypi`.
4. `image`, once for `linux/amd64` and once for `linux/arm64`: wait for the version on PyPI, build and push the image under an intermediate tag `<version>-linux-<arch>`, and run the smoke test against it.
5. `manifest`: one manifest list over both images, under the tags people use.

When `manifest` has passed, the release is out.
Check that the image is there for both platforms:

```shell
docker buildx imagetools inspect ghcr.io/jensens/previously:0.1.0a1
```

On the first release, the package on `ghcr.io` is still private, so log in with `docker login ghcr.io` first, or run the check after you made the image public.

## Make the image public, once

After the first release, the package `previously` on `ghcr.io` is private, which is GitHub's default for a new package.
Open the package's settings on GitHub, under {menuselection}`Packages --> previously --> Package settings`, and change its visibility to public.
Check that it can be pulled without credentials:

```shell
docker logout ghcr.io
docker pull ghcr.io/jensens/previously:0.1.0a1
```

Later releases keep the visibility.

## If a job fails

What to do depends on what the run already published.
Read the table from the job that failed.

| Failed job | Already published | What to do |
|---|---|---|
| `gates`, `tag` or `build` | Nothing. | Delete the release and its tag with `gh release delete v0.1.0a1 --cleanup-tag`, fix the cause on `main`, and publish the release again under the same version. |
| `publish-pypi` | Nothing, unless PyPI shows the version. | Look for the version on `https://pypi.org/project/previously/`. If it isn't there, fix the cause, such as a missing trusted publisher, and rerun the failed jobs. If it's there, even one of its two files, this version stays on PyPI without an image: a rerun repeats the upload, which fails on a file that's already there, so fix the cause on `main` and release the next version. |
| `image`, while it waits for PyPI | The package on PyPI. | The version didn't show on PyPI within five minutes; rerun the failed jobs. |
| `image`, in the build or the smoke test | The package on PyPI, and possibly an intermediate tag on `ghcr.io`. | Read the log. If the build found no such version, rerun the failed jobs: the wait asks PyPI's JSON interface, the build installs from PyPI's simple index, and the second can lag behind the first. If the cause was transient, rerun the failed jobs as well. If it's a defect, fix it on `main` and release the next version: this one stays on PyPI without an image, and its intermediate tags stay unused. |
| `manifest` | The package on PyPI, and both intermediate tags on `ghcr.io`. | Rerun the failed jobs. |

Rerun the failed jobs, and only those, with the run's identifier from `gh run list`:

```shell
gh run rerun 1234567890 --failed
```

A rerun repeats the failed jobs and the jobs that depend on them, so `manifest` runs again after a rerun of `image`.
A rerun of `manifest` alone reads the digests the two `image` jobs left behind, which the run keeps for seven days; after that, release the next version.

A version on PyPI never comes back.
Once the package is there, the next version fixes a defect in it, never an upload of the same one.
