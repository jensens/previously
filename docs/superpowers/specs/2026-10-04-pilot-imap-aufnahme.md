# Previously — Pilot, Einheit 1: die Aufnahme aus einem IMAP-Ordner

**Datum:** 2026-10-04
**Status:** Entwurf, zur Durchsicht

Detail-Spec für die erste Einheit des Piloten an einem echten Kunden. Setzt
den Entwurf (`2026-10-01-previously-design.md`), die Architektur
(`2026-10-01-architektur.md`) und die Stufen 1a, 1b und den äußeren Anker
voraus, und er geht vom Prüfpunkt nach Teilprojekt 1 aus
(`docs/superpowers/sdd/2026-10-04-pruefpunkt-teilprojekt-1/`), der die Befunde
geliefert hat, die hier entschieden werden. Wo dieser Spec eine frühere
Festlegung ändert, steht es in §1.2.

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
seine offenen Punkte gehen dann in die Landkarte.

---

## 1. Zweck und Zuschnitt

Das System hat noch kein echtes Event gehalten. Der Pilot ändert das, an
**einem Kunden**: was der Betreuer in einen eigens dafür angelegten
IMAP-Ordner kopiert, ist relevant und geht ins Log. Diese Einheit baut den
Weg von der Mail im Ordner zum Event in der Kette — und den Vertrag, über den
jede spätere Quelle denselben Weg nimmt.

**Lieferungen:**

1. **Der Einwurf-Vertrag.** `RawEvent` trägt, was die Architektur verlangt und
   Stufe 1a wegließ: Kanalidentitäten und einen Verweis auf die Rohbytes. Dazu
   kommt die **Inhaltsidentität des Artefakts**, an der `append` erkennt, ob
   unter einem bekannten Schlüssel dasselbe oder etwas anderes ankommt (§2).
2. **Eine Mail als Event.** Die Abbildung, Feld für Feld, samt der Fälle, die
   echte Post mitbringt (§3).
3. **Der Konnektor-Vertrag und der Lauf.** `Connector` und `Watermark` in
   `contract`, ein Lauf in `core`, der Stapel anfügt und das Wasserzeichen
   erst danach fortschreibt, und der erste Konnektor: IMAP (§4).
4. **Ein Kommando.** `previously ingest imap` (§5).
5. **Die Dokumentation dazu**, im selben Pull-Request (§9).

**Nicht enthalten:**

- **Der Betrieb.** Image, Deployment in kup6s, Sicherung, CronJobs: Einheit 2.
  §6 sagt, was diese Einheit dem Betrieb abverlangt, und baut nichts davon.
- **Der Nextcloud-Ordner** und jede Textextraktion aus Dateien: Einheit 7.
- **Der Inhalt von Anhängen.** Eine Mail trägt zu jedem Anhang Name, Typ,
  Größe und Hash. Der Inhalt braucht einen Ort für Bytes (Stufe 1c) und eine
  Textextraktion.
- **Die Zuordnung** zu Organisation, Projekt oder Vorgang. In welchem Ordner
  eine Mail liegt, steht in der Nutzlast (§3.4); eine Feststellung wird daraus
  mit Einheit 5.
- **Die Warteschlange** aus §7.1 der Architektur. Der Lauf ist ein Kommando,
  das ein Zeitgeber ruft (§6).
- **Jeder Modellaufruf.** Kein Gate, keine KI-Schicht; in dieser Einheit sieht
  kein Modell den Inhalt.
- **Tilgung.** Siehe §1.1.

### 1.1 Der Rahmen des Piloten

Vom Betreuer am 2026-10-04 entschieden, und für alle Einheiten des Piloten
bindend:

- **Ein echter Kunde, echte Post.** Reine Gedankennotizen wären Theorie. Die
  Bedingung der Landkarte vom selben Tag — Inhalte Dritter erst nach der
  Tilgung — ist damit aufgehoben und durch die nächste Zeile ersetzt.
- **Das Pilot-Log ist wegwerfbar.** Es lässt sich jederzeit aus den Quellen
  neu aufbauen. Tilgen heißt im Piloten: die Mail aus dem Ordner nehmen, die
  Datenbank verwerfen, neu einlesen; die Ankerdatei beginnt neu. Das trägt für
  einen Piloten und für nichts danach: bevor ein zweiter Kunde oder ein
  Dauerbetrieb dazukommt, steht die Tilgung als Event (Stufe 1c).
