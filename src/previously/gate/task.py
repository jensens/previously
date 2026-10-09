# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A task: what the gate asks a model to do, in code and with a version.

A task has a name and a version, a prompt in two halves, an output schema,
and an ordered list of models. The caller names the task and the event, never
the model: which model may see the content is the policy's question, and
which one fits the task best is the task's claim, made by the order of its
list.

The prompt is the `system` half and a `template` for the user half, with one
field, `{units}`, where the text of the event's units goes, one per
paragraph. The two together are what turns content into a prompt, so their
hash is what a `model_call` records (`prompt_sha256`): the prompt itself
holds the content, and the payload of a `model_call` holds none.

The output schema is a pydantic model. `model_json_schema` is the schema the
provider is asked to keep, and `model_validate_json` is the check the gate
makes of every answer itself, whether or not the provider enforces the
schema.
"""

from dataclasses import dataclass
from previously.core.canonical import canonical
from previously.core.decide import Candidate
from pydantic import BaseModel
from typing import TYPE_CHECKING

import hashlib
import json


if TYPE_CHECKING:
    from collections.abc import Sequence
    from previously.contract.rows import UnitRow


@dataclass(frozen=True)
class Task[Out: BaseModel]:
    name: str
    version: int
    system: str
    template: str  # the user half; `{units}` is where the units go
    output: type[Out]
    candidates: tuple[Candidate, ...]

    def render(self, units: Sequence[UnitRow]) -> str:
        """The user half of the prompt, out of the units that still hold
        their content, in their order."""
        return self.template.format(
            units="\n\n".join(unit.content for unit in units if unit.content)
        )

    def schema(self) -> dict[str, object]:
        return self.output.model_json_schema()

    def prompt_sha256(self) -> str:
        """The SHA-256 of the two halves before any content goes in."""
        halves = {"system": self.system, "template": self.template}
        return hashlib.sha256(canonical(halves)).hexdigest()

    def schema_sha256(self) -> str:
        """The SHA-256 of the schema as JSON with sorted keys and no white
        space: the flags `core.canonical` uses, without its restriction to
        lower-case keys, which a JSON schema does not keep
        (`additionalProperties`)."""
        text = json.dumps(self.schema(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(text.encode()).hexdigest()
