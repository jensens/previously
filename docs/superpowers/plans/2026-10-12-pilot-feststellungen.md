# Pilot, Einheit 5: Feststellungen — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verpflichtungen und Entscheidungen als Feststellungen im Log — mit Pflicht-Quellen über Events hinweg, getrennt nach Autor und Verantwortung, als vollständige Fassungen mit Vorrang, Vorschlägen, Freigabe und Ablehnung —, geschrieben auf der Kommandozeile und über MCP, gelesen unter der Policy, und bei jeder Tilgung einer Quelle mitgetilgt.

**Architecture:** Ein reines Modul `core/assertion.py` kennt die Form, die Verweise und die Faltung der Fassungen; ein Schreibweg in `core/assertions.py` hängt Feststellungen an, prüft sie unter dem Tip und sperrt ihre Quellen gegen eine gleichzeitige Tilgung; `core/redact.py` kaskadiert auf sie, `core/verify.py` kennt ihre Form. Gelesen wird durch Falten aus dem Log, ohne Projektionstabelle. Die Kommandozeile bekommt `assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions`, `decision`; der MCP-Server zwei lesende und drei schreibende Werkzeuge, die schreibenden mit einem versiegelten Handle in zwei Schritten.

**Tech Stack:** Python 3.14, SQLAlchemy Core, PostgreSQL 18, `mcp` 2.3, Hypothesis; `hmac`/`hashlib` aus der Standardbibliothek für das Handle.

**Spec:** `docs/superpowers/specs/2026-10-12-pilot-feststellungen.md` („F"), vom Betreuer am 2026-10-12 durchgesehen („ja"). Dazu das MCP-Konzept `2026-10-10-mcp-schnittstelle.md` („K") und der Spec des Lesezugangs `2026-10-10-pilot-mcp-lesezugang.md` („S"). Die Fakten aus dem Code, gemessen am 2026-10-12 auf `915e48a`: `.superpowers/sdd/2026-10-12-pilot-feststellungen/code-facts.md` (git-ignoriert; der Controller gibt sie den Aufträgen mit).

---

## Was der Plan am Spec entscheidet

1. **Keine Projektionstabellen, keine Migration** (F §9, §10 nannten `p_obligation`, `p_decision` und eine Migration `0006`). Gelesen wird durch Falten aller Feststellungen aus dem Log (`read_by_kind(conn, "assertion")`, in SQL nach Art gefiltert). Gründe, aus dem Code: der Rückfall auf die nächste stehende Fassung nach einer Tilgung (F §8) braucht ohnehin alle Fassungen; die Kreise hängen an der **heutigen** Policy (F §7) und lassen sich nicht speichern; der MCP-Server liest nur `LogStore` (code-facts §3). Leitsatz 3 bleibt gewahrt: der Zustand wird berechnet, nicht gehalten. **Die Endprüfung misst** die Zeit einer Liste bei 5 000 Feststellungen; erst wenn sie trägt, kommt eine Projektion (Landkarte). Der Betreuer entscheidet das mit der Durchsicht dieses Plans.
2. **Die Nutzlast**, vertraglich (Schlüssel nach `canonical.KEY_PATTERN`, keine Floats, Daten als Zeichenkette `YYYY-MM-DD`):
   ```
   assertion       "obligation" | "decision" | "rejection"
   author          "human:operator" | "model:<client>"
   responsibility  "direct" | "open"
   sources         [{"event": int, "units": [int, ...] | null}, ...]   nicht leer; units aufsteigend, ohne Doppel
   reason          str | null
   handle          str | null      die Kennung des MCP-Handles (§5), sonst null
   # obligation und decision:
   subject         int | null      Kennung (Event der ersten Fassung); null bei der ersten Fassung
   approves        int | null      der freigegebene Vorschlag
   # obligation:
   debtor, creditor  Verweis;  what  str;  due  "YYYY-MM-DD" | null;  state  "open" | "fulfilled" | "cancelled"
   # decision:
   what  str;  by  [Verweis, ...] nicht leer;  on  "YYYY-MM-DD";  state  "valid" | "revoked";  replaces  int | null
   # rejection:
   of              int             der abgelehnte Vorschlag
   ```
   Feststellungen haben **keine Einheiten**; der Text steht in der Nutzlast. Eine Tilgung nimmt die Nutzlast.
