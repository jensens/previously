# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from previously.storage.schema import metadata


@pytest.mark.db
def test_the_tables_exist(db: Engine) -> None:
    with db.connect() as c:
        names = set(
            c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            .scalars()
            .all()
        )
    assert {"event", "unit", "source_key"} <= names


@pytest.mark.db
def test_only_one_genesis_is_permitted(db: Engine) -> None:
    """NULLS NOT DISTINCT: a second prev_hash IS NULL must fail."""
    do_insert = text(
        "INSERT INTO event (id, kind, recorded_at, occurred_at, prev_hash, "
        "hash, payload_hash, units_hash, payload) VALUES (:i, 'observation', "
        "now(), now(), NULL, :h, :p, :u, '{}'::jsonb)"
    )
    with db.begin() as c:
        c.execute(do_insert, {"i": 1, "h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32})
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(do_insert, {"i": 2, "h": b"\x03" * 32, "p": b"\x04" * 32, "u": b"\x05" * 32})


@pytest.mark.db
def test_prev_hash_is_unique(db: Engine) -> None:
    do_insert = text(
        "INSERT INTO event (id, kind, recorded_at, occurred_at, prev_hash, "
        "hash, payload_hash, units_hash, payload) VALUES (:i, 'observation', "
        "now(), now(), :prev, :h, :p, :u, '{}'::jsonb)"
    )
    with db.begin() as c:
        c.execute(
            do_insert,
            {"i": 1, "prev": None, "h": b"\x01" * 32, "p": b"\x00" * 32, "u": b"\x05" * 32},
        )
        c.execute(
            do_insert,
            {"i": 2, "prev": b"\x01" * 32, "h": b"\x02" * 32, "p": b"\x00" * 32, "u": b"\x05" * 32},
        )
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(
            do_insert,
            {"i": 3, "prev": b"\x01" * 32, "h": b"\x09" * 32, "p": b"\x00" * 32, "u": b"\x05" * 32},
        )


@pytest.mark.db
def test_payload_may_be_null_tombstone(db: Engine) -> None:
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'observation', now(), now(), NULL, :h, :p, :u, NULL)"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32},
        )
        count = c.execute(text("SELECT count(*) FROM event")).scalar_one()
    assert count == 1


@pytest.mark.db
def test_a_json_null_payload_is_refused(db: Engine) -> None:
    """Correction K-1: JSON `null` must not be able to pass for a tombstone.

    psycopg turns SQL `NULL` **and** JSON `null` into Python `None`, so
    `row.payload is None` in `core/verify.py` cannot tell them apart.
    Measured against the version before this constraint:

        UPDATE event SET payload = 'null'::jsonb WHERE id = 2

         id | payload IS NULL | jsonb_typeof
          1 | True            | None            <- real tombstone
          2 | False           | null            <- the forgery

        What Python sees:
          id 1: payload=None   is None -> True
          id 2: payload=None   is None -> True   <- indistinguishable

        Tombstone bookkeeping `WHERE payload IS NULL` finds: [1]
        verify() -> []

    Content silently and permanently erased for the check, and invisible to
    any bookkeeping that asks the database instead of Python.

    The constraint restricts nothing the contract allows: the payload range is
    a JSON object (§3.2 of the 1a spec). It also makes §3.4's
    `payload IS NULL` and the code's `row.payload is None` equivalent, which
    they never were.
    """
    with pytest.raises(IntegrityError) as caught, db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'observation', now(), now(), NULL, :h, :p, :u, CAST('null' AS jsonb))"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32},
        )
    # By the constraint name out of the psycopg diagnosis, not by a substring
    # in the message — the same reasoning as in `storage/postgres.py`: the
    # text depends on language and version, the name does not. Without this
    # the test would also be green if some other constraint had fired.
    diag = getattr(caught.value.orig, "diag", None)
    assert getattr(diag, "constraint_name", None) == "event_payload_object_check"


