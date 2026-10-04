# Task 8 — Bericht: Einfrieren, Design-Records, README, Tutorial zuletzt

Commit `fee6d2b` auf `worktree-stufe-1b-projektionen`, Arbeitsbaum sauber.
Vorgänger `af5f5de`. Alle sechs Tore grün, Vale 0 Fehler in 22 Dateien,
`pytest` 232 passed (gemessen, nicht angenommen).

Vier Dateien geändert, genau die aus dem Dispatch:
`docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`,
`docs/explanation/design-records.md`,
`docs/tutorials/record-your-first-event.md`, `README.md`.
`git status --short` vor dem `git add` zeigte genau diese vier und sonst
nichts.

## 1. Der Spec friert ein

### Kopf

Der Kopfblock wörtlich aus `2026-10-02-stufe-1a-log.md` übernommen, Datum
`2026-10-04` (Datum dieses Commits). Er steht zwischen Titel und `Stand:`-Zeile,
wie im 1a-Spec.

`Stand: 2026-10-04 · Status: Entwurf, zur Abnahme` → `Stand: 2026-10-04 ·
Status: eingefroren`.

Der Absatz „Dieser Spec entsteht auf Deutsch … Bis dahin ist er das maßgebliche
Dokument für 1b." ist gestrichen.

**Folgefehler, in der Selbstprüfung gefunden und in derselben Commit-Fassung
behoben** (der Commit wurde dafür einmal amendiert, `872b54e` → `fee6d2b`):
der nächste Absatz begann mit „**Er** argumentiert aus der Architektur …" und
sein Bezugswort stand in genau dem gestrichenen Absatz. Jetzt: „Dieser Spec
argumentiert aus der Architektur …", Zeile neu umbrochen.

Die 1a-Spec ist **nicht** angefasst (Ruling T8-b), obwohl ihre `Stand:`-Zeile
unter dem eingefrorenen Kopf noch „Status: zur Abnahme" sagt.

### §10 „Was offen bleibt"

Einleitung von Präsens auf die Vergangenheit des Abschnitts umgeschrieben: der
Abschnitt war gepflegt, solange der Spec lebte, verliert mit dem Einfrieren
seine Pflege, und was hier steht, ist nicht abgearbeitet, sondern
weitergegeben — in den Spec der nächsten Stufe, und der äußere Anker dort nach
oben, weil er eine ausdrückliche Zusage ist und keine Vertagung.

Zweiter Absatz, neu: Punkt 8 und die zwei Notizen kamen beim Einfrieren dazu,
„aus den Prüfbefunden F11, F9 und F12 der Prüfung von Aufgabe 5 dieses Plans".
Die Labels tragen also ihre Herkunft im gleichen Satz, damit niemand sie in
den zwei älteren Nummernräumen (`W2`, `G-7`) sucht. Der Ort zum Nachsehen
steht als Pfad in Prosa, nicht als Link:
`docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`.

Die sieben Punkte sind unverändert, der Anker bleibt Punkt 1. Neu:

- **Punkt 8 (F11):** keine Sperre auf der Zustandszeile. Zwei gleichzeitige
  `catch_up`-Läufe kommen beide durch die Versionsprüfung, das Ergebnis zählt
  unter; heute kann sie niemand starten (Kommando, keine Warteschlange, Punkt
  4); die Sperre gehört in denselben Schritt, der die Warteschlange baut, als
  `SELECT … FOR UPDATE` auf die Zustandszeile oder Advisory-Lock je Projektion.
  Letzter Satz nennt die Falle: wer die Warteschlange ohne eins von beiden
  baut, öffnet den Weg.
