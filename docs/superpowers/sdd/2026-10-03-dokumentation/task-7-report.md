# Aufgabe 7 — Bericht

**Status:** fertig. Ein Commit, `fae1c25`, alle sechs Tore grün.

```
fae1c25 docs: point the code at the documentation, and keep it honest with a test
```

34 Dateien, +508/−142, davon zwei neu: `tests/test_docs_references.py` und
`docs/explanation/design-records.md`.

---

## 1. Warum ein Commit und nicht mehrere

Der Brief erlaubt mehrere, verlangt aber, dass jeder für sich alle sechs Tore
besteht. Zwei Commits wären logisch möglich (erst einfrieren, dann umstellen),
aber **nachweisen** ließe sich die Torfestigkeit des ersten nicht: der
Arbeitsbaum trägt dann schon die Änderungen des zweiten, und sie
herauszunehmen heißt `git stash` auf einem Stack, den diese Umgebung
ausdrücklich als mit anderen Sitzungen geteilt bezeichnet. Eine Behauptung
ohne Messung ist genau das, was diese Aufgabe aus dem Baum entfernen soll.

Dazu ist die Kopplung echt: die Meldung in `core/canonical.py`, die Zeile in
`docs/reference/hash-format.md` und die abgetippte Testzahl im Tutorial
hängen über zwei Tore zusammen und müssen in **einem** Commit landen.

## 2. Gemessener Ist-Stand, vor der Umstellung

```
$ grep -rno "§[0-9]\+\(\.[0-9]\+\)*" src/ tests/ migrations/ | wc -l
72
```

72 Vorkommen auf 71 Zeilen (`tests/test_schema.py:111` trug zwei), über 21
Dateien, auf 20 verschiedene Paragraphennummern. Die Häufigkeiten des Briefs
stimmen zeichengenau: §3.2 12×, §3.1 9×, §5.1 8×, §5 5×, §4.2 5×, §3.4 5×,
§4.6 4×, §4.4 4×, §10.2 4×, §9 2×, §7 2×, §4.1 2×, §12 2×, §11 2×, §8 1×,
§6 1×, §4 1×, §3.3 1×, §2 1×, §10.1 1×.

Nachher:

```
$ grep -rn "§" src/ tests/ migrations/ | grep -v test_docs_references | wc -l
13
$ grep -rno "{ref}\`[a-z0-9-]*\`" src/ tests/ migrations/ | grep -v test_docs_references | wc -l
58
```

72 = 57 umgestellt + 13 eingefroren + 2 aus Programmausgaben gestrichen; die
58. `{ref}`-Stelle ist der neue Kommentar über dem `raise` in `canonical.py`,
der die gestrichene Begründung aufnimmt.

## 3. Die Abbildungstabelle — 21 Zeilen für 20 Paragraphen

§5 kommt in **zwei** Dokumenten vor (Architektur §5 = Storage-Schnittstelle,
1a §5 = Idempotenz), deshalb 21 Zeilen. Die Tabelle steht in
`docs/explanation/design-records.md`.

| § | Dokument | Ziel |
|---|---|---|
| §2 | Architektur | `module-boundaries` |
| §3.1 | 1a | `hash-chain`; `hash-format` für die Feldlisten, `tombstone-seam` für die Tilgungsnaht |
| §3.2 | 1a | `payload-range` |
| §3.3 | 1a | `timestamps` |
| §3.4 | 1a | `hash-chain` |
| §4 | 1a | `concurrency` |
| §4.1 | 1a | `hash-chain` |
| §4.2 | 1a | `conflict-classes`; `concurrency`, wo es um die Indexe als Serialisierung geht |
| §4.4 | 1a | `concurrency` |
| §4.6 | Architektur | `tombstone-seam` |
| §5 | Architektur | `module-boundaries` |
| §5 | 1a | `hash-chain`; `canonicalization` für „zwischen Aufrufen gegen innerhalb eines Stapels" |
| §5.1 | Entwurf | `canonicalization` |
| §6 | 1a | `hash-chain` |
| §7 | 1a | `database-schema`; `concurrency` für „genau ein `int` je Event" |
| §8 | 1a | `module-boundaries` |
| §9 | 1a | `cli-reference`; `configuration-reference` für den DSN |
| §10.1 | Architektur | eingefrorener Bericht |
| §10.2 | 1a | eingefrorener Bericht |
| §11 | 1a | eingefrorener Bericht |
| §12 | 1a | eingefrorener Bericht |

Jedes benutzte Label liegt in der Pflichtmenge von 19. Benutzt werden 15
davon; `hash-domain`, `add-a-migration`, `first-event-tutorial` und
`restore-from-a-backup` werden von keinem Verweis angesprochen.

