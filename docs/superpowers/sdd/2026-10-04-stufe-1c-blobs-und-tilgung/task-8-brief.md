## Task 8: Die Anleitungen, das README, das Tutorial — die Landkarte, und der Spec friert ein

**Files:**
- Create: `docs/how-to/erase-something.md`, `docs/how-to/attach-and-fetch-a-file.md`, `docs/how-to/run-a-blob-store-on-your-machine.md`, `docs/how-to/keep-the-blob-key-safe.md`
- Modify: `docs/how-to/index.md`, `docs/how-to/restore-from-a-backup.md`, `docs/how-to/verify-the-chain.md`, `docs/how-to/rebuild-a-projection.md`, `docs/explanation/backup-encryption.md`, `docs/explanation/silent-losses.md`, `docs/explanation/erasure.md`, `docs/explanation/blobs.md`, `docs/explanation/design-records.md`, `README.md`, `docs/tutorials/record-your-first-event.md`, `docs/superpowers/landkarte.md`, `docs/superpowers/specs/2026-10-04-stufe-1c-blobs-und-tilgung.md`

**Interfaces:**
- Consumes: die Kommandos und ihre Ausgaben, am Baum und an `docs/reference/cli.md` abgelesen; die Labels `erasure`, `blobs`, `hash-version-2`.
- Produces: nichts, worauf Code sich stützt.

Vorher `plone-doc-style:author` aufrufen, je Quadrant. Eine Anleitung ist Handlung ohne Erklärung, mit Verweisen statt Gründen.

- [ ] **Schritt 1: Vier neue Anleitungen**

Jede **Hosting-neutral**: die Kommandos sind in kup6s und auf einem Host mit `docker-compose` dieselben.

- **`erase-something.md`** — die drei Formen von `redact`, je mit dem Kommando und dem, was man danach prüft (`show`, `verify`). Dazu: die Begründung steht für immer im Log und darf nicht enthalten, was getilgt wird. Steht das zu Tilgende in der Nutzlast — ein Dateiname, eine Adresse —, ist das Ziel das Event. Bricht das Kommando mit Rückgabecode 2 ab, dasselbe Kommando noch einmal. Und was die Tilgung nicht erreicht: die Sicherungen bis zum Ablauf ihrer Frist; Verweis auf `` {ref}`erasure` ``.
- **`attach-and-fetch-a-file.md`** — die sieben Variablen setzen, `append --attach`, `show`, `blob get`.
- **`run-a-blob-store-on-your-machine.md`** — ein S3-kompatibler Dienst im Container, ein Bucket, die Variablen dazu. **Tipp die Kommandos aus einem Lauf**, den du selbst gemacht hast, und sag, womit der Bucket angelegt wird. Die Seite sagt, dass dies der Dienst der Tests ist und nicht der des Betriebs, und dass auf dem Bucket weder Versionierung noch Object Lock laufen dürfen — sonst löscht Löschen nicht.
- **`keep-the-blob-key-safe.md`** — einen Schlüssel erzeugen (`age-keygen`), die Datei nach ihrem öffentlichen Schlüssel benennen, sie getrennt von den Daten sichern, und **die Sicherung proben**: einen Blob mit einem beliebigen S3-Werkzeug aus dem Bucket holen und mit `age -d -i <gesicherte Datei>` öffnen, ohne diese Software. Dazu der Schlüsselwechsel: ein neuer Empfänger für neue Objekte, die alte Identität bleibt im Verzeichnis. Eine Warnung, und nur diese eine: **Schlüsselverlust ist Totalverlust.**

- [ ] **Schritt 2: Die bestehenden Anleitungen**

- **`restore-from-a-backup.md`:** der Blob-Speicher geht bei einer Wiederherstellung der Datenbank nicht mit zurück. Nach jeder Wiederherstellung `previously verify --blobs`; ein Blob, der als fehlend erscheint, wurde nach dem wiederhergestellten Stand getilgt, und sein Event steht wieder mit Inhalt da. **Was seit dem Stand getilgt wurde, ist zu wiederholen** — und die Seite sagt ehrlich, dass das Log selbst nicht mehr weiß, was das war: wer Tilgungen zusagt, führt außerhalb der Datenbank Buch darüber. Höchstens zwei Admonitions auf der Seite.
- **`verify-the-chain.md`:** `--blobs` als zweite, längere Prüfung; sie liest jedes Byte und gehört in die Nacht, nicht in jeden Lauf der Anker-Routine.
- **`rebuild-a-projection.md`:** prüfen, ob etwas darin durch die Version 2 der Chronik falsch wird.

