# Previously — Stufe 1c: Blobs und Tilgung

**Datum:** 2026-10-04
**Status:** Entwurf, vom Betreuer am 2026-10-04 durchgesehen; Grundlage des
Plans `docs/superpowers/plans/2026-10-04-stufe-1c-blobs-und-tilgung.md`

Detail-Spec für Teilprojekt 1, Stufe 1c (§12.1 der Architektur). Setzt die
Architektur (`2026-10-01-architektur.md`), die Stufen 1a und 1b und den
äußeren Anker voraus, und geht vom Prüfpunkt nach Teilprojekt 1 aus
(`docs/superpowers/sdd/2026-10-04-pruefpunkt-teilprojekt-1/`). Wo dieser Spec
eine frühere Festlegung ändert, steht es in §1.1.

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
seine offenen Punkte gehen dann in die Landkarte.

---

## 1. Zweck und Zuschnitt

Stufe 1c schließt Teilprojekt 1 ab. Sie kommt vor dem Piloten an einem echten
Kunden (Betreuer, 2026-10-04): gebraucht wird sie, wie auch immer der Pilot
ausgeht, und an echter Kundenpost wiegt schwer, was sie liefert — einen Ort
für Bytes und eine Tilgung, die ein Stück aus dem Log nimmt, ohne dass die
Kette bricht.

**Lieferungen:**

1. **Ein Blob-Speicher.** Inhaltsadressiert, clientseitig verschlüsselt, auf
   S3-kompatiblem Objektspeicher (§2).
2. **Das Hash-Format v=2**, in dem jede Einheit ihren eigenen Hash trägt und
   jeder Hash über Inhalt ein Salz (§3). Ohne das Erste ließe sich eine
   einzelne Einheit nicht tilgen, ohne den Rest des Events unprüfbar zu
   machen; ohne das Zweite ließe sich Getilgtes aus seinem Hash erraten.
3. **Die Tilgung**, als Event im Log: ein ganzes Event, einzelne Einheiten,
   oder ein Blob (§4). Der erste Schreibweg für eine andere Event-Art als
   `observation`.
4. **Die Prüfung dazu.** `verify` verlangt zu jedem Grabstein das
   Tilgungs-Event, das ihn anordnet, und zu jeder Anordnung den Vollzug; mit
   `--blobs` liest es die Blobs selbst (§5).
5. **Projektionen und Anzeige** folgen der Tilgung (§6).
6. **Zwei Kommandos und zwei Schalter:** `blob get` und `redact`;
   `append --attach` und `verify --blobs` (§2.5, §4.1, §5.3).
7. **Die Dokumentation dazu**, im selben Pull-Request (§10).

**Nicht enthalten:**

- **Die Suche.** Der 1b-Spec schob „Blobs und Suche" nach 1c (§1 dort). Die
  Suche braucht einen Messversuch an echten gemischtsprachigen Einheiten
  (Architektur §11, Nachtrag vom 2026-10-03), und die gibt es erst mit dem
  Piloten.
- **Ein Schlüssel je Betroffenem** und damit das Krypto-Schreddern. Die
  Architektur baut es ausdrücklich später (§4.6); die `key_id` an jedem
  Objekt hält den Weg offen.
- **Textextraktion aus Blobs.** Ein Blob ist in dieser Stufe ein Beleg, kein
  durchsuchbarer Inhalt.
- **Buckets, Zugangsdaten, Tresor.** §7 sagt, was diese Stufe dem Betrieb
  abverlangt, und baut nichts davon.
- **Aufräumen verwaister Blobs** (§12).

### 1.1 Was dieser Spec an früheren Festlegungen ändert

1. **Kein Dateisystem-Adapter (Architektur §10.3, §12.1).** Die Architektur
   sah ihn vor, „damit dort kein MinIO nötig ist". Gemessen am 2026-10-04: das
   Repository von MinIO ist archiviert, sein Image auf Docker Hub gibt es
   nicht mehr; die Tests brauchen für PostgreSQL ohnehin Docker. Gebaut wird
   **ein** Adapter, S3, und getestet wird er gegen einen echten
   S3-kompatiblen Server im Container (§8.3). Der Weg, der getestet wird, ist
   der Weg, der läuft. Das Protokoll `BlobStore` bleibt, sodass ein zweiter
   Adapter eine Ergänzung wäre und kein Umbau.
2. **`age` statt AES-GCM (Architektur §4.6, §10.3).** Die Architektur nennt
   „AES-GCM, Nonce im Objekt-Header". Verschlüsselt wird im Dateiformat `age`
   (§2.2): ein Standardformat statt eines eigenen, stückweise und damit ohne
   Größengrenze, und im Notfall mit einem verbreiteten Werkzeug lesbar, ohne
   diese Software. Der Grundsatz der Architektur bleibt — clientseitig,
   der Anbieter sieht den Schlüssel nie, und jeder Blob nennt seinen
   Schlüssel; wo er ihn nennt, ändert Punkt 8.
3. **`hash_version` (1a-Spec §3.1, §12).** Die Fassungsangabe je Zeile, dort
   „mit dem ersten v=2" vorgesehen, kommt jetzt (§3).
4. **`unit.content` wird `NULL`-fähig (1a-Spec §2, §3.1).** Stufe 1a kannte
   keine Tilgung von Einheiten, ließ die Spalte `NOT NULL` und nannte den Weg,
   der hier gegangen wird. Der 1b-Spec fand in §1.1 und §10 Punkt 2, dass eine
   Tilgung der Nutzlast die Einheiten stehen lässt.
5. **Die Tilgung ist ein Event (Architektur §4.6; 1a-Spec §3.1, §12).**
   Angekündigt seit Stufe 1a; hier gebaut. Dafür bekommt `core` einen zweiten
   Schreibweg neben `append` (§4.2). Der Prüfpunkt hat ihn für Feststellungen
   als fehlend geführt (Bericht A1, S1); dieser hier schreibt nur Handlungen,
   legt aber frei, was beide Wege an der Kette teilen.
6. **Der `payload_hash` bekommt in v=2 Fassung, Bereich und Salz** (§3). In
   v=1 ist er der SHA-256 der kanonischen Nutzlast und nichts sonst.
7. **Die Chronik-Projektion** verarbeitet künftig Tilgungs-Events und bekommt
   darum eine neue Version (§6). Die Vorgabe des 1b-Specs in §10 Punkt 2 ist
   damit eingelöst, und sein Test „Getilgtes Event" (§5.4 dort) wird bewusst
   geändert — er sagt selbst, dass das dann fällig ist.
