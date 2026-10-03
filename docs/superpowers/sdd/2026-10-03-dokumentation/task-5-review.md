# Aufgabe 5 — Prüfung: Explanation, Teil 1 (die Kette)

Geprüft: `5e2eced..8c01fc6`, Worktree `.claude/worktrees/stufe-1a-log`.
`docs/explanation/hash-chain.md` (315 Zeilen), `docs/explanation/canonicalization.md` (112).
Nur gelesen. Arbeitsbaum, Index und HEAD unverändert; `docs/_build/` ist auf `.gitignore`.
Experimente in einer Kopie unter dem Scratchpad, nicht in einem Git-Worktree —
damit blieb auch die Repo-Metadata unberührt. Danach entfernt.

## Zwei Urteile

**Spec-Treue: bestanden.** Fünfzehn von fünfzehn Punkten stehen auf den Seiten,
alle drei korrigierten Punkte in der korrigierten Fassung. Jede Zahl und jede
Messung der Liste habe ich gegen den Code nachgeprüft, nicht gegen den Bericht
und nicht gegen die Spec. Ein Punkt (3) trägt seine Zahl nur implizit.

**Qualität: bestanden mit Anmerkungen.** Beide Seiten halten die
Explanation-Grenze deutlich. Acht Befunde, keiner davon blockierend; einer
davon (Nutzlastbereich ohne Reference-Heimat) gehört vor Aufgabe 7 entschieden.

---

## Die fünfzehn Punkte, Punkt für Punkt

Spalte „Zahl/Messung" sagt, was die Seite **wörtlich** trägt — nicht, was sich
daraus folgern lässt.

