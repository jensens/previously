# Task 2 — Nachprüfung der Fix-Runde 1

Fix-Basis `2637c8e`, Head `81992f9` (`fix: standard input is read the way a file is`).
Arbeitsbaum beim Start und am Ende sauber (`git status --short` leer); nichts mutiert.

### Finding verdicts

**Important 1 — `--anchors -` liest Standardeingabe wie eine Datei: ADDRESSED.**

- Code: `src/previously/cli.py` `_read_anchors` liest beide Quellen als Bytes (`sys.stdin.buffer.read()` bzw. `open(source, "rb")`), dekodiert einmal mit `utf-8-sig` innerhalb eines `try`, Parser nach dem `try` über `io.StringIO(text, newline=None)` — der geregelte Körper (T2-a) wortgleich.
- Tests auf Standardeingabe, als Bytes: `tests/test_cli.py` — `test_verify_reads_the_anchors_from_standard_input` jetzt `io.TextIOWrapper(io.BytesIO(line.encode()))`; neu `test_a_byte_order_mark_and_windows_line_ends_on_standard_input_are_read` (BOM + `\r\n`, über `TextIOWrapper(BytesIO)`); neu `test_bytes_that_are_not_utf8_on_standard_input_are_an_input_error`, prüft `== 2` und `(out, err) == ("", "Error: standard input is not UTF-8 text\n")`, ohne Datenbank, Docstring nennt den Grund (Exit 1 = Fund für einen Cron-Job).
- Mutationstabelle im Bericht: beide Zeilen der Dispatch-Tabelle vorhanden, je mit rot und grün; beide wie vorhergesagt (Zeile 1: beide BOM-Tests rot, Plain- und Nicht-UTF-8-Test grün; Zeile 2: BOM- und Nicht-UTF-8-Test auf stdin rot, Plain-Test grün, dazu Datei-BOM-Test grün). Nicht von mir nachgemessen (Auftrag: nichts mutieren); in sich stimmig mit dem Code — Zeile 1 lässt `﻿` vor `# kept outside` stehen, das dann kein Kommentar ist, und die Nicht-UTF-8-Eingabe scheitert mit `utf-8` genauso.
- Referenzabsatz `docs/reference/cli.md:64–69`: jeder Satz gegen `_read_anchors` und `parse_anchors` gelesen, für beide Quellen wahr (UTF-8 mit/ohne BOM, `\n`/`\r\n`; Leer- und `#`-Zeilen; fehlerhafte Zeile mit Zeilennummer; „Input without a single anchor line“ → `the anchor file holds no anchor`; nicht UTF-8 → Exit 2). „a file that can't be read“ ist für `-` nicht falsch, nur nicht erwähnt (siehe unten).
- Docstring beschreibt die Funktion, wie sie jetzt ist — inhaltlich korrekt; zu seinen Escape-Sequenzen siehe *New breakage* (Minor, blockiert das Finding nicht).

**Minor 1 — Satz zum mehrfachen `id`: ADDRESSED.**
`docs/reference/cli.md` (neue Zeilen nach 73): „Each of those lines is compared with the event's `hash`, and each line that doesn't match gives its own finding.“ — wahr: `src/previously/core/verify.py:271–273` iteriert `pending.pop(row.id, ())` und hängt pro abweichendem Hash einen Fund an. „A missing event gives one finding for its `id`, however many lines name it.“ — wahr: `verify.py:300–303`, `_closing_findings` iteriert `sorted(pending)`, also die Schlüssel.

**Minor 2 — Präfix der Fundzeile: ADDRESSED.**
`tests/test_docs_references.py` (Schleife über `findings`): `prefix, _, reason = line.partition(": ")`, `assert re.fullmatch(r"FINDING [0-9]+", prefix)` mit Meldung, die die Zeile nennt. Kommentar nennt die Gegenseite: `test_verify_reports_a_deleted_tip_against_the_anchor` und `test_anchor_prints_the_tip_and_verify_holds_it` — nachgelesen, beide vergleichen ganze Fundzeilen exakt (`tests/test_cli.py:900`, `:940`). Mutation `FINDINGS 42: …` im Bericht mit roter Meldung, unmutiert `5 passed` als grüne Kontrolle. `re` ist importiert (`tests/test_docs_references.py:30`).

**Minor 3 — Docstring nennt die Richtung für beide Hälften: ADDRESSED.**
Der Docstring von `test_the_reference_quotes_what_the_code_actually_prints` sagt jetzt „page to code only, for both halves“ und nennt sowohl einen nicht zitierten Grund in `core/verify.py` als auch ein neues `print(..., file=sys.stderr)` in `cli.py`.

### New breakage in the fix diff

