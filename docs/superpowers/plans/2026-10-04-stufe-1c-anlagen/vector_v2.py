"""Scratch: the pinned vector for hash format v=2, computed with hashlib alone.

No project code: the canonical strings are written out by hand, the way the
v=1 vector in tests/test_hashing.py writes them, so the implementation has an
independent figure to meet.

The inputs are the v=1 vector's, plus three fixed salts.
"""

import hashlib

PREV = bytes(range(32))
PAYLOAD_SALT = bytes(range(64, 96))
UNIT_SALTS = (bytes(range(96, 128)), bytes(range(128, 160)))

JCS_PAYLOAD = (
    '{"domain":"previously/payload",'
    '"payload":{"evidence":"verbatim","text":"Preis bleibt 1000 Euro."},'
    f'"salt":"{PAYLOAD_SALT.hex()}","v":2}}'
)
payload_hex = hashlib.sha256(JCS_PAYLOAD.encode("utf-8")).hexdigest()

JCS_UNIT_1 = (
    '{"content":"Preis bleibt 1000 Euro.","domain":"previously/unit","end_ms":null,'
    f'"salt":"{UNIT_SALTS[0].hex()}","seq":1,"speaker":null,"start_ms":null,"v":2}}'
)
JCS_UNIT_2 = (
    '{"content":"Bitte bestätigen.","domain":"previously/unit","end_ms":2500,'
    f'"salt":"{UNIT_SALTS[1].hex()}","seq":2,"speaker":"Anna","start_ms":1500,"v":2}}'
)
unit_hex = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in (JCS_UNIT_1, JCS_UNIT_2)]

JCS_UNITS = f'{{"domain":"previously/units","units":["{unit_hex[0]}","{unit_hex[1]}"],"v":2}}'
units_hex = hashlib.sha256(JCS_UNITS.encode("utf-8")).hexdigest()

JCS_UNITS_EMPTY = '{"domain":"previously/units","units":[],"v":2}'
units_empty_hex = hashlib.sha256(JCS_UNITS_EMPTY.encode("utf-8")).hexdigest()

JCS_EVENT = (
    '{"domain":"previously/event","external_id":"nachricht-1","id":42,'
    '"kind":"observation","occurred_at":"2026-10-01T09:00:00.000000Z",'
    f'"payload":"{payload_hex}",'
    f'"prev":"{PREV.hex()}",'
    '"recorded_at":"2026-10-02T14:23:45.123456Z","source":"email",'
    f'"units":"{units_hex}","v":2}}'
)
event_hex = hashlib.sha256(JCS_EVENT.encode("utf-8")).hexdigest()

print("payload salt   ", PAYLOAD_SALT.hex())
print("unit salts     ", UNIT_SALTS[0].hex(), UNIT_SALTS[1].hex())
print("V2_PAYLOAD_HEX ", payload_hex)
print("V2_UNIT_HEX    ", unit_hex[0], unit_hex[1])
print("V2_UNITS_HEX   ", units_hex)
print("V2_UNITS_EMPTY ", units_empty_hex)
print("V2_EVENT_HEX   ", event_hex)
print(JCS_PAYLOAD)
print(JCS_UNIT_1)
print(JCS_UNIT_2)
print(JCS_UNITS)
print(JCS_EVENT)
