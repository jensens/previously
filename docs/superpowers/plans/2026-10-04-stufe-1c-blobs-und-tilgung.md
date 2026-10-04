# Stufe 1c: Blobs und Tilgung — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Log bekommt einen Ort für Bytes und eine Tilgung, die ein Event, einzelne Einheiten oder einen Blob herausnimmt, ohne dass die Kette bricht — und `verify` kann danach einen berechtigten Grabstein von einer Fälschung unterscheiden.

**Architecture:** Ein zweites Hash-Format (v=2) neben dem ersten: jede Einheit trägt ihren eigenen Hash, und jeder Hash über Inhalt ein Salz, das mit dem Inhalt getilgt wird. Die Tilgung ist ein Event der Art `action` und entsteht in derselben Transaktion wie ihre Grabsteine; `verify` verlangt Anordnung und Vollzug. Blobs liegen unter dem Hash ihres Klartexts in einem S3-Speicher, im Format `age` versiegelt, bevor sie den Prozess verlassen; versiegelt wird in `core`, gespeichert in `storage`, und der Schlüssel steht am Objekt, nicht im Log.

**Tech Stack:** Python 3.14, SQLAlchemy Core, PostgreSQL 17 über testcontainers, pytest, ruff, pyright strict, import-linter, Sphinx/MyST, Vale. Neu: `boto3`, `pyrage`, für die Typprüfung `types-boto3-lite[s3]` und `pyrage-stubs`, und für die Tests das Image `rustfs/rustfs:1.0.1`.

**Spec:** `docs/superpowers/specs/2026-10-04-stufe-1c-blobs-und-tilgung.md` — der Plan argumentiert aus ihm; wer ausführt, liest beide.

**Anlagen:** `docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/` — was vor diesem Plan gemessen wurde, als Dateien, damit es sich wiederholen lässt:

| Datei | Was |
|---|---|
| `task-1-hash-v2.patch` | Aufgabe 1 als Patch: die vier v=2-Funktionen und ihre Tests. Angewendet, gefahren (40 Tests in `tests/test_hashing.py` grün, ruff und pyright ohne Befund), wieder herausgenommen. |
| `vector_v2.py` | der feste Vektor für v=2, nur mit `hashlib` aus von Hand geschriebenen kanonischen Zeichenketten gerechnet |
| `blob_spike.py`, `blob_spike_run.py` | der Blob-Weg in einer Datei, unter pyright strict ohne Befund und gegen RustFS gefahren |
| `measure_rustfs.py` | Speicher und Zeit des ganzen Wegs bei wählbarer Größe |
| `measure_race.py` | zwei Schreiber zugleich auf eine Adresse |
| `measure_guessing.py` | wie schnell sich eine kurze Einheit aus einem Hash ohne Salz erraten lässt |

## Was der Plan vorgibt und was nicht

Aus dem Anker-Plan steht die Lehre: Code im Plan, der nur überlegt und nie gefahren wurde, wird vom Umsetzer abgeschrieben, samt seinem Fehler. Darum trägt dieser Plan **Code nur dort, wo er gefahren wurde** — Aufgabe 1 und der Blob-Weg in Aufgabe 5, beide als Anlage. Überall sonst gibt er vor, was zwischen den Aufgaben hält und was ein Prüfer nachmessen kann: Signaturen, Schema, Wortlaute, die Tests mit Namen und Erwartung, und die Mutation, die jeden Test rot machen muss. Die Rümpfe schreibt der Umsetzer, Test zuerst.

Eine Signatur in einem **Interfaces**-Block ist verbindlich; weicht der Umsetzer ab, ist das ein Ruling im Protokoll, mit Grund, und der Controller trägt es in die späteren Aufgaben.

## Was der Plan am Spec entscheidet

