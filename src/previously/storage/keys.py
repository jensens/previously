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
from previously.storage.errors import IdentityUnreadable

import re


# An X25519 recipient in its `age1…` spelling, and nothing else: `age1`, then
# 58 characters of the Bech32 alphabet, which leaves out `1`, `b`, `i` and
# `o` and is written in lower case. No `/`, no `.`, and no length a file
# system refuses — `age1` with 300 letters behind it raised `OSError: File
# name too long` before the length was pinned (measured on 2026-10-05).
_RECIPIENT = re.compile(r"age1[02-9ac-hj-np-z]{58}")


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
        reaches `open`. A file that is there and cannot be read raises
        `IdentityUnreadable`; no other `OSError` leaves.
        """
        if _RECIPIENT.fullmatch(key_id) is None:
            return None
        path = self._directory / key_id
        try:
            text = path.read_bytes().decode("utf-8")
            failure = None
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            text = ""
            failure = type(error).__name__
        if failure is not None:
            # The file is there and cannot be read: a permission, a directory
            # in its place, bytes that are not text. That is an operator's
            # problem with the key directory, not a missing key, so it is
            # said as such — with the path and the kind of failure, never
            # with what the file holds.
            #
            # Raised here, after the `except`, and not inside it: an error
            # raised inside keeps the one it replaces as its context, `from
            # None` only hides that from a traceback, and a failed decoding
            # carries every byte it was given — the identity included.
            # Measured on 2026-10-05: raised inside, the context's `repr`
            # held the whole file.
            raise IdentityUnreadable(f"the identity file {str(path)!r} cannot be read: {failure}")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        return None
