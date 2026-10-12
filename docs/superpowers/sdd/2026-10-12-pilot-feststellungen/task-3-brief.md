## Task 3: Die Kommandozeile

**Files:** `src/previously/cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `pyproject.toml` (T201).

**Interfaces — Consumes:** Aufgaben 1, 2. **Produces:**
```
previously assert obligation --debtor REF --creditor REF --what TEXT [--due DATE] [--state STATE]
                             [--subject ID] [--reason TEXT] --source EVENT[:SEQ,SEQ…] [--source …] [--yes]
previously assert decision   --what TEXT --by REF [--by …] --on DATE [--state STATE] [--replaces ID]
                             [--subject ID] [--reason TEXT] --source … [--yes]
previously approve ID [ID …] [--yes]
previously reject ID [--reason TEXT] [--yes]
previously obligations [--circle NAME] [--owed-by REF] [--owed-to REF] [--state STATE] [--overdue] [--proposals]
previously obligation ID [--history]
previously decisions [--circle NAME] [--state STATE] [--proposals]
previously decision ID [--history]
```
- Mit `--subject` füllen fehlende Felder sich aus dem heutigen Gewinner; die Vorschau zeigt die vollständige neue Fassung und den Unterschied (`changes`). Autor `human:operator`, Verantwortung direkt.
- Vor dem Fragen: Form und Verweise prüfen (`Error: …`, Exit 2); dann die Nutzlast als JSON, dann `_confirmed`; danach `assertion <id>` je Fassung, Exit 0; Ablehnung der Frage → `nothing written`, Exit 1.
- **Hinweis zu `name:`** (F §2.1): nennt eine Quelle eine Adresse, deren Anzeigename den `name:`-Text enthält (ohne Groß- und Kleinschreibung), schreibt die Vorschau `hint: <adresse> appears in the sources; address: is a reference that holds`. Kein Verbot.
- Listen: eine Zeile je Eintrag mit Kennung, Zustand (überfällig markiert), Frist, Schuldner → Gläubiger bzw. Entscheider, Text, `n versions`, `k proposals`; ohne `--proposals` nur Einträge mit Gewinner, mit nur die mit anhängigen Vorschlägen oder einem Vorschlag als Gewinner. `--history`: alle Fassungen mit Unterschied, Grund, Quellen, Verantwortung, Autor, Ablehnungen.

- [ ] **Step 1: Tests, die scheitern:** jedes Kommando gegen echtes PostgreSQL, Ausgabe wörtlich; Review Focus 5 (Daten vor dem Fragen abgewiesen; `due` gestern → sofort überfällig); `--subject` füllt auf; der `name:`-Hinweis und seine Kontrolle; `approve` einer Liste; `reject` mit Grund; `--circle` findet über `circle:X` beim Schuldner und über eine Quelle des Kreises; ohne Antwort auf die Frage nichts geschrieben.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `--subject` füllt nicht auf → rot; Liste zeigt Vorschläge als gültig → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md` (Kommandos, Wortlaute, Exit-Codes); T201 gemessen; sechs Tore, Commit.

---

