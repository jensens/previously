# Review: Task 4 — How-to guides

Commit geprüft: `738dfec` (`docs: how-to guides for verification, restore
and migrations`), im Kontext des Diffs `06dd2f5..9dbcf42`. `c3d67e8` und
`9dbcf42` sind nicht Gegenstand dieser Prüfung (Jens' eigene Commits), wurden
aber mitgelesen, weil sie eine Behauptung aus Task 4 nachträglich betreffen
(siehe Frage 3). Alle Befehle liefen lesend aus
`.../worktrees/stufe-1a-log`; kein eigenes `/tmp`-Worktree nötig, da keine
Scheitern-Experimente verlangt waren — nur Nachbau des Builds und Code-Greps
gegen den vorliegenden Stand. `docs/_build/` wurde für einen erzwungenen
Neubau gelöscht und neu erzeugt (gitignored, `git status` danach weiterhin
„nothing to commit, working tree clean").

## Urteil 1: Spec-Treue

**ANGENOMMEN.** Alle vier Schritte des Briefs sind umgesetzt: die drei
Seiten mit dem geforderten Titel-Muster, dem „This guide shows you how
to…"-Einstieg und dem verlangten Inhalt, sowie der Toctree-Eintrag in
`docs/how-to/index.md`. Die beiden dokumentierten Abweichungen (keine
Restore-Befehle; Reference-Verweis für die Passphrase umgewidmet statt
erfunden) sind offen gelegt, begründet und bei eigener Nachprüfung sachlich
korrekt — keine verschwiegene Abweichung gefunden.

## Urteil 2: Qualität

**BEFUNDE, beide nicht blockierend.** Die drei Seiten halten den
How-to-Quadranten, der Build ist nach eigenem Neubau tatsächlich sauber, und
die Fallstrick-Warnung in `add-a-migration.md` war zum Zeitpunkt des Commits
`738dfec` korrekt. Zwei Befunde: ein inhaltlicher (die Warnung ist durch
Jens' eigenen, später hinzugekommenen Test jetzt teilweise veraltet) und ein
kosmetischer (Titel von `restore-from-a-backup.md` verspricht mehr, als die
Seite zu liefern beansprucht).

## Die drei Seiten einzeln

- `verify-the-chain.md` — **How-to, hält.** Schluss-Absatz benennt die
  Grenzen der Prüfung als Tatsachen („proves… / doesn't prove…", welche zwei
  Aktionen die Prüfung trotzdem bestehen lassen), ohne das *Warum* zu
  erklären; das bleibt der verlinkten Explanation vorbehalten. Grenzfall, der
  hält.
- `restore-from-a-backup.md` — **How-to, hält, am nächsten am Rand.** Ein
  Satz („This check matches every event's hash against its
  predecessor…") nennt den Mechanismus, der die Handlungsempfehlung
  rechtfertigt — exakt die vom Brief selbst verlangte Formulierung, auf
  einen Satz begrenzt und direkt an die Handlung („run verify, not just
  check Postgres") gekoppelt. Kippt nicht in Lehre, bleibt aber die
  verlockendste Stelle, wie im Auftrag richtig vorhergesagt.
- `add-a-migration.md` — **How-to, hält klar.** Keine Erklärung des *Warum*
  der `NULLS NOT DISTINCT`-Garantie, nur die mechanische Gefahr
  (Mismatch, stilles `autogenerate`-Drop) und was dagegen zu tun ist. Die
  sauberste der drei Seiten auf dieser Achse.

## Die fünf Prüffragen

1. **How-to oder Erklärung?** Alle drei halten den Quadranten; die
   Grenzfälle in `verify-the-chain.md` (Schluss) und
   `restore-from-a-backup.md` (Hash-Satz) sind bewusst auf einen Satz
   begrenzt und an die Handlung gekoppelt, kippen nicht in Lehre.
2. **Seite ohne Befehle.** `grep -rniE "backup|restore|passphrase"
   src/ tests/ migrations/` liefert null Treffer — die Behauptung des
   Umsetzers stimmt. Die auf den Verify-nach-Restore-Schritt verengte Seite
   ist die richtige Entscheidung: sie liefert eine echte, heute existierende
   und projektspezifische Handlung (sonst stünde sie nirgends), und sagt in
   Zeile 11–12 ausdrücklich, was sie nicht leistet — nur der H1-Titel selbst
   verspricht etwas umfassenderes, als der Text dann einlöst (siehe Befunde).
3. **Fallstrick in `add-a-migration.md`.** Beide Stellen bestätigt
   (`src/previously/storage/schema.py:95`,
   `migrations/versions/0001_log.py:79`, je
   `postgresql_nulls_not_distinct=True`); die zum Commit-Zeitpunkt
   bestehende Lücke im Namenstest (`test_the_declared_indexes_exist_in_the_migrated_database`,
   reine Namensmenge) ist korrekt beschrieben. Durch `c3d67e8` ist die
   Behauptung „nothing here catches the mismatch" jetzt aber nur noch für
   genau diesen einen Test wahr — ein neuer Test fängt die Abweichung längst
   (siehe Befund 1).
4. **Vorwärtsverweise und Toctree.** Erzwungener Neubau
   (`rm -rf docs/_build && make -C docs html`) lief mit 0 Warnungen durch
   alle 13 Quelldateien. Alle drei Seiten stehen im Toctree von
   `docs/how-to/index.md`. Die drei `{ref}`-Ziele (`cli-reference`,
   `configuration-reference`, `database-schema`) lösen im gebauten HTML
   korrekt zu `reference/cli.html#cli-reference`,
   `reference/configuration.html#configuration-reference` und
   `reference/database-schema.html#database-schema` auf. Die zwei
   absichtlich noch unverlinkten Prosa-Sätze
   (`verify-the-chain.md:29`, `restore-from-a-backup.md:29`) sind reine
   Prosa ohne `{ref}`-Syntax — kein kaputter Verweis, wie vorgemerkt.
5. **Stil und Fences.** Alle drei Seiten: genau eine H1, Sentence-Case,
   ein Satz je Zeile (eine mit Semikolon verbundene Doppelklausel in
   `add-a-migration.md:15` ist grammatisch ein Satz, kein Verstoß). Beide
   Admonitions (`{important}` in `restore-from-a-backup.md`, `{warning}` in
   `add-a-migration.md`) stehen in Doppelpunkt-Fences, nicht in
   Backtick-Fences — die einzige Backtick-Fence in den drei Dateien ist der
   `{toctree}`-Block in `index.md`, der keine Prosa trägt. `grep -niE
   "\b(we|we're|we'll|we've|our|let's)\b"` über alle drei Dateien: keine
   Treffer, konsistent mit `.vale.ini`, das `Microsoft.We = NO` exakt auf
   `[docs/tutorials/*.md]` begrenzt.

## Befunde

- `docs/how-to/add-a-migration.md:20` — **Mittel.** Der Satz „nothing here
  catches the mismatch: the existence check in `tests/test_schema.py` only
  confirms the index is present under that name, not that its
  `NULLS NOT DISTINCT` setting matches" war zum Commit `738dfec` korrekt
  und ist es für den dort benannten Test (`test_the_declared_indexes_exist_in_the_migrated_database`)
  immer noch. Seit `c3d67e8` fängt aber
  `test_the_declared_nulls_not_distinct_reaches_the_database` genau diese
  Abweichung ab (vergleicht `pg_index.indnullsnotdistinct` gegen die
  deklarierten Flags). Die Seite behauptet jetzt eine Lücke, die nicht
  mehr vollständig besteht. Kein Versäumnis des Umsetzers — der Test
  existierte beim Schreiben noch nicht — aber nachzuziehen, bevor die Seite
  als aktuell gilt; sinnvoller Ort dafür wäre Task 7 oder ein eigener
  Nachtrag.
- `docs/how-to/restore-from-a-backup.md:3` — **Gering.** Die H1 „How to
  restore from a backup" verspricht eine Restore-Anleitung; der eigentliche
  Restore-Schritt wird in Zeile 11–12 ausdrücklich ausgeklammert, die Seite
  liefert nur den Verify-danach-Teil. Die Einstiegszeile 5 stellt das sofort
  richtig, sodass kein Leser lange getäuscht wird, aber Titel und Inhalt
  passen nicht exakt zusammen; ein Titel wie „How to verify a restored
  backup" oder ein expliziter Scope-Hinweis direkt am Titel träfe den
  Inhalt genauer.

Pfad dieses Berichts:
`.superpowers/sdd/2026-10-03-dokumentation/task-4-review.md`
