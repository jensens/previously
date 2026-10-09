# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The Anthropic adapter, the one module that imports `anthropic`.

The call is the one measured on 2026-10-09: `messages.create` with
`output_config` holding the JSON schema and the effort, and `inference_geo`
naming where the call may be processed. `usage.inference_geo` of the answer
becomes `reported_geo`, so the gate can compare what it asked for with what
the provider says it did. When no geo is requested the field is left out of the
request altogether: a model that does not support it answers 400, measured
for `claude-haiku-4-5`.
"""

from anthropic import Anthropic
from anthropic import omit
from previously.gate.adapters import adapter_error
from previously.gate.adapters import AdapterError
from previously.gate.adapters import Request
from previously.gate.adapters import Response
from typing import cast
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from anthropic.types.output_config_param import OutputConfigParam


# The schema is small and the output is a handful of fields; this is a ceiling
# the provider requires, not a budget.
MAX_TOKENS = 4096


class AnthropicAdapter:
    provider = "anthropic"

    def __init__(self, *, api_key: str, base_url: str | None = None, timeout: float = 60.0) -> None:
        self._key = api_key
        self._client = Anthropic(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def complete(self, request: Request) -> Response:
        config: dict[str, object] = {
            "format": {"type": "json_schema", "schema": dict(request.schema)}
        }
        if request.effort is not None:
            config["effort"] = request.effort
        try:
            # The raw response, for its headers: Anthropic names the request in
            # `request-id` (`req_…`); the body's `id` (`msg_…`) names the
            # message. Measured on 2026-10-09.
            raw = self._client.messages.with_raw_response.create(
                model=request.model,
                max_tokens=MAX_TOKENS,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config=cast("OutputConfigParam", config),
                inference_geo=omit if request.inference_geo is None else request.inference_geo,
            )
            message = raw.parse()
        except Exception as error:
            raise adapter_error(self.provider, error, self._key) from None
        output = "".join(block.text for block in message.content if block.type == "text")
        return Response(
            output=output,
            reported_geo=message.usage.inference_geo,
            model=message.model,
            request_id=raw.headers.get("request-id"),
            stop_reason=message.stop_reason,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )


__all__ = ["AdapterError", "AnthropicAdapter"]
