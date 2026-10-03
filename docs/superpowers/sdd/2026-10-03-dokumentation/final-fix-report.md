# Letzte Fixrunde vor dem Merge — Bericht

Zweig `worktree-dokumentation`, Arbeitsverzeichnis
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`, 2026-10-03.

Auswahlprinzip wie im Auftrag: **eine falsch geschriebene Behauptung wird
behoben, neue Prüfmaschinerie wird nicht gebaut.** Zehn Punkte behoben, keine
Maschinerie ergänzt. Jede neue Zahl in diesem Commit ist in dieser Sitzung
gemessen; wo ich nichts messen konnte, steht die Herkunft statt einer Zahl.

## Je Punkt

**F1 — behoben.** `docs/explanation/hash-chain.md`, neuer Absatz direkt hinter
dem, der von „not trusting its own field of view" handelt. Formulierung aus
`src/previously/core/verify.py:119-121` (`_payload_finding` und
`_units_finding` getrennt aufgerufen, beide Ergebnisse gesammelt) und aus dem
Docstring von `tests/test_verify.py::test_w1_a_poisoned_payload_does_not_blind_the_unit_check`.
Die Seite sagt jetzt beides: der Verlust über Zeilen hinweg (W1) **und** der
innerhalb einer Zeile (B5), mit der Begründung, die der Test trägt — wer eine
Nutzlast unkanonisierbar machen kann, könnte sonst die Einheiten derselben
Zeile beliebig umschreiben, weil ein Befund den anderen verdeckt. Dazu der
Satz, dass die Trennung von einem Test gehalten wird und warum es ihn braucht:
beim Zusammenlegen der Blöcke blieb alles grün.

**F2 — behoben.** `silent-losses.md:6`: „Two" → „Three". Nachgezählt:
`canonicalization.md:71`, `concurrency.md:149`, `hash-chain.md:197`;
`index.md:13` ist der Toctree.

**F3 — behoben, mit Widerspruch.** Zahl auf **sechs** berichtigt und `A001`
aufgenommen. Die Begründung im Auftrag ist aber gemessen falsch: `docs/conf.py`
wird von `uv run ruff check .` **nicht** erfasst. Messung mit entfernter
Suppression:

```
uv run ruff check .                         All checks passed!   (36 Dateien, keine unter docs/)
uv run ruff check docs/conf.py              A001 copyright is shadowing a Python builtin
uv run ruff check --force-exclude docs/...  warning: No Python files found
```

Ursache: `[tool.ruff] extend-exclude = ["docs"]`, und der pre-commit-Hook ruft
ruff mit `--force-exclude` — das ist in `.pre-commit-config.yaml:16-25` schon
gemessen dokumentiert. Die Suppression ist also **kein tragender Teil eines
Tors**, sondern eine Notiz für den, der die Datei einzeln lintet. Genau das
steht jetzt in `CLAUDE.md`, mit der Messung daneben.

**F4 — behoben.** `docs/reference/cli.md`: `show` druckt **drei** Zeilen,
`id=` und `kind=` auf einer (`src/previously/cli.py:138`). Die drei Folgesätze
der Seite (Nutzlast/Evidenz, Einheiten, `No event`) am Code nachgeprüft und
korrekt; die Exit-Code-Tabelle ebenfalls (`main` gibt 2 im `except`, `_cmd_show`
1 ohne Treffer, `_cmd_verify` 1 bei Befunden).

**F5 — behoben, Befund des Prüfers reproduziert.** Mutation byteweise gesichert
(`sha256` vor und nach identisch, `git status` sauber). Eigene Messung unten.
Das Beispiel der Seite ist jetzt ein Attributzugriff
(`_ = PostgresStorage.__name__`), der alle fünf anderen Tore übersteht; der
`isinstance`-Fall steht als zweiter Block daneben, weil er zeigt, dass Tor 3
das alte Beispiel abfängt. Der Satz „the only thing left" heißt jetzt „the only
gate left" und stimmt für das neue Beispiel.

**F6 — behoben (nur die Behauptung).** Docstring von
`test_the_reference_quotes_what_the_code_actually_prints`. Selbst gemessen,
beide Richtungen:

- sechste Einschränkung in `_check`, Seite unangetastet → `5 passed` (grün);
- dieselbe Einschränkung nur in der Tabelle → `1 failed, 4 passed`.

Der Docstring sagt jetzt, dass das Tor feuert, wenn die Einschränkung die
**Seite** erreicht, und schweigt, wenn sie nur den Code erreicht. Die Ableitung
der fünf Nutzlasten aus dem Code ist als geparkt benannt, nicht gebaut.

**F7 — behoben (nur die Behauptung).** `CLAUDE.md`: das Tor hält die abgeleitete
Zahl gegen jedes `N passed` im Tutorial, und sonst nichts. Selbst gemessen:
`collected 194 items` → `collected 999 items` plus eine verfälschte
Punktzeile → `1 passed`, grün.

**F9 — behoben.** `record-your-first-event.md:6`. Die falsche Hälfte
(„which is why the paths below say so") ist weg; stattdessen steht, was prüfbar
ist: kein Kommando zeigt das Verzeichnis, und der einzige absolute Pfad in der
Ausgabe — das `rootdir:` — nennt den Arbeitsbaum. Die `rootdir:`-Zeile selbst
ist unangetastet.

**F10 — behoben, alle drei.**
(a) `CLAUDE.md`: die Tabelle führt von jedem der zwanzig Paragraphen zur Seite,
die die Begründung übernommen hat — „oder, für fünf von ihnen, zur Feststellung,
dass es keine tat". Nachgezählt: 21 Zeilen, 20 Paragraphen (§5 zweimal), fünf
mit „nowhere; frozen design record".
(b) `DEPENDENCIES.md:20`: §2 und §10.1 stehen in beiden Mengen, §8.6, §10.6
und §10.7 nicht. Die übrigen Zahlen des Absatzes nachgeprüft und richtig: 13
Paragraphenverweise auf der Seite (§10.6 achtmal in der Tabelle, §10.7 in
Zeile 3 und 69, §8.6 in Zeile 72, §10.1 in Zeile 25, §2 in Zeile 34).
(c) `CLAUDE.md`: der Prüfer liest `*.py` unter `src/`, `tests/`, `migrations/`
und kennt nur `{ref}`. Die reST-Form `:ref:` kommt im Baum heute nirgends vor
(gemessen) — ergänzt wurde sie nicht, nur die Grenze benannt.

**H-a — behoben.** `backup-encryption.md`: ein Satz vor dem ```text```-Block
nennt die Herkunft (Architektur §10.5, eingefrorener Bericht, Stand
2026-10-03) und sagt ausdrücklich, dass weder die Tabelle noch die
pgBackRest-Zahlen auf dieser Seite erhoben wurden. Die Zahlen selbst sind
unangetastet.

**H-b — behoben, durch Ersetzen der Zahl.** 83 ist mit keinem einfachen
Verfahren reproduzierbar, auch nicht am Commit, der die Zahl eingeführt hat:

| Messung | Treffer |
|---|---|
| `\b(W\|G\|B\|K\|N)-?[0-9]+\b`, `*.py` unter src/tests/migrations, heute | 98 |
| dasselbe am Commit `cc8229b` (dort steht die Zahl erstmals) | 97 |
| ganzer verfolgter Baum, heute | 168 |
| ganzer verfolgter Baum, bei `cc8229b` | 163 |
| nur Zeilen mit Stichwort (finding/ruling/correction/review) | 72 |

Keine Variante liegt bei 83, und Zeilenumbrüche in Kommentaren machen ein
stichwortbasiertes Verfahren unbrauchbar. Darum steht jetzt das Zählverfahren
in `CLAUDE.md` — mit dem Hinweis, dass Groß-/Kleinschreibung der tragende Teil
des Musters ist (sonst fangen Testnamen wie `test_k1_f1_…` mit) — und der Satz,
dass die Aussage über den Bindestrich ohne Zensus trägt. Ein Falschtreffer ist
benannt: `N-0112` in `docs/superpowers/specs/2026-10-01-previously-design.md:251`
ist eine Notiz-Kennung, kein Prüfbefund.

## Eigene Messung zu F5

Mutation: `from previously.storage.postgres import PostgresStorage` aus dem
`if TYPE_CHECKING:`-Block in `src/previously/core/verify.py` nach oben geholt,
plus eine Laufzeitnutzung als erste Zeile von `verify`.

Mit `_ = PostgresStorage.__name__` (Zeile 179):

```
uv run ruff check .           All checks passed!
uv run ruff format --check .  39 files already formatted
uv run pyright                0 errors, 0 warnings, 0 informations
uv run lint-imports           Contracts: 4 kept, 0 broken. (2 ignored imports)
uv run pytest -q              1 failed, 193 passed in 16.63s
                              test_the_exempted_core_modules_load_no_sql_at_runtime
                              -> loaded sqlalchemy at runtime