8. **`key_id` steht am Objekt, nicht in der Referenz (Architektur §4.6,
   §10.3).** Die Architektur will in der Referenz „den tatsächlich verwendeten
   Schlüssel". Unter „erster gewinnt" kennt ihn der zweite Schreiber nicht: er
   lädt nicht hoch, und sein eigener Empfänger ist nach einem Schlüsselwechsel
   ein anderer als der, an den das liegende Objekt versiegelt ist. Laden zwei
   zugleich hoch, bleibt nur ein Chiffretext stehen, und der Verlierer hätte
   den falschen Schlüssel ins Log geschrieben (§2.7). Eine Referenz in der
   Nutzlast ist bezeugt und lässt sich nie berichtigen. Der Schlüssel ist eine
   Eigenschaft des Objekts und steht darum dort (§2.2).

---

## 2. Blobs

### 2.1 Adresse und Referenz

Ein Blob liegt unter dem **SHA-256 seines Klartexts**. Der Hash ist seine
Adresse im Speicher und sein Name im Log; derselbe Anhang fünfmal ist ein
Objekt.

Ein Event nennt seine Blobs in der Nutzlast, unter dem reservierten Namen
`blobs`, als Liste:

```
{"sha256": <hex>, "size": <Bytes>, "media_type": <…>, "filename": <… oder null>}
```

Damit deckt der `payload_hash` die Referenzen, und die Kette bezeugt, **welche**
Bytes zu einem Event gehören — nicht die Bytes, aber ihre Identität
(Architektur §10.3). `filename` gehört zur Verwendung, nicht zum Blob:
derselbe Inhalt kann in zwei Events zwei Namen tragen. Den Schlüssel nennt die
Referenz nicht; er steht am Objekt (§1.1 Punkt 8, §2.2).

Daneben steht jede Referenz in einer Tabelle `event_blob` (`event_id`,
`sha256`), damit sich fragen lässt, welche Events einen Blob benutzen (§4.1).
Die Tabelle ist ein Register und trägt keine eigene Wahrheit: `verify` hält
sie gegen die Nutzlast — und am getilgten Event, dessen Nutzlast fehlt, gegen
die Liste im Tilgungs-Event (§4.2, §5.2).

### 2.2 Verschlüsselung

Jeder Blob wird vor dem Hochladen im Format **`age`** verschlüsselt, an einen
X25519-Empfänger. Der Speicher sieht nur Chiffretext.

- **`key_id` ist der Empfänger** in seiner öffentlichen Schreibweise
  (`age1…`). Er sagt, an welchen Schlüssel ein Objekt versiegelt ist, und ist
  kein Geheimnis.
- **Er steht als Metadatum am Objekt**, in derselben Anfrage geschrieben wie
  der Chiffretext, und der Leser nimmt ihn von dort. Er ist ein Hinweis, kein
  Beweis: wer ihn fälscht, erreicht, dass sich das Objekt nicht öffnet — und
  wer das kann, kann es auch löschen.
- **Schreiben braucht nur den Empfänger, Lesen die Identität** (den geheimen
  Schlüssel). Ein Dienst, der nur aufnimmt, kommt ohne das Geheimnis aus.
- **Schlüsselwechsel:** ein neuer Empfänger für neue Objekte; alte bleiben
  lesbar, solange ihre Identität aufbewahrt wird. Ein Objekt, das schon liegt,
  bleibt an seinen alten Schlüssel versiegelt, auch wenn ein neues Event
  darauf zeigt.
- **Stückweise, mit begrenztem Speicher, und darum ohne Größengrenze.** Die
  Messung steht in §2.6.
- **Die Adresse wird beim Lesen geprüft.** `age` bindet den Chiffretext nicht
  an die Adresse; also rechnet der Leser den SHA-256 des Klartexts mit und
  vergleicht ihn am Ende. Stimmt er nicht, ist das Gelesene zu verwerfen —
  wer in eine Datei liest, schreibt in eine vorläufige und benennt sie erst
  nach der Prüfung um.

**Woher die Schlüssel kommen**, steht hinter einer schmalen Naht: `key_id`
hinein, Identität heraus; und für das Schreiben der aktuelle Empfänger. In
dieser Stufe liest die eine Umsetzung Identitäten aus Dateien in einem
Verzeichnis. Das ist die Form, in der Kubernetes ein eingehängtes Secret
zeigt. Ein Tresor mit eigener Schlüsselverwaltung wäre eine zweite Umsetzung
hinter derselben Naht.

### 2.3 Speicher

Ein Protokoll `BlobStore` in `contract`, eine Umsetzung in `storage` für S3:

```python
class BlobStore(Protocol):
    def stat(self, address: str) -> StoredBlob | None: ...
    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None: ...
    def get(self, address: str) -> tuple[StoredBlob, ByteSource] | None: ...
    def delete(self, address: str) -> None: ...
```

Der Speicher bekommt und gibt **nur Chiffretext**; versiegelt und geöffnet
wird in `core`. `stat` sagt, ob ein Objekt liegt und an welche `key_id` es
versiegelt ist. `get` liefert Metadatum und Datenstrom aus **einer** Antwort:
zwei Anfragen könnten, während ein Objekt ersetzt wird, den Schlüssel des
einen und den Inhalt des anderen sehen (§2.7).

- **Erster gewinnt** (Architektur §4.6). Vor dem Hochladen fragt der
  Schreibweg, ob das Objekt liegt, und lädt dann nicht. Das ist Nachsehen und
  dann Handeln, kein Schloss; was dazwischen geschehen kann und was es
  kostet, steht in §2.7.
- **Zwei Durchgänge über die Quelle.** Die Adresse ist der Hash des Klartexts
  und muss vor dem Hochladen feststehen: erst hashen, dann versiegeln und
  hochladen. Die Quelle muss sich darum zweimal lesen lassen; eine Datei kann
  das.
- **Versiegelt wird in eine Zwischendatei**, hochgeladen aus ihr. Das ist der
  gemessene Weg (§2.6), und er kostet vorübergehend Plattenplatz in der Größe
  des Blobs. Ob es ohne sie geht, misst der Plan; zugesagt ist begrenzter
  Speicher, nicht kein Plattenplatz.
- **Löschen löscht, und zweimal Löschen ist kein Fehler.** Auf dem Bucket
  laufen weder Versionierung noch Object Lock (Architektur §4.6, Vorkehrung 3;
  §7).

### 2.4 Ein Blob am Event

`RawEvent` bekommt `blobs: tuple[BlobRef, ...]`, wobei `BlobRef` die vier
Felder aus §2.1 trägt. Wer ein Event mit Anhang einwirft, **speichert erst den
Blob und fügt dann das Event an**. Schlägt das Anfügen fehl, bleibt ein Blob
ohne Event zurück — harmlos, weil niemand auf ihn zeigt, und in §12 als
offener Punkt geführt.

`append` mischt die Referenzen unter dem Namen `blobs` in die Nutzlast, wie
`evidence`, weist eine Nutzlast ab, die den Namen schon trägt, und schreibt
die Zeilen in `event_blob` in derselben Transaktion wie das Event.

### 2.5 Kommandos

