# Aufgabe 6, Fixrunde 1 — Bericht

Zweig `worktree-dokumentation`, Worktree `.claude/worktrees/stufe-1a-log`, BASE `ed84bf5`.

Alle acht Befunde **selbst nachgemessen, bevor ich sie behoben habe** — keiner auf Zuruf
übernommen. Alle acht bestätigt, keiner zurückgewiesen. Dazu ein neunter, den ich beim
Nachrechnen des vierten gefunden habe (Befund 9 unten).

Geändert: `docs/explanation/concurrency.md`, `docs/explanation/module-boundaries.md`,
`docs/explanation/silent-losses.md`, `docs/reference/hash-format.md`, und die zwei
freigegebenen Kommentarstellen `src/previously/core/append.py` und
`tests/test_contracts.py`. Nichts sonst.

---

## Befund 1 — die Backoff-Zahlen

**Behoben.** Zweimal nachgemessen, einmal rechnerisch und einmal durch Zählen der
`time.sleep`-Aufrufe mit einem Stub-Storage, der `ChainPositionTaken` wirft:

```
MAX_RETRIES       : 8
upper bounds      : [0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.2, 0.2]
sum of all eight  : 0.715
sum of first seven: 0.515
seven times cap   : 1.4000000000000001
at the cap        : [6, 7]

raised: ChainConflict chain position not acquired after 8 attempts — …
number of sleeps performed: 8
waits drawn: [0.004956, 0.004305, 0.016557, 0.032671, 0.012002, 0.065669, 0.091033, 0.08177]
```

Alle drei Teilbefunde stimmen: acht Wartezeiten, nur die Versuche 6 und 7 am Deckel,
und `7 × 0.2 = 1.4 s` widerspricht „under a second". Die gezogenen Werte zeigen
nebenbei, wie weit unter den Obergrenzen `random.uniform(0, upper_bound)` im Mittel
landet — in diesem Lauf 0,299 s gegen 0,715 s Obergrenzensumme.

`concurrency.md:49` trägt jetzt die Obergrenzenliste, die Zahl `0.715`, und ausdrücklich,
dass es Obergrenzen und nicht Wartezeiten sind. Die achte Wartezeit habe ich **genannt**,
obwohl sie laut Auftrag optional war — nicht als Warze, sondern weil die Rechnung ohne sie
nicht aufgeht: wer „acht Versuche" liest, zählt sieben Lücken und kommt auf 0,515 s. Der
Satz, der das klarstellt, ist genau der Satz, dessen Fehlen den Fehler erzeugt hat.

**Die Quelle mitgezogen** (`src/previously/core/append.py:73-86`, erste der zwei
freigegebenen Kommentarstellen): dieselben Zahlen, dazu drei Zeilen, die festhalten, was
dort vorher stand und warum es sich selbst widersprach. Die Zitierung
`(§4.2 of the 1a spec, review finding W3)` steht unberührt in Zeile 73, wie angeordnet.

## Befund 2 — „half of the permitted edges"

**Behoben.** Selbst nachgezählt, Importe je erlaubtem Modulpaar:

```
cli -> core         : 5
cli -> storage      : 3
cli -> contract     : 2
core -> storage     : 8
core -> contract    : 3
storage -> contract : 0
contract -> anything: 0
```

Fünf von sechs erlaubten Kanten existieren, einzig `storage → contract` nicht. „Die
Hälfte" stimmt unter keiner Zählweise. `module-boundaries.md:37` sagt jetzt „five of the
six edges the order permits"; die fehlende Kante wird eine Zeile vorher ohnehin
namentlich genannt, darum nenne ich sie nicht zweimal.

## Befund 3 — „eight of the eleven fields that could be forged"

**Behoben.** Gegen `core/hashing.py` geprüft: `event_hash` schreibt elf Schlüssel, und
die ersten zwei sind `"v": HASH_VERSION` und `"domain": HASH_DOMAIN` — Modulkonstanten
aus Zeile 35-36, keine Zeilenwerte. Fälschbar sind sie nicht.

Heilung über das Minimum hinaus, weil der Relativsatz die rhetorische Last trug:
`covered eight of the eleven hashed fields—and the three it left out are exactly where
the three forgeries landed.` Die drei weggelassenen Felder sind `units`, `source` und
`external_id`; die drei gemessenen Fälschungen waren Einheiteninhalt, gelöschte Einheit
und Quellenangabe. „exactly where … landed" statt einer 1:1-Paarung, weil zwei der drei
Fälschungen dasselbe Feld treffen.

## Befund 4 — drei Schweigen, nicht zwei

**Behoben.** Nachgeprüft, dass der CRLF-Fall wirklich ein Schweigen ist: Spec §6
(`stufe-1a-log.md:766-783`) führt vier Schritte auf — trennen, Leerraum entfernen, leere
Abschnitte verwerfen, von 1 an nummerieren —, keiner nennt Zeilenenden. Und:

```
grep -cin "CRLF\|Zeilenende\|\\r" docs/superpowers/specs/2026-10-02-stufe-1a-log.md
0
```

