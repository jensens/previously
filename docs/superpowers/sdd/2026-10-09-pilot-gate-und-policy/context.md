## Was der Plan vorgibt und was nicht

Gelaufen am 2026-10-09, Wegwerfcode im Scratchpad, nicht übernommen; je eine
erfundene Mail (Betreff, drei Zeilen, deutsch und englisch gemischt) mit dem
Schema `{language, topic, participants}`, `additionalProperties: false`:

| Anbieter, Modell | Aufruf | Ergebnis |
|---|---|---|
| Anthropic, `claude-haiku-5-5` | `messages.create(..., output_config={"format": {"type": "json_schema", "schema": S}, "effort": "low"}, inference_geo="global")` | gültiges JSON, 3,1 s; `usage.inference_geo == "global"`; 400 Tokens hinein, 130 heraus |
| ebenso | `inference_geo="us"` | gültiges JSON, 1,9 s; `usage.inference_geo == "us"` |
| Anthropic, `claude-haiku-4-5` | `inference_geo="global"` | **400**: `'claude-haiku-4-5-20251001' does not support inference_geo.` |
| Mistral, `mistral-small-2603` | `openai.OpenAI(base_url="https://api.mistral.ai/v1").chat.completions.create(..., response_format={"type": "json_schema", "json_schema": {"name": "mail_overview", "schema": S, "strict": True}})` | gültiges JSON, 0,6 s; `model == "mistral-small-2603"`; kein Feld zum Raum |
| Ollama 0.13.2, `qwen3:4b`, OpenAI-kompatibel | wie Mistral, `base_url="http://localhost:11434/v1"`, **`reasoning_effort="none"`** | gültiges JSON, 6,7 s auf CPU (i7-11370H, unter fremder Last) |
| ebenso, ohne `reasoning_effort` | | **über 600 s, abgebrochen**: das Modell denkt |

Daraus, und nur daraus, die Aufrufe in Aufgabe 4. `/v1/models` von Mistral
listet `mistral-small-2603` und `ministral-8b-2512` als feste Fassungen;
`mistral-small-latest` antwortet unter seinem Alias.

**Nicht gelaufen**, darum nur als Anforderung mit Tests: Policy, Entscheidung,
Ablauf, Kaskade, Kommandos.

## Was der Plan am Spec entscheidet

1. **Eine Adapter-Klasse für Mistral und lokal**, `OpenAICompatibleAdapter`
   über den Client `openai` (Messung oben). `mistralai` (Spec §7.3) entfällt:
   eine Abhängigkeit weniger, und die Architektur nennt `openai` für den
   OpenAI-kompatiblen Weg ohnehin.
2. **Das Ausgabeschema ist ein Pydantic-Modell** (Architektur §10.1, bisher
   zurückgestellt, `DEPENDENCIES.md`): `model_json_schema()` gibt das Schema
   für den Anbieter, `model_validate_json()` prüft die Antwort. Pydantic ist
   unter pyright strikt getypt; `jsonschema` bräuchte Stubs. `extra="forbid"`
   ergibt `additionalProperties: false`. Der Eintrag
   `runtime-evaluated-base-classes = ["pydantic.BaseModel"]` kommt in die
   ruff-Konfiguration, wie `DEPENDENCIES.md` es vorhersagt.
3. **Modelle von `mail_overview`**, in dieser Reihenfolge:
   `anthropic/claude-haiku-5-5` (Aufwand `low`),
   `mistral/mistral-small-2603`, `local/qwen3:4b`.
4. **Der lokale Adapter setzt immer `reasoning_effort="none"`** (Messung).
5. **Die Kaskade schreibt Tilgungen.** `verify` meldet heute jede getilgte
   Einheit ohne Tilgung, die sie anordnet. Die Kaskade schreibt deshalb je
   betroffenem `model_call` eine `redaction` mit `scope: units` und dem Grund
   `cascade of redaction <id>`, in derselben Transaktion wie die auslösende.
   `verify` gleicht sie mit seinen bestehenden Regeln ab.
6. **`model_call`-Events, die eine Quelle lesen, werden durch Lesen aller
   Handlungen gefunden** (`read_by_kind(conn, "action")`). Für den Piloten
   genügt das; ein Index ist ein offener Punkt der Landkarte.
7. **Die Adressen der Anbieter** sind Konstanten in den Adaptern, mit einem
   Parameter `base_url` im Konstruktor, den nur die Tests setzen. Lokal liest
   `PREVIOUSLY_LOCAL_MODEL_URL` (ohne Vorgabe: kein lokaler Anbieter
   erreichbar).
