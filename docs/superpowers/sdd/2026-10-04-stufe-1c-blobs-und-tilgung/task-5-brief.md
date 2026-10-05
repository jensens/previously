## Task 5: Blobs — versiegeln, speichern, holen

Der Blob-Weg als Bibliothek: nach dieser Aufgabe lässt sich ein Inhalt versiegelt ablegen und geprüft wieder holen. Das Log weiß davon noch nichts; das kommt in Aufgabe 6.

Die Vorlage ist `blob_spike.py` in den Anlagen. Sie ist typisiert und gefahren, aber sie ist ein Entwurf in einer Datei: ohne die Fehlerklassen der zwei Schichten, ohne Kommentare, die begründen, und mit der Standard-Konfiguration von `boto3`. **Lies sie, fahr `blob_spike_run.py`, und schneide sie dann in die Module** — Test zuerst, wie überall.

**Files:**
- Create: `src/previously/contract/blobs.py`, `src/previously/core/sealing.py`, `src/previously/core/blob.py`, `src/previously/storage/s3.py`, `src/previously/storage/keys.py`, `tests/test_sealing.py`, `tests/test_keys.py`, `tests/test_s3.py`, `tests/test_blob.py`, `docs/explanation/blobs.md`
- Modify: `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md`, `.importlinter`, `CLAUDE.md` (eine Zahl), `src/previously/core/errors.py`, `src/previously/storage/errors.py`, `tests/conftest.py`, `tests/test_contracts.py`, `.github/workflows/gates.yml` (ein Kommentar), `docs/explanation/index.md`, `docs/explanation/module-boundaries.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Produces:
  - `previously.contract.blobs` — wie in der Vorlage: `ByteSource`, `SeekableSource`, `ByteSink`, `StoredBlob(key_id: str | None, sealed_size: int)`, `BlobStore` (`stat`, `put`, `get`, `delete`), `KeyProvider` (`identity(key_id: str) -> str | None`).
  - `previously.core.errors`: `BlobError(PreviouslyError)`, darunter `InvalidKey`, `CannotOpen`, `AddressMismatch`.
  - `previously.storage.errors`: `BlobStoreUnreachable(StorageError)`, `BlobStoreRefused(StorageError)`.
  - `previously.core.sealing`: `seal(source: ByteSource, sink: ByteSink, recipient: str) -> None`, `unseal(source: ByteSource, sink: ByteSink, identity: str) -> None`, `recipient_of(identity: str) -> str`, `HashingSink` (mit `write`, `hexdigest()`, `size`).
  - `previously.core.blob`:
    ```python
    @dataclass(frozen=True)
    class Stored:
        address: str        # SHA-256 des Klartexts, hex
        size: int           # Bytes Klartext
        uploaded: bool      # False: das Objekt lag schon

    def address_of(source: SeekableSource) -> tuple[str, int]: ...
    def store_blob(store: BlobStore, source: SeekableSource, *, recipient: str) -> Stored: ...
    def fetch_blob(store: BlobStore, keys: KeyProvider, address: str, sink: ByteSink) -> int | None: ...
    ```
    `fetch_blob` gibt die Größe des Klartexts zurück, oder `None`, wenn kein Objekt liegt. Es wirft `CannotOpen`, wenn das Objekt keinen Schlüssel nennt, wenn es für ihn keine Identität gibt, wenn die Identität zu einem anderen Schlüssel gehört, oder wenn `age` es nicht öffnet; und `AddressMismatch`, wenn der Klartext nicht zur Adresse passt. **Es schreibt in die Senke, bevor es weiß, ob die Adresse stimmt** — wer in eine Datei holt, gibt eine vorläufige und benennt nach dem Rückkehren um. Das ist Sache des Aufrufers und steht im Docstring.
  - `previously.storage.s3`: `S3BlobStore`, `from_settings(*, endpoint: str, region: str, bucket: str, access_key: str, secret_key: str) -> S3BlobStore`. `from_settings` verbindet nicht, wie `from_dsn`.
  - `previously.storage.keys.DirectoryKeys(directory: str)` mit `identity(key_id)`.
  - Fixtures in `tests/conftest.py`: `s3_settings` (Sitzung: der Container, Endpunkt und Zugangsdaten), `blob_store` (je Test ein **eigener, frisch angelegter Bucket**, damit kein Test die Objekte eines anderen sieht), `age_identity` (ein frischer Schlüssel als Text). Marker `s3` in `pyproject.toml`.
  - das Label `(blobs)=` auf `docs/explanation/blobs.md`.

- [ ] **Schritt 1: Die Abhängigkeiten, geprüft und eingetragen**

Prüfe die vier Pakete **selbst** an den Registern, mit heutigem Datum; die Tabelle im Spec (§8.3) ist die Messung vom 2026-10-04 und dein Ausgangspunkt, nicht dein Beleg. In `pyproject.toml`: `boto3` und `pyrage` unter `dependencies`, `pyrage-stubs` und `types-boto3-lite[s3]` unter `dev`, je als Untergrenze. Dann `uv lock`.

`DEPENDENCIES.md`: je Paket das Urteil mit Datum und Beleg. Für `pyrage` gehört hinein, worauf das Urteil steht — das Format, nicht die Bindung. Für die Stubs, warum `lite` (Spec §8.3). Dazu das Test-Image `rustfs/rustfs:1.0.1`: kein Paket, aber eine Abhängigkeit der Tests, und es steht dort mit Datum, Lizenz und dem Satz, dass der Speicher des Betriebs ein anderer ist.

Run: `uv run pip-audit --skip-editable`
Erwartet: kein Befund. Ein Befund hält die Aufgabe an.

- [ ] **Schritt 2: Die zwei Verträge**

`.importlinter` bekommt zwei `forbidden`-Verträge über das ganze Paket, je mit **namentlich** genannter Ausnahme:

- „Only core.sealing imports pyrage": verboten `pyrage`; ausgenommen die eine Kante `previously.core.sealing -> pyrage`.
- „Only storage.s3 imports boto3": verboten `boto3` und `botocore`; ausgenommen `previously.storage.s3 -> boto3` und `previously.storage.s3 -> botocore`.

`tests/test_contracts.py` prüft heute mit einem absichtlich falschen Import, dass die benannten Verträge brechen. Dasselbe für die zwei neuen: ein Probemodul in `core`, das `boto3` importiert; eines in `storage`, das `pyrage` importiert.

Der Kommentar am Kopf von `.importlinter` zählt („Three of the four contracts forbid external packages"), und `CLAUDE.md` zählt mit („the four contract names"). Beide Zahlen neu.

- [ ] **Schritt 3: Versiegeln, ohne Container**

`tests/test_sealing.py`:

| Test | Erwartung |
|---|---|
| `test_what_is_sealed_opens_to_the_same_bytes` | |
| `test_the_sealed_form_is_an_age_file_and_does_not_contain_the_plaintext` | beginnt mit `age-encryption.org/v1`; ein auffälliger Klartext kommt in den versiegelten Bytes nicht vor |
| `test_an_empty_plaintext_seals_and_opens` | Review Focus 2 |
| `test_a_source_with_nothing_but_read_and_a_sink_with_nothing_but_write_suffice` | |
| `test_the_wrong_identity_cannot_open` | `CannotOpen` |
| `test_garbage_cannot_be_opened` | `CannotOpen` |
| `test_a_recipient_or_identity_that_is_none_is_refused` | parametrisiert, vier Fälle: `nonsense` und der leere Text, je als Empfänger und als Identität; `InvalidKey`, und die Meldung zu einer Identität **nennt sie nicht** |
| `test_recipient_of_gives_the_public_half` | |
| `test_the_hashing_sink_counts_and_hashes_what_passes` | |

`pyrage` wird als **ein** Modul importiert (`import pyrage`, dann `pyrage.x25519.…`): mit `from pyrage import x25519` warnt pyright, das Untermodul habe keine Quelle. Die Stubs verlangen `BufferedIOBase`, zur Laufzeit genügen `read` und `write` (gemessen, siehe `blob_spike_run.py`); die zwei `cast` stehen in `core/sealing.py` mit genau diesem Satz daneben.

- [ ] **Schritt 4: Die Schlüssel**

`DirectoryKeys.identity(key_id)` liest die Datei `<Verzeichnis>/<key_id>` und gibt die erste Zeile zurück, die weder leer ist noch mit `#` beginnt — so schreibt `age-keygen` seine Dateien. Fehlt die Datei: `None`.

