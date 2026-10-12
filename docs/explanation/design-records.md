(design-records)=

# About the frozen design records

Twelve German documents under `docs/superpowers/specs/` hold how this project was decided: the design, the architecture, the detailed specification of stage 1a, the one for stage 1b, the one for the external anchor, the one for stage 1c, the one for delivery, the one for taking mail in from an IMAP folder, the one for the gate and the policy, the concept of the MCP interface, the specification of MCP read access, and the one for assertions.
The first three froze on 2026-10-03, the next two on 2026-10-04, two more on 2026-10-05, one on 2026-10-06, one on 2026-10-09, two on 2026-10-11, and the last on 2026-10-12, and nothing pulls any of them forward again.
The reasoning that gets maintained along with the code lives in this quadrant instead, and where a specification and a page disagree, the page is what holds.

Until this documentation existed, those first three documents were the only place a reason was written down, so the code cited them: 72 paragraph references across 21 files in `src/`, `tests/` and `migrations/`, pointing at 20 paragraphs.
Twelve of the 72 still do, two were dropped from error messages the user reads, two left with the test that cited them, and the remaining 56 name a page instead.
This page says what the frozen records are still for, how the freezing works for the stages that follow, and which page took over each of those paragraphs.
If you arrived from a paragraph number in a comment, the table under *Where each cited paragraph went* is the map, and the section after it says when a comment keeps its number instead of naming a page.

## Freezing is a step in a procedure, not a state the project arrived at

German is the language the intent gets written in, and that isn't a leftover to work off.
A new stage therefore starts with a new German specification, and that specification freezes as soon as its explanation pages stand.

So the right way to read the frozen documents is as the output of a step that repeats, not as a rule against writing the next one.
A reader who takes the freeze for a prohibition would start the next stage without the document the stage needs most.

Stage 1b is the first time that step ran as a step.
Projections got their own German specification, dated 2026-10-04, and it froze the same day, because the pages its reasoning belongs on stood by then: {ref}`projections` for the derived tables and the worker that fills them, {ref}`module-boundaries` for the contracts that let `core` write them without importing storage.
{ref}`database-schema` and {ref}`cli-reference` took the facts—the three tables, and the three commands that build and read them.

The specification of the external anchor, dated 2026-10-04 as well, is no stage but a promise kept: the chain says nothing about completeness by itself, and the anchor is the one reference point outside the database that can, up to the newest anchor.
It froze once its pages stood.
{ref}`external-anchor` on the hash chain page carries its reasoning, {ref}`cli-reference` the facts of `anchor` and `verify --anchors`, and the two guides {ref}`verify-the-chain` and {ref}`restore-from-a-backup` the routines it implies for running the system.

The specification of stage 1c, blobs and erasure, is dated 2026-10-04 and froze on 2026-10-05, once the last of its pages stood.
Two explanation pages and a section of a third carry its reasoning: {ref}`erasure` for what an erasure takes, why it's an event, and what it doesn't achieve; {ref}`blobs` for the address, the sealing in `age`, "first wins" and the keys; and {ref}`hash-version-2`, on the hash chain page, for the salt and the digest each unit carries.
{ref}`cli-reference`, {ref}`configuration-reference`, {ref}`hash-format` and {ref}`database-schema` took the facts, and four guides took the routines: {ref}`erase-something`, {ref}`attach-and-fetch-a-file`, {ref}`run-a-blob-store-on-your-machine` and {ref}`keep-the-blob-key-safe`.
Its open points went into the map, `docs/superpowers/landkarte.md`, each under the unit of work it belongs to.