### Die Klassenregel, die quer zur Tabelle liegt

Die Tabelle bildet Paragraphen ab, die Entscheidung fällt aber je **Zeile**.
Regel, die ich festgelegt und auf der Seite dokumentiert habe:

> Ein Verweis, der erklärt, **warum der Code heute so ist**, nennt eine Seite
> als `{ref}`label``. Ein Verweis, der sagt, **was wann entschieden wurde**
> („§3.4 schreibt `payload IS NULL` vor", „§10.2 formuliert P3 als …",
> „§4.2 sagte ‚kein Retry' ohne Einschränkung"), behält seine
> Paragraphennummer und trägt `(frozen design record)` **auf derselben
> Zeile**.

Darum erscheinen §3.4 und §4.2 in beiden Formen: §4.2 fünfmal, drei zu zwei;
§3.4 fünfmal, drei zu zwei. Die 13 verbliebenen Zitierungen:

```
src/previously/core/append.py        2   (§4.2, historisch)
src/previously/storage/schema.py     2   (§10.1 kein ORM, §3.4 payload IS NULL)
tests/test_properties.py             4   (§10.2, P1–P7)
tests/test_schema.py                 2   (§3.4, §11)
tests/test_contracts.py              3   (§11, §12 zweimal)
```

Die „auf derselben Zeile"-Pflicht ist keine Stilfrage: der Test prüft
zeilenweise. Mehrere Kommentare mussten dafür neu umgebrochen werden.

## 4. Abweichungen zwischen Brief und Wirklichkeit

**(A1) §10.5 kommt im Code nicht vor.** Der Brief nennt als Beispiel „§4.6 und
§10.5 → `backup-encryption`". `§10.5` steht in `src/`, `tests/`,
`migrations/` **nirgends** — aus der Architektur erscheinen nur §2, §4.6, §5,
§10.1. `backup-encryption` ist deshalb Ziel **keines** Code-Verweises; es wird
nur aus `docs/how-to/restore-from-a-backup.md` angesprochen (Schritt 3).

**(A2) §4.6 → `tombstone-seam`, nicht `backup-encryption`.** Architektur §4.6
(„Tilgung: heute nichts verbauen") enthält den Unterabschnitt zur
Blob-Verschlüsselung, aber alle **vier** Zitierungen im Code
(`cli.py`, `core/verify.py`, `tests/test_cli.py`, `tests/test_rows.py`)
handeln vom Grabstein. `tombstone-seam` ist das Label des Abschnitts, der sie
trägt.

**(A3) §3.1 → `hash-chain`, nicht `hash-domain`.** Der Brief nennt
`hash-domain`. Das ist das Label über „Separating the domains", also über das
Paar `v`/`domain`. **Keine** der neun §3.1-Zitierungen handelt davon; sie
handeln von der Hash-Reichweite, vom schlüssellosen Fall, von der Eindeutigkeit
der Quellenangabe und von der Tilgungsnaht. Folge: `hash-domain` ist nach
dieser Aufgabe ein Label, auf das nichts zeigt.

**(A4) §5.1 liegt im Entwurf, nicht im 1a-Spec.** Der 1a-Spec hat keine §5.1
(§5 „Idempotenz" hat keine Unterabschnittsnummern), die Architektur auch
nicht. Entwurf §5.1 ist „Wahrnehmung" und definiert `evidence`. Das bestätigt
den Hinweis der Steuerung: die *Reservierungsregel* steht in keinem der drei
Specs, nur die Bedeutung von `evidence`. Ziel ist darum
`canonicalization` — Abschnitt „The reserved key", den Aufgabe 6 geschrieben
hat.

**(A5) Die Zeilennummer der zweiten Programmausgabe ist 310, nicht 301.** Der
Brief nennt zweimal `append.py:301`; die Meldung stand auf 310, der Kommentar
darüber auf 304. Als AST-Konstante beginnt das Literal auf 309.

**(A6) Der Testcode des Briefs kann so nie grün werden.**
`test_no_bare_paragraph_references_remain` durchsucht `tests/**/*.py`, also
**auch sich selbst**: der eigene Docstring nennt `§3.2` und `§5.1`, und die
Prüfzeile `if "§" in line` enthält das Zeichen notwendigerweise. Vier Zeilen
der eigenen Datei hätten als Verstoß gezählt. Eingebaut ist deshalb ein
`SELF`-Ausschluss mit begründetem Kommentar: die Datei, die das Zeichen
buchstabieren muss, um es zu suchen, kann sich nicht selbst prüfen.

**(A7) `produced = []` scheitert an pyright strict.** Annotiert als
`produced: list[str] = []`.

**(A8) Die Prüfung auf Zitierungen in Programmausgaben hat ihren zweiten Fall
durchgewinkt — gemessen.** Die Heuristik des Briefs
(`'f"' in line or ('"' in line and "raise" in line)`) fand nur
`canonical.py:53`:

```
AssertionError: These lines print a paragraph reference to the user:
{'src/previously/core/canonical.py': [53]}
```

`append.py:310` ist die Fortsetzung eines implizit verketteten Literals und
trägt darum weder `raise` noch ein `f`-Präfix. Ersetzt durch eine
`ast`-Prüfung: Stringkonstanten, die kein Docstring sind. Danach:

```
{'src/previously/core/canonical.py': [53], 'src/previously/core/append.py': [309]}
```

**(A9) `quoted in page` war grün, während die Seite etwas zitierte, das
niemand druckt — gemessen.** Nach dem Streichen von `(§3.2)` aus dem Code
blieb `(§3.2)` in `hash-format.md` stehen, und die Teilketten-Prüfung war
zufrieden: die erzeugte Meldung ist eine Teilkette der Tabellenzelle.
Verschärft auf `f"`{quoted}`" in page` — die Rückstriche erzwingen
Gleichheit der Zelle mit der Meldung. Der Test schlug danach wie verlangt
fehl, bevor die Seite nachgezogen wurde.

**(A10) Vier Tests, nicht zwei.** Schritt 6 und 8 des Briefs sprechen von
„beiden" Tests; die Datei enthält vier (der Brief selbst gibt in Schritt 5 zwei
Blöcke mit je zwei Tests an).

**(A11) `DEPENDENCIES.md`: 13 Zitierungen bestätigt, aber einmal markiert
statt dreizehnmal.** Neun der dreizehn sind wörtlich derselbe Satz
(„reasoning in §10.6 of the architecture (choice of tooling)") in neun
Tabellenzeilen. `(frozen design record)` neunmal in dieselbe Spalte zu
schreiben macht die Tabelle unlesbar und sagt nichts Neues. Statt dessen ein
Absatz über der Tabelle, der es für die ganze Seite sagt und auf
`design-records.md` verlinkt. Ich halte das für die bessere Erfüllung derselben
Regel, melde es aber als Abweichung — ein Leser, der nur eine Tabellenzeile
sieht, liest den Absatz nicht.

**(A12) 189 → 193 Tests.** Vier neue, nicht zwei. Das Tor
`test_docs_typed_output` hat die abgetippte Ausgabe im Tutorial beanstandet,
und sie ist als Letztes neu abgetippt (echter Lauf, Seed 1548054570,
`193 passed in 16.38s`).

## 5. Falsche Behauptungen, gefunden und behoben

**(F1) `pyproject.toml`: „the nine `print` calls".** `cli.py` hat **dreizehn**.
Gemessen gegen die Projektkonfiguration, mit dem Eintrag
`"src/previously/cli.py" = ["T201"]` entfernt:

```
$ uv run ruff check --output-format concise src/previously/cli.py | grep -c T201
13
```

Dreizehn Zeilen: 107, 119, 126, 128, 138, 139, 140, 154, 156, 160, 162, 164,
216. Der Satz begründet eine Datei-Ausnahme mit einer Zahl, und die Zahl war
falsch — genau die Klasse Fehler, vor der die Steuerung gewarnt hat, und in
genau dem Kommentar, den diese Aufgabe sowieso anfassen musste (Streichung des
§9-Verweises). Korrigiert, mit der Messung dazu.

**(F2) Eigene, beim Schreiben entstandene Falschaussage.**
`design-records.md` behauptete zunächst „`§4.2` is cited four times for the
three classes of conflict". Nachgezählt sind es drei (zwei auf
`conflict-classes`, eine auf `concurrency`) plus zwei eingefrorene. Korrigiert
auf „five times, and the five split three to two", bevor commit.

**(F3) Tempus in `design-records.md`.** „so the code cites them" war nach der
Umstellung falsch. Jetzt: „cited them", plus die Aufteilung 13 / 2 / 57.

### Nachgezählt und *richtig* befunden

Damit die Liste nicht nach Stichproben aussieht — folgende Zahlen in Texten,
die ich beim Umstellen gelesen habe, habe ich nachgemessen und sie stimmen:
die elf Felder des Event-Hashes (`hashing.py`, `hash-chain.md`,
`silent-losses.md`), die acht Backoff-Schranken und ihre Summe 0,715 s
(`append.py`, `concurrency.md`), „fünf der sechs Kanten"
(`module-boundaries.md`), „elf der fünfzehn Einträge sind kleingeschrieben"
(`.vale.ini` gegen `accept.txt`), die 21 Dateien und 20 Paragraphen des
Briefs, die 13 Verweise in `DEPENDENCIES.md`, und die fünf Meldungen, die
`hash-format.md` wörtlich zitiert (jetzt durch Aufruf des Codes festgenagelt).

## 6. Die Tore

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
39 files already formatted

$ uv run pyright
0 errors, 0 warnings, 0 informations

$ uv run lint-imports
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT (2 ignored imports)
Only storage imports sqlalchemy KEPT (2 ignored imports)
No vendor SDK in stage 1a KEPT
Contracts: 4 kept, 0 broken.

$ uv run pytest -q
193 passed in 16.61s

$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded.
✔ 0 errors, 0 warnings and 0 suggestions in 20 files.
build succeeded.
```

Zusätzlich die Fassung aus CLAUDE.md und die Vektoren:

```
$ uv run pytest --cov --cov-report=term-missing -q
Required test coverage of 90.0% reached. Total coverage: 99.80%
193 passed

$ uv run pytest -q -k vector
3 passed, 190 deselected
```

Die drei Vektortests (`test_vector_payload_hash`, `test_vector_units_hash`,
`test_vector_event_hash`) sind grün — es wurde nichts gehasht Relevantes
angefasst.

## 7. Bedenken

1. **`hash-domain` zeigt nichts an und auf `hash-domain` zeigt nichts.** Nach
   (A3) ist es ein Label ohne Verweis. Es bricht nichts — aber die
   Pflichtmenge von 19 enthält jetzt ein Label, dessen einziger Zweck ein
   Anker im Fließtext ist. Eine Prüfung „jedes Label wird mindestens einmal
   angesprochen" wäre denkbar und würde dieses und drei weitere melden.

2. **Der `SELF`-Ausschluss ist ein Loch mit Namen.** Wer künftig eine nackte
   Paragraphenzitierung in `tests/test_docs_references.py` schreibt, kommt
   durch. Die Alternative — das Zeichen über seinen Codepunkt bilden und in
   den Docstrings umschreiben — hätte die gemessene Fundstelle
   (`canonical.py:53`, `append.py:309`) aus der Dokumentation des Tests
   entfernt. Ich habe das Loch dem Verlust der Messung vorgezogen und es im
   Kommentar benannt.

3. **Der Worktree-Pfad steht in der veröffentlichten Doku.** Die abgetippte
   `pytest`-Ausgabe im Tutorial enthält
   `rootdir: /home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`.
   Das war vorher schon so, und die Regel „tipp einen echten Lauf ab" erzwingt
   es. Nach dem Merge auf `main` wäre ein Lauf aus dem Hauptcheckout die
   ehrlichere Ausgabe. Ich habe nichts geändert, weil es nicht meine Aufgabe
   war — aber jemand sollte es entscheiden.

4. **`(frozen design record)` muss auf *einer Zeile* mit dem §** stehen,
   sonst greift der Test nicht. Das hat mehrere Kommentare zu Umbrüchen
   gezwungen, die ein Mensch anders gesetzt hätte, und es wird den nächsten
   Umsetzer ebenso zwingen. Eine Prüfung über Absätze statt Zeilen wäre
   freundlicher, aber deutlich schwerer korrekt hinzuschreiben; ich halte die
   zeilenweise Fassung für den richtigen Tauschhandel und melde die Kosten.

5. **Zwei Paragraphen haben ein zweites Ziel.** §3.2 und §5.1 sind eindeutig,
   aber §3.1, §4.2, §5 (1a), §7 und §9 haben Zitierungen, die auf
   verschiedene Seiten gehören. Der Brief sagt „je Paragraph ein Ziel"; eine
   erzwungene Einzelabbildung hätte falsche Sätze erzeugt (etwa
   „`insert_event(..., key=None)`, was `{ref}`hash-chain`` erlaubt" — erlaubt
   wird es vom Vertrag, nicht von einer Seite). Die Tabelle nennt darum das
   Zweitziel mit der Regel, die es auswählt. Das ist die eine Stelle, an der
   ich den Brief bewusst nicht wörtlich umgesetzt habe.

6. **Die `(frozen design record)`-Markierung in `DEPENDENCIES.md`** steht
   einmal über der Tabelle und nicht in den dreizehn Zellen (A11). Wenn die
   Prüfung das anders sieht, sind es dreizehn Einzeländerungen — mechanisch,
   aber die Tabelle wird davon nicht besser.
