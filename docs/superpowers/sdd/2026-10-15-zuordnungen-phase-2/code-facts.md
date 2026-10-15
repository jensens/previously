# Code facts — measured on 2026-10-14 at 0bfb228

Worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/zuordnungen-2`, branch `worktree-zuordnungen-2`, tree clean.
Test count: `uv run pytest --collect-only -q | tail -1` gives `2650 tests collected in 6.60s`.
Paths are relative to `src/previously/` unless they start with `tests/`, `docs/` or `.`.
Nothing in the repository was changed; one scratch script lives in the session scratchpad (see §11, trap 1).

The living spec for this phase is `docs/superpowers/specs/2026-10-14-zuordnungen.md` §8 (Zuordnung, Phase 2), §10.1 (Projektionen), §10.2/§10.3 (CLI, MCP), §10.4 (Gate unchanged in phases 1 and 2), §13 (Betrieb).
§8 leaves "whether ingest writes the further find-spots and under which level" to the phase-2 plan.

---

## §1 The graph model as built (`core/graph.py`, 1132 lines)

### Types

- `Period(start: date | None, end: date | None)`, frozen, `holds(day)` — graph.py:113-125.
- `type FieldValue = str | date | Period | int` — graph.py:126.
- `EntityBody(type: str, language: str | None, fields: Mapping[str, FieldValue], state: str)` — graph.py:128-134.
- `RelationBody(type: str, start: int | Source, to: int | None, candidates: tuple[int, ...] | None, period: Period | None, fields: Mapping[str, FieldValue], state: str)` — graph.py:136-151.
  `start` is an entity id (`int`) or a `Source` (`core.assertion.Source(event: int, units: tuple[int, ...] | None)`), "which the form admits for phase 2 and `conformance_problem` refuses until then".
  `to` is `None` only for a question (then `candidates` names 2 to 5 ids; `MIN_CANDIDATES`/`MAX_CANDIDATES` graph.py:96-97).
- `Claim(kind, author, responsibility, evidence, sources: tuple[Source, ...], reason, handle, subject, approves, under, confidence, contests, body: EntityBody | RelationBody)` — graph.py:154-168 (positional, 13 fields).
  `kind` is `"entity"` or `"relation"` (`ENTITY`/`RELATION`, graph.py:74-75, from `vocabulary.ENTITY_KIND`/`RELATION_KIND`); it is the payload key `assertion`.
- `GraphVersion(id: int, recorded_at: datetime, claim: Claim)` — graph.py:699.
- `ClassState(id, revoked, demote)` — graph.py:688.
- `GraphThread(subject: int, kind: str, versions: tuple[GraphVersion, ...], rejected: frozenset[int], approved: frozenset[int])` — graph.py:728. Methods, all taking `classes: Mapping[int, ClassState]`: `winner`, `pending`, `objections`, `question`, plus private `_unanswered`, `_anchor`, `_waiting`.
- `Graph(threads: Mapping[int, GraphThread], classes: Mapping[int, ClassState])` — graph.py:818-901.

### The fold

- `GraphFold` (graph.py:936) — incremental, one row at a time. Fields: `_drafts: dict[int, _Draft]`, `_thread_of: dict[int, int]` (standing version id -> subject), `_erased: set[int]`, `_threads: dict[int, GraphThread]`, `_touched: dict[int, None]`.
  - `add(row_id: int, recorded_at: datetime, payload: Mapping[str, object] | None, classes: Mapping[int, ClassState]) -> None` — graph.py:963. `payload is None` -> `_erased.add(row_id)` and return. A rejection (`payload["assertion"] == REJECTION`) goes to `_reject`. Otherwise `parse_claim` (None -> ignored silently); a `subject` that names no draft and no erased row is dropped; a kind that differs from the draft's is dropped; `contests` must name a direct version (or erased); `approves` must name an unanswered open/transitive version (or erased).
  - `classes` matters at `add` time only for `_reject` (graph.py:1000: a rejection counts when `level_of(target, classes) != DIRECT` at that moment).
  - `graph(classes) -> Graph` copies the thread map (graph.py:1016); `current(classes) -> Graph` returns a `MappingProxyType` view that follows later `add` calls (graph.py:1021); `_built()` rebuilds only `_touched` threads (graph.py:1029).
  - `subject_of(version_id)`, `erased(event_id)` — graph.py:955, 959.
  - There is **no remove / undo**. A row erased after it was folded cannot be taken back out.
- `fold_graph(rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]], classes) -> Graph` — graph.py:1044. `read_graph` hands it the classes **in force now** for every row (not the classes at the row's time); `verify` uses row-time classes through `ClassFold`.
- Winners are computed at read time from `classes` (`GraphThread.winner`, graph.py:756): latest direct, else latest unanswered transitive, else latest unanswered open. So a stored winner goes stale when an approval class is revoked with `demote`, because `level_of` changes. The thread contents (versions, rejected, approved) do not depend on classes except through `_reject`.
- `level_of(version: GraphVersion, classes: Mapping[int, ClassState]) -> str` — graph.py:706. Own responsibility unless transitive; transitive of a `GATE_TYPES` kind -> `OPEN`; transitive with unknown class or class revoked with `demote` -> `OPEN`.
- The fold does not read the vocabulary at all. `conformance_problem` and `closes_cycle` do, at write time and in `verify`.

### `conformance_problem` and the event-start refusal

`conformance_problem(claim: Claim, vocabulary: Vocabulary, *, new_thread: bool, entity_types: Mapping[int, str]) -> str | None` — graph.py:643.

Every place that treats an event start (`isinstance(..., Source)`) specially, measured by `grep -rn "Source)" src` and reading:

| # | Where | What it does |
|---|---|---|
| 1 | graph.py:656-659 | **The refusal.** `isinstance(body, RelationBody) and isinstance(body.start, Source)` returns `"an event as the start of a relation comes with assignments"` before any other check (also before the type lookup, the retired check, the field check). |
| 2 | graph.py:629-641, 682 `_ends_conformance(spec, body, start: int, entity_types)` | The caller casts `cast("int", body.start)`; `ends = [start, *(to or candidates)]`; each must be in `entity_types` (`"an end of the relation is not an entity that stands"`); `entity_types[start] not in (spec.from_ or ())` -> `"the start of the relation is of a kind its relation kind does not start from"`. Nothing here can take an event. |
| 3 | graph.py:887 `Graph.reaches` | skips `isinstance(body.start, Source)` ("A relation that starts at an event is no edge between entities", docstring graph.py:881). |
| 4 | graph.py:215 `claim_payload` | writes `{"event":…, "units":…}` for a Source start and `{"entity": n}` otherwise. Already handles both. |
| 5 | graph.py:537-538 `_body_of` | parses `from` with an `"event"` key to `Source`. Already handles both. |
| 6 | graph.py:422-438 `_end_problem` | form check accepts `{"event","units"}`; `_units_problem` (graph.py:245) accepts units `>= 0` (but see §11, units start at 1). |
| 7 | graph.py:1106-1107 `claim_changes`/`_texts_of` | `_sources_text((start,))` for a Source start. Already handles both. |
| 8 | graph_write.py:273-274 `closes_cycle` | returns False for a Source start. |
| 9 | graph_write.py:745-747 `relation_ends` | `ends = [body.start, …]` then `if isinstance(end, int)`, so a Source start contributes no end. |
| 10 | graph_write.py:770-773 `relation_visible` | `any(not isinstance(v.claim.body, RelationBody) or isinstance(v.claim.body.start, Source) for v in thread.versions)` -> returns **False**: a relation with any event-start version is shown to nobody. |
| 11 | mcp_server/read.py:837-857 `ThreadVerdict` docstring + `GraphView.verdict` (read.py:887-923) | `shown = relation_visible(...)`; `relation_ends` supplies the ends it checks; docstring says "a relation that starts at an event is not shown, since phase 1 shows none at all". |
| 12 | mcp_server/read.py:1072-1073 `claim_lines` | `from: an event` for a Source start. |
| 13 | mcp_server/read.py:1176 `_relation_lines` | `if not isinstance(body.start, int) or not view.seen(relation_id): continue` — an event-start relation is not listed under an entity. |
| 14 | cli.py:3376, 3440, 3486, 3546-3547 | `_claim_label`, `_relation_line`, `_claim_fields`, entity page: `isinstance(body.start, int)` else `"(an event)"`; entity page `elif related.to == thread.subject and isinstance(related.start, int)`. |
| 15 | cli.py:3335 `_marks` | `ends = [body.start, …]`, `judged = all(end in kinds for end in ends if isinstance(end, int))`, then `conformance_problem(claim, vocabulary, new_thread=False, entity_types=kinds)`; so today an event-start version would be marked "not fitting" by the refusal text. |
| 16 | cli.py:3469 `_cmd_relations` | `args.start is None or body.start == args.start` — `body.start` may be a `Source`; compares Source to int -> False, so `--from N` never matches an event start. |
| 17 | cli.py:3183 `_cmd_relate` | `start = args.start if args.start is not None else (old.start if old else None)`; `--from` is `type=int`, so the CLI cannot write an event start (and cannot be `subject`-edited into one). |
| 18 | mcp_server/server.py:573 `RelationItem.start: Annotated[int, Field(alias="from", …)]` and `_relation_claim` (server.py:2201-2235) | `_event_id(number, item.start)`; MCP `write_relation` takes an entity id only. `write_record` (server.py:2396) puts `from` among `ends`. |
| 19 | graph_write.py:280-286, 273 | the cycle rule needs `body.start == body.to` and `reaches(body.to, body.start, …)`, both ints. |

Tests that pin the refusal: `tests/test_graph.py:1400-1403` (`conformance(claim) == "an event as the start of a relation comes with assignments"`), `tests/test_graph.py:242-243` (form accepts `Source(5, (1, 2))`), `tests/test_graph.py:1328` (fold keeps one), `tests/test_graph_write.py:1099-1108` (`test_a_relation_that_starts_at_an_event_closes_no_cycle`).
Docs that say it: `docs/reference/vocabulary.md:75` and `:106`; `docs/explanation/graph.md:11` (page "covers the first phase"; "Assigning events and passages to an entity … come in later phases").

### `Graph.relations()`, `entities()`, `reaches()`

- `entities()` (graph.py:831): winner of each `ENTITY` thread, unless `body.state == RETRACTED`. Includes winners of **any level**, open proposals included.
- `relations(*, at: date | None = None)` (graph.py:839): winner of each `RELATION` thread, skipping a winner with `body.state != STANDING` (retracted) or `body.to is None` (a question; "no relation yet"); with `at`, skips when `body.period` is set and does not hold on `at`. Also winners of every level, open included (docstring says a walk needs a visited set).
  It does **not** check that the ends are entities that stand, and does not look at the vocabulary or the policy.
- `reaches(start: int, end: int, types: frozenset[str], *, without: frozenset[int] = frozenset(), levels: frozenset[str] = frozenset(LEVELS)) -> bool` (graph.py:858): builds `edges` from `self.relations()` over relations of `types`, minus `without`, minus `isinstance(body.start, Source)`, minus those whose `level_of` is not in `levels`; DFS with a visited set from `start`; "path of at least one edge" (so `start == end` is True only through a cycle).
  It rebuilds the edge dict on **every call** (O(relations)) — one reason `verify` is quadratic over acyclic edges.
  There is no method that walks backward (descendants of N), nor one that returns the set of nodes reached; a `chronicle --in N` closure is new code.
- The vocabulary behavior `transitive` is **declared but nothing reads it**: `grep` finds `TRANSITIVE` (behavior) only in `core/vocabulary.py:75` (`_BEHAVIORS`) and `part_of` in `vocabulary.toml:83` carries `behaviors = ["acyclic", "transitive"]`. `closes_cycle` reads `ACYCLIC` (graph_write.py:276), `classes.py:271,430` read `ACYCLIC`, graph.py reads `CLOSABLE` (675) and `PERIOD_BEHAVIOR` (678). "Transitive upward via `part_of`" must either start reading `TRANSITIVE in spec.behaviors` or hard-code the type.

---

## §2 The write path (`core/graph_write.py`, 784 lines)

Module docstring (graph_write.py:4-53) states the order inside one transaction: lock every **source** event ascending (`locker.lock_event`) and refuse a bad source with the sentences of `check_sources`; read the tip, then below it every assertion (`_rows(..., up_to=top)`); a handle already carried = repeat -> answer with those ids; read vocabulary and classes after the tip; take claims one by one, set the level, check form / names / vocabulary / answer / cycle against `GraphFold.current` of what stands below the tip plus the claims earlier in the batch; write all on that tip. `retrying(log, once)` retries on a lost chain position.

Signatures:

- `check_claims[Conn](log: LogStore[Conn], conn: Conn, claims: Sequence[Claim], *, recorded_at: datetime) -> tuple[Claim, ...]` — graph_write.py:535. No locks, no writes; `read_sources(log, conn, events)` reads the source rows with `log.read(conn, event_id, 1)`.
- `write_claims[Conn](log: LogStore[Conn], locker: RedactionStore[Conn], claims: Sequence[Claim], *, recorded_at: datetime, expect: Sequence[Decided] | None = None) -> Written` — graph_write.py:589. `events = sorted({source.event for claim in claims for source in claim.sources})` (graph_write.py:615); `rows = {event_id: locker.lock_event(conn, event_id) for event_id in events}` (graph_write.py:623).
- `read_graph[Conn](log, conn, *, as_of: datetime | None = None) -> Graph` — graph_write.py:164. `classes = read_classes(log, conn, at=as_of)` (reads `log.actions(conn, "approval_class")`), then **all** `log.read_by_kind(conn, "assertion")` (every assertion row, optionally filtered by `recorded_at <= as_of`), then `fold_graph(rows, classes.states)`. Two queries, the second one over every assertion.
- `_checked` (graph_write.py:467): `check_sources(log, conn, rows, [s for claim in claims for s in claim.sources])`; `read_vocabulary`, `read_classes`; builds a `GraphFold` from `below`; per claim: `_levelled` -> `_payload` (form + `canonical`) -> `_check_claim` -> `folded.add(top + 1 + offset, …)`.
- `_check_claim` (graph_write.py:448): `_check_subject`, `_check_approval`, `conformance_problem(..., entity_types=EntityTypes(graph))`, `_check_answer`, `closes_cycle`.
- `EntityTypes(Mapping[int, str])` (graph_write.py:181): kind of each entity with a winner that is not retracted, by id, looked up one at a time; `__iter__`/`__len__` call `graph.entities()`. Winners of any level count (map point M4).
- `Decided(level, under, contests)` / `decided(claim)` / `Written(ids, levels)` — graph_write.py:130-153. `CLASS_CHANGED`, `DIRECT_WRITTEN` — graph_write.py:114-115.
- `GraphRefused(PreviouslyError)` — graph_write.py:124.
- `starts_thread(claim, thread) -> bool` (209), `pending_question` (232), `names_a_candidate` (241), `takes_proposal` (289), `closes_cycle(graph, claim, vocabulary, *, level) -> bool` (252).

`check_sources` is `core/assertions.py:422`: every source event exists, is of kind `observation`, is not erased (payload not None); every cited unit exists and has content. Refusal sentences: `"there is no event {id} to rest on"`, `"event {id} is not an observation, and only one can be a source"`, `"event {id} is erased and cannot be a source"`, `"event {e} has no unit {n}"`, `"unit {n} of event {e} is erased and cannot be a source"`.

### Sources versus start: the start event is not a source today

- A relation's `sources` are the events it rests on (`Claim.sources`); the start (`body.start`) is a separate field.
  Form: `evidence = "sources"` needs at least one source; `evidence = "recollection"` has none (graph.py:275-292).
- Only `claim.sources` is locked (graph_write.py:615, 623), checked by `check_sources` (graph_write.py:476-478), cascaded on erasure and examined by `verify`. **The start event of an event-start relation would be none of these** unless the plan also puts it into `sources`. Nothing checks that `from.event` exists, is an observation, is not erased, or that `from.units` exist. A planner must decide: (a) require the start to be among the sources (then lock, `check_sources`, cascade, `verify` and the visibility rule follow for free), or (b) treat the start separately and add the checks.
- Erasure cascade: `core/redact.py:286-295 _assertions` finds assertions to erase with `sources_named(row.payload)` (`core/assertions.py:158`), which reads `payload["sources"]` only; `stands_on_erased(index, assertion_id, sources)` (`core/assertions.py:188`) decides. `from` is never read. So a `concerns` relation whose `from` names an erased event but whose `sources` do not is **not cascaded** and `verify` reports nothing (`core/verify.py:975-1003` also iterates `self._standing` sources only). With evidence `recollection` there are no sources at all.
- Visibility: `GraphView.verdict` decides a thread over the identities of its **sources' events** (`claim_sources(self._events, thread)`), and relations additionally over `relation_ends(thread)`, which are entity ids only. A start event that is not a source adds no decision: the policy would not look at the mail the assignment is about. §10.4 of the spec says an assignment may find but never release, which makes (a) the natural choice; but the plan must say it.
- `read_claim_events(log, conn, threads)` (graph_write.py:653) reads the events of `version.claim.sources` for the policy.

### Visibility (`claim_verdict`, `relation_visible`, `ThreadVerdict`)

- `claim_verdict(policy, client, identities, sources, *, recollection: bool) -> Decision` — graph_write.py:709. `claim_decisions(...)` (681) returns the per-source decisions; a recollection is decided as a source `recollection` without identities, held back until a rule `source:recollection` exists.
- `relation_ends(thread: GraphThread) -> tuple[int, ...]` — graph_write.py:737. Every entity any version names, candidates included.
- `relation_visible(policy, client, thread, ends: Mapping[int, bool | None], identities, sources) -> bool` — graph_write.py:750. Returns False at once if any version is not a `RelationBody` or has a `Source` start (the refusal to lift, item 10 in §1). Otherwise `verdict.chosen is not None and all(ends.get(end, False) is not False for end in relation_ends(thread))`. `ends[id] is None` means every version of that end is erased (withholds nothing).
- `ThreadVerdict(decisions, ends, blocked, shown)` — `mcp_server/read.py:840-858` (frozen dataclass); `GraphView` — read.py:862-956, `verdict(subject)` (887), `seen(subject)` (925), `rules`, `delivered`, `withheld`, `entity_types()` (949: entities that stand **and** that the client sees).
- Map point (landkarte): `GraphView.entity_types`/`EntityTypes`/`Graph.entities()` count open-only entities as standing; phase 2 `chronicle --in` must filter both ends and the edge by level (`reaches(levels=…)` exists for that).

---

## §3 The vocabulary (`core/vocabulary.py` 743 lines; `vocabulary.toml`)

- **`concerns` is not in the base file.** `src/previously/vocabulary.toml` declares (alphabetical): `entity.circle`, `matter`, `organization`, `person`, `post`, `project`; `relation.holds`, `in_circle`, `involved_in`, `member_of`, `part_of`, `post_in`. Ruling P-2 of the 2026-10-14 phase-1 plan (`docs/superpowers/sdd/2026-10-14-zuordnungen-phase-1/progress.md:35`): "the base vocabulary of phase 1 leaves out `concerns` … if wrong, phase 2 adds `concerns` with one `apply`, which the vocabulary is built for."
  `docs/reference/vocabulary.md:106`: "The relation `concerns` isn't in it, because it starts at an event."
- `KindSpec(declares, name, labels, fields, behaviors, from_: tuple[str, ...] | None, to: tuple[str, ...] | None, retired)` — vocabulary.py:~112-128. `from_`/`to` are **entity kind names**, `None` for an entity kind.
- **The vocabulary cannot say "event" or "any entity kind" for a non-built-in kind.**
  - `_reference_problem` (vocabulary.py:533-549): every name in `from`/`to` must be an entity kind that stands (`kinds.get((ENTITY_KIND, name))`, not retired), and `spec.declares == RELATION_KIND and (not spec.from_ or not spec.to)` -> `'relation kind "x" needs at least one kind in from and in to'`. So `from = []` is refused for a file-declared kind and `from = ["event"]` is refused because no entity kind `event` stands.
  - There is no wildcard for `to`; `concerns` to "any entity" would have to list every entity kind, and a kind the operator adds later would not be allowed.
  - Only a **built-in** kind escapes `_reference_problem` (vocabulary.py:571-573 `continue` for `BUILT_IN`).
- How `vocabulary.py` represents an event start today: only `in_circle`, built in (vocabulary.py:~218-227): `KindSpec(declares, name, labels, (), frozenset(), (), ("circle",), False)` — `from_=()` (empty tuple), commented "`in_circle` starts at an event, which is no entity kind, so `from_` is empty until phase 3 gives a relation that start." `member_of`'s `from_` is `("organization", "person")`.
  `BUILT_IN` = `{("entity","circle"), ("relation","member_of"), ("relation","in_circle")}` (vocabulary.py:~80); `GATE_TYPES` = their names; a built-in's shape lives in code (`_built_in`, vocabulary.py:~208) and `read_vocabulary` takes only labels from an event for it; `refusal`/`_built_in_problem` (vocabulary.py:552, 560) enforce "only its labels can change".
  The `vocabulary.toml` comment above `in_circle` says `from = []`; `parse_file`/`render_file` round-trip it.
- `_BEHAVIORS` (vocabulary.py:73-76): entity `{closable, period}`, relation `{transitive, acyclic, period}`.
- `base_vocabulary()` (vocabulary.py:634) reads the TOML package resource. `missing_kinds` / `apply --base` add only absent kinds (vocabulary.py:~498-520, 599): an operator on 0.1.0a7 gets `concerns` only by running `previously vocabulary apply --base`, and a **built-in** `concerns` would instead appear without any `apply`.
- Consequences for the plan: `concerns` as a file-declared kind needs a vocabulary extension (an "event" start marker and an "any" target); as a built-in kind it needs code (`BUILT_IN`, `GATE_TYPES`? no: `GATE_TYPES` is "the kinds the gate reads", and adding `concerns` there would make it never-transitive — do not add it casually) plus `_built_in` branch plus the "verify measures old statements at today's form" caveat (landkarte, M5).
- `conformance_problem` with a `Source` start must choose `spec.from_` semantic for the event case; `period`/`state` behave as for any relation.

---

## §4 Chronicle

### Projection `chronicle` (`core/projection/chronicle.py`, 144 lines)

- `ChronicleProjection(name: str = "chronicle", version: int = 3)`, frozen dataclass; `write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None` — chronicle.py:104-144. `CHRONICLE = ChronicleProjection()` (chronicle.py:144). Version history in the docstring: 2 since redactions are read, 3 since only observations.
- `derive(batch: Batch) -> list[ChronicleRow]` (chronicle.py:44): one row per unit **with content**, only for `event.kind == "observation"`; `source`/`external_id` from `batch.keys`, `evidence` from `payload["evidence"]` (None for a tombstone).
- `erasures(batch: Batch) -> list[tuple[int, tuple[int, ...] | None]]` (chronicle.py:78): from events of kind `action` whose `parse` (`core/redaction.parse`) succeeds, ignores a redaction that names an event `>=` its own id; `None` for scope `event`, the `units` tuple for scope `units`, nothing for scope `blob`.
- `write` inserts first (`store.insert_chronicle(conn, derive(batch))`), then deletes (`store.delete_chronicle(conn, event_id, seqs)` for each erasure).
- `ChronicleRow(event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker=None, start_ms=None, end_ms=None)` — `contract/rows.py:~93`.

### Schema (`storage/schema.py`, 268 lines)

```
p_chronicle: event_id BigInteger FK event.id NOT NULL, seq Integer NOT NULL, content Text NOT NULL,
  occurred_at timestamptz NOT NULL, kind Text NOT NULL, evidence Text, source Text, external_id Text,
  speaker Text, start_ms Integer, end_ms Integer; PRIMARY KEY (event_id, seq)