- **`previously append … --attach DATEI`**, mehrfach erlaubt. Speichert jede
  Datei als Blob und hängt die Referenzen an das Event. `media_type` kommt aus
  dem Dateinamen, sonst `application/octet-stream`; geraten aus dem Inhalt
  wird nicht.
- **`previously blob get HASH --output DATEI`.** Holt, öffnet, prüft die
  Adresse und schreibt die Datei. Auf die Standardausgabe schreibt das
  Kommando keine Bytes. Ist der Blob getilgt, sagt es das und nennt das
  Tilgungs-Event; Rückgabecode 1, wie `show` bei einem Event, das es nicht
  gibt.

Was diese Kommandos an Angaben brauchen, steht in §7. Alle Kommandos, die es
heute gibt, laufen ohne sie weiter.

### 2.6 Gemessen am 2026-10-04

Vor diesem Spec, mit Wegwerf-Skripten, auf der Entwicklungsmaschine:

- **`pyrage` 1.4.0 allein**, Datei zu Datei: 41 MiB in der Spitze bei 16 MiB,
  256 MiB und 1 GiB; 1 GiB in 1,0 s versiegelt und in 1,3 s geöffnet.
- **AES-GCM in einem Stück** zum Vergleich: rund das Dreifache der Blobgröße
  im Speicher (793 MiB für 256 MiB, 3,1 GiB für 1 GiB), und bei 2³¹−1 Bytes
  hart Schluss.
- **Der ganze Weg**, RustFS 1.0.1 im Container, `boto3` 1.43.108: versiegeln
  in eine Zwischendatei, hochladen, wieder holen, aus dem Datenstrom öffnen
  und dabei die Adresse mitrechnen. Spitze **90 MiB bei 16 MiB, 183 MiB bei
  256 MiB und 183 MiB bei 1 GiB** — ein Sockel und die Puffer des Hochladens
  in Teilen, keine Funktion der Größe. 1 GiB: 1,0 s versiegeln, 2,9 s
  hochladen, 2,5 s holen und öffnen. Die Adresse stimmte jedes Mal.
- **Der Speicher:** ein frischer Bucket hat keine Versionierung; nach dem
  Löschen antwortet er mit 404, ohne Version und ohne Löschmarke; ein zweites
  Löschen ist kein Fehler. Der Container steht in unter einer Sekunde.
- **Eine falsche Identität** öffnet nichts: `DecryptError`.

**Nicht gemessen:** der Notfallweg mit dem Werkzeug `age` selbst — es ist auf
der Entwicklungsmaschine nicht installiert. Er ist Abnahmebedingung 14.

### 2.7 Zwei Schreiber zugleich

„Erster gewinnt" ist Nachsehen und dann Handeln, und dazwischen liegt die
Zeit, die Versiegeln und Hochladen dauern. Wollen zwei Schreiber denselben
neuen Inhalt zur selben Zeit ablegen, sehen beide nichts liegen, und beide
laden hoch.

Gemessen am 2026-10-04 an RustFS 1.0.1, zwanzig Durchgänge mit 64 MiB. Die
zwei Chiffretexte waren an verschiedene Empfänger versiegelt, damit sich
sagen lässt, welcher stehen blieb, und ein Leser holte das Objekt währenddessen
in einer Schleife:

- **Das Objekt ist nie zerrissen.** Jedes Mal blieb genau einer der beiden
  Chiffretexte stehen, ganz — zwölfmal der eine, achtmal der andere —, und er
  öffnete sich zur Adresse.
- **Das Metadatum gehört zum Chiffretext**, in allen zwanzig Durchgängen:
  `key_id` und Inhalt werden zusammen ersetzt. Darum steht der Schlüssel dort
  und nicht in der Referenz (§1.1 Punkt 8) — die des Verlierers bliebe sonst
  für immer falsch.
- **Ein Leser, der gerade liest, während das zweite Hochladen das Objekt
  ersetzt, bekommt einen Fehler**, keine falschen Bytes: in neunzehn der
  zwanzig Durchgänge brach sein Lesen ab. Hinter dem Abbruch stünde noch die
  Prüfung der Adresse. Ein zweiter Versuch gelingt.

Was daraus folgt:

- Beide Events entstehen und zeigen auf dasselbe Objekt. `verify --blobs`
  meldet nichts.
- Der Schaden ist ein abgebrochenes Lesen, und es trifft nur einen Leser, der
  einen Inhalt in dem Augenblick holt, in dem er zum ersten Mal und gleich
  zweimal abgelegt wird.
- **Schließen ließe sich das Fenster mit einem bedingten Schreiben**
  (`If-None-Match: *`). RustFS kennt es: ein zweites `PutObject` wurde mit
  `PreconditionFailed` abgewiesen. Das Hochladen in Teilen von `boto3`
  1.43.108 reicht es nicht durch — es weist `IfNoneMatch` als Argument ab —,
  und ob Hetzner es kennt, ist nicht gemessen. Der Entwurf braucht es nicht
  und baut es nicht; offener Punkt (§12).

**Der Preis von „erster gewinnt"**, auch ohne Wettlauf: der Schreiber vertraut
dem, was liegt. Prüfen kann er es nicht — er hat keine Identität. Liegt unter
einer Adresse ein beschädigtes Objekt, zeigt jedes spätere Event mit diesem
Inhalt darauf, und erst `verify --blobs` meldet es. Ersetzen heißt heute, das
Objekt von Hand zu löschen und den Inhalt neu abzulegen; offener Punkt (§12).

Der dritte Wettlauf, Aufnehmen gegen Tilgen, steht in §12 Punkt 2.

---

## 3. Das Hash-Format v=2

### 3.1 Warum: zwei Gründe

**Erstens: eine Einheit allein.** In v=1 steht der Inhalt aller Einheiten
eines Events gemeinsam in einem Hash: `units_hash` ist der SHA-256 über
**eine** kanonische Form, die jede Einheit mit ihrem Inhalt enthält. Fehlt der
Inhalt einer Einheit, lässt sich der Hash nicht nachrechnen, und die übrigen
Einheiten des Events wären lesbar, aber nicht mehr bezeugt.

**Zweitens: was stehen bleibt, verrät, was fehlt.** Eine Tilgung lässt die
Hashes stehen; daran hängt die Kette. Ein Hash über kurzen Inhalt lässt sich
aber durchprobieren. Gemessen am 2026-10-04, ein Kern, reines Python: 1,7
Millionen Kandidaten in der Sekunde; eine Einheit, die aus einer Telefonnummer
mit sieben unbekannten Ziffern besteht, war nach 0,72 s aus ihrem Hash
zurückgewonnen. Getilgt wird gerade solcher Inhalt — ein Name, eine Nummer,
ein kurzer Satz. Eine Tilgung, die ihn erratbar zurücklässt, ist keine.

