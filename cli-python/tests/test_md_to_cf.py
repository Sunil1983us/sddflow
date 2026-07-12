# Unit tests for md_to_cf.py's Markdown -> Confluence Storage Format
# converter. Regression coverage for the table bug: pipe tables were
# falling through to the generic paragraph handler and being flattened
# onto one line, losing all row/column structure once pushed to Confluence.
from __future__ import annotations

from sdd.utils.md_to_cf import md_to_storage


class TestTables:
    def test_simple_table_renders_as_html_table(self):
        md = (
            "| Method | Path |\n"
            "|---|---|\n"
            "| POST | /tasks |\n"
            "| GET | /tasks/{id} |\n"
        )
        html = md_to_storage(md)
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
        html = md_to_storage(md)
        assert "<p>" not in html

    def test_alignment_markers_produce_text_align_style(self):
        md = (
            "| Left | Center | Right |\n"
            "|:---|:---:|---:|\n"
            "| a | b | c |\n"
        )
        html = md_to_storage(md)
        assert 'style="text-align:left"' in html
        assert 'style="text-align:center"' in html
        assert 'style="text-align:right"' in html

    def test_unaligned_column_has_no_style_attribute(self):
        md = "| A |\n|---|\n| 1 |\n"
        html = md_to_storage(md)
        assert "style=" not in html

    def test_cell_inline_formatting_applied(self):
        md = (
            "| Field | Value |\n"
            "|---|---|\n"
            "| **Status** | `202` |\n"
        )
        html = md_to_storage(md)
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
        html = md_to_storage(md)
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
        html = md_to_storage(md)
        assert "</table>" in html
        assert "<p>Normal paragraph after the table.</p>" in html

    def test_lines_starting_with_pipe_but_no_separator_are_not_a_table(self):
        """A single '|'-prefixed line with no following separator row
        (e.g. a stray pipe in prose) should NOT be treated as a table."""
        md = "| not a table, just a line starting with a pipe\n"
        html = md_to_storage(md)
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
        html = md_to_storage(md)
        assert "<table><tbody>" in html
        assert html.count("<th>") == 6
        assert "202 — JSON {paymentId, correlationId, status, timestamp}" in html
        assert "<p>" not in html
