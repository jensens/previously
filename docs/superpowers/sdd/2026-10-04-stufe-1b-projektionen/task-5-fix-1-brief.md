# Task 5 — Fixrunde 1: Auftrag an den Umsetzer (Opus), nach der Prüfung von `49086f8`

Wörtlich, wie an den Umsetzer geschickt. Ein Satz darin ist falsch und wurde vom Umsetzer widerlegt: „der Lückentest war grün gegen den alten Code" — der Test erwartet `ProjectionGap` und ist gegen den alten Code rot mit `DID NOT RAISE`; grün blieb der alte **Arbeiter**, der 6..10 projizierte. Siehe Hauptbuch und Plan-Commit `71dc078`.

---

Fixrunde 1 zu Aufgabe 5. Die Prüfung bestätigt fast alles — drei Mutationen selbst gefahren und Zahl für Zahl mit deiner Seite deckungsgleich, Tutorial mit Seed reproduziert, die Dreischichten-Darstellung ausdrücklich als **ehrlich** beurteilt. Ein Befund ist erheblich, und er ist ein Fehler **des Briefs**, den du treu umgesetzt hast. Spec §5.2 trägt inzwischen einen zweiten datierten Korrekturblock aus deinem Bedenken 1 (`b465cdc`); der Plan trägt die Guards unten (`fd46f94`).

**F1 (Erheblich) — `ProjectionGap` kann für keine Lücke feuern.** `if not events` wird nur erreicht, wenn `tip.id > up_to_id`, und die Spitze ist selbst eine Zeile mit `id >= up_to_id + 1`; `read` filtert `id >= from_id`. Das Ergebnis ist also nie leer, solange `limit >= 1` — die Bedingung ist äquivalent zu `batch_size == 0`. Gemessen vom Prüfer im Container: zehn Events, Abbruch bei `up_to_id 4`, dann `DELETE … WHERE id = 5` → `catch_up` liefert `events=5 up_to_id=10`, projiziert `[1,2,3,4,6,7,8,9,10]`, **kein** `ProjectionGap`. Drei Behauptungen im Baum sagen das Gegenteil (Docstring `core/errors.py`, `projections.md:74-76`, deine Commit-Botschaft). `worker.py:116` ist unabgedeckt — der `raise` ließe sich löschen, ohne dass einer von 220 Tests rot wird.

**Zu tun in `catch_up`** — ersetze den Block von `events = tuple(log.read(…))` bis zum Ende des `raise` **wörtlich** durch den Kontiguitätsvergleich aus dem Plan (Aufgabe 5 Schritt 4, Stand `fd46f94`): `ids`, `expected = list(range(state.up_to_id + 1, state.up_to_id + 1 + len(ids)))`, `if ids != expected: raise ProjectionGap(...)` mit der Meldung `expected events {expected[:1]}.. above id {state.up_to_id}, read {ids[:3]}…; the tip is {tip.id}`, und dem Kommentar, der die Messung vom 2026-10-04 nennt.

**F2 (Mittel) — `batch_size` ungeprüft.** Gemessen: `0` → irreführender `ProjectionGap`; `-1` → rohe `DataError` (`LIMIT must not be negative`) unübersetzt. Als **erste** Zeilen in `catch_up`, vor `rebuilt_from`: `if batch_size < 1: raise ValueError(f"batch_size must be at least 1, got {batch_size}")`. `ValueError`, nicht `PreviouslyError`: die Kommandozeile reicht `batch_size` nie durch, es ist ein Programmierfehler, kein Nutzerfehler.

**Drei Tests dazu** (Wortlaut im Plan, Aufgabe 5 Schritt 2, Stand `4f01d8d`): `test_a_gap_in_the_log_raises_instead_of_being_skipped`, `test_batch_size_below_one_is_a_caller_error_not_a_gap`, `test_a_batch_without_any_source_leaves_the_stats_untouched`. `EventRow`/`UnitRow` an den Dateikopf, `ProjectionGap` importieren. Fahr den Lückentest **einmal gegen den alten Code** und schreib in den Bericht, was du misst.

**Docstring von `ProjectionGap`** in `core/errors.py`: ergänze, dass die Prüfung die gelesenen Kennungen mit dem erwarteten Lauf `up_to_id + 1 …` vergleicht — und dass die erste Fassung nur auf Leere prüfte und gemessen nie feuern konnte.

**Die Seite `projections.md`**, fünf Stellen: der dritte Absatz von „Why there are no gaps to worry about" ist gemessen falsch und wird neu geschrieben; **F3** Schicht 2 positiv benennen (festgenagelte `first_seen`-Zusicherung fängt die Arithmetik Ende-zu-Ende); **F4** „fails, and alone" → „alone among the pure tests" plus die zweite Hälfte; **F5** ein Halbsatz zum Neubau-Weg „leeren plus `up_to_id = 0` bei unveränderter Version", den `_force_rebuild` nimmt; **F7** ein Halbsatz, dass ein quellenloses Event in `p_source_stats` fehlt.

**F8:** „this wrapper is twenty lines" (Docstring `_FailingStore`) — gemessen 36 Zeilen, 27 ohne Leerzeilen. Zahl streichen: „a wrapper of a few dozen lines and no mock".

**F6 bleibt**: der `{ref}projections` im `Outcome`-Docstring zeigt auf die Kommandozeile, die Aufgabe 6 beschreibt. Vorgriff um eine Aufgabe.

**Danach:** zwölf Tests grün in `test_projection_worker.py`, Testzahl **223**, Tutorial neu abtippen ohne `rootdir:`, alle sechs Tore einzeln mit Ausgabe. Commit „fix: the worker checks contiguity, not emptiness" mit Trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`. Fixbericht an `task-5-report.md` anhängen; zurück nur Commit-Hash, je Punkt eine Zeile, die Messung gegen den alten Code, die sechs Torausgaben, und jede Stelle, an der du widersprichst.