1. **v=1 bleibt unangetastet, v=2 kommt als eigene Funktionen** (`payload_hash_v2`, `unit_digest`, `units_hash_v2`, `event_hash_v2`), nicht als Parameter `version`. So bleiben die v=1-Funktionen und ihr Vektor wörtlich stehen, und kein Aufrufer bekommt v=1, indem er ein Argument weglässt.
2. **Zwei Migrationen statt einer:** `0003` für das Hash-Format in Aufgabe 2, `0004` für `event_blob` in Aufgabe 6. Jede Aufgabe bringt das Schema mit, das sie benutzt, und kein Prüfer beurteilt eine Tabelle, deren Verwendung er nicht sieht.
3. **`RedactionStore[Conn]` ist ein drittes Protokoll.** `LogStore` kann weiterhin nichts ändern; was tilgen darf, ist ein Typ.
4. **`storage` deutet die Nutzlast nicht.** Welche Events Tilgungen sind, fragt kein SQL über `payload->>'action'`: `storage` liefert alle Events einer Art (`read_by_kind`), und `core/redaction.py` liest sie. Das kostet bei `redact`, `show` und `blob get` einen Lauf über alle Handlungen; in dieser Stufe sind das nur Tilgungen.
5. **Kein Salz neben einem Grabstein, per Datenbank.** Zwei `CHECK`-Bedingungen statt eines Befunds in `verify`; der Spec ist in §5.1 so nachgezogen.
6. **Keine `CHECK`-Bedingung auf `hash_version`.** Eine unbekannte Fassung ist ein Befund, den ein Test mit rohem SQL erzeugen kann; eine Bedingung machte ihn unerreichbar.
7. **`types-boto3-lite[s3]`**, nicht `types-boto3[s3]` (gemessen, Spec §8.3).
8. **`put` nimmt eine echte Datei** (`IO[bytes]`), weil das Hochladen von `boto3` genau das verlangt; `get` liefert Metadatum und Datenstrom aus einer Antwort. Das Metadatum heißt `key-id`.
9. **`verify --blobs` liest die Blobs nach dem Schnappschuss**, nicht in ihm: ein Lauf über alle Bytes hielte sonst eine Transaktion über Stunden offen. Ein Blob, der seither getilgt wurde, erscheint darum als fehlend; die Anleitung sagt es.
10. **`redact` sagt nicht vorher, was es tilgen wird**, nur danach, was es getilgt hat (Spec §4.1, nachgezogen): ohne Rückfrage ist eine Ankündigung ein Satz ohne Leser.
11. **Die zwei neuen Explanation-Seiten entstehen in den Aufgaben, die ihre Gründe tragen** (3 und 5), nicht erst am Ende: ein `{ref}` im Code braucht sein Ziel im selben Commit, sonst bricht `tests/test_docs_references.py`.

## Global Constraints

Aus `CLAUDE.md` und dem Spec, für jede Aufgabe verbindlich:

- **Einrichtung des Worktrees:** `uv sync --locked --all-extras`.
- **Alle sechs Tore**, namentlich, je einzeln gefahren, mit ungekürzter Schlusszeile im Bericht. Den Block kopieren, nicht aus dem Gedächtnis aufzählen:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- **Englisch** in `src/`, `tests/`, `migrations/`, `docs/` außer `docs/superpowers/`, `README.md`, `DEPENDENCIES.md`, Wurzelkonfiguration. Deutsch nur in Spec, Plan, Landkarte und Ausführungsprotokoll.
- **Trailer `Assisted-By: Claude <Modell> <noreply@anthropic.com>`** mit dem Modell, das die Arbeit getan hat. Niemals `Co-Authored-By:`, niemals „Generated with".
- **Kein `# type: ignore`**, pyright strict; `cast` ist das Mittel. **Kein Mock** für Zeit, Datenbank, Speicher oder Zufall: Tests gegen echtes PostgreSQL (`db`) und, ab Aufgabe 5, gegen einen echten S3-Server (`blob_store`). **Keine neue Suppression**; die Liste in `CLAUDE.md` steht bei fünf.
- **Ein Kommentar ist eine Behauptung.** Jede Zahl in Kommentar, Docstring oder Seite wird am Baum gemessen, nicht aus diesem Plan übernommen. Das gilt für die Testzahlen hier — sie sind Vorhersagen — und für jede Messung, die eine Seite zitiert: wer sie zitiert, fährt das Skript aus den Anlagen selbst und nennt seine Zahl und sein Datum.
- **Was durch diese Stufe falsch wird, steht unten in jeder Aufgabe** unter *Sätze, die nicht mehr stimmen*. Die Liste ist ein Anfang, kein Ende: wer eine Datei anfasst, liest ihre Kommentare gegen den neuen Stand.
- **Eine Zusage braucht einen Test, von dem gemessen ist, dass er bricht** — mit einer Kontrolle daneben, die gemessen grün bleibt. Die Mutationen stehen in den Aufgaben; Ergebnis mit Ausgabe in den Bericht.
- **Mutationen im Baum sind erlaubt** (Betreuer, 2026-10-04): eine Zeile ändern, die deckenden Tests fahren, die Datei zurücknehmen. Verweigert das Berechtigungssystem es einem Umsetzer, sucht er keinen anderen Weg, sondern meldet es, und der Controller misst.
- **Code zitiert Seiten, nie einen Paragraphen dieses Specs.** Ein Grund steht als `` {ref}`hash-version-2` ``, `` {ref}`erasure` ``, `` {ref}`blobs` `` oder ein bestehendes Label im Kommentar. Kein `§`. In Programmausgabe steht kein Zitat.
- **Ein Label je Plan nennt seinen Plan:** `ruling X of the 2026-10-04 stage 1c plan`, `review focus N of the 2026-10-04 stage 1c plan` — und der Grund steht im Satz daneben.
- **Doku im selben Zweig**, nach `plone-doc-style:author` (unter genau diesem Namen aufrufen): ein Quadrant je Seite, ein Satz pro Zeile, Überschriften in Satzschreibung, amerikanisches Englisch, höchstens zwei Admonitions je Seite.
- **Getippte Ausgabe ist eine Messung.** Der Testlauf im Tutorial wird am Ende **jeder** Aufgabe aus einem echten `uv run pytest`-Lauf getippt, ohne die `rootdir:`-Zeile; `tests/test_docs_typed_output.py` hält `N passed` gegen den Baum.
- **Stagen namentlich**, nie `git add -A`: vorher `git status --short`, nur die eigenen Dateien; alles andere melden.
- **Kein Geheimnis in einer Ausgabe.** Weder das Geheimnis des Speichers noch eine Identität erscheint in einer Meldung, einem Befund oder einem `repr`. Eine Fehlermeldung nennt Endpunkt und Bucket, nie Zugangsdaten.
- **Testdaten sind erfunden.** Das Repository ist öffentlich.
- **Betrieb mitdenken:** Anleitungen zeigen Kommandos, die in kup6s und auf einem Host mit `docker-compose` gleich aussehen. Nichts Hosting-Spezifisches wird gebaut.

**Vertragliche Wortlaute** — exakt so, weil Tests und die Reference sie zitieren. `<hex>` ist der volle SHA-256 in 64 Hex-Zeichen, klein.

