# Auslieferung — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Previously wird ein Paket auf PyPI und ein Image auf ghcr.io, aus dem kup6s Datenbank, Jobs und Werkzeug-Pod betreiben kann.

**Architecture:** Die Migrationen ziehen ins Paket, und ein Kommando `previously migrate` bringt eine Datenbank unter einer Advisory-Sperre auf den neuesten Stand. Ein Release-Workflow nach dem Muster von `fuellhorn` ruft die bestehenden Tore, veröffentlicht über Trusted Publishing und baut je Plattform ein Image, das Previously von PyPI installiert und vor dem Manifest einen Smoke-Test besteht. Ein englischer Handoff sagt dem Agenten in kup6s, was das Image braucht.

**Tech Stack:** Python 3.14, Alembic 1.20, SQLAlchemy 2.1, hatchling mit hatch-vcs, GitHub Actions, Docker Buildx, `ghcr.io/astral-sh/uv` als Basis.

**Spec:** `docs/superpowers/specs/2026-10-05-auslieferung.md` (Commit `e7bb56d`, vom Betreuer am 2026-10-05 durchgesehen: „spec passt").

---

## Was der Plan vorgibt und was nicht

Code steht hier nur, wo er gelaufen ist. Am 2026-10-05 lief im Scratchpad an
einer Kopie des Baums (Commit `e7bb56d`), Wegwerfcode, nicht übernommen:

- **Migrationen im Paket:** `migrations/` nach `src/previously/migrations/`
  verschoben, ein `__init__.py` dazu, in `env.py` der Import auf
  `previously.migrations.dsn`, `script_location = previously:migrations`. Das
  mit `uv build` gebaute Wheel enthält `README`, `__init__.py`, `dsn.py`,
  `env.py`, `script.py.mako` und die vier Revisionen — hatchling nimmt die
  Nicht-Python-Dateien des Paketverzeichnisses ohne weitere Einstellung mit.
- **`migrate` aus dem installierten Wheel**, in einem frischen venv, aus
  einem Verzeichnis ohne `alembic.ini`, gegen `postgres:17`: legt alle sieben
  Tabellen und `alembic_version` an und meldet
  `migrated: (empty) -> 0004_event_blob`; ein zweiter Aufruf meldet
  `up to date: 0004_event_blob`.
- **Zwei Läufe zugleich**, der erste hält die Sperre drei Sekunden: der zweite
  wartet und meldet `up to date`; beide nach vier Sekunden fertig.
- **Eine unbekannte Revision** (`alembic_version` von Hand auf
  `0005_future`): Alembic wirft `alembic.util.exc.CommandError: Can't locate
  revision identified by '0005_future'` — sowohl `ScriptDirectory.get_revision`
  als auch `command.upgrade`.
- **Das Image** aus dem Dockerfile in Aufgabe 3, gebaut mit einem lokalen
  Wheel über einen benannten Build-Kontext, 299 MB; ohne Argumente druckt es
  die Hilfe (mit `CMD ["--help"]`; ohne diese Zeile endete es mit
  `previously: error: the following arguments are required: command`).
- **Der Smoke-Test** aus Aufgabe 3 gegen dieses Image: grün. Zwei Befunde
  unterwegs, beide im Skript berücksichtigt:
  - `uv` im Image braucht ein beschreibbares Cache-Verzeichnis
    (`Failed to initialize cache at /app/.cache/uv: Permission denied`), also
    `UV_CACHE_DIR=/tmp/uv-cache`;
  - der Vergleich gegen `uv.lock` in beide Richtungen scheitert an `tzdata`,
    das der Lock nur unter Windows verlangt; geprüft wird darum nur, dass jede
    installierte Fassung im Lock steht, wie bei `fuellhorn`.
- **Ein Wheel-Bau im Prozess** mit `hatchling.builders.wheel.WheelBuilder`
  (hatchling 1.32.4, hatch-vcs 0.5.0): baut das Wheel und listet dieselben
  Dateien — ohne Unterprozess, also ohne neue Lint-Unterdrückung. hatchling
  trägt `py.typed`, hatch-vcs nicht (es wird nur geladen, nicht importiert).
  Ohne `.git` braucht der Bau eine vorgegebene Version; der Baum hat `.git`.
- **actionlint 1.7.8** im Container (`rhysd/actionlint:1.7.8`) über
  `gates.yml` und `audit.yml`: keine Meldung, Rückgabecode 0.

**Nicht gelaufen**, und darum hier nur als Vorlage mit Pflicht zur Messung:
`release.yml`. Er läuft erst auf `main` und bei einem Release; vorher misst ihn
actionlint, und `fuellhorn` ist der Beleg, dass derselbe Aufbau trägt.

## Was der Plan am Spec entscheidet

1. **Der Probelauf vor dem Merge (Spec §10 Punkt 7) geht nicht.** GitHub
   startet einen `workflow_dispatch` nur für eine Datei, die auf dem
   Standardzweig liegt; `release.yml` liegt dort erst nach dem Merge. Ersatz:
   actionlint vor dem Merge, und der erste Push auf `main` ist der Probelauf
   (Test-PyPI). Abnahmebedingung 8 bleibt, wie sie ist.
2. **Die Tore laufen auf `main` zweimal**: einmal aus `gates.yml` selbst
   (Auslöser `push`), einmal aufgerufen aus `release.yml`. Das kostet Minuten
   und sonst nichts; `gates.yml` auf andere Zweige zu beschränken hieße, dass
   ein Push auf `main` seine Tore nur noch über den Release-Workflow zeigt.
3. **`previously.migrations` steht in den Schichten neben `core`**:
   `previously.core | previously.migrations` als eine Schicht unter `cli` und
   über `storage`. Es importiert `storage.schema` (darunter), `core`
   importiert es nicht und es nicht `core` (unabhängig in derselben Schicht).
   `storage` ruft die Migrationen über den Namen `previously:migrations` auf,
   nicht über einen Import.
4. **Der Aufruf von Alembic steht in `storage/migrate.py`**, nicht in `cli`:
   `cli` kennt Alembic nicht, wie es SQLAlchemy nicht kennt (`_storage`).
5. **Der Wheel-Test baut im Prozess** mit hatchling (oben gemessen).
   hatchling und hatch-vcs kommen dafür in die Entwicklungs-Abhängigkeiten;
   beide stehen schon in `DEPENDENCIES.md` als Build-Werkzeug, der Eintrag
   bekommt die zweite Verwendung.
6. **Der lokale Bau des Images** geht über einen benannten Build-Kontext
   `wheels`: im Release leer (das Paket kommt von PyPI), lokal das Verzeichnis
   mit einem gebauten Wheel. Ein Dockerfile, zwei Wege, keine zweite Datei.
7. **`previously migrate` steht in `COMMANDS` als erstes Kommando**: die Hilfe
   listet es zuerst, weil es zuerst gebraucht wird.
8. **Das Smoke-Skript ist eine Datei im Repository** (`scripts/smoke-image.sh`),
   lokal und im Workflow dieselbe.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Workflow,
  Dockerfile, Skript und Handoff **englisch**; Spec, Plan, Landkarte deutsch.
- Die sechs Tore, jedes für sich, vor jeder Fertigmeldung:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `uv run pip-audit --skip-editable` ohne Befund zur Abnahme.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung (es bleiben fünf, `CLAUDE.md`).
- Kein Mock für Zeit, Datenbank, Speicher oder Zufall; Tests gegen echtes
  PostgreSQL über die Fixtures in `tests/conftest.py`.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener
  Zusicherung, mit einer grünen Kontrolle daneben. Mutationen im Baum, sofort
  zurückgenommen, danach `git status --short`.
- Ein Kommentar ist eine Behauptung; jede Zahl darin ist gemessen.
- Getippte Ausgabe ist eine Messung: neu tippen aus einem Lauf, nie eine Zahl
  in einem Block ändern. Das Tutorial zuletzt.
- Kein Geheimnis in Ausgabe, Seite, Bericht, Commit.
- Commits: Dateien namentlich stagen, nie `git add -A`; Botschaft per Datei,
  `git commit -F`; Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`,
  nie `Co-Authored-By`, nie „Generated with".
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | `migrate`, stdout | `migrated: <from> -> <head>`, mit `(empty)` als `<from>` bei einer leeren Datenbank |
  | `migrate`, stdout | `up to date: <head>` |
  | `migrate`, stderr, Code 2 | `Error: the database is at revision <rev>, which this version of previously does not know; it knows revisions up to <head>` |
  | Hilfe | `migrate` — `bring the database schema up to the newest revision` |
  | Image-Tags | `<version>`, `<major>.<minor>`; `latest` nur für ein stabiles Release |

- Erlaubte Tags: `vX.Y.Z`, `vX.Y.ZaN`, `vX.Y.ZbN`, `vX.Y.ZrcN`
  (regulärer Ausdruck `^v[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$`).
- Aktionen in Workflows auf einen Commit gepinnt, die Fassung als Kommentar
  daneben, wie in `gates.yml`.
- Die Basis des Images per Digest gepinnt:
  `ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:8e88a074b0969bdc461f681727238e109438d70771828909f9ef19cfcc96c43a`
  (aufgelöst am 2026-10-05).

## Review Focus

1. **Eine Datenbank, die weiter ist als das Image.** Ein älteres Image gegen
   eine schon migrierte Datenbank: `migrate` meldet es mit einem Satz und
   Code 2 und ändert nichts; jedes andere Kommando läuft wie bisher.
   → Aufgabe 2, Test `test_migrate_refuses_a_revision_it_does_not_know`.
2. **Zwei Migrations-Jobs zugleich.** Der zweite wartet und meldet
   „up to date". → Aufgabe 2, Test mit gehaltener Sperre.
3. **Ein falsches Passwort oder ein nicht erreichbarer Server** bei `migrate`:
   ein Satz, Code 2, kein Passwort in der Ausgabe, kein Traceback.
   → Aufgabe 2.
4. **Ein Wheel ohne Migrationen.** Ein vergessener Eintrag fiele sonst erst
   nach dem Upload auf. → Aufgabe 1, Wheel-Test.
5. **Ein Tag in falscher Form** (`v0.1.0-alpha1`, `v0.1`): der Workflow bricht
   vor jedem Upload ab. → Aufgabe 4, gemessen mit dem regulären Ausdruck an
   sechs Tags.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/migrations/` (aus `migrations/`) | 1 | die Revisionen, `env.py`, `dsn.py`, Vorlage |
| `alembic.ini` | 1 | `script_location = previously:migrations` |
| `pyproject.toml` | 1 | pyright `include`, pytest `pythonpath`, Dev-Abhängigkeiten |
| `.importlinter` | 1 | `previously.migrations` in den Schichten |
| `tests/test_migrations_dsn.py`, `tests/test_docs_references.py` | 1 | neuer Ort |
| `tests/test_wheel.py` | 1 | das Wheel enthält die Migrationen |
| `src/previously/storage/migrate.py` | 2 | Sperre, Revisionen prüfen, Alembic rufen |
| `src/previously/storage/errors.py` | 2 | `UnknownRevision` |
| `src/previously/cli.py` | 2 | `migrate` |
| `tests/test_migrate.py` | 2 | die Zusicherungen von `migrate` |
| `Dockerfile`, `.dockerignore` | 3 | das Image |
| `scripts/smoke-image.sh` | 3 | der Smoke-Test |
| `.github/workflows/gates.yml` | 4 | `workflow_call` |
| `.github/workflows/release.yml` | 4 | der Release-Weg |
| `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md` | 5 | der Handoff, englisch |
| Doku-Seiten, README, Landkarte, Spec | 2, 5 | siehe dort |

---

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

## Task 2: `previously migrate`

**Files:**
- Create: `src/previously/storage/migrate.py`, `tests/test_migrate.py`
- Modify: `src/previously/storage/errors.py`, `src/previously/cli.py`, `pyproject.toml` (Kommentar der `T201`-Ausnahme, wenn die Zahl der `print` sich ändert), `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/how-to/add-a-migration.md`, `docs/how-to/restore-from-a-backup.md` (falls es das Anlegen nennt — `grep`), `README.md` (falls es `alembic` nennt — `grep`)

**Interfaces:**
- Consumes: `previously:migrations` (Aufgabe 1).
- Produces:
  ```python
  # storage/migrate.py
  @dataclass(frozen=True)
  class Migrated:
      before: str | None   # None: the database had no revision
      head: str
  def migrate(dsn: str) -> Migrated: ...
  # storage/errors.py
  class UnknownRevision(StorageError): ...
  ```

- [ ] **Step 1: Die Tests schreiben, die scheitern**

`tests/test_migrate.py` gegen eine **eigene** leere Datenbank: die Session-Datenbank aus `conftest.py` ist schon migriert. Der Container aus der Fixture, die `conftest.py` für den Fall ohne `alembic upgrade head` schon hat (sie heißt dort nach Befund W2; mit `grep -n "without" tests/conftest.py` finden), oder `CREATE DATABASE` auf dem Session-Container und danach `DROP DATABASE`. Fünf Tests:

```python
def test_migrate_creates_the_schema_and_then_finds_it_up_to_date(empty_dsn: str) -> None:
    first = migrate(empty_dsn)
    assert first.before is None
    assert first.head == HEAD
    second = migrate(empty_dsn)
    assert second == Migrated(before=HEAD, head=HEAD)

def test_migrate_waits_for_a_migration_that_holds_the_lock(empty_dsn: str) -> None:
    # The test takes the lock itself, starts `migrate` in a thread, sees it
    # wait in `pg_stat_activity`, releases, and sees it finish.
    ...

def test_migrate_refuses_a_revision_it_does_not_know(empty_dsn: str) -> None:
    migrate(empty_dsn)
    # raw SQL, as the forgery tests do
    with create_engine(empty_dsn).begin() as conn:
        conn.execute(text("UPDATE alembic_version SET version_num = '9999_future'"))
    with pytest.raises(UnknownRevision, match="9999_future"):
        migrate(empty_dsn)

def test_cli_migrate_prints_one_line_each_way(...) -> None: ...   # `migrated: (empty) -> <head>`, dann `up to date: <head>`

def test_cli_migrate_names_no_password_and_gives_one_sentence(...) -> None:
    # falsches Passwort: Code 2, eine Zeile auf stderr, das Passwort nirgends
```

`HEAD` kommt aus dem Baum, nicht getippt: die höchste Revision in `src/previously/migrations/versions/`, über `ScriptDirectory` gelesen. Der Wartetest liest die Sperre nicht über einen privaten Namen: der Schlüssel ist eine öffentliche Konstante `MIGRATION_LOCK` in `storage/migrate.py`. Er wartet höchstens zehn Sekunden auf `wait_event_type = 'Lock'` des anderen Backends in `pg_stat_activity`, ohne `sleep`, das auf einen Zeitpunkt hofft: es fragt in einer Schleife mit Frist.

- [ ] **Step 2: Die Tests laufen lassen, sie scheitern** (`ImportError` für `previously.storage.migrate`).

- [ ] **Step 3: `storage/migrate.py`**

Gelaufen im Spike (oben), hier in die Form des Baums gebracht:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bringing a database to the newest revision of the schema ({ref}`delivery`).

The migrations live in the package, `previously:migrations`, so this works
from an installed wheel without a checkout and without `alembic.ini`.
"""

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from dataclasses import dataclass
from previously.storage.errors import UnknownRevision
from sqlalchemy import text

# ... from_dsn-style engine creation with the translation of errors the CLI
# already relies on (InvalidDsn, ServerUnreachable) — reuse what
# `storage/postgres.py` has instead of a second translation.

MIGRATION_LOCK = 0x70726576  # "prev"; any other advisory lock in the database uses another key


@dataclass(frozen=True)
class Migrated:
    before: str | None
    head: str


def migrate(dsn: str) -> Migrated:
    config = Config()
    config.set_main_option("script_location", "previously:migrations")
    config.set_main_option("sqlalchemy.url", dsn)
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    # ... engine; under `pg_advisory_lock(MIGRATION_LOCK)` on one connection:
    #     before = MigrationContext.configure(conn).get_current_revision()
    #     if before is not None: script.get_revision(before), a CommandError
    #       becomes UnknownRevision(f"the database is at revision {before}, which
    #       this version of previously does not know; it knows revisions up to {head}")
    #     if before != head: command.upgrade(config, "head")
    #     finally: pg_advisory_unlock, commit
    return Migrated(before=before, head=head)
```

Die ausgelassenen Stellen sind keine Platzhalter für Entscheidungen, sondern für die Anpassung an `storage/postgres.py`: wie dort eine Engine aus dem DSN entsteht und Fehler übersetzt werden (`from_dsn`, `_transaction`), so hier — **nachlesen und wiederverwenden**, nicht neu schreiben. `get_current_head()` ist bei mehreren Köpfen `None`; der Baum hat einen, ein Test hält es (Kopf ist nicht `None`). Die Sperre sitzt auf einer eigenen Verbindung, `command.upgrade` öffnet über `env.py` eine zweite; gemessen im Spike, dass das trägt (die Sitzungssperre gilt für die Sitzung, die sie hält, und reiht jeden zweiten Aufruf ein).

- [ ] **Step 4: Das Kommando**

In `cli.py`: `_cmd_migrate` liest `PREVIOUSLY_DSN` wie `_storage` (dieselbe Meldung, wenn es fehlt), ruft `storage.migrate.migrate`, druckt `migrated: <before or "(empty)"> -> <head>` oder `up to date: <head>`, gibt 0 zurück. `UnknownRevision` ist ein `StorageError` und läuft durch den bestehenden Zweig in `main` (ein Satz, Code 2). In `COMMANDS` **als erstes**: `Command("migrate", "bring the database schema up to the newest revision", _cmd_migrate)`. Zählt sich die Zahl der `print` in `cli.py` neu, den Kommentar an der `T201`-Ausnahme in `pyproject.toml` neu messen (Kommando steht dort) und fortschreiben.

- [ ] **Step 5: Tests grün, Mutationen**

| Mutation | rot | Kontrolle grün |
|---|---|---|
| `pg_advisory_lock` entfernt | der Wartetest (migrate läuft durch, während der Test die Sperre hält) | die anderen vier |
| die Prüfung von `before` entfernt | `test_migrate_refuses_a_revision_it_does_not_know` (dann wirft `command.upgrade` einen `CommandError` als Traceback statt `UnknownRevision`) | die anderen vier |
| `if before != head` entfernt (immer `upgrade`) | keiner — melden; das zweite `migrate` ist dann eine Alembic-Leerfahrt. Der Test hält die Ausgabe `up to date`, nicht den Aufruf | — |

Die dritte Zeile ist eine Erwartung, keine Zusicherung: wenn sie sich anders misst, steht das im Bericht.

- [ ] **Step 6: Die Seiten**

- `cli.md`: ein Abschnitt `migrate` an erster Stelle, mit den drei Wortlauten aus den Global Constraints, Rückgabecodes, der Sperre, „nur vorwärts"; die Zahl der Kommandos (`git grep -n "ten commands\|10 commands"` über `README.md` und `docs/`, ohne `docs/superpowers`) auf elf. `tests/test_docs_references.py` hält die zitierten Meldungen gegen den Code — der neue Satz muss dort durchgehen.
- `configuration.md`: `PREVIOUSLY_DSN` liest auch `migrate`; der Satz zu `sqlalchemy.url` in `alembic.ini` gilt nur für `alembic` in der Entwicklung, `migrate` liest nur die Umgebung.
- `add-a-migration.md`: anwenden mit `previously migrate`; `alembic revision` bleibt.
- Jede andere Stelle, die `alembic upgrade head` als Weg für Betreiber nennt (`git grep -n "alembic upgrade"` über `README.md` und `docs/`, ohne `docs/superpowers`), sagt `previously migrate` — **außer dem Tutorial**, das Aufgabe 5 neu tippt.

- [ ] **Step 7: Sechs Tore, Commit**

```bash
git add src/previously/storage/migrate.py src/previously/storage/errors.py src/previously/cli.py tests/test_migrate.py pyproject.toml docs/reference/cli.md docs/reference/configuration.md docs/how-to/add-a-migration.md
git commit -F <message-file>   # "feat: previously migrate brings the schema up, one run at a time"
```

---

## Task 3: Das Image und sein Smoke-Test

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `scripts/smoke-image.sh`

**Interfaces:**
- Consumes: `previously migrate` (Aufgabe 2).
- Produces: `docker build --build-context wheels=<dir> --build-arg PREVIOUSLY_VERSION=<v> -t <tag> .`; `scripts/smoke-image.sh <image>` mit Rückgabecode 0 bei Erfolg; Aufgabe 4 ruft beides.

- [ ] **Step 1: `Dockerfile`** — gelaufen im Spike, so übernehmen:

```dockerfile
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# The dependencies exactly as `uv.lock` has them, then Previously itself in the
# version of the release, from PyPI, without resolving anything again. The
# image thus holds the package that is on PyPI and the versions the gates ran
# against ({ref}`delivery`).
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:8e88a074b0969bdc461f681727238e109438d70771828909f9ef19cfcc96c43a

ARG PREVIOUSLY_VERSION

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# `wheels` is a named build context: an empty directory in the release
# workflow, where the package comes from PyPI; a directory holding a locally
# built wheel otherwise. One file, two ways in.
RUN --mount=type=bind,from=wheels,target=/wheels \
    uv pip install --python /app/.venv/bin/python --no-deps --find-links /wheels \
    "previously==${PREVIOUSLY_VERSION}"

RUN groupadd --system --gid 1000 previously \
    && useradd --system --uid 1000 --gid 1000 --home-dir /app --no-create-home --shell /usr/sbin/nologin previously
USER previously

LABEL org.opencontainers.image.source="https://github.com/jensens/previously" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.version="${PREVIOUSLY_VERSION}"

ENTRYPOINT ["previously"]
CMD ["--help"]
```

Ein `{ref}` in einem Dockerfile hält kein Test (`test_docs_references` liest nur `*.py`); die Marke `delivery` entsteht in Aufgabe 5. Steht sie dann nicht, ist die Zeile falsch — Aufgabe 5 prüft es.

- [ ] **Step 2: `.dockerignore`** — alles außer `pyproject.toml` und `uv.lock`; das Image kopiert nichts anderes aus dem Kontext:

```
*
!pyproject.toml
!uv.lock
```

- [ ] **Step 3: `scripts/smoke-image.sh`** — gelaufen im Spike, grün; der Text ist die Datei `smoke-image.sh` aus dem Scratchpad dieser Sitzung, hier vollständig:

```bash
#!/usr/bin/env bash
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Smoke test of one image: run from the repository root as
# `scripts/smoke-image.sh IMAGE`. Starts PostgreSQL 17 and RustFS 1.0.1 on a
# network of its own, runs the image against them, and removes everything it
# started, also when a step fails.
set -euo pipefail

IMAGE="$1"
NET="previously-smoke-$$"
PG="$NET-pg"
S3="$NET-s3"
WORK="$(mktemp -d)"
chmod 0777 "$WORK"

cleanup() {
  docker rm -f -v "$PG" "$S3" > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

SECRET="$(openssl rand -hex 16)"
docker network create "$NET" > /dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=previously -e POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously \
  postgres:17 > /dev/null
docker run -d --name "$S3" --network "$NET" \
  -e RUSTFS_ACCESS_KEY=smoke -e RUSTFS_SECRET_KEY="$SECRET" \
  rustfs/rustfs:1.0.1 > /dev/null
for _ in $(seq 1 60); do
  docker exec "$PG" pg_isready -U previously -d previously > /dev/null 2>&1 && break
  sleep 1
done

run() {
  docker run --rm --network "$NET" -v "$WORK:/work" -w /work \
    -e PREVIOUSLY_DSN="postgresql+psycopg://previously:previously@$PG:5432/previously" \
    -e PREVIOUSLY_BLOB_ENDPOINT="http://$S3:9000" \
    -e PREVIOUSLY_BLOB_REGION=us-east-1 \
    -e PREVIOUSLY_BLOB_BUCKET=smoke \
    -e PREVIOUSLY_BLOB_ACCESS_KEY=smoke \
    -e PREVIOUSLY_BLOB_SECRET_KEY="$SECRET" \
    -e PREVIOUSLY_BLOB_RECIPIENT="${RECIPIENT:-}" \
    -e PREVIOUSLY_BLOB_IDENTITIES=/work/identities \
    "$@"
}

echo "::group::the image runs as user 1000"
test "$(run --entrypoint id "$IMAGE" -u)" = 1000
echo "::endgroup::"

echo "::group::installed versions match uv.lock"
uv export --frozen --no-dev --no-emit-project --no-hashes \
  | grep -E '^[A-Za-z0-9_.-]+==' | sed 's/ .*//' | tr 'A-Z_' 'a-z-' | sort > "$WORK/expected.txt"
run -e UV_CACHE_DIR=/tmp/uv-cache --entrypoint uv "$IMAGE" pip freeze --python /app/.venv/bin/python \
  | grep -E '^[A-Za-z0-9_.-]+==' | grep -vi '^previously==' | tr 'A-Z_' 'a-z-' | sort > "$WORK/actual.txt"
# One direction only: every version installed must stand in the lock. The
# reverse would fail on packages the lock needs only on another platform
# (measured: `tzdata`, for Windows); a missing package shows in the steps below.
if comm -23 "$WORK/actual.txt" "$WORK/expected.txt" | grep .; then
  echo "::error::installed versions differ from uv.lock (lines above)"
  exit 1
fi
echo "::endgroup::"

echo "::group::the bucket and a key made at run time"
for _ in $(seq 1 30); do
  run --entrypoint python "$IMAGE" -c "
import boto3, os
s3 = boto3.client('s3', endpoint_url=os.environ['PREVIOUSLY_BLOB_ENDPOINT'], region_name='us-east-1',
    aws_access_key_id='smoke', aws_secret_access_key=os.environ['PREVIOUSLY_BLOB_SECRET_KEY'])
s3.create_bucket(Bucket='smoke')
" > /dev/null 2>&1 && break
  sleep 1
done
RECIPIENT="$(run --entrypoint python "$IMAGE" -c "
import os, pyrage
identity = pyrage.x25519.Identity.generate()
recipient = str(identity.to_public())
os.makedirs('/work/identities', exist_ok=True)
path = '/work/identities/' + recipient
with open(path, 'w') as f:
    f.write(str(identity) + '\n')
os.chmod(path, 0o600)
print(recipient)
")"
export RECIPIENT
echo "::endgroup::"

echo "::group::migrate, twice"
run "$IMAGE" migrate
run "$IMAGE" migrate | grep -q '^up to date: '
echo "::endgroup::"

echo "::group::a blob in and out"
printf 'Smoke test of the image.\n' > "$WORK/attachment.txt"
run "$IMAGE" append --source smoke --external-id one --text "A smoke test." --attach attachment.txt
ADDRESS="$(sha256sum "$WORK/attachment.txt" | cut -d' ' -f1)"
run "$IMAGE" blob get "$ADDRESS" --output fetched.txt
cmp "$WORK/attachment.txt" "$WORK/fetched.txt"
run "$IMAGE" verify --blobs
run "$IMAGE" anchor
echo "::endgroup::"

echo "smoke test passed: $IMAGE"
```

Die Identität entsteht zur Laufzeit in einem temporären Verzeichnis, das das Skript am Ende löscht, und öffnet nichts außerhalb dieses Laufs.

- [ ] **Step 4: Lokal bauen und den Smoke-Test laufen lassen**

```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0 uv build --wheel -o /tmp/<scratch>/wheels
docker build --build-context wheels=/tmp/<scratch>/wheels --build-arg PREVIOUSLY_VERSION=0.0.0.dev0 -t previously:local .
bash scripts/smoke-image.sh previously:local
```
Expected: `smoke test passed: previously:local`. Danach `docker rmi previously:local`.

- [ ] **Step 5: Die Mutationen des Smoke-Tests** — jede rot, jede sofort zurück:
  - `USER previously` im Dockerfile entfernt → „runs as user 1000" scheitert.
  - im Dockerfile `--frozen` → `--upgrade` bei `uv sync` (löst frei auf) → der Lock-Vergleich scheitert, **wenn** eine neuere Fassung existiert; sonst melden, dass die Mutation an diesem Tag nichts misst.
  - `cmp` gegen eine andere Datei → scheitert.
  Kontrolle: unverändert grün.

- [ ] **Step 6: shellcheck** im Container (`koalaman/shellcheck:v0.11.0` oder die zum Zeitpunkt neueste Fassung, gepinnt) über `scripts/smoke-image.sh`: keine Meldung, oder jede Meldung im Bericht begründet.

- [ ] **Step 7: Sechs Tore, Commit**

```bash
git add Dockerfile .dockerignore scripts/smoke-image.sh
git commit -F <message-file>   # "build: an image of the released package, and its smoke test"
```

---

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

## Task 5: Handoff, Dokumentation, Landkarte, Einfrieren

**Files:**
- Create: `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md`, `docs/how-to/cut-a-release.md`, `docs/how-to/run-the-image.md`, `docs/explanation/delivery.md`
- Modify: `docs/how-to/index.md`, `docs/explanation/index.md`, `docs/index.md`, `README.md`, `docs/tutorials/record-your-first-event.md`, `docs/explanation/design-records.md`, `docs/superpowers/landkarte.md`, `docs/superpowers/specs/2026-10-05-auslieferung.md` (Einfrieren)

- [ ] **Step 1: Der Handoff, englisch**, nach Spec §6, Punkt für Punkt; dazu, was der Spec §3.4 vom Betreuer verlangt, als Voraussetzung („before the first image exists"). Er sagt was, warum, woran man es erkennt — nie, wie in cdk8s. Jede Umgebungsvariable mit dem Kommando, das sie liest, aus `docs/reference/configuration.md` übernommen, nicht aus dem Gedächtnis. Kein Geheimnis, kein Platzhalter, der wie eines aussieht.

- [ ] **Step 2: Die Seiten**, nach `plone-doc-style:author` (die Fähigkeit unter genau diesem Namen aufrufen):
  - `cut-a-release.md` (How-to): Spec §3.1, §3.3, §3.4, der Befehl `gh release create v0.1.0a1 --prerelease --generate-notes --target main`, was zu beobachten ist, was zu tun ist, wenn ein Schritt scheitert — welcher Schritt hat was schon veröffentlicht (Spec §5: ein gescheiterter Smoke-Test lässt die Version auf PyPI) —, Release-Notes für Betreiber (neue Migrationen: `previously migrate` vor allem anderen).
  - `run-the-image.md` (How-to): die Angaben, `migrate` zuerst, ein `docker run` je Kommando, der lokale Bau aus einem Wheel (Aufgabe 3, Step 4); für den Cluster der Verweis, dass der Betrieb ihn baut.
  - `delivery.md` (Explanation, Marke `(delivery)=`): warum das Image aus PyPI installiert, warum der Vergleich gegen `uv.lock` nur in eine Richtung geht (`tzdata`), warum kein `latest` für Alphas, warum die Migrationen im Paket liegen, warum `migrate` eine Sperre nimmt, warum die Tag-Prüfung vor dem Upload steht. Prüfen, dass die zwei `{ref}`delivery`` aus Aufgabe 2 und 3 jetzt auflösen (`test_docs_references` für `storage/migrate.py`; das Dockerfile von Hand).
  - Indexseiten und `docs/index.md`: die neuen Seiten.
  - README: Installation aus PyPI (`pip install previously` mit dem Hinweis auf Alphas, `--pre`), das Image, `previously migrate`; die Zahl der Kommandos.
  - `design-records.md`: die siebte Zeile der eingefrorenen Berichte, beim Einfrieren (Step 4).

- [ ] **Step 3: Die Landkarte**: die neue Einheit „Auslieferung" in *Wo das Projekt steht* (gebaut, zur Abnahme: der Merge dieses Zweigs — so gefasst, dass es vor und nach dem Merge stimmt), die Tabelle des Piloten (Einheit 2 beginnt beim Image; der Handoff liegt), die offenen Punkte aus Spec §12 je unter ihre Einheit. Zählen vorher und nachher mit dem Kommando aus `CLAUDE.md`.

- [ ] **Step 4: Den Spec einfrieren**: Kopf wie die anderen eingefrorenen Specs (wörtlich aus `docs/superpowers/specs/2026-10-04-stufe-1c-blobs-und-tilgung.md` übernehmen, Datum 2026-10-05), Statuszeile, die Einleitung von §12 in der Vergangenheit. Sonst nichts am Spec. Dazu: der Spec sagt in §10 Punkt 7, der Workflow laufe vor dem Merge einmal von Hand; das geht nicht (Entscheidung 1 dieses Plans) — der eingefrorene Spec bleibt, die Seite `cut-a-release.md` sagt, wie es ist.

- [ ] **Step 5: Das Tutorial, zuletzt**: aus einem frischen Lauf neu tippen, mit `uv run previously migrate` statt `uv run alembic upgrade head`; den Testblock als Letztes, aus einem grünen Lauf.

- [ ] **Step 6: Sechs Tore, `pip-audit`, Commits** — die Seiten, die Landkarte und das Einfrieren in eigenen Commits, das Tutorial zuletzt.

---

## Nach Aufgabe 5

Sache des Controllers:

1. Endprüfung des ganzen Zweigs (Code und Konfiguration; englische Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-05-auslieferung/`.
4. Push und Pull-Request, nach Rückfrage. Der Merge ist die Abnahme.
5. Danach der Betreuer: Trusted Publishing einrichten, der erste Lauf auf `main`, das Release `v0.1.0a1` (Spec §11, Bedingung 8).

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §2.1 → Aufgabe 1; §2.2 → Aufgabe 2; §3 → Aufgabe 4 (§3.4 als Anleitung in Aufgabe 5); §4 → Aufgabe 3; §5 → Aufgabe 3 (Skript) und 4 (Aufruf); §6 → Aufgabe 5; §7 → Handoff und `delivery.md`; §9 → Aufgaben 2 und 5; §10 Punkte 1–6 → Aufgaben 1–2, Punkt 7 → Entscheidung 1; §11 → die Aufgaben und „Nach Aufgabe 5"; §12 → Landkarte.
- **Platzhalter:** `<sha>` in `release.yml` und `<message-file>` sind Werte, die der Umsetzer misst oder schreibt, mit der Anweisung, wie. Die Auslassungen in `storage/migrate.py` sind die Anpassung an bestehenden Code mit Verweis, was wiederzuverwenden ist; der Kern ist gelaufen.
- **Namen:** `migrate`, `Migrated`, `MIGRATION_LOCK`, `UnknownRevision`, `previously:migrations`, `wheels`, `PREVIOUSLY_VERSION`, `scripts/smoke-image.sh` — überall gleich.
- **Zahlen:** 299 MB, vier Revisionen, sieben Tabellen, sechs Verträge, fünf Unterdrückungen, elf Kommandos — gemessen am 2026-10-05 oder aus dem Baum gezählt; die Zahl der `print` in `cli.py` misst Aufgabe 2 neu.
