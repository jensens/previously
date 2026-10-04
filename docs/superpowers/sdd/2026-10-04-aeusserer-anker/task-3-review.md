# Task 3 — Review (Doku, Tutorial, Spec eingefroren)

Basis `1df139c`, Kopf `a09f56a`, ein Commit, sechs Dateien. Gelesen: Brief bis `## Nach Aufgabe 3`, Dispatch, Bericht, Diff-Datei; außerhalb des Diffs je ein gezielter Blick (unten unter *Checks run* mit Risiko benannt).

### Spec Compliance

- ✅ `docs/how-to/verify-the-chain.md:8` — „It takes no arguments." ist weg.
- ✅ `docs/how-to/verify-the-chain.md:13` — Rückgabecode 0 ohne Anker: `chain intact` auf stdout plus Hinweis auf stderr, stimmt mit `_cmd_verify` (`src/previously/cli.py:258-270`).
- ✅ `docs/how-to/verify-the-chain.md:24-26` — Schlussabsatz auf „ohne Anker" umgestellt: in sich stimmig, mehr nicht; die drei Manipulationen der Kette allein; Verweis auf den neuen Abschnitt.
- ✅ `docs/how-to/verify-the-chain.md:28-60` — Abschnitt `## Anchor the chain, and check against the anchors`: Ort der Datei, erstes Mal ohne Datei, die Routine wörtlich (`:44`), `-` für stdin (`:54`), Rückgabecode ≠ 0 als Alarm, Verweise auf `cli-reference` und `external-anchor`. Keine Kubernetes- oder Compose-Syntax, keine Admonition.
- ✅ `docs/how-to/restore-from-a-backup.md` — „the restore is trustworthy" ist weg; zwei Fälle; `--exact` nur im Festpunkt-Fall; was Rückgabecode 0 ohne Anker heißt (`:52-53`). Die eine Admonition (`important`, „never rehearsed") steht; vorher war es auch nur eine (der Passphrase-Hinweis ist Fließtext), keine neue dazu.
- ❌ `docs/how-to/restore-from-a-backup.md:36-45` — der Festpunkt-Fall funktioniert so geschrieben nur, wenn der Anker der **jüngste** in der Datei ist (Important 1).
- ❌ `docs/how-to/restore-from-a-backup.md:33` — ein Satz behauptet, was die Prüfung nicht sieht (Important 2).
- ✅ `README.md:38-39` — acht Kommandos, `anchor` genannt; Grenzabsatz neu gefasst, Zeile für Zeile mit der Tabelle auf `hash-chain.md` vereinbar; „What it does not do" unverändert; fünfte Tabellenzeile `:84` mit Datum und den Seiten.
- ✅ `docs/tutorials/record-your-first-event.md` — jede Sitzungs-Ausgabe gleicht dem Rohprotokoll Zeichen für Zeichen (Zeitstempel `2026-10-04T13:24:54.151385+00:00`, Hash `52a060a8734b…` in `log`, `show`, `chronicle`, `stats`; die `project`-Blöcke `:147-158` sind unverändert und gleichen dem Protokoll ebenfalls); `verify`-Block mit zweiter Zeile; `## Pin the tip` nach `## Check the chain`, mit echter Ausgabe und „Notice that"; keine Erklärung des Ankers, Verweis unter *Next steps*.
- ✅ Testblock: `collected 265 items` = `265 passed` = gemessene 265; Summe der Dateizahlen 25+49+13+5+24+4+8+3+9+2+1+12+9+30+6+15+11+26+13 = 265; kein `rootdir:`.
- ✅ `docs/superpowers/specs/2026-10-04-aeusserer-anker.md:3-14` — per `diff` gegen Zeilen 3–14 der 1b-Spec: identisch. `Status: eingefroren`. §10: 15 Punkte selbst gezählt (1–4 neu, 5–10 aus 1b §10, 11–15 aus dem 1b-Protokoll), Einleitung nennt „fünfzehn".
- ✅ `docs/explanation/design-records.md:5-6,26-28,91-93` — fünf Dokumente, „the other two on 2026-10-04"; jede Fundstelle von „four"/„three"/„five" geprüft: die übrigen „three"/„five" zählen anderes (drei Tabellen, drei Kommandos, fünf Eigenschaften, §4.2-Aufteilung) und sind richtig. Labels lösen auf (`html` grün).
- ✅ „fifteen" (`design-records.md:92`): `grep … | wc -l` → 15, `grep -v "frozen design record"` → leer; konsistent mit der Seite selbst (12 verbliebene der 72 plus 3 aus Stufe 1b = 15). Der Satz „lines that hold one" ist richtig formuliert (Zeilen, nicht Zitate).
- ✅ Sechs Dateien, keine weitere; `CLAUDE.md` unberührt.
- ⚠️ Commit-Trailer (`Assisted-By:`, kein `Co-Authored-By`) aus dem Diff-Paket nicht prüfbar — die Nachricht steht nicht darin, und git-Kommandos waren untersagt. Bericht behauptet `Assisted-By: Claude Opus 5.5`.
- ⚠️ „the same fifteen as before the anchor was built" stützt sich auf den `git grep main`-Vergleich des Berichts; nicht selbst nachgemessen (git untersagt).

