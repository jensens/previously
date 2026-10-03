# Dokumentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **ZWEITE PFLICHT-SUB-SKILL:** Jede Seite, die dieser Plan erzeugt, folgt dem Skill **`plone-doc-style:author`**. Er ist aufrufbar (`Skill plone-doc-style:author`) — nicht unter dem Namen `plone-doc-style`. Lies ihn, bevor du eine Seite schreibst.

**Goal:** Previously bekommt eine Diátaxis-Dokumentation nach dem `plone-doc-style`-Skill, die Explanation-Seiten werden die maßgebliche Quelle der Entwurfsbegründungen, und „Doku kommt im selben PR mit" wird ein Tor statt einer Absichtserklärung.

**Architecture:** Ein Sphinx/MyST-Baum unter `docs/` mit den vier Diátaxis-Quadranten. Die bestehenden deutschen Specs unter `docs/superpowers/` werden als datierte Entwurfsberichte eingefroren und aus dem Sphinx-Lauf ausgeschlossen; ihre lebende Begründung wandert übersetzt in `docs/explanation/`. Die 72 Paragraphenverweise im Code wechseln von `§x.y` auf MyST-Label, und ein Test hält fest, dass keiner ins Leere zeigt.

**Tech Stack:** Sphinx 9.1, myst-parser 5.1, sphinx-book-theme 1.4, sphinx-design 0.7, sphinx-copybutton 0.5.2, sphinxcontrib-mermaid 2.1, vale 3.22 (PyPI-Hülle um die Go-Binärdatei), GNU make.

**Spec:** `docs/superpowers/specs/2026-10-01-architektur.md` und `docs/superpowers/specs/2026-10-02-stufe-1a-log.md` — zusammen die Quelle, aus der die Explanation-Seiten übersetzt werden. Lies beide; sie sind deutsch und bleiben es.

## Global Constraints

- **Stil:** `plone-doc-style:author` gilt vollständig — amerikanisches Englisch, Microsoft Writing Style, **ein Satz pro Zeile**, sentence-case Überschriften, Dateinamen mit Bindestrichen, `index.md` in jedem Verzeichnis, Admonitions höchstens 1–2 je Seite, `shell` ohne Prompt, `console` nur mit Ausgabe, keine Ellipsen in Code, keine Blog-Links.
- **Jede Seite genau ein Quadrant.** Mischseiten sind ein Planfehler, nicht ein Stilfehler.
- **`html_meta` wird weggelassen** — Plone-spezifisch (Skill 10e), wie in kup6s.
- **Theme:** `sphinx-book-theme`. Begründung: `plone-sphinx-theme` wickelt genau dieses ein, also bleibt jedes Markup des Skills gültig und nichts muss umgeschrieben werden.
- **Sprache:** alles unter `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/` ist **englisch**. Deutsch bleiben nur `docs/superpowers/**` (eingefroren), `NOTIZEN.md` und `.superpowers/**`.
- **Abhängigkeiten:** jede neue Abhängigkeit kommt mit einem Eintrag in `DEPENDENCIES.md`, mit Datum und Beleg (CLAUDE.md). Die Belege für alle sieben stehen in Aufgabe 1, Schritt 2 — abschreiben, nicht neu erheben.
- **Eine Quelle der Wahrheit für Werkzeugfassungen:** `uv.lock`. Der Doku-Workflow ruft `uv run`, nennt keine Fassung.
- **Attribution:** Commit-Botschaften englisch, `Assisted-By:`, **nie** `Co-Authored-By:`.
- **Keine neuen import-linter-Ausnahmen, kein `# type: ignore`.** Eine Unterdrückung kommt nur mit Regelnamen und Grund daneben und wird in die Liste in `CLAUDE.md` eingetragen.
- **Der festgenagelte Hash-Vektor in `tests/test_hashing.py` bleibt unangetastet**, samt seiner drei deutschen Zeichenketten. Schlägt er an, hat die Aufgabe etwas kaputt gemacht.
- **Direktiven mit Prosa darin bekommen Doppelpunkt-Fences** (`:::{note}`), nicht Backticks. Backticks bleiben für Code. Begründung unten — das ist keine Stilfrage, sondern die Bedingung dafür, dass das Vale-Tor überhaupt greift.

### Warum Doppelpunkt-Fences, und nicht Backticks

Ein Befund der Prüfung von Aufgabe 1, mittlere Schwere, und er betrifft jede
folgende Aufgabe: **Vale prüft keinen Text innerhalb einer Backtick-Fence.** Es
hält sie für einen Codeblock und überspringt sie — und zwar auch dann, wenn
eine MyST-Direktive darin steht und der Inhalt reine Prosa ist.

Nachgemessen in einer Datei mit drei Stellen:

```
Zeile  3  (reine Prosa)             ->  beanstandet
Zeile  6  (in ```{note} …)          ->  NICHT beanstandet
Zeile 10  (in :::{note} …)          ->  beanstandet
```

Das heißt: Admonitions, Karten, Tabs — genau die Stellen, an denen in einer
Dokumentation gern wichtige Sätze stehen — lägen außerhalb des Stil-Tors. Ein
Tor mit einem blinden Fleck an der interessantesten Stelle ist schlechter als
eines, dessen Grenzen man kennt.

`colon_fence` ist in `docs/conf.py` bereits eingeschaltet, die Lösung kostet
also nichts: **`:::{note}` statt ```` ```{note} ````.** Beim Verschachteln
zählt die Zahl der Doppelpunkte, wie bei Backticks — außen `::::`, innen
`:::`.

Code**blöcke** bleiben bei Backticks; dort ist das Überspringen richtig.

## Diagramme

Der Auftraggeber wünscht Mermaid-Diagramme, **wo sie Sinn machen**. Das ist
der schwierigere Teil der Vorgabe, denn ein Diagramm, das nur wiederholt, was
der Absatz daneben sagt, kostet Pflege und bringt nichts — dieselbe Regel, die
der Doku-Skill für Admonitions aufstellt.

**Vier Stellen, an denen ein Diagramm mehr kann als die Prosa:**

| Seite | Diagramm | Warum es trägt |
|---|---|---|
| `explanation/hash-chain.md` | `graph LR`, drei Events mit `prev_hash`-Kanten, und die Digest-Umleitung `payload → payload_hash → event hash` | Die **Umleitung** ist der Kern der Tilgungs-Naht und in Prosa zäh: man muss sehen, dass die Kette den Digest hält und nicht den Inhalt |
| `explanation/concurrency.md` | `sequenceDiagram`, zwei Schreiber, dieselbe Spitze, einer gewinnt am Unique-Index, der Verlierer liest neu und wiederholt | Ein Rennen ist ein Ablauf über Zeit; genau dafür ist ein Sequenzdiagramm da, und der Text braucht sonst vier Absätze |
| `explanation/module-boundaries.md` | `graph TD`, `cli → core → storage → contract`, die zwei benannten Ausnahmen gestrichelt | Die Ausnahmen sind der ganze Punkt, und als gestrichelte Kanten sieht man auf einen Blick, dass es genau zwei sind |
| `reference/database-schema.md` | `erDiagram` mit `event`, `unit`, `source_key` und ihren Beziehungen | Drei Tabellen mit Fremdschlüsseln und einer Eindeutigkeitsbedingung je Event — eine Tabelle sagt die Spalten, das Diagramm sagt die Form |

