# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""How the MCP server shows events: one Markdown text block per answer.

Everything here is pure: no database, no clock, no MCP SDK.
The only randomness is the fence tag, drawn with `secrets`.

An answer is a header, then one block per item, then a footer when another
page follows.
A shown event carries a heading written by Previously (URI, time, source,
sender and recipients) and its content inside a fence.
The fence is `<<<customer-content TAG>>>` … `<<<end TAG>>>`, and all fences of
one answer share one TAG.
It is a bet against prompt injection, not a security boundary: a mail cannot
predict the tag, so it cannot close the fence early.

Control and invisible characters are removed **on output only**; the stored
bytes are part of the hash chain and stay as they are.
`sanitize` is the one place that decides what goes, and every string that
reaches the page passes through it, including the title, the reason of a
placeholder and error messages.
"""

from dataclasses import dataclass
from datetime import datetime
from datetime import UTC
from typing import Final
from typing import TYPE_CHECKING

import base64
import binascii
import json
import re
import secrets
import unicodedata


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from collections.abc import Sequence

# 60,000 characters come to about 15,000–20,000 tokens, depending on the
# language, under the 25,000-token cap that Claude Code puts on the output of
# one tool call.
# The figure comes from the unit specification (section 5.1).
# It has NOT been measured against real mails yet: that measurement belongs to
# the acceptance run (section 12, item 2 of the unit specification), and until
# it is done this number is an estimate.
PAGE_CHARS: Final = 60_000

# A heading field longer than this is cut, so that a page can always hold the
# heading of one event, whatever the headers of a mail contained.
_FIELD_CHARS: Final = 200
_MAX_RECIPIENTS: Final = 10
_REASON_CHARS: Final = 500
_ERROR_CHARS: Final = 2_000

# Same length as a real tag and impossible in sanitized text (NUL is a control
# character), so a page is laid out first and the tag is swapped in afterwards.
_TAG_SENTINEL: Final = "\0" * 8

_ESCAPE_SEQUENCE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC, ended by BEL or ST
    r"|\x1b[PX^_][^\x1b]*\x1b\\"  # DCS, SOS, PM, APC
    r"|\x1b[ -/]*[0-~]"  # two-character sequences
)
_LINE_BREAKS = str.maketrans(dict.fromkeys("\n\t\r  ", " "))
_EVENT_ID = re.compile(r"(\d+)$")
_TAG_BLOCK = range(0xE0000, 0xE0080)


@dataclass(frozen=True)
class Head:
    uri: str
    occurred_at: datetime
    source: str
    sender: str | None
    recipients: tuple[str, ...]
    subject: str | None


@dataclass(frozen=True)
class Shown:
    head: Head
    units: tuple[tuple[int, str], ...]  # (seq, text)


@dataclass(frozen=True)
class WithheldMark:
    uri: str
    reason: str


@dataclass(frozen=True)
class ErasedMark:
    uri: str


type Item = Shown | WithheldMark | ErasedMark


@dataclass(frozen=True)
class Page:
    text: str
    next_cursor: str | None
    removed_characters: int


def _removable(char: str) -> bool:
    if char in "\n\t":
        return False
    return unicodedata.category(char) in {"Cc", "Cf", "Cs"} or ord(char) in _TAG_BLOCK


def sanitize(text: str) -> tuple[str, int]:
    """Remove control and invisible characters; return the text and a count.

    Removed: escape sequences (counted by their length), the C0 and C1 control
    characters except newline and tab, everything in the Unicode category `Cf`
    (zero-width characters, bidirectional controls), and the tag block
    U+E0000–U+E007F.
    """
    removed = 0

    def drop_sequence(match: re.Match[str]) -> str:
        nonlocal removed
        removed += len(match.group())
        return ""

    without_sequences = _ESCAPE_SEQUENCE.sub(drop_sequence, text)
    kept = [char for char in without_sequences if not _removable(char)]
    removed += len(without_sequences) - len(kept)
    return "".join(kept), removed


def draw_tag(content: str, *, candidates: Iterator[str] | None = None) -> str:
    """Return a fence tag that does not occur in `content`.

    `candidates` exists so that the redraw can be tested: with the default,
    tags come from `secrets.token_hex(4)`, and a collision cannot be provoked
    on demand.
    """
    lowered = content.lower()
    source = candidates if candidates is not None else _random_tags()
    for tag in source:
        if tag not in lowered:
            return tag
    raise ValueError("no candidate tag is free of the content")


def _random_tags() -> Iterator[str]:
    while True:
        yield secrets.token_hex(4)


class _Counter:
    """Collects the removed-character count and the content of one page."""

    def __init__(self) -> None:
        self.removed = 0
        self.content: list[str] = []

    def text(self, raw: str) -> str:
        clean, removed = sanitize(raw)
        self.removed += removed
        self.content.append(clean)
        return clean

    def line(self, raw: str, limit: int = _FIELD_CHARS) -> str:
        return _one_line(self.text(raw), limit)


def _one_line(clean: str, limit: int) -> str:
    line = clean.translate(_LINE_BREAKS).strip()
    if len(line) > limit:
        return line[: limit - 1] + "…"
    return line


def _time(moment: datetime) -> str:
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC)
    return moment.strftime("%Y-%m-%d %H:%M")


def _heading(head: Head, counter: _Counter) -> str:
    parts = [
        counter.line(head.uri),
        _time(head.occurred_at),
        counter.line(head.source),
    ]
    recipients = [counter.line(name) for name in head.recipients[:_MAX_RECIPIENTS]]
    if len(head.recipients) > _MAX_RECIPIENTS:
        recipients.append(f"+{len(head.recipients) - _MAX_RECIPIENTS} more")
    if head.sender is not None and recipients:
        parts.append(f"{counter.line(head.sender)} → {', '.join(recipients)}")
    elif head.sender is not None:
        parts.append(counter.line(head.sender))
    elif recipients:
        parts.append(f"unknown → {', '.join(recipients)}")
    return "### " + " · ".join(parts)


def _event_id(uri: str) -> str:
    match = _EVENT_ID.search(uri)
    return match.group(1) if match else uri


def _truncation_note(uri: str, from_unit: int) -> str:
    return f"… truncated — continue with get_event ids=[{_event_id(uri)}] from_unit={from_unit}"


def _fence_open() -> str:
    return f"<<<customer-content {_TAG_SENTINEL}>>>"


def _fence_close() -> str:
    return f"<<<end {_TAG_SENTINEL}>>>"


def _shown_block(item: Shown, counter: _Counter, budget: int | None) -> tuple[str, bool]:
    """Return the block of one event and whether it was cut to fit `budget`.

    The caller passes `None` first, to learn the full size, and only passes a
    budget for an event that stands alone on its page.
    """
    heading = _heading(item.head, counter)
    prefix = [heading, _fence_open()]
    if item.head.subject is not None:
        prefix.append("Subject: " + counter.line(item.head.subject, 300))
    units = [(seq, counter.text(text)) for seq, text in item.units]
    marked = [f"[unit {seq}]\n{text}" for seq, text in units]
    closing = _fence_close()
    full = "\n".join([*prefix, *marked, closing])
    if budget is None or len(full) <= budget:
        return full, False

    seq_width = max((len(str(seq)) for seq, _ in units), default=1)
    note_length = len(_truncation_note(item.head.uri, 0)) + seq_width
    room = budget - len("\n".join([*prefix, closing])) - 1 - note_length - 1
    shown: list[str] = []
    from_unit = units[0][0] if units else 0
    for (seq, text), block in zip(units, marked, strict=True):
        if len(block) + 1 <= room:
            shown.append(block)
            room -= len(block) + 1
            continue
        from_unit = seq
        if not shown:
            marker = f"[unit {seq}]\n"
            shown.append(marker + text[: max(room - len(marker) - 1, 0)])
        break
    else:
        from_unit = units[-1][0] + 1 if units else 0
    note = _truncation_note(item.head.uri, from_unit)
    return "\n".join([*prefix, *shown, closing, note]), True


def _placeholder(item: WithheldMark | ErasedMark, counter: _Counter) -> str:
    uri = counter.line(item.uri)
    if isinstance(item, ErasedMark):
        return f"[erased: {uri}]"
    return f"[withheld: {uri} — {counter.line(item.reason, _REASON_CHARS)}]"


def _removed_note(removed: int) -> str:
    if removed == 0:
        return ""
    noun = "character" if removed == 1 else "characters"
    return f" · {removed} control {noun} removed"


def _header(title: str, page: int, cursor: str | None, removed: int) -> str:
    text = f"previously · {title} · page {page}"
    if cursor is not None:
        text += f" · next: c={cursor}"
    return text + _removed_note(removed)


def _footer(cursor: str) -> str:
    return f"More results: call again with cursor={cursor}"


def _length(title: str, page: int, cursor: str | None, removed: int, blocks: list[str]) -> int:
    """Length of the assembled page, without building it."""
    parts = [len(_header(title, page, cursor, removed))]
    parts.extend(len(block) for block in blocks)
    if cursor is not None:
        parts.append(len(_footer(cursor)))
    total = sum(parts) + 2 * (len(parts) - 1)
    return total


def render_page(
    title: str,
    items: Sequence[Item],
    *,
    cursor_for: Callable[[int], str],
    page: int = 1,
) -> Page:
    """Lay out as many `items` as fit in `PAGE_CHARS`.

    `cursor_for(i)` returns the cursor that resumes **after** the item at
    index `i`; it is called with the index of the last item delivered.
    `page` is the number of this page, which the caller knows from the cursor
    chain; the total is unknown here, so the indicator reads `page N` and not
    `page N of M`.

    An item that is cut because it alone exceeds the page counts as delivered:
    the next cursor points behind it, and the rest of it is reachable through
    `get_event` with `from_unit`.
    So a later page never starts in the middle of an event.
    For a cut unit the removed-character count covers the whole unit.
    """
    counter = _Counter()
    clean_title = counter.line(title)
    blocks: list[str] = []
    cursor: str | None = None
    for index, item in enumerate(items):
        before = (counter.removed, len(counter.content))
        if isinstance(item, Shown):
            block, _ = _shown_block(item, counter, None)
        else:
            block = _placeholder(item, counter)
        candidate = [*blocks, block]
        last = index == len(items) - 1
        next_cursor = None if last else cursor_for(index)
        if _length(clean_title, page, next_cursor, counter.removed, candidate) <= PAGE_CHARS:
            blocks, cursor = candidate, next_cursor
            continue
        if blocks:
            counter.removed, kept = before
            del counter.content[kept:]
            break
        if not isinstance(item, Shown):
            # A placeholder is capped far below the page.
            blocks, cursor = candidate, next_cursor
            break
        # The first item alone is over the page: cut it, and count it as
        # delivered.
        with_item = counter.removed
        counter.removed, kept = before
        del counter.content[kept:]
        fixed = _length(clean_title, page, next_cursor, with_item, [""])
        cut, _ = _shown_block(item, counter, PAGE_CHARS - fixed)
        blocks, cursor = [cut], next_cursor
        break
    else:
        cursor = None

    body = "\n\n".join(blocks) if blocks else "No results."
    text = _header(clean_title, page, cursor, counter.removed) + "\n\n" + body
    if cursor is not None:
        text += "\n\n" + _footer(cursor)
    tag = draw_tag("\n".join(counter.content))
    return Page(
        text=text.replace(_TAG_SENTINEL, tag),
        next_cursor=cursor,
        removed_characters=counter.removed,
    )


def render_error(message: str) -> str:
    """Return an error text; callers guarantee it holds no customer content."""
    clean, _ = sanitize(message)
    return "Error: " + _one_line(clean, _ERROR_CHARS)


def encode_cursor(after: tuple[datetime, int], filters: Mapping[str, str]) -> str:
    """Encode the last position and the filters as an opaque, URL-safe string.

    The cursor is not sealed: it releases nothing, because every call checks
    access again.
    """
    payload = {
        "after": [after[0].isoformat(), after[1]],
        "filters": dict(filters),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, filters: Mapping[str, str]) -> tuple[datetime, int]:
    """Decode a cursor; raise `ValueError` if it is malformed or not for `filters`."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        moment, event_id = payload["after"]
        recorded = payload["filters"]
        if (
            not isinstance(moment, str)
            or not isinstance(event_id, int)
            or isinstance(event_id, bool)
        ):
            raise ValueError("malformed cursor")
        after = (datetime.fromisoformat(moment), event_id)
    except (KeyError, TypeError, binascii.Error) as error:
        raise ValueError("malformed cursor") from error
    if recorded != dict(filters):
        raise ValueError("cursor belongs to a different query")
    return after
