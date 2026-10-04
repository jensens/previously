# Ausführungsprotokoll: Stufe 1b, Projektionen, 2026-10-04

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-04.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-04-stufe-1b-projektionen](../../plans/2026-10-04-stufe-1b-projektionen.md)
ausgeführt wurde: acht Aufgaben, je mit Auftrag und Bericht, ab Aufgabe 5
auch mit den Fixaufträgen und ab Aufgabe 6 mit den Prüfberichten und
Nachprüfungen als eigene Dateien; dazu die Endprüfung des ganzen Zweigs, die
Fixwelle danach mit ihrer Nachprüfung, und das Hauptbuch
[`progress.md`](progress.md) mit jeder Entscheidung, die unterwegs getroffen
werden musste — zu finden unter `Ruling`, von `P-1` bis `E-8`.

## Warum das hier liegt

**Ein** Kommentar im Baum zitiert eine Entscheidung dieser Ausführung:
`ruling P-1 of the 2026-10-04 stage 1b plan`, in `tests/test_cli.py`, zur
Reihenfolge, in der `project` den Weg des Arbeiters meldet. Gemessen am
2026-10-04 mit der Erhebung, die `CLAUDE.md` unter *A ruling citation is
provenance* als Kommandozeile führt:

```
grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests migrations pyproject.toml .importlinter | sort -u
```

Dasselbe Kommando findet dreizehn weitere Labels aus den Ausführungen davor —
und hier liegt ein Befund, den diese Ausführung gemacht hat und der über sie
hinausgeht: **Ruling-Labels werden je Plan vergeben, und nichts im Label sagt,
welcher Plan.** Dieser Plan hat die Labels `T5-b`, `T6-b` und `T8-a` vergeben;
dieselben Labels stehen im Baum für Entscheidungen der 1a-Ausführung, deren
Hauptbuch verloren ist. Von den vierzehn zitierten Labels löst **keines** zu
der Entscheidung auf, die es nennt; zwei (`T5-b`, `T7-a`) finden im Protokoll
vom 2026-10-03 eine Zeile gleichen Namens und dort eine andere Entscheidung.
Deshalb nennt das eine Zitat dieser Ausführung das **Datum** seines Plans, und
`CLAUDE.md` verlangt das seit dem Commit `d4bcb53` für jedes neue Zitat. Das
Hauptbuch hält Messung und Entscheidung unter *Vorbereitung Schlussschritt*
und unter *Fixwelle — Bericht*.

Die Regel bleibt, dass **der Grund im Kommentar steht** und das Label nur die
Herkunft trägt. Lies den Kommentar ohne das Label, und er muss noch tragen.

## Was fehlt, und warum

Die Prüfberichte der Aufgaben 1 bis 5 liegen nicht als eigene Dateien vor.
Sie kamen als Nachrichten an den Controller zurück und stehen als
Befundlisten mit Schweregrad im Hauptbuch; ab Aufgabe 6 wurde jeder
Prüfbericht beim Eintreffen als `task-N-review.md` abgelegt, jede
Nachprüfung als `task-N-re-review-1.md`, jeder Fixauftrag als
`task-N-fix-1-brief.md`. Der Fixauftrag und die Nachprüfung zu Aufgabe 5
wurden aus der Sitzung nachgetragen, als die Regel entstand.

Die `review-*.diff`-Pakete, die jeder Prüfer gelesen hat, liegen nicht hier:
sie sind aus `git diff` zwischen den im Hauptbuch genannten Commits jederzeit
wieder zu erzeugen, und sie würden das Repository um Duplikate wachsen lassen,
die nichts sagen, was die Commits nicht sagen.

Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch — er
konnte es nicht, weil das Hauptbuch vor ihm kopiert wurde. Es ist der erste
Commit auf dem Zweig nach `6e46952`.

## Was diese Ausführung gelehrt hat

Das Hauptbuch hält es im Einzelnen; drei Dinge wiederholen sich darin.

- **Eine Behauptung im Plan ist eine Behauptung im Baum.** Zwei Docstrings
  zitierten Paragraphen des eigenen Specs, weil der Plantext sie so
  vorgab — gegen die eigene Regel des Plans. Eine Komplexitätszahl im Plan
  war zweimal falsch, erst im Plan, dann in der Korrektur. Wer einen Plan
  schreibt, misst, oder er schreibt die Seite hin, die der Umsetzer zitieren
  soll.
- **Ein Tor, das nie feuern kann, ist ein Kommentar.** `ProjectionGap` war
  so geschrieben, dass keine Lücke es auslösen konnte; ein Prüfer hat die
  Lücke gebaut und gemessen. Jede Zusicherung dieser Ausführung hat seither
  ihre Mutation daneben.
- **Getippte Ausgabe altert an Stellen, die kein Tor hält.** Der Block
  `Create the schema` im Tutorial zeigte eine Migration, als es zwei gab, durch
  zwei Aufgaben hindurch. Die Regel „zuletzt neu tippen, aus einem echten
  Lauf" hat ihn gefunden; eine Zahl im Block hätte es nicht. Dasselbe Muster
  in einem datierten Messblock auf `module-boundaries.md`, der zwei
  Gegenwartszahlen trug („40 today", „today's test run"), die ab Aufgabe 2
  falsch waren — die Endprüfung hat sie gemessen.

Und zwei Dinge, die diese Ausführung über ihre eigenen Werkzeuge gelernt hat:

- **Das Tor für `§`-Zitate prüft den Marker, nicht den Spec.**
  `test_no_bare_paragraph_references_remain` lässt jedes `§` durch, das
  „(frozen design record)" trägt — auch dann, wenn der zitierte Spec noch
  nicht eingefroren ist. Zwei Docstrings haben genau das getan, bis die
  Prüfung von Aufgabe 8 sie fand. Welchem Dokument ein `§` gehört, ist nicht
  maschinenlesbar; die Lücke bleibt offen und steht hier.
- **„Eine Transaktion" ist unter READ COMMITTED nicht „ein Zeitpunkt".** Die
  Rückstandszeile las Spitze und Lesezeichen in einer Transaktion und begründete
  das mit einem Zeitpunkt; PostgreSQL gibt dort jeder Anweisung ihren eigenen
  Snapshot. Die Endprüfung hat es gefunden, die Fixwelle liest beide Zahlen in
  einer Anweisung. Dieselbe Denkfigur steht älter in `verify`
  (`storage/postgres.py`) und ist dort nicht angefasst — eine Frage für die
  nächste Stufe.

## Was in die nächste Stufe geht

Spec §10 der Stufe 1b ist eingefroren und trägt nichts mehr auf; das hier
ist die Liste, die der nächste Spec übernimmt, zusätzlich zu den acht Punkten
dort — der äußere Anker zuerst:

- ein Test, dass jeder Unterparser-Name einen Eintrag der Dispatch-Tabelle
  hat (ein vergessener Eintrag wäre heute ein `KeyError`-Traceback);
- eine Obergrenze für `--limit` (`limit + 1` läuft bei `bigint`-Maximum über);
- die Seiten-Reihenfolge der zwei `stderr`-Hinweise in `cli.md` hält nichts
  mechanisch, nur Wortlaut und Code-Reihenfolge;
- welche Isolationsstufe eine Lesezusicherung braucht — für die Rückstandszeile
  beantwortet, für `verify` offen;
- `_quoted_notices` in `tests/test_docs_references.py` läuft bei fehlendem
  Ankersatz in einen `IndexError` statt in eine Assertion, und
  `_message_patterns` nimmt auch die `_describe`-Literale auf.
