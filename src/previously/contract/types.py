# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The connector contract as pure types. No logic, no dependencies."""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import StrEnum


class Evidence(StrEnum):
    """Quality of evidence: the verbatim wording, or a report from memory."""

    VERBATIM = "verbatim"
    RECOLLECTION = "recollection"


@dataclass(frozen=True)
class RawUnit:
    seq: int
    content: str
    start_ms: int | None = None
    end_ms: int | None = None
    speaker: str | None = None


@dataclass(frozen=True)
class BlobRef:
    """A reference from an event to a stored blob ({ref}`blobs`).

    `sha256` is the address, the SHA-256 of the plaintext in 64 lower-case
    hexadecimal characters; `size` the plaintext's size in bytes. `filename`
    belongs to this use of the content, not to the content: the same bytes
    may carry two names at two events.
    """

    sha256: str
    size: int
    media_type: str
    filename: str | None = None


@dataclass(frozen=True)
class ChannelIdentity:
    """An identity as one channel names it: an address in a role, such as
    the sender of a mail ({ref}`artifact-identity`).

    `address` stands as the source wrote it. Lower-casing it, merging two
    spellings, or seeing one person behind two addresses is interpretation,
    and a connector takes in rather than interprets. `name` is the display
    name, when the source carries one.
    """

    channel: str
    role: str
    address: str
    name: str | None = None


@dataclass(frozen=True)
class RawEvent:
    source: str
    external_id: str
    occurred_at: datetime
    evidence: Evidence
    units: tuple[RawUnit, ...]
    # dict[str, object], not a bare dict: pyright (strict) would otherwise
    # infer dict[Unknown, Unknown], because with a bare `dict` the type
    # parameter is not carried over from the annotation. The generic alias is
    # callable and produces the origin type — no difference in behaviour.
    payload: Mapping[str, object] = field(default_factory=dict[str, object])
    # The blobs the event names, stored before it is appended. `append` mixes
    # them into the payload under `blobs`, and an event without any carries
    # no such key.
    blobs: tuple[BlobRef, ...] = ()
    # The SHA-256 over what has to be equal for two sightings of the source
    # event to be the same artifact; the caller decides what that is. `None`
    # means "not given", not "empty", and compares with nothing. `append`
    # mixes it into the payload as hexadecimal under `artifact_hash`, and the
    # identities as a list of objects under `channel_identities`, each only
    # when given ({ref}`artifact-identity`).
    artifact_hash: bytes | None = None
    channel_identities: tuple[ChannelIdentity, ...] = ()


@dataclass(frozen=True)
class Anchor:
    """The tip of the chain at one moment: its `id` and its hash
    ({ref}`external-anchor`).

    Input from outside, like `RawEvent`: the line was written down where the
    database's writer cannot reach, and it comes back in to be checked. It
    carries no time and no signature — the place it is kept supplies the
    "when".
    """

    id: int
    hash: bytes
