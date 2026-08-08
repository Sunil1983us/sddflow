"""Convert Confluence Storage Format (XHTML) to Markdown.

Best-effort round-trip for SDD documents. Handles the same subset that
md_to_cf.py produces: headings, bold, italic, inline code, fenced code
macros, unordered/ordered lists, paragraphs, hr, links, and tables.
"""

from __future__ import annotations

import html
import re


def cf_to_md(storage_xml: str) -> str:
    """Return a Markdown string approximating the Confluence storage XML."""
    text = storage_xml

    # Stash raw HTML comments (e.g. specify-doc.prompt.md's
    # "<!-- security-sign-off: ... -->" marker) into placeholders before
    # any other processing, and restore them literally at the very end.
    # Without this, "Strip any remaining HTML tags" near the end of this
    # pipeline deletes them outright -- <!-- ... --> matches that step's
    # <[^>]+> pattern exactly like a real tag would, since it has no
    # notion of comments vs. tags. Placed first so every intermediate
    # regex pass (including the ac:* stripping right below) can't touch
    # a comment's contents either, on the same principle -- md_to_cf.py
    # (the push side) has the matching fix so a round-trip preserves
    # these end to end rather than mangling them on the way in and
    # losing them on the way out.
    _comments: list[str] = []

    def _stash_comment(m: re.Match) -> str:
        _comments.append(m.group(0))
        return f"\x00SDD-COMMENT-{len(_comments) - 1}\x00"

    text = re.sub(r"<!--.*?-->", _stash_comment, text, flags=re.DOTALL)

    # Confluence code macros → fenced code blocks
    text = re.sub(
        r'<ac:structured-macro ac:name="code">\s*'
        r'<ac:parameter ac:name="language">([^<]*)</ac:parameter>\s*'
        r"<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>\s*"
        r"</ac:structured-macro>",
        lambda m: (
            f"```{m.group(1) if m.group(1) not in ('', 'none') else ''}\n"
            f"{m.group(2)}\n"
            f"```"
        ),
        text,
        flags=re.DOTALL,
    )

    # Strip remaining ac:* elements (Confluence macros we don't handle,
    # e.g. <ac:image> diagram references -- local-svg mode's diagram
    # attachment reference has no markdown equivalent, so it's dropped
    # here rather than left as unresolvable raw XML).
    #
    # The closing tag MUST be captured via a backreference to the same
    # tag name as the opening one -- a bare `<ac:[^>]+>.*?</ac:[^>]+>`
    # (no backreference) pairs an opening tag with the next ac: closing
    # tag of ANY name, not necessarily its own. Confirmed as a real,
    # severe data-loss bug reported by a user: a page with an <ac:image>
    # diagram followed later by any other unhandled/nested ac: element
    # (e.g. a structured-macro's own nested <ac:rich-text-body>, or a
    # second macro further down the page) had everything between the
    # <ac:image> and that unrelated LATER closing tag silently deleted --
    # in their case, 6 tables and an entire numbered section. The
    # backreference guarantees this only ever spans exactly one element's
    # own content, never past it into unrelated markup.
    text = re.sub(r"<ac:[^>]+/>", "", text)
    text = re.sub(r"<ac:([a-zA-Z-]+)[^>]*>.*?</ac:\1>", "", text, flags=re.DOTALL)

    # Headings (h1–h6)
    for lvl in range(6, 0, -1):

        def _heading_repl(m: re.Match, level: int = lvl) -> str:
            return "#" * level + " " + _plain(m.group(1))

        text = re.sub(
            rf"<h{lvl}>(.*?)</h{lvl}>",
            _heading_repl,
            text,
            flags=re.DOTALL,
        )

    # Strong / bold
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)

    # Emphasis / italic
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)

    # Links
    text = re.sub(
        r'<a href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL
    )

    # Tables -- round-trip counterpart to _render_table() in md_to_cf.py.
    # Must run after the bold/italic/inline-code/link passes above (so
    # cell content is already markdown by the time we extract it) and
    # before the generic tag-stripping below, which has no notion of
    # rows or columns and would otherwise concatenate every cell in the
    # table into one run-on line with no delimiters at all.
    text = re.sub(r"<table>.*?</table>", _table_to_md, text, flags=re.DOTALL)

    # Horizontal rule
    text = re.sub(r"<hr\s*/?>", "\n---", text)

    # Lists — collapse open/close wrappers, convert <li> to bullets
    text = re.sub(r"</?[uo]l[^>]*>", "", text)
    text = re.sub(r"<li>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL)

    # Paragraphs — unwrap, keep blank line separation
    text = re.sub(r"<p>(.*?)</p>", r"\n\1\n", text, flags=re.DOTALL)

    # Unescape HTML entities introduced by md_to_storage
    text = html.unescape(text)

    # Strip any remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Restore stashed HTML comments
    for i, comment in enumerate(_comments):
        text = text.replace(f"\x00SDD-COMMENT-{i}\x00", comment)

    return text.strip()


def _plain(html_fragment: str) -> str:
    """Strip all tags from an HTML snippet (used for heading text)."""
    return re.sub(r"<[^>]+>", "", html_fragment).strip()


_CELL_RE = re.compile(
    r'<t[hd](?:\s+style="text-align:(left|center|right)")?[^>]*>(.*?)</t[hd]>',
    re.DOTALL,
)
_ALIGN_SEP = {"left": ":---", "center": ":---:", "right": "---:"}


def _table_to_md(m: re.Match) -> str:
    """Convert one <table>...</table> match to a GFM pipe table.

    Mirrors md_to_cf.py's _render_table() shape exactly (<tr> rows of
    <th>/<td>, first row is the header, optional
    style="text-align:..." for alignment) so the round trip is lossless
    for anything this CLI itself produced."""
    row_htmls = re.findall(r"<tr>(.*?)</tr>", m.group(0), flags=re.DOTALL)
    if not row_htmls:
        return ""

    def _cell_text(raw: str) -> str:
        # Collapse any stray newlines (a cell must stay on one line in a
        # GFM table) and escape literal pipes so they aren't mistaken
        # for a column boundary -- the inverse of _split_table_row()'s
        # unescape on the push side.
        return re.sub(r"\s+", " ", raw).strip().replace("|", r"\|")

    rows: list[list[str]] = []
    aligns: list[str] = []
    for i, row_html in enumerate(row_htmls):
        cells = _CELL_RE.findall(row_html)
        if i == 0:
            aligns = [a for a, _text in cells]
        rows.append([_cell_text(text) for _align, text in cells])

    if not rows or not rows[0]:
        return ""

    header, body = rows[0], rows[1:]
    sep = [
        _ALIGN_SEP.get(aligns[i], "---") if i < len(aligns) else "---"
        for i in range(len(header))
    ]

    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(sep) + "|"]
    for row in body:
        row = row + [""] * max(0, len(header) - len(row))
        row = row[: len(header)]
        lines.append("| " + " | ".join(row) + " |")

    return "\n\n" + "\n".join(lines) + "\n\n"
