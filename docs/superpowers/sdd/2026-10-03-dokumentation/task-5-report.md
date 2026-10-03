# Aufgabe 5 — Bericht: Explanation, Teil 1 (die Kette)

Zweig `worktree-dokumentation`, Worktree `.claude/worktrees/stufe-1a-log`, BASE `5e2eced`.
Ein Commit: `8d0f42b` — *docs: explain the hash chain and the canonicalization*.

Angelegt: `docs/explanation/hash-chain.md`, `docs/explanation/canonicalization.md`.
Geändert: `docs/explanation/index.md` (Toctree), `.vale-styles/config/vocabularies/Previously/accept.txt` (drei Wörter).
Kein Code angefasst, 189 Tests unberührt.

Schritt 3 **ausgelassen** — siehe Abweichung A.

---

## Die Überlebensliste, Punkt für Punkt

Alle fünfzehn Punkte sind untergebracht, jeder mit seiner Zahl und seiner Messung.

| # | Begründung | Datei | Abschnitt |
|---|---|---|---|
| 1 | Hash deckt den Digest, nicht die Nutzlast; Tilgungs-Naht, ihr Preis, ihre Einlösung | `docs/explanation/hash-chain.md` | `## The chain covers a digest, not the content` (Label `tombstone-seam`), samt `:::{important}`-Kasten zum Preis |
| 2 | `id = Vorgänger.id + 1`, keine Sequenz, Kette 9 → 11 → 10 | `docs/explanation/hash-chain.md` | `## The identifier comes from the predecessor, not from a sequence` |
| 3 | `recorded_at` ist Eingabe, nicht Ausgabe; stabil über Wiederholungen; Hash aus `show` nicht reproduzierbar | `docs/explanation/hash-chain.md` | `## Timestamps are input, not output` (Label `timestamps`) |
| 4 | Einheiten und Quellenangabe in den Hash, drei gemessene Fälschungen + Gegenprobe, acht → elf Felder | `docs/explanation/hash-chain.md` | `## What the chain has to cover, and the forgeries that taught it` |
| 5 | Was die Kette nicht deckt (Spitze, Anhängen, Neuschreiben); Anhängen schärfer als Löschen; Schlusssatz | `docs/explanation/hash-chain.md` | `## What the chain doesn't cover` |
| 6 | Zählabgleich; `id = 0` eingeschmuggelt, `read(from_id=-5) -> [0, 1]`; `event_prev_hash_idx` weist die genesis-artige Zeile ab | `docs/explanation/hash-chain.md` | `## Counting the rows the check has seen` |
| 7 | JSON-`null` als falscher Grabstein, Messtabelle id 1/id 2, `CHECK`-Beschränkung, zweiteilige Einordnung | `docs/explanation/hash-chain.md` | `## The tombstone that wasn't one` |
| 8 | Bereichstrennung über `v`/`domain`; was ein `v = 2` wirklich bräuchte; verlustfrei nachrüstbar | `docs/explanation/hash-chain.md` | `## Separating the domains` (Label `hash-domain`) |
| 9 | Was eine Einheit ist (§6) und der CRLF-Fund | `docs/explanation/hash-chain.md` | `## What a unit is` |
| 10 | Höchstens eine Quellenangabe je Event; `external_id` bezeichnet das Artefakt | `docs/explanation/hash-chain.md` | `## At most one source attribution per event` |
| 11 | JCS statt Verkettung, `"ab"+"c"` = `"a"+"bc"`, dieselbe Maschinerie mehrfach | `docs/explanation/canonicalization.md` | `## Concatenation is ambiguous, a canonical object isn't` |
| 12 | Der enge Nutzlastbereich, je Einschränkung der Grund | `docs/explanation/canonicalization.md` | `## The payload range is narrow on purpose` |
| 13 | Der reservierte Schlüssel `evidence` | `docs/explanation/canonicalization.md` | `## The reserved key` |
| 14 | Derselbe Schlüssel zweimal in einem Stapel wird abgewiesen, `append([first, second]) -> [1, 1]` | `docs/explanation/canonicalization.md` | `## The same key twice in one batch` |
| 15 | Der festgenagelte Testvektor und die kanonischen Bytes daneben | `docs/explanation/canonicalization.md` | `## The pinned test vector` |

