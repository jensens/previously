## Task 6: Blobs am Event

Nach dieser Aufgabe trägt ein Event seine Anhänge: `append --attach` legt sie ab und nennt sie in der Nutzlast, `blob get` holt sie, und `verify` hält das Register gegen die Kette.

**Files:**
- Create: `migrations/versions/0004_event_blob.py`
- Modify: `src/previously/contract/types.py`, `src/previously/contract/store.py`, `src/previously/storage/schema.py`, `src/previously/storage/postgres.py`, `src/previously/core/chain.py`, `src/previously/core/append.py`, `src/previously/core/redact.py`, `src/previously/core/verify.py`, `src/previously/cli.py`, `pyproject.toml` (die Zahl der `print`-Aufrufe), `tests/conftest.py` (ein Kommentar), `tests/test_schema.py`, `tests/test_storage.py`, `tests/test_chain.py`, `tests/test_append.py`, `tests/test_redact.py`, `tests/test_verify.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/reference/database-schema.md`, `docs/explanation/blobs.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Consumes: `store_blob`, `fetch_blob`, `Stored` aus `core.blob`; `from_settings`, `DirectoryKeys` aus `storage`; `read_index` aus Aufgabe 3.
- Produces:
  - `previously.contract.types`:
    ```python
    @dataclass(frozen=True)
    class BlobRef:
        sha256: str               # 64 Hex-Zeichen, klein
        size: int                 # Bytes Klartext
        media_type: str
        filename: str | None = None
    ```
    und `RawEvent` bekommt am Ende `blobs: tuple[BlobRef, ...] = ()`.
  - Die Nutzlast: `append` mischt unter dem Schlüssel `blobs` eine Liste von Objekten mit genau den vier Schlüsseln `sha256`, `size`, `media_type`, `filename` ein — **nur wenn das Event Blobs hat**. Ein Event ohne Anhang trägt den Schlüssel nicht, und seine Nutzlast ist die von heute. Der Schlüssel ist reserviert wie `evidence`.
  - Schema `event_blob`, in `schema.py` und Migration gleich: `event_id bigint NOT NULL REFERENCES event(id)`, `sha256 bytea NOT NULL`, Primärschlüssel `(event_id, sha256)`, `CHECK (octet_length(sha256) = 32)` mit Namen `event_blob_sha256_check`, Index `event_blob_sha256_idx` auf `sha256`.
  - `LogStore`:
    ```python
    def insert_event(
        self, conn: Conn, row: EventRow, units: Sequence[UnitRow],
        key: tuple[str, str] | None, blobs: Sequence[bytes] = (),
    ) -> None: ...
    def blobs_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[bytes]]: ...
    def events_by_blob(self, conn: Conn, sha256: bytes) -> list[int]: ...
    ```
    `blobs` an `insert_event` sind die **verschiedenen** Hashes des Events; beide Leser liefern aufsteigend.
  - `chain.Prepared` bekommt `blobs: tuple[bytes, ...] = ()`; `chain.prepare` einen Parameter `blobs: Sequence[BlobRef] = ()`, mischt die Referenzen in die Nutzlast und legt die verschiedenen Hashes ab. Für den Schlüssel `blobs` gilt damit, was `_prepare` für `evidence` sagt: an **einer** Stelle eingemischt, einmal, vor dem Hashen.
  - `redact_event` füllt `blobs` im Tilgungs-Event mit dem, was das Register für das Ziel nennt.
  - `verify`: der Befund `blob register does not match the payload`.
  - Kommandos: `previously append … --attach FILE` (mehrfach), `previously blob get HASH --output FILE`.

- [ ] **Schritt 1: Schema und Speicher**

| Test | Datei | Erwartung |
|---|---|---|
| `test_a_register_row_needs_a_hash_of_32_bytes` | `test_schema.py` | 31 Bytes scheitern an `event_blob_sha256_check` |
| `test_blobs_are_registered_with_the_event_and_read_back_by_batch` | `test_storage.py` | `blobs_by_event` für zwei Events, aufsteigend; ein Event ohne Blob fehlt im Ergebnis |
| `test_events_by_blob_lists_every_event_that_uses_it` | `test_storage.py` | |
| `test_blobs_by_event_with_an_empty_batch` | `test_storage.py` | kein Statement, leeres Ergebnis |

`test_the_declared_columns_match_the_migrated_database` aus Aufgabe 2 deckt die neue Tabelle von selbst. Miss das: nimm eine Spalte aus der Migration, fahr ihn, nimm es zurück.

`downgrade()` von `0004` nimmt die Tabelle weg — **aber weigert sich, wenn sie Zeilen hat**: ohne Register weiß nichts mehr, welche Events einen Blob benutzen.

In `tests/conftest.py` sagt der Docstring der `db`-Fixture „All six tables". Es sind sieben, und der Satz gehört so gefasst, dass die achte ihn nicht wieder falsch macht.

- [ ] **Schritt 2: `append` trägt die Referenzen**

| Test | Datei | Erwartung |
|---|---|---|
| `test_prepare_mixes_the_references_in_and_keeps_the_distinct_hashes` | `test_chain.py` | |
| `test_blob_references_land_in_the_payload_and_in_the_register` | `test_append.py` | die Nutzlast trägt `blobs` in der Form oben; `blobs_by_event` nennt den Hash; `verify` meldet nichts |
| `test_an_event_without_blobs_carries_no_blobs_key` | `test_append.py` | |
| `test_the_key_blobs_is_reserved` | `test_append.py` | der Wortlaut aus der Tabelle |
| `test_the_same_content_twice_at_one_event_is_two_references_and_one_register_row` | `test_append.py` | Review Focus 3 |
| `test_a_blob_reference_that_is_not_one_is_refused` | `test_append.py` | parametrisiert, vier Fälle: Hash in Großbuchstaben, Hash mit 63 Zeichen, negative Größe, leerer `media_type`; je `InvalidPayload`, das den Index der Referenz nennt, **bevor** etwas den Speicher erreicht |

- [ ] **Schritt 3: `verify` hält das Register gegen die Kette, und `redact_event` nennt die Blobs**

Je Stapel `blobs_by_event`, ein Statement. Für ein Event **mit** Nutzlast: die Menge der Hashes in `payload.blobs` gegen die Menge im Register; eine Liste, die nicht die Form hat, ist derselbe Befund. Für ein Event **ohne** Nutzlast: das Register gegen `blobs` in seinem Tilgungs-Event, am Ende, wo die Tilgungen bekannt sind.

| Test | Datei | Erwartung |
|---|---|---|
| `test_a_register_row_without_a_reference_fires` | `test_verify.py` | eine Zeile mit rohem SQL dazu |
| `test_a_reference_without_a_register_row_fires` | `test_verify.py` | eine Zeile mit rohem SQL weg |
| `test_the_register_of_an_erased_event_is_held_against_its_redaction` | `test_verify.py` | nach `redact_event`: nichts; danach eine Zeile dazu: der Befund, unter der `id` des getilgten Events |
| `test_the_redaction_of_an_event_names_its_blobs` | `test_redact.py` | `target.blobs` trägt die Hashes, aufsteigend |

Mutation: `redact_event` schreibt weiter eine leere Liste → der dritte Test rot, der erste grün.

- [ ] **Schritt 4: Die Kommandozeile**

Die Angaben liest `cli.py` aus der Umgebung, wie den DSN, und reicht sie als Text an `storage`; es nennt die **erste** Variable, die fehlt. Drei kleine Funktionen: der Speicher (fünf Variablen), der Empfänger, die Identitäten. Jedes Kommando liest nur, was es braucht — und ein Kommando, das keinen Blob anfasst, liest keine.

**`append --attach`:** erst **alle** Dateien öffnen, dann ablegen, dann anfügen. So fügt eine Datei, die sich nicht lesen lässt, nichts an und lässt nichts im Speicher zurück. `filename` ist der Name ohne Verzeichnis. `media_type` kommt aus `mimetypes.MimeTypes().guess_type(…)` — eine **eigene** Instanz, die nur die eingebaute Tabelle kennt und nicht die Dateien des Systems liest: der Wert steht für immer im Hash und soll nicht davon abhängen, auf welcher Maschine angefügt wurde. Ohne Treffer `application/octet-stream`.

**`blob get HASH --output FILE`:** die Adresse prüfen, bevor irgendetwas gefragt wird; nennt kein Event sie (`events_by_blob` leer): Rückgabecode 1. Sonst `fetch_blob` in eine vorläufige Datei **im Verzeichnis des Ziels**, und erst nach der Rückkehr `os.replace`. Bei jedem Fehler ist die vorläufige Datei weg und das Ziel unberührt.

**`show`** druckt je Referenz die Blob-Zeile aus der Wortlaut-Tabelle. Es fragt den Speicher nicht.

| Test, alle in `test_cli.py` | Erwartung |
|---|---|
| `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back` | die geholte Datei ist Byte für Byte die abgelegte; `stdout` von `append` ist die `id` und nichts sonst |
| `test_an_attachment_that_cannot_be_read_appends_nothing` | parametrisiert: fehlt; ist ein Verzeichnis. Rückgabecode 2, ein Satz, das Log leer, der Bucket leer (Review Focus 1) |
| `test_a_blob_address_that_is_not_one_is_an_input_error` | parametrisiert: Großbuchstaben; 63 Zeichen (Review Focus 6) |
| `test_blob_get_of_an_address_no_event_uses_returns_1` | |
| `test_blob_get_writes_nothing_when_the_address_does_not_match` | ein fremdes Objekt unter der Adresse eines Events: Rückgabecode 2, das Ziel existiert nicht, und im Verzeichnis liegt keine vorläufige Datei |
| `test_blob_get_leaves_an_existing_target_alone_when_it_fails` | |
| `test_a_missing_blob_setting_is_named` | parametrisiert über die sieben Variablen, je an dem Kommando, das sie braucht |
| `test_the_commands_of_today_run_without_any_blob_setting` | `append` ohne Anhang, `log`, `verify`, `anchor`, `show`, `project`, `chronicle`, `stats`, `redact event` an einem Event ohne Blob — in einer Umgebung ohne jede `PREVIOUSLY_BLOB_*` (Zusicherung 17) |
| `test_a_store_that_does_not_answer_appends_nothing_and_shows_no_secret` | Endpunkt, an dem niemand hört: Rückgabecode 2, ein Satz, das Log leer; in `stdout` und `stderr` steht das Geheimnis nicht (Review Focus 5, Zusicherung 18) |
| `test_no_identity_reaches_any_output` | über `blob get` mit einer Identitätsdatei, die zu einem anderen Schlüssel gehört: der Text der Identität steht in keiner Ausgabe |
| `test_show_lists_the_blobs_of_an_event` | |

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `_cmd_append` legt jede Datei ab, sobald sie geöffnet ist | `test_an_attachment_that_cannot_be_read_appends_nothing` — mit zwei Anhängen, von denen der zweite fehlt; **so muss der Test gebaut sein** | `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back` |
| `_cmd_blob_get` schreibt direkt ins Ziel | `test_blob_get_writes_nothing_when_the_address_does_not_match` | `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back` |
| `_cmd_log` liest die Blob-Angaben | `test_the_commands_of_today_run_without_any_blob_setting` | `test_a_missing_blob_setting_is_named` |

- [ ] **Schritt 5: Die Seiten**

- `docs/reference/cli.md`: `append --attach`, `blob get`, `show`; der Befund; aus neun Kommandos werden zehn.
- `docs/reference/configuration.md`: die sieben Variablen, je mit dem, was sie ist, und welchem Kommando sie fehlt, wenn sie fehlt (die Tabelle aus Spec §7).
- `docs/reference/database-schema.md`: `event_blob`.
- `docs/explanation/blobs.md`: wie ein Blob an ein Event kommt — erst der Blob, dann das Event, und was zurückbleibt, wenn das Anfügen scheitert; warum die Referenz in der Nutzlast steht und das Register daneben; warum `filename` zur Verwendung gehört und nicht zum Blob.

- [ ] **Schritt 6: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 417 + 36 = **453** (Schritt 1 vier, Schritt 2 neun mit den vier Fällen, Schritt 3 vier, Schritt 4 neunzehn mit den elf Fällen). Zähl nach.

---

