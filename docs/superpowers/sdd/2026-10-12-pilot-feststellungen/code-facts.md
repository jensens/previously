# Code facts for the assertion plan (measured 2026-10-12, worktree `feststellungen`, HEAD 915e48a)

Paths are relative to `src/previously/` unless they start with `tests/`, `docs/`, or are root files.
"Absent" means grep found nothing.
The spec is `docs/superpowers/specs/2026-10-12-pilot-feststellungen.md` (German, 479 lines).

## 1. Writing events

### `core/append.py` (observations)
- `_KIND = "observation"` (append.py:75), a module constant used once, in `_prepare` -> `prepare(kind=_KIND, ...)` (append.py:432-442).
  Nothing in `RawEvent` can change the kind; the comment at :69-74 says assertions are a later stage.
- Public: `MAX_RETRIES = 8` (:60), `MAX_BATCH = 500` (:65), `BACKOFF_BASIS = 0.005`, `BACKOFF_CAP = 0.2` (:91-92), `def backoff_delay(attempt: int) -> float` (:103), `def check_units(units: Sequence[RawUnit]) -> None` (:205), `def known_id[Conn](storage: LogStore[Conn], conn: Conn, event: RawEvent) -> int | None` (:334), and
```python
def append[Conn](
    storage: LogStore[Conn],
    events: Sequence[RawEvent],
    *,
    recorded_at: datetime,
) -> list[int]:                                   # append.py:458
```
  Private: `_prepare(events) -> list[tuple[RawEvent, Prepared]]` (:352), `_check_artifact`, `_identities`, `_check_identity`.
- Flow of `append`: refuse `> MAX_BATCH` (`BatchTooLarge`); `iso_utc(recorded_at)` (naive -> error); `_prepare` once (checks per event: `iso_utc(occurred_at)`, `_check_identity("source"/"external_id")`, duplicate key inside batch -> `InvalidPayload`, `check_units`, reserved key `evidence` -> `InvalidPayload`, payload = `{**event.payload, "evidence": ..., **_identities(event)}`, then `chain.prepare` which draws salts and digests once, so retries only re-run `chain.link`).
  Then up to `MAX_RETRIES` attempts of: `with storage.begin() as conn:` -> `tip = storage.tip(conn)` -> per event `known_id` (idempotent skip, returns the existing id; `ArtifactChanged` rolls the batch back) -> `chain.link(ready, event_id=next_id, prev_hash=prev, recorded_at=recorded_at)` -> `storage.insert_event(conn, row, units, ready.key, ready.blobs)` (append.py:458-500 approx; loop body in the file at "for attempt in range(MAX_RETRIES)").
- Source key / idempotency: `RawEvent.source` + `external_id` -> `key=(source, external_id)` -> `source_key` table via `insert_event(..., key, ...)`; `lookup(conn, source, external_id) -> int | None` before insert. Race: `SourceKeyTaken` (pragma no cover branch) re-reads `lookup` for the whole batch; all found -> return ids, else `continue`.
- Chain conflict: `except ChainPositionTaken: time.sleep(backoff_delay(attempt)); continue` (re-reads tip). After 8 attempts `raise ChainConflict(...)`.
- Event types: `contract/types.py` `RawEvent(source, external_id, occurred_at, evidence: Evidence, units: tuple[RawUnit,...], payload: Mapping = {}, blobs=(), artifact_hash: bytes|None=None, channel_identities=())` (:63-85); `RawUnit(seq, content, start_ms=None, end_ms=None, speaker=None)` (:21); `Evidence` = verbatim | recollection (:13).
- Payload limits (core/canonical.py:37-87): `KEY_PATTERN = ^[a-z][a-z0-9_]*$`, `MAX_SAFE_INT = 2**53-1`, no floats; dict/list/str/int/bool/None only. Enforced inside `chain.prepare` (canonical form), so every write path inherits it. `due` dates must therefore be strings.

### `core/chain.py` (shared by every write path)
- `def prepare(*, kind: str, occurred_at: datetime, payload: Mapping[str, object], units: Sequence[RawUnit], key: tuple[str, str] | None, blobs: Sequence[BlobRef] = ()) -> Prepared` (chain.py:185).
- `def link(prepared: Prepared, *, event_id: int, prev_hash: bytes | None, recorded_at: datetime) -> tuple[EventRow, list[UnitRow]]` (chain.py:268).
- `Prepared` frozen dataclass (:59): kind, occurred_at, payload, payload_salt, payload_digest, units, units_digest, key, blobs.

### `core/action.py` (actions)
- `_KIND = "action"` (action.py:65) is hard-coded; there is NO generic `kind` parameter and no generic append for `assertion`. Absent: any `kind="assertion"` write (grep: only `event_kind_check` in `storage/schema.py:53` and `migrations/versions/0001_log.py:54` allow the value; tests mention it in `tests/test_hashing.py:142` and `tests/test_storage.py:798`).
- Known actions (action.py:49-54): `REDACTION="redaction"`, `POLICY="policy"`, `MODEL_CALL="model_call"`, `MCP_ACCESS="mcp_access"`, `KNOWN_ACTIONS: frozenset[str]`. Outcomes `OK, DENIED, REFUSED, SCHEMA_INVALID, ERROR` / `OUTCOMES` (:58-63).
- Signatures:
```python
def write_action[Conn](log: LogStore[Conn], conn: Conn, payload: Mapping[str, object],
    units: Sequence[RawUnit], *, recorded_at: datetime) -> int                    # :68, tip read inside caller's txn
def write_action_at[Conn](log: LogStore[Conn], conn: Conn, tip: Tip | None, payload: Mapping[str, object],
    units: Sequence[RawUnit], *, recorded_at: datetime) -> int                    # :86, tip read earlier by caller
def retrying[Conn, T](log: LogStore[Conn], once: Callable[[Conn], T]) -> T         # :110
def append_action[Conn](log: LogStore[Conn], payload: Mapping[str, object],
    units: Sequence[RawUnit], *, recorded_at: datetime) -> int                    # :130
```
- `write_action_at` body (:99-107): `prepare(kind=_KIND, occurred_at=recorded_at, payload=payload, units=units, key=None)` -> `link(prepared, event_id=1 if tip is None else tip.id + 1, prev_hash=..., recorded_at=recorded_at)` -> `log.insert_event(conn, row, linked, None)` -> `row.id`. An action has `occurred_at == recorded_at`, no source key.
- `retrying` (:110-127): `for attempt in range(MAX_RETRIES): try: with log.begin() as conn: return once(conn) except ChainPositionTaken: time.sleep(backoff_delay(attempt))`; then `ChainConflict`. Reusable as is (generic over the callback).
- Payload forms are NOT checked in `write_action*`. Each writer checks its own: `policy.set_policy` (policy.py:379; reads tip, `refusal(...)` under the tip, `write_action_at`, wrapped in `retrying`; the model for "validate against state under a fixed tip"), `access.record_access` (access.py:129, builds `_payload(access)` and calls `append_action`), the gate via `redact.append_call` (redact.py:563). Forms are re-checked by `verify` (see 5).
- A second write path for `assertion` could reuse: `chain.prepare` / `chain.link`, `action.retrying`, `action.write_action_at` pattern (copy with `kind="assertion"`; `_KIND` is private so a new function or a `kind` parameter is needed), `iso_utc` early check, `ChainConflict`/`ChainPositionTaken` handling, `LogStore.tip/insert_event/begin`. Idempotency by source key is observation-only (`insert_event(..., key, ...)`); the spec (§6.1, §9) wants idempotency via the handle id carried in the payload, so a lookup by payload would be new (see `LogStore.actions` for the only payload-filtered query).

