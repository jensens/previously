# Endprüfung Stufe 1b (Opus), Zweig `worktree-stufe-1b-projektionen`, HEAD `4c52091`, Basis `cdc508a`

Wörtlich, wie vom Prüfer zurückgegeben; Controller-Rulings stehen im Hauptbuch.

---

Gelesen: Spec §1/§1.1, §3, §4, §5, §6, §9, §10; Plan `## Global Constraints` + `## Review Focus` + Aufgabenköpfe; `CLAUDE.md` vollständig; Hauptbuch (Rückstandsliste nach A8, alle `Ruling`-Zeilen, `## Vorbereitung Schlussschritt`); beide Prüfpakete sowie die betroffenen Dateien bei HEAD. Ein Durchgang, keine Subagenten. Eine Schreiboperation im Baum (Mutation in `source_stats.merge`, mit `git checkout --` zurückgenommen, Tree danach clean — nachgemessen).

## Strengths

- `src/previously/core/projection/worker.py:144-149` — die Lückenprüfung vergleicht die gelesenen `id` gegen den Lauf ab `up_to_id + 1`, nicht gegen „leer", und der Kommentar sagt, **warum** die erste Fassung nie feuern konnte (Spitze hat selbst `id >= up_to_id + 1`). `tests/test_projection_worker.py:300-325` schmiedet die Lücke mit rohem SQL und prüft, dass nichts darüber hinweg wandert. Das ist der Fund, den die Aufgabe-5-Prüfung erzwungen hat, und er ist richtig eingebaut.
- Die drei Zusicherungsschichten aus Spec §5 stehen als Schichten im Baum und decken einander nicht: `tests/test_projection_derive.py` (9 reine Tests, ohne `db`-Marker) für die Arithmetik, die festgenagelte Zeile `tests/test_projection_worker.py:128` (`stats_row[3] == NOW - 5 Tage`) für dieselbe Arithmetik Ende-zu-Ende, `assert incremental == rebuilt` plus die Hypothesis-Eigenschaft für den Ein-Weg-Fehler. `docs/explanation/projections.md:111-148` trägt genau diese Aufteilung mit ihren Messungen — nachgemessen, die Mutation `first_seen=addition.first_seen` lässt `tests/test_projection_worker.py` grün (12 passed) und fällt in `test_merge_adds_counts_and_keeps_the_extremes`, wie die Seite behauptet.
- `_FailingStore` in `tests/test_projection_worker.py:172-207` ist die versprochene Dividende des Protokolls: ein Wrapper ohne Mock, gegen echtes PostgreSQL, der die tragende Invariante (Zeilen und `up_to_id` in einer Transaktion) wirklich bricht. Die Zahlen der Seite (`up_to_id 4`, höchste `event_id` 4, 8 Zeilen, Folgelauf 6 Events bis 10) sind die Zahlen der Assertion, Zeichen für Zeichen.
- `.importlinter` ist **kürzer** geworden: beide `ignore_imports`-Blöcke sind ersatzlos weg, `lint-imports` meldet vier Verträge KEPT ohne jede Klammer, und `test_the_exempted_core_modules_load_no_sql_at_runtime` ist gelöscht — Abnahmebedingung §9/1 eingelöst und am Torprotokoll messbar.
- `docs/explanation/module-boundaries.md:43-59` — die vier `grep`-Blöcke habe ich nachgefahren, sie reproduzieren **wörtlich**; „sechs von sechs Kanten" stimmt, und die letzte Zeile (`contract` importiert nur sich selbst) ist das Fundament der Schichtung als Messung.
- `docs/explanation/design-records.md` rechnet sauber: 12 + 2 + 2 + 56 = 72, und die Teilmengen sind nachmessbar — Basis `cdc508a` hat 14 `§` in `src/tests/migrations`, HEAD hat 15, davon 3 neue (alle Architektur: `contract/store.py:66` §4.4, `storage/schema.py:132` §4.4, `storage/schema.py:173` §4.1), also 12 alte. „Kein Zeile zeigt auf den Spec der eigenen Stufe" habe ich bestätigt.
- Der abgetippte Testblock im Tutorial stimmt vollständig: `collected 232 items`, `232 passed` **und alle 18 Dateizahlen** gegen `--collect-only` nachgemessen identisch. Das ist die Form, die `test_docs_typed_output.py` gerade **nicht** erzwingt (es hält nur `N passed`) — hier wurde über die Pflicht hinaus gemessen.
- Fehlerführung und Rückgabecodes sind konsequent: `--limit < 1` und `--since` ohne Zone gehen durch `InvalidPayload` und damit über `main`s eine `except`-Verzweigung auf 2 statt über `parser.error()` auf einen Prozessabbruch; der Kommentar `cli.py:239-253` nennt beide Messungen, die das begründen, und ich habe sie am Code nachvollzogen.
- Alle 25 Commits tragen `Assisted-By:`, kein einziges `Co-Authored-By:` oder „Generated with" (nachgezählt: 25/25, 0).
- `CLAUDE.md`s Suppressions-Liste ist korrekt nachgezogen: fünf `# noqa`-Zeilen im Baum gemessen (A001, C901, S607, DTZ001 ×2), `S603` ist mit dem Test gefallen, und die Regel „Entfernen zählt auch" steht jetzt dort.
- Die Vorhersage aus Spec §8, das Vokabular brauche `upsert`, wurde **gemessen und verworfen**: `upsert` kommt in keiner Doku-Seite vor, `.vale.ini` und `.vale-styles/` sind unverändert, `vale` grün.

