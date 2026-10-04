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