Dagegen hilft ein **Salz**: 32 zufällige Bytes, die in den Hash eingehen und
**mit dem Inhalt getilgt werden**. Solange der Inhalt steht, braucht die
Prüfung das Salz und hat es; ist er getilgt, fehlt dem Ratenden die Hälfte der
Eingabe. Nachrüsten lässt sich das nicht: ein Hash ohne Salz bleibt für immer
einer.

### 3.2 Die Form

- **Der Hash der Nutzlast:** SHA-256 über die kanonische Form von
  `{"v": 2, "domain": "previously/payload", "salt": <hex>, "payload": {…}}`.
  Das Salz steht in einer neuen Spalte `event.payload_salt`.
- **Der Hash einer Einheit:** SHA-256 über die kanonische Form von
  `{"v": 2, "domain": "previously/unit", "salt": <hex>, "seq", "content",
  "start_ms", "end_ms", "speaker"}`. Er steht in `unit.digest`, sein Salz in
  `unit.salt`.
- **`units_hash`:** SHA-256 über die kanonische Form von
  `{"v": 2, "domain": "previously/units", "units": [<Hash je Einheit, hex,
  aufsteigend nach seq>]}`. Der Bereich ist der von v=1.
- **Der Event-Hash** trägt in seinem Kopf `"v": 2`; Bereich und Felder sind
  die von v=1.
- **`event.hash_version`**, `smallint NOT NULL DEFAULT 1`, sagt der Prüfung,
  welche Form sie nachrechnet. Der Vorgabewert trägt für jede Altzeile die
  richtige Angabe ein, ohne dass ein Hash neu zu rechnen wäre (1a-Spec §3.1).
  Wer die Spalte fälscht, bricht den Hash: die Fassung steht auch im gehashten
  Kopf.

Ein Salz muss niemand bezeugen: es ist Eingabe des Hashs, und ein gefälschtes
bricht ihn.

### 3.3 Alt und neu nebeneinander

- **Geschrieben wird nur noch v=2.**
- **v=1 bleibt prüfbar**, für immer. Der festgenagelte Hash-Vektor in
  `tests/test_hashing.py` bleibt, wie er ist; ein zweiter für v=2 kommt
  daneben, mit denselben deutschen Eingaben und festen Salzen.
- **Ein Event in v=1 lässt sich nur ganz tilgen** (§4.4), und seine Hashes
  bleiben ohne Salz erratbar. Blobs trägt es keine.

Ein Log mit echten Daten gibt es bis heute nicht. Das neue Format kostet darum
keine Altdaten außer denen der Tests — es gab nie einen billigeren Moment.

---

## 4. Tilgung

### 4.1 Drei Ziele

```
previously redact event  ID            --reason TEXT
previously redact units  ID SEQ [SEQ…] --reason TEXT
previously redact blob   HASH          --reason TEXT
```

| Ziel | Was verschwindet | Was bleibt |
|---|---|---|
| **Ein Event** | die Nutzlast mit ihrem Salz, darin auch die Belegart (`evidence`) und die Dateinamen; Inhalt, Sprecher, Zeitmarken und Salz aller Einheiten; jeder Blob, auf den danach keine ungetilgte Referenz mehr zeigt | alle Hashes; `id`, `kind`, beide Zeiten; der Quellschlüssel `(source, external_id)`; die Zeilen der Einheiten als Grabsteine; die Zeilen in `event_blob` |
| **Einheiten** | Inhalt, Sprecher, Zeitmarken und Salz der genannten Einheiten | ihre `seq` und ihr Hash; alles andere am Event |
| **Ein Blob** | das Objekt im Speicher, für **jedes** Event, das ihn zu diesem Zeitpunkt benutzt | die Referenzen in Nutzlast und Register: der Hash als Beleg, dass dort etwas war |

**Wann ein Blob im Speicher zu liegen hat**, folgt aus einer Regel, und
`redact` wie `verify --blobs` rechnen nach ihr:

> Eine Referenz (Event, Blob) ist **getilgt**, wenn das Event ganz getilgt
> ist oder eine Blob-Tilgung das Event nennt. Ein Blob liegt im Speicher,
> solange mindestens eine seiner Referenzen nicht getilgt ist.

Daraus folgt, ohne Sonderfall:

- **Ein geteilter Blob bleibt stehen, wenn eines seiner Events getilgt
  wird**, und das Kommando nennt ihn und die anderen Events. Derselbe Anhang
  hängt an zwei Mails, und das Tilgen der einen soll die andere nicht
  beschädigen. Wer den Inhalt überall loswerden will, tilgt den Blob.
- **Wird das letzte Event getilgt, geht der Blob mit.**
- **Kommt derselbe Inhalt nach einer Blob-Tilgung wieder herein**, an einem
  neuen Event, liegt er wieder da — die Tilgung nannte dieses Event nicht.

Dazu zwei Grenzen des Kommandos:

- **Die Nutzlast lässt sich nicht teilweise tilgen.** Sie steht unter einem
  Hash. Steht das zu Tilgende in der Nutzlast — ein Dateiname, eine Adresse —,
  ist das Ziel das Event.
- **`--reason` ist Pflicht** und steht für immer im Log. Er darf nicht
  enthalten, was getilgt wird; das Kommando kann das nicht prüfen, die
  Anleitung sagt es.

Das Kommando sagt, was es getilgt hat, mit der `id` des Tilgungs-Events. Eine
Rückfrage stellt es nicht: es ist ein Werkzeug für Skripte und Menschen
zugleich, und die Begründung ist die Bremse.

### 4.2 Das Tilgungs-Event

Ein Event der Art `action`, ohne Quellschlüssel und ohne Einheiten, mit der
Nutzlast:

```
{"action": "redaction",
 "scope":  "event" | "units" | "blob",
 "target": {"event": <id>, "blobs": [<hex>…]}
         | {"event": <id>, "units": [<seq>…]}
         | {"blob": <hex>, "events": [<id>…]},
 "reason": <Text>}
```

- **Die Unterart steht in der Nutzlast unter dem Namen der Art.** `event.kind`
  hat drei Werte und bleibt so; was für eine Handlung es ist, sagt
  `payload.action`. Der Prüfpunkt fand, dass die Unterart keinen festgelegten
  Ort hat (Bericht A1, S3); für Handlungen ist er das ab jetzt. Für
  Feststellungen entscheidet es deren Spec, mit diesem Muster vor Augen.
- **Ein getilgtes Event nennt seine Blobs im Tilgungs-Event.** Die Nutzlast,
  die sie bezeugt hat, fehlt danach; die Liste hält bezeugt fest, worauf das
  Event zeigte.
- **Genannt wird nur, was diese Tilgung neu tilgt.** Eine Einheit, die schon
  ein Grabstein ist, überspringt das Kommando und sagt es.
- **`occurred_at` ist `recorded_at`.** Eine Handlung des Systems geschieht,
  wenn sie verzeichnet wird.
