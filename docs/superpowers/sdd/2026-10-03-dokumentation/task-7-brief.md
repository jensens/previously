## Task 7: Die Specs einfrieren, die 72 Verweise umstellen — und ein Tor, das sie hält

**Files:**
- Create: `tests/test_docs_references.py`, `docs/explanation/design-records.md`
- Modify: 21 Dateien unter `src/`, `tests/`, `migrations/` (Liste unten), dazu `docs/superpowers/specs/2026-10-01-architektur.md`, `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`, `docs/superpowers/specs/2026-10-01-previously-design.md`

**Interfaces:**
- Consumes: alle Label aus den Aufgaben 2, 5 und 6.

**Gemessener Ist-Stand (2026-10-03):** 72 Vorkommen von `§x.y` in `src/` (39), `tests/` und `migrations/`, über 21 Dateien, auf **20** verschiedene Paragraphen. Häufigste: §3.2 (12×), §3.1 (9×), §5.1 (8×), §5 (5×), §4.2 (5×), §3.4 (5×).

### Das Einfrieren ist ein Vorgang, kein Ereignis

Hier hatte ich den Plan zunächst falsch gefasst, und die Korrektur kommt vom
Auftraggeber: **Deutsch ist seine Autorensprache für Absicht**, nicht ein
Altbestand, den man abarbeitet. „Mit Deutsch kann ich mich besser ausdrücken,
was ich will."

Daraus folgt: jede künftige Stufe wird **wieder** mit einem deutschen Spec
beginnen, und der friert ein, sobald seine Explanation-Seiten stehen. Das
Einfrieren ist also ein wiederkehrender Schritt im Ablauf und nichts, was
dieser Plan ein einziges Mal erledigt. Schreib es als Ablauf hin, nicht als
Zustand — sonst liest die nächste Stufe die eingefrorenen Specs als Verbot,
einen neuen zu schreiben.

- [ ] **Schritt 1: Die drei Specs einfrieren**

Oben in jedes Dokument, auf Deutsch (die Specs sind und bleiben deutsch):

```markdown
> **Eingefrorener Entwurfsbericht, Stand 2026-10-03.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in `docs/explanation/`; weicht
> dieses Dokument davon ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen.
```

Dieser Schritt kommt **zuerst**, und zwar aus einem Grund, der die
Aufgabenteilung erklärt: die Verweise, die du unten umstellst, bezeichnen die
Specs als „frozen design record". Frierst du erst danach ein, behauptet jeder
dieser Verweise beim Schreiben etwas Unwahres — genau der Fehler, den diese
Umstellung beheben soll (Ruling P2 der Vorab-Durchsicht).

- [ ] **Schritt 2: Die Verweise aus der README mitnehmen**

Nicht nur der Code verweist auf die Specs. `README.md` sagt „§11 of the stage
1a specification states which forgeries are covered and which are not", und
die Dokumententabelle darunter verlinkt alle drei Specs mit einer Zeile
Inhaltsangabe.