## 2. `LogStore` protocol (contract/store.py:77-115)
```python
class LogStore[Conn](Protocol):
    def begin(self) -> AbstractContextManager[Conn]: ...
    def snapshot(self) -> AbstractContextManager[Conn]: ...
    def tip(self, conn: Conn) -> Tip | None: ...
    def lookup(self, conn: Conn, source: str, external_id: str) -> int | None: ...
    def insert_event(self, conn: Conn, row: EventRow, units: Sequence[UnitRow],
        key: tuple[str, str] | None, blobs: Sequence[bytes] = ()) -> None: ...
    def read(self, conn: Conn, from_id: int, limit: int) -> Iterator[EventRow]: ...
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
    def read_by_kind(self, conn: Conn, kind: str) -> Iterator[EventRow]: ...
    def actions(self, conn: Conn, action: str) -> Iterator[EventRow]: ...
    def blobs_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[bytes]]: ...
    def events_by_blob(self, conn: Conn, sha256: bytes) -> list[int]: ...
    def blob_references(self, conn: Conn) -> Iterator[tuple[bytes, int]]: ...
    def observations(self, conn: Conn, *, since: datetime | None, until: datetime | None,
        source: str | None, after: tuple[datetime, int] | None, limit: int) -> Iterator[EventRow]: ...
```
- 15 methods declared. Read by kind: `read_by_kind(conn, kind)` (all events of that kind, chain order, server-side cursor; postgres.py:424). Filter by action name: `actions(conn, action)` (`WHERE kind='action' AND payload->>'action' = :action`, chain order; postgres.py:442), added 2026-10-11 for the policy read. Both are used for `kind="assertion"`-style needs: `read_by_kind(conn, "assertion")` already works (tests/test_storage.py:798 reads it empty). There is no payload-filtered query for assertions (e.g. by `payload->>'assertion'` or `subject`); it would be a new protocol method like `actions`.
- The docstring of store.py:6-42 contains a counted method list (14 called by core, 15 declared) with a shell command; adding a method changes those figures (CLAUDE.md "A comment is a claim").
- `RedactionStore` (:118): `lock_event(conn, event_id) -> EventRow | None`, `erase_payload(conn, event_id) -> None`, `erase_units(conn, event_id, seqs: Sequence[int]) -> None`.
- `ProjectionStore` (:139) and `WatermarkStore` (:181), see 3.
- Rows (contract/rows.py):
```python
@dataclass(frozen=True)
class EventRow:                                   # rows.py:29-46
    id: int; kind: str; recorded_at: datetime; occurred_at: datetime
    prev_hash: bytes | None; hash: bytes; payload_hash: bytes; units_hash: bytes
    payload: Mapping[str, object] | None          # None = tombstone
    hash_version: int = 1; payload_salt: bytes | None = None
@dataclass(frozen=True)
class UnitRow:                                    # :50-61
    event_id: int; seq: int; content: str | None  # None = tombstone
    start_ms: int | None = None; end_ms: int | None = None; speaker: str | None = None
    digest: bytes | None = None; salt: bytes | None = None
```
  Also `Tip(id, hash)` (:22), `ProjectionState(name, up_to_id, version, built_at)` (:65), `TipAndBookmark(tip_id, up_to_id)` (:75), `ChronicleRow(event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker=None, start_ms=None, end_ms=None)` (:91), `SourceStatsRow(source, events, units, first_seen, last_seen, last_event_id)` (:106).
- Schema CHECK: `event_kind_check`: `kind IN ('observation','assertion','action')` (storage/schema.py:53); `event_payload_object_check` at schema.py:94 (payload must be an object or NULL).

## 3. Projections
- Interface (core/projection/worker.py:199-217):
```python
class Projection(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> int: ...
    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None: ...
@dataclass(frozen=True)
class Batch:   # :188
    events: tuple[EventRow, ...]; units: Mapping[int, Sequence[UnitRow]]; keys: Mapping[int, tuple[str, str]]
@dataclass(frozen=True)
class Outcome: name: str; version: int; rebuilt_from: int | None; events: int; up_to_id: int   # :221
def catch_up[Conn](log: LogStore[Conn], store: ProjectionStore[Conn], projection: Projection, *, batch_size: int = 500) -> Outcome   # :235
```
- `catch_up`: txn 1 `lock_projection_state(name)`; if no row or `state.version != projection.version` -> `truncate_projection(name)` + `set_projection_state(ProjectionState(name, 0, version, now))` (rebuild; `rebuilt_from` = 0 or old version). Then loop per batch in its own txn: lock state again (version changed meanwhile -> `ProjectionRebuilt`), `log.tip`, `log.read(from_id=up_to_id+1, limit=batch_size)`, gap check (`ProjectionGap`), build `Batch` (`units_by_event`, `source_keys`), `projection.write(store, conn, batch)`, `set_projection_state(up_to_id=last id)`. Rebuild = version bump; there is no separate rebuild function. A projection sees every event kind (the batch holds all kinds); `derive` filters.
- `p_chronicle` (core/projection/chronicle.py): `@dataclass(frozen=True) class ChronicleProjection: name: str = "chronicle"; version: int = 3` with `write(self, store, conn, batch)` (:147) = `store.insert_chronicle(conn, derive(batch))` then `for event_id, seqs in erasures(batch): store.delete_chronicle(conn, event_id, seqs)`. `derive(batch) -> list[ChronicleRow]` skips `event.kind != "observation"` (:68), one row per unit with content. `erasures(batch)` parses `kind == "action"` redactions via `redaction.parse` and returns `(event, None | units)`; ignores a redaction whose target `>= event.id`. Constant `CHRONICLE = ChronicleProjection()` (:161).
- `source_stats.py`: `SourceStatsProjection(name="source-stats", version=1)`, `SOURCE_STATS`; `merge`/`derive` pure; `write` reads `store.source_stats(conn, sources)` and `upsert_source_stats`. `derive` (:48) counts every event that has a source key, i.e. observations only in practice (actions and assertions carry no key).
- Registration: `core/projection/__init__.py:15` `PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)`; `__all__` at :17 exports `CHRONICLE, PROJECTIONS, SOURCE_STATS, Batch, Outcome, Projection, catch_up`.
- Running all: `cli.py:1337 _cmd_project`: `with _storage() as storage: for projection in PROJECTIONS: outcome = catch_up(storage, storage, projection); print(f"{outcome.name:<15} {_describe(outcome)}")`. Also `cli.py:1236 _catch_up_after(storage)` loops `PROJECTIONS` after a redaction and returns the "outstanding" sentence on `PreviouslyError | StorageError`; a rebuild is named on stderr. Output lines are pinned in `tests/test_cli.py` (e.g. :1293-1358, :1923, :2048: `"source-stats    up to date, up_to_id 0"`), so a new projection adds lines there. `cli.py:1409-1416 _cmd_stats` reads `storage.tip_and_bookmark(conn, SOURCE_STATS.name)`.
- `ProjectionStore` protocol methods (contract/store.py:139-178), all table-specific, no generic row API:
```python
def begin(self) -> AbstractContextManager[Conn]: ...
def lock_projection_state(self, conn: Conn, name: str) -> ProjectionState | None: ...
def set_projection_state(self, conn: Conn, state: ProjectionState) -> None: ...
def truncate_projection(self, conn: Conn, name: str) -> None: ...
def insert_chronicle(self, conn: Conn, rows: Sequence[ChronicleRow]) -> None: ...
def delete_chronicle(self, conn: Conn, event_id: int, seqs: Sequence[int] | None) -> None: ...
def source_stats(self, conn: Conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]: ...
def upsert_source_stats(self, conn: Conn, rows: Sequence[SourceStatsRow]) -> None: ...
```
- `PostgresStorage` (storage/postgres.py): `_PROJECTION_TABLES: ClassVar[dict[str, Table]] = {"chronicle": p_chronicle, "source-stats": p_source_stats}` (:705-708; `truncate_projection` raises `ValueError("unknown projection ...")` otherwise, :769-778); `lock_projection_state` :723, `set_projection_state` :751, `insert_chronicle` :780, `delete_chronicle` :803, `source_stats` :815, `upsert_source_stats` :832, `tip_and_bookmark(conn, name) -> TipAndBookmark` :907 (outside protocol), `read_chronicle(conn, *, since, until, limit)` :945, `read_source_stats(conn)` :979 (readers are outside the protocol; "core never reads a projection back"; the CLI and anything that reads a projection use `PostgresStorage` directly, and `mcp_server` reads only `LogStore`). `lock_event` comment (:670) says every projection row references `event` via FK, hence `FOR NO KEY UPDATE`.
- Schema (storage/schema.py:211-268):
```python
projection_state = Table("projection_state", metadata, Column("name", Text, primary_key=True),
    Column("up_to_id", BigInteger, nullable=False), Column("version", Integer, nullable=False),
    Column("built_at", TIMESTAMP(timezone=True), nullable=False))
p_chronicle = Table("p_chronicle", metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False), Column("seq", Integer, nullable=False),
    Column("content", Text, nullable=False), Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("kind", Text, nullable=False), Column("evidence", Text), Column("source", Text), Column("external_id", Text),
    Column("speaker", Text), Column("start_ms", Integer), Column("end_ms", Integer),
    PrimaryKeyConstraint("event_id", "seq"))
Index("p_chronicle_occurred_idx", p_chronicle.c.occurred_at, p_chronicle.c.event_id, p_chronicle.c.seq)
p_source_stats = Table("p_source_stats", metadata, Column("source", Text, primary_key=True), Column("events", BigInteger, nullable=False),
    Column("units", BigInteger, nullable=False), Column("first_seen", ...), Column("last_seen", ...),
    Column("last_event_id", BigInteger, ForeignKey("event.id"), nullable=False))
```
  Convention: prefix `p_`, FKs only onto `event`, none between projections.
