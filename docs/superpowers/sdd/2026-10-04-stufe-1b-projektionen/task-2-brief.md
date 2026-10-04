## Task 2: Schema und Migration — `projection_state`, `p_chronicle`, `p_source_stats`

**Files:**
- Modify: `src/previously/storage/schema.py`, `tests/conftest.py:34-42`, `docs/reference/database-schema.md`, `docs/explanation/index.md`
- Create: `migrations/versions/0002_projections.py`, `docs/explanation/projections.md`
- Test: `tests/test_schema.py` (bestehende Tests decken neue Tabellen automatisch, ein neuer kommt dazu)

**Interfaces:**
- Produces: `previously.storage.schema.{projection_state, p_chronicle, p_source_stats}` als `Table`-Objekte; Index `p_chronicle_occurred_idx`. Tabellen- und Spaltennamen genau wie Spec §3.

- [ ] **Schritt 1: Den Test schreiben, der die Tabellen verlangt**

In `tests/test_schema.py` anfügen:

```python
@pytest.mark.db
def test_the_projection_tables_exist(db: Engine) -> None:
    """Stage 1b adds three tables ({ref}`projections`); the migration has to
    create all three, the metadata has to declare all three, and the two
    have to agree — `test_the_declared_indexes_exist` above covers the index
    the same way."""
    with db.connect() as c:
        names = set(
            c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            .scalars()
            .all()
        )
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= names
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= set(metadata.tables)
```

- [ ] **Schritt 2: Laufen lassen — rot**

Run: `uv run pytest tests/test_schema.py::test_the_projection_tables_exist -v`
Erwartet: `FAILED`, die drei Namen fehlen in `names`.

- [ ] **Schritt 3: Die Tabellen deklarieren**

Ans Ende von `src/previously/storage/schema.py`:

```python
# --- Projections ({ref}`projections`) ---------------------------------------
#
# Derivable and disposable (architecture §4.4, frozen design record): these
# tables carry no truth of their own, so they carry no foreign keys onto one
# another — only onto `event`, because a projection of an event that does not
# exist must never be built. Prefix `p_`.

projection_state = Table(
    "projection_state",
    metadata,
    Column("name", Text, primary_key=True),
    # 0 = nothing built yet. Unambiguous because events number from 1.
    Column("up_to_id", BigInteger, nullable=False),
    # The rebuild trigger: the worker compares it with the version the code
    # declares, and any difference — not only a lower one — empties the table
    # and starts over.
    Column("version", Integer, nullable=False),
    Column("built_at", TIMESTAMP(timezone=True), nullable=False),
)

p_chronicle = Table(
    "p_chronicle",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("kind", Text, nullable=False),
    # NULL when the payload was erased: the kind of evidence lives in the
    # payload, and a tombstone has none. NOT NULL here would mean the chronicle
    # cannot show an erased event at all — a row in the log, silently missing.
    Column("evidence", Text),
    # NULL when the event carries no source attribution; `source_key` enforces
    # at most one per event, not at least one.
    Column("source", Text),
    Column("external_id", Text),
    Column("speaker", Text),
    Column("start_ms", Integer),
    Column("end_ms", Integer),
    PrimaryKeyConstraint("event_id", "seq"),
)

# The primary key carries chain order; this index carries time order
# (architecture §4.1 wants both). `chronicle` reads in index direction, and the
# triple is unique, so the output is deterministic.
Index("p_chronicle_occurred_idx", p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq)

p_source_stats = Table(
    "p_source_stats",
    metadata,
    Column("source", Text, primary_key=True),
    Column("events", BigInteger, nullable=False),
    Column("units", BigInteger, nullable=False),
    Column("first_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_event_id", BigInteger, ForeignKey("event.id"), nullable=False),
)
```

- [ ] **Schritt 4: Die Migration**

`migrations/versions/0002_projections.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Projections: state, chronicle, source statistics

Revision ID: 0002_projections
Revises: 0001_log

A forward migration, unlike the corrections folded into `0001_log`: nothing
here touches the log, so there is nothing a rebuild would have to redo. The
three tables are derivable and disposable ({ref}`projections`); dropping them
loses no truth, and `previously project` builds them again from the log.
"""

from alembic import op

import sqlalchemy as sa


revision = "0002_projections"
down_revision = "0001_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_state",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("up_to_id", sa.BigInteger, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        "p_chronicle",
        sa.Column("event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text),
        sa.Column("source", sa.Text),
        sa.Column("external_id", sa.Text),
        sa.Column("speaker", sa.Text),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.PrimaryKeyConstraint("event_id", "seq"),
    )
    op.create_index("p_chronicle_occurred_idx", "p_chronicle", ["occurred_at", "event_id", "seq"])
    op.create_table(
        "p_source_stats",
        sa.Column("source", sa.Text, primary_key=True),
        sa.Column("events", sa.BigInteger, nullable=False),
        sa.Column("units", sa.BigInteger, nullable=False),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_event_id", sa.BigInteger, sa.ForeignKey("event.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("p_source_stats")
    op.drop_index("p_chronicle_occurred_idx", table_name="p_chronicle")
    op.drop_table("p_chronicle")
    op.drop_table("projection_state")
```

