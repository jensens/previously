## Task 3: Die Projektion `graph`

**Files:** `storage/schema.py`, `migrations/versions/0006_graph.py` (neu), `contract/rows.py`, `contract/store.py` (`ProjectionStore`), `storage/postgres.py` (Methoden, `_PROJECTION_TABLES` für zwei Tabellen eines Namens), `core/projection/graph.py` (neu), `core/projection/__init__.py`, `tests/test_schema.py`, `tests/test_projection_worker.py`, `tests/test_projection_graph.py` (neu), Tests mit getippter `project`-/`migrate`-Ausgabe, `docs/reference/database-schema.md`, `docs/explanation/projections.md`.

**Interfaces — Produces:** `GraphThreadRow` und `GraphVersionRow` in `contract/rows.py` (Planentscheidung 5); `ProjectionStore`-Methoden `insert_graph_versions`, `graph_version_ids(conn, subjects) -> dict[int, list[int]]`, `class_subjects(conn, under_ids) -> set[int]`, `upsert_graph_threads`, `delete_graph_threads`; `GRAPH = GraphProjection(name="graph", version=1)` in `PROJECTIONS` (nach `chronicle`, `source-stats`). `truncate_projection("graph")` leert beide Tabellen.

- [ ] **Step 1: Tests, die scheitern:**
  - Schema und Migration gleich (die vorhandenen Tests in `test_schema.py` decken es mit; Text von `test_the_projection_tables_exist` nachziehen);
  - **Gleichwertigkeit** (Review Focus 2): Hypothesis über Folgen von Fassungen aller Stufen, Ablehnungen, Freigaben, Tilgungen (auch einer Quelle, die per Kaskade die Aussage nimmt), Klassen (Rückzug mit und ohne `demote`), mit Nachzügen an zufälligen Stellen — danach ist jede Zeile von `p_graph_thread` gleich der Zusammenfassung von `fold_graph` über das ganze Log; inkrementell gleich neu gebaut (`test_incremental_equals_rebuilt` erweitert);
  - **gleichzeitig** (Review Focus 5): zwei Verbindungen ziehen nach, jede sieht einen ganzen Stand, keine Zeile doppelt;
  - kein Inhalt in den Tabellen (die Spalten sind die von Planentscheidung 5, ein Test hält die Spaltennamen).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** eine Tilgung macht ihre Kennung nicht schmutzig → Gleichwertigkeit rot; ein Klassenrückzug macht nichts schmutzig → rot; Kontrolle grün.
- [ ] **Step 5:** getippte `project`-Ausgaben und `migrate`-Zeilen aus echten Läufen nachziehen; sechs Tore, Commit.

---