### Strengths

- Die Restore-Anleitung hat den zu starken Satz nicht nur gestrichen, sondern sagt jetzt ausdrücklich, was Rückgabecode 0 ohne Anker heißt, samt dem Grund, an dem ein Leser hängenbleibt: „a restore from an older state is a shorter chain that passes as well" (`restore-from-a-backup.md:53`).
- Der Warnsatz gegen `--exact` beim Restore bis zum letzten Stand (`:34`) trägt die dritte leicht verlorene Tatsache korrekt ins Handeln.
- Der README-Grenzabsatz (`README.md:50-58` im Diff) hält alle drei Tatsachen: Anhängen fällt nur gegen einen in Ruhe genommenen Anker auf, eine gelöschte Spitze über dem jüngsten Anker „shows nowhere".
- Der Kopf des Specs per Skript kopiert und mit `diff` identisch; §10 gezählt statt übernommen.
- Das Tutorial ist wirklich ein Lauf; die Begründung für den belassenen `uv sync`-Block (Maschinenpfad) ist im Protokoll belegt.
- `verify-the-chain.md` bleibt hosting-neutral und löst den Container-Fall mit einer Zeile Shell statt mit Manifest.

### Issues

#### Critical

Keine.

#### Important

1. **`docs/how-to/restore-from-a-backup.md:36-45` — der Festpunkt-Fall scheitert mit der Datei, die die Routine erzeugt.**
   `--exact` vergleicht die Spitze mit dem **jüngsten** Anker der Datei (`cli.md:77`), und „contains" verlangt jeden Anker der Datei. Die Routine aus `verify-the-chain.md:44` hängt laufend Anker an. Wer auf einen früheren Punkt zurückstellt, der mit einem älteren Anker zusammenfällt, und dann wie geschrieben `previously verify --anchors anchors.txt --exact` ausführt, bekommt für jeden späteren Anker `anchored event is missing` und Rückgabecode 1 — und `:49-50` sagt dann: „the restore failed … Discard the instance and restore again." Ein korrekter Restore wird verworfen, und jede Wiederholung scheitert gleich. Ein Schritt, der so geschrieben nicht funktioniert.
   Fix: sagen, dass der Anker die letzte Zeile der geprüften Datei sein muss — gegen eine Kopie der Datei prüfen, die mit diesem Anker endet (z. B. die Zeilen bis einschließlich dieses Ankers). Gleich mitsagen, was danach mit `anchors.txt` geschieht: die späteren Anker beschreiben einen Log, den es nicht mehr gibt, und die Routine würde sonst ab jetzt bei jedem Lauf Alarm schlagen. (Spec §5.1 schweigt dazu — er schreibt das Falsche nicht vor, also nicht plan-mandated.)

2. **`docs/how-to/restore-from-a-backup.md:33` — „The events after the newest anchor came back from the write-ahead log, and this check doesn't vouch for them."**
   Der erste Halbsatz stellt als Tatsache hin, was die Prüfung nicht sehen kann: Hat das WAL-Replay vor dem Ende aufgehört, fehlen Events über dem jüngsten Anker, und die Prüfung besteht trotzdem — Zeile 3 der Tabelle (`tip deleted, above the newest anchor | not seen | not seen`). Ein eiliger Betreiber liest: „was nach dem Anker kam, ist zurück, nur nicht beglaubigt". Der Satz ist aus Spec §5.1 übernommen, wo er die *Begründung* für „enthält" statt `--exact` ist; auf einer How-to-Seite wird er zur Zusage.
   Fix etwa: „Whatever the restored log holds after the newest anchor, and whatever it should hold there but doesn't, this check doesn't see."

#### Minor

