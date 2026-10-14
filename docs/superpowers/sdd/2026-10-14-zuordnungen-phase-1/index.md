# Ausführungsprotokoll: Zuordnungen, Phase 1, 2026-10-14

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-15.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-14-zuordnungen-phase-1](../../plans/2026-10-14-zuordnungen-phase-1.md)
ausgeführt wurde, subagent-driven, wie der Betreuer es am 2026-10-14 bestimmt
hat:

- `context.md`: der gemeinsame Kontext aller Aufträge — die Entscheidungen des
  Plans, die Global Constraints, der Review Focus.
- `code-facts.md`: die vor dem Plan gemessenen Fakten aus dem Code, Stand
  `4aeb187`.
- `task-*-brief.md`: die sieben Aufträge; `task-*-report.md`: die Berichte der
  Umsetzer, mit angehängten Fixrunden.
- `task-*-review.md` und `task-*-rereview.md`: die Prüfungen je Aufgabe und
  die Nachprüfungen ihrer einen Fixrunde.
- `final-review.md`: die Endprüfung über den ganzen Zweig, am Ende mit dem
  Bericht der einen Fixwelle; `final-rereview.md`: deren Nachprüfung.
- `measurements.md`: die Messung bei 2 000, 10 000 und 100 000 Beziehungen und
  über `part_of`-Ketten, auf einem i7-11370H; welche Zahl auf welchem Stand
  gemessen wurde, steht dort.
- [`progress.md`](progress.md): das Hauptbuch mit jeder Entscheidung unter
  `Ruling` — `P-1`, `P-2` aus der Vorprüfung, `T2-a` bis `T7-a` aus den
  Aufgaben, `F-a` bis `F-d` aus der Endprüfung.

## Warum das hier liegt

Der Baum zitiert sechs Entscheidungen dieser Ausführung, jede als
`ruling <label> of the 2026-10-14 assignments plan`: `T2-b`, `T2-c`, `T4-e`,
`T6-a`, `T6-c` und `F-b`. Jede löst in `progress.md` genau einmal zu der
Entscheidung auf, die sie nennt (`grep -cE '^Ruling <label>[: ]'`, gemessen am
2026-10-15 auf `992029c`). Die Bezeichner gibt es nur in dieser Ausführung;
`T2-b` eines anderen Plans ist eine andere Entscheidung.

## Was der Ablauf mitbrachte

- **Zwei Unterbrechungen:** ein Neustart des Rechners in der Nacht auf den
  2026-10-15 und ein Neustart des Editors am selben Morgen hielten die
  Endprüfung, die Messung und die Fixwelle an. Was sie geschrieben hatten,
  blieb; das Hauptbuch hält fest, was wo stand und wie fortgesetzt wurde.
- **Eine Messung auf einem bewegten Baum:** der erste Lauf bei 100 000
  Beziehungen lief gegen den Worktree, den die Fixwelle gerade bearbeitete;
  sein MCP-Teil scheiterte daran. Nachgemessen wurde auf einer festen Kopie von
  `9967268`. Lehre für den Controller: eine Messung bekommt von Anfang an einen
  festen Stand, nie den Baum, an dem gleichzeitig gearbeitet wird.
- **Die Prüfungsdiffs** (`review-*.diff`) liegen nicht hier: sie sind aus
  `git` jederzeit neu zu erzeugen und hätten das Verzeichnis um ein Vielfaches
  vergrößert.
