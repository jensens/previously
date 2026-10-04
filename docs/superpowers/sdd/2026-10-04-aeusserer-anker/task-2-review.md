# Review Aufgabe 2 — `anchor`, `verify --anchors [--exact]`, Reference

Basis `4d1720a`, Kopf `2637c8e` (`feat: anchor, and verify --anchors`). Gelesen: Brief, Dispatch, Bericht, Diff-Datei (vollständig), Spec §3/§4 (Ausschnitte), Plan-Abschnitt „Review Focus".

### Spec Compliance

- ✅ Sechs Dateien, je mit Hunks: `src/previously/cli.py`, `tests/test_cli.py`, `tests/test_docs_references.py`, `docs/reference/cli.md`, `pyproject.toml`, `docs/tutorials/record-your-first-event.md`. Nichts sonst im Commit.
- ✅ Prüfung 1, Reihenfolge in `_cmd_verify` (`src/previously/cli.py:232`): erst `--exact` ohne `--anchors` → `InvalidPayload`, dann `_read_anchors`, dann `examine(_storage(), …)`. Vor dem ersten `print` kann nur eine Ausnahme fliegen, also bleibt stdout bei jedem Eingabefehler leer. Der Hinweis steht nur im Zweig `not examination.findings and not anchors` — nur bei intakter Kette, nur ohne Anker. Als Literal im `print(..., file=sys.stderr)` (Resolution 2).
- ✅ Prüfung 2, `_cmd_anchor` (`src/previously/cli.py:263`): ein einziges `examine(_storage())`, die Spitze kommt aus `examination.tip`, keine zweite Abfrage; bei einem Befund `return 1` vor jeder Ankerzeile; leeres Log → Satz auf stderr, Code 0.
- ✅ Vertragstexte zeichengenau: `chain intact`, `chain intact, 1 anchor holds`, `chain intact, N anchors hold`, Suffix `, the tip is the newest anchor`; Hinweis und `the log is empty: nothing to anchor`; `--exact needs --anchors`; die drei Befunde in `core/verify.py:273/302/308` unverändert.
- ✅ Rückgabecodes 0/1/2 wie gefordert; Eingabefehler über `InvalidPayload` → `main` → `Error: …`, Code 2.
- ✅ `cli` liest und formatiert; Zeilenformat und Prüfung bleiben in `core/anchor.py` und `core/verify.py`. Kein SQLAlchemy-Import in `cli.py` hinzugekommen.
- ✅ Labels: `review focus 1/2 of the 2026-10-04 external-anchor plan`, jeweils hinter dem Grund; gegen den Plan geprüft (Plan Z. 66–67: 1 = BOM/Windows, 2 = Datei, die keine ist) — sie zeigen auf das Richtige. `{ref}`-Verweise, kein `§`, keine Zitation in Ausgaben.
- ✅ Prüfung 4, Zählungen gemessen: T201 `Found 24 errors.`, `grep -c "print("` 24 — `pyproject.toml` und der Docstring sagen „twenty-four". `grep "seven\|eight"`: Z. 458/459 historisch (Reihe mit sieben), Z. 464 „`anchor` is the eighth command", Z. 486 „one of the eight keys" — die Tabelle hat acht Einträge. C901 mit Schwelle 1: `main` 2, `_read_anchors` 4, `_cmd_verify` 5, `_cmd_anchor` 4 — wie der Kommentar und der Dispatch sagen. Der `C901`-Kommentar trennt Gemessenes (Tabelle = 2) von Abgelesenem (Kette stünde bei 10) und sagt, dass die Kette nicht neu gebaut wurde; keine Behauptung, die er nicht trägt. Der alte Satz „Two branches of headroom", für acht Kommandos falsch, ist zu Recht gefallen.
- ✅ Prüfung 5, `cli.md`: acht Unterkommandos, `anchor` nach `verify`; Zeilen für `verify` und `anchor` in der Exit-Code-Tabelle mit dem Wortlaut des Briefs; Argumenttabelle; Zeilen- und Dateiformat gegen `parse_anchors` geprüft (zwei Felder, `id` ≥ 1 ASCII-Ziffern, 64 Hex-Zeichen, Leerzeilen/`#` übersprungen, Datei ohne Anker = Fehler); „holds"/`--exact` gegen `examine`/`_closing_findings` geprüft (`tip_id = 0` bei leerem Log, `tip_id > newest`); die drei Einleitungssätze wörtlich vorhanden, `Two notices go to standard error` unverändert. Begründung nur als Verweis auf `{ref}`external-anchor``.
- ✅ Prüfung 6, Tutorial: `collected 263 items`, `263 passed`, Summe der Punkte je Datei = 263 (nachgezählt), alle Prozentangaben passen zu `floor(kumuliert·100/263)`, keine `rootdir:`-Zeile. `--collect-only` zählt 263.
- ✅ Prüfung 3, Zitat-Test: `_quoted_block` mit lesbarer Zusicherung, `_finding_patterns` liest jedes positionale `Finding(_, reason)` im Modul (also auch die zwei in `_closing_findings`); Blöcke mit 2/1/1 Hinweisen und 3 Befunden. Jede zitierte Zeile auf `cli.md` ist Wort für Wort, was der Code druckt. Läuft grün (`5 passed`).
- ✅ Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`, kein `Co-Authored-By`.
- ❌ Review-Fokus 2 des Plans („kein UTF-8 → Rückgabecode 2 und ein Satz, kein Traceback") hält auf dem Weg `--anchors -` nicht — gemessen, siehe Important 1. Vom Brief vorgegeben (plan-mandated).
- ⚠️ Die Mutationen aus Schritt 7 habe ich nicht wiederholt (Auftrag: keine Mutation). Bewertet nur durch Lesen von `_is_the_same_sentence` gegen jede zitierte Zeile: die vier Mutationen treffen statische Teile bzw. den Einleitungssatz und müssen rot werden; die Kontrolle (`12`→`7`) trifft eine Interpolation und bleibt grün. Plausibel, aber vom Bericht übernommen, nicht von mir gemessen.

### Strengths

- Die Reihenfolge in `_cmd_verify` ist genau so gebaut, dass „ein Eingabefehler druckt nichts auf stdout" strukturell gilt und nicht nur getestet ist; `test_exact_without_anchors_is_an_input_error` beweist durch das Fehlen einer Datenbank, dass die Datenbank nicht gefragt wird.
- `_cmd_anchor` nimmt die Spitze aus demselben Durchgang, und `test_anchor_prints_the_tip_and_verify_holds_it` prüft über `show 2`, dass es der Hash der Spitze ist und nicht irgendeiner.
- `_quoted_block` ersetzt den alten `IndexError` durch eine Meldung, die den verschwundenen Satz nennt — eine echte Verbesserung der Fehlermeldung, nicht nur eine Verallgemeinerung.
- Der `C901`-Kommentar hält Messung und Ableitung auseinander und streicht den für acht Kommandos falschen „headroom"-Satz, statt ihn fortzuschreiben.
- Der Bericht benennt ehrlich den Defekt des Dispatch (`tail -1` liefert die „No fixes"-Zeile) und hat die Zahl aus der richtigen Zeile genommen; meine Messung bestätigt 24.
- Der Tutorial-Block ist in sich konsistent bis in die Prozentspalte — das spricht für einen echten, ganz abgetippten Lauf.

### Issues

#### Critical

Keine.

#### Important

1. **`src/previously/cli.py:166-167` (`_read_anchors`, Zweig `-`) — nicht-UTF-8 auf stdin endet in einem Traceback und Rückgabecode 1; plan-mandated.**
   Der `try` umschließt nur den Datei-Zweig; `parse_anchors(sys.stdin)` steht davor, und das Dekodieren passiert erst beim Iterieren in `core/anchor.py:34`. Gemessen: `uv run previously verify --anchors - < bad.txt` (Inhalt `\xff\xfe junk\n`) → `UnicodeDecodeError`-Traceback, `exit=1`. Rückgabecode 1 heißt für einen Cron-Job „Befund in Kette oder Anker" — ein Eingabefehler wird als Manipulationsbefund gemeldet. Genau das schließt Review-Fokus 2 des Plans aus („kein UTF-8 … Rückgabecode 2 und ein Satz, kein Traceback"), und der Spec nennt `-` den Weg, auf dem ein docker-compose-Host prüft (Spec Z. 276/285) — der Zweig ist also nicht nebensächlich.
   Dazu der zweite Teil derselben Lücke: stdin wird nicht mit `utf-8-sig` gelesen. Gemessen: Eingabe `\xef\xbb\xbf# c\n` über `-` → `Error: anchor line 1: the id has to be a positive integer, got '﻿#'`, Code 2. Damit ist `docs/reference/cli.md:64` („read as UTF-8 text, with or without a byte order mark") für `--anchors -` falsch, und `cli.md:66`/`:68` („a file that isn't UTF-8 text [is an] input error … returns 2") ebenso.
   Der Test `test_verify_reads_the_anchors_from_standard_input` (`tests/test_cli.py:1031`) prüft nur den Gutfall; die Fehlerfälle des Review-Fokus 2 sind nur für Dateipfade parametrisiert.
   Fix: stdin genauso dekodieren wie die Datei und im selben `try` — etwa `io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig")` (bzw. `sys.stdin.reconfigure(encoding="utf-8-sig")`) und das `UnicodeDecodeError`-`except` für beide Zweige; im Test zusätzlich einen Fall für `-` mit ungültigen Bytes und einen mit BOM (stdin per `monkeypatch` als `io.TextIOWrapper(io.BytesIO(...))`, denn `io.StringIO` hat kein `.buffer`). Mutation messen: `try` wieder auf den Dateizweig verengen → der neue Fall wird rot.

