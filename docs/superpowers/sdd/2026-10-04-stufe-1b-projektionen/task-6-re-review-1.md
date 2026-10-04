# Task 6 — Re-Review Fixrunde 1 (Sonnet), Diff `a2dbe17..daea417`

Wörtlich, wie vom Prüfer zurückgegeben.

---

**I1 — C901-Kommentar** — ADDRESSED. `src/previously/cli.py:344-360`: der Kommentar nennt jetzt Kette 7→9, 8→10, 9→11, Tabelle→2, sagt ausdrücklich „`C901` fires strictly **above** its threshold", „an eighth command would still pass and only a ninth would break the gate" und „Two branches of headroom". Die 13 steht als „a historical figure from a version no longer in the tree, not re-measured here" (`cli.py:359-360`). Commit `daea417` benennt die Abweichung von `a2dbe17`s Botschaft explizit („The commit before this one carries the sharper claim in its message; this one corrects the comment and leaves the history as it was.") — `a2dbe17`s Text ist per `git log` gegengeprüft unverändert, keine Historienumschreibung. Selbst nachgemessen: `ruff check --select C901 --config 'lint.mccabe.max-complexity = 2' src/previously/cli.py` nennt `main` **nicht** (6 andere Funktionen, `main` fehlt); `= 1` meldet „`main` is too complex (2 > 1)" — exakt wie beauftragt zu prüfen.

**I2 — `cli.md`, Exit-Code `stats`** — ADDRESSED. `docs/reference/cli.md:19`: Zelle lautet jetzt „Storage raised an error." wie bei `project` (Zeile 17) und `verify` (Zeile 15).

**Minor — `up to date`-Bedingung** — ADDRESSED. `docs/reference/cli.md:83`: „No event was projected, and the version was unchanged." — exakt der vorgeschlagene Wortlaut, durch den Testfall `…_but_still_names_a_rebuild` gedeckt.

**Minor — quellenloser `stats`-Zweig** — ADDRESSED. `docs/reference/cli.md:130`: „An event with no source attribution appears in no line." Der Grund ist weg, die Tatsache bleibt; der Grund steht in `projections.md`.

**Minor — `pyproject.toml` T201-Begründung** — ADDRESSED. `pyproject.toml:90-96`: Satz und Befehl stimmen jetzt überein („every per-file ignore emptied out ... that also drops the `tests/*` line above, which costs nothing here, since the command names one file under `src/`"), erster Fehlzähler heißt „a miscount and not a drift". Nachgemessen: `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` → „Found 19 errors", stimmt mit der Zahl im Kommentar.

**Minor — `chronicle --limit < 1`** — ADDRESSED. `src/previously/cli.py:254-255`: `if args.limit < 1: raise InvalidPayload(...)` als allererste Anweisung in `_cmd_chronicle`, vor `parse_moment` und vor jedem Lesen. `InvalidPayload(PreviouslyError, ValueError)` läuft über den bestehenden `except (PreviouslyError, StorageError)`-Zweig in `main` (`cli.py:380-388`) zu Rückgabecode 2 mit `stderr` „Error: --limit must be at least 1, got …" — nennt `--limit`. In `tests/test_cli.py` in die bestehende `test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise` gefaltet (`for limit in ("0", "-2"): …`), kein neues `def test_`. `log --limit` unangetastet — kein Hunk an `_cmd_log`.

**Minor — quellenlose Chronik-Zeile** — ADDRESSED. `tests/test_cli.py`, in `test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source`: drittes Event (`id=3`, `key=None`) über `storage.insert_event` bei `2026-10-01T12:00`, fällt damit zeitlich zwischen die beiden bestehenden Events; erwartete Zeile `"3\t1\t2026-10-01T12:00:00+00:00\t\t\torphan"` steht exakt mittig in der erwarteten Liste. Muster deckt sich mit der bestehenden Praxis in `tests/test_projection_worker.py` (`insert_event` mit `key=None`).

**Beide zugesagten Zählungen nachgemessen:** `uv run pytest tests/test_cli.py --collect-only -q -p no:randomly` → 35 Tests (roh nur 30 `def test_`, Differenz durch den `@pytest.mark.parametrize`-Block bei Zeile 426, von der Fixrunde nicht berührt); `git show a2dbe17:tests/test_cli.py | grep -c '^def test_'` und dieselbe Abfrage gegen `daea417` liefern beide 30 — die Fixrunde hat keine Testfunktion hinzugefügt. Gesamtbaum: `uv run pytest --collect-only -q -p no:randomly` → 232, wie berichtet.

### New Breakage in the Fix Diff
None. Selbst gegengeprüft auf dem aktuellen Baum: `uv run ruff check .` → „All checks passed!"; `uv run ruff format --check .` → „48 files already formatted"; `uv run pyright` → „0 errors, 0 warnings, 0 informations"; `uv run lint-imports` → „Contracts: 4 kept, 0 broken." (insbesondere „Only storage imports sqlalchemy KEPT" trotz der neuen `EventRow`/`UnitRow`/`PostgresStorage`-Importe — die stehen nur in `tests/test_cli.py`, nicht in `cli.py`); `make -C docs vale` → „0 errors, 0 warnings and 0 suggestions in 21 files."; `make -C docs html` → „build succeeded." (`docs/_build/` ist per `.gitignore` ausgeschlossen, keine Mutation des Baums). Die neuen `review finding W2`-Zitate in `cli.py:246` und `:251` sind inhaltlich konsistent mit dem bestehenden Zitat in `cli.py:62` und mit der Verwendung in `storage/errors.py`. `pytest` selbst und `linkcheck` wurden nicht erneut vollständig gelaufen (Auftrag), aber `--collect-only` zweimal bestätigt die Zahlen.

### Out-of-Scope Observations
- Der Bericht der Hauptrunde behauptet „tests/test_cli.py — neun neue Tests, 26 → 35 in der Datei". Nachgemessen (`git show 71dc078:tests/test_cli.py | grep -c '^def test_'` = 21, `a2dbe17` = 30): die rohe Zahl an `def test_`-Funktionen ging von 21 auf 30, nicht von 26 auf 35 — „35" stimmt nur als von `pytest --collect-only` gesammelte Testanzahl (durch Parametrisierung), nicht als Zeilenzahl im Quelltext. Das ist eine Behauptung aus der Hauptrunde, von dieser Fixrunde nicht angerührt, blockiert daher nichts — aber nach „Ein Kommentar ist eine Behauptung" eine Zahl, die beim nächsten Anfassen der Datei nachgezählt werden sollte.
- Die sechs „Bedenken" und die drei „Was weiterhin offen steht"-Punkte aus dem Bericht (README veraltet, Tutorial-Überschrift, `ruling P-1` nicht nachschlagbar, `set(sub.choices) == set(commands)`, `log --limit`) sind laut Auftrag vom Controller zurückgestellt und wurden hier nicht verdiktet.

### Verdict
**Fix round:** All findings addressed, no new Critical/Important breakage.
