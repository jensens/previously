# Aufgabe 7 — Fixrunde 1, Bericht

**Status:** fertig. Ein Commit, `a2671ee`, alle sechs Tore grün.
Alle 16 Befunde behoben.

```
a2671ee docs: aim six pointers at the half of the paragraph they meant
fae1c25 docs: point the code at the documentation, and keep it honest with a test
```

13 Dateien, +193/−79.

---

## 1. Die vier schweren Befunde, selbst nachgemessen

Ich habe die vier gegengemessen, bevor ich sie umgesetzt habe. **Alle vier
stimmen.**

```
$ for s in "no update" "no delete" "transaction control" "passthrough" "database object"
  do grep -ril "$s" docs --include=*.md | grep -v _build | grep -v superpowers; done
(leer für alle fünf)                                               → H2 bestätigt

$ grep -rn "ISO 8601\|fractional digits" docs --include=*.md | grep -v _build | grep -v superpowers
docs/reference/cli.md:27,43,61        (CLI-Ausgabe, nicht die Hashform)
docs/explanation/canonicalization.md:108
docs/reference/hash-format.md:78      ← die einzige Stelle mit der Hashform
                                                                   → H3 bestätigt

$ grep -rln "print(" src/
src/previously/cli.py                 (die einzige)                → T1 bestätigt

$ grep -o "code>[^<]*</code>label[^<]*" docs/_build/html/explanation/design-records.html
code class="docutils literal notranslate"><span class="pre">{ref}</span></code>label``, and
                                                                   → H4 bestätigt
```

Dazu H1 gegen die Zielseite: `docs/reference/hash-format.md:33` schließt den
Abschnitt mit „For why the range is drawn here and not wider, see
{ref}`canonicalization`" — die Seite dementiert selbst, das Warum zu tragen.

## 2. Je Befund eine Zeile

