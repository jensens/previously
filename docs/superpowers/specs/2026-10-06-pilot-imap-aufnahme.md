# Previously — Pilot, Einheit 1: die Aufnahme aus einem IMAP-Ordner

**Datum:** 2026-10-06
**Status:** Entwurf, zur Durchsicht durch den Betreuer

Detail-Spec für die erste Einheit des Piloten an einem echten Kunden. Setzt
die Stufen 1a, 1b, den äußeren Anker, Stufe 1c und die Auslieferung voraus
(auf `main` seit `fd3e17f`, veröffentlicht als `0.1.0a1`). Er ersetzt den
Entwurf vom 2026-10-04 auf dem Zweig `worktree-pilot-imap-aufnahme`
(`9b493f0`), der ruhte, bis Stufe 1c gebaut war; was von ihm bleibt, steht hier
noch einmal, damit dieser Spec für sich allein liest.

Grundlage sind das Gespräch mit dem Betreuer am 2026-10-05 (Notiz unter
`.superpowers/notizen/2026-10-05-pilot-aufnahme-entscheidungen.md`) und die
Landkarte.

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
seine offenen Punkte gehen dann in die Landkarte.

---

## 1. Zweck und Zuschnitt

Das System hat noch kein echtes Event gehalten. Diese Einheit baut den Weg von
einer Mail in einem eigens angelegten IMAP-Ordner zum Event in der Kette, mit
der Rohmail und jedem Anhang als Blob — und den Vertrag, über den jede
spätere Quelle denselben Weg nimmt.

**Lieferungen:**

1. **Der Einwurf-Vertrag.** `RawEvent` trägt die Inhaltsidentität des
   Artefakts und die Kanalidentitäten, die die Architektur verlangt und
   Stufe 1a wegließ (§2).
2. **Eine Mail als Event**, Feld für Feld, samt der Fälle, die echte Post
   mitbringt (§3).
3. **Der Konnektor-Vertrag und der Lauf.** `Connector` und `Watermark` in
   `contract`, ein Lauf in `core`, der Blobs speichert, Stapel anfügt und das
   Wasserzeichen erst danach fortschreibt, und der erste Konnektor: IMAP (§4).
4. **Ein Kommando**, `previously ingest imap` (§5).
5. **Die Dokumentation dazu** und eine Ergänzung des Handoffs an kup6s, im
   selben Pull-Request (§9).

**Nicht enthalten:**

- **Gmail und OAuth.** Der Konnektor spricht IMAP mit Benutzer und Passwort;
  ein Postfach bei Google Workspace ist später eine Frage der Anmeldung, kein
  anderer Konnektor (§11).
- **Der Bau im Cluster.** Der CronJob der Aufnahme entsteht in kup6s, aus dem
  Handoff (§6).
- **Der Nextcloud-Ordner** und jede Textextraktion aus Anhängen: Einheit 7.
- **Die Zuordnung** zu Organisation, Projekt oder Vorgang. In welchem Ordner
  eine Mail lag, steht in der Nutzlast; eine Feststellung wird daraus mit
  Einheit 5.
- **Jeder Modellaufruf.** In dieser Einheit sieht kein Modell den Inhalt.
- **`IDLE`**, also Aufnahme ohne Zeitgeber (§11).

### 1.1 Der Rahmen des Piloten

Vom Betreuer am 2026-10-04 und 2026-10-05 entschieden:

- **Ein echter Kunde, echte Post.** Was der Betreuer in den Ordner kopiert,
  ist relevant.
- **Plain IMAP mit Benutzer und Passwort**, ein Mailu-Postfach. Testmails
  werden in einen eigenen Ordner kopiert.
- **Lokal nur eine Probe, auch mit echter Kundenpost, aber nicht
  nachhaltig.** Probe-Log und Bucket werden danach verworfen. Das dauerhafte
  Log beginnt im Cluster, indem der Ordner dort neu eingelesen wird; das
  Einlesen ist idempotent.
- **Die Tilgung gibt es** (Stufe 1c). Wer sie zusagt, löscht die Mail auch im
  Ordner und in den Sicherungen des Postfachs (§6).
