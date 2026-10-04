# Aufgabe 1 — Bericht: `LogStore[Conn]`, und zwei Ausnahmen fallen

Status: **DONE_WITH_CONCERNS** (alle sechs Tore grün; die Bedenken sind
Beobachtungen für die Prüfung, keine offenen Arbeiten).

Commit: `afcbe11` — `refactor: type core against LogStore[Conn], and two
exemptions fall`. Ein Commit, Baum danach clean, Trailer
`Assisted-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## 1. Die negative Messung: vorher und nachher

**Vorher** (`uv run lint-imports`, vor jeder Änderung):

```
Analyzed 31 files, 61 dependencies.
-----------------------------------

Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT (2 ignored imports)
Only storage imports sqlalchemy KEPT (2 ignored imports)
No vendor SDK in stage 1a KEPT

Contracts: 4 kept, 0 broken.
```

**Nachher** (nach Schritt 6, unverändert bis zum Schluss):

```
Analyzed 32 files, 65 dependencies.
-----------------------------------

Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT
Only storage imports sqlalchemy KEPT
No vendor SDK in stage 1a KEPT

Contracts: 4 kept, 0 broken.
```

`(2 ignored imports)` steht an keiner Stelle mehr. Abnahmebedingung 1 aus
Spec §9 ist damit erfüllt, einschließlich des zweiten Halbsatzes:
`test_the_exempted_core_modules_load_no_sql_at_runtime` ist gelöscht.

## 2. Was gemessen wurde, nicht abgeschrieben

**Die Importstellen.** Der Brief sagte sechs Dateien. Gezählt:

```
$ grep -rln "previously.storage.rows" src tests migrations | wc -l
6
```

Dieselben sechs wie im Brief (`core/append.py`, `core/verify.py`,
`storage/postgres.py`, `tests/test_storage.py`, `tests/test_rows.py`,
`tests/test_hashing.py`), mit zusammen 13 Importzeilen. Alle umgestellt,
`src/previously/storage/rows.py` ist weg, kein Re-Export.

**Die acht Methoden.** Gemessen mit dem Befehl aus dem Brief:

```
$ grep -o 'storage\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py \
    | sed 's/^[^:]*://' | sort -u