- **Geschrieben wird es über einen eigenen Weg in `core`**, nicht über
  `append`: `append` nimmt Wahrnehmungen von Quellen entgegen. Beide Wege
  teilen sich, was die Kette betrifft — Spitze lesen, hashen, bei besetzter
  Position wiederholen.
- **Ein Tilgungs-Event lässt sich nicht tilgen.** Seine Nutzlast ist, woran
  die Prüfung die Grabsteine misst.

### 4.3 Ablauf

1. In **einer** Transaktion: das Ziel prüfen (es existiert; es ist kein
   Tilgungs-Event; bei Einheiten ist das Event v=2), das Tilgungs-Event
   anfügen, die Grabsteine setzen. Die Zeile des Ziels ist dabei gesperrt,
   damit zwei Tilgungen desselben Ziels nacheinander laufen und die zweite
   sieht, was die erste getan hat.
2. **Danach** jeden Blob löschen, der nach der Regel aus §4.1 nicht mehr zu
   liegen hat. Der Speicher nimmt an keiner Datenbank-Transaktion teil.
3. **Zuletzt** die Projektionen nachziehen, auf dem Weg von `project`. Bis
   dahin zeigt die Chronik das Getilgte noch; im gewöhnlichen Betrieb ist das
   weniger als eine Sekunde (Prüfpunkt, Bericht C: 1.000 Events nachziehen).

Scheitert Schritt 2 oder 3, endet das Kommando mit Rückgabecode 2 und sagt,
was noch aussteht. **Ein zweiter Aufruf mit demselben Ziel holt es nach** und
schreibt kein zweites Event.

Ein Ziel, das schon ganz getilgt ist und nichts mehr aussteht: das Kommando
sagt es, nennt das Tilgungs-Event, und endet mit 0, ohne etwas zu schreiben.

### 4.4 Ein Event in v=1

Es lässt sich ganz tilgen, nicht in Teilen: `redact units` weist es mit einem
Satz ab, der sagt, warum. Nach einer ganzen Tilgung prüft `verify` an ihm
keine Einheiten mehr; es gibt nichts, wogegen. Das ist der Übersprung, den der
1a-Spec in §3.1 vorgesehen hat.

### 4.5 Was eine Tilgung nicht leistet

- **Die Sicherungen.** Was getilgt ist, steht in jeder Sicherung der
  Datenbank und im WAL-Archiv, bis deren Aufbewahrungsfrist abläuft. Die
  Zusage einer Tilgung ist darum so lang wie diese Frist; §7 und die
  Anleitung sagen das.
- **Eine Wiederherstellung bringt Getilgtes zurück.** Wer auf einen Stand
  vor einer Tilgung zurückgeht, hat den Inhalt wieder und das Tilgungs-Event
  nicht mehr. Für Blobs fällt es auf: der Speicher geht nicht mit zurück, und
  `verify --blobs` meldet sie als fehlend. Für Nutzlast und Einheiten fällt
  es nicht auf. Die Tilgungen seit dem Stand sind zu wiederholen, und woher
  man sie dann kennt, ist ein offener Punkt (§12).
- **Die Hashes bleiben.** Mit Salz lässt sich Getilgtes nicht mehr erraten
  und nicht einmal mehr bestätigen. Die Adresse eines Blobs trägt kein Salz —
  sie ist der Hash des Klartexts, damit derselbe Inhalt ein Objekt ist. Wer
  die Datei schon besitzt, kann belegen, dass sie im Log stand.
- **Der Quellschlüssel.** `source` und `external_id` stehen im Event-Hash und
  bleiben. Eine Message-ID trägt eine Domain; wer das nicht stehen lassen
  kann, kann es nicht tilgen, ohne die Kette zu brechen. Offener Punkt (§12).
- **Was abgeleitet wurde.** Projektionen folgen (§6); was außerhalb liegt —
  eine Ausgabe in einem Terminal, eine Kopie in einem Fremdsystem —, erreicht
  keine Tilgung.

Die Anker dagegen bleiben gültig: alle Event-Hashes stehen.

---

## 5. Prüfung

### 5.1 Grabstein und Anordnung

Bis heute ist ein Grabstein von einer Fälschung nicht zu unterscheiden
(1a-Spec §3.1). Ab dieser Stufe verlangt `verify` **beides**, Anordnung und
Vollzug:

| Befund | wann |
|---|---|
| `payload is erased without a redaction` | Nutzlast `NULL`, und kein Tilgungs-Event nennt das Event |
| `unit <seq> is erased without a redaction` | Einheit ohne Inhalt, und kein Tilgungs-Event nennt sie oder ihr Event |
| `redaction of event <id> is not carried out` | das genannte Event trägt noch Nutzlast oder Inhalt |
| `redaction of unit <seq> of event <id> is not carried out` | die genannte Einheit trägt noch Inhalt |
| `redaction names a target that does not exist` | das Event steht nicht vor dem Tilgungs-Event in der Kette, oder es hat die Einheit nicht |
| `units are erased in part, which version 1 cannot attest` | Teil-Grabsteine, wo es keine Hashes je Einheit gibt |

Die ersten beiden und der letzte stehen unter der `id` des Events mit dem
Grabstein, die übrigen unter der des Tilgungs-Events. Der Wortlaut gilt: die
Reference zitiert ihn, und der Test hält das Zitat gegen den Code.

**Vollzogen heißt: Inhalt und Salz fehlen.** Dass kein Salz neben einem
Grabstein stehen bleibt, erzwingt die Datenbank mit je einer Bedingung an
`event` und `unit`; eine halbe Tilgung lässt sich darum nicht schreiben, und
`verify` muss sie nicht melden.

Geprüft wird im selben Durchlauf: er merkt sich Grabsteine und Anordnungen
und gleicht sie am Ende ab, wie er es mit den Ankern tut. Ein Tilgungs-Event
steht in der Kette immer **nach** seinem Ziel.

### 5.2 Arten, Fassungen, Register

- **Eine Einheit in v=2** wird gegen ihren `digest` gerechnet, wenn sie Inhalt
  trägt (`unit <seq> does not match its digest`); `units_hash` wird aus den
  `digest` gerechnet, ob getilgt oder nicht. Eine Zeile zu viel oder zu wenig
  fällt darum auch am ganz getilgten Event auf.
- **Eine Fassung, die die Prüfung nicht kennt**, ist ein Befund
  (`hash_version <n> is not known`) und kein Abbruch.
- **Ein Event der Art `action`** muss `payload.action` tragen; eine
  `redaction` zusätzlich `scope`, `target` und `reason` in der Form aus §4.2.
  Sonst: `action has no valid form`. Das ist die erste Regel je Art in
  `verify`; der Prüfpunkt hat gemessen, dass es bis hierher keine gab
  (Bericht A1, S2).
- **`event_blob` gegen die Nutzlast:** jede Zeile hat ihre Referenz in
  `payload.blobs` und umgekehrt; am getilgten Event gilt dasselbe gegen die
  Liste im Tilgungs-Event. Sonst: `blob register does not match the payload`.