3. **Verweise** (F §2.1): `own` | `circle:<name>` (Name nach der Grammatik der Policy-Namen) | `address:<adresse>` (genau ein `@`, kein Leerraum, höchstens 254 Zeichen) | `name:<text>` (1 bis 200 Zeichen, keine Steuerzeichen). Alles andere ist ein Formfehler.
4. **Verweise auf andere Feststellungen** (`subject`, `approves`, `of`, `replaces`) und Quellen zeigen **auf frühere Events**; anders kann es beim Schreiben nicht sein, und `verify` prüft es so.
5. **Freigabe:** `approves` zeigt auf eine offene Fassung derselben Kennung, die weder freigegeben noch abgelehnt noch getilgt ist; die Freigabe übernimmt deren Inhalt, Quellen und `author`, mit `responsibility: direct`. Ein zweites Freigeben oder ein Freigeben nach Ablehnung wird abgewiesen. **Ablehnung** übernimmt die Quellen des Vorschlags (F §3.4).
6. **„Überfällig"** heißt `state == "open"` und `due` vor dem Datum von `today`, das der Aufrufer übergibt (die Kommandozeile und der Server nehmen das UTC-Datum von `now`); kein Mock der Zeit.
7. **Policy einer Feststellung** (F §7): die Identitäten aller Quell-Events zusammen; `decide` läuft je verschiedener Quelle der Quell-Events einmal mit diesen Identitäten, und die Feststellung wird zurückgehalten, sobald eine Entscheidung nichts wählt — die strengste Regel gilt.
8. **Der Schreibweg sperrt die Quellen** in aufsteigender Reihenfolge (`lock_event`, wie `append_call` in Einheit 3) und weist eine getilgte Quelle ab; so kann eine Tilgung nicht zwischen Prüfung und Schreiben fallen (die andere Seite der Kaskade, code-facts §4).
9. **Das Handle** (F §6.1, K §4.3): `base64url(kanonisches JSON {client, digest, expires, nonce}) + "." + base64url(HMAC-SHA256)`; `digest` ist der SHA-256 der kanonischen Liste der zu schreibenden Nutzlasten ohne `handle`; Ablauf zehn Minuten. Die Kennung im Log ist der `nonce`. Schlüssel: `PREVIOUSLY_MCP_CONFIRM_KEY`, mindestens 32 Zeichen; fehlt er, antworten die schreibenden Werkzeuge mit einem Fehler, die lesenden arbeiten.
10. **Das Zugriffsprotokoll eines schreibenden Aufrufs** trägt **keinen Text**: als `arguments` nur die Zahl der Feststellungen, die Quell-IDs, `confirm` ja/nein und die geschriebenen IDs. Sonst stünde der aus einer Mail abgeleitete Text im `mcp_access` und überlebte die Tilgung der Mail.

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
- `uv run pip-audit --skip-editable` ohne Befund zur Abnahme.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung; `cast` statt Zwischenannotation; kein privater Name aus einem Test.
- Kein Mock für Zeit, Datenbank oder Zufall; `recorded_at`, `now`, `today` werden übergeben. Gegen echtes PostgreSQL (`db`-Fixture, `PostgresStorage(db)`).
- `core` importiert kein SQL und kein SDK (`.importlinter`); neue Abfragen nur hinter `contract.store`. Kein Vertrag wird erweitert; neue Kanten werden namentlich eingetragen.
- **Kein Text einer Feststellung und keine Adresse** in `mcp_access`, in einer Fehlermeldung, in einem Platzhalter.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener Zusicherung, mit einer grünen Kontrolle.
- Ein Kommentar ist eine Behauptung; Zahlen darin gemessen. **Bekannt falsch vor Beginn:** der Kommentar zu `T201` in `pyproject.toml` sagt vierundsechzig, `ruff` misst 66 (code-facts §9); wer `print` in `cli.py` ändert, misst neu und schreibt die gemessene Zahl. Ebenso die gezählte Methodenliste im Docstring von `contract/store.py`.
- Der Testblock des Tutorials wird aus **einem** Lauf genau des Kommandos getippt, das die Seite zeigt (`uv run pytest`), zuletzt.
- Commits: Dateien namentlich, Trailer `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Hilfe | `assert` — `state an obligation or a decision`; `approve` — `make proposals your own`; `reject` — `reject a proposal`; `obligations` — `list what is owed`; `obligation` — `show one obligation`; `decisions` — `list what was decided`; `decision` — `show one decision` |
  | Kommandozeile, nach dem Schreiben | `assertion <id>` je geschriebener Feststellung |
  | Abgelehnt vor dem Fragen | `Error: ` und ein Satz, was fehlt |
  | Werkzeugnamen | `list_obligations`, `list_decisions`, `write_assertion`, `write_approve`, `write_reject` |
  | Platzhalter | wie S: `[withheld: previously://event/<id> — <reason>]`, `[erased: previously://event/<id>]` |
  | Variable | `PREVIOUSLY_MCP_CONFIRM_KEY` |

## Review Focus

1. **Die gewinnende direkte Fassung wird getilgt, ein Vorschlag steht noch:** der Eintrag fällt auf die nächste **direkte** Fassung zurück; gibt es keine, erscheint der Vorschlag **als Vorschlag**, nie als direkt. → Aufgabe 1 (Faltung), Aufgabe 2 (mit echter Tilgung).
2. **Freigeben, was schon freigegeben, abgelehnt oder getilgt ist** — und ein Freigeben über MCP durch einen Client, der die Quellen nicht sehen darf: abgewiesen mit einem Satz, nichts geschrieben. → Aufgaben 2 und 5.
3. **Eine Tilgung von Einheiten, die die Feststellung nicht nennt**, lässt sie stehen; eine, die eine genannte Einheit oder das ganze Event trifft, nimmt sie mit. → Aufgabe 2.
4. **Ein Handle wird nach Ablauf, von einem anderen Client oder mit geändertem Inhalt eingelöst:** abgewiesen; ein zweites Einlösen mit demselben Handle schreibt nichts und liefert dieselben IDs. → Aufgabe 5.
5. **Ein Datum, das keins ist** (`2026-02-30`, `30.11.2026`, leer) für `due` oder `on`: abgewiesen vor dem Fragen; ein `due` in der Vergangenheit ist erlaubt und sofort überfällig. → Aufgaben 1 und 3.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/assertion.py` (neu) | 1 | Form, Verweise, Nutzlast bauen und prüfen, Faltung (Fassungen, Gewinner, anhängig, Geschichte, Unterschied) |
| `src/previously/core/assertions.py` (neu) | 2 | Schreibweg: unter dem Tip prüfen, Quellen sperren, idempotent anhängen; Lesen und Falten aus dem Log; Kreise und Filter |
| `src/previously/core/redact.py` | 2 | Kaskade auf Feststellungen |
| `src/previously/core/verify.py` | 2 | Form, Verweise, getilgte Quellen |
| `src/previously/cli.py` | 3 | die sieben Kommandos |
| `src/previously/mcp_server/render.py` | 4 | ein Element für eine gezeigte Feststellung |
| `src/previously/mcp_server/read.py`, `server.py` | 4, 5 | lesende und schreibende Werkzeuge |
| `src/previously/mcp_server/confirm.py` (neu) | 5 | das Handle |
| `tests/test_assertion.py`, `test_assertions.py` (neu), `test_cascade.py`, `test_verify.py`, `test_cli.py`, `test_render.py`, `test_mcp_server.py`, `test_confirm.py` (neu) | 1–5 | Tests |
| Seiten, Handoff, Landkarte, Spec | 6 | Doku |

---

## Task 1: Form und Faltung — `core/assertion.py`

**Files:** `src/previously/core/assertion.py` (neu), `tests/test_assertion.py` (neu).

Rein: keine Datenbank, keine Uhr.

**Interfaces — Produces:**
```python
OBLIGATION: Final = "obligation"; DECISION: Final = "decision"; REJECTION: Final = "rejection"
DIRECT: Final = "direct"; OPEN: Final = "open"
OPERATOR: Final = "human:operator"
def model_author(client: str) -> str: ...                          # "model:<client>"
def reference_problem(text: str) -> str | None: ...                # §3 der Planentscheidungen
@dataclass(frozen=True)
class Source: event: int; units: tuple[int, ...] | None
@dataclass(frozen=True)
class ObligationBody: debtor: str; creditor: str; what: str; due: date | None; state: str
@dataclass(frozen=True)
class DecisionBody: what: str; by: tuple[str, ...]; on: date; state: str; replaces: int | None
# nicht `Decision`: so heißt das Ergebnis von `decide` (core/decide.py), das derselbe Code importiert
@dataclass(frozen=True)
class Statement:
    kind: str; author: str; responsibility: str; sources: tuple[Source, ...]; reason: str | None
    handle: str | None; subject: int | None; approves: int | None; of: int | None
    body: ObligationBody | DecisionBody | None   # None nur bei REJECTION
def payload_of(statement: Statement) -> dict[str, object]: ...
def assertion_problem(payload: Mapping[str, object]) -> str | None: ...   # Formprüfung, wirft nie
def parse_statement(payload: Mapping[str, object]) -> Statement | None: ...
@dataclass(frozen=True)
class Version: id: int; recorded_at: datetime; statement: Statement
@dataclass(frozen=True)
class Thread:
    subject: int; kind: str
    versions: tuple[Version, ...]                 # stehende Fassungen in Kettenfolge
    rejected: frozenset[int]; approved: frozenset[int]
    def winner(self) -> Version | None: ...       # jüngste direkte, sonst jüngste offene weder abgelehnt noch freigegeben
    def pending(self) -> tuple[Version, ...]: ... # offene, jünger als der direkte Gewinner, weder abgelehnt noch freigegeben
def fold(rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]]) -> dict[int, Thread]: ...
def changes(before: Statement, after: Statement) -> tuple[tuple[str, str, str], ...]: ...   # (Feld, vorher, nachher), beim Lesen berechnet
def overdue(obligation: ObligationBody, today: date) -> bool: ...
```
`fold` überspringt getilgte Zeilen (`payload is None`) und Zeilen mit Formfehler; eine erste Fassung gründet ihre Kennung mit ihrer eigenen ID.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück (`payload_of` → `assertion_problem is None` → `parse_statement`); jeder Formfehler einzeln mit seinem Satz (leere Quellen, unbekanntes Präfix, `address:` ohne `@`, `name:` mit Steuerzeichen, `due` `2026-02-30`, `30.11.2026`, leer, Zustand unbekannt, Unterart unbekannt, `by` leer, `of` fehlt bei Ablehnung, Float); **Hypothesis**: für beliebige Folgen von Fassungen (direkt/offen, Ablehnungen, Freigaben, Tilgungen) ist der Gewinner die jüngste stehende direkte, sonst die jüngste stehende offene ohne Ablehnung und Freigabe — und ein offener nie Gewinner, solange eine direkte steht (Review Focus 1); `changes` nennt genau die geänderten Felder; `overdue` mit `due` gestern, heute, morgen, ohne `due`, `fulfilled`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Vorrang nach Zeit statt Verantwortung → Hypothesis rot; leere Quellen erlaubt → rot; `name:` mit Steuerzeichen erlaubt → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 2: Schreibweg, Kaskade, Prüfung — `core/assertions.py`, `redact.py`, `verify.py`

**Files:** `src/previously/core/assertions.py` (neu), `src/previously/core/redact.py`, `src/previously/core/verify.py`, `tests/test_assertions.py` (neu), `tests/test_cascade.py`, `tests/test_verify.py`.

**Interfaces — Consumes:** Aufgabe 1; `chain.prepare`/`chain.link`, `action.retrying`, `LogStore`, `RedactionStore.lock_event`, `read_policy`, `circles_of`, `decide`, `Candidate` (code-facts §1, §2, §6). **Produces:**
```python
class AssertionRefused(PreviouslyError): ...      # ein Satz, kein Text der Feststellung
def write_statements[Conn](log: LogStore[Conn], locker: RedactionStore[Conn], statements: Sequence[Statement],
                           *, recorded_at: datetime) -> tuple[int, ...]: ...