Index p_chronicle_occurred_idx (occurred_at, event_id, seq)       # schema.py:~250
p_source_stats: source PK, events, units BigInteger, first_seen, last_seen timestamptz, last_event_id FK event.id
projection_state: name Text PK, up_to_id BigInteger, version Integer, built_at timestamptz
```

Header comment schema.py:~203: projection tables "carry no foreign keys onto one another — only onto `event`". Prefix `p_`.
Other `event` indexes: `event_occurred_idx(occurred_at)`, `event_kind_occurred_idx(kind, occurred_at)`, `event_hash_idx` unique, `event_prev_hash_idx` unique NULLS NOT DISTINCT (schema.py:~94-120). `event.kind` CHECK `IN ('observation','assertion','action')` (`event_kind_check`).

### The worker (`core/projection/worker.py`, 170 lines)

- `Batch(events: tuple[EventRow, ...], units: Mapping[int, Sequence[UnitRow]], keys: Mapping[int, tuple[str, str]])` — worker.py:~23-31. `events` are **all kinds**, in chain order, with `payload` (None when erased).
- `Projection(Protocol)`: `name` (property -> str), `version` (property -> int), `write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None` — worker.py:~34-52.
- `Outcome(name, version, rebuilt_from: int | None, events: int, up_to_id: int)` — worker.py:~55.
- `catch_up[Conn](log: LogStore[Conn], store: ProjectionStore[Conn], projection: Projection, *, batch_size: int = 500) -> Outcome` — worker.py:~64-170. First transaction: `lock_projection_state(conn, name)`; if `state is None or state.version != projection.version` (any difference, both directions) -> `truncate_projection(conn, name)`, `set_projection_state(ProjectionState(name, 0, version, now))`. Then loop, one transaction per batch: lock the state row again (a different version here raises `ProjectionRebuilt`), `tip = log.tip(conn)`, stop when `tip.id <= state.up_to_id`, `events = tuple(log.read(conn, from_id=state.up_to_id + 1, limit=batch_size))`, verify the ids are exactly `up_to_id+1 …` else `ProjectionGap`, build `Batch(events, log.units_by_event(conn, ids), log.source_keys(conn, ids))`, `projection.write(store, conn, batch)`, `set_projection_state(replace(state, up_to_id=events[-1].id, built_at=now))`. Rows and `up_to_id` move in one transaction.
- Rebuild = `DELETE` of the projection's table (`truncate_projection` is a plain `DELETE`, not `TRUNCATE`) in place, no shadow table (landkarte *Projektionen* points).
- `previously project` (`cli.py:1459 _cmd_project`): `for projection in PROJECTIONS: outcome = catch_up(storage, storage, projection); print(f"{outcome.name:<15} {_describe(outcome)}")`. `_describe` (cli.py:326): `rebuilt: version A -> B, N events, up_to_id U` / `up to date, up_to_id U` / `built: N events, up_to_id U` / `caught up: N events, up_to_id U`.
- Who runs a catch-up: `previously project` (scheduled by the operator; `docs/how-to/rebuild-a-projection.md`) and every `previously redact` (`cli.py:1324 _catch_up_after`, loops `PROJECTIONS`, stops at the first failure — landkarte point; prints `{outcome.name:<15} {_describe(outcome)}` to stderr only when `rebuilt_from is not None`). **The MCP server (`mcp`, `serve`) never catches up and never reads a projection** (grep: `catch_up` appears only in `cli.py`).
- `PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)` — `core/projection/__init__.py:11`.

### Store protocol (`contract/store.py`)

`ProjectionStore[Conn]` (store.py:~120-160) has exactly these methods:
```
begin() -> AbstractContextManager[Conn]
lock_projection_state(conn, name: str) -> ProjectionState | None
set_projection_state(conn, state: ProjectionState) -> None
truncate_projection(conn, name: str) -> None
insert_chronicle(conn, rows: Sequence[ChronicleRow]) -> None
delete_chronicle(conn, event_id: int, seqs: Sequence[int] | None) -> None
source_stats(conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]
upsert_source_stats(conn, rows: Sequence[SourceStatsRow]) -> None
```
**No read method for a projection is in any protocol.** `PostgresStorage.read_chronicle`, `read_source_stats`, `tip_and_bookmark`, `projection_state` are methods "outside the protocols … only `cli` calls these" (storage/postgres.py:~920 comment; `core` never reads a projection back). `mcp_server` is typed against `LogStore[Conn]` (`build_server(log: LogStore[Conn], …)`, server.py:2464; `Service` server.py:833) and sits in layer `connectors | gate | mcp_server`, above `core` (`.importlinter` `layers`). Reading `p_*` from the MCP server therefore needs a new protocol (or a new method on an existing one) — and a `.importlinter`/pyright story — not just a table.
`WatermarkStore` is a separate protocol (store.py:~163), the template for "a protocol of its own".

### `PostgresStorage` (`storage/postgres.py`, 1249 lines; `class PostgresStorage` at :150)

- `_PROJECTION_TABLES: ClassVar[dict[str, Table]] = {"chronicle": p_chronicle, "source-stats": p_source_stats}` — postgres.py:724. `truncate_projection(conn, name)` does `delete(table)` for **one** table per name (postgres.py:~786-796); an unknown name raises `ValueError(f"unknown projection {name!r}")`. A projection with two tables does not fit this mapping.
- `lock_projection_state` (postgres.py:~748), `set_projection_state` (~775), `insert_chronicle` (~800), `delete_chronicle` (~824), `source_stats` (~838), `upsert_source_stats` (~854).
- `tip_and_bookmark(conn, name: str) -> TipAndBookmark` — postgres.py:926 (one statement, two scalar subqueries; the lag).
- `read_chronicle(self, conn, *, since: datetime | None, until: datetime | None, limit: int) -> list[ChronicleRow]` — postgres.py:964-996. Query: `select(p_chronicle)`, `occurred_at >= since`, `occurred_at < until`, `ORDER BY occurred_at, event_id, seq LIMIT limit`. No `source` filter, no cursor, no join. A bracket filter has to add either a join/`IN` against a new table or an `event_id` list.
- `read_source_stats(conn) -> list[SourceStatsRow]` — postgres.py:998.

### `previously chronicle` (`cli.py:1470-1521`)

- `_chronicle_arguments(parser)`: `--since` (ISO 8601 with zone, inclusive), `--until` (exclusive), `--limit` (`type=int, default=50`). Registered `Command("chronicle", "print the chronicle in time order", _cmd_chronicle, _chronicle_arguments)` — cli.py:4219.
- `_cmd_chronicle(args)`: refuses `--limit < 1` with `InvalidPayload("--limit must be at least 1, got N")`; `parse_moment` for the window; `position = storage.tip_and_bookmark(conn, CHRONICLE.name)`; `rows = storage.read_chronicle(conn, since=since, until=until, limit=args.limit + 1)`; prints `rows[: args.limit]` as `f"{row.event_id}\t{row.seq}\t{row.occurred_at.isoformat()}\t{escape_field(row.source or '')}\t{escape_field(row.external_id or '')}\t{escape_field(row.content)}"`; stderr `output truncated at {limit} lines; raise --limit or narrow --since/--until` when cut; then `_lag_line(tip_id, up_to_id)` on stderr when behind (silence means current).
- The CLI chronicle is **per unit** (one line per `(event_id, seq)`), so "a unit's own assignment replaces the event's" maps naturally onto `p_chronicle` rows.
- Tests that type the output: `tests/test_cli.py:1387-1590` (chronicle), `:1241` (control characters), `:2193-2230` (after redact), `:1316-1385` (`project` lines).

### MCP tool `previously` (`mcp_server/server.py`)

- Registered at server.py:2526 `@server.tool(name="previously", description=_CHRONICLE)`, signature: `previously(ctx: Context, circle: Annotated[str | None, _CIRCLE] = None, source: Annotated[str | None, _SOURCE] = None, since: Annotated[str | None, _SINCE] = None, until: Annotated[str | None, _UNTIL] = None, cursor: Annotated[str | None, _CURSOR] = None) -> CallToolResult`.
  `filters = cast("dict[str, str]", _given(circle=circle, source=source, since=since, until=until))` (`_given` drops `None`s); `call = ("tool", "previously", _given(**filters, cursor=cursor))` — this is what the access entry records; then `service.answer(request, protocol_version, call, lambda conn, policy, client: service.chronicle_page(conn, policy, client, filters, cursor))`.
- It does **not** read `p_chronicle`. `Service.chronicle_page(conn, policy, client, filters: Mapping[str, str], cursor: str | None) -> Answer` (server.py:1016) calls `mcp_server/read.py:366 chronicle(log, conn, policy, client, *, circle, source, since, until, after) -> Seen`, which loops `log.observations(conn, since=, until=, source=, after=position, limit=BATCH)` and `log.source_keys`, drops events failing the `circle` filter in Python (`circles_of(policy, _identities(row.payload))`; an erased event drops out), then `_decided` (policy verdict per event) and `log.units_by_event` for the events to show, accumulating until `size > PAGE_CHARS` (page full -> `Seen(reads, more=True)`).
  **The MCP chronicle shows whole events (all units, `_texts(units, None)`)**, not single units; the CLI shows single units.
- `LogStore.observations(conn, *, since, until, source, after: tuple[datetime, int] | None, limit) -> Iterator[EventRow]` — postgres.py:483-540: `WHERE kind='observation'` + window + optional EXISTS on `source_key` + `(occurred_at, id) > after`, `ORDER BY occurred_at, id`, server-side cursor. A bracket filter has no place in it: either add a parameter to the protocol method (changes `LogStore` and the docstring counts, see §5) or filter in Python in `read.chronicle` against a set of event ids (cost: `BATCH` windows can come back empty of matches; the loop continues until a page fills or the log ends).
- Cursor: `render.encode_cursor(after: int, filters: Mapping[str, str], *, page: int = 2) -> str` (render.py:594) — base64url JSON `{"after": id, "filters": {...}, "page": n}`; `decode_position(cursor, filters) -> Position(after, page)` (render.py:617) raises `ValueError(CURSOR_REFUSED)` unless `recorded == dict(filters)` exactly. So a new filter `in` becomes part of `filters` and of the cursor, and **`filters` values are `str`** (`Mapping[str, str]`): an entity id must be stringified or the cursor type widened. `resume_point(log, conn, event_id) -> (occurred_at, id) | None` (read.py:415) looks the time up in the log (`log.read(conn, event_id, 1)`).
  The page title is `" · ".join(["chronicle", *(f"{key} {value}" for key, value in filters.items())])` (server.py:1060): a filter named `in` would print `chronicle · in 12`.
- Description text `_CHRONICLE` (server.py:274-282) says "The filters combine: circle …, source, since and until." The tool list is pinned: `tests/test_mcp_server.py:881 TOOLS_SHA256 = "0a0ca06505…"` over name, description, inputSchema and `_meta` of every tool (`test_the_tool_list_matches_its_checksum`, test_mcp_server.py:~893). Adding `in`, or touching the description, changes the digest on purpose; `docs/reference/mcp-tools.md:244-259` (the `previously` argument table) must follow; `INSTRUCTIONS` is held by sentence in `tests/test_mcp_server.py:~925`.
- Also built on the chronicle: resource `previously://circle/{name}/chronicle` and prompts `chronicle_summary` / open-items prompt (`docs/reference/mcp-tools.md:770, 787-799`).

