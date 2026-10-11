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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import UTC
from typing import Final
from typing import TYPE_CHECKING

import base64
import json
import re
import secrets
import unicodedata


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from collections.abc import Sequence

# 60,000 characters come to about 15,000–20,000 tokens, depending on the
# language, under the 25,000-token cap that Claude Code puts on the output of
# one tool call ({ref}`mcp-open-limits`).
# It has NOT been measured against real mails yet, and until then this number
# is an estimate: the maintainer's run after the merge is where it gets
# measured.
# The figure was set in §5.1 of the unit specification (frozen design record).
PAGE_CHARS: Final = 60_000

# A heading field longer than this is cut, so that a page can always hold the
# heading of one event, whatever the headers of a mail contained. The lists in
# it are capped too, recipients and attachment names alike, with a count of
# the rest: the lines before the first unit then come to a few thousand
# characters at most, and the first unit of a cut event always gets text on
# the page and not only its marker.
_FIELD_CHARS: Final = 200
_MAX_RECIPIENTS: Final = 10
_MAX_ATTACHMENTS: Final = 10
_REASON_CHARS: Final = 500
_ERROR_CHARS: Final = 2_000

# Same length as a real tag and impossible in sanitized text (NUL is a control
# character), so a page is laid out first and the tag is swapped in afterwards.
_TAG_SENTINEL: Final = "\0" * 8

# The 8-bit forms (U+009B CSI, U+009D OSC, U+0090, U+0098, U+009E, U+009F) go
# with their sequence, like the ESC forms; a bare C1 control goes in `sanitize`.
_ESCAPE_SEQUENCE = re.compile(
    r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]"  # CSI
    r"|(?:\x1b\]|\x9d)[^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC, ended by BEL or ST
    r"|(?:\x1b[PX^_]|[\x90\x98\x9e\x9f])[^\x1b]*\x1b\\"  # DCS, SOS, PM, APC
    r"|\x1b[ -/]*[0-~]"  # two-character sequences
)
_LINE_BREAKS = str.maketrans(dict.fromkeys("\n\t\r  ", " "))
CURSOR_REFUSED: Final = "cursor is not valid for these filters"
# The largest integer a result may show: above it, a client that reads JSON
# numbers as doubles rounds, measured on 2026-10-10 ({ref}`mcp-text-block`).
_MAX_SAFE: Final = 2**53 - 1
_EVENT_ID = re.compile(r"(\d+)$")
_TAG_BLOCK = range(0xE0000, 0xE0080)
# Invisible characters outside the category `Cf`, removed by ruling R-6 of the
# 2026-10-11 MCP read access plan, each for the reason beside it.
_INVISIBLE: Final = frozenset(
    [
        # Variation selectors: 16 + 240 = 256 values, a smuggling channel
        # (one byte per invisible character).
        *range(0xFE00, 0xFE10),
        *range(0xE0100, 0xE01F0),
        # Combining grapheme joiner: invisible, changes nothing visible.
        0x034F,
        # Hangul fillers: render as blank but are letters.
        0x115F,
        0x1160,
        0x3164,
        0xFFA0,
    ]
)


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
    """An event shown in full: its heading, its units, and what `get_event`
    adds ({ref}`mcp-tools`).

    `attachments` are the names of the blobs the event names, never their
    content, and `provenance` the pairs of label and value that say where the
    event came from (`found_in`, the Message-ID).
    Both are rendered **inside** the fence: the mail supplied them, so they
    are as foreign as its text (ruling R-8 of the 2026-10-11 MCP read access
    plan).
    """

    head: Head
    units: tuple[tuple[int, str], ...]  # (seq, text)
    attachments: tuple[str, ...] = ()
    provenance: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class WithheldMark:
    uri: str
    reason: str


@dataclass(frozen=True)
class ErasedMark:
    uri: str


@dataclass(frozen=True)
class ErrorMark:
    """The error of one requested item, so that the others of the call stay
    untouched: `label` is the URI of the event, or another short name where
    the URI cannot be written (an id beyond 2^53 may not appear in a result).
    """

    label: str
    message: str


