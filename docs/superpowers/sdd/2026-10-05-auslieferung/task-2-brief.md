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

