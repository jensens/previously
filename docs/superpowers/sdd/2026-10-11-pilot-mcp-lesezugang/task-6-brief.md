## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/mcp-interface.md` (neu), `docs/reference/mcp-tools.md` (neu), `docs/how-to/connect-claude-code-and-vibe.md` (neu), `docs/explanation/trust-boundaries.md`, `docs/explanation/processing-policy.md`, `docs/explanation/design-records.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md` (neu, englisch), `docs/superpowers/landkarte.md`, beide Specs (Einfrieren).

- [ ] Nach S §11 und K, und:
  - `mcp-interface.md` (Explanation): warum der Client ein Verarbeiter ist; warum ein Textblock (die Tabelle aus M4); warum der Zaun eine Wette ist und was die Grenze wirklich ist; warum das Zugriffsprotokoll im Log liegt; warum die alte Generation nichts aufhält (Entscheidung vom 2026-10-10);
  - `mcp-tools.md` (Reference): Werkzeuge, Ressourcen, Prompts mit Argumenten und Ausgabe; die Nutzlast von `mcp_access`; `test_docs_references` hält die zitierten Wortlaute;
  - die How-to: Client anlegen, Claude Code (`claude mcp add --transport http … --header`) und Vibe (`headers`, nicht `api_key_env`) verbinden, prüfen mit `whoami`; **die datierte Liste der getesteten Konfigurationen**; stdio für Claude Code lokal;
  - `design-records.md`: §8 der Architektur ist durch das Konzept abgelöst;
  - der Handoff (englisch): `previously-mcp` Deployment, Service, ein Replikat, Bereitschaft über `server/discover`, Stufe A (port-forward) und A2 (Tailscale/Headscale, `PREVIOUSLY_MCP_ALLOWED_HOSTS`), Tokens im Werkzeug-Pod anlegen; zusammen mit dem Handoff des Gates (`2026-10-09-kup6s-gate.md`) und dem lokalen Modellserver; welches Release (`v0.1.0a3`);
  - die Landkarte: Einheit 4 gebaut; die offenen Punkte aus K §10 und S §13 je unter ihre Einheit, darunter **die Idee zu Projekten mit Gegenthese** unter Einheit 5; der Punkt „Vibe auf `mcp` 2.x"; die Menge von `mcp_access`; zählen vorher und nachher;
  - beide Specs einfrieren (Kopf wie die anderen, Statuszeile, „Was offen bleibt" in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung.
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-11-pilot-mcp-lesezugang/`.
3. Push und PR.
4. Nach dem Merge: Release `v0.1.0a3`; dann **Abnahme 9 (S §12), vom Betreuer**: Claude Code und Vibe gegen `previously serve` mit seiner Probe-Datenbank, drei Kreise (Regel für beide, Regel für einen, keine Regel), die Frage aus K §1, danach `previously access`.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** S §2 → 2; §3 → 1; §4 → 5; §5, §6 → 4, 5; §7 → 3, 5; §8 → 6 (Handoff), „Nach Aufgabe 6" (Release); §9 → Dateistruktur; §10 Punkte 1–11 → 5 (4 für 6–8), 9 → 1, 12 → 3/5/6; §11 → 6; §12 → die Aufgaben und „Nach Aufgabe 6"; §13 und K §10 → Landkarte.
- **Platzhalter:** keine „TBD"; die Seitengrenze misst der Umsetzer gegen eine echte Mail und begründet sie im Kommentar.
- **Namen:** `Provider`, `Rule`, `Client`, `CLIENT`, `mint_token`, `token_hash`, `client_for_token`, `add_client`, `MCP_ACCESS`, `Access`, `Delivered`, `Withheld`, `AccessRow`, `record_access`, `read_access`, `PAGE_CHARS`, `Head`, `Shown`, `WithheldMark`, `ErasedMark`, `Item`, `Page`, `sanitize`, `render_page`, `render_error`, `encode_cursor`, `decode_cursor`, `LogStore.observations`, `Seen`, `chronicle`, `events`, `build_server`, `build_app`, `guarded` — überall gleich.
- **Code nur, wo gelaufen:** die SDK-Aufrufe sind gemessen (M1, M2) oder im Quelltext nachgesehen (oben); der Rest steht als Schnittstelle und Test.