- [ ] **Schritt 3: Die bestehenden Erklärungen**

- **`backup-encryption.md`:** es gibt jetzt zwei Schlüssel — den der Sicherung und den der Blobs —, und für beide gilt, dass er nicht dort liegen darf, wo die Daten liegen. Wie die Aufbewahrungsfrist der Sicherung zur Zusage einer Tilgung gehört.
- **`silent-losses.md`:** lesen. Führt die Seite den Grabstein als stillen Verlust, ist er keiner mehr.
- **`erasure.md` und `blobs.md`:** ein Durchgang über beide als Ganzes. Sie sind über vier Aufgaben gewachsen; jetzt müssen sie sich lesen wie eine Seite, und jede Messung darin trägt ein Datum und stammt aus einem Lauf des Umsetzers, der sie hingeschrieben hat.

- [ ] **Schritt 4: `README.md`**

Die Zahl der Kommandos; was das Log jetzt kann; der Abschnitt über die Grenzen — was eine Tilgung nicht leistet, in zwei Sätzen und mit Verweis. Die Tabelle der eingefrorenen Berichte bekommt ihre Zeile in Schritt 7.

- [ ] **Schritt 5: Das Tutorial — die Sitzung neu tippen**

Neue Events tragen andere Hashes, und `show` druckt die Zeile `evidence=` nur noch, wo es eine gibt. **Die ganze Sitzung aus einem Lauf**, gegen den Container, den das Tutorial selbst aufsetzt, seinen eigenen Schritten folgend. Das Tutorial bleibt **ohne Blobs**: es soll ohne einen zweiten Dienst durchlaufen, und die Seite sagt das in einem Satz unter *Next steps*, mit Verweis auf die Anleitung.

Dann der Testlauf-Block, **zuletzt**. Das Rohprotokoll des Laufs gehört in den Bericht.

- [ ] **Schritt 6: Die Landkarte**

`docs/superpowers/landkarte.md`:

- *Wo das Projekt steht*: Stufe 1c ist gebaut; Teilprojekt 1 ist damit abgeschlossen.
- *Was als Nächstes kommt*: der Pilot rückt an die erste Stelle. Sein ruhender Spec umgeht 1c an drei Stellen und wird neu gefasst.
- *Offene Punkte*, Abschnitt *Stufe 1c: Blobs und Tilgung*: jeder Punkt, der erledigt ist, wird gestrichen und bekommt den Commit, der ihn erledigt hat — nach *Erledigt, seit es auf einer Liste stand*. Dazu die Punkte der Landkarte, die diese Stufe nebenbei schließt (die Unterart einer Handlung hat jetzt einen Ort; `verify` kennt eine erste Regel je Art; `evidence` geht mit der Nutzlast).
- Die vierzehn Punkte aus §12 des Specs gehen in die Landkarte, **jeder unter der Einheit, zu der er gehört** — Betrieb, Einwurf-Vertrag, spätere Teilprojekte —, nicht als Block. **Zähl sie am Spec**, nicht an diesem Satz.

Danach die Zahl der Einträge mit dem Kommando aus `CLAUDE.md` messen und in den Bericht schreiben; in `CLAUDE.md` steht keine Zahl, die dadurch falsch würde.

- [ ] **Schritt 7: Der Spec friert ein**

Der Kopf wie bei den anderen eingefrorenen Berichten, wörtlich nach dem Muster von `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`, mit dem Datum des Commits. §12: die Einleitung in die Vergangenheit, mit dem Satz, dass die Punkte in der Landkarte weiterleben.

`docs/explanation/design-records.md`: ein Bericht mehr, dort, wo die anderen eingeführt werden — Datum, Thema, die Seiten, die seine Begründung tragen (`erasure`, `blobs`, `hash-version-2`). Und die Messung, die dort für die anderen steht, für diesen wiederholen:

Run: `grep -rn "§" src tests migrations | grep -v "frozen design record"`
Erwartet: leer.

