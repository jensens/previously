## Task 6: Doku, Handoff, Landkarte

- [ ] **Explanation** (`graph.md`): warum `concerns` deklariert und nicht eingebaut ist; warum ein Event am Anfang Quelle ist; die Menge einer Klammer und „das Genauere ersetzt"; die Projektion: was sie hält (keinen Inhalt), wie sie nachzieht, warum der Schreibweg noch faltet, `project --check`; `projections.md` um `graph`.
- [ ] **How-to:** Mails und Einheiten zuordnen und die Chronik einer Klammer lesen (Markus).
- [ ] **Handoff** (englisch): **Migration `0006_graph`**, `previously migrate` zuerst; dann `vocabulary apply --base` (fügt `concerns` hinzu); `previously project` baut die Projektion beim ersten Lauf, oder der erste Leser tut es; Prüfungen: `migrate` meldet `0006_graph`, `vocabulary show` zeigt `concerns`, `project` zeigt eine Zeile `graph`, `chronicle --within` antwortet. Zugestellt erst, wenn `manifest` grün ist.
- [ ] **Landkarte:** Phase 2 gebaut; Fundorte als offener Punkt mit Planentscheidung 12; der Schreibweg, der noch faltet; zählen vorher/nachher.
- [ ] Sechs Tore, `pip-audit`, Tutorial-Block aus einem grünen Lauf, Commits.

---

## Nach Aufgabe 6

1. Endprüfung über den Zweig, eine Fixwelle, eine Nachprüfung. **Messung auf einer festen Kopie** bei 10 000 und 100 000 Beziehungen: `entities`, `relations --at`, `chronicle --within`, MCP `whoami` und `list_entities`, ein Schreibvorgang, `verify`, `project` (erster Bau und Nachzug).
2. Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-15-zuordnungen-phase-2/`.
3. Push und PR.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung, Phase 2:** Z §8 (concerns, Einheit, keine Partition, transitiv, das Genauere, Markus) → 1, 2; Anhänge → nur Planentscheidung 3 (ein Anhang als Event wird gleich behandelt, wenn es ihn gibt); Fundorte → Planentscheidung 12, Landkarte; Zusammenhang aus dem Graphen → Einheit 6, nicht hier; §10.1 (Projektion) → 3, 4; §10.2 (`--within`) → 5; §10.3 (`within`) → 5; §10.4 → Global Constraints, Review Focus 3; §15 Punkte 9–11 → 2, 5; §17 Punkt 2 → 5.
- **Abweichung vom Spec, bewusst:** der Parameter heißt `within` statt `in` (Entscheidung des Betreuers); `--as-of` und der Schreibweg falten weiter (Planentscheidungen 5, 7).
- **Platzhalter:** keine; die Meldungen legen die Umsetzer fest, die Seiten zitieren sie.
- **Namen:** `EVENT_START`, `ANY_ENTITY`, `Members`, `members`, `START_NOT_A_SOURCE`, `GraphProjection`, `GRAPH`, `GraphThreadRow`, `GraphVersionRow`, `GraphStore`, `read_brackets` — überall gleich.
