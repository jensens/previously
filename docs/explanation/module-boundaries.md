(module-boundaries)=

# About the module boundaries

Previously is one code base with one dependency set and one database, divided into modules whose dependencies run one way.
Through stage 1c there are four of them, and the order is `cli` above `core` above `storage` above `contract`.
The order isn't a convention somebody is asked to respect.
It's `import-linter` contracts, six of them since stage 1c, checked by a gate, and the gate prints the contract names, so the names themselves are part of the design rather than labels on it.

The point of the boundaries is narrow and worth stating before the mechanics.
`core` is where the hash chain and the idempotency live, and it must stay able to run against a store it didn't import.
`storage` carries rows and knows nothing about the domain.
`contract` is pure types and knows nothing at all, which is the only reason it can sit underneath both without closing a cycle: `core` has to be able to accept a `RawEvent`, and if the connector contract lived in `connectors` the core wouldn't know it and every connector would reinvent it.
Since stage 1b `contract` also holds the row types and the store protocol that `core` is typed against, and both are types in the same sense—no logic, no dependency outside the standard library.

## The edges

The diagram shows which module imports which, and since stage 1b there's nothing dashed in it.
The two arrows that stage 1c added, to `pyrage` and to `boto3`, each have a contract that names the one module allowed to draw them.
The arrow to `sqlalchemy` is held the other way round: its contracts name the modules that mustn't draw it, `core` and `contract`, as the section on the contracts explains.

```{mermaid}
:caption: The import edges after stage 1c: all six between its own modules, and not one of them exempted. Three arrows leave the package.

graph TD
    cli[cli] --> core[core]
    cli --> storage[storage]
    cli --> contract[contract]
    core --> storage
    core --> contract
    storage --> contract
    storage --> sqlalchemy[sqlalchemy]
    core --> pyrage[pyrage]
    storage --> boto3[boto3]
```

Two things in that picture answer questions the contract names don't.

`contract` has no outgoing edge, and that's the property the layer order rests on.
A layers contract settles the *order* in which modules may depend on each other; whether an edge exists is a separate question, and counted out, all six edges the order permits exist.

That count was five until stage 1b.
`storage` had no edge to `contract` at all, not even though the layer order would have permitted one, and the sixth edge arrived when the row types moved out of `storage/rows.py` into `contract/rows.py`—the store protocol in `contract.store` names those types, and `contract` may import nothing above itself.
Counted per module, over import statements only, because two modules under `storage` mention `previously.core` in prose rather than in an import, and a count over all text would include them:

```text
$ grep -rhoE 'from previously\.[a-z]+' src/previously/cli.py | sort -u
from previously.contract
from previously.core
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/core | sort -u
from previously.contract
from previously.core
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/storage | sort -u
from previously.contract
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/contract | sort -u
from previously.contract
```

Three target packages for `cli`, three for `core` of which one is itself, two for `storage` of which one is itself, and for `contract` nothing but itself.
That's six edges between distinct modules, and the last line is the layer order's foundation stated as a measurement.

And `cli` reaches `storage.postgres` directly, for `from_dsn` and the storage type, and it never needed an exemption for that.
Until stage 1b this page carried two dashed edges from `core` into `storage.postgres`, and `cli` was no inconsistency beside them.
The exemptions weren't about the edge `core → storage` being forbidden—the layer order allows it—but about what travels along it: `storage.postgres` imports SQLAlchemy, so every module that imports `storage.postgres` reaches SQLAlchemy transitively, and two contracts forbid exactly that for `core`.
`cli` is no source module of those contracts, so the same edge needs no mention there.

## Six contracts, and the names are the output

What `.importlinter` holds, in the words the gate prints:

```text
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT
Only storage imports sqlalchemy KEPT
No vendor SDK in the package KEPT
Only core.sealing imports pyrage KEPT (1 ignored import)
Only storage.s3 imports boto3 KEPT (2 ignored imports)

Contracts: 6 kept, 0 broken.
```

The output was measured on 2026-10-05.
The second and third lines read `KEPT (2 ignored imports)` until 2026-10-04.
That number was the price of typing `core` against a concrete store, and it stood in the gate log so the price stayed countable until somebody paid it.
Stage 1b paid it, and the parentheses on the last two contracts are a different thing: no debt, but the one module each contract exists to allow, named.

Two of the first four contracts differ from the architecture's table on purpose, and both differences are about what a contract can actually check.

The second contract forbids `sqlalchemy`, `psycopg` and `alembic` rather than the four modules the architecture names.
`connectors`, `gate`, `ai_layer` and `mcp_server` don't exist in stage 1a, and a `forbidden` contract on modules that don't exist checks nothing.
It would stand in the configuration looking like a guarantee and guaranteeing nothing, while the packages `core` could in fact reach today—the database ones—went unnamed.