**Ausdrücklich kein Diagramm:**

- `explanation/canonicalization.md` — eine Liste von Einschränkungen ist eine Liste; ein Diagramm wäre Dekoration.
- Die Tutorials — ein Tutorial will sichtbare Ergebnisse nach jedem Schritt, nicht ein Bild vom Ganzen.
- Die How-tos — Schrittfolgen, die der Leser abarbeitet; ein Ablaufdiagramm daneben wäre dieselbe Information zweimal.

### `:alt:` wirkt hier nicht — ein Satz Prosa statt eines Attributs

In Aufgabe 2 gemessen und bestätigt: mit `mermaid_output_format = "raw"` —
der Vorgabe dieses Projekts — nimmt `sphinxcontrib-mermaid` einen Pfad, der
die `:alt:`-Option **nie liest**. Das gerenderte Diagramm trägt kein `alt`
und kein `aria-label`; die Attribute im HTML stammen alle vom Theme (Suche,
Navigation, Farbmodus).

Die naheliegende Lösung wäre `svg`-Ausgabe mit dem `mmdc`-Werkzeug — und
damit eine Node.js-Werkzeugkette in einem Python-Projekt, für vier
Diagramme, gegen die Regel „`uv.lock` ist der einzige Ort, an dem eine
Werkzeugfassung gepinnt wird". **Abgelehnt.**

Stattdessen gilt für jedes Diagramm:

- **kein `:alt:`.** Eine Option, die aussieht, als erledigte sie
  Barrierefreiheit, aber nichts tut, ist schlimmer als keine — irgendwann
  glaubt jemand, das Häkchen sei gesetzt.
- **eine `:caption:`** — die rendert, nachgemessen.
- **ein Satz Prosa davor**, der sagt, was das Diagramm zeigt. Dann steht die
  Information als Text da, unabhängig davon, ob das Diagramm rendert, und bei
  einem Diagramm ist ein beschreibender Satz ohnehin mehr wert als ein
  Attribut.

**Mermaid-Blöcke bleiben bei Backticks**, anders als Direktiven mit Prosa.
In Aufgabe 5 gemessen: eine `:::{mermaid}`-Fence baut sauber und rendert ein
**byteidentisches** `<figure>`, zieht aber den Diagrammtext in den
Geltungsbereich von Vale, das dann über `payload_hash`, `units_hash` und
`event_hash` stolpert (drei `Vale.Spelling`-Treffer). Der Diagrammtext ist
Code, nicht Prosa — das Überspringen ist dort richtig. Der Satz davor und die
`:caption:` stehen ohnehin außerhalb der Fence und werden geprüft.

Syntax:

````markdown
```{mermaid}
:caption: The chain holds a digest of the payload, not the payload

graph LR
    e1[event 1] --> e2[event 2] --> e3[event 3]
```
````

## Review Focus

Fünf Fehlerarten, die dieser Plan erzeugt und die keine Standardprüfung fängt. Jede hat unten einen Test in der Aufgabe, die den Code besitzt.

1. **Ein Doku-Label in einem Code-Kommentar, das es nicht gibt.** Sphinx prüft `{ref}` nur *innerhalb* der Doku — ein `{ref}` in einem Python-Kommentar prüft **niemand**. Nach Aufgabe 7 stehen 72 solche Verweise im Code. Test in Aufgabe 7.
2. **Abgetippte Ausgabe veraltet.** Die Testzahl in der README ist in dieser Sitzung **zweimal** veraltet. Das Tutorial trägt eine ganze Sitzung. Test in Aufgabe 3.
3. **Sphinx zieht die deutschen Specs mit in den Lauf.** `docs/superpowers/**` liegt unter `docs/`; ohne ausdrücklichen Ausschluss baut Sphinx 2000 Zeilen Deutsch mit, wirft Warnungen über fehlende Toctree-Einträge und veröffentlicht Pläne. Test in Aufgabe 1.
4. **Vale läuft über deutschen Text.** Vale prüft amerikanisches Englisch. Ohne begrenzten Geltungsbereich meldet es auf `docs/superpowers/**` und `NOTIZEN.md` hunderte Treffer und ist damit nutzlos. Test in Aufgabe 1.
5. **`linkcheck` macht das Tor flaky.** Die Doku zitiert externe URLs (Hetzner, GitHub, Ceph, pgBackRest). Ein blockierendes Tor, das an einer Ratenbegrenzung scheitert, wird abgeschaltet — und der Skill verbietet ausdrücklich, linkcheck abzuschalten, um kaputte Links zu verstecken. Entscheidung und Test in Aufgabe 1.

---

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

## Task 2: Reference

**Files:**
- Create: `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/reference/database-schema.md`, `docs/reference/hash-format.md`
- Modify: `docs/reference/index.md`

**Interfaces:**
- Consumes: den Baum aus Aufgabe 1.
- Produces: die Label `(cli-reference)=`, `(configuration-reference)=`, `(database-schema)=`, `(hash-format)=`. Aufgabe 7 verweist aus dem Code darauf.

Reference ist der Quadrant, der sich gegen den Code prüfen lässt — tu das, statt aus dem Gedächtnis zu schreiben.

- [ ] **Schritt 1: `docs/reference/cli.md`**

Quadrant: Reference. Keine Anleitung, keine Begründung, nur Tatsachen.

Die Oberfläche steht in `src/previously/cli.py:169-190`. Vier Unterbefehle:

| Befehl | Argumente |
|---|---|
| `append` | `--source` (Pflicht), `--external-id` (Pflicht), `--text` (Pflicht), `--occurred-at`, `--evidence` (Vorgabe `recollection`, erlaubt `verbatim`/`recollection`) |
| `log` | `--from` (Vorgabe 1), `--limit` (Vorgabe 50) |
| `verify` | keine |
| `show` | `event_id` (Positionsargument) |

Dazu je Befehl die Rückgabewerte. Lies sie aus `cli.py` ab, erfinde sie nicht: 0 bei Erfolg, 1 wenn `verify` einen Befund meldet, 2 bei einem Eingabe- oder Speicherfehler. Nenne, dass `append` genau eine `id` je Event ausgibt und dass derselbe `(source, external_id)` zweimal im selben Aufruf abgewiesen wird.

- [ ] **Schritt 2: `docs/reference/configuration.md`**

Nur eine Variable, aber sie hat drei Eigenschaften, die ein Nachschlagender braucht: `PREVIOUSLY_DSN`, Form `postgresql+psycopg://user:pass@host:5432/datenbank`, und die Rangfolge aus `migrations/dsn.py` — ein ausdrückliches `sqlalchemy.url` schlägt die Umgebungsvariable, ohne beides ein Fehler, der beide nennt.

