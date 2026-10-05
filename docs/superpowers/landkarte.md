# Landkarte und offene Punkte

> **Gepflegtes Dokument, nicht eingefroren.** Die Specs unter `specs/` und die
> Protokolle unter `sdd/` halten fest, was an einem Tag entschieden wurde, und
> ändern sich danach nicht mehr. Dieses Dokument ist das Gegenstück: es sagt,
> wo das Projekt **heute** steht, was als Nächstes kommt und wo jeder offene
> Punkt wohnt. Wer einen Spec einfriert, trägt dessen offene Punkte hierher;
> wer einen Punkt schließt, streicht ihn hier und nennt den Commit.
>
> Angelegt am 2026-10-04 mit dem
> [Prüfpunkt nach Teilprojekt 1](sdd/2026-10-04-pruefpunkt-teilprojekt-1/index.md),
> der die Belege zu allem trägt, was hier ohne Begründung steht.

## Wo das Projekt steht

Gebaut und abgenommen, auf `main`:

| Stufe | Inhalt | Spec | Abnahme |
|---|---|---|---|
| 1a | Der Log: `event`, `unit`, `source_key`, Hash-Kette, `append`, `verify` | `specs/2026-10-02-stufe-1a-log.md` | Merge vom 2026-10-03 |
| 1b | Projektionen: Arbeiter, `p_chronicle`, `p_source_stats`, `project`, `chronicle`, `stats` | `specs/2026-10-04-stufe-1b-projektionen.md` | PR #1, `b0396b6` |
| — | Der äußere Anker: `anchor`, `verify --anchors [--exact]`, `examine` in einem Schnappschuss | `specs/2026-10-04-aeusserer-anker.md` | PR #2, `2bc42d4` |
| 1c | Hash-Format v=2 mit Salz; Tilgung von Event, Einheiten und Blob als Event der Art `action`, mit Anordnung und Vollzug in `verify`; Projektionen folgen einer Tilgung; Blobs im Format `age` auf S3, `append --attach`, `blob get`, `verify --blobs`; `redact` | `specs/2026-10-04-stufe-1c-blobs-und-tilgung.md` | PR #5, `d16f3fc` |

Mit Stufe 1c ist Teilprojekt 1 gebaut und abgeschlossen, wie die Architektur
es in §12.1 zuschneidet: Log, Projektionen, Blobs.

Die Auslieferung, die erste Einheit des Piloten, ist auf dem Zweig
`worktree-auslieferung` gebaut; abgenommen ist sie mit dem Merge dieses Zweigs
nach `main`, und nicht vorher:

| Einheit | Inhalt | Spec | Abnahme |
|---|---|---|---|
| Auslieferung | Die Migrationen im Paket und `previously migrate` unter einer Advisory-Sperre; `PREVIOUSLY_DSN` nach einer eigenen Grammatik gelesen; ein Image aus dem Paket auf PyPI, mit Smoke-Test; `release.yml`: Test-PyPI bei jedem Push auf `main`, PyPI und Image für zwei Plattformen bei einem veröffentlichten Release; der Handoff an kup6s | `specs/2026-10-05-auslieferung.md` | der Merge des Zweigs `worktree-auslieferung` nach `main`; Bedingung 8 (Trusted Publishing, der erste Lauf auf `main`, das Release `v0.1.0a1`) folgt ihm, vom Betreuer |

Nicht gebaut: die Suche, jede
Feststellung und jede Entität, der Konnektor-Vertrag über `RawEvent` hinaus,
MCP-Server, Gate, KI-Schicht, jeder Konnektor — und kein Betrieb: mit der
Auslieferung gibt es ein Paket und ein Image, betrieben wird es noch nirgends;
das System hat **noch kein einziges echtes Event** gehalten.

## Was als Nächstes kommt

Der Pilot an einem echten Kunden, jetzt an erster Stelle. Die Reihenfolge
hat der Betreuer am 2026-10-04 entschieden, nach dem Prüfpunkt und der kleinen
Wartungsrunde (ihre vier Punkte stehen unten unter *Erledigt*): erst Stufe 1c,
dann der Pilot. Stufe 1c ist abgenommen (oben); was sie offen lässt, steht
unten unter *Tilgung* und *Blobs und Speicher*, und an den Einheiten, zu denen
es gehört.

Vor die Aufnahme aus IMAP hat der Betreuer am 2026-10-05 die Auslieferung
gestellt: sie hängt an nichts aus der Aufnahme, und kup6s kann mit dem Image
des heutigen Stands Datenbank, Sicherung und Werkzeug-Pod aufbauen, während
die Aufnahme entsteht. Die Aufnahme kommt dann mit dem nächsten
Alpha-Release. Was die Auslieferung offen lässt, steht unten unter
*Auslieferung*.

Der Weg dorthin hatte zwei Umwege, und sie stehen hier, damit die Reihenfolge
nicht wie ein Versehen aussieht: der Prüfpunkt empfahl zuerst den Einwurf mit
eigenen Notizen, weil das System noch kein echtes Event gehalten hatte; der
Betreuer machte daraus den Piloten an einem Kunden; und an echter Kundenpost
wog dann schwerer, was 1c liefert.

### Der Pilot an einem echten Kunden

Der Zuschnitt, den der Prüfpunkt zuerst festhielt — der Einwurf per Prompt,
zuerst eigene Notizen —, ist verworfen: reine Gedankennotizen wären Theorie
und sagten wenig. Stattdessen:

- **Quellen:** ein eigens angelegter IMAP-Ordner und ein Ordner in der
  Nextcloud. Was der Betreuer dorthin kopiert, ist relevant.
- **Ziele, alle vier:** die Chronik des Kunden lesen; die Aufnahme an echter
  Post härten; Claude Code fragt das Log; Protokoll und offene Punkte.
- **Der Weg: Durchstich mit Gate von Anfang an.** Vorschläge kommen aus einer
  eigenen KI-Schicht hinter dem Gate, mit Policy und Audit — nicht aus dem
  Cockpit, das der Betreuer dann abnickt.
