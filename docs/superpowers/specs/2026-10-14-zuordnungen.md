# Previously — Zuordnungen: Entitäten, Beziehungen und Kreise im Graphen

**Datum:** 2026-10-14
**Status:** Entwurf, aus dem Brainstorming mit dem Betreuer am 2026-10-13 und
2026-10-14 („die Basis ist gut und tragfähig"); vom Betreuer am 2026-10-14
durchgesehen („bin durch, der Rest passt"), mit seinen Änderungen beim Lesen
eingearbeitet. Ein Spec für das ganze Modell, gebaut in vier Phasen mit je
einem eigenen Plan (§1); er bleibt lebendig, bis die Seiten aller Phasen
stehen, und friert dann ein.

**Grundlage:** der Design-Record (`2026-10-01-previously-design.md`: Leitsätze
4, 5, 7 und 8, §5.3 Zuordnungen, §6 die zehn Entitäten, §6.1 Organisation und
Beteiligung), die Architektur (`2026-10-01-architektur.md`: §3 Glossar, §4.4
Projektionen), der Spec von Gate und Policy (`2026-10-09-pilot-gate-und-policy.md`,
„PG", §2.3), das MCP-Konzept (`2026-10-10-mcp-schnittstelle.md`, „K", §4.1,
§4.2–§4.3), der Spec der Feststellungen (`2026-10-12-pilot-feststellungen.md`,
„F", §1, §2.1, §3, §15), die Landkarte (*Feststellungen und Entitäten*), die
frühen Notizen in `NOTIZEN.md` (*Vorgang — Definition*, *Zerlegung*, *Ferne
Idee: Föderierte Wissensspeicher*), und die Prinzipien „Previously demands,
the environment provides" und „Previously ist die einzige Quelle des Zustands".

---

## 1. Zweck und Zuschnitt

Diese Einheit gibt Previously **Ordnung über den Inhalt**: was zu welchem
Projekt, Vorgang, Verein oder Kreis gehört, wer in welchem Zeitraum welches Amt
hatte, und was davon wer festgestellt hat. Sie ist der Zugang zum Protokoll
(„Wie steht Projekt X?", Design §1) und die Grundlage dafür, dass Quellen ohne
Adressen — Aufnahmen, Transkripte, Dateien — einem Kreis angehören können.

**Leitbeispiele des Betreuers**, an denen sich das Modell bewährt:

- **Vellenfeld.** Ein Verein, den der Betreuer gegründet hat; er war lange
  Obmann, dann Schriftführer, jetzt Kassier. Die Ämter wechseln, der Verein
  besteht. Der Vorstand ist ein Kreis mit Beginn und Ende, gewählt und neu
  gewählt in anderer Besetzung. `vorstand@` ist ein Verteiler, dessen
  Empfänger sich je Periode ändern. Weder Projekt noch Prozess, mit vielen
  Vorgängen und wechselnden Akteuren.
- **Markus** (F §15). Markus und der Betreuer sind im selben Verein und haben
  beide eine Firma; sie schreiben sich über die Firmenadressen zu Themen des
  Vereins. Die Zugehörigkeit folgt aus dem Thema, nicht aus der Adresse.
- **Der Caterer.** Ein Lieferant bestätigt dem Vorstand das Buffet für das
  Sommerfest, einmal über `vorstand@`, einmal direkt an eine private Adresse.

**Vier Phasen, ein Modell.** Das Modell muss in sich stimmig sein, deshalb ein
Spec; gebaut wird in Phasen, jede mit eigenem Plan, eigenem Merge, eigenem
Release und eigener Abnahme, und jede lässt das System lauffähig zurück
(Betreuer, 2026-10-13: „Zuschnitt passt"):

1. **Der Kern** (§3–§7): Deklarationen, Entitäten, Beziehungen, die drei
   Stufen der Verantwortung, die Projektion des Graphen. Am Gate ändert sich
   nichts.
2. **Zuordnung** (§8): Events und Einheiten an Klammern, die Chronik einer
   Klammer.
3. **Kreise im Graphen** (§9): Mitgliedschaft mit Zeitraum, das Gate liest
   aus dem Graphen. Die Sicherheitsgrenze, mit eigener, schwerer Prüfung.
4. **Verpflichtungen und Entscheidungen im Schema** (§11): erst nach den
   Erfahrungen aus 1–3.

Kreise kommen an dritter Stelle, obwohl sie das Fundament sind: Graph und
Zuordnung sind dann erprobt, bevor das Gate sie liest. Ein Fehler im Kern
kostet ein Release, einer im Gate gibt Inhalte frei. Damit Phase 1 kein Modell
festlegt, das für Kreise nicht passt, entwirft dieser Spec die Kreise
vollständig; nur ihr Bau kommt später. Der Betreuer wollte die Kreise
ausdrücklich in dieser Einheit und im Graphen, „um das sauber umzusetzen,
auch wenn es groß wird" (2026-10-13).

**Nicht in dieser Einheit:** die automatische Erkennung von Zuordnungen und
Lücken (Einheit 6, §7.6), der Identitätsgraph mit seinen Rückfragen zu
`name:` (F §2.1, §15), der Zugriff mehrerer Personen (§12), eine
Weboberfläche (§18), Benachrichtigungen, die zum Betreiber kommen (§7.5),
Föderation (§12).

---

## 2. Was ein Projekt ist — und warum der Kern es nicht weiß

Die Frage stand am Anfang: was ist ein Projekt, und gehört ein Event direkt
dazu oder nur über einen Vorgang?

**Die Definition aus der Wikipedia** — „ein zielgerichtetes, einmaliges
Vorhaben … um unter Berücksichtigung von Vorgaben wie Zeit, Ressourcen und
Qualität ein Ziel zu erreichen" — trifft nur einen Teil dessen, was Previously
begleiten soll. Vieles hat kein Ende: ein Verein, ein Hosting-Betrieb, ein
Wartungsvertrag, die laufende Arbeit mit dem Steuerberater. Wäre „Projekt"
der Oberbegriff, müsste man diese in eine Form biegen, die ihnen ein Ende
unterstellt. Vellenfeld ist weder Projekt noch Prozess.

**Wie andere es lösen** (aus dem Gedächtnis, nicht recherchiert; für diesen
Spec genügt es, Betreuer 2026-10-13):

- PARA (Tiago Forte) trennt *Projects* (Ziel und Frist, enden) von *Areas*
  (Verantwortungsbereich mit einem Standard, der gehalten wird, endet nie);
  GTD kennt *Areas of focus* über den Projekten.
- Die Schriftgutverwaltung (Aktenplan, DOMEA) ordnet Aktenplan → Akte →
  Vorgang → Dokument. **Dort ist der Vorgang die Ebene unter der Akte**, ein
  einzelner Geschäftsvorfall; die Architektur (§3) verwendet „Vorgang" als
  inhaltliche Klammer. Der Konflikt ist bewusst stehen gelassen: `matter` ist
  eine Art im Grundvokabular (§5), deren Beschriftung sich ändern lässt.
- Kanzleisoftware kennt Mandant → Mandat (*matter*), flach; Case Management
  (CMMN) trennt den Fall mit offenem Verlauf vom wiederholbaren Prozess.
  Previously begleitet Fälle, keine Prozessdefinitionen.
- Die Klassifikationslehre kennt Baum, Polyhierarchie und Facetten. Bäume
  scheitern an Design §5.3 — ein Satz gehört zu zwei Vorgängen —, deshalb ein
  Graph ohne Zyklen.

**Die Entscheidung:** Der Kern ist **generisch**, die Bedeutung liegt
**deklarativ** darüber (Betreuer, 2026-10-13: „eine Art Basis-Engine als
Runtime, die mit Deklarationen erst konkrete Bedeutung erhält"). Projekt,
Vorgang, Verein, Vorstand und Amt sind Arten in einem mitgelieferten
Vokabular, nicht Klassen im Code. Neue Bedeutung braucht kein Release, nur eine
Deklaration im Log.

**Die Gefahr ist bekannt** und hat einen Namen, den *Inner-Platform-Effekt*:
eine Deklarationsschicht, die wächst, bis sie eine schlechte
Programmiersprache ist. Eine DSL wird es nicht geben („da können wir gleich
Python schreiben", Betreuer). Die Linie:

- **Deklariert wird Vokabular:** Arten, Felder, welche Beziehung zwischen
  welchen Arten erlaubt ist.
- **Verhalten bleibt Code**, eine kleine, feste Menge (§3.2).
- **Eine Deklaration lockert nie die Policy** (§4.5). Das ist auch die
  Sicherheitsgrenze: sonst würde die Bedeutungsschicht zur Hintertür ins Gate.
- **Die Arten bleiben grob.** Zu spezifische Semantik macht das System
  unbedienbar (Betreuer).

**Direkt oder transitiv?** Beides, ohne Sonderfall: ein Event wird der
genauesten Klammer zugeordnet, die man kennt, und nach oben gilt die
Zugehörigkeit transitiv (§8). „Gehört zum Verein, welches Thema, weiß ich noch
nicht" ist dieselbe Zuordnung, nur gröber; eine neue Fassung verfeinert sie.

**Eine Klammer hilft beim Finden, sie entscheidet keine Tatsachen** (NOTIZEN,
*Korrektur der früheren Einschätzung*). Steht eine Mail im falschen Vorgang,
findet man sie dort, wo man sie nicht sucht — ärgerlich, aber schnell
korrigiert. Ob eine Frist gilt oder eine Rechnung bezahlt ist, darf deshalb nie
davon abhängen, zu welcher Klammer eine Mail gehört; das steht in der
Verpflichtung selbst. Weil eine falsche Zuordnung so wenig kostet, dürfen
Modelle zuordnen, ohne zu fragen (§7). Beim Gate kostet sie mehr, und dort
dürfen sie es nicht (§9).

---

## 3. Der Kern

### 3.1 Vier Begriffe

| deutsch | Bezeichner | was es ist |
|---|---|---|
| Entität | `entity` | ein Ding, über das Previously etwas weiß: ein Projekt, ein Verein, ein Amt. Es hat eine Art, Felder und Fassungen. |
| Beziehung | `relation` | eine Verbindung zwischen zwei Dingen, oder zwischen einer Mail und einem Ding: „gehört zu", „ist Mitglied von". Optional mit Zeitraum und Feldern, immer mit den Quellen, auf die sie sich stützt. |
| Deklaration | `declaration` | legt fest, welche Arten von Dingen und Verbindungen es gibt und welche Felder sie tragen. Sie steht als Handlung im Log. |
| Verhalten | `behavior` | eine Fähigkeit, die im Code programmiert ist, etwa „trägt nach oben" oder „hat einen Zeitraum". Eine Deklaration kann sie für ihre Art einschalten, aber keine neue erfinden. |

Die zehn Entitäten des Design-Records (§6) werden damit vom Code zum
**Grundvokabular** (§5).

**Ein Property Graph, keine Triples.** Knoten und Kanten tragen Felder. Drei
Wege standen zur Wahl (2026-10-13): Knoten und Kanten mit Feldern; reine
Triples wie RDF, in denen auch der Name eines Projekts eine Kante wäre; eine
Art je Entität im Code. Gewählt ist der erste (Betreuer: „A"). Ein Knoten ist
für den Menschen *ein* Eintrag, den man als Ganzes vorschlägt, freigibt und in
Fassungen ändert, wie eine Verpflichtung heute; mit reinen Triples wären
Umbenennen und Verschieben des Endes zwei Feststellungen, einzeln freigebbar,
und der Mensch sähe Bruchstücke. Kanten tragen, was RDF nur über Reifikation,
Named Graphs oder RDF-star kann: Zeitraum und Herkunft. Die dritte Art
widerspricht dem generischen Kern.

**Kein Triple Store.** Die Wahrheit ist das Log; der Graph ist eine Projektion
(Leitsatz 3), aus Feststellungen gefaltet und wegwerfbar. Ein Triple Store hält
Kanten als Wahrheit und ändert sie an Ort und Stelle; hier wird nur angefügt.

**Vokabular ausleihen, nicht Technik.** Wo es einen etablierten Begriff gibt,
wird er genommen (Betreuer: „gescheit"): die W3C Organization Ontology
(`org:Membership` mit `org:memberDuring`, `org:Post`, `org:holds`,
`org:postIn`), PROV-O für die Herkunft, SKOS für Begriffshierarchien, RDFS
`domain` und `range` für die erlaubten Verbindungen — ohne OWL, ohne
Schlussfolgern. Ein Knoten mit Feldern lässt sich verlustfrei als Triples
ausgeben; ein Export als JSON-LD ist damit eine spätere Möglichkeit, kein
Ziel (§18).

### 3.2 Verhalten im Code

| Verhalten | heißt |
|---|---|
| `transitive` | die Beziehung trägt nach oben: ein Event im Sommerfest gehört auch zum Verein |
| `acyclic` | die Beziehung verbietet Zyklen |
| `period` | die Beziehung oder Entität hat einen Gültigkeitszeitraum |
| `closable` | die Entität kann abgeschlossen werden |

Mehr nicht in dieser Einheit. Was das Gate berührt, ist kein Verhalten, sondern
an die eingebauten Arten `circle`, `member_of` und `in_circle` gebunden (§9).

### 3.3 Zwei Zeiten

Jede Feststellung hat `recorded_at`: wann Previously es erfahren hat. Ein
Zeitraum (`period`) ist, wann es *galt*. „Der Betreuer war 2015–2019 Obmann",
erfasst 2026, braucht beide. Damit lässt sich auch fragen, was Previously im
März über den Vorstand von 2019 wusste.

### 3.4 Speicher

**Relational, in PostgreSQL, mit einem Messpunkt.** Graphdatenbanken (Neo4j,
Memgraph, FalkorDB), RDF-Stores (Jena/Fuseki, Oxigraph) und Graphen in
PostgreSQL (Apache AGE, SQL/PGQ aus SQL:2023) wurden erwogen (2026-10-13,
ohne belegte Recherche; „die Grundlage reicht erstmal"). Die Abfragen hier sind
transitive Hüllen über eine Beziehung und Filter nach Stichtag; das trägt eine
rekursive Abfrage. Die Größe ist klein, Tausende bis Zehntausende Knoten. Und
das Gate muss in Phase 3 im selben Haus entscheiden: aus einer zweiten
Datenbank entschiede es aus einer Kopie, die hinterherhinken kann. Ein zweiter
Dienst bräuchte eine zweite Sicherung und einen zweiten Restore-Test und fiele
durch den Einfachheits-Check mit der Compose-Datei.

Weil der Graph eine Projektion ist, ist die Wahl umkehrbar. **Gemessen wird
bei 100 000 Beziehungen**: die transitive Hülle unter einem Knoten und die
Mitgliedschaft eines Kreises zu einem Stichtag. Erst wenn das nicht trägt, wird
ein anderer Speicher wieder Thema.

---

## 4. Deklarationen

### 4.1 Was eine Deklaration sagt

- **Zu einer Art von Entität:** einen festen Bezeichner, eine Beschriftung je
  Sprache, die Felder, das Verhalten.
- **Zu einer Art von Beziehung:** Bezeichner und Beschriftung; von welchen
  Arten sie ausgehen darf und zu welchen sie führt — „Event" ist als
  Ausgangspunkt erlaubt; ihre Felder, etwa die Rolle; ihr Verhalten.
- **Feldtypen**, eine feste kleine Menge: Text, Datum, Zeitraum, Auswahl aus
  festen Werten, Verweis auf eine Art. Keine berechneten Felder, keine
  Bedingungen.

Eine neuere Deklaration desselben Bezeichners ersetzt die ältere; was zu einem
Zeitpunkt galt, ergibt sich aus dem Log bis zu diesem Zeitpunkt (Betreuer: „man
weiß, zu welchem Zeitpunkt welche Deklaration gegolten hat").

### 4.2 Wer deklariert

Nur der Betreiber, auf der Kommandozeile. Ein Modell schlägt keine Deklaration
vor: Bedeutung festzulegen ist keine Feststellung über die Welt, sondern eine
Entscheidung über die Sprache, in der man sie beschreibt. Eine Oberfläche, die
das Vokabular und den Graphen sichtbar macht, braucht es später (§18).

### 4.3 Die Datei als Umweg, das Log als Wahrheit

Das Vokabular lässt sich als Datei bearbeiten, etwa `vocabulary.toml`:

- `previously vocabulary show` erzeugt sie aus dem Log, auch zu einem früheren
  Zeitpunkt.
- `previously vocabulary apply` vergleicht sie mit dem, was im Log gilt, zeigt
  jeden Unterschied — auch eine Änderung, die inzwischen jemand direkt gemacht
  hat — und schreibt nur die Änderungen als Deklarationen.

**Previously ist die einzige Quelle des Zustands** (Betreuer, 2026-10-13:
„außerhalb davon haben wir keinen gespeichert"). Die Datei ist kein zweiter
Speicher. Wer sie aufhebt, etwa in Git, hat eine Kopie, und das Log gewinnt
immer. Das Grundvokabular liefert das Release als eine solche Datei mit; es
wird nie stillschweigend eingespielt, sondern beim ersten `apply` oder nach
einem Update mit sichtbarem Unterschied.

### 4.4 Wenn sich eine Deklaration ändert

- **Geprüft wird beim Schreiben**, gegen die Deklaration, die in diesem Moment
  gilt. Was damals gültig geschrieben wurde, bleibt gültig.
- **Lesen zeigt alles.** Was zur heutigen Deklaration nicht mehr passt, wird
  markiert, nicht versteckt; `verify` meldet es als Hinweis, nicht als Fehler.
  In Ordnung gebracht wird es durch eine neue Fassung, nie durch Umschreiben.
- **Umbenennen** heißt, die Beschriftung zu ändern; der Bezeichner bleibt.
- **Stilllegen:** eine Art nimmt nichts Neues mehr an, Bestehendes bleibt.

### 4.5 Was nie deklarierbar ist

Jedes Verhalten, das das Gate berührt. Das Gate liest ausschließlich die
eingebauten Arten `circle`, `member_of` und `in_circle`, im Code festgelegt
(§9). Eine Deklaration kann keine neue Art mit Wirkung auf das Gate schaffen,
und sie kann eine eingebaute Art nicht so umdeklarieren, dass das Gate anders
entscheidet.

### 4.6 Bezeichner, Kennungen, Sprachen

- **Arten** haben einen selbst gewählten, festen Bezeichner, ASCII,
  unveränderlich (`project`, `member_of`). Er steht dort, wo Maschinen und
  Menschen ihn lesen: auf der Kommandozeile, über MCP, in der Abbildung auf
  `org:` und SKOS, im Code des Gates. Arten gibt es Dutzende, nicht Tausende.
- **Entitäten** haben keinen gewählten Namen, sondern die Kennung wie eine
  Verpflichtung heute: die Event-Id ihrer ersten Fassung,
  `previously://event/<id>` (F §3). Der Name ist ein Feld und darf sich
  ändern. UUIDs braucht es nicht (§12).
- **Beschriftungen** gibt es je Sprache: `label = { de = "Vorgang", en =
  "Matter" }`. Mehrsprachigkeit ist im europäischen Zusammenhang wichtig:
  „wenn ich in einem englischen Vorgang bin, möchte ich keine deutschen
  Begriffe haben, und umgekehrt" (Betreuer).
- **Gezeigt wird die Sprache des Zusammenhangs.** Eine Entität kann eine
  Arbeitssprache haben; innerhalb einer Klammer erscheinen die Begriffe in
  ihrer Sprache, sonst in einer Voreinstellung des Betreibers. Fehlt eine
  Beschriftung, wird auf eine vorhandene ausgewichen, sichtbar markiert. Das
  passt zum Log: die Sprache hängt an der Einheit, nicht am Dokument (Design
  §5).
- **Feldinhalte** — der Name eines Projekts — bleiben Inhalt, in der Sprache,
  in der sie entstehen. Übersetzungen von Inhalten sind nicht in dieser
  Einheit.

---

## 5. Das Grundvokabular

Mitgeliefert, deklariert und nicht programmiert, angelehnt an `org:` und SKOS.
Ein Anfang: „die Arbeit daran wird ein evolutionärer Job" (Betreuer).

**Entitäten:**

| Art | ist | Verhalten |
|---|---|---|
| `organization` | Firma, Verein, Behörde (Design §6.1) | — |
| `project` | Ziel, einmalig | `closable`, `period` |
| `matter` | Vorgang: eine zusammenhängende Klärung oder Abwicklung mit erkennbarem Anlass und erkennbarem Abschluss (NOTIZEN) | `closable`, `period` |
| `circle` | ein Kreis (eingebaut, §9) | — |
| `post` | ein Amt, etwa Kassier von Vellenfeld (`org:Post`) | — |
| `person` | ein Mensch | — |

**Beziehungen:**

| Art | von → zu | Verhalten |
|---|---|---|
| `part_of` | Vorgang, Projekt → Projekt, Organisation | `transitive`, `acyclic` |
| `concerns` | Event oder Einheiten → jede Klammer | — (die Zuordnung, §8) |
| `member_of` | Adresse, Domain, Person → Kreis | `period` (eingebaut, §9) |
| `in_circle` | Event → Kreis | — (eingebaut, §9) |
| `holds` | Person → Amt | `period` (`org:holds`) |
| `post_in` | Amt → Organisation | — (`org:postIn`) |
| `involved_in` | Person, Organisation, Kreis → Projekt, Vorgang | `period`, Feld `role` (Design §6.1, Beteiligung) |

`person` gibt es nur als Knoten, weil Ämter jemanden brauchen, der sie
innehat. Was den Identitätsgraphen ausmacht — `name:` zu einer Person
auflösen, die Rückfragen dazu, Adressen einer Person —, bleibt draußen (F §15).

---

## 6. Entitäten und Beziehungen als Feststellungen

### 6.1 Die Form

Alles, was Einheit 5 für Verpflichtungen gebaut hat, gilt: Fassungen,
Vorschlag und Freigabe, Ablehnung, Vorrang (§7), der Schreibweg mit Sperre und
Idempotenz, die Tilgungskaskade (F §3, §6, §8). Neu sind zwei Arten von
Feststellungen:

- **Eine Entität:** ihre Art, ihre Felder nach der geltenden Deklaration,
  optional eine Arbeitssprache, bei einer neuen Fassung wessen Fassung sie ist.
- **Eine Beziehung:** von wo — eine Entität, ein Event oder Einheiten eines
  Events —, welche Art, wohin — eine Entität —, optional ein Zeitraum mit
  offenen Enden („seit 2022"), ihre Felder.

### 6.2 Quellen oder Erinnerung

In Einheit 5 brauchte jede Feststellung Quellen. „Den Verein Vellenfeld gibt
es, ich habe ihn 2008 gegründet" hat keine Mail als Beleg. Der Design-Record
kennt dafür die Belegart `recollection` (Architektur §3, `evidence`):

- Eine Feststellung hat **Quellen oder** die Belegart `recollection`.
- `recollection` schreibt nur der Betreiber, direkt.
- Ein Modell braucht immer Quellen; es erinnert sich an nichts.

Das löst nebenbei den Fall aus der Abnahme von Einheit 5, in dem eine
Erfüllung nur festgestellt werden konnte und keine Beobachtung als Quelle
hatte (Landkarte). Ob `recollection` auch für Verpflichtungen und
Entscheidungen gilt, entscheidet Phase 4.

### 6.3 Beenden ist nicht Widerrufen

- **Beenden:** etwas galt und gilt nicht mehr — „Obmann bis 2019". Eine neue
  Fassung mit dem Ende des Zeitraums; die Beziehung bleibt wahr für ihre Zeit.
- **Widerrufen:** es war falsch — „diese Mail gehört doch nicht zum
  Sommerfest". Eine neue Fassung im Zustand `retracted`; sie verschwindet aus
  dem geltenden Graphen und bleibt in der Geschichte.

### 6.4 Geprüft beim Schreiben

Die Art ist deklariert und nicht stillgelegt; die Felder passen zu ihren
Typen; Ausgangs- und Zielart sind erlaubt; bei `acyclic` entsteht kein Zyklus.
Den Zyklus prüft der Schreibweg unter einer Sperre: zwei gleichzeitige
Schreibvorgänge, jeder für sich erlaubt, könnten sonst zusammen einen Kreis
schließen.

### 6.5 Tilgung

Wird ein Event oder eine Einheit getilgt, fallen die Zuordnungen, die von ihm
ausgehen, mit ihm, wie die Quellen in Einheit 5 (F §8). Eine Beziehung, die auf
eine getilgte Entität zeigt, bleibt in der Geschichte und wird als „zeigt auf
Getilgtes" markiert.

---

## 7. Verantwortung in drei Stufen

Die Beziehungen sollen am Ende von Modellen gefunden werden; der Betreuer kann
nicht jede verifizieren. Gefragt werden soll er nur, wenn die Unsicherheit eine
Schwelle überschreitet; korrigieren und bestätigen kann er immer (2026-10-13).
Damit wird die Linie aus Einheit 5 — ein Vorschlag eines Modells gilt erst nach
Freigabe — für Zuordnungen aufgegeben, und es kommt, was F §1 zurückgestellt
hat: **transitive Verantwortung mit Freigabeklassen.**

### 7.1 Drei Stufen

| Stufe | heißt | woher |
|---|---|---|
| `direct` | der Betreiber steht dafür | von ihm geschrieben oder freigegeben |
| `transitive` | der Betreiber steht dafür, weil er diese Klasse von Aussagen im Voraus erlaubt hat | ein Modell, unter einer Freigabeklasse |
| `open` | ein Vorschlag, niemand steht dafür | ein Modell ohne passende Klasse oder unter der Schwelle |

**Was gilt:** direkt vor transitiv vor offen, innerhalb einer Stufe die
neueste. Ein Modell ersetzt eine direkte Aussage nie, auch nicht unter einer
Klasse; sonst stünde im Protokoll etwas, wofür der Betreiber stehen soll und
das er nie gesehen hat.

### 7.2 Die Freigabeklasse

Eine Handlung des Betreibers im Log, wie eine Regel der Policy. Sie nennt den
Verfasser (etwa die innere KI mit einem bestimmten Modell, oder einen
MCP-Client), die Art von Aussage (etwa `concerns`), die Schwelle der Sicherheit
und optional einen Gültigkeitszeitraum. Ein Modell gibt jeder Aussage eine
Sicherheit mit (`confidence`, Architektur §3). Liegt sie über der Schwelle
einer passenden Klasse, gilt die Aussage `transitive` und nennt die Klasse;
sonst bleibt sie `open`.

**Eine Klasse zurückziehen** (Betreuer: „A wäre konsequent unserem üblichen
Vorgehen gegenüber"): die Aussagen darunter bleiben `transitive`, weil sie
gültig geschrieben wurden, und werden als „Klasse zurückgezogen" markiert;
sie lassen sich als Liste durchsehen und einzeln korrigieren. Beim
Zurückziehen kann der Betreiber wählen, alles darunter auf `open` zu setzen —
für eine Klasse, die von Anfang an Unsinn erzeugt hat. Auch das ist eine
Handlung im Log, die neue Fassungen erzeugt, und schreibt nichts um.

### 7.3 Eingreifen

- **Rückfrage.** Was offen ist, steht in einer Liste zum Klären
  (`list_triage`, `write_triage_answer`, K §4.2–§4.3). Ist etwas ganz unklar,
  rät das Modell nicht, sondern stellt eine Frage mit Kandidaten
  („Sommerfest oder Generalversammlung?"); die Antwort ist eine direkte
  Fassung.
- **Korrigieren**, jederzeit: eine direkte Fassung oder ein Widerruf. Sie
  schlägt das Transitive.
- **Bestätigen:** eine Freigabe wie in Einheit 5; sie hebt eine transitive
  oder offene Aussage auf `direct`.

### 7.4 Auch der Betreiber kann danebenliegen

Leitsatz 4 gilt für ihn selbst: mit neuen Informationen kann eine direkte
Aussage falsch werden (Betreuer: „ich kann ja auch danebenliegen, wenn ich
unvollständige Informationen habe; das müsste irgendwo sichtbar werden").
Zwei Fragen werden deshalb getrennt: **was gilt** — die direkte Aussage, bis er
sie ändert —, und **ob sie noch haltbar ist**.

- Ein Modell, das einer direkten Aussage mit neuen Belegen widerspricht,
  schreibt einen **Einwand**: einen Vorschlag auf diese Fassung, als Einwand
  gekennzeichnet, mit Quellen, die die Aussage nicht kannte.
- Ein Einwand geht **immer** an den Betreiber, unabhängig von der Sicherheit;
  gegen eine direkte Aussage kann eine Klasse nichts entscheiden, nur fragen.
- Die Aussage ist in jeder Liste **angefochten** markiert, mit Verweis auf den
  Einwand und seine Quellen — „angefochten durch 87, gestützt auf die Mail vom
  14. März". Wer das Protokoll liest, sieht, dass sie wackelt, bevor der
  Betreiber geantwortet hat.
- Nimmt er den Einwand an, wird er eine direkte Fassung; lehnt er ihn ab, mit
  Grund, verschwindet die Markierung. Beides bleibt in der Geschichte.
- Die Belegart steht an jeder Aussage: ruht die eigene auf `recollection` und
  der Einwand auf einer Mail, ist das ein Hinweis auf sein Gewicht. Gezeigt
  wird es, entschieden wird vom Betreiber.

### 7.5 Ein Einwand geht nicht unter

„Es darf nur nicht untergehen, wenn ein Modell einen Widerspruch findet —
zumindest brauche ich eine Benachrichtigung darüber" (Betreuer). In dieser
Einheit eine, die man abholt, aber im Alltag nicht verpasst:

- Einwände stehen **zuoberst** in der Liste der Rückfragen, auf der
  Kommandozeile und über MCP.
- Der **Kopf jedes MCP-Ergebnisses** zählt sie, etwa `· 2 objections
  pending`; wer mit Claude Code oder Vibe in Previously liest, sieht es, und
  das Modell kann darauf hinweisen.
- `previously status` zeigt dasselbe.

Eine Benachrichtigung, die zum Betreiber kommt — Mail, ntfy, Matrix, Webhook —,
ist ein eigener Schritt: sie braucht einen Kanal nach außen, und der ist eine
Forderung an die Umgebung (§18). Einwände gegen direkte Aussagen sind ihr
erster Anlass.

### 7.6 Grenzen

1. **Nie für das Gate.** Eine Zuordnung ist ein Zugangsweg; ein Irrtum
   versteckt oder zeigt eine Mail am falschen Ort. Eine Mitgliedschaft in einem
   Kreis entscheidet, welches Modell Inhalte sieht; ein Irrtum dort gibt
   Kundeninhalte frei. `member_of` und `in_circle` gelten nur `direct`, im Code
   festgelegt und von keiner Klasse erreichbar. Eine Zuordnung, die lockern
   würde, ist immer eine Rückfrage (§9.4).
2. **Nicht für Autorität.** Verpflichtungen und Entscheidungen bleiben
   Vorschläge, wie in Einheit 5, bis Phase 4 anders entscheidet.
3. **Die Sicherheit, die ein Modell angibt, ist schlecht kalibriert.** Eine
   Schwelle von 0,8 heißt nicht, dass 80 % stimmen. Die Korrekturen des
   Betreibers sind Messungen: jede direkte Fassung über einer transitiven ist
   ein gezählter Fehler, und das ergibt eine **Trefferquote je Klasse**. Dazu
   eine Stichprobe zum Prüfen. Die Schwelle wird nach Zahlen eingestellt.
   Fällt eine Klasse plötzlich durch ungewöhnlich viele Aussagen auf, zeigt die
   Quote es (§9.4).

**Was davon in diese Einheit gehört:** der Mechanismus — die dritte Stufe, die
Klassen, die Rückfragen, die Einwände, die Quote. Die **Erzeugung**, eine
innere KI, die Zuordnungen und Lücken nebenläufig findet, ist Einheit 6: „für
die Gaps brauchen wir neben der Auflistung auch eine Autoerkennung … da das
nebenläufig geschehen kann, ist Zeit nicht arg der Faktor; Fehler sind
erlaubt, wenn es nicht ganz schlimm ist — es muss freigegeben werden"
(Betreuer, 2026-10-13). Bis dahin kann ein MCP-Client unter einer Klasse
schreiben, wenn der Betreiber ihm eine gibt; so lässt sich der Mechanismus von
Hand erproben.

---

## 8. Zuordnung (Phase 2)

- **`concerns`** führt von einem Event oder von Einheiten eines Events zu einer
  Klammer, jeder Art. Die Einheit der Zuordnung ist der Abschnitt, nicht die
  Mail (NOTIZEN, *Zerlegung*; Design §5.2): „Absatz 2–4 gehören zum Change
  Request, Absatz 5 zur Rechnung". Heute sind Abschnitte die Einheiten, die die
  Aufnahme vergibt: der Betreff und die Absätze einer Mail (Spec der
  IMAP-Aufnahme, §3.2).
- **Menschen bleiben nicht bei einem Thema.** Markus schreibt zum Projekt XZ
  und am Ende „Ach übrigens, der Caterer hat zugesagt" — was sich nur aus dem
  Zusammenhang aufs Sommerfest des Vereins bezieht, nicht auf den Kunden XZ
  (Betreuer, 2026-10-14). „Menschen schreiben nicht brav zwei Mails", und in
  Transkripten und Chats erst recht nicht. Dann gehören die Einheiten über XZ
  zum Projekt und die letzte zum Sommerfest: zwei Zuordnungen in einem Event.
  Steht der Satz mitten in einem Absatz über XZ, ist die Einheit zu grob; dann
  wird der ganze Absatz beiden zugeordnet. Feinere Stücke — Zeichenbereiche,
  Zeitbereiche in einem Transkript (NOTIZEN, *Zerlegung*) — sind eine spätere
  Erweiterung (§18).
- **Eine Kante für die meisten Mails.** Die meisten Mails gehören als Ganzes
  zu einer Klammer: das ist eine Kante vom Event, und seine Einheiten erben sie
  (Betreuer, 2026-10-14). Eigene Kanten bekommen nur Einheiten, die abweichen.
  **Beim Finden ersetzt das Genauere das Allgemeine:** hat eine Einheit eigene
  Zuordnungen, gelten für sie nur diese; der Nachsatz über den Caterer steht im
  Protokoll des Sommerfests, nicht in dem von XZ. Wer ihn in beiden will, ordnet
  ihn beiden zu. Für das Gate gilt das nicht (§9.4).
- **Anhänge.** Ein PDF oder ein Word-Dokument ist heute ein Blob, sein Inhalt
  wird nicht gelesen; zuordnen lässt sich nur die Mail, die es trägt. Das ist
  ein echtes Problem — Kunden schicken die wichtige Information oft nur als
  Anhang (Betreuer, 2026-10-14) — und gehört in die Textextraktion (Landkarte,
  *Einwurf-Vertrag*), nicht in diese Einheit. Für dann gilt, wie bei einer Mail
  im Anhang (Spec der IMAP-Aufnahme, §3.6): ein gelesener Anhang wird ein
  eigenes Event mit eigenen Einheiten, das auf die Mail verweist, und bekommt
  eigene Zuordnungen — die Bestätigung des Caterers als PDF gehört zum
  Sommerfest, die Mail, die sie trägt, zu XZ. **Ein Anhang ohne eigene Adressen
  erbt die Kreise der Mail, mit der er kam**: er hat dieselben Absender und
  denselben Weg, und ohne die Regel wäre er ohne Kreis und damit nur lokal.
  Eine angehängte Mail hat eigene Adressen und eigene Kreise.
- **Der Zusammenhang kommt aus dem Graphen.** Dass „der Caterer" das
  Sommerfest meint, steht nicht im Satz: Markus ist im Verein und an XZ
  beteiligt, beim Verein ist ein Vorgang Sommerfest offen, und in dessen Mails
  kam ein Caterer vor. Die erkennende KI aus Einheit 6 bekommt ihre Kandidaten
  aus dem Graphen und entscheidet unter ihnen. Sie kann nur Klammern
  vorschlagen, die sie nach der Policy sehen darf.
- **Keine Partition** (Design §5.3): Lücken sind gewollt, Überschneidungen
  erlaubt.
- **Transitiv nach oben** über `part_of`: was zum Sommerfest gehört, gehört
  zum Verein.
- **Weitere Fundorte einer Mail** (Landkarte; Spec der IMAP-Aufnahme, §3.4): dieselbe Mail in
  einem zweiten Ordner schreibt heute nichts, nur der erste Fundort steht unter
  `found_in`. Mit den Zuordnungen wird das Ablegen selbst eine Zuordnung, auch
  mehrfach; ob die Aufnahme sie schreibt und unter welcher Stufe, legt der
  Plan von Phase 2 fest.
- **Markus:** die Mail kommt von seiner Firmenadresse; ihr Kreis ist seine
  Firma, ihre Zuordnung ist Verein › Thema. Die Klammer folgt dem Inhalt, der
  Kreis der Adresse — zwei Achsen, *wer* und *was*.

---

## 9. Kreise im Graphen (Phase 3)

Die Sicherheitsgrenze. Was hier steht, braucht in Phase 3 die schwerste
Prüfung dieser Einheit.

### 9.1 Was ein Kreis wird

Eine Entität der eingebauten Art `circle`. Mitglieder kommen über `member_of`
mit Zeitraum: Adressen, Domains, später Personen. `vorstand@` kann so je
Periode auf andere Empfänger zeigen.

### 9.2 Wem ein Event gehört

Den Kreisen, in denen seine Adressen **zum Zeitpunkt des Events** Mitglied
waren. Eigene Adressen zählen nie (wie heute, `circles_of` in
`core/decide.py`). Eine Adresse ohne Kreis wird übergangen; nur lokal ist ein
Event, das gar keinen Kreis hat oder einen Kreis ohne Regel — das bleibt wie
heute.

Das ist die erste Regel des Betreuers, auf die Verarbeitung angewandt: „nur die,
die sie 2019 sehen durften, dürfen sie auch 2026 sehen". Eine Mail an den
Vorstand von 2019 fällt unter die Mitgliedschaft von 2019. Ändert der Betreiber
eine Mitgliedschaft, entscheidet das Gate sofort neu, wie heute bei einer
geänderten Regel.

### 9.3 Quellen ohne Adressen

`in_circle` (Event → Kreis) stellt ein Event in einen Kreis: eine Aufnahme, ein
Transkript, eine Datei. Das kann Inhalte für ein Modell freigeben, und dafür
ist es da. Deshalb nur `direct`, nur vom Betreiber (§7.6).

### 9.4 Eine Klammer und das Gate

**Je Einheit, nicht je Event.** Die Kreise aus den Adressen gelten für das
ganze Event (§9.2). Die Kreise einer Klammer — die an ihr beteiligt sind, über
`involved_in` und die Klammern darüber — gelten nur für das, was ihr
zugeordnet ist: eine Zuordnung des ganzen Events für das ganze Event, eine
Zuordnung von Einheiten nur für diese Einheiten. Sonst brächte der Nachsatz
über den Caterer (§8) die Regel des Vorstands über die ganze Mail, und der Teil
über XZ verschwände vor einem Modell, das ihn sehen darf. Ein Platzhalter je
Einheit ist schon gebaut: eine getilgte Einheit steht heute als `[erased: …]`
mitten in einer sonst lesbaren Mail, eine zurückgehaltene stünde genauso da.
Das gilt auch umgekehrt: darf Vereinsinhalt nur lokal verarbeitet werden, geht
der Nachsatz nach seiner Zuordnung nicht mehr an ein Modell, das die Mails der
Firma sehen darf. **Vor der Zuordnung bleibt eine Lücke**, und sie lässt sich
nicht schließen: solange niemand weiß, dass der Satz zum Verein gehört, gilt
für ihn die Regel der Firma. Markus hat Vereinsinhalt über den Firmenkanal
geschickt; erst die Zuordnung erkennt es (Betreuer, 2026-10-14: „das macht es
zwar komplexer, aber die Realität ist so").

**Für das Gate wird nur hinzugefügt.** Hat eine Einheit eigene Zuordnungen,
behält sie für das Gate die Kreise der Zuordnung des ganzen Events und bekommt
die ihrer eigenen dazu. Fiele der Nachsatz aus XZ heraus und wäre XZ strenger,
würde er durch die Zuordnung eines Modells lockerer. Nur die direkte Zuordnung
des Betreibers kann das Allgemeine auch für das Gate ersetzen (unten).

**Die Metadaten gehören dem Event.** Kopfzeilen, Absender, Empfänger, Datum,
die Namen der Anhänge sind keine Einheit; der Betreff ist eine, Einheit 1. Für
die Metadaten gelten die Kreise des Events: die aus den Adressen und die aus
Zuordnungen des ganzen Events, nicht die einzelner Einheiten. Die Kopfzeilen
sagen, wer an wen geschrieben hat, und genau das beurteilen die Kreise aus den
Adressen; das Thema eines Absatzes ändert nichts daran. Ein Modell, das den
Nachsatz nicht sehen darf, sieht trotzdem, dass Markus an diesem Tag geschrieben
hat — das verrät nichts über den Verein.

**Die Herkunft wandert mit der Einheit.** Bei einer Mail steht der Absender
einmal im Event, und alle Einheiten teilen ihn; in Transkripten und Chats hat
jede Einheit ihren eigenen Sprecher und ihre eigene Zeit (Landkarte, *Andere
Quellen als Mail*). Eine Einheit ist nach diesen Regeln mindestens so streng
wie die Metadaten ihres Events, bis auf einen Fall: die direkte Zuordnung des
Betreibers lockert eine Einheit, deren Event nur lokal bleibt. Dann gilt: **wer
eine Einheit sehen darf, sieht, wer sie gesagt hat und wann**; die übrigen
Kopfzeilen — Empfänger, Kopie, die anderen Header — nicht (Betreuer,
2026-10-14). Eine Aussage ohne Sprecher ist wenig wert, und der Betreiber hat
diese Einheit wissentlich freigegeben.

Wie eine Zuordnung auf das Gate wirkt, hängt davon ab, wer zugeordnet hat:

- **Die direkte Zuordnung des Betreibers ordnet ein.** Sie stellt das
  Zugeordnete in die Kreise der Klammer und darf damit lockern, wie
  `in_circle`. Ohne sie bräuchte die private Mail des Caterers zwei Handgriffe
  für eine Absicht.
- **Eine transitive oder offene Zuordnung verschärft nur.** Die Kreise der
  Klammer kommen hinzu, es gilt die strengste Regel über alle, und der Zustand
  „ohne Kreis, nur lokal" bleibt in dieser Menge erhalten. Eine Zuordnung, die
  ein Modell schreibt, kann also nie freigeben. Würde sie lockern, wird sie
  eine Rückfrage an den Betreiber, egal wie sicher das Modell ist.

**Warum die Verschärfung bleibt, obwohl sie angreifbar ist.** Der Betreuer fragte,
ob eine einzelne Mail den Modellzugriff kastrieren kann (2026-10-13). Sie
kann es nicht: das Gate entscheidet je Event und, wo eine Klammer wirkt, je
Einheit; die Mail eines Unbekannten verschärft nur sich selbst. Der echte Angriff liegt tiefer: hat eine Klammer
einen strengen Kreis — einen Kunden mit „nur lokal" —, und bringt eine Mail mit
eingeschleusten Anweisungen ein Modell dazu, viele Events unter einer Klasse in
diese Klammer zu hängen, sind sie für das Modell des Betreibers nicht mehr
sichtbar. Das trifft die Verfügbarkeit, nicht die Vertraulichkeit. Ohne die
Verschärfung entstünde dagegen eine Lücke in der Vertraulichkeit: eine interne
Mail über das Projekt von Kunde A trägt keine Adresse von A und ginge an ein
Modell, obwohl A „nur lokal" verlangt — genau dafür ist Leitsatz 8 da.
**Vertraulichkeit vor Verfügbarkeit**, und damit es kein stiller Angriff wird:

- **Der Grund wird sichtbar.** Der Platzhalter sagt „zurückgehalten wegen der
  Klammer Projekt A, über Zuordnung 87".
- **Die Korrektur ist billig.** Ein Widerruf der Zuordnung hebt die
  Verschärfung sofort auf.
- **Die Trefferquote je Klasse** (§7.6) macht auffällig, wenn eine Klasse
  plötzlich ungewöhnlich viel zuordnet.

Die Alternative — nur direkte Zuordnungen verschärfen — schließt den Angriff
und öffnet die Lücke wieder für alles, was die innere KI zuordnet, und das wird
der größte Teil sein.

### 9.5 Der Caterer

- **An `vorstand@`:** auch die weitergeleitete Kopie trägt `vorstand@` im
  `To:`; sie gehört zum Kreis Vorstand, mit der Mitgliedschaft ihres
  Zeitpunkts, und es gilt dessen Regel. Ein Modell, das Vorstandsmails sehen
  darf, sieht sie und kann sie dem Sommerfest zuordnen.
- **Direkt an eine private Adresse:** die eigene Adresse zählt nicht, der
  Caterer hat keinen Kreis; die Mail bleibt nur lokal. Ein Modell bei einem
  Anbieter sieht sie nicht und kann sie nicht zuordnen; **ein lokales Modell
  darf sie lesen** und eine Zuordnung vorschlagen. Weil die lockern würde, wird
  sie eine Rückfrage: „Mail vom Caterer, gehört wohl zum Sommerfest —
  einordnen?" (Betreuer: „zumindest den Vorschlag und um Bestätigung bitten").
- **Bestätigt wird, wo der Inhalt sichtbar ist.** Die Rückfrage steht unter
  derselben Policy wie ihre Quellen; in Claude Code stünde sie als Platzhalter.
  Freigeben, was man nicht sieht, verweigert Previously schon heute
  (`write_approve` verlangt, dass der Client jede Quelle sehen darf). Bestätigt
  wird auf der Kommandozeile, oder mit einem Client über ein lokales Modell.
- **Einmal statt jedes Mal:** schreibt derselbe Absender öfter, kann die
  Rückfrage eine Mitgliedschaft vorschlagen — „`catering-xy.at` in den Kreis
  ‚Lieferanten Vellenfeld' aufnehmen?" —, direkt erst mit Bestätigung. Danach
  gehen künftige Mails ohne Rückfrage in den richtigen Kreis.
- **Was liegen bleibt, wird sichtbar:** eine Liste dessen, was nur lokal ist,
  weil es keinen Kreis hat, neben `previously policy gaps`. Die automatische
  Erkennung darin — ein lokales Modell, und eine einfache Regel wie „diese
  Domain kam schon in Mails vor, die zum Sommerfest gehören" — ist Einheit 6
  (§7.6).

### 9.6 Die bestehenden Kreise

Ihre heutigen Definitionen, Handlungen im Log mit Adressen und Domains
(`Membership` in `core/policy.py`), liest das Gate weiter, ohne Zeitraum, also
„schon immer". Ein Befehl schreibt sie einmalig als `member_of` in den
Graphen; danach lassen sich die alten Definitionen stilllegen. Das Log wird
nicht umgeschrieben, und zu keinem Zeitpunkt sieht ein Modell mehr als vorher
— das ist eine Zusicherung mit Test (§15).

### 9.7 Das Gate liest nichts, was hinterherhinkt

Das Gate darf Mitgliedschaften nicht aus einer Projektion lesen, die ein
asynchroner Lauf nachzieht: ein Mitglied, das der Betreiber gerade entfernt
hat, zählte sonst bis zum nächsten Lauf weiter, und das Gate gäbe in dieser
Zeit frei, was es nicht mehr darf. Entweder liest das Gate die Kreise aus dem
Log, oder ihre Projektion wird in derselben Transaktion fortgeschrieben, in der
die Mitgliedschaft geschrieben wird. Der Plan von Phase 3 entscheidet, welches
— nach Messung.

### 9.8 Die zweite und dritte Regel des Betreuers

Der Betreuer nannte drei Regeln (2026-10-13); die erste gilt in §9.2. Die
anderen betreffen Menschen, nicht Verarbeiter:

2. **Wer es sehen darf, kann es weitergeben.** Eine Mail von 2019 dem
   heutigen Vorstand zu zeigen, ist eine Freigabe mit Urheber und Zeitpunkt;
   wer sie nicht sehen durfte, kann sie nicht freigeben.
3. **Manches gehört dem Amt, nicht den Personen.** Ein Protokoll ist ein
   Dokument des Vorstands als Organ, und jeder spätere Vorstand erbt es — der
   Unterschied zwischen `org:Membership` und `org:Post`.

Previously kennt heute einen Menschen, den Betreiber; das Gate entscheidet,
welcher *Verarbeiter* etwas sehen darf. Beide Regeln setzen voraus, dass
mehrere Personen in Previously lesen. Diese Einheit bleibt bei einem Betreiber,
**ohne den Zugriff mehrerer Personen zu verbauen** (Betreuer: „A, aber B nicht
verbauen"; §12).

---

## 10. Lesen und Zugangswege

### 10.1 Projektionen

Zwei Tabellen, aus dem Log gefaltet und wegwerfbar: Entitäten (geltende
Fassung, Art, Felder, Arbeitssprache, Stufe) und Beziehungen (Subjekt, Art,
Objekt, Zeitraum, Stufe, die Feststellung, aus der sie stammt). Ob sie
gebraucht werden oder ob, wie in Einheit 5, das Falten beim Lesen trägt,
entscheidet die Messung (§3.4); der Plan von Phase 1 hält das als
Planentscheidung fest. Für das Gate gilt §9.7.

**`p_chronicle` bleibt.** Ist der Graph die letzte Projektion? Logisch fast:
ein Event ist ein Knoten, eine Zuordnung eine Kante zu ihm, und die Chronik
einer Klammer ist eine Abfrage über den Graphen. Physisch nicht: Projektionen
sind viele, jede für eine Art zu fragen gebaut — `p_chronicle` ist ein Index
nach **Zeit**, der Graph einer nach **Zugehörigkeit**, die Suche später einer
nach **Wörtern**. Eine einzige Projektion bediente jede Frage mittelmäßig.
`chronicle --in N` verbindet beide: der Graph liefert die Menge, die Chronik
die Ordnung (Betreuer: „dann behalten wir die Zeitachse"). Der alte Punkt, eine
Spalte `project` in `p_chronicle` (1b §10 Punkt 6), entfällt: ein Event gehört
zu mehreren Klammern, das ist eine Verknüpfung, keine Spalte.

### 10.2 Kommandozeile

- `previously vocabulary show|apply` (§4.3).
- `previously entity` und `previously relate` zum Schreiben;
  `previously entities` und `previously entity N` zum Lesen, mit `--history`.
- `previously chronicle --in N`: die Chronik einer Klammer, transitiv. Damit
  entsteht die Familie aus den frühen Notizen ohne eigenen Code: Vorgangs-,
  Projekt- und Organisationsprotokoll sind dieselbe Chronik mit einer anderen
  Klammer.
- `--at DATUM`: der Stichtag — „wer war am 1. März 2019 im Vorstand?".
- `previously triage` und `previously status` (§7.3, §7.5).
- Die Freigabeklassen (§7.2) und, in Phase 3, die Kreise im Graphen.

Die genauen Namen legt der Plan fest.

### 10.3 MCP

- Das Werkzeug `previously` bekommt **einen** Parameter `in`, der jede
  Klammer nimmt. `project` und `matter` waren reserviert (K §4.1), nie gebaut;
  da sie jetzt Arten eines Vokabulars sind, wäre es falsch, sie als Parameter
  zu zementieren (Betreuer: „`in` macht da mehr Sinn"). Es bricht nichts.
- `list_entities` zum Lesen; `write_entity` und `write_relation` in zwei
  Schritten wie `write_assertion` — ohne Klasse Vorschläge, mit Klasse
  transitiv.
- `list_triage` und `write_triage_answer` (K §4.2–§4.3).
- Der Kopf jedes Ergebnisses zählt offene Einwände (§7.5).

### 10.4 Das Gate in den Phasen 1 und 2

Unverändert. Eine Chronik nach Klammer filtert innerhalb dessen, was der
Client nach der Policy sehen darf; eine Zuordnung kann in diesen Phasen nichts
freigeben, nur finden. Eine Entität oder Beziehung, deren Quellen der Client
nicht sehen darf, erscheint als Platzhalter, wie eine Verpflichtung (F §7).

---

## 11. Verpflichtungen und Entscheidungen im Schema (Phase 4)

„Verpflichtungen und Entscheidungen müssen irgendwann konsequenterweise dem
Schema folgen; ob das gleich oder später einfacher umzusetzen ist, weiß ich
nicht" (Betreuer). Sie sind gebaut, abgenommen und laufen; der Umbau wartet auf
die Erfahrung aus den Phasen 1–3. Dieser Spec zeigt, wie sie aussähen, und
prüft damit, ob das Schema sie trägt:

- `obligation` und `decision` werden deklarierte Arten von Entitäten, mit den
  Feldern aus F §4 und §5 (Text, Frist, Zustand; Datum, `replaces`).
- Schuldner, Gläubiger und „entschieden von" werden Beziehungen zu Akteuren;
  die Verweise aus F §2.1 (`own`, `circle:`, `address:`, `name:`) bleiben als
  Feldwerte, bis der Identitätsgraph sie auflöst.
- Die Quellen, die Fassungen, die Freigabe und die Ablehnung sind schon
  dieselben (§6.1).
- Offen für Phase 4: ob `recollection` für sie gilt (§6.2), und ob eine Klasse
  je für sie gelten darf (§7.6, Punkt 2).

Weil Verpflichtungen schon heute Knoten mit Feldern sind, wäre Phase 4 ein
Umzug, kein Umbau. Das ist eines der Argumente für den Property Graph (§3.1).

---

## 12. Nicht verbauen

Was diese Einheit nicht baut, aber nicht unmöglich machen darf:

- **Der Zugriff mehrerer Personen** (§9.8): die Zugriffsentscheidung wird als
  Empfänger × Event × Zeitpunkt entworfen; ein Empfänger kann ein Modell, eine
  Person oder ein Speicher sein. Gebaut wird nur das Modell.
- **Freigaben mit Umfang und Gültigkeit**, für die Weitergabe an den heutigen
  Vorstand (Regel 2) und als Form eines späteren Tokens.
- **„Gehört dem Amt"** (Regel 3): eine Beziehung Event → `post`, die der
  Zugriff von Personen später liest.
- **Verweise, die einen Speicher nennen können.** `previously://event/41` sagt
  nicht, welcher Speicher gemeint ist. Das Format der Verweise auf Entitäten
  und Beziehungen wird so gewählt, dass ein fremder Speicher hineinpasst, auch
  wenn es nur den eigenen gibt. Hintergrund ist eine ferne Idee des Betreuers,
  föderierte Wissensspeicher (`NOTIZEN.md`), ausdrücklich nicht jetzt: „erst
  bleiben wir lokal und machen unser Basissystem".

---

## 13. Was das für den Betrieb heißt

- **Kein neuer Dienst.** Entitäten und Beziehungen sind Feststellungen,
  Deklarationen und Freigabeklassen sind Handlungen; das Log braucht keine
  Migration.
- **Projektionen**, falls die Messung sie verlangt (§10.1), baut der
  vorhandene `project`-Lauf, ohne neuen Job. Ihre Tabellen erzeugt der Code,
  nicht eine Migration (Architektur §4.4).
- **Das Grundvokabular** liegt im Paket; `previously vocabulary apply` im
  Werkzeug-Pod spielt es ein. Der Handoff an kup6s sagt es, und dass es nach
  einem Update mit neuem Vokabular wieder läuft.
- **Phase 3** ändert, wie das Gate entscheidet: der Handoff nennt den Befehl,
  der die bestehenden Kreise in den Graphen schreibt, und die Zusicherung, dass
  dabei kein Modell mehr sieht als vorher.
- **Die Werkzeugliste wächst** (§10.3); ihre Prüfsumme ändert sich, und Vibe
  muss seine Liste auffrischen.
- **docker-compose:** dasselbe — der `project`-Lauf als Cron-Zeile, ein `apply`
  nach dem Update, sonst nichts. **Der Einfachheits-Check hält:** ein Prozess,
  eine Datenbank, kein neuer Dienst.

---

## 14. Schnitt im Code

| Ort | Was |
|---|---|
| `core/` (neu) | Deklarationen: Form, Prüfung, Geltung zu einem Zeitpunkt |
| `core/` (neu) | Entitäten und Beziehungen: Form, Fassungen, Vorrang in drei Stufen, Prüfung |
| `core/` (neu) | Freigabeklassen, Einwände, Trefferquote |
| `core/assertions.py` | der Schreibweg: neue Arten, die Sperre für Zyklen |
| `core/redact.py`, `core/verify.py` | Kaskade und Form der neuen Arten |
| `core/decide.py` | Phase 3: Kreise aus dem Graphen, Zeitpunkt, Klammern je Einheit |
| `mcp_server/` | `in`, `list_entities`, `write_entity`, `write_relation`, `list_triage`, `write_triage_answer`, der Kopf |
| `cli.py` | `vocabulary`, `entity`, `relate`, `entities`, `chronicle --in`, `--at`, `triage`, `status` |
| Paket | das Grundvokabular als Datei |

Die genauen Namen und Grenzen legen die Pläne der Phasen fest.

---

## 15. Zusicherungen und Tests

Gegen echtes PostgreSQL; jede Zusicherung mit einem Test, der unter Mutation
rot gemessen wird, und einer grünen Kontrolle.

**Phase 1:**

1. **Deklaration zur Zeit:** eine Aussage wird gegen die Deklaration geprüft,
   die beim Schreiben gilt; eine spätere Änderung macht sie nicht ungültig,
   nur markiert.
2. **Keine Deklaration erreicht das Gate:** keine deklarierte Art, auch keine
   Umdeklaration einer eingebauten, ändert eine Entscheidung des Gates.
3. **Vorrang in drei Stufen:** direkt vor transitiv vor offen, innerhalb einer
   Stufe die neueste (Hypothesis über beliebige Folgen von Fassungen).
4. **Ein Modell ersetzt nie eine direkte Aussage**, auch nicht unter einer
   Klasse; sein Widerspruch wird ein Einwand und geht an den Betreiber.
5. **Klasse und Schwelle:** über der Schwelle `transitive` mit Verweis auf die
   Klasse, darunter `open`; nach dem Zurückziehen bleiben die Aussagen und sind
   markiert, mit der Wahl „alles auf offen".
6. **`recollection`** schreibt nur der Betreiber; ein Modell ohne Quellen
   schreibt nichts.
7. **Kein Zyklus**, auch nicht durch zwei gleichzeitige Schreibvorgänge.
8. **`apply` ist kein zweiter Speicher:** es schreibt nur Unterschiede, zeigt
   jede Abweichung zum Log, und `show` gibt wieder, was `apply` schrieb.

**Phase 2:**

9. **Transitiv:** die Chronik einer Klammer enthält, was darunter zugeordnet
   ist, und nichts von daneben; ein Widerruf nimmt es heraus.
10. **Das Genauere ersetzt das Allgemeine beim Finden:** eine Einheit mit
    eigener Zuordnung erscheint nur in deren Chronik, nicht in der der
    Zuordnung ihres Events.
11. **Die Chronik nach Klammer filtert innerhalb der Policy:** sie zeigt einem
    Client nichts, was er ohne `in` nicht sähe.

**Phase 3:**

12. **Mitgliedschaft zur Zeit des Events:** eine Mail von 2019 fällt unter die
    Mitgliedschaft von 2019, nicht unter die von heute.
13. **Eine Zuordnung durch ein Modell lockert nie:** ein Event ohne Kreis
    bleibt nur lokal, auch wenn es einer Klammer mit großzügiger Regel
    zugeordnet wird; eine Zuordnung, die lockern würde, wird eine Rückfrage.
14. **`member_of` und `in_circle` nur direkt:** keine Klasse, kein Modell
    erreicht sie.
15. **Die Umstellung der bestehenden Kreise gibt nichts frei:** für jedes Event
    entscheidet das Gate nach der Umstellung höchstens so großzügig wie
    vorher.
16. **Das Gate liest nichts, was hinterherhinkt:** eine entfernte
    Mitgliedschaft wirkt beim nächsten Aufruf, ohne dass ein Projektionslauf
    dazwischen liegt.
17. **Der Grund einer Verschärfung ist sichtbar:** der Platzhalter nennt die
    Klammer und die Zuordnung.
18. **Eine Klammer wirkt je Einheit:** ist eine Einheit einer Klammer mit
    strenger Regel zugeordnet, wird sie zurückgehalten und der Rest des Events
    nicht; eine Zuordnung des ganzen Events wirkt auf das ganze.
19. **Für das Gate wird nur hinzugefügt:** eine eigene Zuordnung einer
    Einheit durch ein Modell nimmt ihr keinen Kreis der Zuordnung des ganzen
    Events.
20. **Metadaten folgen dem Event:** eine Zuordnung einer Einheit ändert nicht,
    wer die Kopfzeilen sieht; wer eine vom Betreiber gelockerte Einheit sieht,
    sieht ihren Sprecher und ihre Zeit und keine weitere Kopfzeile.

---

## 16. Dokumentation

- **Explanation:** warum der Kern generisch ist und die Bedeutung deklariert
  (und wo die Linie gegen eine DSL liegt); warum ein Property Graph und kein
  Triple Store; warum drei Stufen der Verantwortung und warum ein Modell nie
  eine direkte Aussage ersetzt; warum eine Zuordnung durch ein Modell nur
  verschärft (Vertraulichkeit vor Verfügbarkeit); warum Mitgliedschaft zur
  Zeit des Events gilt.
- **Reference:** die Form einer Deklaration und der Vokabulardatei, das
  Grundvokabular, die Form von Entitäten und Beziehungen, die Kommandos, die
  Werkzeuge.
- **How-to:** ein Vokabular anpassen; einen Verein mit seinen Ämtern über die
  Jahre festhalten; Mails einer Klammer zuordnen und ihre Chronik lesen; eine
  Freigabeklasse einrichten und ihre Trefferquote lesen; Einwände und
  Rückfragen beantworten.
- `environment.md`: was neu von der Umgebung verlangt wird — in Phase 1
  nichts außer dem `apply`.
- Die Handoffs je Phase an kup6s, die Landkarte, und dieser Spec friert ein,
  wenn seine Seiten stehen.

---

## 17. Abnahme

Vom Betreuer, nach dem Merge der jeweiligen Phase:

1. **Vellenfeld** (Phase 1): der Verein, Gründung, Obmann, Schriftführer,
   Kassier, Vorstände mit Zeiträumen, auf der Kommandozeile; „wer war am
   1. März 2019 im Vorstand?" antwortet richtig; ein geändertes Vokabular
   deutet nichts Früheres um. Ein MCP-Client schlägt eine Entität vor, der
   Betreuer gibt sie frei.
2. **Markus** (Phase 2): eine Mail von Markus’ Firmenadresse wird dem
   Vereinsthema zugeordnet; `chronicle --in` zeigt das Thema und, eine Stufe
   höher, den Verein. Ein MCP-Client ordnet unter einer Freigabeklasse zu, der
   Betreuer korrigiert eine Zuordnung, die Trefferquote zählt es; ein Einwand
   gegen eine direkte Aussage erscheint zuoberst und im Kopf.
3. **Der Caterer** (Phase 3): die Bestätigung an `vorstand@` gehört zum Kreis
   Vorstand ihres Zeitpunkts; die direkt an eine private Adresse bleibt nur
   lokal, eine Zuordnung durch ein Modell lockert sie nicht, die des Betreuers
   ordnet sie ein. Eine Mail an den Vorstand von 2019 fällt unter dessen
   Mitgliedschaft. Die Mail von Markus zu XZ mit dem Nachsatz über den
   Caterer: der Nachsatz steht unter der Regel des Vorstands, der Rest unter
   der seiner Firma. Die bestehenden Kreise sind umgestellt, und kein Modell
   sieht mehr als vorher.

---

## 18. Was offen bleibt

Gepflegt, solange der Spec lebt; beim Einfrieren gehen die Punkte in die
Landkarte, je unter ihre Einheit.

- **Eine Weboberfläche**, um Vokabular und Graph zu visualisieren und die
  Lücken, Rückfragen und Freigaben zu bearbeiten: „nur per Kommandozeile wird
  das schnell unübersichtlich" (Betreuer, 2026-10-13). Nicht jetzt; Backlog.
- **Benachrichtigungen, die zum Betreiber kommen** (§7.5): Mail, ntfy, Matrix
  oder Webhook, als Forderung an die Umgebung; erster Anlass sind Einwände
  gegen direkte Aussagen.
- **Die automatische Erkennung** von Zuordnungen und Lücken, mit lokalem Modell
  und einfachen Regeln, nebenläufig: Einheit 6 (§7.6, §9.5).
- **Der Identitätsgraph** mit Rückfragen zu `name:` (F §15) und den Adressen
  einer Person; damit auch Personen als Mitglieder eines Kreises über ihre
  Adressen.
- **Der Zugriff mehrerer Personen** mit den Regeln 2 und 3 (§9.8, §12).
- **Föderierte Wissensspeicher** (`NOTIZEN.md`, §12).
- **Ein Export als RDF oder JSON-LD** (§3.1), wenn sich das Vokabular bewährt.
- **Ein anderer Speicher für den Graphen**, wenn die Messung bei 100 000
  Beziehungen nicht trägt (§3.4); eine belegte Recherche zu Graphdatenbanken
  steht aus.
- **Übersetzungen von Inhalten** (§4.6).
- **Feinere Stücke als eine Einheit** für die Zuordnung: Zeichenbereiche in
  einem Absatz, Zeitbereiche in einem Transkript (§8; NOTIZEN, *Zerlegung*).
  Bis dahin wird ein Absatz, der zwei Themen mischt, beiden zugeordnet.
- Ob ein Kreis umbenannt werden kann, ohne dass `circle:`-Verweise in
  Verpflichtungen ins Leere zeigen (F §15): mit Kreisen als Entitäten (§9.1)
  wird die Beschriftung änderbar und der Bezeichner fest; die Verweise aus
  Einheit 5 nennen aber den Namen. Phase 3 oder 4.
- Der Namenskonflikt „Vorgang" zwischen Architektur und Schriftgutverwaltung
  (§2), falls er in der Praxis stört.
