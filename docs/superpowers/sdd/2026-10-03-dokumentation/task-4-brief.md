## Task 4: How-to guides

**Files:**
- Create: `docs/how-to/verify-the-chain.md`, `docs/how-to/restore-from-a-backup.md`, `docs/how-to/add-a-migration.md`
- Modify: `docs/how-to/index.md`

- [ ] **Schritt 1: `verify-the-chain.md`**

Titel nennt das Ziel: „How to check the chain in operation". Öffnet mit „This guide shows you how to…". Inhalt: `previously verify` aufrufen, den Rückgabewert auswerten (0 heißt intakt, 1 heißt Befund), die Befundtexte nachschlagen, und was **nicht** gedeckt ist — mit `{ref}` auf die Explanation, nicht mit einer Erklärung an dieser Stelle.

- [ ] **Schritt 2: `restore-from-a-backup.md`**

```{important}
A restore that was never rehearsed is not a backup.
```

Inhalt: wiederherstellen, dann **`previously verify` gegen den wiederhergestellten Bestand** laufen lassen — das ist der Punkt, der diese Wiederherstellung von einer gewöhnlichen unterscheidet, denn die Kette prüft den Inhalt und nicht nur, dass Postgres startet.

Die Passphrase: ohne sie ist der Restore unmöglich. Verweise auf die Reference für die Konfiguration und auf die Explanation für den Grund.

- [ ] **Schritt 3: `add-a-migration.md`**

Inhalt: `uv run alembic revision -m …`, die Revision schreiben, `uv run alembic upgrade head`, und der Test, der jeden in `metadata` erklärten Index gegen `pg_indexes` hält. Nenne ausdrücklich, dass `postgresql_nulls_not_distinct=True` in **beiden** Orten stehen muss (Schema und Migration), weil ein `autogenerate` den Index sonst still fallen lässt.

- [ ] **Schritt 4: Die drei Seiten in den Toctree von `docs/how-to/index.md` eintragen**

Nicht vergessen: das Tor fährt `sphinx-build -W`, und eine Seite, die in
keinem Toctree steht, erzeugt „document isn't included in any toctree" — unter
`-W` also einen Fehlschlag.

- [ ] **Schritt 5: Tore und Commit**

`docs: how-to guides for verification, restore and migrations`

---