### 5.3 `verify --blobs`

Ohne den Schalter fasst `verify` keinen Blob an. Mit ihm liest es jeden, der
nach der Regel aus §4.1 zu liegen hat, und fragt nach jedem, der es nicht hat:

| Befund | wann |
|---|---|
| `blob <hex> is missing` | hat zu liegen, liegt nicht |
| `blob <hex> does not match its address` | öffnet sich, aber der SHA-256 des Klartexts ist ein anderer |
| `blob <hex> cannot be opened` | keine Identität für die `key_id` am Objekt, oder der Chiffretext ist beschädigt |
| `blob <hex> is erased and still present` | hat nicht zu liegen, liegt aber |

Jeder steht unter der `id` des ersten Events, das den Blob nennt. Der
Klartext wird dabei nicht gespeichert, nur gehasht.

Der Schalter liest alle Bytes; das ist eine Prüfung für die Nacht, nicht für
jeden Lauf der Anker-Routine.

---

## 6. Projektionen und Anzeige

- **Die Chronik zeigt Getilgtes nicht.** Die Projektion `chronicle` liest
  Tilgungs-Events und nimmt die Zeilen des Ziels heraus; beim Neubau erzeugt
  sie für eine Einheit ohne Inhalt keine Zeile. Die Lücke in der Nummerierung
  bleibt sichtbar. Ihre Version steigt, und der erste `project` nach dem
  Einspielen baut neu. Das ist das erste Mal, dass eine Projektion Zeilen
  löscht; `ProjectionStore` bekommt dafür eine Methode.
- **Inkrementell gleich neu gebaut** gilt weiter, auch mit Tilgungen
  dazwischen, und gleich, ob der Arbeiter ein Event vor oder nach seiner
  Tilgung liest; der zentrale Test aus Stufe 1b bekommt beide Fälle.
- **`source-stats` ändert sich nicht.** Sie zählt die Zeilen der Einheiten,
  und die bleiben als Grabsteine. `units` heißt damit „je aufgenommene
  Einheiten", getilgte eingeschlossen; die Reference sagt es. Der Satz im
  1b-Spec §3.3 — korrekt, weil keine Zeile verschwindet — gilt weiter, und
  die Sorge aus §10 Punkt 2 dort tritt nicht ein. Ein Tilgungs-Event hat
  keinen Quellschlüssel und zählt nicht.
- **`show`** nennt jeden Grabstein und das Event, das ihn angeordnet hat, und
  zeigt die Blobs eines Events mit Hash, Größe, Name und Zustand.
- **Ein Tilgungs-Event hat keine Einheiten** und erscheint darum nicht in der
  Chronik. `log` zeigt es; `show` zeigt seine Nutzlast.

---

## 7. Was das für den Betrieb heißt

- **kup6s.** Ein Bucket bei Hetzner Object Storage, **ohne Versionierung und
  ohne Object Lock** — sonst löscht Löschen nicht. Eigene Zugangsdaten nur für
  diesen Bucket; den Bucket der Datenbank-Sicherung erreicht die Anwendung
  nicht (Architektur §10.3). Die Identität kommt über External Secrets aus
  einem Tresor, der **nicht** dort gesichert wird, wo die Blobs liegen
  (Architektur §4.6), und wird als Verzeichnis eingehängt. Gebaut wird das mit
  dem Betrieb des Piloten.
- **Ein Host mit `docker-compose`.** Ein S3-kompatibler Dienst als weiterer
  Container, ein Verzeichnis mit der Identität. Das ist **ein bewegliches Teil
  mehr** als ein Verzeichnis auf der Platte, und es ist der Preis dafür, nur
  einen Adapter zu bauen.
- **Plattenplatz für die Zwischendatei.** Wer Anhänge aufnimmt, braucht
  vorübergehend Platz in der Größe des größten Blobs (§2.3).
- **Schlüsselverlust ist Totalverlust** der Blobs. Die Identität ist eine
  Zeile Text; sie wird getrennt von den Daten gesichert, und die Anleitung
  sagt, wie man die Sicherung probt: einen Blob mit dem Werkzeug `age` und
  der gesicherten Identität öffnen.
- **Die Aufbewahrungsfrist der Sicherungen ist Teil der Tilgungszusage**
  (§4.5). Wer Tilgung binnen einer Frist zusagt, wählt die Aufbewahrung
  danach.
- **Nach einer Wiederherstellung** gehört `verify --blobs` zur Routine, und
  die Frage, welche Tilgungen zu wiederholen sind (§4.5).

**Angaben**, aus der Umgebung, neben `PREVIOUSLY_DSN`:

| Variable | Wozu | Wer sie braucht |
|---|---|---|
| `PREVIOUSLY_BLOB_ENDPOINT`, `…_REGION`, `…_BUCKET`, `…_ACCESS_KEY`, `…_SECRET_KEY` | der Speicher | `append --attach`, `blob get`, `verify --blobs`, und `redact`, wenn am Ziel Blobs hängen |
| `PREVIOUSLY_BLOB_RECIPIENT` | der Empfänger für neue Blobs | `append --attach` |
| `PREVIOUSLY_BLOB_IDENTITIES` | das Verzeichnis der Identitäten | `blob get`, `verify --blobs` |

**Der Einfachheits-Check:** sieben Angaben und ein Dienst mehr. Er findet,
dass nur zwei Kommandos das Geheimnis der Blobs brauchen — holen und prüfen.
Aufnehmen kommt mit dem öffentlichen Empfänger aus und Tilgen ganz ohne
Schlüssel, und das ist die Trennung, die man im Betrieb haben will.

---

## 8. Schnitt im Code

### 8.1 Module

| Ort | Was |
|---|---|
| `contract/types.py` | `BlobRef`; `blobs` an `RawEvent` |
| `contract/store.py` | die Erweiterungen an `LogStore` für `event_blob`, Salze und die Fassung; ein drittes Protokoll `RedactionStore` für die Grabsteine, damit „kann tilgen" ein Typ ist und kein Kommentar; an `ProjectionStore` das Löschen von Chronik-Zeilen |
| `contract/blobs.py` | `BlobStore`, `StoredBlob`, die Naht für Schlüssel |
| `core/hashing.py` | v=2 neben v=1 |
| `core/sealing.py` | versiegeln und öffnen im Format `age`, stückweise; mitrechnen der Adresse |
| `core/blob.py` | speichern und holen: Adresse, „erster gewinnt", die zwei Durchgänge |
| `core/chain.py` | was `append` und der Schreibweg für Handlungen teilen |
| `core/redaction.py` | die Form des Tilgungs-Events, sein Verzeichnis und die Regel aus §4.1 — rein, damit `verify` sie benutzt, ohne den Ablauf zu kennen |
| `core/redact.py` | der Ablauf der Tilgung |
| `core/verify.py` | §5 |
| `core/projection/chronicle.py` | §6 |
| `storage/postgres.py`, Migrationen `0003` und `0004` | `hash_version`, `payload_salt`, `unit.digest`, `unit.salt`, `unit.content` `NULL`-fähig, die zwei Bedingungen aus §5.1; `event_blob` |
| `storage/s3.py` | der Adapter |
| `storage/keys.py` | Identitäten aus einem Verzeichnis, als Text |
| `cli.py` | die Kommandos; liest die Umgebung und formatiert |

