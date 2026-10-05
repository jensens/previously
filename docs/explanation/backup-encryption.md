(backup-encryption)=

# About the backup encryption

The backups this design plans for Previously are encrypted on the client, before they leave the cluster, with `aes-256-cbc` and a key that lives outside the data path; no backup runs yet.
That reads like a strong choice made out of caution.
It isn't: at the storage provider this project uses, client-side encryption is the only kind that encrypts anything at all.
This page is the reasoning, and it ends with the three paths that were on the table and the one finding that would still overturn the chosen one.

## The provider encrypts nothing at rest

Checked on 2026-10-03 against the documentation of Hetzner Object Storage, and the position is sharper than the first draft of this reasoning assumed:

> There is no default data-at-rest encryption of objects, but you can encrypt your data during the upload using SSE-C.

So it isn't merely that there's no SSE-S3.
There's **no** encryption at rest at all, as long as nobody applies one.
That single sentence turns client-side encryption from the more comfortable option into the only option with any effect, and it's the reason this whole section exists rather than a line in a configuration file.

## Server-side encryption breaks on copies

The one server-side mode on offer is SSE-C, where the client supplies the key with every request, and for a backup tool that mode isn't merely inconvenient.
The same documentation states that a copy of an SSE-C encrypted object isn't supported, and that `CopyObject` works only within the same bucket.

The cause lies underneath the API.
The provider confirms that any data saved in a bucket is saved in a Ceph cluster, and in the Ceph object gateway none of the server-side encryption modes supports `CopyObject`.
Every workflow that copies encrypted objects breaks there, which is most of what a backup repository does over its lifetime.

This isn't a prediction.
It has already landed operationally in a sister project (kup6s), where the standing rule reads *never use server-side encryption*, alongside the detour around the tagging calls that the same provider answers with `501`.

## One tool can do it, and the obvious one can't

`barman-cloud-backup` and `barman-cloud-wal-archive` support **only** server-side encryption, as AES256 or `aws:kms`.
Barman in its classic form can encrypt with GPG; the `barman-cloud` tools can't, and the request for that capability remains open.
Put the two facts together—a provider with no encryption at rest and a tool that can only ask the provider to encrypt—and the whole database would lie in the bucket in the clear.

The pgBackRest plugin for CNPG-I closes exactly that gap.
It encrypts backups **and** write-ahead log archives on the client, with `encryption: aes-256-cbc` and the key out of a secret, and it carries the rest of what a database backup needs besides: data directory backup and restore, archiving, point-in-time recovery, replica clusters.
The provider's missing SSE-S3 becomes irrelevant, because the data is already encrypted when it leaves the cluster.

## It isn't a choice between proven and new

The decision looks like *established Barman against a young plugin*, and that framing is wrong.
`barmanObjectStore` has been deprecated in CNPG since 1.26 and is meant to be removed with 1.30, and its successor is the Barman Cloud plugin—which is to say, a CNPG-I plugin, just as new.

> Two new plugins, and only one of them encrypts.

Staying put isn't one of the options.
The choice is between two new things, and that changes what maturity can even mean here.

## Which implementation, measured and dated

Two implementations exist, from Dalibo and from Opera Software, and which one is the better kept at build time has to be looked up rather than remembered.
What follows is a dated reading, so that the looking up doesn't start from zero.
It's carried over from §10.5 of the frozen architecture record, where it was taken on 2026-10-03: neither the table below nor the pgBackRest figures after it were collected on this page.

```text
                          dalibo/cnpg-plugin-pgbackrest   operasoftware/...
commits since 2026-07-03                              2                  30
latest releases                      v0.0.3 (2026-06-25)   v0.8.0 (2026-08-25),
                                                              v0.7.0, v0.6.1
open issues                                          23                  44
self-description                                       —   README: EXPERIMENTAL
```

That measurement reverses the expectation.
This reasoning at first called the implementation from Opera expressly experimental and therefore leaned toward the one from Dalibo.
Measured, the one from Dalibo has stood still since mid-year while the one from Opera released weekly through August.
The README from Opera still carries the experimental note, so it isn't *the more mature one*—it's **the one being worked on**, which is a different and more useful property.

The plugin from Opera also names precisely what's needed here: client-side encryption of both backups and archives, `aes-256-cbc` with the key from a secret, CNPG from 1.25 on.

Neither of the two calls itself production-ready, so the choice stays a build-time decision.
The criterion isn't the version number—`0.0.3` against `0.8.0` says more about counting conventions than about maturity—but whether somebody is still working on it on the day the cluster gets built.
Collect that table again; don't read this one.

A warning belongs beside it, for whoever performs that maintenance check.
Articles circulate claiming that pgBackRest itself is archived or no longer maintained.
That's false, checked on 2026-10-03 against the GitHub API: `archived: false`, last push on 2026-10-02, 24 commits in the preceding 30 days, and three releases in three months, `2.59.0`, `2.59.1` and `2.59.2`, the last of them on 2026-09-27.
The next person to check will stumble over the same pages, which makes them a useful example of the rule they violate: a claim about maintenance gets checked against the repository, never against a headline.

