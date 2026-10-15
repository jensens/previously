## Task 1: Vokabular — `event` als Anfang, `*` als Ziel, `concerns`

**Files:** `core/vocabulary.py`, `vocabulary.toml`, `core/graph.py` (`conformance_problem`), `tests/test_vocabulary.py`, `tests/test_graph.py`, `docs/reference/vocabulary.md`.

**Interfaces — Produces:** `EVENT_START: Final = "event"`, `ANY_ENTITY: Final = "*"` in `core/vocabulary.py`; `KindSpec.from_`/`to` dürfen sie enthalten (Planentscheidung 1); `conformance_problem` lässt einen Event-Anfang zu, wenn die Art `event` in `from_` nennt, und ein Ziel jeder Art bei `*` — und weist sonst wie bisher ab.

- [ ] **Step 1: Tests, die scheitern:** Form und Datei mit `event` und `*` hin und zurück; `event` in `to`, `*` in `from`, `*` mit einer anderen Art zusammen → abgewiesen mit Satz; `concerns` im Grundvokabular; `apply --base` auf einem Log aus Phase 1 schreibt genau `concerns` und meldet sonst nichts (F-a); `conformance_problem`: Event-Anfang bei `concerns` passt, bei `holds` nicht; Ziel `*` nimmt jede Art, `retracted` eingeschlossen nicht neu.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutation:** `*` nimmt nur Arten aus `to` → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

