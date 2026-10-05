(database-schema)=

# Database schema

Previously stores its data in seven PostgreSQL tables.
Three hold the log: `event`, `unit`, and `source_key`.
One is the blob register beside the log: `event_blob`.
Three hold projections, which are derived from the log and disposable: `projection_state`, `p_chronicle`, and `p_source_stats`; {ref}`projections` explains what that means.
`src/previously/storage/schema.py` declares all seven as SQLAlchemy Core tables, with no ORM.
Each event relates to zero or more units, to at most one source key, and to zero or more rows of the blob register.

```{mermaid}
:caption: The three tables of the log and the blob register, with their foreign keys; the projection tables are described below.

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
    event_blob {
        bigint event_id PK, FK
        bytea sha256 PK
    }
    event ||--o{ unit : contains
    event ||--o| source_key : "identified by"
    event ||--o{ event_blob : "names"
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
| `units_hash` | `bytea` | No | The hash of this event's units; in hash format 2, over the units' `digest` values. |
| `payload` | `jsonb` | Yes | The event's content; `NULL` after an erasure (a tombstone). |
| `hash_version` | `smallint` | No | The hash format the row was written in, `1` or `2`; defaults to `1`. |
| `payload_salt` | `bytea` | Yes | The salt of the payload hash in hash format 2; `NULL` in hash format 1 and after an erasure. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `event_pkey` | `id` | Primary key. |
| `event_hash_idx` | `hash` | Unique. |
| `event_prev_hash_idx` | `prev_hash` | Unique, with `NULLS NOT DISTINCT`: at most one row has a `NULL` `prev_hash`. |
| `event_kind_check` | `kind` | `kind IN ('observation', 'assertion', 'action')`. |
| `event_payload_object_check` | `payload` | `payload IS NULL OR jsonb_typeof(payload) = 'object'`. |
| `event_payload_salt_check` | `payload`, `payload_salt` | `payload IS NOT NULL OR payload_salt IS NULL`: a row without a payload has no payload salt. |
| `event_occurred_idx` | `occurred_at` | Not unique; no constraint. |
| `event_kind_occurred_idx` | `kind`, `occurred_at` | Not unique; no constraint. |

## `unit`

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `event_id` | `bigint` | No | The event this unit belongs to. |
| `seq` | `integer` | No | The unit's position within its event, starting at 1. |
| `content` | `text` | Yes | The unit's text; `NULL` after an erasure (a tombstone). |
| `start_ms` | `integer` | Yes | Start offset in milliseconds; always `NULL` in stage 1a. |
| `end_ms` | `integer` | Yes | End offset in milliseconds; always `NULL` in stage 1a. |
| `speaker` | `text` | Yes | The speaker's name; always `NULL` in stage 1a. |
| `digest` | `bytea` | Yes | The unit's own hash in hash format 2; stays valid after an erasure. `NULL` in hash format 1. |
| `salt` | `bytea` | Yes | The salt of `digest`; `NULL` in hash format 1 and after an erasure. |

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `unit_pkey` | `event_id`, `seq` | Primary key. |
| `unit_seq_check` | `seq` | `seq >= 1`. |
| `unit_tombstone_check` | `content`, `salt`, `speaker`, `start_ms`, `end_ms` | `content IS NOT NULL OR (salt IS NULL AND speaker IS NULL AND start_ms IS NULL AND end_ms IS NULL)`: a unit without content keeps only `event_id`, `seq` and `digest`. |
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

## `event_blob`

The blob register: one row for each distinct blob an event names in its payload; see {ref}`blobs`.

| Column | Type | Accepts NULL | Meaning |
|---|---|---|---|
| `event_id` | `bigint` | No | The event that names the blob. |
| `sha256` | `bytea` | No | The blob's address, the SHA-256 of its content, as 32 bytes. |

`append` writes the rows in the transaction that writes the event, and nothing changes or deletes them.
The same content attached twice to one event is two references in the payload and one row here.
`verify` holds the rows against the payload, and for an erased payload against the redaction; see {ref}`cli-reference`.

### Constraints and indexes

| Name | On | Enforces |
|---|---|---|
| `event_blob_pkey` | `event_id`, `sha256` | Primary key. |
| `event_blob_sha256_check` | `sha256` | `octet_length(sha256) = 32`. |
| `event_blob_event_id_fkey` | `event_id` | Foreign key to `event.id`. |
| `event_blob_sha256_idx` | `sha256` | Index: which events name a blob. |

The migration `0004_event_blob` creates the table, and refuses to go back below it while the table holds a row.

The migration `0003_hash_version_2` brings `hash_version`, the salts and the unit digests, and refuses to go back below it while the log holds an event in a hash format other than 1, or a unit without content.
The refusal is one line, with each reason that applies, joined by `; `:

```text
refusing to downgrade below 0003_hash_version_2: the log holds events in a hash format other than 1, which cannot be verified without the version and the salts this would drop; the log holds units without content, which cannot be NOT NULL again
```

Either refusal leaves the database at the revision the `alembic downgrade` started from.

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
| `evidence` | `text` | Yes | The evidence kind from the payload; `NULL` when the payload is a tombstone that no redaction ordered. An event a redaction erased has no rows here. |
| `source` | `text` | Yes | The system the event came from; `NULL` when the event carries no source attribution. |
| `external_id` | `text` | Yes | The event's identifier within that source; `NULL` under the same condition as `source`. |
| `speaker` | `text` | Yes | The speaker's name; always `NULL` until stage 2. |
| `start_ms` | `integer` | Yes | Start offset in milliseconds; always `NULL` until stage 2. |
| `end_ms` | `integer` | Yes | End offset in milliseconds; always `NULL` until stage 2. |

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
