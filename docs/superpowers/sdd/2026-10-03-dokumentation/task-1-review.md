# Review: Task 1 — Werkzeugkette, Makefile und das sechste Tor

Commit geprüft: `9f2804a` (`0a4b6e2..9f2804a`). Alle Befehle liefen aus dem
Checkout `.../worktrees/stufe-1a-log` (lesend) sowie aus einem eigenen,
detachten Worktree unter `/tmp/previously-gate-test` für die
Scheitern-Experimente; letzterer wurde anschließend mit
`git worktree remove --force` entfernt.

## Urteil 1: Spec-Treue

**ANGENOMMEN.** Alle dreizehn Schritte des Briefs sind umgesetzt, in der
vorgegebenen Reihenfolge nachvollziehbar, und die im Bericht behaupteten
Messungen (grünes `html`, grüner `vale`, grüner `linkcheck`, 187 Tests, fünf
unveränderte Tore, saubere Commit-Botschaft mit `Assisted-By:`) halten bei
eigener Nachmessung. Die sechs dokumentierten Abweichungen sind begründet,
vier davon sind Korrekturen echter Lücken im Brief (siehe unten), nicht
Freiheiten des Umsetzers.

## Urteil 2: Qualität

**ANGENOMMEN, mit einem Befund mittlerer Schwere.** Die Umsetzung ist
sorgfältig, die drei Scheitern-Experimente aus Frage 1 bestätigen, dass das
Tor hält. Ein zusätzliches, viertes Experiment (unten) deckt jedoch eine vom
Brief nicht vorgesehene und vom Umsetzer nicht erwähnte Lücke in Vales
Geltungsbereich auf: Text innerhalb einer MyST-Fence (`{note}`,
`{grid-item-card}`, `{tab-item}`, …) wird von Vale überhaupt nicht geprüft —
und genau dort liegt der gesamte Fließtext der vier Karten auf der
Landing-Page selbst. Kein Blocker für diesen Commit (kein Stilverstoß ist
heute davon betroffen), aber eine Lücke, die die nächsten sieben Aufgaben
kennen sollten, bevor sie Admonitions oder Karten mit echtem Inhalt befüllen.

## Frage 1: Hält das Tor, was es behauptet?

### Die drei verlangten Scheitern-Experimente

Alle drei in `/tmp/previously-gate-test`, mit kaltem `_build/`
(`rm -rf docs/_build` vor jedem Lauf, wie die CI es ohnehin tut):

1. **Seite ohne Toctree** (`docs/how-to/orphan.md` angelegt, nirgends
   referenziert): `make -C docs html` → Exit-Code **2**,
   `WARNING: document isn't included in any toctree [toc.not_included]`,
   unter `-W` tödlich. **Tor hält.**