# eine Transaktion (retrying): Tip lesen; ist ein handle gesetzt und steht schon eine Feststellung mit ihm, deren IDs zurück;
# Quellen aufsteigend sperren, getilgte oder fehlende abweisen; subject/approves/of/replaces unter dem Tip prüfen (Planentscheidung 5);
# je Statement prepare(kind="assertion", occurred_at=recorded_at, payload, units=(), key=None) und link
def read_threads[Conn](log: LogStore[Conn], conn: Conn) -> dict[int, Thread]: ...
def source_identities[Conn](log: LogStore[Conn], conn: Conn, thread: Thread) -> tuple[list[Mapping[str, object]], tuple[str | None, ...]]: ...
def assertion_verdict(policy: Policy, client: Client, identities: Sequence[Mapping[str, object]],
                      sources: Sequence[str | None]) -> Decision: ...   # Planentscheidung 7: die erste, die nichts wählt, sonst die letzte
def thread_circles(policy: Policy, identities: Sequence[Mapping[str, object]], statement: Statement) -> tuple[str, ...]: ...
# Filter (F §7): Kreise der Quellen ∪ circle:X der Akteure ∪ Kreise der address:-Akteure
```
`redact.py`: die drei `redact_*` und `append_call` finden zusätzlich Feststellungen, deren `sources` das getilgte Event (oder eine getilgte genannte Einheit, oder das ganze Event bei Einheiten-Tilgung, wenn die Quelle `units: null` hat) nennen, sperren sie in derselben aufsteigenden Runde, schreiben je eine Tilgung `event_payload(id, blobs=(), reason=f"cascade of redaction {trigger}")` und `erase_payload`. `Redacted.cascaded` nennt sie mit. `verify`: vor der `action`-Prüfung ein Zweig für `kind == "assertion"`: `assertion_problem`, Verweise auf frühere Feststellungen passender Unterart, Quellen auf frühere Events; in `reconcile` „assertion stands on an erased source".

- [ ] **Step 1: Tests, die scheitern:** schreiben und lesen (eine Verpflichtung, drei Fassungen, Gewinner, Geschichte); idempotent über `handle`; Quelle fehlt, Quelle getilgt, `approves` auf Freigegebenes, Abgelehntes, Getilgtes → `AssertionRefused` und nichts geschrieben (Review Focus 2); **Kaskade** (Review Focus 3): ganzes Event, genannte Einheit, nicht genannte Einheit (steht weiter), Quelle `units: null` bei Einheiten-Tilgung, eine von drei Quellen — danach `verify` grün und `read_threads` mit Rückfall (Review Focus 1); die Gegenseite: eine Tilgung, die während des Schreibens gesperrt ist (zwei Verbindungen, wie `test_cascade.py`); `verify` findet eine Feststellung mit kaputter Form, mit Verweis nach vorn, mit getilgter Quelle ohne eigene Tilgung (von Hand geschrieben über `chain.prepare` und `insert_event`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Kaskade übergeht Feststellungen → rot; Quellen nicht gesperrt → der Wettlauf-Test rot; idempotenz entfällt → rot; `verify` ohne Zweig → rot; Kontrolle grün.
- [ ] **Step 5:** Docstring-Zahlen in `contract/store.py` und `redact.py` nachmessen, falls berührt; sechs Tore, Commit.

---

## Task 3: Die Kommandozeile

**Files:** `src/previously/cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `pyproject.toml` (T201).

