## Task 5: Die Chronik einer Klammer — `chronicle --within`, `previously(within=)`

**Files:** `cli.py` (`chronicle`), `storage/postgres.py` (`read_chronicle` mit Menge), `mcp_server/read.py`, `server.py` (`previously`), Tests, `docs/reference/cli.md`, `docs/reference/mcp-tools.md` (`TOOLS_SHA256` neu), `docs/how-to/keep-a-club-and-its-offices.md` oder eine neue Anleitung zum Zuordnen.

**Interfaces — Consumes:** `read_brackets`, `Members.holds`. **Produces:** `--within N` (Planentscheidung 8), `within` (Planentscheidung 9).

- [ ] **Step 1: Tests, die scheitern:** die Chronik des Sommerfests zeigt die zugeordneten Einheiten, eine Stufe höher den Verein (Markus, Z §17 Punkt 2); die Grenzen `--since`/`--until`/`--limit` gelten; eine unbekannte Klammer → `Error:` Exit 2; über MCP nur die Einheiten der Klammer, Cursor mit `within`, Titel; **Review Focus 3:** ein Event, das der Client nicht sehen darf, bleibt Platzhalter, auch mit `within`; eine Klammer, die der Client nicht sehen darf, gibt denselben Satz wie eine, die es nicht gibt; `within` lässt keine Einheit durch, die die Policy zurückhält.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutation:** `within` vor der Policy statt nach ihr → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

