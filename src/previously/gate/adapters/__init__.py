# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""What the gate asks of a provider, and what it gets back.

An adapter makes exactly one call per `complete` and never retries: the gate
writes one `model_call` event per attempt, so a client that repeated a
request silently would leave a call that no event accounts for. Both adapters
build their client with `max_retries=0` for that reason.

An adapter answers with the text exactly as the provider returned it. Whether
that text is valid against the schema is the gate's question, not the
adapter's.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from previously.core.errors import PreviouslyError
from typing import Protocol

import re


# How much of a provider's own words an error message may carry. A status
# error quotes the response body, and a body can be long and can echo what
# was sent; a sentence is enough to tell what went wrong.
MAX_DETAIL = 200


@dataclass(frozen=True)
class Request:
    """One call to one model: the prompt halves, the schema the output has to
    meet, and where in the world the provider may process it."""

    model: str
    effort: str | None
    system: str
    user: str
    schema: Mapping[str, object]
    schema_name: str
    inference_geo: str | None


@dataclass(frozen=True)
class Response:
    """The provider's answer. `output` is unchecked text. `reported_geo` is
    where the provider says it processed the call, or `None` if it does not
    say."""

    output: str
    reported_geo: str | None
    model: str
    request_id: str | None
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None


class AdapterError(PreviouslyError):
    """A call failed. One sentence naming the provider and the kind of failure;
    it holds neither the key nor the prompt."""


class Adapter(Protocol):
    """A provider the gate can call."""

    provider: str

    def complete(self, request: Request) -> Response: ...


def adapter_error(provider: str, error: Exception, key: str) -> AdapterError:
    """The `AdapterError` for an exception of a client.

    The class of the exception goes in, and its text too, once every
    occurrence of `key` is gone from it: a server may echo the credential it
    was sent, and an exception quotes what the server said. The text is cut
    to one line of at most `MAX_DETAIL` characters.
    """
    text = str(error)
    if key:
        text = text.replace(key, "[key removed]")
    text = re.sub(r"\s+", " ", text).strip()[:MAX_DETAIL]
    kind = type(error).__name__
    return AdapterError(
        f"{provider}: call failed ({kind}): {text}" if text else f"{provider}: call failed ({kind})"
    )
