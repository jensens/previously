(set-a-policy-and-try-a-call)=

# How to set a policy and try a call

This guide shows you how to declare what your model providers promise, put the people of a customer into a circle, give the circle a rule, and check with `gate explain` and `gate try` which model may see a mail.
It runs the first call against a local model, with Ollama and `qwen3:4b`, so that it needs no key and sends nothing out of your machine.
For why a policy is built from circles and rules, see {ref}`processing-policy`, and for every option, {ref}`cli-reference`.

You need three things before you start.

- The `previously` command, from the first release after `0.1.0a2`, the first one with the gate, or from a checkout, where `uv run previously …` runs it without activating anything.
- A database that `previously migrate` has brought up to date, with `PREVIOUSLY_DSN` exported, and a blob store with a key, with its settings exported too ({ref}`run-a-blob-store-on-your-machine`, {ref}`keep-the-blob-key-safe`).
- At least one mail in the log that `previously ingest imap` took in ({ref}`ingest-a-mail-folder`), and in it somebody from the customer you want to put into a circle.

## Start the local model

Install [Ollama](https://ollama.com), pull the model, and let the server run:

```shell
ollama pull qwen3:4b
ollama serve
```

On Linux, the install script of Ollama runs the server as a system service called `ollama`.
Then `ollama serve` stops with `address already in use`, because the service already listens, and you skip it.

Tell Previously where the server listens:

```shell
export PREVIOUSLY_LOCAL_MODEL_URL=http://localhost:11434/v1
```

`gate try` sends `reasoning_effort` with the value `none` to a local server, because `qwen3:4b` with thinking switched on didn't answer in 600 seconds on a CPU.
Expect the answer to be weaker than the one of a hosted model: the call below took 15 seconds for a short mail on a laptop CPU, on 2026-10-09, and the model invented an application for a "Budgetfunktionalität" where the mail says that the budget stays as discussed.

## Find the event

`previously project` catches the chronicle up, and the first field of each line of `previously chronicle` is the `id` of the event:

```shell
previously project
previously chronicle
```

A circle only applies to a mail in which one of its members takes part.
`previously show` prints the addresses of a mail under `channel_identities`; pick a mail with an address of the customer whose circle you create below, and use its `id` where the commands below say `1`.

```shell
previously show 1
```

## Declare what the providers promise

A provider that the policy doesn't know is never called.
Declare each one with what its account promises.
Every command that writes shows you the statement and asks `write? [y/N]`; add `--yes` to skip the question, as the examples do.

```shell
previously policy provider anthropic --inference global=any --inference us=us \
    --storage us --retention-days 30 --reports-geo \
    --statement "Anthropic: US storage, 30 days, reports the region" --yes
previously policy provider mistral --inference eu=eu --storage eu \
    --retention-days unknown \
    --statement "Mistral: EU, retention not yet looked up" --yes
previously policy provider local --inference eu=eu --storage --retention-days 0 --local \
    --statement "Ollama on my own machine" --yes
```

Write what your contract says and not what the examples above say.
`--storage` is required: give it no region for a provider that stores nothing, such as the local one, because a provider that stores nothing passes every region rule.
If you don't know the retention, write `unknown`: a rule with a retention limit then rejects the provider.

## Create a circle and its members

Create the circle, then say who belongs to it, by address or by domain:

```shell
previously policy circle xz --statement "Customer XZ" --yes
previously policy member xz @example.net \
    --statement "Everybody at example.net works for XZ" --yes
```

Declare your own addresses and domains too: your address is in almost every mail, and if you put it or your domain into a circle, every mail you took part in would belong to that circle.
Previously removes your own identities from the people of a mail before it looks up their circles:

```shell
previously policy own @example.org --statement "My own domain" --yes
```

## Check what the policy would do

`gate explain` calls nothing and writes nothing:

```console
$ previously gate explain 1
circles	xz
rules	local_only
regions	any
max retention days	-
excluded providers	-
candidate	anthropic/claude-haiku-5-5	rejected: anthropic/claude-haiku-5-5: the provider anthropic is not local, and only local applies
candidate	mistral/mistral-small-2603	rejected: mistral/mistral-small-2603: the provider mistral is not local, and only local applies
candidate	local/qwen3:4b	chosen
decision	local/qwen3:4b, inference_geo -
processed locally: no rule for circle:xz — set one with previously policy rule circle:xz …
```

The circle has no rule, so the built-in rule `local_only` applies, and the last line, on standard error, says so.
Look at `rules`: it names the rule that decided, and `local_only` there means you have set none.

## Try a call

```console
$ previously gate try 1
processed locally: no rule for circle:xz — set one with previously policy rule circle:xz …
{"language": "de", "participants": ["Eva", "Jürgen Müller"], "topic": "Relaunch der Projektplanung mit bewerbung für die neue Budgetfunktionalität und ein Zeitplan, der um zwei Wochen nach vorne verlagert wird."}
model_call: event 8
```

The last line is the `id` of the `model_call`, the event that records the call whatever became of it.
`previously show 8` prints its payload, and {ref}`policy-and-model-calls` lists every key.

If the command returns 2 with a sentence about the local server, start the server, with `ollama serve` or the `ollama` service, and check `PREVIOUSLY_LOCAL_MODEL_URL`.
The call is recorded even then, with the outcome `error`.

## List where the policy fell back

`gate try` fell back to the local model because nobody set a rule.
`policy gaps` lists every circle and source where that happened, with how often and when last:

```console
$ previously policy gaps
circle:xz	1	2026-10-09T17:15:32.152423Z
```

Run it after a batch of calls, and give each circle on the list a rule or decide that local is right for it.

## Give the circle a rule

Allow processing anywhere, and look at the decision again:

```console
$ previously policy rule circle:xz --regions any \
    --statement "XZ allows processing anywhere" --yes
{
  "action": "policy",
  "excluded_providers": [],
  "max_retention_days": null,
  "policy": "rule",
  "regions": [
    "any"
  ],
  "revoked": false,
  "scope": "circle:xz",
  "statement": "XZ allows processing anywhere"
}
policy event 9
$ previously gate explain 1
circles	xz
rules	circle:xz (event 9)
regions	any
max retention days	-
excluded providers	-
candidate	anthropic/claude-haiku-5-5	chosen
candidate	mistral/mistral-small-2603	not reached
candidate	local/qwen3:4b	not reached
decision	anthropic/claude-haiku-5-5, inference_geo global
```

Narrow it to the EU, and the decision moves to Mistral:

```console
$ previously policy rule circle:xz --regions eu \
    --statement "XZ: processing in the EU only" --yes
{
  "action": "policy",
  "excluded_providers": [],
  "max_retention_days": null,
  "policy": "rule",
  "regions": [
    "eu"
  ],
  "revoked": false,
  "scope": "circle:xz",
  "statement": "XZ: processing in the EU only"
}
policy event 10
$ previously gate explain 1
circles	xz
rules	circle:xz (event 10)
regions	eu
max retention days	-
excluded providers	-
candidate	anthropic/claude-haiku-5-5	rejected: anthropic/claude-haiku-5-5: the provider stores in ['us'], outside the allowed ['eu']
candidate	mistral/mistral-small-2603	chosen
candidate	local/qwen3:4b	not reached
decision	mistral/mistral-small-2603, inference_geo -
```

A newer rule for the same scope replaces the older one.
To limit the retention as well, add `--max-retention-days 30`; to keep one provider away from the circle, add `--exclude-provider mistral`.

## Call a hosted model

Export the key of the provider the decision chose, Mistral after the last step, and try again:

```shell
export MISTRAL_API_KEY=YOUR-KEY
previously gate try 1
```

Use `ANTHROPIC_API_KEY` where the decision chose Anthropic.
Nothing in an event or a message holds the key.
If the key is missing, `gate try` returns 2 with `Error: mistral: the provider is not configured — set MISTRAL_API_KEY`, and records the call with the outcome `error`.

For a call to Anthropic, the `model_call` carries the region the provider reported under `response.inference_geo`.
Under a rule that allows `us` only, the call asks for `us`, and if the provider reports another region, `gate try` returns 3 and prints an `alarm:` line on standard error.
A call that asked for `global` gets `global` back, which says nothing about where the model ran.

## Revoke a statement

Every form of `previously policy` takes `--revoke`, which lifts the statement and leaves the older event in the chain:

```shell
previously policy circle xz --revoke --statement "XZ is no longer a customer" --yes
```

A revoked circle has no members, so the mail of `example.net` no longer belongs to it and goes by the rules that are left.
Here none is left, and `gate explain 1` shows `local_only` again, for `source:email`.
Had you given `source:email` a rule, the mail would go by that rule, `any` included.
To keep the mail of a former customer on your machine, revoke the rule of the circle instead and keep the circle: a circle without a rule brings back `local_only`.
{ref}`processing-policy` explains why a revoked circle releases its content.

A rule needs `--regions` even when you revoke it, and a provider needs `--storage` and `--retention-days`, because the statement has to be well formed; the values aren't read.
`previously policy show --at TIME` prints the policy as it stood at a moment, so you can see what a past call rested on.
