## Task 7: How-to, README, der Tilgungsfund, Vokabular

**Files:**
- Create: `docs/how-to/rebuild-a-projection.md`
- Modify: `docs/how-to/index.md`, `docs/explanation/projections.md`, `README.md`, `.vale-styles/config/vocabularies/Previously/accept.txt`

- [ ] **Schritt 1: Das How-to**

`docs/how-to/rebuild-a-projection.md`, Label `(rebuild-a-projection)=`, Titel `# Rebuild a projection`. How-to-Ton: „This guide shows you how to …", Handlung ohne Erklärung, Verweise statt Begründung. Drei Abschnitte:

- `## Check how far behind a projection is`: `previously chronicle` oder `stats` laufen lassen; eine Zeile auf `stderr` nennt den Rückstand; Schweigen heißt aktuell. Dann `previously project`.
- `## Force a rebuild after a change to the derivation`: die `version` der Projektion im Code erhöhen (`ChronicleProjection.version` beziehungsweise `SourceStatsProjection.version`), `previously project`, Ausgabe `rebuilt: version N -> M`. Dass die Tabellenstruktur davon unberührt bleibt und eine Strukturänderung eine Migration ist — ein Satz, Verweis auf `{ref}`add-a-migration``.
- `## Force a rebuild without a code change`: `DELETE FROM projection_state WHERE name = 'chronicle'` in `psql`, dann `previously project` → `built: …`. Mit `:::{warning}`: bis zum nächsten `project` ist die Chronik leer, und jedes Lesekommando sagt das auf `stderr`.

Toctree in `docs/how-to/index.md` ergänzen. Verweis am Ende: „For why a rebuild yields the same rows as the incremental path, see {ref}`projections`."

- [ ] **Schritt 2: `projections.md` abschließen**

`## What a chronicle per unit teaches about erasure`: der Fund aus Spec §1.1 — eine Tilgung setzt `payload` auf `NULL`, die Einheiten bleiben, die Chronik zeigt den Inhalt weiter; was das für ein künftiges Tilgungs-Event heißt (Einheiten mittilgen oder den Inhalt nicht getilgt haben); dass `p_source_stats.units` dann ohne Neubau falsch wird; dass `test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` das heutige Verhalten festnagelt. Verweis `{ref}`tombstone-seam``.

Dann die Seite als Ganzes lesen: ein Quadrant (Explanation — kein „do this", keine Faktentabelle, die in die Reference gehört), ein Satz pro Zeile, Überschriften in Satzschreibung ohne Akronyme, höchstens zwei Admonitions. Jede Zahl darin (`0.715`? nein — hier: Stapelgröße 2, zehn Events, `up_to_id 4`, 8 Zeilen, 25 Beispiele) gegen die Tests **abgelesen**.

- [ ] **Schritt 3: README**

Abschnitt `## State`: „Stage 1a is built and runs" → „Stages 1a and 1b are built and run". In **What it does** drei Punkte: Projektionen, die aus dem Log ableitbar und wegwerfbar sind, mit `projection_state` und Versionsneubau; die Chronik je Einheit mit Quellenangabe, in Zeitordnung; die Quellenstatistik. In **What it does not do**: „no projections (header, chronicle as a view — stage 1b)" streichen und stattdessen: kein Kopf — der braucht Feststellungen aus dem Gate; keine Zuordnung zu Projekten, also ist die Chronik die des ganzen Logs; keine Warteschlange, der Arbeiter ist ein Kommando. Die vier Kommandos → „the seven commands `append`, `log`, `verify`, `show`, `project`, `chronicle` and `stats`".

- [ ] **Schritt 4: Vokabular messen**

Run: `make -C docs vale`
Erwartet entweder `0 errors`, oder Treffer auf Wörter wie `upsert`, `denormalization`, `catch-up`. **Je Wort einzeln** in `.vale-styles/config/vocabularies/Previously/accept.txt` anfügen und erneut messen (12 → 10 → 7 → 4 war das Muster am 2026-10-03). Kleingeschriebene Einträge dürfen danach keinen Satz beginnen — die Zahl im `.vale.ini`-Kommentar („Eleven of the fifteen entries are lowercase") **nachzählen** und anpassen: `awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt | wc -l` gegen `wc -l`.

- [ ] **Schritt 5: Alle sechs Tore, Commit**

Erwartet: `pytest` **232 passed** (unverändert), Vale **22 files**.

```bash
git add -A
git commit -F - <<'MSG'
docs: rebuild a projection, what a chronicle teaches about erasure, README

The how-to covers the three things an operator does: read the lag, bump a
version, clear a state row. The explanation page gets its last section —
that a tombstone which empties the payload leaves the units in the
chronicle, which no earlier document said, and what that demands of the
erasure event to come. The README says what stage 1b runs and what it
still does not: no header, because that needs assertions.

Vocabulary extended one word at a time, each measured against `make vale`;
the lowercase count in `.vale.ini` recounted, not carried forward.

Assisted-By: Claude <Modell> <noreply@anthropic.com>
MSG
```

---

