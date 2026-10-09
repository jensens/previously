# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The provider adapters against a real HTTP server standing in for the
providers: the real SDK clients, no mock. Every call shape here was measured
against the real providers on 2026-10-09."""

from previously.gate.adapters import Adapter
from previously.gate.adapters import AdapterError
from previously.gate.adapters import Request
from previously.gate.adapters.anthropic import AnthropicAdapter
from previously.gate.adapters.openai_compatible import MISTRAL_BASE_URL
from previously.gate.adapters.openai_compatible import OpenAICompatibleAdapter
from typing import TYPE_CHECKING

import json
import pytest
import socket


if TYPE_CHECKING:
    from conftest import ModelServer

# A value that cannot occur by accident, so that finding it in a message means
# the adapter let the key through.
KEY = "sk-CONSPICUOUS-fake-key-0123456789"
SCHEMA = {
    "type": "object",
    "properties": {"language": {"type": "string"}},
    "required": ["language"],
    "additionalProperties": False,
}
OUTPUT = '{"language": "de"}'


def make_request(*, effort: str | None = "low", geo: str | None = "global") -> Request:
    return Request(
        model="claude-haiku-5-5",
        effort=effort,
        system="Summarize.",
        user="Betreff: Angebot",
        schema=SCHEMA,
        schema_name="mail_overview",
        inference_geo=geo,
    )


def anthropic_body(geo: str | None = "global", stop_reason: str = "end_turn") -> dict[str, object]:
    usage: dict[str, object] = {"input_tokens": 400, "output_tokens": 130}
    if geo is not None:
        usage["inference_geo"] = geo
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": OUTPUT}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage,
    }


def openai_body(finish_reason: str = "stop") -> dict[str, object]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "mistral-small-2603",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": OUTPUT},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 13, "total_tokens": 53},
    }


def anthropic_adapter(server: ModelServer, timeout: float = 5.0) -> AnthropicAdapter:
    return AnthropicAdapter(api_key=KEY, base_url=server.url, timeout=timeout)


def openai_adapter(
    server: ModelServer, extra: dict[str, object] | None = None, timeout: float = 5.0
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider="mistral",
        api_key=KEY,
        base_url=f"{server.url}/v1",
        extra=extra or {},
        timeout=timeout,
    )


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_mistral_base_url_is_the_measured_one() -> None:
    assert MISTRAL_BASE_URL == "https://api.mistral.ai/v1"


def test_anthropic_request_carries_geo_schema_and_effort(model_server: ModelServer) -> None:
    model_server.enqueue("/v1/messages", 200, anthropic_body(geo="us"))
    response = anthropic_adapter(model_server).complete(make_request(geo="us"))
    ((path, sent),) = model_server.requests
    assert path == "/v1/messages"
    assert sent["inference_geo"] == "us"
    assert sent["output_config"] == {
        "format": {"type": "json_schema", "schema": SCHEMA},
        "effort": "low",
    }
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["system"] == "Summarize."
    assert response.output == OUTPUT
    assert response.reported_geo == "us"
    assert response.model == "claude-haiku-5-5"
    # The request, not the message: support asks for the id in the header.
    assert response.request_id == model_server.anthropic_request_id
    assert response.stop_reason == "end_turn"
    assert (response.input_tokens, response.output_tokens) == (400, 130)


def test_anthropic_request_has_no_geo_field_when_none_is_set(model_server: ModelServer) -> None:
    model_server.enqueue("/v1/messages", 200, anthropic_body(geo=None))
    response = anthropic_adapter(model_server).complete(make_request(geo=None))
    ((_, sent),) = model_server.requests
    assert "inference_geo" not in sent
    assert response.reported_geo is None


def test_anthropic_request_has_no_effort_when_none_is_set(model_server: ModelServer) -> None:
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    anthropic_adapter(model_server).complete(make_request(effort=None))
    ((_, sent),) = model_server.requests
    assert sent["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}


def test_anthropic_passes_a_refusal_through(model_server: ModelServer) -> None:
    body = anthropic_body(stop_reason="refusal")
    body["content"] = []
    model_server.enqueue("/v1/messages", 200, body)
    response = anthropic_adapter(model_server).complete(make_request())
    assert response.stop_reason == "refusal"
    assert response.output == ""


def test_openai_compatible_request_asks_for_a_strict_schema(model_server: ModelServer) -> None:
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    response = openai_adapter(model_server).complete(make_request())
    ((path, sent),) = model_server.requests
    assert path == "/v1/chat/completions"
    assert sent["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "mail_overview", "schema": SCHEMA, "strict": True},
    }
    assert sent["messages"] == [
        {"role": "system", "content": "Summarize."},
        {"role": "user", "content": "Betreff: Angebot"},
    ]
    assert "reasoning_effort" not in sent
    assert response.output == OUTPUT
    assert response.reported_geo is None
    assert response.model == "mistral-small-2603"
    assert response.request_id == "chatcmpl-1"
    assert response.stop_reason == "stop"
    assert (response.input_tokens, response.output_tokens) == (40, 13)


def test_openai_compatible_mixes_extra_into_the_call(model_server: ModelServer) -> None:
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    openai_adapter(model_server, extra={"reasoning_effort": "none"}).complete(make_request())
    ((_, sent),) = model_server.requests
    assert sent["reasoning_effort"] == "none"


def test_providers_are_named() -> None:
    assert AnthropicAdapter(api_key=KEY).provider == "anthropic"
    local = OpenAICompatibleAdapter(provider="local", api_key="x", base_url="http://127.0.0.1:1/v1")
    assert local.provider == "local"


def adapters_for(
    server: ModelServer, timeout: float = 5.0
) -> list[tuple[Adapter, str, dict[str, object]]]:
    return [
        (anthropic_adapter(server, timeout), "/v1/messages", anthropic_body()),
        (openai_adapter(server, timeout=timeout), "/v1/chat/completions", openai_body()),
    ]


@pytest.mark.parametrize("which", [0, 1])
@pytest.mark.parametrize("status", [401, 500])
def test_an_error_status_becomes_an_adapter_error_without_the_key(
    model_server: ModelServer, which: int, status: int
) -> None:
    adapter, path, _ = adapters_for(model_server)[which]
    # The server echoes the key back, as a careless provider might.
    model_server.enqueue(path, status, {"error": {"message": f"bad key {KEY} given"}})
    with pytest.raises(AdapterError) as caught:
        adapter.complete(make_request())
    message = str(caught.value)
    assert KEY not in message
    assert adapter.provider in message
    assert "Error" in message
    assert "\n" not in message
    assert len(model_server.requests) == 1


@pytest.mark.parametrize("which", [0, 1])
def test_a_500_is_not_retried_silently(model_server: ModelServer, which: int) -> None:
    adapter, path, ok = adapters_for(model_server)[which]
    model_server.enqueue(path, 500, {"error": {"message": "overloaded"}})
    model_server.enqueue(path, 200, ok)
    with pytest.raises(AdapterError):
        adapter.complete(make_request())
    assert len(model_server.requests) == 1


@pytest.mark.parametrize("which", [0, 1])
def test_one_request_per_complete(model_server: ModelServer, which: int) -> None:
    adapter, path, ok = adapters_for(model_server)[which]
    model_server.enqueue(path, 200, ok)
    adapter.complete(make_request())
    assert len(model_server.requests) == 1


@pytest.mark.parametrize("which", [0, 1])
def test_a_timeout_becomes_an_adapter_error_after_one_request(
    model_server: ModelServer, which: int
) -> None:
    adapter, path, ok = adapters_for(model_server, timeout=0.3)[which]
    model_server.enqueue(path, 200, ok, delay=2.0)
    with pytest.raises(AdapterError) as caught:
        adapter.complete(make_request())
    assert KEY not in str(caught.value)
    assert adapter.provider in str(caught.value)
    assert len(model_server.requests) == 1


@pytest.mark.parametrize("which", [0, 1])
def test_a_refused_connection_becomes_an_adapter_error(which: int) -> None:
    url = f"http://127.0.0.1:{unused_port()}"
    adapters: list[Adapter] = [
        AnthropicAdapter(api_key=KEY, base_url=url, timeout=2.0),
        OpenAICompatibleAdapter(provider="local", api_key=KEY, base_url=f"{url}/v1", timeout=2.0),
    ]
    with pytest.raises(AdapterError) as caught:
        adapters[which].complete(make_request())
    message = str(caught.value)
    assert KEY not in message
    assert adapters[which].provider in message


def test_the_key_is_removed_from_the_text_of_the_exception(model_server: ModelServer) -> None:
    # The same key twice and inside a JSON string: every occurrence goes.
    model_server.enqueue(
        "/v1/messages", 401, {"error": {"message": f"{KEY} and again {KEY}", "type": "x"}}
    )
    with pytest.raises(AdapterError) as caught:
        anthropic_adapter(model_server).complete(make_request())
    assert KEY not in str(caught.value)
    assert json.dumps(KEY)[1:-1] not in str(caught.value)


def test_a_response_without_choices_is_an_adapter_error(model_server: ModelServer) -> None:
    body = openai_body()
    body["choices"] = []
    model_server.enqueue("/v1/chat/completions", 200, body)
    with pytest.raises(AdapterError, match="mistral"):
        openai_adapter(model_server).complete(make_request())