- **Datenpolitik des Pilotkunden:** sein Inhalt darf über Claude Code an
  Anthropic gehen („bei diesem Kunden gedeckt", Betreuer, 2026-10-04). In
  dieser Einheit ohne Wirkung.
- **kup6s wird nie von hier aus geändert**; was der Betrieb braucht, geht als
  englischer Handoff an den Agenten dort.

### 1.2 Was dieser Spec an früheren Festlegungen ändert

1. **`RawEvent` (Architektur §6.2).** Die Architektur gibt
   `channel_identities` und `raw: bytes | None` vor. Stufe 1c hat einen Ort
   für Bytes gebaut (`blobs`); die Rohbytes einer Mail sind darum ein Blob
   wie jeder Anhang, und ein eigenes Feld `raw` entfällt. Neu ist
   `artifact_hash` (§2.2) und `channel_identities`.
2. **Idempotenz (1a-Spec §5).** „Ein zweiter Einwurf desselben
   Quellereignisses liefert dieselbe `event.id` und schreibt nichts" — das
   bleibt. Neu ist, was *dasselbe* heißt: bisher jeder Einwurf unter
   demselben Schlüssel, gleich mit welchem Inhalt; der Prüfpunkt hat gemessen,
   dass ein geänderter Stand so stumm verloren geht (Bericht A1, Messung M1).
   Künftig vergleicht `append` die Inhaltsidentität und weist Abweichendes
   laut ab (§2.2).
3. **`Connector.ingest` (Architektur §6.1)** gibt jedes `RawEvent` zusammen
   mit der Position zurück, die nach seinem Anfügen als Wasserzeichen gilt
   (§4.1).
4. **`source` ist der Kanal, nicht der Konnektor.** Eine Mail hat
   `source = "email"`, gleich aus welchem Postfach oder Ordner sie kommt
   (§3.1). Woher eine Sichtung stammt, trägt der Name des Konnektor-Laufs.

---

## 2. Der Vertrag

### 2.1 `RawEvent`

```python
@dataclass(frozen=True)
class ChannelIdentity:
    channel: str        # 'email'
    role: str           # 'from' | 'sender' | 'reply_to' | 'to' | 'cc' | 'bcc'
    address: str        # wie in der Quelle, unverändert
    name: str | None    # Anzeigename, wenn die Quelle einen trägt

@dataclass(frozen=True)
class RawEvent:
    source: str
    external_id: str
    occurred_at: datetime
    evidence: Evidence
    units: tuple[RawUnit, ...]
    payload: Mapping[str, object] = ...
    blobs: tuple[BlobRef, ...] = ()                      # seit Stufe 1c
    artifact_hash: bytes | None = None                   # neu, §2.2
    channel_identities: tuple[ChannelIdentity, ...] = () # neu
```

`artifact_hash` ist für einen Konnektor Pflicht und für `previously append`
ableitbar (§2.2); `None` heißt „nicht angegeben", nicht „leer".

Weiterhin kein `assignment`, keine Klassifikation, keine `language`: ein
Konnektor nimmt auf, er deutet nicht (Architektur §6.2, Leitsatz 4).
**`address` bleibt, wie sie in der Quelle steht**: Kleinschreibung,
Zusammenführen von Schreibweisen, dieselbe Person hinter zwei Adressen —
alles Deutung, alles später.

**Wo es im Log steht.** `append` mischt `artifact_hash` (als Hexzeichenkette)
und `channel_identities` unter diesen Namen in die Nutzlast, wie es das mit
`evidence` und `blobs` tut, und weist eine Nutzlast ab, die einen der Namen
schon trägt. Damit sind sie vom `payload_hash` gedeckt, und eine Tilgung des
Events nimmt sie mit — bei Adressen und Namen ist das gewollt.

### 2.2 Die Inhaltsidentität des Artefakts

`artifact_hash` ist ein SHA-256 über das, **was gleich sein muss, damit zwei
Sichtungen dasselbe Artefakt sind**. Der Konnektor legt fest, was das ist, und
schreibt es auf seiner Reference-Seite hin.

Weder die Einheiten noch die Nutzlast taugen dafür: die Einheiten sind eine
Ableitung (eine bessere Zerlegung, ein anderer HTML-Umwandler, und jede
Wiedersichtung wäre ein Konflikt), die Nutzlast trägt den Transport (dieselbe
Mail in zwei Postfächern mit verschiedenen `Received`-Zeilen ist nach
1a-Spec §5 trotzdem **ein** Event).

Die Regel in `append`, für einen Schlüssel `(source, external_id)`, den es
schon gibt:

| Das vorhandene Event … | Ergebnis |
|---|---|
| trägt denselben `artifact_hash` | bekannt: dieselbe `id`, nichts geschrieben |
| trägt einen anderen | **abgewiesen** mit `ArtifactChanged`, die den Schlüssel und beide Hashes nennt; der ganze Stapel wird nicht geschrieben |
| ist getilgt (Nutzlast `NULL`) | bekannt; eine Wiedersichtung macht keine Tilgung rückgängig |
| trägt keinen `artifact_hash` (vor dieser Einheit geschrieben) | bekannt, wie bisher |

`ArtifactChanged` ist ein `PreviouslyError`, und **was dann geschieht,
entscheidet der Aufrufer, nie `append`**:

- `previously append` setzt als `artifact_hash` den SHA-256 des übergebenen
  Texts und der Adressen der Anhänge, meldet den Fehler und endet mit 2.
- Ein Konnektor, dessen Artefakte sich nicht ändern sollten (eine Mail),
  nimmt das Abweichende unter einem **Variantenschlüssel** auf (§3.5).

Der Vergleich kostet eine Abfrage je Wiedersichtung: `lookup` liefert die
`id`, `read` das vorhandene Event. `LogStore` bleibt, wie es ist.

---

## 3. Eine Mail als Event

### 3.1 Die Abbildung

| Feld | Wert |
|---|---|
| `source` | `email` |
| `external_id` | die Message-ID aus dem Kopf, ohne spitze Klammern und Leerraum am Rand; fehlt sie, `sha256:` und der `artifact_hash` in Hex |
| `occurred_at` | der Kopf `Date`, wenn er sich als Zeitpunkt mit Zone lesen lässt; sonst die Eingangszeit des Servers (`INTERNALDATE`) |
| `evidence` | `verbatim` |
| `units` | §3.2 |
| `artifact_hash` | §3.3 |
| `channel_identities` | aus `From`, `Sender`, `Reply-To`, `To`, `Cc`, `Bcc`, in der Reihenfolge des Kopfs |
| `blobs` | die Rohmail (`message/rfc822`, ohne Dateinamen) zuerst, dann jeder Anhang mit Name und Typ |
| `payload` | §3.4 |

### 3.2 Einheiten

Erst der **Betreff** als Einheit 1, dann die Absätze des Textkörpers über
`split_plaintext`, Zitate und Signatur eingeschlossen.

- **Welcher Körper:** der Teil `text/plain`, wenn es einen gibt; sonst
  `text/html`, mechanisch in Text umgewandelt (§7.3). Welcher Teil und
  welcher Umwandler in welcher Fassung, steht in der Nutzlast.
- **Zitate und Signaturen bleiben.** Sie zu erkennen ist Deutung.
- **Keine Mail ohne Einheit.** Hat eine Mail weder Betreff noch lesbaren
  Körper (verschlüsselt, nur Anhänge), bekommt sie eine einzige Einheit mit
  einem festen englischen Satz, der sagt, warum (`no readable body:
  encrypted` und Entsprechendes).
- **Zeichen, die das Log nicht hält.** Ein Nullbyte und ein Zeichen, das sich
  mit dem erklärten Zeichensatz nicht lesen lässt, werden durch U+FFFD
  ersetzt; die Nutzlast vermerkt es. Die Rohmail liegt als Blob daneben.

### 3.3 Die Inhaltsidentität einer Mail

SHA-256 über die kanonische Form des Projekts von:

```
{"subject": <Betreff, dekodiert, oder null>,
 "body": <SHA-256 der dekodierten Bytes des gewählten Körperteils, hex, oder null>,
 "attachments": [<SHA-256 je Anhang, hex, sortiert>]}
```

Dekodiert heißt: nach dem Auflösen der Transportkodierung, vor jeder
Umwandlung in Text. Damit ist die Identität unabhängig vom Umwandler, von der
Zerlegung und vom Transport — und sie ändert sich, wenn sich Betreff, Körper
oder ein Anhang ändert. **Diese Regel gehört dem Projekt, nicht einer
Bibliothek**: ändert eine Bibliothek, wie sie einen Teil dekodiert, ändert
sich die Identität jeder Mail, und jede Wiedersichtung würde eine Variante.
Darum zerlegt `core/mail.py` mit dem Modul `email` der Standardbibliothek
selbst (§7.3), und Tests halten die Regel fest.

### 3.4 Die Nutzlast

| Schlüssel | Inhalt |
|---|---|
| `headers` | **alle** Kopfzeilen als Liste von Paaren `[Name, Wert]`, in der Reihenfolge der Mail, Namen wie geschrieben. Sie stehen auch in der Rohmail; hier, damit man sie ohne Schlüssel lesen kann |
| `raw` | die Adresse der Rohmail unter den `blobs` |
| `date_source` | `header` oder `internaldate` |
| `internaldate` | die Eingangszeit des Servers, ISO 8601 |
| `found_in` | der Name des Konnektor-Laufs und `uidvalidity`/`uid`, wo die Mail bei dieser Sichtung lag |
| `body` | `{"part": …, "charset": …, "converter": … oder null, "replaced": true/false}` |
| `variant_of` | nur bei einer Variante (§3.5): die Message-ID, unter der schon ein anderer Inhalt liegt |
| `forwarded_in` | nur bei einer Mail aus einem Anhang (§3.6): der Schlüssel der äußeren Mail |

Name, Typ, Größe und Hash jedes Anhangs stehen in `blobs`, nicht ein zweites
Mal. **Der Text der Mail steht nicht in der Nutzlast**, nur in den Einheiten;
so tilgt `redact units` ihn wirklich.

Der Ordner ist **keine Eigenschaft der Mail**. Er sagt, wohin der Betreuer sie
gelegt hat; hier steht er als Fundort der ersten Sichtung, und mit Einheit 5
wird daraus eine Zuordnung.

### 3.5 Fälle, die echte Post mitbringt

| Fall | Verhalten |
|---|---|
| **Keine Message-ID** | `external_id` ist `sha256:<artifact_hash>` |
| **Dieselbe Message-ID, derselbe Inhalt** (zwei Kopien, zwei Postfächer, andere Transportzeilen) | bekannt, ein Event; die zweite Rohfassung wird **nicht** gespeichert |
| **Dieselbe Message-ID, anderer Inhalt** (von einer Liste verändert, oder gefälscht) | eigenes Event unter dem Variantenschlüssel `<Message-ID>#<erste 16 Hexzeichen des artifact_hash>`; die Nutzlast trägt `variant_of`. Der Lauf zählt die Variante und nennt sie |
| **`Date` fehlt oder ist unlesbar** | `INTERNALDATE`, und `date_source` sagt es |
| **Nur HTML** | umgewandelt, §7.3 |
| **Verschlüsselt oder signiert** | signiert: der lesbare Teil; verschlüsselt: die eine Einheit aus §3.2. Entschlüsselt wird nichts |
| **Eine Mail als Anhang** (`message/rfc822`), etwa eine weitergeleitete | ein Anhang-Blob der äußeren Mail **und zusätzlich ein eigenes Event**, abgebildet wie jede Mail (§3.6); ihr Text geht nicht in den Körper der äußeren Mail, ihre Anhänge nicht in deren `blobs` |
| **Unbekannter Zeichensatz** | als Latin-1 gelesen, `replaced` vermerkt es |

Im Spike vom 2026-10-05 (Notiz) waren das genau die Fälle, an denen eine
fertige Zerlegung still Inhalt verlor: ein unlesbares `Date` wurde
1900-01-01, ein unbekannter Zeichensatz verlor Zeichen, eine weitergeleitete
Mail ging in den Körper der äußeren auf.

### 3.6 Eine Mail im Anhang wird ein eigenes Event

Der Betreuer kopiert Mails in den Ordner (2026-10-05); dann bleiben sie
Original, und eine Weiterleitung ist die Ausnahme. Leitet aber ein Kunde eine
Mail **als Anhang** weiter, steht der interessante Teil in ihr, und die
äußere Mail sagt oft nur „siehe unten". Als bloßer Blob läge er unlesbar
neben einer leeren Chronikzeile.

Darum wird jede Mail im Anhang auch ein eigenes Event:

- **Abgebildet wie jede Mail** (§3.1–§3.5): ihre eigene Message-ID, ihr
  `Date`, ihre Absender, ihre Einheiten, ihre eigenen Anhänge als Blobs;
  ihre Bytes, wie sie im Anhang stehen, sind ihre Rohmail.
- **Die äußere Mail bleibt ein Event.** Dass jemand weitergeleitet hat, wann
  und mit welchem Satz, ist selbst etwas, das geschah. Sie führt die innere
  unter ihren `blobs`, wie jeden Anhang.
- **Die innere verweist zurück**: ihre Nutzlast trägt `forwarded_in` mit der
  Message-ID (oder dem `sha256:`-Schlüssel) der äußeren.
- **Doppelt abgelegt ist bekannt.** Liegt dieselbe Mail auch direkt im
  Ordner oder wurde sie zweimal weitergeleitet, ist sie über ihre Message-ID
  dasselbe Event; `forwarded_in` hält dann den ersten Fundort.
- **`occurred_at` ist der Zeitpunkt der eigentlichen Mail**, nicht der
  Weiterleitung; die Chronik zeigt sie dort, wo sie hingehört.
- **Verschachtelt** (eine Mail im Anhang einer Mail im Anhang) wird rekursiv
  entpackt, bis zu einer festen Tiefe von **fünf**; was tiefer liegt, bleibt
  Blob, und die Nutzlast der Mail auf Tiefe fünf vermerkt es. Die Grenze
  schützt vor einer kaputten oder böswilligen Mail, nicht vor echter Post.
- **Eine Weiterleitung als zitierter Text** („---------- Forwarded message
  ----------" im Körper) bleibt Text der äußeren Mail: sie zu zerlegen hieße
  den Text deuten. Die Anleitung sagt, dass eine Weiterleitung als Anhang
  sauber erfasst wird.

Im Lauf (§4.2) entstehen aus einem `Fetched` damit ein oder mehrere Events,
die im selben Stapel angefügt werden. Ihre Reihenfolge darin ist gleich:
`forwarded_in` verweist auf einen Schlüssel, nicht auf eine `id`.

---

## 4. Der Konnektor und der Lauf

### 4.1 Vertrag

In `contract`:

```python
@dataclass(frozen=True)
class Watermark:
    connector: str                    # der Name des Konnektor-Laufs
    position: Mapping[str, str]       # konnektorspezifisch, für core undurchsichtig
    set_at: datetime

@dataclass(frozen=True)
class Fetched:
    raw: bytes                        # die Rohbytes eines Artefakts
    position: Mapping[str, str]       # gilt, sobald dieses Artefakt angefügt ist
    found_in: Mapping[str, str]       # wo es lag, für die Nutzlast

class Connector(Protocol):
    name: str                         # z. B. "imap:pilot@mail.example.org/Kunde Müller"
    def fetch(self, since: Watermark | None) -> Iterator[Fetched]: ...
```

Der Konnektor holt **Bytes**, er bildet nicht ab: die Abbildung einer Mail
liegt in `core/mail.py`, weil dieselbe Mail später als Datei im
Nextcloud-Ordner liegen kann.

**Der Name des Konnektor-Laufs** wird aus Host, Benutzer und Ordner gebildet,
ohne eigene Einstellung. Wird der Ordner umbenannt, beginnt ein neues
Wasserzeichen, und der Ordner wird von vorn gelesen — harmlos, weil das
Einlesen idempotent ist.

### 4.2 Der Lauf

In `core/ingest.py`, eine Funktion. Sie liest das Wasserzeichen des
Konnektors und zieht `Fetched` in Stapeln. Je Artefakt:

1. `core/mail.py` bildet die Rohbytes auf ein `RawEvent` ab und nennt die
   Anhänge;
2. die Rohmail und jeder Anhang werden mit `store_blob` gespeichert (Stufe 1c),
   und die `BlobRef` kommen ins `RawEvent`;

dann wird der Stapel mit `append` angefügt, und **danach** wird das
Wasserzeichen auf die Position des letzten Artefakts geschrieben.

- **Bricht der Lauf ab**, holt der nächste dieselben Mails noch einmal: die
  Blobs liegen schon (der Speicher ist inhaltsadressiert), die Events sind
  bekannt, nichts wird doppelt. Ein Objekt ohne Event bleibt nur, wenn die
  Mail aus dem Ordner verschwindet, bevor der nächste Lauf kommt — dieselbe
  offene Grenze wie in Stufe 1c.
- **Meldet `append` `ArtifactChanged`**, nimmt der Lauf das Artefakt unter
  seinem Variantenschlüssel auf und fügt den Stapel erneut an.
- **Derselbe Schlüssel zweimal in einem Stapel** ist für `append` ein Fehler;
  bei zwei Kopien einer Mail im selben Ordner ist es der Normalfall. Der Lauf
  legt sie vor dem Anfügen zusammen, nach derselben Regel: gleiche Identität
  ist bekannt, andere ist eine Variante.
- **Speicher:** eine Mail nach der anderen; ihre Rohbytes liegen nie länger
  im Speicher, als ihre Abbildung dauert. Eine Mail ist so groß, wie das
  Postfach sie annimmt (bei Mailu standardmäßig 50 MB).

Der Lauf gibt zurück, was geschah: angefügt, bekannt, Varianten, und die
Position des Wasserzeichens. Sätze macht die Kommandozeile.

Das Wasserzeichen liegt in einer neuen Tabelle `watermark` (`connector` als
Schlüssel, `position` als `jsonb`, `set_at`), hinter einem eigenen Protokoll
`WatermarkStore` mit zwei Methoden. Migration `0005`.

### 4.3 IMAP

- **Die Standardbibliothek**: `imaplib`. Im Spike vom 2026-10-05 gab
  `imap-tools` die rohen Bytes einer Mail nicht heraus, und was es sonst
  sparte (Ordnernamen umrechnen, OAuth-Anmeldung), sind wenige Zeilen.
- **Nur über TLS** (IMAPS), mit geprüftem Zertifikat. Kein Schalter für
  Klartext.
- **Anmeldung mit Benutzer und Passwort.**
- **Gelesen wird mit `BODY.PEEK[]`**: keine Mail wird als gelesen markiert,
  der Ordner bleibt, wie er ist.
- **Position:** `UIDVALIDITY` und die höchste angefügte `UID`. Ändert der
  Server die `UIDVALIDITY`, beginnt der Lauf von vorn; die Idempotenz fängt es
  auf.
- **Suche schlicht:** `UID n:*` ohne Klammern — GreenMail weist geklammerte
  Ausdrücke ab (Spike).
- **Ordnernamen mit Umlauten** in der Kodierung von IMAP (RFC 3501, „modified
  UTF-7"); ein Ordner „Kunde Müller" ist der erwartbare Fall.
- **Gelöschte und verschobene Mails** bleiben im Log; der Ordner ist die
  Eingangstür, nicht der Spiegel.

---

## 5. `previously ingest imap`

Das zwölfte Kommando, in `COMMANDS`.

**Eingabe** aus der Umgebung: `PREVIOUSLY_IMAP_HOST`, `PREVIOUSLY_IMAP_PORT`
(Vorgabe 993), `PREVIOUSLY_IMAP_USER`, `PREVIOUSLY_IMAP_PASSWORD`,
`PREVIOUSLY_IMAP_FOLDER`; dazu `PREVIOUSLY_DSN`, die fünf Angaben des
Blob-Speichers und der Empfänger (`PREVIOUSLY_BLOB_RECIPIENT`). Das
Verzeichnis der Identitäten braucht das Kommando **nicht**: wer aufnimmt,
öffnet keinen Blob. Fehlt eine Pflichtangabe, ist das ein Eingabefehler, bevor
verbunden wird.

**Ausgabe** auf die Standardausgabe, eine Zeile:

```
imap: 12 appended, 3 known, 0 variants, up to uid 4711
```

Jede Variante zusätzlich als eigene Zeile auf die Standardfehlerausgabe, mit
Message-ID und `id` des neuen Events. Das Passwort erscheint in keiner Ausgabe
und keiner Meldung.

**Rückgabecodes:** 0, wenn der Lauf durchging, auch mit Varianten; 2 bei
Eingabe-, Verbindungs-, Anmelde-, Speicher- oder Blob-Fehler.

`ingest` zieht die Projektionen **nicht** nach; `project` läuft danach. Seit
Stufe 1c ist es sicher, dass beide nebeneinander laufen.

---

## 6. Was das für den Betrieb heißt

- **kup6s.** Eine Ergänzung des Handoffs der Auslieferung, englisch:
  - ein CronJob alle 5 bis 15 Minuten, `previously ingest imap`, dann
    `previously project`, `concurrencyPolicy: Forbid`;
  - ein Secret mit den fünf IMAP-Angaben, nur für diesen Job;
  - Netz nach außen: der Mailserver auf Port 993;
  - **ein eigener Mailu-Benutzer** nur für den Piloten, in dessen Ordner der
    Betreuer die Mails kopiert — das Passwort im Cluster öffnet nur dieses
    Postfach;
  - die erste Aufnahme des echten Kundenordners geschieht dort, nicht lokal.
- **Ein Host mit `docker-compose`.** Eine Cron-Zeile, die dieselben zwei
  Kommandos im Container ruft, und die fünf Angaben in der Umgebungsdatei.
- **Die Tilgung reicht über Previously hinaus.** Previously verändert den
  Ordner nie. Wer eine Tilgung zusagt, löscht die Mail auch im Ordner und in
  den Sicherungen des Postfachs; deren Aufbewahrung gehört dann zur Zusage wie
  die von Datenbank und Bucket.
- **Der Einfachheits-Check** fällt gut aus: ein Kommando mehr, ein Zeitgeber,
  eine Tabelle. Neu ist ein Geheimnis, das Passwort des Postfachs.

---

## 7. Schnitt im Code

### 7.1 Module

| Ort | Was |
|---|---|
| `contract/types.py` | `ChannelIdentity`, die neuen Felder an `RawEvent`, `Watermark`, `Fetched` |
| `contract/connector.py` | `Connector` |
| `contract/store.py` | `WatermarkStore` |
| `core/append.py` | das Einmischen der Namen, der Vergleich, `ArtifactChanged` |
| `core/mail.py` | Rohbytes einer Mail zu `RawEvent` und Anhängen: rein, ohne Netz, ohne Datenbank |
| `core/ingest.py` | der Lauf |
| `connectors/imap.py` | verbinden, Ordner wählen, holen |
| `storage/` | Tabelle `watermark`, Migration `0005`, die zwei Methoden |
| `cli.py` | das Kommando |

### 7.2 Grenzen

Ein neues Modul `previously.connectors`, über `core` und unter `cli`. Nur dort
steht ein Import von `imaplib`; der import-linter-Vertrag dafür wird
namentlich aufgezählt.

### 7.3 Abhängigkeiten

**Eine neue: der Umwandler von HTML nach Text.** Die Wahl fällt im Plan, mit
einer Messung an erfundenen Testmails: welcher Kandidat aus einer HTML-Mail
Absätze macht, die `split_plaintext` trennt, und was jeder mit Tabellen,
Zitatblöcken und Signaturen tut. Zwei Bedingungen stehen fest: der Umwandler
holt **nichts aus dem Netz**, und seine Fassung steht in der Nutzlast. Das
Urteil kommt mit Datum und Beleg nach `DEPENDENCIES.md`.

**Der Testserver** ist ein Image: GreenMail (`greenmail/standalone`, 2.1.14,
im Spike gelaufen), über `testcontainers`.

---

## 8. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, gemessen rot, wenn sie zurückgenommen
wird, mit einer grünen Kontrolle. Gegen echtes PostgreSQL, RustFS und GreenMail
im Container; kein Mock. **Testmails sind erfunden**, deutsch und englisch
gemischt, nie Kundenpost.

1. **Gleicher Schlüssel, gleicher Inhalt: bekannt.**
2. **Gleicher Schlüssel, anderer Inhalt: abgewiesen, nichts geschrieben** —
   die Messung M1 des Prüfpunkts als Test.
3. **Eine Tilgung wird nicht rückgängig gemacht.**
4. **Die neuen Namen in der Nutzlast sind reserviert**, wie `evidence`.
5. **Zwei Kopien einer Mail mit verschiedenen Transportzeilen: ein Event**,
   eine Rohmail im Bucket.
6. **Dieselbe Message-ID, anderer Körper: zwei Events, keins verloren.**
7. **Rohmail und Anhänge sind Blobs**; ein Anhang in zwei Mails liegt einmal
   im Bucket; `blob get` holt die Rohmail byte-gleich.
8. **Ein zweiter Lauf fügt nichts an.**
9. **Das Wasserzeichen folgt dem Anfügen.** Ein Lauf, der nach dem Speichern
   der Blobs abbricht: der nächste holt den Rest und findet die Blobs vor.
10. **Geänderte `UIDVALIDITY`: von vorn, nichts doppelt.**
11. **Der Ordner bleibt, wie er ist.** Mutation: `BODY[]` statt `BODY.PEEK[]`.
12. **Das IMAP-Passwort erscheint nirgends**, auch bei falscher Anmeldung.
    Nur dieser Fall: ein Befund, der nur bei Fehlbedienung auftritt, wird
    benannt, nicht gejagt (Arbeitsregel vom 2026-10-05).
13. **Die Abbildung, Fall für Fall** aus §3.5, an Mails als Dateien, ohne
    Server.
14. **Eine weitergeleitete Mail im Anhang wird ein eigenes Event** mit ihrem
    eigenen Zeitpunkt, ihren Einheiten und `forwarded_in`; liegt sie auch
    direkt im Ordner, bleibt es ein Event; eine Verschachtelung über die
    Tiefe fünf hinaus bleibt Blob. Mutation: das Entpacken entfällt.
15. **Was die Reference zur Abbildung und zum Kommando zitiert**, wird gegen
    den Code gehalten.

---

## 9. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`.

- **Explanation, neu: Konnektoren.** Der Vertrag; warum `source` der Kanal
  ist; die Inhaltsidentität und warum weder Einheiten noch Nutzlast sie
  tragen; die Variante; Rohmail und Anhänge als Blobs; warum der Ordner keine
  Eigenschaft der Mail ist.
- **Reference:** `cli.md` (`ingest imap`, zwölf Kommandos);
  `configuration.md` (die fünf Angaben, wer sie liest); das Schema
  (`watermark`); neu: **die Abbildung einer Mail**, als Tabellen.
- **How-to, neu:** einen Mail-Ordner aufnehmen — Benutzer und Ordner anlegen,
  Angaben setzen, laufen lassen, lesen, was der Lauf sagt; was Tilgen hier
  heißt.
- **Handoff:** die Ergänzung für kup6s (§6), englisch.
- **README** und **Landkarte.**

Das Tutorial bleibt beim Einwurf von Hand.

---

## 10. Abnahme

| # | Bedingung |
|---|---|
| 1 | `RawEvent` trägt `artifact_hash` und `channel_identities`; `append` mischt sie ein und reserviert die Namen. |
| 2 | Gleicher Schlüssel mit anderem Inhalt wird abgewiesen; M1 ist ein Test. |
| 3 | Eine Mail wird nach §3 zum Event; jeder Fall aus §3.5 hat einen Test. |
| 4 | Rohmail und Anhänge liegen als Blobs; ein zweiter Lauf fügt nichts an. |
| 5 | Das Wasserzeichen wird erst nach dem Anfügen geschrieben. |
| 6 | Der Ordner wird nicht verändert; das Passwort erscheint nirgends. |
| 7 | `core` importiert weder `imaplib` noch SQL; die neue Schicht hat ihren Vertrag. |
| 8 | Jede Zusicherung aus §8 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 9 | Die Dokumente aus §9 stehen. |
| 10 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 11 | **Ein Lauf des Betreuers, lokal, gegen seinen echten Mailu-Ordner:** Mails hinein, `previously ingest imap`, `project`, `chronicle` zeigt sie mit Betreff; Rohmail und ein Anhang kommen mit `blob get` zurück; ein zweiter Lauf meldet `0 appended`. Danach wird das Probe-Log samt Bucket verworfen. |

Abgenommen ist die Arbeit mit dem Merge nach `main`.

---

## 11. Was offen bleibt

Gepflegt, solange der Spec lebt; beim Einfrieren gehen die Punkte in die
Landkarte.

1. **Gmail und OAuth.** Ein Postfach bei Google Workspace braucht in der
   Regel `XOAUTH2`; der Konnektor nimmt dann ein Token statt eines Passworts.
   Das Holen und Erneuern des Tokens ist die eigentliche Arbeit
   (`google-auth`).
2. **Weitere Fundorte.** Dieselbe Mail in einem zweiten Ordner schreibt
   nichts; nur der erste Fundort steht im Log. Mit Einheit 5 wird das Ablegen
   eine Zuordnung, und die kann mehrfach sein.
3. **Mehrere Ordner, mehrere Postfächer** in einem Lauf. Einer je Lauf genügt
   dem Piloten.
4. **`occurred_at` aus `Date`** ist die Uhr des Absenders und kann falsch
   sein. Beide Zeiten stehen in der Nutzlast; welche die Chronik ordnet, wenn
   sie weit auseinanderliegen, ist nicht entschieden.
5. **`IDLE`**, Aufnahme ohne Zeitgeber, mit dem MCP-Dienst denkbar.
6. **Die Variante in der Chronik.** Eine Variante erscheint als zweites
   Event; die Chronik sagt nicht, dass sie eine ist.
7. **Ein Objekt ohne Event**, wenn eine Mail zwischen Speichern und Anfügen
   aus dem Ordner verschwindet (wie Stufe 1c).
8. **Textextraktion aus Anhängen** (Einheit 7).
9. **Mails als Dateien im Nextcloud-Ordner (Einheit 7).** Eine `.eml`-Datei
   ist eine Mail nach RFC 822, dieselben Bytes, die IMAP liefert; sie läuft
   durch dieselbe Abbildung (`core/mail.py`) und wird ein Event mit
   `source = email` — liegt dieselbe Mail auch im IMAP-Ordner, ist sie über
   Message-ID und Inhaltsidentität dasselbe Event, gleich welcher Weg zuerst
   kam; ihr Fundort ist dann der Nextcloud-Konnektor. Offen für Einheit 7:
   Outlooks `.msg` (eigenes Binärformat) und `.mbox` (viele Mails in einer
   Datei) müssen erst umgewandelt oder zerlegt werden — was davon gebraucht
   wird, zeigt, was im Ordner tatsächlich landet. Vom Betreuer am 2026-10-06
   gefragt, „dann wird es nicht vergessen".
10. **Weiterleitung als zitierter Text** bleibt Text der äußeren Mail (§3.6);
   sie zu zerlegen wäre Deutung, und ob das eine spätere Einheit leisten
   soll, ist offen.
