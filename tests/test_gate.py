# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The gate: a task, the price file, one call from the event to the
`model_call`, and the commands `gate explain`, `gate try` and `policy gaps`.

Against real PostgreSQL and a real HTTP server standing in for the providers
(`model_server` in `conftest.py`); the real SDK clients talk to it. No test
here reaches a real provider. The mail is `tests/mails/plain.eml`, mapped by
`map_mail` and appended the way `ingest` appends it.
"""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from previously.cli import main
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.action import MODEL_CALL
from previously.core.append import append
from previously.core.decide import Candidate
from previously.core.gaps import gaps
from previously.core.mail import map_mail
from previously.core.policy import Circle
from previously.core.policy import Inference
from previously.core.policy import Membership
from previously.core.policy import OwnIdentity
from previously.core.policy import Provider
from previously.core.policy import Rule
from previously.core.policy import set_policy
from previously.core.redact import redact_event
from previously.core.redact import Redacted
from previously.core.verify import verify
from previously.gate.adapters.anthropic import AnthropicAdapter
from previously.gate.adapters.openai_compatible import OpenAICompatibleAdapter
from previously.gate.gate import call
from previously.gate.gate import Called
from previously.gate.gate import explain
from previously.gate.prices import estimate
from previously.gate.prices import load_prices
from previously.gate.prices import Prices
from previously.gate.tasks.mail_overview import MAIL_OVERVIEW
from previously.gate.tasks.mail_overview import MailOverview
from previously.storage.postgres import PostgresStorage
from sqlalchemy import text
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import json
import pytest
import socket
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from conftest import ModelServer
    from previously.contract.rows import EventRow
    from previously.gate.adapters import Adapter
    from sqlalchemy import Connection
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)
LATER = T0 + timedelta(hours=1)
MAILS = Path(__file__).resolve().parent / "mails"
# A value that cannot occur by accident, so that finding it anywhere means the
# key got through.
KEY = "sk-CONSPICUOUS-gate-key-0123456789"
OVERVIEW = {"language": "de", "topic": "An offer for the relaunch", "participants": ["Eva Huber"]}

ANTHROPIC = Provider(
    "anthropic",
    (Inference("global", frozenset({"any"})), Inference("us", frozenset({"us"}))),
    frozenset({"us"}),
    30,
    True,
    False,
)
MISTRAL = Provider(
    "mistral", (Inference("eu", frozenset({"eu"})),), frozenset({"eu"}), None, False, False
)
LOCAL = Provider("local", (Inference("eu", frozenset({"eu"})),), frozenset(), 0, False, True)


# --- Setting up ----------------------------------------------------------------


def append_mail(storage: PostgresStorage) -> int:
    """`plain.eml` as the one event of the log, the way `ingest` maps it."""
    mapped = map_mail((MAILS / "plain.eml").read_bytes(), internaldate=T0, found_in={})
    (event_id,) = append(storage, [mapped.event], recorded_at=T0)
    return event_id


def declare(storage: PostgresStorage, *providers: Provider) -> None:
    for provider in providers or (ANTHROPIC, MISTRAL, LOCAL):
        set_policy(storage, provider, statement="declared", recorded_at=T0)


def set_rule(storage: PostgresStorage, scope: str, *regions: str) -> int:
    return set_policy(
        storage,
        Rule(scope, frozenset(regions), None, frozenset()),
        statement="a rule",
        recorded_at=T0,
    )


def circle_xz(storage: PostgresStorage) -> None:
    """A circle with the sender's domain, and the operator's own domain."""
    set_policy(storage, Circle("xz"), statement="customer", recorded_at=T0)
    set_policy(storage, Membership("xz", "@example.net"), statement="theirs", recorded_at=T0)
    set_policy(storage, OwnIdentity("@example.org"), statement="mine", recorded_at=T0)


def adapters(server: ModelServer, *, key: str = KEY) -> dict[str, Adapter]:
    return {
        "anthropic": AnthropicAdapter(api_key=key, base_url=server.url, timeout=5.0),
        "mistral": OpenAICompatibleAdapter(
            provider="mistral", api_key=key, base_url=f"{server.url}/v1", timeout=5.0
        ),
        "local": OpenAICompatibleAdapter(
            provider="local",
            api_key="unused",
            base_url=f"{server.url}/v1",
            extra={"reasoning_effort": "none"},
            timeout=5.0,
        ),
    }


def anthropic_body(
    output: str = json.dumps(OVERVIEW),
    *,
    geo: str | None = "global",
    stop_reason: str = "end_turn",
    tokens: tuple[int, int] = (1830, 212),
) -> dict[str, object]:
    usage: dict[str, object] = {"input_tokens": tokens[0], "output_tokens": tokens[1]}
    if geo is not None:
        usage["inference_geo"] = geo
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": output}] if output else [],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": usage,
    }


def openai_body(
    output: str = json.dumps(OVERVIEW), *, model: str = "qwen3:4b"
) -> dict[str, object]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": output},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 13, "total_tokens": 53},
    }


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def model_calls(storage: PostgresStorage) -> list[EventRow]:
    with storage.begin() as conn:
        return [
            row
            for row in storage.read_by_kind(conn, "action")
            if row.payload is not None and row.payload.get("action") == MODEL_CALL
        ]


def units_of(storage: PostgresStorage, event_id: int) -> list[str | None]:
    with storage.begin() as conn:
        return [unit.content for unit in storage.units_by_event(conn, [event_id]).get(event_id, [])]


def event_count(storage: PostgresStorage) -> int:
    with storage.begin() as conn:
        return storage.count_events(conn)


def strings_in(value: object) -> list[str]:
    """Every string anywhere in `value`, keys included."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        entries = cast("dict[str, object]", value)
        return [s for key, item in entries.items() for s in (key, *strings_in(item))]
    if isinstance(value, list):
        return [s for item in cast("list[object]", value) for s in strings_in(item)]
    return []


