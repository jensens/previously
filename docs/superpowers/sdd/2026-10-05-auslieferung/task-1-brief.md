## Task 1: Die Migrationen ziehen ins Paket

**Files:**
- Move: `migrations/` → `src/previously/migrations/` (mit `git mv`, damit die Geschichte folgt)
- Create: `src/previously/migrations/__init__.py`
- Modify: `src/previously/migrations/env.py` (Import), `alembic.ini`, `pyproject.toml`, `.importlinter`, `tests/test_migrations_dsn.py`, `tests/test_docs_references.py`, `CLAUDE.md` (zwei Erwähnungen von `migrations/`), `DEPENDENCIES.md`, `docs/how-to/add-a-migration.md`
- Create: `tests/test_wheel.py`

**Interfaces:**
- Produces: das Paket `previously.migrations`; `script_location = previously:migrations`; `previously.migrations.dsn.resolve_dsn` und `ENV_VAR` unverändert.

- [ ] **Step 1: Den Wheel-Test schreiben, der scheitert**

```python
# tests/test_wheel.py
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The built wheel carries what an installed Previously needs at run time.

An image installs Previously from PyPI, without a checkout beside it, so
whatever `previously migrate` reads has to be inside the wheel. Built in this
process with hatchling's own builder, the backend `pyproject.toml` names, so
that no subprocess and no suppression is needed for it.
"""

from hatchling.builders.wheel import WheelBuilder
from pathlib import Path

import zipfile


ROOT = Path(__file__).resolve().parent.parent
REVISIONS = sorted(path.name for path in (ROOT / "src/previously/migrations/versions").glob("*.py"))


def test_the_wheel_carries_every_migration(tmp_path: Path) -> None:
    builder = WheelBuilder(str(ROOT))
    (built,) = builder.build(directory=str(tmp_path), versions=["standard"])
    with zipfile.ZipFile(built) as wheel:
        names = set(wheel.namelist())
    assert "previously/migrations/env.py" in names
    assert "previously/migrations/script.py.mako" in names
    assert REVISIONS, "no revision found in the tree"
    for revision in REVISIONS:
        assert f"previously/migrations/versions/{revision}" in names
```

pyright strict: `WheelBuilder.build` ist typisiert (hatchling trägt `py.typed`). Meldet pyright den Rückgabetyp als unbekannt, gilt `cast`, nie `# type: ignore`.

- [ ] **Step 2: hatchling und hatch-vcs in die Dev-Abhängigkeiten**

In `pyproject.toml` unter `dev`: `"hatchling>=1.32"`, `"hatch-vcs>=0.5"`. Dann `uv lock` und `uv sync --all-extras`. In `DEPENDENCIES.md` beide Zeilen um die zweite Verwendung ergänzen: der Wheel-Test baut im Prozess (gemessen 2026-10-05; hatchling 1.32.4 vom 2026-09-20, `py.typed`).

- [ ] **Step 3: Den Test laufen lassen, er scheitert**

Run: `uv run pytest tests/test_wheel.py -v`
Expected: FAIL — `src/previously/migrations/versions` gibt es noch nicht, `REVISIONS` ist leer.

- [ ] **Step 4: Verschieben und anpassen**

```bash
git mv migrations src/previously/migrations
```
Dann:
- `src/previously/migrations/__init__.py` mit dem Lizenzkopf und einem Docstring: was das Paket ist, und dass Alembic es über `previously:migrations` findet.
- `src/previously/migrations/env.py`: `from migrations.dsn import resolve_dsn` → `from previously.migrations.dsn import resolve_dsn`.
- `alembic.ini`: `script_location = migrations` → `script_location = previously:migrations`.
- `pyproject.toml`: in `[tool.pyright] include` den Eintrag `"migrations"` streichen (er liegt jetzt unter `src`), und den Kommentar darüber so fassen, dass er stimmt. In `[tool.pytest.ini_options]` prüfen, ob `pythonpath = ["."]` noch gebraucht wird: der Kommentar nennt als einzigen Grund `migrations.dsn`. **Messen**, nicht annehmen: Zeile entfernen, volle Suite, und nur wenn grün entfernt lassen.
- `tests/test_migrations_dsn.py`: Importe auf `previously.migrations.dsn`; Docstring auf den neuen Pfad.
- `tests/test_docs_references.py`: `SOURCE_DIRS` und `OUTPUT_DIRS` ohne `"migrations"` (liegt jetzt unter `src`), die Kommentare dazu, die `migrations/` nennen, auf den neuen Pfad.
- `.importlinter`, Vertrag `layers`:
  ```ini
  layers =
      previously.cli
      previously.core | previously.migrations
      previously.storage
      previously.contract
  ```
  und den Namen des Vertrags so, dass er stimmt. Der Vertrag `core-is-clean` bleibt.
- `CLAUDE.md`: die zwei Stellen, die `migrations/` als eigenes Verzeichnis nennen (Abschnitt *Language*, und *Documentation*, die Liste der Verzeichnisse, die der Zitat-Test liest) — nur diese zwei Stellen, der Plan ist vom Betreuer freigegeben.
- `docs/how-to/add-a-migration.md`: die Pfade auf `src/previously/migrations/versions/`.
- `docs/explanation/design-records.md:91` ist eine datierte Messung über die Verzeichnisse von damals; sie bleibt, wie sie ist.

- [ ] **Step 5: Den Test laufen lassen, er besteht; die Mutation**

Run: `uv run pytest tests/test_wheel.py -v` → PASS.
Mutation: in `pyproject.toml` unter `[tool.hatch.build.targets.wheel]` `exclude = ["src/previously/migrations/versions/0004_event_blob.py"]` → der Test wird rot und nennt `0004_event_blob.py`; zurücknehmen. Kontrolle: ohne die Zeile grün.

- [ ] **Step 6: Alle sechs Tore**

Jedes für sich. `lint-imports` muss sechs Verträge halten; `test_docs_references` muss grün sein; `git grep -n "from migrations\|import migrations"` findet nichts.

- [ ] **Step 7: Commit**

```bash
git add src/previously/migrations alembic.ini pyproject.toml uv.lock .importlinter tests/test_wheel.py tests/test_migrations_dsn.py tests/test_docs_references.py CLAUDE.md DEPENDENCIES.md docs/how-to/add-a-migration.md
git commit -F <message-file>   # "build: the migrations move into the package"
```
(`git mv` hat die Löschung von `migrations/` schon vorgemerkt.)

---

