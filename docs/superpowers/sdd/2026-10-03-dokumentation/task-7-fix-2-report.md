# Aufgabe 7 — Fixrunde 2, Bericht

**Status:** fertig. Ein Commit, `fbc7fee`, alle sechs Tore grün.
E1, E2, P1, P2, P3 behoben; die H2-Anmerkung umgesetzt.

```
fbc7fee docs: make the reference check read what it promises to read
a2671ee docs: aim six pointers at the half of the paragraph they meant
fae1c25 docs: point the code at the documentation, and keep it honest with a test
```

3 Dateien, +67/−28. Testzahl unverändert bei 194, also kein Nachziehen der
Tutorial-Ausgabe.

---

## 1. Nachmessung, bevor ich etwas angefasst habe

**E1 bestätigt.** `migrations/dsn.py:46-52` wirft `RuntimeError` mit einem
implizit verketteten f-String — dieselbe Gestalt wie die zwei Ursprungstäter —
und `docs/reference/configuration.md:13` dokumentiert die Meldung („the
migration fails with an error that names both"), sie ist also Programmausgabe.

**Deine Zählung in `tests/` bestätigt:** 9 Vorkommen, 3 Dateien
(`test_schema.py` 2, `test_contracts.py` 3, `test_properties.py` 4), **alle**
in Docstrings oder `#`-Kommentaren, keines in einem gewöhnlichen Literal. Die
AST-Prüfung wäre dort heute falschtrefferfrei.

**E2 bestätigt latent:** `grep -rn "{ref}$" src/ tests/ migrations/` → kein
Treffer. Die Form existiert heute nicht, das Loch ist latent.

**Die Ursache in einem Satz:** `_modules()` lag auf Zeile 60 und war der
Helfer; Zeile 170 nahm `(ROOT / "src").rglob` von Hand. T1 hat die Liste von
zwei Pfaden auf **ein** Verzeichnis erweitert statt auf den Helfer. Beide
Löcher dieser Runde kommen daher, dass ein Pfad neben einem vorhandenen Helfer
von Hand gegriffen wurde.

## 2. Je Punkt eine Zeile

| # | Status |
|---|---|
| **E1** | **behoben, mit `src/` + `migrations/`.** `_modules(directories)` nimmt die Verzeichnisse jetzt als Argument, `OUTPUT_DIRS = ["src", "migrations"]` ist der Satz, der Nutzer erreicht, und alle vier Prüfungen gehen durch denselben Helfer. `tests/` bleibt draußen; die Erwägung samt deiner Zählung (9 Vorkommen, 3 Dateien, alle Docstring oder Kommentar) steht in einem Kommentar über `OUTPUT_DIRS`, die Messung zu `dsn.py` im Docstring der Prüfung. |
| **E2** | **behoben durch Heilen, nicht durch Streichen der Zusage.** Jeder Rollenaufruf wird erst **gefunden** (`ROLE`), dann **geparst** (`AFTER_ROLE`, `re.S`, erlaubt Leerraum und `#` zwischen Rolle und öffnendem Rückstrich), und was keinen lesbaren Zielteil hat, landet namentlich in `unreadable`. Die Zusage auf Zeile 43 ist damit wahr, und dass sie bricht, wenn jemand sie zurücknimmt, ist in dieser Runde gemessen (E2a/E2c unten). |
| **P1** | **behoben.** Die Arithmetik geht jetzt auf: elf der zwölf eingefrorenen haben keine Seite (§10.6 achtmal, §10.7 zweimal, §8.6), **der zwölfte ist §10.1** in der `sqlalchemy`-Zeile, dessen Ergebnis in `database-schema` steht und dessen Argument nicht; die eine nicht eingefrorene ist §2. 11 + 1 + 1 = 13. |
| **P2** | **behoben.** „not one of the five **is argued** anywhere" statt „appears" — die fünf stehen jetzt genau einmal in der Doku, eine Zeile darüber. |
| **P3** | **behoben.** „six pointers that had gone to the wrong page, **four of them by taking the wrong half** of a paragraph that has two, and for two of the six the row above already named the page they wanted." Sechs und zwei bleiben, die Kennzeichnung ist eingeschränkt. |
| **H2-Anmerkung** | **umgesetzt, ich stimme zu.** `design-records.md` hat jetzt einen eigenen Absatz unter der Zwei-Klassen-Regel: `storage/postgres.py` nennt `{ref}`module-boundaries`` als **Dementi**, geschrieben, weil die Verwechslung der zwei Fragen den Zeiger überhaupt falsch geschickt hat — und es behält die gewöhnliche Form mit Absicht, „because that is what makes the gate check its label". Dein Argument gegen das Streichen des Markups trägt: ohne `{ref}` prüft das Tor den Namen nicht mehr mit, und ein Dementi, das auf eine umbenannte Seite zeigt, ist so irreführend wie eine Erklärung, die das tut. |

## 3. Die 14 Angriffe beider Runden, gegen das Ergebnis

Jede Mutation in situ, Tor gefahren, Datei byteweise aus einem Backup zurück.
`git status` nach dem Lauf sauber bis auf meine drei Dateien.

```
baseline (no mutation)                                 pass
A4   marked message in core/verify.py                  fail  (wanted fail ) ok
A4b  print() with a marked citation in cli.py          fail  (wanted fail ) ok
A5   bare citation inside the test file itself         fail  (wanted fail ) ok
A6   sixth table row that nothing produces             fail  (wanted fail ) ok
A7   float quote moved out of the cell into prose      fail  (wanted fail ) ok
A11  {ref}`hash_chain` with an underscore              fail  (wanted fail ) ok
A12  {ref}`the chain <hash-chain-typo>`                fail  (wanted fail ) ok
A13  {ref}`hash-chainn` (control)                      fail  (wanted fail ) ok
A9   marked message in canonical.py (control)          fail  (wanted fail ) ok
E1a  marked citation in migrations/dsn.py message      fail  (wanted fail ) ok
E1b  marked citation in migrations/versions/0001_log.py fail  (wanted fail ) ok
E2a  wrapped role, label does not exist                fail  (wanted fail ) ok
E2b  wrapped role, label exists (has to be READ)       pass  (wanted pass ) ok
E2c  role with no target at all                        fail  (wanted fail ) ok

unexpected results: 0
```

**Zum Nachweis für E2 gehört das Paar E2a/E2b.** Vor dem Fix waren beide grün,
weil der Verweis unsichtbar war. Jetzt fällt E2a (Label existiert nicht) und
E2b bleibt grün — das heißt, der umbrochene Aufruf wird **gelesen** und nicht
bloß durchgelassen. E2c deckt den Fall ohne Rückstrich überhaupt.

Die neun Angriffe der ersten Runde bleiben unverändert scharf, die zwei
Kontrollen A13/A9 eingeschlossen; es ist nichts verdrängt worden.

## 4. Ein eigener Fehler, den die Suite gefangen hat

Der erste Versuch von E2 lautete
`AFTER_ROLE = re.compile(r"\A(?:\s|#)*`([^`]*)`", re.S)`, angewandt mit
`AFTER_ROLE.match(text, role.end())`. Ergebnis: **jeder** Verweis im Baum kam
als `unreadable` zurück, 61 Stück.

`\A` bindet an den echten Stringanfang, nicht an `pos` — und `match()` bindet
ohnehin schon an `pos`, der Anker war nicht nur falsch, sondern überflüssig.
Der Anker ist weg und die Begründung steht neben dem Ausdruck. Erwähnenswert,
weil es genau die Klasse Fehler ist, die diese Prüfung existieren lässt: ein
Ausdruck, der etwas Wahres zu prüfen behauptet und nichts findet.

## 5. Die sechs Tore

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
194 passed in 16.57s

$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded.
✔ 0 errors, 0 warnings and 0 suggestions in 20 files.
build succeeded.
```

Dazu die CLAUDE.md-Fassung: `Required test coverage of 90.0% reached. Total
coverage: 99.80%`, `194 passed`.

Die Zahl bleibt 194 — diese Runde hat keinen Test hinzugefügt, nur den
Geltungsbereich zweier vorhandener geweitet. Die abgetippte Tutorial-Ausgabe
ist also unverändert richtig und wurde nicht angefasst.

## 6. Wo ich widerspreche

**Nichts.** Beide Löcher nachgemessen und bestätigt, alle drei Prosa-Befunde
nachgerechnet und bestätigt, und die H2-Anmerkung halte ich für richtig —
samt der Begründung, das Markup nicht zu streichen.

Zwei Anmerkungen ohne Widerspruch:

1. **E1: ich habe `src/` + `migrations/` genommen, nicht `_modules()` mit allen
   drei.** Du hast die Entscheidung mir überlassen. Ausschlaggebend war nicht
   die Falschtrefferfreiheit (die stimmt, ich habe deine Zählung bestätigt),
   sondern dass ein Tor, dessen Geltungsbereich weiter ist als sein Name, die
   Art Behauptung ist, die diese Aufgabe aus dem Baum entfernen soll — und dass
   ein `§` in einem Testliteral niemanden erreicht. Dein Gegenargument (nach
   der Umstellung kann kein Test mehr legitim eines tragen) steht als Erwägung
   im Kommentar, damit die nächste Runde es nicht neu erarbeiten muss.

2. **E3/E4 und `ast.AsyncFunctionDef` habe ich nicht angefasst**, wie
   angewiesen. Zu E3/E4 stimme ich deiner Begründung zu und möchte sie um eine
   Beobachtung ergänzen, die den Park-Entscheid stützt: die Spalte
   `Restriction` ist **Prosa über** die Meldung, und ein Tor, das Prosa gegen
   Code prüft, müsste entweder die Umformulierung festnageln (dann ist die
   Spalte keine Prosa mehr, sondern ein zweites Zitat) oder sie verstehen. Das
   erste wäre ein Rückschritt für den Leser, das zweite ist kein Tor.

Offen bleibt unverändert die **`rootdir:`-Zeile im Tutorial** — Entscheidung
des Auftraggebers, und sie hängt daran, ob `test_docs_typed_output` diese
Zeile überhaupt prüfen soll.
