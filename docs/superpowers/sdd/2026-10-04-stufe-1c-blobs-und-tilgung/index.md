# Ausführungsprotokoll: Stufe 1c, Blobs, Verschlüsselung, Tilgung, 2026-10-04/05

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-05.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-04-stufe-1c-blobs-und-tilgung](../../plans/2026-10-04-stufe-1c-blobs-und-tilgung.md)
ausgeführt wurde: acht Aufgaben, je mit Auftrag (`task-N-brief.md`), Bericht
und Prüfbericht; die Endprüfung des ganzen Zweigs in zwei Hälften
(`final-review-code.md`, `final-review-docs.md`); die Fixwelle danach in zwei
Teilen mit Auftrag, Bericht und Nachprüfung (`final-fix-*`); die Skripte der
Sitzung von Hand (`handson-steps/`); und das Hauptbuch
[`progress.md`](progress.md) mit jeder Entscheidung, die unterwegs getroffen
werden musste — unter `Ruling`, von `P-1` bis `E-9`.

## Warum das hier liegt

Der Baum zitiert vier Entscheidungen dieser Ausführung, jede mit dem Datum des
Plans, wie `CLAUDE.md` es verlangt: `ruling P-1`, `T5-a`, `T6-a` und `T6-c of
the 2026-10-04 stage 1c plan`. Alle vier lösen in `progress.md` zu der
Entscheidung auf, die sie nennen. Gemessen am 2026-10-05 mit

```
grep -rnioE 'ruling (P|T[0-9]+|E)-[a-z0-9]+' src tests migrations pyproject.toml .importlinter | sort -u
```

und dem Abgleich jeder Fundstelle mit „of the 2026-10-04 stage 1c plan"
gegen das Hauptbuch. Die übrigen Labels, die dasselbe Kommando findet, gehören
älteren Ausführungen.

## Was fehlt, und warum

- **Drei Berichte kamen als Text, nicht als Datei.** Das Werkzeug wies dem
  Umsetzer der Aufgabe 8 das Schreiben seiner Berichtsdatei ab; danach hat der
  Controller den Bericht ausdrücklich als Nachricht verlangt. Der Controller
  hat jeden unverändert abgelegt, mit einem Kopf, der das sagt:
  `task-8-handback.md`, `task-8-fix1-handback.md`, `final-fix-docs-handback.md`.
- **Die Fixrunden der Aufgaben 1 bis 7** stehen als Befundlisten im Hauptbuch;
  die Nachprüfungen dieser Runden kamen als kurze Verdikte zurück und stehen
  dort, nicht als eigene Dateien.
- **Die `*.diff`-Pakete und die Commit-Botschaften** liegen nicht hier: sie
  sind aus `git` zwischen den im Hauptbuch genannten Commits jederzeit wieder
  zu erzeugen.
- **Der Prüftest der Endprüfung zu Critical 1** lag außerhalb des Baums; aus
  ihm sind die Regressionstests in `tests/test_projection_worker.py` und
  `tests/test_cli.py` geworden, gemessen rot ohne die Sperre.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `47d5ebe`.

## Was diese Ausführung gelehrt hat

- **Ein Nebenläufigkeitsfehler sieht in jeder Aufgabenprüfung gesund aus.**
  Dass jedes `redact` die Projektionen nachzieht, kam in Aufgabe 4; dass ein
  geplantes `project` daneben läuft, ist Betrieb. Keine Aufgabenprüfung sah
  beides zugleich. Die Endprüfung des Codes hat den Fall gebaut und gemessen:
  getilgter Text blieb in der Chronik, `redact` meldete Erfolg. Die
  Endprüfung des ganzen Zweigs ist keine Formsache.
- **Eine Lücke, die der Umsetzer selbst findet, gehört nicht in eine Fußnote.**
  Dass `redact units` den Text in der Nutzlast stehen lässt, hat der Umsetzer
  der Aufgabe 8 beim Tippen der Anleitung gemessen. Der Controller entschied,
  es nur auf die Seiten zu schreiben (T8-a); beide Endprüfer verlangten
  unabhängig einen Hinweis des Kommandos selbst (E-3). Wer ein Kommando
  benutzt, liest das Terminal, nicht die Seite.
- **Ein Ablauf, den niemand ausgeführt hat, ist ein Entwurf.** Die Anleitung
  zur Wiederherstellung ließ jede Tilgung wörtlich wiederholen; ids werden
  nach dem Einspielen neu vergeben. Gefunden durch Lesen in der Prüfung der
  Aufgabe 8, bestätigt in der Sitzung von Hand, wo das wörtliche Wiederholen
  nur zufällig abgewiesen wurde.
- **Eine Mutation des Prüfers misst auch den Prüfer.** Bei der zweiten vom
  Endprüfer verlangten Mutation (Zeilensperre weg, Platzhalter bleibt) war
  genau umgekehrt rot und grün, wie er vorhersagte: der Platzhalter reiht den
  Kommandozeilen-Fall schon ein. Die Zusage hält ein anderer Test.

## Was offen bleibt

In der Landkarte, `docs/superpowers/landkarte.md`, wie `CLAUDE.md` es
verlangt — 100 offene Punkte nach dieser Ausführung. Vor dem Merge liegt beim
Betreuer: ob `append --text` den Text weiter in die Nutzlast legt (die Frage
hinter T8-a und E-3).
