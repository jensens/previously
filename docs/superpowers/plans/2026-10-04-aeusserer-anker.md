# Der äußere Anker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `previously anchor` druckt die Spitze einer intakten Kette als Ankerzeile, und `previously verify --anchors DATEI [--exact]` prüft Anker im selben Durchlauf wie die Kette — damit das Log nicht nur „unverändert", sondern bis zum jüngsten Anker auch „vollständig" bezeugt.

**Architecture:** Ein Typ `Anchor` im Vertrag, zwei reine Funktionen in `core/anchor.py` (lesen, schreiben), und in `core/verify.py` eine neue Funktion `examine`, die der eine Durchlauf ist und ein strukturiertes Ergebnis liefert; `verify()` behält seine Signatur und ruft sie. Die Kommandozeile liest die Datei und formatiert, sonst nichts — sie ist der Einstieg, bis es den MCP-Server gibt, und ein zweiter Einstieg ruft dieselben Kernfunktionen. Keine Tabelle, keine Migration, keine Abhängigkeit.

**Tech Stack:** Python 3.14, SQLAlchemy Core, PostgreSQL 17 über testcontainers, pytest, ruff, pyright strict, import-linter, Sphinx/MyST, Vale. Nichts Neues.

**Spec:** `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` — der Plan argumentiert aus ihm; wer ausführt, liest beide.

## Was der Plan am Spec entscheidet

1. **Der Test „jeder Unterparser hat einen Tabelleneintrag" kommt nicht mit** (Spec §10 Punkt 11 überließ es dem Plan). Die ehrliche Lösung ist strukturell — Parser und Tabelle aus einer Folge bauen —, ein Test müsste in private Namen von `argparse` greifen, und `CLAUDE.md` verbietet das. Der Umbau von `main` ist eine eigene Änderung. Der Punkt bleibt offen.
2. **`_quoted_notices` bekommt nebenbei eine lesbare Zusicherung** statt des `IndexError` (Spec §10 Punkt 14, erste Hälfte): die Hilfsfunktion wird in Aufgabe 2 ohnehin verallgemeinert.
3. **Das Tutorial bekommt einen kurzen Schritt zum Anker.** Der Spec verlangt nur, den `verify`-Block neu zu tippen; ein Anker und eine Prüfung dagegen sind zwei Kommandos und zeigen die zentrale Zusage dort, wo ein Neuer sie zuerst sieht.

## Global Constraints

Aus `CLAUDE.md` und dem Spec, für jede Aufgabe verbindlich:

- **Einrichtung des Worktrees:** `uv sync --locked --all-extras`. Ohne `--all-extras` fehlen `pytest`, `ruff` und Sphinx, und `uv run pytest` scheitert mit `Failed to spawn` (gemessen am 2026-10-04).
- **Alle sechs Tore**, namentlich, je einzeln gefahren, mit ungekürzter Schlusszeile im Bericht. Den Block kopieren, nicht aus dem Gedächtnis aufzählen:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- **Englisch** in `src/`, `tests/`, `docs/` außer `docs/superpowers/`, `README.md`, Wurzelkonfiguration. Deutsch nur in Spec, Plan und Ausführungsprotokoll.
- **Trailer `Assisted-By: Claude <Modell> <noreply@anthropic.com>`** mit dem Modell, das die Arbeit getan hat. Niemals `Co-Authored-By:`, niemals „Generated with".
- **Kein `# type: ignore`**, pyright strict; `cast` ist das Mittel. **Kein Mock** für Zeit, Datenbank oder Zufall; Tests gegen echtes PostgreSQL (`db`-Fixture). **Keine neue Suppression**; die Liste in `CLAUDE.md` steht bei fünf.
- **Ein Kommentar ist eine Behauptung.** Jede Zahl in Kommentar, Docstring oder Seite wird am Baum gemessen, nicht aus diesem Plan übernommen. Das gilt ausdrücklich für die Testzahlen hier: sie sind Vorhersagen.
- **Eine Zusage braucht einen Test, von dem gemessen ist, dass er bricht** — mit einer Kontrolle daneben, die gemessen grün bleibt. Die Mutationen stehen in den Schritten; Ergebnis mit Ausgabe in den Bericht.
- **Code zitiert Seiten, nie einen Paragraphen dieses Specs.** Ein Grund steht als `` {ref}`external-anchor` `` oder `` {ref}`hash-chain` `` im Kommentar. Kein `§`. In Programmausgabe steht kein Zitat. (Lehre aus Stufe 1b: zwei Docstrings zitierten den eigenen Spec, weil der Plantext sie so vorgab.)
- **Ein Ruling-Zitat nennt das Datum des Plans:** `ruling X of the 2026-10-04 external-anchor plan`. Der Grund steht daneben.
- **Doku im selben Zweig**, nach `plone-doc-style:author`: ein Quadrant je Seite, ein Satz pro Zeile, Überschriften in Satzschreibung, amerikanisches Englisch, höchstens zwei Admonitions je Seite, keine Überschrift mit `SQL`/`NULL`/`JSON`/`FK`.
- **Getippte Ausgabe ist eine Messung.** Der Testlauf im Tutorial wird aus einem echten `uv run pytest`-Lauf getippt, ohne die `rootdir:`-Zeile, sobald sich die Zahl ändert; `tests/test_docs_typed_output.py` hält `N passed` gegen den Baum.
- **Stagen namentlich**, nie `git add -A`: vorher `git status --short`, nur die eigenen Dateien; alles andere melden.
- **Mutationen im Baum sind erlaubt.** Der Betreuer hat es am 2026-10-04 ausdrücklich freigegeben, nachdem das Berechtigungssystem dem Umsetzer von Aufgabe 1 die erste Mutation als „Security Test Removal" verweigert hatte: eine Zeile ändern, die deckenden Tests fahren, die Datei zurücknehmen. Verweigert das System es einem Umsetzer wieder, sucht er keinen anderen Weg, sondern meldet es, und der Controller misst.
- **Ein Label je Plan nennt seinen Plan** (Ruling T1-b). „Review focus N" und „ruling X" sind je Plan nummeriert; im Baum stehen sie als `review focus N of the 2026-10-04 external-anchor plan`, und der Grund steht im Satz daneben. Ein Docstring, der nur aus dem Label besteht, ist keiner.
- **Betrieb mitdenken** (`CLAUDE.md`, *Operations are part of every design*): Anleitungen zeigen die Routine als einfache Shell-Kommandos, die in kup6s und auf einem Host mit `docker-compose` gleich aussehen. Nichts Hosting-Spezifisches wird gebaut.

