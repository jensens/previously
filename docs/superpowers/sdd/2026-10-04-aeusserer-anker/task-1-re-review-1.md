# Task 1 — Nachprüfung 1 der Korrekturrunde (11de3f6..c7d8b47)

### Finding verdicts

- **Mutationen aus Schritt 9: ADDRESSED.** `task-1-mutations.md` zeigt grüne Kontrolle davor (`36 passed`) und danach (`36 passed`) und vier Mutationen mit roten Tests und Schlusszeilen.
  M1 `if False:` statt `if anchored != row.hash:` — rot: Umschreiben, zwei Zeilen je Position, Stapeltest (3 failed). Deckt sich mit der Tabelle in `task-1-brief.md:480-485`.
  M2 `for anchor_id in ()` in `_closing_findings` statt Entfernen des Blocks — rot: gelöschte Spitze, leeres Log (2 failed). Das ist dieselbe Wirkung wie das Entfernen des `extend`-Blocks, die Abweichung von der Wortlaut-Tabelle ist unschädlich und im Record ausgewiesen.
  M3 `if exact:` zu `if False:` — rot: der Anhängen-Test (1 failed).
  M4 `len(fields) != 2` zu `if False:` — rot: zwei Fälle des parametrisierten Tests (2 failed).
  Die roten Tests sind die, die die Tabelle nennt. Ich habe selbst keine Mutation gefahren.
- **I1: ADDRESSED.** Alle drei Docstrings sagen jetzt, was der Test festhält und warum, und das verbliebene Label nennt den Plan:
  `tests/test_verify.py` (leeres Log: "every anchor is missing and the finding says the log ends at 0 (review focus 4 of the 2026-10-04 external-anchor plan)"), (Stapelgrenze: "checked as the pass comes by them … review focus 3 of the 2026-10-04 external-anchor plan"), `tests/test_anchor.py` (`²`: "pins that a digit outside ASCII is refused as a bad id … review focus 5 of the 2026-10-04 external-anchor plan").
  Die Begründungen stimmen mit dem Code überein (`examine` meldet am Ende `log ends at 0`; Anker werden beim Vorbeikommen in `pending.pop` geprüft).
- **I2: ADDRESSED.** `verify.py` `_check_event`-Docstring sagt `examine` ("`examine` would otherwise do two things at once: walk over batches and check an event"). Minor 1: Der Kommentar über dem Batch-Abruf sagt `examine` ("`examine` is the routine that runs over the whole history"). Beides trifft zu, die Schleife steht in `examine`.
- **Minor 2: ADDRESSED.** `hash-chain.md`: "Three manipulations pass the chain, and no change to the chain check can stop them." ist jetzt eine Aussage über die Kette allein und stimmt. "An external anchor closes two of the three up to the newest anchor" passt zur Tabelle derselben Seite (gelöschte Spitze unter dem neuesten Anker und Umschreiben: gesehen; Anhängen nur mit `exact`) und zur Lücke danach.
- **Minor 3: ADDRESSED.** Beide Tests tragen eine zweite Assertion mit `exact=True`, die gegen den konkreten Befund vergleicht: `Finding(3, "anchored event is missing (the log ends at 2)")` und `Finding(2, "hash does not match the anchor")`. Das ist der gleiche Befund wie bei `contains`, nicht nur "etwas zurückgegeben". Im ersten Fall ist `tip_id > newest` nicht erfüllt (Log endet bei 2, `newest` = 3), also kommt kein zusätzlicher Exact-Befund; im zweiten Fall sind Tip und Anker beide 2, ebenso. Die Gleichheit ist also wahr, nicht zufällig.
- **Minor 5: ADDRESSED.** Vor dem Löschen: `examine(storage).tip` ist nicht `None` und hat `id == 3`. Nach dem Löschen: `examine(storage).tip == anchor`. Die Kontrolle hält vor und nach der Löschung.

### New breakage in the fix diff

None.

Zur Frage des Controllers, `verify() -> []` im Docstring von `_count_finding` (`verify.py`, "measured `verify() -> []`, while `log --from=-5` displayed it"): Als Satz über eine damalige Messung ("measured", Vergangenheit, vor der Zählabstimmung) ist er wahr, und der Vorbehalt des Umsetzers hält. Heute wäre `verify()` für diese Konstruktion nicht mehr `[]`, weil gerade dieser Docstring die Abstimmung beschreibt, die den Befund erzeugt. Leser könnten `verify` als heutigen Aufruf lesen; das ist eine Schwäche der Formulierung, kein falscher Satz, und keine Blockade. Wer den Docstring ohnehin anfasst, könnte "before this reconciliation" ergänzen.

### Out-of-scope observations

1. `_count_finding`-Docstring, siehe oben: `verify() -> []` bleibt als historische Messung stehen und kann als Gegenwart gelesen werden. Niedrig.
2. Die Mutationsprotokoll-Zeile M2 weicht im Wortlaut von der Plantabelle ab (Schleife auf leeres Tupel statt Entfernen des Blocks). Wirkung gleich, Protokoll benennt die geänderte Zeile genau.

### Checks run

- `uv run pytest tests/test_verify.py tests/test_anchor.py -q -p no:randomly`: `36 passed in 6.95s`.
- `make -C docs vale`: `0 errors, 0 warnings and 0 suggestions in 22 files`.
- Diff-Datei gelesen, `verify.py`, `hash-chain.md` und Brief gegengelesen. Keine Mutation, keine Änderung am Baum.

### Verdict

Alle Findings sind behoben, keine neuen Mängel im Fix-Diff.
