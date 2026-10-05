## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Workflow,
  Dockerfile, Skript und Handoff **englisch**; Spec, Plan, Landkarte deutsch.
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
- Kein `# type: ignore`; keine neue Lint-Unterdrückung (es bleiben fünf, `CLAUDE.md`).
- Kein Mock für Zeit, Datenbank, Speicher oder Zufall; Tests gegen echtes
  PostgreSQL über die Fixtures in `tests/conftest.py`.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener
  Zusicherung, mit einer grünen Kontrolle daneben. Mutationen im Baum, sofort
  zurückgenommen, danach `git status --short`.
- Ein Kommentar ist eine Behauptung; jede Zahl darin ist gemessen.
- Getippte Ausgabe ist eine Messung: neu tippen aus einem Lauf, nie eine Zahl
  in einem Block ändern. Das Tutorial zuletzt.
- Kein Geheimnis in Ausgabe, Seite, Bericht, Commit.
- Commits: Dateien namentlich stagen, nie `git add -A`; Botschaft per Datei,
  `git commit -F`; Trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`,
  nie `Co-Authored-By`, nie „Generated with".
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | `migrate`, stdout | `migrated: <from> -> <head>`, mit `(empty)` als `<from>` bei einer leeren Datenbank |
  | `migrate`, stdout | `up to date: <head>` |
  | `migrate`, stderr, Code 2 | `Error: the database is at revision <rev>, which this version of previously does not know; it knows revisions up to <head>` |
  | Hilfe | `migrate` — `bring the database schema up to the newest revision` |
  | Image-Tags | `<version>`, `<major>.<minor>`; `latest` nur für ein stabiles Release |

- Erlaubte Tags: `vX.Y.Z`, `vX.Y.ZaN`, `vX.Y.ZbN`, `vX.Y.ZrcN`
  (regulärer Ausdruck `^v[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$`).
- Aktionen in Workflows auf einen Commit gepinnt, die Fassung als Kommentar
  daneben, wie in `gates.yml`.
- Die Basis des Images per Digest gepinnt:
  `ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:8e88a074b0969bdc461f681727238e109438d70771828909f9ef19cfcc96c43a`
  (aufgelöst am 2026-10-05).