| # | Begründung | Fundstelle | Zahl / Messung auf der Seite | Urteil |
|---|---|---|---|---|
| 1 | Hash deckt den Digest, nicht die Nutzlast; Naht, Preis, Einlösung | `hash-chain.md:16-61` | `verify() -> []` (`:49`); „A tombstone is indistinguishable from a forgery" (`:48`); Einlösung über ein Tilgungs-Event (`:56-59`); Preis „one column" gegen „the whole chain" (`:39-40`) | **bestätigt** |
| 2 | `id = Vorgänger.id + 1`, keine Sequenz | `hash-chain.md:96-119` | `9 → 11 → 10` (`:103`); „That's the reason no sequence stands here. It isn't thrift." (`:104-105`) | **bestätigt** |
| 3 | `recorded_at` ist Eingabe; `show` nicht nachrechenbar | `hash-chain.md:121-144` | „The caller sets `recorded_at`" (`:125`), „Neither the database nor the append loop produces it" (`:126`), Stabilität über Wiederholungen (`:130-131`); vier Felder **namentlich**: `recorded_at`, `prev`, `source`, `external_id` (`:142-143`) — die **Zahl** „vier der elf" steht nicht da | **bestätigt, mit Vorbehalt** (Befund 1) |
| 4 | Einheiten und Quellenangabe in den Hash; drei Fälschungen + Gegenprobe; acht → elf | `hash-chain.md:146-188` | Messblock mit allen vier Zeilen (`:154-159`); „The event hash wraps eleven fields today instead of eight." (`:164`); „The specification once listed eight hash fields" (`:148`) | **bestätigt** |
| 5 | Was die Kette nicht deckt; Anhängen schärfer als Löschen; Schlusssatz | `hash-chain.md:284-315` | drei Manipulationen (`:287-289`); Spitzenlöschung gemessen, mit Protokoll (`:294-299`); „Deleting takes a statement away from the store; appending puts one into its mouth." (`:307`); Schlusssatz (`:314-315`) | **bestätigt** |
| 6 | Zählabgleich; `id = 0`; `event_prev_hash_idx` | `hash-chain.md:252-282` | `row with id = 0 smuggled in -> verify() -> []` / `read(from_id=-5) -> [0, 1]` (`:262-263`); „Displayed … and never checked" (`:266`); genesis-artige Zeile abgewiesen (`:275`) | **bestätigt** |
| 7 | JSON-`null` war ein falscher Grabstein | `hash-chain.md:63-94` | Messtabelle id 1 / id 2 vollständig, samt `finds: [1]` und `verify() -> []` (`:72-79`); `CHECK (payload IS NULL OR jsonb_typeof(payload) = 'object')` (`:84`); beide Teile der Einordnung (`:87-90`) | **bestätigt** |
| 8 | Bereichstrennung; was ein `v = 2` bräuchte | `hash-chain.md:226-250` | keine Fassungsangabe je Zeile (`:236`); Rateverfahren als „offer to the forger" (`:238`); `ALTER TABLE event ADD COLUMN hash_version smallint NOT NULL DEFAULT 1` (`:240`); verlustfrei, weil alle Altzeilen per Definition v=1 (`:241-242`) | **bestätigt** |
| 9 | Was eine Einheit ist (§6); der CRLF-Fund | `hash-chain.md:190-203` | vier Schritte in Prosa, „number from 1" (`:194`); „one of its five silent losses of data" (`:197`); „the pair `\r\n` before the single `\r`" (`:198`); RFC 5322, **eine** Einheit (`:201`) | **bestätigt** (zur „fünf" siehe Befund 6) |
| 10 | Eine Quellenangabe je Event; `external_id` = Artefakt | `hash-chain.md:205-224` | Unique-Constraint auf `source_key.event_id` (`:208`); „**An `external_id` names the artifact, not the transport.**" (`:213`); Message-ID gegen IMAP-UID (`:214`); Idempotenz greift von selbst (`:218`) | **bestätigt** |
| 11 | JCS statt Verkettung; **dreimal** | `canonicalization.md:11-24` | `"ab" + "c"` und `"a" + "bc"` (`:14`); „gets used three times, not once: for `payload_hash`, for … `units_hash`, and for … the event hash" (`:19`) | **bestätigt, in der korrigierten Fassung** |
| 12 | Enger Nutzlastbereich, je Einschränkung der Grund | `canonicalization.md:26-59` | alle fünf; `^[a-z][a-z0-9_]*$` (`:43`); `±(2**53 - 1)` (`:48`); Nullbyte **und** Surrogat mit **getrennten** Gründen und dem Satz „The two share a section and have separate reasons." (`:52-55`) | **bestätigt, in der korrigierten Fassung** |
| 13 | Reservierter Schlüssel `evidence` | `canonicalization.md:61-70` | Abweisung statt stillem Überschreiben (`:63`); nicht nachtragbar im append-only Speicher (`:67-68`); „one of the five silent losses of data" (`:70`) | **bestätigt** |
| 14 | Derselbe Schlüssel zweimal in einem Stapel | `canonicalization.md:72-98` | `append([first, second]) -> [1, 1]` samt vollem Protokoll (`:78-87`); „two identifiers back as though both entries had been recorded" (`:89`); zwischen/innerhalb (`:92-96`); „at index 0 and index 1" (`:98`) | **bestätigt** |
| 15 | Festgenagelter Testvektor | `canonicalization.md:100-112` | drei Hex-Werte **und** die kanonischen Bytes (`:102-103`); „one-bit verdict into a diff" (`:108`); Verweis auf {ref}`hash-format` statt Wiederholung (`:103`) | **bestätigt** |

**14 vollständig bestätigt, 1 mit Vorbehalt (Punkt 3), 0 fehlend.**

---

## Die drei Korrekturen, am Code nachgeprüft

| Korrektur | Belegstelle | Ergebnis |
|---|---|---|
| Punkt 11: **dreimal**, nicht zweimal | `src/previously/core/hashing.py:52`, `:116`, `:153` | `canonical()` steht genau an diesen drei Stellen. Spec §3.1 sagt ebenfalls „ein Kanonisierer, drei Verwendungen". Seite sagt drei. |
| Punkt 12: zwei verschiedene Gründe | `src/previously/core/canonical.py:58` („null byte not allowed — PostgreSQL jsonb cannot store it"), `:65` („string not representable as UTF-8 … a lone UTF-16 surrogate, for instance") | Zwei verschiedene Gründe, wörtlich wie in der korrigierten Liste. Seite nennt sie getrennt. |
| Punkt 3: vier der elf Felder | `src/previously/cli.py:138-162` druckt `id`, `kind`, `occurred_at`, `hash`, `evidence`, `payload`, Einheiten — **nicht** `recorded_at`, `prev`, `source`, `external_id` | Stimmt. Elf Felder in `hashing.py:140-152`. Seite nennt alle vier namentlich, die Zahl „vier" nicht. |

---

## Die vier Code-Stellen, die ausdrücklich verlangt waren

| Verlangt | Gemessen | Seite |
|---|---|---|
| Elf Felder des Event-Hashes | `core/hashing.py:140-152`: `v`, `domain`, `id`, `kind`, `recorded_at`, `occurred_at`, `prev`, `payload`, `units`, `source`, `external_id` = **11**. Deckungsgleich mit `docs/reference/hash-format.md:36-50`. | `hash-chain.md:12`, `:164` — richtig |
| Zählabgleich und was `read` filtert | `core/verify.py:148-175` (Befund mit `event_id = 0`), `:198` (im selben `with storage.begin()`); `storage/postgres.py:205` `event.c.id >= from_id`; `:291` `count(*)` **ohne** Bedingung | `hash-chain.md:258`, `:267`, `:272` — richtig, einschließlich „same snapshot" |
| `CHECK` gegen JSON-`null` | `storage/schema.py:73-75` und `migrations/versions/0001_log.py:62-65`, beide `payload IS NULL OR jsonb_typeof(payload) = 'object'`, Name `event_payload_object_check` | `hash-chain.md:84` — wörtlich richtig, samt Verweis auf {ref}`database-schema` |
| CRLF-Normalisierung (**nicht** in der Spec) | `core/units.py:32` `text.replace("\r\n", "\n").replace("\r", "\n")` — Paar vor Einzelzeichen; `_SEPARATOR = re.compile(r"\n[ \t]*\n[\s]*")` (`:18`) kennt kein `\r`; `tests/test_units.py:60-77`. §6 der Spec nennt sie **nirgends** — bestätigt. | `hash-chain.md:198` („the pair `\r\n` before the single `\r`"), `:201` („the separator pattern knows of no `\r` between the two `\n`"), `:203` (LF gegen CRLF → verschiedene Hashes) — **alle drei richtig**, und sie decken den Code genauer als die Spec |

Zusätzlich geprüft und richtig: kein Identity/Sequence auf `event.id`
(`schema.py:30` `autoincrement=False`) → `hash-chain.md:99`;
`event_prev_hash_idx` mit `NULLS NOT DISTINCT` (`schema.py:52-57`) →
`hash-chain.md:275`; `UniqueConstraint("event_id")` auf `source_key`
(`schema.py:125`) → `hash-chain.md:208`; die Stapelmeldung nennt beide
Positionen (`core/append.py:285-290`) → `canonicalization.md:98`; der
festgenagelte Vektor mit drei Hex-Werten **und** `JCS_PAYLOAD`/`JCS_UNITS`/
`JCS_EVENT` (`tests/test_hashing.py:244-268`) → `canonicalization.md:102-103`.

---

## Befunde

