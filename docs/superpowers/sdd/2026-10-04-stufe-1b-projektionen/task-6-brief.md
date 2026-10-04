## Task 6: Die Kommandos `project`, `chronicle`, `stats`

**Files:**
- Modify: `src/previously/cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/explanation/projections.md`

**Interfaces:**
- Consumes: `PROJECTIONS`, `catch_up`, `Outcome`, `PostgresStorage.{read_chronicle, read_source_stats, projection_state, tip}`, `parse_moment`.
- Produces: drei Unterkommandos; Hilfsfunktionen `_escape(text) -> str`, `_plural(n, noun) -> str`, `_describe(outcome) -> str`; der Dispatch in `main` als Tabelle statt `if`-Kette.

- [ ] **Schritt 1: Die Tests zuerst**

In `tests/test_cli.py` anfügen (das Gerüst ist das der bestehenden `db`-Tests: `db: object`, `isinstance(db, Engine)`, `monkeypatch.setenv("PREVIOUSLY_DSN", …)`, `capsys`):

```python
from previously.cli import escape_field


def test_escape_field_folds_tab_newline_return_and_backslash_into_two_characters_each() -> None:
    """Spec §6.3 plus review focus 3: one unit is one line, and the escaping
    is reversible because the backslash is escaped first."""
    assert escape_field("a\tb\nc\rd\\e") == "a\\tb\\nc\\rd\\\\e"
    assert escape_field("plain") == "plain"


def _setup(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))


def _append(source: str, external_id: str, text: str, occurred_at: str) -> None:
    assert main(["append", "--source", source, "--external-id", external_id, "--text", text, "--occurred-at", occurred_at]) == 0


@pytest.mark.db
def test_project_on_an_empty_log_is_up_to_date_at_zero(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5. Nothing was built, so it does not say `built`."""
    _setup(db, monkeypatch)
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       up to date, up_to_id 0",
        "source-stats    up to date, up_to_id 0",
    ]


@pytest.mark.db
def test_project_says_which_path_it_took(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """First run on a log with events: `built`. Then `caught up`, then
    `up to date`. The first run has to come *after* the first append — a run
    on the empty log already writes the state row, and every later run is an
    ordinary catch-up (found by the plan's pre-flight scan)."""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello\n\nWorld", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    first = capsys.readouterr().out.splitlines()
    assert first == ["chronicle       built: 1 event, up_to_id 1", "source-stats    built: 1 event, up_to_id 1"]

    _append("email", "m2", "Again", "2026-10-02T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    second = capsys.readouterr().out.splitlines()
    assert second == ["chronicle       caught up: 1 event, up_to_id 2", "source-stats    caught up: 1 event, up_to_id 2"]

    assert main(["project"]) == 0
    third = capsys.readouterr().out.splitlines()
    assert third == ["chronicle       up to date, up_to_id 2", "source-stats    up to date, up_to_id 2"]


@pytest.mark.db
def test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec §6.2: time order, not chain order. Event 2 happened before event 1."""
    _setup(db, monkeypatch)
    _append("email", "m1", "late", "2026-10-02T09:00:00Z")
    _append("chat", "c1", "early\ttab", "2026-10-01T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "2\t1\t2026-10-01T09:00:00+00:00\tchat\tc1\tearly\\ttab",
        "1\t1\t2026-10-02T09:00:00+00:00\temail\tm1\tlate",
    ]
    assert err == ""  # up to date: silence


@pytest.mark.db
def test_chronicle_reports_the_lag_on_stderr_and_only_there(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _append("email", "m1", "x", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err.strip() == "projection is 1 event behind; run `previously project`"


@pytest.mark.db
def test_chronicle_window_is_half_open_and_an_empty_window_is_not_truncated(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 1 folded in: `--since` at or after `--until` prints
    nothing, returns 0, and says nothing on stderr."""
    _setup(db, monkeypatch)
    for n, day in enumerate(("01", "02", "03"), start=1):
        _append("email", f"m{n}", f"day {day}", f"2026-10-{day}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle", "--since", "2026-10-01T09:00:00Z", "--until", "2026-10-03T09:00:00Z"]) == 0
    out, err = capsys.readouterr()
    assert [line.split("\t")[-1] for line in out.splitlines()] == ["day 01", "day 02"]
    assert err == ""
    assert main(["chronicle", "--since", "2026-10-05T00:00:00Z", "--until", "2026-10-01T00:00:00Z"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "")


@pytest.mark.db
def test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    for n in range(1, 4):
        _append("email", f"m{n}", f"u{n}", f"2026-10-0{n}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle", "--limit", "2"]) == 0
    out, err = capsys.readouterr()
    assert len(out.splitlines()) == 2
    assert err.strip() == "output truncated at 2 lines; raise --limit or narrow --since/--until"
    assert main(["chronicle", "--limit", "3"]) == 0
    out, err = capsys.readouterr()
    assert (len(out.splitlines()), err) == (3, "")


@pytest.mark.db
def test_chronicle_rejects_a_naive_since(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 2: the same `parse_moment` as `--occurred-at`."""
    _setup(db, monkeypatch)
    assert main(["chronicle", "--since", "2026-10-01T09:00:00"]) == 2
    assert "time zone" in capsys.readouterr().err


@pytest.mark.db
def test_stats_prints_one_line_per_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _append("email", "m1", "a\n\nb", "2026-10-02T09:00:00Z")
    _append("email", "m2", "c", "2026-10-01T09:00:00Z")
    _append("chat", "c1", "d", "2026-10-03T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["stats"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "chat\t1\t1\t2026-10-03T09:00:00+00:00\t2026-10-03T09:00:00+00:00",
        "email\t2\t3\t2026-10-01T09:00:00+00:00\t2026-10-02T09:00:00+00:00",
    ]
    assert err == ""
```

