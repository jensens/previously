# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Taking in what a connector fetches: the run ({ref}`artifact-identity`).

One function, `ingest`. It reads the connector's watermark, asks the
connector for what is new since, and for every mail it is handed:

1. `core.mail` maps the raw bytes onto an event, its attachments and the
   mails attached to it;
2. every event is looked up before anything of it is stored — a key the log
   or the batch already holds with the same artifact is known, one it holds
   with another artifact becomes a variant under its own key;
3. for every event that is new, the raw mail and each attachment go into the
   blob store, and the references into the event.

Then the batch is appended, and **only then** is the watermark set, to the
position of the last mail the batch covered. A run that stops anywhere in
between leaves the watermark where the last append left it; the next run
fetches the same mails again, finds their blobs stored and their events
known, and writes nothing twice. A blob stored for a batch that never got
appended stays in the store without an event until that next run.

The lookup comes before the blobs for two reasons. A second copy of a mail
— the same Message-ID and the same content, from another mailbox, with
other `Received` lines — is other raw bytes and would be another object,
stored for nothing. And a mail whose event has been erased would put its
raw bytes back into the store, from which the erasure deleted them.

`append` decides the same rule once more, inside its transaction, for what
another writer appended in between: a key that has turned up with another
artifact since the lookup turns the event into a variant there too, and the
batch is appended again. Its blobs stay the same; only the key changes.

Memory: one mail at a time. Its attachments and the mails inside it are
held while it is mapped and stored, and let go once its events are in the
batch; a batch holds events with their references, not their content.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import replace
from previously.contract.types import BlobRef
from previously.contract.types import RawEvent
from previously.contract.types import Watermark
from previously.core.append import append
from previously.core.append import known_id
from previously.core.append import MAX_BATCH
from previously.core.blob import store_blob
from previously.core.errors import ArtifactChanged
from previously.core.mail import map_mail
from previously.core.mail import variant_key
from typing import TYPE_CHECKING

import io


if TYPE_CHECKING:
    from datetime import datetime
    from previously.contract.blobs import BlobStore
    from previously.contract.connector import Connector
    from previously.contract.store import LogStore
    from previously.contract.store import WatermarkStore
    from previously.contract.types import Fetched
    from previously.core.mail import Mapped


# The media type of the raw mail, the blob that comes first.
RAW_MAIL = "message/rfc822"


@dataclass(frozen=True)
class Ingested:
    """What a run did.

    The counts are of **events**, not of mails: a mail with a mail attached
    is two events, and each of them is appended or known on its own.
    `appended` counts the events this run wrote, `known` the events it found
    already in the log or earlier in the same batch. `variants` names each
    variant this run wrote, as the Message-ID it deviates from and the `id`
    of its event; the variants are counted in `appended` too. `position` is
    the watermark as it stands after the run, or `None` when the connector
    has none.

    One race the counts cannot see: an event that another writer appends
    under the same key in the moment between the tip being read for the
    batch and the batch's own transaction is counted as appended here,
    though it is that writer's.
    """

    appended: int
    known: int
    variants: tuple[tuple[str, int], ...]
    position: Mapping[str, str] | None


def ingest[Conn](
    log: LogStore[Conn],
    marks: WatermarkStore[Conn],
    blobs: BlobStore,
    connector: Connector,
    *,
    recipient: str,
    recorded_at: datetime,
) -> Ingested:
    """Takes in what `connector` has that is new since its watermark, and
    moves the watermark after every batch that is appended.

    Two parameters for one store, the way `redact_event` takes two: Python
    has no intersection of two protocols, and the store that keeps the
    watermark is the store that holds the log. `recipient` is the key every
    blob is sealed to; `recorded_at` goes into every event and is the
    `set_at` of every watermark the run writes.

    Whatever the connector raises passes through, and so does whatever the
    log or the blob store raises: the watermark then stands where the last
    batch left it.
    """
    with log.snapshot() as conn:
        since = marks.watermark(conn, connector.name)
    run = _Run(log, marks, blobs, connector.name, recipient=recipient, recorded_at=recorded_at)
    run.position = None if since is None else since.position
    for fetched in connector.fetch(since):
        run.take(fetched)
    run.flush()
    return Ingested(
        appended=run.appended,
        known=run.known,
        variants=tuple(run.variants),
        position=None if run.position is None else dict(run.position),
    )


