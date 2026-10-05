# Pilot, Einheit 1: Aufnahme aus IMAP — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mails aus einem IMAP-Ordner werden Events im Log, mit Rohmail und Anhängen als Blobs, über einen Konnektor-Vertrag, den spätere Quellen mitbenutzen.

**Architecture:** `RawEvent` bekommt eine Inhaltsidentität (`artifact_hash`) und Kanalidentitäten; `append` vergleicht die Identität unter einem bekannten Schlüssel. `core/mail.py` bildet Rohbytes rein auf `RawEvent` ab (Standardbibliothek `email`, HTML über `html2text`), `core/ingest.py` speichert Blobs, fügt Stapel an und schreibt danach das Wasserzeichen; `connectors/imap.py` holt nur Bytes über `imaplib`. `previously ingest imap` verbindet die drei.

**Tech Stack:** Python 3.14, `email`, `imaplib`, `html2text` 2025.4.15, SQLAlchemy Core, Alembic, PostgreSQL 17, RustFS, GreenMail 2.1.14 als Testserver.

**Spec:** `docs/superpowers/specs/2026-10-06-pilot-imap-aufnahme.md` (Commits `eb9c342`..`823ad96`, vom Betreuer am 2026-10-06 durchgesehen: „passt so").

---

## Was der Plan vorgibt und was nicht

Gelaufen, Wegwerfcode im Scratchpad, nicht übernommen:

- **IMAP, 2026-10-05**, gegen GreenMail 2.1.14 (`greenmail/standalone`), IMAPS
  auf 3993 mit selbst signiertem Zertifikat: `imaplib.IMAP4_SSL`,
  `select('"Kunde M&APw-ller"', readonly=True)`, `uid("SEARCH", "UID", "2:*")`
  liefert `b'2 3 4'`; `uid("FETCH", "1:*", "(UID BODY.PEEK[])")` gibt die
  Rohbytes, ohne `\Seen` zu setzen; `STATUS` gibt `UIDVALIDITY`. GreenMail
  speichert Zeilenenden als CRLF; geklammerte Suchen (`(UID 2:*)`) weist es ab.
- **`email` gegen `imap-tools`, 2026-10-05**: `email.message_from_bytes(raw,
  policy=email.policy.default)` hält Reihenfolge und Dubletten der Kopfzeilen
  (`raw_items()`), `get_body(preferencelist=("plain","html"))` wählt den Teil,
  ein unbekannter Zeichensatz wirft `LookupError` (also erkennbar), eine
  weitergeleitete Mail bleibt ein Teil `message/rfc822`.
- **HTML nach Text, 2026-10-06**, an sechs erfundenen HTML-Mails (Absätze,
  Outlook-`MsoNormal`, Gmail-`div`s, `blockquote`, Tabelle, Bild mit Stil):

  | Kandidat | Ergebnis | Typen | Abhängigkeiten |
  |---|---|---|---|
  | `html2text` 2025.4.15 | Absätze wie gemeint; Zitate als `> …`; Tabellen als Markdown-Pipes; ein `<br>` als Markdown-Umbruch (zwei Leerzeichen am Zeilenende) | `py.typed` | keine |
  | `inscriptis` 2.7.5 | Absätze wie gemeint; Tabellen lesbar; die Markierung eines Zitats geht verloren | keine | `lxml`, `requests` |
  | `beautifulsoup4` 4.15.0 | trennt Signatur und Tabellenzellen in eigene Einheiten | — | `soupsieve`, `typing-extensions` |

  Keiner holt beim Umwandeln etwas aus dem Netz (gemessen mit gesperrtem
  `socket.connect` und Bild, Stylesheet, `iframe` mit fremder URL).

**Nicht gelaufen**, darum hier nur als Anforderung mit Tests: die Abbildung im
Ganzen, der Lauf, das Kommando.

## Was der Plan am Spec entscheidet

1. **Der Umwandler ist `html2text`** (Messung oben): Typen für pyright strikt,
   keine Abhängigkeit, und das Zitat bleibt als `> …` markiert — das Signal,
   das ein späteres Ausblenden zitierter Verläufe braucht (Spec §11).
   Einstellungen: `body_width = 0` (kein Umbruch), `ignore_images = True`
   (sonst stünden Adressen von Zählpixeln im Text), Links bleiben (ein Link
   zu einer Konferenz ist ein Signal, Spec §11). Fassung in der Nutzlast
   (`body.converter`). Das Urteil nach `DEPENDENCIES.md`: letzte Fassung
   2025-04-15, Repository zuletzt 2025-10-28 bewegt, 99 offene Issues —
   „fertig, nicht verlassen", wie `hatch-vcs`; wird es verlassen, ist der
   Umwandler eine Funktion in `core/mail.py`, und die Tabelle oben nennt den
   Ersatz.
2. **`Fetched` trägt Bytes** (Spec §4.1); die Abbildung macht der Lauf, nicht
   der Konnektor.
3. **Die Tiefe für Mails im Anhang** ist fünf (Spec §3.6), als Konstante
   `MAX_FORWARD_DEPTH = 5` in `core/mail.py`.
4. **`artifact_hash` von `previously append`**: SHA-256 der kanonischen Form
   von `{"text": <Text>, "attachments": [<Adressen, sortiert>]}` — dieselbe
   Kanonisierung wie in `core/mail.py`.
5. **Ein Ereignis mit Variante** bekommt im Lauf seinen Variantenschlüssel
   vor dem zweiten Versuch; `append` selbst bleibt ohne Wissen über Varianten.
6. **GreenMail** kommt als Fixture in `tests/conftest.py` dazu, wie RustFS:
   `DockerContainer("greenmail/standalone:2.1.14")`, IMAPS auf 3993,
   Zertifikat im Test nicht geprüft — der Konnektor nimmt dafür einen
   `ssl.SSLContext` als Parameter, und nur der Test reicht einen
   ungeprüften. Die Kommandozeile reicht immer den geprüften
   (`ssl.create_default_context()`); es gibt keinen Schalter.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten,
  Handoff **englisch**; Spec, Plan, Landkarte deutsch.
- Die sechs Tore, jedes für sich, vor jeder Fertigmeldung:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `uv run pip-audit --skip-editable` ohne Befund zur Abnahme.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung (fünf, `CLAUDE.md`).
- Kein Mock für Zeit, Datenbank, Speicher oder Zufall. Ein Konnektor aus dem
  Speicher (Bytes in einer Liste) ist ein Testdouble des Protokolls, kein Mock
  dieser vier — zulässig für den Lauf; der IMAP-Weg selbst läuft gegen GreenMail.
- **Testmails sind erfunden**, deutsch und englisch gemischt, nie Kundenpost;
  das Repository ist öffentlich.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener
  Zusicherung, mit einer grünen Kontrolle.
- **Arbeitsregel vom 2026-10-05:** ein Befund, der nur bei Fehlbedienung
  auftritt, wird benannt, nicht gejagt.
- Ein Kommentar ist eine Behauptung; Zahlen darin gemessen.
- Getippte Ausgabe ist eine Messung; der Testblock des Tutorials wird aus
  einem grünen Lauf neu getippt, wenn sich die Zahl ändert.
- Commits: Dateien namentlich, `git commit -F`, Trailer
  `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | `ingest imap`, stdout | `imap: <n> appended, <n> known, <n> variants, up to uid <uid>` |
  | `ingest imap`, stderr je Variante | `variant of <message-id>: event <id>` |
  | `ArtifactChanged` | `<source>/<external_id> is known with another content (artifact <alt> ≠ <neu>)` — die Hashes als die ersten 16 Hexzeichen |
  | Hilfe | `ingest` — `take in new mail from an IMAP folder` |
  | Einheit ohne Inhalt | `no readable body: encrypted`, `no readable body: attachments only`, `no readable body: empty` |
  | Namen in der Nutzlast | `artifact_hash`, `channel_identities`, `headers`, `raw`, `date_source`, `internaldate`, `found_in`, `body`, `variant_of`, `forwarded_in` |

## Review Focus

1. **Eine Mail mit kaputtem MIME** (fehlende Grenze, abgeschnittener Teil):
   sie wird aufgenommen, so gut es geht, statt den Lauf anzuhalten — die
   Rohmail liegt als Blob. → Aufgabe 2, Fall `broken_mime`.
2. **Ein Ordner mit mehreren hundert Mails beim ersten Lauf**: Stapel, kein
   Abbruch an `MAX_BATCH`, das Wasserzeichen wächst je Stapel. → Aufgabe 4.
3. **Eine sehr große Mail** (mehrere zehn MB Anhang): eine Mail nach der
   anderen im Speicher, der Anhang als Strom in den Speicher. → Aufgabe 4,
   eine Mail mit 20 MB Anhang, Spitzenspeicher gemessen.
4. **Ein Server, der während des Laufs die Verbindung schließt**: ein Satz,
   Rückgabecode 2, das Wasserzeichen steht beim letzten angefügten Stapel.
   → Aufgabe 5.
5. **Ein Ordnername mit Umlaut und Leerzeichen** („Kunde Müller"). → Aufgabe 5.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/contract/types.py` | 1, 3 | `ChannelIdentity`, neue Felder an `RawEvent`; `Watermark`, `Fetched` |
| `src/previously/core/append.py` | 1 | Namen einmischen und reservieren, Identität vergleichen |
| `src/previously/core/errors.py` | 1 | `ArtifactChanged` |
| `src/previously/core/identity.py` | 1 | `artifact_hash_of(...)`, die eine Kanonisierung für beide Aufrufer |
| `src/previously/cli.py` | 1, 5 | `append` setzt `artifact_hash`; `ingest imap` |
| `src/previously/core/mail.py` | 2 | Rohbytes → `Mapped` (Event, Anhänge, innere Mails) |
| `src/previously/contract/connector.py` | 3 | `Connector` |
| `src/previously/contract/store.py` | 3 | `WatermarkStore` |
| `src/previously/storage/schema.py`, `postgres.py`, `src/previously/migrations/versions/0005_watermark.py` | 3 | Tabelle, Migration, zwei Methoden |
| `src/previously/core/ingest.py` | 4 | der Lauf |
| `src/previously/connectors/__init__.py`, `imap.py` | 5 | IMAP |
| `.importlinter` | 5 | `previously.connectors` in den Schichten; nur dort `imaplib` |
| `tests/test_identity.py`, `test_append.py`, `test_mail.py`, `tests/mails/*.eml`, `test_watermark.py`, `test_ingest.py`, `test_imap.py`, `test_cli.py`, `conftest.py` | 1–5 | Tests |
| Seiten, Handoff, Landkarte, Spec | 6 | Doku |

---

## Task 1: Inhaltsidentität und Kanalidentitäten in `RawEvent` und `append`

**Files:** `contract/types.py`, `core/identity.py` (neu), `core/errors.py`, `core/append.py`, `cli.py` (`_cmd_append`), `tests/test_identity.py` (neu), `tests/test_append.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/hash-format.md` (die neuen Namen in der Nutzlast).

**Interfaces — Produces:**
```python
# contract/types.py
@dataclass(frozen=True)
class ChannelIdentity:
    channel: str
    role: str
    address: str
    name: str | None = None
# RawEvent bekommt, hinter `blobs`:
    artifact_hash: bytes | None = None
    channel_identities: tuple[ChannelIdentity, ...] = ()

# core/identity.py
def artifact_hash_of(document: Mapping[str, object]) -> bytes: ...   # SHA-256 der kanonischen Form (core/canonical)

# core/errors.py
class ArtifactChanged(PreviouslyError):
    source: str; external_id: str; known: bytes; arrived: bytes
```

- [ ] **Step 1: Tests, die scheitern** — in `tests/test_append.py`, gegen echtes PostgreSQL:
  - `test_same_key_same_artifact_is_known` — zweimal dasselbe Event mit `artifact_hash=h`: dieselbe `id`, ein Event im Log.
  - `test_same_key_other_artifact_is_refused_and_nothing_is_written` — die Messung M1 des Prüfpunkts: zweites Event mit anderem `artifact_hash` → `ArtifactChanged` mit beiden Hashes; das ganze Bündel nicht geschrieben (ein zweites, neues Event im selben Aufruf fehlt danach).
  - `test_an_erased_event_stays_known` — Event tilgen (`redact_event`), dann derselbe Schlüssel mit anderem Hash: bekannt, keine Ausnahme, keine Wiederherstellung.
  - `test_an_event_without_artifact_hash_stays_known` — vorhandenes Event ohne den Namen, neues mit Hash: bekannt.
  - `test_artifact_hash_and_channel_identities_land_in_the_payload` — Hex unter `artifact_hash`, Liste von Objekten unter `channel_identities` in Reihenfolge; vom `payload_hash` gedeckt (eine Änderung von Hand ist ein Befund von `verify`).
  - `test_the_new_names_are_reserved` — eine Nutzlast mit `artifact_hash` oder `channel_identities` wird abgewiesen, wie heute `evidence`.
  - In `tests/test_identity.py`: dasselbe Dokument in anderer Schlüsselreihenfolge gibt denselben Hash; ein Zeichen anders gibt einen anderen.
  - In `tests/test_cli.py`: `append --text A` zweimal: bekannt; dann `--text B` mit demselben `--external-id`: Rückgabecode 2 und der Satz von `ArtifactChanged` aus den Global Constraints.
- [ ] **Step 2: rot laufen lassen.**
- [ ] **Step 3: Umsetzen.** Die Prüfung liegt in `append` dort, wo heute ein bekannter Schlüssel erkannt wird: `lookup` gibt die `id`, ein `read` der Zeile gibt die Nutzlast; ihr `artifact_hash` (Hex) gegen den ankommenden. Getilgt heißt `payload is None`. Die Tabelle aus Spec §2.2 ist die Regel. `_cmd_append` setzt `artifact_hash_of({"text": text, "attachments": sorted(adressen)})`.
- [ ] **Step 4: grün; Mutationen:** der Vergleich entfällt → `…_is_refused…` rot; Getilgtes wird verglichen → `…_erased_event_stays_known` rot; Kontrolle grün.
- [ ] **Step 5: Seiten.** `cli.md`: `append` weist einen bekannten Schlüssel mit anderem Inhalt ab (Satz aus den Global Constraints, `test_docs_references` hält ihn); `hash-format.md`: die zwei neuen Namen in der Nutzlast.
- [ ] **Step 6: Sechs Tore; Testblock des Tutorials, wenn die Zahl sich ändert; Commit.**

---

## Task 2: Eine Mail als Event — `core/mail.py`

**Files:** `core/mail.py` (neu), `tests/test_mail.py` (neu), `tests/mails/*.eml` (neu, erfunden), `pyproject.toml` und `uv.lock` (`html2text>=2025.4`), `DEPENDENCIES.md`, `.importlinter` (nur `core.mail` importiert `html2text`; namentlich, wie `pyrage`).

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class Attachment:
    content: bytes            # dekodiert
    filename: str | None
    media_type: str

@dataclass(frozen=True)
class Mapped:
    event: RawEvent           # ohne `blobs`; `payload` ohne `raw`
    raw: bytes                # die Rohmail, Blob mit media_type "message/rfc822"
    attachments: tuple[Attachment, ...]
    inner: tuple["Mapped", ...]   # Mails im Anhang, §3.6, bis Tiefe MAX_FORWARD_DEPTH

MAX_FORWARD_DEPTH = 5
def map_mail(raw: bytes, *, internaldate: datetime, found_in: Mapping[str, str]) -> Mapped: ...
def variant_key(message_id: str, artifact_hash: bytes) -> str: ...   # "<id>#<16 hex>"
```

`map_mail` ist rein: kein Netz, keine Datenbank, keine Uhr (der Fallback für `occurred_at` ist `internaldate`, nicht „jetzt").

- [ ] **Step 1: Testmails** als Dateien unter `tests/mails/`, je eine erfundene Mail für: einfach (`text/plain`, Umlaute, zwei `Received`), nur HTML (Outlook-Absätze), HTML mit `blockquote`, ohne Message-ID, `Date` unlesbar, unbekannter Zeichensatz, verschlüsselt (`multipart/encrypted`), nur Anhänge, signiert (`multipart/signed`), Antwort mit `In-Reply-To`/`References`, weitergeleitet als Anhang mit leerer Rahmenmail, verschachtelt sechs tief, `broken_mime` (Grenze fehlt), zwei Anhänge mit gleichem Inhalt.
- [ ] **Step 2: Tests, die scheitern** — je Datei die erwarteten Felder nach Spec §3.1–§3.6: `source == "email"`, `external_id`, `occurred_at` und `date_source`, Einheiten (Betreff zuerst; der feste Satz bei keinem lesbaren Körper), `channel_identities` in Kopfreihenfolge, `headers` vollständig mit Dubletten, `body` (Teil, Zeichensatz, Umwandler samt Fassung, `replaced`), `artifact_hash` nach §3.3, `inner` bei Weiterleitung mit `forwarded_in`, Tiefe sechs → fünf entpackt, die sechste bleibt Anhang und die Nutzlast auf Tiefe fünf vermerkt es. Dazu: zwei Kopien derselben Mail mit verschiedenen `Received`-Zeilen haben denselben `artifact_hash`; ein anderer Körper einen anderen; der Text steht nirgends in der Nutzlast.
- [ ] **Step 3: rot.**
- [ ] **Step 4: Umsetzen** mit `email.message_from_bytes(raw, policy=email.policy.default)` (gemessen, siehe oben). HTML: `html2text.HTML2Text()` mit `body_width = 0`, `ignore_images = True`. Ein unbekannter Zeichensatz: als Latin-1 lesen, `replaced = True`. Nullbyte und Unlesbares: U+FFFD, `replaced = True`. Kaputtes MIME: was lesbar ist, und die Mail fällt nicht heraus.
- [ ] **Step 5: grün; Mutationen:** Transportzeilen gehen in den `artifact_hash` → der Kopien-Test rot; das Entpacken entfällt → der Weiterleitungs-Test rot; die Tiefe ohne Grenze → der Tiefe-sechs-Test rot; `Date` ohne Fallback → der Test mit unlesbarem `Date` rot.
- [ ] **Step 6: `DEPENDENCIES.md`** (Urteil aus „Was der Plan am Spec entscheidet", 1), sechs Tore, Commit.

---

## Task 3: Wasserzeichen und Konnektor-Vertrag

**Files:** `contract/types.py` (`Watermark`, `Fetched`), `contract/connector.py` (neu), `contract/store.py` (`WatermarkStore`), `storage/schema.py`, `storage/postgres.py`, `src/previously/migrations/versions/0005_watermark.py`, `tests/test_watermark.py` (neu), `tests/test_schema.py`, `docs/reference/database-schema.md`.

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class Watermark:
    connector: str
    position: Mapping[str, str]
    set_at: datetime

@dataclass(frozen=True)
class Fetched:
    raw: bytes
    position: Mapping[str, str]
    found_in: Mapping[str, str]
    internaldate: datetime

class Connector(Protocol):
    name: str
    def fetch(self, since: Watermark | None) -> Iterator[Fetched]: ...

class WatermarkStore[Conn](Protocol):
    def watermark(self, conn: Conn, connector: str) -> Watermark | None: ...
    def set_watermark(self, conn: Conn, mark: Watermark) -> None: ...
```

Tabelle `watermark`: `connector text PRIMARY KEY`, `position jsonb NOT NULL`, `set_at timestamptz NOT NULL`. Migration `0005_watermark`, mit `downgrade`, der sich weigert, wenn die Tabelle Zeilen hat (wie `0004`).

- [ ] **Steps:** Test zuerst (lesen eines fehlenden Wasserzeichens ist `None`; schreiben, lesen, überschreiben; `previously migrate` legt die Tabelle an; die Weigerung von `downgrade` mit Zeilen), rot, umsetzen, grün, Mutation (der `downgrade` ohne Weigerung → Test rot), `database-schema.md`, sechs Tore, Commit.

---

## Task 4: Der Lauf — `core/ingest.py`

**Files:** `core/ingest.py` (neu), `tests/test_ingest.py` (neu).

**Interfaces — Consumes:** `map_mail`, `variant_key`, `Mapped` (Aufgabe 2); `Connector`, `Fetched`, `Watermark`, `WatermarkStore` (3); `append`, `ArtifactChanged` (1); `store_blob`, `BlobStore` (Stufe 1c).
**Produces:**
```python
@dataclass(frozen=True)
class Ingested:
    appended: int
    known: int
    variants: tuple[tuple[str, int], ...]   # (Message-ID, neue id)
    position: Mapping[str, str] | None

def ingest[Conn](log: LogStore[Conn], marks: WatermarkStore[Conn], blobs: BlobStore,
                 connector: Connector, *, recipient: str, recorded_at: datetime) -> Ingested: ...
```
(Zwei Protokolle als zwei Parameter, beide dieselbe Speicherinstanz — die Form, die `core/redact.py` für `LogStore` und `RedactionStore` hat.)

Ablauf nach Spec §4.2: Wasserzeichen lesen; `fetch` in Stapeln bis `MAX_BATCH`; je `Fetched`: `map_mail`, Rohmail und Anhänge mit `store_blob` (als Strom über `io.BytesIO`), `BlobRef` ins Event (Rohmail zuerst, ohne Dateinamen; `payload["raw"]` = ihre Adresse); innere Mails ebenso, mit `forwarded_in`; Kopien desselben Schlüssels im Stapel zusammenlegen (gleiche Identität bekannt, andere Variante); `append`; bei `ArtifactChanged` das genannte Event unter `variant_key` mit `variant_of` und erneut anfügen; **danach** das Wasserzeichen.

- [ ] **Step 1: Tests, die scheitern** — mit einem Konnektor aus dem Speicher (eine Liste von `Fetched` aus den Testmails von Aufgabe 2), echtem PostgreSQL und RustFS:
  - zweimal laufen: der zweite fügt nichts an, `known` zählt alle;
  - zwei Kopien einer Mail mit verschiedenen Transportzeilen: ein Event, **eine** Rohmail im Bucket (die zweite Rohfassung wird nicht gespeichert);
  - dieselbe Message-ID mit anderem Körper: zwei Events, das zweite unter dem Variantenschlüssel, `variant_of` gesetzt;
  - ein Anhang in zwei Mails: ein Objekt im Bucket;
  - `blob get` der Rohmail gibt die Bytes byte-gleich zurück;
  - eine Weiterleitung als Anhang: zwei Events, `forwarded_in`;
  - **Wasserzeichen folgt dem Anfügen**: ein Konnektor, der nach dem dritten `Fetched` eine Ausnahme wirft — das Wasserzeichen steht beim letzten angefügten Stapel, der nächste Lauf holt den Rest und findet die Blobs vor;
  - ein getilgtes Event: der nächste Lauf nimmt die Mail nicht wieder auf;
  - **Review Focus 2**: 600 Mails im Konnektor, `MAX_BATCH` überschritten — alle angefügt, das Wasserzeichen wächst je Stapel;
  - **Review Focus 3**: eine Mail mit 20 MB Anhang — Spitzenspeicher des Laufs gemessen (`resource.getrusage`, wie die Speichertests von Stufe 1c, nur unter Linux) unter einer Grenze, die der Umsetzer misst und im Test begründet.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** das Wasserzeichen vor dem Anfügen → der Abbruch-Test rot; das Zusammenlegen im Stapel entfällt → der Kopien-Test rot; die Variante entfällt → der Varianten-Test rot.
- [ ] **Step 5: Sechs Tore, Commit.**

---

## Task 5: IMAP und `previously ingest imap`

**Files:** `connectors/__init__.py`, `connectors/imap.py` (neu), `cli.py`, `.importlinter`, `tests/conftest.py` (GreenMail), `tests/test_imap.py` (neu), `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`.

**Interfaces — Produces:**
```python
class ImapConnector:
    name: str      # "imap:<user>@<host>/<folder>"
    def __init__(self, *, host: str, port: int, user: str, password: str, folder: str,
                 ssl_context: ssl.SSLContext) -> None: ...
    def fetch(self, since: Watermark | None) -> Iterator[Fetched]: ...
def encode_folder(name: str) -> str: ...   # modified UTF-7, RFC 3501
```

Position `{"uidvalidity": "<n>", "uid": "<n>"}`. Ändert sich `UIDVALIDITY`, ab `1:*`. Suche `UID <n+1>:*` ohne Klammern; Holen `(UID INTERNALDATE BODY.PEEK[])`, Mail für Mail.

`.importlinter`: eine Schicht `previously.connectors` zwischen `cli` und `core` (die Schichten nachlesen, wie Aufgabe 1 der Auslieferung `previously.migrations` eingeordnet hat), und ein Vertrag: nur `previously.connectors.imap` importiert `imaplib`, namentlich.

- [ ] **Step 1: GreenMail-Fixture** in `conftest.py`, nach dem Muster der RustFS-Fixture; ein Benutzer, ein Ordner „Kunde Müller", Mails per `APPEND` aus `tests/mails/`.
- [ ] **Step 2: Tests, die scheitern:**
  - `encode_folder("Kunde Müller") == "Kunde M&APw-ller"` und zurück;
  - der Konnektor holt alle Mails, dann ab dem Wasserzeichen nur neue;
  - nach dem Lauf ist **keine** Mail `\Seen` (Mutation: `BODY[]` statt `BODY.PEEK[]` → rot);
  - geänderte `UIDVALIDITY` (Ordner löschen und neu anlegen): von vorn, nichts doppelt im Log;
  - `previously ingest imap` gegen GreenMail: die Zeile aus den Global Constraints; zweiter Lauf `0 appended`; `previously chronicle` zeigt die Betreffs;
  - falsches Passwort: ein Satz, Rückgabecode 2, das Passwort nirgends in stdout und stderr;
  - **Review Focus 4**: der Server schließt die Verbindung mitten im Lauf (GreenMail-Container anhalten, während der Lauf in einem Thread holt — oder, wenn das nicht deterministisch geht, sagt der Bericht warum): ein Satz, Rückgabecode 2, das Wasserzeichen beim letzten Stapel;
  - fehlende Angabe: ein Satz vor jeder Verbindung.
- [ ] **Step 3: rot. Step 4: umsetzen** — `imaplib.IMAP4_SSL(host, port, ssl_context=…)`, `login`, `select(<kodiert>, readonly=True)`, `status` für `UIDVALIDITY`; `ingest imap` in `COMMANDS` mit der Hilfe aus den Global Constraints; Angaben `PREVIOUSLY_IMAP_HOST`, `_PORT` (993), `_USER`, `_PASSWORD`, `_FOLDER`, dazu DSN, Bucket, Empfänger; das Identitätsverzeichnis liest es nicht.
- [ ] **Step 5: grün; Mutationen gemessen; `cli.md`, `configuration.md`** (wer welche Angabe liest — das Kommando liest die Identitäten nicht); `T201`-Zählung in `pyproject.toml` neu messen; sechs Tore; Testblock des Tutorials; Commit.

---

## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/connectors.md` (neu, Marke `connectors`), `docs/reference/mail-mapping.md` (neu), `docs/how-to/ingest-a-mail-folder.md` (neu), `docs/explanation/erasure.md`, `docs/how-to/erase-something.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach Spec §9, und:
  - `mail-mapping.md` (Reference): die Tabellen aus Spec §3, mit den Namen und Wortlauten, die der Code hat — `test_docs_references` hält die zitierten Wortlaute;
  - `ingest-a-mail-folder.md` (How-to): eigener Mailu-Benutzer, Ordner anlegen, Angaben setzen, laufen lassen, die Ausgabe lesen; **Tilgen**: auch im Ordner, in den Sicherungen des Postfachs und in den Antworten, die die Mail zitieren (über `In-Reply-To`/`References` zu finden); Weiterleitung als Anhang statt als zitierter Text;
  - `erasure.md`: Zitate in Antworten als Grenze der Tilgung bei Mail;
  - der Handoff (englisch, Spec §6): CronJob, Secret mit den fünf Angaben, Port 993, eigener Mailu-Benutzer, die erste Aufnahme des echten Ordners im Cluster;
  - die Landkarte: Einheit 1 gebaut; die offenen Punkte aus Spec §11 je unter ihre Einheit (Fäden als Vorgang unter Feststellungen; `.msg`/`.mbox` unter Einheit 7; OAuth unter Einwurf-Vertrag); der Hinweis, dass `ubuntu-latest` ab 2026-10-19 Ubuntu 26 ist, unter *Tore und Werkzeuge*; zählen vorher und nachher.
  - Spec einfrieren (Kopf wie die anderen, Statuszeile, §11 in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung; Fehlbedienung benannt, nicht gejagt.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/`.
4. Push und PR.
5. **Abnahme 11 (Spec §10), vom Betreuer, lokal:** sein echter Mailu-Ordner, `ingest imap`, `project`, `chronicle`, `blob get` der Rohmail und eines Anhangs, zweiter Lauf `0 appended`; danach Probe-Log und Bucket verwerfen.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §2 → 1; §3 → 2; §3.6 → 2 und 4; §4.1 → 3; §4.2 → 4; §4.3 und §5 → 5; §6 und §9 → 6; §7.3 → 2 (Entscheidung 1); §8 Punkte 1–4 → 1, 5–9 und 14 → 2/4, 10–12 → 5, 13 → 2, 15 → 1/5/6; §10 → die Aufgaben und „Nach Aufgabe 6"; §11 → Landkarte.
- **Platzhalter:** keine „TBD"; die Grenze für den Spitzenspeicher misst der Umsetzer (Review Focus 3), mit Begründung im Test.
- **Namen:** `artifact_hash_of`, `ArtifactChanged`, `ChannelIdentity`, `Mapped`, `Attachment`, `map_mail`, `variant_key`, `MAX_FORWARD_DEPTH`, `Watermark`, `Fetched`, `Connector`, `WatermarkStore`, `Ingested`, `ingest`, `ImapConnector`, `encode_folder` — überall gleich.
- **Code nur, wo gelaufen:** die Aufrufe von `imaplib` und `email` und die Einstellungen von `html2text` sind gemessen; der Rest steht als Schnittstelle und Test.