The specification of delivery, the package, the image and the release, is dated 2026-10-05 and froze the same day, once its pages stood.
It's no stage of the architecture but the first unit of work of the pilot, and it's the first record whose pages include a handoff: `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md`, in English, tells whoever builds the Kubernetes environment it runs in what the image needs there.
{ref}`delivery` carries its reasoning; {ref}`cli-reference` and {ref}`configuration-reference` took the facts of `migrate` and of the connection string, and two guides took the routines: {ref}`cut-a-release` and {ref}`run-the-image`.
It's also the first record that a page contradicts on the day it froze.
Its §10 point 7 has the release workflow run once by hand on the branch before the merge, and GitHub starts a workflow by hand only from a file on the default branch, so that run can't happen; the record keeps the plan as it stood, and {ref}`cut-a-release` says how it is.
Its open points went into the map as well.

The specification of the pilot's first unit, taking mail in from an IMAP folder, is dated 2026-10-06 and froze the same day, once its pages stood.
It changed the contract every later connector writes against: an event carries the identity of its artifact and the identities its channel names, and `append` compares the first under a key it knows already.
{ref}`connectors` carries its reasoning, and {ref}`erasure` took what it means for erasing a mail; {ref}`mail-mapping` took the mapping of a mail, field by field, {ref}`hash-format` the identity of an artifact, and {ref}`cli-reference`, {ref}`configuration-reference` and {ref}`database-schema` the command, its settings and the watermark.
{ref}`ingest-a-mail-folder` took the routine, and a second handoff, `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md`, tells whoever runs the Kubernetes environment what the ingest needs there.
Its open points went into the map, each under the unit of work it belongs to.

The specification of the pilot's third unit, the gate and the policy, is dated 2026-10-09 and froze the same day.
It decided that a policy is an action of the operator and not an assertion, and that a model call is an event in the chain whatever became of it.
{ref}`processing-policy` carries its reasoning, and {ref}`trust-boundaries` took the list of the places where content leaves the system, which the specification asked for; {ref}`policy-and-model-calls` took the payload of a policy event and of a model call, {ref}`cli-reference` and {ref}`configuration-reference` the commands and their settings, and {ref}`erasure` the cascade that takes the answer of a call with its input.
{ref}`set-a-policy-and-try-a-call` took the routine, and a third handoff, `docs/superpowers/handoffs/2026-10-09-kup6s-gate.md`, tells whoever runs the Kubernetes environment what the gate needs there.
The build departs from its wording in six places, which the header of the record lists, and the pages hold.
Its open points went into the map, each under the unit of work it belongs to.

Two records froze together on 2026-10-11: the concept of the MCP interface, dated 2026-10-10, which decides what the interface looks like when it's complete, and the specification of the pilot's fourth unit, dated the same day, which cuts read access out of it.
The concept is the first record that replaces part of another: the architecture's §8, on the MCP server, is superseded by it.
What the concept keeps of that paragraph is the protocol revision `2026-07-28`, a server without state, no sampling, idempotent writes, the duty to cite a source through the schemas, and a cockpit that can be exchanged; what it changes is the catalog of tools, a confirmation of every write that works without elicitation, and tasks only as a later addition.
The architecture's disclosure check in the MCP server, its §8.7, became the processing check of the gate applied to the client.
{ref}`mcp-interface` carries the reasoning of both records, and {ref}`processing-policy` and {ref}`trust-boundaries` took what they changed about the policy and the places where content leaves; {ref}`mcp-tools` took the tools, the form of a result and the access entry, {ref}`cli-reference` and {ref}`configuration-reference` the commands and their settings, and {ref}`policy-and-model-calls` the client and the processing chain.
{ref}`connect-claude-code-and-vibe` took the routine, with the dated list of tested configurations the concept asks for, and a fourth handoff, `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md`, tells whoever runs the Kubernetes environment what the server needs there.
The build departs from the wording of the two records in places that the header of the specification lists, and the pages hold.
The open points of both went into the map, each under the unit of work it belongs to.

