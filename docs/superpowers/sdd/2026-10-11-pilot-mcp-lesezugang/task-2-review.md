## Task 2 review (890de55..fadfdc2)

### Spec Compliance
- ✅ Token only in the two stdout lines of `client add` (cli.py `_cmd_client_add`, after the write). `mint_token` is called only inside `add_client`. The only exception raised after minting is `PolicyRefused` from `set_policy`, and its text names the processor, never the token. The prompt, the replacement notice and the summary line carry name and processor only. `client list` prints name, processor, date. `policy show` is covered by a test.
- ✅ Stored value is the SHA-256 (`Client.token_sha256`, form-checked to 64 lower-case hex digits). Comparison is `hmac.compare_digest` over all clients with no early exit.
- ✅ Supersede: same key `(client, name)` replaces; the old hash is gone from `policy.clients`, so the old token gives `None`. Tested (`test_adding_a_name_again_...`). The CLI says so on stderr before the question. Tested in the order notice, then "n", then nothing written.
- ✅ Revoked client: `_assemble` skips `None` entries, so `clients` is empty and its token matches nothing. Tested. Revoke of an unknown client is refused with nothing written. A revocation of a client whose provider was lifted still works (`not revoked` guard in `refusal`).
- ✅ Undeclared processor: refused in `refusal` before the question (CLI) and again inside `set_policy` (library path). Tested with no action written.
- ✅ R-2: `--model-origin unknown` stores None, with a parametrized test including the control `us`. The cli.md row is updated.
- ✅ T201: re-measured with the pyproject command: 61, matching the comment (sixty-one twice). The 10 added calls in the list: replacement notice, summary, the "nothing written" in add, the "nothing written" in revoke, 2 token lines, revoke summary, event id, and 2 list outputs. That is 10, and 51+10=61.
- ✅ `.vale.ini`: `awk 'NF && /^[a-z]/'` gives 16 lowercase of 24 entries. Both numbers in the comment are now true. The "twenty-four" is stated once, consistent with the count (the older "fifteen" in the history sentence is a dated record, not a claim about today).
- ⚠️ Not re-run: the suite, the mutation claims, and the docs gates. The tutorial output (1329 items, `test_clients.py ..........` = 10, `test_policy` 46 dots) is consistent with the added tests (10 in test_clients, +3 params... plausible), but I did not recount.

### Risk answers
1. Leak paths: none found. The token variable lives in `add_client` and the final two `print`s. No logging, no exception formatting with it.
2. Placeholder: `Client(args.name, args.processor, token_hash(""))` is used only as an argument to `refusal(...)` and never reaches `set_policy` or storage. `add_client` always builds the stored `Client` from the real `token_hash(token)`. Could the placeholder ever be written? No, with the current code. It is, however, the valid hash of the empty string; if it were ever written, `client_for_token(policy, "")` would match it. The `test_a_wrong_token_finds_no_client` asserts `""` finds nothing, which guards the real hash only. Fine as it stands.
3. Supersede/revoke semantics: correct (above).
4. T201: 61, correct.

### Strengths
- Refusal and replacement notice precede the question; library function re-checks, so the CLI pre-check is advisory only.
- Control cases kept beside the assertions (right token finds, hash is found in the stored text, first add claims no replacement).
- Docs, `KINDS`-driven reference test and the typed output were updated in the same commit.

### Issues
- Important (docs claim): `docs/reference/cli.md` says "`add` prints nothing but the two lines". `_cmd_client_add` also prints the summary `client NAME<TAB>processor PROC` to stdout before the question (cli.py, next to `_confirmed`), and the prompt `write? [y/N] ` goes to stdout without `--yes`. The claim is false for every run, and no test pins the summary line. Fix: either say "prints, after the summary and the question, the two lines" in cli.md, or send the summary to stderr like `nothing written`. The T201 comment already counts "the summary", so the code is the intended behavior and the page should follow.
- Minor: the token line prints `args.name` unescaped (`client {args.name}: token ...`) while every other line uses `escape_field`. A name with a control character reaches the terminal raw; `_check_text` may already reject it, which I did not verify. Using the same unescaped name is defensible for the exact wording, but then the name should be validated, not left to chance.
- Minor: `client_for_token` calls `hmac.compare_digest(str, str)`, which raises `TypeError` for a non-ASCII `str`. `token_sha256` is validated as hex on write, but `_parse` reads it with `_text` without that check, so a hand-built or damaged event with a non-ASCII hash would make every lookup raise instead of returning None. Fix: compare `.encode()` bytes, or validate the form in `_parse`. Not reachable through the CLI.
- Minor: `client_rows` raises `KeyError` if a client's event id is not in `read_by_kind("action")` (no known path; an erased event is already not in `clients`).

### Assessment
Approved, with the Important docs fix (one sentence in `docs/reference/cli.md`, or move the summary to stderr) to be made before the whole-branch review. No Critical issues; the binding token rules hold.