| Wo | Text |
|---|---|
| Befund | `unit <seq> does not match its digest` |
| Befund | `hash_version <n> is not known` |
| Befund | `payload is erased without a redaction` |
| Befund | `unit <seq> is erased without a redaction` |
| Befund | `redaction of event <id> is not carried out` |
| Befund | `redaction of unit <seq> of event <id> is not carried out` |
| Befund | `redaction names a target that does not exist` |
| Befund | `units are erased in part, which version 1 cannot attest` |
| Befund | `action has no valid form` |
| Befund | `blob register does not match the payload` |
| Befund | `blob <hex> is missing` |
| Befund | `blob <hex> does not match its address` |
| Befund | `blob <hex> cannot be opened` |
| Befund | `blob <hex> is erased and still present` |
| `redact`, `stdout` | `redacted by event <id>` |
| `redact`, `stdout` | `already redacted by event <id>` |
| `redact`, `stderr` | `unit <seq> was already erased` |
| `redact`, `stderr` | `blob <hex> stays in the store: event <ids> still uses it` (`<ids>` mit Komma und Leerzeichen getrennt; ab zwei Events `events … still use it`) |
| `redact`, Fehler | `the redaction is recorded as event <id>, but it is not finished: <was aussteht>; run the same command again` |
| `redact`, Weigerung | `there is no event <id>` |
| `redact`, Weigerung | `event <id> is a redaction, and a redaction cannot be redacted` |
| `redact`, Weigerung | ``event <id> was written in hash format 1, which attests its units only together: use `previously redact event` `` |
| `redact`, Weigerung | `event <id> has no unit <seq>` |
| `redact`, Weigerung | `no event uses blob <hex>` |
| `redact`, Weigerung | `--reason must not be empty` |
| `blob get`, `stdout` | `wrote <n> bytes to <file>` |
| `blob get`, `stderr`, Rückgabecode 1 | `blob <hex> is erased (event <id>)` |
| `blob get`, `stderr`, Rückgabecode 1 | `no event uses blob <hex>` |
| `blob get`, Fehler | `blob <hex> does not match its address; nothing was written` |
| `blob get`, Fehler | `blob <hex> cannot be opened: <Grund>` |
| `blob get`, Fehler | `blob <hex> is not in the store` |
| `append --attach`, Eingabefehler | `cannot read the attachment <Name>: <Grund>` |
| `append`, Eingabefehler | `payload already carries the key 'blobs' — it is reserved for the attachments` |
| Eingabefehler | `<hex> is not a blob address: 64 hexadecimal characters, lower case` |
| Eingabefehler | `<VARIABLE> is not set` |
| `show`, Nutzlast | `payload=<erased by event <id>>`; ohne Anordnung weiter `payload=<erased>` |
| `show`, Einheit | `  ¶<seq> <erased by event <id>>`; ohne Anordnung `  ¶<seq> <erased>` |
| `show`, Blob | `  blob <hex> <size> <media_type> <filename oder ->`, bei getilgter Referenz gefolgt von ` <erased by event <id>>` |
| `verify --blobs`, Zusatz | `, 1 blob matches` / `, N blobs match` — am Ende der Erfolgszeile |

**Umgebungsvariablen:** `PREVIOUSLY_BLOB_ENDPOINT`, `PREVIOUSLY_BLOB_REGION`, `PREVIOUSLY_BLOB_BUCKET`, `PREVIOUSLY_BLOB_ACCESS_KEY`, `PREVIOUSLY_BLOB_SECRET_KEY`, `PREVIOUSLY_BLOB_RECIPIENT`, `PREVIOUSLY_BLOB_IDENTITIES`.

## Review Focus

Eingaben, die der Spec impliziert und die keine seiner Zusicherungen von selbst prüft — je mit der Aufgabe, die den Test bekommt:

1. **`--attach` auf etwas, das keine lesbare Datei ist:** fehlt, ist ein Verzeichnis. Erwartet: Rückgabecode 2, ein Satz, **kein Event angefügt**. → Aufgabe 6.
2. **Eine leere Datei als Anhang.** Null Bytes haben einen Hash und lassen sich versiegeln. Erwartet: geht durch, hin und zurück. → Aufgabe 5.
3. **Derselbe Inhalt zweimal an einem Event** — zwei Anhänge einer Mail mit gleichem Inhalt und verschiedenem Namen. Erwartet: zwei Referenzen in der Nutzlast, **eine** Zeile im Register, kein Verstoß gegen den Primärschlüssel. → Aufgabe 6.
4. **`redact units` mit einer `seq` doppelt, in falscher Reihenfolge, oder einer, die es nicht gibt.** Erwartet: doppelt und ungeordnet wird geordnet und einmal getilgt; eine fehlende ist eine Weigerung, und nichts ist geschrieben. → Aufgabe 3.
5. **Der Speicher antwortet nicht, oder der Bucket fehlt, oder das Geheimnis ist falsch.** Erwartet: Rückgabecode 2, ein Satz mit Endpunkt und Bucket, kein Geheimnis, und bei `append --attach` kein Event. → Aufgaben 5 und 6.
6. **Eine Blob-Adresse in Großbuchstaben oder mit 63 Zeichen.** Erwartet: Eingabefehler, bevor irgendetwas gefragt wird. → Aufgabe 6.
7. **`redact event` auf ein Event, dessen Nutzlast schon fehlt, ohne dass eine Tilgung es angeordnet hat.** Das ist eine Fälschung oder ein Unfall. Erwartet: die Tilgung wird geschrieben und tilgt, was noch steht; danach meldet `verify` nichts mehr. Das ist gewollt und steht in der Explanation: das Tilgungs-Event trägt ein späteres Datum als der Grabstein, den es deckt, und sagt das mit seiner Begründung. → Aufgabe 3.
8. **Eine Tilgung, während ein anderer anfügt.** Erwartet: eine der beiden Transaktionen verliert die Kettenposition und wiederholt; am Ende stehen beide Events, und die Kette hält. → Aufgabe 3.

---

## Dateistruktur

| Datei | Verantwortung | Aufgabe |
|---|---|---|
| `src/previously/core/hashing.py` | v=2 neben v=1 | 1 |
| `docs/reference/hash-format.md` | die vier Formen von v=2, der zweite Vektor | 1 |
| `docs/explanation/hash-chain.md` | Abschnitt `(hash-version-2)=`; der Grabstein-Abschnitt in 3 | 1, 2, 3 |
| `src/previously/contract/rows.py` | `EventRow` mit Fassung und Salz, `UnitRow` mit Hash, Salz und Inhalt, der fehlen darf | 2 |
| `src/previously/storage/schema.py`, `migrations/versions/0003_hash_version_2.py` | die Spalten und zwei Bedingungen | 2 |
| `src/previously/core/chain.py` | **neu.** Was jeder Schreibweg an der Kette tut: vorbereiten, einhängen | 2 |
| `src/previously/core/append.py`, `src/previously/core/verify.py` | schreiben v=2, prüfen nach Fassung | 2 |
| `src/previously/contract/store.py` | `RedactionStore`; `read_by_kind`; später `blobs_by_event`, `delete_chronicle` | 3, 4, 6 |
| `src/previously/core/redaction.py` | **neu.** Form, Lesen und Verzeichnis der Tilgungen; die Regel für Blobs. Rein. | 3, 7 |
| `src/previously/core/redact.py` | **neu.** Der Ablauf | 3, 7 |
| `docs/explanation/erasure.md` | **neu.** Label `erasure` | 3, 7, 8 |
| `src/previously/core/projection/chronicle.py` | folgt der Tilgung, Version 2 | 4 |
| `src/previously/contract/blobs.py` | **neu.** `BlobStore`, `StoredBlob`, `KeyProvider`, die Byte-Protokolle | 5 |
| `src/previously/core/sealing.py`, `src/previously/core/blob.py` | **neu.** Versiegeln und öffnen; speichern und holen | 5 |
| `src/previously/storage/s3.py`, `src/previously/storage/keys.py` | **neu.** Der Adapter; Identitäten aus einem Verzeichnis | 5 |
| `docs/explanation/blobs.md` | **neu.** Label `blobs` | 5, 7, 8 |
| `.importlinter`, `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md` | zwei Verträge, vier Abhängigkeiten | 5 |
| `migrations/versions/0004_event_blob.py` | das Register | 6 |
| `src/previously/cli.py` | `redact` (3, 4, 7), `append --attach`, `blob get` (6), `verify --blobs` (7), `show` (3, 6, 7) | 3, 4, 6, 7 |
| `docs/reference/cli.md`, `configuration.md`, `database-schema.md` | die Tatsachen, je in der Aufgabe, die sie ändert | 2, 3, 6, 7 |
| `docs/how-to/*.md`, `README.md`, `docs/tutorials/record-your-first-event.md` | Anleitungen, Sitzung neu getippt | 8 (der Testlauf-Block in jeder) |
| `docs/superpowers/landkarte.md`, der Spec, `docs/explanation/design-records.md` | Landkarte nachgezogen, Spec friert ein | 8 |