def content_of(storage: PostgresStorage, event_id: int) -> list[str]:
    """What the event says that a `model_call` must not repeat: the text of
    every unit, every line of it long enough to be a wording, and every
    address and name of the people involved."""
    with storage.begin() as conn:
        (row,) = storage.read(conn, from_id=event_id, limit=1)
        units = storage.units_by_event(conn, [event_id])[event_id]
    texts = [unit.content for unit in units if unit.content]
    lines = [line.strip() for text in texts for line in text.splitlines()]
    assert row.payload is not None
    identities = cast("list[dict[str, object]]", row.payload["channel_identities"])
    people = [
        value
        for identity in identities
        for value in (identity["address"], identity["name"])
        if isinstance(value, str)
    ]
    return texts + [line for line in lines if len(line) >= 8] + people


def quoted(after: str) -> list[str]:
    """The lines of the first `text` block after the sentence `after` in
    `docs/reference/cli.md`, so that what the page quotes is held against
    what the command prints."""
    page = (Path(__file__).resolve().parent.parent / "docs" / "reference" / "cli.md").read_text(
        encoding="utf-8"
    )
    assert after in page, f"cli.md no longer carries the sentence {after!r}"
    block = page.split(after, 1)[1].split("```text", 1)[1].split("```", 1)[0]
    return [line for line in block.splitlines() if line.strip()]


def payload_of(row: EventRow) -> Mapping[str, object]:
    assert row.payload is not None
    return row.payload


def policy_of(row: EventRow) -> dict[str, object]:
    return cast("dict[str, object]", payload_of(row)["policy"])


# --- The task and the prices ----------------------------------------------------


def test_mail_overview_names_its_models_in_the_order_of_the_plan() -> None:
    assert MAIL_OVERVIEW.name == "mail_overview"
    assert MAIL_OVERVIEW.version == 1
    assert MAIL_OVERVIEW.candidates == (
        Candidate("anthropic", "claude-haiku-5-5", "low"),
        Candidate("mistral", "mistral-small-2603", None),
        Candidate("local", "qwen3:4b", None),
    )


def test_the_output_schema_forbids_fields_the_task_does_not_name() -> None:
    schema = MAIL_OVERVIEW.output.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["language", "topic", "participants"]
    assert MAIL_OVERVIEW.output is MailOverview


def test_the_hashes_of_a_task_are_hexadecimal_sha256_and_stable() -> None:
    for digest in (MAIL_OVERVIEW.prompt_sha256(), MAIL_OVERVIEW.schema_sha256()):
        assert len(digest) == 64
        int(digest, 16)
    assert MAIL_OVERVIEW.prompt_sha256() == MAIL_OVERVIEW.prompt_sha256()
    assert MAIL_OVERVIEW.prompt_sha256() != MAIL_OVERVIEW.schema_sha256()


def test_the_estimate_of_the_specification() -> None:
    """1830 tokens in and 212 out at 0.10 and 0.50 per million: 0.000289."""
    prices = Prices(
        as_of=T0.date(),
        sha256="0" * 64,
        table={"claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50"))},
        surcharges={"us": Decimal("1.1")},
    )
    assert estimate(prices, "claude-haiku-5-5", "global", 1830, 212) == "0.000289"
    assert estimate(prices, "claude-haiku-5-5", None, 1830, 212) == "0.000289"
    assert estimate(prices, "claude-haiku-5-5", "us", 1830, 212) == "0.0003179"
    assert estimate(prices, "qwen3:4b", None, 1830, 212) is None
    assert estimate(prices, "claude-haiku-5-5", "global", None, 212) is None
    assert estimate(prices, "claude-haiku-5-5", "global", 0, 0) == "0"


def test_the_price_file_in_the_package() -> None:
    prices = load_prices()
    path = Path(__file__).resolve().parent.parent / "src" / "previously" / "gate" / "prices.toml"
    assert prices.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert prices.as_of.isoformat() == "2026-10-09"
    assert prices.table["claude-haiku-5-5"] == (Decimal("0.10"), Decimal("0.50"))
    assert prices.table["mistral-small-2603"] == (Decimal("0.15"), Decimal("0.6"))
    assert "qwen3:4b" not in prices.table
    assert prices.surcharges == {"us": Decimal("1.1")}


def test_a_price_file_of_ones_own(tmp_path: Path) -> None:
    own = tmp_path / "prices.toml"
    own.write_text("as_of = 2026-01-01\n[models.m]\ninput = 1\noutput = 2\n", encoding="utf-8")
    prices = load_prices(own)
    assert prices.table == {"m": (Decimal(1), Decimal(2))}
    assert prices.surcharges == {}
    assert estimate(prices, "m", None, 1_000_000, 1_000_000) == "3"


# --- One call: the region, the alarm, the fallback --------------------------------


@pytest.mark.db
def test_without_a_rule_the_call_goes_local_and_carries_the_fallback(
    db: Engine, model_server: ModelServer
) -> None:
    """Spec section 2.6, the event: no rule at all, the built-in one acts,
    and the call says so under `policy.fallback` with an empty list."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    model_server.enqueue("/v1/chat/completions", 200, openai_body())

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "ok"
    assert called.output == MailOverview.model_validate(OVERVIEW)
    ((path, sent),) = model_server.requests
    assert path == "/v1/chat/completions"
    assert sent["model"] == "qwen3:4b"
    assert sent["reasoning_effort"] == "none"
    (row,) = model_calls(storage)
    assert row.id == called.event_id
    assert policy_of(row)["fallback"] == {"reason": "no_rule", "circles": []}
    assert policy_of(row)["provider"] == "local"
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["cost_usd"] is None
    assert response["inference_geo"] is None
    assert units_of(storage, row.id) == [
        '{"language":"de","participants":["Eva Huber"],"topic":"An offer for the relaunch"}'
    ]


@pytest.mark.db
def test_a_circle_without_a_rule_names_the_circle_in_the_fallback(
    db: Engine, model_server: ModelServer
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    (row,) = model_calls(storage)
    assert policy_of(row)["fallback"] == {"reason": "no_rule", "circles": ["xz"]}
    assert policy_of(row)["circles"] == ["xz"]


@pytest.mark.db
def test_with_a_rule_the_call_carries_no_fallback(db: Engine, model_server: ModelServer) -> None:
    """The control of the two above: under a real rule, nothing is marked."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    rule_id = set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.decision.fallback is None
    (row,) = model_calls(storage)
    policy = policy_of(row)
    assert policy["fallback"] is None
    assert policy["rules"] == [rule_id]
    assert policy["decision"] == "allowed"
    assert policy["provider"] == "anthropic"
    assert policy["model"] == "claude-haiku-5-5"
    assert policy["regions"] == ["any"]