## Gates run

| Tor | Ergebnis |
|---|---|
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `48 files already formatted` |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` (vier Namen KEPT, **keine** `ignored imports`) |
| `uv run pytest --cov --cov-report=term-missing` | `232 passed in 21.79s`, `Total coverage: 97.32%` |
| `make -C docs html` | `build succeeded.` |
| `make -C docs vale` | `0 errors, 0 warnings and 0 suggestions in 22 files.` |
| `make -C docs linkcheck` | **nicht gefahren** (Netz, laut Auftrag ausgeschlossen) |

Zusatzmessungen: `pytest --collect-only -q` → `232 tests collected`; `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` → `Found 19 errors`; `ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' src/previously/cli.py` → `main … (2 > 1)`.

## Issues

### Critical (Must Fix)

Keine. Keine falschen oder verlorenen Daten gefunden, kein lügendes Tor.

### Important (Should Fix)

**I-1 — `source` und `external_id` gehen unentschärft in einen tabgetrennten Strom.**
`src/previously/cli.py:270-274` und `:298-302`: `escape_field` wird nur auf `row.content` angewandt. `source` und `external_id` werden roh gedruckt, und `core/append.py:193-200` (`_check_identity`) lehnt nur Null-Byte und einsame Surrogate ab — ein Tab oder ein Umbruch in `--source`/`--external-id` ist über die Kommandozeile erreichbar und wird gespeichert. Folge: `previously chronicle` druckt dann **sieben** Felder statt sechs oder bricht eine Zeile in zwei, `previously stats` entsprechend. `docs/reference/cli.md:98` („Each line holds six tab-separated fields") und `:131` sind damit unter erreichbarer Eingabe falsch, und die Zusicherung „eine Zeile ist eine Einheit" aus Spec §6.3 — der ganze Grund, warum `escape_field` existiert — fällt an der Stelle, an der sie niemand geprüft hat. Bei einem Umbruch in `source` druckt `chronicle` außerdem mehr Zeilen als `--limit` erlaubt, ohne Kappungshinweis. Fix: `escape_field` auch auf `source` und `external_id` (beide Kommandos), `cli.md` sagt „in jedem Feld" statt „in `content`", und ein Testfall mit Tab in `--source`.

**I-2 — „Spitze und `up_to_id` in einer Transaktion" liefert unter READ COMMITTED nicht, was die Begründung behauptet.**
`src/previously/storage/postgres.py:96-98` setzt die Isolationsstufe **ausdrücklich** auf `READ COMMITTED` (zu Recht, wegen des Anfüge-Verfahrens). Unter READ COMMITTED bekommt in PostgreSQL *jede Anweisung* einen eigenen Snapshot. `cli.py:264-265` und `:295-296` lesen `tip` und `projection_state` als **zwei** Anweisungen; sie liegen in einer Transaktion, aber nicht in einem Zeitpunkt. Spec §6.5 und `docs/explanation/projections.md:182` begründen das Verfahren aber genau damit: „two transactions give a difference between two moments — a number that was never true at any single moment". Der Buchstabe ist erfüllt, die Begründung nicht. Praktische Gefahr ist klein (bei monotonem Log und monotonem `up_to_id` bleibt das Schweigen ehrlich), aber die Zusicherung auf einer **lebenden** Seite ist so nicht wahr. Fix: entweder beide Zahlen in **einer** SQL-Anweisung lesen (Skalar-Unterabfrage), oder die Leseverbindung mit `REPEATABLE READ` öffnen, oder — das wäre auch ehrlich — den Satz abschwächen. Hinweis an den Betreuer: dieselbe Denkfigur steht vorbestehend in `postgres.py:203-214` über `verify` („hundreds of different snapshots instead of one"); ich bewerte sie nicht, nenne sie aber, weil der Zweig sie nicht erfunden hat.