```{important}
PostgreSQL 15 or newer.
`NULLS NOT DISTINCT` is not optional; see {ref}`concurrency`.
```

- [ ] **Schritt 3: `docs/reference/database-schema.md`**

Drei Tabellen aus `src/previously/storage/schema.py`, als Tabelle je Tabelle: Spalte, Typ, Nullbarkeit, eine Zeile Bedeutung. Dazu die Indexe und Beschränkungen **namentlich**, weil die Namen in Fehlermeldungen auftauchen: `event_pkey`, `event_hash_idx`, `event_prev_hash_idx`, `event_kind_check`, `event_payload_object_check`, `unit_seq_check`, `source_key_pkey`, `source_key_event_id_key`.

- [ ] **Schritt 4: `docs/reference/hash-format.md`**

Die elf Felder des Event-Hashes und die drei des Einheiten-Hashes, abgeschrieben aus `src/previously/core/hashing.py`. Dazu der festgenagelte Vektor als Beispiel — **die Hex-Werte aus `tests/test_hashing.py` abschreiben, nicht neu rechnen.**

```{warning}
Do not recompute these values.
They are pinned in `tests/test_hashing.py`, and recomputing them to make a test pass destroys the proof that the hash is reproducible.
```

- [ ] **Schritt 5: In den Toctree eintragen und bauen**

```shell
make -C docs html
make -C docs vale
```

- [ ] **Schritt 6: Gegen den Code prüfen**

Geh jede Tabelle und jede Liste einmal gegen die Quelle durch und notiere im Bericht, welche Datei du für welche Seite gelesen hast. Eine Reference, die vom Code abweicht, ist schlimmer als keine.

- [ ] **Schritt 7: Commit**

`docs: reference for the command line, configuration, schema and hash format`

---

## Task 3: Tutorial, und die README schrumpft

**Files:**
- Create: `docs/tutorials/record-your-first-event.md`, `tests/test_docs_typed_output.py`
- Modify: `docs/tutorials/index.md`, `README.md`

**Interfaces:**
- Produces: Label `(first-event-tutorial)=`. Die README verweist darauf.

- [ ] **Schritt 1: Die Sitzung abtippen**

In einem **frischen** Checkout gegen ein echtes PostgreSQL 17, in **einem** zusammenhängenden Lauf: `uv sync --all-extras`, `PREVIOUSLY_DSN` setzen, `uv run alembic upgrade head`, ein `append`, ein `log`, ein `verify`, ein `show`, dann `uv run pytest`.

**Tipp jeden Befehl selbst ab und übernimm die echte Ausgabe.** In dieser Sitzung hat genau dieses Abtippen zweimal einen echten Fehler gefunden: `alembic upgrade head` scheiterte ohne DSN, und `uv sync` installiert die Extras nicht.

**Den Testlauf tippst du zuletzt ab**, nach allem anderen in dieser Aufgabe — sonst ist die Zahl sofort wieder alt (Prüfbefund N-7).

- [ ] **Schritt 2: Die Seite schreiben**

Quadrant: Tutorial. Also: ein garantierter Pfad, keine Alternativen, keine Erklärung, sichtbares Ergebnis nach jedem Schritt, erste Person Plural („We will record…"), Beobachtungshinweise („Notice that the chain now has one event.").

Der Hash in der `show`-Ausgabe ist **nicht reproduzierbar**, weil `recorded_at` in den Hash eingeht. Sag das an der Stelle, mit einer `note`, und erfinde keinen festen Beispielhash.

- [ ] **Schritt 3: Den Test schreiben, der die Testzahl festnagelt**

`tests/test_docs_typed_output.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed-out output is a measurement with a date, so it needs a gate.

The test count in the README went stale twice in one session: it was typed
out, then later commits added tests. Only one number in the documentation is
derivable from the tree, and this test derives it.
"""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = [ROOT / "docs" / "tutorials" / "record-your-first-event.md"]


def _collected() -> int:
    result = subprocess.run(  # noqa: S603 — our own interpreter, fixed arguments
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, result.stdout
    return int(match.group(1))


def test_typed_test_counts_match_the_tree() -> None:
    expected = _collected()
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        for claimed in re.findall(r"(\d+) passed", text):
            assert int(claimed) == expected, (
                f"{page.name} claims {claimed} passing tests, the tree has {expected}. "
                "Retype the test run; it is the last thing you do."
            )
```

- [ ] **Schritt 4: Test laufen lassen**

Run: `uv run pytest tests/test_docs_typed_output.py -v`
Expected: PASS, wenn die abgetippte Zahl stimmt. Scheitert er, tipp den Lauf neu ab — **rechne die Zahl nicht von Hand hoch.**

- [ ] **Schritt 5: Die README schrumpfen**

Drin bleiben: was Previously ist (zwei Sätze), der Stand (Stufe 1a), Lizenz, und ein Zeiger in die Doku. Raus kommt der Durchlauf — er steht jetzt im Tutorial, in **einer** Fassung.

Richtigstelle dabei, was die README heute noch behauptet: der Abschnitt „Language" gibt die **alte** Sprachregel wieder und widerspricht der `CLAUDE.md`.

- [ ] **Schritt 6: Alle Tore**

```shell
make -C docs html
make -C docs vale
uv run pytest
```

- [ ] **Schritt 7: Commit**

`docs: a tutorial that was actually typed out, and a shorter README`

---

## Task 4: How-to guides

**Files:**
- Create: `docs/how-to/verify-the-chain.md`, `docs/how-to/restore-from-a-backup.md`, `docs/how-to/add-a-migration.md`
- Modify: `docs/how-to/index.md`

- [ ] **Schritt 1: `verify-the-chain.md`**

Titel nennt das Ziel: „How to check the chain in operation". Öffnet mit „This guide shows you how to…". Inhalt: `previously verify` aufrufen, den Rückgabewert auswerten (0 heißt intakt, 1 heißt Befund), die Befundtexte nachschlagen, und was **nicht** gedeckt ist — mit `{ref}` auf die Explanation, nicht mit einer Erklärung an dieser Stelle.

- [ ] **Schritt 2: `restore-from-a-backup.md`**

```{important}
A restore that was never rehearsed is not a backup.
```

Inhalt: wiederherstellen, dann **`previously verify` gegen den wiederhergestellten Bestand** laufen lassen — das ist der Punkt, der diese Wiederherstellung von einer gewöhnlichen unterscheidet, denn die Kette prüft den Inhalt und nicht nur, dass Postgres startet.

Die Passphrase: ohne sie ist der Restore unmöglich. Verweise auf die Reference für die Konfiguration und auf die Explanation für den Grund.

- [ ] **Schritt 3: `add-a-migration.md`**

Inhalt: `uv run alembic revision -m …`, die Revision schreiben, `uv run alembic upgrade head`, und der Test, der jeden in `metadata` erklärten Index gegen `pg_indexes` hält. Nenne ausdrücklich, dass `postgresql_nulls_not_distinct=True` in **beiden** Orten stehen muss (Schema und Migration), weil ein `autogenerate` den Index sonst still fallen lässt.

