# Unit tests for md_to_cf.py's Markdown -> Confluence Storage Format
# converter. Regression coverage for the table bug: pipe tables were
# falling through to the generic paragraph handler and being flattened
# onto one line, losing all row/column structure once pushed to Confluence.
from __future__ import annotations
from unittest.mock import patch

from sdd.utils.md_to_cf import md_to_storage
from sdd.utils.integrations import DiagramsConfig


class TestTables:
    def test_simple_table_renders_as_html_table(self):
        md = (
            "| Method | Path |\n"
            "|---|---|\n"
            "| POST | /tasks |\n"
            "| GET | /tasks/{id} |\n"
        )
        html, _ = md_to_storage(md)
        assert "<table><tbody>" in html
        assert "<th>Method</th>" in html
        assert "<th>Path</th>" in html
        assert "<td>POST</td>" in html
        assert "<td>/tasks</td>" in html
        assert "<td>GET</td>" in html
        assert html.count("<tr>") == 3  # header + 2 body rows

    def test_table_not_split_across_paragraphs(self):
        """Regression: previously every row was joined into one <p> with
        spaces, losing all table structure entirely."""
        md = (
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
        )
        html, _ = md_to_storage(md)
        assert "<p>" not in html

    def test_alignment_markers_produce_text_align_style(self):
        md = (
            "| Left | Center | Right |\n"
            "|:---|:---:|---:|\n"
            "| a | b | c |\n"
        )
        html, _ = md_to_storage(md)
        assert 'style="text-align:left"' in html
        assert 'style="text-align:center"' in html
        assert 'style="text-align:right"' in html

    def test_unaligned_column_has_no_style_attribute(self):
        md = "| A |\n|---|\n| 1 |\n"
        html, _ = md_to_storage(md)
        assert "style=" not in html

    def test_cell_inline_formatting_applied(self):
        md = (
            "| Field | Value |\n"
            "|---|---|\n"
            "| **Status** | `202` |\n"
        )
        html, _ = md_to_storage(md)
        assert "<strong>Status</strong>" in html
        assert "<code>202</code>" in html

    def test_ragged_row_padded_to_header_width(self):
        """A body row with fewer cells than the header doesn't crash or
        misalign the remaining columns."""
        md = (
            "| A | B | C |\n"
            "|---|---|---|\n"
            "| 1 | 2 |\n"
        )
        html, _ = md_to_storage(md)
        assert html.count("<td>") == 3
        assert "<td></td>" in html

    def test_table_followed_by_paragraph_resumes_normal_parsing(self):
        md = (
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "\n"
            "Normal paragraph after the table.\n"
        )
        html, _ = md_to_storage(md)
        assert "</table>" in html
        assert "<p>Normal paragraph after the table.</p>" in html

    def test_lines_starting_with_pipe_but_no_separator_are_not_a_table(self):
        """A single '|'-prefixed line with no following separator row
        (e.g. a stray pipe in prose) should NOT be treated as a table."""
        md = "| not a table, just a line starting with a pipe\n"
        html, _ = md_to_storage(md)
        assert "<table>" not in html
        assert "<p>" in html

    def test_real_world_endpoints_table(self):
        """The exact shape reported as broken: a wide table with cell
        content containing commas, braces, and an em dash."""
        md = (
            "| Method | Path | Purpose | Caller | Request | Response |\n"
            "|---|---|---|---|---|---|\n"
            "| POST | /v1/instant-credit-transfer | Accept transfer | Gateway | pacs.008 XML | "
            "202 — JSON {paymentId, correlationId, status, timestamp} |\n"
        )
        html, _ = md_to_storage(md)
        assert "<table><tbody>" in html
        assert html.count("<th>") == 6
        assert "202 — JSON {paymentId, correlationId, status, timestamp}" in html
        assert "<p>" not in html