| # | Stelle | Schwere | Befund |
|---|---|---|---|
| 1 | `docs/explanation/hash-chain.md:143` | niedrig | Punkt 3 trägt seine Zahl nicht. Die vier fehlenden Felder sind namentlich genannt, „**vier** der **elf**" steht nicht da — der Leser muss zählen. Nach dem Maßstab der Liste („mit seiner Zahl") eine Lücke, inhaltlich keine. |
| 2 | `docs/explanation/hash-chain.md:133` | niedrig | Wiederholter Reference-Fakt: „ISO 8601, UTC, six fractional digits, `Z` suffix" steht sinngleich in `docs/reference/hash-format.md:52`, an dieser Stelle ohne `{ref}`. Driftgefahr, gegen die eigene Regel des Skills. |
| 3 | `docs/explanation/hash-chain.md:230` | niedrig | Dasselbe: `v` = `1` und die beiden Bereichskennungen wiederholen `docs/reference/hash-format.md:20,21,40,41`, ohne Verweis an der Stelle. |
| 4 | `docs/explanation/canonicalization.md:43,48` | **mittel** | Der Nutzlastbereich hat **keine Reference-Heimat.** `^[a-z][a-z0-9_]*$` und `±(2**53 - 1)` kommen in `docs/reference/`, `docs/how-to/`, `docs/tutorials/` und `docs/index.md` **nirgends** vor (gegrept). Ab Aufgabe 7 ist damit eine **Pflichtmenge für jeden Aufrufer** allein in der Explanation maßgeblich — das ist die Quadrantengrenze von der anderen Seite. Nicht der Fehler dieser Aufgabe (es gab nichts zu verlinken), aber es gehört in Aufgabe 6/7 vermerkt: Reference bekommt die Tabelle, die Seite behält den Grund und verlinkt. |
| 5 | `docs/explanation/canonicalization.md:111` | niedrig | „A failing pinned vector is never fixed by recomputing it" sagt unbedingt, was `tests/test_hashing.py:225-227` bedingt sagt: bei **absichtlicher** Änderung des Hash-Bereichs gehört `HASH_VERSION` erhöht **und** der Vektor neu gerechnet. `docs/reference/hash-format.md:57` trägt dieselbe unbedingte Form — beide Doku-Seiten schießen gleich weit über den Code hinaus. Ein Nebensatz genügt. |
| 6 | `hash-chain.md:197`, `canonicalization.md:70` | niedrig | „one of the five silent losses of data" ist aus der Doku **nicht auflösbar**: eine Liste der fünf steht nirgends in `docs/`. Der einzige Anker ist `docs/superpowers/specs/2026-10-02-stufe-1a-log.md:689`, und der zählt N-5 als „der fünfte stille Datenverlust **dieser Sitzung**" — eine Sitzungszählung, und die Spec friert ein. Der CRLF-Fund ist überhaupt nirgends als einer der fünf verzeichnet (nur `core/units.py:24-30`, `tests/test_units.py:60`, und der Plantext selbst). Ein bestimmter Artikel auf eine Menge, die der Leser nicht findet. |
| 7 | `docs/explanation/hash-chain.md:254` | niedrig | „{ref}`cli-reference` shows how each one prints" verspricht zu viel: `docs/reference/cli.md:50-51` gibt das Zeilenformat `FINDING <event_id>: <reason>`, nicht die fünf Befundtexte. Entweder „how a finding prints", oder die Reference bekommt die fünf Texte (Aufgabe 6/7). |
| 8 | `docs/explanation/hash-chain.md:256` | niedrig | „Four of them belong to an event and compare a digest against what it covers." Die `prev_hash`-Prüfung (`core/verify.py:113-117`) vergleicht einen gespeicherten Digest mit einem **anderen gespeicherten Digest**, nicht mit dem, was er deckt. Drei von vier passen auf die Beschreibung. |

Kein Befund zu: Spec gegen Code (über die drei Listenkorrekturen hinaus keine
Abweichung gefunden), Ein-Satz-pro-Zeile (keine Verstöße), Überschriften
(alle 15 in Satzschreibung, je eine H1), `we`/`our`/`us` (Vale grün),
Frontmatter (kein Seitenkörper im Baum trägt `html_meta` — die neuen Seiten
folgen dem bestehenden Muster), Admonition-Budget (genau eine auf dem Paar).

---

## 1. Ist das Explanation?

**Beide Seiten halten die Grenze, und nicht knapp.** Der Badewannentest geht
auf: beide sind durchlaufend argumentierend, verbinden ihre Abschnitte
untereinander, wägen Alternativen (`Decimal` geprüft und verworfen,
`canonicalization.md:38-41`; die Schlüsselmenge je Event geprüft und verworfen,
`hash-chain.md:221-224`) und urteilen offen („Of the three, appending is the one
to worry about", `:306`; „the finding deserves no inflation", `:92`; „That looks
like the wrong instinct for Python and is the right one here",
`canonicalization.md:58`). Keine Anweisung an den Leser, kein Imperativ, keine
Schrittfolge als Liste, keine Spaltentabelle. Die Titel nehmen das implizite
„About" nicht nur an, sie tragen es („About the hash chain", „About
canonicalization").

