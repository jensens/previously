**Entscheidungen des Betreuers am 2026-10-15:**
- **Projektion (A):** Tabellen, beim Lesen nachgezogen — immer aktuell, kein Job nötig, Kommandozeile und MCP profitieren.
- **Weitere Fundorte einer Mail: später**, „aber nicht vergessen und nichts verbauen" (Planentscheidung 12).
- **Der Parameter heißt `within`**, auf der Kommandozeile (`--within N`) wie über MCP; `in` ist in Python reserviert, und ein Alias auf einem Parameter eines Werkzeugs scheitert gemessen (CF §11). „Wenn dann konsistent beides."
- **Ein Event am Anfang ist Quelle**; und `concerns` wird **keine eingebaute Art**: „wir müssen aufpassen, nicht inflationär eingebaute Arten einzuführen, sonst führen wir das ganze Deklarative ad absurdum." Eingebaut bleiben die drei, die das Gate liest.

## Was der Plan am Spec entscheidet

1. **`event` und `*` im Vokabular.** Eine Art von Beziehung darf in `from` den Wert `event` nennen (Ausgangspunkt ist ein Event oder Einheiten eines Events, eine Wahrnehmung) und in `to` den Wert `*` (jede Art von Entität). `event` steht nie in `to`; `*` nie in `from`; `*` steht allein. Die Vokabulardatei schreibt beides als Text (`from = ["event"]`, `to = ["*"]`); die Form der Handlung `vocabulary` bekommt keine neuen Schlüssel, nur zwei erlaubte Werte.
2. **`concerns` im Grundvokabular:** `from = ["event"]`, `to = ["*"]`, keine Verhalten, keine Felder, Beschriftungen `de = "betrifft"`, `en = "concerns"`. `apply --base` fügt es auf einem Log aus Phase 1 hinzu (es fehlt dort), ohne sonst etwas zu ändern (F-a).
3. **Ein Event am Anfang ist Quelle.** Für jede Beziehung, deren Anfang ein Event ist: unter `sources` steht ein Eintrag mit diesem Event, dessen Einheiten die Einheiten des Anfangs umfassen (`units: null` umfasst alle). Fehlt er, weist der Schreibweg ab („the event a relation starts at must be among its sources") und `verify` meldet es. Damit tilgt die vorhandene Kaskade die Zuordnung mit der Mail oder mit ihren Einheiten (CF §1, §6), und die Policy entscheidet über die Mail. Die Kommandozeile und MCP setzen den Anfang als Quelle selbst, wenn der Aufrufer ihn nicht nennt.
4. **Die Menge einer Klammer** (Z §8), rein in `core`, `members(bracket, edges) -> Members`:
   - die Klammer und alles, was über `part_of` darunter liegt (transitiv nach unten: ein Vorgang `part_of` ein Projekt gehört zum Projekt); gezählt werden geltende Gewinner, die stehen, wie `Graph.relations()` sie gibt;
   - jede `concerns`-Kante in diese Menge: vom ganzen Event (alle Einheiten) oder von Einheiten;
   - **das Genauere ersetzt das Allgemeine:** hat eine Einheit eigene `concerns`-Kanten, gilt für sie nur, was diese sagen; die Kante ihres Events gilt für sie nicht;
   - Ergebnis: je Event `None` (alle Einheiten) oder die Menge der Einheiten.
5. **Die Projektion `graph`** (Entscheidung A; CF §4, §5, §6):
   - Tabellen (Migration `0006_graph`): `p_graph_version` (`id` PK→`event.id`, `subject`, `kind`, `under` nullable) — eine Zeile je Graph-Fassung und je Ablehnung einer Graph-Fassung (`kind = 'rejection'`, `subject` = die Kennung der abgelehnten Fassung); `p_graph_thread` (`subject` PK→`event.id`, `kind`, `type`, `winner_id`, `level`, `state`, `start_event`, `start_units` int[] nullable, `start_entity`, `to_entity`, `candidates` int[] nullable, `period_start`, `period_end`, `pending`, `objections`, `question` bool) mit Indizes auf `(kind, type)`, `to_entity`, `start_event`. Keine Inhalte, keine Felder, keine Namen: was gezeigt wird, liest der Leser aus dem Log (`events_by_id`) — so hält eine Tilgung, ohne dass die Projektion Inhalt löschen muss.
   - **Nachzug nur der berührten Kennungen:** `GraphProjection.write(batch)` merkt sich je Batch die schmutzigen Kennungen: eine neue Graph-Fassung (ihre Kennung); eine Ablehnung einer Graph-Fassung; eine `redaction`, deren Ziel eine Graph-Fassung ist; ein `approval_class`-Event (alle Kennungen mit einer Fassung `under` einer Klasse desselben Namens). Dann liest es für diese Kennungen die Fassungen aus `p_graph_version`, holt sie mit `events_by_id` aus dem Log (getilgte kommen als `None`), faltet sie mit dem vorhandenen Modell unter `read_classes` und schreibt die Zusammenfassung. Ein `vocabulary`-Event macht nichts schmutzig: was zum Vokabular passt, entscheidet der Leser.
   - **Beim Lesen nachgezogen:** jeder Leser (Kommandozeile, MCP) ruft vor dem Lesen `catch_up(log, store, GRAPH)` in eigener Transaktion; ist nichts neu, kostet das eine Abfrage. Gleichzeitige Nachzüge warten am Zeilenschloss von `projection_state` (CF §4). `previously project` und `redact` ziehen sie wie die anderen nach; ihre Ausgabe bekommt eine Zeile `graph`.
   - **Der Schreibweg bleibt beim Falten** des ganzen Logs (Z §3.4, Messung): er prüft unter dem Tip, und die Projektion hinkt in der Transaktion eines Schreibvorgangs nach. Gemessen kostet das 7 s je Schreibvorgang bei 100 000 Beziehungen; für den Piloten tragbar, und eine Aufgabe für später (Landkarte).
   - **Gleichwertigkeit als Zusicherung:** für beliebige Folgen von Fassungen, Ablehnungen, Freigaben, Tilgungen und Klassen gibt die Projektion nach jedem Nachzug dieselben Gewinner, Zustände und Zähler wie `fold_graph` über das ganze Log — Hypothesis gegen echtes PostgreSQL, auch mit einem Nachzug mitten in der Folge.
6. **Der Leser hat ein eigenes Protokoll** `GraphStore` in `contract/store.py` (CF §4: kein Protokoll liest heute eine Projektion), neben `ProjectionStore`: Abfragen auf `p_graph_thread` (Entitäten nach Art und Zustand; Beziehungen nach Art, Enden, Stichtag; anhängige Fassungen und Einwände; die Kanten für `members`). `build_server` bekommt ihn als Parameter; `PostgresStorage` erfüllt ihn. Die gezählten Methoden im Docstring von `contract/store.py` werden nachgemessen.
7. **`--as-of`** (`relations --as-of`, `entity --history` mit Stichtag) liest weiter das Log und faltet: die Projektion kennt nur den heutigen Stand. Das ist selten und darf langsam sein.
8. **`chronicle --within N`:** die Zeilen von `p_chronicle`, deren `(event_id, seq)` in `members(N)` liegen, in derselben Ordnung und mit denselben Grenzen (`--since`, `--until`, `--limit`). Eine Klammer, die es nicht gibt oder die keine Entität ist: `Error:` mit Exit 2. Die Ausgabezeile bleibt gleich.
9. **`previously(within=N)` über MCP:** zeigt die Events, die in `members(N)` liegen, und von ihnen nur die Einheiten, die dazugehören; `within` geht in die Filter des Cursors (als Text, CF §4) und in den Titel (`chronicle · within 12`). Eine Klammer, die der Client nicht sehen darf oder die es nicht gibt: derselbe Satz. Die Policy entscheidet je Event wie bisher; `within` findet nur, es gibt nichts frei (Z §10.4).
10. **Der Kopf** zählt die Einwände aus `p_graph_thread.objections > 0` und prüft die Sichtbarkeit nur für diese Kennungen; `list_entities`, `list_triage` und `previously status` lesen aus der Projektion. Jeder MCP-Aufruf zieht zuerst nach.
11. **`verify`** bleibt beim Falten des Logs, und `previously project --check` vergleicht die Projektion mit der Faltung und meldet jede Abweichung (eine Zeile je Kennung) — die Projektion ist wegwerfbar, ihr Fehler darf nicht still bleiben.
12. **Nicht verbauen — weitere Fundorte einer Mail** (Z §8, später): eine Zuordnung, die die Aufnahme schreibt, ist eine gewöhnliche `concerns`-Beziehung mit dem Event als Anfang und Quelle; wer sie schreibt (Betreiber über eine Ordner-Zuordnung, oder eine Regel) und auf welcher Stufe, bleibt offen. Nichts in Phase 2 nimmt an, dass nur Menschen oder Modelle `concerns` schreiben; die Landkarte bekommt den Punkt mit diesem Satz.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten, Handoff englisch; Plan, Landkarte deutsch.
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
- Kein Mock für Zeit, Datenbank oder Zufall; gegen echtes PostgreSQL.
- `core` importiert kein SQL; neue Abfragen nur hinter `contract.store`. Kein Vertrag in `.importlinter` wird erweitert.
- **Keine neue eingebaute Art.** Das Gate (`core/decide.py`) bleibt unberührt; eine Zuordnung gibt in Phase 2 nichts frei.
- **Kein Inhalt in der Projektion**, und kein Text in `mcp_access`, in einer Fehlermeldung, in einem Platzhalter.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener Zusicherung, mit grüner Kontrolle.
- Ein Kommentar ist eine Behauptung: `T201` in `pyproject.toml`, die Zählungen in `contract/store.py`, „eight tables" auf `database-schema.md`, „fifteen tools" — nachmessen, was sich bewegt.
- Typed-out output (`project`-Zeilen, `migrate`-Zeilen mit `0006_graph`, Tutorial) wird aus echten Läufen neu getippt.
- Commits: Dateien namentlich, Trailer `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Kommandozeile | `previously chronicle --within N`; `previously relate concerns --from-event E[:SEQ,SEQ] --to N` |
  | MCP | Parameter `within` am Werkzeug `previously`; Titel `chronicle · within N` |
  | Ausgabe von `project` | eine Zeile `graph` mit `_describe` wie die anderen |
  | Migration | `0006_graph` |
  | Abweisung | `the event a relation starts at must be among its sources` |

## Review Focus

1. **Eine Zuordnung überlebt ihre Mail:** die Mail oder ihre Einheit wird getilgt → die Zuordnung fällt mit, die Projektion zieht nach, `chronicle --within` zeigt nichts mehr davon, `verify` ist sauber. → Aufgaben 2 und 3.
2. **Die Projektion weicht still ab:** nach Tilgung einer Fassung, nach Rückzug einer Klasse mit `demote`, nach einer Ablehnung — Gewinner, Zustand und Zähler stimmen nicht mehr mit der Faltung. → Aufgabe 3 (Gleichwertigkeit), Aufgabe 4 (`project --check`).
3. **`within` gibt frei:** ein Client sieht über `within` eine Einheit, die er ohne nicht sähe, oder erfährt über eine leere Seite, dass eine verborgene Klammer existiert. → Aufgabe 5.
4. **Das Genauere ersetzt das Allgemeine falsch:** eine Einheit mit eigener Kante zu einer anderen Klammer erscheint trotzdem in der Chronik der Klammer ihres Events; oder eine Einheit ohne eigene Kante fällt aus der Chronik ihres Events. → Aufgabe 2.
5. **Zwei Leser ziehen gleichzeitig nach** (zwei MCP-Aufrufe, ein CronJob): keiner sieht einen halben Stand, keiner schreibt doppelt. → Aufgabe 3.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/vocabulary.py`, `src/previously/vocabulary.toml` | 1 | `event` und `*`; `concerns` im Grundvokabular |
| `src/previously/core/graph.py`, `core/graph_write.py`, `core/verify.py` | 1, 2 | Anfang als Ereignis, Quelle-Regel, `members` |
| `src/previously/core/projection/graph.py` (neu), `core/projection/__init__.py` | 3 | die Projektion `graph` |
| `src/previously/storage/schema.py`, `migrations/versions/0006_graph.py` (neu), `storage/postgres.py`, `contract/rows.py`, `contract/store.py` | 3, 4 | Tabellen, Migration, `ProjectionStore`-Methoden, `GraphStore` |
| `src/previously/cli.py` | 2, 4, 5 | `relate concerns --from-event`, Leser aus der Projektion, `project --check`, `chronicle --within` |
| `src/previously/mcp_server/*` | 2, 4, 5 | `write_relation` mit Event-Anfang, Leser aus der Projektion, `within` |
| Tests | 1–5 | |
| Seiten, Handoff, Landkarte | 6 | |

---