## The price of the passphrase

It belongs said out loud, because it's of the same family as everything else in this design: **whoever loses the passphrase loses the backups, for good.**
With server-side encryption the provider holds the key and can help when it matters; here nobody can, by construction, which is the whole point and also the whole exposure.

Two requirements follow.

The passphrase has to stand **before the first backup**.
Changing it later is an operation across the entire repository, not an entry in a configuration file, and the window for getting it right closes with the first write.

And it needs the same care as the data it protects: in the vault, with a documented path to recover it, and tested.
A key that has never been used for a restore is as little a key as an untested restore is a backup—which is why the chain check in {ref}`verify-the-chain` is the end of the restore procedure rather than an optional extra.

## Where the keys lie, and why the question stops here

Two encryption points in this design need a key, and there are two keys.
The blobs are sealed in the `age` format before they leave the process, and the identity that opens them lies in a directory of its own; {ref}`blobs` explains the format and the seam.
The backups this design plans are encrypted on the client with `aes-256-cbc` and a passphrase.
For both the same rule holds: a key must not lie where the data it opens lies.
The identity of the blobs doesn't belong in the bucket, nor in a backup of the bucket; the passphrase doesn't belong in the backup target.
A key that lies beside its data protects nothing from whoever reaches the data, and goes down with it in the same incident.

In the operation this design plans, both keys arrive through the External Secrets Operator, out of a namespace of their own—which is to say, not the namespace the database runs in.
That's the operational answer to the obvious objection about one vault holding everything: one place, two keys, and both of them outside the reach of what they protect.
On a host without that operator, the same two requirements hold for whatever directory or file the keys come from.
The keys are separate because the damage radius differs; blobs and backups aren't the same loss, so they aren't the same key.

A real vault is the direction of travel, and it isn't this project's business.
That's a platform decision and belongs where the clusters are run.
Previously asks the platform for two properties, and both are independent of whatever fulfills them: the keys lie neither in the database's namespace nor in the backup target, and there's a **rehearsed** way to obtain them again.
So the question *which vault* isn't left open here—it's delegated, with two checkable requirements in place of an answer.

## The retention is part of an erasure's promise

An erasure takes content out of the log, and out of the bucket, and leaves it in every backup taken before it; {ref}`erasure` explains why it can't do more.
So a backup's retention isn't only a question of how far back a restore can reach.
It's also how long an erased content stays readable for whoever holds the backup and its key.
Whoever promises erasure within a period chooses the retention of the database backups and of the write-ahead log archive by that period, and, where the bucket is backed up or copied, the retention of that copy as well.

The encryption doesn't shorten that period.
The backup and its passphrase stay together on the side of the operator, so a backup that opens for a restore opens for the erased content as well, until it's deleted.

## Three paths, and what would overturn the chosen one

**A: pgBackRest for this database alone.**
Price: a second backup tool in an operation that already has one, and a second restore rehearsal.

**B: keep the `barman-cloud` tools and move the backup target to an S3 service in the EU with real server-side encryption.**
Price: a second provider relationship, and—the decisive part—the provider holds the key.

**C: keep the `barman-cloud` tools and leave the backups in the clear.**
Price: nothing technical at all, which is exactly what makes it dangerous.
It has to be a *decision*, written down as one, rather than something that happens because nobody looked.

**A is chosen, and the reason isn't tool quality.**
It's who holds the key.
Under A it never leaves the project's own machine; under B the provider can decrypt when pressed; under C anybody who reaches the bucket can.
For a store whose entire purpose is a defensible history of client projects, that distinction outranks the convenience of a single backup tool.

**What would overturn A:** a finding that this database's backups stand no differently in the threat model than those of the other databases in the same cluster.
Then uniformity wins the argument and B is the clean choice.
That check hasn't been carried out.
It depends on what lies in those other databases, which is a question for the people who run them rather than for this design, and it's recorded here as unsettled instead of being answered by assumption.

That the sister project has the same point open—the `barman-cloud` tools against the same provider, in the clear—is no argument for A either way.
It's only evidence that the gap is real and doesn't originate in this design.

## The two objections that remain

**Plugin maturity.**
A backup system is the worst possible place for young software, and the objection stands.
But the answer to it doesn't depend on which plugin gets picked: an untested restore is no backup.
Here that test says more than it usually does, because the hash chain verifies the **restored holdings** and not merely that PostgreSQL came up.

**Two backup tools in one operation.**
Barman runs in the rest of the cluster and this design puts pgBackRest beside it, which costs two operational paths and two restore procedures.
By the principle just stated, that means two rehearsals to keep in practice, not one.
The objection is legitimate, and it was missing from this reasoning at first—worth recording, because an argument that lists only the costs it finds comfortable isn't an argument.

## What it tidies up

The backup encryption follows the same line as the content blobs: client-side, with the keys outside the data path.
One principle in two places, rather than encrypted blobs sitting next to a database in the clear—which is the shape these decisions take when each one is made on its own.
