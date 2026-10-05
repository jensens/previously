(design-records)=

# About the frozen design records

Six German documents under `docs/superpowers/specs/` hold how this project was decided: the design, the architecture, the detailed specification of stage 1a, the one for stage 1b, the one for the external anchor, and the one for stage 1c.
The first three froze on 2026-10-03, the next two on 2026-10-04, and the sixth on 2026-10-05, and nothing pulls any of them forward again.
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
It has one row per paragraph rather than one per citation, and §4.1, §4.4 and §5 appear twice each, because the architecture and the stage 1a specification both carry a paragraph with that number.

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

The last five rows are answers and not gaps, and they divide into two kinds.

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
