# Prüfpunkt Teilprojekt 1 — Bericht A2: Storage-Schnittstelle (Frage 2) und §11/§13/§16 (Frage 5)

Stand: 2026-10-04, Baum auf `2bc42d4` (Merge PR #2, äußerer Anker), Worktree
`pruefpunkt-teilprojekt-1`. Nur gelesen und gemessen; im Repository nichts
geändert. Eine Typprobe lief außerhalb des Repositorys im Scratchpad (siehe
„Was ich gelesen und gefahren habe").

Abkürzungen: **Arch** = `docs/superpowers/specs/2026-10-01-architektur.md`,
**Entwurf** = `docs/superpowers/specs/2026-10-01-previously-design.md`,
**1a** / **1b** / **Anker** = die drei Stufen-Specs unter
`docs/superpowers/specs/`, **sdd-1b** / **sdd-Anker** / **sdd-Doku** = die
Ausführungsprotokolle unter `docs/superpowers/sdd/`.

---

## Frage 2: die Storage-Schnittstelle

### Zählungen, mit Kommando

```
$ awk '/^class /{c=$2} /^    def [a-z]/{n[c]++} END{for(k in n) print k, n[k]}' \
      src/previously/contract/store.py src/previously/storage/postgres.py
LogStore[Conn](Protocol): 9
PostgresStorage: 19
ProjectionStore[Conn](Protocol): 7

$ grep -hoE '^    def [a-z_]+' src/previously/contract/store.py | sort -u | wc -l
15            # begin steht in beiden Protokollen

$ grep -o 'storage\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py \
      | sed 's/^[^:]*://' | sort -u | wc -l
9             # = LogStore, wie store.py:6-9 und module-boundaries.md:224-238 behaupten

$ grep -ohE '(log|store)\.[a-z_]*\(' src/previously/core/projection/*.py | sort | uniq -c
      1 log.read(            1 log.source_keys(     1 log.tip(        1 log.units_by_event(
      2 store.begin(         1 store.insert_chronicle(   1 store.projection_state(
      2 store.set_projection_state(   1 store.source_stats(   1 store.truncate_projection(
      1 store.upsert_source_stats(
```

- `LogStore`: **9** Methoden (`store.py:48-62`): `begin`, `snapshot`, `tip`, `lookup`, `insert_event`, `read`, `units_by_event`, `count_events`, `source_keys`.
- `ProjectionStore`: **7** Methoden (`store.py:82-88`): `begin`, `projection_state`, `set_projection_state`, `truncate_projection`, `insert_chronicle`, `source_stats`, `upsert_source_stats`.
- Zusammen 16 Plätze, 15 verschiedene Namen. Der Arbeiter ruft alle 7 von `ProjectionStore`, aber nur 4 von `LogStore` (`tip`, `read`, `units_by_event`, `source_keys`) — und **`log.tip`/`log.read` mit der Verbindung aus `store.begin()`** (`worker.py:117-139`).
- `PostgresStorage`: **19** öffentliche Methoden, dazu `__init__`, `_transaction` und die Modulfunktion `from_dsn`. 19 − 15 = **4 außerhalb jedes Protokolls** (s. u.).
- Zum Vergleich §5 der Architektur (Arch:480-491): **9** Methoden als „Endfassung über alle Stufen" (Arch:474-477), davon im Baum nicht gebaut: `stream`, `search`; in anderer Form: `append` → `insert_event` (+`tip`, `lookup`, `begin`; die Kette rechnet `core`), `last_hash` → `tip`, `write_projection(name, rows: Mapping)` → je Projektion getypte Methoden (`insert_chronicle`, `upsert_source_stats`), `clear_projection` → `truncate_projection`.

### Die fünf Eigenschaften

Gemeinsamer Befund zur Spalte „wo entschieden": `docs/explanation/design-records.md:61` und `:77-79` sagen ausdrücklich, dass **keine** der fünf Eigenschaften auf einer Seite begründet ist („Searched across this documentation, not one of the five is argued anywhere"); §5 der Architektur bleibt die einzige Quelle. `storage/postgres.py:6-14` wiederholt die fünf als Zusage des Moduls.

| Eigenschaft | wie gemeint (Arch:494-496) | wie gebaut | wo entschieden |
|---|---|---|---|
| kein Update | Schnittstelle ändert nichts | `LogStore`: hält. `ProjectionStore`: **hat Update** — `set_projection_state` (`postgres.py:387-403`, `ON CONFLICT DO UPDATE`), `upsert_source_stats` (`postgres.py:456-484`) | 1b §1.1 „§5 wird zu zwei Protokollen" (1b:97-101), 1b §2.2 (1b:156-195); `store.py:65-80`; `module-boundaries.md:274-277`; `postgres.py:12-14` |
| kein Delete | Schnittstelle löscht nichts | `LogStore`: hält. `ProjectionStore`: **hat Delete** — `truncate_projection` = `DELETE` (`postgres.py:405-414`; Begründung DELETE statt TRUNCATE im Docstring) | wie Zeile davor |
| keine Transaktionssteuerung nach außen | Aufrufer steuert keine Transaktion | **nicht gehalten.** `begin()` und `snapshot()` geben `AbstractContextManager[Conn]` heraus (`store.py:48-49, 82`); jede Methode nimmt `conn`. Die Transaktionsgrenze (Umfang des `with`) liegt beim Aufrufer in `core` und `cli`; `core` baut darauf tragende Invarianten: „Zeilen und `up_to_id` in einer Transaktion" (`worker.py:82-85, 117-142`), ein Schnappschuss über die ganze Prüfung (`verify.py:240-248`). Was **nicht** herausgegeben wird: `commit`/`rollback` als Methoden, die Isolationsstufe (fest im Store, `postgres.py:95-103`) | 1a §7, Prüfbefund G4: „Die Transaktionsgrenze gehört damit dem Aufrufer" (1a, Abschnitt „Jede Methode nimmt die `Connection`", in 1a:799-930); `postgres.py:236-252`; `snapshot()` durch Ruling E-1 der Anker-Ausführung (sdd-Anker `progress.md:450-456`, `index.md:86-92, 232-233`), **über den eingefrorenen Anker-Spec hinaus** (Anker §6 „Nicht angefasst", Anker:320-328). Keine Explanation-Seite argumentiert die Umkehr gegen §5 |
| kein SQL-Durchlass | keine SQL-Zeichenkette über die Grenze | gehalten: keine Methode nimmt SQL oder Ausdrücke; Abfragen entstehen nur in `storage/postgres.py`. Statisch zusätzlich durch das opake `Conn` (s. u.) | Arch §5; `postgres.py:6-9`; `.importlinter:52-60` (Vertrag `only-storage-knows-sql`) |
| keine Rückgabe von Datenbankobjekten | nur Zeilen ohne Domänenbedeutung | Lesemethoden geben eingefrorene Dataclasses aus `contract/rows.py` zurück (`rows.py:21-96`) — gehalten. **Aber** `begin()`/`snapshot()` geben zur Laufzeit eine echte `sqlalchemy.Connection` mit offener Transaktion heraus (`postgres.py:105-129, 131-158`); nur der Typ ist verborgen | Arch §10.1 „Was `storage` zurückgibt" (Arch:901-923); 1a §7 (`EventRow` ist Zeile); 1b §2.2 (1b:186-187: „`core` nennt diesen Typ nie") |

