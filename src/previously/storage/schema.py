# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The tables as SQLAlchemy Core. No ORM (architecture §10.1, frozen design record)."""

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import SmallInteger
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TIMESTAMP


metadata = MetaData()

event = Table(
    "event",
    metadata,
    # The id comes from the predecessor, not out of a sequence: a sequence
    # guarantees no commit order, and then id order diverges from chain order
    # ({ref}`hash-chain`).
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("kind", Text, nullable=False),
    Column("recorded_at", TIMESTAMP(timezone=True), nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("prev_hash", LargeBinary),
    Column("hash", LargeBinary, nullable=False),
    Column("payload_hash", LargeBinary, nullable=False),
    # Mirrors payload_hash: the digest stands in the row, the content in
    # `unit`. That makes the event hash cover the units without containing
    # them — and the erasure seam stays open for them ({ref}`tombstone-seam`).
    # In version 2 it is taken over the stored `unit.digest`, so it stays
    # computable for an event whose units have lost their content.
    Column("units_hash", LargeBinary, nullable=False),
    # NULL = tombstone after an erasure. payload_hash stays, the chain holds.
    Column("payload", JSONB),
    # Which hash format the check computes for this row ({ref}`hash-version-2`).
    # The default writes down what holds for every row older than the column:
    # it is version 1, and no hash had to be computed again to say so.
    Column("hash_version", SmallInteger, nullable=False, server_default=text("1")),
    # The salt of the version 2 payload digest; NULL on a version 1 row.
    Column("payload_salt", LargeBinary),
    CheckConstraint("kind IN ('observation','assertion','action')", name="event_kind_check"),
    # A salt goes with its payload: a tombstone that kept the salt would leave
    # a guesser everything but the content ({ref}`hash-version-2`).
    CheckConstraint(
        "payload IS NOT NULL OR payload_salt IS NULL",
        name="event_payload_salt_check",
    ),
    # Correction K-1: SQL `NULL` is the tombstone, JSON `null` must not be
    # able to pass for one.
    #
    # psycopg turns **both** into Python `None`, so `row.payload is None` in
    # `core/verify.py` cannot tell them apart. Measured against a real
    # PostgreSQL 17: `UPDATE event SET payload = 'null'::jsonb` left
    # `verify() -> []`, because the check took the row for a tombstone and
    # skipped its payload — while `SELECT id FROM event WHERE payload IS NULL`
    # did **not** list the row. Content silently and permanently erased for
    # the check, and invisible to every piece of bookkeeping that asks the
    # database rather than Python.
    #
    # This constraint **restricts nothing the contract allows.** The payload
    # range is `Mapping[str, object]`, that is a JSON object
    # ({ref}`payload-range`); a JSON array, a scalar or `null` were never
    # permissible there. The database only enforces what the specification
    # already presupposed.
    #
    # And that is the better half of it: the stage 1a specification
    # §3.4 (frozen design record) prescribes `payload IS NULL`, the code asks
    # `row.payload is None` — the two were never equivalent. With this
    # constraint they are, because JSON `null` can no longer stand in the
    # column. The code is not being bent to fit the spec; the database is made
    # to enforce what the spec took for granted.
    #
    # The limit this closed: until stage 1c a forger gained nothing here that
    # `payload = NULL` would not also give, since both left the check
    # satisfied. The sharpness was that the disclosed limit
    # ({ref}`tombstone-seam`) and the redemption it announced — a tombstone
    # without a redaction becomes a finding — would not have caught this case,
    # because it was no tombstone *in the sense of the query*. That redemption
    # exists now ({ref}`erasure`), and `payload = NULL` without a redaction is
    # a finding; this constraint is what keeps JSON `null` from slipping past
    # it.
    CheckConstraint(
        "payload IS NULL OR jsonb_typeof(payload) = 'object'",
        name="event_payload_object_check",
    ),
)

Index("event_occurred_idx", event.c.occurred_at)
Index("event_kind_occurred_idx", event.c.kind, event.c.occurred_at)
Index("event_hash_idx", event.c.hash, unique=True)

# Together with event_pkey this carries the entire concurrency control for
# the chain position ({ref}`concurrency`): no advisory lock, no FOR UPDATE on
# the tip, but two unique indexes decide which writer gets the position —
# `append` and an erasure alike. The loser re-reads the tip and retries. The
# one row lock in the system, an erasure's `FOR UPDATE`, is on the erased
# event and orders two erasures of the same target, not the chain.
#
# NULLS NOT DISTINCT is not optional: without it several NULL count as
# distinct, and every process could write its own genesis entry
# (prev_hash IS NULL) — that is, precisely the branching this index is meant
# to prevent.
Index(
    "event_prev_hash_idx",
    event.c.prev_hash,
    unique=True,
    postgresql_nulls_not_distinct=True,
)

unit = Table(
    "unit",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    # NULL = tombstone of an erased unit, the counterpart of `event.payload`.
    Column("content", Text),
    Column("start_ms", Integer),
    Column("end_ms", Integer),
    Column("speaker", Text),
    # The unit's own version 2 digest and its salt ({ref}`hash-version-2`);
    # NULL on a version 1 unit.
    Column("digest", LargeBinary),
    Column("salt", LargeBinary),
    PrimaryKeyConstraint("event_id", "seq"),
    CheckConstraint("seq >= 1", name="unit_seq_check"),
    # An erased unit keeps its `seq` and its `digest`, which the units hash
    # needs, and nothing else: not the salt, which a guesser would need, and
    # not speaker and timestamps, which say something of their own.
    CheckConstraint(
        "content IS NOT NULL OR "
        "(salt IS NULL AND speaker IS NULL AND start_ms IS NULL AND end_ms IS NULL)",
        name="unit_tombstone_check",
    ),
)

source_key = Table(
    "source_key",
    metadata,
    Column("source", Text, nullable=False),
    Column("external_id", Text, nullable=False),
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    PrimaryKeyConstraint("source", "external_id"),
    # At most one source attribution per event. Without this constraint
    # several (source, external_id) could point at the same event, and then it
    # would not be determined *which* source attribution belongs in the event
    # hash — the hash needs uniqueness ({ref}`hash-chain`). `append` writes
    # only one row per event anyway; the constraint writes down what already
    # holds instead of leaving it to the whim of future callers.
    UniqueConstraint("event_id", name="source_key_event_id_key"),
)

# The register of blobs ({ref}`blobs`): which event names which blob, so that
# "which events use this blob" is a query and not a pass over every payload.
# It carries no truth of its own — the reference in `payload.blobs` is what
# the event hash covers — and `verify` holds it against the payload. One row
# per distinct blob of an event: the same content attached twice is two
# references in the payload and one row here.
event_blob = Table(
    "event_blob",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    # The SHA-256 of the plaintext, as bytes; the payload names it in hex.
    Column("sha256", LargeBinary, nullable=False),
    PrimaryKeyConstraint("event_id", "sha256"),
    CheckConstraint("octet_length(sha256) = 32", name="event_blob_sha256_check"),
)

# The primary key answers "the blobs of an event"; this index answers the
# other direction.
Index("event_blob_sha256_idx", event_blob.c.sha256)

# --- Projections ({ref}`projections`) ---------------------------------------
#
# Derivable and disposable (architecture §4.4, frozen design record): these
# tables carry no truth of their own, so they carry no foreign keys onto one
# another — only onto `event`, because a projection of an event that does not
# exist must never be built. Prefix `p_`.

projection_state = Table(
    "projection_state",
    metadata,
    Column("name", Text, primary_key=True),
    # 0 = nothing built yet. Unambiguous because events number from 1.
    Column("up_to_id", BigInteger, nullable=False),
    # The rebuild trigger: the worker compares it with the version the code
    # declares, and any difference — not only a lower one — empties the table
    # and starts over.
    Column("version", Integer, nullable=False),
    Column("built_at", TIMESTAMP(timezone=True), nullable=False),
)

p_chronicle = Table(
    "p_chronicle",
    metadata,
    Column("event_id", BigInteger, ForeignKey("event.id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True), nullable=False),
    Column("kind", Text, nullable=False),
    # NULL when the payload is a tombstone that no redaction ordered: the kind
    # of evidence lives in the payload, and a tombstone has none. An event a
    # redaction erased has no row here at all, because its units are erased
    # with it; the tombstone without an order keeps its units, which `verify`
    # reports, and NOT NULL here would mean the chronicle could not show them —
    # rows in the log, silently missing.
    Column("evidence", Text),
    # NULL when the event carries no source attribution; `source_key` enforces
    # at most one per event, not at least one.
    Column("source", Text),
    Column("external_id", Text),
    Column("speaker", Text),
    Column("start_ms", Integer),
    Column("end_ms", Integer),
    PrimaryKeyConstraint("event_id", "seq"),
)

# The primary key carries chain order; this index carries time order
# (architecture §4.1, frozen design record, wants both). `chronicle` reads in
# index direction, and the triple is unique, so the output is deterministic.
Index(
    "p_chronicle_occurred_idx",
    p_chronicle.c.occurred_at,
    p_chronicle.c.event_id,
    p_chronicle.c.seq,
)

p_source_stats = Table(
    "p_source_stats",
    metadata,
    Column("source", Text, primary_key=True),
    Column("events", BigInteger, nullable=False),
    Column("units", BigInteger, nullable=False),
    Column("first_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_seen", TIMESTAMP(timezone=True), nullable=False),
    Column("last_event_id", BigInteger, ForeignKey("event.id"), nullable=False),
)
