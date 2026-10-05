"""What one-shot AES-256-GCM costs in memory, by blob size — the alternative
the stage 1c specification rejected in favor of the `age` format.

Run once per size in a fresh process, so that the peak belongs to that size:

    uv run --with cryptography python measure_gcm.py <size in MiB>

Measured on 2026-10-04 and again on 2026-10-05 on the development machine:

      64 MiB | peak RSS 217 MiB | factor 3.4
     256 MiB | peak RSS 793 MiB | factor 3.1
    1024 MiB | peak RSS 3.1 GiB            (2026-10-04 only)
    2048 MiB | encrypt failed: OverflowError: Data or associated data too
               long. Max 2**31 - 1 bytes

The plaintext, the ciphertext and the decrypted copy are all held at once,
which is what the factor of three is; and the binding refuses anything from
2 GiB on. `cryptography` is not a dependency of the project: the script brings
it along with `--with`. Whoever cites a figure measures it again and cites
their own.
"""

import hashlib
import os
import resource
import sys
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

size_mib = int(sys.argv[1])
plaintext = os.urandom(size_mib * 1024 * 1024)
key = AESGCM.generate_key(bit_length=256)
nonce = os.urandom(12)

started = time.perf_counter()
digest = hashlib.sha256(plaintext).digest()
hashed = time.perf_counter()
try:
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, digest)
except OverflowError as error:
    print(f"{size_mib:>5} MiB | encrypt failed: {type(error).__name__}: {error}")
    raise SystemExit(0) from None
encrypted = time.perf_counter()
recovered = AESGCM(key).decrypt(nonce, ciphertext, digest)
decrypted = time.perf_counter()
assert recovered == plaintext

peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(
    f"{size_mib:>5} MiB | sha256 {hashed - started:6.2f} s | encrypt {encrypted - hashed:6.2f} s"
    f" | decrypt {decrypted - encrypted:6.2f} s | peak RSS {peak_mib:8.0f} MiB"
    f" | factor {peak_mib / size_mib:4.1f}"
)
