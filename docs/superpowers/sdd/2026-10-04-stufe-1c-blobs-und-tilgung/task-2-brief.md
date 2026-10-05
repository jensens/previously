## Task 2: v=2 von Ende zu Ende — Schema, Speicher, `append`, `verify`

Nach dieser Aufgabe schreibt `append` v=2, `verify` prüft jede Zeile nach ihrer Fassung, und ein Log mit Events beider Fassungen besteht. Eine Tilgung gibt es noch nicht: ein Grabstein geht weiter durch, wie heute.

**Files:**
- Create: `migrations/versions/0003_hash_version_2.py`, `src/previously/core/chain.py`, `tests/test_chain.py`, `tests/test_migration_0003.py`
- Modify: `src/previously/contract/rows.py`, `src/previously/storage/schema.py`, `src/previously/storage/postgres.py`, `src/previously/core/append.py`, `src/previously/core/verify.py`, `src/previously/core/hashing.py` (nur der Modul-Docstring), `src/previously/core/projection/chronicle.py`, `src/previously/cli.py`, `tests/test_rows.py`, `tests/test_schema.py`, `tests/test_storage.py`, `tests/test_append.py`, `tests/test_verify.py`, `tests/test_properties.py`, `tests/test_projection_derive.py`, `docs/reference/database-schema.md`, `docs/reference/hash-format.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Consumes: alles aus Aufgabe 1.
- Produces:
  - `previously.contract.rows.EventRow` bekommt am Ende `hash_version: int = 1` und `payload_salt: bytes | None = None`. Die Vorgabewerte spiegeln die Spalten: eine Zeile, die nichts sagt, ist v=1.
  - `previously.contract.rows.UnitRow`: `content: str | None` (`None` ist der Grabstein), am Ende `digest: bytes | None = None` und `salt: bytes | None = None`.
  - Schema, in `schema.py` und in der Migration gleich:
    - `event.hash_version` `smallint NOT NULL DEFAULT 1`
    - `event.payload_salt` `bytea`
    - `CHECK (payload IS NOT NULL OR payload_salt IS NULL)`, Name `event_payload_salt_check`
    - `unit.content` verliert `NOT NULL`
    - `unit.digest` `bytea`, `unit.salt` `bytea`
    - `CHECK (content IS NOT NULL OR (salt IS NULL AND speaker IS NULL AND start_ms IS NULL AND end_ms IS NULL))`, Name `unit_tombstone_check`
  - `previously.core.chain`:
    ```python
    @dataclass(frozen=True)
    class PreparedUnit:
        seq: int
        content: str
        start_ms: int | None
        end_ms: int | None
        speaker: str | None
        salt: bytes
        digest: bytes

    @dataclass(frozen=True)
    class Prepared:
        kind: str
        occurred_at: datetime
        payload: Mapping[str, object]
        payload_salt: bytes
        payload_digest: bytes
        units: tuple[PreparedUnit, ...]
        units_digest: bytes
        key: tuple[str, str] | None

    def prepare(
        *,
        kind: str,
        occurred_at: datetime,
        payload: Mapping[str, object],
        units: Sequence[RawUnit],
        key: tuple[str, str] | None,
    ) -> Prepared: ...

    def link(
        prepared: Prepared,
        *,
        event_id: int,
        prev_hash: bytes | None,
        recorded_at: datetime,
    ) -> tuple[EventRow, list[UnitRow]]: ...
    ```
    `prepare` zieht die Salze und rechnet, was über Wiederholungen gleich bleibt; `link` rechnet, was an der Kettenposition hängt. Beide sind rein bis auf den Zufall der Salze, und keines fasst den Speicher an.
  - `LogStore` unverändert in seinen Signaturen; `insert_event`, `read` und `units_by_event` tragen die neuen Felder.
  - `verify`: zwei neue Befunde, `unit <seq> does not match its digest` und `hash_version <n> is not known`.

- [ ] **Schritt 1: Zeilen und Schema, Test zuerst**

Tests, je zuerst rot:

| Test | Datei | Erwartung |
|---|---|---|
| `test_an_event_row_that_says_nothing_is_version_1_without_a_salt` | `test_rows.py` | Vorgabewerte `1` und `None` |
| `test_a_unit_row_may_lack_its_content_and_carries_digest_and_salt` | `test_rows.py` | `content=None` ist zulässig; `digest`, `salt` Vorgabe `None` |
| `test_hash_version_defaults_to_1_for_a_row_that_does_not_say` | `test_schema.py` | rohes `INSERT` ohne die Spalte, gelesen wird `1` |
| `test_a_salt_beside_a_payload_tombstone_is_refused` | `test_schema.py` | `UPDATE event SET payload = NULL` bei gesetztem Salz scheitert an `event_payload_salt_check`; mit `payload_salt = NULL` im selben `UPDATE` geht es durch |
| `test_a_unit_tombstone_keeps_nothing_but_its_seq_and_its_digest` | `test_schema.py` | `UPDATE unit SET content = NULL` scheitert an `unit_tombstone_check`, solange Salz, Sprecher oder eine Zeitmarke steht; alle fünf auf `NULL` geht durch, `digest` bleibt |
| `test_the_declared_columns_match_the_migrated_database` | `test_schema.py` | für jede Tabelle in `metadata`: Spaltennamen und `NOT NULL` gleich `information_schema.columns`; die Namen der `CHECK`-Bedingungen gleich `pg_constraint` |

Der letzte Test ist nicht für diese Migration allein da: bis heute hält nur ein Test die Indexnamen gegen die Datenbank, und eine Spalte, die in `schema.py` steht und in der Migration fehlt, fiele keinem Tor auf. Miss, dass er das tut: nimm `payload_salt` aus `schema.py`, fahr ihn, nimm es zurück.

Die Migration `0003_hash_version_2.py`, von Hand, wie `0002_projections.py`:

- `upgrade()`: die Spalten und Bedingungen oben. `hash_version` mit `server_default=sa.text("1")`. Der Docstring sagt, warum das eine gewöhnliche Vorwärtsmigration ist und die Korrektur K1 keine war: hier wird kein Hash neu gerechnet, der Vorgabewert schreibt für jede Altzeile hin, was ohnehin gilt.
- `downgrade()`: nimmt zurück, was `upgrade()` brachte — **aber weigert sich, wenn eine Zeile `hash_version = 2` trägt oder eine Einheit ohne Inhalt ist.** Ohne die Salze ist ein v=2-Event nicht mehr prüfbar, und `content` lässt sich nicht wieder `NOT NULL` machen. Die Weigerung ist ein Satz, kein Traceback.

`tests/test_migration_0003.py`, mit einem **eigenen** Container (die Sitzungs-Datenbank darf nicht zurückgestuft werden): auf `head`, zurück auf `0002_projections` geht auf leerer Datenbank; wieder auf `head`, ein Event über `append`, zurück auf `0002_projections` weigert sich mit dem Satz, und die Datenbank steht danach noch auf `head`.

- [ ] **Schritt 2: Der Speicher trägt die neuen Felder**

| Test | Datei | Erwartung |
|---|---|---|
| `test_version_and_salt_round_trip` | `test_storage.py` | eine `EventRow` mit `hash_version=2` und Salz kommt aus `read` so zurück |
| `test_unit_digest_and_salt_round_trip_through_both_readers` | `test_storage.py` | `units` und `units_by_event` liefern `digest` und `salt` |

`insert_event` schreibt `hash_version` **ausdrücklich** aus der Zeile, nicht über den Vorgabewert der Spalte.

- [ ] **Schritt 3: `core/chain.py`**

`tests/test_chain.py`, ohne Datenbank:

| Test | Erwartung |
|---|---|
| `test_prepare_draws_one_salt_for_the_payload_and_one_per_unit` | alle Salze 32 Bytes und paarweise verschieden |
| `test_prepare_computes_what_the_hash_functions_compute` | `payload_digest`, jeder `digest` und `units_digest` gleich dem Ergebnis der vier Funktionen aus Aufgabe 1 mit den gezogenen Salzen |
| `test_prepare_twice_gives_two_different_digests_for_the_same_input` | dieselbe Eingabe, zwei Aufrufe, verschiedene `payload_digest` |
| `test_link_hangs_the_event_into_the_chain` | `id`, `prev_hash`, `hash_version == 2`, `hash == event_hash_v2(…)` aus den Feldern; die Einheiten tragen `event_id`, `digest`, `salt` |
| `test_link_without_a_key_hashes_no_source` | `key=None` → `source` und `external_id` gehen als `None` in den Hash |
| `test_prepare_refuses_what_the_canonical_form_refuses` | Gleitkommazahl in der Nutzlast → `InvalidPayload`, bevor ein Salz eine Rolle spielt |

Mutation: `prepare` benutzt für alle Einheiten dasselbe Salz → der erste Test rot, der zweite grün.

- [ ] **Schritt 4: `append` schreibt v=2**

`_prepare` in `append.py` ruft `chain.prepare` und gibt je Event `(RawEvent, Prepared)` zurück; die Schleife ruft `chain.link` mit `next_id` und `prev`. Die Prüfungen vor dem Hashen (`_check_identity`, `_check_units`, der reservierte Schlüssel, der doppelte Schlüssel im Stapel) bleiben, wo sie sind, und in ihrer Reihenfolge. Der Wiederholungs-Teil der Schleife mit seinen zwei `except`-Zweigen bleibt **wörtlich**; an ihm ändert sich nichts als die zwei Zeilen, die die Zeile bauen.

Dass die Salze **einmal** gezogen werden, vor dem ersten Versuch, gehört in den Docstring von `_prepare`, neben den Satz, der das für die Belegart sagt.

| Test | Datei | Erwartung |
|---|---|---|
| `test_append_writes_version_2_with_a_salt_for_the_payload_and_each_unit` | `test_append.py` | gelesen: `hash_version == 2`, `payload_salt` 32 Bytes, je Einheit `digest` und `salt` 32 Bytes |

Die bestehenden Tests in `test_append.py` müssen grün bleiben, ohne dass eine Erwartung angefasst wird. Wird eine rot, ist das ein Befund für den Bericht, kein Anlass, sie anzupassen.

- [ ] **Schritt 5: `verify` prüft nach Fassung**

`_check_event` wählt nach `row.hash_version`:

- **1:** wie heute. Die v=1-Funktionen brauchen Einheiten mit Inhalt; trägt eine Einheit keinen, lässt sich `units_hash` nicht rechnen, und der Befund ist `units_hash does not match the units` — bis Aufgabe 3 daraus zwei Fälle macht.
- **2:** die Nutzlast gegen `payload_hash_v2(payload, payload_salt)`, wenn sie da ist; fehlt das Salz neben einer Nutzlast, ist das derselbe Befund wie ein falscher Hash. Jede Einheit **mit Inhalt** gegen `unit_digest(…)`: `unit <seq> does not match its digest`. `units_hash_v2` über die gespeicherten `digest` gegen `row.units_hash`; fehlt ein `digest`, ist das ein Befund an `units_hash`, kein Absturz. Der Event-Hash über `event_hash_v2`.
- **alles andere:** `hash_version <n> is not known`, und an dieser Zeile wird sonst nichts gerechnet. Die Kettenverknüpfung (`prev_hash`) wird trotzdem geprüft, und die Prüfung läuft an der nächsten Zeile weiter.

Die Prüfung meldet und bricht nicht ab: was `InvalidPayload` werfen kann, wird gefangen und zum Befund, wie in `_payload_finding`.

| Test, alle in `test_verify.py` | Fälschung, mit rohem SQL | Erwartung |
|---|---|---|
| `test_a_version_1_chain_still_passes` | keine; drei Events von Hand über `insert_event` mit den v=1-Funktionen | `[]` |
| `test_a_chain_of_both_versions_passes` | keine; ein v=1-Event von Hand, dann `append` | `[]`, und das zweite Event ist v=2 |
| `test_v2_a_rewritten_unit_fires_on_that_unit_and_not_on_its_neighbour` | Inhalt von Einheit 2 geändert | genau ein Befund, `unit 2 does not match its digest` |
| `test_v2_a_rewritten_salt_fires` | `payload_salt` geändert; getrennt davon `unit.salt` | `payload_hash does not match the payload`; `unit <seq> does not match its digest` |
| `test_v2_a_deleted_unit_row_fires` | eine Zeile aus `unit` gelöscht | `units_hash does not match the units` |
| `test_v2_a_unit_rewritten_together_with_its_digest_fires` | Inhalt, Salz und `digest` einer Einheit stimmig neu geschrieben | `units_hash does not match the units` — die Einheit für sich stimmt, die Menge nicht |
| `test_a_flipped_hash_version_fires` | `hash_version` von 2 auf 1 | mindestens `hash does not match the fields` |
| `test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on` | `hash_version = 3` am ersten von zwei Events, und am zweiten die Nutzlast geändert | `hash_version 3 is not known` am ersten, `payload_hash does not match the payload` am zweiten |

**Bestehende Tests, deren Erwartung sich ändert**, weil `append` jetzt v=2 schreibt: `test_k1_f1_a_rewritten_unit_content_fires` erwartet künftig `unit <seq> does not match its digest`. Der Befund aus K1 bleibt für v=1 gültig und bekommt dafür einen eigenen Test, der dieselbe Fälschung an einem v=1-Event von Hand macht und `units_hash does not match the units` erwartet. Jede weitere Änderung an einer bestehenden Erwartung steht mit Grund im Bericht.

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `_check_event` rechnet v=2-Zeilen mit den v=1-Funktionen | `test_an_intact_chain_passes` | `test_a_version_1_chain_still_passes` |
| die Prüfung je Einheit entfällt | `test_v2_a_rewritten_unit_fires_on_that_unit_and_not_on_its_neighbour` | `test_v2_a_deleted_unit_row_fires` |
| unbekannte Fassung wird wie v=2 gerechnet | `test_an_unknown_hash_version_is_a_finding_and_the_check_goes_on` | `test_a_flipped_hash_version_fires` |

`tests/test_properties.py`: `test_p5_any_single_byte_change_fails_verification` läuft unverändert weiter. Dazu ein neuer, `test_p8_any_single_byte_change_in_a_salt_or_a_unit_digest_fails_verification`, nach demselben Muster.

- [ ] **Schritt 6: Wer `UnitRow.content` liest**

pyright zeigt jede Stelle. Drei gibt es heute:

- `core/projection/chronicle.py`, `derive`: eine Einheit ohne Inhalt ergibt **keine Zeile**. Die Version der Projektion bleibt in dieser Aufgabe 1 — nichts im Baum kann eine Einheit tilgen —, und Aufgabe 4 hebt sie. Test: `test_chronicle_derives_no_row_for_a_unit_without_content` in `test_projection_derive.py`.
- `cli.py`, `_cmd_show`: druckt `  ¶<seq> <erased>`.
- `core/verify.py`: oben.

- [ ] **Schritt 7: Sätze, die nicht mehr stimmen**

- `core/hashing.py`, Modul-Docstring: „the same holds for the units as soon as `unit.content` may be `NULL`" — sie darf jetzt.
- `storage/schema.py`: der Kommentar an `units_hash` und der lange Kommentar an `event_payload_object_check` reden von der Naht als etwas Künftigem. Die Tilgung kommt in Aufgabe 3; **hier** stimmt noch alles, was sie über die Prüfung sagen. Nur was sie über die Spalten sagen, wird nachgezogen.
- `tests/conftest.py`: „All six tables" bleibt richtig, bis Aufgabe 6 die siebte bringt.

- [ ] **Schritt 8: `docs/reference/database-schema.md` und `hash-format.md`**

`database-schema.md`: die vier Spalten, die geänderte Spalte, die zwei Bedingungen, je mit dem, was sie erzwingen. `hash-format.md`: der Satz aus Aufgabe 1, der gewartet hat — wo Fassung, Salz und der Hash je Einheit stehen.

- [ ] **Schritt 9: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 288 + 27 = **315** (Schritt 1 sieben, Schritt 2 zwei, Schritt 3 sechs, Schritt 4 einer, Schritt 5 acht, dazu der v=1-Zwilling von K1 und `p8`, Schritt 6 einer). Zähl nach.

Commit-Botschaft: `append` schreibt v=2; `verify` prüft nach Fassung, und eine Kette aus beiden besteht; die zwei Bedingungen und was sie verhindern; dass die Migration vorwärts verlustfrei ist und rückwärts sich weigert, sobald es v=2 gibt.

---