2. **Kaputter Querverweis** (`{doc}`/`/how-to/does-not-exist`` an
   `docs/how-to/index.md` angehängt): `make -C docs html` → Exit-Code **2**,
   `WARNING: unknown document: '/how-to/does-not-exist' [ref.doc]`.
   **Tor hält.**
3. **Stilverstoß für Vale** (Satz „You cannot undo this action…“ als
   gewöhnlicher Fließtext an `docs/how-to/index.md` angehängt):
   `make -C docs vale` → Exit-Code **2**,
   `Use 'can't' instead of 'cannot'. Microsoft.Contractions`. **Tor hält.**
   Dieser Lauf fand zugleich aus einem Zustand ohne `.vale-styles/` statt
   (frischer Worktree) und zog den Stil-Paket korrekt automatisch nach
   (`vale sync` lief, lud das Vale-Binary und synchte `Microsoft`).

### Viertes, selbst hinzugefügtes Experiment: derselbe Stilverstoß in einer Fence

Derselbe Satz, aber eingebettet in ` ```{note} … ``` ` statt als
Fließtext: `make -C docs vale` → Exit-Code **0**, „0 errors…“. Vales
Markdown-Parser behandelt jede Backtick-Fence — auch eine mit
geschweiftem Direktiven-Namen wie `{note}` oder `{grid-item-card}` — als
Codeblock und prüft ihren Inhalt grundsätzlich nicht. Beleg dafür im
bestehenden Commit selbst: `docs/index.md:42` trägt „what the chain
**does not** cover" innerhalb der `{grid-item-card}`-Fence der
Explanation-Karte — exakt dieselbe Formulierung, die in
`docs/explanation/index.md:3` (dort als freier Fließtext) zu „doesn't"
korrigiert wurde — und Vale meldet dafür nichts, weil die Karte dafür
unsichtbar ist. Keine Inkonsistenz, die heute falsch *aussieht*, aber ein
blinder Fleck: die komplette Kartenprosa der eigenen Landing-Page, und
jede künftige Admonition, ist für Vale unsichtbar. **Befund, siehe unten.**

### `make -C docs vale` aus frischem Zustand

Bestätigt wie oben: frischer Worktree ohne `.vale-styles/` →
`vale sync` lädt automatisch (`vale not found. Downloading it...` →
`SUCCESS Synced 1 package(s)`), zweiter Lauf ohne Dateiänderung überspringt
den Sync vollständig (kein Download-Output mehr). Die Guard-Klausel
`test -d .vale-styles || …` tut genau das, was der Bericht behauptet.

### `linkcheck`

Funktioniert tatsächlich, nicht nur dem Namen nach: ein frei erfundener
toter Host wurde als `broken` mit `NameResolutionError` gemeldet, Exit-Code
**2**. Der `linkcheck_ignore`-Regex wurde gezielt gegen Überdeckung
geprüft: eine erfundene GitHub-Issue-URL
(`.../issues/99999`) wurde korrekt `-ignored-`, eine erfundene
GitHub-URL **außerhalb** des Issue/Pull-Musters
(`.../this-path-does-not-exist-xyz`) wurde weiterhin geprüft und korrekt
als `404 Client Error` gemeldet. Das Muster nimmt also nur das aus, was es
soll, nicht mehr. Fehlende externe Links in der heutigen Doku sind korrekt
als „nichts zu prüfen", nicht als „geprüft und gut", im Bericht vermerkt.

## Frage 2: Die sechs Abweichungen

1. **`linkify-it-py` als achte Abhängigkeit.** Nachgemessen durch
   Entfernen des installierten Pakets (Modul aus `site-packages`
   verschoben, Sphinx direkt über das Venv-Python gestartet, um
   `uv run`s Auto-Resync zu umgehen): identischer Fehler wie im Bericht,
   `ModuleNotFoundError: Linkify enabled but not installed.` aus
   `markdown_it/rules_core/linkify.py`. Claim korrekt. Eintrag in
   `DEPENDENCIES.md` hat Datum und Beleg im selben Format wie die anderen
   sieben — Projektregel erfüllt.
2. **Grid-Fence 3→4 Backticks.** Nachgebaut (Outer-Fence wieder auf 3
   Backticks gesetzt, gleich der inneren): produziert exakt die
   behaupteten drei `[design.grid]`-Warnungen (unter `-W` tödlich) — und
   zusätzlich, als Nebenwirkung der verschobenen Fence-Grenzen, vier
   weitere `toc.not_included`-Warnungen, weil die nachfolgende
   `{toctree}`-Direktive dadurch mitverschluckt wird. Die Begründung ist
   nicht nur empirisch richtig, sie deckt sich mit Abschnitt 4 des
   Doku-Stil-Skills („Outer fence must use more backticks than inner")
   wörtlich. Gerendertes HTML geprüft: exakt 4 `sd-card`-Divs in genau 1
   `sd-row`-Div, jeder Kartentitel vorhanden. Korrekt.
3. **Zwei Wortänderungen für `Microsoft.Contractions`.** Bedeutung
   unverändert geprüft (reine Kontraktion, kein Bedeutungsunterschied).
   Keine weiteren von Vale beanstandeten Stellen in den fünf geprüften
   Dateien — mit dem Vorbehalt aus dem vierten Experiment oben: Vale sieht
   nur, was außerhalb einer Fence steht.
4. **ruff-Autofix `I001`.** `uv run ruff check tests/test_docs_build.py`
   läuft sauber gegen den committeten Stand; die Begründung
   (`force-single-line` + `no-sections` verlangt keine Leerzeile zwischen
   zwei einzeiligen Importen) ist korrekt.
5. **„Five gates" → „six gates" in `gates.yml`.** Beide Stellen korrekt
   aktualisiert; die Datei nach weiteren Zahlwörtern durchsucht
   (`five|six|seven|four|three|two|one`): die verbleibenden Treffer
   („five hygiene hooks" aus `.pre-commit-config.yaml`, unverändert und
   korrekt; „Two lines, no gate" für die Versions-Ausgabe, unverändert und
   korrekt) sind beide sachlich richtig und nicht Teil dieser Änderung.
   Keine weitere falsche Zahl gefunden.
6. **Kein Kommentar an den zwei `.gitignore`-Zeilen.** Wie vom
   Auftraggeber vorgegeben: kein Befund.

## Frage 3: Sicherheit des Workflows

Diff von `gates.yml` gegen den Vorzustand gelesen: `permissions: contents:
read`, die `on:`-Trigger und beide gepinnten `uses:`-SHAs sind
unverändert; Gate 6 ist ein reiner `run:`-Block aus drei `make`-Aufrufen,
ohne `upload-artifact`, ohne Secrets, ohne zusätzliche `with:`-Eingaben.
Nicht in GitHub geprüft (kein Push von hier aus möglich); stattdessen
lokal nachgewiesen: die YAML ist syntaktisch gültig
(`python3 -c "import yaml; yaml.safe_load(...)"`), und jeder der drei
Befehle in Gate 6 wurde in dieser Review eigenständig gegen den exakt
committeten Stand ausgeführt (siehe Frage 1) — mit demselben Ergebnis, das
der Bericht für den CI-Lauf erwartet.

## Frage 4: Die vier Quadranten-Indexseiten gegen den Stil

Alle fünf neuen Markdown-Dateien (Landing-Page + vier Quadranten) geprüft:
genau eine H1 je Seite, Sentence-Case durchgehend (`# How-to guides`, nicht
`# How-To Guides`), ein Satz je Zeile ausnahmslos eingehalten (auch in den
Grid-Karten, wo „Start here." und der folgende Satz korrekt auf zwei
Zeilen stehen), amerikanisches Englisch bestätigt (gezielt nach
britischen Schreibweisen gesucht — `colour`, `centre`, `organise`,
`licence`, `behaviour` etc. — keine gefunden). Keine Admonition in den fünf
Dateien, also auch keine Überbenutzung. Jede der vier Quadranten-Seiten
trägt bislang nur eine Zwecksatz-Beschreibung ohne Inhalt (absichtlich,
siehe „Nicht Gegenstand") — innerhalb dieses engen Rahmens mischt keine
von ihnen den Quadranten: Tutorials-Satz ist handlungsorientiert ohne
Erklärung, How-to-Satz ist problemorientiert, Reference-Satz ist
Lookup-orientiert, Explanation-Satz ist „Understand why …" im vom Skill
empfohlenen Muster. Die Landing-Page selbst ist korrekt als Landing-Page
behandelt (Cards/Grids laut Skill-Abschnitt 4 „reserve for landing pages",
exakt hier verwendet, nirgends im Fließtext von Body-Seiten).

## Neue Befunde

- `.vale.ini:1` (Geltungsbereich-Konfiguration, zusammen mit
  `docs/Makefile:30-32`): **Mittel.** Vale prüft keinen Text innerhalb
  einer MyST-Direktiven-Fence (` ```{note} `, ` ```{grid-item-card} `,
  Tabs, Codeblöcke …) — nachgewiesen am laufenden Beispiel
  `docs/index.md:42`, dessen „does not cover" innerhalb der
  `{grid-item-card}`-Fence unbeanstandet bleibt, während derselbe
  Ausdruck außerhalb einer Fence (`docs/explanation/index.md:3`) korrekt
  zu „doesn't" korrigiert wurde. Heute folgenlos (kein Stilverstoß
  betroffen), aber die kommenden sieben Aufgaben sollten wissen, dass
  Admonitions und Karten vom Stil-Tor nicht erfasst werden.

Keine weiteren Befunde. Insbesondere: keine losgelöste Abhängigkeit, kein
`# type: ignore`, keine Kontraktabschwächung, keine falsche Zahl neben den
bereits geprüften, keine zweite H1, kein Quadranten-Mix, keine britische
Schreibweise, kein Sicherheitsproblem im Workflow.

## Bereinigung

`/tmp/previously-gate-test` entfernt (`git worktree remove --force`),
`docs/_build/` im Prüf-Worktree nach jedem Lauf gelöscht. Arbeitsbaum,
Index und HEAD des geprüften Worktrees unverändert (einzige neue Datei:
dieser Bericht).

Pfad dieses Berichts:
`.superpowers/sdd/2026-10-03-dokumentation/task-1-review.md`
