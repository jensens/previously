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
- Kein Mock für Zeit, Datenbank, Speicher oder Zufall. Ein Konnektor aus dem
  Speicher (Bytes in einer Liste) ist ein Testdouble des Protokolls, kein Mock
  dieser vier — zulässig für den Lauf; der IMAP-Weg selbst läuft gegen GreenMail.
- **Testmails sind erfunden**, deutsch und englisch gemischt, nie Kundenpost;
  das Repository ist öffentlich.
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
  | `ingest imap`, stdout | `imap: <n> appended, <n> known, <n> variants, up to uid <uid>` |
  | `ingest imap`, stderr je Variante | `variant of <message-id>: event <id>` |
  | `ArtifactChanged` | `<source>/<external_id> is known with another content (artifact <alt> ≠ <neu>)` — die Hashes als die ersten 16 Hexzeichen |
  | Hilfe | `ingest` — `take in new mail from an IMAP folder` |
  | Einheit ohne Inhalt | `no readable body: encrypted`, `no readable body: attachments only`, `no readable body: empty` |
  | Namen in der Nutzlast | `artifact_hash`, `channel_identities`, `headers`, `raw`, `date_source`, `internaldate`, `found_in`, `body`, `variant_of`, `forwarded_in` |

