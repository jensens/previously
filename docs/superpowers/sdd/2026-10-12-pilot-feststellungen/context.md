## Was der Plan am Spec entscheidet

1. **Keine Projektionstabellen, keine Migration** (F §9, §10 nannten `p_obligation`, `p_decision` und eine Migration `0006`). Gelesen wird durch Falten aller Feststellungen aus dem Log (`read_by_kind(conn, "assertion")`, in SQL nach Art gefiltert). Gründe, aus dem Code: der Rückfall auf die nächste stehende Fassung nach einer Tilgung (F §8) braucht ohnehin alle Fassungen; die Kreise hängen an der **heutigen** Policy (F §7) und lassen sich nicht speichern; der MCP-Server liest nur `LogStore` (code-facts §3). Leitsatz 3 bleibt gewahrt: der Zustand wird berechnet, nicht gehalten. **Die Endprüfung misst** die Zeit einer Liste bei 5 000 Feststellungen; erst wenn sie trägt, kommt eine Projektion (Landkarte). Vom Betreuer am 2026-10-12 bestätigt: „schauen wir mal, ob wir ohne Projektionstabellen auskommen — das kann man notfalls nachliefern."
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

