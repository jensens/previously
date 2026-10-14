## Was der Plan am Spec entscheidet

1. **Unterarten der Feststellung, nicht eine neue Event-Art.** `entity` und `relation` sind Werte von `payload["assertion"]` unter `kind = "assertion"` (CF §12). Damit findet die Kaskade sie über `sources` ohne neuen Code (CF §6), und sie stehen in derselben Lesung `read_by_kind(conn, "assertion")`. Die Faltung der Verpflichtungen (`core/assertion.fold`) überspringt sie schon heute still (CF §1); `verify` muss sie vor `assertion_problem` an das Graph-Modell geben, sonst meldet es sie als Formfehler (CF §12).
2. **Die dritte Stufe nur im Graphen.** `transitive` gibt es für `entity` und `relation`; Verpflichtungen und Entscheidungen bleiben bei `direct` und `open` (Z §7.6 Punkt 2). Die fest verdrahteten zwei Stufen in `assertion.py`, `assertions.py`, CLI und `read.py` (CF §12) bleiben unberührt.
3. **Die Nutzlast einer Entität**, vertraglich (Schlüssel nach `canonical.KEY_PATTERN`, keine Floats, Daten `YYYY-MM-DD`):
   ```
   assertion       "entity"
   author          "human:operator" | "model:<client>"
   responsibility  "direct" | "transitive" | "open"
   evidence        "sources" | "recollection"
   sources         [{"event": int, "units": [int, ...] | null}, ...]   leer genau bei "recollection"
   reason          str | null
   handle          str | null
   subject         int | null      Kennung (Event der ersten Fassung); null bei der ersten
   approves        int | null      die freigegebene offene oder transitive Fassung
   under           int | null      das Event der Freigabeklasse; gesetzt genau bei "transitive"
   confidence      int | null      0..100, die Sicherheit, die ein Modell angibt; null beim Betreiber
   contests        int | null      die direkte Fassung, der ein Einwand widerspricht
   type            str             die deklarierte Art (Bezeichner, Planentscheidung 6)
   language        str | null      Arbeitssprache, Tag nach Planentscheidung 11
   fields          {name: value}   value: str | "YYYY-MM-DD" | {"from": date|null, "to": date|null} | int (Kennung einer Entität)
   state           "active" | "closed" | "retracted"     "closed" nur bei Verhalten closable
   ```