`cli.py` bekommt mit `blob get` und `redact event|units|blob` die ersten
Kommandos mit einer zweiten Ebene; die Tabelle `COMMANDS` trägt sie.

### 8.2 Grenzen

`boto3` wird nur in `storage/s3.py` importiert, `pyrage` nur in
`core/sealing.py`; beide Regeln bekommen ihren import-linter-Vertrag,
namentlich aufgezählt. Die Schlüssel-Naht reicht Identitäten als Text durch,
damit `storage` das Format nicht kennen muss.

### 8.3 Abhängigkeiten

Geprüft am 2026-10-04 an den Registern; das Urteil kommt mit Beleg nach
`DEPENDENCIES.md`.

| Paket | Stand | Urteil |
|---|---|---|
| `boto3` 1.43.108 | 2026-10-02, tägliche Veröffentlichungen | aktiv |
| `pyrage` 1.4.0 | 2026-08-23; davor 2025-06 und 2025-04; ein Betreuer; keine Python-Abhängigkeiten; Wheels `abi3` ab 3.10 | dünne Bindung an die Rust-Bibliothek `age`; selten veröffentlicht. Getragen wird das Urteil vom **Format**: verwaist die Bindung, liest jede andere `age`-Umsetzung die Blobs weiter |
| `pyrage-stubs` 1.4.0 | 2026-08-23, aus demselben Repository | nur für die Typprüfung |
| `types-boto3-lite[s3]` 1.43.108 | 2026-10-02, täglich erzeugt; zieht `types-boto3-s3`, `botocore-stubs` (2026-08-08) und `types-s3transfer` (2025-12-08) nach | nur für die Typprüfung |

Die beiden unteren Zeilen sind der Preis von pyright strict: weder `boto3`
noch `pyrage` liefert Typen mit (gemessen: kein `py.typed`, keine `.pyi` im
Paket). Die Fassung `lite` und nicht `types-boto3[s3]`, gemessen am 2026-10-04
an einem Adapter-Entwurf: mit der vollen Fassung ist `boto3.client` unter
strict „partially unknown", weil ihre Überladungen für jeden nicht
installierten Dienst ins Unbekannte zeigen; mit `lite` und `pyrage-stubs`
meldet pyright nichts.

Verworfen: das Python-SDK von MinIO (letzte Veröffentlichung 2025-11, das
Projekt dahinter archiviert); `cryptography` mit AES-GCM in einem Stück
(Speicher, Grenze bei 2 GiB) oder mit eigenem stückweisem Verfahren (eigener
sicherheitskritischer Code, eigenes Format); Tink (zieht `protobuf`, `absl-py`
und `bazel-runfiles` nach).

**Der Testserver** ist ein Image: RustFS (`rustfs/rustfs:1.0.1`, vom
2026-10-03, Apache-2.0), über den allgemeinen Container des vorhandenen
`testcontainers`, ohne eigenes Modul dafür; der Name des Images steht im Test,
wie `postgres:17`. Die Veröffentlichung ist einen Tag alt; für Tests genügt
das, und gemessen trägt sie den ganzen Weg (§2.6). Der Speicher des Betriebs
ist ein anderer — Hetzner Object Storage, darunter Ceph (Architektur §4.6) —,
und was dort anders ist, zeigt erst der Betrieb (§12).

---

## 9. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, von dem gemessen ist, dass er bricht, und
eine Kontrolle, die gemessen grün bleibt. Gegen echtes PostgreSQL und einen
echten S3-Server im Container; kein Mock für Zeit, Datenbank oder Zufall.

1. **Der Speicher sieht nur Chiffretext.** Das Objekt im Bucket enthält den
   Klartext nicht und öffnet sich nur mit der Identität. Mutation: der
   Schreibweg lädt unversiegelt hoch.
2. **Derselbe Inhalt zweimal ist ein Objekt.**
3. **Eine falsche Adresse fällt beim Lesen auf.** Ein Objekt unter fremdem
   Hash abgelegt: `blob get` schreibt keine Datei. Mutation: der Vergleich am
   Ende entfällt.
4. **Speicher bleibt begrenzt.** Ein Blob von 256 MiB, gespeichert und
   geholt, hebt den Speicher des Prozesses nicht um seine Größe. Mutation: der
   Leser nimmt das Objekt in einem Stück.
5. **v=2: eine Einheit getilgt, die übrigen bleiben geprüft.** Nach
   `redact units` meldet `verify` nichts; eine danach geänderte Nachbareinheit
   meldet es. Mutation: `units_hash` rechnet wieder über die Inhalte.
6. **Getilgtes lässt sich nicht erraten.** Nach der Tilgung fehlt das Salz,
   und der stehengebliebene Hash geht aus dem bekannten Inhalt allein nicht
   mehr hervor. Mutation: die Tilgung lässt das Salz stehen — und die
   Datenbank weist sie ab.
7. **v=1 bleibt prüfbar**, und sein Hash-Vektor unverändert.
8. **Ein Grabstein ohne Anordnung ist ein Befund**, für Nutzlast und Einheit.
   Das ist die Messung aus dem 1a-Spec §3.1, umgedreht. Mutation: der Abgleich
   am Ende entfällt.
9. **Eine Anordnung ohne Vollzug ist ein Befund.**
10. **Tilgung und Grabsteine entstehen zusammen oder gar nicht.**
11. **Ein gescheitertes Löschen im Speicher holt der zweite Aufruf nach**, und
    es entsteht kein zweites Tilgungs-Event.
12. **Die Regel aus §4.1:** ein geteilter Blob überlebt die Tilgung des einen
    Events, nicht die des letzten und nicht die des Blobs; derselbe Inhalt an
    einem neuen Event liegt wieder da, und `verify --blobs` meldet nichts.
13. **Die Anker halten nach jeder Art von Tilgung.**
14. **Inkrementell gleich neu gebaut, mit Tilgungen dazwischen**, vor und
    nach dem Arbeiter.
15. **Nach `redact` zeigt die Chronik das Getilgte nicht**, ohne dass jemand
    `project` aufruft.
16. **`verify --blobs`** findet jeden der vier Fälle aus §5.3.
17. **Ohne Blob-Angaben** läuft jedes Kommando, das es heute gibt, wie heute.
18. **Kein Geheimnis in einer Ausgabe**: weder das des Speichers noch eine
    Identität.