---

## Task 1: Das Hash-Format v=2

Das Format ist das Eine in dieser Stufe, das sich nach dem ersten echten Event nie mehr ändern lässt. Darum ist es vorgerechnet: der Vektor stammt aus `vector_v2.py`, mit `hashlib` allein, und die Funktionen aus dem Patch treffen ihn. Die Aufgabe des Umsetzers ist, das **nachzumessen**, nicht abzuschreiben — und die zwei Seiten zu schreiben, die sagen, warum es dieses Format gibt.

**Files:**
- Modify: `src/previously/core/hashing.py`, `tests/test_hashing.py`, `docs/reference/hash-format.md`, `docs/explanation/hash-chain.md`, `docs/explanation/canonicalization.md`, `docs/tutorials/record-your-first-event.md` (nur der Testlauf-Block)

**Interfaces:**
- Consumes: `canonical` aus `previously.core.canonical`; `iso_utc`, `HASH_DOMAIN`, `UNITS_DOMAIN` in `core/hashing.py`.
- Produces, alle in `previously.core.hashing`:
  - `HASH_VERSION_1 = 1`, `HASH_VERSION_2 = 2`, `HASH_VERSION = HASH_VERSION_2` (die Fassung, die geschrieben wird).
  - `PAYLOAD_DOMAIN = "previously/payload"`, `UNIT_DOMAIN = "previously/unit"`, `SALT_BYTES = 32`.
  - `new_salt() -> bytes`
  - `payload_hash_v2(payload: Mapping[str, object], salt: bytes) -> bytes`
  - `unit_digest(*, seq: int, content: str, start_ms: int | None, end_ms: int | None, speaker: str | None, salt: bytes) -> bytes`
  - `units_hash_v2(digests: Mapping[int, bytes]) -> bytes` — Schlüssel ist `seq`, sortiert wird in der Funktion.
  - `event_hash_v2(*, event_id, kind, recorded_at, occurred_at, prev_hash, payload_digest, units_digest, source, external_id) -> bytes` — die Argumente von `event_hash`.
  - unverändert: `payload_hash`, `units_hash`, `event_hash`, `HashableUnit`, `iso_utc`.
  - das Label `(hash-version-2)=` auf `docs/explanation/hash-chain.md`.

- [ ] **Schritt 1: Einrichtung und Ausgangszahl**

Run: `uv sync --locked --all-extras`
Run: `uv run pytest --collect-only -q -p no:randomly | tail -1`
Erwartet: `272 tests collected`. Weicht die Zahl ab, zähl nach, bevor du weitermachst — alle Zahlen dieses Plans rechnen von 272.

- [ ] **Schritt 2: Den Vektor selbst rechnen**

Run: `uv run python docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/vector_v2.py`

Lies das Skript, bevor du seiner Ausgabe traust: es benutzt keinen Projektcode. Prüfe an den gedruckten Zeichenketten, dass die Schlüssel sortiert sind, kein Leerraum steht und `ä` als `ä` steht — so, wie `JCS_UNITS` in `tests/test_hashing.py` es für v=1 zeigt. Die sieben Hex-Werte, die es druckt, sind die, die der Patch als Literale trägt. Stimmt einer nicht überein, halte an und melde es.