- **Datenpolitik des Pilotkunden:** sein Inhalt darf über Claude Code an
  Anthropic gehen („bei diesem Kunden gedeckt", Betreuer, 2026-10-04).
- **Betrieb:** gleich in kup6s, nicht erst lokal.

Die Einheiten, in dieser Reihenfolge; nur die jeweils nächste bekommt einen
Spec:

| # | Einheit | bringt | Spec |
|---|---|---|---|
| 0 | Auslieferung: Migrationen im Paket, `previously migrate`, Image, Release-Weg, Handoff an kup6s | ein Image, aus dem kup6s alles startet | `specs/2026-10-05-auslieferung.md`, eingefroren am 2026-10-05; abgenommen mit dem Merge des Zweigs `worktree-auslieferung` (oben) |
| 1 | Aufnahme aus dem IMAP-Ordner, mit dem Einwurf- und dem Konnektor-Vertrag | Chronik des Kunden; echte Post im Log | ein Entwurf **ruht** auf dem Zweig `worktree-pilot-imap-aufnahme` (Commit `9b493f0`), geschrieben, bevor 1c vorgezogen wurde. Er umgeht 1c an drei Stellen, die sein eigener Kopf nennt — das wegwerfbare Pilot-Log (dort §1.1), der Rohverweis an Stelle der Rohbytes (§2.3), Anhänge ohne Inhalt (§1, §3.4) — und wird neu gefasst, bevor der Pilot anfängt |
| 2 | Betrieb in kup6s: Datenbank mit Sicherung, Restore-Probe, Bucket, Werkzeug-Pod, CronJobs für Aufnahme, Projektion und Anker | Daten, die bleiben | beginnt beim Image aus Einheit 0; gebaut wird er vom Agenten in kup6s, nie von hier. Was er braucht, sagt der Handoff `handoffs/2026-10-05-kup6s-delivery.md`, englisch; er liegt |
| 3 | Gate und Policy: Organisationsprofil des Pilotkunden, ein Anbieter-Adapter, Audit, Offenlegungsprüfung | die Grenze, hinter der ein Modell Inhalt sieht | — |
| 4 | MCP-Lesezugang, mit der Offenlegungsprüfung davor | Claude Code fragt das Log | — |
| 5 | Feststellungen: Schreibweg, Verpflichtung und Entscheidung, Projektionen, Freigabe | was festgestellt ist, mit Quelle und Verantwortung | — |
| 6 | KI-Schicht: Vorschläge hinter dem Gate | Protokoll und offene Punkte | — |
| 7 | Nextcloud-Ordner mit Textextraktion | Dokumente | — |

Für Einheit 2 beantwortet, mit der Auslieferung: kup6s arbeitet mit cdk8s,
ArgoCD und dem CloudNativePG-Operator; das Image kommt von `ghcr.io`; was dort
entsteht, baut der Agent in kup6s nach dem Handoff (Betreuer, 2026-10-05). Der
Zugang vom Arbeitsplatz ist bis zum MCP-Server `kubectl exec` in den
Werkzeug-Pod.

## Was vor was kommen muss

Keine Planung der Teilprojekte — die Architektur nennt das zu Recht Fiktion
(§12.2) —, sondern die Zwänge, die heute schon feststehen. Jede Zeile hat
ihren Beleg im Prüfpunkt.

| Zuerst | dann | weil |
|---|---|---|
| Der Einwurf-Vertrag entscheidet, was mit geändertem Inhalt unter bekanntem Schlüssel geschieht | jeder Konnektor | `append` verwirft ihn heute stumm; wer die Issue-Nummer als `external_id` nimmt, verliert jede Änderung nach der ersten |
| `RawEvent` bekommt Rohbytes und Kanalidentitäten, oder die Architektur gibt sie auf | IMAP, Drop-Ordner | Leitsatz 6: was nicht aufgenommen wurde, ist nicht nachholbar |
| Feststellungen: zweiter Schreibweg, Art und Unterart, Regeln je Art in `verify` | Triage, `record_assertion`, KI-Schicht, Identitätsgraph, jede fachliche Projektion | `append` schreibt nur `observation`; `verify` kennt keine Art-Regeln |
| Blobs mit Verschlüsselung — **gebaut mit Stufe 1c** | Drop-Ordner mit Dateien, IMAP mit Anhängen und Rohmail, Voice | es gab keinen Ort für Bytes |
| Tilgung als Event, die Einheiten und Projektionen mitnimmt — **gebaut mit Stufe 1c** | Inhalte Dritter im Log (Mail, Dokumente) — also der Pilot | ein Grabstein war von einer Fälschung nicht zu unterscheiden, und die Einheiten blieben stehen |
| Ein Betrieb mit Sicherung, Restore-Probe und Anker-Routine — das Image **gebaut mit der Auslieferung**, der Rest beim Agenten in kup6s | Daten, deren Verlust weh tut | bisher gibt es nur Wegwerf-Datenbanken |
| Echte, gemischtsprachige Einheiten im Log | die Messung zur Textsuche und die Wahl des Embedding-Modells | beide verlangen einen Testsatz aus echten gemischten Einheiten (Architektur §11, Nachtrag) |
| Warteschlange (die Sperre auf der Zustandszeile ist gebaut, Commit `3ae7038`) | der erste asynchrone Produzent | ein asynchroner Produzent braucht Entprellung und Wiederholung |
| Das Gate | jeder Modellaufruf | Regel 2 der Architektur: nur `gate` ruft Modelle |
| Prüfung, ob Claude Code MRTR und die Tasks-Erweiterung kann | blockierende Rückfragen und lange Läufe über MCP | Architektur §13 |
| Die Rechtsfrage zur Gesprächsaufzeichnung | Teil 2, Voice | Entwurf §16 |

## Zwei Stücke ohne Teilprojekt

Die Zerlegung in §12 der Architektur hat acht Teilprojekte. Zwei Dinge, die
das MVP braucht, stehen in keinem:

- **Feststellungen und Entitäten.** Teilprojekt 1 heißt „`core` und
  `storage`" und liefert in seinen drei Stufen die Mechanik: Log,
  Projektionen, Blobs. Die Event-Art `assertion`, ihr Schreibweg, die zehn
  Entitäten als Projektionen stehen in keiner Stufe. Die Teilprojekte 5
  (Triage) und 7 (Identitätsgraph) setzen sie voraus.
- **Betrieb.** Die Architektur nennt den Deployment-Mechanismus eine
  Betriebsentscheidung, an der kein Modul hängt (§11). Der Anker hängt daran,
  und `CLAUDE.md` verlangt seit dem 2026-10-04 von jedem Spec eine Aussage zum
  Betrieb. Image, Deployment, Sicherung, Restore-Probe und Anker-Routine waren
  eine Einheit Arbeit, die niemand zugeschnitten hatte; seit dem 2026-10-05
  sind sie zwei Einheiten des Piloten, die Auslieferung (das Image) und der
  Betrieb in kup6s (alles andere), aber weiter in keinem Teilprojekt.

## Offene Punkte, nach ihrem Zuhause

Herkunft in Klammern: **A** Architektur, **E** Entwurf, **1a**/**1b**/**AA**/**1c**
die Stufen-Specs mit Abschnitt, **P-1b**/**P-AA** das `index.md` des
jeweiligen Ausführungsprotokolls, **P-1c** das Ausführungsprotokoll der Stufe
1c (`sdd/2026-10-04-stufe-1c-blobs-und-tilgung/`), **AL** der Spec der
Auslieferung mit Abschnitt, **P-AL** das Ausführungsprotokoll der Auslieferung
(`sdd/2026-10-05-auslieferung/`) mit dem Ruling oder der Aufgabe, **PP** der
Prüfpunkt vom 2026-10-04 mit der Zeile seines Belegberichts.

### Einwurf-Vertrag (`contract`, Teilprojekt 2)

- Geänderter Inhalt unter bekanntem `(source, external_id)` wird stumm
  verworfen; entscheiden: vergleichen und melden, oder die Änderung gehört in
  die `external_id` — und es dann auf eine Seite schreiben (PP, A1 Zeile 8 und
  S7).
- `RawEvent` ohne `raw: bytes` und ohne `channel_identities`, gegen
  Architektur §6.2; ein Grund ist nirgends aufgeschrieben (PP, A1 Zeile 12).
- `RawEvent.payload` steht in keinem Vertrag der Architektur (PP, A1 Zeile
  13). Bis Commit `09c5d81` legte die Kommandozeile den Volltext dort ab, und
  der Text stand dreimal in der Datenbank — Nutzlast, Einheiten,
  `p_chronicle` —; aus 1 GB Text wurden 4,5 GB (PP, Bericht C). Seitdem steht
  der Text eines `append --text` zweimal, in den Einheiten und in
  `p_chronicle`; die Zahl aus Bericht C ist mit der Kopie gemessen und nicht
  neu gemessen. Was ein Konnektor in die Nutzlast legt, bleibt offen.
- Der Nutzlastbereich weist Mail-Header-Schlüssel, Bytes und Gleitkommazahlen
  ab; ein Konnektor muss umformen, bevor er aufnimmt (PP, A1 Zeile 14 und
  Leitsatz 4).
- `--occurred-at` fällt auf „jetzt" zurück, `--evidence` auf `recollection`:
  zwei Vorgabewerte, die als Tatsache in der Kette stehen; und was
  `occurred_at` bei einer Erinnerung meint, die Notiz oder das Ereignis, ist
  nicht entschieden (PP, A1 Zeile 34 und Leitsatz 9).
- Zerlegungsregeln der weiteren Medien (1a §12).
- Interne Abgleichlogik je Konnektor (A §11).
- Der Einwurf per Prompt, der Drop-Ordner mit Textextraktion und OCR, „Quelle
  verlinken" (E §11.4).
- Textextraktion aus Blobs, und damit ihr Inhalt in Einheiten (1c §12 Punkt 8).
- Der Quellschlüssel überlebt jede Tilgung: `source` und `external_id` stehen
  im Event-Hash, und eine Message-ID trägt eine Domain (1c §4.5, §12 Punkt 4).
- Eine Wiedersichtung nach der Tilgung: dass ein getilgtes Event unter seinem
  Schlüssel bekannt bleibt und nicht wieder aufgenommen wird, ist im ruhenden
  Pilot-Spec entworfen; der Hash, an dem er Inhalt wiedererkennt, trüge kein
  Salz (1c §12 Punkt 12).
- Nach einer Wiederherstellung kann ein getilgtes Event, das mit ihr verloren
  ging, neu eingeliefert werden und trägt dann eine neue `id` und einen neuen
  Hash; die Prüfung am Hash weist es zu Recht ab. Die Aufzeichnung einer
  Tilgung führt deshalb den Quellschlüssel (`erase-something.md`,
  `restore-from-a-backup.md`). Kein Kommando findet ein Event an seinem
  Quellschlüssel: `show` druckt ihn nicht, nur `chronicle` neben jeder Einheit,
  die dort eine Zeile hat. Für den Piloten, dessen Aufnahme ein Postfach erneut
  liest (Endprüfung der Doku, Befund 12; P-1c).

### Feststellungen und Entitäten (ohne Teilprojekt)

- Ein zweiter Schreibweg neben `append` für `assertion` und `action`; ihre
  Idempotenz ist heute „Sache des Aufrufers" (PP, A1 S1 und Zeile 19).
- `verify` prüft Regeln je Art erst für `action` (eine Handlung braucht eine
  lesbare Unterart, eine Tilgung genau ihre Form); eine Feststellung ohne
  `sources` und eine Wahrnehmung ohne `evidence` und ohne Schlüssel bestehen
  weiter (PP, A1 S2, Messungen M3 und M4).
- Keine Validierung der Nutzlast gegen ein Schema je Art, gegen Architektur
  §4.1 (PP, A1 Zeile 20).
- `kind` heißt zweierlei: die Event-Art mit drei Werten und die Unterart einer
  Feststellung, die keine Spalte und noch keinen Ort hat; die Unterart einer
  Handlung steht seit Stufe 1c in der Nutzlast unter `action` (PP, A1 S3).
- Wer tilgt: der 1a-Spec nennt für das Tilgungs-Event „Zeitpunkt, Anlass und
  Urheber", es trägt die ersten beiden; das System kennt noch keine Personen
  (1c §12 Punkt 5).
- Verweise einer Feststellung auf Einheiten sind ungeprüftes JSON; ein Event
  ohne Einheiten erscheint in `p_chronicle` gar nicht (PP, A1 S4).
- `p_obligation` passt nicht durch den Projektionsmechanismus, wie die
  Architektur sie zeigt: die Vorrangregel braucht die `responsibility` der
  bisherigen Feststellung, und die Spalte fehlt (PP, A1 S5).
- Zuordnung zu Projekten: `p_chronicle` bekommt `project`, der Index seine
  erste Spalte (1b §10 Punkt 6, AA §10 Punkt 9).
- Fünf der neun Leitsätze (1, 2, 5, 7, 8) hatten noch keinen Kontakt mit Code
  (PP, A1 Frage 4).

### Projektionen

- Eine neue Projektion kostet Methoden im Store-Protokoll, ihre SQL-Umsetzung
  und eine Migration — nicht nur eine Versionsnummer; `write_projection(name,
  rows)` aus der Architektur wurde zu getypten Methoden je Tabelle, ohne
  aufgeschriebenen Grund (PP, A1 Zeile 30 und S5; A2, §10.1).
- Neubau an Ort und Stelle statt Schattentabelle mit Umschaltung; ein Leser
  sieht während des Neubaus eine leere oder halbe Projektion. Architektur §7.3
  Regeln 3 und 4 verlangen das Gegenteil, ein Grund ist nicht aufgeschrieben
  (PP, A2). Gemessen bei 700 000 Events: der Neubau dauert fünf bis sieben
  Minuten, der Eingang läuft dabei weiter, und die Standardausgabe von
  `chronicle` und `stats` sieht in dieser Zeit vollständig aus — `stats`
  zeigt Teilsummen. Der einzige Hinweis ist die Rückstandszeile auf der
  Standardfehlerausgabe, im Wortlaut eines gewöhnlichen Rückstands (PP,
  Bericht C). Zu entscheiden: die Schattentabelle bauen, oder dabei bleiben,
  den Neubau in der Meldung benennen und es auf eine Seite schreiben.
- Jede Projektion liest das ganze Log für sich: 29 % eines Neubaus sind
  doppeltes Lesen, und `source-stats` liest alle Inhalte, um Einheiten zu
  zählen (PP, Bericht C).
- Der Neubau leert mit `DELETE`: bei 700 000 Events bleiben 5,1 Millionen tote
  Zeilen, bis `VACUUM` sie räumt; die Wirkung ist ungemessen (PP, Bericht C).
- Dass der Eingang während eines Neubaus weiterläuft, ist gemessen, aber von
  keinem Test bewacht; die Architektur nennt es als Nachweis für Stufe 1b
  (PP, A2 und Bericht C).
- `Projection.write` könnte sich eine eigene Transaktion nehmen (1b §10, F9);
  `projection_state.version` ohne `CHECK` (F12). Beide vor der dritten
  Projektion zu entscheiden.
- `previously stats` ohne Zeitraum; ein Zeitraum wäre eine neue Projektion
  (1b §10 Punkt 7).
- Die Projektionsnamen stehen zweimal: in `core` und als Abbildung auf die
  Tabelle in `storage` (PP, A2).
- `_catch_up_after` in `cli.py` hört an der ersten Projektion auf, die
  scheitert, und nennt die übrigen nicht: scheitert `chronicle`, wird
  `source-stats` weder nachgezogen noch im Satz genannt. Eine gescheiterte
  Löschung hält das Nachziehen seit Commit `b9b0cdc` nicht mehr auf (P-1c;
  Nachprüfung der Endkorrektur).
- Zwei Releases gegen eine Datenbank bauen eine Projektion gegeneinander neu:
  ein Nachziehen baut neu, sobald die Fassung, die es findet, von seiner
  abweicht, in beide Richtungen. `ProjectionRebuilt` hält einen Lauf an, der
  das zwischen zwei Stapeln bemerkt (Commit `3ae7038`); das Hin und Her über
  Läufe hinweg verhindert nichts. Die Anleitung `rebuild-a-projection.md` sagt,
  den Prozess der anderen Release anzuhalten (Endkorrektur, Teil 2).
- `p_chronicle` hält den Inhalt jeder Einheit ein zweites Mal und ist damit
  größer als die Tabelle `unit`: 1,9 GB gegen 1,4 GB bei 700 000 Events; ihr
  Schreiben ist mit 48 % der größte Posten eines Neubaus (PP, Bericht C).

### Storage-Schnittstelle

- Worauf `core` baut, steht nicht im Protokoll: Isolationsstufe von `begin()`
  und `snapshot()`, die Fehlerklassen `ChainPositionTaken` und
  `SourceKeyTaken` aus `previously.storage.errors`, und dass `LogStore` und
  `ProjectionStore` eine Verbindung teilen (PP, A2 Frage 2).
- Drei der fünf Eigenschaften aus Architektur §5 gelten nicht mehr oder nur
  für `LogStore`, und keine Seite begründet eine der fünf (PP, A2;
  `design-records.md`).
- Vier Lesemethoden außerhalb jedes Protokolls, heute nur von `cli` benutzt;
  ein zweiter Einstieg braucht sie (PP, A2).
- `stream(project=…)` aus der Architektur kam nicht; der 1a-Spec schob es nach
  1b, der 1b-Spec nennt es nicht (PP, A2).
- Der Docstring von `SourceKeyTaken` sagt „Do not retry", `append` wiederholt
  im Teilfall (PP, A2).
- `show` liest Event und Einheiten in zwei Anweisungen; die Begründung im
  Kommentar gilt nur, solange nichts ein Event nach dem Commit umschreibt
  (P-AA).

### Tilgung

- Aufnehmen und Tilgen zugleich: sieht ein `append --attach`, dass ein Blob
  schon liegt, und tilgt ein `redact` in diesem Augenblick dessen letzte
  Referenz, zeigt das neue Event auf ein Objekt, das fehlt. `verify --blobs`
  meldet es, `concurrency.md` benennt es, verhindert wird es nicht (1c §12
  Punkt 2; P-1c).
- Die Weigerung „is a redaction" trifft jedes Event der Art `action`; heute
  ist jede Handlung eine Tilgung, mit der zweiten Art von Handlung ist der
  Satz falsch (`core/redact.py`, der Kommentar daneben sagt es; P-1c).
- `redact_event` nimmt die Blobs eines Events nur aus dem Register. An einem
  beschädigten Register, das `verify` meldet, nennt und löscht die Tilgung
  einen Blob nicht, den nur die Nutzlast nennt. Mit der Nutzlast vereinigen
  oder die Tilgung abweisen — nicht entschieden (ruling E-6 der
  Endkorrektur).
- Ein Schlüssel je Betroffenem und das Krypto-Schreddern (1c §12 Punkt 6).
- Das Ziel von `redact event` und `redact units` ist eine `id`, und eine `id`
  überlebt keine Wiederherstellung: sie vergibt jede `id` über ihrer Spitze
  neu (`id` = Spitze + 1). Eine Tilgung, nach einer Wiederherstellung wörtlich
  wiederholt, kann ein anderes Event treffen. Die Anleitung
  `restore-from-a-backup.md` lässt den Leser das Ziel am `hash` bestätigen,
  den er bei der Tilgung notiert hat; ob `redact` selbst sein Ziel gegen
  etwas prüfen soll, das eine Wiederherstellung überlebt — den `hash` des
  Events —, ist nicht entschieden (Prüfung der Aufgabe 8, P-1c). Die
  Codeprüfung der Endprüfung schlägt eine Option `--hash` an `redact event`
  und `redact units` vor, gegen die gesperrte Zeile geprüft, bevor etwas
  geschrieben wird — empfohlen vor dem Piloten.

### Blobs und Speicher

- Verwaiste Blobs: scheitert das Anfügen nach dem Speichern, bleibt ein Blob
  ohne Event; ihn zu finden heißt, den Bucket gegen `event_blob` zu halten,
  gebaut ist das nicht (1c §12 Punkt 1).
- Hochladen ohne Zwischendatei; heute braucht das Aufnehmen Platz in der
  Größe des größten Blobs (1c §2.3, §12 Punkt 10).
- Bedingtes Schreiben (`If-None-Match: *`) machte aus „erster gewinnt" ein
  Schloss statt eines Nachsehens; dafür müsste das Hochladen in Teilen von
  Hand gebaut und an Hetzner gemessen werden (1c §2.7, §12 Punkt 13).
- Ein beschädigtes Objekt ersetzen: „erster gewinnt" lässt es liegen, ein
  Kommando, das einen Inhalt bewusst neu ablegt, gibt es nicht (1c §2.7, §12
  Punkt 14).
- `pyrage` 1.4.0 kehrt beim Versiegeln eines kleinen Inhalts normal zurück,
  wenn der eine Schreibzugriff der Senke scheitert (gemessen am 2026-10-05,
  12 Bytes; bei größerem Inhalt wirft es). Im Baum umgangen, `core/sealing.py`
  beobachtet Quelle und Senke selbst; dem Projekt `pyrage` nicht gemeldet
  (P-1c).
- `s3transfer` hält den Fehler eines abgewiesenen Hochladens in Zyklen, samt
  der Verbindung. Im Baum umgangen, `put` in `storage/s3.py` wirft den
  eigenen Fehler unverkettet; nicht gemeldet (P-1c).
- Die Lesefrist des S3-Clients, 20 s (`_READ_TIMEOUT` in `storage/s3.py`), ist
  gegen keinen langsamen echten Speicher erprobt, auch nicht der Fall, dass
  die Antwort auf einen Teil eines Hochladens länger braucht (P-1c).

### Suche

- Textsuchvariante: Messversuch mit gemischtsprachigen Einheiten (A §11 und
  Nachtrag; E §12.3, §16).
- Embedding-Modell und Dimension, mit einem Testsatz aus echten gemischten
  Einheiten; die Architektur weist es Teilprojekt 1 zu, keine Stufe trägt es
  (A §11; PP, A2).
- `pg_dict` mit Hunspell; Versionsstände der Erweiterungen; Tokenizer-Weg
  (A §13, E §16). Die erste Migration richtet keine Erweiterung ein.
- `p_unit_search` teilt den Primärschlüssel mit `p_chronicle` (1b §1).

### Warteschlange (mit dem ersten asynchronen Produzenten)

- Tabelle `job`, Entprellung, Wiederholung, `SKIP LOCKED` (A §7.1; 1b §10
  Punkt 4).

### Auslieferung (Paket, Image, Release)

- Signaturen und Herkunftsnachweise (Sigstore/cosign, SLSA-Provenance, SBOM)
  für Paket und Image. PyPI erzeugt mit Trusted Publishing schon
  Attestierungen für das Paket; für das Image ist nichts vorgesehen (AL §12
  Punkt 1).
- Das Image installiert aus PyPI; scheitert sein Smoke-Test, ist die Version
  auf PyPI schon sichtbar und kommt nie wieder. Ein Image aus dem gebauten
  Wheel des Laufs wäre die Alternative, mit dem Preis, dass es nicht beweist,
  dass das Paket auf PyPI installierbar ist (AL §5, §12 Punkt 2;
  `delivery.md`).
- Der Name `previously` auf PyPI ist erst belegt, wenn das erste Release
  veröffentlicht ist (AL §12 Punkt 6). Mit ihm steht Bedingung 8 der Abnahme
  aus, nach dem Merge vom Betreuer: der erste Lauf auf `main` legt eine
  Entwicklungsversion auf Test-PyPI, das Release `v0.1.0a1` Paket und Image
  für beide Plattformen, und das Paket auf `ghcr.io` wird einmal öffentlich
  gestellt. Den Probelauf vor dem Merge, den AL §10 Punkt 7 vorsah, gibt es
  nicht: GitHub startet einen Workflow von Hand nur aus einer Datei auf dem
  Standardzweig; `cut-a-release.md` sagt es (Plan, Entscheidung 1).
- Nichts prüft, dass die gebaute Version dem Tag gleicht. Ein Tag mit
  führender Null (`v1.02.3`) besteht die Tag-Prüfung und endet mit einer
  Version auf PyPI ohne Image; zwei Tags auf einem Commit (rc und final)
  scheitern sicher, gemessen. Eine Zeile in `build`, die das Wheel unter dem
  Namen des Tags sucht, finge jede solche Klasse vor dem Hochladen ab;
  Entscheidung des Betreuers (P-AL, Prüfung der Aufgabe 4; benannt in
  `cut-a-release.md` und im Kommentar von `release.yml`).
- Ein stabiles Release einer älteren Linie, nach einem neueren
  veröffentlicht, setzt `latest` auf sich zurück: `enable` liest nur die
  Markierung als Vorabversion (P-AL, Prüfung der Aufgabe 4; `delivery.md`,
  `cut-a-release.md`). Folgenlos, solange es keine Wartungslinie gibt.
- Der Warteschritt in `image` fragt die JSON-Schnittstelle von PyPI, das
  Image installiert aus dem einfachen Index; hinkt der zweite nach, scheitert
  der Bau nach PyPI, und „Re-run failed jobs" ist die Abhilfe (P-AL, Prüfung
  der Aufgabe 4; `cut-a-release.md`).