**Interfaces — Consumes:** Aufgaben 1, 2. **Produces:**
```
previously assert obligation --debtor REF --creditor REF --what TEXT [--due DATE] [--state STATE]
                             [--subject ID] [--reason TEXT] --source EVENT[:SEQ,SEQ…] [--source …] [--yes]
previously assert decision   --what TEXT --by REF [--by …] --on DATE [--state STATE] [--replaces ID]
                             [--subject ID] [--reason TEXT] --source … [--yes]
previously approve ID [ID …] [--yes]
previously reject ID [--reason TEXT] [--yes]
previously obligations [--circle NAME] [--owed-by REF] [--owed-to REF] [--state STATE] [--overdue] [--proposals]
previously obligation ID [--history]
previously decisions [--circle NAME] [--state STATE] [--proposals]
previously decision ID [--history]
```
- Mit `--subject` füllen fehlende Felder sich aus dem heutigen Gewinner; die Vorschau zeigt die vollständige neue Fassung und den Unterschied (`changes`). Autor `human:operator`, Verantwortung direkt.
- Vor dem Fragen: Form und Verweise prüfen (`Error: …`, Exit 2); dann die Nutzlast als JSON, dann `_confirmed`; danach `assertion <id>` je Fassung, Exit 0; Ablehnung der Frage → `nothing written`, Exit 1.
- **Hinweis zu `name:`** (F §2.1): nennt eine Quelle eine Adresse, deren Anzeigename den `name:`-Text enthält (ohne Groß- und Kleinschreibung), schreibt die Vorschau `hint: <adresse> appears in the sources; address: is a reference that holds`. Kein Verbot.
- Listen: eine Zeile je Eintrag mit Kennung, Zustand (überfällig markiert), Frist, Schuldner → Gläubiger bzw. Entscheider, Text, `n versions`, `k proposals`; ohne `--proposals` nur Einträge mit Gewinner, mit nur die mit anhängigen Vorschlägen oder einem Vorschlag als Gewinner. `--history`: alle Fassungen mit Unterschied, Grund, Quellen, Verantwortung, Autor, Ablehnungen.

