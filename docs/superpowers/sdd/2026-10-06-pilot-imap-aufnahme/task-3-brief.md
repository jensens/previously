## Task 3: Wasserzeichen und Konnektor-Vertrag

**Files:** `contract/types.py` (`Watermark`, `Fetched`), `contract/connector.py` (neu), `contract/store.py` (`WatermarkStore`), `storage/schema.py`, `storage/postgres.py`, `src/previously/migrations/versions/0005_watermark.py`, `tests/test_watermark.py` (neu), `tests/test_schema.py`, `docs/reference/database-schema.md`.

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class Watermark:
    connector: str
    position: Mapping[str, str]
    set_at: datetime

@dataclass(frozen=True)
class Fetched:
    raw: bytes
    position: Mapping[str, str]
    found_in: Mapping[str, str]
    internaldate: datetime

class Connector(Protocol):
    name: str
    def fetch(self, since: Watermark | None) -> Iterator[Fetched]: ...

class WatermarkStore[Conn](Protocol):
    def watermark(self, conn: Conn, connector: str) -> Watermark | None: ...
    def set_watermark(self, conn: Conn, mark: Watermark) -> None: ...
```

Tabelle `watermark`: `connector text PRIMARY KEY`, `position jsonb NOT NULL`, `set_at timestamptz NOT NULL`. Migration `0005_watermark`, mit `downgrade`, der sich weigert, wenn die Tabelle Zeilen hat (wie `0004`).

- [ ] **Steps:** Test zuerst (lesen eines fehlenden Wasserzeichens ist `None`; schreiben, lesen, überschreiben; `previously migrate` legt die Tabelle an; die Weigerung von `downgrade` mit Zeilen), rot, umsetzen, grün, Mutation (der `downgrade` ohne Weigerung → Test rot), `database-schema.md`, sechs Tore, Commit.

---

