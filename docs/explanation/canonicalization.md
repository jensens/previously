(canonicalization)=

# About canonicalization

A hash is a function of bytes, and a payload is a structure.
Something has to turn the structure into bytes, and it has to turn the same structure into the same bytes every time, on every machine, in every language that might ever check the chain.
That something is the canonicalization, and in Previously it follows RFC 8785, the canonicalization scheme for JSON: sorted keys, no whitespace, UTF-8, a fixed rendering of numbers.
{ref}`hash-format` says what the resulting bytes look like for each digest.
This page says why the scheme is a scheme at all, and why the payloads it has to canonicalize are kept so plain.

## Concatenation is ambiguous, a canonical object isn't

The first design concatenated the hashed fields and ran SHA-256 over the result.
That's ambiguous, and the counterexample fits on one line: `"ab" + "c"` and `"a" + "bc"` produce the same byte stream from different field values.
Two different events could therefore carry one hash, and a forger who can choose field boundaries can aim for a collision without touching SHA-256 at all.
A canonicalized object has no such freedom, because the structure survives into the bytes: the keys stay, the delimiters stay, and a value that moves from one field to another changes the bytes.

The choice has a side effect worth noticing, and it argues for the same decision from a different direction.
The canonicalizer gets used three times in version 1 of the hash format, not once: for `payload_hash`, for the wrapped object behind `units_hash`, and for the wrapped object behind the event hash.
Version 2 adds a fourth use, the digest of a single unit.
One piece of machinery, several uses, and the same guarantee in all of them.
A concatenation scheme would have needed a hand-written field order for each instead, each one its own chance to disagree with the check that reads it back.

The restricted range below is what makes this affordable.
With no floating point numbers and keys in lower-case ASCII, `json.dumps` with fixed flags already meets RFC 8785, so no foreign library carries any of this: `sort_keys` sorts by code point, which for ASCII keys is the same order as the scheme's sorting by UTF-16 code units, `separators` removes every bit of whitespace, and `ensure_ascii=False` yields the minimally escaped UTF-8 the scheme asks for.

## The payload range is narrow on purpose

A payload may contain objects, arrays, strings, integers, `true`, `false` and `null`, and the top level is always an object.
Everything else gets refused before anything is hashed.
{ref}`payload-range` lists the restrictions as facts, with the refusal each one produces, because that's what a connector has to look up.
This section is the other half: each exclusion has its own reason, and none of them is tidiness.

**No floating point numbers.**
Floating point serialization is the hardest part of any canonicalization, and the hardest part in a language-dependent way.
A hash that comes out differently depending on the runtime makes the chain worthless, and this project keeps the door open for exactly that situation: a native extension through `PyO3`, or a release as free software with a checker written by somebody else reading the same rows, both mean another language recomputing these digests one day.
The price is that every numeric field has to document its scale instead.
A `confidence` is an integer in thousandths, `0` to `1000`, and never `0.0` to `1.0`; a money amount, once anything can carry one, is in minor units, so cents.

`Decimal` was examined as the way out and rejected, and the reason is instructive.
As a JSON *number* it helps not at all, because the scheme serializes numbers with ECMAScript semantics, which means as a double, and the `Decimal` is gone before the bytes exist.
As a JSON *string* it works, and it moves the problem rather than solving it: `"0.75"`, `"0.750"` and `".75"` are three different strings with one value, so three different hashes for one statement, and nothing in the format enforces a normalization.
Integers are canonical through their type, and strings only through discipline.

**Keys stay in lower-case ASCII.**
Letters, digits and underscores leave no room for the two questions that otherwise have to be answered and then enforced forever: which Unicode normalization form a key is in, and whether `Total` and `total` are one key or two.
A canonical form that depends on an answer nobody wrote down isn't canonical.
The restriction also buys the simple sorting described above, which is how the whole scheme reduces to one call with fixed flags.

**Integers stay inside the safe range.**
Past that bound a JSON reader that represents numbers as doubles loses precision, and a value that arrives as something else than it left makes the hash differ across languages for a payload nobody touched.
The bound is the same one JavaScript calls its safe integer range, which is no coincidence: the scheme's number semantics come from ECMAScript, so its safe range is the chain's safe range.