`README.md`: die Tabelle der eingefrorenen Berichte bekommt ihre Zeile.

- [ ] **Schritt 8: Alle sechs Tore, Commit**

Vale mit vier Seiten mehr als zuvor. `pytest`: die Zahl nach Aufgabe 7, unverändert — diese Aufgabe fügt keinen Test hinzu.

---

## Nach Aufgabe 8: Endprüfung, Abnahme von Hand, Protokoll, Pull-Request

Sache des Controllers, nicht einer Aufgabe:

1. **Endprüfung des ganzen Zweigs**, mit zwei Paketen wie bei den Stufen davor (Code und Konfiguration; englische Doku), dem Spec als Datei.
2. **Die Sitzung von Hand** (Abnahmebedingung 14), gegen einen Speicher auf dem eigenen Rechner, den Anleitungen folgend und nicht dem Gedächtnis: ein Anhang abgelegt, geholt, getilgt, mit `verify --blobs` geprüft. Und der Notfallweg: ein Blob aus dem Bucket geholt und mit dem Werkzeug `age` und der Identität geöffnet, ohne diese Software. Das Werkzeug ist auf der Entwicklungsmaschine nicht installiert; es zu installieren gehört zur Abnahme. Was dabei nicht stimmt, ist ein Befund wie jeder andere.
3. **`uv run pip-audit --skip-editable`** ohne Befund (Abnahmebedingung 13).
4. **Eine Fixwelle** für die Befunde, eine Nachprüfung.
5. **Das Ausführungsprotokoll** nach `docs/superpowers/sdd/2026-10-04-stufe-1c-blobs-und-tilgung/`, als eigener Commit, unverändert kopiert, mit `index.md`. Erst danach das Arbeitsverzeichnis unter `.superpowers/` löschen.
6. **Push und Pull-Request.** Der Merge ist die Abnahme (`CLAUDE.md`).

Prüfer schreiben ihren Bericht in eine Datei im Arbeitsverzeichnis des Plans und geben ein kurzes Verdikt zurück; der Controller tippt keine Berichte ab.

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.**

| Spec | Aufgabe |
|---|---|
| §1.1 Punkte 1–8 | 1: Aufgabe 5 (ein Adapter, RustFS). 2: Aufgabe 5 (`age`). 3: Aufgabe 2. 4: Aufgabe 2. 5: Aufgabe 3. 6: Aufgaben 1 und 2. 7: Aufgabe 4. 8: Aufgabe 5 (`key-id` am Objekt), Aufgabe 6 (die Referenz ohne Schlüssel) |
| §2.1 Adresse, Referenz, Register | Aufgaben 5 und 6 |
| §2.2 Verschlüsselung, Schlüssel | Aufgabe 5 |
| §2.3 Speicher | Aufgabe 5 |
| §2.4 Blob am Event | Aufgabe 6 |
| §2.5 Kommandos | Aufgabe 6; `blob get` am getilgten Blob Aufgabe 7 |
| §2.6, §2.7 Messungen | Anlagen; wiederholt vom Umsetzer in den Aufgaben 1, 5 |
| §3 Format | Aufgabe 1; `hash_version` und Salze im Schema Aufgabe 2 |
| §4.1 drei Ziele, die Regel | Event und Einheiten Aufgabe 3; Blob und Regel Aufgabe 7 |
| §4.2 das Tilgungs-Event | Aufgabe 3; die Blob-Liste Aufgabe 6; die Blob-Form Aufgabe 7 |
| §4.3 Ablauf | Schritt 1 Aufgabe 3; Schritt 3 Aufgabe 4; Schritt 2 Aufgabe 7 |
| §4.4 v=1 | Aufgabe 3 |
| §4.5 was sie nicht leistet | `erasure.md` in Aufgabe 3, die Anleitungen in Aufgabe 8 |
| §5.1 | Aufgabe 3; die Bedingungen der Datenbank Aufgabe 2 |
| §5.2 | Fassungen Aufgabe 2; Arten Aufgabe 3; Register Aufgabe 6 |
| §5.3 | Aufgabe 7 |
| §6 | Aufgabe 4; `show` in 3, 6, 7 |
| §7 | `configuration.md` Aufgabe 6; Anleitungen Aufgabe 8 |
| §8 | Dateistruktur; Verträge und Abhängigkeiten Aufgabe 5 |
| §9 Zusicherungen 1–21 | 1–4, 20, 21: Aufgabe 5. 5, 6, 8, 9, 10, 13: Aufgabe 3. 7: Aufgaben 1 und 2. 11, 12, 16: Aufgabe 7. 14, 15: Aufgabe 4. 17, 18: Aufgabe 6. 19: Aufgabe 3 |
| §10 | je in der Aufgabe, die die Tatsache ändert; Anleitungen, README, Tutorial Aufgabe 8 |
| §11 Abnahme 1–14 | 1, 2: Aufgaben 5, 6. 3: Aufgaben 1, 2. 4: Aufgaben 3, 7. 5, 6, 7: Aufgabe 3. 8: Aufgabe 7. 9: Aufgaben 3, 4. 10: Aufgabe 5. 11: die Mutationstabellen. 12: Aufgabe 8. 13: jede Aufgabe, `pip-audit` in 5 und am Ende. 14: nach Aufgabe 8 |
| §12 | Aufgabe 8, Schritt 6 |

