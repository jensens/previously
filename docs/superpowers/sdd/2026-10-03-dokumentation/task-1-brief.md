## Task 1: Werkzeugkette, Makefile und das sechste Tor

**Files:**
- Create: `docs/conf.py`, `docs/index.md`, `docs/Makefile`, `.vale.ini`, `tests/test_docs_build.py`
- Modify: `pyproject.toml`, `DEPENDENCIES.md`, `.github/workflows/gates.yml`, `.gitignore`

**Interfaces:**
- Produces: `uv run --extra docs sphinx-build -W -b html docs docs/_build/html` baut ohne Warnungen. `make -C docs html`, `make -C docs linkcheck`, `make -C docs vale` existieren. Spätere Aufgaben verlassen sich darauf, dass `-W` (Warnung = Fehler) gilt.

- [ ] **Schritt 1: Abhängigkeiten erklären**

In `pyproject.toml`, `[project.optional-dependencies]`, neue Gruppe nach `dev`:

```toml
docs = [
    "sphinx>=9.1",
    "myst-parser>=5.1",
    "sphinx-book-theme>=1.4",
    "sphinx-design>=0.7",
    "sphinx-copybutton>=0.5.2",
    "sphinxcontrib-mermaid>=2.1",
    "vale>=3.22",
]
```

Dann `uv sync --all-extras` und `uv lock`.

- [ ] **Schritt 2: `DEPENDENCIES.md` ergänzen**

Die Pflegeprüfung ist am 2026-10-03 gemacht; schreib diese Belege ab, erheb sie nicht neu:

| Paket | Fassung | letzte Freigabe | Urteil |
|---|---|---|---|
| `sphinx` | 9.1.0 | 2025-12-31 | aktiv — Repo gepusht 2026-09-21 |
| `myst-parser` | 5.1.0 | 2026-05-13 | aktiv |
| `sphinx-book-theme` | 1.4.0 | 2026-07-19 | aktiv |
| `sphinx-design` | 0.7.0 | 2026-01-19 | aktiv — Repo gepusht 2026-09-28 |
| `sphinx-copybutton` | 0.5.2 | **2023-04-14** | **fertig, nicht verlassen** — Repo gepusht 2026-09-28, nicht archiviert; eine Erweiterung, die einen Kopierknopf anfügt, ist irgendwann fertig |
| `sphinxcontrib-mermaid` | 2.1.1 | 2026-09-01 | aktiv — Repo gepusht 2026-10-01 |
| `vale` | 3.22.0.0 | 2026-09-18 | aktiv |

Zu `vale` gehört ein Satz dazu, der sonst jemandem fehlt: das PyPI-Paket ist eine **Hülle**, die die Go-Binärdatei holt, und seine Fassung kodiert die Vale-Fassung (3.22.0.0 → Vale 3.22.0). `uv.lock` pinnt damit auch die Binärdatei — die Regel „eine Quelle der Wahrheit" hält.

Zur Spalte „Wofür" je Zeile: Sphinx baut, myst-parser liest Markdown statt reStructuredText, das Theme ist der Unterbau von `plone-sphinx-theme` (darum markup-gleich), sphinx-design liefert Grids und Karten für die Landing-Seiten, copybutton den Kopierknopf an Codeblöcken, sphinxcontrib-mermaid die vier Diagramme aus dem Abschnitt „Diagramme", vale prüft Stil und amerikanisches Englisch.

- [ ] **Schritt 3: `docs/conf.py` schreiben**

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx configuration for the Previously documentation."""

project = "Previously"
author = "Jens W. Klein"
copyright = "2026, Jens W. Klein"  # noqa: A001 — Sphinx requires this exact name

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "attrs_block",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "linkify",
    "strikethrough",
    "substitution",
]

# The design records under docs/superpowers/ are frozen German documents and
# the plans are working notes. They stay in the repository for provenance but
# they are not part of the published documentation: without this exclusion
# Sphinx pulls 2000 lines of German into the build, warns about every file
# missing from a toctree, and publishes the plans (review finding 3 of the
# plan's Review Focus).
exclude_patterns = [
    "_build",
    "superpowers/**",
]

html_theme = "sphinx_book_theme"
html_title = "Previously"

html_theme_options = {
    "repository_url": "https://github.com/jensens/previously",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navigation_with_keys": True,
}

# External hosts that rate-limit or block HEAD requests. Listed here rather
# than dropped from linkcheck entirely: the skill forbids disabling linkcheck
# to hide broken links, and these are not broken — they answer a browser and
# refuse a crawler.
linkcheck_ignore = [
    r"https://github\.com/.*/(issues|pull)/\d+",
]
linkcheck_timeout = 20
```

- [ ] **Schritt 4: `.vale.ini` schreiben, mit begrenztem Geltungsbereich**

```ini
StylesPath = .vale-styles
MinAlertLevel = warning

Packages = Microsoft

[*.md]
BasedOnStyles = Vale, Microsoft
```

Und der Geltungsbereich gehört in das Makefile-Ziel, **nicht** hier als Ausschluss: Vale wird nur auf die vier Quadranten gerufen. Grund: `docs/superpowers/**` und `NOTIZEN.md` sind deutsch, und ein Linter für amerikanisches Englisch darüber meldet hunderte Treffer und wird deshalb abgeschaltet (Review Focus 4).

- [ ] **Schritt 5: `docs/Makefile` schreiben**

```make
# Documentation targets. Every tool comes out of the project's own venv, so
# uv.lock is the only place a version is pinned (CLAUDE.md).

SPHINXOPTS  = -W --keep-going
QUADRANTS   = index.md tutorials how-to reference explanation

.PHONY: help html linkcheck vale clean

help:
	@echo "html       build the HTML documentation, warnings are errors"
	@echo "linkcheck  check that every link resolves"
	@echo "vale       check style, spelling and American English"
	@echo "clean      remove the build directory"

html:
	uv run --extra docs sphinx-build $(SPHINXOPTS) -b html . _build/html

linkcheck:
	uv run --extra docs sphinx-build $(SPHINXOPTS) -b linkcheck . _build/linkcheck

vale:
	cd .. && uv run --extra docs vale $(addprefix docs/,$(QUADRANTS))

clean:
	rm -rf _build
```

`-W --keep-going` ist Absicht: Warnung ist Fehler, aber der Lauf zeigt **alle** Warnungen und nicht nur die erste.

- [ ] **Schritt 6: `docs/index.md` als Landing-Seite**

```markdown
# Previously

Previously is an append-only knowledge store for project histories.
It records what happened, splits each record into units, and chains every event by hash so that a later change cannot pass unnoticed.

```{grid} 1 1 2 2

```{grid-item-card}
:link: tutorials/index
:link-type: doc

**Tutorials**
^^^
Start here.
Record your first event and verify the chain.
```

```{grid-item-card}
:link: how-to/index
:link-type: doc

**How-to guides**
^^^
Solve a specific problem: restore a backup, add a migration, check the chain in operation.
```

```{grid-item-card}
:link: reference/index
:link-type: doc

**Reference**
^^^
Look up a command, a configuration variable, a column, or the hash format.
```

```{grid-item-card}
:link: explanation/index
:link-type: doc

**Explanation**
^^^
Understand why the chain hashes a digest, why there is no sequence, and what the chain does not cover.
```
```

```{toctree}
:hidden:

tutorials/index
how-to/index
reference/index
explanation/index
```
```

- [ ] **Schritt 7: `.gitignore` ergänzen**

```
docs/_build/
.vale-styles/
```

- [ ] **Schritt 8: Test schreiben, der die Review-Focus-Punkte 3 und 4 festnagelt**

`tests/test_docs_build.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The documentation build is a gate, so its scope is a gate too."""