- [ ] **Step 1: Tests, die scheitern:** jedes Kommando gegen echtes PostgreSQL, Ausgabe wörtlich; Review Focus 5 (Daten vor dem Fragen abgewiesen; `due` gestern → sofort überfällig); `--subject` füllt auf; der `name:`-Hinweis und seine Kontrolle; `approve` einer Liste; `reject` mit Grund; `--circle` findet über `circle:X` beim Schuldner und über eine Quelle des Kreises; ohne Antwort auf die Frage nichts geschrieben.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `--subject` füllt nicht auf → rot; Liste zeigt Vorschläge als gültig → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md` (Kommandos, Wortlaute, Exit-Codes); T201 gemessen; sechs Tore, Commit.

---

## Task 4: Lesen über MCP — `list_obligations`, `list_decisions`

**Files:** `src/previously/mcp_server/render.py`, `read.py`, `server.py`, `tests/test_render.py`, `tests/test_mcp_server.py`.

**Interfaces — Consumes:** Aufgaben 1, 2; `Service.answer`, `record_access`, `Delivered`/`Withheld`, `render_page` (code-facts §7, §8). **Produces:**
```python
# render.py
@dataclass(frozen=True)
class Stated:
    uri: str; kind: str; label: str        # label: Zustand, überfällig, Verantwortung, "n versions", "k proposals" — von Previously
    lines: tuple[str, ...]                 # Text, Akteure, Frist, Grund, Quellen-URIs — fremd, im Zaun
