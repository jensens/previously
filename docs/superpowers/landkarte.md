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

Nicht gebaut: Stufe 1c (Blobs, Verschlüsselung, Tilgung), die Suche, jede
Feststellung und jede Entität, der Konnektor-Vertrag über `RawEvent` hinaus,
MCP-Server, Gate, KI-Schicht, jeder Konnektor — und kein Betrieb: das System
läuft bisher nur aus dem Arbeitsverzeichnis, gegen eine Wegwerf-Datenbank, und
hat **noch kein einziges echtes Event** gehalten.

## Was als Nächstes kommt

**Der Pilot an einem echten Kunden.** Vom Betreuer am 2026-10-04 entschieden,
nach dem Prüfpunkt und der kleinen Wartungsrunde, die er an die erste Stelle
gesetzt hatte (ihre vier Punkte stehen unten unter *Erledigt*).

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
- **Das Pilot-Log ist wegwerfbar.** Tilgen heißt im Piloten: aus dem Ordner
  nehmen, Datenbank verwerfen, neu einlesen. Das trägt für einen Piloten und
  für nichts danach; vor einem zweiten Kunden oder einem Dauerbetrieb steht
  die Tilgung als Event.
- **Datenpolitik des Pilotkunden:** sein Inhalt darf über Claude Code an
  Anthropic gehen („bei diesem Kunden gedeckt", Betreuer, 2026-10-04).
- **Betrieb:** gleich in kup6s, nicht erst lokal.

Die Einheiten, in dieser Reihenfolge; nur die jeweils nächste bekommt einen
Spec:

| # | Einheit | bringt | Spec |
|---|---|---|---|
| 1 | Aufnahme aus dem IMAP-Ordner, mit dem Einwurf- und dem Konnektor-Vertrag | Chronik des Kunden; echte Post im Log | `specs/2026-10-04-pilot-imap-aufnahme.md`, in Arbeit |
| 2 | Betrieb in kup6s: Image, Datenbank mit Sicherung, Restore-Probe, CronJobs für Aufnahme, Projektion und Anker | Daten, die bleiben | — |
| 3 | Gate und Policy: Organisationsprofil des Pilotkunden, ein Anbieter-Adapter, Audit, Offenlegungsprüfung | die Grenze, hinter der ein Modell Inhalt sieht | — |
| 4 | MCP-Lesezugang, mit der Offenlegungsprüfung davor | Claude Code fragt das Log | — |
| 5 | Feststellungen: Schreibweg, Verpflichtung und Entscheidung, Projektionen, Freigabe | was festgestellt ist, mit Quelle und Verantwortung | — |
| 6 | KI-Schicht: Vorschläge hinter dem Gate | Protokoll und offene Punkte | — |
| 7 | Nextcloud-Ordner mit Textextraktion | Dokumente | — |

Offen für Einheit 2 und vom Betreuer noch zu beantworten: was kup6s heute
bereitstellt (CloudNativePG, ArgoCD, Registry, Zugang vom Arbeitsplatz) und wo
sein Repository liegt.

## Was vor was kommen muss

Keine Planung der Teilprojekte — die Architektur nennt das zu Recht Fiktion
(§12.2) —, sondern die Zwänge, die heute schon feststehen. Jede Zeile hat
ihren Beleg im Prüfpunkt.

| Zuerst | dann | weil |
|---|---|---|
| Der Einwurf-Vertrag entscheidet, was mit geändertem Inhalt unter bekanntem Schlüssel geschieht | jeder Konnektor | `append` verwirft ihn heute stumm; wer die Issue-Nummer als `external_id` nimmt, verliert jede Änderung nach der ersten |
| `RawEvent` bekommt Rohbytes und Kanalidentitäten, oder die Architektur gibt sie auf | IMAP, Drop-Ordner | Leitsatz 6: was nicht aufgenommen wurde, ist nicht nachholbar |
| Feststellungen: zweiter Schreibweg, Art und Unterart, Regeln je Art in `verify` | Triage, `record_assertion`, KI-Schicht, Identitätsgraph, jede fachliche Projektion | `append` schreibt nur `observation`; `verify` kennt keine Art-Regeln |
| Blobs mit Verschlüsselung | Drop-Ordner mit Dateien, IMAP mit Anhängen und Rohmail, Voice | es gibt keinen Ort für Bytes |
| Tilgung als Event, die Einheiten und Projektionen mitnimmt | ein zweiter Kunde, ein Dauerbetrieb — alles, was über das wegwerfbare Pilot-Log hinausgeht | heute ist ein Grabstein von einer Fälschung nicht zu unterscheiden, und die Einheiten bleiben stehen. Für den Piloten am 2026-10-04 ausgesetzt: sein Log lässt sich aus den Quellen neu aufbauen |
| Ein Betrieb mit Sicherung, Restore-Probe und Anker-Routine | Daten, deren Verlust weh tut | bisher gibt es nur Wegwerf-Datenbanken |
| Echte, gemischtsprachige Einheiten im Log | die Messung zur Textsuche und die Wahl des Embedding-Modells | beide verlangen einen Testsatz aus echten gemischten Einheiten (Architektur §11, Nachtrag) |
| Warteschlange mit Sperre auf der Zustandszeile | der erste asynchrone Produzent | zwei gleichzeitige Läufe einer Projektion schreiben heute beide |
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
  Betrieb. Image, Deployment, Sicherung, Restore-Probe und Anker-Routine sind
  eine Einheit Arbeit, die niemand zugeschnitten hat.

## Offene Punkte, nach ihrem Zuhause

Herkunft in Klammern: **A** Architektur, **E** Entwurf, **1a**/**1b**/**AA**
die Stufen-Specs mit Abschnitt, **P-1b**/**P-AA** das `index.md` des
jeweiligen Ausführungsprotokolls, **PP** der Prüfpunkt vom 2026-10-04 mit der
Zeile seines Belegberichts.

### Einwurf-Vertrag (`contract`, Teilprojekt 2)

- Geänderter Inhalt unter bekanntem `(source, external_id)` wird stumm
  verworfen; entscheiden: vergleichen und melden, oder die Änderung gehört in
  die `external_id` — und es dann auf eine Seite schreiben (PP, A1 Zeile 8 und
  S7).
- `RawEvent` ohne `raw: bytes` und ohne `channel_identities`, gegen
  Architektur §6.2; ein Grund ist nirgends aufgeschrieben (PP, A1 Zeile 12).
- `RawEvent.payload` steht in keinem Vertrag der Architektur, und die
  Kommandozeile legt den Volltext dort ab (PP, A1 Zeile 13). Damit steht der
  Text dreimal in der Datenbank — Nutzlast, Einheiten, `p_chronicle` —, und
  aus 1 GB Text werden 4,5 GB (PP, Bericht C).
- Der Nutzlastbereich weist Mail-Header-Schlüssel, Bytes und Gleitkommazahlen
  ab; ein Konnektor muss umformen, bevor er aufnimmt (PP, A1 Zeile 14 und
  Leitsatz 4).
- `evidence` steht in der Nutzlast; eine Tilgung nimmt die Belegart mit (PP,
  A1 Zeilen 10 und 11).
- `--occurred-at` fällt auf „jetzt" zurück, `--evidence` auf `recollection`:
  zwei Vorgabewerte, die als Tatsache in der Kette stehen; und was
  `occurred_at` bei einer Erinnerung meint, die Notiz oder das Ereignis, ist
  nicht entschieden (PP, A1 Zeile 34 und Leitsatz 9).
- Zerlegungsregeln der weiteren Medien (1a §12).
- Interne Abgleichlogik je Konnektor (A §11).
- Der Einwurf per Prompt, der Drop-Ordner mit Textextraktion und OCR, „Quelle
  verlinken" (E §11.4).

### Feststellungen und Entitäten (ohne Teilprojekt)

- Ein zweiter Schreibweg neben `append` für `assertion` und `action`; ihre
  Idempotenz ist heute „Sache des Aufrufers" (PP, A1 S1 und Zeile 19).
- `verify` prüft keine Regeln je Art: eine Feststellung ohne `sources` und
  eine Wahrnehmung ohne `evidence` und ohne Schlüssel bestehen (PP, A1 S2,
  Messungen M3 und M4).
- Keine Validierung der Nutzlast gegen ein Schema je Art, gegen Architektur
  §4.1 (PP, A1 Zeile 20).
- `kind` heißt zweierlei: die Event-Art mit drei Werten und die Unterart einer
  Feststellung oder Handlung, die keine Spalte hat (PP, A1 S3).
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

### Stufe 1c: Blobs und Tilgung

- Blobs inhaltsadressiert, clientseitig verschlüsselt, Schlüsselbehandlung,
  Dateisystem-Adapter; keine Versionierung auf dem Bucket (A §4.6
  Vorkehrungen 2 und 3, §10.3, §12.1).
- Tilgung als Event im Log (`action`, Unterart `redaction`); erst damit ist
  ein Grabstein von einer Fälschung unterscheidbar (1a §12; A §4.6).
- Eine Tilgung der Nutzlast tilgt die Einheiten nicht, und `p_source_stats`
  stimmt danach nicht ohne Neubau (1b §10 Punkt 2, AA §10 Punkt 5).
- Zeitpunkt für den Bau der Tilgung (A §13).
- Fassungsangabe je Zeile, `hash_version`, mit dem ersten `v = 2` (1a §12).

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
- Sperre auf der Zustandszeile: zwei gleichzeitige Läufe einer Projektion
  schreiben heute beide (1b §10 Punkt 8, F11).

### Betrieb (ohne Teilprojekt)

- Deployment-Mechanismus; Image; Datenbank mit Sicherung; welche
  pgBackRest-Plugin-Implementierung (A §11, §13; `backup-encryption.md`).
- Ablageort und Intervall der Anker; benannter Restore-Point im Takt des
  Ankerns (AA §10 Punkt 4).
- Der Container-Weg der Anker-Routine ist für `kubectl exec` ungemessen
  (P-AA).
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
- Die Kommandozeile ist mit acht Kommandos, Ausgabeverträgen und Rückgabecodes
  faktisch eine Oberfläche mit Vertrag geworden, obwohl sie nur der Einstieg
  ist, bis der MCP-Server steht (PP, A2 §11 Zeile 8).

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

### Spätere Teilprojekte, unverändert offen

- Teilprojekt 3, MCP-Server: MRTR und Tasks in Claude Code prüfen (A §13);
  Pydantic kommt mit dem Schemaexport (`DEPENDENCIES.md`).
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
