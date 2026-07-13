"""Render Mermaid diagram source to SVG entirely offline -- no browser, no
Node.js, no network call at render time. Used by confluence.diagrams.mode:
local-svg to attach a rendered image instead of showing diagram source as
plain code text (Confluence has no native Mermaid renderer).

Backed by the optional `mmdr` package (Rust-based, ~18MB, zero further
dependencies) -- not a hard dependency of this CLI. Install with:
    pip install "sddflow[diagrams]"

Renderer choice was verified, not assumed: an earlier candidate
(mermaidx/mmdc, JS-engine backend) was tested against the four Mermaid
diagram types SDD templates actually generate (flowchart, sequenceDiagram,
classDiagram, erDiagram) and failed on flowchart stadium-shape nodes
(``Actor(["User"])``, used in every design/hld/arch template's Actor node)
and on classDiagram entirely. mmdr rendered all four correctly.
"""
from __future__ import annotations


class MermaidRendererNotInstalled(Exception):
    """confluence.diagrams.mode is local-svg but the optional renderer
    package isn't installed. Message names the exact install command --
    never a bare traceback."""
    def __init__(self) -> None:
        super().__init__(
            "confluence.diagrams.mode: local-svg requires the optional "
            "'mmdr' package. Install it with:\n"
            "    pip install \"sddflow[diagrams]\""
        )


def render_mermaid_svg(source: str) -> str:
    """Render Mermaid diagram source to an SVG string.

    Raises MermaidRendererNotInstalled if the optional dependency isn't
    present, or the renderer's own exception (ValueError, typically) if
    the diagram source itself is invalid. Callers should catch broadly
    and fall back to a plain code block on any failure -- one bad or
    unsupported diagram must never fail an entire document push."""
    try:
        import mmdr
    except ImportError:
        raise MermaidRendererNotInstalled() from None
    return mmdr.render(source).svg()
