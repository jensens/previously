## Task 4: Reine Ableitung — `chronicle.derive`, `source_stats.derive`, `source_stats.merge`

**Files:**
- Create: `src/previously/core/projection/__init__.py`, `src/previously/core/projection/worker.py` (nur `Batch` in dieser Aufgabe), `src/previously/core/projection/chronicle.py`, `src/previously/core/projection/source_stats.py`, `tests/test_projection_derive.py`

**Interfaces:**
- Produces: `core.projection.worker.Batch(events: tuple[EventRow, ...], units: Mapping[int, Sequence[UnitRow]], keys: Mapping[int, tuple[str, str]])`; `chronicle.derive(batch) -> list[ChronicleRow]`; `source_stats.derive(batch) -> dict[str, SourceStatsRow]`; `source_stats.merge(existing: SourceStatsRow | None, addition: SourceStatsRow) -> SourceStatsRow`. Alles ohne Datenbank, ohne SQL.

- [ ] **Schritt 1: `Batch` — der Eingabetyp**

`src/previously/core/projection/worker.py` (in dieser Aufgabe nur das; `catch_up` kommt in Aufgabe 5 in dieselbe Datei):

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The projection worker ({ref}`projections`): batches, and the catch-up."""

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.rows import EventRow
    from previously.contract.rows import UnitRow


@dataclass(frozen=True)
class Batch:
    """What one catch-up step reads from the log: a run of events in chain
    order with their units and source attributions, fetched by batch — one
    query each, not one per event, for the reason `units_by_event` and
    `source_keys` exist."""

    events: tuple[EventRow, ...]
    units: Mapping[int, Sequence[UnitRow]]
    keys: Mapping[int, tuple[str, str]]
```

`src/previously/core/projection/__init__.py` vorerst nur mit Lizenzkopf und Docstring `"""Projections: derived, disposable views over the log ({ref}`projections`)."""` — die Re-Exporte kommen in Aufgabe 5.

- [ ] **Schritt 2: Die Tests zuerst**

`tests/test_projection_derive.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The derivation functions, without a database.

They take row types and return row types; that is the whole point of keeping
the arithmetic in `core` ({ref}`projections`), and it is why these tests
carry no `db` marker.
"""

from datetime import datetime
from datetime import UTC
from previously.contract.rows import EventRow
from previously.contract.rows import SourceStatsRow
from previously.contract.rows import UnitRow
from previously.core.projection import chronicle
from previously.core.projection import source_stats
from previously.core.projection.worker import Batch


T1 = datetime(2026, 10, 1, tzinfo=UTC)
T2 = datetime(2026, 10, 2, tzinfo=UTC)
T3 = datetime(2026, 10, 3, tzinfo=UTC)


def _event(event_id: int, occurred_at: datetime, payload: dict[str, object] | None) -> EventRow:
    return EventRow(
        id=event_id,
        kind="observation",
        recorded_at=T3,
        occurred_at=occurred_at,
        prev_hash=None,
        hash=bytes([event_id]) * 32,
        payload_hash=b"\x00" * 32,
        units_hash=b"\x01" * 32,
        payload=payload,
    )


def test_chronicle_derives_one_row_per_unit_with_the_source_attribution() -> None:
    batch = Batch(
        events=(_event(1, T1, {"evidence": "verbatim", "text": "a\n\nb"}),),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b", speaker="alice")]},
        keys={1: ("email", "msg-1")},
    )
    rows = chronicle.derive(batch)
    assert [(r.event_id, r.seq, r.content) for r in rows] == [(1, 1, "a"), (1, 2, "b")]
    assert {(r.source, r.external_id, r.evidence) for r in rows} == {("email", "msg-1", "verbatim")}
    assert rows[1].speaker == "alice"
    assert rows[0].occurred_at == T1


def test_chronicle_leaves_source_null_for_an_event_without_a_key() -> None:
    batch = Batch(events=(_event(1, T1, {"evidence": "recollection"}),), units={1: [UnitRow(1, 1, "a")]}, keys={})
    (row,) = chronicle.derive(batch)
    assert (row.source, row.external_id) == (None, None)


def test_chronicle_still_derives_rows_for_an_erased_payload() -> None:
    """A tombstone empties the payload and leaves the units standing
    ({ref}`projections`): the chronicle shows them, with `evidence` NULL.
    Whoever builds an erasure that deletes units has to change this test on
    purpose."""
    batch = Batch(events=(_event(1, T1, None),), units={1: [UnitRow(1, 1, "a")]}, keys={1: ("cli", "x")})
    (row,) = chronicle.derive(batch)
    assert row.evidence is None
    assert row.content == "a"


