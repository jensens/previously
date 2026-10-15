## Task 4: Lesen aus der Projektion — `GraphStore`, Kommandozeile, MCP, `project --check`

**Files:** `contract/store.py` (`GraphStore`), `storage/postgres.py`, `core/graph_read.py` (neu: die Leser über `GraphStore` mit Nachzug), `cli.py` (`entities`, `relations` ohne `--as-of`, `entity N`, `triage`, `status`, `project --check`), `mcp_server/server.py`, `read.py` (`list_entities`, `list_triage`, Kopf), Tests, `docs/reference/cli.md`, `docs/reference/mcp-tools.md`, `contract/store.py`-Docstring.

**Interfaces — Produces:** `GraphStore[Conn]` mit Lese-Abfragen auf `p_graph_thread` (Planentscheidung 6); `read_brackets[Conn](log, projection, graph_store, conn, bracket) -> Members` (Nachzug, dann `members` aus den Kanten der Projektion); `build_server(..., graph: GraphStore[Conn] | None)`; `previously project --check` (Planentscheidung 11). `--as-of` liest weiter das Log (Planentscheidung 7).

- [ ] **Step 1: Tests, die scheitern:** jede Liste gleich vorher (die Tests aus Phase 1 bleiben grün, unverändert); der Kopf zählt dieselben Einwände; **ein Aufruf liest das Log nicht mehr ganz** (der zählende Test aus Phase 1, `test_a_call_folds_the_graph_once_for_its_header_and_its_body`, wird ersetzt durch einen, der null vollständige Lesungen von `assertion` zählt, wenn nichts neu ist); `project --check` sauber nach jeder Folge, und eine von Hand verfälschte Zeile wird gemeldet.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** ein Leser ohne Nachzug → ein Test, der zwischen zwei Aufrufen schreibt, wird rot; `--check` vergleicht nichts → rot; Kontrolle grün.
- [ ] **Step 5:** Zählungen in `contract/store.py` nachmessen; sechs Tore, Commit.

---

