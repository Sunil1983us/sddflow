"""Convert Confluence Storage Format (XHTML) to Markdown.

Best-effort round-trip for SDD documents. Handles the same subset that
md_to_cf.py produces: headings, bold, italic, inline code, fenced code
macros, unordered/ordered lists, paragraphs, hr, and links.
"""

from __future__ import annotations

import html
import re


def cf_to_md(storage_xml: str) -> str:
    """Return a Markdown string approximating the Confluence storage XML."""
    text = storage_xml

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

    # Strip remaining ac:* elements (Confluence macros we don't handle)
    text = re.sub(r"<ac:[^>]+/>", "", text)
    text = re.sub(r"<ac:[^>]+>.*?</ac:[^>]+>", "", text, flags=re.DOTALL)

    # Headings (h1–h6)
    for lvl in range(6, 0, -1):
        text = re.sub(
            rf"<h{lvl}>(.*?)</h{lvl}>",
            lambda m, l=lvl: "#" * l + " " + _plain(m.group(1)),
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
    return text.strip()


def _plain(html_fragment: str) -> str:
    """Strip all tags from an HTML snippet (used for heading text)."""
    return re.sub(r"<[^>]+>", "", html_fragment).strip()