- **Zwei Notizen darunter** (Ruling T8-a: „F9 und F12 Notizen darunter"), mit
  einem Satz, warum sie keinen eigenen Punkt bekommen (heute kein Weg dorthin)
  und wann sie fällig sind (bevor eine dritte Projektion dazukommt):
  - **F9:** `Projection.write` bekommt die Verbindung des Aufrufers und könnte
    über `store.begin()` eine zweite daneben öffnen; dann hält die tragende
    Invariante aus **§4.1** nicht mehr (Zeilen und `up_to_id` in derselben
    Transaktion — Absatzangabe gegen den Spec geprüft, §4.1, nicht §4.3).
    Handlungsanweisung: in die Typen tragen, oder einen Test, der eine
    Projektion mit eigener Transaktion durchfallen lässt.
  - **F12:** `projection_state.version` ohne `CHECK (version > 0)`; der
    Arbeiter liest `rebuilt_from == 0` als „es gab nichts", eine 0 in der
    Spalte wäre also als Erstbau gemeldet. Handlungsanweisung: `CHECK`, oder
    `rebuilt_from` bekommt eine Form, die „nichts" nicht als Zahl ausdrückt.

Die stderr-Satz-Lücke ist **nicht** in §10 (Ruling T8-a).

## 2. `design-records.md`

### Die Messung zuerst

```
$ grep -rn "§" src/previously/core/projection src/previously/contract/store.py src/previously/contract/rows.py
src/previously/contract/store.py:66:    (architecture §4.4, frozen design record) stays a type and not a
```

**Ein** Treffer, mit `(frozen design record)` auf derselben Zeile, und er
zeigt auf die **Architektur**. Je Datei gezählt
(`grep -rc`): `store.py` 1, `rows.py` 0, `core/projection/__init__.py` 0,
`chronicle.py` 0, `source_stats.py` 0, `worker.py` 0. **Null** Verweise auf
den 1b-Spec. Die Vorbereitungsmessung des Controllers ist damit reproduziert.

### Was auf der Seite steht

- **Eröffnung:** „Three German documents" → „Four …", mit dem 1b-Spec
  benannt; „The first three froze on 2026-10-03, the stage 1b specification on
  2026-10-04". Der Satz danach („Until this documentation existed, those
  **first three** documents were the only place …") musste mit, sonst hätte er
  den 1b-Spec mitgezählt, für den er nicht gilt.
- **Abschnitt „Freezing is a step in a procedure":** der Satz „not as a rule
  against writing a **fourth**" war mit diesem Commit überholt, weil der
  vierte existiert → „not as a rule against writing the next one". Darunter
  drei neue Zeilen: Stufe 1b als erster Durchlauf des Ablaufs, Datum
  2026-10-04, Thema Projektionen, die Seiten, die die Begründung tragen
  (`{ref}`projections``, `{ref}`module-boundaries``), und die zwei
  Reference-Seiten, die die Fakten übernommen haben (`{ref}`database-schema``,
  `{ref}`cli-reference``) — drei Tabellen und drei Kommandos, beides gegen
  `database-schema.md` und `cli.md` geprüft.
- **Abbildungstabelle:** keine neue Zeile, sondern vier Zeilen darunter, die
  sagen, warum keine da ist: die Messung oben, „Not one line points at the
  specification of its own stage", und der Satz, den die Beauftragung
  verlangt — erste Stufe, deren Code nie auf den Spec zeigte, weil die Seiten
  im selben Pull Request wie der Code entstanden, und
  `test_no_bare_paragraph_references_remain` in `tests/test_docs_references.py`
  macht aus der Gewohnheit ein Tor, indem es ein unmarkiertes `§` verweigert
  (Testname gegen die Datei geprüft).
- **Kein Link** auf `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/`
  von dieser Seite (Verzeichnis existiert noch nicht, `html` wertet den toten
  Link als Fehler).

## 3. `README.md`

Die Beauftragung listet den README nicht, der Dispatch schon (Fund des
A7-Prüfers). „The **three** specifications below are frozen design records" →
„**four**", plus ein halber Satz am Absatzende: „— stage 1b is the first one
that went that way from the start." Neue Tabellenzeile zwischen Stage 1a und
Execution records, mit Datum 2026-10-04, Thema (zwei abgeleitete Tabellen,
Arbeiter, drei Kommandos) und den zwei Seiten, die die Begründung tragen. Der
Linktext „About derived views" ist der **echte** Titel von
`docs/explanation/projections.md` — „About the projections" war mein erster
Entwurf und wäre falsch gewesen.

## 4. Das Tutorial

### Der echte Lauf, aus dem jeder Block abgetippt ist

Frischer Clone `/tmp/previously-task8-fresh` (Branch-Stand `af5f5de`), frischer
Container nach dem `docker run` des Tutorials selbst, Port 5432,
`PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5432/previously`.
Container und Clone sind nach dem Lauf entfernt. Rohes Protokoll, Kommando für
Kommando:

```
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
INFO  [alembic.runtime.migration] Running upgrade 0001_log -> 0002_projections, Projections: state, chronicle, source statistics

$ uv run previously append --source email --external-id 2026-10-03-kickoff@example.org --text "…"
1

$ uv run previously log
1	2026-10-04T04:53:01.069903+00:00	observation	b97c59a1f2c3

$ uv run previously verify
chain intact

$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-04T04:53:01.069903+00:00
hash=b97c59a1f2c353abb0e96eb3e2858c7479798f7bd1fbb60c536256867011fcd7
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.

$ uv run previously project
chronicle       built: 1 event, up_to_id 1
source-stats    built: 1 event, up_to_id 1

$ uv run previously project
chronicle       up to date, up_to_id 1
source-stats    up to date, up_to_id 1

$ uv run previously chronicle
1	1	2026-10-04T04:53:01.069903+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-04T04:53:01.069903+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.

$ uv run previously stats
email	1	2	2026-10-04T04:53:01.069903+00:00	2026-10-04T04:53:01.069903+00:00
```

Die Vorhersage der Beauftragung ist **eingetroffen**: zwei Zeilen
`built: 1 event, up_to_id 1`, zweiter Lauf zweimal `up to date, up_to_id 1`,
zwei Chronikzeilen, eine Statistikzeile. Tabs und Leerzeichen sind mit
`cat -A` nachgesehen und die Blöcke per Skript aus den aufgefangenen Dateien
eingesetzt, damit kein Tab zu Leerzeichen wird; die `project`-Zeilen sind
leerzeichengefüllt (Name auf 15 Zeichen, dann ein Leerzeichen), nicht
tabuliert.

### Was auf der Seite geändert ist

1. **Einleitung (Z. 5):** nennt jetzt, was das Tutorial tut — Event
   aufschreiben, aus dem Log zurücklesen, Kette prüfen, die zwei abgeleiteten
   Sichten bauen, Chronik und Zählung je Quelle lesen, Testlauf. „look at the
   chronicle it produces" ist weg.
2. **Herkunftssatz (Z. 6):** siehe Abweichung 1 unten.
3. **`## Create the schema`:** der abgetippte Block zeigte **einen**
   Migrationsschritt und der Text sagte „exactly one upgrade step" — seit
   Migration `0002` (Aufgabe 2 dieses Plans) falsch, von keiner Aufgabe
   bemerkt. Jetzt zwei Zeilen und zwei Sätze: erster Schritt Log, Einheiten,
   Idempotenzschlüssel; zweiter Schritt drei Tabellen, je eine pro Sicht und
   eine für den Lesestand.
4. **`## Look at the chronicle` → `## Look at the log`** (die Sektion lässt
   `previously log` laufen; `chronicle` ist seit Aufgabe 6 ein eigenes
   Kommando). Die Ausgabezeile neu abgetippt.
5. **`## Look at the event in full`:** `occurred_at` und `hash` neu abgetippt,
   damit die Seite eine Sitzung bleibt (siehe Abweichung 2).
6. **Die Notiz unter dem `show`-Block:** „The hash on your screen won't match
   the one above." → „The hash **and the timestamps** on your screen won't
   match the ones above, here or in any block below." Ohne das hätte die Seite
   vier Blöcke mit Zeitstempeln, die beim Leser anders aussehen, und nur den
   Hash erklärt. Zahl der Admonitions unverändert (eine).
7. **Drei neue Abschnitte** nach `## Look at the event in full` und vor
   `## Run the test suite`:
   - `## Build the derived views` — ein Satz Vorlauf, `project`, „Notice that
     both lines say `built` …", dann der zweite Lauf als eigener Block und
     „Notice that both lines now say `up to date`" mit `up_to_id 1` erklärt.
   - `## Read the chronicle` — zwei Zeilen, „Notice that each line is one
     unit, and that each one carries `email` and the message identifier we
     passed to `append`. That source attribution is what makes this a
     chronicle and not a copy of `log`."
   - `## Count per source` — eine Zeile, „Notice that `email` stands at one
     event and two units, and that the two timestamps are the same moment …"
8. **`## Next steps`:** nennt die zwei gebauten Sichten mit, und eine Zeile
   mehr: „For why `log` and `chronicle` are two commands, see
   `{ref}`projections``."
9. **Testlauf zuletzt neu abgetippt**, siehe unten.

Stil nach `plone-doc-style:author` (Tutorial-Quadrant): „we" in der Einleitung,
Imperativ, „Notice that …", ein garantierter Weg, keine Erklärung — die
Begründung, warum es zwei Kommandos sind, steht als Verweis in „Next steps"
und nicht im Abschnitt. Ein Satz pro Zeile; meine ersten Fassungen waren
hart umbrochen und sind nachträglich entwickelt worden.

### Testzahl, gemessen

```
$ uv run pytest --collect-only -q -p no:randomly | tail -1
232 tests collected in 0.14s
```

232, wie der Plan vorhersagte — Aufgabe 7 hat die Zahl nicht verschoben. Der
Block ist aus einem echten `uv run pytest` neu abgetippt (`--randomly-seed=1705979683`,
`232 passed in 21.69s`), ohne die `rootdir:`-Zeile; das Skript prüft, dass die
Zeile wirklich entfernt wurde und dass im Block kein Maschinenpfad steht. Die
Dateireihenfolge und die Prozente sind die dieses Laufs, nicht die des alten
Blocks.

```
$ uv run pytest tests/test_docs_typed_output.py -v
tests/test_docs_typed_output.py::test_typed_test_counts_match_the_tree PASSED [100%]
============================== 1 passed in 0.77s ===============================
```

## 5. Die sechs Tore, Schlusszeilen wörtlich

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 48 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                           → 232 passed in 20.82s
                                             (Required test coverage of 90.0% reached. Total coverage: 97.32%)
make -C docs html                          → build succeeded.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded.
```

Das `pytest --cov` und die drei Doku-Tore sind **nach** der letzten Änderung
(Notiz in Punkt 6 oben, danach der amendierte Commit) noch einmal gelaufen;
`ruff`, `pyright` und `lint-imports` sehen `*.md` nicht, sind aber ebenfalls
nach allen Doku-Änderungen gelaufen.

## 6. Abweichungen von Beauftragung und Dispatch

1. **Der Herkunftssatz des Tutorials nennt keinen Pfad mehr.** Vorher: „it was
   typed against a real PostgreSQL 17, in a fresh checkout at
   `/tmp/previously-task3-fresh`." Jetzt: „it was typed in a fresh checkout,
   against a real PostgreSQL 17 in a container like the one below." Grund: der
   `uv sync`-Block stammt weiter aus der Sitzung von Aufgabe 3 des Doku-Plans,
   alles ab `alembic upgrade head` aus meiner. Ein Pfad im Satz hätte also für
   die halbe Seite gelogen. Den `uv sync`-Block mitabzutippen war die
   Alternative und ist verworfen: mein Lauf druckt dort zwei zusätzliche
   Zeilen, die den Clone-Pfad nennen (`Building previously @
   file:///tmp/previously-task8-fresh`), und die Seite sagt zwei Zeilen
   später, dass keine Ausgabe ein Verzeichnis nennt.
2. **Ich habe mehr abgetippt als die drei neuen Abschnitte und den Testlauf:**
   `alembic upgrade head`, `log`, `show`. Grund: `chronicle` und `stats`
   drucken den **Zeitstempel desselben Events**, das `log` und `show` oben
   zeigen. Wären die alten Blöcke stehen geblieben, stünde über derselben
   Event-`id` 1 oben `2026-10-03T15:41:19.888666+00:00` und unten
   `2026-10-04T04:53:01.069903+00:00` — eine Seite, die sich selbst
   widerspricht. Der Hash hängt über `recorded_at` am Lauf und zieht mit.
   `verify` druckt in beiden Läufen `chain intact`, der Block ist unverändert.
   Der Alternativweg (mein `append` mit `--occurred-at` auf den alten
   Zeitstempel) ist verworfen, weil die Seite dann ein Kommando zeigen würde,
   das ich nicht so gelaufen bin.
3. **Punkt 3 oben (`Create the schema`) ist ein Fund, keine Vorgabe.** Weder
   Beauftragung noch Dispatch nennen ihn; er ist beim echten Lauf aufgefallen
   und gehört in dieselbe Datei und denselben Commit.
4. **Die Notiz um „and the timestamps" erweitert** (Punkt 6 oben) — ebenfalls
   nicht vorgegeben, aber die Selbstprüfung „sieht ein Neuling das wirklich?"
   führt genau dorthin.
5. **Ein `{ref}`-Verweis mehr in „Next steps"** (`{ref}`projections``). Nicht
   vorgegeben; die Begründung, warum `log` und `chronicle` zwei Kommandos
   sind, gehört nicht ins Tutorial, der Verweis darauf schon.
6. **Der Commit wurde einmal amendiert** (`872b54e` → `fee6d2b`), weil die
   Selbstprüfung das hängende „Er" am Satzanfang nach dem gestrichenen Absatz
   fand. Kein zweiter Commit, weil die Aufgabe einen verlangt.

## 7. Bedenken

1. **`CLAUDE.md` zählt noch drei eingefrorene Berichte.** Zeile 72: „So the
   three frozen records are the output of a step and not a rule against
   writing a fourth." Mit diesem Commit sind es vier, und der vierte ist
   geschrieben — der Satz ist überholt, und zwar in genau dem Dokument, das
   die Regel aufstellt. Zeile 56 („until that day the three German
   specifications were the only place a reason was written down") bleibt
   richtig, weil sie Vergangenheit erzählt. `CLAUDE.md` steht nicht in meiner
   Dateiliste, also nicht angefasst: **Kandidat für die Fixwelle.**
2. **Der Pfad in §10 zeigt auf ein Verzeichnis, das noch nicht existiert.**
   `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md` kommt
   erst mit dem Abschluss-Commit des Controllers. Als Prosa-Pfad in einem
   Dokument außerhalb des Sphinx-Builds bricht das kein Tor (geprüft:
   `html`/`linkcheck` grün), aber wenn das Protokoll nicht ausgeliefert wird,
   ist die Angabe toter Text — und dann wäre auch Ruling T8-a („das Protokoll,
   das sie trägt, wird ausgeliefert") nicht eingelöst.
3. **Der `uv sync`-Block des Tutorials ist die letzte Zeile der Seite, die
   niemand nachmessen kann.** Er stammt aus einer Sitzung vom 2026-10-03 und
   nennt „Resolved 74 packages" — in meinem Lauf stand dieselbe Zahl, das ist
   also kein Fund, aber die Zeile „Installed 71 packages" und der Satz „uv
   then lists every one of the 71 packages" hängen an einer Auflösung, die
   `uv lock --upgrade` verschieben kann, ohne dass ein Tor es merkt. Kein
   Vorschlag für diese Aufgabe, nur notiert.
4. **Kein Bedenken, aber geprüft, weil ich es für eines hielt:** wer die drei
   neuen Abschnitte überspringt und `chronicle` vor `project` läuft, bekommt
   leere Ausgabe — aber nicht schweigend. `cli.py` Z. 283 und 303 setzen
   `up_to_id` auf 0, wenn keine Zustandszeile existiert
   (`0 if state is None else state.up_to_id`), also feuert `_lag_line` und
   druckt „projection is 1 event behind; run `previously project`" auf
   `stderr`. Gelesen, nicht gemessen — der Container war zu dem Zeitpunkt
   schon entfernt.


---

# Fixrunde 1 — Bericht

Commit `51c3cfb` auf `worktree-stufe-1b-projektionen`, Arbeitsbaum sauber.
Vorgänger `fee6d2b` (unverändert, die Historie bleibt wie sie ist). Fünf
Dateien: `docs/explanation/design-records.md`,
`docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`,
`docs/tutorials/record-your-first-event.md`, `README.md`, `tests/test_cli.py`.
`git status --short` vor dem `git add` zeigte genau diese fünf.

## I1 — zwei Testdocstrings zitierten den 1b-Spec

Bestätigt, und der Grep der Beauftragung konnte es nicht sehen: er lief über
`src/previously/core/projection`, `src/previously/contract/store.py` und
`src/previously/contract/rows.py`, die beiden Fundstellen liegen in
`tests/test_cli.py`. Nach Ruling T8-f:

- `tests/test_cli.py:478`: `"""Spec §6.3 (frozen design record) plus review
  focus 3: one unit is one line.` → `"""One unit is one line
  ({ref}`cli-reference`) plus review focus 3.`
- `tests/test_cli.py:591`: `"""Spec §6.2 (frozen design record): time order,
  not chain order.` → `"""Time order, not chain order ({ref}`projections`).`

Beide Label gegen die Seiten geprüft, nicht nur gegen das Tor: `cli.md:90`
sagt „Prints the chronicle in time order, one line per unit" und `cli.md:102`
trägt die Vier-Zeichen-Entschärfung (also §6.3), und `projections.md:160-174`
(„Two orders, two commands") trägt Zeit- gegen Kettenordnung (also §6.2). Kein
`§` mehr in `tests/test_cli.py`.

Der Satz auf `design-records.md` bleibt stehen, nennt jetzt aber den
gemessenen Bereich — `src/`, `tests/`, `migrations/`, derselbe, den
`tests/test_docs_references.py` abläuft — und sagt in einem Satz danach, was
vorher war: zwei Zitate, als `§6.2` und `§6.3`, mit der Markierung
`(frozen design record)`, während der Spec noch Entwurf war; Fixrunde 1 hat
sie auf die Seiten gezogen. **Die Messung auf der Seite gilt also nach dieser
Korrektur; vorher waren es zwei Treffer auf den eigenen Spec.** Die Botschaft
von `fee6d2b` trägt die alte Behauptung weiter, und das bleibt so — der
Fix-Commit sagt es in seinem eigenen Text.

## I2 — die zwei Architektur-Zeilen in der Abbildungstabelle

Die Vermutung des Dispatchs ist am Kommentar geprüft, nicht übernommen:

- `src/previously/storage/schema.py:173` (§4.1): „The primary key carries
  chain order; this index carries time order (architecture §4.1 … wants
  both)." → `{ref}`projections`` trägt das unter *Two orders, two commands*,
  und `projections.md:164` zitiert dieselbe Architekturstelle selbst. Zeile:
  `| §4.1 | architecture | {ref}`projections` |`.
- `src/previously/storage/schema.py:132` und
  `src/previously/contract/store.py:66` (§4.4): die Schema-Stelle argumentiert
  „derivable and disposable … carry no truth of their own" → `projections.md`,
  Abschnitt *Derivable and disposable*, der §4.4 ebenfalls selbst zitiert. Die
  `store.py`-Stelle argumentiert etwas **anderes**: dass die Trennung in zwei
  Protokolle „carries no truth of its own" zu einem Typ macht — und das steht
  in `module-boundaries.md:271-274` („A second protocol exists now … One
  protocol covering both would blur exactly the line"). Also die Form, die
  diese Tabelle für zweiteilige Paragraphen hat:
  `| §4.4 | architecture | {ref}`projections`; {ref}`module-boundaries` where
  the citation is about the two store protocols staying apart |`.

**Widerspruch (klein):** der Dispatch sagt „vermutlich `{ref}`projections``"
für beide. Für §4.1 stimmt das; für §4.4 wäre es die halbe Antwort gewesen und
hätte den `store.py`-Leser auf die falsche Seite geschickt — genau der Fehler,
den dieselbe Seite unter *Two kinds of citation* als Fixrunde-1-Fund vom
2026-10-03 beschreibt.

Mitgezogen, weil es sonst falsch geworden wäre: die Einleitung der Tabelle
sagte „§5 appears twice because the architecture and the stage 1a
specification both have one" → jetzt „§4.1, §4.4 and §5 appear twice each".

## I3 — die Zahl, vorher und nachher gemessen

Auf `main`:

```
$ git grep -c "§" main -- src tests migrations
main:src/previously/core/append.py:2
main:src/previously/storage/postgres.py:1
main:src/previously/storage/schema.py:2
main:tests/test_contracts.py:3
main:tests/test_properties.py:4
main:tests/test_schema.py:2
$ git grep -o "§" main -- src tests migrations | wc -l
14
```

**Vor I1**, auf `fee6d2b`:

```
$ git grep -c "§" HEAD -- src tests migrations
HEAD:src/previously/contract/store.py:1
HEAD:src/previously/core/append.py:2
HEAD:src/previously/storage/postgres.py:1
HEAD:src/previously/storage/schema.py:4
HEAD:tests/test_cli.py:2
HEAD:tests/test_contracts.py:1
HEAD:tests/test_properties.py:4
HEAD:tests/test_schema.py:2
$ git grep -o "§" HEAD -- src tests migrations | wc -l
17
```

**Nach I1**, Arbeitsbaum:

```
$ grep -ro "§" src tests migrations | wc -l
15
$ grep -rc "§" src tests migrations | grep -v ":0"
src/previously/contract/store.py:1
src/previously/core/append.py:2
src/previously/storage/schema.py:4
tests/test_properties.py:4
tests/test_contracts.py:1
src/previously/storage/postgres.py:1
tests/test_schema.py:2
```

Rechnung: 14 auf `main`, davon fallen zwei weg (`tests/test_contracts.py`
3 → 1), also **12 der ursprünglichen 14**; dazu **drei** neue aus 1b —
`store.py` §4.4, `schema.py` §4.4 und §4.1 — macht 15. Vor I1 waren es fünf
neue und 17.

Die zwei weggefallenen sind beide §12 und standen in **einem** Test,
`test_the_exempted_core_modules_load_no_sql_at_runtime` (auf `main`
`tests/test_contracts.py:172`); sein Docstring sagte selbst voraus, er „falls
away without replacement once `core` is typed against a generic
`LogStore[Conn]` protocol" — genau das tat Aufgabe 1. Nichts im Baum zitiert
§12 noch (`grep -rn "§12" src tests migrations` → leer), und die Tabellenzeile
sagt es jetzt: „nowhere; frozen design record, and no longer cited since stage
1b deleted the test that cited it".

**Widerspruch (klein), im Satz auf `design-records.md:10`:** der Befund
verlangt „zwölf" statt „vierzehn", aber die Teile des Satzes summieren sich
auf 72, und mit 12 + 2 + 56 wären es 70. Ich habe deshalb eine vierte
Teilmenge benannt: „Twelve of the 72 still do, two were dropped from error
messages the user reads, **two left with the test that cited them**, and the
remaining 56 name a page instead." 12 + 2 + 2 + 56 = 72.

## I4 — die Richtung des Schadens in §10 Punkt 8

Am Code geprüft, nicht am Befund:

- `schema.py:169` `PrimaryKeyConstraint("event_id", "seq")` auf `p_chronicle`,
  und `postgres.py:381 insert_chronicle` fügt mit `insert(p_chronicle)` ein,
  **ohne** `on_conflict` (die zwei `on_conflict_do_update` im Modul gehören
  zur Zustandszeile und zu `p_source_stats`) → der zweite Lauf läuft in eine
  Unique-Verletzung, laut.
- `source_stats.merge` (`source_stats.py:32-39`) addiert `events` und `units`
  und nimmt `min`/`max` der Zeiten → ein doppelter Durchgang zählt **über**.
- Unterzählen kann allein der Neubau-Pfad: `catch_up` macht
  `truncate_projection` plus `up_to_id = 0` in einer eigenen Transaktion
  (`worker.py:103-110`), und wenn die committet, nachdem der andere Lauf schon
  geschrieben hat, sind die Zeilen weg, während der Zähler sagt, sie seien da.

Alle drei Richtungen stehen jetzt im Punkt, die Handlungshälfte (Sperre
zusammen mit der Warteschlange, `SELECT … FOR UPDATE` oder Advisory-Lock)
ist unverändert geblieben. Ruling T8-g ist damit eingelöst: der Spec ist seit
`fee6d2b` eingefroren und wird trotzdem korrigiert, weil das Einfrieren die
Lieferung dieser Aufgabe ist.

## Die fünf Minors

1. **Spec Punkt 8:** „Heute kann sie niemand starten" → „Heute startet das
   System keine zwei Läufe: … — zwei Terminals können es trotzdem."
2. **Tutorial `:126`:** „… derived from the log, they start out empty, and one
   command fills them both." → zwei Sätze, zwei Zeilen („… and they start out
   empty." / „One command fills them both.").
3. **Tutorial `:144`:** „… has read, the log hasn't grown since, so there was
   nothing left to project." → „… has read, and the log hasn't grown since." /
   „There was nothing left to project."
4. **Tutorial Next steps:** „… built the two derived views, **read the
   chronicle and the counts per source**, and proven all of it …" — jetzt
   deckungsgleich mit der Aufzählung in Zeile 5.
5. **README:** die drei älteren Zeilen tragen „Frozen design record,
   2026-10-03: …", die neue „…, 2026-10-04: …". Vier Zeilen, eine Form.

## Ein Tor hat in dieser Runde zugeschlagen

`make -C docs vale` meldete `design-records.md:85  error  Did you really mean
'docstrings'?  Vale.Spelling`. „docstring" steht in keiner der vier
Quadranten-Seiten und nicht im Projektvokabular
(`.vale-styles/config/vocabularies/Previously/accept.txt`, fünfzehn Wörter).
Ich habe das Wort **nicht** ins Vokabular aufgenommen — die Datei steht nicht
in meiner Stageliste, und für eine einzige Prosastelle ist eine
Vokabularzeile die größere Änderung. Der Satz heißt jetzt „Two citations in
the test suite did point at this specification …", was ohnehin die Sprache
dieser Seite ist (sie spricht durchgehend von *citations*). **Für den
Betreuer:** wird „docstring" später in Prosa gebraucht, gehört es ins
Vokabular, mit Singular und Plural wie bei `subcommand`/`subcommands`.

## Gezielte Tests und die sechs Tore, Schlusszeilen ungekürzt

```
$ uv run pytest tests/test_cli.py tests/test_docs_references.py -q
40 passed in 13.14s
```

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 48 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                           → 232 passed in 21.19s
                                             (Required test coverage of 90.0% reached. Total coverage: 97.32%)
make -C docs html                          → build succeeded.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded.
```

232 unverändert, kein Test dazu. Der Testblock im Tutorial bleibt damit gültig
und ist **nicht** neu abgetippt — die Zahl, die `test_docs_typed_output.py`
bewacht, hat sich nicht bewegt.

## Anhang: das Rohprotokoll des abgetippten Testlaufs

Aus diesem Lauf stammt der Block im Tutorial (`uv run pytest` am 2026-10-04 im
Arbeitsbaum, Stand `af5f5de` plus die Doku-Änderungen von Aufgabe 8); auf der
Seite fehlt genau die `rootdir:`-Zeile, wie der Satz unter dem Block sagt.

```
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=1705979683
rootdir: /home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen
configfile: pyproject.toml
testpaths: tests
plugins: hypothesis-6.168.3, cov-7.1.0, randomly-5.0.0, platformdirs-4.12.2
collected 232 items

tests/test_projection_store.py ........                                  [  3%]
tests/test_storage.py ..........................                         [ 14%]
tests/test_contracts.py ..                                               [ 15%]
tests/test_projection_derive.py .........                                [ 19%]
tests/test_rows.py ....                                                  [ 21%]
tests/test_docs_typed_output.py .                                        [ 21%]
tests/test_verify.py .................                                   [ 28%]
tests/test_projection_worker.py ............                             [ 34%]
tests/test_schema.py .............                                       [ 39%]
tests/test_migrations_dsn.py ...                                         [ 40%]
tests/test_docs_build.py ......                                          [ 43%]
tests/test_units.py .............                                        [ 49%]
tests/test_canonical.py ...............                                  [ 55%]
tests/test_properties.py .........                                       [ 59%]
tests/test_docs_references.py .....                                      [ 61%]
tests/test_hashing.py ........................                           [ 71%]
tests/test_cli.py ...................................                    [ 87%]
tests/test_append.py ..............................                      [100%]

============================= 232 passed in 21.69s =============================
```