**Die Stellen am nächsten am Rand**, in dieser Reihenfolge:

1. `hash-chain.md:194` — „split at one or more blank lines, strip the whitespace
   off each section's edges, discard the empty sections, and number from 1."
   Das ist §6s **vierschrittiges Verfahren**, in einen Satz gelegt. Prosa statt
   Nummernliste ist die richtige Entscheidung, aber es bleibt die
   reference-ähnlichste Stelle der beiden Seiten — und sie hat, wie Befund 4,
   keine Reference, auf die sie verweisen könnte.
2. `canonicalization.md:32-55` — fünf fettgeführte Einschränkungen. Der
   **Aufbau** ist eine Liste, der **Inhalt** je ein Absatz Begründung. Es hält,
   weil jede Einschränkung argumentiert statt deklariert; mit einem Satz je
   Punkt wäre es eine Faktenliste gewesen.
3. `hash-chain.md:240` und `:44` — `ALTER TABLE event ADD COLUMN …` und
   `ALTER COLUMN content DROP NOT NULL`. Konkrete DDL in der Explanation, aber
   als *was es bräuchte* und nicht als *was du tun sollst*; der How-to-Rand
   wird berührt, nicht überschritten.

**Wiederholte Reference-Fakten:** zwei belegte Fälle, Befunde 2 und 3. Sonst
ist die Besitzregel gut eingehalten — die vier wichtigsten Delegationen sind
echte Delegationen: die Feldtabellen an {ref}`hash-format` (`:7`), die
`show`-Ausgabe an {ref}`cli-reference` (`:143`, und `docs/reference/cli.md:59-62`
führt die Felder tatsächlich vollständig, der Befund „vier fehlen" ist dort
nachprüfbar), der Constraint-Name an {ref}`database-schema` (`:84`), und der
Testvektor an {ref}`hash-format` (`canonicalization.md:103`, und
`docs/reference/hash-format.md:63-95` trägt wirklich **beide** Hälften).
Verteilung gemessen: `hash-format` 3×, `database-schema` 2×, `cli-reference` 2×,
`configuration-reference` 1× — wie im Bericht behauptet.

---

## 2. Die vier Entscheidungen des Umsetzers

**Schritt 3 ausgelassen — zugestimmt, unabhängig bestätigt.** `concurrency`
fehlt im gebauten `objects.inv` (17 `std:label`-Einträge, kein `concurrency`).
Unter `-W` hätte der Verweis den Bau zum Scheitern gebracht, genau wie Aufgabe 2
gemessen hat.

**Englische Befundtexte statt der deutschen K1-Zitate — zugestimmt, und
stärker als „Ermessensfrage".** Die drei Texte auf der Seite sind wörtlich
`core/verify.py:61`, `:117` und `:92`. Ab Aufgabe 7 ist diese Seite das, womit
ein Leser seine Terminalausgabe vergleicht; ein Zitat, das der Code nicht
ausgibt, wäre dort eine Falle und war in diesem Projekt schon ein Befund. Die
deutsche Aufzeichnung ist nicht verloren — sie steht weiter in der Spec, die im
Repository bleibt. Verloren wäre sie durch eine **Kopie**, die altert.

**„it's" und „can't" — zugestimmt, nachgemessen.**
`.vale-styles/Microsoft/Contractions.yml:4` ist `level: error`, und an Jens'
Wortlaut feuert es reproduzierbar:

```
4:7   error  Use 'it's' instead of 'it is'.    Microsoft.Contractions
4:31  error  Use 'can't' instead of 'cannot'.  Microsoft.Contractions
```