The third names `core` and `contract` as its sources instead of writing "everything except storage."
The enumeration has to be extended by hand with every stage, and the negation would include every future module without anybody deciding that it should.
That reads like a loss of convenience, and it's the same trade the section below is about, one level up.
It's also measurable, because the negation doesn't merely overreach into the future—it breaks on a module that exists today.
With `previously.cli` added to the sources, which is what "everything except storage" means in this tree, measured on 2026-10-04 and abbreviated at the line numbers of the second step:

```text
Probe everything except storage BROKEN

previously.cli is not allowed to import sqlalchemy:
-   previously.cli -> previously.storage.postgres (l.21, l.22)
    previously.storage.postgres -> sqlalchemy
```

`cli` reaches the store on purpose, for `from_dsn` and the storage type, and the layer order permits it without comment.
The negation would have forbidden it and left somebody to add an exemption for a module that never needed one.

The fourth contract is stricter in stage 1a than it will be in the end, and that's right rather than an oversight.
It forbids `anthropic` and `openai` across the whole package without exception.
From stage 4 on `gate` becomes the one exception, because `gate` is where model calls belong—but as long as there's no `gate`, no model call has any business being in this code at all.

## Two contracts for the blobs

Stage 1c brought two foreign systems for the blobs, and each got a contract over the whole package with one module named as the exception.
{ref}`blobs` says what the two modules do; this section says why each sits where it does.

`pyrage` may be imported by `core.sealing` and nowhere else.
Sealing belongs in `core` because that's where the rules are: the format a content is sealed in is part of what the log promises about it, and the store below gets and gives ciphertext only.
The probe that proves the contract therefore goes into `storage`, not into `core`, since a storage module that could open what it stores is the mistake the contract exists for.

`boto3` and `botocore` may be imported by `storage.s3` and nowhere else.
Storing belongs in `storage` for the reason SQL does: that's where the foreign systems are, and what reaches `core` is the protocol in `contract.blobs` and the errors in `storage.errors`.
`botocore` stands beside `boto3` because the exceptions and the client configuration come from there, and an import of either would carry the foreign system upwards.
The adapter keeps that promise for a stream read long after `get` returned, too: it hands out a thin wrapper whose `read` translates what `botocore` raises, because `pyrage` lets an exception out of `read` pass unchanged into `core`.

The exceptions are edges named one by one, never a pattern, for the reason the next section measures.
One more property comes for free, measured on 2026-10-05: an exemption for an import that doesn't exist makes `lint-imports` fail with `No matches for ignored import`, so neither exemption can outlive the edge it names.

## Why the two exemptions were enumerated and not matched

Both contracts that forbid SQLAlchemy in `core` carried an exemption until 2026-10-04, and both carried the same two edges:

```text
previously.core.append -> previously.storage.postgres
previously.core.verify -> previously.storage.postgres
```

They're gone, and the section stays, because the reasoning for *how* they were written is the one that outlives them.

The reason they existed at all was a typing problem, not a layering one.
`core.append` and `core.verify` took a `PostgresStorage` as a parameter, so the signature had to name the type, and both imported it only under `if TYPE_CHECKING:` because neither module ever called a SQLAlchemy function.
`import-linter` counts a `TYPE_CHECKING` import towards a `forbidden` contract regardless: it parses the source, it doesn't watch the runtime.
So the edge had to be named, or the contract was broken by a type annotation.

The question that mattered was how to name it, and a wildcard across `previously.core.*` would have been one line instead of two for every `core` module that followed.
It was measured, with a throwaway module `core/zz_probe.py` that imported `PostgresStorage` under `TYPE_CHECKING` exactly as the two real ones did:

```text
with ignore_imports = previously.core.* -> previously.storage.postgres
    core knows no foreign system and no model KEPT (3 ignored imports)
    Only storage imports sqlalchemy KEPT (3 ignored imports)
    Contracts: 4 kept, 0 broken.

with the two edges named one by one
    core knows no foreign system and no model BROKEN (2 ignored imports)
    Only storage imports sqlalchemy BROKEN (2 ignored imports)
    previously.core.zz_probe -> previously.storage.postgres (l.4)
```

The count in the gate log was the whole finding.
`3 ignored imports` appeared without anybody having decided that a third module may reach the store, and nothing in the output distinguished the two deliberate edges from the one that arrived by accident.

The deeper reason the wildcard was wrong is which side of the edge it widens.
A wildcard widens the *importer* side, and the importer side is precisely what these two contracts ask about: which modules may reach SQLAlchemy, transitively or otherwise.
A pattern on that side answers the contract's own question in advance, for every module that happens to match a naming pattern.
It's the same move as switching `TYPE_CHECKING` imports off globally, which this project had already rejected—one level smaller, and in the same direction.

