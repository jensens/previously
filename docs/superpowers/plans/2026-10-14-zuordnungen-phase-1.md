# Zuordnungen, Phase 1: der Kern — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein generischer Kern für Ordnung über den Inhalt: Vokabular als Handlungen im Log, Entitäten und Beziehungen als Feststellungen mit drei Stufen der Verantwortung, Freigabeklassen mit Trefferquote, Einwände und Rückfragen — auf der Kommandozeile und über MCP, ohne dass sich am Gate etwas ändert.

**Architecture:** Zwei neue Unterarten der Feststellung, `entity` und `relation`, unter der vorhandenen Event-Art `assertion`; sie erben die Tilgungskaskade und die Lage im Log. Ein reines Modul `core/graph.py` kennt ihre Form, die drei Stufen und die Faltung zu einem Graphen; `core/vocabulary.py` die Deklarationen (Handlung `vocabulary`) und die Vokabulardatei; `core/classes.py` die Freigabeklassen (Handlung `approval_class`) und die Trefferquote. Ein Schreibweg in `core/graph_write.py` prüft unter dem Tip gegen Vokabular, Graph und Klassen. Gelesen wird durch Falten, ohne Projektionstabelle; die Endprüfung misst, ob das trägt.

**Tech Stack:** Python 3.14, SQLAlchemy Core, PostgreSQL 18, `mcp` 2.3, Hypothesis, `tomllib` aus der Standardbibliothek.

