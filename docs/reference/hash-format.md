(hash-format)=

# Hash format

Every hash in Previously is the SHA-256 digest of canonical JSON bytes.
`previously.core.canonical.canonical` produces those bytes.
`previously.core.hashing` defines what goes into each digest.

(payload-range)=

## Payload range

A payload must be a JSON object at the top level.
Within it, you must use only objects, arrays, strings, integers, `true`, `false` and `null`.
Previously refuses every other value before it hashes anything, with `previously.core.errors.InvalidPayload`.

The five restrictions below apply to every value at every depth.
Each message is prefixed with the path to the offending value: `$` for the payload itself, `.name` for an object member, `[n]` for an array element.

| Restriction | Message |
|---|---|
| You must not use floating point numbers. State a scale and use an integer. | `floating point number not allowed — state a scale as an integer` |
| Every object key must match `^[a-z][a-z0-9_]*$`. | `key 'Total' must match ^[a-z][a-z0-9_]*$` |
| Every integer must satisfy `abs(value) <= 9007199254740991`, which is `2**53 - 1`. | `integer outside the safe range (±9007199254740991) — not exact across languages` |
| No string may contain a null byte. | `null byte not allowed — PostgreSQL jsonb cannot store it` |
| No string may contain a lone UTF-16 surrogate. | `string not representable as UTF-8 (surrogates not allowed) — a lone UTF-16 surrogate, for instance` |

Any other type is refused by name, for example `type set not allowed`.

`append` reserves the payload key `evidence` for the kind of evidence and refuses a payload that already carries it.
`append` applies the null-byte and surrogate restrictions to `source` and `external_id` as well, before either value reaches the driver.

For why the range is drawn here and not wider, see {ref}`canonicalization`.

## Payload hash

`payload_hash` is the SHA-256 digest of the event's `payload`, canonicalized directly.
It carries no wrapping fields.

## Units hash

`units_hash` wraps the event's units in a header of three fields.

| Field | Value |
|---|---|
| `v` | `1` (`HASH_VERSION`). |
| `domain` | `"previously/units"` (`UNITS_DOMAIN`). |
| `units` | A list of the event's units, sorted by `seq`. |

Each entry in `units` carries five fields.

| Field | Value |
|---|---|
| `seq` | The unit's position within the event. |
| `content` | The unit's text. |
| `start_ms` | The start offset in milliseconds, or `null`. |
| `end_ms` | The end offset in milliseconds, or `null`. |
| `speaker` | The speaker's name, or `null`. |

## Event hash

`event_hash` wraps eleven fields.

| Field | Value |
|---|---|
| `v` | `1` (`HASH_VERSION`). |
| `domain` | `"previously/event"` (`HASH_DOMAIN`). |
| `id` | The event's `id`. |
| `kind` | The event's `kind`. |
| `recorded_at` | `recorded_at`, formatted by `iso_utc`. |
| `occurred_at` | `occurred_at`, formatted by `iso_utc`. |
| `prev` | The predecessor's `hash` as hexadecimal, or `null` for the first event. |
| `payload` | `payload_hash` as hexadecimal. |
| `units` | `units_hash` as hexadecimal. |
| `source` | The source system, or `null` without a source attribution. |
| `external_id` | The event's identifier within that source, or `null` without a source attribution. |

`iso_utc` formats a timestamp as UTC, with six fractional digits and a trailing `Z`, for example `2026-10-02T14:23:45.123456Z`.

## Pinned test vector

```{warning}
Do not recompute these values.
They are pinned in `tests/test_hashing.py`, and recomputing them to make a test pass destroys the proof that the hash is reproducible.
The one exception is a deliberate change to the hash range, which raises `HASH_VERSION` along with the vector; see {ref}`canonicalization`.
```

`tests/test_hashing.py` pins the following vector.

| Input | Value |
|---|---|
| `payload` | `{"text": "Preis bleibt 1000 Euro.", "evidence": "verbatim"}` |
| `units` | seq `1`: `"Preis bleibt 1000 Euro."`, no offsets, no speaker. seq `2`: `"Bitte bestätigen."`, `start_ms=1500`, `end_ms=2500`, `speaker="Anna"`. |
| `id` | `42` |
| `kind` | `observation` |
| `recorded_at` | `2026-10-02T14:23:45.123456Z` |
| `occurred_at` | `2026-10-01T09:00:00.000000Z` |
| `prev_hash` | `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f` |
| `source` | `email` |
| `external_id` | `nachricht-1` |

These inputs produce the following digests, as hexadecimal.

| Digest | Value |
|---|---|
| `payload_hash` | `6f3604dd00c587c361ebf0398cd6a2c9c2d7319341d4fa7708ffaf831ec8a15d` |
| `units_hash` | `0628194c7313b4793d419cdae5d31c21889512f0872ed3ef7dc1efcda9594510` |
| `event_hash` | `6839b69aee7b621d2ded904b677aa770ad9988cdb9ba12b43247e605df8797c3` |

The canonical JSON bytes that SHA-256 runs over, for each of the three digests:

```json
{"evidence":"verbatim","text":"Preis bleibt 1000 Euro."}
```

```json
{"domain":"previously/units","units":[{"content":"Preis bleibt 1000 Euro.","end_ms":null,"seq":1,"speaker":null,"start_ms":null},{"content":"Bitte bestätigen.","end_ms":2500,"seq":2,"speaker":"Anna","start_ms":1500}],"v":1}
```

```json
{"domain":"previously/event","external_id":"nachricht-1","id":42,"kind":"observation","occurred_at":"2026-10-01T09:00:00.000000Z","payload":"6f3604dd00c587c361ebf0398cd6a2c9c2d7319341d4fa7708ffaf831ec8a15d","prev":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","recorded_at":"2026-10-02T14:23:45.123456Z","source":"email","units":"0628194c7313b4793d419cdae5d31c21889512f0872ed3ef7dc1efcda9594510","v":1}
```