Die fünf Label, wörtlich: `(hash-chain)=`, `(hash-domain)=`, `(tombstone-seam)=`, `(canonicalization)=`, `(timestamps)=`.

Verwendete Reference-Label statt wiederholter Fakten: `hash-format` (3×), `database-schema` (2×), `cli-reference` (2×), `configuration-reference` (1×).

---

## Gelesene Quellabschnitte

- `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`: §1, §1.1 samt Korrektur K1, §2, §3.1 mit den drei Kästen, §3.2, §3.3, §3.4 samt Kasten zu Korrektur K-1, §5 samt N-5-Kasten und dem Unterabschnitt zu `external_id`, §6, §7 (Anfang).
- `docs/superpowers/specs/2026-10-01-architektur.md`: §4.3, §4.6 vollständig.
- Code, gegen den ich die Spezifikation geprüft habe: `src/previously/core/canonical.py`, `core/units.py`, `core/append.py` (`_prepare`, `append`), `core/verify.py`, `cli.py` (`_cmd_show`, `_cmd_log`).
- Vorhandene Doku: alle vier Quadranten-Indizes, `reference/hash-format.md`, `reference/database-schema.md`, `reference/cli.md`, `reference/configuration.md`, `how-to/verify-the-chain.md`, `conf.py`, `docs/Makefile`, `.vale.ini`, das Vale-Vokabular und die Microsoft-Regeln unter `.vale-styles/Microsoft/`.

---

## Abweichungen und Befunde

### A. Schritt 3 ausgelassen — Vorwärtsverweis, wie im Auftrag vorhergesagt

`(concurrency)=` existiert nirgends im Baum; der einzige Treffer ist der Plan selbst
(`docs/superpowers/plans/2026-10-03-dokumentation.md:717`, als **Produkt von Aufgabe 6**).
Ein `{ref}`concurrency`` in `docs/reference/configuration.md` hätte unter `-W` genau den
Fehlschlag erzeugt, den Aufgabe 2 gemessen hat. `docs/reference/configuration.md` bleibt
unberührt; der Verweis gehört in Aufgabe 6, sobald das Label existiert.

### B. Überlebensliste Punkt 11 zählt die Verwendungen falsch

Punkt 11 sagt, die Maschinerie werde „**zweimal** gebraucht, für `payload_hash` und für
den Event-Hash". Spec §3.1 sagt „ein Kanonisierer, **drei** Verwendungen", und der Code
gibt der Spec recht: `canonical()` wird aus `payload_hash`, `units_hash` **und**
`event_hash` gerufen (`src/previously/core/hashing.py`). Die Seite sagt darum drei.
Die Überlebensliste ist an dieser Stelle zu korrigieren, nicht die Seite.

### C. Überlebensliste Punkt 12 gibt zwei Einschränkungen einen gemeinsamen, falschen Grund

Punkt 12 fasst „keine Nullbytes, keine einsamen UTF-16-Surrogate" unter „nicht als UTF-8
darstellbar". Für das Nullbyte ist das nicht wahr: U+0000 **ist** in UTF-8 darstellbar.
Der Code nennt zwei verschiedene Gründe (`core/canonical.py`):

- Nullbyte: `"null byte not allowed — PostgreSQL jsonb cannot store it"`
- einsames Surrogat: `"string not representable as UTF-8 … a lone UTF-16 surrogate, for instance"`

Der Code gilt. Die Seite nennt beide Gründe getrennt und sagt dazu, warum das Abfangen
im Kanonisierer trotzdem richtig ist (ein Treiberfehler mitten im Schreiben wird zu einer
klaren Abweisung vor der ersten Transaktion).

### D. Punkt 3, Teilaussage zu `show`: stimmt, mit einem schärferen Grund

Die Aussage „der Hash ist in der `show`-Ausgabe nicht reproduzierbar" ist richtig, und
der Grund ist nachprüfbar stärker als „weil `recorded_at` Eingabe ist":
`_cmd_show` druckt `id`, `kind`, `occurred_at`, `hash`, `evidence`, `payload` und die
Einheiten — **nicht** `recorded_at` und auch nicht `prev`, `source`, `external_id`.
Vier der elf gehashten Felder fehlen der Ausgabe. Die Seite sagt es so.

