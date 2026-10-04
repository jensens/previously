# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Identities out of a directory, one file per recipient ({ref}`blobs`)."""

from previously.core.sealing import recipient_of
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


@pytest.mark.parametrize("key_id", ["../x", "/etc/passwd", "age1../x", "", "AGE1ABC"])
def test_a_key_id_that_is_not_a_recipient_never_reaches_the_disk(
    tmp_path: Path, key_id: str
) -> None:
    """`key_id` comes from the metadata of an object, so whoever can write to
    the bucket chooses it. The control beside the directory is a file that
    `../x` would hit, holding a line that would be returned if it were read;
    `AGE1ABC` stands in the directory itself, so that only the check — not a
    missing file — can be what makes it `None`."""
    keys = _directory(tmp_path)
    (tmp_path / "x").write_text("AGE-SECRET-KEY-OUTSIDE\n", encoding="utf-8")
    (keys / "AGE1ABC").write_text("AGE-SECRET-KEY-UPPER\n", encoding="utf-8")
    assert DirectoryKeys(str(keys)).identity(key_id) is None


def test_the_provider_does_not_show_what_it_holds(tmp_path: Path, age_identity: str) -> None:
    keys = _directory(tmp_path)
    recipient = recipient_of(age_identity)
    (keys / recipient).write_text(age_identity + "\n", encoding="utf-8")
    provider = DirectoryKeys(str(keys))
    assert provider.identity(recipient) == age_identity
    assert str(keys) in repr(provider)
    assert age_identity not in repr(provider)
    assert "AGE-SECRET-KEY" not in repr(provider)
