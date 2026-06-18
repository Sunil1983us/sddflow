"""Convert Markdown to Confluence Storage Format (XHTML).

Handles the subset of Markdown used in SDD documents:
  headings, **bold**, *italic*, `inline code`, fenced code blocks,
  unordered lists (- item), ordered lists (1. item), paragraphs, ---
"""
from __future__ import annotations
import re
import html


def md_to_storage(md: str) -> str:
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
            code = html.escape("\n".join(code_lines))
            out.append(
                f'<ac:structured-macro ac:name="code">'
                f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
                f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                f'</ac:structured-macro>'
            )
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
    return "\n".join(out)


def _inline(text: str) -> str:
    """Apply inline Markdown transforms to an already-escaped-free string."""
    # Extract links before escaping so we can escape label and URL separately.
    # html.escape(quote=True) is required on the URL to prevent href injection
    # (quote=False leaves " unescaped, allowing attribute break-out).
    def _replace_link(m: re.Match) -> str:
        label = html.escape(m.group(1), quote=True)
        url   = html.escape(m.group(2), quote=True)
        return f'<a href="{url}">{label}</a>'

    result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace_link, text)
    result = html.escape(result, quote=False)
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
    result = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', result)
    result = re.sub(r'`([^`]+)`', r'<code>\1</code>', result)
    return result
