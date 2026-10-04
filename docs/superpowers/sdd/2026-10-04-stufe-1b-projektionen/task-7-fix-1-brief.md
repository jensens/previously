# Task 7 — Fixrunde 1: Auftrag an den Umsetzer (Opus), nach der Prüfung von `773cf4a`

Wörtlich, wie an den Umsetzer geschickt.

---

Fixrunde 1 zu Aufgabe 7. Die Prüfung bestätigt die Arbeit in der Sache — den Warnhinweis gegen `catch_up` geprüft (alle drei Sätze wahr), die `stats`-Auslassung als **Korrektur des Dispatch** anerkannt, die `libpq`-Behauptung unabhängig nachgemessen (über `PQconnectdbParams` mit `expand_dbname`: `PQdb` gibt den ganzen String zurück, `PQhost` fällt auf den Socket), jede Zahl auf `projections.md` und jede README-Behauptung gegen den Baum nachgewiesen, der Titel „How to …" bestätigt, kein Vokabelwort nötig. Nicht freigegeben wegen vier Dingen, alle Einzeiler, dazu zwei Minors.

**I1 — `docs/index.md:24`.** Die How-to-Karte der Startseite zählt „restore a backup, add a migration, check the chain in operation" — drei von vier. Ergänze „rebuild a projection". Die Datei stand nicht auf der Liste, du hast es richtig gemeldet; jetzt schließen.

**I2 — `docs/how-to/rebuild-a-projection.md:39` „Both stand at `1`."** Heute wahr, kein Tor hält es, und der nächste Codeblock der Seite (`version: int = 2`) macht den Satz für jeden ungültig, der dem How-to folgt. Die Fundstellen stehen in `:38`; `:39` wird „Read the current value there."

**I3 — `:17-19`, `:48-50`, `:70-72`: drei `text`-Blöcke sind erfundene Läufe, präsentiert als Ausgabe** („die 12 ist ein frei gewähltes Beispiellog" — dein eigener Bericht). CLAUDE.md: getippte Ausgabe ist eine Messung mit Datum. **Ruling: Prosaform**, wie `verify-the-chain.md` es macht („printed exactly one line: `chain intact`") — nenne die Form in Prosa und zeig für den Wortlaut auf `{ref}`cli-reference``, das `:33` ohnehin tut. Also: der Rückstand erscheint als eine Zeile auf `stderr`, die die Zahl der fehlenden Events nennt und `previously project` empfiehlt; nach dem Versionssprung beginnt die Zeile der Chronik mit `rebuilt: version 1 -> 2` und endet mit Eventzahl und `up_to_id`; nach dem `DELETE` beginnt sie mit `built:`. Und in Prosa löst sich der Nebenbefund gleich mit: `:49` und `:71` zeigten je nur die **erste** von zwei Zeilen (`PROJECTIONS = (CHRONICLE, SOURCE_STATS)`), als Ausgabeblock liest sich das als die ganze Ausgabe. Sag, dass `project` eine Zeile je Projektion druckt und die andere `up to date` meldet. Kein echter Lauf hier: ein gemessener Wegwerf-Log wäre genauso wenig der Log des Lesers, und die Geschwisterseiten kommen ohne aus.

**I4 — `:60`.** `psql postgresql://previously:previously@localhost:5432/previously` sind die Wegwerf-Zugangsdaten des Tutorials in einem Operatorbefehl. Platzhalterform `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`, und der Verweis auf `{ref}`configuration-reference`` in `:66` **ersetzt** die Zugangsdaten statt sie zu ergänzen. Der `libpq`-Satz `:65` bleibt wie er ist — er ist gemessen.

**Minors, in dieselbe Runde:** `:80` „use `source-stats` in place of `chronicle`" ist zweideutig → „in place of `'chronicle'` in the `DELETE`"; `docs/explanation/projections.md:201`: §4.6 sagt ausdrücklich, was verschwindet, sei der **Wortlaut** (`architektur.md:458-459`) — ein Halbsatz, der das als den stärkeren Beleg nennt; „overlooks" darf bleiben.

**Für Aufgabe 8 notiert, nicht für dich:** `README.md:58-70` „The three specifications below are frozen design records" — werden mit dem Einfrieren der 1b-Spec vier. Lass es.

**Danach:** die Doku-Tore gezielt, dann alle sechs Tore einzeln mit **ungekürzten Schlusszeilen** im Bericht. `git status --short` vorher; stagen nur `docs/how-to/rebuild-a-projection.md`, `docs/index.md`, `docs/explanation/projections.md`. Testzahl bleibt 232. Commit „docs: the how-to names the form of the output, not an invented run" mit Trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`. Fixbericht an `task-7-report.md` anhängen; zurück nur Commit-Hash, je Punkt eine Zeile, die sechs Schlusszeilen, jede Stelle, an der du widersprichst.