#### Minor

1. `docs/reference/cli.md:73` — „A file may name the same `id` on several lines, and each line is checked." Für den Hash-Vergleich stimmt das; für ein fehlendes Event erzeugt `_closing_findings` (`core/verify.py:302-303`, `sorted(pending)` über die Schlüssel) einen Befund je `id`, nicht je Zeile. Der Satz ist nicht falsch, lässt aber erwarten, dass zwei Zeilen für eine fehlende `id` zwei Befunde ergeben. Präzisieren oder stehen lassen; kein Gate betroffen.
2. `tests/test_docs_references.py:437` — `reason = line.split(": ", 1)[1]` wirft das Präfix `FINDING <n>: ` weg; ob `cli.md` das Präfix so zitiert, wie `cli.py` es druckt (`f"FINDING {finding.event_id}: {finding.reason}"`), prüft nichts. Ein umbenanntes Präfix auf einer Seite bliebe grün. Ebenso ist der interpolierte Bereich der beiden Befunde mit Zahl (`(the log ends at 40)`, `(42)`) beliebig füllbar — das ist gewollt (Kontrolle `12`→`7`) und im Docstring nicht als Zusicherung behauptet, also kein falscher Anspruch; nur zur Kenntnis.
3. `tests/test_docs_references.py:397` — zur Frage des Implementers: Die Richtung Seite→Code ist genau das, was der Brief vorgab (Schritt 7 iteriert über die zitierten Zeilen), und der Docstring sagt die Grenze für die Befunde wahrheitsgemäß. Unvollständig ist er nur darin, dass dieselbe Grenze auch für die Hinweise auf stderr gilt: ein neues `print(..., file=sys.stderr)` in `cli.py`, das `cli.md` nicht zitiert, bemerkt der Test ebenso wenig. Ein Halbsatz würde den Docstring vollständig machen.