Nach dem Einfrieren zeigen diese Verweise auf eingefrorene Berichte. Für die
Tabelle ist das richtig — sie beschreibt Provenienz. Für den §11-Satz nicht:
er beantwortet eine **heutige** Frage („welche Fälschungen sind gedeckt?") und
gehört damit auf `{ref}`hash-chain`` bzw. die Explanation-Seite, die die
Grenzen trägt. Zieh ihn dorthin und kennzeichne die Tabellenzeilen als
eingefrorene Berichte.

- [ ] **Schritt 3: Die zwei Prosa-Verweise aus den How-tos in `{ref}` umwandeln**

Aufgabe 4 durfte noch keine `{ref}` auf Explanation-Label setzen — die gab es
nicht, und ein Vorwärtsverweis bricht das Tor. Sie hat die Sätze darum als
reine Prosa formuliert, **ohne** Marker, weil ein sichtbares TODO Vale
beanstandet hätte. Damit du sie nicht suchen musst, hier ihre Fundstellen:

| Datei | Zeile | Satz |
|---|---|---|
| `docs/how-to/verify-the-chain.md` | 29 | „For what the chain guarantees and where that stops, see the explanation of the hash chain." |
| `docs/how-to/restore-from-a-backup.md` | 29 | „For why losing the passphrase means losing the backups for good, see the explanation of backup encryption." |

Wandle beide in `{ref}`-Verweise auf die jetzt existierenden Label um
(`hash-chain` und `backup-encryption`). Prüfe danach mit `grep`, ob in den
Quadranten weitere Sätze dieser Form stehen — die Zeilennummern oben
verschieben sich, sobald jemand die Seiten anfasst, der Wortlaut nicht.

- [ ] **Schritt 4: Die Abbildungstabelle festlegen**

Nicht 72 Entscheidungen, sondern 20 — je Paragraph ein Ziel. Schreib die Tabelle nach `docs/explanation/design-records.md`, zusammen mit dem Hinweis, dass die Specs eingefroren sind und wofür sie noch gut sind (Provenienz: „so wurde es damals entschieden").

Beispiele: §3.1 → `{ref}`hash-domain``, §3.2 → `{ref}`canonicalization``, §3.4 → `{ref}`hash-chain``, §4.2 → `{ref}`conflict-classes``, §2 und §8 → `{ref}`module-boundaries``, §4.6 und §10.5 → `{ref}`backup-encryption``.

Für Paragraphen, deren Begründung **nicht** in die Doku wandert, bleibt der Verweis auf den eingefrorenen Bericht — aber ausdrücklich als solcher gekennzeichnet, etwa „architecture §10.2 (frozen design record)". Ein Verweis, der nicht sagt, dass sein Ziel eingefroren ist, lügt über seine Aktualität.

### Drei Klassen von Verweis, nicht eine — nachgemessen am 2026-10-03

Der Plan hat diese Aufgabe zunaechst als *eine* Umstellung gefasst: 72
Kommentarverweise auf Doku-Label. Nachgemessen sind es drei Klassen, und die
dritte haette der Test aus Schritt 5 **durchgewinkt**.

**Klasse 1 — lebende Begruendung in Kommentar oder Docstring.** Sie erklaert,
warum der Code heute so ist. Sie muss auf die Doku zeigen, denn sie wird mit
dem Code gepflegt. Das sind die 70 Faelle, die die Tabelle aus Schritt 4
abbildet.

**Klasse 2 — datierte Entscheidung.** Sie zitiert, *wie damals entschieden
wurde*. Fuer sie ist der eingefrorene Bericht die **richtige** Quelle: das
Einfrieren ist gerade das, was ihn zitierfaehig macht. Hierher gehoeren die
Verweise auf Pruefbefunde und Rulings (die der Plan schon ausnimmt) und das
`DEPENDENCIES.md`, dessen 13 Verweise je eine Zeile eines datierten
Entscheidungsregisters begruenden. Sie bleiben — aber mit `(frozen design
record)` gekennzeichnet, denn die Regel aus Schritt 4 gilt fuer jede
englischsprachige Datei, nicht nur fuer `.py`.

**Klasse 3 — Programmausgabe.** Zwei Verweise stehen nicht in einem Kommentar,
sondern in einer Fehlermeldung, die der Nutzer auf dem Terminal liest:

| Datei | Zeile | Was gedruckt wird |
|---|---|---|
| `src/previously/core/canonical.py` | 53 | `…floating point number not allowed — state a scale as an integer (§3.2)` |
| `src/previously/core/append.py` | 301 | `…kind of evidence (§5.1), so that it is not silently overwritten` |

Fuer diese beiden ist **keine** der zwei Behandlungen richtig. Ein
`{ref}`-Label in einer Programmausgabe erscheint dem Nutzer als wortwoertlicher
Unsinn, und `(§3.2, frozen design record)` in einer Fehlermeldung ist schlimmer
als der heutige Zustand: wer `previously append` aufruft, hat
`docs/superpowers/specs/` nicht und wird es auch nicht bekommen.

**Zu tun: die Zitierung aus der Meldung entfernen, nicht umschreiben.** Die
Meldungen tragen ihre Handlungsanweisung schon selbst — „state a scale as an
integer" sagt dem Aufrufer alles, was er tun kann; „(§3.2)" sagt ihm nichts.
Die Begruendung wandert in den Kommentar darueber, und der zeigt dann nach
Klasse 1 auf `{ref}`payload-range``.

Der Test aus Schritt 5 muss das erzwingen koennen, sonst schreibt der naechste
Umsetzer `(frozen design record)` in die Fehlermeldung und der Test ist gruen.
Siehe die Ergaenzung in Schritt 5.

### Was an dieser Aufgabe haengt und nicht in ihrer Dateiliste steht

`docs/reference/hash-format.md` zitiert seit Aufgabe 6 **fuenf** Fehlermeldungen
aus `core/canonical.py` woertlich, darunter die mit dem `§3.2`. Nachgemessen am
2026-10-03: alle fuenf stimmen heute buchstabengenau mit dem Code. Es haelt sie
aber **nichts** — `tests/test_docs_typed_output.py` deckt nur die Testzahlen im
Tutorial.

Daraus folgen zwei Dinge fuer diese Aufgabe:

1. Die Zeile `docs/reference/hash-format.md:22` aendert sich **im selben
   Commit** wie die Meldung in `canonical.py`. Der Plan sagte „diese Aufgabe
   fasst nur Kommentare an" — das war falsch, sie fasst eine Reference-Seite
   mit an. Die drei Vektortests bleiben als Riegel richtig, sie reichen aber
   nicht: sie sehen eine geaenderte Fehlermeldung nicht.
2. Der Test aus Schritt 5 bekommt die Aufgabe, die Zitate festzunageln — und
   zwar indem er die Meldungen **vom Code erzeugen laesst**, nicht indem er
   Zeichenketten in zwei Dateien vergleicht. Eine Zeichenkettensuche findet
   eine geaenderte Meldung nicht wieder; ein Aufruf von `canonical()` mit
   einem Gleitkommawert liefert sie.

`pyproject.toml:88` traegt den letzten Verweis ausserhalb des Codes
(`# Printing to stdout is what this module is for (§9 of the stage 1a spec)`).
Er begruendet eine heutige Lint-Ausnahme, ist also Klasse 1 — aber die
Begruendung steht schon vollstaendig im Satz davor. Streich die Klammer; ein
Verweis, der nichts hinzufuegt, ist nach dem Einfrieren nur noch ein toter
Zeiger.

- [ ] **Schritt 5: Den Test zuerst schreiben**

`tests/test_docs_references.py`:

```python
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sphinx checks cross-references inside the documentation.

Nobody checks a reference that sits in a Python comment. After the migration
there are dozens of them, so this test is the only thing standing between a
renamed label and a comment that points nowhere.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["src", "tests", "migrations"]
DOCS = ROOT / "docs"

REFERENCE = re.compile(r"\{ref\}`([a-z0-9-]+)`")
LABEL = re.compile(r"^\(([a-z0-9-]+)\)=\s*$", re.MULTILINE)


def _labels() -> set[str]:
    found: set[str] = set()
    for page in DOCS.rglob("*.md"):
        if "superpowers" in page.parts or "_build" in page.parts:
            continue
        found.update(LABEL.findall(page.read_text(encoding="utf-8")))
    return found


def _references() -> dict[str, list[str]]:
    used: dict[str, list[str]] = {}
    for directory in SOURCE_DIRS:
        for module in (ROOT / directory).rglob("*.py"):
            text = module.read_text(encoding="utf-8")
            for name in REFERENCE.findall(text):
                used.setdefault(name, []).append(str(module.relative_to(ROOT)))
    return used


def test_every_doc_reference_in_the_code_resolves() -> None:
    labels = _labels()
    dangling = {
        name: files for name, files in _references().items() if name not in labels
    }
    assert not dangling, (
        f"These labels are referenced from code but defined in no page: {dangling}. "
        "Either the label was renamed or the page was not written yet."
    )


def test_no_bare_paragraph_references_remain() -> None:
    """A bare `§3.1` points at a frozen German document without saying so."""
    offenders: dict[str, int] = {}
    for directory in SOURCE_DIRS:
        for module in (ROOT / directory).rglob("*.py"):
            text = module.read_text(encoding="utf-8")
            bare = [
                line
                for line in text.splitlines()
                if "§" in line and "frozen design record" not in line
            ]
            if bare:
                offenders[str(module.relative_to(ROOT))] = len(bare)
    assert not offenders, (
        f"Bare paragraph references remain: {offenders}. Map them to a {{ref}} label "
        "or mark them as pointing at a frozen design record."
    )
```

Dazu zwei Tests, die die zwei oben gemessenen Loecher schliessen. Der erste
haelt die Programmausgabe frei von Zitierungen, der zweite nagelt die
Reference-Zitate fest, indem er sie vom Code erzeugen laesst:

```python
RUNTIME_MESSAGE_FILES = [
    ROOT / "src" / "previously" / "core" / "canonical.py",
    ROOT / "src" / "previously" / "core" / "append.py",
]


def test_no_program_output_cites_a_specification() -> None:
    """A paragraph reference in an error message is a dead pointer.

    Whoever runs `previously append` has no `docs/superpowers/specs/`, so the
    citation buys them nothing even before the freeze makes it stale. Measured
    on 2026-10-03: two messages carried one, `canonical.py:53` with `§3.2` and
    `append.py:301` with `§5.1`. Marking them as a frozen design record would
    pass `test_no_bare_paragraph_references_remain` while making the output
    worse, which is why this test exists beside it.
    """
    offenders: dict[str, list[int]] = {}
    for path in RUNTIME_MESSAGE_FILES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if "§" in line and ('f"' in line or '"' in line and "raise" in line):
                offenders.setdefault(str(path.relative_to(ROOT)), []).append(number)
    assert not offenders, (
        f"These lines print a paragraph reference to the user: {offenders}. "
        "Move the reasoning into the comment above and drop it from the message."
    )


def test_the_reference_quotes_what_the_code_actually_prints() -> None:
    """The Payload range table quotes five messages verbatim.

    Nothing else holds them: the typed-output gate covers only the test counts
    in the tutorial. A string search across the two files would not help -- it
    would follow a changed message into the page. So the messages are produced
    by calling the code, which is the only form of this check that can fail for
    the right reason.
    """
    from previously.core.canonical import canonical
    from previously.core.errors import InvalidPayload

    produced = []
    for payload in (
        {"amount": 1.5},
        {"Total": 1},
        {"amount": 2**53},
        {"text": "a\x00b"},
        {"text": "a\ud800b"},
    ):
        try:
            canonical(payload)
        except InvalidPayload as error:
            produced.append(str(error))
        else:  # pragma: no cover - a passing payload would be the bug
            raise AssertionError(f"{payload!r} was accepted")

    page = (DOCS / "reference" / "hash-format.md").read_text(encoding="utf-8")
    for message in produced:
        # The page prefixes no path, the message does: compare the part the
        # page quotes, which is everything after `$`/`.name`/`[n]` and ": ".
        quoted = message.split(": ", 1)[1]
        assert quoted in page, (
            f"hash-format.md does not quote {quoted!r}. The code's message changed; "
            "the Payload range table has to change in the same commit."
        )
```

- [ ] **Schritt 6: Test laufen lassen — er muss scheitern**

Run: `uv run pytest tests/test_docs_references.py -v`
Expected: FAIL, `test_no_bare_paragraph_references_remain` listet 21 Dateien.

- [ ] **Schritt 7: Umstellen, Datei für Datei**

Die 21 Dateien: `src/previously/cli.py`, `core/{append,canonical,errors,hashing,units,verify}.py`, `storage/{postgres,rows,schema}.py`, `migrations/dsn.py`, `migrations/versions/0001_log.py`, `tests/{test_append,test_canonical,test_cli,test_contracts,test_hashing,test_properties,test_rows,test_schema,test_storage,test_verify}.py`.

Geh nach der Tabelle aus Schritt 1 vor, nicht nach Gefühl. Ändere **nur** den Verweis, nicht den Begründungstext darum.

Die Verweise auf Prüfbefunde und Rulings (`review finding B1`, `Ruling T8-c`) **bleiben wie sie sind** — sie bezeichnen Sitzungsgeschichte, nicht lebende Begründung, und für die ist der eingefrorene Bericht der richtige Ort.

- [ ] **Schritt 8: Tests laufen lassen — beide müssen bestehen**

Run: `uv run pytest tests/test_docs_references.py -v`

- [ ] **Schritt 9: Alle Tore, und der Vektor**

```shell
uv run pytest
make -C docs html
```

Erwartet unter anderem: `test_vector_payload_hash`, `test_vector_units_hash`, `test_vector_event_hash` grün. Diese Aufgabe fasst nur Kommentare an; schlägt einer der drei an, hast du mehr geändert als gedacht.

- [ ] **Schritt 10: Commit**

`docs: point the code at the documentation, and keep it honest with a test`

---