**Was `Conn` verbirgt und was nicht.**

- *Verbirgt*: den Namen `sqlalchemy.Connection` im Quelltext von `core` — damit fällt die Kante `core → storage.postgres` und mit ihr die zwei benannten import-linter-Ausnahmen (`.importlinter:27-50, 61-66`; `module-boundaries.md:218-257`). Und unter pyright strict ist auf einem unbeschränkten Typparameter kein Attributzugriff möglich. Gemessen in einer Probe außerhalb des Repositorys (eigene Datei mit `# pyright: strict`, *nicht* gegen die Projektkonfiguration): `conn.execute("SELECT 1")` in einer über `LogStore[Conn]` generischen Funktion ergibt `error: Cannot access attribute "execute" for class "object*" (reportAttributeAccessIssue)`. Derselbe Zugriff nach `isinstance(conn, sqlalchemy.Connection)` blieb in der Probe **ohne** Fehler — dicht ist das Ganze also nur zusammen mit dem import-linter-Vertrag, der `core` den Import von `sqlalchemy` verbietet (`.importlinter:18-26, 52-60`).
- *Verbirgt nicht*:
  1. dass zur Laufzeit ein lebendiges Datenbankobjekt mit offener Transaktion in `core` liegt;
  2. die **Semantik** der Verbindung: dass `begin()` READ COMMITTED gibt und `snapshot()` einen REPEATABLE-READ-Schnappschuss, steht nur in den Docstrings von `PostgresStorage` (`postgres.py:105-129`), im Protokoll stehen beide Methoden ohne jede Zusage (`store.py:48-49`). `core` hängt aber an dieser Semantik: die Zählabstimmung in `verify` (`verify.py:240-256`), die Unerreichbarkeitsbegründung in `append` mit vier Vorbedingungen, darunter „isolation level is READ COMMITTED" (`append.py:417-422`), die Backoff-Begründung (`append.py:456-466`);
  3. die **Fehlerklassen**: `ChainPositionTaken` und `SourceKeyTaken` liegen in `previously.storage.errors`, nicht in `contract`; `core` importiert sie (`append.py:43-44`), das Protokoll nennt sie nicht. Eine zweite Implementierung müsste `previously.storage.errors` importieren. Nebenbefund: der Docstring von `SourceKeyTaken` sagt „Do not retry" (`storage/errors.py:28-33`), `append` wiederholt aber im Teilfall (G-7, `append.py:18-25, 440-453`);
  4. dass `LogStore` und `ProjectionStore` **dieselbe** Verbindung teilen müssen: `catch_up[Conn](log: LogStore[Conn], store: ProjectionStore[Conn], …)` liest das Log über die Verbindung aus `store.begin()` (`worker.py:73-75, 117-121`), und `cli` übergibt dasselbe Objekt zweimal (`cli.py:341-346`). Dazu Fremdschlüssel von `p_chronicle.event_id` und `p_source_stats.last_event_id` auf `event` (`migrations/versions/0002_projections.py:36, 57`). Log und Projektionen sind damit an eine Datenbank und eine Transaktion gebunden;
  5. für `cli` gar nichts: `cli` ist gegen `PostgresStorage` getypt (`cli.py:29, 145-152`), sieht also `Connection` als Typ; dass es ihn nicht nennt, ist Konvention (ruling T9-a, `cli.py:131-134, 146-148`), kein Vertrag — `only-storage-knows-sql` hat als Quellen nur `core` und `contract` (`.importlinter:55-57`), `module-boundaries.md:92-107` begründet, warum `cli` nicht hineingehört.

### Was um die Protokolle herumgeht

**Methoden von `PostgresStorage` in keinem Protokoll** (4), und jeder Aufrufer (`grep -rnE '\.(units|tip_and_bookmark|read_chronicle|read_source_stats)\(' src`):

| Methode | Ort | Aufrufer | Zweck |
|---|---|---|---|
| `units(conn, event_id)` | `postgres.py:275-288` | `cli.py:333` (`show`) | Einheiten eines Events; aus dem Protokoll bewusst draußen (1b:149-152; `module-boundaries.md:240-242`) |
| `tip_and_bookmark(conn, name)` | `postgres.py:490-526` | `cli.py:377, 415` | Rückstand in **einer** Anweisung (READ COMMITTED gibt je Anweisung einen Schnappschuss) |
| `read_chronicle(conn, *, since, until, limit)` | `postgres.py:528-560` | `cli.py:381` | Projektion zurücklesen |
| `read_source_stats(conn)` | `postgres.py:562-573` | `cli.py:416` | Projektion zurücklesen |

Der Kommentar `postgres.py:486-488` begründet die Lage: „The protocols hold what `core` needs, and `core` never reads a projection back." Außerdem liest `cli` das Log direkt über `storage.begin()`/`storage.read` (`cli.py:246-247` für `log`, `cli.py:305-307` für `show`) — ein Leser des Logs außerhalb von `core` existiert also schon.

