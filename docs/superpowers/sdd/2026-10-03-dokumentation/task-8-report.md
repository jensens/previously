# Aufgabe 8 — Bericht

**Status:** fertig, alle sechs Tore grün, 194 Tests unverändert.
**Commit:** `6eabeb53a18d4fe69b8a17f3d841adcaa21acdb7` —
`docs: write down the documentation rule`

## Geänderte Dateien

- `CLAUDE.md` — Vorspann, Sprachregel, neuer Abschnitt `## Documentation`,
  drei Ergänzungen unter `## Gates`.
- `.gitignore` — drei deutsche Abschnittskommentare übersetzt, ein vierter
  Abschnitt für die zwei Zeilen aus Aufgabe 1 ergänzt.

## Je Schritt eine Zeile

1. **Sprachregel nachgezogen.** Neue Unterüberschrift *A specification starts
   in German and then freezes* am Ende von `## Language`: vier Punkte
   (deutsch entstehen, englisch veröffentlichen, mit datiertem Kopf
   einfrieren, bei Widerspruch gilt die Doku), danach der Absatz, der das
   Einfrieren ausdrücklich als **wiederkehrenden Schritt** festhält und davor
   warnt, es als Verbot eines vierten Specs zu lesen. Als Änderung
   geschrieben („new as of 2026-10-03"), mit Verweis auf den deutschen
   Einfrier-Kopf der drei Specs und auf `docs/explanation/design-records.md`.
2. **Doku-Regel geschrieben.** Neuer Abschnitt `## Documentation` vor
   `## Gates`: Skill `plone-doc-style:author` namentlich, „im selben Pull
   Request", ein Diátaxis-Quadrant je Seite, Stilregeln, die drei
   Doku-Kommandos als das sechste Tor, abgetippte Ausgabe als Messung mit
   `tests/test_docs_typed_output.py`, und dass Sphinx ein Label in einem
   Code-Kommentar nicht prüft, `tests/test_docs_references.py` aber schon.
   Unterabschnitt *Citing a reason from code* mit den zwei Formen (Seite
   nennen / Paragraph behalten plus `(frozen design record)`), dem Verbot in
   Programmausgaben, und dem Zeiger auf die Seite für die Abbildungstabelle.
3. **`.gitignore`-Lücke geschlossen.** Datei in die Liste der englisch
   gebundenen Wurzel-Konfiguration aufgenommen — zusammen mit `.vale.ini`,
   das aus demselben Grund fehlte —, mit einem Absatz, der die halbe
   Begründung benennt: nichts druckt `.gitignore`, aber wer `pyproject.toml`
   öffnet, öffnet es in derselben Sitzung. Die drei vorgefundenen deutschen
   Kommentare übersetzt (`# Werkzeuge` → `# Tools`, `# Editor und System` →
   `# Editor and system`, `# Worktrees und Agenten-Arbeitsbereiche` →
   `# Worktrees and agent workspaces`); `# Python` war schon englisch. Für
   `docs/_build/` und `.vale-styles/Microsoft/` ein `# Documentation`-Abschnitt.
4. **Alle sechs Tore**, jedes einzeln gefahren, Ausgaben unten.
5. **Commit** mit `Assisted-By:`-Trailer.

## Die drei Zusatzregeln

- **Regel 1 (alle sechs Tore namentlich)** → aufgenommen in `## Gates`,
  direkt unter den sechs Kommandos, mit der Messung (fünf gefahren, „alle
  grün" berichtet, `ruff check` und `pyright` nie gefahren, `pyright` rot mit
  drei Fehlern, Prüfer-Dispatch zählte dieselben fünf, Fehler überlebte zwei
  Prüfungen) und der handlungsnahen Anweisung, den Block darüber zu kopieren
  statt aus dem Gedächtnis eine Teilmenge zu nennen.
- **Regel 2 (ein Kommentar ist eine Behauptung)** → aufgenommen als
  `### A comment is a claim` unter `## Gates`, mit allen drei Messungen. Kein
  eigener Hauptabschnitt: `## Gates` trägt schon alle Regeln darüber, was
  belegt sein muss (keine Mocks, kein `# type: ignore`, Suppressions), und
  Regel 2 steht damit neben ihrem nächsten Verwandten.
- **Regel 3 (gemessene Mutation plus Kontrolle)** → aufgenommen als
  `### An assurance needs a test measured to fail` unter `## Gates`. Der
  bestehende Stichpunkt „An explicit assurance needs a test that fails when
  someone takes it back" ist **in den Unterabschnitt gewandert** statt
  zusätzlich stehen zu bleiben — zwei Fassungen derselben Regel hätten
  auseinanderlaufen können.

## Umformulierte Vorgaben

- **„Alles wird dokumentiert"** stand als absolute Zusage ohne Prüfbarkeit.
  Geschrieben als „Everything gets documented, and the documentation follows
  the `plone-doc-style:author` skill" plus die prüfbare Hälfte („check
  whether the documentation has to follow … in the same pull request").
- **Deutsches Betreuerzitat nicht übernommen.** `CLAUDE.md` ist von ihrer
  eigenen Regel auf Englisch gebunden; ein deutsches Zitat wäre eine
  Ausnahme, die die Datei nicht erteilt. Der Inhalt steht englisch
  paraphrasiert („states intent more precisely in German, and a vaguely
  stated intent costs more than a translation").
- **„Drei von sechs Toren sind die der Doku"** — erst so geschrieben, dann
  korrigiert: der Block zählt die drei Doku-Kommandos als **ein** Tor, das
  sechste. Nach Regel 2 die eigene Zahl nachgezählt, bevor sie stehen blieb.
- **„niemals eine Zahl darin anpassen"** zu „retype it rather than editing a
  number inside it" geschärft — die Anweisung ist *neu abtippen*, nicht
  *nichts tun*.
- **Vorspann.** „the reasoning behind each one is published in English under
  `docs/explanation/`" wäre eine Überbehauptung — für Attribution und
  Dependencies gibt es keine Seite. Jetzt: die Begründung sitzt anderswo, in
  `docs/explanation/` (mitgepflegt) und in den eingefrorenen Berichten (an
  ein Datum gebunden).

## Tore

| Tor | Ausgabe |
|---|---|
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `39 files already formatted` |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` |
| `uv run pytest -q` | `194 passed` |
| `make -C docs html && vale && linkcheck` | `build succeeded.` / `0 errors, 0 warnings and 0 suggestions in 20 files.` / `build succeeded.`, `output.txt` leer |

## Bedenken

1. **`.vale.ini` war die zweite Lücke derselben Art** und ist mit
   aufgenommen. Es trägt schon englische Kommentare, die Aufnahme ändert also
   nichts am Baum — aber die Liste zählte vier von sechs
   Wurzel-Konfigurationsdateien auf, und genau dieses Aufzählen hat bei
   `.gitignore` zur Auslassung geführt. `uv.lock` ist bewusst nicht in der
   Liste: generiert, von Hand steht dort nichts.
2. **Keine der drei neuen Regeln hat ein Tor.** Regel 1 (sechs Tore
   namentlich), Regel 2 (Zahlen im Kommentar) und Regel 3 (gemessene
   Mutation) sind Prozessregeln; nichts im Baum bricht, wenn sie verletzt
   werden. Nach der Zusagen-Regel dieser Datei sind sie damit Kommentare, nicht
   Zusagen. Regel 1 wäre teilweise maschinell prüfbar — ein Hook, der einen
   Bericht mit „alle Tore grün" gegen die tatsächlich gelaufenen Kommandos
   hält. Ich habe das nicht gebaut, weil es außerhalb dieser Aufgabe liegt;
   es gehört in die nächste Planung.
3. **`docs/explanation/design-records.md` ist jetzt von drei Seiten verlinkt**
   (`CLAUDE.md` zweimal, `README.md`, `DEPENDENCIES.md`, die drei Specs).
   `linkcheck` prüft nur Links **innerhalb** von `docs/`, die zwei neuen
   relativen Links in `CLAUDE.md` prüft also niemand. Sie sind von Hand
   gegen den Pfad geprüft; eine Umbenennung der Seite würde sie still
   brechen. Dasselbe gilt schon für `README.md` und `DEPENDENCIES.md` — ein
   Test, der alle relativen Markdown-Links der Wurzel-Dateien auflöst, wäre
   eine kleine, lohnende Ergänzung.
4. **Die Datei ist von 187 auf 309 Zeilen gewachsen.** Das ist viel für ein
   Dokument, dessen Vorspann „short on purpose" sagt. Ich habe nichts
   hinzugefügt, was auf eine Doku-Seite gehört, und die Messungen bewusst in
   einen Satz je Fall gedrängt — aber wenn der Betreuer kürzen will, ist der
   Abschnitt `### A comment is a claim` der Kandidat: seine drei Messungen
   stehen jede auch an ihrer eigenen Stelle im Baum, und die Regel selbst
   passt in zwei Zeilen.