Null Treffer im ganzen 1a-Spec. Es ist ein drittes Schweigen.

Die Begründung des Prüfers, warum das „as it was about" nicht als Beispiel trägt, halte
ich für richtig, und ich habe die Zweiteilung gleich ganz aufgelöst — siehe Befund 5, der
dieselbe Textstelle betrifft.

## Befund 5 — der Grabstein ist eine dritte Kategorie

**Behoben.** Gegen `stufe-1a-log.md:403-406` geprüft, wörtlich: „Der Code prüft
`row.payload is None`, diese Spezifikation schreibt `payload IS NULL` vor — die beiden
waren damit nie äquivalent." Die Behauptung „In every case the code did what the
specification said" trug für diesen Fall also nicht.

Befund 4 und 5 fallen auf denselben Absatz, darum habe ich ihn als Rechnung neu gebaut
statt zwei Flicken zu setzen. `silent-losses.md:60-66` zählt jetzt **1 + 3 + 1 = 5**:
eine falsche Zusage (der Hash-Bereich), drei Schweigen (Zeilenenden, Schlüsselkollision,
Stapel-Duplikat) und der Grabstein als eigene Art — eine Vorgabe, die in Python nur unter
einer Voraussetzung umsetzbar war, die die Spezifikation voraussetzte und nichts erzwang,
weshalb die Korrektur in die Voraussetzung ging (`event_payload_object_check`) und nicht
in die Prüfung.

Die fette Zusage „Not one of them was a programming error" steht unverändert, und sie
steht jetzt auf einer Begründung, die auch den Fall abdeckt, der am meisten wie einer
aussieht. „In every case the code did what the specification said" ist weg; an seine
Stelle ist der Satz getreten, der trägt: *at the level a review reads, the implementation
agreed with the plan.*

## Befund 6 — „verbatim"

**Behoben.** Gegenübergestellt: Spec `stufe-1a-log.md:702-703` liest
`payload {'note': 'the second'}       -> NICHT gespeichert`, die Seite liest
`payload of the second entry   ->  NOT stored`. Übersetzt **und** verallgemeinert, also
in keiner Lesart wörtlich. `silent-losses.md:74` sagt jetzt „quote their measurements
rather than summarizing them".

## Befund 7 — der absolute Warnkasten in der Reference

**Behoben.** Gegenübergestellt: `hash-format.md:82-85` verbot unbedingt, während
`canonicalization.md:112-114` seit `a816d4f` „almost never" sagt und die Ausnahme samt
ihrem Erkennungszeichen nennt. Nach dem Einfrieren wären das zwei maßgebliche Seiten mit
entgegengesetzter Aussage. Der vorgeschlagene Satz steht jetzt im Kasten, mit Verweis auf
`{ref}`canonicalization``.

## Befund 8 — „the missing gate"

**Behoben, und das wahre Argument ist stärker, als auch der Prüfbericht es fasst.**

Erst in einer Kopie von `src/` und `pyproject.toml` im Scratchpad: Import aus dem
`TYPE_CHECKING`-Block gezogen, an die sortierte Stelle gesetzt, damit `I001` den Befund
nicht verdeckt —

```
TC001 Move application import `previously.storage.postgres.PostgresStorage`
      into a type-checking block
  --> …/src/previously/core/append.py:42:41
Found 1 error.
```

Dann dieselbe Kopie plus **einen Laufzeitgebrauch** des Symbols
(`if not isinstance(storage, PostgresStorage):`) — `All checks passed!`. Die zweite
Hälfte der Prüferbehauptung stimmt also auch.

`lint-imports` ist aus einer Kopie nicht messbar: grimp analysiert das **installierte**
Paket, und das venv zeigt editierbar auf das echte `src/`. Diese eine Messung lief darum
im Baum, mit sofortiger Rücknahme über `git checkout --`:

```
uv run lint-imports                     Contracts: 4 kept, 0 broken.
uv run ruff check .                     All checks passed!
uv run pytest tests/test_contracts.py   1 failed
    test_the_exempted_core_modules_load_no_sql_at_runtime
    -> loaded sqlalchemy at runtime
```

Danach `git status`: `src/` unberührt, `lint-imports` wieder `4 kept, 0 broken`,
`tests/test_contracts.py` wieder `3 passed`.

Das ist der vollständige Dreiklang, den der Prüfbericht nur zur Hälfte hatte: im Fall,
der weh tut, schweigen **beide** statischen Tore und der Vertragstest ist das Einzige,
was bleibt. `module-boundaries.md:125-150` trägt diesen Messblock; die alte, unvollständige
Messung (`lint-imports` gegen den Test, ohne ruff) ist ersetzt statt daneben gestellt,
weil zwei konkurrierende Messblöcke zum selben Vorgang die nächste Drift wären. „the
missing gate" ist weg; „redundancy beside `lint-imports`" heißt jetzt „beside
`lint-imports` and `TC001`".

