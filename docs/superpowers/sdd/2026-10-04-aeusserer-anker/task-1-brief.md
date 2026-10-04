## Task 1: Der Kern — `Anchor`, lesen und schreiben, `examine`

**Files:**
- Modify: `src/previously/contract/types.py`, `src/previously/core/verify.py`, `tests/test_verify.py`, `docs/explanation/hash-chain.md`, `docs/tutorials/record-your-first-event.md` (nur der Testlauf-Block)
- Create: `src/previously/core/anchor.py`, `tests/test_anchor.py`

**Interfaces:**
- Consumes: `LogStore[Conn]` mit `begin`, `read`, `count_events`, `source_keys`, `units_by_event` (unverändert); `InvalidPayload` aus `previously.core.errors`; `Finding(event_id: int, reason: str)` in `core/verify.py`.
- Produces:
  - `previously.contract.types.Anchor(id: int, hash: bytes)` — eingefrorene Dataclass.
  - `previously.core.anchor.parse_anchors(lines: Iterable[str]) -> tuple[Anchor, ...]`, wirft `InvalidPayload`.
  - `previously.core.anchor.format_anchor(anchor: Anchor) -> str` — ohne Zeilenende.
  - `previously.core.verify.Examination(findings: tuple[Finding, ...], tip: Anchor | None)`.
  - `previously.core.verify.examine(storage, *, anchors: Sequence[Anchor] = (), exact: bool = False, batch: int = 1000) -> Examination`.
  - `previously.core.verify.verify(storage, *, batch: int = 1000) -> list[Finding]` — Signatur unverändert.
  - das Label `(external-anchor)=` auf `docs/explanation/hash-chain.md`.

- [ ] **Schritt 1: Einrichtung und Ausgangszahl**

Run: `uv sync --locked --all-extras`
Run: `uv run pytest --collect-only -q -p no:randomly | tail -1`
Erwartet: `232 tests collected`. Weicht die Zahl ab, zähl nach, bevor du weitermachst — alle Zahlen dieses Plans rechnen von 232.

- [ ] **Schritt 2: Die reinen Tests zuerst**

`tests/test_anchor.py`, neu:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading and writing anchor lines ({ref}`external-anchor`), without a database."""

from previously.contract.types import Anchor
from previously.core.anchor import format_anchor
from previously.core.anchor import parse_anchors
from previously.core.errors import InvalidPayload

import pytest
import re


HASH = "ab" * 32


def test_an_anchor_survives_the_round_trip() -> None:
    anchor = Anchor(42, bytes.fromhex(HASH))
    assert format_anchor(anchor) == f"42 {HASH}"
    assert parse_anchors([format_anchor(anchor)]) == (anchor,)


def test_reading_tolerates_comments_blank_lines_case_and_whitespace() -> None:
    """What a file kept by hand looks like: a comment above, a blank line, a
    hash somebody pasted in upper case, a tab instead of a space, a line end
    from another system."""
    lines = [
        "# kept outside the database\n",
        "\n",
        f"1 {HASH}\n",
        f"  2\t{HASH.upper()}\r\n",
        "   ",
    ]
    assert parse_anchors(lines) == (
        Anchor(1, bytes.fromhex(HASH)),
        Anchor(2, bytes.fromhex(HASH)),
    )


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (f"1 {HASH} extra", "expected `<id> <hash>`"),
        ("1", "expected `<id> <hash>`"),
        (f"0 {HASH}", "positive integer"),
        (f"-3 {HASH}", "positive integer"),
        (f"² {HASH}", "positive integer"),
        (f"1 {HASH[:-1]}", "64 hex characters"),
        (f"1 {'zz' * 32}", "not hexadecimal"),
    ],
)
def test_a_broken_line_is_refused_with_its_line_number(line: str, message: str) -> None:
    """A damaged file is not read by halves ({ref}`external-anchor`): a check
    against some of the anchors would look like a check against all of them.
    `²` is review focus 5 — `str.isdigit()` takes it for a number and `int()`
    does not."""
    with pytest.raises(InvalidPayload, match=re.escape(message)) as caught:
        parse_anchors([f"1 {HASH}", line])
    assert "anchor line 2" in str(caught.value)


@pytest.mark.parametrize("lines", [[], ["", "# only a comment", "   "]])
def test_a_file_without_an_anchor_is_refused(lines: list[str]) -> None:
    """`chain intact, 0 anchors hold` would be the weak statement dressed as
    the strong one."""
    with pytest.raises(InvalidPayload, match="holds no anchor"):
        parse_anchors(lines)
```

- [ ] **Schritt 3: Laufen lassen — rot**

Run: `uv run pytest tests/test_anchor.py -q -p no:randomly`
Erwartet: Abbruch beim Sammeln mit `ImportError` (`Anchor` bzw. `previously.core.anchor` gibt es nicht).

- [ ] **Schritt 4: `Anchor` und `core/anchor.py`**

In `src/previously/contract/types.py`, nach `RawEvent`:

```python
@dataclass(frozen=True)
class Anchor:
    """The tip of the chain at one moment: its `id` and its hash
    ({ref}`external-anchor`).

    Input from outside, like `RawEvent`: the line was written down where the
    database's writer cannot reach, and it comes back in to be checked. It
    carries no time and no signature — the place it is kept supplies the
    "when".
    """

    id: int
    hash: bytes
```

`src/previously/core/anchor.py`, neu:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Anchor lines: reading them and writing them ({ref}`external-anchor`).

Pure. No file, no database: the entry point reads the file and hands the
lines in, and a second entry point can hand in lines it got some other way.
"""