| # | Status |
|---|---|
| **H1** | **behoben.** `canonical.py` nennt jetzt beide, die Begründung zuerst: „…is in {ref}`canonicalization`; {ref}`payload-range` lists the restriction itself." |
| **H2** | **behoben.** `postgres.py:6` → `architecture §5, frozen design record`, mit einem Satz, der sagt *warum* (die fünf Eigenschaften haben keine Seite) und was `module-boundaries` stattdessen regelt. Tabellenzeile „§5 \| architecture" → „nowhere; frozen design record", mit eigenem Absatz unter der Tabelle. |
| **H3** | **behoben.** `test_hashing.py:49` → `{ref}`hash-format``. Die Tabellenzeile §3.3 nennt jetzt `hash-format` zuerst und `timestamps` für die zweite Hälfte („why the caller sets the value"). |
| **H4** | **behoben.** `` `` {ref}`label` `` `` mit doppelten Rückstrichen und Randabstand. Gerendert nachgemessen: `<code>{ref}`label`</code>`, keine stehengebliebenen Rückstriche mehr. |
| **M1** | **behoben.** `append.py:74` → `{ref}`concurrency``. |
| **M2** | **behoben.** `append.py:427` → `{ref}`concurrency``. „the contract permits" bleibt. Tabellenzeile §5 (1a) um `concurrency` erweitert. |
| **M3** | **behoben.** `test_verify.py:268` → `{ref}`canonicalization``, und der Satz umgestellt, damit das Label am Grund steht und nicht an der Zurückweisung. Tabellenzeile §3.2 um `canonicalization` erweitert — damit hat der häufigste Paragraph sein Zweitziel. |
| **M4** | **behoben.** „…stays, which is what the idempotency is for ({ref}`canonicalization`)." Dein Vorschlag wörtlich. |
| **T1** | **behoben.** `test_no_program_output_cites_a_specification` läuft über `sorted((ROOT / "src").rglob("*.py"))`. `RUNTIME_MESSAGE_FILES` ist weg. Die Messung („mit zwei genannten Pfaden gingen eine markierte Meldung in `core/verify.py` und ein `print` in `cli.py` durch; `cli.py` ist mit dreizehn `print`-Aufrufen die einzige druckende Datei") steht im Docstring. |
| **T2** | **behoben.** `_quoted_messages()` liest die Spalte `Message` der Tabelle „Payload range" (Abschnitt zwischen `## Payload range` und dem nächsten `## `), und der Vergleich ist **Mengengleichheit** in beide Richtungen. Dazu ein eigener Test für das sechste Zitat der Seite, `type set not allowed`, das in Prosa steht und von niemandem gedeckt war. |
| **T3** | **behoben.** `REFERENCE = \{ref\}`([^`]*)`` fängt jeden Rollenaufruf, `TARGET` zerlegt ihn in die zwei Formen (bare / `Titel <ziel>`), Unterstriche eingeschlossen. Was in keine Form passt, landet in `unreadable` und ist ein **Fehler**, keine Stille. |
| **T4** | **behoben, deinen dritten Weg.** `SECTION = chr(0xA7)`, `SELF` und das `continue` weg, das illustrative `§3.1` in Zeile 93 ist Prosa („A bare paragraph number"). Die Datei enthält das Zeichen nicht mehr (`grep -c § tests/test_docs_references.py` → 0) und prüft sich mit. Die `.py`-Begründung („die Trennlinie ist nicht die Dateiendung, sondern wie die Stelle gelesen wird") steht im Modul-Docstring, mit `DEPENDENCIES.md` und `pyproject.toml` als den zwei Beispielen. |
| **D1** | **behoben.** „Twelve of the thirteen … point into a frozen design record", mit §10.6/§10.7/§8.6 als die elf, die **keine** Seite haben, und §2 als die Ausnahme, die auf `module-boundaries` verlinkt. Der Link auf `design-records.md` sagt jetzt, was dort steht („its table maps the twenty paragraphs that the **code** cites, which are not the ones below"). |
| **D2** | **behoben.** „Die lebende Begründung steht in der Dokumentation unter `docs/`". |
| **D3** | **behoben.** „— soweit sie dort steht; wo sie fehlt, ist dieses Dokument die einzige Quelle." Dazu verlinkt die Kopfzeile jetzt `../../explanation/design-records.md` für „Das Einfrieren als **Ablauf**, und die Karte von jedem zitierten Paragraphen zu seiner Seite". In allen drei Specs gleich. |
| **D4** | **behoben.** Ein `{ref}`design-records`` im Modul-Docstring von `tests/test_docs_references.py` — das Tor, das die Konvention durchsetzt, zeigt auf die Seite, die sie definiert, und prüft dabei seinen eigenen Verweis mit. Dazu der Wegweiser-Satz oben auf der Seite: „If you arrived from a paragraph number in a comment, the table under *Where each cited paragraph went* is the map…". |

### Nicht geändert, wie angewiesen

Die nackte Zitierung in `pyproject.toml` kommt weiter durch, und die Begründung
dafür steht jetzt im Docstring des Tests statt in einem Bericht. Unangetastet:
die GitHub-Zahlen in `backup-encryption.md`, alle Zitierungen auf Prüfbefunde
(`W3`, `G-7`, `N-1`, `T7-g`, `T10-b`, `T10-d`, `B1`, `G-1`, `G-2`, `W1`, `W4`,
`W-1`, `K-1`), und die `rootdir:`-Zeile im Tutorial.

## 3. Die Angriffe des Prüfers, gegen das Ergebnis nachgefahren

Jede Mutation in situ eingespielt, Tor gefahren, Datei byteweise aus einem
Backup zurückgespielt. Der Baum ist unangetastet (`git status` nach dem Lauf
leer).

```
baseline (no mutation)                               pass
A4  marked message in core/verify.py                 fail  (wanted fail)  ok
A4b print() with a marked citation in cli.py         fail  (wanted fail)  ok
A5  bare citation inside the test file itself        fail  (wanted fail)  ok
A6  sixth table row that nothing produces            fail  (wanted fail)  ok
A7  float quote moved out of the cell into prose     fail  (wanted fail)  ok
A11 {ref}`hash_chain` with an underscore             fail  (wanted fail)  ok
A12 {ref}`the chain <hash-chain-typo>`               fail  (wanted fail)  ok
A13 {ref}`hash-chainn` (control, was already caught) fail  (wanted fail)  ok
A9  marked message in canonical.py (control)         fail  (wanted fail)  ok

unexpected results: 0
```

Die zwei Kontrollen (A13, A9) bleiben scharf — die Verschärfungen haben nichts
verdrängt. Das Skript liegt unter dem Scratchpad.

## 4. Eine falsche Zahl, die ich beim Umsetzen selbst erzeugt hatte

Ich hatte die Lehre aus dem Prüfbericht auf die Seite geschrieben als „found
three citations that had landed on the wrong half, and in two of the three the
row above already named the page they wanted". **Nachgezählt stimmt das
nicht**, und zwar in beiden Zahlen: es sind sechs fehlgeleitete Zeiger (H1,
H2, H3, M1, M2, M3), und nur bei zwei davon stand die Antwort schon in der
eigenen Zeile:

| Zeiger | Antwort stand in der Zeile? |
|---|---|
| H1 §3.2 → `canonicalization` | nein (die Zeile hatte nur `payload-range`) |
| H2 §5 Arch. → eingefroren | nein (die Zeile war selbst falsch) |
| H3 §3.3 → `hash-format` | **ja** |
| M1 §4.2 → `concurrency` | **ja** |
| M2 §5 (1a) → `concurrency` | nein |
| M3 §3.2 → `canonicalization` | nein |

Die Seite sagt jetzt „six pointers … for two of the six". Dein „zwei der drei"
im Prüfbericht meint §3.3 und §3.1 — §3.1 war aber kein Befund, sondern eine
bestätigte Korrektur, also nicht Teil der Menge.

## 5. Zahlen im Bericht, nachgezogen

Alle vier deiner Korrekturen nachgemessen und bestätigt, und die Lage hat sich
durch diese Runde noch einmal verschoben:

| | Bericht 1 | nachgemessen | jetzt |
|---|---|---|---|
| identischer Satz in `DEPENDENCIES.md` | 9× | **8×** | 8× |
| Label aus dem Code benutzt | 15 | **12** | 12 |
| Label ohne jeden Verweis | 4 | **5** | **4** |
| Label insgesamt | 19 | **20** | 20 |
| `{ref}` im Code | 58 | 58 | **60** |
| eingefrorene Zitierungen | 13 | 13 | **14** |

Die vier ohne Verweis sind jetzt `add-a-migration`, `first-event-tutorial`,
`hash-domain`, `restore-from-a-backup`; `design-records` ist durch D4
dazugekommen, `timestamps` hält sich über die Tabellenzeile §3.3.

Bilanz der 72 nach dieser Runde: **14** eingefroren + **2** aus
Programmausgaben gestrichen + **56** auf eine Seite gezeigt. Die 60 `{ref}` im
Code sind diese 56 plus vier, die keiner ursprünglichen Zitierung entsprechen:
zwei im neuen `canonical.py`-Kommentar (H1 nennt beide Hälften), eines im neuen
`postgres.py`-Satz (H2 behält die Nummer und nennt daneben, was
`module-boundaries` wirklich regelt), und `design-records` im Test (D4).
Die Seite trägt diese Zahlen jetzt so.

## 6. Die sechs Tore

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
194 passed in 16.41s

$ make -C docs html && make -C docs vale && make -C docs linkcheck
build succeeded.
✔ 0 errors, 0 warnings and 0 suggestions in 20 files.
build succeeded.
```

Dazu die CLAUDE.md-Fassung: `Required test coverage of 90.0% reached. Total
coverage: 99.80%`, `194 passed`.

193 → 194: der neue Test für `type set not allowed` (T2). Das Tor
`test_docs_typed_output` hat die abgetippte Ausgabe im Tutorial beanstandet,
und sie ist als Letztes aus einem echten Lauf neu abgetippt (Seed 181972377,
`194 passed in 16.39s`).

## 7. Wo ich eine Anweisung für falsch halte

**Keine der sechzehn.** Alle vier schweren habe ich gegengemessen, alle vier
stimmen, und bei H2 stimmt auch die Begründung für die Dringlichkeit: der
Zeiger behauptete, eine Begründung sei in die Doku gewandert, die niemand
geschrieben hat.

Drei Punkte, bei denen ich über das Angewiesene hinaus oder knapp daneben
gegangen bin — als Abweichung gemeldet, nicht als Widerspruch:

1. **H1 nennt zwei Label statt eines.** Du hast `{ref}`canonicalization``
   verlangt. Ich habe „…is in {ref}`canonicalization`; {ref}`payload-range`
   lists the restriction itself" geschrieben. Grund: der Kommentar sitzt über
   einem `raise`, dessen Meldung genau die eine Restriktion ist, die in der
   Tabelle steht — ein Leser, der die Meldung sucht, will die Tabelle, und
   wer das Warum sucht, die Erklärung. Die Reihenfolge erfüllt deine
   Anweisung (die Begründung zuerst), und beide Hälften stehen da, wo diese
   Runde sie hingehören sieht.

2. **H2 behält `module-boundaries` im Satz.** Die Zitierung ist jetzt
   eingefroren, aber ich habe angehängt: „{ref}`module-boundaries` settles
   which module may import which, not which methods this one has." Grund:
   genau diese Verwechslung hat den Fehler erzeugt, und ein Leser, der die
   fünf Eigenschaften in `module-boundaries` sucht, soll erfahren, dass er
   dort richtig *und* falsch ist. Wenn du das für Rauschen hältst, ist es
   eine Zeile.

3. **N7 (`ast.AsyncFunctionDef`, Attribut-Docstrings) habe ich nicht
   umgesetzt**, und es stand nicht auf deiner Liste. Grund, über
   „heute unerreichbar" hinaus: der Fehler, den die Lücke erlaubt, ist ein
   **Falschtreffer** — ein `async def`-Docstring mit Paragraphenzeichen würde
   als Programmausgabe gemeldet. Das Tor würde also klagen, nicht
   schweigen; die Lücke fällt zur sicheren Seite. Dazu verlangt CLAUDE.md für
   eine ausdrückliche Zusage einen Test, der bricht, wenn jemand sie
   zurücknimmt, und in einem bewusst synchronen Projekt (Architektur §10.6)
   gibt es nichts, womit man ihn schreiben könnte. Eine ungetestete
   Erweiterung wollte ich nicht einbauen; melde es gern als Befund zurück,
   dann ist es ein Token.

Ein Bedenken bleibt offen, unverändert aus Bericht 1: **die `rootdir:`-Zeile
im Tutorial** nennt den Worktree-Pfad. Das ist deine Entscheidung, nicht
meine, und sie hängt daran, ob `test_docs_typed_output` die Zeile überhaupt
prüfen soll.