- **Die Quelle bleibt das Archiv.** Solange es keinen Ort für Bytes gibt,
  liegt die Rohmail im IMAP-Ordner und nirgends sonst. Wer eine Mail dort
  löscht, hat danach nur noch, was das Event trägt.
- **Datenpolitik des Pilotkunden:** sein Inhalt darf über Claude Code an
  Anthropic gehen („bei diesem Kunden gedeckt", Betreuer, 2026-10-04). In
  dieser Einheit ohne Wirkung; ab dem MCP-Zugang die Voraussetzung.
- **Der Weg:** Durchstich mit Gate von Anfang an. Aufnahme, Betrieb, Gate und
  Policy, MCP-Lesezugang, Feststellungen, KI-Schicht, Nextcloud. Nur die
  nächste Einheit bekommt einen Spec; die Landkarte führt den Weg.

### 1.2 Was dieser Spec an früheren Festlegungen ändert

1. **`RawEvent` (Architektur §6.2).** Die Architektur gibt
   `channel_identities` und `raw: bytes | None` vor; Stufe 1a baute beides
   nicht, ohne aufgeschriebenen Grund (Prüfpunkt, Bericht A1 Zeile 12). Hier
   kommen die Kanalidentitäten, und statt `raw: bytes` ein **Verweis** mit
   Hash, Größe und Fundstelle — weil es für Bytes noch keinen Ort gibt, und
   weil der Hash genau die Adresse ist, unter der ein inhaltsadressierter
   Blob-Speicher sie später ablegt (§2.3).
2. **Idempotenz (1a-Spec §5).** „Ein zweiter Einwurf desselben Quellereignisses
   liefert dieselbe `event.id` und schreibt nichts" — das bleibt. Neu ist, was
   *dasselbe* heißt: bisher jeder Einwurf unter demselben Schlüssel, gleich
   mit welchem Inhalt. Der Prüfpunkt hat gemessen, dass ein geänderter Stand
   so stumm verloren geht (Bericht A1, Messung M1). Künftig vergleicht
   `append` die Inhaltsidentität und weist Abweichendes laut ab (§2.2).
3. **`Connector.ingest` (Architektur §6.1)** gibt nicht nackte `RawEvent`
   zurück, sondern jedes zusammen mit der Position, die nach seinem Anfügen
   als Wasserzeichen gilt (§4.1). Sonst weiß der Lauf nicht, wie weit er das
   Wasserzeichen schreiben darf.
4. **Die Bedingung „Inhalte Dritter erst nach der Tilgung"** aus der
   Landkarte: siehe §1.1.

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
class RawRef:
    sha256: bytes       # über die Rohbytes
    size: int
    locator: str        # wo die Quelle sie hält; für core undurchsichtig

@dataclass(frozen=True)
class RawEvent:
    source: str
    external_id: str
    occurred_at: datetime
    evidence: Evidence
    units: tuple[RawUnit, ...]
    artifact_hash: bytes                              # §2.2, Pflicht
    channel_identities: tuple[ChannelIdentity, ...] = ()
    raw: RawRef | None = None
    payload: Mapping[str, object] = field(default_factory=dict)
```

Weiterhin kein `assignment`, keine Klassifikation, keine `language`: ein
Konnektor nimmt auf, er deutet nicht (Architektur §6.2, Leitsatz 4).

**`address` bleibt, wie sie in der Quelle steht.** Kleinschreibung,
Zusammenführen von Schreibweisen, das Erkennen derselben Person hinter zwei
Adressen: alles Deutung, alles später (Identitätsgraph).

**Wo es im Log steht.** `append` mischt `artifact_hash`, `channel_identities`
und `raw` unter diesen drei Namen in die Nutzlast, wie es das heute mit
`evidence` tut, und weist eine Nutzlast ab, die einen der vier Namen schon
trägt. Damit sind sie vom `payload_hash` gedeckt, und eine Tilgung der
Nutzlast nimmt sie mit — bei Adressen und Namen ist das gewollt. Hashes
stehen als Hexzeichenkette, weil der Nutzlastbereich keine Bytes kennt.

### 2.2 Die Inhaltsidentität des Artefakts

`artifact_hash` ist ein SHA-256 über das, **was gleich sein muss, damit zwei
Sichtungen dasselbe Artefakt sind**. Der Konnektor legt fest, was das ist, und
schreibt es auf seiner Reference-Seite hin.

Warum nicht die Einheiten vergleichen, und warum nicht die Nutzlast:

- **Die Einheiten** sind eine Ableitung. Dieselbe Mail ergibt nach einer
  Verbesserung der Zerlegung oder mit einer neuen Fassung des
  HTML-Umwandlers andere Einheiten; jede Wiedersichtung wäre dann ein
  Konflikt, obwohl sich an der Mail nichts geändert hat.
- **Die Nutzlast** trägt den Transport. Dieselbe Mail liegt in zwei
  Postfächern mit verschiedenen `Received`-Zeilen; der 1a-Spec verlangt in §5
  ausdrücklich, dass sie trotzdem **ein** Event ist.

Die Regel in `append`, für einen Schlüssel `(source, external_id)`, den es
schon gibt:

| Das vorhandene Event … | Ergebnis |
|---|---|
| trägt denselben `artifact_hash` wie das ankommende | bekannt: dieselbe `id`, nichts geschrieben |
| trägt einen anderen | **abgewiesen** mit `ArtifactChanged`, die Schlüssel und beide Hashes nennt; der ganze Stapel wird nicht geschrieben |
| ist getilgt (Nutzlast `NULL`) | bekannt. Eine Wiedersichtung darf eine Tilgung nicht rückgängig machen |
| trägt keinen `artifact_hash` (vor dieser Einheit geschrieben) | bekannt, wie bisher |

`ArtifactChanged` ist ein `PreviouslyError`. Der Fehler ist die Auskunft „die
Quelle hat unter einem Schlüssel, der Stabilität verspricht, etwas anderes
geliefert" — und **was dann geschieht, entscheidet der Aufrufer, nie
`append`**:

- Die Kommandozeile (`previously append`) meldet den Fehler und endet mit
  Rückgabecode 2. Ihr `artifact_hash` ist der SHA-256 des übergebenen Texts.
- Ein Konnektor, dessen Artefakte sich **ändern können** (ein Issue, eine
  Datei), trägt die Fassung im Schlüssel; für ihn ist `ArtifactChanged` ein
  Programmfehler.
- Ein Konnektor, dessen Artefakte sich **nicht ändern sollten** (eine Mail),
  nimmt das Abweichende unter einem **Variantenschlüssel** auf (§3.5). Nichts
  geht verloren, und nichts blockiert den Lauf.

Der Vergleich kostet eine Abfrage je Wiedersichtung: `lookup` liefert die
`id`, `read` das vorhandene Event. Das Protokoll `LogStore` bleibt, wie es
ist.

### 2.3 Der Rohverweis

Leitsatz 6 verlangt die Rohinhalte. Bis Stufe 1c einen Ort für Bytes baut,
trägt das Event den Verweis: `sha256` über die Rohbytes, `size`, und in
`locator` die Fundstelle in der Schreibweise der Quelle. Für IMAP:
`imap://<host>/<ordner>;uidvalidity=<n>;uid=<n>` — ohne Benutzer, ohne
Geheimnis.

Was der Verweis leistet: wer die Rohmail später holt, kann prüfen, dass sie
dieselbe ist. Was er nicht leistet: sie aufbewahren. Der `locator` wird
falsch, sobald die Mail verschoben wird; der Hash bleibt richtig.

Der Rohverweis gehört zur **ersten Sichtung**. Liegt dieselbe Mail ein zweites
Mal vor, mit anderen Transportzeilen und darum anderen Rohbytes, ist sie
bekannt, und der zweite Verweis wird nicht geschrieben. Das ist der Preis der
Regel aus 1a §5, und er steht hier, damit ihn niemand für ein Versehen hält.

---

## 3. Eine Mail als Event

### 3.1 Die Abbildung

| Feld | Wert |
|---|---|
| `source` | `imap` |
| `external_id` | die Message-ID aus dem Kopf, ohne die spitzen Klammern und ohne Leerraum am Rand; sonst unverändert |
| `occurred_at` | der Kopf `Date`, wenn er sich als Zeitpunkt mit Zone lesen lässt; sonst die Eingangszeit des Servers (`INTERNALDATE`) |
| `evidence` | `verbatim` |
| `units` | §3.2 |
| `artifact_hash` | §3.3 |
| `channel_identities` | aus `From`, `Sender`, `Reply-To`, `To`, `Cc`, `Bcc`, in der Reihenfolge des Kopfs |
| `raw` | §2.3 |
| `payload` | §3.4 |

### 3.2 Einheiten

Erst der **Betreff** als Einheit 1, dann die Absätze des Textkörpers über
`split_plaintext`, Zitate und Signatur eingeschlossen.

- **Der Betreff ist Inhalt.** Ohne ihn zeigt die Chronik eine Mail ohne das,
  woran ein Mensch sie erkennt. Fehlt der Betreff oder ist er leer, beginnt
  die Zählung beim ersten Absatz.
- **Welcher Körper.** Der Teil `text/plain`, wenn es einen gibt. Sonst der
  Teil `text/html`, mechanisch in Text umgewandelt (§7.3). Welcher Teil es war
  und welcher Umwandler in welcher Fassung, steht in der Nutzlast.
- **Zitate und Signaturen bleiben.** Sie zu erkennen und abzutrennen ist
  Deutung.
- **Keine Einheit ohne Inhalt.** Hat eine Mail weder Betreff noch lesbaren
  Körper — verschlüsselt, nur Anhänge —, bekommt sie eine einzige Einheit mit
  einem festen englischen Satz, der sagt, warum (`no readable body:
  encrypted` und Entsprechendes). Ein Event ohne Einheiten weist `append` ab,
  und die Mail nicht aufzunehmen wäre der schlechtere Verlust.
- **Zeichen, die das Log nicht hält.** Ein Nullbyte und ein Zeichen, das sich
  mit dem erklärten Zeichensatz nicht lesen lässt, werden durch U+FFFD
  ersetzt; die Nutzlast vermerkt, dass ersetzt wurde. Die Rohbytes sind über
  den Verweis prüfbar.

### 3.3 Die Inhaltsidentität einer Mail

SHA-256 über die kanonische Form (die des Projekts, wie für den
`payload_hash`) von:

```
{"subject": <Betreff, dekodiert, oder null>,
 "body": <SHA-256 der dekodierten Bytes des gewählten Körperteils, hex, oder null>,
 "attachments": [<SHA-256 je Anhang, hex, sortiert>]}
```

Dekodiert heißt: nach dem Auflösen der Transportkodierung, vor jeder
Umwandlung in Text. `null` steht, wo es keinen Betreff oder keinen lesbaren
Körper gibt. Damit ist die Identität unabhängig vom Umwandler, von der
Zerlegung und vom Transport — und sie ändert sich, wenn sich Betreff, Körper
oder ein Anhang ändert.

### 3.4 Die Nutzlast

Schlüssel in Kleinbuchstaben, wie der Nutzlastbereich es verlangt:

| Schlüssel | Inhalt |
|---|---|
| `headers` | **alle** Kopfzeilen als Liste von Paaren `[Name, Wert]`, in der Reihenfolge der Mail, Namen wie geschrieben. Als Liste, weil Namen wie `Message-ID` keine gültigen Schlüssel sind und weil Kopfzeilen mehrfach vorkommen |
| `date_source` | `header` oder `internaldate` |
| `internaldate` | die Eingangszeit des Servers, ISO 8601 |
| `folder`, `uidvalidity`, `uid` | wo die Mail bei dieser Sichtung lag |
| `body` | `{"part": …, "charset": …, "converter": … oder null, "replaced": true/false}` |
| `attachments` | Liste von `{"filename", "content_type", "size", "sha256"}` |
| `variant_of` | nur bei einer Variante (§3.5): die Message-ID, unter der schon ein anderer Inhalt liegt |

Der Ordner ist **keine Eigenschaft der Mail**. Er sagt, wohin der Betreuer sie
gelegt hat, und das ist seine Aussage über sie. Hier steht er als Fundort der
ersten Sichtung; mit Einheit 5 wird aus dem Ablegen in einen Ordner eine
Zuordnung mit dem Betreuer als Verantwortlichem.

Der Text der Mail steht **nicht** in der Nutzlast. Er steht in den Einheiten;
der Prüfpunkt hat gemessen, dass er sonst dreimal in der Datenbank liegt.

### 3.5 Fälle, die echte Post mitbringt

| Fall | Verhalten |
|---|---|
| **Keine Message-ID** | `external_id` ist `sha256:` und der `artifact_hash` in Hex. Artefaktstabil, wie 1a §5 es verlangt |
| **Dieselbe Message-ID, derselbe Inhalt** (zwei Kopien, andere Transportzeilen) | bekannt, ein Event |
| **Dieselbe Message-ID, anderer Inhalt** (von einer Liste verändert, oder gefälscht) | eigenes Event unter dem Variantenschlüssel `<Message-ID>#<erste 16 Hexzeichen des artifact_hash>`; die Nutzlast trägt `variant_of` mit der Message-ID. Der Lauf zählt die Variante und nennt sie in seiner Ausgabe |
| **`Date` fehlt oder ist unlesbar** | `INTERNALDATE`, und `date_source` sagt es |
| **Nur HTML** | umgewandelt, §7.3 |
| **Verschlüsselt oder signiert** | signiert: der lesbare Teil; verschlüsselt: die eine Einheit aus §3.2. Entschlüsselt wird nichts |
| **Eine Mail als Anhang** (`message/rfc822`) | ein Anhang wie jeder andere: Name, Typ, Größe, Hash |
| **Unbekannter Zeichensatz** | als Latin-1 gelesen, `replaced` vermerkt es |

---

## 4. Der Konnektor und der Lauf

### 4.1 Vertrag

In `contract`:

```python
@dataclass(frozen=True)
class Watermark:
    connector: str
    position: Mapping[str, str]       # konnektorspezifisch, für core undurchsichtig
    set_at: datetime

@dataclass(frozen=True)
class Fetched:
    event: RawEvent
    position: Mapping[str, str]       # gilt, sobald dieses Event angefügt ist
    variant: RawEvent | None = None   # dasselbe unter dem Variantenschlüssel (§3.5)

class Connector(Protocol):
    name: str
    def ingest(self, since: Watermark | None) -> Iterator[Fetched]: ...
```

`variant` ist die Antwort des Konnektors auf die Frage, die `append` mit
`ArtifactChanged` stellt, im Voraus gegeben: dasselbe Event unter einem
Schlüssel, der den abweichenden Inhalt trägt. Ein Konnektor, dessen Artefakte
die Fassung schon im Schlüssel haben, lässt es leer.

`Capability`, `Renderer` und `Target` aus §6 der Architektur kommen mit der
ersten Quelle, die sie braucht. Heute gäbe es für jedes genau einen Wert.

### 4.2 Der Lauf

In `core`, eine Funktion: sie liest das Wasserzeichen des Konnektors, zieht
`Fetched` in Stapeln von höchstens `MAX_BATCH`, fügt jeden Stapel mit
`append` an und schreibt **danach** das Wasserzeichen auf die Position des
letzten Events im Stapel (Architektur §6.3). Bricht der Lauf zwischen Anfügen
und Wasserzeichen ab, holt der nächste dieselben Mails noch einmal und läuft
idempotent ins Leere.

Meldet `append` `ArtifactChanged`, ersetzt der Lauf das eine Event, das der
Fehler nennt, durch seine `variant` und fügt den Stapel erneut an. Hat das
Event keine, geht der Fehler durch.

**Derselbe Schlüssel zweimal in einem Stapel** ist für `append` ein Fehler
(1a-Spec §5). Bei zwei Kopien einer Mail im selben Ordner ist es der
Normalfall. Der Lauf entdoppelt darum vor dem Anfügen, nach derselben Regel
wie `append` zwischen Aufrufen: gleiche Inhaltsidentität ist bekannt, andere
ist eine Variante.

Der Lauf gibt zurück, was geschah: angefügt, bekannt, Varianten, und die
Position, bis zu der das Wasserzeichen steht. Sätze macht die Kommandozeile.

Das Wasserzeichen liegt in einer neuen Tabelle `watermark` (`connector` als
Schlüssel, `position` als `jsonb`, `set_at`), hinter einem dritten Protokoll
`WatermarkStore` mit zwei Methoden. Migration `0003`.

### 4.3 IMAP

- **Die Standardbibliothek**: `imaplib` und `email`. Keine neue Abhängigkeit
  für den Zugriff.
- **Nur über TLS von der ersten Zeile an** (IMAPS), mit geprüftem Zertifikat.
  Ohne TLS verbindet der Konnektor nicht; ein Schalter dafür ist nicht
  vorgesehen.
- **Ordnernamen mit Umlauten.** IMAP schreibt Ordnernamen in einer eigenen
  Kodierung (RFC 3501, „modified UTF-7"), und die Standardbibliothek
  übersetzt sie nicht. Der Konnektor tut es; ein Ordner namens „Kunde Müller"
  ist der erwartbare Fall, nicht die Ausnahme.
- **Eine Mail nach der anderen.** Der Konnektor holt und wandelt Mail für
  Mail; die Rohbytes einer Mail samt Anhängen liegen nie länger im Speicher
  als ihre eigene Abbildung dauert.
- **Anmeldung mit Benutzer und Passwort.** OAuth (`XOAUTH2`) ist nicht
  enthalten; ob der Pilot es braucht, hängt am Mailserver des Betreuers und
  ist vor dem Plan zu klären (§11).
- **Gelesen wird mit `BODY.PEEK[]`**: der Ordner bleibt, wie er ist, keine
  Mail wird als gelesen markiert.
- **Position:** `uidvalidity` und die höchste angefügte `uid`. Ändert der
  Server die `UIDVALIDITY`, beginnt der Lauf von vorn; die Idempotenz fängt
  es auf.
- **Ein Ordner je Lauf.** Der Name kommt aus der Umgebung.
- **Gelöschte und verschobene Mails** bleiben im Log. Das Log ist append-only;
  der Ordner ist die Eingangstür, nicht der Spiegel.

---

## 5. `previously ingest imap`

Das neunte Kommando, in der Folge `COMMANDS`.

**Eingabe**, aus der Umgebung: `PREVIOUSLY_IMAP_HOST`, `PREVIOUSLY_IMAP_PORT`
(Vorgabe 993), `PREVIOUSLY_IMAP_USER`, `PREVIOUSLY_IMAP_PASSWORD`,
`PREVIOUSLY_IMAP_FOLDER`. Fehlt eine Pflichtangabe, ist das ein
Eingabefehler, bevor verbunden wird.

**Ausgabe** auf die Standardausgabe, eine Zeile:

```
imap: 12 appended, 3 known, 0 variants, up to uid 4711
```

Jede Variante zusätzlich als eigene Zeile auf die Standardfehlerausgabe, mit
Message-ID und `id` des neuen Events. Das Passwort erscheint in keiner
Ausgabe und in keiner Fehlermeldung, wie heute das der Datenbank.

**Rückgabecodes:** 0 der Lauf ging durch, auch mit Varianten; 2 Eingabe-,
Verbindungs-, Anmelde- oder Storagefehler. Eine Variante ist kein Fehler: die
Mail ist aufgenommen.

`ingest` ruft `project` nicht. Wer die Projektionen aktuell will, ruft es
danach.

---

## 6. Was das für den Betrieb heißt

`CLAUDE.md` verlangt die Aussage in jedem Spec, gegen zwei Hostingformen.

- **kup6s.** Ein `CronJob` mit dem Image der Anwendung ruft `previously ingest
  imap` und danach `previously project`, mit `concurrencyPolicy: Forbid` —
  das ersetzt für den Piloten die Sperre auf der Zustandszeile, die es noch
  nicht gibt (Landkarte, *Warteschlange*). Die fünf Angaben kommen aus einem
  Secret. Der Job braucht ausgehend den Mailserver auf Port 993 und sonst
  nichts Neues. Gebaut wird das in Einheit 2.
- **Ein Host mit `docker-compose`.** Eine Zeile in der Crontab, die dieselben
  zwei Kommandos im Container ruft, und eine Umgebungsdatei mit den fünf
  Angaben, lesbar nur für den, der den Dienst betreibt.

**Der Einfachheits-Check** fällt gut aus: ein Kommando, ein Zeitgeber, fünf
Angaben, eine Tabelle. Er findet auch etwas: das Passwort eines Postfachs
liegt künftig beim Dienst. Darum der eigene Ordner — und die Empfehlung an
den Betrieb, dafür ein eigenes Postfach oder ein App-Passwort zu nehmen, das
nur liest.

**Was der Pilot dem Betrieb zusätzlich abverlangt:** der IMAP-Ordner ist das
Archiv der Rohbytes (§1.1). Er gehört in die Sicherung des Postfachs, nicht
in die der Datenbank, und wer ihn aufräumt, löscht Belege.

---

## 7. Schnitt im Code

### 7.1 Module

| Ort | Was |
|---|---|
| `contract/types.py` | `ChannelIdentity`, `RawRef`, die neuen Felder an `RawEvent`, `Watermark`, `Fetched` |
| `contract/connector.py` | `Connector` |
| `contract/store.py` | `WatermarkStore` |
| `core/append.py` | das Einmischen der drei Namen, der Vergleich, `ArtifactChanged` |
| `core/ingest.py` | der Lauf |
| `core/mail.py` | Rohbytes einer Mail zu `RawEvent`: rein, ohne Netz, ohne Datenbank |
| `connectors/imap.py` | der Zugriff: verbinden, Ordner wählen, holen, `core.mail` rufen |
| `storage/` | Tabelle `watermark`, Migration `0003`, die zwei Methoden |
| `cli.py` | das Kommando; liest die Umgebung und formatiert |

`core/mail.py` gehört nach `core` und nicht in den Konnektor, weil dieselbe
Abbildung später für eine Mail aus einer Datei gilt, die im Nextcloud-Ordner
liegt.

### 7.2 Grenzen

Ein neues Modul `previously.connectors`, in den Schichten über `core` und
unter `cli`. Nur dort — und in keinem anderen Modul — steht ein Import von
`imaplib`. Der import-linter-Vertrag dafür wird namentlich aufgezählt, wie
die bestehenden.

### 7.3 Abhängigkeiten

**Eine neue: der Umwandler von HTML nach Text.** Geprüft am 2026-10-04 an den
Registern:

| Kandidat | letzte Veröffentlichung | bringt mit | Ausgabe |
|---|---|---|---|
| `inscriptis` 2.7.5 | 2026-09-29, drei Veröffentlichungen in zehn Wochen | `lxml`, `requests` | Text mit Layout |
| `html2text` 2025.4.15 | 2025-04-15, davor 2024-02 | nichts | Markdown |
| `beautifulsoup4` 4.15.0 | 2026-06-07 | `soupsieve`, `typing-extensions` | `get_text`, ohne Layout |

Die Wahl fällt **im Plan, mit einer Messung** an den Testmails: welcher
Kandidat aus einer HTML-Mail Absätze macht, die `split_plaintext` als
Einheiten trennt, und was jeder mit Tabellen, Zitatblöcken und Signaturen tut.
Zwei Bedingungen stehen fest: der Umwandler holt **nichts aus dem Netz**
(keine Bilder, keine Stylesheets), und seine Fassung steht in der Nutzlast
(§3.4). Das Urteil kommt mit Datum und Beleg nach `DEPENDENCIES.md`.

**Der Testserver** ist kein Paket, sondern ein Image: GreenMail
(`greenmail/standalone`, 2.1.14 vom 2026-09-19, Repository zuletzt am
2026-10-04 bewegt), über das schon vorhandene `testcontainers`.

---

## 8. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, von dem gemessen ist, dass er bricht, und
eine Kontrolle, die gemessen grün bleibt. Gegen echtes PostgreSQL und einen
echten IMAP-Server im Container; kein Mock für Zeit, Datenbank oder Zufall.
**Testmails sind erfunden**, auf Deutsch und Englisch gemischt, nie
Kundenpost.

1. **Gleicher Schlüssel, gleicher Inhalt: bekannt.** Wie bisher.
2. **Gleicher Schlüssel, anderer Inhalt: abgewiesen, nichts geschrieben.** Die
   Messung M1 des Prüfpunkts als Test. Mutation: der Vergleich entfällt.
3. **Eine Tilgung wird nicht rückgängig gemacht.** Ein getilgtes Event,
   derselbe Schlüssel noch einmal: bekannt.
4. **Die drei Namen sind reserviert**, wie `evidence`.
5. **Zwei Kopien einer Mail mit verschiedenen Transportzeilen: ein Event.**
   Mutation: die Transportzeilen gehen in die Inhaltsidentität.
6. **Dieselbe Message-ID, anderer Körper: zwei Events, keins verloren.**
7. **Ein zweiter Lauf fügt nichts an.**
8. **Das Wasserzeichen folgt dem Anfügen.** Ein Konnektor, der nach dem
   dritten Event abbricht: das Wasserzeichen steht bei dem, was angefügt ist,
   und der nächste Lauf holt den Rest. Mutation: das Wasserzeichen wird vor
   dem Anfügen geschrieben.
9. **Geänderte `UIDVALIDITY`: von vorn, und nichts doppelt.**
10. **Der Ordner bleibt, wie er ist.** Nach dem Lauf ist keine Mail als
    gelesen markiert. Mutation: `BODY[]` statt `BODY.PEEK[]`.
11. **Das Passwort erscheint nirgends**, auch nicht bei falscher Anmeldung.
12. **Die Abbildung, Fall für Fall** aus §3.5, an Testmails als Dateien, ohne
    Server.
13. **Was `cli.md` und die Reference der Mail-Abbildung zitieren**, wird gegen
    den Code gehalten, wie die bestehenden Zitate.

---

## 9. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`, eine Seite je Quadrant.

- **Explanation, neu: Konnektoren.** Der Vertrag; warum der Schlüssel das
  Artefakt bezeichnet; die Inhaltsidentität und warum weder Einheiten noch
  Nutzlast sie tragen; die Variante; der Rohverweis und was er nicht leistet;
  warum der Ordner keine Eigenschaft der Mail ist.
- **Explanation, bestehend:** `module-boundaries.md` (die neue Schicht),
  `silent-losses.md` oder die Seite, die den stillen Verlust unter bekanntem
  Schlüssel heute als offen führt.
- **Reference:** `cli.md` (`ingest`, neunmal statt achtmal); die
  Konfiguration (fünf Angaben); das Schema (`watermark`); neu: **die
  Abbildung einer Mail**, als Tabellen.
- **How-to, neu:** einen Mail-Ordner aufnehmen — Ordner anlegen, Angaben
  setzen, laufen lassen, lesen, was der Lauf sagt; und was „tilgen" im
  Piloten heißt.
- **README:** neun Kommandos, die sechste Zeile der eingefrorenen Berichte
  beim Einfrieren.
- **Landkarte:** der Weg des Piloten, und was diese Einheit schließt.

Das Tutorial bleibt beim Einwurf von Hand; es bekommt keinen Mailserver.

---

## 10. Abnahme

| # | Bedingung |
|---|---|
| 1 | `RawEvent` trägt `artifact_hash`, `channel_identities` und `raw`; `append` mischt sie ein und reserviert die Namen. |
| 2 | Gleicher Schlüssel mit anderem Inhalt wird abgewiesen; M1 des Prüfpunkts ist ein Test. |
| 3 | Eine Mail wird nach §3 zum Event; jeder Fall aus §3.5 hat einen Test. |
| 4 | `previously ingest imap` nimmt einen Ordner auf; ein zweiter Lauf fügt nichts an. |
| 5 | Das Wasserzeichen wird erst nach dem Anfügen geschrieben. |
| 6 | Der Ordner wird nicht verändert; das Passwort erscheint nirgends. |
| 7 | `core` importiert weder `imaplib` noch SQL; die neue Schicht hat ihren Vertrag. |
| 8 | Jede Zusicherung aus §8 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 9 | Die Dokumente aus §9 stehen. |
| 10 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 11 | **Ein Lauf gegen den echten Ordner des Betreuers, von ihm, lokal:** Mails hinein, `previously project`, `previously chronicle` zeigt sie mit Betreff; ein zweiter Lauf meldet `0 appended`. Was dabei auffällt, geht in die Landkarte. |

Abgenommen ist die Arbeit mit dem Merge nach `main`.

---

## 11. Was offen bleibt

Gepflegt, solange der Spec lebt; beim Einfrieren gehen die Punkte in die
Landkarte.

1. **OAuth für IMAP.** Verlangt der Mailserver des Betreuers `XOAUTH2`,
   gehört es in diese Einheit und nicht in eine spätere. **Vor dem Plan zu
   klären.**
2. **Mehrere Ordner, mehrere Postfächer.** Ein Ordner je Lauf genügt dem
   Piloten. Unterordner je Organisation (Entwurf §11.4) kommen mit der
   Zuordnung.
3. **Der Inhalt von Anhängen**, und die Rohbytes selbst: Stufe 1c.
4. **Eine Änderung nur in der Nutzlast.** Die Inhaltsidentität deckt, was der
   Konnektor in sie legt. Ein Konnektor für Issues muss den Zustand in sie
   aufnehmen oder die Fassung in den Schlüssel; das ist eine Vorgabe an den
   Konnektor, kein Mechanismus.
5. **Der zweite Rohverweis geht verloren** (§2.3). Mit dem Blob-Speicher
   ließe sich jede Sichtung aufbewahren.
6. **`occurred_at` aus dem Kopf `Date`** ist die Uhr des Absenders und kann
   falsch sein. Beide Zeiten stehen in der Nutzlast; welche die Chronik
   ordnen soll, wenn sie weit auseinanderliegen, ist nicht entschieden.
7. **`IDLE`**, also Aufnahme ohne Zeitgeber: nicht vorgesehen.
8. **Der Variantenschlüssel in der Chronik.** Eine Variante erscheint als
   zweites Event; die Chronik sagt nicht, dass sie eine ist.
