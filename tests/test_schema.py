# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from previously.storage.schema import metadata
from sqlalchemy import CheckConstraint
from sqlalchemy import Engine
from sqlalchemy import Index
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import cast
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Mapping


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
    a JSON object ({ref}`payload-range`). It also makes the `payload IS NULL`
    of the stage 1a specification §3.4 (frozen design record) and the code's
    `row.payload is None` equivalent, which they never were.
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
def test_a_real_tombstone_stays_permitted_and_is_found_without_a_redaction(db: Engine) -> None:
    """The counter-test to the constraint, and acceptance condition 3 of the
    stage 1a specification §11 (frozen design record): setting `payload` to
    SQL `NULL` must still work and must not break the chain. Without this
    test the constraint could be tightened until the erasure seam closed, and
    nothing would say so.

    The first half holds as it did: SQL `NULL` is permitted where JSON `null`
    is not. The second half turned over with stage 1c, and the name with it
    (it ended in `passes_verification` until then): a tombstone that no
    redaction ordered is a finding now ({ref}`erasure`). It is the only
    finding, though — every hash still holds, so the chain is not broken.

    Goes through `append` and `verify` rather than through raw DDL, because
    that is the path the acceptance condition is about.
    """
    from datetime import datetime
    from datetime import UTC
    from previously.contract.types import Evidence
    from previously.contract.types import RawEvent
    from previously.core.append import append
    from previously.core.units import split_plaintext
    from previously.core.verify import Finding
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
        # The salt goes with the payload, or `event_payload_salt_check`
        # refuses the statement (ruling P-1 of the 2026-10-04 stage 1c plan).
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"))
        assert c.execute(text("SELECT count(*) FROM event WHERE payload IS NULL")).scalar_one() == 1
    assert verify(storage) == [Finding(1, "payload is erased without a redaction")]


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
    be determined *which* source attribution belongs in the event hash
    ({ref}`hash-chain`). Checks at the same time that the constraint really
    stands in the migrated database and is not merely declared in
    `metadata`."""
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


def _declares_nulls_not_distinct(index: Index) -> bool:
    """Reads the declared flag off an `Index` so that pyright strict accepts it.

    `Index.dialect_options` is a `PopulateDict[str, _DialectArgDict]`, a
    two-level registry keyed first by dialect name and then by argument name,
    and SQLAlchemy types it loosely enough that strict mode rejects a bare
    `.get(...).get(...)` chain on it: the member, the argument and the `{}`
    default all come back partially unknown. The `cast` names the shape this
    project relies on, which is what CLAUDE.md prescribes over a
    `# type: ignore` — an ignore would swallow the next drift here along with
    this one.

    The type is named from a measurement, because the first version of this
    comment named the wrong one. `type(index.dialect_options)` is
    `sqlalchemy.util._collections.PopulateDict`; `_DialectArgView` is what
    `dialect_kwargs` returns, the flat view over the same data, which spells
    the key `postgresql_nulls_not_distinct` in one piece instead of two.

    The declaration it reads is `postgresql_nulls_not_distinct=True` in
    `storage/schema.py`; SQLAlchemy splits such a keyword into the dialect name
    and the option name, which is why the lookup is two steps rather than one.
    """
    options = cast("Mapping[str, Mapping[str, object]]", index.dialect_options)
    return bool(options.get("postgresql", {}).get("nulls_not_distinct", False))


@pytest.mark.db
def test_the_declared_nulls_not_distinct_reaches_the_database(db: Engine) -> None:
    """Compares the declared `NULLS NOT DISTINCT` against the database.

    The test above compares index *names*, and a name cannot carry a flag, so
    it stays green when the migration creates `event_prev_hash_idx` without
    the flag. That gap is narrower than it looks, and the measurement is worth
    recording because it corrects the obvious conclusion: dropping the flag in
    the migration turns **two** tests red, this one and
    `test_only_one_genesis_is_permitted`, which inserts a second row with
    `prev_hash IS NULL` and demands an `IntegrityError`. The behaviour is
    guarded already.

    What was unguarded is the agreement between what `metadata` declares and
    what the database has, and this test covers it for **every** declared
    index rather than for the one index whose symptom happens to be tested. It
    also catches the reverse drift, where `metadata` loses the flag while the
    database keeps it, which no behavioural test can see.

    Measured on a migrated database, with the flag removed from the migration:

        event_prev_hash_idx.indnullsnotdistinct  True -> False
        `SELECT indexname` still finds the index  -> the name check stays green
        two rows with prev_hash IS NULL both commit
    """
    declared = {
        index.name: _declares_nulls_not_distinct(index)
        for table in metadata.tables.values()
        for index in table.indexes
    }
    with db.connect() as c:
        rows = c.execute(
            text("""
                SELECT c.relname, i.indnullsnotdistinct
                FROM pg_index i
                JOIN pg_class c ON c.oid = i.indexrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
            """)
        ).all()
    present = {name: flag for name, flag in rows if name in declared}
    assert present == declared


def _violated_constraint(error: IntegrityError) -> object:
    """The name of the constraint the database reports, out of the psycopg
    diagnosis — by name and not by a substring of the message, for the reason
    `test_a_json_null_payload_is_refused` gives."""
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


_INSERT_EVENT = text(
    "INSERT INTO event (id, kind, recorded_at, occurred_at, prev_hash, hash, "
    "payload_hash, units_hash, payload, hash_version, payload_salt) VALUES "
    "(1, 'observation', now(), now(), NULL, :h, :p, :u, '{}'::jsonb, 2, :salt)"
)


@pytest.mark.db
def test_hash_version_defaults_to_1_for_a_row_that_does_not_say(db: Engine) -> None:
    """The default is what makes the migration lossless: every row written
    before the column existed is version 1, and `DEFAULT 1` says so without a
    single hash being computed again ({ref}`hash-version-2`)."""
    with db.begin() as c:
        c.execute(
            text(
                "INSERT INTO event (id, kind, recorded_at, occurred_at, prev_hash, "
                "hash, payload_hash, units_hash, payload) VALUES "
                "(1, 'observation', now(), now(), NULL, :h, :p, :u, '{}'::jsonb)"
            ),
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32},
        )
        version = c.execute(text("SELECT hash_version FROM event WHERE id = 1")).scalar_one()
    assert version == 1


@pytest.mark.db
def test_a_salt_beside_a_payload_tombstone_is_refused(db: Engine) -> None:
    """A salt is erased together with its content, or the erasure leaves half
    of what a guesser needs ({ref}`hash-version-2`). The constraint refuses
    the half-done erasure; the whole one goes through."""
    with db.begin() as c:
        c.execute(
            _INSERT_EVENT,
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32, "salt": b"\x06" * 32},
        )
    with pytest.raises(IntegrityError) as caught, db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))
    assert _violated_constraint(caught.value) == "event_payload_salt_check"

    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"))
        assert c.execute(text("SELECT payload_hash FROM event WHERE id = 1")).scalar_one() == (
            b"\x02" * 32
        )


@pytest.mark.db
def test_a_unit_tombstone_keeps_nothing_but_its_seq_and_its_digest(db: Engine) -> None:
    """An erased unit keeps `seq` and `digest`, which the units hash needs, and
    nothing else: not the salt, which a guesser would need, and not speaker or
    timestamps, which are content of their own. Each of the four left standing
    alone is refused."""
    with db.begin() as c:
        c.execute(
            _INSERT_EVENT,
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32, "salt": b"\x06" * 32},
        )
        c.execute(
            text(
                "INSERT INTO unit (event_id, seq, content, start_ms, end_ms, speaker, "
                "digest, salt) VALUES (1, 1, 'Text', 10, 20, 'Anna', :d, :s)"
            ),
            {"d": b"\x07" * 32, "s": b"\x08" * 32},
        )
    # One statement per column left standing, each written out in full: each
    # is the erasure that forgot that one column.
    half_done = {
        "salt": "UPDATE unit SET content = NULL, speaker = NULL, start_ms = NULL, end_ms = NULL",
        "speaker": "UPDATE unit SET content = NULL, salt = NULL, start_ms = NULL, end_ms = NULL",
        "start_ms": "UPDATE unit SET content = NULL, salt = NULL, speaker = NULL, end_ms = NULL",
        "end_ms": "UPDATE unit SET content = NULL, salt = NULL, speaker = NULL, start_ms = NULL",
    }
    for kept, statement in half_done.items():
        with pytest.raises(IntegrityError) as caught, db.begin() as c:
            c.execute(text(statement))
        assert _violated_constraint(caught.value) == "unit_tombstone_check", kept

    with db.begin() as c:
        c.execute(
            text(
                "UPDATE unit SET content = NULL, salt = NULL, speaker = NULL, "
                "start_ms = NULL, end_ms = NULL WHERE event_id = 1"
            )
        )
        assert c.execute(text("SELECT digest FROM unit WHERE event_id = 1")).scalar_one() == (
            b"\x07" * 32
        )


@pytest.mark.db
def test_a_register_row_needs_a_hash_of_32_bytes(db: Engine) -> None:
    """A row of `event_blob` names a SHA-256, which is 32 bytes and nothing
    else ({ref}`blobs`): 31 are refused by name, and 32 go through."""
    with db.begin() as c:
        c.execute(
            _INSERT_EVENT,
            {"h": b"\x01" * 32, "p": b"\x02" * 32, "u": b"\x05" * 32, "salt": b"\x06" * 32},
        )
    insert = text("INSERT INTO event_blob (event_id, sha256) VALUES (1, :s)")
    with pytest.raises(IntegrityError) as caught, db.begin() as c:
        c.execute(insert, {"s": b"\x09" * 31})
    assert _violated_constraint(caught.value) == "event_blob_sha256_check"

    with db.begin() as c:
        c.execute(insert, {"s": b"\x09" * 32})
        assert c.execute(text("SELECT count(*) FROM event_blob")).scalar_one() == 1


def _check_names(table: Table) -> set[str]:
    """The names of the `CHECK` constraints `metadata` declares on `table`."""
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


@pytest.mark.db
def test_the_declared_columns_match_the_migrated_database(db: Engine) -> None:
    """Every table in `metadata` against the migrated database: the column
    names with their `NOT NULL`, and the names of the `CHECK` constraints.

    Before this test only the index names were held against the database, so
    a column declared in `schema.py` and missing from the migration reached no
    gate: `metadata` is what the code reads, the migration is what the
    database has, and nothing compared the two.
    """
    with db.connect() as c:
        columns = c.execute(
            text(
                "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public'"
            )
        ).all()
        checks = c.execute(
            text(
                "SELECT cl.relname, co.conname FROM pg_constraint co "
                "JOIN pg_class cl ON cl.oid = co.conrelid "
                "JOIN pg_namespace n ON n.oid = cl.relnamespace "
                "WHERE n.nspname = 'public' AND co.contype = 'c'"
            )
        ).all()
    for table in metadata.tables.values():
        declared = {column.name: column.nullable for column in table.columns}
        present = {
            column: nullable == "YES" for name, column, nullable in columns if name == table.name
        }
        assert present == declared, table.name
        assert {conname for relname, conname in checks if relname == table.name} == _check_names(
            table
        ), table.name


@pytest.mark.db
def test_the_projection_tables_exist(db: Engine) -> None:
    """Stage 1b adds three tables ({ref}`projections`); the migration has to
    create all three, the metadata has to declare all three, and the two
    have to agree — `test_the_declared_indexes_exist_in_the_migrated_database`
    above covers the index the same way."""
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
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= names
    assert {"projection_state", "p_chronicle", "p_source_stats"} <= set(metadata.tables)


@pytest.mark.db
def test_the_watermark_table_is_declared_and_migrated(db: Engine) -> None:
    """The watermark table stands in `metadata` and in the migrated database,
    with the primary key the store's upsert depends on: `ON CONFLICT` names
    `connector`, and without that key a second write would add a row instead
    of replacing one. The columns and their `NOT NULL` are held by
    `test_the_declared_columns_match_the_migrated_database` above."""
    assert "watermark" in metadata.tables
    with db.connect() as c:
        key = set(
            c.execute(
                text(
                    "SELECT a.attname FROM pg_index i "
                    "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                    "WHERE i.indrelid = 'watermark'::regclass AND i.indisprimary"
                )
            )
            .scalars()
            .all()
        )
    assert key == {"connector"}