@pytest.mark.db
@pytest.mark.parametrize(
    ("regions", "expected"),
    [(("any",), "global"), (("us",), "us"), (("eu", "us"), "us")],
)
def test_the_region_decide_names_is_set_in_the_request(
    db: Engine, model_server: ModelServer, regions: tuple[str, ...], expected: str
) -> None:
    """Spec section 8, point 11: the region is always set, `global` too."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", *regions)
    model_server.enqueue("/v1/messages", 200, anthropic_body(geo=expected))

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    ((_, sent),) = model_server.requests
    assert sent["inference_geo"] == expected
    assert called.alarms == ()
    (row,) = model_calls(storage)
    assert policy_of(row)["inference_geo"] == expected
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["inference_geo"] == expected
    assert payload_of(row)["alarms"] == []


@pytest.mark.db
def test_a_provider_with_one_space_gets_no_region(db: Engine, model_server: ModelServer) -> None:
    """Ruling R-6 of the 2026-10-09 gate plan: Mistral declares `eu` alone,
    so nothing is set, and the request carries no field of the kind."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "eu")
    model_server.enqueue("/v1/chat/completions", 200, openai_body(model="mistral-small-2603"))

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "ok"
    ((_, sent),) = model_server.requests
    assert sent["model"] == "mistral-small-2603"
    assert "inference_geo" not in sent
    assert "reasoning_effort" not in sent
    (row,) = model_calls(storage)
    assert policy_of(row)["inference_geo"] is None
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["cost_usd"] == "0.0000138"


@pytest.mark.db
def test_another_region_reported_is_an_alarm(db: Engine, model_server: ModelServer) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "us")
    model_server.enqueue("/v1/messages", 200, anthropic_body(geo="global"))

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "ok"
    assert called.alarms == ("geo_mismatch",)
    (row,) = model_calls(storage)
    assert payload_of(row)["alarms"] == ["geo_mismatch"]


@pytest.mark.db
def test_the_cost_of_a_call_is_estimated_from_the_price_file(
    db: Engine, model_server: ModelServer
) -> None:
    """Spec section 4.1: the example's 1830 and 212 tokens at Haiku 5.5, and
    `us` at the 1.1-fold."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    prices = load_prices()
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    call(
        storage, storage, MAIL_OVERVIEW, event_id, adapters(model_server), prices, recorded_at=LATER
    )
    (row,) = model_calls(storage)
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["cost_usd"] == "0.000289"
    assert response["prices_sha256"] == prices.sha256
    assert response["usage"] == {"input_tokens": 1830, "output_tokens": 212}
    assert response["request_id"] == "msg_01"
    assert response["stop_reason"] == "end_turn"


# --- Every call is recorded --------------------------------------------------------


@pytest.mark.db
def test_a_denied_call_is_recorded_and_reaches_no_provider(
    db: Engine, model_server: ModelServer
) -> None:
    """Spec section 8, point 9, the denial: only local applies and no local
    provider is declared."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage, ANTHROPIC, MISTRAL)
    before = event_count(storage)

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "denied"
    assert called.output is None
    assert model_server.requests == []
    assert event_count(storage) == before + 1
    (row,) = model_calls(storage)
    payload = payload_of(row)
    assert payload["outcome"] == "denied"
    assert "response" not in payload
    assert policy_of(row)["decision"] == "denied"
    assert policy_of(row)["provider"] is None
    assert "no local provider is declared" in cast("str", policy_of(row)["reason"])
    assert units_of(storage, row.id) == []


@pytest.mark.db
def test_erasing_the_event_a_call_read_erases_the_answer_of_the_call(
    db: Engine, model_server: ModelServer
) -> None:
    """The cascade on a call the gate wrote: the answer goes, the payload
    stays, and `verify` reconciles the redaction of the cascade."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    assert any(content is not None for content in units_of(storage, called.event_id))

    result = redact_event(storage, storage, event_id, reason="wrong list", recorded_at=LATER)

    assert result.cascaded == (called.event_id,)
    assert all(content is None for content in units_of(storage, called.event_id))
    (row,) = model_calls(storage)
    assert policy_of(row)["provider"] == "anthropic"
    assert verify(storage) == []


def _waiting_on_a_row_lock(db: Engine) -> bool:
    with db.connect() as conn:
        waiting = conn.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
        ).scalar_one()
    return waiting > 0


def _until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + 15
    while not condition():
        assert time.monotonic() < deadline, what
        time.sleep(0.02)


def _cascade_reason(storage: PostgresStorage, call_id: int) -> object:
    """The reason of the redaction that erased the units of `call_id`."""
    with storage.begin() as conn:
        (reason,) = [
            row.payload["reason"]
            for row in storage.read_by_kind(conn, "action")
            if row.payload is not None
            and row.payload.get("scope") == "units"
            and row.payload.get("target") == {"event": call_id, "units": [1]}
        ]
    return reason


@pytest.mark.db
@pytest.mark.parametrize("erased", [True, False], ids=["erased-meanwhile", "control"])
def test_an_erasure_while_the_provider_answers_erases_the_answer(
    db: Engine, model_server: ModelServer, erased: bool
) -> None:
    """Ruling R-14 of the 2026-10-09 gate plan. The gate reads the mail, the
    provider holds its answer back, and `redact event` of the mail commits
    in that window, before the call is written, so it finds no call to
    cascade. The gate writes the call under the row lock of the mail, reads
    the redactions again, finds the erasure, and erases its own answer in
    the same transaction, naming the redaction that erased the mail.

    Without the second read the call is written `ok` with its answer
    standing, and `verify` reports that it keeps the result of erased input.
    The control erases nothing and keeps the answer."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    release = threading.Event()
    model_server.enqueue("/v1/messages", 200, anthropic_body(), hold=release)
    outcome: list[Called] = []
    failure: list[BaseException] = []

    def run() -> None:
        try:
            outcome.append(
                call(
                    storage,
                    storage,
                    MAIL_OVERVIEW,
                    event_id,
                    adapters(model_server),
                    load_prices(),
                    recorded_at=LATER,
                )
            )
        except BaseException as error:
            failure.append(error)

    caller = threading.Thread(target=run)
    caller.start()
    _until(lambda: len(model_server.requests) == 1, "the provider never got the request")
    redaction = (
        redact_event(storage, storage, event_id, reason="wrong list", recorded_at=LATER)
        if erased
        else None
    )
    release.set()
    caller.join(timeout=30)

    assert not caller.is_alive()
    assert failure == []
    (called,) = outcome
    assert called.outcome == "ok"
    assert verify(storage) == []
    if redaction is None:
        assert called.erased_by is None
        assert called.output is not None
        assert [content is not None for content in units_of(storage, called.event_id)] == [True]
        return
    assert redaction.cascaded == ()
    assert called.erased_by == redaction.redaction_id
    assert called.output is None
    assert units_of(storage, called.event_id) == [None]
    assert _cascade_reason(storage, called.event_id) == (
        f"cascade of redaction {redaction.redaction_id}"
    )


