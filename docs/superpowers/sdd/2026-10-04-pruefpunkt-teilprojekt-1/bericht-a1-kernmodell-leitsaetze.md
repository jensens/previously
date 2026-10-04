# Prüfpunkt Teilprojekt 1 — Bericht A1: Kernmodell (Frage 1) und Leitsätze (Frage 4)

Stand: 2026-10-04, Baum auf `2bc42d4` (Worktree `pruefpunkt-teilprojekt-1`, `git status` sauber vor und nach der Arbeit).

Abkürzungen für Orte:
**E** = `docs/superpowers/specs/2026-10-01-previously-design.md` (Entwurf),
**A** = `docs/superpowers/specs/2026-10-01-architektur.md`,
**1a** = `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`,
**1b** = `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`,
**AA** = `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`.
Baumpfade relativ zur Worktree-Wurzel.
Urteile sind mit **[Urteil]** markiert; alles andere ist Beleg.

Vorab, weil es den Rahmen setzt: A §12.3 (A:1540-1543) setzt den Prüfpunkt **nach 1a, 1b und 1c**.
1c (Blobs, Verschlüsselung, Tilgungs-Vorkehrungen) ist nicht gebaut.
Alles, was an A §4.6 Punkt 2 und 3 (Blobs) hängt, ist in diesem Bericht ungeprüft.

## Messungen, auf die sich die Tabellen beziehen

Ein Wegwerfskript im Scratchpad (nicht im Repository), gegen echtes PostgreSQL 17 per testcontainers, Migrationen `0001_log` und `0002_projections` aus dem Baum, gerufen mit `uv run python …/scratchpad/measure_a1.py` aus der Worktree-Wurzel. Ausgabe wörtlich:

```
M1 same key, different content, two calls
  ids: [1] [1]
  event rows: [(1, {'state': 'opened', 'evidence': 'verbatim'})]
  unit rows: [(1, 1, 'Title: old')]
  findings: ()
M2 payload shapes a connector might carry
  mail header keys: InvalidPayload: $.headers: key 'Message-ID' must match ^[a-z][a-z0-9_]*$
  float weight: InvalidPayload: $.weight: floating point number not allowed — state a scale as an integer
  bytes raw: InvalidPayload: $.raw: type bytes not allowed
  headers as list of pairs: accepted -> [2]
M3 an 'assertion' written past append, keyless, with no sources, verify
  findings: ()
M4 an 'observation' written past append, keyless and without evidence, verify
  findings: ()
```

- **M1**: zwei getrennte `append`-Aufrufe, gleicher Schlüssel `('gitlab','issue-42')`, verschiedener Inhalt (`"Title: old"`/`opened` gegen `"Title: new"`/`closed`). Der zweite gibt `[1]` zurück; Nutzlast und Einheit des zweiten stehen nirgends; `verify` ohne Befund.
- **M2**: was `append` an Nutzlastformen abweist, die ein Konnektor mitbringen könnte.
- **M3/M4**: Events direkt über `PostgresStorage.insert_event(…, key=None)` geschrieben, mit korrekt nach `core.hashing` gerechnetem Hash — also so, wie ein künftiger zweiter Schreibpfad es könnte. `examine` (`verify`) meldet nichts.

## Frage 1: der Log, wie entworfen und wie gebaut

