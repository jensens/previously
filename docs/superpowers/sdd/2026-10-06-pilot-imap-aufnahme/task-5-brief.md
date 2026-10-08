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