Eine Möglichkeit, die der Bericht nicht nennt: es gab einen dritten Weg, der
beide Regeln umgeht und den förmlichen Ton hält — *„That the log is complete, it
does not attest by itself."* Das Tor war also nicht die einzige Zwangslage. Der
ausgelieferte Satz ist trotzdem gut und trägt die Aussage vollständig; ich würde
ihn nicht anfassen.

**Nicht geteilt — zugestimmt, und ich würde einer Teilung widersprechen.**
Zuerst eine Zahlenkorrektur: es sind **zehn** H2-Abschnitte auf
`hash-chain.md`, nicht elf (`grep -n '^## '`), und fünf auf
`canonicalization.md`. Das ändert das Urteil nicht. Die Kopplung ist messbar:
`:63` („The seam has a second price") hängt an Abschnitt 1, `:186` („the reason
the seam from the first section stays usable") an Abschnitt 1, `:304` („the
argument about gaps above held only for a row in the middle") an Abschnitt 3,
`:244` („The contrast with the correction that widened the hash") an Abschnitt 5,
und `:10` verspricht den **letzten Satz dieser Seite**. Eine Teilung verwandelt
fünf interne Rückgriffe in Seitenübergänge — das ist das „No scattering" des
Quadranten, wörtlich.

Falls doch geteilt werden muss, ist die billigste Naht `## What a unit is` +
`## At most one source attribution per event` (`:190-224`): das sind die beiden
Datenmodell-Abschnitte, sie tragen **keinen** Rückgriff in den Zusagen-Bogen
hinein, und sie bräuchten genau ein `{ref}`hash-chain`` zurück. Alles andere
ist tragend.

---

## 3. Die fünf Label und das Tor

| Prüfung | Ergebnis |
|---|---|
| Fünf Label wörtlich | `(hash-chain)=` `hash-chain.md:1`, `(tombstone-seam)=` `:14`, `(timestamps)=` `:121`, `(hash-domain)=` `:226`, `(canonicalization)=` `canonicalization.md:1`. Alle fünf, buchstabengleich, jedes mit Leerzeile vor der Überschrift. |
| Label auflösbar für Aufgabe 7 | Alle fünf stehen als `std:label` in `docs/_build/html/objects.inv` und als `id="…"` im HTML. `hash-domain` zeigt auf `hash-chain.html#hash-domain`, `timestamps` auf `#timestamps`, `tombstone-seam` auf `#tombstone-seam`. Aufgabe 7 kann darauf verweisen. |
| Neubau, 0 Warnungen | `rm -rf docs/_build && make -C docs html` → `build succeeded.`, keine einzige Warnung unter `SPHINXOPTS = -W --keep-going`. |
| Alle `{ref}` im HTML aufgelöst | Alle 8 auflösend, mit korrektem Linktext: Hash format, Database schema, Command line, Database schema, Command line, Configuration (hash-chain); Hash format ×2 (canonicalization). Kein `?`-Platzhalter, kein leerer Linktext. |
| Direktive mit Prosa in Doppelpunkt-Fence | `:::{important}` (`hash-chain.md:46-61`). **Nachgemessen**, dass das der Unterschied ist: Vale prüft den Inhalt einer Doppelpunkt-Fence und **nicht** den einer Backtick-Fence (Probe: ein `we` in `:::{important}` → `Microsoft.We`; dasselbe `we` in ```` ```{important} ```` → 0 Treffer). Codeblöcke und Mermaid bleiben bei Backticks — richtig. |
| `:alt:` / `:caption:` / Prosa davor | Kein `:alt:`, `:caption:` vorhanden, gerendert als `<figure>` mit `<figcaption>` und **ohne** jedes `alt=`. Prosasatz davor: `hash-chain.md:22`. Genau ein Diagramm auf dem Paar. |
| Vale | `make -C docs vale` → 0 errors, 0 warnings, 0 suggestions in 15 files. |
| Tests | `uv run pytest -q` → 189 passed. Commit `8d0f42b` berührt keinen Code (nur zwei neue Seiten, `index.md`, Vokabular). |

**Eine gemessene Nebenbeobachtung zum Mermaid-Block.** Der `:caption:` steht in
einer Backtick-Fence und liegt damit außerhalb des Vale-Tors — die einzige Prosa
auf beiden Seiten, für die das gilt. Ich habe die Alternative gemessen:
`:::{mermaid}` baut sauber unter `-W` und rendert ein **byte-identisches**
`<figure>`, zieht aber den Diagrammtext mit in das Tor, und der fällt dann über
die Knotennamen:

```
30:5   error  Did you really mean 'payload_hash'?  Vale.Spelling
31:5   error  Did you really mean 'units_hash'?    Vale.Spelling
31:20  error  Did you really mean 'event_hash'?    Vale.Spelling
```

Einen Satz Bildunterschrift mit drei Vokabulareinträgen zu bezahlen, die dann
baumweit in ihrer Schreibweise festgenagelt sind (siehe unten), ist der falsche
Tausch. Die Backtick-Fence bleibt richtig. Der Satz hält Vale übrigens ohnehin
stand, einzeln geprüft: 0 Fehler.

---

## 4. Das Vokabular: keine weiteren Paare, aber die Diagnose greift weiter

**Keine weiteren Paare.** `accept.txt` trägt heute elf Einträge, jeder Begriff in
genau einer Schreibweise: `SQLAlchemy`, `canonicalized`, `subcommand`,
`subcommands`, `nullable`, `uv`, `toolchain`, `idempotency`, `canonicalization`,
`canonicalize`, `canonicalizer`.

**Aber die Ursache ist nicht das Paar.** Gemessen, mit genau einer Schreibweise
je Eintrag im Vokabular:

```
Nullable          ->  error  Use 'nullable' instead of 'Nullable'.
Canonicalization  ->  error  Use 'canonicalization' instead of 'Canonicalization'.
Uv                ->  error  Use 'uv' instead of 'Uv'.
Subcommands       ->  error  Use 'subcommands' instead of 'Subcommands'.
Idempotency       ->  error  Use 'idempotency' instead of 'Idempotency'.
SQLALCHEMY        ->  error  Use 'SQLAlchemy' instead of 'SQLALCHEMY'.
sqlalchemy        ->  error  Use 'SQLAlchemy' instead of 'sqlalchemy'.
Canonicalized     ->  error  Use 'canonicalized' instead of 'Canonicalized'.
Toolchain         ->  error  Use 'toolchain' instead of 'Toolchain'.
Canonicalize      ->  error  Use 'canonicalize' instead of 'Canonicalize'.
```

10 Fehler, 1 Datei. `Vale.Terms` nagelt **jeden** Eintrag auf seine eingetragene
Schreibweise, unabhängig davon, ob eine zweite im Vokabular steht. Neun der elf
Einträge sind klein geschrieben — **diese neun Wörter können in diesem Baum
keinen Satz und keine Überschrift beginnen.** Der Zwang kommt also nicht vom
Paar, sondern vom Eintrag; das Paar hat ihn nur in die unerwartete Richtung
gedreht.

**Beißt heute nichts** — das Tor ist grün, 0 Fehler in 15 Dateien. Und
`canonicalization.md` entgeht ihm nur, weil ihre H1 „About canonicalization"
heißt und nicht „Canonicalization": mit der naheliegenden Überschrift wäre es
sofort ein Fehler gewesen. Der Korrektur-Commit `8c01fc6` ist richtig; der
Grund darin ist zu eng formuliert.

Billige Abhilfe, falls es einmal beißt: die Stelle umformulieren oder
`Vale.Terms` eng begrenzt abschalten — **nicht** die Großform nachtragen, das
dreht den Zwang nur um.

---

## Nicht Gegenstand, wie im Auftrag

Aufgabe 6 (Nebenläufigkeit, Modulgrenzen, Backups). Die zwei Prosasätze in den
How-tos ohne `{ref}` (`docs/how-to/verify-the-chain.md`, für Aufgabe 7
vermerkt — das Label existiert jetzt). Die deutschen Specs selbst.
