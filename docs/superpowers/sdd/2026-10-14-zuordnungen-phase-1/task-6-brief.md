## Task 6: MCP — Lesen, Schreiben, Rückfragen, der Kopf

**Files:** `src/previously/mcp_server/read.py`, `render.py`, `server.py`, `tests/test_mcp_server.py`, `tests/test_render.py`, `tests/test_docs_references.py`, `docs/reference/mcp-tools.md`.

**Interfaces — Consumes:** Aufgaben 1–4; `Service.answer`, `staged`, `seal`/`open_handle`, `write_record`, `render_page`, `Stated`, `_ASK_THE_PERSON` (CF §8). **Produces:**
- `list_entities(type?, state?, proposals?, subject?, history?, cursor?)`: Entitäten mit ihren Beziehungen, unter der Policy (Planentscheidung 12), seitenweise wie `list_obligations`.
- `write_entity(items, confirm?)` und `write_relation(items, confirm?)`: zwei Schritte wie `write_assertion`; jedes Element trägt `confidence` (0..100); die Vorschau zeigt die Stufe, die der Schreibweg bestimmen würde; die Bestätigung gibt sie als `expect_levels` (Review Focus 2). Ein Ende, das der Client nicht sehen darf oder das es nicht gibt: ein Satz für beides (Review Focus 3).
- `list_triage(cursor?)`: Einwände zuerst, dann Rückfragen, dann Vorschläge, unter der Policy.
- `write_triage_answer(question, choice, reason?)`: ein Aufruf, `meta=_ASK_THE_PERSON`, schreibt die Antwort im Namen des Betreibers — wie `write_approve` direkt mit dem Autor der Rückfrage.
- `write_approve` und `write_reject` nehmen auch Graph-Fassungen.
- **Der Kopf** jedes Ergebnisses (`render_page` und `render_text`) bekommt ` · N objections pending` hinter dem Titel, gezählt über die Einwände, die der Client sehen darf (Z §7.5).
- `INSTRUCTIONS` sagt, was Entitäten und Beziehungen sind, dass das Modell `confidence` ehrlich angibt und der Server die Stufe bestimmt, dass ein Widerspruch gegen eine direkte Aussage ein Einwand wird und nie ersetzt, dass eine unklare Zuordnung eine Rückfrage mit Kandidaten wird und nicht geraten.

- [ ] **Step 1: Tests, die scheitern:** je Werkzeug in beiden Generationen (`MODES`); Vorschau und Bestätigung; ein Vorschlag des Clients, den der Betreuer über `write_approve` freigibt (Z §17 Punkt 1); `expect_levels` (Review Focus 2); verborgenes und fehlendes Ende mit demselben Satz (Review Focus 3); `recollection` ohne `source:recollection` als Platzhalter; der Kopf mit null, einem und zwei Einwänden, und ohne Einwände, die der Client nicht sehen darf; `write_triage_answer` mit einem Kandidaten und mit einer Kennung, die keiner ist; `mcp_access` ohne Text (Planentscheidung 15); die Prüfsumme der Werkzeugliste und die Namensliste neu (`TOOLS_SHA256`, CF §8), `INSTRUCTIONS` ganz auf `mcp-tools.md`, jedes neue Werkzeug mit Abschnitt und Tabelle seiner Parameter.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Stufe vom Client übernommen → rot; Kopf zählt verborgene Einwände → rot; Ende verborgen mit anderem Satz → rot; Kontrolle grün.
- [ ] **Step 5:** `mcp-tools.md` (Werkzeuge, Kopf, „fifteen tools"), sechs Tore, Commit.

---

