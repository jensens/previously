## Task 2: Reference

**Files:**
- Create: `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/reference/database-schema.md`, `docs/reference/hash-format.md`
- Modify: `docs/reference/index.md`

**Interfaces:**
- Consumes: den Baum aus Aufgabe 1.
- Produces: die Label `(cli-reference)=`, `(configuration-reference)=`, `(database-schema)=`, `(hash-format)=`. Aufgabe 7 verweist aus dem Code darauf.

Reference ist der Quadrant, der sich gegen den Code prüfen lässt — tu das, statt aus dem Gedächtnis zu schreiben.

- [ ] **Schritt 1: `docs/reference/cli.md`**

Quadrant: Reference. Keine Anleitung, keine Begründung, nur Tatsachen.

Die Oberfläche steht in `src/previously/cli.py:169-190`. Vier Unterbefehle:

| Befehl | Argumente |
|---|---|
| `append` | `--source` (Pflicht), `--external-id` (Pflicht), `--text` (Pflicht), `--occurred-at`, `--evidence` (Vorgabe `recollection`, erlaubt `verbatim`/`recollection`) |
| `log` | `--from` (Vorgabe 1), `--limit` (Vorgabe 50) |
| `verify` | keine |
| `show` | `event_id` (Positionsargument) |

Dazu je Befehl die Rückgabewerte. Lies sie aus `cli.py` ab, erfinde sie nicht: 0 bei Erfolg, 1 wenn `verify` einen Befund meldet, 2 bei einem Eingabe- oder Speicherfehler. Nenne, dass `append` genau eine `id` je Event ausgibt und dass derselbe `(source, external_id)` zweimal im selben Aufruf abgewiesen wird.

- [ ] **Schritt 2: `docs/reference/configuration.md`**

Nur eine Variable, aber sie hat drei Eigenschaften, die ein Nachschlagender braucht: `PREVIOUSLY_DSN`, Form `postgresql+psycopg://user:pass@host:5432/datenbank`, und die Rangfolge aus `migrations/dsn.py` — ein ausdrückliches `sqlalchemy.url` schlägt die Umgebungsvariable, ohne beides ein Fehler, der beide nennt.

```{important}
PostgreSQL 15 or newer.
`NULLS NOT DISTINCT` is not optional; see {ref}`concurrency`.
```

- [ ] **Schritt 3: `docs/reference/database-schema.md`**

Drei Tabellen aus `src/previously/storage/schema.py`, als Tabelle je Tabelle: Spalte, Typ, Nullbarkeit, eine Zeile Bedeutung. Dazu die Indexe und Beschränkungen **namentlich**, weil die Namen in Fehlermeldungen auftauchen: `event_pkey`, `event_hash_idx`, `event_prev_hash_idx`, `event_kind_check`, `event_payload_object_check`, `unit_seq_check`, `source_key_pkey`, `source_key_event_id_key`.

- [ ] **Schritt 4: `docs/reference/hash-format.md`**

Die elf Felder des Event-Hashes und die drei des Einheiten-Hashes, abgeschrieben aus `src/previously/core/hashing.py`. Dazu der festgenagelte Vektor als Beispiel — **die Hex-Werte aus `tests/test_hashing.py` abschreiben, nicht neu rechnen.**

```{warning}
Do not recompute these values.
They are pinned in `tests/test_hashing.py`, and recomputing them to make a test pass destroys the proof that the hash is reproducible.
```

- [ ] **Schritt 5: In den Toctree eintragen und bauen**

```shell
make -C docs html
make -C docs vale
```

- [ ] **Schritt 6: Gegen den Code prüfen**

Geh jede Tabelle und jede Liste einmal gegen die Quelle durch und notiere im Bericht, welche Datei du für welche Seite gelesen hast. Eine Reference, die vom Code abweicht, ist schlimmer als keine.

- [ ] **Schritt 7: Commit**

`docs: reference for the command line, configuration, schema and hash format`

---

