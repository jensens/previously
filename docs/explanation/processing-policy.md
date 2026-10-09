(processing-policy)=

# About the processing policy

Before a model reads anything from the log, something has to decide that it may.
This page explains how that decision is built and why it has the shape it has: two checks instead of one, circles instead of a table of customers, the strictest rule winning, a promise kept apart from a report, a default that stays on the machine, and an audit that lives in the log while its result lives in the units.
{ref}`policy-and-model-calls` lists the events and the payload field by field, {ref}`cli-gate` the commands, and {ref}`trust-boundaries` the places this decision guards.

## Two checks, not one

The question "may this content leave?" hides two questions.
The first is which model, at which provider, in which region may see this content at all.
The second is whether this content may appear in a foreign system, such as an issue tracker of a customer, where everybody there reads it.

They have different subjects and different places to stand.
The first concerns a provider that processes content and, as a rule, keeps it for a while.
The second concerns a place that shows content to people.
A model call on the machine of the operator can be harmless for a customer whose issue tracker must never see the same text, and the other way round.
Merging them gave one check with a name that fit neither, and an earlier version of the project's map called it the disclosure check.
That term is gone.

This page and the gate are about the first check, the processing check.
The second, the check before writing outward, arrives with the first action that writes into a foreign system.
The MCP server reuses the processing check, because what Claude Code may see is the same question as what a model of the gate may see.
For that reason the decision lives in `core` and not in `gate`: it needs no model to answer.

## A circle is a social group, not a customer

A rule has to bind something.
The first idea was an organization per customer, and it fails on the mail of an operator who works for an agency, a customer of the agency and a club at once.
What binds a rule is any social group that people belong to: a customer, an agency, a joint venture, a club.
The sociologist Georg Simmel described a person as standing where several such circles cross, and the policy takes the observation literally.
An identity can be a member of several circles, and a piece of content that several members take part in belongs to all of them.

So the policy has circles, and a membership is an explicit statement of the operator: this address, or this domain, belongs to this circle.
Nothing is guessed from the folder a mail lay in, because the operator won't keep one mailbox per customer, and nothing is read from the content, because deciding that two addresses are one person is an assertion that needs a source.
Domains compare without regard to case, and local parts compare exactly, because that's what RFC 5321 allows to differ.

The operator is in almost every mail.
If the operator's own address counted as a member of a circle, every mail would fall under the rules of every circle the operator works with.
The policy therefore lets the operator declare their own identities, and removes them from the participants before it resolves any circle.

A membership counts only while its circle exists.
A membership is a statement about a circle, and when the operator revokes the circle, the statement has nothing left to be about: a revoked circle has no members.
The other reading would keep the circle binding through the back door.
A circle that has no rule brings the built-in `local_only`, so a revoked circle whose old memberships still counted would hold the content of its former members on the machine for good, after the operator said the group no longer exists.

That choice has a consequence that's easy to miss.
Once the circle is revoked, the content of its people goes by the rules that are left, and where none is left but the rule of their source, by that rule, which may be `any`.
Revoking a circle releases its content; it doesn't lock it away.
An operator who wants the content of a former customer to stay local revokes the rule of the circle and keeps the circle, which brings `local_only` back.
The memberships stay in the log either way, and creating the circle again makes them count again.

## The strictest rule wins

When a piece of content belongs to two circles, two rules apply, and so does the rule of its source.
They're merged, and the merge goes one way: regions by intersection, the retention limit by minimum, the excluded providers by union.
A conflict between rules never resolves in favor of the looser one.

The reason is the same as for the default below: a decision that errs toward "allowed" looks like working code, and nothing reports it.
An error toward "not allowed" shows as a call that was refused, and somebody reads that.

Adding a rule doesn't loosen a decision, with two exceptions that are on purpose.
A first rule for a circle that has none takes the built-in `local_only` away from that circle, and the first rule that applies to a piece of content at all takes it away from the content.
Those rules exist to allow something, and an operator who writes one wants the effect.
Replacing a rule isn't adding one, and it may loosen: changing `eu` to `any` on the same scope means exactly that.
A Hypothesis test holds the property for every other kind of added rule: a rule of the source where one already applied, a rule for an uninvolved circle, and a further involved circle with its rule.

## A promise isn't a report

The policy says what a provider promises, and the response says what the provider reported.
They're different facts and the gate keeps them apart.

A promise comes from a contract or a console: where the provider stores, how long it keeps a request, which regions it can process in.
The operator declares it as a `provider` statement, and it stands in the log like any other.
A report comes with the response, and it's as much as the provider chooses to say.

Anthropic reports the region of the processing in `usage.inference_geo`.
Mistral reports nothing.
A local server reports nothing, and doesn't need to, because the operator runs the hardware.

