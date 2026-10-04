# Re-Review der Fixwelle (Opus), Diff `4c52091..ff3c261`

Wörtlich, wie vom Prüfer zurückgegeben; Controller-Rulings zu den drei Minor-Resten stehen im Hauptbuch.

---

## Item verdicts

### Abschnitt A

**I-1, jedes gedruckte Feld entschärft** — ADDRESSED. `src/previously/cli.py:300-303` schickt `source`, `external_id` **und** `content` durch `escape_field`, `:333` den `source` von `stats`; alle übrigen gedruckten Felder sind `int`, ISO-Zeitstempel oder Hex. Docstring `cli.py:77-96` trägt die Messung und sagt „every string field", nicht `content`. Gefaltet statt neu: `tests/test_cli.py:665` `== [6, 6, 6, 6]` und `:822` `== [5, 5, 5]`, beide nach `line.split("\t")` — also genau die Feldzahl, die `cli.md` zusichert. Die berichtete Altmessung ist nachrechenbar: mit Entschärfung nur auf `content` ergibt `de<TAB>sk` / `id<NL>x` zwei Zeilen mit 6 und 2 Feldern und bei `stats` 6 statt 5 — exakt die Zahlen im Bericht; Mutation (je ein `escape_field` entfernt) rot mit Diff-Ausgabe, Kontrolle grün, beides im Bericht.

**I-2, beide Zahlen in einer Anweisung** — ADDRESSED, keine Abweichung vom Ruling. `src/previously/storage/postgres.py:456-485`: ein `conn.execute(select(...))`, zwei Skalar-Unterabfragen je unter `coalesce(…, 0)`, kein äußeres `FROM`. Beide Kommandos nutzen es für die Rückstandszeile: `cli.py:291` (`CHRONICLE.name`) und `:329` (`SOURCE_STATS.name`); `storage.tip(`/`projection_state(` kommen in `cli.py` nicht mehr vor. Isolationsstufe unberührt — `postgres.py:95-98` hat keinen Hunk, `READ COMMITTED` steht unverändert. `docs/explanation/projections.md:182-186` behauptet genau das, was READ COMMITTED gibt (Snapshot je Anweisung, zwei Anweisungen in einer Transaktion sehen zwei Zeitpunkte, eine Anweisung einen) und nicht mehr; der Satz nennt zudem die eigene Vorgeschichte („the first version of this page claimed it did"). Kein neuer Test, Begründung im Docstring — richtig, die Eigenschaft ist strukturell. `tip_and_bookmark` steht außerhalb der Protokolle (`grep tip_and_bookmark src/previously/contract/` → leer).

**I-3, „all nine tests in this file"** — ADDRESSED. `grep -c "^def test_" tests/test_projection_worker.py` → **12**; `tests/test_projection_worker.py:104` sagt „twelve". Das zweite „nine" bei `:110` meint `test_projection_derive.py`, dort gemessen `grep -c "^def test_"` → **9**, bleibt also zu Recht stehen.

**I-4 / I-5, der datierte Messblock** — ADDRESSED, mit einem neuen Minor-Befund (siehe unten). `docs/explanation/module-boundaries.md:177-187` ist nicht neu getippt, „(40 today)" ist weg, „today's test run" ist weg; `193` steht nur noch **im** datierten Block. Die neuen Zahlen bei `:192` habe ich alle drei selbst gemessen: `ruff format --check .` → `48 files already formatted`, `pytest --collect-only -q -p no:randomly` → `232 tests collected`, `make -C docs vale` → `22 files`. „Three of the lines have moved" stimmt: `lint-imports` (`Contracts: 4 kept, 0 broken.`), `ruff check`, `pyright`, `html` und `linkcheck` stehen unverändert.

**I-6, die zwei Ruling-Zeiger in `.importlinter`** — ADDRESSED. `.importlinter:27-36` nennt `ruling T7-a` und `ruling T8-c` **einzeln** (die Erhebung sieht beide), schreibt sie dem 2026-10-02-Plan der Stufe 1a zu — den es gibt: `docs/superpowers/plans/2026-10-02-stufe-1a-log.md` —, nennt dessen Hauptbuch „never shipped and is lost", streicht den Verzeichniszeiger und hält die Messung fest. `.importlinter:52-56` trägt kein nacktes `ruling T8-c` mehr, sondern verweist auf die Schwesterstelle. Der Verweis auf `docs/superpowers/sdd/` steht nur noch als Messprotokoll („carries a `Ruling T7-a` about an unrelated decision and no `Ruling T8-c` at all"), nicht als Wegweiser.