- Migration `migrations/versions/0002_projections.py` (65 lines): docstring; `from alembic import op`, `import sqlalchemy as sa`; `revision = "0002_projections"`, `down_revision = "0001_log"`, `branch_labels = None`, `depends_on = None`; `def upgrade() -> None:` with `op.create_table("projection_state", ...)`, `op.create_table("p_chronicle", ...)`, `op.create_index("p_chronicle_occurred_idx", "p_chronicle", ["occurred_at", "event_id", "seq"])`, `op.create_table("p_source_stats", ...)`; `def downgrade() -> None:` drops in reverse order (indexes by `op.drop_index(name, table_name=...)`). Its docstring says projections are derivable and dropping loses no truth.
- Touchpoints for adding `p_obligation` / `p_decision`: `core/projection/obligation.py` + `decision.py` (new, `Projection` implementations, name+version) and `core/projection/__init__.py` (`PROJECTIONS`, `__all__`); `contract/rows.py` (row dataclasses); `contract/store.py` (`ProjectionStore` methods + docstring); `storage/schema.py` (Tables, Index); `storage/postgres.py` (imports at :42-43, `_PROJECTION_TABLES` at :705, implementations, read methods); migration `0006_...` (next id, see 12); `tests/test_schema.py:534-535` (pins the table set with `<=`, so extension is allowed, but update the docstring at :520), `tests/conftest.py:62` (`TRUNCATE_ALL` derived from `metadata`, automatic), `tests/test_cli.py` projection output lines (:1293-1358, 1923, 2048), `tests/test_projection_worker.py:83,91,259` (iterate `PROJECTIONS`); `docs/reference/database-schema.md`, `docs/explanation/projections.md`; `cli.py` `_cmd_project`/`_catch_up_after` need no change (loop over `PROJECTIONS`). The `previously stats` and `chronicle` commands use `PostgresStorage` read methods directly.
- Erasure interplay: a projection that wants to follow a redaction reads `redaction.parse` as chronicle does; or, being rebuilt from the log with tombstones in view (payload `None`), simply skips tombstoned events.

## 4. Erasure
- `core/redact.py` public: `Redacted` (:101: `redaction_id, written, skipped_units=(), obsolete_blobs=(), kept_blobs={}, payload_holds_wording=False, cascaded: tuple[int,...]=()`), 
```python
def redact_event[Conn](log: LogStore[Conn], eraser: RedactionStore[Conn], event_id: int, *, reason: str, recorded_at: datetime) -> Redacted   # :332
def redact_units[Conn](log, eraser, event_id: int, seqs: Sequence[int], *, reason: str, recorded_at) -> Redacted                              # :409
def redact_blob[Conn](log, eraser, sha256: str, *, reason: str, recorded_at) -> Redacted                                                      # :497
def append_call[Conn](log: LogStore[Conn], eraser: RedactionStore[Conn], payload: Mapping[str, object],
    units: Sequence[RawUnit], *, recorded_at: datetime) -> AppendedCall                                                                      # :563
```
  `PostgresStorage` is both `log` and `eraser` (the CLI passes `storage, storage`).
- `redact_event` `once(conn)` (:349-398): read register blobs; `_lock_round(log, eraser, conn, [event_id, *sharing], lambda entry: _entry_event(entry) == event_id)` locks the target and the `model_call`s that read it, ascending; `_target(rows[event_id], event_id)` refuses a missing event and a redaction (`RedactionRefused`); `index = read_index(log, conn)`; if not already covered: `write_action(log, conn, event_payload(event_id, blobs=registered, reason=reason), (), recorded_at=...)`; `eraser.erase_payload`, `eraser.erase_units(conn, event_id, _seqs(...))`; `cascaded = _cascade(log, eraser, conn, calls, trigger=redaction_id, recorded_at=recorded_at)`; return `Redacted`. Wrapped as `return retrying(log, once)` (:406): ONE transaction for order, tombstones and cascade; a lost chain position rolls everything back and restarts.
- The cascade to `model_call` (unit 3):
```python
def _calls[Conn](log: LogStore[Conn], conn: Conn, wanted: Callable[[Mapping[str, object]], bool]) -> list[int]   # redact.py:230
    # read_by_kind(conn, "action") filtered in Python: payload.action == MODEL_CALL and _reads(payload, wanted)
def _cascade[Conn](log: LogStore[Conn], eraser: RedactionStore[Conn], conn: Conn, calls: Iterable[int],
    *, trigger: int, recorded_at: datetime) -> tuple[int, ...]                                                       # :246
    # per call with live units: write_action(units_payload(call_id, live, reason=f"cascade of redaction {trigger}")) + eraser.erase_units
def _lock_round[Conn](log, eraser, conn, targets: Iterable[int], wanted) -> tuple[dict[int, EventRow | None], list[int]]   # :173
def _lock_ascending[Conn](eraser, conn, event_ids: Iterable[int]) -> dict[int, EventRow | None]                      # :164
```
  `wanted` examples: for `redact_event` `_entry_event(entry) == event_id`; `redact_units` and `redact_blob` have their own predicates (read at :430 and :520). `_reads(payload, wanted)` iterates `payload["inputs"]` (a list of `{"event": int, "units": [...], "blobs": [...]}` entries). The cascade only erases the units of the call (answer), not its payload. The call is called twice (before and after the lock) to catch a call written while waiting. Cascade is called from the three `redact_*` functions at :388, :485, :540, and from `append_call` :601 (the other side of the race).
