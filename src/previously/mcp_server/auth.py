# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The bearer token of an HTTP request, checked before MCP sees the request.

An ASGI wrapper of its own and not the SDK's `TokenVerifier`: with `auth=`
the SDK publishes Protected Resource Metadata, which points a client at an
authorization server, and there is none (concept specification, section 7;
decision 1 of the 2026-10-11 MCP read access plan, which takes precedence
over the line of section 9 of the unit specification that names the
`TokenVerifier`, by ruling R-10 of the 2026-10-11 MCP read access plan).
Moving to OAuth replaces this wrapper with the SDK's verifier and changes
nothing else.

The token is resolved on every request, so a client replaced with a new token
or revoked is locked out from its next request on.
What gets through carries the client's name in `scope["state"]`, under
`CLIENT_STATE`; a header is never an identity.
A request without a valid token ends here with 401 and one sentence, and
writes no access entry: without a client in force there is no principal to
write it for.
"""

from typing import Final
from typing import TYPE_CHECKING

import asyncio


if TYPE_CHECKING:
    from collections.abc import Callable
    from starlette.types import ASGIApp
    from starlette.types import Receive
    from starlette.types import Scope
    from starlette.types import Send

CLIENT_STATE: Final = "previously_client"
REFUSAL: Final = "Error: a valid bearer token is required"
_SCHEME: Final = "bearer"


def bearer_token(scope: Scope) -> str | None:
    """The token of an `Authorization: Bearer` header, or `None`."""
    for name, value in scope.get("headers", []):
        if name.lower() != b"authorization":
            continue
        scheme, _, token = value.decode("latin-1").partition(" ")
        token = token.strip()
        if scheme.lower() == _SCHEME and token:
            return token
        return None
    return None


async def _refuse(send: Send) -> None:
    body = REFUSAL.encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
                # No `resource_metadata` parameter: there is no authorization
                # server to point at.
                (b"www-authenticate", b"Bearer"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def guarded(app: ASGIApp, *, resolve: Callable[[str], str | None]) -> ASGIApp:
    """`app` behind the token check: `resolve` turns a token into the name of
    the client in force, or `None`, and is asked on every request, on a
    worker thread, since it reads the policy from the database."""

    async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await app(scope, receive, send)
            return
        if scope["type"] != "http":
            # No websocket route exists, and nothing unauthenticated passes.
            return
        token = bearer_token(scope)
        name = None if token is None else await asyncio.to_thread(resolve, token)
        if name is None:
            await _refuse(send)
            return
        scope.setdefault("state", {})[CLIENT_STATE] = name
        await app(scope, receive, send)

    return wrapper