1. **`docs/how-to/verify-the-chain.md:35-39` — erstes Ankern ohne Prüfung des Ergebnisses.** Auf leerem Log druckt `anchor` nichts auf stdout und gibt 0 zurück (`cli.py:291-293`), `> anchors.txt` hinterlässt eine leere Datei, und `parse_anchors` (`core/anchor.py:59-60`) macht daraus beim nächsten Lauf Rückgabecode 2. Auf gebrochener Kette landen die `FINDING`-Zeilen (stdout) in der Datei. Die Bedingung „Once the log holds at least one event" deckt den ersten Fall ab, sagt aber nicht, wie man es feststellt, und der zweite Fall ist ungenannt. Dasselbe gilt im Wettlauf für `>> anchors.txt` in der Routine (`:44`): bricht die Kette zwischen den beiden Kommandos, vergiftet die Ankerdatei sich dauerhaft. Fix: „Check that the exit code is `0` and that the file holds one line" nach dem ersten Ankern; für die Routine reicht der Alarm, aber ein Satz, dass die Datei dann von Hand bereinigt wird, hilft.
2. **`docs/how-to/restore-from-a-backup.md:5` — Einleitung „confirm, after any restore, that you got the chain back"** verspricht mehr als die Seite jetzt hält (bis zum jüngsten Anker; ohne Anker nur Stimmigkeit). Fix: „… how to check, after a restore, how much of the chain you got back."
3. **`docs/how-to/restore-from-a-backup.md:47-53` — *Read the result* kennt 1 und 0, nicht 2.** Eine fehlende oder kaputte Ankerdatei ist Rückgabecode 2 (Eingabefehler) — gerade nach einem Restore ein naheliegender Fall. Ein Satz mit Verweis auf `cli-reference` genügt.
4. **`README.md` „What it does" ohne Anker-Aufzählungspunkt.** Ein Leser erfährt aus dem Grenzabsatz, dass es einen äußeren Anker gibt und was er hinzufügt, und aus der Kommandozeile, dass es `anchor` gibt — die Verbindung beider (dass `anchor` den Anker erzeugt und `verify --anchors` ihn prüft) muss er erschließen; jede andere Fähigkeit hat ihren Punkt. Durch „Nothing else" in Resolution 4 so verlangt (plan-mandated, aber Politur, daher Minor). Fix: ein Punkt „**the external anchor** (`anchor`, `verify --anchors`) — …".
5. **`docs/explanation/design-records.md:26` — „the anchor is the one reference point outside the database that can"** [say something about completeness], ohne die Einschränkung „up to the newest anchor". Auf einer Explanation-Seite, die auf `external-anchor` verweist, nicht gefährlich, aber ungeschützt. Fix: „… that can, up to the newest anchor."
6. **Spec-Einleitung behält einen Satz mehr als der Brief** (`2026-10-04-aeusserer-anker.md:17-19`, wer die Zusage wann gab). Kein Befund in der Sache: Provenienz ist genau das, wofür ein eingefrorener Bericht da ist, und der Satz ist wahr. Nur als Abweichung vom Wortlaut des Briefs festgehalten — beibehalten empfohlen.

Zu den fünf Bedenken des Umsetzers, einzeln:
- *Routine nicht als eine Zeile gelaufen:* die Zeile ist syntaktisch und semantisch richtig (`&&` verhindert Ankern nach Befund, Rückgabecode der Zeile ist ≠ 0 bei jedem Fehler); Randfälle unter Minor 1.
- *„Once the log holds at least one event":* gegen `_cmd_anchor` und `parse_anchors` richtig; unvollständig nur, wie unter Minor 1.
- *Spec-Einleitung:* gehört hinein (Minor 6, keine Änderung nötig).
- *README ohne Anker-Punkt:* Minor 4.
- *„fifteen":* gemessen und wahr; der umgebende Satz stimmt (siehe Compliance).

### Checks run

- `diff` der Zeilen 3–14 beider Specs (Skratch-Dateien) → identisch.
- `awk` über §10 des Anker-Specs → Punkte 1–15, lückenlos.
- `grep -niE "\b(four|three|five|fifteen)\b" docs/explanation/design-records.md` → alle Treffer gesichtet.
- `grep -rn "§" src tests migrations | grep -v "frozen design record"` → leer; `… | wc -l` → 15; Dateien: 7.
- Außerhalb des Diffs, je ein Risiko: `docs/explanation/hash-chain.md` ab `(external-anchor)=` (Risiko: Zusage über die Tabelle hinaus); `src/previously/cli.py` `_cmd_verify`/`_cmd_anchor` und `core/anchor.py` `parse_anchors` (Risiko: erstes Ankern auf leerem Log); Spec §5.1 und `docs/reference/cli.md` `--exact` (Risiko: Festpunkt-Fall gegen eine gewachsene Ankerdatei → Important 1); `grep -c ':::'` auf der Restore-Seite vor und nach (Risiko: dritte Admonition → eine vorher, eine nachher); `grep` der `project`-Blöcke im Tutorial (Risiko: Block aus anderem Lauf → gleicht dem Protokoll).
- `make -C docs html` → „The HTML pages are in _build/html." (grün).
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly` → `6 passed`.
- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected`.
- Nicht selbst gelaufen (laut Auftrag): `ruff check`, `ruff format --check`, `pyright`, `lint-imports`, volles `pytest --cov`, `linkcheck`. Der Bericht nennt alle sechs Tore mit Schlusszeile — vollständig.

### Assessment

**Task quality:** Needs fixes

Sorgfältige, gemessene Arbeit: Tutorial, Spec-Kopf, Zählungen und README halten. Aber die Restore-Anleitung hat einen Schritt, der mit der Ankerdatei aus der eigenen Routine einen korrekten Restore verwerfen lässt, und einen Satz, der über dem jüngsten Anker mehr behauptet, als die Prüfung sieht — beides auf der Seite, auf die sich ein Betreiber im Ernstfall verlässt.
