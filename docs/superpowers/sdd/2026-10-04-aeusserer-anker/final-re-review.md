# Nachprüfung der Fixwelle nach der Endprüfung — `7c936be..059ccbd`

Prüfer: Claude Opus 5.5, 2026-10-04.
Gelesen: Auftrag, `final-review.md` (ganz), `final-fix-dispatch.md` (ganz), `final-fix-report.md` (ganz), `task-3-re-review-2.md` (M1–M4), die Diff-Datei einmal, `git log 7c936be..HEAD` einmal.
Bei HEAD nachgelesen: `examine`/`_closing_findings` (`src/previously/core/verify.py:200-345`), `PostgresStorage.__init__`/`begin`/`snapshot`/`_transaction`/`tip_and_bookmark`, `_cmd_log`/`_cmd_verify`/`_cmd_anchor`/`_cmd_show` (`src/previously/cli.py:225-330`), `Anchor` in `contract/types.py`, beide Anleitungen vollständig.
Baum am Ende sauber (`git status --short` leer), keine Mutation gefahren, beide Scratch-Container entfernt.

### Item verdicts

**F2 — eine Momentaufnahme — ADDRESSED.**
- `src/previously/storage/postgres.py:99` `begin`-Engine weiter `isolation_level="READ COMMITTED"`; `:101-103` zweite Engine-Sicht `engine.execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)`; `:105-108` `begin()`, `:110-127` `snapshot()`, beide über `_transaction` (`:129-`), das die Übersetzung von `OperationalError`/`ProgrammingError` einmal trägt — keine Kopie.
- Wo die Isolation wirkt: Engine-Optionen auf einer `OptionEngine` setzt SQLAlchemy beim Auschecken der Verbindung, also vor dem ersten Statement der Transaktion, und setzt sie bei der Rückgabe an den Pool zurück. Gemessen von mir (Scratch-`postgres:17`, `pool_size=1, max_overflow=0`, also zwingend dieselbe Verbindung; Skript `scratchpad/rr/iso.py`):
  ```
  begin     read committed off 65
  snapshot  repeatable read on 65
  begin     read committed off 65
  snapshot  repeatable read on 65
  begin     read committed off 65
  raw       read committed off 65      # engine.connect() ohne jede Option, nach snapshot
  write in snapshot: InternalError (psycopg.errors.ReadOnlySqlTransaction) cannot execute CREATE TABLE in a read-only transaction
  begin     read committed off 65
  ```
  Dieselbe Backend-PID 65 in jeder Zeile: eine Verbindung, die durch `snapshot()` lief, kommt mit `read committed`/`off` zurück — auch ohne dass `begin` die Stufe neu setzt (Zeile `raw`). Das ist der Unterschied zur per-Verbindung-Option: hier ist es eine Engine-Sicht, deren Merkmale SQLAlchemy beim Zurückgeben zurücksetzt, und die Messung bestätigt es.
- Übersetzung für `verify`/`anchor` von Hand gemessen (die vorhandenen Tests `test_an_unreachable_server_shows_one_sentence`, `test_a_missing_table_shows_one_sentence` in `tests/test_cli.py:218/231` und `tests/test_storage.py:448-466` fahren `log` bzw. `begin()`, **nicht** `snapshot()` — siehe Minor 3):
  ```
  verify, DSN localhost:1     Error: database server at postgresql+psycopg://user:***@localhost:1/db does not answer — …   exit 2
  anchor, DSN localhost:1     dieselbe Zeile
  verify, unmigrierte DB      Error: database schema incomplete — `uv run alembic upgrade head` has not run yet   exit 2
  anchor, unmigrierte DB      dieselbe Zeile, exit 2
  ```
