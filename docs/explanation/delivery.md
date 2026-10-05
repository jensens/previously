(delivery)=

# About delivery

Previously reaches the places it runs in two forms: a package on PyPI, and a container image on `ghcr.io` that holds that package.
A published GitHub release produces both, and a push to `main` produces a development version on Test-PyPI and nothing else.
This page explains why the image installs the package from PyPI rather than from the checkout, why its versions get compared with `uv.lock` in one direction only, why an alpha gets no `latest`, why the migrations ship inside the package and run under a lock, and why the tag gets checked before anything is uploaded.
The steps themselves are in {ref}`cut-a-release` and {ref}`run-the-image`.

## The image installs what PyPI holds

The image could be built from the checkout, or from the wheel the same workflow run just built.
It's built from PyPI instead: the dependencies come from `uv.lock` exactly, and then Previously itself, in the version of the release, comes from PyPI without resolving anything again.

The reason is what the image then proves.
Whoever pulls the image gets the package that anybody else gets with `pip install previously`, byte for byte, and the smoke test that ran on the image ran on that package.
An image built from the checkout would prove that the checkout works, which the gates already proved, and say nothing about what PyPI serves.

The price is the order of events.
The package has to be on PyPI before the image can install it, so a smoke test that fails comes after the upload, and the version stays on PyPI without an image.
A version on PyPI never comes back, so the fix is the next version number.
For a project whose releases are alphas until `1.0.0`, that price is acceptable; the alternative, an image from the run's own wheel, would pay with the one thing the image is there to show.

## The versions get compared with the lock in one direction

The image installs the dependencies with `uv sync --frozen`, which takes `uv.lock` unchanged and refuses to resolve again.
The smoke test then checks the result anyway, because a frozen install is a promise of the tool, and the image is the place where a broken promise would go unnoticed.

The check asks one question: does every version installed in the image stand in the lock?
It doesn't ask the reverse, whether every package of the lock is installed, because the lock is written for every platform at once.
`tzdata` stands in it as a dependency that only Windows needs, so the image rightly lacks it, and a check in both directions failed on it.
A package that's missing for real shows up anyway, because the steps after the check run the commands that need it.

## An alpha gets no `latest`

`latest` is the tag that a pull without a tag gets.
Pointing it at an alpha would hand an alpha to anybody who didn't ask for a version, so `latest` follows a stable release only.

Whether a release is stable is decided by the mark on the GitHub release, not by the form of the tag.
The tag's form and the mark could disagree, and the workflow doesn't second-guess the person who published: the mark decides.

An alpha gets no `<major>.<minor>` either, and that one wasn't a decision but a measurement.
The tool that derives the tags, `docker/metadata-action`, extends a pre-release to its exact version only, whatever pattern it's given.
The `semver` rules the plan first named gave `v0.1.0a1` no tag at all, because `0.1.0a1` isn't valid semantic versioning, and the first release would have failed at the manifest after the package was on PyPI.
The `pep440` rules read the version as Python does.
So until `1.0.0`, each release marked as a pre-release has exactly one tag meant for use, its version, and pinning that version is the only way to use it, which is how a deployment should use any image.
The intermediate tags `<version>-linux-amd64` and `<version>-linux-arm64` exist beside it, as steps of the workflow that nobody is meant to pull.
An alpha published without the mark would get `<major>.<minor>` and `latest` as well, because the mark decides.

`latest` also has a limit worth knowing about: it follows the release published last, not the highest version.
A stable release of an older line, published after a newer one, moves `latest` back to it.
That can't happen until the project keeps a second line.

## The migrations ship inside the package

Until this stage, the migrations lived in a directory beside the package, run by `alembic upgrade head` next to `alembic.ini` in a checkout.
A wheel didn't contain them, and so an image that installs the wheel couldn't create its own database.

So they moved into the package, as `previously.migrations`, and Alembic finds them by the package path, from an installed wheel, without a checkout and without `alembic.ini`.
`previously migrate` runs them, and a test holds that the built wheel contains every revision; without that test, a revision left out would show first in the smoke test of a release, after the upload.
In a checkout, `alembic` still works for development, and it's still the way to write a revision and to go back.

`migrate` only goes forward.
Going back in operation means restoring a backup, which {ref}`restore-from-a-backup` covers, not running an older schema over the data.

## `migrate` takes a lock

In a cluster, two migration jobs of the same release can start at the same time, after a retry, or when two deployments overlap.
Without a lock, both would run the same DDL against the same database.

`migrate` takes a PostgreSQL advisory lock on a connection of its own before it reads the revision, and releases it only once the upgrade has committed.
A second `migrate` waits for the lock, then reads the revision the first one left behind, and reports `up to date`.
The lock belongs to the session, not to a transaction, so a `migrate` that fails gives it up when its connection closes, and nothing has to clean up after it.

A database that's ahead of the image, migrated by a newer release, is refused by `migrate` rather than ignored.
That refusal is the only comparison of revisions there is.
The other commands don't compare, in either direction: against a schema that's behind, one fails only where it touches a table or a column the schema lacks, and runs where it touches none, and an older image's commands run against a newer schema as far as it still has what they touch.
Measured on 2026-10-05 against a database one revision behind, `append`, `log` and `project` ran, and only `verify` refused.
So the guard is the order in which a release runs its jobs, migration first, and not the commands.
Whether every command should check the revision itself is open, and it's a decision about the code, not about delivery.

## The tag gets checked before anything is uploaded

A release tag has one of four forms: `vX.Y.Z`, `vX.Y.ZaN`, `vX.Y.ZbN` or `vX.Y.ZrcN`.
The version on PyPI and on the image is the tag without its `v`, so a tag in another form would give a version the rest of the workflow doesn't expect.

The check runs before the upload, side by side with the gates, and a tag in another form ends the run before anything is published.
In the project this workflow was modeled on, the same check runs last, once the package and the image are already out, and so it can only report a mistake that's already public.

The check reads the form, not the result.
Nothing compares the version that was built with the tag, so two cases pass it.
A tag with a leading zero, such as `v1.02.3`, which Python's version rules read as `1.2.3`, is a mistake that costs a version: it reaches PyPI and gets no image.
A tag on a commit that carries a second tag, such as a stable release on the commit of a release candidate, passes the check and does no harm, measured: the build reads the right tag, and if it ever read the other one, PyPI would refuse the upload as a duplicate.
{ref}`cut-a-release` says what to do about each of them.

## No token in the repository

Both uploads use trusted publishing: PyPI and Test-PyPI accept a short-lived token from GitHub's OpenID Connect provider for this one workflow file, and only from its GitHub environment.
The environment `pypi` deploys only from a tag `v*`, and `testpypi` only from `main`, so even a changed workflow on another branch can't publish.
No upload token lies in the repository or in its secrets, so there's none to leak and none to rotate.
