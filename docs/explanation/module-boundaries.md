(module-boundaries)=

# About the module boundaries

Previously is one code base with one dependency set and one database, divided into modules whose dependencies run one way.
In stage 1a there are four of them, and the order is `cli` above `core` above `storage` above `contract`.
The order isn't a convention somebody is asked to respect.
It's four `import-linter` contracts, checked by a gate, and the gate prints the contract names, so the names themselves are part of the design rather than labels on it.

The point of the boundaries is narrow and worth stating before the mechanics.
`core` is where the hash chain and the idempotency live, and it must stay able to run against a store it didn't import.
`storage` carries rows and knows nothing about the domain.
`contract` is pure types and knows nothing at all, which is the only reason it can sit underneath both without closing a cycle: `core` has to be able to accept a `RawEvent`, and if the connector contract lived in `connectors` the core wouldn't know it and every connector would reinvent it.

## The edges, and the two that are exempted

The diagram below shows which module imports which, and the two dashed edges are the subject of the rest of this page.

```{mermaid}
:caption: The import edges of stage 1a, with the two exempted edges dashed.

graph TD
    cli[cli] --> core[core]
    cli --> storage[storage]
    cli --> contract[contract]
    core --> storage
    core --> contract
    append["core.append"] -. exempted .-> postgres["storage.postgres"]
    verify["core.verify"] -. exempted .-> postgres
    postgres --> sqlalchemy[sqlalchemy]
```

Two things in that picture answer questions the contract names don't.

`contract` has no outgoing edge, and that's the property the layer order rests on.
`storage` has none either—not even to `contract`, although the layer order would permit one—so the only module in this tree that knows SQL knows nothing else.
A layers contract settles the *order* in which modules may depend on each other; whether an edge exists is a separate question, and counted out it's five of the six edges the order permits.

And `cli` reaches `storage.postgres` directly, for `from_dsn` and the storage type, without needing any exemption.
That's not an inconsistency with the two dashed edges.
The exemptions aren't about the edge `core → storage` being forbidden—the layer order allows it—but about what travels along it: `storage.postgres` imports SQLAlchemy, so every module that imports `storage.postgres` reaches SQLAlchemy transitively, and two contracts forbid exactly that for `core`.
`cli` is no source module of those contracts, so the same edge needs no mention there.

## Four contracts, and the names are the output

What `.importlinter` holds, in the words the gate prints:

```text
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT (2 ignored imports)
Only storage imports sqlalchemy KEPT (2 ignored imports)
No vendor SDK in stage 1a KEPT

Contracts: 4 kept, 0 broken.
```

Two of the four differ from the architecture's table on purpose, and both differences are about what a contract can actually check.

The second contract forbids `sqlalchemy`, `psycopg` and `alembic` rather than the four modules the architecture names.
`connectors`, `gate`, `ai_layer` and `mcp_server` don't exist in stage 1a, and a `forbidden` contract on modules that don't exist checks nothing.
It would stand in the configuration looking like a guarantee and guaranteeing nothing, while the packages `core` could in fact reach today—the database ones—went unnamed.

The third names `core` and `contract` as its sources instead of writing "everything except storage."
The enumeration has to be extended by hand with every stage, and the negation would include every future module without anybody deciding that it should.
That reads like a loss of convenience, and it's the same trade the exemptions below are about, one level up.
It's also measurable, because the negation doesn't merely overreach into the future—it breaks on a module that exists today.
With `previously.cli` added to the sources, which is what "everything except storage" means in this tree:

```text
Probe everything except storage BROKEN (2 ignored imports)

previously.cli is not allowed to import sqlalchemy:
-   previously.cli -> previously.storage.postgres (l.21, l.22)
    previously.storage.postgres -> sqlalchemy
```

`cli` reaches the store on purpose, for `from_dsn` and the storage type, and the layer order permits it without comment.
The negation would have forbidden it and left somebody to add a third exemption for a module that never needed one.

The fourth contract is stricter in stage 1a than it will be in the end, and that's right rather than an oversight.
It forbids `anthropic` and `openai` across the whole package without exception.
From stage 4 on `gate` becomes the one exception, because `gate` is where model calls belong—but as long as there's no `gate`, no model call has any business being in this code at all.

## Why the two exemptions are enumerated and not matched

Two contracts carry exemptions, and both carry the same two:

```text
previously.core.append -> previously.storage.postgres
previously.core.verify -> previously.storage.postgres
```

The reason the exemptions exist is a typing problem, not a layering one.
`core.append` and `core.verify` take a `PostgresStorage` as a parameter, so the signature has to name the type, and both import it only under `if TYPE_CHECKING:` because neither module ever calls a SQLAlchemy function.
`import-linter` counts a `TYPE_CHECKING` import towards a `forbidden` contract regardless: it parses the source, it doesn't watch the runtime.
So the edge has to be named, or the contract is broken by a type annotation.

The question that matters is how to name it, and a wildcard across `previously.core.*` would have been one line instead of two for every `core` module that follows.
It was measured, with a throwaway module `core/zz_probe.py` that imports `PostgresStorage` under `TYPE_CHECKING` exactly as the two real ones do:

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

The count in the gate log is the whole finding.
`3 ignored imports` appeared without anybody having decided that a third module may reach the store, and nothing in the output distinguished the two deliberate edges from the one that arrived by accident.