Die Funktion heißt `escape_field` und nicht `_escape`, weil `CLAUDE.md` es so verlangt: wer eine Funktion direkt testet, gibt ihr einen öffentlichen Namen statt `reportPrivateUsage` zu unterdrücken. Und kein `# noqa` an den Import — `PL`-Regeln sind in `pyproject.toml` nicht ausgewählt, ein `noqa` dafür wäre `RUF100`.

- [ ] **Schritt 2: Laufen lassen — rot**

Run: `uv run pytest tests/test_cli.py -v -k "escape or project or chronicle or stats"`
Erwartet: `ImportError` für `escape_field`; die anderen `argparse`-Fehler (unbekanntes Kommando → `SystemExit 2`).

- [ ] **Schritt 3: Die Kommandos**

In `src/previously/cli.py`: Importe ergänzen —

```python
from previously.core.projection import catch_up
from previously.core.projection import Outcome
from previously.core.projection import PROJECTIONS
```

Hilfsfunktionen nach `_parse_evidence`:

```python
def escape_field(text: str) -> str:
    """One unit is one line of `chronicle` ({ref}`projections`), so tab,
    newline, carriage return and the backslash itself come out as two
    characters each. Backslash first, or the other escapes would be escaped
    again and the mapping would stop being reversible. Output format, not
    data: `p_chronicle` holds the content unchanged."""
    return (
        text.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _describe(outcome: Outcome) -> str:
    """Which path the worker took — a version-triggered rebuild is otherwise
    invisible ({ref}`projections`).

    Order matters. A version change is reported even when it processed no
    event, because it changed the state row. A first run over an empty log
    says `up to date`, not `built: 0 events`: nothing was built, and the
    spec's reading of `up_to_id 0` is "nothing yet".
    """
    tail = f"{_plural(outcome.events, 'event')}, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from:  # a version the table was at before: 1, 2, …
        return f"rebuilt: version {outcome.rebuilt_from} -> {outcome.version}, {tail}"
    if outcome.events == 0:
        return f"up to date, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from == 0:
        return f"built: {tail}"
    return f"caught up: {tail}"


def _report_lag(storage: PostgresStorage, conn: object, name: str) -> None:
    """`tip.id` and `up_to_id` of the projection being read, in the caller's
    transaction — two snapshots would give a difference that never existed.
    Silence means current."""
    from sqlalchemy import Connection

    assert isinstance(conn, Connection)
    tip = storage.tip(conn)
    state = storage.projection_state(conn, name)
    tip_id = 0 if tip is None else tip.id
    up_to = 0 if state is None else state.up_to_id
    lag = tip_id - up_to
    if lag > 0:
        print(f"projection is {_plural(lag, 'event')} behind; run `previously project`", file=sys.stderr)
```

