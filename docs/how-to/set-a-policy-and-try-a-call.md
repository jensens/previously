(set-a-policy-and-try-a-call)=

# How to set a policy and try a call

This guide shows you how to declare what your model providers promise, put the people of a customer into a circle, give the circle a rule, and check with `gate explain` and `gate try` which model may see a mail.
It runs the first call against a local model, with Ollama and `qwen3:4b`, so that it needs no key and sends nothing out of your machine.
For why a policy is built from circles and rules, see {ref}`processing-policy`, and for every option, {ref}`cli-reference`.

You need a database that `previously migrate` has brought up to date, with a mail in it that `previously ingest imap` took in ({ref}`ingest-a-mail-folder`), and `PREVIOUSLY_DSN` exported.

## Start the local model

Install [Ollama](https://ollama.com), pull the model, and let the server run:

```shell
ollama pull qwen3:4b
ollama serve
```

Tell Previously where the server listens:

```shell
export PREVIOUSLY_LOCAL_MODEL_URL=http://localhost:11434/v1
```

`gate try` sends `reasoning_effort` with the value `none` to a local server, because `qwen3:4b` with thinking switched on didn't answer in 600 seconds on a CPU.
Expect the answer to be weaker than the one of a hosted model: the call below took 15 seconds for a short mail on a laptop CPU, on 2026-10-09, and the model got the direction of the delay wrong.

## Find the event

`previously project` catches the chronicle up, and the first field of each line of `previously chronicle` is the `id` of the event:

```shell
previously project
previously chronicle
```

Use that `id` where the commands below say `1`.

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
previously policy provider local --inference eu=eu --retention-days 0 --local \
    --statement "Ollama on my own machine" --yes
```

Write what your contract says and not what the table above says.
If you don't know the retention, write `unknown`: a rule with a retention limit then rejects the provider.

## Create a circle and its members

Create the circle, then say who belongs to it, by address or by domain:

```shell
previously policy circle xz --statement "Customer XZ" --yes
previously policy member xz @example.net \
    --statement "Everybody at example.net works for XZ" --yes
```

Declare your own addresses and domains too, or the mails you wrote yourself pull your own domain into every circle you work with:

```shell
previously policy own @example.org --statement "My own domain" --yes
```

## Check what the policy would do

`gate explain` calls nothing and writes nothing:

```console
$ previously gate explain 1
processed locally: no rule for circle:xz — set one with previously policy rule circle:xz …
circles	xz
rules	local_only
regions	any
max retention days	-
excluded providers	-
candidate	anthropic/claude-haiku-5-5	rejected: anthropic/claude-haiku-5-5: the provider anthropic is not local, and only local applies
candidate	mistral/mistral-small-2603	rejected: mistral/mistral-small-2603: the provider mistral is not local, and only local applies
candidate	local/qwen3:4b	chosen
decision	local/qwen3:4b, inference_geo -
```

The circle has no rule, so the built-in rule `local_only` applies, and the first line on standard error says so.
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

If the command returns 2 with a sentence about the local server, start `ollama serve` and check `PREVIOUSLY_LOCAL_MODEL_URL`.
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

Export the key of the provider the decision chose, and try again:

```shell
export ANTHROPIC_API_KEY=YOUR-KEY
previously gate try 1
```

Use `MISTRAL_API_KEY` for Mistral.
Nothing in an event or a message holds the key.
If a key is missing, `gate try` returns 2 with `Error: anthropic: the provider is not configured — set ANTHROPIC_API_KEY`, and records the call with the outcome `error`.

For a call to Anthropic, the `model_call` carries the region the provider reported under `response.inference_geo`.
Under a rule that allows `us` only, the call asks for `us`, and if the provider reports another region, `gate try` returns 3 and prints an `alarm:` line on standard error.
A call that asked for `global` gets `global` back, which says nothing about where the model ran.

## Revoke a statement

Every form of `previously policy` takes `--revoke`, which lifts the statement and leaves the older event in the chain:

```shell
previously policy circle xz --revoke --statement "XZ is no longer a customer" --yes
```

A rule needs `--regions` even when you revoke it, because the statement has to be well formed; the value isn't read.
`previously policy show --at TIME` prints the policy as it stood at a moment, so you can see what a past call rested on.
