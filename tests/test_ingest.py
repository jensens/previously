# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The run: mails from a connector into the log and the blob store, against
real PostgreSQL and a real S3 server.

The connector is a list of mails in memory — a test double of the protocol,
not of the database, the store or the clock. It hands out positions as
`uid` and starts after the one its watermark names, the way a mailbox does;
a hook it calls before each mail lets a test look at the watermark or write
to the log in the middle of a run, as a second writer would.
"""

from dataclasses import replace
from datetime import datetime
from datetime import UTC
from previously.contract.types import Fetched
from previously.contract.types import Watermark
from previously.core.append import append
from previously.core.append import MAX_BATCH
from previously.core.blob import fetch_blob
from previously.core.errors import ArtifactChanged
from previously.core.ingest import ingest
from previously.core.ingest import Ingested
from previously.core.mail import map_mail
from previously.core.mail import Mapped
from previously.core.mail import MAX_MESSAGE_ID_BYTES
from previously.core.mail import variant_key
from previously.core.redact import redact_event
from previously.core.sealing import recipient_of
from previously.storage.keys import DirectoryKeys
from previously.storage.postgres import PostgresStorage
from previously.storage.s3 import from_settings
from sqlalchemy import create_engine
from typing import cast
from typing import TYPE_CHECKING

import concurrent.futures
import hashlib
import io
import mailfiles
import multiprocessing
import os
import pathlib
import pytest
import sys


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Sequence
    from pathlib import Path
    from previously.contract.rows import EventRow
    from previously.storage.s3 import S3BlobStore
    from sqlalchemy import Engine


pytestmark = [pytest.mark.db, pytest.mark.s3]

RECORDED_AT = datetime(2026, 10, 6, 12, 0, 0, tzinfo=UTC)
INTERNALDATE = datetime(2026, 10, 6, 9, 0, 1, tzinfo=UTC)
PLAIN_ID = "20261005101500.4711@example.net"
FORWARDED_ID = "fwd-20261008@example.org"
INVOICE_ID = "invoice-2026-10@example.com"
OFFER_PDF = b"%PDF-1.7\n% invented offer, generated for the run\n%%EOF\n"


class ListConnector:
    """A folder in memory: `mails[i]` lies at `uid` `i + 1`.

    `fail_at` is the index at which `fetch` raises instead of handing out a
    mail, as a connection that breaks off would; `hook` is called with the
    index before each mail is handed out.
    """

    def __init__(
        self,
        name: str,
        mails: Sequence[bytes],
        *,
        fail_at: int | None = None,
        hook: Callable[[int], None] | None = None,
    ) -> None:
        self.name = name
        self.mails = list(mails)
        self.fail_at = fail_at
        self.hook = hook

    def fetch(self, since: Watermark | None) -> Iterator[Fetched]:
        start = 0 if since is None else int(since.position["uid"])
        for index in range(start, len(self.mails)):
            if index == self.fail_at:
                raise ConnectionError("the server went away")
            if self.hook is not None:
                self.hook(index)
            uid = str(index + 1)
            yield Fetched(
                raw=self.mails[index],
                position={"uidvalidity": "7", "uid": uid},
                found_in={"folder": self.name, "uidvalidity": "7", "uid": uid},
                internaldate=INTERNALDATE,
            )


def _mail(
    key: str,
    *,
    attachment: tuple[str, bytes] | None = None,
    attached: Sequence[bytes] = (),
    final_crlf: bool = True,
) -> bytes:
    """An invented mail with the Message-ID `<key@example.org>`: plain text
    alone, or a multipart with an attachment and attached mails."""
    lines: list[bytes] = [
        f"From: kunde-{key}@example.org".encode(),
        b"To: office@example.org",
        f"Subject: Anfrage {key} / request {key}".encode(),
        b"Date: Tue, 06 Oct 2026 09:00:00 +0200",
        f"Message-ID: <{key}@example.org>".encode(),
        b"MIME-Version: 1.0",
    ]
    text = [b"Guten Tag,", b"", f"eine erfundene Anfrage, number {key}.".encode()]
    if attachment is None and not attached:
        lines += [b"Content-Type: text/plain; charset=utf-8", b"", *text]
    else:
        lines += [b'Content-Type: multipart/mixed; boundary="part"', b""]
        lines += [b"--part", b"Content-Type: text/plain; charset=utf-8", b"", *text]
        if attachment is not None:
            name, content = attachment
            lines += [
                b"--part",
                b"Content-Type: application/pdf",
                b"Content-Transfer-Encoding: base64",
                f'Content-Disposition: attachment; filename="{name}"'.encode(),
                b"",
                *mailfiles.base64_lines(content),
            ]
        for inner in attached:
            lines += [b"--part", b"Content-Type: message/rfc822", b"", inner]
        lines.append(b"--part--")
    mail = b"\r\n".join(lines)
    return mail + b"\r\n" if final_crlf else mail


def _run(
    storage: PostgresStorage, store: S3BlobStore, connector: ListConnector, age_identity: str
) -> Ingested:
    return ingest(
        storage,
        storage,
        store,
        connector,
        recipient=recipient_of(age_identity),
        recorded_at=RECORDED_AT,
    )


def _events(storage: PostgresStorage) -> dict[str, EventRow]:
    """Every event of the log by its `external_id`."""
    with storage.snapshot() as conn:
        rows = list(storage.read(conn, 1, 100_000))
        keys = storage.source_keys(conn, [row.id for row in rows])
    return {keys[row.id][1]: row for row in rows if row.id in keys}


def _payload(row: EventRow) -> dict[str, object]:
    assert row.payload is not None
    return dict(row.payload)


def _blobs(row: EventRow) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", _payload(row)["blobs"])


def _objects(store: S3BlobStore) -> set[str]:
    found: set[str] = set()
    for page in store.client.get_paginator("list_objects_v2").paginate(Bucket=store.bucket):
        found.update(entry.get("Key", "") for entry in page.get("Contents", []))
    return found


def _watermark(storage: PostgresStorage, connector: str) -> dict[str, str] | None:
    with storage.snapshot() as conn:
        mark = storage.watermark(conn, connector)
    return None if mark is None else dict(mark.position)


def _count(mapped: Mapped) -> int:
    return 1 + sum(_count(inner) for inner in mapped.inner)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact(raw: bytes) -> bytes:
    found = map_mail(raw, internaldate=INTERNALDATE, found_in={}).event.artifact_hash
    assert found is not None
    return found


def test_every_test_mail_is_taken_in_and_a_second_run_appends_nothing(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """All the invented mails of the mapping's tests, broken ones included,
    in one run: no mail stops it, every event names its raw mail first.

    Run again from the same watermark, nothing is fetched. Run again under
    another name — a renamed folder, read from the start — every event is
    known, nothing is appended, and the store gains no object.
    """
    storage = PostgresStorage(db)
    mails = list(mailfiles.MAILS.values())
    events = sum(_count(map_mail(m, internaldate=INTERNALDATE, found_in={})) for m in mails)

    first = _run(storage, blob_store, ListConnector("INBOX", mails), age_identity)

    assert first.appended + first.known == events
    assert first.position == {"uidvalidity": "7", "uid": str(len(mails))}
    log = _events(storage)
    assert len(log) == first.appended
    for row in log.values():
        payload = _payload(row)
        assert payload["raw"] == _blobs(row)[0]["sha256"]
        assert _blobs(row)[0]["media_type"] == "message/rfc822"
        assert _blobs(row)[0]["filename"] is None
    objects = _objects(blob_store)

    again = _run(storage, blob_store, ListConnector("INBOX", mails), age_identity)
    assert again == Ingested(appended=0, known=0, variants=(), position=first.position)

    renamed = _run(storage, blob_store, ListConnector("Kunde Müller", mails), age_identity)
    assert renamed.appended == 0
    assert renamed.known == first.appended + first.known
    assert renamed.variants == ()
    assert len(_events(storage)) == first.appended
    assert _objects(blob_store) == objects


def test_two_copies_in_one_run_are_one_event_and_one_raw_mail(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """The same mail from two mailboxes, with other `Received` lines: the
    second copy is known, and its raw bytes are not stored."""
    storage = PostgresStorage(db)
    copies = [mailfiles.PLAIN, mailfiles.PLAIN_OTHER_TRANSPORT]
    assert copies[0] != copies[1]

    result = _run(storage, blob_store, ListConnector("INBOX", copies), age_identity)

    assert (result.appended, result.known, result.variants) == (1, 1, ())
    assert list(_events(storage)) == [PLAIN_ID]
    assert _objects(blob_store) == {_sha256(mailfiles.PLAIN)}


def test_a_copy_in_a_later_run_stores_no_raw_mail(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    storage = PostgresStorage(db)
    folder = ListConnector("INBOX", [mailfiles.PLAIN])
    _run(storage, blob_store, folder, age_identity)
    folder.mails.append(mailfiles.PLAIN_OTHER_TRANSPORT)

    result = _run(storage, blob_store, folder, age_identity)

    assert (result.appended, result.known) == (0, 1)
    assert _objects(blob_store) == {_sha256(mailfiles.PLAIN)}


@pytest.mark.parametrize("runs", [1, 2], ids=["one run", "two runs"])
def test_another_content_under_a_known_message_id_is_a_variant(
    db: Engine, blob_store: S3BlobStore, age_identity: str, runs: int
) -> None:
    """The same Message-ID with another body, in the batch behind the first
    or in a later run: an event of its own under the variant key, which the
    run names."""
    storage = PostgresStorage(db)
    folder = ListConnector("INBOX", [mailfiles.PLAIN, mailfiles.PLAIN_OTHER_BODY])
    if runs == 2:
        folder.mails.pop()
        _run(storage, blob_store, folder, age_identity)
        folder.mails.append(mailfiles.PLAIN_OTHER_BODY)

    result = _run(storage, blob_store, folder, age_identity)

    key = variant_key(PLAIN_ID, _artifact(mailfiles.PLAIN_OTHER_BODY))
    log = _events(storage)
    assert set(log) == {PLAIN_ID, key}
    assert result.variants == ((PLAIN_ID, log[key].id),)
    assert _payload(log[key])["variant_of"] == PLAIN_ID
    assert "variant_of" not in _payload(log[PLAIN_ID])
    assert _payload(log[key])["raw"] == _sha256(mailfiles.PLAIN_OTHER_BODY)


def test_the_longest_key_a_message_id_gives_fits_the_key_index(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """A Message-ID of `MAX_MESSAGE_ID_BYTES` and another content under it:
    the variant key is the longest key a run builds out of a Message-ID, and
    the key index of the log takes it. The Message-ID is made of digits that
    do not repeat, so that PostgreSQL cannot compress the index entry below
    its length."""
    storage = PostgresStorage(db)
    local = mailfiles.digest_text(MAX_MESSAGE_ID_BYTES - len("@example.org"))
    message_id = f"{local}@example.org"
    first = _mail(local)
    second = _mail(local, attachment=("Angebot.pdf", OFFER_PDF))

    result = _run(storage, blob_store, ListConnector("INBOX", [first, second]), age_identity)

    key = variant_key(message_id, _artifact(second))
    assert len(key.encode("utf-8")) == MAX_MESSAGE_ID_BYTES + 17
    log = _events(storage)
    assert set(log) == {message_id, key}
    assert result.variants == ((message_id, log[key].id),)


def test_an_attachment_in_two_mails_is_one_object(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    storage = PostgresStorage(db)
    first = _mail("offer-1", attachment=("Angebot.pdf", OFFER_PDF))
    second = _mail("offer-2", attachment=("Angebot (Kopie).pdf", OFFER_PDF))

    result = _run(storage, blob_store, ListConnector("INBOX", [first, second]), age_identity)

    assert result.appended == 2
    assert _objects(blob_store) == {_sha256(first), _sha256(second), _sha256(OFFER_PDF)}
    log = _events(storage)
    assert _blobs(log["offer-1@example.org"])[1] == {
        "sha256": _sha256(OFFER_PDF),
        "size": len(OFFER_PDF),
        "media_type": "application/pdf",
        "filename": "Angebot.pdf",
    }
    assert _blobs(log["offer-2@example.org"])[1]["filename"] == "Angebot (Kopie).pdf"


def test_an_attachment_name_with_a_slash_does_not_stop_the_run(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """A blob reference refuses a name with a directory in it, and an empty
    name; a mail may carry either, and `append` would refuse the whole batch
    at every run."""
    storage = PostgresStorage(db)
    mails = [
        _mail("slash", attachment=("Angebot 10/2026.pdf", OFFER_PDF)),
        _mail("empty", attachment=("", OFFER_PDF)),
    ]

    result = _run(storage, blob_store, ListConnector("INBOX", mails), age_identity)

    assert result.appended == 2
    log = _events(storage)
    assert _blobs(log["slash@example.org"])[1]["filename"] == "Angebot 10_2026.pdf"
    assert _blobs(log["empty@example.org"])[1]["filename"] is None


def test_the_raw_mail_comes_back_byte_for_byte(
    db: Engine, blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    storage = PostgresStorage(db)
    _run(storage, blob_store, ListConnector("INBOX", [mailfiles.PLAIN]), age_identity)
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / recipient_of(age_identity)).write_text(age_identity + "\n", encoding="utf-8")

    address = cast("str", _payload(_events(storage)[PLAIN_ID])["raw"])
    sink = io.BytesIO()
    size = fetch_blob(blob_store, DirectoryKeys(str(keys)), address, sink)

    assert sink.getvalue() == mailfiles.PLAIN
    assert size == len(mailfiles.PLAIN)


def test_a_mail_forwarded_as_an_attachment_is_two_events(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """The outer mail names the attached one among its blobs; the attached
    one is an event of its own, whose raw mail is that same blob, pointing
    back with `forwarded_in`."""
    storage = PostgresStorage(db)

    result = _run(storage, blob_store, ListConnector("INBOX", [mailfiles.FORWARDED]), age_identity)

    assert (result.appended, result.known) == (2, 0)
    log = _events(storage)
    outer, inner = log[FORWARDED_ID], log[INVOICE_ID]
    inner_raw = _sha256(mailfiles.FORWARDED_INNER)
    assert _payload(inner)["forwarded_in"] == FORWARDED_ID
    assert "forwarded_in" not in _payload(outer)
    assert _payload(inner)["raw"] == inner_raw
    assert [b["sha256"] for b in _blobs(outer)] == [_sha256(mailfiles.FORWARDED), inner_raw]
    assert [b["sha256"] for b in _blobs(inner)] == [inner_raw, _sha256(mailfiles.INVOICE_PDF)]


def test_the_watermark_follows_the_append(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """The connection breaks off after the third mail. The first mail
    carries `MAX_BATCH - 1` mails inside it and fills a batch of its own, so
    the second and third are in the batch that never gets appended: the
    watermark stands after the first. The next run fetches from there and
    finds the blobs of the second and third stored already."""
    storage = PostgresStorage(db)
    attached = [_mail(f"inner-{i}", final_crlf=False) for i in range(MAX_BATCH - 1)]
    full = _mail("full", attached=attached)
    rest = [mailfiles.PLAIN, mailfiles.REPLY, mailfiles.HTML_ONLY]
    folder = ListConnector("INBOX", [full, *rest], fail_at=3)

    with pytest.raises(ConnectionError):
        _run(storage, blob_store, folder, age_identity)

    assert _watermark(storage, "INBOX") == {"uidvalidity": "7", "uid": "1"}
    assert len(_events(storage)) == MAX_BATCH
    assert {_sha256(mailfiles.PLAIN), _sha256(mailfiles.REPLY)} <= _objects(blob_store)

    folder.fail_at = None
    result = _run(storage, blob_store, folder, age_identity)

    assert (result.appended, result.known) == (3, 0)
    assert result.position == {"uidvalidity": "7", "uid": "4"}
    assert len(_events(storage)) == MAX_BATCH + 3


def test_a_batch_the_log_refuses_leaves_the_watermark(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """Another writer appends the Message-ID of the first mail with another
    artifact, and its variant key with yet another, after the run looked
    both up. `append` refuses the batch, the variant's key too, and the run
    stops with the refusal — before the watermark, which stays unset."""
    storage = PostgresStorage(db)
    other = map_mail(mailfiles.PLAIN_OTHER_BODY, internaldate=INTERNALDATE, found_in={}).event
    taken = variant_key(PLAIN_ID, _artifact(mailfiles.PLAIN))

    def second_writer(index: int) -> None:
        if index == 1:
            append(storage, [other, replace(other, external_id=taken)], recorded_at=RECORDED_AT)

    folder = ListConnector("INBOX", [mailfiles.PLAIN, mailfiles.REPLY], hook=second_writer)

    with pytest.raises(ArtifactChanged, match="is known with another content"):
        _run(storage, blob_store, folder, age_identity)

    assert _watermark(storage, "INBOX") is None
    assert set(_events(storage)) == {PLAIN_ID, taken}


def test_a_key_another_writer_appends_meanwhile_is_a_variant_or_known(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """Between the lookup and the append, a second writer appends the
    forwarding mail with another subject, and the plain mail as it is. The
    run turns the forwarding mail into a variant, which the attached mail
    then names, and counts the plain mail as known."""
    storage = PostgresStorage(db)
    edited = mailfiles.FORWARDED.replace(b"Subject: Fwd:", b"Subject: WG:")
    others = [
        map_mail(edited, internaldate=INTERNALDATE, found_in={}).event,
        map_mail(mailfiles.PLAIN, internaldate=INTERNALDATE, found_in={}).event,
    ]

    def second_writer(index: int) -> None:
        if index == 2:
            append(storage, others, recorded_at=RECORDED_AT)

    mails = [mailfiles.FORWARDED, mailfiles.PLAIN, mailfiles.REPLY]
    result = _run(
        storage, blob_store, ListConnector("INBOX", mails, hook=second_writer), age_identity
    )

    key = variant_key(FORWARDED_ID, _artifact(mailfiles.FORWARDED))
    log = _events(storage)
    assert result.variants == ((FORWARDED_ID, log[key].id),)
    assert (result.appended, result.known) == (3, 1)
    assert _payload(log[key])["variant_of"] == FORWARDED_ID
    assert _payload(log[INVOICE_ID])["forwarded_in"] == key
    # The second writer's event, not the run's: it was mapped without a
    # place it was found in.
    assert _payload(log[PLAIN_ID])["found_in"] == {}


def test_an_erased_mail_is_not_taken_in_again(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """The event is erased and its raw mail deleted from the store. Read
    again from the start, the mail is known, and its raw bytes do not come
    back into the store."""
    storage = PostgresStorage(db)
    _run(storage, blob_store, ListConnector("INBOX", [mailfiles.PLAIN]), age_identity)
    erased = redact_event(
        storage, storage, _events(storage)[PLAIN_ID].id, reason="asked", recorded_at=RECORDED_AT
    )
    assert erased.obsolete_blobs == (_sha256(mailfiles.PLAIN),)
    for address in erased.obsolete_blobs:
        blob_store.delete(address)

    result = _run(storage, blob_store, ListConnector("renamed", [mailfiles.PLAIN]), age_identity)

    assert (result.appended, result.known) == (0, 1)
    assert _objects(blob_store) == set()


def test_more_mails_than_a_batch_holds_are_all_appended(
    db: Engine, blob_store: S3BlobStore, age_identity: str
) -> None:
    """600 mails, one event each: a batch of `MAX_BATCH`, then the rest. The
    connector looks at the watermark before each mail it hands out; it moves
    once the first batch is appended, not before, and stands at the last
    mail after the run."""
    storage = PostgresStorage(db)
    seen: list[str | None] = []

    def look(index: int) -> None:
        del index
        mark = _watermark(storage, "INBOX")
        seen.append(None if mark is None else mark["uid"])

    mails = [_mail(f"bulk-{i}") for i in range(600)]
    result = _run(storage, blob_store, ListConnector("INBOX", mails, hook=look), age_identity)

    assert (result.appended, result.known) == (600, 0)
    assert len(_events(storage)) == 600
    # The batch is appended while the mail at index `MAX_BATCH` is taken,
    # so the connector sees the watermark from the next one on.
    assert seen == [None] * (MAX_BATCH + 1) + [str(MAX_BATCH)] * (600 - MAX_BATCH - 1)
    assert result.position == {"uidvalidity": "7", "uid": "600"}


class FileFolder:
    """A folder whose mails lie in files, each read only when it is handed
    out, the way a mailbox hands out one mail per fetch."""

    def __init__(self, name: str, paths: Sequence[str]) -> None:
        self.name = name
        self.paths = list(paths)

    def fetch(self, since: Watermark | None) -> Iterator[Fetched]:
        del since
        for index, path in enumerate(self.paths):
            uid = str(index + 1)
            yield Fetched(
                raw=pathlib.Path(path).read_bytes(),
                position={"uid": uid},
                found_in={"folder": self.name, "uid": uid},
                internaldate=INTERNALDATE,
            )


def resident_peak() -> int:
    """The peak of the resident memory of this process, in KiB, as the
    kernel keeps it (`VmHWM`)."""
    for line in pathlib.Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    raise AssertionError("/proc/self/status names no VmHWM")


def measure_run(
    url: str, settings: dict[str, str], bucket: str, recipient: str, paths: list[str]
) -> tuple[int, int]:
    """Takes in the mails in `paths`, in an interpreter of its own, and
    returns how many events were appended and by how many KiB the run raised
    the peak of the process.

    A run over one small mail comes first, so that what is loaded and
    connected once is in memory before the measured run starts. Then the
    peak is set back to what is resident, by writing `5` to
    `/proc/self/clear_refs`, and read again after the run.
    """
    engine = create_engine(url)
    store = from_settings(**settings, bucket=bucket)
    storage = PostgresStorage(engine)

    def run(folder: FileFolder) -> Ingested:
        return ingest(storage, storage, store, folder, recipient=recipient, recorded_at=RECORDED_AT)

    try:
        warm = pathlib.Path(paths[0]).with_name("warm.eml")
        warm.write_bytes(mailfiles.PLAIN)
        run(FileFolder("warm", [str(warm)]))
        pathlib.Path("/proc/self/clear_refs").write_text("5", encoding="ascii")
        before = resident_peak()
        result = run(FileFolder("INBOX", paths))
        growth = resident_peak() - before
    finally:
        store.close()
        engine.dispose()
    return result.appended, growth


# Large mails in `test_a_run_holds_one_mail_at_a_time`, each with an
# attachment of 20 MiB, and the bound on the growth of the peak. The test's
# docstring has the measurements the bound lies between.
LARGE_MAILS = 3
BOUND_MIB = 290


@pytest.mark.skipif(sys.platform != "linux", reason="/proc and glibc's malloc are Linux's")
def test_a_run_holds_one_mail_at_a_time(
    db: Engine,
    blob_store: S3BlobStore,
    s3_settings: dict[str, str],
    age_identity: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three mails with an attachment of 20 MiB each — 27 MiB of raw mail in
    base64 — raise the peak of the run by what one of them costs.

    The run is measured in an interpreter started for it, and there with the
    kernel's peak (`VmHWM`) set back just before the run, not with
    `ru_maxrss`: Linux carries `ru_maxrss` over an `exec`, so a child
    started from pytest began at the size of pytest, and measured on
    2026-10-06 the same run read as 75 MiB on its own and as 0 and 1 MiB
    after the other tests of this file — hidden by them, the way
    `tests/test_blob.py` describes for a measurement inside pytest.

    The interpreter runs with glibc's `MALLOC_MMAP_THRESHOLD_` fixed at its
    default of 128 KiB. Left alone, glibc raises the threshold to the size of
    the largest block freed so far, so from the second mail on the blocks of
    a mail come from the heap, which it gives back to the system only in
    part. Measured that day, 1, 3 and 6 such mails raised the peak by 241,
    346 and 383 MiB without the setting, and by 240, 241 and 241 MiB with
    it. What the test holds is that the run lets go of a mail, which the
    fixed threshold shows and the moving one hides.

    The bound lies between two measurements of that day, three mails with
    the threshold fixed, three runs each: the run as it is raised the peak
    by 241 MiB, and the run mutated to keep every mapped mail until it ends
    by 336 MiB.
    """
    paths: list[str] = []
    for number in range(LARGE_MAILS):
        path = tmp_path / f"large-{number}.eml"
        attachment = ("Plan.pdf", os.urandom(20 * 1024 * 1024))
        path.write_bytes(_mail(f"large-{number}", attachment=attachment))
        paths.append(str(path))
    monkeypatch.setenv("MALLOC_MMAP_THRESHOLD_", str(128 * 1024))

    spawn = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(1, mp_context=spawn) as pool:
        appended, growth = pool.submit(
            measure_run,
            db.url.render_as_string(hide_password=False),
            s3_settings,
            blob_store.bucket,
            recipient_of(age_identity),
            paths,
        ).result()

    assert appended == LARGE_MAILS
    assert growth / 1024 < BOUND_MIB, f"the peak grew by {growth / 1024:.0f} MiB"