### Checks run

| Befehl | Ergebnis |
|---|---|
| `git status --short`; `git log --oneline -1` | sauber; `2637c8e feat: anchor, and verify --anchors` |
| `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py \| grep Found` | `Found 24 errors.` |
| `grep -c "print(" src/previously/cli.py` | `24` |
| `grep -n "seven\|eight" src/previously/cli.py` | Z. 458, 459, 464, 486 (s. o.) |
| `uv run ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py` | `_read_anchors` 4, `_cmd_verify` 5, `_cmd_anchor` 4, `main` 2; `Found 15 errors.` |
| `uv run pytest tests/test_docs_references.py -q -p no:randomly` | `5 passed in 0.12s` |
| `uv run pytest --collect-only -q -p no:randomly \| tail -1` | `263 tests collected in 0.17s` |
| Python-Skript über den Testlauf-Block des Tutorials | Summe 263, Prozente = floor, keine `rootdir:`-Zeile |
| `uv run previously verify --anchors - < bad.txt` (`\xff\xfe junk\n`) | Traceback `UnicodeDecodeError`, `exit=1` |
| `uv run previously verify --anchors - < bom.txt` (`\xef\xbb\xbf# c\n`) | `Error: anchor line 1: the id has to be a positive integer, got '﻿#'`, `exit=2` |
| `uv run ruff check .` | `All checks passed!` |
| `make -C docs vale` | `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.` |
| `git log -1 --format=%B 2637c8e \| tail -3` | `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>` |
| Lesen außerhalb des Diffs: `src/previously/core/anchor.py` (Risiko: Format-Aussagen auf `cli.md`), `core/verify.py` Z. 193–310 und `Finding(`-Aufrufe (Risiko: Befundtexte und `_finding_patterns`), `_is_the_same_sentence` (Prüfung 3), Plan Z. 62–70 (Risiko: Label zeigt auf falschen Fokus), Spec Z. 140–160 und `grep stdin` (Risiko: `-`-Pfad) | wie oben bewertet |

Nicht von mir gelaufen (vom Implementer berichtet, nicht nachgeprüft): `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html`, `make -C docs linkcheck`, die vier Mutationen und die Kontrolle. Der Bericht nennt alle sechs Tore mit Schlusszeile.

### Assessment

**Task quality:** Needs fixes

Der Zuschnitt ist sauber — Reihenfolge, Spitze aus demselben Durchgang, Zählungen, Referenzseite und Tutorial halten jeder Messung stand. Aber der `-`-Zweig, den der Spec zum Betriebsweg für docker-compose macht, meldet ungültige Bytes als Traceback mit Rückgabecode 1 (= Befund) und liest keine BOM, was Review-Fokus 2 des Plans und drei Sätze auf `cli.md` widerlegt; die Lücke stammt aus dem Brief, ist also plan-mandated, muss aber vor der Abnahme geschlossen und mit einem gemessen-roten Test belegt werden.