**`key_id` kommt aus dem Metadatum eines Objekts und ist damit eine Eingabe von außen.** Wer in den Bucket schreiben kann, bestimmt sie. Sie wird darum nicht als Pfad benutzt, bevor sie geprüft ist: nur `age1`, gefolgt von Kleinbuchstaben und Ziffern, ist ein Dateiname; alles andere ist `None`, ohne dass die Platte gefragt wird.

`tests/test_keys.py`:

| Test | Erwartung |
|---|---|
| `test_the_file_named_after_the_recipient_holds_its_identity` | |
| `test_comment_lines_as_age_keygen_writes_them_are_skipped` | |
| `test_a_missing_file_is_none` | |
| `test_a_key_id_that_is_not_a_recipient_never_reaches_the_disk` | parametrisiert: `../x`, `/etc/passwd`, `age1../x`, leer, `AGE1ABC`; je `None`. Die Kontrolle, dass wirklich nicht gelesen wurde: neben dem Verzeichnis liegt eine Datei, die `../x` träfe |
| `test_the_provider_does_not_show_what_it_holds` | `repr` nennt das Verzeichnis und keine Identität |

- [ ] **Schritt 5: Der Adapter, gegen RustFS**

Die Fixture nach dem Muster der Anlage: `DockerContainer("rustfs/rustfs:1.0.1")`, Port 9000, `RUSTFS_ACCESS_KEY` und `RUSTFS_SECRET_KEY`, und warten, bis `list_buckets` antwortet. Der Name des Images steht als Literal im Test, wie `postgres:17`.

