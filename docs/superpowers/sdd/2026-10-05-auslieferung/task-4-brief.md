## Task 4: Der Release-Workflow

**Files:**
- Modify: `.github/workflows/gates.yml`
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `Dockerfile` und `scripts/smoke-image.sh` (Aufgabe 3).

- [ ] **Step 1: `gates.yml` aufrufbar**

`on:` bekommt `workflow_call:` dazu. Der Kopfkommentar („nichts über die Tore hinaus") bleibt wahr und bekommt einen Satz: `release.yml` ruft diese Datei, und dort, nicht hier, wird veröffentlicht. Die Rechte bleiben `contents: read`.

- [ ] **Step 2: `release.yml`** — Vorlage nach `fuellhorn` (`/home/jensens/ws/jwk/fuellhorn/.github/workflows/release.yaml`, dort seit Monaten im Gebrauch), angepasst an die Entscheidungen oben. Englische Kommentare in der Dichte von `gates.yml`. Der Aufbau:

```yaml
name: Release

on:
  push:
    branches: [main]
  release:
    types: [published]
  workflow_dispatch:

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  gates:
    uses: ./.github/workflows/gates.yml

  tag:
    # Before anything is uploaded: a tag in another form would otherwise only
    # be refused after the package is on PyPI.
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    steps:
      - run: |
          [[ "$GITHUB_REF_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$ ]] || {
            echo "::error::tag $GITHUB_REF_NAME is not vX.Y.Z, vX.Y.ZaN, vX.Y.ZbN or vX.Y.ZrcN"; exit 1; }

  build:
    needs: [gates, tag]
    if: always() && needs.gates.result == 'success' && needs.tag.result != 'failure'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha> # vX
        with:
          fetch-depth: 0   # hatch-vcs reads the version from the tags
      - uses: astral-sh/setup-uv@<sha> # vX
      - run: uv build
      - uses: actions/upload-artifact@<sha> # vX
        with: {name: dist, path: dist/}

  publish-testpypi:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: testpypi
    permissions: {id-token: write}
    steps:
      - uses: actions/download-artifact@<sha> # vX
        with: {name: dist, path: dist/}
      - uses: pypa/gh-action-pypi-publish@<sha> # vX
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  publish-pypi:
    needs: build
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    environment: pypi
    permissions: {id-token: write}
    steps:
      - uses: actions/download-artifact@<sha> # vX
        with: {name: dist, path: dist/}
      - uses: pypa/gh-action-pypi-publish@<sha> # vX

  image:
    needs: publish-pypi
    strategy:
      matrix:
        include:
          - {platform: linux/amd64, runner: ubuntu-latest}
          - {platform: linux/arm64, runner: ubuntu-24.04-arm}
    runs-on: ${{ matrix.runner }}
    permissions: {contents: read, packages: write}
    steps:
      # checkout; version from the tag; wait for the version on PyPI (as fuellhorn,
      # at most five minutes); an empty directory as the `wheels` context; login
      # to ghcr.io; buildx; build and push `<version>-linux-<arch>` with
      # `build-contexts: wheels=<empty dir>` and `PREVIOUSLY_VERSION`; set up uv;
      # `bash scripts/smoke-image.sh <that tag>`; export and upload the digest.

  manifest:
    needs: image
    runs-on: ubuntu-latest
    permissions: {contents: read, packages: write}
    steps:
      # download the digests; login; buildx; docker/metadata-action with
      # `type=semver,pattern={{version}}`, `type=semver,pattern={{major}}.{{minor}}`,
      # `type=raw,value=latest,enable=${{ github.event.release.prerelease == false }}`;
      # `docker buildx imagetools create` from the digests — as fuellhorn.
```

Die Schritte in `image` und `manifest` stehen in `fuellhorn` ausgeschrieben und werden von dort übernommen, mit drei Änderungen: der Name `previously` statt `fuellhorn`, das Build-Argument `PREVIOUSLY_VERSION`, der Build-Kontext `wheels` (leeres Verzeichnis) und der Aufruf von `scripts/smoke-image.sh` statt des eingebetteten Tests. Kein Job `helm-publish`.

**Die Commits der Aktionen** löst der Umsetzer selbst auf, für jede Aktion die neueste Fassung zum Zeitpunkt: `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` (bei einem annotierten Tag einmal weiter über `git/tags/<sha>`), der Commit in `uses:`, die Fassung als Kommentar. `actions/checkout` und `astral-sh/setup-uv` nehmen dieselben Commits wie `gates.yml`.

- [ ] **Step 3: Die Tag-Prüfung messen** — den regulären Ausdruck in einer Schleife gegen sechs Tags in der Shell: `v0.1.0a1`, `v1.2.3`, `v1.2.3rc4` angenommen; `v0.1.0-alpha1`, `v0.1`, `0.1.0a1` abgewiesen. Die Ausgabe in den Bericht.

- [ ] **Step 4: actionlint**

```bash
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.8 -color .github/workflows/gates.yml .github/workflows/audit.yml .github/workflows/release.yml
```
Expected: keine Meldung, Rückgabecode 0. Mutation: in `release.yml` ein `needs:` auf einen Job, den es nicht gibt → actionlint meldet es; zurück.

- [ ] **Step 5: Sechs Tore, Commit**

```bash
git add .github/workflows/gates.yml .github/workflows/release.yml
git commit -F <message-file>   # "ci: a release publishes the package and a two-platform image"
```

---