class _PausingAtTheLock(PostgresStorage):
    """The real store, except that the first `lock_event` through it, once
    it holds the lock, waits until `go_on` is set; `holding` says it is
    there."""

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine)
        self.holding = threading.Event()
        self.go_on = threading.Event()

    def lock_event(self, conn: Connection, event_id: int) -> EventRow | None:
        row = super().lock_event(conn, event_id)
        if not self.holding.is_set():
            self.holding.set()
            assert self.go_on.wait(timeout=15)
        return row


@pytest.mark.db
def test_an_erasure_that_waits_at_the_lock_of_the_gate_finds_the_call(
    db: Engine, model_server: ModelServer
) -> None:
    """Ruling R-14 of the 2026-10-09 gate plan, the other order. The gate
    holds the row lock of the mail and has not written the call yet; `redact
    event` of the mail reads the calls (none), and waits at that lock. The
    gate writes the call and commits; the erasure gets the lock, reads the
    calls again, finds the new one, and erases its answer.

    Without the second read the erasure cascades over the calls it read
    before the lock, which do not include this one, and `verify` reports
    that the call keeps the result of erased input."""
    plain = PostgresStorage(db)
    event_id = append_mail(plain)
    declare(plain)
    set_rule(plain, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    pausing = _PausingAtTheLock(db)
    called: list[Called] = []
    erased: list[Redacted] = []
    failure: list[BaseException] = []

    def run() -> None:
        try:
            called.append(
                call(
                    pausing,
                    pausing,
                    MAIL_OVERVIEW,
                    event_id,
                    adapters(model_server),
                    load_prices(),
                    recorded_at=LATER,
                )
            )
        except BaseException as error:
            failure.append(error)

    def erase() -> None:
        try:
            erased.append(
                redact_event(plain, plain, event_id, reason="wrong list", recorded_at=LATER)
            )
        except BaseException as error:
            failure.append(error)

    caller = threading.Thread(target=run)
    caller.start()
    assert pausing.holding.wait(timeout=15)
    eraser = threading.Thread(target=erase)
    eraser.start()
    _until(lambda: _waiting_on_a_row_lock(db), "the erasure never waited at the row lock")
    pausing.go_on.set()
    for thread in (caller, eraser):
        thread.join(timeout=30)
        assert not thread.is_alive()

    assert failure == []
    (result,) = called
    (redaction,) = erased
    assert result.erased_by is None
    assert redaction.cascaded == (result.event_id,)
    assert units_of(plain, result.event_id) == [None]
    assert verify(plain) == []


@pytest.mark.db
def test_an_action_is_denied_as_input_without_a_prompt(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ruling R-11 of the 2026-10-09 gate plan: a policy event and a
    `model_call` are no input. The observation beside them still passes."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    policy_id = set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    answered = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    assert answered.outcome == "ok"
    requests = len(model_server.requests)

    for action_id in (policy_id, answered.event_id):
        denied = call(
            storage,
            storage,
            MAIL_OVERVIEW,
            action_id,
            adapters(model_server),
            load_prices(),
            recorded_at=LATER,
        )
        assert denied.outcome == "denied"
        assert denied.message == "the event is not an observation"
    assert len(model_server.requests) == requests

    _env(monkeypatch, db, model_server)
    capsys.readouterr()
    assert main(["gate", "try", str(policy_id)]) == 2
    assert capsys.readouterr().err == "denied: the event is not an observation\n"
    assert verify(storage) == []


@pytest.mark.db
def test_an_erased_event_is_denied_without_a_prompt(db: Engine, model_server: ModelServer) -> None:
    """Review focus 1: no call and no prompt out of tombstones, one
    `model_call` with `denied` and the reason."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    redact_event(storage, storage, event_id, reason="wrong list", recorded_at=T0)

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "denied"
    assert called.message == "the event is erased"
    assert model_server.requests == []
    (row,) = model_calls(storage)
    assert policy_of(row)["reason"] == "the event is erased"
    assert payload_of(row)["inputs"] == [{"event": event_id, "units": [], "blobs": []}]


@pytest.mark.db
def test_a_refusal_by_the_model_is_recorded(db: Engine, model_server: ModelServer) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body("", stop_reason="refusal"))

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "refused"
    assert called.output is None
    (row,) = model_calls(storage)
    assert payload_of(row)["outcome"] == "refused"
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["stop_reason"] == "refusal"
    assert units_of(storage, row.id) == []


@pytest.mark.db
@pytest.mark.parametrize(
    "output",
    [
        json.dumps({**OVERVIEW, "mood": "cheerful"}),
        json.dumps({"language": "de", "topic": "x"}),
        "The mail is about a relaunch.",
    ],
    ids=["a-field-too-many", "a-field-missing", "text-instead-of-json"],
)
def test_an_answer_against_the_schema_is_recorded_as_schema_invalid(
    db: Engine, model_server: ModelServer, output: str
) -> None:
    """Review focus 3: valid JSON the schema refuses, or text, is
    `schema_invalid` with no units. The gate checks the answer itself even
    where the provider enforces the schema."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body(output))

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "schema_invalid"
    assert called.output is None
    (row,) = model_calls(storage)
    assert payload_of(row)["outcome"] == "schema_invalid"
    assert units_of(storage, row.id) == []


@pytest.mark.db
def test_a_valid_answer_is_the_control_of_the_schema_check(
    db: Engine, model_server: ModelServer
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    assert called.outcome == "ok"
    (row,) = model_calls(storage)
    assert len(units_of(storage, row.id)) == 1


@pytest.mark.db
def test_an_answer_that_cannot_be_stored_is_schema_invalid(
    db: Engine, model_server: ModelServer
) -> None:
    """A string the schema takes and the log does not (a NUL character): the
    call happened, so it is recorded, and nothing of the answer is kept."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue(
        "/v1/messages", 200, anthropic_body(json.dumps({**OVERVIEW, "topic": "a\x00b"}))
    )
    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    assert called.outcome == "schema_invalid"
    (row,) = model_calls(storage)
    assert units_of(storage, row.id) == []


@pytest.mark.db
def test_a_failed_call_is_recorded_without_the_providers_words(
    db: Engine, model_server: ModelServer
) -> None:
    """Ruling R-9 of the 2026-10-09 gate plan: the payload names the
    provider, the class of the error and the HTTP status, never what the
    provider said, which may echo the prompt."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    echo = {"type": "error", "error": {"type": "invalid_request_error", "message": "Liebe Eva"}}
    model_server.enqueue("/v1/messages", 400, echo)

    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    assert called.outcome == "error"
    assert called.message is not None
    assert "anthropic" in called.message
    (row,) = model_calls(storage)
    payload = payload_of(row)
    assert payload["error"] == {"provider": "anthropic", "kind": "BadRequestError", "status": 400}
    assert "response" not in payload
    assert not any("Liebe Eva" in s for s in strings_in(payload))
    assert units_of(storage, row.id) == []


@pytest.mark.db
def test_a_chosen_provider_without_an_adapter_is_an_error(
    db: Engine, model_server: ModelServer
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "eu")
    present = {k: v for k, v in adapters(model_server).items() if k != "mistral"}

    called = call(
        storage, storage, MAIL_OVERVIEW, event_id, present, load_prices(), recorded_at=LATER
    )

    assert called.outcome == "error"
    assert called.message == "mistral: the provider is not configured"
    assert model_server.requests == []
    (row,) = model_calls(storage)
    assert payload_of(row)["error"] == {
        "provider": "mistral",
        "kind": "not_configured",
        "status": None,
    }


@pytest.mark.db
def test_a_local_server_that_does_not_run_is_an_error(
    db: Engine, model_server: ModelServer
) -> None:
    """Review focus 4 at the level of the gate; the command line below."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    absent = OpenAICompatibleAdapter(
        provider="local",
        api_key="unused",
        base_url=f"http://127.0.0.1:{unused_port()}/v1",
        extra={"reasoning_effort": "none"},
        timeout=5.0,
    )
    called = call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        {"local": absent},
        load_prices(),
        recorded_at=LATER,
    )
    assert called.outcome == "error"
    (row,) = model_calls(storage)
    assert cast("dict[str, object]", payload_of(row)["error"])["provider"] == "local"


@pytest.mark.db
def test_an_event_that_does_not_exist_is_an_error_and_nothing_is_written(
    db: Engine, model_server: ModelServer
) -> None:
    from previously.core.errors import PreviouslyError

    storage = PostgresStorage(db)
    with pytest.raises(PreviouslyError, match="there is no event 7"):
        call(
            storage,
            storage,
            MAIL_OVERVIEW,
            7,
            adapters(model_server),
            load_prices(),
            recorded_at=LATER,
        )
    assert event_count(storage) == 0


# --- No content in the payload -------------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize("rule", [None, "any", "us"])
def test_the_payload_of_a_model_call_holds_no_content(
    db: Engine, model_server: ModelServer, rule: str | None
) -> None:
    """Spec section 8, point 10: not a unit's text, not a line of it, not an
    address or a name of the people involved — searched in every string of
    the payload, keys included."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    if rule is not None:
        set_rule(storage, "circle:xz", rule)
        set_rule(storage, "source:email", rule)
        model_server.enqueue(
            "/v1/messages", 200, anthropic_body(geo="global" if rule == "any" else rule)
        )
    else:
        model_server.enqueue("/v1/chat/completions", 200, openai_body())

    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    (row,) = model_calls(storage)
    wordings = content_of(storage, event_id)
    assert len(wordings) > 10
    found = [(w, s) for s in strings_in(payload_of(row)) for w in wordings if w in s]
    assert found == []
    # The control: the same search finds the wording where it is.
    ((_, sent),) = model_server.requests
    assert any(w in s for s in strings_in(sent) for w in wordings)


@pytest.mark.db
def test_the_payload_has_the_form_of_the_specification(
    db: Engine, model_server: ModelServer
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    set_rule(storage, "circle:xz", "any")
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    (row,) = model_calls(storage)
    payload = payload_of(row)
    assert set(payload) == {
        "action",
        "task",
        "inputs",
        "policy",
        "response",
        "outcome",
        "alarms",
    }
    assert payload["task"] == {
        "name": "mail_overview",
        "version": 1,
        "prompt_sha256": MAIL_OVERVIEW.prompt_sha256(),
        "schema_sha256": MAIL_OVERVIEW.schema_sha256(),
    }
    with storage.begin() as conn:
        seqs = [u.seq for u in storage.units_by_event(conn, [event_id])[event_id]]
    assert payload["inputs"] == [{"event": event_id, "units": seqs, "blobs": []}]
    policy = policy_of(row)
    assert set(policy) == {
        "circles",
        "rules",
        "providers",
        "regions",
        "max_retention_days",
        "decision",
        "provider",
        "model",
        "inference_geo",
        "fallback",
        "reason",
    }
    assert len(cast("list[int]", policy["rules"])) == 2
    assert len(cast("list[int]", policy["providers"])) == 1


# --- explain, verify, gaps --------------------------------------------------------------


@pytest.mark.db
def test_explain_decides_and_writes_nothing(db: Engine) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "eu")
    before = event_count(storage)
    decision = explain(storage, MAIL_OVERVIEW, event_id)
    assert decision.chosen == Candidate("mistral", "mistral-small-2603", None)
    assert event_count(storage) == before


@pytest.mark.db
def test_explain_reads_the_policy_of_a_moment(db: Engine) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_policy(
        storage,
        Rule("source:email", frozenset({"any"}), None, frozenset()),
        statement="later",
        recorded_at=LATER,
    )
    assert explain(storage, MAIL_OVERVIEW, event_id, at=T0).fallback is not None
    assert explain(storage, MAIL_OVERVIEW, event_id).fallback is None


@pytest.mark.db
def test_verify_finds_a_model_call_with_outcome_ok_and_no_units(db: Engine) -> None:
    storage = PostgresStorage(db)
    payload: dict[str, object] = {
        "action": "model_call",
        "inputs": [{"event": 1, "units": [], "blobs": []}],
        "outcome": "ok",
        "alarms": [],
    }
    bad = append_action(storage, payload, (), recorded_at=T0)
    good = append_action(storage, payload, (RawUnit(1, "{}"),), recorded_at=T0)
    denied = append_action(storage, {**payload, "outcome": "denied"}, (), recorded_at=T0)
    findings = verify(storage)
    assert [(f.event_id, f.reason) for f in findings] == [
        (bad, f"model_call has no valid form: {OK_WITHOUT_UNITS}")
    ]
    assert good not in [f.event_id for f in findings]
    assert denied not in [f.event_id for f in findings]


# Every way a `model_call` with one unit can break its form, and the reason
# `verify` gives; `cli.md` quotes these and the one without units below.
FORM_FINDINGS: list[tuple[dict[str, object], str]] = [
    ({"outcome": None}, "it has no outcome"),
    ({"outcome": "teleported"}, 'it has the unknown outcome "teleported"'),
    ({"outcome": "denied"}, "it is denied and has units"),
    ({"inputs": "42"}, 'it has no list "inputs"'),
    ({"inputs": [{"blobs": "none"}]}, 'it has an "inputs" entry without an event'),
]
OK_WITHOUT_UNITS = "it is ok and has no units"


@pytest.mark.db
@pytest.mark.parametrize(("change", "reason"), FORM_FINDINGS)
def test_verify_holds_a_model_call_to_its_form(
    db: Engine, change: dict[str, object], reason: str
) -> None:
    storage = PostgresStorage(db)
    payload: dict[str, object] = {
        "action": "model_call",
        "inputs": [{"event": 1, "units": [], "blobs": []}],
        "outcome": "ok",
        "alarms": [],
        **change,
    }
    event_id = append_action(storage, payload, (RawUnit(1, "{}"),), recorded_at=T0)
    assert [(f.event_id, f.reason) for f in verify(storage)] == [
        (event_id, f"model_call has no valid form: {reason}")
    ]


@pytest.mark.db
def test_a_written_model_call_passes_verify(db: Engine, model_server: ModelServer) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    call(storage, storage, MAIL_OVERVIEW, event_id, {}, load_prices(), recorded_at=LATER)
    assert verify(storage) == []


@pytest.mark.db
def test_gaps_name_the_circles_and_sources_that_fell_back(
    db: Engine, model_server: ModelServer
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    for _ in range(2):
        model_server.enqueue("/v1/chat/completions", 200, openai_body())
        call(
            storage,
            storage,
            MAIL_OVERVIEW,
            event_id,
            adapters(model_server),
            load_prices(),
            recorded_at=T0,
        )
    circle_xz(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )

    with storage.begin() as conn:
        found = gaps(storage, conn, since=None)
        recent = gaps(storage, conn, since=LATER)
    assert [(g.what, g.count, g.last) for g in found] == [
        ("circle:xz", 1, LATER),
        ("source:email", 2, T0),
    ]
    assert [(g.what, g.count) for g in recent] == [("circle:xz", 1)]


@pytest.mark.db
def test_gaps_leave_out_a_call_under_a_real_rule(db: Engine, model_server: ModelServer) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    model_server.enqueue("/v1/messages", 200, anthropic_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=LATER,
    )
    with storage.begin() as conn:
        assert gaps(storage, conn, since=None) == []


# --- The command line ------------------------------------------------------------------


def _env(
    monkeypatch: pytest.MonkeyPatch,
    db: Engine,
    server: ModelServer,
    *,
    local: str | None = None,
) -> None:
    """The settings of `gate try`: the database, both keys, the local model,
    and the address of the Anthropic API, which its SDK reads from
    `ANTHROPIC_BASE_URL` when the adapter names none. Mistral's address is a
    constant, so the command line reaches Mistral only for real, and the
    tests here take Anthropic and the local model."""
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", server.url)
    monkeypatch.setenv("MISTRAL_API_KEY", KEY)
    monkeypatch.setenv("PREVIOUSLY_LOCAL_MODEL_URL", local or f"{server.url}/v1")
    monkeypatch.delenv("PREVIOUSLY_PRICES", raising=False)


@pytest.mark.db
def test_gate_try_prints_the_output_and_the_event(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/messages", 200, anthropic_body())

    assert main(["gate", "try", str(event_id)]) == 0

    out, err = capsys.readouterr()
    (row,) = model_calls(storage)
    first, second = out.splitlines()
    assert json.loads(first) == OVERVIEW
    assert first == quoted("On standard output it prints")[0]
    assert second == f"model_call: event {row.id}"
    assert err == ""


@pytest.mark.db
def test_gate_try_says_the_fallback_on_standard_error(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/chat/completions", 200, openai_body())

    assert main(["gate", "try", str(event_id)]) == 0

    err = capsys.readouterr().err
    assert err == (
        "processed locally: no rule for circle:xz — set one with previously policy rule "
        "circle:xz …\n"
    )


@pytest.mark.db
def test_gate_try_without_any_rule_names_the_source(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    assert main(["gate", "try", str(event_id)]) == 0
    assert capsys.readouterr().err == (
        "processed locally: no rule for source:email — set one with previously policy rule "
        "source:email …\n"
    )


@pytest.mark.db
def test_gate_try_says_no_fallback_when_the_call_is_denied(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`local_only` acts and no local provider is declared: the call is
    denied, and the one line on standard error is the denial, not a
    `processed locally` that nothing was."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage, ANTHROPIC, MISTRAL)
    _env(monkeypatch, db, model_server)

    assert main(["gate", "try", str(event_id)]) == 2

    err = capsys.readouterr().err
    assert err.startswith("denied: ")
    assert "no local provider is declared" in err
    assert "processed locally" not in err
    assert model_server.requests == []


@pytest.mark.db
def test_gate_try_whose_input_is_erased_during_the_call_prints_no_answer(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ruling R-14 of the 2026-10-09 gate plan on the command line: the mail
    is erased while the provider answers. The answer is erased with it, so
    it is not printed either; one sentence names the redaction, and 2."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    release = threading.Event()
    model_server.enqueue("/v1/messages", 200, anthropic_body(), hold=release)
    erased: list[Redacted] = []

    def erase() -> None:
        # `main` installs a signal handler, which only the main thread may,
        # so the erasure is the one that runs beside it.
        try:
            _until(lambda: len(model_server.requests) == 1, "the provider never got the request")
            erased.append(
                redact_event(storage, storage, event_id, reason="wrong list", recorded_at=LATER)
            )
        finally:
            release.set()

    eraser = threading.Thread(target=erase)
    eraser.start()
    returned = main(["gate", "try", str(event_id)])
    eraser.join(timeout=30)

    assert returned == 2
    (redaction,) = erased
    out, err = capsys.readouterr()
    (row,) = model_calls(storage)
    assert out == f"model_call: event {row.id}\n"
    assert err == (
        f"erased: the input was erased by redaction {redaction.redaction_id} while the call "
        "ran; the answer is erased with it\n"
    )
    assert verify(storage) == []


@pytest.mark.db
def test_gate_try_returns_3_on_an_alarm(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "us")
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/messages", 200, anthropic_body(geo="global"))

    assert main(["gate", "try", str(event_id)]) == 3

    out, err = capsys.readouterr()
    assert out.splitlines()[-1].startswith("model_call: event ")
    assert err == "alarm: inference_geo requested us, reported global\n"


@pytest.mark.db
def test_gate_try_denied_is_one_sentence_and_2(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review focus 1 on the command line: an erased event."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    redact_event(storage, storage, event_id, reason="wrong list", recorded_at=T0)
    _env(monkeypatch, db, model_server)

    assert main(["gate", "try", str(event_id)]) == 2

    out, err = capsys.readouterr()
    (row,) = model_calls(storage)
    assert out == f"model_call: event {row.id}\n"
    assert err == "denied: the event is erased\n"
    assert err.strip() in quoted("A denial and a refusal by the model read")
    assert model_server.requests == []


@pytest.mark.db
def test_gate_try_with_an_answer_against_the_schema_returns_2(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review focus 3 on the command line."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/messages", 200, anthropic_body("not json"))

    assert main(["gate", "try", str(event_id)]) == 2

    out, err = capsys.readouterr()
    assert out.startswith("model_call: event ")
    assert err == (
        "schema_invalid: the answer of anthropic/claude-haiku-5-5 does not match the "
        "schema of mail_overview\n"
    )


@pytest.mark.db
def test_gate_try_against_a_local_server_that_does_not_run(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review focus 4: only local applies and nothing listens. One sentence
    that names the local server, 2, no traceback, and no `processed locally`:
    nothing was."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    set_rule(storage, "source:email", "any")
    url = f"http://127.0.0.1:{unused_port()}/v1"
    _env(monkeypatch, db, model_server, local=url)

    assert main(["gate", "try", str(event_id)]) == 2

    out, err = capsys.readouterr()
    assert out.startswith("model_call: event ")
    (line,) = err.splitlines()
    assert line.startswith("Error: local: call failed (APIConnectionError)")
    assert line.endswith(f"— the local model server is {url}")
    assert "Traceback" not in err
    (row,) = model_calls(storage)
    assert payload_of(row)["outcome"] == "error"


@pytest.mark.db
def test_gate_try_names_the_variable_of_a_provider_not_configured(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    monkeypatch.delenv("ANTHROPIC_API_KEY")

    assert main(["gate", "try", str(event_id)]) == 2

    assert capsys.readouterr().err == (
        "Error: anthropic: the provider is not configured — set ANTHROPIC_API_KEY\n"
    )
    assert len(model_calls(storage)) == 1


@pytest.mark.db
def test_no_key_appears_anywhere_when_the_provider_refuses_it(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Spec section 8, point 14: a 401 whose body echoes the key, as a
    server may. Not on standard output, not on standard error, not in any
    event."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    body = {"type": "error", "error": {"type": "authentication_error", "message": f"bad {KEY}"}}
    model_server.enqueue("/v1/messages", 401, body)

    assert main(["gate", "try", str(event_id)]) == 2

    out, err = capsys.readouterr()
    assert KEY not in out
    assert KEY not in err
    assert "Error: anthropic: call failed (AuthenticationError)" in err
    with storage.begin() as conn:
        rows = list(storage.read(conn, from_id=1, limit=100))
        units = storage.units_by_event(conn, [r.id for r in rows])
    assert not any(KEY in json.dumps(r.payload) for r in rows)
    assert not any(KEY in (u.content or "") for us in units.values() for u in us)
    # The control: the key did reach the server, so it was there to leak.
    ((_, sent),) = model_server.requests
    assert sent["model"] == "claude-haiku-5-5"


@pytest.mark.db
def test_gate_try_reads_the_prices_named_by_the_variable(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    own = tmp_path / "prices.toml"
    own.write_text(
        "as_of = 2026-10-09\n[models.claude-haiku-5-5]\ninput = 1\noutput = 1\n", encoding="utf-8"
    )
    monkeypatch.setenv("PREVIOUSLY_PRICES", str(own))
    model_server.enqueue("/v1/messages", 200, anthropic_body(tokens=(500_000, 500_000)))

    assert main(["gate", "try", str(event_id)]) == 0

    (row,) = model_calls(storage)
    response = cast("dict[str, object]", payload_of(row)["response"])
    assert response["cost_usd"] == "1"
    assert response["prices_sha256"] == hashlib.sha256(own.read_bytes()).hexdigest()


@pytest.mark.db
def test_gate_explain_prints_the_decision_and_writes_nothing(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    circle_xz(storage)
    rule_id = set_rule(storage, "circle:xz", "eu")
    source_id = set_rule(storage, "source:email", "any")
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    before = event_count(storage)

    assert main(["gate", "explain", str(event_id)]) == 0

    out, err = capsys.readouterr()
    assert (rule_id, source_id) == (8, 9)
    assert out.splitlines() == quoted("the mail goes to Mistral")
    assert out.splitlines() == [
        "circles\txz",
        f"rules\tcircle:xz (event {rule_id}),source:email (event {source_id})",
        "regions\teu",
        "max retention days\t-",
        "excluded providers\t-",
        "candidate\tanthropic/claude-haiku-5-5\trejected: anthropic/claude-haiku-5-5: the "
        "provider stores in ['us'], outside the allowed ['eu']",
        "candidate\tmistral/mistral-small-2603\tchosen",
        "candidate\tlocal/qwen3:4b\tnot reached",
        "decision\tmistral/mistral-small-2603, inference_geo -",
    ]
    assert err == ""
    assert event_count(storage) == before


@pytest.mark.db
def test_gate_explain_says_no_fallback_for_a_denial(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`local_only` acts and no local provider is declared: the table says
    both, and standard error stays empty, since nothing would be processed
    locally."""
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage, ANTHROPIC, MISTRAL)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))

    assert main(["gate", "explain", str(event_id)]) == 0

    out, err = capsys.readouterr()
    lines = out.splitlines()
    assert lines[1] == "rules\tlocal_only"
    assert lines[5] == "candidate\t-\tno local provider is declared"
    assert lines[-1] == "decision\tdenied"
    assert err == ""


@pytest.mark.db
def test_gate_on_an_event_that_does_not_exist(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["gate", "explain", "9"]) == 2
    assert capsys.readouterr().err == "Error: there is no event 9\n"


@pytest.mark.db
def test_policy_gaps_lists_what_fell_back(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    model_server.enqueue("/v1/chat/completions", 200, openai_body())
    call(
        storage,
        storage,
        MAIL_OVERVIEW,
        event_id,
        adapters(model_server),
        load_prices(),
        recorded_at=T0,
    )
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))

    assert main(["policy", "gaps"]) == 0
    assert capsys.readouterr() == ("source:email\t1\t2026-10-09T12:00:00.000000Z\n", "")

    assert main(["policy", "gaps", "--since", "2026-10-09T13:00:00Z"]) == 0
    assert capsys.readouterr() == ("", "no call fell back to local only\n")


@pytest.mark.db
def test_gate_try_refused_by_the_model_returns_2(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    set_rule(storage, "source:email", "any")
    _env(monkeypatch, db, model_server)
    model_server.enqueue("/v1/messages", 200, anthropic_body("", stop_reason="refusal"))

    assert main(["gate", "try", str(event_id)]) == 2

    out, err = capsys.readouterr()
    assert out.startswith("model_call: event ")
    assert err == "refused: anthropic/claude-haiku-5-5 declined the task\n"
    assert err.strip() in quoted("A denial and a refusal by the model read")


def test_the_reference_quotes_every_finding_about_a_model_call() -> None:
    """The page's findings against the reasons the tests above measure
    `verify` to give, in both directions."""
    lines = quoted("Each break of that form is a finding")
    reasons = [line.partition(": model_call has no valid form: ")[2] for line in lines]
    assert all(line.startswith("FINDING 12: model_call has no valid form: ") for line in lines)
    assert sorted(reasons) == sorted([reason for _, reason in FORM_FINDINGS] + [OK_WITHOUT_UNITS])


@pytest.mark.db
def test_gate_try_with_a_price_file_that_is_not_toml_calls_nothing(
    db: Engine,
    model_server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    storage = PostgresStorage(db)
    event_id = append_mail(storage)
    declare(storage)
    _env(monkeypatch, db, model_server)
    own = tmp_path / "prices.toml"
    own.write_text("as_of = \n", encoding="utf-8")
    monkeypatch.setenv("PREVIOUSLY_PRICES", str(own))
    before = event_count(storage)

    assert main(["gate", "try", str(event_id)]) == 2

    err = capsys.readouterr().err
    assert err.startswith(f"Error: the price file {own} is not TOML: ")
    assert err.count("\n") == 1
    assert event_count(storage) == before
    assert model_server.requests == []


def test_a_price_file_without_a_date_or_with_a_word_for_a_price(tmp_path: Path) -> None:
    from previously.gate.prices import PricesUnreadable

    own = tmp_path / "prices.toml"
    own.write_text("[models.m]\ninput = 1\noutput = 1\n", encoding="utf-8")
    with pytest.raises(PricesUnreadable, match="has no date as_of"):
        load_prices(own)
    own.write_text('as_of = 2026-10-09\n[models.m]\ninput = "1"\noutput = 1\n', encoding="utf-8")
    with pytest.raises(PricesUnreadable, match=r"models\.m\.input is not a number"):
        load_prices(own)
    with pytest.raises(PricesUnreadable, match="cannot be read"):
        load_prices(tmp_path / "missing.toml")
