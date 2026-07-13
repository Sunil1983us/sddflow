"""Convert Markdown to Confluence Storage Format (XHTML).

Handles the subset of Markdown used in SDD documents:
  headings, **bold**, *italic*, `inline code`, fenced code blocks,
  unordered lists (- item), ordered lists (1. item), paragraphs, ---
"""
from __future__ import annotations
import re
import html

from sdd.utils.integrations import DiagramsConfig

# One attachment: (filename, raw bytes, media type) -- returned alongside
# the HTML by md_to_storage() when diagrams.mode == "local-svg" so the
# caller can upload each rendered diagram to the page after upserting it.
Attachment = tuple[str, bytes, str]


def md_to_storage(md: str, diagrams: DiagramsConfig | None = None) -> tuple[str, list[Attachment]]:
    """Convert Markdown to Confluence storage-format XHTML.

    Returns (html, attachments). attachments is always [] except in
    diagrams.mode == "local-svg", where each successfully-rendered
    ```mermaid fence contributes one (filename, svg_bytes, media_type)
    entry the caller must upload as a page attachment after upsert_page()
    -- the returned html already references that filename via
    <ac:image><ri:attachment ri:filename="...">, but Confluence won't
    resolve it to an actual image until the attachment exists."""
    diagrams = diagrams or DiagramsConfig()
    attachments: list[Attachment] = []
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_list: str | None = None    # "ul" | "ol" | None
    para_buf: list[str] = []

    def flush_para() -> None:
        nonlocal para_buf
        if para_buf:
            text = " ".join(para_buf).strip()
            if text:
                out.append(f"<p>{_inline(text)}</p>")
            para_buf = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        fence = re.match(r'^```(\w*)', line)
        if fence:
            flush_para()
            flush_list()
            lang = fence.group(1) or "none"
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            out.append(_render_fence(lang, "\n".join(code_lines), diagrams, attachments))
            i += 1
            continue

        # Headings
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            flush_para()
            flush_list()
            level = min(len(m.group(1)), 6)
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^-{3,}\s*$', line):
            flush_para()
            flush_list()
            out.append("<hr/>")
            i += 1
            continue

        # Unordered list
        m = re.match(r'^[-*]\s+(.*)', line)
        if m:
            flush_para()
            if in_list != "ul":
                flush_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r'^\d+\.\s+(.*)', line)
        if m:
            flush_para()
            if in_list != "ol":
                flush_list()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # GFM pipe table: a "| cell | cell |" row followed by a
        # "|---|---|" separator row
        if line.strip().startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            flush_para()
            flush_list()
            header = _split_table_row(line)
            align = _table_alignment(lines[i + 1])
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_table_row(lines[i]))
                i += 1
            out.append(_render_table(header, rows, align))
            continue

        # Blank line
        if not line.strip():
            flush_para()
            flush_list()
            i += 1
            continue

        # Paragraph line
        flush_list()
        para_buf.append(line)
        i += 1

    flush_para()
    flush_list()
    return "\n".join(out), attachments