@dataclass
class _Entry:
    """An event of the batch: `parent` is the index of the entry of the mail
    it was attached to, when that mail is in the batch too, and
    `variant_of` the Message-ID it deviates from, when it is a variant."""

    event: RawEvent
    parent: int | None
    variant_of: str | None


class _Run[Conn]:
    """The state of one run: the batch being gathered, the counts so far,
    and the position of the last mail taken."""

    def __init__(
        self,
        log: LogStore[Conn],
        marks: WatermarkStore[Conn],
        blobs: BlobStore,
        connector: str,
        *,
        recipient: str,
        recorded_at: datetime,
    ) -> None:
        self.log = log
        self.marks = marks
        self.blobs = blobs
        self.connector = connector
        self.recipient = recipient
        self.recorded_at = recorded_at
        self.entries: list[_Entry] = []
        # The artifact of every key in the batch: `append` refuses a key
        # twice in one batch, and two copies of a mail in one folder are
        # ordinary, so the batch decides them by the same rule as the log.
        self.in_batch: dict[tuple[str, str], bytes | None] = {}
        self.position: Mapping[str, str] | None = None
        self.unsaved = False
        self.appended = 0
        self.known = 0
        self.variants: list[tuple[str, int]] = []

    def take(self, fetched: Fetched) -> None:
        mapped = map_mail(fetched.raw, internaldate=fetched.internaldate, found_in=fetched.found_in)
        # A mail and the mails inside it go into one batch, never two:
        # `forwarded_in` names the key of the outer one.
        if self.entries and len(self.entries) + _count(mapped) > MAX_BATCH:
            self.flush()
        self._take(mapped, parent_key=None, parent=None)
        self.position = fetched.position
        self.unsaved = True

    def _take(self, mapped: Mapped, *, parent_key: str | None, parent: int | None) -> None:
        event = mapped.event
        if parent_key is not None:
            # The key the outer mail ended up under, which is a variant key
            # when the outer one became a variant.
            event = replace(event, payload={**event.payload, "forwarded_in": parent_key})
        event, variant_of, new = self._resolve(event)
        index = None
        if new:
            index = len(self.entries)
            self.entries.append(_Entry(self._stored(event, mapped), parent, variant_of))
            self.in_batch[event.source, event.external_id] = event.artifact_hash
        else:
            self.known += 1
        for inner in mapped.inner:
            self._take(inner, parent_key=event.external_id, parent=index)

    def _resolve(self, event: RawEvent) -> tuple[RawEvent, str | None, bool]:
        """The event under the key it goes in with, the Message-ID it
        deviates from if it is a variant, and whether it is new."""
        try:
            return event, None, not self._holds(event)
        except ArtifactChanged as changed:
            variant = _variant(event, changed)
        # A variant key held with yet another artifact would take two
        # artifacts whose hashes share their first 64 bits; the
        # `ArtifactChanged` then passes and stops the run.
        return variant, event.external_id, not self._holds(variant)

    def _holds(self, event: RawEvent) -> bool:
        """Whether the batch or the log holds the key of `event` with its
        artifact; raises `ArtifactChanged` when either holds another."""
        key = (event.source, event.external_id)
        if key in self.in_batch:
            # The rule of `append`: a hash that is not given compares with
            # nothing.
            known = self.in_batch[key]
            arrived = event.artifact_hash
            if known is not None and arrived is not None and known != arrived:
                raise ArtifactChanged(*key, known=known, arrived=arrived)
            return True
        with self.log.snapshot() as conn:
            return known_id(self.log, conn, event) is not None

    def _stored(self, event: RawEvent, mapped: Mapped) -> RawEvent:
        """`event` with its blobs stored and named: the raw mail first,
        without a name, then every attachment in the order of the mail."""
        raw = self._store(mapped.raw, RAW_MAIL, None)
        refs = (
            raw,
            *(self._store(a.content, a.media_type, a.filename) for a in mapped.attachments),
        )
        return replace(event, blobs=refs, payload={**event.payload, "raw": raw.sha256})

    def _store(self, content: bytes, media_type: str, filename: str | None) -> BlobRef:
        # `BytesIO` shares the buffer of a `bytes` it is made from until it
        # is written to, so the content is not copied here.
        stored = store_blob(self.blobs, io.BytesIO(content), recipient=self.recipient)
        return BlobRef(
            sha256=stored.address,
            size=stored.size,
            media_type=media_type,
            filename=_blob_name(filename),
        )

    def flush(self) -> None:
        """Appends the batch, then writes the watermark — never the other
        way round."""
        if self.entries:
            with self.log.snapshot() as conn:
                tip = self.log.tip(conn)
            before = 0 if tip is None else tip.id
            ids = self._append()
            for entry, event_id in zip(self.entries, ids, strict=True):
                # A new event gets an `id` above the tip; a key another
                # writer appended since the lookup comes back with its own.
                if event_id <= before:
                    self.known += 1
                    continue
                self.appended += 1
                if entry.variant_of is not None:
                    self.variants.append((entry.variant_of, event_id))
            self.entries = []
            self.in_batch = {}
        if self.unsaved and self.position is not None:
            with self.log.begin() as conn:
                self.marks.set_watermark(
                    conn, Watermark(self.connector, self.position, self.recorded_at)
                )
            self.unsaved = False

    def _append(self) -> list[int]:
        while True:
            try:
                return append(
                    self.log, [entry.event for entry in self.entries], recorded_at=self.recorded_at
                )
            except ArtifactChanged as changed:
                self._vary(changed)

    def _vary(self, changed: ArtifactChanged) -> None:
        """Turns the event `append` refused into a variant: another writer
        appended its key with another artifact since the lookup. The mails
        attached to it name the variant key from then on. An event that is a
        variant already stops the run with the refusal, for the reason
        `_resolve` gives."""
        index = next(
            i
            for i, entry in enumerate(self.entries)
            if (entry.event.source, entry.event.external_id)
            == (changed.source, changed.external_id)
        )
        entry = self.entries[index]
        if entry.variant_of is not None:
            raise changed
        entry.variant_of = entry.event.external_id
        entry.event = _variant(entry.event, changed)
        for child in self.entries:
            if child.parent == index:
                child.event = replace(
                    child.event,
                    payload={**child.event.payload, "forwarded_in": entry.event.external_id},
                )


def _count(mapped: Mapped) -> int:
    """The events a mail can yield: itself and every mail inside it."""
    return 1 + sum(_count(inner) for inner in mapped.inner)


def _variant(event: RawEvent, changed: ArtifactChanged) -> RawEvent:
    """`event` under its variant key, naming the Message-ID it deviates
    from."""
    return replace(
        event,
        external_id=variant_key(event.external_id, changed.arrived),
        payload={**event.payload, "variant_of": event.external_id},
    )


def _blob_name(filename: str | None) -> str | None:
    """The name of an attachment as a blob reference may carry it: a name
    without a directory. A mail may name an attachment `Angebot 10/2026.pdf`,
    and a reference refuses the `/` — a batch with that reference would be
    refused whole, at every run, so the `/` becomes `_`. An empty name, `.`
    and `..` are no names and become none. The name as the mail wrote it
    stays in the raw mail."""
    if filename is None or filename in ("", ".", ".."):
        return None
    return filename.replace("/", "_")
