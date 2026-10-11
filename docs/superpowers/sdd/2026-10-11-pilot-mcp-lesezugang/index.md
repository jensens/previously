# Ausführungsprotokoll: Pilot-Einheit 4, MCP-Lesezugang, 2026-10-11

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-11.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-11-pilot-mcp-lesezugang](../../plans/2026-10-11-pilot-mcp-lesezugang.md)
ausgeführt wurde: sechs Aufgaben mit Auftrag, Bericht und Prüfbericht
(`task-*-brief.md`, `-report.md`, `-review.md`; die Aufgaben 2 bis 5 mit je
einer Fixrunde und ihrer Nachprüfung, `task-*-rereview.md` — die Fixrunde
selbst steht am Ende des jeweiligen `-report.md`; Aufgabe 6 ohne eigene
Prüfung, ihre Prüfung ist die Doku-Hälfte der Endprüfung, Ruling R-15), der
gemeinsame Kontext aller Aufträge (`context.md`: was gemessen war, die Global
Constraints, die Entscheidungen des Plans, der Review Focus), die Mitgabe an
Aufgabe 6 (`task-6-carry.md`: die benannten Grenzen und Korrekturen aus den
Aufgaben 1 bis 5), die Endprüfung in zwei Hälften (`final-code-review.md`,
`final-docs-review.md`), die Fixwelle (`final-fix-brief.md`,
`final-fix-report.md`) mit ihrer Nachprüfung (`final-rereview.md`), und das
Hauptbuch [`progress.md`](progress.md) mit jeder Entscheidung — unter
`Ruling`, von `R-1` bis `R-21`.

## Warum das hier liegt

Der Baum zitiert neun Entscheidungen dieser Ausführung, jede als
`ruling R-<n> of the 2026-10-11 MCP read access plan`: `R-5`, `R-6`, `R-8`,
`R-9`, `R-10`, `R-13` und `R-19` in `src/previously/mcp_server/`, dazu `R-16`
und `R-18` in den Tests (`R-8`, `R-9`, `R-13` und `R-19` auch dort). Jede löst
in `progress.md` genau einmal zu der Entscheidung auf, die sie nennt
(`grep -cE '^Ruling <label>[: ]'`, gemessen am 2026-10-11 auf `fb890d9`).
Der Zählbefehl für Rulings in `CLAUDE.md` erfasst Bezeichner der Form
`R-<n>` nicht (offener Punkt in der Landkarte, seit der Ausführung vom
2026-10-09), und manche Zitate brechen über eine Kommentarzeile um, die ein
zeilenweises `grep` nicht zusammensetzt; gezählt wurde darum über den
zusammengefügten Text jeder Datei.

Die Bezeichner `R-<n>` gibt es auch in der Ausführung des Plans vom
2026-10-09 (Gate und Policy); dort heißen die Zitate `of the 2026-10-09 gate
plan`. Ein `R-9` hier und ein `R-9` dort sind zwei Entscheidungen.

## Was fehlt, und warum

- **Die `*.diff`-Pakete** liegen nicht hier; `git` erzeugt sie aus den
  Commits, die das Hauptbuch nennt.
- **Die Proben der Prüfer** im Scratchpad lagen außerhalb des Baums; was sie
  gemessen haben, steht in den Prüfberichten.
- **Die Messungen an Claude Code und Vibe** stehen nicht hier, sondern unter
  `docs/superpowers/recherche/2026-10-10-mcp-messungen.md`.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `fb890d9`.

## Was diese Ausführung gelehrt hat

- **Das Budget hielt wieder.** Jede Aufgabe kam mit höchstens einer Fixrunde
  und einer Nachprüfung aus, die Endprüfung mit einer Fixwelle und einer
  Nachprüfung. Was offen blieb, steht als Ruling im Hauptbuch oder als Punkt
  in der Landkarte.
- **Die Nähte fand erst die Endprüfung.** Jede Aufgabenprüfung war grün, und
  doch zählte `policy gaps` Kreise mit Regel als Lücke (Aufgabe 3 zählte, was
  Aufgabe 5 schrieb), und jeder Aufruf las alle Handlungen, weil jeder Aufruf
  eine neue anhängt — `read_policy` bei 6.000 Einträgen 0,341 s, nach dem
  SQL-Filter 0,010 s.
- **Gegenproben finden, was Tests nicht fragen.** Der Prüfer auf Opus
  dekodierte einen Cursor und fand darin die Uhrzeit einer zurückgehaltenen
  Mail auf die Sekunde (R-13); ein anderer fand, dass der Test „ein Header ist
  keine Identität" ohne Token lief und darum nicht scheitern konnte.
- **Eine Mitgabe des Controllers kann selbst falsch sein.** Die Grenze „eine
  Antwort ohne Eintrag" stand im Spec und in der Mitgabe an Aufgabe 6; der
  Code schreibt den Eintrag vor der Antwort, und die echte Grenze ist die
  umgekehrte (R-21). Die Doku-Prüfung fand es, weil sie gegen den Code las,
  nicht gegen die Mitgabe.
- **Eine Unterdrückung lässt sich oft umgehen.** Der Umsetzer trug für
  `id` im Ressourcen-Template ein `# noqa: A002` ein und dazu eine Zeile in
  `CLAUDE.md`; ein anderer Variablenname machte beides überflüssig (R-11).