def _render_fence(lang: str, code: str, diagrams: DiagramsConfig,
                   attachments: list[Attachment]) -> str:
    """Render one fenced code block. A ```mermaid or ```plantuml fence
    routes through the matching installed Confluence app's macro when
    diagrams.mode selects it and a macro name is configured, or through
    a locally-rendered SVG image when diagrams.mode == "local-svg"
    (appending to `attachments` as a side effect). Every other fence --
    and a diagram fence whose render/macro path fails or isn't
    configured -- falls back to Confluence's built-in "code" macro,
    which is a syntax-highlighted text block, not a rendered diagram.
    Confluence has no native diagram renderer, so without one of these
    modes configured, a ```mermaid fence always shows as text."""
    if lang == "mermaid" and diagrams.mode == "mermaid-app" and diagrams.mermaid_app_macro:
        return _diagram_macro(diagrams.mermaid_app_macro, code)
    if lang == "plantuml" and diagrams.mode == "plantuml-macro" and diagrams.plantuml_macro:
        return _diagram_macro(diagrams.plantuml_macro, code)
    if lang == "mermaid" and diagrams.mode == "local-svg":
        rendered = _render_local_svg(code, attachments)
        if rendered is not None:
            return rendered
    escaped = html.escape(code)
    return (
        f'<ac:structured-macro ac:name="code">'
        f'<ac:parameter ac:name="language">{lang or "none"}</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[{escaped}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )


def _render_local_svg(code: str, attachments: list[Attachment]) -> str | None:
    """Render Mermaid source to SVG locally and queue it as a page
    attachment. Returns None (never raises) on any failure -- a missing
    optional dependency, invalid diagram source, or renderer bug must
    never fail the whole document push; the caller falls back to a
    plain code block for this one diagram."""
    from sdd.utils.mermaid_render import render_mermaid_svg
    try:
        svg = render_mermaid_svg(code)
    except Exception:
        return None
    filename = f"diagram-{len(attachments) + 1}.svg"
    attachments.append((filename, svg.encode("utf-8"), "image/svg+xml"))
    return f'<ac:image><ri:attachment ri:filename="{filename}" /></ac:image>'


def _diagram_macro(macro_name: str, source: str) -> str:
    """A structured macro wrapping raw diagram source in its plain-text
    body -- used for mermaid-app/plantuml-macro modes, where the
    installed Confluence app owns parsing and rendering; we just hand it
    the diagram source verbatim, same CDATA-wrapping convention as the
    code macro above."""
    escaped = html.escape(source)
    return (
        f'<ac:structured-macro ac:name="{macro_name}">'
        f'<ac:plain-text-body><![CDATA[{escaped}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )


def _split_table_row(line: str) -> list[str]:
    """Split a GFM pipe-table row into cells, trimming the optional
    leading/trailing pipe and each cell's surrounding whitespace.
    A backslash-escaped pipe (\\|) stays inside its cell rather than
    splitting it, so a cell can itself contain a literal '|'."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith(r"\|"):
        line = line[:-1]
    cells = re.split(r'(?<!\\)\|', line)
    return [c.strip().replace(r'\|', '|') for c in cells]


def _is_table_separator(line: str) -> bool:
    """True for a GFM table's header/body divider row, e.g. '|---|---|'
    or '|:---|:---:|---:|' (alignment markers)."""
    cells = _split_table_row(line)
    return bool(cells) and all(re.match(r'^:?-{1,}:?$', c) for c in cells)


_ALIGN_STYLE = {
    "left":   "text-align:left",
    "center": "text-align:center",
    "right":  "text-align:right",
}


def _table_alignment(sep_line: str) -> list[str]:
    aligns = []
    for c in _split_table_row(sep_line):
        left, right = c.startswith(":"), c.endswith(":")
        if left and right:
            aligns.append("center")
        elif right:
            aligns.append("right")
        elif left:
            aligns.append("left")
        else:
            aligns.append("")
    return aligns


def _render_table(header: list[str], rows: list[list[str]], align: list[str]) -> str:
    """Render a parsed GFM table as Confluence storage format's plain
    XHTML <table> markup -- Confluence renders this natively, no
    ac:structured-macro needed (unlike code blocks)."""
    def cell(tag: str, text: str, a: str) -> str:
        style = f' style="{_ALIGN_STYLE[a]}"' if a in _ALIGN_STYLE else ""
        return f"<{tag}{style}>{_inline(text)}</{tag}>"

    def pad(row: list[str]) -> list[str]:
        # Tolerate a body row with fewer/more cells than the header --
        # markdown tables in hand-written docs aren't always perfectly
        # rectangular.
        row = row + [""] * max(0, len(header) - len(row))
        return row[:len(header)] if header else row

    parts = ["<table><tbody><tr>"]
    parts += [cell("th", h, align[idx] if idx < len(align) else "") for idx, h in enumerate(header)]
    parts.append("</tr>")
    for row in rows:
        row = pad(row)
        parts.append("<tr>")
        parts += [cell("td", c, align[idx] if idx < len(align) else "") for idx, c in enumerate(row)]
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _inline(text: str) -> str:
    """Apply inline Markdown transforms, escaping HTML safely."""
    # Process text in segments: split on Markdown links so we can escape
    # the link label and URL independently (URL needs quote=True to prevent
    # href attribute injection via embedded double-quotes).
    parts: list[str] = []
    last = 0

    def _process_non_link(segment: str) -> str:
        s = html.escape(segment, quote=False)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', s)
        s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
        return s

    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text):
        parts.append(_process_non_link(text[last:m.start()]))
        label = html.escape(m.group(1), quote=True)
        url   = html.escape(m.group(2), quote=True)
        parts.append(f'<a href="{url}">{label}</a>')
        last = m.end()

    parts.append(_process_non_link(text[last:]))
    return "".join(parts)
