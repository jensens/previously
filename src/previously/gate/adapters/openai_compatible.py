# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The adapter for OpenAI-compatible endpoints, the one module that imports
`openai`. One class serves Mistral and a local Ollama; the constructor takes
the provider's name, its address and the settings only that provider needs.

The call is the one measured on 2026-10-09: `chat.completions.create` with a
`response_format` of type `json_schema` and `strict: true`. `extra` is mixed
into the request body: the local adapter passes `reasoning_effort: none`,
because measured against `qwen3:4b` the model thinks for over 600 seconds
without it. These endpoints say nothing about where they processed a call, so
`reported_geo` is always `None`.
"""

from openai import OpenAI
from previously.gate.adapters import adapter_error
from previously.gate.adapters import AdapterError
from previously.gate.adapters import Request
from previously.gate.adapters import Response
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


MISTRAL_BASE_URL = "https://api.mistral.ai/v1"


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        base_url: str,
        extra: Mapping[str, object] = {},
        timeout: float = 60.0,
    ) -> None:
        self.provider = provider
        self._key = api_key
        self._extra = dict(extra)
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def complete(self, request: Request) -> Response:
        try:
            completion = self._client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.schema_name,
                        "schema": dict(request.schema),
                        "strict": True,
                    },
                },
                extra_body=self._extra,
            )
        except Exception as error:
            raise adapter_error(self.provider, error, self._key) from None
        if not completion.choices:
            raise AdapterError(f"{self.provider}: the answer holds no choice")
        choice = completion.choices[0]
        usage = completion.usage
        return Response(
            output=choice.message.content or "",
            reported_geo=None,
            model=completion.model,
            request_id=completion.id,
            stop_reason=choice.finish_reason,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
