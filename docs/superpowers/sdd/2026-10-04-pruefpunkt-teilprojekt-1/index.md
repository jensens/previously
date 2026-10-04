# Prüfpunkt nach Teilprojekt 1 — gehalten am 2026-10-04, vor Stufe 1c

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-04.**
> Dieses Dokument und die Berichte daneben werden nicht nachgezogen. Sie halten
> fest, was an diesem Tag am Baum gemessen und daraus geschlossen wurde.
> Was davon weiterlebt — die Reihenfolge, das Zuhause jedes offenen Punkts —
> steht in der gepflegten [Landkarte](../../landkarte.md). Weicht sie später
> von diesem Dokument ab, gilt die Landkarte.

Die Architektur verlangt in §12.3 einen Prüfpunkt, **bevor** die Teilprojekte
2 bis 8 geplant werden, „mit Agenda, sonst wird er ein Ritual", und nennt fünf
Fragen. Sie setzt ihn nach den Stufen 1a, 1b und 1c an. Er wird hier früher
gehalten, nach 1a, 1b und dem äußeren Anker und **vor** 1c — auf Entscheidung
des Betreuers vom 2026-10-04: drei Ausführungen haben genug Material für die
fünf Fragen geliefert, und die Antwort entscheidet mit, ob 1c als Nächstes
kommt. Der Preis steht am Ende unter *Was dieser Prüfpunkt nicht geprüft hat*.

## Wie er entstanden ist

Drei Belegberichte, je von einem eigenen Agenten ohne Kenntnis der anderen
geschrieben, nur lesend und messend:

- [`bericht-a1-kernmodell-leitsaetze.md`](bericht-a1-kernmodell-leitsaetze.md)
  — Fragen 1 und 4, mit vier eigenen Messungen gegen PostgreSQL 17.
- [`bericht-a2-storage-und-offenes.md`](bericht-a2-storage-und-offenes.md)
  — Fragen 2 und 5.
- [`bericht-c-messung.md`](bericht-c-messung.md) — Frage 3, eine Messung bei
  10 000, 100 000 und 700 000 Events, mit allen Skripten und Rohausgaben.

Die Aufträge liegen als `brief-*.md` daneben. Jede Zeile der Berichte trägt
ihren Ort im Dokument und im Baum; Urteile sind dort als Urteile markiert.
Dieses Dokument ist die Zusammenführung durch den Controller: es zitiert die
Berichte, wiederholt sie nicht, und trennt ebenso, was belegt ist, von dem, was
daraus folgen soll. Sieben Behauptungen der Berichte hat der Controller am Baum
nachgeprüft, bevor er sie übernahm (das stumme Verwerfen in `append`, die
Felder von `RawEvent`, der Neubau an Ort und Stelle, die Methodenzahlen der
Protokolle, die Vorgabewerte der Kommandozeile, die `CHECK`-Zeile für `kind`,
das Fehlen von `pip-audit` und Renovate); alle sieben stimmten.

## Die fünf Fragen

### 1. Hat das Kernmodell den Kontakt überlebt?

**Den Kontakt hat es noch nicht gehabt.** Keine der zehn Entitäten ist gebaut,
keine Feststellung, keine Handlung. Was Kontakt hatte, ist die Schicht
darunter, und über sie lässt sich etwas sagen.

**Der Log hat überlebt, mit Korrekturen, die die Architektur nicht kannte.**
Der Bericht zählt 34 Unterschiede zwischen Entwurf und Baum (A1, erste
Tabelle). Die tragenden sind begründet und stehen auf Seiten: die `id` aus dem
Vorgänger statt aus einer Sequenz; `units_hash` und elf statt acht Felder im
Hash, weil drei gemessene Fälschungen sonst durch `verify` liefen; der
Nutzlastbereich; der Schnappschuss für die Kettenprüfung.

**Bei neun der 34 Zeilen fand der Bericht keinen aufgeschriebenen Grund**
(Zeilen 8, 10, 11, 12, 13, 16, 20, 30 und 34). Zeile 8 ist der schwerste
Befund und steht unten; Zeile 16 ist eine Kleinigkeit. Die übrigen liegen alle
an der Naht zum nächsten Teilprojekt:

- `RawEvent` hat kein `raw: bytes` und keine `channel_identities`, obwohl die
  Architektur beides in §6.2 nennt und die Rohbytes ausdrücklich mit Leitsatz
  6 begründet (A1 Zeile 12).
- `RawEvent.payload` steht in keinem Vertrag der Architektur (Zeile 13).
- `evidence` steht in der Nutzlast statt in einer Spalte; eine Tilgung nimmt
  die Belegart mit, und kein Dokument nennt das als Folge (Zeilen 10 und 11).
- Die Nutzlast wird nicht gegen ein Schema je Art geprüft (Zeile 20).
- Projektionen schreiben über je eigene getypte Methoden statt über ein
  generisches `write_projection` (Zeile 30).
- Die Kommandozeile setzt `occurred_at` auf „jetzt", wenn nichts angegeben ist
  (Zeile 34).

**Sieben Stellen, an denen die gebaute Schicht nicht zu dem passt, was der
Entwurf über ihr annimmt** (A1, S1 bis S7). Nach Gewicht:

1. **Ein geändertes Artefakt geht stumm verloren** (S7, Messung M1). Zwei
   `append`-Aufrufe mit demselben Schlüssel und verschiedenem Inhalt: der
   zweite gibt die alte `id` zurück, sein Inhalt steht nirgends, `verify`
   meldet nichts. Der 1a-Spec nennt als `external_id` die Issue-Nummer, der
   Entwurf nennt „ein Issue hat sich geändert" eine Wahrnehmung. Beides
   zusammen verliert jede Änderung nach der ersten. Das ist der eine Verlust,
   den der Entwurf „teuer" nennt, weil er nicht nachholbar ist — und er ist
   noch billig zu beheben, weil kein Konnektor existiert.
2. **Eine Feststellung passt nicht durch `append`** (S1): `kind` ist fest
   `observation`, Quelle und Belegart sind Pflicht. Der zweite Schreibweg, den
   der `LogStore` zulässt, hat keine Regeln: **`verify` ist artenblind** (S2,
   M3 und M4) — eine Feststellung ohne `sources` und eine Wahrnehmung ohne
   Belegart und ohne Schlüssel bestehen die Prüfung.
3. **`kind` heißt zweierlei** (S3): die Event-Art mit drei Werten, die im Hash
   steht, und die Unterart einer Feststellung oder Handlung, für die es keine
   Spalte und keinen festgelegten Schlüssel gibt.
4. **`p_obligation` passt nicht durch den Projektionsmechanismus**, wie die
   Architektur sie zeigt (S5): ob eine neue Feststellung die gespeicherte
   überschreiben darf, hängt an der `responsibility` der bisherigen, und die
   Spalte fehlt. Und der Satz des Entwurfs, Interpretation sei billig — „keine
   Migration, keine Schemaänderung" —, gilt für Bestandsdaten; eine **neue**
   Projektion kostet Methoden im Protokoll, ihre Umsetzung und eine Migration.
5. Die Verweise einer Feststellung auf Einheiten sind im Log ungeprüftes JSON
   (S4); die Tilgung trägt zwei Folgepflichten mehr, als die Architektur nennt
   (S6).

### 2. Ist die Storage-Schnittstelle noch schmal, oder ist SQL durchgesickert?

**SQL ist nicht durchgesickert. PostgreSQL-Semantik ist es.** (A2, Frage 2.)

Kein Modul oberhalb von `storage` baut eine Abfrage oder importiert
SQLAlchemy, und zwei Werkzeuge halten das gemeinsam: der import-linter und der
unbeschränkte Typparameter `Conn`. Gewachsen ist die Schnittstelle von 9
Methoden nach Stufe 1a auf 18 nach 1b und 19 nach dem Anker; in Protokollen
stehen davon 16 Plätze (`LogStore` 9, `ProjectionStore` 7), vier Lesemethoden
benutzt nur die Kommandozeile am konkreten `PostgresStorage` vorbei.

Von den fünf Eigenschaften, die die Schnittstelle laut Architektur §5 „bewusst
nicht haben darf", gelten zwei noch ganz:

| Eigenschaft | Stand |
|---|---|
| kein Update, kein Delete | gilt für `LogStore`; `ProjectionStore` hat beides |
| keine Transaktionssteuerung nach außen | **gilt nicht mehr**: `begin()` und `snapshot()` geben dem Aufrufer die Transaktionsgrenze, und `core` baut tragende Zusagen darauf |
| kein SQL-Durchlass | gilt |
| keine Rückgabe von Datenbankobjekten | gilt für Zeilen; die Verbindung selbst ist zur Laufzeit ein Datenbankobjekt, nur ihr Typ ist verborgen |

