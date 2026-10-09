(policy-and-model-calls)=

# Policy events and model calls

Two kinds of action carry the processing policy and its audit.
A policy event sets one statement of the policy, and a `model_call` records one attempt of the gate to call a model.
Both are events of the kind `action`, written with no source key, and `payload.action` names which one.
`verify` accepts exactly three names there: `redaction`, `policy` and `model_call`.
{ref}`cli-reference` lists the commands that write and read them, and {ref}`processing-policy` explains why they look the way they do.

## Policy events

A policy event has no units.
Four keys are common to all five kinds.

| Key | Value |
|---|---|
| `action` | `policy` |
| `policy` | The kind of statement, one of the five below. |
| `statement` | The sentence the statement was set with. Nothing evaluates it. |
| `revoked` | `true` where the event lifts the statement, otherwise `false`. |

A newer event with the same key replaces the older one, and an event with `revoked` set lifts the statement.
The key is what the table calls the replacement key, and the older event stays in the chain.

### The five kinds

Each kind has a replacement key and keys of its own, beside the four common ones:

| Kind | Replacement key | Further keys |
|---|---|---|
| `circle` | `name` | `name` |
| `membership` | `circle` and `member` | `circle`, `member` |
| `own_identity` | `member` | `member` |
| `rule` | `scope` | `scope`, `regions`, `max_retention_days`, `excluded_providers` |
| `provider` | `provider` | `provider`, `inference`, `storage`, `retention_days`, `reports_inference_geo`, `local` |

Every set is written as a sorted list, so the same statement has the same payload whatever order it was typed in.

A membership counts only while its circle exists.
A revoked circle has no members: its membership events stay in the log, bind nothing, and count again once the circle is created again.
The content of its people then goes by the rules that are left, such as the rule of their source, and not by `local_only`.
`policy member` refuses a membership in a circle that doesn't exist.

The keys of a `rule` and a `provider`, with their values:

| Key | Value |
|---|---|
| `scope` | `circle:<name>` or `source:<source>`. `project:<name>` is refused until projects exist. |
| `regions` | A list of `eu` and `us`, or the list `any`. |
| `max_retention_days` | A whole number of days, `0` for zero retention, or `null` for no limit. |
| `excluded_providers` | A list of provider names. |
| `provider` | The name of the provider. |
| `inference` | A list of the spaces of inference the provider lets a caller choose, each as `name` and `regions`. |
| `storage` | A list of places where the provider stores, or an empty list for a provider that stores nothing. |
| `retention_days` | How long the provider keeps what it receives, in whole days, or `null` for unknown. |
| `reports_inference_geo` | Whether a response names the region. |
| `local` | Whether the provider runs on hardware the operator runs. |

A rule written like this holds for content of the circle `xz`:

```json
{
  "action": "policy",
  "excluded_providers": [],
  "max_retention_days": null,
  "policy": "rule",
  "regions": ["eu"],
  "revoked": false,
  "scope": "circle:xz",
  "statement": "Customer XZ: processing in the EU only"
}
```

### The built-in rule

`local_only` isn't an event.
It applies to content of a circle with no rule, and to content for which no rule applies at all.
Only a provider declared `local` passes it, and it can't be revoked.
`previously policy show` lists it.

## Model calls

A `model_call` records one attempt, whatever became of it.
Its payload holds no content: ids, hashes, numbers and names.
Two attempts are two events, also over the same event with the same task.

### The payload

The keys of the payload:

| Key | Value |
|---|---|
| `action` | `model_call` |
| `task` | The task that ran, as described below. |
| `inputs` | A list with one entry per event the call read. |
| `policy` | What the decision rested on and what it chose. |
| `response` | What the provider answered. Absent where no answer came: a denied call, and a call that failed. |
| `error` | The provider, the class of the error and the HTTP status. Present only where the call failed. |
| `outcome` | What became of the call, as listed below. |
| `alarms` | A list of alarms, empty where there are none. |

The entry of `task`:

| Key | Value |
|---|---|
| `name` | The name of the task, such as `mail_overview`. |
| `version` | The version of the task, a whole number. |
| `prompt_sha256` | The SHA-256 of the object `{"system": …, "template": …}`, the two halves of the prompt before any content goes in, as UTF-8 JSON with sorted keys and no white space. |
| `schema_sha256` | The SHA-256 of the output schema, as JSON with sorted keys and no white space. |

An entry of `inputs`:

| Key | Value |
|---|---|
| `event` | The `id` of the event the call read. |
| `units` | The `seq` of each unit the prompt was built from. |
| `blobs` | The addresses of blobs the call read. Empty for `mail_overview`. |

The entry of `policy`:

| Key | Value |
|---|---|
| `circles` | The circles the content belongs to. |
| `rules` | The ids of the events of the rules that applied. |
| `providers` | The ids of the declarations of the providers the decision consulted. |
| `regions` | The regions the merged rules allow. |
| `max_retention_days` | The lowest retention limit of the rules, or `null`. |
| `decision` | `allowed` or `denied`. |
| `provider` | The provider chosen, or `null`. |
| `model` | The model chosen, or `null`. |
| `inference_geo` | The inference region the call requested, or `null` where the provider has a single space or no candidate was chosen. |
| `fallback` | `null` under a real rule, otherwise the entry below. |
| `reason` | The reasons the candidates were rejected, joined by `; `, or `null`. |

The entry of `fallback`:

| Key | Value |
|---|---|
| `reason` | `no_rule`. |
| `circles` | The circles of the content that have no rule. Empty only where the content belongs to no circle and no rule applied. |

The entry of `response`:

| Key | Value |
|---|---|
| `request_id` | The id the provider gave the request, or `null`: for Anthropic its `request-id` header (`req_…`); for an OpenAI-compatible provider the completion's `id`, because Mistral and Ollama send no request id that the client reads. |
| `model` | The model the provider names in its answer. |
| `inference_geo` | The region the provider reports, or `null` where it reports none. |
| `stop_reason` | The reason the provider gives for stopping, or `null`. |
| `usage` | The tokens, as `input_tokens` and `output_tokens`, each `null` where the provider reports none. |
| `cost_usd` | The estimate as a decimal string, or `null` for a model the price file doesn't name. The chain admits no floating-point number. |
| `prices_sha256` | The SHA-256 of the price file as it lies on disk. |

The entry of `error`:

| Key | Value |
|---|---|
| `provider` | The provider that failed. |
| `kind` | The class of the exception of the client, `NoChoice` where an answer held no choice, or `not_configured` where the provider has no adapter. |
| `status` | The HTTP status, or `null`. |

The payload never holds the provider's words about an error.
A provider can echo what it was sent, the prompt included.

A call that recorded an answer looks like this:

```json
{
  "action": "model_call",
  "alarms": [],
  "inputs": [{"blobs": [], "event": 42, "units": [1, 2, 3, 4]}],
  "outcome": "ok",
  "policy": {
    "circles": ["xz"],
    "decision": "allowed",
    "fallback": null,
    "inference_geo": "global",
    "max_retention_days": null,
    "model": "claude-haiku-5-5",
    "provider": "anthropic",
    "providers": [12, 13],
    "reason": null,
    "regions": ["any"],
    "rules": [17, 19]
  },
  "response": {
    "cost_usd": "0.000289",
    "inference_geo": "global",
    "model": "claude-haiku-5-5",
    "prices_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "request_id": "req_example",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 1830, "output_tokens": 212}
  },
  "task": {
    "name": "mail_overview",
    "prompt_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "schema_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "version": 1
  }
}
```

### The outcomes

The outcome of a call is one of these:

| Outcome | Meaning | Units |
|---|---|---|
| `ok` | The answer met the schema. | One, holding the answer as canonical JSON. |
| `denied` | The policy let no candidate through, or the event can't be read. | None. |
| `refused` | The model declined the task (`stop_reason` is `refusal`). | None. |
| `schema_invalid` | The answer isn't JSON, or doesn't match the schema, or can't be stored in the log. | None. |
| `error` | The call failed: the network, a status, a missing adapter. | None. |

### The unit of an `ok` call

The unit holds the answer of `mail_overview` as canonical JSON, with these keys:

| Key | Value |
|---|---|
| `language` | The BCP 47 tag of the language of the mail. |
| `topic` | One sentence on what the mail is about. |
| `participants` | A list of the people the text names. |

No other key is accepted.

### Alarms

The alarms the gate raises:

| Alarm | Meaning |
|---|---|
| `geo_mismatch` | A region was requested, and the provider reported another or none. |

An alarm can stand beside any outcome that has a response.
`gate try` returns 3 for an `ok` call with an alarm.

### Reasons for a denial

A denial of the event itself, before any candidate is weighed, has one of these reasons:

| Reason | When |
|---|---|
| `the event is not an observation` | The event is of any other kind, such as a policy event, a redaction or a `model_call`. |
| `the event is erased` | The payload of the event is gone. |
| `no unit of the event holds content` | Every unit is a tombstone or empty. |

A denial by the policy names the reason for each candidate and, under `local_only`, one more:

| Reason | When |
|---|---|
| `no local provider is declared` | `local_only` applies and no declared provider is `local`. |

The sentences about a candidate are in {ref}`cli-gate`.