- Eine Vorabversion bekommt nur den Image-Tag `<version>`, kein
  `<major>.<minor>`, anders als AL §3.2 Punkt 6: `docker/metadata-action`
  verlängert eine Vorabversion nur zur genauen Fassung (ruling T4-a; P-AL).
  Hingenommen, kup6s pinnt die genaue Version; bis `1.0.0` hat jedes Image
  genau einen Tag.
- Vier Kommentare in `release.yml` stimmen nicht ganz: Zeile 8 zeichnet
  `gates -> tag -> build`, `tag` läuft neben `gates`; Zeile 34 „none cancelled
  by a newer one" gilt nur für einen laufenden Lauf; Zeile 40 „widen" statt
  „replace"; Zeilen 83–85 nennen `0.1.0a2.dev3` als Version auf `main`, vor
  dem ersten Tag ist es `0.1.devN` (gemessen `0.1.dev178`). Vorgesehen für die
  Fixwelle nach der Endprüfung (P-AL, Prüfung der Aufgabe 4).
- `scripts/smoke-image.sh`: `trap` steht nach `mktemp`; dass das Skript `uv`
  und `openssl` auf dem Wirt braucht, steht in `run-the-image.md`, nicht im
  Kopf des Skripts; ein Abbruch kann einen `--rm`-Container und das Netz
  zurücklassen; `useradd --system` mit uid 1000 warnt harmlos beim Bau (P-AL,
  Prüfung der Aufgabe 3).