**Vertragliche Wortlaute** — exakt so, weil Tests und die Reference sie zitieren:

| Wo | Text |
|---|---|
| Ankerzeile | `<id> <hash>` — ein Leerzeichen, Hash in 64 Hex-Zeichen, klein |
| Befund | `hash does not match the anchor` |
| Befund | `anchored event is missing (the log ends at <tip>)` |
| Befund | `the log continues past the newest anchor (<id>)` |
| `stdout` ohne Anker | `chain intact` |
| `stdout` mit Ankern | `chain intact, 1 anchor holds` / `chain intact, N anchors hold` |
| Zusatz bei `--exact` | `, the tip is the newest anchor` |
| `stderr` ohne Anker | ``no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor` `` |
| `stderr` bei leerem Log | `the log is empty: nothing to anchor` |
| Eingabefehler | `--exact needs --anchors` |

## Review Focus

Fünf Eingaben, die der Spec impliziert und die keine seiner Zusicherungen von selbst prüft — je mit der Aufgabe, die den Test bekommt:

1. **Ankerdatei mit Byte-Order-Mark und Windows-Zeilenenden.** So kommt sie aus einem Editor unter Windows. Erwartet: wird gelesen. → Aufgabe 2.
2. **Ankerdatei, die keine ist:** fehlt, ist ein Verzeichnis, ist kein UTF-8. Erwartet: Rückgabecode 2 und ein Satz, kein Traceback. → Aufgabe 2.
3. **Ein Anker hinter einer Stapelgrenze.** `examine` liest in Stapeln; ein Anker in einem späteren Stapel muss genauso geprüft werden. → Aufgabe 1.
4. **Leeres Log mit Ankern.** Erwartet: jeder Anker fehlt, „the log ends at 0". → Aufgabe 1.
5. **Eine `id` aus Ziffern, die keine ASCII-Ziffern sind** (`²`). `str.isdigit()` hält sie für eine Zahl, `int()` nicht. Erwartet: Eingabefehler mit Zeilennummer, kein `ValueError`. → Aufgabe 1.

> **Nachtrag 2026-10-04, nach der Prüfung der Aufgabe 2 (Ruling T2-a).** Die Punkte 1 und 2 sagen „Ankerdatei" und haben damit die Standardeingabe ausgelassen, die der Spec in §5.1 zum Betriebsweg macht (`--anchors -`, wenn das Kommando im Container läuft und die Datei draußen liegt). Beide gelten für `-` genauso: ein Byte-Order-Mark wird gelesen, und Bytes, die kein UTF-8 sind, sind ein Eingabefehler mit Rückgabecode 2. Was daraus im Plantext der Aufgabe 2 falsch wurde, steht dort im Nachtrag.

---

## Dateistruktur

| Datei | Verantwortung | Aufgabe |
|---|---|---|
| `src/previously/contract/types.py` | bekommt `Anchor` — Eingabe von außen, wie `RawEvent` | 1 |
| `src/previously/core/anchor.py` | **neu.** `parse_anchors`, `format_anchor`. Rein. | 1 |
| `src/previously/core/verify.py` | `Examination`, `examine`; `verify` ruft `examine` | 1 |
| `tests/test_anchor.py` | **neu.** Lesen und Schreiben, ohne Datenbank | 1 |
| `tests/test_verify.py` | die Zusicherungen des Ankers gegen PostgreSQL | 1 |
| `docs/explanation/hash-chain.md` | Abschnitt zum Anker mit Label `external-anchor`; zwei Sätze korrigiert | 1 |
| `src/previously/cli.py` | `_cmd_anchor`, `_cmd_verify`, `_read_anchors`, zwei Parser, ein Tabelleneintrag | 2 |
| `tests/test_cli.py` | die Kommandos Ende-zu-Ende | 2 |
| `tests/test_docs_references.py` | Zitat-Test deckt Befundtexte aus `core/verify.py` und die neuen Hinweise | 2 |
| `docs/reference/cli.md` | `anchor`, `verify`, Rückgabecodes | 2 |
| `pyproject.toml` | die Zahl der `print`-Aufrufe im Kommentar zur `T201`-Ausnahme | 2 |
| `docs/how-to/verify-the-chain.md` | die Routine | 3 |
| `docs/how-to/restore-from-a-backup.md` | zwei Fälle | 3 |
| `README.md` | Kommandozahl, Grenze der Kette, fünfter eingefrorener Bericht | 3 |
| `docs/tutorials/record-your-first-event.md` | Testlauf in jeder Aufgabe; `verify`-Block und Ankerschritt in 3 | 1, 2, 3 |
| `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` | friert ein | 3 |
| `docs/explanation/design-records.md` | fünf Berichte | 3 |

`Tip` in `contract/rows.py` hat dieselben zwei Felder wie `Anchor`. Das ist keine Doppelung, die zusammengelegt gehört: `Tip` ist, was der Speicher jetzt meldet; `Anchor` ist eine Aussage von außen über einen früheren Moment.

---

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

> **Nachtrag 2026-10-04, nach der Umsetzung (Rulings T1-a und T1-b).** Zwei Dinge an diesem Schritt waren im Plan falsch.
>
> *Die Komplexität von `examine` war nicht gemessen.* Mit dem Rumpf, wie er hier steht, meldet `ruff` `C901` (11 gegen die Schwelle 10). Ein neues `# noqa` ist ausgeschlossen, also steht der Teil nach dem Durchlauf — die fehlenden Anker und die `exact`-Prüfung — im Baum in einer eigenen Funktion `_closing_findings(pending, anchors, tip, *, exact)`. Verhalten und Texte sind dieselben. Ein Plan, der eine Funktion um drei Zweige verlängert, misst ihre Komplexität, bevor er sie vorgibt.
>
> *Drei Docstrings der Tests oben zitieren „Review focus N" nackt* — ein Label, das je Plan nummeriert ist; einer besteht nur aus dem Label. Im Baum sagt jeder, was sein Test festnagelt, und nennt den Plan am Label (Commit `c7d8b47`). Dieselbe Klasse wie die `§`-Docstrings der Stufe 1b: was der Plantext vorgibt, landet im Baum. Die Docstrings der Aufgabe 2 sind im Plantext vor dem Dispatch korrigiert.
>
> Die Prüfung fand außerdem zwei Tabellenzellen der Seite ohne Test (die `exact`-Spalte für „Spitze gelöscht" und „umgeschrieben") und eine Grenze ohne sichtbare Kontrolle; beide Tests tragen jetzt je eine Zusicherung mehr, als hier steht. Die Testzahl bleibt 251.

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

