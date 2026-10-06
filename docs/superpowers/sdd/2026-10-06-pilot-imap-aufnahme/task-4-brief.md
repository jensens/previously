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

