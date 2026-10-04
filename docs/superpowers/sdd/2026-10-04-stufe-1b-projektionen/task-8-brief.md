## Task 8: Einfrieren, Design-Records, Tutorial zuletzt

**Files:**
- Modify: `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, `docs/explanation/design-records.md`, `docs/tutorials/record-your-first-event.md`

- [ ] **Schritt 1: Der Spec friert ein**

Oben in den Spec, unter dem Titel, der Kopf — Wortlaut wie bei den drei anderen (aus `2026-10-02-stufe-1a-log.md` kopieren und das Datum setzen):

```markdown
> **Eingefrorener Entwurfsbericht, Stand <Datum des Commits>.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in der Dokumentation unter
> `docs/` — soweit sie dort steht; wo sie fehlt, ist dieses Dokument die
> einzige Quelle. Weicht es von der Doku ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen. Das Einfrieren als **Ablauf**, und die
> Karte von jedem zitierten Paragraphen zu seiner Seite, stehen in
> [About the frozen design records](../../explanation/design-records.md).
```

„Status: Entwurf, zur Abnahme" → „Status: eingefroren". Der Absatz unter dem Titel („Dieser Spec entsteht auf Deutsch … Bis dahin ist er das maßgebliche Dokument") wird gestrichen — der Kopf sagt es.

**§10 „Was offen bleibt"** wandert nicht mit dem Spec in die Vergangenheit: der Abschnitt bekommt einen Satz, dass er mit dem Einfrieren seine Pflege verliert und seine Punkte in den Spec der nächsten Stufe gehören — und dass der äußere Anker darunter ist.

- [ ] **Schritt 2: `design-records.md`**

Den 1b-Spec in die Liste der eingefrorenen Berichte aufnehmen (Datum, Thema, welche Seiten seine Begründung tragen: `projections`, `module-boundaries`). In der Abbildungstabelle: 1b-Code zitiert **keine** Paragraphen des 1b-Specs — er zitiert `{ref}`-Label von Anfang an, weil `test_no_bare_paragraph_references_remain` ein nacktes `§` nicht durchlässt. Das ist einen Satz wert: die erste Stufe, deren Code nie auf den Spec zeigte, weil die Seiten mit dem Code entstanden.

Run: `grep -rn "§" src/previously/core/projection src/previously/contract/store.py src/previously/contract/rows.py`
Erwartet: nur Verweise auf die **Architektur** mit `(frozen design record)` — keiner auf den 1b-Spec. Zahl in den Bericht.

- [ ] **Schritt 3: Das Tutorial, als Letztes**

Nach dem Abschnitt `## Look at the event in full` drei neue Abschnitte, **als echter abgetippter Lauf** gegen den Container aus dem Tutorial:

`## Build the derived views` — `uv run previously project`, Ausgabe zwei Zeilen `built: 1 event, up_to_id 1`. „Notice that both say `built`: nothing existed, so the worker built from scratch. Run it again and both say `up to date`."

`## Read the chronicle` — `uv run previously chronicle`, zwei Zeilen (zwei Einheiten). „Notice that each line is one unit, and each carries `email` and the message identifier — the source attribution, which is what makes this a chronicle and not a copy of `log`."

`## Count per source` — `uv run previously stats`, eine Zeile.

Dann den Testlauf **neu abtippen** — die Zahl ist jetzt 232 und `test_docs_typed_output.py` hält sie gegen den Baum. **Ohne** die `rootdir:`-Zeile (die Seite sagt am Ende des Blocks, dass sie ausgelassen ist). Kein Maschinenpfad.

Run: `uv run pytest tests/test_docs_typed_output.py -v`
Erwartet: `PASSED`.

- [ ] **Schritt 4: Alle sechs Tore, Commit**

