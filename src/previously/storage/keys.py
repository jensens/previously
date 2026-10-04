# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Identities out of a directory, one file per recipient ({ref}`blobs`).

A directory of files is the form in which Kubernetes shows a mounted secret,
and on a host with `docker-compose` it is a directory beside the compose
file. A vault with a key management of its own would be a second
implementation behind the same seam, `contract.blobs.KeyProvider`.

The identities pass through as text. This module does not know the `age`
format beyond the shape of a recipient's name, so `storage` stays free of
`pyrage`, and `.importlinter` holds it to that.
"""

from pathlib import Path

import re


# A recipient in its `age1…` spelling: Bech32 is written in lower case, and
# its data part uses lower-case letters and digits only. Nothing else can be
# the name of a file in the directory, and in particular no `/` and no `.`.
_RECIPIENT = re.compile(r"age1[a-z0-9]+")


class DirectoryKeys:
    """Reads the identity for a recipient out of the file named after it.

    The file is the one `age-keygen -o <recipient>` writes, or any file whose
    first line that is neither empty nor a `#` comment is the identity.
    """

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)

    def __repr__(self) -> str:
        # The directory and nothing it holds: an identity is the secret half
        # of a key, and a `repr` ends up in tracebacks and logs.
        return f"DirectoryKeys({str(self._directory)!r})"

    def identity(self, key_id: str) -> str | None:
        """The identity for `key_id`, or `None` when the directory has none.

        `key_id` comes from the metadata of a stored object, and whoever can
        write to the bucket chooses it. So it is checked before it becomes
        part of a path: a `key_id` that is not a recipient's name is `None`
        without the disk being asked, and `../x` or `/etc/passwd` never
        reaches `open`.
        """
        if _RECIPIENT.fullmatch(key_id) is None:
            return None
        try:
            text = (self._directory / key_id).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        return None