The specification of the pilot's fifth unit, assertions, is dated 2026-10-12 and froze the same day, once its pages stood.
It gave the kind `assertion`, which the schema had allowed since stage 1a, its first way into the log: obligations and decisions in complete versions, with their sources, an author apart from the responsibility, proposals from an MCP client, approval and rejection, and an erasure that takes an assertion along with its source.
{ref}`assertions` carries its reasoning, and {ref}`erasure` took the cascade; {ref}`assertions-reference` took the payload and the references to actors, {ref}`cli-reference` the commands and the findings of `verify`, {ref}`mcp-tools` the five new tools, and {ref}`environment-requirements` the key of the handles and the requirement that a client asks before it answers a proposal.
{ref}`record-what-is-owed-and-decided` took the routine, and a handoff, `docs/superpowers/handoffs/2026-10-12-kup6s-assertions.md`, tells whoever runs the Kubernetes environment what the release needs there.
Its build left out a part the record planned, the two derived tables and their migration, with the consent the maintainer gave on 2026-10-12, before the build began; {ref}`assertions-folded` says why.
That departure and the others are listed in the header of the record, and the pages hold.
Its open points went into the map, each under the unit of work it belongs to.

## What a frozen record is still good for

Provenance, and it's the one thing no current page can supply.

A frozen record says *this was decided this way, on this date, against these alternatives*, and it keeps the rejected route beside the chosen one.
A maintained page states what holds today, and it has every reason to drop the alternative that lost: carrying it along would make the page a history rather than an explanation.
The two jobs pull in opposite directions, which is why the frozen record stays in the repository instead of being deleted once the pages exist.

That's also what makes a frozen record quotable.
A citation of the form *the specification said X until finding Y corrected it* needs a document that no longer moves.
Against a maintained page the same citation would turn false, without a word, the next time somebody edits the page.

## Where each cited paragraph went

The table is the map from a paragraph to the page that carries its reasoning now.
It has one row per paragraph rather than one per citation, and several numbers appear more than once, because more than one record carries a paragraph with that number.
The rows of the two MCP records name every paragraph the build cited, including those that its code no longer cites since they froze, so that a reader holding an older checkout finds the page too.

| Paragraph | Document | Where the reasoning lives now |
|---|---|---|
| §2 | architecture | {ref}`module-boundaries` |
| §3.1 | stage 1a | {ref}`hash-chain`; {ref}`hash-format` where the citation asks for the field list, {ref}`tombstone-seam` where it's about the erasure seam |
| §3.2 | stage 1a | {ref}`payload-range`; {ref}`canonicalization` where the citation asks why an exclusion is there at all |
| §3.3 | stage 1a | {ref}`hash-format` for the exact shape of the hashed string; {ref}`timestamps` for why the caller sets the value |
| §3.4 | stage 1a | {ref}`hash-chain` |
| §4 | stage 1a | {ref}`concurrency` |
| §4.1 | architecture | {ref}`projections` |
| §4.1 | stage 1a | {ref}`hash-chain` |
| §4.2 | stage 1a | {ref}`conflict-classes`; the whole of {ref}`concurrency` where the citation is about the indexes as the serialization, or about the backing off |
| §4.4 | architecture | {ref}`projections`; {ref}`module-boundaries` where the citation is about the two store protocols staying apart |
| §4.4 | stage 1a | {ref}`concurrency` |
| §4.6 | architecture | {ref}`tombstone-seam` |
| §5 | architecture | nowhere; frozen design record |
| §5 | stage 1a | {ref}`hash-chain`; {ref}`concurrency` for the source-key branch, {ref}`canonicalization` for idempotency between calls as against within one batch |
| §5.1 | design | {ref}`canonicalization` |
| §6 | stage 1a | {ref}`hash-chain` |
| §7 | stage 1a | {ref}`database-schema`; {ref}`concurrency` for the one identifier per event that `append` owes its caller |
| §8 | stage 1a | {ref}`module-boundaries` |
| §9 | stage 1a | {ref}`cli-reference`; {ref}`configuration-reference` for the connection string |
| §10.1 | architecture | nowhere; frozen design record |
| §10.2 | stage 1a | nowhere; frozen design record |
| §11 | stage 1a | nowhere; frozen design record |
| §12 | stage 1a | nowhere; frozen design record, and no longer cited since stage 1b deleted the test that cited it |
| §3.3 | MCP concept | {ref}`mcp-client-processor`; no longer cited |
| §5 | MCP concept | {ref}`mcp-access-payload`; cited by `tests/test_access.py` for the sketch of the payload, which only the frozen record holds |
| §6 | MCP concept | {ref}`mcp-text-block`; {ref}`mcp-tools` where the citation is about the form of a result; cited by `tests/test_render.py` for the example of a heading |
| §7 | MCP concept | {ref}`mcp-token`; no longer cited |
| §8 | MCP concept | {ref}`mcp-tool-list`; no longer cited |
| §5, §5.2, §6 | MCP read access | {ref}`mcp-tools`; no longer cited |
| §5.1 | MCP read access | {ref}`mcp-open-limits`; cited by `mcp_server/render.py` for where the limit of a page was set |
| §7 | MCP read access | {ref}`mcp-access-log`; no longer cited |
| §9 | MCP read access | nowhere; frozen design record, cited by `mcp_server/auth.py` for the line that the build departed from |
| §10 | MCP read access | {ref}`mcp-generations` for why every tool test runs in both generations; frozen design record for the numbering of the assurances in `tests/test_mcp_server.py` |
| §13 | MCP read access | {ref}`mcp-open-limits`, and the map of open points; no longer cited |