**I-3 — `tests/test_projection_worker.py:104` behauptet „all nine tests in this file", die Datei hat zwölf.**
Gemessen: bei `49086f8` (Aufgabe 5) hatte die Datei 9 Tests, die Fixrunde `f2687a6` hat drei hinzugefügt, HEAD hat 12 (`--collect-only`: 12). Ich habe die Mutation gefahren, von der der Satz spricht (`first_seen=addition.first_seen`): **`12 passed`**. Die Aussage ist inhaltlich richtig und die Zahl um drei veraltet. `docs/explanation/projections.md:158` wurde korrekt auf 12 nachgezogen („both version tests red … the other ten green"), der Docstring nicht — Seite und Docstring widersprechen sich jetzt über dieselbe Datei. Genau der Fall aus *A comment is a claim*. Fix: „twelve".

**I-4 — `docs/explanation/module-boundaries.md:179` sagt „(40 today)", gemessen sind 48.**
Die Basis `cdc508a` schrieb `39 files already formatted` ohne Klammer; dieser Zweig hat „(40 today)" und `:192` („The file count went from 39 to 40 with `contract/store.py`") ergänzt — wahr am Ende von Aufgabe 1, falsch ab Aufgabe 2. `ruff format --check .` bei HEAD: **48**. Stage 1b legt neun Python-Dateien dazu (39 + 9 = 48, die Umbenennung `storage/rows.py` → `contract/rows.py` ist netto null). Kein Tor erreicht die Zahl.