**Importe von `previously.storage` außerhalb von `src/previously/storage/`** (`grep -rn 'previously\.storage' src --include=*.py | grep -v '^src/previously/storage/'`):

```
src/previously/core/append.py:43:from previously.storage.errors import ChainPositionTaken
src/previously/core/append.py:44:from previously.storage.errors import SourceKeyTaken
src/previously/cli.py:27:from previously.storage.errors import StorageError
src/previously/cli.py:28:from previously.storage.postgres import from_dsn
src/previously/cli.py:29:from previously.storage.postgres import PostgresStorage
```

Die Schichtung erlaubt `core → storage` (`.importlinter:9-16`); `core → storage.errors` braucht keine Ausnahme, weil `storage/errors.py` nichts importiert.

**Importe von `sqlalchemy` außerhalb `storage`**: keine. `grep -rn 'sqlalchemy' src --include=*.py | grep -v '^src/previously/storage/'` findet nur sechs Kommentarzeilen (`cli.py:229, 357, 517`; `append.py:119, 171, 207`). `.importlinter` heute: vier Verträge, **keine** Ausnahme (`.importlinter:27-50, 61-66` beschreiben die zwei weggefallenen). Gate-Ausgabe laut `module-boundaries.md:73-80`: `Contracts: 4 kept, 0 broken.` (nicht selbst gefahren).

**Baut ein Modul oberhalb `storage` eine Abfrage, nennt es Tabelle/Spalte, hängt es an PostgreSQL-Verhalten?**

- Abfragen: nein. Kein `select`/`text`/`execute` in `core` oder `cli` (`grep -nE 'execute|text\(|Connection' src/previously/cli.py src/previously/core -r` — nur Kommentare und `split_plaintext`).
- Tabellen-/Spaltennamen: nur in Kommentaren (`append.py:119`, `anchor.py:18`, `chronicle.py:6`). **Ein String-Kopplungspunkt im Code**: die Projektionsnamen `"chronicle"` und `"source-stats"` stehen in `core` (`chronicle.py:68`, `source_stats.py:66`) und ein zweites Mal in `storage` als Name→Tabelle-Abbildung (`postgres.py:370-375`, `_PROJECTION_TABLES`). Jede neue Projektion braucht eine Zeile dort und eigene Schreibmethoden in `ProjectionStore`.
- PostgreSQL-Verhalten, auf das `core` baut (alles in Kommentaren/Konstanten belegt):
  - Isolationsstufe READ COMMITTED und Serialisierung über Unique-Indizes: `append.py:6-8, 406-422, 456-466`; `docs/explanation/concurrency.md:10-15, 41-48, 124-137`.
  - Indexnamen und deren Reihenfolge nach OID: übersetzt in `storage` (`postgres.py:60-75`), aber die Argumentation steht in `core` (`append.py:12-17, 27-31`) und `concurrency.md:78-109`.
  - Wertebereich `int4` als Konstante in `core`: `_UNIT_INT_MIN/_MAX` (`append.py:119-126`), gemessen gegen PostgreSQL 17.
  - `text`/`jsonb` kann kein Nullbyte: `append.py:192`, `canonical.py:65`.
  - `bigint`-Länge 19 Zeichen: `anchor.py:18-19`.
  - Spaltentypen als Unerreichbarkeitsgrund: `verify.py:103-117`.
  - „Keine Lücken" (`id = Vorgänger.id + 1` plus Unique-Index auf `prev_hash`): `worker.py:93-97, 123-134`.

### Wachstum je Stufe

Gezählt mit `git show <commit>:src/previously/storage/postgres.py | grep -nE '^    def [a-z]'` und dasselbe für `contract/store.py` (öffentliche Methoden):

