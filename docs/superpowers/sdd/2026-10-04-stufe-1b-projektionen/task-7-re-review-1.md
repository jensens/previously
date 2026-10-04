# Task 7 — Re-Review Fixrunde 1 (Sonnet), Diff `773cf4a..af5f5de`

Wörtlich, wie vom Prüfer zurückgegeben.

---

### Finding Verdicts

- **I1 — How-to-Karte auf `docs/index.md` fehlt die vierte Seite** — ADDRESSED. `docs/index.md:24`: „Solve a specific problem: restore a backup, add a migration, rebuild a projection, check the chain in operation." Vierter Eintrag vor dem letzten eingefügt, Reihenfolge der anderen drei unverändert.

- **I2 — „Both stand at `1`." ist eine ungehaltene Zahl** — ADDRESSED. `docs/how-to/rebuild-a-projection.md:35`: „Read the current value there." Keine Zahl mehr über Code, den die Seite im nächsten Codeblock selbst ändern lässt. Die beiden Fundstellen (`:34`) bleiben stehen. Gegengeprüft: `chronicle.py:69` und `source_stats.py:67` stehen weiterhin bei `version: int = 1` — stimmig, aber jetzt irrelevant für die Seite.

- **I3 — drei `text`-Blöcke als erfundene Läufe** — ADDRESSED. Alle drei `text`-Blöcke (`:17-19`, `:48-50`, `:70-72` der alten Fassung) sind entfernt; die Seite trägt jetzt nur noch vier Blöcke (`shell`, `shell`, `python`, `shell`), keiner davon Programmausgabe. Prosaform wie `verify-the-chain.md`:
  - `:15` nennt Rückstandszahl und Empfehlung — deckt sich mit `_lag_line` (`cli.py:112-124`).
  - `:28` „prints one line per projection" — deckt sich mit der Schleife über `PROJECTIONS` in `_cmd_project` (`cli.py:232-234`).
  - `:43-44` „begins with `rebuilt:`, names the version it moved from and to, and ends with the number of events projected and the new `up_to_id`" / „reports `up to date`" — deckt sich wörtlich mit `_describe` (`cli.py:93-109`: `rebuilt: version {from} -> {to}, {tail}` bzw. `up to date, up_to_id {id}`).
  - `:62-63` „begins with `built:` instead of `rebuilt:`" / „again reports `up to date`" — deckt sich mit `_describe` (`rebuilt_from == 0` → `built:`).
  Der Nebenbefund (nur erste von zwei Zeilen gezeigt) ist durch die Prosaform an beiden Stellen geschlossen, `:28` sagt „one line per projection" explizit. Keine Überbehauptung gegen den Code gefunden.

- **I4 — Tutorial-Zugangsdaten im `psql`-Befehl** — ADDRESSED. `:54`: `psql postgresql://USER:PASSWORD@HOST:PORT/DATABASE \`. `:60`: „Take the host, port, database and credentials from the value you have set; see {ref}`configuration-reference` for its form." — der Verweis ersetzt die Zugangsdaten, wie verlangt. Der gemessene `libpq`-Satz (`:59`) ist unverändert stehen geblieben.

- **Minor 1 — zweideutiges `chronicle`** — ADDRESSED. `:71`: „To force the statistics the same way, use `'source-stats'` in place of `'chronicle'` in the `DELETE`." Beide Werte als SQL-Literal in Anführungszeichen und Code-Span, Verwechslung mit dem Kommando ausgeschlossen.

- **Minor 2 — §4.6-Zitat könnte schärfer sein** — ADDRESSED. `docs/explanation/projections.md:203`: „What it does say is the sharper evidence—an erasure takes the proof and not the derived facts, and what disappears is the wording—because the wording is what `unit.content` holds, and a chronicle per unit goes on printing it." Gegen `docs/superpowers/specs/2026-10-01-architektur.md:449-459` gelesen: „Sie nimmt den Beleg, nicht die abgeleiteten Fakten" / „was verschwindet, ist der Wortlaut" — Übersetzung trifft genau. „overlooks" bleibt wie erlaubt stehen.

### New Breakage in the Fix Diff

None. Geprüft: beide {ref}-Ziele (`configuration-reference`, `cli-reference`) existieren und lösen auf (`make -C docs html` selbst gefahren: „build succeeded."); Vale selbst gefahren: „0 errors, 0 warnings and 0 suggestions in 22 files." — deckt sich mit dem Bericht. Ein-Satz-pro-Zeile ist in allen neuen/geänderten Zeilen gehalten (Kolons und Semikolons verbinden wie im übrigen Dokumentbestand, keine neue Abweichung). Vier verbleibende Codeblöcke auf der How-to-Seite sind ausschließlich Befehle oder eine Codeänderung, keiner ist Programmausgabe — Check 2 bestanden. `git status --short` im Worktree ist leer, HEAD steht auf `af5f5de`, Diff-Umfang exakt die drei erlaubten Dateien (`docs/how-to/rebuild-a-projection.md`, `docs/index.md`, `docs/explanation/projections.md`), nichts Fremdes. Commit-Nachricht ist Englisch, trägt `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`, kein `Co-Authored-By`.

### Out-of-Scope Observations

- Die selbst eingeräumte Abweichung des Umsetzers (`{ref}`cli-reference`` nur zweimal statt nach jeder Prosaaussage) ist keine Lücke: `docs/reference/cli.md:74-86` (Outcome-Tabelle) und `:110-119` (Lag-Zeilen-Format) decken alle in der How-to genannten Ausgabeformen vollständig ab — die Bündelung verhindert nur eine dreifache Wiederholung desselben Links.
- Nicht unter Prüfung, aber vom Implementierer korrekt nicht angefasst: `README.md:58-70` („three frozen design records") bleibt für Task 8; `projections.md`-Länge bleibt Sache der Endprüfung.

### Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage.
