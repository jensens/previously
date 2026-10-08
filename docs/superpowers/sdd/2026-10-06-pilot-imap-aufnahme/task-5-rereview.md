# Task 5 re-review: fix round 1 (e26551d..bfe301a)

Reviewer: independent, read-only on the tree. Mutations ran on a scratch copy of `src` put ahead on `PYTHONPATH`, in the session scratchpad; the checkout was not touched.

## Finding Verdicts

**I1: ADDRESSED.**
- `src/previously/connectors/imap.py:~282` `parse_internaldate` is public, and the connector calls it (`imap.py:~199`).
- `tests/test_imap.py:~436-456` pins the value of five RFC 3501 strings, each compared with `==` and with `utcoffset()`:
  - the space-padded day with `+0200`;
  - January with `-0230`;
  - December with `+0545`;
  - 29 Feb in a leap year;
  - `OCT` in capitals.
- `tests/test_imap.py:~459-473` refuses eight texts that name no moment: German months `Okt` and `Mai`, 30 Feb, hour 25, zone `+2400`, no zone, ISO form, empty.
- `tests/test_imap.py:~498-510` is the end-to-end `APPEND` with `05-Jan-2026 23:30:00 -0230`, expecting `2026-01-06 02:00:00+00:00`, through the new `MailServer.append_dated` (`tests/mailserver.py:~101`).
- Mutations measured, control first:
  - Unmutated: the 16 INTERNALDATE tests pass.
  - Month table `start=0`: 7 failed, including the GreenMail case and the Jan case.
  - Zone sign swapped: 4 failed (all the unit value cases with a non-zero zone). The end-to-end case stays green there, as the previous review said it would; the unit cases carry the sign.
- Case-insensitive months are correct: the regex takes `[A-Za-z]{3}`, the lookup is `month.capitalize()`, and `OCT` becomes `Oct`. ABNF quoted strings match without regard to case (RFC 5234), which is what the new comment says. A three-letter ASCII token that is not a month (`Okt`) still gives `None`, and the test holds it.

**M1: ADDRESSED.**
- `tests/test_imap.py:~513-524` creates, fills and fetches the folders `Kunde "Müller"` and `Back\slash Ä`.
- `tests/mailserver.py:~34` has its own `quoted` with the escaping, written independently of the connector's `_quoted`, so the set-up does not depend on the code under test.
- Mutation `_quoted` without escaping: both parametrisations fail, with GreenMail's "Invalid escaped character in quote". Control (unmutated): green.

**M4: ADDRESSED.** `imap.py:~174-177`: "GreenMail refuses it inside parentheses" matches the spec and the earlier measurement.

**M5: ADDRESSED.** `imap.py:~188-194` says the error's `object` is the one argument that would not encode and that `imaplib` encodes each on its own. Checked against CPython 3.14.3 `imaplib.py` lines 1107-1111: each `str` argument goes through `bytes(arg, self._encoding)` on its own, with ASCII as the encoding.

**M6: ADDRESSED.** `tests/test_imap.py:~548-552` now says "over three runs … 7301 to 7303 bytes … 3575 to 3577 … moves by a byte or two per run". That matches the 3577/7303 of the implementer and the 3575/7301 and 3576/7302 of the earlier review. The limit of 5000 is unchanged.

**M7: ADDRESSED.**
- `docs/reference/configuration.md:~105`: the table row now says "the full name of the folder on the server, in plain characters".
- `configuration.md:~42-45` covers the nested folder: the parent names plus the hierarchy delimiter, with `Kunden.Müller` and `Kunden/Müller`, where the delimiter is found (the `LIST` answer), and that a mail client shows only the last part.
- It also says the setting is held in plain characters and never as modified UTF-7.
- One quadrant (reference) is kept, and `make -C docs vale` gives 0 errors, 0 warnings.

M2, M3, M8 stay named, as agreed.

## New Breakage in the Fix Diff

None.

Checked:
- `ruff check src tests` is clean and `ruff format --check src tests` is clean.
- pyright on `imap.py`, `test_imap.py` and `mailserver.py` gives 0 errors.
- `test_imap.py` collects 32 tests (16 plus 16 new), and the tutorial block says `collected 1042` (1026 plus 16) with `test_imap.py` at 32 dots, so the typed output agrees with the tree.
- The diff adds no `noqa` and no `type: ignore`.
- No test reaches a private name: `parse_internaldate` is public.
- I did not run the whole suite or the other documentation commands (html, linkcheck).

## Out-of-Scope Observations

- `parse_internaldate` accepts a zone with minutes of 60 or more (`+0560` reads as +06:00), because only the whole offset is range-checked. That is pre-existing, and a server does not write it. Named only.

## Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage
