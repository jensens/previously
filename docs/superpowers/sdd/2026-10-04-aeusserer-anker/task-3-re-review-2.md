# Task 3 — Re-Review 2 (Fix-Runde 2, `da79b41..7c936be`)

Gelesen: Diff-Datei `review-da79b41..7c936be.diff` (einmal), `docs/how-to/restore-from-a-backup.md` bei HEAD vollständig, Re-Review 1 (N1–N6, Beobachtung 1), Fix-2-Auftrag mit Ruling T3-f, Bericht `## Fix round 1` (Transkript) und `## Fix round 2`, `parse_anchors` (`src/previously/core/anchor.py:24-61`), `examine`/`_closing_findings` (`src/previously/core/verify.py:193-308`), `_cmd_verify`/`_cmd_anchor` (`src/previously/cli.py:247-290`), `verify-the-chain.md:25-60`, `hash-chain.md:363-366`.
Zeilennummern unten: `restore-from-a-backup.md` bei `7c936be`.

### Finding verdicts

**N2 (Important) — ADDRESSED.**
- Hauptweg wie geregelt: `:43` „check the restore against the anchor file as it stood at that point"; `:45` die Datei „from the place you keep it: the version of that time under version control, or the copy or message from that time" — Arten von Orten, kein Werkzeug; `:46` „The file doesn't date its own lines, so you can't read that version off the current file."
- Der fehlende Satz steht: `:59` „An `anchored event is missing` finding against that file is a loss: the restore stopped short of an anchor taken before the point it was meant to reach." Gegen den Code richtig: `_closing_findings` (`verify.py:298-303`) meldet jede Anker-`id`, deren Event der Durchlauf nie sah; die Datei des Restore-Punkts enthält nur Anker, die vor dem Punkt genommen wurden.
- Fallback als schwächer markiert, **vor** den Schritten: `:80-83`, vier Sätze vor Schritt 1 (`:85`); `:83` „It can't show that the restore reached the point you meant, because the cut comes from the result of the restore itself."
- Erster Fall: `:36` „Here, every `anchored event is missing` finding is a loss: the restore stopped short of an anchor, and it failed." `:37` „There's nothing to cut".
- Die Notiz zur heutigen Datei ist Notiz, kein Schritt (`:69-76`), „Expect these findings"/„Don't discard" sind weg.

**N1 (Important) — ADDRESSED.**
`:116-118` benennt den Fall („If no anchor is at or below the restore point, for example because you restored to a point before the first anchor, no anchor describes the restored log"), nennt `previously verify` ohne `--anchors` mit seiner Bedeutung (`:117` „checks only that the chain is consistent in itself", verstärkt in `:129-130`) und den Neubeginn (`:118`). Zugänge: Hauptweg `:48`, Fallback `:98` „If no anchor line has an `id` at or below the tip, don't cut". Kein Pfad endet bei `head -n 0`. Der Fall der leeren Datei steht zusätzlich unter Exit `2` (`:126` „holds no anchor line" — `anchor.py:59-60`).

**N3 (Minor) — ADDRESSED.** `README.md:89` Linktext „How to check how much of the chain a restore brought back" = Titel `:3`. Der Auftrags-`grep` liefert nichts (rc 1, selbst gemessen).

**N4 (Minor) — ADDRESSED.** `:97` „note its line number, the number `cat -n` prints in front of it"; `:101` „Pass the line number to `head -n`, not the `id`, even though both are `2` in this example".

**N5 (Minor) — ADDRESSED.** `:39` „it reports any event after the newest anchor as a finding, and that finding says nothing about loss." Gegen den Code: `--exact` erzeugt `the log continues past the newest anchor` (`verify.py:304-307`) — eine Aussage über die Spitze, keine über Verlust.

**N6 (Minor) — ADDRESSED.** `:26` „… to the latest state, or to any point after the newest anchor".

**Beobachtung 1 (übernommen) — ADDRESSED.** `verify-the-chain.md` nach der Routine: „If no event arrived since the last run, the routine appends the same line again. That's harmless, and it means that the count in `chain intact, <n> anchors hold` counts lines, not events." Gemessen in Runde 1, Schritt 5 (dritte Zeile `2 0cda…`); gegen `cli.py:271` (`count = len(anchors)`, die geparsten Ankerzeilen) richtig.

**Bedenken des Umsetzers — Hauptweg nicht eigens gemessen.** Die Äquivalenz trägt. Die Befehle des Hauptwegs und ihre Ausgaben stehen im Transkript von Runde 1:
- `previously verify --anchors anchors-restored.txt` → Schritt 5: `chain intact, 2 anchors hold`, exit 0;
- `… --exact` → Schritt 4: `chain intact, 2 anchors hold, the tip is the newest anchor`, exit 0;
- der Verlustfall gegen die Datei des gemeinten Punkts → Schritt 4, erster Befehl: `FINDING 3: anchored event is missing (the log ends at 2)`, exit 1.
`parse_anchors` liest Bytes, nicht Herkunft; eine Datei aus der Versionsverwaltung ist für `examine` dieselbe Eingabe wie eine geschnittene. Es gibt im Hauptweg keinen Befehl, keine Ausgabe und keinen Exit-Code, die das Transkript nicht zeigt. Exit `2` bei „holds no anchor line" ist nicht gemessen, sondern aus `anchor.py:59-60` und dem schon vorhandenen `cli.md` — eine Behauptung im Fließtext, kein gezeigter Befehl, und gegen den Code richtig.

**Abweichung — ein Name für beide Dateien.** Im Moment des Lesens verwechselt der Leser sie nicht: wer im Fallback ist, hat die Grenze `:80-83` vier Sätze vor dem ersten Befehl gelesen, und *After the check* (`:110-118`) behauptet für die Datei nichts, was nur die stärkere trüge. Zwei Schwächen bleiben, beide Minor (siehe M2): Schritt 4 des Fallbacks (`:107`) verweist auf „steps 2 and 3 above", deren Sätze für die stärkere Datei geschrieben sind (`:59` „the point it was meant to reach", `:61` „If the restore point coincides …"), ohne die Grenze dort zu wiederholen; und die Datei selbst trägt nachher nicht mehr, welche von beiden sie ist. Beim nächsten Restore ist das unerheblich, weil dann wieder deren eigene Geschichte zählt.

### The four readings

