# Task 5 — Re-Review Fixrunde 1 (Sonnet), Diff `49086f8..71dc078`

Wörtlich, wie vom Prüfer zurückgegeben; Controller-Notizen stehen im Hauptbuch.

---

Verdikte zu den Befunden (Diff `49086f8..71dc078`, Datei `review-49086f8..71dc078.diff`):

- **F1 (ProjectionGap feuert für keine Lücke)** — ADDRESSED. `src/previously/core/projection/worker.py:119-132`: `ids` wird jetzt gegen `expected = list(range(up_to_id+1, up_to_id+1+len(ids)))` verglichen, nicht mehr `if not events`. Neuer Test `tests/test_projection_worker.py:294-320` (`test_a_gap_in_the_log_raises_instead_of_being_skipped`) löscht Event 5 per SQL und erwartet `pytest.raises(ProjectionGap, match="above id 4")`. Nachvollzogen: nach Abbruch bei `fail_on_call=3`, `batch_size=2`, 10 Events à 2 Einheiten steht `up_to_id=4`, `p_chronicle` hat 8 Zeilen (Events 1-4 × 2 Einheiten, `split_plaintext("one\n\ntwo")` liefert exakt 2 Einheiten, geprüft in `src/previously/core/units.py:21-37`). Zweiter `catch_up`-Lauf liest ab `from_id=5`, findet wegen der Löschung `[6, 7]`, `expected=[5, 6]` ≠ `ids` → `ProjectionGap("… above id 4 …")`. Stimmt mit der Zusicherung `(4, 4, 8)` in Zeile 317.
- **F2 (`batch_size` unvalidiert)** — ADDRESSED. `worker.py:97-100`: `if batch_size < 1: raise ValueError(...)` ist die erste Anweisung der Funktion, vor jedem `store.begin()`. Test `test_batch_size_below_one_is_a_caller_error_not_a_gap` (`tests/test_projection_worker.py:323-331`) prüft 0 und -1.
- **Uncovered early return (Bedenken 4)** — ADDRESSED. Neuer Test `test_a_batch_without_any_source_leaves_the_stats_untouched` (`tests/test_projection_worker.py:334-351`) hängt nach einem ersten `catch_up` ein quellenloses Event in einem eigenen Batch an; trifft den `if not additions: return` in `src/previously/core/projection/source_stats.py:69-72` und prüft `p_source_stats` unverändert.
- **F3 (Schicht 2 fehlt positiv)** — ADDRESSED. `docs/explanation/projections.md`, neuer Absatz „Three layers, then, and none of them covers another": benennt die festgenagelte `first_seen`-Zusicherung ausdrücklich als Schicht, die die Arithmetik Ende-zu-Ende fängt.
- **F4 („fails, and alone" zu weit)** — ADDRESSED. `projections.md`, Codeblock: jetzt „fails, alone among the pure tests" plus zweite Zeile „`test_incremental_equals_rebuilt` fails as well, on its pinned `first_seen` value and not on the comparison".
- **F5 (Rebuild-Pfad nicht benannt)** — ADDRESSED. Ein Satz in „The assurance …": „Forcing the rebuild takes one of two paths, a version the table doesn't match or an emptied table with `up_to_id = 0` at an unchanged version, and the test takes the second one …".
- **F7 (quellenloses Event in `p_source_stats` nicht erwähnt)** — ADDRESSED. Ein Satz im Abschnitt „What the two tables are for": „From `p_source_stats` that same event is absent altogether, because there's no source it could be attributed to, and the chronicle is where it stays visible."
- **F8 („twenty lines" falsch)** — ADDRESSED. `tests/test_projection_worker.py` (Docstring `_FailingStore`): Zahl entfernt, jetzt „a wrapper of a few dozen lines and no mock" — keine falsche Zahl mehr, keine neue.
- **Lücken-Absatz („doesn't step over one either")** — ADDRESSED. `projections.md`, Abschnitt „Why there are no gaps to worry about" neu formuliert: Lücke unmöglich, Prüfung trotzdem („a check that can't fire is a comment rather than a check"), die Messung mit id 5/`up_to_id=10`, und dass die Prüfung jetzt Kennungen vergleicht.
- **`ProjectionGap`-Docstring** — ADDRESSED. `src/previously/core/errors.py:33-48`: beschreibt den Kennungsvergleich, dass die erste Fassung nur auf Leere prüfte, und warum das für keine Lücke feuern konnte („the tip is itself a row with `id >= up_to_id + 1` and `read` filters on `id >= from_id`" — gegen `storage/postgres.py:218-225` nachgeprüft: `.where(event.c.id >= from_id)`, stimmt wörtlich).

Drei vorgegebene Zusatzprüfungen:
1. `grep -c "^def test_" tests/test_projection_worker.py` → 12, wie erwartet. Mutation D (Versionsauslöser entfernt) trifft nur die zwei Versionstests (`test_a_version_bump_…`, `test_a_lower_code_version_rebuilds_too`); die drei neuen Tests (Lücke, `batch_size`, quellenloser Early-Return) sind von dieser Mutation unberührt → 12 − 2 = 10. „leaves the other ten green" ist arithmetisch korrekt.
2. `(state.up_to_id, highest, rows) == (4, 4, 8)` nachvollzogen (siehe F1 oben): `_FailingStore(fail_on_call=3)` lässt den dritten `insert_chronicle`-Aufruf (Batch mit Events 5/6 bei `batch_size=2`) scheitern, die Transaktion rollt komplett zurück; `_raw` liefert über `split_plaintext("one\n\ntwo")` zwei Einheiten je Event → 4 × 2 = 8. Stimmt.
3. `grep -rn "(hash-chain)=" docs/` → `docs/explanation/hash-chain.md:1` existiert. Das `{ref}`hash-chain`` im Arbeiter-Kommentar löst auf; `test_docs_references.py` kann grün sein. Ebenso geprüft: `(silent-losses)=` und `(module-boundaries)=` existieren.

Neue Probleme durch den Fix selbst:
- Minor, `src/previously/core/projection/worker.py:80-96`: Die Haupt-Docstring von `catch_up` zählt weiterhin nur die alten Garantien auf (Transaktionsgrenze, `batch_size`-Default, Lückenfreiheit) und erwähnt den neuen `ValueError`-Riegel nirgends in der Prosa — nur der Inline-Kommentar an der `raise`-Zeile trägt die Begründung. Kein funktionaler Fehler, aber eine Lücke in der Selbstdokumentation der Funktion, die der Fix eingeführt hat.
- Sonst keine Regressionen gefunden: Reihenfolge der neuen Tests zwischen `test_a_tombstoned_event_…` und dem Hypothesis-Block ist unauffällig; `EventRow`/`UnitRow`-Imports an den Dateikopf verschoben, keine doppelten Importe mehr; Gap-Check läuft korrekt auch bei kurzer Schluss-Charge (Chargenlänge < `batch_size` am Ende des Logs wird nicht fälschlich als Lücke erkannt, da `expected` aus `len(ids)` und nicht aus `batch_size` gebildet wird).

Out-of-Scope-Beobachtungen (nicht blockierend, für die Abschlussprüfung):
- Implementierer merkt selbst an (Bericht Abschnitt 8.2): der neue `ValueError` für `batch_size` hängt nicht unter `PreviouslyError`, damit ist `catch_up` die einzige Stelle in `core`, deren Fehler nicht dieser Hierarchie folgt. So angewiesen (F2 verlangt wörtlich `ValueError`), aber eine offene Entscheidung, falls Aufgabe 6 `--batch-size` an der CLI anbietet.
- `append.py:483` und `contract/store.py` bleiben laut Bericht unabgedeckt — außerhalb dieser Aufgabe, nicht geprüft.

Verdikt:
**Fix round: Alle Befunde adressiert, keine neue kritische/wichtige Regression.** Eine Minor-Beobachtung (Docstring von `catch_up` erwähnt den `batch_size`-Riegel nicht in der Prosa) blockiert nichts.