### E. Der Schlusssatz ist um zwei Wörter geändert — erzwungen von Vale

Der im Brief vorgegebene Satz verstößt zweimal gegen `Microsoft.Contractions`
(**error**-Level, nicht abschaltbar für die Explanation):
`cannot` → `can't` und `it is` → `it's`. Gemessen, am Satz des Briefs:

```
3:38  error  Use 'it's' instead of 'it is'.    Microsoft.Contractions
3:62  error  Use 'can't' instead of 'cannot'.  Microsoft.Contractions
```

Ausgeliefert, in zwei Zeilen wegen der Ein-Satz-pro-Zeile-Regel:

```markdown
*What the log says is unaltered.*
*That it's complete, the log can't attest by itself.*
```

### F. Die Messprotokolle stehen englisch, nicht als deutsches Zitat

Spec §1.1 hält ausdrücklich fest, dass die K1-Messung deutsch zitiert bleibt („eine
Aufzeichnung wird wörtlich zitiert oder nicht"). Auf einer englischen Explanation-Seite,
die laut Aufgabe 7 **maßgeblich** wird, habe ich stattdessen die Befundtexte in der Form
gesetzt, die der Code **heute** ausgibt — `payload_hash does not match the payload`,
`prev_hash does not match the predecessor`, wörtlich aus `core/verify.py`. Die Spec
verweist für die heutige Form selbst auf §3.4 und §10.1. Das ist eine Ermessensfrage; wer
die wörtliche deutsche Aufzeichnung auf der Seite haben will, muss es sagen.

### G. `Microsoft.BiasFree` hat eine Überschrift erzwungen

„The chain **hangs** on the digest" → `Consider 'stops responding' instead of 'hangs'.`
Die Überschrift heißt darum `## The chain covers a digest, not the content`.

### H. Vokabular: drei Wörter, und eine Falle, die dabei auffiel

Eingetragen, jedes einzeln von Vale beanstandet und einzeln geprüft:
`canonicalization`, `canonicalize`, `canonicalizer`.

Nicht eingetragen, obwohl zuerst versucht: `Canonicalization`. **Gemessen:** stehen
`canonicalization` und `Canonicalization` beide im Vokabular, erzwingt `Vale.Terms` die
**großgeschriebene** Form überall — fünf Fehler, auch im Label `(canonicalization)=` und
in der Überschrift:

```
1:2  error  Use 'Canonicalization' instead of 'canonicalization'.  Vale.Terms
```

Darum nur die Kleinform, und der Eigenname „JSON Canonicalization Scheme" ist zu
„the canonicalization scheme for JSON" umformuliert (RFC 8785 steht als Nummer daneben).

**Daraus folgt ein latenter Befund für den Baum:** das Vokabular enthält `nullable`
**und** `Nullable`. Nach derselben Messung erzwingt Vale damit heute `Nullable` überall.
Das fällt nur nicht auf, weil „nullable" in der Prosa nirgends vorkommt — die drei
Treffer sind Tabellenköpfe in `reference/database-schema.md`. Wer das Wort einmal klein
in einem Satz schreibt, bekommt einen Fehler, den niemand erwartet. Ein Eintrag von
beiden Schreibweisen ist in diesem Vokabular also keine Erlaubnis, sondern ein Zwang.

### I. Empfehlung, nicht umgesetzt (außerhalb meiner Dateiliste)

`docs/how-to/verify-the-chain.md` endet mit „… see the explanation of the hash chain" —
Prosa, weil das Label zur Bauzeit nicht existierte. Es existiert jetzt. Ein
`{ref}`hash-chain`` gehört dort hin; die Datei steht nicht in meiner Liste, darum
unverändert. Gehört zu Aufgabe 6 oder 7.

### J. Keine Abweichung zwischen Spec und Code gefunden, über B/C/D hinaus

Geprüft wurden: die elf Hash-Felder gegen `hashing.py` und `reference/hash-format.md`
(elf, übereinstimmend), die fünf Prüfungen gegen `verify.py` (fünf, Befundtexte wörtlich
übernommen), `event_payload_object_check` gegen `storage/schema.py`, die
CRLF-Normalisierung gegen `core/units.py` (§6 der Spec **nennt sie nicht** — sie steht
nur im Code und in `tests/test_units.py`; das ist keine Abweichung, sondern die Lücke,
die der Brief selbst benennt, und sie ist jetzt dokumentiert), die Stapelabweisung und
den reservierten Schlüssel gegen `core/append.py:_prepare`.

---

## Form

- **Diagramme: genau eines**, in `hash-chain.md`, `graph LR`, die Digest-Umleitung.
  Kein `:alt:`, stattdessen `:caption:` **und** ein Satz Prosa davor („The diagram below
  shows that detour for both of them, two hops where an obvious design would have one.").
  Gerendert geprüft: `<figure>` mit `<figcaption>` in `_build/html/explanation/hash-chain.html`.
  In `canonicalization.md` **kein** Diagramm.
- **Direktive mit Prosa:** `:::{important}` mit Doppelpunkt-Fence, damit Vale den Inhalt
  prüft (und er wird geprüft: die Vale-Läufe haben darin Fehler gefunden und ich habe sie
  behoben). Codeblöcke und die Mermaid-Direktive bleiben bei Backticks.
- Genau **eine** Admonition je Seite-Paar, auf `hash-chain.md`, für den Preis der Naht.
- Keine Schrittfolgen, keine Spaltentabellen, kein „we"/„our"/„us". Ein Satz pro Zeile.
- Toctree-Eintrag in `docs/explanation/index.md` als zwei Zeilen am Blockende, damit
  Aufgabe 6 darunter anfügen kann, ohne eine Zeile von mir zu berühren.

## Tor-Ausgaben

```
$ make -C docs html
build succeeded.
(0 WARNINGs, unter SPHINXOPTS = -W --keep-going)

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 15 files.

$ make -C docs linkcheck
build succeeded.
_build/linkcheck/output.txt ist leer

$ uv run pytest -q
189 passed in 16.55s
```

Vorher-Messung derselben Suite, vor jeder Änderung: `189 passed in 16.47s`.
Die Tore sind nach dem Commit noch einmal aus einem `make -C docs clean` heraus gefahren,
nicht nur aus dem warmen Baum.
`docs/superpowers/plans/2026-10-03-dokumentation.md` trägt eine Änderung, die vor meinem
Start schon im Baum lag — nicht von mir, nicht eingecheckt, unberührt gelassen.

---

## Fixrunde 1 — vier Genauigkeitspunkte

Alle vier am Code nachgeprüft, alle vier bestätigt, alle vier umgesetzt.
Commit darunter; Tore danach noch einmal aus einem `make -C docs clean` heraus.

### 1. Punkt 3 trug seine Zahl nicht

Stimmt. Die Stelle nannte `recorded_at`, `prev`, `source`, `external_id` namentlich
und ließ den Leser zählen.

Nachgetragen, und dabei gleich **anders** formuliert als nur mit einer Zahl davor:
„never reach that output" wäre mit einer Zahl erst falsch geworden. Nicht gedruckt
werden nämlich **sechs** der elf Felder — `v` und `domain` stehen auch nicht in der
Ausgabe. Sie sind aber Konstanten, und `payload_hash`/`units_hash` lassen sich aus
der gedruckten Nutzlast und den gedruckten Einheiten nachrechnen. Nicht
**wiedergewinnbar** sind genau vier. Also:

> Four of the eleven hashed fields can't be recovered from that output at all:
> `recorded_at`, `prev`, `source` and `external_id`; see {ref}`cli-reference` for
> what `show` does print.

### 2. Zwei Reference-Fakten wiederholt statt verlinkt

Stimmt beides, beides bereinigt, die Begründung bleibt jeweils stehen.

- Zeitstempel: „ISO 8601, UTC, six fractional digits, `Z` suffix" ist raus, dafür
  „the timestamp is a canonical string, and {ref}`hash-format` holds its exact
  shape". Der Grund — gehasht wird die kanonische Zeichenkette, nicht was eine
  Sprachbibliothek zufällig ausgibt, und `timestamptz` macht den Rundlauf
  verlustfrei — steht unverändert daneben.
- Bereichskennungen: `v` is `1` und die zwei `domain`-Strings sind raus, dafür
  „carry a version and a domain of their own, and {ref}`hash-format` holds both
  pairs". **Nicht** „the four values", obwohl das mein erster Versuch war:
  `hash-format` listet vier Tabellenzellen, aber nur drei verschiedene Werte, und
  eine Zahl, die sich zweimal zählen lässt, ist genau der Fehler, den Punkt 1
  dieser Runde abstellt. Die Argumentation darunter benutzt „version 1" weiter —
  das ist Begründung („jede bis dahin geschriebene Zeile ist per Definition
  version 1"), keine Wiederholung einer Tabelle.

### 3. Zwei Stellen versprachen mehr als sie halten

Stimmt beides.

- `reference/cli.md:50` gibt nur `FINDING <event_id>: <reason>`. Jetzt: „gives the
  one line each of them prints as" statt „shows how each one prints".
- „Four of them … compare a digest against what it covers" war falsch für die
  `prev_hash`-Prüfung. Nachgeprüft in `core/verify.py:113-117`: dort steht
  `row.prev_hash != previous_hash`, also **Digest gegen Digest**. Die anderen drei
  vergleichen einen Digest gegen das, was er deckt (Nutzlast, Einheiten, Felder).
  Jetzt steht „three of those four … and the fourth compares one stored digest
  against another, `prev_hash` against the predecessor's `hash`, which makes it the
  link itself rather than a seal over content." Der Zusatz ist nicht Kosmetik: er
  sagt, **warum** diese Prüfung anders gebaut ist.

### 4. Eine unbedingte Aussage, die bedingt stimmt

Stimmt. `tests/test_hashing.py:225-227` sagt es bedingt: „Should the hash range
change **deliberately**, `HASH_VERSION` belongs raised and this vector recomputed;
both then come to notice together."

Nachgezogen, aus „never fixed by recomputing it" wurde „almost never", und die
Ausnahme steht daneben, samt dem Satz, der sie prüfbar macht:

> A recomputed vector beside an unchanged version is therefore the signature of
> the shortcut.

(„unexpectedly" war mein erster Versuch für den bedingten Satz und fiel bei
`Microsoft.Adverbs` durch — gemessen, `111:21 warning`. Daher „almost never".)

### Zwei Korrekturen an meinen eigenen Angaben

- **`hash-chain.md` hat zehn H2-Abschnitte, nicht elf.** Nachgezählt:
  `grep -c '^## '` gibt 10 für `hash-chain.md` und 5 für `canonicalization.md`. Die
  Elf stand in meinem Bericht an den Auftraggeber und ist von dort in seinen Brief
  gewandert — ein Zahlenfehler meiner Seite, der eine Runde lang weitergereicht
  wurde. Genau der Fehlertyp, gegen den die Überlebensliste gebaut ist, nur in der
  Metaebene.
- Zur Nichtteilung der Seite: der Prüfer hat fünf Rückgriffe über
  Abschnittsgrenzen gemessen und würde einer Teilung widersprechen. Damit ist meine
  Bedenke 4 erledigt — sie bleibt ungeteilt, und zwar aus einem gemessenen Grund
  statt aus meinem Geschmack.

### Nicht angefasst, wie angewiesen

- Der Nutzlastbereich bekommt eine Reference-Heimat in Aufgabe 6.
- „the five silent losses of data" bleibt wörtlich stehen, bis
  `{ref}`silent-losses`` in Aufgabe 6 existiert. Beide Vorkommen (CRLF in
  `hash-chain.md`, `evidence` in `canonicalization.md`) sind unverändert.
- `reference/hash-format.md:57` (dieselbe Überschießung wie Punkt 4, eine Seite
  weiter) nimmt der Auftraggeber mit.
- `docs/reference/configuration.md` bleibt ohne `{ref}`concurrency``.

### Tor-Ausgaben der Fixrunde

```
$ make -C docs clean && make -C docs html
build succeeded.          (0 WARNINGs unter -W --keep-going)

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 15 files.

$ make -C docs linkcheck
build succeeded.          (_build/linkcheck/output.txt: 0 Bytes)

$ uv run pytest -q
189 passed in 16.50s
```
