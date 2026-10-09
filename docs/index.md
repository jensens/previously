# Previously

Previously is an append-only knowledge store for project histories.
It records what happened, splits each record into units, and chains every event by hash so that a later change can't pass unnoticed.

::::{grid} 1 1 2 2

:::{grid-item-card}
:link: tutorials/index
:link-type: doc

**Tutorials**
^^^
Start here.
Record your first event and verify the chain.
:::

:::{grid-item-card}
:link: how-to/index
:link-type: doc

**How-to guides**
^^^
Solve a specific problem: take in the mail of a folder, set a policy and try a model call, erase something from the log, attach a file and fetch it again, keep the blob key safe, run a blob store on your machine, check the chain in operation, restore a backup, add a migration, rebuild a projection, run the image, cut a release.
:::

:::{grid-item-card}
:link: reference/index
:link-type: doc

**Reference**
^^^
Look up a command, a configuration variable, a column, the hash format, how a mail maps onto an event, or what the events of the policy and of a model call hold.
:::

:::{grid-item-card}
:link: explanation/index
:link-type: doc

**Explanation**
^^^
Understand why the chain hashes a digest, why there is no sequence, and what the chain doesn't cover; how an erasure works as an event, and what it can't reach; how blobs are addressed, sealed and kept; what a connector takes in and how it recognizes a mail it has seen; where content crosses the boundary of the system and who guards each place; how the processing policy decides which model sees what; and why a release installs the image from PyPI.
:::
::::

```{toctree}
:hidden:

tutorials/index
how-to/index
reference/index
explanation/index
```