- Test: `tests/test_storage.py:260` (Zusicherung: erste Anweisung im `snapshot` ist die Zählung, die Momentaufnahme steht also, bevor der Schreiber auf eigener Verbindung committet) und `:276` (Kontrolle unter `begin()`, `before + 1 == 2`). Die Kontrolle steht als eigene Funktion **daneben**, nicht im selben Test — das deckt sich mit `CLAUDE.md` („keep beside the test a case measured to stay green") und dem Fix-Auftrag („the control beside it"). Mutation laut Bericht: `snapshot` auf READ COMMITTED → `assert 2 == 1`, `1 failed, 1 passed`; zurück `2 passed`. Das ist genau das Paar, das zeigt, dass der Test das Richtige liest.
- Rennen laut Bericht und Commit-Text: vorher `examine runs: 563, appends: 1493, runs with findings: 19`; nachher `161 … 0` und `116 … 0`. Zur Frage der Laufzahlen siehe unten (Bewertung der Beobachtungen).
- Sätze: `verify.py:241-247` und `:252-255` sagen jetzt „snapshot" und warum eine Transaktion nicht reicht — wahr. Kommentar über `read` (`postgres.py:240-250`) — wahr. `hash-chain.md:268` („taken in the same snapshot") und `:312` sind jetzt wahr; `:281-284` neu und wahr („keeps the snapshot of its first statement to the end" ist die PostgreSQL-Semantik von REPEATABLE READ). `concurrency.md:46-49` neu. Zum Satz über Serialisierungskonflikte siehe Minor 1.
- Grep `snapshot|one moment|same state` über `src docs`: jede Fundstelle beurteilt. Wahr: `verify.py`, `postgres.py` (alle), `store.py`, `hash-chain.md` (alle), `concurrency.md:47`/`:134`, `projections.md:184/186`, `types.py:45` („at one moment" — der Anker ist die Spitze einer einzigen Momentaufnahme, jetzt tatsächlich), `append.py:411`. **Falsch: `cli.py:237-240`** („for `show` … event and units belong in the same snapshot", `_cmd_show` liest unter `begin()`) — außerhalb der Welle, siehe Beobachtungen.
- `docs/reference/`: nennt keine Isolationsstufe (`grep -n "READ COMMITTED\|isolation\|snapshot" docs/reference/*.md` leer) — nichts nachzuziehen.

**F1 — die Regel im Kern — ADDRESSED.** `src/previously/core/verify.py:63-73` Property `anchor`: `None if self.findings else self.tip`, Docstring mit Grund; `Examination`-Docstring `:55-58` verspricht nichts mehr unbedingt. `_cmd_anchor` (`cli.py:280-296`) entscheidet nichts mehr: druckt Befunde, `format_anchor(anchor)` wenn vorhanden, den Leerhinweis nur ohne Befund, `1 if findings else 0` — Verhalten für leer/intakt/gebrochen von Hand gegen den alten Code nachvollzogen, identisch. `tests/test_cli.py` im Diff nur an der B3-Stelle geändert (`:949`), die Anker-Tests unberührt und grün. Neuer Test `tests/test_verify.py:517`; Mutation laut Bericht: der neue Test **und** `test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain` rot. Kein weiterer Pfad: `grep -rn "\.tip\b\|format_anchor\|\.anchor\b" src` → nur `cli.py:291/293` über `anchor`, `verify.py:73`; `Anchor`-Docstring (`types.py:45`) behauptet nichts über gebrochene Ketten.

**F3 — eine Menge je `id` — ADDRESSED.** `verify.py:231-238` `dict[int, set[bytes]]`, `.add`; Vergleich `:283-285` je Element. Die Iterationsreihenfolge einer Menge von `bytes` hängt von `PYTHONHASHSEED` ab, ist hier aber unsichtbar: jedes Element ergibt denselben Text `hash does not match the anchor` für dieselbe `id`. `anchored event is missing` bleibt `sorted(pending)` (`:324`). `test_two_lines_for_one_position_are_both_checked` (`:558`) unberührt; neuer Test `:541`, Mutation laut Bericht rot. `docs/reference/cli.md:76-78` sagt das jetzt richtig; `<n>` zählt weiterhin Zeilen (`cli.py` `count = len(anchors)`).

**F4 — `id` länger als 19 Ziffern — ADDRESSED.** `src/previously/core/anchor.py:19`, `:52-56` vor `int()`; Meldung nennt die Zeile, kein Echo. `tests/test_anchor.py:49` Fall `5000-digit-id`, `:66` `< 100` für jeden Fall. Mutation laut Bericht: `ValueError … 4300 digits`. `cli.md:61` „a positive integer of at most 19 digits" — nötig und wahr (eine 20-stellige Zahl wird abgewiesen). Von Hand: `9999999999999999999` (19 Stellen, über `bigint`) wird angenommen und ergibt im Durchlauf „anchored event is missing", nie eine Datenbankabfrage — kein Widerspruch zur Seite. Zum Wortlaut bei nicht-numerischen Feldern siehe Minor 2.

**F5 und F6 — `verify-the-chain.md` — ADDRESSED.** `:41-51` erster Anker mit `previously verify --anchors anchors.txt`, `chain intact, 1 anchor holds`, Exit `2` für eine Datei ohne Anker, beide Entstehungssätze erhalten (Lauf im Bericht: leere Datei → `Error: the input holds no anchor` [2], Hinweistext → `got 7 fields` [2], `FINDING`-Zeile → `got 8 fields` [2]). Container: `:75-80` — der allgemeine Satz („has to meet two conditions") steht **vor** den Beispielen, jede Bedingung als Tatsache mit Folge, die Werkzeuge nur in „such as …"; keins wird vorgeschrieben; Quelle `final-review.md` Teil 4, im Bericht genannt. F6: `:53` „between fetching the anchor file from the place you keep it and putting it back there", `:65` „Put the file back after every run …". Kein Werkzeug, kein Manifest, keine Compose-Datei.

**F7 — `pyproject.toml:90-91` — ADDRESSED.** „(ruling T9-c of the stage 1a execution, whose ledger is lost, so the label resolves nowhere)"; ein `ruling` je Label, Grund daneben unverändert.

**F8 — Tutorial — ADDRESSED.** `docs/tutorials/record-your-first-event.md:118`, Anweisung im Tutorial-Ton, kein getippter Block verändert außer dem Testblock.

**F9 — Zusicherung 7 — ADDRESSED.** Mutation laut Bericht: `test_verify_without_an_anchor_says_what_it_does_not_attest` rot an `assert err == ""` (`tests/test_cli.py:865`, auf der Kette mit Befund, `:861`); gelesen: die Assertion steht genau dort. Keine neue Assertion nötig.

**B2 — ADDRESSED.** `cli.py:171` doppelte Backslashes; gemessen: `'text mode does: `\\r\\n` and `\\r` become `\\n`, and nothing else\nends a line. …'`, `chr(13) in doc` → `False`; der einzige Zeilenumbruch ist der des Docstrings selbst.

**B3 — ADDRESSED.** `anchor.py:73` `the input holds no anchor`. Grep `holds no anchor|anchor file holds` über `src tests docs README.md` (ohne `superpowers`/`_build`): `anchor.py:73`, `tests/test_cli.py:949` (ganzer Satz mit `Error: `), `tests/test_anchor.py:73` (verankert `^…$`), `verify-the-chain.md:78` (neu, gleichlautend), `restore-from-a-backup.md:133` („holds no anchor line", Beschreibung einer Datei auf einer Seite über Dateien — kein Zitat, wahr). Mutation laut Bericht: drei Fälle rot.

**B4 — ADDRESSED.** `cli.md:68` „a file or standard input that can't be read" — wahr für `_read_anchors` (`cannot read standard input: …`).

**B7 — M1 bis M4 — ADDRESSED.**
- M1: `restore-from-a-backup.md:117` „Keep `anchors.txt` unchanged in either case below"; `:119-122` der Fall ohne Anker steht jetzt **vor** dem Routine-Absatz (`:124-125`), sagt „no anchor was taken before the restore point", nennt `anchors-new.txt`, „never `anchors.txt`", und „with that name in place of `anchors.txt`". Als Betreiber jeden Weg zu `anchors.txt` abgelaufen (`:49`, `:102`, `:119-122`, `:124`): keine Anweisung führt auf `previously anchor > anchors.txt`.
- M2: `:131` „after a restore on purpose to an earlier point"; `:111-112` „keeping in mind what the cut can't show. Exit code `0` there doesn't mean that the restore reached the point you meant."
- M3: `:92-93`. Gegen den Code richtig: ohne `anchored event is missing` hat der Durchlauf jede Anker-`id` gesehen (`pending.pop` je Zeile, `examine` liest über Lücken hinweg weiter), die Spitze liegt also bei oder über dem jüngsten Anker; „other findings" führen im ersten Fall zu Exit 1 = gescheitert.
- M4: `:43`, `:45` „the last version of the anchor file from before …", `:47` „Don't take a version recorded after the restore point …".
- Weiterhin eine Admonition (`:7-9`).

### Gates run

Alle auf HEAD `059ccbd`, je einmal:

- `uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `50 files already formatted`
- `uv run pyright` — `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` — `Contracts: 4 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` — `============================= 270 passed in 23.69s =============================` (`Total coverage: 97.56%`; `cli.py`, `core/anchor.py`, `core/verify.py`, `storage/postgres.py` je 100 %)
- `make -C docs html` — `The HTML pages are in _build/html.`
- `make -C docs vale` — `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `make -C docs linkcheck` — **nicht gefahren** (Netz, laut Auftrag); der Bericht zeigt ihn: exit 0, `grep -c broken … output.txt` → `0`.

### New breakage in the fix diff

Keine Critical, keine Important. Drei Minor:

**Minor 1 — `src/previously/storage/postgres.py:123-126` und `docs/explanation/concurrency.md:48`: „a read-only transaction never has a serialization conflict" ohne Stufe.**
PostgreSQLs Seite zur Transaktionsisolation sagt den Satz im Abschnitt *Repeatable Read* („read-only transactions will never have serialization conflicts"). Unter *Serializable* gilt er nicht: dort kann auch eine nur lesende Transaktion mit einem Serialisierungsfehler abbrechen, wenn sie nicht `DEFERRABLE` ist (die Seite sagt, dass Gelesenes erst nach dem Commit gültig ist, „even for read-only transactions, except … deferrable"). Beide Sätze lösen die Bedingung von der Stufe ab; in `concurrency.md` steht er zwei Absätze unter dem Satz über `SERIALIZABLE` (`:40`) und liest sich dort als allgemeine Regel. Für den Code ist es wahr (die Transaktion ist REPEATABLE READ), die Begründung sagt aber mehr, als die Quelle trägt. Fix: „a read-only transaction at REPEATABLE READ never has …" an beiden Stellen. „under MVCC reading never blocks writing" ist wörtlich aus der MVCC-Einführung und hält.

**Minor 2 — `src/previously/core/anchor.py:52-56`: „the id has more than 19 digits" auch für ein Feld ohne Ziffern.**
Die Längenprüfung steht vor der Ziffernprüfung. Gemessen: `parse_anchors(['abcdefghijklmnopqrstu ' + 'a'*64])` → `anchor line 1: the id has more than 19 digits, longer than any event id`. Fail-closed, Exit 2, kein Echo — nur der Satz stimmt für diese Eingabe nicht. Fix: „the id is longer than 19 characters, longer than any event id", oder die Längenprüfung hinter `isascii() and isdigit()` (beides ist vor `int()`, nur dort zählt sie).

**Minor 3 — kein Test hält die Übersetzung für `snapshot()`.**
`tests/test_storage.py:448-466` und `tests/test_cli.py:218/231` fahren `begin()` bzw. `log`. Ein `snapshot()`, das an `_transaction` vorbei direkt `self._snapshot_engine.begin()` öffnete, ließe jede Gate grün (Abdeckung bliebe 100 %, weil `begin` den Helfer weiter durchläuft), und `verify` gegen einen toten Server endete wieder im Traceback mit Code 1. Heute stimmt das Verhalten (oben von Hand gemessen); die Zusicherung „must hold for `snapshot()` too" hat aber keinen Test, der rot würde. Fix: die zwei Fälle in `test_storage.py` über `begin`/`snapshot` parametrisieren, oder `main(["verify"])` in die zwei CLI-Fälle aufnehmen.

Nicht als Befund, aber zum Mitnehmen: `verify-the-chain.md:48-49` „that happens in two cases … so the file is empty" — der dritte Weg zu einer Datei ohne Anker, den `:80` selbst nennt (Hinweistext durch ein Terminal), hat dieselbe Ursache (leeres Log) und dieselbe Handlung (`:51`), nur ist die Datei dann nicht leer. Der Leser handelt richtig; ich würde es nicht anfassen.

### Bewertung der vier Punkte des Umsetzers

1. **F2-Commit allein auf der Doku.** `module-boundaries.md` ist bei HEAD wahr: `:224` „nine methods", der Block `:228-238` stimmt Zeichen für Zeichen mit dem von mir gefahrenen `grep -o … | sort -u` (neun Namen inkl. `storage.snapshot(`), `:242` „ten methods" = die zehn Log-Methoden von `PostgresStorage` (`begin`, `snapshot`, `tip`, `lookup`, `insert_event`, `read`, `units`, `units_by_event`, `count_events`, `source_keys`; die Projektionsmethoden gehören zu `ProjectionStore`) — dieselbe Zählweise wie das alte „nine" = acht + `units`. Grep `eight methods|nine methods|count_events` außerhalb `superpowers`/`_build`: nur `module-boundaries.md` (Treffer `:245/252` sind die datierte pyright-Messung zum Umbenennen von `count_events`, unberührt und unabhängig von `snapshot`). Zusätzlich `grep LogStore`: nur `contract/store.py:6` („nine methods", wahr) und Stellen ohne Zahl. Nichts verpasst. Dass `59072c4` die Seite für einen Commit falsch ließ, bricht keinen Test (die Seite ist nicht gegen den Baum geprüft) und ist im Text von `059ccbd` offen benannt; ohne Amend gab es keinen anderen Weg.
2. **`_cmd_log`-Kommentar (`cli.py:237-240`).** Falsch im Wortlaut: `_cmd_show` (`:299-330`) liest Event (`read`, Server-Cursor) und Einheiten (`units`, eigene Anweisung) unter `begin()`, also zwei Momentaufnahmen. Beobachtbar ist davon heute nichts: ein Event und seine Einheiten werden in **einer** Transaktion geschrieben (`insert_event`), und kein Codepfad in `src` ändert oder löscht sie (`grep` nach UPDATE/DELETE: nur Projektionstabellen). Ist das Event in der ersten Momentaufnahme sichtbar, ist sein Commit vorbei, und jede spätere Momentaufnahme enthält auch die Einheiten. Nur ein Schreiben am Code vorbei zwischen den zwei Anweisungen (Fälschung, oder eine künftige Löschung am Tombstone-Saum) könnte einen gemischten Stand zeigen. Kleinster Fix, der keinen falschen Satz lässt: **der Kommentar** — „for `show` it is not: event and units are read in one transaction, two snapshots under READ COMMITTED, which shows one state only because an event and its units commit together and are never rewritten". `snapshot()` für `show` wäre ein Token und machte den alten Satz wahr, führte aber eine Zusicherung ein, die — wie bei `tip_and_bookmark` — kein Test beobachten kann; nach `CLAUDE.md` wäre sie dann nur ein Kommentar. Nicht blockierend.
3. **Rennen: weniger Läufe nachher.** Der Bericht nennt den Grund: dieselbe Scratch-Datenbank wuchs über die Läufe (~2600, dann ~3700 Events), und jeder `examine`-Lauf geht über das ganze Log; in 20 s passen also weniger Läufe. Das Fenster des Fehlers (zwischen dem letzten leeren `read` und `count_events`) hängt nicht von der Loglänge ab, die Fehlerrate je Lauf also kaum. Bei 19/563 ≈ 3,4 % ist die Wahrscheinlichkeit, in 277 Läufen null Treffer zu sehen, wenn sich nichts geändert hätte, `0.966^277 ≈ 7·10⁻⁵`; selbst bei halbierter Rate je Lauf (weniger Anhänge je Sekunde: 1075 statt 1493) rund `1 %`. Ausreichend — zumal das Rennen nur Bestätigung ist: die Ursache ist durch REPEATABLE READ strukturell ausgeschlossen und durch den deterministischen Test `test_storage.py:260` mit Kontrolle festgenagelt.
4. **Container-Weg ohne `kubectl`.** Ja, die Seite trägt den Kubernetes-Leser: `verify-the-chain.md:75` stellt die zwei Bedingungen allgemein voran („Whatever starts the command inside the container has to meet two conditions"), jede mit ihrer Folge; `-i`/`-T` stehen nur als „such as"-Beispiele dahinter. Wer `kubectl exec` benutzt, liest „pass standard input through" und „must not allocate a terminal" und findet `-i` bzw. das Weglassen von `-t` in der Hilfe seines Werkzeugs. Ungemessenes nicht zu nennen ist hier richtig.

### Out-of-scope observations

1. `src/previously/cli.py:237-240` — falscher Satz über `show`, siehe Punkt 2 oben; nicht blockierend, Kandidat für den nächsten Schritt.
2. Die Zahl „27 of 539" im Docstring von `snapshot` und auf `hash-chain.md:283` ist die Messung der Endprüfung, nicht die des Umsetzers (19 of 563); datiert und als Messung markiert, also ehrlich — wer sie nachprüfen will, findet die eigene Zahl des Umsetzers nur im Commit-Text.

### Checks run

- `uv run python scratchpad/rr/iso.py` gegen Scratch-`postgres:17` (Port 55437, `pool_size=1`) — Ausgabe oben unter F2. Container `rr-anchor` entfernt.
- `previously verify`/`anchor` gegen `localhost:1` und gegen eine unmigrierte Scratch-Datenbank (Port 55438) — Ausgabe oben. Container `rr-anchor2` entfernt; `docker ps --filter name=rr-anchor` leer.
- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `270 tests collected in 0.16s`; Tutorial `:199` `collected 270 items`, `:221` `270 passed`; Zahlen je Datei gegen `--collect-only` (19 Dateien, alle gleich), Summe der Punkte 270, Prozente kumuliert nachgerechnet (alle abgerundet richtig, z. B. 28/270 → 10, 238/270 → 88); keine `rootdir:`-Zeile im Block.
- `git show 59072c4:docs/tutorials/record-your-first-event.md` → `collected 267 items` / `267 passed`; `git show 59072c4 --stat` → der Tutorial-Block reist mit dem Test, `module-boundaries.md` fehlt (wie der Bericht sagt).
- `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py | grep Found` → `Found 24 errors.`; `pyproject.toml:89-90/99` und `tests/test_docs_references.py:219` sagen „twenty-four".
- `grep -o 'storage\.[a-z_]*(' … | sort -u` → neun Namen; `grep -n "    def " storage/postgres.py` für „ten".
- `python -c "len(str(2**63-1))"` laut Bericht 19 — gegen den Kommentar `anchor.py:18` gelesen, stimmt.
- `parse_anchors` mit drei Grenzfällen (nicht-numerisch 21 Zeichen, 19 Neunen, 22-stellige `…001`) — Ausgaben unter F4/Minor 2.
- `uv run python -c "…_read_anchors.__doc__…"` (nur Shell) für B2.
- Die vier Greps des Auftrags (Methodenzahl, `snapshot|one moment|same state`, `holds no anchor|anchor file holds`) — oben beurteilt.
- Commits: `git log 7c936be..HEAD` — zwei Commits, F2 zuerst und allein; englische Betreffs; je `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`; `Co-Authored-By`/„Generated with": 0 Treffer. Der Commit-Text von `59072c4` zitiert „§10 item 2, frozen design record" — in einer Commit-Nachricht, nicht im Code, also erlaubt.
- Keine Mutation gefahren: die Zusicherungen, an denen ich zweifelte, waren durch die Berichtsmessungen beantwortet; die eine Lücke (Minor 3) ist das Fehlen eines Tests, keine Frage, ob ein vorhandener rot würde.
- `git status --short` am Ende leer.

### Verdict

**Ready for the pull request? Yes.**

Alle Punkte der Welle (F1–F9, B2, B3, B4, B7 mit M1–M4) sind ADDRESSED; F2 ist im Code, gegen die Datenbank und an jedem Satz, der „ein Schnappschuss" sagt, wahr, und die Isolation fällt nachweislich auf derselben Pool-Verbindung auf READ COMMITTED zurück. Die sechs Gates sind grün (fünf von mir gefahren, `linkcheck` laut Bericht). Die drei Minor (eine zu allgemein formulierte Begründung, ein Meldungswortlaut für nicht-numerische Felder, ein fehlender Test für die Übersetzung unter `snapshot()`) und der falsche Kommentar in `_cmd_log` blockieren nicht und lassen sich in einem kleinen Nachzug oder im PR selbst schließen.
