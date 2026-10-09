# Ausführungsprotokoll: Pilot-Einheit 3, Gate und Policy, 2026-10-09

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-09.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-09-pilot-gate-und-policy](../../plans/2026-10-09-pilot-gate-und-policy.md)
ausgeführt wurde: sieben Aufgaben mit Auftrag, Bericht und Prüfbericht
(`task-*-brief.md`, `-report.md`, `-review.md`; die Aufgaben 1, 3 und 6 mit
je einer Fixrunde und ihrer Nachprüfung, `task-*-rereview.md`; Aufgabe 7 ohne
eigene Prüfung, ihre Prüfung ist die Doku-Hälfte der Endprüfung), der
gemeinsame Kontext aller Aufträge (`context.md`: die Messungen an den drei
Anbietern, die Global Constraints, die Rulings der Vorprüfung), die
Endprüfung in zwei Hälften (`final-review-code.md`, `final-review-docs.md`),
die Fixwelle (`final-fix-report.md`) mit ihrer Nachprüfung
(`final-rereview.md`), und das Hauptbuch [`progress.md`](progress.md) mit
jeder Entscheidung — unter `Ruling`, von `R-1` bis `R-15`, dazu `T1-a`
(abgelöst durch `T1-b`) und `T2-a`.

## Warum das hier liegt

Der Baum zitiert sechs Entscheidungen dieser Ausführung, jede mit dem Datum
des Plans: `ruling R-5` in `tests/test_decide.py`, `R-6`, `R-9`, `R-11` und
`R-14` in `tests/test_gate.py`, `R-12` in `tests/test_cascade.py`, jeweils
`of the 2026-10-09 gate plan`. Jede löst in `progress.md` genau einmal zu der
Entscheidung auf, die sie nennt (`grep -c '^Ruling <label>[: ]'`, gemessen am
2026-10-09). Die Landkarte und der eingefrorene Spec verweisen auf dieses
Verzeichnis unter dem Kürzel **P-PG**.

Der Befehl für die Zählung der Rulings in `CLAUDE.md` erfasst Bezeichner der
Form `R-<n>` nicht; das steht als offener Punkt in der Landkarte.

## Was fehlt, und warum

- **Die `*.diff`-Pakete** liegen nicht hier; `git` erzeugt sie aus den
  Commits, die das Hauptbuch nennt.
- **Die Proben im Scratchpad** — die Aufrufe an Anthropic, Mistral und
  Ollama vom 2026-10-09 — lagen außerhalb des Baums; was sie gemessen haben,
  steht im Plan und in `context.md`.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `f08ca34`.

## Was diese Ausführung gelehrt hat

- **Ein festes Budget an Zyklen hält.** Der Betreuer verlangte nach der
  vorigen Ausführung, die Zyklen im Griff zu halten. Jede Aufgabe bekam
  höchstens eine Fixrunde und eine Nachprüfung, die Endprüfung eine Fixwelle
  und eine Nachprüfung. Keine Aufgabe brauchte mehr; was danach offen blieb,
  ging mit einem Ruling ins Hauptbuch oder in die Landkarte.
- **Die stillen Fehler fand ein Prüfer auf Opus, nicht die Tests.** Die
  Entscheidung (Aufgabe 3) war nicht monoton — eine zusätzliche Regel konnte
  sie lockerer machen —, und die Hypothesis-Eigenschaft stand grün, weil
  ihre Zufallsbeispiele den Fall nicht trafen; der Prüfer belegte ihn mit
  einem Gegenbeispiel. Die Endprüfung fand die Tilgung während eines
  Anbieteraufrufs, die `verify` mit zwei legitimen Kommandos rot macht.
- **Ein Ruling des Controllers kann selbst der Fehler sein.** `T1-a` verlangte
  den Testblock des Tutorials aus einem Lauf mit `--cov`, unter einem
  Kommando, das die Seite ohne zeigt; die Prüfung von Aufgabe 6 fand den
  Widerspruch, `T1-b` löste ihn ab.
- **Messen vor dem Plan zahlt sich aus.** Drei Aufrufe vor dem Plan zeigten,
  dass Haiku 4.5 `inference_geo` abweist, dass `global` als `global`
  zurückgemeldet wird, und dass das lokale Modell ohne abgeschaltetes Denken
  über zehn Minuten braucht — jedes davon hätte sonst ein Umsetzer finden
  müssen.