Keine Seite der Dokumentation begründet eine der fünf — `design-records.md`
sagt das selbst.

Worauf `core` baut, steht **nicht im Protokoll**, sondern in Docstrings der
einen Implementierung und in `previously.storage.errors`: dass `begin()`
`READ COMMITTED` gibt und `snapshot()` einen Schnappschuss; die Fehlerklassen,
an denen `append` seine Wiederholung aufhängt; dass Log und Projektionen eine
Verbindung teilen. Für eine einzige Implementierung ist das folgenlos. Es
drückt an drei Nähten, sobald weitergebaut wird: ein **zweiter Leser** (der
MCP-Server) braucht die Lesemethoden, die heute außerhalb jedes Protokolls
stehen; die **Suche** verbreitert `ProjectionStore` mit jeder Tabelle;
**Blobs** sind keine Datenbank-Transaktion, die geteilte Verbindung passt
nicht auf einen Objektspeicher.

### 3. Was hat die Projektionsmechanik wirklich gekostet?

**Bis heute hatte es niemand gemessen. Die Mechanik ist billig, wo es täglich
zählt, und ein Neubau ist eine Sache von Minuten.** (Bericht C; ein Container
`postgres:17` in Standardkonfiguration, Events von der Länge einer Mail, über
das `append` des Projekts in Stapeln von 500 geladen.)

Je Zelle der Median aus drei Läufen, beim Neubau dazu die Spanne:

| Events | Einheiten | Laden | Neubau beider Projektionen | Nachziehen von 1 000 | Kettenprüfung | Lesen |
|---|---|---|---|---|---|---|
| 10 000 | 73 631 | 871 Events/s | 3,8 s (3,4–3,8) | 0,63 s | 1,5 s | 0,28 s |
| 100 000 | 734 303 | 800 Events/s | 38,9 s (38,8–42,2) | 0,67 s | 12,5 s | 0,27 s |
| 700 000 | 5 137 856 | 710 Events/s | 388 s (312–416) | 0,74 s | 93,7 s | 0,28 s |

Größer wurde nicht gemessen: bis 700 000 dauerte das Laden gut sechzehn
Minuten, eine Million hätte rund 23 gebraucht. Der Entwurf rechnet mit
„einstelligen Millionen" über fünf Jahre (§12.1). Der Rechner war ein Laptop
unter Last; der Bericht nennt sie bei jeder Streuung.

- **Der Speicher bleibt flach.** 105 bis 108 MiB beim Neubau und 107 bis
  111 MiB bei der Kettenprüfung, bei 100 000 wie bei 700 000 Events. Die
  Forderung der Architektur, eine Reprojektion dürfe „nichts in den Speicher
  ziehen" (§5), hält.
- **Der Alltag ist billig.** 1 000 neue Events nachzuziehen dauert unter einer
  Sekunde, gleich wie groß das Log ist. Lesen dauert 0,27 bis 0,30 s, wovon
  0,20 s der Prozessstart sind.
- **Ein Neubau dauert bei 700 000 Events fünf bis sieben Minuten.** Ob er je
  Event mit der Größe teurer wird, ließ sich nicht entscheiden: gemessen ist
  der Faktor 1,4 zwischen 100 000 und 700 000, aber im selben Lauf wurde auch
  der Teil langsamer, der die Datenbank gar nicht berührt, um 1,31. Linear
  hochgerechnet — eine Hochrechnung, keine Messung — wären es bei fünf
  Millionen Events 32 bis 46 Minuten.
- **Die Zeit geht ins Schreiben und ins Lesen, nicht ins Ableiten.** 48 % des
  Neubaus schreibt die Chronik, 29 % liest das Log — und zwar zweimal, jede
  Projektion für sich —, 3 % ist das Ableiten in Python. Die Trennung von
  Ableiten und Schreiben, die Stufe 1b gebaut hat, kostet also nichts.