That's the rule an exemption here would have to meet again.
Should one ever come back, it's a named edge and never a pattern, and having to edit `.importlinter` for every module that follows isn't the drawback of enumerating—it's the point.
The number in `N ignored imports` rises only when somebody changed that file on purpose, never because a module happened to be named a certain way.

## The bolt that fell with the edge

A third test in `tests/test_contracts.py` guarded the two exemptions, and stage 1b deleted it without putting anything in its place.
What it watched was a gap the configuration couldn't express.
The exemptions hung on the import **edge**, not on the `TYPE_CHECKING` property that justified them: pull one of those two imports out of its `if TYPE_CHECKING:` block and the exemption kept covering it, because it was the same edge either way, and `lint-imports` reported `4 kept, 0 broken` before and after.
So the test imported the two exempted modules in a **fresh** interpreter and reported which forbidden top-level packages ended up in `sys.modules`.
The fresh interpreter was a requirement rather than a precaution: inside the test process SQLAlchemy and `psycopg` have long been loaded, through the fixtures, through `storage`, through `testcontainers`, so `sys.modules` there says nothing about anything.

One gate does notice the simplest form of that mutation, and saying so made the case for the test stronger rather than weaker.
`ruff` reports `TC001`, *move application import into a type-checking block*, for as long as the symbol appears in annotations and nowhere else.
But `TC001` is a statement about where a symbol is used, not about which layer may load a database driver, and the two come apart at the case that hurts.
Add one use of the symbol outside an annotation and ruff falls silent, because the import is then no longer one that *could* move into a type-checking block.
That's also the moment at which `core` does load SQLAlchemy for real.

The choice of use decided how far the mutation got, and the obvious candidate didn't get far.
An `isinstance` call against the parameter was that candidate, and `pyright` strict refused it: `storage` was declared as `PostgresStorage`, so the check could never fail.
`core/append.py` still argues the same point from the other side, where `_is_text` takes `object` precisely so that its `isinstance` isn't a dead check.
An attribute access on the class was the use that survived every gate but one.

Measured against the project configuration on 2026-10-03, with the import out of the block and `_ = PostgresStorage.__name__` in `verify`, all six gates:

```text
uv run ruff check .           All checks passed!
uv run ruff format --check .  39 files already formatted
uv run pyright                0 errors, 0 warnings, 0 informations
uv run lint-imports           Contracts: 4 kept, 0 broken.
uv run pytest -q              1 failed, 193 passed         (194 tests then)
    test_the_exempted_core_modules_load_no_sql_at_runtime
    -> loaded sqlalchemy at runtime
make -C docs html             build succeeded.
make -C docs vale             0 errors, 0 warnings and 0 suggestions in 20 files.
make -C docs linkcheck        build succeeded.
```

Every number above is the number of 2026-10-03, and the block keeps it that way rather than tracking the tree.
Three of the lines have moved since.
Measured on 2026-10-04: `uv run ruff format --check .` reports `48 files already formatted`, `uv run pytest` reports `232 passed`, and `make -C docs vale` reads 22 files.
The file count moved by one with `contract/store.py` and by the rest with stage 1b's other modules, all of it on 2026-10-04, the day after the block was measured.
The fifth line is the one worth reading twice: the test that failed there is the test stage 1b deleted, so a run today has nothing to put in its place, and that's why the failure can't be reproduced from the current tree.

The first line and the fourth are the whole case for the test.
`ruff` passed and `lint-imports` passed while `core` loaded SQLAlchemy at runtime, and the fifth line is the only gate that noticed.

With an `isinstance` call in that same place instead of the attribute access, the third gate caught the example before the test did:

```text
uv run pyright  1 error
src/previously/core/verify.py:179:12 - error: Unnecessary isinstance call;
"PostgresStorage" is always an instance of "PostgresStorage"
(reportUnnecessaryIsInstance)
```

The six-gate block further up, not the `pyright` line right above, is the measurement that argued for the test's existence, and without it written down the test looked like redundancy beside `lint-imports` and `TC001`, and somebody would delete it.
It was green on the day it was written, so it held a state that already obtained rather than uncovering an error—which is what it was for, because the exemptions were the one place in this tree where a correct decision and a wrong one looked exactly alike in the configuration.