**Minors** — alle ADDRESSED:
- `docs/reference/cli.md:114` listet Kappung zuerst, Rückstand zweitens und sagt „a single run can print both in that order" — das ist die Code-Reihenfolge (`cli.py:308-315`).
- `cli.md:17` `project`/2: „Storage raised an error, or the worker found a gap in the log."
- `docs/reference/database-schema.md:122-124` sagt „always `NULL` until stage 2"; die `unit`-Zeilen mit „in stage 1a" sind unberührt.
- Vertragsname: `.importlinter:69` `No vendor SDK in the package`, vom Tor gedruckt (selbst gefahren), `docs/explanation/module-boundaries.md:77` nachgezogen. Alter Name tree-weit: **7 Treffer, alle unter `docs/superpowers/`** (5 Aufgabenberichte, der eingefrorene 1a-Spec, der 1b-Plan), kein Treffer in `CLAUDE.md` oder einer lebenden Seite.
- `tests/test_docs_references.py:49` `CONFIG_FILES = ["pyproject.toml", ".importlinter"]`, `:111-120` `_referencing_files()`; Paragraphenzeichen-Prüfungen bleiben auf `*.py`, Modul-Docstring sagt, welche Prüfung sich geweitet hat. **Selbst gemessen** (Spiegelbaum im Scratchpad, Arbeitsbaum unberührt): `module-boundries` in `.importlinter` → **rot** (`These labels are referenced from code but defined in no page: {'module-boundries': ['.importlinter']}`); dieselbe Mutation mit `CONFIG_FILES = []` → **grün** (Kontrolle); Baum wie committet → grün.
- `cli.py:291`/`:329` nutzen `CHRONICLE.name`/`SOURCE_STATS.name`; die Werte sind identisch zu den alten Literalen (`'chronicle'`, `'source-stats'`, in-process geprüft), also keine Verhaltensänderung.
- `src/previously/core/projection/worker.py:132` `expected[0]`; `tests/test_projection_worker.py:317` matcht `"above id 4"`, bleibt gültig.
- `docs/how-to/rebuild-a-projection.md:20` sagt es einmal.
- `TRUNCATE`-Helfer gebaut: `tests/conftest.py:27` `TRUNCATE_ALL` aus `metadata`, `:55-74` Fixture `truncate_statement`. Nachgemessen: der abgeleitete Text ist `TRUNCATE unit, source_key, p_source_stats, p_chronicle, projection_state, event` — genau die sechs Schematabellen, `alembic_version` nicht dabei. `str` statt Callable ist begründet (hypothesis `eval_str`) und hält die Suppressions-Liste bei fünf; gemessen: `# noqa` in `src tests migrations docs/conf.py` → **5** (C901, DTZ001 ×2, S607, A001).

### Abschnitt B

**B.1, `ruling P-1` qualifiziert** — ADDRESSED. `tests/test_cli.py:517-519`: „ruling P-1 of the 2026-10-04 stage 1b plan, recorded in `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`"; der Grund daneben ist unverändert.