- **Die Kettenprüfung wächst linear**, etwa 13 s je 100 000 Events, zur Hälfte
  Hashen in Python, und hält ihren Schnappschuss so lange offen: bei 700 000
  Events 89 bis 112 s. Bei fünf Millionen wären es rund elf Minuten — bei
  **jedem** Lauf der Anker-Routine, denn sie geht jedes Mal das ganze Log ab.
  Das stand auf keiner Liste und ist ein neuer Punkt der Landkarte.
- **Der Text steht dreimal in der Datenbank**: in der Nutzlast, wie die
  Kommandozeile sie baut, in den Einheiten und in `p_chronicle`. Rund 1 GB
  Text ergeben 4,5 GB Datenbank; `p_chronicle` allein ist größer als die
  Tabelle der Einheiten.
- **Ein Bestandsimport dauert Stunden**: bei 700 Events in der Sekunde rund
  zwei Stunden für fünf Millionen Events.

**Was während eines Neubaus geschieht**, hat dieser Prüfpunkt als Erster
gemessen, bei 700 000 Events und mit einem zweiten Prozess, der fortlaufend
anhängt:

- **Der Eingang läuft weiter.** 6 379 Aufrufe von `append` während der 375 s
  des Neubaus, kein Fehler, kein `ProjectionGap`. Ein Aufruf dauert im Median
  14 ms statt 9 ms ohne Neubau; das 95. Perzentil steigt von 13 ms auf 86 ms,
  der längste einzelne Aufruf von 27 ms auf 1,4 s. Der Nachweis, den die
  Architektur für Stufe 1b nennt, gilt — er war nur nie erbracht worden.
