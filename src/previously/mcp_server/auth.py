# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The bearer token of an HTTP request, checked before MCP sees the request.

An ASGI wrapper of its own and not the SDK's `TokenVerifier`: with `auth=`
the SDK publishes Protected Resource Metadata, which points a client at an
authorization server, and there is none ({ref}`mcp-token`).
Moving to OAuth replaces this wrapper with the SDK's verifier and changes
nothing else.
The unit specification named the `TokenVerifier` in its §9 (frozen design record),
and decision 1 of the 2026-10-11 MCP read access plan took precedence over
that line, by ruling R-10 of the 2026-10-11 MCP read access plan.

The token is resolved on every request, so a client replaced with a new token
or revoked is locked out from its next request on.
What gets through carries the client's name in `scope["state"]`, under
`CLIENT_STATE`; a header is never an identity.
A request without a valid token ends here with 401 and one sentence, and
writes no access entry: without a client in force there is no principal to
write it for.

One request passes without a token: `GET /healthz`, the readiness probe of a
deployment, matched by its exact path. It runs a trivial query and answers
with a constant body, 200 or 503; it reaches no MCP, shows no data and writes
no access entry, so it has no principal to name. A probe with a token would
need a client of its own, and a client can read whatever its processor may
see ({ref}`mcp-token`).
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
HEALTH_PATH: Final = "/healthz"
READY: Final = "ok"
NOT_READY: Final = "Error: the database does not answer"
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


async def _answer(
    send: Send, status: int, text: str, extra: tuple[tuple[bytes, bytes], ...] = ()
) -> None:
    body = text.encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
                *extra,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _refuse(send: Send) -> None:
    # No `resource_metadata` parameter: there is no authorization server to
    # point at.
    await _answer(send, 401, REFUSAL, ((b"www-authenticate", b"Bearer"),))


def _is_health(scope: Scope) -> bool:
    """Whether the request is the readiness probe: `GET` on exactly that
    path, so that no other path or method gets past the token check."""
    return scope.get("method") == "GET" and scope.get("path") == HEALTH_PATH


def guarded(
    app: ASGIApp, *, resolve: Callable[[str], str | None], ready: Callable[[], bool]
) -> ASGIApp:
    """`app` behind the token check: `resolve` turns a token into the name of
    the client in force, or `None`, and is asked on every request, on a
    worker thread, since it reads the policy from the database. `ready` says
    whether the database answers, for the readiness probe, on a worker thread
    too."""

    async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await app(scope, receive, send)
            return
        if scope["type"] != "http":
            # No websocket route exists, and nothing unauthenticated passes.
            return
        if _is_health(scope):
            if await asyncio.to_thread(ready):
                await _answer(send, 200, READY)
            else:
                await _answer(send, 503, NOT_READY)
            return
        token = bearer_token(scope)
        name = None if token is None else await asyncio.to_thread(resolve, token)
        if name is None:
            await _refuse(send)
            return
        scope.setdefault("state", {})[CLIENT_STATE] = name
        await app(scope, receive, send)

    return wrapper
