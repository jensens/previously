## Task 5: Die Kommandozeile

**Files:** `src/previously/cli.py` (liest die Einstellungen wie `PREVIOUSLY_IMAP_FOLDER` aus der Umgebung; dort auch `PREVIOUSLY_LANGUAGE`), `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`, `pyproject.toml` (T201).

**Interfaces — Consumes:** Aufgaben 1–4. **Produces:** die Kommandos (Wortlaute oben):
- `previously entity TYPE --name … [--field NAME=VALUE]… [--language TAG] [--source …]… | --recollection [--subject N] [--state …] [--reason …] [--yes]`; `previously entity N [--history]` zeigt die Entität, ihre Beziehungen in beide Richtungen und anhängige Fassungen.
- `previously relate TYPE --from N --to N [--from-date D] [--to-date D] [--field …]… [--source …]… | --recollection [--subject N] [--retract] [--reason …] [--yes]`.
- `previously entities [--type T] [--state S] [--proposals]` und `previously relations [--type T] [--from N] [--to N] [--at YYYY-MM-DD] [--as-of ISO-DATETIME]`.
- `previously classes add NAME --author model:C --assertion entity|relation --type T… --threshold P [--from …] [--until …] --statement … [--yes]`; `classes revoke NAME [--demote] --statement … [--yes]`; `classes list` mit Trefferquote; `classes sample NAME [--count K]`.
- `previously triage`: Einwände zuerst, dann Rückfragen, dann Vorschläge; `previously answer N --choose ID [--reason …] [--yes]`; `previously status`: je eine Zeile `objections`, `questions`, `proposals`, mit Zahl.
- `previously approve` und `reject` nehmen auch Graph-Fassungen (Planentscheidung 5).
Ausgabe wie bei den Feststellungen: Vorschau als JSON auf stdout, Hinweise auf stderr, `Error:` mit Exit 2, „nothing written" mit Exit 1 (CF §7). Beschriftungen nach Planentscheidung 11.

- [ ] **Step 1: Tests, die scheitern:** je Kommando die Ausgabe und die Exit-Codes; die Vellenfeld-Folge auf der Kommandozeile (Z §17 Punkt 1: Verein, Gründung, Obmann, Schriftführer, Kassier, Vorstände mit Zeiträumen, „wer war am 1. März 2019 im Vorstand?" über `relations --type member_of --to N --at 2019-03-01`); ein geändertes Vokabular deutet nichts Früheres um (`entity N --history` zeigt die alte Fassung unverändert, markiert, was nicht mehr passt); `--as-of` zeigt den Stand eines früheren Zeitpunkts; Beschriftung in der Arbeitssprache, mit Ausweichsprache markiert; `classes list` mit Trefferquote nach einer Korrektur; `triage` in der Reihenfolge; `--help` hält `COMMANDS`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `triage` ohne Einwände zuerst → rot; `--at` übergangen → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md` (je Kommando ein Abschnitt, Exit-Codes), `configuration.md` (`PREVIOUSLY_LANGUAGE`), T201 nachmessen und die Erzählung in `pyproject.toml` ergänzen; sechs Tore, Commit.

---

