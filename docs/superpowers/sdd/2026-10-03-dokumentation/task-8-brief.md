## Task 8: Die Regeln nachziehen

**Files:**
- Modify: `CLAUDE.md`

Das Einfrieren der Specs ist nach Ruling P2 der Vorab-Durchsicht **Teil von
Aufgabe 7** — es muss vor der Verweisumstellung passieren, sonst behaupten die
neuen Code-Verweise einen Zustand, den es noch nicht gibt. Diese Aufgabe
schreibt nur noch die Regeln.

- [ ] **Schritt 1: Die Sprachregel in `CLAUDE.md` nachziehen**

Sie sagt heute „German is fine — specifications, plans, …". Das bleibt
richtig, bekommt aber einen Ablauf dazu, und der ist der Kern dieser Aufgabe:

- **Ein Spec entsteht auf Deutsch.** Das ist Absicht und keine Nachlässigkeit:
  der Betreuer formuliert Absicht auf Deutsch genauer, und eine ungenau
  formulierte Absicht ist teurer als eine Übersetzung.
- **Die Begründung wird auf Englisch veröffentlicht**, in
  `docs/explanation/`, und ist dort maßgeblich.
- **Der Spec friert ein, sobald seine Explanation-Seiten stehen**, mit
  datiertem Kopf. Danach ist er Provenienz: „so wurde es damals entschieden".
- Weicht ein eingefrorener Spec von der Doku ab, **gilt die Doku**.

Schreib die Änderung als Änderung hin, nicht als wäre es immer so gewesen — die
Regel ist am 2026-10-03 entstanden und am selben Tag verfeinert worden, und das
ist für einen Leser nützlicher als eine glatte Fassung.

- [ ] **Schritt 2: Die Doku-Regel in `CLAUDE.md`**

Ein eigener Abschnitt, mit diesen Punkten:

- Alles wird dokumentiert, und zwar nach dem Skill `plone-doc-style:author` (aufrufbar unter genau diesem Namen).
- Ändert sich Code, wird **geprüft**, ob die Doku nachzuziehen ist, und die Änderung kommt im **selben** PR mit.
- Jede Seite genau ein Diátaxis-Quadrant.
- Ein Satz pro Zeile, sentence-case Überschriften, Bindestriche in Dateinamen, amerikanisches Englisch.
- Die Tore: `make -C docs html` (Warnung = Fehler), `make -C docs vale`, `make -C docs linkcheck`.
- Abgetippte Ausgabe ist eine **Messung mit einem Datum**: sie wird zuletzt abgetippt, und `tests/test_docs_typed_output.py` hält die Testzahl fest.
- Ein Doku-Label in einem Code-Kommentar prüft Sphinx nicht — das tut `tests/test_docs_references.py`.

- [ ] **Schritt 3: Die Lücke in der Sprachregel schließen**

Die Liste der englisch gebundenen Wurzel-Konfiguration in `CLAUDE.md` nennt
`pyproject.toml`, `.importlinter`, `alembic.ini` und `.pre-commit-config.yaml`
— **`.gitignore` fehlt**, und das war eine Auslassung, keine Entscheidung. Der
Umsetzer von Aufgabe 1 hat die Regel darum korrekt gelesen und die Datei
unangetastet gelassen; sie trägt weiter deutsche Abschnittskommentare
(`# Werkzeuge`, `# Editor und System`, `# Worktrees und Agenten-Arbeitsbereiche`).

Zu tun: `.gitignore` in die Liste aufnehmen und seine drei Abschnittskommentare
übersetzen. Begründung für den Kommentar daneben: die „Programmausgabe"-Hälfte
der Regel trifft auf `.gitignore` nicht zu — es wird nirgends gedruckt —, aber
die andere Hälfte schon: wer `pyproject.toml` liest, liest auch `.gitignore`.
Die zwei Zeilen, die Aufgabe 1 angefügt hat (`docs/_build/`, `.vale-styles/`),
bekommen dabei ihren Abschnitt.

- [ ] **Schritt 4: Alle Tore**

```shell
uv run pytest
make -C docs html
make -C docs vale
make -C docs linkcheck
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run lint-imports
```

- [ ] **Schritt 5: Commit**

`docs: write down the documentation rule`

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** Die Explanation-Aufgaben 5 und 6 decken aus dem 1a-Spec §3.1–§3.4 (Kette, Kanonisierung, Zeitstempel, Prüfung), §4.1–§4.4 (Anfügen, Konfliktklassen, keine Vorab-Sperre, Stapeln) und §8 (Modulgrenzen); aus der Architektur §2, §4.6, §10.1, §10.5. **Nicht gedeckt und bewusst so:** Architektur §5–§9 und §12 beschreiben spätere Teilprojekte, über die Stufe 1a nichts zu sagen hat; §10.2 (modularer Monolith), §10.3 (Blob-Speicher), §10.4 (Deployment) und §10.6/§10.7 (Werkzeuge, Abhängigkeiten) betreffen das Ganze und nicht diese Stufe — ihre Verweise im Code bleiben darum nach Aufgabe 7, Schritt 2 als gekennzeichnete Verweise auf den eingefrorenen Bericht stehen. §11 (was offen bleibt) gehört nicht in eine Doku für Benutzer.

**2. Platzhalter.** Kein „TBD", kein „analog zu Aufgabe N", keine Schritte ohne Inhalt. Die Doku-Seiten tragen Seitenspezifikationen nach Abschnitt 10c des Doku-Skills — das ist die vorgesehene Planungsform für Dokumentation, kein Platzhalter.

**3. Namenskonsistenz.** Die Label, die Aufgabe 7 abbildet, werden in den Aufgaben 2, 5 und 6 erzeugt: `hash-domain`, `canonicalization`, `hash-chain`, `tombstone-seam`, `timestamps`, `concurrency`, `conflict-classes`, `module-boundaries`, `backup-encryption`, `cli-reference`, `configuration-reference`, `database-schema`, `hash-format`. Aufgabe 7 läuft **nach** 2, 5 und 6 — sonst scheitert ihr Test zu Recht.

**4. Review Focus.** Alle fünf Punkte haben einen Test: 1 → Aufgabe 7, Schritt 3; 2 → Aufgabe 3, Schritt 3; 3 und 4 → Aufgabe 1, Schritt 8; 5 → Aufgabe 1, Schritte 3 und 12 (`linkcheck_ignore` plus der Lauf im Tor).

**Eine Warnung an den Ausführenden.** Die Explanation-Aufgaben sind die eigentliche Arbeit dieses Plans, und sie sind leicht zu unterschätzen: es sind über 2000 Zeilen dichte Begründung mit Messungen, Zahlen und Gegenargumenten. In dieser Sitzung ist dieselbe Gefahr schon einmal benannt und mit einem AST-Vergleich geprüft worden. Hier gibt es dafür keinen mechanischen Prüfstein — nur die Regel, und einen Prüfer, der stichprobenweise gegen das Original liest.