@pytest.mark.db
def test_a_json_array_or_scalar_payload_is_refused(db: Engine) -> None:
    """The same constraint, for the rest of the range it closes. A JSON array
    or a bare scalar is no tombstone, but it is no object either — `canonical`
    takes a `Mapping`, and `verify` would ask `payload_hash` of something that
    the payload range never contained."""
    do_insert = text(
        "INSERT INTO event (id, kind, recorded_at, occurred_at, "
        "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
        "(:i, 'observation', now(), now(), :prev, :h, :p, :u, CAST(:payload AS jsonb))"
    )
    for i, payload in enumerate(["[]", '"text"', "7", "true"], start=1):
        with pytest.raises(IntegrityError), db.begin() as c:
            c.execute(
                do_insert,
                {
                    "i": i,
                    "prev": None,
                    "h": bytes([i]) * 32,
                    "p": b"\x02" * 32,
                    "u": b"\x05" * 32,
                    "payload": payload,
                },
            )


@pytest.mark.db
def test_a_real_tombstone_stays_permitted_and_passes_verification(db: Engine) -> None:
    """The counter-test to the constraint, and acceptance condition 3 of §11:
    setting `payload` to SQL `NULL` must still work and must not break the
    chain. Without this test the constraint could be tightened until the
    erasure seam closed, and nothing would say so.

    Goes through `append` and `verify` rather than through raw DDL, because
    that is the path the acceptance condition is about.
    """
    from datetime import UTC, datetime

    from previously.contract.types import Evidence, RawEvent
    from previously.core.append import append
    from previously.core.units import split_plaintext
    from previously.core.verify import verify
    from previously.storage.postgres import PostgresStorage

    now = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
    storage = PostgresStorage(db)
    append(
        storage,
        [
            RawEvent(
                source="cli",
                external_id=f"e{i}",
                occurred_at=now,
                evidence=Evidence.RECOLLECTION,
                units=split_plaintext(f"content {i}"),
                payload={"note": f"n{i}"},
            )
            for i in (1, 2)
        ],
        recorded_at=now,
    )
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))
        assert c.execute(text("SELECT count(*) FROM event WHERE payload IS NULL")).scalar_one() == 1
    assert verify(storage) == []


@pytest.mark.db
def test_kind_is_restricted(db: Engine) -> None:
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'nonsense', now(), now(), NULL, :h, :p, :u, '{}'::jsonb)"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32},
        )


@pytest.mark.db
def test_units_hash_is_mandatory(db: Engine) -> None:
    """`units_hash` is `NOT NULL`: an event without a units digest is an event
    whose units are not attested (correction K1)."""
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'observation', now(), now(), NULL, :h, :p, NULL, '{}'::jsonb)"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32},
        )


@pytest.mark.db
def test_only_one_source_attribution_per_event(db: Engine) -> None:
    """source_key_event_id_key: without this constraint several
    (source, external_id) could point at the same event, and then it would not
    be determined *which* source attribution belongs in the event hash (§3.1).
    Checks at the same time that the constraint really stands in the migrated
    database and is not merely declared in `metadata`."""
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, "
                "prev_hash, hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'observation', now(), now(), NULL, :h, :p, :u, '{}'::jsonb)"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32},
        )
        c.execute(
            text("INSERT INTO source_key (source, external_id, event_id) VALUES ('cli', 'x1', 1)")
        )
    with pytest.raises(IntegrityError), db.begin() as c:
        c.execute(
            text("INSERT INTO source_key (source, external_id, event_id) VALUES ('cli', 'x2', 1)")
        )


@pytest.mark.db
def test_the_declared_indexes_exist_in_the_migrated_database(db: Engine) -> None:
    """Guards the seam out of ruling T5-b: if an index arises only through raw
    DDL in the migration but is not declared in `metadata`, schema and
    migration diverge — and a future `alembic revision --autogenerate` will
    propose dropping the "superfluous" index again.

    The check goes in one direction only: every index declared in `metadata`
    must exist in the database. The other way round (equality) would be wrong,
    because the database additionally keeps the indexes behind primary keys
    (`event_pkey` and so on), which are no `Index` objects in `metadata`.
    """
    declared = {index.name for table in metadata.tables.values() for index in table.indexes}
    with db.connect() as c:
        present = set(
            c.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"))
            .scalars()
            .all()
        )
    assert declared <= present