- For assertions the spec (§8) wants the same shape: find assertions whose `sources` name the erased event (or the erased units / the whole event), lock them in the same ascending round, erase payload (and units, if any) in the same transaction. Note `_target` only refuses redactions, and `lock_event` uses `FOR NO KEY UPDATE`. Absent: any assertion handling in `redact.py`, `redaction.py`, `verify.py`.
- `core/redaction.py`: payload forms (`_PAYLOAD_KEYS = {"action","scope","target","reason"}` :48), `event_payload(event_id, *, blobs, reason)`, `units_payload(event_id, seqs, *, reason)`, `blob_payload(sha256, event_ids, *, reason)` (:74-103), `action_name(payload) -> str` (:106, raises `MalformedAction`), `parse(event_id, payload) -> Redaction` (:139), `Redaction` (:52; id, scope `"event"|"units"|"blob"`, reason, event, units, blobs, blob, events), `RedactionIndex` (:184: `add`, `of_event(event_id)`, `of_unit(event_id, seq)`, `of_reference(event_id, sha256)`, `__iter__`), `blob_expected`, `blob_erasure`, `read_index(log, conn) -> RedactionIndex` (:267; reads `read_by_kind(conn, "action")`, skips malformed).
- Tombstone shape: an erased event keeps its row: `payload IS NULL` and `payload_salt IS NULL` (`erase_payload`, postgres.py:682, writes SQL `NULL`, not JSON null; `EventRow.payload is None`); an erased unit keeps its row and digest with `content`, `salt`, `speaker`, `start_ms`, `end_ms` all `NULL` (`erase_units`, :692; `UnitRow.content is None`). Hashes/digests stay, so the chain still verifies. Readers treat `payload is None` as erased (MCP: `ErasedMark`, read.py:264-267; CLI `show`: `<erased by event N>` via `_erased`, cli.py:1122). `verify` demands a redaction for every tombstone (`_Erasures.reconcile`).

## 5. `verify` (core/verify.py)
- `Finding(event_id: int, reason: str)` (:83). `verify(storage, *, batch=1000) -> list[Finding]` (:916) wraps `examine[Conn](storage, *, anchors=(), exact=False, batch=1000, blobs=None, before_blobs=None) -> Examination` (:684; `Examination(findings, tip, blobs_checked=0)`, `.anchor`).
- Per row `_check_event(row, units, source_key, blobs, *, previous_hash, first)` (:613): linkage, `_CHECKS[row.hash_version]` (:367; hash/payload/units digests), blob register. Nothing is checked per kind there.
- Form checks are only for `kind == "action"`, in `_Erasures.observe(row, units, blobs)` (:407), called from `examine` at :792 for every row (`erasures = _Erasures()` :719; `erasures.reconcile(storage, conn)` :754 at the end). `observe` records tombstones, then `if row.kind != "action" or row.payload is None: return []` (:423): an assertion never gets a form check today, and the tombstone bookkeeping above that line already runs for every kind.
  Then: `name = action_name(row.payload)`; `REDACTION` -> `parse` into the index; `MalformedAction` -> `Finding(row.id, "action has no valid form")`; `name not in KNOWN_ACTIONS` -> `Finding(row.id, f'unknown action "{name}"')`; then `_form_finding(name, row.id, row.payload, units)`.
- The hook:
```python
def _form_finding(name: str, event_id: int, payload: Mapping[str, object], units: Sequence[UnitRow]) -> Finding | None:   # :484
    if name == POLICY:  problem = check_payload(payload)  -> Finding(event_id, f"policy event {problem}"); also "policy event has units"
    if name == MODEL_CALL and (problem := _model_call_problem(payload, units)) is not None:
        return Finding(event_id, f"model_call has no valid form: {problem}")
    if name == MCP_ACCESS:
        if (problem := access_problem(payload)) is not None: return Finding(event_id, f"mcp_access has no valid form: {problem}")
        if units: return Finding(event_id, "mcp_access has units")
```
  Form functions return `str | None` (a problem sentence, never raise): `policy.check_payload(payload) -> str | None` (policy.py:549), `access.access_problem(payload) -> str | None` (access.py:222), `verify._model_call_problem(payload, units) -> str | None` (:543). Findings print in the CLI as lines (`_print_findings`, cli.py:860) and `verify` returns 1 on any finding.
- `_Erasures.reconcile` also does the cross-event check "model_call keeps the result of erased input" (:463) via `_inputs_read`/`_erased`; an assertion analogue (assertion names an erased source) would go here, and reference checks (`subject`, `approves`, `of` pointing at an assertion of the right sub-kind) need a second pass or a remembered map of id -> sub-kind, since the target stands earlier in the chain (the spec says earlier events only? it does not say; a later-pointing reference needs a decision).
- Tests: forged-form pattern in `tests/test_verify.py:1371-1418` (`append_action(storage, {...}, (), recorded_at=NOW)` then `assert verify(storage) == [Finding(id, "...")]`) and `tests/test_access.py:298-314`.

## 6. Policy and decide
```python
# core/decide.py
def circles_of(policy: Policy, identities: Sequence[Mapping[str, object]]) -> tuple[str, ...]          # :81
def decide(policy: Policy, *, identities: Sequence[Mapping[str, object]], source: str | None,
    candidates: Sequence[Candidate]) -> Decision                                                      # :240
@dataclass(frozen=True) class Candidate: provider: str; model: str; effort: str | None               # :35
@dataclass(frozen=True) class Fallback: reason: str; circles: tuple[str, ...]                        # :42
@dataclass(frozen=True)
class Decision:                                                                                       # :50
    circles: tuple[str, ...]; rule_keys: tuple[str, ...]; regions: frozenset[str]
    max_retention_days: int | None; excluded_providers: frozenset[str]; local_only: bool
    chosen: Candidate | None; inference_geo: str | None; fallback: Fallback | None
    reasons: tuple[str, ...]; undeclared: tuple[str, ...] = ()
# core/policy.py
def read_policy[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Policy       # :563
```
- `read_policy` iterates `log.actions(conn, POLICY)`, skips erased/malformed, keeps the newest per `key_of(item)`, revocations lifted, `_assemble`. `Policy` (:148): `circles, memberships, own, rules, providers, ids: Mapping[tuple[str,str], int], clients`. `Client(name, processor, token_sha256)` (:135).
- `circles_of`: `identities` are payload `channel_identities` entries (`{"channel","role","address","name"}`); own addresses (`policy.own`) are removed first; only addresses count (an `address:` match via `_matches`, domain `@x` supported). An assertion's circles would be computed from the union of its source events' identities (spec §7); there is no multi-event helper yet.
- MCP read decision (mcp_server/read.py):
```python
def _identities(payload) -> list[Mapping[str, object]]                               # :128 (channel_identities)
def _verdict(policy: Policy, client: Client, identities: Sequence[Mapping[str, object]], source: str | None) -> Decision   # :139
    # decide(policy, identities=identities, source=source, candidates=(Candidate(provider=client.processor, model="", effort=None),))
def _rules_of(policy, decision) -> tuple[int, ...]                                   # :149 (ids of rule events)
def withholding(policy: Policy, client: Client, decision: Decision) -> tuple[str, str]   # :157 (reason code NO_RULE|"rule", sentence)
def _decided(policy, client, row: EventRow, key: tuple[str, str] | None) -> _Pending     # :261
```
  `_decided`: `payload is None` -> `Read(ErasedMark(event_uri(id)), Delivered(id, (), ()), event=id)`; else `decision = _verdict(...)`; `decision.chosen is None` -> `code, reason = withholding(...)`; `mark = WithheldMark(event_uri(row.id), reason)`; `entry = Withheld(row.id, code, decision.circles, reason, uncovered, source)` with `uncovered = decision.fallback.circles if decision.fallback is not None else ()`; `Read(mark, entry, rules, row.id)`; else a pending to be shown.