**Nicht gedeckt und bewusst so:** kein Test hält den Wettlauf „Aufnehmen gegen Tilgen" (Spec §12 Punkt 2) — er ist ein offener Punkt und kein Versprechen.

**2. Platzhalter.** Kein „TBD". Wo der Plan keinen Code gibt, gibt er Signatur, Wortlaut, Test mit Name und Erwartung, und Mutation; das ist oben unter *Was der Plan vorgibt und was nicht* begründet. Drei Stellen verlangen vom Umsetzer ausdrücklich eine eigene Messung statt einer Zahl: die Frist des S3-Clients, die Grenze im Speichertest, und ob die Prüfung „Identität gehört zur `key_id`" etwas hinzufügt.

**3. Namenskonsistenz.** `payload_hash_v2`, `unit_digest`, `units_hash_v2`, `event_hash_v2`, `new_salt` (Aufgabe 1) werden in `chain.prepare` und `chain.link` (2) und in `verify` (2) so gerufen. `prepare(kind, occurred_at, payload, units, key[, blobs])` und `link(prepared, event_id, prev_hash, recorded_at)` stehen gleich in 2, 3 und 6. `RedactionStore` mit `lock_event`, `erase_payload`, `erase_units` in 3 und 7. `Redaction`, `RedactionIndex` mit `of_event`, `of_unit` (3) und `of_reference` (7); `read_index` in 3, 6, 7. `Redacted` wächst von 3 nach 7 um zwei Felder mit Vorgabewert. `BlobStore` mit `stat`, `put`, `get`, `delete` und `KeyProvider.identity` in 5, 6, 7. `store_blob`, `fetch_blob`, `Stored` in 5 und 6. Die Befunde und Meldungen stehen einmal, in *Vertragliche Wortlaute*, und die Aufgaben verweisen dorthin.

**4. Testzahlen**, am Plantext gezählt: 272 → **288** (Aufgabe 1, gemessen) → 315 → 367 → 374 → 417 → 453 → 485 → 485. Jede Zahl nach der zweiten ist eine Vorhersage, die der Umsetzer nachzählt: gezählt sind die Zeilen der Testtabellen und die Fälle, die sie nennen, nicht was beim Umsetzen dazukommt.

**5. Review Focus.** 1 → `test_an_attachment_that_cannot_be_read_appends_nothing`. 2 → `test_an_empty_plaintext_seals_and_opens`, `test_an_empty_file_goes_through_the_whole_path`. 3 → `test_the_same_content_twice_at_one_event_is_two_references_and_one_register_row`. 4 → `test_redact_units_orders_deduplicates_and_refuses_a_missing_seq`. 5 → `test_a_missing_bucket_is_refused_and_named`, `test_a_wrong_secret_is_refused_and_not_shown`, `test_an_endpoint_nobody_listens_on_is_unreachable_within_seconds`, `test_a_store_that_does_not_answer_appends_nothing_and_shows_no_secret`. 6 → `test_a_blob_address_that_is_not_one_is_an_input_error`. 7 → `test_a_tombstone_without_an_order_gets_one`. 8 → `test_a_redaction_racing_an_append_keeps_the_chain`.
