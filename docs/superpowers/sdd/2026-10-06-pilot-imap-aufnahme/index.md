# Ausführungsprotokoll: Pilot-Einheit 1, Aufnahme aus IMAP, 2026-10-06

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-06.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-06-pilot-imap-aufnahme](../../plans/2026-10-06-pilot-imap-aufnahme.md)
ausgeführt wurde: sechs Aufgaben mit Auftrag, Bericht und Prüfbericht
(Aufgabe 2 und 5 mit je einer Fixrunde und Nachprüfung, `task-*-rereview.md`;
Aufgabe 6 mit den Übergaben der früheren Aufgaben, `task-6-addendum.md`, und
ohne eigene Prüfung), die Endprüfung in zwei Hälften (`final-review-code.md`,
`final-review-docs.md`), die Fixwelle mit Auftrag, Bericht und Nachprüfung
(`fixwave-*`), und das Hauptbuch [`progress.md`](progress.md) mit jeder
Entscheidung — unter `Ruling`, von `P-1` bis `F-1`.

## Warum das hier liegt

Der Baum zitiert fünf Entscheidungen dieser Ausführung, jede mit dem Datum des
Plans: `ruling T2-b`, `T2-d`, `T2-e`, `T2-f` und `T2-g of the 2026-10-06 pilot
ingest plan`, alle in `tests/test_mail.py`. Jede löst in `progress.md` genau
einmal zu der Entscheidung auf, die sie nennt. Gemessen am 2026-10-06 mit dem
Befehl aus `CLAUDE.md`.

## Was fehlt, und warum

- **Die `*.diff`-Pakete und die Entwürfe der Commit-Botschaften** liegen nicht
  hier; `git` erzeugt die Pakete aus den Commits, die das Hauptbuch nennt.
- **Die Proben der Prüfer und Umsetzer** (erfundene Mails, Speichermessungen,
  die 49-MiB-Mail) lagen außerhalb des Baums; was sie gemessen haben, steht in
  den Berichten.
- Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch: es
  wurde vor ihm kopiert. Er ist der erste nach `3460fc8`.

## Was diese Ausführung gelehrt hat

- **Stiller Verlust zeigt sich nur an gebauter Post.** Die erste Abbildung
  nahm nur den ersten Textteil als Körper, ließ einen leeren `text/plain` den
  HTML-Text verdecken und las Windows-1252 als ISO-8859-1. Alle Tests waren
  grün; gefunden hat es der Prüfer von Aufgabe 2, der Mails baute, wie Apple
  Mail und Outlook sie schicken. Ein Test, der nur die Mails des Plans liest,
  prüft den Plan, nicht die Post.
- **Eine Schätzung des Speichers ohne Grundlast ist keine Messung.** Der
  Umsetzer von Aufgabe 4 nannte „etwa 450 MiB" für eine 50-MB-Mail; der Prüfer
  maß 528 MiB Spitze des Prozesses, das Image 529–531 MiB. 512 MiB im Handoff
  wären knapp gescheitert; jetzt stehen dort 768 MiB.
- **Die Standardbibliothek kann Inhalt in eine Fehlermeldung tragen.**
  `imaplib` von CPython 3.14.3 zitiert bei einem Abbruch mitten in einer Mail
  eine Zeile dieser Mail in seiner Meldung. Gefunden hat es der Test des
  Abbruchs über ein TCP-Relais, nicht das Lesen des Codes.
- **Prüfung nach Gewicht trug.** Sonnet für die Tabelle mit Migration und für
  die Nachprüfungen, Opus für die Aufgaben mit Inhalt; je höchstens eine
  Fixrunde, und Befunde nur aus Fehlbedienung benannt statt gejagt — anders
  als bei der Auslieferung, die eine Aufgabe fünf Runden kostete.

## Was offen bleibt

In der Landkarte, `docs/superpowers/landkarte.md`, 152 offene Punkte nach
dieser Ausführung. Beim Betreuer: ein eigener Mailu-Benutzer für die Aufnahme;
nach dem Merge die Abnahme 11 des Specs lokal gegen seinen echten Ordner; den
Handoff `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` an den
kup6s-Agenten weitergeben.
