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