```bash
git add -A
git commit -F - <<'MSG'
docs: freeze the stage 1b specification, and type out the new commands

The spec gets the dated header the three before it carry: its explanation
pages stand, so from here the pages are the authority and the spec is
provenance. Its open points keep the external anchor at the top and move
to the next stage's spec by rule.

`design-records.md` lists it, and notes the one thing new about it: no
line of stage 1b code cites a paragraph of this spec, because the pages
were written alongside the code and the gate refuses a bare paragraph
sign. The tutorial gains project, chronicle and stats as a typed run, and
the test run is retyped last at 232.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

## Selbstprüfung dieses Plans

**1. Spec-Deckung.** §1 Lieferungen → Aufgaben 1 (Protokoll), 2+3+5 (Maschinerie), 4+5 (zwei Projektionen), 6 (Kommandos). §1.1 Korrekturen → Aufgabe 1 (zwei Protokolle, Kommentar in `.importlinter`), 5 (Arbeiter als Kommando, kein `job`), 5+7 (Tilgungsfund als Test und Abschnitt), 8 (`show` bleibt, steht in §10). §2 → Aufgabe 1 und 3; die Gegenprobe §2.3 → Aufgabe 1 Schritt 8. §3 → Aufgabe 2 (Tabellen) und 3 (Zeilentypen). §4 → Aufgabe 5, inklusive `!=` (Schritt 4 und Review Focus 4) und `ProjectionGap` für §4.2. §5 → Aufgabe 4 (Mutation auf `merge`) und 5 (alle neun Zusagen aus §5.4 haben einen Test; Entschärfung, Rückstand und Kappung in Aufgabe 6). §6 → Aufgabe 6, mit den Korrekturen 2–4 oben. §7 → Aufgabe 4/5 (Paketstruktur mit vier Dateien statt drei — `worker.py` zusätzlich, um den Importzirkel zu vermeiden; der Spec sagt drei und das ist eine Präzisierung, keine Abweichung). §8 → `database-schema.md` (2), `projections.md` (2, 5, 6, 7), `module-boundaries.md` (1), `cli.md` (6), How-to (7), Tutorial (8), Design-Records (8), Einfrieren (8). §9 Abnahmebedingungen: 1→A1 S6, 2→A1 S8, 3→A5, 4→A5 S6, 5→A5, 6→A5, 7→A5, 8→A3+A6, 9→A6, 10→A6, 11→A5, 12→A4, 13→jede Aufgabe, 14→A8. §10 → Aufgabe 8 Schritt 1.

**Nicht gedeckt und bewusst so:** Spec §2.2 nennt `truncate_projection` mit `name` und die Einfüge-/Aktualisierungsmethoden tabellenspezifisch — gemischte Abstraktionsebene, im Plan so übernommen, weil `core` kein `Table` kennen darf und die Tabellen keine gemeinsame Zeilenform haben.

**2. Platzhalter.** Kein „TBD", kein „analog zu Aufgabe N". Die Doku-Schritte tragen Seitenspezifikationen (Abschnitte mit Muss-Inhalt und Messung) — die Form, die der Doku-Plan vom 2026-10-03 etabliert hat.

**3. Namenskonsistenz.** `escape_field` (nicht `_escape`) in Aufgabe 6 Test und Code — der Test oben zeigt die Falle und löst sie im Text; `Outcome.rebuilt_from` mit den drei Bedeutungen in Aufgabe 5 definiert und in `_describe` (6) genau so gelesen; `ProjectionState(name, up_to_id, version, built_at)` positional in Tests, benannt im Worker — gleiche Reihenfolge wie die Dataclass; `_PROJECTION_TABLES`-Schlüssel `"chronicle"`/`"source-stats"` = `ChronicleProjection.name`/`SourceStatsProjection.name` = `projection_state.name` in den CLI-Reads. Testzahlen je Aufgabe: 193, 194, 202, 211, 223, 232, 232, 232 — jede eine Vorhersage, die der Umsetzer **nachzählt**. (Die erste Fassung dieses Plans sagte 229 für Aufgabe 6, zählte nach und fand acht — dann brachte der Vorab-Scan den Test für das leere Log, und es sind wieder neun; die Zahl im Plan blieb zwei Commits lang bei 228 stehen, bis sie beim Nachführen der Aufgabe-5-Zahlen gegen die `def test_` im Text gezählt wurde. Aufgabe 5 bekam in Fixrunde 1 drei Tests dazu, weil `ProjectionGap` gemessen für keine Lücke feuern konnte. Beides zusammen: 223 und 232.)

**4. Review Focus.** Alle fünf haben einen Test: 1 → A6 (`…empty_window_is_not_truncated`), 2 → A6 (`…rejects_a_naive_since`), 3 → A6 (`escape_field`-Test), 4 → A5 (`…lower_code_version_rebuilds_too`), 5 → A5 (`…empty_log…`) und A6 (`project` auf leerem Log).

**Zwei Warnungen an den Ausführenden.** Erstens: `_FailingStore` in Aufgabe 5 muss **jede** Methode von `ProjectionStore` haben, sonst meldet pyright, und die Versuchung ist, das Protokoll zu kürzen — falsch herum. Zweitens: die Spaltenindizes in `_snapshot`-Assertions (`r[6]`, `stats_row[3]`) sind an die Tabellenreihenfolge gebunden; wer `p_chronicle` eine Spalte voranstellt, bricht die Tests, und das ist gewollt.