**Spec:** `docs/superpowers/specs/2026-10-14-zuordnungen.md` („Z"), vom Betreuer am 2026-10-14 durchgesehen („bin durch, der Rest passt"). Dieser Plan baut **nur Phase 1** (Z §1: §3–§7, dazu §10 soweit Phase 1, §13, §15 Punkte 1–8, §17 Punkt 1). Dazu der Spec der Feststellungen `2026-10-12-pilot-feststellungen.md` („F") und das MCP-Konzept `2026-10-10-mcp-schnittstelle.md` („K"). Die Fakten aus dem Code, gemessen am 2026-10-14 auf `4aeb187`: `.superpowers/sdd/2026-10-14-zuordnungen-phase-1/code-facts.md` (git-ignoriert; der Controller gibt sie den Aufträgen mit, „CF §n").

**Ausführung:** subagent-driven, vom Betreuer am 2026-10-14 so bestimmt („du kannst jetzt eigenständig den Plan erstellen und subagent-driven umsetzen und einen PR draus machen"). Gewogen nach `CLAUDE.md`: die Aufgaben hängen stark an den Schnittstellen von Aufgabe 2 — ein Controller hält sie und gibt sie in jeden Auftrag; die Fehler, die zählen, sehen aus wie gute Arbeit (eine Klasse, die doch eine Art des Gates erreicht; ein Einwand, der still ersetzt) — ein frischer Prüfer je Aufgabe lohnt. Zyklenbudget wie zuletzt: je Aufgabe höchstens **eine** Fixrunde und eine Nachprüfung (Sonnet); die Endprüfung eine Fixwelle und eine Nachprüfung. Umsetzer und Prüfer auf Opus für die Aufgaben 2, 4 und 6, sonst Sonnet; Prüfer schreiben ihren Bericht in eine Datei.

---

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

## Task 1: Vokabular — `core/vocabulary.py`, die Datei, `previously vocabulary`

**Files:** `src/previously/core/vocabulary.py` (neu), `src/previously/vocabulary.toml` (neu), `src/previously/core/action.py`, `src/previously/core/verify.py`, `src/previously/cli.py`, `tests/test_vocabulary.py` (neu), `tests/test_action.py`, `tests/test_access.py`, `tests/test_verify.py`, `tests/test_cli.py`, `tests/test_wheel.py`, `tests/test_docs_references.py`, `docs/reference/vocabulary.md` (neu), `docs/reference/cli.md`, `docs/reference/policy-and-model-calls.md` (Liste der Handlungen), `pyproject.toml` (T201).

**Interfaces — Consumes:** `write_action_at`, `retrying`, `KNOWN_ACTIONS` (CF §3); das Muster von `set_policy`/`read_policy`. **Produces:**
```python
VOCABULARY: Final = "vocabulary"                 # in core/action.py, in KNOWN_ACTIONS
ENTITY_KIND: Final = "entity"; RELATION_KIND: Final = "relation"
TEXT, DATE, PERIOD, CHOICE, REF: Final[str]      # die Feldtypen
CLOSABLE, PERIOD_BEHAVIOR, TRANSITIVE, ACYCLIC: Final[str]
BUILT_IN: Final[frozenset[tuple[str, str]]]      # {("entity","circle"), ("relation","member_of"), ("relation","in_circle")}
GATE_TYPES: Final[frozenset[str]]                 # {"circle", "member_of", "in_circle"}
@dataclass(frozen=True)
class FieldSpec: name: str; type: str; values: tuple[str, ...] | None; ref: str | None; required: bool
@dataclass(frozen=True)
class KindSpec:
    declares: str; name: str; labels: Mapping[str, str]; fields: tuple[FieldSpec, ...]
    behaviors: frozenset[str]; from_: tuple[str, ...] | None; to: tuple[str, ...] | None; retired: bool
@dataclass(frozen=True)
class Vocabulary:
    kinds: Mapping[tuple[str, str], KindSpec]; ids: Mapping[tuple[str, str], int]
    def kind(self, declares: str, name: str) -> KindSpec | None: ...
    def label(self, declares: str, name: str, language: str) -> tuple[str, str | None]: ...  # (Text, Ausweichsprache oder None), Planentscheidung 11
class VocabularyRefused(PreviouslyError): ...
def vocabulary_problem(payload: Mapping[str, object]) -> str | None: ...       # Formprüfung, wirft nie
def to_payload(spec: KindSpec, *, statement: str) -> dict[str, object]: ...
def read_vocabulary[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Vocabulary: ...
def parse_file(text: str) -> tuple[KindSpec, ...]: ...                         # VocabularyRefused mit Satz bei Fehler
def render_file(vocabulary: Vocabulary) -> str: ...
def differences(current: Vocabulary, wanted: Sequence[KindSpec]) -> tuple[KindSpec, ...]: ...  # zu schreiben, stillgelegt eingeschlossen
def apply_vocabulary[Conn](log: LogStore[Conn], specs: Sequence[KindSpec], *, recorded_at: datetime) -> tuple[int, ...]: ...
def base_vocabulary() -> str: ...                                              # importlib.resources
```
Die eingebauten Arten stehen in `read_vocabulary` immer drin, mit festen Verbindungen und festem Verhalten; ein Event zu ihnen setzt nur `labels`, jede andere Abweichung weist `apply_vocabulary` ab. Prüfungen beim Schreiben: Bezeichner, Beschriftungen, Feldtypen und ihre Bedingungen (Planentscheidung 7), `from`/`to` nennen deklarierte, nicht stillgelegte Arten von Entitäten (auch solche aus derselben Datei), `name` Pflichtfeld jeder Entität.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück (`to_payload` → `vocabulary_problem is None`); jeder Formfehler einzeln mit Satz (Bezeichner mit Großbuchstaben, leere Beschriftung, `choice` ohne `values`, `ref` auf eine Beziehung, `period`-Verhalten bei einer Entität ohne Feld `period`, unbekanntes Verhalten, unbekannter Schlüssel in der Datei); Faltung zur Zeit (`at` vor und nach einer Änderung, Z §15 Punkt 1 vorbereitet); die eingebauten Arten: Beschriftung änderbar, `from` oder Verhalten von `member_of` geändert → abgewiesen (Z §15 Punkt 2); `render_file(read_vocabulary(...))` nach `apply` derselben Datei ist dieselbe Datei, und ein zweites `apply` schreibt nichts (Z §15 Punkt 8); eine Art, die in der Datei fehlt, wird stillgelegt und bleibt lesbar; das Grundvokabular besteht die Form und steht im Wheel; `verify` meldet eine Handlung `vocabulary` mit kaputter Form; `previously vocabulary show [--at]`, `apply FILE|--base [--yes]` mit Unterschieden vor dem Fragen.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** eingebaute Art wird umdeklarierbar → rot; `apply` schreibt auch Unverändertes → rot; `verify` ohne Zweig → rot; Kontrolle grün.
- [ ] **Step 5:** `KNOWN_ACTIONS`-Tests und -Seiten (CF §3), Seite `docs/reference/vocabulary.md` (die Handlung, die Datei, das Grundvokabular), `cli.md` mit Zeile in der Tabelle der Exit-Codes, T201 nachmessen; sechs Tore, Commit.

---

## Task 2: Das Graph-Modell — `core/graph.py`

**Files:** `src/previously/core/graph.py` (neu), `tests/test_graph.py` (neu).

Rein: keine Datenbank, keine Uhr. Nimmt `Source`, `OPERATOR`, `MODEL_PREFIX`, `model_author`, `DIRECT`, `OPEN` aus `core/assertion.py` (CF §1); `Statement` wird nicht erweitert (CF §12: zehn Positionsfelder).

**Interfaces — Consumes:** Aufgabe 1 (`Vocabulary`, `KindSpec`, `GATE_TYPES`). **Produces:**
```python
ENTITY: Final = "entity"; RELATION: Final = "relation"; GRAPH_KINDS: Final = frozenset({ENTITY, RELATION})
TRANSITIVE: Final = "transitive"; LEVELS: Final = (DIRECT, TRANSITIVE, OPEN)
SOURCES: Final = "sources"; RECOLLECTION: Final = "recollection"
ACTIVE, CLOSED, RETRACTED, STANDING: Final[str]
@dataclass(frozen=True)
class Period: start: date | None; end: date | None
    def holds(self, day: date) -> bool: ...
type FieldValue = str | date | Period | int
@dataclass(frozen=True)
class EntityBody: type: str; language: str | None; fields: Mapping[str, FieldValue]; state: str
@dataclass(frozen=True)
class RelationBody: type: str; start: int; to: int | None; candidates: tuple[int, ...] | None
    period: Period | None; fields: Mapping[str, FieldValue]; state: str
@dataclass(frozen=True)
class Claim:                                    # nicht `Statement` (zweimal vergeben, CF §12)
    kind: str; author: str; responsibility: str; evidence: str; sources: tuple[Source, ...]
    reason: str | None; handle: str | None; subject: int | None; approves: int | None
    under: int | None; confidence: int | None; contests: int | None
    body: EntityBody | RelationBody
def claim_payload(claim: Claim) -> dict[str, object]: ...
def claim_problem(payload: Mapping[str, object]) -> str | None: ...      # Form allein, wirft nie (Planentscheidung 3, 4)
def parse_claim(payload: Mapping[str, object]) -> Claim | None: ...
def conformance_problem(claim: Claim, vocabulary: Vocabulary, *, new_thread: bool) -> str | None: ...
# Art deklariert; neue Kennung nicht bei stillgelegter Art (Review Focus 4); Felder nach Typ, Pflichtfelder;
# closed nur bei closable; period nur bei period; Enden-Arten nach from/to; GATE_TYPES nur direct oder open
@dataclass(frozen=True)
class ClassState: id: int; revoked: bool; demote: bool          # aus Aufgabe 3 befüllt; hier nur der Typ
@dataclass(frozen=True)
class GraphVersion: id: int; recorded_at: datetime; claim: Claim
@dataclass(frozen=True)
class GraphThread:
    subject: int; kind: str; versions: tuple[GraphVersion, ...]
    rejected: frozenset[int]; approved: frozenset[int]
    def winner(self, classes: Mapping[int, ClassState]) -> GraphVersion | None: ...  # Planentscheidung 10
    def pending(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]: ...
    def objections(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]: ...  # anhängige mit contests auf den direkten Gewinner
    def question(self, classes: Mapping[int, ClassState]) -> GraphVersion | None: ...   # anhängige Rückfrage
@dataclass(frozen=True)
class Graph:
    threads: Mapping[int, GraphThread]; classes: Mapping[int, ClassState]
    def entities(self) -> Mapping[int, GraphVersion]: ...     # Gewinner, nicht retracted
    def relations(self, *, at: date | None = None) -> Mapping[int, GraphVersion]: ...   # Gewinner, standing, Zeitraum hält am Tag
    def reaches(self, start: int, end: int, types: frozenset[str]) -> bool: ...   # über Gewinner, für Zyklen
def fold_graph(rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]],
               classes: Mapping[int, ClassState]) -> Graph: ...
# überspringt getilgte Zeilen, Zeilen ohne Graph-Unterart und mit Formfehler; nimmt rejection-Zeilen, deren of eine Graph-Fassung nennt
def claim_changes(before: Claim, after: Claim) -> tuple[tuple[str, str, str], ...]: ...
```
Freigabe: eine direkte Fassung mit `approves`, die Inhalt, Quellen und `author` ihrer offenen oder transitiven Fassung übernimmt (F §3.3); ein Modell schreibt `direct` nur als Freigabe (F-6, wie in Einheit 5); `transitive` verlangt `under` und `confidence` und einen Modell-Autor; `recollection` verlangt leere Quellen, `human:operator` und `direct`; `contests` nur bei `open` und Modell-Autor; `candidates` nur bei `open`.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück; jeder Formfehler einzeln mit Satz (Float in `confidence`, `confidence` 101, `transitive` ohne `under`, `recollection` mit Quellen, `recollection` von einem Modell, `contests` bei `direct`, `candidates` mit einem Kandidaten oder Doppel, `closed` bei einer Beziehung, Datum `2026-02-30`); `conformance_problem` für jede Regel einzeln, auch Review Focus 4; **Hypothesis** (Z §15 Punkt 3): für beliebige Folgen von Fassungen aller drei Stufen, Ablehnungen, Freigaben, Tilgungen und Klassen (zurückgezogen, mit und ohne `demote`) ist der Gewinner die jüngste direkte, sonst die jüngste geltende transitive, sonst die jüngste unbeantwortete offene — die Erwartung aus den Zeilen allein, nicht aus `fold_graph` (wie CF §9); eine transitive nie Gewinner über einer direkten (Z §15 Punkt 4); `objections` und `question`; `relations(at=…)` an den Grenzen eines Zeitraums und mit offenen Enden; `reaches` über eine Kette und mit einer Kante zu sich selbst.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** transitiv vor direkt → Hypothesis rot; `demote` übergangen → rot; ein Modell darf `recollection` → rot; `GATE_TYPES` transitiv erlaubt → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 3: Freigabeklassen — `core/classes.py`

**Files:** `src/previously/core/classes.py` (neu), `src/previously/core/action.py`, `src/previously/core/verify.py`, `tests/test_classes.py` (neu), die Tests und Seiten, die `KNOWN_ACTIONS` festhalten.

**Interfaces — Consumes:** Aufgaben 1, 2 (`ClassState`, `Graph`, `GATE_TYPES`). **Produces:**
```python
APPROVAL_CLASS: Final = "approval_class"          # in core/action.py, in KNOWN_ACTIONS
@dataclass(frozen=True)
class ApprovalClass:
    name: str; author: str; assertion: str; types: frozenset[str]; threshold: int
    valid_from: datetime | None; valid_until: datetime | None; revoked: bool; demote: bool
class ClassRefused(PreviouslyError): ...
def class_problem(payload: Mapping[str, object]) -> str | None: ...
def class_payload(item: ApprovalClass, *, statement: str) -> dict[str, object]: ...
@dataclass(frozen=True)
class Classes:
    by_name: Mapping[str, tuple[ApprovalClass, int]]          # (geltend, Event-Id)
    states: Mapping[int, ClassState]                          # jede Event-Id einer Klasse → ihr heutiger Stand
    def level(self, *, author: str, kind: str, type: str, confidence: int | None,
              recorded_at: datetime) -> tuple[str, int | None]: ...   # (TRANSITIVE, id) oder (OPEN, None); GATE_TYPES nie
def read_classes[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Classes: ...
def set_class[Conn](log: LogStore[Conn], item: ApprovalClass, *, statement: str, recorded_at: datetime) -> int: ...
@dataclass(frozen=True)
class HitRate: class_id: int; name: str; total: int; confirmed: int; corrected: int; standing: int
def hit_rates(graph: Graph, classes: Classes) -> tuple[HitRate, ...]: ...
# corrected: über der transitiven Fassung steht eine spätere direkte, die nicht ihre Freigabe ist, oder ein Widerruf des Betreibers
def sample(graph: Graph, class_id: int, count: int, rng: random.Random) -> tuple[GraphVersion, ...]: ...
```
`states` gibt jedem Event, das eine Klasse je gesetzt hat, den Stand ihres **jüngsten** Events: zieht der Betreiber sie zurück, sehen alle Fassungen darunter es (Z §7.2). `set_class` weist ab: Typen aus `GATE_TYPES` (Z §7.6 Punkt 1), Typen, die das Vokabular nicht kennt, `demote` ohne `revoked`.

- [ ] **Step 1: Tests, die scheitern:** Form hin und zurück, Formfehler einzeln; `level` über und unter der Schwelle, genau an ihr, außerhalb von `valid`, für einen anderen Autor, für eine andere Art, nach Rückzug (Z §15 Punkt 5); `GATE_TYPES` in einer Klasse → abgewiesen, und `level` gibt für sie nie `transitive`, auch wenn ein Event sie im Log nennt (von Hand geschrieben); `hit_rates` mit bestätigter, korrigierter, widerrufener, stehender Fassung; `sample` mit `SystemRandom` gibt `count` verschiedene Fassungen der Klasse oder alle, wenn weniger; `verify` meldet eine kaputte Handlung `approval_class`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `GATE_TYPES` nicht geprüft → rot; Schwelle mit `>` statt `>=` → rot; Rückzug wirkt nur auf das jüngste Event → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 4: Schreibweg, Lesen, Prüfung, Kaskade — `core/graph_write.py`

**Files:** `src/previously/core/graph_write.py` (neu), `src/previously/core/assertions.py`, `src/previously/core/verify.py`, `tests/test_graph_write.py` (neu), `tests/test_cascade.py`, `tests/test_verify.py`, `tests/test_assertions.py`.

**Interfaces — Consumes:** Aufgaben 1–3; `retrying`, `prepare`, `link`, `LogStore`, `RedactionStore.lock_event`, `read_policy`, `decide`, `Candidate`, `SourceEvents`/`read_source_events` (CF §2, §4, §5). **Produces:**
```python
class GraphRefused(PreviouslyError): ...            # ein Satz, kein Text, keine Adresse
@dataclass(frozen=True)
class Written: ids: tuple[int, ...]; levels: tuple[str, ...]
def check_claims[Conn](log: LogStore[Conn], conn: Conn, claims: Sequence[Claim], *, recorded_at: datetime) -> tuple[Claim, ...]: ...
# Vorschau: gibt die Aussagen mit der Stufe zurück, die der Schreibweg jetzt bestimmen würde (Planentscheidung 9)
def write_claims[Conn](log: LogStore[Conn], locker: RedactionStore[Conn], claims: Sequence[Claim],
                       *, recorded_at: datetime, expect_levels: Sequence[str] | None = None) -> Written: ...
# eine Transaktion (retrying): Quellen aufsteigend sperren; Tip; ist ein handle gesetzt und steht schon eine Aussage mit ihm, deren IDs zurück;
# Vokabular, Klassen und Graph unter dem Tip lesen; Quellen wie in Einheit 5; Stufe und contests bestimmen; mit expect_levels abweichend → GraphRefused (Review Focus 2);
# conformance_problem; Enden stehen und haben die richtige Art; Freigabe nach F §3.3; acyclic über reaches, mit den Aussagen desselben Stapels; anhängen
def read_graph[Conn](log: LogStore[Conn], conn: Conn, *, as_of: datetime | None = None) -> Graph: ...
def claim_verdict(policy: Policy, client: Client, identities: Sequence[Mapping[str, object]],
                  sources: Sequence[str | None], *, recollection: bool) -> Decision: ...   # Planentscheidung 12
def relation_visible(policy: Policy, client: Client, relation: GraphVersion, ends: Mapping[int, bool],
                     identities: Sequence[Mapping[str, object]], sources: Sequence[str | None]) -> bool: ...
# eigene Quellen nach claim_verdict und beide Enden sichtbar (ends: Kennung der Entität → sichtbar)
```
In `core/assertions.py` lernen `check_statements`/`write_statements`, dass das `of` einer `rejection` auch eine offene oder transitive Graph-Fassung nennen darf (Planentscheidung 5); die Ablehnung übernimmt ihre Quellen unverändert. Leer sind sie nie: abgelehnt wird nur eine offene oder transitive Fassung, und die schreibt nur ein Modell, immer mit Quellen (Planentscheidung 12). `verify`: ein Zweig vor `assertion_problem` für `GRAPH_KINDS` — Form, Verweise auf frühere Fassungen derselben Unterart, Konformität gegen das Vokabular **zur Zeit der Aussage** (es faltet `vocabulary` und `approval_class` beim Durchgang mit), Stufe passt zur Klasse zur Zeit, Enden stehen davor, `acyclic`; in `reconcile` getilgte Quellen wie bei Feststellungen. Die Kaskade braucht keinen neuen Code (Planentscheidung 1); ein Test hält es fest.

- [ ] **Step 1: Tests, die scheitern:** schreiben und lesen (Vellenfeld: Organisation, Ämter, Personen, `holds` mit Zeiträumen, `relations(at=2019-03-01)`); idempotent über `handle`; Stufe nach Klasse, `contests` gegen einen direkten Gewinner (Z §15 Punkt 4), ein Modell ohne Klasse → `open`; `recollection` vom Betreiber geht, von einem Modell nicht (Punkt 6); Vokabular geändert zwischen `check_claims` und `write_claims` → abgewiesen (Review Focus 1); `expect_levels` weicht ab → abgewiesen (Review Focus 2); stillgelegte Art (Review Focus 4); **Zyklus** durch neue Kante, durch neue Fassung einer Kante, zu sich selbst, innerhalb eines Stapels (Review Focus 5), und durch **zwei gleichzeitige** Schreibvorgänge über zwei Verbindungen, von denen jeder für sich erlaubt ist (Z §15 Punkt 7, Planentscheidung 13); Ablehnung einer Graph-Fassung schreiben und falten; Kaskade: Quelle getilgt → Aussage getilgt, `verify` grün, Gewinner fällt zurück; `verify` findet eine Graph-Aussage mit kaputter Form, gegen das Vokabular ihrer Zeit, mit einer Stufe ohne Klasse (von Hand über `chain.prepare` und `insert_event`); `claim_verdict` mit `recollection` ohne Regel zurückgehalten, mit `source:recollection` frei.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Zyklus nur gegen den gefalteten Graphen, nicht gegen den Stapel → rot; Vokabular zur Zeit der Vorschau statt unter dem Tip → rot; `verify` prüft gegen das heutige Vokabular statt das der Zeit → rot; die Stufe vom Client übernommen → rot; Kontrolle grün.
- [ ] **Step 5:** Kommentar in `assertions.py` zur Reihenfolge in der Transaktion (CF §12) und `docs/explanation/concurrency.md` nachziehen, falls sich die Reihenfolge ändert; sechs Tore, Commit.

---

## Task 5: Die Kommandozeile

**Files:** `src/previously/cli.py` (liest die Einstellungen wie `PREVIOUSLY_IMAP_FOLDER` aus der Umgebung; dort auch `PREVIOUSLY_LANGUAGE`), `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`, `pyproject.toml` (T201).

**Interfaces — Consumes:** Aufgaben 1–4. **Produces:** die Kommandos (Wortlaute oben):
- `previously entity TYPE --name … [--field NAME=VALUE]… [--language TAG] [--source …]… | --recollection [--subject N] [--state …] [--reason …] [--yes]`; `previously entity N [--history]` zeigt die Entität, ihre Beziehungen in beide Richtungen und anhängige Fassungen.
- `previously relate TYPE --from N --to N [--from-date D] [--to-date D] [--field …]… [--source …]… | --recollection [--subject N] [--retract] [--reason …] [--yes]`.
- `previously entities [--type T] [--state S] [--proposals]` und `previously relations [--type T] [--from N] [--to N] [--at YYYY-MM-DD] [--as-of ISO-DATETIME]`.
- `previously classes add NAME --author model:C --assertion entity|relation --type T… --threshold P [--from …] [--until …] --statement … [--yes]`; `classes revoke NAME [--demote] --statement … [--yes]`; `classes list` mit Trefferquote; `classes sample NAME [--count K]`.
- `previously triage`: Einwände zuerst, dann Rückfragen, dann Vorschläge; `previously answer N --choose ID [--reason …] [--yes]`; `previously status`: je eine Zeile `objections`, `questions`, `proposals`, mit Zahl.
- `previously approve` und `reject` nehmen auch Graph-Fassungen (Planentscheidung 5).
Ausgabe wie bei den Feststellungen: Vorschau als JSON auf stdout, Hinweise auf stderr, `Error:` mit Exit 2, „nothing written" mit Exit 1 (CF §7). Beschriftungen nach Planentscheidung 11.

- [ ] **Step 1: Tests, die scheitern:** je Kommando die Ausgabe und die Exit-Codes; die Vellenfeld-Folge auf der Kommandozeile (Z §17 Punkt 1: Verein, Gründung, Obmann, Schriftführer, Kassier, Vorstände mit Zeiträumen, „wer war am 1. März 2019 im Vorstand?" über `relations --type member_of --to N --at 2019-03-01`); ein geändertes Vokabular deutet nichts Früheres um (`entity N --history` zeigt die alte Fassung unverändert, markiert, was nicht mehr passt); `--as-of` zeigt den Stand eines früheren Zeitpunkts; Beschriftung in der Arbeitssprache, mit Ausweichsprache markiert; `classes list` mit Trefferquote nach einer Korrektur; `triage` in der Reihenfolge; `--help` hält `COMMANDS`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `triage` ohne Einwände zuerst → rot; `--at` übergangen → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md` (je Kommando ein Abschnitt, Exit-Codes), `configuration.md` (`PREVIOUSLY_LANGUAGE`), T201 nachmessen und die Erzählung in `pyproject.toml` ergänzen; sechs Tore, Commit.

---

## Task 6: MCP — Lesen, Schreiben, Rückfragen, der Kopf

**Files:** `src/previously/mcp_server/read.py`, `render.py`, `server.py`, `tests/test_mcp_server.py`, `tests/test_render.py`, `tests/test_docs_references.py`, `docs/reference/mcp-tools.md`.

**Interfaces — Consumes:** Aufgaben 1–4; `Service.answer`, `staged`, `seal`/`open_handle`, `write_record`, `render_page`, `Stated`, `_ASK_THE_PERSON` (CF §8). **Produces:**
- `list_entities(type?, state?, proposals?, subject?, history?, cursor?)`: Entitäten mit ihren Beziehungen, unter der Policy (Planentscheidung 12), seitenweise wie `list_obligations`.
- `write_entity(items, confirm?)` und `write_relation(items, confirm?)`: zwei Schritte wie `write_assertion`; jedes Element trägt `confidence` (0..100); die Vorschau zeigt die Stufe, die der Schreibweg bestimmen würde; die Bestätigung gibt sie als `expect_levels` (Review Focus 2). Ein Ende, das der Client nicht sehen darf oder das es nicht gibt: ein Satz für beides (Review Focus 3).
- `list_triage(cursor?)`: Einwände zuerst, dann Rückfragen, dann Vorschläge, unter der Policy.
- `write_triage_answer(question, choice, reason?)`: ein Aufruf, `meta=_ASK_THE_PERSON`, schreibt die Antwort im Namen des Betreibers — wie `write_approve` direkt mit dem Autor der Rückfrage.
- `write_approve` und `write_reject` nehmen auch Graph-Fassungen.
- **Der Kopf** jedes Ergebnisses (`render_page` und `render_text`) bekommt ` · N objections pending` hinter dem Titel, gezählt über die Einwände, die der Client sehen darf (Z §7.5).
- `INSTRUCTIONS` sagt, was Entitäten und Beziehungen sind, dass das Modell `confidence` ehrlich angibt und der Server die Stufe bestimmt, dass ein Widerspruch gegen eine direkte Aussage ein Einwand wird und nie ersetzt, dass eine unklare Zuordnung eine Rückfrage mit Kandidaten wird und nicht geraten.

- [ ] **Step 1: Tests, die scheitern:** je Werkzeug in beiden Generationen (`MODES`); Vorschau und Bestätigung; ein Vorschlag des Clients, den der Betreuer über `write_approve` freigibt (Z §17 Punkt 1); `expect_levels` (Review Focus 2); verborgenes und fehlendes Ende mit demselben Satz (Review Focus 3); `recollection` ohne `source:recollection` als Platzhalter; der Kopf mit null, einem und zwei Einwänden, und ohne Einwände, die der Client nicht sehen darf; `write_triage_answer` mit einem Kandidaten und mit einer Kennung, die keiner ist; `mcp_access` ohne Text (Planentscheidung 15); die Prüfsumme der Werkzeugliste und die Namensliste neu (`TOOLS_SHA256`, CF §8), `INSTRUCTIONS` ganz auf `mcp-tools.md`, jedes neue Werkzeug mit Abschnitt und Tabelle seiner Parameter.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Stufe vom Client übernommen → rot; Kopf zählt verborgene Einwände → rot; Ende verborgen mit anderem Satz → rot; Kontrolle grün.
- [ ] **Step 5:** `mcp-tools.md` (Werkzeuge, Kopf, „fifteen tools"), sechs Tore, Commit.

---

## Task 7: Doku, Handoff, Landkarte

**Files:** `docs/explanation/graph.md` (neu; Bezeichner der Seite nach dem Umsetzer, Label `(graph)=`), `docs/how-to/keep-a-club-and-its-offices.md` (neu), `docs/how-to/let-a-model-stand-for-a-class.md` (neu), `docs/explanation/assertions.md` (Verweis auf die dritte Stufe), `docs/explanation/processing-policy.md` (Erinnerung als Quelle), `docs/reference/environment.md`, `docs/how-to/connect-claude-code-and-vibe.md` (neue Werkzeuge, Ask-Regel für `write_triage_answer`), `docs/how-to/record-what-is-owed-and-decided.md` (Ask-Regel), Indexseiten, `README.md` falls es Fähigkeiten aufzählt, `docs/superpowers/handoffs/2026-10-14-kup6s-graph-phase-1.md` (neu, englisch), `docs/superpowers/landkarte.md`, `NOTIZEN.md` nicht.

- [ ] Nach Z §16, soweit Phase 1:
  - **Explanation:** warum der Kern generisch ist und die Bedeutung deklariert, und wo die Linie gegen eine DSL liegt; warum ein Property Graph und kein Triple Store, und warum aus dem Log gefaltet; warum drei Stufen und warum ein Modell nie eine direkte Aussage ersetzt (Einwand); warum die Stufe der Server bestimmt; warum die Arten des Gates nie transitiv sind; warum Erinnerung zurückgehalten ist, bis eine Regel sie öffnet. Mit Verweisen auf Z, wo eine Entscheidung datiert ist (frozen design record — **hier noch nicht eingefroren**, also als Spec zitieren, nicht als frozen).
  - **How-to:** einen Verein mit seinen Ämtern über die Jahre festhalten (Vellenfeld, Z §17 Punkt 1); ein Vokabular anpassen; eine Freigabeklasse einrichten, ihre Trefferquote lesen, sie zurückziehen; Einwände und Rückfragen beantworten.
  - `environment.md`: in Phase 1 nichts Neues außer `apply` nach dem Update; die Ask-Regel für `write_triage_answer` als Forderung an den Client.
  - **Handoff** (englisch): `0.1.0a7` oder das nächste Release; keine Migration; `previously vocabulary apply --base` im Werkzeug-Pod nach dem Image; die Werkzeugliste wächst auf fünfzehn, Vibe frischt auf; `source:recollection` nur, wenn der Betreiber es will. Prüfungen: `vocabulary show` zeigt das Grundvokabular; `entities` antwortet; `list_entities` antwortet über MCP.
  - **Landkarte:** Phase 1 gebaut; die Messung der Endprüfung; Abnahme nach Z §17 Punkt 1 als nächster Schritt; zählen vorher und nachher.
  - Der Spec bleibt lebendig (Z, Status); kein Einfrieren in Phase 1.
- [ ] Sechs Tore, `pip-audit`, Testblock des Tutorials aus einem grünen Lauf, Commits.

---

## Nach Aufgabe 7

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung. Das Code-Paket **misst** `entities` und `relations --at` bei 10 000 und 100 000 Beziehungen (Planentscheidung 14, Z §3.4) und schreibt die Zahlen in die Landkarte und auf die Explanation-Seite.
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-14-zuordnungen-phase-1/`.
3. Push und PR. Danach, mit dem Betreuer: Merge, Release, Handoff, Abnahme nach Z §17 Punkt 1.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung, Phase 1:** Z §3.1 → 2; §3.2 → 1 (Verhalten), 2 (Wirkung); §3.3 → 2 (`Period`), 5 (`--as-of`); §3.4 → Planentscheidung 14, Endprüfung; §4.1–§4.4 → 1; §4.5 → 1, 2, 3; §4.6 → 1, 5 (Sprachen), 2 (Kennungen); §5 → 1; §6.1–§6.5 → 2, 4; §7.1–§7.3 → 2, 3, 4, 5, 6; §7.4 → 2, 4, 6; §7.5 → 5 (`triage`, `status`), 6 (Kopf); §7.6 → 2, 3 (Grenzen), 3 (Trefferquote, Stichprobe); §10.2–§10.3 soweit Phase 1 → 5, 6 (`in` kommt mit Phase 2); §10.4 → Global Constraints; §13 → 7; §15 Punkte 1–8 → 1–4; §16 → 7; §17 Punkt 1 → 5, 6, 7.
- **Nicht in Phase 1, bewusst:** ein Event als Ende (§8, Phase 2), `chronicle --in` und `in` über MCP (Phase 2), alles an Kreisen und Gate (§9, Phase 3), Verpflichtungen im Schema (§11, Phase 4).
- **Platzhalter:** keine; die genauen Sätze der Meldungen legen die Umsetzer fest, und `cli.md`/`mcp-tools.md` zitieren sie, gehalten von `test_docs_references`.
- **Namen:** `Vocabulary`, `KindSpec`, `FieldSpec`, `read_vocabulary`, `apply_vocabulary`, `GATE_TYPES`, `Claim`, `EntityBody`, `RelationBody`, `Period`, `GraphVersion`, `GraphThread`, `Graph`, `fold_graph`, `ClassState`, `ApprovalClass`, `Classes`, `read_classes`, `set_class`, `HitRate`, `hit_rates`, `sample`, `check_claims`, `write_claims`, `read_graph`, `claim_verdict`, `GraphRefused`, `Written` — überall gleich.
- **Bekannte Spannung:** Planentscheidung 12 hält Erinnerungen vor MCP-Clients zurück, bis der Betreiber `source:recollection` öffnet; das ist die sichere Seite, kostet aber in der Abnahme einen Handgriff. Der How-to sagt es.
