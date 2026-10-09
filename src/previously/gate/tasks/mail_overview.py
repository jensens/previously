# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The first task: an overview of one mail, as a probe of the gate.

It runs policy, adapter, audit and the proof of the region through once, end
to end. Its result is not used as a statement about anything.

The models, in this order, are the plan's claim of what fits, not a
measurement of which fits best: Claude Haiku 5.5 with effort `low`, then
Mistral Small 4, then `qwen3:4b` on a local server. Each id is a pinned
version and no alias such as `…-latest`, so that the audit says what
actually ran.
"""

from previously.core.decide import Candidate
from previously.gate.task import Task
from pydantic import BaseModel
from pydantic import ConfigDict


class MailOverview(BaseModel):
    """`language` a BCP 47 tag, `topic` one sentence, `participants` the
    people the text names. No other field: `extra="forbid"` puts
    `additionalProperties: false` into the schema, and an answer with a
    field too many fails the check."""

    model_config = ConfigDict(extra="forbid")

    language: str
    topic: str
    participants: list[str]


SYSTEM = (
    "You read one e-mail and describe it in JSON that matches the schema you are given. "
    "language is the BCP 47 tag of the language the mail is written in, such as de or en. "
    "topic is one sentence on what the mail is about. "
    "participants lists the people the text of the mail names, by name. "
    "Use only what the mail says."
)
TEMPLATE = "The e-mail, its subject first, one part per paragraph:\n\n{units}"

MAIL_OVERVIEW: Task[MailOverview] = Task(
    name="mail_overview",
    version=1,
    system=SYSTEM,
    template=TEMPLATE,
    output=MailOverview,
    candidates=(
        Candidate("anthropic", "claude-haiku-5-5", "low"),
        Candidate("mistral", "mistral-small-2603", None),
        Candidate("local", "qwen3:4b", None),
    ),
)