from previously.contract.types import Anchor
from previously.core.errors import InvalidPayload
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


def format_anchor(anchor: Anchor) -> str:
    """`<id> <hash>`, the hash in lower-case hex, no line end."""
    return f"{anchor.id} {anchor.hash.hex()}"


def parse_anchors(lines: Iterable[str]) -> tuple[Anchor, ...]:
    """Every anchor in `lines`, or `InvalidPayload` naming the first bad line.

    Blank lines and lines starting with `#` do not count, so that a file kept
    by hand can be annotated. Everything else that is not `<id> <hash>` is an
    error and not a line to skip: a check against half the anchors would look
    like a check against all of them. For the same reason a file without a
    single anchor is an error too.
    """
    anchors: list[Anchor] = []
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 2:
            raise InvalidPayload(
                f"anchor line {number}: expected `<id> <hash>`, got {len(fields)} fields"
            )
        id_text, hash_text = fields
        # `isascii` first: `str.isdigit()` is true for `²`, and `int()` then
        # raises a `ValueError` nobody translated.
        if not (id_text.isascii() and id_text.isdigit() and int(id_text) >= 1):
            raise InvalidPayload(
                f"anchor line {number}: the id has to be a positive integer, got {id_text!r}"
            )
        if len(hash_text) != 64:
            raise InvalidPayload(
                f"anchor line {number}: the hash has to be 64 hex characters, "
                f"got {len(hash_text)}"
            )
        try:
            digest = bytes.fromhex(hash_text)
        except ValueError:
            raise InvalidPayload(f"anchor line {number}: the hash is not hexadecimal") from None
        anchors.append(Anchor(int(id_text), digest))
    if not anchors:
        raise InvalidPayload("the anchor file holds no anchor")
    return tuple(anchors)
```

- [ ] **Schritt 5: Laufen lassen — grün**

Run: `uv run pytest tests/test_anchor.py -q -p no:randomly`
Erwartet: `11 passed` (zwei einfache Tests, sieben und zwei Fälle der beiden parametrisierten).

- [ ] **Schritt 6: Die Tests gegen die Datenbank**

In `tests/test_verify.py` die Importe ergänzen (einzeln, sortiert, wie die Datei es hält):

```python
from previously.contract.types import Anchor
from previously.core.errors import InvalidPayload
from previously.core.verify import examine
from previously.core.verify import Examination
from previously.core.verify import Finding
```

Und am Ende der Datei anfügen:

```python
def _anchor_of(storage: PostgresStorage) -> Anchor:
    """The tip of an intact chain, the way `previously anchor` prints it."""
    examination = examine(storage)
    assert examination.findings == ()
    assert examination.tip is not None
    return examination.tip