- [ ] **Schritt 5: Das `db`-Fixture leert auch die neuen Tabellen**

`tests/conftest.py`, die `TRUNCATE`-Zeile in `db`:

```python
    with engine.begin() as c:
        c.execute(text("TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event"))
```

Docstring des Fixtures: „All three tables" → „All six tables". Ohne diese Zeile leckt der Zustand einer Projektion in den nächsten Test, und der Fehler sieht aus wie ein falsches Nachziehen.

- [ ] **Schritt 6: Laufen lassen — grün, und die bestehenden Schema-Tests mit**

Run: `uv run pytest tests/test_schema.py -v`
Erwartet: alle `PASSED`, darunter `test_the_declared_indexes_exist` (der neue Index ist in `metadata` **und** in der Datenbank) und `test_the_declared_nulls_not_distinct_reaches_the_database` (die neuen Indizes haben das Flag nicht, auf beiden Seiten).

- [ ] **Schritt 7: `database-schema.md` um drei Abschnitte**

Nach dem Muster der drei bestehenden (`## event` … `### Constraints and indexes`): je Tabelle eine Spaltentabelle mit Name, Typ, Nullbarkeit, Bedeutung — **abgelesen aus einer migrierten Datenbank**, nicht aus `schema.py`. Die Abschlussprüfung der Doku hat genau so gemessen (gegen `information_schema.columns` und `pg_indexes` in einem Container). Dazu je `### Constraints and indexes` mit den von PostgreSQL erzeugten Namen (`projection_state_pkey`, `p_chronicle_pkey`, `p_chronicle_event_id_fkey`, `p_chronicle_occurred_idx`, `p_source_stats_pkey`, `p_source_stats_last_event_id_fkey`) — **nachgeschlagen**, nicht geraten.

Reference-Ton: Tatsachen, keine Begründung. Für das Warum ein Satz: „{ref}`projections` explains why these tables carry no foreign keys onto one another."

- [ ] **Schritt 8: `projections.md` anlegen — mit dem, was jetzt schon stimmt**

`docs/explanation/projections.md`, Label `(projections)=`, Titel `# About derived views`. Diese Aufgabe schreibt die **ersten zwei Abschnitte**; Aufgaben 5, 6 und 7 fügen ihre an. Explanation-Ton, ein Satz pro Zeile.

Abschnitt 1, `## Derivable and disposable`: §4.4 der Architektur verspricht, dass Projektionen keine eigene Wahrheit tragen; was das praktisch heißt (wegwerfen und beim Neubau dasselbe bekommen); warum deshalb kein Fremdschlüssel zwischen Projektionen, wohl aber auf `event`.

Abschnitt 2, `## What the two tables are for`: `p_chronicle` ist eine Zeile je **Einheit** über vier Tabellen — der Unterschied zu `log`; warum `evidence` nullable ist (die Belegart steht in der Nutzlast, ein Grabstein hat keine — ein `NOT NULL` ließe eine Zeile des Logs still verschwinden); warum `source` nullable ist. `p_source_stats` als Aggregation, mit dem Satz aus Spec §3.3: inkrementell nachziehbar **nur, weil das Log append-only ist** — könnte eine Zeile verschwinden, bräuchte ein Minimum einen Neubau. Und der Vorgriff, dass genau das die Projektion zum Prüfstein macht (Aufgabe 5 schreibt den Abschnitt dazu).

In `docs/explanation/index.md` den Toctree um `projections` ergänzen (nach `module-boundaries`).

Run: `make -C docs html && make -C docs vale && make -C docs linkcheck`
Erwartet: grün, Vale **21 files**.

- [ ] **Schritt 9: Alle sechs Tore, Commit**

Run: der Block. Erwartet: grün, `pytest` **194 passed** (193 + 1).

```bash
git add -A
git commit -F - <<'MSG'
feat: the three projection tables, by migration 0002

`projection_state`, `p_chronicle` and `p_source_stats` as in spec §3,
declared in `schema.py` and created by `0002_projections`, which is a
plain forward migration: nothing touches the log. The `db` fixture
truncates all six tables now — without that, projection state leaks into
the next test and looks like a wrong catch-up.

`evidence` is nullable on purpose: the kind of evidence lives in the
payload and a tombstone has none, so NOT NULL would make the chronicle
unable to show an erased event. `p_chronicle_occurred_idx` carries time
order; the primary key carries chain order.

`database-schema.md` gains three sections read off a migrated database,
and `projections.md` opens with the two sections that are true already.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

