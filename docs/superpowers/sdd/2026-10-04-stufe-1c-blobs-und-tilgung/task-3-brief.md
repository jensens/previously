## Task 3: Die Tilgung von Event und Einheiten

Der zweite Schreibweg, und mit ihm die Einlösung der Naht aus Stufe 1a: nach dieser Aufgabe ist ein Grabstein ohne Tilgungs-Event ein Befund. Blobs kommen in Aufgabe 7 dazu; hier trägt das Tilgungs-Event eines Events eine leere Blob-Liste.

**Files:**
- Create: `src/previously/core/redaction.py`, `src/previously/core/redact.py`, `tests/test_redaction.py`, `tests/test_redact.py`, `docs/explanation/erasure.md`
- Modify: `src/previously/contract/store.py`, `src/previously/storage/postgres.py`, `src/previously/storage/schema.py` (Kommentare), `src/previously/core/errors.py`, `src/previously/core/verify.py`, `src/previously/core/append.py` (ein Kommentar), `src/previously/cli.py`, `pyproject.toml` (die Zahl der `print`-Aufrufe), `tests/test_verify.py`, `tests/test_schema.py`, `tests/test_storage.py`, `tests/test_projection_store.py`, `tests/test_cli.py`, `tests/test_docs_references.py`, `docs/explanation/index.md`, `docs/explanation/hash-chain.md`, `docs/explanation/concurrency.md`, `docs/reference/cli.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Consumes: `chain.prepare`, `chain.link` aus Aufgabe 2; `backoff_delay`, `MAX_RETRIES` aus `core.append`; `ChainPositionTaken` aus `storage.errors`; `ChainConflict` aus `core.errors`.
- Produces:
  - `previously.contract.store`:
    ```python
    class LogStore[Conn](Protocol):
        # … wie bisher, dazu:
        def read_by_kind(self, conn: Conn, kind: str) -> Iterator[EventRow]: ...

    class RedactionStore[Conn](Protocol):
        def lock_event(self, conn: Conn, event_id: int) -> EventRow | None: ...
        def erase_payload(self, conn: Conn, event_id: int) -> None: ...
        def erase_units(self, conn: Conn, event_id: int, seqs: Sequence[int]) -> None: ...
    ```
    `lock_event` liest die Zeile mit `FOR UPDATE`. `erase_payload` setzt `payload` und `payload_salt` auf `NULL`, in **einem** `UPDATE`. `erase_units` setzt an den genannten Einheiten `content`, `salt`, `speaker`, `start_ms`, `end_ms` auf `NULL`, in einem `UPDATE`; eine leere Folge ist kein Statement. `read_by_kind` liefert in Kettenordnung.
  - `previously.core.errors.RedactionRefused(PreviouslyError)`.
  - `previously.core.redaction`, rein:
    ```python
    @dataclass(frozen=True)
    class Redaction:
        id: int                                    # das Tilgungs-Event
        scope: Literal["event", "units", "blob"]
        reason: str
        event: int | None = None                   # scope event und units
        units: tuple[int, ...] = ()                # scope units
        blobs: tuple[str, ...] = ()                # scope event: was das Event referenzierte
        blob: str | None = None                    # scope blob
        events: tuple[int, ...] = ()               # scope blob

    class MalformedAction(ValueError): ...

    def event_payload(event_id: int, *, blobs: Sequence[str], reason: str) -> dict[str, object]: ...
    def units_payload(event_id: int, seqs: Sequence[int], *, reason: str) -> dict[str, object]: ...
    def action_name(payload: Mapping[str, object]) -> str: ...             # wirft MalformedAction
    def parse(event_id: int, payload: Mapping[str, object]) -> Redaction: ...  # wirft MalformedAction

    class RedactionIndex:
        def add(self, redaction: Redaction) -> None: ...
        def of_event(self, event_id: int) -> Redaction | None: ...
        def of_unit(self, event_id: int, seq: int) -> Redaction | None: ...
        def __iter__(self) -> Iterator[Redaction]: ...

    def read_index[Conn](log: LogStore[Conn], conn: Conn) -> RedactionIndex: ...
    ```
    `parse` nimmt **alle drei** Formen aus dem Spec an, auch `blob`: die Form ist eine Sache, und `verify` hält jede Handlung dagegen. Den Erbauer und den Ablauf für `blob` bringt Aufgabe 7. `of_unit` findet eine Einheiten-Tilgung, die die Einheit nennt, und sonst die Tilgung des ganzen Events. `read_index` nimmt jede Handlung, die sich lesen lässt, und übergeht die anderen — sie zu melden ist Sache von `verify`.
  - `previously.core.redact`:
    ```python
    @dataclass(frozen=True)
    class Redacted:
        redaction_id: int
        written: bool                      # False: das Ziel war schon gedeckt, nichts wurde geschrieben
        skipped_units: tuple[int, ...] = ()

    def redact_event[Conn](
        log: LogStore[Conn], eraser: RedactionStore[Conn], event_id: int,
        *, reason: str, recorded_at: datetime,
    ) -> Redacted: ...

    def redact_units[Conn](
        log: LogStore[Conn], eraser: RedactionStore[Conn], event_id: int, seqs: Sequence[int],
        *, reason: str, recorded_at: datetime,
    ) -> Redacted: ...
    ```
    Zwei Parameter für denselben Speicher, wie `catch_up(storage, storage, …)` es schon tut: Python kennt keinen Schnitt zweier Protokolle.
  - das Label `(erasure)=` auf `docs/explanation/erasure.md`.

**Die Form der Nutzlast**, wie der Spec sie in §4.2 gibt, mit dem, was `parse` verlangt: genau die vier Schlüssel `action`, `scope`, `target`, `reason`; `action` ist `"redaction"`; `reason` ein nicht leerer Text; `target` je `scope` genau die zwei Schlüssel des Specs; Listen aufsteigend und ohne Doppelte; `units` nicht leer; eine `id` ist eine ganze Zahl und kein `bool`; ein Blob-Hash 64 Hex-Zeichen, klein. Alles andere ist `MalformedAction`. Streng, weil der einzige Schreiber der eigene ist: eine Tilgung, die anders aussieht, hat niemand über `redact` geschrieben.

**Der Ablauf**, für beide Funktionen, in **einer** Transaktion aus `log.begin()`:

1. `eraser.lock_event` auf das Ziel. Gibt es keine Zeile: `RedactionRefused`. Ist das Ziel selbst eine Tilgung: `RedactionRefused`.
2. `read_index`, **nach** der Sperre: eine zweite Tilgung desselben Ziels hat an der Sperre gewartet und sieht jetzt, was die erste geschrieben hat.
3. Was schon **gedeckt** ist — ein Event, wenn `of_event` etwas findet; eine Einheit, wenn `of_unit` etwas findet —, wird nicht noch einmal genannt. Bleibt nichts, wird kein Event geschrieben; die Grabsteine werden trotzdem gesetzt (das heilt eine Anordnung ohne Vollzug), und das Ergebnis nennt die deckende Tilgung mit `written=False`.
4. Sonst: die Nutzlast bauen, `chain.prepare(kind="action", occurred_at=recorded_at, payload=…, units=(), key=None)`, die Spitze lesen, `chain.link`, `log.insert_event`, dann die Grabsteine.
5. `ChainPositionTaken` rollt die Transaktion zurück; warten mit `backoff_delay`, von vorn, höchstens `MAX_RETRIES` Mal, dann `ChainConflict`.

Gedeckt heißt: es gibt eine Tilgung. Nicht: der Inhalt fehlt. Ein Grabstein ohne Tilgung ist **nicht** gedeckt, und `redact` schreibt ihm eine (Review Focus 7).

`redact_units` zusätzlich: die `seq` ordnen und Doppelte entfernen; eine `seq`, die das Event nicht hat, ist eine Weigerung, bevor irgendetwas geschrieben ist; ein Event mit `hash_version != 2` ist eine Weigerung mit dem Satz aus der Wortlaut-Tabelle.

- [ ] **Schritt 1: `core/redaction.py`, ohne Datenbank**

`tests/test_redaction.py`:

| Test | Erwartung |
|---|---|
| `test_the_event_form_round_trips` | `parse(9, event_payload(5, blobs=[], reason="r"))` ergibt `Redaction(id=9, scope="event", event=5, …)` |
| `test_the_units_form_orders_and_deduplicates` | `units_payload(5, [3, 1, 3], …)` trägt `[1, 3]` |
| `test_parse_refuses_what_is_not_exactly_one_of_the_forms` | parametrisiert, je `MalformedAction`: `reason` fehlt; `reason` leer; `scope` unbekannt; ein fünfter Schlüssel; `units` leer; `units` ungeordnet; `event` ist `True`; ein Blob-Hash mit 63 Zeichen; `target` trägt die Schlüssel eines anderen `scope` |
| `test_an_action_without_a_name_is_malformed` | `action_name({})` wirft |
| `test_the_blob_form_parses` | die dritte Form aus dem Spec, von Hand geschrieben |
| `test_the_index_finds_a_unit_through_its_own_redaction_and_through_its_event` | beide Wege von `of_unit` |
| `test_every_payload_a_builder_makes_is_canonical` | `canonical(…)` wirft nicht |

- [ ] **Schritt 2: Der Speicher**

| Test | Datei | Erwartung |
|---|---|---|
| `test_lock_event_returns_the_row_or_none` | `test_storage.py` | Zeile, oder `None` für eine `id`, die es nicht gibt |
| `test_lock_event_makes_a_second_locker_wait` | `test_storage.py` | zwei Verbindungen; die zweite kommt erst durch, wenn die erste abgeschlossen hat |
| `test_erase_payload_takes_the_salt_along` | `test_storage.py` | beides `NULL`, `payload_hash` unverändert |
| `test_erase_units_touches_only_the_named` | `test_storage.py` | die genannte Einheit ist ein Grabstein mit `digest`; die andere ist, wie sie war |
| `test_read_by_kind_yields_only_that_kind_in_chain_order` | `test_storage.py` | |
| `test_postgres_storage_satisfies_the_redaction_protocol` | `test_projection_store.py`, neben dem Test für die zwei anderen Protokolle | |

- [ ] **Schritt 3: Der Ablauf**

`tests/test_redact.py`, gegen die Datenbank:

| Test | Erwartung |
|---|---|
| `test_redacting_an_event_writes_an_action_and_leaves_tombstones` | Nutzlast und Salz `NULL`; jede Einheit ohne Inhalt und Salz, mit `digest`; das neue Event ist `action`, v=2, ohne Einheiten und ohne Quellschlüssel, mit der Form aus dem Spec; `verify` meldet nichts |
| `test_redacting_units_leaves_the_others_attested` | nach `redact_units(…, [2])` meldet `verify` nichts; danach Einheit 1 mit rohem SQL geändert: `unit 1 does not match its digest` |
| `test_redaction_and_tombstones_arrive_together_or_not_at_all` | ein Speicher, dessen `erase_units` wirft (eine Hülle um den echten, wie `_FailingStore` in `test_projection_worker.py`): danach gibt es kein neues Event, und der Inhalt steht |
| `test_a_second_redaction_of_the_same_event_writes_nothing` | `written=False`, dieselbe `redaction_id`, dieselbe Zahl von Events |
| `test_redacting_units_again_skips_what_is_covered` | `skipped_units` nennt sie; nur die neue steht im neuen Event |
| `test_redact_units_orders_deduplicates_and_refuses_a_missing_seq` | Review Focus 4 |
| `test_a_redaction_cannot_be_redacted` | Weigerung, nichts geschrieben |
| `test_a_missing_event_is_refused` | |
| `test_units_of_a_version_1_event_are_refused_and_the_event_is_not` | ein v=1-Event von Hand; `redact_units` weigert sich mit dem Satz; `redact_event` geht, und `verify` meldet nichts |
| `test_a_tombstone_without_an_order_gets_one` | Review Focus 7: Nutzlast mit rohem SQL auf `NULL`; `verify` meldet es; `redact_event` schreibt (`written=True`) und tilgt den Rest; `verify` meldet nichts |
| `test_a_redaction_racing_an_append_keeps_the_chain` | Review Focus 8, nach dem Muster von `test_a_conflict_on_the_chain_position_is_retried` in `test_append.py` |
| `test_the_anchors_hold_after_every_kind_of_redaction` | ein Anker vor den Tilgungen hält danach („contains"); ein Anker danach hält mit `exact` |
| `test_what_is_erased_cannot_be_guessed_from_what_stays` | vor der Tilgung: `unit_digest(…, salt=gespeichertes Salz)` trifft den gespeicherten `digest` (die Kontrolle); danach ist das Salz weg und der `digest` derselbe |

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `erase_units` lässt `salt` stehen | jeder Test, der Einheiten tilgt — die Datenbank weist das `UPDATE` ab (`unit_tombstone_check`) | `test_a_missing_event_is_refused` |
| `redact_event` setzt die Grabsteine in einer zweiten Transaktion | `test_redaction_and_tombstones_arrive_together_or_not_at_all` | `test_redacting_an_event_writes_an_action_and_leaves_tombstones` |
| `read_index` vor `lock_event` | — das zeigt kein Test mit einem Faden. Schreib den Test mit zwei Fäden auf dasselbe Ziel (`test_two_redactions_of_one_event_at_once_write_one`), miss, dass er mit der Mutation rot wird, und nenne im Bericht, in wie vielen von zwanzig Läufen | `test_a_second_redaction_of_the_same_event_writes_nothing` |

- [ ] **Schritt 4: `verify` verlangt Anordnung und Vollzug**

Was der Durchlauf sich merkt, ist klein: die Grabsteine, die er sieht, und die Tilgungen, die er liest. Am Ende, **noch im Schnappschuss**, gleicht er ab:

- Jede Handlung: `action_name`, und für `"redaction"` `parse`. Was wirft: `action has no valid form`, unter der `id` der Handlung.
- Jeder Grabstein der Nutzlast ohne `of_event`: `payload is erased without a redaction`. Jeder Grabstein einer Einheit ohne `of_unit`: `unit <seq> is erased without a redaction`.
- Jede Tilgung gegen ihr Ziel, das dafür **gelesen** wird (`read` und `units_by_event` für die eine `id` — Tilgungen sind wenige): steht das Ziel nicht vor ihr in der Kette, oder hat es die genannte Einheit nicht: `redaction names a target that does not exist`. Trägt es noch, was getilgt sein soll: die zwei Befunde „not carried out".
- Ein v=1-Event mit Einheiten ohne Inhalt: sind es **alle** und nennt eine Tilgung das Event, wird an ihm keine Einheit geprüft, und es gibt keinen Befund. Sind es nicht alle: `units are erased in part, which version 1 cannot attest`. Die Entscheidung fällt am Ende, nicht an der Zeile — die Tilgung steht in der Kette hinter ihrem Ziel.

`examine` steht heute nah an der Grenze von `C901`. Das Merken und Abgleichen gehört in eine eigene kleine Klasse oder in Funktionen, die `examine` ruft; miss die Komplexität, bevor du committest.

| Test, alle in `test_verify.py` | Erwartung |
|---|---|
| `test_a_tombstone_without_a_redaction_fires` — **der bestehende `test_a_tombstone_passes`, umgedreht** | `payload is erased without a redaction` |
| `test_a_unit_tombstone_without_a_redaction_fires` | `unit 2 is erased without a redaction` |
| `test_a_redaction_of_an_event_that_was_not_carried_out_fires` | eine Tilgung von Hand über `chain` und `insert_event`, ohne Grabsteine |
| `test_a_redaction_of_units_that_was_not_carried_out_fires` | |
| `test_a_redaction_naming_a_missing_target_fires` | parametrisiert: eine `id` hinter der eigenen; eine `seq`, die das Event nicht hat |
| `test_an_action_without_a_valid_form_fires` | parametrisiert: ohne `action`; `redaction` ohne `reason` |
| `test_partial_unit_tombstones_in_version_1_fire` | |
| `test_tombstone_and_redaction_are_matched_across_batch_boundaries` | `batch=2`, Ziel im ersten Stapel, Tilgung im dritten |

In `test_schema.py` prüft `test_a_real_tombstone_stays_permitted_and_passes_verification` zwei Dinge: dass SQL-`NULL` zulässig bleibt, wo JSON-`null` es nicht ist, und dass `verify` es durchlässt. Das erste gilt weiter. Das zweite ist umgedreht. Name und Docstring folgen.

Mutationen:

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| der Abgleich der Grabsteine am Ende entfällt | `test_a_tombstone_without_a_redaction_fires` | `test_an_intact_chain_passes` |
| der Abgleich läuft je Stapel statt am Ende | `test_tombstone_and_redaction_are_matched_across_batch_boundaries` | `test_a_tombstone_without_a_redaction_fires` |
| das Ziel wird nicht gelesen, nur die Grabsteine gezählt | `test_a_redaction_of_units_that_was_not_carried_out_fires` | `test_redacting_units_leaves_the_others_attested` |

- [ ] **Schritt 5: Die Kommandozeile**

```
previously redact event ID --reason TEXT
previously redact units ID SEQ [SEQ…] --reason TEXT
```

`redact` ist das erste Kommando mit einer zweiten Ebene: die `arguments`-Funktion seines `Command` hängt eigene Unterparser an. `COMMANDS` bekommt einen Eintrag, und der Test über die Hilfe bleibt, wie er ist.

Die Kommandozeile prüft, dass `--reason` nicht leer ist, ruft `redact_event` oder `redact_units` mit `datetime.now(UTC)`, und druckt die Zeilen aus der Wortlaut-Tabelle: auf `stdout` genau eine, auf `stderr` je übersprungene Einheit eine. Eine Weigerung ist ein `RedactionRefused` und geht durch den bestehenden `except`-Zweig von `main`: ein Satz, Rückgabecode 2.

`show` liest das Verzeichnis der Tilgungen (`read_index`) und nennt für jeden Grabstein das Event, das ihn angeordnet hat. Die Zeile `evidence=` druckt es nur noch, wenn die Nutzlast den Schlüssel trägt: eine Handlung hat keine Belegart, und `evidence=None` wäre eine Aussage, die niemand gemacht hat.

| Test, alle in `test_cli.py` | Erwartung |
|---|---|
| `test_redact_event_prints_the_redaction_and_show_names_it` | `stdout` ist `redacted by event 2`; `show 1` druckt `payload=<erased by event 2>` und je Einheit `<erased by event 2>`; `show 2` druckt die Nutzlast der Tilgung und keine Zeile `evidence=` |
| `test_redact_units_names_each_tombstone` | |
| `test_redacting_twice_says_already` | Rückgabecode 0, `already redacted by event 2` |
| `test_a_refused_redaction_is_one_sentence` | parametrisiert über die fünf Weigerungen dieser Aufgabe: Rückgabecode 2, eine Zeile auf `stderr`, nichts auf `stdout` |
| `test_show_says_so_when_the_payload_is_erased` — besteht | bleibt: ein Grabstein **ohne** Tilgung druckt weiter `payload=<erased>` |

`tests/test_docs_references.py` hält, was die Reference zitiert, gegen den Code, der es druckt. Die Weigerungen entstehen in `core/redact.py`, die Befunde in `core/verify.py`: erweitere sein Blickfeld um die neue Datei, und miss mit einem Zitat auf `cli.md`, das nichts erzeugt, dass der Test rot wird.

Die Zahl der `print`-Aufrufe im Kommentar zur `T201`-Ausnahme in `pyproject.toml`: mit dem Kommando messen, das dort steht.

- [ ] **Schritt 6: Sätze, die nicht mehr stimmen**

Run: `grep -rn "tombstone\|erasure\|append-only\|never change\|no update" src docs/explanation docs/reference docs/how-to README.md | grep -v "^docs/superpowers"`

Lies jede Fundstelle. Sicher falsch werden:

- `storage/postgres.py`, Modul-Docstring: „no update, no delete". Es gibt jetzt genau zwei `UPDATE` auf das Log, beide hinter `RedactionStore`, und was sie dürfen, ist aufgezählt.
- `contract/store.py`: `LogStore` „write once, read in chain order, never change" gilt weiter — für dieses Protokoll, und das ist der Punkt des dritten. Die Zahl „nine methods" und ihr `grep` werden neu gemessen, über die Module, die `LogStore` heute rufen.
- `cli.py`, Kommentar in `_cmd_log`: „nothing in `src` rewrites or deletes either afterwards".
- `storage/schema.py`: der Schlussabsatz des Kommentars an `event_payload_object_check` („The honest limit: *today* …") beschreibt die Lücke, die diese Aufgabe schließt.
- `storage/schema.py`, Kommentar an `event_prev_hash_idx`: „no advisory lock, no FOR UPDATE". Für die Kettenposition stimmt das weiter, und so muss der Satz es sagen: die Tilgung sperrt die Zeile ihres **Ziels**, nicht die Spitze. Dasselbe auf `docs/explanation/concurrency.md` — dort gehört in einem Absatz hin, dass es jetzt zwei Schreibwege an derselben Kette gibt, dass beide dieselben zwei Indizes entscheiden lassen, und wozu die eine Zeilensperre da ist.
- `core/verify.py`, Docstring von `_payload_finding`.
- `core/append.py`, Kommentar an `_KIND`: Handlungen schreibt jetzt `core/redact.py`.
- `docs/explanation/hash-chain.md`, der Abschnitt mit dem Label `tombstone-seam`: der Preis der Naht ist bezahlt. Der Abschnitt sagt künftig, was die Naht war, was sie kostete, und verweist auf `` {ref}`erasure` ``.

- [ ] **Schritt 7: `docs/explanation/erasure.md`**

Neue Seite, Label `(erasure)=`, in `index.md` eingehängt. Explanation, „About erasure". Was sie tragen muss — der Spec ist deutsch und friert ein, diese Seite ist danach die Quelle:

- Was eine Tilgung nimmt und was stehen bleibt, für Event und Einheiten (die Tabelle aus Spec §4.1, ohne die Blob-Zeile; die kommt in Aufgabe 7).
- **Warum sie ein Event ist:** nur so steht die Berechtigung in der Kette, und nur so ist ein Grabstein von einer Fälschung zu unterscheiden. Die Messung aus Stufe 1a, umgedreht.
- **Warum die Nutzlast sich nicht in Teilen tilgen lässt.**
- **Warum ein Tilgungs-Event sich nicht tilgen lässt.**
- **Was „gedeckt" heißt**, und warum `redact` einem Grabstein ohne Anordnung eine schreibt, statt sich zu weigern — und was daran ehrlich bleibt: das Tilgungs-Event ist jünger als der Grabstein.
- **Was eine Tilgung nicht leistet** (Spec §4.5): die Sicherungen bis zum Ablauf ihrer Frist; eine Wiederherstellung auf einen älteren Stand bringt Getilgtes zurück; der Quellschlüssel bleibt; was abgeleitet oder kopiert wurde. Zu den Hashes ein Verweis auf `` {ref}`hash-version-2` ``.
- Die Tabelle der Befunde gehört **nicht** hierher, sondern nach `cli.md`.

- [ ] **Schritt 8: `docs/reference/cli.md`**

`redact` mit seinen zwei Formen, den Ausgaben und Weigerungen; `show` mit den neuen Zeilen; die Befunde dieser Aufgabe; die Tabelle der Rückgabecodes; „eight subcommands" wird neun.

- [ ] **Schritt 9: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 315 + 52 = **367** (Schritt 1 fünfzehn mit den neun Fällen, Schritt 2 sechs, Schritt 3 vierzehn mit dem Test aus der Mutationstabelle, Schritt 4 neun mit den vier Fällen und ohne den umgedrehten, Schritt 5 acht mit den fünf Fällen). Zähl nach.

---