## Task 2: Die Kommandozeile — `anchor`, `verify --anchors`, und die Reference

**Files:**
- Modify: `src/previously/cli.py`, `tests/test_cli.py`, `tests/test_docs_references.py`, `docs/reference/cli.md`, `pyproject.toml`, `docs/tutorials/record-your-first-event.md` (nur der Testlauf-Block)

**Interfaces:**
- Consumes (aus Aufgabe 1, am Baum prüfen): `Anchor`, `parse_anchors`, `format_anchor`, `examine`, `Examination`; aus `cli.py` bestehend: `_storage()`, `_plural(n, noun)`, `main`, die Dispatch-Tabelle `commands`, `InvalidPayload`, `PreviouslyError`.
- Produces: das Kommando `anchor`; `verify` mit `--anchors FILE` und `--exact`; in `docs/reference/cli.md` die Abschnitte `## \`verify\`` und `## \`anchor\`` mit den Sätzen, an denen der Zitat-Test sie findet.

- [ ] **Schritt 1: Die Tests zuerst**

In `tests/test_cli.py` am Dateikopf ergänzen: `import io`, `import re`, `import sys` (bei `import pytest`, sortiert).

Am Ende der Datei anfügen. `_setup` und `_append` gibt es dort schon; nicht neu schreiben.

```python
_HINT = (
    "no anchor given: verify attests that the log is unchanged, "
    "not that it is complete; see `previously anchor`\n"
)


@pytest.mark.db
def test_verify_without_an_anchor_says_what_it_does_not_attest(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standard output stays the one line scripts read; the limit of the
    statement goes to standard error ({ref}`external-anchor`). Beside a
    finding the hint would be noise, so the second half has none."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()

    assert main(["verify"]) == 0
    out, err = capsys.readouterr()
    assert out == "chain intact\n"
    assert err == _HINT

    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\x00" * 32})
    assert main(["verify"]) == 1
    out, err = capsys.readouterr()
    assert out.startswith("FINDING 1: ")
    assert err == ""


@pytest.mark.db
def test_anchor_prints_the_tip_and_verify_holds_it(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The routine end to end: anchor, check, grow, check again."""
    _setup(db, monkeypatch)
    _append("email", "m1", "one", "2026-10-01T09:00:00Z")
    _append("email", "m2", "two", "2026-10-02T09:00:00Z")
    capsys.readouterr()

    assert main(["anchor"]) == 0
    line, err = capsys.readouterr()
    assert re.fullmatch(r"2 [0-9a-f]{64}\n", line)
    assert err == ""
    assert main(["show", "2"]) == 0
    assert f"hash={line.split()[1]}\n" in capsys.readouterr().out  # the tip, not some hash

    anchors = tmp_path / "anchors.txt"
    anchors.write_text(line, encoding="utf-8")
    assert main(["verify", "--anchors", str(anchors)]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("chain intact, 1 anchor holds\n", "")
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("chain intact, 1 anchor holds, the tip is the newest anchor\n", "")

    _append("email", "m3", "three", "2026-10-03T09:00:00Z")
    capsys.readouterr()
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 1
    assert capsys.readouterr().out == "FINDING 3: the log continues past the newest anchor (2)\n"

    assert main(["anchor"]) == 0
    with anchors.open("a", encoding="utf-8") as handle:
        handle.write(capsys.readouterr().out)
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 0
    expected = "chain intact, 2 anchors hold, the tip is the newest anchor\n"
    assert capsys.readouterr().out == expected


@pytest.mark.db
def test_verify_reports_a_deleted_tip_against_the_anchor(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The case stage 1a measured, at the surface a cron job reads: without
    an anchor exit code 0, with one exit code 1 and the finding."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    for n in (1, 2, 3):
        _append("email", f"m{n}", f"text {n}", f"2026-10-0{n}T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    anchors = tmp_path / "anchors.txt"
    anchors.write_text(capsys.readouterr().out, encoding="utf-8")

    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 3"))
        c.execute(text("DELETE FROM unit WHERE event_id = 3"))
        c.execute(text("DELETE FROM event WHERE id = 3"))

    assert main(["verify"]) == 0
    assert capsys.readouterr().out == "chain intact\n"
    assert main(["verify", "--anchors", str(anchors)]) == 1
    out, err = capsys.readouterr()
    assert out == "FINDING 3: anchored event is missing (the log ends at 2)\n"
    assert err == ""


@pytest.mark.db
@pytest.mark.parametrize(
    ("content", "fragment"),
    [
        (b"1 zz\n", "anchor line 1"),
        (b"", "holds no anchor"),
        (b"\xff\xfe\x00junk", "not UTF-8"),
        (None, "cannot read the anchor file"),
    ],
)
def test_a_broken_anchor_file_is_an_input_error(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    content: bytes | None,
    fragment: str,
) -> None:
    """A file that is no anchor file is an input error: exit code 2 and one
    sentence, never a traceback, and nothing on standard output — no half
    result. `None` is the file that does not exist. (Review focus 2 of the
    2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    anchors = tmp_path / "anchors.txt"
    if content is not None:
        anchors.write_bytes(content)

    assert main(["verify", "--anchors", str(anchors)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: ")
    assert fragment in err


@pytest.mark.db
def test_a_directory_as_anchor_file_is_an_input_error(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """A directory is the third shape of "not a file", after the one that is
    missing and the one that is not text: same exit code, same kind of
    sentence. (Review focus 2 of the 2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    assert main(["verify", "--anchors", str(tmp_path)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: cannot read the anchor file")


def test_exact_without_anchors_is_an_input_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Refused before the database is even asked for, which is why this test
    needs none."""
    assert main(["verify", "--exact"]) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "Error: --exact needs --anchors\n")


@pytest.mark.db
def test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An anchor on a broken chain would certify the break
    ({ref}`external-anchor`)."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    assert main(["anchor"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "the log is empty: nothing to anchor\n")

    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\x00" * 32})
    assert main(["anchor"]) == 1
    out, err = capsys.readouterr()
    assert out.startswith("FINDING 1: ")
    assert not re.search(r"^1 [0-9a-f]{64}$", out, flags=re.MULTILINE)


@pytest.mark.db
def test_verify_reads_the_anchors_from_standard_input(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`-` is not a convenience: it is how a host with docker-compose runs
    the check without mounting the file into the container
    ({ref}`external-anchor`)."""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    line = capsys.readouterr().out

    monkeypatch.setattr(sys, "stdin", io.StringIO(line))
    assert main(["verify", "--anchors", "-"]) == 0
    assert capsys.readouterr().out == "chain intact, 1 anchor holds\n"


@pytest.mark.db
def test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """A byte order mark and Windows line ends are what an editor on another
    system leaves behind, and the file is read all the same. (Review focus 1
    of the 2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    line = capsys.readouterr().out.strip()

    anchors = tmp_path / "anchors.txt"
    anchors.write_bytes(b"\xef\xbb\xbf# kept outside\r\n" + line.encode() + b"\r\n")
    assert main(["verify", "--anchors", str(anchors)]) == 0
    assert capsys.readouterr().out == "chain intact, 1 anchor holds\n"
```

