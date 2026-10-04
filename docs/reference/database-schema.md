(database-schema)=

# Database schema

Previously stores every event in three PostgreSQL tables: `event`, `unit`, and `source_key`.
`src/previously/storage/schema.py` declares them as SQLAlchemy Core tables, with no ORM.
Each event relates to zero or more units, and to at most one source key.

```{mermaid}
:caption: event, unit, and source_key, with their foreign keys.

erDiagram
    event {
        bigint id PK
    }
    unit {
        bigint event_id FK
        int seq PK
    }
    source_key {
        text source PK
        text external_id PK
        bigint event_id FK
    }
    event ||--o{ unit : contains
    event ||--o| source_key : "identified by"
```

## `event`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `id` | `bigint` | No | The event's position in the chain; comes from the predecessor's `id`, not a sequence. |
| `kind` | `text` | No | One of `observation`, `assertion`, `action`. |
| `recorded_at` | `timestamp with time zone` | No | When the event was written. |
| `occurred_at` | `timestamp with time zone` | No | When the event happened. |
| `prev_hash` | `bytea` | Yes | The predecessor's `hash`; `NULL` for the first event in the chain. |
| `hash` | `bytea` | No | This event's hash; see {ref}`hash-format`. |
| `payload_hash` | `bytea` | No | The hash of `payload`; stays valid after an erasure. |
| `units_hash` | `bytea` | No | The hash of this event's units. |
| `payload` | `jsonb` | Yes | The event's content; `NULL` after an erasure (a tombstone). |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `event_pkey` | `id` | Primary key. |
| `event_hash_idx` | `hash` | Unique. |
| `event_prev_hash_idx` | `prev_hash` | Unique, with `NULLS NOT DISTINCT`: at most one row has a `NULL` `prev_hash`. |
| `event_kind_check` | `kind` | `kind IN ('observation', 'assertion', 'action')`. |
| `event_payload_object_check` | `payload` | `payload IS NULL OR jsonb_typeof(payload) = 'object'`. |
| `event_occurred_idx` | `occurred_at` | Not unique; no constraint. |
| `event_kind_occurred_idx` | `kind`, `occurred_at` | Not unique; no constraint. |

## `unit`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `event_id` | `bigint` | No | The event this unit belongs to. |
| `seq` | `integer` | No | The unit's position within its event, starting at 1. |
| `content` | `text` | No | The unit's text. |
| `start_ms` | `integer` | Yes | Start offset in milliseconds; always `NULL` in stage 1a. |
| `end_ms` | `integer` | Yes | End offset in milliseconds; always `NULL` in stage 1a. |
| `speaker` | `text` | Yes | The speaker's name; always `NULL` in stage 1a. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `unit_pkey` | `event_id`, `seq` | Primary key. |
| `unit_seq_check` | `seq` | `seq >= 1`. |
| `unit_event_id_fkey` | `event_id` | Foreign key to `event.id`. |

## `source_key`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `source` | `text` | No | The system the event came from. |
| `external_id` | `text` | No | The event's identifier within that source. |
| `event_id` | `bigint` | No | The event this attribution belongs to. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `source_key_pkey` | `source`, `external_id` | Primary key. |
| `source_key_event_id_key` | `event_id` | Unique: at most one source attribution per event. |
| `source_key_event_id_fkey` | `event_id` | Foreign key to `event.id`. |

Three more tables hold projections derived from the tables above.
{ref}`projections` explains why they carry no foreign keys onto one another.

## `projection_state`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `name` | `text` | No | The projection's name, such as `chronicle` or `source-stats`. |
| `up_to_id` | `bigint` | No | The highest event `id` this projection has processed; `0` before any run. |
| `version` | `integer` | No | The projection code's derivation version; a mismatch triggers a rebuild. |
| `built_at` | `timestamp with time zone` | No | When this row was last written. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `projection_state_pkey` | `name` | Primary key. |

## `p_chronicle`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `event_id` | `bigint` | No | The event this row derives from. |
| `seq` | `integer` | No | The unit's position within its event, starting at 1. |
| `content` | `text` | No | The unit's text. |
| `occurred_at` | `timestamp with time zone` | No | When the event happened. |
| `kind` | `text` | No | The event's kind: one of `observation`, `assertion`, `action`. |
| `evidence` | `text` | Yes | The evidence kind from the payload; `NULL` after an erasure (a tombstone). |
| `source` | `text` | Yes | The system the event came from; `NULL` when the event carries no source attribution. |
| `external_id` | `text` | Yes | The event's identifier within that source; `NULL` under the same condition as `source`. |
| `speaker` | `text` | Yes | The speaker's name; always `NULL` in stage 1a. |
| `start_ms` | `integer` | Yes | Start offset in milliseconds; always `NULL` in stage 1a. |
| `end_ms` | `integer` | Yes | End offset in milliseconds; always `NULL` in stage 1a. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `p_chronicle_pkey` | `event_id`, `seq` | Primary key. |
| `p_chronicle_event_id_fkey` | `event_id` | Foreign key to `event.id`. |
| `p_chronicle_occurred_idx` | `occurred_at`, `event_id`, `seq` | Not unique; no constraint. |

## `p_source_stats`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `source` | `text` | No | The system the events came from. |
| `events` | `bigint` | No | The number of events attributed to this source. |
| `units` | `bigint` | No | The number of units across those events. |
| `first_seen` | `timestamp with time zone` | No | The earliest `occurred_at` among those events. |
| `last_seen` | `timestamp with time zone` | No | The latest `occurred_at` among those events. |
| `last_event_id` | `bigint` | No | The `id` of the event that last updated this row. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `p_source_stats_pkey` | `source` | Primary key. |
| `p_source_stats_last_event_id_fkey` | `last_event_id` | Foreign key to `event.id`. |
