"""How fast can a short unit be recovered from an unsalted digest?

    uv run python measure_guessing.py

The reason version 2 of the hash format carries a salt. A unit that consists
of a phone number with seven unknown digits is hashed the way a version 2
unit digest would be hashed without a salt, and then every candidate is tried
in order, on one core, in plain Python.

Measured on 2026-10-04 on the development machine: 1,234,568 candidates in
0.72 s, 1.7 million per second. Whoever cites the figure measures it again
and cites their own.
"""

import hashlib
import json
import time

SECRET_DIGITS = 1234567
head = json.dumps(
    {"v": 2, "domain": "previously/unit", "seq": 1, "start_ms": None, "end_ms": None, "speaker": None},
    separators=(",", ":"),
    sort_keys=True,
)[:-1]


def digest(number: int) -> bytes:
    return hashlib.sha256((head + ',"content":"+43 660 %07d"}' % number).encode()).digest()


wanted = digest(SECRET_DIGITS)
started = time.perf_counter()
found = next(candidate for candidate in range(10_000_000) if digest(candidate) == wanted)
elapsed = time.perf_counter() - started
print(
    f"found {found:07d} after {found + 1} candidates in {elapsed:.2f} s"
    f" — {(found + 1) / elapsed:,.0f} per second"
)
