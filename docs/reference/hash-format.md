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

## Hash versions

`previously.core.hashing` defines two hash formats, version 1 and version 2.
Each digest carries its version in the field `v` of the hashed object, except the version 1 payload hash, which carries no wrapping fields.

| Name | Value |
|---|---|
| `HASH_VERSION_1` | `1` |
| `HASH_VERSION_2` | `2` |
| `HASH_VERSION` | `HASH_VERSION_2`, the version new events are meant to be written in. |

`previously.core.append` and `previously.core.verify` call the version 1 functions.
No module in `previously` calls the version 2 functions yet.
The version 1 functions stay unchanged beside the version 2 functions, and version 1 stays verifiable.

For why there are two versions, see {ref}`hash-version-2`.

## Version 1

### Payload hash

`payload_hash` is the SHA-256 digest of the event's `payload`, canonicalized directly.
It carries no wrapping fields.

### Units hash

`units_hash` wraps the event's units in a header of three fields.

| Field | Value |
|---|---|
| `v` | `1` (`HASH_VERSION_1`). |
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

### Event hash

`event_hash` wraps eleven fields.

| Field | Value |
|---|---|
| `v` | `1` (`HASH_VERSION_1`). |
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

## Version 2

Version 2 has four digests: the payload, each single unit, the units, and the event.
Every version 2 digest over content takes a salt.
A salt is `SALT_BYTES` random bytes, which is 32, and it enters the hashed object as 64 lowercase hexadecimal characters.
`new_salt` draws a salt from the operating system's random source through `secrets`.

### Payload hash

`payload_hash_v2(payload, salt)` wraps the payload in four fields.

| Field | Value |
|---|---|
| `v` | `2` (`HASH_VERSION_2`). |
| `domain` | `"previously/payload"` (`PAYLOAD_DOMAIN`). |
| `salt` | The payload's salt as hexadecimal. |
| `payload` | The event's `payload` as an object. |

### Unit digest

`unit_digest` takes keyword arguments and hashes one unit in eight fields.

| Field | Value |
|---|---|
| `v` | `2` (`HASH_VERSION_2`). |
| `domain` | `"previously/unit"` (`UNIT_DOMAIN`). |
| `salt` | The unit's salt as hexadecimal. |
| `seq` | The unit's position within the event. |
| `content` | The unit's text. |
| `start_ms` | The start offset in milliseconds, or `null`. |
| `end_ms` | The end offset in milliseconds, or `null`. |
| `speaker` | The speaker's name, or `null`. |

### Units hash

`units_hash_v2(digests)` takes a mapping from `seq` to unit digest and wraps the digests in three fields.

| Field | Value |
|---|---|
| `v` | `2` (`HASH_VERSION_2`). |
| `domain` | `"previously/units"` (`UNITS_DOMAIN`), the domain of version 1. |
| `units` | The unit digests as hexadecimal, sorted by `seq`. |

`units_hash_v2` sorts the mapping by `seq` itself.
`seq` doesn't stand in the list, because every unit digest covers its own.
An event without units has the units hash of an empty list.

### Event hash

`event_hash_v2` takes the arguments of `event_hash` and wraps the same eleven fields.
The one difference is `v`, which is `2` (`HASH_VERSION_2`).
`payload` carries the version 2 payload hash, and `units` carries the version 2 units hash.

## Pinned test vectors

```{warning}
Do not recompute these values.
They are pinned in `tests/test_hashing.py`, and recomputing them to make a test pass destroys the proof that the hash is reproducible.
A deliberate change to the hash range gets a new version and a vector of its own beside these; see {ref}`canonicalization`.
```

### Version 1

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

### Version 2

`tests/test_hashing.py` pins a second vector, below the first.
Its inputs are the inputs of the version 1 vector, plus three fixed salts.

| Salt | Value |
|---|---|
| payload | `404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f`, the bytes 64 to 95 |
| unit `1` | `606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f`, the bytes 96 to 127 |
| unit `2` | `808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f`, the bytes 128 to 159 |

These inputs produce the following digests, as hexadecimal.

| Digest | Value |
|---|---|
| `payload_hash_v2` | `5342ceb35fbc3d8dedddfa72adbc75380347a7179aad95cdb201cbc51d6c0c39` |
| `unit_digest`, unit `1` | `a86bc83e609f7686c3697f011e0792f8c52b3e5dab0553bc2551b6e5964f836f` |
| `unit_digest`, unit `2` | `83d20dfe310bb300e408dfb8eb62c6176dc2806d562e3af70581f4c1ee413d34` |
| `units_hash_v2` | `af0a6ca8f38722aed8e2c801a6753cb620515ca5918364b70f1077fa06c6fc49` |
| `event_hash_v2` | `649d57e7656dc7a62c02e35fb75d30b0212b100ec20ce9dde7e1e34b5339e484` |

`units_hash_v2` of an empty mapping, the units hash of an event without units, is `12360633d51803183369cb1eb37230e63427af0800125eb7a38af155dd1cd3d9`.

The canonical JSON bytes that SHA-256 runs over, for the payload, the two units, the units and the event:

```json
{"domain":"previously/payload","payload":{"evidence":"verbatim","text":"Preis bleibt 1000 Euro."},"salt":"404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f","v":2}
```

```json
{"content":"Preis bleibt 1000 Euro.","domain":"previously/unit","end_ms":null,"salt":"606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f","seq":1,"speaker":null,"start_ms":null,"v":2}
```

```json
{"content":"Bitte bestätigen.","domain":"previously/unit","end_ms":2500,"salt":"808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f","seq":2,"speaker":"Anna","start_ms":1500,"v":2}
```

```json
{"domain":"previously/units","units":["a86bc83e609f7686c3697f011e0792f8c52b3e5dab0553bc2551b6e5964f836f","83d20dfe310bb300e408dfb8eb62c6176dc2806d562e3af70581f4c1ee413d34"],"v":2}
```

```json
{"domain":"previously/event","external_id":"nachricht-1","id":42,"kind":"observation","occurred_at":"2026-10-01T09:00:00.000000Z","payload":"5342ceb35fbc3d8dedddfa72adbc75380347a7179aad95cdb201cbc51d6c0c39","prev":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","recorded_at":"2026-10-02T14:23:45.123456Z","source":"email","units":"af0a6ca8f38722aed8e2c801a6753cb620515ca5918364b70f1077fa06c6fc49","v":2}
```
