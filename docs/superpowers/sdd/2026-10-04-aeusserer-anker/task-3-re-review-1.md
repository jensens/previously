# Task 3 — Re-Review nach Fix-Runde 1

Fix-Basis `a09f56a`, Kopf `da79b41`, Diff aus `review-a09f56a..da79b41.diff` (einmal gelesen, nicht neu gebaut).

### Finding verdicts

- **Important 1 — zweiter Restore-Fall gegen die ganze Datei mit `--exact`: ADDRESSED.**
  Die fünf Tatsachen aus T3-c stehen auf der Seite und stimmen mit dem Code:
  1. Gegen die ganze Datei meldet jeder spätere Anker `anchored event is missing (the log ends at <tip>)`, Rückgabe 1, und das ist erwartet — `docs/how-to/restore-from-a-backup.md:39-52`; die zitierte Zeile `FINDING 3: anchored event is missing (the log ends at 2)` steht wörtlich im Protokoll (Schritt 4), Format aus `_closing_findings` (`core/verify.py:301-304`).
  2. Prüfung gegen die Datei, wie sie am Restore-Punkt stand, mit einer schlichten Shell-Zeile — `:55-72` (`cat -n`, `head -n 2 … > anchors-restored.txt`), im Protokoll Schritt 4.
  3. Die Zeile finden: Spitze aus dem Befund, letzte Zeile deren `id` nicht darüber liegt — `:57`, `:65`.
  4. `--exact` nur, wenn die `id` der letzten Zeile die Spitze ist, sonst die gewöhnliche Prüfung mit derselben Grenze wie im ersten Fall — `:74-89`; Erfolgszeile `chain intact, 2 anchors hold, the tip is the newest anchor` im Protokoll.
  5. Danach läuft die Routine gegen die geschnittene Datei, die alte bleibt unverändert als Aufzeichnung — `:91-93`; im Protokoll Schritt 5.
  *Read the result* folgt: `:97` bindet Rückgabe 1 an „the anchor file that fits your case".
  Zwei neue Lücken in genau diesem Abschnitt stehen unten unter *New breakage* (N1, N2); sie heben das Verdikt für den Befund selbst nicht auf, weil der Befund — ein korrekter Restore wird verworfen — so nicht mehr eintritt.