| Stand | Commit | Protokoll(e) | `PostgresStorage` öffentlich | Was dazukam, wofür |
|---|---|---|---|---|
| nach 1a | `07561a8`, unverändert bis `cdc508a` | **keins** (`contract/store.py` existiert nicht; 1a §7 „Es gibt kein `Storage`-Protokoll, und das ist eine Entscheidung", W-4) | **9** | `begin` (Aufrufer hält die Transaktion, G4), `tip` (ersetzt `next_id`/`last_hash`, ein SELECT), `lookup`, `insert_event` (nimmt fertigen Hash), `read` (serverseitiger Cursor), `units` (`show`), `units_by_event` (stapelweise, N2), `count_events` (Zählabstimmung, B1), `source_keys` (Quelle im Hash, K1; stapelweise) — 1a §7 |
| nach 1b | `b0396b6` | `LogStore` **8**, `ProjectionStore` **7** (14 Namen) | **18** (+9) | `projection_state`, `set_projection_state`, `truncate_projection`, `insert_chronicle`, `source_stats` (Lesen für `merge` in `core`), `upsert_source_stats` (schreibt nur, Arithmetik in `core`, 1b:189-195) — Protokoll; `tip_and_bookmark` (Rückstand in einer Anweisung, Fixwelle `ff3c261`), `read_chronicle`, `read_source_stats` — nur `cli` |
| nach Anker | `2bc42d4` | `LogStore` **9**, `ProjectionStore` **7** (15 Namen) | **19** (+1) | `snapshot` (REPEATABLE READ, nur lesend) für `examine`: 27 von 539 Läufen meldeten unter gleichzeitigem Anhängen falsche Befunde (`postgres.py:110-129`; sdd-Anker `index.md:86-92, 130-138`; Ruling E-1) |

Der Anker-Spec selbst sah **keine** Schnittstellenänderung vor (Anker:315-316 „Keine Migration, keine Tabelle, keine neue Abhängigkeit, kein neuer Vertrag"; Anker:318-328 ließ die Isolationsfrage offen). Die eine Erweiterung kam aus der Endprüfung, nicht aus dem Spec.

### Urteil (als Urteil markiert)

**Urteil:** Gemessen an „kein SQL im Kern" ist die Schnittstelle schmal geblieben — keine Abfrage, kein Import, kein SQL-Typ oberhalb `storage`, und die Grenze wird von zwei Werkzeugen gemeinsam gehalten. Durchgesickert ist nicht SQL, sondern **PostgreSQL-Semantik**: Transaktionsumfang, Isolationsstufe, Fehlerklassen und Wertebereiche sind Zusagen, auf die `core` baut, die aber im Protokoll nicht stehen, sondern in Docstrings von `PostgresStorage` und in `storage.errors`. Drei der fünf Eigenschaften aus §5 gelten nur noch für `LogStore` oder gar nicht mehr (Transaktionssteuerung), und keine Seite begründet das. Drücken werden die nächsten Teilprojekte voraussichtlich an drei Nähten: (1) ein **zweiter Leser des Logs** (MCP-Server) braucht Lesemethoden für Projektionen und `units`, die heute nur `cli` am konkreten `PostgresStorage` hat — also entweder ein drittes Protokoll oder Wachstum an `ProjectionStore`; (2) **Suche** (`search`, `p_unit_search`) bringt Indexsteuerung in rohem SQL (Arch:974) und je Projektion getypte Schreibmethoden, die `ProjectionStore` mit jeder Projektion verbreitern; (3) **Blobs** sind keine Datenbank-Transaktion, die geteilte `Conn` von Log und Projektion passt nicht auf einen Objektspeicher, und die Fehlerklassen- und Isolationszusagen müssten für einen zweiten Store-Typ erstmals ausgeschrieben werden.

---

## Frage 5: §11, §13, §16 Zeile für Zeile

„berührt" heißt: beim Bau von 1a, 1b oder Anker angefasst, vorweggenommen oder davon abhängig geworden.

| Punkt (Ort) | berührt | was daran hängt oder es vorwegnimmt (Ort) | Status |
|---|---|---|---|
| **§11-1** Textsuchvariante (Arch:1439) | nein | Nichts gebaut. `p_chronicle` teilt absichtlich den Primärschlüssel `(event_id, seq)` mit dem künftigen `p_unit_search` (1b:49-51) | offen, unverändert |
| **§11-2** Embedding-Modell und `N` — „Teilprojekt 1" (Arch:1440) | nein | Nichts gebaut. Zugewiesen an Teilprojekt 1, aber **keine** Stufe in §12.1 (Arch:1506-1510) trägt es: 1c ist dort nur „Blobs"; erst 1b:49-51 schiebt „Blobs und Suche" nach 1c | offen; Zuordnung zu einer Stufe fehlt in Arch §12.1 |
| **§11-3** ORM-Detailabbildung der Projektionen, „innerhalb der Grenze aus §10.1" (Arch:1441) | **ja** | 1b hat sie für zwei Projektionen entschieden: Core-Tabellen in `storage/schema.py`, Zeilen-Dataclasses in `contract/rows.py:80-96`, je Projektion eine getypte Store-Methode (1b §2.2, §3, §7). **Die Grenze aus §10.1 selbst wurde dabei verschoben**: `p_*` werden migriert (`migrations/versions/0002_projections.py`), §10.1 sagt „nicht migriert" (Arch:955-962) — siehe nächster Abschnitt | entschieden für 1b; Grenze geändert |
| **§11-4** Interne Abgleichlogik je Konnektor (Arch:1442) | am Rand | Kein Konnektor gebaut. Vorweggenommen ist der Rahmen: Idempotenz über `(source, external_id)` in `source_key` (1a §5), Eingangsprüfungen für „a connector from stage 2 on" (`append.py:130-142, 145-200, 204-212`), und die Vorbedingung „`insert_event` schreibt Event vor Schlüssel" für jeden künftigen Aufrufer (`append.py:399-405, 417-422`) | offen; Rahmen fest |
| **§11-5** Prompt- und Templatetexte (Arch:1443) | nein | — | offen, unverändert |
| **§11-6** Rangfunktion der Triage (Arch:1444) | nein | — | offen, unverändert |
| **§11-7** Deployment-*Mechanismus*, „kein Modul hängt daran" (Arch:1445) | **ja** | Der Anker hängt am Betrieb: Ablageort, Intervall, Restore-Point im Ankertakt (Anker §5.1, Anker:250-300; Anker §10 Punkt 4, Anker:441-454). Die Schnittstelle des Kommandos wurde vom Compose-Fall geformt: `--anchors -` liest `stdin`, „nicht Bequemlichkeit, sondern der Weg, auf dem der Compose-Fall ohne Volume auskommt" (Anker:282-296). Container-Aufruf ohne durchgereichte Standardeingabe erst in der Endprüfung gefunden; `kubectl exec` ungemessen (sdd-Anker `index.md:206-212, 255-257`). Seit 2026-10-04 verlangt `CLAUDE.md` („Operations are part of every design") beide Hostingformen in jedem Spec | Mechanismus offen; die Annahme „kein Modul hängt daran" hält für `cli`/Anker nicht |
| **§11-8** Oberfläche jenseits MCP (Arch:1446) | am Rand | Keine UI gebaut. Die CLI ist von einem „minimalen Einwurfweg" (1a §9) auf acht Unterkommandos gewachsen (`grep -c add_parser src/previously/cli.py` → 8), mit Ausgabeverträgen auf `stdout`/`stderr` und Rückgabecodes, die eine Reference-Seite zitiert und ein Test bewacht (`docs/reference/cli.md`; `tests/test_docs_references.py`) | offen; CLI ist faktisch eine Oberfläche mit Vertrag |
| **§11-Nachtrag** Deutsch und Englisch gemischt (Arch:1450-1482) | nein | Betrifft Suche und Embedding, beide nicht gebaut. Kanonisierung verlangt ASCII-Schlüssel, nicht ASCII-Inhalt (`DEPENDENCIES.md:82-86`) | offen, unverändert |
| **§13-1** `pg_dict` + Hunspell (Arch:1560) | nein | — | offen |
| **§13-2** Versionsstände der Postgres-Erweiterungen (Arch:1561) | nein | Keine Erweiterung installiert; 1a §9 stellt `CREATE EXTENSION` zurück (1a:978-980), entgegen Arch:964-966. Mindestversion PostgreSQL 15 wegen `NULLS NOT DISTINCT` (`concurrency.md:71`), Tests gegen 17 | offen |
| **§13-3** MRTR/Tasks in Claude Code (Arch:1562) | nein | — | offen, „vor Teilprojekt 3" |
| **§13-4** Zeitpunkt für den Bau der Tilgung (Arch:1563, 1571-1574) | **ja** | 1b fand: Tilgung der Nutzlast tilgt die Einheiten nicht, eine Chronik je Einheit zeigt den Inhalt weiter (1b §1.1, 1b:87-95; `projections.md:199-220`); `p_source_stats.units` wird nach einer Tilgung von Einheiten falsch, ohne Neubau (1b:306-314, 1b §10 Punkt 2). Der Test `test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` nagelt das heutige Verhalten fest (`tests/test_projection_worker.py:285`). `hash-chain.md:42-44` hält die Naht für Einheiten offen (`content` heute `NOT NULL`). sdd-Anker `index.md:258-261`: `show` liest Event und Einheiten in zwei Anweisungen; „Kommt die Löschung am Tombstone-Saum, gilt die Begründung nicht mehr" | Zeitpunkt offen; die Anforderungen an die Tilgung sind gewachsen (Einheiten, Projektionsversion) |
| **§13-5** Welche pgBackRest-Plugin-Implementierung (Arch:1564) | ja (Doku) | `docs/explanation/backup-encryption.md:52-75` übernimmt die datierte Messung (Opera vs. Dalibo) und lässt die Wahl „a build-time decision". Der Anker-Spec baut auf WAL-Archiv/PITR auf (Anker:256-273), und `docs/how-to/restore-from-a-backup.md` hängt den Restore an die Kettenprüfung | offen, Messung datiert |
| **§13-6** Trace MCP ↔ Gate über OpenTelemetry (Arch:1565) | nein | — | offen |
| **§16-1** Datenbankwahl (Entwurf:1724) | ja | PostgreSQL gebaut; pgvector nicht installiert (s. §13-2) | entschieden, gebaut ohne Erweiterung |
| **§16-2** Messversuch Textsuche (Entwurf:1725) | nein | — | offen |
| **§16-3** Tokenizer-Weg (Entwurf:1726) | nein | — | offen |
| **§16-4** mehrsprachiges Embedding-Modell (Entwurf:1727) | nein | wie §11-2 | offen |
| **§16-5** Voxtral und Diarisation (Entwurf:1728) | am Rand | Vorweggenommen im Schema: `unit.speaker`, `start_ms`, `end_ms` (1a), und `p_chronicle.speaker` „fuer Voice (Stufe 2) schon da" (1b:262); `append` prüft `start_ms`/`end_ms` gegen `int4` (`append.py:119-126`) | offen; Schema vorbereitet |
| **§16-6** Rechtsfrage Gesprächsaufnahme (Entwurf:1729) | nein | — | offen, vor Teil 2 |
| **§16-7** Verarbeitungsräume der Anbieter (Entwurf:1730) | nein | — | offen |
| **§16-8** Call-Plattformen (Entwurf:1731) | nein | — | offen |
| **§16-9** Pilotkunde (Entwurf:1732) | nein | — | offen |
| **§16-10** Externer Compliance-Anlass, „Annahme in §5.5" (Entwurf:1733) | **ja** | Die Annahme steht tatsächlich in Entwurf §5.7 (Entwurf:513-517: „nicht zertifizierungsgetrieben … keine WORM-Speicherung"). Der Anker bewegt sich darauf zu: „Gegenüber Dritten ist der Anker nur ein Beleg, wenn er bei einem Dritten liegt", Ablageorte „Git-Repository bei einem Dritten … gesperrtem Force-Push" und „Bucket mit Object Lock" (Anker:446-451); dazu „ein beglaubigtes ‚wann'" über einen Zeitstempeldienst (Anker §10 Punkt 3) und die Signatur des Schreibers (Punkt 1) | Annahme unbestätigt; der Anker hat Teile eines Drittbelegs vorweggenommen |

---

## Frage 5: was als entschieden galt und anders gebaut wurde

| Festlegung (Ort) | gebaut (Ort) | Status | Grund (Ort) |
|---|---|---|---|
| §4.4: Projektionen ableitbar und wegwerfbar, FK nur auf `event`, Präfix `p_` (Arch:279-282) | `0002_projections.py:36, 57`; `projections.md:11-20`; Test `test_incremental_equals_rebuilt` (`tests/test_projection_worker.py:91`) und Eigenschaft (`:402`) | wie festgelegt | 1b §5 |
| §4.4: `version` als Neubau-Auslöser, „keine Migration, kein Handgriff" (Arch:293-295) | `worker.py:105-113` (Vergleich `!=`) | wie festgelegt, präzisiert (`!=` statt `<`) | 1b:324-328 |
| §4.4: Beispielprojektion `p_obligation` (Arch:299-313) | nicht gebaut; stattdessen `p_chronicle` und `p_source_stats` | anders | vor Stufe 4 nicht baubar, weil nur `observation` existiert (1b §1.1, 1b:68-76) |
| §4.6 Vorkehrung 1: Kette hängt am Hash, Tilgung behält `payload_hash` (Arch:350-361) | `schema.py:36-42` (`payload` nullable, `payload_hash NOT NULL`); erweitert um `units_hash` und Quelle im Hash (1a Korrektur K1) | wie festgelegt, erweitert | 1a §1.1 K1 |
| §4.6: Tilgung ist selbst ein Event (`action`, `kind: redaction`) (Arch:361-362) | nicht gebaut; `append` schreibt nur `observation` | vertagt | 1a §12 „Tilgung als Event im Log … mit der ersten echten Tilgung" |
| §4.6 Vorkehrung 2: Blobs von Anfang an verschlüsselt (Arch:363-431); §13 „Teil von Teilprojekt 1" (Arch:1573) | nicht gebaut | vertagt | 1c nicht gebaut (Arch §12.1 1c) |
| §4.6 Vorkehrung 3: keine Versionierung auf dem Blob-Bucket (Arch:433-448) | kein Bucket | vertagt | wie davor |
| §4.6 und 1b: Tilgung reicht nicht in die Einheiten | — | Lücke in der Festlegung gefunden | 1b §1.1 (1b:87-95), §10 Punkt 2 |
| §5: eine Schnittstelle (Arch:480-491) | zwei Protokolle `LogStore`/`ProjectionStore` (`store.py:45-88`) | anders | 1b §1.1 (1b:97-101), `module-boundaries.md:274-277` |
| §5: `stream(project=…, from_id)` als Iterator (Arch:483, 497-498) | kein `stream`; `read(conn, from_id, limit)` mit serverseitigem Cursor (`postgres.py:253-273`), Arbeiter liest in Stapeln (`worker.py:121`) | anders | 1a §7 nennt `stream` „gehört zu 1b"; 1b nennt keinen Grund, warum es nicht kam (gesucht: `grep -n stream` in 1b → nur 1b:562 „Ein Strom" für die Ausgabe) |
| §7.1: `project` ereignisgetrieben; Warteschlange `job` mit `SKIP LOCKED` (Arch:603-637) | `project` ist ein Kommando (`cli.py:340-347`); keine Tabelle `job` | vertagt | 1b §1.1 (1b:78-85), §10 Punkt 4: kommt mit dem ersten Konnektor |
| §7.1: `maintain` täglich, Kettenprüfung (Arch:612) | Routine `verify --anchors … && anchor >> …` per Cron/CronJob (`docs/how-to/verify-the-chain.md:52-61`; Anker:276-296) | anders (Betriebsroutine statt Prozess) | Anker §5.1 |
| §7.3 Regel 1: `append` über Unique-Indizes, READ COMMITTED, Stapeln (Arch:657-665) | `postgres.py:95-99`; `append.py:6-31` | wie festgelegt | 1a §4 |
| (keine Festlegung) Lesekonsistenz der Prüfung | `snapshot()` REPEATABLE READ (`postgres.py:110-129`) | neu | Ruling E-1, sdd-Anker `index.md:86-92` |
| §7.3 Regel 2: Projektionen pro Name einfädig, „`up_to_id` ist die Sperre" (Arch:667-669) | keine Sperre; zwei parallele `project` laufen beide durch | anders | 1b §10 Punkt 8 (1b:764-780, Prüfbefund F11): Sperre kommt mit der Warteschlange |
| §7.3 Regel 3: Reprojektion in eine **Schattentabelle**, am Ende umschalten; Eingang läuft weiter (Arch:670-672) | Neubau leert die Tabelle **an Ort und Stelle** (`DELETE` plus Zustandszeile in einer Transaktion, `worker.py:105-113`; `postgres.py:405-414`), dann Stapel | anders | **kein Grund geschrieben.** Gesucht: `grep -rnEil 'schatten|shadow|umschalt' docs/` findet nur Arch und eine fremde Fundstelle (`A001 … shadowing`); weder 1b-Spec, 1b-Plan noch sdd-1b erwähnen die Schattentabelle |
| §7.3 Regel 4: „Lesen sieht nie halbe Projektionen" (Arch:673-674) | während eines Neubaus sehen `chronicle`/`stats` eine leere oder Teilprojektion und melden den Rückstand auf `stderr` (`projections.md:176-192`) | anders | Rückstandsmeldung ist 1b §6.5 (1b:593-618); Bezug zu Regel 4 nirgends hergestellt |
| §12.1 1b-Nachweis „Eingang läuft weiter" (Arch:1509) | kein Test mit gleichzeitigem `append` während eines Neubaus (`grep -nEi 'concurrent|thread' tests/*.py` → nur `test_append.py`) | nicht nachgewiesen | Nicht in den 14 Abnahmebedingungen von 1b §9 (1b:694-711). Baulich plausibel (Neubau schreibt nur `p_*`/`projection_state`), gemessen hat es niemand |
| §12.1 1b-Nachweis „Projektion bauen, Version erhöhen, neu bauen, identisches Ergebnis" (Arch:1509) | `tests/test_projection_worker.py:91, 132, 160, 402` | wie festgelegt | 1b §5, §9 |
| §12.1 1b „Reprojektion als Stream" (Arch:1509) | Stapel à 500 über `read` mit `stream_results`/`yield_per=100` | anders (gestapelt, kein `stream`) | 1b §4.1 (1b:331-346) |
| §12.1 1a-Nachweis: schreiben, verifizieren, Idempotenz, Verzweigung unmöglich (Arch:1508) | `tests/test_append.py:43-170`, `tests/test_properties.py:164-304` (u. a. `test_p3_concurrent_writers_leave_one_gapless_chain_with_each_event_once`), `test_verify.py` | wie festgelegt, erweitert (K1, äußerer Anker) | 1a §11; Anker-Spec |
| §7.4: „Kettenprüfung schlägt an → alles Schreiben anhalten, Alarm" (Arch:683) | kein Schreibstopp; `verify` endet mit 1, die Anleitung sagt „Treat any exit code other than `0` as an alarm" (`verify-the-chain.md:61`) | vertagt (nur Alarm) | **kein Grund geschrieben** (`grep -rnEi 'anhalten|halt all|stop.*writ'` über Specs 1a/1b/Anker und die Anleitung: nichts) |
| §7.4 übrige Zeilen (Konnektor, Modell, Rendern, Zielort) (Arch:678-686) | nicht gebaut | vertagt | Teilprojekte 2-6 |
| §10.1: SQLAlchemy Core, kein ORM (Arch:882-923) | `storage/schema.py`, `postgres.py` | wie festgelegt | `DEPENDENCIES.md:26` |
| §10.1: Pydantic für Nutzlastvalidierung (Arch:887) | nicht Abhängigkeit; Validierung von Hand in `core/canonical.py` | vertagt | `DEPENDENCIES.md:64-80` (Zombie-Regel; kommt mit MCP-Schemaexport) |
| §10.1: `EventRow` (Arch:909-919) | `contract/rows.py:29-41`: zusätzlich `payload_hash`, `units_hash`, `payload` nullable; liegt in `contract`, nicht `storage` | anders | 1a §7; 1b:173-184 (Korrektur beim Planen, Schichtung) |
| §10.1: „Alembic migriert `event`, `source_key`, `unit`, `job`, `projection_state`. **Projektionstabellen (`p_*`) werden von Code erzeugt und verworfen, nicht migriert**" (Arch:955-960) | `0002_projections.py` migriert `p_chronicle`, `p_source_stats` samt Index | anders | 1b §4.3 (1b:365-367) und §7 (1b:648-650) setzen es voraus, **ohne** §10.1 zu nennen; 1b §1.1 führt es nicht unter den Korrekturen. `rebuild-a-projection.md:46-47` schreibt Migrationen für Projektionen vor |
| §10.1: Versionssprung „`DROP` und neu bauen" (Arch:961-962) | `DELETE` (`postgres.py:405-414`) | anders | Docstring: TRUNCATE nimmt ACCESS EXCLUSIVE und soll mit der Zustandszeile zurückrollbar sein |
| §10.1: erste Migration richtet Erweiterungen ein (Arch:964-966) | keine `CREATE EXTENSION` | vertagt | 1a §9 (1a:978-980) |
| §10.1: Projektionen schreiben per `COPY` oder `executemany` (Arch:973) | `executemany` (`postgres.py:419-437, 462-484`) | wie festgelegt | — |
| §10.1: `stream` mit serverseitigem Cursor (Arch:972) | `read` mit `stream_results=True, yield_per=100` (`postgres.py:255-261`) | wie festgelegt (unter anderem Namen) | 1a §7 |
| §10.6: uv, hatchling + hatch-vcs, ruff (DTZ, S, TID, TC; `line-length` oben), pyright strict, import-linter, pytest/cov `fail_under = 90`, testcontainers, hypothesis, pytest-randomly, pre-commit, Python 3.14, synchron (Arch:1333-1397) | `pyproject.toml:2-3, 11, 47-49, 53-54, 61, 127, 146`; `.pre-commit-config.yaml` (`repo: local`); `grep -rn 'async ' src` → 0 | wie festgelegt | `DEPENDENCIES.md:24-48`; pre-commit läuft aus dem venv (`CLAUDE.md`, „One source of truth") |
| §10.6: **pip-audit in CI** (Arch:1345) | `.github/workflows/gates.yml` hat sechs Tore, kein pip-audit | nicht gebaut | **kein Grund geschrieben** (`grep -rnEil 'pip-audit|renovate'` außerhalb `.venv`/`.git` findet nur Arch) |
| §10.7: Register `DEPENDENCIES.md` mit Datum und Urteil (Arch:1408-1429) | `DEPENDENCIES.md:24-48` | wie festgelegt | — |
| §10.7: **Renovate** (Arch:1431-1433) | nicht im Repository | nicht gebaut | kein Grund geschrieben (wie pip-audit) |

---

## Frage 5: Überraschungen von keiner Liste

Quelle sind die Lehren am Ende der drei Ausführungsprotokolle. `sdd-Doku/index.md` hat **keinen** Abschnitt „was diese Ausführung gelehrt hat"; die Lehren stehen dort verstreut im Hauptbuch, ich nenne die, die das Hauptbuch selbst als „übertragbar" auszeichnet. Keiner der folgenden Punkte steht in Arch §11, Arch §13 oder Entwurf §16.

- **„Eine Transaktion" ist unter READ COMMITTED nicht „ein Zeitpunkt".** In zwei Ausführungen hintereinander gefunden: Rückstandszeile (sdd-1b `index.md:97-103`, Fix `tip_and_bookmark`) und Kettenprüfung mit gemessen 27 von 539 Fehlbefunden unter gleichzeitigem Anhängen (sdd-Anker `index.md:217-220, 130-138`, Fix `snapshot()`). Arch §7.3 legt die Isolationsstufe nur für das Schreiben fest (Arch:661-662). Für Lesezusagen gab es keine Festlegung, und jetzt hat die Schnittstelle eine Methode mehr.
- **Ein Tor, das nie feuern kann, ist ein Kommentar**: `ProjectionGap` prüfte auf Leere und konnte für eine echte Lücke nie auslösen (sdd-1b `index.md:77-80`; `worker.py:123-134`; `projections.md:77-80`). Das betrifft die „keine Lücken"-Eigenschaft, die die Architektur als gegeben behandelt.
- **Ruling-Labels sind je Plan vergeben und lösen nicht auf**: keines der vierzehn zitierten Labels führt zu der Entscheidung, die es nennt, und das Hauptbuch der 1a-Ausführung ist verloren (sdd-1b `index.md:32-43`; sdd-Doku `progress.md`, Ruling F-d; `.importlinter:27-41`). Damit ist die Begründung der 1a-Rulings T7-a, T8-c und T9-a nur noch im Kommentar am Ort vorhanden.
- **Getippte Ausgabe altert an Stellen, die kein Tor hält** (sdd-1b `index.md:81-87`), und das Tor für `§`-Zitate prüft nur den Marker, nicht ob der Spec eingefroren ist (sdd-1b `index.md:91-96`). Beides sind Lücken der Prüfmaschinerie der Dokumentation.
- **Die Must-survive-Liste soll mechanisch erzeugt werden**: B5 fehlte auf der Liste und auf allen zwanzig Seiten (sdd-Doku `progress.md:1250-1267`).
- **Code im Plan wird auf jedem Weg ausgeführt, den er hat**: zweimal war ein wörtlich vorgegebener Rumpf falsch, darunter `_read_anchors` für `-` mit Traceback und Rückgabecode 1 (sdd-Anker `index.md:193-199`).
- **Eine Prüfung darf ihren Maßstab nicht aus dem nehmen, was sie prüft**: die Restore-Anleitung schnitt die Ankerdatei an der Spitze des wiederhergestellten Logs (sdd-Anker `index.md:200-205`; `index.md:77-85`, Rulings T3-c, T3-f).
- **Eine unerwartete Ausnahme endet mit Rückgabecode 1, dem Code eines Befunds** (sdd-Anker `index.md:241-245`). Der Fehlervertrag der CLI steht auf keiner Liste; Arch §7.4 kennt nur Fehlerverhalten von Prozessen.
- **Nebenbei, ohne eigenen Lehrsatz**: die Fremdschlüssel von `p_*` auf `event` (Arch §4.4) brachen jedes `TRUNCATE source_key, unit, event` in den Tests (`NotSupportedError`) (sdd-1b `progress.md:255-262`).

Nicht hier, weil auf einer Liste: „Die Frage nach dem Betrieb findet die Löcher" (sdd-Anker `index.md:213-216`) gehört zu §11 Zeile 7 (Deployment-Mechanismus). Arch hat diese Zeile für unkritisch erklärt, siehe erste Tabelle.

---

## Was ich nicht klären konnte

- **Die pyright-Probe zu `Conn`** lief in einer eigenen Datei außerhalb des Repositorys mit `# pyright: strict`, **nicht** gegen die Projektkonfiguration. Ein Gegenstück im Baum hätte den Baum verändert. Eine Kontrollprobe (`ok`, ohne Fehler) und die Umgehung über `isinstance` sind in derselben Datei mitgemessen.
- **„Eingang läuft weiter" während eines Neubaus**: nicht gemessen. Dafür braucht es ein Rennskript gegen eine Datenbank. Mein Auftrag war Lesen; ich habe keine Datenbank gestartet.
- **Tore und Tests nicht gefahren.** Die Gate-Ausgabe `4 kept, 0 broken` ist aus `module-boundaries.md:73-80` übernommen, nicht selbst gemessen.
- **Warum Schattentabelle, Schreibstopp bei Kettenbefund, pip-audit und Renovate wegfielen**: in Specs, Plänen, Hauptbüchern und Explanation-Seiten keinen Grund gefunden (Kommandos oben). Ob es eine mündliche Entscheidung gab, kann ich nicht wissen.
- **Gründe der 1a-Rulings** (T7-a, T8-c, T9-a): das Hauptbuch ist verloren (`CLAUDE.md`, „A ruling citation is provenance"), also nicht nachprüfbar.
- **Umfang von 1c**: Arch §12.1 (Arch:1510) nennt nur Blobs, 1b:49-51 und der Auftrag nennen Blobs und Suche. Welche Fassung gilt, habe ich nicht entschieden.
- **Verweisfehler in Entwurf §16**: Zeile 1733 verweist für den Compliance-Anlass auf „§5.5", der Text steht in §5.7 (Entwurf:513-517). Nur festgestellt, nicht weiter verfolgt.
- **sdd-Doku** hat keinen Lehren-Abschnitt in `index.md`. Meine Auswahl aus dem 1332 Zeilen langen Hauptbuch stützt sich nur auf die Stellen, die es selbst „Lehre"/„übertragbar" nennt (`grep -nEi 'lehre|gelernt|gelehrt'`). Sie ist nicht vollständig.

## Was ich gelesen und gefahren habe

**Gelesen** (Zeilenbereiche):
- `.superpowers/pruefpunkt/brief-a2-storage-und-offenes.md` (ganz)
- Arch: 1-28, 277-462, 455-505, 601-692, 877-1030, 1149-1192 (teilweise), 1328-1434, 1430-1587
- Entwurf: 440-530, 1715-1762
- 1a: 40-124, 799-930, 965-990, 1134-1144
- 1b: ganz (1-802)
- Anker: 250-330, 422-479 (+ `grep` über das ganze Dokument)
- sdd-Anker `index.md` ganz; sdd-1b `index.md` ganz; sdd-Doku `index.md` ganz, `progress.md:1250-1332`; sdd-1b `progress.md:250-266`; sdd-Anker `progress.md:450-456`
- `src/previously/contract/store.py` ganz; `src/previously/storage/postgres.py` ganz; `src/previously/storage/errors.py:1-40`; `src/previously/core/append.py:1-60, 110-230, 380-487`; `src/previously/core/anchor.py` ganz; `src/previously/core/projection/worker.py` ganz; `src/previously/core/verify.py:100-125, 236-260`; `src/previously/cli.py:125-155, 336-350`
- `docs/explanation/module-boundaries.md` ganz; `docs/explanation/projections.md` ganz; `docs/explanation/hash-chain.md:25-50`; `docs/explanation/design-records.md:70-84`; `docs/explanation/backup-encryption.md:52-75`; `docs/how-to/rebuild-a-projection.md:1-60`; `docs/how-to/verify-the-chain.md:50-66`
- `.importlinter` ganz; `DEPENDENCIES.md:24-90`; `pyproject.toml` (Auszüge über `grep`); `migrations/versions/0002_projections.py:1-30` + `grep`

**Gefahren** (alle aus dem Worktree, nur lesend):
- `git log --oneline --first-parent main`; `git log --oneline --reverse -- src/previously/storage/postgres.py src/previously/contract/store.py`
- `git show {07561a8,cdc508a,b0396b6}:src/previously/storage/postgres.py | grep -nE '^    def [a-z]'`; `git show {cdc508a,b0396b6}:src/previously/contract/store.py` (cdc508a: Datei existiert nicht)
- die Zählkommandos aus „Zählungen" oben
- `grep -rn 'previously\.storage' src …`, `grep -rn 'sqlalchemy' src …`, `grep -rnE '\.(units|tip_and_bookmark|read_chronicle|read_source_stats)\(' src`
- `grep -rnE 'Postgre|READ COMMITTED|…' src/previously/core`; `grep -nE 'execute|text\(|Connection' src/previously/cli.py src/previously/core -r`
- `grep -rnEil 'schatten|shadow|umschalt' docs/ .superpowers/`; `grep -nEi … docs/superpowers/plans/*.md`
- `grep -rnEil 'pip-audit|renovate' --exclude-dir=.venv --exclude-dir=.git .`
- `grep -rnEi 'anhalten|halt all|stop.*writ' …`; `grep -rnEi 'concurrent|thread' tests/*.py`; `grep -c add_parser src/previously/cli.py`; `grep -rn 'async ' src | wc -l`
- pyright-Probe: `.venv/bin/pyright --pythonpath .venv/bin/python <scratchpad>/probe/probe.py` → `2 errors` (beide auf `conn.execute` in `leak`, Zeile 13), keiner in `ok` oder `via_isinstance`
