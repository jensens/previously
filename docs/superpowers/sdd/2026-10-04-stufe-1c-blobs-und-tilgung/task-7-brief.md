## Task 7: Blobs tilgen und prüfen

Die Regel aus Spec §4.1, an einer Stelle gerechnet und von zwei Seiten benutzt: `redact` löscht, was nach ihr nicht mehr zu liegen hat, und `verify --blobs` meldet, was gegen sie verstößt.

**Files:**
- Modify: `src/previously/contract/store.py`, `src/previously/storage/postgres.py`, `src/previously/core/redaction.py`, `src/previously/core/redact.py`, `src/previously/core/sealing.py`, `src/previously/core/verify.py`, `src/previously/cli.py`, `pyproject.toml` (die Zahl der `print`-Aufrufe), `tests/test_redaction.py`, `tests/test_storage.py`, `tests/test_redact.py`, `tests/test_verify.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/explanation/erasure.md`, `docs/explanation/blobs.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Produces:
  - `previously.core.redaction`:
    ```python
    def blob_payload(sha256: str, event_ids: Sequence[int], *, reason: str) -> dict[str, object]: ...

    class RedactionIndex:
        # … dazu:
        def of_reference(self, event_id: int, sha256: str) -> Redaction | None: ...

    def blob_expected(index: RedactionIndex, sha256: str, event_ids: Iterable[int]) -> bool: ...
    ```
    `of_reference` findet die Tilgung des Events oder eine Blob-Tilgung, die das Event nennt. `blob_expected` ist die Regel: wahr, solange mindestens eine der Referenzen nicht getilgt ist. Ohne jede Referenz ist es falsch.
  - `previously.core.redact`:
    ```python
    @dataclass(frozen=True)
    class Redacted:
        redaction_id: int
        written: bool
        skipped_units: tuple[int, ...] = ()
        obsolete_blobs: tuple[str, ...] = ()   # haben nach der Regel nicht mehr zu liegen
        # bleiben, je mit den Events, die sie noch benutzen
        kept_blobs: Mapping[str, tuple[int, ...]] = field(
            default_factory=dict[str, tuple[int, ...]]
        )

    def redact_blob[Conn](
        log: LogStore[Conn], eraser: RedactionStore[Conn], sha256: str,
        *, reason: str, recorded_at: datetime,
    ) -> Redacted: ...
    ```
    `obsolete_blobs` und `kept_blobs` rechnet **jeder** Aufruf, auch der, der nichts schreibt: daran hängt, dass ein zweiter Aufruf das Löschen nachholt. `core` löscht nicht selbst — der Speicher nimmt an keiner Transaktion teil, und wer ruft, löscht danach.
  - `LogStore.blob_references(self, conn: Conn) -> Iterator[tuple[bytes, int]]` — jede Zeile des Registers, nach Hash und dann nach Event geordnet.
  - `previously.core.sealing.NullSink` — nimmt Bytes und verwirft sie.
  - `previously.core.verify`:
    ```python
    @dataclass(frozen=True)
    class BlobCheck:
        store: BlobStore
        keys: KeyProvider

    def examine[Conn](
        storage: LogStore[Conn], *, anchors: Sequence[Anchor] = (), exact: bool = False,
        batch: int = 1000, blobs: BlobCheck | None = None,
    ) -> Examination: ...
    ```
    `Examination` bekommt `blobs_checked: int = 0`.
  - Kommandos: `previously redact blob HASH --reason TEXT`, `previously verify --blobs`.

**`redact_blob`:** die Events, die den Blob nennen, aus dem Register; nennt ihn keines, eine Weigerung. Ihre Zeilen in aufsteigender Reihenfolge sperren — eine Reihenfolge, damit zwei Tilgungen sich nicht gegenseitig blockieren. Dann das Verzeichnis lesen. Genannt werden die Events, deren Referenz noch nicht getilgt ist; bleibt keines, wird nichts geschrieben. Die Nutzlast und die Einheiten der Events bleiben, wie sie sind.

**Was die Kommandozeile nach jeder Tilgung tut**, in dieser Reihenfolge: jeden Blob aus `obsolete_blobs` im Speicher löschen (zweimal löschen ist kein Fehler); die Projektionen nachziehen; dann die eine Zeile auf `stdout` und je Blob aus `kept_blobs` eine auf `stderr`. Scheitert das Löschen oder das Nachziehen: der Fehler aus der Wortlaut-Tabelle, mit dem, was aussteht, und Rückgabecode 2. Die Blob-Angaben liest sie nur, wenn `obsolete_blobs` nicht leer ist.

**`verify --blobs`:** im Schnappschuss die Referenzen sammeln (`blob_references`), nach Hash gruppiert. **Nach** dem Schnappschuss je Blob: hat er zu liegen, `fetch_blob` in eine `NullSink` — `None` ist `is missing`, `AddressMismatch` ist `does not match its address`, `CannotOpen` ist `cannot be opened`; hat er nicht zu liegen und `stat` findet ihn, `is erased and still present`. Jeder Befund unter der kleinsten `id`, die den Blob nennt. Ein Speicher, der nicht antwortet, ist kein Befund, sondern ein Fehler: Rückgabecode 2. Die Referenzen aller Blobs stehen dabei im Speicher des Prozesses; das ist die Grenze, die im Docstring steht.

Eine Blob-Tilgung wird gegen ihr Ziel gehalten wie die anderen: jedes genannte Event steht vor ihr in der Kette und nennt den Blob im Register. Sonst `redaction names a target that does not exist`.

- [ ] **Schritt 1: Die Regel, ohne Datenbank**

| Test, alle in `test_redaction.py` | Erwartung |
|---|---|
| `test_the_blob_form_round_trips` | Events aufsteigend, ohne Doppelte |
| `test_a_reference_is_erased_through_its_event_or_through_a_blob_redaction_that_names_it` | beide Wege von `of_reference`; eine Blob-Tilgung, die ein **anderes** Event nennt, tilgt diese Referenz nicht |
| `test_blob_expected` | parametrisiert, fünf Fälle: zwei Events, eines getilgt → wahr; beide getilgt → falsch; eine Blob-Tilgung nennt beide → falsch; eine Blob-Tilgung nennt beide, ein drittes Event kommt später dazu → wahr; keine Referenz → falsch |

- [ ] **Schritt 2: Der Ablauf**

| Test | Datei | Erwartung |
|---|---|---|
| `test_blob_references_come_ordered_by_hash_and_then_by_event` | `test_storage.py` | |
| `test_redacting_the_only_event_of_a_blob_makes_it_obsolete` | `test_redact.py` | `obsolete_blobs` nennt ihn |
| `test_a_shared_blob_is_kept_until_its_last_event_goes` | `test_redact.py` | nach dem ersten Event: `kept_blobs` nennt ihn mit dem zweiten; nach dem zweiten: `obsolete_blobs` |
| `test_redacting_a_blob_names_every_event_that_uses_it` | `test_redact.py` | das Tilgungs-Event trägt die Form; Nutzlast und Einheiten der Events stehen; `obsolete_blobs` nennt ihn |
| `test_the_same_content_at_a_new_event_after_a_blob_redaction_is_expected_again` | `test_redact.py` | |
| `test_a_second_blob_redaction_writes_nothing_and_still_names_the_blob_obsolete` | `test_redact.py` | daran hängt das Nachholen |
| `test_redacting_a_blob_no_event_uses_is_refused` | `test_redact.py` | |

- [ ] **Schritt 3: `verify --blobs`**

| Test, alle in `test_verify.py`, gegen Datenbank und Speicher | Erwartung |
|---|---|
| `test_an_intact_store_passes_and_counts` | keine Befunde, `blobs_checked` gleich der Zahl der verschiedenen Blobs |
| `test_verify_blobs_finds_each_of_the_four` | parametrisiert: das Objekt von Hand gelöscht; ein fremdes Objekt unter der Adresse; Müll unter der Adresse; nach der Tilgung wieder hingelegt. Je der Befund aus der Wortlaut-Tabelle |
| `test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on` | ein Schlüsselverzeichnis ohne die Identität; der nächste Blob wird trotzdem geprüft |
| `test_a_blob_finding_stands_under_the_first_event_that_names_the_blob` | |
| `test_without_the_switch_no_blob_is_touched` | `examine` ohne `blobs`: ein Speicher, der bei jedem Aufruf wirft, wird nicht gerufen |
| `test_a_blob_redaction_naming_an_event_that_does_not_use_the_blob_fires` | `redaction names a target that does not exist` |
| `test_the_rule_holds_end_to_end` | geteilter Blob, ein Event getilgt, dann der Blob, dann derselbe Inhalt an einem neuen Event: nach jedem Schritt meldet `verify --blobs` nichts (Zusicherung 12) |

- [ ] **Schritt 4: Die Kommandozeile**

| Test, alle in `test_cli.py` | Erwartung |
|---|---|
| `test_redact_event_deletes_its_blob_and_says_which_one_stays` | zwei Events, ein eigener und ein geteilter Blob: der eigene ist aus dem Bucket weg, der geteilte liegt, und `stderr` nennt ihn mit dem anderen Event |
| `test_redact_blob_and_then_blob_get_says_erased` | Rückgabecode 1, der Wortlaut mit der `id` der Tilgung |
| `test_a_delete_that_fails_is_finished_by_the_second_call` | erster Aufruf mit einem Endpunkt, an dem niemand hört: Rückgabecode 2, der Satz, und das Tilgungs-Event **steht**; zweiter Aufruf mit dem richtigen: `already redacted by event <id>`, Rückgabecode 0, das Objekt ist weg, und es gibt kein zweites Tilgungs-Event (Zusicherung 11) |
| `test_verify_blobs_prints_the_count` | `chain intact, 2 blobs match`; mit einem: `1 blob matches` |
| `test_verify_blobs_reports_a_missing_blob_and_returns_1` | |
| `test_show_marks_an_erased_blob` | an einem Event mit Nutzlast die Zeile mit `<erased by event <id>>`; an einem getilgten Event die Blobs aus dem Tilgungs-Event |
| `test_redacting_an_event_without_blobs_needs_no_blob_setting` | |

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `blob_expected` zählt jede Referenz, getilgt oder nicht | `test_blob_expected`, `test_redacting_the_only_event_of_a_blob_makes_it_obsolete` | `test_a_shared_blob_is_kept_until_its_last_event_goes`, erster Schritt |
| ein Aufruf, der nichts schreibt, gibt `obsolete_blobs` leer zurück | `test_a_delete_that_fails_is_finished_by_the_second_call` | `test_redact_event_deletes_its_blob_and_says_which_one_stays` |
| `verify --blobs` fragt nach getilgten Blobs nicht | der vierte Fall von `test_verify_blobs_finds_each_of_the_four` | die drei anderen |
| `verify --blobs` vergleicht die Adresse nicht (der Vergleich sitzt in `fetch_blob`; die Mutation ist dieselbe wie in Aufgabe 5) | der zweite Fall | der erste |
| die Kommandozeile löscht **vor** der Transaktion | schreib den Test, der es hält: eine Tilgung, die sich weigert, löscht nichts | — |

- [ ] **Schritt 5: Die Seiten**

- `docs/reference/cli.md`: `redact blob`; `verify --blobs` mit den vier Befunden, dem Zusatz der Erfolgszeile, und dem Satz, dass ein Blob, der seit dem Beginn des Laufs getilgt wurde, als fehlend erscheinen kann; `blob get` an einem getilgten Blob. Die Zahl der Kommandos bleibt, wie Aufgabe 6 sie gelassen hat: `redact blob` ist eine Form von `redact`, `--blobs` ein Schalter.
- `docs/explanation/erasure.md`: die dritte Zeile der Tabelle; **die Regel**, in einem Satz und mit ihren drei Folgen; warum ein geteilter Blob stehen bleibt; warum erst die Transaktion kommt und dann das Löschen, und was ein zweiter Aufruf nachholt; dass die Adresse eines Blobs kein Salz trägt und was das heißt.
- `docs/explanation/blobs.md`: wann ein Blob wieder geht, mit Verweis auf `` {ref}`erasure` ``; was `verify --blobs` prüft und warum es alle Bytes liest.

- [ ] **Schritt 6: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 453 + 32 = **485** (Schritt 1 sieben mit den fünf Fällen, Schritt 2 sieben, Schritt 3 zehn mit den vier Fällen, Schritt 4 sieben, dazu der eine Test aus der Mutationstabelle). Zähl nach.

---