`pathlib` für die Annotation `tmp_path: pathlib.Path`: unter `TYPE_CHECKING` importieren, wenn `ruff` es so verlangt; die Datei hat bisher keinen solchen Block, dann anlegen wie in `tests/conftest.py`.

- [ ] **Schritt 2: Laufen lassen — rot**

Run: `uv run pytest tests/test_cli.py -q -p no:randomly -k "anchor or exact"`
Erwartet: rot — `argparse` kennt `anchor`, `--anchors` und `--exact` nicht (`SystemExit: 2`), und `verify` druckt den Hinweis nicht.

- [ ] **Schritt 3: Die Kommandos**

In `src/previously/cli.py`:

Importe: `from previously.core.anchor import format_anchor`, `from previously.core.anchor import parse_anchors`, `from previously.core.verify import examine` kommen dazu; `from previously.core.verify import verify` fällt, wenn nichts mehr es braucht. `Anchor` aus `previously.contract.types` nur für die Annotation — unter `TYPE_CHECKING`, wenn `ruff` (`TC`) es so will.

Nach `_storage`:

```python
def _read_anchors(source: str) -> tuple[Anchor, ...]:
    """The anchor file, or standard input for `-` ({ref}`external-anchor`).

    Reading is all this function does; what a line has to look like is
    `parse_anchors` in `core`, so that a second entry point reads the same
    format without this file.

    `utf-8-sig`, so that a file an editor saved with a byte order mark reads
    like one without. A file that is no file — missing, a directory, not
    text — becomes `InvalidPayload` and with it exit code 2: one sentence,
    not a stack trace.
    """
    if source == "-":
        return parse_anchors(sys.stdin)
    try:
        with open(source, encoding="utf-8-sig") as handle:
            return parse_anchors(handle)
    except OSError as error:
        raise InvalidPayload(
            f"cannot read the anchor file {source!r}: {error.strerror}"
        ) from error
    except UnicodeDecodeError as error:
        raise InvalidPayload(f"the anchor file {source!r} is not UTF-8 text") from error
```

> **Nachtrag 2026-10-04, nach der Prüfung (Ruling T2-a).** Dieser Rumpf ist falsch, und der Fehler ist einer des Plans: der Zweig für `-` steht **vor** dem `try` und liest `sys.stdin`, wie das Terminal es dekodiert. An der Kommandozeile gemessen: Bytes, die kein UTF-8 sind, enden auf `--anchors -` in einem Traceback mit Rückgabecode 1 — und 1 heißt für den Cron-Job, der das Kommando fährt, „Befund"; ein Byte-Order-Mark wird verweigert. Ich hatte vor dem Dispatch die Komplexität dieses Rumpfs gemessen, nicht sein Verhalten auf der Standardeingabe.
>
> Im Baum (Commit `81992f9`) liest die Funktion beide Quellen als Bytes und dekodiert an **einer** Stelle, in **einem** `try`: `sys.stdin.buffer.read()` oder `open(source, "rb")`, dann `raw.decode("utf-8-sig")`, die Zeilen über `io.StringIO(text, newline=None)` — das bricht wie eine Datei im Textmodus und nicht, wie `str.splitlines()`, auch an U+2028. Die Meldungen für eine Datei sind wortgleich geblieben; für `-` heißen sie `cannot read standard input: …` und `standard input is not UTF-8 text`. Zwei Tests kamen dazu (Byte-Order-Mark und Windows-Zeilenenden auf der Standardeingabe; Bytes, die kein UTF-8 sind), und der bestehende Test für `-` reicht die Zeile jetzt als Bytes, wie eine Pipe es tut — mit `io.StringIO` lief die Dekodierung, um die es geht, nie.
>
> Die Lehre ist dieselbe wie bei `examine` in Aufgabe 1, eine Stufe weiter: **Code im Plan wird nicht nur gemessen, sondern auf jedem Weg, den er hat, ausgeführt.** Ein Zweig, der vor dem `try` zurückkehrt, ist ein eigener Weg.

`_cmd_verify` wird:

```python
def _cmd_verify(args: argparse.Namespace) -> int:
    # Refused before the database is asked for: there is nothing `--exact`
    # could compare the tip with.
    if args.exact and args.anchors is None:
        raise InvalidPayload("--exact needs --anchors")
    anchors = () if args.anchors is None else _read_anchors(args.anchors)
    examination = examine(_storage(), anchors=anchors, exact=args.exact)
    for finding in examination.findings:
        print(f"FINDING {finding.event_id}: {finding.reason}")
    if examination.findings:
        return 1
    if not anchors:
        # Standard output stays the one line scripts read. The limit of the
        # statement goes to standard error, the way `chronicle` reports its
        # lag ({ref}`external-anchor`): without an anchor the chain attests
        # "unchanged" and nothing about "complete". Only on an intact chain —
        # beside findings the sentence would be noise.
        print("chain intact")
        print(
            "no anchor given: verify attests that the log is unchanged, "
            "not that it is complete; see `previously anchor`",
            file=sys.stderr,
        )
        return 0
    count = len(anchors)
    held = f"{_plural(count, 'anchor')} {'holds' if count == 1 else 'hold'}"
    tail = ", the tip is the newest anchor" if args.exact else ""
    print(f"chain intact, {held}{tail}")
    return 0
```

Der Hinweis steht **als Literal im Aufruf**, nicht in einer Konstanten: der Zitat-Test liest das erste Argument von `print(..., file=sys.stderr)` aus dem Quelltext, und einen Namen sähe er nicht.

Danach, neu:

```python
def _cmd_anchor(_args: argparse.Namespace) -> int:
    """Prints the tip of an intact chain as an anchor line
    ({ref}`external-anchor`).

    The tip is the last row the pass saw, so the line describes exactly the
    chain that was checked. On a finding there is no line: an anchor on a
    broken chain would certify the break.
    """
    examination = examine(_storage())
    for finding in examination.findings:
        print(f"FINDING {finding.event_id}: {finding.reason}")
    if examination.findings:
        return 1
    if examination.tip is None:
        print("the log is empty: nothing to anchor", file=sys.stderr)
        return 0
    print(format_anchor(examination.tip))
    return 0
```

In `main`, der Parser für `verify` wird ausgebaut und `anchor` kommt dazu:

```python
    p_verify = sub.add_parser("verify", help="check the chain, and anchors if given")
    p_verify.add_argument(
        "--anchors", metavar="FILE", help="anchor lines to check against; - reads standard input"
    )
    p_verify.add_argument(
        "--exact", action="store_true", help="the tip has to be the newest anchor"
    )

    sub.add_parser("anchor", help="print the tip of an intact chain as an anchor line")
```

Und in der Tabelle `commands` der Eintrag `"anchor": _cmd_anchor`, nach `"verify"`.

**Zwei Kommentare in `main` nennen eine Zahl, die jetzt falsch wird**, und beide sind zu messen, nicht umzuschreiben:

- „with these seven commands" im Kommentar über die Tabelle. Er trägt eine gemessene Reihe (Kette mit sieben Kommandos 9, mit acht 10, mit neun 11; `C901` feuert strikt oberhalb der Schwelle 10). Heute sind es acht: die Kette stünde bei 10 und käme noch durch, die Tabelle steht weiter bei 2. Die Tabelle mit `uv run ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py` nachmessen und den Kommentar so nachziehen, dass er für acht Kommandos stimmt und sagt, was gemessen und was aus der Reihe abgelesen ist.
- „one of the seven keys" im Kommentar unter der Tabelle.

- [ ] **Schritt 4: Laufen lassen — grün**

Run: `uv run pytest tests/test_cli.py -q -p no:randomly`
Erwartet: alles grün, die bestehenden eingeschlossen. `test_append_log_and_verify_together` und `test_verify_prints_the_finding_and_returns_1` rufen `main(["verify"])` und lesen nur `stdout` und den Rückgabecode; sie bleiben grün. Wird einer rot, liest er `stderr` — dann sag es im Bericht, statt ihn anzupassen.

Run: `uv run ruff check .`
Erwartet: `All checks passed!` — insbesondere kein `C901` auf `main` oder `_cmd_verify`.

- [ ] **Schritt 5: Die Zahl der `print`-Aufrufe**

Run: `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | tail -1`

`pyproject.toml` (Kommentar zur `T201`-Ausnahme) und der Docstring in `tests/test_docs_references.py` nennen heute „nineteen". Beide auf die **gemessene** Zahl ziehen, mit Datum; in `pyproject.toml` die Geschichte um eine Zeile fortschreiben, nicht ersetzen.

- [ ] **Schritt 6: `cli.md`**

Quadrant Reference: Tatsachen, keine Begründung; der Grund steht auf `` {ref}`external-anchor` ``.

- **Einleitung:** acht Unterkommandos, `anchor` nach `verify` genannt.
- **Rückgabecodes:** die Zeile für `verify` — 0 „The chain has no finding, and every anchor holds.", 1 „The chain or an anchor has at least one finding.", 2 „The input was invalid, or storage raised an error." Eine neue Zeile für `anchor` — 0 „The anchor line was printed, or the log is empty.", 1 „The chain has at least one finding.", 2 „Storage raised an error."
- **`## \`verify\``** neu geschrieben. „It takes no arguments" fällt. Eine Argumenttabelle (`--anchors FILE`, `--exact`), das Format einer Ankerzeile und der Datei (Leerzeilen, `#`, sonst Eingabefehler; eine Datei ohne Anker ebenso), was „contains" und `--exact` prüfen, die drei Erfolgsmeldungen. Und zwei Blöcke, **mit genau diesen Einleitungssätzen**, weil der Test sie daran findet:

  ````markdown
  Three findings come from the anchors:

  ```text
  FINDING 42: hash does not match the anchor
  FINDING 42: anchored event is missing (the log ends at 40)
  FINDING 43: the log continues past the newest anchor (42)
  ```
  ````

  ````markdown
  Without anchors, one notice goes to standard error, and the exit code stays 0:

  ```text
  no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
  ```
  ````

- **`## \`anchor\``**, neu, nach `verify`: keine Argumente; eine Zeile `<id> <hash>` für die Spitze einer intakten Kette; bei einem Befund die `FINDING`-Zeilen und keine Ankerzeile. Und:

  ````markdown
  On an empty log, one notice goes to standard error, and nothing goes to standard output:

  ```text
  the log is empty: nothing to anchor
  ```
  ````

Die Zahlen in den Beispielzeilen (42, 40, 43) sind Platzhalter in einem Format, kein getippter Lauf; der Block für `chronicle` auf derselben Seite hält es genauso.

- [ ] **Schritt 7: Der Zitat-Test**

In `tests/test_docs_references.py`:

`_quoted_notices` wird verallgemeinert — und bekommt die lesbare Zusicherung, die ihm fehlte (bisher lief ein verschwundener Einleitungssatz in einen `IndexError`):

```python
def _quoted_block(page: str, after: str) -> list[str]:
    """The lines of the first `text` block after the sentence `after`."""
    assert after in page, f"cli.md no longer carries the sentence {after!r}"
    rest = page.split(after, 1)[1]
    block = rest.split("```text", 1)[1].split("```", 1)[0]
    return [line for line in block.splitlines() if line.strip()]
```

Dazu, neu:

```python
def _finding_patterns(path: pathlib.Path) -> list[list[str]]:
    """The static parts of every reason a module hands to `Finding(...)`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        parts
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Finding"
        and len(node.args) == 2
        and (parts := _static_parts(node.args[1]))
    ]
```

In `test_the_reference_quotes_what_the_code_actually_prints` tritt an die Stelle des bisherigen Blocks, der `_quoted_notices` rief:

```python
    page = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    patterns = _message_patterns(ROOT / "src" / "previously" / "cli.py")
    for after, expected in (
        ("Two notices go to standard error", 2),
        ("Without anchors, one notice goes to standard error", 1),
        ("On an empty log, one notice goes to standard error", 1),
    ):
        notices = _quoted_block(page, after)
        assert len(notices) == expected, f"{after!r}: {notices}"
        for notice in notices:
            assert any(_is_the_same_sentence(parts, notice) for parts in patterns), (
                f"cli.md quotes {notice!r} on standard error and no message in cli.py "
                "says that. Either the code's wording changed, or the page's did."
            )

    reasons = _finding_patterns(ROOT / "src" / "previously" / "core" / "verify.py")
    findings = _quoted_block(page, "Three findings come from the anchors")
    assert len(findings) == 3, findings
    for line in findings:
        reason = line.split(": ", 1)[1]
        assert any(_is_the_same_sentence(parts, reason) for parts in reasons), (
            f"cli.md quotes the finding {reason!r} and core/verify.py produces no such "
            "reason. Either the code's wording changed, or the page's did."
        )
```

Der Docstring des Tests zählt, was er hält; ihn nachziehen und die Zahlen darin am Test ablesen.

**Die Mutationen**, je einzeln, mit `uv run pytest tests/test_docs_references.py -q -p no:randomly`, danach zurücknehmen:

| Mutation | muss rot werden |
|---|---|
| auf `cli.md` im Hinweis `unchanged` durch `unaltered` ersetzen | der Zitat-Test, mit dem Satz in der Meldung |
| auf `cli.md` im zweiten Befund `missing` durch `absent` ersetzen | der Zitat-Test |
| in `core/verify.py` `"hash does not match the anchor"` durch `"hash differs from the anchor"` ersetzen | der Zitat-Test **und** Tests in `test_verify.py` |
| auf `cli.md` den Satz `Three findings come from the anchors` umformulieren | der Zitat-Test, mit der lesbaren Meldung statt eines `IndexError` |

Kontrolle: ohne Mutation grün; und die Zahlen im `chronicle`-Block ändern (`12 events` → `7 events`) lässt ihn grün — der Test hält den Wortlaut, nicht die eingesetzten Werte.

- [ ] **Schritt 8: Der Testlauf im Tutorial**

Wie in Aufgabe 1: den Testlauf-Block aus einem echten Lauf neu tippen. Den `verify`-Block darüber **nicht** anfassen — er zeigt jetzt eine Zeile zu wenig, und Aufgabe 3 tippt die ganze Sitzung neu.

- [ ] **Schritt 9: Alle sechs Tore, Commit**

Erwartet: `pytest` **263 passed** (251 + 12: acht einfache Tests und vier Fälle des parametrisierten).

> **Nachtrag 2026-10-04.** Gemessen 263 nach dem ersten Commit der Aufgabe (`2637c8e`) und **265** nach ihrer Fixrunde (`81992f9`), die zwei Tests für die Standardeingabe brachte. Die Fixrunde hält außerdem das Präfix `FINDING <id>` der zitierten Befundzeilen fest (Ruling T2-c), das Schritt 7 mit `line.split(": ", 1)[1]` ungeprüft weggeworfen hatte.

```bash
git status --short
git add src/previously/cli.py tests/test_cli.py tests/test_docs_references.py \
        docs/reference/cli.md pyproject.toml docs/tutorials/record-your-first-event.md
git commit -F - <<'MSG'
feat: anchor, and verify --anchors

`previously anchor` prints the tip of an intact chain as `<id> <hash>`;
on a finding it prints the findings and no line, because an anchor on a
broken chain would certify the break. `previously verify --anchors FILE`
checks every line in the pass that checks the chain, `--exact` also
requires the tip to be the newest anchor, and `-` reads standard input —
which is how a host with docker-compose runs the check without mounting
the file.

Without anchors standard output stays `chain intact` and the exit code
stays 0. One sentence on standard error says what that attests and what
it does not.

The reference quotes the three anchor findings and the two notices, and
the test that holds its quotations against the code now reads the reasons
`core/verify.py` hands to `Finding` as well. A sentence that vanishes from
the page fails with a readable message instead of an IndexError.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Task 3: Die Anleitungen, das README, das Tutorial — und der Spec friert ein

**Files:**
- Modify: `docs/how-to/verify-the-chain.md`, `docs/how-to/restore-from-a-backup.md`, `README.md`, `docs/tutorials/record-your-first-event.md`, `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`, `docs/explanation/design-records.md`

**Interfaces:**
- Consumes: die Kommandos und ihre Ausgaben aus Aufgabe 2, am Baum und an `docs/reference/cli.md` abgelesen; das Label `external-anchor` aus Aufgabe 1.
- Produces: nichts, worauf Code sich stützt.

Vorher `plone-doc-style:author` aufrufen, je Quadrant: How-to ist Handlung ohne Erklärung, mit Verweisen statt Gründen; Tutorial ist ein garantierter Weg in der ersten Person Plural.

- [ ] **Schritt 1: `verify-the-chain.md`**

- „It takes no arguments" fällt.
- Der Schlussabsatz („It doesn't prove that the chain is complete …") stimmt nur noch ohne Anker. Er wird zu dem, was Rückgabecode 0 **ohne** Anker heißt, mit Verweis auf den neuen Abschnitt.
- Neuer Abschnitt `## Anchor the chain, and check against the anchors`: die Routine als zwei Kommandos, erst prüfen, dann ankern:

  ```shell
  previously verify --anchors anchors.txt && previously anchor >> anchors.txt
  ```

  Dazu: beim ersten Mal gibt es noch keine Datei, dann nur `previously anchor > anchors.txt`; die Datei gehört an einen Ort, den nicht schreiben kann, wer die Datenbank schreiben kann; `-` liest die Datei von der Standardeingabe, wenn das Kommando in einem Container läuft und die Datei draußen liegt; ein Rückgabecode ungleich 0 ist ein Alarm. **Hosting-neutral**: keine Kubernetes- und keine Compose-Syntax, nur die zwei Kommandos — sie sind in beiden gleich.