def _delete_event(db: Engine, event_id: int) -> None:
    """Forged with plain SQL: nothing in the append path can delete."""
    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = :id"), {"id": event_id})
        c.execute(text("DELETE FROM unit WHERE event_id = :id"), {"id": event_id})
        c.execute(text("DELETE FROM event WHERE id = :id"), {"id": event_id})


@pytest.mark.db
def test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one(db: Engine) -> None:
    """The case stage 1a measured and could not close ({ref}`external-anchor`):
    three events, the tip deleted, and the chain that is left is consistent in
    itself. The first assertion is the control — without an anchor nothing is
    amiss — and the second is what the anchor adds."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b"), _event("c")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    assert anchor.id == 3
    _delete_event(db, 3)

    assert verify(storage) == []
    assert examine(storage, anchors=[anchor]).findings == (
        Finding(3, "anchored event is missing (the log ends at 2)"),
    )


@pytest.mark.db
def test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor(
    db: Engine, truncate_statement: str
) -> None:
    """Rewriting the whole chain is the forgery in its purest form: the result
    is a chain the append path itself produced. Emptied and filled again with
    other events here, which is that."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    with db.begin() as c:
        c.execute(text(truncate_statement))
    append(storage, [_event("x"), _event("y")], recorded_at=NOW)

    assert verify(storage) == []
    assert examine(storage, anchors=[anchor]).findings == (
        Finding(2, "hash does not match the anchor"),
    )


