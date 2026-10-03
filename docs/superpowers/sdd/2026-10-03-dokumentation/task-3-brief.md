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