- [ ] **Schritt 4: Die drei Seiten in den Toctree von `docs/how-to/index.md` eintragen**

Nicht vergessen: das Tor fährt `sphinx-build -W`, und eine Seite, die in
keinem Toctree steht, erzeugt „document isn't included in any toctree" — unter
`-W` also einen Fehlschlag.

- [ ] **Schritt 5: Tore und Commit**

`docs: how-to guides for verification, restore and migrations`

---

## Task 5: Explanation, Teil 1 — die Kette

**Files:**
- Create: `docs/explanation/hash-chain.md`, `docs/explanation/canonicalization.md`
- Modify: `docs/explanation/index.md`

**Interfaces:**
- Produces: Label `(hash-chain)=`, `(hash-domain)=`, `(tombstone-seam)=`, `(canonicalization)=`, `(timestamps)=`. Aufgabe 7 bildet Paragraphen darauf ab.

**Quelle:** `docs/superpowers/specs/2026-10-02-stufe-1a-log.md` §3.1–§3.4 und
**§6**, und `docs/superpowers/specs/2026-10-01-architektur.md` §4.6.

§6 (die Zerlegung in Einheiten) war in keiner Aufgabe dieses Plans
untergebracht — eine Lücke, die beim Vorbereiten der Überlebensliste
auffiel. Sie gehört hierher und nicht auf eine eigene Seite: wer liest,
**warum** die Einheiten im Hash stecken, will im selben Atemzug wissen, was
eine Einheit überhaupt ist. Dazu gehört der CRLF-Fund, einer der fünf stillen
Datenverluste dieses Projekts — ohne Normalisierung von `\r\n` käme ein
E-Mail-Text als **eine** Einheit an und hebelte damit die Zerlegung aus, auf
der das ganze Zuordnungsmodell beruht.

- [ ] **Schritt 1: `hash-chain.md` übersetzen**

Quadrant: Explanation. Also diskursiv, verbindend, begründend — und **keine** Anleitung, **keine** Faktenlisten (die stehen in der Reference).

Diese Begründungen müssen hinüberkommen, jede mit ihrer Zahl und ihrer Messung:

- warum der Hash den **Digest** der Nutzlast deckt und nicht die Nutzlast — die Tilgungs-Naht, und ihr Preis: ein Grabstein ist heute von einer Fälschung nicht zu unterscheiden, weil es kein Tilgungs-Event gibt
- warum `id = Vorgänger.id + 1` und **keine** Sequenz: eine Sequenz garantiert die Commit-Reihenfolge nicht, die Kette wäre 9 → 11 → 10
- warum `recorded_at` **Eingabe** ist und nicht Ausgabe
- warum Einheiten und Quellenangabe dazugehören — mit den drei gemessenen Fälschungen, die vorher durchgingen
- was die Kette **nicht** deckt: Spitze löschen, ein selbst gehashtes Event anhängen, die Kette neu schreiben. Mit der Zuspitzung, dass Anhängen schärfer ist als Löschen, und dem Satz, der das Kapitel schließen soll: *What the log says is unaltered; that it is complete, the log cannot attest by itself.*

**Übersetzen heißt nicht kürzen.** Lass keine Messung und keine Zahl weg. Ein Absatz, der danach nur noch sagt *was* gilt statt *warum*, ist ein Verlust, den niemand bemerkt.

- [ ] **Schritt 2: `canonicalization.md` übersetzen**

Aus §3.2: JCS nach RFC 8785, und warum der Nutzlastbereich absichtlich eng ist — keine Gleitkommazahlen, Schlüssel auf `^[a-z][a-z0-9_]*$`, ganze Zahlen in ±(2⁵³−1), keine Nullbytes, keine einsamen Surrogate. Je Einschränkung der Grund, nicht nur die Regel.

- [ ] **Schritt 3: Den Querverweis nachrüsten, den Aufgabe 2 weglassen musste**

`docs/reference/configuration.md` sollte laut meinem Brief auf
`{ref}`concurrency`` verweisen. Aufgabe 2 hat die Zeile zu Recht weggelassen
und das gemessen: `WARNING: undefined label: 'concurrency' [ref.ref]`, unter
`-W` ein Fehlschlag — das Label entsteht erst hier. Jetzt existiert es, also
trag den Verweis dort ein, wo er hingehört: bei der Angabe, dass PostgreSQL 15
die Untergrenze ist und `NULLS NOT DISTINCT` nicht optional.

- [ ] **Schritt 4: Beide Seiten in den Toctree von `docs/explanation/index.md` eintragen**

Das Tor fährt `sphinx-build -W`; eine Seite ohne Toctree-Eintrag lässt den Bau
scheitern. Aufgabe 6 trägt später **weitere** Seiten in dieselbe Datei ein —
schreib deinen Eintrag so, dass ein Anfügen daneben keine Konflikte macht.

- [ ] **Schritt 5: Tore und Commit**

`docs: explain the hash chain and the canonicalization`

---

## Task 6: Explanation, Teil 2 — Nebenläufigkeit, Grenzen, Backups

**Files:**
- Create: `docs/explanation/concurrency.md`, `docs/explanation/module-boundaries.md`, `docs/explanation/backup-encryption.md`
- Modify: `docs/explanation/index.md`

**Interfaces:**
- Produces: Label `(concurrency)=`, `(conflict-classes)=`, `(module-boundaries)=`, `(backup-encryption)=`.

**Quelle:** 1a-Spec §4.1–§4.4 und §8, Architektur §2, §10.1, §10.5.

- [ ] **Schritt 1: `concurrency.md`**

Die beiden Unique-Indexe als **gesamte** Nebenläufigkeitssteuerung — kein Advisory-Lock, kein `FOR UPDATE`. Warum `NULLS NOT DISTINCT` nicht optional ist. Die drei Konfliktklassen mit **zwei** Wiederherstellungen, und warum der Quellschlüssel-Zweig nicht zurückweicht: unter READ COMMITTED kann die Verletzung erst entstehen, **nachdem** der Wettbewerber committet hat, es kann also keinen Partner im Gleichschritt geben. Warum welcher Index zuerst anschlägt an der Index-OID-Reihenfolge hängt und darum alle drei in denselben Fehler übersetzt werden.

- [ ] **Schritt 2: `module-boundaries.md`**

`cli` → `core` → `storage` → `contract`, als Verträge geprüft. Warum die beiden Ausnahmen **namentlich** aufgezählt sind und nicht gemustert — samt der Messung mit dem Wegwerfmodul, die zeigt, dass ein Wildcard eine neue Kante lautlos durchlässt. Warum es den Riegel im Testlauf gibt. Und dass ein `LogStore[Conn]`-Protokoll die Ausnahmen ersatzlos entbehrlich machen würde.

- [ ] **Schritt 3: `backup-encryption.md`**