- Die Etiketten `org.opencontainers.image.title`, `description`, `url` und
  `revision` erbt das Image vom Basis-Image `uv` und beschreibt damit `uv`,
  nicht Previously; `source`, `licenses` und `version` setzt das `Dockerfile`
  selbst (gemessen mit `docker image inspect` am 2026-10-05, Aufgabe 5; im
  Handoff benannt).

### Betrieb (ohne Teilprojekt)

- Deployment-Mechanismus und Datenbank mit Sicherung baut der Agent in kup6s
  nach dem Handoff (das Image ist gebaut, unten unter *Erledigt*); offen,
  welche pgBackRest-Plugin-Implementierung (A §11, §13;
  `backup-encryption.md`).
- Ablageort und Intervall der Anker; benannter Restore-Point im Takt des
  Ankerns (AA §10 Punkt 4). Wo die Ankerdatei im Cluster liegt, entscheidet
  der Betrieb, die Bedingungen stehen in `verify-the-chain.md`; ob Previously
  sie selbst irgendwohin veröffentlichen soll, ist offen (AL §12 Punkt 4).
- `previously migrate` geht nur vorwärts; ein Zurück im Betrieb ist eine
  Wiederherstellung, kein Kommando (AL §12 Punkt 3; `delivery.md`).
- Der Container-Weg der Anker-Routine ist für `kubectl exec` ungemessen
  (P-AA).