**1. Neuester Stand, Replay vor dem jüngsten Anker abgebrochen.** `:22` Fallwahl → `:24` Abschnitt passt (er hat nicht „on purpose" früher zurückgestellt) → `:29` `verify --anchors anchors.txt` → `FINDING n: anchored event is missing (the log ends at t)`, exit 1 (Transkript Schritt 4) → `:36` „every … finding is a loss … it failed", `:37` „nothing to cut; see *Read the result*" → `:122-123` „the restore failed … Discard the instance and restore again." Endet bei „the restore failed". Kein Satz auf seinem Weg öffnet einen Ausweg.

**2. Absichtlich drei Wochen zurück, Ankerdatei unter Versionsverwaltung.** `:43` passt → `:45` Version jener Zeit holen, `:47` als `anchors-restored.txt` → `:54` prüfen → exit 0 (`chain intact, n anchors hold`) bedeutet nach `:57-58` „up to the newest anchor in that file" und nichts darüber → optional `:64` `--exact`, nur wenn der Punkt mit dem letzten Anker zusammenfällt → `:112-114` Routine gegen die Datei, `anchors.txt` behalten. Blieb das Replay vor einem Anker jener Version stehen: `missing` → `:59` „is a loss" → `:122` „the restore failed". Beide Enden wie verlangt. Kein Schritt leitet den Maßstab aus Datenbank oder `verify`-Ausgabe ab.

**3. Dasselbe, Datei nur auf einem Host angehängt.** `:43` → `:45` kann die Version nicht holen → `:49` „If you can't get it, see *If the anchor file has no history*" → `:80-83` Grenze, bevor er etwas tippt: zeigt nur „nothing up to the last anchor it keeps was rewritten", **nicht**, dass der gemeinte Punkt erreicht wurde. Erst dann `:88`. Er weiß es vor dem ersten Befehl. (Ein Hostsicherungs-Abzug der Datei von damals wäre „the copy … from that time" nach `:45` und brächte ihn zurück auf den Hauptweg — richtig so.)

**4. Adversarial: Fall 1, will nicht neu zurückspielen.** Die Seite erlaubt es nicht. Der einzige Satz, der Befunde „erwartet" nennt, ist `:124` („The one check whose findings you expect is the first step of *If the anchor file has no history*"), und der Befehl jenes Schritts (`:88`) ist Zeichen für Zeichen der Befehl von Fall 1 (`:29`). Ein Leser mit Datei ohne Geschichte könnte daher seine Befunde dem Fallback zuschlagen. Dazu muss er aber `:36-37` übergehen, der für genau seinen Fall „every … is a loss … it failed. There's nothing to cut" sagt, und den Abschnitt `:43` betreten, der „on purpose to a point before the newest anchor" verlangt. Gegen ausdrücklichen Wortlaut der Seite, also nicht Important. Härtung als M2.

### New breakage in the fix diff

**M1 — Minor — `restore-from-a-backup.md:110-118`, *After the check*: Reihenfolge und Verweis für den Fall ohne Anker.**
Wer aus `:48` oder `:98` hierher kommt, liest zuerst `:112` „From now on, run the routine … against `anchors-restored.txt`" — eine Datei, die er nicht hat oder die leer ist (gegen sie gäbe die Routine bei jedem Lauf exit 2, `anchor.py:59-60`) — und erst danach `:116` seinen Fall. Und `:118` „start over with a first anchor in a new file, as {ref}`verify-the-chain` shows" führt auf `previously anchor > anchors.txt` (`verify-the-chain.md`), das genau die Datei überschreibt, die `:114` „Keep `anchors.txt` unchanged" schützen soll; „a new file" sagt es richtig, der gezeigte Befehl nennt den falschen Namen. Nebenbei mischt `:116` „at or below the restore point" Anker-`id` und Zeitpunkt. Fix: den No-Anchor-Absatz vor den Routine-Absatz stellen und den Dateinamen nennen („… in a new file, for example `anchors-new.txt`, not `anchors.txt`"); „no anchor taken before the restore point".

**M2 — Minor — `:80`, `:107`, `:124`: der Fallback sagt seine Eingangsbedingung nur über die Datei, nicht über den Restore.**
`:80` öffnet mit „If the anchor file was only ever appended to in one place", `:124` nennt seinen ersten Schritt als einzige Prüfung mit erwarteten Befunden, und dessen Befehl ist der von Fall 1 (siehe Lesart 4). Die Sperre gegen das Verschleppen liegt allein in `:36` und in der Überschrift-Bedingung `:43`. Fix in je einem Halbsatz: `:124` „… after a restore on purpose to an earlier point"; `:107` „… keeping in mind what the cut can't show".

**M3 — Minor — `:85`, Fallback Schritt 1 setzt ein `the log ends at` voraus.**
Gibt die Prüfung gegen die ganze Datei exit 0 (der Restore ging über den jüngsten Anker hinaus) oder nur `hash does not match the anchor`, gibt es keine Spitze abzulesen, und die Seite schweigt. Ungefährlich — exit 0 heißt, alles bis zum jüngsten Anker ist da (dann gilt Fall 1), ein Umschreibungsbefund führt in Schritt 4 gegen die geschnittene Datei wieder zu exit 1 —, aber der Leser hat keinen nächsten Zug. Fix: „If it exits `0`, the restore reached the newest anchor; treat it as the first case."

