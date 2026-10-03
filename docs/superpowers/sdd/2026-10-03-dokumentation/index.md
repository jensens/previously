# Ausführungsprotokoll: Dokumentation, 2026-10-03

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-03.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-03-dokumentation](../../plans/2026-10-03-dokumentation.md) ausgeführt
wurde: acht Aufgaben, je mit Auftrag, Bericht und Prüfung, dazu das Hauptbuch
mit jeder Entscheidung, die unterwegs getroffen werden musste.

Sie liegen im Repository aus **einem** Grund, und der ist nicht Nostalgie.

## Warum das hier liegt

Sechzehn Kommentare in `src/`, `tests/` und `pyproject.toml` zitieren
Entscheidungen aus dieser Ausführung — `ruling T6-b`, `ruling T10-c` und neun
weitere. Bis zu diesem Commit zeigten sie in ein Verzeichnis, das
`.gitignore` ausschließt: das Ziel wurde nicht ausgeliefert, und ein
Ruling-Label war damit schwächer als ein Prüfbefund oder ein eingefrorener
Paragraph, weil es für niemanden nachschlagbar war.

Jetzt löst es auf. Die Rulings stehen in [`progress.md`](progress.md), dem
Hauptbuch; such dort nach `Ruling T6-b`, oder nach `Ruling` für alle.

Die Regel bleibt trotzdem, dass **der Grund im Kommentar steht** und das Label
nur Provenienz trägt — ein Kommentar, der ohne seine Zitierung nicht mehr
trägt, ist ein schlechter Kommentar. Nachzulesen in `CLAUDE.md` unter *A
ruling citation is provenance, never the reason*.

## Was hier liegt

- [`progress.md`](progress.md) — das Hauptbuch, 1332 Zeilen. Die
  Vorab-Durchsicht des Plans, jede Aufgabe mit ihren Messungen, und jede
  Entscheidung als `Ruling <Nummer>: <was> — <warum> — <was es kostet, wenn
  es falsch ist>`. Dies ist der Einstieg.
- [`task-5-must-survive.md`](task-5-must-survive.md) — fünfzehn Begründungen,
  die die Übersetzung ins Englische überleben mussten, je mit Zahl und
  Messung. Das Werkzeug, mit dem ein Prüfer eine verlorene Begründung finden
  konnte; die Abschlussprüfung hat gezeigt, wo seine Grenze lag.
- `task-N-brief.md` — der Auftrag je Aufgabe, aus dem Plan erzeugt und um
  das ergänzt, was der Plan nicht wissen konnte.
- `task-N-report.md` — was der Umsetzer gemessen, gefunden und
  entschieden hat.
- `task-N-review.md`, `task-N-fix-N-report.md`, `final-fix-report.md` — die
  Prüfungen und die Fixrunden.

Die acht Prüf-Diffs der Ausführung sind **nicht** hier: sie waren 1,13 MB
reines `git log` und `git diff -U10` über bekannte Commit-Bereiche und sind
jederzeit neu zu erzeugen.

## Was diese Aufzeichnung wert ist, und was nicht

Sie ist die Antwort auf „warum steht das so im Code" für alles, was zu klein
für eine Doku-Seite war. Sie ist **keine** Dokumentation: nicht lektoriert,
nicht nach Diátaxis sortiert, deutsch, und von keinem Tor geprüft — `conf.py`
schließt `superpowers/**` vom Bau aus, und das vale-Ziel läuft nur über die
vier Quadranten.

Wächst eine Begründung von hier aus über ihren Kommentar hinaus, bekommt sie
eine Seite unter `docs/explanation/` und der Kommentar zeigt dorthin. Dieses
Verzeichnis ist der Ort für das, was dafür zu klein bleibt — nicht die
Warteschlange dafür.