class TestDiagramMacros:
    """mermaid-app / plantuml-macro modes -- routing a diagram fence
    through the configured Confluence app's macro instead of the plain
    "code" macro, which only shows syntax-highlighted text, never a
    rendered diagram (Confluence has no native diagram renderer)."""

    def test_default_mode_renders_mermaid_as_plain_code_block(self):
        """No diagrams config at all -- exact pre-existing behavior,
        unchanged. This is the regression the user originally reported:
        a mermaid fence just shows as text."""
        md = "```mermaid\ngraph TD;\nA-->B;\n```"
        html, _ = md_to_storage(md)
        assert '<ac:structured-macro ac:name="code">' in html
        assert '<ac:parameter ac:name="language">mermaid</ac:parameter>' in html
        assert "graph TD;" in html

    def test_mermaid_app_mode_emits_configured_macro(self):
        md = "```mermaid\ngraph TD;\nA-->B;\n```"
        diagrams = DiagramsConfig(mode="mermaid-app", mermaid_app_macro="mermaid-cloud")
        html, _ = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="mermaid-cloud">' in html
        assert "graph TD;" in html
        # no language parameter or generic code-macro wrapper leaks through
        assert '<ac:name="code">' not in html

    def test_mermaid_app_mode_without_macro_name_falls_back_to_code_block(self):
        """Misconfiguration (mode set but no macro_name) must never
        crash or emit a broken macro reference -- falls back to the
        same safe default as no config at all."""
        md = "```mermaid\ngraph TD;\n```"
        diagrams = DiagramsConfig(mode="mermaid-app")  # macro name left unset
        html, _ = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="code">' in html

    def test_mermaid_app_mode_does_not_affect_other_fence_languages(self):
        md = "```python\nprint(1)\n```"
        diagrams = DiagramsConfig(mode="mermaid-app", mermaid_app_macro="mermaid-cloud")
        html, _ = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="code">' in html
        assert "mermaid-cloud" not in html

    def test_plantuml_macro_mode_emits_configured_macro(self):
        md = "```plantuml\n@startuml\nAlice -> Bob\n@enduml\n```"
        diagrams = DiagramsConfig(mode="plantuml-macro", plantuml_macro="plantuml")
        html, _ = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="plantuml">' in html
        # ">" is HTML-escaped inside the CDATA body, same convention as
        # the code macro -- the arrow becomes "-&gt;"
        assert "Alice -&gt; Bob" in html

    def test_plantuml_macro_mode_does_not_convert_mermaid_fences(self):
        """plantuml-macro mode only intercepts ```plantuml fences --
        Mermaid and PlantUML are different diagram languages, not
        mechanically convertible, so a ```mermaid fence must still fall
        back to the plain code block rather than being silently routed
        through a macro that expects PlantUML syntax."""
        md = "```mermaid\ngraph TD;\n```"
        diagrams = DiagramsConfig(mode="plantuml-macro", plantuml_macro="plantuml")
        html, _ = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="code">' in html
        assert '<ac:name="plantuml">' not in html

    def test_diagram_source_is_html_escaped_in_cdata(self):
        """Diagram source containing characters like < > & must be
        HTML-escaped inside the CDATA body, same convention as the
        existing code-macro path."""
        md = "```mermaid\nA-->B & C<D>\n```"
        diagrams = DiagramsConfig(mode="mermaid-app", mermaid_app_macro="mermaid-cloud")
        html, _ = md_to_storage(md, diagrams)
        assert "&amp;" in html
        assert "&lt;D&gt;" in html


class TestLocalSvgMode:
    """diagrams.mode: local-svg -- render a ```mermaid fence to SVG
    locally (no Confluence app, no network call), reference it via
    <ac:image>/<ri:attachment>, and return the rendered bytes for the
    caller to upload as a page attachment after upsert_page()."""

    def test_success_emits_image_reference_and_queues_attachment(self):
        md = "```mermaid\ngraph TD;\nA-->B;\n```"
        diagrams = DiagramsConfig(mode="local-svg")
        with patch("sdd.utils.mermaid_render.render_mermaid_svg",
                   return_value="<svg>rendered</svg>"):
            html, attachments = md_to_storage(md, diagrams)
        assert '<ac:image><ri:attachment ri:filename="diagram-1.svg" /></ac:image>' in html
        assert '<ac:structured-macro ac:name="code">' not in html
        assert attachments == [("diagram-1.svg", b"<svg>rendered</svg>", "image/svg+xml")]

    def test_render_failure_falls_back_to_code_block(self):
        """A renderer failure (missing optional dependency, invalid
        diagram source, or a renderer bug) must never fail the whole
        document push -- falls back to the plain code block for this
        one diagram, exactly like an unconfigured mode would."""
        md = "```mermaid\nnot valid\n```"
        diagrams = DiagramsConfig(mode="local-svg")
        with patch("sdd.utils.mermaid_render.render_mermaid_svg",
                   side_effect=ValueError("bad diagram")):
            html, attachments = md_to_storage(md, diagrams)
        assert '<ac:structured-macro ac:name="code">' in html
        assert attachments == []

    def test_multiple_diagrams_get_distinct_incrementing_filenames(self):
        md = (
            "```mermaid\ngraph TD; A-->B;\n```\n\n"
            "```mermaid\nsequenceDiagram\nA->>B: hi\n```\n"
        )
        diagrams = DiagramsConfig(mode="local-svg")
        with patch("sdd.utils.mermaid_render.render_mermaid_svg",
                   return_value="<svg>x</svg>"):
            html, attachments = md_to_storage(md, diagrams)
        assert '"diagram-1.svg"' in html
        assert '"diagram-2.svg"' in html
        assert [a[0] for a in attachments] == ["diagram-1.svg", "diagram-2.svg"]

    def test_does_not_affect_other_fence_languages(self):
        md = "```python\nprint(1)\n```"
        diagrams = DiagramsConfig(mode="local-svg")
        with patch("sdd.utils.mermaid_render.render_mermaid_svg") as fake_render:
            html, attachments = md_to_storage(md, diagrams)
        fake_render.assert_not_called()
        assert '<ac:structured-macro ac:name="code">' in html
        assert attachments == []

    def test_non_local_svg_modes_never_produce_attachments(self):
        """Sanity check that mermaid-app/plantuml-macro/none never
        populate the attachments list -- only local-svg does."""
        md = "```mermaid\ngraph TD;\n```"
        for diagrams in (
            DiagramsConfig(mode="none"),
            DiagramsConfig(mode="mermaid-app", mermaid_app_macro="mermaid-cloud"),
        ):
            _, attachments = md_to_storage(md, diagrams)
            assert attachments == []
