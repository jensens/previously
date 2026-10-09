## Task 7: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/trust-boundaries.md` (neu), `docs/explanation/processing-policy.md` (neu), `docs/reference/policy-and-model-calls.md` (neu), `docs/how-to/set-a-policy-and-try-a-call.md` (neu), Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-09-kup6s-gate.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach Spec §9, und:
  - `trust-boundaries.md` (Explanation): jede Stelle, an der Inhalt das System verlässt — IMAP, S3, Sicherungen, der Anker, das Gate je Anbieter —, wer sie bewacht, was offen ist (unbekannte Beteiligte, Aufbewahrung beim Anbieter, Aufruf ohne Audit bei Abbruch, MCP und Schreiben nach außen kommen);
  - `processing-policy.md` (Explanation): Spec §1.2 erster Punkt, Kreise nach Simmel, strengste gewinnt, Zusage und Meldung (mit der Messung: `global` meldet `global`), „ohne Regel nur lokal" und warum der Rückfall sichtbar sein muss, warum das Audit im Log liegt und das Ergebnis in den Einheiten;
  - `policy-and-model-calls.md` (Reference): die Nutzlasten aus Spec §2.1 und §4.1 mit den Namen, die der Code hat — `test_docs_references` hält die Wortlaute;
  - die How-to: Zusagen deklarieren, einen Kreis anlegen, Mitglied, eigene Identität, Regel, `gate explain`, `gate try`, `policy gaps`; Ollama mit `qwen3:4b` lokal;
  - der Handoff (englisch, Spec §6): zwei Secrets, Egress auf 443 zu `api.anthropic.com` und `api.mistral.ai`, wahlweise `PREVIOUSLY_PRICES`; und, als eigener Abschnitt, der Modellserver im Cluster mit `PREVIOUSLY_LOCAL_MODEL_URL`;
  - die Landkarte: Einheit 3 gebaut; „Offenlegungsprüfung" bei den Einheiten 3 und 4 durch die beiden Prüfungen ersetzt (Spec §1.2); Release `v0.1.0a2` vom 2026-10-09 und die Übergabe des Handoffs der Aufnahme nachgetragen; die offenen Punkte aus Spec §11 und Entscheidung 6 je unter ihre Einheit; zählen vorher und nachher.
  - Spec einfrieren (Kopf wie die anderen, Statuszeile, §11 in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 7

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung; Fehlbedienung benannt, nicht gejagt.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-09-pilot-gate-und-policy/`.
4. Push und PR.
5. **Abnahme 10 (Spec §10), vom Betreuer, lokal, nach dem Merge:** die echten Schlüssel, Ollama mit `qwen3:4b`; Zusagen, Kreis, Mitgliedschaft, eigene Identität; „überall" → Anthropic mit `response.inference_geo` im Event; „EU" → Mistral; widerrufen → lokal mit Warnung, `policy gaps` nennt den Kreis; Quelle getilgt → Einheiten des `model_call` leer, `verify` grün. Danach Probe-Log verwerfen.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §1.2 → 1 (Handlung statt Feststellung), 7 (Landkarte); §2.1 → 2; §2.2–§2.5 → 3; §2.6 → 3 (`Fallback`), 5 (Event, stderr, `gaps`); §3.1–§3.4 → 4, 5; §4.1 → 5; §4.2 → 6; §4.3 → 1, 2, 5, 6; §4.4 → 1; §5 → 2, 5; §6 → 7 (Handoff), 4 (Schlüssel nirgends); §7 → Dateistruktur (`core/decide.py` statt der Entscheidung in `core/policy.py`, eine Datei je Verantwortung); §8 Punkt 1–7 → 3, 8–11 und 13 → 5, 11 → 6, 12 → 1, 14 → 4, 15 → 2/5/7, der Rückfall → 3/5; §9 → 7; §10 → die Aufgaben und „Nach Aufgabe 7"; §11 → Landkarte.
- **Platzhalter:** keine „TBD"; die Preise liest der Umsetzer nach und nennt die Quelle.
- **Namen:** `write_action`, `append_action`, `KNOWN_ACTIONS`, `REDACTION`, `POLICY`, `MODEL_CALL`, `Circle`, `Membership`, `OwnIdentity`, `Rule`, `Inference`, `Provider`, `Policy`, `PolicyRefused`, `set_policy`, `read_policy`, `check_payload`, `Candidate`, `Fallback`, `Decision`, `LOCAL_ONLY`, `circles_of`, `decide`, `Request`, `Response`, `Adapter`, `AdapterError`, `AnthropicAdapter`, `OpenAICompatibleAdapter`, `MISTRAL_BASE_URL`, `ModelServer`, `Task`, `MailOverview`, `MAIL_OVERVIEW`, `Prices`, `load_prices`, `estimate`, `Called`, `explain`, `call`, `Gap`, `gaps`, `Redacted.cascaded` — überall gleich.
- **Code nur, wo gelaufen:** die Aufrufe der drei Anbieter sind gemessen; der Rest steht als Schnittstelle und Test.