**Halt — `_report_lag` so nicht.** `cli` darf SQLAlchemy nicht kennen (ruling T9-a, und `cli` steht über `storage` nur für `from_dsn`/`PostgresStorage`). Der `isinstance`-Umweg ist ein Geruch. Richtig: die Signatur nimmt `conn: Connection` **nicht** an, sondern die Funktion öffnet keine eigene Transaktion und bekommt die Werte übergeben:

```python
def _lag_line(tip_id: int, up_to_id: int) -> str | None:
    lag = tip_id - up_to_id
    if lag <= 0:
        return None
    return f"projection is {_plural(lag, 'event')} behind; run `previously project`"
```

und die Kommandos lesen `tip` und `state` selbst innerhalb ihrer Transaktion. So:

```python
def _cmd_project(_args: argparse.Namespace) -> int:
    storage = _storage()
    for projection in PROJECTIONS:
        outcome = catch_up(storage, storage, projection)
        print(f"{outcome.name:<15} {_describe(outcome)}")
    return 0


def _cmd_chronicle(args: argparse.Namespace) -> int:
    since = parse_moment(args.since) if args.since else None
    until = parse_moment(args.until) if args.until else None
    storage = _storage()
    with storage.begin() as conn:
        tip = storage.tip(conn)
        state = storage.projection_state(conn, "chronicle")
        # One more than the limit: if it comes back, the window was cut.
        rows = storage.read_chronicle(conn, since=since, until=until, limit=args.limit + 1)
    for row in rows[: args.limit]:
        print(
            f"{row.event_id}\t{row.seq}\t{row.occurred_at.isoformat()}\t"
            f"{row.source or ''}\t{row.external_id or ''}\t{escape_field(row.content)}"
        )
    if len(rows) > args.limit:
        print(
            f"output truncated at {args.limit} lines; raise --limit or narrow --since/--until",
            file=sys.stderr,
        )
    lag = _lag_line(0 if tip is None else tip.id, 0 if state is None else state.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0


def _cmd_stats(_args: argparse.Namespace) -> int:
    storage = _storage()
    with storage.begin() as conn:
        tip = storage.tip(conn)
        state = storage.projection_state(conn, "source-stats")
        rows = storage.read_source_stats(conn)
    for row in rows:
        print(
            f"{row.source}\t{row.events}\t{row.units}\t"
            f"{row.first_seen.isoformat()}\t{row.last_seen.isoformat()}"
        )
    lag = _lag_line(0 if tip is None else tip.id, 0 if state is None else state.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0
```

`_cmd_verify()` bekommt einen Parameter `_args: argparse.Namespace`, damit alle Kommandofunktionen dieselbe Signatur haben. Der Unterstrich ist kein `noqa`: ruff hat `ARG` nicht aktiv, und pyright strict meldet unbenutzte Parameter nicht.

In `main`, die Parser:

```python
    sub.add_parser("project", help="bring the projections up to the tip of the log")

    p_chronicle = sub.add_parser("chronicle", help="print the chronicle in time order")
    p_chronicle.add_argument("--since", help="ISO 8601 with a zone, inclusive")
    p_chronicle.add_argument("--until", help="ISO 8601 with a zone, exclusive")
    p_chronicle.add_argument("--limit", type=int, default=50)

    sub.add_parser("stats", help="print the per-source statistics")
```