type Item = Shown | WithheldMark | ErasedMark | ErrorMark | Stated
# Werkzeuge
list_obligations(circle: str | None, state: str | None, overdue: bool, proposals: bool, subject: int | None, history: bool, cursor: str | None)
list_decisions(circle: str | None, state: str | None, proposals: bool, subject: int | None, history: bool, cursor: str | None)
# `subject`, nicht `id`: der Name `id` verlangte eine Lint-Unterdrückung (Einheit 4, Ruling R-11 des Plans vom 2026-10-11)
```
Je Eintrag `assertion_verdict` (Planentscheidung 7); zurückgehalten → `WithheldMark` ohne Text und Verweise; `mcp_access` nennt jede gelieferte und zurückgehaltene Feststellung (die Kennung der gewinnenden Fassung) mit ihren Kreisen. `Stated` wird durch `sanitize` und den Zaun gerendert wie `Shown`; die Seitengrenze gilt. Die Beschreibungen sind deklarativ; `INSTRUCTIONS`, der Modul-Docstring und `mcp-tools.md` sagen nicht mehr „only reads" (code-facts §7).

- [ ] **Step 1: Tests, die scheitern:** beide Werkzeuge in beiden Generationen; ein Eintrag mit einer Quelle aus einem Kreis ohne Regel ist für `claude-code` ein Platzhalter, für `local-harness` sichtbar; ein erwähnter `address:`-Akteur aus einem anderen Kreis ändert daran nichts (F §7); `circle`-Filter über Akteure; `history`; Platzhalter ohne Text; `mcp_access` je Eintrag; die Prüfsumme der Werkzeugliste neu (Namensliste und Hex); ein Ergebnis bleibt ein Textblock.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Policy über die Akteure statt über die Quellen → rot; Platzhalter mit Text → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 5: Schreiben über MCP — Handle, `write_assertion`, `write_approve`, `write_reject`

**Files:** `src/previously/mcp_server/confirm.py` (neu), `server.py`, `src/previously/cli.py` (Einstellung), `tests/test_confirm.py` (neu), `tests/test_mcp_server.py`, `tests/test_settings.py` (falls die Sammlung es verlangt), `.importlinter` (nur falls `confirm.py` das SDK importiert — soll es nicht).

**Interfaces — Consumes:** Aufgaben 1, 2, 4. **Produces:**
```python
# confirm.py — rein; Uhr übergeben
HANDLE_SECONDS: Final = 600
def seal(key: bytes, *, client: str, payloads: Sequence[Mapping[str, object]], now: datetime, nonce: str) -> str: ...
def open_handle(key: bytes, handle: str, *, client: str, payloads: Sequence[Mapping[str, object]], now: datetime) -> str: ...
#   gibt den nonce zurück; HandleRefused mit einem Satz bei falschem Siegel, anderem Client, anderem Inhalt, Ablauf
class HandleRefused(PreviouslyError): ...
# Werkzeuge
write_assertion(items: list[...], confirm: str | None)     # items: je kind, Felder der Unterart, sources, reason, subject
write_approve(ids: list[int], confirm: str | None)
write_reject(proposal: int, reason: str | None, confirm: str | None)
```
- Ohne `confirm`: prüfen (Form, Sichtbarkeit jeder Quelle für diesen Client, Verweise) und eine Vorschau plus Handle liefern, nichts schreiben. Mit `confirm`: Handle öffnen, `write_statements` mit `handle=<nonce>` — idempotent.
- `write_assertion` schreibt immer `author: model:<client>`, `responsibility: open`. `write_approve`/`write_reject` schreiben direkt (F §6); jede Quelle der betroffenen Vorschläge muss für den Client sichtbar sein.
- Eine Quelle, die der Client nicht sehen darf oder die es nicht gibt, ergibt **dieselbe** Meldung (F §6).
- Der Schreibteil läuft **außerhalb** der Schnappschuss-Verbindung von `Service.answer` (sie liest nur): Policy und Sichtbarkeit im Schnappschuss, dann `write_statements` in eigener Transaktion; das `mcp_access` nach Planentscheidung 10, ein Eintrag je Aufruf.
- `PREVIOUSLY_MCP_CONFIRM_KEY` fehlt oder ist kürzer als 32 Zeichen → die drei Werkzeuge antworten `Error: writing is not configured on this server`; die lesenden arbeiten.

- [ ] **Step 1: Tests, die scheitern:** `confirm.py` rein: hin und zurück; anderes Siegel, anderer Client, anderer Inhalt, abgelaufen (mit `now` + 601 s) → `HandleRefused`; Werkzeuge in beiden Generationen: Vorschau ohne Schreiben; Bestätigen schreibt Vorschläge mit `model:claude-code`; zweites Bestätigen → dieselben IDs, nichts Neues (Review Focus 4); ein fremder Client löst das Handle nicht ein; eine unsichtbare Quelle und eine fehlende ergeben denselben Satz; `write_approve` durch einen Client, der eine Quelle nicht sehen darf → abgewiesen (Review Focus 2); ohne Schlüssel die Fehlermeldung, lesend weiter; `mcp_access` eines Schreibaufrufs enthält keinen Text und keine Adresse (rekursive Suche wie in `test_access.py`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Handle nicht an den Client gebunden → rot; Idempotenz entfällt → rot; Text im `mcp_access` → rot; unterschiedliche Meldung für unsichtbar und fehlend → rot; Kontrolle grün.
- [ ] **Step 5:** `configuration.md` (Variable), `cli.md` falls `serve`/`mcp` betroffen, Prüfsumme der Werkzeugliste; sechs Tore, Commit.

---

## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/assertions.md` (neu), `docs/reference/assertions.md` (neu), `docs/how-to/record-what-is-owed-and-decided.md` (neu), `docs/reference/mcp-tools.md`, `docs/reference/environment.md`, `docs/reference/configuration.md`, `docs/how-to/connect-claude-code-and-vibe.md`, `docs/explanation/erasure.md`, `docs/explanation/design-records.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-12-kup6s-assertions.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach F §13 und:
  - **Explanation:** warum vollständige Fassungen; Autor und Verantwortung getrennt, Vorrang über die Verantwortung; warum MCP nur vorschlägt und Freigabe über MCP an der Umgebung hängt; warum die Tilgung kaskadiert; warum erwähnt nicht beteiligt heißt; warum `name:` eine Beschriftung ist; warum gefaltet und nicht projiziert wird (Planentscheidung 1, mit der Messung der Endprüfung).
  - **Reference:** die Nutzlast je Unterart (Planentscheidung 2), die Verweise, die Werkzeuge; `test_docs_references` hält die zitierten Wortlaute.
  - **How-to:** eine Verpflichtung festhalten; Vorschläge von Claude Code durchgehen, freigeben, ablehnen; was offen ist abfragen; `write_approve` und `write_reject` im Client nicht automatisch erlauben.
  - `environment.md`: `PREVIOUSLY_MCP_CONFIRM_KEY` nur im MCP-Server; die Forderung an den Client mit Risiko.
  - **Handoff** (englisch): das neue Geheimnis nur für `previously-mcp`; keine Migration; die Forderung an den Client; die Ausgabezeile der Aufnahme mit mehreren Ordnern (PR #16: ` in <folder>`, `Error: folder <name>:`).
  - **Landkarte:** Einheit 5 gebaut; die offenen Punkte aus F §15 je unter ihre Einheit; erledigt: zweiter Schreibweg, `verify` kennt die Form der Feststellung, `p_obligation` braucht `responsibility`; zählen vorher und nachher.
  - Den Spec einfrieren (Kopf wie die anderen, Abweichungen des Baus im Kopf, „Was offen bleibt" in der Vergangenheit); `design-records.md` um die zitierten Paragraphen.
- [ ] Sechs Tore, `pip-audit`, Testblock des Tutorials, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung. Das Code-Paket **misst** die Lesezeit von `obligations` und `list_obligations` bei 5 000 Feststellungen (Planentscheidung 1).
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-12-pilot-feststellungen/`.
3. Push und PR.
4. Nach dem Merge: Release; dann die Abnahme nach F §14, vom Betreuer.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** F §2 → 1; §2.1 → 1 (Grammatik), 3 (Hinweis); §3 → 1 (Faltung), 2 (Freigabe/Ablehnung schreiben), 3, 4 (Ist-Zustand und Geschichte); §4, §5 → 1, 3; §6 → 3, 5; §6.1 → 5; §7 → 2 (Verdikt, Filter), 4; §8 → 2; §9 → 2, Planentscheidung 1; §10 → 5, 6; §12 Punkte 1–8 → 1, 2, 4, 5; §13 → 6; §14 → „Nach Aufgabe 6"; §15 → Landkarte in 6.
- **Platzhalter:** keine; die genauen Sätze der Meldungen legt der Umsetzer fest und `cli.md`/`mcp-tools.md` zitieren sie.
- **Namen:** `Statement`, `ObligationBody`, `DecisionBody`, `Source`, `Version`, `Thread`, `fold`, `changes`, `overdue`, `payload_of`, `assertion_problem`, `parse_statement`, `reference_problem`, `write_statements`, `read_threads`, `source_identities`, `assertion_verdict`, `thread_circles`, `AssertionRefused`, `Stated`, `seal`, `open_handle`, `HandleRefused` — überall gleich.
- **Bekannte Abweichung vom Spec:** Planentscheidung 1 (keine Projektion, keine Migration), vom Betreuer mit der Durchsicht dieses Plans zu bestätigen.