Dazu der zweite freigegebene Kommentar, `tests/test_contracts.py:182-187`: „without any
one of the five gates going off. This test is that missing gate." ist durch die
gemessene Fassung ersetzt. Nebeneffekt, den ich mitnehme statt ihn stehen zu lassen: die
Zahl „five gates" war ohnehin überholt — CLAUDE.md zählt sechs. Die neue Fassung nennt
keine Zahl, sondern die Tore, die sie meint.

Der Prüfer gibt die Stelle als `:181-182` an; es sind `:182-183`. Ohne Folgen.

## Befund 9 — von mir dazu, gleiche Art, gleiche Stelle

**Behoben.** Beim Nachrechnen von Befund 4/5 fiel auf: der Absatz „Each was a gap between
a promise and the world" listete **vier** Zusagen für **fünf** Verluste. Der
`evidence`-Schlüssel fehlte. Das stand schon in `ed84bf5` so und ist in der Prüfung nicht
aufgefallen — aber weil ich den Absatz direkt darüber zu einer ausdrücklichen Rechnung
gemacht habe, zählt der Leser jetzt erst recht mit.

Der Absatz führt jetzt fünf Zusagen, in der Reihenfolge der fünf Abschnitte der Seite,
und der Einleitungssatz sagt „and there are five of those too".

---

## Was ich für falsch halte

**Nichts in der Sache.** Alle acht Befunde habe ich eigenständig nachgemessen und alle
acht bestätigt; die vorgeschlagenen Heilungen waren in sieben Fällen tragfähig und in
einem (Befund 8) habe ich mehr gemessen, als der Vorschlag verlangte, weil die
Messung dann auch die zweite Hälfte des Arguments deckt.

Drei Anmerkungen, die keine Widersprüche sind:

**1. Gate 3 ist rot, und zwar schon vor dieser Runde.** `uv run pyright` meldet drei
Fehler, alle in `tests/test_schema.py:295` (`reportUnknownMemberType`,
`reportUnknownArgumentType` ×2 auf einem `.get(...)`-Aufruf). Diese Datei habe ich nicht
angefasst. Nachgewiesen, nicht vermutet: meine zwei Dateien beiseitegelegt,
`git checkout --` auf beide, `git diff --stat HEAD -- src/ tests/` leer,

```
uv run pyright  ->  3 errors, 0 warnings, 0 informations
```

also identisch rot bei unverändertem `ed84bf5`. Danach meine zwei Dateien zurückgelegt.
Der Auftrag sagt „alle sechs" Tore — dieses kann ich nicht grün machen, ohne
`tests/test_schema.py` anzufassen, und das ist keine der zwei freigegebenen
Kommentarzeilen. **Das gehört vor das Einfrieren**, aber es ist eine eigene Runde: der
Fehler liegt in einem Test, den Aufgabe 5 angelegt hat (`5e2eced`, *test(schema): mark the
new test as needing a database*), und eine Typkorrektur dort ist eine Codeänderung mit
eigenem Urteil.

**2. Die achte Wartezeit habe ich genannt, obwohl sie optional war.** Begründung oben
unter Befund 1: ohne sie geht die Summe nicht auf, und eine Zahl, deren Herleitung der
Leser nicht nachrechnen kann, ist genau die Sorte Zahl, die diese Fixrunde beseitigt. Das
Verhalten selbst ist unberührt, der Ledger-Eintrag bleibt stehen.

**3. Befund 8 hat mehr Text gekostet als „ein Satz nach `:128`".** Der vorgeschlagene
Einschub hätte neben der alten, unvollständigen Messung gestanden — zwei Messblöcke zum
selben Vorgang, einer davon ohne ruff. Ich habe den Abschnitt stattdessen umgebaut:
eine Messung, vollständig, und die Behauptung „the gate would report nothing" auf
`lint-imports` eingeengt, wo sie stimmt. Wenn das mehr ist als freigegeben war, ist es
hier benannt.

---

## Tor-Ausgaben

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
38 files already formatted

$ uv run pyright
3 errors, 0 warnings, 0 informations     <- tests/test_schema.py:295, vorbestehend,
                                            bei unverändertem ed84bf5 identisch

$ uv run lint-imports
Contracts: 4 kept, 0 broken.

$ uv run pytest -q
189 passed in 16.66s

$ make -C docs html
build succeeded.

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 19 files.

$ make -C docs linkcheck
build succeeded.          (output.txt: 0 Bytes)
```

Vale hat einmal zugeschlagen und eine Formulierung erzwungen:
`module-boundaries.md:134` „`core` **really** does load SQLAlchemy" →
`Microsoft.Adverbs`, umformuliert zu „does load SQLAlchemy for real".

**189 Tests unverändert.** Die zwei Code-Änderungen sind ein Blockkommentar und ein
Docstring; keine Zeile ausführbaren Codes ist berührt, und `git diff` bestätigt es:
`src/previously/core/append.py` +13/−5 (nur Kommentarzeilen),
`tests/test_contracts.py` +8/−3 (nur Docstringzeilen).