The deeper reason the wildcard is wrong is which side of the edge it widens.
A wildcard widens the *importer* side, and the importer side is precisely what these two contracts ask about: which modules may reach SQLAlchemy, transitively or otherwise.
A pattern on that side answers the contract's own question in advance, for every module that happens to match a naming pattern.
It's the same move as switching `TYPE_CHECKING` imports off globally, which this project had already rejected—one level smaller, and in the same direction.

Having to edit `.importlinter` for every new `core` module that follows the same pattern isn't the drawback of enumerating.
It's the point.
The number in `N ignored imports` rises only when somebody changed that file on purpose, never because a module happened to be named a certain way.

## The bolt in the test run

The exemptions hang on the import **edge**, not on the `TYPE_CHECKING` property that justifies them, and the configuration has no way to say otherwise.
Pull one of those two imports out of its `if TYPE_CHECKING:` block and the exemption keeps covering it, because it's the same edge either way: `lint-imports` reports `4 kept, 0 broken` before and after.

One gate does notice the simplest form of that, and saying so makes the case for the next one stronger rather than weaker.
`ruff` reports `TC001`, *move application import into a type-checking block*, for as long as the symbol appears in annotations and nowhere else.
But `TC001` is a statement about where a symbol is used, not about which layer may load a database driver, and the two come apart at the case that hurts.
Add one use of the symbol outside an annotation and ruff falls silent, because the import is then no longer one that *could* move into a type-checking block.
That's also the moment at which `core` does load SQLAlchemy for real.

The choice of use decides how far the mutation gets, and the obvious candidate doesn't get far.
An `isinstance` call against the parameter is that candidate, and `pyright` strict refuses it: `storage` is declared as `PostgresStorage`, so the test can never fail.
`core/append.py` argues the same point from the other side, where `_is_text` takes `object` precisely so that its `isinstance` isn't a dead check.
An attribute access on the class is the use that survives every gate but one.

Measured against the project configuration on 2026-10-03, with the import out of the block and `_ = PostgresStorage.__name__` in `verify`, all six gates:

```text
uv run ruff check .           All checks passed!
uv run ruff format --check .  39 files already formatted
uv run pyright                0 errors, 0 warnings, 0 informations
uv run lint-imports           Contracts: 4 kept, 0 broken.
uv run pytest -q              1 failed, 193 passed
    test_the_exempted_core_modules_load_no_sql_at_runtime
    -> loaded sqlalchemy at runtime
make -C docs html             build succeeded.
make -C docs vale             0 errors, 0 warnings and 0 suggestions in 20 files.
make -C docs linkcheck        build succeeded.
```

With an `isinstance` call in that same place instead of the attribute access, the third gate catches the example before the test does:

```text
uv run pyright  1 error
src/previously/core/verify.py:179:12 - error: Unnecessary isinstance call;
"PostgresStorage" is always an instance of "PostgresStorage"
(reportUnnecessaryIsInstance)
```

`tests/test_contracts.py` is the only gate left at that point, and that's what it's there for.
It imports the two exempted modules in a **fresh** interpreter and reports which forbidden top-level packages ended up in `sys.modules`.
The fresh interpreter is a requirement rather than a precaution: inside the test process SQLAlchemy and `psycopg` have long been loaded, through the fixtures, through `storage`, through `testcontainers`, so `sys.modules` there says nothing about anything.

That measurement is the whole argument for the test's existence, and without it written down the test looks like redundancy beside `lint-imports` and `TC001`, and somebody deletes it.
It's green today, so it holds a state that already obtains rather than uncovering an error—which is what it's for, because the exemptions are the one place in this tree where a correct decision and a wrong one look exactly alike in the configuration.

The same file carries a second test that breaks the contracts on purpose, by writing `import sqlalchemy` into a probe module inside `core`, and it checks the contract names and the offending import in the output rather than the return code.
The reason is a measurement too: `lint-imports` answers a broken **configuration** with the same return code `1` as a broken contract.
Measured against a configuration broken on purpose, the return code was `1` with no contract name and no import in the output; measured from the wrong working directory, `1` with `Could not read any configuration.`
In both cases an assertion on the return code alone was green although no contract had been checked at all—and the acceptance condition that a wrong import lets the build fail hung on exactly that assertion.

## The protocol that would make all of this unnecessary

One change removes the two exemptions and the bolt behind them, and it removes them without replacement rather than relocating them.
A `class LogStore[Conn](Protocol)` in `contract`, generic over the connection type, gives `core` something to be typed against that isn't the concrete `PostgresStorage`.
Then the edge `core → storage.postgres` doesn't exist, so there's nothing to exempt, and nothing for a test to watch over either.

The shape is already half in place, which is what makes this a plan rather than a wish.
`storage.rows` imports no SQLAlchemy at all, so the row types it holds would be an unobjectionable source of types across the boundary today.
What's missing is the protocol itself and the decision about the connection type, and that's scheduled for the planning round after the first part of the project rather than for this stage.

The honest version deserves saying plainly.
The exemptions aren't a compromise anybody is proud of.
They're the cost of typing `core` against a concrete store, they're visible in every gate log as a number, and the number is there so the cost stays countable until it's paid off.