type Item = Shown | WithheldMark | ErasedMark | ErrorMark


@dataclass(frozen=True)
class Page:
    """A laid-out page and what it used up.

    `consumed` is how many of the items reached the page, and `units` holds,
    for each of them in order, the seqs of the units that appeared on it
    (empty for a placeholder or an error).
    A unit cut inside appeared, in part, and is listed.
    The access log is built from these two and not from what was read:
    an item that did not fit was not seen, and belongs to the next page's
    entry (ruling R-9 of the 2026-10-11 MCP read access plan).
    """

    text: str
    next_cursor: str | None
    removed_characters: int
    consumed: int = 0
    units: tuple[tuple[int, ...], ...] = ()


def _removable(char: str) -> bool:
    if char in "\n\t":
        return False
    if ord(char) in _TAG_BLOCK or ord(char) in _INVISIBLE:
        return True
    return unicodedata.category(char) in {"Cc", "Cf", "Cs"}


def sanitize(text: str) -> tuple[str, int]:
    """Remove control and invisible characters; return the text and a count.

    Removed:

    - escape sequences, counted by their length;
    - the C0 and C1 control characters except newline and tab, and lone
      surrogates;
    - everything in the Unicode category `Cf` (zero-width characters,
      bidirectional controls) and the tag block U+E0000–U+E007F;
    - the invisible characters of `_INVISIBLE`.
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


def _heading(head: Head, uri: str, counter: _Counter) -> str:
    parts = [
        uri,
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


def _pointer_note(uri: str, from_unit: int) -> str:
    return f"… truncated — continue with get_event ids=[{_event_id(uri)}] from_unit={from_unit}"


def _cut_unit_note(uri: str, unit: int, following: int | None) -> str:
    """Note for a unit cut inside; it never points back at that unit.

    `get_event` would serve the same cut again, so the pilot serves no more of
    such a unit (ruling R-5 of the 2026-10-11 MCP read access plan).
    """
    note = f"… truncated — the rest of unit {unit} is not served in the pilot"
    if following is None:
        return note
    return f"{note}; continue with get_event ids=[{_event_id(uri)}] from_unit={following}"


def _fence_open() -> str:
    return f"<<<customer-content {_TAG_SENTINEL}>>>"


def _fence_close() -> str:
    return f"<<<end {_TAG_SENTINEL}>>>"


def _shown_block(item: Shown, counter: _Counter, budget: int | None) -> tuple[str, tuple[int, ...]]:
    """Return the block of one event and the seqs of the units in it.

    The caller passes `None` first, to learn the full size, and only passes a
    budget for an event that stands alone on its page; then the block is cut
    to fit, and the seqs are those that made it.
    """
    uri = counter.line(item.head.uri)
    prefix = [_heading(item.head, uri, counter), _fence_open()]
    if item.head.subject is not None:
        prefix.append("Subject: " + counter.line(item.head.subject, 300))
    if item.attachments:
        names = [counter.line(name) for name in item.attachments[:_MAX_ATTACHMENTS]]
        if len(item.attachments) > _MAX_ATTACHMENTS:
            names.append(f"+{len(item.attachments) - _MAX_ATTACHMENTS} more")
        prefix.append("Attachments: " + ", ".join(names))
    prefix.extend(
        f"{counter.line(label)}: {counter.line(value)}" for label, value in item.provenance
    )
    units = [(seq, counter.text(text)) for seq, text in item.units]
    marked = [f"#unit-{seq}\n{text}" for seq, text in units]
    closing = _fence_close()
    full = "\n".join([*prefix, *marked, closing])
    if budget is None or len(full) <= budget:
        return full, tuple(seq for seq, _ in units)

    # Reserve room for the longer of the two notes, with one digit to spare
    # for `seq + 1`.
    width = max((len(str(seq)) for seq, _ in units), default=1) + 1
    wide = int("9" * width)
    note_length = max(
        len(_pointer_note(uri, wide)),
        len(_cut_unit_note(uri, wide, wide)),
    )
    room = budget - len("\n".join([*prefix, closing])) - 1 - note_length - 1
    shown: list[str] = []
    seqs: list[int] = []
    note = _pointer_note(uri, units[0][0] if units else 0)
    for index, ((seq, text), block) in enumerate(zip(units, marked, strict=True)):
        if len(block) + 1 <= room:
            shown.append(block)
            seqs.append(seq)
            room -= len(block) + 1
            continue
        if shown:
            note = _pointer_note(uri, seq)
        else:
            marker = f"#unit-{seq}\n"
            shown.append(marker + text[: max(room - len(marker) - 1, 0)])
            seqs.append(seq)
            following = units[index + 1][0] if index + 1 < len(units) else None
            note = _cut_unit_note(uri, seq, following)
        break
    else:
        note = _pointer_note(uri, units[-1][0] + 1 if units else 0)
    return "\n".join([*prefix, *shown, closing, note]), tuple(seqs)


def _placeholder(item: WithheldMark | ErasedMark | ErrorMark, counter: _Counter) -> str:
    if isinstance(item, ErrorMark):
        label = counter.line(item.label)
        return f"Error: {label} — {counter.line(item.message, _REASON_CHARS)}"
    uri = counter.line(item.uri)
    if isinstance(item, ErasedMark):
        return f"[erased: {uri}]"
    return f"[withheld: {uri} — {counter.line(item.reason, _REASON_CHARS)}]"


def _removed_note(removed: int) -> str:
    if removed == 0:
        return ""
    noun = "character" if removed == 1 else "characters"
    return f" · {removed} control {noun} removed"


def _again(cursor: str) -> str:
    return f"call again with cursor={cursor}"


@dataclass(frozen=True)
class _Frame:
    """What stands around the blocks: the title, the page number, and how
    the footer says where to go on (`next_hint`, given the next cursor)."""

    title: str
    page: int
    next_hint: Callable[[str], str] | None

    def header(self, cursor: str | None, removed: int) -> str:
        text = f"previously · {self.title} · page {self.page}"
        if cursor is not None and self.next_hint is None:
            text += f" · next: c={cursor}"
        return text + _removed_note(removed)

    def footer(self, cursor: str) -> str:
        hint = (self.next_hint or _again)(cursor)
        return f"End of page {self.page}. More results: {hint}"

    def length(self, cursor: str | None, removed: int, blocks: list[str]) -> int:
        """Length of the assembled page, without building it."""
        parts = [len(self.header(cursor, removed))]
        parts.extend(len(block) for block in blocks)
        if cursor is not None:
            parts.append(len(self.footer(cursor)))
        return sum(parts) + 2 * (len(parts) - 1)


def render_page(
    title: str,
    items: Sequence[Item],
    *,
    cursor_for: Callable[[int], str],
    page: int = 1,
    candidates: Iterator[str] | None = None,
    more: bool = False,
    next_hint: Callable[[str], str] | None = None,
) -> Page:
    """Lay out as many `items` as fit in `PAGE_CHARS`.

    `cursor_for(i)` returns the cursor that resumes **after** the item at
    index `i`; it is called with the index of the last item delivered.
    `more` says that further items exist beyond `items`, so that a page that
    holds every one of them still gets a cursor.
    `next_hint(cursor)` words the footer's way on, for a caller whose way on
    is no `cursor` argument (`get_event` names the ids that are left); without
    it the footer says to call again with the cursor, and the header names the
    cursor too.
    `page` is the number of this page, which the caller knows from the cursor
    chain; the total is unknown here, so the indicator reads `page N` and not
    `page N of M`.

    An item that is cut because it alone exceeds the page counts as delivered,
    and the next cursor points behind it, so a later page never starts in the
    middle of an event.
    Cut at a unit boundary, the note points at `get_event` with `from_unit`
    for the rest; cut inside a unit, the note says that the rest of that unit
    is not served in the pilot, and points at the unit after it, if there is
    one (ruling R-5 of the 2026-10-11 MCP read access plan).
    For a cut unit the removed-character count covers the whole unit.
    """
    counter = _Counter()
    frame = _Frame(counter.line(title), page, next_hint)
    blocks: list[str] = []
    shown: list[tuple[int, ...]] = []
    cursor: str | None = None
    for index, item in enumerate(items):
        before = (counter.removed, len(counter.content))
        if isinstance(item, Shown):
            block, seqs = _shown_block(item, counter, None)
        else:
            block, seqs = _placeholder(item, counter), ()
        candidate = [*blocks, block]
        last = index == len(items) - 1 and not more
        next_cursor = None if last else cursor_for(index)
        if frame.length(next_cursor, counter.removed, candidate) <= PAGE_CHARS:
            blocks, cursor = candidate, next_cursor
            shown.append(seqs)
            continue
        if blocks:
            counter.removed, kept = before
            del counter.content[kept:]
            break
        if not isinstance(item, Shown):
            # A placeholder is capped far below the page.
            blocks, cursor = candidate, next_cursor
            shown.append(seqs)
            break
        # The first item alone is over the page: cut it, and count it as
        # delivered.
        with_item = counter.removed
        counter.removed, kept = before
        del counter.content[kept:]
        fixed = frame.length(next_cursor, with_item, [""])
        cut, seqs = _shown_block(item, counter, PAGE_CHARS - fixed)
        blocks, cursor = [cut], next_cursor
        shown.append(seqs)
        break

    body = "\n\n".join(blocks) if blocks else "No results."
    text = frame.header(cursor, counter.removed) + "\n\n" + body
    if cursor is not None:
        text += "\n\n" + frame.footer(cursor)
    tag = draw_tag("\n".join(counter.content), candidates=candidates)
    return Page(
        text=text.replace(_TAG_SENTINEL, tag),
        next_cursor=cursor,
        removed_characters=counter.removed,
        consumed=len(shown),
        units=tuple(shown),
    )


def render_text(title: str, lines: Sequence[str]) -> str:
    """Return a result that holds no customer content, such as the circles of
    the policy: a header, then each line sanitized and kept on one line."""
    counter = _Counter()
    clean_title = counter.line(title)
    body = [counter.line(line, _ERROR_CHARS) for line in lines] or ["No results."]
    return f"previously · {clean_title}{_removed_note(counter.removed)}\n\n" + "\n".join(body)


def render_error(message: str) -> str:
    """Return an error text; callers guarantee it holds no customer content."""
    clean, _ = sanitize(message)
    return "Error: " + _one_line(clean, _ERROR_CHARS)


@dataclass(frozen=True)
class Position:
    """Where a cursor resumes: after the event `after`, on page `page`."""

    after: int
    page: int


def encode_cursor(after: int, filters: Mapping[str, str], *, page: int = 2) -> str:
    """Encode the id of the last item a page consumed, the filters and the
    number of the page the cursor opens as an opaque, URL-safe string.

    The cursor is not sealed: it releases nothing, because every call checks
    access again.
    It names an id and no time.
    The last item can be a withheld or an erased event, whose time is content
    of it like its subject, and a cursor is one base64 decode away from
    whoever holds it; the server looks the time up in the log instead
    (ruling R-13 of the 2026-10-11 MCP read access plan).
    What stays visible is the order of placeholders between visible events,
    which the pages show anyway.
    """
    payload = {"after": after, "filters": dict(filters), "page": page}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= _MAX_SAFE


def decode_position(cursor: str, filters: Mapping[str, str]) -> Position:
    """Decode a cursor; raise `ValueError` if it is malformed or not for `filters`.

    A cursor is the caller's input like any other argument, so whatever it
    holds is checked before it reaches a query: an id and a page number
    inside the range a result may show.
    Whether the id names an observation is the caller's to check, against
    the log.
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        event_id = payload["after"]
        recorded = payload["filters"]
        page = payload.get("page", 2)
        if not _whole(event_id) or not _whole(page) or page < 2:
            raise ValueError("unexpected types")
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        # One fixed message: the parser's own wording would leak internals to
        # whoever echoes it.
        raise ValueError(CURSOR_REFUSED) from error
    if recorded != dict(filters):
        raise ValueError(CURSOR_REFUSED)
    return Position(event_id, page)