The five rows of the first three records that say *nowhere* are answers and not gaps, and they divide into two kinds.

Two of them are arguments that no page took over.
The architecture's §10.1 argues why an append-only store has no use for an object-relational mapper, and {ref}`database-schema` records the outcome—tables declared as SQLAlchemy Core, no mapper—without repeating the argument.
The architecture's §5 lists five properties the storage interface lacks on purpose—no update, no delete, no transaction control to the outside, no raw SQL passed through, no returning of database objects—and argues all five from one sentence: narrow, so that it holds.
Searched across this documentation, not one of the five is argued anywhere: {ref}`module-boundaries` settles which module may import which, which is a different question from which methods an interface has.
So both keep their number, and `storage/postgres.py` says which document to open.

The other three are registers tied to a date.
The stage 1a specification's §10.2 names the chain's properties `P1` to `P7`, §11 numbers the acceptance conditions for the stage, and §12 lists its open points.
The property names, the condition numbers and the open points mean something only against the document that assigned them, so a citation of one of those belongs in a frozen record and says so.

No row names the stage 1b specification, and that's the one thing worth saying about it.
Measured over `src/`, `tests/` and `migrations/`, the directories `tests/test_docs_references.py` walked until the migrations moved under `src/` on 2026-10-05, stage 1b added three paragraph references, and all three name the architecture: §4.4 twice, for the promise that a projection carries no truth of its own, and §4.1 once, for the two orders the chronicle's index keeps apart.
Not one line points at the specification of its own stage.
Stage 1b is the first stage whose code never had to: its pages were written in the same pull request as the code, so a reason had a page to name from the first draft, and `test_no_bare_paragraph_references_remain` in `tests/test_docs_references.py` turns that from a habit into a gate by refusing an unmarked paragraph sign.
Two citations in the test suite did point at this specification, as `§6.2` and `§6.3`, and both carried the `(frozen design record)` marking while the specification was still a draft; fix round 1 of the freezing task sent them to the pages that hold the reasoning instead.

No row names the specification of the external anchor either, for the same reason.
Measured over the same three directories on 2026-10-04, every paragraph sign in them carries the `(frozen design record)` marking, and the fifteen lines that hold one are the same fifteen as before the anchor was built: the anchor's code and tests added none.
Not one of them points at its specification.