- **Important 2 — „came back from the write-ahead log": ADDRESSED.** `restore-from-a-backup.md:33-34` sagt beide Richtungen: was nach dem jüngsten Anker da ist, ist nicht verbürgt; was dort sein sollte und fehlt, sieht die Prüfung nicht. Deckt Tabellenzeile 3 (`tip deleted, above the newest anchor | not seen | not seen`).
- **Minor 1 — erstes Ankern und Routine: ADDRESSED.** `verify-the-chain.md:41-45`: Rückgabe 0 und genau eine Zeile prüfen; leeres Log → nichts auf stdout, 0, leere Datei (gemessen, Protokoll Schritt 1, die Meldung `the log is empty: nothing to anchor` geht auf stderr, `cli.py:291-293`); Befund → `FINDING`-Zeilen auf stdout, 1 (`cli.py:286-290`, im Bericht als aus dem Code genommen markiert). `:56`: zweites Kommando ≠ 0 → Zeilen von Hand entfernen.
- **Minor 2 — Einleitungssatz: ADDRESSED.** `restore-from-a-backup.md:5`, und der Titel `:3` mit demselben Auge geändert. (Folge siehe N3.)
- **Minor 3 — Rückgabe 2: ADDRESSED.** `restore-from-a-backup.md:100-101`; stimmt mit `cli.py:506-516` (`PreviouslyError`, `StorageError` → 2) und `cli.md` Abschnitt `verify`. Fehlende Datei gemessen (Protokoll, „extra").
- **Minor 4 — README-Punkt: ADDRESSED.** `README.md:38-42`; „up to the newest anchor nothing can go missing or be rewritten unseen" = Tabellenzeilen „deleted below/at an anchor" und „rewritten", nichts darüber hinaus.
- **Minor 5 — `design-records.md`: ADDRESSED.** `docs/explanation/design-records.md:26`, „…, up to the newest anchor."
- **Neuer Absatz `hash-chain.md` (T3-d): ADDRESSED.** `docs/explanation/hash-chain.md:363-366`, unter `(external-anchor)=` nach dem Lücken-Absatz. Begründet, keine Schritte, verspricht nichts über die Tabelle hinaus (ein Restore auf einen früheren Punkt ist eine gelöschte Spitze; die Anker darüber melden „missing", wahr). Die Restore-Seite verweist dorthin (`:53`).

### New breakage in the fix diff

**N1 — Important — `restore-from-a-backup.md:57-65`: die Schnittregel kennt den Fall nicht, dass kein Anker auf oder unter der Spitze liegt.**
Mit einer Datei, die die Routine selbst erzeugt: Restore auf einen Stand vor dem ersten Anker (Basis-Backup älter als der Beginn des Ankerns, oder ein leeres Log, Spitze `0`). Jeder Anker meldet `missing`, „the last anchor line whose `id` isn't above that tip" gibt es nicht, und die Seite lässt den Betreiber ohne nächsten Zug. Wer trotzdem schneidet, bekommt mit `head -n 0` eine leere Datei; `verify` gibt dann 2 (`parse_anchors`, `core/anchor.py:59-60`: „the anchor file holds no anchor"), und `:100` beschreibt diesen Fall nicht einmal („a line in it isn't an anchor line" — es gibt keine Zeile). Nach der Bewertungsregel des Auftrags (Fall aus einer routine-erzeugten Datei) Important.
Fix, ein bis zwei Sätze: liegt kein Anker auf oder unter der Spitze, beschreibt keiner das wiederhergestellte Log; dann bleibt nur `previously verify` ohne `--anchors` (`:103-104`), und die Routine beginnt mit einem ersten Anker in einer neuen Datei wie in {ref}`verify-the-chain`.

**N2 — Important — `restore-from-a-backup.md:51-57`: im zweiten Fall leitet die Prüfung ihren Maßstab aus dem Ergebnis ab, und damit lässt sich ein echter Verlust wegreden** (Bedenken 2 des Umsetzers, beantwortet).
Die Schnittstelle wird aus der beobachteten Spitze bestimmt (`:57`), nicht aus dem beabsichtigten Restore-Punkt. Gegen eine so geschnittene Datei kann `anchored event is missing` per Konstruktion nicht mehr auftreten: jede Zeile der Schnittdatei hat `id ≤ tip`. Die Prüfung in Fall 2 findet also nur noch Umschreibungen, nie eine Kürzung — gleich ob das WAL-Replay früher als beabsichtigt stehen blieb oder ob der Betreiber in Wahrheit auf den neuesten Stand wiederherstellen wollte. Die Befunde sehen in beiden Fällen identisch aus; `:51` sagt „Expect these findings here", `:52` „Don't discard the instance because of them", und nirgends steht, dass der Betreiber die Spitze mit dem Punkt vergleichen muss, auf den er zurückstellen *wollte*. Wer um drei Uhr nach einem missglückten Replay die Befunde sieht und zum Abschnitt mit „Expect these findings" springt, geht mit Rückgabe 0 hinaus. Der erste Abschnitt sagt auch nicht ausdrücklich, dass dort jedes `missing` ein Verlust ist; das steht nur indirekt über `:97`.
Herkunft: der Wortlaut der Tatsache „How to find the line" stammt aus Ruling T3-c; der Umsetzer hat ihn befolgt. Der Leserschaden ist trotzdem auf der Seite.
Fix: vor dem Schnitt die Spitze gegen das Ziel prüfen lassen — z. B. „Confirm that the tip is where you meant the restore to end: `previously show <tip>` … If the log ends earlier than you meant, the restore lost events; that is a failed restore, see *Read the result*." — und im ersten Abschnitt ein Satz: dort ist jedes `anchored event is missing` ein Verlust, nicht zu schneiden.

**N3 — Minor — `README.md:89` zitiert den alten Titel als Linktext:** „[How to check that a restore brought the chain back](docs/how-to/restore-from-a-backup.md)". Durch die Titeländerung veraltet (Abweichung 2 des Umsetzers; der Auftrags-`grep` findet genau diese Zeile). Der Treffer in `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-report.md:267` ist eingefrorener Bericht und bleibt; die Treffer in `docs/_build/` waren der alte, git-ignorierte Build vor meinem `make html`.

**N4 — Minor — `restore-from-a-backup.md:48` und `:68-71`: im Beispiel fallen `id` und Zeilennummer zusammen** (Spitze `2`, Zeile `2`, `head -n 2`). Ein Leser kann die `2` für die Spitze halten und `head -n <tip>` tippen. In einer Datei der Routine weichen beide ab, sobald der erste Anker nicht bei `id 1` lag oder die Routine Duplikate angehängt hat (Protokoll Schritt 5). Mit `head -n <tip>` bei 500 Events und 30 Zeilen nimmt man die ganze Datei, bekommt wieder `missing` und Rückgabe 1 — und `:97-98` sagt „Discard". Zur Bedenken 3: „For that line as line 2" ist für den sorgfältigen Leser eindeutig; ein Halbsatz „the line number from `cat -n`, not the `id`" oder ein Beispiel mit abweichenden Zahlen schließt es.

**N5 — Minor — `restore-from-a-backup.md:35`, „although nothing is missing"**: die Begründung gegen `--exact` behauptet wieder, was keine Prüfung sieht (dieselbe Art wie Important 2, zwei Zeilen darüber gerade behoben). Fix: „… reported as a finding, and that finding says nothing about loss."

**N6 — Minor — `restore-from-a-backup.md:39`:** ein Restore auf einen früheren Punkt, der noch *über* dem jüngsten Anker liegt, hat keinen Abschnitt. Er gehört in der Sache zum ersten Fall (Prüfung gegen die ganze Datei, Rückgabe 0, gleiche Grenze); ein Halbsatz im ersten Abschnitt („… or to any point after the newest anchor") genügt.

Zur Schnittregel (Prüfung 2) im Einzelnen: `the log ends at <tip>` nennt die `id` der letzten gelesenen Zeile, also die höchste vorhandene `id` (`core/verify.py:273`, `:298`). Gleiche `id` zweimal (routine-erzeugt, Schritt 5): die Duplikate stehen hintereinander, „die letzte" Zeile nimmt beide mit — richtig. Nicht aufsteigend: kommt aus der Routine nicht vor (sie hängt nur nach bestandener Prüfung an, die Spitze wächst monoton); in einer von Hand bearbeiteten Datei kann „letzte Zeile mit `id ≤ tip`" eine höhere Zeile davor einschließen → `missing` gegen die Schnittdatei — Minor, nur von Hand erzeugbar, nicht separat aufgeführt. Kein Anker ≤ Spitze: N1. `cat -n` und `head -n` zählen beide physische Zeilen, Kommentar- und Leerzeilen eingeschlossen — konsistent.

### Out-of-scope observations

1. **Duplikatzeilen der Routine (Bedenken 1).** Gemessen in Schritt 5: ohne neues Event hängt die Routine dieselbe Zeile erneut an; `cli.md:74` erlaubt das, und `n anchors hold` zählt Zeilen (`cli.py:271`). Für die Prüfung harmlos, für die Schnittregel ebenfalls (siehe oben). Ein Satz auf `verify-the-chain.md` nach der Routine wäre nützlich, damit ein Betreiber eine mit Läufen wachsende Zahl nicht für Events hält und sich nicht über wiederholte Zeilen wundert; nicht blockierend, und er wäre zugleich der Kontext für N4.
2. Nach dem Wechsel auf `anchors-restored.txt` muss der Betreiber die Routinezeile aus `verify-the-chain.md` (die `anchors.txt` nennt) anpassen; `:91` sagt das hinreichend.

### Checks run

- Gelesen: `task-3-review.md` (Issues), `task-3-fix-1-dispatch.md`, Diff-Datei, `task-3-report.md` § Fix round 1 samt Protokoll.
- Code gegen Seiten: `_closing_findings`, `examine` (`core/verify.py:199-309`), `parse_anchors` (`core/anchor.py:24-61`), `_read_anchors`, `_cmd_verify`, `_cmd_anchor`, Ausnahmebehandlung in `main` (`cli.py:155-295`, `:506-516`), `cli.md` Abschnitt `verify`; `core/append.py:348` (neue `id` = Spitze + 1).
- Jede zitierte/beschriebene Ausgabe gegen das Protokoll: späterer Anker `missing` (Schritt 4) ✓; Erfolgszeile mit `--exact` (Schritt 4) ✓; leere Datei nach `anchor` auf leerem Log (Schritt 1) ✓; `--exact` auf gewachsenem Log (Schritt 3, `FINDING 4: the log continues past the newest anchor (3)`) ✓; Rückgabe 2 bei fehlender Datei ✓; `FINDING` auf stdout bei Befund — aus dem Code, im Bericht markiert ✓.
- `grep -rn "brought the chain back" docs README.md` → `README.md:89` (N3), ein eingefrorener SDD-Bericht, alter Build.
- `grep -c ':::{'` → Restore-Seite 1, `verify-the-chain.md` 0: keine dritte Admonition.
- Diff-Dateiliste: nur `README.md`, `design-records.md`, `hash-chain.md`, `restore-from-a-backup.md`, `verify-the-chain.md` — kein Hunk in `docs/superpowers/specs/`, `docs/reference/cli.md`, Tutorial, `src/`, `tests/`.
- Form: ein Satz pro Zeile in allen hinzugefügten Zeilen; nichts Hosting-Spezifisches (`cat -n`, `head -n`, `previously …`); der `hash-chain.md`-Absatz ohne Schritte, die Guides verweisen für das Warum.
- `make -C docs html` → „The HTML pages are in _build/html."
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly` → `6 passed in 1.14s`.
- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected in 0.18s` (Tutorial-Block bleibt gültig).
- Der Bericht nennt alle sechs Tore mit Schlusszeile — vollständig. Nicht selbst gelaufen (laut Auftrag): `ruff check`, `ruff format --check`, `pyright`, `lint-imports`, volles `pytest --cov`, `linkcheck`. Keine eigene Datenbank-Sitzung: das Protokoll beantwortet jede Frage, N1 folgt aus `parse_anchors` und `head -n 0`.

### Verdict

Alle acht Punkte der Fix-Runde sind ADDRESSED. Die Fix-Runde führt aber zwei neue Important-Lücken in den neuen Abschnitt „Restore to an earlier point" ein: N1 (kein Anker unter der Spitze — Betreiber ohne nächsten Zug) und N2 (der Schnitt aus der beobachteten Spitze macht eine Kürzung in Fall 2 unsichtbar und erlaubt, einen echten Verlust als Restore auf einen früheren Punkt zu lesen; Herkunft Ruling T3-c). Dazu vier Minor (N3–N6). Eine weitere Runde ist nötig, sie betrifft wenige Sätze auf `restore-from-a-backup.md` und `README.md:89`.