19. **Was die Reference zitiert**, wird gegen den Code gehalten.
20. **Zwei Schreiber zugleich, derselbe Inhalt, zwei Empfänger:** es bleibt
    ein ganzes Objekt, beide Events holen ihren Blob, und `verify --blobs`
    meldet nichts. Mutation: der Leser nimmt die `key_id` vom Empfänger des
    Schreibers statt vom Objekt.
21. **Nach einem Schlüsselwechsel** zeigt ein neues Event auf ein Objekt, das
    an den alten Schlüssel versiegelt ist, und holt es.

---

## 10. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`, eine Seite je Quadrant.

- **Explanation, neu: Tilgung.** Was sie nimmt und was nicht; warum sie ein
  Event ist; die Naht aus Stufe 1a und wie sie hier bezahlt wird; drei Ziele
  und warum die Nutzlast keins in Teilen ist; das Salz; die Sicherungen und
  die Wiederherstellung.
- **Explanation, neu: Blobs.** Adresse, Verschlüsselung, warum `age`, warum
  der Speicher nur Chiffretext sieht, „erster gewinnt", die Schlüssel, wann
  ein Blob zu liegen hat.
- **Explanation, bestehend:** `hash-chain.md` (v=2; die Grabstein-Naht ist
  eingelöst), `projections.md` (eine Projektion löscht), `concurrency.md` (ein
  zweiter Schreibweg an derselben Kette), `module-boundaries.md`,
  `backup-encryption.md` (wo der Schlüssel der Blobs im Verhältnis zur
  Sicherung liegt).
- **Reference:** `hash-format.md` (v=2 neben v=1), `cli.md` (zehn Kommandos
  statt acht, die Befunde), `database-schema.md`, `configuration.md`.
- **How-to, neu:** etwas tilgen; einen Anhang ablegen und holen; einen
  Blob-Speicher für den eigenen Rechner starten; die Identität sichern und
  die Sicherung proben.
- **How-to, bestehend:** `restore-from-a-backup.md` (was nach einer
  Wiederherstellung mit Tilgungen ist), `verify-the-chain.md` (`--blobs`).
- **Tutorial:** neu getippt aus einem Lauf — neue Events tragen andere
  Hashes. Es bleibt ohne Blobs, damit es ohne zweiten Dienst durchläuft.
- **README, Landkarte**, und beim Einfrieren `design-records.md`.

---

## 11. Abnahme

| # | Bedingung |
|---|---|
| 1 | Ein Blob wird verschlüsselt unter seinem Klartext-Hash abgelegt; derselbe Inhalt zweimal ist ein Objekt. |
| 2 | `blob get` gibt nur zurück, was zur Adresse passt. |
| 3 | Neue Events sind v=2, mit Salz; v=1 bleibt prüfbar, sein Vektor unverändert. |
| 4 | `redact` tilgt ein Event, einzelne Einheiten, einen Blob; jede Tilgung ist ein Event in der Kette. |
| 5 | `verify` meldet einen Grabstein ohne Anordnung und eine Anordnung ohne Vollzug. |
| 6 | Nach einer Teil-Tilgung bleiben die übrigen Einheiten geprüft. |
| 7 | Was getilgt ist, lässt sich aus dem, was stehen bleibt, nicht erraten — die Adresse eines Blobs ausgenommen (§4.5). |
| 8 | `verify --blobs` findet fehlende, falsche, unlesbare und getilgt-vorhandene Blobs. |
| 9 | Anker halten nach jeder Tilgung; Projektionen folgen ihr, inkrementell wie neu gebaut, und `redact` zieht sie nach. |
| 10 | `boto3` nur in `storage/s3.py`, `pyrage` nur in `core/sealing.py`; jede Grenze hat ihren Vertrag. |
| 11 | Jede Zusicherung aus §9 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 12 | Die Dokumente aus §10 stehen. |
| 13 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 14 | **Von Hand:** ein Anhang abgelegt, geholt, getilgt und mit `verify --blobs` geprüft, gegen einen Speicher auf dem eigenen Rechner. Und der Notfallweg, einmal gegangen: ein Blob aus dem Bucket geholt und mit dem Werkzeug `age` und der Identität geöffnet, ohne diese Software. |

Abgenommen ist die Arbeit mit dem Merge nach `main`.

---

## 12. Was offen bleibt

Gepflegt, solange der Spec lebt; beim Einfrieren gehen die Punkte in die
Landkarte.

1. **Verwaiste Blobs.** Scheitert das Anfügen nach dem Speichern, bleibt ein
   Blob ohne Event. Ihn zu finden heißt, den Bucket gegen `event_blob` zu
   halten; gebaut ist das nicht.
2. **Aufnehmen und Tilgen zugleich.** Sieht ein Schreiber, dass ein Blob
   schon liegt, und tilgt ein anderer in diesem Augenblick dessen letzte
   Referenz, zeigt das neue Event auf ein Objekt, das fehlt. `verify --blobs`
   meldet es; verhindert wird es nicht.
3. **Ein Verzeichnis der Tilgungen außerhalb der Datenbank.** Nach einer
   Wiederherstellung auf einen älteren Stand weiß das Log nicht mehr, was
   seither getilgt wurde (§4.5). Die Anker-Datei wäre ein Muster dafür.
4. **Der Quellschlüssel überlebt jede Tilgung** (§4.5).
5. **Wer tilgt.** Der 1a-Spec nennt für das Tilgungs-Event „Zeitpunkt, Anlass
   und Urheber". Dieses hier trägt die ersten beiden; das System kennt noch
   keine Personen.
6. **Ein Schlüssel je Betroffenem** und das Krypto-Schreddern.
7. **Ein Tresor hinter der Schlüssel-Naht.**
8. **Textextraktion aus Blobs**, und damit ihr Inhalt in Einheiten.
9. **`verify --blobs` liest alles.** Eine Prüfung nur der Blobs seit dem
   letzten Lauf gibt es nicht.
10. **Hochladen ohne Zwischendatei** (§2.3).
11. **Was bei Hetzner anders ist** als beim Testserver.
12. **Eine Wiedersichtung nach der Tilgung.** Dass ein getilgtes Event unter
    seinem Schlüssel bekannt bleibt und nicht wieder aufgenommen wird, gehört
    zum Einwurf-Vertrag des Piloten und ist dort entworfen. Der Hash, an dem
    er Inhalt wiedererkennt, trüge kein Salz; das ist dort abzuwägen.
13. **Bedingtes Schreiben** (`If-None-Match: *`) machte aus „erster gewinnt"
    ein Schloss statt eines Nachsehens (§2.7). Dafür müsste das Hochladen in
    Teilen von Hand gebaut und an Hetzner gemessen werden.
14. **Ein beschädigtes Objekt ersetzen.** „Erster gewinnt" lässt es liegen
    (§2.7); ein Kommando, das einen Inhalt bewusst neu ablegt, gibt es nicht.