### How the chronicle follows erasure

- CLI projection: units without content give no row (`derive`), and a redaction in the batch deletes rows (`erasures` + `delete_chronicle`), insert-then-delete order so a batch boundary makes no difference (docstring chronicle.py:104-115; test `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker`, `tests/test_projection_worker.py:328`, and `test_an_order_without_its_execution_ends_alike_on_both_paths`, :359).
- MCP: reads the log directly, so an erased event is `_decided` -> `ErasedMark` (read.py:314-320), and a `circle` filter drops it.
- A new projection fed by **assertion** events has no equivalent yet: an assertion erased by the cascade (`core/redact.py:298 _cascade_assertions`) gets a `redaction` action (scope `event`, `reason = "cascade of redaction {trigger}"`, written with `write_action` before `eraser.erase_payload`) and its payload set to NULL; a projection that folded the assertion earlier must delete what it derived from it when it reads that redaction, as the chronicle does for units. The graph fold has no removal (§1), so the design is "state derived per assertion row, deletable by row id", not "a GraphFold persisted".

---

## §5 What a new projection takes end to end

Measured by reading `p_chronicle`/`p_source_stats`, tests and docs. Every item is an edit the change has to carry:

1. **Table in `storage/schema.py`**, prefix `p_`, FK only onto `event`, `metadata` object; plus `Index` objects.
2. **Alembic migration** `src/previously/migrations/versions/0006_….py` (head is `0005_watermark`, `down_revision = "0005_watermark"`); hand-written `op.create_table` / `op.create_index` mirroring `schema.py` (template: `0002_projections.py` for projection tables, `0005_watermark.py` for the shape of a small forward migration with a guarded `downgrade`). Dropping a projection table loses no truth, so `downgrade` can drop without a refusal (0002's downgrade does).
   - **The "projection tables are created by code, not by a migration" note is not what the tree does.** It stands in the frozen architecture record `docs/superpowers/specs/2026-10-01-architektur.md:954-958`: "> **Alembic migriert `event`, `source_key`, `unit`, `job` und `projection_state`. Projektionstabellen (`p_*`) werden von Code erzeugt und verworfen, nicht migriert.**" The tree contradicts it: `src/previously/migrations/versions/0002_projections.py` creates `projection_state`, `p_chronicle` (with `p_chronicle_occurred_idx`) and `p_source_stats` with `op.create_table`, and its docstring says "A forward migration … the three tables are derivable and disposable; dropping them loses no truth, and `previously project` builds them again from the log." The 1b spec §4.3 (`specs/2026-10-04-stufe-1b-projektionen.md:360-367`) draws the line the code follows: a version bump is "keine Migration, kein Handgriff", but "Die Tabellen**struktur** ändert sich dabei nicht; eine Strukturänderung bleibt eine Alembic-Migration, wie bei jeder anderen Tabelle." The landkarte (*Projektionen*, first point) states the cost: "Eine neue Projektion kostet Methoden im Store-Protokoll, ihre SQL-Umsetzung und eine Migration — nicht nur eine Versionsnummer". The phase-1 plan chose "no projection tables, no migration" (`specs/2026-10-12-pilot-feststellungen.md:24`, and for the graph by ruling F-c); that is a decision not to build one, not a rule against.
3. **Contract**: row dataclass(es) in `contract/rows.py` (like `ChronicleRow`, `SourceStatsRow`); new methods on `ProjectionStore` in `contract/store.py` (insert/delete/upsert, and any read the MCP side needs — which has no protocol today, see §4).
4. **`PostgresStorage` methods** (postgres.py) and an entry in `_PROJECTION_TABLES` (postgres.py:724) — one table per name; the `truncate_projection(name)` empties exactly that table.
5. **Projection module** under `core/projection/` (`derive`/`merge` pure, `…Projection` frozen dataclass with `name`, `version`, `write`), the constant, and the `PROJECTIONS` tuple in `core/projection/__init__.py:11` (order fixes the order of the `project` output lines and of `_catch_up_after`).
6. **CLI**: nothing new is needed for catching up (`_cmd_project` and `_catch_up_after` loop `PROJECTIONS`), **but the output grows by one line per projection**: every typed `project` output and every `redact` stderr that lists `chronicle`/`source-stats` lines changes. Pinned in `tests/test_cli.py:1316-1325, 1349-1366, 1381-1382, 1946-1947, 2096-2097, 2403, 2432-2437, 3328`; typed in docs at `docs/tutorials/record-your-first-event.md:151, 160`, `docs/how-to/ingest-a-mail-folder.md:66`, `docs/reference/cli.md:794-826 (## project)`, `docs/how-to/rebuild-a-projection.md`, `docs/how-to/set-a-policy-and-try-a-call.md:38-41`.
7. **Tests that hold metadata and migrations equal** (`tests/test_schema.py`):
   - `test_the_declared_indexes_exist_in_the_migrated_database` (:267): every `Index` in `metadata` is in `pg_indexes` after `alembic upgrade head` (one direction only; a name cannot carry `NULLS NOT DISTINCT`, which `test_the_declared_nulls_not_distinct_reaches_the_database` (:315) holds).
   - `test_the_declared_columns_match_the_migrated_database` (:483): for **every** table in `metadata`, the columns with `NOT NULL` equal the database's, and the CHECK constraint names equal. Automatic for a new table.
   - `test_the_projection_tables_exist` (:519): hard-codes `{"projection_state", "p_chronicle", "p_source_stats"} <= names` and docstring "Stage 1b adds three tables"; a `<=`, so it stays green with a fourth table but its text will be stale.
   - `test_the_watermark_table_is_declared_and_migrated` (:539) is the model for a PK check of a new table.
   - `tests/conftest.py:62 TRUNCATE_ALL` is derived from `metadata.sorted_tables`, so the `db` fixture empties a new table with no edit. `engine` (conftest.py:65) runs `command.upgrade(config, "head")` once per session, so a migration is exercised by every db test.
   - A per-migration test in the style of `tests/test_migration_0005.py` (own container, `postgres()` from `tests/database.py`) only if the downgrade refuses something. `tests/test_migrate.py:43 _head()` reads the head from the tree, no edit.
   - `tests/test_projection_worker.py`: `_snapshot` (:71) returns two tables only (`p_chronicle`, `p_source_stats`) — add the new table to hold `test_incremental_equals_rebuilt` (:99) and the property test (:548) for it; `_project_all` (:82) and `_force_rebuild` (:87) already loop `PROJECTIONS`.
   - `tests/test_projection_store.py:177 test_postgres_storage_satisfies_both_protocols` is the pyright-proof for `ProjectionStore`.
   - `tests/test_projection_derive.py` (pure derive tests, no db).
8. **Docs that name the tables**: `docs/reference/database-schema.md:5-10` ("eight PostgreSQL tables … Three hold projections …", "declares all eight", a mermaid caption, one `## p_…` section per table with a constraints table (:156-196)); `docs/explanation/projections.md:5` ("Stage 1b adds three tables"); `docs/reference/cli.md:104-106, 122, 128` and `docs/how-to/run-the-image.md:65` type `migrated: … -> 0005_watermark` (the revision name appears in typed output, `previously migrate`); `docs/how-to/add-a-migration.md` is the procedure. `tests/test_docs_typed_output.py` holds only the `N passed` number of `docs/tutorials/record-your-first-event.md:200, 283` (currently `collected 2650 items` / `2650 passed in 282.77s`) against `--collect-only`; every added test moves it; retype the whole block last (CLAUDE.md "Typed-out output").
9. **Docstring counts in `contract/store.py`** (module docstring, :4-52): "`LogStore` is … fifteen methods, counted on 2026-10-12 by this command … and fifteen on 2026-10-14", "The protocol declares sixteen: `observations` …", "names the eight the server calls … counted on 2026-10-14". Measured now at 0bfb228: the grep (`grep -ohE '(storage|log)\.[a-z_]*\(' $(grep -rl LogStore src/previously/core) | sed 's/.*\.//' | sort -u | wc -l`) gives **15**; `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py | sort -u` gives **8** (`begin, observations, read, read_by_kind, snapshot, source_keys, tip, units_by_event`); `LogStore` declares **16** methods. Adding methods to `ProjectionStore` moves none of these counts. They move if `core` calls a new `LogStore` method (e.g. a bracket parameter on `observations` changes only the signature, a new method changes 16) or if `mcp_server/` calls another `log.` method. If the MCP side reads a projection through a new protocol typed beside `log`, the "eight" sentence is unaffected but should be reread.
   `tests/test_docs_references.py` has number-word lists (:1927-1949: "eight", "eighteen", "fifteen", "sixteen") used by a count checker; sentences with those words in docs are checked there (see the test for the exact rule before adding a count word near code).

---

## §6 Reading the log incrementally

- `LogStore.read(conn, from_id: int, limit: int) -> Iterator[EventRow]` — contract/store.py (protocol); postgres.py:412: `WHERE id >= from_id ORDER BY id LIMIT limit`, server-side cursor (`stream_results=True, yield_per=100`). **All kinds**, each `EventRow` with `payload` (None if erased).
- `read_by_kind(conn, kind: str) -> Iterator[EventRow]` — postgres.py:443: `WHERE kind = :kind ORDER BY id`, no `from_id`, no limit: **always from the beginning**. `read_graph` therefore re-reads every assertion on every call. An incremental reader of assertions has only `read(from_id, limit)` (all kinds) today; a `read_by_kind` with `from_id` does not exist.
- `actions(conn, action: str) -> Iterator[EventRow]` — postgres.py:461: `WHERE kind='action' AND payload->>'action' = :action ORDER BY id`. "No index serves the filter: the database still visits every action."
- `events_by_id(conn, ids)` (postgres.py:424) one query; `units_by_event(conn, ids)` (:542); `source_keys(conn, ids)` (:599); `count_events` (:587); `lookup(conn, source, external_id) -> int | None` (:314); `tip(conn) -> Tip | None`.
- **Indexes**: `event_kind_occurred_idx (kind, occurred_at)` serves `kind = …` filtering (not the `ORDER BY id`); there is **no index on `payload->>'assertion'`** or on any payload key (`grep -rn "gin\|->>'assertion'\|astext" src` finds only the `actions` `payload['action'].astext` filter). `schema.py` has exactly the four `event` indexes listed in §4 plus `event_blob_sha256_idx`.
- Assertion rows (`kind='assertion'`) carry `occurred_at = recorded_at` of the write (`_append` in graph_write.py:564 passes `occurred_at=recorded_at`), `units=()`, `key=None` — so they have no unit rows and no `source_key` row.
- Erasure of a row: `RedactionStore.erase_payload(conn, event_id)` sets `payload` and `payload_salt` to NULL (SQL NULL via `null()`, since JSON `null` is refused by `event_payload_object_check`); `erase_units(conn, event_id, seqs)` sets `content, salt, speaker, start_ms, end_ms` of the named units to NULL; digests stay (the chain depends on them). The row is **updated in place**: a projection that already consumed it never sees a new row for it.
- **Which event records an erasure**: an event of kind `action` with `payload.action == "redaction"` (`core/action.py:49 REDACTION`), payload form `{"action": "redaction", "scope": "event"|"units"|"blob", "target": {…}, "reason": …}` (`core/redaction.py:event_payload, units_payload, blob_payload`; parsed by `redaction.parse(event_id, payload) -> Redaction(id, scope, reason, event, units, blobs, blob, events)`). Scope `event`: `target = {"event": id, "blobs": [sha256…]}`; scope `units`: `target = {"event": id, "units": [seq…]}`. It is **written before** the tombstone is set, in the same transaction (`redact_event` redact.py:419+: `write_action` then `erase_payload` / `erase_units`). The cascade writes one `scope: event` redaction per erased assertion (reason `cascade of redaction {id}`) and a `scope: units` one per model call.
  `redact_units` of an observation leaves the observation's payload alone and erases unit content only; an assertion that cites that unit is erased by the cascade (units cited) or, for a source cited whole, when a unit of it was erased after the assertion (`stands_on_erased`).
- `RedactionIndex` / `read_index(log, conn)` (`core/redaction.py`) indexes all redactions by event/unit — used by `verify`, the cascade and `stands_on_erased`.
- The chain has no gaps (`id = predecessor.id + 1`), which is what lets `catch_up` read `from_id = up_to_id + 1` and detect a gap (`ProjectionGap`).

---

## §7 The IMAP ingest and `found_in`

- `core/mail.py:191 map_mail(raw: bytes, *, internaldate: datetime, found_in: Mapping[str, str]) -> Mapped`; the payload carries `"found_in": dict(found_in)` (mail.py:255, 309) and `"internaldate"`. The event hash covers the payload, so `found_in` is part of the event (immutable); it is **not** part of the artifact hash: `artifact_hash_of({"subject", "body": [sha256…], "attachments": […]})` (mail.py:292-297, `core/identity.py:19`).
- `connectors/imap.py:107` `self.name = f"imap:{user}@{host}/{folder}"`; `_fetch` (imap.py:~198) builds `position = {"uidvalidity": validity, "uid": str(uid)}` and `found_in={"connector": self.name, **position}` (imap.py:225). `Fetched(raw, position, found_in, internaldate)` — `contract/types.py:~120-135`. The watermark is per connector name = per folder (`Watermark(connector, position, set_at)`).
- `core/ingest.py` (337 lines): `ingest(log, marks, blobs, connector, *, recipient, recorded_at) -> Ingested(appended, known, variants, position)`. `_Run.take` maps each fetched mail; `_take` -> `_resolve(event)` -> `_holds(event)`: key `(source, external_id)` in the batch (`in_batch`) or in the log (`known_id(log, conn, event)` returns the existing event id or None; raises `ArtifactChanged` when the artifact hash differs, then the event becomes a **variant** under `variant_key` and is written as a new event).
  **The known case** (same Message-ID, same artifact hash, e.g. the same mail in a second folder or a second copy in one folder): `_take` does `else: self.known += 1` and nothing else — no event, no blobs, no assertion. `_holds` returns only a bool (`known_id(...) is not None`), so the **id of the known event is discarded**; the `found_in` of the second sighting is dropped on the floor. Recursion continues for the `mapped.inner` mails. `flush()` writes the batch via `append(...)` and then the watermark; a mail seen in a second folder advances that folder's watermark and leaves no trace of the sighting.
  `Ingested.known` counts **events**, not mails, "the events it found already in the log or earlier in the same batch", plus `append`'s own "key another writer appended since the lookup comes back with its own" (`event_id <= before` in `flush`).
  CLI line: `imap: {appended} appended, {known} known, {variants} variants, up to uid {uid} in {folder}` (`cli.py:~866`).
- What a second find-spot needs (facts, not design): (1) in `_take`, the id of the known event (change `_holds`/`known_id` use to keep it) and the second sighting's `found_in` (`event.payload["found_in"]`); (2) a place that says which entity ("bracket") the folder stands for — see below; (3) a write through `core/graph_write.write_claims` from inside or after the run (ingest today knows `LogStore`, `WatermarkStore`, `BlobStore`, `Connector`; `core.ingest` may import `graph_write`, same layer); the claim's `sources` need an `observation` (the known event is one, unless erased); (4) the first sighting of a **new** mail in a folder with a bracket would write the assignment too (the event id is only known after `append` returns the ids, `flush()` pairs `entries` with `ids` via `zip`); (5) idempotence: a `handle` on the claims makes a repeated batch a repeat (`_repeated`, graph_write.py:516) — a stable handle per (event, folder) would make a re-run write nothing; (6) the level: ingest is no model and no operator; `_levelled` gives the operator's claims `direct` (author `OPERATOR`, `core.assertion.OPERATOR`) and a model's `open/transitive`; what author an ingest run would write as is undecided (spec §8 leaves it to the plan).
- **`--folder`**: `cli.py:735-745 _ingest_arguments` adds `--folder NAME` (`action="append"`, `metavar="NAME"`, help "a folder to read, by its full name; repeatable, and in place of PREVIOUSLY_IMAP_FOLDER"); `_imap_connectors(named)` (cli.py:~770-800): refuses `""`, reads `PREVIOUSLY_IMAP_ADDRESS/USER/PASSWORD`, `folders = named if named is not None else [_setting("PREVIOUSLY_IMAP_FOLDER")]`, de-duplicates with `dict.fromkeys`, one `ImapConnector` per folder. `_cmd_ingest` (cli.py:~803-870) loops connectors; a failing folder prints `Error: folder {folder}: …` and the run returns 2 at the end.
- **There is no per-folder setting at all** besides the folder's name and its watermark: nowhere to name a bracket. Settings: `PREVIOUSLY_IMAP_FOLDER` (single value, `docs/reference/configuration.md:118`), `--folder NAME` (name only). The natural carrier is a new option (e.g. `--folder NAME=ENTITY`, or a mapping table/setting) — new surface, new docs (`docs/reference/cli.md:219-228`, `configuration.md:118-132`, `how-to/ingest-a-mail-folder.md`, `explanation/connectors.md:130`: "Which project or customer a mail belongs to is an assignment, an assertion … and it waits for the unit of work that brings assertions.").
- `mcp_server/read.py:283-295 _provenance` prints `Found in: connector …, uid …, uidvalidity …` from `payload["found_in"]` (only the first sighting).
- Landkarte (*Feststellungen und Entitäten*): "Weitere Fundorte: dieselbe Mail in einem zweiten Ordner schreibt nichts, nur der erste Fundort steht im Log, unter `found_in`. Mit den Zuordnungen wird das Ablegen eine Zuordnung, und die kann mehrfach sein (PI §3.4, §11 Punkt 2; `connectors.md`)."

---

## §8 MCP header and per-call cost

- `Service.answer(request, era, call, body)` — server.py:894-946: inside `with self.log.snapshot() as conn:` it does `policy = read_policy(self.log, conn)`, resolves the client, then **`graph = read_graph(self.log, conn)`** (server.py:933) and `_FOLDED.set(_Folded(graph, objections_seen(self.log, conn, policy, client, graph)))` (server.py:934-936), then runs `body(conn, policy, client)`; afterwards `self.record(...)` writes an `mcp_access` action (so every call moves the tip). This happens **for every tool, `whoami` and the chronicle included**; it is on the path of `previously`.
- `_Folded(graph: Graph, objections: int)` — server.py:739-745; `_FOLDED: ContextVar[_Folded | None]` — server.py:756; `_pending() -> int` — server.py:759 (read by `render_page(…, objections=_pending())` for the header line `· N objections pending`).
- `Service.graph_now(conn) -> Graph` — server.py:1609: `_FOLDED.get()` -> `folded.graph`, else `read_graph(self.log, conn)` (outside a call). Users: `assertion_page`-style graph tools at server.py:1548, 1592 (`graph=self.graph_now(conn)`), `graph_of` (1616).
- `objections_seen(log, conn, policy, client, graph) -> int` — read.py:982: `waiting = {s: t for s, t in graph.threads.items() if t.objections(graph.classes)}`; returns 0 without further reads if none; else `graph_view(log, conn, policy, client, graph, waiting)` (reads source events of the waiting threads and their entity ends in two queries) and counts `thread.objections` of those the client `seen`.
- Cost model (measured by the phase-1 final review, 2026-10-14; `docs/explanation/graph.md` (graph-cost), landkarte *Zuordnungen*): fold of the whole graph 0.08 s @ 2,000 relations, 0.47 s @ 10,000, 7.35 s @ 100,000 (median of three); every MCP call pays it; MCP `whoami` 7.69 s, `list_entities` 23.7 s @ 100,000. "A cache keyed on the tip of the chain would not help, since every call writes its own access entry and moves the tip."
  What the cost contains per call: `read_classes` (all `approval_class` actions), `read_by_kind('assertion')` (every assertion row incl. payload), the Python fold, `graph.threads` winner computation inside `objections` for every thread.
- **There is no per-process cache** anywhere: `grep -rn "lru_cache\|functools.cache\|@cache\|_cache"` over `src` finds nothing but `cache_hints=_CACHE_HINTS` (server.py:607, MCP resource cache hints, `ttl_ms=0`). `Service` holds no state between calls (fields: `log`, `stdio_client`, `locker`, `key`, `language`, server.py:833-858). `serve` can run as several processes/pods; a per-process cache would need invalidation by watching the tip/class events.
- `tests/test_mcp_server.py:4155-4190 _CountingFolds` / `test_a_call_folds_the_graph_once_for_its_header_and_its_body` pins **exactly one `read_by_kind("assertion")` per call** for `list_entities`, `list_entities {subject}`, `list_triage`, `whoami` (`assert counting.folds == 1`). A projection or an incremental fold that stops reading assertions per call breaks this test on purpose (its docstring cites ruling T6-c); it needs a new assertion of what a call reads.
- Policy read per call: `read_policy` -> `log.actions(conn, "policy")` (every policy action); `core/clients.py` reads client dates the same way; these also scale with the log of actions, not with assertions.

---

## §9 Tests

### Helpers and fixtures for graph tests

`tests/test_graph_write.py` (1307 lines), module-level, all importable by copy (no shared module; conftest.py has only `engine`, `db`, `truncate_statement`, `write_version_1` and the IMAP/S3 fixtures):
- constants `T0..T3`, `MODEL = model_author("claude")`, `ADDRESS`, `CLASS`/`EDGES` (`ApprovalClass`), `TEAM`/`LEADS` (`KindSpec`) — :100-148.
- `_mail(external_id) -> RawEvent` (two units "One."/"Two."), `_setup(db, mails=3) -> PostgresStorage` (appends mails, applies the base vocabulary plus `team`/`leads`) — :150-168.
- builders: `entity(kind, name, *, author, responsibility, evidence, sources=(Source(1, None),), subject, approves, confidence, handle, state, fields) -> Claim` (:171), `guess(kind, name, *, confidence=90, **changes)` (:203), `relation(kind, start, to, *, author, responsibility, sources, subject, approves, confidence, candidates, period, state) -> Claim` (:210; `start: int`), `edge(start, to, …)` (:242, the operator's `part_of`), `model_edge(…)` (:254).
- actions: `_write(storage, *claims, at=T1) -> Written`, `_ids`, `_refused(storage, *claims, at, expect) -> str` (asserts nothing was written), `_checked`, `_graph(storage, *, as_of)`, `_count`, `_projects(storage, count)`, `_retire_team`.
- models of the concurrency tests: `_MeetingAtTheTip(PostgresStorage)` (:1111), `test_two_writes_that_each_close_half_a_cycle_cannot_both_stand` (:1134).
- A test for an event-start relation can build one with `replace(edge(1, 2), body=RelationBody("part_of", Source(1, None), 2, None, None, {}, STANDING))` as `test_a_relation_that_starts_at_an_event_closes_no_cycle` does (:1099).
`tests/test_graph.py` (1600 lines): pure-form and fold tests; its own `relation(start=…)`, `edge(...)`, `row(...)`, `conformance(claim)` helpers (:242, :1328, :1400).

`tests/test_mcp_server.py` (4226 lines): `World(storage, tokens, ids, policy_event)` (:168), `_world(db)` (:217; policy with circles huber/office/bauer/team, clients `claude-code` (processor `claude-max`) and `local-harness` (`local`), seven mails from `tests/mailfiles` (`ids` by name), one redacted), fixture `world` (:242), `_take_in(storage, raw, *, internaldate)` (:177), `_session(server, mode, use)` (:250; `MODES`), `_tool(world, mode, name, arguments, *, client="claude-code")` (:258), `_text(result)` (:270, holds the one-text-block form), `_accesses`, `_last_access`, `_shown_ids(page)` (:291), `_untagged`; graph block: `Graphed(anna, treasurer, lea, holds, secretary)` (:3094), `_person`, `_office`, `_graphed(world)` (:3126), `_relate(world, start, to, *, source, period, kind)` (:3143), `_entity_item`, `_question_item`, `_graph_payloads`, `_header(result)` (:3200 first line), `_circle` (:3746), `_project` (:4046); `_CountingFolds` (:4155); `TOOLS_SHA256` (:881) and `tool_list_digest`.
Chronicle over MCP tests: grep `"previously"` / `_shown_ids` / `cursor` in `tests/test_mcp_server.py` (cursor helpers `_decoded` :1437, `_team_mail` :1427, `_long_mail` :630).

### Chronicle and projection tests

- `tests/test_chronicle.py` (89 lines): `_observation()`, `_rows(db)`, `_write_both(storage)`; two tests (action units not in the chronicle; the upgrade to version 3 rebuilds).
- `tests/test_projection_worker.py` (818 lines): `_raw(n, source, occurred_at)`, `_snapshot(db)` (two tables), `_project_all`, `_force_rebuild`, `test_incremental_equals_rebuilt` (:99), `test_a_version_bump_rebuilds_and_without_it_nothing_moves` (:143), `test_an_abort_leaves_rows_and_up_to_id_in_step` (:225, `_FailingStore` :183), redaction equality tests (:328, :359, :390), `test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild` (:548, hypothesis; `_Append`, `_CatchUp`, `_Redact`), lock-order tests (`_PausingStore` :613, `_HoldingFirstLock` :703), `test_a_catch_up_stops_when_another_release_rebuilds_under_it` (:802).
- `tests/test_projection_store.py` (202 lines): per-method store tests, protocol-satisfaction proofs (:177-202).
- `tests/test_projection_derive.py` (182 lines): pure derive/merge.
- `tests/test_cli.py` (7456 lines): `project`/`chronicle` blocks at :1241, :1316-1385, :1387-1590, :1946, :2096, :2193-2230, :2262-2297, :2364-2459, :3328. CLI tests call `main([...])` with env set by fixtures at the top of the file.
- DB tests are marked `@pytest.mark.db` and take the `db` fixture (testcontainers PostgreSQL, one container per session, `TRUNCATE_ALL` per test).

### Count

`uv run pytest --collect-only -q | tail -1` -> `2650 tests collected in 6.60s` (2026-10-14, 0bfb228).

---

## §10 The map's phase-2 points (`docs/superpowers/landkarte.md`, verbatim)

Section *Zuordnungen (Phasen 1–4)* starts at landkarte.md:457. The points that concern phase 2 or the projection:

> - **Jeder MCP-Aufruf faltet den ganzen Graphen für die Zahl im Kopf.** Um die anhängigen Einwände zu zählen, faltet `Service.answer` vor jedem Werkzeug den Graphen und fragt die Policy nach den Quellen jedes Einwands, auch bei `whoami` und den Werkzeugen der Einheit 5, die den Graphen sonst nie lesen. Gemessen von der Endprüfung am 2026-10-14, Median aus drei Läufen, bei 10 000 Beziehungen und 5 000 Entitäten: `whoami` 0,52 s, `list_entities` 1,72 s, `read_graph` 0,47 s, `previously entities` 0,53 s, ein Schreiben 0,47 s, `verify` 2,77 s; bei 2 000 Beziehungen `whoami` 0,10 s, `list_entities` 0,28 s, `verify` 0,62 s. Bis 10 000 wächst es linear. Bei 100 000 Beziehungen und 50 000 Entitäten, auf festem Stand von `9967268` (i7-11370H): `read_graph` 7,35 s (Median aus drei), in Einzelläufen `whoami` 7,69 s, `list_entities` 23,7 s, mit 20 Einwänden 7,33 s und 24,2 s; aus dem ersten Lauf `entities` 7,59 s, `relations --at` 7,50 s, ein Schreiben 7,34 s — sechzehnmal so lang für zehnmal so viel. Bei 10 000 tragen Listen, Schreiben und Kopf noch, `list_entities` liegt mit 1,7 s schon über einer Sekunde; bei 100 000 trägt keins davon. Phase 1 nimmt die Kosten hin (Ruling F-c): ein Zwischenspeicher, der am Tip hängt, verfällt mit dem Zugriffseintrag jedes Aufrufs, und beim Piloten mit einigen hundert Aussagen sind es Millisekunden. **Phase 2 braucht eine Projektion oder eine inkrementelle Faltung, bevor die Daten wachsen** (Planentscheidung 14, Z §3.4); `explanation/graph.md` trägt die Zahlen. Die Messungen der Aufgabe 6 (`whoami` bei 1 000 Entitäten ohne Beziehungen 53 ms, bei 5 000 153 ms) stehen dort daneben.

> - **`verify` wächst überlinear über azyklischen Kanten, etwa quadratisch.** … wächst der Graph weit darüber, wird die Prüfung auf Zyklen in `verify` inkrementell, spätestens mit Phase 2.

(Figures in that point: chain 1 000 edges 0,84 s, 2 000 2,34 s, 5 000 14,84 s; tree 0,78 s, 2,10 s, 13,05 s; a chain of 10 000 edges 78,6 s, one run; whole log of 100 000 relations 135 s.)

> - **Offene Enden und offene Kanten zählen als stehend.** `EntityTypes` (`graph_write.py`) und `Graph.entities()` geben auch Entitäten zurück, die nur ein Modell vorgeschlagen hat, und `relations()` offene Gewinner. Eine direkte Beziehung des Betreibers oder eine Freigabe kann also auf eine nur vorgeschlagene Entität zeigen, auch ein direktes `member_of` auf einen vorgeschlagenen `circle`. In Phase 1 harmlos. Phase 2 (`chronicle --in`) und Phase 3 (das Gate) müssen beide Enden und die Kante nach Stufe filtern; das Gate liest nur direkte Enden (P-Z1, Endprüfung M4).

> - **Ein Ereignis als Beginn einer Beziehung, was Phase 2 ändern muss.** Die Form (`RelationBody.start: int | Source`) nimmt es schon an, `conformance_problem` weist es in Phase 1 mit einem Satz ab, und `reaches`, `closes_cycle`, `relation_ends` und `relation_visible` überspringen es. Phase 2 ändert: die Abweisung und den `int`-Cast in `_ends_conformance`, `EntityTypes` und die Enden, und `relation_visible`, das für jeden Source-Beginn `False` gibt (P-Z1, Endprüfung).

> - **Die eingebauten Arten stehen im Code, `verify` misst alte Aussagen an der heutigen Form.** `VocabularyFold.add` ersetzt die Form einer eingebauten Art an jeder Stelle durch die des Codes. Gibt Phase 3 `member_of` weitere `from`-Arten (Adresse, Domain) und `in_circle` ein Ereignis als Beginn, wird jedes frühere `member_of` am neuen Code gemessen; nimmt sie `person` oder `organization` aus `from`, werden Mitgliedschaften der Phase 1 zu Befunden. Unter Phase 3: die Verbindungen einer eingebauten Art dürfen nur wachsen, oder ihre Form bekommt eine Version (P-Z1, Endprüfung M5).

> - **Triage, Freigabe und Antwort stehen zweimal, je Oberfläche einmal.** `cli.py` `_waiting` entspricht `mcp_server/read.py` `waiting_versions`, `_approval_of` dem `replace(…)` in `graph_approval_write`, die Antwort in `cli.py` der in `triage_answer_write`. … (P-Z1, Endprüfung M8).

> - **Der Platzhalter einer verborgenen Entität verschwindet, wenn ihr letzter Vorschlag abgelehnt wird.** … Seit dem Zweig `worktree-rueckmeldung-a7` bleibt der Platzhalter einer verborgenen, widerrufenen Entität unter jedem Filter stehen, mit Absicht (Option A des Betreuers).

> - **`cli.py` teilen.** 4 274 Zeilen zur Endprüfung; die Befehle des Graphen stehen in einem Block (etwa Zeilen 2 995–3 950) und könnten ohne Verhaltensänderung `previously/cli_graph.py` werden (P-Z1, Endprüfung).

> - **Phasen 2 bis 4 selbst**, im Spec ausgearbeitet und nicht gebaut: die Zuordnung von Events und Einheiten an Klammern mit `chronicle --in` und `in` über MCP (Z §8, Phase 2), Kreise im Graphen, die das Gate liest, mit der schweren Prüfung der Sicherheitsgrenze (Z §9, Phase 3), und Verpflichtungen und Entscheidungen im Schema (Z §11, Phase 4). Jede mit eigenem Plan, Merge, Release und Abnahme (Z §1, §17); die Relationen `concerns` und `in_circle` mit Ereignis als Beginn kommen mit Phase 2 (P-Z1, Ruling P-2).


Points in *Feststellungen und Entitäten* (landkarte.md:374+) that concern phase 2:

> - Zuordnung zu Projekten: `p_chronicle` bekommt `project`, der Index seine erste Spalte (1b §10 Punkt 6, AA §10 Punkt 9).
> - Weitere Fundorte: dieselbe Mail in einem zweiten Ordner schreibt nichts, nur der erste Fundort steht im Log, unter `found_in`. Mit den Zuordnungen wird das Ablegen eine Zuordnung, und die kann mehrfach sein (PI §3.4, §11 Punkt 2; `connectors.md`).
> - Projekt als Geltungsbereich einer Regel: `project:<name>` ist vorgesehen, und der Schreibweg weist es ab, bis es eine Zuordnung von Events zu Projekten gibt (PG §2.3, §11 Punkt 3; die Zuordnungen, F §1).

(The first of these is superseded by spec §10.1: "Der alte Punkt, eine Spalte `project` in `p_chronicle` (1b §10 Punkt 6), entfällt: ein Event gehört zu mehreren Klammern, das ist eine Verknüpfung, keine Spalte.")

Points in *Projektionen* (landkarte.md:598+) that bear on a new projection:

> - Eine neue Projektion kostet Methoden im Store-Protokoll, ihre SQL-Umsetzung und eine Migration — nicht nur eine Versionsnummer; `write_projection(name, rows)` aus der Architektur wurde zu getypten Methoden je Tabelle, ohne aufgeschriebenen Grund (PP, A1 Zeile 30 und S5; A2, §10.1).
> - Neubau an Ort und Stelle statt Schattentabelle mit Umschaltung; ein Leser sieht während des Neubaus eine leere oder halbe Projektion. … Gemessen bei 700 000 Events: der Neubau dauert fünf bis sieben Minuten, der Eingang läuft dabei weiter, und die Standardausgabe von `chronicle` und `stats` sieht in dieser Zeit vollständig aus — `stats` zeigt Teilsummen. … Zu entscheiden: die Schattentabelle bauen, oder dabei bleiben, den Neubau in der Meldung benennen und es auf eine Seite schreiben.
> - Jede Projektion liest das ganze Log für sich: 29 % eines Neubaus sind doppeltes Lesen, und `source-stats` liest alle Inhalte, um Einheiten zu zählen (PP, Bericht C).
> - Der Neubau leert mit `DELETE`: bei 700 000 Events bleiben 5,1 Millionen tote Zeilen, bis `VACUUM` sie räumt; die Wirkung ist ungemessen (PP, Bericht C).
> - `Projection.write` könnte sich eine eigene Transaktion nehmen (1b §10, F9); `projection_state.version` ohne `CHECK` (F12). Beide vor der dritten Projektion zu entscheiden.
> - Die Projektionsnamen stehen zweimal: in `core` und als Abbildung auf die Tabelle in `storage` (PP, A2).
> - `_catch_up_after` in `cli.py` hört an der ersten Projektion auf, die scheitert, und nennt die übrigen nicht … (P-1c; Nachprüfung der Endkorrektur).
> - Zwei Releases gegen eine Datenbank bauen eine Projektion gegeneinander neu … `ProjectionRebuilt` hält einen Lauf an … (Endkorrektur, Teil 2).
> - `p_chronicle` hält den Inhalt jeder Einheit ein zweites Mal und ist damit größer als die Tabelle `unit`: 1,9 GB gegen 1,4 GB bei 700 000 Events; ihr Schreiben ist mit 48 % der größte Posten eines Neubaus (PP, Bericht C).

Note the pair **"Beide vor der dritten Projektion zu entscheiden"** (`Projection.write` in its own transaction; `CHECK` on `projection_state.version`): a graph/assignment projection is the third.

The map's header section also says (landkarte.md:126, 185-196): phase 2 is "Zuordnung von Events … mit der Projektion oder der inkrementellen Faltung, die die Messungen verlangen" and is the next plan.

Citation habits for the plan text: the label `P-Z1` is "the phase-1 plan's findings" and `Z §n` the living spec; rulings are per plan and the plan's date must be named (CLAUDE.md "Ruling citation").

---

## §11 Traps

1. **`in` is a Python keyword.** A tool function cannot have a parameter named `in`. Measured with the installed MCP SDK (`mcp.server.mcpserver.MCPServer`, scratch script in the session scratchpad): `def previously(in_: Annotated[int | None, Field(alias="in")] = None)` **advertises** a property `"in"` in the input schema, but a call with `{"in": 5}` fails with `TypeError: previously() got an unexpected keyword argument 'in'. Did you mean 'in_'?` (the SDK calls the function with the alias as keyword). So the pydantic-alias route that `RelationItem.start` uses for `from` (server.py:573, a `BaseModel` field, not a function parameter) does **not** work for a tool function parameter. `inspect.Parameter("in", …)` also rejects keywords. Options a plan must weigh: register the schema with a different mechanism (a `BaseModel` argument, which nests the arguments; or a hand-built `Tool`/schema), or rename the property (the spec fixes `in`, §10.3; Betreuer: "`in` macht da mehr Sinn"). Measure again against the lockfile version before relying on this. The same on the CLI side: `argparse` `--in` is fine as an option, but `args.in` is a syntax error — use `dest="bracket"`; `_chronicle_arguments` has no `dest` today.
2. **`TRANSITIVE` is two things with one string**: `core/graph.py:81 TRANSITIVE = "transitive"` is the **level** (`DIRECT`, `TRANSITIVE`, `OPEN`; `DIRECT`/`OPEN` come from `core/assertion.py:52-53`), `core/vocabulary.py:~74 TRANSITIVE = "transitive"` is the relation **behavior**. `graph_write.py` imports the level one (`from previously.core.graph import TRANSITIVE`) and `vocabulary` as `ACYCLIC`. Writing "transitive upward via `part_of`" is the behavior; "a transitive version" is the level. `docs/explanation/graph.md` uses both words.
3. **"assignment"**: in the code tree the word appears only in citations of "the 2026-10-14 assignments plan" (= `Zuordnungen` phase 1, 30+ comments) and in two Python-sense uses (`chain.py:47` "assigned to an event", comments about pyright assignment). "Zuordnung/assignment" in docs is the relation `concerns` (explanation/graph.md:46, :146; connectors.md:130). **"bracket"** (German "Klammer") appears nowhere in code or English docs (`grep -rniE "bracket"` finds only IPv6/angle brackets). The vocabulary's term for the other end is "entity".
4. **"project" and "matter" were reserved MCP parameter names** (landkarte; spec §10.3 drops them for `in`); nothing in code uses them as parameters. `project` is an entity kind in the base file; `involved_in` and `part_of` use it.
5. **Unit numbering**: units are `seq >= 1` (`schema.py` `unit_seq_check`), but the graph form accepts units `>= 0` (`graph.py:_units_problem`, `0 <= seq`); `check_sources` is what refuses a unit the event does not have. A `concerns` claim citing unit 0 passes the form and fails at write; `verify` has "assertion names a unit its source does not have".
6. **`filters` for the cursor are `Mapping[str, str]`** (server.py cast, render.py:594/617); cursor equality is exact `dict` equality. An `in` filter (int id) must be rendered to a str in `filters`, and the same string must be used in `call` for the access entry (`_given(**filters, cursor=cursor)` — the access log records the filters as given).
7. **`read_chronicle` has no `source` filter and the MCP chronicle does** (observations `source`). The CLI `chronicle` has `--since/--until/--limit` only. A bracket filter on both surfaces is two implementations (SQL over `p_*` for CLI; set-of-ids or protocol change for MCP).
8. **The CLI chronicle is per unit, the MCP chronicle is per event with all units.** "A unit's own assignment replaces the event's assignment when finding" is easy on the first and needs a rule on the second (show the event? show only matching units? `get_event` already takes `from_unit`).
9. **Open proposals and the closure**: `Graph.relations()` and `entities()` include open winners; a `part_of` or `concerns` edge proposed by a model would pull events into a bracket's chronicle unless filtered by `level_of` (map M4). `Graph.reaches(levels=…)` is the existing tool; `relations()` has none.
10. **`part_of` is declared `acyclic` and `transitive`; edges point part -> whole** (`from = ["matter", "project"]`, `to = ["organization", "project"]`). "Everything that belongs to bracket N" is the reverse closure (all X that reach N); the existing walk is forward only. Because `part_of` cannot start at a `person` or `post`, a `concerns` to a `person`/`post` bracket gets no upward closure.
11. **The window of `reaches`**: it ignores periods (`whatever their periods`), while `relations(at=…)` applies them. A bracket closure should say which it uses.
12. **Counts near this code** (recheck before copying into new comments): `core/graph.py` 1132 lines; `cli.py` 4329 lines (the map still says 4 274); `server.py` 3062; `tests` 2650; `LogStore` 16 methods / 15 called from `core` / 8 from `mcp_server`; DB tables 8 (database-schema.md); migrations 5 (head `0005_watermark`); `PROJECTIONS` 2; CLI `Command(...)` entries ~50; `project` prints one line per projection.
13. **`write_record` / access log**: the access entry of a `write_relation` call keeps `ends = _event_ids([entry.get("from"), entry.get("to"), *candidates])` (server.py:2396). If `from` becomes an object `{event, units}`, `_event_ids` (ints only) silently drops it.
14. **`verify` message lists are quoted in docs and held by tests** (`tests/test_docs_references.py:1717, 1770`: "the sixteen findings `verify` reports about an assertion", "the eight findings … about an entity or a relation"). A new finding, or a new refusal sentence from `conformance_problem` that `verify` prints (`"assertion does not fit the vocabulary of its time: …"`), moves those quoted blocks in `docs/reference/cli.md`. The sentence `an event as the start of a relation comes with assignments` is exactly what `_NOT_FITTING` marks and what `verify` would print for a hand-written event-start relation until lifted.
15. **A comment is a claim / program output carries no `{ref}`**: refusal sentences must not name an id or a value (`graph.py` docstring), and `tests/test_docs_references.py` resolves every `{ref}` label in `src`/`tests` `*.py` and holds the quoted messages of reference pages against the code.
16. **Nothing else reads a projection for correctness today.** `p_chronicle` is a convenience for the CLI; the MCP server (the only place whose answers a model sees) reads the log. If a projection becomes what the MCP header or `chronicle in` reads, then a lagging projection changes answers — and the gate (phase 3) must never read a lagging projection (spec §9.7). Both `serve` and `mcp` never run `catch_up`; an operator who forgets `previously project` would get stale brackets. Per CLAUDE.md "Operations are part of every design": the plan needs a paragraph for kup6s (CronJob/`project` after ingest, or catch-up inside the server) and one for a compose file plus cron line.
17. **Erased subjects and ids in the fold**: a thread whose first version is erased still accepts later versions naming it as `subject` (`GraphFold.add`: `subject not in drafts and subject not in erased` -> dropped, so erased ones are accepted); `GraphThread` for a fully erased thread does not exist. `relation_visible`'s `ends[id] is None` means "every version erased". A projection that maps bracket -> events must treat an end that is erased the same way.
18. **`ChronicleProjection(version=…)`**: chronicle is at version 3; the dataclass form exists so a test can force a rebuild. A bracket column on `p_chronicle` (the dropped 1b idea) would bump it; the spec chose a separate association instead.
19. **Tooling on this machine**: `uv run pytest` needs Docker for the `db` tests (testcontainers); the whole suite took 282.77 s on the last typed run (tutorial line 283).