import pathlib

import pytest

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


def test_sphinx_excludes_the_frozen_design_records() -> None:
    """Without this exclusion Sphinx builds 2000 lines of German and
    publishes the plans. The exclusion is load-bearing, so it is pinned."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    assert '"superpowers/**"' in conf


@pytest.mark.parametrize("quadrant", ["tutorials", "how-to", "reference", "explanation"])
def test_every_quadrant_has_an_index(quadrant: str) -> None:
    """The skill requires an index.md in every directory, and the toctree in
    docs/index.md references exactly these four."""
    assert (DOCS / quadrant / "index.md").is_file()


def test_vale_runs_on_the_quadrants_only() -> None:
    """Vale checks American English. Pointed at the German design records it
    reports hundreds of hits and gets switched off, which is worse than not
    running it."""
    makefile = (DOCS / "Makefile").read_text(encoding="utf-8")
    assert "QUADRANTS" in makefile
    assert "superpowers" not in makefile
```

- [ ] **Schritt 9: Tests laufen lassen — sie müssen scheitern**

Run: `uv run pytest tests/test_docs_build.py -v`
Expected: FAIL, weil `docs/tutorials/index.md` und die übrigen drei noch nicht existieren.

- [ ] **Schritt 10: Die vier Quadranten-Index-Seiten anlegen**

Je Verzeichnis eine `index.md` mit H1, einem Satz Zweck und einem leeren `{toctree}`. Beispiel `docs/reference/index.md`:

```markdown
# Reference

Look up the exact behavior of a command, a configuration variable, or a column.

```{toctree}
:maxdepth: 1

```
```

Die anderen drei nach demselben Muster, mit diesen Sätzen:

- `tutorials/index.md`: „Learn Previously by recording an event and verifying the chain."
- `how-to/index.md`: „Solve a specific problem with Previously."
- `explanation/index.md`: „Understand the decisions behind the log and what it does not promise."

- [ ] **Schritt 11: Bauen und alle Tore laufen lassen**

```shell
make -C docs html
make -C docs vale
uv run pytest tests/test_docs_build.py -v
uv run ruff check .
uv run pyright
uv run lint-imports
```

Erwartet: `make -C docs html` endet mit „build succeeded" **ohne** Warnung. Scheitert es an einem leeren `{toctree}`, nimm die Direktive in den drei leeren Indexseiten vorerst heraus und trag sie in der Aufgabe wieder ein, die die erste Seite dort anlegt.

- [ ] **Schritt 12: Das sechste Tor in die CI**

In `.github/workflows/gates.yml` nach „Gate 5 — pytest":

```yaml
      - name: Gate 6 — documentation
        # Warnings are errors (-W in docs/Makefile). linkcheck runs here too:
        # the hosts that rate-limit crawlers are listed in conf.py's
        # linkcheck_ignore, so a failure means a genuinely broken link.
        run: |
          make -C docs html
          make -C docs vale
          make -C docs linkcheck
```

Der Schritt installiert nichts eigenes: `uv sync --locked --all-extras` weiter oben bringt das `docs`-Extra mit.

- [ ] **Schritt 13: Commit**

```shell
git add pyproject.toml uv.lock DEPENDENCIES.md .gitignore .vale.ini docs .github tests/test_docs_build.py
git commit
```

Botschaft: `docs: a Sphinx toolchain and a sixth gate`, englisch, mit `Assisted-By:`.

---

