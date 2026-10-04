## Task 3: Die Anleitungen, das README, das Tutorial — und der Spec friert ein

**Files:**
- Modify: `docs/how-to/verify-the-chain.md`, `docs/how-to/restore-from-a-backup.md`, `README.md`, `docs/tutorials/record-your-first-event.md`, `docs/superpowers/specs/2026-10-04-aeusserer-anker.md`, `docs/explanation/design-records.md`

**Interfaces:**
- Consumes: die Kommandos und ihre Ausgaben aus Aufgabe 2, am Baum und an `docs/reference/cli.md` abgelesen; das Label `external-anchor` aus Aufgabe 1.
- Produces: nichts, worauf Code sich stützt.

Vorher `plone-doc-style:author` aufrufen, je Quadrant: How-to ist Handlung ohne Erklärung, mit Verweisen statt Gründen; Tutorial ist ein garantierter Weg in der ersten Person Plural.

- [ ] **Schritt 1: `verify-the-chain.md`**

- „It takes no arguments" fällt.
- Der Schlussabsatz („It doesn't prove that the chain is complete …") stimmt nur noch ohne Anker. Er wird zu dem, was Rückgabecode 0 **ohne** Anker heißt, mit Verweis auf den neuen Abschnitt.
- Neuer Abschnitt `## Anchor the chain, and check against the anchors`: die Routine als zwei Kommandos, erst prüfen, dann ankern:

  ```shell
  previously verify --anchors anchors.txt && previously anchor >> anchors.txt
  ```

  Dazu: beim ersten Mal gibt es noch keine Datei, dann nur `previously anchor > anchors.txt`; die Datei gehört an einen Ort, den nicht schreiben kann, wer die Datenbank schreiben kann; `-` liest die Datei von der Standardeingabe, wenn das Kommando in einem Container läuft und die Datei draußen liegt; ein Rückgabecode ungleich 0 ist ein Alarm. **Hosting-neutral**: keine Kubernetes- und keine Compose-Syntax, nur die zwei Kommandos — sie sind in beiden gleich.
- Für das Warum ein Verweis: `` {ref}`external-anchor` ``.

- [ ] **Schritt 2: `restore-from-a-backup.md`**

Der Satz „If `previously verify` exits `0`, the restore is trustworthy" ist zu stark: ein Restore aus einem älteren Stand ist eine kürzere, in sich stimmige Kette und besteht. Die Anleitung führt künftig zwei Fälle:

- **Restore bis zum letzten Stand** (Base-Backup plus Write-Ahead-Log): `previously verify --anchors anchors.txt`. Rückgabecode 0 heißt: bis zum jüngsten Anker ist nichts verloren und nichts umgeschrieben. Was nach dem jüngsten Anker angefügt wurde, bezeugt die Prüfung nicht.
- **Restore auf einen festen Punkt, der mit einem Anker zusammenfällt:** zusätzlich `--exact`. Rückgabecode 0 heißt: die Spitze ist genau der Anker.

Und was Rückgabecode 0 **ohne** Anker bedeutet: die Kette ist in sich stimmig, mehr nicht. Die bestehenden Hinweise (Passphrase, „never rehearsed") bleiben; höchstens zwei Admonitions auf der Seite.

- [ ] **Schritt 3: `README.md`**

- „the seven commands …" → acht, `anchor` genannt.
- Der Absatz über die Grenze („a hash chain without an **outer anchor** …") stimmt nicht mehr als Beschreibung eines Mangels: es gibt den Anker jetzt. Neu fassen — was die Kette allein bezeugt, was ein Anker dazugibt, und dass gefälschtes Anhängen nur im Vergleich mit einem in Ruhe genommenen Anker auffällt. Nicht mehr zusagen, als die Tabelle auf `hash-chain.md` hält.
- „What it does not do" bleibt, wie es ist.

- [ ] **Schritt 4: Das Tutorial — die Sitzung neu tippen**

`verify` druckt jetzt eine zweite Zeile, und ein Terminal zeigt `stderr` neben `stdout`. Der `verify`-Block im Tutorial wird **aus einem echten Lauf** neu getippt, gegen den Container, den das Tutorial selbst aufsetzt (seinen eigenen Schritten folgen, frischer Container), und der Satz danach („It found nothing wrong, so it printed exactly that one line.") stimmt nicht mehr — neu fassen, mit einem „Notice that …" zur zweiten Zeile.

Danach ein kurzer neuer Abschnitt `## Pin the tip`, zwei Kommandos, getippt aus demselben Lauf:

```console
$ uv run previously anchor > anchors.txt
$ uv run previously verify --anchors anchors.txt
```

mit ihrer echten Ausgabe und einem „Notice that …": die erste Zeile ist jetzt eine andere, und der Hinweis ist weg. Keine Erklärung, was ein Anker schließt — dafür ein Verweis unter *Next steps*.

Weil die anderen Blöcke derselben Sitzung denselben Zeitstempel und denselben Hash zeigen: **die ganze Sitzung aus einem Lauf**, wie Aufgabe 8 der Stufe 1b es gemacht hat, damit die Seite sich nicht selbst widerspricht. Der `uv sync`-Block bleibt, wenn ein neuer Lauf einen Maschinenpfad druckte; die Seite sagt, dass keine Ausgabe ein Verzeichnis nennt.

Dann der Testlauf-Block, **zuletzt**, aus einem echten `uv run pytest`-Lauf. Die Zahl **messen**: `uv run pytest --collect-only -q -p no:randomly | tail -1`.

Das Rohprotokoll des Laufs, aus dem die Blöcke stammen, gehört in den Bericht — der Prüfer vergleicht dagegen.

- [ ] **Schritt 5: Der Spec friert ein**

`docs/superpowers/specs/2026-10-04-aeusserer-anker.md`: der Kopf wie bei den vier anderen, wörtlich aus `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md` (Zeilen 3 bis 14) kopiert, das Datum ist das des Commits. „Status: Entwurf, zur Abnahme" → „Status: eingefroren". Der Einleitungsabsatz, der das Einfrieren ankündigt, fällt bis auf den Satz, dass der Spec klein ist und eine Zusage einlöst.

§10 „Was offen bleibt": die Einleitung in die Vergangenheit setzen — der Abschnitt war gepflegt, solange der Spec lebte, und gibt seine fünfzehn Punkte an den Spec weiter, der ihm folgt. **Die Zahl zählen**, nicht aus diesem Satz übernehmen.

- [ ] **Schritt 6: `design-records.md` und die Tabelle im README**

`docs/explanation/design-records.md`: fünf Dokumente statt vier; der Anker-Spec dort, wo die anderen eingeführt werden — Datum, Thema, die Seiten, die seine Begründung tragen (`` {ref}`external-anchor` `` auf `hash-chain.md`; die Tatsachen in `` {ref}`cli-reference` ``, die Routinen in den zwei Anleitungen). Und die Messung, die schon für Stufe 1b dort steht, für diesen Spec wiederholen: kein `§` im Code, das auf ihn zeigt.

Run: `grep -rn "§" src tests migrations | grep -v "frozen design record"`
Erwartet: leer. Und `grep -rn "§" src tests migrations | wc -l` gegen die Zahl, die die Seite nennt — der Anker fügt keines hinzu.

`README.md`: die Tabelle der eingefrorenen Berichte bekommt die fünfte Zeile, mit Datum.

`CLAUDE.md` nicht anfassen: der Absatz über die eingefrorenen Berichte ist seit Stufe 1b ohne Zahl gefasst, damit der fünfte ihn nicht wieder falsch macht.

- [ ] **Schritt 7: Alle sechs Tore, Commit**

Erwartet: `pytest` **265 passed**, unverändert gegenüber dem Stand nach Aufgabe 2 samt ihrer Fixrunde (hier stand 263, bis die Fixrunde zwei Tests für die Standardeingabe brachte); Vale mit derselben Dateizahl wie zuvor (keine neue Seite).

```bash
git status --short
git add docs/how-to/verify-the-chain.md docs/how-to/restore-from-a-backup.md README.md \
        docs/tutorials/record-your-first-event.md docs/explanation/design-records.md \
        docs/superpowers/specs/2026-10-04-aeusserer-anker.md
git commit -F - <<'MSG'
docs: the anchoring routine, a restore in two cases, and the spec frozen

The how-to for checking the chain gains the routine: check the old
anchors, take a new one, keep the file where the database's writer cannot
write. The restore guide said that exit code 0 makes a restore
trustworthy; a restore from an older state is a shorter chain that is
consistent in itself and passes. It now asks for the anchors, and names
two cases — a restore to the latest state, checked with "contains", and a
restore to a fixed point that coincides with an anchor, checked with
--exact.

The tutorial is retyped from one run: verify shows its second line now,
and a short step pins the tip. The README says what an anchor adds and
what it does not.

The specification gets the dated header the four before it carry, and its
open points go to the specification that follows.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Nach Aufgabe 3: Endprüfung, Protokoll, Pull-Request

Sache des Controllers, nicht einer Aufgabe:

1. **Endprüfung des ganzen Zweigs**, mit zwei Paketen wie bei Stufe 1b (Code und Konfiguration; englische Doku), dem Spec als Datei.
2. **Eine Fixwelle** für ihre Befunde, eine Nachprüfung.
3. **Das Ausführungsprotokoll** nach `docs/superpowers/sdd/2026-10-04-aeusserer-anker/`, als eigener Commit, unverändert kopiert, mit `index.md`. Erst danach das Arbeitsverzeichnis unter `.superpowers/` löschen.
4. **Push und Pull-Request.** Der Merge ist die Abnahme (`CLAUDE.md`).

Prüfer schreiben ihren Bericht in eine Datei im Arbeitsverzeichnis des Plans und geben ein kurzes Verdikt zurück; der Controller tippt keine Berichte ab.

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** §1 Lieferungen 1–5 → Aufgaben 1 (Ankerzeile, Kern), 2 (`anchor`, `verify --anchors`, Hinweis), 1+2+3 (Doku). §1.1 Korrektur → Aufgabe 1 Schritt 10 (Seite), Tests zum Anhängen und zur Grenze. §1.2 zwei Einstiege → Aufgabe 1 (`examine` liefert `Examination`), Aufgabe 2 (`cli` liest und formatiert nur). §2 Format und Fehler → Aufgabe 1 Schritte 2–5. §3 `anchor` → Aufgabe 2. §4 Argumente, Prüfarten, Befunde, Meldungen, Rückgabecodes → Aufgabe 1 Schritt 7 und Aufgabe 2 Schritte 3 und 6. §5 Tabelle und Zusage → Aufgabe 1 Schritt 10; §5.1 Betrieb → Aufgabe 3 Schritte 1 und 2. §6 Schnitt → Dateistruktur. §7 Zusicherungen 1–9 → 1: beide Tests zur gelöschten Spitze (Kern und CLI); 2: Umschreiben; 3: Anhängen; 4: Grenze; 5: `test_anchor.py` und der parametrisierte CLI-Test; 6: `anchor` auf leerem Log und gebrochener Kette; 7: `verify` ohne Anker; 8: `test_anchor.py`; 9: Aufgabe 2 Schritt 7. §8 Doku → Aufgaben 1, 2, 3. §9 Abnahme 1–12 → 1–4: Aufgabe 1; 5–7: Aufgabe 2; 8: Aufgabe 1 (`verify` behält Signatur) und `lint-imports`; 9: die Mutationstabellen; 10: Aufgabe 3; 11: jede Aufgabe; 12: Aufgabe 3 Schritte 5 und 6.

**Nicht gedeckt und bewusst so:** der Tabellentest aus §10 Punkt 11 (oben begründet).

**2. Platzhalter.** Kein „TBD". Die Doku-Schritte tragen Seitenspezifikationen mit Muss-Inhalt und, wo ein Test daran hängt, den Wortlaut.

**3. Namenskonsistenz.** `Anchor(id, hash)`; `parse_anchors`, `format_anchor`; `Examination(findings, tip)`; `examine(storage, *, anchors, exact, batch)`; `verify(storage, *, batch)`. Die drei Befundtexte stehen gleichlautend in *Vertragliche Wortlaute*, in `examine`, in den Tests beider Aufgaben und im Block für `cli.md`. Der Hinweis steht gleichlautend in `_cmd_verify`, in `_HINT` (mit Zeilenende) und im Block für `cli.md`.

**4. Testzahlen**, am Plantext gezählt: `test_anchor.py` zwei einfache Tests, ein parametrisierter mit sieben Fällen, einer mit zwei → 11. `test_verify.py` acht neue. Aufgabe 1: 232 + 19 = **251**. `test_cli.py` acht einfache Tests und ein parametrisierter mit vier Fällen → 12. Aufgabe 2: 251 + 12 = **263**. Aufgabe 3: **263**. Jede Zahl ist eine Vorhersage, die der Umsetzer nachzählt. *Nachtrag 2026-10-04:* gemessen 251, 263 und nach der Fixrunde der Aufgabe 2 **265**; Aufgabe 3 fügt keinen Test hinzu und steht damit bei 265.

**5. Review Focus.** 1 → `test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read`; 2 → `test_a_broken_anchor_file_is_an_input_error` und `test_a_directory_as_anchor_file_is_an_input_error`; 3 → `test_anchors_are_checked_across_a_batch_boundary`; 4 → `test_an_empty_log_has_no_tip_and_misses_every_anchor`; 5 → der Fall `²` in `test_a_broken_line_is_refused_with_its_line_number`.