Aus Architektur §10.5, das die vollständige Abwägung schon trägt: dass Hetzner **gar keine** Verschlüsselung im Ruhezustand hat, dass SSE-C bei Kopien bricht (Ceph), dass barman-cloud clientseitig nicht kann, der Preis der Passphrase, und die drei Wege A/B/C samt dem, was A umstoßen würde.

- [ ] **Schritt 4: Dem Nutzlastbereich eine Heimat in der Reference geben**

Befund mittlerer Schwere aus der Prüfung von Aufgabe 5, und er muss **vor dem
Einfrieren** behoben sein: `^[a-z][a-z0-9_]*$` und `±(2**53 − 1)` kommen in
`docs/reference/`, `docs/how-to/`, `docs/tutorials/` und `docs/index.md`
**nirgends** vor. Sie stehen allein in der Explanation.

Das ist die falsche Heimat. Der Nutzlastbereich ist eine **Pflichtmenge für
jeden Aufrufer** — wer einen Konnektor schreibt, schlägt nach, was eine
Nutzlast enthalten darf, und schlägt es in der Reference nach, nicht in einem
Aufsatz über Kanonisierung. Ab Aufgabe 7 wäre die einzige maßgebliche Quelle
dafür eine Explanation-Seite.

Zu tun: einen Abschnitt in `docs/reference/hash-format.md` (dort gehört er hin,
denn er sagt, was gehasht werden **darf**), mit den fünf Einschränkungen als
Tatsachen — keine Gleitkommazahlen, Schlüsselmuster, Zahlenbereich, keine
Nullbytes, keine einsamen Surrogate — und je Zeile die Fehlermeldung, die
`core/canonical.py` dazu ausgibt. Lies sie dort ab. Dann verweist
`canonicalization.md` dorthin statt die Werte zu tragen, und behält die
Begründung.

- [ ] **Schritt 5: Die fünf stillen Datenverluste auflistbar machen**

Zweiter Befund derselben Prüfung: die Explanation sagt zweimal „one of the five
silent losses of data", und diese Fünf sind aus `docs/` **nicht auflösbar** —
nirgends steht eine Liste. Der einzige Anker ist die Spezifikation, die „der
fünfte … **dieser Sitzung**" sagt und in Aufgabe 7 einfriert. Der CRLF-Fund ist
überhaupt nirgends als einer der fünf verzeichnet.

Zu tun: eine Seite `docs/explanation/silent-losses.md`, Label
`(silent-losses)=`, die die fünf **nennt**, je in zwei bis drei Sätzen, und
sagt, was sie verbindet. Es sind:

1. Der reservierte Schlüssel `evidence` — eine Nutzlast, die ihn schon trug,
   wäre still überschrieben worden, und die Belegart ist in einem append-only
   Speicher nicht nachtragbar.
2. CRLF-Text, der als **eine** Einheit angekommen wäre und damit die Zerlegung
   ausgehebelt hätte, auf der das Zuordnungsmodell beruht.
3. Einheiten und Quellenangabe waren von der Kette **nicht gedeckt** — drei
   gemessene Fälschungen gingen durch.
4. JSON-`null` galt als Grabstein, war aber für die Grabstein-Abfrage
   unsichtbar.
5. Derselbe Quellschlüssel zweimal in einem Stapel verwarf den Inhalt des
   zweiten Eintrags und gab dem Aufrufer trotzdem zwei `id`s zurück.

Das Verbindende gehört dazu, denn es ist die Lehre des Projekts: **keiner war
ein Programmierfehler.** Jeder war eine Lücke zwischen einer Zusage und der
Wirklichkeit, und jeder wurde durch Messen gefunden, nicht durch Lesen. In
einem append-only Speicher ist jeder davon unwiederbringlich gewesen.

Danach lösen die zwei Verweise in `hash-chain.md` und `canonicalization.md`
auf — setz dort `{ref}`silent-losses``.

- [ ] **Schritt 6: Die drei Seiten in den Toctree von `docs/explanation/index.md` eintragen**

Aufgabe 5 hat dort schon zwei Einträge; füge deine an, ohne die bestehenden
anzufassen. Das Tor fährt `sphinx-build -W`, eine Seite ohne Eintrag lässt den
Bau scheitern.

- [ ] **Schritt 7: Tore und Commit**

`docs: explain concurrency, the module boundaries and the backup encryption`

---

## Task 7: Die Specs einfrieren, die 72 Verweise umstellen — und ein Tor, das sie hält

**Files:**
- Create: `tests/test_docs_references.py`, `docs/explanation/design-records.md`
- Modify: 21 Dateien unter `src/`, `tests/`, `migrations/` (Liste unten), dazu `docs/superpowers/specs/2026-10-01-architektur.md`, `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`, `docs/superpowers/specs/2026-10-01-previously-design.md`

**Interfaces:**
- Consumes: alle Label aus den Aufgaben 2, 5 und 6.

**Gemessener Ist-Stand (2026-10-03):** 72 Vorkommen von `§x.y` in `src/` (39), `tests/` und `migrations/`, über 21 Dateien, auf **20** verschiedene Paragraphen. Häufigste: §3.2 (12×), §3.1 (9×), §5.1 (8×), §5 (5×), §4.2 (5×), §3.4 (5×).

### Das Einfrieren ist ein Vorgang, kein Ereignis

Hier hatte ich den Plan zunächst falsch gefasst, und die Korrektur kommt vom
Auftraggeber: **Deutsch ist seine Autorensprache für Absicht**, nicht ein
Altbestand, den man abarbeitet. „Mit Deutsch kann ich mich besser ausdrücken,
was ich will."

Daraus folgt: jede künftige Stufe wird **wieder** mit einem deutschen Spec
beginnen, und der friert ein, sobald seine Explanation-Seiten stehen. Das
Einfrieren ist also ein wiederkehrender Schritt im Ablauf und nichts, was
dieser Plan ein einziges Mal erledigt. Schreib es als Ablauf hin, nicht als
Zustand — sonst liest die nächste Stufe die eingefrorenen Specs als Verbot,
einen neuen zu schreiben.

- [ ] **Schritt 1: Die drei Specs einfrieren**

Oben in jedes Dokument, auf Deutsch (die Specs sind und bleiben deutsch):

```markdown
> **Eingefrorener Entwurfsbericht, Stand 2026-10-03.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in `docs/explanation/`; weicht
> dieses Dokument davon ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen.
```

Dieser Schritt kommt **zuerst**, und zwar aus einem Grund, der die
Aufgabenteilung erklärt: die Verweise, die du unten umstellst, bezeichnen die
Specs als „frozen design record". Frierst du erst danach ein, behauptet jeder
dieser Verweise beim Schreiben etwas Unwahres — genau der Fehler, den diese
Umstellung beheben soll (Ruling P2 der Vorab-Durchsicht).

- [ ] **Schritt 2: Die Verweise aus der README mitnehmen**

Nicht nur der Code verweist auf die Specs. `README.md` sagt „§11 of the stage
1a specification states which forgeries are covered and which are not", und
die Dokumententabelle darunter verlinkt alle drei Specs mit einer Zeile
Inhaltsangabe.