- `Read(item: Item, entry: Delivered | Withheld | None, rules: tuple[int,...] = (), event: int | None = None)` (:81), `Seen(reads, more=False)` (:95; `.items`), `logged(seen, page)` (:106), `rule_ids(seen, consumed)` (:120), `event_uri(event_id) -> "previously://event/{id}"` (:76), `events(log, conn, policy, client, ids, *, from_unit) -> Seen` (:375; refuses non-observation: "the event is not an observation but an {kind}; get_event serves observations", :400-403), `chronicle(...)` (:311), `resume_point`, `circle_verdict`, `source_verdict`.
- `core/access.py` entries: 
```python
@dataclass(frozen=True) class Withheld: event: int; reason_code: str; circles: tuple[str, ...]; reason: str; uncovered: tuple[str, ...]; source: str | None   # :49
@dataclass(frozen=True) class Delivered: event: int; units: tuple[int, ...]; circles: tuple[str, ...]                                                         # :70
@dataclass(frozen=True) class Access: client: str; policy_ids: Mapping[str, object]; kind: str; name: str; arguments: Mapping[str, object]; delivered: tuple[Delivered, ...]; withheld: tuple[Withheld, ...]; outcome: str; era: str | None   # :80
def record_access[Conn](log: LogStore[Conn], access: Access, *, recorded_at: datetime) -> int                                                                   # :129
def access_problem(payload) -> str | None  # :222;  parse_access(payload) -> Access | None  # :254;  read_access(log, conn, *, client, circle, since) -> list[AccessRow]  # :296
```
  `Delivered.event`/`Withheld.event` are ints named "event" and must be event ids; an assertion id is an event id, so the access log can name an assertion without a new field. `mcp_access` payload `_FIELDS` (access.py:43) is closed; `_DELIVERED_KEYS = {"event","units","circles"}`.

