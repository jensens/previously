# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The identity of an artifact ({ref}`artifact-identity`).

Two sightings of a source event are the same artifact when what has to be
equal for that is equal. The caller decides what that is and hands it in as a
document; this module only hashes it, in the one canonical form the project
has (`core.canonical`), so that the order of the keys does not matter and the
same document gives the same hash in every runtime.
"""

from previously.core.canonical import canonical
from typing import TYPE_CHECKING

import hashlib


if TYPE_CHECKING:
    from collections.abc import Mapping


def artifact_hash_of(document: Mapping[str, object]) -> bytes:
    """The SHA-256 of the canonical form of `document`.

    Unsalted, unlike the digests of hash format 2: the point of this hash is
    that the same artifact gives it again at the next sighting. Raises
    `InvalidPayload` for whatever the canonical form refuses.
    """
    return hashlib.sha256(canonical(document)).digest()