**I-5 — `docs/explanation/module-boundaries.md:191` sagt, `193` stehe auch im heutigen Testlauf.**
Der heutige Lauf ist `232 passed`. Der Satz („`193` reads the same here and in today's test run for a reason rather than by accident") war am Ende von Aufgabe 1 wahr und ist seit Aufgabe 2 falsch; der Absatz davor sagt zugleich, die fünfte Zeile trage eine Zahl, „die sich bewegt hat" — er widerlegt sich selbst. Fix: entweder den Block als datierte Messung stehen lassen und die Gegenwartsaussagen (I-4, I-5) herausnehmen, oder beide Zahlen neu tippen. Ich empfehle das erste: der Block ist ausdrücklich „Measured … on 2026-10-03" und soll historisch sein.

**I-6 — die Ruling-Erhebung, auf der Ruling T8-c steht, hat `.importlinter` nicht gesehen — und dort steht der schädlichste Zeiger.**
Meine Zählung über `src tests migrations pyproject.toml .importlinter`: **17** Vorkommen, nicht 16. Das 17. ist `.importlinter:51` („see there for the reasoning, ruling T8-c") — ein unqualifiziertes Label, das mit dem **eigenen** T8-c dieses Plans kollidiert. Schlimmer ist `.importlinter:30-31`, von diesem Zweig neu geschrieben: „(rulings T7-a and T8-c of stage 1a, in `docs/superpowers/sdd/`)". Nachgemessen in `docs/superpowers/sdd/2026-10-03-dokumentation/progress.md`: `Ruling T7-a` existiert dort — als **andere** Entscheidung (drei Klassen von Verweis), `Ruling T8-c` existiert dort gar nicht. Ein Leser, der dem Zeiger folgt, landet begründet bei der falschen Entscheidung. Das ist strikt schlechter als ein Label ohne Zeiger. Fix: beide Stellen in `.importlinter` in die Fixwelle aufnehmen (Plan-Datum nennen oder den Verzeichnis-Zeiger streichen), und die Erhebungs-Kommandozeile in `CLAUDE.md` so aufnehmen, wie es dort für `W`/`G`/`B`/`K`/`N` schon steht — als Befehl, nicht als Zahl.

**I-7 — der eingefrorene Spec zitiert einen Pfad, den der Baum bei HEAD nicht hat.**
`docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md:727` nennt `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md` als Quelle für F11/F9/F12 im Wortlaut. `ls docs/superpowers/sdd/` bei HEAD: nur `2026-10-03-dokumentation`. Der Schlussschritt T6-c soll das liefern; solange er nicht gelaufen ist, zeigt ein **eingefrorener** Spec ins Leere, und nichts fängt das — `conf.py` schließt `superpowers/**` aus, also sieht `linkcheck` die Stelle nie. Auch Ruling T8-a hängt daran (A8-Bedenken 2 sagt das). Vor dem Merge liefern.

### Minor (Nice to Have)

- `docs/reference/cli.md:111-115` — der Block listet die Rückstandszeile **vor** der Kappungszeile, `cli.py:278-285` druckt die Kappung zuerst. Kein Test lässt beide Hinweise zusammen feuern, also hält das nichts. Zwei Zeilen tauschen oder die Reihenfolge ausdrücklich nennen.
- `docs/reference/cli.md:17` — die Spalte „2" für `project` sagt nur „Storage raised an error". `ProjectionGap` ist ein `PreviouslyError` aus `core` und endet ebenfalls auf 2.
- `docs/reference/database-schema.md:122-124` — `speaker`/`start_ms`/`end_ms` von `p_chronicle` tragen „always `NULL` in stage 1a". `p_chronicle` existiert in Stufe 1a nicht. Der Satz ist aus der `unit`-Tabelle (`:64-66`) übernommen. „until stage 2" wäre richtig.
- `.importlinter:57` — der Vertragsname `No vendor SDK in stage 1a` wird vom Tor **gedruckt** und ist jetzt veraltet: der Vertrag gilt für das ganze Paket, und 1b liegt im Baum. In Plan und Hauptbuch kommt er nicht vor, ist also niemandem aufgefallen.
- `.importlinter:38` — das neue `{ref}`module-boundaries`` löst heute auf, aber `tests/test_docs_references.py` liest nur `*.py` unter `src/tests/migrations`; `.importlinter` liegt außerhalb jeder Sichtweite. Entweder die Dateiliste des Tests erweitern oder als offenen Punkt notieren.
- Sieben Stellen tragen dasselbe `TRUNCATE p_source_stats, p_chronicle, projection_state, source_key, unit, event` (`tests/conftest.py`, `tests/test_properties.py` ×5, `tests/test_projection_worker.py:409`). Eine vierte Projektion heißt sieben Änderungen; eine Konstante in `conftest.py` wäre DRY ohne verfrühte Abstraktion.
- `src/previously/cli.py:265` und `:296` tippen `"chronicle"` und `"source-stats"` als Literale, obwohl `CHRONICLE.name`/`SOURCE_STATS.name` öffentlich sind. Ein Umbenennen würde den Rückstand still auf „ganzes Log" setzen — `test_both_reading_commands_report_the_lag_on_stderr_and_only_there` fängt es heute, darum nur Minor.
- `src/previously/cli.py:269` — `limit=args.limit + 1`: bei `--limit 9223372036854775807` übersteigt `limit + 1` `bigint`, der Treiber wirft, und man bekommt einen Traceback mit Rückgabecode 1 statt 2 — dieselbe Klasse wie der gerade behobene `--limit -2`. Eine Obergrenze im Riegel eine Zeile darüber kostet nichts.
- `src/previously/core/projection/worker.py:147` — die Meldung formatiert eine Liste in den Text (`expected events [5].. above id 4`). `expected[0]` wäre lesbarer.
- `docs/how-to/rebuild-a-projection.md:15` und `:20` sagen zweimal dasselbe („each command reports the lag of the projection it read" / „of its own projection").

## Deferred items (Rückstandsliste, Stand nach Aufgabe 8)

Zuerst die Bestätigung des Erledigten: `docs/reference/database-schema.md:5-7` nennt sechs Tabellen in zwei Gruppen (T7-b ✅), `tests/test_schema.py:348` heißt `test_the_projection_tables_exist` ✅, README nennt „the seven commands" und die vier Bereiche unter *What it does not do* ✅, `docs/index.md:24` nennt „rebuild a projection" ✅, der `warning`-Text im How-to ist Prosa in `:::{warning}` ✅ (und sachlich richtig: `catch_up` leert in der ersten Transaktion und füllt stapelweise, wie `:68` behauptet), Tutorial-Überschrift/Einleitung/Next-steps nachgezogen ✅, Spec §10 Punkt 8 plus zwei Notizen vorhanden ✅ (T8-a — aber siehe I-7), README nennt vier eingefrorene Berichte ✅, Tutorial mit 232 neu getippt und **alle** Dateizahlen nachgemessen ✅, „exactly one upgrade step" → zwei Schritte ✅.

1. `tests/test_cli.py:504` `ruling P-1` qualifizieren — **vor dem Merge**. Es ist das einzige 1b-Zitat und der ganze Zweck von T8-c; Kosten: eine Zeile. **Erweitern** um `.importlinter:30-31` und `:51` (I-6), die die Erhebung übersehen hat.
2. `CLAUDE.md`, drei Stellen — **vor dem Merge**, (a) und (b) dem Betreuer vorlegen wie geplant. (c) ist nicht verhandelbar: `CLAUDE.md:72` sagt „the three frozen records … not a rule against writing a fourth", und der vierte liegt seit `fee6d2b` im Baum — der Zweig macht seine eigene Regeldatei falsch. Zu (b) siehe meine Messung unten.
3. `catch_up`-Docstring nennt den `batch_size`-Riegel nicht — **vor dem Merge**. Ein Satz, und der Docstring erklärt `batch_size` zwei Absätze weiter oben schon; die Stelle, an der ein Aufrufer liest, ist die einzige, die den Riegel verschweigt.
4. `log --limit < 1` — **vor dem Merge** (knapp). Gemessen am Code: `cli.py:327` hat keinen Riegel, `log --limit -2` läuft in `LIMIT -1` und damit in Treiber-Traceback mit Rückgabecode 1, während `chronicle --limit -2` eine Zeile und 2 liefert. Zwei Kommandos, dieselbe Option, zwei Fehlerformen — und `cli.md:43` sagt bei `log` nichts von „at least 1", bei `chronicle:97` doch. Drei Zeilen plus eine Zusicherung im bestehenden `log`-Test. Wenn die Fixwelle eng wird: **später** vertretbar, dann aber in die offenen Punkte der nächsten Stufe, denn Spec §10 ist eingefroren und trägt es nicht.
5. Test `set(sub.choices) == set(commands)` — **später**. Bestätigt offen (kein solcher Test in `tests/`). Der Fehler, den er fängt, braucht einen neuen Subparser **und** einen vergessenen Tabelleneintrag zwölf Zeilen darunter in derselben Datei; der Preis ist der erneut abzutippende Tutorial-Block (T6-f), und das ist der teure Teil. Mit der nächsten Änderung an `main` nachholen. (Die verwandte Lücke bei `PostgresStorage._PROJECTION_TABLES` ist **keine**: `_project_all` ruft `catch_up` für beide registrierten Projektionen, und der Erstbau geht durch `truncate_projection` — eine dritte Projektion ohne Tabelleneintrag lässt mehrere Worker-Tests fallen.)
6. stderr-Literale in `cli.md` nicht gegen den Code gehalten — **später**, aber ausdrücklich notieren, denn der Punkt hat jetzt einen zweiten Fall: nicht nur der Wortlaut, auch die **Reihenfolge** der zwei Hinweise ist unbewacht und falsch dokumentiert (Minor oben). `test_the_reference_quotes_what_the_code_actually_prints` liest nur die *Payload range*-Tabelle, nachgelesen in `tests/test_docs_references.py:213-226`.
7. Seitenlängen — **streichen**, gemessen: `module-boundaries.md` 279 Zeilen, `projections.md` 216, aber `hash-chain.md` 321. 279 ist kein Ausreißer, und beide Seiten bleiben in einem Quadranten. **Nicht** gestrichen ist der verwandte Teil: `module-boundaries.md:175-192` ist genau der Block, in dem zwei veraltete Zahlen leben (I-4, I-5). Das ist eine Messfrage, keine Längenfrage.
8. Berichtsformulierung „26 → 35 Tests" — **streichen** ✅ nichts im Baum.

## Urteil über die zwei Vorlagen des Controllers

**Ruling T8-c (Label-Namensraum je Plan).** Richtig in der Sache, aber in der Reichweite zu schmal, und zwar aus einem messbaren Grund: die Erhebung lief über `src tests pyproject.toml` und hat `.importlinter` ausgelassen — dort stehen das 17. Zitat und ein neu geschriebener Zeiger, der auf die **falsche** Entscheidung auflöst (I-6). „Die 15 alten bleiben, wer sie anfasst, qualifiziert sie" halte ich für richtig — mit einer Ausnahme: `.importlinter:30-31` hat dieser Zweig angefasst, also fällt es unter die eigene Regel. Zwei Zusätze zum CLAUDE.md-Satz: er soll sagen, dass ein Zitat das **Datum** des Plans nennt (das Verzeichnis heißt nach dem Datum), und er soll die Erhebungs-Kommandozeile mitbringen statt einer Zahl — dieselbe Lehre, die `CLAUDE.md` für `W3`/`W-3` schon gezogen hat („ein Count ohne Verfahren daneben ist keine Behauptung, die jemand prüfen kann").

**Ruling T8-d (das eingefrorene 2026-10-03-Protokoll bleibt, `CLAUDE.md` bekommt den gemessenen Stand).** Richtig, und aus dem Grund, den sein eigener Kopf nennt: „absichtlich unverändert". Zwei Schärfungen, beide nachgemessen. Erstens ist die Übertreibung größer als eine Zahl: `docs/superpowers/sdd/2026-10-03-dokumentation/index.md:28` gibt eine **Arbeitsanweisung** — „such dort nach `Ruling T6-b`" — und `Ruling T6-b` steht in jenem `progress.md` **nicht** (gemessen: 0 Treffer). Wer der Anweisung folgt, schließt, er habe das falsche Protokoll. Von den zehn im Baum zitierten Labels löst dort genau eines auf (`T5-b`); `T2-e`, `T6-b`, `T8-a`, `T9-a`, `T9-c`, `T10-a`…`T10-d` nicht — deine Messung bestätigt. Zweitens soll der CLAUDE.md-Text das 1a-Hauptbuch als **verloren** benennen, nicht als abwesend, sonst sucht der nächste Leser eine Datei, die nicht mehr herstellbar ist. Und `CLAUDE.md:364` („`progress.md` … holds every `Ruling …` of that execution") ist als allgemeine Aussage über die Zitate falsch, auch wenn sie für *dieses* Hauptbuch zutrifft — die Fixwelle soll beides trennen.

## Declined to judge

- Spec §10 Punkt 1, der äußere Anker — ausdrückliche Zusage des Betreuers, ausdrücklich nicht in 1b.
- Spec §10 Punkt 2 und 3 (Tilgung tilgt Einheiten nicht; `show` druckt roh) — vom Spec §1.1/§6 begründet aus 1b herausgehalten; der Pin `test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` existiert und greift.
- Spec §10 Punkt 4, die Warteschlange — auf Stufe 2 vertagt.
- Spec §10 Punkt 8 / Prüfbefund F11, keine Sperre auf `projection_state` — mit drei durchgerechneten Richtungen vertagt; ich habe die Entscheidung nicht neu aufgerollt.
- Prüfbefund F9 (`Projection.write` könnte eine eigene Transaktion nehmen) und F12 (`version` ohne `CHECK (version > 0)`) — als Notizen unter §10 vertagt; ich habe beide am Code bestätigt (das Typsystem verhindert F9 nicht; `_describe` würde eine 0 in der Spalte als Erstbau melden) und bewerte sie nicht.
- Spec §10 Punkt 5, die drei geparkten Testlöcher am Doku-Tor — aus der vorigen Ausführung übernommen.
- Spec §10 Punkt 6 und 7 (Projektzuordnung, `stats` ohne Zeitraum) — bewusste Begrenzungen.
- Das vorbestehende „one snapshot"-Argument in `storage/postgres.py:203-214` über `verify` — dieselbe Denkfigur wie I-2, aber älter als dieser Zweig; nur als Kontext genannt.
- Die 1a-Spec mit `Status: zur Abnahme` unter eingefrorenem Kopf (T8-b) — bereits entschieden, dem Betreuer als Beobachtung vorgelegt.
- Commit-Botschaften und Vermischungen früherer Commits dieses Zweigs (T5-g, T6-d) — History, bereits beurteilt.
- Deutsche Ausdrucksqualität von Spec, Plan und Hauptbuch jenseits der Tatsachen, die sie behaupten.
- Fehlende Tests auf die dokumentierten Constraint-Namen (`p_chronicle_event_id_fkey` usw.) — ich habe sie gegen PostgreSQLs Vergabeschema geprüft und für richtig befunden; dass sie kein Test hält, ist ein vorbestehendes Muster (auch 1a hält nur Indexnamen, über `test_the_declared_indexes_exist_in_the_migrated_database`, das den neuen `p_chronicle_occurred_idx` aus den Metadaten mit abdeckt).
- Kein Downgrade-Test für `0002_projections` — `0001_log` hat auch keinen; vorbestehendes Muster.

## Recommendations

1. Eine Fixwelle, ein Dispatch, Reihenfolge: I-7 (Schlussschritt T6-c, sonst zeigt ein eingefrorener Spec ins Leere) → I-6 plus Rückstandspunkt 1 und 2 (Labels und `CLAUDE.md`, dem Betreuer vorlegen) → I-1 (Entschärfung aller Felder, mit Test) → I-2 (eine Anweisung oder `REPEATABLE READ` oder Satz abschwächen) → I-3/I-4/I-5 (drei Zahlen) → Rückstandspunkte 3 und 4 → die Minors.
2. Wenn I-1 oder Rückstandspunkt 4 oder 5 einen Test dazulegen, ändert sich die Testzahl — dann **zuletzt** den Tutorial-Block erneut aus einem echten Lauf tippen, wie T6-f es vorsieht, und die Dateizahlen mit. `test_docs_typed_output` hält nur `N passed`, der Rest hängt an der Disziplin.
3. Der Dispatch dieser Fixwelle nennt alle sechs Tore wörtlich. Mein eigener Auftrag zählte „die billigen vier" plus `pytest` plus `html`/`vale` auf und schloss `linkcheck` aus — das war begründet, aber genau die Form, die am 2026-10-03 einen roten `pyright` durch zwei Prüfungen gelassen hat. Die Fixwelle braucht den vollen Block, `linkcheck` eingeschlossen.
4. `CLAUDE.md` soll die Ruling-Erhebung als **Kommandozeile** bekommen, mit `.importlinter` und `pyproject.toml` in der Pfadliste — sonst wiederholt sich I-6 bei der nächsten Stufe.
5. Für die nächste Stufe vormerken, was Spec §10 eingefroren nicht mehr aufnehmen kann: `log --limit`-Riegel (falls jetzt nicht behoben), der Subkommando-Tabellentest, die unbewachten stderr-Literale samt ihrer Reihenfolge, und — neu aus dieser Prüfung — die Frage aus I-2, welche Isolationsstufe eine Lesezusicherung eigentlich braucht.

## Assessment

**Ready to merge?** With fixes

**Reasoning:** Die Substanz steht: alle vierzehn Abnahmebedingungen aus Spec §9 sind am Baum belegbar, die Zusage „ableitbar und wegwerfbar" hält durch drei Schichten, die ich einzeln nachgemessen habe, die beiden Ausnahmen in `.importlinter` sind ersatzlos gefallen, und sieben von acht Toren laufen grün (`linkcheck` laut Auftrag nicht gefahren). Was fehlt, ist kein Datenfehler, sondern eine Schicht von Behauptungen, die der Baum widerlegt — drei veraltete Zahlen, ein Zeiger, der begründet auf die falsche Entscheidung auflöst, ein eingefrorener Spec, der auf eine noch nicht ausgelieferte Datei zeigt — plus zwei echte Verhaltenslücken (unentschärfte Felder im Strom, und eine Transaktionszusicherung, die READ COMMITTED nicht gibt). Alles davon ist in einer Fixwelle erreichbar; I-7 und Rückstandspunkt 2c müssen darin sein, weil der Zweig sonst mit einem toten Zitat im eingefrorenen Bericht und einer falschen Zeile in seiner eigenen Regeldatei auf `main` landet.