| # | Was | Entwurf (Ort) | Baum (Ort) | Grund (Ort) oder „kein Grund gefunden" |
|---|---|---|---|---|
| 1 | `id` aus Vorgänger statt Sequenz | A §4.1 nannte zuerst eine Sequenz (korrigiert in A:212-218) | `storage/schema.py:27-30` (`autoincrement=False`), `core/append.py:347-349` | 1a §1.1 Nr. 1 (1a:50), 1a §4.1 (1a:584-586); `docs/explanation/hash-chain.md:96ff` |
| 2 | `recorded_at` vom Aufrufer, kein DB-Default; ein Wert je `append`-Aufruf für den ganzen Stapel | A §4.1 (A:219-220) | `core/append.py:324-333`, `cli.py:217` (`datetime.now(UTC)`) | 1a §1.1 Nr. 2 (1a:51), 1a §4.1 (1a:600-602) |
| 3 | `NULLS NOT DISTINCT` auf `prev_hash` | A:190-192 (schon drin, „frühere Fassung hatte das übersehen", A:206-210) | `storage/schema.py:94-99`, `migrations/versions/0001_log.py:74-80` | 1a §1.1 Nr. 3 (1a:52) |
| 4 | Spalte `units_hash` (nicht im Architektur-Schema) | A:174-184 hat sie nicht | `storage/schema.py:37-40`, `contract/rows.py:267-269` | Korrektur K1 (1a:64-120): drei gemessene Fälschungen F1–F3 liefen durch `verify` |
| 5 | Hash-Bereich: elf Felder statt acht — `units`, `source`, `external_id` kamen hinzu | A:229-232 (acht Felder) | `core/hashing.py:141-154` | K1 (1a:98-101, 304-334); `hash-chain.md:146ff` |
| 6 | `source_key` darf höchstens **eine** Zeile je Event haben (`UNIQUE(event_id)`) | A §4.2 (A:245-251) ohne diese Beschränkung | `storage/schema.py:121-127` | 1a §2 (1a:179-184), 1a §3.1 (1a:336-359); `hash-chain.md:205-224` |
| 7 | Regel für Konnektoren: `external_id` bezeichnet das Artefakt, nicht den Transport (Issue-Nummer, Commit-SHA, Message-ID) | E §5.1 nur „quellennative ID trägt die Idempotenz" (E:277-278) | nicht im Code, nur Doku: `hash-chain.md:212-219` | 1a §5 (1a:735-762), Prüfbefund B4 |
| 8 | Zweiter Aufruf mit gleichem Schlüssel und **anderem** Inhalt: stumm verworfen, gleiche `id` zurück, Rückgabe 0 | E:277-278 („ein zweiter Import verdoppelt nichts") | `core/append.py:351-355`; gemessen M1; `docs/reference/cli.md:41-42` | Idempotenz zwischen Aufrufen gewollt (1a §5, 1a:690-693; `canonicalization.md:93-94`). Für **abweichenden** Inhalt zwischen Aufrufen kein Grund gefunden; die Tests `tests/test_append.py:75-83` und `:534-544` nutzen beide gleichen Inhalt |
| 9 | Gleicher Schlüssel zweimal **in einem** Stapel: abgewiesen | — | `core/append.py:271-302` | 1a §5 (1a:695-733), Prüfbefund N-5; `canonicalization.md:73-99` |
| 10 | `evidence` ist kein eigenes Feld, sondern reservierter Schlüssel in `payload`; `append` mischt ihn ein und weist eine Nutzlast ab, die ihn schon trägt | E §5.1 als eigenes Wahrnehmungsfeld (E:232); A §4.1 hat keine Spalte (A:174-184), A §6.2 als `RawEvent`-Feld (A:541) | `core/append.py:305-318`, `contract/types.py:187-191, 208` | Abweisung begründet: `canonicalization.md:62-71`. Warum Nutzlast statt Spalte oder Hash-Feld: kein Grund gefunden (A §4.1 hat schon keine Spalte) |
| 11 | Folge von 10: eine Tilgung der Nutzlast tilgt auch die Belegart | E:254-257 (Unterscheidung „unwiederbringlich verloren", wenn nicht modelliert) | `storage/schema.py:158-161` (`p_chronicle.evidence` NULL bei Grabstein), `core/projection/chronicle.py:191-200` | als Verhalten benannt in 1b §3.2 (1b:277-280), `projections.md:27-28`; dass damit die Belegart mitgeht, ist nirgends als Folge benannt — kein Grund gefunden |
| 12 | `RawEvent` ohne `channel_identities` und ohne `raw: bytes` | E §5.1 `channel_identities` (E:234); A §6.2 `channel_identities`, `raw: bytes \| None` „Leitsatz 6" (A:542-544) | `contract/types.py:203-214` | kein Grund gefunden. Der 1a-Plan legt die Form fest, ohne sie zu begründen (`docs/superpowers/plans/2026-10-02-stufe-1a-log.md:768`) |
| 13 | `RawEvent.payload` (beliebiges Objekt) — im Architektur-Vertrag nicht vorhanden | A:536-545 ohne `payload` | `contract/types.py:214`; CLI legt den Volltext dort ab: `cli.py:215` (`payload={"text": args.text}`) | kein Grund gefunden |
| 14 | Nutzlastbereich: keine Gleitkommazahlen, Schlüssel `^[a-z][a-z0-9_]*$` auf **jeder** Ebene, ganze Zahlen in ±2⁵³−1, keine Nullbytes, keine einzelnen Surrogate, Wurzel ist Objekt | A:235-237 nur „keine Gleitkommazahlen" | `core/canonical.py:228-278`; gemessen M2 (Header-Schlüssel, Float, Bytes abgewiesen) | 1a §3.2 (1a:363-392); `canonicalization.md:26-60` |
| 15 | `CHECK (payload IS NULL OR jsonb_typeof(payload)='object')` | A:183 nur „NULL = Grabstein" | `storage/schema.py:75-78` | Korrektur K-1 (1a:416-462); `hash-chain.md:63-94`, `silent-losses.md:32-37` |
| 16 | `unit.seq >= 1` | A:263-271 ohne `CHECK` | `storage/schema.py:111` | 1a §2 (1a:153), ohne eigene Begründung im Text; kein Grund gefunden außer Nummerierung ab 1 (1a §6, 1a:789) |
| 17 | `append` prüft Einheiten vor dem Hashen (seq ≥ 1, eindeutig, keine Nullbytes, 32-Bit-Grenzen, `start_ms ≤ end_ms`) und Quellenkennung (String, kein Nullbyte, UTF-8) | — | `core/append.py:145-234` | Prüfbefund G1 (append.py:202-213), Befund W-1 (append.py:146-199) |
| 18 | `append` schreibt ausschließlich `kind = 'observation'` und verlangt immer `source`/`external_id` | A §4.1: eine Tabelle für drei Arten (A:170-177) | `core/append.py:67-72`, `contract/types.py:205-206` | „Assertions come from the model and therefore only in a later stage" (append.py:67-71); 1b §1.1 (1b:68-76) |
| 19 | `assertion`/`action` tragen keinen `source_key`, hashen `null`; ihre Idempotenz ist „Sache des Aufrufers" | E §5.2/§5.4 sagen nichts zu Idempotenz | `core/hashing.py:133-140`, `LogStore.insert_event(key: … \| None)` in `contract/store.py:206-212` | 1a §5 (1a:774-775), 1a §3.1 (1a:329-334) |
| 20 | Nutzlast wird **nicht** gegen ein JSON-Schema je Art validiert | A:222-224 („validiert gegen JSON-Schema in `core`") | nichts im Baum: `grep -rn -i "json.schema\|jsonschema" src` leer; nur Bereichsprüfung `canonical.py` | kein Grund gefunden (Feststellungen nicht gebaut, 1b:52-53) |
| 21 | `verify` prüft keine Art-Regeln: Observation ohne `source_key` oder ohne `evidence`, Assertion ohne `sources` — alles ohne Befund | E:397-400 („`sources` ist Pflicht und wird im Schema erzwungen") | `core/verify.py:124-173` (nur Hashes, `prev_hash`, Zählung); gemessen M3, M4 | 1a §3.4 (1a:465-469: fehlende Quellenangabe ist „kein eigener Befund", wirkt nur über den Hash) |
| 22 | Grabstein besteht `verify`; ein Grabstein ist von Fälschung nicht unterscheidbar | A §4.6 (A:350-361) | `core/verify.py:76-90` | 1a §3.1 Kasten B2 (1a:283-302); `hash-chain.md:46-61` |
| 23 | Tilgung der Nutzlast tilgt die Einheiten nicht; `unit.content` bleibt `NOT NULL` | A §4.6 erwähnt `unit` nicht (A:350-361, 452-460) | `storage/schema.py:106`, `core/projection/chronicle.py:208` (Inhalt bleibt in `p_chronicle`) | 1b §1.1 (1b:87-95), 1b §10 Pkt. 2 (1b:739-743); `projections.md:199-220`; Naht offen: 1a:274-281 |
| 24 | Tilgung soll `action` mit `kind: redaction` sein | A:360-361 | nicht gebaut; `event.kind` hat nur drei Werte (`storage/schema.py:43`) — der Unterart-Wert `redaction` hätte keinen Platz außer in `payload` | „Tilgung als Event" offen: 1a §12 (1a:1142) |
| 25 | `verify` zählt Zeilen gegen `count_events` | — | `core/verify.py:176-203` | Prüfbefund B1 (1a:471-489) |
| 26 | `verify` liest in einem Schnappschuss `REPEATABLE READ`, nur lesend | 1a:504-509 verlangte „eine Transaktion" | `storage/postgres.py:99-124` (`snapshot`), `core/verify.py:248` | AA §10 Pkt. 2 (AA:437-439); 27 Fehlbefunde in 539 Läufen, `docs/superpowers/sdd/2026-10-04-aeusserer-anker/index.md:86-92` (Ruling E-1) |
| 27 | Äußerer Anker: `contract.types.Anchor(id, hash)`, `examine(anchors, exact)` | nicht im Entwurf; 1a §11 als offen (1a:1072-1095) | `contract/types.py:217-229`, `core/verify.py:206-298`, `core/anchor.py` | AA §1 (AA:25-49), AA §1.1 korrigiert 1a §11 (AA:51-76); `hash-chain.md:327-382` |
| 28 | Keine Fassungsangabe je Zeile (`hash_version`) | — | `storage/schema.py:24-79` (keine Spalte), `HASH_VERSION = 1` in `core/hashing.py:35` | 1a §3.1 Kasten B4 (1a:246-272): verlustfrei nachrüstbar |
| 29 | Eine Storage-Schnittstelle wurde zwei Protokolle `LogStore[Conn]` und `ProjectionStore[Conn]` in `contract` | A §5: ein `Storage(Protocol)` (A:479-492) | `contract/store.py:199-242` | 1b §1.1 (1b:97-101), 1b §2 (1b:112-195); `module-boundaries.md:218ff` |
| 30 | Projektionen schreiben über **je Projektion eigene** Store-Methoden (`insert_chronicle`, `upsert_source_stats`), nicht über ein generisches `write_projection(name, rows)` | A:487-489 | `contract/store.py:236-242` | Arithmetik gehört nach `core`: 1b §2.2 (1b:189-195). Warum je Tabelle eine Methode statt generisch: kein Grund gefunden |
| 31 | Gebaute Projektionen `p_chronicle`, `p_source_stats` statt `p_obligation`/`p_unit_search` | A §4.4/§4.5 (A:296-340) | `storage/schema.py:150-191`, `migrations/versions/0002_projections.py:135-167` | 1b §1.1 (1b:68-76): `p_obligation` vor dem Gate nicht baubar |
| 32 | Kein Index `p_unit_search`, keine Spalte `project` an Projektionen | A §4.5 (A:319-331) | — | 1b:49-51 (gehört nach 1c), 1b §10 Pkt. 6 (1b:757-760) |
| 33 | Einheiten-Zerlegung: Zeilenenden werden vor dem Trennen normalisiert | 1a §6 vier Schritte (1a:786-789) | `core/units.py:315-328` | `hash-chain.md:197-203` (CRLF, stiller Verlust) |
| 34 | CLI-Einwurf: `occurred_at` fällt auf „jetzt" zurück, `evidence` auf `recollection`, Text ≤ 1 000 000 Byte | E §5.1 kennt keine Vorgabewerte | `cli.py:208, 437-440, 44`; `docs/reference/cli.md:30-32` | `recollection`: „the cautious assumption" (cli.py:437-438, Prüfbefund G3). `occurred_at`-Vorgabe und Größengrenze: kein Grund gefunden (1a-Plan setzt `MAX_TEXT_BYTES` ohne Begründung, Plan:2166) |

## Frage 1: was die gebaute Schicht von den Schichten darüber verlangt

**Event-Arten, die es gibt.**
Das Schema erlaubt `observation`, `assertion`, `action` (`storage/schema.py:43`).
Geschrieben wird nur `observation` (`core/append.py:72`); es gibt im Baum keinen Schreibpfad für die beiden anderen (`grep -rn "assertion\|'action'" src/` trifft nur Kommentare und die `CHECK`-Zeile).

**S1 — Eine Feststellung passt nicht durch `append`.**
- Annahme: E §5.2 (E:305-315) — Feststellung mit `kind`, `target`, `units`, `author`, `responsibility`, `confidence`, `payload`, `sources`; A §4.1 eine Tabelle für alle drei Arten (A:170-172).
- Verlangt: `append` nimmt nur `RawEvent` (Pflichtfelder `source`, `external_id`, `evidence`, `contract/types.py:203-214`), setzt `kind='observation'` fest (`append.py:72`) und mischt `evidence` in jede Nutzlast (`append.py:315-318`).
- Warum es nicht passt: eine Feststellung hat keine Quelle und keine Belegart (1a:774-775). Sie braucht einen zweiten Schreibweg neben `append`. Der `LogStore` lässt ihn zu (`insert_event(…, key=None)`, `contract/store.py:206-212`), und M3 zeigt, dass `verify` ein so geschriebenes Event annimmt.

**S2 — Die Pflichten einer Feststellung erzwingt heute nichts.**
- Annahme: „`sources` ist Pflicht und wird im Schema erzwungen" (E:397-400); Validierung gegen JSON-Schema in `core` (A:222-224).
- Verlangt: `verify` prüft nur Hash, Vorgänger, Digests und Zählung (`verify.py:124-203`); die Datenbank nur `kind` und „Objekt oder NULL" (`schema.py:43, 75-78`).
- Warum es nicht passt: M3 — Assertion ohne `sources`, ohne Schlüssel, ohne Einheiten: `findings: ()`. M4 — Observation ohne `evidence` und ohne `source_key`: `findings: ()`. Was eine Wahrnehmung zur Wahrnehmung macht, prüft nur `append` beim Schreiben, nicht die Kette beim Prüfen. **[Urteil]** Mit einem zweiten Schreibpfad wandert jede Art-Regel in dessen Code, solange `verify` artenblind bleibt.

**S3 — `kind` heißt zweierlei.**
- Annahme: Glossar `kind` = „Art" (A:125); E §5.2 `kind assignment | obligation | decision | language` (E:307), E §5.4 `kind task_created | mail_sent` (E:417), A §4.6 `action, kind: redaction` (A:360).
- Verlangt: `event.kind` ist die Event-Art mit genau drei Werten (`schema.py:43`) und geht so in den Hash ein (`hashing.py:145`).
- Warum es nicht passt: die Unterart einer Feststellung oder Handlung hat keine Spalte; sie muss in `payload` stehen, unter einem Schlüssel, den kein Dokument festlegt. Die Projektion sieht in `Batch.events[i].kind` nur `'assertion'`.

**S4 — Bezüge einer Feststellung auf Einheiten sind nicht gedeckt.**
- Annahme: `units [3, 4, 7, 12]` und `sources` als Event-IDs + Einheiten (E:309, 314).
- Verlangt: die Tabelle `unit` gehört dem Event, das die Einheiten **hat** (`schema.py:101-112`); eine Feststellung hat selbst keine und hasht die leere Menge (M3, `units_hash([])`). Ihre Verweise stünden in `payload`, ohne Fremdschlüssel und ohne Prüfung, dass das Ziel-Event existiert.
- Warum es nicht passt: **[Urteil]** passt technisch, aber die Quellenpflicht „in Tabellenform" (A:314-315) gibt es erst in einer Projektion; im Log ist sie ungeprüftes JSON. Nebenbefund: `p_chronicle` erzeugt Zeilen je Einheit (`chronicle.py:208`), ein Event ohne Einheiten erscheint dort gar nicht.

**S5 — `p_obligation` und der Projektionsmechanismus.**
- Annahme: A §4.4 (A:296-315): `p_obligation` mit fachlicher `id`, `debtor`, `state`, `split_into`, `evidenced_by bigint[]`, `last_event_id`; die Vorrangordnung `direct > transitive > offen`, darunter Regel vor Modell (E:353-355), und „eine unverantwortete Feststellung darf eine verantwortete nie überschreiben" (E:472-476); „keine Migration, kein Handgriff" bei Versionswechsel (A:292-294).
- Verlangt:
  - (a) `Projection.write(store, conn, batch)` bekommt nur einen Stapel in `id`-Reihenfolge (`worker.py:42-72`); früheren Zustand liest eine Projektion nur über eigene Store-Methoden. Das Muster ist `source_stats` → `upsert_source_stats` (`source_stats.py:312-319`).
  - (b) `ProjectionStore` hat je Tabelle eigene Methoden (`store.py:236-242`). Eine neue Projektion heißt neue Protokollmethoden in `contract`, ihre SQL-Umsetzung in `storage` und eine Alembic-Migration für die Tabelle (1b §4.3, 1b:363-367).
  - (c) Die Zusage „inkrementell gleich neu gebaut" (1b §5.2, 1b:388-393).
- Warum es nicht passt: **[Urteil]** Zu (a)+(c): ob eine neue Feststellung die gespeicherte überschreiben darf, hängt an der `responsibility` der bisherigen. Die Spalten von `p_obligation` in A §4.4 tragen sie nicht. Inkrementell ginge es also nur mit einer zusätzlichen Spalte oder mit Rücklesen der Feststellungen aus dem Log, sonst nur durch Neubau. Zu (b): E §3 „Billig ist alles, was Interpretation ist … keine Migration, keine Schemaänderung an Bestandsdaten" (E:143-146) hält für Bestandsdaten. Eine neue Projektion kostet aber eine Migration und eine Vertragsänderung in `contract`, nicht nur eine Versionsnummer.

**S6 — Tilgung und Projektionen.**
- Annahme: Tilgung nimmt den Beleg, die Feststellung überlebt (A:452-460).
- Verlangt: Tilgung = `payload` NULL. Einheiten bleiben (1b:87-95), `p_source_stats.units` stimmt nach Einheitenlöschung nur nach Neubau (1b:311-314, 1b §10 Pkt. 2).
- Warum es nicht passt: das Tilgungs-Event muss Einheiten mittilgen **und** eine Projektionsversion erhöhen oder gezielt korrigieren (1b:739-743). Keins davon steht in A §4.6. Eine Spannung liegt nicht im Gebauten, sondern in einer Vorgabe, die die Architektur nicht kannte.

**S7 — Ein geändertes Artefakt unter derselben `external_id`.**
- Annahme: „Ein Issue hat sich geändert" ist eine Wahrnehmung (E:222); der Konnektor meldet bei Abweichung (E:466-470); `external_id` = „Issue-Nummer, Commit-SHA, Dokument-Kennung" (1a:748-749, `hash-chain.md:215`).
- Verlangt: `append` gibt bei bekanntem Schlüssel die alte `id` zurück, ohne Inhalt zu vergleichen (`append.py:351-355`).
- Warum es nicht passt: M1 — der geänderte Stand (`closed`, „Title: new") wird mit Rückgabe 0 verworfen, `verify` meldet nichts. Wer die Regel aus 1a §5 wörtlich nimmt und die Issue-Nummer als `external_id` setzt, verliert jede Änderung nach der ersten. **[Urteil]** Der Konnektor muss die Änderung selbst in die `external_id` tragen (Version, Zeitstempel, Kommentar-ID); keine Seite und kein Spec sagt das.

**Keine Spannung gefunden:**
- **Zeitordnungen**: `occurred_at` indiziert (`schema.py:81`), `p_chronicle_occurred_idx` (`schema.py:175-180`), Test für rückwärts laufendes `occurred_at` (1b:700).
- **Lückenlosigkeit für Projektionen**: `ProjectionGap` (`worker.py:140-151`).
- **Sprache als Feststellung**: keine Spalte `language` an `unit` (`schema.py:101-112`), wie A:274-275.

## Frage 4: die neun Leitsätze

| # | Leitsatz (E-Ort) | Was ihn berührt (Orte) | Status | Urteil |
|---|---|---|---|---|
| 1 | Autonomie durch Einschränkung (E:87-90) | Keine Handlung, kein Template, kein Gate gebaut. `kind='action'` nur als erlaubter Wert (`schema.py:43`). Import-linter verbietet Anbieter-SDKs ganz (1a §8, 1a:940-944) | ungeprüft | **[Urteil]** Nichts, was er regelt, existiert. Strenger als die Endfassung ist nur das SDK-Verbot. |
| 2 | Kernmodell nichts Werkzeugförmiges (E:92-95) | `source` ist freier Text (`schema.py:117`); kein Werkzeugname in Schema oder `core`. Die Regel „`external_id` = Artefakt" verlangt Werkzeugwissen im Konnektor (1a:741-750) | ungeprüft (Kernmodell); hält (Log) | **[Urteil]** Im Log hält er; die zehn Entitäten, für die er geschrieben ist, gibt es nicht. |
| 3 | Append-only; jeder Zustand Projektion (E:97-99) | Hält: `LogStore` ohne Update/Delete (`store.py:199-216`, auch A:494-496); `ProjectionStore` getrennt, „carries no truth" als Typ (`store.py:219-226`); Test inkrementell = Neubau (1b §5.2); Neubau bei jeder Versionsabweichung (`worker.py:124-130`). Biegt bzw. ist vorgesehene Ausnahme: Grabstein-Naht (A §4.6; `verify.py:76-90`); gemessen besteht `UPDATE … payload = NULL` die Prüfung (1a:283-302); Tilgung lässt Einheiten stehen (1b:87-95); `p_source_stats` additiv „nur weil append-only" (`source_stats.py:249-252`) | hält (gebaut); Tilgung ungeprüft | **[Urteil]** Im gebauten Code wird nichts gelöscht. Die geplante Tilgung ist eine benannte Ausnahme, die nach 1b schon zwei Folgepflichten mehr trägt, als A §4.6 nennt (Einheiten, Projektionsversion). Bis zum Tilgungs-Event ist jedes NULL eine unentdeckte Fälschung (`hash-chain.md:52-54`). |
| 4 | Wahrnehmungen nicht falsch, Feststellungen schon (E:101-103) | Hält: Sprache nicht an `unit` (A:274-275, `units.py:7`); keine Interpretation im `RawEvent` (`types.py:203-214`). `append` weist Formen ab, nicht Inhalte: Float, Großbuchstaben-/Bindestrich-Schlüssel, Bytes (M2), naive Zeit (`hashing.py:46-47`), leerer Text (`units.py:326-327`), Text > 1 MB (`cli.py:204-207`). Belegart wird beim Einwurf festgelegt und ist danach unkorrigierbar (`canonicalization.md:67-70`); CLI-Vorgabe `recollection` (`cli.py:440`) | hält | **[Urteil]** Abgewiesen wird nur Darstellbarkeit, nie ein Wahrheitsurteil. Echte Mail-Header oder Gleitkommawerte einer API muss der Konnektor aber umformen (Liste von Paaren geht durch, M2), und das ist ein kleiner Schritt Deutung vor der Aufnahme. |
| 5 | Unordnung in der Quelle, Ordnung in der Feststellung (E:105-109) | Keine Zuordnung gebaut (1b:56-57); Einheiten als Voraussetzung vorhanden, die CRLF-Normalisierung schützt die Körnung (`hash-chain.md:200-202`) | ungeprüft | **[Urteil]** Nur die Voraussetzung (Einheiten) steht. |
| 6 | Im Zweifel mehr aufnehmen (E:111-113) | Hält: CLI legt Volltext zusätzlich zu den Einheiten in `payload.text` ab (`cli.py:215`). Alle fünf Einheitenfelder sind im Hash (`hashing.py:96-114`). Biegt: kein `raw: bytes` und keine `channel_identities` im `RawEvent` (`types.py:203-214` gegen A:542-544, E:234), Grund nicht gefunden. Nutzlastbereich weist Header-Schlüssel, Bytes, Floats ab (M2). Abweichender Inhalt unter bekanntem Schlüssel wird stumm verworfen (M1, `append.py:351-355`). Textgrenze 1 MB (`cli.py:44`) | gebogen | **[Urteil]** Der Vertrag, über den Konnektoren aufnehmen, ist schmaler als der der Architektur, die Rohbytes ausdrücklich mit Leitsatz 6 begründete. Und M1 ist genau der unwiederbringliche Verlust, den E:148 „teuer" nennt. Beides ist noch ohne Konnektor und darum noch billig. |
| 7 | Rollen sind Beziehungen (E:115-119) | Nichts gebaut (`involvement` fehlt) | ungeprüft | **[Urteil]** Kein Feld im Baum, an dem die Prüffrage greifen könnte. |
| 8 | Strengste Festlegung gewinnt (E:121-128) | Nichts gebaut (`data_policy`, `processing_region`, `jurisdiction` fehlen) | ungeprüft | **[Urteil]** Keine Politik im Baum. |
| 9 | Unentschiedenheit darstellbar (E:130-136) | Hält: `p_chronicle.evidence/source/external_id` nullable mit Begründung (`schema.py:158-165`); `source`/`external_id` als `null` gehasht (`hashing.py:133-140`); `Outcome.rebuilt_from: int \| None` (`worker.py:83-85`). Biegt: `--evidence` Vorgabe `recollection` (`cli.py:437-440`) — ein Vorgabewert, der dauerhaft im Hash steht; `Evidence` kennt kein „unbekannt" (`types.py:187-191`, wie E:232). `--occurred-at` Vorgabe „jetzt" (`cli.py:208`, `cli.md:31`). `up_to_id = 0` und fehlende Zustandszeile werden absichtlich gleich gelesen (`rows.py:294-302`). `projection_state.version` ohne `CHECK > 0`, eine 0 sähe aus wie „nichts gebaut" (1b:796-801, F12) | gebogen (an der CLI); sonst hält | **[Urteil]** Zwei Vorgabewerte am einzigen Einwurfweg legen eine Vermutung als Tatsache in die Kette. `recollection` ist die vorsichtigere Richtung und begründet (G3). `occurred_at = jetzt` ist für eine Notiz über ein früheres Ereignis die Zeit der Notiz, nicht des Ereignisses — ohne Begründung im Baum. Die sechs Stellen aus E:133-135 sind alle nicht gebaut. |

## Was ich nicht klären konnte

- **Warum `evidence` in der Nutzlast steht** und nicht als Spalte oder eigenes Hash-Feld. A §4.1 hat schon keine Spalte; eine Entscheidung dazu fand ich nicht. Damit hängt offen, ob der Verlust der Belegart bei Tilgung (Zeile 11) gesehen wurde.
- **Warum `RawEvent` ohne `raw` und `channel_identities` gebaut wurde.** Der 1a-Plan setzt die Form (Plan:768), ohne Begründung. Das Ausführungsprotokoll der Stufe 1a ist laut `CLAUDE.md` verloren; dort könnte der Grund gestanden haben.
- **Ob das stumme Verwerfen abweichenden Inhalts zwischen Aufrufen (M1) gewollt ist.** Die Doku begründet Idempotenz zwischen Aufrufen nur für gleiche Einreichungen (`canonicalization.md:94`), Tests decken nur gleichen Inhalt ab.
- **Welche Zeit `occurred_at` bei einer `recollection` meint**: Notiz oder berichtetes Ereignis. E §5.1 (E:241-245) legt nahe: die Notiz ist die Wahrnehmung; E:231 sagt „wann es tatsächlich geschah". Die Chronik sortiert danach.
- **Ob die Tilgungs-Vorkehrungen aus A §4.6 Punkt 2/3 tragen**: 1c ist nicht gebaut, der Prüfpunkt läuft vor dem Zeitpunkt, den A §12.3 nennt.
- Die `progress.md` der drei Ausführungsprotokolle habe ich nur über die Ruling-Überschriften (1b) und die `index.md` gelesen, nicht vollständig. Ein Grund für Zeilen 12, 13, 30, 34 könnte dort stehen.

## Was ich gelesen und gefahren habe

Gelesen:
- E: 80-213 (§3, §4), 215-520 (§5)
- A: 1-462 (§1–§4), 462-566 (§5, §6.1–6.3), 1480-1555 (§12)
- 1a: 1-1145 (ganz)
- 1b: 24-393, 700-801
- AA: 25-96, 422-479
- `docs/explanation/hash-chain.md`: 1-62, 180-229, 293-382
- `docs/explanation/canonicalization.md`: ganz
- `docs/explanation/design-records.md`: 100-125
- `docs/explanation/projections.md`: per grep (Zeilen 9-28, 50, 96-100, 162-174, 199-220)
- `docs/explanation/silent-losses.md`: per grep
- `docs/reference/cli.md`: 1-60
- `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/index.md`: ganz
- `docs/superpowers/sdd/2026-10-04-aeusserer-anker/index.md`: 80-110, 235-263
- `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`: Ruling-Überschriften per grep
- `docs/superpowers/plans/2026-10-02-stufe-1a-log.md`: 755-790, 840-880, 2155-2172
- `NOTIZEN.md`: Kopf und grep (ohne Bezug zu den Fragen)
- Baum, ganz: `migrations/versions/0001_log.py`, `0002_projections.py`, `src/previously/storage/schema.py`, `contract/types.py`, `contract/rows.py`, `contract/store.py`, `core/append.py`, `core/hashing.py`, `core/canonical.py`, `core/units.py`, `core/projection/__init__.py`, `worker.py`, `chronicle.py`, `source_stats.py`
- Baum, teilweise: `core/verify.py` (ohne die Kommentarzeilen 233-273), `cli.py` (30-80, 190-222, 425-450), `storage/postgres.py` per grep, `tests/test_append.py` (20-86, 534-547), `tests/conftest.py` (1-80)

Gefahren:
- `git log --oneline -3`, `git status --short` (vorher und nachher sauber)
- `grep -rn "assertion\|'action'\|\"action\"\|kind=" src/`
- `grep -rn -i "json.schema\|jsonschema\|JSON-Schema" src docs/explanation` (ohne Treffer)
- `grep -rn "channel_identit\|raw: bytes" …` über `src`, `docs/explanation`, Specs, `sdd`, `NOTIZEN.md` und `docs/superpowers/plans`
- `grep -rn "MAX_TEXT_BYTES\|1_000_000" docs src tests`
- `uv run python <scratchpad>/measure_a1.py` (Ausgabe oben; Container per Context-Manager beendet, danach per `docker ps` geprüft)