Nach dem Einfrieren zeigen diese Verweise auf eingefrorene Berichte. Für die
Tabelle ist das richtig — sie beschreibt Provenienz. Für den §11-Satz nicht:
er beantwortet eine **heutige** Frage („welche Fälschungen sind gedeckt?") und
gehört damit auf `{ref}`hash-chain`` bzw. die Explanation-Seite, die die
Grenzen trägt. Zieh ihn dorthin und kennzeichne die Tabellenzeilen als
eingefrorene Berichte.

- [ ] **Schritt 3: Die zwei Prosa-Verweise aus den How-tos in `{ref}` umwandeln**

Aufgabe 4 durfte noch keine `{ref}` auf Explanation-Label setzen — die gab es
nicht, und ein Vorwärtsverweis bricht das Tor. Sie hat die Sätze darum als
reine Prosa formuliert, **ohne** Marker, weil ein sichtbares TODO Vale
beanstandet hätte. Damit du sie nicht suchen musst, hier ihre Fundstellen:

| Datei | Zeile | Satz |
|---|---|---|
| `docs/how-to/verify-the-chain.md` | 29 | „For what the chain guarantees and where that stops, see the explanation of the hash chain." |
| `docs/how-to/restore-from-a-backup.md` | 29 | „For why losing the passphrase means losing the backups for good, see the explanation of backup encryption." |

Wandle beide in `{ref}`-Verweise auf die jetzt existierenden Label um
(`hash-chain` und `backup-encryption`). Prüfe danach mit `grep`, ob in den
Quadranten weitere Sätze dieser Form stehen — die Zeilennummern oben
verschieben sich, sobald jemand die Seiten anfasst, der Wortlaut nicht.

- [ ] **Schritt 4: Die Abbildungstabelle festlegen**

Nicht 72 Entscheidungen, sondern 20 — je Paragraph ein Ziel. Schreib die Tabelle nach `docs/explanation/design-records.md`, zusammen mit dem Hinweis, dass die Specs eingefroren sind und wofür sie noch gut sind (Provenienz: „so wurde es damals entschieden").

Beispiele: §3.1 → `{ref}`hash-domain``, §3.2 → `{ref}`canonicalization``, §3.4 → `{ref}`hash-chain``, §4.2 → `{ref}`conflict-classes``, §2 und §8 → `{ref}`module-boundaries``, §4.6 und §10.5 → `{ref}`backup-encryption``.

Für Paragraphen, deren Begründung **nicht** in die Doku wandert, bleibt der Verweis auf den eingefrorenen Bericht — aber ausdrücklich als solcher gekennzeichnet, etwa „architecture §10.2 (frozen design record)". Ein Verweis, der nicht sagt, dass sein Ziel eingefroren ist, lügt über seine Aktualität.

### Drei Klassen von Verweis, nicht eine — nachgemessen am 2026-10-03

Der Plan hat diese Aufgabe zunaechst als *eine* Umstellung gefasst: 72
Kommentarverweise auf Doku-Label. Nachgemessen sind es drei Klassen, und die
dritte haette der Test aus Schritt 5 **durchgewinkt**.

**Klasse 1 — lebende Begruendung in Kommentar oder Docstring.** Sie erklaert,
warum der Code heute so ist. Sie muss auf die Doku zeigen, denn sie wird mit
dem Code gepflegt. Das sind die 70 Faelle, die die Tabelle aus Schritt 4
abbildet.

**Klasse 2 — datierte Entscheidung.** Sie zitiert, *wie damals entschieden
wurde*. Fuer sie ist der eingefrorene Bericht die **richtige** Quelle: das
Einfrieren ist gerade das, was ihn zitierfaehig macht. Hierher gehoeren die
Verweise auf Pruefbefunde und Rulings (die der Plan schon ausnimmt) und das
`DEPENDENCIES.md`, dessen 13 Verweise je eine Zeile eines datierten
Entscheidungsregisters begruenden. Sie bleiben — aber mit `(frozen design
record)` gekennzeichnet, denn die Regel aus Schritt 4 gilt fuer jede
englischsprachige Datei, nicht nur fuer `.py`.

**Klasse 3 — Programmausgabe.** Zwei Verweise stehen nicht in einem Kommentar,
sondern in einer Fehlermeldung, die der Nutzer auf dem Terminal liest:

| Datei | Zeile | Was gedruckt wird |
|---|---|---|
| `src/previously/core/canonical.py` | 53 | `…floating point number not allowed — state a scale as an integer (§3.2)` |
| `src/previously/core/append.py` | 301 | `…kind of evidence (§5.1), so that it is not silently overwritten` |

Fuer diese beiden ist **keine** der zwei Behandlungen richtig. Ein
`{ref}`-Label in einer Programmausgabe erscheint dem Nutzer als wortwoertlicher
Unsinn, und `(§3.2, frozen design record)` in einer Fehlermeldung ist schlimmer
als der heutige Zustand: wer `previously append` aufruft, hat
`docs/superpowers/specs/` nicht und wird es auch nicht bekommen.

**Zu tun: die Zitierung aus der Meldung entfernen, nicht umschreiben.** Die
Meldungen tragen ihre Handlungsanweisung schon selbst — „state a scale as an
integer" sagt dem Aufrufer alles, was er tun kann; „(§3.2)" sagt ihm nichts.
Die Begruendung wandert in den Kommentar darueber, und der zeigt dann nach
Klasse 1 auf `{ref}`payload-range``.

Der Test aus Schritt 5 muss das erzwingen koennen, sonst schreibt der naechste
Umsetzer `(frozen design record)` in die Fehlermeldung und der Test ist gruen.
Siehe die Ergaenzung in Schritt 5.

### Was an dieser Aufgabe haengt und nicht in ihrer Dateiliste steht

`docs/reference/hash-format.md` zitiert seit Aufgabe 6 **fuenf** Fehlermeldungen
aus `core/canonical.py` woertlich, darunter die mit dem `§3.2`. Nachgemessen am
2026-10-03: alle fuenf stimmen heute buchstabengenau mit dem Code. Es haelt sie
aber **nichts** — `tests/test_docs_typed_output.py` deckt nur die Testzahlen im
Tutorial.

Daraus folgen zwei Dinge fuer diese Aufgabe:

1. Die Zeile `docs/reference/hash-format.md:22` aendert sich **im selben
   Commit** wie die Meldung in `canonical.py`. Der Plan sagte „diese Aufgabe
   fasst nur Kommentare an" — das war falsch, sie fasst eine Reference-Seite
   mit an. Die drei Vektortests bleiben als Riegel richtig, sie reichen aber
   nicht: sie sehen eine geaenderte Fehlermeldung nicht.
2. Der Test aus Schritt 5 bekommt die Aufgabe, die Zitate festzunageln — und
   zwar indem er die Meldungen **vom Code erzeugen laesst**, nicht indem er
   Zeichenketten in zwei Dateien vergleicht. Eine Zeichenkettensuche findet
   eine geaenderte Meldung nicht wieder; ein Aufruf von `canonical()` mit
   einem Gleitkommawert liefert sie.

`pyproject.toml:88` traegt den letzten Verweis ausserhalb des Codes
(`# Printing to stdout is what this module is for (§9 of the stage 1a spec)`).
Er begruendet eine heutige Lint-Ausnahme, ist also Klasse 1 — aber die
Begruendung steht schon vollstaendig im Satz davor. Streich die Klammer; ein
Verweis, der nichts hinzufuegt, ist nach dem Einfrieren nur noch ein toter
Zeiger.

- [ ] **Schritt 5: Den Test zuerst schreiben**

`tests/test_docs_references.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx checks cross-references inside the documentation.

Nobody checks a reference that sits in a Python comment. After the migration
there are dozens of them, so this test is the only thing standing between a
renamed label and a comment that points nowhere.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["src", "tests", "migrations"]
DOCS = ROOT / "docs"

REFERENCE = re.compile(r"\{ref\}`([a-z0-9-]+)`")
LABEL = re.compile(r"^\(([a-z0-9-]+)\)=\s*$", re.MULTILINE)


def _labels() -> set[str]:
    found: set[str] = set()
    for page in DOCS.rglob("*.md"):
        if "superpowers" in page.parts or "_build" in page.parts:
            continue
        found.update(LABEL.findall(page.read_text(encoding="utf-8")))
    return found


def _references() -> dict[str, list[str]]:
    used: dict[str, list[str]] = {}
    for directory in SOURCE_DIRS:
        for module in (ROOT / directory).rglob("*.py"):
            text = module.read_text(encoding="utf-8")
            for name in REFERENCE.findall(text):
                used.setdefault(name, []).append(str(module.relative_to(ROOT)))
    return used


def test_every_doc_reference_in_the_code_resolves() -> None:
    labels = _labels()
    dangling = {
        name: files for name, files in _references().items() if name not in labels
    }
    assert not dangling, (
        f"These labels are referenced from code but defined in no page: {dangling}. "
        "Either the label was renamed or the page was not written yet."
    )


def test_no_bare_paragraph_references_remain() -> None:
    """A bare `§3.1` points at a frozen German document without saying so."""
    offenders: dict[str, int] = {}
    for directory in SOURCE_DIRS:
        for module in (ROOT / directory).rglob("*.py"):
            text = module.read_text(encoding="utf-8")
            bare = [
                line
                for line in text.splitlines()
                if "§" in line and "frozen design record" not in line
            ]
            if bare:
                offenders[str(module.relative_to(ROOT))] = len(bare)
    assert not offenders, (
        f"Bare paragraph references remain: {offenders}. Map them to a {{ref}} label "
        "or mark them as pointing at a frozen design record."
    )
```

Dazu zwei Tests, die die zwei oben gemessenen Loecher schliessen. Der erste
haelt die Programmausgabe frei von Zitierungen, der zweite nagelt die
Reference-Zitate fest, indem er sie vom Code erzeugen laesst:

```python
RUNTIME_MESSAGE_FILES = [
    ROOT / "src" / "previously" / "core" / "canonical.py",
    ROOT / "src" / "previously" / "core" / "append.py",
]


def test_no_program_output_cites_a_specification() -> None:
    """A paragraph reference in an error message is a dead pointer.

    Whoever runs `previously append` has no `docs/superpowers/specs/`, so the
    citation buys them nothing even before the freeze makes it stale. Measured
    on 2026-10-03: two messages carried one, `canonical.py:53` with `§3.2` and
    `append.py:301` with `§5.1`. Marking them as a frozen design record would
    pass `test_no_bare_paragraph_references_remain` while making the output
    worse, which is why this test exists beside it.
    """
    offenders: dict[str, list[int]] = {}
    for path in RUNTIME_MESSAGE_FILES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if "§" in line and ('f"' in line or '"' in line and "raise" in line):
                offenders.setdefault(str(path.relative_to(ROOT)), []).append(number)
    assert not offenders, (
        f"These lines print a paragraph reference to the user: {offenders}. "
        "Move the reasoning into the comment above and drop it from the message."
    )


def test_the_reference_quotes_what_the_code_actually_prints() -> None:
    """The Payload range table quotes five messages verbatim.

    Nothing else holds them: the typed-output gate covers only the test counts
    in the tutorial. A string search across the two files would not help -- it
    would follow a changed message into the page. So the messages are produced
    by calling the code, which is the only form of this check that can fail for
    the right reason.
    """
    from previously.core.canonical import canonical
    from previously.core.errors import InvalidPayload

    produced = []
    for payload in (
        {"amount": 1.5},
        {"Total": 1},
        {"amount": 2**53},
        {"text": "a\x00b"},
        {"text": "a\ud800b"},
    ):
        try:
            canonical(payload)
        except InvalidPayload as error:
            produced.append(str(error))
        else:  # pragma: no cover - a passing payload would be the bug
            raise AssertionError(f"{payload!r} was accepted")

    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    for message in produced:
        # The page prefixes no path, the message does: compare the part the
        # page quotes, which is everything after `$`/`.name`/`[n]` and ": ".
        quoted = message.split(": ", 1)[1]
        assert quoted in page, (
            f"hash-format.md does not quote {quoted!r}. The code's message changed; "
            "the Payload range table has to change in the same commit."
        )
```

- [ ] **Schritt 6: Test laufen lassen — er muss scheitern**

Run: `uv run pytest tests/test_docs_references.py -v`
Expected: FAIL, `test_no_bare_paragraph_references_remain` listet 21 Dateien.

- [ ] **Schritt 7: Umstellen, Datei für Datei**

Die 21 Dateien: `src/previously/cli.py`, `core/{append,canonical,errors,hashing,units,verify}.py`, `storage/{postgres,rows,schema}.py`, `migrations/dsn.py`, `migrations/versions/0001_log.py`, `tests/{test_append,test_canonical,test_cli,test_contracts,test_hashing,test_properties,test_rows,test_schema,test_storage,test_verify}.py`.

Geh nach der Tabelle aus Schritt 1 vor, nicht nach Gefühl. Ändere **nur** den Verweis, nicht den Begründungstext darum.

Die Verweise auf Prüfbefunde und Rulings (`review finding B1`, `Ruling T8-c`) **bleiben wie sie sind** — sie bezeichnen Sitzungsgeschichte, nicht lebende Begründung, und für die ist der eingefrorene Bericht der richtige Ort.

- [ ] **Schritt 8: Tests laufen lassen — beide müssen bestehen**

Run: `uv run pytest tests/test_docs_references.py -v`

- [ ] **Schritt 9: Alle Tore, und der Vektor**

```shell
uv run pytest
make -C docs html
```

Erwartet unter anderem: `test_vector_payload_hash`, `test_vector_units_hash`, `test_vector_event_hash` grün. Diese Aufgabe fasst nur Kommentare an; schlägt einer der drei an, hast du mehr geändert als gedacht.

- [ ] **Schritt 10: Commit**

`docs: point the code at the documentation, and keep it honest with a test`

---

## Task 8: Die Regeln nachziehen

**Files:**
- Modify: `CLAUDE.md`

Das Einfrieren der Specs ist nach Ruling P2 der Vorab-Durchsicht **Teil von
Aufgabe 7** — es muss vor der Verweisumstellung passieren, sonst behaupten die
neuen Code-Verweise einen Zustand, den es noch nicht gibt. Diese Aufgabe
schreibt nur noch die Regeln.

- [ ] **Schritt 1: Die Sprachregel in `CLAUDE.md` nachziehen**

Sie sagt heute „German is fine — specifications, plans, …". Das bleibt
richtig, bekommt aber einen Ablauf dazu, und der ist der Kern dieser Aufgabe:

- **Ein Spec entsteht auf Deutsch.** Das ist Absicht und keine Nachlässigkeit:
  der Betreuer formuliert Absicht auf Deutsch genauer, und eine ungenau
  formulierte Absicht ist teurer als eine Übersetzung.
- **Die Begründung wird auf Englisch veröffentlicht**, in
  `docs/explanation/`, und ist dort maßgeblich.
- **Der Spec friert ein, sobald seine Explanation-Seiten stehen**, mit
  datiertem Kopf. Danach ist er Provenienz: „so wurde es damals entschieden".
- Weicht ein eingefrorener Spec von der Doku ab, **gilt die Doku**.

Schreib die Änderung als Änderung hin, nicht als wäre es immer so gewesen — die
Regel ist am 2026-10-03 entstanden und am selben Tag verfeinert worden, und das
ist für einen Leser nützlicher als eine glatte Fassung.

- [ ] **Schritt 2: Die Doku-Regel in `CLAUDE.md`**

Ein eigener Abschnitt, mit diesen Punkten:

- Alles wird dokumentiert, und zwar nach dem Skill `plone-doc-style:author` (aufrufbar unter genau diesem Namen).
- Ändert sich Code, wird **geprüft**, ob die Doku nachzuziehen ist, und die Änderung kommt im **selben** PR mit.
- Jede Seite genau ein Diátaxis-Quadrant.
- Ein Satz pro Zeile, sentence-case Überschriften, Bindestriche in Dateinamen, amerikanisches Englisch.
- Die Tore: `make -C docs html` (Warnung = Fehler), `make -C docs vale`, `make -C docs linkcheck`.
- Abgetippte Ausgabe ist eine **Messung mit einem Datum**: sie wird zuletzt abgetippt, und `tests/test_docs_typed_output.py` hält die Testzahl fest.
- Ein Doku-Label in einem Code-Kommentar prüft Sphinx nicht — das tut `tests/test_docs_references.py`.

- [ ] **Schritt 3: Die Lücke in der Sprachregel schließen**

Die Liste der englisch gebundenen Wurzel-Konfiguration in `CLAUDE.md` nennt
`pyproject.toml`, `.importlinter`, `alembic.ini` und `.pre-commit-config.yaml`
— **`.gitignore` fehlt**, und das war eine Auslassung, keine Entscheidung. Der
Umsetzer von Aufgabe 1 hat die Regel darum korrekt gelesen und die Datei
unangetastet gelassen; sie trägt weiter deutsche Abschnittskommentare
(`# Werkzeuge`, `# Editor und System`, `# Worktrees und Agenten-Arbeitsbereiche`).

Zu tun: `.gitignore` in die Liste aufnehmen und seine drei Abschnittskommentare
übersetzen. Begründung für den Kommentar daneben: die „Programmausgabe"-Hälfte
der Regel trifft auf `.gitignore` nicht zu — es wird nirgends gedruckt —, aber
die andere Hälfte schon: wer `pyproject.toml` liest, liest auch `.gitignore`.
Die zwei Zeilen, die Aufgabe 1 angefügt hat (`docs/_build/`, `.vale-styles/`),
bekommen dabei ihren Abschnitt.

- [ ] **Schritt 4: Alle Tore**

```shell
uv run pytest
make -C docs html
make -C docs vale
make -C docs linkcheck
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
```

- [ ] **Schritt 5: Commit**

`docs: write down the documentation rule`

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** Die Explanation-Aufgaben 5 und 6 decken aus dem 1a-Spec §3.1–§3.4 (Kette, Kanonisierung, Zeitstempel, Prüfung), §4.1–§4.4 (Anfügen, Konfliktklassen, keine Vorab-Sperre, Stapeln) und §8 (Modulgrenzen); aus der Architektur §2, §4.6, §10.1, §10.5. **Nicht gedeckt und bewusst so:** Architektur §5–§9 und §12 beschreiben spätere Teilprojekte, über die Stufe 1a nichts zu sagen hat; §10.2 (modularer Monolith), §10.3 (Blob-Speicher), §10.4 (Deployment) und §10.6/§10.7 (Werkzeuge, Abhängigkeiten) betreffen das Ganze und nicht diese Stufe — ihre Verweise im Code bleiben darum nach Aufgabe 7, Schritt 2 als gekennzeichnete Verweise auf den eingefrorenen Bericht stehen. §11 (was offen bleibt) gehört nicht in eine Doku für Benutzer.

**2. Platzhalter.** Kein „TBD", kein „analog zu Aufgabe N", keine Schritte ohne Inhalt. Die Doku-Seiten tragen Seitenspezifikationen nach Abschnitt 10c des Doku-Skills — das ist die vorgesehene Planungsform für Dokumentation, kein Platzhalter.

**3. Namenskonsistenz.** Die Label, die Aufgabe 7 abbildet, werden in den Aufgaben 2, 5 und 6 erzeugt: `hash-domain`, `canonicalization`, `hash-chain`, `tombstone-seam`, `timestamps`, `concurrency`, `conflict-classes`, `module-boundaries`, `backup-encryption`, `cli-reference`, `configuration-reference`, `database-schema`, `hash-format`. Aufgabe 7 läuft **nach** 2, 5 und 6 — sonst scheitert ihr Test zu Recht.

**4. Review Focus.** Alle fünf Punkte haben einen Test: 1 → Aufgabe 7, Schritt 3; 2 → Aufgabe 3, Schritt 3; 3 und 4 → Aufgabe 1, Schritt 8; 5 → Aufgabe 1, Schritte 3 und 12 (`linkcheck_ignore` plus der Lauf im Tor).

**Eine Warnung an den Ausführenden.** Die Explanation-Aufgaben sind die eigentliche Arbeit dieses Plans, und sie sind leicht zu unterschätzen: es sind über 2000 Zeilen dichte Begründung mit Messungen, Zahlen und Gegenargumenten. In dieser Sitzung ist dieselbe Gefahr schon einmal benannt und mit einem AST-Vergleich geprüft worden. Hier gibt es dafür keinen mechanischen Prüfstein — nur die Regel, und einen Prüfer, der stichprobenweise gegen das Original liest.