8. **Der Testserver** ist ein `http.server.ThreadingHTTPServer` im
   Testprozess, als Fixture in `tests/conftest.py`: er beantwortet
   `POST /v1/messages` (Anthropic) und `POST /v1/chat/completions`
   (OpenAI-kompatibel) mit Antworten, die der Test vorher einreiht, und hält
   jede empfangene Anfrage fest, damit ein Test sie lesen kann (gesetzter
   Raum, Schema, `reasoning_effort`). Kein Container, keine Mocks: die echten
   Clients reden echtes HTTP mit ihm.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten,
  Handoff **englisch**; Spec, Plan, Landkarte deutsch.
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
- Kein `# type: ignore`; keine neue Lint-Unterdrückung (fünf, `CLAUDE.md`).
- Kein Mock für Zeit, Datenbank oder Zufall. `recorded_at` wird übergeben,
  wie überall im Kern. Der Testserver aus Entscheidung 8 ist ein Server, kein
  Mock.
- **Kein Test ruft einen echten Anbieter.** CI hat keine Secrets
  (`gates.yml`); echte Aufrufe sind Abnahme 10.
- **Kein Schlüssel erscheint** in einem Event, einer Meldung, einem
  Traceback auf stderr (Spec §6).
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener
  Zusicherung, mit einer grünen Kontrolle.
- **Arbeitsregel vom 2026-10-05:** ein Befund, der nur bei Fehlbedienung
  auftritt, wird benannt, nicht gejagt.
- Ein Kommentar ist eine Behauptung; Zahlen darin gemessen.
- Getippte Ausgabe ist eine Messung; der Testblock des Tutorials wird aus
  einem grünen Lauf neu getippt, wenn sich die Zahl ändert.
- Commits: Dateien namentlich, `git commit -F`, Trailer
  `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Hilfe | `policy` — `set and show the processing policy`; `gate` — `explain or try a model call` |
  | `gate try`, stdout | die Ausgabe als JSON, dann `model_call: event <id>` |
  | stderr, Rückfall | `processed locally: no rule for <what> — set one with previously policy rule <scope> …` |
  | stderr, Alarm | `alarm: inference_geo requested <a>, reported <b>` |
  | stderr, Ablehnung | `denied: <reason>` |
  | Grund, kein lokaler Anbieter | `no local provider is declared` |
  | Grund der Kaskade | `cascade of redaction <id>` |
  | Namen in der Nutzlast | `action`, `policy`, `statement`, `revoked`, `task`, `inputs`, `response`, `outcome`, `alarms`, `fallback` |
  | `outcome` | `ok`, `denied`, `refused`, `schema_invalid`, `error` |

## Review Focus

1. **Ein getilgtes Event** (`payload is None`, Einheiten ohne Inhalt) als
   Eingabe von `gate try`: kein Aufruf, kein Prompt aus Grabsteinen — ein
   Satz, Rückgabe 2, und ein `model_call` mit `outcome: denied`, Grund
   `the event is erased`. → Aufgabe 5.
2. **Eine Adresse mit großgeschriebener Domain** (`Eva.Huber@Kunde-XZ.at`)
   gegen die Mitgliedschaft `@kunde-xz.at`: Mitglied. Ein lokaler Teil mit
   anderer Schreibung ist es nicht. → Aufgabe 3.
3. **Der Anbieter antwortet mit gültigem JSON, das dem Schema nicht genügt**
   (ein Feld zu viel, eines fehlt) oder mit Text statt JSON:
   `outcome: schema_invalid`, keine Einheiten, Rückgabe 2. → Aufgabe 5.
4. **Ollama läuft nicht**, und die Vorgabe „nur lokal" greift: ein Satz, der
   den lokalen Server nennt, `outcome: error`, Rückgabe 2, kein Traceback.
   → Aufgabe 5.
5. **Eine Mitgliedschaft in einem Kreis, der nicht angelegt ist**, oder eine
   Regel mit `project:…`: abgewiesen beim Schreiben, ein Satz, nichts
   geschrieben. → Aufgabe 2.

---


## Rulings der Vorprüfung

Ruling R-1: `LOCAL_ONLY` (der Name der eingebauten Regel) wohnt in `core/policy.py` (Aufgabe 2), `core/decide.py` importiert ihn — `policy show` braucht ihn vor Aufgabe 3 — kostet, wenn falsch: ein Import mehr.
Ruling R-2: `pydantic` samt ruff-Eintrag `runtime-evaluated-base-classes` und Urteil in `DEPENDENCIES.md` kommt mit Aufgabe 5, nicht 4 — eine deklarierte Abhängigkeit, die nichts importiert, ist nach CLAUDE.md eine Leiche, auch für eine Aufgabe lang — kostet, wenn falsch: nichts.
Ruling R-3: Zuordnung nach Inhalt, Spec §8 in der Fassung 62d044f: 1–7 → Aufgabe 3; 8 (Ablösen) → 2; 9, 10, 11, 14 → 5; 12 (Kaskade) → 6; 13 (Chronik) → 1; 15 (lint-imports) → 4; 16 (Referenz) → 2, 5, 7 — der Plan zählte vor der Umnummerierung — kostet, wenn falsch: ein Test fehlt, die Endprüfung findet ihn.
