# Ausführungsprotokoll: Zuordnungen, Phase 2, 2026-10-15

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-15.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-15-zuordnungen-phase-2](../../plans/2026-10-15-zuordnungen-phase-2.md)
ausgeführt wurde, subagent-driven, wie der Betreuer es am 2026-10-15 dem
Controller überlassen hat („wähle, was hier am besten passt“):

- `context.md`: der gemeinsame Kontext aller Aufträge — die Entscheidungen des
  Plans, die Global Constraints, der Review Focus.
- `code-facts.md`: die vor dem Plan gemessenen Fakten aus dem Code, Stand
  `0bfb228`.
- `task-*-brief.md`: die sechs Aufträge; `task-*-report.md`: die Berichte der
  Umsetzer, mit angehängten Fixrunden.
- `task-*-review.md` und `task-*-rereview.md`: die Prüfungen je Aufgabe und
  die Nachprüfungen ihrer einen Fixrunde. Aufgabe 1 kam ohne Fixrunde durch,
  also ohne Nachprüfung; Aufgabe 6, die Dokumentation, hat keine eigene
  Prüfung, sie ging in die Endprüfung der Doku ein.
- `final-review.md`: die Endprüfung des Codes über den ganzen Zweig, am Ende
  mit dem Bericht der einen Fixwelle; `final-docs-review.md`: die Endprüfung
  der Dokumentation, parallel dazu; `final-rereview.md`: die Nachprüfung der
  Fixwelle.
- `measurements.md`: die Messung bei 10 000 und 100 000 Beziehungen, auf einer
  festen Kopie von `22b3dec`, auf einem i7-11370H.
- [`progress.md`](progress.md): das Hauptbuch mit jeder Entscheidung unter
  `Ruling` — `P-1`, `P-2` aus der Vorprüfung, `T2-a` bis `T5-c` aus den
  Aufgaben, `F-a` und `F-b` aus der Endprüfung.

## Warum das hier liegt

Der Baum zitiert acht Entscheidungen dieser Ausführung, jede als
`ruling <label> of the 2026-10-15 assignments plan`: `T2-a` bis `T2-f`,
`T4-b` und `T5-c`. Jede löst in `progress.md` genau einmal zu der
Entscheidung auf, die sie nennt (`grep -cE '^Ruling <label>[: ]'`, gemessen am
2026-10-15 auf `9ad6eeb`). Die Bezeichner gibt es nur in dieser Ausführung;
`T2-c` dieses Plans und `T2-c` des Plans vom 2026-10-14 sind zwei
verschiedene Entscheidungen, und beide werden aus dem Baum zitiert.

## Was der Ablauf mitbrachte

- **Arten aus dem Vokabular statt aus dem Code:** der Umsetzer von Aufgabe 2
  meldete selbst, dass `members` `part_of` und `concerns` beim Namen liest.
  Das widersprach der Sorge des Betreuers vor inflationär eingebauten Arten;
  `T2-a` ging in die Fixrunde, und `members` liest die Hierarchie und die
  Zuordnungen seither aus dem geltenden Vokabular.
- **Die Messung auf festem Stand:** die Lehre aus Phase 1 galt von Anfang an;
  gemessen wurde auf einer festen Kopie, nicht auf dem Worktree.
- **Zwei Reste geparkt (`F-b`):** die Zeilenzahlen von `cli.py` und
  `server.py` auf der Landkarte und ein Satz auf
  `docs/explanation/module-boundaries.md`, der die Zeiträume der Graph-Tabellen
  verschweigt, bleiben für den nächsten Zweig.
- **Die Prüfungsdiffs** (`review-*.diff`) liegen nicht hier: sie sind aus
  `git` jederzeit neu zu erzeugen und hätten das Verzeichnis um ein Vielfaches
  vergrößert.