**M4 — Minor — `:45`, „as it stood at the restore point".**
Eine Version, die *nach* dem Punkt festgehalten wurde, enthält Anker von danach; die meldet `:59` als Verlust, und `:123` schickt den Betreiber in einen Restore-Kreislauf, der nie grün wird. Sichere Richtung (Fehlalarm, kein verschwiegener Verlust), daher Minor. Fix: „the last version from before that point".

### Out-of-scope observations

1. `cat -n anchors.txt` (`:94`) wurde in keinem Transkript ausgeführt; der Bericht sagt das offen. Die Zeile stand schon in `da79b41` (Kontextzeile im Diff), also außerhalb des Fix-Diffs. Seine Ausgabe wird nicht zitiert; die Aussage `:97`, die Zahl vor der Zeile sei die für `head -n`, passt zu `head` (beide zählen physische Zeilen, auch Kommentar- und Leerzeilen, die `parse_anchors` überspringt).
2. Der Bericht `## Fix round 2` zählt „plain `verify`" zu den Befehlen der Runde-1-Sitzung; im Runde-1-Transkript steht er nicht, wohl aber im ursprünglichen Tutorial-Transkript (`task-3-report.md`, Abschnitt *Raw transcript of the tutorial run*: `chain intact` / Hinweis auf stderr). Der Befehl ist also gemessen, nur nicht dort, wo der Bericht sagt.

### Checks run

- Form: Diff berührt nur `README.md`, `docs/how-to/restore-from-a-backup.md`, `docs/how-to/verify-the-chain.md` — kein Hunk unter `docs/superpowers/specs/`, `docs/reference/`, `docs/tutorials/`, `src/`, `tests/`; kein Hunk in `hash-chain.md`, dessen Absatz `:363-366` mit dem Leitfaden übereinstimmt (keine Schnitt-Aussage, keine Schritte). Ein Satz pro Zeile; weiterhin genau eine Admonition (`:7-9`); keine Hosting-Spezifik, kein Werkzeug für den Aufbewahrungsort; How-to-Form (Schritte, Links, Begründung nur so weit ein Schritt sie braucht — `:46`, `:75`, `:83` sind je ein Satz).
- `grep -rn "brought the chain back" README.md docs --include=*.md --exclude-dir=_build --exclude-dir=superpowers` → keine Ausgabe, rc 1.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly` → `6 passed in 0.96s`
- `uv run pytest --collect-only -q -p no:randomly | tail -1` → `265 tests collected in 0.17s` (Tutorial-Block unverändert, passt).
- Bericht zeigt alle sechs Gates mit Schlusszeile (`ruff check`, `ruff format --check`, `pyright`, `lint-imports`, `pytest --cov` 265 passed, `html`/`vale`/`linkcheck`) — als Behauptung bestätigt vorhanden; `ruff`, `pyright`, `lint-imports`, volle Suite und `linkcheck` habe ich laut Auftrag nicht selbst laufen lassen.
- Code gelesen: `anchor.py:24-61`, `verify.py:193-308`, `cli.py:247-290`; Commit-Trailer laut Bericht `Assisted-By:`.
- `git status --short` leer; nichts verändert außer dieser Datei.

### Verdict

Alle Befunde der Runde (N1–N6, Beobachtung 1) sind ADDRESSED; die zwei Important-Befunde sind in der Sache behoben — der Hauptweg nimmt seinen Maßstab von außen, ein `missing` gegen die Datei des Punkts ist ein Verlust, der Fallback sagt seine Grenze vor dem ersten Befehl, Fall 1 nennt jedes `missing` ein Scheitern. Keine neue Critical- oder Important-Bruchstelle. Vier neue Minor (M1–M4), zwei Beobachtungen außerhalb des Umfangs; keiner davon blockiert.