- [ ] **Schritt 3: Nur die Tests anwenden, und sehen, dass sie scheitern**

```bash
git apply --include='tests/*' docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/task-1-hash-v2.patch
uv run pytest tests/test_hashing.py -q -p no:randomly
```

Erwartet: ein `ImportError` beim Sammeln (`cannot import name 'event_hash_v2'`).

- [ ] **Schritt 4: Die Funktionen anwenden**

```bash
git apply --include='src/*' docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/task-1-hash-v2.patch
uv run pytest tests/test_hashing.py -q -p no:randomly
```

Erwartet: `40 passed`. Die drei Tests des v=1-Vektors sind unter ihnen und unverändert.

Lies den Diff an `hashing.py`. In den zwei v=1-Funktionen hat sich genau ein Wort geändert: `"v": HASH_VERSION` heißt `"v": HASH_VERSION_1`. Alles andere daran steht wie zuvor.

- [ ] **Schritt 5: Der Kommentar über dem v=1-Vektor**

In `tests/test_hashing.py` sagt der Kommentar über dem ersten Vektor: „Should the hash range change **deliberately**, `HASH_VERSION` belongs raised and this vector recomputed; both then come to notice together." Das stimmt nicht mehr und war die Anleitung, die diese Aufgabe gerade **nicht** befolgt: ein neues Format bekommt eine neue Fassung und einen **zweiten** Vektor, und der erste bleibt, solange es Events seiner Fassung geben kann. Fass den Satz neu. **Kein Literal und keine Eingabe des ersten Vektors ändert sich.**

- [ ] **Schritt 6: Mutationen**

Je eine Zeile ändern, `uv run pytest tests/test_hashing.py -q -p no:randomly` fahren, zurücknehmen. Ausgabe in den Bericht.

| Mutation | muss rot werden | muss grün bleiben |
|---|---|---|
| `unit_digest`: die Zeile `"salt": salt.hex(),` entfernen | `test_v2_vector_unit_digests`, `test_the_salt_alone_changes_a_digest` | die drei `test_vector_*` von v=1 |
| `units_hash_v2`: `sorted(digests)` → `digests` | `test_units_hash_v2_sorts_by_seq_itself` | `test_v2_vector_units_hash` (seine Eingabe ist schon geordnet) |
| `payload_hash_v2`: `PAYLOAD_DOMAIN` → `UNITS_DOMAIN` | `test_v2_vector_payload_hash` | `test_vector_payload_hash` |
| `event_hash_v2`: `HASH_VERSION_2` → `HASH_VERSION_1` | `test_v2_vector_event_hash`, `test_version_1_and_version_2_never_agree` | `test_vector_event_hash` |
| `event_hash` (v=1): `HASH_VERSION_1` → `HASH_VERSION` | `test_vector_event_hash` | `test_v2_vector_event_hash` |

Die letzte Zeile ist die Kontrolle, dass der v=1-Vektor wirklich v=1 hält und nicht mitgewandert ist.

- [ ] **Schritt 7: `docs/reference/hash-format.md`**

Vorher `plone-doc-style:author` aufrufen. Reference: beschreiben, nichts begründen.

