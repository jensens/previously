# Ausführungsprotokoll: Auslieferung, 2026-10-05

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-05.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-05-auslieferung](../../plans/2026-10-05-auslieferung.md) ausgeführt
wurde: fünf Aufgaben mit Auftrag, Bericht und Prüfberichten (Aufgabe 2 mit
fünf Fixrunden und drei Angriffs-Prüfungen, `task-2-fix*-review.md`), die
Endprüfung in zwei Hälften (`final-review-code.md`, `final-review-docs.md`),
die Fixwelle mit ihrer Nachprüfung (`final-fix-*`), und das Hauptbuch
[`progress.md`](progress.md) mit jeder Entscheidung — unter `Ruling`, von `P-1`
bis `E-3`.

## Warum das hier liegt

Der Baum zitiert zwei Entscheidungen dieser Ausführung, jede mit dem Datum des
Plans: `ruling T2-j` und `ruling T2-l of the 2026-10-05 delivery plan`, in
`src/previously/storage/postgres.py`, `tests/test_cli.py` und
`tests/test_migrate.py`. Beide lösen in `progress.md` zu der Entscheidung auf,
die sie nennen. Gemessen am 2026-10-05 mit dem Befehl aus `CLAUDE.md`.

## Was fehlt, und warum

- **Die `*.diff`-Pakete und die Commit-Botschaften** liegen nicht hier; `git`
  erzeugt sie aus den Commits, die das Hauptbuch nennt.
- **Die Prüfskripte der Angriffe** auf die Datenbank-URL lagen außerhalb des
  Baums; was sie gemessen haben, steht in den Prüfberichten, und die Formen
  stehen als Tabelle in `tests/test_cli.py`.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `5200508`.

## Was diese Ausführung gelehrt hat

- **Ein Leck stopft man an der Klasse, nicht am Fall.** Das Passwort in
  Fehlermeldungen brauchte fünf Runden, weil drei davon Prüfungen
  nachbesserten, die im Nachhinein rieten, wie ein Parser eine URL zerlegt hat.
  Erst eine Grammatik, die vorher nur zulässt, was sich eindeutig zerlegen
  lässt, schloss die Klasse. Der Betreuer hat daraus eine Arbeitsregel gemacht:
  ein Befund, der nur bei Fehlbedienung auftritt, wird benannt, nicht in einer
  weiteren Runde gejagt.
- **Was im Cluster zuerst läuft, misst man im Cluster-Fall.** Drei Fehler am
  Image zeigte erst ein Lauf unter fremder uid oder in einem kind-Cluster: der
  Smoke-Test scheiterte auf dem Runner (uid 1001) an Rechten, `runAsNonRoot`
  verweigerte einen Benutzernamen statt einer Zahl, und `SIGTERM` an Prozess 1
  wurde ignoriert. Auf dem Rechner des Entwicklers (uid 1000, kein Kubelet)
  war alles grün.
- **Ein Plan, der eine Aktion vorgibt, misst sie besser vorher.** Die Regeln
  `type=semver` für die Image-Tags hätten für `v0.1.0a1` keinen Tag erzeugt;
  das erste Release wäre am Manifest gescheitert, nachdem das Paket schon auf
  PyPI lag. Gefunden hat es der Umsetzer, der die Aktion lokal laufen ließ.

## Was offen bleibt

In der Landkarte, `docs/superpowers/landkarte.md`, 120 offene Punkte nach
dieser Ausführung. Beim Betreuer: ob alle Kommandos die Revision des Schemas
prüfen sollen; ob die Sprachregel in `CLAUDE.md` `scripts/` und das
`Dockerfile` nennen soll.
