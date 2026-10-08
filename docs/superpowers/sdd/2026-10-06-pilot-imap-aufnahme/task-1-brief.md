## Task 1: Inhaltsidentität und Kanalidentitäten in `RawEvent` und `append`

**Files:** `contract/types.py`, `core/identity.py` (neu), `core/errors.py`, `core/append.py`, `cli.py` (`_cmd_append`), `tests/test_identity.py` (neu), `tests/test_append.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/hash-format.md` (die neuen Namen in der Nutzlast).

**Interfaces — Produces:**
```python
# contract/types.py
@dataclass(frozen=True)
class ChannelIdentity:
    channel: str
    role: str
    address: str
    name: str | None = None
# RawEvent bekommt, hinter `blobs`:
    artifact_hash: bytes | None = None
    channel_identities: tuple[ChannelIdentity, ...] = ()

# core/identity.py
def artifact_hash_of(document: Mapping[str, object]) -> bytes: ...   # SHA-256 der kanonischen Form (core/canonical)

# core/errors.py
class ArtifactChanged(PreviouslyError):
    source: str; external_id: str; known: bytes; arrived: bytes
```

- [ ] **Step 1: Tests, die scheitern** — in `tests/test_append.py`, gegen echtes PostgreSQL:
  - `test_same_key_same_artifact_is_known` — zweimal dasselbe Event mit `artifact_hash=h`: dieselbe `id`, ein Event im Log.
  - `test_same_key_other_artifact_is_refused_and_nothing_is_written` — die Messung M1 des Prüfpunkts: zweites Event mit anderem `artifact_hash` → `ArtifactChanged` mit beiden Hashes; das ganze Bündel nicht geschrieben (ein zweites, neues Event im selben Aufruf fehlt danach).
  - `test_an_erased_event_stays_known` — Event tilgen (`redact_event`), dann derselbe Schlüssel mit anderem Hash: bekannt, keine Ausnahme, keine Wiederherstellung.
  - `test_an_event_without_artifact_hash_stays_known` — vorhandenes Event ohne den Namen, neues mit Hash: bekannt.
  - `test_artifact_hash_and_channel_identities_land_in_the_payload` — Hex unter `artifact_hash`, Liste von Objekten unter `channel_identities` in Reihenfolge; vom `payload_hash` gedeckt (eine Änderung von Hand ist ein Befund von `verify`).
  - `test_the_new_names_are_reserved` — eine Nutzlast mit `artifact_hash` oder `channel_identities` wird abgewiesen, wie heute `evidence`.
  - In `tests/test_identity.py`: dasselbe Dokument in anderer Schlüsselreihenfolge gibt denselben Hash; ein Zeichen anders gibt einen anderen.
  - In `tests/test_cli.py`: `append --text A` zweimal: bekannt; dann `--text B` mit demselben `--external-id`: Rückgabecode 2 und der Satz von `ArtifactChanged` aus den Global Constraints.
- [ ] **Step 2: rot laufen lassen.**
- [ ] **Step 3: Umsetzen.** Die Prüfung liegt in `append` dort, wo heute ein bekannter Schlüssel erkannt wird: `lookup` gibt die `id`, ein `read` der Zeile gibt die Nutzlast; ihr `artifact_hash` (Hex) gegen den ankommenden. Getilgt heißt `payload is None`. Die Tabelle aus Spec §2.2 ist die Regel. `_cmd_append` setzt `artifact_hash_of({"text": text, "attachments": sorted(adressen)})`.
- [ ] **Step 4: grün; Mutationen:** der Vergleich entfällt → `…_is_refused…` rot; Getilgtes wird verglichen → `…_erased_event_stays_known` rot; Kontrolle grün.
- [ ] **Step 5: Seiten.** `cli.md`: `append` weist einen bekannten Schlüssel mit anderem Inhalt ab (Satz aus den Global Constraints, `test_docs_references` hält ihn); `hash-format.md`: die zwei neuen Namen in der Nutzlast.
- [ ] **Step 6: Sechs Tore; Testblock des Tutorials, wenn die Zahl sich ändert; Commit.**

---

