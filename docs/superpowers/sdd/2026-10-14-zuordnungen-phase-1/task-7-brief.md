## Task 7: Doku, Handoff, Landkarte

**Files:** `docs/explanation/graph.md` (neu; Bezeichner der Seite nach dem Umsetzer, Label `(graph)=`), `docs/how-to/keep-a-club-and-its-offices.md` (neu), `docs/how-to/let-a-model-stand-for-a-class.md` (neu), `docs/explanation/assertions.md` (Verweis auf die dritte Stufe), `docs/explanation/processing-policy.md` (Erinnerung als Quelle), `docs/reference/environment.md`, `docs/how-to/connect-claude-code-and-vibe.md` (neue Werkzeuge, Ask-Regel für `write_triage_answer`), `docs/how-to/record-what-is-owed-and-decided.md` (Ask-Regel), Indexseiten, `README.md` falls es Fähigkeiten aufzählt, `docs/superpowers/handoffs/2026-10-14-kup6s-graph-phase-1.md` (neu, englisch), `docs/superpowers/landkarte.md`, `NOTIZEN.md` nicht.

- [ ] Nach Z §16, soweit Phase 1:
  - **Explanation:** warum der Kern generisch ist und die Bedeutung deklariert, und wo die Linie gegen eine DSL liegt; warum ein Property Graph und kein Triple Store, und warum aus dem Log gefaltet; warum drei Stufen und warum ein Modell nie eine direkte Aussage ersetzt (Einwand); warum die Stufe der Server bestimmt; warum die Arten des Gates nie transitiv sind; warum Erinnerung zurückgehalten ist, bis eine Regel sie öffnet. Mit Verweisen auf Z, wo eine Entscheidung datiert ist (frozen design record — **hier noch nicht eingefroren**, also als Spec zitieren, nicht als frozen).
  - **How-to:** einen Verein mit seinen Ämtern über die Jahre festhalten (Vellenfeld, Z §17 Punkt 1); ein Vokabular anpassen; eine Freigabeklasse einrichten, ihre Trefferquote lesen, sie zurückziehen; Einwände und Rückfragen beantworten.
  - `environment.md`: in Phase 1 nichts Neues außer `apply` nach dem Update; die Ask-Regel für `write_triage_answer` als Forderung an den Client.
  - **Handoff** (englisch): `0.1.0a7` oder das nächste Release; keine Migration; `previously vocabulary apply --base` im Werkzeug-Pod nach dem Image; die Werkzeugliste wächst auf fünfzehn, Vibe frischt auf; `source:recollection` nur, wenn der Betreiber es will. Prüfungen: `vocabulary show` zeigt das Grundvokabular; `entities` antwortet; `list_entities` antwortet über MCP.
  - **Landkarte:** Phase 1 gebaut; die Messung der Endprüfung; Abnahme nach Z §17 Punkt 1 als nächster Schritt; zählen vorher und nachher.
  - Der Spec bleibt lebendig (Z, Status); kein Einfrieren in Phase 1.
- [ ] Sechs Tore, `pip-audit`, Testblock des Tutorials aus einem grünen Lauf, Commits.

---

## Nach Aufgabe 7

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung. Das Code-Paket **misst** `entities` und `relations --at` bei 10 000 und 100 000 Beziehungen (Planentscheidung 14, Z §3.4) und schreibt die Zahlen in die Landkarte und auf die Explanation-Seite.
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-14-zuordnungen-phase-1/`.
3. Push und PR. Danach, mit dem Betreuer: Merge, Release, Handoff, Abnahme nach Z §17 Punkt 1.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung, Phase 1:** Z §3.1 → 2; §3.2 → 1 (Verhalten), 2 (Wirkung); §3.3 → 2 (`Period`), 5 (`--as-of`); §3.4 → Planentscheidung 14, Endprüfung; §4.1–§4.4 → 1; §4.5 → 1, 2, 3; §4.6 → 1, 5 (Sprachen), 2 (Kennungen); §5 → 1; §6.1–§6.5 → 2, 4; §7.1–§7.3 → 2, 3, 4, 5, 6; §7.4 → 2, 4, 6; §7.5 → 5 (`triage`, `status`), 6 (Kopf); §7.6 → 2, 3 (Grenzen), 3 (Trefferquote, Stichprobe); §10.2–§10.3 soweit Phase 1 → 5, 6 (`in` kommt mit Phase 2); §10.4 → Global Constraints; §13 → 7; §15 Punkte 1–8 → 1–4; §16 → 7; §17 Punkt 1 → 5, 6, 7.
- **Nicht in Phase 1, bewusst:** ein Event als Ende (§8, Phase 2), `chronicle --in` und `in` über MCP (Phase 2), alles an Kreisen und Gate (§9, Phase 3), Verpflichtungen im Schema (§11, Phase 4).
- **Platzhalter:** keine; die genauen Sätze der Meldungen legen die Umsetzer fest, und `cli.md`/`mcp-tools.md` zitieren sie, gehalten von `test_docs_references`.
- **Namen:** `Vocabulary`, `KindSpec`, `FieldSpec`, `read_vocabulary`, `apply_vocabulary`, `GATE_TYPES`, `Claim`, `EntityBody`, `RelationBody`, `Period`, `GraphVersion`, `GraphThread`, `Graph`, `fold_graph`, `ClassState`, `ApprovalClass`, `Classes`, `read_classes`, `set_class`, `HitRate`, `hit_rates`, `sample`, `check_claims`, `write_claims`, `read_graph`, `claim_verdict`, `GraphRefused`, `Written` — überall gleich.
- **Bekannte Spannung:** Planentscheidung 12 hält Erinnerungen vor MCP-Clients zurück, bis der Betreiber `source:recollection` öffnet; das ist die sichere Seite, kostet aber in der Abnahme einen Handgriff. Der How-to sagt es.