`tests/test_s3.py`:

| Test | Erwartung |
|---|---|
| `test_stat_and_get_of_a_missing_object_are_none` | |
| `test_put_stat_get_round_trip_with_the_key_id` | `key_id` und `sealed_size` aus `stat` und aus `get`; die Bytes aus `get` sind die aus `put` |
| `test_get_gives_metadata_and_body_from_one_answer` | struktureller Test: genau ein `get_object`, kein `head_object` daneben — gezählt an den Ereignissen des Clients (`client.meta.events`), nicht an einem Mock |
| `test_delete_twice_is_no_error` | |
| `test_a_fresh_bucket_keeps_no_version_after_a_delete` | `list_object_versions`: keine Version, keine Löschmarke |
| `test_a_missing_bucket_is_refused_and_named` | `get` wirft `BlobStoreRefused`, die Meldung nennt Endpunkt und Bucket |
| `test_a_wrong_secret_is_refused_and_not_shown` | `BlobStoreRefused`; weder in `str` noch in `repr` des Fehlers noch seiner Ursache-Kette als Text steht das Geheimnis |
| `test_an_endpoint_nobody_listens_on_is_unreachable_within_seconds` | `BlobStoreUnreachable`, die Meldung nennt den Endpunkt |
| `test_a_read_that_breaks_off_is_a_storage_error` | der Datenstrom, den `get` herausgibt, übersetzt einen `BotoCoreError` beim Lesen in `BlobStoreUnreachable` |
| `test_s3_blob_store_satisfies_the_protocol` | |

Drei Dinge, die die Vorlage nicht hat:

- **Die Fehler.** `ClientError` mit `404`, `NoSuchKey` oder `NotFound` heißt „liegt nicht" und ist `None`. Jeder andere `ClientError` ist `BlobStoreRefused` mit Endpunkt, Bucket und dem Code des Speichers. Ein `BotoCoreError` ist `BlobStoreUnreachable`. Keine Meldung trägt Zugangsdaten.
- **Die Frist.** Mit der Standard-Konfiguration brauchten zwei Aufrufe gegen einen Endpunkt, an dem niemand hört, zwischen 14 und 23 s. Setz in `Config` eine Verbindungsfrist und eine kleine, feste Zahl von Versuchen, **miss**, wie lange ein Aufruf dann braucht, und schreib die Zahl mit Datum in den Kommentar. Der Test oben hält eine obere Grenze, die du aus deiner Messung nimmst.
- **Der Datenstrom.** Bricht das Lesen ab — gemessen in 19 von 20 Durchgängen, wenn ein zweites Hochladen das Objekt unter dem Leser ersetzt (`measure_race.py`) —, kommt ein `ResponseStreamingError` aus `botocore` durch `pyrage` hindurch bis in `core`. Eine fremde Ausnahme verlässt damit eine Schicht, die sie nicht kennen soll. Der Adapter gibt darum nicht den rohen Datenstrom heraus, sondern eine dünne Hülle, deren `read` übersetzt.

`stat` kann einen fehlenden Bucket nicht von einem fehlenden Objekt unterscheiden: beides ist ein `404` ohne Code (gemessen). Das steht im Docstring; der fehlende Bucket fällt beim ersten `get` oder `put` auf.

- [ ] **Schritt 6: Speichern und holen**

`tests/test_blob.py`, gegen RustFS:

| Test | Erwartung | Zusicherung im Spec §9 |
|---|---|---|
| `test_the_store_sees_only_ciphertext` | das Objekt, roh aus dem Bucket gelesen, beginnt mit dem `age`-Kopf, enthält den Klartext nicht, und öffnet sich mit der Identität | 1 |
| `test_the_same_content_twice_is_one_object` | zweiter Aufruf `uploaded=False`; im Bucket liegt ein Objekt | 2 |
| `test_an_object_under_a_foreign_address_is_not_delivered` | ein Objekt, das unter einer fremden Adresse abgelegt ist: `AddressMismatch` | 3 |
| `test_memory_stays_bounded` | siehe unten | 4 |
| `test_two_writers_at_once_leave_one_whole_object_that_opens` | zwei Fäden, eine Schranke, **zwei Empfänger**; danach ein Objekt, und `fetch_blob` holt es mit einem Schlüsselverzeichnis, das beide Identitäten hält | 20 |
| `test_after_a_key_change_the_stored_object_keeps_its_key` | zweiter Schreiber mit neuem Empfänger lädt nicht hoch; `fetch_blob` holt mit der alten Identität | 21 |
| `test_an_object_that_names_no_key_cannot_be_opened` | `CannotOpen` | |
| `test_an_identity_file_that_holds_another_key_cannot_open` | `CannotOpen`, und die Meldung nennt keine Identität | |
| `test_a_missing_object_is_none` | | |
| `test_an_empty_file_goes_through_the_whole_path` | Review Focus 2 | |