- Die Seite führt heute drei Formen (Nutzlast, Einheiten, Event) mit je einer Tabelle der Felder. Sie bekommt für v=2 dieselbe Darstellung für **vier** Formen: Nutzlast, einzelne Einheit, Einheiten, Event. Je Form die Felder, ihr Bereich (`domain`), und was der Wert ist.
- Welche Fassung geschrieben wird (`HASH_VERSION`), dass v=1 geprüft bleibt, und dass eine Zeile ihre Fassung in `event.hash_version` nennt — die Spalte kommt in Aufgabe 2, die Seite sagt es als Tatsache dieser Stufe erst, wenn sie steht: **in dieser Aufgabe nur das Format**, der Satz zur Spalte in Aufgabe 2.
- Der zweite Vektor: Eingaben, Salze, die fünf Hex-Werte, und wo er im Baum steht.
- Der Satz bei Zeile 85 („The one exception is a deliberate change to the hash range, which raises `HASH_VERSION` along with the vector") ist die Seitenfassung des Kommentars aus Schritt 5 und genauso falsch. Neu fassen.
- Die Tabellenzeilen `` `1` (`HASH_VERSION`) `` nennen einen Namen, der jetzt 2 ist: `HASH_VERSION_1`.

- [ ] **Schritt 8: `docs/explanation/hash-chain.md` und `canonicalization.md`**

Explanation: warum es so ist.

Neuer Abschnitt auf `hash-chain.md`, Label `(hash-version-2)=`, Überschrift in Satzschreibung, etwa „Version 2: a digest per unit, and a salt". Was er sagen muss:

- **Warum ein Hash je Einheit.** In v=1 steht der Inhalt aller Einheiten in einem Hash; fehlt einer, lässt sich der Hash nicht mehr rechnen, und die übrigen Einheiten wären lesbar, aber nicht bezeugt. In v=2 behält die getilgte Einheit ihren Hash, und der Hash über die Hashes bleibt rechenbar.
- **Warum ein Salz.** Was nach einer Tilgung stehen bleibt, ist ein Hash, und ein Hash über kurzen Inhalt lässt sich durchprobieren. **Miss es selbst**: `uv run python docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/measure_guessing.py`, und nenne deine Zahl und dein Datum, nicht die aus dem Skriptkopf. Das Salz geht in den Hash ein und wird mit dem Inhalt getilgt; solange der Inhalt steht, hat die Prüfung es.
- **Warum es sich nicht nachrüsten lässt**, und warum v=1 darum für immer geprüft bleibt, statt umgerechnet zu werden: einen Hash neu zu rechnen heißt die Kette neu zu schreiben.
- **Was v=1 kostet:** ein Event dieser Fassung lässt sich nur ganz tilgen, und seine Hashes bleiben erratbar.
- **Was das Salz nicht leistet:** die Tilgung selbst gibt es noch nicht. Der Abschnitt sagt, wofür das Format gebaut ist, und verspricht nichts, was der Baum an diesem Commit nicht hält — der Verweis auf die Seite zur Tilgung kommt in Aufgabe 3.

Dazu zwei Sätze, die falsch werden:

- `hash-chain.md`, bei Zeile 250: „`HASH_VERSION` stays 1 for the same kind of reason: version 1 was never written to a production database, so version 1 is still being defined here, not departed from." Der Grund stimmte für die Korrekturen der Stufe 1a; jetzt gibt es eine zweite Fassung. Neu fassen, ohne die Geschichte zu verlieren: warum damals in v=1 hinein korrigiert wurde, und warum jetzt nicht.
- `canonicalization.md`, Zeile 114: derselbe Gedanke wie in Schritt 5.

- [ ] **Schritt 9: Der Testlauf im Tutorial**

Run: `uv run pytest --collect-only -q -p no:randomly | tail -1`
Erwartet: `288 tests collected` (272 + 16: elf einfache Tests und einer mit fünf Fällen). Den Block in `docs/tutorials/record-your-first-event.md` aus einem echten `uv run pytest`-Lauf neu tippen.

- [ ] **Schritt 10: Alle sechs Tore, Commit**

```bash
git status --short
git add src/previously/core/hashing.py tests/test_hashing.py docs/reference/hash-format.md \
        docs/explanation/hash-chain.md docs/explanation/canonicalization.md \
        docs/tutorials/record-your-first-event.md
```

Commit-Botschaft, englisch: was v=2 ist (ein Hash je Einheit, ein Salz), dass v=1 und sein Vektor unangetastet bleiben, dass der zweite Vektor unabhängig von den Funktionen gerechnet wurde, und dass noch nichts v=2 schreibt.

---

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