## 7. MCP server (mcp_server/server.py, 881 lines)
- Registration: `build_server[Conn](log, *, stdio_client) -> MCPServer` (:618) builds `Service(log, stdio_client=...)`, `MCPServer(SERVER_NAME, version=..., instructions=INSTRUCTIONS, log_level="WARNING", cache_hints=_CACHE_HINTS)`, `server.middleware.append(service.safety_net)`, then `_tools(server, service)` (:636), `_resources` (:716), `_prompts` (:756). Docstring says "five tools, two resource templates and two prompts" (server.py:4) and `INSTRUCTIONS` (:116) says "These tools only read."; both are claims a write tool makes false. `docs/reference/mcp-tools.md:4,6` repeat it ("Every one of them only reads").
- A tool: decorator `@server.tool(name="get_event", description=_GET_EVENT)` on an inner function whose parameters are `ctx: Context` plus `Annotated[type, Field(description=...)]` arguments (pydantic `Field`s are module constants: `_CIRCLE, _SOURCE, _SINCE, _UNTIL, _CURSOR, _IDS, _FROM_UNIT` :158-164); description strings are module constants `_CHRONICLE, _GET_EVENT, _LIST_CIRCLES, _WHOAMI, _POLICY_GAPS` (:125-155), declarative and without customer data. Return type `CallToolResult`, built by `_ok(answer)` (:314: one `TextContent`, `is_error=answer.error`).
```python
@server.tool(name="get_event", description=_GET_EVENT)
def get_event(ctx: Context, ids: Annotated[list[int], _IDS], from_unit: Annotated[int | None, _FROM_UNIT] = None) -> CallToolResult:
    call = ("tool", "get_event", _given(ids=ids, from_unit=from_unit))
    return _ok(service.answer(ctx.request_context.request, ctx.protocol_version, call,
        lambda conn, policy, client: service.event_page(conn, policy, client, ids, from_unit)))
```
- Client and policy: `Service.answer(request, era, call: tuple[str, str, Mapping[str, object]], body: Callable[[Conn, Policy, Client], Answer]) -> Answer` (:361). It marks the call recorded, `name = self.client_name(request)` (:328; stdio name, else `request.scope["state"][CLIENT_STATE]` set by `auth.guarded` at auth.py:122 after the bearer token resolves through `client_for_token(read_policy(...), token)` in `build_app`'s `resolve`, server.py:850), then `with self.log.snapshot() as conn:` (READ ONLY snapshot) `policy = read_policy(self.log, conn)`; `client = policy.clients.get(name)` else `Refused("the client {name} is not in force...")`; `policy_ids = {"client": ..., "processor": ..., "rules": []}`; `answer = body(conn, policy, client)`; `finally: self.record(name, policy_ids, call, answer, era)` writes `mcp_access` whatever happened (a failure becomes the fixed `_FAILED` error text, logged). Note: the body runs in a SNAPSHOT connection, i.e. a read context; a write tool cannot write inside `body` and needs its own `log.begin()` path (and its own access entry decision; `_CALL` ContextVar `_Mark.recorded` exists so a call that writes its own access entry stops the safety net from writing a second).
- Rendering a page: `render_page(title, seen.items, cursor_for=..., page=1, more=..., next_hint=...)` -> `Page`, then `_paged(seen, page)` (:581) -> `Answer(page.text, delivered=..., withheld=..., rules=...)` using `logged(seen, page)` and `rule_ids(seen, page.consumed)`. See `event_page` (:501) and `chronicle_page` (:458). Non-item text results use `render_text(title, lines)`, errors `render_error(message)`.
- `Answer(text: str, error: bool = False, delivered: tuple[Delivered,...] = (), withheld: tuple[Withheld,...] = (), rules: tuple[int,...] = ())` (:230). `Refused(Exception)` (:225) = worded error for the client.
- Recording: `Service.record(client, policy_ids, call, answer, era)` (:339) builds `Access(...)` with `arguments=recordable(dict(arguments))` (`recordable` :201 limits: `_TEXT_LIMIT=1_000`, `_ENTRY_LIMIT=50`, `_DEPTH_LIMIT=4`; NUL/float/int>2^53 handled) and calls `record_access(self.log, access, recorded_at=datetime.now(UTC))` which is `append_action` (own transaction + retry). `Service.net` (:403) and `safety_net` (:432) record calls that never reached a handler.
- Tool-list checksum test: `tests/test_mcp_server.py:817-856`. `TOOLS_SHA256 = "393fe0fd49afaea2289e95e377a42e3b3ed4876e6085396bdabde8d8344bd3fc"` (:822); `tool_list_digest(tools)` = sha256 of `json.dumps(sorted(tools, key=name), sort_keys=True, separators=(",", ":"), ensure_ascii=False)` (:830-837); `test_the_tool_list_matches_its_checksum(world, mode)` parametrized over `MODES = ("auto", "legacy")` lists tools via `_session(server, mode, lambda s: s.list_tools())`, builds `{"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}` per tool, asserts the sorted name list equals `["get_event","list_circles","policy_gaps","previously","whoami"]` and the digest equals `TOOLS_SHA256`. Adding five tools changes both the name list and the checksum. `docs/reference/mcp-tools.md` and `docs/explanation` ({ref}`mcp-tool-list`) refer to it.
- `_CACHE_HINTS: Final[Mapping[CacheableMethod, CacheHint]] = {"resources/read": CacheHint(ttl_ms=0, scope="private")}` (:173-175), used only in `build_server` (`cache_hints=_CACHE_HINTS`, :627); it concerns resources, not tools.
- The auth wrapper: `auth.guarded(app, *, resolve: Callable[[str], str | None], ready: Callable[[], bool]) -> ASGIApp` (auth.py:95); sets `scope.setdefault("state", {})[CLIENT_STATE] = name` (:122, `CLIENT_STATE = "previously_client"` :44); `Service.client_name` reads it (server.py:328-337); `build_app[Conn](log, *, allowed_hosts: Sequence[str]) -> Starlette` (:839) wires `resolve`/`ready` and `app.add_middleware(guarded, ...)`. Over stdio the name is `stdio_client` (env `PREVIOUSLY_MCP_CLIENT`, `CLIENT_VARIABLE` :110).
- No write tool or confirm-handle code exists: grep for `confirm|handle|write_assert|write_approve|hmac` in `mcp_server/` finds only the unrelated word "handler". `hmac` is used only in `core/clients.py:27` (`hmac.compare_digest` for token hashes). The spec's seal key would be a new setting.

## 8. `mcp_server/render.py`
```python
@dataclass(frozen=True) class Head: uri: str; occurred_at: datetime; source: str; sender: str | None; recipients: tuple[str, ...]; subject: str | None   # :104
@dataclass(frozen=True) class Shown: head: Head; units: tuple[tuple[int, str], ...]; attachments: tuple[str, ...] = (); provenance: tuple[tuple[str, str], ...] = ()   # :114
@dataclass(frozen=True) class WithheldMark: uri: str; reason: str          # :133
@dataclass(frozen=True) class ErasedMark: uri: str                          # :139
@dataclass(frozen=True) class ErrorMark: label: str; message: str           # :144 (the per-id error item)
type Item = Shown | WithheldMark | ErasedMark | ErrorMark                   # :155
@dataclass(frozen=True) class Page: text: str; next_cursor: str | None; removed_characters: int; consumed: int = 0; units: tuple[tuple[int, ...], ...] = ()   # :158
def sanitize(text: str) -> tuple[str, int]                                  # :185
def draw_tag(content: str, *, candidates: Iterator[str] | None = None) -> str   # :210
def render_page(title: str, items: Sequence[Item], *, cursor_for: Callable[[int], str], page: int = 1,
    candidates: Iterator[str] | None = None, more: bool = False, next_hint: Callable[[str], str] | None = None) -> Page   # :414
def render_text(title: str, lines: Sequence[str]) -> str                    # :499
def render_error(message: str) -> str                                       # :508
@dataclass(frozen=True) class Position: after: int; page: int               # :515
def encode_cursor(after: int, filters: Mapping[str, str], *, page: int = 2) -> str   # :522
def decode_position(cursor: str, filters: Mapping[str, str]) -> Position    # :545 (raises ValueError(CURSOR_REFUSED))
```
- Constants: `PAGE_CHARS = 60_000` (:51), `CURSOR_REFUSED = "cursor is not valid for these filters"` (:78), `_FIELD_CHARS=200, _MAX_RECIPIENTS=10, _MAX_ATTACHMENTS=10, _REASON_CHARS=500, _ERROR_CHARS=2_000`.
- Rendering of `Shown` (`_shown_block` :307): heading `### uri · time · source · sender → recipients` (`_heading` :260; assumes a mail-shaped `Head`), then a fence (`_fence_open`/`_fence_close`, random tag from `draw_tag`) holding `Subject:`, `Attachments:`, provenance `label: value` lines, and `#unit-<seq>` blocks, all through `_Counter.line/.text` which sanitize. Placeholders: `[erased: uri]`, `[withheld: uri — reason]`, `Error: label — message` (`_placeholder` :365).
- Could an assertion use the existing items? `WithheldMark`, `ErasedMark` and `ErrorMark` carry only a URI/label and text, so a withheld, erased or failed assertion renders with them unchanged (the URI is `previously://event/<id>`). A shown assertion does NOT fit `Shown`: `Head` requires `source`, `sender`, `recipients`, `subject`, which are mail concepts, units are `(seq, text)` pairs inside the fence, and the page layout (budget cut by units, `#unit-` pointers, `_pointer_note`) is unit-based. An assertion has structured fields (debtor, creditor, what, due, state, versions, sources); it needs a new item type (added to `Item`; `render_page` branches on `isinstance` in several places, check `render_page` :414-497 and `_placeholder`/`_shown_block` call sites, and `read._weight` :302, which tests `isinstance(read.item, Shown)`), or a mapping onto `Shown` with `source="assertion"` and a unit per field, which would put structured data into "units" that `Delivered.units` then records as unit numbers.
- Tests: `tests/test_render.py` (687 lines).

## 9. CLI (cli.py, 2295 lines)
- Subcommand with sub-subcommands, `policy`: `Command("policy", "set and show the processing policy", _cmd_policy, _policy_arguments)` (cli.py:2213) where
```python
def _policy_arguments(parser: argparse.ArgumentParser) -> None:     # :1432
    what = parser.add_subparsers(dest="what", required=True)
    def writing(name: str, sentence: str) -> argparse.ArgumentParser:
        form = what.add_parser(name, help=sentence, description=sentence)
        form.add_argument("--statement", required=True, help="the sentence it was set with; it stays in the log")
        form.add_argument("--revoke", action="store_true", help="lift the statement instead")
        form.add_argument("--yes", action="store_true", help="write without asking")
        return form
    circle = writing("circle", "create a circle"); circle.add_argument("name"); ...
    show = what.add_parser("show", ...); found = what.add_parser("gaps", ...)
def _cmd_policy(args) -> int:   # :1714  dispatches on args.what: "gaps" -> _cmd_policy_gaps, != "show" -> _cmd_policy_set, else prints
```
  `redact` (`dest="target"`, `form(name, sentence)` helper, cli.py:1129) and `client` (`dest="what"`, :2025) use the same shape. `COMMANDS: tuple[Command, ...]` (:2201) is the single declaration; `Command(name, help, run: Callable[[Namespace], int], arguments: Callable[[ArgumentParser], None] = _no_arguments)` (:2012); `main` builds subparsers and a dispatch table from it. New commands go there; `tests/test_cli.py` holds the command names the help prints against `COMMANDS`.
- `_confirmed(args) -> bool` (:1591): `args.yes` -> True; else `input("write? [y/N] ")`; `EOFError` -> prints "no answer: the input ended before one came; --yes writes without asking" to stderr and returns False; yes iff `answer.strip().lower() in {"y", "yes"}`.
- `--statement` pattern: required free-text sentence kept in the log; `_cmd_policy_set` (:1612): build item -> `normalized` -> `with _storage() as storage:` read policy -> `refusal(...)` raise `PolicyRefused` BEFORE asking -> print the structured payload as `json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)` -> `if not _confirmed(args): print("nothing written", file=sys.stderr); return 1` -> write with `recorded_at=datetime.now(UTC)` -> `print(f"policy event {event_id}")` -> `return 0`.
- Exit codes: `0` success; `1` declined ("nothing written") and `verify` with findings (cli.py ~:893); `2` for `PreviouslyError` or `StorageError`, printed by `main` as `Error: <escape_controls(msg)>` on stderr (cli.py `main` `except (PreviouslyError, StorageError)`); argparse errors exit 2 itself; a signal gives `128 + signum` (`_terminate`, SIGTERM -> 143); anything else is a stack trace (exit 1 from the interpreter). `redact` asks no question (reason is the brake).
- Settings: `_dsn()` (:274) reads `PREVIOUSLY_DSN` else `PreviouslyError("PREVIOUSLY_DSN is not set")`; `def _setting(name: str) -> str` (:310) = `os.environ.get(name)`, empty/unset -> `PreviouslyError(f"{name} is not set")`. Others read `os.environ.get(...)` directly (`_cmd_mcp`, `_mcp_address`, `_cmd_serve`). Names must not look like a Kubernetes service variable (`tests/test_settings.py`: no `_PORT`/`_HOST` suffix; it collects every `PREVIOUSLY_*` name from the source AST outside docstrings).
- `_storage()` (:283) is `@contextmanager def _storage() -> Generator[PostgresStorage]`: `storage = from_dsn(_dsn())`, yields, `storage.close()` in `finally`. Used as `with _storage() as storage:` then `storage.begin()` / `storage.snapshot()`; commands pass `storage` as `log`, `eraser` and projection store. Imports of heavy modules (MCP SDK) happen inside the command function (:2126 comment).
- T201 comment (pyproject.toml:111-148): `"src/previously/cli.py" = ["T201"]` (:149), with a history list ending "`serve` took it to sixty-four the same day... `mcp` prints nothing" (:146-148); the first line says "each of the sixty-four `print` calls" (:112-113). MEASURED now: `/home/jensens/ws/jwk/previously/.venv/bin/ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` reports `Found 66 errors.` So the comment (64) is two behind; the IMAP-folders PR #16 (merged on main) probably added the two. Any new `print` raises it again, and the comment must be retyped with the measured number (CLAUDE.md "A comment is a claim").

## 10. Tests
- `tests/conftest.py`: `@pytest.fixture(scope="session") def engine() -> Iterator[Engine]` (:65; starts `PostgresContainer("postgres:18", driver="psycopg")`, runs `command.upgrade(Config("alembic.ini"), "head")`); `@pytest.fixture def db(engine: Engine) -> Iterator[Engine]` (:76; `TRUNCATE_ALL` over `metadata.sorted_tables` reversed, so new tables are covered automatically); `truncate_statement() -> str` (:91); `write_version_1() -> WriteVersion1` (:117; `write(storage, events, recorded_at) -> list[int]` writes hash-format-1 observations by hand); `unmigrated_engine` (:192); `age_identity`, `other_age_identity`; `s3_settings`, `blob_store`, `s3_connections`; `mail_server`, `imap_folder`; `model_server` (class `ModelServer` :406). There is NO `storage` fixture: tests do `storage = PostgresStorage(db)` (import `from previously.storage.postgres import PostgresStorage`) and mark `@pytest.mark.db`.
- MCP tests: `tests/test_mcp_server.py`. `World(storage, tokens: dict[str,str], ids: dict[str,int], policy_event: int)` frozen dataclass (:~108); `@pytest.fixture def world(db: Engine) -> World: return _world(db)` (:~176). `_world(db)` builds storage, `_policy(storage)` (providers `CLAUDE` (us, not local) and `LOCAL`, circles huber/office/bauer/team, rules for three), clients `claude-code` (processor `claude-max`) and `local-harness` via `add_client(storage, name, processor=..., statement="s", recorded_at=T0)` which returns `(id, token)`, mails via `_take_in(storage, raw, *, internaldate=INTERNALDATE) -> int`, one `redact_event`.
  - Both generations: `MODES = ("auto", "legacy")` and `ERAS = {"auto": "2026-07-28", "legacy": "2025-11-25"}`; every tool test is `@pytest.mark.db @pytest.mark.parametrize("mode", MODES)`. `def _session[T](server: Any, mode: str, use: Callable[[Client], Awaitable[T]]) -> T` runs `anyio.run` with `async with Client(server, mode=mode) as client: return await use(client)` (`from mcp.client.client import Client`). `def _tool(world, mode, name, arguments=None, *, client="claude-code") -> CallToolResult` builds `build_server(world.storage, stdio_client=client)` and calls `session.call_tool(name, arguments or {})`. `_text(result)` asserts exactly one text block, `structured_content is None`, numbers `<= 2**53-1`. `_accesses(world, client=None) -> list[AccessRow]` / `_last_access(world)` via `read_access`. `_shown_ids`, `_untagged` (strip fence tag).
  - HTTP: `_http(world, use, *, allowed_hosts=())` builds `build_app(world.storage, allowed_hosts=...)`, runs `app.router.lifespan_context(app)` with `httpx2.ASGITransport` + `httpx2.AsyncClient(base_url="http://127.0.0.1:8765")`; `_over_http(world, token, mode, name, arguments)` uses `Client(streamable_http_client(URL, http_client=http), mode=mode)` with an `Authorization: Bearer <token>` header (`URL = "http://127.0.0.1:8765/mcp"`).
- Hash-chain helpers / verify: `tests/conftest.py` `write_version_1` (uses `core.hashing` `event_hash`, `payload_hash`, `units_hash`); `tests/test_hashing.py:114 _event_hash(...)`; `tests/test_verify.py` uses `examine(storage)` (imported from `previously.core.verify`) at :702, :729-816 (`examine(storage, anchors=[...], exact=True).findings`), plain `verify(storage) == [Finding(id, "...")]`; forging by raw `UPDATE event SET payload = CAST(:p AS jsonb)` through `db.begin()` (:~125). For action forms: `append_action(storage, {...}, (), recorded_at=NOW)` then `verify`. `tests/test_verify.py:56 _event(external_id)` builds a `RawEvent(source="cli", ..., evidence=Evidence.RECOLLECTION, units=split_plaintext(...), payload={"note": ...})`; `WRITTEN_IN` parametrizes hash version 1/2 (`_write(version, storage, events, write_version_1)`). There is no assertion helper; forging an assertion would need a hand-built `chain.prepare` + `chain.link` + `storage.insert_event` with `kind="assertion"` (the `event_kind_check` allows it) or the new write path.
- Mail to observation: `from previously.core.mail import map_mail`; `map_mail(raw: bytes, *, internaldate: datetime, found_in: Mapping[str, str]) -> Mapped` (mail.py:191; `Mapped(event: RawEvent, raw: bytes, attachments, inner)`); `append(storage, [mapped.event], recorded_at=T0)` returns ids. `test_mcp_server._take_in` (shown above) adds `BlobRef`s and `payload["raw"]`. Mail fixtures: `tests/mailfiles.py` (`PLAIN`, `HTML_ONLY`, `HTML_BLOCKQUOTE`, `NO_MESSAGE_ID`, `ATTACHMENTS_ONLY`, `DATE_WITHOUT_ZONE`, `DATE_UNREADABLE`), `FOUND_IN = {"connector": "imap:pilot@mail.example.org/Kunde Huber", "uid": "7"}`, `INTERNALDATE = datetime(2026,10,8,9,0,0,tzinfo=UTC)`, `T0 = datetime(2026,10,11,12,0,0,tzinfo=UTC)`.
- Other test files that a new feature touches: `tests/test_cascade.py` (erasure cascade for model calls; `_event`, `_rows`), `tests/test_redact.py`, `tests/test_projection_worker.py`, `tests/test_chronicle.py`, `tests/test_schema.py`, `tests/test_migrate.py` (`_head()` reads `get_current_head()`; no literal revision), `tests/test_docs_references.py` (resolves `{ref}` labels in `src/` and `tests/`, holds quoted messages), `tests/test_docs_typed_output.py` (test count in the tutorial; changes with every new test), `tests/test_contracts.py`.

## 11. Settings, docs and import contracts
- Env settings read in `src/` (grep, with count of occurrences): `PREVIOUSLY_DSN` (12), `PREVIOUSLY_BLOB_{ENDPOINT,BUCKET,REGION,ACCESS_KEY,SECRET_KEY,RECIPIENT,IDENTITIES}`, `PREVIOUSLY_IMAP_{ADDRESS,HOST(refused),USER,PASSWORD,FOLDER}`, `PREVIOUSLY_LOCAL_MODEL_URL`, `PREVIOUSLY_PRICES`, and for the MCP server only: `PREVIOUSLY_MCP_CLIENT` (server.py:110 `CLIENT_VARIABLE`, cli.py `_cmd_mcp`), `PREVIOUSLY_MCP_ADDRESS` (cli.py:`_mcp_address`; default `MCP_ADDRESS = "127.0.0.1:8765"`), `PREVIOUSLY_MCP_ALLOWED_HOSTS` (cli.py `_cmd_serve`, split on commas/blanks), plus `PREVIOUSLY_MCP_HOST`/`_PORT` only in refusal messages and the Kubernetes-collision test. `PREVIOUSLY_DSN` is read by `_storage()`, so the MCP server gets it through `from_dsn`. The server reads no secret today.
- Settings reference: `docs/reference/configuration.md`, section "## Server settings" (:~186-211), table `| Variable | Meaning | Missing at |` with rows like ``| `PREVIOUSLY_MCP_CLIENT` | The name of the client that `mcp` serves over standard input and output, a client in force from `client add`. | `mcp` |``; a "Missing at" cell says which command fails or "Never; ...".
- `docs/reference/environment.md` (page label `(environment-requirements)=`, title "Environment requirements"): ONE table, header `| Concerns | Requirement | Reason |` / `|---|---|---|`; a row is `| MCP server | <requirement sentence> | {ref}`mcp-token` |` (reason cell = one or two `{ref}` labels, comma separated). Existing groups: Database, Backups, Bucket, Credentials, Keys, MCP server, Network, Anchors. One sentence per line rule applies to prose, but table rows stay on one line each. The spec (§10, §13) wants a new row for the handle key (only the MCP server holds it; not the tools pod) and one for "`write_approve`/`write_reject` are not auto-allowed in the client".
- Import-linter (`.importlinter`; nine contracts): `layers` (cli > connectors | gate | mcp_server > core | migrations > storage > contract); `core-is-clean` (core imports no sqlalchemy/psycopg/alembic/anthropic/openai/pyrage/boto3/botocore/html2text/mcp/mcp_types/starlette/uvicorn/imaplib); `core-and-contract-know-no-sql` (core and contract import no sqlalchemy/psycopg); `no-vendor-sdk`; `only-sealing-knows-age` (pyrage only in `core.sealing`); `only-s3-knows-boto3`; `only-mail-knows-html2text`; `only-imap-knows-imaplib`; `only-mcp-server-knows-mcp` (named edges `mcp_server.server -> mcp|starlette|uvicorn`, `mcp_server.auth -> starlette`). A new `core/assertion.py` (and `core/projection/*.py`) touches `layers` (may import `contract` and `storage.errors` as `core.action` does; must not import `cli`, `gate`, `mcp_server`, `connectors`) and `core-is-clean`/`core-and-contract-know-no-sql` (no SQL: new queries go into `storage` behind a `contract.store` protocol). A handle seal in `mcp_server` would use `hmac`/`hashlib` from the standard library (not forbidden). A new module in `mcp_server` that imports the SDK needs a named edge in `only-mcp-server-knows-mcp`; modules that do not import `mcp`/`starlette` need none (like `read.py`, `render.py`). Never widen a contract; edges are named.

## 12. Migrations
- 5 revisions in `migrations/versions/`: `0001_log`, `0002_projections`, `0003_hash_version_2`, `0004_event_blob`, `0005_watermark` (a linear chain, each `down_revision` the previous; `0005_watermark` has a guarded downgrade, see `tests/test_migration_0005.py`).
- Next revision id: `0006_<name>` (file `src/previously/migrations/versions/0006_<name>.py`, `revision = "0006_<name>"`, `down_revision = "0005_watermark"`, `branch_labels = None`, `depends_on = None`; the spec names it `0006`). Docs that name migrations: `docs/reference/database-schema.md` (e.g. :218), `docs/superpowers/landkarte.md`; `tests/test_migrate.py` takes the head from the script directory, no literal to update.

## Observations that bear on the plan
1. `action._KIND` is private and `write_action*` hard-codes `kind="action"`; an assertion path needs its own `prepare(kind="assertion", ...)` call or a refactor with a `kind` parameter. The chain, retry and canonical payload checks are all reusable.
2. `verify` form checks are inside `_Erasures.observe` and gated on `row.kind == "action"` (verify.py:423); assertions need a branch before or at that line, and cross-event checks (references to earlier assertions, sources existing, named units existing) need state across the pass.
3. `ProjectionStore` has table-specific methods only; each projection adds protocol methods, Postgres methods, a `_PROJECTION_TABLES` entry, and row dataclasses. `PROJECTIONS` drives `project` and the post-redaction catch-up, so a new projection must also tolerate an erased (payload `None`) assertion.
4. MCP tools run inside `Service.answer` with a read-only `snapshot()` connection and always record `mcp_access` afterwards; `INSTRUCTIONS`, the module docstring, `docs/reference/mcp-tools.md` and the tool-list checksum all say "only reads"/"five tools".
5. `render.Shown`/`Head` are mail-shaped; placeholders (`WithheldMark`, `ErasedMark`, `ErrorMark`) are item-agnostic.
6. `cli.py` T201 comment says 64; the measured count is 66.
7. `store.py` docstring and `pyproject.toml` hold counted figures that adding a `LogStore` method or a `print` will falsify.