Der Dispatch — **Tabelle statt `if`-Kette**, und der Grund steht schon in der Datei: `main` hat `C901` einmal gerissen (13 gegen 10). Sieben `if` plus `try/except` säßen genau auf der Schwelle.

```python
    commands: dict[str, Callable[[argparse.Namespace], int]] = {
        "append": _cmd_append,
        "log": _cmd_log,
        "verify": _cmd_verify,
        "show": _cmd_show,
        "project": _cmd_project,
        "chronicle": _cmd_chronicle,
        "stats": _cmd_stats,
    }
    try:
        return commands[args.command](args)
    except (PreviouslyError, StorageError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
```

`from collections.abc import Callable` unter `TYPE_CHECKING`. Der Kommentar „One branch per command instead of all four command bodies in one function" wird: eine Tabelle statt einer `if`-Kette, mit der `C901`-Geschichte als Grund. Der `return 2  # pragma: no cover` am Ende entfällt — `commands[args.command]` wirft `KeyError` nur, wenn argparse versagt hat, und das kann es mit `required=True` nicht.

- [ ] **Schritt 4: Laufen lassen — grün**

Run: `uv run pytest tests/test_cli.py -v`
Erwartet: alle `PASSED`, inklusive der bestehenden.

Run: `uv run ruff check .`
Erwartet: `All checks passed!` — insbesondere kein `C901` auf `main`.

- [ ] **Schritt 5: `cli.md`**

Die Exit-Code-Tabelle um drei Zeilen (`project`: 0 nachgezogen / 1 nicht benutzt / 2 Storage-Fehler; `chronicle` und `stats`: 0 gedruckt / 1 nicht benutzt / 2 ungültige Eingabe oder Storage-Fehler). Drei Abschnitte nach dem Muster von `## log`: Argumenttabelle, dann Ausgabeformat **als Tatsache**:

- `project`: „Prints one line per projection: the name padded to 15 characters, a space, and the outcome — `built: …`, `caught up: …`, `rebuilt: version N -> M, …` or `up to date, …`, each ending in `up_to_id <id>`."
- `chronicle`: die sechs Felder in Reihenfolge; die Ordnung `(occurred_at, event_id, seq)`; `--since` einschließlich, `--until` ausschließlich; die Entschärfung (vier Zeichen, je zwei Ausgabezeichen, Rückstrich zuerst); Rückstand und Kappung auf `stderr`, Rückgabecode 0.
- `stats`: fünf Felder, sortiert nach `source`; Rückstand auf `stderr`.

Ein Verweis für das Warum: „{ref}`projections` explains why `log` and `chronicle` are two commands."

- [ ] **Schritt 6: `projections.md` um `## Two orders, two commands`**

Spec §6.2 wörtlich sinngemäß: `occurred_at` läuft nicht parallel zu `id`; die Mail von letzter Woche; `log` ist Kettenordnung, `chronicle` ist Chronologie; das sind die zwei Zeitordnungen aus §4.1 der Architektur. Dazu `## Saying what it doesn't know`: Rückstand und Kappung auf `stderr`, Schweigen heißt aktuell, derselbe Gedanke zweimal.

Run: Doku-Tore. Erwartet: grün.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **232 passed** (223 + 9).

```bash
git add -A
git commit -F - <<'MSG'
feat: project, chronicle and stats

`project` catches every projection up and says which path it took — a
version-triggered rebuild would otherwise be invisible. `chronicle` is the
chronology, ordered by (occurred_at, event_id, seq) with a half-open
--since/--until window; `log` stays the chain order. Two orders, two
commands, which is what architecture §4.1 asked for.

One unit is one line: tab, newline, carriage return and backslash come out
as two characters each, backslash first so the mapping stays reversible.
Lag and truncation go to stderr, where no consumer reads them as a record,
and silence means current. The lag is tip against the up_to_id of the
projection being read, both in one transaction.

The dispatch in main is a table: seven branches plus the except would have
sat on the C901 threshold this function has already crossed once.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