- Der Bucket der Blobs bei Hetzner, ohne Versionierung und ohne Object Lock,
  mit eigenen Zugangsdaten; die Identität über External Secrets als
  Verzeichnis eingehängt (1c §7). Was bei Hetzner anders ist als beim
  Testserver, hat seit der Ausführung Namen: ob der Speicher das Metadatum
  `key-id` so zurückgibt; was ein Leser sieht, während ein Objekt ersetzt
  wird (bei RustFS bricht sein Lesen ab); ob ein bedingtes Schreiben
  angenommen wird; ob Löschen ohne Version und ohne Löschmarke löscht (1c §12
  Punkt 11; P-1c). Nichts prüft, dass der Bucket ohne Versionierung und ohne
  Objektsperre ist; ein Bucket mit einem von beiden behält getilgte Blobs, und
  `verify --blobs` sieht es nicht, könnte es aber melden (Endprüfung der Doku,
  Befund 5).
- Ein Tresor hinter der Schlüssel-Naht; heute ein Verzeichnis mit einer Datei
  je Empfänger (1c §12 Punkt 7).
- Keine Seite sagt einem Betreiber, der von Stufe 1b kommt, was mit seinen
  Events im Format 1 ist: kein Salz, Einheiten nur zusammen tilgbar
  (Endprüfung der Doku, als Lücke des Projekts zurückgestellt). Dass er die
  Datenbank migrieren muss, sagen seit der Auslieferung `run-the-image.md`
  und die Release-Notes für Betreiber, die `cut-a-release.md` verlangt — mit
  `previously migrate` statt `alembic upgrade head`.