No row names the specification of stage 1c either.
Measured over the same three directories on 2026-10-05, the paragraph signs stand on the same fifteen lines in the same seven files as at the start of the stage, each with the `(frozen design record)` marking, and `grep -rn "§" src tests migrations | grep -v "frozen design record"` printed nothing.
Later that day the migrations moved under `src/`, so the command drops its third directory: measured after the move, `grep -rn "§" src tests | grep -v "frozen design record"` still prints nothing, and the signs stand on the same fifteen lines in the same seven files.
Its code cites {ref}`erasure`, {ref}`blobs` and {ref}`hash-version-2` instead, and the gate checks that each label resolves.

No row names the specification of delivery either.
Measured on 2026-10-05, once its pages stood, `grep -rn "§" src tests | grep -v "frozen design record"` printed nothing, and the signs still stand on the same fifteen lines in the same seven files.
Its code cites {ref}`delivery` instead, in `storage/migrate.py`, where the gate checks the label, and in a comment of the `Dockerfile`, which no gate reads.

No row names the specification of the pilot's first unit either.
Measured on 2026-10-06, once its pages stood, `grep -rn "§" src tests | grep -v "frozen design record"` printed nothing, and the signs stand on the same fifteen lines in the same seven files as at the start of the unit.
Its code cites {ref}`artifact-identity` and {ref}`cli-reference` instead.

No row names the specification of the pilot's fifth unit either.
Measured on 2026-10-12, once its pages stood, `grep -rn "§" src tests | grep -v "frozen design record"` printed nothing, and the signs stand on the same twenty-one lines in the same thirteen files as at the start of the unit.
Its code cites the sections of {ref}`assertions` instead, beside the decisions and rulings of the plan that built it.

## Two kinds of citation, and the code shows which is which

A reference that explains why the code looks the way it does *today* names a page, as `` {ref}`label` ``, and the gate in `tests/test_docs_references.py` checks that the label resolves.
A reference that says what *was decided when* keeps its paragraph number and carries `(frozen design record)` on the same line, so that nobody mistakes it for a current source.
The same gate refuses a paragraph sign without that marking.

One reference does neither, and it's the only one of its kind in the tree.
`storage/postgres.py` names {ref}`module-boundaries` in order to say that the five properties above it are *not* settled there—a denial rather than an explanation, written because mistaking the one question for the other is what sent that pointer wrong in the first place.
It keeps the same form on purpose: the gate checks a denial's label exactly as it checks any other, so a renamed page can't leave the disclaimer pointing nowhere.

The distinction lands on individual lines and not on whole paragraphs, which is why a few paragraphs appear in both forms.
`§4.2` is cited five times, and the five split three to two.
Three describe the mechanism and now name {ref}`conflict-classes` or {ref}`concurrency`; two carry the sentence *the specification said "no retry" without qualification until finding G-7 corrected it*, for which only the frozen record can be the source.
`§3.4` divides the same way, three to two: the chain check itself is explained in {ref}`hash-chain`, while the claim that the specification prescribed `payload IS NULL` is a claim about the document.

The table above is read per line for the same reason, and that's the part worth carrying into the next stage.
A specification paragraph usually has two halves that this documentation has split across two quadrants: the restriction as a fact in Reference, the reason for it in Explanation.
A citation asks for one half or the other, which is why several rows name two pages together with the clause that picks between them.
Fix round 1 of this task found six pointers that had gone to the wrong page, four of them by taking the wrong half of a paragraph that has two, and for two of the six the row above already named the page they wanted.

Two citations were in neither class, and both were removed rather than converted.
They stood in error messages that a user reads on the terminal:

```text
… floating point number not allowed — state a scale as an integer (§3.2)
… kind of evidence (§5.1), so that it is not silently overwritten
```

Whoever runs `previously append` has no `docs/superpowers/specs/` and won't be getting one, so the citation buys nothing even before the freeze makes it stale, and a `{ref}` label in program output would read as literal nonsense.
Both messages already carry what the caller can act on, so the reasoning moved into the comment above the `raise` and the citation came out of the message.
`tests/test_docs_references.py` keeps them out by producing the messages from the code rather than searching for strings, because a search follows a changed message into the page it's supposed to be checking.
