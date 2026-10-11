# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MCP clients as principals: a name, a processing chain and a token.

A client is a policy event of the kind `client`. Its token is minted here,
shown once to whoever runs `client add`, and stored only as its SHA-256: the
token is 32 random bytes, so the hash cannot be guessed back, and the log can
carry it without carrying a secret.

A token is checked against the hashes of the clients in force, each with
`hmac.compare_digest`, so that the time a check takes does not tell how many
leading digits were right.
"""

from dataclasses import dataclass
from datetime import datetime
from previously.core.policy import CLIENT
from previously.core.policy import Client
from previously.core.policy import PolicyRefused
from previously.core.policy import read_policy
from previously.core.policy import set_policy
from typing import TYPE_CHECKING

import hashlib
import hmac
import secrets


if TYPE_CHECKING:
    from previously.contract.store import LogStore
    from previously.core.policy import Policy

# Bytes of randomness in a token; `token_urlsafe` turns them into 43 characters.
TOKEN_BYTES = 32


@dataclass(frozen=True)
class ClientRow:
    """A client in force with the event that set it, for `client list`."""

    client: Client
    event_id: int
    recorded_at: datetime


def mint_token() -> str:
    """A new token: 32 random bytes from `secrets`, URL-safe."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_hash(token: str) -> str:
    """The SHA-256 of a token as hex, which is all the log keeps of it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def client_for_token(policy: Policy, token: str) -> Client | None:
    """The client whose token this is, or `None`.

    Every client is compared, with no early exit on a match, so the time does
    not depend on which one matched.
    """
    digest = token_hash(token)
    found: Client | None = None
    for client in policy.clients.values():
        if hmac.compare_digest(client.token_sha256, digest):
            found = client
    return found


def add_client[Conn](
    log: LogStore[Conn], name: str, *, processor: str, statement: str, recorded_at: datetime
) -> tuple[int, str]:
    """Writes a client with a new token and returns the id of the event and
    the token, which is not kept anywhere else.

    A client of that name in force is replaced: its token stops matching with
    the next read of the policy. An undeclared `processor` is refused with
    `PolicyRefused`, and then no token has left this function.
    """
    token = mint_token()
    client = Client(name, processor, token_hash(token))
    event_id = set_policy(log, client, statement=statement, recorded_at=recorded_at)
    return event_id, token


def revoke_client[Conn](
    log: LogStore[Conn], name: str, *, statement: str, recorded_at: datetime
) -> int:
    """Lifts the client of that name, or refuses with `PolicyRefused` when
    none is in force. The revocation repeats the hash it lifts."""
    with log.begin() as conn:
        client = read_policy(log, conn).clients.get(name)
    if client is None:
        raise PolicyRefused(f'no client "{name}" exists')
    return set_policy(log, client, statement=statement, revoked=True, recorded_at=recorded_at)


def client_rows[Conn](log: LogStore[Conn], conn: Conn) -> list[ClientRow]:
    """The clients in force by name, each with its event and its date."""
    policy = read_policy(log, conn)
    wanted = {policy.ids[(CLIENT, name)] for name in policy.clients}
    dates = {
        row.id: row.recorded_at for row in log.read_by_kind(conn, "action") if row.id in wanted
    }
    return [
        ClientRow(client, policy.ids[(CLIENT, name)], dates[policy.ids[(CLIENT, name)]])
        for name, client in sorted(policy.clients.items())
    ]
