# Previously — Der äußere Anker

Stand: 2026-10-04 · Status: Entwurf, zur Abnahme

Dieser Spec entsteht auf Deutsch und friert ein, sobald
`docs/explanation/hash-chain.md` den Anker trägt — so, wie `CLAUDE.md` es unter
*A specification starts in German and then freezes* beschreibt. Er ist klein:
keine Stufe, sondern die Einlösung einer Zusage. Der Betreuer hat sie am
2026-10-04 gegeben („darf nicht vergessen werden"), und sie stand als Punkt 1
in §10 der eingefrorenen 1b-Spec.

Er argumentiert aus §11 der eingefrorenen 1a-Spec, die den Anker zuerst
beschrieb, und widerspricht ihr an einer Stelle (§1.1).

## 1. Zweck und Zuschnitt

Die Kette bezeugt, dass **unverändert** ist, was im Log steht. Dass es
**vollständig** ist, bezeugt sie nicht. Die 1a-Spec hat das gemessen: drei
Events, `DELETE` auf `id = 3` samt Einheiten und Quellenangabe, und `verify`
meldet `chain intact` mit Rückgabecode 0. Eine Kette 1→2 mit gelöschter 3 ist
von einer Kette, die nie mehr als 1→2 war, nicht zu unterscheiden.

Dagegen hilft nur ein Bezugspunkt außerhalb der Datenbank. Gebaut wird:

1. **die Ankerzeile** `<id> <hash>` und die Ankerdatei als Folge solcher
   Zeilen (§2);
2. **`previously anchor`**, das die Spitze einer intakten Kette als Ankerzeile
   druckt (§3);
3. **`previously verify --anchors DATEI [--exact]`**, das die Anker im selben
   Durchlauf wie die Kette prüft (§4);
4. **ein Hinweis auf `stderr`**, wenn `verify` ohne Anker läuft: die Grenze
   der Aussage steht dann nicht nur in der Doku (§4.4);
5. **die Dokumentation**, einschließlich zweier Korrekturen an Seiten, die
   heute mehr zusagen, als der Baum hält (§8).

**Nicht im Zuschnitt:** Signaturen des Schreibers, Zeitstempeldienste,
automatisches Veröffentlichen, Anker in der Datenbank. Der letzte Punkt ist
keine Vertagung, sondern ausgeschlossen: wer die Kette umschreiben kann,
schriebe einen Anker in derselben Datenbank mit um.

### 1.1 Was dieser Spec an der 1a-Spec korrigiert

§11 der 1a-Spec sagt, gegen den Anker könne `verify` „Länge und Spitzenwert
prüfen, und damit fällt Löschen, Anhängen und Neuschreiben auf".
`hash-chain.md` hat den Satz übernommen („is what closes all three at once")
und dabei die `id`-Hälfte verloren („publishing the tip's hash").

Der Satz ist zur Hälfte richtig. Ein Anker `(n, h)` nagelt das **Präfix**
1..n fest: weil jeder Hash seinen Vorgänger einschließt, steht mit `h` an
Position n alles davor. Abschneiden unter n und jedes Umschreiben bis n
fallen auf.

Ein **gefälschtes Anhängen nach n** fällt nicht auf. Es sieht aus wie
legitimes Wachstum, denn Wachstum ist der Normalfall eines Logs. Schlimmer:
der nächste Anker, der nach der Fälschung genommen wird, schreibt sie mit
fest.

Erkennbar wird es nur, wenn man prüft, dass die Spitze **genau** der Anker
ist — also in einem Moment, in dem man weiß, dass nichts Legitimes dazukam:
nach einem Restore, gegen den Anker vom Zeitpunkt des Backups, oder
unmittelbar nach dem Ankern. Wirklich schließen würde es erst eine Signatur
des Schreibers je Event; die steht in §10.

Daraus folgen **zwei Prüfarten** (§4), und §5 sagt je Fälschung, welche sie
erkennt. Dass einer der vier Fälle in keiner Prüfart erkannt wird, steht
dort als Grenze und bekommt einen Test, der sie festnagelt.

### 1.2 Zwei Einstiege

Die Kommandozeile ist der Einstieg, **bis es den MCP-Server gibt**: der
Entwurf führt die MCP-Werkzeuge als „im MVP die gesamte Oberfläche", und die
1a-Spec zählt `mcp_server` zu dem, was Stufe 1a nicht enthält. Für diesen Spec
heißt das:

- Was der Anker **ist** und was `verify` dagegen prüft, gehört in den Kern.
  Der Kern liefert **strukturierte Ergebnisse** — Anker, Befunde — und keine
  fertigen Sätze.
- Der Einstieg liest die Datei und formatiert. Ein zweiter Einstieg ruft
  dieselben zwei Kernfunktionen und formatiert anders.
- Das Dateiformat ist das Dauerhafte, nicht der Schalter `--anchors`.

Die Ankerroutine selbst bleibt auch mit MCP-Server ein Betriebsvorgang — sie
läuft aus `cron`, nicht aus einem Gespräch —, und das ist ein zweiter Grund,
sie skriptbar zu halten.

## 2. Der Anker

Ein **Anker** ist das Paar `(id, hash)` der Spitze zu einem Zeitpunkt. Als
Text ist er eine Zeile:

```
<id> <hash>
```

`id` ist eine positive ganze Zahl, `hash` sind 64 Hex-Zeichen. Geschrieben
wird klein, gelesen werden beide Schreibweisen. Die Felder trennt beim
Schreiben ein Leerzeichen, beim Lesen beliebiger Leerraum.

Eine **Ankerdatei** ist eine Folge solcher Zeilen. Leerzeilen und Zeilen, die
mit `#` beginnen, zählen nicht — damit lässt sich eine Datei von Hand
kommentieren. **Alles andere ist ein Eingabefehler**: ein drittes Feld, eine
`id`, die keine positive ganze Zahl ist, ein Hash, der nicht 64 Hex-Zeichen
hat. Die Meldung nennt die Zeilennummer. Eine beschädigte Datei wird nicht
halb gelesen; eine Prüfung gegen die Hälfte der Anker sähe aus wie eine gegen
alle.

Eine Datei **ohne einen einzigen Anker** ist ebenfalls ein Eingabefehler.
`chain intact, 0 anchors hold` wäre die schwache Aussage im Kleid der
starken.

Dieselbe Zeile zweimal ist harmlos. Zwei Zeilen mit derselben `id` und
verschiedenen Hashes werden beide geprüft, und mindestens eine ergibt einen
Befund — dafür braucht es keine eigene Regel.

**Was der Anker nicht ist:** er trägt keinen Zeitpunkt und keine Unterschrift.
Das „wann" liefert der Ort, an dem die Datei liegt — das Commit-Datum im
Git-Repository, das Datum der Mail an sich selbst. Previously veröffentlicht
nicht; es druckt die Zeile, und wohin sie geht, entscheidet der Betrieb. Die
eine Bedingung an den Ort: **wer die Datenbank schreiben kann, darf ihn nicht
schreiben können.**

## 3. `previously anchor`

Nimmt keine Argumente. Prüft die Kette in demselben Durchlauf, den `verify`
macht, und:

| Lage | `stdout` | `stderr` | Rückgabecode |
|---|---|---|---|
| Kette intakt, Log nicht leer | eine Ankerzeile für die Spitze | — | 0 |
| mindestens ein Befund | die `FINDING`-Zeilen wie bei `verify` | — | 1 |
| Log leer | — | `the log is empty: nothing to anchor` | 0 |
| Storage-Fehler | — | `Error: …` | 2 |

Bei einem Befund entsteht **kein** Anker: ein Anker auf einer gebrochenen
Kette würde den Bruch beglaubigen.

Die Spitze, die gedruckt wird, ist die letzte Zeile, die der Durchlauf
gesehen hat — nicht das Ergebnis einer zweiten Abfrage danach. Zwischen
Prüfung und Anker liegt damit kein Moment, in dem die Spitze eine andere
sein könnte als die geprüfte.

`anchor` nimmt absichtlich keine `--anchors`: alte Anker zu prüfen ist die
Sache von `verify`, und die Routine ist zwei Kommandos (§8, How-to).

## 4. `previously verify` mit Ankern

### 4.1 Argumente

- `--anchors DATEI` — die Ankerdatei; `-` liest `stdin`.
- `--exact` — zusätzlich muss die Spitze genau der jüngste Anker sein. Ohne
  `--anchors` ist `--exact` ein Eingabefehler.

### 4.2 Was geprüft wird

**„enthält"** ist der Normalfall. Für jeden Anker: das Event mit dieser `id`
existiert, und sein Hash ist der geankerte.

**`--exact`** verlangt darüber hinaus, dass die `id` der Spitze die höchste
`id` unter den Ankern ist. Der Hash dieser Spitze ist dann schon durch
„enthält" geprüft.

Die Anker werden **im Durchlauf** geprüft: wenn der Lauf an einer geankerten
`id` vorbeikommt, vergleicht er. Es gibt keine zweite Lesung, und die Spitze
für `--exact` ist die letzte Zeile des Laufs.

### 4.3 Befunde

Im bestehenden Format `FINDING <event_id>: <reason>`, zusammen mit den
Befunden der Kette, Rückgabecode 1:

| Befund | `event_id` | `reason` |
|---|---|---|
| Hash weicht ab | die `id` des Ankers | `hash does not match the anchor` |
| geankertes Event fehlt | die `id` des Ankers | `anchored event is missing — the log ends at <tip>` |
| Spitze liegt über dem jüngsten Anker (nur `--exact`) | die `id` der Spitze | `the log continues past the newest anchor (<id>)` |

`<tip>` ist die `id` der Spitze, bei leerem Log 0. Liegt die Spitze **unter**
dem jüngsten Anker, ist das schon „fehlt"; `--exact` meldet dann nichts
Zweites.

### 4.4 Erfolgsmeldungen und der Hinweis ohne Anker

| Aufruf | `stdout` bei intakter Kette |
|---|---|
| `verify` | `chain intact` |
| `verify --anchors DATEI` | `chain intact, N anchors hold` (bei einem: `1 anchor holds`) |
| `verify --anchors DATEI --exact` | `chain intact, N anchors hold, the tip is the newest anchor` |

`N` ist die Zahl der Ankerzeilen in der Datei.

**Ohne Anker** bleibt `stdout` unverändert `chain intact` und der
Rückgabecode 0 — bestehende Skripte merken nichts. Auf `stderr` steht eine
Zeile:

```
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

Nur bei intakter Kette; neben Befunden wäre der Satz Rauschen. Das Muster ist
das der Rückstandszeile von `chronicle`: Skripte lesen `stdout`, Menschen
sehen die Grenze der Aussage. Die Zeile trägt kein Zitat — sie ist
Programmausgabe.

### 4.5 Rückgabecodes

| Code | Bedeutung |
|---|---|
| 0 | kein Befund |
| 1 | mindestens ein Befund, aus der Kette oder aus den Ankern |
| 2 | Eingabefehler (Ankerdatei unlesbar, fehlerhaft oder leer; `--exact` ohne `--anchors`) oder Storage-Fehler |

## 5. Was die Zusage danach sagt

| Fälschung | „enthält" | `--exact` |
|---|---|---|
| Spitze löschen, unter dem jüngsten Anker | erkannt | erkannt |
| Kette bis zu einem Anker umschreiben | erkannt | erkannt |
| Spitze löschen, **über** dem jüngsten Anker | nicht erkannt | nicht erkannt |
| gefälschtes Anhängen | nicht erkannt | erkannt, solange seit dem Anker nichts Legitimes dazukam |

Die dritte Zeile ist die Grenze jedes Ankers: er bezeugt nur, was es gab, als
er genommen wurde. Sie wird kleiner, je öfter geankert wird, und verschwindet
nie.

Die vierte Zeile ist die Korrektur aus §1.1. `--exact` ist darum kein Modus
für den laufenden Betrieb, sondern für den Moment der Ruhe: nach dem Restore,
vor einer Übergabe.

Die Zusage, im Ganzen, für `hash-chain.md`: *Was das Log sagt, ist
unverändert. Was es bis zum jüngsten Anker sagte, ist vollständig. Dass
seither nichts hinzugefälscht wurde, bezeugt nur der Vergleich der Spitze mit
einem Anker, den man in Ruhe genommen hat.*

### 5.1 Was das für den Betrieb heißt

**Das Intervall ist die Beweis-Lücke.** Was seit dem jüngsten Anker dazukam,
ist nicht verankert. Wer stündlich ankert, hat höchstens eine Stunde, die das
Log nicht als vollständig bezeugt.

**Ein Restore hat zwei Fälle**, und sie verlangen verschiedene Prüfarten. Die
Architektur sichert mit Base-Backup und WAL-Archiv (§10.5 der Architektur),
also mit Point-in-Time-Recovery:

- **Restore bis zum letzten Stand.** Er bringt auch die Events zurück, die
  nach dem jüngsten Anker angefügt wurden — sie kommen aus dem WAL. `--exact`
  würde dann „continues past" melden, obwohl nichts fehlt. Richtig ist
  **„enthält"** gegen den jüngsten Anker: darunter ist nichts verloren und
  nichts umgeschrieben; was darüber liegt, ist der unverankerte Rest aus dem
  Absatz davor.
- **Restore auf einen festen Punkt.** Nur hier passt **`--exact`**, und nur,
  wenn Anker und Wiederherstellungspunkt zusammenfallen: ein benannter
  Restore-Point unmittelbar nach dem Ankern, oder ein logischer Dump mit dem
  Anker im selben Atemzug.

Die erste Fassung dieses Specs verlangte nach jedem Restore `--exact` gegen
„den Anker vom Zeitpunkt des Backups". Für ein Backup mit WAL-Archiv gibt es
diesen einen Zeitpunkt nicht; die Frage des Betreuers nach dem Betrieb hat
das gezeigt (2026-10-04).

**Wo die Datei liegt und wie oft geankert wird**, entscheidet dieser Spec
nicht. Beides fällt mit dem Deployment einer späteren Stufe und steht in §10.
Die eine Bedingung aus §2 gilt unabhängig davon.

## 6. Schnitt im Code

- **`previously.contract.types.Anchor`** — eingefrorene Dataclass,
  `id: int`, `hash: bytes`.
- **`previously.core.anchor`** — zwei reine Funktionen:
  `parse_anchors(lines: Iterable[str]) -> tuple[Anchor, ...]`, die bei einem
  Fehler `InvalidPayload` mit Zeilennummer wirft und bei null Ankern ebenso;
  `format_anchor(anchor: Anchor) -> str`. Kein Dateizugriff, keine Datenbank.
- **`previously.core.verify`** — eine neue Funktion
  `examine(storage, *, anchors=(), exact=False, batch=1000) -> Examination`
  mit `Examination(findings: tuple[Finding, ...], tip: Anchor | None)`. Sie
  ist der eine Durchlauf. `verify()` bleibt mit seiner heutigen Signatur und
  ruft sie; bestehende Aufrufer und Tests ändern sich nicht.
- **`previously.cli`** — `_cmd_anchor`, das erweiterte `_cmd_verify`, das
  Lesen der Datei (`-` für `stdin`), die Sätze. Ein achter Eintrag in der
  Dispatch-Tabelle.

Keine Migration, keine Tabelle, keine neue Abhängigkeit, kein neuer Vertrag
in `.importlinter`.

**Nicht angefasst:** der Kommentar in `verify`, eine Transaktion über die
ganze Prüfung gebe allen Lesungen denselben Schnappschuss (Prüfbefund G4 der
ersten Endprüfung). Unter `READ COMMITTED` bekommt jede Anweisung ihren
eigenen; die Endprüfung von Stufe 1b hat dieselbe Denkfigur an der
Rückstandszeile gefunden und dort beheben lassen. Für `verify` ist die Frage
offen und steht in §10. Der Anker fügt ihr nichts hinzu: er liest nichts
Zusätzliches.

## 7. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, von dem gemessen ist, dass er bricht,
und eine Kontrolle daneben, die gemessen grün bleibt (`CLAUDE.md`, *An
assurance needs a test measured to fail*). Gegen echtes PostgreSQL, ohne
Mock; Fälschungen mit rohem SQL, wie in den Tests der Kette.

1. **Der Fall aus der 1a-Spec.** Drei Events, Anker auf die Spitze, `DELETE`
   der Spitze: ohne Anker `chain intact`, mit Anker der Befund „fehlt". Die
   Kontrolle ist die erste Hälfte desselben Tests.
2. **Umschreiben unter dem Anker.** Ein Event unter dem Anker so umschreiben,
   dass die Kette in sich wieder stimmt (alle Hashes ab dort neu): ohne Anker
   `chain intact`, mit Anker „hash does not match the anchor".
3. **Gefälschtes Anhängen.** Ein in sich gültiges Event nach dem Anker:
   „enthält" bleibt grün — das ist die festgenagelte Grenze —, `--exact`
   meldet „continues past".
4. **Die Grenze über dem jüngsten Anker.** Anker bei n, zwei Events dazu, das
   letzte gelöscht: beide Prüfarten grün. Der Test hält fest, dass das
   **nicht** erkannt wird; wer es später schließt, sieht ihn rot werden.
5. **Fehlerhafte Datei.** Je ein Fall: drittes Feld, `id` 0, Hash mit 63
   Zeichen, Hash mit Nicht-Hex, Datei ohne Anker. Rückgabecode 2, kein
   Teilergebnis auf `stdout`.
6. **`anchor` auf gebrochener Kette** druckt keinen Anker; auf leerem Log
   nichts auf `stdout`.
7. **`verify` ohne Anker:** `stdout` ist genau `chain intact`, `stderr` der
   Hinweis, Rückgabecode 0; mit Befund kein Hinweis.
8. **`parse_anchors` und `format_anchor`** rein: Rundreise, Groß- und
   Kleinschreibung, Kommentare, Leerzeilen.
9. **Der Hinweis und die drei Befundtexte** stehen auf `cli.md` und werden
   gegen den Code gehalten. Gemessen am 2026-10-04: der Test, der die Zitate
   der Reference prüft, liest dafür nur `cli.py`; die Befundtexte entstehen
   in `core/verify.py`. Er wird um diese Datei erweitert — für die drei neuen
   Texte; die bestehenden Befundtexte, soweit `cli.md` sie zitiert, kommen
   damit mit.

Die Mutationen: den Vergleich des Hashs entfernen (1 und 2 rot), die Prüfung
auf fehlende Anker entfernen (1 rot), `--exact` zur Nulloperation machen
(3 rot), den strengen Parser lockern (5 rot).

## 8. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`.

- **`docs/explanation/hash-chain.md`** — ein Abschnitt zum Anker mit eigenem
  Label: was er ist, warum die `id`-Hälfte die wichtige ist, die Tabelle aus
  §5, die Zusage im Ganzen, und was offen bleibt. Der Satz „closes all three
  at once" fällt; „stage 1a has none" ebenso.
- **`docs/reference/cli.md`** — `anchor` als achtes Kommando; `verify` mit
  seinen zwei Argumenten, den drei Befundtexten, den Erfolgsmeldungen, dem
  Hinweis; die Rückgabecode-Tabelle.
- **`docs/how-to/verify-the-chain.md`** — „It takes no arguments" stimmt
  nicht mehr. Dazu die Routine: erst die alten Anker prüfen, dann einen neuen
  nehmen, die Datei außerhalb halten.
- **`docs/how-to/restore-from-a-backup.md`** — der Satz „If `previously
  verify` exits `0`, the restore is trustworthy" ist zu stark: ein Restore
  aus einem älteren Backup ist eine kürzere, in sich stimmige Kette und
  besteht. Die Anleitung führt künftig die zwei Fälle aus §5.1 — Restore bis
  zum letzten Stand mit `verify --anchors …`, Restore auf einen festen Punkt
  mit `--exact` — und sagt, was Rückgabecode 0 **ohne** Anker bedeutet.
- **`README.md`** — die Zahl der Kommandos, und der Absatz über die Grenze
  der Kette.
- **`docs/tutorials/record-your-first-event.md`** — der `verify`-Block zeigt
  im Terminal künftig auch die `stderr`-Zeile; er wird aus einem echten Lauf
  neu getippt, mit einem Satz dazu, und der Testlauf zuletzt.
- **`docs/explanation/design-records.md`** und die Tabelle im README — der
  fünfte eingefrorene Bericht, wenn dieser Spec einfriert.

## 9. Abnahme

| # | Bedingung |
|---|---|
| 1 | Der in 1a §11 gemessene Fall (Spitze gelöscht, `chain intact`) ergibt mit Anker einen Befund. |
| 2 | Umschreiben bis zu einem Anker ergibt einen Befund, auch wenn die Kette in sich stimmt. |
| 3 | Gefälschtes Anhängen: „enthält" grün, `--exact` Befund — beide Hälften in einem Test. |
| 4 | Die Grenze über dem jüngsten Anker ist als Test festgenagelt und auf `hash-chain.md` benannt. |
| 5 | Eine fehlerhafte oder leere Ankerdatei gibt Rückgabecode 2 und nichts auf `stdout`. |
| 6 | `anchor` druckt nur bei intakter Kette; die gedruckte Spitze ist die des Durchlaufs. |
| 7 | `verify` ohne Anker: `stdout` unverändert, ein Satz auf `stderr`, Rückgabecode 0. |
| 8 | `core` liefert `Anchor` und `Finding`, keine Sätze; `cli` importiert kein SQL; `verify()` behält seine Signatur. |
| 9 | Jede Zusicherung aus §7 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 10 | Die Dokumente aus §8 sind nachgezogen; keines sagt mehr zu, als §5 hält. |
| 11 | Alle sechs Tore grün. |
| 12 | Dieser Spec ist eingefroren, `design-records.md` und README führen ihn. |

Abgenommen ist die Arbeit mit dem Merge nach `main` (`CLAUDE.md`, *A merge
into `main` is the acceptance*).

## 10. Was offen bleibt

Dieser Abschnitt ist **gepflegt**, solange der Spec lebt. Er übernimmt, was
die eingefrorene 1b-Spec in §10 weitergegeben hat, und was das
Ausführungsprotokoll der Stufe 1b in seiner `index.md` für die nächste Stufe
vorgemerkt hat. Friert dieser Spec ein, wandert die Liste in den Spec, der
ihm folgt.

**Neu aus diesem Spec:**

1. **Die Signatur des Schreibers.** Nur sie schließt gefälschtes Anhängen
   außerhalb des Moments der Ruhe (§1.1, §5). Sie verlangt einen Schlüssel,
   seinen Ort und seine Rotation — eine eigene Entscheidung, kein halber Tag.
2. **`verify` und `READ COMMITTED`.** Der Kommentar zum einen Schnappschuss
   (§6). Entweder liest `verify` unter `REPEATABLE READ`, oder der Kommentar
   sagt, was eine Transaktion unter `READ COMMITTED` wirklich gibt.
3. **Ein beglaubigtes „wann".** Der Anker trägt keinen Zeitpunkt (§2). Wer
   ihn braucht, über den Ablageort hinaus, landet bei einem Zeitstempeldienst.
4. **Ablageort und Intervall im Betrieb.** Eine Betriebsentscheidung, die mit
   dem Deployment fällt (§5.1). Der Stand der Überlegung vom 2026-10-04, als
   Ausgangspunkt und nicht als Beschluss: die Routine ist ein CronJob mit dem
   Image der Anwendung, der die alten Anker prüft, einen neuen nimmt und bei
   einem Rückgabecode ungleich 0 alarmiert. Als Ablageort, nach Stärke: ein
   Git-Repository bei einem Dritten mit einem Deploy-Key, der nur dorthin
   schreiben darf, und gesperrtem Force-Push — dann kann auch ein
   Cluster-Admin nur anhängen; ein Bucket mit Object Lock im anderen
   Standort — **ungeprüft**, ob der Anbieter das hat; eine Mail an ein
   Postfach bei einem Dritten als zweiter Kanal. Gegenüber Dritten ist der
   Anker nur ein Beleg, wenn er bei einem Dritten liegt. Und für `--exact`
   nach einem Restore braucht es einen benannten Restore-Point im Takt des
   Ankerns.

**Übernommen aus der 1b-Spec §10** (dort im Wortlaut):

5. Eine Tilgung der Nutzlast tilgt die Einheiten nicht (Punkt 2).
6. `show` druckt Einheiten roh (Punkt 3).
7. Die Warteschlange, mit ihr die Sperre auf der Zustandszeile (Punkte 4
   und 8, Prüfbefund F11 der Prüfung von Aufgabe 5 des 1b-Plans), und die
   zwei Notizen darunter: `Projection.write` mit eigener Transaktion (F9),
   `projection_state.version` ohne `CHECK` (F12).
8. Drei geparkte Testlöcher am Doku-Tor (Punkt 5).
9. Zuordnung zu Projekten (Punkt 6).
10. `previously stats` ohne Zeitraum (Punkt 7).

**Übernommen aus dem Ausführungsprotokoll der Stufe 1b**
(`docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/index.md`):

11. Ein Test, dass jeder Unterparser-Name einen Eintrag der Dispatch-Tabelle
    hat. Dieser Spec fügt einen achten Eintrag hinzu; der Plan entscheidet,
    ob der Test mitkommt.
12. Eine Obergrenze für `--limit`.
13. Die Seiten-Reihenfolge der zwei `stderr`-Hinweise in `cli.md` hält nichts
    mechanisch.
14. `_quoted_notices` läuft bei fehlendem Ankersatz in einen `IndexError`;
    `_message_patterns` nimmt auch die `_describe`-Literale auf.
15. Das Tor für `§`-Zitate prüft den Marker, nicht, ob der zitierte Spec
    eingefroren ist.
