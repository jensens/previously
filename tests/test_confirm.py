# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The sealed handle of a writing MCP call, without a server: `now` and the
nonce are passed in, so an expired handle is one sealed at an earlier `now`.

Review focus 4 of the 2026-10-12 assertions plan: a handle redeemed after its
expiry, by another client, or with changed content is refused, each with a
sentence that holds nothing of the content.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from functools import partial
from previously.core.errors import InvalidPayload
from previously.mcp_server.confirm import expiry
from previously.mcp_server.confirm import HANDLE_SECONDS
from previously.mcp_server.confirm import HandleRefused
from previously.mcp_server.confirm import key_of
from previously.mcp_server.confirm import MIN_KEY_CHARS
from previously.mcp_server.confirm import open_handle
from previously.mcp_server.confirm import payload_digest
from previously.mcp_server.confirm import seal
from typing import TYPE_CHECKING

import base64
import hashlib
import hmac
import json
import pytest


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence

KEY = b"k" * 32
NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=UTC)
PRIVATE_TEXT = "PRIVATE-WORDING-OF-A-PROPOSAL"
PAYLOADS: list[Mapping[str, object]] = [
    {"assertion": "obligation", "what": PRIVATE_TEXT, "handle": None, "sources": [{"event": 4}]},
    {"assertion": "decision", "what": "use slate", "handle": None, "sources": [{"event": 5}]},
]

AGAIN = "; call again without confirm for a new one"
NOT_SEALED = "the handle is not one this server sealed" + AGAIN
OTHER_CLIENT = "the handle was sealed for another client" + AGAIN
OTHER_CONTENT = "the handle was sealed for other statements than these" + AGAIN
EXPIRED = "the handle has expired: a handle holds for 10 minutes" + AGAIN


def _sealed(*, client: str = "claude-code", now: datetime = NOW) -> str:
    return seal(KEY, client=client, payloads=PAYLOADS, now=now, nonce="n0nce")


def _opened(
    handle: str,
    *,
    key: bytes = KEY,
    client: str = "claude-code",
    payloads: Sequence[Mapping[str, object]] = PAYLOADS,
    now: datetime = NOW,
) -> str:
    return open_handle(key, handle, client=client, payloads=payloads, now=now)


def _refusal(call: Callable[[], object]) -> str:
    """The sentence `call` is refused with, after holding it to say nothing
    of the content and to name no client."""
    with pytest.raises(HandleRefused) as refused:
        call()
    message = str(refused.value)
    assert PRIVATE_TEXT not in message
    assert "claude-code" not in message
    assert "vibe" not in message
    return message


def _reencoded(handle: str, change: Mapping[str, object]) -> str:
    """The handle with its body changed and sealed again with the right key:
    what only a holder of the key can make."""
    head, _, _ = handle.partition(".")
    body = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
    body.update(change)
    text = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    new_head = base64.urlsafe_b64encode(text).rstrip(b"=").decode()
    mac = hmac.new(KEY, new_head.encode(), hashlib.sha256).digest()
    return f"{new_head}.{base64.urlsafe_b64encode(mac).rstrip(b'=').decode()}"


# --- a handle opens to its nonce ------------------------------------------------------


def test_a_sealed_handle_opens_to_its_nonce() -> None:
    assert _opened(_sealed()) == "n0nce"


def test_a_handle_holds_its_content_only_as_a_digest() -> None:
    handle = _sealed()
    assert PRIVATE_TEXT not in handle
    head, _, _ = handle.partition(".")
    body = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
    assert body == {
        "client": "claude-code",
        "digest": payload_digest(PAYLOADS),
        "expires": int(NOW.timestamp()) + HANDLE_SECONDS,
        "nonce": "n0nce",
    }
    assert "=" not in handle


def test_the_digest_leaves_the_handle_out() -> None:
    """The handle goes into the payload only once it is opened, so the
    digest of the preview and of the write must be the same."""
    with_handle = [{**payload, "handle": "n0nce"} for payload in PAYLOADS]
    assert payload_digest(with_handle) == payload_digest(PAYLOADS)
    assert _opened(_sealed(), payloads=with_handle) == "n0nce"