Somebody did, and for the other reason: there's no exempted edge left to pull out of a `TYPE_CHECKING` block, because there's no import of `PostgresStorage` in `core` at all.
The bolt fell with the edge rather than moving elsewhere, and `tests/test_contracts.py` has held two tests since stage 1b.
The one that breaks the contracts on purpose stays, and it's now the only counter-probe in the file: it writes `import sqlalchemy` into a probe module inside `core` and checks the contract names and the offending import in the output rather than the return code.
The reason for checking the output is a measurement too: `lint-imports` answers a broken **configuration** with the same return code `1` as a broken contract.
Measured against a configuration broken on purpose, the return code was `1` with no contract name and no import in the output; measured from the wrong working directory, `1` with `Could not read any configuration.`
In both cases an assertion on the return code alone was green although no contract had been checked at all—and the acceptance condition that a wrong import lets the build fail hung on exactly that assertion.

## The protocols that made the exemptions unnecessary

One change removed the two exemptions and the bolt behind them, and it removed them rather than relocating them.
`class LogStore[Conn](Protocol)` in `contract.store`, generic over the connection type, gives `core` something to be typed against that isn't the concrete `PostgresStorage`.
`append` and `verify` are generic functions over that connection type, the edge `core → storage.postgres` doesn't exist, so there's nothing to exempt and nothing for a test to watch over.

The protocol had nine methods when stage 1b introduced it, and the number was read off the two callers of that day rather than copied from the store's method list:

```text
$ grep -o 'storage\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py \
    | sed 's/^[^:]*://' | sort -u
storage.begin(
storage.count_events(
storage.insert_event(
storage.lookup(
storage.read(
storage.snapshot(
storage.source_keys(
storage.tip(
storage.units_by_event(
```

Reading it off that way is what keeps the protocol a statement about what `core` needs instead of a copy of what the store happens to offer.
`PostgresStorage.units` is the test of that: it fetches the units of a single event, `cli` calls it for `show`, and `core` never does—so it's a method of the store and not a member of the protocol.
A protocol copied from the implementation would have carried ten methods and said something false about `core`.
Stage 1c took it to thirteen, read off the same way from the five modules of `core` that name it today; the command that counts them stands at the top of `contract/store.py`.

The store still has to satisfy the protocol, and that's now a typed claim rather than a guarded one.
Renaming `count_events` to `count_rows` in `storage/postgres.py`, measured on 2026-10-04, turns `pyright` red at every place a `PostgresStorage` is handed to `append` or `verify`:

```text
uv run pyright  75 errors
src/previously/cli.py:106:18 - error: Argument of type "PostgresStorage" cannot be
assigned to parameter "storage" of type "LogStore[Conn@append]" in function "append"
  "PostgresStorage" is incompatible with protocol "LogStore[Conn@append]"
    "count_events" is not present (reportArgumentType)
```

Note where the errors land: at the call sites, in `cli` and in the tests, and not in `core`.
That's the shape of the change as much as a consequence of it.
`core` no longer mentions a store implementation, so it has nothing left to be wrong about; whoever passes a store is the one who has to own something that fits.

The row types had to move for this, and that's the part worth knowing before another protocol is added.
`contract.store` names `Tip`, `EventRow` and `UnitRow` in its signatures, and `contract` is the bottom layer, so it may import nothing above itself.
Leaving the types in `storage/rows.py` would have meant a `contract → storage` import, and the first contract on this page is the one that forbids it.
Measured on 2026-10-04, with a throwaway import from `storage` in `contract/store.py`:

```text
Layers: core above storage, contract below both BROKEN

previously.contract is not allowed to import previously.storage:
- previously.contract.store -> previously.storage.errors (l.27)
```

So `storage/rows.py` became `contract/rows.py`, six import sites followed, and no re-export stayed behind: a module that exists only to forward a name is the kind of thing this project removes rather than keeps.
`storage.postgres` imports the row types from `contract` now, which is where the page's sixth edge came from.

A second protocol has existed since stage 1b, `ProjectionStore[Conn]`, for the projection store ({ref}`projections`), and it's a second one by design rather than more methods on this one.
`LogStore` is append-only—write once, read in chain order, never change.
A projection store empties, inserts and updates, because a projection is derivable and disposable by design ({ref}`projections`).
One protocol covering both would blur exactly the line that separates them: a projection carries no truth of its own, and a type that offers "append to the log" and "truncate the table" through the same interface stops saying so.

Stage 1c added a third, `RedactionStore[Conn]`, with three methods: `lock_event`, `erase_payload` and `erase_units`.
An erasure changes rows of the log, which is the one thing `LogStore` promises never to do, and the protocol of its own keeps that promise a statement about a type.
Nothing typed against `LogStore` can erase, and what can erase is listed in one place, three methods long; {ref}`erasure` says what those three may change and why.
Adding them to `LogStore` would have made every caller of the log a possible eraser, `append` and `verify` among them.

The honest version of the old arrangement deserves saying plainly.
The exemptions weren't a compromise anybody was proud of.
They were the cost of typing `core` against a concrete store, they were visible in every gate log as a number, and the number was there so the cost stayed countable until it was paid off.
It's paid.