**No null bytes, and no lone UTF-16 surrogates.**
The two share a section and have separate reasons.
A null byte inside a string has no reason to be in a payload and would be refused one layer down anyway, because PostgreSQL `jsonb` can't store it; catching it in the canonicalizer turns a driver-level error deep in a write into a clear refusal before the first transaction opens.
A lone surrogate has no UTF-8 representation at all, so the canonicalizer couldn't produce bytes for it even in principle, and a Python string is free to hold one.

The check in front of `json.dumps` tests against the concrete types `json.dumps` handles, `dict`, `list` and `tuple`, rather than against the abstract `Mapping` and `Sequence`.
That looks like the wrong instinct for Python and is the right one here: `bytes`, `bytearray` and `range` are all sequences and none of them can be turned into JSON, and a foreign mapping is no `dict`.
Whatever passes the check can be turned into JSON, which is the only property the gate exists to guarantee.

## The reserved key

`append` mixes one field of its own into every payload, under the key `evidence`, and it refuses a payload that already carries that key.
The refusal looks heavy-handed for a name collision, and it protects something that can't be recovered.

The kind of evidence separates proof from report: a verbatim wording is a different kind of claim about the world than a recollection, and the distinction is the first thing a later reader of the log needs.
In an append-only store, nobody can supply it afterward.
Once an event is written, its payload is in a hash and in a chain, and a correction is a new event rather than an edit.
So an `evidence` key that the caller happened to use for something else, overwritten without a word, would have taken the caller's value with it forever.
That makes it one of the {ref}`five silent losses of data <silent-losses>` this project has found, and the cheapest of the five to prevent: a refusal, with the key named, before anything is written.

## The same key twice in one batch

`append` takes a batch, and a batch with the same `(source, external_id)` in two entries gets refused before the first transaction opens, with both positions named.
Before that check existed, this was measured:

```text
append([first, second])  ->  [1, 1]

event rows:      [(1, {'note': 'the first', 'evidence': 'verbatim'})]
unit rows:       [(1, 1, 'First content.')]
source_key rows: [('email', 'message-1', 1)]
verify():        []

payload of the second entry   ->  NOT stored
units of the second entry     ->  NOT stored
```

No exception, no finding, no warning, and the caller got two identifiers back as though both entries had been recorded.
One of them was a payload and a set of units that reached the store and left no trace in it.

The reasoning for refusing rather than tolerating is the part that isn't obvious, because idempotency is a feature everywhere else in this system.
The wanted property is idempotency *between* calls: the same submission twice yields the same event, the append loop relies on it, and the transport contract for a retried call needs it.
Nobody asked for idempotency *within* one batch, and it's indistinguishable from a caller's mistake.
If the two entries are equal, the refusal costs the caller nothing, because removing the duplicate is easy.
If they differ, the caller has a bug, and taking the first entry in silence is the worst answer available: it loses data and it looks like success.

After the correction the batch raises `InvalidPayload`, the message names the key and both positions, at index 0 and index 1, and nothing reaches the database, neither event nor unit.

## The pinned test vector

The test suite pins a vector for each version of the hash format, and each vector pins more than its hexadecimal values.
It also holds the canonical bytes, verbatim, for each digest; {ref}`hash-format` reproduces both halves.

The second half is the one that earns its keep.
A pinned hexadecimal value alone says "something is different" when it fails, and leaves the reader to find out what.
With the canonical bytes beside it, a failing test shows *which field* moved: a renamed key, a timestamp with five fractional digits instead of six, a unit that sorted the other way, a `null` that became an empty string.
The bytes turn a one-bit verdict into a diff.

There's a discipline attached, and it's the kind that has to be said out loud because the shortcut is so tempting.
A failing pinned vector is almost never fixed by recomputing it.
The value exists to prove that the hash is reproducible, and a value recomputed from the current code proves only that the current code agrees with itself.
Not even a change to the hash range made on purpose recomputes a vector.
It gets a version of its own and a second vector beside the first, the way version 2 did, and the first vector stays for as long as rows of its version can exist, which is for good.
A vector whose values changed is therefore the signature of the shortcut, whatever version it names.