make -C docs html             build succeeded.
make -C docs vale             0 errors, 0 warnings and 0 suggestions in 20 files.
make -C docs linkcheck        build succeeded.
```

Mit `if not isinstance(storage, PostgresStorage):` an derselben Stelle:

```
uv run lint-imports   Contracts: 4 kept, 0 broken.
uv run ruff check .   All checks passed!
uv run pyright        1 error
  src/previously/core/verify.py:179:12 - error: Unnecessary isinstance call;
  "PostgresStorage" is always an instance of "PostgresStorage"
  (reportUnnecessaryIsInstance)
```

Zeile und Spalte stimmen mit dem Prüfbericht überein. Wiederherstellung
byteweise: `sha256` von `verify.py` vorher und nachher
`b63a02921565b2f51f6777cd7f0e60c96ad9263cbd4f2daae0bb99bd45d68b88`,
`git status` sauber.

## Tore nach der Runde

Alle sechs grün, 194 Tests wie vorher. Ausgaben im Rückbericht.

## Weitere Funde

1. **`ruff check .` erfasst `docs/conf.py` nicht** (siehe F3). Das war die
   Begründung für F3 im Auftrag und ist gemessen falsch.
2. **`backup-encryption.md:12`** („Checked on 2026-10-03 against the
   documentation of Hetzner Object Storage") hat dieselbe Herkunft wie H-a,
   ist aber keine Falschaussage: Datum und Quelle stimmen, nur der Prüfer war
   ein anderer. Nicht angefasst, weil außerhalb des Auftrags und nicht falsch.
3. **Ein dritter Label-Raum** im Baum: `ruling T7-a`, `T8-c`, `T9-c`, `T2-e`
   (Task-Entscheidungen). `CLAUDE.md` beschreibt nur die zwei Befundräume.
   Keine Falschaussage, aber wer `T8-c` sucht, findet die Erklärung nirgends.
4. Nachgeprüft und **richtig**: die dreizehn Paragraphenverweise in
   `DEPENDENCIES.md`, die vierzehn verbliebenen `§`-Zitate im Code
   (`design-records.md:10`), die fünf Abschnitte in `silent-losses.md`, die
   fünf Zeilen der Payload-Tabelle, die vier Felder der `log`-Zeile und die
   Exit-Code-Tabelle in `cli.md`.
