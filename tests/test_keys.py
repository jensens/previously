# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Identities out of a directory, one file per recipient ({ref}`blobs`)."""

from previously.core.sealing import recipient_of
from previously.storage.errors import IdentityUnreadable
from previously.storage.keys import DirectoryKeys
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path


def _directory(tmp_path: Path) -> Path:
    keys = tmp_path / "keys"
    keys.mkdir()
    return keys


def test_the_file_named_after_the_recipient_holds_its_identity(
    tmp_path: Path, age_identity: str
) -> None:
    keys = _directory(tmp_path)
    recipient = recipient_of(age_identity)
    (keys / recipient).write_text(age_identity + "\n", encoding="utf-8")
    assert DirectoryKeys(str(keys)).identity(recipient) == age_identity


def test_comment_lines_as_age_keygen_writes_them_are_skipped(
    tmp_path: Path, age_identity: str
) -> None:
    keys = _directory(tmp_path)
    recipient = recipient_of(age_identity)
    (keys / recipient).write_text(
        f"# created: 2026-10-05T09:00:00+02:00\n# public key: {recipient}\n\n{age_identity}\n",
        encoding="utf-8",
    )
    assert DirectoryKeys(str(keys)).identity(recipient) == age_identity
    # A file with nothing but comments holds no identity.
    (keys / recipient).write_text(f"# public key: {recipient}\n\n", encoding="utf-8")
    assert DirectoryKeys(str(keys)).identity(recipient) is None


def test_a_missing_file_is_none(tmp_path: Path, age_identity: str) -> None:
    keys = _directory(tmp_path)
    assert DirectoryKeys(str(keys)).identity(recipient_of(age_identity)) is None


SHORT = "age1" + "q" * 57
OVERLONG = "age1" + "q" * 300


@pytest.mark.parametrize(
    "key_id",
    ["../x", "/etc/passwd", "age1../x", "", "AGE1ABC", SHORT, OVERLONG],
    ids=["parent", "absolute", "age1-parent", "empty", "upper-case", "short", "overlong"],
)
def test_a_key_id_that_is_not_a_recipient_never_reaches_the_disk(
    tmp_path: Path, key_id: str
) -> None:
    """`key_id` comes from the metadata of an object, so whoever can write to
    the bucket chooses it. Every case has a file it would hit if it were
    used as a path, holding a line that would be returned — so only the
    check, not a missing file, can be what makes it `None`: `../x` and
    `age1../x` would each reach a file `x`, `AGE1ABC` and a recipient one
    character short stand in the directory itself. `OVERLONG` is a name no
    file system takes, and without the check it raised `OSError: File name
    too long` instead of being `None`."""
    keys = _directory(tmp_path)
    (tmp_path / "x").write_text("AGE-SECRET-KEY-OUTSIDE\n", encoding="utf-8")
    (keys / "age1..").mkdir()
    (keys / "age1.." / "x").write_text("AGE-SECRET-KEY-INSIDE\n", encoding="utf-8")
    (keys / "AGE1ABC").write_text("AGE-SECRET-KEY-UPPER\n", encoding="utf-8")
    (keys / SHORT).write_text("AGE-SECRET-KEY-SHORT\n", encoding="utf-8")
    assert DirectoryKeys(str(keys)).identity(key_id) is None


def test_a_file_that_cannot_be_read_is_a_storage_error_that_shows_no_content(
    tmp_path: Path, age_identity: str
) -> None:
    """A directory where the identity file should be: the file is there and
    cannot be read, which is a fault in the key directory and not a missing
    key, so it is not `None` — and not a bare `OSError` either."""
    keys = _directory(tmp_path)
    recipient = recipient_of(age_identity)
    (keys / recipient).mkdir()
    with pytest.raises(IdentityUnreadable) as caught:
        DirectoryKeys(str(keys)).identity(recipient)
    assert recipient in str(caught.value)
    assert "IsADirectoryError" in str(caught.value)


def test_the_provider_does_not_show_what_it_holds(tmp_path: Path, age_identity: str) -> None:
    keys = _directory(tmp_path)
    recipient = recipient_of(age_identity)
    (keys / recipient).write_text(age_identity + "\n", encoding="utf-8")
    provider = DirectoryKeys(str(keys))
    assert provider.identity(recipient) == age_identity
    assert str(keys) in repr(provider)
    assert age_identity not in repr(provider)
    assert "AGE-SECRET-KEY" not in repr(provider)
