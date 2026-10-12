## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/assertions.md` (neu), `docs/reference/assertions.md` (neu), `docs/how-to/record-what-is-owed-and-decided.md` (neu), `docs/reference/mcp-tools.md`, `docs/reference/environment.md`, `docs/reference/configuration.md`, `docs/how-to/connect-claude-code-and-vibe.md`, `docs/explanation/erasure.md`, `docs/explanation/design-records.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-12-kup6s-assertions.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach F §13 und:
  - **Explanation:** warum vollständige Fassungen; Autor und Verantwortung getrennt, Vorrang über die Verantwortung; warum MCP nur vorschlägt und Freigabe über MCP an der Umgebung hängt; warum die Tilgung kaskadiert; warum erwähnt nicht beteiligt heißt; warum `name:` eine Beschriftung ist; warum gefaltet und nicht projiziert wird (Planentscheidung 1, mit der Messung der Endprüfung).
  - **Reference:** die Nutzlast je Unterart (Planentscheidung 2), die Verweise, die Werkzeuge; `test_docs_references` hält die zitierten Wortlaute.
  - **How-to:** eine Verpflichtung festhalten; Vorschläge von Claude Code durchgehen, freigeben, ablehnen; was offen ist abfragen; `write_approve` und `write_reject` im Client nicht automatisch erlauben.
  - `environment.md`: `PREVIOUSLY_MCP_CONFIRM_KEY` nur im MCP-Server; die Forderung an den Client mit Risiko.
  - **Handoff** (englisch): das neue Geheimnis nur für `previously-mcp`; keine Migration; die Forderung an den Client; die Ausgabezeile der Aufnahme mit mehreren Ordnern (PR #16: ` in <folder>`, `Error: folder <name>:`).
  - **Landkarte:** Einheit 5 gebaut; die offenen Punkte aus F §15 je unter ihre Einheit; erledigt: zweiter Schreibweg, `verify` kennt die Form der Feststellung, `p_obligation` braucht `responsibility`; zählen vorher und nachher.
  - Den Spec einfrieren (Kopf wie die anderen, Abweichungen des Baus im Kopf, „Was offen bleibt" in der Vergangenheit); `design-records.md` um die zitierten Paragraphen.
- [ ] Sechs Tore, `pip-audit`, Testblock des Tutorials, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung. Das Code-Paket **misst** die Lesezeit von `obligations` und `list_obligations` bei 5 000 Feststellungen (Planentscheidung 1).
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-12-pilot-feststellungen/`.
3. Push und PR.
4. Nach dem Merge: Release; dann die Abnahme nach F §14, vom Betreuer.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** F §2 → 1; §2.1 → 1 (Grammatik), 3 (Hinweis); §3 → 1 (Faltung), 2 (Freigabe/Ablehnung schreiben), 3, 4 (Ist-Zustand und Geschichte); §4, §5 → 1, 3; §6 → 3, 5; §6.1 → 5; §7 → 2 (Verdikt, Filter), 4; §8 → 2; §9 → 2, Planentscheidung 1; §10 → 5, 6; §12 Punkte 1–8 → 1, 2, 4, 5; §13 → 6; §14 → „Nach Aufgabe 6"; §15 → Landkarte in 6.
- **Platzhalter:** keine; die genauen Sätze der Meldungen legt der Umsetzer fest und `cli.md`/`mcp-tools.md` zitieren sie.
- **Namen:** `Statement`, `ObligationBody`, `DecisionBody`, `Source`, `Version`, `Thread`, `fold`, `changes`, `overdue`, `payload_of`, `assertion_problem`, `parse_statement`, `reference_problem`, `write_statements`, `read_threads`, `source_identities`, `assertion_verdict`, `thread_circles`, `AssertionRefused`, `Stated`, `seal`, `open_handle`, `HandleRefused` — überall gleich.
- **Bekannte Abweichung vom Spec:** Planentscheidung 1 (keine Projektion, keine Migration), vom Betreuer am 2026-10-12 bestätigt.
