## Task 2: Clients — Prinzipal, Token, Zusage

**Files:** `core/policy.py` (Art `client`), `core/clients.py` (neu), `cli.py` (`client add|revoke|list`), `tests/test_clients.py` (neu), `tests/test_policy.py`, `tests/test_cli.py`, `docs/reference/cli.md`.

**Interfaces — Consumes:** `set_policy`, `read_policy`, `Policy` (Einheit 3). **Produces:**
```python
# core/policy.py
CLIENT: Final = "client"
@dataclass(frozen=True)
class Client:
    name: str; processor: str; token_sha256: str   # hex
# Policy bekommt: clients: Mapping[str, Client]   (ids wie die anderen Arten)

# core/clients.py
def mint_token() -> str: ...                       # secrets.token_urlsafe(32)
def token_hash(token: str) -> str: ...             # sha256 hex
def client_for_token(policy: Policy, token: str) -> Client | None: ...   # hmac.compare_digest je Client
def add_client[Conn](log: LogStore[Conn], name: str, *, processor: str,
                     statement: str, recorded_at: datetime) -> tuple[int, str]: ...  # (event id, token)
```
`set_policy` weist ab: eine Zusage, die nicht deklariert ist (S §2). `client add` für einen vorhandenen Namen löst ab und sagt es vor der Rückfrage (S §2). Die Nutzlast trägt nie den Token, nur `token_sha256`; `client list` zeigt nie den Hash.

- [ ] **Step 1: Tests, die scheitern:** anlegen, ablösen (alter Token → `None`, neuer → Client), widerrufen; unbekannte Zusage abgewiesen, nichts geschrieben; der Token steht in keiner Nutzlast, keiner Ausgabe außer der einen Zeile von `client add` (alle Events durchsucht); `client_for_token` mit falschem Token → `None`; CLI-Wortlaute aus den Global Constraints.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** der Token statt des Hashes in der Nutzlast → rot; Ablösen behält den alten Token gültig → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, sechs Tore, Commit.

---

