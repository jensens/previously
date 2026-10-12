# Ausführungsprotokoll: Pilot-Einheit 5, Feststellungen, 2026-10-12

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-12.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-12-pilot-feststellungen](../../plans/2026-10-12-pilot-feststellungen.md)
ausgeführt wurde: der gemeinsame Kontext aller Aufträge (`context.md`: die
Entscheidungen des Plans, die Global Constraints, der Review Focus), die vor
dem Plan gemessenen Fakten aus dem Code (`code-facts.md`), die sechs Aufträge
(`task-*-brief.md`), die Mitgabe an Aufgabe 6 (`task-6-carry.md`), die
Prüfberichte der Aufgaben 1 bis 5 (`task-*-review.md`), der Auftrag der
Fixwelle der Endprüfung (`final-fix-brief.md`), und das Hauptbuch
[`progress.md`](progress.md) mit jeder Entscheidung — unter `Ruling`, von
`F-1` bis `F-19`, dazu `P-1` aus der Vorprüfung.

## Warum das hier liegt

Der Baum zitiert elf Entscheidungen dieser Ausführung, jede als
`ruling F-<n> of the 2026-10-12 assertions plan`: `F-3`, `F-5`, `F-6`,
`F-7`, `F-9`, `F-10`, `F-12`, `F-13`, `F-17`, `F-18` und `F-19`. Jede löst in
`progress.md` genau einmal zu der Entscheidung auf, die sie nennt
(`grep -cE '^Ruling <label>[: ]'`, gemessen am 2026-10-12 auf `8e485b6`).
Der Zählbefehl für Rulings in `CLAUDE.md` erfasst die Form `F-<n>` nicht; das
steht als offener Punkt in der Landkarte.

Die Bezeichner `F-<n>` gibt es nur in dieser Ausführung; `R-<n>` gehört den
Plänen vom 2026-10-09 und 2026-10-11.

## Was fehlt, und warum

- **Die Berichte der Umsetzer, die Nachprüfungen, und die beiden Hälften der
  Endprüfung** liegen nicht als Dateien hier. Die Umgebung ließ die
  Untergeordneten in dieser Ausführung meist keine Berichtsdateien schreiben;
  sie gaben ihre Berichte als Nachricht zurück. Was aus ihnen zählt —
  Befunde, Messungen, Mutationen, Abweichungen — hat der Controller ins
  Hauptbuch übernommen, jeweils mit dem Commit, auf den es sich bezieht.
- **Die `*.diff`-Pakete** liegen nicht hier; `git` erzeugt sie aus den
  Commits, die das Hauptbuch nennt.
- **Die Messskripte der Endprüfung** (5 000 Feststellungen) lagen im
  Scratchpad des Controllers, außerhalb des Baums. Ihre Zahlen stehen im
  Hauptbuch und auf `explanation/assertions.md`.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `8e485b6`.

## Was diese Ausführung gelehrt hat

- **Das Budget hielt.** Jede Aufgabe kam mit genau einer Fixrunde und einer
  Nachprüfung aus, die Endprüfung mit einer Fixwelle und einer Nachprüfung.
- **Die Prüfer fanden, was die Tests nicht fragten, und zwar an den
  Sicherheitsgrenzen.** Ein Modell konnte im Kern eine direkte Fassung ohne
  Freigabe schreiben (F-6); eine Vorschau kürzte, was die Bestätigung ganz
  schrieb (F-12); ein vertippter Werkzeugname legte Text ins Zugriffsprotokoll
  (F-13); die Inhaltsfilter verrieten den Zustand eines zurückgehaltenen
  Eintrags; `verify` erkannte eine gefälschte Freigabe mit anderem Inhalt
  nicht. Jedes davon belegte ein Prüfer mit einer Probe gegen die echte
  Datenbank, keines ein Test.
- **Messen vor dem Bauen einer Projektion hat sich gelohnt.** Der Betreuer
  bestätigte den Versuch ohne Projektionstabellen. Die Messung zeigte, dass
  nicht das Falten langsam war, sondern das einzelne Lesen jeder Quelle; ein
  gesammeltes Lesen brachte die gefilterten Listen von 2,8 s auf 0,2 s, ohne
  Tabelle und ohne Migration (F-16).
- **Ein Satz über den Betrieb kam aus dem Code, nicht aus dem Spec.** Dass der
  Schreibweg Quellzeilen sperrt und dafür das UPDATE-Recht auf `event`
  braucht, fand die Doku-Hälfte der Endprüfung; gemessen auf PostgreSQL 18.6.