def test_chronicle_derives_nothing_for_an_event_without_units() -> None:
    batch = Batch(events=(_event(1, T1, {"evidence": "recollection"}),), units={}, keys={})
    assert chronicle.derive(batch) == []


def test_source_stats_aggregates_a_batch_per_source() -> None:
    batch = Batch(
        events=(_event(1, T1, {}), _event(2, T2, {}), _event(3, T3, {})),
        units={1: [UnitRow(1, 1, "a"), UnitRow(1, 2, "b")], 2: [UnitRow(2, 1, "c")], 3: []},
        keys={1: ("email", "m1"), 2: ("email", "m2"), 3: ("cli", "x")},
    )
    stats = source_stats.derive(batch)
    assert stats == {
        "email": SourceStatsRow("email", events=2, units=3, first_seen=T1, last_seen=T2, last_event_id=2),
        "cli": SourceStatsRow("cli", events=1, units=0, first_seen=T3, last_seen=T3, last_event_id=3),
    }


def test_source_stats_ignores_an_event_without_a_source() -> None:
    batch = Batch(events=(_event(1, T1, {}),), units={1: [UnitRow(1, 1, "a")]}, keys={})
    assert source_stats.derive(batch) == {}


def test_merge_adds_counts_and_keeps_the_extremes() -> None:
    existing = SourceStatsRow("email", 2, 3, T1, T2, 2)
    addition = SourceStatsRow("email", 1, 1, T3, T3, 3)
    assert source_stats.merge(existing, addition) == SourceStatsRow("email", 3, 4, T1, T3, 3)


def test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older() -> None:
    """The regression case the spec names (§5.2): an event that *arrives*
    later but *happened* earlier. Assignment and minimum agree on every
    in-order sequence and part here. Measured on 2026-10-04: with
    `first_seen=addition.first_seen` this test fails and the one above stays
    green — the one above is the control."""
    existing = SourceStatsRow("email", 1, 1, T2, T2, 1)
    late_but_older = SourceStatsRow("email", 1, 1, T1, T1, 2)
    merged = source_stats.merge(existing, late_but_older)
    assert merged.first_seen == T1
    assert merged.last_seen == T2
    assert merged.last_event_id == 2


def test_merge_with_nothing_existing_is_the_addition() -> None:
    addition = SourceStatsRow("email", 1, 1, T1, T1, 1)
    assert source_stats.merge(None, addition) == addition
```

- [ ] **Schritt 3: Laufen lassen — rot**

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: `ModuleNotFoundError` für `chronicle`/`source_stats`.

- [ ] **Schritt 4: `chronicle.py`**

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The chronicle: one row per unit, each with its source attribution.

A denormalization over four tables — `event`, `unit`, `source_key` and the
payload for the kind of evidence — cut to the question "what happened, line
by line, and how do I know". That is what makes it a projection and not a
copy of `log` ({ref}`projections`).
"""

from dataclasses import dataclass
from previously.contract.rows import ChronicleRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def _evidence(payload: Mapping[str, object] | None) -> str | None:
    """The kind of evidence out of the payload, or None for a tombstone.

    `append` mixes it in under the reserved key ({ref}`canonicalization`);
    a value that is not a string is not one this projection can name.
    """
    if payload is None:
        return None
    value = payload.get("evidence")
    return value if isinstance(value, str) else None


def derive(batch: Batch) -> list[ChronicleRow]:
    rows: list[ChronicleRow] = []
    for event in batch.events:
        key = batch.keys.get(event.id)
        evidence = _evidence(event.payload)
        for unit in batch.units.get(event.id, ()):
            rows.append(
                ChronicleRow(
                    event_id=event.id,
                    seq=unit.seq,
                    content=unit.content,
                    occurred_at=event.occurred_at,
                    kind=event.kind,
                    evidence=evidence,
                    source=None if key is None else key[0],
                    external_id=None if key is None else key[1],
                    speaker=unit.speaker,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                )
            )
    return rows


@dataclass(frozen=True)
class ChronicleProjection:
    """Name and version as `projection_state` knows them, and the write step.

    A frozen dataclass rather than module constants, so a test can say
    `ChronicleProjection(version=2)` to force a rebuild without touching this
    module.
    """

    name: str = "chronicle"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        store.insert_chronicle(conn, derive(batch))


CHRONICLE = ChronicleProjection()
```