- **Ein Leser sieht rund sechs Minuten lang eine halbe Projektion, und die
  Standardausgabe sieht dabei vollständig aus.** `chronicle` zeigt dieselben
  fünfzig frühesten Zeilen wie immer, weil der Neubau genau die zuerst baut.
  `stats` zeigt, sobald der Arbeiter bei dieser Projektion ankommt, Teilsummen
  — für `mail` 56 272 Events statt 497 429 — in vier Zeilen, die aussehen wie
  jede andere Ausgabe. Der einzige Hinweis ist die Rückstandszeile auf der
  Standardfehlerausgabe, „projection is 694605 events behind", im selben
  Wortlaut wie bei einem gewöhnlichen Rückstand; dass gerade neu gebaut wird,
  sagt sie nicht. Regel 4 der Architektur („Lesen sieht nie halbe
  Projektionen") gilt also nicht, und die Rückstandsmeldung ersetzt sie nur
  für den, der die Standardfehlerausgabe liest.
- **Das Ergebnis stimmt.** Nach dem Neubau und einem Nachziehen ist die
  Chronik Zeile für Zeile gleich einem Neubau von null auf demselben Log
  (5 214 291 Zeilen, gleiche Prüfsumme), und `stats` gibt byteweise dasselbe
  aus.

### 4. Steht jeder Leitsatz noch, oder wurde einer unter Druck gebogen?

**Fünf der neun hatten noch keinen Kontakt** — die Leitsätze 1, 2, 5, 7 und 8
regeln Dinge, die nicht gebaut sind (A1, Frage 4). Von den vier anderen:

| Leitsatz | Stand |
|---|---|
| 3 Append-only, jeder Zustand ist Projektion | hält im Gebauten. Die Tilgung ist die benannte Ausnahme, und sie ist seit 1b zwei Pflichten schwerer |
| 4 Wahrnehmungen können nicht falsch sein | hält: `append` weist Formen ab, nie Inhalte |
| 6 Im Zweifel mehr aufnehmen | **gebogen**: der Vertrag der Aufnahme ist schmaler als der der Architektur (keine Rohbytes, keine Kanalidentitäten), der Nutzlastbereich weist Mail-Header-Schlüssel, Bytes und Gleitkommazahlen ab, und geänderter Inhalt unter bekanntem Schlüssel wird verworfen |
| 9 Unentschiedenheit muss darstellbar sein | **gebogen an der Kommandozeile**: `--evidence` fällt auf `recollection`, `--occurred-at` auf „jetzt" — zwei Vermutungen, die als Tatsache im Hash stehen. Die erste ist begründet, die zweite nicht |

Beide Biegungen liegen am einzigen Einwurfweg, den es gibt, und beide sind
billig zu richten, solange nichts Echtes im Log steht.

### 5. Was aus §11 war doch tragend?

Die Architektur nennt diese Frage die wichtigste. Von den acht Zeilen in §11
war **eine tragend**, und eine zweite hat ihre Grenze verschoben (A2, Frage 5,
erste Tabelle):

- **„Deployment-Mechanismus: kein Modul hängt daran."** Der Anker hängt daran.
  Sein Schalter `--anchors -` existiert, weil ein Container die Datei sonst
  nicht erreicht; Ablageort, Intervall und Restore-Punkt sind
  Betriebsentscheidungen; und beide Löcher in der Restore-Logik kamen aus der
  Frage nach dem Betrieb. `CLAUDE.md` verlangt seit dem 2026-10-04 die
  Betriebsaussage in jedem Spec.
- **„ORM-Detailabbildung der Projektionen, innerhalb der Grenze aus §10.1."**
  Stufe 1b hat die Abbildung entschieden und dabei die Grenze verschoben:
  §10.1 sagt, Projektionstabellen würden von Code erzeugt und verworfen, nicht
  migriert; `0002_projections.py` migriert sie. Der 1b-Spec setzt das voraus,
  ohne §10.1 zu nennen.

Dazu, aus den anderen Listen: die Anforderungen an die **Tilgung** sind
gewachsen (Architektur §13); die Annahme „kein externer Compliance-Anlass"
(Entwurf §16) ist unbestätigt, und der Anker hat mit Ablageorten bei Dritten
schon Teile eines Drittbelegs vorweggenommen.

**Die größere Antwort liegt neben §11**: in dem, was die Architektur für
*entschieden* hielt. Von 35 geprüften Festlegungen (A2, zweite Tabelle) wurden
acht anders gebaut oder nicht gebaut, **ohne dass irgendwo ein Grund steht**.
Die eine ist die Migration der Projektionstabellen von eben; die anderen
sieben:

| Festlegung | gebaut |
|---|---|
| §7.3 Regel 3: Reprojektion in eine Schattentabelle, am Ende umschalten | Neubau an Ort und Stelle: leeren, dann in Stapeln füllen |
| §7.3 Regel 4: Lesen sieht nie halbe Projektionen | ein Leser sieht während des Neubaus eine leere oder halbe Projektion und bekommt den Rückstand gemeldet |
| §12.1, Nachweis für 1b: „Eingang läuft weiter" | von keinem Test gezeigt, in den Abnahmebedingungen von 1b nicht enthalten |
| §7.4: Kettenprüfung schlägt an → alles Schreiben anhalten | nur der Alarm |
| §5: `stream(project=…)` | nicht gebaut; der 1a-Spec schob es nach 1b, der 1b-Spec nennt es nicht |
| §10.6: `pip-audit` in der CI | nicht gebaut |
| §10.7: Renovate | nicht gebaut |

Keine davon ist heute ein Schaden. Aber es sind acht Stellen, an denen ein
eingefrorener Bericht etwas zusagt und der Baum etwas anderes tut, ohne dass
es eine Entscheidung war. Die erste, zweite und dritte hat dieser Prüfpunkt
nachgemessen; siehe Frage 3.

## Was auf keiner Liste stand

Die Überraschungen, die weder §11 noch §13 der Architektur noch §16 des
Entwurfs vorhergesehen haben (A2, letzter Abschnitt), in einem Satz je:

- **„Eine Transaktion" ist unter `READ COMMITTED` nicht „ein Zeitpunkt"** —
  zweimal hintereinander gefunden, bei der Rückstandszeile und bei der
  Kettenprüfung, dort mit 27 Fehlbefunden in 539 Läufen. Die Architektur legt
  die Isolationsstufe nur für das Schreiben fest.
- **Ein Tor, das nie feuern kann, ist ein Kommentar** — `ProjectionGap` konnte
  für eine echte Lücke nie auslösen.
- **Der Fehlervertrag der Kommandozeile**: eine unerwartete Ausnahme endet mit
  dem Rückgabecode eines Befunds.
- **Die Herkunft der Entscheidungen ist teilweise verloren**: kein
  `ruling`-Label im Baum löst auf, das Hauptbuch der Stufe 1a gibt es nicht
  mehr.
- Und dreimal etwas über die eigene Arbeitsweise, das jede weitere Stufe
  betrifft: Code im Plan wird auf jedem Weg ausgeführt, nicht nur gemessen;
  eine Prüfung nimmt ihren Maßstab nicht aus dem, was sie prüft; getippte
  Ausgabe altert, wo kein Tor sie hält.

## Was daraus folgt

**Für die Zerlegung.** Zwei Stücke, die das MVP braucht, stehen in keinem der
acht Teilprojekte: die **Feststellungen und Entitäten** — Teilprojekt 1
liefert in seinen drei Stufen nur die Mechanik, die Teilprojekte 5 und 7
setzen die Feststellungen schon voraus —, und der **Betrieb**. Die Landkarte
führt beide als eigene Einheiten.

**Für die nächste Einheit.** Der schwerste Einzelbefund ist keiner der oben
gezählten, sondern der, der sie alle erklärt: **das System hat noch kein
echtes Event gehalten.** Drei Stufen sind gegen Testdaten gebaut und geprüft;
fünf von neun Leitsätzen und alle zehn Entitäten sind ohne Kontakt. Die
Ausführung des Ankers hat an einem Tag gezeigt, was Benutzen findet und Lesen
nicht. Die Empfehlung dieses Prüfpunkts ist darum, die nächste Einheit so zu
schneiden, dass danach echte Daten hineingehen.

Zur Wahl standen drei Einheiten: der Einwurf (Vertrag, Einwurf per Prompt,
Pilotbetrieb), die Feststellungen (zweiter Schreibweg, Regeln je Art, das
Projekt als erste Entität), oder Stufe 1c, wie die Architektur sie als
Nächstes vorsieht. **Der Betreuer hat am 2026-10-04 den Einwurf gewählt.** Für
ihn spricht, dass er als einzige der drei Daten ins System bringt; dass der
Entwurf selbst die manuellen Pfade zuerst gebaut sehen will — „In der
umgekehrten Reihenfolge entsteht ein Vertrag, der nach Mail aussieht" (§11.4)
—; dass er die Entscheidungen
an der Aufnahme erzwingt, solange sie billig sind; und dass erst echte,
gemischtsprachige Einheiten die Messungen zur Suche möglich machen. Gegen ihn
spricht, dass personenbezogene Inhalte ins Log kommen, bevor es eine Tilgung
gibt — darum die Bedingung: zuerst eigene Notizen, Inhalte Dritter erst mit
der Tilgung.

Davor läuft eine kleine Wartungsrunde als eigener Pull-Request, ebenfalls am
2026-10-04 entschieden: `pip-audit`, Renovate, der Test Unterparser gegen
Dispatch-Tabelle, und `previously anchor` schreibt Befunde auf die
Standardfehlerausgabe.

**Für die acht unbegründeten Abweichungen.** Jede bekommt eine Entscheidung
statt eines Zustands: entweder der Baum folgt der Architektur, oder eine Seite
sagt, warum nicht. Die Landkarte führt sie bei ihrem Zuhause.

**Für die Storage-Schnittstelle.** Bevor ein zweiter Einstieg oder ein zweiter
Speicher dazukommt, schreibt das Protokoll aus, worauf `core` baut:
Isolation, Fehlerklassen, die geteilte Verbindung. Heute steht es in den
Docstrings der einen Implementierung.

## Was dieser Prüfpunkt nicht geprüft hat

- **Alles, was an Blobs hängt.** Stufe 1c ist nicht gebaut; die Vorkehrungen 2
  und 3 der Architektur für die Tilgung (§4.6) sind ungeprüft. Ein zweiter,
  kleiner Blick nach 1c gehört in dessen Abnahme.
- **Die zehn Entitäten.** Nichts ist gebaut; über sie sagt dieser Prüfpunkt
  nur, was die Schicht darunter ihnen abverlangt.
- **Die Tore.** Bericht A2 hat keine Tore gefahren und keine Datenbank
  gestartet; seine Typprobe zu `Conn` lief außerhalb der Projektkonfiguration.
- **Die Gründe der Stufe 1a.** Ihr Hauptbuch ist verloren. Wo ein Bericht
  „kein Grund gefunden" sagt, kann der Grund dort gestanden haben.
- **Die Vollständigkeit der Lehren aus dem Dokumentations-Protokoll.** Es hat
  keinen eigenen Abschnitt dafür; Bericht A2 hat nur gelesen, was das Hauptbuch
  selbst „Lehre" nennt.