- Die Aufbewahrungsfrist der Sicherungen ist Teil der Tilgungszusage: die der
  Datenbank und des WAL-Archivs, und die der Sicherungen oder Kopien des
  Buckets, wenn es sie gibt (1c §4.5, §7; P-1c). Steht auf `erasure.md`,
  `blobs.md` und `backup-encryption.md`; gewählt ist keine Frist.
- Ein Verzeichnis der Tilgungen außerhalb der Datenbank: nach einer
  Wiederherstellung auf einen älteren Stand weiß das Log nicht mehr, was
  seither getilgt wurde, und die Tilgungen sind zu wiederholen; die Anker-Datei
  wäre ein Muster (1c §4.5, §12 Punkt 3). Die Anleitung
  `restore-from-a-backup.md` verlangt es, gebaut ist nichts.
- Der Notfallweg mit dem Werkzeug `age`: am 2026-10-05 in einem Container mit
  `age` 1.2.1 gegangen, ein Objekt mit der AWS-Kommandozeile geholt und mit
  der Identität allein geöffnet (Aufgabe 8, P-1c); von Hand, mit installiertem
  Werkzeug, steht er für die Abnahme aus (1c §11 Bedingung 14).
- „Kettenprüfung schlägt an → alles Schreiben anhalten" (A §7.4) ist nicht
  gebaut; es gibt nur den Alarm. Kein Grund aufgeschrieben (PP, A2).
- Zwei gleichzeitig laufende Anker-Routinen hängen beide an; folgenlos, aber
  ohne Sperre (P-AA).
- GitHub schaltet geplante Workflows in einem öffentlichen Repository nach 60
  Tagen ohne Aktivität ab; die wöchentliche Prüfung mit `pip-audit` kann dann
  still aufhören (Prüfung der Wartungsrunde, 2026-10-04).
- Die Renovate-App ist auf dem Repository noch nicht installiert; ohne sie tut
  `renovate.json5` nichts. Validiert ist die Konfiguration mit Renovate
  42.99.0, nicht mit der aktuellen Hauptversion, und ob Renovate den
  Versionskommentar neben einem gepinnten Action-Commit mitzieht, steht nicht
  in seiner Dokumentation — am ersten solchen Pull-Request nachsehen (Prüfung
  der Wartungsrunde, 2026-10-04).

### Kette und Anker

- Die Signatur des Schreibers: nur sie schließt gefälschtes Anhängen außerhalb
  eines Moments der Ruhe (AA §10 Punkt 1).
- Ein beglaubigtes „wann" über den Ablageort hinaus (AA §10 Punkt 3).
- Die Kettenprüfung geht bei jedem Lauf das ganze Log ab und hält ihren
  Schnappschuss so lange offen: gemessen 13 s je 100 000 Events, hochgerechnet
  rund elf Minuten bei fünf Millionen — bei jedem Lauf der Anker-Routine. Eine
  Prüfung, die beim jüngsten Anker beginnt, gibt es nicht; und ein so lange
  offener Schnappschuss hält `VACUUM` zurück, was niemand gemessen hat (PP,
  Bericht C).
- `verify --blobs` liest alles: eine Prüfung nur der Blobs seit dem letzten
  Lauf gibt es nicht (1c §12 Punkt 9); und es hält die Referenzen aller Blobs
  im Speicher des Prozesses, im Docstring gesagt, nicht gemessen (P-1c).
- In v=1 ist an einem ganz getilgten Event nichts mehr über seine Einheiten
  bezeugt: Zahl und `seq` der Grabstein-Zeilen prüft nichts. In v=2 fällt
  beides auf. Steht auf `erasure.md`, festgenagelt von
  `test_the_tombstone_rows_of_a_fully_erased_version_1_event_are_attested_by_nothing`
  in `tests/test_verify.py`; wer die Grenze schließt, dreht den Test bewusst
  um (P-1c).
- `previously anchor` allein prüft keine alten Anker (P-AA).
- Ein Befund nennt die `id`, nicht die Zeile der Ankerdatei (P-AA).
- `anchored event is missing (the log ends at 5)` für ein Event aus der Mitte
  liest sich wie ein Widerspruch (P-AA).