**`test_memory_stays_bounded`.** Gemessen am 2026-10-04 mit `measure_rustfs.py`, je in einem frischen Prozess: Spitze 90 MiB bei 16 MiB, 183 MiB bei 256 MiB und bei 1 GiB. Der Test läuft im Prozess von pytest und kann darum nur den **Zuwachs** der Spitze halten (`resource.getrusage(RUSAGE_SELF).ru_maxrss` vor und nach). Wähl den Blob so groß, dass zwischen dem Zuwachs des Wegs und dem der Mutation eine Lücke liegt, in der eine Grenze sicher steht; miss beide Seiten, und schreib beide Zahlen mit Datum in den Kommentar am Test. Kein Unterprozess: der bräuchte eine Suppression, und die Liste steht bei fünf.

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `store_blob` lädt die Quelle hoch statt der versiegelten Datei | `test_the_store_sees_only_ciphertext` | `test_the_same_content_twice_is_one_object` |
| `store_blob` fragt `stat` nicht | `test_the_same_content_twice_is_one_object`, `test_after_a_key_change_the_stored_object_keeps_its_key` | `test_the_store_sees_only_ciphertext` |
| `fetch_blob` vergleicht die Adresse nicht | `test_an_object_under_a_foreign_address_is_not_delivered` | `test_a_missing_object_is_none` |
| `fetch_blob` liest das Objekt in einem Stück (`body.read()`) | `test_memory_stays_bounded` | `test_the_store_sees_only_ciphertext` |
| `fetch_blob` nimmt die `key_id` nicht vom Objekt, sondern vom Empfänger des Aufrufers | `test_two_writers_at_once_leave_one_whole_object_that_opens` — in den Durchgängen, in denen der andere gewinnt; wiederhol ihn im Test so oft, dass beide Ausgänge vorkommen, und nenne die Zahl | `test_the_same_content_twice_is_one_object` |
| `fetch_blob` prüft nicht, dass die Identität zur `key_id` gehört | `test_an_identity_file_that_holds_another_key_cannot_open` — oder `age` weist sie ohnehin ab; **miss es**, und wenn die Prüfung nichts hinzufügt, nimm sie heraus und schreib es in den Bericht | — |

- [ ] **Schritt 7: Sätze, die nicht mehr stimmen**

- `.importlinter` und `CLAUDE.md`: die Zahl der Verträge (Schritt 2).
- `.github/workflows/gates.yml`: der Kommentar am Job sagt, Docker werde für PostgreSQL gebraucht. Jetzt auch für den Blob-Speicher.
- `tests/conftest.py`: der Modul-Docstring nennt nur PostgreSQL.

- [ ] **Schritt 8: `docs/explanation/blobs.md` und `module-boundaries.md`**

Neue Seite, Label `(blobs)=`, „About blobs". Was sie tragen muss:

- **Die Adresse** ist der Hash des Klartexts, und warum: derselbe Inhalt ist ein Objekt, und das Log nennt, welche Bytes gemeint sind.
- **Der Speicher sieht nur Chiffretext**, und was das wert ist: gestohlene Zugangsdaten zum Bucket liefern nichts Lesbares.
- **Warum `age`** und kein eigenes Verfahren: ein Standardformat, stückweise, und im Notfall mit einem verbreiteten Werkzeug zu öffnen, ohne diese Software.
- **Warum es keine Größengrenze gibt.** Fahr `measure_rustfs.py` bei drei Größen und nenne deine Zahlen und dein Datum.
- **„Erster gewinnt" ist Nachsehen, kein Schloss**, und was dazwischen geschehen kann. Fahr `measure_race.py` und nenne deine Zahlen. Was der Preis ist: ein Leser, der in dem Augenblick liest, bricht ab; und der Schreiber vertraut dem, was liegt.
- **Warum der Schlüssel am Objekt steht und nicht im Log** — der Grund aus Spec §1.1 Punkt 8, als Argument, nicht als Verweis.
- **Die Schlüssel:** ein Empfänger zum Schreiben, eine Identität zum Lesen; warum ein Dienst, der nur aufnimmt, das Geheimnis nicht braucht; dass `key_id` vom Objekt kommt und darum als Eingabe behandelt wird; **Schlüsselverlust ist Totalverlust**.
- Was diese Seite noch **nicht** sagt, weil es noch nicht gebaut ist: wie ein Blob an ein Event kommt (Aufgabe 6) und wann er wieder geht (Aufgabe 7).

`module-boundaries.md`: die zwei neuen Verträge, je mit dem Grund — warum versiegelt wird, wo die Regeln stehen, und gespeichert, wo die fremden Systeme stehen.

- [ ] **Schritt 9: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 374 + 43 = **417** (Schritt 2 zwei, Schritt 3 zwölf mit den vier Fällen, Schritt 4 neun mit den fünf Fällen, Schritt 5 zehn, Schritt 6 zehn). Zähl nach.

Die Tore laufen jetzt mit zwei Containern. Miss, was das den Testlauf kostet, und nenne die Zahl im Bericht.

---