4. **Die Nutzlast einer Beziehung**, vertraglich, mit denselben gemeinsamen Schlüsseln (`assertion` bis `contests`, `type`) und:
   ```
   from      {"entity": int}
   to        {"entity": int} | {"candidates": [int, ...]}     2 bis 5 verschiedene; eine Rückfrage
   period    {"from": date | null, "to": date | null} | null   nur bei Verhalten period
   fields    {name: value}
   state     "standing" | "retracted"
   ```
   Ein Event als Ausgangspunkt (`{"event": …, "units": …}`) kommt mit Phase 2; die Form ist dafür offen, der Schreibweg weist es in Phase 1 ab („an event as the start of a relation comes with assignments"). Beenden ist eine neue Fassung mit `period.to`; Widerrufen der Zustand `retracted` (Z §6.3).
5. **Rückfragen und Einwände ohne neue Unterart.** Eine **Rückfrage** ist eine offene Beziehung mit `to.candidates`; ihre **Antwort** ist eine direkte Fassung derselben Kennung mit `to.entity`, einer der Kandidaten — sie macht die Rückfrage unanhängig, wie jede direkte Fassung jüngere offene überholt (F §3.2). Ein **Einwand** ist eine offene Fassung mit `contests`; er entsteht, wenn ein Modell auf eine Kennung schreibt, deren Gewinner direkt ist, und wird angenommen wie ein Vorschlag (Freigabe) oder abgelehnt (Ablehnung). **Abgelehnt** wird mit der vorhandenen Unterart `rejection` (F §3.4): ihr `of` darf künftig auch eine offene oder transitive Fassung einer Entität oder Beziehung nennen; `core/assertion.fold` ignoriert ein fremdes `of` schon heute (CF §1), der Schreibweg und `verify` lernen es.
6. **Bezeichner einer Art:** `[a-z][a-z0-9_]{0,39}`. **Eingebaut** sind `circle` (Entität), `member_of` und `in_circle` (Beziehungen): ihre Verbindungen und ihr Verhalten stehen im Code, eine Deklaration darf nur ihre Beschriftungen setzen (Z §4.5). Keine Klasse erreicht sie, und ein Modell schreibt sie nie anders als `open` (Z §7.6 Punkt 1).
7. **Die Handlung `vocabulary`** (nicht „declaration": das Wort steht schon für die Zusagen eines Anbieters, CF §12), vertraglich:
   ```
   action      "vocabulary"
   declares    "entity" | "relation"
   name        Bezeichner (Planentscheidung 6)
   labels      {sprache: text}      mindestens eine Sprache, Text 1..80 Zeichen ohne Steuerzeichen
   fields      [{"name": Bezeichner, "type": "text"|"date"|"period"|"choice"|"ref",
                 "values": [str, ...] | null,   genau bei choice, 1..50 verschiedene
                 "ref": Bezeichner | null,      genau bei ref: eine Art von Entität
                 "required": bool}, ...]
   behaviors   Entität: Teilmenge von ["closable", "period"]; Beziehung: von ["transitive", "acyclic", "period"]
   from, to    [Bezeichner, ...] bei einer Beziehung (Arten von Entitäten), sonst null
   retired     bool
   statement   str                  ein Satz, was deklariert wird
   ```
   Je `(declares, name)` ersetzt das jüngere Event das ältere; `read_vocabulary(log, conn, *, at=None)` faltet wie `read_policy` (CF §3). Ein Feld `name` ist bei jeder Art von Entität Pflicht und Text; ein Feld mit Verhalten `period` heißt `period`. `KNOWN_ACTIONS` bekommt `vocabulary` und `approval_class`; die vier Tests und zwei Seiten, die die Menge festhalten (CF §3 „What it takes"), folgen.
8. **Die Vokabulardatei** ist TOML, gelesen mit `tomllib`; geschrieben von einem eigenen, kleinen Ausgeber für genau diese Form (keine Abhängigkeit). Je Art eine Tabelle `[entity.<name>]` oder `[relation.<name>]` mit `labels`, `fields`, `behaviors`, `from`, `to`; ein unbekannter Schlüssel ist ein Fehler, nicht still übergangen. `apply` vergleicht mit dem geltenden Vokabular, zeigt jeden Unterschied, fragt (`--yes` wie bei `policy`) und schreibt je geänderter Art ein Event; eine Art, die in der Datei fehlt, wird stillgelegt. `show` gibt das Geltende als Datei aus; `show` nach `apply` derselben Datei ergibt dieselbe Datei. Das **Grundvokabular** (Z §5) liegt als `src/previously/vocabulary.toml` im Paket und kommt mit `apply --base` (oder einer Datei). Es muss im Wheel stehen; `tests/test_wheel.py` hält das fest.
9. **Die Handlung `approval_class`**, vertraglich:
   ```
   action      "approval_class"
   name        Bezeichner
   author      "model:<client>"
   assertion   "entity" | "relation"
   types       [Bezeichner, ...]    nicht leer; nie circle, member_of, in_circle
   threshold   int 0..100
   valid       {"from": iso-datetime | null, "until": iso-datetime | null} | null
   revoked     bool
   demote      bool                 nur mit revoked: alles darunter fällt auf open
   statement   str
   ```
   Je `name` ersetzt das jüngere Event das ältere. **Die Stufe bestimmt der Schreibweg, nie der Client:** der Client gibt `confidence`; ein Modell schreibt `transitive` mit `under`, wenn eine Klasse in Kraft ist (nicht zurückgezogen, `valid` umfasst `recorded_at`), die Autor, Unterart und Art deckt und deren Schwelle `confidence` erreicht — sonst `open`. Gegen eine Kennung mit direktem Gewinner schreibt ein Modell immer `open` mit `contests` (Z §7.4).
10. **Faltung mit Klassen.** `fold_graph(rows, classes)` ist rein. Gewinner einer Kennung: die jüngste `direct`, sonst die jüngste `transitive`, deren Klasse nicht mit `demote` zurückgezogen ist, sonst die jüngste offene ohne Ablehnung und Freigabe; `retracted` gewinnt wie jede Fassung und nimmt die Kennung aus dem geltenden Graphen. Eine transitive Fassung unter einer zurückgezogenen Klasse ohne `demote` bleibt und ist markiert (`class_revoked`); mit `demote` zählt sie als offen (Z §7.2).
11. **Sprachen:** ein Tag `[a-z]{2,3}(-[A-Za-z0-9]{1,8})*`. Gezeigt wird die Arbeitssprache der Entität, sonst `PREVIOUSLY_LANGUAGE` (Voreinstellung `en`), sonst die erste vorhandene Beschriftung in alphabetischer Ordnung der Sprache, dann markiert als `(<tag>)`.
12. **Erinnerung und Policy.** Eine Feststellung mit `evidence: "recollection"` hat keine Quellen; nur `human:operator` schreibt sie, direkt (Z §6.2). Über MCP entscheidet die Policy über sie wie über eine Quelle `recollection` ohne Identitäten (`decide(..., source="recollection")`): sie ist zurückgehalten, bis der Betreiber eine Regel `source:recollection` setzt. Fail-safe, und der Weg ist der vorhandene. Eine Beziehung ist für einen Client sichtbar, wenn ihre eigenen Quellen **und** beide Enden es sind; sonst ein Platzhalter.
13. **Zyklen ohne eigene Sperre.** Der Schreibweg faltet unter dem Tip und hängt an `tip + 1`; ein gleichzeitiger Schreibvorgang verliert die Kettenposition und versucht es neu, mit frischer Faltung (CF §2, `retrying`). Die Prüfung auf Zyklen bei `acyclic` ist damit gegen Wettläufe sicher; ein Test mit zwei Verbindungen hält es fest.
14. **Keine Projektionstabelle, keine Migration** (Z §10.1). Gelesen wird durch Falten aller Feststellungen und der Handlungen `vocabulary` und `approval_class`. **Die Endprüfung misst** die Liste der Entitäten und eine Abfrage zum Stichtag bei 10 000 und bei 100 000 Beziehungen (Z §3.4); was sie misst, entscheidet, ob Phase 2 eine Projektion bekommt.
15. **Das Zugriffsprotokoll** eines schreibenden Aufrufs trägt wie bisher keinen Text: Zahl der Aussagen, Quell-IDs, Enden-IDs, `confirm` ja/nein, geschriebene IDs (`write_record`, CF §8).

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten, Handoff **englisch**; Spec, Plan, Landkarte deutsch.
- Die sechs Tore, jedes für sich, vor jeder Fertigmeldung:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `uv run pip-audit --skip-editable` ohne Befund vor dem PR.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung; `cast` statt Zwischenannotation; kein privater Name aus einem Test.
- Kein Mock für Zeit, Datenbank oder Zufall; `recorded_at`, `now`, `today` werden übergeben; eine Stichprobe nimmt `random.SystemRandom`. Gegen echtes PostgreSQL (`db`-Fixture, `PostgresStorage(db)`).
- `core` importiert kein SQL und kein SDK; **keine neue Methode in `contract/store.py`** (das Lesen reicht: `read_by_kind`, `actions`, `events_by_id`, `units_by_event`, `source_keys`). Kein Vertrag in `.importlinter` wird erweitert.
- **Keine Deklaration, keine Klasse erreicht das Gate:** `core/decide.py` bleibt in Phase 1 unberührt, und kein neuer Code ruft es mit etwas aus dem Graphen auf außer der Sichtbarkeit nach Planentscheidung 12.
- **Kein Text einer Aussage und keine Adresse** in `mcp_access`, in einer Fehlermeldung, in einem Platzhalter.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener Zusicherung, mit einer grünen Kontrolle.
- Ein Kommentar ist eine Behauptung. **Bewegt sich in Phase 1:** die `T201`-Zahl in `pyproject.toml` (76, zweimal, CF §7) mit jedem neuen `print` in `cli.py` — nachmessen mit `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py --statistics`, die Erzählung um einen Eintrag ergänzen; die Zählungen im Docstring von `contract/store.py` (15/12/16/7, CF §5), falls `core` einen weiteren `LogStore`-Aufruf nutzt; „ten tools" auf `mcp-tools.md:5`; „six kinds" der Policy bleibt.
- Der Testblock des Tutorials wird aus **einem** grünen Lauf genau des Kommandos getippt, das die Seite zeigt (`uv run pytest`), zuletzt.
- Commits: Dateien namentlich, Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>` (oder das Modell des Umsetzers), nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Hilfe | `vocabulary` — `show or apply the vocabulary of entities and relations`; `entity` — `state an entity, or show one`; `relate` — `state a relation between two entities`; `entities` — `list the entities`; `relations` — `list the relations`; `classes` — `allow a model to stand for a class of statements`; `triage` — `list what waits for an answer`; `answer` — `answer a question with one of its candidates`; `status` — `show what waits` |
  | Kommandozeile, nach dem Schreiben | `assertion <id>` je geschriebener Aussage; `vocabulary event <id>`; `approval class event <id>` |
  | Werkzeugnamen | `list_entities`, `write_entity`, `write_relation`, `list_triage`, `write_triage_answer` |
  | Kopf eines MCP-Ergebnisses | ` · N objections pending` (` · 1 objection pending`) hinter dem Titel, nur bei N > 0 |
  | Platzhalter | wie heute: `[withheld: previously://event/<id> — <reason>]`, `[erased: previously://event/<id>]` |
  | Variable | `PREVIOUSLY_LANGUAGE` |

## Review Focus

1. **Das Vokabular ändert sich zwischen Vorschau und Bestätigung** von `write_entity`: der Schreibweg prüft unter dem Tip neu und weist mit einem Satz ab; nichts wird gegen ein Vokabular geschrieben, das nicht mehr gilt. → Aufgaben 4 und 6.
2. **Eine Klasse wird zwischen Vorschau und Bestätigung zurückgezogen oder eingerichtet:** die Stufe der Bestätigung ist die unter dem Tip; weicht sie von der Vorschau ab, wird abgewiesen („the approval class changed since the preview; call again without confirm"), nicht still anders geschrieben. → Aufgaben 4 und 6.
3. **Ein Modell nennt als Ende eine Entität, die es nicht sehen darf, oder eine, die es nicht gibt:** derselbe Satz für beides, nichts geschrieben, nichts verraten. → Aufgabe 6.
4. **Eine neue Fassung einer Entität, deren Art stillgelegt ist:** erlaubt (schließen, widerrufen, umbenennen); eine neue Entität dieser Art abgewiesen. Ebenso eine Beziehung, deren Art stillgelegt ist. → Aufgaben 2 und 4.
5. **Ein Zyklus durch eine neue Fassung**, die die Enden einer bestehenden `part_of`-Kante ändert, nicht nur durch eine neue Kante; und eine Kante von einer Entität zu sich selbst. → Aufgabe 4.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/vocabulary.py` (neu) | 1 | Handlung `vocabulary`: Form, Faltung zur Zeit, eingebaute Arten, Datei lesen und ausgeben, Unterschiede |
| `src/previously/vocabulary.toml` (neu) | 1 | das Grundvokabular (Z §5) |
| `src/previously/core/action.py`, `core/verify.py` | 1, 3, 4 | `KNOWN_ACTIONS`, Formprüfung der Handlungen; der Zweig für Graph-Feststellungen |
| `src/previously/core/graph.py` (neu) | 2 | Form von Entität und Beziehung, drei Stufen, Faltung mit Klassen, Gewinner, anhängig, Einwände, Rückfragen, Prüfung gegen Vokabular, Zyklen, Unterschiede |
| `src/previously/core/classes.py` (neu) | 3 | Handlung `approval_class`: Form, Faltung, Stufe bestimmen, Trefferquote, Stichprobe |
| `src/previously/core/graph_write.py` (neu) | 4 | Schreibweg und Vorschau, Lesen und Falten aus dem Log, Sichtbarkeit nach der Policy |
| `src/previously/core/assertions.py` | 4 | `rejection` mit `of` auf eine Graph-Fassung |
| `src/previously/cli.py` | 1, 5 | `vocabulary`; `entity`, `relate`, `entities`, `relations`, `classes`, `triage`, `answer`, `status`; `approve`/`reject` für Graph-Fassungen |
| `src/previously/mcp_server/read.py`, `render.py`, `server.py` | 6 | die fünf Werkzeuge, Freigabe und Ablehnung für Graph-Fassungen, der Kopf, `INSTRUCTIONS` |
| `tests/test_vocabulary.py`, `test_graph.py`, `test_classes.py`, `test_graph_write.py` (neu); `test_action.py`, `test_verify.py`, `test_cascade.py`, `test_cli.py`, `test_mcp_server.py`, `test_render.py`, `test_docs_references.py`, `test_wheel.py` | 1–6 | Tests |
| Seiten, Handoff, Landkarte | 7 | Doku |

---