**A request for `global` is reported back as `global`.**
That was measured on 2026-10-09 against the API.
The value names the class of routing, not the place of the computation.
So a region is evidenced only where one was demanded: a call that requested `us` and got `us` back has the provider's word for it, and a call that requested `global` has a word that says nothing about where.
For this reason the gate sets the region explicitly wherever the provider offers a choice, even when it's `global`, and raises an alarm when the reported region differs from the requested one.
Where the gate sets no region, because the provider has one space only, the ids of the declarations in the audit say what was promised.

The gate sets the region that the rules demand, the widest one that fits.
From the point of view of the EU, `global` and `us` are both outside, so there is no ranking between them to apply, and `us` set without need costs more at Anthropic: 1.1 times the price.
With the regions `eu` and `us` allowed, Anthropic is eligible with `us`; with `any` it's eligible with `global`; with `eu` alone it's not eligible, because Anthropic has no space in the EU and stores in the United States.

## Without a rule, only the machine

A piece of content for which no rule applies gets the built-in rule `local_only`: only a provider declared `local` may see it.
So does the content of a circle that has no rule, even when a rule for another circle in the same content says `any`.
What leaves the machine is what somebody allowed, and a gap in the policy isn't a permission.

The operator's statement is the reasoning behind it: a local model that runs next to the database sees nothing that doesn't already lie there, so processing there is equivalent to what Previously does anyway.

That default has a cost, and the cost is the reason for the next section.
A local model on CPU is weaker.
The pilot measured it on 2026-10-09 with `qwen3:4b`: the model has to run with its thinking switched off (`reasoning_effort` set to `none`), because with the default the call didn't finish in 600 seconds, and the answer it gives is poorer, such as a topic of "Email Response."
A policy that falls back to it makes every result worse and says nothing.

### The fallback has to be visible

Because the fallback is safe and weaker, the one thing that can go wrong is that nobody notices.
So it shows in three places.
The `model_call` that ran under the built-in rule carries `policy.fallback`, with the circles of the content that had no rule; the list is empty only where the content belongs to no circle and no rule applied.
It isn't an alarm, because nothing went wrong, and it's a different mark for that reason.
`gate explain` and `gate try` say it on standard error, with the command that fixes it.
And `policy gaps` lists the circles and sources that fell back, with a count and the last time, from the `model_call` events and the source of the events they read.
A batch of a hundred calls, run by a layer that nobody watches call by call, still leaves that list.

If no local provider is declared, the same content is denied, and the reason says so.
That's the better failure: a refusal that names the cause, not a silent exit through the one provider that was configured.

## A policy is an action, not an assertion

A policy is set by the operator, and it's an action in the log, not an assertion.
An assertion needs a source: the architecture requires `evidenced_by` of every one.
A rule has no source in the log, because it holds since the operator says so.
Writing it as an assertion would have meant carving an exception out of the source requirement before the assertions were designed.
An action fits better: a redaction is an action too, and carries a reason and no evidence.

So a policy statement is an event of kind `action` with `payload.action` set to `policy`, and a model call is one with `model_call`.
`verify` knows three action names now, and an action with another name is a finding: with three that the system writes itself, a stranger is a typing mistake or a forgery.

A newer event with the same key replaces the older one, and a revocation is an event of its own.
The older event stays in the chain, so the policy of a past day is the log read up to that day.
An erasure of a policy event works as a revocation.
Nothing of this needs a table, because there are few events and the decision reads them on every call.

## The audit lives in the log, and the result in the units

Every attempt becomes a `model_call`: allowed, denied, failed, refused by the model, or answered against the schema.
A call that the policy stopped is as much a part of the record as one that ran.
A log that showed only what happened would not show that the policy worked.

The payload holds what the call rested on and what became of it, and never the content: ids of events and units, the hash of the prompt template rather than the prompt, which would hold the mail, the ids of the rules and declarations, the provider and model, the region, and the counts and cost.
The estimate of the cost is an estimate, and the provider's bill is what counts.

The result goes into the units, as canonical JSON.
That's a choice for erasure.
A result is derived from the input and holds some of its content, such as a topic or the names of the people.
If it sat in the payload, it would outlive an erasure of the input, and the rule that a payload shows no content would be broken at once.
In a unit it can be erased unit by unit, and an erasure of the input does that on its own, as {ref}`erasure` explains.

For the same reason the gate takes only observations as input.
A call that read the result of another call would have to be followed through the cascade, and the cascade follows one level only.
Keeping actions out of the gate is what lets the cascade stay one level deep.

## What the pilot leaves open

Some limits are known and left.

The order of the models in a task is the task's claim of what fits best, and nobody has compared them on real cases.
Unknown participants bind no rule: if the source has a rule, the content goes out under it, and nothing treats a mail with strangers in it differently.
Deciding whether it should is open.
A call can go unrecorded if the process dies between the answer and the write.
And a provider's retention is out of reach of any erasure here.
{ref}`trust-boundaries` lists these, and the map of open points holds each of them.