- Für das Warum ein Verweis: `` {ref}`external-anchor` ``.

- [ ] **Schritt 2: `restore-from-a-backup.md`**

Der Satz „If `previously verify` exits `0`, the restore is trustworthy" ist zu stark: ein Restore aus einem älteren Stand ist eine kürzere, in sich stimmige Kette und besteht. Die Anleitung führt künftig zwei Fälle:

- **Restore bis zum letzten Stand** (Base-Backup plus Write-Ahead-Log): `previously verify --anchors anchors.txt`. Rückgabecode 0 heißt: bis zum jüngsten Anker ist nichts verloren und nichts umgeschrieben. Was nach dem jüngsten Anker angefügt wurde, bezeugt die Prüfung nicht.
- **Restore auf einen festen Punkt, der mit einem Anker zusammenfällt:** zusätzlich `--exact`. Rückgabecode 0 heißt: die Spitze ist genau der Anker.

Und was Rückgabecode 0 **ohne** Anker bedeutet: die Kette ist in sich stimmig, mehr nicht. Die bestehenden Hinweise (Passphrase, „never rehearsed") bleiben; höchstens zwei Admonitions auf der Seite.

- [ ] **Schritt 3: `README.md`**

- „the seven commands …" → acht, `anchor` genannt.
- Der Absatz über die Grenze („a hash chain without an **outer anchor** …") stimmt nicht mehr als Beschreibung eines Mangels: es gibt den Anker jetzt. Neu fassen — was die Kette allein bezeugt, was ein Anker dazugibt, und dass gefälschtes Anhängen nur im Vergleich mit einem in Ruhe genommenen Anker auffällt. Nicht mehr zusagen, als die Tabelle auf `hash-chain.md` hält.
- „What it does not do" bleibt, wie es ist.

- [ ] **Schritt 4: Das Tutorial — die Sitzung neu tippen**

`verify` druckt jetzt eine zweite Zeile, und ein Terminal zeigt `stderr` neben `stdout`. Der `verify`-Block im Tutorial wird **aus einem echten Lauf** neu getippt, gegen den Container, den das Tutorial selbst aufsetzt (seinen eigenen Schritten folgen, frischer Container), und der Satz danach („It found nothing wrong, so it printed exactly that one line.") stimmt nicht mehr — neu fassen, mit einem „Notice that …" zur zweiten Zeile.

Danach ein kurzer neuer Abschnitt `## Pin the tip`, zwei Kommandos, getippt aus demselben Lauf:

```console
$ uv run previously anchor > anchors.txt
$ uv run previously verify --anchors anchors.txt
```

mit ihrer echten Ausgabe und einem „Notice that …": die erste Zeile ist jetzt eine andere, und der Hinweis ist weg. Keine Erklärung, was ein Anker schließt — dafür ein Verweis unter *Next steps*.

Weil die anderen Blöcke derselben Sitzung denselben Zeitstempel und denselben Hash zeigen: **die ganze Sitzung aus einem Lauf**, wie Aufgabe 8 der Stufe 1b es gemacht hat, damit die Seite sich nicht selbst widerspricht. Der `uv sync`-Block bleibt, wenn ein neuer Lauf einen Maschinenpfad druckte; die Seite sagt, dass keine Ausgabe ein Verzeichnis nennt.

Dann der Testlauf-Block, **zuletzt**, aus einem echten `uv run pytest`-Lauf. Die Zahl **messen**: `uv run pytest --collect-only -q -p no:randomly | tail -1`.

Das Rohprotokoll des Laufs, aus dem die Blöcke stammen, gehört in den Bericht — der Prüfer vergleicht dagegen.

- [ ] **Schritt 5: Der Spec friert ein**

`docs/superpowers/specs/2026-10-04-aeusserer-anker.md`: der Kopf wie bei den vier anderen, wörtlich aus `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md` (Zeilen 3 bis 14) kopiert, das Datum ist das des Commits. „Status: Entwurf, zur Abnahme" → „Status: eingefroren". Der Einleitungsabsatz, der das Einfrieren ankündigt, fällt bis auf den Satz, dass der Spec klein ist und eine Zusage einlöst.

§10 „Was offen bleibt": die Einleitung in die Vergangenheit setzen — der Abschnitt war gepflegt, solange der Spec lebte, und gibt seine fünfzehn Punkte an den Spec weiter, der ihm folgt. **Die Zahl zählen**, nicht aus diesem Satz übernehmen.

- [ ] **Schritt 6: `design-records.md` und die Tabelle im README**

`docs/explanation/design-records.md`: fünf Dokumente statt vier; der Anker-Spec dort, wo die anderen eingeführt werden — Datum, Thema, die Seiten, die seine Begründung tragen (`` {ref}`external-anchor` `` auf `hash-chain.md`; die Tatsachen in `` {ref}`cli-reference` ``, die Routinen in den zwei Anleitungen). Und die Messung, die schon für Stufe 1b dort steht, für diesen Spec wiederholen: kein `§` im Code, das auf ihn zeigt.

Run: `grep -rn "§" src tests migrations | grep -v "frozen design record"`
Erwartet: leer. Und `grep -rn "§" src tests migrations | wc -l` gegen die Zahl, die die Seite nennt — der Anker fügt keines hinzu.

`README.md`: die Tabelle der eingefrorenen Berichte bekommt die fünfte Zeile, mit Datum.

`CLAUDE.md` nicht anfassen: der Absatz über die eingefrorenen Berichte ist seit Stufe 1b ohne Zahl gefasst, damit der fünfte ihn nicht wieder falsch macht.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **265 passed**, unverändert gegenüber dem Stand nach Aufgabe 2 samt ihrer Fixrunde (hier stand 263, bis die Fixrunde zwei Tests für die Standardeingabe brachte); Vale mit derselben Dateizahl wie zuvor (keine neue Seite).

```bash
git status --short
git add docs/how-to/verify-the-chain.md docs/how-to/restore-from-a-backup.md README.md \
        docs/tutorials/record-your-first-event.md docs/explanation/design-records.md \
        docs/superpowers/specs/2026-10-04-aeusserer-anker.md
git commit -F - <<'MSG'
docs: the anchoring routine, a restore in two cases, and the spec frozen

The how-to for checking the chain gains the routine: check the old
anchors, take a new one, keep the file where the database's writer cannot
write. The restore guide said that exit code 0 makes a restore
trustworthy; a restore from an older state is a shorter chain that is
consistent in itself and passes. It now asks for the anchors, and names
two cases — a restore to the latest state, checked with "contains", and a
restore to a fixed point that coincides with an anchor, checked with
--exact.

The tutorial is retyped from one run: verify shows its second line now,
and a short step pins the tip. The README says what an anchor adds and
what it does not.

The specification gets the dated header the four before it carry, and its
open points go to the specification that follows.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Nach Aufgabe 3: Endprüfung, Protokoll, Pull-Request

Sache des Controllers, nicht einer Aufgabe:

1. **Endprüfung des ganzen Zweigs**, mit zwei Paketen wie bei Stufe 1b (Code und Konfiguration; englische Doku), dem Spec als Datei.
2. **Eine Fixwelle** für ihre Befunde, eine Nachprüfung.
3. **Das Ausführungsprotokoll** nach `docs/superpowers/sdd/2026-10-04-aeusserer-anker/`, als eigener Commit, unverändert kopiert, mit `index.md`. Erst danach das Arbeitsverzeichnis unter `.superpowers/` löschen.
4. **Push und Pull-Request.** Der Merge ist die Abnahme (`CLAUDE.md`).

Prüfer schreiben ihren Bericht in eine Datei im Arbeitsverzeichnis des Plans und geben ein kurzes Verdikt zurück; der Controller tippt keine Berichte ab.

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** §1 Lieferungen 1–5 → Aufgaben 1 (Ankerzeile, Kern), 2 (`anchor`, `verify --anchors`, Hinweis), 1+2+3 (Doku). §1.1 Korrektur → Aufgabe 1 Schritt 10 (Seite), Tests zum Anhängen und zur Grenze. §1.2 zwei Einstiege → Aufgabe 1 (`examine` liefert `Examination`), Aufgabe 2 (`cli` liest und formatiert nur). §2 Format und Fehler → Aufgabe 1 Schritte 2–5. §3 `anchor` → Aufgabe 2. §4 Argumente, Prüfarten, Befunde, Meldungen, Rückgabecodes → Aufgabe 1 Schritt 7 und Aufgabe 2 Schritte 3 und 6. §5 Tabelle und Zusage → Aufgabe 1 Schritt 10; §5.1 Betrieb → Aufgabe 3 Schritte 1 und 2. §6 Schnitt → Dateistruktur. §7 Zusicherungen 1–9 → 1: beide Tests zur gelöschten Spitze (Kern und CLI); 2: Umschreiben; 3: Anhängen; 4: Grenze; 5: `test_anchor.py` und der parametrisierte CLI-Test; 6: `anchor` auf leerem Log und gebrochener Kette; 7: `verify` ohne Anker; 8: `test_anchor.py`; 9: Aufgabe 2 Schritt 7. §8 Doku → Aufgaben 1, 2, 3. §9 Abnahme 1–12 → 1–4: Aufgabe 1; 5–7: Aufgabe 2; 8: Aufgabe 1 (`verify` behält Signatur) und `lint-imports`; 9: die Mutationstabellen; 10: Aufgabe 3; 11: jede Aufgabe; 12: Aufgabe 3 Schritte 5 und 6.

**Nicht gedeckt und bewusst so:** der Tabellentest aus §10 Punkt 11 (oben begründet).

**2. Platzhalter.** Kein „TBD". Die Doku-Schritte tragen Seitenspezifikationen mit Muss-Inhalt und, wo ein Test daran hängt, den Wortlaut.

**3. Namenskonsistenz.** `Anchor(id, hash)`; `parse_anchors`, `format_anchor`; `Examination(findings, tip)`; `examine(storage, *, anchors, exact, batch)`; `verify(storage, *, batch)`. Die drei Befundtexte stehen gleichlautend in *Vertragliche Wortlaute*, in `examine`, in den Tests beider Aufgaben und im Block für `cli.md`. Der Hinweis steht gleichlautend in `_cmd_verify`, in `_HINT` (mit Zeilenende) und im Block für `cli.md`.

**4. Testzahlen**, am Plantext gezählt: `test_anchor.py` zwei einfache Tests, ein parametrisierter mit sieben Fällen, einer mit zwei → 11. `test_verify.py` acht neue. Aufgabe 1: 232 + 19 = **251**. `test_cli.py` acht einfache Tests und ein parametrisierter mit vier Fällen → 12. Aufgabe 2: 251 + 12 = **263**. Aufgabe 3: **263**. Jede Zahl ist eine Vorhersage, die der Umsetzer nachzählt. *Nachtrag 2026-10-04:* gemessen 251, 263 und nach der Fixrunde der Aufgabe 2 **265**; Aufgabe 3 fügt keinen Test hinzu und steht damit bei 265.

**5. Review Focus.** 1 → `test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read`; 2 → `test_a_broken_anchor_file_is_an_input_error` und `test_a_directory_as_anchor_file_is_an_input_error`; 3 → `test_anchors_are_checked_across_a_batch_boundary`; 4 → `test_an_empty_log_has_no_tip_and_misses_every_anchor`; 5 → der Fall `²` in `test_a_broken_line_is_refused_with_its_line_number`.
