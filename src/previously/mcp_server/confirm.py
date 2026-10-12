# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The sealed handle of a writing call of the MCP server ({ref}`mcp-tools`).

A writing tool takes two calls. The first checks the statements, shows them,
and hands back a handle; the second repeats the arguments with
`confirm=<handle>`, and only that one writes. The handle is

    base64url(canonical JSON {client, digest, expires, nonce}) "." base64url(HMAC-SHA256)

without padding. `digest` is the SHA-256 of the canonical JSON list of the
payloads to be written, each without its `handle`, so the handle names a
content without carrying a word of it. `expires` is ten minutes after the
first call, in whole seconds since the epoch. The key is the setting
`PREVIOUSLY_MCP_CONFIRM_KEY`, which only the MCP server is given; rotating it
makes the open handles fail and nothing else.

The handle needs no state of its own. Its `nonce` goes into the payload of
every statement written, and the write path finds a batch that carries it
and answers with its ids instead of writing again, so confirming twice, or
again after a lost answer, writes once (`core/assertions.py`).

Pure: no clock and no randomness. `now` is the caller's, and so is the nonce,
which the server draws with `secrets`. The canonical form is the one the log
hashes payloads in (`core/canonical.py`): each payload is serialized by it,
and the list of them is those joined by commas inside brackets, which is the
same JSON a canonical serializer gives the list. A payload the log would not
take is refused here with the same `InvalidPayload` as on the write path.

A refusal is one sentence that names neither the content nor a client: it
reaches the client that presented the handle, which may not be the one it
was sealed for.
"""

from previously.core.canonical import canonical
from previously.core.errors import PreviouslyError
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import base64
import binascii
import hashlib
import hmac
import json


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime

HANDLE_SECONDS: Final = 600
MIN_KEY_CHARS: Final = 32
KEY_VARIABLE: Final = "PREVIOUSLY_MCP_CONFIRM_KEY"

_AGAIN: Final = "; call again without confirm for a new one"
_NOT_SEALED: Final = "the handle is not one this server sealed" + _AGAIN
_OTHER_CLIENT: Final = "the handle was sealed for another client" + _AGAIN
_OTHER_CONTENT: Final = "the handle was sealed for other statements than these" + _AGAIN
_EXPIRED: Final = (
    f"the handle has expired: a handle holds for {HANDLE_SECONDS // 60} minutes" + _AGAIN
)
_BODY_KEYS: Final = frozenset({"client", "digest", "expires", "nonce"})


class HandleRefused(PreviouslyError):
    """A handle that does not let the call write: one sentence, no content."""


def key_of(text: str | None) -> bytes | None:
    """The key a setting holds, or `None` when it is unset or shorter than
    `MIN_KEY_CHARS` characters; without a key the server does not write."""
    if text is None or len(text) < MIN_KEY_CHARS:
        return None
    return text.encode("utf-8")


def payload_digest(payloads: Sequence[Mapping[str, object]]) -> str:
    """The hex SHA-256 of the canonical list of `payloads`, each without its
    `handle`. Raises `InvalidPayload` for a payload the log would not take."""
    members = [canonical({k: v for k, v in p.items() if k != "handle"}) for p in payloads]
    return hashlib.sha256(b"[" + b",".join(members) + b"]").hexdigest()


def _seconds(now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now has no zone")
    return int(now.timestamp())


def expiry(now: datetime) -> datetime:
    """When a handle sealed at `now` stops holding, to the second."""
    return now.fromtimestamp(_seconds(now) + HANDLE_SECONDS, now.tzinfo)


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode(text: str) -> bytes:
    """Strict: a character outside the alphabet is an error, not skipped."""
    padded = text.encode("ascii") + b"=" * (-len(text) % 4)
    return base64.b64decode(padded, altchars=b"-_", validate=True)


def _mac(key: bytes, head: str) -> bytes:
    return hmac.new(key, head.encode("utf-8"), hashlib.sha256).digest()


def seal(
    key: bytes,
    *,
    client: str,
    payloads: Sequence[Mapping[str, object]],
    now: datetime,
    nonce: str,
) -> str:
    """The handle for writing `payloads` as `client`, holding from `now` for
    `HANDLE_SECONDS`, that opens to `nonce`."""
    body = {
        "client": client,
        "digest": payload_digest(payloads),
        "expires": _seconds(now) + HANDLE_SECONDS,
        "nonce": nonce,
    }
    head = _encode(canonical(body))
    return f"{head}.{_encode(_mac(key, head))}"


def _body(key: bytes, handle: str) -> Mapping[str, object]:
    """The body of a handle sealed with `key`, or `HandleRefused`."""
    head, dot, mac = handle.partition(".")
    try:
        if not dot or not hmac.compare_digest(_mac(key, head), _decode(mac)):
            raise HandleRefused(_NOT_SEALED)
        body = json.loads(_decode(head))
    except (ValueError, binascii.Error) as error:  # UnicodeError and JSONDecodeError among them
        raise HandleRefused(_NOT_SEALED) from error
    # Only the holder of the key can seal a body; one of another form is
    # refused all the same, so that nothing below reads a wrong type.
    if not isinstance(body, dict) or frozenset(cast("dict[str, object]", body)) != _BODY_KEYS:
        raise HandleRefused(_NOT_SEALED)
    found = cast("dict[str, object]", body)
    expires = found["expires"]
    if not (
        all(isinstance(found[name], str) for name in ("client", "digest", "nonce"))
        and found["nonce"]
        and isinstance(expires, int)
        and not isinstance(expires, bool)
    ):
        raise HandleRefused(_NOT_SEALED)
    return found


def open_handle(
    key: bytes,
    handle: str,
    *,
    client: str,
    payloads: Sequence[Mapping[str, object]],
    now: datetime,
) -> str:
    """The nonce of `handle`, if this server sealed it for `client` and for
    exactly `payloads`, and it has not expired at `now`; else `HandleRefused`.

    The seal, the client and the digest are compared with
    `hmac.compare_digest`, so that the time a refusal takes tells nothing of
    how much of them matched. The expiry is a plain comparison of whole
    seconds: the moment it holds is no secret.
    """
    seconds = _seconds(now)
    body = _body(key, handle)
    if not hmac.compare_digest(cast("str", body["client"]).encode(), client.encode()):
        raise HandleRefused(_OTHER_CLIENT)
    digest = payload_digest(payloads)
    if not hmac.compare_digest(cast("str", body["digest"]).encode(), digest.encode()):
        raise HandleRefused(_OTHER_CONTENT)
    if seconds > cast("int", body["expires"]):
        raise HandleRefused(_EXPIRED)
    return cast("str", body["nonce"])