- **Minor — `src/previously/cli.py`, Docstring von `_read_anchors` (Absatz „`io.StringIO(text, newline=None)` …“):** Der Docstring ist kein Raw-String, also sind `\r\n`, `\r` und `\n` darin echte Steuerzeichen. Gemessen: `repr` des Laufzeit-Docstrings zeigt `` `\r\n` and `\r` become `\n` `` als CR/LF-Zeichen, `pydoc.render_doc` enthält ein CR. Im Quelltext liest der Satz richtig, in `help()` zerbricht er an genau der Stelle, die er erklärt. Der Baum hat das Muster schon richtig vorgemacht: `src/previously/core/units.py:25–28` schreibt `` `\\r\\n` ``. Behebung: verdoppelte Backslashes oder `r"""`. Kein Gate fängt es (ruff `D301` offenbar nicht ausgewählt). Blockiert die Runde nicht.

Sonst nichts. Dateipfad (Check 2): die Meldungen für fehlende Datei, Verzeichnis und Nicht-UTF-8 sind für Dateien wortgleich (`cannot read the anchor file '<path>': <strerror>`, `the anchor file '<path>' is not UTF-8 text`); `open(dir, "rb")` wirft `IsADirectoryError` beim Öffnen wie vorher. Die parametrisierten Datei-Tests sind im Diff unberührt. Zeilenenden: vorher Textmodus mit universellen Zeilenenden, jetzt `StringIO(newline=None)` — beide übersetzen `\r\n` und `\r` zu `\n` und sonst nichts; leere Datei → derselbe `holds no anchor`-Fehler; Datei ohne abschließenden Zeilenumbruch → letzte Zeile wird wie vorher gelesen (`raw.strip()` im Parser). Einziger Unterschied: die Datei wird ganz gelesen statt zeilenweise — ohne Verhaltensfolge für Ankerdateien. Ein Dekodierfehler mitten in der Datei bleibt dieselbe Meldung; vorher konnte er nach Teil-Parsing kommen, jetzt immer vorher — der Exit-Code ist in beiden Fällen 2.

### Out-of-scope observations

1. **`the anchor file holds no anchor` bei `-`** (Controller entscheidet, nicht offen gezählt): Für eine Pipe lese ich das als leicht falsch — es gibt keine Datei, und der Fix hat für die anderen beiden Meldungen gerade die Unterscheidung „standard input“ / „the anchor file …“ eingeführt. Exit-Code und Form (ein Satz, Exit 2) stimmen; die Referenzseite sagt neutral „Input without a single anchor line“. Gemessen mit BOM-Eingabe und mit `/dev/null`.
2. `docs/reference/cli.md`: „a file that can't be read“ — für `-` fängt derselbe `except OSError` auch einen Lesefehler der Standardeingabe ab (`cannot read standard input: …`). Der Satz ist nicht falsch, nur unvollständig.
3. Ungemessen, nur gelesen: bei geschlossener Standardeingabe (`sys.stdin is None`) wirft `sys.stdin.buffer` einen `AttributeError` → Traceback, Exit 1. Vorher `parse_anchors(None)` → `TypeError`, ebenfalls Traceback; keine Regression des Fixes.
4. Aus Runde 0 weiter offen (Task 3): `docs/how-to/verify-the-chain.md:8` „takes no arguments“.

### Checks run

Handläufe (statt `printf … |` per Umleitung aus Scratch-Dateien mit denselben Bytes, weil die Sandbox die Pipe-Form ablehnte; für `sys.stdin.buffer.read()` gleichwertig):

```
$ uv run previously verify --anchors - < bad.txt     # printf '\xff\xfe junk\n'
Error: standard input is not UTF-8 text
exit=2
$ uv run previously verify --anchors - < bom.txt     # printf '\xef\xbb\xbf# c\n'
Error: the anchor file holds no anchor
exit=2
$ uv run previously verify --anchors - < /dev/null
Error: the anchor file holds no anchor
exit=2
```

Jeweils ein Satz auf stderr, kein Traceback, Exit 2.

- `uv run pytest tests/test_cli.py -q -p no:randomly -k "anchor or exact or standard_input"` → `14 passed, 35 deselected in 7.09s`
- `uv run pytest tests/test_docs_references.py -q -p no:randomly` → `5 passed in 0.12s`
- `uv run ruff check .` → `All checks passed!`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected in 0.18s`; Tutorial: `collected 265 items`, `265 passed`, Summe der Punkte je Datei = 265, keine `rootdir:`-Zeile im Block (nur der erklärende Satz in Zeile 207).
- Laufzeit-Docstring per `uv run python -c` geprüft (siehe Minor oben).
- Bericht des Umsetzers zeigt alle sechs Gates mit Schlusszeile (`ruff check`, `ruff format --check`, `pyright`, `lint-imports`, `pytest --cov` 265 passed / 97,65 %, `html` + `vale` + `linkcheck`). `ruff format --check`, `lint-imports`, die volle Suite, `html` und `linkcheck` habe ich laut Auftrag nicht selbst gefahren — dort sind es Behauptungen des Berichts.
- Commit-Nachricht: nicht geprüft (Diff-Datei enthält nur den Betreff).

### Verdict

Alle vier Findings ADDRESSED. Eine neue Minor-Schwäche im Fix-Diff (Steuerzeichen statt Backslash-Text im Docstring von `_read_anchors`), keine Critical oder Important. Fix-Runde ist abgeschlossen; die Minor kann im nächsten Commit mitgehen.
