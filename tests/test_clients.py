# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MCP clients: the token, its hash, the write path and the lookup."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.core.clients import add_client
from previously.core.clients import client_for_token
from previously.core.clients import client_rows
from previously.core.clients import mint_token
from previously.core.clients import revoke_client
from previously.core.clients import token_hash
from previously.core.policy import Client
from previously.core.policy import Inference
from previously.core.policy import PolicyRefused
from previously.core.policy import Provider
from previously.core.policy import read_policy
from previously.core.policy import set_policy
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import hashlib
import json
import pytest


if TYPE_CHECKING:
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)

LOCAL = Provider("local", (Inference("local", frozenset({"any"})),), frozenset(), 0, False, True)


def _storage(db: Engine) -> PostgresStorage:
    storage = PostgresStorage(db)
    set_policy(storage, LOCAL, statement="declared", recorded_at=T0)
    return storage


def _policy(storage: PostgresStorage):
    with storage.begin() as conn:
        return read_policy(storage, conn)


def _all_payloads(storage: PostgresStorage) -> str:
    """Every action payload in the log, as text."""
    with storage.begin() as conn:
        return json.dumps(
            [row.payload for row in storage.read_by_kind(conn, "action")], sort_keys=True
        )


def test_a_token_is_long_random_and_new_each_time() -> None:
    tokens = {mint_token() for _ in range(50)}
    assert len(tokens) == 50
    # 32 bytes of URL-safe base64 without padding are 43 characters.
    assert all(len(token) == 43 for token in tokens)


def test_the_hash_is_the_sha256_of_the_token_as_hex() -> None:
    assert token_hash("abc") == hashlib.sha256(b"abc").hexdigest()
    assert len(token_hash("abc")) == 64


@pytest.mark.db
def test_a_client_is_added_and_found_by_its_token(db: Engine) -> None:
    storage = _storage(db)
    event_id, token = add_client(
        storage, "claude-code", processor="local", statement="s", recorded_at=T1
    )
    policy = _policy(storage)
    assert policy.clients == {"claude-code": Client("claude-code", "local", token_hash(token))}
    assert policy.ids[("client", "claude-code")] == event_id
    assert client_for_token(policy, token) == policy.clients["claude-code"]
    assert verify(storage) == []


@pytest.mark.db
def test_a_wrong_token_finds_no_client(db: Engine) -> None:
    """The control of the lookup: the right token finds one."""
    storage = _storage(db)
    _, token = add_client(storage, "a", processor="local", statement="s", recorded_at=T1)
    policy = _policy(storage)
    assert client_for_token(policy, mint_token()) is None
    assert client_for_token(policy, "") is None
    assert client_for_token(policy, token + "x") is None
    assert client_for_token(policy, token) is not None


@pytest.mark.db
def test_the_token_is_in_no_payload_only_its_hash(db: Engine) -> None:
    storage = _storage(db)
    _, token = add_client(storage, "a", processor="local", statement="s", recorded_at=T1)
    stored = _all_payloads(storage)
    assert token not in stored
    # The control: the search finds what is there.
    assert token_hash(token) in stored


@pytest.mark.db
def test_adding_a_name_again_replaces_the_client_and_the_old_token_stops_matching(
    db: Engine,
) -> None:
    storage = _storage(db)
    _, old = add_client(storage, "a", processor="local", statement="first", recorded_at=T1)
    _, new = add_client(storage, "a", processor="local", statement="rotated", recorded_at=T2)
    policy = _policy(storage)
    assert client_for_token(policy, old) is None
    assert client_for_token(policy, new) == Client("a", "local", token_hash(new))
    assert len(policy.clients) == 1


@pytest.mark.db
def test_a_revoked_client_is_gone_and_its_token_matches_nothing(db: Engine) -> None:
    storage = _storage(db)
    _, token = add_client(storage, "a", processor="local", statement="s", recorded_at=T1)
    revoke_client(storage, "a", statement="left", recorded_at=T2)
    policy = _policy(storage)
    assert policy.clients == {}
    assert client_for_token(policy, token) is None
    assert verify(storage) == []


@pytest.mark.db
def test_revoking_a_client_that_does_not_exist_is_refused(db: Engine) -> None:
    storage = _storage(db)
    with storage.begin() as conn:
        before = len(list(storage.read_by_kind(conn, "action")))
    with pytest.raises(PolicyRefused, match='no client "ghost" exists'):
        revoke_client(storage, "ghost", statement="s", recorded_at=T1)
    with storage.begin() as conn:
        assert len(list(storage.read_by_kind(conn, "action"))) == before


@pytest.mark.db
def test_an_undeclared_processor_is_refused_and_nothing_is_written(db: Engine) -> None:
    storage = _storage(db)
    with storage.begin() as conn:
        before = len(list(storage.read_by_kind(conn, "action")))
    with pytest.raises(PolicyRefused, match='the processor "nowhere" is not declared'):
        add_client(storage, "a", processor="nowhere", statement="s", recorded_at=T1)
    with storage.begin() as conn:
        assert len(list(storage.read_by_kind(conn, "action"))) == before
    assert _policy(storage).clients == {}


@pytest.mark.db
def test_the_rows_name_the_client_the_event_and_the_date(db: Engine) -> None:
    storage = _storage(db)
    event_id, _ = add_client(storage, "b", processor="local", statement="s", recorded_at=T1)
    add_client(storage, "a", processor="local", statement="s", recorded_at=T2)
    with storage.begin() as conn:
        rows = client_rows(storage, conn)
    assert [row.client.name for row in rows] == ["a", "b"]
    assert (rows[1].event_id, rows[1].recorded_at) == (event_id, T1)