- [ ] **Schritt 5: `source_stats.py`**

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Per-source statistics: the aggregate that puts the assurance to the test.

Counts are additive and `first_seen`/`last_seen` are extremes, and they can be
caught up incrementally **only because the log is append-only**: were a row
able to disappear, a minimum would need a rebuild, because a minimum does not
show whether its carrier still exists ({ref}`projections`).

The merge arithmetic is here and not in SQL. Done as `ON CONFLICT DO UPDATE
SET events = events + excluded.events, first_seen = least(…)` the
correctness of the incremental step would sit in `storage`, and the claim
"derivation without SQL" would be false. Here a unit test reaches it without a
database — and the one that matters is the late arrival that happened
earlier, where assignment and minimum part.
"""

from dataclasses import dataclass
from previously.contract.rows import SourceStatsRow
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from previously.contract.store import ProjectionStore
    from previously.core.projection.worker import Batch


def merge(existing: SourceStatsRow | None, addition: SourceStatsRow) -> SourceStatsRow:
    if existing is None:
        return addition
    return SourceStatsRow(
        source=existing.source,
        events=existing.events + addition.events,
        units=existing.units + addition.units,
        first_seen=min(existing.first_seen, addition.first_seen),
        last_seen=max(existing.last_seen, addition.last_seen),
        last_event_id=max(existing.last_event_id, addition.last_event_id),
    )


def derive(batch: Batch) -> dict[str, SourceStatsRow]:
    """The batch folded per source. Events without a source attribution do not
    count: there is no source to attribute them to. The chronicle shows them,
    this table does not — a decision, so it is written down."""
    out: dict[str, SourceStatsRow] = {}
    for event in batch.events:
        key = batch.keys.get(event.id)
        if key is None:
            continue
        source = key[0]
        addition = SourceStatsRow(
            source=source,
            events=1,
            units=len(batch.units.get(event.id, ())),
            first_seen=event.occurred_at,
            last_seen=event.occurred_at,
            last_event_id=event.id,
        )
        out[source] = merge(out.get(source), addition)
    return out


@dataclass(frozen=True)
class SourceStatsProjection:
    name: str = "source-stats"
    version: int = 1

    def write[Conn](self, store: ProjectionStore[Conn], conn: Conn, batch: Batch) -> None:
        additions = derive(batch)
        if not additions:
            return
        existing = store.source_stats(conn, sorted(additions))
        store.upsert_source_stats(
            conn, [merge(existing.get(source), row) for source, row in sorted(additions.items())]
        )


SOURCE_STATS = SourceStatsProjection()
```

- [ ] **Schritt 6: Laufen lassen — grün, dann die Mutation**

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: neun `PASSED`.

**Messung, nicht committen:** in `merge` `first_seen=min(existing.first_seen, addition.first_seen)` durch `first_seen=addition.first_seen` ersetzen.

Run: `uv run pytest tests/test_projection_derive.py -v`
Erwartet: **genau einer** rot — `test_merge_keeps_the_earliest_first_seen_when_the_late_arrival_is_older`; `test_merge_adds_counts_and_keeps_the_extremes` bleibt grün (die Kontrolle: in Zeitreihenfolge sind Zuweisung und Minimum gleich). Beide Ergebnisse in den Bericht und in den Docstring des Regressionstests („Measured on …" steht schon dort — Datum prüfen).

Zurücksetzen. Grün.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **211 passed** (202 + 9). `lint-imports`: `core.projection.*` importiert `contract.rows`, `contract.store` — beides erlaubt, `4 kept, 0 broken`.

```bash
git add -A
git commit -F - <<'MSG'
feat: the two derivations, pure and tested without a database

`chronicle.derive` flattens an event, its units and its source attribution
into one row per unit; `evidence` is None for a tombstone, and the rows
still exist — the test pins that on purpose, so a future erasure has to
change it deliberately.

`source_stats.derive` folds a batch per source and `merge` folds a batch
into an existing row: counts add, extremes take the minimum and maximum.
The regression case the spec names is a test: an event that arrives later
but happened earlier. Measured — with `first_seen = addition.first_seen`
that test fails alone and the in-order test stays green, which is what
makes the in-order test the control and not a duplicate.

`Batch` in `worker.py` is the input type; the worker itself follows.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