- Externer Compliance-Anlass: die Annahme „nicht zertifizierungsgetrieben" ist
  unbestätigt, und der Anker hat Teile eines Drittbelegs vorweggenommen
  (E §16; PP, A2).

### Kommandozeile

- Eine unerwartete Ausnahme endet mit Rückgabecode 1, dem Code eines Befunds
  (P-AA).
- `show` druckt Einheiten roh; eine Einheit mit Umbruch bricht die
  Zeilenstruktur (1b §10 Punkt 3).
- Eine Obergrenze für `--limit` (P-1b).
- `N blobs match` zählt getilgte, zu Recht fehlende Blobs mit (Endprüfung,
  ruling E-6 der Endkorrektur).
- Die Hilfe von `verify --blobs` sagt „also read every blob in the store and
  check it"; gelesen wird jeder Blob, den das Register nennt und der liegen
  muss, nach einem getilgten wird nur gefragt (Endkorrektur, Teil 2).
- Die Kommandozeile ist mit elf Kommandos, Ausgabeverträgen und Rückgabecodes
  faktisch eine Oberfläche mit Vertrag geworden, obwohl sie nur der Einstieg
  ist, bis der MCP-Server steht (PP, A2 §11 Zeile 8).
- `PREVIOUSLY_DSN` wird nach einer Grammatik gelesen (ruling T2-k), die einen
  Text nur auf eine Weise liest, nicht immer so, wie er gemeint war. Eine
  vertippte Zeichenkette, die passt, kann ein Stück Passwort in eine Meldung
  bringen: ein Passwort aus höchstens fünf Ziffern bei vergessenem `@host`
  (`user:12345/db`) als Port (ruling T2-j), dieselbe Form ohne Datenbank als
  Datenbank, ein rohes `@` im Passwort bei vergessenem `@host` als Host, ein
  Passwort als Wert von `sslmode`, `require_auth`, `channel_binding`, gegen
  einen Server mit TLS auch von `sslrootcert` und `sslkey`, im Grund von
  libpq, ein Passwort als Benutzer oder als Datenbank (ruling T2-m). Kein
  Parser unterscheidet `user:12345` von `host:12345`. Benannt als Tabelle auf
  `configuration.md` und im Docstring von `_url_of`; gejagt wird es nicht
  (Arbeitsregel des Betreuers vom 2026-10-05: Fehlbedienung wird benannt).
  `alembic` im Checkout liest die Zeichenkette mit SQLAlchemy, nicht mit der
  Grammatik (P-AL).
- Der Docstring von `_unreadable` in `storage/postgres.py` sagt „every part
  takes the escape"; Host, Port und Schema nehmen keine (P-AL, Nachprüfung der
  Fixrunde 5 der Aufgabe 2).
- `alembic` zu importieren kostet jedes Kommando rund 70 ms, nicht nur
  `migrate` (ruling T2-e; P-AL, gemessen vom Prüfer).
- Ein Datenbankfehler beim COMMIT von `migrate`, der weder eine aufgeschobene
  Prüfung noch ein `OperationalError` ist, entginge `_refusals` und endete
  als Traceback; in PostgreSQL ist keiner bekannt (P-AL, Fixrunde 5 der
  Aufgabe 2).

### Tore und Werkzeuge

- Drei geparkte Testlöcher am Doku-Tor (1b §10 Punkt 5).
- Die Reihenfolge der zwei `stderr`-Hinweise in `cli.md` hält nichts
  mechanisch; `_message_patterns` nimmt auch die `_describe`-Literale auf
  (P-1b).
- Das Tor für `§`-Zitate prüft den Marker, nicht, ob der zitierte Spec
  eingefroren ist (P-1b).
- Die Reinheit von `parse_anchors` und `format_anchor` hat Tests, aber keine
  gemessene Mutation (P-AA).
- `ruling`-Labels im Baum lösen nicht auf; das Hauptbuch der Stufe 1a ist
  verloren (`CLAUDE.md`).
- Der Testlauf ist mit Stufe 1c von rund 31 s auf 87 s gewachsen (`632 passed in 86.80s`, gemessen am 2026-10-05 nach der Endkorrektur): ein
  zweiter Container, und Tests, die wirklich hochladen (P-1c).
- Die neun Befunde der Kette selbst stehen seit der Endkorrektur in `cli.md`,
  aber `tests/test_docs_references.py` hält nur die Blöcke, die es mit ihrem
  Einleitungssatz kennt, und zählt dreizehn; den neuen Block hält kein Test.
  Am 2026-10-05 mit den Helfern des Tests per Skript geprüft, alle sieben
  Zeilen stimmen. Ihn aufzunehmen ist eine Änderung an `tests/` (Endkorrektur,
  Teil 2).
- Der Zitat-Test in `tests/test_docs_references.py` lässt hinter einem
  eingesetzten Wert am Satzende beliebigen Text zu; eine Verschärfung auf
  „kein Leerzeichen im eingesetzten Ende" bräche an Sätzen, die mit einem
  Grund enden (P-1c).
- Drei Tests laufen nur unter Linux und werden sonst übersprungen
  (`ru_maxrss`, `/proc`); zwei senken für die Dauer eines Kommandos die
  Dateigrößengrenze des Testprozesses (P-1c).
- Der Test zum abgebrochenen Lesen verlässt sich darauf, dass RustFS das
  Senden einstellt, wenn das Objekt gelöscht wird; an den ersten CI-Läufen
  beobachten (P-1c).
- import-linter liest `src/previously/migrations/versions/` nicht: das
  Verzeichnis hat kein `__init__.py`, und die Dateinamen der Revisionen
  beginnen mit Ziffern, sind also keine importierbaren Modulnamen. Gemessen
  blieb eine Kante von `0004_event_blob.py` nach `cli` ungemeldet. Ein
  `__init__.py` dort ist in dieser Stufe nicht gebaut; was grimp dann mit den
  Namen tut, ist ungemessen (ruling T1-d; P-AL).
- `module-boundaries.md`: die zwei alten Blöcke mit dem früheren
  Vertragsnamen sind nur durch einen Satz weiter oben als Geschichte
  gekennzeichnet; wer direkt dorthin springt, sieht es nicht (P-AL, Prüfung
  der Aufgabe 1).
- `migrate`: zwei Mechanismen, die Autocommit-Verbindung und kein Entsperren
  im Fehlerweg, verhindern je für sich, dass das Entsperren einen Fehler
  verdeckt; der Test wird nur rot, wenn beide fehlen, und nur eine der zwei
  Sperr-Prüfungen fängt ein fehlendes `storage.close()` (P-AL, Fixrunde 1 der
  Aufgabe 2).

### Spätere Teilprojekte, unverändert offen