def test_the_digest_is_of_the_canonical_list() -> None:
    reordered = [dict(reversed(list(payload.items()))) for payload in PAYLOADS]
    assert payload_digest(reordered) == payload_digest(PAYLOADS)
    canonical = json.dumps(
        [{k: v for k, v in p.items() if k != "handle"} for p in PAYLOADS],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert payload_digest(PAYLOADS) == hashlib.sha256(canonical.encode()).hexdigest()


def test_a_payload_the_log_would_not_take_is_refused_as_the_write_path_refuses_it() -> None:
    with pytest.raises(InvalidPayload):
        payload_digest([{"what": "a\x00b"}])


# --- review focus 4: what is refused -----------------------------------------------------


def test_a_handle_for_another_client_is_refused() -> None:
    assert _refusal(lambda: _opened(_sealed(), client="vibe")) == OTHER_CLIENT


def test_a_handle_for_other_content_is_refused() -> None:
    changed = [PAYLOADS[0], {**PAYLOADS[1], "what": "use tiles"}]
    assert _refusal(lambda: _opened(_sealed(), payloads=changed)) == OTHER_CONTENT
    assert _refusal(lambda: _opened(_sealed(), payloads=PAYLOADS[:1])) == OTHER_CONTENT
    assert _refusal(lambda: _opened(_sealed(), payloads=PAYLOADS[::-1])) == OTHER_CONTENT


def test_a_handle_expires_after_ten_minutes() -> None:
    sealed = _sealed()
    assert _opened(sealed, now=NOW + timedelta(seconds=HANDLE_SECONDS - 1)) == "n0nce"
    assert _opened(sealed, now=NOW + timedelta(seconds=HANDLE_SECONDS)) == "n0nce"
    late = NOW + timedelta(seconds=HANDLE_SECONDS + 1)
    assert _refusal(lambda: _opened(sealed, now=late)) == EXPIRED
    assert expiry(NOW) == NOW + timedelta(minutes=10)


def test_a_handle_sealed_with_another_key_is_refused() -> None:
    assert _refusal(lambda: _opened(_sealed(), key=b"q" * 32)) == NOT_SEALED


_ZERO_MAC = base64.urlsafe_b64encode(bytes(32)).rstrip(b"=").decode()


TAMPERED: list[Callable[[str], str]] = [
    lambda handle: handle.partition(".")[0] + "." + _ZERO_MAC,
    lambda handle: "x" + handle,
    lambda handle: handle.replace(".", ""),
    lambda handle: handle.partition(".")[0] + ".",
    lambda handle: handle + "!",
    lambda handle: handle + ".more",
    lambda handle: "",
    lambda handle: "ä.ö",
    lambda handle: "\udc80.\udc80",
]


@pytest.mark.parametrize("tamper", TAMPERED)
def test_a_tampered_handle_is_refused(tamper: Callable[[str], str]) -> None:
    assert _refusal(lambda: _opened(tamper(_sealed()))) == NOT_SEALED


def test_a_body_sealed_with_the_key_but_not_of_the_form_is_refused() -> None:
    """Only a holder of the key can seal one; it is refused all the same."""
    sealed = _sealed()
    assert _opened(_reencoded(sealed, {})) == "n0nce"  # the control: re-sealing alone passes
    for change in ({"expires": "soon"}, {"nonce": ""}, {"extra": 1}, {"client": 7}):
        assert _refusal(partial(_opened, _reencoded(sealed, change))) == NOT_SEALED


def test_a_moment_without_a_zone_is_refused() -> None:
    naive = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="zone"):
        _sealed(now=naive)
    with pytest.raises(ValueError, match="zone"):
        _opened(_sealed(), now=naive)


# --- the key ----------------------------------------------------------------------------


def test_a_key_of_fewer_than_32_characters_or_none_is_no_key() -> None:
    assert MIN_KEY_CHARS == 32
    assert key_of(None) is None
    assert key_of("") is None
    assert key_of("x" * 31) is None
    assert key_of("x" * 32) == b"x" * 32
    assert key_of("ä" * 32) == "ä".encode() * 32  # characters, not bytes
