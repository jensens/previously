# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The identity of an artifact: what has to be equal for two sightings to be
the same artifact ({ref}`artifact-identity`)."""

from previously.core.identity import artifact_hash_of

import hashlib


def test_the_order_of_the_keys_does_not_matter() -> None:
    first = artifact_hash_of({"text": "Hello", "attachments": ["a", "b"]})
    second = artifact_hash_of({"attachments": ["a", "b"], "text": "Hello"})
    assert first == second


def test_one_character_different_is_another_artifact() -> None:
    assert artifact_hash_of({"text": "Hello"}) != artifact_hash_of({"text": "Hellp"})


def test_it_is_the_sha256_of_the_canonical_form() -> None:
    """Spelled out, so that a second canonicalisation beside `canonical`
    would fail here: sorted keys, no whitespace, UTF-8 unescaped."""
    expected = hashlib.sha256('{"attachments":[],"text":"café"}'.encode()).digest()
    assert artifact_hash_of({"text": "café", "attachments": []}) == expected
