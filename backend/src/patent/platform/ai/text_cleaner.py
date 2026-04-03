"""
Clean fixed-column line breaks from JPO Office Action text.

JPO documents (PDF copy-paste or plain-text exports) contain hard line breaks
every 36 characters. This module merges those mid-sentence breaks while
preserving intentional paragraph structure.

Rules (derived by testing against Japio 改行削除ツール):
  - Lines ≥ 36 characters are fixed-column breaks → merged with next line
  - Lines < 36 characters are natural line endings → newline preserved
  - Exception: if the NEXT line starts with 　 (U+3000, full-width space),
    the newline is always kept (start of an indented paragraph)
  - Blank lines are paragraph separators → always preserved
  - Lines containing 続葉有 are page-break markers → removed along with
    the following page header (統葉/続葉) and its surrounding blanks
"""

import re

COLUMN_WIDTH = 36  # JPO document fixed column width in characters

_PAGE_HEADER = re.compile(r'[統続]\s*葉')

# Standalone page-number line  (entire stripped line must match):
#   P.  2 / P. 1    – Western style
#   ２/  ２/５      – full-width digit(s) + slash (J-PlatPat)
#   ７Ｅ  3B        – digit + letter code (J-PlatPat)
_PAGE_NUMBER = re.compile(
    r'P\.\s*\d+'                        # P.  N
    r'|[0-9０-９]{1,3}'                 # digit(s)
    r'(?:[/／][0-9０-９]{0,3})?'        # optional /M
    r'[A-Za-zＡ-Ｚａ-ｚ]?'            # optional letter suffix
)

# Page-number prefix embedded at the start of a continuation line:
#   e.g. stripped = "4/ラグメント。"  →  prefix="4/", continuation="ラグメント。"
# The character after N/ must be a non-digit (actual text, not another number).
_PAGE_PREFIX = re.compile(r'^[0-9０-９]{1,3}[/／](?![0-9０-９])')


def _remove_page_breaks(lines: list[str]) -> list[str]:
    """
    Remove 続葉有 page-break sections.

    Looks for the 統葉/続葉 continuation header within 30 lines after 続葉有.
    If found: removes from the 続葉有 line through the page header and any
    trailing blank lines.  If not found (simple / synthetic input): removes
    only the 続葉有 line itself.
    """
    result = []
    i = 0
    while i < len(lines):
        if '続葉有' in lines[i]:
            # Scan ahead for the page continuation header
            header_idx = None
            for j in range(i + 1, min(i + 30, len(lines))):
                if _PAGE_HEADER.search(lines[j].strip()):
                    header_idx = j
                    break

            if header_idx is not None:
                # Skip everything from 続葉有 through the page header
                i = header_idx + 1
                # Skip any blank lines that follow the header
                while i < len(lines) and not lines[i].strip():
                    i += 1
            else:
                # No page header found – skip only the 続葉有 line
                i += 1
            continue

        result.append(lines[i])
        i += 1
    return result


def _remove_page_numbers(lines: list[str]) -> list[str]:
    """
    Remove page-number separators in two forms:

    1. Standalone line  – entire stripped content is a page number:
          "                P.  2"   "２/"   "７Ｅ"
       → drop the line; also drop the preceding blank (avoid double-blanks).

    2. Embedded prefix  – stripped content starts with N/ followed by text:
          "                                    4/ラグメント。"
       → strip N/ prefix, keep the continuation text, and remove the blank
         that separated it from the previous content so the two pieces merge.
    """
    result: list[str] = []
    for line in lines:
        stripped = line.strip()

        if not stripped:
            result.append(line)
            continue

        # Case 1: whole line is a page number
        if _PAGE_NUMBER.fullmatch(stripped):
            # Drop preceding blank to avoid leaving an orphan blank line
            if result and not result[-1].strip():
                result.pop()
            continue

        # Case 2: line starts with N/ + actual continuation text
        m = _PAGE_PREFIX.match(stripped)
        if m:
            continuation = stripped[m.end():]
            # Remove the blank separator before this line so the continuation
            # attaches to the previous content (e.g. "フ" + "ラグメント。")
            if result and not result[-1].strip():
                result.pop()
            # Append the continuation to the last line (if any), or start fresh
            if result:
                result[-1] = result[-1].rstrip() + continuation
            else:
                result.append(continuation)
            continue

        result.append(line)
    return result


def clean_linebreaks(text: str) -> str:
    """
    Remove fixed-column newlines from JPO OA text.

    Algorithm:
      1. Strip 続葉有 page-break sections.
      2. For each line:
         - Blank → flush buffer and emit paragraph separator.
         - len(line) >= COLUMN_WIDTH and next non-blank does NOT start with
           → hard-wrap: concatenate without newline.
         - Otherwise → natural ending: flush buffer.
    """
    lines = text.splitlines()
    lines = _remove_page_breaks(lines)
    lines = _remove_page_numbers(lines)

    out: list[str] = []
    buf = ''

    for i, raw in enumerate(lines):
        line = raw.rstrip()

        if not line.strip():
            if buf:
                out.append(buf)
                buf = ''
            out.append('')
            continue

        # Peek at the next non-blank line to check for paragraph indent
        next_starts_indent = False
        for j in range(i + 1, len(lines)):
            if lines[j].strip():
                next_starts_indent = lines[j].startswith('\u3000')  #
                break

        if len(line) >= COLUMN_WIDTH and not next_starts_indent:
            # Fixed-column hard wrap: concatenate into current paragraph
            buf += line
        else:
            # Natural line ending: flush
            buf += line
            out.append(buf)
            buf = ''

    if buf:
        out.append(buf)

    # Collapse 3+ blank lines to 2
    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(out))
    return result.strip()


def normalize_app_number(raw: str) -> str:
    """
    Convert application number to JPO API format (digits only, zero-padded).

    Examples:
      特願2020-123456  →  2020123456   (wait: JPO API uses 7-digit serial)
      特願2020-1234    →  2020001234   (pad serial to 6 digits? check API docs)
      2020-123456      →  2020123456
    """
    # Strip Japanese prefix
    s = re.sub(r'^特願', '', raw.strip())
    # Remove spaces
    s = s.replace(' ', '').replace('\u3000', '')
    # Extract year and serial
    m = re.match(r'(\d{4})[－\-](\d+)', s)
    if m:
        year, serial = m.group(1), m.group(2)
        return f"{year}{serial.zfill(6)}"
    # Already digits only
    return re.sub(r'\D', '', s)