storage.begin(      storage.lookup(
storage.count_events(   storage.read(
storage.insert_event(   storage.source_keys(
                        storage.tip(
                        storage.units_by_event(
```

Acht, genau die acht aus dem Brief. **Gegenprobe zur Neun:**
`PostgresStorage` hat zehn `def`-Zeilen, davon eine `__init__` — also neun
öffentliche Methoden. Die neunte ist `units(conn, event_id)`, und sie hat
genau einen Aufrufer:

```
$ grep -rn "\.units(" src/previously/
src/previously/cli.py:161:            for unit in storage.units(conn, row.id):
```

`cli.py:161` liegt im `show`-Pfad. `core` ruft `units` nirgends. Der Fehler
der ersten Spec-Fassung ist damit reproduziert und als Fehler bestätigt: ein
vom Implementierungsstand abgeschriebenes Protokoll hätte neun Methoden
getragen.

## 3. Gegenprobe aus Schritt 5 (pyright gegen das Protokoll)

`count_events` → `count_rows` in `storage/postgres.py:283`, nicht committet.

```
uv run pyright  75 errors
```

Erste Fehlerzeile:

```
src/previously/cli.py:106:18 - error: Argument of type "PostgresStorage" cannot be
assigned to parameter "storage" of type "LogStore[Conn@append]" in function "append"
  "PostgresStorage" is incompatible with protocol "LogStore[Conn@append]"
    "count_events" is not present (reportArgumentType)
```

**Abweichung zum Brief.** Der Brief erwartete den Fehler „in `core/verify.py`
an der Stelle, wo `verify(_storage())` beziehungsweise
`storage.count_events(conn)` steht". Er landet dort **nicht**, und zwar aus
einem Grund, der die Änderung bestätigt statt sie in Frage zu stellen:
`core/verify.py` nennt `PostgresStorage` nach dieser Aufgabe überhaupt nicht
mehr. `core` hat nichts, worüber es sich noch irren könnte. Die 75 Fehler
stehen ausnahmslos an den **Aufrufstellen**, in sechs Dateien:

```
src/previously/cli.py        tests/test_properties.py   tests/test_storage.py
tests/test_append.py         tests/test_schema.py       tests/test_verify.py
```

Fünf davon — `cli.py` und die vier Testdateien außer `test_storage.py` —
übergeben einen `PostgresStorage` an `append` oder `verify` und bekommen
genau die Protokollmeldung oben. `tests/test_storage.py` ist der Sonderfall:
es ruft `storage.count_events(c)` direkt auf (Zeilen 243 und 255) und bricht
deshalb aus dem gewöhnlichen Grund, dass das Attribut fehlt. Wer einen Store
übergibt, muss etwas Passendes besitzen; das Protokoll bindet dort, wo die
Zuordnung stattfindet. Das ist eine stärkere Bindung als der Brief erwartete, nicht
eine schwächere. Umbenennung zurückgenommen, `uv run pyright` → `0 errors`.

## 4. Gegenprobe aus Schritt 8 (lint-imports gegen die Kante)

`from previously.storage.postgres import PostgresStorage  # probe` in
`core/verify.py` oberhalb des `TYPE_CHECKING`-Blocks, nicht committet.

```
core knows no foreign system and no model BROKEN
Only storage imports sqlalchemy BROKEN
Contracts: 2 kept, 2 broken.
```

Mit der Begründung darunter, in beiden Verträgen gleichlautend:

```
previously.core is not allowed to import sqlalchemy:

-   previously.core.verify -> previously.storage.postgres (l.32)
    previously.storage.postgres -> sqlalchemy (l.25, …, l.34)
```

Zeile entfernt, `4 kept, 0 broken`. Abnahmebedingung 2 aus Spec §9 erfüllt.

## 5. Dritte Gegenprobe, nicht im Brief verlangt: `contract → storage`

Die Doku behauptet auf meiner Seite, `contract → storage` wäre `BROKEN`. Der
Brief übergab diese Messung als Tatsache aus der Planung. Weil ich sie auf
eine Seite schreibe, habe ich sie selbst gefahren —
`from previously.storage.errors import InvalidDsn` in `contract/store.py`:

```
Layers: core above storage, contract below both BROKEN

previously.contract is not allowed to import previously.storage:
- previously.contract.store -> previously.storage.errors (l.27)
```

Bestätigt. Die Korrektur am Spec (Zeilentypen nach `contract`) ist richtig,
und die Messung steht jetzt mit ihrer Ausgabe auf der Seite statt als
Behauptung.

**Erste Fassung der Messung war falsch und wurde verworfen:** der Probe-Import
landete per `sed` innerhalb des Modul-Docstrings, `lint-imports` meldete
`4 kept, 0 broken`, und das hätte als „die Kante ist erlaubt" durchgehen
können. Erst der Import nach dem Docstring misst etwas. Wert zu notieren,
weil die falsche Messung grün aussah.

## 6. Kantenzählung für die Doku

Alle sechs Kanten, die die Schichtordnung erlaubt, existieren jetzt. Gezählt
je Modul, **nur über Importanweisungen** — eine Zählung über den ganzen Text
wäre falsch, weil `storage/errors.py:7` und `storage/postgres.py:47`
`previously.core` in Prosa nennen — im Modul-Docstring beziehungsweise in
einem Kommentar, siehe M-3 der Fixrunde — und damit eine Kante
`storage → core` vortäuschen, die es nicht gibt (und die die Schichtordnung
verbieten würde):

```
$ grep -rhoE 'from previously\.[a-z]+' src/previously/cli.py | sort -u
from previously.contract
from previously.core
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/core | sort -u
from previously.contract
from previously.core
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/storage | sort -u
from previously.contract
from previously.storage

$ grep -rhoE 'from previously\.[a-z]+' src/previously/contract | sort -u
from previously.contract
```

Sechs Kanten zwischen verschiedenen Modulen: `cli → core`,
`cli → storage`, `cli → contract`, `core → storage`, `core → contract`,
`storage → contract`. `contract` hat keine ausgehende Kante — die letzte
Zeile ist das Fundament der Schichtordnung als Messung. Die Seite sagte
„five of the six"; sie sagt jetzt sechs, mit dem Befehl daneben.

Zur Genauigkeit: `core → contract` gab es schon vorher (`contract.types`).
Neu ist nur `storage → contract`, über `contract.rows`. Die Seite sagt das so.

Der Negationsblock in Abschnitt 3 der Seite trug ebenfalls
`(2 ignored imports)` und ist neu gefahren — mit einem Wegwerfvertrag
*Probe everything except storage*:

```
Probe everything except storage BROKEN

previously.cli is not allowed to import sqlalchemy:
-   previously.cli -> previously.storage.postgres (l.21, l.22)
    previously.storage.postgres -> sqlalchemy
```

Jetzt ohne Klammerzahl, Kante und Zeilennummern unverändert.

## 7. Die Suppressions-Liste

```
$ grep -rn "noqa:" --include="*.py" . | grep -v .venv | wc -l
5
```

Die fünf: `A001` (`docs/conf.py`), `C901` (`core/canonical.py`), `DTZ001`
(zweimal, `tests/test_append.py` und `tests/test_hashing.py`), `S607`
(`tests/test_contracts.py`). `S603` ist mit dem Test verschwunden.

**Eine dritte Zahl, die der Brief nicht nannte.** `CLAUDE.md` nannte `A001`
„**The sixth** arrived with the documentation". Mit `S603` weg ist `A001` die
fünfte. Der Brief verlangte nur zwei Änderungen (Halbsatz streichen,
„six" → „five"); ohne die dritte hätte die Datei sich selbst widersprochen —
eine Liste von fünf, in der ein Eintrag „der sechste" heißt. Geändert. Dazu
ein Satz, dass Entfernen genauso in die Liste gehört wie Hinzufügen, weil die
Datei bisher nur das Hinzufügen verlangte.

## 8. Was der Brief nicht wusste: ein siebter Riegel schlug zu

`tests/test_docs_typed_output.py::test_typed_test_counts_match_the_tree` ist
beim ersten vollen Lauf rot geworden:

```
AssertionError: record-your-first-event.md claims 194 passing tests,
the tree has 193. Retype the test run; it is the last thing you do.
```

Das Tutorial trägt einen **abgetippten** Testlauf, und der Riegel vergleicht
jede `N passed`-Zahl darin mit `pytest --collect-only`. Der Brief listete
`docs/tutorials/record-your-first-event.md` nicht unter den zu ändernden
Dateien. Die Zahl von 194 auf 193 zu setzen hätte den Riegel befriedigt und
das Transkript verfälscht: darin steht auch `collected 194 items` und
`tests/test_contracts.py ...` mit **drei** Punkten für drei Tests. Also
neu abgetippt — `uv run pytest` gefahren und die echte Ausgabe eingesetzt,
ohne die `rootdir:`-Zeile, die die Seite ausdrücklich auslässt:

```
collected 193 items
…
tests/test_contracts.py ..                                               [  2%]
…
============================= 193 passed in 16.48s =============================
```

Der Riegel hat genau das geleistet, wofür er da ist. Er ist auch der Grund,
dass die Reihenfolge der Dateien und die Prozentspalte im Transkript jetzt
anders aussehen: `pytest-randomly` mischt je Lauf, und die Seite sagt das.

## 9. Abweichungen zwischen Brief und Wirklichkeit

**a) `contract/store.py`: Importe unter `TYPE_CHECKING`, nicht auf Modulebene.**
Der Brief gab den Codeblock mit sechs Importen auf Modulebene. So geschrieben
meldet `uv run ruff check .` **sechs** `TC001`-Fehler („Move application
import into a type-checking block") — die Typen erscheinen ausschließlich in
Annotationen. `pyproject.toml` begründet die Regelkonfiguration ausdrücklich:
`runtime-evaluated-decorators = ["dataclasses.dataclass"]` nimmt
`contract/types.py` aus, weil dessen Annotationen zur Laufzeit via
`get_type_hints()` gebraucht werden — ein Protokoll mit `...`-Rümpfen braucht
das nicht. Also `TYPE_CHECKING`-Block, wie in `core/append.py`,
`core/verify.py` und `storage/postgres.py`. Der Inhalt des Protokolls, die
acht Signaturen und der Docstring sind wörtlich aus dem Brief. Eine
Suppression wäre die Alternative gewesen und ist nach `CLAUDE.md` die
schlechtere.

**b) Überschrift `## The bolt that is gone` → `## The bolt that fell with the edge`.**
Vale (`Microsoft.Contractions`) verlangt bei „that is" die Kurzform
„that's". Eine Überschrift mit Kontraktion ist schlechter als eine
umformulierte, also umformuliert — dieselbe Logik, die `.vale.ini` für
`Vale.Terms` vorgibt („reword, don't fight the rule"). Die Seite trägt den
Satz „The bolt fell with the edge" im Fließtext weiter. Zwei weitere
Vale-Treffer gleich mitbehandelt: ein „that is" in Abschnitt 6 zur Kurzform,
und ein „deliberately", das `Microsoft.Adverbs` als entbehrlich meldete.

**c) `## The protocols that made the exemptions unnecessary` ist Singular geblieben:
`## The protocol that made the exemptions unnecessary`.**
Das ist die Abweichung, über die ich am längsten nachgedacht habe. Der Brief
verlangte Plural und Präsens, und begründete das aus Spec §1.1. Aber
`ProjectionStore` existiert nach dieser Aufgabe **nicht** — Punkt 3 des
Briefs sagt das selbst („Aufgabe 3 fügt an"). Eine Überschrift im Plural und
ein Präsenssatz „zwei Protokolle" wären eine Behauptung, die am Baum nicht
messbar ist, und `CLAUDE.md` verlangt das Gegenteil. Darum: Singular,
Präsens für `LogStore`, und ein eigener Absatz, **warum** der Projektionsspeicher
ein zweites Protokoll wird statt weiterer Methoden an diesem (Spec §1.1,
letzter Punkt: `LogStore` ist append-only, ein Projektionsspeicher leert,
fügt ein und aktualisiert; ein Protokoll für beides verwischte, dass eine
Projektion keine eigene Wahrheit trägt). Aufgabe 3 muss dann nur die
Überschrift pluralisieren und den Absatz ins Präsens ziehen — der Inhalt
steht schon da.

**d) Der Sechs-Tore-Messblock in „The bolt in the test run" ist entfallen.**
Der Brief sagte, der `TC001`-Messblock bleibe. Der Abschnitt hatte zwei
Blöcke: die `pyright`-Meldung zum `isinstance`-Fall (behalten, datiert
2026-10-03) und eine Tabelle aller sechs Tore mit
`uv run pytest -q  1 failed, 193 passed`. Die Tabelle ist raus, aus zwei
Gründen. Erstens beschreibt sie eine Mutation, die sich nicht mehr
durchführen lässt — es gibt keinen `PostgresStorage`-Import in `core`, den
man aus einem `TYPE_CHECKING`-Block ziehen könnte. Zweitens ist ihre
`193 passed` die **alte** Zahl neben einem Fehlschlag (194 insgesamt) und
kollidiert ab heute mit der neuen Gesamtzahl 193 — ein Leser liest dort eine
richtige Zahl mit falscher Bedeutung. Die Lehre des Abschnitts (`TC001`
reicht nicht, weil es eine Aussage über Symbolverwendung ist und nicht über
Schichten) steht im Fließtext und mit der `pyright`-Messung weiter da.

**e) Eine siebte Quelldatei geändert, die der Brief nicht listete.**
`src/previously/core/hashing.py:59` nannte im Docstring von `HashableUnit`
den alten Ort: „`storage.rows.UnitRow` on the way out". Nach dem Verschieben
falsch, also auf `contract.rows.UnitRow` gezogen. Kein Gate hätte das
gefunden — es ist Prosa in einem Docstring.

## 10. Testzahl

**193 passed**, genau die erwartete Zahl (194 minus der gelöschte Riegel).
Keine Abweichung, nichts nachzuzählen.

## 11. Die sechs Tore

| # | Tor | Ausgabe |
|---|-----|---------|
| 1 | `uv run ruff check .` | `All checks passed!` |
| 2 | `uv run ruff format --check .` | `40 files already formatted` |
| 3 | `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| 4 | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` — ohne `(N ignored imports)` |
| 5 | `uv run pytest --cov --cov-report=term-missing` | `193 passed`, `Total coverage: 97.65%` |
| 6 | `make -C docs html && make -C docs vale && make -C docs linkcheck` | `build succeeded.` / `0 errors, 0 warnings and 0 suggestions in 20 files.` / `build succeeded.` |

Jedes Tor einzeln gefahren, die Ausgaben oben kopiert, nicht erinnert.

## 12. Bedenken

**1. `contract/store.py` steht bei 0% Coverage, und das bleibt so.**
Die Gesamtabdeckung fällt von 99.8% auf 97.65% (Schwelle 90, Tor grün). Die
Buchführung ist aber sauberer als die Prozentzahl vermuten lässt: vorher
500 Statements, 1 nicht abgedeckt; nachher 511 Statements, 12 nicht
abgedeckt. Absolut abgedeckt bleiben **499** — keine vorher abgedeckte Zeile
hat Abdeckung verloren, alle 11 neuen Fehlstellen sind das Protokollmodul.
Gemessen, warum: das Modul wird zur Laufzeit nie geladen, weil beide
Importeure `LogStore` nur unter `TYPE_CHECKING` nennen.

```
$ uv run python -c "import previously.cli, previously.core.append, \
    previously.core.verify, sys; \
    print('previously.contract.store' in sys.modules)"
False
```

Ich habe **keinen** Test hinzugefügt, der das Modul nur importiert, um eine
Zahl zu heben, und **kein** `# pragma: no cover` gesetzt, das eine wahre
Tatsache verstecken würde. Statt dessen steht die Messung im Modul-Docstring.
Wenn Du die Prozentzahl im Torprotokoll nicht sinken sehen willst, ist
`exclude_lines` in `pyproject.toml` der Ort — aber das ist Deine Entscheidung,
nicht meine, und sie wirkt auf jedes künftige Protokoll.

**2. `units` ist jetzt eine untypisierte Kante von `cli` zum Store.**
`cli.py:161` ruft `storage.units(conn, row.id)` auf einem `PostgresStorage`,
und das ist in Ordnung — `cli` darf `storage.postgres` sehen. Aber: `cli` ist
nach dieser Aufgabe der einzige Ort, der den Store **nominal** braucht.
Sollte irgendwann `cli` gegen Protokolle getypt werden, braucht `show`
entweder `units` im Protokoll oder einen eigenen Weg. Heute kein Problem,
aber die Stelle, an der die Neun wieder auftauchen wird.

**3. Die Tests bleiben an `PostgresStorage` gebunden, und das ist richtig.**
`tests/test_append.py`, `tests/test_verify.py`, `tests/test_properties.py`
und `tests/test_schema.py` übergeben echte `PostgresStorage`-Instanzen an die
jetzt generischen Funktionen. Kein Mock,
wie `CLAUDE.md` verlangt — und die 75 pyright-Fehler aus Abschnitt 3 zeigen,
dass diese Tests die Protokollkonformität mitprüfen, ohne sie zu behaupten.
Es gibt keinen Test, der `LogStore` gegen eine **zweite** Implementierung
fährt, also ist „`core` läuft gegen einen Store, den es nicht importiert
hat" heute eine statische Zusage von pyright und keine ausgeführte. Für
Stufe 1b reicht das; wer die Zusage ausgeführt sehen will, braucht eine
zweite Implementierung, und die gibt es ohne guten fachlichen Grund nicht.

**4. Die Seite ist lang geworden.**
`module-boundaries.md` wächst von 189 auf rund 250 Zeilen, weil jeder
abgeschaffte Zustand seine Begründung in der Vergangenheitsform behält
(Ausnahmen, Riegel, Wildcard-Messung) **und** der neue Zustand dazukommt.
Der Brief wollte das so, und ich halte es für richtig — aber nach Aufgabe 2
steht daneben eine `projections.md`, und dann lohnt die Frage, ob die
Vergangenheit von 1a nicht besser in die eingefrorenen Design-Records als in
eine Erklärseite gehört. Keine Arbeit für diese Aufgabe, eine Frage für die
Dokumentationsaufgabe am Ende.

**5. Was ich nicht gesetzt habe.**
Kein `{ref}`projections`` — die Seite existiert erst ab Aufgabe 2, und
`tests/test_docs_references.py` prüft jede Referenz. Aufgabe 2 muss die
Querverweise von `module-boundaries.md` nach `projections.md` selbst legen;
diese Seite hat an zwei Stellen eine passende Anschlussstelle (der Absatz zum
zweiten Protokoll und der Satz über „derivable and disposable").

---

# Fixrunde 1 — Bericht

Commit: `fdd3215` — `docs: restore the measurement the TC001 argument
rests on`. Alle sechs Tore grün, Baum clean.

## I-1 — Der Sechs-Tore-Messblock ist wiederhergestellt

**Gewählte Fassung: der vollständige Block, datiert, mit zwei beschrifteten
Zahlen.** Nicht die Kurzfassung aus drei Zeilen, und zwar aus einem Grund,
der dem Prüfer zuzustimmen heißt und gleichzeitig seine zweite Option
ausschließt: die Kurzfassung hätte `ruff`, `pyright` und `lint-imports`
behalten — also genau die Zeilen, die zeigen, dass die Tore **schweigen**.
Die load-bearing Hälfte der Behauptung „survived every gate but that one
test" ist aber die Zeile, die zeigt, dass der Test **zuschlug**:

```
uv run pytest -q              1 failed, 193 passed
    test_the_exempted_core_modules_load_no_sql_at_runtime
    -> loaded sqlalchemy at runtime
```

Ohne sie wäre die Hälfte „but that one test" wieder unbelegt — dieselbe
Fehlerart in kleinerer Dosis. Die Option „nur die drei Zahlenlosen" löst
die Kollision, indem sie den Beweis wegnimmt. Also voller Block.

**Die Kollision ist nicht beschriftet, sondern aufgelöst.** Der Prüfer schlug
`(194 tests then; the tree has 193 today for an unrelated reason)` vor. „For
an unrelated reason" wäre falsch, und das ist der einzige Punkt, an dem ich
widerspreche — in der Sache, nicht im Befund. Der Grund ist nicht unverwandt,
er ist **derselbe**: der Baum hatte damals 194 Tests, einer davon war der
Riegel, und der Riegel ist genau der, der in dieser Messung fehlschlug und den
1b gelöscht hat. Also gilt arithmetisch

    194 damals − 1 (dieser Test) = 193 heute

und daraus folgt eine schärfere, wahre Aussage statt einer Entwarnung:

> `193` reads the same here and in today's test run for a reason rather than
> by accident: the 193 that passed then are the 193 that remain, because the
> one that failed is the one stage 1b deleted.

Gegengeprüft: mein Commit hat genau eine Testfunktion entfernt (`test_contracts.py`
von drei auf zwei Tests) und keine hinzugefügt; das Tutorial trug vorher
`collected 194 items`, jetzt `193`. Die Mengen sind identisch, nicht nur die
Zahlen.

Die zweite Zahl ebenso aufgelöst statt nur markiert:
`39 files already formatted (40 today)`, mit dem Satz „The file count went
from 39 to 40 with `contract/store.py`". Gemessen, weil die 40 nicht
offensichtlich ist — `ruff` formatiert auch Markdown:

```
$ git ls-tree -r --name-only HEAD~1 | grep '\.py$' | grep -v '^docs/' | wc -l
35
$ git ls-files '*.py' | grep -v '^docs/' | wc -l
36
$ git ls-files '*.md' | grep -v '/'
CLAUDE.md  DEPENDENCIES.md  NOTIZEN.md  README.md
$ uv run ruff format --check .
40 files already formatted
```

35 + 4 = 39 damals, 36 + 4 = 40 heute, und die eine neue Datei ist
`contract/store.py`. Kein Zufall, keine Entwarnung nötig.

**Zu meinen beiden verworfenen Gründen.** Der Prüfer hat beide zerlegt, und
beide Zerlegungen treffen. Grund 1 („Mutation nicht mehr durchführbar") war
der schlechtere der zwei, und zwar aus genau dem genannten Grund: er gilt
identisch für den `pyright`/`isinstance`-Block, den ich behalten habe. Ich
habe denselben Maßstab auf zwei Blöcke verschieden angewandt und die
Inkonsistenz nicht gesehen. Grund 2 war ein richtiger Fund mit falschem
Heilmittel — ich habe von einer stehengebliebenen Zahl auf „Block raus"
geschlossen, statt auf „Zahl erklären", und das ist der teurere Fehler, weil
Löschen die Begründung mitnimmt und das Ergebnis wie Knappheit aussieht.

Die Reihenfolge des Abschnitts ist dabei wieder die ursprüngliche: erst die
Mutation, die **durchkam** (Attributzugriff, sechs Tore), dann die, die
**scheiterte** (`isinstance`, pyright). Meine Fassung hatte nur die zweite
und damit die schwächere zuerst.

## Die drei Formulierungen — alle drei wiederhergestellt

Ich lasse **keine** draußen. Begründung je Stück:

1. **`_is_text`-Querverweis.** Wiederhergestellt, im Präsens, weil er auf
   heutigen Code zeigt: `core/append.py:130` nimmt weiterhin `object`, mit
   einem Docstring, der `reportUnnecessaryIsInstance` nennt. Der Satz trägt
   das `isinstance`-Argument von der anderen Seite und kostet eine Zeile.
2. **„the same trade … one level up"** in *Four contracts*. Wiederhergestellt
   mit einer Zeitanpassung: „the same trade **the section below** is about"
   statt „the exemptions below", weil die Ausnahmen nicht mehr da sind, der
   Abschnitt aber schon. Ohne den Satz steht der Verneinungs-Tausch als
   isolierte Konfigurationsfrage da, statt als derselbe Handel eine Ebene
   höher.
3. **„a correct decision and a wrong one look exactly alike in the
   configuration".** Wiederhergestellt in der Vergangenheitsform, am
   ursprünglichen Ort (Abschnittsende), zusammen mit dem Halbsatz, dass der
   Test grün war und einen bestehenden Zustand hielt. Dem „halte ich für
   tragend" stimme ich zu: das ist der Satz, der erklärt, warum ein grüner
   Test kein nutzloser Test war. Mein „a gap the configuration couldn't
   express" bleibt als Einleitung stehen, trägt jetzt aber nicht mehr allein.

## M-1 bis M-3

- **M-1.** Erledigt. `.importlinter` endet wieder auf ein einzelnes `\n`,
  byteweise identisch mit `HEAD~1`:
  `git show HEAD~1:.importlinter | tail -c 16 | od -c` und
  `tail -c 16 .importlinter | od -c` liefern dieselben Bytes
  (`o p e n a i \n`). Ursache war mein `python`-Schnitt beim Entfernen des
  Wegwerfvertrags: `s[:i] + "\n"`, wobei `s[:i]` schon auf `\n` endete.
- **M-2.** Erledigt, und zwar über die Beschriftung statt über das Bild:
  „all six **between its own modules**, and not one of them exempted. The
  seventh arrow leaves the package." Die Kante `storage → sqlalchemy` bleibt
  gezeichnet, weil sie der Grund für zwei der vier Verträge ist; wer Pfeile
  zählt, findet die Differenz jetzt erklärt statt sie selbst auflösen zu
  müssen.
- **M-3.** Erledigt, aber **anders formuliert als vorgeschlagen**, erzwungen
  von Tor 6. Erste Fassung war Deine Präzisierung wörtlich — „in prose—a
  comment in `postgres.py`, a module docstring in `errors.py`". Vale schlug
  an: `40:158 error Did you really mean 'docstring'? Vale.Spelling`. Das Wort
  steht nicht in `.vale-styles/config/vocabularies/Previously/accept.txt`.
  Ich habe es **nicht** eingetragen: `.vale.ini` legt dar, dass `Vale.Terms`
  jeden Eintrag auf seine Schreibweise festnagelt, ein kleingeschriebener
  Eintrag also im ganzen Baum keinen Satz mehr beginnen darf — eine
  baumweite Nebenwirkung für eine Wortwahl in einem Nebensatz, und die
  Vokabelliste zu erweitern ist Deine Entscheidung, nicht meine in einer
  Fixrunde. Statt dessen die kürzere Fassung, die Dein eigenes Kriterium
  erfüllt („'in prose' deckt beides"): „mention `previously.core` **in prose
  rather than in an import**". Welche Datei welche Form trägt, steht hier:
  `storage/postgres.py:47` ist ein Kommentar, `storage/errors.py:7` steht im
  Modul-Docstring. Wenn Du „docstring" in der Vokabelliste willst, ist das
  ein eigener, bewusster Commit mit der dokumentierten Nebenwirkung.

## M-4 — Korrektur an §9a dieses Berichts

**§9a ist in diesem Punkt falsch.** Der Satz „Der Inhalt des Protokolls, die
acht Signaturen und der Docstring sind wörtlich aus dem Brief" trifft auf den
Docstring **nicht** zu. Ich habe einen Absatz von acht Zeilen ergänzt, der
die 0 %-Coverage von `contract/store.py` erklärt und die Messung dazu nennt
(`previously.contract.store` erreicht `sys.modules` nie, weil beide
Importeure nur unter `TYPE_CHECKING` importieren). Die Ergänzung entstand erst
in Schritt 10, als die Coverage-Tabelle das 0 % zeigte, und ich habe sie in
§12 Bedenken 1 beschrieben, aber nicht in §9 als Abweichung deklariert — in
einem Bericht, dessen Gliederung „was abwich und warum" ist, ist das ein
Loch an der Stelle, an der ein Prüfer nachsieht. Richtig gelesen heißt §9a:
die acht Signaturen, der Klassen-Docstring und die ersten zwei Absätze des
Modul-Docstrings sind wörtlich aus dem Brief; der dritte Absatz ist meine
Ergänzung. Die Abweichung (a) selbst — `TYPE_CHECKING` statt Modulebene —
bleibt wie beschrieben.

## Gefahrene Tore

| # | Befehl | Ausgabe |
|---|--------|---------|
| 1 | `uv run ruff check .` | `All checks passed!` |
| 2 | `uv run ruff format --check .` | `40 files already formatted` |
| 3 | `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| 4 | `uv run lint-imports` | `Contracts: 4 kept, 0 broken.` (vier `KEPT`, keine Klammerzahl) |
| 5 | `uv run pytest --cov --cov-report=term-missing` | `193 passed in 17.03s`, `Total coverage: 97.65%` |
| 6 | `make -C docs html` | `build succeeded.` |
| 6 | `make -C docs vale` | `0 errors, 0 warnings and 0 suggestions in 20 files.` |
| 6 | `make -C docs linkcheck` | `build succeeded.` |

Dazu die beiden gezielt verlangten Doku-Tests:

```
$ uv run pytest tests/test_docs_references.py tests/test_docs_build.py -q
...........                                                              [100%]
11 passed in 0.11s
```

Die Seite ist von 251 auf 279 Zeilen gewachsen (der wiederhergestellte Block
plus die drei Formulierungen), gemessen mit
`wc -l docs/explanation/module-boundaries.md`. Damit ist sie 90 Zeilen länger
als vor der Aufgabe (189), und Bedenken 4 aus dem Hauptbericht gilt
entsprechend stärker.

## Widerspruch

Einer, in der Sache und nicht am Befund: „for an unrelated reason" in der
vorgeschlagenen Beschriftung der `193`. Der Grund ist derselbe, nicht ein
unverwandter — damals 194 Tests, einer davon dieser Riegel, heute 193. Die
Seite sagt das jetzt als positive Aussage („the 193 that passed then are the
193 that remain"), weil eine Erklärung dort besser steht als eine Entwarnung.
Der Befund I-1 selbst trifft vollständig zu, ebenso M-1 bis M-4.