- Teilprojekt 3, MCP-Server: MRTR und Tasks in Claude Code prüfen (A §13);
  Pydantic kommt mit dem Schemaexport (`DEPENDENCIES.md`). Mit ihm kommt der
  Zugang ohne `kubectl exec`; bis dahin ist der Werkzeug-Pod der Zugang (AL
  §12 Punkt 5).
- Teilprojekt 4, Gate: Verarbeitungsräume der Anbieter (E §16);
  Trace-Verknüpfung über OpenTelemetry (A §13).
- Teilprojekt 5, KI-Schicht und Triage: Prompt- und Templatetexte;
  Rangfunktion der Triage (A §11).
- Teilprojekt 8, Bestandsimport: Pilotkunde (E §16). Gemessen lädt `append`
  rund 700 Events in der Sekunde; fünf Millionen Events sind zwei Stunden
  (PP, Bericht C).
- Teil 2, Voice: Rechtsfrage zur Gesprächsaufzeichnung; Voxtral und
  Diarisation; Call-Plattformen (E §16). Das Schema trägt `speaker`,
  `start_ms`, `end_ms` schon.
- Oberfläche jenseits MCP (A §11); Mehrsprachigkeit der Bedienung (A §11,
  Nachtrag).

## Erledigt, seit es auf einer Liste stand

- Der äußere Anker (1a §12; 1b §10 Punkt 1) — PR #2.
- `LogStore[Conn]` als Protokoll in `contract`, beide import-linter-Ausnahmen
  entfallen (1a §12) — Stufe 1b.
- `verify` und `READ COMMITTED` (AA §10 Punkt 2) — für `examine` mit
  `snapshot()`, Commit `59072c4`.
- `_quoted_notices` mit lesbarer Zusicherung (P-1b) — Stufe Anker.
- JCS-Implementierung gewählt; Versionsquelle entschieden (1a §12) — Stufe 1a,
  `DEPENDENCIES.md`.
- `previously anchor` druckt Befunde auf die Standardfehlerausgabe statt auf
  die Standardausgabe, sodass `>>` sie nicht in die Ankerdatei trägt (P-AA);
  weicht vom eingefrorenen Anker-Spec §3 ab, die Reference-Seite gilt —
  Wartungsrunde, Commit `43f8df7`.
- Unterparser und Dispatch-Tabelle entstehen aus einer Folge `COMMANDS`; ein
  Test hält die Kommandos aus `previously --help` gegen sie (P-1b; AA §10
  Punkt 11) — Wartungsrunde, Commit `d702007`.
- `pip-audit` in der CI, als eigener Workflow `audit.yml`, wöchentlich und an
  jedem Pull-Request (A §10.6; PP, A2) — Wartungsrunde, Commit `a5ac2db`.
- Renovate konfiguriert, `renovate.json5`; die App muss der Betreuer noch auf
  dem Repository installieren (A §10.7; PP, A2) — Wartungsrunde, Commit
  `b36e715`.
- ~~Fassungsangabe je Zeile, `hash_version`, mit dem ersten `v = 2`~~ (1a
  §12) — Stufe 1c, Commits `72a0044` und `4c078ad`.
- ~~Tilgung als Event im Log (`action`, Unterart `redaction`); erst damit ist
  ein Grabstein von einer Fälschung unterscheidbar~~ (1a §12; A §4.6) —
  Stufe 1c, Commit `a0377ba`; die Blob-Form Commit `a65d1cc`.
- ~~Zeitpunkt für den Bau der Tilgung~~ (A §13) — Stufe 1c, Commit `a0377ba`.
- ~~Eine Tilgung der Nutzlast tilgt die Einheiten nicht, und `p_source_stats`
  stimmt danach nicht ohne Neubau~~ (1b §10 Punkt 2, AA §10 Punkt 5) — eine
  Tilgung des Events nimmt die Einheiten mit, Commit `a0377ba`; die Chronik
  folgt, und `p_source_stats` zählt einen Grabstein inkrementell wie neu
  gebaut weiter, Commit `600f757`.
- ~~Blobs inhaltsadressiert, clientseitig verschlüsselt, Schlüsselbehandlung,
  Dateisystem-Adapter; keine Versionierung auf dem Bucket~~ (A §4.6
  Vorkehrungen 2 und 3, §10.3, §12.1) — Stufe 1c, Commits `13d0d5e` und
  `9efb419`. Statt eines Dateisystem-Adapters gibt es einen einzigen, für
  S3 (1c §1.1); „ohne Versionierung" steht in `configuration.md` und in der
  Anleitung für den eigenen Rechner, geprüft wird es nicht.
- ~~`evidence` steht in der Nutzlast; eine Tilgung nimmt die Belegart mit~~
  (PP, A1 Zeilen 10 und 11) — entschieden: die Belegart geht mit der Nutzlast,
  `erasure.md` sagt es; Stufe 1c, Commit `a0377ba`.
- ~~Sperre auf der Zustandszeile: zwei gleichzeitige Läufe einer Projektion
  schreiben heute beide~~ (1b §10 Punkt 8, F11) — Endkorrektur, Commit
  `3ae7038`: jede Transaktion eines Nachziehens sperrt die Zustandszeile und
  liest Lesezeichen und Fassung aus ihr.
- Die Unterart einer Handlung hat einen Ort, die Nutzlast unter `action`, und
  `verify` kennt eine erste Regel je Art, für `action` (PP, A1 S2 und S3, je
  zur Hälfte; die andere Hälfte steht oben unter *Feststellungen und
  Entitäten*) — Stufe 1c, Commit `a0377ba`.
- ~~Image~~ (A §11, §13; aus dem Punkt „Deployment-Mechanismus; Image; …"
  unter *Betrieb*) — Auslieferung, Commits `aa5ee8c` (Image und Smoke-Test),
  `ea7ceb2` (Release-Weg), `05372db` und `4d7e4b9` (der Smoke-Test unter
  fremder uid). Der Rest des Punkts steht weiter dort.
- ~~`redact units` lässt den Wortlaut der Einheiten in der Nutzlast stehen,
  und `append --text` legt den ganzen Text unter `text` ab~~ (Aufgabe 8, P-1c;
  ruling E-3 der Endkorrektur) — entschieden vom Betreuer am 2026-10-05:
  `append --text` legt den Text nur noch in die Einheiten, die Nutzlast trägt
  `evidence` und mit Anhängen `blobs`; Events von vorher behalten ihre Kopie.
  Der Hinweis von `redact units` kommt nur noch, wenn ein Text der Nutzlast den
  Wortlaut einer getilgten Einheit enthält — Commit `09c5d81`. Dass eine
  Nutzlast, die den Wortlaut hält, ihn nach `redact units` behält, bleibt als
  Regel stehen und steht in `cli.md` und `erasure.md`.