**B.2(a), Labels je Plan** — ADDRESSED. `CLAUDE.md:376-383` sagt „Labels are assigned per plan", verlangt das **Datum** (weil das Verzeichnis so heißt), zeigt die Form am P-1-Zitat und regelt die alten Zitate („stay bare … Whoever touches one qualifies it"). Bemerkenswert richtig: der Satz nennt **keine Zahl** („fifteen" wäre falsch gewesen).

**B.2(b), der gemessene Stand** — ADDRESSED, und die Korrektur der Controller-Zahlen ist bestätigt. Selbst nachgemessen: `grep -rnoiE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests migrations pyproject.toml .importlinter | sort -u` → 22 Vorkommen, **14** verschiedene Labels (nicht zehn). `git grep` bei `cdc508a` über dieselbe Pfadliste → **13** Labels, also alle außer `P-1` — wie `CLAUDE.md:392` sagt. Je Label `grep -c "Ruling <label>"` in `docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`: nur `T5-b` → 1 und `T7-a` → 1, die anderen zwölf → 0, also „eleven of those thirteen" ohne jede Zeile ✓. Die zwei Treffer nebeneinander gelesen: `progress.md:583` `Ruling T5-b` handelt von `Vale.Terms`, das Zitat `tests/test_schema.py:257` von der Naht „Index nur per Roh-DDL, nicht in `metadata` deklariert"; `progress.md:697` `Ruling T7-a` handelt von „drei Klassen von Verweis", das Zitat `.importlinter:30-31` von den `TYPE_CHECKING`-Ausnahmen. Also löst **keines** der vierzehn auf die benannte Entscheidung auf, und zwei auf eine fremde — genau so steht es in `CLAUDE.md:391-404`. „Lost" ist gemessen: `ls docs/superpowers/sdd/` → nur `2026-10-03-dokumentation`, und auch `.superpowers/sdd/` hält nur `2026-10-04-stufe-1b-projektionen`, es gibt kein 1a-Hauptbuch mehr. Die zwei Aussagen stehen getrennt (`:385-388`: „a shipped `progress.md` holds every ruling of its own execution — is true" gegen „the labels cited from the tree resolve there — is not"). Die Erhebung steht als **Kommandozeile** (`:409-411`) mit `.importlinter` und `pyproject.toml` in der Pfadliste, mit begründetem `-i`, mit dem benannten blinden Fleck (Plural) und der Regel „write one `ruling` per label" — die `.importlinter` jetzt einhält. Der alte Count „all sixteen do" ist ersatzlos heraus (`:425-428`). Der eingefrorene 2026-10-03-Bericht hat keinen Hunk.

**B.2(c), vier eingefrorene Berichte** — ADDRESSED. `CLAUDE.md:70-76` zählt nicht mehr als Regel, nennt die Daten und sagt, dass die Zahl weiterwandert; `:81-84` hält fest, was der Satz bis 2026-10-04 behauptete und seit welchem Commit (`fee6d2b`) das falsch war. Nachgemessen: vier Specs, Köpfe `Eingefrorener Entwurfsbericht, Stand 2026-10-03` (drei) und `… 2026-10-04` (Stufe 1b) — „Three froze on 2026-10-03 … which is four" stimmt. Das verbliebene „three" bei `:56` ist eine datierte Aussage über den 2026-10-03 („until that day the three German specifications") und war an jenem Tag richtig; es bleibt zu Recht stehen.

**B.3, `catch_up`-Docstring** — ADDRESSED. `src/previously/core/projection/worker.py:88-91` nennt den Riegel („refused with `ValueError` before the first transaction opens"); der Riegel selbst `:99-102` unverändert.

**B.4, `log --limit < 1`** — ADDRESSED. `cli.py:183-194`: gleicher Wortlaut wie `chronicle` (`:282`), vor `_storage()`, mit der Messung beider Altformen im Kommentar. Gefaltet in `tests/test_cli.py:54-64` (0 und -2 → Exit 2, leeres stdout, `Error: --limit must be at least 1, got …`). `docs/reference/cli.md:43` „at least 1", `:48` der Satz, `:8` die Rückgabecode-Zeile für `log`. Altverhalten im Bericht gemessen (stiller Exit 0 bei 0; `InvalidRowCountInLimitClause` und Exit 1 bei -2), Mutation rot, Kontrolle grün.

**B.6, die zwei stderr-Sätze gegen den Code** — ADDRESSED, mit erklärter und von mir nachgemessener Erweiterung des Kandidatenfelds. `tests/test_docs_references.py:252-333` plus Assertion `:394-400`. **Selbst gemessen** (Helfer in-process, kein Schreibzugriff): die Prüfung bleibt grün, wenn nur die interpolierten Zahlen wechseln (`9 lines`, `7 events`), und wird rot bei drei Verfälschungen (`previously catch-up`, `widen --since/--until`, abgeschnittener Satz). Die Begründung für das breitere Feld stimmt: ein auf `print(…, file=sys.stderr)` beschränkter Satz von Mustern deckt nachgemessen **nur** die Kappungszeile, nicht die Rückstandszeile (`_lag_line` gibt sie zurück, `print(lag, …)` druckt eine Variable). Die Reihenfolge ist zusätzlich im CLI-Test gepinnt: `tests/test_cli.py:770-773` lässt beide Hinweise in einem Lauf feuern, Kappung zuerst.

**B.7, die zwei Formulierungen in `module-boundaries.md`** — ADDRESSED. Der Antezedens-Satz heißt jetzt „The six-gate block further up, not the `pyright` line right above, …" (`:197`), und „when a second protocol follows" ist „before another protocol is added" (`:251`).

**Nicht unter Verifikation, wie beauftragt:** I-7 (Controller), B.5, die Längenfrage, die `--limit`-Obergrenze.

### Abschnitt C

Zahlen: alle von mir nachgefahren (48 / 232 / 22 / 12 / 9 / 14 Labels / 5 Suppressions / Vertragsname aus dem Torprotokoll). Tutorial: Zählwert unverändert bei 232 (`--collect-only` → `232 tests collected`), `docs/tutorials/record-your-first-event.md:181` `collected 232 items` und `:202` `232 passed` stehen unangetastet, die Datei hat keinen Hunk — richtig, der Block wurde nicht angefasst. Tore: der Bericht führt alle sechs einzeln auf, `linkcheck` eingeschlossen (`build succeeded.`, `output.txt` 0 Bytes). Commit-Hygiene: beide Commits tragen `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`, `git log -2` enthält 0 Treffer auf `Co-Authored-By|Generated with`; `.importlinter` ist per Hunk auf die zwei Commits verteilt, wie der Bericht sagt.

## Eigene Messungen (Tore)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `48 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 4 kept, 0 broken.`, vier Namen KEPT, `No vendor SDK in the package` darunter, keine `ignored imports`
- `make -C docs vale` → `0 errors, 0 warnings and 0 suggestions in 22 files.`
- `uv run pytest tests/test_cli.py tests/test_docs_references.py -q -p no:randomly` → `40 passed in 13.22s`
- Nicht gefahren, laut Auftrag: volle Suite, `linkcheck`.
- Keine Schreiboperation im Arbeitsbaum: `git status --short` war und ist leer; die zwei Mutationsmessungen liefen über einen Spiegel im Scratchpad bzw. in-process.

## New breakage in the fix diff

**Minor — `docs/explanation/module-boundaries.md:193` datiert eine Zahl falsch.** „The file count moved by one on the day of the measurement itself, with `contract/store.py`, and by the rest with stage 1b's modules." Der Block darüber ist ausdrücklich der Stand **2026-10-03** (`:176`, `:190`), `contract/store.py` kam aber mit `afcbe11` am **2026-10-04** dazu, und die Notiz „(40 today)" schrieb `fdd3215`, ebenfalls 2026-10-04 (gemessen: `git log --diff-filter=A` bzw. `git log -S"(40 today)"`; alle 27 Commits dieses Zweigs sind 2026-10-04). Unter der Lesart, die der Absatz stützt, ist der Satz falsch; unter der anderen („der Messung von 2026-10-04") unterscheidet er nichts, denn 39→40 und 40→48 fielen auf denselben Tag. Sache stimmt (die eine Datei ist `contract/store.py`, heute sind es 48), nur die Zeitangabe nicht — dieselbe Fehlerklasse, die I-4/I-5 beseitigt haben.

**Minor — `src/previously/contract/rows.py:69-71` behauptet wörtlich etwas Falsches.** „Both numbers are 0 when the log is empty or the projection has no state row yet — … and the two cases give the same lag." Ohne Zustandszeile ist nur `up_to_id` 0, `tip_id` nicht: genau diesen Fall fährt `tests/test_cli.py` in `test_both_reading_commands_report_the_lag_on_stderr_and_only_there` (ein Event angefügt, nichts projiziert → `tip_id 1`, `up_to_id 0`, „1 event behind"). Und die beiden *genannten* Fälle geben verschiedene Rückstände (0 gegen `tip`). Gemeint ist offenbar „je eine Zahl in ihrem eigenen Leerfall" und „Zustandszeile mit `up_to_id 0` gegen keine Zustandszeile" — ein Satz, nicht das Verhalten; der Code selbst ist richtig (`coalesce(…, 0)` zweimal).

**Minor, nur im Bericht, nicht im Baum — eine Zahl im Fixbericht stimmt nicht.** `final-fix-report.md` sagt zum Vertragsnamen „found six places … The other five are frozen or historical … four task reports under `docs/superpowers/sdd/2026-10-03-dokumentation/`". Gemessen sind es **sieben** Stellen unter `docs/superpowers/` und darunter **fünf** Aufgabenberichte (`task-1`, `task-6`, `task-7`, `task-7-fix-1`, `task-7-fix-2`). Die Entscheidung (eingefrorene Stellen stehenlassen, lebende Seite nachziehen) ist davon unberührt und richtig.

## Out-of-scope observations

- `CLAUDE.md:410` lässt `migrations` aus der Pfadliste der Ruling-Erhebung, während die `W`/`G`/`B`/`K`/`N`-Erhebung darüber es mitführt. Heute ohne Folge (gemessen: kein Ruling-Zitat unter `migrations/`), aber das nächste landet dort unsichtbar.
- Gegen den Code gehalten wird die **Wortwahl** der zwei Hinweise und, im CLI-Test, die **Code**-Reihenfolge; die **Seiten**-Reihenfolge in `cli.md:114-120` hält weiterhin nichts mechanisch. Für die nächste Stufe vormerken.
- `tests/test_docs_references.py:252-256` (`_quoted_notices`) läuft bei verschwundenem Ankersatz in einen `IndexError` statt in eine lesbare Assertion.
- `_message_patterns` nimmt jedes zurückgegebene Literal ab 10 Zeichen auf, also auch die `_describe`-Ausgaben (`caught up: `, `rebuilt: version …`). Heute unschädlich, erweitert aber die Fläche für einen Treffer am falschen Satz.
- `src/previously/storage/postgres.py:462-464` sagt, PostgreSQLs Dokumentation formuliere es „in those words" — dort steht „command"/„query", nicht „statement". Inhaltlich deckungsgleich, als Zitatbehauptung eine Spur zu stark.
- `CLAUDE.md:391-397` ist eng auf den 2026-10-03-Bericht datiert und bleibt daher wahr, wenn der Controller das 1b-Hauptbuch ausliefert; der Nachsatz „The fourteenth label is `P-1`, whose record ships with stage 1b" fängt den Leser dabei auf.
- I-7 bleibt offen, wie beauftragt, und hängt jetzt an **zwei** Zitaten: `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md:727` und `tests/test_cli.py:519`.
- Fünf eingefrorene Stellen unter `docs/superpowers/` zitieren weiter `No vendor SDK in stage 1a` — genau dafür sind eingefrorene Berichte da.

## Verdict

**Fix wave:** All items addressed, no new Critical/Important breakage. Offen bleibt nichts aus den Abschnitten A und B, die unter Verifikation standen; drei Minor-Befunde (zwei im Baum: `module-boundaries.md:193`, `contract/rows.py:69-71`; einer nur im Fixbericht) sind in einer Zeile je Stelle behebbar und blockieren den Merge nicht — wobei `module-boundaries.md:193` eine datierte Behauptung auf einer lebenden Seite ist und damit genau die Art Zeile, die diese Welle beseitigen sollte.
