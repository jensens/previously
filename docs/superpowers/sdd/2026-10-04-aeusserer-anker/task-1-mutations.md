# Task 1 — die vier Mutationen aus Schritt 9, gemessen

Gemessen vom Controller am 2026-10-04 an Commit `11de3f6`, **mit
ausdrücklicher Erlaubnis des Betreuers** („Im Baum messen"), nachdem das
Berechtigungssystem dem Umsetzer die erste Mutation verweigert hatte. Je eine
Zeile geändert, die zwei deckenden Testdateien gefahren, aus einer
Sicherungskopie zurückgenommen. Kommando je Lauf:

```
uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly -rf
```

| Mutation | geänderte Zeile | rot | Schlusszeile |
|---|---|---|---|
| Kontrolle davor | — | — | `36 passed in 6.92s` |
| M1: Hash-Vergleich feuert nie | `verify.py`: `if anchored != row.hash:` → `if False:` | `test_a_rewritten_chain_is_consistent_in_itself_and_fails_the_anchor`, `test_two_lines_for_one_position_are_both_checked`, `test_anchors_are_checked_across_a_batch_boundary` | `3 failed, 33 passed in 6.88s` |
| M2: kein Befund für einen Anker, der nie vorbeikam | `verify.py`, `_closing_findings`: `for anchor_id in sorted(pending)` → `for anchor_id in ()` | `test_a_deleted_tip_passes_without_an_anchor_and_fires_with_one`, `test_an_empty_log_has_no_tip_and_misses_every_anchor` | `2 failed, 34 passed in 6.91s` |
| M3: `exact` ist wirkungslos | `verify.py`, `_closing_findings`: `if exact:` → `if False:` | `test_an_appended_event_passes_contains_and_fails_exact` | `1 failed, 35 passed in 6.86s` |
| M4: der Parser prüft die Feldzahl nicht | `anchor.py`: `if len(fields) != 2:` → `if False:` | zwei Fälle von `test_a_broken_line_is_refused_with_its_line_number` (drittes Feld; nur ein Feld) | `2 failed, 34 passed in 6.85s` |
| Kontrolle danach | — | — | `36 passed in 6.85s` |

Jede Zeile deckt sich mit der Tabelle des Plans (Aufgabe 1 Schritt 9). Der
Baum war nach dem Lauf sauber (`git status --short` leer). Das Skript liegt
als `task1-mutations.sh` im Scratchpad der Sitzung.
