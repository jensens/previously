## Task 4: Die Projektionen folgen der Tilgung

**Files:**
- Modify: `src/previously/contract/store.py`, `src/previously/storage/postgres.py`, `src/previously/storage/schema.py` (ein Kommentar), `src/previously/core/projection/chronicle.py`, `src/previously/cli.py`, `tests/test_projection_derive.py`, `tests/test_projection_store.py`, `tests/test_projection_worker.py`, `tests/test_cli.py`, `docs/explanation/projections.md`, `docs/reference/cli.md`, `docs/tutorials/record-your-first-event.md`

**Interfaces:**
- Consumes: `redaction.action_name`, `redaction.parse`, `MalformedAction` aus Aufgabe 3; `catch_up`, `PROJECTIONS`.
- Produces:
  - `ProjectionStore.delete_chronicle(self, conn: Conn, event_id: int, seqs: Sequence[int] | None) -> None` — `None` nimmt jede Zeile des Events.
  - `previously.core.projection.chronicle.erasures(batch: Batch) -> list[tuple[int, tuple[int, ...] | None]]` — rein: was die Tilgungen eines Stapels aus der Chronik nehmen, in Kettenordnung. Eine Handlung, die sich nicht lesen lässt, und eine Blob-Tilgung ergeben nichts.
  - `ChronicleProjection.version == 2`; `write` fügt ein, was `derive` liefert, und löscht dann, was `erasures` nennt.
  - `previously redact` zieht nach dem Tilgen jede Projektion aus `PROJECTIONS` nach.

Warum das hält, und die Seite muss es sagen: eine Einheit ohne Inhalt ergibt keine Zeile, und eine Tilgung löscht Zeilen. Liest der Arbeiter ein Event **vor** seiner Tilgung, entstehen die Zeilen und werden gelöscht, wenn er die Tilgung liest. Liest er es **danach**, entstehen sie nie, und das Löschen trifft nichts. Beide Wege enden gleich, und der Neubau geht den zweiten.

- [ ] **Schritt 1: Tests zuerst**

| Test | Datei | Erwartung |
|---|---|---|
| `test_erasures_names_what_a_redaction_takes_out` | `test_projection_derive.py` | eine Event-Tilgung ergibt `(5, None)`, eine Einheiten-Tilgung `(5, (1, 3))`; eine verformte Handlung und eine Blob-Tilgung nichts |
| `test_delete_chronicle_takes_the_named_rows_or_all_of_an_event` | `test_projection_store.py` | |
| `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker` | `test_projection_worker.py` | Events anfügen, projizieren; ein Event tilgen, das projiziert **ist**; Einheiten eines zweiten tilgen; weitere anfügen und eines davon tilgen, **bevor** der Arbeiter es sieht; projizieren. Beide Tabellen gleich dem Neubau |
| `test_a_redacted_event_leaves_no_chronicle_row` | `test_projection_worker.py` | |
| `test_the_stats_keep_counting_an_erased_unit` | `test_projection_worker.py` | `units` vor und nach der Tilgung gleich, inkrementell wie neu gebaut |
| `test_after_redact_the_chronicle_no_longer_shows_it` | `test_cli.py` | `redact event`, dann `chronicle` **ohne** `project` dazwischen: die Zeilen fehlen, und `stderr` meldet keinen Rückstand |

Der Eigenschaftstest `test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild` bekommt die Tilgung als dritte Operation.

`test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` setzt die Nutzlast mit rohem SQL auf `NULL` und lässt die Einheiten stehen. Das ist seit Aufgabe 3 kein getilgtes Event mehr, sondern ein Grabstein ohne Anordnung, und für den stimmt, was der Test hält. Name und Docstring sagen das künftig; der Test über das wirklich getilgte Event ist der neue daneben. Dasselbe gilt für `test_chronicle_still_derives_rows_for_an_erased_payload`.

- [ ] **Schritt 2: Umsetzen**

`ChronicleProjection.version` wird 2: die Ableitung liest jetzt Tilgungen. Der erste `project` nach dem Einspielen baut darum neu und sagt es (`rebuilt: version 1 -> 2`).

In `cli.py` zieht `_cmd_redact` nach — nach einer geschriebenen Tilgung **und** nach `already`, damit ein zweiter Aufruf nachholt, was der erste nicht mehr geschafft hat. Scheitert das Nachziehen, ist die Tilgung geschrieben und die Chronik hinterher: der Fehler aus der Wortlaut-Tabelle, Rückgabecode 2. `stdout` bleibt die eine Zeile.

- [ ] **Schritt 3: Mutationen**

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `write` löscht nicht | `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker`, `test_after_redact_the_chronicle_no_longer_shows_it` | `test_a_redacted_event_leaves_no_chronicle_row`, wenn er von leerer Projektion ausgeht |
| `derive` erzeugt für eine Einheit ohne Inhalt eine Zeile | scheitert schon an `NOT NULL` von `p_chronicle.content` | — |
| `_cmd_redact` zieht nicht nach | `test_after_redact_the_chronicle_no_longer_shows_it` | `test_redact_event_prints_the_redaction_and_show_names_it` |
| `version` bleibt 1 | schreib den Test, der das hält: eine Datenbank, deren `projection_state` für `chronicle` Version 1 trägt, wird von `project` neu gebaut | — |

- [ ] **Schritt 4: Sätze, die nicht mehr stimmen, und die Seiten**

- `storage/schema.py`, Kommentar an `p_chronicle.evidence`: der Fall, den er beschreibt, ist jetzt der Grabstein ohne Anordnung.
- `core/projection/source_stats.py`, Modul-Docstring: „could a row disappear … a minimum would need a rebuild" stimmt weiter und ist jetzt **geprüft**: eine Tilgung lässt die Zeilen stehen. Ein Satz dazu.
- `docs/explanation/projections.md`: eine Projektion löscht jetzt Zeilen; das Argument oben, warum inkrementell gleich neu gebaut bleibt; warum `source-stats` sich nicht ändert und was `units` damit heißt.
- `docs/reference/cli.md`: `redact` zieht nach; `stats`: `units` zählt aufgenommene Einheiten, getilgte eingeschlossen.

- [ ] **Schritt 5: Testlauf im Tutorial, alle sechs Tore, Commit**

Vorhersage: 367 + 7 = **374**.

---