@pytest.mark.db
def test_an_appended_event_passes_contains_and_fails_exact(db: Engine) -> None:
    """An anchor pins a prefix ({ref}`external-anchor`). An event appended
    after it looks like growth — and a forged one is not told apart from a
    legitimate one, which is why it is appended the ordinary way here. Only
    the comparison of the tip with the anchor sees it, and only while nothing
    legitimate was added: the first assertion is that moment of rest."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    assert examine(storage, anchors=[anchor], exact=True).findings == ()

    append(storage, [_event("c")], recorded_at=NOW)
    assert examine(storage, anchors=[anchor]).findings == ()
    assert examine(storage, anchors=[anchor], exact=True).findings == (
        Finding(3, "the log continues past the newest anchor (2)"),
    )


@pytest.mark.db
def test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check(db: Engine) -> None:
    """The limit of every anchor, pinned ({ref}`external-anchor`): it attests
    only what existed when it was taken. Event 3 arrived after the anchor and
    was deleted again; nothing shows that it ever existed. Whoever closes this
    later will see this test turn red."""
    storage = PostgresStorage(db)
    append(storage, [_event("a"), _event("b")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    append(storage, [_event("c")], recorded_at=NOW)
    _delete_event(db, 3)

    assert examine(storage, anchors=[anchor]).findings == ()
    assert examine(storage, anchors=[anchor], exact=True).findings == ()


@pytest.mark.db
def test_exact_without_an_anchor_is_refused(db: Engine) -> None:
    """There is nothing to compare the tip with. Refused in the core and not
    only at the command line, so that a second entry point gets the same
    answer."""
    with pytest.raises(InvalidPayload, match="at least one anchor"):
        examine(PostgresStorage(db), exact=True)


@pytest.mark.db
def test_an_empty_log_has_no_tip_and_misses_every_anchor(db: Engine) -> None:
    """Review focus 4."""
    storage = PostgresStorage(db)
    assert examine(storage) == Examination((), None)
    stray = Anchor(1, b"\x11" * 32)
    assert examine(storage, anchors=[stray]).findings == (
        Finding(1, "anchored event is missing (the log ends at 0)"),
    )


@pytest.mark.db
def test_two_lines_for_one_position_are_both_checked(db: Engine) -> None:
    """The same line twice is harmless; two lines that disagree about one
    position cannot both hold, and the one that does not is reported."""
    storage = PostgresStorage(db)
    append(storage, [_event("a")], recorded_at=NOW)
    anchor = _anchor_of(storage)
    wrong = Anchor(1, b"\x22" * 32)

    assert examine(storage, anchors=[anchor, anchor]).findings == ()
    assert examine(storage, anchors=[anchor, wrong]).findings == (
        Finding(1, "hash does not match the anchor"),
    )


@pytest.mark.db
def test_anchors_are_checked_across_a_batch_boundary(db: Engine) -> None:
    """Review focus 3. Five events in batches of two: the anchor at 3 lies in
    the second batch, the tip in the third."""
    storage = PostgresStorage(db)
    append(storage, [_event(str(n)) for n in range(5)], recorded_at=NOW)
    tip = _anchor_of(storage)
    assert tip.id == 5
    with db.begin() as c:
        third = c.execute(text("SELECT hash FROM event WHERE id = 3")).scalar_one()

    anchors = [Anchor(3, bytes(third)), tip]
    assert examine(storage, anchors=anchors, exact=True, batch=2) == Examination((), tip)
    assert examine(storage, anchors=[Anchor(3, b"\x33" * 32)], batch=2).findings == (
        Finding(3, "hash does not match the anchor"),
    )
```

Run: `uv run pytest tests/test_verify.py -q -p no:randomly`
Erwartet: Abbruch beim Sammeln mit `ImportError` (`examine`).

- [ ] **Schritt 7: `examine`**

In `src/previously/core/verify.py`:

Der Import `from previously.contract.types import Anchor` kommt dazu (zur Laufzeit gebraucht: `examine` baut einen).

Nach der Klasse `Finding`:

```python
@dataclass(frozen=True)
class Examination:
    """What one pass over the chain found, and where the chain ended.

    `tip` is the last row the pass saw, not the answer to a second query
    after it ({ref}`external-anchor`): an anchor printed from it describes
    exactly the chain that was checked. `None` for an empty log.
    """

    findings: tuple[Finding, ...]
    tip: Anchor | None
```

Die Funktion `verify` wird zu `examine`. **Ihr Rumpf bleibt, Kommentare eingeschlossen**; es ändern sich genau diese Stellen:

1. Signatur und Docstring:

```python
def examine[Conn](
    storage: LogStore[Conn],
    *,
    anchors: Sequence[Anchor] = (),
    exact: bool = False,
    batch: int = 1000,
) -> Examination:
    """The one pass: the chain, and the anchors against it.

    Without anchors this is the chain check and nothing else. With anchors it
    also checks that each anchored event exists and carries the anchored hash
    — "contains" — and with `exact` that the tip is the newest anchor
    ({ref}`external-anchor`). The anchors are checked as the pass comes by
    them; there is no second read.

    Returns structured results and no sentences: the command line formats
    them today, and a second entry point formats them its own way.
    """
    if exact and not anchors:
        raise InvalidPayload("exact needs at least one anchor to compare the tip with")
```

2. Vor dem `with storage.begin()`, bei den übrigen lokalen Variablen:

```python
    tip: Anchor | None = None
    # Anchors still waiting for their event, by `id`. A list per `id`, because
    # a file may carry one position twice, and two lines that disagree are
    # both checked.
    pending: dict[int, list[bytes]] = {}
    for anchor in anchors:
        pending.setdefault(anchor.id, []).append(anchor.hash)
```

3. Im Zweig `if not rows:` steht heute `return findings`. Daraus wird `break` — die Zählprüfung davor bleibt, wie sie ist.

4. In der Schleife `for row in rows:`, nach `findings.extend(_check_event(...))`:

```python
                for anchored in pending.pop(row.id, ()):
                    if anchored != row.hash:
                        findings.append(Finding(row.id, "hash does not match the anchor"))
```

und nach `checked += 1`:

```python
                tip = Anchor(row.id, row.hash)
```

5. Nach dem `with`-Block, als Ende der Funktion:

```python
    tip_id = 0 if tip is None else tip.id
    # What is still pending never came by: the log ends before it, or the row
    # is gone from the middle — and then the chain itself has a finding too.
    findings.extend(
        Finding(anchor_id, f"anchored event is missing (the log ends at {tip_id})")
        for anchor_id in sorted(pending)
    )
    if exact:
        newest = max(anchor.id for anchor in anchors)
        if tip_id > newest:
            findings.append(
                Finding(tip_id, f"the log continues past the newest anchor ({newest})")
            )
    return Examination(tuple(findings), tip)
```

Die drei Befundtexte **enden auf festem Text**, nicht auf einer eingesetzten Zahl. Das ist Absicht: der Test, der die Zitate der Reference gegen den Code hält, ordnet einen Satz über sein festes Ende zu (Aufgabe 2). Nicht umformulieren.

Und darunter, neu, die alte Signatur:

```python
def verify[Conn](storage: LogStore[Conn], *, batch: int = 1000) -> list[Finding]:
    """The chain alone, as a list — what every caller asked for before there
    were anchors. `examine` is the pass; this is its findings without any."""
    return list(examine(storage, batch=batch).findings)
```

**Nicht anfassen:** den Kommentar über die eine Transaktion und den einen Schnappschuss. Er ist unter `READ COMMITTED` fraglich, und der Spec führt das als offenen Punkt; der Anker liest nichts Zusätzliches und fügt der Frage nichts hinzu.

- [ ] **Schritt 8: Laufen lassen — grün**

Run: `uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly`
Erwartet: alles grün, darunter die acht neuen in `test_verify.py`.

Run: `uv run pyright`
Erwartet: `0 errors`. Meldet pyright den Typ von `scalar_one()` im Stapeltest, ist `bytes(third)` schon die Antwort; kein `cast` nötig.

Run: `uv run lint-imports`
Erwartet: `Contracts: 4 kept, 0 broken.` — `core.anchor` importiert `contract.types` und `core.errors`, beides erlaubt.

- [ ] **Schritt 9: Die Mutationen messen**

Jede einzeln, mit `uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly`, danach zurücknehmen. Namen der roten Tests und die Schlusszeile in den Bericht.

| Mutation | muss rot werden |
|---|---|
| in `examine` die Zeile `if anchored != row.hash:` durch `if False:` ersetzen | der Test zum Umschreiben, der zu zwei Zeilen für eine Position, der Stapeltest |
| den Block `findings.extend(… anchored event is missing …)` entfernen | der Test zur gelöschten Spitze, der zum leeren Log |
| `if exact:` durch `if False:` ersetzen | der Test zum Anhängen |
| in `parse_anchors` die Prüfung `len(fields) != 2` entfernen | zwei Fälle des parametrisierten Tests |

Kontrolle: ohne Mutation alles grün. Stimmt eine Zeile der Tabelle nicht mit dem überein, was du misst, gilt die Messung — schreib sie in den Bericht, nicht die Tabelle ab.

- [ ] **Schritt 10: `hash-chain.md`**

Vorher `plone-doc-style:author` aufrufen, Quadrant Explanation: Begründung, keine Anweisung, keine Faktentabelle, die in die Reference gehört.

Am Ende des Abschnitts `## What the chain doesn't cover` steht heute:

> An external anchor, such as publishing the tip's hash somewhere the store can't reach, is what closes all three at once, and stage 1a has none.

Der Satz ist zur Hälfte falsch und fällt. An seine Stelle tritt ein Satz, der auf den neuen Abschnitt zeigt. Die Zusage darunter („So the promise, in full: …") bleibt als das, was die Kette **ohne Anker** sagt, und der neue Abschnitt gibt die Zusage mit Anker.

Neuer Abschnitt, direkt danach, mit Label:

```markdown
(external-anchor)=

## The external anchor
```

Muss enthalten, in dieser Reihenfolge:

1. **Was der Anker ist:** `id` und Hash der Spitze zu einem Moment, als eine Zeile aufgeschrieben, wo der, der die Datenbank schreiben kann, nicht hinreicht. Ein Anker in der Datenbank wäre keiner: wer die Kette umschreibt, schriebe ihn mit um.
2. **Was die `id` neben dem Hash leistet.** Der Hash deckt die `id` mit ab — `event_hash` in `src/previously/core/hashing.py` nimmt sie in das gehashte Objekt —, er allein nagelt das Präfix schon fest. Die `id` sagt, **wie lang** das Log mindestens war, und sie ist das, was der Vergleich mit der Spitze braucht. Nicht schreiben, sie sei „die wichtige Hälfte"; das stand so in der 1b-Spec und ist zu grob.
3. **Ein Anker nagelt ein Präfix fest, nicht die Spitze.** Abschneiden unter dem Anker und Umschreiben bis zum Anker fallen auf. Ein Event, das nach dem Anker angefügt wird, sieht aus wie Wachstum, und der nächste Anker schriebe eine Fälschung mit fest.
4. **Zwei Prüfarten**, als Tabelle — vier Fälschungen, zwei Spalten:

   | Forgery | contains | exact |
   |---|---|---|
   | tip deleted, below the newest anchor | seen | seen |
   | chain rewritten up to an anchor | seen | seen |
   | tip deleted, above the newest anchor | not seen | not seen |
   | event appended | not seen | seen, while nothing legitimate was added since |

   Mit einem Satz dazu, dass „exact" darum kein Modus für den laufenden Betrieb ist, sondern für den Moment der Ruhe.
5. **Das Intervall ist die Lücke:** was seit dem jüngsten Anker dazukam, ist nicht verankert.
6. **Die Zusage, im Ganzen**, als drei kursive Zeilen wie die bestehende: *What the log says is unaltered.* / *What it said up to the newest anchor is complete.* / *That nothing was forged onto it since is attested only by comparing the tip with an anchor taken at rest.*
7. **Was offen bleibt:** nur eine Signatur des Schreibers je Event schließt gefälschtes Anhängen außerhalb des Moments der Ruhe; die gibt es nicht.
8. Die Messung, die die 1a-Seite schon zitiert (drei Events, Spitze gelöscht, `chain intact`), und was der Anker daraus macht: `tests/test_verify.py` hält beide Hälften in einem Test. **Die Zahlen aus dem Test ablesen**, nicht aus diesem Plan.

Run: `make -C docs html && make -C docs vale && make -C docs linkcheck`
Erwartet: grün. Vale kennt `anchor` als gewöhnliches Wort; meldet es ein anderes, das du brauchst, nicht selbst ins Vokabular schreiben, sondern Kennungen als Inline-Code setzen und das Wort melden.

- [ ] **Schritt 11: Der Testlauf im Tutorial**

Die Testzahl hat sich geändert, also hält `tests/test_docs_typed_output.py` den Block in `docs/tutorials/record-your-first-event.md` gegen den Baum. Den Testlauf-Block **aus einem echten `uv run pytest`-Lauf neu tippen**, ohne die `rootdir:`-Zeile, ohne Maschinenpfad. Sonst nichts im Tutorial anfassen.

- [ ] **Schritt 12: Alle sechs Tore, Commit**

Erwartet: `pytest` **251 passed** (232 + 19: elf in `test_anchor.py`, acht in `test_verify.py`).

```bash
git status --short
git add src/previously/contract/types.py src/previously/core/anchor.py \
        src/previously/core/verify.py tests/test_anchor.py tests/test_verify.py \
        docs/explanation/hash-chain.md docs/tutorials/record-your-first-event.md
git commit -F - <<'MSG'
feat: examine — the chain, and the anchors against it

An anchor is the tip of the chain at one moment, `<id> <hash>`, written
down where the database's writer cannot reach. `examine` checks anchors in
the same pass as the chain: that each anchored event exists and carries
the anchored hash, and with `exact` that the tip is the newest anchor.
`verify` keeps its signature and calls it.

The case stage 1a measured and could not close — the tip deleted, and
"chain intact" — is a finding against an anchor now. What an anchor does
not close is pinned as well: an event appended after it looks like
growth, and a tip deleted above the newest anchor leaves no trace.

The hash-chain page said an external anchor closes all three forgeries at
once. It closes two, and the page now says which.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

